#!/bin/sh
# R4c (rodada 0204): 15 treinos --ataque com o gerador G8-G10 (_atqc), medida. Para no 1º erro.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
P=/var/home/gabriel/Projects/chorinho-dataset
cd $P
L=data/saida/tab_rotulo/r4c
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
T="python /app/data/saida/n4/treinar_ft.py --passos 3000"
while docker ps --no-trunc --format "{{.Command}}" | grep -q treinar_ft; do sleep 30; done
# a GPU é dividida com outras trilhas: espera a trava alheia e memória livre (>= 3 GB)
while [ -f data/saida/gpu.lock ] && ! grep -q "^tablatura" data/saida/gpu.lock; do
  echo "$(date '+%T') espera trava: $(cat data/saida/gpu.lock)"; sleep 120; done
livre() { nvidia-smi --query-gpu=memory.total,memory.used --format=csv,noheader,nounits | awk -F', ' '{print $1-$2}'; }
espera_memoria() { while [ "$(livre)" -lt 3000 ]; do echo "$(date '+%T') espera memoria: $(livre) MiB livres"; sleep 120; done; }
echo "tablatura, $(date '+%F %T'), ~8 h (R4c: 15 treinos + medida)" > data/saida/gpu.lock
falha() { echo "FALHOU $1 (ver $L/$1.log)"; rm -f data/saida/gpu.lock; exit 1; }
treinar() {
  if [ -f "$2" ]; then echo "ja existe $3"; return; fi
  espera_memoria
  $CP $T $1 > $L/$3.log 2>&1 || falha $3
  grep -q "^gravado" $L/$3.log && [ -f "$2" ] || falha $3
  echo "$(date '+%T') ok $3 | $(grep '^passo 3000' $L/$3.log)"
}
atqc() { if [ $1 = 0 ]; then echo artefatos/detector_tab_final_atqc_s$2/modelo.pt; else echo artefatos/detector_tab_v3ft_d$1_atqc_s$2/modelo.pt; fi; }
med() { $CP python -m tab.ataque_r4 medir --versao atqc --semente $1 > $L/medida_atqc_s$1.log 2>&1 || falha medida_atqc_s$1; echo "$(date '+%T') medida atqc s$1 | $(grep ' t82 ' $L/medida_atqc_s$1.log)"; }
for s in 1 2 3; do
  for d in 4 1 2 3 0; do treinar "--dobra $d --semente $s --ataque --nome _atqc_s$s" $(atqc $d $s) treino_atqc_d${d}_s$s; done
  med $s
done
rm -f data/saida/gpu.lock
echo fim
