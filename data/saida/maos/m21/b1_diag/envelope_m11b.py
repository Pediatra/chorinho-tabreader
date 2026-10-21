"""Diagnóstico pós-prova 1024: erro do eixo do estágio 1 na M11b, por semente."""

import json

from tab import maos_braco_localizador as L
from tab.maos_braco_detector import QUADROS_PROVA, _imagem
from tab.maos_braco_faixa import eixo_da_faixa

ent = {e[0]: e for e in L._entradas_prova()}
saida = []
with L._trava_gpu():
    for s in (1, 2, 3):
        loc = L._carregar_localizador(f"L1_todos_s{s}")
        for q in QUADROS_PROVA:
            c, e = L.enquadrar(_imagem(L.MAOS_M11B / "quadros" / f"{q}.png"))
            dec = L.decodificar_quadro(L.prever_localizador(loc, [c])[0], e)
            linha = {"s": s, "id": q, "canal": ent[q][1], "achou": dec["achou"],
                     "presenca": dec.get("presenca")}
            if dec["achou"]:
                try:
                    erro = L.erro_do_eixo(eixo_da_faixa(dec["marcas"]), eixo_da_faixa(ent[q][2]))
                    linha["erro"] = erro
                    linha["dentro"] = L.dentro_do_envelope(erro)
                except ValueError:
                    linha["dentro"] = False
            saida.append(linha)
json.dump(saida, open("data/saida/maos/m21/b1_diag/envelope_m11b.json", "w"), indent=1, default=float)
