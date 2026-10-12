"""Testes das regras puras da linha de base dos dedos (M3): ``tab.maos_regra_dedos``.

Cobre a posição da mão, o limite de 1 a 4 dedos, a corda solta, a regra de pestana, a
janela de tempo (com a borda inclusiva) e a regra da direita. As notas são pequenas e
escritas à mão, no formato do MVP (``tela``, ``coluna``, ``corda``, ``casa``, ``t_ini``).
"""

from tab import maos_regra_dedos as r


def _n(corda: int, casa: int, t: float | None = 1.0, tela: int = 1, coluna: int = 1):
    """Nota do MVP, só com os campos que as regras leem."""
    return {"tela": tela, "coluna": coluna, "corda": corda, "casa": casa, "t_ini": t}


def test_posicao_e_a_menor_casa_maior_que_zero():
    assert r.posicao([0, 3, 2, 5]) == 2


def test_posicao_sem_casa_positiva_e_none():
    assert r.posicao([0, 0]) is None
    assert r.posicao([]) is None


def test_dedo_pela_posicao_soma_um_a_partir_de_p():
    assert r.dedo_pela_posicao(2, 2) == "1"
    assert r.dedo_pela_posicao(4, 2) == "3"


def test_dedo_pela_posicao_corda_solta_e_zero_mesmo_sem_posicao():
    assert r.dedo_pela_posicao(0, None) == "0"
    assert r.dedo_pela_posicao(0, 3) == "0"


def test_dedo_pela_posicao_sem_posicao_nao_decide():
    assert r.dedo_pela_posicao(3, None) is None


def test_dedo_pela_posicao_limita_a_1_ate_4():
    assert r.dedo_pela_posicao(5, 2) == "4"
    assert r.dedo_pela_posicao(6, 2) is None
    assert r.dedo_pela_posicao(1, 3) is None


def test_dedo_pela_casa_primeira_posicao():
    assert r.dedo_pela_casa(0) == "0"
    assert r.dedo_pela_casa(1) == "1"
    assert r.dedo_pela_casa(4) == "4"
    assert r.dedo_pela_casa(5) is None


def test_ataque_agrupa_por_tela_coluna_e_tempo():
    mvp = [
        _n(1, 2, t=1.0, tela=1, coluna=1),
        _n(2, 2, t=1.0, tela=1, coluna=1),
        _n(1, 2, t=1.0, tela=1, coluna=2),
        _n(1, 2, t=2.0, tela=1, coluna=1),
    ]
    grupos = r.ataques(mvp)
    assert sorted(grupos.values()) == [[0, 1], [2], [3]]


def test_nota_sem_tempo_fica_fora_de_todo_ataque():
    mvp = [_n(1, 2, t=None), _n(2, 2, t=None)]
    assert r.ataques(mvp) == {}


def test_esquerda_posicao_ataque_usa_a_menor_casa_do_acorde():
    mvp = [_n(6, 0), _n(3, 2), _n(1, 4)]
    esq = r.esquerda_posicao_ataque(mvp, pestana=False)
    assert esq == {0: "0", 1: "1", 2: "3"}


def test_esquerda_posicao_janela_inclui_as_vizinhas_na_borda():
    mvp = [_n(3, 3, t=1.0), _n(2, 1, t=1.5), _n(1, 6, t=2.5)]
    esq = r.esquerda_posicao_janela(mvp, janela=0.5, pestana=False)
    # Nota em 1.0: vizinhas em 1.0 e 1.5 (|dt| = 0.5 entra). P = 1, dedo = 3.
    assert esq[0] == "3"
    # Nota em 2.5 está a 1.0 s das outras: sem vizinha, P é a própria casa (6), e o
    # dedo cai em "1". É o viés de quem não tem contexto: a regra chuta a primeira.
    assert esq[2] == "1"


def test_esquerda_posicao_janela_menor_janela_deixa_de_ver_a_vizinha():
    mvp = [_n(3, 3, t=1.0), _n(2, 1, t=1.4)]
    assert r.esquerda_posicao_janela(mvp, janela=0.2, pestana=False)[0] == "1"
    assert r.esquerda_posicao_janela(mvp, janela=0.5, pestana=False)[0] == "3"


def test_esquerda_nota_sem_tempo_so_decide_corda_solta():
    mvp = [_n(6, 0, t=None), _n(5, 2, t=None)]
    esq = r.esquerda_posicao_janela(mvp, janela=1.0, pestana=False)
    assert esq == {0: "0", 1: None}


def test_pestana_do_ataque_com_cordas_nao_vizinhas():
    mvp = [_n(1, 2), _n(5, 2), _n(3, 4)]
    assert r.pestana_do_ataque(mvp, [0, 1, 2]) == {0, 1}


def test_pestana_do_ataque_so_com_cordas_vizinhas_nao_marca():
    mvp = [_n(1, 2), _n(2, 2)]
    assert r.pestana_do_ataque(mvp, [0, 1]) == set()


def test_pestana_do_ataque_exige_duas_notas_na_menor_casa():
    mvp = [_n(1, 2), _n(5, 4)]
    assert r.pestana_do_ataque(mvp, [0, 1]) == set()


def test_pestana_ignora_corda_solta_ao_procurar_a_menor_casa():
    mvp = [_n(6, 0), _n(1, 3), _n(4, 3)]
    assert r.pestana_do_ataque(mvp, [0, 1, 2]) == {1, 2}


def test_esquerda_pestana_sobrescreve_para_um():
    mvp = [_n(1, 2, t=1.0), _n(5, 2, t=1.0), _n(3, 4, t=1.0)]
    esq = r.esquerda_posicao_ataque(mvp, pestana=True)
    assert esq[0] == "1"
    assert esq[1] == "1"
    assert esq[2] == "3"


def test_esquerda_pestana_janela_corrige_quando_a_janela_traz_casa_menor():
    mvp = [_n(3, 1, t=0.5), _n(1, 2, t=1.0), _n(5, 2, t=1.0)]
    sem = r.esquerda_posicao_janela(mvp, janela=1.0, pestana=False)
    com = r.esquerda_posicao_janela(mvp, janela=1.0, pestana=True)
    assert sem[1] == "2"
    assert com[1] == "1"
    assert com[2] == "1"


def test_direita_nota_mais_grave_nas_cordas_4_a_6_e_p():
    mvp = [_n(6, 0), _n(3, 2), _n(1, 4)]
    assert r.direita_do_ataque(mvp, [0, 1, 2]) == {0: "p", 1: "i", 2: "a"}


def test_direita_corda_4_a_6_que_nao_e_a_mais_grave_nao_decide():
    mvp = [_n(6, 0), _n(4, 2)]
    assert r.direita_do_ataque(mvp, [0, 1]) == {0: "p", 1: None}


def test_direita_nota_sozinha_segue_a_mesma_tabela():
    assert r.direita([_n(4, 1, t=1.0)]) == {0: "p"}
    assert r.direita([_n(3, 1, t=2.0)]) == {0: "i"}
    assert r.direita([_n(2, 1, t=3.0)]) == {0: "m"}
    assert r.direita([_n(1, 1, t=4.0)]) == {0: "a"}


def test_direita_sem_tempo_trata_a_nota_como_sozinha():
    assert r.direita([_n(5, 1, t=None)]) == {0: "p"}


def test_esquerdas_por_metodo_lista_as_variantes_medidas():
    mvp = [_n(1, 2)]
    nomes = set(r.esquerdas_por_metodo(mvp))
    assert nomes == {
        "regra_casa",
        "regra_posicao_ataque",
        "regra_pestana_ataque",
        "regra_posicao_janela_0_5",
        "regra_pestana_janela_0_5",
        "regra_posicao_janela_1",
        "regra_pestana_janela_1",
        "regra_posicao_janela_2",
        "regra_pestana_janela_2",
    }


def test_conferir_indices_aponta_nota_que_nao_bate():
    mvp = [_n(3, 2, t=1.0), _n(2, 4, t=2.0)]
    gab = {
        "notas": [
            {"id": "ok", "indice_mvp": 0, "corda": 3, "casa": 2, "t_ini": 1.0},
            {"id": "trocada", "indice_mvp": 1, "corda": 3, "casa": 2, "t_ini": 1.0},
            {"id": "fora", "indice_mvp": 9, "corda": 3, "casa": 2, "t_ini": 1.0},
        ]
    }
    assert r.conferir_indices(gab, mvp) == ["trocada", "fora"]
