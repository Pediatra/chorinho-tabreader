#!/bin/bash
# Pontas da mão (t_ini das notas presas) nos vídeos da confirmação M9, em CPU.
set -e
cd /app
for i in 1 2 3 5 6; do
  arq=$(python -c "import json;print(json.load(open('data/saida/maos/m3d/sky_$i.json'))['video']['arquivo'])")
  python -m tab.maos_pontas_notas --dispositivo cpu --video "/acervo/$arq" \
    --mvp data/saida/maos/m3d/sky_$i.json --saida data/saida/maos/m9/pontas_sky_$i.json
done
