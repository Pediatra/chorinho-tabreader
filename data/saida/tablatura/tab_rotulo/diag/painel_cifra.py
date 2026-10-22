"""Diagnóstico: onde o painel do produto cai nos vídeos do cifra club (2026-10-21).

Na T8.4 (tela c01_v1), ``escolher_ou_mascara`` pegou o braço do violão (horizontal, no
topo) e perdeu a TAB escura embaixo; o produto leu 14 notas falsas. Aqui: 1 quadro por
vídeo do cifra club com tablatura no censo (o instante com tab mais perto do meio), e a
posição do candidato escolhido. Grava ``painel_cifra/medida.jsonl`` e miniaturas.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/diag/painel_cifra.py
"""

import json
from pathlib import Path

import cv2

from tab import caminhos, leitor, painel

CENSO = caminhos.SAIDA / "censo" / "censo_cache.jsonl"
SAIDA = Path("/app/data/saida/tab_rotulo/diag/painel_cifra")


def instante_central(rec: dict) -> float | None:
    """O instante com tab mais perto do meio da janela de tablatura (como t83/gerar.py)."""
    tabs = [i["t"] for i in rec["instantes"] if i.get("tab")]
    if not tabs:
        return None
    meio = (min(tabs) + max(tabs)) / 2
    return min(tabs, key=lambda t: abs(t - meio))


def main() -> int:
    """Mede e grava."""
    recs = [json.loads(linha) for linha in CENSO.open(encoding="utf-8") if linha.strip()]
    recs = sorted(
        (r for r in recs if r["canal"] == "cifra club" and r.get("tablatura")),
        key=lambda r: r["arquivo"],
    )
    SAIDA.mkdir(parents=True, exist_ok=True)
    with (SAIDA / "medida.jsonl").open("w", encoding="utf-8") as f:
        for k, r in enumerate(recs):
            t = instante_central(r)
            q = leitor.quadro_em(str(caminhos.acervo() / r["arquivo"]), t) if t else None
            linha = {"k": k, "arquivo": r["arquivo"], "t": t}
            if q is None:
                linha["erro"] = "sem quadro"
            else:
                c = painel.escolher_ou_mascara(q)
                linha["altura"] = int(q.shape[0])
                if c is None:
                    linha["painel"] = None
                else:
                    y0 = int(c.y0) + int(min(c.grade.linhas_y))
                    y1 = int(c.y0) + int(max(c.grade.linhas_y))
                    linha["painel"] = {"nome": c.nome, "y_corda1": y0, "y_corda6": y1,
                                       "passo": round(float(c.passo), 1),
                                       "centro_frac": round((y0 + y1) / 2 / q.shape[0], 3)}
                mini = cv2.resize(q, (480, int(480 * q.shape[0] / q.shape[1])))
                if c is not None:
                    s = 480 / q.shape[1]
                    cv2.rectangle(mini, (int(c.x0 * s), int(y0 * s)),
                                  (int((c.x0 + c.roi.shape[1]) * s), int(y1 * s)),
                                  (0, 255, 0), 2)
                cv2.imwrite(str(SAIDA / f"{k:03d}.jpg"), mini)
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
            f.flush()
            print(k, linha.get("painel"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
