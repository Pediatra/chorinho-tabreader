"""Rodada 2020: veredito do cruzamento tela × som contra o gabarito do dono.

Amostra principal (fora do treino do leitor): as 4 telas de acordes_2018, produtos da 2017.
Secundária (dentro do treino): os 8 vídeos do gabarito de tablatura.
"""

import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/app")
from tab import audio_som_medir as M  # noqa: E402
from tab import avaliar_video as A  # noqa: E402
from tab import cruzar_fontes as C  # noqa: E402

R = Path("/app/data/saida/audio/r2020")
R17 = Path("/app/data/saida/audio/r2017/produtos")
SOM = Path("/app/data/saida/audio/r2019/som_fl")
GOLD = Path("/app/data/gold")
CAPOS = json.loads(M.CAPO.read_text(encoding="utf-8"))
NFC = lambda s: unicodedata.normalize("NFC", s or "")  # noqa: E731

OURO = {  # gabarito de tablatura -> produto
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics": R / "produtos",
    "greensleeves_guia_de_estudio_partitura_tab_pdf": R / "produtos",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar": R / "produtos",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab": R / "produtos",
    "la_vie_en_rose_edith_piaf_tab": R17 / "iwaki_la_vie_en_rose.json",
    "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover": R17 / "kimny_from_this_place.json",
    "tabroom_335_larry_carlton_fingerstyle_guitar": R17 / "shin_izumi_room_335.json",
    "retrato_brasileiro_v2": R17 / "mvp.json",
}


def produto_de(nome, alvo):
    p = alvo / f"{nome}.json" if alvo.is_dir() else alvo
    return json.loads(p.read_text(encoding="utf-8"))


def cruzado(produto, som_nome):
    som = json.loads((SOM / f"{som_nome}.json").read_text(encoding="utf-8"))
    video = produto["video"]["arquivo"]
    assert NFC(video) == NFC(som["video"]), (video, som["video"])
    som["video"] = video
    capo = M.capo_do_video(NFC(video), {"videos": [dict(v, arquivo=NFC(v["arquivo"])) for v in CAPOS["videos"]]})
    return C.cruzar(produto, som, capo, str(CAPOS["fonte"])), capo


def status_das_notas(gold_notas, prod_notas, passo):
    gold = [g for g in gold_notas if not g.get("removida")]
    prev = [A.NotaPrevista(corda=n["corda"], casa=n["casa"], x=n["x"], t_ini=None) for n in prod_notas]
    status = ["inventada"] * len(prod_notas)
    for i, j in A.casar_notas(gold, prev, A.FRACAO_PASSO * passo):
        status[j] = "certa" if M.casa_inteira(gold[i]["casa"]) == prod_notas[j]["casa"] else "casa_errada"
    return status


def registrar(tab, erros, amostra, video, tela, notas, status):
    for n, s in zip(notas, status):
        tab[(amostra, n["veredito"], s)] += 1
        if s != "certa":
            erros.append({"amostra": amostra, "video": video[:40], "tela": tela, "coluna": n["coluna"],
                          "corda": n["corda"], "casa": n["casa"], "midi": n["midi"], "status": s,
                          "veredito": n["veredito"], "ouvidas": n.get("ouvidas_no_evento")})


def main():
    tab, erros, resumo = Counter(), [], {}
    # principal: acordes_2018
    ouro = json.loads((GOLD / "audio" / "acordes_2018.json").read_text(encoding="utf-8"))
    indice = {i["id"]: i for i in json.loads((Path("/app/data/saida/audio/r2018/ferramenta_acordes/indice.json")).read_text())}
    for t in ouro["telas"]:
        if not t.get("conferida"):
            continue
        ind = indice[t["id"]]
        prod = json.loads((R17 / f"{ind['produto']}.json").read_text(encoding="utf-8"))
        cz, capo = cruzado(prod, ind["produto"])
        tc = next(x for x in cz["telas"] if x["tela"] == ind["tela_produto"])
        passo = float(next(x for x in prod["telas"] if x["id"] == ind["tela_produto"])["passo"])
        st = status_das_notas(t["notas"], tc["notas"], passo)
        registrar(tab, erros, "fora_do_treino", ind["produto"], ind["tela_produto"], tc["notas"], st)
        resumo[ind["produto"]] = {"capo": capo, "notas": len(st), **Counter(st)}
    # secundária: os 8 do gabarito de tablatura
    for nome, alvo in OURO.items():
        prod = produto_de(nome, alvo)
        cz, capo = cruzado(prod, nome)
        ouro = json.loads((GOLD / "ouro_video" / f"{nome}.json").read_text(encoding="utf-8"))
        conf = A.so_conferidas(ouro)
        pred = A.ler_predicao(prod)
        mapa = A.casar_telas([int(t["id"]) for t in conf["telas"]], conf.get("instantes", []), pred.telas)
        mapa, _ = A.casar_sem_instante(conf["telas"], mapa, pred.telas)
        por_id = {x["tela"]: x for x in cz["telas"]}
        passos = {int(x["id"]): x.get("passo") for x in prod["telas"]}
        cont = Counter()
        for t in conf["telas"]:
            pid = mapa.get(int(t["id"]))
            if pid is None or not passos.get(pid):
                cont["tela_sem_par"] += 1
                continue
            notas = por_id[pid]["notas"]
            st = status_das_notas(t["notas"], notas, float(passos[pid]))
            registrar(tab, erros, "dentro_do_treino", nome, pid, notas, st)
            cont.update(st)
        resumo[nome] = {"capo": capo, **cont}
    out = {"tabela": {"|".join(k): v for k, v in sorted(tab.items())}, "resumo": resumo, "erros": erros}
    (R / "medida.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    linhas = []
    for amostra in ("fora_do_treino", "dentro_do_treino", "somadas"):
        def n(v, s):
            if amostra == "somadas":
                return sum(tab[(a, v, s)] for a in ("fora_do_treino", "dentro_do_treino"))
            return tab[(amostra, v, s)]
        linhas.append(f"== {amostra}")
        for v in C.VEREDITOS:
            linhas.append(f"  {v:15s} certa {n(v,'certa'):5d}  casa_errada {n(v,'casa_errada'):3d}  inventada {n(v,'inventada'):3d}")
        conf_ok = n("confirma", "certa"); conf_err = n("confirma", "casa_errada") + n("confirma", "inventada")
        err_com = sum(n(v, s) for v in ("confirma", "nao_confirma", "coluna_sem_par") for s in ("casa_errada", "inventada"))
        err_acus = sum(n(v, s) for v in ("nao_confirma", "coluna_sem_par") for s in ("casa_errada", "inventada"))
        alarme = sum(n(v, s) for v in ("nao_confirma", "coluna_sem_par") for s in ("certa", "casa_errada", "inventada"))
        linhas.append(f"  K1 erradas entre confirma: {conf_err}/{conf_ok + conf_err} = {conf_err / max(1, conf_ok + conf_err):.4f}")
        linhas.append(f"  K2 erros acusados: {err_acus}/{err_com} = {err_acus / max(1, err_com):.3f}")
        linhas.append(f"  precisão do alarme: {err_acus}/{alarme} = {err_acus / max(1, alarme):.3f}")
    for k, v in resumo.items():
        linhas.append(f"  {k[:40]:40s} {v}")
    texto = "\n".join(linhas)
    (R / "medida.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
