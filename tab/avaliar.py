"""Aferição padronizada no gabarito real (usada para comparar execuções)."""
import sys, json, cv2
sys.path.insert(0, 'tools')
from inventario import ler_quadro
from reconhecer import carregar_modelo, reconhecer_linha

modelo, rotulos, dev = carregar_modelo('/tmp/sint/glifo_sint.pt')
g = json.load(open('gold/gabarito.json'))
linhas = []
for am in g['amostras']:
    if not am.get('video') or am['video'].startswith('sky guitar'):
        img = cv2.imread('parts/clipes/-6rawhontyg_000120_000200/linha_01_tablatura.png', cv2.IMREAD_UNCHANGED)
    else:
        frame, _ = ler_quadro('/run/media/gabriel/3014CD4714CD1130/chorinho/' + am['video'], 0.5)
        img = frame[620:1080, :] if am['faixa'] == 'base' else frame[0:400, :]
    r = reconhecer_linha(img, modelo, rotulos, dev)
    prev = [n['casa'] for n in r['notas']]
    idx = sorted(int(k) for k in am['rotulos'])
    ok = sum(1 for i in idx if prev[i] == am['rotulos'][str(i)])
    linhas.append((am['canal'], ok, len(idx)))
ac = sum(o for _, o, _ in linhas); tot = sum(t for _, _, t in linhas)
print("RESULTADO " + " ".join(f"{c.split()[0][:6]}={o}/{t}" for c, o, t in linhas) +
      f" | TOTAL={ac}/{tot}={ac/tot:.3f}")
