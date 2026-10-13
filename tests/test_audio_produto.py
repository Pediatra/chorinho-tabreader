"""Testes do arquivo irmão chorinho/audio@1 (trilha A5). Sem acervo e sem GPU.

Cobre: (a) montar preserva todas as colunas do alinhamento, recusadas inclusive; (b) cada
regra de ``validar`` é acionada por um caso quebrado; (c) o sha256 do produto detecta a
alteração; (d) a ordem de saída é estável.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tab.audio_produto import (
    ESQUEMA,
    confere_produto,
    main,
    montar,
    validar,
)


def _produto() -> dict:
    """Produto sintético: tela 1 com duas exibições, notas nas colunas 1 a 3.

    Returns:
        Dicionário no formato ``chorinho/video@1`` (só os campos que o módulo lê).
    """
    return {
        "esquema": "chorinho/video@1",
        "telas": [
            {
                "id": 1,
                "exibicoes": [
                    {"t0": 0.0, "t1": 10.0, "tempo": {"medido": False}},
                    {"t0": 10.0, "t1": 20.0, "tempo": {"medido": False}},
                ],
            }
        ],
        "notas": [
            {"tela": 1, "coluna": 1, "corda": 1, "casa": 0, "exibicao": None},
            {"tela": 1, "coluna": 2, "corda": 2, "casa": 3, "exibicao": None},
            {"tela": 1, "coluna": 3, "corda": 3, "casa": 2, "exibicao": None},
        ],
    }


def _alinhado() -> dict:
    """Alinhamento sintético: exibição 0 com três colunas (uma recusada), exibição 1 recusada.

    Returns:
        Dicionário no formato de saída do ``tab.audio_alinhar`` (campos lidos pelo módulo).
    """

    def col(exib: int, coluna: int, t: float | None, motivo: str | None) -> dict:
        """Uma linha de ``colunas`` do alinhamento."""
        afirmada = t is not None
        return {
            "tela": 1,
            "exibicao": exib,
            "coluna": coluna,
            "t_audio": t,
            "confianca": 0.7 if afirmada else None,
            "cos": 0.8 if afirmada else None,
            "motivo": motivo,
        }

    return {
        "metodo": "onsets",
        "transposicao": 0,
        "parametros": {"LIMIAR_COSSENO_EXIBICAO": 0.4, "MIN_COLUNAS_CASADAS": 4},
        "video": {"arquivo": "/acervo/teste.mp4", "t_amostra0": 0.0, "taxa": 22050},
        "exibicoes": [
            {
                "tela": 1,
                "exibicao": 0,
                "trecho_colunas": [1, 3],
                "T_usado_s": 0.5,
                "recusada_exibicao": False,
                "motivo_exibicao": None,
            },
            {
                "tela": 1,
                "exibicao": 1,
                "trecho_colunas": None,
                "T_usado_s": None,
                "recusada_exibicao": True,
                "motivo_exibicao": "poucas colunas casadas: 0 < 4",
            },
        ],
        "colunas": [
            col(0, 1, 1.0, None),
            col(0, 2, 2.5, None),
            col(0, 3, None, "fora_do_trecho"),
            col(1, 1, None, "exibicao_recusada"),
            col(1, 2, None, "exibicao_recusada"),
            col(1, 3, None, "sem_ataque_casado"),
        ],
    }


def _arquivos(tmp_path: Path, produto: dict, alinhado: dict) -> tuple[Path, Path]:
    """Grava o produto e o alinhamento em ``tmp_path``.

    Args:
        tmp_path: pasta temporária do teste.
        produto: JSON do produto.
        alinhado: JSON do alinhamento.

    Returns:
        ``(caminho_produto, caminho_alinhado)``.
    """
    caminho_produto = tmp_path / "produto.json"
    caminho_alinhado = tmp_path / "alinhado.json"
    caminho_produto.write_text(json.dumps(produto), encoding="utf-8")
    caminho_alinhado.write_text(json.dumps(alinhado), encoding="utf-8")
    return caminho_produto, caminho_alinhado


@pytest.fixture
def base(tmp_path: Path) -> tuple[dict, dict]:
    """Arquivo montado e válido, com o produto sintético.

    Args:
        tmp_path: pasta temporária do teste.

    Returns:
        ``(arquivo_montado, produto)``.
    """
    caminho_produto, caminho_alinhado = _arquivos(tmp_path, _produto(), _alinhado())
    d = montar(
        str(caminho_produto),
        str(caminho_alinhado),
        commit="abc123",
        gabarito=["data/gold/audio/folha1.json"],
    )
    return d, _produto()


def test_montar_preserva_todas_as_colunas_inclusive_recusadas(
    tmp_path: Path,
) -> None:
    """Nada é descartado: cada (tela, exibição, coluna) do alinhamento vira uma linha."""
    caminho_produto, caminho_alinhado = _arquivos(tmp_path, _produto(), _alinhado())
    d = montar(str(caminho_produto), str(caminho_alinhado), commit="abc")

    assert d["esquema"] == ESQUEMA
    assert len(d["colunas"]) == len(_alinhado()["colunas"]) == 6
    chaves = {(c["tela"], c["exibicao"], c["coluna"]) for c in d["colunas"]}
    assert chaves == {(1, e, c) for e in (0, 1) for c in (1, 2, 3)}
    recusadas = [c for c in d["colunas"] if c["t_audio"] is None]
    assert len(recusadas) == 4
    assert all(c["motivo"] for c in recusadas)
    exib1 = next(e for e in d["exibicoes"] if e["exibicao"] == 1)
    assert exib1["recusada"] is True
    assert exib1["motivo"] == "poucas colunas casadas: 0 < 4"
    assert d["gerado_por"]["metodo"] == "onsets_v2"
    assert d["gerado_por"]["passagens"] == "so_primeira"
    assert d["gerado_por"]["commit"] == "abc"
    assert d["gerado_por"]["parametros"] == _alinhado()["parametros"]
    assert d["video"] == {"arquivo": "/acervo/teste.mp4", "t_amostra0": 0.0}
    assert validar(d, _produto()) == []


def test_montar_sem_t_amostra0_declara_null(tmp_path: Path) -> None:
    """Sem ``t_amostra0`` no alinhamento o campo fica nulo, sem valor inventado."""
    alinhado = _alinhado()
    del alinhado["video"]["t_amostra0"]
    caminho_produto, caminho_alinhado = _arquivos(tmp_path, _produto(), alinhado)
    d = montar(str(caminho_produto), str(caminho_alinhado), commit="abc")
    assert d["video"]["t_amostra0"] is None


def test_montar_sem_gabarito_grava_lista_vazia(tmp_path: Path) -> None:
    """A aferição registra a lista de gabaritos que foi dada (aqui, nenhuma)."""
    caminho_produto, caminho_alinhado = _arquivos(tmp_path, _produto(), _alinhado())
    d = montar(str(caminho_produto), str(caminho_alinhado), commit="abc", gabarito=[])
    assert d["afericao"] == {
        "gabarito": [],
        "nivel": "ms",
        "resolucao_escuta_ms": 100,
    }


def test_validar_aceita_arquivo_montado(base: tuple[dict, dict]) -> None:
    """O arquivo montado a partir de dados coerentes passa em todas as regras."""
    d, produto = base
    assert validar(d, produto) == []
    assert validar(d) == []


def _mut_esquema(d: dict) -> None:
    """Troca o esquema."""
    d["esquema"] = "chorinho/audio@0"


def _mut_sem_colunas(d: dict) -> None:
    """Tira a chave obrigatória ``colunas`` do topo."""
    del d["colunas"]


def _mut_sem_cos(d: dict) -> None:
    """Tira ``cos`` de uma linha de coluna."""
    del d["colunas"][0]["cos"]


def _mut_t_texto(d: dict) -> None:
    """Põe um texto no lugar do tempo."""
    d["colunas"][0]["t_audio"] = "1.0"


def _mut_nulo_sem_motivo(d: dict) -> None:
    """Tempo nulo sem motivo de recusa."""
    d["colunas"][0]["t_audio"] = None
    d["colunas"][0]["motivo"] = None


def _mut_afirmado_com_motivo(d: dict) -> None:
    """Tempo afirmado com motivo de recusa preenchido."""
    d["colunas"][0]["motivo"] = "cosseno_baixo"


def _mut_confianca(d: dict) -> None:
    """Confiança acima de 1."""
    d["colunas"][0]["confianca"] = 1.5


def _mut_repetida(d: dict) -> None:
    """Uma mesma (tela, exibição, coluna) duas vezes."""
    d["colunas"].append(copy.deepcopy(d["colunas"][0]))


def _mut_nao_crescente(d: dict) -> None:
    """Na mesma exibição, a coluna 2 soa antes da coluna 1."""
    d["colunas"][1]["t_audio"] = 0.5


def _mut_fora_da_janela(d: dict) -> None:
    """Tempo de uma exibição de 0 a 10 s, colocado a 15 s."""
    d["colunas"][0]["t_audio"] = 15.0


def _mut_tela_inexistente(d: dict) -> None:
    """Uma exibição que cita uma tela que o produto não tem."""
    d["exibicoes"][0]["tela"] = 9


def _mut_exibicao_inexistente(d: dict) -> None:
    """Uma coluna que cita uma exibição fora da tela."""
    d["colunas"][0]["exibicao"] = 5


def _mut_nota_sem_entrada(d: dict) -> None:
    """Some a coluna 3 da exibição 0, que tem nota no produto."""
    d["colunas"] = [
        c for c in d["colunas"] if not (c["exibicao"] == 0 and c["coluna"] == 3)
    ]


@pytest.mark.parametrize(
    ("mutar", "trecho"),
    [
        (_mut_esquema, "esquema"),
        (_mut_sem_colunas, "chave ausente: colunas"),
        (_mut_sem_cos, "chave ausente: cos"),
        (_mut_t_texto, "não é número nem null"),
        (_mut_nulo_sem_motivo, "t_audio null sem motivo"),
        (_mut_afirmado_com_motivo, "t_audio afirmado com motivo"),
        (_mut_confianca, "confianca fora de [0, 1]"),
        (_mut_repetida, "entrada repetida"),
        (_mut_nao_crescente, "tempo não crescente"),
        (_mut_fora_da_janela, "fora da janela"),
        (_mut_tela_inexistente, "não existe no produto"),
        (_mut_exibicao_inexistente, "não existe no produto"),
        (_mut_nota_sem_entrada, "nota sem entrada em colunas"),
    ],
)
def test_validar_acusa_cada_regra_quebrada(
    base: tuple[dict, dict], mutar, trecho: str
) -> None:
    """Cada regra quebrada gera um erro com o trecho esperado."""
    d, produto = base
    mutado = copy.deepcopy(d)
    mutar(mutado)
    erros = validar(mutado, produto)
    assert any(trecho in e for e in erros), erros


def test_sha256_detecta_produto_alterado(tmp_path: Path) -> None:
    """O arquivo irmão amarra o produto pelo sha256 dos bytes."""
    caminho_produto, caminho_alinhado = _arquivos(tmp_path, _produto(), _alinhado())
    d = montar(str(caminho_produto), str(caminho_alinhado), commit="abc")
    assert confere_produto(d, caminho_produto) is True

    caminho_produto.write_text(
        json.dumps(_produto(), indent=2) + "\n", encoding="utf-8"
    )
    assert confere_produto(d, caminho_produto) is False
    assert confere_produto(d, tmp_path / "nao_existe.json") is False


def test_ordem_de_saida_e_estavel(tmp_path: Path) -> None:
    """A ordem das linhas não depende da ordem em que o alinhamento as lista."""
    alinhado = _alinhado()
    caminho_produto, caminho_alinhado = _arquivos(tmp_path, _produto(), alinhado)
    primeira = montar(str(caminho_produto), str(caminho_alinhado), commit="abc")

    embaralhado = _alinhado()
    embaralhado["colunas"] = list(reversed(embaralhado["colunas"]))
    embaralhado["exibicoes"] = list(reversed(embaralhado["exibicoes"]))
    caminho_alinhado.write_text(json.dumps(embaralhado), encoding="utf-8")
    segunda = montar(str(caminho_produto), str(caminho_alinhado), commit="abc")

    # O sha256 do próprio alinhamento muda quando o arquivo muda; a ordem é o que importa.
    assert (
        segunda["gerado_por"]["alinhamento_sha256"]
        != (primeira["gerado_por"]["alinhamento_sha256"])
    )
    for secao in ("exibicoes", "colunas"):
        texto_1 = json.dumps(primeira[secao], ensure_ascii=False, indent=1)
        texto_2 = json.dumps(segunda[secao], ensure_ascii=False, indent=1)
        assert texto_1 == texto_2
    chaves = [(c["tela"], c["exibicao"], c["coluna"]) for c in primeira["colunas"]]
    assert chaves == sorted(chaves)


def test_cli_grava_arquivo_valido_e_recusa_o_invalido(tmp_path: Path) -> None:
    """A CLI grava o arquivo quando ele valida e não grava quando ele não valida."""
    caminho_produto, caminho_alinhado = _arquivos(tmp_path, _produto(), _alinhado())
    saida = tmp_path / "saida" / "teste.audio.json"

    assert (
        main(
            [
                "--produto",
                str(caminho_produto),
                "--alinhado",
                str(caminho_alinhado),
                "--saida",
                str(saida),
                "--commit",
                "abc123",
            ]
        )
        == 0
    )
    gravado = json.loads(saida.read_text(encoding="utf-8"))
    assert gravado["esquema"] == ESQUEMA
    assert gravado["gerado_por"]["commit"] == "abc123"
    assert not list(saida.parent.glob(".*.tmp"))

    ruim = _alinhado()
    ruim["colunas"][0]["t_audio"] = 99.0
    caminho_ruim = tmp_path / "ruim.json"
    caminho_ruim.write_text(json.dumps(ruim), encoding="utf-8")
    saida_ruim = tmp_path / "ruim.audio.json"
    assert (
        main(
            [
                "--produto",
                str(caminho_produto),
                "--alinhado",
                str(caminho_ruim),
                "--saida",
                str(saida_ruim),
                "--commit",
                "abc",
            ]
        )
        == 1
    )
    assert not saida_ruim.exists()
