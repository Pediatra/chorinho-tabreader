#!/bin/sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
R=data/saida/ouro_video/_regen_2026-10-13
DC="env DOCKER_HOST=unix:///run/user/1000/podman/podman.sock docker compose -f compose.yaml -f compose.podman.yaml run --rm chorinho"
ACERVO=/acervo

for s in end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics la_vie_en_rose_edith_piaf_tab tab_from_this_place_pat_metheny_fingerstyle_guitar_cover tabroom_335_larry_carlton_fingerstyle_guitar; do
  rm -f "data/gold/ouro_video/$s.json"
  if [ -e "data/saida/ouro_video/$s" ]; then
    rm -rf "data/saida/ouro_video/$s" 2>/dev/null || $DC rm -rf "/app/data/saida/ouro_video/$s"
  fi
  echo "removido $s: gold=$(test -e data/gold/ouro_video/$s.json && echo existe || echo ok) saida=$(test -e data/saida/ouro_video/$s && echo existe || echo ok)"
done

echo "== 1 kenneth"
$DC python -m tab.ouro_video completar "$ACERVO/kenneth acoustic/end of beginning - djo ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4" --ouro-v2 data/gold/ouro_video/end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics.json --saida data/saida/ouro_video/end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics --modelo artefatos/serif3_2/glifo_sint.pt --faixa 820 1080 > "$R/end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics.log" 2>&1
echo "exit=$?"

echo "== 2 la vie en rose"
$DC python -m tab.ouro_video completar "$ACERVO/iwaki/la vie en rose - edith piaf ｜ tab.mp4" --ouro-v2 data/gold/ouro_video/la_vie_en_rose_edith_piaf_tab.json --saida data/saida/ouro_video/la_vie_en_rose_edith_piaf_tab --modelo artefatos/serif3_2/glifo_sint.pt > "$R/la_vie_en_rose_edith_piaf_tab.log" 2>&1
echo "exit=$?"

echo "== 3 from this place"
$DC python -m tab.ouro_video completar "$ACERVO/kimny's guitar/[ tab ] from this place - pat metheny ｜ fingerstyle guitar cover.mp4" --ouro-v2 data/gold/ouro_video/tab_from_this_place_pat_metheny_fingerstyle_guitar_cover.json --saida data/saida/ouro_video/tab_from_this_place_pat_metheny_fingerstyle_guitar_cover --modelo artefatos/serif3_2/glifo_sint.pt > "$R/tab_from_this_place_pat_metheny_fingerstyle_guitar_cover.log" 2>&1
echo "exit=$?"

echo "== 4 room 335"
$DC python -m tab.ouro_video completar "$ACERVO/shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4" --ouro-v2 data/gold/ouro_video/tabroom_335_larry_carlton_fingerstyle_guitar.json --saida data/saida/ouro_video/tabroom_335_larry_carlton_fingerstyle_guitar --modelo artefatos/serif3_2/glifo_sint.pt > "$R/tabroom_335_larry_carlton_fingerstyle_guitar.log" 2>&1
echo "exit=$?"
echo RUN_DONE
