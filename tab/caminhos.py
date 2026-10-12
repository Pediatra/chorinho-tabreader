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

#: Ouro de vídeo (telas + instantes), rotulado pelo dono com `tab.ouro_video servir`.
OURO_VIDEO = RAIZ / "data" / "gold" / "ouro_video"

#: Saídas geradas (visíveis no host, ao contrário de /tmp do container).
SAIDA = RAIZ / "data" / "saida"

#: Notas do produto (uma lista ``notas`` com ``t_ini``, ``corda``, ``casa``...).
MVP = SAIDA / "produto" / "mvp.json"

#: Censo de presença das mãos: uma linha por vídeo, com a caixa da tablatura por quadro.
CENSO_MAOS = SAIDA / "maos" / "censo_maos.jsonl"

#: Gabarito dos dedos (M2 da trilha das mãos), rotulado pelo dono com
#: ``tab.maos_gabarito servir``.
GABARITO_DEDOS = RAIZ / "data" / "gold" / "maos" / "dedos_retrato_brasileiro.json"

#: Material por nota da ferramenta dos dedos (quadros e recortes), gerado por
#: ``tab.maos_gabarito_preparar``.
MAOS_DEDOS = SAIDA / "maos" / "m2" / "dedos"

#: Predições e avaliações dos métodos dos dedos (M3): ``tab.maos_regra_dedos`` grava
#: ``pred_<metodo>.json`` e ``tab.maos_avaliar_dedos`` grava ``avaliacao_<metodo>.json``.
MAOS_M3 = SAIDA / "maos" / "m3"

#: Gabarito da geometria do braço (M3b da trilha das mãos: cordas 1 e 6, nut, trastes),
#: rotulado pelo dono com ``tab.maos_braco_gabarito servir``.
GABARITO_BRACO = RAIZ / "data" / "gold" / "maos" / "braco.json"

#: Material da ferramenta do braço (quadros da amostra e ``indice.json``), gerado por
#: ``tab.maos_braco_gabarito preparar``.
MAOS_M3B = SAIDA / "maos" / "m3b"

#: Perfil dos canais (o que foi medido, e quais canais estão fora do rollout).
CANAIS = RAIZ / "configs" / "canais.yaml"

_CACHE_CONTAINER = Path("/cache")


def cache_quadros() -> Path:
    """Raiz do cache de quadros do censo (leitura e escrita), fora do acervo.

    Resolve, nesta ordem: a variável de ambiente ``CHORINHO_CACHE``, o ponto de montagem do
    container (``/cache``, o HD externo ``chorinho_cache``, separado do acervo) e, por último,
    ``data/cache/quadros`` no projeto. O cache é regenerável: nunca vai para o git.

    Returns:
        Caminho da raiz do cache (o diretório pode ainda não existir).
    """
    do_ambiente = os.environ.get("CHORINHO_CACHE")
    if do_ambiente:
        return Path(do_ambiente)
    if _CACHE_CONTAINER.is_dir():
        return _CACHE_CONTAINER
    return RAIZ / "data" / "cache" / "quadros"


#: Pesos treinados. NUNCA em /tmp.
ARTEFATOS = RAIZ / "artefatos"

#: Recortes de amostra do acervo.
PARTES = RAIZ / "parts"

#: Modelo de glifos usado por padrão no ponta a ponta.
# PROCEDÊNCIA MEDIDA (Fase 0 / T0.2). O `glifo_sint.pt` daqui dava **72/72 = 1,000** no próprio
# gabarito que serve de régua — perfeição na régua é sinal de sobreajuste a ela, não de qualidade —
# e ele NÃO está na tabela de procedência do `artefatos/LEIA-ME.md`. Passa a valer a semente
# MEDIANA (oficial_3, 68/72 = 0,944), e não a melhor (oficial_2, 0,986): escolher a melhor pelo
# gabarito de 72 glifos é sobreajustar a régua. Ver docs/decisoes/0008-modelo-do-produto.md.
MODELO_PADRAO = ARTEFATOS / "oficial_3" / "glifo_sint.pt"


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


#: PISO DE TINTA — MEDIDO E **REPROVADO** (não usar; fica como registro). (fração de pixels de tinta na janela).
#:
#: Medido: os 422 **vazios** que o modelo aprovava no pipeline têm tinta mediana **0,071** e
#: **máximo 0,100**; os **523 símbolos verdadeiros** do dono têm mediana **0,174** e p10 **0,128**.
#: Logo existe um vão: o vazio termina onde o símbolo começa.
#:
#:     piso 0,10 -> mata 400 de 422 vazios, custa 25 de 523 símbolos (5%)
#:     piso 0,12 -> mata 422 de 422 vazios, custa 42 de 523 símbolos (8%)   <- escolhido
#:
#: O custo de 8% é provavelmente **arco de baixo contraste** — exatamente o que o dono avisou
#: ("arco de ligadura quase sumindo, cuidado pra não cortar coisa demais"). É um preço REAL e está
#: declarado: troca 8% dos símbolos por acabar com o modo de falha que derrubava a precisão a 0,17.
PISO_TINTA_SIMBOLO = 0.12
