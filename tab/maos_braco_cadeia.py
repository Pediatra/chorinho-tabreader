"""Braço em cadeia (M11b): rastreio por passos, com âncora no quadro-chave.

O rastreador anda do quadro-chave ao alvo em passos fixos de tempo. Em cada passo,
os pontos ORB são procurados só numa janela: a máscara do braço levada pela
homografia do passo anterior, alargada e recortada pela caixa do painel que contém o
braço no quadro-chave. Essa janela é a correção da rodada 1015, em que os pontos
caíam na tablatura.

Em cada passo há duas tentativas de homografia:

- **âncora**: o quadro-chave (pontos só na máscara do braço da chave) contra o passo;
- **cadeia**: o passo anterior contra o passo, composto com a homografia anterior.

Se as duas existem e discordam, o passo é "não achei". Se a homografia nova dá um
salto grande das marcas, há troca de plano: a cadeia para, e só um casamento direto
com o quadro-chave volta a dizer "achei". Nada da tablatura entra no rastreio, e o
gabarito do alvo só serve para medir.

A CLI ``python -m tab.maos_braco_cadeia dev`` roda os 38 pares de desenvolvimento
(``PARES_DESENVOLVIMENTO`` e ``PARES_TESTE`` de ``tab.maos_braco_tempo``) e grava
``dev_<rotulo>.json`` em ``MAOS_M11 / "cadeia"``. Com ``--desenhar``, grava as imagens
das marcas (previstas em vermelho, do dono em verde). O subcomando ``pares``
roda a mesma medida em pares dados por arquivo.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import json
import subprocess
import sys
import time
from collections.abc import Iterable, Iterator
from pathlib import Path

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, MAOS_M3B, MAOS_M3B_QUADROS, MAOS_M11, acervo
from .maos_braco_rastreio import (
    _cinza,
    _classe_do_par,
    _desenhar_marcas,
    _vao_px,
    mascara_do_braco,
)
from .maos_braco_tempo import (
    PARES_DESENVOLVIMENTO,
    PARES_TESTE,
    Marcas,
    marcas_do_registro,
    transformar,
)

#: Mínimo de casamentos para estimar uma homografia (4 pares de pontos).
CASAMENTOS_MINIMOS = 4
#: Semente fixa do RANSAC (o cv2 usa o gerador global).
SEMENTE_RANSAC = 0
#: Escala aceitável da homografia (raiz do determinante do bloco 2x2).
ESCALA_MINIMA = 0.2
ESCALA_MAXIMA = 5.0
#: Pontos de cada passo que entram no cálculo do salto e do desacordo.
TOLERANCIA_TEMPO = 1e-6


@dataclasses.dataclass(frozen=True)
class ParametrosCadeia:
    """Parâmetros do rastreio em cadeia. Ajustados só no desenvolvimento.

    Attributes:
        passo_s: intervalo entre os quadros do rastreio, em segundos.
        razao_lowe: teste de razão de Lowe para aceitar um casamento.
        min_inliers: inliers mínimos para aceitar uma homografia.
        max_reproj_px: erro de reprojeção mediano máximo dos inliers, em px.
        n_orb: número máximo de pontos ORB por detecção.
        ransac_px: limiar de inlier do RANSAC, em px.
        folga_px: alargamento da janela prevista (pelo passo anterior), em px.
        folga_recuperacao_px: alargamento da janela de recuperação (sem cadeia), em px.
        salto_vao: deslocamento máximo das marcas num passo, em vãos de corda.
        desacordo_vao: discordância máxima entre âncora e cadeia, em vãos de corda.
        bloco_s: tamanho do bloco lido de uma vez quando o alvo vem antes da chave.
    """

    passo_s: float = 0.5
    razao_lowe: float = 0.8
    min_inliers: int = 15
    max_reproj_px: float = 3.0
    n_orb: int = 5000
    ransac_px: float = 3.0
    folga_px: int = 80
    folga_recuperacao_px: int = 400
    salto_vao: float = 1.0
    desacordo_vao: float = 0.5
    bloco_s: float = 30.0


PARAMETROS_PADRAO = ParametrosCadeia()


def _dimensoes(video: Path) -> tuple[int, int]:
    """Largura e altura do primeiro vídeo do arquivo, pelo ffprobe.

    Args:
        video: arquivo no acervo (só leitura).

    Returns:
        ``(largura, altura)`` em px.

    Raises:
        subprocess.CalledProcessError: se o ffprobe falhar.
    """
    comando = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(video),
    ]
    saida = subprocess.run(comando, capture_output=True, text=True, check=True)
    largura, altura = saida.stdout.strip().split("x")
    return int(largura), int(altura)


def _ler_quadro(fluxo, tamanho: int) -> bytes | None:
    """Lê exatamente ``tamanho`` bytes do fluxo, ou ``None`` no fim.

    Args:
        fluxo: fluxo binário do ffmpeg.
        tamanho: bytes de um quadro.

    Returns:
        Os bytes do quadro, ou ``None`` se o fluxo acabou antes de um quadro cheio.
    """
    buffer = bytearray()
    while len(buffer) < tamanho:
        pedaco = fluxo.read(tamanho - len(buffer))
        if not pedaco:
            break
        buffer.extend(pedaco)
    if len(buffer) != tamanho:
        return None
    return bytes(buffer)


def ler_trecho(
    video: Path, t_ini: float, t_fim: float, passo_s: float
) -> Iterator[tuple[float, np.ndarray]]:
    """Quadros de um trecho, num passo fixo, em ordem de tempo (um processo ffmpeg).

    O ffmpeg lê com ``-ss`` antes de ``-i`` e filtra ``fps=1/passo``. O instante de
    cada quadro é nominal: ``t_ini + k * passo_s``.

    Args:
        video: arquivo no acervo (só leitura).
        t_ini: início do trecho, em segundos.
        t_fim: fim do trecho (exclusive), em segundos.
        passo_s: intervalo entre os quadros, em segundos.

    Yields:
        ``(t, imagem)`` com a imagem BGR na resolução nativa.

    Raises:
        RuntimeError: se o ffmpeg falhar.
    """
    if t_fim <= t_ini:
        return
    largura, altura = _dimensoes(video)
    tamanho = largura * altura * 3
    comando = [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-ss",
        f"{t_ini:.3f}",
        "-i",
        str(video),
        "-t",
        f"{t_fim - t_ini:.3f}",
        "-map",
        "0:v:0",
        "-vf",
        f"fps=1/{passo_s:.6f}",
        "-an",
        "-sn",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-",
    ]
    processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        k = 0
        while True:
            t = t_ini + k * passo_s
            if t >= t_fim - TOLERANCIA_TEMPO:
                break
            bruto = _ler_quadro(processo.stdout, tamanho)
            if bruto is None:
                break
            imagem = np.frombuffer(bruto, dtype=np.uint8).reshape(altura, largura, 3)
            yield t, imagem.copy()
            k += 1
        codigo = processo.wait()
        if codigo != 0:
            erro = processo.stderr.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ffmpeg falhou em {video}: {erro.strip()}")
    finally:
        if processo.poll() is None:
            processo.kill()
            processo.wait()
        processo.stdout.close()
        processo.stderr.close()


def ler_reverso(
    video: Path, t_baixo: float, t_alto: float, passo_s: float, bloco_s: float
) -> Iterator[tuple[float, np.ndarray]]:
    """Quadros de um trecho em ordem de tempo decrescente, lidos em blocos.

    Cada bloco tem ``bloco_s`` segundos e é lido para a memória uma vez; a memória
    fica limitada a um bloco, e não ao trecho inteiro.

    Args:
        video: arquivo no acervo (só leitura).
        t_baixo: início do trecho (inclusive), em segundos.
        t_alto: fim do trecho (exclusive), em segundos.
        passo_s: intervalo entre os quadros, em segundos.
        bloco_s: tamanho de cada bloco lido de uma vez, em segundos.

    Yields:
        ``(t, imagem)`` do mais novo para o mais antigo.
    """
    topo = t_alto
    while topo > t_baixo + TOLERANCIA_TEMPO:
        base = max(t_baixo, topo - bloco_s)
        quadros = list(ler_trecho(video, base, topo, passo_s))
        yield from reversed(quadros)
        topo = base


def sequencia_ate_alvo(
    video: Path,
    t_chave: float,
    t_alvo: float,
    img_alvo: np.ndarray,
    passo_s: float,
    bloco_s: float,
) -> Iterator[tuple[float, np.ndarray]]:
    """Quadros do passo a passo da chave até o alvo, o alvo por último.

    O alvo entra como a imagem dada (o PNG da ferramenta, que é onde estão as marcas
    do dono). Os quadros intermediários vêm do ffmpeg, no mesmo passo.

    Args:
        video: arquivo no acervo (só leitura).
        t_chave: instante do quadro-chave, em segundos.
        t_alvo: instante do alvo, em segundos.
        img_alvo: imagem BGR do alvo.
        passo_s: intervalo entre os quadros, em segundos.
        bloco_s: tamanho do bloco de leitura quando o alvo vem antes da chave.

    Yields:
        ``(t, imagem)`` na ordem da cadeia, terminando no alvo.
    """
    if t_alvo > t_chave:
        intermediarios = ler_trecho(video, t_chave + passo_s, t_alvo, passo_s)
    elif t_alvo < t_chave:
        intermediarios = ler_reverso(
            video, t_alvo + passo_s, t_chave - passo_s, passo_s, bloco_s
        )
    else:
        intermediarios = iter(())
    yield from intermediarios
    yield t_alvo, img_alvo


def _dilatar(mascara: np.ndarray, folga: int) -> np.ndarray:
    """Alarga uma máscara por um quadrado de ``folga`` px de cada lado.

    Args:
        mascara: máscara uint8 (0 ou 255).
        folga: alargamento em px; 0 devolve uma cópia.

    Returns:
        Máscara uint8 alargada.
    """
    if folga <= 0:
        return mascara.copy()
    tamanho = 2 * folga + 1
    nucleo = cv2.getStructuringElement(cv2.MORPH_RECT, (tamanho, tamanho))
    return cv2.dilate(mascara, nucleo)


def _caixa_do_braco(
    paineis: str | list | None, mascara_chave: np.ndarray
) -> np.ndarray | None:
    """Máscara da caixa do painel que contém o braço no quadro-chave.

    Args:
        paineis: campo ``paineis`` do registro (``"nao"`` ou lista de caixas
            ``[[x0, y0], [x1, y1]]``).
        mascara_chave: máscara do braço no quadro-chave.

    Returns:
        Máscara uint8 da caixa com mais pixels do braço, ou ``None`` (quadro inteiro)
        quando não há caixas ou o braço não cai em nenhuma.
    """
    if not isinstance(paineis, list) or not paineis:
        return None
    melhor, melhor_pixels = None, 0
    for caixa in paineis:
        (x0, y0), (x1, y1) = caixa
        x0, x1 = sorted((round(x0), round(x1)))
        y0, y1 = sorted((round(y0), round(y1)))
        pixels = int(np.count_nonzero(mascara_chave[y0:y1, x0:x1]))
        if pixels > melhor_pixels:
            melhor, melhor_pixels = (x0, y0, x1, y1), pixels
    if melhor is None:
        return None
    x0, y0, x1, y1 = melhor
    caixa_mask = np.zeros_like(mascara_chave)
    caixa_mask[y0:y1, x0:x1] = 255
    return caixa_mask


def _janela_prevista(
    mascara_chave: np.ndarray,
    h_prev: np.ndarray,
    forma: tuple[int, int],
    folga: int,
    caixa: np.ndarray | None,
) -> np.ndarray:
    """Janela de busca de um passo: o braço previsto pelo passo anterior.

    Args:
        mascara_chave: máscara do braço no quadro-chave.
        h_prev: homografia do quadro-chave ao passo anterior.
        forma: ``(altura, largura)`` do quadro.
        folga: alargamento da janela, em px.
        caixa: máscara do painel do braço, ou ``None``.

    Returns:
        Máscara uint8 da janela no quadro do passo.
    """
    altura, largura = forma
    prevista = cv2.warpPerspective(
        mascara_chave, h_prev, (largura, altura), flags=cv2.INTER_NEAREST
    )
    janela = _dilatar(prevista, folga)
    if caixa is not None:
        janela = cv2.bitwise_and(janela, caixa)
    return janela


def _janela_recuperacao(
    mascara_chave: np.ndarray, folga: int, caixa: np.ndarray | None
) -> np.ndarray:
    """Janela de recuperação (sem cadeia): o braço do quadro-chave alargado.

    Args:
        mascara_chave: máscara do braço no quadro-chave.
        folga: alargamento da janela, em px.
        caixa: máscara do painel do braço, ou ``None``.

    Returns:
        Máscara uint8 da janela.
    """
    janela = _dilatar(mascara_chave, folga)
    if caixa is not None:
        janela = cv2.bitwise_and(janela, caixa)
    return janela


def _pontos_das_marcas(marcas: Marcas) -> np.ndarray:
    """Todos os pontos das marcas (cordas, nut e trastes) num array ``(n, 2)``.

    Args:
        marcas: marcas do quadro.

    Returns:
        Array ``(n, 2)`` float.
    """
    partes = [marcas.corda1, marcas.corda6]
    if marcas.nut is not None:
        partes.append(marcas.nut[np.newaxis, :])
    if marcas.trastes:
        partes.append(np.stack(list(marcas.trastes.values())))
    return np.vstack(partes)


def _deslocamento_vao(marcas_chave: Marcas, h_a: np.ndarray, h_b: np.ndarray) -> float:
    """Maior deslocamento entre duas homografias, em vãos de corda.

    O vão é medido na projeção ``h_a``. Se o vão não é definido, o deslocamento é
    infinito (o caso é tratado como ruim).

    Args:
        marcas_chave: marcas do quadro-chave.
        h_a: primeira homografia (chave ao passo).
        h_b: segunda homografia (chave ao passo).

    Returns:
        Deslocamento máximo das marcas, em vãos.
    """
    proj_a = transformar(marcas_chave, h_a)
    proj_b = transformar(marcas_chave, h_b)
    try:
        vao = _vao_px(proj_a)
    except ValueError:
        return float("inf")
    deslocamento = np.linalg.norm(
        _pontos_das_marcas(proj_a) - _pontos_das_marcas(proj_b), axis=1
    )
    return float(np.max(deslocamento) / vao)


def _casar(
    des_a: np.ndarray | None,
    kp_a: list,
    des_b: np.ndarray | None,
    kp_b: list,
    params: ParametrosCadeia,
) -> tuple[np.ndarray | None, int, float | None]:
    """Homografia de ``a`` para ``b`` por casamento ORB e RANSAC.

    Args:
        des_a: descritores de ``a`` (ou ``None``).
        kp_a: pontos de ``a``.
        des_b: descritores de ``b`` (ou ``None``).
        kp_b: pontos de ``b``.
        params: parâmetros do rastreio.

    Returns:
        ``(h, inliers, reproj)``. ``h`` é ``None`` quando não passa nos limiares;
        ``inliers`` e ``reproj`` dizem o que foi medido (``reproj`` pode ser ``None``).
    """
    if des_a is None or des_b is None:
        return None, 0, None
    pares = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(des_a, des_b, k=2)
    bons = [
        p[0]
        for p in pares
        if len(p) == 2 and p[0].distance < params.razao_lowe * p[1].distance
    ]
    if len(bons) < CASAMENTOS_MINIMOS:
        return None, 0, None
    origem = np.float32([kp_a[m.queryIdx].pt for m in bons]).reshape(-1, 1, 2)
    destino = np.float32([kp_b[m.trainIdx].pt for m in bons]).reshape(-1, 1, 2)
    cv2.setRNGSeed(SEMENTE_RANSAC)
    h, mascara = cv2.findHomography(origem, destino, cv2.RANSAC, params.ransac_px)
    if h is None or not np.all(np.isfinite(h)):
        return None, 0, None
    ativos = mascara.ravel().astype(bool)
    inliers = int(np.count_nonzero(ativos))
    if inliers < params.min_inliers:
        return None, inliers, None
    previsto = cv2.perspectiveTransform(origem[ativos], h)
    erro = np.linalg.norm(previsto - destino[ativos], axis=2).ravel()
    reproj = float(np.median(erro))
    if reproj > params.max_reproj_px:
        return None, inliers, reproj
    det = float(np.linalg.det(h[:2, :2]))
    if det <= 0.0 or not ESCALA_MINIMA**2 <= det <= ESCALA_MAXIMA**2:
        return None, inliers, reproj
    return h, inliers, reproj


def rastrear_cadeia(
    quadros: Iterable[tuple[float, np.ndarray]],
    img_chave: np.ndarray,
    marcas_chave: Marcas,
    paineis: str | list | None,
    params: ParametrosCadeia = PARAMETROS_PADRAO,
) -> tuple[np.ndarray | None, dict]:
    """Acha o braço do quadro-chave no último quadro, em cadeia com âncora.

    Args:
        quadros: ``(t, imagem)`` na ordem da cadeia; o último é o alvo.
        img_chave: quadro-chave.
        marcas_chave: marcas do quadro-chave (para a máscara do braço).
        paineis: campo ``paineis`` do registro do quadro-chave.
        params: parâmetros do rastreio.

    Returns:
        ``(h, info)``: ``h`` é a homografia do quadro-chave ao último quadro, ou
        ``None`` ("não achei"). ``info`` traz os contadores por fonte (``ancora``,
        ``cadeia``, ``ancora+cadeia``), ``perdido``, ``desacordo``, ``salto`` e
        ``passos``.

    Raises:
        ValueError: se a sequência de quadros é vazia.
    """
    cinza_chave = _cinza(img_chave)
    forma = cinza_chave.shape[:2]
    mascara_chave = mascara_do_braco(marcas_chave, forma)
    caixa = _caixa_do_braco(paineis, mascara_chave)
    orb = cv2.ORB_create(nfeatures=params.n_orb)
    kp_chave, des_chave = orb.detectAndCompute(cinza_chave, mascara_chave)

    info: dict = {
        "passos": 0,
        "ancora": 0,
        "cadeia": 0,
        "ancora+cadeia": 0,
        "perdido": 0,
        "desacordo": 0,
        "salto": 0,
    }
    h_prev: np.ndarray | None = np.eye(3)
    kp_prev, des_prev = kp_chave, des_chave
    h_ultimo: np.ndarray | None = None
    visto = False

    for _t, img in quadros:
        visto = True
        info["passos"] += 1
        cinza = _cinza(img)
        if h_prev is not None:
            janela = _janela_prevista(
                mascara_chave, h_prev, forma, params.folga_px, caixa
            )
        else:
            janela = _janela_recuperacao(
                mascara_chave, params.folga_recuperacao_px, caixa
            )
        kp_cur, des_cur = orb.detectAndCompute(cinza, janela)

        h_ancora, _, _ = _casar(des_chave, kp_chave, des_cur, kp_cur, params)
        h_cadeia = None
        if h_prev is not None:
            h_passo, _, _ = _casar(des_prev, kp_prev, des_cur, kp_cur, params)
            if h_passo is not None:
                h_cadeia = h_passo @ h_prev

        escolha: np.ndarray | None = None
        fonte = None
        if h_ancora is not None and h_cadeia is not None:
            if _deslocamento_vao(marcas_chave, h_ancora, h_cadeia) > (
                params.desacordo_vao
            ):
                info["desacordo"] += 1
            else:
                escolha, fonte = h_ancora, "ancora+cadeia"
        elif h_ancora is not None:
            escolha, fonte = h_ancora, "ancora"
        elif h_cadeia is not None:
            escolha, fonte = h_cadeia, "cadeia"

        if (
            escolha is not None
            and h_prev is not None
            and _deslocamento_vao(marcas_chave, h_prev, escolha) > params.salto_vao
        ):
            info["salto"] += 1
            escolha, fonte = None, None

        if escolha is None:
            info["perdido"] += 1
            h_prev = None
            kp_prev, des_prev = [], None
        else:
            info[fonte] += 1
            h_prev = escolha
            kp_prev, des_prev = kp_cur, des_cur
        h_ultimo = escolha

    if not visto:
        raise ValueError("sequência de quadros vazia")
    return h_ultimo, info


def _ler_png(pasta: str, identificador: str) -> np.ndarray:
    """Lê um quadro PNG de uma pasta, em cores.

    Args:
        pasta: pasta dos quadros.
        identificador: id do quadro (``q02``...).

    Returns:
        Imagem BGR.

    Raises:
        FileNotFoundError: se o quadro não existe na pasta.
    """
    caminho = Path(pasta) / f"{identificador}.png"
    img = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(caminho)
    return img


def _tarefa(
    chave: str,
    alvo: str,
    canal: str,
    arquivo: str,
    t_chave: float,
    t_alvo: float,
    reg_chave: dict,
    reg_alvo: dict,
    params: ParametrosCadeia,
    pasta_quadros: str,
    pasta_desenhos: str | None,
) -> dict:
    """Roda o rastreio num par e mede o resultado (função de trabalho).

    Args:
        chave: id do quadro-chave.
        alvo: id do quadro alvo.
        canal: canal do vídeo.
        arquivo: caminho do vídeo relativo ao acervo.
        t_chave: instante do quadro-chave, em segundos.
        t_alvo: instante do alvo, em segundos.
        reg_chave: registro do quadro-chave no gabarito.
        reg_alvo: registro do alvo no gabarito.
        params: parâmetros do rastreio.
        pasta_quadros: pasta dos quadros PNG (``<id>.png``).
        pasta_desenhos: pasta onde gravar as imagens, ou ``None``.

    Returns:
        Entrada do par, com a classe e os erros.
    """
    video = acervo() / arquivo
    img_chave = _ler_png(pasta_quadros, chave)
    img_alvo = _ler_png(pasta_quadros, alvo)
    marcas_chave = marcas_do_registro(reg_chave)
    marcas_alvo = marcas_do_registro(reg_alvo)
    if marcas_chave is None:
        raise ValueError(f"quadro-chave {chave} sem marcas")
    braco = reg_alvo.get("braco")
    quadros = sequencia_ate_alvo(
        video, t_chave, t_alvo, img_alvo, params.passo_s, params.bloco_s
    )
    h, info = rastrear_cadeia(
        quadros, img_chave, marcas_chave, reg_chave.get("paineis"), params
    )
    e, classe = _classe_do_par(h, marcas_chave, marcas_alvo, braco)
    if pasta_desenhos is not None:
        _gravar_desenho(
            Path(pasta_desenhos), chave, alvo, img_alvo, marcas_chave, marcas_alvo, h
        )
    return {
        "chave": chave,
        "alvo": alvo,
        "canal": canal,
        "t_chave": t_chave,
        "t_alvo": t_alvo,
        "braco_alvo": braco,
        "achou": h is not None,
        "classe": classe,
        "erros": e,
        "info": info,
    }


def _gravar_desenho(
    pasta: Path,
    chave: str,
    alvo: str,
    img_alvo: np.ndarray,
    marcas_chave: Marcas,
    marcas_alvo: Marcas | None,
    h: np.ndarray | None,
) -> None:
    """Grava o alvo com as marcas previstas (vermelho) e do dono (verde).

    Args:
        pasta: pasta de saída.
        chave: id do quadro-chave.
        alvo: id do quadro alvo.
        img_alvo: imagem do alvo.
        marcas_chave: marcas do quadro-chave.
        marcas_alvo: marcas do dono no alvo, ou ``None``.
        h: homografia prevista, ou ``None``.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    desenho = img_alvo.copy()
    if marcas_alvo is not None:
        _desenhar_marcas(desenho, marcas_alvo, (0, 255, 0))
    if h is not None:
        _desenhar_marcas(desenho, transformar(marcas_chave, h), (0, 0, 255))
    cv2.imwrite(str(pasta / f"{chave}_{alvo}.jpg"), desenho)


def _resumo(entradas: list[dict]) -> dict:
    """Contagens e cobertura de um conjunto de pares.

    Args:
        entradas: entradas de ``_tarefa``.

    Returns:
        Dicionário com ``pares``, ``braco_sim``, ``achou``, ``certo``, ``impreciso``,
        ``falso``, ``nao_achou``, ``sem_medida`` e as razões.
    """
    contagem = {
        "pares": len(entradas),
        "braco_sim": sum(1 for x in entradas if x["braco_alvo"] == "sim"),
        "achou": sum(1 for x in entradas if x["achou"]),
    }
    for classe in ("certo", "impreciso", "falso", "nao_achou", "sem_medida"):
        contagem[classe] = sum(1 for x in entradas if x["classe"] == classe)
    certos_sim = sum(
        1 for x in entradas if x["classe"] == "certo" and x["braco_alvo"] == "sim"
    )
    contagem["cobertura"] = (
        certos_sim / contagem["braco_sim"] if contagem["braco_sim"] else None
    )
    contagem["certos_por_achei"] = (
        contagem["certo"] / contagem["achou"] if contagem["achou"] else None
    )
    return contagem


def _formatar(valor: float | None) -> str:
    """Número com 2 casas, ou traço se ausente.

    Args:
        valor: número ou None.

    Returns:
        Texto para a tabela.
    """
    return "—" if valor is None else f"{valor:.2f}"


def _imprimir(entradas: list[dict]) -> None:
    """Imprime a tabela por par, o resumo por canal e o resumo geral.

    Args:
        entradas: entradas de ``_tarefa``.
    """
    print(
        f"{'par':<12}{'canal':<14}{'achou':>6}{'passos':>7}{'anc':>5}{'cad':>5}"
        f"{'perd':>6}{'nut':>7}{'pior':>7}{'perp':>7}  classe"
    )
    for x in entradas:
        info = x["info"]
        e = x["erros"]
        anc = info["ancora"] + info["ancora+cadeia"]
        print(
            f"{x['chave'] + '->' + x['alvo']:<12}{x['canal'][:13]:<14}"
            f"{'sim' if x['achou'] else 'não':>6}{info['passos']:>7}{anc:>5}"
            f"{info['cadeia']:>5}{info['perdido']:>6}"
            f"{_formatar(None if e is None else e['nut_casas']):>7}"
            f"{_formatar(None if e is None else e['pior_traste_casas']):>7}"
            f"{_formatar(None if e is None else e['perp_cordas']):>7}  {x['classe']}"
        )
    print()
    canais = sorted({x["canal"] for x in entradas})
    print(
        f"{'canal':<18}{'pares':>6}{'certo':>7}{'impr':>6}{'falso':>7}"
        f"{'n_ach':>7}{'braço':>7}{'cobert':>8}"
    )
    for canal in [*canais, "GERAL"]:
        grupo = (
            entradas
            if canal == "GERAL"
            else [x for x in entradas if x["canal"] == canal]
        )
        r = _resumo(grupo)
        cobertura = "—" if r["cobertura"] is None else f"{r['cobertura']:.2f}"
        print(
            f"{canal:<18}{r['pares']:>6}{r['certo']:>7}{r['impreciso']:>6}"
            f"{r['falso']:>7}{r['nao_achou']:>7}{r['braco_sim']:>7}{cobertura:>8}"
        )
    geral = _resumo(entradas)
    print(
        f"certos/achei={_formatar(geral['certos_por_achei'])} "
        f"falsos={geral['falso']} cobertura={_formatar(geral['cobertura'])}"
    )


def _tarefas(
    pares: tuple[tuple[str, str], ...],
    indice_arq: Path,
    ouro_arq: Path,
    pasta_quadros: str,
    params: ParametrosCadeia,
    pasta_desenhos: str | None,
) -> list[dict]:
    """Monta uma tarefa por par, com os registros do gabarito e os instantes do índice.

    Args:
        pares: pares (quadro-chave, alvo).
        indice_arq: ``indice.json`` com ``arquivo``, ``canal`` e ``t`` de cada quadro.
        ouro_arq: gabarito do braço (campo ``quadros``).
        pasta_quadros: pasta dos quadros PNG.
        params: parâmetros do rastreio.
        pasta_desenhos: pasta de desenhos, ou ``None``.

    Returns:
        Uma tarefa por par (argumentos de ``_tarefa``).

    Raises:
        ValueError: se um id não está no índice ou no gabarito, ou se o par mistura vídeos.
    """
    gabarito = json.loads(ouro_arq.read_text(encoding="utf-8"))["quadros"]
    indice = json.loads(indice_arq.read_text(encoding="utf-8"))["quadros"]
    por_id = {item["id"]: item for item in indice}
    tarefas = []
    for chave, alvo in pares:
        for identificador in (chave, alvo):
            if identificador not in por_id or identificador not in gabarito:
                raise ValueError(f"{identificador} fora do índice ou do gabarito")
        ic, ia = por_id[chave], por_id[alvo]
        if ic["arquivo"] != ia["arquivo"]:
            raise ValueError(f"{chave} e {alvo} são de vídeos diferentes")
        tarefas.append(
            {
                "chave": chave,
                "alvo": alvo,
                "canal": ic["canal"],
                "arquivo": ic["arquivo"],
                "t_chave": float(ic["t"]),
                "t_alvo": float(ia["t"]),
                "reg_chave": gabarito[chave],
                "reg_alvo": gabarito[alvo],
                "params": params,
                "pasta_quadros": pasta_quadros,
                "pasta_desenhos": pasta_desenhos,
            }
        )
    return tarefas


def _pares_da_entrada(texto: str) -> tuple[tuple[str, str], ...]:
    """Pares (chave, alvo) de um JSON inline ou de um arquivo com o mesmo JSON.

    Args:
        texto: JSON ``[{"chave": ..., "alvo": ...}]`` ou caminho de um arquivo com ele.

    Returns:
        Os pares, na ordem dada.
    """
    bruto = texto.strip()
    if not bruto.startswith("["):
        bruto = Path(texto).read_text(encoding="utf-8")
    return tuple((item["chave"], item["alvo"]) for item in json.loads(bruto))


def _salvar(entradas: list[dict], params: ParametrosCadeia, saida: Path) -> Path:
    """Grava o resultado da rodada num arquivo JSON.

    Args:
        entradas: entradas de ``_tarefa``.
        params: parâmetros usados.
        saida: arquivo de saída (a pasta é criada se faltar).

    Returns:
        Caminho do arquivo gravado.
    """
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(
            {
                "parametros": dataclasses.asdict(params),
                "resumo": _resumo(entradas),
                "pares": entradas,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return saida


def _adicionar_parametros(parser: argparse.ArgumentParser) -> None:
    """Acrescenta à CLI os parâmetros do rastreio (padrões de ``ParametrosCadeia``).

    Args:
        parser: subparser que recebe as opções.
    """
    padrao = PARAMETROS_PADRAO
    parser.add_argument("--passo", type=float, default=padrao.passo_s)
    parser.add_argument("--folga", type=int, default=padrao.folga_px)
    parser.add_argument(
        "--folga-recuperacao", type=int, default=padrao.folga_recuperacao_px
    )
    parser.add_argument("--min-inliers", type=int, default=padrao.min_inliers)
    parser.add_argument("--max-reproj", type=float, default=padrao.max_reproj_px)
    parser.add_argument("--n-orb", type=int, default=padrao.n_orb)
    parser.add_argument("--salto", type=float, default=padrao.salto_vao)
    parser.add_argument("--desacordo", type=float, default=padrao.desacordo_vao)
    parser.add_argument("--workers", type=int, default=4)


def _params_de(args: argparse.Namespace) -> ParametrosCadeia:
    """Parâmetros do rastreio a partir das opções da CLI.

    Args:
        args: argumentos já lidos.

    Returns:
        ``ParametrosCadeia`` com os valores dados.
    """
    return ParametrosCadeia(
        passo_s=args.passo,
        folga_px=args.folga,
        folga_recuperacao_px=args.folga_recuperacao,
        min_inliers=args.min_inliers,
        max_reproj_px=args.max_reproj,
        n_orb=args.n_orb,
        salto_vao=args.salto,
        desacordo_vao=args.desacordo,
    )


def main() -> int:
    """Ponto de entrada da CLI.

    Subcomandos: ``dev`` (os 38 pares de desenvolvimento, saída em
    ``MAOS_M11 / "cadeia"``) e ``pares`` (pares dados por arquivo, com índice,
    gabarito, pasta de quadros e arquivo de saída).

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)

    dev = sub.add_parser("dev", help="os 38 pares de desenvolvimento")
    _adicionar_parametros(dev)
    dev.add_argument("--rotulo", default="base")
    dev.add_argument(
        "--desenhar", action="store_true", help="grava as imagens das marcas"
    )

    pares = sub.add_parser("pares", help="pares passados por arquivo")
    _adicionar_parametros(pares)
    pares.add_argument("--indice", type=Path, required=True)
    pares.add_argument("--ouro", type=Path, required=True)
    pares.add_argument(
        "--pares",
        required=True,
        help='JSON [{"chave": "qNN", "alvo": "qNN"}] ou caminho de arquivo com ele',
    )
    pares.add_argument("--pasta-quadros", type=Path, required=True)
    pares.add_argument("--saida", type=Path, required=True)

    args = parser.parse_args()
    params = _params_de(args)
    inicio = time.monotonic()
    if args.comando == "dev":
        pasta_desenhos = None
        if args.desenhar:
            pasta_desenhos = str(MAOS_M11 / "cadeia" / "desenhos")
        tarefas = _tarefas(
            PARES_DESENVOLVIMENTO + PARES_TESTE,
            MAOS_M3B / "indice.json",
            GABARITO_BRACO,
            str(MAOS_M3B_QUADROS),
            params,
            pasta_desenhos,
        )
        saida = MAOS_M11 / "cadeia" / f"dev_{args.rotulo}.json"
    else:
        tarefas = _tarefas(
            _pares_da_entrada(args.pares),
            args.indice,
            args.ouro,
            str(args.pasta_quadros),
            params,
            None,
        )
        saida = args.saida
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        entradas = list(pool.map(_executar, tarefas))
    _imprimir(entradas)
    gravado = _salvar(entradas, params, saida)
    print(f"tempo: {time.monotonic() - inicio:.1f} s", file=sys.stderr)
    print(f"gravado em {gravado}", file=sys.stderr)
    return 0


def _executar(tarefa: dict) -> dict:
    """Desempacota uma tarefa e roda ``_tarefa`` (para o pool de processos).

    Args:
        tarefa: dicionário de ``_tarefas``.

    Returns:
        Entrada do par.
    """
    return _tarefa(**tarefa)


if __name__ == "__main__":
    sys.exit(main())
