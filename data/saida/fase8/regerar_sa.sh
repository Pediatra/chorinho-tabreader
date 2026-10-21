set -e
S=south_american_music_easy_guitar_tutorial_with_sheet_and_tab
V=$(ls -d /acervo/guitar\ dell*/south\ american\ music\ \(easy\)*)
rm -f data/gold/ouro_video/$S.json
rm -rf data/saida/ouro_video/$S
python -m tab.ouro_video completar "$V" --ouro-v2 data/gold/ouro_video/$S.json --saida data/saida/ouro_video/$S --faixa 880 1080 | tail -30
