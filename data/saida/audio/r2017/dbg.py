import sys
sys.path.insert(0, "data/saida/audio/r2017")
import comparar as C
item = next(x for x in C.LISTA if x["apelido"] == "iwaki_michelle")
pa = C.ler(item["produto_antigo"]); pn = C.ler(C.R / "produtos" / "iwaki_michelle.json")
ca, cn = C.centros_colunas(pa), C.centros_colunas(pn)
print(sorted((c, round(x)) for (t, c), x in ca.items() if t == 2))
print(sorted((c, round(x)) for (t, c), x in cn.items() if t == 2))
an = C.ler(C.R / "alinhado_iwaki_michelle.json")
print(sorted(c["coluna"] for c in an["colunas"] if c["tela"] == 2))
