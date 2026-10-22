"""Diagnóstico: a T8.3 lida com o recorte de hoje e com um recorte mais alto, sem treinar.

O painel do produto deixa ~1 passo acima da corda 1 e abaixo da 6; o modelo lê 2,5 passos e
preenche o resto com a cor da borda. Aqui o recorte é aumentado no QUADRO até 2,5 passos de
cada lado (mesma grade, mesmas linhas), e os mesmos pesos (_atqt, dobra 0) leem de novo.
Conta como medir_t83 (L = 0,02) e mostra as 6 notas-alvo da 0208.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/diag/recorte_alto.py [versao]
"""

import json
import math
import sys
from collections import Counter

from tab import ataque_r4 as A
from tab import ataque_rotulo, caminhos, detector_tab, leitor, painel
from tab.ataque_base import parear

GAB = caminhos.TAB_ROTULO / "r2" / "conferir_t83" / "ataque_t83.json"
INDICE = caminhos.SAIDA / "t83" / "ferramenta" / "indice.json"
ALVOS = {"t24-n13", "t24-n14", "t25-n16", "t28-n17", "t28-n49", "t28-n50"}
L = 0.02


def ler(modelo, roi, linhas_y, passo, x0):
    """Notas previstas com x no quadro (como ataque_r4.ler_tela)."""
    return [
        {"corda": int(d["corda"]), "casa": str(d["rotulo"]), "tecnica": d["tecnica"],
         "x_centro_quadro": float(d["x"]) + x0, "tecnica_p": d["tecnica_p"]}
        for d in detector_tab.detectar(modelo, roi, linhas_y, passo, com_escores=True)
    ]


def main() -> int:
    versao = sys.argv[1] if len(sys.argv) > 1 else "atqt"
    indice = {int(r["id"]): r for r in json.loads(INDICE.read_text(encoding="utf-8"))}
    gab = A.gabarito_por_tela(GAB)
    quadros = {}
    for tela in sorted(gab):
        r = indice[tela]
        q = leitor.quadro_em(str(caminhos.acervo() / r["video"]), float(r["t"]))
        quadros[tela] = (q, painel.escolher_ou_mascara(q) if q is not None else None)
    for s in (1, 2, 3):
        modelo = detector_tab.carregar(A.modelo_da_dobra(versao, 0, s))
        soma = {"hoje": Counter(), "alto": Counter()}
        alvo = {"hoje": [], "alto": []}
        for tela, notas in sorted(gab.items()):
            q, c = quadros[tela]
            if c is None:
                continue
            ly, p = list(c.grade.linhas_y), float(c.passo)
            h, w = c.roi.shape[:2]
            cima = max(0, math.ceil(2.5 * p - ly[0]))
            baixo = max(0, math.ceil(ly[-1] + 2.5 * p - h))
            topo = max(0, c.y0 - cima)
            fim = min(q.shape[0], c.y0 + h + baixo)
            roi_alto = q[topo:fim, c.x0:c.x0 + w]
            ly_alto = [y + (c.y0 - topo) for y in ly]
            for modo, (roi, linhas) in {"hoje": (c.roi, ly), "alto": (roi_alto, ly_alto)}.items():
                pred = ler(modelo, roi, linhas, p, c.x0)
                soma[modo] += A.contar(notas, A.com_limiar(pred, L), p)
                rot = ataque_rotulo.rotular(pred, p)
                for i, j in parear(notas, pred, p).items():
                    if notas[i]["nota"] in ALVOS:
                        alvo[modo].append(f"{notas[i]['nota']}:{rot[j][0]}")
        for modo in ("hoje", "alto"):
            m = A.regra(soma[modo])
            print(f"{versao} s{s} {modo}: sim falso {m['nao|sim']}/{m['nao|sim'] + m['nao|nao']}"
                  f" custo {m['sim|nao']}/{m['sim|nao'] + m['sim|sim']}"
                  f" casa {soma[modo]['casa_certa']}/{soma[modo]['casadas']}"
                  f" | alvos {' '.join(sorted(alvo[modo]))}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
