"""Testes do método V (quadros vizinhos), com quadros sintéticos."""

from tab.maos.braco.vizinhos import (
    casar,
    metodo_v,
    nut_confiante,
    propagar_k,
)

POSICOES = [300.0 + 100.0 * n for n in range(8)]


def _quadro(
    id_: str,
    t: float,
    x0: float = 200.0,
    numeros: list[int] | None = None,
    *,
    achou: bool = True,
    sinalizado: bool = False,
    dimensoes: list[int] | None = None,
) -> dict:
    """Monta um quadro sintético com cordas horizontais e trastes.

    Args:
        id_: Identificador do quadro.
        t: Instante do quadro, em segundos.
        x0: Coordenada x do nut e início das cordas.
        numeros: Números dos trastes; None usa 1..8 nas posições POSICOES.
        achou: Valor de "achou" do braço.
        sinalizado: Valor de "sinalizado".
        dimensoes: Dimensões da imagem; None usa [1280, 720].

    Returns:
        Quadro no formato de registro denso.
    """
    if numeros is None:
        numeros = list(range(1, 9))
    trastes = [
        {"numero": n, "ponto": [x, 130.0]}
        for n, x in zip(numeros, POSICOES, strict=True)
    ]
    return {
        "id": id_,
        "t": t,
        "dimensoes": [1280, 720] if dimensoes is None else dimensoes,
        "previsto": {
            "achou": achou,
            "sinalizado": sinalizado,
            "nut": [x0, 130.0],
            "corda1": [[x0, 100.0], [1200.0, 100.0]],
            "corda6": [[x0, 160.0], [1200.0, 160.0]],
            "trastes": trastes,
        },
    }


def _deslocar(quadro: dict, delta: float) -> dict:
    """Desloca os trastes de um quadro no eixo x.

    Args:
        quadro: Quadro a ser alterado (é copiado, não modificado).
        delta: Deslocamento em pixels.

    Returns:
        Novo quadro com os trastes deslocados.
    """
    novo = {**quadro, "previsto": {**quadro["previsto"]}}
    novo["previsto"]["trastes"] = [
        {"numero": t["numero"], "ponto": [t["ponto"][0] + delta, t["ponto"][1]]}
        for t in quadro["previsto"]["trastes"]
    ]
    return novo


def test_nut_confiante_com_nut_longe_da_borda():
    """Nut no meio da imagem é confiável."""
    assert nut_confiante(_quadro("a", 0.0, x0=200.0)) is True


def test_nut_confiante_falso_com_nut_na_borda():
    """Nut a 30 px da borda, com margem de 36 px (5% de 720), não é confiável."""
    assert nut_confiante(_quadro("a", 0.0, x0=30.0)) is False


def test_nut_confiante_falso_quando_sinalizado():
    """Quadro sinalizado nunca é confiável."""
    assert nut_confiante(_quadro("a", 0.0, sinalizado=True)) is False


def test_nut_confiante_falso_sem_dimensoes():
    """Quadro sem a chave dimensoes não é confiável."""
    quadro = _quadro("a", 0.0)
    del quadro["dimensoes"]
    assert nut_confiante(quadro) is False


def test_casar_quadros_identicos_casa_todos():
    """Mesmos trastes em dois quadros casam os oito pares, na mesma ordem."""
    a = _quadro("a", 0.0)
    b = _quadro("b", 0.5)
    assert casar(a, b) == [(i, i) for i in range(8)]


def test_casar_desvio_de_um_decimo_do_espaco_ainda_casa():
    """Deslocamento de 0,1 espaçamento (10 px) continua dentro da tolerância."""
    a = _deslocar(_quadro("a", 0.0), 10.0)
    b = _quadro("b", 0.5)
    assert casar(a, b) == [(i, i) for i in range(8)]


def test_casar_desvio_de_meio_espaco_nao_casa():
    """Deslocamento de 0,5 espaçamento (50 px) excede a tolerância: sem casamento."""
    a = _deslocar(_quadro("a", 0.0), 50.0)
    b = _quadro("b", 0.5)
    assert casar(a, b) is None


def test_casar_com_menos_de_tres_trastes_retorna_none():
    """Com dois trastes apenas, não há casamento."""
    a = _quadro("a", 0.0)
    a["previsto"]["trastes"] = a["previsto"]["trastes"][:2]
    b = _quadro("b", 0.5)
    assert casar(a, b) is None


def test_propagar_k_detector_pulou_o_primeiro_traste():
    """Alvo numerado 0..7 onde a referência tem 1..8 dá k = 1."""
    referencia = _quadro("ref", 0.0, numeros=list(range(1, 9)))
    alvo = _quadro("alvo", 0.5, numeros=list(range(0, 8)))
    assert propagar_k([referencia, alvo]) == 1


def test_propagar_k_um_quadro_so_retorna_zero():
    """Caminho de um único quadro (a própria referência) dá k = 0."""
    assert propagar_k([_quadro("ref", 0.0)]) == 0


def test_propagar_k_offsets_inconsistentes_retorna_none():
    """Pares de um mesmo elo com k diferentes invalidam o caminho."""
    referencia = _quadro("ref", 0.0, numeros=list(range(1, 9)))
    alvo = _quadro("alvo", 0.5, numeros=[0, 1, 2, 3, 4, 5, 6, 9])
    assert propagar_k([referencia, alvo]) is None


def test_propagar_k_encadeado_acumula_o_offset():
    """Dois elos com offset 1 e depois 1 de novo somam k = 2 no último quadro."""
    ref = _quadro("ref", 0.0, numeros=list(range(1, 9)))
    meio = _quadro("meio", 0.5, numeros=list(range(0, 8)))
    fim = _quadro("fim", 1.0, numeros=list(range(-1, 7)))
    assert propagar_k([ref, meio, fim]) == 2


def test_metodo_v_sequencia_com_nut_na_borda_segue_a_referencia():
    """Quadros 1 a 4 com nut na borda e numeração -1 recebem k = 1 por propagação."""
    registros = [_quadro("f0", 0.0, x0=200.0, numeros=list(range(1, 9)))]
    for n in range(1, 5):
        registros.append(
            _quadro(
                f"f{n}",
                n * 0.5,
                x0=10.0,
                numeros=list(range(0, 8)),
            )
        )
    saida = metodo_v(registros)
    assert saida["f0"] == {"k": 0, "referencia": "f0", "motivo": "nut visível"}
    for n in range(1, 5):
        assert saida[f"f{n}"] == {"k": 1, "referencia": "f0", "motivo": "seguido"}


def test_metodo_v_quadro_sem_braco_no_caminho():
    """Quadro sem braço entre a referência e o alvo invalida o caminho."""
    sem_braco = _quadro("meio", 0.5, x0=10.0, achou=False)
    registros = [
        _quadro("ref", 0.0, x0=200.0),
        sem_braco,
        _quadro("alvo", 1.0, x0=10.0, numeros=list(range(0, 8))),
    ]
    saida = metodo_v(registros)
    assert "meio" not in saida
    assert saida["alvo"] == {
        "k": None,
        "referencia": "ref",
        "motivo": "caminho sem braço",
    }


def test_metodo_v_referencia_a_mais_de_30_segundos():
    """Sem nut confiável a até 30 s, o quadro fica sem numeração."""
    registros = [
        _quadro("ref", 0.0, x0=200.0),
        _quadro("alvo", 31.0, x0=10.0),
    ]
    saida = metodo_v(registros)
    assert saida["alvo"] == {
        "k": None,
        "referencia": None,
        "motivo": "sem nut a até 30 s",
    }


def test_metodo_v_referencia_exatamente_a_30_segundos_entra():
    """Referência a exatamente 30 s está dentro da janela."""
    registros = [
        _quadro("ref", 0.0, x0=200.0),
        _quadro("alvo", 30.0, x0=10.0, numeros=list(range(0, 8))),
    ]
    saida = metodo_v(registros)
    assert saida["alvo"] == {"k": 1, "referencia": "ref", "motivo": "seguido"}


def test_metodo_v_empate_de_distancia_escolhe_o_anterior():
    """Com nut confiável a 1 s antes e 1 s depois, a referência é a anterior."""
    registros = [
        _quadro("antes", 0.0, x0=200.0, numeros=list(range(1, 9))),
        _quadro("alvo", 1.0, x0=10.0, numeros=list(range(0, 8))),
        _quadro("depois", 2.0, x0=200.0, numeros=list(range(1, 9))),
    ]
    saida = metodo_v(registros)
    assert saida["alvo"]["referencia"] == "antes"
    assert saida["alvo"]["k"] == 1
