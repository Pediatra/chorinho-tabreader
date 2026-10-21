#!/bin/sh
# Alinha o MVP pelos dois métodos, duas vezes cada (determinismo), e avalia contra a régua.
# Roda DENTRO do container (cwd /app).
cd /app || exit 1
V="/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
P=data/saida/conserto_v2/mvp.json
R=data/saida/audio/a1/atraso_mvp.json
O=data/saida/audio/a2
for m in onsets dtw; do
  for rep in 1 2; do
    echo "== alinhar $m rep $rep ($(date +%T))"
    python -m tab.audio_alinhar --produto "$P" --video "$V" --saida "$O/alinhado_${m}_r${rep}.json" --metodo $m 2>&1 | tail -5
    echo "fim $(date +%T)"
  done
  sha256sum "$O/alinhado_${m}_r1.json" "$O/alinhado_${m}_r2.json"
  echo "== avaliar $m"
  python -m tab.audio_alinhar_avaliar --alinhado "$O/alinhado_${m}_r1.json" --regua "$R" --saida "$O/avaliacao_${m}.json"
done
