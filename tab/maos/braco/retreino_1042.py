"""Rodada 1042: retreino do braço com as marcas da 1039 e veto de inversão na escolha.

A receita é a da 1041 (``tab.maos.braco.retreino_capo3``): as fontes da 1037, o capo
sorteado ``FATOR_CAPO`` vezes nos dois estágios e a escolha com piso de certos. Mudam:

- **fonte nova**: os 64 quadros da 1039 (``M39``, capo nas casas 2 a 5), como fonte do dono;
- **barreira**: nenhum quadro de um vídeo do lote da 1043 entra no treino (a prova);
- **veto de inversão**: na M36 (vídeos verticais), o par não pode inverter o braço em mais
  quadros que o par antigo;
- **critério 3** só no N, porque a M36 passa a ser folha de escolha.

Pré-registro: ``docs/rodadas/1042-retreino-com-a-1039.md``.

CLI: ``python -m tab.maos.braco.retreino_1042
{contar,smoke,treinar,escolher,medir-dev,prever-prova,medir-prova}``.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from tab.comum.arquivos import gravar_atomico, nfc
from tab.comum.caminhos import (
    GABARITO_BRACO_M36,
    GABARITO_BRACO_M39,
    GABARITO_BRACO_M43,
    MAOS_M36,
    MAOS_M39,
    MAOS_M42,
    MAOS_M43,
)
from tab.maos.braco.ciclo import (
    ARQUIVO_INDICE,
    avaliar_combinacao,
    escolher_combinacao,
    pesos_da_rodada,
)
from tab.maos.braco.detector import PASSOS, _ler_json
from tab.maos.braco.retreino import (
    CONJUNTOS_MEDIDA,
    EXCLUIDOS,
    RODADA_REFERENCIA,
    SEMENTES,
    _contagem,
    _gabaritos_por_origem,
    _peso_existe,
    _prever_conjunto,
    _registros_dono,
    _somar,
    com_capo,
    cortar_no_nut,
    medir_por_grupo,
    quadros_escolha,
    separar,
)
from tab.maos.braco.retreino import fontes as fontes_1037
from tab.maos.braco.retreino import treinar as treinar_1037
from tab.maos.braco.retreino_capo3 import (
    FATOR_CAPO,
    LIMITE_FALSOS,
    _sem_linhas,
    passa_piso,
    sobreamostrar,
)
from tab.maos.braco.tempo import marcas_do_registro

RODADA = "1042"
MODULO = "tab.maos.braco.retreino_1042"
#: Prefixos dos pesos do estágio 1 e do estágio 2.
PREFIXOS = ("L6_capo_s", "A8_capo_s")
#: O par da 1041, a referência no capo (pré-preenche a 1043).
PAR_1041 = ("L5_capo3_s2", "A7_capo3_s2")
ARQUIVO_CONTAGEM = MAOS_M42 / "contagem.json"
ARQUIVO_ESCOLHA = MAOS_M42 / "escolha_pesos.json"
ARQUIVO_MEDIDA_DEV = MAOS_M42 / "medida_dev.json"
ARQUIVO_PREVISTO_PROVA = MAOS_M42 / "previsto_1043.json"
ARQUIVO_MEDIDA_PROVA = MAOS_M42 / "medida_prova.json"


def videos_da_prova() -> set[str]:
    """Vídeos (NFC) do lote da 1043, que não podem entrar no treino.

    Returns:
        Os nomes de arquivo, relativos ao acervo.
    """
    indice = _ler_json(MAOS_M43 / ARQUIVO_INDICE)
    return {nfc(q["arquivo"]) for q in indice["quadros"]}


def fontes() -> dict:
    """As fontes da 1037 mais a M39, sem a 1043 e com o capo sobreamostrado.

    Returns:
        ``estagio1`` e ``estagio2`` (já repetidos), ``relatorio`` e ``antes`` da 1037,
        ``m39`` (o que entrou e saiu da 1039), ``prova_fora`` (por estágio) e ``capo``
        (quadros distintos com capo por estágio).
    """
    base = fontes_1037()
    prova = videos_da_prova()
    m39, contagem_m39 = _registros_dono("M39", GABARITO_BRACO_M39, MAOS_M39)
    m39, relatorio_m39 = separar(m39, prova, EXCLUIDOS)
    gabaritos = {
        **_gabaritos_por_origem(),
        "M39": _ler_json(GABARITO_BRACO_M39)["quadros"],
    }
    cortados = {r["id"] for r in com_capo(m39, gabaritos)}
    m39_estagio1 = [
        {**r, "marcas": cortar_no_nut(r["marcas"])} if r["id"] in cortados else r
        for r in m39
    ]
    resultado = {
        "relatorio": base["relatorio"],
        "antes": base["antes"],
        "m39": {"antes": contagem_m39, "separar": relatorio_m39.get("M39", {})},
        "prova_fora": {},
        "capo": {},
    }
    novos = {"estagio1": m39_estagio1, "estagio2": m39}
    for estagio in ("estagio1", "estagio2"):
        todos = base[estagio] + novos[estagio]
        ficam = [r for r in todos if nfc(r["arquivo"]) not in prova]
        resultado["prova_fora"][estagio] = len(todos) - len(ficam)
        capo = {r["id"] for r in com_capo(ficam, gabaritos)}
        resultado["capo"][estagio] = len(capo)
        resultado[estagio] = sobreamostrar(ficam, capo, FATOR_CAPO)
    return resultado


def contar() -> dict:
    """Conta as fontes (sem GPU) e grava ``contagem.json``.

    Returns:
        Quadros por origem (com as cópias), capo distintos, M39 e prova fora.
    """
    fonte = fontes()
    resultado = {
        "fator_capo": FATOR_CAPO,
        "estagio1_com_copias": _contagem(fonte["estagio1"]),
        "estagio2_com_copias": _contagem(fonte["estagio2"]),
        "capo_distintos": fonte["capo"],
        "m39": fonte["m39"],
        "prova_fora": fonte["prova_fora"],
    }
    gravar_atomico(ARQUIVO_CONTAGEM, resultado)
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    return resultado


def treinar(
    estagio: str, semente: int, passos: int = PASSOS, gravar: bool = True
) -> int:
    """Treina L6 (estágio 1) ou A8 (estágio 2) com a receita da 1041 e a M39.

    Args:
        estagio: ``l4`` (estágio 1) ou ``a6`` (estágio 2), os nomes da CLI da 1037.
        semente: semente do treino.
        passos: passos (``PASSOS`` no treino oficial).
        gravar: se grava o peso e a procedência.

    Returns:
        0 ao terminar.
    """
    return treinar_1037(
        estagio,
        semente,
        passos,
        gravar,
        fonte=fontes(),
        prefixos=PREFIXOS,
        procedencia=(RODADA, MODULO),
    )


def smoke(passos: int = 50) -> int:
    """Teste curto dos dois estágios, sem gravar peso.

    Args:
        passos: passos do teste.

    Returns:
        0 ao terminar.
    """
    treinar("l4", 1, passos, gravar=False)
    treinar("a6", 1, passos, gravar=False)
    return 0


def combinacoes() -> list[tuple[str, str]]:
    """Pares ``(L6, A8)`` cujos pesos existem.

    Returns:
        Os pares, na ordem das sementes.
    """
    um = [f"{PREFIXOS[0]}{s}" for s in SEMENTES if _peso_existe(f"{PREFIXOS[0]}{s}")]
    dois = [f"{PREFIXOS[1]}{s}" for s in SEMENTES if _peso_existe(f"{PREFIXOS[1]}{s}")]
    return [(i, j) for i in um for j in dois]


def invertido(nut_previsto: list[float] | None, registro: dict) -> bool | None:
    """Se o nut previsto caiu do lado do corpo (braço invertido).

    Inverter é o nut previsto ficar mais perto da ponta das cordas do lado do corpo do que
    do nut do dono. A ponta do corpo é a média das pontas de ``corda1`` e ``corda6`` mais
    longe do nut do dono.

    Args:
        nut_previsto: ponto do nut previsto, ou None.
        registro: registro do gabarito do dono.

    Returns:
        True ou False; None quando não há nut previsto ou o quadro não tem o nut do dono.
    """
    marcas = marcas_do_registro(registro)
    if nut_previsto is None or marcas is None or marcas.nut is None:
        return None
    nut = np.asarray(marcas.nut, dtype=float)
    pontas = []
    for corda in (marcas.corda1, marcas.corda6):
        pontos = np.asarray(corda, dtype=float)
        pontas.append(pontos[int(np.argmax(np.linalg.norm(pontos - nut, axis=1)))])
    corpo = np.mean(pontas, axis=0)
    previsto = np.asarray(nut_previsto, dtype=float)
    return bool(np.linalg.norm(previsto - corpo) < np.linalg.norm(previsto - nut))


def contar_inversoes(previsto_doc: dict, gabarito: dict) -> list[int]:
    """Quadros invertidos e quadros com os dois nuts (previsto e do dono).

    Args:
        previsto_doc: previsão no formato de ``previsto.json``.
        gabarito: gabarito do dono (com ``quadros``).

    Returns:
        ``[invertidos, medidos]``.
    """
    invertidos = medidos = 0
    for id_q in previsto_doc["ordem"]:
        registro = gabarito["quadros"].get(id_q)
        if registro is None:
            continue
        previsto = previsto_doc["quadros"][id_q]
        valor = invertido(previsto.get("nut") if previsto["achou"] else None, registro)
        if valor is None:
            continue
        medidos += 1
        invertidos += int(valor)
    return [invertidos, medidos]


def escolher_com_veto(tabela: list[dict], referencia: dict) -> dict | None:
    """O critério da 1029 entre os pares que passam o piso e o veto de inversão.

    Args:
        tabela: uma linha por par, com ``inversoes_m36`` (``[invertidos, medidos]``).
        referencia: a linha do par antigo, com ``inversoes_m36``.

    Returns:
        A linha escolhida, ou None quando nenhum par passa.
    """
    limite = referencia["inversoes_m36"][0]
    candidatos = [
        linha
        for linha in tabela
        if passa_piso(linha, referencia) and linha["inversoes_m36"][0] <= limite
    ]
    return escolher_combinacao(candidatos) if candidatos else None


def escolher() -> dict:
    """Escolhe o par (M11b com piso e veto na M36) e grava ``escolha_pesos.json`` (GPU).

    Returns:
        ``estagio1`` e ``estagio2`` (None se nenhum par passa), ``tabela`` e
        ``referencia``.

    Raises:
        ValueError: se nenhum par L6 + A8 existe.
    """
    combos = combinacoes()
    if not combos:
        raise ValueError("nenhum par L6 + A8 em artefatos")
    itens, registros = quadros_escolha()
    gabarito_m36 = _ler_json(GABARITO_BRACO_M36)
    antigo = pesos_da_rodada(RODADA_REFERENCIA)
    linhas = []
    for e1, e2 in [*combos, (antigo.estagio1, antigo.estagio2)]:
        linha = avaliar_combinacao(e1, e2, itens, registros)
        previsto = _prever_conjunto(MAOS_M36, {}, e1, e2)
        linha["inversoes_m36"] = contar_inversoes(previsto, gabarito_m36)
        linhas.append(linha)
    tabela, referencia = linhas[:-1], linhas[-1]
    vencedora = escolher_com_veto(tabela, referencia)
    escolha = {
        "estagio1": vencedora["estagio1"] if vencedora else None,
        "estagio2": vencedora["estagio2"] if vencedora else None,
        "quadros": [item["id"] for item in itens],
        "criterio": (
            "piso: certos ≥ antigo − 2 na M11b; veto: inversões na M36 ≤ as do antigo; "
            "entre os que passam, o da 1029"
        ),
        "tabela": tabela,
        "referencia": referencia,
    }
    gravar_atomico(ARQUIVO_ESCOLHA, escolha)
    print(json.dumps({k: escolha[k] for k in ("estagio1", "estagio2")}))
    return escolha


def criterio_sem_capo(novo: dict, antigo: dict) -> dict:
    """Critério 3 da 1042 nos quadros sem capo do N.

    Args:
        novo: ``medir_por_grupo`` do par escolhido no N.
        antigo: o mesmo, do par antigo.

    Returns:
        ``passa`` e os números: falsos e certos sem capo, novo e antigo.
    """
    falsos = (
        _somar([novo], "sem_capo", "falsos_passam_n"),
        _somar([antigo], "sem_capo", "falsos_passam_n"),
    )
    certos = (
        _somar([novo], "sem_capo", "entregue_certo"),
        _somar([antigo], "sem_capo", "entregue_certo"),
    )
    return {
        "passa": falsos[0] <= falsos[1] + 1 and certos[0] >= certos[1] - 2,
        "sem_capo_falsos_novo_antigo": list(falsos),
        "sem_capo_certos_novo_antigo": list(certos),
    }


def medir_dev() -> dict:
    """Mede o par escolhido e o antigo no N (critério 3) e grava a medida (GPU).

    Returns:
        ``medidas`` por par e ``criterio_3``; sem medida se não houve escolha.
    """
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    if escolha["estagio1"] is None:
        resultado = {"criterio_3": None, "motivo": "nenhum par passou o piso e o veto"}
        gravar_atomico(ARQUIVO_MEDIDA_DEV, resultado)
        return resultado
    antigo = pesos_da_rodada(RODADA_REFERENCIA)
    pares = {
        "novo": (escolha["estagio1"], escolha["estagio2"]),
        "antigo": (antigo.estagio1, antigo.estagio2),
    }
    _, pasta, gabarito, excluir = next(c for c in CONJUNTOS_MEDIDA if c[0] == "N")
    medidas = {}
    for rotulo, (e1, e2) in pares.items():
        previsto = _prever_conjunto(pasta, excluir, e1, e2)
        gravar_atomico(MAOS_M42 / f"previsto_N_{e1}+{e2}.json", previsto)
        medidas[rotulo] = medir_por_grupo(previsto, _ler_json(gabarito))
    resultado = {
        "pares": {k: list(v) for k, v in pares.items()},
        "medidas": {r: _sem_linhas(m) for r, m in medidas.items()},
        "criterio_3": criterio_sem_capo(medidas["novo"], medidas["antigo"]),
    }
    gravar_atomico(ARQUIVO_MEDIDA_DEV, resultado)
    print(json.dumps(resultado["criterio_3"], ensure_ascii=False))
    return resultado


def prever_prova() -> int:
    """Prevê o lote da 1043 com o par escolhido (GPU). Não lê o gabarito.

    Returns:
        0 ao terminar (também quando não houve escolha).
    """
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    if escolha["estagio1"] is None:
        return 0
    previsto = _prever_conjunto(MAOS_M43, {}, escolha["estagio1"], escolha["estagio2"])
    gravar_atomico(ARQUIVO_PREVISTO_PROVA, previsto)
    return 0


def criterios_prova(novo: dict, referencia: dict) -> dict:
    """Critérios 1 e 2 da 1042 na 1043, contra o par da 1041.

    Args:
        novo: ``medir_por_grupo`` do par escolhido no lote.
        referencia: o mesmo, do par da 1041 (o pré-preenchimento do ciclo).

    Returns:
        ``seguranca`` e ``capo`` (bool cada) e os números usados.
    """
    falsos = novo["todos"]["falsos_passam"]
    return {
        "seguranca": falsos is not None and falsos <= LIMITE_FALSOS,
        "capo": novo["capo"]["falsos_passam_n"] <= 1
        and novo["capo"]["entregue_certo"] >= referencia["capo"]["entregue_certo"],
        "numeros": {
            "falsos_novo": [novo["todos"]["falsos_passam_n"], novo["todos"]["medidos"]],
            "capo_falsos_novo_1041": [
                novo["capo"]["falsos_passam_n"],
                referencia["capo"]["falsos_passam_n"],
            ],
            "capo_certos_novo_1041": [
                novo["capo"]["entregue_certo"],
                referencia["capo"]["entregue_certo"],
            ],
        },
    }


def medir_prova() -> dict:
    """Mede o par novo e o da 1041 no lote da 1043, depois da revisão do dono.

    Returns:
        As medidas dos dois pares e os critérios 1 e 2.
    """
    gabarito = _ler_json(GABARITO_BRACO_M43)
    novo = medir_por_grupo(_ler_json(ARQUIVO_PREVISTO_PROVA), gabarito)
    referencia = medir_por_grupo(_ler_json(MAOS_M43 / "previsto.json"), gabarito)
    resultado = {
        "novo": _sem_linhas(novo),
        "par_1041": _sem_linhas(referencia),
        "criterios": criterios_prova(novo, referencia),
    }
    gravar_atomico(ARQUIVO_MEDIDA_PROVA, resultado)
    print(json.dumps(resultado["criterios"], ensure_ascii=False, indent=1))
    return resultado


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("contar", help="conta as fontes, sem GPU")
    sub.add_parser("smoke", help="50 passos de cada estágio, sem gravar")
    p_treino = sub.add_parser("treinar", help="um treino (GPU)")
    p_treino.add_argument("--estagio", choices=("l4", "a6"), required=True)
    p_treino.add_argument("--semente", type=int, required=True)
    sub.add_parser("escolher", help="escolha com piso e veto de inversão (GPU)")
    sub.add_parser("medir-dev", help="critério 3 no N (GPU)")
    sub.add_parser("prever-prova", help="previsão do lote da 1043 (GPU)")
    sub.add_parser("medir-prova", help="critérios 1 e 2 na 1043, depois do dono")
    args = parser.parse_args()
    if args.comando == "contar":
        contar()
    elif args.comando == "smoke":
        smoke()
    elif args.comando == "treinar":
        treinar(args.estagio, args.semente)
    elif args.comando == "escolher":
        escolher()
    elif args.comando == "medir-dev":
        medir_dev()
    elif args.comando == "prever-prova":
        prever_prova()
    else:
        medir_prova()
    return 0


if __name__ == "__main__":
    sys.exit(main())
