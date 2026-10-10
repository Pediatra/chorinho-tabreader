"""Censo do acervo (Fase 7, T7.1): retomada, formato da linha e classificação.

Sem acervo e sem GPU: os quadros são sintéticos e o vídeo, quando preciso, é um arquivo
inválido (o ``ffprobe`` devolve duração zero e o censo declara o erro).
"""

from __future__ import annotations

import json
import os

import numpy as np

from tab import censo


def _instantes(com_tab: list[bool]) -> list[dict]:
    """Medidas de presença sintéticas, uma por fração de ``FRACOES_PRESENCA``."""
    return [
        {"frac": f, "t": float(k), "tab": t, "rect": [0, 0, 1, 1] if t else None}
        for k, (f, t) in enumerate(zip(censo.FRACOES_PRESENCA, com_tab, strict=True))
    ]


def _janela(**medidas: bool) -> dict:
    """Janela sintética com as quatro medidas, todas falsas por padrão."""
    base = {"faixa": False, "cor": False, "troca_tela": False, "rolagem": False}
    base.update(medidas)
    return base


def test_chave_muda_com_tamanho_e_mtime(tmp_path) -> None:
    arquivo = tmp_path / "canal" / "video.mp4"
    arquivo.parent.mkdir()
    arquivo.write_bytes(b"0123456789")
    os.utime(arquivo, (1_700_000_000, 1_700_000_000))
    chave = censo.chave_do_arquivo(str(arquivo), str(tmp_path))
    assert chave == "canal/video.mp4|10|1700000000"
    os.utime(arquivo, (1_700_000_500, 1_700_000_500))
    assert censo.chave_do_arquivo(str(arquivo), str(tmp_path)) != chave
    os.utime(arquivo, (1_700_000_000, 1_700_000_000))
    arquivo.write_bytes(b"0123456789AB")
    os.utime(arquivo, (1_700_000_000, 1_700_000_000))
    assert censo.chave_do_arquivo(str(arquivo), str(tmp_path)) != chave


def test_chave_trunca_mtime_para_inteiro() -> None:
    assert censo.chave_de("a/b.mp4", 7, 1_700_000_000.9) == "a/b.mp4|7|1700000000"


def test_ja_feitas_ignora_erro_linha_ruim_e_refaz_o_erro(tmp_path) -> None:
    saida = tmp_path / "censo.jsonl"
    linhas = [
        {"chave": "a|1|1", "arquivo": "a", "tablatura": True},
        {"chave": "b|1|1", "arquivo": "b", "erro": "ValueError: x"},
        {"chave": "c|1|1", "arquivo": "c", "tablatura": False},
        {"chave": "c|1|1", "arquivo": "c", "erro": "OSError: y"},
    ]
    with open(saida, "w", encoding="utf-8") as fh:
        for linha in linhas:
            fh.write(json.dumps(linha) + "\n")
        fh.write("isto não é json\n")
    assert censo.ja_feitas(str(saida)) == {"a|1|1"}
    assert censo.ja_feitas(str(tmp_path / "nao_existe.jsonl")) == set()


def test_registro_de_arquivo_invalido_declara_erro(tmp_path) -> None:
    arquivo = tmp_path / "canal" / "lixo.mp4"
    arquivo.parent.mkdir()
    arquivo.write_bytes(b"isto nao e video")
    registro = censo.censar_video(str(arquivo), str(tmp_path))
    assert registro["arquivo"] == "canal/lixo.mp4"
    assert registro["canal"] == "canal"
    assert registro["chave"].startswith("canal/lixo.mp4|")
    assert registro["erro"] == "duracao_desconhecida"
    # a linha tem de ser JSON puro (sem tipos do numpy)
    json.loads(json.dumps(registro, ensure_ascii=False))


def test_fracoes_de_presenca_de_005_a_095() -> None:
    fracoes = censo.FRACOES_PRESENCA
    assert len(fracoes) == 12
    assert fracoes[0] == 0.05
    assert fracoes[-1] == 0.95


def test_sem_tablatura_em_nenhum_instante() -> None:
    resultado = censo.classificar(_instantes([False] * 12), [])
    assert resultado == {
        "tablatura": False,
        "frac_tablatura": 0.0,
        "marcador": None,
        "forma": None,
    }


def test_tablatura_sem_janela_nao_inventa_marcador_nem_forma() -> None:
    resultado = censo.classificar(_instantes([True] + [False] * 11), [])
    assert resultado["tablatura"] is True
    assert resultado["marcador"] is None
    assert resultado["forma"] is None


def test_faixa_tem_prioridade_sobre_cor_e_rolagem() -> None:
    janelas = [_janela(faixa=True, cor=True, rolagem=True)]
    resultado = censo.classificar(_instantes([True] * 12), janelas)
    assert resultado["marcador"] == "faixa"
    assert resultado["forma"] == "rolante"


def test_cor_sem_faixa_e_troca_dao_paginado() -> None:
    janelas = [_janela(cor=True, troca_tela=True)]
    resultado = censo.classificar(_instantes([True] * 12), janelas)
    assert resultado["marcador"] == "cor"
    assert resultado["forma"] == "paginado"


def test_sem_marcador_e_fixo() -> None:
    resultado = censo.classificar(_instantes([True] * 12), [_janela()])
    assert resultado["marcador"] == "sem_marcador"
    assert resultado["forma"] == "fixo"


def test_fracao_ignora_instante_com_erro() -> None:
    instantes = _instantes([True, True, True] + [False] * 9)
    instantes[-1] = {"frac": 0.95, "t": 9.0, "erro": "sem_quadro"}
    resultado = censo.classificar(instantes, [])
    assert resultado["frac_tablatura"] == round(3 / 11, 3)


def test_escolhe_ate_tres_instantes_espalhados() -> None:
    instantes = _instantes([True] * 10 + [False] * 2)
    escolhidos = censo.escolher_instantes_com_tab(instantes)
    assert [i["t"] for i in escolhidos] == [0.0, 5.0, 9.0]
    poucos = _instantes([False, True, False, True] + [False] * 8)
    assert [i["t"] for i in censo.escolher_instantes_com_tab(poucos)] == [1.0, 3.0]


def test_janela_de_dez_segundos_recuada_no_fim() -> None:
    assert censo.janela_em(5.0, 60.0) == (5.0, 15.0)
    assert censo.janela_em(58.0, 60.0) == (50.0, 60.0)
    assert censo.janela_em(2.0, 6.0) == (0.0, 6.0)


def test_amostra_espalhada_e_deterministica() -> None:
    videos = [f"v{i:03d}" for i in range(100)]
    amostra = censo.amostra_espalhada(videos, 20)
    assert len(amostra) == 20
    assert amostra[0] == "v000"
    assert amostra[-1] == "v099"
    assert amostra == censo.amostra_espalhada(videos, 20)
    assert censo.amostra_espalhada(videos[:5], 20) == videos[:5]


def _quadro_sintetico(seed: int) -> np.ndarray:
    """Quadro cinza com blocos escuros em posições aleatórias (não é tablatura)."""
    rng = np.random.default_rng(seed)
    quadro = np.full((300, 1200, 3), 240, np.uint8)
    for _ in range(40):
        x = int(rng.integers(0, 1100))
        y = int(rng.integers(0, 260))
        quadro[y : y + 40, x : x + 40] = 30
    return quadro


def test_medir_janela_troca_e_estatica(monkeypatch) -> None:
    estatico = _quadro_sintetico(1)
    alternado = [_quadro_sintetico(s) for s in (1, 2)]

    def quadros_estaticos(caminho, t0, t1, qps, recorte_y=None):
        for k in range(6):
            yield t0 + k / qps, estatico

    def quadros_trocando(caminho, t0, t1, qps, recorte_y=None):
        for k in range(6):
            yield t0 + k / qps, alternado[k % 2]

    rect = (0, 0, 1200, 300)
    monkeypatch.setattr(censo.leitor, "quadros", quadros_estaticos)
    parado = censo.medir_janela("v.mp4", 0.0, 10.0, rect)
    assert parado["quadros"] == 6
    assert parado["troca_tela"] is False
    assert parado["rolagem"] is False
    assert parado["faixa"] is False
    assert parado["cor"] is False

    monkeypatch.setattr(censo.leitor, "quadros", quadros_trocando)
    trocando = censo.medir_janela("v.mp4", 0.0, 10.0, rect)
    assert trocando["troca_tela"] is True
