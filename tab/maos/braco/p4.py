"""Rodada 1028, P4: fontes novas (m26, m27 e N) e os treinos L3 e A4.

L3 (estágio 1, ``L3_todos_s<k>``): R + G + C + m26 + m27 + N. Sai o que não tem violão
de 6 cordas (``7 cordas`` na observação, e os ids excluídos da prova da 1025) e o quadro
com nut ``fora``, como no C.

A4 (estágio 2, ``A4_100_todos_s<k>``): a mistura A3 (S + R), com os R aumentados pelas
marcas completas de m26, m27 e N. Sai o que não tem violão de 6 cordas e o braço
``nao``. Os quadros com nut ``fora`` saem: ``eixo_da_faixa`` e ``mapas_alvo`` exigem o
nut, e o código do estágio 2 não suporta nut ausente sem remendo. Quantos saíram fica no
json do peso.

Pré-registro: ``docs/rodadas/1028-um-braco-consenso-e-retreino.md``.

CLI: ``python -m tab.maos_braco_p4 {smoke,treinar,folhas}``.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import cv2
import numpy as np

from tab.comum.caminhos import (
    GABARITO_BRACO_M25_PROVA,
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    MAOS_M21,
    MAOS_M25,
    MAOS_M26,
    MAOS_M27,
)
from tab.maos.braco.detector import (
    MISTURA,
    PASSOS,
    _Itens,
    _ler_json,
    _pool_r,
    _pool_s,
    _salvar_pesos,
    _sequencia,
    _trava_gpu,
    _treinar,
)
from tab.maos.braco.localizador import (
    QUADRO_EXCLUIDO_PROVA,
    _grava_folha,
    _indice_por_id,
    _registros_final2,
    _treinar_localizador,
    _utilizavel,
)
from tab.maos.braco.localizador import (
    _sequencia as _sequencia_localizador,
)
from tab.maos.braco.tempo import marcas_do_registro

#: Fontes novas: (origem, gabarito, pasta com indice.json e quadros/, ids excluídos).
#: N é a prova do dono da 1025 (``braco_m25_prova.json``); q08 saiu nela (guitarra).
FONTES_NOVAS = (
    ("M26", GABARITO_BRACO_M26, MAOS_M26, ()),
    ("M27", GABARITO_BRACO_M27, MAOS_M27, ()),
    ("N", GABARITO_BRACO_M25_PROVA, MAOS_M25 / "prova", (QUADRO_EXCLUIDO_PROVA,)),
)
#: Marca do dono para violão de 7 cordas (regra da 1027).
MARCA_7_CORDAS = "7 cordas"
#: Semente da folha da rodada.
SEMENTE_P4 = "20261028:p4"
ARQUIVO_FOLHA_L3 = MAOS_M21 / "l3_folha.jpg"
ARQUIVO_FOLHA_A4 = MAOS_M21 / "a4_folha.jpg"
#: Cores dos 4 canais do estágio 2 na folha (BGR): corda 1, corda 6, trastes, nut.
CORES_A4 = ((0, 0, 255), (255, 0, 0), (0, 255, 255), (0, 255, 0))
#: Quadros por folha (3 colunas, 4 linhas).
QUADROS_FOLHA = 12


def _do_dono(
    origem: str, gabarito: Path, pasta: Path, excluir: tuple[str, ...]
) -> tuple[list[dict], list[dict], dict]:
    """Quadros de uma fonte do dono, para o estágio 1 e para o estágio 2.

    Args:
        origem: rótulo da fonte (``M26``, ``M27`` ou ``N``).
        gabarito: arquivo ``braco_*.json`` do dono.
        pasta: pasta com ``indice.json`` (canal e png por id).
        excluir: ids que saem por decisão de rodada.

    Returns:
        ``(estagio1, estagio2, relatorio)``: registros do L3 (com ``marcas``), entradas
        do A4 (com ``caminho`` e ``registro``) e a contagem do que saiu e por quê.
    """
    indice = _indice_por_id(pasta / "indice.json")
    quadros = _ler_json(gabarito)["quadros"]
    relatorio = {
        "total": len(quadros),
        "sem_braco": 0,
        "excluidos_pelo_dono": 0,
        "excluidos_7_cordas": 0,
        "incompletos": 0,
        "nut_fora": 0,
        "usados": 0,
    }
    estagio1: list[dict] = []
    estagio2: list[dict] = []
    for id_quadro, registro in quadros.items():
        if registro.get("braco") != "sim":
            relatorio["sem_braco"] += 1
            continue
        if id_quadro in excluir:
            relatorio["excluidos_pelo_dono"] += 1
            continue
        if MARCA_7_CORDAS in str(registro.get("obs") or ""):
            relatorio["excluidos_7_cordas"] += 1
            continue
        marcas = marcas_do_registro(registro)
        if marcas is None:
            relatorio["incompletos"] += 1
            continue
        if marcas.nut is None:
            relatorio["nut_fora"] += 1
            continue
        if not _utilizavel(marcas):
            relatorio["incompletos"] += 1
            continue
        entrada = indice[id_quadro]
        caminho = str(pasta / entrada["png"])
        id_global = f"{origem}-{id_quadro}"
        relatorio["usados"] += 1
        estagio1.append(
            {
                "id": id_global,
                "origem": origem,
                "canal": entrada["canal"],
                "caminho": caminho,
                "marcas": marcas,
            }
        )
        estagio2.append(
            {
                "id": id_global,
                "origem": origem,
                "canal": entrada["canal"],
                "caminho": caminho,
                "registro": registro,
            }
        )
    return estagio1, estagio2, relatorio


def fontes_novas() -> tuple[list[dict], list[dict], dict]:
    """Fontes novas da 1028 (m26, m27 e N), com o relatório de cada uma.

    Returns:
        ``(estagio1, estagio2, relatorios)``, com ``relatorios`` por origem.
    """
    e1: list[dict] = []
    e2: list[dict] = []
    relatorios: dict[str, dict] = {}
    for origem, gabarito, pasta, excluir in FONTES_NOVAS:
        a, b, rel = _do_dono(origem, gabarito, pasta, excluir)
        e1 += a
        e2 += b
        relatorios[origem] = rel
    return e1, e2, relatorios


def registros_l3() -> tuple[list[dict], dict]:
    """Treino do estágio 1 da 1028: R + G + C + m26 + m27 + N.

    Returns:
        ``(registros, relatorios)``: os registros do ``_sequencia`` do localizador e o
        relatório das fontes novas.
    """
    novos, _, relatorios = fontes_novas()
    return _registros_final2() + novos, relatorios


def _contagem(registros: list[dict]) -> dict[str, int]:
    """Quadros por fonte (``origem``), na ordem de aparição.

    Args:
        registros: registros com a chave ``origem``.

    Returns:
        Dicionário origem -> quantidade.
    """
    contagem: dict[str, int] = {}
    for registro in registros:
        contagem[registro["origem"]] = contagem.get(registro["origem"], 0) + 1
    return contagem


def pool_a4() -> tuple[list[dict], list[dict], dict]:
    """Pool R do estágio 2 da 1028: os R de ``_pool_r`` mais m26, m27 e N.

    Returns:
        ``(pool, novos, relatorios)``: pool com ``caminho`` e ``registro`` (o formato
        que ``_sequencia`` lê), as entradas novas e o relatório de cada fonte.
    """
    _, novos, relatorios = fontes_novas()
    pool = list(_pool_r()) + [
        {"caminho": e["caminho"], "registro": e["registro"], "canal": e["canal"]}
        for e in novos
    ]
    return pool, novos, relatorios


def _sequencia_a4(
    pool_s: list[tuple[str, dict]], pool: list[dict], passos: int, etiqueta: str
) -> list[tuple]:
    """Sequência do A4: a mistura A3 de S e R, com a semente da etiqueta.

    Args:
        pool_s: quadros S (de ``_pool_s``).
        pool: pool R aumentado (de ``pool_a4``).
        passos: número de passos.
        etiqueta: identifica o treino para a semente do sorteio.

    Returns:
        Lista de ``passos * LOTE`` itens para ``_Itens``.
    """
    return _sequencia(pool_s, pool, passos, MISTURA["A3"], etiqueta)


def treinar(
    estagio: str, semente: int, passos: int = PASSOS, gravar: bool = True
) -> int:
    """Treina L3 (estágio 1) ou A4 (estágio 2) e grava o peso com a contagem por fonte.

    A GPU é reservada por ``_trava_gpu``. Com ``gravar=False`` é o teste curto (não
    grava peso).

    Args:
        estagio: ``l3`` ou ``a4``.
        semente: semente do treino.
        passos: passos (``PASSOS`` no treino oficial).
        gravar: se grava ``artefatos/m21/<nome>.pt`` e o json.

    Returns:
        0 ao terminar.

    Raises:
        ValueError: se ``estagio`` não é ``l3`` nem ``a4``.
    """
    if estagio == "l3":
        return _treinar_l3(semente, passos, gravar)
    if estagio == "a4":
        return _treinar_a4(semente, passos, gravar)
    raise ValueError(f"estágio desconhecido: {estagio}")


def _treinar_l3(semente: int, passos: int, gravar: bool) -> int:
    """Treino do estágio 1 (L3). Ver ``treinar``.

    Args:
        semente: semente do treino.
        passos: passos do treino.
        gravar: se grava o peso.

    Returns:
        0 ao terminar.
    """
    registros, relatorios = registros_l3()
    fontes = _contagem(registros)
    nome = f"L3_todos_s{semente}"
    itens = _sequencia_localizador(registros, passos, nome)
    with _trava_gpu():
        modelo, perdas, segundos = _treinar_localizador(itens, passos, semente)
        if gravar:
            _salvar_pesos(
                modelo,
                nome,
                {
                    "nome": nome,
                    "comando": (
                        "python -m tab.maos_braco_p4 treinar --estagio l3 "
                        f"--semente {semente}"
                    ),
                    "semente": semente,
                    "passos": passos,
                    "fontes": "R + G + C + M26 + M27 + N",
                    "quadros_por_fonte": fontes,
                    "quadros_de_treino": len(registros),
                    "novas_fontes": relatorios,
                    "tempo_treino_s": segundos,
                    "perdas": perdas,
                },
            )
    print(
        f"{nome}: {passos} passos, quadros {fontes}, perda final {perdas[-1]:.4f}, "
        f"{segundos:.0f} s",
        file=sys.stderr,
    )
    return 0


def _treinar_a4(semente: int, passos: int, gravar: bool) -> int:
    """Treino do estágio 2 (A4). Ver ``treinar``.

    Args:
        semente: semente do treino.
        passos: passos do treino.
        gravar: se grava o peso.

    Returns:
        0 ao terminar.
    """
    pool_s = _pool_s()
    pool, novos, relatorios = pool_a4()
    fontes = {"S": len(pool_s), "R": len(pool) - len(novos)}
    fontes.update(_contagem(novos))
    nome = f"A4_100_todos_s{semente}"
    sequencia = _sequencia_a4(pool_s, pool, passos, f"a4:{semente}:{passos}")
    with _trava_gpu():
        modelo, perdas, segundos = _treinar(sequencia, passos, semente)
        if gravar:
            _salvar_pesos(
                modelo,
                nome,
                {
                    "nome": nome,
                    "exp": "A4",
                    "fracao": "100",
                    "dobra": "todos",
                    "canal_deixado_fora": None,
                    "semente": semente,
                    "passos": passos,
                    "quadros_por_fonte": fontes,
                    "novas_fontes": relatorios,
                    "nut_fora_excluido": sum(
                        r["nut_fora"] for r in relatorios.values()
                    ),
                    "tamanho_s": len(pool_s),
                    "tamanho_r": len(pool),
                    "tempo_treino_s": segundos,
                    "perdas": perdas,
                    "comando": (
                        "python -m tab.maos_braco_p4 treinar --estagio a4 "
                        f"--semente {semente}"
                    ),
                },
            )
    print(
        f"{nome}: {passos} passos, quadros {fontes}, perda final {perdas[-1]:.4f}, "
        f"{segundos:.0f} s",
        file=sys.stderr,
    )
    return 0


def _folha_a4(entradas: list[dict], destino: Path) -> None:
    """Folha do estágio 2: 12 faixas com os 4 canais do alvo sobre a faixa.

    Args:
        entradas: 12 entradas com ``caminho``, ``registro``, ``id`` e ``canal``.
        destino: arquivo JPEG da folha.
    """
    itens = [(e["caminho"], e["registro"], i, None) for i, e in enumerate(entradas)]
    dados = _Itens(itens)
    quadros = []
    for i, entrada in enumerate(entradas):
        rgb, alvo = dados[i]
        bgr = np.ascontiguousarray(rgb[..., ::-1]).astype(np.float32)
        for canal in range(len(CORES_A4)):
            mascara = alvo[canal] > 127
            cor = np.array(CORES_A4[canal], dtype=np.float32)
            bgr[mascara] = 0.45 * bgr[mascara] + 0.55 * cor
        imagem = np.clip(bgr, 0, 255).astype(np.uint8)
        cv2.putText(
            imagem,
            f"{entrada['id']} {entrada['canal'][:18]}",
            (8, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
        quadros.append(imagem)
    linhas = [np.hstack(quadros[k : k + 3]) for k in range(0, QUADROS_FOLHA, 3)]
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"folha gravada em {destino}", file=sys.stderr)


def folhas() -> None:
    """Folhas de alvo das fontes novas: estágio 1 (L3) e estágio 2 (A4).

    As 12 amostras saem só das fontes novas (m26, m27 e N), com semente fixa.
    """
    novos1, novos2, _ = fontes_novas()
    rng = random.Random(f"{SEMENTE_P4}:folha")
    sorteio1 = rng.sample(range(len(novos1)), min(QUADROS_FOLHA, len(novos1)))
    _grava_folha(
        [novos1[i] for i in sorteio1],
        [rng.getrandbits(31) for _ in sorteio1],
        ARQUIVO_FOLHA_L3,
    )
    sorteio2 = rng.sample(range(len(novos2)), min(QUADROS_FOLHA, len(novos2)))
    _folha_a4([novos2[i] for i in sorteio2], ARQUIVO_FOLHA_A4)


def smoke(passos: int = 50) -> int:
    """Teste curto dos dois estágios (sem gravar peso) e as duas folhas.

    Args:
        passos: passos do teste.

    Returns:
        0 ao terminar.
    """
    folhas()
    treinar("l3", 1, passos, gravar=False)
    treinar("a4", 1, passos, gravar=False)
    return 0


def _parser() -> argparse.ArgumentParser:
    """Parser da CLI.

    Returns:
        Parser com ``smoke``, ``treinar`` e ``folhas``.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("smoke", help="teste de 50 passos dos dois estágios e folhas")
    sub.add_parser("folhas", help="folhas de alvo das fontes novas")
    treino = sub.add_parser("treinar", help="treino L3 ou A4")
    treino.add_argument("--estagio", choices=("l3", "a4"), required=True)
    treino.add_argument("--semente", type=int, required=True)
    return parser


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    args = _parser().parse_args()
    if args.comando == "smoke":
        return smoke()
    if args.comando == "folhas":
        folhas()
        return 0
    return treinar(args.estagio, args.semente)


if __name__ == "__main__":
    sys.exit(main())
