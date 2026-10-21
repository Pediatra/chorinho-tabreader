#!/bin/sh
# Prova byte a byte da trilha áudio para a reestruturação 9001.
# Roda os módulos do áudio pelos NOMES ANTIGOS (python -m tab.audio_*) e grava em $1
# (antes/ ou depois/). Depois: diff -r antes depois  -> tem de sair vazio.
# Uso (no host, na raiz do repositório): sh data/saida/audio/r2020/prova_9001/prova.sh antes
set -u
R=/var/home/gabriel/Projects/chorinho-dataset
B=$R/data/saida/audio/r2017/podman_base.sh
P=data/saida/audio/r2020/prova_9001
D=$P/atual   # sempre a mesma pasta: o caminho entra no retrato.audio.json
rm -rf "$R/$D"; mkdir -p "$R/$D"
V="/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
rc=0
# 1. alinhador (audio_alinhar -> audio_extrair, audio_onsets), imagem base
sh $B python -m tab.audio_alinhar --produto data/saida/produto/mvp.json --video "$V" \
  --saida $D/alinhado_retrato.json || rc=1
# 2. produto do áudio (audio_produto; lê data/gold/audio), commit fixo para comparar
sh $B python -m tab.audio_produto --produto data/saida/produto/mvp.json \
  --alinhado $D/alinhado_retrato.json --saida $D/retrato.audio.json --commit prova || rc=2
# 3. régua do transcritor (audio_som_medir; lê data/gold/ouro_video, data/gold/audio, o capo das mãos)
sh $B python -m tab.audio_som_medir --lista data/saida/audio/r2018/lista.json \
  --som data/saida/audio/r2019/som_fl --saida $D/som_medir.json > $R/$D/som_medir.txt || rc=3
# 4. cruzamento (cruzar_fontes) no retrato
sh $B python -m tab.cruzar_fontes --produto data/saida/audio/r2017/produtos/mvp.json \
  --som data/saida/audio/r2019/som_fl/retrato_brasileiro_v2.json \
  --saida $D/cruzado_retrato.json > $R/$D/cruzado_retrato.txt || rc=4
# 5. transcritor na imagem chorinho-som (Python 3.10), ~5 min de CPU
IMAGEM=localhost/chorinho-som:dev sh $B python -m tab.audio_transcrever_riley \
  /cache/audio/ba866b765043431d1ca098a8.flac --pesos artefatos/riley_guitar/guitar-fl.pth \
  --saida $D/som_retrato.json || rc=5
rm -rf "$R/$P/$1"; mv "$R/$D" "$R/$P/$1"
echo "RC=$rc"
exit $rc
