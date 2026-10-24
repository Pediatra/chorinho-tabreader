#!/bin/bash
# Prova 0216, PASSO 2: produto da tela (DETECTOR_PADRAO/CALIBRADO, CPU, imagem base), sem som.
# Retomavel: pula o que ja existe. Um video que falha tenta de novo uma vez, depois segue.
# Uso, no host, na raiz do repositorio: bash data/saida/tablatura/recusa/r0216/rodar.sh
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
R=data/saida/tablatura/recusa/r0216
B=data/saida/audio/r2017/podman_base.sh
LOG=$R/rodar.log
mkdir -p "$R/produtos" "$R/logs"
echo "INICIO $(date -Is)" >> "$LOG"
while IFS=$'\t' read -r nome video; do
  [ -n "$nome" ] || continue
  [ -s "$R/produtos/$nome.json" ] && continue
  for tentativa in 1 2; do
    t0=$(date +%s)
    sh $B python -m tab.tablatura.produto.video "/acervo/$video" \
      --json "$R/produtos/$nome.json" > "$R/logs/${nome}.t${tentativa}.log" 2>&1
    rc=$?
    echo "$nome RC=$rc TEMPO_S=$(( $(date +%s) - t0 )) TENTATIVA=$tentativa" >> "$LOG"
    [ $rc -eq 0 ] && break
  done
done < "$R/lista.tsv"
echo "FIM $(date -Is)" >> "$LOG"
