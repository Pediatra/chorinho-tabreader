"""Gabarito dos dedos: amostra, caixas, registro e o servidor, sem GPU e sem acervo."""

from __future__ import annotations

import copy
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
    ataque_completo,
    ataque_de,
    atualizar_pestana,
    atualizar_resposta,
    caixa_da_nota,
    caixa_final,
    completas,
    criar_servidor,
    escolher_caixa,
    gabarito_novo,
    linhas_confiaveis,
    mesclar_gabarito,
    migrar_arquivo,
    migrar_gabarito,
    migrar_pestanas,
    notas_do_ataque,
    progresso_ataques,
    recortar_caixa,
    redimensionar_altura,
    servir,
    texto_acorde,
    validar_pestana,
    validar_resposta,
    y_da_corda,
)


def _pestana_vazia() -> dict:
    """Registro de pestana sem resposta (como o gabarito grava).

    Returns:
        Todos os campos de pestana em ``None``.
    """
    return {
        "pestana": None,
        "pestana_dedo": None,
        "pestana_casa": None,
        "pestana_de": None,
        "pestana_ate": None,
        "respondido_em": None,
    }


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
    """Gabarito novo (formato 2) com ``n`` ataques sintéticos, sem acorde.

    Args:
        video: chave do vídeo.
        n: quantos ataques.

    Returns:
        O registro com respostas em branco.
    """
    notas = _notas_sinteticas(200)
    amostra = amostrar_notas(notas, semente=1, n_com_casa=n, n_corda_solta=0)
    return gabarito_novo(video, amostra, 1, notas)


def _nota(tela: int, coluna: int, t: float, corda: int, casa: int) -> dict:
    """Nota no formato do ``mvp.json`` (só os campos usados pelo acorde).

    Args:
        tela: id da tela.
        coluna: coluna da nota.
        t: ``t_ini`` da nota.
        corda: corda (1 a 6).
        casa: casa (0 = solta).

    Returns:
        A nota.
    """
    return {
        "tela": tela,
        "coluna": coluna,
        "t_ini": t,
        "corda": corda,
        "casa": casa,
        "x_centro_quadro": 500.0 + coluna,
    }


def _mvp_com_acordes() -> list[dict]:
    """Mvp mínimo: um acorde de 3 notas (a sorteada é a do meio), uma solta e uma repetida.

    Returns:
        Notas: 0 a 2 formam o acorde em t=10; 3 é solta em t=20; 4 é outra tela no mesmo t.
    """
    return [
        _nota(1, 5, 10.0, 1, 0),
        _nota(1, 5, 10.0, 3, 2),
        _nota(1, 5, 10.0, 5, 3),
        _nota(1, 6, 20.0, 2, 7),
        _nota(2, 5, 10.0, 6, 1),
    ]


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


def test_texto_acorde_lista_as_notas_sem_marcar_nenhuma() -> None:
    """O cabeçalho lista o acorde em ordem de corda, sem marca de nota pedida."""
    acorde = [
        {"corda": 1, "casa": 0},
        {"corda": 3, "casa": 2},
        {"corda": 5, "casa": 3},
    ]
    assert texto_acorde(acorde) == "acorde: c1 casa 0 | c3 casa 2 | c5 casa 3"


def test_ataque_de_troca_o_n_por_a() -> None:
    """O ataque tem o mesmo número da nota da amostra."""
    assert ataque_de("n02") == "a02"
    assert ataque_de("n40") == "a40"


def test_nota_sem_acorde_vira_ataque_de_uma_nota() -> None:
    """Nota sozinha na coluna: o ataque tem só ela, com o id da amostra."""
    notas = _mvp_com_acordes()
    ataque = notas_do_ataque({"id": "n07", "indice_mvp": 3}, notas)
    assert [(e["id"], e["ataque"], e["sorteada"]) for e in ataque] == [
        ("n07", "a07", True)
    ]


def test_ataque_expande_o_acorde_com_ids_e_ordem_de_corda() -> None:
    """Sorteada da nota do meio: as outras do acorde entram como nNN_cN, por corda."""
    notas = _mvp_com_acordes()
    ataque = notas_do_ataque({"id": "n02", "indice_mvp": 1}, notas)
    assert [(e["id"], e["corda"], e["casa"], e["sorteada"]) for e in ataque] == [
        ("n02_c1", 1, 0, False),
        ("n02", 3, 2, True),
        ("n02_c5", 5, 3, False),
    ]
    assert all(e["ataque"] == "a02" for e in ataque)
    assert all(e["t_ini"] == 10.0 for e in ataque)


def test_ataque_recusa_duas_notas_na_mesma_corda() -> None:
    """Dois registros da mesma corda no mesmo acorde não viram ids distintos: recusa."""
    notas = [*_mvp_com_acordes(), _nota(1, 5, 10.0, 3, 4)]
    with pytest.raises(ValueError):
        notas_do_ataque({"id": "n02", "indice_mvp": 1}, notas)


def test_gabarito_novo_tem_formato_3_e_uma_entrada_por_nota_do_ataque() -> None:
    """Formato 3 no topo; a amostra de 1 ataque com acorde de 3 gera 3 entradas e 1 pestana."""
    notas = _mvp_com_acordes()
    amostra = [{"id": "n02", "indice_mvp": 1}]
    gab = gabarito_novo("v.mp4", amostra, 9, notas)
    assert gab["formato"] == 3
    assert next(iter(gab)) == "formato"
    assert [n["id"] for n in gab["notas"]] == ["n02_c1", "n02", "n02_c5"]
    assert all(n["esquerda"] is None and n["direita"] is None for n in gab["notas"])
    assert gab["ataques"] == {"a02": _pestana_vazia()}


def _gabarito_v1(notas: list[dict]) -> dict:
    """Gabarito do formato 1 (antes da mudança), com respostas no n01 e n02.

    Args:
        notas: notas do mvp usadas pelas notas antigas.

    Returns:
        O registro no formato antigo (sem ``formato``, uma nota por item).
    """
    return {
        "video": "v.mp4",
        "como_foi_rotulado": "antigo",
        "semente": 1,
        "ferramenta": "tab.maos_gabarito",
        "notas": [
            {
                "id": "n01",
                "indice_mvp": 1,
                "corda": 3,
                "casa": 2,
                "t_ini": 10.0,
                "esquerda": "3",
                "direita": "m",
                "obs": "",
                "respondido_em": "2026-10-12T14:05:44",
            },
            {
                "id": "n02",
                "indice_mvp": 3,
                "corda": 2,
                "casa": 7,
                "t_ini": 20.0,
                "esquerda": "1",
                "direita": None,
                "obs": "dedo oculto",
                "respondido_em": "2026-10-12T14:05:54",
            },
        ],
    }


def test_migrar_preserva_respostas_e_acrescenta_as_do_acorde() -> None:
    """Respostas antigas ficam idênticas no mesmo id; as do acorde entram em branco."""
    notas = _mvp_com_acordes()
    antigo = _gabarito_v1(notas)
    copia_antes = copy.deepcopy(antigo)
    novo = migrar_gabarito(antigo, notas)
    assert antigo == copia_antes
    assert novo["formato"] == 3
    assert novo["video"] == "v.mp4"
    assert novo["ataques"] == {"a01": _pestana_vazia(), "a02": _pestana_vazia()}
    por_id = {n["id"]: n for n in novo["notas"]}
    assert set(por_id) == {"n01", "n01_c1", "n01_c5", "n02"}
    for velha in antigo["notas"]:
        nova = por_id[velha["id"]]
        for campo in ("indice_mvp", "corda", "casa", "t_ini", "esquerda", "direita"):
            assert nova[campo] == velha[campo]
        assert nova["obs"] == velha["obs"]
        assert nova["respondido_em"] == velha["respondido_em"]
    assert por_id["n01_c1"]["esquerda"] is None
    assert por_id["n01_c1"]["sorteada"] is False


def test_migrar_e_idempotente() -> None:
    """Rodar a migração de novo (sobre o resultado) não duplica nada nem muda nada."""
    notas = _mvp_com_acordes()
    uma = migrar_gabarito(_gabarito_v1(notas), notas)
    duas = migrar_gabarito(uma, notas)
    assert duas == uma
    assert len(duas["notas"]) == len({n["id"] for n in duas["notas"]})


def test_migrar_recusa_nota_que_nao_bate_com_o_mvp() -> None:
    """Se a corda do gabarito antigo não é a do mvp, recusa em vez de alterar."""
    notas = _mvp_com_acordes()
    antigo = _gabarito_v1(notas)
    antigo["notas"][0]["corda"] = 6
    with pytest.raises(ValueError):
        migrar_gabarito(antigo, notas)


def test_progresso_so_conta_ataque_com_notas_e_pestana() -> None:
    """Um ataque só conta como completo com as notas (esquerda e direita) E a pestana."""
    notas = _mvp_com_acordes()
    gab = gabarito_novo("v.mp4", [{"id": "n02", "indice_mvp": 1}], 9, notas)
    gab["notas"].append(
        {**gab["notas"][0], "id": "n09", "ataque": "a09", "sorteada": True}
    )
    gab["ataques"]["a09"] = _pestana_vazia()
    assert progresso_ataques(gab) == (0, 2)
    for n in gab["notas"][:2]:
        atualizar_resposta(gab, n["id"], {"esquerda": "1", "direita": "p"}, "t")
    assert progresso_ataques(gab) == (0, 2)
    atualizar_resposta(gab, "n02_c5", {"esquerda": "?", "direita": "?"}, "t")
    assert progresso_ataques(gab) == (0, 2)  # notas prontas, pestana ainda null
    atualizar_pestana(gab, "a02", {"pestana": "nao"}, "t")
    assert progresso_ataques(gab) == (1, 2)
    assert completas(gab) == 3


def test_atualizar_resposta_aceita_id_de_nota_do_acorde() -> None:
    """O id ``nNN_cN`` de uma nota acrescentada é respondido como qualquer outro."""
    notas = _mvp_com_acordes()
    gab = gabarito_novo("v.mp4", [{"id": "n02", "indice_mvp": 1}], 9, notas)
    nota = atualizar_resposta(gab, "n02_c1", {"direita": "a"}, "t")
    assert nota["direita"] == "a"
    assert nota["sorteada"] is False


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


def _gabarito_formato_2(notas: list[dict]) -> dict:
    """Gabarito no formato 2 (sem ``ataques``), com a nota ``n02`` respondida.

    Args:
        notas: notas do mvp de ``_mvp_com_acordes``.

    Returns:
        O registro no formato 2, com ataques a02 (3 notas) e a03 (1 nota).
    """
    gab = gabarito_novo(
        "v.mp4",
        [{"id": "n02", "indice_mvp": 1}, {"id": "n03", "indice_mvp": 3}],
        9,
        notas,
    )
    gab.pop("ataques")
    gab["formato"] = 2
    atualizar_resposta(gab, "n02", {"esquerda": "2", "direita": "p", "obs": "x"}, "t1")
    return gab


def test_migrar_pestanas_2_para_3_nao_muda_nenhuma_nota() -> None:
    """Formato 2 vira 3 só com a pestana em branco de cada ataque; as notas ficam iguais."""
    gab = _gabarito_formato_2(_mvp_com_acordes())
    antes = copy.deepcopy(gab)
    novo = migrar_pestanas(gab)
    assert gab == antes
    assert novo["formato"] == 3
    assert novo["notas"] == antes["notas"]
    assert novo["ataques"] == {"a02": _pestana_vazia(), "a03": _pestana_vazia()}
    assert novo["video"] == "v.mp4"


def test_migrar_pestanas_e_idempotente_e_mantem_pestana_respondida() -> None:
    """Rodar de novo não muda nada; uma pestana já respondida é mantida."""
    gab = _gabarito_formato_2(_mvp_com_acordes())
    gab["ataques"] = {
        "a03": {**_pestana_vazia(), "pestana": "nao", "respondido_em": "t"}
    }
    uma = migrar_pestanas(gab)
    assert uma["ataques"]["a03"]["pestana"] == "nao"
    assert uma["ataques"]["a02"] == _pestana_vazia()
    assert migrar_pestanas(uma) == uma


def test_migrar_pestanas_recusa_formato_1() -> None:
    """Sem as notas do mvp, só o formato 2 e o 3 passam por aqui."""
    with pytest.raises(ValueError):
        migrar_pestanas({"formato": 1, "notas": []})
    with pytest.raises(ValueError):
        migrar_pestanas({"notas": []})


def test_migrar_arquivo_grava_formato_3_e_e_idempotente(tmp_path: Path) -> None:
    """O arquivo em disco passa a ter ``ataques``; notas iguais; a segunda vez não regrava."""
    ouro = tmp_path / "gabarito.json"
    gab = _gabarito_formato_2(_mvp_com_acordes())
    ouro.write_text(json.dumps(gab, ensure_ascii=False), encoding="utf-8")
    assert migrar_arquivo(ouro) == 2
    gravado = json.loads(ouro.read_text(encoding="utf-8"))
    assert gravado["formato"] == 3
    assert gravado["notas"] == gab["notas"]
    bytes_depois = ouro.read_bytes()
    assert migrar_arquivo(ouro) == 2
    assert ouro.read_bytes() == bytes_depois


@pytest.mark.parametrize(
    ("campos", "esperado"),
    [
        ({"pestana": "nao"}, "nao"),
        ({"pestana": "?"}, "?"),
    ],
)
def test_validar_pestana_nao_e_interrogacao_limpam_os_campos(
    campos: dict, esperado: str
) -> None:
    """``nao`` e ``?`` gravam só a resposta; os campos de dedo, casa e cordas ficam vazios."""
    assert validar_pestana(campos) == {**_pestana_vazia(), "pestana": esperado}


def test_validar_pestana_aceita_sim_com_casa_e_cordas() -> None:
    """Pestana ``sim`` válida passa com os campos como vieram."""
    registro = validar_pestana(
        {
            "pestana": "sim",
            "pestana_dedo": "2",
            "pestana_casa": 3,
            "pestana_de": 1,
            "pestana_ate": 6,
        }
    )
    assert registro == {
        **_pestana_vazia(),
        "pestana": "sim",
        "pestana_dedo": "2",
        "pestana_casa": 3,
        "pestana_de": 1,
        "pestana_ate": 6,
    }


def test_validar_pestana_sim_sem_dedo_usa_o_1() -> None:
    """Sem ``pestana_dedo``, o dedo da pestana é o indicador (``1``)."""
    registro = validar_pestana(
        {"pestana": "sim", "pestana_casa": 2, "pestana_de": 2, "pestana_ate": 3}
    )
    assert registro["pestana_dedo"] == "1"


@pytest.mark.parametrize(
    "campos",
    [
        {"pestana": "talvez"},
        {"pestana": None},
        {"pestana": "sim", "pestana_casa": 0, "pestana_de": 1, "pestana_ate": 3},
        {"pestana": "sim", "pestana_de": 1, "pestana_ate": 3},
        {"pestana": "sim", "pestana_casa": True, "pestana_de": 1, "pestana_ate": 3},
        {"pestana": "sim", "pestana_casa": 2.0, "pestana_de": 1, "pestana_ate": 3},
        {"pestana": "sim", "pestana_casa": 2, "pestana_de": 0, "pestana_ate": 3},
        {"pestana": "sim", "pestana_casa": 2, "pestana_de": 1, "pestana_ate": 7},
        {"pestana": "sim", "pestana_casa": 2, "pestana_de": 3, "pestana_ate": 3},
        {"pestana": "sim", "pestana_casa": 2, "pestana_de": 4, "pestana_ate": 2},
        {
            "pestana": "sim",
            "pestana_dedo": "5",
            "pestana_casa": 2,
            "pestana_de": 1,
            "pestana_ate": 3,
        },
        {
            "pestana": "sim",
            "pestana_dedo": 1,
            "pestana_casa": 2,
            "pestana_de": 1,
            "pestana_ate": 3,
        },
        {
            "pestana": "sim",
            "pestana_casa": 2,
            "pestana_de": 1,
            "pestana_ate": 3,
            "pe": "x",
        },
    ],
)
def test_validar_pestana_recusa_valor_invalido(campos: dict) -> None:
    """Casa < 1, cordas fora de 1 a 6, de >= ate, dedo inexistente e campo estranho: recusa."""
    with pytest.raises(ValueError):
        validar_pestana(campos)


def test_atualizar_pestana_grava_e_recusa_sem_mudar_nada() -> None:
    """Pestana válida entra com ``respondido_em``; ataque inexistente e valor inválido não mudam o gabarito."""
    gab = _gabarito_formato_2(_mvp_com_acordes())
    migrado = migrar_pestanas(gab)
    atualizar_pestana(
        migrado,
        "a02",
        {"pestana": "sim", "pestana_casa": 2, "pestana_de": 1, "pestana_ate": 3},
        "t9",
    )
    registro = migrado["ataques"]["a02"]
    assert (registro["pestana"], registro["respondido_em"]) == ("sim", "t9")
    antes = copy.deepcopy(migrado)
    with pytest.raises(ValueError):
        atualizar_pestana(migrado, "a99", {"pestana": "nao"}, "t")
    with pytest.raises(ValueError):
        atualizar_pestana(
            migrado,
            "a02",
            {"pestana": "sim", "pestana_casa": 0, "pestana_de": 1, "pestana_ate": 3},
            "t",
        )
    assert migrado == antes


def test_ataque_completo_exige_notas_e_pestana() -> None:
    """Notas todas prontas com pestana null: incompleto. Com pestana respondida: completo."""
    gab = gabarito_novo(
        "v.mp4", [{"id": "n02", "indice_mvp": 1}], 9, _mvp_com_acordes()
    )
    for n in gab["notas"]:
        atualizar_resposta(gab, n["id"], {"esquerda": "1", "direita": "p"}, "t")
    assert ataque_completo(gab, "a02") is False
    atualizar_pestana(gab, "a02", {"pestana": "?"}, "t")
    assert ataque_completo(gab, "a02") is True
    assert ataque_completo(gab, "a77") is False


def test_mesclar_preserva_pestana_respondida_e_recusa_orfa() -> None:
    """A pestana respondida vai para o gabarito novo; uma de ataque que sumiu é recusada."""
    existente = _gabarito()
    atualizar_pestana(existente, "a01", {"pestana": "nao"}, "t")
    novo = mesclar_gabarito(_gabarito(), existente)
    assert novo["ataques"]["a01"]["pestana"] == "nao"
    existente["ataques"]["a99"] = {**_pestana_vazia(), "pestana": "nao"}
    with pytest.raises(ValueError):
        mesclar_gabarito(_gabarito(), existente)


def test_servidor_grava_pestana_recusa_invalida_e_preserva_notas(
    tmp_path: Path,
) -> None:
    """POST /pestana grava na cópia; valor inválido vira 400 sem mexer no arquivo."""
    gab = _gabarito()
    atualizar_resposta(gab, "n01", {"esquerda": "3", "direita": "m"}, "t")
    ouro = tmp_path / "gabarito.json"
    ouro.write_text(json.dumps(gab, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "indice.json").write_text("{}", encoding="utf-8")
    servidor = criar_servidor(tmp_path, ouro, porta=0)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{servidor.server_address[1]}"

        def post(caminho: str, corpo: dict) -> tuple[int, dict]:
            req = urllib.request.Request(
                base + caminho,
                data=json.dumps(corpo).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as erro:
                return erro.code, json.loads(erro.read())

        status, dados = post(
            "/pestana",
            {
                "ataque": "a01",
                "pestana": "sim",
                "pestana_casa": 2,
                "pestana_de": 1,
                "pestana_ate": 4,
            },
        )
        assert status == 200
        assert dados["pestana"]["pestana_ate"] == 4
        antes_invalidos = ouro.read_bytes()
        notas_gravadas = json.loads(antes_invalidos)["notas"]
        assert (
            post(
                "/pestana",
                {
                    "ataque": "a01",
                    "pestana": "sim",
                    "pestana_casa": 0,
                    "pestana_de": 1,
                    "pestana_ate": 4,
                },
            )[0]
            == 400
        )
        assert (
            post(
                "/pestana",
                {
                    "ataque": "a01",
                    "pestana": "sim",
                    "pestana_casa": 2,
                    "pestana_de": 4,
                    "pestana_ate": 4,
                },
            )[0]
            == 400
        )
        assert post("/pestana", {"ataque": "a99", "pestana": "nao"})[0] == 400
        assert post("/pestana", {"pestana": "nao"})[0] == 400
        assert post("/pestana", {"ataque": "a01", "pestana": "nao", "x": 1})[0] == 400
        assert ouro.read_bytes() == antes_invalidos

        status, dados = post("/responder", {"id": "n01", "esquerda": "1"})
        assert status == 200
        gravado = json.loads(ouro.read_text(encoding="utf-8"))
        assert gravado["ataques"]["a01"]["pestana"] == "sim"
        assert gravado["notas"][0]["esquerda"] == "1"
        assert gravado["notas"][1:] == notas_gravadas[1:]
        assert dados["total_ataques"] == 4
    finally:
        servidor.shutdown()
        servidor.server_close()


def test_servir_recusa_gabarito_que_nao_esta_no_formato_3(tmp_path: Path) -> None:
    """Um gabarito no formato 2 não sobe o servidor: manda migrar antes."""
    ouro = tmp_path / "gabarito.json"
    ouro.write_text(
        json.dumps(_gabarito_formato_2(_mvp_com_acordes()), ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "indice.json").write_text("{}", encoding="utf-8")
    assert servir(tmp_path, ouro, 0, "127.0.0.1") == 2
