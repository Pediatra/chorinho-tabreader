"""Testes do alinhador tela -> áudio (trilha A2). Sem acervo e sem GPU.

Cobre: (a) o marcador não sobrevive a ``esconder_marcador``; (b) a programação dinâmica pula
picos extras e recusa uma coluna sem ataque; (c) áudio sintético: erro medido até o ataque
verdadeiro; (d) o perfil "nova energia" responde mais à nota que entrou.
"""

from __future__ import annotations

import json

import numpy as np

from tab.audio.alinhar import (
    COS_ABAFADA,
    CUSTO_SEM_ATAQUE_V1,
    MIDI_MIN,
    N_POSICOES,
    _cos_abafada,
    _decidir_onsets_v2,
    alinhar,
    alinhar_dtw,
    alinhar_sequencia,
    alinhar_trecho,
    alinhar_trecho_iterativo,
    colunas_abafadas,
    e_rasgueado,
    esconder_marcador,
    molde_coluna,
    perfis_em_instantes,
)
from tab.audio.onsets import espectrograma

TAXA = 22050


def _produto_com_marcador() -> dict:
    """Produto sintético com todos os campos do marcador e dos observadores.

    Returns:
        Dicionário no formato do produto, com ``t_ini`` = 1,2345 s e ``tela`` 7.
    """
    nota = {
        "tela": 7,
        "coluna": 1,
        "corda": 2,
        "casa": 0,
        "x_quadro": 224,
        "x_centro_quadro": 231.0,
        "compasso": 4,
        "tecnica": None,
        "confianca": 0.99,
        "passagem": 1,
        "exibicao": 0,
        "t_ini": 1.2345,
    }
    nota_b = {**nota, "corda": 1, "casa": 3, "t_ini": 1.2345}
    nota_c = {**nota, "coluna": 2, "corda": 3, "casa": 2, "t_ini": 1.9876}
    return {
        "esquema": "chorinho/video@1",
        "video": {"arquivo": "x.mp4"},
        "gerado_por": "teste",
        "telas": [
            {
                "id": 7,
                "painel": {"x0": 10, "y0": 20},
                "passo": 20,
                "modo": "observador_posicao",
                "barlines_x": [100, 200],
                "tempo": {"medido": True, "observador": "posicao"},
                "leitura": {"confianca": 0.9},
                "exibicoes": [
                    {
                        "t0": 1.0,
                        "t1": 5.0,
                        "tempo": {"medido": True, "observador": "cor"},
                        "observadores": {"posicao": {"coerencia": 1.0}},
                        "passagens": [
                            [
                                {"coluna": 1, "t_ini": 1.2345},
                                {"coluna": 2, "t_ini": 1.9876},
                            ]
                        ],
                        "amostras": 3,
                    }
                ],
            }
        ],
        "notas": [nota, nota_b, nota_c],
        "nao_notas": [{"tela": 7, "coluna": 3, "tipo": "barra"}],
        "resumo": {"notas": 3},
    }


def _chaves_recursivas(obj: object) -> set[str]:
    """Todas as chaves de dicionários aninhados, em qualquer profundidade.

    Args:
        obj: estrutura JSON (dict, list ou escalar).

    Returns:
        Conjunto com todas as chaves encontradas.
    """
    if isinstance(obj, dict):
        chaves = set(obj)
        for v in obj.values():
            chaves |= _chaves_recursivas(v)
        return chaves
    if isinstance(obj, list):
        return set().union(*(_chaves_recursivas(v) for v in obj)) if obj else set()
    return set()


def test_esconder_marcador_remove_todo_o_marcador():
    """(a) Nenhum campo do marcador sobrevive, e o instante de ``t_ini`` não aparece."""
    oculto = esconder_marcador(_produto_com_marcador())
    texto = json.dumps(oculto)
    proibidos = {
        "t_ini",
        "passagens",
        "passagem",
        "exibicao",
        "tempo",
        "observadores",
        "observador",
        "tecnica",
        "compasso",
        "confianca",
        "x_quadro",
        "x_centro_quadro",
        "barlines_x",
        "painel",
        "modo",
        "leitura",
        "amostras",
        "notas",
        "nao_notas",
        "resumo",
        "video",
    }
    assert not (_chaves_recursivas(oculto) & proibidos)
    assert "1.2345" not in texto
    assert "1.9876" not in texto
    assert set(oculto) == {"telas"}
    tela = oculto["telas"][0]
    assert set(tela) == {"id", "exibicoes", "colunas", "abafadas"}
    assert tela["id"] == 7
    assert tela["exibicoes"] == [{"t0": 1.0, "t1": 5.0}]
    assert tela["colunas"] == {1: [[1, 3], [2, 0]], 2: [[3, 2]]}


def test_programacao_dinamica_pula_extras_e_recusa_ausente():
    """(b) Seis colunas, dois picos extras e um ataque faltando.

    Candidatos (tempo, molde da coluna ou ``None`` para extra):
    0,50 (c0); 1,20 (c1); 1,35 (extra); 1,90 (c2); 2,90 (extra); 3,10 (c4); 3,80 (c5).
    A coluna 3 não tem candidato: deve ser recusada (``None``).
    """
    moldes = [np.eye(N_POSICOES)[i * 10] for i in range(6)]
    candidatos = [
        (0.50, 0),
        (1.20, 1),
        (1.35, None),
        (1.90, 2),
        (2.90, None),
        (3.10, 4),
        (3.80, 5),
    ]
    tempos = np.array([t for t, _ in candidatos])
    perfis = []
    for _, indice in candidatos:
        if indice is None:
            perfis.append(np.eye(N_POSICOES)[59])
        else:
            perfis.append(moldes[indice])
    custo = np.array([[1.0 - float(m @ p) for p in perfis] for m in moldes])
    atribuicao, total = alinhar_sequencia(custo, tempos, periodo=0.7)
    assert atribuicao == [0, 1, 3, None, 5, 6]
    assert total < 6 * CUSTO_SEM_ATAQUE_V1
    # Os extras (índices 2 e 4) não podem ter sido casados.
    assert 2 not in atribuicao
    assert 4 not in atribuicao


def test_programacao_dinamica_sem_candidatos_recusa_tudo():
    """(b, caso limite) Sem nenhum candidato, todas as colunas saem recusadas."""
    custo = np.ones((3, 0))
    atribuicao, total = alinhar_sequencia(custo, np.array([]), periodo=0.5)
    assert atribuicao == [None, None, None]
    assert total == 3 * CUSTO_SEM_ATAQUE_V1


def test_dtw_de_subsequencia_e_monotono():
    """DTW: o 1º quadro de cada coluna cresce com a coluna, e todas são casadas.

    Propriedade, não acerto: com custo local não negativo e passos (1,0), (0,1), (1,1), o DTW
    não "pula" para um vale distante (cada célula do caminho soma custo). Por isso aqui só se
    testa a monotonia e a cobertura do caminho, não o vale exato.
    """
    rng = np.random.default_rng(7)
    custo = rng.uniform(0.2, 1.0, size=(5, 60))
    primeiro, total = alinhar_dtw(custo)
    assert np.all(primeiro >= 0)
    assert np.all(np.diff(primeiro) >= 0)
    assert np.isfinite(total)


def _sintetizar(duracao: float, notas: list[tuple[float, int, float]]) -> np.ndarray:
    """Áudio sintético: harmônicos 1 a 4 com amplitude 1/h, uma nota por ataque.

    Cada nota é ``(t_ataque, midi, tau)``: envelope exponencial a partir do ataque, que é
    instantâneo. Ruído branco de amplitude 0,002 com semente fixa (12345).

    Args:
        duracao: duração total, em segundos.
        notas: lista de ``(t_ataque, midi, tau)``.

    Returns:
        Áudio ``int16`` mono a 22 050 Hz.
    """
    n = round(duracao * TAXA)
    t = np.arange(n) / TAXA
    x = np.zeros(n)
    for t_ataque, midi, tau in notas:
        f0 = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        env = np.where(t >= t_ataque, np.exp(-(t - t_ataque) / tau), 0.0)
        for h in range(1, 5):
            x += env * np.sin(2.0 * np.pi * f0 * h * t) / h
    x = 0.3 * x / max(float(np.max(np.abs(x))), 1e-9)
    rng = np.random.default_rng(12345)
    x += 0.002 * rng.standard_normal(n)
    return np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16)


#: (coluna, pares (corda, casa)) e MIDI esperado de cada uma.
_COLUNAS_SINTETICAS = [
    (1, [[6, 0]]),  # 40
    (2, [[5, 2]]),  # 47
    (3, [[4, 2]]),  # 52
    (4, [[3, 0]]),  # 55
    (5, [[2, 3]]),  # 62
    (6, [[1, 0]]),  # 64
    (7, [[2, 8]]),  # 67
    (8, [[1, 7]]),  # 71
]
_MIDIS_SINTETICOS = [40, 47, 52, 55, 62, 64, 67, 71]
_RUBATO_S = [0.06, -0.08, 0.03, -0.05, 0.08, -0.02, 0.05, -0.07]


def test_audio_sintetico_ataque_a_ataque():
    """(c) Oito colunas, rubato de até ±80 ms: erro do ``t_audio`` até o ataque verdadeiro.

    O fluxo tende a cair ~28 ms ANTES do ataque (viés medido em ``audio_onsets``), então o
    erro esperado é negativo. O limite de 30 ms é o do enunciado; o erro medido é reportado.
    """
    ataques = [1.0 + 0.7 * k + _RUBATO_S[k] for k in range(8)]
    notas = [(t, m, 0.4) for t, m in zip(ataques, _MIDIS_SINTETICOS, strict=True)]
    amostras = _sintetizar(7.5, notas)
    oculto = {
        "telas": [
            {
                "id": 1,
                "exibicoes": [{"t0": 0.5, "t1": 6.5}],
                "colunas": dict(_COLUNAS_SINTETICAS),
            }
        ]
    }
    saida = alinhar(oculto, amostras, TAXA, 0.0, metodo="onsets")
    registros = {r["coluna"]: r for r in saida["colunas"]}
    erros_ms = {}
    for k, col in enumerate(range(1, 9)):
        reg = registros[col]
        assert reg["t_audio"] is not None, f"coluna {col} recusada: {reg['motivo']}"
        erros_ms[col] = round((reg["t_audio"] - ataques[k]) * 1000.0, 2)
    print("erros medidos (ms):", erros_ms)
    maior = max(abs(e) for e in erros_ms.values())
    assert maior <= 30.0, f"erro máximo medido {maior:.2f} ms: {erros_ms}"


def test_perfil_responde_mais_a_nota_que_entrou():
    """(d) No ataque da nota B, o perfil marca B, não a nota A que já soava.

    A (MIDI 57) soa de 0 s a 2 s; B (MIDI 64) entra em 1,0 s. Em t = 1,0 s, a média de depois
    ([1,0; 1,15]) tem A e B, a de antes ([0,9; 1,0]) só A: o bin de A quase não muda.
    """
    amostras = _sintetizar(2.0, [(0.0, 57, 1000.0), (1.0, 64, 1000.0)])
    mag, tempos, freqs = espectrograma(
        amostras, TAXA, 0.0, n_fft=4096, passo=256, t0=0.6, t1=1.4
    )
    dt = 256 / TAXA
    perfil = perfis_em_instantes(mag, tempos, freqs, np.array([1.0]), dt)[0]
    pos_a = 57 - MIDI_MIN
    pos_b = 64 - MIDI_MIN
    assert perfil[pos_b] > 0.5
    assert perfil[pos_a] < 0.3 * perfil[pos_b]


def test_molde_tem_norma_um_e_harmonicos():
    """Molde de uma nota: pico na fundamental e menor na oitava, com norma 1."""
    molde = molde_coluna([60])
    assert abs(float(np.linalg.norm(molde)) - 1.0) < 1e-12
    assert molde[60 - MIDI_MIN] > molde[72 - MIDI_MIN] > 0.0


def test_trecho_v2_com_prefixo_e_sufixo_fora():
    """(a, v2) 10 colunas, só as 2..7 (6 de 10) são tocadas; prefixo e sufixo ficam fora.

    Candidatos só nos instantes das colunas tocadas, mais dois candidatos extras (pulados). As
    colunas fora do trecho têm cosseno zero para todos os candidatos.
    """
    n_col = 10
    tempos = np.array([0.20, 0.60, 1.00, 1.70, 2.40, 3.10, 3.80, 4.50, 4.9])
    cos = np.zeros((n_col, len(tempos)))
    tocadas = {2: 0, 3: 1, 4: 3, 5: 4, 6: 5, 7: 6}
    for c, j in tocadas.items():
        cos[c, j] = 0.95
    atrib, trecho, pontuacao = alinhar_trecho(cos, tempos, periodo=0.7)
    assert trecho == (2, 7)
    assert [atrib[c] for c in (0, 1, 8, 9)] == [None, None, None, None]
    assert [atrib[c] for c in range(2, 8)] == [0, 1, 3, 4, 5, 6]
    assert pontuacao > 0.0


def test_t_iterativo_converge_partindo_do_dobro():
    """(b, v2) T0 = 2 * T verdadeiro (0,7 s): converge para 0,7 s, em até 4 rodadas."""
    n = 10
    tempos = np.array([0.7 * k for k in range(n)])
    cos = np.eye(n) * 0.95
    res = alinhar_trecho_iterativo(cos, tempos, t0_periodo=1.4)
    assert res["atribuicao"] == list(range(n))
    assert res["trecho"] == (0, n - 1)
    assert res["iteracoes"] <= 4
    assert res["convergiu"]
    assert abs(res["T_recalculado"] - 0.7) / 0.7 < 0.02
    assert abs(res["T_usado"] - 0.7) / 0.7 < 0.02


def _nao_nota_x(tela: int, coluna: int, corda: int, top1: str) -> dict:
    """Um glifo de técnica (``nao_notas``) com o top-1 dado, como o classificador grava.

    Args:
        tela: id da tela.
        coluna: coluna da tela.
        corda: corda do glifo.
        top1: rótulo de maior confiança do classificador.

    Returns:
        Registro de ``nao_notas`` com ``classe`` ``tecnica`` e ``simbolo_cru.top3``.
    """
    return {
        "tela": tela,
        "coluna": coluna,
        "corda": corda,
        "classe": "tecnica",
        "simbolo_cru": {"top3": [[top1, 0.9], ["tecnica", 0.05]]},
    }


def test_colunas_abafadas_pega_pilha_de_quatro_x_sem_nota():
    """Quatro técnicas com top-1 ``15`` em cordas distintas, sem nota: coluna abafada."""
    produto = {
        "notas": [{"tela": 7, "coluna": 1, "corda": 1, "casa": 0}],
        "nao_notas": [_nao_nota_x(7, 5, c, "15") for c in (1, 2, 3, 4)],
    }
    assert colunas_abafadas(produto) == {(7, 5)}


def test_colunas_abafadas_ignora_duas_cordas_nota_vizinha_e_digito():
    """Duas técnicas não bastam; técnica numa coluna com nota não conta; top-1 de dígito não."""
    produto = {
        "notas": [{"tela": 7, "coluna": 7, "corda": 1, "casa": 3}],
        "nao_notas": [
            _nao_nota_x(7, 6, 1, "15"),
            _nao_nota_x(7, 6, 2, "15"),
            *[_nao_nota_x(7, 7, c, "15") for c in (1, 2, 3, 4)],
            *[_nao_nota_x(7, 8, c, "7") for c in (1, 2, 3, 4)],
            *[_nao_nota_x(7, 5, c, "15") for c in (1, 2, 3, 4)],
        ],
    }
    assert colunas_abafadas(produto) == {(7, 5)}


def _nao_nota_x_rede(tela: int, coluna: int, corda: int) -> dict:
    """X do leitor ``rede`` (decisão 0010): classe ``x``, sem ``simbolo_cru``.

    Args:
        tela: id da tela.
        coluna: coluna do X.
        corda: corda do X.

    Returns:
        Registro de ``nao_notas``.
    """
    return {"tela": tela, "coluna": coluna, "corda": corda, "classe": "x"}


def test_colunas_abafadas_pega_pilha_de_x_do_leitor_rede():
    """Quatro X de classe ``x`` em cordas distintas, sem nota: abafada; três não bastam."""
    produto = {
        "notas": [{"tela": 2, "coluna": 9, "corda": 1, "casa": 0}],
        "nao_notas": [
            *[_nao_nota_x_rede(2, 4, c) for c in (3, 4, 5, 6)],
            *[_nao_nota_x_rede(2, 6, c) for c in (4, 5, 6)],
            *[_nao_nota_x_rede(2, 9, c) for c in (2, 3, 4, 5)],
        ],
    }
    assert colunas_abafadas(produto) == {(2, 4)}


def test_cos_abafada_so_vale_no_pico_de_fluxo_forte():
    """Pico com fluxo abaixo da mediana vira ``-inf`` (sem ataque); os demais, ``COS_ABAFADA``."""
    fluxo = np.array([1.0, 2.0, 3.0, 4.0])
    linha = _cos_abafada(fluxo)
    assert np.isneginf(linha[0]) and np.isneginf(linha[1])
    assert linha[2] == COS_ABAFADA and linha[3] == COS_ABAFADA


def test_dp_abafada_casa_pico_forte_e_colunas_com_altura_mantem_o_seu():
    """Abafada entre duas notas casa o pico do meio; cada nota mantém o seu pico e o cosseno
    médio só conta as colunas com altura (o 0,5 da abafada não entra)."""
    sequencia = [(1, [60]), (2, []), (3, [62]), (4, [64]), (5, [65])]
    t_pk = np.array([0.5, 1.0, 1.5, 2.0, 2.5])
    cos_pk = np.full((5, 5), 0.05)
    cos_pk[0, 0] = cos_pk[2, 2] = cos_pk[3, 3] = cos_pk[4, 4] = 0.9
    cos_pk[1] = _cos_abafada(np.array([5.0, 9.0, 5.0, 5.0, 5.0]))
    resumo, registros = _decidir_onsets_v2(1, 0, sequencia, {}, cos_pk, t_pk, 3.0, {2})
    por_coluna = {r["coluna"]: r for r in registros}
    assert not resumo["recusada_exibicao"]
    assert resumo["n_casadas"] == 4
    assert resumo["n_abafadas_casadas"] == 1
    assert resumo["cos_medio"] == 0.9
    assert por_coluna[1]["t_audio"] == 0.5
    assert por_coluna[2]["t_audio"] == 1.0 and por_coluna[2]["motivo"] is None
    assert por_coluna[3]["t_audio"] == 1.5
    assert por_coluna[4]["t_audio"] == 2.0
    assert por_coluna[5]["t_audio"] == 2.5


def test_rasgueado_no_limite_de_vinte_por_cento():
    """Uma em cinco (20 %) já é rasgueado; uma em seis (16 %) não; sem colunas, não."""
    assert e_rasgueado(1, 5) is True
    assert e_rasgueado(1, 6) is False
    assert e_rasgueado(0, 0) is False


def _oculto_sintetico(colunas: dict, abafadas: list[int] | None = None) -> dict:
    """Um oculto de uma tela e uma exibição, com as colunas dadas.

    Args:
        colunas: ``{coluna: [[corda, casa]]}`` das colunas com altura.
        abafadas: colunas abafadas da tela, ou ``None`` para não declarar.

    Returns:
        Dicionário no formato de ``esconder_marcador``.
    """
    tela = {"id": 1, "exibicoes": [{"t0": 0.5, "t1": 7.0}], "colunas": colunas}
    if abafadas is not None:
        tela["abafadas"] = abafadas
    return {"telas": [tela]}


def test_sem_abafada_saida_com_tipo_nota_e_flags_zero():
    """Sem coluna abafada, a saída é a de antes: todas ``nota``, sem rasgueado."""
    ataques = [1.0 + 0.7 * k for k in range(8)]
    notas = [(t, m, 0.4) for t, m in zip(ataques, _MIDIS_SINTETICOS, strict=True)]
    amostras = _sintetizar(7.5, notas)
    saida_sem = alinhar(
        _oculto_sintetico(dict(_COLUNAS_SINTETICAS)), amostras, TAXA, 0.0
    )
    saida_vazia = alinhar(
        _oculto_sintetico(dict(_COLUNAS_SINTETICAS), abafadas=[]),
        amostras,
        TAXA,
        0.0,
    )
    assert saida_sem == saida_vazia
    assert all(c["tipo"] == "nota" for c in saida_sem["colunas"])
    ex = saida_sem["exibicoes"][0]
    assert ex["n_abafadas_casadas"] == 0 and ex["rasgueado"] is False


def test_abafada_ponta_a_ponta_casa_o_ataque_de_ruido():
    """Nove slots de grade de 0,7 s; o slot 5 é um X (ruído de 30 ms, sem altura).

    A coluna abafada casa o ataque de ruído, tem ``tipo`` ``abafada`` e não entra no cosseno
    médio; as notas seguem nos seus slots. Uma abafada em nove colunas fica abaixo de 20 %.
    """
    slots = [1.0 + 0.7 * k for k in range(9)]
    pares = {
        1: [[6, 0]],
        2: [[5, 2]],
        3: [[4, 2]],
        4: [[3, 0]],
        6: [[2, 3]],
        7: [[1, 0]],
        8: [[2, 8]],
        9: [[1, 7]],
    }
    midis = {1: 40, 2: 47, 3: 52, 4: 55, 6: 62, 7: 64, 8: 67, 9: 71}
    coluna_slot = {1: 0, 2: 1, 3: 2, 4: 3, 6: 5, 7: 6, 8: 7, 9: 8}
    notas = [(slots[coluna_slot[c]], midis[c], 0.4) for c in pares]
    amostras = _sintetizar(8.0, notas).astype(np.float64)
    rng = np.random.default_rng(777)
    i0 = round(slots[4] * TAXA)
    amostras[i0 : i0 + round(0.03 * TAXA)] += (
        rng.standard_normal(round(0.03 * TAXA)) * 3000.0
    )
    amostras = np.clip(np.round(amostras), -32768, 32767).astype(np.int16)
    oculto = _oculto_sintetico(pares, abafadas=[5])
    saida = alinhar(oculto, amostras, TAXA, 0.0, metodo="onsets")
    por_coluna = {r["coluna"]: r for r in saida["colunas"]}
    abafada = por_coluna[5]
    assert abafada["tipo"] == "abafada"
    assert abafada["t_audio"] is not None, abafada["motivo"]
    assert abs(abafada["t_audio"] - slots[4]) <= 0.06
    assert abafada["motivo"] is None
    for c in pares:
        assert por_coluna[c]["tipo"] == "nota"
        assert por_coluna[c]["t_audio"] is not None, por_coluna[c]["motivo"]
    ex = saida["exibicoes"][0]
    assert ex["n_abafadas_casadas"] == 1
    assert ex["rasgueado"] is False
