"""Grade de medicao: qps e estabilidade por argv (so medicao)."""

import sys

sys.path.insert(0, "/app")

from tab import video as V  # noqa: E402

VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
qps, est, saida = float(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
V.QPS_EXIBICAO = qps
V.ESTAVEL_EXIBICAO = est
dados = V.transcrever_video(VIDEO)
import json  # noqa: E402

json.dump(dados, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("qps", qps, "estavel", est, "notas", dados["resumo"]["notas"], "invariantes", V.validar_tempo(dados)[:3])
