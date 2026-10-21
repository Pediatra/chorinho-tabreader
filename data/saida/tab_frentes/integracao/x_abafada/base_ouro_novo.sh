for s in ger ger_s2 ger_s3; do mkdir -p /tmp/b/$s; for f in /app/data/saida/fase8/ger/$s/*.json; do case $f in *regua*) continue;; esac; v=$(basename $f .json); python -m tab.avaliar_video --ouro /app/data/gold/ouro_video/$v.json --pred $f --json /tmp/b/$s/$v.json >/dev/null; done; python -c "
import json,glob,collections
s=collections.Counter()
for f in glob.glob('/tmp/b/$s/*.json'):
    t=json.load(open(f))['notas']['total']; s.update({k:t[k] for k in ('notas_ouro','entregues','casadas','casa_certa','inventadas','perdidas')})
print('$s',dict(s))"; done
