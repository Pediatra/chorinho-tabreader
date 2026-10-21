"""Rodada 2020: olhar as notas erradas confirmadas (paolo tela 4, charagua tela 6)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/data/saida/audio/r2020")
import medir as X  # noqa: E402
from tab import audio_som_medir as M  # noqa: E402
from tab import cruzar_fontes as C  # noqa: E402

CASOS = {"paolo_those_who_wait": (1, 4, range(42, 52)), "transcriptor_charagua": (3, 6, range(1, 9))}
ouro = json.loads((X.GOLD / "audio" / "acordes_2018.json").read_text(encoding="utf-8"))
for nome, (gid, tid, cols) in CASOS.items():
    prod = json.loads((X.R17 / f"{nome}.json").read_text(encoding="utf-8"))
    cz, capo = X.cruzado(prod, nome)
    tc = next(t for t in cz["telas"] if t["tela"] == tid)
    som = json.loads((X.SOM / f"{nome}.json").read_text(encoding="utf-8"))
    eventos = M.eventos_do_som(som["notas"], tc["t0"] - M.FOLGA_S, tc["t1"] + M.FOLGA_S)
    print(f"=== {nome} tela {tid} exib {tc['exibicao']} t0 {tc['t0']:.2f} t1 {tc['t1']:.2f} capo {capo}")
    gold = next(t for t in ouro["telas"] if t["id"] == gid)
    for c in cols:
        notas = [n for n in tc["notas"] if n["coluna"] == c]
        if not notas:
            continue
        x = sum(n["x"] for n in notas) / len(notas)
        g = sorted((n["corda"], n["casa"]) for n in gold["notas"] if abs(n["x_centro_quadro"] - x) < 12 and not n.get("removida"))
        print(f" col {c} x {x:.0f} prod {[(n['corda'], n['casa'], n['midi'], n['veredito'][:4], n.get('t_som')) for n in notas]}")
        print(f"        ouro {g} ouro_midi {sorted(M.midi_da_nota(k, M.casa_inteira(v), capo) for k, v in g if M.casa_inteira(v) is not None)}")
        ts = [n.get("t_som") for n in notas if n.get("t_som") is not None]
        if ts:
            ev = [e for e in eventos if abs(e[0]["t_ini"] - ts[0]) < 0.07]
            print(f"        som  {[sorted((round(n['t_ini'], 2), n['midi']) for n in e) for e in ev]}")
