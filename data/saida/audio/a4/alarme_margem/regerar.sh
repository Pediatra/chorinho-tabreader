#!/bin/sh
# Regenera os .audio.json v2.1 com o código novo (fora_da_pagina + alarme_leitura).
# Rodar dentro do host-spawn, com cwd na raiz do repo. transcriptor_campanitas fica de fora
# (vídeo descartado pelo dono).
set -u
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
COMMIT=$(git rev-parse HEAD)
A2=data/saida/audio/a2
A5=data/saida/audio/a5
L=data/saida/audio/a4/lote1
falhas=0

rodar() {
    # $1 nome, $2 produto, $3 alinhado, $4 saida
    echo "== $1"
    podman run --rm --security-opt label=disable -v "$PWD:/app" -w /app \
        -e PYTHONPATH=/app localhost/chorinho-audio:dev \
        python -m tab.audio_produto --produto "$2" --alinhado "$3" --saida "$4" \
        --commit "$COMMIT" || {
        echo "FALHOU: $1"
        falhas=$((falhas + 1))
    }
}

rodar mvp data/saida/conserto_v2/mvp.json "$A2/alinhado_v21_mvp.json" "$A5/v21_mvp.audio.json"
for n in iwaki_la_vie_en_rose kimny_from_this_place shin_izumi_room_335; do
    rodar "$n" "$A2/produtos/$n.json" "$A2/produtos/alinhado_v21_$n.json" "$A5/v21_$n.audio.json"
done
for n in guitarous_sakura iwaki_fly_me_to_the_moon iwaki_michelle kimny_bach_prelude \
    kimny_gunjo paolo_those_who_wait shin_izumi_dream_wish shin_izumi_giant_steps \
    transcriptor_charagua; do
    rodar "$n" "$L/$n.json" "$L/alinhado_v21_$n.json" "$L/v21_$n.audio.json"
done
echo "falhas: $falhas"
exit $falhas
