"""Compara duas saidas do censo campo a campo nas decisoes (regra 9)."""
import json
import sys

CAMPOS_DECISAO = ("tablatura", "frac_tablatura", "marcador", "forma", "erro")


def carregar(caminho):
    ultimo = {}
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            r = json.loads(linha)
            ultimo[r["arquivo"]] = r
    return ultimo


def decisao(r):
    instantes = [(i.get("tab"), i.get("rect")) for i in r.get("instantes", [])]
    janelas = [
        (j.get("t0"), j.get("faixa"), j.get("faixa_quadros"), j.get("cor"),
         j.get("cor_quadros"), j.get("troca_tela"), j.get("rolagem"), j.get("quadros"),
         j.get("erro"))
        for j in r.get("janelas", [])
    ]
    return {"campos": {c: r.get(c) for c in CAMPOS_DECISAO}, "instantes": instantes,
            "janelas": janelas}


def main(a, b):
    ra, rb = carregar(a), carregar(b)
    comuns = sorted(set(ra) & set(rb))
    diverg = []
    for arq in comuns:
        if decisao(ra[arq]) != decisao(rb[arq]):
            diverg.append(arq)
    print(json.dumps({"comparados": len(comuns), "so_em_a": len(set(ra) - set(rb)),
                      "so_em_b": len(set(rb) - set(ra)), "divergentes": len(diverg),
                      "exemplos": diverg[:5]}, ensure_ascii=False, indent=1))
    return 0 if not diverg else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
