"""Testes da trava da GPU compartilhada (``tab.gpu``). Sem GPU: a memória não é checada."""

from __future__ import annotations

import fcntl
import threading
import time

import pytest

from tab import gpu
from tab.gpu import arquivo_da_trilha, dono_da_trava, trava_gpu, trilha_viva


def _entrar_em_thread(arquivo, trilha: str) -> tuple[threading.Thread, threading.Event]:
    """Roda ``trava_gpu`` numa thread e marca o evento quando entra no bloco.

    Args:
        arquivo: o ``gpu.lock`` do teste.
        trilha: trilha que pede.

    Returns:
        A thread (já iniciada) e o evento de entrada.
    """
    entrou = threading.Event()

    def alvo() -> None:
        """Pede a trava, marca a entrada e sai."""
        with trava_gpu(trilha, checar_memoria=False, arquivo=arquivo, espera_s=0.02):
            entrou.set()

    fio = threading.Thread(target=alvo)
    fio.start()
    return fio, entrou


def test_pega_grava_e_solta(tmp_path):
    arquivo = tmp_path / "gpu.lock"
    with trava_gpu("audio", "40 min", checar_memoria=False, arquivo=arquivo):
        texto = arquivo.read_text(encoding="utf-8")
        assert texto.startswith("audio, ")
        assert texto.rstrip().endswith(", 40 min")
        assert dono_da_trava(arquivo) == "audio"
    assert not arquivo.exists()


def test_retoma_sobra_da_propria_trilha(tmp_path):
    arquivo = tmp_path / "gpu.lock"
    arquivo.write_text("maos, 2026-10-20T01:00:00, 6 h\n", encoding="utf-8")
    with trava_gpu("maos", checar_memoria=False, arquivo=arquivo, espera_s=0.01):
        assert "2026-10-20T01:00:00" not in arquivo.read_text(encoding="utf-8")
    assert not arquivo.exists()


def test_retoma_sobra_de_outra_trilha_com_flock_livre(tmp_path):
    arquivo = tmp_path / "gpu.lock"
    arquivo.write_text("audio, 2026-10-20T01:00:00, 1 h\n", encoding="utf-8")
    arquivo_da_trilha(arquivo, "audio").touch()
    assert not trilha_viva(arquivo, "audio")
    with trava_gpu("maos", checar_memoria=False, arquivo=arquivo, espera_s=0.01):
        assert dono_da_trava(arquivo) == "maos"


def test_espera_trilha_viva_e_entra_quando_ela_solta(tmp_path):
    arquivo = tmp_path / "gpu.lock"
    arquivo.write_text("audio, 2026-10-20T01:00:00, 1 h\n", encoding="utf-8")
    with arquivo_da_trilha(arquivo, "audio").open("a") as segurado:
        fcntl.flock(segurado, fcntl.LOCK_EX)
        assert trilha_viva(arquivo, "audio")
        fio, entrou = _entrar_em_thread(arquivo, "maos")
        time.sleep(0.2)
        assert not entrou.is_set()
        fcntl.flock(segurado, fcntl.LOCK_UN)
    fio.join(timeout=5)
    assert entrou.is_set()


def test_respeita_trava_feita_a_mao(tmp_path):
    arquivo = tmp_path / "gpu.lock"
    arquivo.write_text("partitura, 2026-10-20T01:00:00, 2 h\n", encoding="utf-8")
    fio, entrou = _entrar_em_thread(arquivo, "audio")
    time.sleep(0.2)
    assert not entrou.is_set()
    arquivo.unlink()
    fio.join(timeout=5)
    assert entrou.is_set()


def test_nao_apaga_trava_que_outro_gravou(tmp_path):
    arquivo = tmp_path / "gpu.lock"
    with trava_gpu("maos", checar_memoria=False, arquivo=arquivo):
        arquivo.write_text("partitura, agora, 1 h\n", encoding="utf-8")
    assert dono_da_trava(arquivo) == "partitura"


def test_trilha_com_virgula_recusa(tmp_path):
    with (
        pytest.raises(ValueError),
        trava_gpu("a,b", checar_memoria=False, arquivo=tmp_path / "gpu.lock"),
    ):
        pass


def test_divide_pela_memoria_sem_tocar_a_trava_da_outra(tmp_path, monkeypatch):
    arquivo = tmp_path / "gpu.lock"
    arquivo.write_text("tablatura, 2026-10-21T09:00:00, treino\n", encoding="utf-8")
    monkeypatch.setattr(gpu.torch.cuda, "mem_get_info", lambda: (5 * 2**30, 8 * 2**30))
    with arquivo_da_trilha(arquivo, "tablatura").open("a") as segurado:
        fcntl.flock(segurado, fcntl.LOCK_EX)
        with trava_gpu("maos", arquivo=arquivo, espera_s=0.01):
            assert dono_da_trava(arquivo) == "tablatura"
        assert dono_da_trava(arquivo) == "tablatura"


def test_dividindo_espera_memoria_livre(tmp_path, monkeypatch):
    arquivo = tmp_path / "gpu.lock"
    arquivo.write_text("tablatura, 2026-10-21T09:00:00, treino\n", encoding="utf-8")
    livres = iter([1 * 2**30, 2 * 2**30, 4 * 2**30])
    chamadas = []

    def memoria() -> tuple[int, int]:
        """Memória livre que sobe a cada consulta."""
        chamadas.append(1)
        return next(livres), 8 * 2**30

    monkeypatch.setattr(gpu.torch.cuda, "mem_get_info", memoria)
    with trava_gpu("maos", arquivo=arquivo, espera_s=0.01):
        assert len(chamadas) == 3
