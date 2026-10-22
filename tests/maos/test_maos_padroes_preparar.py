"""Testes do preparo dos padrões da mão direita (M5): amostra, caixa, janela e página."""

from __future__ import annotations

import random
from pathlib import Path

from tab.maos.padroes_preparar import (
    MARGEM_S,
    MIN_NOTAS,
    amostrar_compassos,
    caixa_da_direita,
    caixa_par,
    caixas_da_direita,
    comando_clipe,
    compassos_tocados,
    escolher_pagina,
    janela_do_compasso,
    nome_do_item,
    notas_com_tempo,
)


def _nota(t: float, tela: int = 1, compasso: int = 1, exibicao: int = 0, **extra):
    """Nota mínima com tempo, para os testes."""
    nota = {
        "t_ini": t,
        "tela": tela,
        "compasso": compasso,
        "exibicao": exibicao,
        "corda": 1,
        "casa": 0,
        "x_quadro": 100,
    }
    nota.update(extra)
    return nota


def test_notas_com_tempo_descarta_sem_tempo_ou_sem_compasso():
    notas = [
        _nota(1.0),
        _nota(None),
        {"t_ini": 2.0, "tela": 1, "compasso": None, "exibicao": 0},
    ]
    assert [n["t_ini"] for n in notas_com_tempo(notas)] == [1.0]


def test_compassos_tocados_exige_minimo_de_notas():
    notas = [_nota(t, compasso=1) for t in (1.0, 1.2, 1.4)]  # 3 notas: entra
    notas += [_nota(t, compasso=2) for t in (5.0, 5.2)]  # 2 notas: fica de fora
    compassos = compassos_tocados(notas)
    assert MIN_NOTAS == 3
    assert [c["compasso"] for c in compassos] == [1]
    assert compassos[0]["n_notas"] == 3
    assert compassos[0]["t0"] == 1.0 and compassos[0]["t1"] == 1.4


def test_compassos_tocados_separa_exibicoes_do_mesmo_compasso():
    notas = [_nota(t, exibicao=0) for t in (1, 2, 3)]
    notas += [_nota(t, exibicao=1) for t in (10, 11, 12)]
    assert len(compassos_tocados(notas)) == 2


def _elegiveis(n: int) -> list[dict]:
    """Compassos sintéticos, um por tempo crescente."""
    notas = []
    for i in range(n):
        base = 10.0 * i
        notas += [_nota(base + k, compasso=i + 1) for k in (0.0, 0.2, 0.4)]
    return compassos_tocados(notas)


def test_amostra_e_determinista_e_estratificada():
    elegiveis = _elegiveis(40)
    a = amostrar_compassos(elegiveis, 10, random.Random(20261013))
    b = amostrar_compassos(elegiveis, 10, random.Random(20261013))
    assert [c["compasso"] for c in a] == [c["compasso"] for c in b]
    assert len(a) == 10
    # uma por faixa de 4 compassos: a k-ésima escolha cai em [4k, 4k+4)
    indices = [c["compasso"] - 1 for c in a]
    assert all(4 * k <= i < 4 * k + 4 for k, i in enumerate(indices))


def test_amostra_devolve_todos_se_faltarem_compassos():
    elegiveis = _elegiveis(4)
    assert len(amostrar_compassos(elegiveis, 10, random.Random(1))) == 4


def test_caixa_da_direita_usa_o_compasso_quando_ha_mao():
    instantes = [
        {"t_ini": 1.0, "maos": [{"lado": "direita", "caixa": [100, 100, 200, 200]}]},
        {"t_ini": 1.2, "maos": [{"lado": "direita", "caixa": [110, 100, 210, 200]}]},
        {"t_ini": 9.0, "maos": [{"lado": "direita", "caixa": [900, 0, 999, 50]}]},
        {"t_ini": 1.4, "maos": [{"lado": "esquerda", "caixa": [0, 0, 5, 5]}]},
    ]
    pares = caixas_da_direita(instantes)
    caixa, origem = caixa_da_direita([1.0, 1.2, 1.4], pares, 1.2)
    assert origem == "compasso"
    assert caixa == [105.0, 100.0, 205.0, 200.0]


def test_caixa_da_direita_cai_nos_mais_proximos_sem_mao_no_compasso():
    instantes = [
        {"t_ini": 50.0, "maos": [{"lado": "direita", "caixa": [10, 10, 20, 20]}]},
        {"t_ini": 51.0, "maos": [{"lado": "direita", "caixa": [30, 30, 40, 40]}]},
    ]
    pares = caixas_da_direita(instantes)
    caixa, origem = caixa_da_direita([1.0], pares, 1.0)
    assert origem == "proximos"
    assert caixa == [20.0, 20.0, 30.0, 30.0]


def test_caixa_da_direita_sem_nenhuma_mao():
    caixa, origem = caixa_da_direita([1.0], [], 1.0)
    assert caixa is None and origem == "sem_mao_direita"


def test_caixa_par_fica_no_quadro_com_lados_pares():
    x0, y0, x1, y1 = caixa_par([100.3, 200.0, 150.0, 260.0], (1920, 1080))
    assert 0 <= x0 < x1 <= 1920 and 0 <= y0 < y1 <= 1080
    assert (x1 - x0) % 2 == 0 and (y1 - y0) % 2 == 0


def test_caixa_par_respeita_a_borda_da_direita():
    x0, _, x1, _ = caixa_par([1900.0, 0.0, 1919.0, 50.0], (1920, 1080))
    assert x1 <= 1920 and (x1 - x0) % 2 == 0


def test_janela_tem_margem_e_respeita_a_duracao():
    assert janela_do_compasso(10.0, 12.0, None) == (10.0 - MARGEM_S, 12.0 + MARGEM_S)
    assert janela_do_compasso(0.1, 1.0, None)[0] == 0.0
    assert janela_do_compasso(10.0, 12.0, 11.0)[1] == 11.0


def test_comando_clipe_limita_entrada_e_dobra_o_lento():
    normal = comando_clipe(
        Path("v.mp4"), 1.0, 3.0, (0, 0, 10, 20), Path("o.mp4"), lento=False
    )
    lento = comando_clipe(
        Path("v.mp4"), 1.0, 3.0, (0, 0, 10, 20), Path("o.mp4"), lento=True
    )
    # o -t precisa vir ANTES do -i: depois dele corta o clipe lento pela metade
    assert normal.index("-t") < normal.index("-i")
    assert "crop=10:20:0:0" in normal
    assert "setpts=2*PTS" not in normal[normal.index("-vf") + 1]
    assert "setpts=2*PTS" in lento[lento.index("-vf") + 1]


def test_nome_do_item_tem_dois_digitos():
    assert nome_do_item(1) == "c01"
    assert nome_do_item(40) == "c40"


def test_escolher_pagina_pega_os_impares_de_cada_video():
    itens = [
        {"id": f"c{k:02d}", "video": "a.mp4" if k <= 10 else "b.mp4"}
        for k in range(1, 21)
    ]
    escolhidos = escolher_pagina(itens)
    assert escolhidos == {f"c{k:02d}" for k in (1, 3, 5, 7, 9, 11, 13, 15, 17, 19)}
    assert len(escolhidos) == 10
