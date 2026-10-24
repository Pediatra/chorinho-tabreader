#!/bin/sh
# 0218: 15 treinos _atqx (receita do _atqs + G17 no gerador + --x-dono), as medidas nos
# ouros (ataque e casa pelo r4; X pela dobra 4) e a decisão contra o _atqs. A T8.6 não é
# medida aqui: espera r6/t86_x_liberada.json (medir_x.py t86, uma vez só).
# A GPU é pega e solta por tab.comum.gpu.trava_gpu dentro de cada treino e medida.
# As medidas leem o HD: precisam acabar antes das 22:00 (lote da 0217) ou esperar o FIM dele.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
L=data/saida/tablatura/tab_rotulo/r6
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/tablatura/n4/treinar_ft.py --passos 3000 --ataque --t82 --recorte-alto --t83-toda --t84 --t85 --x-dono"
falha() { echo "$(date '+%T') FALHOU $1 (ver $L/$1.log)"; exit 1; }
for d in 0 1 2 3 4; do for s in 1 2 3; do
  n=treino_atqx_d${d}_s$s
  if [ $d = 0 ]; then a=artefatos/detector_tab_final_atqx_s$s; else a=artefatos/detector_tab_v3ft_d${d}_atqx_s$s; fi
  if [ -f $a/modelo.pt ]; then echo "ja existe $n"; continue; fi
  $CP $T --dobra $d --semente $s --nome _atqx_s$s > $L/$n.log 2>&1 || falha $n
  grep -q "^gravado" $L/$n.log || falha $n
  echo "$(date '+%T') ok $n | $(grep '^passo 3000' $L/$n.log)"
done; done
for s in 1 2 3; do
  $CP python -m tab.ataque_r4 medir --versao atqx --semente $s --recorte alto > $L/medida_atqx_s${s}_alto.log 2>&1 || falha medida_atqx_s${s}_alto
  echo "$(date '+%T') ok medida atqx s$s"
done
$CP env PYTHONPATH=/app python /app/$L/medir_x.py ouros > $L/medida_x_ouros.log 2>&1 || falha medida_x_ouros
$CP env PYTHONPATH=/app python /app/$L/decidir.py > $L/decidir.log 2>&1 || falha decidir
cat $L/decidir.log
echo "$(date '+%T') fim"
