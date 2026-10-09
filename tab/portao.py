"""Portão aprendido: este recorte é uma pauta de tablatura?

Por que um modelo e não uma regra: **quatro discriminadores feitos à mão foram medidos e
os quatro falharam** (ver `docs/decisoes/0005`). O detector aceitava como tablatura:

- **teclado de piano** (`violaodecria`) — uniformidade 0,856, "fração de algarismos" 0,20;
- **cabeça do violão com tarraxas** (`shin izumi`) — uniformidade 0,925, fração 0,28;
- **corpo do violão** (`cifra club`) — uniformidade **0,974**, a mais lisa de todas;
- **a partitura** (`guitar dell'arte`).

E a tablatura real de `sky4_t120` deu fração de algarismos **0,23** enquanto a cabeça do
violão deu **0,28**: não há regra que separe.

Aqui o portão é um classificador binário pequeno sobre o recorte do painel. Positivos do
**mesmo gerador sintético** que treina o classificador de glifos (pauta clara/escura,
linha sólida/tracejada, passo 14–36, acorde, rótulo `TAB`) mais os painéis reais
confirmados; negativos sintéticos (tecla larga, madeira com veio e cordas em diagonal,
pauta de 5 linhas com notas, bloco de texto) mais os negativos reais que a rodada achou.

Uso:
    python -m tab.portao treinar --n 3000 --epocas 12 --seed 1 --saida artefatos/portao_1
    python -m tab.portao avaliar --modelo artefatos/portao_1/portao.pt
"""

from __future__ import annotations

import argparse
import json
import os
import random

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .caminhos import ARTEFATOS
from .inventario import ler_quadro
from .painel import FAIXAS, escolher
from .sintetico import fixar_semente, gerar_linha

#: Tamanho fixo da entrada. Largo e baixo, como o painel; a distorção de aspecto é
#: aceitável porque o que decide é a ESTRUTURA (linhas finas + glifos entre elas).
ALTURA, LARGURA = 64, 256

#: Casos reais conferidos no olho — viram teste permanente.
POSITIVOS_REAIS: tuple[str, ...] = (
    "data/saida/frames/sky4_t88.png",
    "data/saida/frames/sky4_t120.png",
    "data/saida/frames/asturias_t417.png",
)
NEGATIVOS_REAIS: tuple[tuple[str, float], ...] = (
    ("data/saida/ouro_novos/03_violaodecria/auto.json", 0.0),
    ("data/saida/ouro_novos/02_shin izumi/auto.json", 0.0),
    ("data/saida/ouro_novos/00_cifra club/auto.json", 0.0),
    ("data/saida/ouro_novos/01_guitar dell ́a/auto.json", 0.0),
)


def preparar(roi: np.ndarray) -> np.ndarray:
    """Recorte do painel → entrada do portão (cinza, tamanho fixo, 0..1)."""
    cinza = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    redimensionado = cv2.resize(cinza, (LARGURA, ALTURA), interpolation=cv2.INTER_AREA)
    return (redimensionado.astype(np.float32) / 255.0)[None, :, :]


class PortaoCNN(nn.Module):
    """Rede pequena: decide se o recorte é pauta de tablatura."""

    def __init__(self) -> None:
        super().__init__()
        self.c1 = nn.Conv2d(1, 8, 3, padding=1)
        self.c2 = nn.Conv2d(8, 16, 3, padding=1)
        self.c3 = nn.Conv2d(16, 32, 3, padding=1)
        self.drop = nn.Dropout(0.15)
        self.fc1 = nn.Linear(32 * 8 * 32, 32)
        self.fc2 = nn.Linear(32, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Logits das duas classes."""
        x = F.max_pool2d(F.relu(self.c1(x)), 2)
        x = F.max_pool2d(F.relu(self.c2(x)), 2)
        x = F.max_pool2d(F.relu(self.c3(x)), 2)
        x = self.drop(x.flatten(1))
        return self.fc2(F.relu(self.fc1(x)))


def negativo_teclado(rng: random.Random) -> np.ndarray:
    """Teclado: teclas brancas separadas por barras pretas LARGAS."""
    img = np.full((200, 900), 235, np.uint8)
    x = rng.randint(0, 20)
    while x < 900:
        largura = rng.randint(18, 46)
        cv2.rectangle(img, (x, 30), (x + largura, 190), (25, 25, 25), -1)
        x += largura + rng.randint(30, 70)
    cv2.line(img, (0, 30), (900, 30), (60, 60, 60), 3)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def negativo_madeira(rng: random.Random) -> np.ndarray:
    """Cabeça/braço: madeira com veio e cordas em diagonal."""
    gerador = np.random.default_rng(rng.randint(0, 2**31 - 1))
    base = gerador.integers(70, 200, (200, 900), dtype=np.uint8)
    veio = cv2.GaussianBlur(base, (0, 0), 1.0)
    img = cv2.cvtColor(veio, cv2.COLOR_GRAY2BGR)
    for i in range(6):
        y = 20 + i * 30
        cv2.line(img, (0, y), (900, y + rng.randint(-40, 40)), (45, 45, 45), 2)
    return img


def negativo_pauta5(rng: random.Random) -> np.ndarray:
    """Partitura: 5 linhas finas com bolinhas (notas) — sem algarismos."""
    img = np.full((200, 900, 3), 250, np.uint8)
    for i in range(5):
        cv2.line(img, (20, 60 + i * 20), (880, 60 + i * 20), (40, 40, 40), 1)
    for _ in range(rng.randint(8, 20)):
        x, y = rng.randint(40, 860), rng.randint(60, 140)
        cv2.ellipse(img, (x, y), (7, 5), 20, 0, 360, (30, 30, 30), -1)
    return img


def negativo_texto(rng: random.Random) -> np.ndarray:
    """Cifra/letra: blocos de texto sem pauta nenhuma."""
    img = np.full((200, 900, 3), 235, np.uint8)
    for linha in range(6):
        x = rng.randint(10, 60)
        y = 25 + linha * 30
        while x < 880:
            largura = rng.randint(10, 40)
            if rng.random() < 0.8:
                cv2.rectangle(img, (x, y), (x + largura, y + 16), (50, 50, 50), -1)
            x += largura + rng.randint(8, 20)
    return img


def negativo_corpo(rng: random.Random) -> np.ndarray:
    """Corpo/mão: manchas grandes e gradiente — nada de linha regular."""
    img = np.zeros((200, 900, 3), np.uint8)
    img[:, :] = (120, 150, 190)
    for _ in range(rng.randint(3, 8)):
        centro = (rng.randint(0, 900), rng.randint(0, 200))
        eixos = (rng.randint(60, 260), rng.randint(40, 150))
        cor = (rng.randint(90, 220), rng.randint(90, 220), rng.randint(90, 230))
        cv2.ellipse(img, centro, eixos, rng.randint(0, 180), 0, 360, cor, -1)
    return cv2.GaussianBlur(img, (0, 0), 6)


NEGATIVOS_SINTETICOS = (
    negativo_teclado,
    negativo_madeira,
    negativo_pauta5,
    negativo_texto,
    negativo_corpo,
)


def fundo_de_video(rng: random.Random) -> np.ndarray:
    """Fundo parecido com quadro de vídeo: cor sólida, gradiente e manchas."""
    quadro = np.zeros((1080, 1920, 3), np.uint8)
    tom = rng.randint(20, 240)
    quadro[:, :] = (tom, tom, tom)
    for _ in range(rng.randint(2, 6)):
        centro = (rng.randint(0, 1920), rng.randint(0, 1080))
        eixos = (rng.randint(80, 400), rng.randint(60, 260))
        cor = tuple(rng.randint(20, 240) for _ in range(3))
        cv2.ellipse(quadro, centro, eixos, rng.randint(0, 180), 0, 360, cor, -1)
    return cv2.GaussianBlur(quadro, (0, 0), rng.uniform(2, 8))


def cena_em_quadro(cena: np.ndarray, rng: random.Random) -> np.ndarray:
    """Cola a cena numa faixa do quadro e devolve o recorte da FAIXA.

    É o mesmo recorte que o pipeline recebe em produção: largura total do quadro,
    altura da faixa, com fundo de vídeo em volta. Sem isto o portão aprende a separar
    "desenho limpo" de "desenho limpo" e não transfere para quadro real (medido: 0 de 3
    painéis reais com acurácia de treino 1,0000).
    """
    quadro = fundo_de_video(rng)
    _, y0, y1 = FAIXAS[rng.randrange(len(FAIXAS))]
    y1 = min(y1, quadro.shape[0])
    altura = y1 - y0
    largura = min(cena.shape[1], quadro.shape[1])
    fator = rng.uniform(0.8, 1.6)
    redimensionada = cv2.resize(
        cena, (int(largura * fator), max(8, int(cena.shape[0] * fator)))
    )
    if redimensionada.shape[0] > altura:
        redimensionada = cv2.resize(redimensionada, (redimensionada.shape[1], altura))
    x = rng.randint(0, max(0, quadro.shape[1] - redimensionada.shape[1]))
    y = y0 + rng.randint(0, max(0, altura - redimensionada.shape[0]))
    h = min(redimensionada.shape[0], altura, quadro.shape[0] - y)
    w = min(redimensionada.shape[1], quadro.shape[1] - x)
    if h >= 8 and w >= 8:
        quadro[y : y + h, x : x + w] = redimensionada[:h, :w]
    return quadro[y0:y1, :]


def montar_dataset(n_por_classe: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Monta o conjunto com o MESMO recorte que o pipeline vê em produção.

    Positivo: linha de tablatura do gerador posta numa faixa de um quadro de vídeo
    sintético. Negativo: cena que não é tablatura (teclado, madeira com veio, pauta de
    5 linhas, texto, corpo/mão) na mesma situação. Assim o portão aprende a decisão que
    vai de fato tomar, e não a diferença entre dois desenhos limpos.

    Args:
        n_por_classe: quantos exemplos de cada classe.
        seed: semente do sorteio.

    Returns:
        ``(X, y)`` com X em ``(N, 1, ALTURA, LARGURA)`` e y em ``{0, 1}``.
    """
    rng = random.Random(seed)
    X: list[np.ndarray] = []
    y: list[int] = []
    for _ in range(n_por_classe):
        linha, _ = gerar_linha(rng)
        X.append(preparar(cena_em_quadro(linha, rng)))
        y.append(1)
    for i in range(n_por_classe):
        desenhar = NEGATIVOS_SINTETICOS[i % len(NEGATIVOS_SINTETICOS)]
        X.append(preparar(cena_em_quadro(desenhar(rng), rng)))
        y.append(0)
    return np.stack(X), np.array(y)


def treinar(
    X: np.ndarray, y: np.ndarray, saida: str, epocas: int, seed: int, lote: int = 64
) -> tuple[PortaoCNN, str]:
    """Treina o portão.

    Args:
        X: entradas.
        y: rótulos (1 = tablatura).
        saida: diretório do modelo.
        epocas: passagens pelo conjunto.
        seed: semente (determinismo ligado por `fixar_semente`).
        lote: tamanho do lote.

    Returns:
        ``(modelo, dispositivo)``.
    """
    fixar_semente(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    xt = torch.tensor(X).to(dev)
    yt = torch.tensor(y).to(dev)
    modelo = PortaoCNN().to(dev)
    otim = torch.optim.AdamW(modelo.parameters(), lr=2e-3, weight_decay=1e-4)
    for ep in range(epocas):
        modelo.train()
        perm = torch.randperm(len(xt), device=dev)
        perda_tot = 0.0
        for i in range(0, len(xt), lote):
            b = perm[i : i + lote]
            otim.zero_grad()
            perda = F.cross_entropy(modelo(xt[b]), yt[b])
            perda.backward()
            otim.step()
            perda_tot += float(perda.detach()) * len(b)
        modelo.eval()
        with torch.no_grad():
            acc = float((modelo(xt).argmax(1) == yt).float().mean())
        if (ep + 1) % max(1, epocas // 4) == 0:
            print(
                f"  época {ep + 1:>3}/{epocas} perda={perda_tot / len(xt):.4f} "
                f"acc_treino={acc:.4f}",
                flush=True,
            )
    os.makedirs(saida, exist_ok=True)
    modelo.eval()
    torch.save({"state_dict": modelo.state_dict()}, os.path.join(saida, "portao.pt"))
    return modelo, dev


def carregar_modelo(caminho: str):
    """Carrega o portão do disco (em modo de avaliação)."""
    ck = torch.load(caminho)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = PortaoCNN().to(dev)
    modelo.load_state_dict(ck["state_dict"])
    modelo.eval()
    return modelo, dev


def probabilidade(rois: list[np.ndarray], modelo, dev) -> np.ndarray:
    """Probabilidade de ser tablatura para cada recorte."""
    xt = torch.tensor(np.stack([preparar(r)[0] for r in rois])[:, None]).to(dev)
    with torch.no_grad():
        return torch.softmax(modelo(xt), 1)[:, 1].cpu().numpy()


def _casos_reais() -> tuple[list[np.ndarray], list[int], list[str]]:
    """Recortes reais com verdade conferida no olho."""
    rois: list[np.ndarray] = []
    rotulos: list[int] = []
    nomes: list[str] = []
    for caminho in POSITIVOS_REAIS:
        img = cv2.imread(caminho)
        if img is None:
            continue
        c = escolher(img)
        if c is None:
            continue
        rois.append(c.roi)
        rotulos.append(1)
        nomes.append(os.path.basename(caminho))
    for caminho, _ in NEGATIVOS_REAIS:
        if not os.path.exists(caminho):
            continue
        with open(caminho, encoding="utf-8") as fh:
            auto = json.load(fh)
        quadro, _ = ler_quadro(f"/acervo/{auto['video']}", auto["instante_frac"])
        if quadro is None:
            continue
        c = escolher(quadro)
        if c is None:
            continue
        rois.append(c.roi)
        rotulos.append(0)
        nomes.append(os.path.basename(os.path.dirname(caminho)))
    return rois, rotulos, nomes


def avaliar(modelo, dev) -> dict:
    """Mede o portão nos casos reais e devolve o veredito por caso."""
    rois, rotulos, nomes = _casos_reais()
    if not rois:
        return {"casos": []}
    probs = probabilidade(rois, modelo, dev)
    casos = []
    for nome, real, p in zip(nomes, rotulos, probs, strict=True):
        casos.append(
            {
                "caso": nome,
                "verdade": "tablatura" if real else "nao_tablatura",
                "p_tablatura": round(float(p), 3),
                "acertou": bool((p >= 0.5) == bool(real)),
            }
        )
    acertos = sum(1 for c in casos if c["acertou"])
    return {"casos": casos, "acertos": acertos, "total": len(casos)}


def main() -> int:
    """Treina ou avalia o portão."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("acao", choices=["treinar", "avaliar"])
    ap.add_argument("--n", type=int, default=3000, help="exemplos por classe")
    ap.add_argument("--epocas", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--saida", default=str(ARTEFATOS / "portao"))
    ap.add_argument("--modelo", default=str(ARTEFATOS / "portao" / "portao.pt"))
    args = ap.parse_args()

    if args.acao == "treinar":
        X, y = montar_dataset(args.n, seed=args.seed)
        print(f"conjunto: {X.shape} | tablatura {int(y.sum())} de {len(y)}", flush=True)
        modelo, dev = treinar(X, y, args.saida, args.epocas, args.seed)
        print(f"\nmodelo salvo em {args.saida}", flush=True)
    else:
        modelo, dev = carregar_modelo(args.modelo)

    resultado = avaliar(modelo, dev)
    print(json.dumps(resultado, ensure_ascii=False, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
