"""Ajuste 1 da P4 (rodada 3027): notas que não entram, com o motivo, e a tabela por vídeo.

Só lê. Refaz `_pauta_do_recorte` e `_completar_pauta_do_recorte` nos recortes da cópia da frente
(`fp_produto/video`), com as pausas de cada recorte, e imprime cada nota que não entra. Também
conta as pausas da leitura herdada que não têm slot no `.omr` (não entram na regra de pausa).

Uso (dentro do container, em /app): python motivos_p4.py
"""

import collections
import json
from pathlib import Path

from tab import partitura_video as pv
from tab.partitura_completar_pauta import _nome
from tab.partitura_gabarito import ler_partitura
from tab.partitura_pareamento import _x_do_simbolo, x_dos_compassos

FRENTE = Path("/app/data/saida/part_frentes/fp_produto/video")
STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]
CURTO = {
    STEMS[0]: "greensleeves",
    STEMS[1]: "south",
    STEMS[2]: "gym",
}
GYM = STEMS[2]


def pausas_sem_slot(entrada, omr):
    """Pausas da leitura herdada do recorte: (total, sem x)."""
    rid = entrada["id"]
    herdada = omr / "audiveris" / f"{pv.CONDICAO_AUDIVERIS}_herdada" / rid / "saida.musicxml"
    entrada_omr = omr / "audiveris" / pv.CONDICAO_AUDIVERIS / rid / "entrada.omr"
    if not herdada.exists() or not entrada_omr.exists():
        return 0, 0
    leitura = ler_partitura(herdada)
    pilhas = x_dos_compassos(entrada_omr)
    total = sem = 0
    for k, compasso in enumerate(leitura["compassos"]):
        pilha = pilhas[k] if k < len(pilhas) else None
        for simbolo in compasso["simbolos"]:
            if simbolo["pausa"]:
                total += 1
                if _x_do_simbolo(simbolo, pilha, entrada["caixa_recorte"][0], 2.0) is None:
                    sem += 1
    return total, sem


def main():
    motivos_todos = []
    for stem in STEMS:
        notas = json.loads(
            Path(f"/app/data/saida/fase8/rede/{stem}.json").read_text(encoding="utf-8")
        )["notas"]
        pasta = FRENTE / stem
        indice = json.loads((pasta / "recortes" / "indice.json").read_text(encoding="utf-8"))
        omr = pasta / "omr"
        total_pausas = sem_slot = 0
        for entrada in indice:
            if entrada["sem_pauta"]:
                continue
            pauta = pv._pauta_do_recorte(entrada, notas, omr)
            pausas = pv._pausas_do_recorte(entrada, omr)
            t, s = pausas_sem_slot(entrada, omr)
            total_pausas += t
            sem_slot += s
            _, _, motivos = pv._completar_pauta_do_recorte(pauta, notas, pausas, pv._vozes_do_recorte(entrada, omr))
            for m in motivos:
                motivos_todos.append((stem, m))
        print(f"{CURTO[stem]}: pausas na leitura herdada {total_pausas}, sem slot no .omr {sem_slot}")
    print()
    print("vídeo | tela | recorte | x | nota | tipo | compasso | motivo")
    for stem, m in motivos_todos:
        print(
            f"{CURTO[stem]} | {m['tela']} | {m['recorte']} | {m['x']:.1f} |"
            f" {_nome(m['midi'])} | {m['tipo']} | {m['compasso']} | {m['motivo']}"
        )
    contagem = collections.Counter((CURTO[s], m["motivo"]) for s, m in motivos_todos)
    print()
    print("contagem por vídeo e motivo:", dict(contagem))
    print(f"total de notas que não entram: {len(motivos_todos)}")
    for stem, m in motivos_todos:
        if stem == GYM and m["tela"] == 7 and m["recorte"] == "T07":
            print(f"gym T07 x={m['x']:.1f} {_nome(m['midi'])}: motivo {m['motivo']}")
    conciliar(motivos_todos)


def conciliar(motivos_todos):
    """Confere: completadas do documento novo + notas que saíram = E1 (e tela 10 à parte)."""
    e1 = json.loads(
        Path("/app/data/saida/part_frentes/fp_produto/e1_passo3.json").read_text(
            encoding="utf-8"
        )
    )
    contadas_e1 = collections.Counter((n["video"], n["tipo"]) for n in e1["completadas"])
    novos = collections.Counter()
    tela10_novas = 0
    for stem in STEMS:
        doc = json.loads(
            (FRENTE / stem / f"{stem}.partitura.json").read_text(encoding="utf-8")
        )
        for pauta in doc["pautas"]:
            for evento in pauta["eventos"]:
                tipo = "isolado" if evento["par"] and evento["par"]["metodo"] == "tab" else "acorde"
                for s in evento["simbolos"]:
                    if s["origem"] != "tab_completada":
                        continue
                    if stem == GYM and pauta["tela"] == 10:
                        tela10_novas += 1
                    else:
                        novos[(stem, tipo)] += 1
    saiu = collections.Counter(
        (stem, m["tipo"]) for stem, m in motivos_todos if not (stem == GYM and m["tela"] == 10)
    )
    tela10_saiu = sum(1 for stem, m in motivos_todos if stem == GYM and m["tela"] == 10)
    ok = True
    for stem in STEMS:
        for tipo in ("acorde", "isolado"):
            if novos[(stem, tipo)] + saiu[(stem, tipo)] != contadas_e1[(stem, tipo)]:
                ok = False
                print(f"FALHA {stem} {tipo}")
    print(f"conciliação fora da tela 10 com a E1 (contadas): {'OK' if ok else 'FALHA'}")
    total_tela10 = tela10_novas + tela10_saiu
    print(
        f"tela 10: novas {tela10_novas} + saíram {tela10_saiu} = {total_tela10}"
        f" (E1 à parte: {e1['a_parte']['tela_10_gym']})"
    )


if __name__ == "__main__":
    main()
