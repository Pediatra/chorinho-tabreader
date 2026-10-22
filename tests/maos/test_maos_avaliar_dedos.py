"""Testes do avaliador dos dedos (M3): ``tab.maos_avaliar_dedos``.

Cobre a exclusão por id e por ataque duplicado, a dedup por ``indice_mvp``, o ``"?"``
fora da conta de cada mão, a cobertura, a acurácia nas pisadas, a matriz de confusão
e a validação da predição. Os gabaritos são pequenos e escritos à mão; nada aqui lê o
acervo nem o gabarito real.
"""

import json

import pytest

from tab.maos import avaliar_dedos as av


def _nota(
    id_: str,
    indice: int,
    esquerda: str,
    direita: str,
    ataque: str = "a01",
    sorteada: bool = True,
    corda: int = 3,
    casa: int = 2,
) -> dict:
    """Entrada do gabarito no formato 3, com os campos que o avaliador lê."""
    return {
        "id": id_,
        "ataque": ataque,
        "sorteada": sorteada,
        "indice_mvp": indice,
        "corda": corda,
        "casa": casa,
        "t_ini": 1.0,
        "esquerda": esquerda,
        "direita": direita,
        "obs": "",
    }


def _gabarito(notas: list[dict], excluir=None, duplicadas=None) -> dict:
    """Gabarito mínimo: as notas e a seção ``confiabilidade``."""
    return {
        "notas": notas,
        "confiabilidade": {
            "excluir": excluir or {},
            "duplicadas": duplicadas or {},
        },
    }


def test_exclui_nota_listada_em_excluir():
    gab = _gabarito(
        [_nota("n01", 10, "1", "p"), _nota("n19", 11, "2", "i")],
        excluir={"n19": "casa não apertada"},
    )
    notas, meta = av.notas_fisicas(gab)
    assert [n["id"] for n in notas] == ["n01"]
    assert meta["contagem"]["excluidas_por_id"] == ["n19"]
    assert meta["contagem"]["notas_no_gabarito"] == 2
    assert meta["contagem"]["notas_fisicas"] == 1


def test_exclui_ataque_duplicado_inteiro():
    gab = _gabarito(
        [
            _nota("n21", 20, "4", "a", ataque="a21"),
            _nota("n22", 20, "?", "?", ataque="a22", sorteada=False),
            _nota("n22b", 21, "0", "p", ataque="a22"),
        ],
        duplicadas={"a22": "mesmo ataque que a21"},
    )
    notas, meta = av.notas_fisicas(gab)
    assert [n["id"] for n in notas] == ["n21"]
    assert meta["contagem"]["excluidas_por_ataque_duplicado"] == ["n22", "n22b"]


def test_dedup_mantem_a_sorteada_e_avisa_quando_respostas_diferem():
    gab = _gabarito(
        [
            _nota("x_nao", 7, "2", "m", sorteada=False),
            _nota("x_sort", 7, "3", "i", sorteada=True),
        ]
    )
    notas, meta = av.notas_fisicas(gab)
    assert len(notas) == 1
    assert notas[0]["id"] == "x_sort"
    assert len(meta["avisos"]) == 1
    assert "7" in meta["avisos"][0]


def test_dedup_sem_aviso_quando_respostas_iguais():
    gab = _gabarito(
        [
            _nota("x_nao", 7, "2", "m", sorteada=False),
            _nota("x_sort", 7, "2", "m", sorteada=True),
        ]
    )
    notas, meta = av.notas_fisicas(gab)
    assert [n["id"] for n in notas] == ["x_sort"]
    assert meta["avisos"] == []


def test_interrogacao_sai_so_da_conta_da_mao_dela():
    gab = _gabarito([_nota("n01", 1, "?", "p"), _nota("n02", 2, "1", "?")])
    notas, _ = av.notas_fisicas(gab)
    pred = av.montar_predicao("teste", {1: ("1", "p"), 2: ("1", "m")})
    rel = av.avaliar(gab, pred)
    assert rel["esquerda"]["n_validas"] == 1
    assert rel["direita"]["n_validas"] == 1
    assert len(notas) == 2


def test_cobertura_e_acerto_total_contam_none_como_erro():
    gab = _gabarito([_nota("n01", 1, "1", "p"), _nota("n02", 2, "2", "m")])
    pred = av.montar_predicao("teste", {1: ("1", "p"), 2: (None, None)})
    rel = av.avaliar(gab, pred)
    esq = rel["esquerda"]
    assert esq["decididas"] == 1
    assert esq["cobertura"] == pytest.approx(0.5)
    assert esq["acerto_total"] == pytest.approx(0.5)
    assert esq["acerto_entre_decididas"] == pytest.approx(1.0)
    assert {e["id"] for e in esq["erros"]} == {"n02"}
    assert esq["erros"][0]["predito"] is None


def test_acerto_nas_pisadas_ignora_corda_solta():
    gab = _gabarito(
        [
            _nota("n01", 1, "0", "p"),
            _nota("n02", 2, "1", "m"),
            _nota("n03", 3, "2", "a"),
        ]
    )
    pred = av.montar_predicao(
        "teste",
        {1: ("0", "p"), 2: ("1", "m"), 3: ("3", "a")},
    )
    esq = av.avaliar(gab, pred)["esquerda"]
    assert esq["n_validas"] == 3
    assert esq["n_pisadas"] == 2
    assert esq["acertos"] == 2
    assert esq["acerto_total"] == pytest.approx(2 / 3)
    assert esq["acertos_pisadas"] == 1
    assert esq["acerto_pisadas"] == pytest.approx(0.5)


def test_matriz_de_confusao_conta_predito_e_nao_decidido():
    gab = _gabarito([_nota("n01", 1, "2", "m"), _nota("n02", 2, "1", "p")])
    pred = av.montar_predicao("teste", {1: ("3", "m"), 2: (None, "p")})
    matriz = av.avaliar(gab, pred)["esquerda"]["matriz"]
    assert matriz["2"]["3"] == 1
    assert matriz["1"]["-"] == 1
    assert matriz["1"]["1"] == 0


def test_relatorio_da_direita_sempre_traz_o_aviso_parcial():
    gab = _gabarito([_nota("n01", 1, "1", "p")])
    pred = av.montar_predicao("teste", {1: ("1", "p")})
    texto = av.relatorio_markdown(av.avaliar(gab, pred))
    assert av.AVISO_DIREITA in texto
    assert "gabarito parcial (inferido em parte)" in texto


def test_montar_predicao_recusa_nome_de_metodo_invalido():
    with pytest.raises(ValueError):
        av.montar_predicao("Regra X", {})


def test_carregar_predicao_recusa_resposta_fora_do_vocabulario(tmp_path):
    arquivo = tmp_path / "pred.json"
    arquivo.write_text(
        json.dumps({"metodo": "teste", "notas": {"1": {"esquerda": "?"}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        av.carregar_predicao(arquivo)


def test_carregar_predicao_aceita_none_como_nao_decidido(tmp_path):
    arquivo = tmp_path / "pred.json"
    arquivo.write_text(
        json.dumps(
            {"metodo": "teste", "notas": {"1": {"esquerda": None, "direita": "a"}}}
        ),
        encoding="utf-8",
    )
    pred = av.carregar_predicao(arquivo)
    assert pred["notas"]["1"]["esquerda"] is None
