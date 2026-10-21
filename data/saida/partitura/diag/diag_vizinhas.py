"""Diagnóstico: vizinhas verticais de todas as pautas dos 21 quadros, com espessura."""

from dataclasses import replace

from tab.partitura_pauta import achar_pautas
from tab.partitura_recortes import (
    AMOSTRA_P0,
    CANAIS_B,
    FRACAO_ESTRUTURA_VIZINHA,
    _cinza,
    candidatos_verticais,
    carregar_amostra,
    escolher_quadros_b,
    estruturas_horizontais,
    extensao_horizontal,
    fontes_b,
    fontes_ouro,
    ler_fonte,
)

amostra = carregar_amostra(AMOSTRA_P0)
fontes = fontes_ouro() + fontes_b(escolher_quadros_b(amostra, CANAIS_B))
numero = 0
for fonte in fontes:
    quadro, origem = ler_fonte(fonte)
    pautas = achar_pautas(quadro)
    if not pautas:
        print("SEM PAUTA", fonte.canal, fonte.t)
        continue
    estr = estruturas_horizontais(quadro)
    cinza = _cinza(quadro)
    for k, pa in enumerate(pautas):
        numero += 1
        ex0, ex1 = extensao_horizontal(cinza, pa)
        p = replace(pa, x0=ex0, x1=ex1)
        outras = [q for j, q in enumerate(pautas) if j != k]
        ac, ab = candidatos_verticais(p, estr, fonte.rect, outras)
        minimo = FRACAO_ESTRUTURA_VIZINHA * (p.x1 - p.x0)
        perto = [
            (round(e.y, 1), e.x0, e.x1, e.altura)
            for e in estr
            if e.x1 - e.x0 >= minimo and (e.y < p.ys[0] - 3 or e.y > p.ys[4] + 3)
            and (e.y > p.ys[0] - 90 and e.y < p.ys[4] + 90)
        ]
        print(
            f"R{numero:02d} {fonte.canal[:12]:12s} t={fonte.t:7.2f} e={p.entrelinha:5.2f}"
            f" ys={p.ys[0]}-{p.ys[4]} ext={ex0}-{ex1} rect={fonte.rect is not None}"
            f" acima={ac} abaixo={ab}"
        )
        print("     perto (y, x0, x1, altura):", perto)
