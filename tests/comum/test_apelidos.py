"""Os nomes antigos dos módulos continuam valendo (decisão 9001), e o que importa ``tab``
fora do Python 3.14 continua importável."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

import tab
from tab._apelidos import APELIDOS
from tab.comum import caminhos

RAIZ = Path(__file__).resolve().parents[2]
#: Bibliotecas que só existem nas imagens derivadas: o módulo é conferido lá, não aqui.
SO_EM_IMAGEM_DERIVADA = ("basic_pitch", "librosa", "matplotlib", "mediapipe", "rtmlib")


def _importar(antigo: str):
    """Importa o módulo novo de um apelido.

    Quando falta uma biblioteca que só existe numa imagem derivada, não importa: confere só
    que o nome antigo e o novo apontam para o mesmo arquivo (sem pular o teste).

    Args:
        antigo: nome antigo pontuado.

    Returns:
        O módulo novo, ou None quando só o arquivo foi conferido.
    """
    try:
        return importlib.import_module(APELIDOS[antigo])
    except ModuleNotFoundError as erro:
        if not (erro.name and erro.name.split(".")[0] in SO_EM_IMAGEM_DERIVADA):
            raise
    velho = importlib.util.find_spec(antigo)
    assert velho is not None
    assert velho.origin == importlib.util.find_spec(APELIDOS[antigo]).origin
    return None


def test_cada_apelido_aponta_para_um_arquivo_que_existe():
    faltam = [a for a, n in APELIDOS.items() if importlib.util.find_spec(n) is None]
    assert not faltam


def test_nenhum_apelido_colide_com_um_modulo_de_verdade():
    reais = {
        "tab." + ".".join(p.relative_to(RAIZ / "tab").with_suffix("").parts)
        for p in (RAIZ / "tab").rglob("*.py")
    }
    assert not set(APELIDOS) & reais
    assert len(set(APELIDOS.values())) == len(APELIDOS)


@pytest.mark.parametrize("antigo", sorted(APELIDOS))
def test_as_tres_formas_do_nome_antigo_dao_o_mesmo_objeto(antigo):
    novo = _importar(antigo)
    if novo is None:
        return
    assert importlib.import_module(antigo) is novo
    local: dict = {}
    exec(f"from tab import {antigo.removeprefix('tab.')} as _m", {}, local)
    assert local["_m"] is novo
    local = {}
    exec(f"from {antigo} import __name__ as _n", {}, local)
    assert local["_n"] == novo.__name__


def test_python_m_pelo_nome_antigo_roda_o_main_do_novo():
    resultado = subprocess.run(
        [sys.executable, "-m", "tab.cruzar_fontes", "--help"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "usage" in resultado.stdout.lower()


def _sintaxe_310(arquivo: Path) -> None:
    """Falha se o arquivo não for sintaxe do Python 3.10.

    Args:
        arquivo: o arquivo.
    """
    ast.parse(arquivo.read_text(encoding="utf-8"), feature_version=(3, 10))


def _arquivos_310() -> list[Path]:
    """O que roda fora do Python 3.14: o pacote, os apelidos e o ``caminhos``.

    Returns:
        Os arquivos que precisam ser sintaxe 3.10 e só stdlib.
    """
    return sorted(
        {
            RAIZ / "tab" / "__init__.py",
            RAIZ / "tab" / "_apelidos.py",
            RAIZ / "tab" / "comum" / "caminhos.py",
            *(RAIZ / "tab").rglob("__init__.py"),
        }
    )


@pytest.mark.parametrize(
    "arquivo", _arquivos_310(), ids=lambda p: str(p.relative_to(RAIZ))
)
def test_o_que_imagens_antigas_importam_e_sintaxe_310_e_stdlib(arquivo):
    _sintaxe_310(arquivo)
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom) and no.level == 0:
            nomes = [no.module or ""]
        else:
            continue
        for nome in nomes:
            raiz = nome.split(".")[0]
            assert raiz in sys.stdlib_module_names or raiz == "tab", (arquivo, nome)


def test_init_do_comum_fica_vazio_de_codigo():
    arvore = ast.parse((RAIZ / "tab" / "comum" / "__init__.py").read_text("utf-8"))
    assert all(isinstance(n, ast.Expr) for n in arvore.body)


def test_a_raiz_do_caminhos_e_a_raiz_do_repositorio():
    assert (caminhos.RAIZ / "AGENTS.md").is_file()
    assert caminhos.RAIZ == RAIZ


def test_o_pacote_tab_continua_vindo_deste_repositorio():
    assert Path(tab.__file__).resolve() == RAIZ / "tab" / "__init__.py"
