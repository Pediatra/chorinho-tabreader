"""Ataques de nota no áudio: espectrograma, fluxo espectral e picos (trilha A1).

Módulo de biblioteca, sem CLI. Usa numpy e o ``indice_de`` do A0 (que importa o pacote
``censo``; por isso o import da base é o mesmo do resto do motor).

PRÉ-PROCESSAMENTO É PARTE DA MEDIÇÃO. As constantes abaixo (``N_FFT``, ``PASSO``, a janela
de Hann de ``espectrograma``, ``GAMA_LOG``, ``DELTA_PICO`` e a conversão int16 -> [-1, 1))
são entrada do método: mudar qualquer uma delas INVALIDA a comparação com as medições já
feitas em ``data/saida/audio/a1/``.

Convenções:

- amostras int16 divididas por 32768 (intervalo [-1, 1));
- quadros CENTRADOS: o quadro ``k`` está centrado na amostra ``k * PASSO`` do trecho;
- todo tempo devolvido está na linha do tempo do VÍDEO (``t_amostra0 + índice / taxa``),
  a mesma do A0.

Viés do detector: o fluxo usa a diferença ``L[k] - L[k-1]`` atribuída ao quadro ``k``, então
o pico tende a cair depois do ataque real. O valor é medido no sintético (teste de
``tests/test_audio_onsets.py``) e reportado, NÃO subtraído das medições.
"""

from __future__ import annotations

import numpy as np

from tab.audio.extrair import indice_de
from tab.comum.violao import AFINACAO_MIDI as MIDI_CORDA

#: Tamanho da FFT, em amostras (2048 a 22050 Hz: resolução de ~10,8 Hz por bin).
N_FFT = 2048

#: Passo entre quadros, em amostras (256 a 22050 Hz: ~11,6 ms).
PASSO = 256

#: Ganho do log do fluxo: ``L = log1p(GAMA_LOG * mag)``.
GAMA_LOG = 100.0

#: Fração do máximo global da curva que um pico precisa estar acima da mediana móvel.
#: Escolhido antes das medições reais, para ficar acima da oscilação do ruído de fundo
#: (checado no teste de silêncio); não foi ajustado para casar com o gabarito.
DELTA_PICO = 0.05

#: MIDI das cordas soltas em afinação padrão (E A D G B E), contadas de 1 (aguda) a 6.

#: Quadros por bloco no cálculo da FFT (limita a memória sem mudar o resultado).
_BLOCO = 4096


def espectrograma(
    amostras: np.ndarray,
    taxa: int,
    t_amostra0: float,
    n_fft: int = N_FFT,
    passo: int = PASSO,
    t0: float | None = None,
    t1: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Magnitude da STFT com quadros centrados, na linha do tempo do vídeo.

    Args:
        amostras: áudio ``int16`` mono (o FLAC do A0, lido por ``ler``).
        taxa: taxa de amostragem, em Hz.
        t_amostra0: instante, no vídeo, da amostra de índice 0.
        n_fft: tamanho da FFT (padrão ``N_FFT``).
        passo: passo entre quadros, em amostras (padrão ``PASSO``).
        t0: início do trecho, em segundos do vídeo (opcional).
        t1: fim do trecho, em segundos do vídeo (opcional).

    Returns:
        ``(mag, tempos, freqs)``: ``mag`` tem forma ``[quadros, bins]`` (Hann, magnitude da
        FFT em float64); ``tempos`` são os instantes de cada quadro no vídeo
        (``t_amostra0 + (i0 + k * passo) / taxa``); ``freqs`` são as frequências dos bins, em
        Hz. Com trecho vazio, ``mag`` tem zero linhas.
    """
    x = np.asarray(amostras).astype(np.float64) / 32768.0
    meta = {"t_amostra0": float(t_amostra0), "taxa": int(taxa)}
    i0, i1 = 0, len(x)
    if t0 is not None:
        i0 = max(0, indice_de(t0, meta))
    if t1 is not None:
        i1 = min(len(x), indice_de(t1, meta))
    x = x[i0:i1]
    freqs = np.fft.rfftfreq(n_fft, 1.0 / taxa)
    if len(x) == 0:
        return np.zeros((0, len(freqs))), np.zeros(0), freqs

    n_quadros = (len(x) - 1) // passo + 1
    xp = np.pad(x, (n_fft // 2, n_fft // 2))
    quadros = np.lib.stride_tricks.sliding_window_view(xp, n_fft)[::passo][:n_quadros]
    janela = np.hanning(n_fft)
    mag = np.empty((n_quadros, len(freqs)), dtype=np.float64)
    for ini in range(0, n_quadros, _BLOCO):
        fim = min(ini + _BLOCO, n_quadros)
        bloco = quadros[ini:fim] * janela
        mag[ini:fim] = np.abs(np.fft.rfft(bloco, axis=1))
    tempos = float(t_amostra0) + (i0 + np.arange(n_quadros) * passo) / taxa
    return mag, tempos, freqs


def fluxo_espectral(mag: np.ndarray) -> np.ndarray:
    """Fluxo espectral: soma, sobre os bins, do aumento positivo do log da magnitude.

    Args:
        mag: magnitude ``[quadros, bins]`` (de ``espectrograma``).

    Returns:
        Curva ``[quadros]``: ``fluxo[k] = sum_bins max(0, L[k] - L[k-1])`` com
        ``L = log1p(GAMA_LOG * mag)``; ``fluxo[0] = 0``.
    """
    fluxo = np.zeros(mag.shape[0], dtype=np.float64)
    if mag.shape[0] > 1:
        lg = np.log1p(GAMA_LOG * mag)
        fluxo[1:] = np.maximum(np.diff(lg, axis=0), 0.0).sum(axis=1)
    return fluxo


def midi_da_nota(corda: int, casa: int, transposicao: int = 0) -> int:
    """Número MIDI de uma nota do violão em afinação padrão.

    Args:
        corda: corda de 1 (mi agudo) a 6 (mi grave).
        casa: casa pisada (0 é solta).
        transposicao: semitons somados (capotraste ou afinação diferente).

    Returns:
        ``MIDI_CORDA[corda] + casa + transposicao``. Cordas 1..6 = MIDI 64, 59, 55, 50, 45, 40.

    Raises:
        ValueError: se ``corda`` não estiver entre 1 e 6.
    """
    if corda not in MIDI_CORDA:
        raise ValueError(f"corda fora de 1..6: {corda}")
    return MIDI_CORDA[corda] + int(casa) + int(transposicao)


def mascara_alturas(
    freqs: np.ndarray,
    midis: list[int],
    n_harm: int = 4,
    cents: float = 50.0,
) -> np.ndarray:
    """Bins que caem perto dos harmônicos das alturas dadas.

    Para cada MIDI e cada harmônico ``h`` (1..``n_harm``), marca os bins dentro de ``cents``
    da frequência ``f0 * h`` (``f0 = 440 * 2^((m - 69) / 12)``). Também marca SEMPRE o bin mais
    próximo de cada harmônico: com ``N_FFT`` de 2048 a 22050 Hz, um bin tem ~10,8 Hz e ±50 cents
    em notas graves é menos que um bin; sem isso a máscara ficaria vazia.

    Args:
        freqs: frequências dos bins, em Hz.
        midis: números MIDI das notas do evento.
        n_harm: quantos harmônicos (1 é a fundamental).
        cents: meia-largura da tolerância, em cents.

    Returns:
        Máscara booleana ``[bins]``.
    """
    mascara = np.zeros(len(freqs), dtype=bool)
    for m in midis:
        f0 = 440.0 * 2.0 ** ((m - 69) / 12.0)
        for h in range(1, n_harm + 1):
            f = f0 * h
            if f > freqs[-1]:
                break
            desvio = np.abs(1200.0 * np.log2(np.maximum(freqs, 1e-9) / f))
            mascara |= desvio <= cents
            mascara[int(np.argmin(np.abs(freqs - f)))] = True
    return mascara


def fluxo_nas_alturas(
    mag: np.ndarray,
    freqs: np.ndarray,
    midis: list[int],
    n_harm: int = 4,
    cents: float = 50.0,
) -> np.ndarray:
    """Fluxo espectral somado só nos bins dos harmônicos das alturas dadas.

    Mesma conta de ``fluxo_espectral``, restrita às colunas de ``mascara_alturas``.

    Args:
        mag: magnitude ``[quadros, bins]``.
        freqs: frequências dos bins, em Hz.
        midis: números MIDI esperados no evento.
        n_harm: quantos harmônicos.
        cents: meia-largura da tolerância, em cents.

    Returns:
        Curva ``[quadros]``; ``[0] = 0``. Se ``midis`` estiver vazia, é zero.
    """
    fluxo = np.zeros(mag.shape[0], dtype=np.float64)
    if mag.shape[0] < 2 or not midis:
        return fluxo
    mascara = mascara_alturas(freqs, midis, n_harm=n_harm, cents=cents)
    lg = np.log1p(GAMA_LOG * mag[:, mascara])
    fluxo[1:] = np.maximum(np.diff(lg, axis=0), 0.0).sum(axis=1)
    return fluxo


def _mediana_movel(curva: np.ndarray, meia: int) -> np.ndarray:
    """Mediana móvel de janela ``2 * meia + 1``, com borda replicada.

    Args:
        curva: sinal ``[quadros]``.
        meia: meia-largura da janela, em quadros.

    Returns:
        Mediana de cada quadro, ``[quadros]``.
    """
    preenchida = np.pad(curva, meia, mode="edge")
    janelas = np.lib.stride_tricks.sliding_window_view(preenchida, 2 * meia + 1)
    return np.median(janelas, axis=1)


def picos(
    curva: np.ndarray,
    tempos: np.ndarray,
    janela_mediana_s: float = 0.1,
    delta: float = DELTA_PICO,
) -> list[int]:
    """Máximos locais de uma curva acima de um limiar adaptativo.

    Um índice ``k`` é pico se ``curva[k]`` for maior que os dois vizinhos imediatos e maior que
    ``mediana_movel(k) + delta * max(curva)``. A mediana móvel é de ±``janela_mediana_s``
    (meia-largura de ``round(janela / dt)`` quadros; largura total de 2 vezes isso).

    Args:
        curva: curva ``[quadros]`` (por exemplo, ``fluxo_espectral``).
        tempos: instantes dos quadros (só o passo entre eles é usado).
        janela_mediana_s: meia-largura da janela da mediana, em segundos.
        delta: fração do máximo global que o pico precisa passar acima da mediana.

    Returns:
        Índices dos picos, em ordem crescente. Curva com menos de 3 quadros não tem picos.
    """
    if len(curva) < 3:
        return []
    dt = float(tempos[1] - tempos[0])
    meia = max(1, round(janela_mediana_s / dt))
    limiar = _mediana_movel(curva, meia) + delta * float(np.max(curva))
    c = curva[1:-1]
    maximo = (c > curva[:-2]) & (c > curva[2:]) & (c > limiar[1:-1])
    return (np.flatnonzero(maximo) + 1).tolist()
