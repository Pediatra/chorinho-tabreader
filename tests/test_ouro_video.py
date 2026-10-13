"""Fase 2 / T2.1+T2.2: funções puras e o servidor da ferramenta do ouro de vídeo."""

import http.client
import json
import re
import threading
from pathlib import Path

import numpy as np
import pytest

from tab.ouro_video import (
    PAGINA,
    TECNICAS,
    Agrupador,
    agrupar_telas,
    clique_para_quadro,
    comparar_notas,
    corda_mais_proxima,
    criar_servidor,
    diferenca_cinza,
    fazer_slug,
    fundir_ouro,
    fundir_sem_v1,
    gravar_atomico,
    histograma,
    montar_ouro,
    pagina_em,
    painel_com_caixas,
    sortear_instantes,
    texto_sem_v1,
    validar_ouro,
)

RECT = (10, 10, 190, 70)


def quadro(conteudo: int = 0, faixa_x: int | None = None) -> np.ndarray:
    """Quadro BGR branco; ``conteudo`` desenha N 'algarismos' pretos; faixa azul pálida."""
    q = np.full((80, 200, 3), 255, np.uint8)
    for k in range(conteudo):
        q[30:40, 20 + 25 * k : 30 + 25 * k] = 0
    if faixa_x is not None:
        q[10:70, faixa_x : faixa_x + 12] = (240, 215, 200)  # azul pálido, S ~ 40
    return q


def test_faixa_colorida_andando_nao_cria_tela() -> None:
    """Uma faixa pálida passando por cima não é tela nova; conteúdo novo é."""
    amostras = [(2.0 * k, quadro(3, 20 + 15 * k)) for k in range(8)]
    assert set(agrupar_telas(amostras, 2.0, RECT)) == {1}
    amostras += [(16.0 + 2.0 * k, quadro(5, 20 + 15 * k)) for k in range(3)]
    assert agrupar_telas(amostras, 2.0, RECT) == [1] * 8 + [2] * 3


def test_diferenca_ignora_cor_mas_ve_tinta() -> None:
    """Mesma tinta com faixa: ~0. Tinta diferente: acima do limiar."""
    assert diferenca_cinza(quadro(3), quadro(3, 50))[0] < 0.5
    assert diferenca_cinza(quadro(3), quadro(6))[0] > 2.0


def test_tela_volta_igual_depois_de_ausencia_e_a_mesma() -> None:
    """Sumiu e voltou igual: mesma tela; voltou diferente: tela nova."""
    escuro = np.zeros((80, 200, 3), np.uint8)

    def detectar(q: np.ndarray):
        return (RECT, None) if q.max() > 0 else None

    ag = Agrupador(2.0, detectar)
    ids = [ag.alimentar(t, q) for t, q in enumerate([quadro(3), escuro, quadro(3)])]
    assert ids == [1, None, 1]
    assert ag.alimentar(9, quadro(7)) == 2


def test_clique_e_corda() -> None:
    """Imagem ampliada 2x que começa em x=70: clique em 100 px -> x_quadro 120."""
    assert clique_para_quadro(100, 2, 70) == 120
    assert clique_para_quadro(0, 1, 5) == 5
    linhas = [10, 20, 30, 40, 50, 60]
    assert corda_mais_proxima(21, linhas) == 2
    assert corda_mais_proxima(-5, linhas) == 1
    assert corda_mais_proxima(99, linhas) == 6


def test_sorteio_dentro_da_presenca_e_reprodutivel() -> None:
    """Só instantes com tela; mesma semente, mesma ordem embaralhada."""
    tela = [None, 1, 1, None, 2, 2, 2, None] * 5
    a = sortear_instantes(tela, 2.0, 10, 0)
    assert a == sortear_instantes(tela, 2.0, 10, 0)
    assert len(a) == 10 and len({t for t, _ in a}) == 10
    assert all(tela[round(t / 2)] == k for t, k in a)
    assert [t for t, _ in a] != sorted(t for t, _ in a)
    assert len(sortear_instantes([1, None], 2.0, 40, 0)) == 1
    assert sum(histograma([0.1, 3, 500]).values()) == 2  # 500 fica fora do último bin


PRE = {
    "video": "canal/v.mp4",
    "modelo": "artefatos/m.pt",
    "telas": [
        {"id": 1, "quadro_ref_s": 10.0},
        {"id": 2, "quadro_ref_s": 50.0},
        {"id": 3, "quadro_ref_s": 90.0},
    ],
}


def estado() -> dict:
    """Estado de página com notas, remoção, junção e instantes dos 3 tipos."""
    return {
        "telas": [
            {
                "id": 1,
                "conferida": True,
                "junta_em": None,
                "notas": [
                    {"corda": 2, "casa": "0", "x_quadro": 224, "removida": False},
                    {"corda": 6, "casa": "3", "x_quadro": 224.0, "removida": False},
                    {"corda": 1, "casa": "9", "x_quadro": 300, "removida": True},
                    {"corda": 3, "casa": "", "x_quadro": 310, "removida": False},
                ],
            },
            {"id": 2, "conferida": False, "junta_em": 1, "notas": []},
            {"id": 3, "conferida": False, "junta_em": None, "notas": []},
        ],
        "instantes": [
            {"t": 52.0, "estado": "coluna", "tela": 2, "coluna_x_quadro": 224.04},
            {"t": 11.0, "estado": "nenhuma", "tela": 1, "coluna_x_quadro": None},
            {"t": 70.0, "estado": "sem_tablatura", "tela": 3, "coluna_x_quadro": None},
            {"t": 91.0, "estado": "coluna", "tela": None, "coluna_x_quadro": 500},
            {"t": 5.0, "estado": None, "tela": 1, "coluna_x_quadro": None},
        ],
    }


def test_montar_ouro() -> None:
    """Formato do plano: remove não-nota e sem casa, junta telas, remapeia instantes."""
    ouro = montar_ouro(PRE, estado(), agora="2026-10-10T12:00:00")
    assert validar_ouro(ouro) == []
    assert [t["id"] for t in ouro["telas"]] == [1, 3]
    assert ouro["telas"][0]["notas"] == [
        {"corda": 2, "casa": 0, "x_quadro": 224.0},
        {"corda": 6, "casa": 3, "x_quadro": 224.0},
    ]
    assert ouro["telas"][0]["conferida"] is True
    por_t = {i["t"]: i for i in ouro["instantes"]}
    assert len(por_t) == 4  # o instante sem resposta não entra
    assert por_t[52.0]["tela"] == 1 and por_t[52.0]["coluna_x_quadro"] == 224.0
    assert por_t[11.0]["coluna_x_quadro"] is None and por_t[11.0]["tela"] == 1
    assert por_t[70.0] == {
        "t": 70.0,
        "tela": None,
        "coluna_x_quadro": None,
        "obs": "sem tablatura",
    }
    assert por_t[91.0]["tela"] == 3  # tela mais próxima no tempo
    assert "artefatos/m.pt" in ouro["como_foi_rotulado"]
    assert "leitura visual" in ouro["como_foi_rotulado"]
    assert ouro["juntadas"] == {"2": 1}
    assert [i["t"] for i in ouro["instantes"]] == sorted(por_t)


def test_validar_ouro_acusa_problemas() -> None:
    """Corda fora de 1-6, tela inexistente e id repetido são recusados."""
    ruim = {
        "video": "v",
        "como_foi_rotulado": "x",
        "telas": [
            {
                "id": 1,
                "quadro_ref_s": 1.0,
                "notas": [{"corda": 7, "casa": 0, "x_quadro": 1}],
            },
            {"id": 1, "quadro_ref_s": 2.0, "notas": []},
        ],
        "instantes": [{"t": 1.0, "tela": 9, "coluna_x_quadro": None}],
    }
    erros = " | ".join(validar_ouro(ruim))
    assert "corda inválida" in erros and "repetido" in erros and "tela 9" in erros
    with pytest.raises(ValueError):
        montar_ouro(
            PRE,
            {"telas": [{"id": 1, "notas": [{"corda": 9, "casa": "1", "x_quadro": 1}]}]},
        )


def test_gravar_atomico(tmp_path: Path) -> None:
    """Grava, substitui sem deixar temporário e cria o diretório."""
    destino = tmp_path / "a" / "ouro.json"
    gravar_atomico(destino, {"a": 1})
    gravar_atomico(destino, {"a": 2, "b": "ç"})
    assert json.loads(destino.read_text(encoding="utf-8")) == {"a": 2, "b": "ç"}
    assert [p.name for p in destino.parent.iterdir()] == ["ouro.json"]


def test_slug() -> None:
    """Nome do vídeo vira slug sem acento."""
    assert (
        fazer_slug("Retrato Brasileiro - tab & lesson")
        == "retrato_brasileiro_tab_lesson"
    )


def test_servidor_grava_no_post(tmp_path: Path) -> None:
    """GET serve página/imagem; POST /salvar grava o arquivo; resposta ruim não grava."""
    pasta = tmp_path / "pasta"
    (pasta / "telas").mkdir(parents=True)
    (pasta / "telas" / "001.png").write_bytes(b"\x89PNG")
    (pasta / "pre.json").write_text(json.dumps(PRE), encoding="utf-8")
    ouro = tmp_path / "gold" / "v.json"
    servidor = criar_servidor(pasta, ouro, 0)
    assert servidor.server_address[0] == "127.0.0.1"
    porta = servidor.server_address[1]
    fio = threading.Thread(target=servidor.serve_forever, daemon=True)
    fio.start()
    try:

        def pedir(metodo: str, caminho: str, corpo: bytes | None = None, host=None):
            con = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
            con.request(metodo, caminho, corpo, {"Host": host or f"127.0.0.1:{porta}"})
            r = con.getresponse()
            dados = r.read()
            con.close()
            return r.status, dados

        status, dados = pedir("GET", "/")
        assert status == 200 and b"/salvar" in dados
        assert pedir("GET", "/telas/001.png") == (200, b"\x89PNG")
        assert pedir("GET", "/../pre.json")[0] in {200, 404}
        assert pedir("GET", "/%2e%2e/%2e%2e/etc/passwd")[0] == 404
        assert json.loads(pedir("GET", "/ouro.json")[1]) == {}
        assert pedir("GET", "/", host="evil.example")[0] == 403

        status, dados = pedir("POST", "/salvar", json.dumps(estado()).encode())
        assert status == 200 and json.loads(dados)["ok"] is True
        salvo = json.loads(ouro.read_text(encoding="utf-8"))
        assert [t["id"] for t in salvo["telas"]] == [1, 3]
        assert salvo["ferramenta"]["telas"][0]["id"] == 1  # permite retomar
        assert json.loads(pedir("GET", "/ouro.json")[1]) == salvo

        antes = ouro.read_bytes()
        assert pedir("POST", "/salvar", b"{nao json")[0] == 400
        assert (
            pedir(
                "POST",
                "/salvar",
                b'{"telas":[{"id":1,"notas":[{"corda":9,"casa":"1","x_quadro":1}]}]}',
            )[0]
            == 400
        )
        assert ouro.read_bytes() == antes
    finally:
        servidor.shutdown()
        servidor.server_close()


def test_painel_com_caixas_contem_todas() -> None:
    """Painel estreito + caixas largas (tela 1 do retrato): o recorte as contém."""
    caixas = [[100, 300, 120, 320], [1790, 310, 1810, 330], [60, 280, 80, 300]]
    x0, y0, x1, y1 = painel_com_caixas((70, 285, 1217, 457), caixas, (1080, 1920, 3))
    assert all(x0 <= c[0] and c[2] <= x1 for c in caixas)
    assert all(y0 <= c[1] and c[3] <= y1 for c in caixas)
    assert (x0, y0, x1, y1) == (52, 272, 1818, 457)


def test_painel_com_caixas_nao_mexe_se_ja_contem() -> None:
    """Sem caixa fora, o painel fica como está (e respeita a borda do quadro)."""
    rect = (70, 285, 1854, 457)
    assert painel_com_caixas(rect, [[100, 300, 120, 320]], (1080, 1920, 3)) == rect
    assert painel_com_caixas((0, 0, 50, 50), [[40, 40, 60, 60]], (55, 55, 3)) == (
        0,
        0,
        55,
        55,
    )


# --- ouro v2: fusão do v1 com as páginas do tab.telas ---------------------------


def _nota(corda: int, casa: int, x: float) -> dict:
    return {"corda": corda, "casa": casa, "x_quadro": x, "x_centro_quadro": x + 5}


def _pagina(id_: int, ref: float, exib: list, notas: list | None = None) -> dict:
    return {
        "id": id_,
        "quadro_ref_s": ref,
        "exibicoes": exib,
        "passo": 20.0,
        "notas": notas or [_nota(1, 9, 50.0)],
    }


def _v1() -> dict:
    return {
        "telas": [
            {"id": 1, "quadro_ref_s": 15.0, "notas": [_nota(1, 0, 10.0)]},
            {"id": 2, "quadro_ref_s": 42.0, "notas": [_nota(2, 3, 30.0)]},
            {"id": 3, "quadro_ref_s": 48.0, "notas": [_nota(2, 3, 31.0)]},
        ],
        "instantes": [
            {"t": 44, "tela": 2, "coluna_x_quadro": 30.5, "obs": "x"},
            {"t": 12, "tela": 1, "coluna_x_quadro": None, "obs": "nenhuma acesa"},
            {"t": 90, "tela": None, "coluna_x_quadro": None, "obs": "sem tablatura"},
            {"t": 25, "tela": 1, "coluna_x_quadro": 70.0, "obs": ""},
        ],
    }


def _paginas() -> list[dict]:
    return [
        _pagina(1, 15.0, [[10, 20]]),
        _pagina(2, 28.0, [[20, 40]]),
        _pagina(3, 46.0, [[40, 60], [100, 110]]),
    ]


def test_pagina_em_usa_exibicao_semiaberta() -> None:
    """A exibição é [t0, t1): t1 já é a página seguinte."""
    paginas = _paginas()
    assert pagina_em(paginas, 20.0) == 2
    assert pagina_em(paginas, 105.0) == 3
    assert pagina_em(paginas, 75.0) is None


def test_fusao_copia_pelo_quadro_ref_e_marca_origem() -> None:
    """A tela v1 cujo quadro_ref_s cai na exibição dá as notas à página."""
    estado, rel = fundir_ouro(_v1(), _paginas())
    p1 = estado["telas"][0]
    assert p1["origem"].startswith("ouro_v1") and p1["conferida"] is True
    assert [(n["corda"], n["casa"]) for n in p1["notas"]] == [(1, "0")]
    assert rel["herdadas"] == [1, 3] and rel["a_rotular"] == [2]


def test_fusao_pagina_sem_v1_fica_com_o_modelo_a_rotular() -> None:
    """Página sem tela v1: notas do modelo, não conferida, a rotular."""
    estado, rel = fundir_ouro(_v1(), _paginas())
    p2 = estado["telas"][1]
    assert p2["origem"].startswith("modelo") and p2["conferida"] is False
    assert [(n["corda"], n["casa"], n["origem"]) for n in p2["notas"]] == [
        (1, "9", "modelo")
    ]
    assert rel["notas_a_rotular"] == 1


def test_fusao_conflito_de_duas_telas_v1_na_mesma_pagina() -> None:
    """Duas telas v1 na página 3: usa a de ref mais próxima e RELATA a divergência."""
    v1 = _v1()
    v1["telas"][2]["notas"] = [_nota(2, 5, 31.0)]  # casa diferente da tela 2
    estado, rel = fundir_ouro(v1, _paginas())
    assert estado["telas"][2]["v1_usada"] == 3  # ref 48 é a mais perto de 45
    assert estado["telas"][2]["v1_telas"] == [2, 3]
    assert estado["telas"][2]["conferida"] is False  # conflito: o dono decide
    assert estado["telas"][0]["conferida"] is True
    assert len(rel["conflitos"]) == 1
    c = rel["conflitos"][0]
    assert (c["pagina"], c["usada_v1"], c["outra_v1"]) == (3, 3, 2)
    assert c["so_na_usada"] == [(2, "5", 31.0)] and c["so_na_outra"] == [(2, "3", 30.0)]


def test_fusao_duas_telas_v1_que_concordam_nao_geram_conflito() -> None:
    """Mesma nota a 1 px de diferença: concordam."""
    _, rel = fundir_ouro(_v1(), _paginas())
    assert rel["conflitos"] == []


def test_fusao_reatribui_instante_por_tempo() -> None:
    """t, coluna e obs ficam; a tela vira a página da exibição; não confirmada."""
    estado, rel = fundir_ouro(_v1(), _paginas())
    por_t = {i["t"]: i for i in estado["instantes"]}
    assert [i["t"] for i in estado["instantes"]] == [12, 25, 44, 90]
    assert por_t[25]["tela"] == 2 and por_t[25]["tela_v1"] == 1  # v1 dizia tela 1
    assert por_t[25]["coluna_x_quadro"] == 70.0 and por_t[44]["obs"] == "x"
    assert por_t[44]["tela"] == 3 and por_t[12]["estado"] == "nenhuma"
    assert por_t[90]["estado"] == "sem_tablatura" and por_t[90]["tela"] is None
    assert not any(i["tela_confirmada"] for i in estado["instantes"])
    assert [r["t"] for r in rel["instantes_reatribuidos"]] == [25]


def test_montar_ouro_v2_leva_origem_e_confirmacao_e_valida() -> None:
    """O estado fundido vira um ouro válido com origem, v1_telas e tela_confirmada."""
    estado, rel = fundir_ouro(_v1(), _paginas())
    pre = {
        "video": "v.mp4",
        "modelo": "m.pt",
        "como_foi_rotulado": "fusão",
        "telas": [
            {"id": p["id"], "quadro_ref_s": p["quadro_ref_s"]} for p in _paginas()
        ],
    }
    ouro = montar_ouro(pre, estado, agora="2026-10-10T00:00:00")
    assert validar_ouro(ouro) == []
    assert ouro["como_foi_rotulado"] == "fusão"
    assert ouro["telas"][0]["origem"].startswith("ouro_v1")
    assert ouro["telas"][2]["v1_telas"] == [2, 3]
    assert all(i["tela_confirmada"] is False for i in ouro["instantes"])
    assert rel["n_paginas"] == 3


def test_montar_ouro_v1_continua_sem_campos_novos() -> None:
    """Compatibilidade: estado do v1 (sem origem/tela_confirmada) não ganha campos."""
    pre = {"video": "v", "modelo": "m", "telas": [{"id": 1, "quadro_ref_s": 1.0}]}
    estado = {
        "telas": [{"id": 1, "notas": []}],
        "instantes": [{"t": 1, "estado": "nenhuma", "tela": 1}],
    }
    ouro = montar_ouro(pre, estado)
    assert "origem" not in ouro["telas"][0]
    assert "tela_confirmada" not in ouro["instantes"][0]


def test_comparar_notas_tolera_x() -> None:
    """Mesma corda/casa com x a 5 px é igual; casa diferente não."""
    a = [_nota(1, 3, 10.0), _nota(2, 0, 50.0)]
    b = [_nota(1, 3, 15.0), _nota(2, 1, 50.0)]
    r = comparar_notas(a, b)
    assert (
        r["iguais"] == 1
        and r["so_a"] == [(2, "0", 50.0)]
        and r["so_b"] == [(2, "1", 50.0)]
    )


def test_pagina_liga_as_abas_e_todo_id_usado_existe() -> None:
    """Trava o defeito "clicar na aba não troca": handlers presentes e ids existentes."""
    assert 'getElementById("aba-inst").addEventListener("click"' in PAGINA
    assert 'getElementById("aba-telas").addEventListener("click"' in PAGINA
    assert 'irParaAba("instantes")' in PAGINA
    usados = set(re.findall(r'getElementById\("([^"]+)"\)', PAGINA))
    declarados = set(re.findall(r'id="([^"]+)"', PAGINA.split("<script>")[0]))
    assert usados <= declarados, usados - declarados


def test_fusao_tela_v1_na_borda_vai_para_a_pagina_cujas_notas_concordam() -> None:
    """ref 20.2 cai na página 1 [10,20)? Não: é 2 [20,40); mas ref 19.9 com notas da 2."""
    v1 = _v1()
    v1["telas"] = [
        {
            "id": 1,
            "quadro_ref_s": 19.9,
            "notas": [_nota(1, 9, 50.0)],
        },  # = modelo da pág. 2
    ]
    v1["instantes"] = []
    paginas = [
        _pagina(1, 15.0, [[10, 20]], [_nota(3, 1, 10.0)]),
        _pagina(2, 28.0, [[20, 40]], [_nota(1, 9, 50.0)]),
    ]
    estado, rel = fundir_ouro(v1, paginas)
    assert rel["herdadas"] == [2] and rel["a_rotular"] == [1]
    assert rel["telas_v1_na_borda"][0]["contem_o_instante"] == 1
    assert estado["telas"][1]["origem"].startswith("ouro_v1")


# --- vídeo NOVO, sem ouro v1 --------------------------------------------------------


def test_sem_v1_toda_pagina_fica_a_rotular_com_notas_do_modelo() -> None:
    """Sem v1: nenhuma página herdada, todas ``conferida: false`` com o modelo."""
    estado, rel = fundir_sem_v1(_paginas(), 120.0, 2.0, 10, 0)
    assert [t["conferida"] for t in estado["telas"]] == [False, False, False]
    assert all(t["origem"].startswith("modelo") for t in estado["telas"])
    assert all(n["origem"] == "modelo" for t in estado["telas"] for n in t["notas"])
    assert rel["herdadas"] == [] and rel["a_rotular"] == [1, 2, 3]
    assert rel["notas_a_rotular"] == 3 and rel["conflitos"] == []


def test_sem_v1_instantes_na_presenca_sem_coluna_e_com_pagina_sugerida() -> None:
    """Instantes só onde há página, sem resposta, página sugerida e não confirmada."""
    paginas = _paginas()
    estado, _ = fundir_sem_v1(paginas, 120.0, 2.0, 10, 0)
    instantes = estado["instantes"]
    assert len(instantes) == 10
    for i in instantes:
        assert i["tela"] == pagina_em(paginas, i["t"]) and i["tela"] is not None
        assert i["estado"] is None and i["coluna_x_quadro"] is None
        assert i["tela_confirmada"] is False and i["pagina_sugerida"] is True
    assert not any(60 <= i["t"] < 100 for i in instantes)  # fora das exibições


def test_sem_v1_e_reprodutivel_e_depende_da_semente() -> None:
    """Mesma semente, mesmos instantes; outra semente, outro sorteio."""
    a = fundir_sem_v1(_paginas(), 120.0, 2.0, 10, 3)[0]["instantes"]
    b = fundir_sem_v1(_paginas(), 120.0, 2.0, 10, 3)[0]["instantes"]
    c = fundir_sem_v1(_paginas(), 120.0, 2.0, 10, 4)[0]["instantes"]
    assert [i["t"] for i in a] == [i["t"] for i in b]
    assert [i["t"] for i in a] != [i["t"] for i in c]


def test_sem_v1_gera_ouro_inicial_valido_e_registra_a_sugestao() -> None:
    """O ouro inicial é válido; instante respondido leva ``pagina_sugerida``."""
    estado, rel = fundir_sem_v1(_paginas(), 120.0, 2.0, 4, 0)
    pre = {
        "video": "v.mp4",
        "modelo": "m.pt",
        "como_foi_rotulado": texto_sem_v1(rel),
        "telas": [
            {"id": p["id"], "quadro_ref_s": p["quadro_ref_s"]} for p in _paginas()
        ],
    }
    inicial = montar_ouro(pre, estado, agora="2026-10-12T00:00:00")
    assert validar_ouro(inicial) == []
    assert all(t["conferida"] is False for t in inicial["telas"])
    assert inicial["instantes"] == []  # nada respondido ainda
    assert "viés" in inicial["como_foi_rotulado"]
    estado["instantes"][0]["estado"] = "coluna"
    estado["instantes"][0]["coluna_x_quadro"] = 33.0
    estado["instantes"][1]["estado"] = "nenhuma"
    ouro = montar_ouro(pre, estado)
    assert validar_ouro(ouro) == []
    assert len(ouro["instantes"]) == 2
    assert all(i["pagina_sugerida"] is True for i in ouro["instantes"])
    assert all(i["tela_confirmada"] is False for i in ouro["instantes"])


def test_tecnica_marcada_entra_no_ouro_em_ordem_fixa() -> None:
    """Técnica do dono vai para a nota do ouro; nota sem técnica não ganha o campo."""
    est = estado()
    est["telas"][0]["notas"][0]["tecnica"] = ["lig", "h"]
    ouro = montar_ouro(PRE, est, agora="2026-10-10T12:00:00")
    assert validar_ouro(ouro) == []
    notas = ouro["telas"][0]["notas"]
    assert [n.get("tecnica") for n in notas] == [["h", "lig"], None]


def test_tecnica_desconhecida_e_acusada() -> None:
    """Código fora de TECNICAS não passa na validação."""
    ouro = montar_ouro(PRE, estado(), agora="2026-10-10T12:00:00")
    ouro["telas"][0]["notas"][0]["tecnica"] = ["martelo"]
    assert any("técnica" in e for e in validar_ouro(ouro))


def test_pagina_recebe_o_vocabulario_de_tecnicas() -> None:
    """O JS usa o mesmo dicionário do Python (sem marcador por substituir)."""
    assert "__TECNICAS__" not in PAGINA
    assert json.dumps(TECNICAS, ensure_ascii=False) in PAGINA
