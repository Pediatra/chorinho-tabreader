"""T8.5: telas para a validação do rótulo de ataque (rodada 0211), semente 3.

Cópia do gerar.py da T8.4. Só saída em data/saida/tablatura/t85/. É um quarto lote, com vídeos
diferentes dos do ouro, da T8.2, da T8.3 e da T8.4: nenhum deles foi visto por treino ou escolha.

Sorteio: random.Random(3), canais em ordem alfabética. Por canal, 2 vídeos com
tablatura=true e frac_tablatura >= 0.5 (fora ouro, fora vídeos da T8.2, da T8.3 e da T8.4, fora
canais descartados), preferindo forma != rolante. Por vídeo, o instante com tab=true mais perto do meio da janela de
tablatura. A leitura é do produto: painel.escolher_ou_mascara + detector_tab.detectar.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import cv2
import numpy as np

from tab import caminhos, detector_tab, leitor, painel

RAIZ = Path("/app")
SAIDA = caminhos.SAIDA / "tablatura" / "t85"
CENSO = RAIZ / "data" / "saida" / "censo" / "censo_cache.jsonl"
OURO = RAIZ / "data" / "gold" / "ouro_video"
CANAIS_FORA = {"violaodecria", "tv cifras", "raman korshun"}
TRECHOS_FORA = ("campanitas",)
LARGURA_PAINEL = 1200
FONTE = cv2.FONT_HERSHEY_SIMPLEX


def carregar_censo() -> list[dict]:
    """Lê uma linha por vídeo do censo.

    Returns:
        Lista de registros do censo.
    """
    with CENSO.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def ouro_videos() -> set[str]:
    """Caminhos relativos dos vídeos que já são ouro.

    Returns:
        Conjunto de campos ``video`` do ouro de vídeo.
    """
    return {
        json.loads(p.read_text(encoding="utf-8"))["video"]
        for p in OURO.glob("*.json")
    }


def videos_usados() -> set[str]:
    """Caminhos relativos dos vídeos já usados na T8.2, na T8.3 e na T8.4 (plano e índice).

    Returns:
        União dos campos ``video`` de ``plano.json`` e de ``ferramenta/indice.json``.
    """
    usados: set[str] = set()
    for lote in ("t82", "t83", "t84"):
        base = RAIZ / "data" / "saida" / "tablatura" / lote
        plano = json.loads((base / "plano.json").read_text(encoding="utf-8"))
        indice = json.loads(
            (base / "ferramenta" / "indice.json").read_text(encoding="utf-8")
        )
        usados |= {t["video"] for t in plano["telas"]} | {i["video"] for i in indice}
    return usados


def elegivel(rec: dict, ouro: set[str]) -> bool:
    """Diz se o vídeo pode entrar no sorteio.

    Args:
        rec: registro do censo.
        ouro: vídeos que já são ouro.

    Returns:
        True se tem tablatura alta e não é ouro nem canal/vídeo descartado.
    """
    if rec["canal"] in CANAIS_FORA or rec["arquivo"] in ouro:
        return False
    if any(trecho in rec["arquivo"] for trecho in TRECHOS_FORA):
        return False
    return bool(rec.get("tablatura")) and (rec.get("frac_tablatura") or 0) >= 0.5


def sortear(
    pool: list[dict], rng: random.Random
) -> tuple[list[dict], str]:
    """Escolhe até 2 vídeos de um canal, preferindo forma diferente de rolante.

    Args:
        pool: vídeos elegíveis do canal, já ordenados.
        rng: gerador com semente 3.

    Returns:
        Os vídeos sorteados e uma nota sobre o sorteio.
    """
    nao_rolante = [r for r in pool if r.get("forma") != "rolante"]
    rolante = [r for r in pool if r.get("forma") == "rolante"]
    if len(nao_rolante) >= 2:
        return rng.sample(nao_rolante, 2), "2 nao_rolante"
    if len(nao_rolante) == 1:
        if rolante:
            return nao_rolante + [rng.choice(rolante)], "1 nao_rolante + 1 rolante"
        return nao_rolante, "so 1 video elegivel"
    if len(rolante) >= 2:
        return rng.sample(rolante, 2), "so_rolante"
    return rolante, "so_rolante; 1 video elegivel"


def instante_central(rec: dict) -> float | None:
    """Instante com tab=true mais perto do meio da janela de tablatura.

    Args:
        rec: registro do censo.

    Returns:
        O instante em segundos, ou None se não há instante com tablatura.
    """
    tabs = [i["t"] for i in rec["instantes"] if i.get("tab")]
    if not tabs:
        return None
    meio = (min(tabs) + max(tabs)) / 2
    return min(tabs, key=lambda t: abs(t - meio))


def desenhar_painel(roi: np.ndarray, notas: list[dict], linhas: list[float]) -> np.ndarray:
    """Desenha o painel com as cordas (verde) e a casa de cada nota (vermelho).

    Args:
        roi: recorte do painel em BGR.
        notas: notas com ``x`` (px do recorte) e ``casa``.
        linhas: y de cada corda, em px do recorte.

    Returns:
        Imagem BGR para salvar.
    """
    s = LARGURA_PAINEL / roi.shape[1] if roi.shape[1] < LARGURA_PAINEL else 1.0
    img = (
        cv2.resize(roi, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
        if s != 1.0
        else roi.copy()
    )
    for y in linhas:
        cv2.line(img, (0, int(y * s)), (img.shape[1], int(y * s)), (0, 200, 0), 1)
    topo = min(linhas) * s
    escala, esp = 0.9, 2
    for n in notas:
        texto = str(n["casa"])
        x = int(round(n["x"] * s))
        (tw, th), base = cv2.getTextSize(texto, FONTE, escala, esp)
        y1 = max(int(topo) - 8, th + 8)
        x0 = max(3, x - tw // 2)
        y0 = y1 - th - 6
        cv2.rectangle(img, (x0 - 3, y0 - 3), (x0 + tw + 3, y1 + base + 3), (255, 255, 255), -1)
        cv2.putText(img, texto, (x0, y1), FONTE, escala, (0, 0, 255), esp, cv2.LINE_AA)
    return img


def analisar(rec: dict, t: float, modelo, pasta: Path) -> dict:
    """Extrai o quadro, roda o produto e grava PNGs e JSON da tela.

    Args:
        rec: registro do censo.
        t: instante em segundos.
        modelo: DetectorTab carregado.
        pasta: pasta de saída da tela.

    Returns:
        Linha do resumo (dict).
    """
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = str(caminhos.acervo() / rec["arquivo"])
    quadro = leitor.quadro_em(caminho, t)
    if quadro is None:
        return {"erro": "quadro nao extraido", "notas": [], "painel": None}
    c = painel.escolher_ou_mascara(quadro)
    quadro_png = quadro.copy()
    if c is None:
        cv2.imwrite(str(pasta / "quadro.png"), quadro_png)
        cv2.imwrite(str(pasta / "painel.png"), quadro_png)
        (pasta / "tela.json").write_text(
            json.dumps(
                {"video": rec["arquivo"], "canal": rec["canal"], "t": t, "painel": None,
                 "passo": None, "linhas_y": None, "notas": [],
                 "aviso": "escolher_ou_mascara devolveu None"},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        return {"erro": "sem painel", "notas": [], "painel": None}

    h, w = c.roi.shape[:2]
    aviso = ""
    if not np.array_equal(quadro[c.y0 : c.y0 + h, c.x0 : c.x0 + w], c.roi):
        aviso = "roi_nao_confere_com_quadro"
    cv2.rectangle(quadro_png, (c.x0, c.y0), (c.x0 + w, c.y0 + h), (0, 255, 0), 3)
    cv2.imwrite(str(pasta / "quadro.png"), quadro_png)

    detectadas = detector_tab.detectar(modelo, c.roi, c.grade.linhas_y, c.passo)
    notas = [
        {
            "corda": int(d["corda"]),
            "casa": str(d["rotulo"]),
            "x_centro_quadro": round(float(d["x"]) + c.x0, 1),
            "confianca": round(float(d["confianca"]), 3),
        }
        for d in sorted(detectadas, key=lambda d: d["x"])
    ]
    linhas_abs = [c.y0 + y for y in c.grade.linhas_y]
    cv2.imwrite(str(pasta / "painel.png"), desenhar_painel(c.roi, [
        {"x": d["x"], "casa": d["rotulo"]} for d in sorted(detectadas, key=lambda d: d["x"])
    ], c.grade.linhas_y))
    tela = {
        "video": rec["arquivo"],
        "canal": rec["canal"],
        "t": t,
        "painel": {"nome": c.nome, "x0": c.x0, "y0": c.y0, "x1": c.x0 + w, "y1": c.y0 + h},
        "passo": round(c.passo, 2),
        "linhas_y": linhas_abs,
        "notas": notas,
        "aviso": aviso,
    }
    (pasta / "tela.json").write_text(
        json.dumps(tela, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"erro": "", "notas": notas, "painel": tela["painel"], "aviso": aviso}


def main() -> None:
    """Sorteia, processa as telas e grava plano.json e resumo.csv."""
    censo = carregar_censo()
    ouro = ouro_videos() | videos_usados()
    elegiveis: dict[str, list[dict]] = {}
    for rec in censo:
        if elegivel(rec, ouro):
            elegiveis.setdefault(rec["canal"], []).append(rec)
    for pool in elegiveis.values():
        pool.sort(key=lambda r: r["arquivo"])

    todos_canais = sorted({r["canal"] for r in censo})
    sem_sorteavel = [c for c in todos_canais if c not in elegiveis]
    rng = random.Random(3)
    plano = []
    for ci, canal in enumerate(sorted(elegiveis), start=1):
        escolhidos, nota = sortear(elegiveis[canal], rng)
        for k, rec in enumerate(escolhidos, start=1):
            plano.append(
                {"canal": canal, "ci": ci, "k": k, "rec": rec, "nota_sorteio": nota}
            )

    modelo = detector_tab.carregar(caminhos.DETECTOR_PADRAO)
    SAIDA.mkdir(parents=True, exist_ok=True)
    linhas_resumo = []
    registro_plano = []
    for item in plano:
        rec = item["rec"]
        t = instante_central(rec)
        pasta = SAIDA / "telas" / f"c{item['ci']:02d}_v{item['k']}"
        res = analisar(rec, t, modelo, pasta)
        n = len(res["notas"])
        obs = []
        if item["nota_sorteio"] != "2 nao_rolante":
            obs.append(item["nota_sorteio"])
        if res.get("erro"):
            obs.append(res["erro"])
        if res.get("aviso"):
            obs.append(res["aviso"])
        linhas_resumo.append(
            {
                "canal": item["canal"],
                "video": rec["arquivo"],
                "t": round(t, 2),
                "painel_ok": "nao_olhado",
                "n_notas": n,
                "observacao": "; ".join(obs) + f" [forma={rec.get('forma')}, frac={rec.get('frac_tablatura')}]",
                "pasta": str(pasta.relative_to(RAIZ)),
            }
        )
        registro_plano.append(
            {"canal": item["canal"], "video": rec["arquivo"], "forma": rec.get("forma"),
             "t": round(t, 2), "nota_sorteio": item["nota_sorteio"],
             "n_notas": n, "erro": res.get("erro", "")}
        )
        print(f"{item['canal']} {item['k']} t={t:.2f} notas={n} {res.get('erro','')}", flush=True)

    with (SAIDA / "resumo.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas_resumo[0].keys()))
        w.writeheader()
        w.writerows(linhas_resumo)
    (SAIDA / "plano.json").write_text(
        json.dumps(
            {"sem_sorteavel": sem_sorteavel, "telas": registro_plano},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print("sem sorteavel:", sem_sorteavel)


if __name__ == "__main__":
    main()
