"""Testes da folha de cliques (``tab.audio_folha``). Sem acervo: vídeo sintético do ffmpeg."""

import json
import random
import shutil
import subprocess
from pathlib import Path

import numpy as np
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


def _audio_com_rajadas(instantes: list[float], dur: float = 8.0) -> tuple:
    """Áudio int16 mono de 22 050 Hz com rajadas de ruído de 40 ms nos instantes dados.

    Args:
        instantes: início de cada rajada, em segundos.
        dur: duração total, em segundos.

    Returns:
        ``(amostras, taxa, t_amostra0)`` no formato de ``carregar_audio``.
    """
    taxa = 22050
    rng = np.random.default_rng(0)
    x = np.zeros(round(dur * taxa))
    for t in instantes:
        i = round(t * taxa)
        x[i : i + round(0.04 * taxa)] = 0.5 * rng.standard_normal(round(0.04 * taxa))
    return (x * 32767).astype(np.int16), taxa, 0.0


def _coluna(coluna: int, t: float) -> dict:
    """Registro de coluna no formato do alinhador (só o necessário ao controle)."""
    return {"tela": 1, "exibicao": 0, "coluna": coluna, "t_audio": t}


def test_pares_vizinhos_exigem_consecutivas_afirmadas_e_intervalo() -> None:
    """Par (c, c+1) só vale com as duas afirmadas, numeração seguida e dt >= 0,40 s."""
    colunas = [
        _coluna(1, 1.0),
        _coluna(2, 1.5),  # ok: dt 0,5
        _coluna(3, None),  # recusada: bloqueia (2,3) e (3,4)
        _coluna(4, 3.0),
        _coluna(5, 3.2),  # dt 0,2: fora
        _coluna(7, 5.0),  # não consecutiva com 5
    ]
    pares = af.pares_vizinhos_validos(colunas)
    assert [(a["coluna"], b["coluna"]) for a, b in pares] == [(1, 2)]


def test_controle_rejeita_clique_sobre_pico_e_aceita_limpo() -> None:
    """Clique no ponto médio de uma rajada é rejeitado; num trecho limpo é aceito."""
    audio = _audio_com_rajadas([2.0, 4.0, 5.3])
    sobre_pico = (_coluna(1, 5.0), _coluna(2, 5.6))  # médio 5,3 = rajada
    limpo = (_coluna(1, 2.0), _coluna(2, 4.0))  # médio 3,0, sem rajada
    assert af.escolher_controle([sobre_pico], audio, random.Random(0), set()) is None
    escolha = af.escolher_controle([limpo], audio, random.Random(0), set())
    assert escolha is not None
    assert abs(escolha["clique"] - 3.0) < 1e-9
    assert escolha["distancia_pico_s"] >= af.DISTANCIA_MIN_PICO_S


def test_sorteio_espalhado_uma_coluna_por_faixa_de_tempo() -> None:
    """Com K faixas e itens em todas, sai um item por faixa, sem repetição."""
    itens = [
        {"tela": 1, "exibicao": 0, "coluna": c, "t_audio": 1.0 + c * 1.0}
        for c in range(1, 21)
    ]
    escolhidos = af.sortear_espalhado(itens, 4, random.Random(7))
    assert len(escolhidos) == 4
    assert len({it["coluna"] for it in escolhidos}) == 4
    faixas = [min(3, int((it["t_audio"] - 2.0) // 5.0)) for it in escolhidos]
    assert sorted(faixas) == [0, 1, 2, 3]


def _elegivel(i: int, video: str = "/acervo/x/y.mp4") -> dict:
    """Elegível sintético da comparação A/B (campos de ``elegiveis_comparacao``)."""
    return {
        "item_gold": f"f{i:02d}",
        "video": video,
        "tela": 1 + i % 5,
        "exibicao": 0,
        "coluna": i,
        "t_alinhador": 10.0 + i,
        "painel": [20, 100, 620, 200],
        "passo": 21.6,
        "x_centro_quadro": 300.0,
        "rotulo": "sintetico",
    }


def test_planejar_comparacao_contagens_e_determinismo() -> None:
    """36 pares com 6 de cada d, 2 de cada ±400; metade com o alinhador em A; mesma semente."""
    elegiveis = [_elegivel(i, f"/acervo/v{i % 3}.mp4") for i in range(40)]
    pares = af.planejar_comparacao(elegiveis, 2003)
    assert len(pares) == 40
    assert [p["id"] for p in pares] == [f"p{n:02d}" for n in range(1, 41)]
    contagem = {}
    for p in pares:
        contagem[p["d_ms"]] = contagem.get(p["d_ms"], 0) + 1
    assert all(contagem[d] == 6 for d in af.D_MS)
    assert contagem[-400] == 2 and contagem[400] == 2
    assert sum(1 for p in pares if p["alinhador_e"] == "A") == 20
    assert pares == af.planejar_comparacao(elegiveis, 2003)
    assert pares != af.planejar_comparacao(elegiveis, 2004)


def test_planejar_comparacao_distribui_videos_pelos_deslocamentos() -> None:
    """Cada vídeo com 6 ou mais pares principais aparece em todos os seis deslocamentos."""
    elegiveis = [_elegivel(i, f"/acervo/v{i // 12}.mp4") for i in range(36)]
    pares = af.planejar_comparacao(elegiveis, 2003)
    for video in {e["video"] for e in elegiveis}:
        ds = {p["d_ms"] for p in pares if p["video"] == video and not p["atencao"]}
        assert ds == set(af.D_MS)


def test_elegiveis_so_certo_e_sem_controle_e_sem_f13() -> None:
    """Entram só 'certo', não controle e não o f13; o instante tem de bater com o pedido."""
    golds = [
        {"id": "f01", "resposta_dono": "certo", "controle": False, "t_clique": 5.0},
        {"id": "f02", "resposta_dono": "errado", "controle": False, "t_clique": 6.0},
        {"id": "f03", "resposta_dono": "certo", "controle": True, "t_clique": 7.0},
        {"id": "f13", "resposta_dono": "certo", "controle": False, "t_clique": 8.0},
    ]
    pedido = {
        "video": "/acervo/x/y.mp4",
        "t_audio": 5.0,
        "tela": 1,
        "exibicao": 0,
        "coluna": 2,
        "painel": [1, 2, 3, 4],
        "passo": 20.0,
        "x_centro_quadro": 50.0,
        "rotulo": "x",
    }
    pedidos = {"f01": pedido, "f13": {**pedido, "t_audio": 8.0}}
    elegiveis = af.elegiveis_comparacao(golds, pedidos)
    assert [e["item_gold"] for e in elegiveis] == ["f01"]
    assert elegiveis[0]["t_alinhador"] == 5.0


def test_pagina_comparacao_nao_revela_deslocamento_nem_alinhador(
    tmp_path: Path,
) -> None:
    """A página só tem ids e arquivos: sem d, sem 'alinhador', sem o valor de d."""
    pasta = tmp_path / "folha3"
    pasta.mkdir()
    manifesto = [
        {
            "id": f"p{n:02d}",
            "arquivo_a": f"p{n:02d}_a.mp4",
            "arquivo_b": f"p{n:02d}_b.mp4",
        }
        for n in range(1, 4)
    ]
    texto = af.gerar_pagina_comparacao(pasta, manifesto).read_text(encoding="utf-8")
    assert texto.count('<section class="linha"') == 3
    assert texto.count("<video ") == 6
    for proibido in ("d_ms", "alinhador", "deslocado", "t_alinhador"):
        assert proibido not in texto
    for valor in ("-400", "+400", "-200", "+200", "-100", "+100", "-50", "+50"):
        assert valor not in texto
    assert sorted(p.name for p in pasta.iterdir()) == ["index.html"]


@requer_ffmpeg
def test_par_tem_mesma_janela_e_clique_separado_por_d(tmp_path: Path) -> None:
    """A e B começam no mesmo quadro (mesma janela) e os cliques distam d (±2 ms)."""
    video = _video_sintetico(tmp_path)
    pasta = tmp_path / "saida"
    pasta.mkdir()
    par = {
        **_elegivel(1, str(video)),
        "id": "p01",
        "d_ms": 200,
        "alinhador_e": "A",
        "t_alinhador": 6.0,
        "passo": 21.6,
        "painel": [20, 100, 620, 200],
        "x_centro_quadro": 320.0,
    }
    saida = af.gerar_par_comparacao(
        par, pasta, raiz=tmp_path / "cache", raiz_acervo=str(tmp_path)
    )
    a = pasta / saida["arquivo_a"]
    b = pasta / saida["arquivo_b"]
    assert abs(af._sondar_video(str(a))[2] - af._sondar_video(str(b))[2]) <= 1 / 25

    def primeiro_quadro(arq: Path) -> bytes:
        return subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(arq),
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout

    assert primeiro_quadro(a) == primeiro_quadro(b)

    inicio = saida["inicio_clipe_s"]
    orig = af._audio_mono(str(video), inicio) * af.GANHO_MUSICA

    def clique(arq: Path, esperado: float) -> float:
        amostras = af._audio_mono(str(arq), None)
        lag = af._atraso_amostras(amostras, orig)
        residuo = af._residuo(amostras, orig, lag)
        return af._achar_clique(residuo, esperado)[0]

    t_a = clique(a, saida["clique_a_s"])
    t_b = clique(b, saida["clique_b_s"])
    assert abs((t_b - t_a) - 0.200) <= 0.002, (t_a, t_b)
    assert abs(t_a - saida["clique_a_s"]) <= 0.002
