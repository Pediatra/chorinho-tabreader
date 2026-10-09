"""Vídeo → intervalos de notação → JSON e MusicXML **por intervalo**.

Requisito do dono do projeto, que muda o formato de saída: *"praticamente todos os vídeos
contêm tablatura em algum momento, são vários formatos e eles **aparecem ou desaparecem**
em certos momentos da tela"*. Medido: no `sky guitar` a tablatura aparece **da metade para
o fim** (20 de 20 vídeos chamados de "sem tablatura" por um instante único têm tablatura em
algum instante).

Então a saída não é "o JSON do vídeo": é uma lista de **intervalos**, cada um com seu
painel, seu passo, sua máscara, seu mecanismo de tempo — e cada intervalo declara o que é
medido e o que é inferido.

Uso:
    python -m tab.pipeline VIDEO --saida data/saida/intervalos
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field

import cv2

from .caminhos import MODELO_PADRAO, SAIDA
from .cursor import detectar_cursor
from .digito import carregar
from .inventario import ler_quadro
from .musicxml import exportar
from .painel import escolher
from .reconhecer import carregar_modelo, reconhecer_linha
from .tempo import atribuir_tempos, resumo, tempos_por_patamar

#: Frações amostradas para achar a notação. Densidade na segunda metade porque é onde ela
#: costuma estar (`sky guitar`) e sem custo proibitivo.
FRACOES_PADRAO: tuple[float, ...] = (0.40, 0.50, 0.60, 0.70, 0.80, 0.90)

#: Folga de cada lado de uma amostra com notação, em segundos.
FOLGA_S = 20.0

#: Passo entre cordas abaixo disto não é tablatura: a faixa medida no acervo é
#: 14–45 px (ver ESTADO.md). Medido: uma amostra com 7,6 px era painel falso.
PASSO_MINIMO_PX = 10.0

#: Passo da série do marcador, em segundos (denso: amostragem esparsa já enganou aqui).
PASSO_SERIE_S = 0.5


@dataclass
class Intervalo:
    """Trecho do vídeo em que existe notação na tela."""

    t0: float
    t1: float
    amostras: list[dict] = field(default_factory=list)
    json: dict | None = None
    musicxml: str | None = None

    @property
    def meio(self) -> float:
        """Instante do meio do intervalo."""
        return (self.t0 + self.t1) / 2

    def melhor_amostra(self) -> dict | None:
        """A amostra com o painel mais confiável dentro do que é PLAUSÍVEL.

        Medido no `sky guitar` (henze): entre as amostras do intervalo havia uma com
        `passo 7,6 px` — fora da faixa medida no acervo (14–45 px, ver ESTADO.md) — e
        uniformidade 0,877 contra 0,867 das outras, que tinham `passo 16` e o DOBRO de
        glifos. Ordenar só por uniformidade escolhia a amostra suspeita, e a diferença de
        0,01 é ruído. Então: descarta passo implausível e arredonda a uniformidade antes
        de comparar, deixando os glifos decidirem o empate.
        """
        boas = [
            a
            for a in self.amostras
            if a.get("tem_notacao") and (a.get("passo") or 0) >= PASSO_MINIMO_PX
        ]
        if not boas:
            return None
        return max(
            boas,
            key=lambda a: (
                round(a.get("uniformidade") or 0.0, 2),
                a.get("glifos") or 0,
            ),
        )


def amostrar_presenca(
    video: str, fracoes: tuple[float, ...] = FRACOES_PADRAO
) -> list[dict]:
    """Mede, em cada fração, se há notação na tela.

    Args:
        video: caminho do vídeo.
        fracoes: frações da duração a amostrar.

    Returns:
        Uma entrada por fração, com ``t``, ``tem_notacao``, faixa, uniformidade e passo.
    """
    cap = cv2.VideoCapture(video)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duracao = n / fps if n else 0.0
    cap.release()
    if duracao <= 0:
        return []

    amostras: list[dict] = []
    for frac in fracoes:
        quadro, via = ler_quadro(video, frac)
        registro: dict = {
            "t": round(duracao * frac, 1),
            "frac": round(frac, 4),
            "via": via,
            "tem_notacao": False,
        }
        if quadro is not None:
            candidato = escolher(quadro)
            if candidato is not None:
                registro.update(
                    {
                        "tem_notacao": True,
                        "faixa": candidato.nome,
                        "uniformidade": round(candidato.uniformidade, 3),
                        "passo": round(candidato.grade.passo, 1),
                        "glifos": len(candidato.grade.glifos),
                        "largura_painel": int(candidato.roi.shape[1]),
                    }
                )
        amostras.append(registro)
    return amostras


def agrupar_intervalos(
    amostras: list[dict], folga_s: float = FOLGA_S
) -> list[Intervalo]:
    """Agrupa amostras vizinhas com notação em intervalos contíguos.

    Args:
        amostras: saída de :func:`amostrar_presenca`.
        folga_s: quanto estender cada intervalo para os lados, em segundos.

    Returns:
        Intervalos em ordem de tempo, cada um com as amostras que o formaram.
    """
    marcadas = [a for a in amostras if a.get("tem_notacao")]
    if not marcadas:
        return []
    intervalos: list[Intervalo] = []
    atual = Intervalo(t0=marcadas[0]["t"] - folga_s, t1=marcadas[0]["t"] + folga_s)
    atual.amostras.append(marcadas[0])
    for amostra in marcadas[1:]:
        t = amostra["t"]
        if t - folga_s <= atual.t1:  # encosta no intervalo atual: estende
            atual.t1 = max(atual.t1, t + folga_s)
            atual.amostras.append(amostra)
        else:
            intervalos.append(atual)
            atual = Intervalo(t0=t - folga_s, t1=t + folga_s, amostras=[amostra])
    intervalos.append(atual)
    return intervalos


def roi_das_cordas(candidato) -> tuple[int, int]:
    """y absoluto do sistema de cordas (com margem) — não da faixa inteira.

    A faixa (`meio` = 300–750 px) contém a tablatura **e o vídeo abaixo dela**. Montar a
    série do marcador na faixa inteira pega elemento colorido do vídeo e o veredito sai
    `erratico` (medido: 75 pontos, passo mediano 0). Nas cordas detectadas (318–487) a
    série é o deslize limpo de ~8,5 px/s (380 pontos, veredito `salta`).

    Args:
        candidato: painel escolhido.

    Returns:
        ``(y0, y1)`` em coordenadas do quadro inteiro.
    """
    linhas = list(candidato.grade.linhas_y)
    if not linhas:
        return candidato.y0, candidato.y1
    margem = round(candidato.grade.passo) or 12  # round() de float já é int (regra 8)
    return (
        max(0, candidato.y0 + min(linhas) - margem),
        candidato.y0 + max(linhas) + margem,
    )


def serie_do_marcador(
    video: str,
    roi_y: tuple[int, int],
    t0: float,
    janela: float,
    passo_s: float = PASSO_SERIE_S,
) -> list[tuple[float, int]]:
    """Série ``(t, x)`` do marcador, amostrada DENSA dentro da janela.

    Amostragem esparsa engana: medido no `iwaki/henze`, 14 pontos a cada 9 s davam
    `erratico` e 241 pontos a cada 0,5 s dão `desliza`. O marcador se move devagar e a
    amostra grossa o encontra em posições que parecem aleatórias.
    """
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        return []
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duracao = n / fps if n else 0.0
    pontos: list[tuple[float, int]] = []
    t = t0
    while t <= min(t0 + janela, duracao):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, quadro = cap.read()
        if ok:
            det = detectar_cursor(quadro[roi_y[0] : roi_y[1], :])
            if det:
                pontos.append((round(t, 2), int(det[0])))
        t += passo_s
    cap.release()
    return pontos


def transcrever_intervalo(
    video: str,
    intervalo: Intervalo,
    modelo,
    rotulos: list[str],
    dev: str,
    dir_simbolos: str | None = None,
    prefixo: str = "",
) -> dict:
    """Transcreve UM intervalo: painel, notas, tempo (se houver marcador) e inferências.

    Args:
        video: caminho do vídeo.
        intervalo: o trecho a transcrever.
        modelo: classificador de glifos.
        rotulos: classes do modelo.
        dev: dispositivo.
        dir_simbolos: diretório dos recortes de símbolo.
        prefixo: subpasta dos símbolos.

    Returns:
        A transcrição do intervalo, com o que é medido e o que é inferido declarado.
    """
    melhor = intervalo.melhor_amostra()
    resultado: dict = {
        "t0": round(intervalo.t0, 1),
        "t1": round(intervalo.t1, 1),
        "amostras": intervalo.amostras,
        "notas": [],
    }
    if melhor is None:
        return resultado
    frac = melhor.get("frac")
    if frac is None:
        resultado["erro"] = "amostra_sem_fracao"
        return resultado
    quadro, via = ler_quadro(video, frac)
    if quadro is None:
        resultado["erro"] = "quadro_ilegivel"
        return resultado
    # O painel vem do MESMO instante da amostra. Escolher de novo podia devolver outra
    # faixa (a escolha varia com o quadro) e a série do marcador saía de uma região
    # diferente da que foi lida — medido: `erratico` com 75 pontos onde o painel certo dá
    # `salta` com 380 e o deslize de ~8,5 px/s aparece inteiro.
    candidato = escolher(quadro)
    if candidato is None:
        resultado["erro"] = "painel_desapareceu"
        return resultado
    roi_y = roi_das_cordas(candidato)
    r = reconhecer_linha(
        candidato.roi,
        modelo,
        rotulos,
        dev,
        dir_simbolos=dir_simbolos,
        prefixo=prefixo,
        discriminador=carregar(),
    )
    resultado.update(
        {
            "painel": candidato.nome,
            "uniformidade": round(candidato.uniformidade, 3),
            "passo": round(candidato.grade.passo, 2),
            "largura_painel": int(candidato.roi.shape[1]),
            "lido_via": via,
            "notas": r["notas"],
        }
    )
    serie = serie_do_marcador(video, roi_y, intervalo.t0, intervalo.t1 - intervalo.t0)
    veredito = resumo(serie)
    if veredito["veredito"] in {"desliza", "salta"}:
        xs = [n["x"] for n in r["notas"]]
        onsets = (
            atribuir_tempos(xs, serie)
            if veredito["veredito"] == "desliza"
            else tempos_por_patamar(xs, serie)
        )
        for nota, t in zip(r["notas"], onsets, strict=False):
            if t is not None:
                nota["t_ini"] = t
        distintos = len({n["t_ini"] for n in r["notas"] if "t_ini" in n})
        resultado["tempo"] = {
            "medido": distintos >= 2,
            "mecanismo": f"marcador: {veredito['veredito']}",
            "instantes_distintos": distintos,
            "serie": veredito,
        }
    else:
        resultado["tempo"] = {
            "medido": False,
            "motivo": f"marcador {veredito['veredito']} no intervalo",
            "serie": veredito,
        }
    return resultado


def processar_video(
    video: str,
    caminho_modelo: str = str(MODELO_PADRAO),
    fracoes: tuple[float, ...] = FRACOES_PADRAO,
    dir_simbolos: str | None = None,
) -> dict:
    """Processa o vídeo inteiro: presença, intervalos, transcrição e MusicXML.

    Args:
        video: caminho do vídeo.
        caminho_modelo: pesos do classificador de glifos.
        fracoes: frações amostradas para achar a notação.
        dir_simbolos: diretório dos recortes de símbolo.

    Returns:
        Dicionário com a lista de intervalos e o resumo do vídeo.
    """
    amostras = amostrar_presenca(video, fracoes)
    intervalos = agrupar_intervalos(amostras)
    if not intervalos:
        return {
            "video": os.path.basename(video),
            "tem_notacao": False,
            "intervalos": [],
            "amostras": amostras,
        }
    modelo, rotulos, dev = carregar_modelo(caminho_modelo)
    prefixo = os.path.basename(os.path.dirname(os.path.abspath(video)))
    saida = []
    for i, intervalo in enumerate(intervalos, 1):
        dados = transcrever_intervalo(
            video, intervalo, modelo, rotulos, dev, dir_simbolos, prefixo
        )
        dados["indice"] = i
        dados["rotulo"] = f"{os.path.splitext(os.path.basename(video))[0]}_int{i:02d}"
        xml, relatorio = exportar(dados, titulo=dados["rotulo"])
        dados["musicxml_relatorio"] = relatorio
        saida.append({"transcricao": dados, "musicxml": xml})
    return {
        "video": os.path.basename(video),
        "tem_notacao": True,
        "amostras": amostras,
        "intervalos": saida,
    }


def main() -> int:
    """Processa um vídeo e grava um JSON e um MusicXML por intervalo."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    ap.add_argument("--saida", default=str(SAIDA / "intervalos"))
    ap.add_argument("--simbolos", default=str(SAIDA / "simbolos"))
    args = ap.parse_args()

    resultado = processar_video(
        args.video, args.modelo, dir_simbolos=args.simbolos or None
    )
    os.makedirs(args.saida, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.video))[0][:40].strip()
    pasta = os.path.join(args.saida, base)
    os.makedirs(pasta, exist_ok=True)
    for item in resultado["intervalos"]:
        transcricao = item["transcricao"]
        nome = transcricao["rotulo"]
        with open(os.path.join(pasta, f"{nome}.json"), "w", encoding="utf-8") as fh:
            json.dump(transcricao, fh, ensure_ascii=False, indent=1)
        with open(os.path.join(pasta, f"{nome}.musicxml"), "w", encoding="utf-8") as fh:
            fh.write(item["musicxml"])
    resumo_video = {
        "video": resultado["video"],
        "tem_notacao": resultado["tem_notacao"],
        "amostras": resultado["amostras"],
        "intervalos": [
            {
                "indice": i["transcricao"]["indice"],
                "t0": i["transcricao"]["t0"],
                "t1": i["transcricao"]["t1"],
                "notas": len(i["transcricao"]["notas"]),
                "tempo": i["transcricao"].get("tempo"),
                "musicxml": i["transcricao"]["musicxml_relatorio"],
            }
            for i in resultado["intervalos"]
        ],
    }
    with open(os.path.join(pasta, "resumo.json"), "w", encoding="utf-8") as fh:
        json.dump(resumo_video, fh, ensure_ascii=False, indent=1)
    print(json.dumps(resumo_video, ensure_ascii=False, indent=1))
    print("salvo em", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
