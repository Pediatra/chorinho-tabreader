set -e
python -m tab.avaliar_video --ouro data/gold/ouro_video/retrato_brasileiro_v2.json --pred data/saida/conserto_v2/mvp.json --fps 29.970030 --json data/saida/fase8/medida/mvp_regua_nova.json | tail -25
echo ======
python -m tab.avaliar_video --ouro data/gold/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf.json --pred data/saida/fase8/medida/greensleeves/run1.json --fps 25.0 --json data/saida/fase8/medida/greensleeves_regua_nova.json | tail -25
