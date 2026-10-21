"""Remedida da 0153: reexecuta as 6 janelas da 0152 e aplica o palpite pelo cursor.

Roda dentro do container, com /app = worktree tab/c1-rolagem. Não usa GPU.
Confere que o dx_a de cada salto sai igual ao da 0152 (reprodutibilidade) e grava
saltos.json e metodo.json em rodada0153/<janela>/.
"""

import json
import subprocess
import sys
from pathlib import Path

R0152 = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0152")
R0153 = Path("/app/data/saida/tab_frentes/fc_rolagem/rodada0153")
JANELAS = [
    "mrtabs_w150",
    "mrtabs_w180",
    "mrtabs_w210",
    "kenneth_w62",
    "kenneth_w92",
    "kenneth_w122",
]
MAO = {
    "mrtabs": R0152 / "mao_mrtabs_0152.json",
    "kenneth": R0152 / "mao_kenneth.json",
}


def main() -> int:
    """Roda as janelas, confere a reprodutibilidade e aplica o palpite."""
    for nome in JANELAS:
        rel = json.loads((R0152 / nome / "saltos.json").read_text(encoding="utf-8"))
        pasta = R0153 / nome
        pasta.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable,
            "-m",
            "tab.rolagem_saltos",
            rel["video"],
            "--t0",
            str(rel["t0"]),
            "--dur",
            str(rel["dur"]),
            "--qps",
            str(rel["qps"]),
            "--recorte",
            str(rel["recorte"][0]),
            str(rel["recorte"][1]),
            "--x-max",
            str(rel["x_max"]),
            "--saida",
            str(pasta),
        ]
        subprocess.run(cmd, check=True)
        novo = json.loads((pasta / "saltos.json").read_text(encoding="utf-8"))
        dif = 0.0
        ok_t = len(novo["saltos"]) == len(rel["saltos"])
        if ok_t:
            for a, b in zip(rel["saltos"], novo["saltos"], strict=True):
                dif = max(dif, abs(a["dx_total"] - b["dx_total"]))
                ok_t = ok_t and a["t_antes"] == b["t_antes"]
        print(f"[reprod] {nome}: saltos {len(novo['saltos'])}, "
              f"mesmos instantes={ok_t}, maior |dx_a 0152 - 0153|={dif:.6f}")
        grupo = "mrtabs" if nome.startswith("mrtabs") else "kenneth"
        cmd2 = [
            sys.executable,
            "-m",
            "tab.rolagem_cursor",
            str(pasta / "saltos.json"),
            str(MAO[grupo]),
            str(pasta / "metodo.json"),
        ]
        subprocess.run(cmd2, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
