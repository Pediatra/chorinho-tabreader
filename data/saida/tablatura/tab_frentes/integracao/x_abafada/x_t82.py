"""Rótulos x por modelo nas 35 telas conferidas da T8.2 (fora do treino de todos)."""

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")
from tab import caminhos, detector_tab, leitor, painel  # noqa: E402

FERR = Path("/app/data/saida/t82/ferramenta")
MODELOS = {
    "novo_x": "/app/artefatos/detector_tab_final_s1_gerx/modelo.pt",
    "produto": "/app/artefatos/detector_tab_final_s1_ger/modelo.pt",
    "d4_ger": "/app/artefatos/detector_tab_v3ft_d4_ger/modelo.pt",
    "d2_ger": "/app/artefatos/detector_tab_v3ft_d2_ger/modelo.pt",
}
conf = json.loads((FERR / "conferencia_t82.json").read_text(encoding="utf-8"))
indice = {r["id"]: r for r in json.loads((FERR / "indice.json").read_text(encoding="utf-8"))}
mods = {k: detector_tab.carregar(v) for k, v in MODELOS.items()}
tot = collections.Counter()
for tela in conf["telas"]:
    if not tela.get("conferida"):
        continue
    r = indice[tela["id"]]
    q = leitor.quadro_em(str(caminhos.acervo() / r["video"]), r["t"])
    c = painel.escolher_ou_mascara(q)
    if c is None:
        continue
    nx = sum(1 for g in tela.get("regioes") or [] if "x" in (g.get("tecnica") or []))
    tot["regioes_x"] += nx
    linha = [f"tela {tela['id']} {r['canal'][:14]:14s} regx {nx}"]
    for k, m in mods.items():
        d = detector_tab.detectar(m, c.roi, c.grade.linhas_y, c.passo)
        n = sum(1 for p in d if p["rotulo"] == "x")
        tot[k] += n
        linha.append(f"{k} x={n}")
    if nx or any("x=0" not in s for s in linha[1:]):
        print(" | ".join(linha), flush=True)
print(dict(tot))
