"""Testes da régua do produto (tab.avaliar_video), com dicionários feitos à mão.

Nenhum destes testes lê vídeo, GPU ou acervo. O cenário base tem uma tela (passo 16 px),
exibida de t=10 a t=50, com um acorde em t=12 (cordas 2 e 6 na mesma coluna x=224), uma
nota em t=20 (x=240) e outra em t=30 (x=300).
"""

from __future__ import annotations

import copy

import pytest

from tab.avaliar_video import (
    avaliar,
    casar_telas,
    coluna_atual,
    ler_predicao,
    linhas_do_relatorio,
    ocorrencias,
    tela_em_t,
    validar_ouro,
)

OURO_BASE = {
    "video": "exemplo/video.mp4",
    "como_foi_rotulado": "teste",
    "telas": [
        {
            "id": 1,
            "quadro_ref_s": 12.0,
            "notas": [
                {"corda": 2, "casa": 0, "x_quadro": 224},
                {"corda": 6, "casa": 0, "x_quadro": 224},
                {"corda": 3, "casa": 2, "x_quadro": 240},
                {"corda": 1, "casa": 3, "x_quadro": 300},
            ],
        }
    ],
    "instantes": [
        {"t": 12.0, "tela": 1, "coluna_x_quadro": 224},
        {"t": 20.0, "tela": 1, "coluna_x_quadro": 240},
        {"t": 30.0, "tela": 1, "coluna_x_quadro": 300},
        {"t": 5.0, "tela": None, "coluna_x_quadro": None, "obs": "sem tablatura"},
    ],
}


def _nota(corda: int, casa: int, x: float, t: float | None) -> dict:
    """Monta uma nota v1 da tela 1."""
    return {
        "tela": 1,
        "passagem": 1,
        "coluna": 1,
        "corda": corda,
        "casa": casa,
        "x_quadro": x,
        "t_ini": t,
    }


def _pred_v1(notas: list[dict] | None = None, medido: bool = True) -> dict:
    """Predição v1 com a tela 1 do cenário base."""
    if notas is None:
        notas = [
            _nota(2, 0, 224, 12.0),
            _nota(6, 0, 224, 12.0),
            _nota(3, 2, 240, 20.0),
            _nota(1, 3, 300, 30.0),
        ]
    return {
        "esquema": "chorinho/video@1",
        "video": {"arquivo": "exemplo/video.mp4"},
        "gerado_por": {"commit": "abc1234", "modelo": "artefatos/x/glifo_sint.pt"},
        "telas": [
            {
                "id": 1,
                "passo": 16.0,
                "exibicoes": [{"t0": 10.0, "t1": 50.0}],
                "tempo": {"medido": medido},
            }
        ],
        "notas": notas,
    }


def _rodar(ouro: dict, pred: dict) -> dict:
    """Valida, lê e avalia, como o ``main`` faz."""
    validar_ouro(ouro)
    return avaliar(ouro, ler_predicao(pred))


def test_caso_perfeito_tudo_um():
    rel = _rodar(OURO_BASE, _pred_v1())
    assert rel["telas"]["casadas"] == 1
    notas = rel["notas"]["total"]
    assert notas["notas_ouro"] == 4
    assert notas["casadas"] == 4
    assert notas["precisao"] == 1.0
    assert notas["revocacao"] == 1.0
    assert notas["inventadas"] == 0
    assert notas["acerto_casa"] == 1.0
    tempo = rel["tempo"]
    assert tempo["classes"]["acerto"] == 3
    assert tempo["classes"]["ausencia_certa"] == 1
    assert tempo["classes"]["tempo_falso"] == 0
    assert tempo["estado_certo"] == 3
    assert tempo["com_coluna"] == 3


def test_nota_inventada_sai_em_inventadas():
    notas = [*_pred_v1()["notas"], _nota(4, 5, 400, 40.0)]
    total = _rodar(OURO_BASE, _pred_v1(notas))["notas"]["total"]
    assert total["entregues"] == 5
    assert total["casadas"] == 4
    assert total["inventadas"] == 1
    assert total["precisao"] == 0.8


def test_nota_perdida_sai_em_perdidas():
    notas = _pred_v1()["notas"][:3]
    rel = _rodar(OURO_BASE, _pred_v1(notas))
    total = rel["notas"]["total"]
    assert total["perdidas"] == 1
    assert total["revocacao"] == 0.75
    # Sem a nota da corda 1 no t=30, a predição diz a coluna 240 e o ouro diz 300.
    assert rel["tempo"]["classes"]["erro"] == 1


def test_casa_errada_conta_casada_mas_nao_casa_certa():
    notas = _pred_v1()["notas"]
    notas[2] = _nota(3, 9, 240, 20.0)
    total = _rodar(OURO_BASE, _pred_v1(notas))["notas"]["total"]
    assert total["casadas"] == 4
    assert total["casa_certa"] == 3
    assert total["acerto_casa"] == 0.75


def test_acorde_e_uma_coluna_com_um_onset():
    tela = ler_predicao(_pred_v1()).telas[0]
    # As duas notas do acorde (cordas 2 e 6, x=224) caem na mesma coluna.
    indices_do_acorde = {idx for t, _, idx in ocorrencias(tela) if t == 12.0}
    assert len(indices_do_acorde) == 1
    atual = coluna_atual(12.0, tela, ocorrencias(tela))
    assert atual is not None
    assert atual.x == 224.0


def test_nenhuma_acesa_com_tempo_afirmado_e_tempo_falso():
    ouro = copy.deepcopy(OURO_BASE)
    ouro["instantes"].append({"t": 25.0, "tela": 1, "coluna_x_quadro": None})
    tempo = _rodar(ouro, _pred_v1())["tempo"]
    assert tempo["classes"]["tempo_falso"] == 1
    assert tempo["sem_coluna"] == 2
    assert tempo["classes"]["ausencia_certa"] == 1


def test_instante_dentro_da_tolerancia_aceita_coluna_anterior():
    ouro = copy.deepcopy(OURO_BASE)
    # Em t=20.1 a predição já é a coluna 240 (onset 20); o ouro ainda diz 224.
    ouro["instantes"] = [{"t": 20.1, "tela": 1, "coluna_x_quadro": 224}]
    tempo = _rodar(ouro, _pred_v1())["tempo"]
    assert tempo["classes"]["acerto_tolerancia"] == 1
    assert tempo["classes"]["erro"] == 0


def test_instante_fora_da_tolerancia_e_erro():
    ouro = copy.deepcopy(OURO_BASE)
    ouro["instantes"] = [{"t": 20.3, "tela": 1, "coluna_x_quadro": 224}]
    tempo = _rodar(ouro, _pred_v1())["tempo"]
    assert tempo["classes"]["erro"] == 1
    assert tempo["classes"]["acerto_tolerancia"] == 0


def test_formato_legado_avalia_como_uma_tela_inteira():
    legado = {
        "passo": 16.0,
        "tempo": {"medido": True},
        "notas": [
            {"corda": 2, "casa": "0", "x": 10, "x_quadro": 224, "t_ini": 12.0},
            {"corda": 6, "casa": "0", "x": 10, "x_quadro": 224, "t_ini": 12.0},
            {"corda": 3, "casa": "2", "x": 50, "x_quadro": 240, "t_ini": 20.0},
            {
                "corda": 1,
                "casa": "harmonico",
                "x": 90,
                "x_quadro": 300,
                "t_ini": 30.0,
            },
        ],
    }
    rel = _rodar(OURO_BASE, legado)
    assert rel["formato_predicao"] == "legado"
    assert rel["telas"]["previstas"] == 1
    total = rel["notas"]["total"]
    # O harmônico não é casa numérica: não é entregue, e a nota do ouro fica perdida.
    assert total["entregues"] == 3
    assert total["casadas"] == 3
    assert total["perdidas"] == 1
    assert rel["notas"]["total"]["notas_ouro"] == 4
    # Mas o harmônico ocupa a coluna 300 e o marcador passa por ela: acerto.
    assert rel["tempo"]["classes"]["acerto"] == 3


def test_legado_sem_x_quadro_nao_avalia_e_diz_por_que():
    legado = {
        "passo": 16.0,
        "tempo": {"medido": True},
        "notas": [{"corda": 2, "casa": "0", "x": 10, "t_ini": 12.0}],
    }
    rel = _rodar(OURO_BASE, legado)
    assert rel["notas"]["avaliavel"] is False
    assert "x_quadro" in rel["notas"]["motivo"]
    assert rel["tempo"]["avaliavel"] is False
    # Telas não dependem de x: continuam avaliadas.
    assert rel["telas"]["casadas"] == 1


def test_tempo_sem_medido_nao_afirma_coluna():
    tempo = _rodar(OURO_BASE, _pred_v1(medido=False))["tempo"]
    assert tempo["classes"]["json_sem_tempo"] == 3
    assert tempo["classes"]["tempo_falso"] == 0


def test_tela_do_ouro_casa_com_a_prevista_que_mais_aparece():
    predicao = ler_predicao(
        {
            "esquema": "chorinho/video@1",
            "telas": [
                {"id": 1, "passo": 16.0, "exibicoes": [{"t0": 10, "t1": 50}]},
                {"id": 2, "passo": 16.0, "exibicoes": [{"t0": 60, "t1": 80}]},
            ],
            "notas": [],
        }
    )
    instantes = [{"t": 12.0, "tela": 7}, {"t": 20.0, "tela": 7}, {"t": 65.0, "tela": 7}]
    assert casar_telas([7], instantes, predicao.telas) == {7: 1}
    assert tela_em_t(65.0, 7, {7: 1}, predicao.telas).id == 2


def test_coluna_atual_nao_usa_onset_de_outra_exibicao():
    # A tela sai e volta: o onset da primeira exibição não vale na segunda.
    dados = _pred_v1()
    dados["telas"][0]["exibicoes"] = [
        {"t0": 10.0, "t1": 22.0},
        {"t0": 60.0, "t1": 80.0},
    ]
    tela = ler_predicao(dados).telas[0]
    # Em t=65 a tela está na segunda exibição, e as notas (t=12, 20, 30) são da primeira.
    assert coluna_atual(65.0, tela, ocorrencias(tela)) is None


def test_ouro_com_coluna_acesa_sem_tela_e_recusado():
    ouro = copy.deepcopy(OURO_BASE)
    ouro["instantes"] = [{"t": 12.0, "tela": None, "coluna_x_quadro": 224}]
    with pytest.raises(ValueError, match="coluna acesa sem tela"):
        validar_ouro(ouro)


def test_avaliacao_e_reprodutivel():
    primeira = _rodar(OURO_BASE, _pred_v1())
    segunda = _rodar(OURO_BASE, _pred_v1())
    assert primeira == segunda


def test_ouro_com_x_centro_casa_pelo_centro_e_nao_pela_borda():
    """O ouro traz o centro 12 px à direita da borda: a régua usa o centro."""
    ouro = copy.deepcopy(OURO_BASE)
    for nota in ouro["telas"][0]["notas"]:
        nota["x_centro_quadro"] = nota["x_quadro"]
        nota["x_quadro"] -= 12
    rel = _rodar(ouro, _pred_v1())
    assert rel["notas"]["total"]["casadas"] == 4
    assert rel["x_fallback"]["ouro"] == 0
    assert rel["x_fallback"]["ouro_total"] == 4


def test_predicao_com_x_centro_casa_pelo_centro_e_nao_pela_borda():
    """A predição traz a borda 12 px deslocada: o centro é o que casa."""
    notas = [
        {**_nota(2, 0, 236, 12.0), "x_centro_quadro": 224.0},
        {**_nota(6, 0, 236, 12.0), "x_centro_quadro": 224.0},
        {**_nota(3, 2, 252, 20.0), "x_centro_quadro": 240.0},
        {**_nota(1, 3, 312, 30.0), "x_centro_quadro": 300.0},
    ]
    rel = _rodar(OURO_BASE, _pred_v1(notas))
    assert rel["notas"]["total"]["casadas"] == 4
    assert rel["x_fallback"]["previsao"] == 0
    assert rel["x_fallback"]["previsao_total"] == 4


def test_coluna_prevista_e_mediana_dos_centros():
    """Um acorde com bordas 207 e 209 tem centros 223 e 225: coluna 224, acerto."""
    ouro = copy.deepcopy(OURO_BASE)
    ouro["instantes"] = [{"t": 12.0, "tela": 1, "coluna_x_quadro": 224}]
    notas = [
        {**_nota(2, 0, 207, 12.0), "x_centro_quadro": 223.0},
        {**_nota(6, 0, 209, 12.0), "x_centro_quadro": 225.0},
    ]
    rel = _rodar(ouro, _pred_v1(notas))
    assert rel["tempo"]["classes"]["acerto"] == 1


def test_fallback_x_quadro_e_declarado_com_contagem():
    """Sem ``x_centro_quadro`` a régua usa a borda e declara quantas notas caíram nisso."""
    ouro = copy.deepcopy(OURO_BASE)
    ouro["telas"][0]["notas"][0]["x_centro_quadro"] = 224.0
    notas = [
        {**_nota(2, 0, 224, 12.0), "x_centro_quadro": 224.0},
        _nota(6, 0, 224, 12.0),
        _nota(3, 2, 240, 20.0),
        _nota(1, 3, 300, 30.0),
    ]
    rel = _rodar(ouro, _pred_v1(notas))
    assert rel["x_fallback"] == {
        "ouro": 3,
        "ouro_total": 4,
        "previsao": 3,
        "previsao_total": 4,
    }
    rel["ouro_caminho"], rel["predicao_caminho"] = "ouro.json", "pred.json"
    texto = "\n".join(linhas_do_relatorio(rel))
    assert "ouro 3 de 4 notas, predição 3 de 4 notas" in texto


def test_chaves_extras_do_ouro_nao_quebram():
    """``juntadas`` e ``ferramenta`` vêm do ouro e a régua as ignora."""
    ouro = copy.deepcopy(OURO_BASE)
    ouro["juntadas"] = {"2": 1}
    ouro["ferramenta"] = "ignorar"
    rel = _rodar(ouro, _pred_v1())
    assert rel["telas"]["ouro"] == 1
    assert rel["notas"]["total"]["casadas"] == 4
