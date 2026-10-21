#!/bin/bash
# Depois da 1037: previsão da 1039 (pesos pela 1037) e, se a 1037 passou, a 1038.
cd /var/home/gabriel/Projects/chorinho-dataset
LOG=data/saida/maos/m37/logs
ETAPAS=$LOG/etapas.txt
until grep -q "fim medir\|fim escolher código [1-9]\|fim smoke código [1-9]" "$ETAPAS" 2>/dev/null; do sleep 60; done
grep -q "fim medir código 0" "$ETAPAS" || { echo "$(date '+%F %T') 1037 não mediu; fila 2 parada" >> "$ETAPAS"; exit 1; }
rodar() {
  local nome=$1; shift
  echo "$(date '+%F %T') início $nome" >> "$ETAPAS"
  podman run --rm --security-opt label=disable --device nvidia.com/gpu=all \
    -v "$PWD":/app -w /app -e PYTHONPATH=/app \
    localhost/chorinho-maos:dev "$@" > "$LOG/$nome.log" 2>&1
  local codigo=$?
  echo "$(date '+%F %T') fim $nome código $codigo" >> "$ETAPAS"
  return $codigo
}
rodar prever_1039 python -m tab.maos_braco_ciclo prever --rodada 1039
passou=$(python3 -c "import json; c=json.load(open('data/saida/maos/m37/medida.json'))['criterios']; print(int(c['seguranca'] and c['capo'] and c['sem_capo']))")
if [ "$passou" = "1" ]; then
  rodar capo_prever python -m tab.maos_braco_capo_imagem prever && rodar capo_medir python -m tab.maos_braco_capo_imagem medir
else
  echo "$(date '+%F %T') 1037 não passou: 1038 não roda (pré-registro)" >> "$ETAPAS"
fi
