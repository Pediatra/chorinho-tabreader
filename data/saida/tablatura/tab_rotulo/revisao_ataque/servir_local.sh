#!/bin/sh
# Revisão do modo ataque (dono, 2026-10-23): sobe as 11 ferramentas do modo ataque.
# Só no PC do dono (sem Cloudflare, pedido de 2026-10-23). Os logs ficam em revisao_ataque/logs/.
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset
R=data/saida/tablatura; R2=$R/tab_rotulo/r2; O=$R/ouro_video; G=data/gold/ouro_video
L=$R/tab_rotulo/revisao_ataque/logs; mkdir -p $L
CP="docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps"
subir() {  # nome porta pasta ouro ataque
  $CP -p 127.0.0.1:$2:$2 chorinho python -m tab.tablatura.ouro.ouro_video servir \
    --pasta "$3" --ouro "$4" --ataque "$5" --porta $2 --host 0.0.0.0 > $L/$1.log 2>&1 &
  i=0; until curl -s -o /dev/null http://127.0.0.1:$2/; do i=$((i+1)); [ $i -gt 90 ] && { echo "FALHOU $1"; return; }; sleep 2; done
  echo "$1 http://127.0.0.1:$2/"
}
subir t85 8127 $R/t85/passe_ataque/ferramenta $R/t85/passe_ataque/conferencia_t85_servida.json $R2/conferir_t85/ataque_t85.json
subir t84 8151 $R/t84/ferramenta $R/t84/passe_ataque/conferencia_t84_servida.json $R2/conferir_t84/ataque_t84.json
subir t83 8152 $R/t83/ferramenta $R/t83/ferramenta/conferencia_t83.json $R2/conferir_t83/ataque_t83.json
subir t82 8153 $R/t82/ferramenta $R/t82/ferramenta/conferencia_t82.json $R2/conferir_novos/ataque_t82.json
s=end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics; subir eob 8154 $O/$s $G/$s.json $R2/conferir/ataque_end_of_beginning.json
s=la_vie_en_rose_edith_piaf_tab; subir lavie 8155 $O/$s $G/$s.json $R2/conferir/ataque_la_vie_en_rose.json
s=tab_from_this_place_pat_metheny_fingerstyle_guitar_cover; subir pat 8156 $O/$s $G/$s.json $R2/conferir/ataque_pat_metheny.json
s=tabroom_335_larry_carlton_fingerstyle_guitar; subir room335 8157 $O/$s $G/$s.json $R2/conferir/ataque_tabroom_335.json
s=greensleeves_guia_de_estudio_partitura_tab_pdf; subir greensleeves 8158 $O/$s $G/$s.json $R2/conferir_novos/ataque_greensleeves.json
s=retrato_brasileiro_v2; subir retrato 8159 $O/$s $G/$s.json $R2/conferir_novos/ataque_retrato.json
s=south_american_music_easy_guitar_tutorial_with_sheet_and_tab; subir south 8160 $O/$s $G/$s.json $R2/conferir_novos/ataque_south_american.json
echo "todas no ar"
wait
