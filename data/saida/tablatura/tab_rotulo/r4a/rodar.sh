#!/bin/sh
# R4a (rodada 0202). Para no primeiro erro. Ordem: primeiro sinal cedo (dobra 4, semente 1),
# depois a semente 1 inteira medida, depois sementes 2 e 3.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
cd $P
L=data/saida/tab_rotulo/r4a
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/n4/treinar_ft.py --passos 3000"
while docker ps --no-trunc --format "{{.Command}}" | grep -q treinar_ft; do sleep 30; done
echo "tablatura, $(date '+%F %T'), ~8 h (R4a: treinos + medida)" > data/saida/gpu.lock
falha() { echo "FALHOU $1 (ver $L/$1.log)"; rm -f data/saida/gpu.lock; exit 1; }
treinar() {
  if [ -f "$2" ]; then echo "ja existe $3"; return; fi
  $CP $T $1 > $L/$3.log 2>&1 || falha $3
  grep -q "^gravado" $L/$3.log && [ -f "$2" ] || falha $3
  echo "$(date '+%T') ok $3 | $(grep '^passo 3000' $L/$3.log)"
}
ger() { if [ $1 = 0 ]; then echo artefatos/detector_tab_final_s$2_ger/modelo.pt; elif [ $2 = 1 ]; then echo artefatos/detector_tab_v3ft_d$1_ger/modelo.pt; else echo artefatos/detector_tab_v3ft_d$1_ger_s$2/modelo.pt; fi; }
atq() { if [ $1 = 0 ]; then echo artefatos/detector_tab_final_atq_s$2/modelo.pt; else echo artefatos/detector_tab_v3ft_d$1_atq_s$2/modelo.pt; fi; }
med() { $CP python -m tab.ataque_r4 medir --versao $1 --semente $2 > $L/medida_$1_s$2.log 2>&1 || falha medida_$1_s$2; echo "$(date '+%T') medida $1 s$2 | $(grep -E ' t82 | south_american ' $L/medida_$1_s$2.log | tr '\n' ' ')"; }
treinar "--dobra 1 --semente 3 --nome _ger_s3" $(ger 1 3) treino_ger_d1_s3
treinar "--dobra 4 --semente 1 --ataque --nome _atq_s1" $(atq 4 1) treino_atq_d4_s1
for v in ger atq; do $CP env PYTHONPATH=/app python /app/$L/rapida.py $v 1 2>&1 | grep '^rapida' || falha rapida_$v; done
for d in 1 2 3 0; do treinar "--dobra $d --semente 1 --ataque --nome _atq_s1" $(atq $d 1) treino_atq_d${d}_s1; done
med ger 1; med atq 1
for s in 2 3; do treinar "--dobra 0 --semente $s --nome _s${s}_ger" $(ger 0 $s) treino_ger_d0_s$s; done
for s in 2 3; do for d in 4 1 2 3 0; do treinar "--dobra $d --semente $s --ataque --nome _atq_s$s" $(atq $d $s) treino_atq_d${d}_s$s; done; done
for s in 2 3; do med ger $s; med atq $s; done
rm -f data/saida/gpu.lock
echo fim
