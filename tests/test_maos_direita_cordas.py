"""Testes das funções puras do diagnóstico M7 (sem GPU e sem acervo)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tab.maos_direita_cordas import (
    CORES_PONTAS,
    N_CORDAS,
    _filtro_de_linha,
    _picos_do_perfil,
    _relevo_de_linha,
    achar_painel,
    achar_retas,
    alinhar_retas,
    ataques_sorteados,
    auc,
    consolidar_retas,
    corda_mais_frequente,
    cordas_do_ataque,
    cresta_da_reta,
    desenhar_folha,
    deslocamento_entre_quadros,
    deslocamentos_pontas,
    espessura_corda,
    instantes_de_controle,
    instantes_de_referencia,
    instantes_distintos,
    mao_direita_no_painel,
    mascara_de_caixas,
    ordenar_cordas,
    pontas_no_painel,
    ponto_do_rotulo,
    preditor_ataque,
    refinar_reta,
    resumo_deslocamentos,
    rotulo_ataque,
    texto_deslocamentos,
)

# Ângulo da direção das cordas: sobem para a direita na imagem (y cresce para baixo).
THETA_CORDAS = np.deg2rad(140.0)


def _quadro_com_cordas(ys: list[float], w: int = 400, h: int = 300) -> np.ndarray:
    """Imagem escura com linhas claras paralelas, que cruzam o meio em ``ys``.

    Args:
        ys: alturas, em ``x = w/2``, das linhas.
        w: largura.
        h: altura.

    Returns:
        Imagem BGR de ``uint8``.
    """
    img = np.full((h, w, 3), 30, np.uint8)
    d = np.array([np.cos(THETA_CORDAS), np.sin(THETA_CORDAS)])
    for y in ys:
        p = np.array([w / 2, y])
        a = (int(p[0] - d[0] * w), int(p[1] - d[1] * w))
        b = (int(p[0] + d[0] * w), int(p[1] + d[1] * w))
        cv2.line(img, a, b, (200, 200, 200), 2)
    return img


def test_achar_painel_acha_faixa_preta_e_tablatura_branca():
    """O painel começa depois da faixa preta horizontal e para na faixa vertical."""
    img = np.full((1080, 1920, 3), 250, np.uint8)
    img[500:520, :] = 0
    img[520:, :] = 40
    img[520:, 0:655] = 120
    img[520:, 655:670] = 0
    assert achar_painel(img) == (0, 520, 655, 1080)


def test_achar_painel_sem_faixa_levanta_erro():
    """Sem a faixa preta vertical não há painel."""
    img = np.full((1080, 1920, 3), 120, np.uint8)
    with pytest.raises(ValueError, match="vertical"):
        achar_painel(img)


def test_achar_retas_recupera_as_seis_cordas():
    """Seis linhas paralelas viram seis retas com o ângulo e a altura certos."""
    ys = [60, 100, 140, 180, 220, 260]
    retas = achar_retas(_quadro_com_cordas(ys))
    assert len(retas) >= N_CORDAS
    achadas = sorted(r["y_centro"] for r in retas)
    for y in ys:
        assert min(abs(a - y) for a in achadas) <= 3.0
    for r in retas:
        assert abs(np.degrees(r["theta"]) - 140.0) <= 2.0


def test_picos_do_perfil_pega_os_mais_proeminentes():
    """O maior pico vem primeiro; um pico colado ao maior é descartado."""
    perfil = np.zeros(40, np.float32)
    perfil[5] = 10
    perfil[6] = 9
    perfil[20] = 4
    picos = _picos_do_perfil(perfil, n=2, janela=5, separacao=3)
    assert [i for i, _ in picos] == [5, 20]


def test_deslocamento_entre_quadros_mede_a_translacao():
    """Um quadro deslocado de (dx, dy) devolve (dx, dy) em relação ao de referência."""
    rng = np.random.default_rng(20261015)
    base = cv2.GaussianBlur(rng.random((120, 160)).astype(np.float32), (0, 0), 2)
    ref = _relevo_de_linha((base * 255).astype(np.uint8))
    desl = np.roll(np.roll(ref, 4, axis=1), -3, axis=0)
    dx, dy = deslocamento_entre_quadros(ref, desl)
    assert dx == pytest.approx(4.0, abs=0.5)
    assert dy == pytest.approx(-3.0, abs=0.5)


def test_alinhar_retas_aplica_a_formula_do_deslocamento():
    """Com (dx, dy), y_centro vira y - dy + dx * tan(theta)."""
    reta = {"theta": 0.7, "y_centro": 100.0, "suporte": 1.0}
    (nova,) = alinhar_retas([reta], (2.0, -3.0))
    assert nova["y_centro"] == pytest.approx(100.0 + 3.0 + 2.0 * np.tan(0.7))


def test_consolidar_retas_junta_quadros_com_deriva():
    """Seis cordas que derivam de quadro para quadro viram seis, cada uma em 5 quadros."""
    base = [300.0, 337.0, 374.0, 411.0, 448.0, 485.0]
    quadros = []
    for deriva in (-6.0, -2.0, 0.0, 3.0, 5.0):
        retas = [{"theta": 2.4, "y_centro": y + deriva, "suporte": 50.0} for y in base]
        quadros.append(retas)
    quadros[1].append({"theta": 2.4, "y_centro": 100.0, "suporte": 5.0})
    cordas = consolidar_retas(quadros)
    assert len(cordas) == N_CORDAS
    assert [c["n_quadros"] for c in cordas] == [5] * 6
    for c, y in zip(cordas, base, strict=True):
        assert c["y_centro"] == pytest.approx(y, abs=6.0)


def test_consolidar_retas_descarta_linha_que_some():
    """Uma reta que aparece em menos de três quadros não entra."""
    quadros = [
        [{"theta": 2.4, "y_centro": 200.0, "suporte": 9.0}],
        [{"theta": 2.4, "y_centro": 200.0, "suporte": 9.0}],
        [],
        [],
    ]
    assert consolidar_retas(quadros) == []


def test_ordenar_cordas_numera_grossas_embaixo():
    """Se a metade de baixo é a mais grossa, 1 fica em cima e 6 embaixo."""
    cordas = [{"y_centro": y, "theta": 2.4} for y in range(6)]
    esp = [10.0, 10.0, 10.0, 50.0, 50.0, 50.0]
    numeradas = ordenar_cordas(cordas, esp)
    assert [c["corda"] for c in numeradas] == [1, 2, 3, 4, 5, 6]


def test_ordenar_cordas_numera_grossas_em_cima():
    """Se a metade de cima é a mais grossa, 6 fica em cima e 1 embaixo."""
    cordas = [{"y_centro": y, "theta": 2.4} for y in range(6)]
    esp = [50.0, 50.0, 50.0, 10.0, 10.0, 10.0]
    numeradas = ordenar_cordas(cordas, esp)
    assert [c["corda"] for c in numeradas] == [6, 5, 4, 3, 2, 1]


def test_ordenar_cordas_exige_seis():
    """Sem seis cordas não há numeração."""
    with pytest.raises(ValueError, match="esperava 6"):
        ordenar_cordas([{"y_centro": 1.0, "theta": 0.0}], [1.0])


def test_espessura_corda_cresce_com_a_largura():
    """Uma linha de 5 px dá área maior que uma de 1 px, na mesma posição."""
    fina = np.full((200, 300), 20, np.uint8)
    grossa = np.full((200, 300), 20, np.uint8)
    th = np.deg2rad(40.0)
    d = np.array([np.cos(th), np.sin(th)])
    for img, esp in ((fina, 1), (grossa, 5)):
        a = np.array([150.0, 100.0]) - d * 300
        b = np.array([150.0, 100.0]) + d * 300
        cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), 220, esp)
    reta = {"theta": float(th), "y_centro": 100.0}
    e_fina = espessura_corda(fina.astype(np.float32), reta)
    e_grossa = espessura_corda(grossa.astype(np.float32), reta)
    assert e_fina is not None and e_grossa is not None
    assert e_grossa["area"] > 2 * e_fina["area"]


def test_ataques_sorteados_sao_deterministicos_e_espalhados():
    """Mesma semente, mesmo sorteio; um ataque por faixa, em ordem."""
    instantes = [float(i) for i in range(300)]
    a = ataques_sorteados(instantes, 30, 20261015)
    b = ataques_sorteados(instantes, 30, 20261015)
    assert a == b
    assert len(a) == 30
    assert a == sorted(a)
    for i, t in enumerate(a):
        assert i * 10 <= t < (i + 1) * 10


def test_instantes_distintos_e_de_referencia():
    """Instantes sem repetição e quadros de referência espalhados."""
    notas = [{"t_ini": 1.0004}, {"t_ini": 1.0}, {"t_ini": None}, {"t_ini": 2.0}]
    assert instantes_distintos(notas) == [1.0, 2.0]
    ref = instantes_de_referencia([float(i) for i in range(100)], 5)
    assert len(ref) == 5
    assert ref == sorted(ref)


def test_cordas_do_ataque_usa_tolerancia():
    """Só notas com o mesmo t_ini (dentro de 2 ms) contam."""
    notas = [
        {"corda": 6, "casa": 0, "t_ini": 1.0},
        {"corda": 4, "casa": 2, "t_ini": 1.001},
        {"corda": 3, "casa": 2, "t_ini": 2.0},
    ]
    tab = cordas_do_ataque(notas, 1.0)
    assert [(c["corda"], c["casa"]) for c in tab] == [(6, 0), (4, 2)]


def test_mao_direita_no_painel_escolhe_a_de_maior_media():
    """Entre as mãos direitas com o centro no painel, fica a de maior média."""
    maos = [
        {"lado": "esquerda", "caixa": [100, 600, 150, 650], "media": 0.9},
        {"lado": "direita", "caixa": [10, 600, 60, 650], "media": 0.5},
        {"lado": "direita", "caixa": [20, 600, 80, 700], "media": 0.8},
        {"lado": "direita", "caixa": [700, 600, 800, 700], "media": 0.99},
    ]
    assert mao_direita_no_painel(maos, (0, 522, 655, 1080)) == 2


def test_mao_direita_no_painel_sem_mao_devolve_none():
    """Sem mão direita dentro do painel, o resultado é None."""
    maos = [{"lado": "direita", "caixa": [700, 600, 800, 700], "media": 0.9}]
    assert mao_direita_no_painel(maos, (0, 522, 655, 1080)) is None


def test_pontas_no_painel_tira_o_deslocamento():
    """As pontas saem em pixels do recorte, descontado o canto do painel."""
    pts = [[0.0, 0.0] for _ in range(21)]
    pts[4] = [110.0, 600.0]
    pts[8] = [130.0, 620.0]
    registro = {"pts": pts}
    saida = pontas_no_painel(registro, (10, 500, 655, 1080))
    assert saida[4] == (100, 100)
    assert saida[8] == (120, 120)


def test_rotulo_e_folha_formatos():
    """O rótulo traz o instante e corda/casa; a folha empilha as linhas."""
    ataque = {"t_ini": 462.8, "cordas_tab": [{"corda": 6, "casa": 0}]}
    assert rotulo_ataque(ataque) == "t=462.80  tab corda/casa: 6/0"
    quadro = np.zeros((50, 40, 3), np.uint8)
    folha = desenhar_folha([("x", [quadro, quadro])])
    assert folha.shape == (26 + 50 + 8, 80, 3)


def _ataque_com_maos(t: float, dist: float) -> dict:
    """Ataque sintético: a ponta 4 anda ``dist`` px entre -0,13 s e +0,07 s."""
    pts_a = [[0.0, 0.0] for _ in range(21)]
    pts_b = [[0.0, 0.0] for _ in range(21)]
    for k in CORES_PONTAS:
        pts_a[k] = [100.0, 600.0]
        pts_b[k] = [100.0 + (dist if k == 4 else 0.0), 600.0]
    quadros = []
    for delta in (-0.20, -0.13, -0.07, 0.0, 0.07):
        pts = pts_a if delta == -0.13 else pts_b
        quadros.append(
            {
                "delta": delta,
                "direita": {"pts": pts} if delta in (-0.13, 0.07) else None,
            }
        )
    return {"t_ini": t, "cordas_tab": [{"corda": 6, "casa": 0}], "quadros": quadros}


def test_rotulo_mostra_o_instante_do_proprio_ataque():
    """Cada rótulo traz o t do seu ataque (não o do primeiro)."""
    a = {"t_ini": 387.85, "cordas_tab": [{"corda": 2, "casa": 0}]}
    b = {"t_ini": 62.5, "cordas_tab": [{"corda": 4, "casa": 3}]}
    assert rotulo_ataque(a).startswith("t=387.85")
    assert rotulo_ataque(b).startswith("t=62.50")
    assert "4/3" in rotulo_ataque(b)


def test_deslocamento_da_ponta_entre_os_dois_quadros():
    """A distância da ponta 4 entre -0,13 s e +0,07 s sai em px; as outras, zero."""
    ataque = _ataque_com_maos(10.0, 12.0)
    desl = deslocamentos_pontas(ataque)
    assert desl[4] == pytest.approx(12.0)
    assert desl[8] == pytest.approx(0.0)
    assert "4=12.0" in texto_deslocamentos(ataque)


def test_deslocamento_sem_mao_vira_none():
    """Sem mão direita num dos quadros, o deslocamento é None."""
    ataque = _ataque_com_maos(10.0, 12.0)
    ataque["quadros"][4]["direita"] = None
    assert all(v is None for v in deslocamentos_pontas(ataque).values())


def test_resumo_mediana_e_p90():
    """O resumo traz mediana e p90 por ponta entre os ataques com mão."""
    ataques = [_ataque_com_maos(float(i), float(i)) for i in range(1, 11)]
    resumo = resumo_deslocamentos(ataques)
    assert resumo["4"]["n"] == 10
    assert resumo["4"]["mediana"] == pytest.approx(5.5)
    assert resumo["4"]["p90"] == pytest.approx(9.1)
    assert resumo["8"]["mediana"] == pytest.approx(0.0)


def test_ponto_do_rotulo_fica_dentro_do_painel():
    """O número da corda cai dentro do painel, mesmo com a reta saindo por baixo."""
    x, y = ponto_do_rotulo(
        y_centro=300.0, theta=np.deg2rad(139.0), largura=655, altura=558
    )
    assert 25 <= x <= 655 - 25
    assert 25 <= y <= 558 - 25


def test_filtro_de_linha_tem_media_zero():
    """O núcleo de linha não responde a região lisa (média zero)."""
    nucleo = _filtro_de_linha(np.deg2rad(139.0))
    assert abs(float(nucleo.sum())) < 1e-3
    assert nucleo.shape == (41, 41)


def test_cresta_positiva_sobre_linha_clara_e_menor_fora():
    """A crista é maior sobre uma linha clara do que deslocada para fora dela."""
    cinza = np.full((200, 300), 40.0, np.float32)
    th = np.deg2rad(139.0)
    d = np.array([np.cos(th), np.sin(th)])
    p0 = np.array([150.0, 100.0])
    for t in np.linspace(-130, 130, 300):
        x, y = p0 + t * d
        cinza[round(float(y)), round(float(x))] = 220.0
    cinza = cv2.GaussianBlur(cinza, (3, 3), 0.8)
    sem_mao = np.zeros(cinza.shape, bool)
    sobre = cresta_da_reta(cinza, sem_mao, th, 100.0, 30.0)
    fora = cresta_da_reta(cinza, sem_mao, th, 100.0 + 15.0, 30.0)
    assert sobre is not None and fora is not None
    assert sobre > fora + 20


def test_refinar_reta_recupera_deslocamento_pequeno():
    """Uma reta deslocada 3 px volta para perto da linha clara real."""
    cinza = np.full((200, 300), 40.0, np.float32)
    th = np.deg2rad(139.0)
    d = np.array([np.cos(th), np.sin(th)])
    p0 = np.array([150.0, 100.0])
    for t in np.linspace(-130, 130, 300):
        x, y = p0 + t * d
        cinza[round(float(y)), round(float(x))] = 220.0
    cinza = cv2.GaussianBlur(cinza, (3, 3), 0.8)
    mascara = np.zeros(cinza.shape, bool)
    reta = {"theta": float(th), "y_centro": 103.0}
    refinada = refinar_reta([cinza], [mascara], reta, espacamento=30.0)
    assert abs(refinada["y_centro"] - 100.0) <= 1.0
    assert refinada["crista_depois"] >= refinada["crista_antes"]


def test_mascara_de_caixas_marca_a_mao():
    """A máscara cobre a caixa da mão, com folga."""
    m = mascara_de_caixas((100, 100), [(20, 20, 40, 40)], margem=2)
    assert m[30, 30]
    assert not m[70, 70]


def test_instantes_de_controle_longe_dos_ataques():
    """Os controles ficam a pelo menos 0,30 s de qualquer t_ini do produto."""
    ataques = [float(i) for i in range(0, 100, 5)]
    controles = instantes_de_controle(ataques, 0.0, 100.0, 10, semente=20261015)
    assert len(controles) == 10
    for c in controles:
        assert min(abs(c - a) for a in ataques) >= 0.30
    assert controles == instantes_de_controle(ataques, 0.0, 100.0, 10, 20261015)


def test_auc_separa_e_empata():
    """AUC 1 quando todo positivo passa todo negativo; 0,5 com listas iguais."""
    assert auc([3.0, 4.0], [1.0, 2.0]) == pytest.approx(1.0)
    assert auc([1.0, 2.0], [1.0, 2.0]) == pytest.approx(0.5)
    assert auc([], [1.0]) is None


def test_preditor_escolhe_a_reta_mais_proxima_do_dedo_que_mais_se_moveu():
    """A ponta 8 é a que mais se move; em -0,07 s ela cai na reta 3."""
    cordas = [
        {"corda": n, "a": 0.0, "b": 1.0, "c": 100.0 + 30.0 * n} for n in range(1, 7)
    ]
    pts_a = [[0.0, 0.0] for _ in range(21)]
    pts_b = [[0.0, 0.0] for _ in range(21)]
    pts_a[8] = [50.0, 190.0]
    pts_b[8] = [50.0, 230.0]
    ataque = {
        "t_ini": 5.0,
        "cordas_tab": [{"corda": 3, "casa": 2}],
        "quadros": [
            {"delta": -0.13, "direita": {"pts": pts_a}},
            {"delta": -0.07, "direita": {"pts": [[50.0, 190.0]] * 21}},
            {"delta": 0.07, "direita": {"pts": pts_b}},
        ],
    }
    ataque["quadros"][1]["direita"]["pts"][8] = [50.0, 190.0]
    previsao = preditor_ataque(ataque, cordas)
    assert previsao is not None
    assert previsao["dedo"] == 8
    assert previsao["corda_prevista"] == 3
    assert previsao["acerto"] is True


def test_corda_mais_frequente_ignora_instantes_excluidos():
    """A contagem não inclui as notas dos ataques avaliados."""
    notas = [
        {"corda": 1, "t_ini": 1.0},
        {"corda": 2, "t_ini": 2.0},
        {"corda": 2, "t_ini": 2.0},
        {"corda": 2, "t_ini": 3.0},
        {"corda": 1, "t_ini": 4.0},
    ]
    assert corda_mais_frequente(notas, [2.0, 3.0]) == 1
