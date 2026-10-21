"""Tabela por exibição das saídas do alinhador (leitura apenas)."""

import collections
import json
import sys
from pathlib import Path

PRODUTOS = Path("/var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/a2/produtos")
APELIDOS = sys.argv[1:] or [
    "iwaki_la_vie_en_rose",
    "shin_izumi_room_335",
    "kimny_from_this_place",
]
for apelido in APELIDOS:
    prod = json.loads((PRODUTOS / f"{apelido}.json").read_text("utf-8"))
    al = json.loads((PRODUTOS / f"alinhado_{apelido}.json").read_text("utf-8"))
    t_tela = {t["id"]: t for t in prod["telas"]}
    print(f"== {apelido}  (exibicao null nas notas: {sum(n['exibicao'] is None for n in prod['notas'])}/{len(prod['notas'])})")
    print("tela ex  t0-t1(s)        cols  trecho      casadas  T_usado  cos_med  recusada  motivos_recusa")
    colunas = collections.defaultdict(list)
    for c in al["colunas"]:
        colunas[(c["tela"], c["exibicao"])].append(c)
    for ex in al["exibicoes"]:
        tela, idx = ex["tela"], ex["exibicao"]
        t = t_tela[tela]["exibicoes"][idx]
        mot = collections.Counter(
            c["motivo"] for c in colunas[(tela, idx)] if c["t_audio"] is None
        )
        mot_txt = ", ".join(f"{k} {v}" for k, v in mot.most_common()) or "-"
        tr = ex.get("trecho_colunas")
        print(
            f"{tela:>4} {idx:>2}  {t['t0']:>7.2f}-{t['t1']:<7.2f}  {ex['n_colunas']:>4}  "
            f"{str(tr):<10}  {ex.get('n_casadas', 0):>7}  {str(ex.get('T_usado_s')):>7}  "
            f"{str(ex.get('cos_medio')):>7}  {'SIM' if ex['recusada_exibicao'] else 'nao':>8}  {mot_txt}"
            + (f" | {ex['motivo_exibicao']}" if ex["recusada_exibicao"] else "")
        )
    print()
