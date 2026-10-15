"""Funções puras da etapa de recorte por vídeo (sem vídeo e sem acervo)."""

import copy
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from tab import partitura_video
from tab.musicxml import midi_da_corda
from tab.partitura_avaliar import SEMITONS_ESCRITA
from tab.partitura_pareamento import EventoPartitura, EventoTab, parear
from tab.partitura_pauta import Pauta
from tab.partitura_video import (
    agrupar_paginas,
    assinatura,
    diferenca,
    eventos_do_produto,
    instante_da_tela,
    ler,
    pasta_omr,
    pauta_acima_da_tab,
    reparear_por_x,
)


def _pauta(y_base: int, sem_pauta: bool = False) -> dict:
    """Entrada de pauta com 5 linhas espaçadas de 10 px a partir de ``y_base``."""
    ys = [y_base + 10 * k for k in range(5)]
    return {"sem_pauta": sem_pauta, "ys": ys, "id": f"R{y_base:03d}"}


def test_instante_usa_primeira_exibicao_valida():
    """O instante é o ponto médio da primeira exibição com ``t1 > t0``."""
    tela = {
        "exibicoes": [
            {"t0": 10.0, "t1": 20.0},
            {"t0": 30.0, "t1": 40.0},
        ]
    }
    assert instante_da_tela(tela) == 15.0


def test_instante_pula_exibicao_com_t1_menor_ou_igual_t0():
    """Exibições com ``t1 <= t0`` são puladas; vale a primeira válida depois delas."""
    tela = {
        "exibicoes": [
            {"t0": 50.0, "t1": 50.0},
            {"t0": 60.0, "t1": 40.0},
            {"t0": 70.0, "t1": 80.0},
        ]
    }
    assert instante_da_tela(tela) == 75.0


def test_instante_sem_exibicoes_devolve_none():
    """Tela sem exibições (ou só com exibições inválidas) não tem instante."""
    assert instante_da_tela({"exibicoes": []}) is None
    assert instante_da_tela({}) is None
    assert instante_da_tela({"exibicoes": [{"t0": 5.0, "t1": 5.0}]}) is None


def test_pauta_acima_escolhe_a_de_maior_ys4_acima_do_painel():
    """Entre as pautas acima do topo do painel, vence a mais próxima dele."""
    painel = [0, 300, 640, 420]
    entradas = [_pauta(50), _pauta(150), _pauta(250)]
    escolhida = pauta_acima_da_tab(entradas, painel, 20.0)
    assert escolhida is not None
    assert escolhida["ys"][4] == 290


def test_pauta_acima_ignora_pautas_dentro_das_cordas_da_tab():
    """Pauta que termina abaixo de ``base do painel - 5 passos`` não é candidata."""
    painel = [0, 300, 640, 420]
    entradas = [_pauta(100), _pauta(320)]
    escolhida = pauta_acima_da_tab(entradas, painel, 20.0)
    assert escolhida is not None
    assert escolhida["ys"][0] == 100


def test_pauta_acima_ignora_entradas_sem_pauta():
    """Entradas marcadas como ``sem_pauta`` nunca são escolhidas."""
    painel = [0, 300, 640, 420]
    entradas = [_pauta(200, sem_pauta=True), _pauta(100)]
    escolhida = pauta_acima_da_tab(entradas, painel, 20.0)
    assert escolhida is not None
    assert escolhida["ys"][0] == 100


def test_pauta_acima_sem_candidata_devolve_none():
    """Quando nenhuma pauta está acima do painel, devolve ``None``."""
    painel = [0, 300, 640, 420]
    assert pauta_acima_da_tab([], painel, 20.0) is None
    assert pauta_acima_da_tab([_pauta(400)], painel, 20.0) is None
    assert pauta_acima_da_tab([_pauta(100, sem_pauta=True)], painel, 20.0) is None


def test_pauta_acima_aceita_painel_que_comeca_acima_da_pauta():
    """Painel frouxo (cartão branco): a pauta dentro dele, acima das cordas, vale."""
    painel = [0, 50, 640, 420]
    escolhida = pauta_acima_da_tab([_pauta(200)], painel, 20.0)
    assert escolhida is not None
    assert escolhida["ys"][0] == 200


def _produto_falso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Produto com ``recortes/indice.json`` falso: T01 com pauta, T02 sem pauta."""
    monkeypatch.setattr(partitura_video, "PASTA_VIDEO", tmp_path)
    produto = tmp_path / "video_falso.json"
    recortes = tmp_path / "video_falso" / "recortes"
    recortes.mkdir(parents=True)
    indice = [
        {"id": "T01", "tela": 1, "video": "canal/v.mp4", "sem_pauta": False},
        {"id": "T02", "tela": 2, "sem_pauta": True, "motivo": "modo fora"},
    ]
    (recortes / "indice.json").write_text(json.dumps(indice), encoding="utf-8")
    return produto


def test_pasta_omr_fica_dentro_da_pasta_do_produto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pasta das leituras é ``omr`` dentro da pasta do produto."""
    produto = _produto_falso(tmp_path, monkeypatch)
    assert pasta_omr(produto) == tmp_path / "video_falso" / "omr"


def test_ler_id_desconhecido_levanta_antes_de_rodar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Id fora do índice, ou sem pauta, levanta ``ValueError`` e nada é lido."""

    def nao_deve_rodar(*_args: object, **_kwargs: object) -> dict:
        pytest.fail("rodar_um não podia ser chamado")

    monkeypatch.setattr(partitura_video, "rodar_um", nao_deve_rodar)
    produto = _produto_falso(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="T99"):
        ler(produto, ids=["T01", "T99"])
    with pytest.raises(ValueError, match="T02"):
        ler(produto, ids=["T02"])
    assert not pasta_omr(produto).exists()


def _nota_do_produto(
    coluna: int, corda: int, casa: object, x: float, tela: int = 1, passagem: int = 1
) -> dict:
    """Nota do produto, com só os campos que ``eventos_do_produto`` lê."""
    return {
        "tela": tela,
        "coluna": coluna,
        "corda": corda,
        "casa": casa,
        "x_centro_quadro": x,
        "passagem": passagem,
    }


def _altura_escrita(corda: int, casa: int) -> int:
    """Altura escrita da nota na afinação real, como o pareamento a calcula."""
    soado = midi_da_corda(corda, casa)
    assert soado is not None
    return soado + SEMITONS_ESCRITA


def test_eventos_do_produto_agrupa_por_coluna_e_une_passagens():
    """Mesma nota em duas passagens vira um evento com duas notas e uma altura."""
    notas = [
        _nota_do_produto(1, 1, 0, 100.0),
        _nota_do_produto(2, 2, 3, 200.0, passagem=1),
        _nota_do_produto(2, 2, 3, 200.0, passagem=2),
    ]
    eventos = eventos_do_produto(notas, 1, 0.0, 300.0)
    assert [e.indice for e in eventos] == [0, 1]
    assert [e.notas[0]["coluna"] for e in eventos] == [1, 2]
    assert len(eventos[1].notas) == 2
    assert len(eventos[1].midis) == 1
    assert eventos[1].midis == frozenset({_altura_escrita(2, 3)})
    assert eventos[0].midis == frozenset({_altura_escrita(1, 0)})


def test_eventos_do_produto_deixa_de_fora_janela_tela_e_casa_invalida():
    """Fora de [x0, x1], de outra tela ou com casa não inteira não entram."""
    notas = [
        _nota_do_produto(1, 1, 0, 100.0),
        _nota_do_produto(2, 1, 0, 400.0),
        _nota_do_produto(3, 1, 0, 50.0),
        _nota_do_produto(4, 1, 0, 150.0, tela=2),
        _nota_do_produto(5, 1, "x", 150.0),
    ]
    eventos = eventos_do_produto(notas, 1, 80.0, 300.0)
    assert len(eventos) == 1
    assert eventos[0].notas[0]["coluna"] == 1


def test_eventos_do_produto_ordena_por_coluna_mesmo_embaralhado():
    """A ordem dos eventos é a da coluna, qualquer que seja a ordem da lista."""
    notas = [
        _nota_do_produto(3, 2, 1, 150.0),
        _nota_do_produto(1, 1, 0, 100.0),
        _nota_do_produto(2, 3, 2, 120.0),
    ]
    eventos = eventos_do_produto(notas, 1, 0.0, 300.0)
    assert [e.notas[0]["coluna"] for e in eventos] == [1, 2, 3]
    assert [e.indice for e in eventos] == [0, 1, 2]


def test_eventos_do_produto_x_e_a_media_dos_x_do_grupo():
    """O x do evento é a média dos ``x_centro_quadro`` das notas do grupo."""
    notas = [
        _nota_do_produto(7, 1, 0, 100.0),
        _nota_do_produto(7, 2, 0, 110.0),
    ]
    eventos = eventos_do_produto(notas, 1, 0.0, 300.0)
    assert len(eventos) == 1
    assert eventos[0].x_quadro == 105.0
    assert eventos[0].midis == frozenset({_altura_escrita(1, 0), _altura_escrita(2, 0)})


def _evento_partitura(indice: int, x: float | None, midis: set[int]) -> EventoPartitura:
    """Evento da partitura com x e alturas dados (sem símbolos)."""
    return EventoPartitura(
        indice=indice,
        compasso=1,
        t=float(indice),
        t_global=float(indice),
        x_quadro=x,
        midis=frozenset(midis),
        simbolos=[],
    )


def _evento_tab(indice: int, x: float, midis: set[int], t_ini: float) -> EventoTab:
    """Evento da tab com x e alturas dados; a nota leva o ``t_ini`` dado."""
    nota = {"coluna": indice + 1, "t_ini": t_ini}
    return EventoTab(indice=indice, x_quadro=x, midis=frozenset(midis), notas=[nota])


def test_reparear_troca_para_coluna_proxima_em_x():
    """Par por altura contradito por x (200 px) troca para a coluna a 3 px."""
    partitura = [_evento_partitura(0, 100.0, {60})]
    tab = [
        _evento_tab(0, 300.0, {60}, 1.0),
        _evento_tab(1, 103.0, {72}, 2.0),
    ]
    pares = parear(partitura, tab, 19.0)
    assert pares[0]["par_tab"] == 0
    assert pares[0]["confere_x"] is False
    novos = reparear_por_x(partitura, tab, pares, 19.0)
    assert novos[0]["par_tab"] == 1
    assert novos[0]["confere_x"] is True
    assert novos[0]["distancia_x"] == 3.0
    assert novos[0]["t_ini"] == [2.0]
    assert novos[0]["metodo"] == "x"


def test_reparear_mantem_par_quando_coluna_mais_proxima_passa_da_tolerancia():
    """Coluna livre mais próxima a 50 px, com tolerância 19: fica o par por altura."""
    partitura = [_evento_partitura(0, 100.0, {60})]
    tab = [
        _evento_tab(0, 300.0, {60}, 1.0),
        _evento_tab(1, 150.0, {72}, 2.0),
    ]
    pares = parear(partitura, tab, 19.0)
    novos = reparear_por_x(partitura, tab, pares, 19.0)
    assert novos[0]["par_tab"] == 0
    assert novos[0]["confere_x"] is False
    assert novos[0]["metodo"] == "altura"


def test_reparear_nunca_pega_coluna_de_par_confirmado():
    """Coluna já segurada por par confirmado não é tomada, mesmo sendo a mais próxima."""
    partitura = [
        _evento_partitura(0, 100.0, {60}),
        _evento_partitura(1, 300.0, {62}),
        _evento_partitura(2, 101.0, {66}),
    ]
    tab = [
        _evento_tab(0, 101.0, {60}, 1.0),
        _evento_tab(1, 300.0, {62}, 2.0),
        _evento_tab(2, 102.0, {64}, 3.0),
        _evento_tab(3, 500.0, {66}, 4.0),
    ]
    pares = parear(partitura, tab, 19.0)
    assert [p["par_tab"] for p in pares] == [0, 1, 3]
    assert pares[2]["confere_x"] is False
    novos = reparear_por_x(partitura, tab, pares, 19.0)
    assert [p["par_tab"] for p in novos] == [0, 1, 2]
    assert novos[0]["metodo"] == "altura"
    assert novos[2]["metodo"] == "x"
    assert novos[2]["distancia_x"] == 1.0


def test_reparear_dois_candidatos_disputam_uma_coluna_vence_o_primeiro():
    """Dois candidatos querem a mesma coluna livre: o primeiro na ordem leva."""
    partitura = [
        _evento_partitura(0, 100.0, {60}),
        _evento_partitura(1, 105.0, {62}),
    ]
    tab = [
        _evento_tab(0, 102.0, {70}, 1.0),
        _evento_tab(1, 300.0, {60}, 2.0),
        _evento_tab(2, 400.0, {62}, 3.0),
    ]
    pares = parear(partitura, tab, 19.0)
    assert [p["par_tab"] for p in pares] == [1, 2]
    assert [p["confere_x"] for p in pares] == [False, False]
    novos = reparear_por_x(partitura, tab, pares, 19.0)
    assert [p["par_tab"] for p in novos] == [0, 2]
    assert novos[0]["metodo"] == "x"
    assert novos[1]["metodo"] == "altura"
    assert novos[1]["confere_x"] is False


def test_reparear_nao_altera_as_entradas():
    """A função devolve linhas novas: pares, partitura e tab ficam como estavam."""
    partitura = [
        _evento_partitura(0, 100.0, {60}),
        _evento_partitura(1, 200.0, {62}),
    ]
    tab = [
        _evento_tab(0, 300.0, {60}, 1.0),
        _evento_tab(1, 103.0, {72}, 2.0),
    ]
    pares = parear(partitura, tab, 19.0)
    antes = (copy.deepcopy(partitura), copy.deepcopy(tab), copy.deepcopy(pares))
    novos = reparear_por_x(partitura, tab, pares, 19.0)
    assert novos is not pares
    assert (partitura, tab, pares) == antes
    assert novos[0]["par_tab"] == 1


def _bits(*valores: int) -> np.ndarray:
    """Assinatura de teste: vetor booleano com os bits dados."""
    return np.array(valores, dtype=bool)


_A = _bits(1, 1, 0, 0, 0, 0, 0, 0)
_B = _bits(0, 0, 0, 0, 1, 1, 0, 0)
_X = _bits(0, 0, 0, 0, 0, 0, 1, 1)


def _amostras(
    sequencia: list[np.ndarray | None],
) -> list[tuple[float, np.ndarray | None]]:
    """Amostras em t = 0, 1, 2... para uma sequência de assinaturas (``None`` vale)."""
    return [(float(t), sinal) for t, sinal in enumerate(sequencia)]


def test_diferenca_de_identicas_e_disjuntas():
    """Iguais dão 0; disjuntas com tinta dão 1; duas vazias dão 0, sem divisão por zero."""
    assert diferenca(_A, _A.copy()) == 0.0
    assert diferenca(_A, _B) == 1.0
    assert diferenca(np.zeros(8, bool), np.zeros(8, bool)) == 0.0


def test_agrupar_paginas_com_repeticao():
    """A A A B B A A: duas páginas; a primeira tem duas exibições, a segunda uma."""
    paginas = agrupar_paginas(_amostras([_A, _A, _A, _B, _B, _A, _A]))
    assert [p["pagina"] for p in paginas] == [1, 2]
    assert paginas[0]["exibicoes"] == [{"t0": 0.0, "t1": 2.0}, {"t0": 5.0, "t1": 6.0}]
    assert paginas[1]["exibicoes"] == [{"t0": 3.0, "t1": 4.0}]


def test_agrupar_paginas_descarta_quadro_isolado():
    """A A X A A: o X sozinho é um corte e some; as duas exibições de A ficam."""
    paginas = agrupar_paginas(_amostras([_A, _A, _X, _A, _A]))
    assert len(paginas) == 1
    assert paginas[0]["exibicoes"] == [{"t0": 0.0, "t1": 1.0}, {"t0": 3.0, "t1": 4.0}]


def test_agrupar_paginas_none_no_meio_separa_sequencias():
    """Sem pauta (None) no meio, A A None A A vira duas exibições da mesma página."""
    paginas = agrupar_paginas(_amostras([_A, _A, None, _A, _A]))
    assert len(paginas) == 1
    assert paginas[0]["exibicoes"] == [{"t0": 0.0, "t1": 1.0}, {"t0": 3.0, "t1": 4.0}]


def test_agrupar_paginas_t_e_o_meio_da_exibicao_mais_longa():
    """Com exibições de 2 s e 5 s da mesma página, ``t`` é o meio da de 5 s."""
    sequencia = [_A, _A, _A, _B, _B, _A, _A, _A, _A, _A, _A]
    paginas = agrupar_paginas(_amostras(sequencia))
    assert paginas[0]["t"] == 7.5
    assert paginas[1]["t"] == 3.5


def test_agrupar_paginas_sem_amostras_validas():
    """Vazio, ou só com ``None``, não tem página."""
    assert agrupar_paginas([]) == []
    assert agrupar_paginas(_amostras([None, None, None])) == []


def _quadro_claro(largura: int = 400, altura: int = 300) -> np.ndarray:
    """Quadro BGR branco com 5 linhas de pauta e um bloco preto (uma nota)."""
    quadro = np.full((altura, largura, 3), 255, np.uint8)
    for y in (100, 110, 120, 130, 140):
        cv2.line(quadro, (50, y), (350, y), (0, 0, 0), 1)
    cv2.rectangle(quadro, (200, 112), (212, 128), (0, 0, 0), -1)
    return quadro


_PAUTA_DE_TESTE = Pauta(ys=(100, 110, 120, 130, 140), entrelinha=10.0, x0=50, x1=350)


def test_assinatura_sem_pauta_devolve_none():
    """Sem pauta não há região a assinar."""
    assert assinatura(_quadro_claro(), []) is None


def test_assinatura_tem_forma_fixa_e_tinta():
    """A assinatura tem 64 x 256 e marca a tinta (a nota) como verdadeira."""
    sig = assinatura(_quadro_claro(), [_PAUTA_DE_TESTE])
    assert sig is not None
    assert sig.shape == (64, 256)
    assert sig.dtype == bool
    assert sig.any()


def test_assinatura_fundo_escuro_igual_ao_claro_invertido():
    """O mesmo conteúdo com fundo escuro dá a mesma assinatura (polaridade invertida)."""
    claro = _quadro_claro()
    escuro = 255 - claro
    sig_claro = assinatura(claro, [_PAUTA_DE_TESTE])
    sig_escuro = assinatura(escuro, [_PAUTA_DE_TESTE])
    assert sig_claro is not None and sig_escuro is not None
    assert np.array_equal(sig_claro, sig_escuro)
