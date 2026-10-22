"""O caminho da TAB escura acha a TAB nos quadros em que o painel pegou o braço?"""
import json
import sys

from tab import caminhos, leitor, painel

B = caminhos.TAB_ROTULO / "diag" / "painel_cifra"
L = [json.loads(linha) for linha in (B / "medida.jsonl").open(encoding="utf-8")]
ks = [int(a) for a in sys.argv[1:]] or [
    r["k"] for r in L if r.get("painel") and r["painel"]["centro_frac"] < 0.5
]
for r in (r for r in L if r["k"] in ks):
    q = leitor.quadro_em(str(caminhos.acervo() / r["arquivo"]), r["t"])
    esc = painel.escolher(q)
    escuros = sorted(painel.candidatos_escuros_estreitos(q), key=lambda t: -t[0])
    alt = painel._primeira_tablatura([[c for _u, c in escuros]])
    conv = painel._cordas_convergem(esc) if esc is not None else None
    def pos(c):
        return None if c is None else (c.nome, int(c.y0 + min(c.grade.linhas_y)), round(c.passo, 1))
    print(r["k"], "escolher", pos(esc), "converge", conv, "| escuros", len(escuros),
          "alternativa", pos(alt), flush=True)
