"""Testes da folha de cliques (``tab.audio_folha``). Sem acervo: vídeo sintético do ffmpeg."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tab import audio_folha as af

requer_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="sem ffmpeg/ffprobe nesta imagem",
)


def _video_sintetico(pasta: Path) -> Path:
    """Vídeo de 12 s com mira colorida em movimento e um tom de 440 Hz no áudio.

    Args:
        pasta: pasta onde o vídeo é gravado.

    Returns:
        Caminho do MP4 gerado.
    """
    destino = pasta / "sintetico.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=25:duration=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=12",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(destino),
        ],
        check=True,
        capture_output=True,
    )
    return destino


def _produto(arquivo: str) -> dict:
    """Produto ``tab.video`` mínimo: duas telas, quatro colunas por exibição.

    Args:
        arquivo: caminho relativo ao acervo.

    Returns:
        Dicionário no formato de ``carregar_produtos``.
    """
    telas = [
        {"id": 1, "painel": [20, 100, 620, 200], "passo": 21.6},
        {"id": 2, "painel": [20, 120, 620, 220], "passo": 22.0},
    ]
    notas = []
    for tela in (1, 2):
        for exib in (0, 1):
            for coluna in range(1, 5):
                notas.append(
                    {
                        "tela": tela,
                        "coluna": coluna,
                        "exibicao": exib,
                        "corda": 1 + coluna % 4,
                        "casa": coluna,
                        "x_centro_quadro": 100.0 + 40.0 * coluna + 5.0 * exib,
                    }
                )
    return {"video": {"arquivo": arquivo}, "telas": telas, "notas": notas}


def _itens(video: str) -> list[dict]:
    """Itens de alinhamento: duas exibições, duas telas, quatro colunas; um sem tempo.

    Args:
        video: caminho do vídeo no container (``/acervo/...``).

    Returns:
        Lista de itens no formato de ``ler_alinhados``.
    """
    itens = []
    for exib in (0, 1):
        for tela in (1, 2):
            for coluna in range(1, 5):
                itens.append(
                    {
                        "video": video,
                        "tela": tela,
                        "exibicao": exib,
                        "coluna": coluna,
                        "t_audio": 10.0 + tela + coluna + 3.0 * exib,
                        "confianca": 0.9,
                    }
                )
    itens.append(
        {
            "video": video,
            "tela": 1,
            "exibicao": 0,
            "coluna": 4,
            "t_audio": None,
            "confianca": 0.0,
        }
    )
    return itens


@requer_ffmpeg
def test_clipe_tem_quatro_segundos_e_clique_no_instante(tmp_path: Path) -> None:
    """O clipe dura 4 s (±1 quadro) e o clique cai em ``t_audio`` a até 2 ms."""
    video = _video_sintetico(tmp_path)
    pasta = tmp_path / "saida"
    pasta.mkdir()
    pedido = {
        "id": "t1",
        "video": str(video),
        "t_audio": 6.0,
        "tela": 1,
        "coluna": 1,
        "exibicao": 0,
        "x_centro_quadro": 320.0,
        "painel": [20, 100, 620, 200],
        "passo": 21.6,
        "rotulo": "sintetico",
        "notas": [[1, 0]],
    }
    entrada = af.gerar_clipe(
        pedido, pasta, raiz=tmp_path / "cache", raiz_acervo=str(tmp_path)
    )
    assert abs(entrada["duracao_s"] - 4.0) <= 1 / 25
    assert (pasta / "t1.mp4").is_file()
    assert abs(entrada["erro_clique_ms"]) <= 2.0, entrada
    assert abs(entrada["erro_quadro_ms"]) <= 1000 / 25, entrada


def test_pedido_aceita_nota_sem_exibicao() -> None:
    """Produtos reais trazem ``exibicao: null`` nas notas; o pedido ainda sai certo."""
    produto = _produto("x/y.mp4")
    for nota in produto["notas"]:
        nota["exibicao"] = None
    item = _itens("/acervo/x/y.mp4")[0]
    pedido = af._pedido_do_item(item, produto, 1)
    assert pedido["x_centro_quadro"] == 100.0 + 40.0 * item["coluna"] + 2.5


def test_sorteio_e_deterministico_e_estratificado(tmp_path: Path) -> None:
    """Mesma semente, mesmos pedidos; por vídeo, as exibições saem em partes iguais."""
    produtos = {"/acervo/x/y.mp4": _produto("x/y.mp4")}
    itens = _itens("/acervo/x/y.mp4")

    primeiro = af.sortear_pedidos(itens, produtos, por_video=4, semente=7)
    segundo = af.sortear_pedidos(itens, produtos, por_video=4, semente=7)
    assert primeiro == segundo
    assert len(primeiro) == 4

    exibicoes = [p["exibicao"] for p in primeiro]
    assert exibicoes.count(0) == 2 and exibicoes.count(1) == 2

    colunas_com_tempo = {(i["tela"], i["coluna"], i["exibicao"]) for i in itens}
    assert all(
        (p["tela"], p["coluna"], p["exibicao"]) in colunas_com_tempo for p in primeiro
    )
    sem_tempo = (1, 4, 0)
    assert all((p["tela"], p["coluna"], p["exibicao"]) != sem_tempo for p in primeiro)

    tela1 = next(p for p in primeiro if p["tela"] == 1)
    assert tela1["painel"] == [20, 100, 620, 200]
    assert tela1["passo"] == 21.6
    assert tela1["notas"]


def test_pagina_tem_video_e_tres_respostas_por_clipe(tmp_path: Path) -> None:
    """O HTML tem um ``<video>`` e os três botões por clipe, sem recurso externo."""
    pasta = tmp_path / "folha"
    pasta.mkdir()
    manifesto = [
        {
            "id": f"p{i}",
            "arquivo": f"p{i}.mp4",
            "rotulo": "vídeo <teste>",
            "tela": 1,
            "coluna": i,
            "notas": [[2, 0], [5, 3]],
        }
        for i in range(1, 4)
    ]
    (pasta / "manifesto.json").write_text(json.dumps(manifesto), encoding="utf-8")

    destino = af.gerar_pagina(pasta)
    texto = destino.read_text(encoding="utf-8")

    assert texto.count('<section class="clipe"') == 3
    assert texto.count("<video ") == 3
    for resposta in ("certo", "errado", "nao_sei"):
        assert texto.count(f'<button type="button" data-resposta="{resposta}">') == 3
    assert "vídeo &lt;teste&gt;" in texto
    assert "http://" not in texto and "https://" not in texto
    assert 'src="p1.mp4"' in texto
    assert "corda 2 casa 0 + corda 5 casa 3" in texto


def test_itens_afirmados_exclui_sem_tempo_e_exibicao_recusada() -> None:
    """Só entram colunas com ``t_audio`` em exibições não recusadas."""
    alinhamento = {
        "video": {"arquivo": "/acervo/x/y.mp4"},
        "exibicoes": [
            {"tela": 1, "exibicao": 0, "recusada_exibicao": False, "T_usado_s": 0.6},
            {"tela": 2, "exibicao": 0, "recusada_exibicao": True, "T_usado_s": 0.4},
        ],
        "colunas": [
            {
                "tela": 1,
                "exibicao": 0,
                "coluna": 1,
                "t_audio": 3.0,
                "confianca": 0.9,
                "motivo": None,
                "cos": 0.8,
            },
            {
                "tela": 1,
                "exibicao": 0,
                "coluna": 2,
                "t_audio": None,
                "confianca": None,
                "motivo": "fora_do_trecho",
                "cos": None,
            },
            {
                "tela": 2,
                "exibicao": 0,
                "coluna": 1,
                "t_audio": 4.0,
                "confianca": 0.9,
                "motivo": None,
                "cos": 0.8,
            },
        ],
    }
    itens = af.itens_afirmados(alinhamento)
    assert [(i["tela"], i["coluna"]) for i in itens] == [(1, 1)]
    assert itens[0]["T_usado_s"] == 0.6
    assert itens[0]["video"] == "/acervo/x/y.mp4"


def test_pedido_usa_notas_de_outra_exibicao_quando_falta_na_propria() -> None:
    """Coluna afirmada na exibição 0 sem nota nela usa as notas da coluna (MVP, tela 9 col 9)."""
    produto = _produto("x/y.mp4")
    for nota in produto["notas"]:
        nota["exibicao"] = 1
    item = {
        "video": "/acervo/x/y.mp4",
        "tela": 1,
        "exibicao": 0,
        "coluna": 2,
        "t_audio": 3.0,
    }
    pedido = af._pedido_do_item(item, produto, 1)
    assert pedido["notas"]
    assert {tuple(n) for n in pedido["notas"]} == {(3, 2)}
