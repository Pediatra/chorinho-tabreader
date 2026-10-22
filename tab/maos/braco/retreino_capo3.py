"""Rodada 1041: retreino do braço com os quadros de capo sorteados 3 vezes mais.

A receita, as fontes e as exclusões são as da 1037 (``tab.maos_braco_retreino``). Mudam
três coisas:

- **sobreamostragem**: cada quadro com capo entra ``FATOR_CAPO`` vezes no sorteio do treino
  dos dois estágios (``L5_capo3_s<k>`` e ``A7_capo3_s<k>``);
- **barreira**: além das medidas da 1037, nenhum quadro de um vídeo do lote da 1039 entra no
  treino, porque a 1039 é a prova desta rodada;
- **escolha com piso**: só concorre o par com entregues certos ≥ os do par antigo menos
  ``PISO_CERTOS`` na folha da escolha. Na 1037, o critério sem piso escolheu o par que
  invertia o braço e sinalizava quase tudo.

Pré-registro: ``docs/rodadas/1041-retreino-capo-sobreamostrado.md``.

CLI: ``python -m tab.maos_braco_retreino_capo3
{contar,smoke,treinar,escolher,medir-dev,prever-prova,medir-prova}``.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata

from tab.comum.caminhos import (
    GABARITO_BRACO_M39,
    MAOS_M39,
    MAOS_M41,
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
    RODADA_REFERENCIA,
    SEMENTES,
    _contagem,
    _gabaritos_por_origem,
    _peso_existe,
    _prever_conjunto,
    _somar,
    com_capo,
    medir_por_grupo,
    quadros_escolha,
)
from tab.maos.braco.retreino import fontes as fontes_1037
from tab.maos.braco.retreino import treinar as treinar_1037
from tab.maos.gabarito import gravar_atomico

RODADA = "1041"
MODULO = "tab.maos_braco_retreino_capo3"
#: Quantas vezes cada quadro com capo entra no sorteio do treino.
FATOR_CAPO = 3
#: Prefixos dos pesos do estágio 1 e do estágio 2.
PREFIXOS = ("L5_capo3_s", "A7_capo3_s")
#: Piso da escolha: entregues certos ≥ os do par antigo menos este número.
PISO_CERTOS = 2
#: Limite de falsos que passam na prova (1039): 5 % dos quadros medidos.
LIMITE_FALSOS = 0.05
ARQUIVO_CONTAGEM = MAOS_M41 / "contagem.json"
ARQUIVO_ESCOLHA = MAOS_M41 / "escolha_pesos.json"
ARQUIVO_MEDIDA_DEV = MAOS_M41 / "medida_dev.json"
ARQUIVO_PREVISTO_PROVA = MAOS_M41 / "previsto_1039.json"
ARQUIVO_MEDIDA_PROVA = MAOS_M41 / "medida_prova.json"


def _nfc(texto: str) -> str:
    """Nome de arquivo em NFC.

    Args:
        texto: nome.

    Returns:
        O nome normalizado.
    """
    return unicodedata.normalize("NFC", texto)


def videos_da_prova() -> set[str]:
    """Vídeos (NFC) do lote da 1039, que não podem entrar no treino.

    Returns:
        Os nomes de arquivo, relativos ao acervo.
    """
    indice = _ler_json(MAOS_M39 / ARQUIVO_INDICE)
    return {_nfc(q["arquivo"]) for q in indice["quadros"]}


def sobreamostrar(registros: list[dict], capo: set[str], fator: int) -> list[dict]:
    """Repete ``fator`` vezes cada registro com capo (o sorteio do treino é uniforme).

    Args:
        registros: quadros de treino, com ``id``.
        capo: ids dos quadros com capo.
        fator: quantas vezes cada um entra (1 deixa como está).

    Returns:
        Os registros na ordem original, com as cópias dos de capo logo depois de cada um.

    Raises:
        ValueError: se ``fator`` < 1.
    """
    if fator < 1:
        raise ValueError(f"fator inválido: {fator}")
    saida: list[dict] = []
    for registro in registros:
        copias = fator if registro["id"] in capo else 1
        saida += [registro] * copias
    return saida


def fontes() -> dict:
    """Os quadros da 1037, sem o lote da 1039 e com o capo sobreamostrado.

    Returns:
        ``estagio1`` e ``estagio2`` (já repetidos), ``relatorio`` e ``antes`` da 1037,
        ``prova_fora`` (quantos saíram por estágio por serem da 1039) e ``capo``
        (quadros distintos com capo por estágio).
    """
    base = fontes_1037()
    prova = videos_da_prova()
    gabaritos = _gabaritos_por_origem()
    resultado = {"relatorio": base["relatorio"], "antes": base["antes"]}
    resultado["prova_fora"] = {}
    resultado["capo"] = {}
    for estagio in ("estagio1", "estagio2"):
        ficam = [r for r in base[estagio] if _nfc(r["arquivo"]) not in prova]
        resultado["prova_fora"][estagio] = len(base[estagio]) - len(ficam)
        capo = {r["id"] for r in com_capo(ficam, gabaritos)}
        resultado["capo"][estagio] = len(capo)
        resultado[estagio] = sobreamostrar(ficam, capo, FATOR_CAPO)
    return resultado


def contar() -> dict:
    """Conta as fontes (sem GPU) e grava ``contagem.json``.

    Returns:
        Quadros por origem (com as cópias), quadros distintos com capo e os da 1039 fora.
    """
    fonte = fontes()
    resultado = {
        "fator_capo": FATOR_CAPO,
        "estagio1_com_copias": _contagem(fonte["estagio1"]),
        "estagio2_com_copias": _contagem(fonte["estagio2"]),
        "capo_distintos": fonte["capo"],
        "prova_fora": fonte["prova_fora"],
    }
    gravar_atomico(ARQUIVO_CONTAGEM, resultado)
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    return resultado


def treinar(
    estagio: str, semente: int, passos: int = PASSOS, gravar: bool = True
) -> int:
    """Treina L5 (estágio 1) ou A7 (estágio 2) com a receita da 1037 e o capo repetido.

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
    """Pares ``(L5, A7)`` cujos pesos existem.

    Returns:
        Os pares, na ordem das sementes.
    """
    um = [f"{PREFIXOS[0]}{s}" for s in SEMENTES if _peso_existe(f"{PREFIXOS[0]}{s}")]
    dois = [f"{PREFIXOS[1]}{s}" for s in SEMENTES if _peso_existe(f"{PREFIXOS[1]}{s}")]
    return [(i, j) for i in um for j in dois]


def passa_piso(linha: dict, referencia: dict, piso: int = PISO_CERTOS) -> bool:
    """Se o par entrega certos suficientes para concorrer.

    Args:
        linha: linha da tabela da escolha (``avaliar_combinacao``).
        referencia: a linha do par antigo nos mesmos quadros.
        piso: quantos certos a menos que o antigo ainda são aceitos.

    Returns:
        True com ``entregue_certo`` ≥ o do antigo − ``piso``.
    """
    return linha["entregue_certo"] >= referencia["entregue_certo"] - piso


def escolher_com_piso(tabela: list[dict], referencia: dict) -> dict | None:
    """O critério da 1029 entre os pares que passam o piso.

    Args:
        tabela: uma linha por par.
        referencia: a linha do par antigo.

    Returns:
        A linha escolhida, ou None quando nenhum par passa o piso.
    """
    candidatos = [linha for linha in tabela if passa_piso(linha, referencia)]
    return escolher_combinacao(candidatos) if candidatos else None


def escolher() -> dict:
    """Escolhe o par nos 33 quadros da escolha da 1037 e grava ``escolha_pesos.json`` (GPU).

    Returns:
        ``estagio1`` e ``estagio2`` (None se nenhum par passa o piso), ``tabela``,
        ``referencia`` e os quadros usados.

    Raises:
        ValueError: se nenhum par L5 + A7 existe.
    """
    combos = combinacoes()
    if not combos:
        raise ValueError("nenhum par L5 + A7 em artefatos/m21")
    itens, registros = quadros_escolha()
    tabela = [avaliar_combinacao(a, b, itens, registros) for a, b in combos]
    antigo = pesos_da_rodada(RODADA_REFERENCIA)
    referencia = avaliar_combinacao(antigo.estagio1, antigo.estagio2, itens, registros)
    vencedora = escolher_com_piso(tabela, referencia)
    escolha = {
        "estagio1": vencedora["estagio1"] if vencedora else None,
        "estagio2": vencedora["estagio2"] if vencedora else None,
        "quadros": [item["id"] for item in itens],
        "criterio": (
            f"piso: certos ≥ antigo − {PISO_CERTOS}; entre os que passam, o da 1029"
        ),
        "tabela": tabela,
        "referencia": referencia,
    }
    gravar_atomico(ARQUIVO_ESCOLHA, escolha)
    print(json.dumps({k: escolha[k] for k in ("estagio1", "estagio2")}))
    return escolha


def criterio_sem_capo(novo: dict[str, dict], antigo: dict[str, dict]) -> dict:
    """Critério 3 da 1041 (o mesmo da 1037) nos quadros sem capo da M36 e do N.

    Args:
        novo: ``{conjunto: medir_por_grupo}`` do par escolhido.
        antigo: o mesmo, do par antigo.

    Returns:
        ``passa`` e os números: falsos e certos sem capo, novo e antigo.
    """
    n, a = list(novo.values()), list(antigo.values())
    falsos = (
        _somar(n, "sem_capo", "falsos_passam_n"),
        _somar(a, "sem_capo", "falsos_passam_n"),
    )
    certos = (
        _somar(n, "sem_capo", "entregue_certo"),
        _somar(a, "sem_capo", "entregue_certo"),
    )
    return {
        "passa": falsos[0] <= falsos[1] + 1 and certos[0] >= certos[1] - 2,
        "sem_capo_falsos_novo_antigo": list(falsos),
        "sem_capo_certos_novo_antigo": list(certos),
    }


def _sem_linhas(medida: dict) -> dict:
    """A medida sem as linhas por quadro (para o resumo).

    Args:
        medida: saída de ``medir_por_grupo``.

    Returns:
        A mesma medida, sem ``linhas``.
    """
    return {k: v for k, v in medida.items() if k != "linhas"}


def medir_dev() -> dict:
    """Mede o par escolhido e o antigo na M36 e no N (critério 3) e grava a medida (GPU).

    Returns:
        ``medidas`` por par e conjunto e ``criterio_3``; vazio se não houve escolha.
    """
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    if escolha["estagio1"] is None:
        resultado = {"criterio_3": None, "motivo": "nenhum par passou o piso"}
        gravar_atomico(ARQUIVO_MEDIDA_DEV, resultado)
        return resultado
    antigo = pesos_da_rodada(RODADA_REFERENCIA)
    pares = {
        "novo": (escolha["estagio1"], escolha["estagio2"]),
        "antigo": (antigo.estagio1, antigo.estagio2),
    }
    medidas: dict[str, dict] = {}
    for rotulo, (e1, e2) in pares.items():
        medidas[rotulo] = {}
        for nome, pasta, gabarito, excluir in CONJUNTOS_MEDIDA:
            previsto = _prever_conjunto(pasta, excluir, e1, e2)
            gravar_atomico(MAOS_M41 / f"previsto_{nome}_{e1}+{e2}.json", previsto)
            medidas[rotulo][nome] = medir_por_grupo(previsto, _ler_json(gabarito))
    resultado = {
        "pares": {k: list(v) for k, v in pares.items()},
        "medidas": {
            r: {c: _sem_linhas(m) for c, m in conj.items()}
            for r, conj in medidas.items()
        },
        "criterio_3": criterio_sem_capo(medidas["novo"], medidas["antigo"]),
    }
    gravar_atomico(ARQUIVO_MEDIDA_DEV, resultado)
    print(json.dumps(resultado["criterio_3"], ensure_ascii=False))
    return resultado


def prever_prova() -> int:
    """Prevê o lote da 1039 com o par escolhido (GPU). Não lê o gabarito.

    Returns:
        0 ao terminar (também quando não houve escolha).
    """
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    if escolha["estagio1"] is None:
        return 0
    previsto = _prever_conjunto(MAOS_M39, {}, escolha["estagio1"], escolha["estagio2"])
    gravar_atomico(ARQUIVO_PREVISTO_PROVA, previsto)
    return 0


def criterios_prova(novo: dict, antigo: dict) -> dict:
    """Critérios 1 e 2 da 1041 no lote da 1039, contra o par antigo.

    Args:
        novo: ``medir_por_grupo`` do par escolhido no lote.
        antigo: o mesmo, do par antigo (a previsão do ciclo).

    Returns:
        ``seguranca`` e ``capo`` (bool cada) e os números usados.
    """
    falsos = novo["todos"]["falsos_passam"]
    return {
        "seguranca": falsos is not None and falsos <= LIMITE_FALSOS,
        "capo": novo["capo"]["falsos_passam_n"] <= 1
        and novo["capo"]["entregue_certo"] >= antigo["capo"]["entregue_certo"],
        "numeros": {
            "falsos_novo": [novo["todos"]["falsos_passam_n"], novo["todos"]["medidos"]],
            "capo_falsos_novo_antigo": [
                novo["capo"]["falsos_passam_n"],
                antigo["capo"]["falsos_passam_n"],
            ],
            "capo_certos_novo_antigo": [
                novo["capo"]["entregue_certo"],
                antigo["capo"]["entregue_certo"],
            ],
        },
    }


def medir_prova() -> dict:
    """Mede o par novo e o antigo no lote da 1039, depois da revisão do dono.

    Returns:
        As medidas dos dois pares e os critérios 1 e 2.
    """
    gabarito = _ler_json(GABARITO_BRACO_M39)
    novo = medir_por_grupo(_ler_json(ARQUIVO_PREVISTO_PROVA), gabarito)
    antigo = medir_por_grupo(_ler_json(MAOS_M39 / "previsto.json"), gabarito)
    resultado = {
        "novo": _sem_linhas(novo),
        "antigo": _sem_linhas(antigo),
        "criterios": criterios_prova(novo, antigo),
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
    sub.add_parser("escolher", help="escolha do par com piso (GPU)")
    sub.add_parser("medir-dev", help="critério 3 na M36 e no N (GPU)")
    sub.add_parser("prever-prova", help="previsão do lote da 1039 (GPU)")
    sub.add_parser("medir-prova", help="critérios 1 e 2 na 1039, depois do dono")
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
