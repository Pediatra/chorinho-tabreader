"""Regra do dedo da mão direita por compasso tocado (M5): palpite sem visão.

Fase M5 da trilha das mãos (``docs/decisoes/1004-m5-padroes-da-mao-direita.md``). A regra
é a do dono, para dedilhado (90% das músicas): o polegar (``p``) toca as cordas 6, 5 e 4;
o indicador (``i``) a corda 3; o médio (``m``) a 2; o anelar (``a``) a 1. Quatro regras,
nesta ordem, cada uma podendo trocar o dedo da anterior:

1. padrão da corda: 6, 5 e 4 → ``p``; 3 → ``i``; 2 → ``m``; 1 → ``a``;
2. exceção do bordão: corda 4 com polegar nas cordas 5 ou 6 no mesmo ataque, ou no
   ataque seguinte se vier em até ``JANELA_POLEGAR_S`` → ``i``;
3. acorde (dois ou mais dedos fora do polegar): as notas fora do polegar, da corda mais
   grave para a mais aguda, recebem ``i``, ``m``, ``a`` em ordem;
4. sequência melódica (ataques de uma nota fora do polegar, até
   ``JANELA_SEQUENCIA_S`` um do outro, ignorando ataques só de polegar): na mesma corda
   ou numa mais aguda, o dedo é o seguinte ao anterior (i → m → a); ao passar de ``a``
   reinicia no padrão da corda; numa corda mais grave, usa o padrão. Com
   ``alternar_ma``, a mesma corda depois de ``a`` dá ``m`` (I-M-A-M-A).

Em toda regra o dedo nunca fica abaixo do padrão da corda (na ordem i < m < a), salvo
a alternância m-a da regra 4.

Versão atual: v2 (janelas de 1,0 s e alternância ligada). A v2 foi medida na rodada 1010
(``docs/rodadas/1010-m5-regra-da-direita-contra-o-dono.md``): 171/199 fora da amostra,
contra 154/199 da v1. A v1 é a que o dono viu e confirmou nos compassos ímpares.

Funções puras: a regra só lê corda e tempo. A casa vai na saída para o dono conferir,
mas não entra na decisão.

Uso::

    from tab.maos.regra_direita import atribuir_dedos_direita
    atribuir_dedos_direita([{"corda": 3, "casa": 4, "t_ini": 1.0}])
"""

from __future__ import annotations

#: Dedo padrão de cada corda (regra 1).
PADRAO_POR_CORDA: dict[int, str] = {6: "p", 5: "p", 4: "p", 3: "i", 2: "m", 1: "a"}

#: Dedos da mão direita fora do polegar, na ordem em que a sequência anda.
ORDEM_DEDOS: tuple[str, ...] = ("i", "m", "a")

#: Notas com tempo a menos disto de diferença são o mesmo ataque (acorde).
TOLERANCIA_ATAQUE_S = 0.02

#: Polegar ainda ocupado: a corda 4 logo depois de um bordão (5 ou 6) usa ``i``.
JANELA_POLEGAR_S = 1.0

#: Ataques de uma nota fora do polegar, até este intervalo um do outro, formam sequência.
JANELA_SEQUENCIA_S = 1.0

#: Regra v1, a que o dono viu nos compassos ímpares (rodada 1010, referência).
V1_JANELA_POLEGAR_S = 0.25
V1_JANELA_SEQUENCIA_S = 0.6
V1_ALTERNAR_MA = False

#: Alternância m-a na sequência (I-M-A-M-A), ligada na v2.
ALTERNAR_MA_PADRAO = True

#: Folga para comparar tempos em ponto flutuante.
_EPS = 1e-9

_CORDAS_BORDAO = (5, 6)
_CORDA_EXCECAO = 4

REGRA_PADRAO = "padrão da corda"
REGRA_EXCECAO = "exceção do bordão: corda 4 com polegar em 5/6"
REGRA_ACORDE = "acorde: dedos em sequência, da corda mais grave"
REGRA_ACORDE_INSUFICIENTE = "acorde: dedos insuficientes, padrão da corda"
REGRA_SEQUENCIA = "sequência: seguinte ao anterior (i-m-a)"
REGRA_SEQUENCIA_REINICIA = "sequência: passou de a, reinicia no padrão"
REGRA_SEQUENCIA_ACIMA = "sequência: padrão da corda, acima do seguinte"
REGRA_SEQUENCIA_GRAVE = "sequência: corda mais grave, padrão da corda"
REGRA_SEQUENCIA_ALTERNA = "sequência: mesma corda depois de a, alterna m-a"


def _padrao_sem_polegar(corda: int) -> str:
    """Padrão da corda para uma nota fora do polegar (corda 4 vira ``i``).

    Args:
        corda: número da corda (1 a 6).

    Returns:
        ``i``, ``m`` ou ``a``. Corda 4 cai em ``i``: é a exceção do bordão.
    """
    padrao = PADRAO_POR_CORDA[corda]
    return "i" if padrao == "p" else padrao


def _agrupar_ataques(notas: list[dict]) -> list[list[int]]:
    """Agrupa notas já ordenadas por ``t_ini`` em ataques.

    Args:
        notas: notas ordenadas por ``t_ini``.

    Returns:
        Lista de ataques; cada ataque é a lista dos índices das notas dele.
    """
    ataques: list[list[int]] = []
    for i, nota in enumerate(notas):
        if ataques:
            ancora = notas[ataques[-1][0]]["t_ini"]
            if nota["t_ini"] - ancora <= TOLERANCIA_ATAQUE_S + _EPS:
                ataques[-1].append(i)
                continue
        ataques.append([i])
    return ataques


def _tempo_do_ataque(notas: list[dict], ataque: list[int]) -> float:
    """Tempo de um ataque (o da primeira nota dele).

    Args:
        notas: notas ordenadas.
        ataque: índices das notas do ataque.

    Returns:
        ``t_ini`` do ataque, em segundos.
    """
    return notas[ataque[0]]["t_ini"]


def _tem_bordao(notas: list[dict], ataque: list[int]) -> bool:
    """Se o ataque tem nota nas cordas 5 ou 6 (polegar).

    Args:
        notas: notas ordenadas.
        ataque: índices das notas do ataque.

    Returns:
        True se alguma nota do ataque está na corda 5 ou 6.
    """
    return any(notas[i]["corda"] in _CORDAS_BORDAO for i in ataque)


def _aplicar_excecao_bordao(
    notas: list[dict],
    ataques: list[list[int]],
    dedo: list[str],
    regra: list[str],
    janela_polegar_s: float = JANELA_POLEGAR_S,
) -> None:
    """Regra 2: corda 4 com polegar em 5/6 no mesmo ataque ou logo antes usa ``i``.

    Args:
        notas: notas ordenadas.
        ataques: ataques (índices) de ``notas``.
        dedo: dedos atuais, alterados em lugar.
        regra: textos das regras, alterados em lugar.
        janela_polegar_s: até quantos segundos depois de um ataque com polegar em 5/6
            a corda 4 ainda usa ``i``.
    """
    for k, ataque in enumerate(ataques):
        bordao_antes = False
        if k > 0:
            gap = _tempo_do_ataque(notas, ataque) - _tempo_do_ataque(
                notas, ataques[k - 1]
            )
            bordao_antes = gap <= janela_polegar_s + _EPS and _tem_bordao(
                notas, ataques[k - 1]
            )
        for i in ataque:
            if notas[i]["corda"] != _CORDA_EXCECAO:
                continue
            if bordao_antes or _tem_bordao(notas, ataque):
                dedo[i] = "i"
                regra[i] = REGRA_EXCECAO


def _aplicar_acordes(
    notas: list[dict], ataques: list[list[int]], dedo: list[str], regra: list[str]
) -> None:
    """Regra 3: num ataque com dois ou mais dedos fora do polegar, dá i, m, a em ordem.

    As notas fora do polegar entram da corda mais grave para a mais aguda, e a
    sequência começa no padrão da mais grave. Nunca fica abaixo do padrão da própria
    corda. Notas que sobram além de ``a`` ficam com o padrão e dizem isso na regra.

    Args:
        notas: notas ordenadas.
        ataques: ataques (índices) de ``notas``.
        dedo: dedos atuais, alterados em lugar.
        regra: textos das regras, alterados em lugar.
    """
    for ataque in ataques:
        fora = [i for i in ataque if dedo[i] != "p"]
        if len(fora) < 2:
            continue
        fora.sort(key=lambda i: -notas[i]["corda"])
        inicio = ORDEM_DEDOS.index(_padrao_sem_polegar(notas[fora[0]]["corda"]))
        for n, i in enumerate(fora):
            padrao = _padrao_sem_polegar(notas[i]["corda"])
            if inicio + n >= len(ORDEM_DEDOS):
                dedo[i] = padrao
                regra[i] = REGRA_ACORDE_INSUFICIENTE
                continue
            pos = max(inicio + n, ORDEM_DEDOS.index(padrao))
            dedo[i] = ORDEM_DEDOS[pos]
            regra[i] = REGRA_ACORDE


def _proximo_dedo(dedo: str) -> str | None:
    """Dedo seguinte na ordem i → m → a.

    Args:
        dedo: ``i``, ``m`` ou ``a``.

    Returns:
        O seguinte, ou ``None`` depois de ``a``.
    """
    pos = ORDEM_DEDOS.index(dedo)
    return ORDEM_DEDOS[pos + 1] if pos + 1 < len(ORDEM_DEDOS) else None


def _aplicar_sequencia(
    notas: list[dict],
    ataques: list[list[int]],
    dedo: list[str],
    regra: list[str],
    janela_sequencia_s: float = JANELA_SEQUENCIA_S,
    alternar_ma: bool = ALTERNAR_MA_PADRAO,
) -> None:
    """Regra 4: sequência de ataques de uma nota fora do polegar.

    Um ataque só de polegar é ignorado (não quebra a sequência). Um acorde a zera.
    Com ``alternar_ma``, depois de ``a`` na MESMA corda vem ``m`` (I-M-A-M-A), e essa
    alternância é a única exceção à ordem i < m < a (inclusive na corda 1, onde dá ``m``
    abaixo do padrão). Numa corda diferente vale a regra normal.

    Args:
        notas: notas ordenadas.
        ataques: ataques (índices) de ``notas``.
        dedo: dedos atuais, alterados em lugar.
        regra: textos das regras, alterados em lugar.
        janela_sequencia_s: intervalo máximo, em segundos, entre dois ataques de uma
            nota fora do polegar para formarem sequência.
        alternar_ma: se True, a mesma corda repetida depois de ``a`` alterna ``m``/``a``.
    """
    anterior: dict | None = None
    for ataque in ataques:
        fora = [i for i in ataque if dedo[i] != "p"]
        if not fora:
            continue
        if len(fora) > 1:
            anterior = None
            continue
        i = fora[0]
        corda = notas[i]["corda"]
        tempo = _tempo_do_ataque(notas, ataque)
        if anterior is not None and (
            tempo - anterior["tempo"] <= janela_sequencia_s + _EPS
        ):
            padrao = _padrao_sem_polegar(corda)
            if corda > anterior["corda"]:
                dedo[i] = padrao
                regra[i] = REGRA_SEQUENCIA_GRAVE
            elif alternar_ma and corda == anterior["corda"] and anterior["dedo"] == "a":
                dedo[i] = "m"
                regra[i] = REGRA_SEQUENCIA_ALTERNA
            else:
                seguinte = _proximo_dedo(anterior["dedo"])
                if seguinte is None:
                    dedo[i] = padrao
                    regra[i] = REGRA_SEQUENCIA_REINICIA
                elif ORDEM_DEDOS.index(seguinte) >= ORDEM_DEDOS.index(padrao):
                    dedo[i] = seguinte
                    regra[i] = REGRA_SEQUENCIA
                else:
                    dedo[i] = padrao
                    regra[i] = REGRA_SEQUENCIA_ACIMA
        anterior = {"corda": corda, "dedo": dedo[i], "tempo": tempo}


def atribuir_dedos_direita(
    notas: list[dict],
    *,
    janela_polegar_s: float = JANELA_POLEGAR_S,
    janela_sequencia_s: float = JANELA_SEQUENCIA_S,
    alternar_ma: bool = ALTERNAR_MA_PADRAO,
) -> list[dict]:
    """Palpite do dedo da mão direita para cada nota de um compasso tocado.

    Os parâmetros opcionais existem para medir variantes contra o gabarito. O default
    de cada um é a regra de produção; sem eles a saída é a mesma de sempre.

    Args:
        notas: notas do compasso, cada uma com ``corda`` (1 a 6), ``casa`` e
            ``t_ini`` (segundos). Campos extras são preservados na saída.
        janela_polegar_s: até quantos segundos depois de um ataque com polegar em 5/6
            a corda 4 usa ``i`` (regra 2).
        janela_sequencia_s: intervalo máximo, em segundos, entre dois ataques de uma
            nota fora do polegar para formarem sequência (regra 4).
        alternar_ma: se True, na sequência a mesma corda depois de ``a`` dá ``m``
            (I-M-A-M-A). Numa corda diferente segue a regra normal.

    Returns:
        Cópias das notas, na ordem de ``t_ini``, cada uma com ``dedo`` (``p``, ``i``,
        ``m`` ou ``a``) e ``regra`` (texto curto de qual regra decidiu).

    Raises:
        ValueError: se alguma nota tiver corda fora de 1 a 6.
    """
    for nota in notas:
        if nota["corda"] not in PADRAO_POR_CORDA:
            raise ValueError(f"corda inválida: {nota['corda']!r}")
    ordenadas = sorted(notas, key=lambda n: n["t_ini"])
    ataques = _agrupar_ataques(ordenadas)
    dedo = [PADRAO_POR_CORDA[n["corda"]] for n in ordenadas]
    regra = [REGRA_PADRAO] * len(ordenadas)
    _aplicar_excecao_bordao(ordenadas, ataques, dedo, regra, janela_polegar_s)
    _aplicar_acordes(ordenadas, ataques, dedo, regra)
    _aplicar_sequencia(
        ordenadas,
        ataques,
        dedo,
        regra,
        janela_sequencia_s=janela_sequencia_s,
        alternar_ma=alternar_ma,
    )
    return [
        {**nota, "dedo": d, "regra": r}
        for nota, d, r in zip(ordenadas, dedo, regra, strict=True)
    ]
