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
from .painel import FAIXAS, candidatos_quadro, criar, refinar, uniformidade
from .tabseg import segmentar

# O OpenCV grita a cada vídeo AV1 (44% do acervo) e isso poluiria horas de log.
# A API é `cv2.utils.logging` (em cv2 5.0 não existe `cv2.setLogLevel`).
cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)

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
    """Mede as três faixas: tablatura, linhas, fundo e cursor.

    Custo medido num quadro real (1920x1080): `segmentar` custa **52 ms** na faixa da
    tablatura, **190 ms** na do meio e **758 ms** na do braço — ali a cascata de
    máscaras é tentada inteira e falha. Rodar `segmentar` nas três faixas sempre é
    pagar o pior caso.

    Aqui as medidas BARATAS (`medir_linhas` 2 ms, `uniformidade` 38 ms) rodam nas três
    faixas e ficam gravadas; `segmentar` roda **em ordem decrescente de uniformidade,
    parando na primeira faixa que serve** — que é exatamente a regra de escolha
    decidida, então o resultado é o mesmo por 3 a 8x menos custo.

    Args:
        frame: quadro inteiro.

    Returns:
        Dicionário com a faixa escolhida e as medidas cruas de cada faixa, para
        análise posterior sem reabrir o vídeo.
    """
    faixas: dict[str, dict] = {}
    medidas: list[tuple[float, str, int, int, np.ndarray]] = []
    for nome, y0, y1 in FAIXAS:
        y1 = min(y1, frame.shape[0])
        if y1 - y0 < 60:
            continue
        roi = frame[y0:y1, :]
        u = uniformidade(roi)
        registro: dict = {
            "linhas": medir_linhas(roi),
            "uniformidade": round(u, 3),
        }
        det = detectar_cursor(roi)
        registro["cursor"] = bool(det)
        if det:
            registro["cursor_largura"] = int(det[1] - det[0] + 1)
            registro["cursor_matiz"] = int(det[2][0])
        faixas[nome] = registro
        medidas.append((u, nome, y0, y1, roi))

    out: dict = {"tab": False, "faixas": faixas}
    for _u, nome, y0, y1, roi in sorted(medidas, key=lambda m: -m[0]):
        try:
            g = segmentar(roi)
        except Exception as exc:  # nunca derrubar a varredura
            faixas[nome]["erro"] = type(exc).__name__
            continue
        faixas[nome].update(
            {
                "n_linhas": len(g.linhas_y),
                "passo": round(g.passo, 1),
                "glifos": len(g.glifos),
                "centrados": g.glifos_centrados,
            }
        )
        c = criar(nome, y0, y1, roi, g)
        if c is None:
            continue
        c = refinar(c)
        faixas[nome]["refinado_largura"] = int(c.roi.shape[1])
        faixas[nome].update(
            {
                "n_linhas_refinado": len(c.grade.linhas_y),
                "passo_refinado": round(c.grade.passo, 1),
                "glifos_refinado": len(c.grade.glifos),
                "centrados_refinado": c.grade.glifos_centrados,
            }
        )
        g = c.grade
        out.update(
            {
                "tab": True,
                "faixa": c.nome,
                "uniformidade": round(c.uniformidade, 3),
                "passo": round(g.passo, 1),
                "mascara": g.avisos[0].replace("mascara=", "") if g.avisos else None,
                "glifos": len(g.glifos),
                "centrados": g.glifos_centrados,
                "colunas": len({x.coluna for x in g.glifos}),
                "cordas_com_nota": len({x.corda for x in g.glifos}),
                "y_linhas": g.linhas_y,
            }
        )
        faixas[nome]["escolhida"] = True
        break
    if not out["tab"]:
        out["cursor"] = any(f.get("cursor") for f in faixas.values())
    # O mesmo critério do pipeline, medido no MESMO quadro: busca das 6 linhas regulares
    # no quadro inteiro (`painel.candidatos_quadro`). Sem isto a varredura e o pipeline
    # respondem "tem tablatura?" com regras diferentes — duas fontes de verdade para a
    # mesma pergunta. Medido: a regra das três faixas aceita piano, cabeça de violão e
    # corpo (decisão 0005); os 97,9 % de "tem notação" saíram por essa regra velha.
    # Custo medido: 70 ms por quadro.
    try:
        achados = candidatos_quadro(frame)
    except Exception:  # nunca derrubar a varredura por um quadro ruim
        achados = []
    if achados:
        escolhido = max(achados, key=lambda c: c.uniformidade)
        out["painel_quadro"] = {
            "y0": escolhido.y0,
            "y1": escolhido.y1,
            "passo": round(escolhido.grade.passo, 1),
            "glifos": len(escolhido.grade.glifos),
            "uniformidade": round(escolhido.uniformidade, 3),
        }
    out["tab_painel"] = bool(achados)
    return out


def instantes(
    duracao: float,
    quantos: int,
    frac_inicio: float = 0.08,
    frac_fim: float = 0.90,
) -> list[float]:
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
    fracoes = np.linspace(frac_inicio, frac_fim, quantos)
    return [round(duracao * float(f), 2) for f in fracoes]


def varrer_video(
    caminho: str,
    raiz: str,
    quantos: int,
    frac_inicio: float = 0.08,
    frac_fim: float = 0.90,
) -> dict:
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
        for t in instantes(dur, quantos, frac_inicio, frac_fim):
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
        # presença pelo critério do PIPELINE (quadro inteiro), para os dois poderem ser
        # comparados no mesmo registro em vez de cada um ter o seu número.
        painel = [bool(a.get("tab_painel")) for a in amostras]
        registro["painel_em_algum"] = any(painel)
        registro["frac_instantes_com_painel"] = (
            round(sum(painel) / len(painel), 3) if painel else 0.0
        )
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
    # Medido no `sky guitar`: a tablatura aparece da METADE para o fim, então amostrar a
    # segunda metade detecta quase tudo; amostrar cedo subestima. Ver ESTADO.md.
    ap.add_argument("--frac-inicio", type=float, default=0.08)
    ap.add_argument("--frac-fim", type=float, default=0.90)
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
                    registro = varrer_video(
                        v,
                        args.raiz,
                        args.instantes,
                        args.frac_inicio,
                        args.frac_fim,
                    )
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
