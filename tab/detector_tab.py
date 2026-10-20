"""Detector de notas em sistemas de tablatura: um modelo que vê o sistema inteiro.

Entrada: uma imagem de sistema (6 cordas) já com a geometria do segmentador (`linhas_y`
e `passo`). A imagem é normalizada para passo de 16 px e altura de 160 px, e o modelo
devolve, para cada corda e cada coluna de 4 px normalizados, três mapas: centro da nota
(sigmoide), rótulo (26 classes: "0".."24" e "x") e técnicas (multirrótulo).

Por que um modelo e não regra: o problema "onde está a nota" depende do contexto
vertical (barline, haste de ritmo e acorde empilhado têm o mesmo traço na corda). O
backbone 2D vê o sistema inteiro antes de a corda ser amostrada.

Treino: dados gerados na hora por `tab.sintetico_sistema.gerar_sistema`, com semente
de dados derivada da semente do treino. Validação fixa: sementes de dados
10.000 a 10.299, nunca usadas no treino.

Uso:
    python -m tab.detector_tab treinar --semente 1 --passos 20000
    python -m tab.detector_tab avaliar-sintetico --modelo artefatos/detector_tab_s1/modelo.pt
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import multiprocessing as mp
import random
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from .caminhos import ARTEFATOS
from .sintetico import _resolver_fontes, fixar_semente
from .sintetico_sistema import ROTULOS, TECNICAS, gerar_sistema

#: Passo do sistema depois da normalização, em px.
PASSO_NORM = 16

#: Passos lidos acima da corda 1 e abaixo da 6 (``painel.FOLGA_DETECTOR_PASSOS`` igual).
MARGEM_PASSOS = 2.5
#: Altura do sistema normalizado: 10 passos (2,5 acima da corda 1 e 2,5 abaixo da 6).
ALTURA_NORM = 10 * PASSO_NORM

#: Passo, em px normalizados, da saída do modelo (uma coluna de saída a cada 4 px).
STRIDE = 4

#: Número de cordas.
N_CORDAS = 6

#: Posição, em px normalizados, do centro da coluna de saída j: STRIDE * j + DESLOC.
DESLOC = STRIDE / 2 - 0.5

#: Técnicas que o modelo aprende (TECNICAS sem a nota "sem técnica").
TECNICAS_MODELO = tuple(t for t in TECNICAS if t is not None)

#: Índice de cada rótulo e de cada técnica nas cabeças do modelo.
ROTULO_IDX = {rotulo: i for i, rotulo in enumerate(ROTULOS)}
TECNICA_IDX = {tecnica: i for i, tecnica in enumerate(TECNICAS_MODELO)}

#: Desvio do gaussiano do centro, em passo (0,15 passo, como no plano).
SIGMA_PASSO = 0.15

#: Raio, em bins de saída, em que a classe e a técnica são supervisionadas.
RAIO_CLASSE_BINS = 1.0

#: Largura do recorte de treino, em px normalizados.
LARGURA_TREINO = 512

#: Sistemas por lote de treino.
LOTE_PADRAO = 32

#: Taxa de aprendizado inicial (AdamW, cosseno).
TAXA_APRENDIZADO = 2e-3

#: Lotes gerados à frente do treino (pipeline de geração em processos).
PREFETCH = 8

#: Processos de geração de dados.
TRABALHADORES = 10

#: Passos entre duas avaliações sintéticas durante o treino.
AVALIACAO_CADA = 5000

#: Validação fixa: sementes de dados que o treino nunca usa.
SEMENTE_VALIDACAO_INICIO = 10_000
N_VALIDACAO = 300

#: Nomes das fontes do gerador de treino, todas do pacote `fonts-liberation` do
#: container. Sans e serif em regular e bold, mais Mono. Motivo: com só as Bold
#: (preset `padrao`) o "1" fino regular de fonte sans nunca aparecia no treino, e o
#: v2 lia esse "1" como "4" nos vídeos reais (27 casos no greensleeves, 33 no end of
#: beginning, 18 no retrato). O gerador separa serif de sans pelo nome ("Serif"),
#: então Mono entra como sans.
NOMES_FONTES_TREINO = (
    "LiberationSans-Regular.ttf",
    "LiberationSans-Bold.ttf",
    "LiberationSerif-Regular.ttf",
    "LiberationSerif-Bold.ttf",
    "LiberationMono-Regular.ttf",
    "LiberationMono-Bold.ttf",
)

#: Caminhos das fontes de treino, na ordem de `NOMES_FONTES_TREINO`.
FONTES_TREINO = _resolver_fontes(NOMES_FONTES_TREINO)

#: Limiar de probabilidade do centro e das técnicas na decodificação.
LIMIAR = 0.5

#: Janela de supressão de picos, em passo.
JANELA_NMS_PASSO = 0.5

#: Casamento entre predição e gabarito: |dx| em passo.
TOLERANCIA_PASSO = 0.5


def normalizar_sistema(
    img: np.ndarray, linhas_y: Sequence[float], passo: float
) -> tuple[np.ndarray, float, float]:
    """Normaliza um sistema para passo de 16 px e altura de 160 px.

    A imagem vira cinza, é invertida se o fundo for escuro (mediana menor que 128) e é
    reescalada por `16 / passo`. O recorte vertical vai de `linhas_y[0] - 2,5 passos`
    a `linhas_y[-1] + 2,5 passos`, em coordenadas de origem; onde o recorte sai da
    imagem, preenche-se com a cor da borda. A largura acompanha a escala (e é
    arredondada para cima ao múltiplo de 4, que o backbone exige).

    Args:
        img: imagem BGR (ou cinza) uint8, do sistema inteiro.
        linhas_y: y de cada corda na imagem original, da 1 (em cima) à 6.
        passo: distância vertical entre cordas, em px da imagem original.

    Returns:
        Tupla (array float32 de forma (160, largura) em [0, 1], com tinta escura,
        escala, y_topo). `escala` multiplica coordenadas originais para normalizadas;
        `y_topo` é o y da origem (imagem) que virou a linha 0 do array.
    """
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    if float(np.median(cinza)) < 128:
        cinza = 255 - cinza
    escala = PASSO_NORM / passo
    y_topo = float(linhas_y[0]) - MARGEM_PASSOS * passo
    largura = math.ceil(cinza.shape[1] * escala / STRIDE) * STRIDE
    borda = np.concatenate([cinza[0], cinza[-1], cinza[:, 0], cinza[:, -1]])
    matriz = np.float32([[escala, 0, 0], [0, escala, -escala * y_topo]])
    saida = cv2.warpAffine(
        cinza,
        matriz,
        (largura, ALTURA_NORM),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=float(np.median(borda)),
    )
    return saida.astype(np.float32) / 255.0, escala, y_topo


def x_para_original(x_norm: float | np.ndarray, escala: float) -> float | np.ndarray:
    """Converte x normalizado de volta para o x da imagem original.

    A normalização não corta na horizontal, então a conversão é só a escala.

    Args:
        x_norm: x em px normalizados (escalar ou array).
        escala: a escala devolvida por `normalizar_sistema`.

    Returns:
        x em px da imagem original, do mesmo tipo de `x_norm`.
    """
    return x_norm / escala


def alvos_do_sistema(
    notas: Sequence[dict],
    escala: float,
    largura_norm: int,
    arcos: Sequence[dict] = (),
) -> dict[str, np.ndarray]:
    """Monta os alvos de treino de um sistema, na grade de saída.

    Para cada nota (corda k, x do centro convertido pela escala), o centro é um
    gaussiano 1D de sigma 0,15 passo com pico exatamente 1 no bin mais próximo. A
    classe e a técnica valem nos bins a até 1 bin do centro; fora deles não há
    supervisão. Notas sem técnica têm multirrótulo zero.

    Args:
        notas: lista de {"corda" (1-6), "rotulo", "tecnica", "x"} do gerador (x em
            px da imagem original).
        escala: escala de `normalizar_sistema`.
        largura_norm: largura do array normalizado (múltiplo de 4).
        arcos: ``info["arcos"]`` do gerador ({"corda", "x_ini", "x_fim"}, px da imagem
            original). O alvo "arco" é 1 nos bins entre as duas pontas (rodada 0206).

    Returns:
        Dict com "centro" (6, L) float32, "classe" (6, L) int64 (-1 onde não há
        supervisão), "tecnica" (6, L, 10) float32 e "arco" (6, L) float32, com
        L = largura_norm // 4.
    """
    comprimento = largura_norm // STRIDE
    centro = np.zeros((N_CORDAS, comprimento), dtype=np.float32)
    classe = np.full((N_CORDAS, comprimento), -1, dtype=np.int64)
    tecnica = np.zeros((N_CORDAS, comprimento, len(TECNICAS_MODELO)), dtype=np.float32)
    bins = np.arange(comprimento)
    for nota in notas:
        k = int(nota["corda"]) - 1
        u = (float(nota["x"]) * escala - DESLOC) / STRIDE
        pico = int(np.clip(round(u), 0, comprimento - 1))
        gauss = np.exp(
            -((bins - pico) ** 2) / (2 * (SIGMA_PASSO * PASSO_NORM / STRIDE) ** 2)
        )
        centro[k] = np.maximum(centro[k], gauss.astype(np.float32))
        sup = np.flatnonzero(np.abs(bins - u) <= RAIO_CLASSE_BINS)
        classe[k, sup] = ROTULO_IDX[str(nota["rotulo"])]
        if nota["tecnica"] is not None:
            tecnica[k, sup, TECNICA_IDX[nota["tecnica"]]] = 1.0
    arco = np.zeros((N_CORDAS, comprimento), dtype=np.float32)
    for a in arcos:
        ua = (float(a["x_ini"]) * escala - DESLOC) / STRIDE
        ub = (float(a["x_fim"]) * escala - DESLOC) / STRIDE
        ja = max(0, math.ceil(min(ua, ub)))
        jb = min(comprimento - 1, math.floor(max(ua, ub)))
        if ja <= jb:
            arco[int(a["corda"]) - 1, ja : jb + 1] = 1.0
    return {"centro": centro, "classe": classe, "tecnica": tecnica, "arco": arco}


def _bloco2d(c_in: int, c_out: int, stride: int = 1, dilacao: int = 1) -> nn.Sequential:
    """Convolução 3x3 com BatchNorm e ReLU; `dilacao` só na vertical.

    Args:
        c_in: canais de entrada.
        c_out: canais de saída.
        stride: passo da convolução (2 reduz à metade em x e em y).
        dilacao: dilatação vertical (cresce o contexto em y, não em x).

    Returns:
        Módulo sequencial conv + BatchNorm2d + ReLU.
    """
    return nn.Sequential(
        nn.Conv2d(
            c_in,
            c_out,
            (3, 3),
            stride=stride,
            padding=(dilacao, 1),
            dilation=(dilacao, 1),
            bias=False,
        ),
        nn.BatchNorm2d(c_out),
        nn.ReLU(inplace=True),
    )


def _bloco1d(c: int, kernel: int) -> nn.Sequential:
    """Convolução 1D com BatchNorm e ReLU, preservando o comprimento.

    Args:
        c: canais de entrada e de saída.
        kernel: tamanho do núcleo (ímpar).

    Returns:
        Módulo sequencial conv1d + BatchNorm1d + ReLU.
    """
    return nn.Sequential(
        nn.Conv1d(c, c, kernel, padding=kernel // 2, bias=False),
        nn.BatchNorm1d(c),
        nn.ReLU(inplace=True),
    )


class DetectorTab(nn.Module):
    """Backbone 2D (stride 4) + amostragem por corda + convoluções 1D compartilhadas.

    Para cada corda k, a linha de features na altura (2,5 + k) * 16 / 4 é amostrada
    com os vizinhos de ±1 linha (concatenados), projetada para D canais e somada a um
    embedding da corda. As cabeças são: centro (1), classe (26), técnica (10) e arco (1,
    "bin debaixo de um arco desta corda", rodada 0206).
    """

    def __init__(self, c_back: int = 64, d: int = 128) -> None:
        """Monta o modelo.

        Args:
            c_back: canais do backbone no stride 4.
            d: canais do ramo 1D (um por corda, compartilhado).
        """
        super().__init__()
        self.tronco = nn.Sequential(
            _bloco2d(1, 32, stride=2),
            _bloco2d(32, 32),
            _bloco2d(32, c_back, stride=2),
            _bloco2d(c_back, c_back),
            _bloco2d(c_back, c_back, dilacao=2),
            _bloco2d(c_back, c_back, dilacao=4),
            _bloco2d(c_back, c_back, dilacao=8),
            _bloco2d(c_back, c_back, dilacao=16),
        )
        linhas = [
            [round((2.5 + k) * PASSO_NORM / STRIDE) + delta for delta in (-1, 0, 1)]
            for k in range(N_CORDAS)
        ]
        self.register_buffer("linhas", torch.tensor(linhas), persistent=False)
        self.proj = nn.Sequential(
            nn.Conv1d(3 * c_back, d, 1, bias=False),
            nn.BatchNorm1d(d),
            nn.ReLU(inplace=True),
        )
        self.embedding_corda = nn.Embedding(N_CORDAS, d)
        self.temporal = nn.Sequential(_bloco1d(d, 7), _bloco1d(d, 7), _bloco1d(d, 5))
        self.h_centro = nn.Conv1d(d, 1, 1)
        self.h_classe = nn.Conv1d(d, len(ROTULOS), 1)
        self.h_tecnica = nn.Conv1d(d, len(TECNICAS_MODELO), 1)
        self.h_arco = nn.Conv1d(d, 1, 1)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Calcula os quatro mapas de saída.

        Args:
            x: lote (B, 1, 160, W) float em [0, 1], com W múltiplo de 4.

        Returns:
            Dict com "centro" (B, 6, L) logits, "classe" (B, 6, L, 26) logits,
            "tecnica" (B, 6, L, 10) logits e "arco" (B, 6, L) logits, com L = W // 4.

        Raises:
            ValueError: se W não for múltiplo de 4.
        """
        if x.shape[-1] % STRIDE:
            raise ValueError(f"largura {x.shape[-1]} não é múltiplo de {STRIDE}")
        f = self.tronco(x)
        b, c, _, comprimento = f.shape
        amostra = f[:, :, self.linhas]  # (B, C, 6, 3, L)
        amostra = amostra.permute(0, 2, 1, 3, 4).reshape(
            b * N_CORDAS, c * 3, comprimento
        )
        h = self.proj(amostra)
        d = h.shape[1]
        h = h.view(b, N_CORDAS, d, comprimento)
        h = h + self.embedding_corda.weight[None, :, :, None]
        h = self.temporal(h.reshape(b * N_CORDAS, d, comprimento))
        centro = self.h_centro(h).view(b, N_CORDAS, comprimento)
        classe = self.h_classe(h).view(b, N_CORDAS, len(ROTULOS), comprimento)
        tecnica = self.h_tecnica(h).view(b, N_CORDAS, len(TECNICAS_MODELO), comprimento)
        arco = self.h_arco(h).view(b, N_CORDAS, comprimento)
        return {
            "centro": centro,
            "classe": classe.permute(0, 1, 3, 2),
            "tecnica": tecnica.permute(0, 1, 3, 2),
            "arco": arco,
        }


def perda_centro(logits: torch.Tensor, alvo: torch.Tensor) -> torch.Tensor:
    """Focal loss no estilo CenterNet (alfa 2, beta 4), normalizada pelos picos.

    Args:
        logits: logits do centro, qualquer forma.
        alvo: gaussiano com pico 1 em cada nota, mesma forma de `logits`.

    Returns:
        Escalar: soma da perda sobre o número de picos (mínimo 1).
    """
    p = torch.sigmoid(logits).clamp(1e-6, 1 - 1e-6)
    pos = alvo.eq(1.0).float()
    neg = (alvo < 1.0).float()
    perda_pos = ((1 - p) ** 2) * torch.log(p) * pos
    perda_neg = ((1 - alvo) ** 4) * (p**2) * torch.log(1 - p) * neg
    return -(perda_pos.sum() + perda_neg.sum()) / pos.sum().clamp(min=1.0)


def perda_total(
    saida: dict[str, torch.Tensor], alvos: dict[str, torch.Tensor]
) -> tuple[torch.Tensor, dict[str, float]]:
    """Soma as perdas: centro (focal), classe (CE), técnica (BCE) e arco (BCE).

    Classe e técnica só contam onde há supervisão (`classe >= 0`). O arco conta em
    todos os bins, e só quando os alvos trazem "arco".

    Args:
        saida: saída de `DetectorTab.forward`.
        alvos: lote de alvos (tensores com as mesmas formas de `alvos_do_sistema`).

    Returns:
        Tupla (perda total com grafo, dict com os valores float de cada parcela).
    """
    l_centro = perda_centro(saida["centro"], alvos["centro"])
    mascara = alvos["classe"] >= 0
    if bool(mascara.any()):
        l_classe = F.cross_entropy(saida["classe"][mascara], alvos["classe"][mascara])
        l_tecnica = F.binary_cross_entropy_with_logits(
            saida["tecnica"][mascara], alvos["tecnica"][mascara]
        )
    else:
        l_classe = l_tecnica = saida["centro"].sum() * 0.0
    total = l_centro + l_classe + l_tecnica
    parcelas = {
        "centro": float(l_centro.detach()),
        "classe": float(l_classe.detach()),
        "tecnica": float(l_tecnica.detach()),
    }
    if "arco" in alvos and "arco" in saida:
        l_arco = F.binary_cross_entropy_with_logits(saida["arco"], alvos["arco"])
        total = total + l_arco
        parcelas["arco"] = float(l_arco.detach())
    return total, parcelas


def _amostra_treino(semente: int) -> tuple[np.ndarray, ...]:
    """Gera um sistema de treino e devolve um recorte de 512 px com seus alvos.

    Tudo sai de um único `random.Random(semente)`, então a mesma semente dá sempre a
    mesma amostra, qualquer que seja o processo que a gera.

    Args:
        semente: semente de dados.

    Returns:
        Tupla (imagem (160, 512) float32, centro (6, 128) float32, classe (6, 128)
        int64, técnica (6, 128, 10) float32, arco (6, 128) float32).
    """
    rng = random.Random(semente)
    img, info = gerar_sistema(rng, FONTES_TREINO)
    arr, escala, _ = normalizar_sistema(img, info["linhas_y"], info["passo"])
    largura = arr.shape[1]
    alvos = alvos_do_sistema(info["notas"], escala, largura, info["arcos"])
    b0 = rng.randint(0, max(0, largura - LARGURA_TREINO) // STRIDE)
    x0 = b0 * STRIDE
    comp = LARGURA_TREINO // STRIDE
    mediana = float(np.median(arr))
    recorte = np.full((ALTURA_NORM, LARGURA_TREINO), mediana, dtype=np.float32)
    tam = min(LARGURA_TREINO, largura - x0)
    recorte[:, :tam] = arr[:, x0 : x0 + tam]
    centro = np.zeros((N_CORDAS, comp), dtype=np.float32)
    classe = np.full((N_CORDAS, comp), -1, dtype=np.int64)
    tecnica = np.zeros((N_CORDAS, comp, len(TECNICAS_MODELO)), dtype=np.float32)
    arco = np.zeros((N_CORDAS, comp), dtype=np.float32)
    n = min(comp, alvos["centro"].shape[1] - b0)
    if n > 0:
        centro[:, :n] = alvos["centro"][:, b0 : b0 + n]
        classe[:, :n] = alvos["classe"][:, b0 : b0 + n]
        tecnica[:, :n] = alvos["tecnica"][:, b0 : b0 + n]
        arco[:, :n] = alvos["arco"][:, b0 : b0 + n]
    return recorte, centro, classe, tecnica, arco


def _iniciar_trabalhador() -> None:
    """Inicializa um processo de geração: OpenCV de uma thread só."""
    cv2.setNumThreads(1)


def _dispositivo(modelo: nn.Module) -> torch.device:
    """Dispositivo dos parâmetros do modelo (CPU se não houver parâmetros).

    Args:
        modelo: qualquer `nn.Module`.

    Returns:
        O dispositivo do primeiro parâmetro, ou CPU.
    """
    for parametro in modelo.parameters():
        return parametro.device
    return torch.device("cpu")


def _decodificar(
    modelo: nn.Module, arr: np.ndarray, escala: float, com_escores: bool = False
) -> list[dict]:
    """Roda o modelo num sistema já normalizado e extrai as notas.

    Args:
        modelo: modelo com a mesma saída de `DetectorTab`.
        arr: sistema normalizado (160, W), W múltiplo de 4.
        escala: escala de `normalizar_sistema`.
        com_escores: inclui "tecnica_p", a probabilidade de cada técnica
            (``TECNICAS_MODELO``), para medir outro limiar sem reler (rodada 0203), e
            "arco_esq", a média do arco entre a nota anterior da mesma corda e esta
            (``None`` na primeira nota da corda; rodada 0206).

    Returns:
        Lista de {"corda", "rotulo", "tecnica", "x", "confianca"}, ordenada por corda
        e x; "x" em px da imagem original.
    """
    x = torch.from_numpy(arr)[None, None].to(_dispositivo(modelo))
    modo = modelo.training
    modelo.eval()
    try:
        with torch.no_grad():
            saida = modelo(x)
    finally:
        modelo.train(modo)
    centro = torch.sigmoid(saida["centro"][0]).cpu().numpy()
    classe = saida["classe"][0].cpu().numpy()
    tecnica = torch.sigmoid(saida["tecnica"][0]).cpu().numpy()
    arco = torch.sigmoid(saida["arco"][0]).cpu().numpy() if "arco" in saida else None
    notas: list[dict] = []
    for k in range(N_CORDAS):
        probs = centro[k]
        cand = np.flatnonzero(probs > LIMIAR)
        ordem = cand[np.argsort(-probs[cand], kind="stable")]
        aceitos: list[int] = []
        for j in ordem:
            if all(
                abs(int(j) - a) * STRIDE >= JANELA_NMS_PASSO * PASSO_NORM
                for a in aceitos
            ):
                aceitos.append(int(j))
        anterior = None
        for j in sorted(aceitos):
            notas.append(
                {
                    "corda": k + 1,
                    "rotulo": ROTULOS[int(np.argmax(classe[k, j]))],
                    "tecnica": [
                        TECNICAS_MODELO[i]
                        for i in np.flatnonzero(tecnica[k, j] > LIMIAR)
                    ],
                    "x": float(x_para_original(j * STRIDE + DESLOC, escala)),
                    "confianca": float(probs[j]),
                }
            )
            if com_escores:
                notas[-1]["tecnica_p"] = [round(float(v), 4) for v in tecnica[k, j]]
                notas[-1]["arco_esq"] = (
                    None
                    if anterior is None or arco is None
                    else round(float(arco[k, anterior : j + 1].mean()), 4)
                )
            anterior = j
    return notas


def detectar(
    modelo: nn.Module,
    img: np.ndarray,
    linhas_y: Sequence[float],
    passo: float,
    com_escores: bool = False,
) -> list[dict]:
    """Detecta as notas de um sistema de tablatura.

    Args:
        modelo: `DetectorTab` treinado (ou modelo com a mesma saída).
        img: imagem BGR do sistema inteiro.
        linhas_y: y de cada corda na imagem, da 1 (em cima) à 6.
        passo: distância vertical entre cordas, em px.
        com_escores: inclui "tecnica_p" em cada nota (ver `_decodificar`).

    Returns:
        Lista de {"corda" (1-6), "rotulo", "tecnica" (lista), "x" (px da imagem),
        "confianca" (probabilidade do centro)}.
    """
    arr, escala, _ = normalizar_sistema(img, linhas_y, passo)
    return _decodificar(modelo, arr, escala, com_escores)


def _contar_sistema(
    notas_gt: Sequence[dict],
    preds: Sequence[dict],
    passo: float,
    acum: collections.Counter,
) -> None:
    """Casa predições e gabarito por corda e soma os contadores da métrica.

    O casamento é guloso por distância em x, uma a uma, com |dx| <= 0,5 passo.
    Técnica (F1 micro) é contada só nos pares casados.

    Args:
        notas_gt: notas do gerador.
        preds: saída de `detectar`.
        passo: passo do sistema, em px.
        acum: contadores acumulados (alterado in place).
    """
    tol = TOLERANCIA_PASSO * passo
    for k in range(1, N_CORDAS + 1):
        gt = [n for n in notas_gt if int(n["corda"]) == k]
        pr = [p for p in preds if int(p["corda"]) == k]
        acum["n_gt"] += len(gt)
        acum["n_pred"] += len(pr)
        pares = sorted(
            (abs(p["x"] - g["x"]), i, j)
            for i, p in enumerate(pr)
            for j, g in enumerate(gt)
            if abs(p["x"] - g["x"]) <= tol
        )
        usado_p: set[int] = set()
        usado_g: set[int] = set()
        for _, i, j in pares:
            if i in usado_p or j in usado_g:
                continue
            usado_p.add(i)
            usado_g.add(j)
            g, p = gt[j], pr[i]
            acum["tp"] += 1
            certo = p["rotulo"] == g["rotulo"]
            acum["tp_rotulo"] += int(certo)
            pred_t = set(p["tecnica"])
            gt_t = {g["tecnica"]} - {None}
            acum["tec_tp"] += len(pred_t & gt_t)
            acum["tec_fp"] += len(pred_t - gt_t)
            acum["tec_fn"] += len(gt_t - pred_t)
            if len(g["rotulo"]) == 2:
                acum["dois_total"] += 1
                acum["dois_ok"] += int(certo)
            if g["rotulo"] == "x":
                acum["x_total"] += 1
                acum["x_ok"] += int(certo)


def _metricas(acum: collections.Counter) -> dict[str, float]:
    """Converte contadores em precisão, revocação, rótulo, técnica e recortes.

    Args:
        acum: contadores de `_contar_sistema`.

    Returns:
        Dict com precisao, revocacao, rotulo, tecnica_f1, revocacao_dois_algarismos
        e revocacao_x (estas duas: com o rótulo certo).
    """

    def razao(a: float, b: float) -> float:
        return a / b if b else float("nan")

    tp = acum["tp"]
    return {
        "precisao": razao(tp, acum["n_pred"]),
        "revocacao": razao(tp, acum["n_gt"]),
        "rotulo": razao(acum["tp_rotulo"], tp),
        "tecnica_f1": razao(
            2 * acum["tec_tp"],
            2 * acum["tec_tp"] + acum["tec_fp"] + acum["tec_fn"],
        ),
        "revocacao_dois_algarismos": razao(acum["dois_ok"], acum["dois_total"]),
        "revocacao_x": razao(acum["x_ok"], acum["x_total"]),
        "n_gt": float(acum["n_gt"]),
        "n_pred": float(acum["n_pred"]),
    }


def avaliar_sintetico(
    modelo: nn.Module, sementes: Sequence[int] | None = None
) -> dict[str, float]:
    """Mede o modelo nos sistemas de validação sintéticos.

    Args:
        modelo: modelo a medir (vira `eval()` durante a medição).
        sementes: sementes de dados; padrão são as 300 de validação fixa.

    Returns:
        Dict de `_metricas`.
    """
    if sementes is None:
        sementes = range(
            SEMENTE_VALIDACAO_INICIO, SEMENTE_VALIDACAO_INICIO + N_VALIDACAO
        )
    acum: collections.Counter = collections.Counter()
    for semente in sementes:
        img, info = gerar_sistema(random.Random(semente), FONTES_TREINO)
        preds = detectar(modelo, img, info["linhas_y"], info["passo"])
        _contar_sistema(info["notas"], preds, info["passo"], acum)
    return _metricas(acum)


def medir_validacao(
    modelo: nn.Module,
) -> dict[str, float]:
    """Métricas de validação com o modelo em modo de avaliação; devolve ao modo anterior.

    Args:
        modelo: modelo a medir.

    Returns:
        Mesmo dict de `avaliar_sintetico`.
    """
    modo = modelo.training
    modelo.eval()
    try:
        return avaliar_sintetico(modelo)
    finally:
        modelo.train(modo)


def treinar(
    semente: int,
    passos: int,
    lote: int = LOTE_PADRAO,
    saida: Path | None = None,
    comando: str = "",
) -> Path:
    """Treina o `DetectorTab` com dados gerados na hora e grava o artefato.

    Args:
        semente: semente do treino (fixa modelo e ordem; os dados vêm de
            `(semente + 1) * 10**9 + índice`, sem colidir com a validação).
        passos: passos de otimização.
        lote: sistemas por passo.
        saida: pasta de saída; padrão `artefatos/detector_tab_s{semente}`.
        comando: texto do comando, gravado em config.json.

    Returns:
        Caminho do `modelo.pt` gravado.
    """
    pasta = saida or ARTEFATOS / f"detector_tab_s{semente}"
    pasta.mkdir(parents=True, exist_ok=True)
    base = (semente + 1) * 10**9
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    contexto = mp.get_context("fork")
    with contexto.Pool(TRABALHADORES, initializer=_iniciar_trabalhador) as pool:
        fixar_semente(semente)
        modelo = DetectorTab().to(dispositivo)
        n_parametros = sum(p.numel() for p in modelo.parameters())
        opt = torch.optim.AdamW(modelo.parameters(), lr=TAXA_APRENDIZADO)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=passos)
        pendentes: collections.deque = collections.deque()

        def submeter(indice: int) -> None:
            sementes = [base + indice * lote + j for j in range(lote)]
            pendentes.append(pool.map_async(_amostra_treino, sementes, chunksize=2))

        for indice in range(PREFETCH):
            submeter(indice)
        print(f"parametros {n_parametros} | dispositivo {dispositivo}", flush=True)
        inicio = time.time()
        modelo.train()
        soma: collections.Counter = collections.Counter()
        for passo in range(passos):
            amostras = pendentes.popleft().get()
            submeter(passo + PREFETCH)
            imgs = torch.from_numpy(np.stack([a[0] for a in amostras])[:, None])
            alvos = {
                "centro": torch.from_numpy(np.stack([a[1] for a in amostras])),
                "classe": torch.from_numpy(np.stack([a[2] for a in amostras])),
                "tecnica": torch.from_numpy(np.stack([a[3] for a in amostras])),
                "arco": torch.from_numpy(np.stack([a[4] for a in amostras])),
            }
            alvos = {k: v.to(dispositivo) for k, v in alvos.items()}
            saida_modelo = modelo(imgs.to(dispositivo))
            perda, parcelas = perda_total(saida_modelo, alvos)
            opt.zero_grad(set_to_none=True)
            perda.backward()
            opt.step()
            sched.step()
            soma["perda"] += float(perda.detach())
            for nome, valor in parcelas.items():
                soma[nome] += valor
            if (passo + 1) % 500 == 0:
                medio = {k: v / 500 for k, v in soma.items()}
                soma.clear()
                print(
                    f"passo {passo + 1}/{passos} | "
                    + " ".join(f"{k} {v:.4f}" for k, v in medio.items())
                    + f" | lr {sched.get_last_lr()[0]:.2e}"
                    + f" | {time.time() - inicio:.0f} s",
                    flush=True,
                )
            if (passo + 1) % AVALIACAO_CADA == 0 and passo + 1 < passos:
                val = medir_validacao(modelo)
                print(f"validacao passo {passo + 1}: {json.dumps(val)}", flush=True)
        tempo = time.time() - inicio
        val = medir_validacao(modelo)
    caminho = pasta / "modelo.pt"
    torch.save(modelo.state_dict(), caminho)
    config = {
        "comando": comando,
        "semente": semente,
        "passos": passos,
        "lote": lote,
        "parametros": n_parametros,
        "tempo_s": round(tempo, 1),
        "vram_pico_mb": round(torch.cuda.max_memory_allocated() / 2**20, 1)
        if dispositivo.type == "cuda"
        else None,
        "validacao": val,
    }
    (pasta / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"validacao final: {json.dumps(val)}", flush=True)
    print(f"gravado {caminho}", flush=True)
    return caminho


def carregar(caminho: Path) -> DetectorTab:
    """Carrega um `DetectorTab` salvo por `treinar`.

    Args:
        caminho: arquivo `modelo.pt` (state_dict).

    Pesos de antes da rodada 0206 não têm a cabeça de arco: ela fica com o valor inicial
    (e o "arco" que ela devolve não significa nada).

    Returns:
        Modelo em modo de avaliação, no dispositivo disponível.

    Raises:
        RuntimeError: se faltar ou sobrar algum peso além da cabeça de arco.
    """
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    modelo = DetectorTab()
    r = modelo.load_state_dict(
        torch.load(caminho, map_location=dispositivo), strict=False
    )
    faltam = [k for k in r.missing_keys if not k.startswith("h_arco.")]
    if faltam or r.unexpected_keys:
        raise RuntimeError(
            f"pesos incompatíveis em {caminho}: faltam {faltam}, "
            f"sobram {r.unexpected_keys}"
        )
    return modelo.to(dispositivo).eval()


def _parser() -> argparse.ArgumentParser:
    """Monta o parser de linha de comando.

    Returns:
        Parser com os subcomandos `treinar` e `avaliar-sintetico`.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    treino = sub.add_parser("treinar", help="treina uma semente")
    treino.add_argument("--semente", type=int, required=True)
    treino.add_argument("--passos", type=int, default=20_000)
    treino.add_argument("--lote", type=int, default=LOTE_PADRAO)
    treino.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="pasta de saída (padrão artefatos/detector_tab_s{semente})",
    )
    avaliacao = sub.add_parser("avaliar-sintetico", help="mede na validação fixa")
    avaliacao.add_argument("--modelo", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI.

    Args:
        argv: argumentos (padrão: `sys.argv[1:]`).

    Returns:
        Código de saída (0 em sucesso).
    """
    args = _parser().parse_args(argv)
    comando_texto = "python -m tab.detector_tab " + " ".join(
        sys.argv[1:] if argv is None else argv
    )
    if args.comando == "treinar":
        treinar(
            args.semente,
            args.passos,
            lote=args.lote,
            saida=args.saida,
            comando=comando_texto,
        )
        return 0
    modelo = carregar(args.modelo)
    print(json.dumps(avaliar_sintetico(modelo), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
