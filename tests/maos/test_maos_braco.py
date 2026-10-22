"""Testes da geometria do braço (M3): sintético, sem vídeo, sem GPU."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from tab.maos.braco import braco as mb


def _braco_sintetico(
    cordas: list[tuple[float, float]], x0: float, comprimento: float
) -> np.ndarray:
    """Imagem cinza com cordas (retas claras) e trastes (verticais) no modelo."""
    img = np.full((300, 1000), 30, dtype=np.uint8)
    xs = np.arange(1000)
    for a, b in cordas:
        ys = np.round(a + b * xs).astype(int)
        for dy in (-1, 0, 1):
            img[np.clip(ys + dy, 0, 299), xs] = 170
    for k in range(1, mb.N_TRASTES + 1):
        x = round(x0 - comprimento * (1 - 2.0 ** (-k / 12)))
        if 0 <= x < 1000:
            img[:, x - 1 : x + 2] = 200
    return img


def test_razao_entre_trastes_e_2_elevado_a_menos_um_duodecimo() -> None:
    assert abs(mb.RAZAO_TEORICA - 0.9439) < 1e-4


def test_picos_respeita_minimo_e_distancia() -> None:
    perfil = np.array([0, 5, 0, 9, 0, 0, 0, 7, 0, 0.0])
    assert mb.picos(perfil, minimo=6, distancia=2) == [3, 7]
    assert mb.picos(perfil, minimo=6, distancia=5) == [3]


def test_ajustar_reta_robusta_descarta_ponto_ruim() -> None:
    xs = np.arange(0, 100, 5, dtype=float)
    ys = 10 + 0.5 * xs
    ys[3] += 40
    a, b, rms = mb.ajustar_reta_robusta(xs, ys)
    assert abs(a - 10) < 1e-6
    assert abs(b - 0.5) < 1e-6
    assert rms < 1e-6


def test_achar_cordas_recupera_as_seis_retas_de_cima_para_baixo() -> None:
    cordas = [(100 + 30 * k, 0.01 * (k - 2)) for k in range(6)]
    img = _braco_sintetico(cordas, x0=1900, comprimento=1800)
    achadas = mb.achar_cordas(img, x_ini=100, x_fim=900, y_ini=50, y_fim=280)
    assert len(achadas) == 6
    for achada, (a, b) in zip(achadas, cordas, strict=True):
        assert abs(achada["b"] - b) < 0.005
        assert abs(achada["a"] - a) < 1.5


def test_numerar_cordas_linha_de_baixo_e_a_um() -> None:
    cordas = [{"a": float(k), "b": 0.0, "brilho": 180 - 15 * k} for k in range(6)]
    numeradas = mb.numerar_cordas(cordas)
    assert [c["corda"] for c in numeradas] == [1, 2, 3, 4, 5, 6]
    assert numeradas[0]["a"] == 5.0  # a de baixo, perto da mão, é a 1
    assert numeradas[5]["a"] == 0.0  # a de cima é a 6 (bordão, mais claro)


def test_numerar_cordas_levanta_se_brilho_discorda() -> None:
    cordas = [{"a": float(k), "b": 0.0, "brilho": 60 + 15 * k} for k in range(6)]
    try:
        mb.numerar_cordas(cordas)
    except ValueError as erro:
        assert "discorda" in str(erro)
        return
    raise AssertionError("brilho invertido devia levantar ValueError")


def test_achar_nut_pega_faixa_clara() -> None:
    img = np.full((50, 400), 40, dtype=np.uint8)
    img[:, 200:210] = 240
    assert abs(mb.achar_nut(img, 0, 50, 150, 300) - 204.5) < 1.0


def test_ajustar_escala_recupera_comprimento_e_preve_traste_faltando() -> None:
    x0, L = 1770.0, 1880.0
    det = []
    for k in range(1, 15):
        if k == 5:
            continue  # traste não detectado: tem que sair como previsto
        x = x0 - L * (1 - 2.0 ** (-k / 12))
        det.append(x)
    escala = mb.ajustar_escala(x0, det)
    assert abs(escala["L"] - L) < 15
    assert escala["trastes"][5]["origem"] == "previsto"
    assert escala["trastes"][4]["origem"] == "detectado"
    assert abs(escala["razao_mediana"] - mb.RAZAO_TEORICA) < 1e-6


def test_x_da_pisada_fica_a_setenta_por_cento_do_caminho() -> None:
    trastes = {0: {"x": 1000.0}, 1: {"x": 900.0}, 2: {"x": 820.0}}
    assert abs(mb.x_da_pisada(1, trastes) - 930.0) < 1e-9
    assert abs(mb.x_da_pisada(2, trastes) - 844.0) < 1e-9


def test_alvo_da_nota_usa_a_reta_da_corda() -> None:
    cordas = {2: {"a": 300.0, "b": -0.01}}
    trastes = {0: {"x": 1000.0}, 1: {"x": 900.0}}
    x, y = mb.alvo_da_nota(2, 1, cordas, trastes)
    assert abs(x - 930.0) < 1e-9
    assert abs(y - (300.0 - 0.01 * 930.0)) < 1e-9


def test_corda_solta_nao_tem_alvo() -> None:
    try:
        mb.x_da_pisada(0, {0: {"x": 1000.0}})
    except ValueError:
        return
    raise AssertionError("casa 0 devia levantar ValueError")


def test_meia_largura_casa() -> None:
    trastes = {0: {"x": 1000.0}, 1: {"x": 900.0}}
    assert mb.meia_largura_casa(1, trastes) == 50.0


def test_dedo_mais_perto_devolve_dedo_e_segunda_distancia() -> None:
    pontas = {1: (10.0, 0.0), 2: (0.0, 3.0), 3: (100.0, 0.0), 4: (0.0, 50.0)}
    dedo, dist, segunda = mb.dedo_mais_perto((0.0, 0.0), pontas)
    assert dedo == "2"
    assert abs(dist - 3.0) < 1e-9
    assert abs(segunda - 10.0) < 1e-9


def test_dedo_mais_perto_sem_pontas_levanta() -> None:
    try:
        mb.dedo_mais_perto((0.0, 0.0), {})
    except ValueError:
        return
    raise AssertionError("sem pontas devia levantar ValueError")


def test_votar_maioria_empate_e_vazio() -> None:
    assert mb.votar(["1", "2", "2"], padrao="3") == "2"
    assert mb.votar(["1", "2", None], padrao="3") == "3"
    assert mb.votar([None, None], padrao="4") == "4"
    assert mb.votar(["1", "1", None], padrao="4") == "1"


def test_escolher_mao_esquerda_so_na_camera_do_braco() -> None:
    fora = {"lado": "esquerda", "caixa": [0, 700, 300, 1000], "origem": "x", "pts": []}
    dentro_pequena = {
        "lado": "esquerda",
        "caixa": [1600, 800, 1700, 900],
        "origem": "x",
        "pts": [],
    }
    dentro_grande = {
        "lado": "esquerda",
        "caixa": [1550, 760, 1850, 1050],
        "origem": "y",
        "pts": [],
    }
    direita = {
        "lado": "direita",
        "caixa": [1600, 800, 1900, 1050],
        "origem": "x",
        "pts": [],
    }
    escolhida = mb.escolher_mao_esquerda([fora, dentro_pequena, dentro_grande, direita])
    assert escolhida is dentro_grande
    assert mb.escolher_mao_esquerda([fora, direita]) is None


def test_pontas_da_mao_usam_indicador_medio_anelar_minimo() -> None:
    pts = [[float(i), float(2 * i)] for i in range(21)]
    pontas = mb.pontas_da_mao({"pts": pts})
    assert pontas == {1: (8.0, 16.0), 2: (12.0, 24.0), 3: (16.0, 32.0), 4: (20.0, 40.0)}


def test_modulo_geometrico_nao_importa_detector() -> None:
    fonte = Path(mb.__file__).read_text(encoding="utf-8")
    importados = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Import):
            importados |= {a.name.split(".")[0] for a in no.names}
        if isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module.split(".")[0])
    assert not importados & {"cv2", "mediapipe", "rtmlib", "torch"}
