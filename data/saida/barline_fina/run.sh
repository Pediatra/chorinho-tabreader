#!/bin/sh
# Medição LARGURA_MAX_BARLINE_PASSOS: controle (inf = descarte antigo) x variante (0.25, código).
# Uso (dentro de /app): sh data/saida/barline_fina/run.sh
# Um vídeo por vez. Falha de um vídeo é registrada e a rodada segue.
cd /app || exit 1
D=data/saida/barline_fina
OUR=data/gold/ouro_video
PRE=data/saida/ouro_video

rodada() {
  # nome video fps slug_ouro
  nome=$1; video=$2; fps=$3; slug=$4
  for modo in controle variante; do
    base=$D/${nome}_${modo}
    echo "== $base $(date +%T)"
    python $D/rodar.py "$video" "$base.json" "$modo" > "$base.transcrever.txt" 2>&1 \
      || { echo "FALHA transcrever $base"; continue; }
    if [ -n "$slug" ]; then
      pre=$PRE/$slug/pre.json
      if [ -f "$pre" ]; then
        python -m tab.avaliar_video --ouro $OUR/$slug.json --pred "$base.json" \
          --fps "$fps" --pre "$pre" > "$base.avaliar.txt" 2>&1
      else
        python -m tab.avaliar_video --ouro $OUR/$slug.json --pred "$base.json" \
          --fps "$fps" > "$base.avaliar.txt" 2>&1
      fi || echo "FALHA avaliar_video $base"
    fi
    echo "fim $base $(date +%T)"
  done
}

rodada retrato "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" 29.970030 retrato_brasileiro_v2
rodada greensleeves "/acervo/pablo romé/greensleeves 💚 guía de estudio 👌 partitura + tab + pdf.mp4" 25.0 greensleeves_guia_de_estudio_partitura_tab_pdf
rodada gymnopedie "/acervo/robert lunn/gymnopédie no.1 (erik satie) - includes sheet music⧸tab - classical guitar.mp4" 23.976024 gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar
rodada south_american "/acervo/guitar dell ́arte/south american music (easy), guitar tutorial with sheet and tab.mp4" 59.940060 south_american_music_easy_guitar_tutorial_with_sheet_and_tab
rodada tab_from_this_place "/acervo/kimny's guitar/[ tab ] from this place - pat metheny ｜ fingerstyle guitar cover.mp4" 30.0 tab_from_this_place_pat_metheny_fingerstyle_guitar_cover
rodada la_vie_en_rose "/acervo/iwaki/la vie en rose - edith piaf ｜ tab.mp4" 24.0 la_vie_en_rose_edith_piaf_tab
rodada end_of_beginning "/acervo/kenneth acoustic/end of beginning - djo ｜ fingerstyle guitar ｜ tab + chords + lyrics.mp4" 23.976024 end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics

# Sakura: sem ouro, só contagem por corda.
SAKURA="/acervo/ギタロー ⧸ guitarous/sakuraドロップス ソロギター 初心者向け タブ譜.mp4"
for modo in controle variante; do
  base=$D/sakura_${modo}
  echo "== $base $(date +%T)"
  python $D/rodar.py "$SAKURA" "$base.json" "$modo" > "$base.transcrever.txt" 2>&1 \
    || { echo "FALHA transcrever $base"; continue; }
  python $D/resumo_notas.py "$base.json" > "$base.resumo.txt" 2>&1
  echo "fim $base $(date +%T)"
done

# Métrica oficial de glifos, nos três modelos do projeto.
for modo in controle variante; do
  for k in 1 2 3; do
    echo "== oficial_$k $modo $(date +%T)"
    python $D/rodar_oficial.py "$modo" "artefatos/oficial_$k/glifo_sint.pt" \
      > "$D/oficial_${k}_${modo}.txt" 2>&1 || echo "FALHA oficial_$k $modo"
  done
done

echo "etapa concluida"
