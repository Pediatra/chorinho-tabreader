#!/bin/sh
# v2 (regressão) e v3 no MVP; v2 e v3 nos 3 vídeos sem marcador. Dentro do container (cwd /app).
cd /app || exit 1
S=data/saida/audio/a2/v3/saidas
V="/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
python -m tab.audio_alinhar --produto data/saida/conserto_v2/mvp.json --video "$V" --saida $S/mvp_v2_repro.json --metodo onsets | tail -1
python -m tab.audio_alinhar --produto data/saida/conserto_v2/mvp.json --video "$V" --saida $S/mvp_v3.json --metodo onsets_v3 | tail -2
python -m tab.audio_alinhar_avaliar --alinhado $S/mvp_v3.json --regua data/saida/audio/a1/atraso_mvp.json --saida $S/avaliacao_mvp_v3.json > $S/avaliacao_mvp_v3.txt
python -m tab.audio_alinhar_avaliar --alinhado data/saida/audio/a2/alinhado_v2_r1.json --regua data/saida/audio/a1/atraso_mvp.json --saida $S/avaliacao_mvp_v2.json > $S/avaliacao_mvp_v2.txt
P=data/saida/audio/a2/produtos
run() {
  nome="$1"; video="$2"
  python -m tab.audio_alinhar --produto "$P/$nome.json" --video "$video" --saida $S/${nome}_v2.json --metodo onsets | tail -1
  python -m tab.audio_alinhar --produto "$P/$nome.json" --video "$video" --saida $S/${nome}_v3.json --metodo onsets_v3 | tail -2
}
run iwaki_la_vie_en_rose "/acervo/iwaki/la vie en rose - edith piaf ｜ tab.mp4"
run shin_izumi_room_335 "/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4"
run kimny_from_this_place "/acervo/kimny's guitar/[ tab ] from this place - pat metheny ｜ fingerstyle guitar cover.mp4"
echo FIM
