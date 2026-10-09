"""Levantamento do marcador: agregação, julgamento e amostra, sem abrir vídeo.

Os testes de vídeo (série densa real) exigem o acervo e ficam de fora do gate. Aqui se
trava o que **decide** o resultado: a agregação de vereditos por canal, a matiz mediana, o
rebaixamento para `duvida` quando a medida não sustenta veredito, e a seleção de amostra
(que é o que garante que um canal não seja medido só no bloco alfabético inicial).
"""

from __future__ import annotations

import json
import os

from tab.marcador import (
    N_BINS_MATIZ,
    VEREDITOS,
    agregar_canais,
    agregar_canal,
    amostra_espacada,
    escrever_resumo,
    histograma_matiz,
    julgar,
    listar_videos,
    mediana_do_histograma,
    tabela_texto,
)


def _serie_deslizante(n: int = 30, passo_px: int = 30) -> list[tuple[float, int]]:
    """Marcador andando para o mesmo lado, 30 px a cada 0,5 s."""
    return [(i * 0.5, 100 + i * passo_px) for i in range(n)]


def _linha(veredito: str, matiz: float | None = 102.0, **extra: object) -> dict:
    """Linha de resultado falsa, no formato do JSONL."""
    base: dict = {
        "arquivo": f"canal/{veredito}_{matiz}.mp4",
        "veredito": veredito,
        "veredito_resumo": veredito,
        "n_deteccoes": 10,
        "matiz_mediana": matiz,
        "matiz_hist": histograma_matiz([int(matiz)] * 10 if matiz is not None else []),
    }
    base.update(extra)
    return base


def test_histograma_matiz_conta_faixas_de_cinco_graus() -> None:
    """Cada matiz cai na sua faixa, e a última faixa absorve o topo do intervalo."""
    hist = histograma_matiz([0, 4, 5, 102, 179, 179])
    assert hist[0] == 2  # 0 e 4
    assert hist[1] == 1  # 5
    assert hist[20] == 1  # 102
    assert hist[N_BINS_MATIZ - 1] == 2  # 179
    assert sum(hist) == 6


def test_mediana_do_histograma_vazio_e_unimodal() -> None:
    """Sem detecção não há matiz; com uma faixa só, a mediana é o centro dela."""
    assert mediana_do_histograma([]) is None
    assert mediana_do_histograma([0] * N_BINS_MATIZ) is None
    unimodal = [0] * N_BINS_MATIZ
    unimodal[20] = 7  # matizes 100–104
    assert mediana_do_histograma(unimodal) == 102.5


def test_amostra_espacada_cobre_o_canal_inteiro() -> None:
    """8 de 100 vídeos pegam o primeiro, o último e espaçam o resto."""
    videos = [f"v{i:03d}.mp4" for i in range(100)]
    escolhidos = amostra_espacada(videos, 8)
    assert len(escolhidos) == 8
    assert escolhidos[0] == videos[0]
    assert escolhidos[-1] == videos[-1]
    assert escolhidos == sorted(escolhidos)


def test_amostra_espacada_com_canal_menor_que_o_pedido() -> None:
    """Canal com menos vídeos que o pedido devolve todos, sem repetir."""
    assert amostra_espacada(["a.mp4", "b.mp4", "c.mp4"], 8) == [
        "a.mp4",
        "b.mp4",
        "c.mp4",
    ]


def test_amostra_espacada_inclui_arquivo_pedido() -> None:
    """`--incluir` põe o arquivo na amostra (é como o `henze` entra no `iwaki`)."""
    videos = [f"v{i:03d}.mp4" for i in range(100)]
    escolhidos = amostra_espacada(videos, 8, ["alvo"])
    assert len(escolhidos) == 8
    assert "alvo" not in escolhidos  # não existe na lista: nada a incluir
    videos.append("m-alvo.mp4")
    escolhidos = amostra_espacada(sorted(videos), 8, ["alvo"])
    assert len(escolhidos) == 8
    assert any("alvo" in v for v in escolhidos)


def test_julgar_deslize_valido_nao_vira_duvida() -> None:
    """Série completa, detecção em todos os quadros e passo real: `desliza`."""
    r = julgar(_serie_deslizante(), [6] * 30, [102] * 30, 30, 30)
    assert r["veredito"] == "desliza"
    assert r["motivo_duvida"] is None
    assert r["velocidade_trechos_px_s"] == 60.0
    assert r["matiz_mediana"] == 102.0
    assert r["matiz_p10"] == 102.0


def test_julgar_amostragem_incompleta_vira_duvida() -> None:
    """Cortar a leitura no meio é o caso que produz aliasing — não pode virar veredito."""
    r = julgar(_serie_deslizante(10), [6] * 10, [102] * 10, 10, 241)
    assert r["veredito"] == "duvida"
    assert r["motivo_duvida"] == "amostragem_incompleta"
    assert r["veredito_resumo"] == "desliza"  # o bruto fica gravado, não é apagado


def test_julgar_poucas_deteccoes_vira_duvida() -> None:
    """Quatro detecções não sustentam `desliza`, mesmo com a série bonita."""
    r = julgar(_serie_deslizante(4), [6] * 4, [102] * 4, 4, 4)
    assert r["veredito"] == "duvida"
    assert r["motivo_duvida"] == "poucas_deteccoes"


def test_julgar_serie_esparsa_vira_duvida() -> None:
    """Dez detecções em 241 quadros: a série existe, mas o marcador não aparece sempre."""
    r = julgar(_serie_deslizante(10), [6] * 10, [102] * 10, 241, 241)
    assert r["veredito"] == "duvida"
    assert r["motivo_duvida"] == "serie_esparsa"


def test_julgar_banda_larga_vira_duvida() -> None:
    """Banda de 100 px é objeto colorido, não cursor (o medido no acervo tem 5–7 px)."""
    r = julgar(_serie_deslizante(), [100] * 30, [102] * 30, 30, 30)
    assert r["veredito"] == "duvida"
    assert r["motivo_duvida"] == "banda_larga"


def test_julgar_movimento_dominado_por_saltos_vira_duvida() -> None:
    """Três saltos grandes em quatro passos: o que parece deslize é teleporte."""
    serie = [(0.0, 100), (0.5, 900), (1.0, 1800), (1.5, 2700), (2.0, 2710)]
    r = julgar(serie, [6] * 5, [102] * 5, 5, 5)
    assert r["veredito"] == "duvida"
    assert r["motivo_duvida"] == "movimento_dominado_por_saltos"
    assert r["n_saltos_grandes"] == 3


def test_julgar_sem_deteccao_e_erratico_permanecem() -> None:
    """Sem detecção não há veredito a rebaixar; série espalhada continua `erratico`."""
    vazio = julgar([], [], [], 241, 241)
    assert vazio["veredito"] == "sem_marcador"
    assert vazio["motivo_duvida"] is None
    espalhada = [(t * 1.0, x) for t, x in enumerate([690, 341, 638, 285, 1527, 548])]
    r = julgar(espalhada, [6] * 6, [102] * 6, 6, 6)
    assert r["veredito"] == "erratico"


def test_agregar_canal_conta_cada_veredito() -> None:
    """A contagem por veredito soma o número de vídeos e separa o utilizável."""
    resultados = [
        _linha("desliza", 100.0),
        _linha("desliza", 104.0),
        _linha("salta", 100.0),
        _linha("parado", None),
        _linha("erratico", None),
        _linha("sem_marcador", None),
        _linha("duvida", 100.0),
    ]
    ag = agregar_canal(resultados)
    assert ag["videos"] == 7
    assert ag["por_veredito"]["desliza"] == 2
    assert ag["por_veredito"]["lento"] == 0  # todo veredito existe na contagem
    assert set(ag["por_veredito"]) == set(VEREDITOS)
    assert ag["marcador_utilizavel"] == 3  # desliza + salta
    assert ag["matiz_mediana_por_video"] == 100.0
    assert ag["matiz_mediana_global"] == 102.5  # mediana do histograma somado
    assert len(ag["por_arquivo"]) == 7


def test_agregar_canais_soma_totais() -> None:
    """O agregado geral soma vídeos e vídeos utilizáveis dos canais."""
    doc = agregar_canais(
        {
            "a": [_linha("desliza", 10.0), _linha("parado", None)],
            "b": [_linha("salta", 200.0)],
        }
    )
    assert doc["total_videos"] == 3
    assert doc["total_utilizavel"] == 2
    assert list(doc["canais"]) == ["a", "b"]


def test_escrever_resumo_grava_e_rele(tmp_path) -> None:
    """`resumo.json` sai dos JSONL e pode ser regravado sem reabrir vídeo."""
    canal = "canal de teste"
    caminho = os.path.join(tmp_path, f"{canal}.jsonl")
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(_linha("desliza", 13.0), ensure_ascii=False) + "\n")
        fh.write("{linha corrompida\n")
        fh.write(json.dumps(_linha("parado", None), ensure_ascii=False) + "\n")
    doc = escrever_resumo(str(tmp_path))
    assert doc["total_videos"] == 2
    assert doc["canais"][canal]["por_veredito"]["desliza"] == 1
    assert doc["parametros"]["passo_s"] == 0.5
    with open(os.path.join(tmp_path, "resumo.json"), encoding="utf-8") as fh:
        lido = json.load(fh)
    assert lido["canais"][canal]["marcador_utilizavel"] == 1


def test_escrever_resumo_sem_jsonl_nao_quebra(tmp_path) -> None:
    """Pasta vazia gera um resumo vazio em vez de estourar."""
    doc = escrever_resumo(str(tmp_path))
    assert doc["canais"] == {}
    assert doc["total_videos"] == 0


def test_listar_videos_com_arvore_falsa(tmp_path) -> None:
    """A listagem por canal funciona sem acervo: só precisa da árvore de pastas."""
    for nome in ("a.mp4", "b.mp4", "c.mkv"):
        aberto = tmp_path / "canal" / nome
        aberto.parent.mkdir(parents=True, exist_ok=True)
        aberto.write_bytes(b"")
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    (vazio / "ignorado.webm").write_bytes(b"")
    achados = listar_videos(str(tmp_path), ["canal"], 2)
    assert set(achados) == {"canal"}
    assert len(achados["canal"]) == 2
    assert all(p.endswith((".mp4", ".mkv")) for p in achados["canal"])


def test_tabela_texto_tem_uma_linha_por_canal() -> None:
    """A tabela do relatório tem cabeçalho, uma linha por canal e a matiz."""
    canais = agregar_canais(
        {
            "sky guitar": [_linha("desliza", 100.0)],
            "cifra club": [_linha("sem_marcador", None)],
        }
    )["canais"]
    linhas = tabela_texto(canais).splitlines()
    assert len(linhas) == 3
    assert linhas[0].startswith("canal")
    assert "sky guitar" in linhas[1]
    assert "102" in linhas[1]
    assert "cifra club" in linhas[2]
