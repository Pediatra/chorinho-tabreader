#!/bin/bash
# CA1 (rodada 0101, reprodução após o merge de main de 2026-10-16).
# Roda dentro do container, a partir de /app (worktree tab/f0-regua-tecnica).
set -u
cd /app || exit 1
F=/app/data/saida/tab_frentes/f0_tecnica
mkdir -p "$F/ca1_dobras_v2"

echo "== T8.2 (final_s1_ger e antigo)"
python "$F/ca1/t82_comparar.py" 2>&1 | grep -v Warning

echo "== dobras (avaliar_video, leituras gravadas)"
for s in end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics \
         greensleeves_guia_de_estudio_partitura_tab_pdf \
         gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar \
         south_american_music_easy_guitar_tutorial_with_sheet_and_tab \
         tab_from_this_place_pat_metheny_fingerstyle_guitar_cover \
         tabroom_335_larry_carlton_fingerstyle_guitar; do
    python -m tab.avaliar_video --ouro "data/gold/ouro_video/$s.json" \
        --pred "data/saida/fase8/ger/ger/$s.json" \
        --json "$F/ca1_dobras_v2/$s.json" > "$F/ca1_dobras_v2/$s.txt" 2>&1
    echo "exit $? $s"
done
python "$F/ca1/ca1_somar.py"
