"""Testes de ``tab.cruzar_fontes`` (cruzamento tela × som, rodada 2020)."""

import pytest

from tab.cruzamento.cruzar_fontes import colunas_do_produto, cruzar, cruzar_tela


def _nota(tela: int, coluna: int, corda: int, casa: object, x: float) -> dict:
    return {
        "tela": tela,
        "coluna": coluna,
        "corda": corda,
        "casa": casa,
        "x_centro_quadro": x,
    }


def _som(t: float, midi: int) -> dict:
    return {"t_ini": t, "t_fim": t + 0.3, "midi": midi, "velocidade": 80}


def test_colunas_do_produto_deduplica_passagens_e_aplica_capo() -> None:
    produto = {
        "notas": [
            _nota(1, 2, 1, 0, 200),
            _nota(1, 1, 6, 3, 100),
            _nota(1, 1, 6, 3, 100),  # a mesma nota em outra passagem
            _nota(1, 1, 5, "x", 100),  # casa não numérica: fora
        ]
    }
    colunas = colunas_do_produto(produto, capo=2)
    assert [[n["midi"] for n in c] for c in colunas[1]] == [[45], [66]]


def test_cruzar_tela_da_os_quatro_vereditos() -> None:
    colunas = colunas_do_produto(
        {
            "notas": [
                _nota(1, 1, 1, 0, 100),  # 64, ouvida
                _nota(1, 1, 2, 1, 100),  # 60, não ouvida no evento pareado
                _nota(1, 2, 1, 3, 200),  # 67, ouvida
                _nota(1, 3, 1, 12, 300),  # 76, coluna sem nada parecido no som
            ]
        },
        capo=0,
    )[1]
    som = [_som(1.0, 64), _som(1.01, 59), _som(1.5, 67), _som(2.0, 50)]
    r = cruzar_tela(colunas, som, [(0.9, 2.2)])
    vereditos = {(n["coluna"], n["corda"]): n["veredito"] for n in r["notas"]}
    assert vereditos == {
        (1, 1): "confirma",
        (1, 2): "nao_confirma",
        (2, 1): "confirma",
        (3, 1): "coluna_sem_par",
    }
    assert r["som_sem_tela"] == 1  # o 59 do primeiro evento


def test_cruzar_tela_sem_par_nenhum_e_sem_dado() -> None:
    colunas = colunas_do_produto({"notas": [_nota(1, 1, 1, 0, 100)]}, capo=0)[1]
    r = cruzar_tela(colunas, [_som(1.0, 50)], [(0.9, 1.5)])
    assert [n["veredito"] for n in r["notas"]] == ["sem_dado"]


def test_cruzar_recusa_videos_diferentes() -> None:
    with pytest.raises(ValueError):
        cruzar({"video": {"arquivo": "a.mp4"}}, {"video": "b.mp4", "notas": []}, 0, "")


def test_coluna_de_uma_nota_dentro_do_acorde_vizinho_e_ambigua() -> None:
    colunas = colunas_do_produto(
        {
            "notas": [
                _nota(1, 1, 1, 4, 100),  # 68: a "ponta da seta" antes do acorde
                _nota(1, 2, 1, 9, 200),  # 73
                _nota(1, 2, 2, 9, 200),  # 68
                _nota(1, 2, 3, 9, 200),  # 64
            ]
        },
        capo=0,
    )[1]
    som = [_som(1.0, 68), _som(1.0, 73), _som(1.0, 64)]
    som += [_som(1.5, 73), _som(1.5, 68), _som(1.5, 64)]
    r = cruzar_tela(colunas, som, [(0.9, 2.0)])
    vereditos = {(n["coluna"], n["corda"]): n["veredito"] for n in r["notas"]}
    assert vereditos[(1, 1)] == "ambigua"
    assert {vereditos[(2, c)] for c in (1, 2, 3)} == {"confirma"}


def test_acordes_iguais_vizinhos_continuam_confirmados() -> None:
    notas = [_nota(1, k, c, 0, 100 * k) for k in (1, 2) for c in (1, 2, 3)]
    colunas = colunas_do_produto({"notas": notas}, capo=0)[1]
    som = [_som(t, m) for t in (1.0, 1.5) for m in (64, 59, 55)]
    r = cruzar_tela(colunas, som, [(0.9, 2.0)])
    assert {n["veredito"] for n in r["notas"]} == {"confirma"}
