"""Medição n3 (pedido 4): padrões de casa errada dos v2, híbrido 1 e híbrido 2.

Reusa medir.py (base, detectores, casamento), medir2.py (recorte) e tab.reconhecer
(_recortar e _probs, a mesma convenção do classificador da BASE).

HÍBRIDO 1: posição = detector v2; casa = casa da BASE se a BASE tem nota na mesma corda
com |dx| <= 0,5 passo; senão casa do detector.
HÍBRIDO 2: posição = detector v2; casa = classificador da BASE (oficial_3) sobre o
glifo do segmentar na mesma corda e |dx| <= 0,5 passo; se não há glifo, caixa sintética
do tamanho do algarismo (como ler_notas), e a classe é o algarismo de maior probabilidade.

Saídas em data/saida/n3/: hibrido.txt, casa3_*.png, casa3_mont_*.png.

Uso (container, cwd /app):
    python /app/data/saida/n3/medir4.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import medir as M  # noqa: E402
import medir2 as M2  # noqa: E402
import medir3 as M3  # noqa: E402
from tab import detector_tab  # noqa: E402
from tab.avaliar_video import NotaPrevista  # noqa: E402
from tab.digito import carregar as carregar_discriminador  # noqa: E402
from tab.ouro_video import LARGURA_ALGARISMO_PASSOS  # noqa: E402
from tab.reconhecer import ALGARISMOS, _probs, _recortar, carregar_modelo  # noqa: E402
from tab.tabseg import segmentar  # noqa: E402

SAIDA = M.SAIDA
CHAVES = ("v2_s1", "v2_s2", "v2_s3")
VIDEOS_CASA = {
    "retrato_brasileiro_v2": "ret",
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics": "eob",
    "greensleeves_guia_de_estudio_partitura_tab_pdf": "gre",
}


def hibrido1(reg: dict, chave: str) -> list[NotaPrevista]:
    """Posição do detector; casa da BASE quando há nota da BASE perto na mesma corda."""
    passo = reg["passo"]
    out = []
    for p in reg["det_prev"].get(chave, []):
        perto = [
            (abs(xb - p.x), cb)
            for corda_b, cb, xb in reg["base"]
            if corda_b == p.corda and abs(xb - p.x) <= 0.5 * passo
        ]
        casa = min(perto)[1] if perto else p.casa
        out.append(NotaPrevista(p.corda, casa, p.x, None))
    return out


def hibrido2(reg: dict, chave: str, base_modelo, rotulos, dev) -> list[NotaPrevista]:
    """Posição do detector; casa = classificador da BASE sobre o glifo da mesma posição."""
    previstas = reg["det_prev"].get(chave, [])
    if not previstas:
        return []
    cand = reg["cand"]
    passo = reg["passo"]
    grade = segmentar(cand.roi)
    gray = cv2.cvtColor(cand.roi, cv2.COLOR_BGR2GRAY) if cand.roi.ndim == 3 else cand.roi
    linhas = reg["linhas"]
    recortes = []
    for p in previstas:
        xr = p.x - cand.x0
        melhores = [
            (abs((g.x0 + g.x1) / 2 - xr), g)
            for g in grade.glifos
            if g.corda == p.corda and abs((g.x0 + g.x1) / 2 - xr) <= 0.5 * passo
        ]
        if melhores:
            g = min(melhores, key=lambda t: t[0])[1]
            recortes.append(_recortar(gray, g.x0, g.y0, g.x1, g.y1))
        else:
            y = linhas[p.corda - 1]
            largura = LARGURA_ALGARISMO_PASSOS * passo
            caixa = (
                int(xr - largura / 2),
                int(y - 0.4 * passo),
                int(xr + largura / 2),
                int(y + 0.4 * passo),
            )
            recortes.append(_recortar(gray, *caixa))
    probs = _probs(recortes, base_modelo, dev)
    idx_dig = [i for i, r in enumerate(rotulos) if r in ALGARISMOS]
    out = []
    for p, pr in zip(previstas, probs):
        casa = rotulos[max(idx_dig, key=lambda i: pr[i])]
        out.append(NotaPrevista(p.corda, int(casa), p.x, None))
    return out


def metricas(reg: dict, previstas: list[NotaPrevista]) -> dict:
    """Métricas de uma previsão contra o ouro da tela."""
    return M._metricas_par(reg["notas_ouro"], previstas, reg["meia"])


def linha(nome: str, ms: list[dict]) -> str:
    """Uma linha da tabela, com P, R, casa e contagens."""
    r = M.resumo(ms)
    return (
        f"  {nome:<14} entregues={r['entregues']:>4} casadas={r['casadas']:>4} "
        f"casa_certa={r['casa_certa']:>4} | P={M.fmt(r['P'])} R={M.fmt(r['R'])} "
        f"casa={M.fmt(r['AC'])}"
    )


def main() -> int:
    """Mede base, v2 puro, híbrido 1 e híbrido 2; casa errada e recortes."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    detectores = {k: detector_tab.carregar(M.DETECTORES_CAMINHO[k]) for k in CHAVES}
    base = carregar_modelo(str(M.MODELO_BASE))
    disc = carregar_discriminador()
    videos = M.videos_do_run()
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    videos[M.EXTRA_SLUG] = "/acervo/" + extra["video"]
    por_video = {}
    for slug in videos:
        if (M.OURO / f"{slug}.json").exists():
            print(f"== {slug}", flush=True)
            por_video[slug] = M.medir_video(slug, videos[slug], base, detectores, disc)

    # Métricas por (vídeo, variante)
    texto = ["Híbrido: posição = detector v2; casa = ver definição no script medir4.py.",
             "P e R dos híbridos são iguais aos do v2 puro (casamento só usa corda e x).",
             ""]
    h2_mismatch = 0
    tot: dict[str, list[dict]] = {}
    for slug, regs in por_video.items():
        texto.append(f"## {slug}")
        linhas_v = {"BASE": [r["m_base"] for r in regs]}
        for chave in CHAVES:
            puro, h1, h2 = [], [], []
            for reg in regs:
                if reg["sem_painel"] or reg["cand"] is None:
                    m0 = metricas(reg, [])
                    puro.append(m0)
                    h1.append(m0)
                    h2.append(m0)
                    continue
                puro.append(metricas(reg, reg["det_prev"].get(chave, [])))
                p1 = hibrido1(reg, chave)
                h1.append(metricas(reg, p1))
                p2 = hibrido2(reg, chave, base[0], base[1], base[2])
                h2.append(metricas(reg, p2))
                if [x.x for x in p2] != [x.x for x in reg["det_prev"].get(chave, [])]:
                    h2_mismatch += 1
            linhas_v[chave] = puro
            linhas_v[chave + " H1"] = h1
            linhas_v[chave + " H2"] = h2
        for nome, ms in linhas_v.items():
            texto.append(linha(nome, ms))
            tot.setdefault(nome, []).extend(ms)
        texto.append("")

    texto.append("## TOTAL (todos os vídeos)")
    for nome, ms in tot.items():
        texto.append(linha(nome, ms))
    texto.append(f"(verificação: H2 com x diferente do detector em {h2_mismatch} telas)")
    texto.append("")

    # ---- casa errada dos v2 nos 3 vídeos --------------------------------
    texto.append("# Padrões de casa errada (ouro -> lido), v2 puro, por vídeo")
    for slug, abrev in VIDEOS_CASA.items():
        pares_v: list[tuple[int, int, int, float, str, int]] = []
        contagem: Counter = Counter()
        for chave in ("v2_s1", "v2_s2"):
            for reg in por_video[slug]:
                if reg["sem_painel"] or reg["cand"] is None:
                    continue
                for corda, c_ouro, c_lido, x in M3.pares_casa(reg, chave):
                    pares_v.append((reg["id"], corda, c_ouro, x, chave, c_lido))
                    contagem[(c_ouro, c_lido)] += 1
        texto.append(f"{slug}: {len(pares_v)} pares (v2_s1 + v2_s2)")
        for (o, l), n in contagem.most_common():
            texto.append(f"  ouro {o} -> lido {l}: {n}")
        # recortes: 3 por padrão principal (top 2 padrões)
        for (o, l), _n in contagem.most_common(2):
            exemplos = [p for p in pares_v if p[2] == o and p[5] == l][:3]
            imgs = []
            for i, (tid, corda, c_ouro, x, chave, c_lido) in enumerate(exemplos):
                reg = next(r for r in por_video[slug] if r["id"] == tid)
                nome = SAIDA / f"casa3_{abrev}_{o}to{l}_{i}.png"
                M2.recorte(reg, x, corda, nome,
                           [(f"ouro {c_ouro}", (0, 200, 0), x, -0.3),
                            (f"{chave} {c_lido}", (0, 0, 255), x, 0.3)])
                imgs.append(nome)
                texto.append(f"    {nome.name}: tela={tid} corda={corda} x={x:.1f} {chave}")
    (SAIDA / "hibrido.txt").write_text("\n".join(texto) + "\n", encoding="utf-8")
    print("\n".join(texto), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
