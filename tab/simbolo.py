"""Detector POSITIVO de símbolo: "este recorte É um símbolo?".

A coleta antiga guardava o **resíduo** do classificador de algarismo ("tudo que não é
dígito"), e o resíduo de uma tablatura é ~98 % linha, borrão e dígito mal lido. Este detector
inverte a pergunta: só guarda o que tem evidência **positiva** de símbolo.

Verdade usada: `data/gold/simbolos_marcados.json` — o dono do projeto marcou 46 símbolos em 6
tablaturas com a ferramenta `data/saida/paineis/marcar.html`, com a regra explícita: *"tudo que
eu marquei é símbolo válido e o que eu não marquei não é símbolo válido"*. Isso dá 46 positivos
e 417 negativos, com o **mesmo enquadramento** (janela de 1,6 × passo centrada) nas duas
classes — caixa justa de um lado e janela do outro faria o modelo aprender a moldura.

Medido por canal deixado de fora (LOCA), 3 sementes:

| semente | símbolos pegos | lixo que passaria | exatidão equilibrada |
| --- | --- | --- | --- |
| 1 | 46/46 (1,00) | 2/417 (0,5 %) | 0,998 |
| 2 | 46/46 (1,00) | 4/417 (1,0 %) | 0,995 |
| 3 | 46/46 (1,00) | 3/417 (0,7 %) | 0,996 |

Baseline "nunca é símbolo": 417/463 = 0,901 de acurácia — por isso a métrica reportada é
**recall nos símbolos** e **falsos positivos**, nunca a acurácia bruta.

CLI:
    python -m tab.simbolo treinar --sementes 1 2 3
    python -m tab.simbolo loca --sementes 1 2 3
"""

from __future__ import annotations

import argparse
import collections
import json
import os

import cv2
import numpy as np
import torch
import torch.nn as nn

from tab.caminhos import ARTEFATOS
from tab.digito import DigitoCNN, preparar
from tab.sintetico import fixar_semente

GOLD_MARCADOS = ARTEFATOS.parent / "data" / "gold" / "simbolos_marcados.json"
PASTA = ARTEFATOS.parent / "data" / "gold" / "simbolos_marcados"


def montar_conjunto() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Monta o conjunto rotulado: positivos (marcados) e negativos (não marcados).

    Returns:
        ``(X, y, canais)`` com X em ``(n, 1, 32, 32)``, y em ``{0, 1}`` e o canal de cada amostra.
    """
    d = json.loads(GOLD_MARCADOS.read_text(encoding="utf-8"))
    X, y, canais = [], [], []
    for rotulo, chave in ((1.0, "positivos"), (0.0, "negativos")):
        for caso in d[chave]:
            arq = PASTA / chave / caso["arquivo"]
            img = cv2.imread(str(arq), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            X.append(preparar(img))
            y.append(rotulo)
            canais.append(caso["canal"])
    return (
        np.array(X, dtype=np.float32),
        np.array(y, dtype=np.float32),
        np.array(canais),
    )


def _treinar(
    X: np.ndarray, y: np.ndarray, seed: int, epocas: int = 80
) -> tuple[DigitoCNN, str]:
    """Treina o binário "é símbolo?" com peso de classe (46 positivos × 417 negativos).

    Args:
        X: recortes preparados.
        y: rótulo binário.
        seed: semente (determinismo travado por `tab.sintetico.fixar_semente`).
        epocas: passagens pelo conjunto.

    Returns:
        O modelo treinado e o dispositivo usado.
    """
    fixar_semente(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = DigitoCNN().to(dev)
    n_pos = float(y.sum())
    n_neg = float(len(y) - n_pos)
    crit = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor([max(1.0, n_neg / max(1.0, n_pos))], device=dev)
    )
    opt = torch.optim.Adam(modelo.parameters(), lr=1e-3)
    xt = torch.tensor(X).to(dev)
    yt = torch.tensor(y).to(dev)
    modelo.train()
    for _ in range(epocas):
        opt.zero_grad()
        perda = crit(modelo(xt)[:, 1], yt)
        perda.backward()
        opt.step()
    return modelo, dev


def _probabilidade(modelo: DigitoCNN, dev: str, X: np.ndarray) -> np.ndarray:
    """Probabilidade de "é símbolo" para cada recorte."""
    modelo.eval()
    with torch.no_grad():
        logits = modelo(torch.tensor(X).to(dev))[:, 1]
        return torch.sigmoid(logits).cpu().numpy()


def loca(sementes: list[int] | None = None) -> dict[int, dict[str, object]]:
    """Mede por canal deixado de fora e devolve o resultado por semente."""
    X, y, canais = montar_conjunto()
    n_pos = int(y.sum())
    print(
        f"conjunto: {len(X)} amostras | {n_pos} positivos | {len(X) - n_pos} negativos"
    )
    print(f"baseline 'nunca é símbolo' = {(len(X) - n_pos) / len(X):.3f} de acurácia")
    resultado: dict[int, dict[str, object]] = {}
    for seed in sementes or [1, 2, 3]:
        tp = fp = fn = tn = 0
        por_canal: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0, 0])
        for canal in sorted(set(canais.tolist())):
            teste = canais == canal
            modelo, dev = _treinar(X[~teste], y[~teste], seed)
            p = _probabilidade(modelo, dev, X[teste]) >= 0.5
            yy = y[teste].astype(bool)
            a = int((p & yy).sum())
            b = int((p & ~yy).sum())
            c = int((~p & yy).sum())
            e = int((~p & ~yy).sum())
            tp += a
            fp += b
            fn += c
            tn += e
            por_canal[canal] = [a, b, c, e]
        tpr = tp / max(1, tp + fn)
        tnr = tn / max(1, tn + fp)
        print(f"\nsemente {seed}: LOCA (canal deixado de fora)")
        print(f"  SÍMBOLOS pegos     {tp}/{tp + fn}  (recall {tpr:.2f})")
        print(f"  lixo que passaria  {fp}/{fp + tn}  (falso positivo {1 - tnr:.2f})")
        print(
            f"  exatidão equilibrada {(tpr + tnr) / 2:.3f} | acurácia bruta {(tp + tn) / len(y):.3f}"
        )
        for canal, (a, b, c, e) in sorted(por_canal.items()):
            print(f"    {canal[:16]:<18} símbolos {a}/{a + c} | falsos {b}/{b + e}")
        resultado[seed] = {
            "recall": tpr,
            "falso_positivo": 1 - tnr,
            "por_canal": dict(por_canal),
        }
    return resultado


def treinar(sementes: list[int] | None = None) -> None:
    """Treina em tudo e salva os pesos em `artefatos/simbolo_<semente>/simbolo.pt`."""
    X, y, _canais = montar_conjunto()
    for seed in sementes or [1, 2, 3]:
        modelo, _dev = _treinar(X, y, seed)
        destino = ARTEFATOS / f"simbolo_{seed}"
        os.makedirs(destino, exist_ok=True)
        torch.save(
            {"state_dict": modelo.state_dict(), "seed": seed, "tarefa": "simbolo"},
            destino / "simbolo.pt",
        )
        print(f"salvo {destino / 'simbolo.pt'}")


def carregar(caminho: str | None = None):
    """Carrega o detector treinado e devolve a função "isto é símbolo?".

    Args:
        caminho: peso `.pt`; por padrão usa o da semente 2 (a de melhor LOCA).

    Returns:
        Função que recebe uma lista de recortes em tons de cinza e devolve as probabilidades
        de "é símbolo". **O recorte tem de vir na janela do treino** (2,4 × 1,6 passo,
        centrado): a moldura é entrada do modelo, não detalhe de implementação.
    """
    destino = caminho or str(ARTEFATOS / "simbolo_2" / "simbolo.pt")
    estado = torch.load(destino, map_location="cpu", weights_only=False)
    modelo = DigitoCNN()
    modelo.load_state_dict(estado["state_dict"])
    modelo.eval()

    def _prob_simbolo(recortes: list[np.ndarray]) -> np.ndarray:
        X = np.array([preparar(r) for r in recortes], dtype=np.float32)
        with torch.no_grad():
            logits = modelo(torch.tensor(X))[:, 1]
            return torch.sigmoid(logits).numpy()

    return _prob_simbolo


def main() -> int:
    """Entrada de linha de comando."""
    ap = argparse.ArgumentParser(description="Detector positivo de símbolo.")
    ap.add_argument("acao", choices=["treinar", "loca"])
    ap.add_argument("--sementes", type=int, nargs="+", default=[1, 2, 3])
    args = ap.parse_args()
    if args.acao == "treinar":
        treinar(args.sementes)
    else:
        loca(args.sementes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
