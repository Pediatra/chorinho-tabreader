"""Teste causal da rodada 3026: reduzir a pauta grande e ler de novo com o Audiveris.

Recortes conferidos pelo dono com entrelinha >= 16 px (``resultado.json`` do medir.py).
Para cada um, duas leituras na condição ``x2_margem`` (a mesma da conferência):

- ``controle``: o PNG do item, sem mudança (confere que o caminho reproduz a leitura);
- ``reduzido``: o PNG reduzido (INTER_AREA) até a entrelinha de 11 px.

Medida: das notas que o dono marcou ``certo`` na leitura original, quantas a nova leitura
ainda acha, por alinhamento de eventos (``alinhar``) com a altura sem acidente (letra e
oitava: a armadura herdada não entra nesta leitura). Também conta as notas lidas.

Uso (imagem localhost/chorinho-partitura:dev, na raiz):
python data/saida/partitura/diag/qualidade_imagem/reduzir.py [--max N]
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import cv2

from tab.caminhos import RAIZ
from tab.partitura_avaliar import alinhar
from tab.partitura_gabarito import ler_partitura
from tab.partitura_omr import rodar_um

PASTA = Path(__file__).parent
ALVO_PX = 11.0
MINIMO_PX = 16.0
GABARITOS = {
    "leitura_p1": "data/gold/partitura/leitura_p1.json",
    "leitura_sem_produto": "data/gold/partitura/leitura_sem_produto.json",
    "leitura_d1": "data/gold/partitura/leitura_d1.json",
}


def _diatonica(nome: str) -> str:
    """``F#4`` -> ``F4``: altura sem acidente."""
    return re.sub(r"[#b♯♭]+", "", nome)


def _eventos(simbolos: list[dict]) -> list[frozenset]:
    """Eventos (compasso, t) com as alturas sem acidente, na ordem."""
    grupos: dict[tuple, set] = defaultdict(set)
    for s in simbolos:
        grupos[(int(re.sub(r"\D", "", str(s["compasso"])) or 0), s["t"])].add(
            _diatonica(s["nome"])
        )
    return [frozenset(grupos[k]) for k in sorted(grupos)]


def _notas_da_leitura(musicxml: Path) -> list[dict]:
    """Notas (sem pausa e sem graça) de uma leitura, com compasso, t e nome."""
    leitura = ler_partitura(musicxml)
    return [
        {"compasso": c["numero"], "t": s["t"], "nome": s["nome"]}
        for c in leitura["compassos"]
        for s in c["simbolos"]
        if not s.get("pausa") and not s.get("graca")
    ]


def _achadas(ref: list[frozenset], lib: list[frozenset]) -> int:
    """Notas da referência achadas na leitura, pelos pares casados do alinhamento."""
    return sum(
        len(lib[i] & ref[j]) for op, i, j in alinhar(lib, ref) if op == "casa"
    )


def main() -> None:
    """Lê os recortes nas duas condições e grava ``reduzir.json``."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=0)
    args = parser.parse_args()
    medidos = json.loads((PASTA / "resultado.json").read_text(encoding="utf-8"))
    grandes = [m for m in medidos if m["entrelinha"] and m["entrelinha"] >= MINIMO_PX]
    if args.max:
        grandes = grandes[: args.max]
    linhas = []
    for m in grandes:
        ouro = json.loads((RAIZ / GABARITOS[m["gabarito"]]).read_text(encoding="utf-8"))
        itens = json.loads((RAIZ / ouro["fonte_itens"]).read_text(encoding="utf-8"))
        item = next(i for i in itens["itens"] if i["id"] == m["id"])
        certos = [
            {**s["palpite"]}
            for s in ouro["recortes"][m["id"]]["simbolos"]
            if s["dono"] == "certo" and not s["palpite"].get("pausa")
            and not s["palpite"].get("graca")
        ]
        ref = _eventos(certos)
        n_ref = sum(len(e) for e in ref)
        png = RAIZ / item["png"]
        imagem = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
        fator = ALVO_PX / m["entrelinha"]
        reduzido = cv2.resize(imagem, None, fx=fator, fy=fator, interpolation=cv2.INTER_AREA)
        caminho_red = PASTA / "reduzido" / f"{m['id']}.png"
        caminho_red.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(caminho_red), reduzido)
        linha = {"gabarito": m["gabarito"], "id": m["id"], "canal": m["canal"],
                 "entrelinha": m["entrelinha"], "fator": fator, "certos_dono": n_ref}
        for condicao, origem in (("controle", png), ("reduzido", caminho_red)):
            reg = rodar_um("audiveris", "x2_margem", {"id": m["id"]},
                           PASTA / "leituras" / condicao, origem=origem)
            if not reg["ok"] or not reg.get("saida"):
                linha[condicao] = {"ok": False, "achadas": 0, "lidas": 0}
            else:
                notas = _notas_da_leitura(RAIZ / reg["saida"])
                lib = _eventos(notas)
                linha[condicao] = {"ok": True, "achadas": _achadas(ref, lib),
                                   "lidas": len(notas)}
            print(m["id"][:26], condicao, linha[condicao], "de", n_ref, flush=True)
        linhas.append(linha)
        (PASTA / "reduzir.json").write_text(
            json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    for condicao in ("controle", "reduzido"):
        ach = sum(x[condicao]["achadas"] for x in linhas)
        ref = sum(x["certos_dono"] for x in linhas)
        ok = sum(x[condicao]["ok"] for x in linhas)
        lidas = sum(x[condicao]["lidas"] for x in linhas)
        print(f"{condicao}: leitura saiu {ok}/{len(linhas)}; achadas {ach}/{ref} = "
              f"{ach / max(1, ref):.3f}; notas lidas {lidas}")


if __name__ == "__main__":
    main()
