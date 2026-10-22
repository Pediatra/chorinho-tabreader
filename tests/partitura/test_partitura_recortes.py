"""Testes dos recortes de pauta (funções puras e imagens sintéticas; sem acervo nem cache)."""

from __future__ import annotations

import cv2
import numpy as np

from tab.partitura.pauta import Pauta
from tab.partitura.recortes import (
    PASTA_SAIDA,
    Estrutura,
    Vizinha,
    caixa_do_recorte,
    canal_ascii,
    candidatos_verticais,
    construir_parser,
    escolher_quadros_b,
    estruturas_horizontais,
    extensao_horizontal,
)

ALTURA = 1080
LARGURA = 1920


def _pauta(y0: int = 100, e: int = 10, x0: int = 200, x1: int = 1000) -> Pauta:
    """Pauta de 5 linhas equiespaçadas, começando em ``y0``.

    Args:
        y0: y da primeira linha.
        e: entrelinha, em px.
        x0: início horizontal comum.
        x1: fim horizontal comum.

    Returns:
        A pauta.
    """
    ys = tuple(y0 + k * e for k in range(5))
    return Pauta(ys=ys, entrelinha=float(e), x0=x0, x1=x1)


def _faixas_longas(ys: list[float], x0: int = 200, x1: int = 1000) -> list[Estrutura]:
    """Estruturas de linhas com a mesma extensão ``[x0, x1]``.

    Args:
        ys: y de cada linha.
        x0: início horizontal.
        x1: fim horizontal.

    Returns:
        Uma ``Estrutura`` por y.
    """
    return [Estrutura(y=y, x0=x0, x1=x1) for y in ys]


def test_caixa_sem_vizinhos_usa_margens_de_entrelinhas() -> None:
    """Margens: 2 entrelinhas na horizontal e 4 na vertical, fim exclusivo."""
    caixa = caixa_do_recorte(_pauta(), LARGURA, ALTURA, None, None)
    # x: 200 - 20 = 180 e 1000 + 20 + 1 = 1021; y: 100 - 40 = 60 e 140 + 60 + 1 = 201
    assert caixa == (180, 60, 1021, 201)


def test_caixa_corta_na_tablatura_meia_entrelinha_antes() -> None:
    """Tablatura a 170 (e=10): o corte fica em 165, meia entrelinha antes dela."""
    caixa = caixa_do_recorte(_pauta(), LARGURA, ALTURA, None, Vizinha(170.0, False))
    assert caixa == (180, 60, 1021, 166)


def test_caixa_corta_na_pauta_vizinha_no_ponto_medio() -> None:
    """Outra pauta a 170 (e=10): o corte fica no ponto médio, 155."""
    caixa = caixa_do_recorte(_pauta(), LARGURA, ALTURA, None, Vizinha(170.0, True))
    assert caixa == (180, 60, 1021, 156)


def test_caixa_acima_no_ponto_medio_e_na_tablatura() -> None:
    """Acima: outra pauta com base em 80 corta em 90; tablatura com base em 80, em 85."""
    assert caixa_do_recorte(_pauta(), LARGURA, ALTURA, Vizinha(80.0, True), None) == (
        180,
        90,
        1021,
        201,
    )
    assert caixa_do_recorte(_pauta(), LARGURA, ALTURA, Vizinha(80.0, False), None) == (
        180,
        85,
        1021,
        201,
    )


def test_caixa_recorta_na_borda_do_quadro() -> None:
    """Margens que passam da borda superior, esquerda, direita e inferior são cortadas."""
    no_topo = _pauta(y0=10, e=20, x0=5, x1=1900)
    assert caixa_do_recorte(no_topo, LARGURA, ALTURA, None, None) == (0, 0, 1920, 211)
    no_fundo = _pauta(y0=1000, e=10)
    assert caixa_do_recorte(no_fundo, LARGURA, ALTURA, None, None) == (
        180,
        960,
        1021,
        1080,
    )


def test_candidatos_ignoram_a_propria_pauta() -> None:
    """Linhas da própria pauta não contam; ficam as mais próximas de cada lado."""
    estruturas = _faixas_longas([30.0, 100.0, 110.0, 120.0, 130.0, 140.0, 200.0, 250.0])
    acima, abaixo = candidatos_verticais(_pauta(), estruturas, None)
    assert acima == Vizinha(30.0, False)
    assert abaixo == Vizinha(200.0, False)


def test_barra_curta_nao_limita_e_linha_longa_limita() -> None:
    """Barra de nota curta (100 px, abaixo de metade de 800) não conta; linha longa, sim."""
    barra = Estrutura(y=170.0, x0=300, x1=400)
    _, abaixo = candidatos_verticais(_pauta(), [barra], None)
    assert abaixo is None
    linha = Estrutura(y=170.0, x0=200, x1=1000)
    _, abaixo = candidatos_verticais(_pauta(), [barra, linha], None)
    assert abaixo == Vizinha(170.0, False)


def test_conjunto_de_barras_grossas_nao_limita_o_recorte() -> None:
    """Faixa com 23 px de espessura (mais de 1,5 entrelinha de 10 px) é barra, não linha.

    A barra não corta o recorte; a linha fina de tablatura acima dela (y=60), sim.
    """
    barras = Estrutura(y=170.0, x0=200, x1=1000, altura=23)
    _, abaixo = candidatos_verticais(_pauta(), [barras], None)
    assert abaixo is None
    linha_fina = Estrutura(y=60.0, x0=200, x1=1000, altura=3)
    acima, _ = candidatos_verticais(_pauta(), [barras, linha_fina], None)
    assert acima == Vizinha(60.0, False)


def test_candidatos_ignoram_estrutura_de_baixa_cobertura() -> None:
    """Fileira de vigas (cobertura 0,3) acima da pauta não limita; com cobertura 0,95, sim."""
    viga = Estrutura(y=30.0, x0=200, x1=1000, cobertura=0.3)
    acima, _ = candidatos_verticais(_pauta(), [viga], None)
    assert acima is None
    linha = Estrutura(y=30.0, x0=200, x1=1000, cobertura=0.95)
    acima, _ = candidatos_verticais(_pauta(), [linha], None)
    assert acima == Vizinha(30.0, False)


def test_estruturas_horizontais_mede_cobertura() -> None:
    """Linha contínua sai com cobertura > 0,9; quatro segmentos de 100 px separados por
    buracos de 300 px (cobertura ~0,31), como uma fileira de vigas, saem abaixo de 0,6."""
    quadro = np.full((ALTURA, LARGURA), 255, np.uint8)
    cv2.line(quadro, (200, 200), (1700, 200), 0, 2)
    for x in (200, 600, 1000, 1400):
        cv2.line(quadro, (x, 600), (x + 99, 600), 0, 2)
    estruturas = estruturas_horizontais(quadro)
    continua = [e for e in estruturas if abs(e.y - 200) <= 2]
    assert len(continua) == 1
    assert continua[0].cobertura > 0.9
    segmentos = [e for e in estruturas if abs(e.y - 600) <= 2]
    assert len(segmentos) == 1
    assert segmentos[0].cobertura < 0.6


def test_candidatos_marcam_linha_de_outra_pauta() -> None:
    """A linha de cima da pauta de baixo (200) é marcada como pauta, não como tablatura."""
    estruturas = _faixas_longas(
        [100.0, 110.0, 120.0, 130.0, 140.0, 200.0, 210.0, 240.0]
    )
    outra = _pauta(y0=200, e=10)
    _, abaixo = candidatos_verticais(_pauta(), estruturas, None, [outra])
    assert abaixo == Vizinha(200.0, True)


def test_candidatos_incluem_o_retangulo_da_tablatura() -> None:
    """O topo do retângulo da tablatura do censo (190) vence a linha em 200."""
    estruturas = _faixas_longas([100.0, 110.0, 120.0, 130.0, 140.0, 200.0])
    rect = (0, 190, 1920, 260)
    acima, abaixo = candidatos_verticais(_pauta(), estruturas, rect)
    assert acima is None
    assert abaixo == Vizinha(190.0, False)


def test_extensao_passa_pela_clave_e_pelas_linhas_sob_ela() -> None:
    """Bloco preto de 60 px (5 entrelinhas de altura) sobre as linhas: a extensão chega
    às bordas das linhas (300 e 1700), não para no bloco."""
    cinza = np.full((ALTURA, LARGURA), 255, np.uint8)
    ys = [100 + 10 * k for k in range(5)]
    # Clave simulada: bloco preto com as linhas de intervalo em branco (o fundo ao redor
    # das linhas continua visível); as próprias linhas são desenhadas por cima.
    cv2.rectangle(cinza, (320, 100), (380, 140), 0, -1)
    for y in (105, 115, 125, 135):
        cv2.line(cinza, (320, y), (380, y), 255, 1)
    for y in ys:
        cv2.line(cinza, (300, y), (1700, y), 0, 2)
    pauta = Pauta(ys=tuple(ys), entrelinha=10.0, x0=300, x1=1700)
    x0, x1 = extensao_horizontal(cinza, pauta)
    assert abs(x0 - 300) <= 3
    assert abs(x1 - 1700) <= 3


def test_extensao_para_no_buraco_de_4_entrelinhas() -> None:
    """Linhas com um buraco de 40 px (4 entrelinhas) no meio: a extensão para na borda
    do buraco (940), e não chega a 300."""
    cinza = np.full((ALTURA, LARGURA), 255, np.uint8)
    ys = [100 + 10 * k for k in range(5)]
    for y in ys:
        cv2.line(cinza, (300, y), (899, y), 0, 2)
        cv2.line(cinza, (940, y), (1700, y), 0, 2)
    pauta = Pauta(ys=tuple(ys), entrelinha=10.0, x0=940, x1=1700)
    x0, x1 = extensao_horizontal(cinza, pauta)
    assert abs(x0 - 940) <= 2
    assert abs(x1 - 1700) <= 3


def test_estruturas_horizontais_acha_pauta_e_tablatura() -> None:
    """Cinco linhas de pauta e seis de tablatura viram 11 faixas nos y certos."""
    quadro = np.full((ALTURA, LARGURA, 3), 255, np.uint8)
    esperadas = [100 + 10 * k for k in range(5)] + [200 + 10 * k for k in range(6)]
    for y in esperadas:
        cv2.line(quadro, (200, y), (1700, y), (0, 0, 0), 2)
    achadas = estruturas_horizontais(quadro)
    assert len(achadas) == len(esperadas)
    for y, achado in zip(esperadas, achadas, strict=True):
        assert abs(achado.y - y) <= 1.5
        assert abs(achado.x0 - 200) <= 2
        assert abs(achado.x1 - 1700) <= 2


def test_canal_ascii_tira_acentos_e_troca_o_resto_por_interrogacao() -> None:
    """Acentos saem; japonês e ``⧸`` viram ``?``; o resultado é ASCII."""
    assert canal_ascii("pablo romé") == "pablo rome"
    assert canal_ascii("guitar dell ́arte") == "guitar dell arte"
    nome = canal_ascii("ギタロー ⧸ guitarous")
    assert nome.isascii()
    assert nome.endswith(" guitarous")


def _quadro(classe: str, frac: float) -> dict:
    """Quadro fictício de uma amostra da P0.

    Args:
        classe: classe do censo.
        frac: fração do vídeo.

    Returns:
        Um ``dict`` com os campos usados pelo sorteio.
    """
    return {"frac": frac, "t": frac * 100, "classe": classe, "rect": None}


def _video(canal: str, chave: str, quadros: list[dict]) -> dict:
    """Linha fictícia da amostra da P0.

    Args:
        canal: nome do canal.
        chave: chave de retomada do vídeo.
        quadros: quadros do vídeo.

    Returns:
        Um ``dict`` com canal, chave, arquivo e quadros.
    """
    return {
        "canal": canal,
        "chave": chave,
        "arquivo": f"{canal}/{chave}.mp4",
        "quadros": quadros,
    }


def test_escolha_b_e_determinista_e_pega_menor_frac_com_pauta_tab() -> None:
    """Mesma entrada, mesma escolha; dentro do vídeo, o pauta+tab de menor frac."""
    amostra = [
        _video(
            "A",
            "a|1",
            [
                _quadro("so_tab", 0.05),
                _quadro("pauta+tab", 0.5),
                _quadro("pauta+tab", 0.3),
            ],
        ),
        _video("A", "a|2", [_quadro("nenhum", 0.1), _quadro("so_pauta", 0.2)]),
        _video("A", "a|3", [_quadro("pauta+tab", 0.7)]),
    ]
    primeira = escolher_quadros_b(amostra, ["A"], videos_por_canal={"A": 1})
    segunda = escolher_quadros_b(amostra, ["A"], videos_por_canal={"A": 1})
    assert primeira == segunda
    video, indice = primeira[0]
    assert video["chave"] in {"a|1", "a|3"}
    if video["chave"] == "a|1":
        assert indice == 2
    else:
        assert indice == 0


def test_escolha_b_sorteia_videos_distintos_por_canal() -> None:
    """Pedir 2 vídeos num canal devolve 2 vídeos diferentes, sem repetição."""
    amostra = [
        _video("S", f"s|{k}", [_quadro("pauta+tab", 0.1 * k)]) for k in range(1, 6)
    ]
    escolhidos = escolher_quadros_b(amostra, ["S"], videos_por_canal={"S": 2})
    chaves = [video["chave"] for video, _ in escolhidos]
    assert len(chaves) == 2
    assert len(set(chaves)) == 2


def test_escolha_b_ignora_videos_sem_pauta_tab() -> None:
    """Vídeo sem nenhum quadro pauta+tab nunca é sorteado."""
    amostra = [
        _video("C", "c|1", [_quadro("so_tab", 0.1)]),
        _video("C", "c|2", [_quadro("pauta+tab", 0.4)]),
    ]
    for semente in range(5):
        escolhidos = escolher_quadros_b(
            amostra, ["C"], semente=semente, videos_por_canal={"C": 1}
        )
        assert [video["chave"] for video, _ in escolhidos] == ["c|2"]


def test_caixa_margem_padrao_e_igual_a_4_e_6() -> None:
    """Margens explícitas 4 e 6 dão a mesma caixa que o padrão (nada muda sem opção)."""
    padrao = caixa_do_recorte(_pauta(), LARGURA, ALTURA, None, None)
    explicita = caixa_do_recorte(_pauta(), LARGURA, ALTURA, None, None, 4, 6)
    assert padrao == explicita


def test_caixa_margem_7_ganha_3_entrelinhas_em_cada_lado() -> None:
    """Margem 7 em cima e embaixo: 3 entrelinhas a mais que a margem padrão."""
    caixa = caixa_do_recorte(_pauta(), LARGURA, ALTURA, None, None, 7, 7)
    # y: 100 - 70 = 30 e 140 + 70 + 1 = 211; x não muda
    assert caixa == (180, 30, 1021, 211)


def test_caixa_margem_7_limitada_pela_tablatura_vizinha() -> None:
    """Com tablatura a 80 px acima, a margem de 7 é limitada: corta meia entrelinha antes."""
    acima = Vizinha(y=80.0, de_pauta=False)
    caixa = caixa_do_recorte(_pauta(), LARGURA, ALTURA, acima, None, 7, 7)
    # topo = ceil(80 + 0.5 * 10) = 85, não 30
    assert caixa[1] == 85


def test_parser_padrao_e_opcoes_de_margem() -> None:
    """Sem opções, a CLI usa 4 e 6 entrelinhas e a pasta da rodada 3001."""
    padrao = construir_parser().parse_args([])
    assert (padrao.margem_cima, padrao.margem_baixo) == (4, 6)
    assert padrao.saida == PASTA_SAIDA
    opcoes = construir_parser().parse_args(
        ["--margem-cima", "7", "--margem-baixo", "7", "--saida", "/tmp/x"]
    )
    assert (opcoes.margem_cima, opcoes.margem_baixo) == (7, 7)
