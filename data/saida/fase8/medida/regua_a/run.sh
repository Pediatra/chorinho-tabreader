set -e
O=data/saida/fase8/medida/regua_a
GSP=data/saida/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf/pre.json
GS=data/gold/ouro_video/greensleeves_guia_de_estudio_partitura_tab_pdf.json
SA=data/gold/ouro_video/south_american_music_easy_guitar_tutorial_with_sheet_and_tab.json
r() { echo "== $1"; shift; python -m tab.avaliar_video "$@" | grep -E "^tempo|precisão|revocação|acerto de casa"; }
r "MVP (mvp_v2, oficial)" --ouro data/gold/ouro_video/retrato_brasileiro_v2.json --pred data/saida/mvp_v2/mvp.json --fps 29.970030 --json $O/mvp.json
r "Greensleeves oficial (greensleeves_v2)" --ouro $GS --pred data/saida/fase8/medida/greensleeves_v2/run1.json --pre $GSP --fps 25.0 --json $O/gs_oficial.json
for s in 1 2 3; do r "Greensleeves serif3_$s (t$s)" --ouro $GS --pred data/saida/serif/t$s/d_gs.json --pre $GSP --fps 25.0 --json $O/gs_t$s.json; done
for s in 1 2 3; do r "MVP serif3_$s (t$s)" --ouro data/gold/ouro_video/retrato_brasileiro_v2.json --pred data/saida/serif/t$s/c_mvp.json --fps 29.970030 --json $O/mvp_t$s.json; done
r "South American (v2)" --ouro $SA --pred data/saida/fase8/medida/south_american_v2/run1.json --fps 59.940060 --json $O/sa.json
