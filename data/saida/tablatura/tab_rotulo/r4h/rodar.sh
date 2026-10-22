#!/bin/sh
# 0214: 15 treinos _atqb (G13–G15, T8.3 inteira e T8.4 no treino), medidas nos ouros,
# decisão e, se o _atqb passar nos ouros, a T8.5 uma vez (depois o _atqa, só informado).
# A GPU é pega e solta por tab.comum.gpu.trava_gpu dentro de cada treino e medida.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
L=data/saida/tablatura/tab_rotulo/r4h
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/tablatura/n4/treinar_ft.py --passos 3000 --ataque --t82 --recorte-alto --t83-toda --t84"
falha() { echo "$(date '+%T') FALHOU $1 (ver $L/$1.log)"; exit 1; }
for d in 0 1 2 3 4; do for s in 1 2 3; do
  n=treino_atqb_d${d}_s$s
  if [ $d = 0 ]; then a=artefatos/detector_tab_final_atqb_s$s; else a=artefatos/detector_tab_v3ft_d${d}_atqb_s$s; fi
  if [ -f $a/modelo.pt ]; then echo "ja existe $n"; continue; fi
  $CP $T --dobra $d --semente $s --nome _atqb_s$s > $L/$n.log 2>&1 || falha $n
  grep -q "^gravado" $L/$n.log || falha $n
  echo "$(date '+%T') ok $n | $(grep '^passo 3000' $L/$n.log)"
done; done
for s in 1 2 3; do
  $CP python -m tab.ataque_r4 medir --versao atqb --semente $s --recorte alto > $L/medida_atqb_s${s}_alto.log 2>&1 || falha medida_atqb_s${s}_alto
  echo "$(date '+%T') ok medida atqb s$s"
done
$CP env PYTHONPATH=/app python /app/$L/decidir.py > $L/decidir.log 2>&1 || falha decidir
cat $L/decidir.log
if grep -q "atqb passa nos ouros: True" $L/decidir.log; then
  $CP env PYTHONPATH=/app python /app/$L/medir_t85.py atqb > $L/medida_t85_atqb.log 2>&1 || falha medida_t85_atqb
  cat $L/medida_t85_atqb.log
  $CP env PYTHONPATH=/app python /app/$L/medir_t85.py atqa > $L/medida_t85_atqa.log 2>&1 || falha medida_t85_atqa
  cat $L/medida_t85_atqa.log
fi
echo "$(date '+%T') fim"
