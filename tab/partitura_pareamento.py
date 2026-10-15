"""Pareamento partitura x tab pela posição x no quadro (P3).

A pauta fica em cima da tab, alinhada na vertical. Se o pareamento por sequência estiver
certo, a nota da partitura e a coluna da tab pareada caem no mesmo x do quadro. O x da
partitura vem do ``.omr`` do Audiveris (``stack.left`` + ``slot.x-offset``, na imagem
ampliada), e o da tab vem de ``x_centro_quadro``. O tempo de cada nota da partitura é o
``t_ini`` da coluna da tab pareada: não há medidor próprio. Antes de parear, as notas
do homr que a tab confirma completam a leitura (``completar_com_homr``).

Uso (dentro do container)::

    python -m tab.partitura_pareamento [--ids R01,R02]
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field, replace
from fractions import Fraction
from pathlib import Path

from tab.caminhos import SAIDA
from tab.musicxml import midi_da_corda
from tab.partitura_avaliar import (
    DISTANCIA_AGRUPAMENTO_PX,
    SEMITONS_ESCRITA,
    _carregar_ouro,
    alinhar,
    contar,
)
from tab.partitura_gabarito import _e_nota, ler_partitura

#: Pasta da fase 1 (recortes e leituras do Audiveris).
PASTA_P1 = SAIDA / "partitura" / "p1"

#: Índice dos recortes com margem (``origem``, ``video``, ``tela``, ``caixa_recorte``...).
INDICE = PASTA_P1 / "recortes_margem" / "indice.json"

#: Condição da leitura (MusicXML) e do ``.omr`` usados no pareamento.
CONDICAO_MUSICXML = "x2_margem_herdada"
CONDICAO_OMR = "x2_margem"

#: Saída do pareamento: um JSON por recorte.
PASTA_PAREAMENTO = SAIDA / "partitura" / "p3" / "pareamento"

#: Leitura do homr usada para completar as notas que o Audiveris perdeu.
CONDICAO_HOMR = "nativo"

#: Troca o compasso do Audiveris pelo do homr quando o homr tem pelo menos esse
#: múltiplo das notas (rodada 3024: recupera 25/40 notas com 8 inventadas).
RAZAO_TROCA_HOMR = 2.0


@dataclass
class EventoPartitura:
    """Um instante da partitura: as notas que soam juntas no mesmo ``t_global``.

    Attributes:
        indice: posição do evento na sequência (0-based).
        compasso: número do compasso da partitura.
        t: início no compasso, em semínimas.
        t_global: início no trecho, em semínimas.
        x_quadro: posição x no quadro, ou None se o slot do ``.omr`` não foi achado.
        midis: alturas escritas (MIDI) das notas do evento.
        simbolos: símbolos de ``ler_partitura`` que compõem o evento.
        trocadas: notas do Audiveris tiradas do evento porque a tab as desmente e
            confirma a nota do homr no lugar (guardadas, não apagadas).
    """

    indice: int
    compasso: int
    t: float
    t_global: float
    x_quadro: float | None
    midis: frozenset[int]
    simbolos: list[dict]
    trocadas: list[dict] = field(default_factory=list)


@dataclass
class EventoTab:
    """Um instante da tab: as notas de uma coluna, agrupadas por x.

    Attributes:
        indice: posição do evento na sequência (0-based).
        x_quadro: posição x do evento (ponto médio das notas do grupo).
        midis: alturas escritas (MIDI soado + 12) das notas do evento.
        notas: notas originais da tab, com tudo o que vier do gabarito.
    """

    indice: int
    x_quadro: float
    midis: frozenset[int]
    notas: list[dict]


def x_dos_compassos(omr: Path) -> list[tuple[float, dict[Fraction, float]]]:
    """Lê o ``.omr`` do Audiveris: a posição de cada compasso e de cada slot.

    Args:
        omr: arquivo ``.omr`` (zip com ``sheet#1/sheet#1.xml``).

    Returns:
        Uma tupla ``(left, {time-offset: x-offset})`` por compasso, na ordem do arquivo.
    """
    with zipfile.ZipFile(omr) as arquivo:
        raiz = ET.fromstring(arquivo.read("sheet#1/sheet#1.xml"))
    compassos = []
    for pilha in raiz.iter("stack"):
        slots = {
            Fraction(slot.get("time-offset")): float(slot.get("x-offset"))
            for slot in pilha.iter("slot")
        }
        compassos.append((float(pilha.get("left")), slots))
    return compassos


def _x_do_simbolo(
    simbolo: dict,
    pilha: tuple[float, dict[Fraction, float]] | None,
    x0: float,
    escala: float,
) -> float | None:
    """Posição x no quadro de um símbolo, a partir do slot do compasso dele.

    Args:
        simbolo: símbolo de ``ler_partitura`` (usa ``t``, em semínimas).
        pilha: ``(left, slots)`` do compasso, ou None se o ``.omr`` não tem esse compasso.
        x0: início da janela horizontal do recorte (``caixa_recorte[0]``).
        escala: fator da imagem ampliada (2.0 para a condição ``x2``).

    Returns:
        O x no quadro, ou None se o compasso ou o slot não foram achados.
    """
    if pilha is None:
        return None
    esquerda, slots = pilha
    deslocamento = Fraction(simbolo["t"]).limit_denominator(64) / 4
    if deslocamento not in slots:
        return None
    return x0 + (esquerda + slots[deslocamento]) / escala


def eventos_da_partitura(
    musicxml: Path, omr: Path | None, x0: float, escala: float = 2.0
) -> list[EventoPartitura]:
    """Monta a sequência de eventos da partitura, com o x de cada um no quadro.

    Só entram as notas com altura (sem pausa e sem nota de graça). Notas com o mesmo
    ``t_global`` formam um evento; o x do evento é o primeiro x achado entre elas.

    Args:
        musicxml: leitura da partitura (``score-partwise``, do Audiveris).
        omr: ``.omr`` da mesma imagem, ou None (nesse caso nenhum evento tem x).
        x0: início da janela horizontal do recorte (``caixa_recorte[0]``).
        escala: fator da imagem ampliada em relação ao quadro.

    Returns:
        Eventos em ordem de ``t_global``.
    """
    leitura = ler_partitura(musicxml)
    pilhas = x_dos_compassos(omr) if omr is not None else []
    grupos: dict[float, list[tuple[float | None, dict]]] = {}
    for k, compasso in enumerate(leitura["compassos"]):
        pilha = pilhas[k] if k < len(pilhas) else None
        for simbolo in compasso["simbolos"]:
            if not _e_nota(simbolo):
                continue
            x = _x_do_simbolo(simbolo, pilha, x0, escala)
            chave = round(simbolo["t_global"], 6)
            grupos.setdefault(chave, []).append((x, simbolo))
    eventos = []
    for indice, chave in enumerate(sorted(grupos)):
        membros = grupos[chave]
        xs = [x for x, _ in membros if x is not None]
        simbolos = [simbolo for _, simbolo in membros]
        eventos.append(
            EventoPartitura(
                indice=indice,
                compasso=simbolos[0]["compasso"],
                t=simbolos[0]["t"],
                t_global=chave,
                x_quadro=xs[0] if xs else None,
                midis=frozenset(simbolo["midi"] for simbolo in simbolos),
                simbolos=simbolos,
            )
        )
    return eventos


def eventos_da_tab(notas: list[dict], x0: float, x1: float) -> list[EventoTab]:
    """Monta a sequência de eventos da tab dentro de uma janela em x.

    A regra é a mesma de ``tab.partitura_avaliar.referencia_do_recorte``: cada nota
    vira a altura escrita (MIDI soado + 12), e uma nota a até ``DISTANCIA_AGRUPAMENTO_PX``
    da anterior pertence ao mesmo evento. Notas sem altura (corda fora da afinação)
    ficam de fora.

    Args:
        notas: lista ``notas`` da tela do gabarito.
        x0: início da janela horizontal (``caixa_recorte[0]``).
        x1: fim da janela horizontal (``caixa_recorte[2]``).

    Returns:
        Eventos em ordem de x.
    """
    pontos: list[tuple[float, int, dict]] = []
    for nota in notas:
        x = float(nota["x_centro_quadro"])
        if not x0 <= x <= x1:
            continue
        soado = midi_da_corda(int(nota["corda"]), int(nota["casa"]))
        if soado is None:
            continue
        pontos.append((x, soado + SEMITONS_ESCRITA, nota))
    pontos.sort(key=lambda ponto: (ponto[0], ponto[1]))
    agrupados: list[list[tuple[float, int, dict]]] = []
    for ponto in pontos:
        if agrupados and ponto[0] - agrupados[-1][-1][0] <= DISTANCIA_AGRUPAMENTO_PX:
            agrupados[-1].append(ponto)
        else:
            agrupados.append([ponto])
    eventos = []
    for indice, grupo in enumerate(agrupados):
        xs = [x for x, _, _ in grupo]
        eventos.append(
            EventoTab(
                indice=indice,
                x_quadro=(xs[0] + xs[-1]) / 2,
                midis=frozenset(midi for _, midi, _ in grupo),
                notas=[nota for _, _, nota in grupo],
            )
        )
    return eventos


def _t_inis(notas: list[dict]) -> list[float]:
    """Os ``t_ini`` distintos das notas, em ordem (vazia se as notas não os trazem).

    Args:
        notas: notas originais de um evento da tab.

    Returns:
        Lista ordenada e sem repetição.
    """
    return sorted({nota["t_ini"] for nota in notas if "t_ini" in nota})


def parear(
    partitura: list[EventoPartitura],
    tab: list[EventoTab],
    tolerancia_px: float | None,
) -> list[dict]:
    """Pareia cada evento da partitura com um evento da tab, e confere o x.

    O alinhamento é o Needleman-Wunsch de ``alinhar``, com Jaccard sobre as alturas.
    O tempo de uma nota da partitura é o ``t_ini`` da coluna da tab pareada.

    Args:
        partitura: eventos da partitura, em ordem.
        tab: eventos da tab, em ordem.
        tolerancia_px: tolerância de x para ``confere_x``, ou None para não conferir.

    Returns:
        Uma linha por evento da partitura, com ``indice``, ``compasso``, ``t``,
        ``x_quadro``, ``par_tab`` (índice do evento da tab ou None), ``x_tab``,
        ``distancia_x``, ``confere_x`` (True, False ou None se falta x ou tolerância)
        e ``t_ini`` (lista ordenada dos ``t_ini`` da coluna pareada).
    """
    operacoes = alinhar(
        [evento.midis for evento in partitura], [evento.midis for evento in tab]
    )
    par_de = {i: j for op, i, j in operacoes if op == "casa"}
    linhas = []
    for i, evento in enumerate(partitura):
        j = par_de.get(i)
        par = tab[j] if j is not None else None
        x_tab = par.x_quadro if par is not None else None
        distancia = None
        if evento.x_quadro is not None and x_tab is not None:
            distancia = abs(evento.x_quadro - x_tab)
        confere = None
        if distancia is not None and tolerancia_px is not None:
            confere = distancia <= tolerancia_px
        linhas.append(
            {
                "indice": evento.indice,
                "compasso": evento.compasso,
                "t": evento.t,
                "x_quadro": evento.x_quadro,
                "par_tab": j,
                "x_tab": x_tab,
                "distancia_x": distancia,
                "confere_x": confere,
                "t_ini": _t_inis(par.notas) if par is not None else [],
            }
        )
    return linhas


def completar_com_homr(
    partitura: list[EventoPartitura],
    homr: list[EventoPartitura],
    tab: list[EventoTab],
) -> tuple[list[EventoPartitura], int]:
    """Acrescenta à partitura as notas do homr que a tab confirma (rodada 3006).

    As duas leituras são alinhadas, cada uma, com a tab. Uma nota da tab que a
    partitura não cobre entra se o evento do homr casado com a mesma coluna tem essa
    altura. Ela vai para o evento da partitura casado com a coluna; se a coluna não
    tem evento da partitura, vira um evento novo, com o x da tab. Toda nota ganha
    ``origem`` (``audiveris`` ou ``homr``). Nota que a tab não confirma não entra, então
    a junção não inventa nota.

    Quando o homr completa um evento, as notas do Audiveris desse evento que a coluna
    da tab não tem saem para ``trocadas`` (rodada 3012): a tab desmente a altura lida e
    confirma a do homr no mesmo instante. Nota igual à da tab em outra oitava
    (harmônico, 8va) não é trocada (rodada 3013).

    Args:
        partitura: eventos da leitura principal (Audiveris), em ordem.
        homr: eventos da leitura do homr, em ordem (sem x).
        tab: eventos da tab, em ordem.

    Returns:
        ``(eventos, acrescimos)``: a sequência completada, reindexada em ordem, e
        quantas notas vieram do homr.
    """
    alvo = [evento.midis for evento in tab]
    par_da_tab = {
        j: i for op, i, j in alinhar([e.midis for e in partitura], alvo) if op == "casa"
    }
    homr_da_tab = {
        j: i for op, i, j in alinhar([e.midis for e in homr], alvo) if op == "casa"
    }
    novos = [
        EventoPartitura(
            indice=e.indice,
            compasso=e.compasso,
            t=e.t,
            t_global=e.t_global,
            x_quadro=e.x_quadro,
            midis=e.midis,
            simbolos=[{**s, "origem": "audiveris"} for s in e.simbolos],
        )
        for e in partitura
    ]
    criados: list[tuple[int, EventoPartitura]] = []
    acrescimos = 0
    for j, coluna in enumerate(tab):
        if j not in homr_da_tab:
            continue
        i = par_da_tab.get(j)
        cobertas = novos[i].midis if i is not None else frozenset()
        do_homr = homr[homr_da_tab[j]]
        extras = [
            {**s, "origem": "homr"}
            for s in do_homr.simbolos
            if s["midi"] in coluna.midis - cobertas
        ]
        if not extras:
            continue
        acrescimos += len(extras)
        midis = frozenset(s["midi"] for s in extras)
        if i is not None:
            evento = novos[i]
            evento.trocadas = [
                s for s in evento.simbolos if _desmentida(s["midi"], coluna.midis)
            ]
            evento.simbolos = [
                s for s in evento.simbolos if not _desmentida(s["midi"], coluna.midis)
            ]
            evento.simbolos.extend(extras)
            evento.midis = frozenset(s["midi"] for s in evento.simbolos)
        else:
            criados.append(
                (
                    j,
                    EventoPartitura(
                        indice=-1,
                        compasso=do_homr.compasso,
                        t=do_homr.t,
                        t_global=do_homr.t_global,
                        x_quadro=coluna.x_quadro,
                        midis=midis,
                        simbolos=extras,
                    ),
                )
            )
    # Evento criado entra logo depois do último evento da partitura casado com uma
    # coluna anterior à dele.
    posicoes = [(float(i), -1, e) for i, e in enumerate(novos)]
    for j, evento in criados:
        anteriores = [i for jj, i in par_da_tab.items() if jj < j]
        posicoes.append(((max(anteriores) if anteriores else -1) + 0.5, j, evento))
    ordenados = sorted(posicoes, key=lambda item: (item[0], item[1]))
    eventos = [item[2] for item in ordenados]
    for indice, evento in enumerate(eventos):
        evento.indice = indice
    return eventos, acrescimos


def _posicoes(numeros: list[int]) -> dict[int, int]:
    """Posição de cada número de compasso na lista (a primeira, se repetido).

    Args:
        numeros: números dos compassos de uma leitura, na ordem.

    Returns:
        Mapa número do compasso -> posição k.
    """
    posicao: dict[int, int] = {}
    for k, numero in enumerate(numeros):
        posicao.setdefault(numero, k)
    return posicao


def trocar_compassos_pelo_homr(
    audiveris: list[EventoPartitura],
    numeros_audiveris: list[int],
    homr: list[EventoPartitura],
    numeros_homr: list[int],
    razao: float = RAZAO_TROCA_HOMR,
) -> tuple[list[EventoPartitura], list[int]]:
    """Troca o compasso do Audiveris pelo do homr quando o homr lê bem mais notas.

    Regra da rodada 3024. Para cada posição ``k``, conta-se os símbolos do Audiveris no
    compasso ``numeros_audiveris[k]`` e os do homr no compasso ``numeros_homr[k]``. Se o
    homr tem mais símbolos e pelo menos ``razao`` vezes os do Audiveris, o compasso do
    Audiveris sai e entra o do homr, renumerado para ``numeros_audiveris[k]``. Sem
    tablatura a nota do homr não tem confirmação, por isso essas notas saem com
    ``origem`` ``homr_sem_confirmacao``. O x fica None, porque o homr não tem ``.omr``.
    Evento do Audiveris cujo compasso não está em ``numeros_audiveris`` vai para o fim.

    Com contagens de compassos diferentes entre as duas leituras, nada é trocado e a
    lista de entrada volta intacta. Nenhum objeto de entrada é alterado.

    Args:
        audiveris: eventos do Audiveris, em ordem.
        numeros_audiveris: número de cada compasso do Audiveris, na ordem (com os vazios).
        homr: eventos do homr, em ordem.
        numeros_homr: número de cada compasso do homr, na ordem (com os vazios).
        razao: múltiplo mínimo de notas do homr sobre as do Audiveris para trocar.

    Returns:
        ``(eventos, trocados)``: os eventos em ordem de (posição do compasso, ``t``), com
        ``indice`` de 0 a n-1, e os números dos compassos do Audiveris trocados, em ordem.
    """
    if len(numeros_audiveris) != len(numeros_homr):
        return audiveris, []
    posicao_aud = _posicoes(numeros_audiveris)
    posicao_homr = _posicoes(numeros_homr)
    na = [0] * len(numeros_audiveris)
    nh = [0] * len(numeros_audiveris)
    for evento in audiveris:
        k = posicao_aud.get(evento.compasso)
        if k is not None:
            na[k] += len(evento.simbolos)
    for evento in homr:
        k = posicao_homr.get(evento.compasso)
        if k is not None:
            nh[k] += len(evento.simbolos)
    trocar = {k for k in range(len(na)) if nh[k] > na[k] and nh[k] >= razao * na[k]}
    fora = len(numeros_audiveris)
    saida: list[tuple[int, float, EventoPartitura]] = []
    for evento in audiveris:
        k = posicao_aud.get(evento.compasso, fora)
        if k not in trocar:
            saida.append((k, evento.t, evento))
    for evento in homr:
        k = posicao_homr.get(evento.compasso)
        if k is None or k not in trocar:
            continue
        compasso = numeros_audiveris[k]
        copia = replace(
            evento,
            compasso=compasso,
            x_quadro=None,
            trocadas=[],
            simbolos=[
                {**s, "compasso": compasso, "origem": "homr_sem_confirmacao"}
                for s in evento.simbolos
            ],
        )
        saida.append((k, evento.t, copia))
    saida.sort(key=lambda item: (item[0], item[1]))
    eventos = [replace(evento, indice=i) for i, (_, _, evento) in enumerate(saida)]
    trocados = [numeros_audiveris[k] for k in sorted(trocar)]
    return eventos, trocados


def _desmentida(midi: int, coluna_midis: frozenset[int]) -> bool:
    """Diz se a tab desmente uma altura lida: nem ela nem a sua classe estão na coluna.

    Nota igual à da tab em outra oitava (harmônico, 8va) não é desmentida.

    Args:
        midi: altura escrita (MIDI) da nota lida.
        coluna_midis: alturas escritas das notas da coluna da tab.

    Returns:
        True se nenhuma nota da coluna tem a mesma altura nem a mesma classe de altura.
    """
    return midi not in coluna_midis and all(m % 12 != midi % 12 for m in coluna_midis)


def _gabarito_do_video(video: str, ouro: dict[str, list[dict]]) -> dict:
    """O gabarito único de um vídeo do ouro.

    Args:
        video: campo ``video`` do índice.
        ouro: mapa ``video`` -> gabaritos, de ``_carregar_ouro``.

    Returns:
        O gabarito do vídeo.

    Raises:
        ValueError: se o vídeo não tem exatamente um gabarito.
    """
    candidatos = ouro[video]
    if len(candidatos) != 1:
        raise ValueError(f"vídeo com {len(candidatos)} gabaritos: {video}")
    return candidatos[0]


def _parear_recorte(entrada: dict, ouro: dict[str, list[dict]]) -> dict:
    """Pareia um recorte do índice e devolve o documento que vai para o JSON.

    Args:
        entrada: item do índice (``id``, ``video``, ``tela``, ``caixa_recorte``...).
        ouro: mapa ``video`` -> gabaritos.

    Returns:
        Documento com ``partitura``, ``tab``, ``pares`` e ``resumo``.
    """
    rid = entrada["id"]
    x0, _, x1, _ = entrada["caixa_recorte"]
    gabarito = _gabarito_do_video(entrada["video"], ouro)
    tela = next(t for t in gabarito["telas"] if t["id"] == entrada["tela"])
    partitura = eventos_da_partitura(
        PASTA_P1 / "omr" / "audiveris" / CONDICAO_MUSICXML / rid / "saida.musicxml",
        PASTA_P1 / "omr" / "audiveris" / CONDICAO_OMR / rid / "entrada.omr",
        x0,
    )
    tab = eventos_da_tab(tela["notas"], x0, x1)
    homr = eventos_da_partitura(
        PASTA_P1 / "omr" / "homr" / CONDICAO_HOMR / rid / "saida.musicxml", None, x0
    )
    referencia = [evento.midis for evento in tab]
    antes, _ = contar([e.midis for e in partitura], referencia, "exato")
    partitura, acrescimos = completar_com_homr(partitura, homr, tab)
    depois, _ = contar([e.midis for e in partitura], referencia, "exato")
    tolerancia = float(entrada["entrelinha"])
    pares = parear(partitura, tab, tolerancia)
    distancias = sorted(p["distancia_x"] for p in pares if p["distancia_x"] is not None)
    return {
        "id": rid,
        "video": entrada["video"],
        "tela": entrada["tela"],
        "caixa_recorte": entrada["caixa_recorte"],
        "tolerancia_px": tolerancia,
        "partitura": [
            {
                "indice": e.indice,
                "compasso": e.compasso,
                "t": e.t,
                "t_global": e.t_global,
                "x_quadro": e.x_quadro,
                "midis": sorted(e.midis),
                "simbolos": e.simbolos,
                "trocadas": e.trocadas,
            }
            for e in partitura
        ],
        "tab": [
            {
                "indice": e.indice,
                "x_quadro": e.x_quadro,
                "midis": sorted(e.midis),
                "notas": e.notas,
            }
            for e in tab
        ],
        "pares": pares,
        "resumo": {
            "eventos_partitura": len(partitura),
            "eventos_tab": len(tab),
            "pares": sum(p["par_tab"] is not None for p in pares),
            "com_x_conferido": sum(p["confere_x"] is True for p in pares),
            "mediana_distancia_px": (
                round(distancias[len(distancias) // 2], 2) if distancias else None
            ),
            "acrescimos_homr": acrescimos,
            "trocadas_pela_tab": sum(len(e.trocadas) for e in partitura),
            "tab_antes": antes,
            "tab_depois": depois,
        },
    }


def _ler_argumentos(argv: list[str] | None) -> argparse.Namespace:
    """Lê as opções da CLI.

    Args:
        argv: argumentos da linha de comando, ou None para usar ``sys.argv``.

    Returns:
        Os argumentos já lidos.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ids",
        help="recortes separados por vírgula (padrão: todos os de origem 'ouro')",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI: pareia os recortes, grava o JSON e imprime o resumo.

    Args:
        argv: argumentos da linha de comando.

    Returns:
        0 ao terminar.
    """
    args = _ler_argumentos(argv)
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    entradas = [e for e in indice if e["origem"] == "ouro"]
    if args.ids:
        pedidos = [rid.strip() for rid in args.ids.split(",") if rid.strip()]
        por_id = {e["id"]: e for e in entradas}
        ausentes = [rid for rid in pedidos if rid not in por_id]
        if ausentes:
            raise SystemExit(f"recorte(s) fora do ouro: {', '.join(ausentes)}")
        entradas = [por_id[rid] for rid in pedidos]
    ouro = _carregar_ouro()
    PASTA_PAREAMENTO.mkdir(parents=True, exist_ok=True)
    total = {"pares": 0, "com_x": 0, "acrescimos_homr": 0, "trocadas": 0}
    tab_antes: dict[str, int] = {}
    tab_depois: dict[str, int] = {}
    for entrada in entradas:
        documento = _parear_recorte(entrada, ouro)
        resumo = documento["resumo"]
        destino = PASTA_PAREAMENTO / f"{entrada['id']}.json"
        destino.write_text(
            json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        total["pares"] += resumo["pares"]
        total["com_x"] += resumo["com_x_conferido"]
        total["acrescimos_homr"] += resumo["acrescimos_homr"]
        total["trocadas"] += resumo["trocadas_pela_tab"]
        for chave, valor in resumo["tab_antes"].items():
            tab_antes[chave] = tab_antes.get(chave, 0) + valor
        for chave, valor in resumo["tab_depois"].items():
            tab_depois[chave] = tab_depois.get(chave, 0) + valor
        print(
            f"{entrada['id']} eventos partitura {resumo['eventos_partitura']} "
            f"eventos tab {resumo['eventos_tab']} pares {resumo['pares']} "
            f"com x conferido {resumo['com_x_conferido']} "
            f"(mediana {resumo['mediana_distancia_px']}, "
            f"tol {documento['tolerancia_px']:.1f} px)"
        )
    print(
        f"total: pares {total['pares']}, com x conferido {total['com_x']}, "
        f"notas do homr {total['acrescimos_homr']}, "
        f"trocadas pela tab {total['trocadas']}"
    )
    print(f"tab antes:  {tab_antes}")
    print(f"tab depois: {tab_depois}")
    print(f"gravado em {PASTA_PAREAMENTO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
