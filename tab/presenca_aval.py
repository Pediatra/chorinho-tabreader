"""Medição da CAIXA do detector de tablatura, por quadro (Fase 7.1).

O gabarito ``data/gold/presenca_quadros.json`` foi lido à mão pelo dono, quadro a quadro
(2026-10-10). Cada caso é um quadro inteiro: ou o detector desenhou uma caixa, e o dono
disse se ela cobre tablatura real (``caixa_sobre_tablatura``), ou não desenhou caixa.

Dois números, e eles são diferentes:

- **precisão de caixa**: das caixas desenhadas, quantas cobrem tablatura de verdade.
  Caixa em cima do braço do violão ou só na pauta é nota inventada no produto.
- **revocação de caixa**: dos quadros com tablatura (``tablatura_no_quadro``), quantos
  receberam caixa sobre ela.

A presença por quadro ("há tablatura?") sai junto, só como referência: o erro que o
produto sofre é a caixa, não a presença. Uma caixa que cobre a tablatura em outra faixa
do quadro não conta como acerto; a caixa tem de estar sobre a tablatura.

Uma caixa que não bate com a do gabarito (IoU < ``LIMIAR_IOU_CAIXA``) precisa de rótulo
em ``caixas_revistas``; sem rótulo a medição para com erro, em vez de contar em silêncio.

Uso:
    python -m tab.presenca_aval
    python -m tab.presenca_aval --gold data/gold/presenca_quadros.json --saida <pasta>
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from . import leitor
from .caminhos import SAIDA, acervo
from .telas import painel_do_quadro

#: Gabarito por quadro (dono, 2026-10-10), versionado em ``data/gold``.
GOLD_QUADROS = SAIDA.parent / "gold" / "presenca_quadros.json"

#: Duas caixas são "a mesma" se a interseção sobre a união for pelo menos isto.
LIMIAR_IOU_CAIXA = 0.9


def classe(previsto: bool, rotulo: str) -> str | None:
    """Classifica uma previsão de presença contra o rótulo do dono.

    Args:
        previsto: o detector disse que há tablatura neste quadro.
        rotulo: ``tablatura``, ``nao_tablatura`` ou ``duvida``.

    Returns:
        ``VP``, ``FP``, ``VN`` ou ``FN``; ``None`` para ``duvida`` (fica fora da conta).
    """
    if rotulo == "duvida":
        return None
    real = rotulo == "tablatura"
    if previsto and real:
        return "VP"
    if previsto:
        return "FP"
    if real:
        return "FN"
    return "VN"


def _razao(a: int, b: int) -> float | None:
    """Razão arredondada a 3 casas, ou ``None`` se o denominador é zero."""
    return round(a / b, 3) if b else None


def matriz(classes: list[str | None]) -> dict:
    """Contagens da matriz de confusão com precisão e revocação.

    Args:
        classes: rótulos de ``classe`` (``None`` é ignorado).

    Returns:
        ``{"VP", "FP", "VN", "FN", "precisao", "revocacao"}``. Precisão e revocação são
        ``None`` quando o denominador é zero.
    """
    c = Counter(x for x in classes if x is not None)
    vp, fp, vn, fn = c["VP"], c["FP"], c["VN"], c["FN"]
    return {
        "VP": vp,
        "FP": fp,
        "VN": vn,
        "FN": fn,
        "precisao": _razao(vp, vp + fp),
        "revocacao": _razao(vp, vp + fn),
    }


def iou(a: list[int], b: list[int]) -> float:
    """Interseção sobre união de duas caixas ``[x0, y0, x1, y1]``.

    Args:
        a: primeira caixa.
        b: segunda caixa.

    Returns:
        Valor entre 0 e 1 (0 se as caixas não se tocam).
    """
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    uniao = area_a + area_b - inter
    return inter / uniao if uniao else 0.0


def carregar_gabarito(caminho: str | Path | None = None) -> dict:
    """Lê o gabarito por quadro.

    Args:
        caminho: JSON do gabarito; por padrão ``data/gold/presenca_quadros.json``.

    Returns:
        O documento: ``casos`` (um por quadro) e ``caixas_revistas`` (rótulos extras).
    """
    alvo = Path(caminho) if caminho else GOLD_QUADROS
    return json.loads(alvo.read_text(encoding="utf-8"))


def caixa_sobre_tablatura(
    caso: dict, rect: list[int] | tuple[int, ...] | None, revistas: list[dict]
) -> bool | None:
    """Rótulo do dono para a caixa que o detector desenhou neste quadro.

    Args:
        caso: um caso do gabarito (``codigo``, ``caixa``, ``caixa_sobre_tablatura``).
        rect: caixa do detector no quadro, ou ``None`` se não desenhou.
        revistas: rótulos extras (``caixas_revistas`` do gabarito).

    Returns:
        ``True``/``False`` se a caixa cobre (ou não) tablatura; ``None`` se não há caixa.

    Raises:
        ValueError: a caixa não bate com a do gabarito nem com um rótulo revisto.
    """
    if rect is None:
        return None
    rotulos: list[tuple[list[int], bool]] = []
    if caso["caixa"] is not None:
        rotulos.append((caso["caixa"], caso["caixa_sobre_tablatura"]))
    rotulos += [
        (r["caixa"], r["caixa_sobre_tablatura"])
        for r in revistas
        if r["codigo"] == caso["codigo"]
    ]
    for caixa, ok in rotulos:
        if iou(list(rect), caixa) >= LIMIAR_IOU_CAIXA:
            return ok
    raise ValueError(
        f"{caso['codigo']}: caixa {list(rect)} sem rótulo no gabarito "
        "(incluir em caixas_revistas depois de olhar o quadro)"
    )


def _metricas_caixa(itens: list[dict]) -> dict:
    """Precisão e revocação de caixa de um conjunto de quadros.

    Args:
        itens: dicts com ``tab`` (há tablatura no quadro) e ``caixa_ok`` (``None`` se
            não há caixa, senão se ela cobre tablatura).

    Returns:
        ``{"caixas", "corretas", "tablatura", "precisao", "revocacao"}``.
    """
    com_caixa = [r for r in itens if r["caixa_ok"] is not None]
    corretas = sum(1 for r in com_caixa if r["caixa_ok"])
    tab = sum(1 for r in itens if r["tab"])
    tab_certas = sum(1 for r in itens if r["tab"] and r["caixa_ok"])
    return {
        "caixas": len(com_caixa),
        "corretas": corretas,
        "tablatura": tab,
        "precisao": _razao(corretas, len(com_caixa)),
        "revocacao": _razao(tab_certas, tab),
    }


def metricas_caixa(resultados: list[dict]) -> dict:
    """Precisão e revocação de caixa, no total e por canal.

    Args:
        resultados: um dict por quadro, com ``canal``, ``tab`` e ``caixa_ok``.

    Returns:
        ``{"total": {...}, "por_canal": {canal: {...}}}``.
    """
    por_canal: dict[str, list[dict]] = {}
    for r in resultados:
        por_canal.setdefault(r["canal"], []).append(r)
    return {
        "total": _metricas_caixa(resultados),
        "por_canal": {c: _metricas_caixa(v) for c, v in sorted(por_canal.items())},
    }


def metricas_presenca(resultados: list[dict]) -> dict:
    """Matriz de presença por quadro (referência; a métrica do produto é a caixa).

    Args:
        resultados: um dict por quadro, com ``tab`` e ``presenca``.

    Returns:
        ``matriz`` de ``classe`` sobre todos os quadros.
    """
    return matriz(
        [
            classe(bool(r["presenca"]), "tablatura" if r["tab"] else "nao_tablatura")
            for r in resultados
        ]
    )


def medir(gabarito: dict, detector=painel_do_quadro) -> tuple[list[dict], list[dict]]:
    """Roda o detector em cada quadro do gabarito e confere a caixa com o rótulo.

    Args:
        gabarito: documento de ``carregar_gabarito``.
        detector: ``quadro -> caixa | None``; por padrão o critério do produto.

    Returns:
        ``(resultados, erros)``: um dict por quadro lido e os quadros sem imagem.
    """
    resultados: list[dict] = []
    erros: list[dict] = []
    raiz = acervo()
    revistas = gabarito.get("caixas_revistas", [])
    for c in gabarito["casos"]:
        quadro = leitor.quadro_em(str(raiz / c["video"]), c["t"])
        if quadro is None:
            erros.append(
                {"codigo": c["codigo"], "video": c["video"], "erro": "sem quadro"}
            )
            continue
        rect = detector(quadro)
        resultados.append(
            {
                "codigo": c["codigo"],
                "canal": c["canal"],
                "video": c["video"],
                "t": c["t"],
                "tab": c["tablatura_no_quadro"],
                "presenca": rect is not None,
                "rect": list(rect) if rect is not None else None,
                "caixa_ok": caixa_sobre_tablatura(c, rect, revistas),
            }
        )
    return resultados, erros


def folha(
    itens: list[tuple[np.ndarray, tuple[int, int, int, int] | None, str]],
    caminho: Path,
    colunas: int = 2,
    largura: int = 960,
) -> Path:
    """Folha de quadros com a caixa do detector e uma legenda por célula.

    Args:
        itens: ``(quadro BGR, caixa do detector ou None, legenda ASCII)``.
        caminho: JPEG de saída.
        colunas: células por linha.
        largura: largura de cada célula, em px.

    Returns:
        O caminho gravado.
    """
    celulas = []
    for quadro, rect, legenda in itens:
        escala = largura / quadro.shape[1]
        img = cv2.resize(quadro, (largura, int(quadro.shape[0] * escala)))
        if rect is not None:
            x0, y0, x1, y1 = (int(v * escala) for v in rect)
            cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), 6)
        cv2.rectangle(img, (0, 0), (largura, 34), (0, 0, 0), -1)
        cv2.putText(
            img, legenda, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2
        )
        celulas.append(img)
    altura = max(c.shape[0] for c in celulas)
    linhas = []
    for k in range(0, len(celulas), colunas):
        linha = []
        for c in celulas[k : k + colunas]:
            pad = np.zeros((altura, largura, 3), dtype=np.uint8)
            pad[: c.shape[0], : c.shape[1]] = c
            linha.append(pad)
        while len(linha) < colunas:
            linha.append(np.zeros((altura, largura, 3), dtype=np.uint8))
        linhas.append(np.hstack(linha))
    cv2.imwrite(str(caminho), np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 80])
    return caminho


def main() -> int:
    """Mede a caixa e a presença contra o gabarito por quadro e grava o resumo."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--gold", default=None, help="gabarito (padrão data/gold/presenca_quadros.json)"
    )
    ap.add_argument("--saida", default=str(SAIDA / "presenca_7_1"))
    args = ap.parse_args()

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    gabarito = carregar_gabarito(args.gold)
    resultados, erros = medir(gabarito)

    caixa = metricas_caixa(resultados)
    presenca = metricas_presenca(resultados)
    erradas = [r for r in resultados if r["caixa_ok"] is False]
    if erradas:
        raiz = acervo()
        itens = []
        for r in erradas:
            quadro = leitor.quadro_em(str(raiz / r["video"]), r["t"])
            legenda = f"{r['codigo']} {r['canal'][:16]} t={r['t']}"
            itens.append((quadro, tuple(r["rect"]), legenda))
        folha(itens, saida / "caixas_erradas.jpg")

    resumo = {
        "gold": args.gold or str(GOLD_QUADROS),
        "quadros_avaliados": len(resultados),
        "erros": erros,
        "caixa": caixa,
        "presenca": presenca,
        "casos": resultados,
    }
    (saida / "resultado.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    t = caixa["total"]
    print(
        f"[caixa] caixas {t['caixas']} corretas {t['corretas']} "
        f"tablatura {t['tablatura']} precisao {t['precisao']} revocacao {t['revocacao']}"
    )
    p = presenca
    print(
        f"[presenca] VP {p['VP']} FP {p['FP']} VN {p['VN']} FN {p['FN']} "
        f"precisao {p['precisao']} revocacao {p['revocacao']}"
    )
    for canal, m in caixa["por_canal"].items():
        print(
            f"  {canal}: caixas {m['caixas']} corretas {m['corretas']} "
            f"precisao {m['precisao']} revocacao {m['revocacao']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
