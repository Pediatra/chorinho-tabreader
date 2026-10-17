"""DeepSeek direto (rodada 1020): chave, pedido, E0, recorte do E3 e retomada.

Tudo sintético: ``_chamar`` é simulado, sem rede, sem chave real e sem acervo.
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import cv2
import numpy as np
import pytest

from tab import maos_braco_deepseek as dsk


def _resposta(
    texto: str, raciocinio: str | None = None, uso: dict | None = None
) -> dict:
    """Resposta no formato de chat da API, com ``usage``."""
    return {
        "choices": [{"message": {"content": texto, "reasoning_content": raciocinio}}],
        "usage": uso or {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _png(pasta: Path, quadro: str) -> None:
    """Grava um PNG sintético 400x300 em ``pasta``."""
    pasta.mkdir(parents=True, exist_ok=True)
    imagem = np.full((300, 400, 3), 128, dtype=np.uint8)
    cv2.imwrite(str(pasta / f"{quadro}.png"), imagem)


def _falha_http(codigo: int) -> urllib.error.HTTPError:
    """Erro HTTP da API, sem corpo."""
    return urllib.error.HTTPError("https://api.invalido", codigo, "x", {}, None)


@pytest.fixture
def pastas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redireciona saída e quadros para ``tmp_path`` e zera as esperas."""
    monkeypatch.setattr(dsk, "MAOS_M20", tmp_path / "m20")
    monkeypatch.setattr(dsk, "MAOS_M3B_QUADROS", tmp_path / "quadros")
    monkeypatch.setattr(dsk, "ESPERAS_S", (0, 0))
    _png(tmp_path / "quadros", "q01")
    return tmp_path


# ---------------------------------------------------------------------------------
# Chave
# ---------------------------------------------------------------------------------


def test_ler_chave_arquivo_ausente_erro_claro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(dsk.VARIAVEL_CHAVE, raising=False)
    with pytest.raises(dsk.ChaveAusente, match="ausente"):
        dsk.ler_chave(tmp_path / "nao_existe")


def test_ler_chave_arquivo_vazio_e_recusado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(dsk.VARIAVEL_CHAVE, raising=False)
    arquivo = tmp_path / "chave"
    arquivo.write_text("  \n", encoding="utf-8")
    with pytest.raises(dsk.ChaveAusente, match="vazia"):
        dsk.ler_chave(arquivo)


def test_ler_chave_le_arquivo_sem_espacos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(dsk.VARIAVEL_CHAVE, raising=False)
    arquivo = tmp_path / "chave"
    arquivo.write_text("  SEGREDO-DE-TESTE\n", encoding="utf-8")
    assert dsk.ler_chave(arquivo) == "SEGREDO-DE-TESTE"


def test_ler_chave_ambiente_tem_prioridade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(dsk.VARIAVEL_CHAVE, " DO-AMBIENTE ")
    arquivo = tmp_path / "chave"
    arquivo.write_text("DO-ARQUIVO", encoding="utf-8")
    assert dsk.ler_chave(arquivo) == "DO-AMBIENTE"


def test_main_sem_chave_sai_com_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(dsk.VARIAVEL_CHAVE, raising=False)
    monkeypatch.setattr(dsk, "CHAVE_CONTAINER", tmp_path / "nao_existe")
    assert dsk.main(["e1"]) == 2
    assert "ausente" in capsys.readouterr().err


# ---------------------------------------------------------------------------------
# Corpo do pedido e requisição
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize(("pensar", "tipo"), [(False, "disabled"), (True, "enabled")])
def test_corpo_pedido_modelo_temperatura_e_raciocinio(pensar: bool, tipo: str) -> None:
    conteudo = [{"type": "text", "text": "oi"}]
    corpo = dsk.corpo_pedido(conteudo, pensar=pensar)
    assert corpo["model"] == "deepseek-flash"
    assert corpo["temperature"] == 0
    assert corpo["thinking"] == {"type": tipo}
    assert corpo["messages"] == [{"role": "user", "content": conteudo}]


def test_bloco_imagem_jpeg_com_detail_alto() -> None:
    bloco = dsk.bloco_imagem("AAAA")
    assert bloco["type"] == "image_url"
    assert bloco["image_url"]["url"] == "data:image/jpeg;base64,AAAA"
    assert bloco["image_url"]["detail"] == "high"


def test_montar_requisicao_usa_bearer_e_post() -> None:
    requisicao = dsk.montar_requisicao({"model": "x"}, "CHAVE-TESTE")
    assert requisicao.full_url == dsk.URL_API
    assert requisicao.get_method() == "POST"
    assert requisicao.get_header("Authorization") == "Bearer CHAVE-TESTE"


# ---------------------------------------------------------------------------------
# Pedido, retentativas e registro
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("falha", "transitorio"),
    [
        (_falha_http(429), True),
        (_falha_http(503), True),
        (_falha_http(400), False),
        (urllib.error.URLError(TimeoutError("demorou")), True),
        (ConnectionResetError("resetada"), True),
        (TimeoutError("tempo"), True),
        (ValueError("não é JSON"), False),
    ],
)
def test_eh_transitorio(falha: Exception, transitorio: bool) -> None:
    assert dsk._eh_transitorio(falha) is transitorio


def test_pedir_recupera_429_em_retentativa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    respostas: list[object] = [_falha_http(429), _falha_http(429), _resposta("{}")]
    monkeypatch.setattr(dsk, "ESPERAS_S", (0, 0))

    def chamar(corpo: dict, chave: str) -> dict:
        proximo = respostas.pop(0)
        if isinstance(proximo, Exception):
            raise proximo
        assert isinstance(proximo, dict)
        return proximo

    monkeypatch.setattr(dsk, "_chamar", chamar)
    registro = dsk.pedir({"model": "x"}, "CHAVE")
    assert registro["erro"] is None
    assert registro["tentativas"] == 3
    assert registro["conteudo"] == "{}"


def test_pedir_erro_400_nao_repete(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[int] = []

    def chamar(corpo: dict, chave: str) -> dict:
        chamadas.append(1)
        raise _falha_http(400)

    monkeypatch.setattr(dsk, "_chamar", chamar)
    registro = dsk.pedir({"model": "x"}, "CHAVE")
    assert registro["erro"] == "HTTP 400"
    assert registro["tentativas"] == 1
    assert len(chamadas) == 1


def test_pedir_esgota_tentativas_em_transitorio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas: list[int] = []

    def chamar(corpo: dict, chave: str) -> dict:
        chamadas.append(1)
        raise _falha_http(500)

    monkeypatch.setattr(dsk, "_chamar", chamar)
    monkeypatch.setattr(dsk, "ESPERAS_S", (0, 0))
    registro = dsk.pedir({"model": "x"}, "CHAVE")
    assert registro["erro"] == "HTTP 500"
    assert registro["tentativas"] == dsk.TENTATIVAS
    assert len(chamadas) == dsk.TENTATIVAS


def test_pedir_guarda_raciocinio_e_uso(monkeypatch: pytest.MonkeyPatch) -> None:
    uso = {"prompt_tokens": 100, "completion_tokens": 40}
    monkeypatch.setattr(
        dsk, "_chamar", lambda corpo, chave: _resposta("", "pensei", uso)
    )
    registro = dsk.pedir({"model": "x"}, "CHAVE")
    assert registro["conteudo"] == ""
    assert registro["raciocinio"] == "pensei"
    assert registro["uso"] == uso


def test_chave_nunca_aparece_no_registro(
    pastas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dsk, "_chamar", lambda corpo, chave: _resposta("{}"))
    chave = "CHAVE-SECRETA-DE-TESTE-9876"
    assert chave not in json.dumps(dsk.pedir({"model": "x"}, chave))
    assert dsk._pedido_e0("s08_a00", chave) == "ok"
    gravados = list((pastas / "m20").rglob("*.json"))
    assert gravados
    for arquivo in gravados:
        assert chave not in arquivo.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------
# E0: sonda sintética
# ---------------------------------------------------------------------------------


def test_desenhar_e0_tem_o_tamanho_do_quadro() -> None:
    imagem = dsk.desenhar_e0(8, 0.0)
    assert imagem.shape == (dsk.ALTURA_E0, dsk.LARGURA_E0, 3)
    assert imagem.dtype == np.uint8


def test_geometria_e0_linhas_com_espacamento_perpendicular() -> None:
    linhas = dsk.geometria_e0(20, 0.0)
    assert len(linhas) == dsk.N_LINHAS
    # Sem inclinação, a distância vertical entre linhas vizinhas é o espaçamento.
    assert linhas[1][0][1] - linhas[0][0][1] == pytest.approx(20.0)
    assert linhas[0][0][0] == pytest.approx(linhas[0][1][0] - dsk.COMPRIMENTO_E0)


def _resposta_e0(linhas: list[np.ndarray], trocar: bool = False) -> str:
    """JSON da resposta perfeita (0 a 1000), com 1 e 6 trocadas se ``trocar``."""

    def normalizar(p: np.ndarray) -> list[float]:
        return [p[0] * 1000 / dsk.LARGURA_E0, p[1] * 1000 / dsk.ALTURA_E0]

    l1, l6 = linhas[0], linhas[-1]
    if trocar:
        l1, l6 = l6, l1
    return json.dumps(
        {
            "linha1": [normalizar(p) for p in l1],
            "linha6": [normalizar(p) for p in l6],
        }
    )


def test_erros_e0_resposta_perfeita_nao_troca() -> None:
    linhas = dsk.geometria_e0(14, 12.0)
    medida = dsk.erros_e0(_resposta_e0(linhas), 14, 12.0)
    assert medida is not None
    assert medida["erro1"] < 1e-3
    assert medida["erro6"] < 1e-3
    assert medida["trocou"] is False


def test_erros_e0_resposta_trocada_conta_troca() -> None:
    linhas = dsk.geometria_e0(14, 12.0)
    medida = dsk.erros_e0(_resposta_e0(linhas, trocar=True), 14, 12.0)
    assert medida is not None
    assert medida["trocou"] is True
    assert medida["erro1"] > 0.5


def test_erros_e0_sem_as_duas_linhas_devolve_none() -> None:
    assert dsk.erros_e0('{"linha1": [[1, 2], [3, 4]]}', 8, 0.0) is None
    assert dsk.erros_e0("sem json", 8, 0.0) is None


def test_pedido_e0_grava_imagem_e_registro(
    pastas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dsk, "_chamar", lambda corpo, chave: _resposta("{}"))
    assert dsk._pedido_e0("s14_a12", "CHAVE") == "ok"
    registro = json.loads(
        (pastas / "m20" / "e0" / "s14_a12.json").read_text(encoding="utf-8")
    )
    assert registro["exp"] == "e0" and registro["quadro"] == "s14_a12"
    assert (pastas / "m20" / "e0" / "s14_a12.png").exists()


# ---------------------------------------------------------------------------------
# Retomada e conjunto de desenvolvimento
# ---------------------------------------------------------------------------------


def test_retomada_pula_pedido_sem_erro(
    pastas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo = pastas / "m20" / "e1" / "q01.json"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text(
        json.dumps({"exp": "e1", "quadro": "q01", "conteudo": "{}", "erro": None}),
        encoding="utf-8",
    )
    chamadas: list[int] = []
    monkeypatch.setattr(
        dsk, "_chamar", lambda corpo, chave: chamadas.append(1) or _resposta("{}")
    )
    assert dsk._pedido_quadro("e1", "q01", False, "CHAVE") == "pulado"
    assert chamadas == []


def test_retomada_refaz_pedido_com_erro(
    pastas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo = pastas / "m20" / "e1" / "q01.json"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text(
        json.dumps({"exp": "e1", "quadro": "q01", "conteudo": "", "erro": "HTTP 500"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(dsk, "_chamar", lambda corpo, chave: _resposta("{}"))
    assert dsk._pedido_quadro("e1", "q01", False, "CHAVE") == "ok"
    assert json.loads(arquivo.read_text(encoding="utf-8"))["erro"] is None


def test_exigir_dev_recusa_quadro_de_teste() -> None:
    with pytest.raises(ValueError, match="teste lacrado"):
        dsk.exigir_dev(["q09"], ["q01", "q02"])


def test_escolher_quadros_so_aceita_dev() -> None:
    dev = ["q01", "q02", "q05"]
    assert dsk.escolher_quadros(["q02"], None, dev) == ["q02"]
    assert dsk.escolher_quadros(None, 2, dev) == ["q01", "q02"]
    assert dsk.escolher_quadros(None, None, dev) == dev
    with pytest.raises(ValueError):
        dsk.escolher_quadros(["q01", "q09"], None, dev)


# ---------------------------------------------------------------------------------
# E3: caixa, margem e recorte
# ---------------------------------------------------------------------------------


def test_caixa_com_margem_no_meio_do_quadro() -> None:
    assert dsk.caixa_com_margem((400.0, 400.0, 600.0, 600.0), 1000, 1000) == (
        380,
        380,
        620,
        620,
    )


def test_caixa_com_margem_corta_na_borda_esquerda_e_superior() -> None:
    recorte = dsk.caixa_com_margem((0.0, 0.0, 500.0, 500.0), 1000, 1000)
    assert recorte == (0, 0, 550, 550)


def test_caixa_com_margem_corta_na_borda_direita_e_inferior() -> None:
    recorte = dsk.caixa_com_margem((600.0, 600.0, 1000.0, 1000.0), 1000, 1000)
    assert recorte == (560, 560, 1000, 1000)


def test_caixa_da_resposta_ordena_e_recusa_invalida() -> None:
    assert dsk.caixa_da_resposta('{"caixa": [900, 800, 100, 100]}') == (
        100.0,
        100.0,
        900.0,
        800.0,
    )
    assert dsk.caixa_da_resposta('{"caixa": [1, 2, 3]}') is None
    assert dsk.caixa_da_resposta('{"caixa": [5, 5, 5, 900]}') is None
    assert dsk.caixa_da_resposta("sem json") is None


def test_dimensoes_recorte_respeitam_largura_e_lado() -> None:
    nova_largura, nova_altura, escala = dsk.dimensoes_recorte(100, 300)
    assert nova_largura <= dsk.LARGURA_RECORTE
    assert nova_altura <= dsk.LADO_RECORTE
    assert escala == pytest.approx(nova_largura / 100)
    assert (nova_largura, nova_altura) == (433, 1300)
    assert dsk.dimensoes_recorte(800, 200)[:2] == (1280, 320)


def test_ponto_do_recorte_e_inverso_da_normalizacao() -> None:
    recorte = (80, 60, 320, 240)
    # Um ponto do original, em 0 a 1000, vai ao recorte e volta sem erro.
    x_original, y_original = 250.0, 150.0
    xr = (x_original - 80) * 1000 / 240
    yr = (y_original - 60) * 1000 / 180
    x, y = dsk.ponto_do_recorte((xr, yr), recorte)
    assert (x, y) == pytest.approx((x_original, y_original))


def test_converter_resposta_recorte_na_borda_do_quadro() -> None:
    # Recorte encostado na borda esquerda e superior: (0, 0) do recorte é (0, 0).
    recorte = (0, 0, 200, 200)
    conteudo = json.dumps(
        {
            "braco": "sim",
            "nut": [0, 0],
            "corda1": [[0, 0], [1000, 1000]],
            "corda6": [[500, 500], "fora"],
            "traste5": None,
            "traste12": [1000, 1000],
        }
    )
    convertido = json.loads(
        dsk.converter_resposta_recorte(conteudo, recorte, 1000, 1000)
    )
    assert convertido["nut"] == [0.0, 0.0]
    assert convertido["corda1"] == [[0.0, 0.0], [200.0, 200.0]]
    assert convertido["corda6"][0] == [100.0, 100.0]
    assert convertido["corda6"][1] == "fora"
    assert convertido["traste5"] is None
    assert convertido["traste12"] == [200.0, 200.0]


def test_converter_resposta_recorte_sem_json_devolve_none() -> None:
    assert dsk.converter_resposta_recorte("oi", (0, 0, 10, 10), 100, 100) is None


def test_pedido_e3_duas_etapas_gravam_recorte(
    pastas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas: list[str] = []

    def chamar(corpo: dict, chave: str) -> dict:
        texto = corpo["messages"][0]["content"][0]["text"]
        chamadas.append(texto)
        if '"caixa"' in texto and "recorte" not in texto:
            return _resposta('{"caixa": [250, 250, 750, 750]}')
        return _resposta('{"braco": "sim"}')

    monkeypatch.setattr(dsk, "_chamar", chamar)
    assert dsk._pedido_e3("q01", "CHAVE", pensar=False) == "ok"
    assert len(chamadas) == 2
    assert chamadas[1].startswith(dsk.PREFIXO_E3)
    caixa = json.loads((pastas / "m20" / "e3" / "q01_caixa.json").read_text("utf-8"))
    assert caixa["erro"] is None
    registro = json.loads((pastas / "m20" / "e3" / "q01.json").read_text("utf-8"))
    assert registro["recorte"] == [80, 60, 320, 240]
    assert registro["escala"] == pytest.approx(1280 / 240)


def test_pedido_e3_caixa_invalida_nao_pede_segunda_etapa(
    pastas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas: list[int] = []

    def chamar(corpo: dict, chave: str) -> dict:
        chamadas.append(1)
        return _resposta('{"caixa": [1]}')

    monkeypatch.setattr(dsk, "_chamar", chamar)
    assert dsk._pedido_e3("q01", "CHAVE", pensar=False) == "caixa_invalida"
    assert len(chamadas) == 1
    registro = json.loads((pastas / "m20" / "e3" / "q01.json").read_text("utf-8"))
    assert registro["motivo"] == "caixa_invalida"
    assert registro["recorte"] is None


def test_pedido_e3_retomada_pula_quando_pronto(
    pastas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo = pastas / "m20" / "e3" / "q01.json"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text(
        json.dumps({"exp": "e3", "quadro": "q01", "conteudo": "{}", "erro": None}),
        encoding="utf-8",
    )
    chamadas: list[int] = []
    monkeypatch.setattr(
        dsk, "_chamar", lambda corpo, chave: chamadas.append(1) or _resposta("{}")
    )
    assert dsk._pedido_e3("q01", "CHAVE", pensar=True) == "pulado"
    assert chamadas == []
