"""`cursor.rastrear` pelo leitor único: x e t de uma faixa sintética em x conhecido."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from tab.tablatura.leitura.cursor import rastrear

FPS = 10
LARGURA, ALTURA = 400, 120
# (segundo, x do centro): a faixa fica parada em cada x por 1 s, como o cursor real.
POSICOES = [(0, 60), (1, 120), (2, 200), (3, 300)]


def _gerar_video(caminho: Path) -> None:
    """Grava 4 s de fundo branco com uma faixa azul saturada, estreita e de altura total."""
    escritor = cv2.VideoWriter(
        str(caminho), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (LARGURA, ALTURA)
    )
    assert escritor.isOpened()
    for i in range(4 * FPS):
        quadro = np.full((ALTURA, LARGURA, 3), 255, np.uint8)
        x = POSICOES[i // FPS][1]
        quadro[:, x - 4 : x + 5] = (255, 0, 0)  # BGR: azul saturado
        escritor.write(quadro)
    escritor.release()


def test_rastrear_acha_faixa_em_x_e_t_conhecidos(tmp_path: Path) -> None:
    """A faixa é achada no x certo e no instante certo (em segundos)."""
    video = tmp_path / "faixa.mp4"
    _gerar_video(video)
    r = rastrear(str(video), roi=(10, 110), passo=2)
    assert "erro" not in r["resumo"]
    amostras = r["amostras"]
    assert len(amostras) >= 15
    for a in amostras:
        esperado = POSICOES[min(3, int(a["t"] + 1e-6))][1]
        # tolerância de 1 quadro de amostragem na borda e 3 px no x (codec com perdas)
        if abs(a["t"] - round(a["t"])) > 0.15:
            assert a["x"] == pytest.approx(esperado, abs=3)
        assert a["frame"] == round(a["t"] * r["resumo"]["fps"])
    assert r["resumo"]["fps"] == pytest.approx(FPS)
    assert r["resumo"]["x_min"] == pytest.approx(60, abs=3)
    assert r["resumo"]["x_max"] == pytest.approx(300, abs=3)
    # `passo` em quadros: qps = fps / passo = 5 amostras por segundo
    assert amostras[1]["t"] - amostras[0]["t"] == pytest.approx(0.2, abs=1e-6)


def test_rastrear_video_ilegivel_declara_erro(tmp_path: Path) -> None:
    """Vídeo que não abre vira `erro` no resumo, não 0 amostras sem motivo."""
    lixo = tmp_path / "lixo.mp4"
    lixo.write_bytes(b"nao e video")
    r = rastrear(str(lixo), roi=(0, 50), passo=1)
    assert r["amostras"] == []
    assert r["resumo"]["erro"]
