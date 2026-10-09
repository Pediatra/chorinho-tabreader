"""Varredura do acervo: a tablatura está na tela, e quando?

Motivo: a tablatura **aparece e desaparece** durante o vídeo, e o formato pode mudar
dentro do mesmo vídeo (tema claro/escuro, cor de voz, marcador por faixa ou por cor).
Então "este vídeo tem tablatura" não é propriedade de um quadro: é um conjunto de
**intervalos de presença**. O inventário antigo lia UM quadro por vídeo e subestimava a
cobertura.

Desenho:
  - custo medido: ler um quadro custa 0,17 s pelo OpenCV (51% dos arquivos) e 0,40 s
    pelo ffmpeg (100%). O leitor é escolhido UMA vez por vídeo e reaproveitado nos
    instantes seguintes;
  - grava **mais do que precisa**: picos de linha por faixa, passo, máscara e cursor,
    para que a análise posterior não precise reabrir vídeo nenhum;
  - grava **incremental** (JSONL, um vídeo por linha) e **pula o que já fez**: uma
    varredura de horas precisa sobreviver a queda e a `--max-segundos`.

Uso:
    python -m tab.varredura --raiz /acervo --todos --instantes 1 --saida data/saida/varredura/inventario
    python -m tab.varredura --raiz /acervo --canais "sky guitar" cifra\\ club --instantes 6 \\
        --saida data/saida/varredura/presenca
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import time

import cv2
import numpy as np

from .caminhos import SAIDA
from .cursor import detectar_cursor
from .tabseg import segmentar

# O OpenCV grita a cada vídeo AV1 (44% do acervo) e isso poluiria horas de log.
# A API é `cv2.utils.logging` (em cv2 5.0 não existe `cv2.setLogLevel`).
cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)

#: Faixas verticais onde o painel costuma estar (a posição varia por vídeo).
FAIXAS = [("topo", 0, 400), ("meio", 300, 750), ("base", 620, 1080)]

#: Frações da duração amostradas. Evita o começo e o fim (vinheta/fala/despedida).
FRACOES_PADRAO = (0.08, 0.22, 0.36, 0.50, 0.64, 0.78, 0.90)


def duracao_s(caminho: str) -> float:
    """Duração do vídeo em segundos (0.0 se o ffprobe falhar)."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                caminho,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return float(proc.stdout.strip() or 0.0)
    except Exception:
        return 0.0


def _ffmpeg_em(caminho: str, t_s: float) -> np.ndarray | None:
    """Um quadro no instante pedido, por ffmpeg em software (lê 100% do acervo)."""
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                f"{max(0.0, t_s):.2f}",
                "-i",
                caminho,
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ],
            capture_output=True,
            timeout=120,
        )
        if proc.stdout:
            frame = cv2.imdecode(np.frombuffer(proc.stdout, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None and frame.size:
                return frame
    except Exception:
        pass
    return None


class Leitor:
    """Lê quadros de um vídeo escolhendo o caminho mais rápido que funcionar.

    O OpenCV é ~2,4x mais rápido, mas falha em 49% do acervo (AV1 sem aceleração).
    A escolha é feita UMA vez por vídeo e vale para todos os instantes dele.
    """

    def __init__(self, caminho: str) -> None:
        self.caminho = caminho
        self.cap: cv2.VideoCapture | None = None
        self.via = "ffmpeg"
        cap = cv2.VideoCapture(caminho)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None and frame.size:
                self.cap = cap
                self.via = "cv2"
                self._primeiro = frame
            else:
                cap.release()
        self._primeiro: np.ndarray | None = getattr(self, "_primeiro", None)

    def ler(self, t_s: float) -> np.ndarray | None:
        """Quadro no instante t (segundos)."""
        if self.cap is not None:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t_s) * 1000.0)
            ok, frame = self.cap.read()
            if ok and frame is not None and frame.size:
                return frame
            # cv2 falhou no meio do vídeo: cai para ffmpeg daqui em diante
            self.cap.release()
            self.cap = None
            self.via = "ffmpeg"
        return _ffmpeg_em(self.caminho, t_s)

    def fechar(self) -> None:
        """Libera o decodificador."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None


def medir_linhas(banda: np.ndarray) -> dict:
    """Conta linhas horizontais regulares na faixa (serve para TAB e para partitura).

    Usa Otsu e o perfil de tinta por linha: não depende do `tabseg`, então roda
    mesmo quando a faixa não é tablatura — é assim que a partitura de 5 linhas fica
    registrada em vez de ser confundida com ausência de tablatura.

    Args:
        banda: recorte da faixa (altura x largura), BGR ou cinza.

    Returns:
        Dicionário com número de picos, espaçamento mediano e cobertura de tinta.
    """
    cinza = banda if banda.ndim == 2 else cv2.cvtColor(banda, cv2.COLOR_BGR2GRAY)
    if cinza.size == 0:
        return {"picos": 0, "espacamento": 0.0, "tinta": 0.0}
    _, tinta = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if tinta.mean() > 127:  # fundo claro: a tinta é o que está escuro
        tinta = 255 - tinta
    perfil = (tinta > 127).mean(axis=1)
    limiar = max(0.15, float(perfil.mean()) * 1.6)
    picos: list[int] = []
    i = 0
    while i < len(perfil):
        if perfil[i] >= limiar:
            j = i
            while j + 1 < len(perfil) and perfil[j + 1] >= limiar:
                j += 1
            picos.append((i + j) // 2)
            i = j + 1
        else:
            i += 1
    espacamento = float(np.median(np.diff(picos))) if len(picos) > 1 else 0.0
    return {
        "picos": len(picos),
        "espacamento": round(espacamento, 1),
        "tinta": round(float((tinta > 127).mean()), 4),
    }


def medir_quadro(frame: np.ndarray) -> dict:
    """Mede as três faixas do quadro: tablatura, linhas e cursor.

    Args:
        frame: quadro inteiro.

    Returns:
        Dicionário com a faixa escolhida, a máscara/passo/glifos e as medidas cruas
        de cada faixa (para análise posterior sem reabrir o vídeo).
    """
    faixas: dict[str, dict] = {}
    melhor = None
    for nome, y0, y1 in FAIXAS:
        y1 = min(y1, frame.shape[0])
        if y1 - y0 < 60:
            continue
        roi = frame[y0:y1, :]
        medidas = medir_linhas(roi)
        registro = {"linhas": medidas}
        try:
            g = segmentar(roi)
        except Exception as exc:  # nunca derrubar a varredura
            registro["erro"] = type(exc).__name__
            faixas[nome] = registro
            continue
        registro["n_linhas"] = len(g.linhas_y)
        registro["passo"] = round(g.passo, 1)
        registro["glifos"] = len(g.glifos)
        registro["centrados"] = g.glifos_centrados
        faixas[nome] = registro
        if len(g.linhas_y) == 6 and g.glifos:
            pontos = (g.glifos_centrados, len(g.glifos))
            if melhor is None or pontos > melhor[0]:
                melhor = (pontos, nome, g)

    out: dict = {"tab": False, "faixas": faixas}
    if melhor is not None:
        pontos, nome, g = melhor
        out.update(
            {
                "tab": True,
                "faixa": nome,
                "passo": round(g.passo, 1),
                "mascara": g.avisos[0].replace("mascara=", "") if g.avisos else None,
                "glifos": len(g.glifos),
                "centrados": g.glifos_centrados,
                "colunas": len({x.coluna for x in g.glifos}),
                "cordas_com_nota": len({x.corda for x in g.glifos}),
                "y_linhas": g.linhas_y,
            }
        )
    det = detectar_cursor(frame)
    out["cursor"] = bool(det)
    if det:
        # detectar_cursor devolve (x0, x1, (matiz, sat))
        out["cursor_largura"] = int(det[1] - det[0] + 1)
        out["cursor_matiz"] = int(det[2][0])
    return out


def instantes(duracao: float, quantos: int) -> list[float]:
    """Instantes de amostragem, em segundos.

    Args:
        duracao: duração do vídeo em segundos (0 se desconhecida).
        quantos: quantos instantes amostrar; 1 usa o meio do vídeo.

    Returns:
        Lista de instantes distintos em segundos.
    """
    if duracao <= 0:
        return [0.0]
    if quantos <= 1:
        return [round(duracao * 0.35, 2)]
    fracoes = np.linspace(0.08, 0.90, quantos)
    return [round(duracao * float(f), 2) for f in fracoes]


def varrer_video(caminho: str, raiz: str, quantos: int) -> dict:
    """Varre um vídeo e devolve a linha de resultado (sem escrever nada)."""
    rel = os.path.relpath(caminho, raiz)
    canal = rel.split(os.sep)[0]
    dur = duracao_s(caminho)
    registro: dict = {
        "canal": canal,
        "arquivo": rel,
        "duracao_s": round(dur, 1),
    }
    leitor = Leitor(caminho)
    registro["via"] = leitor.via
    try:
        amostras = []
        for t in instantes(dur, quantos):
            frame = leitor.ler(t)
            if frame is None:
                amostras.append({"t": t, "erro": "sem_quadro"})
                continue
            m = medir_quadro(frame)
            m["t"] = t
            amostras.append(m)
            del frame
        registro["amostras"] = amostras
        presencas = [bool(a.get("tab")) for a in amostras]
        registro["tab_em_algum"] = any(presencas)
        registro["frac_instantes_com_tab"] = round(
            sum(presencas) / max(1, len(presencas)), 3
        )
        registro["altura"] = (
            int(leitor._primeiro.shape[0]) if leitor._primeiro is not None else None
        )
    finally:
        leitor.fechar()
    return registro


def canais_e_videos(raiz: str, canais: list[str] | None) -> dict[str, list[str]]:
    """Lista os vídeos por canal, em ordem estável."""
    achados: dict[str, list[str]] = {}
    for d in sorted(glob.glob(os.path.join(raiz, "*"))):
        if not os.path.isdir(d):
            continue
        nome = os.path.basename(d)
        if canais and nome not in canais:
            continue
        vids = sorted(glob.glob(os.path.join(d, "**", "*.mp4"), recursive=True))
        vids += sorted(glob.glob(os.path.join(d, "**", "*.mkv"), recursive=True))
        vids += sorted(glob.glob(os.path.join(d, "**", "*.webm"), recursive=True))
        if vids:
            achados[nome] = vids
    return achados


def ja_feitos(caminho_jsonl: str) -> set[str]:
    """Conjunto de arquivos já varridos (para a varredura ser retomável)."""
    prontos: set[str] = set()
    if not os.path.exists(caminho_jsonl):
        return prontos
    with open(caminho_jsonl, encoding="utf-8") as fh:
        for linha in fh:
            try:
                prontos.add(json.loads(linha)["arquivo"])
            except Exception:
                continue
    return prontos


def main() -> int:
    """Varre o acervo e grava uma linha JSON por vídeo."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default="/acervo")
    ap.add_argument("--saida", default=str(SAIDA / "varredura" / "inventario"))
    ap.add_argument("--canais", nargs="*", default=None)
    ap.add_argument("--instantes", type=int, default=1)
    ap.add_argument(
        "--limite", type=int, default=0, help="máximo de vídeos (0 = todos)"
    )
    ap.add_argument(
        "--max-segundos",
        type=float,
        default=0.0,
        help="para limpo depois deste tempo (0 = sem limite); retome rodando de novo",
    )
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.saida), exist_ok=True)
    canais = canais_e_videos(args.raiz, args.canais)
    total = sum(len(v) for v in canais.values())
    print(
        f"canais: {len(canais)} | vídeos: {total} | instantes: {args.instantes}",
        flush=True,
    )

    t_inicio = time.time()
    processados = 0
    erros = 0
    for canal, vids in canais.items():
        destino = f"{args.saida}_{canal.replace('/', '_')}.jsonl"
        prontos = ja_feitos(destino)
        pendentes = [v for v in vids if os.path.relpath(v, args.raiz) not in prontos]
        print(
            f"\n=== {canal}: {len(vids)} vídeos, {len(prontos)} já feitos, "
            f"{len(pendentes)} pendentes -> {os.path.basename(destino)}",
            flush=True,
        )
        if not pendentes:
            continue
        with open(destino, "a", encoding="utf-8") as fh:
            for i, v in enumerate(pendentes, 1):
                if args.limite and processados >= args.limite:
                    print("limite de vídeos atingido", flush=True)
                    return 0
                if args.max_segundos and time.time() - t_inicio > args.max_segundos:
                    print(
                        f"tempo esgotado após {processados} vídeos; retome rodando de novo",
                        flush=True,
                    )
                    return 0
                try:
                    registro = varrer_video(v, args.raiz, args.instantes)
                except Exception as exc:
                    registro = {
                        "canal": canal,
                        "arquivo": os.path.relpath(v, args.raiz),
                        "erro": f"{type(exc).__name__}: {exc}",
                    }
                if "erro" in registro:
                    erros += 1
                    # Guarda contra bug sistemático: o try/except por vídeo
                    # protegeria a varredura e esconderia o erro a noite toda.
                    if processados >= 20 and erros / (processados + 1) > 0.5:
                        print(
                            f"ABORTADO: {erros} de {processados + 1} vídeos com erro — "
                            f"é bug sistemático. Último: {registro['erro']}",
                            flush=True,
                        )
                        return 1
                fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                processados += 1
                if i % 10 == 0 or i == len(pendentes):
                    marcas = [a.get("tab") for a in registro.get("amostras", [])]
                    print(
                        f"  [{i}/{len(pendentes)}] {os.path.basename(v)[:44]:<44} "
                        f"tab={marcas} via={registro.get('via')}",
                        flush=True,
                    )
    print(
        f"\nfim: {processados} vídeos em {(time.time() - t_inicio) / 60:.1f} min",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
