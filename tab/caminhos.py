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


#: Limiar do detector POSITIVO de símbolo ("isto é símbolo?"). O treino usou 0,5 e o falso
#: positivo medido é 0,2–0,4 % (2 a 4 de 1076) — subir o limiar só trocaria símbolo perdido por
#: nada ganho. Fica aqui (e não em `tab.simbolo`) porque `reconhecer` e `simbolo` precisam dela e
#: `simbolo` importa `digito`, que importa `reconhecer`: pôr em `simbolo` fecharia o ciclo.
LIMIAR_SIMBOLO = 0.5


#: Largura/altura mínima para um token poder ser símbolo. Instrução do dono do projeto sobre o
#: `shin izumi`: *"essas barras que estão embaixo dos números na vertical não significam nada de
#: importante, pode fazer o leitor desconsiderar"*. Medido: as barras que o detector aprovava lá
#: têm razão mediana **0,118** (100 barras em 3 quadros) e os **123 símbolos verdadeiros** dele têm
#: mediana **1,706** — **0 de 123** abaixo de 0,35. Regra determinística com zero colateral:
#: símbolo de tablatura é LARGO (arco, seta, ligadura); barra vertical é lixo de render.
RAZAO_MINIMA_SIMBOLO = 0.35
