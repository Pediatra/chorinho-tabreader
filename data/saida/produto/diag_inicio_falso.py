"""Diagnostico: passagens curtas no comeco de exibicao (possivel marcador falso)."""

import json

r = json.load(open("data/saida/produto/mvp.json", encoding="utf-8"))
for t in r["telas"]:
    for k, e in enumerate(t["exibicoes"]):
        for p, passagem in enumerate(e["passagens"]):
            if p == 0 and len(passagem) <= 2:
                print(
                    "tela", t["id"], "exib", k, "t0", e["t0"],
                    "passagem0 tamanho", len(passagem), passagem,
                )
# notas cujo t_ini e o menor da nota, mas ha outra leitura depois da 1a passagem
for n in r["notas"]:
    if n["t_ini"] is not None and n["tela"] == 1 and n["coluna"] == 20:
        print("nota tela1 col20", n["corda"], n["casa"], n["t_ini"], "exib", n["exibicao"], "pass", n["passagem"])
