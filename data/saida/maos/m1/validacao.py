"""Validação M1 (rascunho, fora do pacote tab/): MediaPipe (censo M0) x RTMPose Wholebody.

Conjunto de 90 quadros FORA do ajuste: 30 da conferência (C01..C30) e 60 novos
(N01..N60), sorteados fora do piloto e da conferência. O MediaPipe vem do censo (nada a
rodar). O Wholebody roda em duas variantes: imagem em BGR (como a rtmlib faz) e imagem em
RGB passada SÓ para a pose. O detector de pessoa (YOLOX) recebe sempre BGR.

Saídas em data/saida/maos/m1/: validacao_conjunto.json, validacao_deteccoes.json,
rotular_{1..9}.jpg (sem detecção, para rotular a olho) e deteccoes_{1..9}.jpg (com
detecções).

Uso (dentro do container chorinho-maos-rtm:dev, CPU)::

    python data/saida/maos/m1/validacao.py
"""

from __future__ import annotations

import hashlib
import json
import random
import time
import unicodedata
from pathlib import Path

import cv2
import numpy as np
from rtmlib import Wholebody

from tab.maos_conferencia import escolher_quadro, sortear
from tab.maos_tabela import resumo_do_quadro

RAIZ = Path("/app")
SAIDA = RAIZ / "data/saida/maos"
M1 = SAIDA / "m1"
CENSO = SAIDA / "censo_maos.jsonl"
PILOTO = SAIDA / "piloto_c0.3_b2.jsonl"
CONFERENCIA = SAIDA / "conferencia_30.json"
CACHE_PNG = Path("/cache/png")

SEMENTE_SORTEIO = 20261014
SEMENTE_QUADROS = 20261015
N_NOVOS = 60

#: Limiar da média dos 21 scores de uma mão do Wholebody ("a mão existe" quando passa).
LIMIAR = 0.5
#: Abaixo deste limiar a mão nem é desenhada; entre 0,3 e 0,5 é desenhada fina e minúscula.
LIMIAR_DESENHO = 0.3
#: Score mínimo de ponto para desenhar (não entra em nenhuma decisão).
SCORE_PONTO = 0.3
#: Faixas do COCO-WholeBody sem to_openpose: mão esquerda 91-111, direita 112-132.
FAIXA_ESQ = slice(91, 112)
FAIXA_DIR = slice(112, 133)

LARGURA_CELULA = 640
ALTURA_CELULA = 480
ALTURA_RODAPE = 56
COLUNAS = 2
POR_FOLHA = 10
QUALIDADE_JPEG = 90

#: Cores em BGR.
AMARELO = (0, 255, 255)  # MediaPipe
CINZA = (200, 200, 200)  # MediaPipe, mão dentro da tablatura
VERDE = (0, 255, 0)  # Wholebody BGR
MAGENTA = (255, 0, 255)  # Wholebody RGB
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
FONTE = cv2.FONT_HERSHEY_SIMPLEX


def ascii_(texto: str) -> str:
    """Texto sem acento, porque as fontes do OpenCV são só ASCII.

    Args:
        texto: texto com acentos.

    Returns:
        O mesmo texto em ASCII.
    """
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def caminho_quadro(chave: str, quadro: int) -> Path:
    """Caminho do PNG de um quadro de presença no cache (mesmo layout da sondagem).

    Args:
        chave: chave de retomada do vídeo no censo.
        quadro: índice ``i`` do quadro de presença.

    Returns:
        ``presenca_<quadro>.png`` dentro da pasta do vídeo no cache.
    """
    digest = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]
    return CACHE_PNG / digest / f"presenca_{quadro:02d}.png"


def ler_imagem(chave: str, quadro: int) -> np.ndarray:
    """Lê o PNG do quadro em BGR, o formato que o OpenCV dá.

    Args:
        chave: chave do vídeo.
        quadro: índice ``i`` do quadro.

    Returns:
        Imagem BGR.

    Raises:
        SystemExit: se o PNG não existe ou não lê.
    """
    arq = caminho_quadro(chave, quadro)
    img = cv2.imread(str(arq))
    if img is None:
        raise SystemExit(f"PNG do quadro nao encontrado ou ilegivel: {arq}")
    return img


def ler_jsonl(caminho: Path) -> list[dict]:
    """Lê um jsonl (um registro por linha), pulando linhas em branco.

    Args:
        caminho: arquivo jsonl.

    Returns:
        Registros na ordem do arquivo.
    """
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas if linha.strip()]


def quadro_do_censo(video: dict, i: int) -> dict:
    """Registro do quadro ``i`` dentro de um vídeo do censo.

    Args:
        video: registro do censo.
        i: índice do quadro.

    Returns:
        O registro do quadro.

    Raises:
        SystemExit: se o quadro não existe no vídeo.
    """
    for q in video["quadros"]:
        if q["i"] == i:
            return q
    raise SystemExit(f"quadro {i} nao existe no video {video['chave']}")


def item(id_: str, grupo: str, video: dict, quadro: dict) -> dict:
    """Um dos 90 quadros do conjunto, com os campos que vão para o JSON.

    Args:
        id_: C01..C30 ou N01..N60.
        grupo: ``conferencia`` ou ``novo``.
        video: registro do censo.
        quadro: registro do quadro no censo.

    Returns:
        Dicionário do quadro (``registro`` guarda o quadro do censo, para o MediaPipe).
    """
    return {
        "id": id_,
        "grupo": grupo,
        "canal": video["canal"],
        "arquivo": video["arquivo"],
        "chave": video["chave"],
        "quadro": quadro["i"],
        "t": quadro["t"],
        "registro": quadro,
    }


def montar_conjunto(
    censo: list[dict], piloto: list[dict], conferencia: list[dict]
) -> tuple[list[dict], set[str]]:
    """Os 30 da conferência e os 60 novos, sorteados fora do piloto e da conferência.

    Args:
        censo: censo completo de mãos (uma linha por vídeo).
        piloto: linhas do piloto (36 quadros de ajuste).
        conferencia: manifesto dos 30 quadros da conferência.

    Returns:
        Os 90 itens (C antes de N) e o conjunto de chaves excluídas do sorteio.
    """
    por_chave = {v["chave"]: v for v in censo}
    itens = []
    for c in conferencia:
        video = por_chave[c["chave"]]
        itens.append(item(f"C{c['n']:02d}", "conferencia", video, quadro_do_censo(video, c["quadro"])))
    excluir = {r["chave"] for r in piloto} | {c["chave"] for c in conferencia}
    novos = sortear(censo, N_NOVOS, SEMENTE_SORTEIO, excluir)
    rng = random.Random(SEMENTE_QUADROS)
    for k, video in enumerate(novos, 1):
        quadro = escolher_quadro(video, rng)
        itens.append(item(f"N{k:02d}", "novo", video, quadro))
    return itens, excluir


def verificar_conjunto(itens: list[dict], piloto: list[dict], conferencia: list[dict]) -> None:
    """Confere o conjunto e imprime a checagem.

    Args:
        itens: os 90 quadros.
        piloto: linhas do piloto.
        conferencia: manifesto da conferência.

    Raises:
        SystemExit: se alguma regra do conjunto não vale.
    """
    conf = [i for i in itens if i["grupo"] == "conferencia"]
    novos = [i for i in itens if i["grupo"] == "novo"]
    chaves_piloto = {r["chave"] for r in piloto}
    chaves_conf = {c["chave"] for c in conferencia}
    chaves_novas = {i["chave"] for i in novos}
    if len(conf) != 30 or len(novos) != 60:
        raise SystemExit(f"contagem errada: {len(conf)} conferencia, {len(novos)} novos")
    if len({i["chave"] for i in itens}) != 90:
        raise SystemExit("chave repetida no conjunto de 90")
    if chaves_novas & chaves_piloto or chaves_novas & chaves_conf:
        raise SystemExit("algum dos 60 novos esta no piloto ou na conferencia")
    print("checagem: 30 conferencia + 60 novos = 90 quadros, chaves unicas")
    print(
        f"checagem: nenhuma das 60 chaves novas esta no piloto ({len(chaves_piloto)} chaves) "
        f"nem na conferencia ({len(chaves_conf)} chaves): True"
    )
    por_canal: dict[str, int] = {}
    for i in itens:
        por_canal[i["canal"]] = por_canal.get(i["canal"], 0) + 1
    print("por canal (90 quadros):")
    for canal in sorted(por_canal):
        print(f"  {canal}: {por_canal[canal]}")
    divergencias = 0
    for c, orig in zip(conf, conferencia):
        a = resumo_do_quadro(c["registro"])
        if (bool(a["esquerda"]), bool(a["direita"])) != (orig["afirma"]["esquerda"], orig["afirma"]["direita"]):
            divergencias += 1
    print(f"manifesto da conferencia vs censo (E/D do MediaPipe): {divergencias} divergencias de 30")


def mao_wb(kp: np.ndarray, sc: np.ndarray) -> dict:
    """Uma mão do Wholebody: caixa dos 21 pontos, média dos scores e os pontos.

    Args:
        kp: coordenadas ``(21, 2)``.
        sc: scores ``(21,)``.

    Returns:
        ``caixa`` (x0, y0, x1, y1), ``media`` (sem arredondar) e ``pts`` ``[x, y, score]``.
    """
    caixa = [
        round(float(kp[:, 0].min()), 1),
        round(float(kp[:, 1].min()), 1),
        round(float(kp[:, 0].max()), 1),
        round(float(kp[:, 1].max()), 1),
    ]
    pts = [[round(float(x), 1), round(float(y), 1), float(s)] for (x, y), s in zip(kp, sc)]
    return {"caixa": caixa, "media": float(sc.mean()), "pts": pts}


def afirma_wb(r: dict) -> dict:
    """Se alguma pessoa tem a mão com média acima de ``LIMIAR``.

    Args:
        r: saída de ``rodar_wb``.

    Returns:
        ``{"esquerda": bool, "direita": bool}``.
    """
    return {
        lado: any(p[lado]["media"] > LIMIAR for p in r["pessoas"])
        for lado in ("esquerda", "direita")
    }


def rodar_wb(wb: Wholebody, img_det: np.ndarray, img_pose: np.ndarray) -> dict:
    """Pessoas e mãos do Wholebody num quadro, com detector e pose chamados em separado.

    Chamar o detector e a pose em separado evita o fallback da rtmlib: sem pessoa
    detectada, ``Wholebody.__call__`` mandaria a pose para o quadro inteiro. Aqui, sem
    pessoa, a pose não roda.

    Args:
        wb: ``rtmlib.Wholebody`` com ``to_openpose=False``.
        img_det: imagem para o detector de pessoa (sempre BGR).
        img_pose: imagem para a pose (BGR ou RGB, conforme a variante).

    Returns:
        ``tempo_s`` (detector + pose), ``pessoas`` (caixa, mão esquerda e direita) e
        ``afirma`` no limiar ``LIMIAR``.
    """
    inicio = time.perf_counter()
    caixas = np.asarray(wb.det_model(img_det), dtype=float).reshape(-1, 4)
    if len(caixas):
        kp, sc = wb.pose_model(img_pose, bboxes=caixas)
    else:
        kp, sc = np.zeros((0, 133, 2)), np.zeros((0, 133))
    tempo = time.perf_counter() - inicio
    pessoas = []
    for c, k, s in zip(caixas, kp, sc):
        pessoas.append(
            {
                "caixa": [round(float(v), 1) for v in c],
                "esquerda": mao_wb(k[FAIXA_ESQ], s[FAIXA_ESQ]),
                "direita": mao_wb(k[FAIXA_DIR], s[FAIXA_DIR]),
            }
        )
    r = {"tempo_s": tempo, "sem_pessoa": len(caixas) == 0, "pessoas": pessoas}
    r["afirma"] = afirma_wb(r)
    return r


def mp_registro(quadro: dict) -> dict:
    """Afirmações e mãos do MediaPipe, a partir do quadro do censo (sem rodar nada).

    Args:
        quadro: registro do quadro no censo.

    Returns:
        ``afirma`` (E/D pelo ``resumo_do_quadro``, mãos fora da tablatura) e ``maos``.
    """
    a = resumo_do_quadro(quadro)
    maos = [
        {
            "lado": m["lado"],
            "na_tab": m["na_tab"],
            "score": m["score"],
            "caixa": m["caixa"],
            "pts": m["pts"],
        }
        for m in quadro["maos"]
    ]
    return {
        "afirma": {
            "esquerda": bool(a["esquerda"]),
            "direita": bool(a["direita"]),
            "n_maos_validas": a["n_maos"],
        },
        "maos": maos,
    }


def concordancia(itens: list[dict], a: str, b: str) -> dict:
    """Em quantos quadros dois detectores concordam em E e em D.

    Args:
        itens: quadros processados, com ``a`` e ``b`` como chaves de detector.
        a: nome do primeiro detector.
        b: nome do segundo detector.

    Returns:
        Por lado: ``concordam``, ``total`` e ``discordam`` (ids).
    """
    out = {}
    for lado in ("esquerda", "direita"):
        iguais = [i["id"] for i in itens if i[a]["afirma"][lado] == i[b]["afirma"][lado]]
        difere = [i["id"] for i in itens if i[a]["afirma"][lado] != i[b]["afirma"][lado]]
        out[lado] = {"concordam": len(iguais), "total": len(itens), "discordam": difere}
    return out


def desenhar_mp(img: np.ndarray, mp: dict) -> None:
    """Desenha as mãos do MediaPipe (amarelo; cinza se dentro da tablatura).

    Args:
        img: quadro BGR, alterado no lugar.
        mp: saída de ``mp_registro``.
    """
    esp = max(2, img.shape[1] // 400)
    for m in mp["maos"]:
        cor = CINZA if m["na_tab"] else AMARELO
        x0, y0, x1, y1 = (int(v) for v in m["caixa"])
        cv2.rectangle(img, (x0, y0), (x1, y1), cor, esp)
        cv2.putText(img, m["lado"], (x0, max(30, y0 - 8)), FONTE, esp * 0.8, cor, esp)
        for x, y in m["pts"]:
            cv2.circle(img, (int(x), int(y)), esp * 2, cor, -1)


def desenhar_wb(img: np.ndarray, r: dict, cor: tuple, deslocamento: int) -> None:
    """Desenha as mãos do Wholebody com média acima de ``LIMIAR_DESENHO``.

    Letra maiúscula (E/D) quando a média passa de ``LIMIAR``; minúscula e linha fina
    quando fica entre 0,3 e 0,5. O ``deslocamento`` separa as letras das duas variantes.

    Args:
        img: quadro BGR, alterado no lugar.
        r: saída de ``rodar_wb``.
        cor: cor da variante em BGR.
        deslocamento: deslocamento horizontal do rótulo, em pixels.
    """
    esp = max(2, img.shape[1] // 400)
    for p in r["pessoas"]:
        for lado, letra in (("esquerda", "E"), ("direita", "D")):
            m = p[lado]
            if m["media"] <= LIMIAR_DESENHO:
                continue
            forte = m["media"] > LIMIAR
            x0, y0, x1, y1 = (int(v) for v in m["caixa"])
            cv2.rectangle(img, (x0, y0), (x1, y1), cor, esp if forte else max(1, esp // 2))
            rotulo = letra if forte else letra.lower()
            cv2.putText(img, rotulo, (x0 + deslocamento, max(30, y0 - 8)), FONTE, esp * 0.8, cor, esp)
            for x, y, s in m["pts"]:
                if s >= SCORE_PONTO:
                    cv2.circle(img, (int(x), int(y)), esp * 2, cor, -1)


def texto(img: np.ndarray, msg: str, x: int, y: int, escala: float) -> None:
    """Texto branco com contorno preto, para ler em qualquer fundo.

    Args:
        img: imagem (alterada no lugar).
        msg: texto em ASCII.
        x: coluna da linha de base.
        y: linha de base.
        escala: escala da fonte do OpenCV.
    """
    cv2.putText(img, msg, (x, y), FONTE, escala, PRETO, 3)
    cv2.putText(img, msg, (x, y), FONTE, escala, BRANCO, 1)


def celula(img: np.ndarray, linhas: list[str], escala_rodape: float) -> np.ndarray:
    """Uma célula 640x480: o quadro reduzido com a proporção e o rodapé.

    Args:
        img: quadro (já desenhado, se for o caso), em BGR.
        linhas: linhas do rodapé (ASCII).
        escala_rodape: escala da fonte do rodapé.

    Returns:
        Imagem 480x640 em BGR, fundo preto.
    """
    area = ALTURA_CELULA - ALTURA_RODAPE
    h, w = img.shape[:2]
    escala = min(LARGURA_CELULA / w, area / h)
    nw, nh = max(1, round(w * escala)), max(1, round(h * escala))
    cel = np.zeros((ALTURA_CELULA, LARGURA_CELULA, 3), np.uint8)
    x, y = (LARGURA_CELULA - nw) // 2, (area - nh) // 2
    cel[y : y + nh, x : x + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    for k, msg in enumerate(linhas):
        texto(cel, msg, 8, area + 26 + k * 26, escala_rodape)
    return cel


def folhas(celulas: list[np.ndarray], prefixo: str) -> list[Path]:
    """Junta as células em folhas de 2 colunas por 5 linhas (10 por folha).

    Args:
        celulas: células na ordem da folha.
        prefixo: ``rotular`` ou ``deteccoes``; grava ``<prefixo>_<k>.jpg`` em m1/.

    Returns:
        Caminhos das folhas gravadas.

    Raises:
        SystemExit: se o OpenCV não gravar uma folha.
    """
    vazia = np.zeros((ALTURA_CELULA, LARGURA_CELULA, 3), np.uint8)
    arquivos = []
    for k0 in range(0, len(celulas), POR_FOLHA):
        bloco = celulas[k0 : k0 + POR_FOLHA]
        bloco = bloco + [vazia] * (POR_FOLHA - len(bloco))
        linhas = [np.hstack(bloco[i : i + COLUNAS]) for i in range(0, POR_FOLHA, COLUNAS)]
        arq = M1 / f"{prefixo}_{k0 // POR_FOLHA + 1}.jpg"
        if not cv2.imwrite(str(arq), np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG]):
            raise SystemExit(f"cv2 nao gravou {arq}")
        arquivos.append(arq)
    return arquivos


def celula_det(img: np.ndarray, it: dict) -> np.ndarray:
    """Célula com as detecções dos três detectores e o rodapé de E/D.

    Args:
        img: quadro original em BGR (não é alterado).
        it: quadro processado.

    Returns:
        Célula 640x480.
    """
    out = img.copy()
    desenhar_mp(out, it["mediapipe"])
    desenhar_wb(out, it["wb_bgr"], VERDE, 0)
    desenhar_wb(out, it["wb_rgb"], MAGENTA, 34)
    a, b, c = it["mediapipe"]["afirma"], it["wb_bgr"]["afirma"], it["wb_rgb"]["afirma"]
    linha = (
        f"{it['id']} | MP E={int(a['esquerda'])} D={int(a['direita'])} | "
        f"WB-BGR E={int(b['esquerda'])} D={int(b['direita'])} | "
        f"WB-RGB E={int(c['esquerda'])} D={int(c['direita'])}"
    )
    legenda = "amarelo=MP  verde=WB-BGR  magenta=WB-RGB  maiusc.=media>0.5  minusc.=0.3-0.5"
    return celula(out, [legenda, linha], 0.5)


def tabela_concordancia(pares: dict[str, dict]) -> None:
    """Imprime a tabela de concordância entre detectores (não é acerto).

    Args:
        pares: nome do par -> saída de ``concordancia``.
    """
    print()
    print("| par | E concordam | D concordam | discordam em E | discordam em D |")
    print("| --- | --- | --- | --- | --- |")
    for nome, r in pares.items():
        e, d = r["esquerda"], r["direita"]
        print(
            f"| {nome} | {e['concordam']}/{e['total']} | {d['concordam']}/{d['total']} | "
            f"{', '.join(e['discordam']) or '-'} | {', '.join(d['discordam']) or '-'} |"
        )


def main() -> None:
    """Monta o conjunto, roda os detectores, grava o JSON e as folhas."""
    censo = ler_jsonl(CENSO)
    piloto = ler_jsonl(PILOTO)
    conferencia = json.loads(CONFERENCIA.read_text(encoding="utf-8"))
    itens, _excluir = montar_conjunto(censo, piloto, conferencia)
    verificar_conjunto(itens, piloto, conferencia)

    conjunto = [
        {
            "id": i["id"],
            "canal": i["canal"],
            "arquivo": i["arquivo"],
            "chave": i["chave"],
            "quadro": i["quadro"],
            "grupo": i["grupo"],
        }
        for i in itens
    ]
    (M1 / "validacao_conjunto.json").write_text(
        json.dumps(conjunto, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"conjunto gravado: {M1 / 'validacao_conjunto.json'}")

    inicio = time.perf_counter()
    wb = Wholebody(backend="onnxruntime", device="cpu", to_openpose=False)
    print(f"Wholebody carregado em {time.perf_counter() - inicio:.1f} s", flush=True)

    # Aquecimento (não medido, não gravado): a primeira chamada de sessão é mais lenta.
    img0 = ler_imagem(itens[0]["chave"], itens[0]["quadro"])
    rodar_wb(wb, img0, img0)
    rodar_wb(wb, img0, cv2.cvtColor(img0, cv2.COLOR_BGR2RGB))

    for k, it in enumerate(itens, 1):
        img = ler_imagem(it["chave"], it["quadro"])
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        it["mediapipe"] = mp_registro(it["registro"])
        it["wb_bgr"] = rodar_wb(wb, img, img)
        it["wb_rgb"] = rodar_wb(wb, img, img_rgb)
        print(
            f"{k:2d}/{len(itens)} {it['id']} "
            f"MP E={int(it['mediapipe']['afirma']['esquerda'])} D={int(it['mediapipe']['afirma']['direita'])} "
            f"BGR E={int(it['wb_bgr']['afirma']['esquerda'])} D={int(it['wb_bgr']['afirma']['direita'])} "
            f"RGB E={int(it['wb_rgb']['afirma']['esquerda'])} D={int(it['wb_rgb']['afirma']['direita'])} "
            f"t_bgr={it['wb_bgr']['tempo_s']:.2f}s t_rgb={it['wb_rgb']['tempo_s']:.2f}s",
            flush=True,
        )

    pares = {
        "MP x WB-BGR": concordancia(itens, "mediapipe", "wb_bgr"),
        "MP x WB-RGB": concordancia(itens, "mediapipe", "wb_rgb"),
        "WB-BGR x WB-RGB": concordancia(itens, "wb_bgr", "wb_rgb"),
    }
    tabela_concordancia(pares)
    tempo_medio = {
        "wb_bgr": float(np.mean([i["wb_bgr"]["tempo_s"] for i in itens])),
        "wb_rgb": float(np.mean([i["wb_rgb"]["tempo_s"] for i in itens])),
    }
    print(
        f"tempo medio por quadro (CPU, {len(itens)} quadros): "
        f"WB-BGR {tempo_medio['wb_bgr']:.2f} s, WB-RGB {tempo_medio['wb_rgb']:.2f} s, "
        "MediaPipe 0 s (vem do censo)"
    )

    quadros = []
    for it in itens:
        quadros.append(
            {
                "id": it["id"],
                "grupo": it["grupo"],
                "canal": it["canal"],
                "arquivo": it["arquivo"],
                "chave": it["chave"],
                "quadro": it["quadro"],
                "t": it["t"],
                "mediapipe": it["mediapipe"],
                "wb_bgr": it["wb_bgr"],
                "wb_rgb": it["wb_rgb"],
            }
        )
    saida = {
        "modelos": {
            "mediapipe": "censo M0 (tab.maos_censo), lido de censo_maos.jsonl; nada rodado aqui",
            "wholebody": "YOLOX-m humanart + RTMW-DW-X-L cocktail14, modo balanced, to_openpose=False",
        },
        "limiar_wb": LIMIAR,
        "concordancia": pares,
        "tempo_medio_s": tempo_medio,
        "quadros": quadros,
    }
    (M1 / "validacao_deteccoes.json").write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"deteccoes gravadas: {M1 / 'validacao_deteccoes.json'}")

    # Folhas limpas para rotular: só o quadro e o id, sem nenhuma detecção.
    limpas = []
    for it in itens:
        img = ler_imagem(it["chave"], it["quadro"])
        limpas.append(celula(img, [it["id"]], 0.9))
    for arq in folhas(limpas, "rotular"):
        print(f"folha limpa: {arq}")

    # Folhas com as detecções desenhadas.
    com_det = []
    for it in itens:
        img = ler_imagem(it["chave"], it["quadro"])
        com_det.append(celula_det(img, it))
    for arq in folhas(com_det, "deteccoes"):
        print(f"folha de deteccao: {arq}")


if __name__ == "__main__":
    main()
