"""Rodada 2021: cruzamento tela × som na T8.2 (fora do treino do leitor), com a regra ambigua.

Principal: as telas conferidas pelo dono em conferencia_t82.json, produtos e som da 2021.
Descritivo: acordes_2018 (já visto na 2020) recalculado com a regra ambigua.
Uso: sh data/saida/audio/r2017/podman_base.sh python data/saida/audio/r2021/medir.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/app")
from tab.audio import som_medir as M  # noqa: E402
from tab.comum.arquivos import nfc  # noqa: E402
from tab.cruzamento import cruzar_fontes as C  # noqa: E402
from tab.tablatura.ouro import avaliar_video as A  # noqa: E402

APP = Path("/app")
R = APP / "data/saida/audio/r2021"
T82 = APP / "data/saida/tablatura/t82/ferramenta"
R17 = APP / "data/saida/audio/r2017/produtos"
SOM19 = APP / "data/saida/audio/r2019/som_fl"
GOLD = APP / "data/gold"
CAPOS = json.loads(M.CAPO.read_text(encoding="utf-8"))
CAPOS_NFC = {"videos": [dict(v, arquivo=nfc(v["arquivo"])) for v in CAPOS["videos"]]}
ERRADAS = ("casa_errada", "inventada")


def ler(p: Path) -> dict:
    """Lê um JSON."""
    return json.loads(p.read_text(encoding="utf-8"))


def cruzado(produto: dict, som: dict) -> tuple[dict, int]:
    """Cruza produto e som do mesmo vídeo, com o capo do capo_por_video.json."""
    video = produto["video"]["arquivo"]
    assert nfc(video) == nfc(som["video"]), (video, som["video"])
    som = dict(som, video=video)
    capo = M.capo_do_video(nfc(video), CAPOS_NFC)
    return C.cruzar(produto, som, capo, str(CAPOS["fonte"])), capo


def status_das_notas(gold_notas: list, prod_notas: list, passo: float) -> list[str]:
    """certa / casa_errada / inventada para cada nota do produto (régua da 2020)."""
    gold = [g for g in gold_notas if not g.get("removida")]
    prev = [
        A.NotaPrevista(corda=n["corda"], casa=n["casa"], x=n["x"], t_ini=None)
        for n in prod_notas
    ]
    status = ["inventada"] * len(prod_notas)
    for i, j in A.casar_notas(gold, prev, A.FRACAO_PASSO * passo):
        igual = M.casa_inteira(gold[i]["casa"]) == prod_notas[j]["casa"]
        status[j] = "certa" if igual else "casa_errada"
    return status


def registrar(tab, erros, amostra, video, tela, notas, status) -> None:
    """Soma (amostra, veredito, status) e guarda as notas não certas."""
    for n, s in zip(notas, status, strict=True):
        tab[(amostra, n["veredito"], s)] += 1
        if s != "certa" or n["veredito"] == "ambigua":
            erros.append({
                "amostra": amostra, "video": video[:50], "tela": tela,
                "coluna": n["coluna"], "corda": n["corda"], "casa": n["casa"],
                "midi": n["midi"], "status": s, "veredito": n["veredito"],
            })


def principal(tab, erros, resumo) -> None:
    """A T8.2: cada tela conferida casada com a tela do produto que contém o instante."""
    conf = ler(T82 / "conferencia_t82.json")
    indice = {i["id"]: i for i in ler(T82 / "indice.json")}
    lista = {}
    for linha in (R / "lista.tsv").read_text(encoding="utf-8").splitlines():
        nome, video, _ = linha.split("\t")
        lista[nfc(video)] = nome
    for t in conf["telas"]:
        ind = indice[t["id"]]
        chave = f"tela {t['id']:02d}"
        if not t.get("conferida"):
            resumo[chave] = {"fora": "nao_conferida"}
            continue
        nome = lista.get(nfc(ind["video"]))
        if nome is None:
            resumo[chave] = {"fora": "video_ausente"}
            continue
        p_prod, p_som = R / "produtos" / f"{nome}.json", R / "som" / f"{nome}.json"
        if not (p_prod.exists() and p_som.exists()):
            resumo[chave] = {"fora": "sem_produto_ou_som"}
            continue
        prod = ler(p_prod)
        alvo = [
            x for x in prod["telas"]
            if x.get("passo") and any(e["t0"] <= ind["t"] <= e["t1"] for e in x["exibicoes"])
        ]
        if not alvo:
            resumo[chave] = {"fora": "sem_tela_no_instante", "video": nome[:40]}
            continue
        tp = alvo[0]
        cz, capo = cruzado(prod, ler(p_som))
        tc = next(x for x in cz["telas"] if x["tela"] == tp["id"])
        st = status_das_notas(t["notas"], tc["notas"], float(tp["passo"]))
        registrar(tab, erros, "t82", nome, tp["id"], tc["notas"], st)
        vered = Counter(n["veredito"] for n in tc["notas"])
        resumo[chave] = {"video": nome[:40], "capo": capo, "tela_produto": tp["id"],
                         "notas": len(st), **Counter(st), "vereditos": dict(vered)}


def descritivo(tab, erros, resumo) -> None:
    """acordes_2018 com a regra ambigua (produtos da 2017, som da 2019): não é prova."""
    ouro = ler(GOLD / "audio" / "acordes_2018.json")
    indice = {i["id"]: i for i in ler(APP / "data/saida/audio/r2018/ferramenta_acordes/indice.json")}
    for t in ouro["telas"]:
        if not t.get("conferida"):
            continue
        ind = indice[t["id"]]
        prod = ler(R17 / f"{ind['produto']}.json")
        cz, _ = cruzado(prod, ler(SOM19 / f"{ind['produto']}.json"))
        tc = next(x for x in cz["telas"] if x["tela"] == ind["tela_produto"])
        passo = float(next(x for x in prod["telas"] if x["id"] == ind["tela_produto"])["passo"])
        st = status_das_notas(t["notas"], tc["notas"], passo)
        registrar(tab, erros, "acordes_2018", ind["produto"], ind["tela_produto"], tc["notas"], st)
        resumo[f"2018 {ind['produto'][:30]}"] = dict(Counter(st))


def linhas_da_amostra(tab, amostra) -> list[str]:
    """A tabela veredito × status e K1, K2, custo da regra."""
    def n(v, s):
        return tab[(amostra, v, s)]
    out = [f"== {amostra}"]
    for v in C.VEREDITOS:
        out.append(f"  {v:15s} certa {n(v, 'certa'):5d}  casa_errada {n(v, 'casa_errada'):3d}"
                   f"  inventada {n(v, 'inventada'):3d}")
    ok, err = n("confirma", "certa"), sum(n("confirma", s) for s in ERRADAS)
    com = sum(n(v, s) for v in ("confirma", "nao_confirma", "coluna_sem_par", "ambigua") for s in ERRADAS)
    acus = sum(n(v, s) for v in ("nao_confirma", "coluna_sem_par") for s in ERRADAS)
    alarme = sum(n(v, s) for v in ("nao_confirma", "coluna_sem_par") for s in ("certa", *ERRADAS))
    out.append(f"  K1 erradas entre confirma: {err}/{ok + err} = {err / max(1, ok + err):.4f}")
    out.append(f"  K2 erros acusados: {acus}/{com} = {acus / max(1, com):.3f}")
    out.append(f"  precisão do alarme: {acus}/{alarme} = {acus / max(1, alarme):.3f}")
    out.append(f"  custo da regra (certa -> ambigua): {n('ambigua', 'certa')};"
               f" erradas pegas pela ambigua: {sum(n('ambigua', s) for s in ERRADAS)}")
    return out


def main() -> None:
    """Mede e grava medida.json e medida.txt."""
    tab, erros, resumo = Counter(), [], {}
    principal(tab, erros, resumo)
    descritivo(tab, erros, resumo)
    out = {"tabela": {"|".join(k): v for k, v in sorted(tab.items())}, "resumo": resumo,
           "erros": erros}
    (R / "medida.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    linhas = linhas_da_amostra(tab, "t82") + linhas_da_amostra(tab, "acordes_2018")
    linhas += [f"  {k:12s} {v}" for k, v in resumo.items()]
    texto = "\n".join(linhas)
    (R / "medida.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
