"""Testes da rodada 1041 (``tab.maos_braco_retreino_capo3``), sem GPU e sem acervo."""

from __future__ import annotations

import pytest

from tab.maos.braco.retreino_capo3 import (
    criterio_sem_capo,
    criterios_prova,
    escolher_com_piso,
    passa_piso,
    sobreamostrar,
)


def _linha(nome: str, falsos: int, certos: int, sinal: int, soma: int = 2) -> dict:
    """Linha da tabela da escolha.

    Args:
        nome: nome do estágio 1.
        falsos: falsos que passam.
        certos: entregues certos.
        sinal: sinalizados.
        soma: soma das sementes.

    Returns:
        A linha no formato de ``avaliar_combinacao``.
    """
    return {
        "estagio1": nome,
        "estagio2": "A",
        "soma_sementes": soma,
        "falsos_passam_n": falsos,
        "entregue_certo": certos,
        "sinalizados": sinal,
    }


def _grupo(falsos: int, certos: int, medidos: int = 20) -> dict:
    """Totais de um grupo no formato de ``medir_por_grupo``.

    Args:
        falsos: falsos que passam.
        certos: entregues certos.
        medidos: quadros medidos.

    Returns:
        O dicionário de totais.
    """
    return {
        "falsos_passam_n": falsos,
        "falsos_passam": falsos / medidos,
        "entregue_certo": certos,
        "medidos": medidos,
    }


def test_sobreamostrar_repete_so_o_capo():
    registros = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    saida = sobreamostrar(registros, {"b"}, 3)
    assert [r["id"] for r in saida] == ["a", "b", "b", "b", "c"]


def test_sobreamostrar_fator_um_nao_muda_e_zero_recusa():
    registros = [{"id": "a"}, {"id": "b"}]
    assert sobreamostrar(registros, {"a"}, 1) == registros
    with pytest.raises(ValueError):
        sobreamostrar(registros, {"a"}, 0)


def test_piso_barra_o_par_que_sinaliza_tudo():
    # O caso da 1037: 0 falsos com 5 certos venceria o critério da 1029 sem piso.
    referencia = _linha("antigo", 6, 14, 12)
    invertido = _linha("L_s2", 0, 5, 28)
    sao = _linha("L_s1", 2, 13, 16, soma=3)
    assert not passa_piso(invertido, referencia)
    assert passa_piso(sao, referencia)
    assert escolher_com_piso([invertido, sao], referencia)["estagio1"] == "L_s1"


def test_piso_sem_candidato_devolve_none():
    referencia = _linha("antigo", 6, 14, 12)
    assert escolher_com_piso([_linha("L_s2", 0, 5, 28)], referencia) is None


def test_criterio_sem_capo():
    antigo = {"M36": {"sem_capo": _grupo(0, 3)}, "N": {"sem_capo": _grupo(0, 12)}}
    passa = {"M36": {"sem_capo": _grupo(1, 2)}, "N": {"sem_capo": _grupo(0, 11)}}
    falha = {"M36": {"sem_capo": _grupo(0, 1)}, "N": {"sem_capo": _grupo(0, 11)}}
    assert criterio_sem_capo(passa, antigo)["passa"]
    resultado = criterio_sem_capo(falha, antigo)
    assert not resultado["passa"]
    assert resultado["sem_capo_certos_novo_antigo"] == [12, 15]


def test_criterios_prova():
    antigo = {"todos": _grupo(5, 30, 64), "capo": _grupo(4, 6)}
    bom = {"todos": _grupo(3, 40, 64), "capo": _grupo(1, 9)}
    inseguro = {"todos": _grupo(4, 40, 64), "capo": _grupo(1, 9)}
    capo_ruim = {"todos": _grupo(2, 40, 64), "capo": _grupo(2, 9)}
    assert criterios_prova(bom, antigo)["seguranca"]
    assert criterios_prova(bom, antigo)["capo"]
    assert not criterios_prova(inseguro, antigo)["seguranca"]
    assert not criterios_prova(capo_ruim, antigo)["capo"]
