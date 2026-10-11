"""Censo do acervo (Fase 7, T7.1): retomada, formato da linha e classificação.

Sem acervo e sem GPU: os quadros são sintéticos e o vídeo, quando preciso, é um arquivo
inválido (o ``ffprobe`` devolve duração zero e o censo declara o erro).
"""

from __future__ import annotations

import json
import os
import sys

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

    def recortes(fonte) -> list:
        return [censo.telas.recortar(q, rect) for _t, q in fonte(None, 0, 10, 3.0)]

    parado = censo.medir_janela(0.0, 10.0, recortes(quadros_estaticos))
    assert parado["quadros"] == 6
    assert parado["troca_tela"] is False
    assert parado["rolagem"] is False
    assert parado["faixa"] is False
    assert parado["cor"] is False

    trocando = censo.medir_janela(0.0, 10.0, recortes(quadros_trocando))
    assert trocando["troca_tela"] is True


def test_sorteio_do_piloto_e_fixo_e_por_canal():
    """O piloto sorteia N vídeos por canal com semente fixa: o mesmo sorteio sempre."""
    por_canal = {
        "a": [f"a/{k}.mp4" for k in range(10)],
        "b": [f"b/{k}.mp4" for k in range(2)],
    }
    primeiro = censo.sortear_piloto(por_canal, 3)
    assert primeiro == censo.sortear_piloto(por_canal, 3)
    assert len(primeiro["a"]) == 3
    assert len(primeiro["b"]) == 2  # canal com menos vídeos que N leva todos
    assert set(primeiro["a"]) <= set(por_canal["a"])


def test_slug_do_canal_tira_acento_e_tem_fallback():
    """Nome de arquivo da folha: ASCII minúsculo; sem letras, cai para canal_NN."""
    assert censo.slug_do_canal("guitar dell ́arte", 1) == "guitar_dell_arte"
    assert censo.slug_do_canal("pablo romé", 2) == "pablo_rome"
    assert censo.slug_do_canal("ギタロー", 7) == "canal_07"


YAML_EXEMPLO = """\
versao: 1
canais:

  "tv cifras":
    fonte: decisão do dono
    rollout: fora               # decisão do dono
    motivo: "51/537 vídeos"

  iwaki:
    medido: >
      texto solto
      rollout: nao_e_campo
    partitura: true

  "sky guitar":
    rollout: dentro
"""


def _gravar_video(raiz, rel: str, mtime: int = 1_700_000_000) -> str:
    """Cria um arquivo de vídeo falso em ``raiz/rel`` e devolve o caminho."""
    arquivo = raiz / rel
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(b"0123456789")
    os.utime(arquivo, (mtime, mtime))
    return str(arquivo)


def test_ler_rollout_sem_pyyaml(tmp_path) -> None:
    """Lê ``rollout`` dos canais; ignora blocos de texto e canal sem o campo."""
    arquivo = tmp_path / "canais.yaml"
    arquivo.write_text(YAML_EXEMPLO, encoding="utf-8")
    assert censo.ler_rollout(arquivo) == {
        "tv cifras": "fora",
        "iwaki": "",
        "sky guitar": "dentro",
    }
    assert censo.ler_rollout(tmp_path / "nao_existe.yaml") == {}


def test_yaml_do_projeto_marca_os_dois_canais_fora() -> None:
    """A decisão 0009 está no arquivo real: os dois canais saem do censo padrão."""
    fora = censo.canais_fora(censo.ler_rollout(censo.CANAIS))
    assert {"violaodecria", "tv cifras"} <= fora
    assert "sky guitar" not in fora


def test_video_novo_em_canal_existente_e_o_unico_pendente(tmp_path) -> None:
    """Retomada: os censados não voltam; o novo entra; mudança de mtime ou erro refaz."""
    raiz = tmp_path / "acervo"
    a = _gravar_video(raiz, "canal/a.mp4")
    b = _gravar_video(raiz, "canal/b.mp4")
    c = _gravar_video(raiz, "canal/c.mp4")  # o vídeo novo
    saida = tmp_path / "censo.jsonl"
    with open(saida, "w", encoding="utf-8") as fh:
        for v in (a, b):
            chave = censo.chave_do_arquivo(v, str(raiz))
            fh.write(json.dumps({"chave": chave, "arquivo": v}) + "\n")
    feitas = censo.ja_feitas(str(saida))
    assert censo.pendentes_de([a, b, c], str(raiz), feitas) == [c]
    # arquivo que mudou de data ganha chave nova e volta a pendente
    os.utime(a, (1_700_000_500, 1_700_000_500))
    assert censo.pendentes_de([a, b, c], str(raiz), feitas) == [a, c]
    # linha com erro não conta como feita
    with open(saida, "a", encoding="utf-8") as fh:
        chave_b = censo.chave_do_arquivo(b, str(raiz))
        fh.write(json.dumps({"chave": chave_b, "erro": "X: y"}) + "\n")
    assert censo.pendentes_de([b], str(raiz), censo.ja_feitas(str(saida))) == [b]


def test_estratificacao_com_video_novo(tmp_path) -> None:
    """Com ``--janelas-por-canal``: canal até N vídeos todos ganham janela; acima de N o
    novo ganha só se cair na amostra recalculada (extremos sempre caem, interior pode não)."""
    pequeno = [f"c/{k:02d}.mp4" for k in range(10)]
    assert "c/zz.mp4" in censo.amostra_espalhada([*pequeno, "c/zz.mp4"], 30)
    grande = [f"c/{k:03d}.mp4" for k in range(100)]
    assert len(censo.amostra_espalhada(grande, 30)) == 30
    fim = censo.amostra_espalhada([*grande, "c/zz.mp4"], 30)
    assert len(fim) == 30 and "c/zz.mp4" in fim
    meio = [*grande[:51], "c/050a.mp4", *grande[51:]]
    amostra_meio = censo.amostra_espalhada(meio, 30)
    assert len(amostra_meio) == 30 and "c/050a.mp4" not in amostra_meio


def test_resumo_do_lote_marca_canal_novo(tmp_path) -> None:
    """Resumo final: total, por canal (canal novo marcado) e contagem de canais novos."""
    linhas = censo.resumo_do_lote({"novo": 2, "antigo": 1}, ["novo", "outro"], 1)
    assert linhas[0] == "resumo: 3 vídeos novos censados em 2 canais (1 com erro)"
    assert linhas[1] == "  antigo: 1"
    assert linhas[2] == "  novo: 2 (canal novo)"
    assert linhas[3].startswith("canais novos no acervo: 2")
    assert "outro" in linhas[3]


def test_censo_padrao_pula_fora_e_censa_so_o_novo(
    tmp_path, monkeypatch, capsys
) -> None:
    """Execução sem --canal: pula ``rollout: fora``, não refaz o que já está no JSONL e
    censa só o vídeo novo (de canal existente e de canal sem entrada no yaml)."""
    raiz = tmp_path / "acervo"
    antigo_a = _gravar_video(raiz, "antigo/a.mp4")
    antigo_b = _gravar_video(raiz, "antigo/b.mp4")
    _gravar_video(raiz, "antigo/novo_video.mp4")
    _gravar_video(raiz, "fora/x.mp4")
    _gravar_video(raiz, "sem_yaml/n.mp4")
    yaml = tmp_path / "canais.yaml"
    yaml.write_text(
        'versao: 1\ncanais:\n\n  "fora":\n    rollout: fora\n\n  antigo:\n'
        "    fonte: teste\n",
        encoding="utf-8",
    )
    saida = tmp_path / "censo.jsonl"
    with open(saida, "w", encoding="utf-8") as fh:
        for v in (antigo_a, antigo_b):
            chave = censo.chave_do_arquivo(v, str(raiz))
            fh.write(json.dumps({"chave": chave, "arquivo": v}) + "\n")
    monkeypatch.setattr(censo, "CANAIS", yaml)
    monkeypatch.setattr(
        sys, "argv", ["censo", "--raiz", str(raiz), "--saida", str(saida)]
    )
    assert censo.main() == 0
    with open(saida, encoding="utf-8") as fh:
        novas = [json.loads(linha)["arquivo"] for linha in fh][2:]
    assert sorted(novas) == ["antigo/novo_video.mp4", "sem_yaml/n.mp4"]
    out = capsys.readouterr().out
    assert "pulados (rollout: fora, decisão 0009): fora" in out
    assert "canal novo (sem entrada em configs/canais.yaml): sem_yaml" in out
    assert "resumo: 2 vídeos novos censados em 2 canais" in out
    assert "  sem_yaml: 1 (canal novo)" in out
