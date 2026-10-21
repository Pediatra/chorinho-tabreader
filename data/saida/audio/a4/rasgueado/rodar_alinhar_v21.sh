#!/bin/sh
# Passo 4 (alinhador v2.1): 14 produtos; saídas NOVAS alinhado_v21_<apelido>.json.
P=data/saida/audio/a4/rasgueado/pod.sh
LOG=data/saida/audio/a4/rasgueado/alinhar_v21.log
: > $LOG
run() { echo "== $1" >> $LOG; t0=$(date +%s); $P python -m tab.audio_alinhar --produto "$2" --video "$3" --saida "$4" --metodo onsets >> $LOG 2>&1; echo "RC=$? TEMPO_S=$(( $(date +%s) - t0 ))" >> $LOG; }
run mvp data/saida/conserto_v2/mvp.json '/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4' data/saida/audio/a2/alinhado_v21_mvp.json
run iwaki_la_vie_en_rose data/saida/audio/a2/produtos/iwaki_la_vie_en_rose.json '/acervo/iwaki/la vie en rose - edith piaf ｜ tab.mp4' data/saida/audio/a2/produtos/alinhado_v21_iwaki_la_vie_en_rose.json
run kimny_from_this_place data/saida/audio/a2/produtos/kimny_from_this_place.json '/acervo/kimny'"'"'s guitar/[ tab ] from this place - pat metheny ｜ fingerstyle guitar cover.mp4' data/saida/audio/a2/produtos/alinhado_v21_kimny_from_this_place.json
run shin_izumi_room_335 data/saida/audio/a2/produtos/shin_izumi_room_335.json '/acervo/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4' data/saida/audio/a2/produtos/alinhado_v21_shin_izumi_room_335.json
run iwaki_michelle data/saida/audio/a4/lote1/iwaki_michelle.json '/acervo/iwaki/the beatles - michelle｜tab for beginners.mp4' data/saida/audio/a4/lote1/alinhado_v21_iwaki_michelle.json
run iwaki_fly_me_to_the_moon data/saida/audio/a4/lote1/iwaki_fly_me_to_the_moon.json '/acervo/iwaki/fly me to the moon ｜ tab.mp4' data/saida/audio/a4/lote1/alinhado_v21_iwaki_fly_me_to_the_moon.json
run kimny_gunjo data/saida/audio/a4/lote1/kimny_gunjo.json '/acervo/kimny'"'"'s guitar/[tab] 群青（合唱曲）- 小田美樹 ｜ fingerstyle guitar cover.mp4' data/saida/audio/a4/lote1/alinhado_v21_kimny_gunjo.json
run kimny_bach_prelude data/saida/audio/a4/lote1/kimny_bach_prelude.json '/acervo/kimny'"'"'s guitar/[ tab ] bach - prelude (cello suite no.1, bwv1007) ｜ performed by kimny.mp4' data/saida/audio/a4/lote1/alinhado_v21_kimny_bach_prelude.json
run shin_izumi_giant_steps data/saida/audio/a4/lote1/shin_izumi_giant_steps.json '/acervo/shin izumi/【tab】giant steps - john coltrane - fingerstyle guitar ソロギター【タブ】.mp4' data/saida/audio/a4/lote1/alinhado_v21_shin_izumi_giant_steps.json
run transcriptor_charagua data/saida/audio/a4/lote1/transcriptor_charagua.json '/acervo/transcriptor/charagua - victor jara -  2＊ guitarra - partitura ⧸ tablatura..mp4' data/saida/audio/a4/lote1/alinhado_v21_transcriptor_charagua.json
run transcriptor_campanitas data/saida/audio/a4/lote1/transcriptor_campanitas.json '/acervo/transcriptor/inti illimani - campanitas - ernesto cavour - guitarra - partitura ⧸ tablatura..mp4' data/saida/audio/a4/lote1/alinhado_v21_transcriptor_campanitas.json
run guitarous_sakura data/saida/audio/a4/lote1/guitarous_sakura.json '/acervo/ギタロー ⧸ guitarous/sakuraドロップス ソロギター 初心者向け タブ譜.mp4' data/saida/audio/a4/lote1/alinhado_v21_guitarous_sakura.json
run shin_izumi_dream_wish data/saida/audio/a4/lote1/shin_izumi_dream_wish.json '/acervo/shin izumi/【tab】a dream is a wish your heart makes- cinderella - fingerstyle guitar ソロギター【タブ】.mp4' data/saida/audio/a4/lote1/alinhado_v21_shin_izumi_dream_wish.json
run paolo_those_who_wait data/saida/audio/a4/lote1/paolo_those_who_wait.json '/acervo/paolo d'"'"'angelo/those who wait ｜ tommy emmanuel ｜ guitar tab ｜ fingerstyle tutorial.mp4' data/saida/audio/a4/lote1/alinhado_v21_paolo_those_who_wait.json
echo FIM >> $LOG
