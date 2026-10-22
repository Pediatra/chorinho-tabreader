"""Bancada de aferição do classificador de glifos de tablatura.

Pergunta que este script responde, com número: um modelo PEQUENO treinado em
alguns canais reconhece os algarismos de um canal NOVO (generalização entre
estilos de renderização)? Ou cada canal exige ajuste próprio?

Rotulagem: usa os tokens prata (tab_tokens.json) que acompanham os recortes —
(corda, casa, linha, t_instante). O alinhamento é feito por coluna (acorde) x
instante, e só entram casos em que o número de glifos bate com o número de notas.

Uso:
    python -m tab.glyph_bench --saida data/saida/glyphbench [--epocas 30]
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from tab.comum.caminhos import SAIDA
from tab.tablatura.leitura.glyphset import normalizar
from tab.tablatura.leitura.tabseg import limpar_glifo, segmentar

# --------------------------------------------------------------------------- #


def montar_dataset(padrao: str, verbose: bool = True) -> dict:
    """Casa os glifos segmentados com os tokens prata e devolve amostras rotuladas."""
    amostras = []
    estat = collections.Counter()
    for tok_path in sorted(glob.glob(padrao)):
        pasta = os.path.dirname(tok_path)
        clip = os.path.basename(pasta)
        with open(tok_path) as origem:
            tokens = json.load(origem)
        if not tokens:
            continue
        por_linha: dict[int, list[dict]] = collections.defaultdict(list)
        for t in tokens:
            por_linha[int(t.get("linha") or 0)].append(t)

        for linha, toks in sorted(por_linha.items()):
            img_path = os.path.join(pasta, f"linha_{linha:02d}_tablatura.png")
            if not os.path.exists(img_path):
                estat["sem_recorte"] += 1
                continue
            img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                continue
            g = segmentar(img)
            if len(g.linhas_y) != 6:
                estat["recorte_nao_e_tab"] += 1
                continue
            gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # casa por (corda, ordem no tempo) x glifo por (corda, ordem em x):
            # casar por corda é muito mais estável que casar por acorde.
            for corda in sorted({int(t["corda"]) for t in toks}):
                toks_c = sorted(
                    [t for t in toks if int(t["corda"]) == corda],
                    key=lambda t: float(t.get("t_instante") or 0),
                )
                glifos_c = sorted(
                    [gl for gl in g.glifos if int(gl.corda) == corda],
                    key=lambda gl: gl.x0,
                )
                if len(toks_c) != len(glifos_c):
                    estat["contagem_diferente_por_corda"] += 1
                    continue
                for gl, tk in zip(glifos_c, toks_c, strict=True):
                    casa = str(tk.get("glifo") or tk.get("casa"))
                    if not casa.isdigit() or len(casa) > 2:
                        estat["rotulo_estranho"] += 1
                        continue
                    crop = gray[
                        max(0, gl.y0 - 1) : gl.y1 + 1, max(0, gl.x0 - 1) : gl.x1 + 1
                    ]
                    crop = limpar_glifo(crop, g.passo)
                    norm = normalizar(crop)
                    if norm is None:
                        continue
                    amostras.append(
                        {
                            "img": norm,
                            "rotulo": casa,
                            "clip": clip,
                            "linha": linha,
                            "x": gl.x0,
                            "corda": int(gl.corda),
                        }
                    )
                    estat["ok"] += 1
    if verbose:
        print("montagem do conjunto:", dict(estat))
    return amostras


# --------------------------------------------------------------------------- #


class GlifoCNN(nn.Module):
    """Rede minúscula: ~40 mil parâmetros. Cabe em qualquer GPU e roda em tempo real."""

    def __init__(self, n_classes: int):
        super().__init__()
        self.c1 = nn.Conv2d(1, 16, 3, padding=1)
        self.c2 = nn.Conv2d(16, 32, 3, padding=1)
        self.c3 = nn.Conv2d(32, 64, 3, padding=1)
        self.fc = nn.Linear(64 * 3 * 2, 128)
        self.out = nn.Linear(128, n_classes)
        self.drop = nn.Dropout(0.15)

    def forward(self, x):
        x = F.max_pool2d(F.relu(self.c1(x)), 2)
        x = F.max_pool2d(F.relu(self.c2(x)), 2)
        x = F.max_pool2d(F.relu(self.c3(x)), 2)
        x = x.flatten(1)
        x = self.drop(F.relu(self.fc(x)))
        return self.out(x)


def treinar(amostras: list[dict], saida: str, epocas: int, seed: int = 0) -> dict:
    clips = sorted({a["clip"] for a in amostras})
    if len(clips) < 3:
        raise SystemExit("poucos canais para separar treino/teste")
    rng = np.random.default_rng(seed)
    teste_clips = set(
        rng.choice(clips, size=max(1, len(clips) // 4), replace=False).tolist()
    )
    treino = [a for a in amostras if a["clip"] not in teste_clips]
    teste = [a for a in amostras if a["clip"] in teste_clips]

    rotulos = sorted({a["rotulo"] for a in treino})
    idx = {r: i for i, r in enumerate(rotulos)}
    treino = [a for a in treino if a["rotulo"] in idx]
    teste = [a for a in teste if a["rotulo"] in idx]

    def tensor(itens):
        x = torch.tensor(
            np.stack([a["img"] for a in itens])[:, None].astype(np.float32) / 255.0
        )
        y = torch.tensor([idx[a["rotulo"]] for a in itens])
        return x, y

    xt, yt = tensor(treino)
    xv, yv = (
        tensor(teste) if teste else (torch.zeros(0), torch.zeros(0, dtype=torch.long))
    )
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = GlifoCNN(len(rotulos)).to(dev)
    nparam = sum(p.numel() for p in modelo.parameters())
    otim = torch.optim.AdamW(modelo.parameters(), lr=2e-3, weight_decay=1e-4)
    xt, yt, xv, yv = xt.to(dev), yt.to(dev), xv.to(dev), yv.to(dev)

    bs = 128
    hist = []
    for ep in range(epocas):
        modelo.train()
        perm = torch.randperm(len(xt), device=dev)
        perda_tot = 0.0
        for i in range(0, len(xt), bs):
            b = perm[i : i + bs]
            otim.zero_grad()
            logits = modelo(xt[b])
            perda = F.cross_entropy(logits, yt[b])
            perda.backward()
            otim.step()
            perda_tot += float(perda.detach()) * len(b)
        modelo.eval()
        with torch.no_grad():
            acc_tr = float((modelo(xt).argmax(1) == yt).float().mean())
            acc_te = (
                float((modelo(xv).argmax(1) == yv).float().mean())
                if len(xv)
                else float("nan")
            )
        hist.append(
            {
                "epoca": ep + 1,
                "perda": perda_tot / max(1, len(xt)),
                "acc_treino": acc_tr,
                "acc_teste": acc_te,
            }
        )
        if (ep + 1) % max(1, epocas // 5) == 0 or ep == 0:
            print(
                f"  época {ep + 1:>3}/{epocas}  perda={hist[-1]['perda']:.4f} "
                f"acc_treino={acc_tr:.4f}  acc_teste(canais novos)={acc_te:.4f}"
            )

    # matriz de confusão nos canais novos
    conf = collections.Counter()
    modelo.eval()
    with torch.no_grad():
        pred = modelo(xv).argmax(1).cpu().numpy() if len(xv) else np.zeros(0, int)
    reais = yv.cpu().numpy()
    for r, p in zip(reais, pred, strict=True):
        conf[(rotulos[r], rotulos[p])] += 1
    erros = sorted(
        ((v, k) for k, v in conf.items() if k[0] != k[1]), key=lambda x: -x[0]
    )[:15]

    os.makedirs(saida, exist_ok=True)
    torch.save(
        {"state_dict": modelo.state_dict(), "rotulos": rotulos, "parametros": nparam},
        os.path.join(saida, "glifo_cnn.pt"),
    )
    relatorio = {
        "historico": hist,
        "clips_treino": sorted(set(clips) - teste_clips),
        "clips_teste": sorted(teste_clips),
        "rotulos": rotulos,
        "n_treino": len(treino),
        "n_teste": len(teste),
        "parametros": nparam,
        "erros": [{"real": k[0], "previsto": k[1], "n": v} for v, k in erros],
    }
    with open(os.path.join(saida, "relatorio.json"), "w") as destino:
        json.dump(relatorio, destino, indent=1, ensure_ascii=False)
    return {
        "acc_treino": hist[-1]["acc_treino"],
        "acc_teste": hist[-1]["acc_teste"],
        "parametros": nparam,
        "n_treino": len(treino),
        "n_teste": len(teste),
        "clips_teste": sorted(teste_clips),
        "rotulos": rotulos,
        "erros": [{"real": k[0], "previsto": k[1], "n": v} for v, k in erros],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--padrao", default="parts/*/*/tab_tokens.json")
    ap.add_argument("--saida", default=str(SAIDA / "glyphbench"))
    ap.add_argument("--epocas", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    amostras = montar_dataset(args.padrao)
    if not amostras:
        print("nenhuma amostra rotulada", file=sys.stderr)
        return 2
    dist = collections.Counter(a["rotulo"] for a in amostras)
    print(
        f"amostras rotuladas: {len(amostras)}  classes: {len(dist)}  "
        f"top: {dist.most_common(8)}"
    )
    r = treinar(amostras, args.saida, args.epocas, args.seed)
    print(
        f"\nRESULTADO  parâmetros={r['parametros']}  treino={r['n_treino']}  teste={r['n_teste']}"
    )
    print(f"  acurácia treino ............. {r['acc_treino']:.4f}")
    print(
        f"  acurácia canais NOVOS ....... {r['acc_teste']:.4f}   (teste: {r['clips_teste']})"
    )
    print(
        f"  erros mais comuns: {[(e['real'], e['previsto'], e['n']) for e in r['erros'][:8]]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
