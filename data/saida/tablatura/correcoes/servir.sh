#!/bin/sh
# Correções do X empilhado e da auditoria cega: uma ferramenta por lote, só no PC do dono.
# As notas sugeridas aparecem em verde ("acrescentada"); marque "só a rotular" para ver só
# as telas a rever. Uso, no host: sh data/saida/tablatura/correcoes/servir.sh
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
cd /var/home/gabriel/Projects/chorinho-dataset || exit 1
C=data/saida/tablatura/correcoes
porta=8131
for lote in eob room335 t82 t83 t84 t85 t86; do
  docker compose -f compose.yaml -f compose.podman.yaml run --rm --no-deps -d \
    --name "correcoes_$lote" -e CUDA_VISIBLE_DEVICES= -p "127.0.0.1:$porta:$porta" chorinho \
    python -m tab.tablatura.ouro.ouro_video servir --pasta "$C/$lote" \
    --ouro "$C/$lote/conferencia_$lote.json" --porta "$porta" --host 0.0.0.0
  echo "$lote: http://127.0.0.1:$porta/"
  porta=$((porta + 1))
done
