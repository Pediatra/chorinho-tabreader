import json, time
from tab import caminhos, leitor, painel
L = [json.loads(l) for l in open("/app/data/saida/tab_rotulo/diag/painel_cifra/medida.jsonl")]
r = L[13]
t0 = time.time(); q = leitor.quadro_em(str(caminhos.acervo() / r["arquivo"]), r["t"]); t1 = time.time()
e = painel.escolher(q); t2 = time.time()
x = painel.candidatos_escuros_estreitos(q); t3 = time.time()
print(f"quadro {t1-t0:.1f}s escolher {t2-t1:.2f}s escuros {t3-t2:.2f}s", r["info"] if "info" in r else "")
