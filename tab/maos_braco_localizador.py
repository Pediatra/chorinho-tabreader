"""Localizador do braço no quadro inteiro (rodada 1024, fase B, estágio 1).

O quadro inteiro entra na U-Net da 1021 reduzido para 640 x 360 (com borda preta, mantendo
a proporção; o canvas tem 384 linhas, porque a rede exige múltiplos de 32, e as 24 de
baixo são preto). A saída tem 5 canais: 4 pontos (corda 1 perto do nut, corda 1 longe,
corda 6 perto, corda 6 longe; gaussianas de 3 px) e 1 máscara do braço entre as cordas.

A cadeia é: estágio 1 -> faixa -> estágio 2 (v2) -> refino (segunda passada) -> sinais da
1023 (S1 com as extras da semente 1024, S2 e S3) -> regra congelada da 1023. Não usa S.

Pré-registro: ``docs/rodadas/1024-fase-b-localizador-do-braco.md``.

CLI: ``python -m tab.maos_braco_localizador {treinar,smoke,b1,b2,prova}``.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from .caminhos import GABARITO_BRACO_M11B, MAOS_M3B, MAOS_M11B, MAOS_M21
from .maos_braco_confianca import (
    N_EXTRAS,
    _constantes_congeladas,
    decodificar_com_dados,
    marcar,
    sinal_s1,
    sinal_s2,
    sinal_s3,
)
from .maos_braco_detector import (
    DIR_G,
    DIR_PESOS,
    LOTE,
    LR_CODIFICADOR,
    LR_DECODIFICADOR,
    PASSOS,
    PESO_POSITIVO,
    QUADROS_PROVA,
    SEMENTES_FINAIS,
    UNetBraco,
    _canal_por_quadro,
    _carregar_pesos,
    _dispositivo,
    _entradas_g,
    _gabarito,
    _gravar_json,
    _imagem,
    _iniciar_worker,
    _ler_json,
    _medir,
    _no_quadro,
    _nome_unidade,
    _para_modelo,
    _pool_r,
    _salvar_pesos,
    _trava_gpu,
    canais_g,
    fator_lr,
    prever_mapas,
)
from .maos_braco_faixa import (
    eixo_da_faixa,
    matriz_da_faixa,
    perturbar,
    recortar,
)
from .maos_braco_tempo import Marcas, classificar, marcas_do_registro
from .sintetico import fixar_semente

#: Entrada da rede: quadro inteiro em 640 x 360, com o canvas de 384 (múltiplo de 32).
LARGURA_ENTRADA = 640
ALTURA_CONTEUDO = 360
ALTURA_CANVAS = 384
#: Canais de saída: 4 pontos, e a presença do braço (canal 4).
CANAIS_LOCALIZADOR = 5
CANAL_PRESENCA = 4
#: Alvo: gaussiana de sigma 3 px na escala 640.
SIGMA_PONTO_PX = 3.0
#: Limiar de presença e de cada ponto (fixo, sem ajuste).
P_MIN = 0.3
#: Aumentos do treino (pré-registro): escala, rotação, translação e cor.
ESCALA_AUMENTO = (0.7, 1.3)
ROTACAO_AUMENTO_GRAUS = 10.0
TRANSLACAO_AUMENTO = 0.15
COR_AUMENTO = 0.2
#: Envelope do B1 (o mesmo da 1021): erro perpendicular em larguras, ao longo em
#: comprimentos, rotação em graus, escala em fração; passa com 90 % dentro.
ENVELOPE_PERPENDICULAR = 0.3
ENVELOPE_AO_LONGO = 0.05
ENVELOPE_ROTACAO_GRAUS = 3.0
ENVELOPE_ESCALA = 0.10
LIMITE_B1 = 0.90
#: Canais de validação do desenvolvimento: fora do treino do estágio 1 (R e G).
CANAIS_VALIDACAO = ("kenneth acoustic", "shin izumi")
#: Semente da rodada (prefixo de todos os sorteios deste módulo).
SEMENTE_TEXTO = "20261024"
#: Semente das extras do S1 da 1024: ``20261024:P:<id>:<j>``.
SEMENTE_EXTRAS_LOC = "20261024:P"
#: Prova (pré-registro): segurança e utilidade, com as medidas de cada critério.
LIMITE_FALSOS_PROVA = 0.05
LIMITE_SINALIZADOS_PROVA = 0.50
QUADRO_BRACO_NAO = "q77"
#: Trabalhadores de dados (no máximo 4: a máquina tem 15 GB de RAM).
TRABALHADORES = 4
#: Pesos e arquivos de resultado.
NOME_LOCALIZADOR_VALIDACAO = "L1_val_s1"
ARQUIVO_B1 = MAOS_M21 / "b1_envelope.json"
ARQUIVO_B2 = MAOS_M21 / "b2_cadeia.json"
ARQUIVO_PROVA = MAOS_M21 / "prova_localizador.json"
ARQUIVO_FOLHA = MAOS_M21 / "l1_folha_alvos.jpg"
#: Cores dos 4 pontos na folha (BGR): corda 1 perto, corda 1 longe, corda 6 perto/longe.
CORES_PONTOS = ((0, 0, 255), (0, 128, 255), (255, 0, 0), (255, 255, 0))
#: Ordem dos pontos no alvo: corda 1 perto, corda 1 longe, corda 6 perto, corda 6 longe.
PONTOS_POR_CORDA = 2
#: Quadrilátero do braço: corda 1 perto, corda 1 longe, corda 6 longe, corda 6 perto.
ORDEM_QUADRILATERO = (0, 1, 3, 2)
#: Classes da medida B2 e da prova (as mesmas do detector).
CHAVES_ERRO = ("perpendicular", "ao_longo", "rotacao_graus", "escala")


@dataclass(frozen=True)
class Enquadre:
    """Como o quadro original foi posto no canvas: escala por eixo e deslocamento.

    Attributes:
        sx: escala horizontal (largura do conteúdo / largura original).
        sy: escala vertical (altura do conteúdo / altura original).
        ox: deslocamento horizontal do conteúdo no canvas, em px.
        oy: deslocamento vertical do conteúdo no canvas, em px.
    """

    sx: float
    sy: float
    ox: float
    oy: float


# ---------------------------------------------------------------------------
# Quadro inteiro -> canvas 640 x 384 e de volta
# ---------------------------------------------------------------------------


def enquadrar(imagem: np.ndarray) -> tuple[np.ndarray, Enquadre]:
    """Reduz o quadro inteiro para caber em 640 x 360, com borda preta, e põe no canvas.

    O conteúdo é centrado na faixa de 360 linhas; o canvas tem 384 linhas, com as 24 de
    baixo pretas (o canvas é o que entra na rede, e ele não desloca nenhuma coordenada).

    Args:
        imagem: quadro BGR uint8 de qualquer tamanho.

    Returns:
        ``(canvas, enquadre)``: canvas BGR uint8 ``(384, 640, 3)`` e a transformação.
    """
    altura, largura = imagem.shape[:2]
    escala = min(LARGURA_ENTRADA / largura, ALTURA_CONTEUDO / altura)
    nova_largura = max(1, round(largura * escala))
    nova_altura = max(1, round(altura * escala))
    ox = (LARGURA_ENTRADA - nova_largura) // 2
    oy = (ALTURA_CONTEUDO - nova_altura) // 2
    reduzida = cv2.resize(
        imagem, (nova_largura, nova_altura), interpolation=cv2.INTER_AREA
    )
    canvas = np.zeros((ALTURA_CANVAS, LARGURA_ENTRADA, 3), dtype=np.uint8)
    canvas[oy : oy + nova_altura, ox : ox + nova_largura] = reduzida
    enquadre = Enquadre(
        sx=nova_largura / largura,
        sy=nova_altura / altura,
        ox=float(ox),
        oy=float(oy),
    )
    return canvas, enquadre


def para_canvas(pontos: np.ndarray, enquadre: Enquadre) -> np.ndarray:
    """Leva pontos do quadro original às coordenadas do canvas.

    Args:
        pontos: array ``(..., 2)`` no quadro original.
        enquadre: transformação de ``enquadrar``.

    Returns:
        Array com a mesma forma, no canvas.
    """
    escala = np.array([enquadre.sx, enquadre.sy])
    desloca = np.array([enquadre.ox, enquadre.oy])
    return np.asarray(pontos, dtype=float) * escala + desloca


def do_canvas(pontos: np.ndarray, enquadre: Enquadre) -> np.ndarray:
    """Inversa de ``para_canvas``: pontos do canvas de volta ao quadro original.

    Args:
        pontos: array ``(..., 2)`` no canvas.
        enquadre: transformação de ``enquadrar``.

    Returns:
        Array com a mesma forma, no quadro original.
    """
    escala = np.array([enquadre.sx, enquadre.sy])
    desloca = np.array([enquadre.ox, enquadre.oy])
    return (np.asarray(pontos, dtype=float) - desloca) / escala


# ---------------------------------------------------------------------------
# Alvos
# ---------------------------------------------------------------------------


def pontos_do_rotulo(marcas: Marcas) -> np.ndarray:
    """Os 4 pontos do alvo, no quadro original (como ``eixo_da_faixa`` os escolhe).

    Ordem: corda 1 perto do nut, corda 1 longe, corda 6 perto, corda 6 longe. "Perto"
    é a ponta de corda mais próxima do nut; "longe" é a mais distante, a mesma escolha
    de ``eixo_da_faixa``.

    Args:
        marcas: marcas do quadro, com o nut.

    Returns:
        Array ``(4, 2)``.

    Raises:
        ValueError: se o rótulo não tem o nut.
    """
    if marcas.nut is None:
        raise ValueError("o alvo do localizador precisa do nut")
    origem = np.asarray(marcas.nut, dtype=float)
    pontos: list[np.ndarray] = []
    for corda in (marcas.corda1, marcas.corda6):
        corda = np.asarray(corda, dtype=float)
        distancias = np.linalg.norm(corda - origem, axis=1)
        pontos.append(corda[int(np.argmin(distancias))])
        pontos.append(corda[int(np.argmax(distancias))])
    return np.array(pontos, dtype=float)


def transformar_pontos(pontos: np.ndarray, matriz: np.ndarray) -> np.ndarray:
    """Aplica uma afim 2 x 3 a pontos ``(n, 2)``, no mesmo sentido de ``warpAffine``.

    Args:
        pontos: array ``(n, 2)``.
        matriz: afim ``(2, 3)``.

    Returns:
        Array ``(n, 2)``.
    """
    return np.asarray(pontos, dtype=float) @ matriz[:, :2].T + matriz[:, 2]


def desenhar_alvo(pontos_canvas: np.ndarray) -> np.ndarray:
    """Alvo de 5 canais no canvas: gaussianas nos 4 pontos e a máscara do braço.

    A máscara é o quadrilátero corda 1 (perto e longe) mais corda 6 (longe e perto).

    Args:
        pontos_canvas: array ``(4, 2)`` no canvas, na ordem de ``pontos_do_rotulo``.

    Returns:
        Array float32 ``(5, 384, 640)`` com valores em [0, 1].
    """
    ys, xs = np.mgrid[0:ALTURA_CANVAS, 0:LARGURA_ENTRADA].astype(np.float32)
    alvo = np.zeros((CANAIS_LOCALIZADOR, ALTURA_CANVAS, LARGURA_ENTRADA), np.float32)
    dois_sigma = 2.0 * SIGMA_PONTO_PX**2
    for canal, (px, py) in enumerate(pontos_canvas):
        alvo[canal] = np.exp(-((xs - px) ** 2 + (ys - py) ** 2) / dois_sigma)
    quadrilatero = np.asarray(pontos_canvas, dtype=float)[list(ORDEM_QUADRILATERO)]
    mascara = np.zeros((ALTURA_CANVAS, LARGURA_ENTRADA), dtype=np.uint8)
    cv2.fillPoly(mascara, [np.round(quadrilatero * 16).astype(np.int32)], 1, shift=4)
    alvo[CANAL_PRESENCA] = mascara
    return alvo


# ---------------------------------------------------------------------------
# Aumentos
# ---------------------------------------------------------------------------


def matriz_aumento(rng: random.Random) -> np.ndarray:
    """Afim do aumento: escala, rotação em torno do centro e translação. Sem espelho.

    Args:
        rng: gerador do item (semente fixa).

    Returns:
        Afim ``(2, 3)`` float64, do canvas original para o aumentado.
    """
    escala = rng.uniform(*ESCALA_AUMENTO)
    angulo = rng.uniform(-ROTACAO_AUMENTO_GRAUS, ROTACAO_AUMENTO_GRAUS)
    tx = rng.uniform(-TRANSLACAO_AUMENTO, TRANSLACAO_AUMENTO) * LARGURA_ENTRADA
    ty = rng.uniform(-TRANSLACAO_AUMENTO, TRANSLACAO_AUMENTO) * ALTURA_CONTEUDO
    centro = (LARGURA_ENTRADA / 2.0, ALTURA_CONTEUDO / 2.0)
    matriz = cv2.getRotationMatrix2D(centro, angulo, escala)
    matriz[0, 2] += tx
    matriz[1, 2] += ty
    return matriz


def aplicar_cor(imagem: np.ndarray, rng: random.Random) -> np.ndarray:
    """Brilho, contraste e saturação de até 20 % (fatores em [0,8; 1,2]).

    Args:
        imagem: canvas BGR uint8.
        rng: gerador do item.

    Returns:
        Canvas BGR uint8.
    """
    img = imagem.astype(np.float32) / 255.0
    fator = {
        nome: rng.uniform(1.0 - COR_AUMENTO, 1.0 + COR_AUMENTO)
        for nome in ("contraste", "brilho", "saturacao")
    }
    media = float(img.mean())
    img = (img - media) * fator["contraste"] + media
    img = img * fator["brilho"]
    cinza = img.mean(axis=2, keepdims=True)
    img = cinza + (img - cinza) * fator["saturacao"]
    return np.clip(img * 255.0, 0.0, 255.0).round().astype(np.uint8)


# ---------------------------------------------------------------------------
# Dados e divisão
# ---------------------------------------------------------------------------


class _Quadros(Dataset):
    """Quadros inteiros de treino: cada item é ``(caminho, marcas, semente_aumento)``.

    A imagem é lida sob demanda, e o aumento depende só da semente do item, então o
    resultado não depende da ordem dos workers.
    """

    def __init__(self, itens: list[tuple[str, Marcas, int]]) -> None:
        """Guarda a lista de itens.

        Args:
            itens: tuplas ``(caminho, marcas, semente_aumento)``.
        """
        self.itens = itens

    def __len__(self) -> int:
        """Quantidade de itens.

        Returns:
            Número de itens.
        """
        return len(self.itens)

    def __getitem__(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        """Amostra ``i``: canvas RGB uint8 e alvo uint8 ``(5, 384, 640)``.

        Args:
            i: índice do item.

        Returns:
            ``(rgb, alvo)`` prontos para a rede, com o alvo quantizado em uint8.
        """
        caminho, marcas, semente = self.itens[i]
        canvas, enquadre = enquadrar(_imagem(Path(caminho)))
        pontos = para_canvas(pontos_do_rotulo(marcas), enquadre)
        rng = random.Random(semente)
        matriz = matriz_aumento(rng)
        canvas = cv2.warpAffine(
            canvas,
            matriz,
            (LARGURA_ENTRADA, ALTURA_CANVAS),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        pontos = transformar_pontos(pontos, matriz)
        canvas = aplicar_cor(canvas, rng)
        alvo = desenhar_alvo(pontos)
        rgb = np.ascontiguousarray(canvas[..., ::-1])
        return rgb, np.ascontiguousarray((alvo * 255.0).round().astype(np.uint8))


def _utilizavel(marcas: Marcas | None) -> bool:
    """Se o quadro tem braço, nut e eixo válido (sem isso não há alvo).

    Args:
        marcas: marcas do quadro, ou None.

    Returns:
        True quando ``eixo_da_faixa`` aceita as marcas.
    """
    if marcas is None or marcas.nut is None:
        return False
    try:
        eixo_da_faixa(marcas)
    except ValueError:
        return False
    return True


def _registros() -> list[dict]:
    """Todos os quadros com alvo: R (achou do rastreador) e G (gabarito do dono).

    Os G são lidos do quadro inteiro ``data/saida/maos/m3b/quadros/<id>.png``, que é a
    origem das faixas G (``data/saida/maos/m21/G``). O rótulo é o gabarito ``braco.json``.

    Returns:
        Dicionários com ``id``, ``origem`` (``R`` ou ``G``), ``canal``, ``caminho``
        (quadro inteiro) e ``marcas`` (rótulo no quadro).
    """
    registros: list[dict] = []
    for entrada in _pool_r():
        marcas = marcas_do_registro(entrada["registro"])
        if not _utilizavel(marcas):
            continue
        registros.append(
            {
                "id": Path(entrada["caminho"]).stem,
                "origem": "R",
                "canal": entrada["canal"],
                "caminho": entrada["caminho"],
                "marcas": marcas,
            }
        )
    gabarito = _gabarito()
    for entrada in _entradas_g(None):
        marcas = marcas_do_registro(gabarito[entrada["id"]])
        if not _utilizavel(marcas):
            continue
        registros.append(
            {
                "id": entrada["id"],
                "origem": "G",
                "canal": entrada["canal"],
                "caminho": str(MAOS_M3B / "quadros" / f"{entrada['id']}.png"),
                "marcas": marcas,
            }
        )
    return registros


def dividir_por_canal(
    registros: list[dict], fora: tuple[str, ...] = CANAIS_VALIDACAO
) -> tuple[list[dict], list[dict]]:
    """Separa treino e validação por canal: os canais de ``fora`` ficam só na validação.

    Args:
        registros: saída de ``_registros``.
        fora: canais de validação (R e G deles não entram no treino).

    Returns:
        ``(treino, validacao)``, sem canal em comum.
    """
    validacao = [r for r in registros if r["canal"] in fora]
    treino = [r for r in registros if r["canal"] not in fora]
    return treino, validacao


def _sequencia(
    registros: list[dict], passos: int, etiqueta: str
) -> list[tuple[str, Marcas, int]]:
    """Itens do treino: ``passos * LOTE`` sorteios uniformes com semente própria.

    Args:
        registros: quadros de treino.
        passos: número de passos.
        etiqueta: identifica o experimento, para a semente do sorteio.

    Returns:
        Tuplas ``(caminho, marcas, semente_aumento)`` para ``_Quadros``.
    """
    rng = random.Random(f"{SEMENTE_TEXTO}:seq:{etiqueta}")
    itens: list[tuple[str, Marcas, int]] = []
    for _ in range(passos * LOTE):
        registro = registros[rng.randrange(len(registros))]
        itens.append((registro["caminho"], registro["marcas"], rng.getrandbits(31)))
    return itens


# ---------------------------------------------------------------------------
# Rede e treino
# ---------------------------------------------------------------------------


def _treinar_localizador(
    itens: list[tuple[str, Marcas, int]], passos: int, semente: int
) -> tuple[nn.Module, list[float], float]:
    """Treina o localizador (U-Net da 1021, 5 saídas) por ``passos`` passos.

    AdamW com as taxas da 1021, cronograma de ``fator_lr``, BCE com peso positivo e AMP.

    Args:
        itens: sequência de ``_sequencia`` com ``passos * LOTE`` itens.
        passos: número de passos.
        semente: semente fixa do treino.

    Returns:
        ``(modelo, perdas, segundos)``.

    Raises:
        ValueError: se a sequência não tem ``passos * LOTE`` itens.
        RuntimeError: se uma perda não é finita.
    """
    if len(itens) != passos * LOTE:
        raise ValueError("a sequência precisa de passos * LOTE itens")
    fixar_semente(semente)
    dev = _dispositivo()
    modelo = UNetBraco(pesos_imagenet=True, canais=CANAIS_LOCALIZADOR).to(dev)
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
        """Fator do cronograma da 1021."""
        return fator_lr(passo, passos)

    cronograma = torch.optim.lr_scheduler.LambdaLR(otimizador, fator)
    criterio = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(PESO_POSITIVO, device=dev))
    escala = torch.amp.GradScaler("cuda")
    carga = DataLoader(
        _Quadros(itens),
        batch_size=LOTE,
        shuffle=False,
        num_workers=TRABALHADORES,
        drop_last=True,
        pin_memory=True,
        worker_init_fn=_iniciar_worker,
    )
    perdas: list[float] = []
    modelo.train()
    inicio = time.perf_counter()
    for imagem_u8, alvo_u8 in carga:
        x = _para_modelo(imagem_u8)
        y = alvo_u8.to(dev).float().div_(255.0)
        with torch.autocast("cuda", dtype=torch.float16):
            logits = modelo(x)
        perda = criterio(logits.float(), y)
        if not math.isfinite(float(perda.item())):
            raise RuntimeError(f"perda não finita no passo {len(perdas)}")
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
def prever_localizador(modelo: nn.Module, canvas: list[np.ndarray]) -> list[np.ndarray]:
    """Probabilidades dos 5 canais de cada canvas BGR uint8 ``(384, 640, 3)``.

    Args:
        modelo: localizador treinado.
        canvas: lista de canvas BGR uint8.

    Returns:
        Lista de arrays float32 ``(5, 384, 640)`` com valores em [0, 1].
    """
    modelo.eval()
    saidas: list[np.ndarray] = []
    for ini in range(0, len(canvas), 8):
        lote = np.stack([c[..., ::-1] for c in canvas[ini : ini + 8]])
        x = _para_modelo(torch.from_numpy(np.ascontiguousarray(lote)))
        with torch.autocast("cuda", dtype=torch.float16):
            logits = modelo(x)
        prob = torch.sigmoid(logits.float()).cpu().numpy()
        saidas.extend(list(prob))
    return saidas


def _carregar_localizador(nome: str) -> nn.Module:
    """Carrega o localizador ``nome`` (pesos e json em ``artefatos/m21``).

    Args:
        nome: ``L1_val_s1`` ou ``L1_todos_s<k>``.

    Returns:
        Rede em modo de avaliação, na GPU.

    Raises:
        ValueError: se o peso foi treinado com outro número de passos.
    """
    meta = _ler_json(DIR_PESOS / f"{nome}.json")
    if meta["passos"] != PASSOS:
        raise ValueError(f"{nome} foi treinado com {meta['passos']} passos")
    modelo = UNetBraco(pesos_imagenet=False, canais=CANAIS_LOCALIZADOR)
    modelo.load_state_dict(
        torch.load(DIR_PESOS / f"{nome}.pt", map_location=_dispositivo())
    )
    return modelo.to(_dispositivo()).eval()


# ---------------------------------------------------------------------------
# Decodificação do estágio 1
# ---------------------------------------------------------------------------


def _sem_braco_localizador(motivo: str, presenca: float) -> dict:
    """Resposta do estágio 1 quando o braço não aparece (sem alvo).

    Args:
        motivo: texto para o log.
        presenca: máximo do canal de presença.

    Returns:
        Dicionário com ``achou`` falso.
    """
    return {
        "achou": False,
        "motivo": motivo,
        "presenca": presenca,
        "pontos": None,
        "marcas": None,
    }


def _centroide(mapa: np.ndarray, y: int, x: int) -> tuple[float, float]:
    """Centróide 3 x 3 em torno do máximo ``(y, x)`` (pesos = probabilidades).

    Args:
        mapa: canal ``(altura, largura)``.
        y: linha do máximo.
        x: coluna do máximo.

    Returns:
        ``(x, y)`` em px no canvas, com precisão de subpixel.
    """
    altura, largura = mapa.shape
    y0, y1 = max(0, y - 1), min(altura, y + 2)
    x0, x1 = max(0, x - 1), min(largura, x + 2)
    janela = mapa[y0:y1, x0:x1].astype(np.float64)
    gy, gx = np.mgrid[y0:y1, x0:x1]
    soma = float(janela.sum())
    return float((janela * gx).sum() / soma), float((janela * gy).sum() / soma)


def decodificar_quadro(mapas: np.ndarray, enquadre: Enquadre) -> dict:
    """Pontos e presença do estágio 1, levados ao quadro original.

    Cada ponto é o argmax do seu canal refinado pelo centróide 3 x 3. Sem braço quando a
    presença máxima é menor que ``P_MIN`` ou quando algum ponto tem máximo menor que
    ``P_MIN``. O nut é a média das pontas perto do nut (pontos 0 e 2).

    Args:
        mapas: probabilidades ``(5, 384, 640)``.
        enquadre: transformação de ``enquadrar`` do quadro.

    Returns:
        Com braço: ``achou`` verdadeiro, ``pontos`` (4 x 2 no quadro), ``marcas`` (nut
        e as duas cordas, sem trastes) e ``presenca``. Sem braço: ``achou`` falso e
        ``motivo``.
    """
    presenca = float(mapas[CANAL_PRESENCA].max())
    if presenca < P_MIN:
        return _sem_braco_localizador(f"presença {presenca:.2f} < 0,3", presenca)
    pontos_canvas: list[tuple[float, float]] = []
    for canal in range(CANAL_PRESENCA):
        mapa = mapas[canal]
        y, x = np.unravel_index(int(np.argmax(mapa)), mapa.shape)
        if float(mapa[y, x]) < P_MIN:
            return _sem_braco_localizador(
                f"ponto {canal} com máximo {float(mapa[y, x]):.2f} < 0,3", presenca
            )
        pontos_canvas.append(_centroide(mapa, int(y), int(x)))
    pontos = do_canvas(np.array(pontos_canvas), enquadre)
    marcas = Marcas(
        nut=(pontos[0] + pontos[2]) / 2.0,
        trastes={},
        corda1=pontos[0:PONTOS_POR_CORDA],
        corda6=pontos[PONTOS_POR_CORDA : 2 * PONTOS_POR_CORDA],
    )
    return {
        "achou": True,
        "motivo": None,
        "presenca": presenca,
        "pontos": pontos,
        "marcas": marcas,
    }


# ---------------------------------------------------------------------------
# Cadeia completa
# ---------------------------------------------------------------------------


def _sem_braco_cadeia(motivo: str, passadas: int, presenca: float) -> dict:
    """Resposta da cadeia quando não há braço: sinais infinitos (sinalizado).

    Args:
        motivo: explicação para o log.
        passadas: passadas do estágio 2 feitas (0 se o estágio 1 já negou).
        presenca: presença do estágio 1.

    Returns:
        Dicionário no formato de ``cadeia``.
    """
    dec = {"achou": False, "motivo": motivo}
    return {
        "achou": False,
        "motivo": motivo,
        "passadas": passadas,
        "presenca": presenca,
        "dec": dec,
        "matriz": None,
        "S1": math.inf,
        "S2": math.inf,
        "S3": math.inf,
    }


def _extras(
    imagem: np.ndarray,
    marcas: Marcas,
    identificador: str,
    modelo_dois: nn.Module,
) -> list[Marcas | None]:
    """Marcas das ``N_EXTRAS`` perturbações do eixo final (S1 da 1023, semente da 1024).

    Args:
        imagem: quadro inteiro BGR.
        marcas: marcas finais (da segunda passada), no quadro.
        identificador: id do quadro (para a semente).
        modelo_dois: estágio 2 do canal.

    Returns:
        Uma entrada por extra: ``Marcas`` ou None (sem braço ou eixo inválido).
    """
    try:
        eixo = eixo_da_faixa(marcas)
    except ValueError:
        return [None] * N_EXTRAS
    matrizes = [
        matriz_da_faixa(
            perturbar(eixo, random.Random(f"{SEMENTE_EXTRAS_LOC}:{identificador}:{j}"))
        )
        for j in range(1, N_EXTRAS + 1)
    ]
    mapas = prever_mapas(modelo_dois, [recortar(imagem, m) for m in matrizes])
    extras: list[Marcas | None] = []
    for matriz, mapa in zip(matrizes, mapas, strict=True):
        dec, _ = decodificar_com_dados(mapa)
        extras.append(_no_quadro(dec, matriz) if dec["achou"] else None)
    return extras


def cadeia(
    modelo_loc: nn.Module,
    modelo_dois: nn.Module,
    imagem: np.ndarray,
    identificador: str,
) -> dict:
    """Cadeia completa de um quadro: estágio 1 -> faixa -> estágio 2 -> refino -> sinais.

    A primeira passada usa a faixa do estágio 1. Se o estágio 2 acha o braço, a faixa é
    recortada de novo a partir das marcas dele, e a resposta final é a da segunda passada
    (achou ou não). Os sinais S1, S2 e S3 são medidos na faixa final.

    Args:
        modelo_loc: estágio 1 (localizador).
        modelo_dois: estágio 2 (detector v2) do canal.
        imagem: quadro inteiro BGR uint8.
        identificador: id do quadro, para a semente das extras.

    Returns:
        ``achou``, ``motivo``, ``passadas``, ``presenca``, ``dec`` (saída do estágio 2
        final), ``matriz`` (faixa final), e os sinais ``S1``, ``S2``, ``S3``.
    """
    canvas, enquadre = enquadrar(imagem)
    loc = decodificar_quadro(prever_localizador(modelo_loc, [canvas])[0], enquadre)
    if not loc["achou"]:
        return _sem_braco_cadeia(loc["motivo"], 0, loc["presenca"])
    try:
        m1 = matriz_da_faixa(eixo_da_faixa(loc["marcas"]))
    except ValueError as erro:
        return _sem_braco_cadeia(f"eixo do estágio 1: {erro}", 0, loc["presenca"])
    mapa = prever_mapas(modelo_dois, [recortar(imagem, m1)])[0]
    dec, info = decodificar_com_dados(mapa)
    matriz, passadas = m1, 1
    if dec["achou"]:
        try:
            m2 = matriz_da_faixa(eixo_da_faixa(_no_quadro(dec, m1)))
        except ValueError as erro:
            return _sem_braco_cadeia(f"eixo do refino: {erro}", 1, loc["presenca"])
        mapa = prever_mapas(modelo_dois, [recortar(imagem, m2)])[0]
        dec, info = decodificar_com_dados(mapa)
        matriz, passadas = m2, 2
    resultado = {
        "achou": bool(dec["achou"]),
        "motivo": dec.get("motivo"),
        "passadas": passadas,
        "presenca": loc["presenca"],
        "dec": dec,
        "matriz": matriz,
        "S1": math.inf,
        "S2": sinal_s2(info),
        "S3": sinal_s3(mapa),
    }
    if resultado["achou"]:
        marcas = _no_quadro(dec, matriz)
        extras = _extras(imagem, marcas, identificador, modelo_dois)
        resultado["S1"] = sinal_s1(marcas, extras)
    return resultado


def sinalizado(resultado: dict) -> bool:
    """Se a regra congelada da 1023 manda o quadro para revisão.

    Args:
        resultado: saída de ``cadeia`` (``achou``, ``S1``, ``S2``, ``S3``).

    Returns:
        True quando o quadro é sinalizado (sem braço, ou algum sinal da regra acima do
        limiar congelado).
    """
    regra, limiares = _constantes_congeladas()
    quadro = {
        "achou": resultado["achou"],
        "S1": resultado["S1"],
        "S2": resultado["S2"],
        "S3": resultado["S3"],
    }
    return bool(marcar([quadro], regra, limiares)[0])


def _classe(resultado: dict, alvo: Marcas) -> str:
    """Classe da cadeia contra as marcas do dono (certo, impreciso, falso, nao_achou).

    Args:
        resultado: saída de ``cadeia``.
        alvo: marcas do dono no quadro.

    Returns:
        A classe de ``_medir``.
    """
    return _medir(resultado["dec"], resultado["matriz"], alvo)[0]


def _json(valor: float) -> float | None:
    """Número para JSON: infinito vira None.

    Args:
        valor: número.

    Returns:
        O número, ou None se não é finito.
    """
    return float(valor) if math.isfinite(valor) else None


# ---------------------------------------------------------------------------
# Erro do eixo (B1)
# ---------------------------------------------------------------------------


def erro_do_eixo(previsto: tuple, rotulo: tuple) -> dict:
    """Erro do eixo previsto contra o eixo do rótulo, nos mesmos termos da perturbação.

    A rotação é a que leva a direção do rótulo à prevista, em torno do centro do rótulo.
    Depois da rotação, o deslocamento da origem é medido em larguras (transversal) e em
    comprimentos (ao longo). A escala é o maior desvio relativo de comprimento e largura.

    Args:
        previsto: ``(origem, direcao, comprimento, largura)`` do estágio 1.
        rotulo: ``(origem, direcao, comprimento, largura)`` do rótulo.

    Returns:
        Dicionário com ``perpendicular``, ``ao_longo``, ``rotacao_graus`` e ``escala``.
    """
    origem, u, comprimento, largura = rotulo
    origem_p, u_p, comprimento_p, largura_p = previsto
    angulo = math.atan2(u[0] * u_p[1] - u[1] * u_p[0], float(np.dot(u, u_p)))
    rot = np.array(
        [[math.cos(angulo), -math.sin(angulo)], [math.sin(angulo), math.cos(angulo)]]
    )
    centro = origem + u * (comprimento / 2.0)
    origem_r = centro + rot @ (np.asarray(origem, dtype=float) - centro)
    u_r = rot @ u
    n_r = np.array([-u_r[1], u_r[0]])
    deslocamento = np.asarray(origem_p, dtype=float) - origem_r
    return {
        "perpendicular": float(deslocamento @ n_r) / largura,
        "ao_longo": float(deslocamento @ u_r) / comprimento,
        "rotacao_graus": math.degrees(angulo),
        "escala": max(
            abs(comprimento_p / comprimento - 1.0), abs(largura_p / largura - 1.0)
        ),
    }


def dentro_do_envelope(erro: dict | None) -> bool:
    """Se o erro cabe no envelope da 1021 (0,3; 0,05; 3 graus; 10 %).

    Args:
        erro: saída de ``erro_do_eixo``, ou None (sem braço).

    Returns:
        True quando os quatro critérios passam.
    """
    if erro is None:
        return False
    return (
        abs(erro["perpendicular"]) <= ENVELOPE_PERPENDICULAR
        and abs(erro["ao_longo"]) <= ENVELOPE_AO_LONGO
        and abs(erro["rotacao_graus"]) <= ENVELOPE_ROTACAO_GRAUS
        and erro["escala"] <= ENVELOPE_ESCALA
    )


def _resumo_grupo(grupo: list[dict]) -> dict:
    """Totais, fração dentro do envelope e medianas de um grupo de quadros.

    Args:
        grupo: linhas do B1 (``erro`` e ``dentro``).

    Returns:
        Dicionário com ``n``, ``sem_braco``, ``dentro``, ``fracao_dentro``,
        ``fracao_por_criterio`` e ``mediana_absoluta``.
    """
    n = len(grupo)
    com = [linha["erro"] for linha in grupo if linha["erro"] is not None]
    dentro = sum(linha["dentro"] for linha in grupo)
    criterios = {
        "perpendicular": sum(
            abs(e["perpendicular"]) <= ENVELOPE_PERPENDICULAR for e in com
        ),
        "ao_longo": sum(abs(e["ao_longo"]) <= ENVELOPE_AO_LONGO for e in com),
        "rotacao_graus": sum(
            abs(e["rotacao_graus"]) <= ENVELOPE_ROTACAO_GRAUS for e in com
        ),
        "escala": sum(e["escala"] <= ENVELOPE_ESCALA for e in com),
    }
    return {
        "n": n,
        "sem_braco": n - len(com),
        "dentro": dentro,
        "fracao_dentro": dentro / n if n else None,
        "fracao_por_criterio": {
            chave: (valor / n if n else None) for chave, valor in criterios.items()
        },
        "mediana_absoluta": {
            chave: (statistics.median(abs(e[chave]) for e in com) if com else None)
            for chave in CHAVES_ERRO
        },
    }


# ---------------------------------------------------------------------------
# Portões e prova
# ---------------------------------------------------------------------------


def _imprimir_b1(resumo: dict) -> None:
    """Tabela do B1 para o terminal (por canal, depois R e G, depois o geral).

    Args:
        resumo: saída de ``b1``.
    """
    linhas = [f"{'canal':<18} {'orig':<4} {'n':>3} {'dentro%':>8} {'sem':>4}"]
    for item in resumo["por_canal"]:
        g = item["resumo"]
        linhas.append(
            f"{item['canal']:<18} {item['origem']:<4} {g['n']:>3} "
            f"{100 * g['fracao_dentro']:>7.1f}% {g['sem_braco']:>4}"
        )
    for nome in ("R", "G", "geral"):
        g = resumo[nome]
        linhas.append(
            f"{nome:<18} {'':<4} {g['n']:>3} {100 * g['fracao_dentro']:>7.1f}% "
            f"{g['sem_braco']:>4}"
        )
    print("\n".join(linhas))


def b1(destino: Path = ARQUIVO_B1) -> int:
    """Portão B1: erro do eixo do estágio 1 (sem refino) nos R e G de validação.

    Usa o ``L1_val_s1``. Grava a tabela por canal, separando R de G, e o total.

    Args:
        destino: arquivo do resultado.

    Returns:
        0 ao terminar (a decisão é do dono, pelo campo ``passou``).
    """
    _, validacao = dividir_por_canal(_registros())
    linhas: list[dict] = []
    with _trava_gpu():
        modelo = _carregar_localizador(NOME_LOCALIZADOR_VALIDACAO)
        for ini in range(0, len(validacao), 8):
            lote = validacao[ini : ini + 8]
            canvas, enquadres = [], []
            for registro in lote:
                c, e = enquadrar(_imagem(Path(registro["caminho"])))
                canvas.append(c)
                enquadres.append(e)
            mapas = prever_localizador(modelo, canvas)
            for registro, mapa, enquadre in zip(lote, mapas, enquadres, strict=True):
                dec = decodificar_quadro(mapa, enquadre)
                erro = None
                if dec["achou"]:
                    try:
                        erro = erro_do_eixo(
                            eixo_da_faixa(dec["marcas"]),
                            eixo_da_faixa(registro["marcas"]),
                        )
                    except ValueError:
                        # Pontos previstos degenerados: sem eixo, fora do envelope.
                        erro = None
                linhas.append(
                    {
                        "id": registro["id"],
                        "origem": registro["origem"],
                        "canal": registro["canal"],
                        "presenca": dec["presenca"],
                        "achou": dec["achou"],
                        "erro": erro,
                        "dentro": dentro_do_envelope(erro),
                    }
                )
        del modelo
        torch.cuda.empty_cache()
    por_canal = []
    for canal in CANAIS_VALIDACAO:
        for origem in ("R", "G"):
            grupo = [
                linha
                for linha in linhas
                if linha["canal"] == canal and linha["origem"] == origem
            ]
            por_canal.append(
                {"canal": canal, "origem": origem, "resumo": _resumo_grupo(grupo)}
            )
    resumo = {
        "R": _resumo_grupo([x for x in linhas if x["origem"] == "R"]),
        "G": _resumo_grupo([x for x in linhas if x["origem"] == "G"]),
        "geral": _resumo_grupo(linhas),
    }
    passou = resumo["geral"]["fracao_dentro"] >= LIMITE_B1
    dados = {
        "portao": "B1_ENVELOPE",
        "pesos": NOME_LOCALIZADOR_VALIDACAO,
        "canais_validacao": list(CANAIS_VALIDACAO),
        "envelope": {
            "perpendicular_larguras": ENVELOPE_PERPENDICULAR,
            "ao_longo_comprimentos": ENVELOPE_AO_LONGO,
            "rotacao_graus": ENVELOPE_ROTACAO_GRAUS,
            "escala": ENVELOPE_ESCALA,
        },
        "limite_passou": LIMITE_B1,
        "passou": passou,
        "por_canal": por_canal,
        "R": resumo["R"],
        "G": resumo["G"],
        "geral": resumo["geral"],
        "quadros": linhas,
    }
    _gravar_json(destino, dados)
    _imprimir_b1({**resumo, "por_canal": por_canal})
    print(f"passou no B1: {passou} ({100 * resumo['geral']['fracao_dentro']:.1f} %)")
    return 0


def b2(destino: Path = ARQUIVO_B2) -> int:
    """Portão B2 (registro): cadeia completa nos G de validação, contra o gabarito.

    O estágio 2 é o da dobra que não viu o canal (``A3_100_<k>_s1``). Só registra.

    Args:
        destino: arquivo do resultado.

    Returns:
        0 ao terminar.
    """
    gabarito = _gabarito()
    indice = {canal: k for k, canal in enumerate(canais_g())}
    entradas = [e for e in _entradas_g(None) if e["canal"] in CANAIS_VALIDACAO]
    quadros: list[dict] = []
    estagio2_por_canal: dict[str, str] = {}
    with _trava_gpu():
        loc = _carregar_localizador(NOME_LOCALIZADOR_VALIDACAO)
        dois: dict[str, nn.Module] = {}
        for entrada in entradas:
            canal = entrada["canal"]
            if canal not in dois:
                nome = _nome_unidade("A3", "100", indice[canal], 1)
                passos = _ler_json(DIR_PESOS / f"{nome}.json")["passos"]
                dois[canal], _ = _carregar_pesos(nome, passos)
                estagio2_por_canal[canal] = nome
            alvo = marcas_do_registro(gabarito[entrada["id"]])
            imagem = _imagem(MAOS_M3B / "quadros" / f"{entrada['id']}.png")
            resultado = cadeia(loc, dois[canal], imagem, entrada["id"])
            quadros.append(
                {
                    "id": entrada["id"],
                    "canal": canal,
                    "estagio2": estagio2_por_canal[canal],
                    "achou": resultado["achou"],
                    "passadas": resultado["passadas"],
                    "presenca": resultado["presenca"],
                    "motivo": resultado["motivo"],
                    "classe": _classe(resultado, alvo),
                    "sinalizado": sinalizado(resultado),
                    "S1": _json(resultado["S1"]),
                    "S2": _json(resultado["S2"]),
                    "S3": _json(resultado["S3"]),
                }
            )
    contagem = {
        classe: sum(q["classe"] == classe for q in quadros)
        for classe in ("certo", "impreciso", "falso", "nao_achou", "erro")
    }
    falsos_nao = [
        q["id"] for q in quadros if q["classe"] == "falso" and not q["sinalizado"]
    ]
    dados = {
        "portao": "B2_CADEIA_REGISTRO",
        "pesos_estagio1": NOME_LOCALIZADOR_VALIDACAO,
        "estagio2": estagio2_por_canal,
        "regra": "+".join(_constantes_congeladas()[0]),
        "limiares": _constantes_congeladas()[1],
        "medidas": len(quadros),
        "contagem": contagem,
        "sinalizados": sum(q["sinalizado"] for q in quadros),
        "falsos_nao_sinalizados": falsos_nao,
        "quadros": quadros,
    }
    _gravar_json(destino, dados)
    print(
        f"B2: {len(quadros)} medidas; {contagem}; sinalizados "
        f"{dados['sinalizados']}; falsos não sinalizados {falsos_nao}"
    )
    return 0


def _entradas_prova() -> list[tuple[str, str, Marcas | None, str]]:
    """Quadros da prova M11b: os 28 do detector mais o q77 (braço "não").

    Lê o gabarito e o índice da M11b: só deve ser chamada na prova lacrada.

    Returns:
        Tuplas ``(id, canal, marcas_ou_None, braco)``.

    Raises:
        ValueError: se um quadro com braço "sim" não tem marcas completas.
    """
    gabarito = _ler_json(GABARITO_BRACO_M11B)["quadros"]
    ids = (*QUADROS_PROVA, QUADRO_BRACO_NAO)
    canais = _canal_por_quadro(set(ids))
    entradas = []
    for id_quadro in ids:
        registro = gabarito[id_quadro]
        braco = str(registro.get("braco"))
        marcas = marcas_do_registro(registro)
        if braco == "sim" and marcas is None:
            raise ValueError(f"{id_quadro} sem marcas completas")
        entradas.append((id_quadro, canais[id_quadro], marcas, braco))
    return entradas


def prova(destino: Path = ARQUIVO_PROVA) -> int:
    """Prova M11b: 29 quadros x 3 sementes com o treino final (não rodar nesta fase).

    Pesos ``L1_todos_s<k>`` com ``A3_100_todos_s<k>``. Para o q77 (braço "não"), achado
    e não sinalizado é falso. Critério: falsos não sinalizados até 5 % das medidas (87),
    e sinalizados (incluindo "não achou") até 50 % das medidas com braço (84).

    Args:
        destino: arquivo do resultado.

    Returns:
        0 ao terminar.
    """
    entradas = _entradas_prova()
    por_semente: dict[int, list[dict]] = {}
    with _trava_gpu():
        for semente in SEMENTES_FINAIS:
            loc = _carregar_localizador(f"L1_todos_s{semente}")
            dois, _ = _carregar_pesos(f"A3_100_todos_s{semente}", PASSOS)
            linhas: list[dict] = []
            for id_quadro, canal, marcas, braco in entradas:
                imagem = _imagem(MAOS_M11B / "quadros" / f"{id_quadro}.png")
                resultado = cadeia(loc, dois, imagem, id_quadro)
                if marcas is not None:
                    classe = _classe(resultado, marcas)
                else:
                    classe = classificar({}, resultado["achou"], "nao")
                linhas.append(
                    {
                        "id": id_quadro,
                        "canal": canal,
                        "braco": braco,
                        "achou": resultado["achou"],
                        "classe": classe,
                        "sinalizado": sinalizado(resultado),
                        "S1": _json(resultado["S1"]),
                        "S2": _json(resultado["S2"]),
                        "S3": _json(resultado["S3"]),
                    }
                )
            por_semente[semente] = linhas
    medidas = [linha for linhas in por_semente.values() for linha in linhas]
    com_braco = [linha for linha in medidas if linha["braco"] != "nao"]
    falsos_nao = sum(
        linha["classe"] == "falso" and not linha["sinalizado"] for linha in medidas
    )
    sinalizados = sum(linha["sinalizado"] for linha in com_braco)
    seguranca = falsos_nao / len(medidas) <= LIMITE_FALSOS_PROVA
    utilidade = sinalizados / len(com_braco) <= LIMITE_SINALIZADOS_PROVA
    dados = {
        "portao": "PROVA_LOCALIZADOR_M11B",
        "medidas": len(medidas),
        "medidas_com_braco": len(com_braco),
        "falsos_nao_sinalizados": falsos_nao,
        "sinalizados_com_braco": sinalizados,
        "seguranca": seguranca,
        "utilidade": utilidade,
        "quadros_por_semente": por_semente,
    }
    _gravar_json(destino, dados)
    print(
        f"prova: {len(medidas)} medidas; falsos não sinalizados {falsos_nao} "
        f"(limite {LIMITE_FALSOS_PROVA:.0%}); sinalizados {sinalizados}/{len(com_braco)}"
        f" (limite {LIMITE_SINALIZADOS_PROVA:.0%}); segurança {seguranca}, "
        f"utilidade {utilidade}"
    )
    return 0


# ---------------------------------------------------------------------------
# Treino (CLI), smoke e folha de alvos
# ---------------------------------------------------------------------------


def treinar(validacao: bool, semente: int, passos: int = PASSOS) -> int:
    """Treina o localizador: validação (sem os canais de validação) ou final (tudo).

    Grava ``artefatos/m21/<nome>.pt`` com o json de comando, semente, passos e perdas.

    Args:
        validacao: True para ``L1_val_s<semente>`` (fora os canais de validação).
        semente: semente do treino.
        passos: passos (``PASSOS`` no treino oficial).

    Returns:
        0 ao terminar.
    """
    registros = _registros()
    if validacao:
        treino, _ = dividir_por_canal(registros)
        nome = f"L1_val_s{semente}"
        fora = list(CANAIS_VALIDACAO)
    else:
        treino = registros
        nome = f"L1_todos_s{semente}"
        fora = []
    itens = _sequencia(treino, passos, nome)
    with _trava_gpu():
        modelo, perdas, segundos = _treinar_localizador(itens, passos, semente)
        _salvar_pesos(
            modelo,
            nome,
            {
                "nome": nome,
                "comando": (
                    "python -m tab.maos_braco_localizador treinar "
                    f"{'--validacao' if validacao else '--final'} --semente {semente}"
                ),
                "semente": semente,
                "passos": passos,
                "canais_fora": fora,
                "quadros_de_treino": len(treino),
                "tempo_treino_s": segundos,
                "perdas": perdas,
            },
        )
    print(f"{nome}: {passos} passos, perda final {perdas[-1]:.4f}, {segundos:.0f} s")
    return 0


def conferir_frames_g() -> None:
    """Confere que o quadro inteiro do G (m3b) é o que originou a faixa G (m21).

    Recorta o quadro inteiro com a matriz do json G e compara com o png G.
    """
    diferencas = []
    for entrada in _entradas_g(None):
        quadro = _imagem(MAOS_M3B / "quadros" / f"{entrada['id']}.png")
        faixa = recortar(quadro, np.asarray(entrada["matriz"], dtype=float))
        referencia = _imagem(DIR_G / f"{entrada['id']}.png")
        diferencas.append(float(np.abs(faixa.astype(float) - referencia).mean()))
    print(
        f"G: {len(diferencas)} quadros; diferença média por quadro: "
        f"mediana {statistics.median(diferencas):.2f}, máxima {max(diferencas):.2f}"
    )


def folha_alvos(destino: Path = ARQUIVO_FOLHA) -> None:
    """Folha de conferência: 12 quadros de treino com os 4 pontos e a máscara.

    Os quadros saem do próprio ``_Quadros`` (com aumento), para conferir o alvo que a rede
    recebe. Cada ponto é o pico do seu canal; a máscara aparece em verde.

    Args:
        destino: arquivo JPEG da folha.
    """
    treino, _ = dividir_por_canal(_registros())
    sorteio = random.Random(f"{SEMENTE_TEXTO}:folha").sample(range(len(treino)), 12)
    dados = _Quadros([(treino[i]["caminho"], treino[i]["marcas"], i) for i in sorteio])
    quadros = []
    for i, indice in enumerate(sorteio):
        rgb, alvo = dados[i]
        bgr = np.ascontiguousarray(rgb[..., ::-1])
        mascara = alvo[CANAL_PRESENCA] > 127
        bgr[mascara] = (0.6 * bgr[mascara] + 0.4 * np.array([0, 255, 0])).astype(
            np.uint8
        )
        for canal in range(CANAL_PRESENCA):
            y, x = np.unravel_index(int(np.argmax(alvo[canal])), alvo[canal].shape)
            cv2.circle(bgr, (int(x), int(y)), 6, CORES_PONTOS[canal], -1)
        cv2.putText(
            bgr,
            f"{treino[indice]['id']} {treino[indice]['canal'][:18]}",
            (8, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
        quadros.append(bgr)
    linhas = [np.hstack(quadros[k : k + 3]) for k in range(0, 12, 3)]
    folha = np.vstack(linhas)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), folha, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"folha gravada em {destino}")


def smoke(passos: int = 50) -> int:
    """Teste de ponta a ponta: 50 passos de treino (sem gravar pesos), e a folha.

    Args:
        passos: passos do teste.

    Returns:
        0 ao terminar.
    """
    conferir_frames_g()
    treino, _ = dividir_por_canal(_registros())
    itens = _sequencia(treino, passos, "smoke")
    with _trava_gpu():
        _, perdas, segundos = _treinar_localizador(itens, passos, 1)
    print(
        f"smoke: {passos} passos, perda {perdas[0]:.4f} -> {perdas[-1]:.4f}, "
        f"{segundos:.1f} s"
    )
    folha_alvos()
    return 0


def _parser() -> argparse.ArgumentParser:
    """Parser da CLI.

    Returns:
        Parser com os subcomandos do localizador.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    treino = sub.add_parser("treinar", help="treino do estágio 1")
    modo = treino.add_mutually_exclusive_group(required=True)
    modo.add_argument("--validacao", action="store_true")
    modo.add_argument("--final", action="store_true")
    treino.add_argument("--semente", type=int, required=True)
    sub.add_parser("smoke", help="teste de 50 passos e folha de alvos")
    sub.add_parser("b1", help="portão B1: envelope do estágio 1")
    sub.add_parser("b2", help="portão B2: cadeia completa nos G de validação")
    sub.add_parser("prova", help="prova M11b (não rodar nesta fase)")
    return parser


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída do subcomando.
    """
    args = _parser().parse_args()
    if args.comando == "treinar":
        return treinar(validacao=args.validacao, semente=args.semente)
    if args.comando == "smoke":
        return smoke()
    if args.comando == "b1":
        return b1()
    if args.comando == "b2":
        return b2()
    return prova()


if __name__ == "__main__":
    sys.exit(main())
