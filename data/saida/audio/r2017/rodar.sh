#!/bin/bash
# Rodada 2017: por vídeo, produto novo (tab.video, leitor padrão rede, CPU), alinhador v2.1
# sem mudança (imagem base) e arquivo irmão chorinho/audio@1 (imagem chorinho-audio:dev).
# Falha de um passo: registra e pula só o que depende dele. Retomável: pula o que já existe.
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
R=data/saida/audio/r2017
B=$R/podman_base.sh
LOG=$R/rodar.log
COMMIT=$(host-spawn -no-pty -cwd "$PWD" git rev-parse HEAD)
echo "INICIO $(date -Is) COMMIT=$COMMIT" >> "$LOG"

passo() {
  ap="$1"; nome="$2"; shift 2
  t0=$(date +%s)
  "$@" > "$R/logs/${ap}_${nome}.log" 2>&1
  rc=$?
  echo "[$ap] $nome RC=$rc TEMPO_S=$(( $(date +%s) - t0 ))" >> "$LOG"
  return $rc
}

while IFS=$'\t' read -r ap video; do
  [ -n "$ap" ] || continue
  if [ ! -s "$R/produtos/$ap.json" ]; then
    passo "$ap" produto "$B" python -m tab.video "/acervo/$video" \
      --json "$R/produtos/$ap.json" || continue
  fi
  if [ ! -s "$R/alinhado_$ap.json" ]; then
    passo "$ap" alinhar "$B" python -m tab.audio_alinhar --produto "$R/produtos/$ap.json" \
      --video "/acervo/$video" --saida "$R/alinhado_$ap.json" --metodo onsets || continue
  fi
  if [ ! -s "$R/$ap.audio.json" ]; then
    IMAGEM=localhost/chorinho-audio:dev passo "$ap" irmao "$B" python -m tab.audio_produto \
      --produto "$R/produtos/$ap.json" --alinhado "$R/alinhado_$ap.json" \
      --saida "$R/$ap.audio.json" --commit "$COMMIT"
  fi
done < "$R/lista.tsv"
echo "FIM $(date -Is)" >> "$LOG"
