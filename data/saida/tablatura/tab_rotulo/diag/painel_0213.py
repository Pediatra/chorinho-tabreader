"""0213: regra antiga x nova do painel, no mesmo quadro, nas três amostras do pré-registro.

- desenho: os 197 quadros de ``painel_cifra/medida.jsonl`` (instante central);
- prova: 1 quadro novo por vídeo do cifra club, no instante com tab mais perto de 1/4 da
  janela de tablatura do censo;
- regressao: todas as telas conferidas dos 8 ouros, da T8.2 e da T8.3 (a T8.4 fica fora).

Grava ``painel_0213/<amostra>.jsonl`` e, para cada quadro que muda, uma miniatura com o
painel antigo (vermelho) e o novo (verde). Uso (container, sem GPU):
    env PYTHONPATH=/app CUDA_VISIBLE_DEVICES= python /app/data/saida/tab_rotulo/diag/painel_0213.py
"""

import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, "/app/data/saida/n3")

import medir as M  # noqa: E402
from tab import caminhos, leitor  # noqa: E402
from tab import painel as P  # noqa: E402

B = caminhos.TAB_ROTULO / "diag"
SAIDA = B / "painel_0213"
CENSO = caminhos.SAIDA / "censo" / "censo_cache.jsonl"


def pos(c: P.Candidato | None) -> dict | None:
    """Posição do painel no quadro (cordas 1 e 6, passo, x0)."""
    if c is None:
        return None
    y1, y6 = P._faixa_das_cordas(c)
    return {"nome": c.nome, "y_corda1": int(y1), "y_corda6": int(y6),
            "passo": round(float(c.passo), 1), "x0": int(c.x0),
            "largura": int(c.roi.shape[1])}


def velho_e_novo(q) -> tuple[P.Candidato | None, P.Candidato | None]:
    """O painel pela regra antiga e pela nova (0213), com um ``escolher`` só."""
    esc = P.escolher(q)
    if esc is None:
        c = P._primeira_tablatura([P._por_mascara(q)])
        return c, c
    if P._cordas_convergem(esc):
        achados = sorted(P.candidatos_escuros_estreitos(q), key=lambda t: -t[0])
        alt = P._primeira_tablatura([[c for _u, c in achados]])
        c = esc if alt is None else alt
        return c, c
    alt = P._tab_escura_em_outro_lugar(q, esc)
    return esc, esc if alt is None else alt


def amostras() -> dict[str, list[dict]]:
    """As três amostras: arquivo (relativo ao acervo ou absoluto) e instante."""
    desenho = [
        {"id": f"k{r['k']}", "arquivo": r["arquivo"], "t": r["t"]}
        for r in map(json.loads, (B / "painel_cifra" / "medida.jsonl").open())
        if r.get("t") is not None
    ]
    recs = sorted(
        (r for r in map(json.loads, CENSO.open(encoding="utf-8"))
         if r["canal"] == "cifra club" and r.get("tablatura")),
        key=lambda r: r["arquivo"],
    )
    prova = []
    for k, r in enumerate(recs):
        tabs = [i["t"] for i in r["instantes"] if i.get("tab")]
        if tabs:
            alvo = min(tabs) + (max(tabs) - min(tabs)) / 4
            prova.append({"id": f"k{k}", "arquivo": r["arquivo"],
                          "t": min(tabs, key=lambda t: abs(t - alvo))})
    regressao = []
    vids = dict(M.videos_do_run())
    extra = json.loads((M.OURO / f"{M.EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    vids.setdefault(M.EXTRA_SLUG, "/acervo/" + extra["video"])
    for slug, video in sorted(vids.items()):
        ouro = json.loads((M.OURO / f"{slug}.json").read_text(encoding="utf-8"))
        for t in ouro["telas"]:
            if t.get("conferida"):
                regressao.append({"id": f"{slug}#{t['id']}", "arquivo": video,
                                  "t": float(t["quadro_ref_s"])})
    for lote in ("t82", "t83"):
        ind = json.loads((caminhos.SAIDA / lote / "ferramenta" / "indice.json").read_text())
        for r in ind:
            regressao.append({"id": f"{lote}#{r['id']}", "arquivo": r["video"],
                              "t": float(r["t"])})
    return {"desenho": desenho, "prova": prova, "regressao": regressao}


def main() -> int:
    """Mede as três amostras e grava."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    for nome, itens in amostras().items():
        mudou = 0
        with (SAIDA / f"{nome}.jsonl").open("w", encoding="utf-8") as f:
            for it in itens:
                arq = it["arquivo"]
                caminho = arq if arq.startswith("/") else str(caminhos.acervo() / arq)
                q = leitor.quadro_em(caminho, float(it["t"]))
                if q is None:
                    f.write(json.dumps({**it, "erro": "sem quadro"}, ensure_ascii=False) + "\n")
                    continue
                v, n = velho_e_novo(q)
                linha = {**it, "altura": int(q.shape[0]), "velho": pos(v), "novo": pos(n),
                         "mudou": pos(v) != pos(n)}
                if linha["mudou"]:
                    mudou += 1
                    s = 480 / q.shape[1]
                    mini = cv2.resize(q, (480, int(q.shape[0] * s)))
                    for c, cor in ((v, (0, 0, 255)), (n, (0, 255, 0))):
                        if c is not None:
                            y1, y6 = P._faixa_das_cordas(c)
                            cv2.rectangle(mini, (int(c.x0 * s), int(y1 * s)),
                                          (int((c.x0 + c.roi.shape[1]) * s), int(y6 * s)),
                                          cor, 2)
                    rotulo = it["id"].replace("/", "_").replace("#", "_")
                    cv2.imwrite(str(SAIDA / f"{nome}_{rotulo}.jpg"), mini)
                f.write(json.dumps(linha, ensure_ascii=False) + "\n")
                f.flush()
        print(f"{nome}: {len(itens)} quadros, {mudou} mudaram", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
