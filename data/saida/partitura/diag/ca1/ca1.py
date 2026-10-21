"""CA1 das frentes da partitura: reproduz os números de referência sem ler vídeo.

Só lê o que já está gravado (leituras de OMR, ``.partitura.json``, gabaritos) e só
imprime: não grava nada, então roda igual com ``data/saida`` montado só para leitura.

Uso (dentro do container, na raiz do projeto)::

    python data/saida/partitura/diag/ca1/ca1.py > <pasta da frente>/ca1/ca1.txt

Blocos:
    A. P3 em R01–R12 (Audiveris x2 + armadura do vídeo + homr confirmado pela tab),
       contra a tab do gabarito: ``tab.partitura_pareamento`` em memória.
    B. ``.partitura.json`` dos 3 produtos (19 telas) contra a tab do gabarito.
    C. Gabarito do dono R01–R21 (``leitura_p1.json``).
    D. Gabarito do dono sem produto (``leitura_sem_produto.json``).
    E. Gabarito do dono da troca pelo homr (``compassos_homr.json``), só contagem crua.
    F. Piloto sem produto: leituras que saíram (``execucao.json``).
"""

import collections
import glob
import json
from pathlib import Path

from tab.partitura_avaliar import contar, referencia_do_recorte
from tab.partitura_pareamento import INDICE, _carregar_ouro, _parear_recorte
from tab.partitura_video import eventos_do_produto

CHAVES = ["referencia", "certas", "altura_errada", "faltando", "inventada"]
STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]
GOLD = Path("data/gold/partitura")


def somar(a: dict, b: dict) -> None:
    """Soma as contagens de ``b`` em ``a``."""
    for k in CHAVES:
        a[k] = a.get(k, 0) + b.get(k, 0)


def lista(c: dict) -> list[int]:
    """Contagem na ordem de ``CHAVES``."""
    return [c.get(k, 0) for k in CHAVES]


def bloco_a(ouro: dict) -> None:
    """P3 nos 12 recortes do ouro."""
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    entradas = [e for e in indice if e["origem"] == "ouro"]
    antes, depois = {}, {}
    pares = com_x = homr = trocadas = 0
    for e in entradas:
        r = _parear_recorte(e, ouro)["resumo"]
        somar(antes, r["tab_antes"])
        somar(depois, r["tab_depois"])
        pares += r["pares"]
        com_x += r["com_x_conferido"]
        homr += r["acrescimos_homr"]
        trocadas += r["trocadas_pela_tab"]
    print(f"A. P3 R01-R12 ({len(entradas)} recortes), ordem {CHAVES}")
    print(f"   so Audiveris (com armadura do video): {lista(antes)}")
    print(f"   com homr confirmado pela tab:         {lista(depois)}")
    print(f"   pares {pares}, x conferido {com_x}, notas do homr {homr},"
          f" trocadas pela tab {trocadas}")


def bloco_b(ouro: dict) -> None:
    """Partitura dos produtos, todas as telas com pauta."""
    tot, tabprod = {}, {}
    telas_n = 0
    print("B. produtos (.partitura.json) contra a tab do gabarito")
    for stem in STEMS:
        produto = json.loads(Path(f"data/saida/fase8/rede/{stem}.json").read_text())
        gab = ouro[produto["video"]["arquivo"]][0]
        telas = {t["id"]: t for t in gab["telas"]}
        doc = json.loads(
            Path(f"data/saida/partitura/video/{stem}/{stem}.partitura.json").read_text()
        )
        por_video = {}
        for pauta in doc["pautas"]:
            tela = pauta["tela"]
            if tela not in telas:
                print(f"   {stem[:14]} tela {tela}: sem gabarito")
                continue
            x0, _, x1, _ = pauta["caixa_quadro"]
            ref = referencia_do_recorte(telas[tela]["notas"], x0, x1)
            lib = [
                frozenset(s["midi_escrito"] for s in e["simbolos"])
                for e in pauta["eventos"]
            ]
            c, _ = contar(lib, ref, "exato")
            tp = [e.midis for e in eventos_do_produto(produto["notas"], tela, x0, x1)]
            ct, _ = contar(tp, ref, "exato")
            somar(por_video, c)
            somar(tot, c)
            somar(tabprod, ct)
            telas_n += 1
        print(f"   {stem[:14]}: {lista(por_video)}")
    print(f"   total partitura ({telas_n} telas): {lista(tot)}")
    print(f"   so a tab do produto, mesmas telas: {lista(tabprod)}")


def contar_gabarito(arquivo: Path, rotulo: str) -> None:
    """Contagem crua dos estados que o dono marcou."""
    dados = json.loads(arquivo.read_text(encoding="utf-8"))["recortes"]
    total = collections.Counter()
    falt = conf = 0
    for k in sorted(dados):
        r = dados[k]
        conf += bool(r.get("confirmado", True))
        total.update(s["dono"] for s in r["simbolos"])
        falt += len(r["faltando"])
    lidos = sum(total.values())
    certos = total.get("certo", 0)
    print(f"{rotulo}: {len(dados)} recortes ({conf} confirmados), lidos {lidos},"
          f" certos {certos}, {dict(sorted(total.items()))}, faltando {falt},"
          f" cobertura {certos}/{certos + falt}")


def bloco_f() -> None:
    """Piloto sem produto: quantas leituras saíram por biblioteca."""
    tot = collections.Counter()
    for f in sorted(glob.glob("data/saida/partitura/sem_produto/*/omr/*/*/execucao.json")):
        partes = f.split("/")
        registros = json.loads(Path(f).read_text(encoding="utf-8"))
        chave = f"{partes[-3]}/{partes[-2]}"
        tot[(chave, "ok")] += sum(bool(r["ok"]) for r in registros)
        tot[(chave, "n")] += len(registros)
    print("F. piloto sem produto, leituras que sairam:")
    for chave in sorted({c for c, _ in tot}):
        print(f"   {chave}: {tot[(chave, 'ok')]}/{tot[(chave, 'n')]}")


def main() -> None:
    """Imprime os blocos A a F."""
    ouro = _carregar_ouro()
    bloco_a(ouro)
    bloco_b(ouro)
    contar_gabarito(GOLD / "leitura_p1.json", "C. leitura_p1")
    contar_gabarito(GOLD / "leitura_sem_produto.json", "D. leitura_sem_produto")
    if (GOLD / "compassos_homr.json").exists():
        contar_gabarito(GOLD / "compassos_homr.json", "E. compassos_homr")
    bloco_f()


if __name__ == "__main__":
    main()
