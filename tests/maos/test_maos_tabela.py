"""Testes das regras puras do censo de mãos (M0): ``tab.maos_tabela``.

Cobre área e sobreposição de caixas, fusão de detecções da mesma mão, a checagem de
mão dentro do painel da tablatura, a vista do quadro, o resumo por quadro e por vídeo
e a tabela por canal em Markdown. Os dados são pequenos e escritos à mão; nada aqui
depende de MediaPipe, de GPU ou do acervo.
"""

from tab.maos import tabela as maos_tabela

RECT_TAB = [0, 500, 1000, 700]
CAIXA_A = [0, 0, 100, 100]
CAIXA_B = [300, 0, 400, 100]


def _mao(
    lado: str, caixa: list[float], score: float = 0.9, na_tab: bool = False
) -> dict:
    """Detecção de mão no formato gravado pelo censo."""
    return {
        "lado": lado,
        "score": score,
        "caixa": caixa,
        "palma_px": 50.0,
        "na_tab": na_tab,
    }


def _quadro(maos: list[dict], tab: bool = False, rostos: int = 0) -> dict:
    """Quadro do censo com as mãos dadas e ``rostos`` rostos."""
    return {
        "i": 0,
        "t": 1.0,
        "tab": tab,
        "rect": RECT_TAB if tab else None,
        "maos": maos,
        "rostos": [[0, 0, 10, 10]] * rostos,
    }


def _video(quadros: list[dict], canal: str = "x", altura: int = 1080) -> dict:
    """Linha do censo de mãos com os quadros dados."""
    return {
        "chave": f"{canal}/video.mp4|1|1",
        "arquivo": f"{canal}/video.mp4",
        "canal": canal,
        "altura": altura,
        "largura": 1920,
        "quadros": quadros,
        "faltam": [],
    }


def _quadros_com_duas_maos_em_dois() -> list[dict]:
    """Quatro quadros: dois com duas mãos (lados quaisquer) e dois sem mão."""
    duas_lr = [_mao("L", CAIXA_A), _mao("R", CAIXA_B)]
    duas_ll = [_mao("L", CAIXA_A), _mao("L", CAIXA_B)]
    return [_quadro(duas_lr), _quadro(duas_ll), _quadro([]), _quadro([])]


def _quadros_com_tab() -> list[dict]:
    """Quatro quadros cruzando painel de TAB (sim/não) e duas mãos (sim/não)."""
    return [
        _quadro([_mao("L", CAIXA_A), _mao("R", CAIXA_B)], tab=True),
        _quadro([_mao("L", CAIXA_A)], tab=True),
        _quadro([_mao("L", CAIXA_A), _mao("L", CAIXA_B)], tab=False),
        _quadro([], tab=False),
    ]


def _resumos_por_canal() -> list[dict]:
    """Dois vídeos do canal ``alfa`` e um do canal ``beta``, já resumidos."""
    duas = _quadro([_mao("L", CAIXA_A), _mao("R", CAIXA_B)])
    vazio = _quadro([])
    return [
        maos_tabela.resumo_do_video(_video([duas, vazio], canal="alfa")),
        maos_tabela.resumo_do_video(_video([vazio], canal="alfa")),
        maos_tabela.resumo_do_video(_video([duas, duas], canal="beta")),
    ]


# a) area


def test_area_de_caixa_normal() -> None:
    assert maos_tabela.area([0, 0, 10, 5]) == 50


def test_area_de_caixa_degenerada_da_zero() -> None:
    assert maos_tabela.area([10, 0, 5, 5]) == 0


# b) sobreposicao


def test_sobreposicao_de_caixas_identicas_da_um() -> None:
    assert maos_tabela.sobreposicao([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_sobreposicao_de_caixas_disjuntas_da_zero() -> None:
    assert maos_tabela.sobreposicao([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_sobreposicao_de_caixa_pequena_dentro_da_grande_da_um() -> None:
    assert maos_tabela.sobreposicao([0, 0, 100, 100], [10, 10, 20, 20]) == 1.0


def test_sobreposicao_mede_sobre_a_caixa_menor() -> None:
    # interseção [5, 0, 10, 10] tem 50 px; a caixa menor tem 100 px (não 200)
    assert maos_tabela.sobreposicao([0, 0, 10, 10], [5, 0, 25, 10]) == 0.5


def test_sobreposicao_com_caixa_degenerada_da_zero() -> None:
    assert maos_tabela.sobreposicao([10, 0, 5, 5], [0, 0, 100, 100]) == 0.0


# c) fundir_maos


def test_fundir_mesma_mao_fica_com_maior_score() -> None:
    grande = _mao("L", [0, 0, 100, 100], score=0.6)
    pequena = _mao("L", [10, 10, 50, 50], score=0.9)
    assert maos_tabela.fundir_maos([grande, pequena]) == [pequena]


def test_fundir_maos_separadas_continuam_duas() -> None:
    fundidas = maos_tabela.fundir_maos([_mao("L", CAIXA_A), _mao("R", CAIXA_B)])
    assert len(fundidas) == 2


def test_fundir_saida_em_ordem_decrescente_de_score() -> None:
    maos = [
        _mao("L", [0, 0, 10, 10], score=0.5),
        _mao("R", [100, 0, 110, 10], score=0.9),
        _mao("L", [200, 0, 210, 10], score=0.7),
    ]
    scores = [m["score"] for m in maos_tabela.fundir_maos(maos)]
    assert scores == [0.9, 0.7, 0.5]


def test_fundir_lista_vazia_da_lista_vazia() -> None:
    assert maos_tabela.fundir_maos([]) == []


# d) dentro_da_tab


def test_dentro_da_tab_centro_dentro_do_painel() -> None:
    assert maos_tabela.dentro_da_tab([400, 550, 600, 650], RECT_TAB) is True


def test_dentro_da_tab_centro_fora_do_painel() -> None:
    assert maos_tabela.dentro_da_tab([400, 100, 600, 200], RECT_TAB) is False


def test_dentro_da_tab_olha_o_centro_e_nao_o_canto() -> None:
    # canto superior esquerdo cai no painel, mas o centro (1050, 750) está fora
    assert maos_tabela.dentro_da_tab([950, 650, 1150, 850], RECT_TAB) is False


def test_dentro_da_tab_sem_painel_da_false() -> None:
    assert maos_tabela.dentro_da_tab([400, 550, 600, 650], None) is False


# e) vista_do_quadro


def test_vista_com_rosto_da_rosto() -> None:
    assert maos_tabela.vista_do_quadro(1, 0) == "rosto"


def test_vista_sem_rosto_com_maos_da_sem_rosto() -> None:
    assert maos_tabela.vista_do_quadro(0, 2) == "sem_rosto"


def test_vista_sem_rosto_e_sem_mao_da_sem_mao() -> None:
    assert maos_tabela.vista_do_quadro(0, 0) == "sem_mao"


# f) resumo_do_quadro


def test_quadro_com_L_e_R_marca_esquerda_e_direita() -> None:
    registro = _quadro([_mao("L", CAIXA_A), _mao("R", CAIXA_B)])
    resumo = maos_tabela.resumo_do_quadro(registro)
    assert resumo["esquerda"] is True
    assert resumo["direita"] is True


def test_quadro_com_L_e_R_marca_duas() -> None:
    registro = _quadro([_mao("L", CAIXA_A), _mao("R", CAIXA_B)])
    resumo = maos_tabela.resumo_do_quadro(registro)
    assert resumo["duas"] is True
    assert resumo["duas_qualquer"] is True
    assert resumo["n_maos"] == 2


def test_duas_maos_do_mesmo_lado_nao_marcam_duas() -> None:
    registro = _quadro([_mao("L", CAIXA_A), _mao("L", CAIXA_B)])
    resumo = maos_tabela.resumo_do_quadro(registro)
    assert resumo["duas"] is False


def test_duas_maos_do_mesmo_lado_marcam_duas_qualquer() -> None:
    # troca de lado do detector: as duas mãos são L, mas contam como "duas" no total
    registro = _quadro([_mao("L", CAIXA_A), _mao("L", CAIXA_B)])
    resumo = maos_tabela.resumo_do_quadro(registro)
    assert resumo["duas_qualquer"] is True


def test_mao_na_tab_nao_conta_em_n_maos() -> None:
    registro = _quadro([_mao("L", CAIXA_A, na_tab=True)])
    assert maos_tabela.resumo_do_quadro(registro)["n_maos"] == 0


def test_mao_na_tab_nao_marca_lado() -> None:
    registro = _quadro([_mao("L", CAIXA_A, na_tab=True)])
    assert maos_tabela.resumo_do_quadro(registro)["esquerda"] is False


def test_quadro_sem_chave_rostos_nao_quebra() -> None:
    registro = {
        "i": 0,
        "t": 1.0,
        "tab": False,
        "rect": None,
        "maos": [_mao("L", CAIXA_A)],
    }
    assert maos_tabela.resumo_do_quadro(registro)["vista"] == "sem_rosto"


# g) resumo_do_video


def test_video_conta_os_quadros_lidos() -> None:
    resumo = maos_tabela.resumo_do_video(_video(_quadros_com_duas_maos_em_dois()))
    assert resumo["n"] == 4


def test_video_conta_duas_maos_de_qualquer_lado() -> None:
    resumo = maos_tabela.resumo_do_video(_video(_quadros_com_duas_maos_em_dois()))
    assert resumo["duas_qualquer"] == 2


def test_video_duas_so_quando_ha_L_e_R() -> None:
    resumo = maos_tabela.resumo_do_video(_video(_quadros_com_duas_maos_em_dois()))
    assert resumo["duas"] == 1


def test_video_serve_na_fronteira_de_metade() -> None:
    resumo = maos_tabela.resumo_do_video(_video(_quadros_com_duas_maos_em_dois()))
    assert resumo["serve"] is True


def test_video_com_1_de_4_quadros_nao_serve() -> None:
    quadros = [
        _quadro([_mao("L", CAIXA_A), _mao("R", CAIXA_B)]),
        _quadro([]),
        _quadro([]),
        _quadro([]),
    ]
    resumo = maos_tabela.resumo_do_video(_video(quadros))
    assert resumo["serve"] is False


def test_video_conta_quadros_com_tab() -> None:
    resumo = maos_tabela.resumo_do_video(_video(_quadros_com_tab()))
    assert resumo["n_tab"] == 2


def test_video_conta_duas_maos_com_tab() -> None:
    resumo = maos_tabela.resumo_do_video(_video(_quadros_com_tab()))
    assert resumo["tab_e_duas"] == 1


# h) tabela_por_canal


def test_tabela_canal_com_mais_videos_vem_primeiro() -> None:
    linhas = maos_tabela.tabela_por_canal(_resumos_por_canal())
    assert linhas[0]["canal"] == "alfa"


def test_tabela_ultima_linha_e_total() -> None:
    linhas = maos_tabela.tabela_por_canal(_resumos_por_canal())
    assert linhas[-1]["canal"] == "TOTAL"


def test_tabela_total_soma_os_videos() -> None:
    linhas = maos_tabela.tabela_por_canal(_resumos_por_canal())
    assert linhas[-1]["videos"] == 3


def test_tabela_uma_linha_por_canal_mais_total() -> None:
    linhas = maos_tabela.tabela_por_canal(_resumos_por_canal())
    assert len(linhas) == 3


# i) markdown


def test_markdown_cabecalho_e_separador() -> None:
    texto = maos_tabela.markdown(maos_tabela.tabela_por_canal(_resumos_por_canal()))
    cabecalho, separador = texto.split("\n")[:2]
    assert cabecalho.startswith("| canal |")
    assert separador.startswith("| --- |")


def test_markdown_uma_linha_por_canal_e_total() -> None:
    texto = maos_tabela.markdown(maos_tabela.tabela_por_canal(_resumos_por_canal()))
    # cabeçalho + separador + 2 canais + TOTAL
    assert len(texto.split("\n")) == 5


def test_markdown_total_em_negrito() -> None:
    texto = maos_tabela.markdown(maos_tabela.tabela_por_canal(_resumos_por_canal()))
    assert texto.split("\n")[-1].startswith("| **TOTAL** |")


def test_markdown_canal_sem_tab_mostra_travessao() -> None:
    videos = [maos_tabela.resumo_do_video(_video([_quadro([])], canal="gama"))]
    texto = maos_tabela.markdown(maos_tabela.tabela_por_canal(videos))
    linha_do_canal = texto.split("\n")[2]
    assert "| — (0/0) |" in linha_do_canal
