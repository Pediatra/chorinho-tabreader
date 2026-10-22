"""0211, diagnóstico depois da T8.4 (gasta): as notas não atacadas que o modelo lê atacadas.

Semente 1, dobra 0, recorte alto, L dos ouros, regra do slide sem origem (como o
``medir_t84``). Grava ``erros_t84/erros.json`` e um recorte por nota (círculo na nota,
retângulo na região do dono, a técnica prevista e as probabilidades).
"""

import json

import cv2

from tab import ataque_r4 as A
from tab import caminhos, detector_tab, leitor
from tab.gpu import trava_gpu

B = caminhos.TAB_ROTULO
GAB = B / "r2" / "conferir_t84" / "ataque_t84.json"
INDICE = caminhos.SAIDA / "t84" / "ferramenta" / "indice.json"
SAIDA = B / "r4g" / "erros_t84"


def main() -> int:
    """Lista e desenha os 'sim' falsos."""
    dec = json.loads((B / "r4g" / "decisao.json").read_text())
    versao = dec["escolhida"]; L = dec["versoes"][versao]["L"]
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text())}
    doc = json.loads(GAB.read_text())
    regioes = {}
    conf = json.loads((caminhos.SAIDA / "t84/passe_ataque/conferencia_t84_servida.json").read_text())
    for t in conf["telas"]:
        for k, r in enumerate(t.get("regioes") or []):
            regioes[f"t{t['id']}-r{k}"] = r
    gab = A.gabarito_por_tela(GAB)
    modelo = detector_tab.carregar(A.modelo_da_dobra(versao, 0, 1))
    erros = []
    for tela, notas in sorted(gab.items()):
        r = indice[tela]
        video = caminhos.acervo() / r["video"]
        pred, passo = A.ler_tela(modelo, video, float(r["t"]))
        pred = A.com_limiar(pred, L)
        pares = A.parear(notas, pred, passo)
        quadro = None
        for i, n in enumerate(notas):
            if n["ataque"] != "nao" or i not in pares:
                continue
            j = pares[i]
            if A.ataque_com_regra(pred, j, passo) != "sim":
                continue
            p = pred[j]
            e = {"nota": n["nota"], "tela": tela, "corda": n["corda"], "casa": n["casa"],
                 "motivo_dono": n["motivo"], "regiao": n.get("regiao"),
                 "tecnica_prevista": p["tecnica"],
                 "tecnica_p": {k: round(float(v), 3) for k, v in zip(detector_tab.TECNICAS_MODELO, p["tecnica_p"])}}
            erros.append(e)
            if quadro is None:
                quadro = leitor.quadro_em(str(video), float(r["t"]))
            im = quadro.copy(); x = int(n["x_centro_quadro"]); ps = passo
            ys = [int(round(y)) for y in p.get("linhas_y", [])] if p.get("linhas_y") else None
            reg = regioes.get(n.get("regiao") or "")
            if reg:
                cv2.rectangle(im, (int(min(reg["x_quadro"])), 0), (int(max(reg["x_quadro"])), im.shape[0] - 1), (0, 0, 255), 1)
            cv2.line(im, (x, 0), (x, im.shape[0] - 1), (255, 0, 255), 1)
            y0 = max(0, int(r.get("y", 0)) if False else 0)
            rec = im[:, max(0, x - int(8 * ps)): x + int(8 * ps)]
            cv2.imwrite(str(SAIDA / f"{n['nota']}.jpg"), rec)
    (SAIDA / "erros.json").write_text(json.dumps(erros, ensure_ascii=False, indent=1) + "\n")
    for e in erros:
        print(e["nota"], e["corda"], e["casa"], e["motivo_dono"], e["regiao"], "prev:", e["tecnica_prevista"],
              {k: v for k, v in e["tecnica_p"].items() if v >= 0.005})
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "diagnóstico T8.4 (~3 min)"):
        raise SystemExit(main())
