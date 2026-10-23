"""0214, depois da medida: os erros do ``_atqr_s1`` na T8.5 (já gasta), nota por nota.

Lê cada tela com o ``_atqr`` dobra 0 semente 1 e o ``L`` dos ouros, pareia com o
gabarito como ``tab.ataque_r4.contar`` e grava ``r4h/diag_t85/erros.json`` (os "sim"
falsos e o custo, com a técnica prevista e a probabilidade) e um recorte por erro.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tablatura/tab_rotulo/r4h/diagnostico_t85.py
"""

import json
from collections import Counter

import cv2

from tab.comum import caminhos, leitor
from tab.comum.gpu import trava_gpu
from tab.tablatura.ataque import r4 as A
from tab.tablatura.ataque.base import parear
from tab.tablatura.leitura import detector_tab, painel

R4H = caminhos.TAB_ROTULO / "r4h"
GAB = caminhos.TAB_ROTULO / "r2" / "conferir_t85" / "ataque_t85.json"
INDICE = caminhos.SAIDA / "tablatura" / "t85" / "ferramenta" / "indice.json"


def main() -> int:
    """Lista os erros, grava o JSON e os recortes."""
    saida = R4H / "diag_t85"
    (saida / "recortes").mkdir(parents=True, exist_ok=True)
    L = json.loads((R4H / "decisao.json").read_text(encoding="utf-8"))["versoes"][
        "atqr"
    ]["L"]
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    modelo = detector_tab.carregar(A.modelo_da_dobra("atqr", 0, 1))
    erros: list[dict] = []
    resumo: Counter = Counter()
    for tela, notas in sorted(A.gabarito_por_tela(GAB).items()):
        r = indice[tela]
        video = caminhos.acervo() / r["video"]
        pred, passo = A.ler_tela(modelo, video, float(r["t"]))
        pred = A.com_limiar(pred, L)
        pares = parear(notas, pred, passo)
        quadro = None
        for i, n in enumerate(notas):
            if i not in pares:
                continue
            j = pares[i]
            previsto = A.ataque_com_regra(pred, j, passo)
            if previsto == n["ataque"]:
                continue
            p = pred[j]
            tipo = "custo" if n["ataque"] == "sim" else "sim_falso"
            resumo[(tipo, n["motivo"], "+".join(sorted(p["tecnica"])) or "-")] += 1
            if quadro is None:
                quadro = leitor.quadro_em(str(video), float(r["t"]))
                c = painel.escolher_ou_mascara(quadro)
                linhas = [y + c.y0 for y in c.grade.linhas_y]
            nome = f"{tipo}_t{tela}_{n['nota']}.png"
            x = int(n["x_centro_quadro"])
            yc = int(linhas[int(n["corda"]) - 1])
            y0 = max(0, int(linhas[0] - 2.5 * passo))
            y1 = int(linhas[-1] + 2.5 * passo)
            x0 = max(0, x - int(5 * passo))
            recorte = quadro[y0:y1, x0 : x + int(5 * passo)].copy()
            cv2.circle(recorte, (x - x0, yc - y0), int(0.6 * passo), (0, 0, 255), 1)
            cv2.imwrite(str(saida / "recortes" / nome), recorte)
            erros.append(
                {
                    "tipo": tipo,
                    "tela": tela,
                    "nota": n["nota"],
                    "corda": n["corda"],
                    "casa": n["casa"],
                    "motivo": n["motivo"],
                    "tecnica_prevista": p["tecnica"],
                    "tecnica_p": dict(
                        zip(detector_tab.TECNICAS_MODELO, p["tecnica_p"], strict=True)
                    ),
                    "recorte": nome,
                }
            )
    (saida / "erros.json").write_text(
        json.dumps(erros, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for (tipo, motivo, tec), k in resumo.most_common():
        print(f"{k:4d} {tipo:9s} ouro {motivo:16s} previsto {tec}")
    print(f"{len(erros)} erros; L {L}")
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "diagnóstico T8.5"):
        codigo = main()
    raise SystemExit(codigo)
