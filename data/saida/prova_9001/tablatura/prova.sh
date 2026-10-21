#!/bin/sh
# Prova de antes da trilha tablatura (decisao 9001).
# Uso (dentro do container): sh /app/data/saida/prova_9001/tablatura/prova.sh <pasta_de_saida>
# Comandos pelos nomes antigos (python -m tab.<nome>); CUDA_VISIBLE_DEVICES vazio = so CPU.
set -e

if [ -z "$1" ]; then
    echo "uso: prova.sh <pasta_de_saida>" >&2
    exit 2
fi
OUT="$1"
mkdir -p "$OUT"
cd /app

# a. produto do greensleeves: caminho do video vem do ouro (NFC na comparacao de nome)
VIDEO=$(python - <<'PY'
import json
import os
import unicodedata

ouro = "data/gold/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf.json"
with open(ouro, encoding="utf-8") as f:
    video = json.load(f)["video"]
caminho = os.path.join("/acervo", video)
if not os.path.exists(caminho):
    pasta, nome = os.path.split(caminho)
    alvo = unicodedata.normalize("NFC", nome)
    for n in os.listdir(pasta):
        if unicodedata.normalize("NFC", n) == alvo:
            caminho = os.path.join(pasta, n)
            break
print(caminho)
PY
)
echo "video: $VIDEO"
python -m tab.video "$VIDEO" --json "$OUT/produto_greensleeves.json" > "$OUT/produto_greensleeves.txt"

# b. medida nos ouros. Sao 8: sai retrato_brasileiro.json (v1, substituida pela v2).
#    Predicao: fase8/ger/ger/<slug>.json; se nao existir, fase8/rede/<slug>.json.
: > "$OUT/ouros_status.txt"
for ouro in data/gold/ouro_video/*.json; do
    slug=$(basename "$ouro" .json)
    if [ "$slug" = "retrato_brasileiro" ]; then
        echo "EXCLUIDO $slug (substituido por retrato_brasileiro_v2)" >> "$OUT/ouros_status.txt"
        continue
    fi
    if [ -f "data/saida/fase8/ger/ger/$slug.json" ]; then
        pred="data/saida/fase8/ger/ger/$slug.json"
        origem="fase8/ger/ger"
    elif [ -f "data/saida/fase8/rede/$slug.json" ]; then
        pred="data/saida/fase8/rede/$slug.json"
        origem="fase8/rede"
    else
        echo "SEM_PRODUTO $slug" >> "$OUT/ouros_status.txt"
        continue
    fi
    echo "COM_PRODUTO $slug pred=$origem" >> "$OUT/ouros_status.txt"
    python -m tab.avaliar_video --ouro "$ouro" --pred "$pred" \
        --json "$OUT/avaliar_$slug.json" > "$OUT/avaliar_$slug.txt"
done
echo "concluido: $OUT"
