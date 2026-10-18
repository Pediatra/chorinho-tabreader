"""Localizador do braço (``tab.maos_braco_localizador``): alvos, enquadre e decodificação.

Sem GPU e sem acervo: as imagens e os mapas são sintéticos, e a rede tem pesos aleatórios
só para conferir formas.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch

from tab import maos_braco_localizador as loc
from tab.maos_braco_detector import UNetBraco
from tab.maos_braco_faixa import eixo_da_faixa
from tab.maos_braco_tempo import Marcas, marcas_do_registro


def _marcas_sinteticas() -> Marcas:
    """Braço horizontal com nut em x=100; cordas 1 e 6 com pontas perto e longe.

    Returns:
        Marcas com nut, corda1 (y=40 longe, y=52 perto) e corda6 (y=60 perto, y=58 longe).
    """
    return Marcas(
        nut=np.array([100.0, 50.0]),
        trastes={},
        corda1=np.array([[600.0, 40.0], [100.0, 52.0]]),
        corda6=np.array([[600.0, 60.0], [100.0, 58.0]]),
    )


def test_alvos_pontos_perto_e_longe_do_nut() -> None:
    """Ordem dos 4 pontos: corda 1 perto, corda 1 longe, corda 6 perto, corda 6 longe."""
    pontos = loc.pontos_do_rotulo(_marcas_sinteticas())
    assert pontos.shape == (4, 2)
    assert pontos[0].tolist() == [100.0, 52.0]
    assert pontos[1].tolist() == [600.0, 40.0]
    assert pontos[2].tolist() == [100.0, 58.0]
    assert pontos[3].tolist() == [600.0, 60.0]


def test_alvos_sem_nut_levantam_erro() -> None:
    """Sem nut não há alvo: a função recusa em vez de inventar o ponto."""
    marcas = _marcas_sinteticas()
    sem_nut = Marcas(nut=None, trastes={}, corda1=marcas.corda1, corda6=marcas.corda6)
    with pytest.raises(ValueError):
        loc.pontos_do_rotulo(sem_nut)


def test_alvo_gaussiano_no_ponto_e_mascara_entre_cordas() -> None:
    """Cada canal de ponto tem pico no ponto; a máscara cobre o meio entre as cordas."""
    pontos = loc.pontos_do_rotulo(_marcas_sinteticas())
    alvo = loc.desenhar_alvo(pontos)
    assert alvo.shape == (5, loc.ALTURA_CANVAS, loc.LARGURA_ENTRADA)
    for canal in range(4):
        y, x = np.unravel_index(int(np.argmax(alvo[canal])), alvo[canal].shape)
        assert abs(x - pontos[canal, 0]) <= 1
        assert abs(y - pontos[canal, 1]) <= 1
        assert alvo[canal].max() == pytest.approx(1.0, abs=1e-6)
    mascara = alvo[loc.CANAL_PRESENCA]
    assert mascara[52, 300] == 1  # meio do braço: entre as cordas em x=300
    assert mascara[10, 300] == 0  # acima das cordas
    assert mascara[100, 300] == 0  # abaixo das cordas


def test_enquadre_ida_e_volta_e_canvas_multiplo_de_32() -> None:
    """Letterbox e a inversa devolvem o mesmo ponto; o canvas é 384 x 640."""
    assert loc.ALTURA_CANVAS % 32 == 0
    assert loc.LARGURA_ENTRADA % 32 == 0
    for altura, largura in ((1080, 2220), (1080, 1920), (360, 640), (720, 1280)):
        imagem = np.full((altura, largura, 3), 200, dtype=np.uint8)
        canvas, enquadre = loc.enquadrar(imagem)
        assert canvas.shape == (loc.ALTURA_CANVAS, loc.LARGURA_ENTRADA, 3)
        pontos = np.array(
            [[0.0, 0.0], [largura - 1.0, altura - 1.0], [largura / 3, 7.0]]
        )
        ida = loc.para_canvas(pontos, enquadre)
        assert np.allclose(loc.do_canvas(ida, enquadre), pontos, atol=1e-9)


def test_enquadre_deixa_borda_preta_no_formato_largo() -> None:
    """Quadro 2220 x 1080 entra em 640 x 311 centrado, com faixas pretas em cima e embaixo."""
    imagem = np.full((1080, 2220, 3), 255, dtype=np.uint8)
    canvas, _ = loc.enquadrar(imagem)
    assert canvas[0].max() == 0
    assert canvas[loc.ALTURA_CANVAS - 1].max() == 0
    assert canvas[loc.ALTURA_CONTEUDO // 2].max() == 255


def test_decodificar_pontos_sinteticos() -> None:
    """Picos conhecidos no canvas voltam ao quadro original com erro menor que 0,3 px."""
    enquadre = loc.Enquadre(sx=0.5, sy=0.5, ox=10.0, oy=20.0)
    originais = np.array([[100.0, 60.0], [400.0, 50.0], [100.0, 90.0], [400.0, 100.0]])
    no_canvas = loc.para_canvas(originais, enquadre)
    mapas = np.zeros((5, loc.ALTURA_CANVAS, loc.LARGURA_ENTRADA), dtype=np.float32)
    ys, xs = np.mgrid[0 : loc.ALTURA_CANVAS, 0 : loc.LARGURA_ENTRADA]
    for canal, (px, py) in enumerate(no_canvas):
        mapas[canal] = 0.9 * np.exp(-((xs - px) ** 2 + (ys - py) ** 2) / 8.0)
    mapas[loc.CANAL_PRESENCA, 100:200, 200:300] = 0.95
    dec = loc.decodificar_quadro(mapas, enquadre)
    assert dec["achou"] is True
    assert np.max(np.abs(dec["pontos"] - originais)) < 0.3
    assert dec["marcas"].nut.tolist() == pytest.approx(
        ((originais[0] + originais[2]) / 2).tolist(), abs=0.3
    )


def test_sem_braco_quando_presenca_abaixo_do_limiar() -> None:
    """Presença máxima de 0,2 é "sem braço" (P_MIN = 0,3)."""
    mapas = np.zeros((5, loc.ALTURA_CANVAS, loc.LARGURA_ENTRADA), dtype=np.float32)
    mapas[loc.CANAL_PRESENCA, 10:20, 10:20] = 0.2
    dec = loc.decodificar_quadro(mapas, loc.Enquadre(1.0, 1.0, 0.0, 0.0))
    assert dec["achou"] is False
    assert "0,3" in dec["motivo"]


def test_sem_braco_quando_um_ponto_fica_abaixo_do_limiar() -> None:
    """Presença alta mas um ponto com máximo 0,25 também é "sem braço"."""
    mapas = np.zeros((5, loc.ALTURA_CANVAS, loc.LARGURA_ENTRADA), dtype=np.float32)
    mapas[loc.CANAL_PRESENCA, 10:20, 10:20] = 0.9
    mapas[0, 50, 50] = 0.9
    mapas[1, 60, 60] = 0.9
    mapas[2, 70, 70] = 0.9
    mapas[3, 80, 80] = 0.25
    dec = loc.decodificar_quadro(mapas, loc.Enquadre(1.0, 1.0, 0.0, 0.0))
    assert dec["achou"] is False


def test_divisao_sem_vazamento_de_canal() -> None:
    """Canais de validação ficam fora do treino, e o treino não tem nenhum deles."""
    canais = ["cifra club", "kenneth acoustic", "shin izumi", "sky guitar"]
    registros = [
        {
            "id": f"{canal}-{i}",
            "canal": canal,
            "origem": "R",
            "caminho": "",
            "marcas": None,
        }
        for canal in canais
        for i in range(3)
    ]
    treino, validacao = loc.dividir_por_canal(registros)
    assert {r["canal"] for r in validacao} == set(loc.CANAIS_VALIDACAO)
    assert not {r["canal"] for r in treino} & set(loc.CANAIS_VALIDACAO)
    assert len(treino) + len(validacao) == len(registros)


def test_aumento_leva_os_pontos_junto_com_a_imagem() -> None:
    """Um pixel marcado e o seu ponto transformado caem no mesmo lugar após o aumento."""
    rng = random.Random(7)
    for _ in range(5):
        matriz = loc.matriz_aumento(rng)
        ponto = np.array([[200.0, 150.0]])
        marca = np.zeros((loc.ALTURA_CANVAS, loc.LARGURA_ENTRADA), dtype=np.uint8)
        marca[150, 200] = 255
        aumentada = cv2.warpAffine(
            marca,
            matriz,
            (loc.LARGURA_ENTRADA, loc.ALTURA_CANVAS),
            flags=cv2.INTER_NEAREST,
        )
        y, x = np.unravel_index(int(np.argmax(aumentada)), aumentada.shape)
        esperado = loc.transformar_pontos(ponto, matriz)[0]
        assert abs(x - esperado[0]) <= 1.0
        assert abs(y - esperado[1]) <= 1.0


def test_erro_do_eixo_zero_quando_o_eixo_e_o_mesmo() -> None:
    """Eixo previsto igual ao rótulo: todos os erros são zero."""
    eixo = eixo_da_faixa(_marcas_sinteticas())
    erro = loc.erro_do_eixo(eixo, eixo)
    assert erro["perpendicular"] == pytest.approx(0.0, abs=1e-9)
    assert erro["ao_longo"] == pytest.approx(0.0, abs=1e-9)
    assert erro["rotacao_graus"] == pytest.approx(0.0, abs=1e-9)
    assert erro["escala"] == pytest.approx(0.0, abs=1e-9)
    assert loc.dentro_do_envelope(erro) is True


def test_erro_do_eixo_de_rotacao_pura_nao_conta_como_deslocamento() -> None:
    """Uma rotação de 2 graus em torno do centro dá 2 graus e nenhum deslocamento."""
    origem, u, comprimento, largura = eixo_da_faixa(_marcas_sinteticas())
    angulo = math.radians(2.0)
    rot = np.array(
        [[math.cos(angulo), -math.sin(angulo)], [math.sin(angulo), math.cos(angulo)]]
    )
    centro = origem + u * (comprimento / 2.0)
    origem_p = centro + rot @ (origem - centro)
    previsto = (origem_p, rot @ u, comprimento, largura)
    erro = loc.erro_do_eixo(previsto, (origem, u, comprimento, largura))
    assert erro["rotacao_graus"] == pytest.approx(2.0, abs=1e-6)
    assert erro["perpendicular"] == pytest.approx(0.0, abs=1e-6)
    assert erro["ao_longo"] == pytest.approx(0.0, abs=1e-6)
    assert loc.dentro_do_envelope(erro) is True


def test_envelope_reprova_erro_de_rotacao_grande() -> None:
    """Rotação de 5 graus sai do envelope (3 graus)."""
    erro = {"perpendicular": 0.0, "ao_longo": 0.0, "rotacao_graus": 5.0, "escala": 0.0}
    assert loc.dentro_do_envelope(erro) is False
    assert loc.dentro_do_envelope(None) is False


def test_rede_com_cinco_saidas_na_forma_certa() -> None:
    """A U-Net com 5 canais devolve (N, 5, H, W); o padrão continua com 4."""
    rede = UNetBraco(pesos_imagenet=False, canais=5)
    rede.eval()
    with torch.no_grad():
        saida = rede(torch.zeros(1, 3, 128, 160))
    assert tuple(saida.shape) == (1, 5, 128, 160)
    assert UNetBraco(pesos_imagenet=False).cabeca.out_channels == 4


def _registro_c(**campos: object) -> dict:
    """Registro da fonte C válido (braço nulo, nut e duas cordas de 2 pontos, sem trastes).

    Args:
        **campos: campos a sobrescrever.

    Returns:
        Registro no formato de ``braco_m25_treino.json``.
    """
    base: dict = {
        "braco": None,
        "corda1": [[600.0, 40.0], [100.0, 52.0]],
        "corda6": [[600.0, 60.0], [100.0, 58.0]],
        "nut": [100.0, 50.0],
        "trastes": None,
        "obs": None,
    }
    base.update(campos)
    return base


def _registro_completo_sim(**campos: object) -> dict:
    """Registro do gabarito com braço "sim" completo (nut, cordas e dois trastes).

    Args:
        **campos: campos a sobrescrever.

    Returns:
        Registro que ``marcas_do_registro`` aceita.
    """
    base = _registro_c(braco="sim", trastes=[[300.0, 46.0], [450.0, 44.0]])
    base.update(campos)
    return base


def _escreve_fonte(pasta: Path, quadros: dict[str, dict]) -> tuple[Path, Path]:
    """Grava um gabarito e um ``indice.json`` falsos em ``pasta``.

    Args:
        pasta: diretório temporário.
        quadros: id -> registro do gabarito.

    Returns:
        ``(caminho_do_gabarito, pasta_com_indice)``.
    """
    gold = pasta / "gold.json"
    gold.write_text(json.dumps({"formato": 1, "quadros": quadros}), encoding="utf-8")
    pasta_quadros = pasta / "fonte"
    pasta_quadros.mkdir()
    indice = {
        "semente": 1,
        "quadros": [
            {"id": qid, "canal": "canal x", "png": f"quadros/{qid}.png"}
            for qid in quadros
        ],
    }
    (pasta_quadros / "indice.json").write_text(json.dumps(indice), encoding="utf-8")
    return gold, pasta_quadros


def test_fonte_c_monta_marcas_sem_trastes() -> None:
    """O registro do C vira ``Marcas`` com nut, duas cordas e trastes vazios."""
    marcas = loc.marcas_da_fonte_c(_registro_c())
    assert marcas is not None
    assert marcas.nut.tolist() == [100.0, 50.0]
    assert marcas.trastes == {}
    assert marcas.corda1.shape == (2, 2)
    assert marcas.corda6.shape == (2, 2)


def test_fonte_c_recusa_corda_com_um_ponto_ou_sem_nut() -> None:
    """Corda com 1 ponto, ou nut ausente, deixa o quadro de fora da fonte C."""
    assert loc.marcas_da_fonte_c(_registro_c(corda1=[[600.0, 40.0]])) is None
    assert loc.marcas_da_fonte_c(_registro_c(nut=None)) is None


def test_marcas_do_registro_nao_serve_para_o_c() -> None:
    """Por isso o C monta as marcas direto: com braço nulo, ``marcas_do_registro`` dá None."""
    assert marcas_do_registro(_registro_c()) is None


def test_ler_fonte_c_so_conta_quadros_completos(tmp_path: Path) -> None:
    """Só entra o quadro com nut e as duas cordas de 2 pontos; id, canal e caminho certos."""
    gold, pasta = _escreve_fonte(
        tmp_path,
        {
            "q01": _registro_c(),
            "q02": _registro_c(corda1=[[600.0, 40.0]]),
            "q03": _registro_c(nut=None),
        },
    )
    registros = loc.ler_fonte_c(gold=gold, pasta=pasta)
    assert [r["id"] for r in registros] == ["C-q01"]
    assert registros[0]["origem"] == "C"
    assert registros[0]["canal"] == "canal x"
    assert registros[0]["caminho"] == str(pasta / "quadros" / "q01.png")
    assert registros[0]["marcas"].trastes == {}


def test_regra_de_inclusao_da_prova() -> None:
    """q08 sai; sem resposta sai; "nao" entra negativo; braço nulo com marcas vira "sim"."""
    gold = {
        "q08": _registro_completo_sim(),
        "q01": _registro_c(corda1=None, corda6=None, nut=None, braco=None),
        "q02": {"braco": "nao", "corda1": None, "corda6": None, "obs": None},
        "q03": _registro_c(trastes=[[300.0, 46.0], [450.0, 44.0]], obs="2 braços"),
        "q04": _registro_c(trastes=[]),
        "q05": _registro_completo_sim(),
        "q06": _registro_completo_sim(braco="?"),
    }
    indice = {
        qid: {"id": qid, "canal": "canal y", "png": f"quadros/{qid}.png"}
        for qid in gold
    }
    incluidos, excluidos = loc.selecionar_prova(gold, indice, Path("/x"))
    assert [q["id"] for q in incluidos] == ["q02", "q03", "q05"]
    assert {e["id"]: e["motivo"] for e in excluidos}["q08"].startswith("q08")
    assert {e["id"] for e in excluidos} == {"q08", "q01", "q04", "q06"}
    por_id = {q["id"]: q for q in incluidos}
    assert por_id["q02"]["braco"] == "nao"
    assert por_id["q02"]["marcas"] is None
    assert por_id["q03"]["braco"] == "sim"
    assert por_id["q03"]["dois_bracos"] is True
    assert por_id["q05"]["dois_bracos"] is False
    assert por_id["q03"]["caminho"] == str(Path("/x") / "quadros" / "q03.png")


def test_carregar_prova_le_os_arquivos_da_pasta(tmp_path: Path) -> None:
    """Com gabarito e índice falsos, ``carregar_prova`` aplica a mesma regra."""
    gold, pasta = _escreve_fonte(
        tmp_path,
        {
            "q02": {"braco": "nao", "corda1": None, "corda6": None, "obs": None},
            "q03": _registro_completo_sim(obs="2 braços"),
        },
    )
    incluidos, excluidos = loc.carregar_prova(gold=gold, pasta=pasta)
    assert [q["id"] for q in incluidos] == ["q02", "q03"]
    assert excluidos == []
    assert incluidos[1]["dois_bracos"] is True


_IDENTIDADE = loc.Enquadre(sx=1.0, sy=1.0, ox=0.0, oy=0.0)


def _mapas_com_picos(picos: dict[int, list[tuple[float, float, float]]]) -> np.ndarray:
    """Mapas ``(5, 384, 640)`` com gaussianas (sigma 2) nos picos ``(x, y, valor)``.

    Args:
        picos: canal -> lista de picos. A presença (canal 4) fica alta num bloco fixo.

    Returns:
        Array float32 com os 5 canais.
    """
    ys, xs = np.mgrid[0 : loc.ALTURA_CANVAS, 0 : loc.LARGURA_ENTRADA].astype(np.float32)
    mapas = np.zeros((5, loc.ALTURA_CANVAS, loc.LARGURA_ENTRADA), dtype=np.float32)
    for canal, lista in picos.items():
        for x, y, valor in lista:
            gauss = valor * np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / 8.0)
            mapas[canal] = np.maximum(mapas[canal], gauss.astype(np.float32))
    mapas[loc.CANAL_PRESENCA, 100:200, 200:300] = 0.95
    return mapas


def test_conjunta_escolhe_a_combinacao_certa_com_dois_picos_por_canal() -> None:
    """Cada canal tem um pico em cada ponta. A antiga (argmax) erra; a conjunta acerta.

    Os canais 1 e 3 têm o pico mais alto no ponto errado (a ponta perto), reproduzindo
    o caso da semente 2: o argmax põe mais de um ponto na mesma ponta.
    """
    picos = {
        0: [(100.0, 52.0, 0.9), (600.0, 40.0, 0.8)],
        1: [(100.0, 52.0, 0.9), (600.0, 40.0, 0.85)],
        2: [(100.0, 58.0, 0.9), (600.0, 60.0, 0.8)],
        3: [(100.0, 58.0, 0.9), (600.0, 60.0, 0.85)],
    }
    mapas = _mapas_com_picos(picos)
    esperado = np.array([[100.0, 52.0], [600.0, 40.0], [100.0, 58.0], [600.0, 60.0]])
    conjunta = loc.decodificar_quadro_conjunto(mapas, _IDENTIDADE)
    assert conjunta["achou"] is True
    assert np.max(np.abs(conjunta["pontos"] - esperado)) < 0.3
    antiga = loc.decodificar_quadro(mapas, _IDENTIDADE)
    assert np.max(np.abs(antiga["pontos"] - esperado)) > 100.0


def test_combinacao_impossivel_dá_sem_braco() -> None:
    """Com um só candidato por canal, o único par de pontas é degenerado: sem braço."""
    picos = {
        0: [(100.0, 52.0, 0.9)],
        1: [(100.0, 52.0, 0.9)],
        2: [(100.0, 58.0, 0.9)],
        3: [(100.0, 58.0, 0.9)],
    }
    dec = loc.decodificar_quadro_conjunto(_mapas_com_picos(picos), _IDENTIDADE)
    assert dec["achou"] is False
    assert "combinação" in dec["motivo"]


def test_cruzamento_e_rejeitado() -> None:
    """Cordas que se cruzam não passam na regra d, mesmo com as outras três regras."""
    cruzadas = np.array([[100.0, 52.0], [600.0, 58.0], [100.0, 58.0], [600.0, 52.0]])
    paralelas = np.array([[100.0, 52.0], [600.0, 40.0], [100.0, 58.0], [600.0, 60.0]])
    assert loc.combinacao_valida(paralelas) is True
    assert loc.combinacao_valida(cruzadas) is False
    picos = {
        0: [(100.0, 52.0, 0.9)],
        1: [(600.0, 58.0, 0.9)],
        2: [(100.0, 58.0, 0.9)],
        3: [(600.0, 52.0, 0.9)],
    }
    dec = loc.decodificar_quadro_conjunto(_mapas_com_picos(picos), _IDENTIDADE)
    assert dec["achou"] is False


def test_candidatos_respeitam_limiar_e_o_maximo_de_cinco() -> None:
    """Sete picos acima de 0,3 viram 5 candidatos, do maior para o menor."""
    picos = [(40.0 + 60.0 * k, 50.0, 0.4 + 0.05 * k) for k in range(7)]
    mapa = _mapas_com_picos({0: picos})[0]
    candidatos = loc._candidatos(mapa)
    assert len(candidatos) == 5
    valores = [v for _, _, v in candidatos]
    assert valores == sorted(valores, reverse=True)
    assert all(v >= 0.3 for v in valores)
