"""Partitura (pauta de 5 linhas) de todas as telas de um vídeo, a partir do produto.

Cadeia da trilha "partitura" aplicada ao JSON de produto da tablatura (esquema
``chorinho/video@1``): para cada tela ``paginado``, acha a pauta logo acima da tablatura
e grava o recorte. As etapas são:

1. ``recortar`` (este módulo): lê o quadro no instante da tela, acha as pautas com
   ``tab.partitura_recortes`` e grava o recorte da pauta mais próxima de cima da tab;
2. ``ler`` (este módulo): roda os dois leitores de partitura, Audiveris e homr, em cada
   recorte com pauta, um após o outro, e aplica a armadura do vídeo às leituras sem
   clave. Os leitores ficam na imagem ``chorinho-partitura:dev`` (ver o uso abaixo);
3. ``parear`` (este módulo): casa as notas lidas com as notas do produto, agrupadas por
   ``coluna``, e grava o documento ``chorinho/partitura@1`` do produto.

O tempo não é medido aqui. Ele vem do ``t_ini`` do produto, pela chave (tela, coluna),
como decide ``docs/decisoes/3002-partitura-no-produto.md``. Por isso cada recorte leva o
instante do ponto médio da primeira exibição válida da tela.

Saída de ``recortar``, por produto, em ``PASTA_VIDEO / <stem>/recortes/``: ``T{id}.png``
por tela com pauta, ``indice.json`` (uma entrada por tela, com ou sem pauta) e
``contexto_NN.jpg``.

Saída de ``ler``, na pasta ``PASTA_VIDEO / <stem>/omr/``: ``audiveris/x2_margem/`` e
``homr/nativo/``, cada uma com uma pasta por recorte e ``execucao.json``; e
``audiveris/x2_margem_herdada/``, com a armadura do vídeo aplicada e ``herdada.json``.

Saída de ``parear``, em ``PASTA_VIDEO / <stem>/``: ``<stem>.partitura.json``, com uma
pauta por recorte com pauta. Cada pauta traz ``fifths`` (armadura lida na leitura
herdada, em sustenidos + ou bemóis −), ``fifths_origem`` (``video`` se a armadura do vídeo
foi aplicada, ``leitura`` se não), ``compassos`` (número, fórmula e x de cada compasso),
e os eventos. Cada evento tem o par na tab (ou None) com ``metodo``: ``altura`` quando o
pareamento por sequência de alturas vale, ``x`` quando a posição no quadro trocou o par
(``reparear_por_x``).

Etapa ``paginar``, para vídeos **sem** produto de tablatura: varre o vídeo inteiro a
``QPS_PAGINAS``, reduz cada quadro a uma assinatura binária da região das pautas
(``assinatura``) e agrupa os quadros estáveis em páginas (``agrupar_paginas``). Uma página
é um trecho que fica parado e volta a aparecer nas repetições. Para cada página, lê o
quadro no ponto médio da exibição mais longa, descarta as pautas que são tablatura
(``e_tablatura``: 6 linhas em vez de 5) e recorta as demais. Saída, em
``PASTA_SEM_PRODUTO / <slug>/recortes/``: ``P{pagina}{letra}.png`` por pauta (``P01a``,
``P01b``...), ``contexto_PNN.jpg`` por página e ``indice.json``. Não grava produto nem as outras pastas.

Uso:
    python -m tab.partitura_video recortar --produto CAMINHO [--produto CAMINHO ...]
    python -m tab.partitura_video ler --produto CAMINHO [--produto CAMINHO ...] [--ids T01,T02]
    python -m tab.partitura_video parear --produto CAMINHO [--produto CAMINHO ...]
    python -m tab.partitura_video paginar --video CAMINHO [--video CAMINHO ...] [--pasta PASTA]

A etapa ``ler`` roda dentro da imagem ``chorinho-partitura:dev``, em CPU, com
``--security-opt label=disable`` (obrigatório no host deste projeto):
    podman run --rm --security-opt label=disable -v $PWD:/app -w /app \
        -e PYTHONPATH=/app chorinho-partitura:dev \
        python -m tab.partitura_video ler --produto CAMINHO
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import RAIZ, SAIDA, acervo
from tab.leitor import info, quadro_em, quadros
from tab.musicxml import midi_da_corda
from tab.partitura_avaliar import SEMITONS_ESCRITA
from tab.partitura_gabarito import ler_partitura
from tab.partitura_omr import _gravar_execucao, herdar_condicao, rodar_um
from tab.partitura_pareamento import (
    EventoPartitura,
    EventoTab,
    _t_inis,
    completar_com_homr,
    eventos_da_partitura,
    parear,
    x_dos_compassos,
)
from tab.partitura_pauta import Pauta, achar_pautas
from tab.partitura_recortes import (
    CRISTA_DELTA_EXT,
    Celula,
    FonteQuadro,
    Recorte,
    _cinza,
    _tinta_escura,
    canal_ascii,
    folha_contexto,
    ler_fonte,
    processar_quadro,
)
from tab.video import _slug

#: Pasta de saída da etapa de recorte, uma subpasta por produto.
PASTA_VIDEO = SAIDA / "partitura" / "video"

#: Pasta da etapa ``paginar`` (vídeo sem produto). Fica separada de ``PASTA_VIDEO`` para
#: o slug de um vídeo nunca cair na pasta de um produto e apagar os recortes dele.
PASTA_SEM_PRODUTO = SAIDA / "partitura" / "sem_produto"

#: Margem (em entrelinhas) acima e abaixo da pauta no recorte (condição x2_margem, 3003).
MARGEM_ENTRELINHAS = 7.0

#: Altura das 6 cordas da tablatura, em passos (5 intervalos entre cordas).
ALTURA_DA_TAB_PASSOS = 5

#: Condição de entrada do Audiveris na etapa ``ler`` (PNG ampliado 2x, margem 7).
CONDICAO_AUDIVERIS = "x2_margem"

#: Condição de entrada do homr na etapa ``ler`` (PNG do recorte, sem alteração).
CONDICAO_HOMR = "nativo"

#: Esquema do documento gravado por ``parear``.
ESQUEMA_PARTITURA = "chorinho/partitura@1"

#: Fator da imagem ampliada (condição ``x2``) em relação ao quadro, para o x do ``.omr``.
ESCALA_X2 = 2.0

#: Quadros por segundo da varredura de páginas (``paginar``). Um quadro por segundo basta:
#: a tela fica parada por vários segundos entre uma página e a seguinte.
QPS_PAGINAS = 1.0

#: Distância máxima entre duas assinaturas para serem a mesma página, como fração dos
#: pixels que diferem (``diferenca``). Uma sequência que sai desse limiar começa outra.
LIMIAR_PAGINA = 0.25

#: Amostras mínimas de uma sequência estável para contar como exibição de página. Corta
#: viradas, fades e quadros isolados.
MINIMO_AMOSTRAS = 2

#: Largura, em px, da assinatura da região das pautas.
LARGURA_ASSINATURA = 256

#: Altura, em px, da assinatura da região das pautas.
ALTURA_ASSINATURA = 64

#: Contraste mínimo, em V (escala do OpenCV, 0 a 255), entre o traço e o fundo local para
#: o pixel ser tinta. O fundo local vem de um top-hat com elemento de lado ~1 entrelinha.
#: Compressão do vídeo tinge o traço preto de cor e destaque amarelo ou rosa dá saturação
#: alta; medir só a saturação deixava linhas e notas de fora, por isso se usa o contraste.
DELTA_TINTA = 60

#: Fração de um bloco da assinatura que precisa ser tinta para o bloco contar como tinta
#: (a assinatura é a média da máscara de tinta em cada bloco, depois limiarizada).
FRACAO_TINTA = 0.25

#: Número de trechos em que a largura da pauta é dividida para medir a força de uma linha
#: (``_forca_por_trechos``). Viga de semicolcheia cobre só alguns trechos; a linha, todos.
TRECHOS_TABLATURA = 10

#: Razão mínima entre a força da 6ª linha (fora da pauta) e a mediana das 5 linhas para o
#: trecho ser tablatura (``e_tablatura``).
LIMIAR_TABLATURA = 0.75

#: Tolerância, em px, da posição da 6ª linha em torno de ``ys[4] + entrelinha`` (ou
#: ``ys[0] - entrelinha``).
TOLERANCIA_SEXTA_LINHA = 2

#: Folga (em entrelinhas) acima da 1ª linha e abaixo da 5ª da última pauta na assinatura.
MARGEM_ASSINATURA_ENTRELINHAS = 4.0


def instante_da_tela(tela: dict) -> float | None:
    """Instante médio da primeira exibição válida de uma tela.

    Uma exibição é válida quando ``t1 > t0``. Exibições com ``t1 <= t0`` são puladas.

    Args:
        tela: uma tela do produto, com a lista ``exibicoes`` (cada uma com ``t0`` e ``t1``).

    Returns:
        O ponto médio ``(t0 + t1) / 2`` da primeira exibição válida, em segundos, ou
        ``None`` se a tela não tem exibição válida.
    """
    for exibicao in tela.get("exibicoes", []):
        t0 = float(exibicao["t0"])
        t1 = float(exibicao["t1"])
        if t1 > t0:
            return (t0 + t1) / 2
    return None


def pauta_acima_da_tab(
    entradas: list[dict], painel: list[int], passo: float
) -> dict | None:
    """Escolhe, entre as pautas achadas, a mais próxima de cima da tablatura.

    O topo do painel não serve de limite: em telas com cartão branco (Gymnopédie, tela
    12), o painel do produto começa acima da pauta. O limite é a base do painel menos a
    altura das 6 cordas (``ALTURA_DA_TAB_PASSOS`` passos). São candidatas as entradas com
    ``sem_pauta`` falso e ``ys[4]`` acima desse limite; vence a de maior ``ys[4]``.

    Args:
        entradas: entradas do índice de um quadro (``processar_quadro``).
        painel: caixa ``[x0, y0, x1, y1]`` da tablatura no quadro.
        passo: distância entre cordas da tab, em px (``passo`` da tela do produto).

    Returns:
        A entrada escolhida, ou ``None`` se nenhuma pauta está acima da tablatura.
    """
    limite = painel[3] - ALTURA_DA_TAB_PASSOS * passo
    candidatas = [
        entrada
        for entrada in entradas
        if not entrada["sem_pauta"] and entrada["ys"][4] < limite
    ]
    if not candidatas:
        return None
    return max(candidatas, key=lambda entrada: entrada["ys"][4])


def pasta_do_produto(produto: Path) -> Path:
    """Pasta de saída de um produto: ``PASTA_VIDEO / <nome sem extensão>``.

    Args:
        produto: caminho do JSON de produto.

    Returns:
        A pasta onde os recortes do produto são gravados.
    """
    return PASTA_VIDEO / produto.stem


def pasta_omr(produto: Path) -> Path:
    """Pasta das leituras de partitura de um produto: ``pasta_do_produto / omr``.

    Args:
        produto: caminho do JSON de produto.

    Returns:
        A pasta com uma subpasta por biblioteca e condição (e a armadura herdada).
    """
    return pasta_do_produto(produto) / "omr"


def _limpar_recortes(pasta_recortes: Path) -> None:
    """Apaga os arquivos de uma execução anterior de ``recortar``.

    Remove apenas ``T*.png``, ``contexto_*.jpg`` e ``indice.json``. Outros arquivos da
    pasta ficam intactos.

    Args:
        pasta_recortes: pasta ``recortes/`` do produto (criada se faltar).
    """
    pasta_recortes.mkdir(parents=True, exist_ok=True)
    for padrao in ("T*.png", "contexto_*.jpg", "indice.json"):
        for arquivo in pasta_recortes.glob(padrao):
            arquivo.unlink()


def recortar(produto: Path) -> list[dict]:
    """Recorta a pauta de cada tela de um produto e grava o índice.

    Para cada tela, em ordem: se o modo não é ``paginado`` ou a tela não tem exibição
    válida, a entrada é marcada como ``sem_pauta``. Caso contrário, lê o quadro no
    instante médio da tela, acha as pautas e escolhe a que está mais perto de cima da
    tablatura. Se achou, grava o recorte como ``recortes/T{id:02d}.png``.

    Ao fim, grava as folhas ``contexto_NN.jpg`` e ``indice.json`` na pasta
    ``recortes/`` do produto, apagando antes as versões anteriores.

    Args:
        produto: caminho do JSON de produto (somente leitura).

    Returns:
        A lista de entradas do índice, uma por tela, na ordem das telas.
    """
    dados = json.loads(produto.read_text(encoding="utf-8"))
    arquivo = dados["video"]["arquivo"]
    canal = Path(arquivo).parts[0]
    pasta_recortes = pasta_do_produto(produto) / "recortes"
    _limpar_recortes(pasta_recortes)

    indice: list[dict] = []
    celulas = []
    for tela in dados["telas"]:
        id_tela = int(tela["id"])
        modo = tela.get("modo")
        instante = instante_da_tela(tela)
        if modo != "paginado":
            indice.append(
                {"tela": id_tela, "sem_pauta": True, "motivo": f"modo {modo}"}
            )
            continue
        if instante is None:
            indice.append(
                {"tela": id_tela, "sem_pauta": True, "motivo": "sem exibição"}
            )
            continue

        painel = [int(v) for v in tela["painel"]]
        # O painel só escolhe a pauta; não limita o recorte. O topo do painel fica acima
        # da 1ª corda, e cortar meia entrelinha antes dele perde as linhas suplementares
        # de baixo (A3 do R11). O limite vem das linhas achadas no quadro, como na P1.
        fonte = FonteQuadro(
            origem="produto",
            canal=canal,
            video=arquivo,
            t=instante,
            tela=id_tela,
        )
        quadro, fonte_quadro = ler_fonte(fonte)
        entradas, recortes, celula = processar_quadro(
            fonte,
            quadro,
            fonte_quadro,
            primeiro_numero=1,
            margem_cima=MARGEM_ENTRELINHAS,
            margem_baixo=MARGEM_ENTRELINHAS,
        )
        celulas.append(celula)
        escolhida = pauta_acima_da_tab(entradas, painel, float(tela["passo"]))
        if escolhida is None:
            indice.append(
                {
                    "tela": id_tela,
                    "sem_pauta": True,
                    "motivo": "sem pauta acima da tab",
                    "t": instante,
                }
            )
            continue

        recorte = next(r for r in recortes if r.id == escolhida["id"])
        identificador = f"T{id_tela:02d}"
        cv2.imwrite(str(pasta_recortes / f"{identificador}.png"), recorte.imagem)
        indice.append(
            {
                "id": identificador,
                "tela": id_tela,
                "video": arquivo,
                "t": instante,
                "painel": painel,
                "sem_pauta": False,
                "ys": escolhida["ys"],
                "entrelinha": escolhida["entrelinha"],
                "caixa_recorte": escolhida["caixa_recorte"],
                "largura": escolhida["largura"],
                "altura": escolhida["altura"],
            }
        )

    if celulas:
        folha_contexto(celulas, pasta_recortes)
    (pasta_recortes / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return indice


def ler(produto: Path, ids: list[str] | None = None) -> list[dict]:
    """Roda Audiveris e homr em cada recorte com pauta de um produto.

    Lê ``recortes/indice.json`` e fica com as entradas com pauta (``sem_pauta`` falso).
    Com ``ids``, roda só essas; um id que não é recorte com pauta levanta ``ValueError``
    antes de qualquer leitor rodar. Para cada biblioteca, em sequência, grava
    ``omr/<biblioteca>/<condicao>/`` com ``execucao.json``. Ao fim, aplica a armadura do
    vídeo, calculada sobre todas as entradas com pauta do índice (não só as pedidas), e
    grava ``omr/audiveris/<CONDICAO_AUDIVERIS>_herdada/``.

    Args:
        produto: caminho do JSON de produto (somente leitura).
        ids: ids dos recortes a ler (``None`` = todos com pauta).

    Returns:
        Os registros de execução das duas bibliotecas, na ordem Audiveris e depois homr.
        Cada registro traz a chave extra ``biblioteca``.

    Raises:
        ValueError: se algum id de ``ids`` não é recorte com pauta do índice.
    """
    pasta_recortes = pasta_do_produto(produto) / "recortes"
    indice = json.loads((pasta_recortes / "indice.json").read_text(encoding="utf-8"))
    com_pauta = [entrada for entrada in indice if not entrada["sem_pauta"]]
    if ids is None:
        escolhidas = com_pauta
    else:
        existentes = {entrada["id"] for entrada in com_pauta}
        desconhecidos = sorted(set(ids) - existentes)
        if desconhecidos:
            raise ValueError(f"ids sem pauta ou fora do índice: {desconhecidos}")
        escolhidas = [entrada for entrada in com_pauta if entrada["id"] in ids]

    registros: list[dict] = []
    for biblioteca, condicao in (
        ("audiveris", CONDICAO_AUDIVERIS),
        ("homr", CONDICAO_HOMR),
    ):
        pasta_base = pasta_omr(produto) / biblioteca / condicao
        pasta_base.mkdir(parents=True, exist_ok=True)
        do_lote: list[dict] = []
        for entrada in escolhidas:
            registro = rodar_um(
                biblioteca,
                condicao,
                entrada,
                pasta_base,
                origem=pasta_recortes / f"{entrada['id']}.png",
            )
            do_lote.append(registro)
            estado = "ok" if registro["ok"] else "FALHA"
            detalhe = f" ({registro['motivo']})" if registro["motivo"] else ""
            print(
                f"{biblioteca} {entrada['id']}: {estado} {registro['segundos']} s"
                f"{detalhe}",
                flush=True,
            )
        _gravar_execucao(pasta_base, do_lote)
        registros.extend({**registro, "biblioteca": biblioteca} for registro in do_lote)

    pasta_audiveris = pasta_omr(produto) / "audiveris"
    execucoes = json.loads(
        (pasta_audiveris / CONDICAO_AUDIVERIS / "execucao.json").read_text(
            encoding="utf-8"
        )
    )
    no_execucao = {registro["id"] for registro in execucoes}
    do_video = [entrada for entrada in com_pauta if entrada["id"] in no_execucao]
    herdar_condicao(
        execucoes,
        do_video,
        pasta_audiveris / f"{CONDICAO_AUDIVERIS}_herdada",
        RAIZ,
    )
    return registros


def eventos_do_produto(
    notas: list[dict], tela: int, x0: float, x1: float
) -> list[EventoTab]:
    """Monta os eventos da tab a partir das notas do produto, agrupadas por coluna.

    Entram as notas da tela ``tela`` com ``x_centro_quadro`` em ``[x0, x1]``, casa
    inteira e altura (``midi_da_corda`` não devolve None). Notas da mesma ``coluna``
    (por exemplo, a mesma nota em duas passagens) formam um evento: as alturas são o
    conjunto das alturas do grupo, e o x é a média dos ``x_centro_quadro``.

    Args:
        notas: lista ``notas`` do produto (``chorinho/video@1``).
        tela: id da tela cujas notas entram.
        x0: início da janela horizontal do recorte (``caixa_recorte[0]``).
        x1: fim da janela horizontal do recorte (``caixa_recorte[2]``).

    Returns:
        Eventos em ordem de coluna, com ``indice`` de 0 a n-1. Cada evento guarda todas
        as notas do grupo em ``notas``.
    """
    grupos: dict[int, list[tuple[dict, int]]] = {}
    for nota in notas:
        if nota["tela"] != tela:
            continue
        x = float(nota["x_centro_quadro"])
        if not x0 <= x <= x1:
            continue
        try:
            corda = int(nota["corda"])
            casa = int(nota["casa"])
        except ValueError, TypeError:
            continue
        soado = midi_da_corda(corda, casa)
        if soado is None:
            continue
        grupos.setdefault(int(nota["coluna"]), []).append(
            (nota, soado + SEMITONS_ESCRITA)
        )
    eventos = []
    for indice, coluna in enumerate(sorted(grupos)):
        membros = grupos[coluna]
        xs = [float(nota["x_centro_quadro"]) for nota, _ in membros]
        eventos.append(
            EventoTab(
                indice=indice,
                x_quadro=sum(xs) / len(xs),
                midis=frozenset(midi for _, midi in membros),
                notas=[nota for nota, _ in membros],
            )
        )
    return eventos


def reparear_por_x(
    partitura: list[EventoPartitura],
    tab: list[EventoTab],
    pares: list[dict],
    tolerancia_px: float,
) -> list[dict]:
    """Troca o par por altura quando a posição no quadro o contradiz.

    Candidato é o evento com x no quadro cujo par por altura é None ou tem
    ``confere_x`` falso. Os candidatos são vistos em ordem. Cada um pega a coluna da tab
    livre mais próxima em x, se a distância for até ``tolerancia_px``; senão fica com o
    par que tinha (ou sem par).

    Uma coluna está livre para um candidato quando nenhuma outra linha a segura: segura
    é o par de uma linha com ``confere_x`` diferente de falso, ou o par de uma linha já
    decidida (um candidato anterior, ou um evento que não é candidato). O par de um
    candidato ainda não decidido não segura a coluna. Se o candidato pega essa coluna, o
    candidato ainda não decidido perde o par e segue como candidato, sem par, quando
    chegar a vez dele.

    ``metodo`` é ``"x"`` na linha cujo par veio desta função e ``"altura"`` nas demais,
    inclusive as sem par. As entradas não são alteradas: a função devolve linhas novas.

    Args:
        partitura: eventos da partitura, na mesma ordem de ``pares``.
        tab: eventos da tab, em ordem.
        pares: linhas de ``parear``, uma por evento da partitura.
        tolerancia_px: distância máxima em x para trocar o par (a entrelinha da pauta).

    Returns:
        Uma linha por evento da partitura, com as mesmas chaves de ``parear`` mais
        ``metodo``.
    """
    atuais = [{**par, "metodo": "altura"} for par in pares]
    decididos: set[int] = set()
    for i, evento in enumerate(partitura):
        linha = atuais[i]
        candidato = evento.x_quadro is not None and (
            linha["par_tab"] is None or linha["confere_x"] is False
        )
        if candidato:
            livres = [
                j
                for j in range(len(tab))
                if not _coluna_segura(atuais, decididos, j, i)
            ]
            mais_perto: tuple[float, int] | None = None
            for j in livres:
                distancia = abs(evento.x_quadro - tab[j].x_quadro)
                if mais_perto is None or distancia < mais_perto[0]:
                    mais_perto = (distancia, j)
            if mais_perto is not None and mais_perto[0] <= tolerancia_px:
                distancia, j = mais_perto
                for k, outra in enumerate(atuais):
                    if k != i and k not in decididos and outra["par_tab"] == j:
                        atuais[k] = {
                            **outra,
                            "par_tab": None,
                            "x_tab": None,
                            "distancia_x": None,
                            "confere_x": None,
                            "t_ini": [],
                        }
                atuais[i] = {
                    **linha,
                    "par_tab": j,
                    "x_tab": tab[j].x_quadro,
                    "distancia_x": distancia,
                    "confere_x": True,
                    "t_ini": _t_inis(tab[j].notas),
                    "metodo": "x",
                }
        decididos.add(i)
    return atuais


def _coluna_segura(
    atuais: list[dict], decididos: set[int], coluna: int, quem: int
) -> bool:
    """Diz se uma coluna da tab está segurada por outra linha de ``reparear_por_x``.

    Args:
        atuais: linhas correntes do pareamento.
        decididos: índices das linhas já decididas.
        coluna: índice da coluna da tab.
        quem: índice da linha que quer a coluna (ela mesma não conta).

    Returns:
        True se outra linha tem a coluna como par e não é um candidato ainda não decidido
        com ``confere_x`` falso.
    """
    return any(
        k != quem
        and linha["par_tab"] == coluna
        and (linha["confere_x"] is not False or k in decididos)
        for k, linha in enumerate(atuais)
    )


def _fifths_origem(omr: Path, rid: str) -> str:
    """De onde veio a armadura da pauta: do vídeo, se foi aplicada, ou da leitura.

    Lê ``herdada.json`` em ``omr/audiveris/<CONDICAO_AUDIVERIS>_herdada``. Sem o arquivo,
    ou sem o registro do recorte, a origem é ``leitura``.

    Args:
        omr: pasta ``omr`` do produto (``pasta_omr``).
        rid: id do recorte.

    Returns:
        ``"video"`` se ``fifths_aplicado`` do registro não é None, senão ``"leitura"``.
    """
    caminho = omr / "audiveris" / f"{CONDICAO_AUDIVERIS}_herdada" / "herdada.json"
    if not caminho.exists():
        return "leitura"
    registros = json.loads(caminho.read_text(encoding="utf-8"))
    for registro in registros:
        if registro["id"] == rid:
            return "video" if registro["fifths_aplicado"] is not None else "leitura"
    return "leitura"


def _compassos_do_recorte(leitura: dict, entrada_omr: Path, x0: float) -> list[dict]:
    """Número, fórmula e x no quadro de cada compasso de uma leitura.

    O x do compasso ``k`` é ``x0 + left / ESCALA_X2``, com ``left`` do ``.omr`` (o mesmo
    cálculo de ``_x_do_simbolo``). Compasso além dos do ``.omr`` fica com x None.

    Args:
        leitura: resultado de ``ler_partitura`` da leitura herdada.
        entrada_omr: ``.omr`` da mesma imagem.
        x0: início da janela horizontal do recorte (``caixa_recorte[0]``).

    Returns:
        Uma entrada ``{"numero", "fracao", "x_quadro"}`` por compasso, na ordem.
    """
    pilhas = x_dos_compassos(entrada_omr)
    formula = leitura["compasso_formula"]
    fracao = None
    if formula and formula["beats"] is not None and formula["beat_type"] is not None:
        fracao = f"{formula['beats']}/{formula['beat_type']}"
    compassos = []
    for k, medida in enumerate(leitura["compassos"]):
        x = x0 + pilhas[k][0] / ESCALA_X2 if k < len(pilhas) else None
        compassos.append({"numero": medida["numero"], "fracao": fracao, "x_quadro": x})
    return compassos


def _simbolo_do_documento(simbolo: dict) -> dict:
    """Símbolo no formato do documento ``chorinho/partitura@1``.

    Args:
        simbolo: símbolo de ``ler_partitura``, com ``origem`` acrescentada por
            ``completar_com_homr``.

    Returns:
        Dicionário com ``nome``, ``midi_escrito``, ``figura``, ``pontuada``, ``voz``,
        ``ligadura_inicio``, ``ligadura_fim``, ``notacoes`` e ``origem``.
    """
    return {
        "nome": simbolo["nome"],
        "midi_escrito": simbolo["midi"],
        "figura": simbolo["figura"],
        "pontuada": simbolo["pontuada"],
        "voz": simbolo["voz"],
        "ligadura_inicio": simbolo["ligadura_inicio"],
        "ligadura_fim": simbolo["ligadura_fim"],
        "notacoes": simbolo["notacoes"],
        "origem": simbolo.get("origem", "audiveris"),
    }


def _pauta_do_recorte(entrada: dict, notas: list[dict], omr: Path) -> dict:
    """Pauta de um recorte: armadura, compassos e eventos, cada evento com o par na tab.

    Os pares vêm de ``parear`` e passam por ``reparear_por_x``, que troca o par quando a
    posição no quadro o contradiz. Cada par traz ``metodo`` (``altura`` ou ``x``).

    Se falta algum dos três arquivos de leitura (ou algum não abre), a pauta sai com
    ``eventos`` vazio, ``compassos`` vazio, ``fifths`` None e a chave ``erro``, e o
    processamento segue para as outras.

    Args:
        entrada: entrada do ``indice.json`` com ``sem_pauta`` falso.
        notas: lista ``notas`` do produto.
        omr: pasta ``omr`` do produto (``pasta_omr``).

    Returns:
        ``{"tela", "recorte", "caixa_quadro", "entrelinha", "fifths", "fifths_origem",
        "compassos", "eventos"}``, com ``erro`` quando a leitura não pôde ser feita.
    """
    rid = entrada["id"]
    tela = int(entrada["tela"])
    x0, _, x1, _ = entrada["caixa_recorte"]
    pauta: dict = {
        "tela": tela,
        "recorte": rid,
        "caixa_quadro": entrada["caixa_recorte"],
        "entrelinha": float(entrada["entrelinha"]),
        "fifths": None,
        "fifths_origem": None,
        "compassos": [],
    }
    herdada = (
        omr / "audiveris" / f"{CONDICAO_AUDIVERIS}_herdada" / rid / "saida.musicxml"
    )
    entrada_omr = omr / "audiveris" / CONDICAO_AUDIVERIS / rid / "entrada.omr"
    homr_xml = omr / "homr" / CONDICAO_HOMR / rid / "saida.musicxml"
    faltando = [str(c) for c in (herdada, entrada_omr, homr_xml) if not c.exists()]
    if faltando:
        return {**pauta, "eventos": [], "erro": f"faltando: {', '.join(faltando)}"}
    try:
        leitura = ler_partitura(herdada)
        partitura = eventos_da_partitura(herdada, entrada_omr, x0, ESCALA_X2)
        homr = eventos_da_partitura(homr_xml, None, x0)
        compassos = _compassos_do_recorte(leitura, entrada_omr, x0)
    except (ValueError, ET.ParseError) as falha:
        return {**pauta, "eventos": [], "erro": f"leitura: {falha}"}
    pauta["fifths"] = leitura["armadura"]
    pauta["fifths_origem"] = _fifths_origem(omr, rid)
    pauta["compassos"] = compassos
    tab = eventos_do_produto(notas, tela, x0, x1)
    partitura, _ = completar_com_homr(partitura, homr, tab)
    pares = reparear_por_x(
        partitura,
        tab,
        parear(partitura, tab, pauta["entrelinha"]),
        pauta["entrelinha"],
    )
    eventos = []
    for evento, linha in zip(partitura, pares, strict=True):
        j = linha["par_tab"]
        par = None
        if j is not None:
            par = {
                "tela": tela,
                "coluna": tab[j].notas[0]["coluna"],
                "distancia_x": linha["distancia_x"],
                "confere_x": linha["confere_x"],
                "metodo": linha["metodo"],
            }
        eventos.append(
            {
                "compasso": evento.compasso,
                "t": evento.t,
                "x_quadro": evento.x_quadro,
                "par": par,
                "simbolos": [_simbolo_do_documento(s) for s in evento.simbolos],
                "trocadas": [_simbolo_do_documento(s) for s in evento.trocadas],
            }
        )
    return {**pauta, "eventos": eventos}


def _contagens_da_pauta(pauta: dict, notas: list[dict]) -> dict[str, int]:
    """Contagens de uma pauta, para o resumo e para a linha da CLI.

    Args:
        pauta: pauta de ``_pauta_do_recorte``.
        notas: lista ``notas`` do produto (para contar as colunas da tab da janela).

    Returns:
        ``eventos``, ``com_par``, ``com_x_conferido``, ``par_por_x`` (pares com
        ``metodo`` ``x``), ``colunas_tab`` (eventos da tab na janela da pauta),
        ``notas_homr`` (símbolos com ``origem`` homr) e ``trocadas``.
    """
    eventos = pauta["eventos"]
    x0, x1 = pauta["caixa_quadro"][0], pauta["caixa_quadro"][2]
    return {
        "eventos": len(eventos),
        "com_par": sum(e["par"] is not None for e in eventos),
        "com_x_conferido": sum(
            e["par"] is not None and e["par"]["confere_x"] is True for e in eventos
        ),
        "par_por_x": sum(
            e["par"] is not None and e["par"]["metodo"] == "x" for e in eventos
        ),
        "colunas_tab": len(eventos_do_produto(notas, pauta["tela"], x0, x1)),
        "notas_homr": sum(
            s["origem"] == "homr" for e in eventos for s in e["simbolos"]
        ),
        "trocadas": sum(len(e["trocadas"]) for e in eventos),
    }


def caminho_do_parear(produto: Path) -> Path:
    """Caminho do documento de ``parear``: ``pasta_do_produto / <stem>.partitura.json``.

    Args:
        produto: caminho do JSON de produto.

    Returns:
        O caminho onde ``parear_produto`` grava o documento.
    """
    return pasta_do_produto(produto) / f"{produto.stem}.partitura.json"


def parear_produto(produto: Path) -> dict:
    """Pareia as pautas de um produto com as colunas da tab e grava o documento.

    Lê ``recortes/indice.json`` e processa, em ordem, as entradas com pauta. Cada pauta
    vira um item de ``pautas`` (ver ``_pauta_do_recorte``). O documento é gravado em
    ``caminho_do_parear(produto)``. O produto é lido, nunca escrito.

    Args:
        produto: caminho do JSON de produto (somente leitura).

    Returns:
        O documento ``chorinho/partitura@1``, com ``produto_sha256`` e ``resumo``.
    """
    bruto = produto.read_bytes()
    dados = json.loads(bruto.decode("utf-8"))
    indice = json.loads(
        (pasta_do_produto(produto) / "recortes" / "indice.json").read_text(
            encoding="utf-8"
        )
    )
    pautas = [
        _pauta_do_recorte(entrada, dados["notas"], pasta_omr(produto))
        for entrada in indice
        if not entrada["sem_pauta"]
    ]
    contagens = [_contagens_da_pauta(pauta, dados["notas"]) for pauta in pautas]
    totais = {
        chave: sum(c[chave] for c in contagens)
        for chave in (
            "eventos",
            "com_par",
            "com_x_conferido",
            "par_por_x",
            "notas_homr",
            "trocadas",
            "colunas_tab",
        )
    }
    pares = [
        (e["par"]["tela"], e["par"]["coluna"])
        for pauta in pautas
        for e in pauta["eventos"]
        if e["par"] is not None
    ]
    documento = {
        "esquema": ESQUEMA_PARTITURA,
        "produto": str(produto),
        "produto_sha256": hashlib.sha256(bruto).hexdigest(),
        "gerado_por": {
            "leitor": "audiveris x2_margem + armadura do vídeo",
            "completar": "homr nativo confirmado pela tab",
        },
        "pautas": pautas,
        "resumo": {
            "pautas": len(pautas),
            **totais,
            "colunas_pareadas": len(set(pares)),
        },
    }
    destino = caminho_do_parear(produto)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return documento


def assinatura(quadro: np.ndarray, pautas: list[Pauta]) -> np.ndarray | None:
    """Imagem binária de tinta da região das pautas, para comparar quadros.

    A região vai da linha de cima da primeira pauta à linha de baixo da última, com
    ``MARGEM_ASSINATURA_ENTRELINHAS`` entrelinhas de folga de cada lado, e tem a largura
    toda do quadro. Tinta é o pixel escuro (ou claro, em fundo escuro, pela regra de
    ``_tinta_escura``) e com contraste sobre o fundo local (top-hat): ver ``_tinta``. A
    máscara de tinta é reduzida a ``LARGURA_ASSINATURA`` por ``ALTURA_ASSINATURA`` com
    ``cv2.INTER_AREA`` (cada bloco vira a fração de tinta dele) e limiarizada em
    ``FRACAO_TINTA``. Assim o destaque colorido atrás da nota, o cursor vermelho e a cor
    da compressão não mudam a assinatura da mesma página.

    Args:
        quadro: quadro BGR (ou cinza), ``uint8``.
        pautas: pautas do quadro, como devolve ``achar_pautas``.

    Returns:
        Matriz booleana de forma ``(ALTURA_ASSINATURA, LARGURA_ASSINATURA)``, ou ``None``
        se o quadro não tem pauta ou a região sai vazia depois de cortada no quadro.
    """
    if not pautas:
        return None
    cinza = _cinza(quadro)
    primeira = min(pautas, key=lambda pauta: pauta.ys[0])
    ultima = max(pautas, key=lambda pauta: pauta.ys[4])
    y0 = max(
        0,
        int(primeira.ys[0] - MARGEM_ASSINATURA_ENTRELINHAS * primeira.entrelinha),
    )
    y1 = min(
        cinza.shape[0],
        int(ultima.ys[4] + MARGEM_ASSINATURA_ENTRELINHAS * ultima.entrelinha) + 1,
    )
    if y1 <= y0:
        return None
    entrelinha = float(np.median([pauta.entrelinha for pauta in pautas]))
    tinta = _tinta(quadro, cinza, entrelinha)[y0:y1].astype(np.float32)
    fracao = cv2.resize(
        tinta,
        (LARGURA_ASSINATURA, ALTURA_ASSINATURA),
        interpolation=cv2.INTER_AREA,
    )
    return fracao >= FRACAO_TINTA


def _tinta(quadro: np.ndarray, cinza: np.ndarray, entrelinha: float) -> np.ndarray:
    """Máscara booleana de tinta do quadro inteiro, por contraste local no canal V.

    Usa o top-hat do V com elemento quadrado de lado ``2 * round(entrelinha) + 1``: em
    fundo claro, o black-hat (o que é mais escuro que o fundo local); em fundo escuro, o
    top-hat (o que é mais claro). A polaridade vem de ``_tinta_escura``. Tinta é o pixel
    cujo contraste passa de ``DELTA_TINTA``. Assim o traço preto tingido pela compressão
    e o destaque colorido, que mudam a saturação mas não o contraste, não somem da máscara.
    Quadro cinza usa o próprio quadro como V.

    Args:
        quadro: quadro BGR ou cinza, ``uint8``.
        cinza: o mesmo quadro em tons de cinza (``_cinza``).
        entrelinha: entrelinha mediana das pautas do quadro, em px.

    Returns:
        Matriz booleana do tamanho do quadro.
    """
    valor = (
        quadro if quadro.ndim == 2 else cv2.cvtColor(quadro, cv2.COLOR_BGR2HSV)[:, :, 2]
    )
    lado = 2 * round(entrelinha) + 1
    elemento = cv2.getStructuringElement(cv2.MORPH_RECT, (lado, lado))
    if _tinta_escura(cinza):
        contraste = cv2.morphologyEx(valor, cv2.MORPH_BLACKHAT, elemento)
    else:
        contraste = cv2.morphologyEx(valor, cv2.MORPH_TOPHAT, elemento)
    return contraste > DELTA_TINTA


def _forca_de_linha(
    cinza: np.ndarray, y: float, entrelinha: float, x0: int, x1: int
) -> float:
    """Fração das colunas de ``[x0, x1)`` em que há uma linha horizontal em ``y``.

    Regra de ``partitura_recortes._colunas_com_linhas`` (a coluna tem linha se o mínimo do
    cinza é ``<= ref - CRISTA_DELTA_EXT``, com ``ref`` a média do cinza nas linhas
    ``y - e/2`` e ``y + e/2``), mas com a faixa de ``y-2`` a ``y+2`` pedida para a 6ª linha.
    Uma faixa de linhas de tinta grossa (viga de colcheias, haste) também passa nesse teste:
    ver ``diag/razoes_tab.txt``.

    Args:
        cinza: quadro em tons de cinza.
        y: linha candidata, em px.
        entrelinha: entrelinha da pauta, em px.
        x0: início horizontal (inclusive).
        x1: fim horizontal (exclusivo).

    Returns:
        A fração, entre 0 e 1 (0 se o intervalo horizontal está vazio).
    """
    altura = cinza.shape[0]
    largura = x1 - x0
    if largura <= 0:
        return 0.0
    yc = round(y)
    meia = round(entrelinha / 2)
    ya = min(max(yc - meia, 0), altura - 1)
    yb = min(max(yc + meia, 0), altura - 1)
    faixa = cinza[max(yc - 2, 0) : min(yc + 3, altura), x0:x1].astype(np.int32)
    ref = (cinza[ya, x0:x1].astype(np.int32) + cinza[yb, x0:x1].astype(np.int32)) / 2
    presente = faixa.min(axis=0) <= ref - CRISTA_DELTA_EXT
    return float(np.count_nonzero(presente)) / largura


def _forca_por_trechos(
    cinza: np.ndarray, y: float, entrelinha: float, x0: int, x1: int
) -> float:
    """Força de uma linha pelo 2º menor valor entre ``TRECHOS_TABLATURA`` trechos.

    Divide ``[x0, x1)`` em ``TRECHOS_TABLATURA`` trechos de largura igual, mede
    ``_forca_de_linha`` em cada um, ordena e devolve o 2º menor valor (índice 1). Uma linha
    de tablatura atravessa a largura toda e dá força alta em quase todos os trechos. Uma
    viga de semicolcheia, acima da pauta, cobre só alguns trechos e fica no mínimo, ou
    perto dele, e por isso não é confundida com a 6ª linha.

    Args:
        cinza: quadro em tons de cinza.
        y: linha candidata, em px.
        entrelinha: entrelinha da pauta, em px.
        x0: início horizontal (inclusive).
        x1: fim horizontal (exclusivo).

    Returns:
        A força, entre 0 e 1.
    """
    bordas = np.linspace(x0, x1, TRECHOS_TABLATURA + 1).round().astype(int)
    forcas = sorted(
        _forca_de_linha(cinza, y, entrelinha, int(a), int(b))
        for a, b in itertools.pairwise(bordas)
    )
    return forcas[1]


def razoes_de_tablatura(
    cinza: np.ndarray, ys: list[float], entrelinha: float, x0: int, x1: int
) -> tuple[float, float, float]:
    """Força da 6ª linha, abaixo e acima da pauta, em relação à das 5 linhas.

    A força de cada uma das 5 linhas é ``_forca_por_trechos``; a mediana delas é a
    referência. Para cada lado, a 6ª linha é procurada em ``ys[4] + entrelinha`` (abaixo)
    e em ``ys[0] - entrelinha`` (acima), com ``TOLERANCIA_SEXTA_LINHA`` px de folga para
    cada lado (vale a maior força nessa faixa). A razão é essa força dividida pela mediana.

    Args:
        cinza: quadro em tons de cinza.
        ys: as 5 linhas da pauta, de cima para baixo, em px.
        entrelinha: entrelinha da pauta, em px.
        x0: início horizontal do trecho (inclusive).
        x1: fim horizontal do trecho (exclusivo).

    Returns:
        ``(razao_abaixo, razao_acima, mediana)``. Razões são 0 se a mediana é 0 (sem
        linhas detectáveis no trecho).
    """
    mediana = float(
        np.median([_forca_por_trechos(cinza, y, entrelinha, x0, x1) for y in ys])
    )

    def razao(centro: float) -> float:
        forca = max(
            _forca_por_trechos(cinza, centro + d, entrelinha, x0, x1)
            for d in range(-TOLERANCIA_SEXTA_LINHA, TOLERANCIA_SEXTA_LINHA + 1)
        )
        return forca / mediana if mediana > 0 else 0.0

    return (
        razao(ys[4] + entrelinha),
        razao(ys[0] - entrelinha),
        mediana,
    )


def e_tablatura(
    cinza: np.ndarray, ys: list[float], entrelinha: float, x0: int, x1: int
) -> bool:
    """Diz se uma pauta achada é, na verdade, uma tablatura de 6 linhas.

    A tablatura tem 6 cordas e o detector de pauta acha 5 delas. Então é tablatura se a
    6ª linha aparece abaixo (``ys[4] + entrelinha``) ou acima (``ys[0] - entrelinha``) com
    força ``>= LIMIAR_TABLATURA`` vezes a das 5 linhas (``razoes_de_tablatura``). A força
    é medida em trechos (``_forca_por_trechos``): a linha da tablatura atravessa a largura
    toda, mas uma viga de semicolcheia acima da pauta cobre só parte dela e não passa do
    limiar. Numa pauta de 5 linhas, esses lugares são vão claro, salvo uma viga, que tem
    força muito menor que a das linhas inteiras.

    Args:
        cinza: quadro em tons de cinza.
        ys: as 5 linhas da pauta, de cima para baixo, em px.
        entrelinha: entrelinha da pauta, em px.
        x0: início horizontal do trecho (inclusive).
        x1: fim horizontal do trecho (exclusivo).

    Returns:
        True se a pauta é tablatura, False se é pauta de 5 linhas.
    """
    abaixo, acima, _ = razoes_de_tablatura(cinza, ys, entrelinha, x0, x1)
    return max(abaixo, acima) >= LIMIAR_TABLATURA


def diferenca(a: np.ndarray, b: np.ndarray) -> float:
    """Fração de pixels que diferem entre duas assinaturas.

    Calcula ``|a XOR b| / max(1, |a OR b|)``. Assinaturas iguais dão 0; sem nenhum pixel
    em comum (e ambas com tinta) dão 1.

    Args:
        a: assinatura booleana.
        b: assinatura booleana, da mesma forma que ``a``.

    Returns:
        A diferença, entre 0 e 1.
    """
    uniao = int(np.count_nonzero(a | b))
    return float(np.count_nonzero(a ^ b)) / max(1, uniao)


def _sequencias_estaveis(
    amostras: list[tuple[float, np.ndarray | None]], limiar: float
) -> list[list[tuple[float, np.ndarray]]]:
    """Quebra as amostras em sequências em que cada assinatura está perto da primeira.

    Uma amostra sem assinatura (``None``) encerra a sequência corrente. Uma amostra
    que passa de ``limiar`` em relação à primeira da sequência encerra a corrente e
    abre outra com ela.

    Args:
        amostras: pares ``(t, assinatura)`` em ordem de tempo.
        limiar: diferença máxima, em relação à primeira amostra da sequência.

    Returns:
        As sequências, na ordem em que aparecem; cada uma é uma lista de ``(t, assinatura)``.
    """
    sequencias: list[list[tuple[float, np.ndarray]]] = []
    atual: list[tuple[float, np.ndarray]] = []
    for t, assinatura_atual in amostras:
        if assinatura_atual is None:
            if atual:
                sequencias.append(atual)
            atual = []
            continue
        if atual and diferenca(atual[0][1], assinatura_atual) > limiar:
            sequencias.append(atual)
            atual = []
        atual.append((t, assinatura_atual))
    if atual:
        sequencias.append(atual)
    return sequencias


def agrupar_paginas(
    amostras: list[tuple[float, np.ndarray | None]],
    limiar: float = LIMIAR_PAGINA,
    minimo: int = MINIMO_AMOSTRAS,
) -> list[dict]:
    """Agrupa as amostras de um vídeo em páginas, com as exibições de cada uma.

    Uma sequência estável (``_sequencias_estaveis``) com menos de ``minimo`` amostras é
    descartada. Cada sequência que sobra é comparada com a primeira amostra de cada
    página já achada. Se alguma está a até ``limiar``, a sequência é uma nova exibição
    dessa página (a mais parecida, se são várias); senão começa uma página nova.

    Args:
        amostras: pares ``(t, assinatura)`` em ordem de tempo; ``None`` onde não há pauta.
        limiar: diferença máxima para duas assinaturas serem a mesma página.
        minimo: amostras mínimas de uma sequência para contar como exibição.

    Returns:
        Uma entrada por página, na ordem da primeira aparição, com ``pagina`` (1 a n),
        ``exibicoes`` (lista de ``{"t0", "t1"}``, a primeira e a última amostra de cada
        exibição) e ``t`` (o ponto médio da exibição mais longa).
    """
    paginas: list[dict] = []
    for sequencia in _sequencias_estaveis(amostras, limiar):
        if len(sequencia) < minimo:
            continue
        exibicao = {"t0": sequencia[0][0], "t1": sequencia[-1][0]}
        referencia = sequencia[0][1]
        candidatas = [
            (diferenca(pagina["assinatura"], referencia), pagina) for pagina in paginas
        ]
        proxima = min(candidatas, key=lambda par: par[0], default=None)
        if proxima is not None and proxima[0] <= limiar:
            proxima[1]["exibicoes"].append(exibicao)
        else:
            paginas.append({"assinatura": referencia, "exibicoes": [exibicao]})
    resultado = []
    for numero, pagina in enumerate(paginas, start=1):
        mais_longa = max(pagina["exibicoes"], key=lambda e: e["t1"] - e["t0"])
        resultado.append(
            {
                "pagina": numero,
                "exibicoes": pagina["exibicoes"],
                "t": (mais_longa["t0"] + mais_longa["t1"]) / 2,
            }
        )
    return resultado


def _limpar_paginas(pasta_recortes: Path) -> None:
    """Apaga os arquivos de uma execução anterior de ``paginar``.

    Remove ``P*.png``, ``contexto_*.jpg`` e ``indice.json``; outros arquivos ficam.

    Args:
        pasta_recortes: pasta ``recortes/`` do vídeo (criada se faltar).
    """
    pasta_recortes.mkdir(parents=True, exist_ok=True)
    for padrao in ("P*.png", "contexto_*.jpg", "indice.json"):
        for arquivo in pasta_recortes.glob(padrao):
            arquivo.unlink()


def _verificar_video(arquivo: Path) -> None:
    """Confere que o vídeo existe e tem duração, antes de varrer.

    Sem essa conferência, um nome que não bate com o disco (ex.: ``ó`` em NFC no lugar de
    NFD) fazia ``info`` devolver duração 0 e a varredura gravava 0 páginas em silêncio.
    Quando o nome difere só na forma Unicode, a mensagem diz qual é o nome no disco.

    Args:
        arquivo: caminho completo do vídeo (``acervo() / video``).

    Raises:
        FileNotFoundError: o arquivo não existe; a mensagem traz o nome no disco, se a
            diferença for só de normalização Unicode.
        RuntimeError: o ``ffprobe`` não leu a duração do arquivo.
    """
    if not arquivo.is_file():
        dica = ""
        if arquivo.parent.is_dir():
            alvo = unicodedata.normalize("NFC", arquivo.name)
            for irmao in arquivo.parent.iterdir():
                if unicodedata.normalize("NFC", irmao.name) == alvo:
                    dica = f"; no disco o nome é {irmao.name!r} (NFC/NFD diferem)"
                    break
        raise FileNotFoundError(f"vídeo não encontrado no acervo: {arquivo}{dica}")
    if float(info(str(arquivo))["duracao_s"]) <= 0:
        raise RuntimeError(f"ffprobe não leu a duração de {arquivo}")


def _paginar(video: str, pasta: Path | None) -> tuple[list[dict], int, int, int]:
    """Varre um vídeo, acha as páginas e grava os recortes de todas as pautas.

    Ver ``paginar``. Devolve também o número de amostras, de recortes gravados e de pautas
    descartadas por serem tablatura (``e_tablatura``), para a linha da CLI.

    Args:
        video: caminho do vídeo, relativo ao acervo.
        pasta: pasta do vídeo (dentro dela vai ``recortes/``); ``None`` usa
            ``PASTA_SEM_PRODUTO / _slug(video)``.

    Returns:
        ``(paginas, amostras, recortes, descartadas)``: as páginas (como ``paginar``), o
        número de quadros amostrados, o de recortes de pauta gravados e o de pautas
        descartadas por serem tablatura.

    Raises:
        FileNotFoundError: o vídeo não está no acervo (ver ``_verificar_video``).
        RuntimeError: o ``ffprobe`` não leu a duração do vídeo.
    """
    _verificar_video(acervo() / video)
    caminho = str(acervo() / video)
    duracao = float(info(caminho)["duracao_s"])
    amostras: list[tuple[float, np.ndarray | None]] = []
    for t, quadro in quadros(caminho, 0.0, duracao, QPS_PAGINAS):
        amostras.append((t, assinatura(quadro, achar_pautas(quadro))))
    paginas = agrupar_paginas(amostras)

    pasta_video = pasta if pasta is not None else PASTA_SEM_PRODUTO / _slug(video)
    pasta_recortes = pasta_video / "recortes"
    _limpar_paginas(pasta_recortes)
    canal = Path(video).parts[0]
    indice: list[dict] = []
    total_recortes = 0
    total_descartadas = 0
    for pagina in paginas:
        numero = pagina["pagina"]
        t = pagina["t"]
        exibicoes = pagina["exibicoes"]
        quadro = quadro_em(caminho, t)
        if quadro is None:
            pagina["pautas"] = 0
            indice.append(
                {
                    "tela": numero,
                    "sem_pauta": True,
                    "motivo": "ffmpeg não leu o quadro",
                    "t": t,
                    "pagina": numero,
                    "exibicoes": exibicoes,
                }
            )
            continue
        fonte = FonteQuadro(origem="video", canal=canal, video=video, t=t)
        entradas, recortes, celula = processar_quadro(
            fonte,
            quadro,
            "video",
            primeiro_numero=1,
            margem_cima=MARGEM_ENTRELINHAS,
            margem_baixo=MARGEM_ENTRELINHAS,
        )
        cinza = _cinza(quadro)
        com_pauta = [entrada for entrada in entradas if not entrada["sem_pauta"]]
        mantidas: list[tuple[dict, Recorte, tuple[int, int, int, int]]] = []
        descartadas = 0
        for entrada, recorte, caixa in zip(
            com_pauta, recortes, celula.caixas, strict=True
        ):
            x0, x1 = entrada["caixa_recorte"][0], entrada["caixa_recorte"][2]
            if e_tablatura(cinza, entrada["ys"], entrada["entrelinha"], x0, x1):
                descartadas += 1
                continue
            mantidas.append((entrada, recorte, caixa))
        total_descartadas += descartadas
        pagina["pautas"] = len(mantidas)
        if not mantidas:
            motivo = "só tablatura no quadro" if descartadas else "sem pauta no quadro"
            indice.append(
                {
                    "tela": numero,
                    "sem_pauta": True,
                    "motivo": motivo,
                    "t": t,
                    "pagina": numero,
                    "exibicoes": exibicoes,
                }
            )
        for k, (entrada, recorte, _) in enumerate(mantidas):
            letra = chr(ord("a") + k)
            identificador = f"P{numero:02d}{letra}"
            cv2.imwrite(str(pasta_recortes / f"{identificador}.png"), recorte.imagem)
            indice.append(
                {
                    "id": identificador,
                    "tela": numero,
                    "video": video,
                    "t": t,
                    "painel": None,
                    "sem_pauta": False,
                    "ys": entrada["ys"],
                    "entrelinha": entrada["entrelinha"],
                    "caixa_recorte": entrada["caixa_recorte"],
                    "largura": entrada["largura"],
                    "altura": entrada["altura"],
                    "pagina": numero,
                    "letra": letra,
                    "exibicoes": exibicoes,
                }
            )
            total_recortes += 1
        # A célula de contexto mostra só as pautas mantidas, com os ids que sobraram.
        ids = [f"P{numero:02d}{chr(ord('a') + k)}" for k in range(len(mantidas))]
        celula = Celula(
            legenda=(
                f"{' '.join(ids) or 'SEM PAUTA'} | {canal_ascii(canal)} | t={t:.2f}s"
            ),
            imagem=quadro,
            caixas=[caixa for _, _, caixa in mantidas],
        )
        # folha_contexto numera pela ordem das células; com uma célula sai contexto_01.jpg,
        # que é renomeado para a página.
        folha_contexto([celula], pasta_recortes)
        (pasta_recortes / "contexto_01.jpg").replace(
            pasta_recortes / f"contexto_P{numero:02d}.jpg"
        )
    (pasta_recortes / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return paginas, len(amostras), total_recortes, total_descartadas


def paginar(video: str, pasta: Path | None = None) -> list[dict]:
    """Acha as páginas distintas de um vídeo com pauta, sem produto, e grava os recortes.

    Varre o vídeo inteiro a ``QPS_PAGINAS`` (uma passada de ``quadros``), guarda só a
    assinatura de cada quadro (``assinatura``) e agrupa as estáveis em páginas
    (``agrupar_paginas``). Para cada página, lê o quadro em ``t`` com ``quadro_em`` e
    recorta as pautas dele, com ``processar_quadro`` e as margens da etapa ``recortar``.
    Pauta que é tablatura de 6 linhas (``e_tablatura``) é descartada antes do recorte.
    Cada pauta mantida vira ``P{pagina:02d}{letra}.png``, de cima para baixo.

    Gera ``recortes/indice.json`` com uma entrada por pauta e uma por página sem pauta
    (``sem_pauta``, com ``motivo``), e ``contexto_PNN.jpg`` por página. Apaga antes as
    saídas anteriores desse tipo. Não lê nem grava produto.

    Args:
        video: caminho do vídeo, relativo ao acervo.
        pasta: pasta do vídeo, onde fica ``recortes/``. ``None`` usa
            ``PASTA_SEM_PRODUTO / _slug(video)``, separado das pastas de produto.

    Returns:
        Uma entrada por página, na ordem da primeira aparição: ``pagina``, ``exibicoes``,
        ``t`` e ``pautas`` (quantas pautas o quadro tem).
    """
    return _paginar(video, pasta)[0]


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da linha de comando.

    Subcomando ``recortar --produto CAMINHO`` (repetível). Para cada produto, imprime
    a contagem de telas com e sem pauta e o motivo de cada tela sem pauta.

    Subcomando ``ler --produto CAMINHO [--ids T01,T02]`` (repetível). Para cada produto,
    imprime uma linha com os ``ok`` de cada biblioteca e a contagem de armaduras herdadas.

    Subcomando ``parear --produto CAMINHO`` (repetível). Para cada produto, imprime uma
    linha por pauta com as contagens, uma linha de total e o caminho gravado.

    Subcomando ``paginar --video CAMINHO [--pasta PASTA]`` (repetível; ``--pasta`` só com
    um vídeo). Para cada vídeo, imprime uma linha com páginas, recortes, tabs descartadas,
    amostras e segundos, e uma linha por página com as exibições e o número de pautas.

    Args:
        argv: argumentos (sem o nome do programa). ``None`` usa ``sys.argv``.

    Returns:
        Código de saída (0 em sucesso).
    """
    parser = argparse.ArgumentParser(
        prog="python -m tab.partitura_video",
        description="Etapas da cadeia de partitura por vídeo.",
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)
    parser_recortar = subparsers.add_parser(
        "recortar", help="recorta a pauta de cada tela de um produto"
    )
    parser_recortar.add_argument(
        "--produto",
        action="append",
        required=True,
        type=Path,
        help="JSON de produto (pode repetir)",
    )
    parser_ler = subparsers.add_parser(
        "ler", help="roda Audiveris e homr em cada recorte de pauta de um produto"
    )
    parser_ler.add_argument(
        "--produto",
        action="append",
        required=True,
        type=Path,
        help="JSON de produto (pode repetir)",
    )
    parser_ler.add_argument(
        "--ids",
        default=None,
        help="ids dos recortes, separados por vírgula (ex.: T01,T02)",
    )
    parser_parear = subparsers.add_parser(
        "parear", help="pareia as pautas com as colunas da tab de um produto"
    )
    parser_parear.add_argument(
        "--produto",
        action="append",
        required=True,
        type=Path,
        help="JSON de produto (pode repetir)",
    )
    parser_paginar = subparsers.add_parser(
        "paginar", help="acha as páginas de um vídeo sem produto e recorta as pautas"
    )
    parser_paginar.add_argument(
        "--video",
        action="append",
        required=True,
        help="caminho do vídeo, relativo ao acervo (pode repetir)",
    )
    parser_paginar.add_argument(
        "--pasta",
        default=None,
        type=Path,
        help="pasta do vídeo, onde fica recortes/ (só com um --video)",
    )
    args = parser.parse_args(argv)

    if args.comando == "recortar":
        for produto in args.produto:
            indice = recortar(produto)
            sem = [entrada for entrada in indice if entrada["sem_pauta"]]
            com = len(indice) - len(sem)
            print(
                f"{produto.stem}: telas {len(indice)}, com pauta {com},"
                f" sem pauta {len(sem)}"
            )
            for entrada in sem:
                print(f"  tela {entrada['tela']}: {entrada['motivo']}")
    elif args.comando == "ler":
        ids = None
        if args.ids is not None:
            ids = [i.strip() for i in args.ids.split(",") if i.strip()]
        for produto in args.produto:
            registros = ler(produto, ids)
            audiveris = [r for r in registros if r["biblioteca"] == "audiveris"]
            homr = [r for r in registros if r["biblioteca"] == "homr"]
            herdada = json.loads(
                (
                    pasta_omr(produto)
                    / "audiveris"
                    / f"{CONDICAO_AUDIVERIS}_herdada"
                    / "herdada.json"
                ).read_text(encoding="utf-8")
            )
            aplicadas = sum(1 for h in herdada if h["fifths_aplicado"] is not None)
            print(
                f"{produto.stem}: audiveris ok"
                f" {sum(r['ok'] for r in audiveris)}/{len(audiveris)},"
                f" homr ok {sum(r['ok'] for r in homr)}/{len(homr)},"
                f" armadura herdada em {aplicadas}"
            )
    elif args.comando == "parear":
        for produto in args.produto:
            documento = parear_produto(produto)
            notas = json.loads(produto.read_text(encoding="utf-8"))["notas"]
            for pauta in documento["pautas"]:
                c = _contagens_da_pauta(pauta, notas)
                aviso = f" (erro: {pauta['erro']})" if "erro" in pauta else ""
                print(
                    f"{pauta['recorte']} tela {pauta['tela']}:"
                    f" eventos {c['eventos']}, com par {c['com_par']},"
                    f" x conferido {c['com_x_conferido']},"
                    f" par por x {c['par_por_x']},"
                    f" colunas tab {c['colunas_tab']},"
                    f" homr {c['notas_homr']}, trocadas {c['trocadas']}{aviso}"
                )
            r = documento["resumo"]
            print(
                f"{produto.stem}: pautas {r['pautas']}, eventos {r['eventos']},"
                f" com par {r['com_par']}, x conferido {r['com_x_conferido']},"
                f" colunas tab {r['colunas_tab']},"
                f" colunas pareadas {r['colunas_pareadas']},"
                f" homr {r['notas_homr']}, trocadas {r['trocadas']}"
            )
            print(f"gravado em {caminho_do_parear(produto)}")
    elif args.comando == "paginar":
        if args.pasta is not None and len(args.video) > 1:
            parser.error("--pasta só vale com um --video")
        for video in args.video:
            inicio = time.monotonic()
            paginas, amostras, recortes, descartadas = _paginar(video, args.pasta)
            segundos = time.monotonic() - inicio
            print(
                f"{_slug(video)}: paginas {len(paginas)}, recortes {recortes},"
                f" tabs descartadas {descartadas},"
                f" amostras {amostras}, segundos {segundos:.1f}"
            )
            for pagina in paginas:
                exibicoes = ", ".join(
                    f"({e['t0']:.2f},{e['t1']:.2f})" for e in pagina["exibicoes"]
                )
                print(
                    f"P{pagina['pagina']:02d} exibicoes [{exibicoes}]"
                    f" pautas {pagina['pautas']}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
