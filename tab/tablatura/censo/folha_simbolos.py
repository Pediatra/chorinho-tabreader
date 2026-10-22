"""Folha de contato dos símbolos INTEIROS que o dono marcou — exibição, não detecção.

Por que existe: o dono viu o símbolo **cortado** na auditoria, e estava certo. A janela que o modelo julga
tem 2,4 x 1,6 passos, e era ELA que a página mostrava. Medido depois: mostrar uma janela maior **não muda a
detecção** (78 acertos nos dois lados) — **exibição e detecção são coisas separadas**.

Duas lições do dono estão embutidas aqui, cada uma corrigindo um recorte meu:

1. **O ARPEJO**: "símbolo que tem tamanho variável dependendo de quantas cordas tem que ser tocadas —
   seria interessante se ele pegasse ele por inteiro para definir quais cordas devem ser arpejadas". O
   corte **apagava a informação**: a altura do arpejo É quais cordas. Por isso o recorte não é mais uma
   janela fixa: é a **caixa dos componentes vizinhos da marca**.
2. **SÍMBOLO COMPOSTO**: parênteses + arco são **componentes separados**; cortar por um só continua
   cortando o símbolo. Por isso a caixa é a **união** dos componentes que caem perto da marca.

Uso:

    python -m tab.folha_simbolos --saida data/saida/folha_inteira
"""

import argparse
import glob
import json
import os
import pathlib
import sys

import cv2
import numpy as np

from tab.comum.caminhos import COLETA_MARCAR, FOLHA_INTEIRA, GOLD_MARCAS_SIMBOLOS_6
from tab.tablatura.leitura.inventario import ler_quadro
from tab.tablatura.leitura.painel import escolher
from tab.tablatura.leitura.tabseg import _sem_faixas, mascaras_candidatas
from tab.tablatura.produto.pipeline import roi_das_cordas


def _caixa_do_simbolo(
    cinza: np.ndarray, x: int, y: int, passo: float, linhas: list[int]
) -> tuple[int, int, int, int]:
    """Devolve a caixa que contém o símbolo da marca: união dos componentes vizinhos.

    Args:
        cinza: painel em tons de cinza.
        x: coluna da marca (coordenada do quadro).
        y: linha da marca (coordenada do quadro).
        passo: distância entre cordas, em px.

    Returns:
        ``(x0, y0, x1, y1)`` com margem; se nenhum componente aparecer, uma janela fixa de 2,0 x 1,6 passos.
    """
    # AS FAIXAS DAS CORDAS SAEM DA MÁSCARA. Motivo medido: o ARCO encosta na linha e o componente
    # dele traz um pedaço de linha junto (235 px de largura para um arco ✗), e o dono pediu duas
    # vezes "a imagem podia ser menor". Sem as faixas o arco fica justo, e o ARPEJO — que cruza as
    # linhas — vira pedaços cuja UNIÃO cobre o arpejo inteiro (a altura dele é a informação).
    mascara = dict(mascaras_candidatas(cinza)).get("otsu")
    if mascara is not None:
        mascara = _sem_faixas(mascara, linhas, passo)
    hx, hy = int(2.0 * passo), int(1.6 * passo)
    if mascara is None:
        return x - hx, y - hy, x + hx, y + hy
    n, _rot, stats, _cent = cv2.connectedComponentsWithStats(
        mascara.astype(np.uint8), 8
    )
    x0 = y0 = 10**9
    x1 = y1 = -1
    perto_x, perto_y = int(1.5 * passo), int(2.5 * passo)
    for k in range(1, n):
        cx, cy, w, h, area = stats[k]
        if area < 12:
            continue
        if abs(cx + w // 2 - x) <= perto_x and abs(cy + h // 2 - y) <= perto_y:
            x0, y0 = min(x0, cx), min(y0, cy)
            x1, y1 = max(x1, cx + w), max(y1, cy + h)
    if x1 < 0:
        return x - hx, y - hy, x + hx, y + hy
    margem = int(0.4 * passo)
    # A UNIÃO COM A JANELA FIXA é obrigatória, e a razão está medida: só a caixa dos componentes vizinhos
    # deixou o `C07_028` com 28 x 117 px — ALTO e ESTREITO — mostrando a coluna de dígitos e PERDENDO a
    # linha ondulada do arpejo, que fica ao lado. A caixa por componente pega o que o modelo vê; a janela
    # fixa garante o CONTEXTO lateral do símbolo (arpejo, chaves, parênteses com arco).
    # LATERAL ESTREITO, VERTICAL GENEROSO. O dono apontou que o recorte "expandiu demais para a esquerda"
    # (o `C06_010`, um arco de ligadura simples, saiu largo): a janela fixa de ±2,0 passos entrava inteira
    # no eixo x. Ela existia para compensar uma SELEÇÃO ruim, não para enquadrar. Agora o x leva só uma
    # margem pequena; o y mantém a janela inteira, porque é a ALTURA que carrega informação (o arpejo
    # diz quais cordas).
    lateral = int(0.6 * passo)
    return (
        min(x0 - margem, x - lateral),
        min(y0 - margem, y - hy),
        max(x1 + margem, x + lateral),
        max(y1 + margem, y + hy),
    )


def main() -> int:
    """Recorta cada marca do dono pela caixa dos componentes vizinhos e escreve folhas de 24."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--marca", default=str(GOLD_MARCAS_SIMBOLOS_6))
    ap.add_argument("--indice", default=str(COLETA_MARCAR / "indice.json"))
    ap.add_argument("--saida", default=str(FOLHA_INTEIRA))
    ap.add_argument("--altura", type=int, default=96)
    args = ap.parse_args()

    os.makedirs(args.saida, exist_ok=True)
    indice = {
        r["arq"]: r
        for r in json.loads(pathlib.Path(args.indice).read_text(encoding="utf-8"))
    }
    marcas: dict[str, list[dict]] = {}
    for marca in json.loads(pathlib.Path(args.marca).read_text(encoding="utf-8"))[
        "marcas"
    ]:
        marcas.setdefault(marca["imagem"], []).append(marca)

    celulas = []
    alturas = []
    for imagem, ms in sorted(marcas.items()):
        reg = indice.get(imagem)
        if reg is None:
            continue
        base = os.path.basename(str(reg["video"]))
        videos = [
            v
            for v in glob.glob(f"/acervo/{reg['canal']}/*.mp4")
            if os.path.basename(v).startswith(base[:24])
        ]
        if not videos:
            continue
        quadro, _ = ler_quadro(videos[0], reg["frac"])
        cand = escolher(quadro)
        if cand is None or not (14 <= cand.grade.passo <= 45):
            continue
        passo = cand.grade.passo
        y0, _y1 = roi_das_cordas(cand)
        cinza = quadro if quadro.ndim == 2 else cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
        for k, marca in enumerate(ms):
            # A MARCA ESTA EM COORDENADA DA FAIXA (y ~ 0..190), NAO DO QUADRO: y_quadro = y_faixa + y0.
            x, y = int(marca["x"]), int(marca["y"]) + y0
            x0, y0c, x1, y1c = _caixa_do_simbolo(
                cinza, x, y, passo, list(cand.grade.linhas_y)
            )
            rec = cinza[max(0, y0c) : y1c, max(0, x0) : x1]
            if rec.shape[0] < 16 or rec.shape[1] < 16:
                continue
            nome = f"{imagem.split('_')[0]}_{k:03d}.png"
            cv2.imwrite(f"{args.saida}/{nome}", rec)
            alturas.append(rec.shape[0] / passo)
            escala = args.altura / rec.shape[0]
            im = cv2.resize(rec, (max(24, int(rec.shape[1] * escala)), args.altura))
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
            et = np.full((16, im.shape[1], 3), 255, np.uint8)
            # ROTULO UNICO: o nome do recorte (`C06_003`), nao so o prefixo da imagem.
            cv2.putText(
                et, nome[:-4], (2, 12), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 0, 200), 1
            )
            celulas.append(np.vstack([et, im]))

    for s in range(0, len(celulas), 24):
        grupo = celulas[s : s + 24]
        linhas = []
        for i in range(0, len(grupo), 6):
            linha = grupo[i : i + 6]
            largura = max(c.shape[1] for c in linha)
            linha = [
                cv2.copyMakeBorder(
                    c,
                    0,
                    6,
                    0,
                    largura - c.shape[1],
                    cv2.BORDER_CONSTANT,
                    value=(255, 255, 255),
                )
                for c in linha
            ]
            linhas.append(np.hstack(linha))
        largura = max(ln.shape[1] for ln in linhas)
        linhas = [
            cv2.copyMakeBorder(
                ln,
                0,
                6,
                0,
                largura - ln.shape[1],
                cv2.BORDER_CONSTANT,
                value=(180, 180, 180),
            )
            for ln in linhas
        ]
        cv2.imwrite(f"{args.saida}/folha_{s // 24}.png", np.vstack(linhas))
    if alturas:
        a = np.array(alturas)
        print(
            f"recortes: {len(celulas)} | folhas: {(len(celulas) + 23) // 24} | "
            f"altura em passos: mediana {np.median(a):.2f} | p90 {np.percentile(a, 90):.2f} | max {a.max():.2f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
