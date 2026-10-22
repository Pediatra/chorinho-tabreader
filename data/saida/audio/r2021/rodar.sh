#!/bin/bash
# Rodada 2021: por vídeo da T8.2, o produto da tela (leitor rede, CPU, imagem base) e o som
# livre (Riley guitar-fl, imagem chorinho-som). Retomável: pula o que já existe.
# Uso, no host, na raiz do repositório: bash data/saida/audio/r2021/rodar.sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
R=data/saida/audio/r2021
B=data/saida/audio/r2017/podman_base.sh
LOG=$R/rodar.log
echo "INICIO $(date -Is) COMMIT=$(host-spawn -no-pty -cwd "$PWD" git rev-parse HEAD)" >> "$LOG"
passo() {
  nome="$1"; etapa="$2"; shift 2
  t0=$(date +%s)
  "$@" > "$R/logs/${etapa}_${nome}.log" 2>&1
  rc=$?
  echo "$nome $etapa RC=$rc TEMPO_S=$(( $(date +%s) - t0 ))" >> "$LOG"
  return $rc
}
[ -s "$R/lista.tsv" ] || passo todos preparar sh $B python $R/preparar.py || { echo "FIM_COM_ERRO preparar" >> "$LOG"; exit 2; }
while IFS=$'\t' read -r nome video flac; do
  [ -n "$nome" ] || continue
  if [ ! -s "$R/produtos/$nome.json" ]; then
    passo "$nome" produto sh $B python -m tab.tablatura.produto.video "/acervo/$video" \
      --json "$R/produtos/$nome.json"
  fi
  if [ ! -s "$R/som/$nome.json" ]; then
    IMAGEM=localhost/chorinho-som:dev passo "$nome" som sh $B python -m tab.audio.transcrever_riley \
      "$flac" --pesos artefatos/riley_guitar/guitar-fl.pth --saida "$R/som/$nome.json"
  fi
done < "$R/lista.tsv"
echo "FIM $(date -Is)" >> "$LOG"
