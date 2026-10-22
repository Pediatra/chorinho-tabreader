"""n4 seguimento: dobra 1 com sementes 1, 2 e 3 (retrato e la_vie, fora do treino).

Mede BASE, v3_s1 e os três ft_d1 no mesmo quadro (medir.medir_video). Para la_vie,
com o ft s1: lista inventadas e perdidas (tela, corda, x, rótulo) e grava recortes
ampliados em data/saida/n4/lavie_*.png.

Uso (container, cwd /app):
    python /app/data/saida/n4/avaliar_seeds.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app")

import medir as M  # noqa: E402
import medir2 as M2  # noqa: E402
import medir3 as M3  # noqa: E402
from tab import detector_tab  # noqa: E402
from tab.avaliar_video import casar_notas  # noqa: E402
from tab.digito import carregar as carregar_discriminador  # noqa: E402
from tab.reconhecer import carregar_modelo  # noqa: E402

SAIDA = Path("/app/data/saida/n4")
ARTEFATOS = Path("/app/artefatos")
VIDEOS = ("retrato_brasileiro_v2", "la_vie_en_rose_edith_piaf_tab")
SEMENTES = {
    "ft_s1": "detector_tab_v3ft_d1",
    "ft_s2": "detector_tab_v3ft_d1_s2",
    "ft_s3": "detector_tab_v3ft_d1_s3",
}
COR_OURO = (0, 200, 0)
COR_INV = (0, 0, 255)


def main() -> int:
    """Mede os quatro modelos nos dois vídeos e lista erros de la_vie (ft_s1)."""
    videos = M.videos_do_run()
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    videos.setdefault(M.EXTRA_SLUG, "/acervo/" + extra["video"])
    base = carregar_modelo(str(M.MODELO_BASE))
    disc = carregar_discriminador()
    detectores = {"v3_s1": detector_tab.carregar(ARTEFATOS / "detector_tab_v3_s1" / "modelo.pt")}
    for chave, pasta in SEMENTES.items():
        detectores[chave] = detector_tab.carregar(ARTEFATOS / pasta / "modelo.pt")

    linhas = ["Sementes da dobra 1 (retrato e la_vie fora do treino). P / R / casa.", ""]
    resultado: dict = {}
    for slug in VIDEOS:
        regs = M.medir_video(slug, videos[slug], base, detectores, disc)
        resultado[slug] = {}
        linhas.append(f"## {slug}")
        resumos = {"BASE": M.resumo([r["m_base"] for r in regs])}
        for chave in ("v3_s1", *SEMENTES):
            resumos[chave] = M.resumo([r["m_det"][chave] for r in regs])
        for nome, s in resumos.items():
            linhas.append(M.linha_resumo(nome, s))
            resultado[slug][nome] = {k: s[k] for k in ("P", "R", "AC", "inventadas", "perdidas", "casadas")}
        linhas.append("")
        if slug == VIDEOS[1]:
            _listar_lavie(regs)
    linhas.append("## Ver lavie_erros.txt para inventadas e perdidas de la_vie (ft_s1)")
    (SAIDA / "seeds_d1.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (SAIDA / "seeds_d1.json").write_text(json.dumps(resultado, indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    print("\n".join(linhas), flush=True)
    return 0


def _listar_lavie(regs: list[dict]) -> None:
    """Lista e desenha inventadas e perdidas de la_vie para o ft_s1."""
    chave = "ft_s1"
    saida: list[str] = ["# la_vie_en_rose, ft_s1 (dobra 1, semente 1): erros", ""]
    for reg in regs:
        if reg["sem_painel"] or reg["cand"] is None:
            continue
        previstas = reg["det_prev"].get(chave, [])
        pares = casar_notas(reg["notas_ouro"], previstas, reg["meia"])
        casados_ouro = {i for i, _ in pares}
        casados_prev = {j for _, j in pares}
        for j, p in enumerate(previstas):
            if j in casados_prev:
                continue
            saida.append(f"INVENTADA tela={reg['id']} corda={p.corda} x={p.x:.1f} rotulo_lido={p.casa}")
            nome = SAIDA / f"lavie_inv_t{reg['id']}_c{p.corda}_x{int(p.x)}.png"
            M2.recorte(reg, p.x, p.corda, nome, [(f"ft_s1 {p.casa}", COR_INV, p.x, 0.0)])
        for i, n in enumerate(reg["notas_ouro"]):
            if i in casados_ouro:
                continue
            corda, casa, x = int(n["corda"]), int(n["casa"]), float(n["x_centro_quadro"])
            saida.append(f"PERDIDA tela={reg['id']} corda={corda} x={x:.1f} rotulo_ouro={casa}")
            nome = SAIDA / f"lavie_per_t{reg['id']}_c{corda}_x{int(x)}.png"
            M2.recorte(reg, x, corda, nome, [(f"ouro {casa}", COR_OURO, x, 0.0)])
    (SAIDA / "lavie_erros.txt").write_text("\n".join(saida) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
