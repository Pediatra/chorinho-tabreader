"""Gabarito dos dedos: amostra, caixas, registro e o servidor, sem GPU e sem acervo."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pytest

from tab.maos_gabarito import (
    acorde_da_coluna,
    amostrar_notas,
    ampliar_caixa,
    atualizar_resposta,
    caixa_da_nota,
    caixa_final,
    completas,
    criar_servidor,
    escolher_caixa,
    gabarito_novo,
    linhas_confiaveis,
    mesclar_gabarito,
    perguntas,
    recortar_caixa,
    redimensionar_altura,
    texto_acorde,
    validar_resposta,
    y_da_corda,
)


def _notas_sinteticas(n: int, com_casa_zero: int = 0) -> list[dict]:
    """Notas com ``t_ini`` distintos; as primeiras ``com_casa_zero`` são corda solta.

    Args:
        n: quantas notas.
        com_casa_zero: quantas (no início) têm casa 0.

    Returns:
        Lista no formato do ``mvp.json`` (só os campos usados).
    """
    notas = []
    for i in range(n):
        casa = 0 if i < com_casa_zero else 1 + i % 5
        notas.append(
            {
                "tela": 1,
                "corda": 1 + i % 6,
                "casa": casa,
                "x_quadro": 100 + i,
                "x_centro_quadro": 110.0 + i,
                "coluna": i,
                "t_ini": round(10.0 + i * 0.5, 3),
            }
        )
    return notas


def test_amostra_tem_32_com_casa_e_8_de_corda_solta() -> None:
    """A amostra padrão tem 32 notas com casa > 0 e 8 com casa 0, ids n01..n40."""
    notas = _notas_sinteticas(300, com_casa_zero=60)
    amostra = amostrar_notas(notas, semente=20261012)
    assert len(amostra) == 40
    assert sum(1 for a in amostra if a["casa"] == 0) == 8
    assert sum(1 for a in amostra if a["casa"] > 0) == 32
    assert [a["id"] for a in amostra] == [f"n{k:02d}" for k in range(1, 41)]


def test_amostra_em_ordem_de_tempo_e_deterministica() -> None:
    """Mesma semente, mesma amostra; e a lista sai ordenada por ``t_ini``."""
    notas = _notas_sinteticas(300, com_casa_zero=60)
    primeira = amostrar_notas(notas, semente=7)
    segunda = amostrar_notas(notas, semente=7)
    assert primeira == segunda
    tempos = [a["t_ini"] for a in primeira]
    assert tempos == sorted(tempos)


def test_amostra_estratifica_um_por_faixa() -> None:
    """Com 64 notas de casa > 0 e 32 faixas, cada par consecutivo tem exatamente uma."""
    notas = _notas_sinteticas(64)  # todas com casa > 0 (com_casa_zero=0)
    amostra = amostrar_notas(notas, semente=3, n_com_casa=32, n_corda_solta=0)
    indices = sorted(a["indice_mvp"] for a in amostra)
    assert len(indices) == 32
    for faixa in range(32):
        assert sum(1 for i in indices if i // 2 == faixa) == 1


def test_amostra_recusa_grupo_pequeno() -> None:
    """Pedir mais faixas do que notas candidatas é erro, não amostra torta."""
    notas = _notas_sinteticas(10)
    with pytest.raises(ValueError):
        amostrar_notas(notas, n_com_casa=32, n_corda_solta=0)


def test_ampliar_caixa_quarenta_por_cento_de_cada_lado() -> None:
    """A folga é 40% do tamanho da caixa em cada lado (x pela largura, y pela altura)."""
    assert ampliar_caixa([100, 100, 200, 200], 0.4, (1080, 1920)) == (60, 60, 240, 240)


def test_ampliar_caixa_limita_ao_quadro() -> None:
    """Caixa encostada na borda não sai do quadro."""
    assert ampliar_caixa([0, 0, 50, 50], 0.4, (1080, 1920)) == (0, 0, 70, 70)
    assert ampliar_caixa([1800, 1000, 1900, 1070], 0.4, (1080, 1920)) == (
        1760,
        972,
        1920,
        1080,
    )


def test_ampliar_caixa_fora_do_quadro_recusa() -> None:
    """Caixa totalmente fora do quadro não vira recorte vazio em silêncio."""
    with pytest.raises(ValueError):
        ampliar_caixa([-500, -500, -400, -400], 0.0, (1080, 1920))


def _mp(lado: str, score: float, caixa: list[float], na_tab: bool = False) -> dict:
    """Mão do MediaPipe no formato de ``DetectorMaos`` (só os campos usados).

    Args:
        lado: ``L`` ou ``R``.
        score: score do MediaPipe.
        caixa: caixa no quadro.
        na_tab: se a caixa está sobre a tablatura.

    Returns:
        A mão.
    """
    return {"lado": lado, "score": score, "caixa": caixa, "na_tab": na_tab}


def test_escolher_caixa_mediapipe_de_maior_score_do_lado() -> None:
    """Entre as mãos do MediaPipe do lado pedido, vale a de maior score."""
    maos = [
        _mp("L", 0.95, [1600, 800, 1800, 1050]),
        _mp("L", 0.7, [1500, 700, 1700, 1000]),
        _mp("R", 0.99, [130, 700, 480, 950]),
    ]
    escolha = escolher_caixa("esquerda", maos, [], (1080, 1920))
    assert escolha["origem"] == "mediapipe"
    assert escolha["caixa"] == [1600.0, 800.0, 1800.0, 1050.0]
    assert escolha["score"] == 0.95


def test_escolher_caixa_ignora_mao_sobre_a_tablatura() -> None:
    """Mão do MediaPipe marcada ``na_tab`` não conta: cai para o Wholebody."""
    maos = [_mp("R", 0.99, [300, 300, 400, 400], na_tab=True)]
    pessoas = [
        {
            "caixa": [0, 0, 10, 10],
            "direita": {"caixa": [120, 700, 470, 940], "media": 0.8, "pts": []},
            "esquerda": {"caixa": [1600, 800, 1800, 1050], "media": 0.5, "pts": []},
        }
    ]
    escolha = escolher_caixa("direita", maos, pessoas, (1080, 1920))
    assert escolha["origem"] == "wholebody"
    assert escolha["caixa"] == [120.0, 700.0, 470.0, 940.0]


def test_escolher_caixa_fallback_e_metade_inferior() -> None:
    """Sem mão nenhuma, a caixa é a metade inferior inteira, marcada ``fallback``."""
    escolha = escolher_caixa("esquerda", [], [], (1080, 1920))
    assert escolha["origem"] == "fallback"
    assert escolha["score"] is None
    assert caixa_final(escolha, (1080, 1920)) == (0, 540, 1920, 1080)


def test_caixa_final_amplia_quando_nao_e_fallback() -> None:
    """Caixa do MediaPipe/Wholebody é ampliada; o fallback não."""
    escolha = {"origem": "mediapipe", "caixa": [100.0, 100.0, 200.0, 200.0], "score": 1}
    assert caixa_final(escolha, (1080, 1920)) == (60, 60, 240, 240)


def test_recortar_e_redimensionar() -> None:
    """Recorte sai com o tamanho da caixa; redimensionar mantém a proporção."""
    quadro = np.zeros((100, 200, 3), dtype=np.uint8)
    recorte = recortar_caixa(quadro, (10, 20, 60, 70))
    assert recorte.shape == (50, 50, 3)
    grande = redimensionar_altura(recorte, 700)
    assert grande.shape == (700, 700, 3)
    with pytest.raises(ValueError):
        recortar_caixa(quadro, (300, 300, 400, 400))


def _gabarito(video: str = "sky/v.mp4", n: int = 4) -> dict:
    """Gabarito novo com ``n`` notas da amostra sintética.

    Args:
        video: chave do vídeo.
        n: quantas notas.

    Returns:
        O registro com respostas em branco.
    """
    amostra = amostrar_notas(
        _notas_sinteticas(200), semente=1, n_com_casa=n, n_corda_solta=0
    )
    return gabarito_novo(video, amostra, 1)


def test_gabarito_novo_comeca_sem_respostas() -> None:
    """Todas as respostas começam em ``None`` e o formato do plano está completo."""
    gab = _gabarito()
    assert gab["video"] == "sky/v.mp4"
    assert all(n["esquerda"] is None and n["direita"] is None for n in gab["notas"])
    assert completas(gab) == 0
    assert set(gab["notas"][0]) >= {"id", "indice_mvp", "corda", "casa", "t_ini"}


def test_mesclar_preserva_respostas_existentes() -> None:
    """Respostas dadas antes são copiadas para o gabarito recém-montado."""
    existente = _gabarito()
    atualizar_resposta(
        existente, "n01", {"esquerda": "2", "direita": "p"}, "2026-10-12T10:00:00"
    )
    atualizar_resposta(existente, "n02", {"obs": "dedo oculto"}, "2026-10-12T10:01:00")
    novo = mesclar_gabarito(_gabarito(), existente)
    n01 = next(n for n in novo["notas"] if n["id"] == "n01")
    assert (n01["esquerda"], n01["direita"]) == ("2", "p")
    assert next(n for n in novo["notas"] if n["id"] == "n02")["obs"] == "dedo oculto"


def test_mesclar_recusa_resposta_orfa_e_outro_video() -> None:
    """Resposta sem nota correspondente na amostra nova é recusada, não apagada."""
    existente = _gabarito()
    atualizar_resposta(existente, "n01", {"esquerda": "1"}, "agora")
    novo = _gabarito()
    novo["notas"][0]["indice_mvp"] = 999999
    with pytest.raises(ValueError):
        mesclar_gabarito(novo, existente)
    with pytest.raises(ValueError):
        mesclar_gabarito(_gabarito(video="outro.mp4"), existente)


def test_atualizar_resposta_valida_e_completa() -> None:
    """Respostas válidas entram; ``completas`` conta as notas com as duas."""
    gab = _gabarito()
    atualizar_resposta(gab, "n03", {"esquerda": "?"}, "t1")
    assert completas(gab) == 0
    nota = atualizar_resposta(gab, "n03", {"direita": "m"}, "t2")
    assert nota["respondido_em"] == "t2"
    assert completas(gab) == 1
    atualizar_resposta(gab, "n03", {"esquerda": None}, "t3")
    assert completas(gab) == 0


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("esquerda", "5"),
        ("esquerda", 1),
        ("direita", "x"),
        ("direita", "P"),
        ("obs", 12),
        ("obs", "x" * 501),
        ("pe", "1"),
    ],
)
def test_validar_resposta_rejeita_valor_invalido(campo: str, valor: object) -> None:
    """Dedo inexistente, tipo errado ou campo desconhecido são recusados."""
    with pytest.raises(ValueError):
        validar_resposta(campo, valor)


def test_validar_resposta_aceita_os_valores_do_plano() -> None:
    """Todos os dedos do plano e ``None`` (limpar) passam."""
    for valor in ("0", "1", "2", "3", "4", "?"):
        validar_resposta("esquerda", valor)
    for valor in ("p", "i", "m", "a", "c", "?"):
        validar_resposta("direita", valor)
    validar_resposta("esquerda", None)
    validar_resposta("obs", "")


def test_servidor_grava_resposta_e_recusa_invalida(tmp_path: Path) -> None:
    """POST grava no arquivo (cópia), GET devolve o estado, valor inválido vira 400."""
    ouro = tmp_path / "gabarito.json"
    ouro.write_text(json.dumps(_gabarito(), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "indice.json").write_text("{}", encoding="utf-8")
    servidor = criar_servidor(tmp_path, ouro, porta=0)
    porta = servidor.server_address[1]
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{porta}"

        def post(corpo: dict) -> tuple[int, dict]:
            req = urllib.request.Request(
                base + "/responder",
                data=json.dumps(corpo).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as erro:
                return erro.code, json.loads(erro.read())

        status, dados = post({"id": "n01", "esquerda": "3", "direita": "i"})
        assert status == 200
        assert dados["completas"] == 1
        gravado = json.loads(ouro.read_text(encoding="utf-8"))
        n01 = next(n for n in gravado["notas"] if n["id"] == "n01")
        assert (n01["esquerda"], n01["direita"]) == ("3", "i")

        assert post({"id": "n01", "esquerda": "9"})[0] == 400
        assert post({"id": "n99", "esquerda": "1"})[0] == 400

        with urllib.request.urlopen(base + "/gabarito.json") as r:
            estado = json.loads(r.read())
        assert completas(estado) == 1
        with urllib.request.urlopen(base + "/") as r:
            assert b"Dedos do gabarito" in r.read()
    finally:
        servidor.shutdown()
        servidor.server_close()


PAINEL = [70, 297, 1854, 446]
PASSO = 21.6


def _seis_linhas(y0: float, passo: float) -> list[float]:
    """Seis linhas de corda, com espaçamento ``passo``, a partir de ``y0``.

    Args:
        y0: altura da primeira linha (corda 1).
        passo: espaçamento entre cordas, em px.

    Returns:
        As seis alturas, de cima para baixo.
    """
    return [y0 + k * passo for k in range(6)]


def test_acorde_so_com_mesma_tela_coluna_e_instante() -> None:
    """Nota de outro instante, na mesma coluna, e nota de outra tela não entram."""
    notas = [
        {"tela": 1, "coluna": 5, "t_ini": 10.0, "corda": 1, "casa": 0},
        {"tela": 1, "coluna": 5, "t_ini": 10.0, "corda": 3, "casa": 2},
        {"tela": 1, "coluna": 5, "t_ini": 10.0, "corda": 5, "casa": 3},
        {"tela": 1, "coluna": 5, "t_ini": 20.0, "corda": 2, "casa": 7},
        {"tela": 2, "coluna": 5, "t_ini": 10.0, "corda": 6, "casa": 1},
    ]
    acorde = acorde_da_coluna(notas, 1)
    assert [(a["corda"], a["casa"]) for a in acorde] == [(1, 0), (3, 2), (5, 3)]
    assert acorde_da_coluna(notas, 3) == [{"indice_mvp": 3, "corda": 2, "casa": 7}]


def test_texto_acorde_marca_a_nota_pedida() -> None:
    """O texto lista o acorde inteiro e marca só a nota pedida com <- ESTA."""
    acorde = [
        {"indice_mvp": 4, "corda": 1, "casa": 0},
        {"indice_mvp": 7, "corda": 3, "casa": 2},
        {"indice_mvp": 9, "corda": 5, "casa": 3},
    ]
    assert texto_acorde(acorde, 7) == (
        "acorde: c1 casa 0 | c3 casa 2 <- ESTA | c5 casa 3"
    )


def test_perguntas_citam_corda_e_casa() -> None:
    """Cada mão pergunta pela corda da nota; a esquerda também cita a casa."""
    esquerda, direita = perguntas(3, 2)
    assert esquerda == "Mão esquerda: que dedo pisa a corda 3 (casa 2)?"
    assert direita == "Mão direita: que dedo toca a corda 3?"


def test_linhas_confiaveis_exige_seis_regulares_no_passo() -> None:
    """Seis linhas regulares no passo do painel valem; as outras não."""
    assert linhas_confiaveis(_seis_linhas(300, PASSO), PASSO)
    assert not linhas_confiaveis(_seis_linhas(300, PASSO)[:5], PASSO)
    assert not linhas_confiaveis(_seis_linhas(300, PASSO), 40.0)
    assert not linhas_confiaveis([300, 321, 343, 380, 401, 423], PASSO)
    assert not linhas_confiaveis(None, PASSO)


def test_y_da_corda_segmentacao_ordena_de_cima_para_baixo() -> None:
    """Com linhas válidas, a corda 1 é a de menor y (a mais aguda), mesmo fora de ordem."""
    linhas = list(reversed(_seis_linhas(300, PASSO)))
    y1, origem = y_da_corda(1, linhas, PAINEL, PASSO)
    assert (y1, origem) == (300.0, "segmentacao")
    y6, _ = y_da_corda(6, linhas, PAINEL, PASSO)
    assert y6 == pytest.approx(300 + 5 * PASSO)


def test_y_da_corda_reserva_sem_seis_linhas() -> None:
    """Sem linhas válidas, a reserva é y0 do painel + (corda - 1) * passo."""
    y, origem = y_da_corda(3, None, PAINEL, PASSO)
    assert origem == "reserva"
    assert y == pytest.approx(297 + 2 * PASSO)


def test_y_da_corda_recusa_corda_fora_do_intervalo() -> None:
    """Corda 0 ou 7 não existe: recusa."""
    with pytest.raises(ValueError):
        y_da_corda(7, None, PAINEL, PASSO)
    with pytest.raises(ValueError):
        y_da_corda(0, None, PAINEL, PASSO)


def test_caixa_da_nota_tem_14_por_11_passos_centrada() -> None:
    """Caixa de 1,4 x passo de largura e 1,1 x passo de altura, centrada na nota."""
    x0, y0, x1, y1 = caixa_da_nota(1000.0, 400.0, 20.0)
    assert (x1 - x0, y1 - y0) == (28, 22)
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == (1000.0, 400.0)
