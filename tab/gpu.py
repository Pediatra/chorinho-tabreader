"""Trava da GPU compartilhada entre as trilhas (protocolo ``data/saida/gpu.lock``).

O protocolo do projeto (``docs/guias/contexto-*.md``): antes de usar a GPU, a trilha cria
``data/saida/gpu.lock`` com "trilha, início, estimativa"; se o arquivo existe e é de outra
trilha, espera ele sumir. Este módulo faz o protocolo pelo código:

- a trilha dona segura ``gpu.lock.<trilha>`` (``flock``) enquanto usa a GPU. Dois processos
  da mesma trilha entram um de cada vez;
- a criação do ``gpu.lock`` é atômica (``O_EXCL``), sob a trava curta ``gpu.lock.trava``;
- um ``gpu.lock`` de trilha cujo ``gpu.lock.<trilha>`` existe e está livre é sobra de
  processo morto, e é retomado. Trilha que cria o ``gpu.lock`` à mão (sem esse arquivo) é
  respeitada: espera-se o arquivo sumir;
- com o ``gpu.lock`` na mão, confere ≥ 3 GB livres, porque alguém pode usar a GPU sem o
  protocolo;
- **a GPU se divide pela memória** (dono, 2026-10-21): com a checagem de memória ligada, a
  trilha que acha o ``gpu.lock`` de outra trilha viva não espera ela soltar. Entra quando
  houver ≥ 3 GB livres, sem gravar o ``gpu.lock`` (ele continua da trilha que o pegou). Com
  ``checar_memoria=False`` a trava segue exclusiva, porque sem medir a memória não há como
  saber se cabe.

Uso: ``with trava_gpu("audio", "40 min"): ...``. O ``flock`` vale entre containers, porque
``data/saida`` é o mesmo diretório do host em todos.
"""

from __future__ import annotations

import datetime
import fcntl
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import torch

from .caminhos import TRAVA_GPU

#: Memória livre mínima na GPU antes de começar, e espera entre tentativas.
MEMORIA_LIVRE_MINIMA = 3 * 2**30
ESPERA_GPU_S = 60.0


def arquivo_da_trilha(arquivo: Path, trilha: str) -> Path:
    """Arquivo que a trilha segura com ``flock`` enquanto usa a GPU.

    Args:
        arquivo: o ``gpu.lock``.
        trilha: nome da trilha (``maos``, ``audio``...).

    Returns:
        ``gpu.lock.<trilha>``, ao lado do ``gpu.lock``.
    """
    return arquivo.with_name(f"{arquivo.name}.{trilha}")


def dono_da_trava(arquivo: Path) -> str | None:
    """Trilha escrita no ``gpu.lock`` (o primeiro campo, antes da vírgula).

    Args:
        arquivo: o ``gpu.lock``.

    Returns:
        O nome da trilha, ``""`` se o arquivo existe sem conteúdo, ou None se não existe.
    """
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return texto.split(",", 1)[0].strip()


def trilha_viva(arquivo: Path, trilha: str) -> bool:
    """Se algum processo da trilha segura o ``gpu.lock.<trilha>``.

    Sem esse arquivo (trilha que segue o protocolo à mão), a trilha conta como viva.

    Args:
        arquivo: o ``gpu.lock``.
        trilha: trilha dona do ``gpu.lock``.

    Returns:
        False só quando o arquivo da trilha existe e o ``flock`` dele está livre.
    """
    caminho = arquivo_da_trilha(arquivo, trilha)
    if not trilha or not caminho.exists():
        return True
    with caminho.open("a") as aberto:
        try:
            fcntl.flock(aberto, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(aberto, fcntl.LOCK_UN)
    return False


def _tentar_pegar(arquivo: Path, trilha: str, conteudo: str) -> str | None:
    """Uma tentativa de pegar o ``gpu.lock``, sob a trava curta.

    Args:
        arquivo: o ``gpu.lock``.
        trilha: trilha que pede (já segura o ``gpu.lock.<trilha>``).
        conteudo: texto a gravar ("trilha, início, estimativa").

    Returns:
        None se pegou; senão, a trilha dona atual.
    """
    with arquivo.with_name(f"{arquivo.name}.trava").open("a") as curta:
        fcntl.flock(curta, fcntl.LOCK_EX)
        try:
            fd = os.open(arquivo, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            dono = dono_da_trava(arquivo)
            if dono is None or dono == trilha or not trilha_viva(arquivo, dono):
                # Sobra de processo morto (da própria trilha, ou de outra com o
                # flock livre): retoma.
                temporario = arquivo.with_name(f"{arquivo.name}.{trilha}.novo")
                temporario.write_text(conteudo, encoding="utf-8")
                os.replace(temporario, arquivo)
                return None
            return dono
        with os.fdopen(fd, "w", encoding="utf-8") as novo:
            novo.write(conteudo)
        return None


def _soltar(arquivo: Path, conteudo: str) -> None:
    """Apaga o ``gpu.lock`` se ele ainda é o que este processo gravou.

    Args:
        arquivo: o ``gpu.lock``.
        conteudo: o texto gravado ao pegar.
    """
    with arquivo.with_name(f"{arquivo.name}.trava").open("a") as curta:
        fcntl.flock(curta, fcntl.LOCK_EX)
        try:
            if arquivo.read_text(encoding="utf-8") == conteudo:
                arquivo.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def trava_gpu(
    trilha: str,
    estimativa: str = "?",
    checar_memoria: bool = True,
    arquivo: Path = TRAVA_GPU,
    espera_s: float = ESPERA_GPU_S,
) -> Iterator[None]:
    """Reserva a GPU para a trilha pelo protocolo do ``gpu.lock``.

    Args:
        trilha: nome da trilha (``maos``, ``audio``...), sem vírgula.
        estimativa: duração prevista, para quem ler o arquivo (ex.: ``"40 min"``).
        checar_memoria: se True, espera ≥ ``MEMORIA_LIVRE_MINIMA`` livres na GPU.
        arquivo: o ``gpu.lock`` (padrão ``data/saida/gpu.lock``).
        espera_s: espera entre tentativas, em segundos.

    Yields:
        Nada; o bloco roda com a GPU reservada.

    Raises:
        ValueError: se a trilha for vazia ou tiver vírgula.
    """
    if not trilha or "," in trilha:
        raise ValueError(f"nome de trilha inválido: {trilha!r}")
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo_da_trilha(arquivo, trilha).open("a") as propria:
        fcntl.flock(propria, fcntl.LOCK_EX)
        inicio = datetime.datetime.now().isoformat(timespec="seconds")
        conteudo = f"{trilha}, {inicio}, {estimativa}\n"
        dono_anterior = None
        pegou = True
        while (dono := _tentar_pegar(arquivo, trilha, conteudo)) is not None:
            if checar_memoria:
                print(
                    f"GPU com a trava da trilha {dono!r}; divido pela memória livre",
                    file=sys.stderr,
                )
                pegou = False
                break
            if dono != dono_anterior:
                print(
                    f"GPU com a trava da trilha {dono!r}; espero (a cada {espera_s:.0f} s)",
                    file=sys.stderr,
                )
                dono_anterior = dono
            time.sleep(espera_s)
        try:
            while checar_memoria:
                livre, _ = torch.cuda.mem_get_info()
                if livre >= MEMORIA_LIVRE_MINIMA:
                    break
                print(
                    f"GPU com {livre / 2**30:.1f} GB livres; espero {espera_s:.0f} s",
                    file=sys.stderr,
                )
                time.sleep(espera_s)
            yield
        finally:
            if pegou:
                _soltar(arquivo, conteudo)
            fcntl.flock(propria, fcntl.LOCK_UN)
