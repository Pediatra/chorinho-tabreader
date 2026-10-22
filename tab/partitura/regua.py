"""F0.1 da partitura: em que compasso está o erro, e o Audiveris avisa? (rodada 3101).

Para cada recorte dos gabaritos completos do dono (R01–R21 e os 3 sem produto), lê a
leitura que o dono conferiu (campo ``fonte``) e o ``.omr`` dela. Divide em compassos: o
símbolo pelo ``compasso`` do palpite; o clique de faltando pelo x entre as barras do
``.omr`` (x do ``stack`` dividido por 2, porque o ``.omr`` é 2× a imagem).

Para cada compasso guarda as marcas do Audiveris: ``abnormal`` (o ``measure`` com
``abnormal="true"``), o déficit e o excesso de duração contra a duração esperada de duas
fontes (``expected`` do ``.omr`` e a fórmula da própria leitura, separadas). Monta a tabela
compasso com erro × marca e conta os alarmes falsos de cada marca.

Só lê o que está gravado e só grava o JSON na pasta da frente 0.

Uso (na raiz do projeto)::

    python -m tab.partitura_regua
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
import zipfile
from fractions import Fraction
from pathlib import Path

from tab.comum.caminhos import GOLD_PARTITURA, PART_FRENTE_0, PARTITURA_SEM_PRODUTO
from tab.partitura.gabarito import ler_partitura
from tab.partitura.pareamento import PASTA_P1

GOLD_P1 = GOLD_PARTITURA / "leitura_p1.json"
GOLD_SP = GOLD_PARTITURA / "leitura_sem_produto.json"
PASTA_SP = PARTITURA_SEM_PRODUTO
SAIDA_JSON = PART_FRENTE_0 / "regua_compassos.json"

#: Recortes que ficam de fora da tabela de compasso (ver a rodada 3101).
R20 = "R20"
TOLERANCIA_PX = 5.0
ESCALA_OMR = 2.0
MARCAS = [
    "abnormal",
    "deficit_A",
    "excesso_A",
    "sem_A",
    "deficit_B",
    "excesso_B",
]


def _seminimas(fracao: str | None) -> float | None:
    """Duração de um compasso em semínimas, a partir de uma fração ``"3/4"``.

    Args:
        fracao: fração da fórmula de compasso, ou None.

    Returns:
        Número de semínimas do compasso (``3/4`` → 3.0), ou None se não há fração.
    """
    if not fracao:
        return None
    return float(Fraction(fracao) * 4)


def _pasta_sem_produto(curto: str, rec: str) -> Path | None:
    """Pasta do recorte sem produto (``omr/audiveris/x2_margem/<rec>``) pelo prefixo.

    A pasta ``ólafur_...`` é uma cópia vazia; por isso só conta a que tem o ``.omr``.

    Args:
        curto: prefixo do nome do vídeo (antes do ``_`` final do id).
        rec: id do recorte (``P01a_...``).

    Returns:
        Pasta ``.../omr/audiveris`` do vídeo com o ``.omr``, ou None.
    """
    for pasta in sorted(PASTA_SP.iterdir()):
        if not pasta.name.startswith(curto):
            continue
        omr = pasta / "omr" / "audiveris" / "x2_margem" / rec / "entrada.omr"
        if omr.exists():
            return pasta / "omr" / "audiveris"
    return None


def _itens() -> list[dict]:
    """Os recortes dos dois gabaritos com os caminhos de leitura e de ``.omr``.

    Returns:
        Uma entrada por recorte: ``grupo``, ``rid``, ``xml``, ``omr``, ``png``,
        ``simbolos``, ``faltando`` e ``fonte``.
    """
    itens = []
    p1 = json.loads(GOLD_P1.read_text(encoding="utf-8"))["recortes"]
    for rid in sorted(p1):
        r = p1[rid]
        if r["fonte"] == "audiveris/x2_margem":
            base = PASTA_P1 / "omr" / "audiveris" / "x2_margem" / rid
            xml, omr, png = (
                base / "saida.musicxml",
                base / "entrada.omr",
                base / "entrada.png",
            )
        elif r["fonte"] == "homr/nativo":
            base = PASTA_P1 / "omr" / "homr" / "nativo" / rid
            xml, omr, png = base / "saida.musicxml", None, None
        else:
            raise ValueError(f"fonte desconhecida em {rid}: {r['fonte']}")
        itens.append(
            {
                "grupo": "R01-R21",
                "rid": rid,
                "xml": xml,
                "omr": omr,
                "png": png,
                "simbolos": r["simbolos"],
                "faltando": r["faltando"],
                "fonte": r["fonte"],
            }
        )
    sp = json.loads(GOLD_SP.read_text(encoding="utf-8"))["recortes"]
    for rid in sorted(sp):
        curto, rec = rid.rsplit("_", 1)
        pasta = _pasta_sem_produto(curto, rec)
        if pasta is None:
            raise ValueError(f"sem .omr para {rid}")
        base_omr = pasta / "x2_margem" / rec
        itens.append(
            {
                "grupo": "sem_produto",
                "rid": rid,
                "xml": pasta / "x2_margem_herdada" / rec / "saida.musicxml",
                "omr": base_omr / "entrada.omr",
                "png": base_omr / "entrada.png",
                "simbolos": sp[rid]["simbolos"],
                "faltando": sp[rid]["faltando"],
                "fonte": sp[rid]["fonte"],
            }
        )
    return itens


def _stacks_e_marcas(omr: Path) -> tuple[list[dict], list[bool]]:
    """Stacks do ``.omr`` (na ordem, com x e fração) e a marca ``abnormal`` de cada um.

    Args:
        omr: arquivo ``.omr`` (zip com ``sheet#1/sheet#1.xml``).

    Returns:
        ``(stacks, abnormal)``: cada stack com ``left`` (já /2) e ``expected``/``duration``,
        e uma booleana de ``abnormal`` por compasso (mesma ordem).
    """
    with zipfile.ZipFile(omr) as arquivo:
        raiz = ET.fromstring(arquivo.read("sheet#1/sheet#1.xml"))
    stacks = [
        {
            "left": float(s.get("left")) / ESCALA_OMR,
            "expected": s.get("expected"),
            "duration": s.get("duration"),
        }
        for s in raiz.iter("stack")
    ]
    abnormal = [m.get("abnormal") == "true" for m in raiz.iter("measure")]
    return stacks, abnormal


def _duracao_por_voz(simbolos: list[dict]) -> float:
    """Maior soma de durações por voz de um compasso, sem contar o acorde duas vezes.

    Args:
        simbolos: símbolos de ``ler_partitura`` do compasso (inclui pausas).

    Returns:
        A maior soma de ``duracao`` entre as vozes, em semínimas.
    """
    somas: dict[str, float] = {}
    for simbolo in simbolos:
        if simbolo.get("acorde"):
            continue
        voz = str(simbolo.get("voz"))
        somas[voz] = somas.get(voz, 0.0) + float(simbolo.get("duracao") or 0.0)
    return max(somas.values(), default=0.0)


def _linhas_do_recorte(item: dict) -> tuple[list[dict], dict]:
    """Linhas de compasso de um recorte, e o que sobrou de fora.

    Args:
        item: entrada de ``_itens``.

    Returns:
        ``(linhas, fora)``: uma linha por compasso (marcas, erros e cliques) e um dicionário
        com os cliques que não caem em nenhum compasso e a contagem de stacks e compassos.
    """
    leitura = ler_partitura(item["xml"])
    compassos = leitura["compassos"]
    numeros = [m["numero"] for m in compassos]
    formula = leitura["compasso_formula"]
    esperada_b = None
    if formula and formula["beats"] is not None and formula["beat_type"] is not None:
        esperada_b = float(Fraction(formula["beats"], formula["beat_type"]) * 4)
    fora: dict = {"cliques_fora": 0, "stacks": None, "compassos": len(numeros)}
    if item["omr"] is None:
        fora["motivo"] = "sem .omr (homr)"
        return [], fora
    stacks, abnormal = _stacks_e_marcas(item["omr"])
    fora["stacks"] = len(stacks)
    if len(stacks) != len(numeros) or len(abnormal) != len(numeros):
        fora["motivo"] = "stacks e compassos diferem"
        return [], fora
    posicao = {}
    for k, numero in enumerate(numeros):
        posicao.setdefault(numero, k)
    erro_simbolo = [False] * len(numeros)
    for simbolo in item["simbolos"]:
        if simbolo["dono"] != "certo":
            erro_simbolo[posicao[simbolo["palpite"]["compasso"]]] = True
    cliques = [0] * len(numeros)
    inicios = [s["left"] for s in stacks]
    for clique in item["faltando"]:
        x = clique["x"]
        antes = [k for k, ini in enumerate(inicios) if ini <= x + TOLERANCIA_PX]
        if not antes:
            fora["cliques_fora"] += 1
            continue
        cliques[max(antes)] += 1
    linhas = []
    for k, numero in enumerate(numeros):
        soma = _duracao_por_voz(compassos[k]["simbolos"])
        esp_a = _seminimas(stacks[k]["expected"])
        linha = {
            "rid": item["rid"],
            "grupo": item["grupo"],
            "posicao": k,
            "numero": numero,
            "soma": soma,
            "esperada_A": esp_a,
            "esperada_B": esperada_b,
            "abnormal": abnormal[k],
            "deficit_A": esp_a is not None and soma < esp_a - 1e-6,
            "excesso_A": esp_a is not None and soma > esp_a + 1e-6,
            "sem_A": esp_a is None,
            "deficit_B": esperada_b is not None and soma < esperada_b - 1e-6,
            "excesso_B": esperada_b is not None and soma > esperada_b + 1e-6,
            "cliques": cliques[k],
            "simbolos_nao_certos": erro_simbolo[k],
        }
        linha["erro"] = bool(cliques[k] or erro_simbolo[k])
        linhas.append(linha)
    return linhas, fora


def _tabela(linhas: list[dict]) -> dict:
    """Tabela compasso com erro × marca, com o denominador e os alarmes falsos.

    Args:
        linhas: linhas de compasso de todos os recortes da tabela.

    Returns:
        ``{"compassos": n, "com_erro": n, "marcas": {marca: {...}}}``. Por marca: quantos
        compassos a marca acusa, quantos desses têm erro (acertos) e quantos não têm (alarmes
        falsos).
    """
    tabela: dict = {
        "compassos": len(linhas),
        "com_erro": sum(1 for x in linhas if x["erro"]),
        "marcas": {},
    }
    for marca in MARCAS:
        acusa = [x for x in linhas if x[marca]]
        tabela["marcas"][marca] = {
            "acusa": len(acusa),
            "com_erro": sum(1 for x in acusa if x["erro"]),
            "alarmes_falsos": sum(1 for x in acusa if not x["erro"]),
            "exemplos": [
                {"rid": x["rid"], "posicao": x["posicao"], "erro": x["erro"]}
                for x in acusa[:5]
            ],
        }
    return tabela


def medir() -> dict:
    """Roda a F0.1 nos 24 recortes e devolve o documento de saída.

    Returns:
        Documento com ``linhas``, ``fora`` por recorte, ``tabela`` (R01–R21 sem R20 e sem
        os recortes de contagem diferente, mais os 3 sem produto), contagens de conferência
        e os cliques fora de compasso.
    """
    linhas: list[dict] = []
    fora: dict[str, dict] = {}
    for item in _itens():
        if item["rid"] == R20:
            # R20 não tem os faltando da segunda metade: entra só na precisão.
            fora[item["rid"]] = {"motivo": "R20: só precisão (rodada 3005)"}
            continue
        if item["omr"] is None:
            fora[item["rid"]] = {"motivo": "R21: homr, sem .omr (à parte)"}
            continue
        linhas_rec, info = _linhas_do_recorte(item)
        if not linhas_rec:
            fora[item["rid"]] = info
            continue
        fora[item["rid"]] = {
            "stacks": info["stacks"],
            "compassos": info["compassos"],
            "cliques_fora": info["cliques_fora"],
        }
        linhas.extend(linhas_rec)
    lidos = sum(len(i["simbolos"]) for i in _itens())
    certos = sum(1 for i in _itens() for s in i["simbolos"] if s["dono"] == "certo")
    faltando = sum(len(i["faltando"]) for i in _itens())
    cliques_fora = sum(info.get("cliques_fora", 0) for info in fora.values())
    return {
        "frente": "F0.1",
        "rodada": 3101,
        "escala_omr": ESCALA_OMR,
        "tolerancia_px": TOLERANCIA_PX,
        "conferencia": {
            "lidos": lidos,
            "certos": certos,
            "faltando": faltando,
            "esperado": {"lidos": 873 + 178, "certos": 852 + 176, "faltando": 78 + 40},
        },
        "cliques_fora_de_compasso": cliques_fora,
        "fora_da_tabela": fora,
        "tabela": _tabela(linhas),
        "com_faltando": _tabela([x for x in linhas if x["cliques"] > 0]),
        "deficit_calculavel_em_compasso_com_faltando": sum(
            1 for x in linhas if x["cliques"] > 0 and x["esperada_A"] is not None
        ),
        "linhas": linhas,
    }


def main(argv: list[str] | None = None) -> int:
    """Roda a F0.1 e grava ``regua_compassos.json`` na pasta da frente 0.

    Args:
        argv: argumentos da linha de comando (não há opções).

    Returns:
        Zero em caso de sucesso.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    documento = medir()
    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_JSON.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    conf = documento["conferencia"]
    print(f"conferencia {conf}")
    print(f"cliques fora de compasso: {documento['cliques_fora_de_compasso']}")
    t = documento["tabela"]
    print(f"compassos {t['compassos']}, com erro {t['com_erro']}")
    for marca, v in t["marcas"].items():
        print(
            f"  {marca}: acusa {v['acusa']}, com erro {v['com_erro']},"
            f" alarmes falsos {v['alarmes_falsos']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
