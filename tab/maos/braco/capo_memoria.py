"""Rodada 1048: memória do capo por vídeo (o capo visto num quadro vale para os outros).

Sobre a cadeia da 1045 (a da 1047 + a rede de capo + o nut pela conta):

1. **Quadros-chave** de um vídeo: capo visto com nota ≥ ``NOTA_CHAVE`` e a conta aprovada
   pelos validadores da 1044.
2. **Levar o capo** a um quadro do mesmo vídeo sem capo visto: pontos ORB casados entre o
   quadro-chave (do mais próximo no tempo ao mais distante) e o alvo, só dentro do braço nos
   dois (a máscara das marcas previstas pelo par antigo), Lowe 0,8 e homografia por RANSAC.
3. Com o capo levado, o nut pela conta; sinalizado se os validadores reprovam ou se o par
   antigo sinalizou.

Pré-registro: ``docs/rodadas/1048-memoria-do-capo-por-video.md``.

CLI (``python -m tab.maos.braco.capo_memoria``): ``picos --rodada N`` (GPU),
``escolher`` (na 1043 e na M39) e ``medir`` (na M48).
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from tab.comum.arquivos import gravar_atomico
from tab.comum.caminhos import (
    GABARITO_BRACO_M39,
    GABARITO_BRACO_M43,
    GABARITO_BRACO_M48,
    MAOS_M39,
    MAOS_M43,
    MAOS_M48,
    SAIDA,
)
from tab.comum.gpu import trava_gpu
from tab.maos.braco.capo_aberto import nut_pela_conta
from tab.maos.braco.capo_rede import (
    ARQUIVO_ESCOLHA as ESCOLHA_1045,
)
from tab.maos.braco.capo_rede import (
    ARQUIVO_PICOS as PICOS_1045,
)
from tab.maos.braco.capo_rede import (
    PREFIXO,
    achado,
    carregar,
    com_capo,
    pico_do_quadro,
)
from tab.maos.braco.ciclo import marcas_do_previsto
from tab.maos.braco.rastreio import mascara_do_braco
from tab.maos.braco.retreino import medir_por_grupo, tem_capo
from tab.maos.braco.validadores import (
    PASTA_HIPOTESES,
    REFERENCIA,
    cadeia,
    ler_faixas,
    nome_da_hipotese,
    validar,
)

MAOS_M48_MEDIDA = MAOS_M48 / "memoria"
#: Grade da escolha (pré-registro).
NOTAS_CHAVE = (0.5, 0.7, 0.9)
MINIMOS_INLIERS = (10, 20, 40)
#: Fração máxima de levados errados entre os levados.
FRACAO_ERRADOS = 0.05
#: Rastreio: pontos ORB, razão de Lowe, RANSAC, reprojeção e determinante.
PONTOS_ORB = 5000
RAZAO_LOWE = 0.8
RANSAC_PX = 5.0
REPROJ_MAXIMA_PX = 3.0
DETERMINANTE = (0.5, 2.0)
#: Desenvolvimento: (fonte, gabarito, pasta, antigo.json) e o nome da fonte nos picos.
DESENVOLVIMENTO = (
    (
        "M43",
        GABARITO_BRACO_M43,
        MAOS_M43,
        SAIDA / "maos" / "m46" / "1043" / "antigo.json",
    ),
    (
        "M39",
        GABARITO_BRACO_M39,
        MAOS_M39,
        SAIDA / "maos" / "m46" / "1039" / "antigo.json",
    ),
)
RODADA_PROVA = "1048"

ARQUIVO_PICOS = MAOS_M48_MEDIDA / "picos_1048.json"
ARQUIVO_ESCOLHA = MAOS_M48_MEDIDA / "escolha.json"
ARQUIVO_MEDIDA = MAOS_M48_MEDIDA / "medida.json"


def _ler_json(caminho: Path) -> dict:
    """Lê um JSON em UTF-8.

    Args:
        caminho: arquivo.

    Returns:
        O conteúdo.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def _indice(pasta: Path) -> dict[str, dict]:
    """O ``indice.json`` de uma pasta, por id.

    Args:
        pasta: pasta com ``indice.json``.

    Returns:
        ``{id: item}``.
    """
    return {q["id"]: q for q in _ler_json(pasta / "indice.json")["quadros"]}


def levar(
    img_chave: np.ndarray,
    marcas_chave: object,
    ponto: list[float],
    img_alvo: np.ndarray,
    marcas_alvo: object,
    min_inliers: int,
) -> list[float] | None:
    """Leva um ponto do quadro-chave ao alvo por homografia, só com pontos do braço.

    Args:
        img_chave: quadro-chave BGR.
        marcas_chave: marcas previstas no quadro-chave (``Marcas``).
        ponto: o capo no quadro-chave.
        img_alvo: quadro alvo BGR.
        marcas_alvo: marcas previstas no alvo (``Marcas``).
        min_inliers: inliers mínimos.

    Returns:
        O ponto no alvo, ou None quando o rastreio não acha.
    """
    try:
        mascara_chave = mascara_do_braco(marcas_chave, img_chave.shape)
        mascara_alvo = mascara_do_braco(marcas_alvo, img_alvo.shape)
    except ValueError:
        return None
    orb = cv2.ORB_create(nfeatures=PONTOS_ORB)
    kp_c, des_c = orb.detectAndCompute(
        cv2.cvtColor(img_chave, cv2.COLOR_BGR2GRAY), mascara_chave
    )
    kp_a, des_a = orb.detectAndCompute(
        cv2.cvtColor(img_alvo, cv2.COLOR_BGR2GRAY), mascara_alvo
    )
    if des_c is None or des_a is None:
        return None
    pares = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(des_c, des_a, k=2)
    bons = [
        p[0]
        for p in pares
        if len(p) == 2 and p[0].distance < RAZAO_LOWE * p[1].distance
    ]
    if len(bons) < max(4, min_inliers):
        return None
    origem = np.float32([kp_c[m.queryIdx].pt for m in bons]).reshape(-1, 1, 2)
    destino = np.float32([kp_a[m.trainIdx].pt for m in bons]).reshape(-1, 1, 2)
    cv2.setRNGSeed(0)
    h, mascara = cv2.findHomography(origem, destino, cv2.RANSAC, RANSAC_PX)
    if h is None or not np.all(np.isfinite(h)):
        return None
    ativos = mascara.ravel().astype(bool)
    if int(ativos.sum()) < min_inliers:
        return None
    erro = np.linalg.norm(
        cv2.perspectiveTransform(origem[ativos], h) - destino[ativos], axis=2
    )
    if float(np.median(erro)) > REPROJ_MAXIMA_PX:
        return None
    if not DETERMINANTE[0] <= float(np.linalg.det(h[:2, :2])) <= DETERMINANTE[1]:
        return None
    alvo = cv2.perspectiveTransform(np.float32([[ponto]]), h)[0, 0]
    return [float(alvo[0]), float(alvo[1])]


def chaves_do_video(
    ids: list[str], antigo: dict, picos: dict, nota_chave: float, faixas: dict
) -> list[str]:
    """Os quadros-chave de um vídeo: capo com nota alta e a conta aprovada.

    Args:
        ids: quadros do vídeo.
        antigo: previsões do par antigo por id.
        picos: ``{id: pico ou None}``.
        nota_chave: nota mínima do quadro-chave.
        faixas: as faixas dos validadores.

    Returns:
        Os ids dos quadros-chave.
    """
    chaves = []
    for id_q in ids:
        pico = picos.get(id_q)
        if pico is None or pico["nota"] < nota_chave or not antigo[id_q].get("achou"):
            continue
        x, y = pico["ponto"]
        novo = nut_pela_conta(
            antigo[id_q], {"caixa": [x - 1, y - 1, x + 1, y + 1], "nota": 1.0}
        )
        if novo is not None and validar(marcas_do_previsto(novo), faixas)["passa"]:
            chaves.append(id_q)
    return chaves


def levar_no_video(
    alvo: str,
    chaves: list[str],
    indice: dict[str, dict],
    pasta: Path,
    antigo: dict,
    picos: dict,
    min_inliers: int,
) -> list[float] | None:
    """Leva o capo ao alvo do quadro-chave mais próximo no tempo que der certo.

    Args:
        alvo: id do quadro alvo.
        chaves: ids dos quadros-chave do vídeo.
        indice: índice da pasta por id (``t`` e ``png``).
        pasta: pasta dos quadros.
        antigo: previsões do par antigo por id.
        picos: ``{id: pico}``.
        min_inliers: inliers mínimos.

    Returns:
        O capo no alvo, ou None.
    """
    marcas_alvo = marcas_do_previsto(antigo[alvo])
    if marcas_alvo is None:
        return None
    img_alvo = cv2.imread(str(pasta / indice[alvo]["png"]))
    for chave in sorted(chaves, key=lambda c: abs(indice[c]["t"] - indice[alvo]["t"])):
        if chave == alvo:
            continue
        img_chave = cv2.imread(str(pasta / indice[chave]["png"]))
        ponto = levar(
            img_chave,
            marcas_do_previsto(antigo[chave]),
            picos[chave]["ponto"],
            img_alvo,
            marcas_alvo,
            min_inliers,
        )
        if ponto is not None:
            return ponto
    return None


def _por_video(indice: dict[str, dict]) -> dict[str, list[str]]:
    """Os ids de cada vídeo.

    Args:
        indice: índice por id.

    Returns:
        ``{arquivo: [ids]}``.
    """
    videos: dict[str, list[str]] = {}
    for id_q, item in indice.items():
        videos.setdefault(item["arquivo"], []).append(id_q)
    return videos


def avaliar_ponto(
    fonte: tuple,
    picos: dict,
    limiar: float,
    nota_chave: float,
    min_inliers: int,
    faixas: dict,
) -> dict:
    """Levados e levados certos de um ponto da grade numa fonte do desenvolvimento.

    Args:
        fonte: ``(nome, gabarito, pasta, antigo.json)``.
        picos: ``{id: pico}`` da rede de capo nessa fonte.
        limiar: o limiar da 1045.
        nota_chave: nota mínima do quadro-chave.
        min_inliers: inliers mínimos.
        faixas: as faixas dos validadores.

    Returns:
        ``{"levados", "certos"}``.
    """
    _, gabarito_caminho, pasta, antigo_caminho = fonte
    gabarito = _ler_json(gabarito_caminho)["quadros"]
    antigo = _ler_json(antigo_caminho)["quadros"]
    indice = _indice(pasta)
    levados = certos = 0
    for ids in _por_video(indice).values():
        ids = [i for i in ids if i in antigo]
        chaves = chaves_do_video(ids, antigo, picos, nota_chave, faixas)
        for alvo in ids:
            registro = gabarito.get(alvo, {})
            pico = picos.get(alvo)
            visto = pico is not None and pico["nota"] >= limiar
            if visto or registro.get("braco") != "sim" or not tem_capo(registro):
                continue
            ponto = levar_no_video(
                alvo, chaves, indice, pasta, antigo, picos, min_inliers
            )
            if ponto is None:
                continue
            levados += 1
            certos += int(achado({"nota": 1.0, "ponto": ponto}, registro, 0.0))
    return {"levados": levados, "certos": certos}


def escolher() -> dict:
    """Escolhe ``NOTA_CHAVE`` e ``MIN_INLIERS`` no desenvolvimento (1043 e M39).

    Returns:
        A escolha e a tabela; também em ``ARQUIVO_ESCOLHA``.
    """
    escolha_1045 = _ler_json(ESCOLHA_1045)
    picos = _ler_json(PICOS_1045)[str(escolha_1045["semente"])]
    faixas = ler_faixas()
    tabela = []
    for nota_chave, minimo in itertools.product(NOTAS_CHAVE, MINIMOS_INLIERS):
        soma = {"levados": 0, "certos": 0}
        for fonte in DESENVOLVIMENTO:
            r = avaliar_ponto(
                fonte,
                picos[fonte[0]],
                escolha_1045["limiar"],
                nota_chave,
                minimo,
                faixas,
            )
            soma = {k: soma[k] + r[k] for k in soma}
        errados = soma["levados"] - soma["certos"]
        tabela.append(
            {
                "nota_chave": nota_chave,
                "min_inliers": minimo,
                **soma,
                "errados": errados,
                "cumpre": errados <= FRACAO_ERRADOS * soma["levados"]
                and soma["levados"] > 0,
            }
        )
    validos = [t for t in tabela if t["cumpre"]]
    melhor = (
        max(validos, key=lambda t: (t["certos"], t["min_inliers"], t["nota_chave"]))
        if validos
        else None
    )
    escolha = {
        "nota_chave": melhor["nota_chave"] if melhor else None,
        "min_inliers": melhor["min_inliers"] if melhor else None,
        "segue_para_prova": melhor is not None,
        "tabela": tabela,
    }
    gravar_atomico(ARQUIVO_ESCOLHA, escolha)
    return escolha


def _antigo_da_prova() -> dict:
    """As previsões do par antigo na M48 (a hipótese de referência da 1044).

    Returns:
        ``{id: entrada de previsto.json}``.
    """
    caminho = PASTA_HIPOTESES / RODADA_PROVA / f"{nome_da_hipotese(*REFERENCIA)}.json"
    return _ler_json(caminho)["quadros"]


def picos_da_prova() -> dict:
    """Os picos da rede de capo escolhida na 1045 em cada quadro da M48 (GPU).

    Returns:
        ``{id: pico ou None}``; também em ``ARQUIVO_PICOS``.
    """
    escolha_1045 = _ler_json(ESCOLHA_1045)
    antigo = _antigo_da_prova()
    indice = _indice(MAOS_M48)
    saida = {}
    with trava_gpu("maos", "~2 min"):
        modelo = carregar(f"{PREFIXO}{escolha_1045['semente']}")
        for id_q, item in indice.items():
            imagem = cv2.imread(str(MAOS_M48 / item["png"]))
            saida[id_q] = pico_do_quadro(modelo, imagem, antigo[id_q])
    gravar_atomico(ARQUIVO_PICOS, saida)
    return saida


def com_memoria(
    doc_1045: dict,
    registro_1045: dict,
    antigo: dict,
    picos: dict,
    escolha: dict,
    faixas: dict,
) -> tuple[dict, dict]:
    """A cadeia da 1048 sobre a da 1045 numa rodada.

    Args:
        doc_1045: ``previsto.json`` da cadeia da 1045.
        registro_1045: o registro do capo da 1045 por id (``visto``).
        antigo: previsões do par antigo por id.
        picos: ``{id: pico}``.
        escolha: ``nota_chave`` e ``min_inliers``.
        faixas: as faixas dos validadores.

    Returns:
        ``(previsto, registro)`` com os levados por quadro.
    """
    indice = _indice(MAOS_M48)
    quadros = dict(doc_1045["quadros"])
    registro = {}
    for ids in _por_video(indice).values():
        chaves = chaves_do_video(ids, antigo, picos, escolha["nota_chave"], faixas)
        for alvo in ids:
            if registro_1045[alvo]["visto"] or not antigo[alvo].get("achou"):
                continue
            ponto = levar_no_video(
                alvo, chaves, indice, MAOS_M48, antigo, picos, escolha["min_inliers"]
            )
            if ponto is None:
                continue
            x, y = ponto
            novo = nut_pela_conta(
                antigo[alvo], {"caixa": [x - 1, y - 1, x + 1, y + 1], "nota": 1.0}
            )
            if novo is None:
                registro[alvo] = {"levado": True, "casa": None}
                continue
            valido = validar(marcas_do_previsto(novo), faixas)["passa"]
            novo["sinalizado"] = bool(antigo[alvo]["sinalizado"] or not valido)
            quadros[alvo] = novo
            registro[alvo] = {
                "levado": True,
                "casa": novo["capo_casa"],
                "valido": valido,
                "ponto": ponto,
            }
    return dict(doc_1045, quadros=quadros), registro


def _sem_linhas(medida: dict) -> dict:
    """A medida sem as linhas quadro a quadro.

    Args:
        medida: saída de ``medir_por_grupo``.

    Returns:
        Cópia sem ``linhas``.
    """
    return {k: v for k, v in medida.items() if k != "linhas"}


def medir() -> dict:
    """Mede a cadeia da 1048 contra a da 1045 na M48, com as escolhas congeladas.

    Returns:
        As medidas, os critérios e o registro; também em ``ARQUIVO_MEDIDA``.
    """
    escolha_1045 = _ler_json(ESCOLHA_1045)
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    faixas = ler_faixas()
    antigo = _antigo_da_prova()
    picos = _ler_json(ARQUIVO_PICOS)
    gabarito = _ler_json(GABARITO_BRACO_M48)
    base, _ = cadeia(RODADA_PROVA, faixas, tomada=False)
    doc_1045, reg_1045 = com_capo(base, antigo, picos, escolha_1045["limiar"], faixas)
    doc_1048, reg_1048 = com_memoria(doc_1045, reg_1045, antigo, picos, escolha, faixas)
    m45 = medir_por_grupo(doc_1045, gabarito)
    m48 = medir_por_grupo(doc_1048, gabarito)
    n, r = m48["todos"], m45["todos"]
    certos_45 = {
        linha["id"]
        for linha in m45["linhas"]
        if not linha["sinalizado"] and linha["classe"] == "certo"
    }
    estragados = sum(
        1
        for linha in m48["linhas"]
        if linha["id"] in certos_45
        and not linha["sinalizado"]
        and linha["classe"] == "falso"
    )
    criterios = {
        "1_seguranca": {
            "falsos": [n["falsos_passam_n"], n["medidos"]],
            "passa": n["falsos_passam_n"] <= 0.05 * n["medidos"],
        },
        "2_ganho": {
            "certos_1048_1045": [n["entregue_certo"], r["entregue_certo"]],
            "passa": n["entregue_certo"] >= r["entregue_certo"] + 6,
        },
        "3_nao_estragar": {
            "estragados_de": [estragados, len(certos_45)],
            "passa": estragados <= 1,
        },
    }
    levados_certos = sum(
        1
        for id_q, reg in reg_1048.items()
        if "ponto" in reg
        and achado({"nota": 1.0, "ponto": reg["ponto"]}, gabarito["quadros"][id_q], 0.0)
    )
    resultado = {
        "escolha": escolha,
        "criterios": criterios,
        "cadeia_1048": _sem_linhas(m48),
        "cadeia_1045": _sem_linhas(m45),
        "levados": [levados_certos, len(reg_1048)],
        "registro_1045": reg_1045,
        "registro_1048": reg_1048,
    }
    gravar_atomico(ARQUIVO_MEDIDA, resultado)
    return resultado


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("picos", help="picos da rede de capo na M48 (GPU)")
    sub.add_parser("escolher", help="NOTA_CHAVE e MIN_INLIERS no desenvolvimento")
    sub.add_parser("medir", help="a cadeia da 1048 na M48")
    args = parser.parse_args()
    if args.comando == "picos":
        picos_da_prova()
        resultado = {"gravado": str(ARQUIVO_PICOS)}
    elif args.comando == "escolher":
        resultado = escolher()
    else:
        resultado = medir()
        resultado = {k: resultado[k] for k in ("criterios", "levados")}
    print(json.dumps(resultado, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
