#!/bin/sh
set -eu
cd /var/home/gabriel/Projects/chorinho-dataset
B=data/saida/ouro_video/_backup_2026-10-13
mkdir -p "$B"
for s in end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics la_vie_en_rose_edith_piaf_tab tab_from_this_place_pat_metheny_fingerstyle_guitar_cover tabroom_335_larry_carlton_fingerstyle_guitar; do
  cp -a "data/gold/ouro_video/$s.json" "$B/$s.json"
  cmp "data/gold/ouro_video/$s.json" "$B/$s.json"
  cp -a "data/saida/ouro_video/$s" "$B/$s"
  (cd "data/saida/ouro_video/$s" && find . -type f | sort | while read f; do cmp "$f" "../../../../$B/$s/$f" || echo "DIFF $s/$f"; done)
  echo "backup OK $s: $(find "$B/$s" -type f | wc -l) arquivos"
done
echo BACKUP_DONE
