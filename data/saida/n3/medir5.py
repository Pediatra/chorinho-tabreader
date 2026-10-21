"""Medição n3 (pedido 5): v3 - casa errada (3 vídeos) e inventadas do v3_s1 (8 vídeos).

Reusa medir.py (tabela principal, base, detectores), medir2.py (recorte) e medir3.py
(inventadas, pares de casa, folha). Saídas em data/saida/n3/:
  casa5_<vid>_<chave>.txt : pares ouro->lido por vídeo e semente
  inv5_<vid>_t<tela>_x<x>_c<corda>.png, inv5_<vid>_mont.png, inv5_indice.txt

Uso (container, cwd /app):
    python /app/data/saida/n3/medir5.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")
sys.path.insert(0, "/app")

import medir as M  # noqa: E402
import medir2 as M2  # noqa: E402
import medir3 as M3  # noqa: E402
from tab import detector_tab  # noqa: E402
from tab.digito import carregar as carregar_discriminador  # noqa: E402
from tab.reconhecer import carregar_modelo  # noqa: E402

SAIDA = M.SAIDA
CHAVES_V3 = ("v3_s1", "v3_s2", "v3_s3")
VIDEOS_CASA = {
    "retrato_brasileiro_v2": "ret",
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics": "eob",
    "greensleeves_guia_de_estudio_partitura_tab_pdf": "gre",
}
COR_CASA = (0, 0, 255)
COR_OURO = (0, 200, 0)


def main() -> int:
    """Tabela principal (tabela_v3.txt) e as medições dos pedidos 3 e 5."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    print("== tabela principal (medir.main)", flush=True)
    M.main()

    detectores = {k: detector_tab.carregar(M.DETECTORES_CAMINHO[k]) for k in CHAVES_V3}
    base = carregar_modelo(str(M.MODELO_BASE))
    disc = carregar_discriminador()
    videos = M.videos_do_run()
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    videos[M.EXTRA_SLUG] = "/acervo/" + extra["video"]

    por_video = {}
    for slug, video in videos.items():
        if (M.OURO / f"{slug}.json").exists():
            print(f"== medindo {slug}", flush=True)
            por_video[slug] = M.medir_video(slug, video, base, detectores, disc)

    rel: list[str] = ["# Casa errada dos v3 (ouro -> lido), 3 vídeos"]
    for slug, abrev in VIDEOS_CASA.items():
        rel.append(f"## {slug}")
        for chave in CHAVES_V3:
            contagem: Counter = Counter()
            exemplos = []
            for reg in por_video[slug]:
                if reg["sem_painel"] or reg["cand"] is None:
                    continue
                for corda, c_ouro, c_lido, x in M3.pares_casa(reg, chave):
                    contagem[(c_ouro, c_lido)] += 1
                    exemplos.append((reg, corda, c_ouro, c_lido, x))
            total = sum(contagem.values())
            rel.append(f"  {chave}: {total} pares")
            for (o, l), n in contagem.most_common():
                rel.append(f"    ouro {o} -> lido {l}: {n}")
            for reg, corda, c_ouro, c_lido, x in exemplos[:3]:
                nome = SAIDA / f"casa5_{abrev}_{chave}_t{reg['id']}_x{int(x)}_c{corda}.png"
                M2.recorte(reg, x, corda, nome,
                           [(f"ouro {c_ouro}", COR_OURO, x, -0.3),
                            (f"{chave} {c_lido}", COR_CASA, x, 0.3)])
    (SAIDA / "casa5_v3.txt").write_text("\n".join(rel) + "\n", encoding="utf-8")
    print("\n".join(rel), flush=True)

    # ---- inventadas do v3_s1 nos 8 vídeos --------------------------------
    inv_rel: list[str] = ["# Inventadas do v3_s1 por vídeo"]
    indice: list[str] = []
    for slug, regs in por_video.items():
        abrev = slug[:12]
        itens = []
        for reg in regs:
            if reg["sem_painel"] or reg["cand"] is None:
                continue
            for corda, casa, x, conf in M3.inventadas(reg, "v3_s1"):
                nome = SAIDA / f"inv5_{abrev}_t{reg['id']}_x{int(x)}_c{corda}.png"
                M2.recorte(reg, x, corda, nome, [(f"v3 {casa}", COR_CASA, x, 0.0)])
                itens.append((reg["id"], corda, x, casa, conf, nome))
        inv_rel.append(f"{slug}: {len(itens)}")
        for idx, (tid, corda, x, casa, conf, nome) in enumerate(itens):
            indice.append(
                f"{abrev}\t{idx}\ttela={tid}\tcorda={corda}\tx={x:.1f}\t"
                f"rotulo={casa}\tconf={conf:.3f}\t{nome.name}"
            )
        if itens:
            M3.folha([(*it[:5], it[5]) for it in itens], SAIDA / f"inv5_{abrev}_mont.png")
    (SAIDA / "inv5_indice.txt").write_text("\n".join(indice) + "\n", encoding="utf-8")
    (SAIDA / "inv5_v3.txt").write_text("\n".join(inv_rel) + "\n", encoding="utf-8")
    print("\n".join(inv_rel), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
