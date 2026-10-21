#!/bin/bash
# Roda o alinhador da trilha do audio nos 4 videos da M7 (saidas em data/saida/maos/m7/audio/).
set -u
cd /app
A=/acervo/sky\ guitar
D=data/saida/maos/m7/audio
python -m tab.audio_alinhar --produto data/saida/produto/mvp.json --video "$A/retrato brasileiro - tab & lesson.mp4" --saida $D/alinhado_retrato_brasileiro.json
python -m tab.audio_alinhar --produto data/saida/maos/m3d/q16_chopin_nocturne20.json --video "$A/(chopin) nocturne no.20 - tab & lesson.mp4" --saida $D/alinhado_chopin_nocturne20.json
python -m tab.audio_alinhar --produto data/saida/maos/m3d/sky_4.json --video "$A/lacrimosa (requiem k.626) - guitar lesson + tab.mp4" --saida $D/alinhado_lacrimosa.json
python -m tab.audio_alinhar --produto data/saida/maos/m3d/sky_8.json --video "$A/glimpse of us (joji) - fingerstyle lesson + tab.mp4" --saida $D/alinhado_glimpse_of_us.json
echo FIM
