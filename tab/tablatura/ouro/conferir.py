"""Folha de conferência: o JSON contra o quadro, em instantes sorteados.

Para N instantes sorteados (com semente), mostra o quadro do vídeo no instante em que a
coluna acende, a caixa verde na coluna que o JSON diz estar acesa naquela passagem e as
casas lidas escritas embaixo. É a resposta à pergunta "é isso que eu quero receber?": o
dono olha a folha em dois minutos.

Os quadros vêm de ``tab.leitor`` (o leitor único). A coluna e as casas vêm do JSON
``chorinho/video@1``, sem nenhuma releitura: a folha mostra o que o JSON afirma.

Uso:
    python -m tab.conferir JSON [--n 12] [--semente 0] [--video CAMINHO] [--saida PNG]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tab.comum import leitor
from tab.comum.caminhos import acervo
from tab.tablatura.produto.video import FPS_PADRAO

#: Largura, em pixels, do recorte do painel na folha.
LARGURA_PAINEL = 1100

#: Margem, em pixels, em volta da folha e entre os instantes.
MARGEM = 20

#: Metade da largura da caixa de coluna, em passos (distância entre cordas).
MEIA_CAIXA_PASSOS = 0.45

#: Cor da caixa da coluna acesa (RGB).
VERDE = (0, 170, 60)

#: Fontes do Debian/Fedora que o container tem (``fonts-liberation``), por ordem.
FONTES = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
)


def instantes(dados: dict) -> list[dict]:
    """Cada instante em que uma coluna acende, uma vez por passagem.

    Lê as passagens das exibições (``telas[].exibicoes[].passagens``), que são a fonte do
    tempo; as notas só dizem as casas.

    Args:
        dados: JSON ``chorinho/video@1``.

    Returns:
        Lista de dicionários com ``tela``, ``exibicao``, ``passagem``, ``coluna``,
        ``t_ini``, ``painel``, ``passo``, na ordem do JSON.
    """
    saida: list[dict] = []
    for tela in dados.get("telas", []):
        for e, ex in enumerate(tela.get("exibicoes", [])):
            for p, passagem in enumerate(ex.get("passagens", []), start=1):
                for item in passagem:
                    saida.append(
                        {
                            "tela": tela["id"],
                            "exibicao": e,
                            "passagem": p,
                            "coluna": item["coluna"],
                            "t_ini": item["t_ini"],
                            "painel": tela["painel"],
                            "passo": tela.get("passo") or 16.0,
                        }
                    )
    return saida


def notas_da_coluna(dados: dict, tela_id: int, coluna: int) -> list[dict]:
    """As notas do JSON nesta tela e coluna, uma por corda, em ordem de corda.

    Args:
        dados: JSON ``chorinho/video@1``.
        tela_id: id da tela.
        coluna: coluna dentro da tela (1-based).

    Returns:
        Notas distintas por corda.
    """
    por_corda: dict[int, dict] = {}
    for n in dados.get("notas", []):
        if n["tela"] == tela_id and n["coluna"] == coluna:
            por_corda.setdefault(n["corda"], n)
    return [por_corda[c] for c in sorted(por_corda)]


def x_da_coluna(dados: dict, tela_id: int, coluna: int) -> float | None:
    """Posição horizontal da coluna no quadro, pela mediana dos tokens dela.

    Usa as notas e as não-notas da coluna (símbolo também ocupa a coluna).

    Args:
        dados: JSON ``chorinho/video@1``.
        tela_id: id da tela.
        coluna: coluna dentro da tela.

    Returns:
        O x do centro da coluna, em pixels do quadro, ou ``None`` se o JSON não tem token.
    """
    xs = [
        n["x_centro_quadro"]
        for bloco in ("notas", "nao_notas")
        for n in dados.get(bloco, [])
        if n["tela"] == tela_id and n["coluna"] == coluna
    ]
    return float(statistics.median(xs)) if xs else None


def caixa_da_coluna(
    x: float, passo: float, painel: list[int]
) -> tuple[float, float, float, float]:
    """Retângulo da coluna: a faixa vertical de largura do passo, altura do painel.

    Args:
        x: centro da coluna no quadro.
        passo: distância entre cordas, em px.
        painel: ``[x0, y0, x1, y1]`` da tela no quadro.

    Returns:
        ``(x0, y0, x1, y1)`` no espaço do quadro.
    """
    meia = max(6.0, MEIA_CAIXA_PASSOS * passo)
    return (x - meia, float(painel[1]), x + meia, float(painel[3]))


def _fonte(tamanho: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """A fonte Liberation se existir, senão a padrão do Pillow.

    Args:
        tamanho: altura da fonte em pixels.

    Returns:
        Uma fonte que o Pillow sabe desenhar.
    """
    for caminho in FONTES:
        if Path(caminho).is_file():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(size=tamanho)


def _quadro_rgb(quadro: np.ndarray | None) -> Image.Image | None:
    """Converte o quadro BGR do leitor em imagem RGB do Pillow.

    Args:
        quadro: quadro em BGR, ou ``None``.

    Returns:
        A imagem, ou ``None`` se não há quadro.
    """
    if quadro is None:
        return None
    return Image.fromarray(np.ascontiguousarray(quadro[:, :, ::-1]))


def _bloco(
    quadro: Image.Image | None,
    caixa: tuple[float, float, float, float] | None,
    painel: list[int],
    cabecalho: str,
    rodape: str,
) -> Image.Image:
    """Um instante da folha: cabeçalho, recorte do painel com a caixa, e casas.

    Args:
        quadro: quadro inteiro do instante (ou ``None``).
        caixa: retângulo da coluna acesa, no espaço do quadro; ``None`` não desenha.
        painel: ``[x0, y0, x1, y1]`` da tela no quadro.
        cabecalho: texto de identificação do instante.
        rodape: casas lidas, escritas embaixo.

    Returns:
        A imagem do bloco, na largura da folha.
    """
    f_txt = _fonte(22)
    altura_txt = 30
    if quadro is None:
        recorte = Image.new("RGB", (LARGURA_PAINEL, 120), (235, 235, 235))
        ImageDraw.Draw(recorte).text(
            (10, 40), "sem quadro neste instante", font=f_txt, fill=(90, 0, 0)
        )
    else:
        x0, y0, x1, y1 = painel
        y0m, y1m = max(0, y0 - 6), min(quadro.height, y1 + 6)
        x0c, x1c = max(0, x0), min(quadro.width, x1)
        recorte = quadro.crop((x0c, y0m, x1c, y1m))
        escala = LARGURA_PAINEL / recorte.width
        recorte = recorte.resize(
            (LARGURA_PAINEL, max(1, round(recorte.height * escala))), Image.LANCZOS
        )
        if caixa is not None:
            cx0, cy0, cx1, cy1 = caixa
            desenho = ImageDraw.Draw(recorte)
            desenho.rectangle(
                [
                    (cx0 - x0c) * escala,
                    (cy0 - y0m) * escala,
                    (cx1 - x0c) * escala,
                    (cy1 - y0m) * escala,
                ],
                outline=VERDE,
                width=4,
            )
    bloco = Image.new(
        "RGB",
        (LARGURA_PAINEL, altura_txt + recorte.height + altura_txt + 14),
        (255, 255, 255),
    )
    dt = ImageDraw.Draw(bloco)
    dt.text((0, 4), cabecalho, font=f_txt, fill=(0, 0, 0))
    bloco.paste(recorte, (0, altura_txt))
    dt.text(
        (0, altura_txt + recorte.height + 4), rodape, font=f_txt, fill=(20, 60, 140)
    )
    return bloco


def folha(
    video: str, dados: dict, escolhidos: list[dict], fps: float
) -> Image.Image | None:
    """Monta a folha: um bloco por instante, em coluna única.

    Args:
        video: caminho do vídeo (lido por ``tab.leitor``).
        dados: JSON ``chorinho/video@1``.
        escolhidos: instantes sorteados (de ``instantes``).
        fps: taxa do vídeo; o quadro desenhado é o de PTS mais próximo de ``t`` (meio quadro
            antes do instante pedido, para o ``-ss`` cair no próprio quadro, e não no seguinte).

    Returns:
        A folha, ou ``None`` se não há instante.
    """
    if not escolhidos:
        return None
    blocos: list[Image.Image] = []
    for k, inst in enumerate(escolhidos, start=1):
        t = float(inst["t_ini"])
        quadro = _quadro_rgb(leitor.quadro_em(video, max(0.0, t - 0.5 / fps)))
        x = x_da_coluna(dados, inst["tela"], inst["coluna"])
        caixa = None if x is None else caixa_da_coluna(x, inst["passo"], inst["painel"])
        notas = notas_da_coluna(dados, inst["tela"], inst["coluna"])
        casas = "  ".join(f"c{n['corda']}={n['casa']}" for n in notas)
        rodape = (
            f"casas lidas: {casas}"
            if casas
            else "casas lidas: (nenhuma nota nesta coluna)"
        )
        cabecalho = (
            f"{k}. t = {t:.3f} s | tela {inst['tela']} | exibicao {inst['exibicao']}"
            f" | passagem {inst['passagem']} | coluna {inst['coluna']}"
        )
        blocos.append(_bloco(quadro, caixa, inst["painel"], cabecalho, rodape))
    altura = sum(b.height for b in blocos) + MARGEM * (len(blocos) + 1)
    folha_img = Image.new("RGB", (LARGURA_PAINEL + 2 * MARGEM, altura), (255, 255, 255))
    y = MARGEM
    for b in blocos:
        folha_img.paste(b, (MARGEM, y))
        y += b.height + MARGEM
    return folha_img


def sortear(todos: list[dict], n: int, semente: int) -> list[dict]:
    """Sorteia ``n`` instantes com semente fixa, em ordem de tempo.

    Args:
        todos: todos os instantes do JSON (de ``instantes``).
        n: quantos sortear; se passar do total, saem todos.
        semente: semente do sorteio (mesma semente, mesmos instantes).

    Returns:
        Os instantes sorteados, ordenados por ``t_ini``.
    """
    ordenados = sorted(todos, key=lambda i: (i["t_ini"], i["tela"], i["coluna"]))
    escolhidos = random.Random(semente).sample(ordenados, min(n, len(ordenados)))
    return sorted(escolhidos, key=lambda i: i["t_ini"])


def main() -> int:
    """CLI: ``python -m tab.conferir JSON --n 12``.

    Returns:
        ``0`` ao gravar a folha; ``1`` se o JSON não tem nenhum instante com tempo.
    """
    ap = argparse.ArgumentParser(description="Folha de conferência do JSON v1.")
    ap.add_argument("json")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--semente", type=int, default=0)
    ap.add_argument("--video", help="vídeo (padrão: video.arquivo no acervo)")
    ap.add_argument("--saida", help="PNG de saída (padrão: junto do JSON)")
    args = ap.parse_args()

    dados = json.loads(Path(args.json).read_text(encoding="utf-8"))
    video = args.video or str(acervo() / dados["video"]["arquivo"])
    todos = instantes(dados)
    if not todos:
        print("nenhum instante com tempo no JSON: nada para conferir", file=sys.stderr)
        return 1
    escolhidos = sortear(todos, args.n, args.semente)
    fps = leitor.info(video).get("fps") or FPS_PADRAO
    img = folha(video, dados, escolhidos, fps)
    destino = (
        Path(args.saida)
        if args.saida
        else (Path(args.json).parent / f"conferencia_{Path(args.json).stem}.png")
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino)
    print(
        f"{len(escolhidos)} de {len(todos)} instantes (semente {args.semente}) -> {destino}"
    )
    for k, inst in enumerate(escolhidos, start=1):
        casas = [
            n["casa"] for n in notas_da_coluna(dados, inst["tela"], inst["coluna"])
        ]
        print(
            f"{k:2d} t={inst['t_ini']:.3f} tela={inst['tela']} coluna={inst['coluna']} casas={casas}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
