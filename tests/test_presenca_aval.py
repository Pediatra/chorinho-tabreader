"""Funções puras da medição de presença (``tab.presenca_aval``): sem acervo, sem GPU."""

from tab.presenca_aval import classe, fps, matriz, por_quadro, resumir


def test_classe_cobre_as_quatro_celulas_e_ignora_duvida():
    assert classe(True, "tablatura") == "VP"
    assert classe(True, "nao_tablatura") == "FP"
    assert classe(False, "tablatura") == "FN"
    assert classe(False, "nao_tablatura") == "VN"
    assert classe(True, "duvida") is None
    assert classe(False, "duvida") is None


def test_matriz_calcula_precisao_e_revocacao_e_trata_denominador_zero():
    m = matriz(["VP", "VP", "FP", "FN", "VN", None])
    assert (m["VP"], m["FP"], m["VN"], m["FN"]) == (2, 1, 1, 1)
    assert m["precisao"] == round(2 / 3, 3)
    assert m["revocacao"] == round(2 / 3, 3)
    vazia = matriz([])
    assert vazia["precisao"] is None and vazia["revocacao"] is None


def test_resumir_separa_por_canal_e_fps_lista_so_os_falsos_positivos():
    casos = [
        {"canal": "a", "rotulo": "tablatura", "presenca": True},
        {"canal": "a", "rotulo": "nao_tablatura", "presenca": True},
        {"canal": "b", "rotulo": "nao_tablatura", "presenca": False},
        {"canal": "b", "rotulo": "duvida", "presenca": True},
    ]
    r = resumir(casos, "presenca")
    assert r["total"]["FP"] == 1 and r["total"]["VP"] == 1
    assert r["por_canal"]["a"]["FP"] == 1
    assert r["por_canal"]["b"]["VN"] == 1
    assert [c["canal"] for c in fps(casos, "presenca")] == ["a"]


def test_por_quadro_conta_quadro_uma_vez_e_usa_tablatura_se_algum_recorte_tem():
    quadro_mv = {"video": "v", "t_s": 1.0, "canal": "a", "presenca": True}
    casos = [
        {**quadro_mv, "rotulo": "tablatura"},
        {**quadro_mv, "rotulo": "nao_tablatura"},
        {
            "video": "v",
            "t_s": 2.0,
            "canal": "a",
            "presenca": True,
            "rotulo": "nao_tablatura",
        },
        {
            "video": "v",
            "t_s": 2.0,
            "canal": "a",
            "presenca": True,
            "rotulo": "nao_tablatura",
        },
    ]
    r = por_quadro(casos, "presenca")
    assert r["quadros"] == 2
    assert (r["total"]["VP"], r["total"]["FP"]) == (1, 1)
