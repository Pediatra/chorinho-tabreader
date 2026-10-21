"""Mede o detector de símbolo DE PONTA A PONTA, contra as marcas do dono.

Existe no repositório (e não em `/tmp`) porque já foi perdido num reboot, e é a medição que responde se o
caminho do símbolo melhorou.

Duas coisas que este módulo faz de propósito, cada uma por um erro meu já cometido:

1. **Conta AS DUAS passadas** do `reconhecer_linha` — a primeira (tokens da grade, que trazem o símbolo
   junto do dígito) e a segunda (`origem == "simbolo"`, candidatos do caminho do símbolo). Contar só a
   segunda deu 29 aprovados onde a referência dava 178, e a comparação parecia não mudar nada.
2. **Imprime o caminho do modelo** que carregou. Sem isso, uma troca de `SAIDA_SIMBOLO` que não surtisse
   efeito passaria como "a mudança não ajudou".

A precisão é medida **contra as marcas** e isso é um **PISO**, não o valor real: a auditoria do dono
mostrou que 9 de 10 "falsos positivos" eram símbolos que ele **não tinha marcado**. O módulo imprime essa
ressalva junto do número.

Uso:

    python -m tab.fimafim --jx 1.5 --jy 1.25
"""

import argparse
import glob
import json
import os
import pathlib
import sys

from .caminhos import COLETA_MARCAR, GOLD_MARCAS_SIMBOLOS_6, PESOS_TABLATURA
from .digito import carregar as carregar_discriminador
from .inventario import ler_quadro
from .painel import escolher
from .pipeline import roi_das_cordas
from .reconhecer import carregar_modelo, reconhecer_linha
from .simbolo import carregar as carregar_simbolo


def main() -> int:
    """Mede precisão e recall de ponta a frente contra as marcas e imprime o resumo."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--marca", default=str(GOLD_MARCAS_SIMBOLOS_6))
    ap.add_argument("--indice", default=str(COLETA_MARCAR / "indice.json"))
    ap.add_argument(
        "--modelo", default=str(PESOS_TABLATURA / "oficial_2" / "glifo_sint.pt")
    )
    ap.add_argument("--jx", type=float, default=1.2)
    ap.add_argument("--jy", type=float, default=0.8)
    ap.add_argument("--limiar2", type=float, default=0.5)
    args = ap.parse_args()

    arq_simbolo = (
        pathlib.Path(os.environ.get("SAIDA_SIMBOLO", PESOS_TABLATURA))
        / "simbolo_2"
        / "simbolo.pt"
    )
    print(f"modelo de simbolo: {arq_simbolo} | existe={arq_simbolo.exists()}")
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
        videos = [
            v
            for v in glob.glob(f"/acervo/{reg['canal']}/*.mp4")
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
        gs = list(cand.grade.glifos)
        aprovados = []
        for i, nota in enumerate(r["notas"]):
            dados = nota.get("simbolo_cru")
            if not (isinstance(dados, dict) and "prob_simbolo" in dados):
                continue
            caixa = dados.get("caixa_token")
            if nota.get("origem") == "simbolo":
                if not (isinstance(caixa, (list, tuple)) and len(caixa) == 4):
                    continue
                x0, y0t, x1, y1t = caixa
            elif i < len(gs):
                x0, y0t, x1, y1t = gs[i].x0, gs[i].y0, gs[i].x1, gs[i].y1
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
    print(
        f"J={args.jx}x{args.jy} marcas={total} aprovados={tp + fp} BATE={tp} nao={fp} nao_pego={fn}"
    )
    if tp + fp:
        print(
            f"PRECISAO = {tp}/{tp + fp} = {tp / (tp + fp):.3f}  (PISO: a regua 'esta em cima de uma "
            f"marca' perde simbolos, como a auditoria do dono mostrou)"
        )
    if tp + fn:
        print(f"RECALL    = {tp}/{tp + fn} = {tp / (tp + fn):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
