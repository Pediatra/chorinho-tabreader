"""Cache de quadros do censo (T-cache): cada vídeo é lido UMA vez e os quadros ficam em disco.

O censo (``tab.censo``) usa, por vídeo, 12 quadros de presença (quadro inteiro, nativo) e, em até
3 instantes com tablatura, uma janela de 10 s a 3 quadros/s, da qual só o recorte do painel é
medido. Ler isso do acervo (HD externo, AV1 com seek) é o custo do censo. Com o cache, um conserto
no classificador se reprocessa do disco local, sem reabrir o vídeo.

Layout (um diretório por vídeo e formato)::

    <CHORINHO_CACHE ou /cache>/<formato>/<hash da chave>/
        meta.json                   chave, caminho, info, quadros sem leitura
        presenca_00.png ... _11     quadro inteiro, nativo, nos 12 instantes
        janela_<t0*100>_<x0-y0-x1-y1>/
            meta.json               t0, t1, rect, quadros
            000.png, 001.png ...    recorte do painel, a 3 qps

A chave de retomada é ``relativo|tamanho|mtime`` (como no censo): um vídeo que muda ganha
diretório novo, e o antigo fica órfão (não é apagado sozinho).

Formato: ``png`` é SEM perda (o padrão). ``webp`` também é sem perda e existe só para comparação.
Formato com perda (JPEG) fica fora: mudaria a saída do censo (regra 9 do AGENTS.md).

Por que o recorte da janela e não o quadro inteiro: a janela só é medida dentro do painel, e o
painel sai da presença. Guardar o quadro inteiro dos 90 quadros de janela custaria ~16 MB por
janela (ver o relatório T-cache). O recorte é exatamente o que ``tab.censo`` mede, pixel a pixel.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .caminhos import cache_quadros

#: Formato -> (extensão, parâmetros do ``cv2.imencode``). Os dois são SEM perda.
#: PNG é o de produção: medido, codifica ~19x mais rápido que WebP sem perda (0,034 s contra
#: 0,64 s por quadro de presença) e a diferença de tamanho não importa no HD externo.
FORMATOS: dict[str, tuple[str, list[int]]] = {
    "png": (".png", []),
    "webp": (".webp", [cv2.IMWRITE_WEBP_QUALITY, 101]),
}

#: Formato de produção (sem perda).
FORMATO_PADRAO = "png"


class FaltaNoCache(RuntimeError):
    """O censo pediu um quadro que não está no cache, e o modo é só-cache (falha alta)."""


@dataclass(frozen=True)
class ModoCache:
    """Como o censo usa o cache.

    Attributes:
        usar: lê do cache quando há, e grava o que falta (``--cache``).
        so_cache: nunca abre o vídeo; falta de quadro vira ``FaltaNoCache`` (``--so-cache``).
        formato: uma das chaves de ``FORMATOS``.
        raiz: diretório raiz do cache (``caminhos.cache_quadros()``).
    """

    usar: bool = False
    so_cache: bool = False
    formato: str = FORMATO_PADRAO
    raiz: Path = field(default_factory=cache_quadros)

    def __post_init__(self) -> None:
        """Recusa formato desconhecido logo na criação."""
        if self.formato not in FORMATOS:
            raise ValueError(f"formato de cache desconhecido: {self.formato}")

    @property
    def ligado(self) -> bool:
        """Se o censo deve passar pelo cache (``--cache`` ou ``--so-cache``).

        Returns:
            True quando há leitura ou gravação de cache.
        """
        return self.usar or self.so_cache


def pasta_do_video(chave: str, modo: ModoCache) -> Path:
    """Diretório do cache de um vídeo, para o formato de ``modo``.

    Args:
        chave: chave de retomada do vídeo (``relativo|tamanho|mtime``).
        modo: formato e raiz do cache.

    Returns:
        ``<raiz>/<formato>/<hash>``; o diretório pode ainda não existir.
    """
    digest = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]
    return modo.raiz / modo.formato / digest


def pasta_da_janela(pasta: Path, t0: float, rect: tuple[int, ...] | list[int]) -> Path:
    """Diretório de uma janela dentro do cache do vídeo.

    A janela é identificada pelo instante inicial (centésimos de segundo) e pela caixa do
    painel: se um conserto mudar o painel, a janela nova não existe no cache e o ``--so-cache``
    falha alto em vez de medir recorte velho.

    Args:
        pasta: diretório do cache do vídeo.
        t0: instante inicial da janela, em segundos.
        rect: caixa do painel ``(x0, y0, x1, y1)``.

    Returns:
        O diretório da janela.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    return pasta / f"janela_{round(t0 * 100)}_{x0}-{y0}-{x1}-{y1}"


def caminho_do_quadro(pasta: Path, nome: str, formato: str) -> Path:
    """Caminho de um quadro gravado: ``<pasta>/<nome><extensão do formato>``.

    Args:
        pasta: diretório onde o quadro fica.
        nome: nome sem extensão (ex.: ``presenca_03``).
        formato: uma das chaves de ``FORMATOS``.

    Returns:
        O caminho do arquivo.
    """
    return pasta / f"{nome}{FORMATOS[formato][0]}"


def gravar_quadro(caminho: Path, quadro: np.ndarray, formato: str) -> None:
    """Grava um quadro BGR no formato dado, de forma atômica (arquivo temporário e troca).

    Args:
        caminho: arquivo de destino.
        quadro: quadro BGR (``uint8``).
        formato: uma das chaves de ``FORMATOS``.

    Raises:
        OSError: se o OpenCV não conseguir codificar o quadro.
    """
    extensao, parametros = FORMATOS[formato]
    ok, buf = cv2.imencode(extensao, quadro, parametros)
    if not ok:
        raise OSError(f"cv2 não codificou o quadro para {caminho}")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_bytes(buf.tobytes())
    os.replace(temporario, caminho)


def ler_quadro(caminho: Path) -> np.ndarray:
    """Lê um quadro do cache.

    Args:
        caminho: arquivo gravado por ``gravar_quadro``.

    Returns:
        O quadro BGR.

    Raises:
        OSError: se o arquivo não decodificar (cache corrompido: refazer, não ignorar).
    """
    quadro = cv2.imdecode(np.fromfile(caminho, np.uint8), cv2.IMREAD_COLOR)
    if quadro is None:
        raise OSError(f"quadro corrompido no cache: {caminho}")
    return quadro


def gravar_meta(pasta: Path, meta: dict) -> None:
    """Grava o ``meta.json`` de um diretório do cache, de forma atômica.

    Args:
        pasta: diretório do cache (do vídeo ou de uma janela).
        meta: dados em JSON.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    temporario = pasta / "meta.json.tmp"
    temporario.write_text(
        json.dumps(meta, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    os.replace(temporario, pasta / "meta.json")


def ler_meta(pasta: Path) -> dict | None:
    """Lê o ``meta.json`` de um diretório do cache.

    Args:
        pasta: diretório do cache.

    Returns:
        O dicionário, ou ``None`` se o diretório não tem meta (ainda não foi concluído).
    """
    arquivo = pasta / "meta.json"
    if not arquivo.exists():
        return None
    return json.loads(arquivo.read_text(encoding="utf-8"))
