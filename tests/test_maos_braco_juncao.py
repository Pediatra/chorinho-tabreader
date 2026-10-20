"""Testes da junção do braço com o corpo (método J), com dados sintéticos."""

import numpy as np

from tab.maos_braco_juncao import (
    CONTRASTE_MINIMO,
    SEGMENTO_MINIMO,
    achar_juncao,
    numero_do_video,
    ponto_de_mudanca,
)

COR_CORPO = (200, 180, 120)
COR_FUNDO = 40
TRASTES = 18


def _xs_trastes() -> dict[int, float]:
    """Posição x de cada traste 1..18 no quadro sintético.

    Returns:
        Dicionário ``{número: x}`` com o espaçamento de equal temperamento.
    """
    base = 1.0 - 2.0 ** (-TRASTES / 12)
    return {
        n: 100.0 + 1100.0 * (1.0 - 2.0 ** (-n / 12)) / base * 0.95
        for n in range(1, TRASTES + 1)
    }


def _quadro_com_corpo(inicio_corpo: int) -> tuple[np.ndarray, dict]:
    """Monta um quadro 720x1280 com braço horizontal e corpo a partir de um traste.

    Args:
        inicio_corpo: número do traste a partir do qual a cor do corpo aparece.

    Returns:
        ``(imagem, previsto)``: quadro BGR e previsão no formato dos registros densos.
    """
    imagem = np.full((720, 1280, 3), COR_FUNDO, dtype=np.uint8)
    x_corpo = round(_xs_trastes()[inicio_corpo])
    imagem[:325, x_corpo:] = COR_CORPO
    imagem[396:, x_corpo:] = COR_CORPO
    trastes = [{"numero": n, "ponto": [x, 360.0]} for n, x in _xs_trastes().items()]
    previsto = {
        "achou": True,
        "sinalizado": False,
        "nut": [100.0, 360.0],
        "corda1": [[100.0, 330.0], [1200.0, 330.0]],
        "corda6": [[100.0, 390.0], [1200.0, 390.0]],
        "trastes": trastes,
    }
    return imagem, previsto


def test_ponto_de_mudanca_acha_degrau():
    """Degrau de 0 para 50 em 300 colunas é achado a até 2 colunas, com contraste."""
    rng = np.random.default_rng(1)
    sinal = np.zeros((600, 6))
    sinal[300:] = 50.0
    sinal += rng.normal(0.0, 1.0, size=sinal.shape)
    corte = ponto_de_mudanca(sinal, 0, 600)
    assert corte is not None
    coluna, contraste = corte
    assert abs(coluna - 300) <= 2
    assert contraste >= CONTRASTE_MINIMO


def test_ponto_de_mudanca_sem_degrau_tem_contraste_baixo():
    """Sinal constante com ruído não tem mudança: o contraste fica abaixo do mínimo."""
    rng = np.random.default_rng(2)
    sinal = rng.normal(0.0, 1.0, size=(600, 6))
    corte = ponto_de_mudanca(sinal, 0, 600)
    assert corte is not None
    _, contraste = corte
    assert contraste < CONTRASTE_MINIMO


def test_ponto_de_mudanca_janela_curta_devolve_none():
    """Janela menor que dois segmentos mínimos não tem corte."""
    sinal = np.zeros((2 * SEGMENTO_MINIMO - 1, 6))
    assert ponto_de_mudanca(sinal, 0, 2 * SEGMENTO_MINIMO - 1) is None


def test_numero_do_video_moda_de_nut_aceita():
    """Moda 12 em 8 de 10 quadros com nut vale 12, pela fonte nut."""
    saida = numero_do_video([12] * 8 + [13] * 2, [])
    assert saida["numero"] == 12
    assert saida["fonte"] == "nut"


def test_numero_do_video_concordancia_abaixo_de_70_por_cento():
    """Moda 12 em 60 % dos quadros com nut não decide."""
    saida = numero_do_video([12] * 6 + [13] * 4, [])
    assert saida["numero"] is None
    assert saida["fonte"] == "nut"


def test_numero_do_video_moda_fora_de_12_e_14_nao_decide():
    """Moda 13, mesmo unânime, não é número de junção aceito."""
    saida = numero_do_video([13] * 10, [])
    assert saida["numero"] is None


def test_numero_do_video_contagem_nylon():
    """Sem nut, a contagem 18 (moda) dá junção 12, pela fonte contagem."""
    saida = numero_do_video([], [18, 18, 19])
    assert saida["numero"] == 12
    assert saida["fonte"] == "contagem"


def test_numero_do_video_contagem_aco():
    """Sem nut, a contagem 21 dá junção 14."""
    saida = numero_do_video([], [21, 21])
    assert saida["numero"] == 14


def test_numero_do_video_contagem_no_meio_nao_decide():
    """Sem nut, a contagem 19 (moda) não decide entre 12 e 14."""
    saida = numero_do_video([], [19, 20, 19])
    assert saida["numero"] is None


def test_numero_do_video_sem_dados_devolve_none():
    """Sem quadro com nut e sem contagens, o número é None."""
    saida = numero_do_video([], [])
    assert saida["numero"] is None
    assert saida["fonte"] == "nenhuma"


def test_achar_juncao_acha_corpo_no_traste_12():
    """Corpo a partir do traste 12 é achado como junção 12, com contraste."""
    imagem, previsto = _quadro_com_corpo(12)
    achado = achar_juncao(imagem, previsto)
    assert achado is not None
    assert achado["numero"] == 12
    assert achado["contraste"] >= CONTRASTE_MINIMO


def test_achar_juncao_acha_corpo_no_traste_14():
    """Corpo a partir do traste 14 é achado como junção 14, com contraste."""
    imagem, previsto = _quadro_com_corpo(14)
    achado = achar_juncao(imagem, previsto)
    assert achado is not None
    assert achado["numero"] == 14
    assert achado["contraste"] >= CONTRASTE_MINIMO
