"""Braço quadro a quadro (M11a): erros da grade levada do quadro-chave ao alvo.

Um quadro-chave marcado pelo dono (nut, trastes, cordas 1 e 6) é levado a um
quadro alvo por uma homografia. Aqui se medem os erros dessa previsão contra as
marcas do dono no alvo, nas três métricas da rodada 1015: pestana, pior traste e
erro perpendicular às cordas. A classificação (certo, impreciso, falso, nao_achou)
segue os critérios da mesma rodada.

A CLI ``python -m tab.maos_braco_tempo base`` mede a linha de base, que é a grade
fixa do quadro-chave (homografia identidade), e grava o resultado em
``MAOS_M11``. Com ``--teste`` usa os pares de teste; isso não deve ser rodado antes
de as regras estarem congeladas.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

import numpy as np

from tab.comum.caminhos import GABARITO_BRACO, MAOS_M11
from tab.maos.braco.gabarito import numerar_trastes, registro_completo
from tab.maos.braco.geometria import eixo_do_braco

#: Limite (em casas ou vãos) abaixo do qual a medida é "certa".
LIMITE_CERTO = 0.25
#: Limite (em casas ou vãos) acima do qual a medida é "falsa".
LIMITE_FALSO = 0.5
#: Intervalos entre as 6 cordas: vão de corda = distância entre as cordas 1 e 6 / 5.
INTERVALOS_CORDAS = 5
#: Trastes (1 a 12) que entram no pior traste.
TRASTE_MAXIMO = 12

#: Pares (quadro-chave, alvo) de desenvolvimento: sky guitar, com mais de uma marca.
PARES_DESENVOLVIMENTO = (
    ("q02", "q24"),
    ("q02", "q25"),
    ("q16", "q26"),
    ("q16", "q27"),
    ("q21", "q28"),
    ("q21", "q29"),
    ("q23", "q30"),
    ("q23", "q31"),
)

#: Grupos de teste: (quadro-chave, primeiro alvo, último alvo), por canal.
_GRUPOS_TESTE = (
    ("q01", 37, 41),
    ("q04", 42, 46),
    ("q05", 47, 51),
    ("q06", 52, 56),
    ("q08", 57, 61),
    ("q13", 62, 66),
)
#: Pares (quadro-chave, alvo) de teste. Não rodar antes de a regra estar congelada.
PARES_TESTE = tuple(
    (chave, f"q{n:02d}")
    for chave, primeiro, ultimo in _GRUPOS_TESTE
    for n in range(primeiro, ultimo + 1)
)


@dataclasses.dataclass(frozen=True, eq=False)
class Marcas:
    """Marcas do braço de um quadro, em pixels.

    Attributes:
        nut: ponto do nut ``(2,)``, ou ``None`` quando o nut está fora do quadro.
        trastes: número do traste -> ponto ``(2,)``, só os trastes com número.
        corda1: dois pontos ``(2, 2)`` da corda 1.
        corda6: dois pontos ``(2, 2)`` da corda 6.
    """

    nut: np.ndarray | None
    trastes: dict[int, np.ndarray]
    corda1: np.ndarray
    corda6: np.ndarray


def marcas_do_registro(registro: dict) -> Marcas | None:
    """Marcas de um quadro do gabarito, se ele tem braço e está completo.

    Args:
        registro: resposta do quadro no gabarito (``braco``, ``nut``, ``trastes``...).

    Returns:
        As marcas, ou ``None`` se o braço não é ``sim``/``parcial`` ou o registro não
        está completo.
    """
    if registro.get("braco") not in ("sim", "parcial"):
        return None
    if not registro_completo(registro):
        return None
    nut = registro.get("nut")
    trastes = {
        item["numero"]: np.asarray(item["ponto"], dtype=float)
        for item in numerar_trastes(registro)
        if item["numero"] is not None
    }
    return Marcas(
        nut=np.asarray(nut, dtype=float) if isinstance(nut, list) else None,
        trastes=trastes,
        corda1=np.asarray(registro["corda1"], dtype=float),
        corda6=np.asarray(registro["corda6"], dtype=float),
    )


def _aplicar(h: np.ndarray, pontos: np.ndarray) -> np.ndarray:
    """Aplica uma homografia a pontos 2D (coordenadas homogêneas).

    Args:
        h: matriz 3x3.
        pontos: array de pontos, com a última dimensão igual a 2.

    Returns:
        Array com a mesma forma de ``pontos``.
    """
    pts = np.asarray(pontos, dtype=float)
    n = pts.size // 2
    homog = np.concatenate([pts.reshape(n, 2), np.ones((n, 1))], axis=1)
    proj = homog @ h.T
    return (proj[:, :2] / proj[:, 2:3]).reshape(pts.shape)


def transformar(marcas: Marcas, h: np.ndarray) -> Marcas:
    """Leva todas as marcas por uma homografia.

    Args:
        marcas: marcas do quadro de origem.
        h: homografia 3x3 (origem -> alvo).

    Returns:
        As marcas no quadro de destino.
    """
    return Marcas(
        nut=None if marcas.nut is None else _aplicar(h, marcas.nut),
        trastes={n: _aplicar(h, p) for n, p in marcas.trastes.items()},
        corda1=_aplicar(h, marcas.corda1),
        corda6=_aplicar(h, marcas.corda6),
    )


def _distancia_a_reta(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Distância perpendicular de um ponto à reta que passa por ``a`` e ``b``.

    Args:
        p: ponto ``(2,)``.
        a: primeiro ponto da reta.
        b: segundo ponto da reta.

    Returns:
        Distância em px (sem sinal).
    """
    d = b - a
    cruz = d[0] * (p[1] - a[1]) - d[1] * (p[0] - a[0])
    return float(abs(cruz) / np.linalg.norm(d))


def _desvio_com_sinal(
    p: np.ndarray, a: np.ndarray, b: np.ndarray, n: np.ndarray
) -> float:
    """Desvio assinado de um ponto em relação à reta ``a``-``b``, ao longo de ``n``.

    A normal da reta é orientada para o mesmo lado que ``n``. Positivo quer dizer que
    o ponto fica no sentido de ``n`` em relação à reta.

    Args:
        p: ponto ``(2,)`` (do alvo).
        a: primeiro ponto da reta (da previsão).
        b: segundo ponto da reta (da previsão).
        n: normal do eixo, ``[-u[1], u[0]]``.

    Returns:
        Desvio em px, com sinal.
    """
    d = (b - a) / np.linalg.norm(b - a)
    normal = np.array([-d[1], d[0]])
    if float(np.dot(normal, n)) < 0.0:
        normal = -normal
    return float(np.dot(p - a, normal))


def _orientar(u: np.ndarray, alvo: Marcas) -> np.ndarray:
    """Orienta o eixo para o corpo, como ``montar_geometria``.

    Com o nut visível, o corpo é o lado oposto ao nut (média dos trastes). Sem o nut,
    os números dos trastes crescem para o corpo: o eixo aponta do menor número para o
    maior.

    Args:
        u: vetor unitário do eixo (sentido ainda não definido).
        alvo: marcas do quadro alvo.

    Returns:
        ``u`` ou ``-u``.
    """
    if alvo.nut is not None:
        media = np.mean(np.stack(list(alvo.trastes.values())), axis=0)
        if float(np.dot(media - alvo.nut, u)) < 0.0:
            return -u
        return u
    ordenados = [alvo.trastes[n] for n in sorted(alvo.trastes)]
    if len(ordenados) >= 2 and float(np.dot(ordenados[-1] - ordenados[0], u)) < 0.0:
        return -u
    return u


def _larguras_locais(trastes: dict[int, np.ndarray], u: np.ndarray) -> dict[int, float]:
    """Largura local da casa de cada traste, ao longo de ``u``.

    A largura do traste ``n`` é a distância ao próximo traste marcado (em ordem de
    número); o último traste usa o anterior. Traste sem vizinho fica de fora.

    Args:
        trastes: número -> ponto, do alvo.
        u: vetor unitário do eixo.

    Returns:
        Largura em px por número de traste.

    Raises:
        ValueError: se dois trastes vizinhos estão no mesmo lugar.
    """
    ordenados = sorted(trastes.items())
    larguras: dict[int, float] = {}
    for i, (n, p) in enumerate(ordenados):
        if i + 1 < len(ordenados):
            vizinho = ordenados[i + 1][1]
        elif i > 0:
            vizinho = ordenados[i - 1][1]
        else:
            continue
        largura = abs(float(np.dot(vizinho - p, u)))
        if largura == 0.0:
            raise ValueError(f"trastes vizinhos de número {n} no mesmo lugar")
        larguras[n] = largura
    return larguras


def _largura_pestana(
    nut: np.ndarray | None, trastes: dict[int, np.ndarray], u: np.ndarray
) -> float | None:
    """Largura da casa 0 (a pestana), estimada a partir do nut.

    Assume casas aproximadamente iguais perto do nut: a distância ao longo de ``u``
    entre o nut e o traste de menor número, dividida por esse número.

    Args:
        nut: ponto do nut, ou ``None``.
        trastes: número -> ponto, do alvo.
        u: vetor unitário do eixo.

    Returns:
        Largura em px, ou ``None`` sem nut ou sem traste numerado.
    """
    if nut is None or not trastes:
        return None
    menor = min(trastes)
    return abs(float(np.dot(trastes[menor] - nut, u))) / menor


def erros(previsto: Marcas, alvo: Marcas) -> dict:
    """Erros da previsão contra as marcas do alvo, nas três métricas.

    O eixo e a largura das casas vêm sempre do alvo (o dono), e a previsão é medida
    contra ele.

    Args:
        previsto: marcas levadas ao alvo (previsão).
        alvo: marcas do dono no quadro alvo.

    Returns:
        Dicionário com ``nut_casas`` (ou None), ``por_traste`` (número -> casas),
        ``pior_traste_casas`` (ou None), ``vao_px``, ``perp_cordas`` (vãos),
        ``perp_assinado_px`` (média com sinal; positivo quer dizer que o alvo fica no
        sentido da normal ``[-u[1], u[0]]`` em relação à previsão).
    """
    _, u = eixo_do_braco(alvo.corda1.tolist(), alvo.corda6.tolist())
    u = _orientar(u, alvo)
    normal = np.array([-u[1], u[0]])

    larguras = _larguras_locais(alvo.trastes, u)
    largura0 = _largura_pestana(alvo.nut, alvo.trastes, u)
    nut_casas = None
    if previsto.nut is not None and largura0 is not None:
        nut_casas = abs(float(np.dot(previsto.nut - alvo.nut, u))) / largura0

    por_traste: dict[int, float] = {}
    for n in range(1, TRASTE_MAXIMO + 1):
        if n in previsto.trastes and n in alvo.trastes and n in larguras:
            dif = float(np.dot(previsto.trastes[n] - alvo.trastes[n], u))
            por_traste[n] = abs(dif) / larguras[n]
    pior = max(por_traste.values()) if por_traste else None

    cruzadas = [
        _distancia_a_reta(p, alvo.corda1[0], alvo.corda1[1]) for p in alvo.corda6
    ]
    cruzadas += [
        _distancia_a_reta(p, alvo.corda6[0], alvo.corda6[1]) for p in alvo.corda1
    ]
    vao_px = float(np.mean(cruzadas)) / INTERVALOS_CORDAS
    if vao_px == 0.0:
        raise ValueError("cordas 1 e 6 do alvo coincidem: vão nulo")

    desvios = [
        _desvio_com_sinal(p, previsto.corda1[0], previsto.corda1[1], normal)
        for p in alvo.corda1
    ]
    desvios += [
        _desvio_com_sinal(p, previsto.corda6[0], previsto.corda6[1], normal)
        for p in alvo.corda6
    ]
    perp_cordas = max(abs(d) for d in desvios) / vao_px
    return {
        "nut_casas": None if nut_casas is None else float(nut_casas),
        "por_traste": {n: float(v) for n, v in por_traste.items()},
        "pior_traste_casas": None if pior is None else float(pior),
        "vao_px": float(vao_px),
        "perp_cordas": float(perp_cordas),
        "perp_assinado_px": float(np.mean(desvios)),
    }


def classificar(e: dict, achou: bool, braco_alvo: str) -> str:
    """Classe de uma medida, pelos critérios da rodada 1015.

    Args:
        e: resultado de ``erros`` (ignorado quando ``achou`` é False).
        achou: se o rastreador disse que achou o braço.
        braco_alvo: valor de ``braco`` no gabarito do quadro alvo.

    Returns:
        ``"certo"``, ``"falso"``, ``"impreciso"`` ou ``"nao_achou"``. Com braço ``nao``
        e ``achou``, é ``"falso"``. Com ``nut_casas`` None, o nut é ignorado.
    """
    if not achou:
        return "nao_achou"
    if braco_alvo == "nao":
        return "falso"
    nut = e.get("nut_casas")
    pior = e.get("pior_traste_casas")
    perp = e["perp_cordas"]
    if (
        (nut is not None and nut > LIMITE_FALSO)
        or (pior is not None and pior > LIMITE_FALSO)
        or perp > LIMITE_FALSO
    ):
        return "falso"
    if (
        (nut is None or nut < LIMITE_CERTO)
        and (pior is None or pior < LIMITE_CERTO)
        and perp < LIMITE_CERTO
    ):
        return "certo"
    return "impreciso"


def linha_de_base(pares: tuple[tuple[str, str], ...], gabarito: dict) -> list[dict]:
    """Mede a grade fixa (homografia identidade) em cada par.

    Args:
        pares: pares (quadro-chave, alvo).
        gabarito: dicionário ``quadros`` do gabarito do braço.

    Returns:
        Uma entrada por par, com ``motivo`` preenchido quando não há medida.
    """
    identidade = np.eye(3)
    entradas = []
    for chave, alvo in pares:
        reg_alvo = gabarito.get(alvo, {})
        braco_alvo = reg_alvo.get("braco")
        entrada: dict = {
            "chave": chave,
            "alvo": alvo,
            "braco_alvo": braco_alvo,
            "motivo": None,
            "erros": None,
            "classe": None,
        }
        previsto_base = marcas_do_registro(gabarito.get(chave, {}))
        marcas_alvo = marcas_do_registro(reg_alvo)
        if previsto_base is None:
            entrada["motivo"] = "quadro-chave sem braço ou registro incompleto"
        elif marcas_alvo is None:
            entrada["motivo"] = f"alvo sem marcas (braço {braco_alvo!r} ou incompleto)"
        else:
            e = erros(transformar(previsto_base, identidade), marcas_alvo)
            entrada["erros"] = e
            entrada["classe"] = classificar(e, True, braco_alvo)
        entradas.append(entrada)
    return entradas


def _formatar(valor: float | None) -> str:
    """Número com 2 casas, ou traço se ausente.

    Args:
        valor: número ou None.

    Returns:
        Texto para a tabela.
    """
    return "—" if valor is None else f"{valor:.2f}"


def _imprimir(entradas: list[dict]) -> None:
    """Imprime a tabela da linha de base.

    Args:
        entradas: resultado de ``linha_de_base``.
    """
    print(
        f"{'par':<12}{'nut(casas)':>12}{'pior(casas)':>13}"
        f"{'perp(px)':>10}{'perp(cordas)':>14}  classe"
    )
    for item in entradas:
        par = f"{item['chave']}->{item['alvo']}"
        if item["motivo"] is not None:
            print(f"{par:<12}  {item['motivo']}")
            continue
        e = item["erros"]
        print(
            f"{par:<12}{_formatar(e['nut_casas']):>12}"
            f"{_formatar(e['pior_traste_casas']):>13}"
            f"{_formatar(e['perp_assinado_px']):>10}"
            f"{_formatar(e['perp_cordas']):>14}  {item['classe']}"
        )


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("comando", choices=["base"])
    parser.add_argument(
        "--teste", action="store_true", help="usa os pares de teste (não rodar agora)"
    )
    args = parser.parse_args()
    gabarito = json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))["quadros"]
    pares = PARES_TESTE if args.teste else PARES_DESENVOLVIMENTO
    nome = "base_teste.json" if args.teste else "base_dev.json"
    entradas = linha_de_base(pares, gabarito)
    MAOS_M11.mkdir(parents=True, exist_ok=True)
    (MAOS_M11 / nome).write_text(
        json.dumps(entradas, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _imprimir(entradas)
    print(f"gravado em {MAOS_M11 / nome}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
