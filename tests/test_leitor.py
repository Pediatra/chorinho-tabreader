"""Testes do leitor de vídeo (`tab/leitor.py`): mapeamento tempo→quadro, `info` e AV1 real.

Os testes sintéticos geram o vídeo no `tmp_path` (sem GPU e sem acervo). O teste de AV1 é
marcado `integration` e é pulado se o acervo não estiver montado.
"""

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from tab.caminhos import acervo
from tab.estado import ler_amostras
from tab.leitor import info, quadro_em, quadros, quadros_pts

FPS = 10.0
LARGURA = 160
ALTURA = 90
N_QUADROS = 25  # 2,5 s a 10 fps
BARRA_LARGURA = 4
PASSO = 10  # a barra anda 10 px por quadro
# x = 10·(k mod 15): a barra volta ao início antes de sair da tela de 160 px
PERIODO = 15
# tolerância de posição: só é erro se a barra cair no quadro vizinho
METADE_PASSO = PASSO / 2


def _x_esperado(k: int) -> int:
    """Posição esquerda da barra no quadro de índice ``k``.

    Args:
        k: índice do quadro (0 é o primeiro).

    Returns:
        A coluna em que a barra começa, em px.
    """
    return PASSO * (k % PERIODO)


def _centro_da_barra(quadro: np.ndarray) -> float:
    """Centro horizontal da faixa branca, pela média das colunas do canal verde.

    Args:
        quadro: quadro BGR com uma barra branca sobre fundo preto.

    Returns:
        A coluna central da barra, em px (com frações).
    """
    brilho = quadro[:, :, 1].astype(float).mean(axis=0)
    assert brilho.max() > 128, "nenhuma barra branca no quadro"
    pesos = np.where(brilho >= brilho.max() * 0.5, brilho, 0.0)
    colunas = np.arange(brilho.size)
    return float((colunas * pesos).sum() / pesos.sum())


def _centro_esperado(k: int) -> float:
    """Centro horizontal esperado da barra no quadro ``k``.

    Args:
        k: índice do quadro.

    Returns:
        Coluna central prevista, em px.
    """
    return _x_esperado(k) + (BARRA_LARGURA - 1) / 2


def _gravar_video_de_barra(caminho: Path) -> Path:
    """Grava um vídeo mp4v em que o quadro ``k`` tem a barra branca em ``x = 10·k``.

    Args:
        caminho: arquivo de saída (``.mp4``).

    Returns:
        O próprio ``caminho``, já gravado.
    """
    escritor = cv2.VideoWriter(
        str(caminho), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (LARGURA, ALTURA)
    )
    assert escritor.isOpened(), "cv2.VideoWriter não abriu o arquivo"
    for k in range(N_QUADROS):
        quadro = np.zeros((ALTURA, LARGURA, 3), np.uint8)
        x = _x_esperado(k)
        quadro[:, x : x + BARRA_LARGURA] = 255
        escritor.write(quadro)
    escritor.release()
    assert caminho.stat().st_size > 0
    return caminho


@pytest.fixture
def video_barra(tmp_path: Path) -> str:
    """Vídeo sintético de 2,5 s com a barra branca andando um passo por quadro.

    Args:
        tmp_path: diretório temporário do teste.

    Returns:
        Caminho do vídeo, como texto.
    """
    return str(_gravar_video_de_barra(tmp_path / "barra.mp4"))


def test_quadros_mapeia_tempo_em_quadro(video_barra: str) -> None:
    """Cada ``(t, quadro)`` de ``quadros`` tem a barra onde o tempo ``t`` prevê.

    Args:
        video_barra: vídeo sintético com a barra andando.
    """
    lidos = list(quadros(video_barra, 0.0, N_QUADROS / FPS, FPS))
    assert len(lidos) == N_QUADROS
    for t, quadro in lidos:
        k = round(t * FPS)
        assert abs(t - k / FPS) < 1e-9, f"instante {t} não cai num quadro"
        centro = _centro_da_barra(quadro)
        assert abs(centro - _centro_esperado(k)) <= METADE_PASSO, (
            f"t={t:.2f}s (quadro {k}): centro {centro:.1f}, "
            f"esperado {_centro_esperado(k):.1f}"
        )


def test_quadro_em_devolve_o_quadro_do_instante(video_barra: str) -> None:
    """``quadro_em`` devolve o quadro certo para instantes diferentes.

    Args:
        video_barra: vídeo sintético com a barra andando.
    """
    for t in (0.5, 1.2, 2.0):
        k = round(t * FPS)
        quadro = quadro_em(video_barra, t)
        assert quadro is not None, f"quadro_em não devolveu quadro em t={t}"
        assert quadro.shape == (ALTURA, LARGURA, 3)
        centro = _centro_da_barra(quadro)
        assert abs(centro - _centro_esperado(k)) <= METADE_PASSO, (
            f"t={t}s (quadro {k}): centro {centro:.1f}, "
            f"esperado {_centro_esperado(k):.1f}"
        )


def test_info_devolve_duracao_e_dimensoes(video_barra: str) -> None:
    """``info`` traz largura, altura, fps e duração dentro de 1 quadro.

    Args:
        video_barra: vídeo sintético com a barra andando.
    """
    dados = info(video_barra)
    assert dados["largura"] == LARGURA
    assert dados["altura"] == ALTURA
    assert dados["fps"] == pytest.approx(FPS, abs=0.01)
    assert dados["codec"] == "mpeg4"
    assert abs(dados["duracao_s"] - N_QUADROS / FPS) <= 1 / FPS


@pytest.mark.integration
def test_quadros_le_av1_real() -> None:
    """Um AV1 real do acervo (o `mr. tabs`, §2.4 do plano) rende quadros numa janela de 2 s."""
    caminho = (
        acervo()
        / "mr. tabs"
        / "blind melon - no rain - guitar tab ｜ lesson ｜ cover ｜ tutorial ｜ lead only.mp4"
    )
    if not caminho.exists():
        pytest.skip(f"acervo ausente: {caminho}")
    lidos = list(quadros(str(caminho), 0.0, 2.0, 6.0))
    assert len(lidos) > 0


def test_recorte_de_altura_impar_bate_com_seek(tmp_path: Path) -> None:
    """Recorte com y0 e altura ímpares, em yuv420: cada quadro de ``quadros`` = ``quadro_em``.

    Regressão da Fase 5: o crop em yuv420p saía com uma linha a menos e o ``read`` desalinhava
    os quadros seguintes (o erro crescia a cada quadro). Com ``format=bgr24`` antes do crop, o
    quadro lido é o mesmo do seek exato.
    """
    caminho = tmp_path / "yuv.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x240:rate=10",
            "-t",
            "2",
            "-c:v",
            "mpeg4",
            "-pix_fmt",
            "yuv420p",
            str(caminho),
        ],
        check=True,
    )
    y0, altura = 13, 37  # ímpares: o caso que quebrava
    lidos = list(quadros(str(caminho), 0.0, 2.0, 6.0, recorte_y=(y0, y0 + altura)))
    assert len(lidos) >= 10
    for t, quadro in lidos[:10]:
        assert quadro.shape == (altura, 320, 3)
        seek = quadro_em(str(caminho), t)
        assert seek is not None
        dif = np.abs(
            seek[y0 : y0 + altura].astype(np.float32) - quadro.astype(np.float32)
        )
        assert dif.mean() < 0.5, (
            f"quadro em t={t:.3f} desalinhado (dif {dif.mean():.2f})"
        )


def test_quadros_pts_rotula_com_o_pts_do_quadro_lido(video_barra: str) -> None:
    """``quadros_pts`` rotula cada quadro com o PTS do quadro que foi lido (não com a grade).

    Regressão da Fase 6: a grade ``t0 + k/qps`` começava fora do quadro (t0 = 0,03 s, quadros em
    0,1 s) e o tempo ficava 2 a 3 quadros adiantado. Aqui o instante da grade (0,03; 0,13; ...)
    cai no quadro nativo mais próximo, e o rótulo é o PTS dele: a barra lida é a do próprio
    quadro rotulado.
    """
    lidos = list(quadros_pts(video_barra, 0.03, 2.0, FPS))
    assert len(lidos) >= 15
    for t, quadro in lidos:
        k = round(t * FPS)
        assert abs(t * FPS - k) < 1e-6, f"rótulo {t} não é um PTS de quadro"
        assert abs(_centro_da_barra(quadro) - _centro_esperado(k)) < METADE_PASSO
    tempos = [t for t, _ in lidos]
    assert tempos == sorted(set(tempos)), (
        "um quadro nativo não pode aparecer duas vezes"
    )


def test_quadros_pts_nao_repete_quadro_quando_qps_e_menor_que_o_nativo(
    video_barra: str,
) -> None:
    """Com 6 qps num vídeo de 10 fps, cada instante da grade pega um quadro distinto e em ordem."""
    lidos = list(quadros_pts(video_barra, 0.0, 2.0, 6.0))
    tempos = [t for t, _ in lidos]
    assert tempos == sorted(set(tempos))
    assert len(tempos) == len(set(tempos)) > 0
    for t, quadro in lidos:
        k = round(t * FPS)
        assert abs(_centro_da_barra(quadro) - _centro_esperado(k)) < METADE_PASSO


def test_amostras_do_tempo_herdam_o_pts_do_quadro(video_barra: str) -> None:
    """``ler_amostras`` (o caminho do tempo, ``tab.estado``) rotula com o PTS do quadro nativo."""
    amostras = ler_amostras(video_barra, 0.03, 2.0, 6.0, (0, ALTURA), [[]])
    assert amostras
    for a in amostras:
        assert abs(a.t * FPS - round(a.t * FPS)) < 1e-6
