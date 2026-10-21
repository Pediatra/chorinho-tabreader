"""Passo 3: extrai um quadro no meio de cada exibição escolhida e recorta o painel.

Roda DENTRO do container (precisa de ffmpeg). Só lê o vídeo (somente leitura).
Para cada tela: PNG do painel (2x, Lanczos, para leitura) e um TXT com as colunas do
produto ordenadas por x_centro_quadro, com corda/casa.
"""

import json
import os
import subprocess
import sys

VIDEO = (
    "/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar "
    "ソロギター【タブ】.mp4"
)
PRODUTO = "/app/data/saida/audio/a2/produtos/shin_izumi_room_335.json"
SAIDA = "/app/data/saida/audio/a4/shin/quadros"

# (tela, motivo) — recusadas com mais casa > 7; aceitas com mais casa > 7 para comparação.
TELAS = [
    (16, "recusada"),
    (12, "recusada"),
    (17, "recusada"),
    (25, "recusada"),
    (41, "aceita"),
    (20, "aceita"),
]


def main() -> int:
    os.makedirs(SAIDA, exist_ok=True)
    with open(PRODUTO, encoding="utf-8") as f:
        prod = json.load(f)
    telas = {int(t["id"]): t for t in prod["telas"]}
    notas_por_tela: dict[int, list[dict]] = {}
    for n in prod["notas"]:
        notas_por_tela.setdefault(int(n["tela"]), []).append(n)

    for tela_id, situacao in TELAS:
        tela = telas[tela_id]
        ex = tela["exibicoes"][0]
        meio = (float(ex["t0"]) + float(ex["t1"])) / 2.0
        x0, y0, x1, y1 = (int(v) for v in tela["painel"])
        w, h = x1 - x0, y1 - y0
        base = f"tela{tela_id:02d}_{situacao}_t{meio:.2f}"
        png = f"{SAIDA}/{base}.png"
        filtro = f"crop={w}:{h}:{x0}:{y0},scale={w * 2}:{h * 2}:flags=lanczos"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                f"{meio:.3f}",
                "-i",
                VIDEO,
                "-frames:v",
                "1",
                "-vf",
                filtro,
                png,
            ],
            check=True,
        )
        # Colunas do produto, ordenadas pela posição horizontal média.
        por_coluna: dict[int, dict] = {}
        for n in notas_por_tela.get(tela_id, []):
            c = por_coluna.setdefault(
                int(n["coluna"]), {"xs": [], "notas": []}
            )
            c["xs"].append(float(n["x_centro_quadro"]))
            c["notas"].append((int(n["corda"]), int(n["casa"])))
        linhas = [
            f"tela {tela_id} ({situacao}) exibicao t0={ex['t0']} t1={ex['t1']} "
            f"quadro em t={meio:.2f} painel={[x0, y0, x1, y1]}",
            "coluna\tx_centro_medio\tnotas (corda,casa)",
        ]
        for coluna, c in sorted(
            por_coluna.items(), key=lambda kv: sum(kv[1]["xs"]) / len(kv[1]["xs"])
        ):
            xm = sum(c["xs"]) / len(c["xs"])
            pares = " ".join(f"({a},{b})" for a, b in sorted(c["notas"]))
            linhas.append(f"{coluna}\t{xm:.1f}\t{pares}")
        with open(f"{SAIDA}/{base}_colunas.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
        print(f"ok {png} colunas={len(por_coluna)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
