"""Compara v2 e v3: régua do A1 (MVP), gabarito folha1 (itens não controle) e 3 vídeos sem marcador."""

import collections
import json

S = "data/saida/audio/a2/v3/saidas"
R = "data/saida/audio/a1/atraso_mvp.json"
G = "data/gold/audio/folha1.json"


def por_chave(alin):
    return {(c["tela"], c["exibicao"], c["coluna"]): c for c in alin["colunas"]}


def main():
    v2_antigo = json.load(open("data/saida/audio/a2/alinhado_v2_r1.json", encoding="utf-8"))
    v2_novo = json.load(open(f"{S}/mvp_v2_repro.json", encoding="utf-8"))
    a = por_chave(v2_antigo)
    b = por_chave(v2_novo)
    diff = [k for k in a if a[k]["t_audio"] != b[k]["t_audio"] or a[k]["motivo"] != b[k]["motivo"]]
    print(f"REGRESSAO v2 (registro x repro): colunas diferentes = {len(diff)} de {len(a)}")

    av2 = json.load(open(f"{S}/avaliacao_mvp_v2.json", encoding="utf-8"))
    av3 = json.load(open(f"{S}/avaliacao_mvp_v3.json", encoding="utf-8"))
    print("\nREGUA DO A1 (MVP), Y = 636:")
    linhas = [
        ("afirmadas", "afirmadas"),
        ("<=50 fluxo", "ok50_fluxo"),
        ("<=100 fluxo", "ok100_fluxo"),
        ("<=50 fluxo ou alturas", "ok50_fluxo_ou_alturas"),
        ("falsos >200 ms", "falsos_mais_de_200ms"),
        ("recusadas", "recusadas"),
    ]
    print(f"  {'metrica':24s} v2 | v3")
    for rot, k in linhas:
        print(f"  {rot:24s} {av2['totais'][k]} | {av3['totais'][k]}")
    print("  recusas por motivo: v2", av2["recusas"], "| v3", av3["recusas"])
    print("  afirmadas sem par:  v2", av2["sem_par"]["afirmadas_sem_par"], "| v3", av3["sem_par"]["afirmadas_sem_par"])
    print("  curva (conf>=limiar: afirm | <=100 | falsas):")
    for c2, c3 in zip(av2["curva"], av3["curva"], strict=True):
        print(f"    >= {c2['confianca_minima']:.1f}: v2 {c2['afirmadas']} | {c2['ok100_fluxo']} | {c2['falsos']}   v3 {c3['afirmadas']} | {c3['ok100_fluxo']} | {c3['falsos']}")

    g = json.load(open(G, encoding="utf-8"))
    mapa = {"sky": "mvp", "iwaki": "iwaki", "shin": "shin", "kimny": "kimny"}
    arquivos = {
        "mvp": None,
        "iwaki": f"{S}/iwaki_la_vie_en_rose_",
        "shin": f"{S}/shin_izumi_room_335_",
        "kimny": f"{S}/kimny_from_this_place_",
    }
    v2v3 = {}
    for nome, pref in arquivos.items():
        if pref is None:
            v2v3[nome] = (por_chave(v2_novo), por_chave(json.load(open(f"{S}/mvp_v3.json", encoding="utf-8"))))
        else:
            v2v3[nome] = (
                por_chave(json.load(open(pref + "v2.json", encoding="utf-8"))),
                por_chave(json.load(open(pref + "v3.json", encoding="utf-8"))),
            )
    print("\nGABARITO folha1 (itens NAO controle): o que v2 e v3 dizem daquela coluna")
    print("  id  video  coluna  dono      t_clique   | v2 (t, motivo)          | v3 (t, motivo)")
    contagem = collections.Counter()
    for it in g["itens"]:
        if it["controle"]:
            continue
        nome = next(v for k, v in mapa.items() if it["video"].lower().startswith(k))
        v2d, v3d = v2v3[nome]
        k = (it["tela"], it["exibicao"], it["coluna"])
        r2 = v2d.get(k)
        r3 = v3d.get(k)

        def desc(r):
            if r is None:
                return "sem registro"
            if r["t_audio"] is None:
                return f"RECUSA ({r['motivo']})"
            d = (r["t_audio"] - it["t_clique"]) * 1000
            return f"afirma {r['t_audio']:.3f} (dif {d:+.0f} ms)"

        print(f"  {it['id']} {nome:6s} t{it['tela']} e{it['exibicao']} c{it['coluna']:<3d} {it['resposta_dono']:8s} {it['t_clique']:.3f} | {desc(r2)} | {desc(r3)}")
        contagem[(it["resposta_dono"], "v2", r2 is not None and r2["t_audio"] is not None)] += 1
        contagem[(it["resposta_dono"], "v3", r3 is not None and r3["t_audio"] is not None)] += 1
    print("\nafirma (True) / recusa (False) por resposta do dono:", dict(sorted(contagem.items())))

    print("\nSEM MARCADOR: colunas que a v3 mudou (v2 afirmava -> v3 recusa; ou t diferente):")
    for nome in ("iwaki", "shin", "kimny"):
        v2d, v3d = v2v3[nome]
        mudou_recusa = [k for k in v2d if v2d[k]["t_audio"] is not None and v3d.get(k, {}).get("t_audio") is None]
        mudou_tempo = [k for k in v2d if v2d[k]["t_audio"] is not None and v3d.get(k, {}).get("t_audio") not in (None, v2d[k]["t_audio"])]
        marcadas = [k for k in v3d if v3d[k]["motivo"] == "sem_ataque_esperado"]
        afirm2 = sum(1 for r in v2d.values() if r["t_audio"] is not None)
        afirm3 = sum(1 for r in v3d.values() if r["t_audio"] is not None)
        print(f"  {nome}: colunas {len(v3d)} | afirmadas v2 {afirm2} -> v3 {afirm3} | marcadas sem_ataque_esperado {len(marcadas)} | afirmadas que viraram recusa {len(mudou_recusa)} | tempo mudou {len(mudou_tempo)}")
        print(f"     marcadas (tela,exib,col): {sorted(marcadas)}")


if __name__ == "__main__":
    main()
