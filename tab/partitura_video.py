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
pauta por recorte com pauta, cada uma com seus eventos e o par na tab.

Uso:
    python -m tab.partitura_video recortar --produto CAMINHO [--produto CAMINHO ...]
    python -m tab.partitura_video ler --produto CAMINHO [--produto CAMINHO ...] [--ids T01,T02]
    python -m tab.partitura_video parear --produto CAMINHO [--produto CAMINHO ...]

A etapa ``ler`` roda dentro da imagem ``chorinho-partitura:dev``, em CPU, com
``--security-opt label=disable`` (obrigatório no host deste projeto):
    podman run --rm --security-opt label=disable -v $PWD:/app -w /app \
        -e PYTHONPATH=/app chorinho-partitura:dev \
        python -m tab.partitura_video ler --produto CAMINHO
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2

from tab.caminhos import RAIZ, SAIDA
from tab.musicxml import midi_da_corda
from tab.partitura_avaliar import SEMITONS_ESCRITA
from tab.partitura_omr import _gravar_execucao, herdar_condicao, rodar_um
from tab.partitura_pareamento import (
    EventoTab,
    completar_com_homr,
    eventos_da_partitura,
    parear,
)
from tab.partitura_recortes import (
    FonteQuadro,
    folha_contexto,
    ler_fonte,
    processar_quadro,
)

#: Pasta de saída da etapa de recorte, uma subpasta por produto.
PASTA_VIDEO = SAIDA / "partitura" / "video"

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
    """Pauta de um recorte: eventos da partitura, cada um com o par na tab.

    Se falta algum dos três arquivos de leitura (ou algum não abre), a pauta sai com
    ``eventos`` vazio e a chave ``erro``, e o processamento segue para as outras.

    Args:
        entrada: entrada do ``indice.json`` com ``sem_pauta`` falso.
        notas: lista ``notas`` do produto.
        omr: pasta ``omr`` do produto (``pasta_omr``).

    Returns:
        ``{"tela", "recorte", "caixa_quadro", "entrelinha", "eventos"}``, com ``erro``
        quando a leitura não pôde ser feita.
    """
    rid = entrada["id"]
    tela = int(entrada["tela"])
    x0, _, x1, _ = entrada["caixa_recorte"]
    pauta: dict = {
        "tela": tela,
        "recorte": rid,
        "caixa_quadro": entrada["caixa_recorte"],
        "entrelinha": float(entrada["entrelinha"]),
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
        partitura = eventos_da_partitura(herdada, entrada_omr, x0)
        homr = eventos_da_partitura(homr_xml, None, x0)
    except (ValueError, ET.ParseError) as falha:
        return {**pauta, "eventos": [], "erro": f"leitura: {falha}"}
    tab = eventos_do_produto(notas, tela, x0, x1)
    partitura, _ = completar_com_homr(partitura, homr, tab)
    pares = parear(partitura, tab, pauta["entrelinha"])
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
        ``eventos``, ``com_par``, ``com_x_conferido``, ``colunas_tab`` (eventos da tab na
        janela da pauta), ``notas_homr`` (símbolos com ``origem`` homr) e ``trocadas``.
    """
    eventos = pauta["eventos"]
    x0, x1 = pauta["caixa_quadro"][0], pauta["caixa_quadro"][2]
    return {
        "eventos": len(eventos),
        "com_par": sum(e["par"] is not None for e in eventos),
        "com_x_conferido": sum(
            e["par"] is not None and e["par"]["confere_x"] is True for e in eventos
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


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da linha de comando.

    Subcomando ``recortar --produto CAMINHO`` (repetível). Para cada produto, imprime
    a contagem de telas com e sem pauta e o motivo de cada tela sem pauta.

    Subcomando ``ler --produto CAMINHO [--ids T01,T02]`` (repetível). Para cada produto,
    imprime uma linha com os ``ok`` de cada biblioteca e a contagem de armaduras herdadas.

    Subcomando ``parear --produto CAMINHO`` (repetível). Para cada produto, imprime uma
    linha por pauta com as contagens, uma linha de total e o caminho gravado.

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
