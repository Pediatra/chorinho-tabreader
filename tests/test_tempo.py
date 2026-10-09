"""Tempo por travessia: o marcador que desliza dá onset; o que fica parado não dá.

Medido no `iwaki/henze`: banda de 6 px, matiz 102, ~16 px por 0,25 s (≈65 px/s), sem
saltos. Medido no `sky guitar` #4: banda parada em x=0–99 por 5 s — e ali o módulo tem
de devolver None em vez de carimbar um instante para todas as notas.
"""

from __future__ import annotations

from tab.tempo import (
    atribuir_tempos,
    duracoes_por_onset,
    patamares,
    resumo,
    tempo_de_x,
)


def _serie_deslizante() -> list[tuple[float, int]]:
    """O marcador andando 20 px a cada 0,25 s, de x=100 a x=500."""
    return [(i * 0.25, 100 + i * 20) for i in range(21)]


def test_travessia_interpola_entre_amostras() -> None:
    """Cruzar x=110 é 0,125 s depois do ponto em x=100."""
    assert tempo_de_x(_serie_deslizante(), 110) == 0.125


def test_travessia_acha_o_instante_de_cada_nota() -> None:
    """Três notas em x diferentes recebem três instantes diferentes."""
    tempos = atribuir_tempos([100, 200, 300], _serie_deslizante())
    assert tempos == [0.0, 1.25, 2.5]
    assert len(set(tempos)) == 3


def test_x_fora_da_serie_nao_recebe_tempo() -> None:
    """Sem travessia não há tempo — nada de instante inventado."""
    assert tempo_de_x(_serie_deslizante(), 5000) is None


def test_marcador_parado_nao_gera_onsets() -> None:
    """Banda parada (o caso do `sky guitar` #4) não descreve travessia."""
    parada = [(i * 0.25, 0) for i in range(20)]
    assert tempo_de_x(parada, 0) == 0.0  # o único x que ela cobre
    assert tempo_de_x(parada, 300) is None
    assert resumo(parada)["veredito"] == "parado"


def test_serie_vazia_ou_curta() -> None:
    """Sem marcador, o resumo diz isso em vez de fingir movimento."""
    assert resumo([])["veredito"] == "sem_marcador"
    assert resumo([(0.0, 10), (1.0, 12)])["veredito"] == "sem_marcador"


def test_resumo_reconhece_deslize() -> None:
    """A série do `iwaki/henze` é classificada como deslize."""
    r = resumo(_serie_deslizante())
    assert r["veredito"] == "desliza"
    assert r["passo_mediano_px"] == 20
    assert r["deslocamento_total_px"] == 400


def test_duracoes_sao_intervalos_e_a_ultima_e_nula() -> None:
    """Duração = intervalo até o próximo onset; a última não tem próximo."""
    assert duracoes_por_onset([0.0, 1.25, 2.5]) == [1.25, 1.25, None]
    assert duracoes_por_onset([0.0, None, 2.5]) == [None, None, None]


def test_salto_grande_nao_e_interpolado() -> None:
    """Troca de trecho (salto de +200 px) não pode virar travessia contínua."""
    serie = [(0.0, 100), (0.25, 120), (0.50, 320), (0.75, 340)]
    assert tempo_de_x(serie, 220) is None


def test_serie_erratica_nao_e_travessia() -> None:
    """Detecções espalhadas não são marcador andando — é o caso do `iwaki/henze`.

    Medido ao longo dos 342 s daquele vídeo: 14 detecções em x = 230, 285, 341, 548,
    638, 690, 844, 1184, 1491, 1527..., sem progressão. Um movimento suave de 4 s
    dentro disso me fez concluir "o marcador desliza" — era coincidência.
    """
    espalhada = [
        (t * 1.0, x) for t, x in enumerate([690, 341, 638, 285, 1527, 548, 1184, 230])
    ]
    assert resumo(espalhada)["veredito"] == "erratico"


def test_serie_monotonica_continua_deslizando() -> None:
    """O caso bom não pode ser afetado pela checagem de sentido."""
    assert resumo(_serie_deslizante())["veredito"] == "desliza"


def test_patamares_encontra_os_degraus() -> None:
    """Cursor que salta: x parado por várias amostras, depois salto, e assim por diante."""
    serie = [(0.0, 100), (0.25, 100), (0.5, 100), (0.75, 250), (1.0, 250), (1.25, 250)]
    degraus = patamares(serie)
    assert degraus == [(0.0, 0.5, 100), (0.75, 1.25, 250)]


def test_cursor_que_salta_e_reconhecido() -> None:
    """Três patamares avançando para o mesmo lado = `salta`, não `parado`."""
    serie = []
    for i, x in enumerate([100, 240, 380, 520]):
        serie += [(i * 1.0 + d * 0.25, x) for d in range(3)]
    assert resumo(serie)["veredito"] == "salta"


def test_patamar_unico_continua_parado() -> None:
    """Ficar parado num x só não é cursor que salta — é ruído parado."""
    assert resumo([(i * 0.25, 300) for i in range(20)])["veredito"] == "parado"


def test_trepida_nao_vira_erratico() -> None:
    """Banda que anda devagar e trepida ±2 px não é artefato — é lenta."""
    # 1 px por segundo: anda sempre para o mesmo lado, mas devagar demais para dar onset
    lenta = [(i * 1.0, 300 + i) for i in range(40)]
    assert resumo(lenta)["veredito"] == "lento"


def test_playhead_de_nota_passa_a_velocidade() -> None:
    """O caso bom continua `desliza`: ~60 px/s."""
    rapida = [(i * 0.5, 100 + i * 30) for i in range(30)]  # 60 px/s
    r = resumo(rapida)
    assert r["veredito"] == "desliza"
    assert r["velocidade_px_s"] >= 5.0
