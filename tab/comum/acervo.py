"""O acervo visto por todas as trilhas: a chave de um vídeo e o rollout por canal (9001).

Copiado sem mudança do ``censo`` da tablatura, que reexporta os nomes. Quem usa fora da
tablatura: o áudio (``audio_extrair``) e as mãos (``chave_do_arquivo``, ``canais_fora``).
"""

from __future__ import annotations

import os
from pathlib import Path


def chave_de(rel: str, tamanho: int, mtime: float) -> str:
    """Monta a chave de retomada a partir de seus três campos.

    Args:
        rel: caminho relativo à raiz do acervo.
        tamanho: tamanho do arquivo, em bytes.
        mtime: data de modificação, em segundos (truncada para inteiro).

    Returns:
        Texto ``"relativo|tamanho|mtime"``.
    """
    return f"{rel}|{int(tamanho)}|{int(mtime)}"


def chave_do_arquivo(caminho: str, raiz: str) -> str:
    """Chave de retomada de um vídeo: caminho relativo, tamanho e mtime.

    Args:
        caminho: caminho absoluto do vídeo.
        raiz: raiz do acervo (o caminho da chave é relativo a ela).

    Returns:
        Texto ``"relativo|tamanho|mtime"``.
    """
    st = os.stat(caminho)
    return chave_de(os.path.relpath(caminho, raiz), st.st_size, st.st_mtime)


def ler_rollout(caminho: Path) -> dict[str, str]:
    """Campo ``rollout`` de cada canal de ``configs/canais.yaml``, sem PyYAML.

    O container não tem PyYAML, e o arquivo tem uma forma fixa: ``canais:`` no topo, cada
    canal com dois espaços de recuo e os campos com quatro. Só essas duas coisas são lidas;
    o resto do arquivo (blocos ``>``, comentários) é ignorado. Comentário ``# ...`` sai.

    Args:
        caminho: o ``canais.yaml``.

    Returns:
        Canal -> valor de ``rollout`` (``""`` quando o canal está no yaml sem o campo). Um
        arquivo ausente devolve ``{}``: todo canal é então "novo".
    """
    if not caminho.exists():
        return {}
    achados: dict[str, str] = {}
    dentro_canais = False
    canal: str | None = None
    for bruta in caminho.read_text(encoding="utf-8").splitlines():
        linha = bruta.split(" #")[0].rstrip()
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if not linha.startswith(" "):
            dentro_canais = linha.strip() == "canais:"
            canal = None
            continue
        if not dentro_canais:
            continue
        if linha.startswith("  ") and not linha.startswith("   "):
            if linha.strip().endswith(":"):
                canal = linha.strip()[:-1].strip().strip('"')
                achados[canal] = ""
            else:
                canal = None
        elif canal is not None and linha.startswith("    rollout:"):
            valor = linha.split(":", 1)[1].strip().strip('"')
            achados[canal] = valor
    return achados


def canais_fora(cadastro: dict[str, str]) -> set[str]:
    """Canais marcados ``rollout: fora`` (decisão 0009): não entram no censo padrão.

    Args:
        cadastro: saída de ``ler_rollout``.

    Returns:
        Os nomes de canal com ``rollout`` igual a ``fora``.
    """
    return {canal for canal, valor in cadastro.items() if valor == "fora"}
