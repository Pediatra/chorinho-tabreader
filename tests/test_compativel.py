"""Portão de forma: a classe prevista cabe no recorte medido?

É o que impede o modelo de alucinar classe incompatível com a geometria — foi
esta verificação que levou a última nota do gabarito de 14/15 para 15/15, ao
recusar um algarismo de 2 px (fragmento de barline) classificado como `1`.

A última função documenta uma LACUNA conhecida: classes não numéricas passam sem
nenhuma verificação de forma (ver `docs/HISTORICO.md` e a pendência de símbolos).
"""

from __future__ import annotations

from tab.reconhecer import compativel

PASSO = 20.0


class _Token:
    """Token mínimo: o portão só olha largura e número de partes de algarismo."""

    def __init__(self, largura_px: float, partes_digito: int = 1) -> None:
        self.x0 = 0.0
        self.x1 = float(largura_px)
        self.partes_digito = partes_digito


def test_algarismo_estreito_demais_e_recusado() -> None:
    """Fragmento de barline de 2 px (0,1 passo) não pode virar algarismo."""
    assert compativel("1", _Token(2), PASSO) is False


def test_algarismo_unico_normal_e_aceito() -> None:
    """Um algarismo de meia passada de largura é plausível."""
    assert compativel("7", _Token(10), PASSO) is True


def test_algarismo_unico_largo_demais_e_recusado() -> None:
    """Um único algarismo não ocupa 1,5 passo de largura."""
    assert compativel("1", _Token(30), PASSO) is False


def test_dois_digitos_exigem_dois_componentes() -> None:
    """Um `7` com a barra de slide fundida é largo mas não é `24`."""
    assert compativel("24", _Token(18, partes_digito=2), PASSO) is True
    assert compativel("24", _Token(18, partes_digito=1), PASSO) is False


def test_dois_digitos_estreitos_demais_sao_recusados() -> None:
    """Dois algarismos não cabem em meia passada."""
    assert compativel("24", _Token(10, partes_digito=2), PASSO) is False


def test_classe_nao_numerica_nao_tem_portao_de_forma() -> None:
    """LACUNA conhecida: `harmonico` e `tecnica` passam sem checagem de forma.

    Este teste documenta o comportamento atual de propósito. Quando o portão de
    forma cobrir símbolos (harmônico exige >= 2 partes, por exemplo), este teste
    deve ser invertido — e não apenas apagado.
    """
    assert compativel("harmonico", _Token(2), PASSO) is True
