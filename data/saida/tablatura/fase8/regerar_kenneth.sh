set -e
S=end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics
V=$(ls -d /acervo/kenneth\ acoustic/end\ of\ beginning*)
rm -f data/gold/ouro_video/$S.json
rm -rf data/saida/ouro_video/$S
python -m tab.ouro_video completar "$V" --ouro-v2 data/gold/ouro_video/$S.json --saida data/saida/ouro_video/$S --faixa 820 1080 | tail -30
