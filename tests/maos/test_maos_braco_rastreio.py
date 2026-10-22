"""Rastreio do braço (M11a): máscara, homografia e determinismo, sintéticos."""

from __future__ import annotations

import cv2
import numpy as np

from tab.maos.braco.rastreio import Parametros, mascara_do_braco, rastrear
from tab.maos.braco.tempo import Marcas, classificar, erros, transformar

ALTURA, LARGURA = 400, 800
DESLOCAMENTO = 30.0
#: AKAZE não existe no OpenCV desta imagem; os testes usam o ORB.
ORB = Parametros(detector="orb")


def _marcas_sinteticas() -> Marcas:
    """Quadro-chave sintético: braço horizontal, nut em x = 650, trastes a cada 50 px.

    As cordas 1 e 6 estão em y = 150 e y = 250 (vão = 100 / 5 = 20 px).
    """
    trastes = {n: np.array([650.0 - 50.0 * n, 200.0]) for n in range(1, 7)}
    return Marcas(
        nut=np.array([650.0, 200.0]),
        trastes=trastes,
        corda1=np.array([[100.0, 150.0], [700.0, 150.0]]),
        corda6=np.array([[100.0, 250.0], [700.0, 250.0]]),
    )


def _textura(semente: int = 0) -> np.ndarray:
    """Textura cinza com semente fixa: ruído suavizado e retângulos aleatórios.

    Args:
        semente: semente do gerador de números aleatórios.

    Returns:
        Imagem BGR uint8 ``(ALTURA, LARGURA, 3)``.
    """
    rng = np.random.default_rng(semente)
    img = rng.integers(0, 256, (ALTURA, LARGURA)).astype(np.uint8)
    img = cv2.GaussianBlur(img, (0, 0), 1.5)
    for _ in range(60):
        x, y = rng.integers(0, LARGURA - 40), rng.integers(0, ALTURA - 40)
        cor = int(rng.integers(0, 256))
        cv2.rectangle(img, (int(x), int(y)), (int(x) + 30, int(y) + 25), cor, -1)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def test_mascara_entre_cordas_e_zero_longe():
    """Pixel entre as cordas 1 e 6 cai na máscara; pixel longe dela, não."""
    mascara = mascara_do_braco(_marcas_sinteticas(), (ALTURA, LARGURA))
    assert mascara.dtype == np.uint8
    assert set(np.unique(mascara)) <= {0, 255}
    assert mascara[200, 500] == 255
    assert mascara[50, 500] == 0


def test_rastreio_recupera_translacao_e_marcas_certas():
    """Alvo transladado 30 px: o rastreio acha, e a previsão sai certa."""
    marcas = _marcas_sinteticas()
    img = _textura()
    translacao = np.array([[1.0, 0.0, DESLOCAMENTO], [0.0, 1.0, 0.0]])
    alvo = cv2.warpAffine(img, translacao, (LARGURA, ALTURA))
    marcas_alvo = transformar(marcas, np.vstack([translacao, [0.0, 0.0, 1.0]]))

    h, info = rastrear(img, marcas, alvo, ORB)

    assert h is not None, info
    assert info["motivo"] == "achou"
    ponto = cv2.perspectiveTransform(np.array([[[300.0, 200.0]]]), h)[0, 0]
    assert np.linalg.norm(ponto - np.array([300.0 + DESLOCAMENTO, 200.0])) < 1.0
    e = erros(transformar(marcas, h), marcas_alvo)
    assert classificar(e, True, "sim") == "certo"


def test_alvo_uniforme_nao_acha():
    """Alvo preto não tem pontos suficientes: devolve None com motivo."""
    img = _textura()
    alvo = np.zeros((ALTURA, LARGURA, 3), dtype=np.uint8)
    h, info = rastrear(img, _marcas_sinteticas(), alvo, ORB)
    assert h is None
    assert info["motivo"] not in (None, "achou")


def test_rastreio_e_determinista():
    """Duas chamadas com os mesmos dados dão a mesma homografia."""
    marcas = _marcas_sinteticas()
    img = _textura()
    translacao = np.array([[1.0, 0.0, DESLOCAMENTO], [0.0, 1.0, 0.0]])
    alvo = cv2.warpAffine(img, translacao, (LARGURA, ALTURA))
    h1, _ = rastrear(img, marcas, alvo, ORB)
    h2, _ = rastrear(img, marcas, alvo, ORB)
    assert h1 is not None
    assert np.array_equal(h1, h2)
