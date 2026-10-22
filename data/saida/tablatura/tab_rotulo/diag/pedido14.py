"""Pedido 14 da 2004: o "10" da corda 1 perdido no room 335, tela 20. É o recorte?

Lê o quadro em t=73 s com o leitor do produto (DETECTOR_PADRAO) e com o _atqa_s1, cada um
no recorte antigo (painel) e no alto, e imprime as notas da corda 1 (x, casa).
"""

from pathlib import Path

import cv2

from tab import caminhos, detector_tab, leitor, painel
from tab.gpu import trava_gpu

VIDEO = "shin izumi/【tab】room 335 - larry carlton  - fingerstyle guitar ソロギター【タブ】.mp4"
SAIDA = Path("/app/data/saida/tab_rotulo/diag/pedido14")


def main() -> int:
    """Lê e imprime."""
    q = leitor.quadro_em(str(caminhos.acervo() / VIDEO), 73.0)
    c = painel.escolher_ou_mascara(q)
    cv2.imwrite(str(SAIDA / "quadro.png"), q)
    modelos = {
        "produto": caminhos.DETECTOR_PADRAO,
        "atqa": caminhos.ARTEFATOS / "detector_tab_final_atqa_s1" / "modelo.pt",
    }
    for nome, arq in modelos.items():
        m = detector_tab.carregar(arq)
        for rec in ("painel", "alto"):
            roi, ly = (
                painel.recorte_alto(q, c) if rec == "alto" else (c.roi, c.grade.linhas_y)
            )
            notas = detector_tab.detectar(m, roi, ly, c.passo)
            c1 = sorted((round(float(n["x"])), n["rotulo"]) for n in notas if n["corda"] == 1)
            print(f"{nome} {rec}: {len(notas)} notas | corda 1: {c1}", flush=True)
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "diagnóstico pedido 14"):
        codigo = main()
    raise SystemExit(codigo)
