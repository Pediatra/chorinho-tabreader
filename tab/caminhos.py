"""Caminhos do projeto em um lugar só.

Antes disto havia o caminho do acervo fixo em 3 arquivos (apontando para o HD do
host) e `gold/gabarito.json` em 4 — e dentro do container o acervo vive em
`/acervo`. Também era assim que o modelo acabava em `/tmp`, que é efêmero e não
aparece no bind-mount: modelo treinado em `/tmp` é modelo perdido.

Uso:
    from .caminhos import GABARITO, MODELO_PADRAO, acervo
"""

from __future__ import annotations

import os
from pathlib import Path

# Raiz do projeto: este arquivo vive em <raiz>/tab/caminhos.py
RAIZ = Path(__file__).resolve().parent.parent

_ACERVO_CONTAINER = Path("/acervo")
_ACERVO_HOST = Path("/run/media/gabriel/3014CD4714CD1130/chorinho")

#: Gabarito rotulado à mão (96 glifos, 4 canais).
GABARITO = RAIZ / "data" / "gold" / "gabarito.json"

#: Saídas geradas (visíveis no host, ao contrário de /tmp do container).
SAIDA = RAIZ / "data" / "saida"

#: Pesos treinados. NUNCA em /tmp.
ARTEFATOS = RAIZ / "artefatos"

#: Recortes de amostra do acervo.
PARTES = RAIZ / "parts"

#: Modelo de glifos usado por padrão no ponta a ponta.
MODELO_PADRAO = ARTEFATOS / "glifo_sint.pt"


def acervo() -> Path:
    """Raiz do acervo de vídeos (somente leitura).

    Resolve, nesta ordem: a variável de ambiente ``CHORINHO_ACERVO``, o ponto de
    montagem do container (``/acervo``) e, por último, o caminho do HD no host.

    Returns:
        Caminho da raiz do acervo.
    """
    do_ambiente = os.environ.get("CHORINHO_ACERVO")
    if do_ambiente:
        return Path(do_ambiente)
    if _ACERVO_CONTAINER.is_dir():
        return _ACERVO_CONTAINER
    return _ACERVO_HOST
