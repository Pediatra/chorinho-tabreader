"""Confere os 4 arquivos chorinho/audio@1 contra os produtos (validar + sha256)."""

import json
import sys

from tab.audio_produto import confere_produto, validar

PARES = [
    ("mvp", "data/saida/conserto_v2/mvp.json"),
    ("iwaki_la_vie_en_rose", "data/saida/audio/a2/produtos/iwaki_la_vie_en_rose.json"),
    ("kimny_from_this_place", "data/saida/audio/a2/produtos/kimny_from_this_place.json"),
    ("shin_izumi_room_335", "data/saida/audio/a2/produtos/shin_izumi_room_335.json"),
]
ruim = False
for nome, produto_caminho in PARES:
    d = json.load(open(f"data/saida/audio/a5/{nome}.audio.json", encoding="utf-8"))
    produto = json.load(open(produto_caminho, encoding="utf-8"))
    erros = validar(d, produto)
    sha_ok = confere_produto(d, produto_caminho)
    print(f"{nome}: erros={len(erros)} sha_ok={sha_ok} colunas={len(d['colunas'])}")
    for e in erros[:5]:
        print("   ", e)
    ruim = ruim or bool(erros) or not sha_ok
sys.exit(1 if ruim else 0)
