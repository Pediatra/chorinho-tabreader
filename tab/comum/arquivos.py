"""Leitura e gravação de arquivo usadas por mais de uma trilha (decisão 9001).

O código de cada função é o mesmo que existia, copiado sem mudança, nos módulos de origem:
``gravar_atomico`` (``maos_gabarito`` e ``ouro_video``, idênticos), ``ler_json``
(``_ler_json`` de ``maos_braco_ciclo``, ``maos_braco_detector`` e ``maos_padroes_preparar``),
``nfc`` (``_nfc`` de 5 módulos do braço) e ``slug`` (``video._slug``). Os módulos de origem
reexportam o nome antigo.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path


def gravar_atomico(destino: Path, conteudo: dict) -> None:
    """Grava JSON de forma atômica: temporário no mesmo diretório + ``os.replace``.

    Args:
        destino: arquivo final.
        conteudo: dicionário serializável.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, destino)


def ler_json(caminho: Path) -> dict:
    """Lê um JSON em UTF-8.

    Args:
        caminho: arquivo.

    Returns:
        O conteúdo.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def nfc(texto: str) -> str:
    """Nome de arquivo em NFC (kana e acento comparam igual).

    Args:
        texto: nome.

    Returns:
        O nome normalizado.
    """
    return unicodedata.normalize("NFC", texto)


def slug(caminho: str) -> str:
    """Nome de pasta seguro para o vídeo (usado nos recortes de símbolo).

    Args:
        caminho: caminho do vídeo.

    Returns:
        O nome do arquivo sem extensão, com caracteres especiais trocados por ``_``.
    """
    return re.sub(r"[^\w.-]+", "_", Path(caminho).stem).strip("_") or "video"
