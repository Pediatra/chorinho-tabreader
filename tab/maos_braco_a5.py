"""Rodada 1031, A5: retreino do estágio 2 com os quadros de nut fora da imagem.

Pré-registro: ``docs/rodadas/1031-nut-fora-por-vizinhos-e-juncao.md``.

O A5 é o A4 (``tab.maos_braco_p4``) com um acréscimo: os quadros cujo rótulo do dono tem
o nut ``fora`` entram no treino, com o nut ausente do alvo. No A4 eles saem
(``relatorio["nut_fora"]``). Para eles o eixo vem das pontas das cordas
(``eixo_sem_nut``), o alvo não tem o canal do nut e as cordas começam no x de início da
faixa (``mapas_alvo_sem_nut``). Os quadros com nut seguem exatamente como no A4.

CLI: ``python -m tab.maos_braco_a5 {treinar,smoke}``.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import cv2
import numpy as np

from .caminhos import MAOS_M21
from .maos_braco_detector import (
    CANAIS_ALVO,
    CANAL_CORDA1,
    CANAL_CORDA6,
    CANAL_TRASTES,
    PASSOS,
    SIGMA_CRISTA_PX,
    _distancia_reta,
    _distancia_segmento,
    _imagem,
    _Itens,
    _ler_json,
    _ponto_na_corda,
    _pool_r,
    _pool_s,
    _salvar_pesos,
    _trava_gpu,
    _treinar,
    aumentar,
)
from .maos_braco_faixa import (
    ALTURA_FAIXA,
    LARGURA_FAIXA,
    aplicar_matriz,
    matriz_da_faixa,
    perturbar,
    recortar,
    rotulo_na_faixa,
)
from .maos_braco_localizador import _indice_por_id, _utilizavel
from .maos_braco_p4 import (
    CORES_A4,
    FONTES_NOVAS,
    MARCA_7_CORDAS,
    QUADROS_FOLHA,
    _contagem,
    _sequencia_a4,
)
from .maos_braco_tempo import Marcas, marcas_do_registro
from .maos_braco_video import eixo_sem_nut

#: Semente da amostra da folha de A5 (sorteio fixo entre os quadros de nut fora).
SEMENTE_A5 = "20261031:a5"
#: Trastes numerados mínimos para um quadro de nut fora entrar no A5.
TRASTES_NUT_FORA_MINIMOS = 3
ARQUIVO_FOLHA_A5 = MAOS_M21 / "a5_folha.jpg"


class ItensA5(_Itens):
    """Itens do A5: como ``_Itens``, mas aceita quadros com o nut fora da imagem.

    Quadros com nut usam a leitura do ``_Itens``. Sem nut, o eixo sai das pontas das
    cordas (``eixo_sem_nut``), a faixa é retificada a partir do lado das cordas mais
    perto da borda, e o alvo vem de ``mapas_alvo_sem_nut``.
    """

    def __getitem__(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        """Amostra ``i``: faixa RGB uint8 ``(192, 1024, 3)`` e alvo uint8 ``(4, 192, 1024)``.

        Args:
            i: índice do item.

        Returns:
            ``(faixa, alvo)`` prontos para a GPU, com os valores quantizados em uint8.

        Raises:
            ValueError: se o quadro não tem marcas completas.
        """
        caminho, registro, semente_perturbacao, semente_aumento = self.itens[i]
        marcas = marcas_do_registro(registro)
        if marcas is None:
            raise ValueError(f"{caminho} sem marcas completas")
        if marcas.nut is not None:
            return super().__getitem__(i)
        img = _imagem(Path(caminho))
        altura, largura = img.shape[:2]
        eixo = eixo_sem_nut(
            marcas.corda1.tolist(), marcas.corda6.tolist(), largura, altura
        )
        eixo_p = perturbar(eixo, random.Random(semente_perturbacao))
        matriz = matriz_da_faixa(eixo_p)
        faixa = recortar(img, matriz)
        rotulo = rotulo_na_faixa(marcas, matriz)
        x_inicio = float(aplicar_matriz(matriz, eixo_p[0])[0])
        alvo = mapas_alvo_sem_nut(rotulo, x_inicio)
        if semente_aumento is None:
            faixa_f = faixa.astype(np.float32) / 255.0
        else:
            faixa_f, alvo = aumentar(faixa, alvo, random.Random(semente_aumento))
        rgb = np.ascontiguousarray(
            (faixa_f[..., ::-1] * 255.0).round().astype(np.uint8)
        )
        alvo_u8 = np.ascontiguousarray((alvo * 255.0).round().astype(np.uint8))
        return rgb, alvo_u8


def mapas_alvo_sem_nut(rotulo: dict, x_inicio: float) -> np.ndarray:
    """Alvo de 4 canais (192 x 1024) para uma faixa sem o nut.

    Canais 0 e 1: crista gaussiana (sigma de 2 px) sobre a reta da corda 1 e da corda 6,
    a partir de ``x_inicio`` (zero antes). Canal 2: uma crista para cada traste numerado,
    sobre o segmento que liga a corda 1 à corda 6 no x do traste. Canal 3 (nut): zeros.

    Args:
        rotulo: dicionário de ``rotulo_na_faixa``, sem traste de número 0.
        x_inicio: x, na faixa, onde as cordas começam (o lado das pontas mais perto da
            borda). Valores negativos são tratados como 0.

    Returns:
        Array float32 ``(4, 192, 1024)`` com valores em [0, 1].

    Raises:
        ValueError: se o rótulo tem o nut (número 0); use ``mapas_alvo`` nesse caso.
    """
    if any(numero == 0 for numero, _x, _y in rotulo["trastes"]):
        raise ValueError("rótulo com nut: use mapas_alvo")
    x_corte = max(0.0, x_inicio)
    ys, xs = np.mgrid[0:ALTURA_FAIXA, 0:LARGURA_FAIXA].astype(np.float64)
    dentro = xs >= x_corte
    dois_sigma = 2.0 * SIGMA_CRISTA_PX**2
    alvo = np.zeros((CANAIS_ALVO, ALTURA_FAIXA, LARGURA_FAIXA), dtype=np.float64)
    for canal, chave in ((CANAL_CORDA1, "corda1"), (CANAL_CORDA6, "corda6")):
        crista = np.exp(-(_distancia_reta(xs, ys, rotulo[chave]) ** 2) / dois_sigma)
        alvo[canal] = np.where(dentro, crista, 0.0)
    for _numero, x, _y in rotulo["trastes"]:
        a = _ponto_na_corda(rotulo["corda1"], x)
        b = _ponto_na_corda(rotulo["corda6"], x)
        crista = np.exp(-(_distancia_segmento(xs, ys, a, b) ** 2) / dois_sigma)
        alvo[CANAL_TRASTES] = np.maximum(alvo[CANAL_TRASTES], crista)
    return alvo.astype(np.float32)


def _nut_fora_utilizavel(marcas: Marcas) -> bool:
    """Se um quadro sem nut tem trastes numerados suficientes e um eixo válido.

    O eixo sem nut não depende do tamanho do quadro quando é degenerado (os dois lados
    têm o mesmo comprimento), então a checagem usa um quadro de referência de 1 px.

    Args:
        marcas: marcas do quadro, com ``nut`` None.

    Returns:
        True quando o quadro entra no A5.
    """
    if len(marcas.trastes) < TRASTES_NUT_FORA_MINIMOS:
        return False
    try:
        eixo_sem_nut(marcas.corda1.tolist(), marcas.corda6.tolist(), 1, 1)
    except ValueError:
        return False
    return True


def _do_dono_a5(
    origem: str, gabarito: Path, pasta: Path, excluir: tuple[str, ...]
) -> tuple[list[dict], dict]:
    """Entradas do estágio 2 de uma fonte do dono, com nut fora incluído.

    Mesmas exclusões de ``_do_dono`` (braço, ids excluídos, "7 cordas", marcas
    incompletas). A diferença: quadro com ``marcas.nut`` None entra quando tem pelo menos
    ``TRASTES_NUT_FORA_MINIMOS`` trastes numerados (contado em ``nut_fora_incluido``).

    Args:
        origem: rótulo da fonte (``M26``, ``M27`` ou ``N``).
        gabarito: arquivo ``braco_*.json`` do dono.
        pasta: pasta com ``indice.json`` (canal e png por id).
        excluir: ids que saem por decisão de rodada.

    Returns:
        ``(entradas, relatorio)``: entradas com ``id``, ``origem``, ``canal``,
        ``caminho`` e ``registro``, e a contagem do que saiu e por quê.
    """
    indice = _indice_por_id(pasta / "indice.json")
    quadros = _ler_json(gabarito)["quadros"]
    relatorio = {
        "total": len(quadros),
        "sem_braco": 0,
        "excluidos_pelo_dono": 0,
        "excluidos_7_cordas": 0,
        "incompletos": 0,
        "nut_fora_incluido": 0,
        "usados": 0,
    }
    entradas: list[dict] = []
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
            if not _nut_fora_utilizavel(marcas):
                relatorio["incompletos"] += 1
                continue
            relatorio["nut_fora_incluido"] += 1
        elif not _utilizavel(marcas):
            relatorio["incompletos"] += 1
            continue
        entrada = indice[id_quadro]
        relatorio["usados"] += 1
        entradas.append(
            {
                "id": f"{origem}-{id_quadro}",
                "origem": origem,
                "canal": entrada["canal"],
                "caminho": str(pasta / entrada["png"]),
                "registro": registro,
            }
        )
    return entradas, relatorio


def fontes_a5() -> tuple[list[dict], dict]:
    """Entradas do estágio 2 das fontes novas da 1028, com nut fora incluído (A5).

    Returns:
        ``(entradas, relatorios)``: as entradas de todas as fontes e o relatório de cada
        uma, por origem.
    """
    entradas: list[dict] = []
    relatorios: dict[str, dict] = {}
    for origem, gabarito, pasta, excluir in FONTES_NOVAS:
        novas, relatorio = _do_dono_a5(origem, gabarito, pasta, excluir)
        entradas += novas
        relatorios[origem] = relatorio
    return entradas, relatorios


def _pool_e_fontes() -> tuple[list[dict], list[dict], dict]:
    """Pool R do A5: os R de ``_pool_r`` mais as entradas de ``fontes_a5``.

    Returns:
        ``(pool, novos, relatorios)``: pool com ``caminho``, ``registro`` e ``canal``
        (o formato que ``_sequencia`` lê), as entradas novas e o relatório por fonte.
    """
    novos, relatorios = fontes_a5()
    pool = list(_pool_r()) + [
        {"caminho": e["caminho"], "registro": e["registro"], "canal": e["canal"]}
        for e in novos
    ]
    return pool, novos, relatorios


def pool_a5() -> list[dict]:
    """Pool R do estágio 2 do A5 (ver ``_pool_e_fontes``).

    Returns:
        Lista de dicionários com ``caminho``, ``registro`` e ``canal``.
    """
    pool, _novos, _relatorios = _pool_e_fontes()
    return pool


def treinar_a5(semente: int, passos: int = PASSOS, gravar: bool = True) -> int:
    """Treina o A5 (estágio 2) e grava o peso com a contagem por fonte.

    A GPU é reservada por ``_trava_gpu``. Com ``gravar=False`` é o teste curto, que não
    grava peso.

    Args:
        semente: semente do treino.
        passos: passos (``PASSOS`` no treino oficial).
        gravar: se grava ``artefatos/m21/A5_100_todos_s<semente>.pt`` e o json.

    Returns:
        0 ao terminar.
    """
    pool_s = _pool_s()
    pool, novos, relatorios = _pool_e_fontes()
    fontes = {"S": len(pool_s), "R": len(pool) - len(novos)}
    fontes.update(_contagem(novos))
    nome = f"A5_100_todos_s{semente}"
    sequencia = _sequencia_a4(pool_s, pool, passos, f"a5:{semente}:{passos}")
    with _trava_gpu():
        modelo, perdas, segundos = _treinar(
            sequencia, passos, semente, classe_itens=ItensA5
        )
        if gravar:
            _salvar_pesos(
                modelo,
                nome,
                {
                    "nome": nome,
                    "exp": "A5",
                    "fracao": "100",
                    "dobra": "todos",
                    "canal_deixado_fora": None,
                    "semente": semente,
                    "passos": passos,
                    "quadros_por_fonte": fontes,
                    "novas_fontes": relatorios,
                    "nut_fora_incluido": sum(
                        r["nut_fora_incluido"] for r in relatorios.values()
                    ),
                    "tamanho_s": len(pool_s),
                    "tamanho_r": len(pool),
                    "tempo_treino_s": segundos,
                    "perdas": perdas,
                    "comando": (
                        f"python -m tab.maos_braco_a5 treinar --semente {semente}"
                    ),
                },
            )
    print(
        f"{nome}: {passos} passos, quadros {fontes}, perda final {perdas[-1]:.4f}, "
        f"{segundos:.0f} s",
        file=sys.stderr,
    )
    return 0


def folha_a5(destino: Path = ARQUIVO_FOLHA_A5) -> None:
    """Folha do A5: até 12 quadros de nut fora, com os canais do alvo sobre a faixa.

    Os quadros são sorteados com semente fixa entre os de nut fora. Se há menos de 12,
    saem todos. Cada canal do alvo é pintado com a cor de ``CORES_A4``.

    Args:
        destino: arquivo JPEG da folha.

    Raises:
        ValueError: se nenhum quadro de nut fora entra no A5.
    """
    entradas, _relatorios = fontes_a5()
    sem_nut = [
        e
        for e in entradas
        if (marcas := marcas_do_registro(e["registro"])) is not None
        and marcas.nut is None
    ]
    if not sem_nut:
        raise ValueError("nenhum quadro de nut fora entra no A5")
    rng = random.Random(SEMENTE_A5)
    sorteio = sorted(rng.sample(range(len(sem_nut)), min(QUADROS_FOLHA, len(sem_nut))))
    escolhidos = [sem_nut[i] for i in sorteio]
    itens = [(e["caminho"], e["registro"], i, None) for i, e in enumerate(escolhidos)]
    dados = ItensA5(itens)
    quadros = []
    for i, entrada in enumerate(escolhidos):
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
    while len(quadros) % 3:
        quadros.append(np.zeros_like(quadros[0]))
    linhas = [np.hstack(quadros[k : k + 3]) for k in range(0, len(quadros), 3)]
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"folha gravada em {destino}", file=sys.stderr)


def smoke() -> int:
    """Teste curto do A5: a folha de nut fora e 20 passos sem gravar peso.

    Returns:
        0 ao terminar.
    """
    folha_a5()
    treinar_a5(1, 20, gravar=False)
    return 0


def _parser() -> argparse.ArgumentParser:
    """Parser da CLI.

    Returns:
        Parser com ``treinar`` e ``smoke``.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("smoke", help="folha de nut fora e 20 passos sem gravar peso")
    treino = sub.add_parser("treinar", help="treino do A5 (estágio 2)")
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
    return treinar_a5(args.semente)


if __name__ == "__main__":
    sys.exit(main())
