#!/bin/sh
# 0211 fase 2: 15 treinos _atqa (recorte alto, G11-G12 ligados) e as medidas da fase 1.
# A GPU é pega e solta por tab.gpu.trava_gpu dentro de cada treino e de cada medida.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
L=data/saida/tab_rotulo/r4g
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/n4/treinar_ft.py --passos 3000 --ataque --t82 --recorte-alto"
falha() { echo "$(date '+%T') FALHOU $1 (ver $L/$1.log)"; exit 1; }
for d in 4 1 2 3 0; do for s in 1 2 3; do
  n=treino_atqa_d${d}_s$s
  if [ $d = 0 ]; then a=artefatos/detector_tab_final_atqa_s$s; else a=artefatos/detector_tab_v3ft_d${d}_atqa_s$s; fi
  if [ -f $a/modelo.pt ]; then echo "ja existe $n"; continue; fi
  $CP $T --dobra $d --semente $s --nome _atqa_s$s > $L/$n.log 2>&1 || falha $n
  grep -q "^gravado" $L/$n.log || falha $n
  echo "$(date '+%T') ok $n | $(grep '^passo 3000' $L/$n.log)"
done; done
for s in 1 2 3; do
  $CP python -m tab.ataque_r4 medir --versao atqa --semente $s --recorte alto > $L/medida_atqa_s${s}_alto.log 2>&1 || falha medida_atqa_s${s}_alto
  echo "$(date '+%T') ok medida atqa s$s"
done
$CP env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4c/medir_t83.py atqa alto > $L/medida_t83_atqa.log 2>&1 || falha medida_t83_atqa
echo "$(date '+%T') fim"
