"""Cortes de câmera (medida 1009-b): distâncias, máscara e sorteio, sem acervo."""

from __future__ import annotations

import shutil
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from tab.maos_cortes import (
    ALTURA_ANALISE,
    LARGURA_ANALISE,
    assinatura,
    cortes,
    mascara_da_tablatura,
    medir_video,
    pares_consecutivos,
    sortear,
)


def _quadro(cor: tuple[int, int, int]) -> np.ndarray:
    """Quadro sólido na resolução da análise, em BGR."""
    return np.full((ALTURA_ANALISE, LARGURA_ANALISE, 3), cor, dtype=np.uint8)


def test_corte_de_cor_so_no_quadro_certo():
    """Quadros iguais não dão corte; a troca de cor dá um corte, no instante certo."""
    mascara = np.full((ALTURA_ANALISE, LARGURA_ANALISE), 255, dtype=np.uint8)
    vermelho, azul = (0, 0, 200), (200, 0, 0)
    quadros = [
        assinatura(_quadro(vermelho), t, mascara) for t in (0.0, 1.0, 2.0, 3.0)
    ] + [assinatura(_quadro(azul), t, mascara) for t in (4.0, 5.0, 6.0)]

    pares = pares_consecutivos(quadros)

    achados = cortes(pares, 0.3)
    assert [(p.t_a, p.t_b) for p in achados] == [(3.0, 4.0)]
    iguais = [p for p in pares if p.i != 3]
    assert all(p.bhattacharyya == pytest.approx(0.0, abs=1e-6) for p in iguais)
    assert all(p.mad == 0.0 for p in iguais)


def test_mudanca_so_dentro_da_tablatura_nao_conta():
    """Uma mudança que cai só na caixa da tablatura não é corte; fora dela, é."""
    largura, altura = 1920, 1080
    # Caixa do censo em pixels do vídeo; em 192x108 vira x 48..144 e y 54..108.
    rects = [[480, 540, 1440, 1080]]
    mascara = mascara_da_tablatura(rects, largura, altura)
    base = _quadro((90, 90, 90))
    com_tablatura = base.copy()
    com_tablatura[54:108, 48:144] = (0, 200, 255)

    quadros = [
        assinatura(base, 0.0, mascara),
        assinatura(com_tablatura, 1.0, mascara),
        assinatura(base, 2.0, mascara),
    ]
    assert cortes(pares_consecutivos(quadros), 0.3) == []

    # Controle: sem máscara, a mesma mudança (um quarto do quadro) passa do limiar.
    sem_mascara = np.full((ALTURA_ANALISE, LARGURA_ANALISE), 255, dtype=np.uint8)
    controle = [
        assinatura(base, 0.0, sem_mascara),
        assinatura(com_tablatura, 1.0, sem_mascara),
    ]
    assert len(cortes(pares_consecutivos(controle), 0.3)) == 1


def test_sorteio_e_deterministico_e_respeita_o_limite_por_canal():
    """Mesma semente, mesma amostra; canal pequeno entra inteiro."""
    contagens = {"alfa": 10, "beta": 2, "gama": 7, "delta": 3}
    linhas = [
        {"canal": canal, "arquivo": f"{canal}/{n:03d}.mp4"}
        for canal, total in contagens.items()
        for n in range(total)
    ]

    primeira = sortear(linhas, semente=20261017, por_canal=3)
    segunda = sortear(linhas, semente=20261017, por_canal=3)

    assert primeira == segunda
    assert Counter(linha["canal"] for linha in primeira) == {
        "alfa": 3,
        "beta": 2,
        "gama": 3,
        "delta": 3,
    }
    assert all(linha["arquivo"].startswith(linha["canal"] + "/") for linha in primeira)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="precisa do ffmpeg")
def test_video_sintetico_tem_corte_no_quadro_chave(tmp_path: Path):
    """Ponta a ponta: um vídeo de 2 s vermelho + 2 s azul, com quadro-chave no corte."""
    video = tmp_path / "corte.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x240:d=2:r=25",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x240:d=2:r=25",
            "-filter_complex",
            "[0][1]concat=n=2:v=1:a=0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "250",
            "-force_key_frames",
            "2",
            str(video),
        ],
        check=True,
    )
    linha = {
        "arquivo": video.name,
        "canal": "sintetico",
        "largura": 320,
        "altura": 240,
        "quadros": [{"t": 0.0, "tab": False, "rect": None}],
    }

    estatisticas, pares = medir_video(linha, tmp_path)

    assert estatisticas["erro"] is None
    assert estatisticas["quadros_chave"] == 2
    achados = cortes(pares, 0.3)
    assert len(achados) == 1
    assert achados[0].t_a == pytest.approx(0.0)
    assert achados[0].t_b == pytest.approx(2.0)
