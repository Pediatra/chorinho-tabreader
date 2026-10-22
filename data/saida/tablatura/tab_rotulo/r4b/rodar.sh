#!/bin/sh
# R4b (rodada 0203): 15 treinos --ataque com o gerador novo (_atqg), medida. Para no 1º erro.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
cd $P
L=data/saida/tab_rotulo/r4b
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/n4/treinar_ft.py --passos 3000"
while docker ps --no-trunc --format "{{.Command}}" | grep -q treinar_ft; do sleep 30; done
echo "tablatura, $(date '+%F %T'), ~8 h (R4b: 15 treinos + medida)" > data/saida/gpu.lock
falha() { echo "FALHOU $1 (ver $L/$1.log)"; rm -f data/saida/gpu.lock; exit 1; }
treinar() {
  if [ -f "$2" ]; then echo "ja existe $3"; return; fi
  $CP $T $1 > $L/$3.log 2>&1 || falha $3
  grep -q "^gravado" $L/$3.log && [ -f "$2" ] || falha $3
  echo "$(date '+%T') ok $3 | $(grep '^passo 3000' $L/$3.log)"
}
atqg() { if [ $1 = 0 ]; then echo artefatos/detector_tab_final_atqg_s$2/modelo.pt; else echo artefatos/detector_tab_v3ft_d$1_atqg_s$2/modelo.pt; fi; }
med() { $CP python -m tab.ataque_r4 medir --versao atqg --semente $1 > $L/medida_atqg_s$1.log 2>&1 || falha medida_atqg_s$1; echo "$(date '+%T') medida atqg s$1 | $(grep ' t82 ' $L/medida_atqg_s$1.log)"; }
R="$CP env PYTHONPATH=/app python /app/$L"
treinar "--dobra 0 --semente 1 --ataque --nome _atqg_s1" $(atqg 0 1) treino_atqg_d0_s1
for v in atq atqg; do $R/rapida_t82.py $v 1 2>&1 | grep '^rapida' || falha rapida_t82_$v; done
treinar "--dobra 4 --semente 1 --ataque --nome _atqg_s1" $(atqg 4 1) treino_atqg_d4_s1
for v in atq atqg; do $CP env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4a/rapida.py $v 1 2>&1 | grep '^rapida' || falha rapida_$v; done
for s in 1 2 3; do
  for d in 4 1 2 3 0; do treinar "--dobra $d --semente $s --ataque --nome _atqg_s$s" $(atqg $d $s) treino_atqg_d${d}_s$s; done
  med $s
done
rm -f data/saida/gpu.lock
echo fim
