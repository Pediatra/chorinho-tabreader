"""Mede o detector de símbolo DE PONTA A PONTA, contra as marcas do dono.

Por que este módulo existe no repositório e não em `/tmp`: ele já foi perdido num reboot, e a medição que
ele faz é a única que responde se o caminho do símbolo melhorou. O `AGENTS.md` diz que caminho não se
espalha — e isso vale para os meus instrumentos.

A métrica mede **contra as marcas**, e isso é um **PISO de precisão**, não o valor real: a auditoria do
dono mostrou que 9 de 10 "falsos positivos" eram símbolos que ele **não tinha marcado**. Por isso o módulo
imprime o número com essa ressalva junto.

Uso:

    python -m tab.fimafim --marca data/gold/marcas_simbolos_6.json --jx 1.5 --jy 1.25
"""

import argparse
import glob
import json
import os
import pathlib
import sys

from .digito import carregar as carregar_discriminador
from .inventario import ler_quadro
from .painel import escolher
from .pipeline import roi_das_cordas
from .reconhecer import carregar_modelo, reconhecer_linha
from .simbolo import carregar as carregar_simbolo


def main() -> int:
    """Mede precisão e recall de ponta a frente contra as marcas e imprime o resumo."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--marca", default="data/gold/marcas_simbolos_6.json")
    ap.add_argument("--indice", default="data/saida/coleta_marcar/indice.json")
    ap.add_argument("--modelo", default="artefatos/oficial_2/glifo_sint.pt")
    ap.add_argument("--jx", type=float, default=1.2)
    ap.add_argument("--jy", type=float, default=0.8)
    ap.add_argument("--limiar2", type=float, default=0.5)
    args = ap.parse_args()

    modelo, rotulos, dev = carregar_modelo(args.modelo)
    filtro, disc = carregar_simbolo(), carregar_discriminador()
    indice = {
        r["arq"]: r
        for r in json.loads(pathlib.Path(args.indice).read_text(encoding="utf-8"))
    }
    marcas: dict[str, list[dict]] = {}
    for marca in json.loads(pathlib.Path(args.marca).read_text(encoding="utf-8"))[
        "marcas"
    ]:
        marcas.setdefault(marca["imagem"], []).append(marca)

    tp = fp = fn = 0
    for imagem, ms in sorted(marcas.items()):
        reg = indice.get(imagem)
        if reg is None:
            continue
        base = os.path.basename(str(reg["video"]))
        canal = reg["canal"]
        videos = [
            v
            for v in glob.glob(f"/acervo/{canal}/*.mp4")
            if os.path.basename(v).startswith(base[:24])
        ]
        if not videos:
            continue
        quadro, _ = ler_quadro(videos[0], reg["frac"])
        cand = escolher(quadro)
        if cand is None or not (14 <= cand.grade.passo <= 45):
            continue
        passo = cand.grade.passo
        y0, y1 = roi_das_cordas(cand)
        roi_y0 = cand.y0
        r = reconhecer_linha(
            cand.roi,
            modelo,
            rotulos,
            dev,
            discriminador=disc,
            filtro_simbolo=filtro,
            dir_simbolos=None,
            faixa_y=(y0 - roi_y0, y1 - roi_y0),
            julgar_todos=True,
            janela_simbolo=(args.jx, args.jy),
            limiar_simbolo2=args.limiar2,
        )
        aprovados = []
        for nota in r["notas"]:
            dados = nota.get("simbolo_cru")
            if not (isinstance(dados, dict) and "prob_simbolo" in dados):
                continue
            caixa = dados.get("caixa_token")
            if (
                nota.get("origem") == "simbolo"
                and isinstance(caixa, (list, tuple))
                and len(caixa) == 4
            ):
                x0, y0t, x1, y1t = caixa
            else:
                continue
            aprovados.append(((x0 + x1) // 2, (y0t + y1t) // 2 + roi_y0 - y0))
        usados: set[int] = set()
        for cx, cy in aprovados:
            casou = False
            for j, m in enumerate(ms):
                if j in usados:
                    continue
                if abs(cx - m["x"]) < 1.2 * passo and abs(cy - m["y"]) < 2.0 * passo:
                    usados.add(j)
                    casou = True
                    break
            tp += casou
            fp += not casou
        fn += len(ms) - len(usados)

    total = len(
        json.loads(pathlib.Path(args.marca).read_text(encoding="utf-8"))["marcas"]
    )
    print(f"marcas={total} | aprovados={tp + fp} | BATE={tp} nao={fp} nao_pego={fn}")
    if tp + fp:
        print(
            f"PRECISAO = {tp}/{tp + fp} = {tp / (tp + fp):.3f}  (PISO: a régua 'está em cima de uma "
            f"marca' perde símbolos, como a auditoria do dono mostrou)"
        )
    if tp + fn:
        print(f"RECALL    = {tp}/{tp + fn} = {tp / (tp + fn):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
