"""Rodada 1045: uma rede que acha o capo na faixa do braço, e o nut pela conta da 1046.

A rede é a U-Net do estágio 2 com 1 canal de saída: na faixa retificada (1024 × 192), uma
crista no segmento entre as cordas 1 e 6 na posição do capo (o ponto ``k`` do dono). Quadro
sem capo: mapa vazio.

- No treino, a faixa sai das marcas do dono com o começo nas pontas das cordas do lado da
  cabeça (com capo, o dono marca as cordas até o nut verdadeiro), com o erro de eixo
  sorteado e os aumentos do estágio 2.
- Na previsão, a faixa sai das marcas previstas pelo par antigo. O capo é visto quando o
  pico do perfil (média do mapa entre as cordas, por coluna) passa do limiar.

Pré-registro: ``docs/rodadas/1045-rede-de-capo.md``.

CLI (``python -m tab.maos.braco.capo_rede``): ``contar``, ``treinar --semente N`` (GPU),
``picos`` (GPU: os picos nos quadros da escolha e da prova), ``escolher`` e ``medir``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from tab.comum.arquivos import gravar_atomico
from tab.comum.caminhos import (
    GABARITO_BRACO,
    GABARITO_BRACO_M11B,
    GABARITO_BRACO_M25_PROVA,
    GABARITO_BRACO_M25_TREINO,
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    GABARITO_BRACO_M29,
    GABARITO_BRACO_M32,
    GABARITO_BRACO_M36,
    GABARITO_BRACO_M39,
    GABARITO_BRACO_M43,
    GABARITO_BRACO_M44,
    GABARITO_BRACO_M47,
    MAOS_M3B,
    MAOS_M11B,
    MAOS_M25,
    MAOS_M26,
    MAOS_M27,
    MAOS_M29,
    MAOS_M32,
    MAOS_M36,
    MAOS_M39,
    MAOS_M43,
    MAOS_M44,
    MAOS_M45,
    MAOS_M47,
    SAIDA,
)
from tab.comum.gpu import trava_gpu
from tab.comum.semente import fixar_semente
from tab.maos.braco.capo_aberto import nut_pela_conta
from tab.maos.braco.ciclo import marcas_do_previsto
from tab.maos.braco.detector import (
    DESVIO_IMAGENET,
    DIR_PESOS,
    LOTE,
    LR_CODIFICADOR,
    LR_DECODIFICADOR,
    MEDIA_IMAGENET,
    PESO_POSITIVO,
    UNetBraco,
    aumentar,
    fator_lr,
)
from tab.maos.braco.faixa import (
    ALTURA_FAIXA,
    LARGURA_FAIXA,
    aplicar_matriz,
    eixo_da_faixa,
    matriz_da_faixa,
    perturbar,
    recortar,
    voltar,
)
from tab.maos.braco.retreino import EXCLUIDOS, medir_por_grupo, tem_capo
from tab.maos.braco.tempo import Marcas, marcas_do_registro
from tab.maos.braco.validadores import (
    PASTA_HIPOTESES,
    REFERENCIA,
    cadeia,
    ler_faixas,
    nome_da_hipotese,
    validar,
)

#: Fontes: (origem, gabarito, pasta com ``indice.json``) e o papel de cada uma.
TREINO = (
    ("M3b", GABARITO_BRACO, MAOS_M3B),
    ("M11b", GABARITO_BRACO_M11B, MAOS_M11B),
    ("C", GABARITO_BRACO_M25_TREINO, MAOS_M25 / "treino"),
    ("N", GABARITO_BRACO_M25_PROVA, MAOS_M25 / "prova"),
    ("M26", GABARITO_BRACO_M26, MAOS_M26),
    ("M27", GABARITO_BRACO_M27, MAOS_M27),
    ("M32", GABARITO_BRACO_M32, MAOS_M32),
    ("M36", GABARITO_BRACO_M36, MAOS_M36),
)
ESCOLHA = (
    ("M39", GABARITO_BRACO_M39, MAOS_M39),
    ("M29", GABARITO_BRACO_M29, MAOS_M29),
    ("M44", GABARITO_BRACO_M44, MAOS_M44),
)
PROVA = (
    ("M43", GABARITO_BRACO_M43, MAOS_M43),
    ("M47", GABARITO_BRACO_M47, MAOS_M47),
)
#: Rodada do ciclo de cada fonte da escolha e da prova (onde estão as previsões do par
#: antigo: ``m46/<rodada>/antigo.json`` ou as hipóteses da 1044).
RODADA_DA_FONTE = {
    "M39": "1039",
    "M29": "1029",
    "M44": "1044",
    "M43": "1043",
    "M47": "1047",
}
SEMENTES = (1, 2, 3)
PREFIXO = "C1_capo_s"
PASSOS = 1500
#: Sigma da crista do capo, em px da faixa (o capo é mais largo que um traste).
SIGMA_CAPO_PX = 4.0
#: Itens com capo por lote (o resto é sem capo).
COM_CAPO_POR_LOTE = 8
#: Capo achado: a ≤ esta fração de casa do ``k`` do dono, ao longo do braço.
TOLERANCIA_ACHADO = 0.5
#: Capo falso permitido entre os sem capo da escolha.
FALSOS_PERMITIDOS = 1
#: Fração mínima de achados na M39 para seguir à prova.
FRACAO_ACHADO_MIN = 0.70
#: Faixa acima do limiar em que o capo é duvidoso (sinaliza).
FAIXA_DUVIDA = 0.10
PROCESSOS_DADOS = 6
SEMENTE_SEQUENCIA = "20261045:seq"

ARQUIVO_CONTAGEM = MAOS_M45 / "contagem.json"
ARQUIVO_PICOS = MAOS_M45 / "picos.json"
ARQUIVO_ESCOLHA = MAOS_M45 / "escolha.json"
ARQUIVO_MEDIDA = MAOS_M45 / "medida.json"


def _ler_json(caminho: Path) -> dict:
    """Lê um JSON em UTF-8.

    Args:
        caminho: arquivo.

    Returns:
        O conteúdo.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def _indice(pasta: Path) -> dict[str, dict]:
    """O ``indice.json`` de uma pasta, por id.

    Args:
        pasta: pasta com ``indice.json``.

    Returns:
        ``{id: item}``.
    """
    return {q["id"]: q for q in _ler_json(pasta / "indice.json")["quadros"]}


def registros(fontes: tuple, excluir_videos: set[str] = frozenset()) -> list[dict]:
    """Os quadros com braço ``sim`` e marcas completas de um conjunto de fontes.

    Args:
        fontes: tuplas ``(origem, gabarito, pasta)``.
        excluir_videos: vídeos que não podem entrar (os da escolha e da prova).

    Returns:
        ``[{"id", "origem", "arquivo", "canal", "caminho", "marcas", "capo"}]``, com
        ``capo`` o ponto ``k`` do dono ou None.
    """
    saida = []
    for origem, gabarito, pasta in fontes:
        indice = _indice(pasta)
        fora = EXCLUIDOS.get(origem, {})
        for id_q, registro in _ler_json(gabarito)["quadros"].items():
            if id_q in fora or id_q not in indice:
                continue
            marcas = marcas_do_registro(registro)
            if registro.get("braco") != "sim" or marcas is None:
                continue
            item = indice[id_q]
            if item["arquivo"] in excluir_videos:
                continue
            saida.append(
                {
                    "id": f"{origem}-{id_q}",
                    "origem": origem,
                    "chave": id_q,
                    "arquivo": item["arquivo"],
                    "canal": item.get("canal") or item["arquivo"].split("/")[0],
                    "caminho": str(pasta / item["png"]),
                    "marcas": marcas,
                    "capo": registro["capo"] if tem_capo(registro) else None,
                }
            )
    return saida


def _videos(fontes: tuple) -> set[str]:
    """Os vídeos de um conjunto de fontes.

    Args:
        fontes: tuplas ``(origem, gabarito, pasta)``.

    Returns:
        Os caminhos relativos ao acervo.
    """
    return {
        item["arquivo"] for _, _, pasta in fontes for item in _indice(pasta).values()
    }


def treino() -> list[dict]:
    """Os quadros de treino, sem nenhum vídeo da escolha ou da prova.

    Returns:
        Os registros de treino.
    """
    return registros(TREINO, _videos(ESCOLHA) | _videos(PROVA))


def marcas_da_cabeca(marcas: Marcas) -> Marcas:
    """As marcas com o nut nas pontas das cordas do lado da cabeça.

    Com capo, o dono põe o nut no traste à frente do capo e as cordas vão até o nut
    verdadeiro; a faixa precisa começar ali para o capo ficar dentro dela.

    Args:
        marcas: marcas do dono.

    Returns:
        Uma cópia com ``nut`` no meio das pontas das cordas mais perto do nut marcado (ou
        do primeiro traste, se o nut está fora).
    """
    referencia = (
        marcas.nut if marcas.nut is not None else marcas.trastes[min(marcas.trastes)]
    )
    referencia = np.asarray(referencia, dtype=float)
    pontas = []
    for corda in (marcas.corda1, marcas.corda6):
        pontos = np.asarray(corda, dtype=float)
        pontas.append(
            pontos[int(np.argmin(np.linalg.norm(pontos - referencia, axis=1)))]
        )
    return dataclasses.replace(marcas, nut=(pontas[0] + pontas[1]) / 2.0)


def _ponto_na_reta(reta: list, x: float) -> np.ndarray:
    """O ponto da reta (dois pontos) com a abscissa x.

    Args:
        reta: ``[[x0, y0], [x1, y1]]``.
        x: abscissa.

    Returns:
        ``(x, y)``.
    """
    (x0, y0), (x1, y1) = reta
    if abs(x1 - x0) < 1e-9:
        return np.array([x, (y0 + y1) / 2.0])
    return np.array([x, y0 + (y1 - y0) * (x - x0) / (x1 - x0)])


def alvo_do_capo(cordas: tuple[list, list], x_capo: float | None) -> np.ndarray:
    """O mapa alvo de 1 canal: a crista do capo entre as cordas, ou vazio.

    Args:
        cordas: as cordas 1 e 6 na faixa (dois pontos cada).
        x_capo: a posição do capo na faixa, ou None sem capo.

    Returns:
        Array float32 ``(1, 192, 1024)``.
    """
    alvo = np.zeros((1, ALTURA_FAIXA, LARGURA_FAIXA), dtype=np.float32)
    if x_capo is None:
        return alvo
    a = _ponto_na_reta(cordas[0], x_capo)
    b = _ponto_na_reta(cordas[1], x_capo)
    ys, xs = np.mgrid[0:ALTURA_FAIXA, 0:LARGURA_FAIXA].astype(np.float64)
    d = b - a
    t = np.clip(
        ((xs - a[0]) * d[0] + (ys - a[1]) * d[1]) / max(float(d @ d), 1e-9), 0, 1
    )
    dist = np.hypot(a[0] + t * d[0] - xs, a[1] + t * d[1] - ys)
    alvo[0] = np.exp(-(dist**2) / (2.0 * SIGMA_CAPO_PX**2))
    return alvo


def faixa_e_alvo(
    imagem: np.ndarray, marcas: Marcas, capo: list | None, rng: random.Random | None
) -> tuple[np.ndarray, np.ndarray]:
    """A faixa de um quadro e o alvo do capo nela.

    Args:
        imagem: quadro BGR.
        marcas: marcas do dono.
        capo: o ponto ``k`` do dono, ou None.
        rng: sorteio do erro de eixo (None: sem erro).

    Returns:
        ``(faixa BGR uint8, alvo (1, 192, 1024))``.
    """
    marcas_faixa = marcas_da_cabeca(marcas)
    eixo = eixo_da_faixa(marcas_faixa)
    if rng is not None:
        eixo = perturbar(eixo, rng)
    matriz = matriz_da_faixa(eixo)
    faixa = recortar(imagem, matriz)
    cordas = (
        aplicar_matriz(matriz, marcas.corda1).tolist(),
        aplicar_matriz(matriz, marcas.corda6).tolist(),
    )
    x_capo = None if capo is None else float(aplicar_matriz(matriz, capo)[0])
    if x_capo is not None and not 0 <= x_capo < LARGURA_FAIXA:
        x_capo = None
    return faixa, alvo_do_capo(cordas, x_capo)


class ItensCapo(Dataset):
    """Amostras de treino da rede de capo: ``(caminho, marcas, capo, semente)``."""

    def __init__(self, itens: list[tuple]) -> None:
        """Guarda a lista de itens.

        Args:
            itens: tuplas ``(caminho, marcas, capo, semente)``.
        """
        self.itens = itens

    def __len__(self) -> int:
        """Quantidade de amostras.

        Returns:
            Número de itens.
        """
        return len(self.itens)

    def __getitem__(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        """Amostra ``i``: faixa RGB uint8 e alvo uint8.

        Args:
            i: índice do item.

        Returns:
            ``(faixa (192, 1024, 3), alvo (1, 192, 1024))``.
        """
        caminho, marcas, capo, semente = self.itens[i]
        rng = random.Random(semente)
        imagem = cv2.imread(caminho)
        faixa, alvo = faixa_e_alvo(imagem, marcas, capo, rng)
        faixa_f, alvo = aumentar(faixa, alvo, rng)
        rgb = np.ascontiguousarray(
            (faixa_f[..., ::-1] * 255.0).round().astype(np.uint8)
        )
        return rgb, np.ascontiguousarray((alvo * 255.0).round().astype(np.uint8))


def sequencia(regs: list[dict], passos: int, semente: int) -> list[tuple]:
    """A sequência do treino: em cada lote, ``COM_CAPO_POR_LOTE`` com capo e o resto sem.

    Args:
        regs: registros de treino.
        passos: número de passos.
        semente: semente do treino.

    Returns:
        ``passos * LOTE`` itens para ``ItensCapo``.

    Raises:
        ValueError: sem quadros com capo ou sem quadros sem capo.
    """
    com = [r for r in regs if r["capo"] is not None]
    sem = [r for r in regs if r["capo"] is None]
    if not com or not sem:
        raise ValueError("o treino precisa de quadros com e sem capo")
    rng = random.Random(f"{SEMENTE_SEQUENCIA}:{semente}")
    itens = []
    for _ in range(passos):
        for j in range(LOTE):
            r = (com if j < COM_CAPO_POR_LOTE else sem)[
                rng.randrange(len(com) if j < COM_CAPO_POR_LOTE else len(sem))
            ]
            itens.append((r["caminho"], r["marcas"], r["capo"], rng.getrandbits(31)))
    return itens


def _dispositivo() -> torch.device:
    """O dispositivo do treino.

    Returns:
        CUDA se houver, senão CPU.
    """
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def para_modelo(rgb_u8: torch.Tensor) -> torch.Tensor:
    """Normaliza um lote RGB uint8 ``(N, H, W, 3)`` como o ImageNet.

    Args:
        rgb_u8: lote uint8, canais por último.

    Returns:
        Tensor ``(N, 3, H, W)`` no dispositivo.
    """
    dev = _dispositivo()
    x = rgb_u8.to(dev).permute(0, 3, 1, 2).float().div_(255.0)
    media = torch.tensor(MEDIA_IMAGENET, device=dev).view(1, 3, 1, 1)
    desvio = torch.tensor(DESVIO_IMAGENET, device=dev).view(1, 3, 1, 1)
    return (x - media) / desvio


def _iniciar_worker(_: int) -> None:
    """OpenCV e torch numa thread só por worker.

    Args:
        _: índice do worker.
    """
    cv2.setNumThreads(0)
    torch.set_num_threads(1)


def treinar(semente: int, passos: int = PASSOS, gravar: bool = True) -> dict:
    """Treina a rede de capo de uma semente e grava o peso com a procedência.

    Args:
        semente: semente do treino.
        passos: passos.
        gravar: se grava ``artefatos/m21/C1_capo_s<semente>.pt`` e o json.

    Returns:
        O resumo (nome, quadros, perda final, segundos).
    """
    regs = treino()
    itens = sequencia(regs, passos, semente)
    nome = f"{PREFIXO}{semente}"
    with trava_gpu("maos", "~30 min"):
        fixar_semente(semente)
        dev = _dispositivo()
        modelo = UNetBraco(canais=1).to(dev)
        otimizador = torch.optim.AdamW(
            [
                {
                    "params": [p for m in modelo.codificador() for p in m.parameters()],
                    "lr": LR_CODIFICADOR,
                },
                {
                    "params": [
                        p for m in modelo.decodificador() for p in m.parameters()
                    ],
                    "lr": LR_DECODIFICADOR,
                },
            ]
        )
        cronograma = torch.optim.lr_scheduler.LambdaLR(
            otimizador, lambda passo: fator_lr(passo, passos)
        )
        criterio = nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor(PESO_POSITIVO, device=dev)
        )
        escala = torch.amp.GradScaler("cuda")
        carga = DataLoader(
            ItensCapo(itens),
            batch_size=LOTE,
            shuffle=False,
            num_workers=PROCESSOS_DADOS,
            drop_last=True,
            pin_memory=True,
            worker_init_fn=_iniciar_worker,
        )
        perdas = []
        modelo.train()
        inicio = time.perf_counter()
        for faixa_u8, alvo_u8 in carga:
            x = para_modelo(faixa_u8)
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
    resumo = {
        "nome": nome,
        "rodada": "1045",
        "comando": f"python -m tab.maos.braco.capo_rede treinar --semente {semente}",
        "semente": semente,
        "passos": passos,
        "quadros": {
            "com_capo": sum(1 for r in regs if r["capo"] is not None),
            "sem_capo": sum(1 for r in regs if r["capo"] is None),
        },
        "perda_final": perdas[-1],
        "perdas_a_cada_100": perdas[::100],
        "segundos": segundos,
    }
    if gravar:
        DIR_PESOS.mkdir(parents=True, exist_ok=True)
        torch.save(modelo.state_dict(), DIR_PESOS / f"{nome}.pt")
        gravar_atomico(DIR_PESOS / f"{nome}.json", resumo)
    return resumo


def carregar(nome: str) -> UNetBraco:
    """Carrega uma rede de capo treinada.

    Args:
        nome: nome do peso.

    Returns:
        A rede em modo de avaliação.
    """
    modelo = UNetBraco(pesos_imagenet=False, canais=1).to(_dispositivo())
    modelo.load_state_dict(
        torch.load(DIR_PESOS / f"{nome}.pt", map_location=_dispositivo())
    )
    return modelo.eval()


def perfil_entre_cordas(mapa: np.ndarray, cordas: tuple[list, list]) -> np.ndarray:
    """A média do mapa entre as cordas, por coluna da faixa.

    Args:
        mapa: probabilidades ``(192, 1024)``.
        cordas: as cordas 1 e 6 na faixa.

    Returns:
        Perfil ``(1024,)``.
    """
    perfil = np.zeros(LARGURA_FAIXA, dtype=np.float64)
    for x in range(LARGURA_FAIXA):
        y1 = _ponto_na_reta(cordas[0], x)[1]
        y6 = _ponto_na_reta(cordas[1], x)[1]
        lo, hi = sorted((int(np.rint(y1)), int(np.rint(y6))))
        lo, hi = max(lo, 0), min(hi, ALTURA_FAIXA - 1)
        if hi > lo:
            perfil[x] = float(mapa[lo : hi + 1, x].mean())
    return perfil


@torch.no_grad()
def pico_do_quadro(
    modelo: nn.Module, imagem: np.ndarray, previsto: dict
) -> dict | None:
    """O pico do capo num quadro, na faixa das marcas previstas pelo par antigo.

    Args:
        modelo: rede de capo.
        imagem: quadro BGR.
        previsto: entrada de ``previsto.json`` do par antigo.

    Returns:
        ``{"nota", "ponto"}`` (ponto no quadro), ou None sem braço previsto.
    """
    marcas = marcas_do_previsto(previsto)
    if marcas is None:
        return None
    matriz = matriz_da_faixa(eixo_da_faixa(marcas_da_cabeca(marcas)))
    faixa = recortar(imagem, matriz)
    rgb = torch.from_numpy(np.ascontiguousarray(faixa[None, ..., ::-1]))
    with torch.autocast("cuda", dtype=torch.float16):
        logits = modelo(para_modelo(rgb))
    mapa = torch.sigmoid(logits.float())[0, 0].cpu().numpy()
    cordas = (
        aplicar_matriz(matriz, marcas.corda1).tolist(),
        aplicar_matriz(matriz, marcas.corda6).tolist(),
    )
    perfil = perfil_entre_cordas(mapa, cordas)
    x = int(np.argmax(perfil))
    meio = (_ponto_na_reta(cordas[0], x) + _ponto_na_reta(cordas[1], x)) / 2.0
    return {
        "nota": float(perfil[x]),
        "ponto": voltar([meio.tolist()], matriz)[0].tolist(),
    }


def _antigo(fonte: str) -> dict:
    """As previsões do par antigo (quadro original) de uma fonte da escolha ou da prova.

    Args:
        fonte: ``M39``, ``M29``, ``M44``, ``M43`` ou ``M47``.

    Returns:
        ``{id: entrada de previsto.json}``.
    """
    rodada = RODADA_DA_FONTE[fonte]
    caminho = SAIDA / "maos" / "m46" / rodada / "antigo.json"
    if not caminho.exists():
        caminho = PASTA_HIPOTESES / rodada / f"{nome_da_hipotese(*REFERENCIA)}.json"
    return _ler_json(caminho)["quadros"]


def picos() -> dict:
    """Os picos de cada semente em cada quadro com braço da escolha e da prova (GPU).

    Returns:
        ``{semente: {fonte: {id: pico ou None}}}``; também gravado em ``ARQUIVO_PICOS``.
    """
    saida: dict[str, dict] = {}
    with trava_gpu("maos", "~5 min"):
        for semente in SEMENTES:
            modelo = carregar(f"{PREFIXO}{semente}")
            por_fonte: dict[str, dict] = {}
            for fonte, gabarito, pasta in ESCOLHA + PROVA:
                antigo = _antigo(fonte)
                indice = _indice(pasta)
                por_fonte[fonte] = {}
                for id_q, registro in _ler_json(gabarito)["quadros"].items():
                    if registro.get("braco") != "sim" or id_q not in antigo:
                        continue
                    imagem = cv2.imread(str(pasta / indice[id_q]["png"]))
                    por_fonte[fonte][id_q] = pico_do_quadro(
                        modelo, imagem, antigo[id_q]
                    )
            saida[str(semente)] = por_fonte
    gravar_atomico(ARQUIVO_PICOS, saida)
    return saida


def achado(pico: dict | None, registro: dict, limiar: float) -> bool:
    """Se o capo previsto está a ≤ ½ casa do ``k`` do dono, ao longo do braço.

    Args:
        pico: ``{"nota", "ponto"}`` ou None.
        registro: registro do dono (com ``capo``, ``nut`` e ``trastes``).
        limiar: nota mínima.

    Returns:
        True se o capo foi visto e está na tolerância.
    """
    marcas = marcas_do_registro(registro)
    if (
        pico is None
        or pico["nota"] < limiar
        or marcas is None
        or not tem_capo(registro)
    ):
        return False
    pontos = sorted(marcas.trastes.items())
    if marcas.nut is not None:
        pontos = [(0, np.asarray(marcas.nut, dtype=float)), *pontos]
    if len(pontos) < 2:
        return False
    eixo = np.asarray(pontos[1][1]) - np.asarray(pontos[0][1])
    casa = float(np.linalg.norm(eixo))
    if casa == 0:
        return False
    eixo = eixo / casa
    desvio = float((np.asarray(pico["ponto"]) - np.asarray(registro["capo"])) @ eixo)
    return abs(desvio) <= TOLERANCIA_ACHADO * casa


def limiar_dos_sem_capo(
    notas: list[float], permitidos: int = FALSOS_PERMITIDOS
) -> float:
    """O menor limiar com no máximo ``permitidos`` quadros sem capo acima dele.

    Args:
        notas: o pico de cada quadro sem capo (0 sem braço previsto).
        permitidos: quantos podem passar.

    Returns:
        O limiar.
    """
    ordenadas = sorted(notas, reverse=True)
    if len(ordenadas) <= permitidos:
        return 0.0
    return ordenadas[permitidos] + 1e-6


def escolher() -> dict:
    """Escolhe a semente e o limiar na escolha (M39, M29 e M44), pelo pré-registro.

    Returns:
        A escolha e a tabela; também gravadas em ``ARQUIVO_ESCOLHA``.
    """
    todos = _ler_json(ARQUIVO_PICOS)
    gabaritos = {f: _ler_json(g)["quadros"] for f, g, _ in ESCOLHA}
    tabela = []
    for semente in SEMENTES:
        p = todos[str(semente)]
        notas_sem = [
            (pico or {"nota": 0.0})["nota"]
            for fonte in ("M29", "M44", "M39")
            for id_q, pico in p[fonte].items()
            if not tem_capo(gabaritos[fonte][id_q])
        ]
        limiar = limiar_dos_sem_capo(notas_sem)
        com = {
            i: r for i, r in gabaritos["M39"].items() if tem_capo(r) and i in p["M39"]
        }
        achados = sum(1 for i, r in com.items() if achado(p["M39"][i], r, limiar))
        tabela.append(
            {
                "semente": semente,
                "limiar": limiar,
                "sem_capo": [sum(1 for n in notas_sem if n >= limiar), len(notas_sem)],
                "achados_M39": [achados, len(com)],
            }
        )
    melhor = max(tabela, key=lambda t: (t["achados_M39"][0], -t["semente"]))
    achados, total = melhor["achados_M39"]
    escolha = {
        "semente": melhor["semente"],
        "limiar": melhor["limiar"],
        "segue_para_prova": achados >= FRACAO_ACHADO_MIN * total,
        "tabela": tabela,
    }
    gravar_atomico(ARQUIVO_ESCOLHA, escolha)
    return escolha


def com_capo(
    base: dict, antigo: dict[str, dict], picos_fonte: dict, limiar: float, faixas: dict
) -> tuple[dict, dict]:
    """A cadeia da 1045: a da 1047, e o nut pela conta onde o capo é visto.

    Args:
        base: ``previsto.json`` da cadeia da 1047 (sem tomada).
        antigo: previsões do par antigo por id.
        picos_fonte: ``{id: pico ou None}`` da semente escolhida.
        limiar: o limiar escolhido.
        faixas: as faixas dos validadores da 1044.

    Returns:
        ``(previsto, registro)`` com o capo por quadro.
    """
    quadros, registro = {}, {}
    for id_q, quadro in base["quadros"].items():
        pico = picos_fonte.get(id_q)
        if pico is None or pico["nota"] < limiar or not antigo[id_q].get("achou"):
            quadros[id_q] = quadro
            registro[id_q] = {"visto": False}
            continue
        x, y = pico["ponto"]
        caixa = {"caixa": [x - 1.0, y - 1.0, x + 1.0, y + 1.0], "nota": pico["nota"]}
        novo = nut_pela_conta(antigo[id_q], caixa)
        if novo is None:
            quadros[id_q] = dict(
                antigo[id_q], sinalizado=True, motivo="capo sem traste"
            )
            registro[id_q] = {"visto": True, "casa": None}
            continue
        valido = validar(marcas_do_previsto(novo), faixas)["passa"]
        duvida = pico["nota"] < limiar + FAIXA_DUVIDA
        novo["sinalizado"] = bool(antigo[id_q]["sinalizado"] or duvida or not valido)
        quadros[id_q] = novo
        registro[id_q] = {
            "visto": True,
            "casa": novo["capo_casa"],
            "valido": valido,
            "duvida": duvida,
        }
    return dict(base, quadros=quadros), registro


def _sem_linhas(medida: dict) -> dict:
    """A medida sem as linhas quadro a quadro.

    Args:
        medida: saída de ``medir_por_grupo``.

    Returns:
        Cópia sem ``linhas``.
    """
    return {k: v for k, v in medida.items() if k != "linhas"}


def medir() -> dict:
    """Mede a cadeia da 1045 na prova (1043 e M47), com a escolha congelada.

    Returns:
        As medidas, os critérios e o registro do capo; também em ``ARQUIVO_MEDIDA``.
    """
    escolha = _ler_json(ARQUIVO_ESCOLHA)
    p = _ler_json(ARQUIVO_PICOS)[str(escolha["semente"])]
    faixas = ler_faixas()
    medidas = {}
    for fonte, gabarito_caminho, _ in PROVA:
        rodada = RODADA_DA_FONTE[fonte]
        gabarito = _ler_json(gabarito_caminho)
        base, _ = cadeia(rodada, faixas, tomada=False)
        doc, registro = com_capo(
            base, _antigo(fonte), p[fonte], escolha["limiar"], faixas
        )
        nova = medir_por_grupo(doc, gabarito)
        velha = medir_por_grupo(base, gabarito)
        capo_falso = sum(
            1
            for id_q, r in registro.items()
            if r["visto"]
            and gabarito["quadros"][id_q].get("braco") == "sim"
            and not tem_capo(gabarito["quadros"][id_q])
        )
        achados = sum(
            1
            for id_q, r in gabarito["quadros"].items()
            if tem_capo(r) and achado(p[fonte].get(id_q), r, escolha["limiar"])
        )
        medidas[fonte] = {
            "cadeia_1045": _sem_linhas(nova),
            "cadeia_1047": _sem_linhas(velha),
            "capo_falso": capo_falso,
            "capo_achado": [
                achados,
                sum(1 for r in gabarito["quadros"].values() if tem_capo(r)),
            ],
            "registro": registro,
        }
    m43, m47 = medidas["M43"], medidas["M47"]
    n43, n47, v47 = (
        m43["cadeia_1045"]["todos"],
        m47["cadeia_1045"]["todos"],
        m47["cadeia_1047"]["todos"],
    )
    criterios = {
        "1_seguranca": {
            "falsos": n43["falsos_passam_n"],
            "passa": n43["falsos_passam_n"] <= 2,
        },
        "2_ganho": {
            "certos": n43["entregue_certo"],
            "passa": n43["entregue_certo"] >= 20,
        },
        "3_capo_falso": {"vistos": m47["capo_falso"], "passa": m47["capo_falso"] <= 1},
        "4_nao_estragar": {
            "falsos_novo_1047": [n47["falsos_passam_n"], v47["falsos_passam_n"]],
            "certos_novo_1047": [n47["entregue_certo"], v47["entregue_certo"]],
            "passa": n47["falsos_passam_n"] <= v47["falsos_passam_n"] + 1
            and n47["entregue_certo"] >= v47["entregue_certo"] - 1,
        },
    }
    resultado = {"escolha": escolha, "criterios": criterios, "medidas": medidas}
    gravar_atomico(ARQUIVO_MEDIDA, resultado)
    return resultado


def contar() -> dict:
    """Conta os quadros de treino, de escolha e de prova, com e sem capo.

    Returns:
        A contagem por papel e por canal; também em ``ARQUIVO_CONTAGEM``.
    """
    papeis = {
        "treino": treino(),
        "escolha": registros(ESCOLHA),
        "prova": registros(PROVA),
    }
    contagem = {}
    for papel, regs in papeis.items():
        por_canal: dict[str, list[int]] = {}
        for r in regs:
            linha = por_canal.setdefault(r["canal"], [0, 0])
            linha[0 if r["capo"] is not None else 1] += 1
        contagem[papel] = {
            "com_capo": sum(v[0] for v in por_canal.values()),
            "sem_capo": sum(v[1] for v in por_canal.values()),
            "por_canal_com_sem": por_canal,
        }
    gravar_atomico(ARQUIVO_CONTAGEM, contagem)
    return contagem


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("contar")
    p_treino = sub.add_parser("treinar")
    p_treino.add_argument("--semente", type=int, required=True)
    p_treino.add_argument("--passos", type=int, default=PASSOS)
    p_treino.add_argument("--sem-gravar", action="store_true")
    sub.add_parser("picos")
    sub.add_parser("escolher")
    sub.add_parser("medir")
    args = parser.parse_args()
    if args.comando == "contar":
        resultado = contar()
    elif args.comando == "treinar":
        resultado = treinar(args.semente, args.passos, not args.sem_gravar)
        resultado.pop("perdas_a_cada_100", None)
    elif args.comando == "picos":
        picos()
        resultado = {"gravado": str(ARQUIVO_PICOS)}
    elif args.comando == "escolher":
        resultado = escolher()
    else:
        resultado = medir()["criterios"]
    print(json.dumps(resultado, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
