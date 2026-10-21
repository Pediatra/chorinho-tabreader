#!/bin/bash
# Prova "antes/depois" da partitura para a reestruturação 9001. Roda TUDO pelo nome antigo.
# Uso (no host, na raiz):  bash data/saida/partitura/diag/r9001/prova_9001.sh antes|depois
# Saída em data/saida/partitura/diag/r9001/prova/<rotulo>/. Compare depois com:
#   diff -r data/saida/partitura/diag/r9001/prova/antes data/saida/partitura/diag/r9001/prova/depois
set -euo pipefail
ROT=${1:?antes ou depois}
D=data/saida/partitura/diag/r9001/prova
OUT=$D/$ROT
rm -rf "$OUT" "$D/video_copia_$ROT"
mkdir -p "$OUT"
cp -r data/saida/partitura/video "$D/video_copia_$ROT"
STEMS="greensleeves_guia_de_estudio_partitura_tab_pdf south_american_music_easy_guitar_tutorial_with_sheet_and_tab gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"
PROD=""
for s in $STEMS; do PROD="$PROD --produto data/saida/fase8/rede/$s.json"; done
podman run --rm --security-opt label=disable -v "$PWD":/app -w /app -e PYTHONPATH=/app \
  docker.io/library/chorinho:dev bash -c "
    set -e
    python -m tab.partitura_video parear $PROD --pasta-video $D/video_copia_$ROT > $OUT/parear.txt
    python data/saida/partitura/diag/ca1/ca1.py > $OUT/ca1.txt
    porta=8184
    for f in data/gold/partitura/leitura_p1.json:data/saida/partitura/p1/conferencia/itens.json:R01 \
             data/gold/partitura/leitura_sem_produto.json:data/saida/partitura/diag/conferencia_sem_produto/itens.json:- \
             data/gold/partitura/leitura_d1.json:data/saida/part_frentes/fd_gabarito/itens_d1.json:-; do
      IFS=: read ouro itens rid <<< \"\$f\"
      cp \$ouro /tmp/ouro_copia.json
      python -m tab.partitura_gabarito servir --ouro /tmp/ouro_copia.json --itens \$itens --porta \$porta --host 127.0.0.1 > /tmp/servidor_\$porta.log 2>&1 &
      pid=\$!
      sleep 4
      python - \$itens \$porta >> $OUT/ferramenta.txt <<'PY' || { cat /tmp/servidor_\$porta.log; exit 1; }
import json, sys, urllib.parse, urllib.request
itens = json.load(open(sys.argv[1]))['itens']
rid = itens[0]['id']
url = 'http://127.0.0.1:' + sys.argv[2] + '/recorte/' + urllib.parse.quote(rid) + '.png'
with urllib.request.urlopen(url) as r:
    print(sys.argv[1], rid, r.status, len(r.read()))
PY
      kill \$pid
      cmp \$ouro /tmp/ouro_copia.json
      porta=\$((porta + 1))
    done
  "
for s in $STEMS; do
  cmp "$D/video_copia_$ROT/$s/$s.partitura.json" "data/saida/partitura/video/$s/$s.partitura.json"
  sha256sum "$D/video_copia_$ROT/$s/$s.partitura.json" | sed "s|$D/video_copia_$ROT/||" >> "$OUT/sha256_partitura.txt"
done
echo "OK: 3 documentos iguais byte a byte a data/saida/partitura/video" >> "$OUT/parear.txt"
