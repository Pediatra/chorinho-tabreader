"""Desempate por altura, região da mão e F1 por corda para a M7 (item 2 da rodada 1012).

Três perguntas, sem GPU, sobre o que já foi medido na rodada 1011:

1. Quantas notas são ambíguas? Uma nota é ambígua quando a mesma altura existe em mais de
   uma corda, dadas a afinação padrão e a região da mão esquerda (casa real ± raio). A
   corda solta (casa 0) de qualquer candidato sempre conta como possível.
2. Num caso ambíguo, o preditor visual acerta a corda real? O preditor escolhe, entre as
   cordas candidatas, a reta mais próxima da ponta que mais se moveu. Comparado com duas
   bases de desempate que não olham a imagem: a casa mais baixa e a corda mais frequente.
3. F1 por corda: cada ataque são seis decisões sim/não (uma por corda). O preditor dá
   uma corda, a base dá uma corda, e a tablatura dá o conjunto de cordas do ataque.

Uso::

    python -m tab.maos_direita_desempate
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tab.comum.caminhos import MAOS_M7
from tab.comum.violao import AFINACAO_MIDI
from tab.maos.direita.cordas import (
    JANELA_AMPLA,
    _quadro_do_delta,
    corda_mais_frequente,
    corda_mais_proxima,
    preditor_ataque,
    preditor_ataque_pares,
)
from tab.maos.direita.tempo import NOMES
from tab.maos.padroes_preparar import VIDEOS

#: MIDI das cordas soltas, da 1 (mi aguda) à 6 (mi grave), afinação padrão.

#: Maior casa considerada no violão (0 é a corda solta).
CASA_MAX = 19

#: Cenários de ambiguidade: ``None`` quer dizer só altura; um inteiro é o raio em casas.
CENARIOS: tuple[int | None, ...] = (None, 2, 3)

#: Deslocamento, em segundos, do quadro usado pelo preditor da fase B (antes).
DELTA_ANTES = -0.07


def nome_do_cenario(raio: int | None) -> str:
    """Nome curto de um cenário de ambiguidade.

    Args:
        raio: ``None`` (só altura) ou o raio, em casas, da região da mão.

    Returns:
        ``"altura"`` ou ``"altura+-R"``, com R o raio.
    """
    return "altura" if raio is None else f"altura+-{raio}"


def candidatos(
    corda_real: int, casa_real: int, raio: int | None
) -> list[tuple[int, int]]:
    """Cordas em que a mesma altura da nota existe, dentro da região da mão.

    Args:
        corda_real: corda da nota na tablatura (1 a 6).
        casa_real: casa da nota na tablatura (0 a 19).
        raio: ``None`` para só altura; senão, a casa do candidato deve estar a até ``raio``
            casas da casa real. A casa 0 do candidato (corda solta) sempre passa.

    Returns:
        Lista ordenada de pares ``(corda, casa)``. Sempre contém a corda real.
    """
    altura = AFINACAO_MIDI[corda_real] + casa_real
    saida = []
    for corda in sorted(AFINACAO_MIDI):
        casa = altura - AFINACAO_MIDI[corda]
        if not 0 <= casa <= CASA_MAX:
            continue
        if raio is None or casa == 0 or abs(casa - casa_real) <= raio:
            saida.append((corda, casa))
    return saida


def notas_validas(notas: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """Pares ``(corda, casa)`` das notas com casa de 0 a 19 e corda de 1 a 6.

    Args:
        notas: notas do produto (``corda``, ``casa``).

    Returns:
        Lista de pares, na ordem recebida.
    """
    return [
        (int(n["corda"]), int(n["casa"]))
        for n in notas
        if n.get("corda") is not None
        and n.get("casa") is not None
        and 1 <= int(n["corda"]) <= 6
        and 0 <= int(n["casa"]) <= CASA_MAX
    ]


def estatisticas_de_ambiguidade(
    notas: list[dict[str, Any]], raio: int | None
) -> dict[str, Any]:
    """Fração de notas ambíguas e distribuição do nº de candidatos, num cenário.

    Args:
        notas: notas do produto.
        raio: cenário (``None`` ou raio em casas).

    Returns:
        ``{cenario, n_notas, n_ambiguas, fracao_ambiguas, distribuicao}``, com
        ``distribuicao`` um dicionário ``{n_candidatos: quantidade}``.
    """
    pares = notas_validas(notas)
    distribuicao: dict[int, int] = {}
    for corda, casa in pares:
        n = len(candidatos(corda, casa, raio))
        distribuicao[n] = distribuicao.get(n, 0) + 1
    ambiguas = sum(q for n, q in distribuicao.items() if n > 1)
    total = len(pares)
    return {
        "cenario": nome_do_cenario(raio),
        "n_notas": total,
        "n_ambiguas": ambiguas,
        "fracao_ambiguas": round(ambiguas / total, 4) if total else None,
        "distribuicao": {str(k): v for k, v in sorted(distribuicao.items())},
    }


def escolha_visual(
    xy: tuple[float, float],
    cordas: list[dict[str, Any]],
    permitidas: list[int],
) -> int:
    """Corda cuja reta está mais perto do ponto, entre as candidatas.

    Args:
        xy: ponto (ponta da mão) no quadro inteiro.
        cordas: cordas numeradas, com ``a``, ``b``, ``c`` e ``corda``.
        permitidas: números das cordas candidatas (não vazio).

    Returns:
        O número da corda candidata mais próxima.

    Raises:
        ValueError: se ``permitidas`` estiver vazio.
    """
    if not permitidas:
        raise ValueError("escolha_visual precisa de pelo menos uma corda candidata")
    restritas = [c for c in cordas if int(c["corda"]) in permitidas]
    return corda_mais_proxima(xy, restritas)


def escolha_casa_baixa(cands: list[tuple[int, int]]) -> int:
    """Candidata de casa mais baixa (a corda solta conta como casa 0); empate: corda menor.

    Args:
        cands: pares ``(corda, casa)`` candidatos.

    Returns:
        O número da corda escolhida.

    Raises:
        ValueError: se ``cands`` estiver vazio.
    """
    if not cands:
        raise ValueError("escolha_casa_baixa precisa de pelo menos um candidato")
    return min(cands, key=lambda p: (p[1], p[0]))[0]


def escolha_frequente(cands: list[tuple[int, int]], contagem: dict[int, int]) -> int:
    """Candidata mais frequente no produto; empate: corda menor.

    Args:
        cands: pares ``(corda, casa)`` candidatos.
        contagem: quantas notas o produto tem em cada corda.

    Returns:
        O número da corda escolhida.

    Raises:
        ValueError: se ``cands`` estiver vazio.
    """
    if not cands:
        raise ValueError("escolha_frequente precisa de pelo menos um candidato")
    return min(cands, key=lambda p: (-contagem.get(p[0], 0), p[0]))[0]


def contagem_por_corda(notas: list[dict[str, Any]]) -> dict[int, int]:
    """Quantas notas do produto há em cada corda.

    Args:
        notas: notas do produto (``corda``).

    Returns:
        Dicionário ``{corda: quantidade}``.
    """
    contagem: dict[int, int] = {}
    for corda, _casa in notas_validas(notas):
        contagem[corda] = contagem.get(corda, 0) + 1
    return contagem


def ponto_do_preditor(
    ataque: dict[str, Any], cordas: list[dict[str, Any]], depois: bool
) -> dict[str, Any] | None:
    """Ponta e quadro que o preditor usa, e a corda que ele daria.

    Antes: a ponta que mais se move entre -0,13 e +0,07 s, no quadro de -0,07 s. Depois:
    a ponta que mais se move nos pares de quadros da janela deslocada, no quadro anterior ao
    maior salto (``tab.maos_direita_cordas.preditor_ataque_pares``).

    Args:
        ataque: ataque de ``registrar_ataque`` (trajetórias).
        cordas: cordas numeradas da mesma medição.
        depois: ``True`` para a janela deslocada.

    Returns:
        ``{dedo, xy, corda_prevista}``, ou None se o preditor não tem a mão.
    """
    if depois:
        pred = preditor_ataque_pares(ataque, cordas, JANELA_AMPLA)
        if pred is None:
            return None
        delta = pred["delta_antes"]
    else:
        pred = preditor_ataque(ataque, cordas)
        if pred is None:
            return None
        delta = DELTA_ANTES
    quadro = _quadro_do_delta(ataque, delta)
    if quadro is None or quadro.get("direita") is None:
        return None
    dedo = int(pred["dedo"])
    xy = tuple(float(v) for v in quadro["direita"]["pts"][dedo])
    return {"dedo": dedo, "xy": xy, "corda_prevista": int(pred["corda_prevista"])}


def avaliar_desempate(
    ataques: list[dict[str, Any]],
    cordas: list[dict[str, Any]],
    contagem: dict[int, int],
    depois: bool,
) -> dict[str, dict[str, Any]]:
    """Acerto, em notas ambíguas, do visual e das duas bases, por cenário.

    Só entram as notas do ataque cujas candidatas têm mais de uma corda. Cada nota conta
    uma vez: a corda prevista é a escolha visual restrita às candidatas, e a corda real é a
    da tablatura do ataque.

    Args:
        ataques: ataques com ``cordas_tab`` e ``quadros``.
        cordas: cordas numeradas da medição.
        contagem: notas por corda do produto (base "mais frequente").
        depois: janela deslocada (``True``) ou fase B antes (``False``).

    Returns:
        ``{cenario: {ataques_avaliados, notas_ambiguas, visual, casa_baixa, frequente}}``,
        em que cada acerto é a contagem de notas ambíguas em que a escolha bate com a real.
    """
    saida: dict[str, dict[str, Any]] = {}
    previsoes = []
    for ataque in ataques:
        pt = ponto_do_preditor(ataque, cordas, depois)
        if pt is not None:
            previsoes.append((ataque, pt))
    for raio in CENARIOS:
        nome = nome_do_cenario(raio)
        ambiguas = visual = baixa = freq = 0
        for ataque, pt in previsoes:
            for corda_real, casa_real in {
                (int(c["corda"]), int(c["casa"])) for c in ataque["cordas_tab"]
            }:
                cands = candidatos(corda_real, casa_real, raio)
                if len(cands) < 2:
                    continue
                ambiguas += 1
                nums = [c for c, _ in cands]
                visual += escolha_visual(pt["xy"], cordas, nums) == corda_real
                baixa += escolha_casa_baixa(cands) == corda_real
                freq += escolha_frequente(cands, contagem) == corda_real
        saida[nome] = {
            "ataques_avaliados": len(previsoes),
            "notas_ambiguas": ambiguas,
            "visual": visual,
            "casa_baixa": baixa,
            "frequente": freq,
        }
    return saida


def contar_f1(
    verdade: list[set[int]], previstas: list[set[int]]
) -> dict[str, dict[str, float | int | None]]:
    """Precisão, revocação e F1 por corda, e micro, a partir de conjuntos por ataque.

    Args:
        verdade: para cada ataque, o conjunto das cordas da tablatura.
        previstas: para cada ataque, o conjunto das cordas previstas (mesma ordem).

    Returns:
        ``{"1".."6": {tp, fp, fn, precisao, revocacao, f1}, "micro": {...}}``. Precisão,
        revocação e F1 são None quando o denominador é zero.
    """
    tabela: dict[str, dict[str, float | int | None]] = {}
    tot = {"tp": 0, "fp": 0, "fn": 0}
    for corda in sorted(AFINACAO_MIDI):
        tp = fp = fn = 0
        for real, prev in zip(verdade, previstas, strict=True):
            r, p = corda in real, corda in prev
            tp += r and p
            fp += (not r) and p
            fn += r and (not p)
        tabela[str(corda)] = _metricas(tp, fp, fn)
        tot["tp"] += tp
        tot["fp"] += fp
        tot["fn"] += fn
    tabela["micro"] = _metricas(tot["tp"], tot["fp"], tot["fn"])
    return tabela


def _metricas(tp: int, fp: int, fn: int) -> dict[str, float | int | None]:
    """Precisão, revocação e F1 de contagens TP, FP e FN.

    Args:
        tp: verdadeiros positivos.
        fp: falsos positivos.
        fn: falsos negativos.

    Returns:
        ``{tp, fp, fn, precisao, revocacao, f1}``, com None onde o denominador é zero.
    """
    precisao = tp / (tp + fp) if tp + fp else None
    revocacao = tp / (tp + fn) if tp + fn else None
    if precisao is None or revocacao is None or precisao + revocacao == 0:
        f1 = None
    else:
        f1 = 2 * precisao * revocacao / (precisao + revocacao)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precisao": _r(precisao),
        "revocacao": _r(revocacao),
        "f1": _r(f1),
    }


def _r(valor: float | None) -> float | None:
    """Arredonda a 4 casas, mantendo None.

    Args:
        valor: número ou None.

    Returns:
        ``round(valor, 4)`` ou None.
    """
    return None if valor is None else round(float(valor), 4)


def _carregar(caminho: Path) -> dict[str, Any]:
    """Lê um JSON do disco.

    Args:
        caminho: arquivo JSON.

    Returns:
        O conteúdo decodificado.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def _log(msg: str) -> None:
    """Progresso no stderr.

    Args:
        msg: texto da linha.
    """
    print(msg, file=sys.stderr, flush=True)


def main() -> None:
    """Avalia os 4 vídeos (antes e depois), grava ``desempate.json`` e imprime o resumo."""
    saida: dict[str, Any] = {
        "afinacao_midi": AFINACAO_MIDI,
        "cenarios": [nome_do_cenario(r) for r in CENARIOS],
        "ambiguidade": {},
        "desempate": {"antes": {}, "depois": {}},
        "f1": {"antes": {}, "depois": {}, "base": {}},
    }
    total: dict[str, list[list[set[int]]]] = {
        "antes": [[], []],
        "depois": [[], []],
        "base": [[], []],
    }
    for indice, video in enumerate(VIDEOS):
        nome = NOMES[indice]
        produto = _carregar(Path(video["produto"]))
        notas = produto["notas"]
        saida["ambiguidade"][nome] = {
            nome_do_cenario(r): estatisticas_de_ambiguidade(notas, r) for r in CENARIOS
        }
        contagem = contagem_por_corda(notas)
        fases = {
            "antes": _carregar(MAOS_M7 / f"trajetorias_{nome}.json"),
            "depois": _carregar(MAOS_M7 / f"trajetorias_depois_{nome}.json"),
        }
        instantes = [round(float(a["t_ini"]), 3) for a in fases["antes"]["ataques"]]
        base_corda = corda_mais_frequente(notas, instantes)
        base_v: list[set[int]] = []
        base_p: list[set[int]] = []
        for fase, dados in fases.items():
            cordas_fase = dados["cordas"]
            ataques = dados["ataques"]
            _log(f"{nome} {fase}: {len(ataques)} ataques")
            saida["desempate"][fase][nome] = avaliar_desempate(
                ataques, cordas_fase, contagem, depois=(fase == "depois")
            )
            verdades: list[set[int]] = []
            previstas: list[set[int]] = []
            for ataque in ataques:
                pt = ponto_do_preditor(ataque, cordas_fase, fase == "depois")
                if pt is None:
                    continue
                verdade = {int(c["corda"]) for c in ataque["cordas_tab"]}
                verdades.append(verdade)
                previstas.append({pt["corda_prevista"]})
                if fase == "antes":
                    base_v.append(verdade)
                    base_p.append({base_corda} if base_corda is not None else set())
            saida["f1"][fase][nome] = contar_f1(verdades, previstas)
            total[fase][0].extend(verdades)
            total[fase][1].extend(previstas)
        saida["f1"]["base"][nome] = contar_f1(base_v, base_p)
        total["base"][0].extend(base_v)
        total["base"][1].extend(base_p)
    for fase in ("antes", "depois", "base"):
        saida["f1"][fase]["total"] = contar_f1(total[fase][0], total[fase][1])
    MAOS_M7.mkdir(parents=True, exist_ok=True)
    (MAOS_M7 / "desempate.json").write_text(
        json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    for fase in ("antes", "depois", "base"):
        micro = saida["f1"][fase]["total"]["micro"]
        n_cel = micro["tp"] + micro["fn"]
        print(f"{fase}: celulas_verdade={n_cel} micro={json.dumps(micro)}")


if __name__ == "__main__":
    main()
