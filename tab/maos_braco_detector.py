"""Detector do braço (rodada 1021, parte 2): U-Net, pós-processamento, medida e portões.

A rede recebe a faixa retificada de 1024 x 192 px e devolve 3 mapas de calor: a corda 1,
a corda 6 e os trastes com o nut. O pós-processamento transforma os mapas em retas e em
trastes numerados, e ``voltar`` leva as marcas ao quadro, onde ``erros`` e ``classificar``
medem contra o gabarito. Os dados vêm de ``tab.maos_braco_m21`` (S, R, G) e o rótulo de
cada faixa de ``tab.maos_braco_faixa``.

Experimentos (ver ``docs/rodadas/1021-piloto-detector-do-braco.md``): A1 treina só com S,
A2 só com R, A3 com S e R. A prova é por canal deixado de fora: na dobra k saem do treino
os R do canal k, e a medida é feita nos G do canal k. O G não entra em treino nenhum.

CLI: ``python -m tab.maos_braco_detector {v1,v2,v3,treinar,avaliar,rodar,resumo}``.
Rodada 1022: ``final --semente N`` (treino sem medida), ``d1``, ``d2``, ``d3`` (portões
de desenvolvimento) e ``prova`` (M11b lacrada; só com o aval do dono).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import random
import statistics
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np
import torch
import torchvision
from torch import nn
from torch.utils.data import DataLoader, Dataset

from .caminhos import (
    ARTEFATOS,
    GABARITO_BRACO,
    GABARITO_BRACO_M11B,
    MAOS_M11B,
    MAOS_M21,
)
from .gpu import trava_gpu
from .maos_braco_faixa import (
    ALTURA_FAIXA,
    LARGURA_FAIXA,
    eixo_da_faixa,
    matriz_da_faixa,
    perturbar,
    recortar,
    rotulo_na_faixa,
    voltar,
)
from .maos_braco_m21 import QUADROS_PELE
from .maos_braco_regra import N_MAXIMO, s_do_traste
from .maos_braco_sintetico import conferir_fora_m11b, gerar, videos_proibidos
from .maos_braco_tempo import Marcas, classificar, erros, marcas_do_registro
from .sintetico import fixar_semente

#: Semente da rodada 1021 (prefixo de todos os sorteios).
SEMENTE = 20261021
#: Passos de treino (fixos para todos os experimentos; V4 pode reduzir antes de G).
PASSOS = 3000
#: Piso de passos depois do corte do V4 (emenda 5 da 1021).
PASSOS_MINIMO = 2000
#: Amostras por passo.
LOTE = 16
#: Passos e amostras do teste de sobreajuste (V2).
PASSOS_V2 = 1000
AMOSTRAS_V2 = 32
#: Emenda 3: trabalhadores de dados no V2 (a máquina estava saturada).
TRABALHADORES_V2 = 2
#: Emenda 3: cores dos canais na folha, em BGR: corda 1, corda 6, trastes, nut.
CORES_CANAIS = ((0, 0, 255), (255, 0, 0), (0, 255, 255), (0, 255, 0))
#: Amostras S fora do treino para a validação (V3).
AMOSTRAS_SVAL = 500
#: Otimização.
LR_DECODIFICADOR = 3e-4
LR_CODIFICADOR = 1e-4
AQUECIMENTO = 200
PESO_POSITIVO = 20.0
#: Alvo: crista gaussiana, em px.
SIGMA_CRISTA_PX = 2.0
#: Pós-processamento (valores do pré-registro; ver as notas de cada função).
LIMITE_CRISTA = 0.3
LIMITE_RANSAC_CORDA_PX = 2.0
ITERACOES_RANSAC_CORDA = 500
MINIMO_INLIERS_CORDA = 20
ALTURA_PICO_MINIMA = 0.2
DISTANCIA_PICO_MINIMA_PX = 8
#: Suavização do perfil antes de achar os picos, em px (emenda 4).
SIGMA_PERFIL_PX = 1.5
#: Emenda 2: numeração por ordem. Pico do nut abaixo disto é "não achou".
LIMITE_NUT = 0.3
#: Emenda 2: intervalo maior que este fator vezes o espaço esperado é salto.
FATOR_SALTO = 1.6
#: Razão entre vizinhos (2^(-1/12)): o espaço do traste n+1 é este vezes o do n.
RAZAO_ESPACO = 2.0 ** (-1.0 / 12.0)
#: Emenda 2: com menos trastes detectados que isto, "não achou".
MINIMO_TRASTES = 4
#: Decodificador v2 (rodada 1022): tolerância do inlier, em fração do espaço local.
TOLERANCIA_V2 = 0.25
#: Decodificador v2: maior número de traste nas hipóteses.
N_MAX_V2 = 20
#: Decodificador v2: inliers mínimos para achar o braço.
MIN_INLIERS_V2 = 4
#: Oráculo (V1): logit alto na crista e baixo fora dela.
LOGIT_CRISTA = 12.0
LOGIT_FUNDO = -6.0
#: Limites dos portões.
LIMITE_V1 = 0.95
LIMITE_V2_QUEDA = 10.0  # Emenda 3: (perda - piso) cai pelo menos 10 vezes
LIMITE_V2_CERTO = 0.90
LIMITE_V3_CERTO = 0.50
ORCAMENTO_HORAS = 10.0
#: Processos de leitura de dados por treino.
PROCESSOS_DADOS = 6
#: Processos que geram o S de validação: o gerador desenha em 4x e 6 estouram a memória.
PROCESSOS_SVAL = 2
#: Canais: cordas, trastes (sem o nut) e nut (Emenda 2: 4 canais).
CANAL_CORDA1 = 0
CANAL_CORDA6 = 1
CANAL_TRASTES = 2
CANAL_NUT = 3
CANAIS_ALVO = 4
#: Normalização ImageNet (RGB).
MEDIA_IMAGENET = (0.485, 0.456, 0.406)
DESVIO_IMAGENET = (0.229, 0.224, 0.225)
#: Pesos ImageNet já baixados (sem download).
PESOS_RESNET18 = ARTEFATOS / "torch" / "hub" / "checkpoints" / "resnet18-f37072fd.pth"
DIR_PESOS = ARTEFATOS / "m21"
DIR_G = MAOS_M21 / "G"
DIR_R = MAOS_M21 / "R"
DIR_S = MAOS_M21 / "S"
DIR_FUNDOS = MAOS_M21 / "fundos"
DIR_RESULTADOS = MAOS_M21 / "resultados"
ARQUIVO_RESUMO = MAOS_M21 / "resumo.json"
ARQUIVO_V1 = MAOS_M21 / "v1_oraculo.json"
ARQUIVO_V2 = MAOS_M21 / "v2_sobreajuste.json"
ARQUIVO_V3 = MAOS_M21 / "v3_validacao_s.json"
ARQUIVO_V4 = MAOS_M21 / "v4_tempo.json"
#: Variável de ambiente que manda a inferência para a CPU (GPU fora do ar).
VARIAVEL_CPU = "CHORINHO_MAOS_CPU"
#: Rodada 1022: portões de desenvolvimento, prova e semente da perturbação.
ARQUIVO_D1 = MAOS_M21 / "d1_oraculo_v2.json"
ARQUIVO_D2 = MAOS_M21 / "d2_r_fora.json"
ARQUIVO_D3 = MAOS_M21 / "d3_sval.json"
ARQUIVO_PROVA = MAOS_M21 / "prova_m11b.json"
SEMENTE_D2 = "20261022:D2"
SEMENTE_PROVA = "20261021:T"
#: Sementes do treino final (A3 sem dobra, com todos os R).
SEMENTES_FINAIS = (1, 2, 3)
#: Critério da prova (pela média das sementes), em porcentagem.
LIMITE_PROVA_CERTO = 70.0
LIMITE_PROVA_FALSO = 5.0
#: Quadros da prova M11b (pré-registro 1022): 8 quadros-chave e 20 alvos.
QUADROS_PROVA = (
    "q01",
    "q41",
    "q11",
    "q16",
    "q21",
    "q26",
    "q31",
    "q36",
    *(f"q{n}" for n in range(46, 62)),
    "q65",
    "q69",
    "q73",
    "q74",
)
#: Plano da rodada (Emenda 1): tamanho das misturas por passo (S, R).
MISTURA = {"A1": (LOTE, 0), "A2": (0, LOTE), "A3": (LOTE // 2, LOTE // 2)}
#: Frações de vídeos de R, por nome.
FRACOES = {"100": 1.0, "50": 0.5, "25": 0.25}
#: Sementes de A1 e A3 com 100 %; as frações usam uma semente só.
SEMENTES = (1, 2, 3)
SEMENTE_FRACOES = 1
#: Dobra de A1 (sem canal deixado de fora).
DOBRA_A1 = "sem"
#: Classes da medida, na ordem do relatório.
CLASSES = ("certo", "impreciso", "falso", "nao_achou", "erro")
#: Estado do processo de geração de Sval (preenchido por ``_iniciar_sval``).
_CONTEXTO: dict = {}


def _dispositivo() -> torch.device:
    """Dispositivo do treino e da inferência (a GPU deste projeto).

    Com ``CHORINHO_MAOS_CPU=1`` no ambiente, usa a CPU: só para inferência quando a
    GPU caiu (os números podem diferir pouco dos da GPU, que usa fp16).

    Returns:
        ``torch.device("cuda")``, ou ``cpu`` com a variável ligada.
    """
    if os.environ.get(VARIAVEL_CPU) == "1":
        return torch.device("cpu")
    return torch.device("cuda")


def _imagem(caminho: Path) -> np.ndarray:
    """Lê uma imagem BGR, ou levanta erro se ela não existe.

    Args:
        caminho: arquivo da imagem.

    Returns:
        Imagem BGR uint8.

    Raises:
        FileNotFoundError: se o arquivo não pode ser lido.
    """
    img = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(caminho)
    return img


def _gabarito() -> dict:
    """Quadros do gabarito do dono (``braco.json``), por id.

    Returns:
        Dicionário id -> registro.
    """
    return json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))["quadros"]


def _ler_json(caminho: Path) -> dict:
    """Lê um JSON em UTF-8.

    Args:
        caminho: arquivo JSON.

    Returns:
        O conteúdo.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def _gravar_json(caminho: Path, dados: dict) -> None:
    """Grava um JSON legível, criando a pasta se preciso.

    Args:
        caminho: arquivo de destino.
        dados: conteúdo serializável.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Alvos e aumentos
# ---------------------------------------------------------------------------


def _ponto_na_corda(corda: list, x: float) -> tuple[float, float]:
    """Ponto da reta da corda na coordenada x dada.

    Args:
        corda: dois pontos ``[x, y]``.
        x: coordenada horizontal, em px.

    Returns:
        ``(x, y)`` sobre a reta.

    Raises:
        ValueError: se a corda é vertical (x dos dois pontos iguais).
    """
    (x0, y0), (x1, y1) = corda
    if abs(x1 - x0) < 1e-9:
        raise ValueError("corda vertical: não dá para ler y em função de x")
    return float(x), float(y0 + (x - x0) * (y1 - y0) / (x1 - x0))


def _distancia_reta(xs: np.ndarray, ys: np.ndarray, corda: list) -> np.ndarray:
    """Distância perpendicular de cada pixel à reta da corda.

    Args:
        xs: coordenadas x da grade.
        ys: coordenadas y da grade.
        corda: dois pontos ``[x, y]``.

    Returns:
        Distâncias em px, com a forma da grade.
    """
    (x0, y0), (x1, y1) = corda
    dx, dy = x1 - x0, y1 - y0
    norma = math.hypot(dx, dy)
    return np.abs(dy * (xs - x0) - dx * (ys - y0)) / norma


def _distancia_segmento(
    xs: np.ndarray, ys: np.ndarray, a: tuple[float, float], b: tuple[float, float]
) -> np.ndarray:
    """Distância de cada pixel ao segmento ``a``-``b``.

    Args:
        xs: coordenadas x da grade.
        ys: coordenadas y da grade.
        a: primeiro extremo.
        b: segundo extremo.

    Returns:
        Distâncias em px, com a forma da grade.
    """
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    comprimento2 = dx * dx + dy * dy
    t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / comprimento2, 0.0, 1.0)
    return np.hypot(ax + t * dx - xs, ay + t * dy - ys)


def mapas_alvo(rotulo: dict) -> np.ndarray:
    """Alvo de 4 canais (1024 x 192) a partir do rótulo na faixa (Emenda 2).

    Canais 0 e 1: crista gaussiana (sigma de 2 px) sobre a reta da corda 1 e da corda 6,
    estendida em x do nut até a borda oposta da faixa. Canal 2: uma crista para cada
    traste numerado (sem o nut), sobre o segmento que liga a corda 1 à corda 6 na mesma
    coordenada x do traste. Canal 3: o nut, sobre o segmento entre as cordas no x do nut.

    Args:
        rotulo: dicionário de ``rotulo_na_faixa`` (``corda1``, ``corda6``, ``trastes``).

    Returns:
        Array float32 ``(4, 192, 1024)`` com valores em [0, 1].

    Raises:
        ValueError: se o rótulo não tem o nut (número 0).
    """
    nuts = [t for t in rotulo["trastes"] if t[0] == 0]
    if not nuts:
        raise ValueError("rótulo sem nut")
    x_nut_rotulo = float(nuts[0][1])
    x_nut = max(0.0, x_nut_rotulo)
    ys, xs = np.mgrid[0:ALTURA_FAIXA, 0:LARGURA_FAIXA].astype(np.float64)
    dentro = xs >= x_nut
    dois_sigma = 2.0 * SIGMA_CRISTA_PX**2
    alvo = np.zeros((CANAIS_ALVO, ALTURA_FAIXA, LARGURA_FAIXA), dtype=np.float64)
    for canal, chave in ((CANAL_CORDA1, "corda1"), (CANAL_CORDA6, "corda6")):
        crista = np.exp(-(_distancia_reta(xs, ys, rotulo[chave]) ** 2) / dois_sigma)
        alvo[canal] = np.where(dentro, crista, 0.0)
    for numero, x, _y in rotulo["trastes"]:
        if numero == 0:
            continue
        a = _ponto_na_corda(rotulo["corda1"], x)
        b = _ponto_na_corda(rotulo["corda6"], x)
        crista = np.exp(-(_distancia_segmento(xs, ys, a, b) ** 2) / dois_sigma)
        alvo[CANAL_TRASTES] = np.maximum(alvo[CANAL_TRASTES], crista)
    a = _ponto_na_corda(rotulo["corda1"], x_nut_rotulo)
    b = _ponto_na_corda(rotulo["corda6"], x_nut_rotulo)
    alvo[CANAL_NUT] = np.exp(-(_distancia_segmento(xs, ys, a, b) ** 2) / dois_sigma)
    return alvo.astype(np.float32)


def espelhar(faixa: np.ndarray, alvo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Espelhamento vertical da faixa e dos mapas, sem trocar os canais.

    O rótulo segue os pixels: a crista de cada canal vai junto com a imagem, e o canal 0
    continua sendo a corda 1 mesmo quando ela fica embaixo.

    Args:
        faixa: imagem ``(192, 1024, 3)``.
        alvo: mapas ``(3, 192, 1024)``.

    Returns:
        ``(faixa, alvo)`` espelhados no eixo y.
    """
    return faixa[::-1], alvo[:, ::-1]


def aumentar(
    faixa: np.ndarray, alvo: np.ndarray, rng: random.Random
) -> tuple[np.ndarray, np.ndarray]:
    """Aumentos do treino: cor, desfoque, JPEG e espelhamento vertical.

    Args:
        faixa: faixa BGR uint8 ``(192, 1024, 3)``.
        alvo: mapas float32 ``(3, 192, 1024)``.
        rng: gerador do aumento (semente fixa por amostra).

    Returns:
        ``(faixa, alvo)``: a faixa em BGR float32 com valores em [0, 1], e os mapas.
    """
    img = faixa.astype(np.float32) / 255.0
    contraste = rng.uniform(0.7, 1.3)
    brilho = rng.uniform(-0.15, 0.15)
    saturacao = rng.uniform(0.6, 1.4)
    media = float(img.mean())
    img = (img - media) * contraste + media + brilho
    cinza = img.mean(axis=2, keepdims=True)
    img = np.clip(cinza + (img - cinza) * saturacao, 0.0, 1.0)
    if rng.random() < 0.5:
        img = cv2.GaussianBlur(img, (0, 0), rng.uniform(0.3, 1.2))
    if rng.random() < 0.5:
        qualidade = rng.randint(40, 95)
        imagem_u8 = np.ascontiguousarray((img * 255.0).round().astype(np.uint8))
        _, buffer = cv2.imencode(
            ".jpg", imagem_u8, [cv2.IMWRITE_JPEG_QUALITY, qualidade]
        )
        img = cv2.imdecode(buffer, cv2.IMREAD_COLOR).astype(np.float32) / 255.0
    if rng.random() < 0.5:
        img, alvo = espelhar(img, alvo)
    return img, alvo


class _Itens(Dataset):
    """Amostras de treino: cada item é um quadro S ou R com o seu erro de eixo.

    Cada item é ``(caminho, registro, semente_perturbacao, semente_aumento)``. Quando
    ``semente_aumento`` é None, não há aumento (usado na V2). Tudo é determinado pelas
    sementes do item, então o resultado não depende da ordem dos workers.
    """

    def __init__(self, itens: list[tuple]) -> None:
        """Guarda a lista de itens.

        Args:
            itens: tuplas ``(caminho, registro, semente_perturbacao, semente_aumento)``.
        """
        self.itens = itens

    def __len__(self) -> int:
        """Quantidade de amostras.

        Returns:
            Número de itens.
        """
        return len(self.itens)

    def __getitem__(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        """Amostra ``i``: faixa RGB uint8 ``(192, 1024, 3)`` e alvo uint8 ``(3, 192, 1024)``.

        Args:
            i: índice do item.

        Returns:
            ``(faixa, alvo)`` prontos para a GPU, com os valores quantizados em uint8.
        """
        caminho, registro, semente_perturbacao, semente_aumento = self.itens[i]
        img = _imagem(Path(caminho))
        marcas = marcas_do_registro(registro)
        if marcas is None:
            raise ValueError(f"{caminho} sem marcas completas")
        matriz = matriz_da_faixa(
            perturbar(eixo_da_faixa(marcas), random.Random(semente_perturbacao))
        )
        faixa = recortar(img, matriz)
        alvo = mapas_alvo(rotulo_na_faixa(marcas, matriz))
        if semente_aumento is None:
            faixa_f = faixa.astype(np.float32) / 255.0
        else:
            faixa_f, alvo = aumentar(faixa, alvo, random.Random(semente_aumento))
        rgb = np.ascontiguousarray(
            (faixa_f[..., ::-1] * 255.0).round().astype(np.uint8)
        )
        alvo_u8 = np.ascontiguousarray((alvo * 255.0).round().astype(np.uint8))
        return rgb, alvo_u8


def _iniciar_worker(_: int) -> None:
    """Configura um worker de dados: OpenCV e torch em uma thread só.

    Args:
        _: índice do worker (não usado).
    """
    cv2.setNumThreads(0)
    torch.set_num_threads(1)


# ---------------------------------------------------------------------------
# Rede
# ---------------------------------------------------------------------------


class _Bloco(nn.Module):
    """Duas convoluções 3 x 3 com normalização e ReLU."""

    def __init__(self, entrada: int, saida: int) -> None:
        """Monta o bloco.

        Args:
            entrada: canais de entrada.
            saida: canais de saída.
        """
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(entrada, saida, 3, padding=1, bias=False),
            nn.BatchNorm2d(saida),
            nn.ReLU(inplace=True),
            nn.Conv2d(saida, saida, 3, padding=1, bias=False),
            nn.BatchNorm2d(saida),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Aplica o bloco.

        Args:
            x: tensor ``(N, C, H, W)``.

        Returns:
            Tensor ``(N, saida, H, W)``.
        """
        return self.conv(x)


class UNetBraco(nn.Module):
    """U-Net com codificador ResNet18 e decodificador de 5 blocos até a resolução cheia."""

    def __init__(self, pesos_imagenet: bool = True, canais: int = CANAIS_ALVO) -> None:
        """Monta a rede, com os pesos ImageNet do cache local se pedido.

        Args:
            pesos_imagenet: se True, carrega ``IMAGENET1K_V1`` de ``PESOS_RESNET18``.
            canais: canais de saída (4 no estágio 2; 5 no localizador da 1024).

        Raises:
            FileNotFoundError: se os pesos pedidos não estão no cache.
        """
        super().__init__()
        resnet = torchvision.models.resnet18(weights=None)
        if pesos_imagenet:
            if not PESOS_RESNET18.exists():
                raise FileNotFoundError(PESOS_RESNET18)
            estado = torch.load(PESOS_RESNET18, map_location="cpu", weights_only=True)
            resnet.load_state_dict(estado)
        self.inicio = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu)
        self.pool = resnet.maxpool
        self.l1, self.l2 = resnet.layer1, resnet.layer2
        self.l3, self.l4 = resnet.layer3, resnet.layer4
        self.sobe4 = nn.ConvTranspose2d(512, 512, 2, stride=2)
        self.dec4 = _Bloco(512 + 256, 256)
        self.sobe3 = nn.ConvTranspose2d(256, 256, 2, stride=2)
        self.dec3 = _Bloco(256 + 128, 128)
        self.sobe2 = nn.ConvTranspose2d(128, 128, 2, stride=2)
        self.dec2 = _Bloco(128 + 64, 64)
        self.sobe1 = nn.ConvTranspose2d(64, 64, 2, stride=2)
        self.dec1 = _Bloco(64 + 64, 32)
        self.sobe0 = nn.ConvTranspose2d(32, 32, 2, stride=2)
        self.dec0 = _Bloco(32, 16)
        self.cabeca = nn.Conv2d(16, canais, 1)

    def codificador(self) -> list[nn.Module]:
        """Módulos do codificador (ResNet18), para a taxa de aprendizado menor.

        Returns:
            Lista de módulos.
        """
        return [self.inicio, self.l1, self.l2, self.l3, self.l4]

    def decodificador(self) -> list[nn.Module]:
        """Módulos do decodificador e da cabeça, para a taxa de aprendizado maior.

        Returns:
            Lista de módulos.
        """
        return [
            self.sobe4,
            self.dec4,
            self.sobe3,
            self.dec3,
            self.sobe2,
            self.dec2,
            self.sobe1,
            self.dec1,
            self.sobe0,
            self.dec0,
            self.cabeca,
        ]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Logits dos canais de alvo, na mesma resolução da entrada.

        Args:
            x: tensor ``(N, 3, H, W)`` normalizado (H e W múltiplos de 32).

        Returns:
            Tensor ``(N, CANAIS_ALVO, H, W)`` de logits.
        """
        e0 = self.inicio(x)
        e1 = self.l1(self.pool(e0))
        e2 = self.l2(e1)
        e3 = self.l3(e2)
        e4 = self.l4(e3)
        d = self.dec4(torch.cat([self.sobe4(e4), e3], dim=1))
        d = self.dec3(torch.cat([self.sobe3(d), e2], dim=1))
        d = self.dec2(torch.cat([self.sobe2(d), e1], dim=1))
        d = self.dec1(torch.cat([self.sobe1(d), e0], dim=1))
        d = self.dec0(self.sobe0(d))
        return self.cabeca(d)


def _para_modelo(rgb_u8: torch.Tensor) -> torch.Tensor:
    """Normaliza um lote RGB uint8 ``(N, H, W, 3)`` como o ImageNet, para a GPU.

    Args:
        rgb_u8: lote uint8 em RGB, com canais por último.

    Returns:
        Tensor float ``(N, 3, H, W)``.
    """
    dev = _dispositivo()
    x = rgb_u8.to(dev).permute(0, 3, 1, 2).float().div_(255.0)
    media = torch.tensor(MEDIA_IMAGENET, device=dev).view(1, 3, 1, 1)
    desvio = torch.tensor(DESVIO_IMAGENET, device=dev).view(1, 3, 1, 1)
    return (x - media) / desvio


def fator_lr(passo: int, total: int) -> float:
    """Fator do cronograma: aquecimento linear e depois cosseno até zero.

    Args:
        passo: passo atual, a partir de 0.
        total: número total de passos.

    Returns:
        Fator multiplicativo sobre a taxa base.
    """
    if passo < AQUECIMENTO:
        return (passo + 1) / AQUECIMENTO
    progresso = (passo - AQUECIMENTO) / max(1, total - AQUECIMENTO)
    return 0.5 * (1.0 + math.cos(math.pi * min(1.0, progresso)))


def _treinar(
    itens: list[tuple],
    passos: int,
    semente: int,
    constante: bool = False,
    trabalhadores: int = PROCESSOS_DADOS,
    classe_itens: type = _Itens,
) -> tuple[UNetBraco, list[float], float]:
    """Treina a rede por ``passos`` passos sobre a sequência de itens.

    A sequência tem ``passos * LOTE`` itens, e cada bloco de ``LOTE`` é um passo. Não
    há parada antecipada nem escolha de época.

    Args:
        itens: sequência de itens da classe ``classe_itens``.
        passos: número de passos.
        semente: semente fixa (``fixar_semente``).
        constante: se True, a taxa de aprendizado fica constante (sem cosseno).
        trabalhadores: processos de leitura de dados.
        classe_itens: classe ``Dataset`` que lê os itens (padrão ``_Itens``; a 1031
            usa ``ItensA5``, que aceita quadros com o nut fora da imagem).

    Returns:
        ``(modelo, perdas, segundos)``: a rede treinada, a perda de cada passo e o tempo
        do laço de treino.

    Raises:
        ValueError: se a sequência não tem ``passos * LOTE`` itens.
    """
    if len(itens) != passos * LOTE:
        raise ValueError("a sequência precisa de passos * LOTE itens")
    fixar_semente(semente)
    dev = _dispositivo()
    modelo = UNetBraco().to(dev)
    otimizador = torch.optim.AdamW(
        [
            {
                "params": [p for m in modelo.codificador() for p in m.parameters()],
                "lr": LR_CODIFICADOR,
            },
            {
                "params": [p for m in modelo.decodificador() for p in m.parameters()],
                "lr": LR_DECODIFICADOR,
            },
        ]
    )

    def fator(passo: int) -> float:
        """Fator do cronograma: 1 (taxa constante, Emenda 3) ou o cosseno padrão."""
        return 1.0 if constante else fator_lr(passo, passos)

    cronograma = torch.optim.lr_scheduler.LambdaLR(otimizador, fator)
    criterio = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(PESO_POSITIVO, device=dev))
    escala = torch.amp.GradScaler("cuda")
    carga = DataLoader(
        classe_itens(itens),
        batch_size=LOTE,
        shuffle=False,
        num_workers=trabalhadores,
        drop_last=True,
        pin_memory=True,
        worker_init_fn=_iniciar_worker,
    )
    perdas: list[float] = []
    modelo.train()
    inicio = time.perf_counter()
    for faixa_u8, alvo_u8 in carga:
        x = _para_modelo(faixa_u8)
        y = alvo_u8.to(dev).float().div_(255.0)
        with torch.autocast("cuda", dtype=torch.float16):
            logits = modelo(x)
        perda = criterio(logits.float(), y)
        otimizador.zero_grad(set_to_none=True)
        escala.scale(perda).backward()
        escala.step(otimizador)
        escala.update()
        cronograma.step()
        perdas.append(float(perda.item()))
    segundos = time.perf_counter() - inicio
    if len(perdas) != passos:
        raise RuntimeError(f"treino deu {len(perdas)} passos, eram {passos}")
    return modelo, perdas, segundos


@torch.no_grad()
def prever_mapas(modelo: nn.Module, faixas: list[np.ndarray]) -> list[np.ndarray]:
    """Probabilidades dos 3 canais para cada faixa BGR uint8.

    Args:
        modelo: rede treinada.
        faixas: faixas BGR uint8 ``(192, 1024, 3)``.

    Returns:
        Lista de arrays float32 ``(CANAIS_ALVO, 192, 1024)`` com valores em [0, 1].
    """
    modelo.eval()
    saidas: list[np.ndarray] = []
    for i in range(0, len(faixas), 8):
        lote = np.stack([f[..., ::-1] for f in faixas[i : i + 8]])
        x = _para_modelo(torch.from_numpy(np.ascontiguousarray(lote)))
        with torch.autocast("cuda", dtype=torch.float16):
            logits = modelo(x)
        prob = torch.sigmoid(logits.float()).cpu().numpy()
        saidas.extend(list(prob))
    return saidas


# ---------------------------------------------------------------------------
# Pós-processamento: mapas -> retas e trastes
# ---------------------------------------------------------------------------


def _ransac_reta(xs: np.ndarray, ys: np.ndarray) -> np.ndarray | None:
    """Máscara dos inliers da melhor reta por RANSAC (limite de 2 px).

    A amostragem usa um gerador com semente fixa, então o resultado é reproduzível.

    Args:
        xs: coordenadas x dos pontos.
        ys: coordenadas y dos pontos.

    Returns:
        Máscara booleana dos inliers, ou None se não há como ajustar uma reta.
    """
    rng = random.Random(0)
    n = len(xs)
    if n < 2:
        return None
    melhor = None
    melhor_contagem = -1
    for _ in range(ITERACOES_RANSAC_CORDA):
        i, j = rng.sample(range(n), 2)
        if xs[i] == xs[j]:
            continue
        m = (ys[j] - ys[i]) / (xs[j] - xs[i])
        b = ys[i] - m * xs[i]
        distancia = np.abs(ys - (m * xs + b)) / math.sqrt(1.0 + m * m)
        mascara = distancia <= LIMITE_RANSAC_CORDA_PX
        contagem = int(mascara.sum())
        if contagem > melhor_contagem:
            melhor_contagem = contagem
            melhor = mascara
    return melhor


def _ajustar_corda(canal: np.ndarray) -> tuple[float, float] | None:
    """Reta ``y = m x + b`` de uma corda, a partir do mapa de um canal.

    Para cada coluna x, o pico em y (só se o valor passa de 0,3). RANSAC com limite de 2 px
    e depois mínimos quadrados nos inliers. Exige ``MINIMO_INLIERS_CORDA`` colunas.

    Args:
        canal: probabilidades ``(192, 1024)``.

    Returns:
        ``(m, b)``, ou None quando não há reta.
    """
    colunas = np.arange(canal.shape[1])
    linhas = np.argmax(canal, axis=0)
    valores = canal[linhas, colunas]
    mascara = valores > LIMITE_CRISTA
    xs = colunas[mascara].astype(float)
    ys = linhas[mascara].astype(float)
    if xs.size < MINIMO_INLIERS_CORDA:
        return None
    inliers = _ransac_reta(xs, ys)
    if inliers is None or int(inliers.sum()) < MINIMO_INLIERS_CORDA:
        return None
    m, b = np.polyfit(xs[inliers], ys[inliers], 1)
    return float(m), float(b)


def _perfil_entre_cordas(
    canal: np.ndarray, y1: np.ndarray, y6: np.ndarray
) -> np.ndarray:
    """Média de um canal (trastes ou nut) na faixa vertical entre as cordas, por coluna.

    Args:
        canal: probabilidades do canal 2 ``(192, 1024)``.
        y1: y da corda 1 em cada coluna.
        y6: y da corda 6 em cada coluna.

    Returns:
        Perfil ``(1024,)``.
    """
    altura, largura = canal.shape
    r0 = np.clip(np.floor(np.minimum(y1, y6)).astype(int), 0, altura - 1)
    r1 = np.clip(np.ceil(np.maximum(y1, y6)).astype(int), 0, altura - 1)
    r1 = np.maximum(r1, r0)
    soma_acumulada = np.vstack([np.zeros((1, largura)), np.cumsum(canal, axis=0)])
    colunas = np.arange(largura)
    soma = soma_acumulada[r1 + 1, colunas] - soma_acumulada[r0, colunas]
    return soma / (r1 - r0 + 1)


def _picos(perfil: np.ndarray) -> list[int]:
    """Picos do perfil: máximos locais, um por crista.

    O perfil é suavizado (gaussiana de sigma ``SIGMA_PERFIL_PX``). Um pico é um máximo
    local estrito na janela de ``DISTANCIA_PICO_MINIMA_PX`` para cada lado, acima de
    ``ALTURA_PICO_MINIMA``. Sem a exigência de máximo local, as encostas de uma crista
    larga viravam picos extras (V2 da 1021, emenda 4).

    Args:
        perfil: perfil ``(1024,)``.

    Returns:
        Coordenadas x dos picos, em ordem crescente.
    """
    suave = cv2.GaussianBlur(
        perfil.astype(np.float64).reshape(1, -1),
        (0, 0),
        sigmaX=SIGMA_PERFIL_PX,
        borderType=cv2.BORDER_REPLICATE,
    ).ravel()
    raio = DISTANCIA_PICO_MINIMA_PX
    escolhidos: list[int] = []
    for i in range(len(suave)):
        if suave[i] <= ALTURA_PICO_MINIMA:
            continue
        janela = suave[max(0, i - raio) : i + raio + 1]
        if suave[i] < janela.max():
            continue
        if escolhidos and i - escolhidos[-1] <= raio:
            continue
        escolhidos.append(i)
    return escolhidos


def _projetar(params: np.ndarray, numeros: list[int]) -> np.ndarray | None:
    """Posições ``t(n)`` pelo modelo projetivo, ou None se o denominador não é positivo.

    Args:
        params: ``[a, b, c]`` do modelo ``t = (a s + b) / (c s + 1)``.
        numeros: números de traste.

    Returns:
        Array de posições, ou None.
    """
    a, b, c = (float(v) for v in params)
    s = np.array([s_do_traste(int(n)) for n in numeros], dtype=float)
    denominador = c * s + 1.0
    if np.any(denominador <= 1e-9):
        return None
    return (a * s + b) / denominador


def _refit_projetivo(
    pares: list[tuple[int, float]], mascara: np.ndarray
) -> np.ndarray | None:
    """Mínimos quadrados do modelo projetivo nos inliers.

    Args:
        pares: pares ``(número, t)``.
        mascara: inliers.

    Returns:
        ``[a, b, c]``, ou None se o sistema é singular.
    """
    usados = [p for p, m in zip(pares, mascara, strict=True) if m]
    if len(usados) < 3:
        return None
    s = np.array([s_do_traste(n) for n, _ in usados], dtype=float)
    t = np.array([valor for _, valor in usados], dtype=float)
    matriz = np.column_stack([s, np.ones_like(s), -t * s])
    solucao, *_ = np.linalg.lstsq(matriz, t, rcond=None)
    return solucao


def _nao_achou(motivo: str) -> dict:
    """Resposta do pós-processamento quando não há braço.

    Args:
        motivo: explicação curta, para o log.

    Returns:
        Dicionário com ``achou`` falso e o motivo.
    """
    return {"achou": False, "motivo": motivo}


def _nut_do_perfil(mapas: np.ndarray, y1: np.ndarray, y6: np.ndarray) -> float | None:
    """Coordenada x do nut: pico do canal do nut no perfil entre as cordas (Emenda 2).

    Args:
        mapas: probabilidades ``(4, 192, 1024)``.
        y1: y da corda 1 em cada coluna.
        y6: y da corda 6 em cada coluna.

    Returns:
        x do pico em px, ou None se o pico é menor que ``LIMITE_NUT``.
    """
    perfil = _perfil_entre_cordas(mapas[CANAL_NUT], y1, y6)
    x = int(np.argmax(perfil))
    if perfil[x] < LIMITE_NUT:
        return None
    return float(x)


def _trastes_no_intervalo(d: float, espaco: float) -> int:
    """Quantos espaços esperados cabem no intervalo ``d`` (salto de traste escondido).

    Com o primeiro espaço ``espaco`` e razão ``r``, ``k`` espaços somam
    ``espaco * (1 - r**k) / (1 - r)``. Inverte-se essa soma para achar ``k``. O resultado
    fica entre 2 (um salto já exige pelo menos 2 espaços) e ``N_MAXIMO`` (19 casas).

    Args:
        d: intervalo medido, em px, entre dois picos consecutivos.
        espaco: espaço esperado do primeiro traste do intervalo, em px.

    Returns:
        Número de espaços (trastes) que o intervalo contém.
    """
    r = RAZAO_ESPACO
    restante = max(1.0 - d * (1.0 - r) / espaco, 1e-6)
    k = round(math.log(restante) / math.log(r))
    return int(min(max(k, 2), N_MAXIMO))


def _numerar_por_ordem(picos: list[int], x_nut: float) -> list[tuple[int, float]]:
    """Numera os picos à direita do nut, em ordem, com saltos (Emenda 2).

    O primeiro pico recebe o número 1. Para o primeiro intervalo (nut até o 1º pico),
    o espaço esperado é o intervalo entre o 1º e o 2º pico dividido por ``RAZAO_ESPACO``.
    Cada intervalo ``d`` é comparado com o espaço esperado ``e``: se ``d > 1,6 e``, é um
    salto e o número pula pelo número de espaços que cabem em ``d``. Depois de cada
    intervalo, o espaço esperado do próximo é o último espaço aceito vezes ``RAZAO_ESPACO``.

    Args:
        picos: x dos picos do canal de trastes, em ordem crescente.
        x_nut: x do nut.

    Returns:
        Pares ``(numero, x)``, em ordem de x. Vazio se há menos de 2 picos à direita.
    """
    direita = [float(p) for p in picos if p > x_nut]
    if len(direita) < 2:
        return []
    r = RAZAO_ESPACO
    espaco = (direita[1] - direita[0]) / r
    numerados: list[tuple[int, float]] = []
    numero = 0
    x_ant = x_nut
    for x in direita:
        d = x - x_ant
        if d > FATOR_SALTO * espaco:
            k = _trastes_no_intervalo(d, espaco)
            numero += k
            espaco_ultimo = d * (1.0 - r) / (1.0 - r**k) * r ** (k - 1)
        else:
            numero += 1
            espaco_ultimo = d
        numerados.append((numero, x))
        x_ant = x
        espaco = espaco_ultimo * r
    return numerados


def decodificar(mapas: np.ndarray) -> dict:
    """Converte os 4 mapas de uma faixa em retas, nut e trastes numerados (Emenda 2).

    Passos: retas das cordas (RANSAC e mínimos quadrados); nut = pico do canal do nut
    entre as cordas (abaixo de 0,3 é "não achou"); picos do canal de trastes à direita do
    nut, numerados em ordem com saltos (``_numerar_por_ordem``); com menos de 4 trastes
    detectados é "não achou". Um ajuste projetivo por mínimos quadrados, com o nut
    incluído, só preenche os números que faltam até o último pico. Os números não são
    refeitos. Trastes detectados ficam na posição do pico; os preenchidos, na posição do
    modelo.

    Args:
        mapas: probabilidades ``(4, 192, 1024)``.

    Returns:
        Com braço: ``achou``, ``nut``, ``trastes`` (número -> ``[x, y]``), ``corda1``,
        ``corda6`` (dois pontos cada), ``detectados`` (quantos trastes vieram de picos),
        ``preenchidos`` (números que vieram do modelo). Sem braço: ``achou`` falso e
        ``motivo``.
    """
    geo = _cordas_e_nut(mapas)
    if not geo["achou"]:
        return geo
    x_nut = geo["x_nut"]
    numerados = _numerar_por_ordem(geo["picos"], x_nut)
    if len(numerados) < MINIMO_TRASTES:
        return _nao_achou("menos de 4 trastes detectados")
    pares = [(0, x_nut)] + [(n, x) for n, x in numerados]
    ajuste = _refit_projetivo(pares, np.ones(len(pares), dtype=bool))
    if ajuste is None:
        return _nao_achou("ajuste projetivo singular")
    maior = numerados[-1][0]
    ts = _projetar(ajuste, list(range(maior + 1)))
    if ts is None or np.any(np.diff(ts) <= 0.0):
        return _nao_achou("modelo ajustado não cresce do nut para fora")
    return _montar_saida(geo, dict(numerados), ts)


def _cordas_e_nut(mapas: np.ndarray) -> dict:
    """Retas das cordas, eixo médio, nut e picos dos trastes (iguais nas versões 1 e 2).

    Args:
        mapas: probabilidades ``(4, 192, 1024)``.

    Returns:
        Com braço: ``achou`` verdadeiro, ``xs``, ``y1``, ``y6``, ``ymedio`` (médio das
        cordas), ``x_nut`` e ``picos`` (x dos picos do canal de trastes entre as cordas).
        Sem braço: ``achou`` falso e ``motivo``.
    """
    reta1 = _ajustar_corda(mapas[CANAL_CORDA1])
    reta6 = _ajustar_corda(mapas[CANAL_CORDA6])
    if reta1 is None or reta6 is None:
        return _nao_achou("corda sem reta")
    xs = np.arange(mapas.shape[2], dtype=float)
    y1 = reta1[0] * xs + reta1[1]
    y6 = reta6[0] * xs + reta6[1]
    ymedio = (y1 + y6) / 2.0
    x_nut = _nut_do_perfil(mapas, y1, y6)
    if x_nut is None:
        return _nao_achou("nut sem pico acima de 0,3")
    picos = _picos(_perfil_entre_cordas(mapas[CANAL_TRASTES], y1, y6))
    return {
        "achou": True,
        "xs": xs,
        "y1": y1,
        "y6": y6,
        "ymedio": ymedio,
        "x_nut": x_nut,
        "picos": picos,
    }


def _montar_saida(geo: dict, detectados: dict[int, float], ts: np.ndarray) -> dict:
    """Saída do decodificador: trastes de 1 até o maior detectado.

    Número detectado usa a posição do pico; número sem pico usa a posição do modelo
    (``ts[n]``).

    Args:
        geo: resultado de ``_cordas_e_nut`` com ``achou`` verdadeiro.
        detectados: número -> x do pico, para os números que têm pico.
        ts: posições do modelo, com ``ts[n]`` para n de 0 até o maior número.

    Returns:
        Dicionário com ``achou``, ``nut``, ``trastes``, ``corda1``, ``corda6``,
        ``detectados`` e ``preenchidos``.
    """
    xs, y1, y6, ymedio = geo["xs"], geo["y1"], geo["y6"], geo["ymedio"]
    x_nut = geo["x_nut"]
    maior = max(detectados)
    trastes: dict[int, list[float]] = {}
    preenchidos: list[int] = []
    for n in range(1, maior + 1):
        if n in detectados:
            x = detectados[n]
        else:
            x = float(ts[n])
            preenchidos.append(n)
        trastes[n] = [x, float(np.interp(x, xs, ymedio))]
    fim = trastes[maior][0]

    def ponto_corda(y: np.ndarray, x: float) -> list[float]:
        """Ponto de uma corda na coordenada x."""
        return [x, float(np.interp(x, xs, y))]

    return {
        "achou": True,
        "nut": [x_nut, float(np.interp(x_nut, xs, ymedio))],
        "trastes": trastes,
        "corda1": [ponto_corda(y1, x_nut), ponto_corda(y1, fim)],
        "corda6": [ponto_corda(y6, x_nut), ponto_corda(y6, fim)],
        "detectados": len(detectados),
        "preenchidos": preenchidos,
    }


def _numerar_v2(picos: list[int], x_nut: float) -> dict | None:
    """Numeração robusta dos picos por ajuste (decodificador v2, rodada 1022).

    Modelo ``t(n) = (a s(n) + b) / (c s(n) + 1)`` com ``b`` preso no x do nut. Para cada
    par de picos (``p_i < p_j``) e cada par de números (``1 <= n_i < n_j <= N_MAX_V2``),
    resolve ``a`` e ``c`` pelo sistema 2 x 2 (``a s - c t s = t - b``). A hipótese é
    descartada se o denominador não é positivo em n = 0..N_MAX_V2 + 1 (o +1 é o espaço do
    último número) ou se ``t`` não cresce em 0..N_MAX_V2. Um pico é inlier do número n
    quando ``|p - t(n)| <= TOLERANCIA_V2 * (t(n+1) - t(n))``, com atribuição um-para-um
    (o mais próximo, por ordem de número). Só contam os números de 1 até o maior com
    ``t(n) < LARGURA_FAIXA``. Vence a hipótese com mais inliers; empate, a menor soma dos
    erros normalizados pelo espaço local. O ajuste final refaz ``a`` e ``c`` por mínimos
    quadrados com ``b`` preso.

    Args:
        picos: x dos picos do canal de trastes, em ordem crescente.
        x_nut: x do nut (``b`` do modelo).

    Returns:
        ``{"inliers": {numero: x}, "ts": array}`` com ``ts[n]`` de 0 até o maior inlier,
        ou None se há menos de ``MIN_INLIERS_V2`` inliers (ou o ajuste não é válido).
    """
    direita = np.array([float(p) for p in picos if p > x_nut])
    if direita.size < MIN_INLIERS_V2:
        return None
    b = float(x_nut)
    s_todos = np.array([s_do_traste(n) for n in range(N_MAX_V2 + 2)], dtype=float)
    indices_picos = np.triu_indices(direita.size, k=1)
    pares_numeros = [
        (i, j) for i in range(1, N_MAX_V2 + 1) for j in range(i + 1, N_MAX_V2 + 1)
    ]
    ni = np.array([i for i, _ in pares_numeros])
    nj = np.array([j for _, j in pares_numeros])
    si, sj = s_todos[ni], s_todos[nj]
    s_n = s_todos[None, :]
    melhor = None
    for k in range(len(indices_picos[0])):
        pi = direita[indices_picos[0][k]]
        pj = direita[indices_picos[1][k]]
        di, dj = pi - b, pj - b
        det = si * sj * (pi - pj)
        a = (-di * pj * sj + pi * si * dj) / det
        c = (si * dj - sj * di) / det
        with np.errstate(divide="ignore", invalid="ignore"):
            den = c[:, None] * s_n + 1.0
            t = (a[:, None] * s_n + b) / den
        ok = np.all(den > 0.0, axis=1)
        ok &= np.all(np.diff(t[:, : N_MAX_V2 + 1], axis=1) > 0.0, axis=1)
        if not np.any(ok):
            continue
        idx = np.nonzero(ok)[0]
        tn = t[idx, 1 : N_MAX_V2 + 1]
        espaco = t[idx, 2 : N_MAX_V2 + 2] - tn
        dentro = np.logical_and.accumulate(tn < LARGURA_FAIXA, axis=1)
        dist = np.abs(direita[None, None, :] - tn[:, :, None])
        cand = (dist <= TOLERANCIA_V2 * espaco[:, :, None]) & dentro[:, :, None]
        usado = np.zeros((idx.size, direita.size), dtype=bool)
        linhas = np.arange(idx.size)
        atribuido = np.full((idx.size, N_MAX_V2), -1, dtype=int)
        erro = np.zeros(idx.size)
        for m in range(N_MAX_V2):
            d = np.where(cand[:, m, :] & ~usado, dist[:, m, :], np.inf)
            j = np.argmin(d, axis=1)
            tem = np.isfinite(d[linhas, j])
            atribuido[tem, m] = j[tem]
            usado[linhas[tem], j[tem]] = True
            erro[tem] += d[linhas[tem], j[tem]] / espaco[tem, m]
        contagem = (atribuido >= 0).sum(axis=1)
        ordem = np.lexsort((erro, -contagem))[0]
        if melhor is None or (contagem[ordem], -erro[ordem]) > (
            melhor["contagem"],
            -melhor["erro"],
        ):
            melhor = {
                "contagem": int(contagem[ordem]),
                "erro": float(erro[ordem]),
                "atribuido": atribuido[ordem].copy(),
            }
    if melhor is None or melhor["contagem"] < MIN_INLIERS_V2:
        return None
    inliers = {
        m + 1: float(direita[j]) for m, j in enumerate(melhor["atribuido"]) if j >= 0
    }
    numeros = sorted(inliers)
    maior = numeros[-1]
    s_in = np.array([s_do_traste(n) for n in numeros], dtype=float)
    p_in = np.array([inliers[n] for n in numeros], dtype=float)
    matriz = np.column_stack([s_in, -p_in * s_in])
    (a_fim, c_fim), *_ = np.linalg.lstsq(matriz, p_in - b, rcond=None)
    ts = _projetar(np.array([a_fim, b, c_fim]), list(range(maior + 1)))
    if ts is None or np.any(np.diff(ts) <= 0.0):
        return None
    return {"inliers": inliers, "ts": ts}


def decodificar_v2(mapas: np.ndarray) -> dict:
    """Decodificador v2 (rodada 1022): numeração por ajuste robusto, no lugar da ordem.

    Cordas e nut são os da v1 (``_cordas_e_nut``). Só a numeração dos picos muda, via
    ``_numerar_v2``: tolera picos espúrios e trastes faltando. Menos de
    ``MIN_INLIERS_V2`` inliers é "não achou".

    Args:
        mapas: probabilidades ``(4, 192, 1024)``.

    Returns:
        O mesmo formato de ``decodificar``.
    """
    geo = _cordas_e_nut(mapas)
    if not geo["achou"]:
        return geo
    resultado = _numerar_v2(geo["picos"], geo["x_nut"])
    if resultado is None:
        return _nao_achou("menos de 4 inliers de traste")
    return _montar_saida(geo, resultado["inliers"], resultado["ts"])


def decodificar_versao(mapas: np.ndarray, versao: int) -> dict:
    """Escolhe o decodificador pela versão (1 é o da 1021, 2 é o da 1022).

    Args:
        mapas: probabilidades ``(4, 192, 1024)``.
        versao: 1 ou 2.

    Returns:
        O resultado do decodificador escolhido.

    Raises:
        ValueError: se a versão não existe.
    """
    if versao == 1:
        return decodificar(mapas)
    if versao == 2:
        return decodificar_v2(mapas)
    raise ValueError(f"decodificador desconhecido: {versao}")


def _no_quadro(dec: dict, matriz: np.ndarray) -> Marcas:
    """Leva as marcas decodificadas da faixa de volta ao quadro.

    Args:
        dec: resultado de ``decodificar`` com ``achou`` verdadeiro.
        matriz: afim da faixa (``matriz_da_faixa``).

    Returns:
        ``Marcas`` no quadro original.
    """
    return Marcas(
        nut=voltar(np.asarray(dec["nut"], dtype=float), matriz),
        trastes={
            n: voltar(np.asarray(p, dtype=float), matriz)
            for n, p in dec["trastes"].items()
        },
        corda1=voltar(np.asarray(dec["corda1"], dtype=float), matriz),
        corda6=voltar(np.asarray(dec["corda6"], dtype=float), matriz),
    )


def _medir(dec: dict, matriz: np.ndarray, alvo: Marcas) -> tuple[str, dict | None]:
    """Classe e erros de uma faixa contra as marcas do quadro (braço "sim").

    Args:
        dec: resultado de ``decodificar``.
        matriz: afim da faixa.
        alvo: marcas do dono (ou do rótulo S) no quadro.

    Returns:
        ``(classe, erros)``; ``erros`` é None quando não há medida.
    """
    if not dec["achou"]:
        return classificar({}, False, "sim"), None
    try:
        medida = erros(_no_quadro(dec, matriz), alvo)
    except ValueError as erro:
        return "erro", {"erro": str(erro)}
    return classificar(medida, True, "sim"), medida


# ---------------------------------------------------------------------------
# Pools e sequências
# ---------------------------------------------------------------------------


def pool_r_da_dobra(pool_r: list[dict], dobra: int, fracao: float) -> list[dict]:
    """Quadros R de treino da dobra k: sem nenhum R do canal k, só nos vídeos sorteados.

    Args:
        pool_r: quadros R (de ``_pool_r``), de todos os canais.
        dobra: índice k do canal deixado de fora.
        fracao: 0,25, 0,5 ou 1,0.

    Returns:
        Quadros R que entram no treino da dobra.
    """
    canal_fora = canais_g()[dobra]
    videos = videos_da_dobra(pool_r, dobra, fracao)
    return [e for e in pool_r if e["canal"] != canal_fora and e["arquivo"] in videos]


def _pool_s() -> list[tuple[str, dict]]:
    """Quadros S prontos (jpg e json, com marcas completas).

    Returns:
        Lista de ``(caminho_jpg, registro)``, em ordem de nome.
    """
    pool: list[tuple[str, dict]] = []
    for caminho in sorted(DIR_S.glob("*.json")):
        jpg = caminho.with_suffix(".jpg")
        if not jpg.exists():
            continue
        registro = _ler_json(caminho)
        if marcas_do_registro(registro) is None:
            continue
        pool.append((str(jpg), registro))
    return pool


def _pool_r() -> list[dict]:
    """Quadros R que o rastreador entregou como "achou".

    Returns:
        Lista de dicionários com ``caminho``, ``registro``, ``canal`` e ``arquivo``.
    """
    pool: list[dict] = []
    for caminho in sorted(DIR_R.glob("*.json")):
        dados = _ler_json(caminho)
        if not dados["achou"]:
            continue
        if marcas_do_registro(dados["registro"]) is None:
            continue
        pool.append(
            {
                "caminho": str(caminho.with_suffix(".jpg")),
                "registro": dados["registro"],
                "canal": dados["canal"],
                "arquivo": dados["arquivo"],
            }
        )
    return pool


def _entradas_g(canal: str | None) -> list[dict]:
    """Quadros G (faixas fixas) de um canal, ou de todos.

    Args:
        canal: nome do canal, ou None para todos.

    Returns:
        Registros de G (``id``, ``canal``, ``matriz``, ``rotulo_na_faixa``).
    """
    entradas = []
    for caminho in sorted(DIR_G.glob("*.json")):
        dados = _ler_json(caminho)
        if canal is None or dados["canal"] == canal:
            entradas.append(dados)
    return entradas


def canais_g() -> list[str]:
    """Canais dos quadros G, em ordem. A dobra k deixa o canal k de fora.

    Returns:
        Nomes dos canais, ordenados.
    """
    return sorted({dados["canal"] for dados in _entradas_g(None)})


def videos_da_dobra(pool_r: list[dict], dobra: int, fracao: float) -> set[str]:
    """Vídeos de R usados na dobra, com a fração pedida (prefixos aninhados).

    Os vídeos são os de R sem o canal k. Sorteio com ``random.Random`` na semente
    ``"20261021:frac:<dobra>"``, e a fração é um prefixo do mesmo sorteio, então 25 %
    está dentro de 50 %, que está dentro de 100 %.

    Args:
        pool_r: quadros R (de ``_pool_r``).
        dobra: índice k do canal deixado de fora.
        fracao: 0,25, 0,5 ou 1,0.

    Returns:
        Conjunto de nomes de arquivo de vídeo.
    """
    canal = canais_g()[dobra]
    videos = sorted({e["arquivo"] for e in pool_r if e["canal"] != canal})
    random.Random(f"{SEMENTE}:frac:{dobra}").shuffle(videos)
    quantidade = math.ceil(fracao * len(videos) - 1e-9)
    return set(videos[:quantidade])


def _sequencia(
    pool_s: list[tuple[str, dict]],
    pool_r: list[dict],
    passos: int,
    mistura: tuple[int, int],
    tag: str,
) -> list[tuple]:
    """Sequência de itens do treino: ``mistura`` de S e R em cada passo.

    Args:
        pool_s: quadros S.
        pool_r: quadros R da dobra (vazio quando a mistura não usa R).
        passos: número de passos.
        mistura: ``(itens de S por passo, itens de R por passo)``.
        tag: identifica o experimento, para a semente do sorteio.

    Returns:
        Lista de ``passos * LOTE`` tuplas para ``_Itens``.

    Raises:
        ValueError: se a mistura pede um pool vazio.
    """
    n_s, n_r = mistura
    if n_s and not pool_s:
        raise ValueError("pool S vazio")
    if n_r and not pool_r:
        raise ValueError("pool R vazio")
    rng = random.Random(f"{SEMENTE}:seq:{tag}")
    sequencia: list[tuple] = []
    for _ in range(passos):
        for _ in range(n_s):
            caminho, registro = pool_s[rng.randrange(len(pool_s))]
            sequencia.append(
                (caminho, registro, rng.getrandbits(31), rng.getrandbits(31))
            )
        for _ in range(n_r):
            entrada = pool_r[rng.randrange(len(pool_r))]
            sequencia.append(
                (
                    entrada["caminho"],
                    entrada["registro"],
                    rng.getrandbits(31),
                    rng.getrandbits(31),
                )
            )
    return sequencia


# ---------------------------------------------------------------------------
# Pesos e trava de GPU
# ---------------------------------------------------------------------------


@contextmanager
def _trava_gpu() -> Iterator[None]:
    """Reserva a GPU para a trilha mãos (``tab.gpu.trava_gpu``, protocolo ``gpu.lock``).

    Na CPU (``CHORINHO_MAOS_CPU=1``) não trava nada: a GPU fica livre para as outras
    trilhas.

    Yields:
        Nada; o bloco roda com a GPU reservada.
    """
    if os.environ.get(VARIAVEL_CPU) == "1":
        yield
        return
    with trava_gpu("maos"):
        yield


def _nome_unidade(exp: str, fracao: str, dobra: str | int, semente: int) -> str:
    """Nome de uma unidade de trabalho (peso e resultado), ``<exp>_<frac>_<dobra>_s<s>``.

    Args:
        exp: ``A1``, ``A2`` ou ``A3``.
        fracao: ``25``, ``50`` ou ``100``.
        dobra: índice k da dobra, ou ``sem`` em A1.
        semente: semente do treino.

    Returns:
        Nome sem extensão.
    """
    return f"{exp}_{fracao}_{dobra}_s{semente}"


def _salvar_pesos(modelo: nn.Module, nome: str, meta: dict) -> None:
    """Grava os pesos e o json do comando e da semente ao lado.

    Args:
        modelo: rede treinada.
        nome: nome da unidade.
        meta: comando, semente, passos e tempo.
    """
    DIR_PESOS.mkdir(parents=True, exist_ok=True)
    torch.save(modelo.state_dict(), DIR_PESOS / f"{nome}.pt")
    _gravar_json(DIR_PESOS / f"{nome}.json", meta)


def _carregar_pesos(nome: str, passos: int) -> tuple[UNetBraco, dict]:
    """Carrega uma rede treinada, conferindo o número de passos.

    Args:
        nome: nome da unidade.
        passos: passos esperados.

    Returns:
        ``(modelo, meta)``.

    Raises:
        ValueError: se o peso foi treinado com outro número de passos.
    """
    meta = _ler_json(DIR_PESOS / f"{nome}.json")
    if meta["passos"] != passos:
        raise ValueError(
            f"{nome} foi treinado com {meta['passos']} passos, não {passos}"
        )
    modelo = UNetBraco(pesos_imagenet=False).to(_dispositivo())
    modelo.load_state_dict(
        torch.load(DIR_PESOS / f"{nome}.pt", map_location=_dispositivo())
    )
    modelo.eval()
    return modelo, meta


def passos_do_orcamento() -> int:
    """Passos de treino em uso: os de ``v4_tempo.json`` se existir, senão ``PASSOS``.

    Emenda 5 da 1021: o corte do V4 nunca desce abaixo de ``PASSOS_MINIMO``. Se o
    orçamento estoura, o plano demora mais em vez de treinar pouco.

    Returns:
        Número de passos.
    """
    if ARQUIVO_V4.exists():
        return max(PASSOS_MINIMO, int(_ler_json(ARQUIVO_V4)["passos"]))
    return PASSOS


# ---------------------------------------------------------------------------
# Portões e execução
# ---------------------------------------------------------------------------


def _avaliar_g(modelo: nn.Module, canal: str | None) -> list[dict]:
    """Mede a rede nos quadros G de um canal (ou de todos).

    Args:
        modelo: rede treinada.
        canal: canal deixado de fora, ou None para todos os G.

    Returns:
        Uma entrada por quadro: id, canal, classe, achou, detectados, motivo e erros.
    """
    gabarito = _gabarito()
    entradas = _entradas_g(canal)
    faixas = [_imagem(DIR_G / f"{e['id']}.png") for e in entradas]
    mapas = prever_mapas(modelo, faixas)
    quadros = []
    for entrada, mapa in zip(entradas, mapas, strict=True):
        dec = decodificar(mapa)
        alvo = marcas_do_registro(gabarito[entrada["id"]])
        if alvo is None:
            raise ValueError(f"{entrada['id']} sem marcas no gabarito")
        classe, medida = _medir(dec, np.asarray(entrada["matriz"], dtype=float), alvo)
        quadros.append(
            {
                "id": entrada["id"],
                "canal": entrada["canal"],
                "classe": classe,
                "achou": bool(dec["achou"]),
                "detectados": dec.get("detectados"),
                "motivo": dec.get("motivo"),
                "erros": medida,
            }
        )
    return quadros


def _executar_unidade(
    exp: str,
    fracao: str,
    dobra: int | None,
    semente: int,
    passos: int,
    pool_s: list[tuple[str, dict]],
    pool_r: list[dict],
) -> str:
    """Treina (ou reusa o peso) e mede uma unidade, gravando o resultado.

    Args:
        exp: ``A1``, ``A2`` ou ``A3``.
        fracao: ``25``, ``50`` ou ``100``.
        dobra: índice k da dobra, ou None em A1.
        semente: semente do treino.
        passos: passos de treino.
        pool_s: quadros S.
        pool_r: quadros R (todos os canais).

    Returns:
        Nome da unidade.
    """
    rotulo_dobra = DOBRA_A1 if dobra is None else dobra
    nome = _nome_unidade(exp, fracao, rotulo_dobra, semente)
    canal_fora = None if dobra is None else canais_g()[dobra]
    with _trava_gpu():
        if (DIR_PESOS / f"{nome}.pt").exists():
            modelo, meta = _carregar_pesos(nome, passos)
        else:
            pool_r_dobra = (
                [] if dobra is None else pool_r_da_dobra(pool_r, dobra, FRACOES[fracao])
            )
            sequencia = _sequencia(
                pool_s,
                pool_r_dobra,
                passos,
                MISTURA[exp],
                f"{exp}:{fracao}:{rotulo_dobra}:{semente}",
            )
            modelo, perdas, segundos = _treinar(sequencia, passos, semente)
            meta = {
                "nome": nome,
                "exp": exp,
                "fracao": fracao,
                "dobra": rotulo_dobra,
                "canal_deixado_fora": canal_fora,
                "semente": semente,
                "passos": passos,
                "tamanho_s": len(pool_s),
                "tamanho_r_dobra": len(pool_r_dobra),
                "tempo_treino_s": segundos,
                "perdas": perdas,
                "comando": f"python -m tab.maos_braco_detector rodar (unidade {nome})",
            }
            _salvar_pesos(modelo, nome, meta)
        quadros = _avaliar_g(modelo, canal_fora)
    _gravar_json(
        DIR_RESULTADOS / f"{nome}.json",
        {
            "nome": nome,
            "exp": exp,
            "fracao": fracao,
            "dobra": rotulo_dobra,
            "canal_deixado_fora": canal_fora,
            "semente": semente,
            "passos": passos,
            "tempo_treino_s": meta["tempo_treino_s"],
            "quadros": quadros,
        },
    )
    return nome


def _plano() -> Iterator[tuple[str, str, int | None, int]]:
    """Ordem da Emenda 1: A3-100, A1, A2-100, A2 com 25 e 50, A3 com 25 e 50.

    Yields:
        ``(exp, fracao, dobra, semente)``; dobra é None em A1.
    """
    n_dobras = len(canais_g())
    for semente in SEMENTES:
        for k in range(n_dobras):
            yield ("A3", "100", k, semente)
    for semente in SEMENTES:
        yield ("A1", "100", None, semente)
    for semente in SEMENTES:
        for k in range(n_dobras):
            yield ("A2", "100", k, semente)
    for fracao in ("25", "50"):
        for k in range(n_dobras):
            yield ("A2", fracao, k, SEMENTE_FRACOES)
    for fracao in ("25", "50"):
        for k in range(n_dobras):
            yield ("A3", fracao, k, SEMENTE_FRACOES)


def rodar() -> int:
    """Roda o plano inteiro, retomável: pula as unidades com resultado gravado.

    Returns:
        0 ao terminar.
    """
    passos = passos_do_orcamento()
    pool_s = _pool_s()
    pool_r = _pool_r()
    print(f"plano: passos={passos}, S={len(pool_s)}, R={len(pool_r)}", file=sys.stderr)
    for exp, fracao, dobra, semente in _plano():
        rotulo_dobra = DOBRA_A1 if dobra is None else dobra
        nome = _nome_unidade(exp, fracao, rotulo_dobra, semente)
        if (DIR_RESULTADOS / f"{nome}.json").exists():
            continue
        inicio = time.perf_counter()
        _executar_unidade(exp, fracao, dobra, semente, passos, pool_s, pool_r)
        print(f"{nome}: {time.perf_counter() - inicio:.1f} s", file=sys.stderr)
    return 0


def _quadro_v1(versao: int = 1) -> list[dict]:
    """Oráculo (V1): mapas perfeitos desenhados a partir do rótulo G.

    Args:
        versao: decodificador a usar (1 ou 2).

    Returns:
        Medidas por quadro G (todos os 64).
    """
    gabarito = _gabarito()
    quadros = []
    for entrada in _entradas_g(None):
        alvo_g = mapas_alvo(entrada["rotulo_na_faixa"])
        mapa = 1.0 / (1.0 + np.exp(-(LOGIT_CRISTA * alvo_g + LOGIT_FUNDO)))
        dec = decodificar_versao(mapa.astype(np.float32), versao)
        marcas = marcas_do_registro(gabarito[entrada["id"]])
        classe, medida = _medir(dec, np.asarray(entrada["matriz"], dtype=float), marcas)
        quadros.append(
            {
                "id": entrada["id"],
                "canal": entrada["canal"],
                "classe": classe,
                "erros": medida,
            }
        )
    return quadros


def _contagem(quadros: list[dict]) -> dict[str, int]:
    """Quantidade de quadros por classe.

    Args:
        quadros: entradas com a chave ``classe``.

    Returns:
        Dicionário classe -> quantidade (todas as classes presentes).
    """
    return {c: sum(1 for q in quadros if q["classe"] == c) for c in CLASSES}


def v1() -> int:
    """Portão V1: oráculo passa pela cadeia de geometria e de métrica.

    Returns:
        0 se passou (>= 95 % certo), 1 se não passou.
    """
    quadros = _quadro_v1()
    contagem = _contagem(quadros)
    total = len(quadros)
    passou = contagem["certo"] / total >= LIMITE_V1
    dados = {
        "portao": "V1",
        "quadros": total,
        "contagem": contagem,
        "limite": LIMITE_V1,
        "passou": passou,
        "nao_certos": [q["id"] for q in quadros if q["classe"] != "certo"],
    }
    _gravar_json(ARQUIVO_V1, dados)
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    return 0 if passou else 1


def _amostras_v2(pool: list[tuple[str, dict]]) -> list[tuple]:
    """32 amostras S fixas (sorteio da semente da V2), sem aumento.

    Args:
        pool: quadros S.

    Returns:
        Itens ``(caminho, registro, semente_perturbacao, None)``.
    """
    rng = random.Random(f"{SEMENTE}:V2")
    escolhidas = rng.sample(pool, AMOSTRAS_V2)
    return [(c, r, rng.getrandbits(31), None) for c, r in escolhidas]


def _faixa_da_amostra(item: tuple) -> tuple[np.ndarray, np.ndarray, Marcas]:
    """Faixa BGR, matriz e marcas no quadro de uma amostra S (mesma perturbação do treino).

    Args:
        item: item de ``_amostras_v2`` (caminho, registro, semente).

    Returns:
        ``(faixa, matriz, alvo)``.
    """
    caminho, registro, semente, _ = item
    marcas = marcas_do_registro(registro)
    matriz = matriz_da_faixa(perturbar(eixo_da_faixa(marcas), random.Random(semente)))
    return recortar(_imagem(Path(caminho)), matriz), matriz, marcas


def v2() -> int:
    """Portão V2 (Emenda 3) sob a trava de GPU: sobreajuste em 32 amostras S.

    Returns:
        0 se (perda - piso) cai 10 vezes e >= 90 % certo nas 32, 1 caso contrário.
    """
    with _trava_gpu():
        return _v2()


def _piso_da_bce(amostras: list[tuple]) -> float:
    """Piso da BCE: perda do alvo contra ele mesmo, com o mesmo ``pos_weight`` (Emenda 3).

    O logit é ``logit(alvo)`` com o alvo limitado a ``[1e-6, 1 - 1e-6]``. Média sobre as
    amostras (cada uma com o mesmo alvo do treino, sem aumento).

    Args:
        amostras: itens de ``_amostras_v2``.

    Returns:
        Piso em nats por pixel e canal.
    """
    criterio = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(PESO_POSITIVO))
    total = 0.0
    for item in amostras:
        _, alvo_u8 = _Itens([item])[0]
        y = torch.from_numpy(alvo_u8.astype(np.float32) / 255.0)[None]
        z = torch.logit(y.clamp(1e-6, 1.0 - 1e-6))
        total += float(criterio(z, y))
    return total / len(amostras)


def _pintar_canais(mapas: np.ndarray) -> np.ndarray:
    """Quatro canais coloridos num quadro BGR: corda 1 vermelha, corda 6 azul, trastes
    amarelos e nut verde (Emenda 3).

    Args:
        mapas: ``(4, 192, 1024)`` em [0, 1].

    Returns:
        Imagem BGR uint8 ``(192, 1024, 3)``.
    """
    tela = np.zeros((ALTURA_FAIXA, LARGURA_FAIXA, 3), dtype=np.float64)
    for canal, cor in enumerate(CORES_CANAIS):
        tela += mapas[canal][..., None] * np.array(cor, dtype=np.float64)
    return np.clip(tela, 0, 255).astype(np.uint8)


def _desenhar_decodificado(faixa: np.ndarray, dec: dict) -> np.ndarray:
    """Marcas decodificadas (pontos, cordas e números) sobre a faixa de entrada.

    Args:
        faixa: faixa BGR uint8.
        dec: resultado de ``decodificar``.

    Returns:
        Cópia da faixa com as marcas.
    """
    img = faixa.copy()
    if not dec["achou"]:
        cv2.putText(
            img,
            "nao achou: " + dec["motivo"],
            (6, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            1,
        )
        return img

    def ponto(p: list) -> tuple[int, int]:
        """Ponto inteiro para o OpenCV."""
        return round(p[0]), round(p[1])

    cv2.line(img, ponto(dec["corda1"][0]), ponto(dec["corda1"][1]), (0, 0, 255), 1)
    cv2.line(img, ponto(dec["corda6"][0]), ponto(dec["corda6"][1]), (255, 0, 0), 1)
    cv2.circle(img, ponto(dec["nut"]), 5, (0, 255, 0), 2)
    for n, p in dec["trastes"].items():
        cv2.circle(img, ponto(p), 3, (0, 255, 255), -1)
        cv2.putText(
            img,
            str(n),
            (ponto(p)[0] + 4, ponto(p)[1] - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
        )
    return img


def _folha_v2(
    faixas: list[np.ndarray],
    alvos: list[np.ndarray],
    mapas: list[np.ndarray],
    decs: list[dict],
) -> np.ndarray:
    """Folha de conferência: uma linha por amostra com entrada, alvo, saída e decodificado.

    Args:
        faixas: faixas BGR uint8 das amostras.
        alvos: alvos ``(4, 192, 1024)`` em [0, 1].
        mapas: saídas sigmoides ``(4, 192, 1024)``.
        decs: resultados de ``decodificar``.

    Returns:
        Imagem BGR uint8 com as linhas empilhadas.
    """
    separador = np.full((ALTURA_FAIXA, 8, 3), 60, dtype=np.uint8)
    linhas = []
    for faixa, alvo, mapa, dec in zip(faixas, alvos, mapas, decs, strict=True):
        paineis = [
            faixa.copy(),
            _pintar_canais(alvo),
            _pintar_canais(mapa),
            _desenhar_decodificado(faixa, dec),
        ]
        for rotulo, painel in zip(
            ("entrada", "alvo", "saida", "decodificado"), paineis, strict=True
        ):
            cv2.putText(
                painel,
                rotulo,
                (6, ALTURA_FAIXA - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )
        linha = paineis[0]
        for painel in paineis[1:]:
            linha = np.hstack([linha, separador, painel])
        linhas.append(linha)
    largura = linhas[0].shape[1]
    separador_h = np.full((8, largura, 3), 60, dtype=np.uint8)
    pilha = []
    for linha in linhas:
        pilha += [linha, separador_h]
    return np.vstack(pilha[:-1])


def _estatisticas_canais(alvos: list[np.ndarray], mapas: list[np.ndarray]) -> dict:
    """Diagnóstico por canal: mínimo, máximo e fração de pixels > 0,5 no alvo e na saída.

    Também a matriz de ordem: ``M[i, j]`` é a média da saída do canal i nos pixels em que
    o alvo do canal j passa de 0,5. A ordem está certa se o maior ``M[:, j]`` cai em i = j.

    Args:
        alvos: alvos ``(4, 192, 1024)``.
        mapas: saídas sigmoides ``(4, 192, 1024)``.

    Returns:
        Dicionário com as estatísticas.
    """
    a = np.stack(alvos).astype(np.float32)
    m = np.stack(mapas).astype(np.float32)
    matriz = np.zeros((CANAIS_ALVO, CANAIS_ALVO))
    for j in range(CANAIS_ALVO):
        pixels = a[:, j] > 0.5
        for i in range(CANAIS_ALVO):
            matriz[i, j] = (
                float(m[:, i][pixels].mean()) if pixels.any() else float("nan")
            )
    ordem_certa = all(int(np.argmax(matriz[:, j])) == j for j in range(CANAIS_ALVO))
    return {
        "alvo_min": [float(a[:, c].min()) for c in range(CANAIS_ALVO)],
        "alvo_max": [float(a[:, c].max()) for c in range(CANAIS_ALVO)],
        "alvo_fracao_maior_0_5": [
            float((a[:, c] > 0.5).mean()) for c in range(CANAIS_ALVO)
        ],
        "saida_fracao_maior_0_5": [
            float((m[:, c] > 0.5).mean()) for c in range(CANAIS_ALVO)
        ],
        "matriz_saida_por_alvo": matriz.tolist(),
        "ordem_da_saida_igual_ao_alvo": ordem_certa,
    }


def _v2() -> int:
    """Corpo do V2 (Emenda 3), chamado com a GPU reservada.

    Taxa constante, 1.000 passos, sem aumento. Critérios: (perda - piso) cai 10 vezes
    (médias dos 10 primeiros e dos 10 últimos passos), e >= 90 % certos nas 32 amostras.

    Returns:
        0 se passou, 1 caso contrário.
    """
    pool = _pool_s()
    amostras = _amostras_v2(pool)
    rng = random.Random(f"{SEMENTE}:V2:seq")
    sequencia = [amostras[rng.randrange(AMOSTRAS_V2)] for _ in range(PASSOS_V2 * LOTE)]
    curta = sequencia[: 20 * LOTE]
    opcoes = {"constante": True, "trabalhadores": TRABALHADORES_V2}
    _, perdas_a, _ = _treinar(curta, 20, semente=1, **opcoes)
    _, perdas_b, _ = _treinar(curta, 20, semente=1, **opcoes)
    determinismo = perdas_a == perdas_b
    modelo, perdas, segundos = _treinar(sequencia, PASSOS_V2, semente=1, **opcoes)
    _salvar_pesos(
        modelo,
        "v2_sobreajuste",
        {"comando": "v2", "semente": 1, "passos": PASSOS_V2, "segundos": segundos},
    )
    inicial = statistics.mean(perdas[:10])
    final = statistics.mean(perdas[-10:])
    piso = _piso_da_bce(amostras)
    criterio_a = (final - piso) <= (inicial - piso) / LIMITE_V2_QUEDA
    faixas, matrizes, alvos_u8, alvos = [], [], [], []
    for item in amostras:
        faixa, matriz, _ = _faixa_da_amostra(item)
        _, alvo_u8 = _Itens([item])[0]
        faixas.append(faixa)
        matrizes.append(matriz)
        alvos.append(alvo_u8.astype(np.float32) / 255.0)
        alvos_u8.append(alvo_u8)
    mapas = prever_mapas(modelo, faixas)
    quadros = []
    decs = []
    for mapa, matriz, item in zip(mapas, matrizes, amostras, strict=True):
        dec = decodificar(mapa)
        decs.append(dec)
        classe, _ = _medir(dec, matriz, _marcas_da_amostra(item))
        quadros.append({"classe": classe})
    contagem = _contagem(quadros)
    certo = contagem["certo"] / len(quadros)
    passou = criterio_a and certo >= LIMITE_V2_CERTO
    _gravar_imagem(
        MAOS_M21 / "v2_folha.jpg",
        _folha_v2(faixas[:4], alvos[:4], mapas[:4], decs[:4]),
    )
    dados = {
        "portao": "V2",
        "determinismo_duas_execucoes_iguais": determinismo,
        "perda_inicial": inicial,
        "perda_final": final,
        "piso": piso,
        "inicial_menos_piso": inicial - piso,
        "final_menos_piso": final - piso,
        "criterio_a_passou": criterio_a,
        "contagem": contagem,
        "certo_fracao": certo,
        "tempo_treino_s": segundos,
        "passou": passou,
        "diagnostico": _estatisticas_canais(alvos, mapas),
        "perdas": perdas,
    }
    _gravar_json(ARQUIVO_V2, dados)
    print(json.dumps({k: v for k, v in dados.items() if k != "perdas"}, indent=2))
    return 0 if passou else 1


def _marcas_da_amostra(item: tuple) -> Marcas:
    """Marcas do quadro de uma amostra S (o rótulo exato).

    Args:
        item: item de ``_amostras_v2``.

    Returns:
        Marcas no quadro.
    """
    return marcas_do_registro(item[1])


def _gravar_imagem(caminho: Path, imagem: np.ndarray) -> None:
    """Grava uma imagem JPEG, criando a pasta se preciso.

    Args:
        caminho: arquivo de destino.
        imagem: BGR uint8.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(caminho), imagem, [cv2.IMWRITE_JPEG_QUALITY, 90])


def _amostra_sval(i: int) -> tuple[np.ndarray, list, dict]:
    """Amostra S de validação ``i``, gerada na hora com a semente ``Sval:<i>``.

    Args:
        i: índice da amostra.

    Returns:
        ``(faixa, matriz, registro)``.
    """
    fundos = _CONTEXTO["fundos"]
    proibidos = _CONTEXTO["proibidos"]
    rng = random.Random(f"{SEMENTE}:Sval:{i}")
    entrada = fundos[rng.randrange(len(fundos))]
    entradas_mao = [fundos[rng.randrange(len(fundos))] for _ in range(QUADROS_PELE)]
    conferir_fora_m11b(entrada["arquivo"], proibidos)
    for entrada_mao in entradas_mao:
        conferir_fora_m11b(entrada_mao["arquivo"], proibidos)
    fundo = _imagem(DIR_FUNDOS / entrada["jpg"])
    fundos_mao = [_imagem(DIR_FUNDOS / e["jpg"]) for e in entradas_mao]
    img, registro = gerar(rng, fundo, fundos_mao)
    matriz = matriz_da_faixa(
        perturbar(eixo_da_faixa(marcas_do_registro(registro)), rng)
    )
    return recortar(img, matriz), matriz.tolist(), registro


def _iniciar_sval(fundos: list[dict], proibidos: frozenset[str]) -> None:
    """Contexto do processo que gera Sval.

    Args:
        fundos: entradas de ``fundos/indice.json``.
        proibidos: conjunto de ``videos_proibidos``.
    """
    _CONTEXTO["fundos"] = fundos
    _CONTEXTO["proibidos"] = proibidos


def _gerar_sval() -> list[tuple[np.ndarray, list, dict]]:
    """Gera as ``AMOSTRAS_SVAL`` amostras S de validação, em paralelo.

    Returns:
        Lista de ``(faixa, matriz, registro)``.
    """
    fundos = _ler_json(DIR_FUNDOS / "indice.json")["fundos"]
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=PROCESSOS_SVAL,
        initializer=_iniciar_sval,
        initargs=(fundos, videos_proibidos()),
    ) as executor:
        return list(executor.map(_amostra_sval, range(AMOSTRAS_SVAL), chunksize=8))


def v3() -> int:
    """Portão V3 e V4: treino A1 completo (semente 1), medido em S fora do treino.

    Grava o peso como a unidade A1 da semente 1 (reusada pela rodada) e o tempo que dá a
    V4. Se o total previsto passa de 10 h, reduz os passos igualmente e grava em
    ``v4_tempo.json``.

    Returns:
        0 ao terminar (a decisão de seguir é do dono, pelo número gravado).
    """
    passos = PASSOS
    amostras = _gerar_sval()
    pool_s = _pool_s()
    sequencia = _sequencia(pool_s, [], passos, MISTURA["A1"], "A1:100:sem:1")
    nome = _nome_unidade("A1", "100", DOBRA_A1, 1)
    with _trava_gpu():
        modelo, perdas, segundos = _treinar(sequencia, passos, semente=1)
        _salvar_pesos(
            modelo,
            nome,
            {
                "nome": nome,
                "exp": "A1",
                "fracao": "100",
                "dobra": DOBRA_A1,
                "canal_deixado_fora": None,
                "semente": 1,
                "passos": passos,
                "tamanho_s": len(pool_s),
                "tamanho_r_dobra": 0,
                "tempo_treino_s": segundos,
                "perdas": perdas,
                "comando": "python -m tab.maos_braco_detector v3",
            },
        )
        mapas = prever_mapas(modelo, [a[0] for a in amostras])
    classes = []
    for mapa, (_, matriz, registro) in zip(mapas, amostras, strict=True):
        dec = decodificar(mapa)
        classe, _ = _medir(
            dec, np.asarray(matriz, dtype=float), marcas_do_registro(registro)
        )
        classes.append(classe)
    contagem = {c: classes.count(c) for c in CLASSES}
    certo = contagem["certo"] / len(classes)
    previsto_h = segundos * 83 / 3600.0
    reduzir = previsto_h > ORCAMENTO_HORAS
    passos_novos = (
        math.floor(passos * ORCAMENTO_HORAS / previsto_h) if reduzir else passos
    )
    _gravar_json(
        ARQUIVO_V3,
        {
            "portao": "V3",
            "amostras": len(classes),
            "contagem": contagem,
            "certo_fracao": certo,
            "abaixo_de_50": certo < LIMITE_V3_CERTO,
            "passos": passos,
            "tempo_treino_s": segundos,
        },
    )
    _gravar_json(
        ARQUIVO_V4,
        {
            "portao": "V4",
            "tempo_um_treino_s": segundos,
            "treinos": 83,
            "previsto_h": previsto_h,
            "orcamento_h": ORCAMENTO_HORAS,
            "reduziu": reduzir,
            "passos": passos_novos,
        },
    )
    print(
        f"V3 certo={certo:.3f} {contagem}; V4 tempo={segundos:.0f} s, "
        f"previsto={previsto_h:.2f} h, passos={passos_novos}",
        file=sys.stderr,
    )
    return 0


def _medias_e_amplitude(valores: list[float]) -> dict:
    """Média e amplitude (máximo menos mínimo) de valores entre sementes.

    Args:
        valores: uma medida por semente.

    Returns:
        Dicionário com ``media``, ``amplitude`` e ``valores``.
    """
    return {
        "media": statistics.mean(valores),
        "amplitude": max(valores) - min(valores),
        "valores": valores,
    }


def resumo() -> int:
    """Resumo de todos os resultados: por experimento e fração, média e amplitude.

    Grava ``resumo.json``. Por experimento e fração: média e amplitude de certo,
    impreciso, falso e não achou (em % dos quadros medidos) entre as sementes; medianas
    de ``perp_cordas`` e ``pior_traste_casas``; tabela por canal (média entre sementes).

    Returns:
        0 ao terminar.
    """
    grupos: dict[tuple[str, str], dict[int, list[dict]]] = {}
    for caminho in sorted(DIR_RESULTADOS.glob("*.json")):
        dados = _ler_json(caminho)
        grupos.setdefault((dados["exp"], dados["fracao"]), {}).setdefault(
            dados["semente"], []
        ).extend(dados["quadros"])
    saida: dict = {}
    for (exp, fracao), por_semente in sorted(grupos.items()):
        sementes = sorted(por_semente)
        por_classe: dict[str, dict] = {}
        for classe in CLASSES[:4]:
            pct = [
                100.0
                * sum(q["classe"] == classe for q in por_semente[s])
                / len(por_semente[s])
                for s in sementes
            ]
            por_classe[classe] = _medias_e_amplitude(pct)
        todos = [q for s in sementes for q in por_semente[s]]
        perp = [q["erros"]["perp_cordas"] for q in todos if q["erros"]]
        pior = [
            q["erros"]["pior_traste_casas"]
            for q in todos
            if q["erros"] and q["erros"]["pior_traste_casas"] is not None
        ]
        canais: dict[str, dict] = {}
        for canal in sorted({q["canal"] for q in todos}):
            canais[canal] = {
                "quadros_por_semente": statistics.mean(
                    sum(q["canal"] == canal for q in por_semente[s]) for s in sementes
                ),
                **{
                    classe: statistics.mean(
                        100.0
                        * sum(
                            q["canal"] == canal and q["classe"] == classe
                            for q in por_semente[s]
                        )
                        / max(1, sum(q["canal"] == canal for q in por_semente[s]))
                        for s in sementes
                    )
                    for classe in CLASSES[:4]
                },
            }
        saida[f"{exp}_{fracao}"] = {
            "sementes": sementes,
            "quadros_por_semente": {str(s): len(por_semente[s]) for s in sementes},
            "percentuais": por_classe,
            "mediana_perp_cordas": statistics.median(perp) if perp else None,
            "mediana_pior_traste_casas": statistics.median(pior) if pior else None,
            "por_canal_media_entre_sementes_pct": canais,
        }
    _gravar_json(ARQUIVO_RESUMO, saida)
    for nome, bloco in saida.items():
        print(nome, json.dumps(bloco["percentuais"], ensure_ascii=False))
    return 0


def _itens_final(
    pool_s: list[tuple[str, dict]],
    pool_r: list[dict],
    semente: int,
    passos: int = PASSOS,
) -> list[tuple]:
    """Sequência da unidade final (rodada 1022): S e R de todos os canais, sem dobra.

    A mistura é a de A3 (``MISTURA["A3"]``). Os R entram todos, sem deixar canal de fora.

    Args:
        pool_s: quadros S.
        pool_r: quadros R de todos os canais (de ``_pool_r``).
        semente: semente do treino, para o sorteio da sequência.
        passos: número de passos (``PASSOS`` na unidade final).

    Returns:
        Lista de ``passos * LOTE`` tuplas para ``_Itens``.
    """
    return _sequencia(pool_s, pool_r, passos, MISTURA["A3"], f"final:{semente}")


def treinar_final(semente: int) -> int:
    """Treina a unidade final ``A3_100_todos_s<semente>`` e grava só o peso.

    S e todos os R dos 8 canais, em ``PASSOS`` passos fixos (sem orçamento do V4), sob a
    trava de GPU. Não mede nada: a prova é feita depois, pelo subcomando ``prova``.

    Args:
        semente: semente do treino.

    Returns:
        0 ao terminar.
    """
    pool_s = _pool_s()
    pool_r = _pool_r()
    nome = f"A3_100_todos_s{semente}"
    sequencia = _itens_final(pool_s, pool_r, semente)
    with _trava_gpu():
        modelo, perdas, segundos = _treinar(sequencia, PASSOS, semente)
        _salvar_pesos(
            modelo,
            nome,
            {
                "nome": nome,
                "exp": "A3",
                "fracao": "100",
                "dobra": "todos",
                "canal_deixado_fora": None,
                "semente": semente,
                "passos": PASSOS,
                "tamanho_s": len(pool_s),
                "tamanho_r": len(pool_r),
                "tempo_treino_s": segundos,
                "perdas": perdas,
                "comando": (
                    f"python -m tab.maos_braco_detector final --semente {semente}"
                ),
            },
        )
    print(f"{nome} gravada em {segundos:.0f} s", file=sys.stderr)
    return 0


def treinar_unidade(exp: str, fracao: str, dobra: int | None, semente: int) -> int:
    """Treina e mede uma única unidade (CLI ``treinar``).

    Args:
        exp: ``A1``, ``A2`` ou ``A3``.
        fracao: ``25``, ``50`` ou ``100``.
        dobra: índice k, ou None em A1.
        semente: semente.

    Returns:
        0 ao terminar.
    """
    passos = passos_do_orcamento()
    nome = _executar_unidade(exp, fracao, dobra, semente, passos, _pool_s(), _pool_r())
    print(f"unidade {nome} gravada", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Rodada 1022: portões D1 a D3 (desenvolvimento) e prova M11b (lacrada)
# ---------------------------------------------------------------------------


def _contagem_chave(quadros: list[dict], chave: str) -> dict[str, int]:
    """Quantidade de quadros por classe, lida de ``chave``.

    Args:
        quadros: entradas com a chave indicada.
        chave: nome da chave com a classe (``classe_v1``, ``classe_v2``...).

    Returns:
        Dicionário classe -> quantidade.
    """
    return {c: sum(1 for q in quadros if q[chave] == c) for c in CLASSES}


def _medir_r_fora(modelo: nn.Module, entradas: list[dict]) -> list[dict]:
    """Mede a rede nos quadros R de um canal deixado de fora, com a v1 e a v2 (D2).

    A perturbação é fixa (``SEMENTE_D2``) e o rótulo é o do rastreador (R).

    Args:
        modelo: rede treinada sem o canal dos ``entradas``.
        entradas: entradas de ``_pool_r`` com o canal deixado de fora.

    Returns:
        Uma entrada por quadro: ``id``, ``canal``, ``classe_v1``, ``classe_v2`` e os
        erros de cada versão.
    """
    faixas, matrizes, marcas = [], [], []
    for entrada in entradas:
        caminho = Path(entrada["caminho"])
        alvo = marcas_do_registro(entrada["registro"])
        eixo = eixo_da_faixa(alvo)
        matriz = matriz_da_faixa(
            perturbar(eixo, random.Random(f"{SEMENTE_D2}:{caminho.stem}"))
        )
        faixas.append(recortar(_imagem(caminho), matriz))
        matrizes.append(matriz)
        marcas.append(alvo)
    mapas = prever_mapas(modelo, faixas)
    quadros = []
    for entrada, mapa, matriz, alvo in zip(
        entradas, mapas, matrizes, marcas, strict=True
    ):
        linha: dict = {
            "id": Path(entrada["caminho"]).stem,
            "canal": entrada["canal"],
        }
        for versao in (1, 2):
            dec = decodificar_versao(mapa, versao)
            classe, medida = _medir(dec, matriz, alvo)
            linha[f"classe_v{versao}"] = classe
            linha[f"erros_v{versao}"] = medida
        quadros.append(linha)
    return quadros


def d1() -> int:
    """Portão D1 (1022): oráculo de G pelo decodificador v2, com a v1 ao lado.

    Só desenvolvimento, sem modelo: mapas perfeitos de G. Passa com >= 95 % certo.

    Returns:
        0 se passou, 1 caso contrário.
    """
    quadros_v2 = _quadro_v1(versao=2)
    quadros_v1 = _quadro_v1(versao=1)
    contagem = _contagem(quadros_v2)
    total = len(quadros_v2)
    passou = contagem["certo"] / total >= LIMITE_V1
    dados = {
        "portao": "D1",
        "decodificador": 2,
        "tolerancia_v2": TOLERANCIA_V2,
        "quadros": total,
        "contagem": contagem,
        "contagem_v1_mesmo_oraculo": _contagem(quadros_v1),
        "limite": LIMITE_V1,
        "passou": passou,
        "nao_certos": [q["id"] for q in quadros_v2 if q["classe"] != "certo"],
    }
    _gravar_json(ARQUIVO_D1, dados)
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    return 0 if passou else 1


def d2() -> int:
    """Portão D2 (1022): pesos ``A3_100_<k>_s1`` aplicados aos R do canal k.

    O canal k ficou de fora do treino da dobra k, então os R dele são fora da dobra.
    Só registro: certos e falsos contra o rótulo R, com a v1 e a v2.

    Returns:
        0 ao terminar.
    """
    pool_r = _pool_r()
    por_dobra = []
    todos: list[dict] = []
    for k, canal in enumerate(canais_g()):
        nome = _nome_unidade("A3", "100", k, 1)
        passos = _ler_json(DIR_PESOS / f"{nome}.json")["passos"]
        entradas = [e for e in pool_r if e["canal"] == canal]
        with _trava_gpu():
            modelo, _ = _carregar_pesos(nome, passos)
            quadros = _medir_r_fora(modelo, entradas)
        por_dobra.append(
            {
                "dobra": k,
                "canal": canal,
                "peso": nome,
                "quadros": len(quadros),
                "contagem_v1": _contagem_chave(quadros, "classe_v1"),
                "contagem_v2": _contagem_chave(quadros, "classe_v2"),
            }
        )
        todos.extend(quadros)
    dados = {
        "portao": "D2",
        "tolerancia_v2": TOLERANCIA_V2,
        "por_dobra": por_dobra,
        "total": {
            "quadros": len(todos),
            "contagem_v1": _contagem_chave(todos, "classe_v1"),
            "contagem_v2": _contagem_chave(todos, "classe_v2"),
        },
        "quadros": todos,
    }
    _gravar_json(ARQUIVO_D2, dados)
    print(json.dumps(dados["total"], ensure_ascii=False, indent=2))
    return 0


def d3() -> int:
    """Portão D3 (1022): peso ``A1_100_sem_s1`` nos 500 S de validação, v1 e v2.

    Os S são gerados como no V3. A contagem da v1 deve reproduzir a do V3 gravado
    (``v3_validacao_s.json``); é conferência, não critério. Só registro.

    Returns:
        0 ao terminar.
    """
    amostras = _gerar_sval()
    nome = _nome_unidade("A1", "100", DOBRA_A1, 1)
    passos = _ler_json(DIR_PESOS / f"{nome}.json")["passos"]
    with _trava_gpu():
        modelo, _ = _carregar_pesos(nome, passos)
        mapas = prever_mapas(modelo, [a[0] for a in amostras])
    quadros: list[dict] = []
    for mapa, (_, matriz, registro) in zip(mapas, amostras, strict=True):
        alvo = marcas_do_registro(registro)
        linha: dict = {}
        for versao in (1, 2):
            dec = decodificar_versao(mapa, versao)
            classe, _ = _medir(dec, np.asarray(matriz, dtype=float), alvo)
            linha[f"classe_v{versao}"] = classe
        quadros.append(linha)
    dados = {
        "portao": "D3",
        "peso": nome,
        "tolerancia_v2": TOLERANCIA_V2,
        "amostras": len(quadros),
        "contagem_v1": _contagem_chave(quadros, "classe_v1"),
        "contagem_v2": _contagem_chave(quadros, "classe_v2"),
        "v3_gravado": _ler_json(ARQUIVO_V3)["contagem"]
        if ARQUIVO_V3.exists()
        else None,
    }
    _gravar_json(ARQUIVO_D3, dados)
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    return 0


def _canal_por_quadro(ids: set[str]) -> dict[str, str]:
    """Canal de cada quadro da prova, pelo índice da M11b (ou pelos vídeos sorteados).

    Args:
        ids: identificadores dos quadros da prova.

    Returns:
        Quadro -> canal.

    Raises:
        ValueError: se algum quadro não está no índice da M11b.
    """
    indice = _ler_json(MAOS_M11B / "indice.json")["quadros"]
    chaves = _ler_json(MAOS_M11B / "chaves.json")["videos"]
    canal_do_arquivo = {v["arquivo"]: v["canal"] for v in chaves}
    canais: dict[str, str] = {}
    for quadro in indice:
        if quadro["id"] in ids:
            canais[quadro["id"]] = (
                quadro.get("canal") or canal_do_arquivo[quadro["arquivo"]]
            )
    faltam = sorted(ids - set(canais))
    if faltam:
        raise ValueError(f"quadros da prova fora do índice da M11b: {faltam}")
    return canais


def _entradas_prova() -> list[dict]:
    """Os 28 quadros da prova M11b, com a faixa recortada e as marcas do dono.

    A perturbação é ``random.Random("20261021:T:<id>")``, a mesma que o pré-registro
    fixa. Lê o gabarito e as imagens da M11b: só deve ser chamada na prova lacrada.

    Returns:
        Uma entrada por quadro: ``id``, ``canal``, ``faixa``, ``matriz`` e ``marcas``.

    Raises:
        ValueError: se algum quadro não tem braço ou marcas completas.
    """
    gabarito = _ler_json(GABARITO_BRACO_M11B)["quadros"]
    canais = _canal_por_quadro(set(QUADROS_PROVA))
    entradas = []
    for id_quadro in QUADROS_PROVA:
        marcas = marcas_do_registro(gabarito[id_quadro])
        if marcas is None:
            raise ValueError(f"{id_quadro} sem braço ou marcas completas")
        imagem = _imagem(MAOS_M11B / "quadros" / f"{id_quadro}.png")
        matriz = matriz_da_faixa(
            perturbar(
                eixo_da_faixa(marcas),
                random.Random(f"{SEMENTE_PROVA}:{id_quadro}"),
            )
        )
        entradas.append(
            {
                "id": id_quadro,
                "canal": canais[id_quadro],
                "faixa": recortar(imagem, matriz),
                "matriz": matriz,
                "marcas": marcas,
            }
        )
    return entradas


def _agregar_prova(por_semente: dict[int, list[dict]]) -> dict:
    """Resumo da prova: classes por semente, média, canais, medianas e o critério.

    Args:
        por_semente: semente -> uma entrada por quadro, com ``classe``, ``canal`` e
            ``erros`` (``None`` se não houve medida).

    Returns:
        Dicionário com ``por_semente``, ``media`` (por classe, com amplitude), ``canais``,
        ``medianas`` e ``passou`` (certos >= 70 % e falsos <= 5 %, pela média).
    """
    sementes = sorted(por_semente)
    por_classe: dict[str, dict] = {}
    for classe in CLASSES[:4]:
        pct = [
            100.0
            * sum(q["classe"] == classe for q in por_semente[s])
            / len(por_semente[s])
            for s in sementes
        ]
        por_classe[classe] = _medias_e_amplitude(pct)
    todos = [q for s in sementes for q in por_semente[s]]
    canais = {}
    for canal in sorted({q["canal"] for q in todos}):
        canais[canal] = {
            classe: statistics.mean(
                100.0
                * sum(
                    q["canal"] == canal and q["classe"] == classe
                    for q in por_semente[s]
                )
                / max(1, sum(q["canal"] == canal for q in por_semente[s]))
                for s in sementes
            )
            for classe in CLASSES[:4]
        }
        canais[canal]["quadros"] = sum(
            q["canal"] == canal for q in por_semente[sementes[0]]
        )

    def mediana(chave: str) -> float | None:
        valores = [
            q["erros"][chave]
            for q in todos
            if q["erros"] and q["erros"].get(chave) is not None
        ]
        return statistics.median(valores) if valores else None

    media_certo = por_classe["certo"]["media"]
    media_falso = por_classe["falso"]["media"]
    return {
        "portao": "PROVA_M11B",
        "pesos": [f"A3_100_todos_s{s}" for s in sementes],
        "tolerancia_v2": TOLERANCIA_V2,
        "quadros": len(por_semente[sementes[0]]),
        "por_semente": {str(s): _contagem(por_semente[s]) for s in sementes},
        "percentuais": por_classe,
        "canais_media_pct": canais,
        "medianas": {
            "perp_cordas": mediana("perp_cordas"),
            "nut_casas": mediana("nut_casas"),
            "pior_traste_casas": mediana("pior_traste_casas"),
        },
        "criterio": {
            "certo_minimo_pct": LIMITE_PROVA_CERTO,
            "falso_maximo_pct": LIMITE_PROVA_FALSO,
        },
        "passou": media_certo >= LIMITE_PROVA_CERTO
        and media_falso <= LIMITE_PROVA_FALSO,
    }


def prova(destino: Path = ARQUIVO_PROVA) -> int:
    """Prova M11b (1022): NÃO executar antes do commit do decodificador congelado.

    Aplica os 3 pesos finais (``A3_100_todos_s1..3``) com a v2 aos 28 quadros, mede
    (cordas, nut, trastes, classe) e grava o resumo em ``destino``.

    Args:
        destino: arquivo do resumo.

    Returns:
        0 ao terminar (a decisão é do dono, pelo campo ``passou``).
    """
    entradas = _entradas_prova()
    por_semente: dict[int, list[dict]] = {}
    for semente in SEMENTES_FINAIS:
        nome = f"A3_100_todos_s{semente}"
        with _trava_gpu():
            modelo, _ = _carregar_pesos(nome, PASSOS)
            mapas = prever_mapas(modelo, [e["faixa"] for e in entradas])
        quadros = []
        for entrada, mapa in zip(entradas, mapas, strict=True):
            dec = decodificar_versao(mapa, 2)
            classe, medida = _medir(dec, entrada["matriz"], entrada["marcas"])
            quadros.append(
                {
                    "id": entrada["id"],
                    "canal": entrada["canal"],
                    "classe": classe,
                    "achou": bool(dec["achou"]),
                    "erros": medida,
                }
            )
        por_semente[semente] = quadros
    dados = _agregar_prova(por_semente)
    _gravar_json(destino, dados)
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    return 0


def _parser() -> argparse.ArgumentParser:
    """Parser da CLI.

    Returns:
        Parser com os subcomandos do piloto.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("v1", help="portão V1: oráculo de G pela cadeia de medida")
    sub.add_parser("v2", help="portão V2: sobreajuste em 32 amostras S")
    sub.add_parser("v3", help="portões V3 e V4: A1 completo e tempo")
    for nome in ("treinar", "avaliar"):
        p = sub.add_parser(nome, help=f"{nome} uma unidade")
        p.add_argument("--exp", choices=("A1", "A2", "A3"), required=True)
        p.add_argument("--fracao", choices=tuple(FRACOES), default="100")
        p.add_argument("--dobra", type=int, default=None)
        p.add_argument("--semente", type=int, default=1)
    sub.add_parser("rodar", help="plano inteiro, retomável")
    sub.add_parser("resumo", help="resumo.json de todos os resultados")
    p = sub.add_parser("final", help="treina A3 sem dobra (S + todos os R), sem medir")
    p.add_argument("--semente", type=int, required=True)
    sub.add_parser("d1", help="portão D1: oráculo de G pela v2 (desenvolvimento)")
    sub.add_parser("d2", help="portão D2: R fora da dobra, v1 e v2 (desenvolvimento)")
    sub.add_parser("d3", help="portão D3: S de validação, v1 e v2 (desenvolvimento)")
    sub.add_parser("prova", help="PROVA M11b lacrada: não rodar antes do aval do dono")
    return parser


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    args = _parser().parse_args()
    if args.comando == "v1":
        return v1()
    if args.comando == "v2":
        return v2()
    if args.comando == "v3":
        return v3()
    if args.comando in ("treinar", "avaliar"):
        return treinar_unidade(args.exp, args.fracao, args.dobra, args.semente)
    if args.comando == "rodar":
        return rodar()
    if args.comando == "final":
        return treinar_final(args.semente)
    if args.comando == "d1":
        return d1()
    if args.comando == "d2":
        return d2()
    if args.comando == "d3":
        return d3()
    if args.comando == "prova":
        return prova()
    return resumo()


if __name__ == "__main__":
    sys.exit(main())
