#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho sh -c '
python -c "
import json
from pathlib import Path
p = json.loads(Path(\"data/saida/audio/a2/produtos/kimny_from_this_place.json\").read_text())
video = \"/acervo/\" + p[\"video\"][\"arquivo\"]
itens = []
for t in p[\"telas\"]:
    for c in sorted({n[\"coluna\"] for n in p[\"notas\"] if n[\"tela\"] == t[\"id\"]}):
        itens.append({\"video\": video, \"tela\": t[\"id\"], \"exibicao\": t[\"id\"] % 2, \"coluna\": c, \"t_audio\": 5.0 + t[\"id\"] * 3 + c * 0.1, \"confianca\": 0.5})
Path(\"/tmp/itens_fumaca.json\").write_text(json.dumps({\"itens\": itens}))
print(\"itens\", len(itens))
" && python -m tab.audio_folha sortear --alinhados /tmp/itens_fumaca.json --por-video 6 --semente 3 --saida /tmp/pedidos_fumaca.json && python -c "
import json
for p in json.load(open(\"/tmp/pedidos_fumaca.json\")): print(p[\"id\"], p[\"tela\"], p[\"coluna\"], p[\"exibicao\"], p[\"x_centro_quadro\"], p[\"passo\"], p[\"notas\"])
"'
