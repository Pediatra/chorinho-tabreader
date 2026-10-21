"""Rodada 3026: a mediana de quadros recupera nota na pauta pequena?

Recortes conferidos pelo dono com entrelinha < 16 px (``resultado.json`` do medir.py).
Para cada um, duas leituras do Audiveris na condição ``x2_margem``:

- ``controle``: o PNG do item, sem mudança;
- ``mediana``: mediana pixel a pixel de até 15 quadros da mesma página, na caixa do
  recorte. Janela: a primeira exibição do índice, ou t ± 3 s se não houver. Só entram
  quadros parecidos com o quadro do instante t (diferença média < ``LIMIAR``), para não
  misturar página trocada.

Medidas: notas certas do dono ainda achadas (alinhamento, altura sem acidente), notas
lidas e ``extras`` (lidas que não casam com nota certa: nota recuperada ou inventada).
O teto de recuperação é o ``faltando`` do dono.

Uso (imagem localhost/chorinho-partitura:dev, na raiz):
python data/saida/partitura/diag/qualidade_imagem/mediana.py [--max N]
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_omr import rodar_um

from reduzir import GABARITOS, _achadas, _eventos, _notas_da_leitura

PASTA = Path(__file__).parent
MAXIMO_PX = 16.0
N_QUADROS = 15
LIMIAR = 12.0


def _entrada_do_indice(png: Path, rid: str) -> dict:
    """Entrada do indice.json ao lado do PNG."""
    indice = json.loads((png.parent / "indice.json").read_text(encoding="utf-8"))
    return next(e for e in indice if e.get("id") in (png.stem, rid))


def _mediana(entrada: dict) -> tuple[np.ndarray | None, dict]:
    """Mediana dos quadros parecidos com o do instante t, e o registro do que entrou."""
    caminho = str(acervo() / entrada["video"])
    x0, y0, x1, y1 = entrada["caixa_recorte"]
    exib = entrada.get("exibicoes") or [{"t0": entrada["t"] - 3, "t1": entrada["t"] + 3}]
    t0, t1 = exib[0]["t0"], exib[0]["t1"]
    ref = quadro_em(caminho, entrada["t"])
    if ref is None:
        return None, {"motivo": "sem quadro no instante t"}
    ref = ref[y0:y1, x0:x1].astype(np.float32)
    pilha, difs = [], []
    for k in range(N_QUADROS):
        quadro = quadro_em(caminho, t0 + (t1 - t0) * (k + 0.5) / N_QUADROS)
        if quadro is None:
            continue
        rec = quadro[y0:y1, x0:x1]
        dif = float(np.abs(rec.astype(np.float32) - ref).mean())
        difs.append(round(dif, 1))
        if dif < LIMIAR:
            pilha.append(rec)
    if len(pilha) < 3:
        return None, {"motivo": f"poucos quadros parecidos ({len(pilha)})", "difs": difs}
    med = np.median(np.stack(pilha), axis=0).astype(np.uint8)
    return med, {"quadros": len(pilha), "difs": difs, "janela": [t0, t1]}


def main() -> None:
    """Lê os recortes nas duas condições e grava ``mediana.json``."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=0)
    args = parser.parse_args()
    medidos = json.loads((PASTA / "resultado.json").read_text(encoding="utf-8"))
    pequenos = [m for m in medidos if m["entrelinha"] and m["entrelinha"] < MAXIMO_PX]
    if args.max:
        pequenos = pequenos[: args.max]
    linhas = []
    for m in pequenos:
        ouro = json.loads((RAIZ / GABARITOS[m["gabarito"]]).read_text(encoding="utf-8"))
        itens = json.loads((RAIZ / ouro["fonte_itens"]).read_text(encoding="utf-8"))
        item = next(i for i in itens["itens"] if i["id"] == m["id"])
        recorte = ouro["recortes"][m["id"]]
        certos = [
            s["palpite"]
            for s in recorte["simbolos"]
            if s["dono"] == "certo" and not s["palpite"].get("pausa")
            and not s["palpite"].get("graca")
        ]
        ref = _eventos(certos)
        png = RAIZ / item["png"]
        entrada = _entrada_do_indice(png, m["id"])
        linha = {"gabarito": m["gabarito"], "id": m["id"], "canal": m["canal"],
                 "entrelinha": m["entrelinha"], "certos_dono": sum(len(e) for e in ref),
                 "faltando_dono": len(recorte["faltando"])}
        med, registro = _mediana(entrada)
        linha["registro"] = registro
        origens = [("controle", png)]
        if med is not None:
            original = cv2.imread(str(png))
            if med.shape != original.shape:
                linha["registro"]["motivo"] = f"forma {med.shape} != {original.shape}"
            else:
                linha["registro"]["dif_png"] = round(float(np.abs(
                    med.astype(np.float32) - original.astype(np.float32)).mean()), 1)
                caminho_med = PASTA / "mediana" / f"{m['id']}.png"
                caminho_med.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(caminho_med), med)
                origens.append(("mediana", caminho_med))
        for condicao, origem in origens:
            reg = rodar_um("audiveris", "x2_margem", {"id": m["id"]},
                           PASTA / "leituras_mediana" / condicao, origem=origem)
            if not reg["ok"] or not reg.get("saida"):
                linha[condicao] = {"ok": False, "achadas": 0, "lidas": 0, "extras": 0}
            else:
                notas = _notas_da_leitura(RAIZ / reg["saida"])
                achadas = _achadas(ref, _eventos(notas))
                linha[condicao] = {"ok": True, "achadas": achadas, "lidas": len(notas),
                                   "extras": len(notas) - achadas}
        print(m["id"][:26], linha["certos_dono"], linha["faltando_dono"],
              linha.get("controle"), linha.get("mediana"), linha["registro"], flush=True)
        linhas.append(linha)
        (PASTA / "mediana.json").write_text(
            json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    pares = [x for x in linhas if "mediana" in x]
    print(f"com mediana: {len(pares)}/{len(linhas)}")
    for condicao in ("controle", "mediana"):
        ach = sum(x[condicao]["achadas"] for x in pares)
        ref = sum(x["certos_dono"] for x in pares)
        ok = sum(x[condicao]["ok"] for x in pares)
        lidas = sum(x[condicao]["lidas"] for x in pares)
        extras = sum(x[condicao]["extras"] for x in pares)
        print(f"{condicao}: saiu {ok}/{len(pares)}; certas achadas {ach}/{ref}; "
              f"lidas {lidas}; extras {extras}; faltando do dono "
              f"{sum(x['faltando_dono'] for x in pares)}")


if __name__ == "__main__":
    main()
