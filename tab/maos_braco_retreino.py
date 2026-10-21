"""Rodada 1037: retreino dos dois estágios do braço com a regra do capo (decisão 1010).

Estágio 1 (``L4_capo_s<k>``): R + G + C + M26 + M27 + M29 + M32.
Estágio 2 (``A6_capo_s<k>``): S + R + M26 + M27 + M29 + M32, na mistura A3.

O que muda em relação à 1028 (L3 e A4):

- as marcas são as remarcadas pela decisão 1010: com capo, o nut é o traste à frente do
  capo. Os R das 8 chaves da M3b com capo foram rastreados de novo
  (``python -m tab.maos_braco_m21 rastreador --chaves ...``);
- entram a M29 (1029) e a M32 (1032, 48 quadros com capo);
- sai o N (M25 prova), que passa a ser medida, junto com a 1036 (M36);
- saem os quadros que o dono ainda não confirmou (``EXCLUIDOS``) e todo quadro de um vídeo
  das medidas (M11b, M25 prova e M36).

Pré-registro: ``docs/rodadas/1037-retreino-com-capo.md``.

CLI: ``python -m tab.maos_braco_retreino {contar,folhas,smoke,treinar,escolher,medir}``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import random
import statistics
import sys
import unicodedata
from pathlib import Path

import numpy as np

from .caminhos import (
    GABARITO_BRACO_M11B,
    GABARITO_BRACO_M25_PROVA,
    GABARITO_BRACO_M25_TREINO,
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    GABARITO_BRACO_M29,
    GABARITO_BRACO_M32,
    GABARITO_BRACO_M36,
    MAOS_M3B,
    MAOS_M11B,
    MAOS_M25,
    MAOS_M26,
    MAOS_M27,
    MAOS_M29,
    MAOS_M32,
    MAOS_M36,
    MAOS_M37,
)
from .maos_braco_ciclo import (
    ARQUIVO_INDICE,
    _quadros_m11b,
    _totais,
    aplicar_sinal_nut_v2,
    avaliar_combinacao,
    escolher_combinacao,
    medir_quadros,
    pesos_da_rodada,
)
from .maos_braco_ciclo import (
    _prever_quadros as prever_quadros,
)
from .maos_braco_detector import (
    DIR_PESOS,
    MISTURA,
    PASSOS,
    _entradas_g,
    _gabarito,
    _ler_json,
    _pool_r,
    _pool_s,
    _salvar_pesos,
    _sequencia,
    _trava_gpu,
    _treinar,
)
from .maos_braco_localizador import (
    QUADRO_EXCLUIDO_PROVA,
    _grava_folha,
    _indice_por_id,
    _treinar_localizador,
    _utilizavel,
    marcas_da_fonte_c,
)
from .maos_braco_localizador import (
    _sequencia as _sequencia_localizador,
)
from .maos_braco_p4 import MARCA_7_CORDAS, _folha_a4
from .maos_braco_tempo import Marcas, marcas_do_registro
from .maos_gabarito import gravar_atomico

#: Quadros fora do treino e da medida até o dono confirmar, por origem e chave.
EXCLUIDOS: dict[str, dict[str, str]] = {
    "M3b": {"q10": "capo a 1,36 casa atrás do nut marcado (mais de uma casa)"},
    "M32": {
        "q14": "capo à frente do nut marcado (+0,52 casa)",
        "q45": "capo à frente do nut marcado (+0,17 casa)",
    },
    "C": {"q139": "vídeo com capo, nut marcado e sem a marca k do capo"},
}
#: Fontes do dono com marcas completas: (origem, gabarito, pasta com ``indice.json``).
FONTES_DONO = (
    ("M26", GABARITO_BRACO_M26, MAOS_M26),
    ("M27", GABARITO_BRACO_M27, MAOS_M27),
    ("M29", GABARITO_BRACO_M29, MAOS_M29),
    ("M32", GABARITO_BRACO_M32, MAOS_M32),
)
#: Índices dos conjuntos de medida. Nenhum quadro de um vídeo deles entra no treino.
INDICES_MEDIDA = (
    ("M11b", MAOS_M11B / ARQUIVO_INDICE),
    ("N", MAOS_M25 / "prova" / ARQUIVO_INDICE),
    ("M36", MAOS_M36 / ARQUIVO_INDICE),
)
#: Conjuntos medidos depois da escolha: (nome, pasta, gabarito, ids fora e motivo).
CONJUNTOS_MEDIDA = (
    ("M36", MAOS_M36, GABARITO_BRACO_M36, {}),
    (
        "N",
        MAOS_M25 / "prova",
        GABARITO_BRACO_M25_PROVA,
        {QUADRO_EXCLUIDO_PROVA: "guitarra (fora desde a 1025)"},
    ),
)
#: Quadros da M11b com capo fora da lista da escolha da 1029, que a 1037 acrescenta.
EXTRA_ESCOLHA = ("q37", "q38", "q39", "q40")
#: Prefixos dos pesos novos e sementes.
PREFIXO_L4 = "L4_capo_s"
PREFIXO_A6 = "A6_capo_s"
SEMENTES = (1, 2, 3)
#: Rodada cujos pesos são a referência antiga (L3_todos_s3 + A4_100_todos_s1).
RODADA_REFERENCIA = "1032"
#: Rodada que mede o par escolhido num lote novo (a frase do critério do ciclo).
PROXIMA = "1039"
#: Estimativa de GPU por treino, escrita no ``gpu.lock``.
ESTIMATIVA = {"l4": "~25 min", "a6": "~60 min"}
#: Saídas da rodada.
ARQUIVO_CONTAGEM = MAOS_M37 / "contagem.json"
ARQUIVO_ESCOLHA = MAOS_M37 / "escolha_pesos.json"
ARQUIVO_MEDIDA = MAOS_M37 / "medida.json"
ARQUIVO_FOLHA_L4 = MAOS_M37 / "l4_folha_capo.jpg"
ARQUIVO_FOLHA_A6 = MAOS_M37 / "a6_folha_capo.jpg"
SEMENTE_FOLHA = "20261037:folha"
QUADROS_FOLHA = 12
#: Variável com o commit do código, gravada no json do peso (o container não tem git).
VARIAVEL_COMMIT = "CHORINHO_COMMIT"


def _nfc(texto: str) -> str:
    """Normaliza um nome de arquivo para comparação (kana e acento).

    Args:
        texto: nome do arquivo.

    Returns:
        O nome em NFC.
    """
    return unicodedata.normalize("NFC", texto)


def chave_do_r(caminho: str) -> str:
    """Quadro-chave da M3b de onde um quadro R foi rastreado.

    Args:
        caminho: arquivo do R, como ``.../q10_+3.jpg``.

    Returns:
        A chave, como ``q10``.
    """
    return Path(caminho).stem.split("_", 1)[0]


def videos_das_medidas() -> set[str]:
    """Vídeos (NFC) dos conjuntos de medida: M11b, M25 prova e M36.

    Returns:
        Os nomes de arquivo, relativos ao acervo.
    """
    videos: set[str] = set()
    for _, caminho in INDICES_MEDIDA:
        videos |= {_nfc(q["arquivo"]) for q in _ler_json(caminho)["quadros"]}
    return videos


def separar(
    registros: list[dict],
    proibidos: set[str],
    excluidos: dict[str, dict[str, str]],
) -> tuple[list[dict], dict[str, dict]]:
    """Tira do treino os quadros excluídos e os de vídeos das medidas.

    Args:
        registros: quadros com ``origem``, ``chave`` (id do quadro na origem; no R, a
            chave da M3b) e ``arquivo``.
        proibidos: vídeos das medidas, em NFC.
        excluidos: chaves fora por origem (``EXCLUIDOS``). O R e o G seguem a M3b.

    Returns:
        ``(ficam, relatorio)``: os registros que ficam, e por origem quantos ficam e
        quais saíram, com o motivo.
    """
    ficam: list[dict] = []
    relatorio: dict[str, dict] = {}
    for registro in registros:
        origem = registro["origem"]
        conta = relatorio.setdefault(origem, {"usados": 0, "fora": []})
        grupo = "M3b" if origem in ("R", "G") else origem
        motivo = excluidos.get(grupo, {}).get(registro["chave"])
        if motivo is None and _nfc(registro["arquivo"]) in proibidos:
            motivo = "vídeo de um conjunto de medida"
        if motivo is not None:
            conta["fora"].append({"id": registro["id"], "motivo": motivo})
            continue
        conta["usados"] += 1
        ficam.append(registro)
    return ficam, relatorio


def _registros_r() -> list[dict]:
    """Quadros R (rastreados da M3b), com a chave e o vídeo.

    Returns:
        Registros com ``id``, ``origem``, ``chave``, ``canal``, ``arquivo``,
        ``caminho``, ``registro`` e ``marcas`` (None quando o alvo do L4 não é
        utilizável).
    """
    registros = []
    for entrada in _pool_r():
        marcas = marcas_do_registro(entrada["registro"])
        registros.append(
            {
                "id": Path(entrada["caminho"]).stem,
                "origem": "R",
                "chave": chave_do_r(entrada["caminho"]),
                "canal": entrada["canal"],
                "arquivo": entrada["arquivo"],
                "caminho": entrada["caminho"],
                "registro": entrada["registro"],
                "marcas": marcas if _utilizavel(marcas) else None,
            }
        )
    return registros


def _registros_g() -> list[dict]:
    """Quadros G (M3b do dono), com as marcas atuais do ``braco.json``.

    Returns:
        Registros com ``id``, ``origem``, ``chave``, ``canal``, ``arquivo``,
        ``caminho`` e ``marcas`` (só os utilizáveis).
    """
    gabarito = _gabarito()
    registros = []
    for entrada in _entradas_g(None):
        marcas = marcas_do_registro(gabarito[entrada["id"]])
        if not _utilizavel(marcas):
            continue
        registros.append(
            {
                "id": entrada["id"],
                "origem": "G",
                "chave": entrada["id"],
                "canal": entrada["canal"],
                "arquivo": entrada["arquivo"],
                "caminho": str(MAOS_M3B / "quadros" / f"{entrada['id']}.png"),
                "marcas": marcas,
            }
        )
    return registros


def _registros_c() -> list[dict]:
    """Quadros C (M25 treino, marcas grosseiras: nut e duas cordas).

    Returns:
        Registros com ``id``, ``origem``, ``chave``, ``canal``, ``arquivo``,
        ``caminho`` e ``marcas``.
    """
    pasta = MAOS_M25 / "treino"
    indice = _indice_por_id(pasta / ARQUIVO_INDICE)
    registros = []
    for id_quadro, registro in _ler_json(GABARITO_BRACO_M25_TREINO)["quadros"].items():
        marcas = marcas_da_fonte_c(registro)
        if not _utilizavel(marcas):
            continue
        entrada = indice[id_quadro]
        registros.append(
            {
                "id": f"C-{id_quadro}",
                "origem": "C",
                "chave": id_quadro,
                "canal": entrada["canal"],
                "arquivo": entrada["arquivo"],
                "caminho": str(pasta / entrada["png"]),
                "marcas": marcas,
            }
        )
    return registros


def _registros_dono(origem: str, gabarito: Path, pasta: Path) -> tuple[list, dict]:
    """Quadros de uma rodada do ciclo com marcas completas do dono.

    Sai o que não tem braço ``sim``, o violão de 7 cordas, o nut fora e as marcas
    incompletas, como na 1028.

    Args:
        origem: ``M26``, ``M27``, ``M29`` ou ``M32``.
        gabarito: gabarito da rodada.
        pasta: pasta com ``indice.json``.

    Returns:
        ``(registros, contagem)``: registros com ``id``, ``origem``, ``chave``,
        ``canal``, ``arquivo``, ``caminho``, ``registro`` e ``marcas``, e o que saiu
        antes de ``separar``, por motivo.
    """
    indice = _indice_por_id(pasta / ARQUIVO_INDICE)
    contagem = {
        "total": 0,
        "sem_braco": 0,
        "7_cordas": 0,
        "nut_fora": 0,
        "incompletos": 0,
    }
    registros = []
    for id_quadro, registro in _ler_json(gabarito)["quadros"].items():
        contagem["total"] += 1
        if registro.get("braco") != "sim":
            contagem["sem_braco"] += 1
            continue
        if MARCA_7_CORDAS in str(registro.get("obs") or ""):
            contagem["7_cordas"] += 1
            continue
        marcas = marcas_do_registro(registro)
        if marcas is not None and marcas.nut is None:
            contagem["nut_fora"] += 1
            continue
        if not _utilizavel(marcas):
            contagem["incompletos"] += 1
            continue
        entrada = indice[id_quadro]
        registros.append(
            {
                "id": f"{origem}-{id_quadro}",
                "origem": origem,
                "chave": id_quadro,
                "canal": entrada["canal"],
                "arquivo": entrada["arquivo"],
                "caminho": str(pasta / entrada["png"]),
                "registro": registro,
                "marcas": marcas,
            }
        )
    return registros, contagem


def fontes() -> dict:
    """Os quadros de treino dos dois estágios, já sem os excluídos e os das medidas.

    Returns:
        ``estagio1`` (R, G, C e dono, com ``marcas``), ``estagio2`` (R e dono, com
        ``registro``), ``relatorio`` (por origem, de ``separar``) e ``antes`` (o que saiu
        das fontes do dono antes, por motivo).
    """
    proibidos = videos_das_medidas()
    dono: list[dict] = []
    antes: dict[str, dict] = {}
    for origem, gabarito, pasta in FONTES_DONO:
        registros, contagem = _registros_dono(origem, gabarito, pasta)
        dono += registros
        antes[origem] = contagem
    todos_r = _registros_r()
    candidatos1 = (
        [r for r in todos_r if r["marcas"] is not None]
        + _registros_g()
        + _registros_c()
        + dono
    )
    estagio1, relatorio = separar(candidatos1, proibidos, EXCLUIDOS)
    estagio2, relatorio2 = separar(todos_r + dono, proibidos, EXCLUIDOS)
    relatorio["R_estagio2"] = relatorio2["R"]
    gabaritos = _gabaritos_por_origem()
    cortados = {r["id"] for r in com_capo(estagio1, gabaritos)}
    estagio1 = [
        {**r, "marcas": cortar_no_nut(r["marcas"])} if r["id"] in cortados else r
        for r in estagio1
    ]
    return {
        "estagio1": estagio1,
        "estagio2": estagio2,
        "relatorio": relatorio,
        "antes": antes,
    }


def cortar_no_nut(marcas: Marcas) -> Marcas:
    """Alvo do estágio 1 com capo: as cordas começam no nut marcado, não no verdadeiro.

    O dono marca as cordas por toda a extensão visível, e com capo elas seguem até o nut
    verdadeiro. Pela decisão 1010 o braço começa no capo, e o estágio 1 tira desses pontos
    o começo da faixa. Por isso, a ponta de cada corda mais perto do nut vira a projeção
    do nut marcado sobre a reta da corda. A ponta longe fica igual.

    Args:
        marcas: marcas do quadro, com o nut.

    Returns:
        Novas marcas, com a ponta perto de ``corda1`` e de ``corda6`` trocada.

    Raises:
        ValueError: se o quadro não tem o nut.
    """
    if marcas.nut is None:
        raise ValueError("cortar no nut precisa do nut")
    nut = np.asarray(marcas.nut, dtype=float)
    cordas = []
    for corda in (marcas.corda1, marcas.corda6):
        pontos = np.asarray(corda, dtype=float).copy()
        perto = int(np.argmin(np.linalg.norm(pontos - nut, axis=1)))
        direcao = pontos[1] - pontos[0]
        t = float(np.dot(nut - pontos[0], direcao) / np.dot(direcao, direcao))
        pontos[perto] = pontos[0] + t * direcao
        cordas.append(pontos)
    return dataclasses.replace(marcas, corda1=cordas[0], corda6=cordas[1])


def _contagem(registros: list[dict]) -> dict[str, int]:
    """Quadros por origem, na ordem de aparição.

    Args:
        registros: registros com ``origem``.

    Returns:
        origem -> quantidade.
    """
    contagem: dict[str, int] = {}
    for registro in registros:
        contagem[registro["origem"]] = contagem.get(registro["origem"], 0) + 1
    return contagem


def tem_capo(registro: dict) -> bool:
    """Se o quadro tem o capo marcado pelo dono (tecla ``k``).

    Args:
        registro: registro do gabarito.

    Returns:
        True com o ponto ``capo``.
    """
    return isinstance(registro.get("capo"), list)


def _gabaritos_por_origem() -> dict[str, dict]:
    """Gabarito de cada origem do treino (o R e o G usam o da M3b).

    Returns:
        origem -> ``quadros`` do gabarito.
    """
    m3b = _gabarito()
    gabaritos = {origem: _ler_json(g)["quadros"] for origem, g, _ in FONTES_DONO}
    gabaritos["C"] = _ler_json(GABARITO_BRACO_M25_TREINO)["quadros"]
    gabaritos["R"] = m3b
    gabaritos["G"] = m3b
    return gabaritos


def com_capo(registros: list[dict], gabaritos: dict[str, dict]) -> list[dict]:
    """Os registros de treino cujo quadro tem o capo marcado (o R herda da chave).

    Args:
        registros: registros com ``origem`` e ``chave``.
        gabaritos: saída de ``_gabaritos_por_origem``.

    Returns:
        Os registros com capo, na mesma ordem.
    """
    return [r for r in registros if tem_capo(gabaritos[r["origem"]][r["chave"]])]


def contar() -> dict:
    """Conta as fontes (sem GPU) e grava ``contagem.json``.

    Returns:
        Quadros por origem nos dois estágios, os que saíram e os com capo.
    """
    fonte = fontes()
    resultado = {
        "estagio1": _contagem(fonte["estagio1"]),
        "estagio2": _contagem(fonte["estagio2"]),
        "capo_estagio1": _contagem(
            com_capo(fonte["estagio1"], _gabaritos_por_origem())
        ),
        "capo_estagio2": _contagem(
            com_capo(fonte["estagio2"], _gabaritos_por_origem())
        ),
        "fora": {k: v["fora"] for k, v in fonte["relatorio"].items() if v["fora"]},
        "antes": fonte["antes"],
    }
    gravar_atomico(ARQUIVO_CONTAGEM, resultado)
    print(json.dumps(resultado, ensure_ascii=False, indent=1)[:3000])
    return resultado


def _meta(nome: str, estagio: str, semente: int, passos: int, extra: dict) -> dict:
    """Procedência do peso: comando, semente, passos, commit e fontes.

    Args:
        nome: nome do peso.
        estagio: ``l4`` ou ``a6``.
        semente: semente do treino.
        passos: passos do treino.
        extra: contagens e perdas.

    Returns:
        O json gravado ao lado do ``.pt``.
    """
    return {
        "nome": nome,
        "rodada": "1037",
        "comando": (
            f"python -m tab.maos_braco_retreino treinar --estagio {estagio} "
            f"--semente {semente}"
        ),
        "commit": os.environ.get(VARIAVEL_COMMIT),
        "semente": semente,
        "passos": passos,
        **extra,
    }


def treinar(
    estagio: str, semente: int, passos: int = PASSOS, gravar: bool = True
) -> int:
    """Treina L4 (estágio 1) ou A6 (estágio 2) e grava o peso com a procedência.

    Args:
        estagio: ``l4`` ou ``a6``.
        semente: semente do treino.
        passos: passos (``PASSOS`` no treino oficial).
        gravar: se grava ``artefatos/m21/<nome>.pt`` e o json.

    Returns:
        0 ao terminar.

    Raises:
        ValueError: se ``estagio`` não é ``l4`` nem ``a6``.
    """
    if estagio not in ESTIMATIVA:
        raise ValueError(f"estágio desconhecido: {estagio}")
    fonte = fontes()
    if estagio == "l4":
        nome = f"{PREFIXO_L4}{semente}"
        registros = fonte["estagio1"]
        itens = _sequencia_localizador(registros, passos, nome)
        with _trava_gpu(ESTIMATIVA[estagio]):
            modelo, perdas, segundos = _treinar_localizador(itens, passos, semente)
    else:
        nome = f"{PREFIXO_A6}{semente}"
        registros = fonte["estagio2"]
        pool_s = _pool_s()
        pool = [
            {"caminho": r["caminho"], "registro": r["registro"], "canal": r["canal"]}
            for r in registros
        ]
        sequencia = _sequencia(
            pool_s, pool, passos, MISTURA["A3"], f"a6:{semente}:{passos}"
        )
        with _trava_gpu(ESTIMATIVA[estagio]):
            modelo, perdas, segundos = _treinar(sequencia, passos, semente)
    fontes_usadas = _contagem(registros)
    if estagio == "a6":
        fontes_usadas = {"S": len(pool_s), **fontes_usadas}
    if gravar:
        _salvar_pesos(
            modelo,
            nome,
            _meta(
                nome,
                estagio,
                semente,
                passos,
                {
                    "quadros_por_fonte": fontes_usadas,
                    "fora": {
                        k: v["fora"] for k, v in fonte["relatorio"].items() if v["fora"]
                    },
                    "tempo_treino_s": segundos,
                    "perdas": perdas,
                },
            ),
        )
    print(
        f"{nome}: {passos} passos, quadros {fontes_usadas}, perda final "
        f"{perdas[-1]:.4f}, {segundos:.0f} s",
        file=sys.stderr,
    )
    return 0


def folhas() -> None:
    """Folhas do alvo que a rede recebe, só com quadros de capo (12 de cada estágio)."""
    fonte = fontes()
    gabaritos = _gabaritos_por_origem()
    rng = random.Random(SEMENTE_FOLHA)
    capo1 = com_capo(fonte["estagio1"], gabaritos)
    sorteio1 = rng.sample(capo1, min(QUADROS_FOLHA, len(capo1)))
    _grava_folha(sorteio1, [rng.getrandbits(31) for _ in sorteio1], ARQUIVO_FOLHA_L4)
    capo2 = com_capo(fonte["estagio2"], gabaritos)
    _folha_a4(rng.sample(capo2, min(QUADROS_FOLHA, len(capo2))), ARQUIVO_FOLHA_A6)


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


def _peso_existe(nome: str) -> bool:
    """Se o peso tem ``.pt`` e ``.json`` em ``artefatos/m21``.

    Args:
        nome: nome do peso.

    Returns:
        True quando os dois existem.
    """
    return (DIR_PESOS / f"{nome}.pt").is_file() and (
        DIR_PESOS / f"{nome}.json"
    ).is_file()


def combinacoes() -> list[tuple[str, str]]:
    """Pares ``(L4, A6)`` cujos pesos existem.

    Returns:
        Os pares, na ordem das sementes.
    """
    l4 = [f"{PREFIXO_L4}{s}" for s in SEMENTES if _peso_existe(f"{PREFIXO_L4}{s}")]
    a6 = [f"{PREFIXO_A6}{s}" for s in SEMENTES if _peso_existe(f"{PREFIXO_A6}{s}")]
    return [(i, j) for i in l4 for j in a6]


def quadros_escolha() -> tuple[list[dict], dict[str, dict]]:
    """Quadros da escolha: os 29 da 1029 (M11b) e os 4 com capo de ``EXTRA_ESCOLHA``.

    Returns:
        ``(itens, registros)`` como ``_quadros_m11b``.

    Raises:
        ValueError: se um quadro extra falta no índice ou no gabarito.
    """
    itens, registros = _quadros_m11b()
    indice = {q["id"]: q for q in _ler_json(MAOS_M11B / ARQUIVO_INDICE)["quadros"]}
    gabarito = _ler_json(GABARITO_BRACO_M11B)["quadros"]
    faltam = [i for i in EXTRA_ESCOLHA if i not in indice or i not in gabarito]
    if faltam:
        raise ValueError(f"quadros extras fora do índice ou do gabarito: {faltam}")
    return (
        itens + [indice[i] for i in EXTRA_ESCOLHA],
        {**registros, **{i: gabarito[i] for i in EXTRA_ESCOLHA}},
    )


def escolher() -> dict:
    """Escolhe o par L4 + A6 nos quadros da escolha e grava ``escolha_pesos.json`` (GPU).

    O critério é o da 1029 (``escolher_combinacao``), sem o sinal v2. O par antigo da
    1032 é medido nos mesmos quadros só como referência: ele não concorre.

    Returns:
        ``estagio1``, ``estagio2``, ``tabela``, ``referencia`` e os quadros usados.

    Raises:
        ValueError: se nenhum par L4 + A6 existe.
    """
    combos = combinacoes()
    if not combos:
        raise ValueError("nenhum par L4 + A6 em artefatos/m21")
    itens, registros = quadros_escolha()
    tabela = [avaliar_combinacao(l4, a6, itens, registros) for l4, a6 in combos]
    vencedora = escolher_combinacao(tabela)
    antigo = pesos_da_rodada(RODADA_REFERENCIA)
    escolha = {
        "estagio1": vencedora["estagio1"],
        "estagio2": vencedora["estagio2"],
        "quadros": [item["id"] for item in itens],
        "criterio": "o da 1029: menos falsos que passam, mais certos, menos sinalizados",
        "tabela": tabela,
        "referencia": avaliar_combinacao(
            antigo.estagio1, antigo.estagio2, itens, registros
        ),
    }
    gravar_atomico(ARQUIVO_ESCOLHA, escolha)
    return escolha


def calibracao(linhas: list[dict], previstos: dict[str, dict]) -> dict:
    """A confiança bate com o acerto? Certos por sinal e por terço do S1.

    Args:
        linhas: linhas de ``medir_quadros`` (``id``, ``sinalizado``, ``correto``).
        previstos: ``{id: entrada de previsto.json}`` (com ``S1``).

    Returns:
        ``sem_sinal`` e ``sinalizados`` como ``[certos, total]``, e ``terços_S1``
        (do mais confiante ao menos) com ``[certos, total, S1 máximo]``, só nos quadros
        em que o braço foi achado.
    """
    resultado: dict = {"sem_sinal": [0, 0], "sinalizados": [0, 0]}
    for linha in linhas:
        grupo = resultado["sinalizados" if linha["sinalizado"] else "sem_sinal"]
        grupo[0] += int(linha["correto"])
        grupo[1] += 1
    achados = sorted(
        (
            (previstos[linha["id"]]["S1"], linha["correto"])
            for linha in linhas
            if previstos[linha["id"]]["achou"]
            and previstos[linha["id"]]["S1"] is not None
        ),
        key=lambda par: par[0],
    )
    tercos = []
    for k in range(3):
        fatia = achados[k * len(achados) // 3 : (k + 1) * len(achados) // 3]
        if fatia:
            tercos.append(
                [sum(c for _, c in fatia), len(fatia), round(fatia[-1][0], 4)]
            )
    resultado["tercos_S1"] = tercos
    return resultado


def medir_por_grupo(previsto_doc: dict, gabarito: dict) -> dict:
    """Mede a previsão no conjunto inteiro, nos quadros com capo e nos sem capo.

    Args:
        previsto_doc: ``ordem`` e ``quadros`` (formato de ``previsto.json``).
        gabarito: gabarito do dono.

    Returns:
        ``todos``, ``capo`` e ``sem_capo`` (totais), ``calibracao``, ``linhas`` e
        ``excluidos``.
    """
    medida = medir_quadros(previsto_doc, gabarito, PROXIMA)
    linhas = medida["linhas"]
    com = [linha for linha in linhas if tem_capo(gabarito["quadros"][linha["id"]])]
    sem = [linha for linha in linhas if not tem_capo(gabarito["quadros"][linha["id"]])]
    return {
        "todos": medida["totais"],
        "capo": _totais(com),
        "sem_capo": _totais(sem),
        "calibracao": calibracao(linhas, previsto_doc["quadros"]),
        "linhas": linhas,
        "excluidos": medida["excluidos"],
    }


def _somar(medidas: list[dict], grupo: str, chave: str) -> int:
    """Soma uma contagem de um grupo sobre os conjuntos.

    Args:
        medidas: saídas de ``medir_por_grupo``.
        grupo: ``todos``, ``capo`` ou ``sem_capo``.
        chave: ``falsos_passam_n``, ``entregue_certo``...

    Returns:
        A soma.
    """
    return sum(m[grupo][chave] for m in medidas)


def avaliar_criterios(novo: dict[str, dict], antigo: dict[str, dict]) -> dict:
    """Os três critérios do pré-registro 1037, para o par novo contra o antigo.

    Args:
        novo: ``{conjunto: medir_por_grupo}`` do par escolhido.
        antigo: o mesmo, do par da 1032.

    Returns:
        ``seguranca``, ``capo`` e ``sem_capo`` (bool cada) e os números usados.
    """
    seguranca = all(
        m["todos"]["falsos_passam"] is not None and m["todos"]["falsos_passam"] <= 0.05
        for m in novo.values()
    )
    n, a = list(novo.values()), list(antigo.values())
    capo_falsos = _somar(n, "capo", "falsos_passam_n")
    capo_certos = (
        _somar(n, "capo", "entregue_certo"),
        _somar(a, "capo", "entregue_certo"),
    )
    sem_falsos = (
        _somar(n, "sem_capo", "falsos_passam_n"),
        _somar(a, "sem_capo", "falsos_passam_n"),
    )
    sem_certos = (
        _somar(n, "sem_capo", "entregue_certo"),
        _somar(a, "sem_capo", "entregue_certo"),
    )
    return {
        "seguranca": seguranca,
        "capo": capo_falsos <= 1 and capo_certos[0] >= capo_certos[1],
        "sem_capo": sem_falsos[0] <= sem_falsos[1] + 1
        and sem_certos[0] >= sem_certos[1] - 2,
        "numeros": {
            "falsos_por_conjunto_novo": {
                k: [m["todos"]["falsos_passam_n"], m["todos"]["medidos"]]
                for k, m in novo.items()
            },
            "capo_falsos_novo": capo_falsos,
            "capo_certos_novo_antigo": list(capo_certos),
            "sem_capo_falsos_novo_antigo": list(sem_falsos),
            "sem_capo_certos_novo_antigo": list(sem_certos),
        },
    }


def _prever_conjunto(
    pasta: Path, excluir: dict[str, str], estagio1: str, estagio2: str
) -> dict:
    """Previsão de um conjunto de medida com a regra 1023 e o sinal v2 (GPU).

    Não toca no gabarito: só devolve a previsão.

    Args:
        pasta: pasta do conjunto (``indice.json`` e quadros).
        excluir: ids fora da medida.
        estagio1: localizador.
        estagio2: detector.

    Returns:
        ``ordem`` e ``quadros``, no formato de ``previsto.json``.
    """
    indice = _ler_json(pasta / ARQUIVO_INDICE)
    sub = {"quadros": [q for q in indice["quadros"] if q["id"] not in excluir]}
    previstos = prever_quadros(pasta, sub, estagio1, estagio2, False)
    aplicar_sinal_nut_v2(previstos, pasta, sub)
    return {
        "pesos": {"estagio1": estagio1, "estagio2": estagio2, "sinal_nut": "v2"},
        "ordem": [q["id"] for q in sub["quadros"]],
        "quadros": previstos,
    }


def _resumo(medidas: dict[str, dict]) -> str:
    """Linha de texto com os totais de um par em cada conjunto.

    Args:
        medidas: ``{conjunto: medir_por_grupo}``.

    Returns:
        O texto.
    """
    partes = []
    for nome, m in medidas.items():
        t, c = m["todos"], m["capo"]
        partes.append(
            f"{nome}: certos {t['entregue_certo']}/{t['com_braco']}, falsos "
            f"{t['falsos_passam_n']}/{t['medidos']}, sinal {t['sinalizados']} | capo "
            f"certos {c['entregue_certo']}/{c['com_braco']}, falsos {c['falsos_passam_n']}"
        )
    return " ; ".join(partes)


def medir() -> dict:
    """Mede o par escolhido, o antigo e os 9 pares nos conjuntos de medida (GPU).

    Grava ``previsto_<conjunto>_<par>.json`` e ``medida.json`` em ``MAOS_M37``.

    Returns:
        O conteúdo de ``medida.json``.
    """
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    antigo = pesos_da_rodada(RODADA_REFERENCIA)
    pares = {
        "novo": (escolha["estagio1"], escolha["estagio2"]),
        "antigo": (antigo.estagio1, antigo.estagio2),
    }
    for l4, a6 in combinacoes():
        pares.setdefault(f"{l4}+{a6}", (l4, a6))
    resultado: dict = {"pares": {k: list(v) for k, v in pares.items()}, "medidas": {}}
    cache: dict[tuple[str, str, str], dict] = {}
    for rotulo, (e1, e2) in pares.items():
        resultado["medidas"][rotulo] = {}
        for nome, pasta, gabarito, excluir in CONJUNTOS_MEDIDA:
            chave = (nome, e1, e2)
            if chave not in cache:
                cache[chave] = _prever_conjunto(pasta, excluir, e1, e2)
                gravar_atomico(
                    MAOS_M37 / f"previsto_{nome}_{e1}+{e2}.json", cache[chave]
                )
            resultado["medidas"][rotulo][nome] = medir_por_grupo(
                cache[chave], _ler_json(gabarito)
            )
        print(f"{rotulo}: {_resumo(resultado['medidas'][rotulo])}", flush=True)
    resultado["criterios"] = avaliar_criterios(
        resultado["medidas"]["novo"], resultado["medidas"]["antigo"]
    )
    resultado["sementes"] = _variacao(
        {k: v for k, v in resultado["medidas"].items() if "+" in k}
    )
    gravar_atomico(ARQUIVO_MEDIDA, resultado)
    print(json.dumps(resultado["criterios"], ensure_ascii=False, indent=1))
    return resultado


def _variacao(por_par: dict[str, dict]) -> dict:
    """Média e amplitude, entre os pares L4 + A6, de certos e falsos por conjunto.

    Args:
        por_par: ``{par: {conjunto: medir_por_grupo}}``.

    Returns:
        ``{conjunto: {grupo: {chave: [média, mínimo, máximo]}}}``.
    """
    resultado: dict = {}
    if not por_par:
        return resultado
    conjuntos = next(iter(por_par.values())).keys()
    for nome in conjuntos:
        resultado[nome] = {}
        for grupo in ("todos", "capo", "sem_capo"):
            resultado[nome][grupo] = {}
            for chave in ("entregue_certo", "falsos_passam_n", "sinalizados"):
                valores = [m[nome][grupo][chave] for m in por_par.values()]
                resultado[nome][grupo][chave] = [
                    round(statistics.mean(valores), 2),
                    min(valores),
                    max(valores),
                ]
    return resultado


def _parser() -> argparse.ArgumentParser:
    """Parser da CLI.

    Returns:
        Parser com ``contar``, ``folhas``, ``smoke``, ``treinar``, ``escolher`` e
        ``medir``.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("contar", help="conta as fontes (sem GPU)")
    sub.add_parser("folhas", help="folhas do alvo nos quadros com capo")
    sub.add_parser("smoke", help="50 passos de cada estágio, sem gravar")
    treino = sub.add_parser("treinar", help="treino L4 ou A6")
    treino.add_argument("--estagio", choices=tuple(ESTIMATIVA), required=True)
    treino.add_argument("--semente", type=int, required=True)
    sub.add_parser("escolher", help="escolhe o par na M11b (GPU)")
    sub.add_parser("medir", help="mede na M36 e na M25 prova (GPU)")
    return parser


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    args = _parser().parse_args()
    if args.comando == "contar":
        contar()
    elif args.comando == "folhas":
        folhas()
    elif args.comando == "smoke":
        smoke()
    elif args.comando == "treinar":
        treinar(args.estagio, args.semente)
    elif args.comando == "escolher":
        escolha = escolher()
        print(json.dumps({k: escolha[k] for k in ("estagio1", "estagio2")}))
    else:
        medir()
    return 0


if __name__ == "__main__":
    sys.exit(main())
