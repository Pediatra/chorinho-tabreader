#!/bin/sh
# Passo 4 (audio_produto v2.1): 14 pares; saídas NOVAS v21_<apelido>.audio.json.
P=data/saida/audio/a4/rasgueado/pod.sh
LOG=data/saida/audio/a4/rasgueado/audio_v21.log
: > $LOG
run() { echo "== $1" >> $LOG; $P python -m tab.audio_produto --produto "$2" --alinhado "$3" --saida "$4" >> $LOG 2>&1; echo "RC=$?" >> $LOG; }
run mvp data/saida/conserto_v2/mvp.json data/saida/audio/a2/alinhado_v21_mvp.json data/saida/audio/a5/v21_mvp.audio.json
run iwaki_la_vie_en_rose data/saida/audio/a2/produtos/iwaki_la_vie_en_rose.json data/saida/audio/a2/produtos/alinhado_v21_iwaki_la_vie_en_rose.json data/saida/audio/a5/v21_iwaki_la_vie_en_rose.audio.json
run kimny_from_this_place data/saida/audio/a2/produtos/kimny_from_this_place.json data/saida/audio/a2/produtos/alinhado_v21_kimny_from_this_place.json data/saida/audio/a5/v21_kimny_from_this_place.audio.json
run shin_izumi_room_335 data/saida/audio/a2/produtos/shin_izumi_room_335.json data/saida/audio/a2/produtos/alinhado_v21_shin_izumi_room_335.json data/saida/audio/a5/v21_shin_izumi_room_335.audio.json
run iwaki_michelle data/saida/audio/a4/lote1/iwaki_michelle.json data/saida/audio/a4/lote1/alinhado_v21_iwaki_michelle.json data/saida/audio/a4/lote1/v21_iwaki_michelle.audio.json
run iwaki_fly_me_to_the_moon data/saida/audio/a4/lote1/iwaki_fly_me_to_the_moon.json data/saida/audio/a4/lote1/alinhado_v21_iwaki_fly_me_to_the_moon.json data/saida/audio/a4/lote1/v21_iwaki_fly_me_to_the_moon.audio.json
run kimny_gunjo data/saida/audio/a4/lote1/kimny_gunjo.json data/saida/audio/a4/lote1/alinhado_v21_kimny_gunjo.json data/saida/audio/a4/lote1/v21_kimny_gunjo.audio.json
run kimny_bach_prelude data/saida/audio/a4/lote1/kimny_bach_prelude.json data/saida/audio/a4/lote1/alinhado_v21_kimny_bach_prelude.json data/saida/audio/a4/lote1/v21_kimny_bach_prelude.audio.json
run shin_izumi_giant_steps data/saida/audio/a4/lote1/shin_izumi_giant_steps.json data/saida/audio/a4/lote1/alinhado_v21_shin_izumi_giant_steps.json data/saida/audio/a4/lote1/v21_shin_izumi_giant_steps.audio.json
run transcriptor_charagua data/saida/audio/a4/lote1/transcriptor_charagua.json data/saida/audio/a4/lote1/alinhado_v21_transcriptor_charagua.json data/saida/audio/a4/lote1/v21_transcriptor_charagua.audio.json
run transcriptor_campanitas data/saida/audio/a4/lote1/transcriptor_campanitas.json data/saida/audio/a4/lote1/alinhado_v21_transcriptor_campanitas.json data/saida/audio/a4/lote1/v21_transcriptor_campanitas.audio.json
run guitarous_sakura data/saida/audio/a4/lote1/guitarous_sakura.json data/saida/audio/a4/lote1/alinhado_v21_guitarous_sakura.json data/saida/audio/a4/lote1/v21_guitarous_sakura.audio.json
run shin_izumi_dream_wish data/saida/audio/a4/lote1/shin_izumi_dream_wish.json data/saida/audio/a4/lote1/alinhado_v21_shin_izumi_dream_wish.json data/saida/audio/a4/lote1/v21_shin_izumi_dream_wish.audio.json
run paolo_those_who_wait data/saida/audio/a4/lote1/paolo_those_who_wait.json data/saida/audio/a4/lote1/alinhado_v21_paolo_those_who_wait.json data/saida/audio/a4/lote1/v21_paolo_those_who_wait.audio.json
echo FIM >> $LOG
