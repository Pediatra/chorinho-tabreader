"""Rodada 1049, parte GPU: lê o vídeo, roda mãos e braço e grava o par ``chorinho/maos@1``.

A parte pura (checagens, eventos, formato) está em ``tab.maos.base``.

CLI: ``python -m tab.maos.base_gpu gerar --video V --produto P --audio A --saida PASTA``
(GPU e acervo) e ``python -m tab.maos.base_gpu folha --json X.maos.json`` (20 eventos ouro).
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from tab.comum import leitor
from tab.comum.arquivos import gravar_atomico
from tab.comum.caminhos import RAIZ, acervo
from tab.comum.gpu import trava_gpu
from tab.maos import cortes
from tab.maos.base import (
    BRACO_MAX_S,
    CAPO_DONO,
    FOLGA_CASA,
    FOLGA_S,
    LACUNA_TRILHA_S,
    LADOS,
    LIMIAR_CORTE,
    MEIA_JANELA_S,
    ORIGEM,
    PASSO_BRACO,
    PONTAS,
    PRESENCA_ATAQUE,
    QPS,
    VAOS_CORDA,
    braco_do_previsto,
    caixa_em,
    corpo_da_maior,
    dentro_do_quadro,
    distancia_na_celula,
    eventos,
    intervalos,
    melhor_mao,
    pontos_da_mao,
    resumo,
    sha256,
    trilhas,
    vazio,
)
from tab.maos.braco.validadores import cadeia_sem_tomada, ler_faixas, ler_hipoteses
from tab.maos.braco.validadores_gpu import hipoteses_na_pasta
from tab.maos.detector import DetectorMaos
from tab.maos.esquema import ESQUEMA, validar_par

SEMENTE_FOLHA = 20261049
#: O denso com o braço e os cortes, antes dos eventos (``montar`` parte dele).
ARQUIVO_BRUTO = "denso_bruto.npz"
N_FOLHA = 20


def _commit() -> str:
    """O commit atual (``git`` pelo host, se houver; senão ``desconhecido``).

    Returns:
        O hash.
    """
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except OSError, subprocess.CalledProcessError:
        return "desconhecido"


def _ler_maos(
    caminho_video: str,
    produto: dict,
    detector: DetectorMaos,
    mascara: np.ndarray,
    pasta_braco: Path,
    cortes_pares: list[float],
    itens: list[dict],
) -> list[tuple]:
    """Lê os quadros, acha as mãos e grava 1 quadro a cada ``PASSO_BRACO`` para o braço.

    Args:
        caminho_video: vídeo no acervo.
        produto: ``chorinho/video@1``.
        detector: o ``DetectorMaos``.
        mascara: máscara da tablatura para os cortes.
        pasta_braco: pasta dos quadros do braço.
        cortes_pares: lista a preencher com a distância ao quadro anterior.
        itens: lista a preencher com os itens do índice do braço.

    Returns:
        Uma linha por quadro: ``(t, maos, origem, corpo, caixa)``.
    """
    info = leitor.info(caminho_video)
    largura, altura = info["largura"], info["altura"]
    linhas: list[tuple] = []
    for t0, t1 in intervalos(produto, info["duracao_s"]):
        anterior = None
        for t, bgr in leitor.quadros_pts(caminho_video, t0, t1, QPS):
            caixa = caixa_em(produto, t)
            achado = detector.detectar(
                bgr, None if caixa is None else [int(v) for v in caixa]
            )
            maos = np.full((2, 21, 3), np.nan)
            origem = np.zeros(2, dtype=np.int8)
            for k, lado in enumerate(LADOS):
                mao = melhor_mao(achado["maos"], lado)
                if mao is None:
                    continue
                pontos = pontos_da_mao(mao)
                if not dentro_do_quadro(pontos[:, :2], largura, altura):
                    continue
                maos[k], origem[k] = pontos, ORIGEM[mao["origem"]]
            corpo = corpo_da_maior(achado["pessoas_wb"])
            if not dentro_do_quadro(
                corpo[np.isfinite(corpo[:, 0]), :2], largura, altura
            ):
                corpo = np.full((6, 3), np.nan)
            pequeno = cv2.resize(
                bgr,
                (cortes.LARGURA_ANALISE, cortes.ALTURA_ANALISE),
                interpolation=cv2.INTER_AREA,
            )
            atual = cortes.assinatura(pequeno, t, mascara)
            cortes_pares.append(
                0.0 if anterior is None else cortes.distancia(anterior, atual)[0]
            )
            anterior = atual
            i = len(linhas)
            if i % PASSO_BRACO == 0:
                relativo = f"quadros/b{i:06d}.png"
                cv2.imwrite(str(pasta_braco / relativo), bgr)
                itens.append(
                    {
                        "id": f"b{i:06d}",
                        "arquivo": caminho_video,
                        "t": t,
                        "png": relativo,
                        "largura": largura,
                        "altura": altura,
                        "indice_denso": i,
                    }
                )
            linhas.append((t, maos, origem, corpo, caixa))
    return linhas


def denso_das_maos(
    caminho_video: str, produto: dict, pasta_braco: Path
) -> tuple[dict[str, np.ndarray], np.ndarray, dict, dict]:
    """Mãos, corpo, caixa e cortes em cada quadro; grava os quadros do braço (GPU).

    Args:
        caminho_video: vídeo no acervo.
        produto: ``chorinho/video@1``.
        pasta_braco: onde gravar os quadros do braço e o ``indice.json``.

    Returns:
        ``(denso sem o braço, cortes por quadro, índice do braço, tempos)``.
    """
    info = leitor.info(caminho_video)
    largura, altura = info["largura"], info["altura"]
    linhas, cortes_pares, itens = [], [], []
    (pasta_braco / "quadros").mkdir(parents=True, exist_ok=True)
    mascara = cortes.mascara_da_tablatura(
        [t["painel"] for t in produto["telas"] if t.get("painel")], largura, altura
    )
    inicio = time.time()
    with trava_gpu("maos", "mãos da base, ~0,3 s por quadro"):
        detector = DetectorMaos("cuda")
        linhas = _ler_maos(
            caminho_video, produto, detector, mascara, pasta_braco, cortes_pares, itens
        )
    tempo_maos = time.time() - inicio
    arr = vazio(len(linhas))
    for i, (t, maos, origem, corpo, caixa) in enumerate(linhas):
        arr["pts"][i] = t
        arr["maos"][i] = maos
        arr["maos_origem"][i] = origem
        arr["corpo"][i] = corpo
        if caixa is not None:
            arr["tab_caixa"][i] = caixa
    arr["maos_trilha"] = trilhas(arr["maos_origem"] > 0, arr["pts"])
    indice = {"quadros": itens}
    gravar_atomico(pasta_braco / "indice.json", indice)
    return arr, np.asarray(cortes_pares), indice, {"maos_s": round(tempo_maos, 1)}


def braco_nos_quadros(pasta_braco: Path, indice: dict) -> tuple[dict, float]:
    """A cadeia da 1047 nos quadros do braço (GPU).

    Args:
        pasta_braco: pasta com ``quadros/`` e ``indice.json``.
        indice: o índice.

    Returns:
        ``({id: previsto}, segundos)``.
    """
    inicio = time.time()
    hipoteses_na_pasta(pasta_braco, indice, pasta_braco / "hipoteses")
    doc, _ = cadeia_sem_tomada(ler_hipoteses(pasta_braco / "hipoteses"), ler_faixas())
    return doc["quadros"], time.time() - inicio


def gerar(video: str, produto_caminho: Path, audio_caminho: Path, saida: Path) -> dict:
    """Gera o par ``.maos.json`` + ``.maos.npz`` de um vídeo e confere pelo esquema.

    Args:
        video: caminho relativo ao acervo (``canal/arquivo.mp4``).
        produto_caminho: ``chorinho/video@1``.
        audio_caminho: ``chorinho/audio@1``.
        saida: pasta de saída.

    Returns:
        O resumo, os tempos e os erros do esquema (vazio se válido).
    """
    produto = json.loads(produto_caminho.read_text(encoding="utf-8"))
    caminho_video = str(acervo() / video)
    info = leitor.info(caminho_video)
    saida.mkdir(parents=True, exist_ok=True)
    pasta_braco = saida / "braco"
    arr, cortes_pares, indice, tempos = denso_das_maos(
        caminho_video, produto, pasta_braco
    )
    previstos, tempo_braco = braco_nos_quadros(pasta_braco, indice)
    tempos["braco_s"] = round(tempo_braco, 1)
    tempos["quadros"] = len(arr["pts"])
    tempos["quadros_braco"] = len(indice["quadros"])
    for item in indice["quadros"]:
        i = item["indice_denso"]
        trastes, c1, c6, achou, conf = braco_do_previsto(
            previstos[item["id"]], info["largura"], info["altura"]
        )
        arr["braco_trastes"][i] = trastes
        arr["braco_corda1"][i] = c1
        arr["braco_corda6"][i] = c6
        arr["braco_achou"][i] = achou
        arr["braco_conf"][i] = conf
    with (saida / ARQUIVO_BRUTO).open("wb") as f:
        np.savez_compressed(f, cortes=cortes_pares, **arr)
    gravar_atomico(saida / "tempos.json", tempos)
    return montar(video, produto_caminho, audio_caminho, saida)


def montar(video: str, produto_caminho: Path, audio_caminho: Path, saida: Path) -> dict:
    """Monta os eventos e o par a partir do denso bruto já gravado (sem GPU).

    Args:
        video: caminho relativo ao acervo.
        produto_caminho: ``chorinho/video@1``.
        audio_caminho: ``chorinho/audio@1``.
        saida: pasta de saída (com ``ARQUIVO_BRUTO``).

    Returns:
        O resumo, os tempos e os erros do esquema (vazio se válido).
    """
    produto = json.loads(produto_caminho.read_text(encoding="utf-8"))
    audio = json.loads(audio_caminho.read_text(encoding="utf-8"))
    info = leitor.info(str(acervo() / video))
    nome = Path(video).stem
    with np.load(saida / ARQUIVO_BRUTO, allow_pickle=False) as dados:
        arr = {k: dados[k] for k in dados.files}
    cortes_pares = arr.pop("cortes")
    capo = CAPO_DONO.get(video.split("/")[0])
    evs = eventos(produto, audio, arr, cortes_pares, capo)
    caminho_npz = saida / f"{nome}.maos.npz"
    with caminho_npz.open("wb") as f:
        np.savez_compressed(f, **arr)
    doc = {
        "esquema": ESQUEMA,
        "produto": str(produto_caminho),
        "produto_sha256": sha256(produto_caminho),
        "audio": str(audio_caminho),
        "audio_sha256": sha256(audio_caminho),
        "denso": caminho_npz.name,
        "denso_sha256": sha256(caminho_npz),
        "video": {
            "arquivo": video,
            "fps": info["fps"],
            "largura": info["largura"],
            "altura": info["altura"],
        },
        "gerado_por": {
            "commit": _commit(),
            "detector_maos": "M1: RTMW Wholebody + MediaPipe (tab.maos.detector)",
            "detector_braco": "cadeia da 1047 (22 hipóteses, validadores, sem tomada)",
            "parametros": {
                "QPS": QPS,
                "PASSO_BRACO": PASSO_BRACO,
                "FOLGA_S": FOLGA_S,
                "MEIA_JANELA_S": MEIA_JANELA_S,
                "BRACO_MAX_S": BRACO_MAX_S,
                "FOLGA_CASA": FOLGA_CASA,
                "VAOS_CORDA": VAOS_CORDA,
                "PRESENCA_ATAQUE": PRESENCA_ATAQUE,
                "LACUNA_TRILHA_S": LACUNA_TRILHA_S,
                "LIMIAR_CORTE": LIMIAR_CORTE,
            },
        },
        "violao": {
            "canhoto": False,
            "capotraste": capo,
            "capotraste_fonte": None if capo is None else "dono",
        },
        "eventos": evs,
        "resumo": resumo(evs),
    }
    caminho_json = saida / f"{nome}.maos.json"
    gravar_atomico(caminho_json, doc)
    erros = validar_par(doc, arr)
    tempos = json.loads((saida / "tempos.json").read_text(encoding="utf-8"))
    relatorio = {"resumo": doc["resumo"], "tempos": tempos, "erros": erros}
    gravar_atomico(saida / "relatorio.json", relatorio)
    return relatorio


def _quadro_da_k2(
    arr: dict, ev: dict, trastes: np.ndarray, c1: np.ndarray, c6: np.ndarray
) -> int:
    """O quadro da janela em que uma ponta da mão do braço fica mais perto da célula.

    Args:
        arr: o denso.
        ev: o evento (com ``janela``, ``corda`` e ``casa``).
        trastes: ``(25, 2)`` do quadro de braço usado pela K2.
        c1: reta da corda 1.
        c6: reta da corda 6.

    Returns:
        O índice do quadro; o mais perto de ``t_som`` se nenhuma ponta cai na casa.
    """
    melhor, indice = np.inf, int(np.argmin(np.abs(arr["pts"] - ev["t_som"])))
    for i in range(ev["janela"][0], ev["janela"][1]):
        for ponta in PONTAS:
            ponto = arr["maos"][i, 0, ponta, :2]
            if not np.all(np.isfinite(ponto)):
                continue
            d = distancia_na_celula(trastes, c1, c6, ev["corda"], ev["casa"], ponto)
            if d < melhor:
                melhor, indice = d, i
    return indice


def _celula_na_corda(
    trastes: np.ndarray, a: np.ndarray, b: np.ndarray, casa: int
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """O trecho da reta da corda que a K2 aceita (traste ``casa − 1`` a ``casa`` + folga).

    Args:
        trastes: ``(25, 2)`` (0 = nut).
        a: um ponto da reta da corda.
        b: outro ponto da reta da corda.
        casa: ≥ 1.

    Returns:
        Os dois extremos em pixels, ou ``None`` sem os trastes.
    """
    t0, t1 = trastes[casa - 1], trastes[casa]
    if not (np.all(np.isfinite(t0)) and np.all(np.isfinite(t1))):
        return None
    eixo = t1 - t0
    passo = float((b - a) @ eixo)
    if passo == 0:
        return None
    extremos = []
    for s in (0.0, 1.0 + FOLGA_CASA):
        t = (s * float(eixo @ eixo) - float((a - t0) @ eixo)) / passo
        q = a + t * (b - a)
        extremos.append((int(q[0]), int(q[1])))
    return extremos[0], extremos[1]


def folha(caminho_json: Path) -> Path:
    """Folha de ``N_FOLHA`` eventos ouro sorteados: braço, célula e pontas desenhados.

    Args:
        caminho_json: o ``.maos.json``.

    Returns:
        O caminho da folha.
    """
    doc = json.loads(caminho_json.read_text(encoding="utf-8"))
    with np.load(caminho_json.parent / doc["denso"], allow_pickle=False) as dados:
        arr = {k: dados[k] for k in dados.files}
    ouro = [e for e in doc["eventos"] if e["nivel"] == "ouro"]
    escolhidos = random.Random(SEMENTE_FOLHA).sample(ouro, min(N_FOLHA, len(ouro)))
    celulas = []
    entregues = np.flatnonzero(arr["braco_achou"] & (arr["braco_conf"] == 1.0))
    for ev in escolhidos:
        j = int(entregues[np.argmin(np.abs(arr["pts"][entregues] - ev["t_som"]))])
        trastes, c1, c6 = (
            arr["braco_trastes"][j],
            arr["braco_corda1"][j],
            arr["braco_corda6"][j],
        )
        i = _quadro_da_k2(arr, ev, trastes, c1, c6)
        bgr = leitor.quadro_em(
            str(acervo() / doc["video"]["arquivo"]), float(arr["pts"][i])
        )
        for p in trastes:
            if np.all(np.isfinite(p)):
                cv2.circle(bgr, (int(p[0]), int(p[1])), 5, (0, 255, 0), -1)
        for c in (c1, c6):
            cv2.line(
                bgr,
                tuple(int(v) for v in c[0]),
                tuple(int(v) for v in c[1]),
                (0, 255, 0),
                1,
            )
        f = (ev["corda"] - 1) / 5.0
        a = c1[0] + (c6[0] - c1[0]) * f
        b = c1[1] + (c6[1] - c1[1]) * f
        cv2.line(
            bgr, tuple(int(v) for v in a), tuple(int(v) for v in b), (0, 200, 255), 2
        )
        celula = _celula_na_corda(trastes, a, b, ev["casa"])
        if celula is not None:
            cv2.line(bgr, celula[0], celula[1], (0, 0, 255), 6)
        mao = arr["maos"][i, 0]
        for ponta in PONTAS:
            if np.all(np.isfinite(mao[ponta, :2])):
                cv2.circle(
                    bgr, (int(mao[ponta, 0]), int(mao[ponta, 1])), 7, (255, 0, 255), 2
                )
        texto = f"corda {ev['corda']} casa {ev['casa']} t={ev['t_som']:.2f}"
        cv2.rectangle(bgr, (0, 0), (900, 50), (0, 0, 0), -1)
        cv2.putText(
            bgr, texto, (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2
        )
        celulas.append(cv2.resize(bgr, (640, 360)))
    while len(celulas) % 4:
        celulas.append(np.zeros_like(celulas[0]))
    imagem = np.vstack(
        [np.hstack(celulas[k : k + 4]) for k in range(0, len(celulas), 4)]
    )
    destino = caminho_json.parent / "folha_ouro.jpg"
    cv2.imwrite(str(destino), imagem)
    return destino


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 se o par saiu válido (``gerar``) ou a folha foi gravada; 1 com erros.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p_gerar = sub.add_parser("gerar", help="o par de um vídeo (GPU, acervo)")
    p_montar = sub.add_parser("montar", help="só os eventos, do denso bruto (sem GPU)")
    for p in (p_gerar, p_montar):
        p.add_argument("--video", required=True, help="canal/arquivo.mp4 no acervo")
        p.add_argument("--produto", required=True, type=Path)
        p.add_argument("--audio", required=True, type=Path)
        p.add_argument("--saida", required=True, type=Path)
    p_folha = sub.add_parser("folha", help="folha de 20 eventos ouro")
    p_folha.add_argument("--json", required=True, type=Path)
    args = parser.parse_args()
    if args.comando == "folha":
        print(folha(args.json))
        return 0
    acao = gerar if args.comando == "gerar" else montar
    relatorio = acao(args.video, args.produto, args.audio, args.saida)
    print(json.dumps(relatorio, ensure_ascii=False, indent=1))
    return 1 if relatorio["erros"] else 0


if __name__ == "__main__":
    sys.exit(main())
