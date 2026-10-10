"""Erro de PRESENÇA do detector que o produto usa, medido no ``portao.json``.

Medição (Fase 7.0): **não muda o detector**. Para cada caso rotulado no olho (fora os
``duvida``), lê o quadro INTEIRO no instante ``instante_frac * duração`` (via
``tab.leitor``) e roda ``tab.telas.painel_do_quadro`` — o mesmo critério que ``tab.telas``
usa para dizer "há tablatura neste quadro". Compara com o rótulo e conta a matriz de
confusão, total e por canal. Como a presença é o que vira nota, o FALSO POSITIVO é o erro
que importa aqui (nota inventada).

O portão aprendido (``tab.portao``) é medido nos mesmos casos só para comparação. Ele
NÃO é o usado pelo produto. Também foi treinado nestes casos, então o número dele é
dentro da amostra (otimista).

Uso:
    python -m tab.presenca_aval --saida data/saida/presenca
    python -m tab.presenca_aval --tipos data/saida/presenca/tipos_fp.json --sem-portao
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from . import leitor, portao
from .caminhos import ARTEFATOS, SAIDA, acervo
from .painel import escolher
from .telas import painel_do_quadro

#: Limiar de probabilidade do portão aprendido (mesmo de ``tab.portao.avaliar``).
LIMIAR_PORTAO = 0.5

#: Modelo do portão aprendido comparado (config vencedora da rodada 0002: ``--seed 1``).
PORTAO_PADRAO = ARTEFATOS / "portao_real_1" / "portao.pt"


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


def resumir(resultados: list[dict], campo: str) -> dict:
    """Matriz total e por canal para uma das previsões (``presenca`` ou ``portao``).

    Args:
        resultados: um dict por caso, com ``canal``, ``rotulo`` e o campo de previsão.
        campo: chave booleana do dict que é a previsão.

    Returns:
        ``{"total": matriz, "por_canal": {canal: matriz}}``.
    """
    por_canal: dict[str, list[str | None]] = {}
    todas: list[str | None] = []
    for r in resultados:
        cl = classe(bool(r[campo]), r["rotulo"])
        todas.append(cl)
        por_canal.setdefault(r["canal"], []).append(cl)
    return {
        "total": matriz(todas),
        "por_canal": {canal: matriz(v) for canal, v in sorted(por_canal.items())},
    }


def por_quadro(resultados: list[dict], campo: str) -> dict:
    """Matriz no nível do QUADRO: um quadro conta uma vez, mesmo com vários recortes.

    O detector responde por quadro inteiro. Um quadro tem verdade ``tablatura`` se algum
    recorte dele foi rotulado ``tablatura`` (a tablatura está em outra faixa); é
    ``nao_tablatura`` se só há recortes ``nao_tablatura``. Os recortes ``nao_tablatura``
    são só as faixas que o dono olhou: o quadro pode ter tablatura numa faixa que
    ninguém rotulou (ver a nota no ESTADO.md).

    Args:
        resultados: um dict por caso, com ``video``, ``t_s``, ``canal``, ``rotulo`` e o campo.
        campo: chave booleana da previsão (a mesma em todos os recortes do quadro).

    Returns:
        ``{"total": matriz, "por_canal": {canal: matriz}, "quadros": n}``.
    """
    grupos: dict[tuple[str, float], list[dict]] = {}
    for r in resultados:
        grupos.setdefault((r["video"], r["t_s"]), []).append(r)
    rotulos: list[tuple[str, str | None]] = []
    por_canal: dict[str, list[str | None]] = {}
    for (_video, _t), v in grupos.items():
        verdade = (
            "tablatura"
            if any(x["rotulo"] == "tablatura" for x in v)
            else "nao_tablatura"
        )
        cl = classe(bool(v[0][campo]), verdade)
        rotulos.append((v[0]["canal"], cl))
        por_canal.setdefault(v[0]["canal"], []).append(cl)
    return {
        "total": matriz([cl for _, cl in rotulos]),
        "por_canal": {c: matriz(v) for c, v in sorted(por_canal.items())},
        "quadros": len(grupos),
    }


def fps_quadros(resultados: list[dict], campo: str) -> list[dict]:
    """Os quadros FP (um recorte por quadro), pelo critério de ``por_quadro``.

    Args:
        resultados: um dict por caso.
        campo: chave booleana da previsão.

    Returns:
        Um dict por quadro com previsão positiva e nenhum recorte ``tablatura``.
    """
    tablatura = {
        (r["video"], r["t_s"]) for r in resultados if r["rotulo"] == "tablatura"
    }
    return [
        r
        for r in _unicos(resultados)
        if r[campo] and (r["video"], r["t_s"]) not in tablatura
    ]


def fps(resultados: list[dict], campo: str) -> list[dict]:
    """Os falsos positivos de uma previsão, na ordem do gabarito.

    Args:
        resultados: um dict por caso.
        campo: chave booleana da previsão.

    Returns:
        Os casos com previsão positiva e rótulo ``nao_tablatura``.
    """
    return [r for r in resultados if classe(bool(r[campo]), r["rotulo"]) == "FP"]


def folha(
    itens: list[tuple[np.ndarray, tuple[int, int, int, int] | None, str]],
    caminho: Path,
    colunas: int = 4,
    largura: int = 480,
) -> Path:
    """Folha de quadros com a caixa do painel detectado e uma legenda por célula.

    Args:
        itens: ``(quadro BGR, retângulo do detector ou None, legenda ASCII)``.
        caminho: PNG de saída.
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
            cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), 3)
        cv2.rectangle(img, (0, 0), (largura, 22), (0, 0, 0), -1)
        cv2.putText(
            img, legenda, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
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
    cv2.imwrite(str(caminho), np.vstack(linhas))
    return caminho


def _quadro(video: Path, frac: float) -> tuple[np.ndarray | None, float]:
    """Quadro inteiro no instante ``frac`` da duração, e esse instante em segundos."""
    dur = float(leitor.info(str(video)).get("duracao_s") or 0.0)
    t = frac * dur
    return leitor.quadro_em(str(video), t), t


def medir(
    casos: list[dict], modelo_portao: tuple | None
) -> tuple[list[dict], list[dict]]:
    """Roda o detector de presença (e o portão, se houver) em cada caso.

    Args:
        casos: casos do gabarito, já sem ``duvida``.
        modelo_portao: ``(modelo, dispositivo)`` do ``tab.portao`` ou ``None``.

    Returns:
        ``(resultados, erros)``: um dict por caso lido e os casos sem quadro.
    """
    resultados: list[dict] = []
    erros: list[dict] = []
    raiz = acervo()
    for c in casos:
        quadro, t = _quadro(raiz / c["video"], c["instante_frac"])
        if quadro is None:
            erros.append(
                {"arquivo": c["arquivo"], "video": c["video"], "erro": "sem quadro"}
            )
            continue
        rect = painel_do_quadro(quadro)
        cand = escolher(quadro)
        r = {
            "arquivo": c["arquivo"],
            "canal": c["canal"],
            "video": c["video"],
            "instante_frac": c["instante_frac"],
            "t_s": round(t, 2),
            "rotulo": c["rotulo"],
            "faixa_gold": c["faixa"],
            "presenca": rect is not None,
            "rect": list(rect) if rect is not None else None,
            "faixa_det": cand.nome if cand is not None else None,
            "passo_det": round(cand.passo, 1) if cand is not None else None,
        }
        if modelo_portao is not None:
            modelo, dev = modelo_portao
            if cand is None:
                r["p_portao"] = None
                r["portao"] = False
            else:
                p = float(portao.probabilidade([cand.roi], modelo, dev)[0])
                r["p_portao"] = round(p, 3)
                r["portao"] = p >= LIMIAR_PORTAO
        resultados.append(r)
    return resultados, erros


def _unicos(resultados: list[dict]) -> list[dict]:
    """Um recorte por quadro (``video``, ``t_s``), na ordem do gabarito."""
    vistos: set[tuple[str, float]] = set()
    saida: list[dict] = []
    for r in resultados:
        chave = (r["video"], r["t_s"])
        if chave not in vistos:
            vistos.add(chave)
            saida.append(r)
    return saida


def main() -> int:
    """Mede a presença do ``tab.telas`` contra o ``portao.json`` e grava a folha de FPs."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--gold", default=None, help="gabarito (padrão data/gold/portao.json)"
    )
    ap.add_argument("--saida", default=str(SAIDA / "presenca"))
    ap.add_argument("--portao", default=str(PORTAO_PADRAO), help="'' para pular")
    ap.add_argument("--sem-portao", action="store_true")
    ap.add_argument("--tipos", default=None, help="JSON {arquivo: tipo} para a legenda")
    ap.add_argument(
        "--tps", type=int, default=10, help="verdadeiros positivos na folha"
    )
    args = ap.parse_args()

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    gold = portao.carregar_gold(args.gold)
    casos = [c for c in gold["casos"] if c["rotulo"] != "duvida"]
    duvidas = len(gold["casos"]) - len(casos)

    modelo_portao = None
    if not args.sem_portao and args.portao:
        modelo_portao = portao.carregar_modelo(args.portao)

    resultados, erros = medir(casos, modelo_portao)
    campos = ["presenca"] + (["portao"] if modelo_portao is not None else [])
    resumo = {campo: resumir(resultados, campo) for campo in campos}
    tipos = (
        json.loads(Path(args.tipos).read_text(encoding="utf-8")) if args.tipos else {}
    )

    fp_presenca = fps(resultados, "presenca")
    tp_presenca = [
        r for r in resultados if classe(bool(r["presenca"]), r["rotulo"]) == "VP"
    ]
    quadros_fp = fps_quadros(resultados, "presenca")
    quadros_vp = _unicos(tp_presenca)
    escolhidos: list[dict] = []
    if quadros_vp and args.tps > 0:
        idx = np.linspace(0, len(quadros_vp) - 1, min(args.tps, len(quadros_vp)))
        escolhidos = [quadros_vp[round(float(i))] for i in idx]

    folhas: dict[str, list[str]] = {"fp": [], "vp": []}
    for sigla, lista in (("fp", quadros_fp), ("vp", escolhidos)):
        for n, k in enumerate(range(0, len(lista), 12), 1):
            itens = []
            for j, r in enumerate(lista[k : k + 12], 1):
                quadro, _ = _quadro(acervo() / r["video"], r["instante_frac"])
                legenda = f"{sigla.upper()}{k + j:02d} {r['canal'][:14]} t={r['t_s']}s"
                itens.append((quadro, tuple(r["rect"]) if r["rect"] else None, legenda))
            caminho = saida / f"{sigla}_presenca_{n}.png"
            folhas[sigla].append(str(folha(itens, caminho, colunas=4, largura=480)))

    for r in resultados:
        r["tipo"] = tipos.get(r["arquivo"])
    resumo_quadro = {campo: por_quadro(resultados, campo) for campo in campos}

    saida_json = {
        "gold": args.gold or str(portao.GOLD_PORTAO),
        "portao": args.portao if modelo_portao is not None else None,
        "limiar_portao": LIMIAR_PORTAO,
        "casos_avaliados": len(resultados),
        "duvidas_excluidas": duvidas,
        "erros": erros,
        "resumo": resumo,
        "resumo_por_quadro": resumo_quadro,
        "falsos_positivos_presenca_quadros": quadros_fp,
        "falsos_positivos_presenca_casos": fp_presenca,
        "folhas": folhas,
        "casos": resultados,
    }
    (saida / "resultado.json").write_text(
        json.dumps(saida_json, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )

    for campo in campos:
        t = resumo[campo]["total"]
        print(
            f"[{campo}] VP {t['VP']} FP {t['FP']} VN {t['VN']} FN {t['FN']} "
            f"precisao {t['precisao']} revocacao {t['revocacao']}"
        )
    print(
        f"casos avaliados {len(resultados)}, duvidas excluidas {duvidas}, sem quadro {len(erros)}"
    )
    print(f"folhas: {folhas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
