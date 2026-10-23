#!/bin/sh
# 0215: 15 treinos _atqs (receita do _atqr + G16 no gerador + T8.5 no treino), medidas nos
# ouros revisados e a decisão contra o _atqr (medidas de 2026-10-23 em r4a/). A T8.6 não é
# medida aqui: espera a conferência do dono (r5/medir_t86.py, uma vez só).
# A GPU é pega e solta por tab.comum.gpu.trava_gpu dentro de cada treino e medida.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
L=data/saida/tablatura/tab_rotulo/r5
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/tablatura/n4/treinar_ft.py --passos 3000 --ataque --t82 --recorte-alto --t83-toda --t84 --t85"
falha() { echo "$(date '+%T') FALHOU $1 (ver $L/$1.log)"; exit 1; }
for d in 0 1 2 3 4; do for s in 1 2 3; do
  n=treino_atqs_d${d}_s$s
  if [ $d = 0 ]; then a=artefatos/detector_tab_final_atqs_s$s; else a=artefatos/detector_tab_v3ft_d${d}_atqs_s$s; fi
  if [ -f $a/modelo.pt ]; then echo "ja existe $n"; continue; fi
  $CP $T --dobra $d --semente $s --nome _atqs_s$s > $L/$n.log 2>&1 || falha $n
  grep -q "^gravado" $L/$n.log || falha $n
  echo "$(date '+%T') ok $n | $(grep '^passo 3000' $L/$n.log)"
done; done
for s in 1 2 3; do
  $CP python -m tab.ataque_r4 medir --versao atqs --semente $s --recorte alto > $L/medida_atqs_s${s}_alto.log 2>&1 || falha medida_atqs_s${s}_alto
  echo "$(date '+%T') ok medida atqs s$s"
done
$CP env PYTHONPATH=/app python /app/$L/decidir.py > $L/decidir.log 2>&1 || falha decidir
cat $L/decidir.log
echo "$(date '+%T') fim"
