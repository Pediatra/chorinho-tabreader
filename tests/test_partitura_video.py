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
    caminho_da_pasta,
    diferenca,
    e_tablatura,
    eventos_do_produto,
    instante_da_tela,
    ler,
    ler_pasta,
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


def _pagina_de_teste(t: float, *exibicoes: tuple[float, float]) -> dict:
    """Página de teste com ``t`` e as exibições ``(t0, t1)`` dadas."""
    return {
        "pagina": 1,
        "t": t,
        "exibicoes": [{"t0": a, "t1": b} for a, b in exibicoes],
    }


def test_escolher_instante_maior_contagem_ganha():
    """Entre as amostras dentro da exibição, a de mais pautas vence, mesmo longe de t."""
    pagina = _pagina_de_teste(5.0, (0.0, 10.0))
    contagens = [(1.0, 1), (4.0, 1), (5.0, 1), (9.0, 2)]
    assert partitura_video.escolher_instante(pagina, contagens) == 9.0


def test_escolher_instante_empate_fica_com_o_mais_perto_de_t():
    """Duas amostras com a mesma contagem: a mais perto do ``t`` original vence."""
    pagina = _pagina_de_teste(5.0, (0.0, 10.0))
    contagens = [(2.0, 2), (6.0, 2), (9.0, 2)]
    assert partitura_video.escolher_instante(pagina, contagens) == 6.0


def test_escolher_instante_ignora_amostra_fora_das_exibicoes():
    """Uma amostra com mais pautas, mas fora de qualquer exibição, não conta."""
    pagina = _pagina_de_teste(5.0, (0.0, 3.0), (7.0, 8.0))
    contagens = [(1.0, 1), (5.0, 4), (7.5, 2)]
    assert partitura_video.escolher_instante(pagina, contagens) == 7.5


def test_escolher_instante_sem_amostra_dentro_devolve_t_original():
    """Sem nenhuma amostra nas exibições, devolve o ``t`` da página."""
    pagina = _pagina_de_teste(5.0, (0.0, 3.0))
    contagens = [(4.0, 3), (9.0, 3)]
    assert partitura_video.escolher_instante(pagina, contagens) == 5.0
    assert partitura_video.escolher_instante(pagina, []) == 5.0


def test_escolher_instante_limites_da_exibicao_contam():
    """``t0`` e ``t1`` são inclusivos: amostras nas bordas entram na escolha."""
    pagina = _pagina_de_teste(5.0, (2.0, 4.0))
    contagens = [(2.0, 1), (4.0, 3)]
    assert partitura_video.escolher_instante(pagina, contagens) == 4.0


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


def _quadro_com_destaque(
    cor: tuple[int, int, int] | None, cursor: bool = False
) -> np.ndarray:
    """Quadro BGR com a pauta e duas notas pretas; ``cor`` vai atrás das notas e linhas.

    ``cursor`` põe uma barra vertical vermelha por cima das linhas, como o cursor de
    reprodução do vídeo.
    """
    quadro = np.full((300, 400, 3), 255, np.uint8)
    if cor is not None:
        cv2.rectangle(quadro, (190, 95), (230, 150), cor, -1)
    for y in (100, 110, 120, 130, 140):
        cv2.line(quadro, (50, y), (350, y), (0, 0, 0), 1)
    cv2.rectangle(quadro, (200, 112), (212, 128), (0, 0, 0), -1)
    cv2.rectangle(quadro, (222, 108), (226, 132), (0, 0, 0), -1)
    if cursor:
        cv2.rectangle(quadro, (300, 90), (301, 160), (0, 0, 255), -1)
    return quadro


@pytest.mark.parametrize(
    "cor",
    [(0, 255, 255), (203, 192, 255)],
    ids=["amarelo", "rosa"],
)
def test_assinatura_destaque_claro_atras_das_notas_nao_muda(cor):
    """Destaque amarelo ou rosa atrás das notas não entra na assinatura."""
    sem = assinatura(_quadro_com_destaque(None), [_PAUTA_DE_TESTE])
    com = assinatura(_quadro_com_destaque(cor), [_PAUTA_DE_TESTE])
    assert sem is not None and com is not None
    assert diferenca(sem, com) < 0.02


def test_assinatura_cursor_vermelho_nao_muda():
    """A barra vermelha do cursor, por cima das linhas, muda a assinatura só um pouco."""
    sem = assinatura(_quadro_com_destaque(None), [_PAUTA_DE_TESTE])
    com = assinatura(_quadro_com_destaque(None, cursor=True), [_PAUTA_DE_TESTE])
    assert sem is not None and com is not None
    assert diferenca(sem, com) < 0.02


def _quadro_de_linhas(linhas: list[int]) -> np.ndarray:
    """Cinza branco com linhas horizontais pretas de x 50 a 350, nas alturas dadas."""
    cinza = np.full((300, 400), 255, np.uint8)
    for y in linhas:
        cv2.line(cinza, (50, y), (350, y), 0, 1)
    return cinza


_YS_DE_TESTE = [100.0, 110.0, 120.0, 130.0, 140.0]


def test_e_tablatura_pauta_de_cinco_linhas_e_falso():
    """Cinco linhas, sem nada além delas, não é tablatura."""
    cinza = _quadro_de_linhas([100, 110, 120, 130, 140])
    assert e_tablatura(cinza, _YS_DE_TESTE, 10.0, 50, 350) is False


def test_e_tablatura_sexta_linha_embaixo_e_verdadeira():
    """Uma 6ª linha a uma entrelinha abaixo da 5ª faz da pauta uma tablatura."""
    cinza = _quadro_de_linhas([100, 110, 120, 130, 140, 150])
    assert e_tablatura(cinza, _YS_DE_TESTE, 10.0, 50, 350) is True


def test_e_tablatura_sexta_linha_em_cima_e_verdadeira():
    """Uma 6ª linha a uma entrelinha acima da 1ª também faz da pauta uma tablatura."""
    cinza = _quadro_de_linhas([90, 100, 110, 120, 130, 140])
    assert e_tablatura(cinza, _YS_DE_TESTE, 10.0, 50, 350) is True


def _quadro_tingido(destaque: bool) -> np.ndarray:
    """Quadro BGR com traços pretos tingidos de cor (compressão) e destaque amarelo opcional.

    Os traços têm BGR (0, 90, 110): saturação alta, o que a regra antiga de HSV barrava.
    """
    cor_traco = (0, 90, 110)
    quadro = np.full((300, 400, 3), 255, np.uint8)
    if destaque:
        cv2.rectangle(quadro, (190, 95), (230, 150), (0, 255, 255), -1)
    for y in (100, 110, 120, 130, 140):
        cv2.line(quadro, (50, y), (350, y), cor_traco, 1)
    cv2.rectangle(quadro, (200, 112), (212, 128), cor_traco, -1)
    cv2.rectangle(quadro, (222, 108), (226, 132), cor_traco, -1)
    return quadro


def test_assinatura_traco_tingido_sobre_destaque_continua_tinta():
    """Traço tingido de cor sobre destaque amarelo dá a mesma assinatura que sem destaque."""
    sem = assinatura(_quadro_tingido(False), [_PAUTA_DE_TESTE])
    com = assinatura(_quadro_tingido(True), [_PAUTA_DE_TESTE])
    assert sem is not None and com is not None
    assert sem.any()
    assert diferenca(sem, com) <= 0.05


def test_e_tablatura_viga_de_semicolcheia_acima_da_pauta_e_falso():
    """Viga de 0,4 entrelinha em 3 blocos, sobre 60% da largura, não faz tablatura."""
    cinza = _quadro_de_linhas([100, 110, 120, 130, 140])
    for x0, x1 in ((140, 200), (210, 270), (280, 340)):
        cv2.rectangle(cinza, (x0, 88), (x1, 91), 0, -1)
    assert e_tablatura(cinza, _YS_DE_TESTE, 10.0, 50, 350) is False


def test_e_tablatura_sexta_linha_interrompida_por_algarismos_e_verdadeira():
    """6ª linha cortada por "algarismos" a cada 3 entrelinhas ainda conta como linha.

    Como no vídeo (diag/razoes_trechos.txt), o algarismo é escuro e abre só uma folga
    branca estreita na linha de cada lado; a coluna do algarismo continua escura.
    """
    cinza = _quadro_de_linhas([100, 110, 120, 130, 140, 150])
    for x in range(80, 350, 30):
        cinza[145:156, x : x + 10] = 255
        cinza[146:155, x + 2 : x + 8] = 0
    assert e_tablatura(cinza, _YS_DE_TESTE, 10.0, 50, 350) is True


def _entrada_pauta(id_: str, sem_pauta: bool = False) -> dict:
    """Entrada de ``paginar`` com pauta (página 1, letra a) e exibição de 9 a 11 s."""
    return {
        "id": id_,
        "tela": 1,
        "video": "canal/v.mp4",
        "t": 10.0,
        "sem_pauta": sem_pauta,
        "entrelinha": 10.0,
        "caixa_recorte": [0, 0, 100, 50],
        "pagina": 1,
        "letra": "a",
        "exibicoes": [{"t0": 9.0, "t1": 11.0}],
    }


def _pasta_sem_produto(tmp_path: Path) -> Path:
    """Pasta de vídeo sem produto: T01 com pauta e T02 sem pauta, no ``indice.json``."""
    pasta = tmp_path / "video_sem"
    recortes = pasta / "recortes"
    recortes.mkdir(parents=True)
    sem = {**_entrada_pauta("T02", sem_pauta=True), "motivo": "modo fora"}
    indice = [_entrada_pauta("T01"), sem]
    (recortes / "indice.json").write_text(json.dumps(indice), encoding="utf-8")
    return pasta


def _rodar_um_falso(ok: bool, chamadas: list[tuple[str, str, str]]):
    """Substituto de ``rodar_um`` que registra a chamada e devolve um registro fixo."""

    def falso(biblioteca, condicao, item, pasta_base, origem=None, cabecalho=None):
        chamadas.append((biblioteca, condicao, item["id"]))
        return {
            "id": item["id"],
            "ok": ok,
            "motivo": None if ok else "teste",
            "segundos": 0.0,
            "codigo": 0,
            "saida": None,
            "entrada": {},
        }

    return falso


def test_ler_pasta_roda_so_audiveris_uma_vez_por_recorte_com_pauta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Só a biblioteca Audiveris roda, uma vez por recorte com pauta; homr nunca."""
    chamadas: list[tuple[str, str, str]] = []
    monkeypatch.setattr(partitura_video, "rodar_um", _rodar_um_falso(False, chamadas))
    ler_pasta(_pasta_sem_produto(tmp_path))
    assert chamadas == [("audiveris", "x2_margem", "T01")]


def test_ler_pasta_id_desconhecido_levanta_antes_de_rodar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Id fora do índice, ou sem pauta, levanta ``ValueError`` e nenhum leitor roda."""

    def nao_deve_rodar(*_args: object, **_kwargs: object) -> dict:
        pytest.fail("rodar_um não podia ser chamado")

    monkeypatch.setattr(partitura_video, "rodar_um", nao_deve_rodar)
    pasta = _pasta_sem_produto(tmp_path)
    with pytest.raises(ValueError, match="T99"):
        ler_pasta(pasta, ids=["T01", "T99"])
    with pytest.raises(ValueError, match="T02"):
        ler_pasta(pasta, ids=["T02"])
    assert not (pasta / "omr").exists()


def test_pauta_sem_produto_sem_leitura_sai_com_erro(tmp_path: Path) -> None:
    """Sem a leitura herdada e o ``.omr``: eventos e compassos vazios, ``fifths`` None."""
    pauta = partitura_video._pauta_sem_produto(_entrada_pauta("T01"), tmp_path / "omr")
    assert pauta["eventos"] == []
    assert pauta["compassos"] == []
    assert pauta["fifths"] is None
    assert "erro" in pauta
    assert pauta["recorte"] == "T01"
    assert pauta["pagina"] == 1
    assert pauta["letra"] == "a"
    assert pauta["exibicoes"] == [{"t0": 9.0, "t1": 11.0}]


def test_ler_pasta_documento_sem_tab_com_eventos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Documento com produto None, eventos sem par e pautas com página, letra e exibições."""
    chamadas: list[tuple[str, str, str]] = []
    monkeypatch.setattr(partitura_video, "rodar_um", _rodar_um_falso(True, chamadas))
    # herdar_condicao lê os MusicXML de verdade; aqui ele é substituído por um no-op.
    monkeypatch.setattr(partitura_video, "herdar_condicao", lambda *a, **k: [])
    monkeypatch.setattr(
        partitura_video,
        "ler_partitura",
        lambda caminho: {
            "armadura": 2,
            "compassos": [{"numero": 1}],
            "compasso_formula": None,
        },
    )
    evento = EventoPartitura(
        indice=0,
        compasso=1,
        t=0.0,
        t_global=0.0,
        x_quadro=12.5,
        midis=frozenset({60}),
        simbolos=[
            {
                "nome": "c",
                "midi": 60,
                "figura": "q",
                "pontuada": False,
                "voz": 1,
                "ligadura_inicio": False,
                "ligadura_fim": False,
                "notacoes": [],
            }
        ],
    )
    monkeypatch.setattr(
        partitura_video,
        "eventos_da_partitura",
        lambda musicxml, omr, x0, escala=2.0: [evento],
    )
    monkeypatch.setattr(
        partitura_video,
        "_compassos_do_recorte",
        lambda leitura, entrada_omr, x0: [
            {"numero": 1, "fracao": None, "x_quadro": 12.5}
        ],
    )
    pasta = _pasta_sem_produto(tmp_path)
    herdada = pasta / "omr" / "audiveris" / "x2_margem_herdada" / "T01"
    herdada.mkdir(parents=True)
    (herdada / "saida.musicxml").write_text("<x/>", encoding="utf-8")
    entrada_omr = pasta / "omr" / "audiveris" / "x2_margem" / "T01"
    entrada_omr.mkdir(parents=True)
    (entrada_omr / "entrada.omr").write_bytes(b"")

    documento = ler_pasta(pasta)

    assert chamadas == [("audiveris", "x2_margem", "T01")]
    assert documento["produto"] is None
    assert documento["produto_sha256"] is None
    assert documento["esquema"] == partitura_video.ESQUEMA_PARTITURA
    assert documento["video"] == "canal/v.mp4"
    assert documento["gerado_por"]["completar"] is None
    assert len(documento["pautas"]) == 1
    pauta = documento["pautas"][0]
    assert pauta["fifths"] == 2
    assert pauta["pagina"] == 1
    assert pauta["letra"] == "a"
    assert pauta["exibicoes"] == [{"t0": 9.0, "t1": 11.0}]
    assert "erro" not in pauta
    assert len(pauta["eventos"]) == 1
    assert pauta["eventos"][0]["t"] == 0.0
    assert pauta["eventos"][0]["trocadas"] == []
    assert all(e["par"] is None for p in documento["pautas"] for e in p["eventos"])
    assert documento["resumo"] == {
        "pautas": 1,
        "eventos": 1,
        "com_erro": 0,
        "paginas": 1,
    }
    gravado = json.loads(caminho_da_pasta(pasta).read_text(encoding="utf-8"))
    assert gravado == documento


def test_caminho_da_pasta_usa_o_nome_da_pasta(tmp_path: Path) -> None:
    """O documento fica dentro da pasta, com o nome dela e ``.partitura.json``."""
    pasta = tmp_path / "meu_video"
    assert caminho_da_pasta(pasta) == pasta / "meu_video.partitura.json"


def test_cli_ler_sem_produto_nem_pasta_dá_erro() -> None:
    """``ler`` exige exatamente um de ``--produto`` e ``--pasta``."""
    with pytest.raises(SystemExit) as erro:
        partitura_video.main(["ler"])
    assert erro.value.code == 2


def test_cli_ler_com_produto_e_pasta_dá_erro(tmp_path: Path) -> None:
    """Os dois juntos são exclusivos: erro do argparse, sem rodar nada."""
    with pytest.raises(SystemExit) as erro:
        partitura_video.main(["ler", "--produto", "a.json", "--pasta", str(tmp_path)])
    assert erro.value.code == 2


def test_cli_ler_pasta_imprime_total_e_caminho(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``ler --pasta`` imprime a linha de cada pauta, o total e o caminho gravado."""
    chamadas: list[tuple[str, str, str]] = []
    monkeypatch.setattr(partitura_video, "rodar_um", _rodar_um_falso(False, chamadas))
    pasta = _pasta_sem_produto(tmp_path)
    assert partitura_video.main(["ler", "--pasta", str(pasta)]) == 0
    saida = capsys.readouterr().out
    assert "T01 pagina 1: eventos 0" in saida
    assert "audiveris ok 0/1" in saida
    assert "armadura herdada em 0" in saida
    assert f"gravado em {caminho_da_pasta(pasta)}" in saida
