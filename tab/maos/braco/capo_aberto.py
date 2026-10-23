"""Rodada 1046: o capo pelo Grounding DINO (detector aberto) e o nut pela conta.

A cadeia: o par antigo (``L3_todos_s3`` + ``A4_100_todos_s1``, treinado com o nut verdadeiro)
acha cordas e trastes; o Grounding DINO tiny, sem treino, acha o capo pelo texto
(``tab.maos.braco.capo_aberto_gpu``); com o capo visto, o nut passa a ser o traste do par
antigo logo antes do capo, do lado do corpo (decisão 1010), e os trastes são renumerados a
partir dele.

Este módulo é só CPU (sem ``transformers``), para o gate rodar na imagem base.

Pré-registro: ``docs/rodadas/1046-capo-por-detector-aberto.md``.

CLI (``python -m tab.maos.braco.capo_aberto``):

- ``escolher``: o texto e o limiar, só no desenvolvimento;
- ``medir --rodada N``: a cadeia com a escolha congelada, contra o gabarito do dono.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

import numpy as np

from tab.comum.arquivos import gravar_atomico
from tab.comum.caminhos import MAOS_M46
from tab.maos.braco.ciclo import RODADAS
from tab.maos.braco.retreino import medir_por_grupo, tem_capo

#: Modelo e revisão fixos (Apache-2.0), baixados no build da imagem das mãos.
MODELO = "IDEA-Research/grounding-dino-tiny"
REVISAO = "a2bb814dd30d776dcf7e30523b00659f4f141c71"
#: Os textos testados no desenvolvimento (pré-registro).
TEXTOS = ("capo.", "guitar capo.", "guitar capo. guitar nut. hand.")
#: O par antigo, que acha o nut verdadeiro.
PAR_ANTIGO = ("L3_todos_s3", "A4_100_todos_s1")
#: Rodadas de desenvolvimento (revisadas, vistas) e a de capo entre elas.
RODADAS_DEV = ("1026", "1027", "1029", "1032", "1036", "1039")
RODADA_CAPO_DEV = "1039"
#: Nota mínima das caixas guardadas no bruto (o limiar real sai da escolha).
NOTA_BRUTO = 0.05
#: Fração máxima de quadros sem capo com capo visto, no desenvolvimento.
FRACAO_CAPO_FALSO = 0.02
#: Fração mínima de capos achados na 1039 para seguir à prova.
FRACAO_ACHADO_MIN = 0.70
#: Faixa acima do limiar em que o capo é duvidoso (sinaliza).
FAIXA_DUVIDA = 0.10
#: Distância máxima, em casas, do centro do capo ao traste que vira o nut.
JANELA_CASAS = 1.0
#: Pontos amostrados em cada corda para saber se ela cruza a caixa.
AMOSTRAS_CORDA = 200

ARQUIVO_ANTIGO = "antigo.json"
ARQUIVO_CAIXAS = "caixas.json"
ARQUIVO_ESCOLHA = MAOS_M46 / "escolha.json"


def _ler_json(caminho: Path) -> dict:
    """Lê um JSON em UTF-8.

    Args:
        caminho: arquivo.

    Returns:
        O conteúdo.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def pasta_da_rodada(numero: str) -> Path:
    """Pasta da 1046 para uma rodada do ciclo.

    Args:
        numero: rodada do ciclo.

    Returns:
        ``MAOS_M46 / numero``.
    """
    return MAOS_M46 / numero


def contem(caixa: list[float], ponto: object) -> bool:
    """Se o ponto está dentro da caixa (bordas incluídas).

    Args:
        caixa: ``[x0, y0, x1, y1]``.
        ponto: ``[x, y]``.

    Returns:
        True dentro.
    """
    x, y = (float(v) for v in ponto)
    return caixa[0] <= x <= caixa[2] and caixa[1] <= y <= caixa[3]


def cruza_braco(caixa: list[float], previsto: dict) -> bool:
    """Se as cordas 1 e 6 previstas passam as duas pela caixa.

    Args:
        caixa: ``[x0, y0, x1, y1]``.
        previsto: entrada de ``previsto.json`` com ``corda1`` e ``corda6``.

    Returns:
        True se cada corda tem algum ponto dentro da caixa.
    """
    for nome in ("corda1", "corda6"):
        corda = previsto.get(nome)
        if not corda:
            return False
        a, b = (np.asarray(p, dtype=float) for p in corda)
        pesos = np.linspace(0.0, 1.0, AMOSTRAS_CORDA)[:, None]
        pontos = a + (b - a) * pesos
        if not any(contem(caixa, p) for p in pontos):
            return False
    return True


def melhor_caixa(caixas: list[dict], previsto: dict) -> dict | None:
    """A caixa de capo de maior nota que cruza o braço previsto.

    Args:
        caixas: saída do detector (``caixa``, ``nota``, ``rotulo``).
        previsto: entrada de ``previsto.json``.

    Returns:
        A caixa, ou None se nenhuma de rótulo com "capo" cruza o braço.
    """
    if not previsto.get("achou"):
        return None
    validas = [
        c for c in caixas if "capo" in c["rotulo"] and cruza_braco(c["caixa"], previsto)
    ]
    return max(validas, key=lambda c: c["nota"]) if validas else None


def _pontos_numerados(previsto: dict) -> list[tuple[int, np.ndarray]]:
    """O nut (número 0) e os trastes previstos, em ordem de número.

    Args:
        previsto: entrada de ``previsto.json``.

    Returns:
        ``[(numero, ponto)]``.
    """
    pontos = [(0, np.asarray(previsto["nut"], dtype=float))]
    for traste in previsto.get("trastes") or []:
        pontos.append((int(traste["numero"]), np.asarray(traste["ponto"], dtype=float)))
    return sorted(pontos, key=lambda p: p[0])


def _ponta_do_nut(corda: list, nut: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """As pontas de uma corda, a do lado do nut primeiro.

    Args:
        corda: ``[[x, y], [x, y]]``.
        nut: ponto do nut.

    Returns:
        ``(ponta do nut, ponta do corpo)``.
    """
    a, b = (np.asarray(p, dtype=float) for p in corda)
    return (a, b) if np.linalg.norm(a - nut) <= np.linalg.norm(b - nut) else (b, a)


def nut_pela_conta(previsto: dict, caixa: dict) -> dict | None:
    """Põe o nut no traste logo antes do capo (lado do corpo) e renumera os trastes.

    Args:
        previsto: entrada de ``previsto.json`` do par antigo (nut verdadeiro).
        caixa: a caixa do capo (``caixa``, ``nota``).

    Returns:
        Uma cópia de ``previsto`` com ``nut``, ``trastes`` e as pontas das cordas do lado
        do nut movidas, e ``capo_casa`` (o número do traste que virou nut); ou None se não
        há traste do lado do corpo a até ``JANELA_CASAS`` casa do centro do capo.
    """
    pontos = _pontos_numerados(previsto)
    if len(pontos) < 3:
        return None
    nut = pontos[0][1]
    eixo = pontos[-1][1] - nut
    eixo = eixo / np.linalg.norm(eixo)
    x0, y0, x1, y1 = caixa["caixa"]
    centro = (float(np.array([x0, x1]).mean()), float(np.array([y0, y1]).mean()))
    pos_capo = float((np.asarray(centro) - nut) @ eixo)
    posicoes = [float((p - nut) @ eixo) for _, p in pontos]
    depois = [
        i for i, pos in enumerate(posicoes) if pos > pos_capo and pontos[i][0] > 0
    ]
    if not depois:
        return None
    i = depois[0]
    vizinho = i + 1 if i + 1 < len(pontos) else i - 1
    casa = abs(posicoes[vizinho] - posicoes[i])
    if casa <= 0 or posicoes[i] - pos_capo > JANELA_CASAS * casa:
        return None
    numero_nut, ponto_nut = pontos[i]
    novo = copy.deepcopy(previsto)
    novo["nut"] = [float(v) for v in ponto_nut]
    novo["trastes"] = [
        {"numero": numero - numero_nut, "ponto": [float(v) for v in ponto]}
        for numero, ponto in pontos
        if numero > numero_nut
    ]
    alvo = posicoes[i]
    for nome in ("corda1", "corda6"):
        ponta, corpo = _ponta_do_nut(previsto[nome], nut)
        passo = float((corpo - ponta) @ eixo)
        t = (alvo - float((ponta - nut) @ eixo)) / passo if passo else 0.0
        novo[nome] = [[float(v) for v in ponta + (corpo - ponta) * t], corpo.tolist()]
    novo["capo_casa"] = numero_nut
    novo["capo_caixa"] = caixa["caixa"]
    novo["capo_nota"] = caixa["nota"]
    return novo


def prever_com_capo(
    antigo: dict, caixas: dict[str, dict], texto: str, limiar: float
) -> dict:
    """A cadeia da 1046 sobre o par antigo e as caixas guardadas.

    Args:
        antigo: ``previsto.json`` do par antigo (``ordem`` e ``quadros``).
        caixas: ``{id: {texto: [caixas]}}``.
        texto: o texto escolhido.
        limiar: a nota mínima do capo visto.

    Returns:
        Um documento no formato de ``previsto.json``, com ``capo`` por quadro
        (``visto``, ``nota``, ``casa``).
    """
    quadros = {}
    for id_q in antigo["ordem"]:
        previsto = antigo["quadros"][id_q]
        caixa = melhor_caixa(caixas.get(id_q, {}).get(texto, []), previsto)
        if caixa is None or caixa["nota"] < limiar:
            quadros[id_q] = dict(previsto, capo={"visto": False})
            continue
        novo = nut_pela_conta(previsto, caixa)
        if novo is None:
            quadros[id_q] = dict(
                previsto,
                sinalizado=True,
                motivo="capo sem traste",
                capo={"visto": True, "nota": caixa["nota"], "casa": None},
            )
            continue
        duvida = caixa["nota"] < limiar + FAIXA_DUVIDA
        novo["sinalizado"] = bool(previsto["sinalizado"] or duvida)
        novo["capo"] = {"visto": True, "nota": caixa["nota"], "casa": novo["capo_casa"]}
        quadros[id_q] = novo
    return dict(antigo, quadros=quadros)


def nota_do_quadro(caixas: list[dict], previsto: dict) -> float:
    """A nota da melhor caixa de capo que cruza o braço (0 sem nenhuma).

    Args:
        caixas: caixas de um texto num quadro.
        previsto: entrada de ``previsto.json``.

    Returns:
        A nota.
    """
    caixa = melhor_caixa(caixas, previsto)
    return caixa["nota"] if caixa else 0.0


def limiar_por_falsos(notas_sem_capo: list[float], fracao: float) -> float:
    """O menor limiar com no máximo ``fracao`` dos quadros sem capo acima dele.

    Args:
        notas_sem_capo: a nota de cada quadro sem capo.
        fracao: fração máxima permitida.

    Returns:
        O limiar (nunca abaixo de ``NOTA_BRUTO``).
    """
    notas = sorted(notas_sem_capo, reverse=True)
    permitidos = int(fracao * len(notas))
    if permitidos >= len(notas):
        return NOTA_BRUTO
    return max(NOTA_BRUTO, notas[permitidos] + 1e-6)


def _dados(numero: str) -> tuple[dict, dict, dict]:
    """O par antigo, as caixas e o gabarito de uma rodada.

    Args:
        numero: rodada do ciclo.

    Returns:
        ``(antigo, caixas, gabarito)``.
    """
    pasta = pasta_da_rodada(numero)
    return (
        _ler_json(pasta / ARQUIVO_ANTIGO),
        _ler_json(pasta / ARQUIVO_CAIXAS),
        _ler_json(RODADAS[numero].gabarito),
    )


def _com_braco(gabarito: dict) -> dict[str, dict]:
    """Os registros com braço do dono (``sim`` ou ``parcial``).

    Args:
        gabarito: gabarito do dono.

    Returns:
        ``{id: registro}``.
    """
    return {
        id_q: r
        for id_q, r in gabarito["quadros"].items()
        if r.get("braco") in ("sim", "parcial")
    }


def escolher() -> dict:
    """Escolhe o texto e o limiar no desenvolvimento, pela regra do pré-registro.

    Returns:
        A escolha, com a tabela de cada texto; também gravada em ``ARQUIVO_ESCOLHA``.
    """
    dados = {numero: _dados(numero) for numero in RODADAS_DEV}
    tabela = []
    for texto in TEXTOS:
        notas_sem = []
        for antigo, caixas, gabarito in dados.values():
            for id_q, registro in _com_braco(gabarito).items():
                if tem_capo(registro) or id_q not in antigo["quadros"]:
                    continue
                notas_sem.append(
                    nota_do_quadro(
                        caixas.get(id_q, {}).get(texto, []), antigo["quadros"][id_q]
                    )
                )
        limiar = limiar_por_falsos(notas_sem, FRACAO_CAPO_FALSO)
        antigo, caixas, gabarito = dados[RODADA_CAPO_DEV]
        com = {i: r for i, r in _com_braco(gabarito).items() if tem_capo(r)}
        achados = 0
        for id_q, registro in com.items():
            caixa = melhor_caixa(
                caixas.get(id_q, {}).get(texto, []), antigo["quadros"][id_q]
            )
            if (
                caixa
                and caixa["nota"] >= limiar
                and contem(caixa["caixa"], registro["capo"])
            ):
                achados += 1
        falsos = sum(1 for n in notas_sem if n >= limiar)
        tabela.append(
            {
                "texto": texto,
                "limiar": limiar,
                "sem_capo": [falsos, len(notas_sem)],
                "achados_1039": [achados, len(com)],
            }
        )
    melhor = max(
        tabela, key=lambda linha: (linha["achados_1039"][0], -linha["sem_capo"][0])
    )
    achados, total = melhor["achados_1039"]
    escolha = {
        "texto": melhor["texto"],
        "limiar": melhor["limiar"],
        "segue_para_prova": achados >= FRACAO_ACHADO_MIN * total,
        "tabela": tabela,
        "regra": "limiar: ≤ 2 % dos sem capo do dev; texto: mais capos achados na 1039",
    }
    gravar_atomico(ARQUIVO_ESCOLHA, escolha)
    return escolha


def casa_do_dono(registro: dict) -> int | None:
    """A casa do capo escrita pelo dono na observação ("capotraste casa N").

    Args:
        registro: registro do gabarito.

    Returns:
        N, ou None.
    """
    achado = re.search(r"capotraste\s+casa\s+(\d+)", registro.get("obs") or "")
    return int(achado.group(1)) if achado else None


def _sem_linhas(medida: dict) -> dict:
    """A medida sem as linhas quadro a quadro.

    Args:
        medida: saída de ``medir_por_grupo``.

    Returns:
        Cópia sem ``linhas``.
    """
    return {k: v for k, v in medida.items() if k != "linhas"}


def medir(numero: str) -> dict:
    """Mede a cadeia da 1046 numa rodada, com a escolha congelada.

    Args:
        numero: rodada do ciclo (a prova é a 1043).

    Returns:
        A medida da cadeia e do par antigo, e o registro do capo por quadro; também
        gravada em ``pasta_da_rodada(numero) / "medida.json"``.
    """
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    antigo, caixas, gabarito = _dados(numero)
    cadeia = prever_com_capo(antigo, caixas, escolha["texto"], escolha["limiar"])
    capo = {}
    for id_q, registro in _com_braco(gabarito).items():
        info = cadeia["quadros"][id_q]["capo"]
        caixa = cadeia["quadros"][id_q].get("capo_caixa")
        capo[id_q] = {
            "dono": tem_capo(registro),
            "casa_dono": casa_do_dono(registro),
            "visto": info["visto"],
            "casa": info.get("casa"),
            "caixa_contem_k": bool(caixa and tem_capo(registro))
            and contem(caixa, registro["capo"]),
        }
    medida = {
        "escolha": {k: escolha[k] for k in ("texto", "limiar")},
        "cadeia": _sem_linhas(medir_por_grupo(cadeia, gabarito)),
        "antigo": _sem_linhas(medir_por_grupo(antigo, gabarito)),
        "capo": capo,
    }
    pasta = pasta_da_rodada(numero)
    gravar_atomico(pasta / "previsto.json", cadeia)
    gravar_atomico(pasta / "medida.json", medida)
    return medida


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("escolher", help="texto e limiar no desenvolvimento")
    p_medir = sub.add_parser("medir", help="a cadeia contra o gabarito")
    p_medir.add_argument("--rodada", required=True)
    args = parser.parse_args()
    if args.comando == "escolher":
        resultado = escolher()
    else:
        medida = medir(args.rodada)
        resultado = {
            k: {g: medida[k][g] for g in ("todos", "capo", "sem_capo")}
            for k in ("cadeia", "antigo")
        }
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
