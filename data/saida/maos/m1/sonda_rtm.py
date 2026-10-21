"""Sondagem M1 (rascunho, fora do pacote tab/): RTMPose via rtmlib nos 36 quadros do piloto.

Compara dois candidatos com o rótulo PROVISÓRIO do agente (o mesmo do M0):

- Hand: RTMDet-nano de mão + RTMPose-m hand5 (21 pontos, SEM lado);
- Wholebody: YOLOX-m (pessoa) + RTMW-DW-X-L (133 pontos por pessoa, com as duas mãos).

Roda dentro do container ``chorinho-maos-rtm:dev``, com o repositório em ``/app`` e o
cache de quadros em ``/cache`` (somente leitura). Entrada: o rótulo e o censo do M0.

Uso (dentro do container)::

    python data/saida/maos/m1/sonda_rtm.py
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import cv2
import numpy as np
from rtmlib import Hand, Wholebody

RAIZ = Path("/app")
ROTULO = RAIZ / "data/saida/maos/rotulo_agente_piloto.json"
CENSO = RAIZ / "data/saida/maos/piloto_c0.3_b2.jsonl"
CACHE_PNG = Path("/cache/png")
SAIDA = RAIZ / "data/saida/maos/m1"

#: Limiares da média dos 21 pontos de uma mão do Wholebody ("a mão existe" quando passa).
LIMIARES = (0.3, 0.5)
#: Score mínimo de ponto para DESENHAR (não entra em nenhuma decisão).
SCORE_DESENHO = 0.3
#: Faixas do COCO-WholeBody SEM to_openpose: raiz (pulso) da mão esquerda = 91 e da
#: direita = 112; cada faixa tem 21 pontos (91-111 e 112-132).
FAIXA_ESQ = slice(91, 112)
FAIXA_DIR = slice(112, 133)
#: Pulsos do corpo, COCO-17: 9 = left_wrist, 10 = right_wrist (conferido no coco133.py).
PULSO_ESQ_CORPO, PULSO_DIR_CORPO = 9, 10
#: Cores em BGR.
AMARELO = (0, 255, 255)  # Hand
MAGENTA = (255, 0, 255)  # Wholebody, mão com média > 0,3
VERDE = (0, 255, 0)  # Wholebody, mão com média > 0,5
CINZA = (200, 200, 200)  # caixa da pessoa (YOLOX do Wholebody)


def caminho_quadro(chave: str, quadro: int) -> Path:
    """Caminho do PNG de um quadro de presença no cache de quadros.

    Args:
        chave: chave de retomada do vídeo no censo do M0.
        quadro: índice do quadro de presença (0 a 11).

    Returns:
        Caminho de ``presenca_<quadro>.png`` dentro da pasta do vídeo.
    """
    digest = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]
    return CACHE_PNG / digest / f"presenca_{quadro:02d}.png"


def ponto(kp: np.ndarray, sc: np.ndarray) -> list[float]:
    """Um ponto como ``[x, y, score]`` com coordenadas de 1 casa decimal.

    Args:
        kp: coordenadas ``(x, y)`` do ponto.
        sc: score do ponto.

    Returns:
        Lista ``[x, y, score]``.
    """
    return [round(float(kp[0]), 1), round(float(kp[1]), 1), float(sc)]


def pontos(kp: np.ndarray, sc: np.ndarray) -> list[list[float]]:
    """Todos os pontos de uma mão ou de uma pessoa como ``[x, y, score]``.

    Args:
        kp: coordenadas ``(N, 2)``.
        sc: scores ``(N,)``.

    Returns:
        Lista de N pontos.
    """
    return [ponto(k, s) for k, s in zip(kp, sc)]


def mao(kp: np.ndarray, sc: np.ndarray) -> dict:
    """Uma mão do Wholebody: caixa dos pontos, média dos scores e os pontos.

    Args:
        kp: coordenadas ``(21, 2)``.
        sc: scores ``(21,)``.

    Returns:
        Dicionário com ``caixa`` (dos 21 pontos), ``media`` (sem arredondar) e ``pts``.
    """
    caixa = [
        round(float(kp[:, 0].min()), 1),
        round(float(kp[:, 1].min()), 1),
        round(float(kp[:, 0].max()), 1),
        round(float(kp[:, 1].max()), 1),
    ]
    return {"caixa": caixa, "media": float(sc.mean()), "pts": pontos(kp, sc)}


def rodar_hand(hand: Hand, img: np.ndarray) -> dict:
    """Mãos do Hand num quadro, pelo mesmo caminho de ``Hand.__call__``.

    O ``Hand.__call__`` esconde as caixas do detector; aqui o detector e a pose são
    chamados em sequência para guardar as caixas. Quando o detector não acha mão, a
    ``rtmlib`` chamaria a pose com bboxes vazio, e o RTMPose usa o QUADRO INTEIRO como
    bbox: isso é registrado à parte em ``sem_det_lib`` e NÃO entra como mão achada.

    Args:
        hand: instância de ``rtmlib.Hand``.
        img: quadro em BGR (OpenCV).

    Returns:
        ``tempo_s``, ``maos`` (caixa, pontos e média por mão) e ``sem_det_lib`` (None
        quando havia detecção; senão o que a rtmlib daria pelo quadro inteiro).
    """
    inicio = time.perf_counter()
    caixas = np.asarray(hand.det_model(img), dtype=float).reshape(-1, 4)
    if len(caixas):
        kp, sc = hand.pose_model(img, bboxes=caixas)
    else:
        kp, sc = np.zeros((0, 21, 2)), np.zeros((0, 21))
    tempo = time.perf_counter() - inicio
    sem_det_lib = None
    if not len(caixas):
        kp2, sc2 = hand.pose_model(img, bboxes=[])
        sem_det_lib = {"media_quadro_inteiro": float(sc2[0].mean())}
    maos = []
    for c, k, s in zip(caixas, kp, sc):
        m = mao(k, s)
        m["caixa_det"] = [round(float(v), 1) for v in c]
        maos.append(m)
    return {"tempo_s": tempo, "maos": maos, "sem_det_lib": sem_det_lib}


def rodar_wb(wb: Wholebody, img: np.ndarray) -> dict:
    """Pessoas e mãos do Wholebody num quadro, pelo caminho de ``Wholebody.__call__``.

    Como em ``rodar_hand``: detector e pose em sequência, e o caso sem pessoa é
    registrado à parte (a rtmlib usaria o quadro inteiro como pessoa).

    Args:
        wb: instância de ``rtmlib.Wholebody``, com ``to_openpose=False``.
        img: quadro em BGR (OpenCV).

    Returns:
        ``tempo_s``, ``pessoas`` (caixa da pessoa, média do corpo, mão esquerda e
        direita, e os pulsos do corpo) e ``sem_det_lib``.
    """
    inicio = time.perf_counter()
    caixas = np.asarray(wb.det_model(img), dtype=float).reshape(-1, 4)
    if len(caixas):
        kp, sc = wb.pose_model(img, bboxes=caixas)
    else:
        kp, sc = np.zeros((0, 133, 2)), np.zeros((0, 133))
    tempo = time.perf_counter() - inicio
    sem_det_lib = None
    if not len(caixas):
        kp2, sc2 = wb.pose_model(img, bboxes=[])
        sem_det_lib = {
            "media_corpo_quadro_inteiro": float(sc2[0, :17].mean()),
            "media_esq_quadro_inteiro": float(sc2[0, FAIXA_ESQ].mean()),
            "media_dir_quadro_inteiro": float(sc2[0, FAIXA_DIR].mean()),
        }
    pessoas = []
    for c, k, s in zip(caixas, kp, sc):
        pessoas.append(
            {
                "caixa": [round(float(v), 1) for v in c],
                "media_corpo": float(s[:17].mean()),
                "esquerda": mao(k[FAIXA_ESQ], s[FAIXA_ESQ]),
                "direita": mao(k[FAIXA_DIR], s[FAIXA_DIR]),
                "pulsos_corpo": {
                    "esq": ponto(k[PULSO_ESQ_CORPO], s[PULSO_ESQ_CORPO]),
                    "dir": ponto(k[PULSO_DIR_CORPO], s[PULSO_DIR_CORPO]),
                },
            }
        )
    return {"tempo_s": tempo, "pessoas": pessoas, "sem_det_lib": sem_det_lib}


def achou_wb(r: dict, lado: str, limiar: float) -> bool:
    """Se alguma pessoa tem a mão ``lado`` com média de score acima do limiar.

    Args:
        r: saída de ``rodar_wb``.
        lado: ``esquerda`` (do sujeito) ou ``direita``.
        limiar: limiar da média dos 21 pontos.

    Returns:
        True quando a mão existe no quadro.
    """
    return any(p[lado]["media"] > limiar for p in r["pessoas"])


def checar_lado(wbs: list[dict]) -> dict:
    """Confere se ``esquerda`` (índice 91) é a mão do pulso 9 do corpo, e ``direita`` a do 10.

    Só conta quando o pulso do corpo e a raiz da mão têm score acima de 0,3, e a raiz
    fica mais perto do pulso do próprio lado do que do outro.

    Args:
        wbs: saídas de ``rodar_wb`` de todos os quadros.

    Returns:
        ``{"esquerda": [checados, de_acordo], "direita": [checados, de_acordo]}``.
    """
    cont = {"esquerda": [0, 0], "direita": [0, 0]}
    for r in wbs:
        for p in r["pessoas"]:
            pe, pd = p["pulsos_corpo"]["esq"], p["pulsos_corpo"]["dir"]
            if pe[2] <= SCORE_DESENHO or pd[2] <= SCORE_DESENHO:
                continue
            for lado, certo, errado in (("esquerda", pe, pd), ("direita", pd, pe)):
                raiz = p[lado]["pts"][0]
                if raiz[2] <= SCORE_DESENHO:
                    continue
                cont[lado][0] += 1
                d_certo = math.dist(raiz[:2], certo[:2])
                d_errado = math.dist(raiz[:2], errado[:2])
                cont[lado][1] += int(d_certo < d_errado)
    return cont


def desenhar(img: np.ndarray, hand_r: dict, wb_r: dict) -> np.ndarray:
    """Cópia do quadro com as caixas e os pontos de cada detector.

    Args:
        img: quadro em BGR.
        hand_r: saída de ``rodar_hand``.
        wb_r: saída de ``rodar_wb``.

    Returns:
        Quadro desenhado (BGR), no tamanho original.
    """
    out = img.copy()
    esp = max(2, out.shape[1] // 400)
    for p in wb_r["pessoas"]:
        x0, y0, x1, y1 = (int(v) for v in p["caixa"])
        cv2.rectangle(out, (x0, y0), (x1, y1), CINZA, esp)
    for m in hand_r["maos"]:
        x0, y0, x1, y1 = (int(v) for v in m["caixa"])
        cv2.rectangle(out, (x0, y0), (x1, y1), AMARELO, esp)
        cv2.putText(out, "h", (x0, max(20, y0 - 6)), 0, esp * 0.6, AMARELO, esp)
        for x, y, s in m["pts"]:
            if s >= SCORE_DESENHO:
                cv2.circle(out, (int(x), int(y)), esp * 2, AMARELO, -1)
    for limiar, cor in ((0.3, MAGENTA), (0.5, VERDE)):
        for p in wb_r["pessoas"]:
            for lado, letra in (("esquerda", "E"), ("direita", "D")):
                m = p[lado]
                if m["media"] <= limiar:
                    continue
                x0, y0, x1, y1 = (int(v) for v in m["caixa"])
                cv2.rectangle(out, (x0, y0), (x1, y1), cor, esp)
                cv2.putText(out, letra, (x0, max(20, y0 - 6)), 0, esp * 0.6, cor, esp)
                for x, y, s in m["pts"]:
                    if s >= SCORE_DESENHO:
                        cv2.circle(out, (int(x), int(y)), esp * 2, cor, -1)
    return out


def texto(img: np.ndarray, msg: str, y: int, escala: float) -> None:
    """Texto branco com contorno preto, para ler em qualquer fundo.

    Args:
        img: imagem a escrever (alterada no lugar).
        msg: texto em ASCII (o cv2 não desenha acentos).
        y: linha de base em pixels.
        escala: escala da fonte do cv2.
    """
    cv2.putText(img, msg, (5, y), 0, escala, (0, 0, 0), 3)
    cv2.putText(img, msg, (5, y), 0, escala, (255, 255, 255), 1)


def celula(it: dict) -> np.ndarray:
    """Uma célula 640x480 da folha: quadro desenhado e rodapé com o rótulo e as afirmações.

    Args:
        it: item já processado (``img``, ``rot``, ``hand``, ``wb``).

    Returns:
        Imagem 480x640 em BGR.
    """
    img = desenhar(it["img"], it["hand"], it["wb"])
    h, w = img.shape[:2]
    escala = min(640 / w, 420 / h)
    img = cv2.resize(img, (round(w * escala), round(h * escala)), interpolation=cv2.INTER_AREA)
    cel = np.zeros((480, 640, 3), np.uint8)
    cel[: img.shape[0], : img.shape[1]] = img
    r = it["rot"]
    canal = r["canal"].encode("ascii", "replace").decode("ascii")
    texto(cel, "amarelo=Hand  magenta=WB>0.3  verde=WB>0.5  cinza=pessoa", 14, 0.4)
    texto(cel, f"n={r['n']} q={r['quadro']} {canal[:24]}", 438, 0.42)
    texto(cel, f"rotulo E={r['esquerda']} D={r['direita']}", 458, 0.42)
    afirma = (
        f"Hand={len(it['hand']['maos'])} | "
        f"WB0.3 E={int(achou_wb(it['wb'], 'esquerda', 0.3))} "
        f"D={int(achou_wb(it['wb'], 'direita', 0.3))} | "
        f"WB0.5 E={int(achou_wb(it['wb'], 'esquerda', 0.5))} "
        f"D={int(achou_wb(it['wb'], 'direita', 0.5))}"
    )
    texto(cel, afirma, 478, 0.42)
    return cel


def tabela(itens: list[dict]) -> dict:
    """Imprime a tabela da sondagem e devolve os números.

    Args:
        itens: itens processados, na ordem do rótulo.

    Returns:
        Resumo com as contagens de Hand e de Wholebody por limiar.
    """
    resumo: dict = {}
    # Hand: sem lado; compara o número de mãos com o número de mãos visíveis no rótulo.
    achadas_todas = sum(len(it["hand"]["maos"]) for it in itens)
    completos = [it for it in itens if it["rot"]["esquerda"] is not None and it["rot"]["direita"] is not None]
    ach_c = vis_c = mais = menos = iguais = 0
    for it in completos:
        r = it["rot"]
        n_vis = int(r["esquerda"] == 1) + int(r["direita"] == 1)
        n = len(it["hand"]["maos"])
        ach_c += n
        vis_c += n_vis
        if n > n_vis:
            mais += 1
        elif n < n_vis:
            menos += 1
        else:
            iguais += 1
    resumo["hand"] = {
        "maos_achadas_total": achadas_todas,
        "quadros_rotulo_completo": len(completos),
        "maos_achadas_rotulo_completo": ach_c,
        "maos_visiveis_rotulo": vis_c,
        "quadros_mais_maos_que_rotulo": mais,
        "quadros_menos_maos_que_rotulo": menos,
        "quadros_igual_contagem": iguais,
        "quadros_sem_det_lib": sum(it["hand"]["sem_det_lib"] is not None for it in itens),
    }
    print("Hand (RTMDet-nano hand + RTMPose-m hand5), sem lado:")
    print(
        f"  maos achadas (rotulo completo) {ach_c} / visiveis {vis_c}; "
        f"quadros com MAIS maos que o rotulo {mais}, com MENOS {menos}, "
        f"com a mesma contagem {iguais} (de {len(completos)} quadros com rotulo completo)."
    )
    print(
        f"  quadros em que o detector nao achou mao (rtmlib cairia no quadro inteiro): "
        f"{resumo['hand']['quadros_sem_det_lib']}"
    )

    # Wholebody: mesmo critério de comparar.py, por lado e por limiar.
    print()
    print("| detector | quadro certo | mão esquerda achada | mão direita achada | falsas |")
    print("| --- | --- | --- | --- | --- |")
    resumo["wb"] = {}
    for limiar in LIMIARES:
        cont = {"esquerda": [0, 0, 0], "direita": [0, 0, 0]}  # achadas, visiveis, falsas
        ok = n = 0
        for it in itens:
            certo = True
            for lado in ("esquerda", "direita"):
                v = it["rot"][lado]
                if v is None:
                    continue
                a = achou_wb(it["wb"], lado, limiar)
                if v:
                    cont[lado][1] += 1
                    cont[lado][0] += int(a)
                else:
                    cont[lado][2] += int(a)
                certo &= a == bool(v)
            n += 1
            ok += int(certo)
        falsas = cont["esquerda"][2] + cont["direita"][2]
        print(
            f"| Wholebody > {limiar} | {ok}/{n} | "
            f"E: {cont['esquerda'][0]}/{cont['esquerda'][1]} | "
            f"D: {cont['direita'][0]}/{cont['direita'][1]} | {falsas} |"
        )
        resumo["wb"][str(limiar)] = {"quadro_certo": ok, "quadros": n, "cont": cont}
    print(
        "| Hand (sem lado) | n/a | maos: "
        f"{ach_c}/{vis_c} (contagem) | - | quadros com mais maos: {mais} |"
    )
    return resumo


def main() -> None:
    """Roda os dois detectores nos 36 quadros do rótulo, imprime, grava JSON e folhas."""
    rotulos = json.loads(ROTULO.read_text(encoding="utf-8"))["rotulos"]
    censo = {}
    for linha in CENSO.read_text(encoding="utf-8").splitlines():
        reg = json.loads(linha)
        censo[reg["arquivo"]] = reg
    itens = []
    for rot in rotulos:
        arq = caminho_quadro(censo[rot["arquivo"]]["chave"], rot["quadro"])
        img = cv2.imread(str(arq))
        if img is None:
            raise SystemExit(f"PNG do quadro nao encontrado ou ilegivel: {arq}")
        itens.append({"rot": rot, "png": str(arq), "img": img})
    print(f"{len(itens)} quadros lidos do cache (BGR, sem conversao de cor).", flush=True)

    inicio = time.perf_counter()
    hand = Hand(backend="onnxruntime", device="cpu")
    wb = Wholebody(backend="onnxruntime", device="cpu", to_openpose=False)
    print(f"modelos carregados em {time.perf_counter() - inicio:.1f} s", flush=True)
    print(
        "saidas do det de mao:",
        [(o.name, o.shape) for o in hand.det_model.session.get_outputs()],
        "score_thr",
        hand.det_model.score_thr,
        flush=True,
    )
    print(
        "saidas do det de pessoa:",
        [(o.name, o.shape) for o in wb.det_model.session.get_outputs()],
        "score_thr",
        wb.det_model.score_thr,
        flush=True,
    )

    # Aquecimento (não medido, não gravado): a primeira chamada de sessão é mais lenta.
    rodar_hand(hand, itens[0]["img"])
    rodar_wb(wb, itens[0]["img"])

    for k, it in enumerate(itens, 1):
        it["hand"] = rodar_hand(hand, it["img"])
        it["wb"] = rodar_wb(wb, it["img"])
        pessoas = len(it["wb"]["pessoas"])
        print(
            f"{k:2d}/{len(itens)} n={it['rot']['n']:2d} q={it['rot']['quadro']:2d} "
            f"hand={len(it['hand']['maos'])} wb_pessoas={pessoas} "
            f"t_hand={it['hand']['tempo_s']:.2f}s t_wb={it['wb']['tempo_s']:.2f}s",
            flush=True,
        )

    print()
    resumo = tabela(itens)
    print()
    lado = checar_lado([it["wb"] for it in itens])
    print(
        "checagem de lado (raiz da mao vs pulso do corpo 9/10): "
        f"esquerda {lado['esquerda'][1]}/{lado['esquerda'][0]} de acordo, "
        f"direita {lado['direita'][1]}/{lado['direita'][0]} de acordo"
    )
    t_hand = [it["hand"]["tempo_s"] for it in itens]
    t_wb = [it["wb"]["tempo_s"] for it in itens]
    print(
        f"tempo medio por quadro (CPU, {len(itens)} quadros, sem aquecimento): "
        f"Hand {np.mean(t_hand):.2f} s, Wholebody {np.mean(t_wb):.2f} s"
    )
    resumo["tempo_medio_s"] = {"hand": float(np.mean(t_hand)), "wholebody": float(np.mean(t_wb))}
    resumo["checagem_lado"] = lado

    quadros = []
    for it in itens:
        r = it["rot"]
        quadros.append(
            {
                "n": r["n"],
                "canal": r["canal"],
                "arquivo": r["arquivo"],
                "quadro": r["quadro"],
                "png": it["png"],
                "altura": int(it["img"].shape[0]),
                "largura": int(it["img"].shape[1]),
                "rotulo": {"esquerda": r["esquerda"], "direita": r["direita"]},
                "afirma": {
                    "hand_n": len(it["hand"]["maos"]),
                    "wb": {
                        str(lim): {
                            "esquerda": achou_wb(it["wb"], "esquerda", lim),
                            "direita": achou_wb(it["wb"], "direita", lim),
                        }
                        for lim in LIMIARES
                    },
                },
                "hand": it["hand"],
                "wholebody": it["wb"],
            }
        )
    saida = {
        "modelos": {
            "hand": "RTMDet-nano hand (rtmdet_nano_8xb32-300e_hand-267f9c8f) + RTMPose-m hand5 "
            "(rtmpose-m_simcc-hand5_pt-aic-coco_210e-256x256-74fb594_20230320), modo lightweight",
            "wholebody": "YOLOX-m humanart (yolox_m_8xb8-300e_humanart-c2c7a14a) + RTMW-DW-X-L "
            "cocktail14 (rtmw-dw-x-l_simcc-cocktail14_270e-256x192_20231122), modo balanced",
            "to_openpose": False,
        },
        "resumo": resumo,
        "quadros": quadros,
    }
    (SAIDA / "sonda_rtm.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    cels = [celula(it) for it in itens]
    for k0 in range(0, len(cels), 10):
        bloco = cels[k0 : k0 + 10]
        while len(bloco) < 10:
            bloco.append(np.zeros((480, 640, 3), np.uint8))
        linhas = [np.hstack(bloco[i : i + 2]) for i in range(0, 10, 2)]
        cv2.imwrite(
            str(SAIDA / f"folha_rtm_{k0 // 10 + 1}.jpg"),
            np.vstack(linhas),
            [cv2.IMWRITE_JPEG_QUALITY, 85],
        )
    print(f"folhas gravadas em {SAIDA}", flush=True)


if __name__ == "__main__":
    main()
