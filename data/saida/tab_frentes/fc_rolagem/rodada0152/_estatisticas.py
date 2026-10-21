"""Estatística da 0152: erros (a), (b) e consenso por vídeo, contra a mão (só stdlib)."""

import json
import statistics
import sys
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset/data/saida/tab_frentes/fc_rolagem")


def ler_saltos(saltos_json: str) -> dict:
    """Mapa salto -> dx_consenso e n_passos, a partir do saltos.json da janela (caminho do container)."""
    caminho = RAIZ / Path(saltos_json).relative_to("/app/data/saida/tab_frentes/fc_rolagem")
    d = json.loads(caminho.read_text(encoding="utf-8"))
    return {
        k: {"consenso": s.get("dx_consenso"), "n_passos": s["n_passos"], "sobrepoe": s["sobreposicao"], "dx_b": s["dx_b_total"], "dx_a": s["dx_total"]}
        for k, s in enumerate(d["saltos"])
    }


def resumo(nome: str, mao_json: Path, escolhas_json: Path) -> None:
    """Imprime a tabela de um vídeo e os agregados.

    A referência (``mao_json``) sai na mesma ordem das escolhas (janela, depois salto),
    então cada linha recebe o ``saltos_json`` da sua janela pela ordem.
    """
    linhas = json.loads(mao_json.read_text(encoding="utf-8"))
    ordem = [w["saltos_json"] for w in json.loads(escolhas_json.read_text(encoding="utf-8")) for _ in w["escolhas"]]
    assert len(ordem) == len(linhas), (len(ordem), len(linhas))
    for l, sj in zip(linhas, ordem, strict=True):
        l["saltos_json"] = sj
    cache: dict = {}
    print(f"== {nome} ({len(linhas)} pares) ==")
    erros_a, erros_b, erros_c = [], [], []
    erros_a_v, erros_b_v = [], []
    indef = []
    grossos = []
    for l in linhas:
        if l["t0"] not in cache:
            cache[l["t0"]] = None
        info = ler_saltos(l["saltos_json"]) if "saltos_json" in l else None
        cons = None
        c = info.get(l["salto"]) if info else None
        if c:
            cons = c["consenso"]
        dxm = l["dx_mao"]
        ea, eb = l["erro_a"], l["erro_b"]
        if ea is not None:
            erros_a.append(ea)
        if eb is not None:
            erros_b.append(eb)
        valido = cons is not None
        ec = abs(cons - dxm) if (valido and dxm is not None) else None
        if valido:
            if ea is not None:
                erros_a_v.append(ea)
            if eb is not None:
                erros_b_v.append(eb)
            erros_c.append(ec)
            if ec > 5:
                grossos.append((l["t_antes"], ec))
        else:
            indef.append((l["t_antes"], "sem consenso"))
        print(f"  {l['t_antes']:8.2f} num={l.get('compasso')} mao={dxm:9.2f} a={l['dx_a']:9.2f} b={l['dx_b']} cons={cons} ea={ea if ea is None else round(ea,2)} eb={eb if eb is None else round(eb,2)} ec={ec if ec is None else round(ec,2)}")
    med = lambda v: round(statistics.median(v), 2) if v else None  # noqa: E731
    mx = lambda v: round(max(v), 2) if v else None  # noqa: E731
    print(f"  todos com estimativa: a mediana={med(erros_a)} max={mx(erros_a)} | b mediana={med(erros_b)} max={mx(erros_b)}")
    print(f"  validos (consenso): n={len(erros_c)} a mediana={med(erros_a_v)} max={mx(erros_a_v)} | b mediana={med(erros_b_v)} max={mx(erros_b_v)} | consenso mediana={med(erros_c)} max={mx(erros_c)}")
    print(f"  indefinidos: {len(indef)} {indef}")
    print(f"  validos com erro de consenso > 5 px: {grossos}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        nome, resto = arg.split("=", 1)
        mao, esc = resto.split(":", 1)
        resumo(nome, Path(mao), Path(esc))
