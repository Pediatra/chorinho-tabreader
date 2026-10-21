#!/bin/sh
# v1 (onsets_v1, registrado) e v2 (onsets, duas rodadas). Dentro do container (cwd /app).
cd /app || exit 1
V="/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
P=data/saida/conserto_v2/mvp.json
R=data/saida/audio/a1/atraso_mvp.json
O=data/saida/audio/a2
python -m tab.audio_alinhar --produto "$P" --video "$V" --saida "$O/alinhado_v1.json" --metodo onsets_v1 | tail -2
python -m tab.audio_alinhar_avaliar --alinhado "$O/alinhado_v1.json" --regua "$R" --saida "$O/avaliacao_v1.json" > "$O/avaliacao_v1.txt"
for rep in 1 2; do
  python -m tab.audio_alinhar --produto "$P" --video "$V" --saida "$O/alinhado_v2_r${rep}.json" --metodo onsets | tail -2
done
sha256sum "$O/alinhado_v2_r1.json" "$O/alinhado_v2_r2.json"
python -m tab.audio_alinhar_avaliar --alinhado "$O/alinhado_v2_r1.json" --regua "$R" --saida "$O/avaliacao_v2.json" > "$O/avaliacao_v2.txt"
cat "$O/avaliacao_v1.txt"
echo ======
cat "$O/avaliacao_v2.txt"
