mkdir -p /tmp/ca1; for v in greensleeves_guia_de_estudio_partitura_tab_pdf gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar south_american_music_easy_guitar_tutorial_with_sheet_and_tab tab_from_this_place_pat_metheny_fingerstyle_guitar_cover end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics tabroom_335_larry_carlton_fingerstyle_guitar; do python -m tab.avaliar_video --ouro data/gold/ouro_video/$v.json --pred data/saida/fase8/ger/ger/$v.json --json /tmp/ca1/$v.json > /dev/null; done
python -c "
import json,glob,collections
s=collections.Counter()
for f in glob.glob('/tmp/ca1/*.json'):
    t=json.load(open(f))['notas']['total']; s.update({k:v for k,v in t.items() if isinstance(v,(int,float))})
print(dict(s))"
