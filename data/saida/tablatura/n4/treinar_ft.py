"""n4 passo 3: ajuste fino do DetectorTab (partida v3_s1) com telas reais + sintético.

Uma dobra por execução. Os vídeos da dobra ficam FORA do treino. Cada lote: 16
telas reais (aumento: brilho/contraste, JPEG 40-95, desfoque leve 50%, escala
horizontal 0,9-1,1 sobre o sistema normalizado, recorte de 512 px) e 16 sistemas
sintéticos de tab.detector_tab._amostra_treino. Técnica: máscara zero nas reais.
Perda: centro (focal), classe (CE, só onde há supervisão) e técnica (BCE, só sintético).
AdamW lr 3e-4, cosseno, fixar_semente(1).

--ignorar-x (2026-10-16): dentro das regiões de nota abafada (X) que o dono marcou no
ouro, o centro não conta como fundo (sem o flag, o ajuste fino ensinava a apagar o X).

--ataque (2026-10-17, rodada 0202, R4a): nas telas reais conferidas no R2, as 7 técnicas que
tiram o ataque passam a ser supervisionadas em cada nota casada com o gabarito
(``tab.ataque_r4``). A máscara de técnica vira por classe (6, L, 10).

--arco (2026-10-19, rodada 0206, A2): a cabeça de arco (``h_arco``) aprende no sintético, com
o alvo de ``info["arcos"]``; nas reais ela fica sem supervisão (piloto). Sem o flag, a perda é
a de antes.

--t82 (2026-10-19, rodada 0207): as 34 telas da T8.2 (``cache_t82``, de ``extrair_t82.py``)
entram no treino de todas as dobras, com a técnica do gabarito do dono. A T8.3 fica de teste.

--recorte-alto (2026-10-21, rodada 0211, fase 2): lê as cópias ``<cache>_alto`` de
``cache_alto.py`` (recorte até 2,5 passos acima da corda 1 e abaixo da 6), em vez do cache
do painel, que apagava os arcos acima do sistema (0210).

--t83-toda e --t84 (2026-10-22, rodada 0214): as 33 telas da T8.3 (as duas metades) e as
telas da T8.4 (``cache_t84``, de ``extrair_t84.py``) entram no treino de todas as dobras, com
a técnica do gabarito do dono. As duas já estão gastas; a prova lacrada é a T8.5.

--t85 (2026-10-23, rodada 0215): as 28 telas da T8.5, já gasta (``cache_t85``, de
``extrair_t85.py``), entram no treino de todas as dobras. A prova lacrada é a T8.6.

Uso (container, cwd /app):
    python /app/data/saida/n4/treinar_ft.py --dobra 1 --passos 3000
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, "/app")

from tab import ataque_r4  # noqa: E402
from tab.gpu import trava_gpu  # noqa: E402
from tab import detector_tab as D  # noqa: E402
from tab.sintetico import fixar_semente  # noqa: E402

CACHE = Path("/app/data/saida/n4/cache")
#: Telas da T8.2 (extrair_t82.py), só com --t82 (rodada 0207). Entram em todas as dobras.
CACHE_T82 = Path("/app/data/saida/n4/cache_t82")
#: Gabarito de ataque das fontes do cache que não são ouro.
GABARITOS_EXTRA = {
    "t82": ("conferir_novos", "t82"),
    "t83": ("conferir_t83", "t83"),
    "t84": ("conferir_t84", "t84"),
    "t85": ("conferir_t85", "t85"),
}
#: Telas da T8.3 (extrair_t83.py), só com --t83-metade (rodada 0209): entra só essa metade.
CACHE_T83 = Path("/app/data/saida/n4/cache_t83")
#: Telas da T8.4 (extrair_t84.py, só recorte alto), só com --t84 (rodada 0214).
CACHE_T84 = Path("/app/data/saida/n4/cache_t84")
#: Telas da T8.5 (extrair_t85.py, só recorte alto), só com --t85 (rodada 0215).
CACHE_T85 = Path("/app/data/saida/n4/cache_t85")
ARTEFATOS = Path("/app/artefatos")
PARTIDA = ARTEFATOS / "detector_tab_v3_s1" / "modelo.pt"
OURO_VIDEO = Path("/app/data/gold/ouro_video")
MARGEM_X_BINS = 1  # folga, em bins de saída, em volta da região de X
#: X do dono nas telas conferidas (rodada 0218, ``correcoes/x_dono.py``), só com --x-dono.
X_DONO = Path("/app/data/saida/tablatura/correcoes/x_dono.json")
DOBRAS = {
    0: (),  # final: todos os gabaritos no treino
    1: ("retrato_brasileiro_v2", "la_vie_en_rose_edith_piaf_tab"),
    2: (
        "greensleeves_guia_de_estudio_partitura_tab_pdf",
        "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
    ),
    3: (
        "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
        "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
    ),
    4: (
        "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
        "tabroom_335_larry_carlton_fingerstyle_guitar",
    ),
}
METADE = 16  # reais por lote (e sintéticos por lote): 50/50 de 32
LARGURA = D.LARGURA_TREINO  # 512
N_BIN = LARGURA // D.STRIDE  # 128


def log(msg: str) -> None:
    """Imprime com descarga imediata."""
    print(msg, flush=True)


def regioes_x(slug: str, tela: int, x0: float) -> list[tuple[int, int, float, float]]:
    """Regiões de X (nota abafada) da tela no ouro, em x do roi.

    Args:
        slug: vídeo.
        tela: id da tela no ouro.
        x0: deslocamento do roi no quadro.

    Returns:
        Lista de (corda_min, corda_max, x_ini_roi, x_fim_roi).
    """
    ouro = json.loads((OURO_VIDEO / f"{slug}.json").read_text(encoding="utf-8"))
    saida = []
    for t in ouro["telas"]:
        if int(t["id"]) != int(tela):
            continue
        for r in t.get("regioes") or []:
            if r.get("tecnica") == ["x"]:
                c = sorted(int(v) for v in r["cordas"])
                xs = sorted(float(v) - x0 for v in r["x_quadro"])
                saida.append((c[0], c[-1], xs[0], xs[-1]))
    return saida


def com_x_dono(meta: dict, xs: list[dict]) -> int:
    """Põe as notas X do dono numa tela do cache (rodada 0218).

    A nota do cache na mesma corda a até 0,5 passo vira ``x`` (o dono trocou o número por
    X); sem nota perto, a nota X entra nova. As duas ficam sem alvo de ataque: o X não
    ganha rótulo de ataque inferido.

    Args:
        meta: a tela do cache, com ``notas``, ``alvos_tec``, ``x0`` e ``passo`` (alterada).
        xs: as notas X do dono da tela (``corda``, ``x_centro_quadro``).

    Returns:
        Quantas notas X entraram ou trocaram de rótulo.
    """
    passo, x0 = float(meta["passo"]), float(meta["x0"])
    for x in xs:
        x_roi = float(x["x_centro_quadro"]) - x0
        perto = [
            i
            for i, n in enumerate(meta["notas"])
            if int(n["corda"]) == int(x["corda"])
            and abs(float(n["x_roi"]) - x_roi) <= 0.5 * passo
        ]
        if perto:
            i = min(perto, key=lambda i: abs(float(meta["notas"][i]["x_roi"]) - x_roi))
            meta["notas"][i]["casa"] = "x"
            meta["alvos_tec"][i] = (False, None)
        else:
            meta["notas"].append({"corda": int(x["corda"]), "casa": "x", "x_roi": x_roi})
            meta["alvos_tec"].append((False, None))
    return len(xs)


def casa_do_cache(casa: int | str) -> str:
    """Casa de uma nota do cache como rótulo do detector ("7", "x").

    Args:
        casa: a casa como está no cache (número, ou "x" depois do ``com_x_dono``).

    Returns:
        O rótulo em texto.
    """
    return "x" if str(casa).lower() in ("x", "xs") else str(int(casa))


def carregar_telas(
    excluir: tuple[str, ...],
    ignorar_x: bool = False,
    ataque: bool = False,
    t82: bool = False,
    t83_metade: str | None = None,
    alto: bool = False,
    t83_toda: bool = False,
    t84: bool = False,
    t85: bool = False,
    x_dono: bool = False,
) -> list[dict]:
    """Lê o cache, tirando os vídeos da dobra.

    Args:
        excluir: slugs que não entram no treino.
        ignorar_x: anexa as regiões de X do ouro em "regioes_x".
        ataque: anexa o alvo de técnica de cada nota em "alvos_tec" (R4a).
        t82: soma as telas de ``CACHE_T82`` (rodada 0207).
        t83_metade: "a" ou "b" soma essa metade de ``CACHE_T83`` (rodada 0209).
        alto: lê as cópias ``<cache>_alto`` com o recorte alto (rodada 0211).
        t83_toda: soma as duas metades de ``CACHE_T83`` (rodada 0214).
        t84: soma as telas de ``CACHE_T84`` (rodada 0214; existe só com o recorte alto).
        t85: soma as telas de ``CACHE_T85`` (rodada 0215; existe só com o recorte alto).
        x_dono: põe as notas X do dono de ``X_DONO`` (rodada 0218).

    Returns:
        Lista de dicts do cache, com a imagem BGR em "img".
    """
    telas = []
    xs_dono = json.loads(X_DONO.read_text(encoding="utf-8"))["treino"] if x_dono else {}
    def pasta(p: Path) -> Path:
        return p.with_name(p.name + "_alto") if alto else p

    arquivos = sorted(pasta(CACHE).glob("*.json"))
    if t82:
        arquivos += sorted(pasta(CACHE_T82).glob("*.json"))
    if t83_metade or t83_toda:
        arquivos += sorted(pasta(CACHE_T83).glob("*.json"))
    if t84:
        arquivos += sorted(pasta(CACHE_T84).glob("*.json"))
    if t85:
        arquivos += sorted(pasta(CACHE_T85).glob("*.json"))
    for caminho in arquivos:
        meta = json.loads(caminho.read_text(encoding="utf-8"))
        if meta["slug"] in excluir:
            continue
        if not t83_toda and meta.get("metade", t83_metade) != t83_metade:
            continue
        if alto and meta.get("recorte") != "alto":
            raise SystemExit(f"tela sem recorte alto: {caminho}")
        meta["img"] = cv2.imread(str(caminho.parent / meta["png"]))
        meta["regioes_x"] = (
            regioes_x(meta["slug"], meta["tela"], meta["x0"])
            if ignorar_x and meta["slug"] not in GABARITOS_EXTRA
            else []
        )
        meta["alvos_tec"] = (
            alvos_tec(meta) if ataque else [(False, None)] * len(meta["notas"])
        )
        meta["x_dono"] = com_x_dono(
            meta, xs_dono.get(meta["slug"], {}).get(str(meta["tela"]), [])
        )
        telas.append(meta)
    return telas


_GABARITOS: dict[str, dict[int, list[dict]]] = {}


def alvos_tec(meta: dict) -> list[tuple[bool, str | None]]:
    """Alvo de técnica das notas de uma tela do cache, pelo gabarito do R2."""
    sub, fonte = ataque_r4.GABARITOS.get(meta["slug"]) or GABARITOS_EXTRA[meta["slug"]]
    if meta["slug"] not in _GABARITOS:
        arquivo = ataque_r4.caminhos.TAB_ROTULO / "r2" / sub / f"ataque_{fonte}.json"
        _GABARITOS[meta["slug"]] = ataque_r4.gabarito_por_tela(arquivo)
    gab = _GABARITOS[meta["slug"]].get(int(meta["tela"]), [])
    return ataque_r4.alvos_da_tela(meta["notas"], float(meta["x0"]), float(meta["passo"]), gab)


def alvos_reais(
    notas_norm: list[tuple[int, str, float]], comprimento: int
) -> tuple[np.ndarray, np.ndarray]:
    """Centro e classe de uma tela real, na grade de saída (sem técnica).

    Args:
        notas_norm: lista de (corda 1-6, casa como texto, x em px normalizados).
        comprimento: número de bins de saída.

    Returns:
        Tupla (centro (6, L) float32, classe (6, L) int64 com -1 sem supervisão).
    """
    centro = np.zeros((D.N_CORDAS, comprimento), dtype=np.float32)
    classe = np.full((D.N_CORDAS, comprimento), -1, dtype=np.int64)
    bins = np.arange(comprimento)
    for corda, casa, x in notas_norm:
        k = corda - 1
        u = (x - D.DESLOC) / D.STRIDE
        pico = int(np.clip(round(u), 0, comprimento - 1))
        gauss = np.exp(-((bins - pico) ** 2) / (2 * (D.SIGMA_PASSO * D.PASSO_NORM / D.STRIDE) ** 2))
        centro[k] = np.maximum(centro[k], gauss.astype(np.float32))
        sup = np.flatnonzero(np.abs(bins - u) <= D.RAIO_CLASSE_BINS)
        if casa in D.ROTULO_IDX:
            classe[k, sup] = D.ROTULO_IDX[casa]
    return centro, classe


def amostra_real(tela: dict, rng: random.Random) -> tuple[np.ndarray, ...]:
    """Um recorte aumentado de tela real, com alvos (técnica mascarada).

    Args:
        tela: entrada do cache (com "img", "linhas_y", "passo", "notas").
        rng: gerador do aumento e do recorte.

    Returns:
        Tupla (recorte (160, 512) float32, centro (6, 128), classe (6, 128) int64,
        técnica (6, 128, 10) zeros, máscara de técnica (6, 128) zeros, ignorar
        (6, 128) com 1 onde o centro não conta como fundo).
    """
    img = tela["img"].astype(np.float32)
    img = np.clip(img * rng.uniform(0.8, 1.2) + rng.uniform(-20, 20), 0, 255)
    img = img.astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(40, 95)])
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if rng.random() < 0.5:
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.5, 0.8))
    arr, escala, _ = D.normalizar_sistema(img, tela["linhas_y"], tela["passo"])
    s = rng.uniform(0.9, 1.1)
    w2 = max(4, int(round(arr.shape[1] * s)))
    arr = cv2.resize(arr, (w2, arr.shape[0]), interpolation=cv2.INTER_LINEAR)
    w3 = math.ceil(w2 / D.STRIDE) * D.STRIDE
    if w3 > w2:
        arr = np.pad(arr, ((0, 0), (0, w3 - w2)), mode="edge")
    notas = [
        (int(n["corda"]), casa_do_cache(n["casa"]), float(n["x_roi"]) * escala * s)
        for n in tela["notas"]
    ]
    centro_c, classe_c = alvos_reais(notas, w3 // D.STRIDE)
    b0 = rng.randint(0, max(0, w3 - LARGURA) // D.STRIDE)
    x0 = b0 * D.STRIDE
    recorte = np.full((D.ALTURA_NORM, LARGURA), float(np.median(arr)), dtype=np.float32)
    tam = min(LARGURA, w3 - x0)
    recorte[:, :tam] = arr[:, x0 : x0 + tam]
    centro = np.zeros((D.N_CORDAS, N_BIN), dtype=np.float32)
    classe = np.full((D.N_CORDAS, N_BIN), -1, dtype=np.int64)
    n = min(N_BIN, centro_c.shape[1] - b0)
    if n > 0:
        centro[:, :n] = centro_c[:, b0 : b0 + n]
        classe[:, :n] = classe_c[:, b0 : b0 + n]
    tecnica = np.zeros((D.N_CORDAS, N_BIN, len(D.TECNICAS_MODELO)), dtype=np.float32)
    mascara = np.zeros((D.N_CORDAS, N_BIN, len(D.TECNICAS_MODELO)), dtype=np.float32)
    sup_idx = [D.TECNICA_IDX[t] for t in ataque_r4.TECNICAS_SUPERVISIONADAS]
    for (corda, _, x), (sup, tec) in zip(notas, tela["alvos_tec"], strict=True):
        if not sup:
            continue
        u = (x - D.DESLOC) / D.STRIDE - b0
        js = [j for j in range(N_BIN) if abs(j - u) <= D.RAIO_CLASSE_BINS]
        for j in js:
            mascara[corda - 1, j, sup_idx] = 1.0
            if tec is not None:
                tecnica[corda - 1, j, D.TECNICA_IDX[tec]] = 1.0
    ignorar = np.zeros((D.N_CORDAS, N_BIN), dtype=np.float32)
    for c0, c1, xa, xb in tela.get("regioes_x", []):
        ua = (xa * escala * s - D.DESLOC) / D.STRIDE - b0 - MARGEM_X_BINS
        ub = (xb * escala * s - D.DESLOC) / D.STRIDE - b0 + MARGEM_X_BINS
        ja, jb = max(0, math.floor(ua)), min(N_BIN - 1, math.ceil(ub))
        if ja <= jb:
            ignorar[c0 - 1 : c1, ja : jb + 1] = 1.0
    arco = np.zeros((D.N_CORDAS, N_BIN), dtype=np.float32)
    return recorte, centro, classe, tecnica, mascara, ignorar, arco, np.zeros_like(arco)


def contar_alvos(telas: list[dict]) -> dict[str, int]:
    """Contagem das notas reais supervisionadas: atacadas e por técnica."""
    c = collections.Counter(
        tec or "atacada" for t in telas for sup, tec in t["alvos_tec"] if sup
    )
    return dict(sorted(c.items()))


def perda_centro_ignorando(
    logits: torch.Tensor, alvo: torch.Tensor, ignorar: torch.Tensor
) -> torch.Tensor:
    """D.perda_centro sem a parcela de fundo onde ``ignorar`` é 1.

    Com ``ignorar`` todo zero dá exatamente D.perda_centro.

    Args:
        logits: logits do centro (B, 6, L).
        alvo: gaussiano com pico 1 em cada nota.
        ignorar: 1 onde o fundo não conta (região de X do ouro).

    Returns:
        Escalar, normalizado pelo número de picos (mínimo 1).
    """
    p = torch.sigmoid(logits).clamp(1e-6, 1 - 1e-6)
    pos = alvo.eq(1.0).float()
    neg = (alvo < 1.0).float() * (1.0 - ignorar)
    perda_pos = ((1 - p) ** 2) * torch.log(p) * pos
    perda_neg = ((1 - alvo) ** 4) * (p**2) * torch.log(1 - p) * neg
    return -(perda_pos.sum() + perda_neg.sum()) / pos.sum().clamp(min=1.0)


def perda_ft(saida: dict, alvos: dict) -> tuple[torch.Tensor, dict[str, float]]:
    """Perda de D.perda_total, com máscara de técnica por amostra.

    Args:
        saida: saída de DetectorTab.forward.
        alvos: centro, classe, ignorar (B, 6, L); tecnica e tecmask (B, 6, L, 10).

    Returns:
        Tupla (perda com grafo, parcelas em float).
    """
    l_centro = perda_centro_ignorando(saida["centro"], alvos["centro"], alvos["ignorar"])
    m = alvos["classe"] >= 0
    if bool(m.any()):
        l_classe = F.cross_entropy(saida["classe"][m], alvos["classe"][m])
    else:
        l_classe = saida["centro"].sum() * 0.0
    mt = m[..., None] & alvos["tecmask"].bool()
    if bool(mt.any()):
        l_tec = F.binary_cross_entropy_with_logits(
            saida["tecnica"][mt], alvos["tecnica"][mt]
        )
    else:
        l_tec = saida["centro"].sum() * 0.0
    total = l_centro + l_classe + l_tec
    parcelas = {
        "centro": float(l_centro.detach()),
        "classe": float(l_classe.detach()),
        "tecnica": float(l_tec.detach()),
    }
    ma = alvos["arcomask"].bool()
    if bool(ma.any()):  # rodada 0206: cabeça de arco, só com --arco
        l_arco = F.binary_cross_entropy_with_logits(saida["arco"][ma], alvos["arco"][ma])
        total = total + l_arco
        parcelas["arco"] = float(l_arco.detach())
    return total, parcelas


def main() -> int:
    """Treina a dobra pedida e grava o artefato."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--dobra", type=int, required=True, choices=sorted(DOBRAS))
    ap.add_argument("--passos", type=int, default=3000)
    ap.add_argument("--semente", type=int, default=1)
    ap.add_argument("--nome", default="", help="sufixo da pasta, ex. _s2")
    ap.add_argument("--ignorar-x", action="store_true", help="X do ouro não é fundo")
    ap.add_argument("--ataque", action="store_true", help="técnica real do R2 (R4a)")
    ap.add_argument("--arco", action="store_true", help="cabeça de arco no sintético (0206)")
    ap.add_argument("--t82", action="store_true", help="telas da T8.2 no treino (0207)")
    ap.add_argument("--t83-metade", choices=("a", "b"), help="metade da T8.3 no treino (0209)")
    ap.add_argument("--recorte-alto", action="store_true", help="cache *_alto (0211)")
    ap.add_argument("--t83-toda", action="store_true", help="T8.3 inteira no treino (0214)")
    ap.add_argument("--t84", action="store_true", help="telas da T8.4 no treino (0214)")
    ap.add_argument("--t85", action="store_true", help="telas da T8.5 no treino (0215)")
    ap.add_argument("--x-dono", action="store_true", help="X do dono no treino (0218)")
    args = ap.parse_args()
    comando = "python /app/data/saida/n4/treinar_ft.py " + " ".join(sys.argv[1:])
    fora = DOBRAS[args.dobra]
    if (args.t84 or args.t85) and not args.recorte_alto:
        raise SystemExit("--t84 e --t85 só existem com --recorte-alto")
    telas = carregar_telas(
        fora, args.ignorar_x, args.ataque, args.t82, args.t83_metade, args.recorte_alto,
        args.t83_toda, args.t84, args.t85, args.x_dono,
    )
    if not telas:
        raise SystemExit("sem telas de treino")
    if args.dobra == 0:
        pasta = ARTEFATOS / f"detector_tab_final{args.nome}"
    else:
        pasta = ARTEFATOS / f"detector_tab_v3ft_d{args.dobra}{args.nome}"
    pasta.mkdir(parents=True, exist_ok=True)
    log(f"dobra {args.dobra}: fora={fora} | telas reais de treino={len(telas)}")
    log(f"regiões de X ignoradas: {sum(len(t['regioes_x']) for t in telas)}")
    log(f"notas X do dono: {sum(t['x_dono'] for t in telas)}")
    sup = contar_alvos(telas)
    log(f"notas reais com técnica supervisionada: {sup}")

    base = (args.semente + 1) * 10**9
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    contexto = mp.get_context("fork")
    rng = random.Random(args.semente * 1000 + args.dobra)
    with contexto.Pool(D.TRABALHADORES, initializer=D._iniciar_trabalhador) as pool:
        fixar_semente(args.semente)
        modelo = D.DetectorTab()
        r = modelo.load_state_dict(torch.load(PARTIDA, map_location="cpu"), strict=False)
        assert all(k.startswith("h_arco.") for k in r.missing_keys) and not r.unexpected_keys
        modelo = modelo.to(dispositivo)
        modelo.train()
        opt = torch.optim.AdamW(modelo.parameters(), lr=3e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.passos)
        pendentes: collections.deque = collections.deque()

        def submeter(indice: int) -> None:
            sementes = [base + indice * METADE + j for j in range(METADE)]
            pendentes.append(pool.map_async(D._amostra_treino, sementes, chunksize=2))

        for indice in range(D.PREFETCH):
            submeter(indice)
        inicio = time.time()
        soma: collections.Counter = collections.Counter()
        for passo in range(args.passos):
            sint = pendentes.popleft().get()
            submeter(passo + D.PREFETCH)
            reais = [amostra_real(telas[rng.randrange(len(telas))], rng) for _ in range(METADE)]
            amostras = [
                (a[0], a[1], a[2], a[3], np.ones_like(a[3]) * (a[2] >= 0)[..., None], np.zeros_like(a[1]),
                 a[4], np.full_like(a[4], 1.0 if args.arco else 0.0))
                for a in sint
            ] + reais
            # técnica do sintético: máscara = onde há supervisão de classe
            imgs = torch.from_numpy(np.stack([a[0] for a in amostras])[:, None])
            alvos = {
                "centro": torch.from_numpy(np.stack([a[1] for a in amostras])),
                "classe": torch.from_numpy(np.stack([a[2] for a in amostras])),
                "tecnica": torch.from_numpy(np.stack([a[3] for a in amostras])),
                "tecmask": torch.from_numpy(np.stack([a[4] for a in amostras]).astype(np.float32)),
                "ignorar": torch.from_numpy(np.stack([a[5] for a in amostras]).astype(np.float32)),
                "arco": torch.from_numpy(np.stack([a[6] for a in amostras])),
                "arcomask": torch.from_numpy(np.stack([a[7] for a in amostras])),
            }
            alvos = {k: v.to(dispositivo) for k, v in alvos.items()}
            saida = modelo(imgs.to(dispositivo))
            perda, parcelas = perda_ft(saida, alvos)
            opt.zero_grad(set_to_none=True)
            perda.backward()
            opt.step()
            sched.step()
            soma["perda"] += float(perda.detach())
            for nome, valor in parcelas.items():
                soma[nome] += valor
            if (passo + 1) % 250 == 0:
                medio = {k: v / 250 for k, v in soma.items()}
                soma.clear()
                log(
                    f"passo {passo + 1}/{args.passos} | "
                    + " ".join(f"{k} {v:.4f}" for k, v in medio.items())
                    + f" | lr {sched.get_last_lr()[0]:.2e} | {time.time() - inicio:.0f} s"
                )
        tempo = time.time() - inicio
    caminho = pasta / "modelo.pt"
    torch.save(modelo.state_dict(), caminho)
    config = {
        "comando": comando,
        "dobra": args.dobra,
        "videos_fora_do_treino": list(fora),
        "videos_de_treino": sorted({t["slug"] for t in telas}),
        "telas_reais_treino": len(telas),
        "partida": "artefatos/detector_tab_v3_s1/modelo.pt",
        "passos": args.passos,
        "lote": 2 * METADE,
        "lote_real": METADE,
        "lote_sintetico": METADE,
        "lr": 3e-4,
        "semente": args.semente,
        "ignorar_x": args.ignorar_x,
        "ataque": args.ataque,
        "arco": args.arco,
        "t82": args.t82,
        "t83_metade": args.t83_metade,
        "recorte_alto": args.recorte_alto,
        "t83_toda": args.t83_toda,
        "t84": args.t84,
        "t85": args.t85,
        "x_dono": args.x_dono,
        "notas_supervisionadas": sup,
        "tempo_s": round(tempo, 1),
    }
    (pasta / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(f"gravado {caminho} em {tempo:.0f} s")
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "treino"):  # protocolo da GPU compartilhada
        codigo = main()
    sys.exit(codigo)
