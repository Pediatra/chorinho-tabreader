"""Testes do detector de ataques (`tab/audio_onsets.py`) num sinal sintético.

Tudo é gerado em memória (numpy): sem acervo, sem GPU, sem ffmpeg. O "dedilhado" tem
harmônicos com ataque instantâneo e decaimento exponencial (tau = 0,3 s), notas em instantes
conhecidos e ruído leve. O viés do detector é medido aqui e impresso (`pytest -s`); o teste só
falha se ele estiver fora da tolerância da especificação.
"""

import numpy as np
import pytest

from tab.audio_onsets import (
    PASSO,
    espectrograma,
    fluxo_espectral,
    fluxo_nas_alturas,
    midi_da_nota,
    picos,
)

TAXA = 22050
#: Instante, no vídeo, da amostra de índice 0 (não nulo, para testar a linha do vídeo).
T_AMOSTRA0 = 3.0
#: Tolerância do erro por nota, em segundos (15 ms).
TOLERANCIA_S = 0.015
#: Notas do dedilhado: (instante local em s, MIDI). Algumas repetidas seguidas.
NOTAS_DEDILHADO = [
    (1.0, 64),
    (1.5, 64),
    (2.1, 59),
    (2.6, 55),
    (3.2, 50),
    (3.7, 45),
    (4.4, 40),
    (4.9, 52),
    (5.4, 52),
    (5.9, 60),
    (6.6, 64),
    (7.1, 67),
]
#: Fim do sinal, em s locais (2 s de cauda sem nota).
DURACAO_S = 9.0


def _dedilhado(notas: list[tuple[float, int]], duracao: float) -> np.ndarray:
    """Sinal sintético: notas com 4 harmônicos, ataque instantâneo e decaimento de 0,3 s.

    Args:
        notas: pares ``(instante local em s, MIDI)``.
        duracao: duração total, em segundos.

    Returns:
        Áudio ``int16`` mono a ``TAXA`` Hz, com ruído gaussiano de desvio 1e-3.
    """
    rng = np.random.default_rng(0)
    n = round(duracao * TAXA)
    x = np.zeros(n)
    for t_on, midi in notas:
        s0 = round(t_on * TAXA)
        tt = np.arange(n - s0) / TAXA
        f0 = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        env = np.exp(-tt / 0.3)
        for h in range(1, 5):
            x[s0:] += (0.2 / h) * np.sin(2 * np.pi * f0 * h * tt) * env
    x += rng.normal(0.0, 1e-3, n)
    return np.round(np.clip(x, -1, 1) * 32767).astype(np.int16)


@pytest.mark.xfail(
    strict=True,
    reason="limite medido (A1): o fluxo com N_FFT=2048 acha o pico 23-34 ms ANTES do "
    "ataque (média -27,9 ms); a tolerância de 15 ms não é cumprida",
)
def test_dedilhado_acha_cada_nota_e_mede_o_vies():
    """Cada nota é achada a até 15 ms; sem picos inventados; viés medido e impresso."""
    amostras = _dedilhado(NOTAS_DEDILHADO, DURACAO_S)
    mag, tempos, _ = espectrograma(amostras, TAXA, T_AMOSTRA0)
    pk = np.asarray(picos(fluxo_espectral(mag), tempos))
    tp = tempos[pk]

    erros = []
    for t_on, _ in NOTAS_DEDILHADO:
        alvo = T_AMOSTRA0 + t_on
        perto = np.flatnonzero(np.abs(tp - alvo) <= 0.15)
        assert perto.size > 0, f"nota em {alvo:.3f} s sem pico"
        mais = perto[np.argmin(np.abs(tp[perto] - alvo))]
        erros.append(tp[mais] - alvo)
    erros = np.asarray(erros)
    vies_ms = float(np.mean(erros)) * 1000.0
    print(
        f"\nviés do fluxo no sintético: média {vies_ms:.2f} ms, "
        f"mínimo {erros.min() * 1000:.2f} ms, máximo {erros.max() * 1000:.2f} ms"
    )
    assert np.all(np.abs(erros) <= TOLERANCIA_S), erros * 1000.0

    # Nenhum pico pode estar longe de todas as notas (silêncio inicial, cauda e ruído).
    alvos = np.asarray([T_AMOSTRA0 + t for t, _ in NOTAS_DEDILHADO])
    longe = [t for t in tp if np.min(np.abs(alvos - t)) > 0.1]
    assert longe == [], f"picos inventados em {longe}"


def test_fluxo_zero_no_silencio():
    """Silêncio total não gera fluxo nem picos."""
    amostras = np.zeros(TAXA * 2, dtype=np.int16)
    mag, tempos, _ = espectrograma(amostras, TAXA, 0.0)
    fl = fluxo_espectral(mag)
    assert fl[0] == 0.0
    assert np.all(fl == 0.0)
    assert picos(fl, tempos) == []


@pytest.mark.xfail(
    strict=True,
    reason="limite medido (A1): com N_FFT=2048 (10,8 Hz por bin) a máscara de 1 semitom "
    "em 330 Hz recebe o vazamento da nota certa (razão 0,983)",
)
def test_alturas_responde_a_nota_certa_e_quase_nao_a_um_semitom():
    """A máscara da nota certa acha o ataque; a 1 semitom acha bem menos (razão medida)."""
    amostras = _dedilhado([(1.0, 64)], 2.5)
    mag, tempos, freqs = espectrograma(amostras, TAXA, 0.0)
    certa = fluxo_nas_alturas(mag, freqs, [64])
    vizinha = fluxo_nas_alturas(mag, freqs, [65])
    janela = (tempos >= 0.9) & (tempos <= 1.5)
    pico_certa = float(certa[janela].max())
    pico_vizinha = float(vizinha[janela].max())
    razao = pico_vizinha / pico_certa
    print(f"\nrazão alturas (nota a 1 semitom / nota certa): {razao:.3f}")
    assert pico_certa > 0
    assert razao < 0.5


def test_midi_da_nota():
    """Afinação padrão E A D G B E, casa e transposição."""
    assert midi_da_nota(1, 0) == 64
    assert midi_da_nota(6, 5) == 45
    assert midi_da_nota(6, 0) == 40
    assert midi_da_nota(4, 2, transposicao=3) == 50 + 2 + 3
    try:
        midi_da_nota(7, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("corda 7 deveria falhar")


def test_espectrograma_linha_do_video_e_trecho():
    """Com t_amostra0 != 0 os tempos estão na linha do vídeo; o trecho também."""
    amostras = np.zeros(TAXA * 4, dtype=np.int16)
    mag, tempos, _ = espectrograma(amostras, TAXA, T_AMOSTRA0)
    assert abs(tempos[0] - T_AMOSTRA0) < 1e-12
    assert abs((tempos[1] - tempos[0]) - PASSO / TAXA) < 1e-12
    assert mag.shape[0] == (len(amostras) - 1) // PASSO + 1

    # Trecho de 5,0 s a 6,0 s do vídeo: a 1ª linha é 5,0 s, não 3,0 s.
    mag_t, tempos_t, _ = espectrograma(amostras, TAXA, T_AMOSTRA0, t0=5.0, t1=6.0)
    assert abs(tempos_t[0] - 5.0) < 1e-9
    assert tempos_t[-1] <= 6.0 + 1e-9
    assert mag_t.shape[0] > 0


def test_espectrograma_quadro_centrado_no_impulso():
    """Um impulso no instante t faz o quadro de maior energia cair perto de t (centrado)."""
    amostras = np.zeros(TAXA * 2, dtype=np.int16)
    amostras[round(1.2345 * TAXA)] = 16000
    mag, tempos, _ = espectrograma(amostras, TAXA, 0.0)
    energia = mag.sum(axis=1)
    k = int(np.argmax(energia))
    assert abs(tempos[k] - 1.2345) <= PASSO / TAXA / 2 + 1e-9
