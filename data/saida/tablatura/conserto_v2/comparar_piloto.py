"""Compara o piloto novo com o anterior, por instante, e desenha a folha dos que mudaram.

Só lê: o piloto anterior (data/saida/cifra/copia/...), o piloto novo (conserto_v2/piloto) e
os quadros do cache. Escreve apenas em data/saida/conserto_v2/.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from tab.cache import ModoCache, pasta_do_video

RAIZ = Path("/app")
ANTIGO = RAIZ / "data/saida/cifra/copia/data/saida/cifra/piloto/censo.jsonl"
NOVO = RAIZ / "data/saida/conserto_v2/piloto/censo.jsonl"
SAIDA_FOLHA = RAIZ / "data/saida/conserto_v2/piloto_mudaram.jpg"
SAIDA_TXT = RAIZ / "data/saida/conserto_v2/piloto_comparacao.txt"


def carregar(caminho: Path) -> dict[str, dict]:
    """Lê um JSONL do censo indexado pelo arquivo.

    Args:
        caminho: JSONL de saída do ``tab.censo``.

    Returns:
        Mapa arquivo -> linha (a última linha vale).
    """
    linhas = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            r = json.loads(linha)
            linhas[r["arquivo"]] = r
    return linhas


def main() -> None:
    """Gera o relatório de comparação e a folha dos instantes SEM -> TAB."""
    antigo = carregar(ANTIGO)
    novo = carregar(NOVO)
    comuns = sorted(set(antigo) & set(novo))
    so_antigo = sorted(set(antigo) - set(novo))
    so_novo = sorted(set(novo) - set(antigo))

    sem_para_tab: Counter = Counter()
    tab_para_sem: Counter = Counter()
    total_instantes: Counter = Counter()
    mudaram: list[dict] = []
    regressoes: list[dict] = []
    desalinhados: list[str] = []
    modo = ModoCache()

    for arq in comuns:
        a, n = antigo[arq], novo[arq]
        canal = n["canal"]
        ia, ina = a["instantes"], n["instantes"]
        if len(ia) != len(ina) or any(
            abs(x["t"] - y["t"]) > 0.01 for x, y in zip(ia, ina, strict=False)
        ):
            desalinhados.append(arq)
            continue
        for i, (x, y) in enumerate(zip(ia, ina, strict=True)):
            total_instantes[canal] += 1
            if not x["tab"] and y["tab"]:
                sem_para_tab[canal] += 1
                mudaram.append(
                    {
                        "canal": canal,
                        "arquivo": arq,
                        "chave": n["chave"],
                        "i": i,
                        "t": y["t"],
                        "rect": y.get("rect"),
                    }
                )
            elif x["tab"] and not y["tab"]:
                tab_para_sem[canal] += 1
                regressoes.append(
                    {"canal": canal, "arquivo": arq, "i": i, "t": y["t"]}
                )

    linhas = []
    linhas.append(f"videos no piloto antigo: {len(antigo)}  novo: {len(novo)}")
    linhas.append(f"videos em comum: {len(comuns)}")
    linhas.append(f"so no antigo: {len(so_antigo)}  so no novo: {len(so_novo)}")
    linhas.append(f"desalinhados (instantes diferentes): {len(desalinhados)}")
    linhas.append("")
    linhas.append("canal | instantes comparados | SEM->TAB | TAB->SEM")
    for canal in sorted(total_instantes):
        linhas.append(
            f"{canal} | {total_instantes[canal]} | {sem_para_tab[canal]} | "
            f"{tab_para_sem[canal]}"
        )
    linhas.append(
        f"TOTAL | {sum(total_instantes.values())} | {sum(sem_para_tab.values())} | "
        f"{sum(tab_para_sem.values())}"
    )
    linhas.append("")
    linhas.append(f"REGRESSOES TAB->SEM ({len(regressoes)}):")
    for r in regressoes:
        linhas.append(f"  {r['canal']} | {r['arquivo']} | i={r['i']} t={r['t']}")
    linhas.append("")
    linhas.append(f"SEM->TAB ({len(mudaram)}):")
    for m in mudaram:
        linhas.append(
            f"  {m['canal']} | {m['arquivo']} | i={m['i']} t={m['t']} rect={m['rect']}"
        )
    SAIDA_TXT.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))

    desenhar_folha(mudaram)


def desenhar_folha(mudaram: list[dict], colunas: int = 3, largura: int = 560) -> None:
    """Desenha os quadros SEM->TAB com a caixa e o código, numa folha JPEG.

    Args:
        mudaram: instantes que passaram de SEM para TAB no piloto novo.
        colunas: quantas miniaturas por linha.
        largura: largura de cada miniatura, em px.
    """
    modo = ModoCache()
    celulas = []
    for k, m in enumerate(mudaram):
        pasta = pasta_do_video(m["chave"], modo)
        quadro_path = pasta / f"presenca_{m['i']:02d}.png"
        img = cv2.imread(str(quadro_path))
        if img is None:
            img = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(img, "SEM QUADRO", (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        else:
            img = img.copy()
            if m["rect"]:
                x0, y0, x1, y1 = (int(v) for v in m["rect"])
                cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), max(3, img.shape[1] // 400))
        escala = largura / img.shape[1]
        peq = cv2.resize(img, (largura, int(img.shape[0] * escala)), interpolation=cv2.INTER_AREA)
        cabeca = np.full((46, largura, 3), 255, dtype=np.uint8)
        codigo = f"#{k:02d} {m['canal'][:14]} t={m['t']:.1f}s i={m['i']}"
        cv2.putText(cabeca, codigo, (6, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        celulas.append(np.vstack([cabeca, peq]))

    if not celulas:
        print("nenhum SEM->TAB para desenhar")
        return
    altura = max(c.shape[0] for c in celulas)
    linhas_img = []
    for r in range(0, len(celulas), colunas):
        fila = []
        for c in celulas[r : r + colunas]:
            pad = np.full((altura, largura, 3), 255, dtype=np.uint8)
            pad[: c.shape[0], : c.shape[1]] = c
            fila.append(pad)
        while len(fila) < colunas:
            fila.append(np.full((altura, largura, 3), 255, dtype=np.uint8))
        linhas_img.append(np.hstack(fila))
    folha = np.vstack(linhas_img)
    cv2.imwrite(str(SAIDA_FOLHA), folha, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"folha: {SAIDA_FOLHA} {folha.shape}")


if __name__ == "__main__":
    main()
