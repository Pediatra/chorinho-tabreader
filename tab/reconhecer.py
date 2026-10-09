"""Reconhecimento da linha de tablatura: tokens -> (corda, casa, tecnica) -> JSON.

Junta as três camadas numa ferramenta só:
  1. geometria (tabseg): grade, tokens por corda/coluna;
  2. classificador minúsculo treinado só em dado sintético (tools/sintetico.py);
  3. verificação de FORMA, que é o que impede o modelo de alucinar uma classe
     incompatível com o recorte (um "12" não cabe em meio passo; um harmônico <n>
     precisa de mais de um componente). Sem ela, a última nota do gabarito era
     classificada como "harmonico" e o acerto ficava em 14/15.

Uso:
    python -m tab.reconhecer IMAGEM [--modelo artefatos/glifo_sint.pt] [--json saida.json]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import statistics
import sys

import cv2
import numpy as np
import torch

from .caminhos import MODELO_PADRAO
from .glyph_bench import GlifoCNN
from .glyphset import normalizar
from .tabseg import segmentar


def compativel(classe: str, tk, passo: float) -> bool:
    """A classe prevista cabe no recorte medido?"""
    larg = (tk.x1 - tk.x0) / passo
    if classe.isdigit():
        # Piso de largura: um algarismo nao pode ter 2 px num painel de passo 21.6
        # (medido: fragmentos de barline de 2 px eram classificados como "1").
        if larg < 0.22:
            return False
        if len(classe) == 1:
            return larg <= 1.15
        # 2 dígitos exigem DOIS componentes com altura de algarismo: um "7" com a barra
        # de slide fundida no token fica largo e era aceito como "24" (erro medido no
        # canal raman korshun). O risco de slide é fino, não é dígito.
        return larg >= 0.85 and tk.partes_digito >= 2
    return True


def carregar_modelo(caminho: str):
    ck = torch.load(caminho)
    rot = ck["rotulos"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = GlifoCNN(len(rot)).to(dev)
    m.load_state_dict(ck["state_dict"])
    m.eval()
    return m, rot, dev


def reconhecer_linha(img: np.ndarray, modelo, rotulos, dev) -> dict:
    g = segmentar(img)
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tokens = sorted(g.glifos, key=lambda x: (x.coluna, x.corda))
    if not tokens:
        return {"passo": g.passo, "linhas_y": g.linhas_y, "notas": []}
    X = [
        normalizar(gray[max(0, t.y0 - 1) : t.y1 + 1, max(0, t.x0 - 1) : t.x1 + 1])
        for t in tokens
    ]
    X = [x if x is not None else np.zeros((24, 16), np.uint8) for x in X]
    xt = torch.tensor(np.stack(X)[:, None].astype(np.float32) / 255.0).to(dev)
    with torch.no_grad():
        probs = torch.softmax(modelo(xt), 1).cpu().numpy()
    # Assinatura de lixo POR VIDEO: fracao de tokens estreitos (< 0.3 passo). Medido:
    # apenas o canal raman korshun apresenta isso (28%); iwaki/sky/paolo dao 0%.
    # Onde ha assinatura, token estreito e recusado em vez de virar "1" ou "harmonico".
    estreitos = sum(1 for t in tokens if (t.x1 - t.x0) < 0.30 * g.passo)
    assinatura = estreitos / max(1, len(tokens))
    recusar = assinatura > 0.10
    notas = []
    for i, tk in enumerate(tokens):
        classe, corrigido = None, False
        if recusar and (tk.x1 - tk.x0) < 0.30 * g.passo:
            notas.append(
                {
                    "ordem": i + 1,
                    "corda": int(tk.corda),
                    "casa": "junk",
                    "tecnica": None,
                    "x": int(tk.x0),
                    "confianca": 0.0,
                    "corrigido_pela_forma": True,
                }
            )
            continue
        for k in np.argsort(-probs[i]):
            if compativel(rotulos[k], tk, g.passo):
                classe = rotulos[k]
                corrigido = bool(int(k) != int(np.argmax(probs[i])))
                break
        if classe is None:
            classe = rotulos[int(np.argmax(probs[i]))]
        tecnica = "harmonico" if classe == "harmonico" else None
        notas.append(
            {
                "ordem": i + 1,
                "corda": int(tk.corda),
                "casa": classe,
                "tecnica": tecnica,
                "x": int(tk.x0),
                "confianca": round(float(probs[i][int(np.argmax(probs[i]))]), 3),
                "corrigido_pela_forma": corrigido,
            }
        )
    return {
        "passo": round(g.passo, 2),
        "linhas_y": g.linhas_y,
        "barlines_x": g.barlines_x,
        "notas": notas,
    }


def completar(r: dict, tempos: list[tuple] | None = None) -> dict:
    """Acrescenta compasso (pelas barlines) e andamento (pelos onsets do cursor).

    Andamento honesto: o que a imagem e o cursor permitem medir é NOTAS POR MINUTO e
    quantas notas cabem em cada compasso. BPM só sai disso com uma suposição de figura
    (por isso vai separado, com o nome dizendo a suposição).
    """
    bl = r.get("barlines_x") or []
    for n in r["notas"]:
        n["compasso"] = 1 + sum(1 for bx in bl[1:] if bx < n["x"])
    por_compasso = {}
    for n in r["notas"]:
        por_compasso[n["compasso"]] = por_compasso.get(n["compasso"], 0) + 1
    r["notas_por_compasso"] = por_compasso
    if tempos and len(tempos) >= len(r["notas"]):
        onsets = [t[0] for t in tempos[: len(r["notas"])] if t and t[0] is not None]
        for n, t in zip(r["notas"], tempos, strict=False):
            if t and t[0] is not None:
                n["t_ini"] = round(t[0], 2)
                if t[1] is not None:
                    n["t_fim"] = round(t[1], 2)
        if len(onsets) > 2:
            dt = statistics.median([b - a for a, b in itertools.pairwise(onsets)])
            rpm = 60.0 / dt if dt > 0 else None
            r["andamento"] = {
                "notas_por_minuto": round(rpm, 1) if rpm else None,
                "intervalo_mediano_s": round(dt, 3),
                "notas_por_compasso_medido": round(
                    sum(por_compasso.values()) / max(1, len(por_compasso)), 2
                ),
                "bpm_se_1_nota_por_tempo": round(rpm, 1) if rpm else None,
            }
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("imagem")
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    ap.add_argument("--json")
    args = ap.parse_args()
    img = cv2.imread(args.imagem, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"não abri {args.imagem}", file=sys.stderr)
        return 2
    modelo, rotulos, dev = carregar_modelo(args.modelo)
    r = reconhecer_linha(img, modelo, rotulos, dev)
    r["fonte"] = os.path.basename(args.imagem)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:900])
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
