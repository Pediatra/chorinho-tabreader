#!/bin/sh
# Diagnostico da rodada p1 (variantes): roda o Audiveris nas condicoes novas, uma por vez.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
for c in x3 x4 x2_binaria x2_margem x2_cabecalho; do
  podman run --rm --security-opt label=disable -v "$PWD:/app" -w /app chorinho-partitura:dev \
    python -m tab.partitura_omr rodar --biblioteca audiveris --condicao "$c" \
    --ids R01,R02,R03,R04,R05,R06,R07,R08,R09,R10,R11,R12 \
    > "data/saida/partitura/p1/variantes/log_audiveris_$c.txt" 2>&1
  echo "fim $c $?" >> data/saida/partitura/p1/variantes/progresso.txt
done
echo tudo >> data/saida/partitura/p1/variantes/progresso.txt
