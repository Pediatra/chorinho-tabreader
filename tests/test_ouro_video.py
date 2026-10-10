"""Fase 2 / T2.1+T2.2: funções puras e o servidor da ferramenta do ouro de vídeo."""

import http.client
import json
import threading
from pathlib import Path

import numpy as np
import pytest

from tab.ouro_video import (
    Agrupador,
    agrupar_telas,
    clique_para_quadro,
    corda_mais_proxima,
    criar_servidor,
    diferenca_cinza,
    fazer_slug,
    gravar_atomico,
    histograma,
    montar_ouro,
    painel_com_caixas,
    sortear_instantes,
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
