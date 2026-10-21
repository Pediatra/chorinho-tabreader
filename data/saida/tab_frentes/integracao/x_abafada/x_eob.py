"""Quantos rótulos x cada modelo dá nas telas conferidas do EOB (mesmo quadro e recorte)."""

import collections
import json
import sys

sys.path.insert(0, "/app")
from tab import caminhos, detector_tab, leitor, painel  # noqa: E402

OURO = "/app/data/gold/ouro_video/end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics.json"
MODELOS = {
    "novo_x": "/app/artefatos/detector_tab_final_s1_gerx/modelo.pt",
    "produto": "/app/artefatos/detector_tab_final_s1_ger/modelo.pt",
    "d4_ger": "/app/artefatos/detector_tab_v3ft_d4_ger/modelo.pt",
    "final_s1": "/app/artefatos/detector_tab_final_s1/modelo.pt",
}
ouro = json.load(open(OURO, encoding="utf-8"))
mods = {k: detector_tab.carregar(v) for k, v in MODELOS.items()}
for tela in ouro["telas"]:
    if not tela.get("regioes"):
        continue
    q = leitor.quadro_em(str(caminhos.acervo() / ouro["video"]), tela["quadro_ref_s"])
    c = painel.escolher_ou_mascara(q)
    nx_ouro = sum(1 for r in tela["regioes"] if r.get("tecnica") == ["x"])
    linha = [f"tela {tela['id']} regioes_x {nx_ouro}"]
    for k, m in mods.items():
        d = detector_tab.detectar(m, c.roi, c.grade.linhas_y, c.passo)
        cnt = collections.Counter(p["rotulo"] for p in d)
        linha.append(f"{k}: n={len(d)} x={cnt.get('x', 0)}")
    print(" | ".join(linha), flush=True)
