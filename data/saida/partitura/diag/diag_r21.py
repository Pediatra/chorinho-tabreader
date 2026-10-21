"""Diagnóstico do R21: estruturas e pautas do quadro de origem."""

import json
from pathlib import Path

import cv2

from tab.cache import ModoCache, caminho_do_quadro, ler_quadro, pasta_do_video
from tab.partitura_pauta import achar_pautas
from tab.partitura_recortes import (
    AMOSTRA_P0,
    carregar_amostra,
    escolher_quadros_b,
    CANAIS_B,
    estruturas_horizontais,
    extensao_horizontal,
    candidatos_verticais,
)
from dataclasses import replace

SAIDA = Path("/app/data/saida/partitura/diag")

amostra = carregar_amostra(AMOSTRA_P0)
CHAVE = "ギタロー ⧸ guitarous/【無料タブ譜】感電 - 米津玄師 - ソロギタータブ譜.mp4|4481331|1791502043"
linha = next(l for l in amostra if l["chave"] == CHAVE)
pasta = pasta_do_video(linha["chave"], ModoCache())
arquivo = caminho_do_quadro(pasta, "presenca_00", "png")
print("arquivo:", arquivo, arquivo.exists())
quadro = ler_quadro(arquivo)
print("shape", quadro.shape)
pautas = achar_pautas(quadro)
estr = estruturas_horizontais(quadro)
print("PAUTAS", len(pautas), linha["arquivo"])
for p in pautas:
    print(p.ys, p.entrelinha, p.x0, p.x1)
print("ESTRUTURAS")
for e in estr:
    print(round(e.y, 1), e.x0, e.x1, e.x1 - e.x0)
cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
for k, p in enumerate(pautas):
    ex0, ex1 = extensao_horizontal(cinza, p)
    pa = replace(p, x0=ex0, x1=ex1)
    outras = [q for j, q in enumerate(pautas) if j != k]
    ac, ab = candidatos_verticais(pa, estr, None, outras)
    print("pauta", k, pa.ys, "ext", ex0, ex1, "acima", ac, "abaixo", ab)
cv2.imwrite(str(SAIDA / "quadro_origem_r21.png"), quadro)
recorte = quadro[300:580, 0:1280]
cv2.imwrite(str(SAIDA / "recorte_ampliado_r21.png"), cv2.resize(recorte, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
