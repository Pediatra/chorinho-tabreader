"""Testes da régua do produto (tab.avaliar_video), com dicionários feitos à mão.

Nenhum destes testes lê vídeo, GPU ou acervo. O cenário base tem uma tela (passo 16 px),
exibida de t=10 a t=50, com um acorde em t=12 (cordas 2 e 6 na mesma coluna x=224), uma
nota em t=20 (x=240) e outra em t=30 (x=300).
"""

from __future__ import annotations

import copy

import pytest

from tab.avaliar_video import (
    NotaPrevista,
    avaliar,
    casar_legado,
    casar_telas,
    coluna_atual,
    coluna_do_ouro,
    escolher_tela_legado,
    ler_predicao,
    linhas_do_relatorio,
    notas_distintas,
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


def test_formato_legado_avalia_na_janela_transcrita():
    # Ajustado: antes o legado tinha exibição = vídeo inteiro (o defeito). Agora a exibição
    # é a janela gravada pelo transcrever, que cobre os instantes de tempo deste cenário.
    legado = {
        "passo": 16.0,
        "tempo": {"medido": True},
        "janela_s": [0.0, 100.0],
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


def _legado(notas: list[dict], **extra) -> dict:
    """Predição legada (uma tela, passo 16) com as notas dadas e campos extras."""
    dados = {"passo": 16.0, "tempo": {"medido": True}, "notas": notas}
    dados.update(extra)
    return dados


NOTAS_LEGADO = [
    {"corda": 2, "casa": "0", "x_quadro": 224, "t_ini": 12.0},
    {"corda": 6, "casa": "0", "x_quadro": 224, "t_ini": 12.0},
    {"corda": 3, "casa": "2", "x_quadro": 240, "t_ini": 20.0},
    {"corda": 1, "casa": "3", "x_quadro": 300, "t_ini": 30.0},
]


def test_legado_pareia_pelo_conteudo_e_nao_pelos_instantes():
    # A tela 1 do ouro tem os instantes (3 deles), mas nenhuma nota da predição. A tela 2
    # tem as 4 notas. Pareamento por instantes escolheria a 1; por conteúdo, a 2.
    ouro = {
        "video": "exemplo/video.mp4",
        "telas": [
            {
                "id": 1,
                "quadro_ref_s": 12.0,
                "notas": [{"corda": 1, "casa": 9, "x_quadro": 900}],
            },
            {
                "id": 2,
                "quadro_ref_s": 300.0,
                "notas": [
                    {"corda": 2, "casa": 0, "x_quadro": 224},
                    {"corda": 6, "casa": 0, "x_quadro": 224},
                    {"corda": 3, "casa": 2, "x_quadro": 240},
                    {"corda": 1, "casa": 3, "x_quadro": 300},
                ],
            },
        ],
        "instantes": [
            {"t": 12.0, "tela": 1, "coluna_x_quadro": 900},
            {"t": 13.0, "tela": 1, "coluna_x_quadro": 900},
            {"t": 14.0, "tela": 1, "coluna_x_quadro": 900},
            {"t": 20.0, "tela": 2, "coluna_x_quadro": 240},
        ],
    }
    rel = _rodar(ouro, _legado(NOTAS_LEGADO, janela_s=[0.0, 100.0]))
    assert rel["telas"]["pareamento"] == "por conteudo (legado)"
    assert rel["telas"]["mapa"] == {"1": None, "2": 0}
    assert rel["telas"]["casadas"] == 1
    assert rel["notas"]["total"]["casadas"] == 4


def test_legado_empate_de_notas_desempata_pelo_quadro_lido():
    # As duas telas do ouro casam as mesmas 4 notas. O quadro lido (239 s) está perto
    # do quadro_ref_s da tela 2, então a 2 vence, mesmo com id maior.
    notas_tela = [
        {"corda": 2, "casa": 0, "x_quadro": 224},
        {"corda": 6, "casa": 0, "x_quadro": 224},
        {"corda": 3, "casa": 2, "x_quadro": 240},
        {"corda": 1, "casa": 3, "x_quadro": 300},
    ]
    ouro = {
        "video": "exemplo/video.mp4",
        "telas": [
            {"id": 1, "quadro_ref_s": 10.0, "notas": copy.deepcopy(notas_tela)},
            {"id": 2, "quadro_ref_s": 240.0, "notas": copy.deepcopy(notas_tela)},
        ],
        "instantes": [{"t": 12.0, "tela": 1, "coluna_x_quadro": 224}],
    }
    predicao = ler_predicao(
        _legado(NOTAS_LEGADO, janela_s=[0.0, 300.0], quadro_lido_s=239.2)
    )
    assert casar_legado(ouro["telas"], predicao) == {1: None, 2: 0}
    # Sem referência de quadro, o empate cai no menor id.
    sem_ref = ler_predicao(_legado(NOTAS_LEGADO, janela_s=[0.0, 300.0]))
    assert casar_legado(ouro["telas"], sem_ref) == {1: 0, 2: None}


def test_legado_instante_fora_da_janela_e_json_sem_tempo_nao_erro():
    # A predição cobre só 10 a 40 s. O instante do ouro em t=60 tem coluna acesa (300),
    # e a predição não tem tela ali: é "sem tempo", não "erro".
    ouro = copy.deepcopy(OURO_BASE)
    ouro["instantes"].append({"t": 60.0, "tela": 1, "coluna_x_quadro": 300})
    rel = _rodar(ouro, _legado(NOTAS_LEGADO, janela_s=[10.0, 40.0]))
    classes = rel["tempo"]["classes"]
    assert classes["json_sem_tempo"] == 1
    assert classes["erro"] == 0
    assert classes["acerto"] == 3
    assert rel["exibicao_previsao"].startswith("janela_s 10.0 a 40.0")


def test_legado_sem_janela_declara_quadro_em_s_e_nao_vira_erro():
    # Sem janela_s, a exibição é só o instante quadro_em_s (12 s), e a saída diz isso.
    rel = _rodar(OURO_BASE, _legado(NOTAS_LEGADO, quadro_em_s=12.0))
    classes = rel["tempo"]["classes"]
    assert classes["erro"] == 0
    assert classes["acerto"] == 1  # só o instante t=12 está na exibição
    assert classes["json_sem_tempo"] == 2  # t=20 e t=30 caem fora
    assert "quadro_em_s 12.0 s" in rel["exibicao_previsao"]
    # linhas_do_relatorio recebe os caminhos que o main preenche.
    rel["ouro_caminho"] = "ouro.json"
    rel["predicao_caminho"] = "pred.json"
    assert "pareamento: tela do instante do ouro mais próximo" in "\n".join(
        linhas_do_relatorio(rel)
    )


def test_legado_janela_malformada_e_recusada():
    with pytest.raises(ValueError, match="janela_s"):
        ler_predicao(_legado(NOTAS_LEGADO, janela_s=[10.0]))


def test_v1_continua_pareando_por_instantes():
    rel = _rodar(OURO_BASE, _pred_v1())
    assert rel["telas"]["pareamento"] == "por instantes (v1)"
    assert rel["telas"]["mapa"] == {"1": 1}


def _ouro_duas_telas() -> dict:
    """Ouro com duas telas: a 1 tem o instante t=20 e a 2 tem as notas casadas pela predição."""
    return {
        "video": "exemplo/video.mp4",
        "telas": [
            {
                "id": 1,
                "quadro_ref_s": 100.0,
                "notas": [{"corda": 1, "casa": 9, "x_quadro": 900}],
            },
            {
                "id": 2,
                "quadro_ref_s": 300.0,
                "notas": [
                    {"corda": 2, "casa": 0, "x_quadro": 224},
                    {"corda": 6, "casa": 0, "x_quadro": 224},
                    {"corda": 3, "casa": 2, "x_quadro": 240},
                    {"corda": 1, "casa": 3, "x_quadro": 300},
                ],
            },
        ],
        "instantes": [
            {"t": 20.0, "tela": 1, "coluna_x_quadro": 900},
            {"t": 270.0, "tela": 2, "coluna_x_quadro": 240},
        ],
    }


def test_escolha_legado_ramo_pre_json_vence_os_outros():
    # Quadro lido 271,6 s está em [240, 306] da tela 1 do pre.json. O conteúdo daria a 2.
    pre = {
        "telas": [
            {"id": 1, "t_ini": 240.0, "t_fim": 306.0},
            {"id": 2, "t_ini": 308.0, "t_fim": 326.0},
        ]
    }
    ouro = _ouro_duas_telas()
    predicao = ler_predicao(_legado(NOTAS_LEGADO, quadro_lido_s=271.6))
    mapa, criterio = escolher_tela_legado(
        ouro["telas"], ouro["instantes"], predicao, pre
    )
    assert mapa == {1: 0, 2: None}
    assert criterio == "tela do pre.json em quadro_lido_s"


def test_escolha_legado_ramo_instante_mais_proximo_sem_pre():
    # Sem pre.json, o instante do ouro mais perto de 271,6 s (t=270, tela 2) decide.
    ouro = _ouro_duas_telas()
    predicao = ler_predicao(_legado(NOTAS_LEGADO, quadro_lido_s=271.6))
    mapa, criterio = escolher_tela_legado(
        ouro["telas"], ouro["instantes"], predicao, None
    )
    assert mapa == {1: None, 2: 0}
    assert criterio == "tela do instante do ouro mais próximo de quadro_lido_s"


def test_escolha_legado_pre_sem_o_quadro_cai_no_instante():
    # O pre.json não cobre 271,6 s, então vale o instante mais próximo.
    pre = {"telas": [{"id": 1, "t_ini": 0.0, "t_fim": 100.0}]}
    ouro = _ouro_duas_telas()
    predicao = ler_predicao(_legado(NOTAS_LEGADO, quadro_lido_s=271.6))
    mapa, criterio = escolher_tela_legado(
        ouro["telas"], ouro["instantes"], predicao, pre
    )
    assert mapa == {1: None, 2: 0}
    assert criterio.startswith("tela do instante")


def test_escolha_legado_ramo_conteudo_sem_quadro_nem_pre():
    # Sem quadro lido não há como usar pre nem instante: vale o conteúdo (tela 2).
    ouro = _ouro_duas_telas()
    ouro["instantes"] = []
    predicao = ler_predicao(_legado(NOTAS_LEGADO))
    mapa, criterio = escolher_tela_legado(
        ouro["telas"], ouro["instantes"], predicao, None
    )
    assert mapa == {1: None, 2: 0}
    assert criterio == "por conteudo (legado)"


def test_avaliar_declara_o_criterio_de_pareamento():
    ouro = _ouro_duas_telas()
    pre = {"telas": [{"id": 1, "t_ini": 240.0, "t_fim": 306.0}]}
    predicao = ler_predicao(
        _legado(NOTAS_LEGADO, quadro_lido_s=271.6, janela_s=[0, 500])
    )
    rel = avaliar(ouro, predicao, pre=pre)
    assert rel["telas"]["pareamento"] == "tela do pre.json em quadro_lido_s"
    assert rel["telas"]["mapa"] == {"1": 0, "2": None}


def _predicao_duas_exibicoes() -> object:
    """Predição v1 com a tela 1 em [10, 50] e a tela 2 em [60, 80]."""
    return ler_predicao(
        {
            "esquema": "chorinho/video@1",
            "telas": [
                {"id": 1, "passo": 16.0, "exibicoes": [{"t0": 10, "t1": 50}]},
                {"id": 2, "passo": 16.0, "exibicoes": [{"t0": 60, "t1": 80}]},
            ],
            "notas": [],
        }
    )


def test_tela_do_ouro_sem_instante_pareia_pelo_quadro_ref():
    # A tela 2 do ouro não tem instante; o quadro_ref_s (70 s) cai na exibição da tela 2.
    ouro = {
        "video": "x.mp4",
        "telas": [
            {"id": 1, "quadro_ref_s": 20.0, "notas": []},
            {"id": 2, "quadro_ref_s": 70.0, "notas": []},
        ],
        "instantes": [{"t": 12.0, "tela": 1, "coluna_x_quadro": None}],
    }
    rel = avaliar(ouro, _predicao_duas_exibicoes())
    assert rel["telas"]["mapa"] == {"1": 1, "2": 2}
    assert rel["telas"]["criterio"] == {"1": "instantes", "2": "quadro_ref_s"}
    assert "quadro_ref_s" in rel["telas"]["pareamento"]


def test_tela_do_ouro_sem_instante_fora_das_exibicoes_fica_sem_par():
    ouro = {
        "video": "x.mp4",
        "telas": [{"id": 1, "quadro_ref_s": 100.0, "notas": []}],
        "instantes": [{"t": 12.0, "tela": 1, "coluna_x_quadro": None}],
    }
    rel = avaliar(ouro, _predicao_duas_exibicoes())
    assert rel["telas"]["mapa"] == {"1": 1}
    assert rel["telas"]["criterio"] == {"1": "instantes"}
    ouro_sem_instante = {
        "video": "x.mp4",
        "telas": [{"id": 3, "quadro_ref_s": 100.0, "notas": []}],
        "instantes": [],
    }
    rel2 = avaliar(ouro_sem_instante, _predicao_duas_exibicoes())
    assert rel2["telas"]["mapa"] == {"3": None}
    assert rel2["telas"]["criterio"] == {"3": None}


def test_quadro_ref_nao_reusa_tela_prevista_ja_casada():
    # As duas telas do ouro caem na exibição da tela prevista 1; só a primeira pareia.
    ouro = {
        "video": "x.mp4",
        "telas": [
            {"id": 1, "quadro_ref_s": 20.0, "notas": []},
            {"id": 2, "quadro_ref_s": 25.0, "notas": []},
        ],
        "instantes": [{"t": 12.0, "tela": 1, "coluna_x_quadro": None}],
    }
    rel = avaliar(ouro, _predicao_duas_exibicoes())
    assert rel["telas"]["mapa"] == {"1": 1, "2": None}


def test_notas_distintas_conta_cada_nota_uma_vez():
    # Uma nota por (corda, x): a segunda passagem da mesma nota não conta de novo.
    notas = [
        NotaPrevista(corda=3, casa=2, x=240.0, t_ini=20.0),
        NotaPrevista(corda=3, casa=2, x=240.0, t_ini=40.0),
        NotaPrevista(corda=3, casa=2, x=300.0, t_ini=40.0),
        NotaPrevista(corda=2, casa=2, x=240.0, t_ini=40.0),
    ]
    distintas = notas_distintas(notas)
    assert [(n.corda, n.x, n.t_ini) for n in distintas] == [
        (3, 240.0, 20.0),
        (3, 300.0, 40.0),
        (2, 240.0, 40.0),
    ]


def test_notas_distintas_sem_x_nao_deduplica():
    # Sem x não há como saber se duas entradas são a mesma nota: ficam as duas.
    notas = [
        NotaPrevista(corda=3, casa=2, x=None, t_ini=20.0),
        NotaPrevista(corda=3, casa=2, x=None, t_ini=40.0),
    ]
    assert len(notas_distintas(notas)) == 2


def test_passagem_repetida_nao_inventa_nota():
    # A mesma nota (corda 3, x 240) nas passagens t=20 e t=40: uma nota, não duas.
    notas = [*_pred_v1()["notas"], _nota(3, 2, 240, 40.0)]
    rel = _rodar(OURO_BASE, _pred_v1(notas))
    total = rel["notas"]["total"]
    assert total["entregues"] == 4
    assert total["casadas"] == 4
    assert total["inventadas"] == 0
    assert total["precisao"] == 1.0
    assert total["revocacao"] == 1.0


def test_passagem_repetida_nao_muda_o_tempo():
    # O tempo usa todas as entradas: a entrada extra não altera a classificação.
    base = _rodar(OURO_BASE, _pred_v1())["tempo"]
    notas = [*_pred_v1()["notas"], _nota(3, 2, 240, 40.0)]
    repetido = _rodar(OURO_BASE, _pred_v1(notas))["tempo"]
    assert repetido["classes"] == base["classes"]
    assert repetido["estado_certo"] == base["estado_certo"] == 3


def _rodar_com_fps(ouro: dict, pred: dict, fps: float | None) -> dict:
    """Valida, lê e avalia com o fps dado (``None`` desliga a regra de 1 quadro)."""
    validar_ouro(ouro)
    return avaliar(ouro, ler_predicao(pred), fps=fps)


def _ouro_com_instante(t: float, coluna: float) -> dict:
    """Ouro do cenário base com um único instante, na tela 1."""
    ouro = copy.deepcopy(OURO_BASE)
    ouro["instantes"] = [{"t": t, "tela": 1, "coluna_x_quadro": coluna}]
    return ouro


def test_rotulo_ate_um_quadro_antes_da_coluna_passa():
    # Coluna 240 começa em t=20.0; a 30 fps um quadro é 0,0333 s. Rótulo em 19,98 cai dentro.
    rel = _rodar_com_fps(_ouro_com_instante(19.98, 240), _pred_v1(), 30.0)
    assert rel["tempo"]["classes"]["acerto_quadro"] == 1
    assert rel["tempo"]["estado_certo"] == 1
    assert rel["tempo"]["classes"]["erro"] == 0


def test_rotulo_dois_quadros_antes_da_coluna_nao_passa():
    # 19,93 está a dois quadros (0,0667 s) de 20,0: fora da regra.
    rel = _rodar_com_fps(_ouro_com_instante(19.93, 240), _pred_v1(), 30.0)
    assert rel["tempo"]["classes"]["acerto_quadro"] == 0
    assert rel["tempo"]["classes"]["erro"] == 1


def test_rotulo_um_quadro_antes_com_coluna_errada_nao_passa():
    # Dentro de 1 quadro antes de 20,0, mas o ouro diz outra coluna (300): continua erro.
    rel = _rodar_com_fps(_ouro_com_instante(19.99, 300), _pred_v1(), 30.0)
    assert rel["tempo"]["classes"]["acerto_quadro"] == 0
    assert rel["tempo"]["classes"]["erro"] == 1


def test_regra_de_quadro_com_fps_desconhecido_fica_desligada():
    rel = _rodar_com_fps(_ouro_com_instante(19.98, 240), _pred_v1(), None)
    assert rel["tempo"]["classes"]["acerto_quadro"] == 0
    assert rel["tempo"]["classes"]["erro"] == 1
    assert rel["quadro_s"] is None


def test_inicio_fora_da_grade_e_posto_no_quadro_nativo():
    # Início 20,02 s é amostra; a 30 fps o quadro nativo é round(600,6)=601, em 20,0333 s.
    # O rótulo em 20,0 cai exatamente 1 quadro antes dele: passa.
    pred = _pred_v1(
        [
            _nota(2, 0, 224, 12.0),
            _nota(6, 0, 224, 12.0),
            _nota(3, 2, 240, 20.02),
            _nota(1, 3, 300, 30.0),
        ]
    )
    rel = _rodar_com_fps(_ouro_com_instante(20.0, 240), pred, 30.0)
    assert rel["tempo"]["classes"]["acerto_quadro"] == 1


def test_coluna_do_ouro_leva_o_clique_do_cursor_para_a_coluna():
    """Cursor fino antes da coluna (pablo romé): clique 17 px à esquerda, passo 24."""
    xs = [1204.5, 1291.2, 1382.0]
    assert coluna_do_ouro(1274.5, xs, 24.4) == 1291.2


def test_coluna_do_ouro_longe_de_toda_coluna_fica_como_esta():
    """A mais de um passo de toda nota do ouro, o clique vale como está."""
    assert coluna_do_ouro(1240.0, [1204.5, 1291.2], 24.4) == 1240.0
    assert coluna_do_ouro(1240.0, [], 24.4) == 1240.0
    assert coluna_do_ouro(1240.0, [1241.0], 0.0) == 1240.0
