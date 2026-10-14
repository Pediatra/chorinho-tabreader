"""Avalia as leituras de OMR (homr, audiveris, oemer) contra a tablatura do ouro, por nota.

Lê os MusicXML gerados por ``tab.partitura_omr``, transforma cada um em uma sequência de
eventos (um evento = o conjunto de alturas que começam no mesmo instante) e compara com a
referência tirada do gabarito de tablatura (``data/gold/ouro_video``), só para os recortes
de origem ``ouro`` (R01–R12). A comparação é feita de duas maneiras: por altura exata
(MIDI) e por classe de altura (MIDI mod 12), para separar erro de nota de erro de oitava.

A referência soa uma oitava abaixo da escrita, então a altura escrita é o MIDI soado + 12.

Para os recortes sem gabarito (R13–R21) a avaliação só registra se houve saída, quantas
notas e quantos compassos.

Saída: ``data/saida/partitura/p1/omr/avaliacao.json`` e a tabela no terminal.

Uso:
    python -m tab.partitura_avaliar
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from tab.caminhos import OURO_VIDEO, RAIZ, SAIDA
from tab.musicxml import midi_da_corda

#: Pasta das saídas do OMR (``<biblioteca>/<condicao>/``) e do índice dos recortes.
PASTA_OMR = SAIDA / "partitura" / "p1" / "omr"
PASTA_RECORTES = SAIDA / "partitura" / "p1" / "recortes"

#: Arquivo consolidado da avaliação.
AVALIACAO = PASTA_OMR / "avaliacao.json"

#: Semitons de cada nota natural a partir de dó (MIDI mod 12).
SEMITONS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

#: Notas da tablatura a menos de tantos px da anterior são um mesmo instante.
DISTANCIA_AGRUPAMENTO_PX = 6.0

#: Violão soa uma oitava abaixo da escrita: altura escrita = soada + 12.
SEMITONS_ESCRITA = 12

#: Tolerância para comparar custos de float no traceback do alinhamento.
EPSILON = 1e-9

#: Ordem das combinações na saída e na tabela.
BIBLIOTECAS = ("homr", "audiveris", "oemer")
CONDICOES = (
    "nativo",
    "x2",
    "x3",
    "x4",
    "x2_binaria",
    "x2_margem",
    "x2_cabecalho",
)

#: Um evento é um conjunto de alturas (MIDI, ou classes 0–11) que soam juntas.
Evento = frozenset


@dataclass(frozen=True)
class NotaXML:
    """Uma nota lida do MusicXML.

    Attributes:
        parte: número da ``part`` (1-based).
        compasso: atributo ``number`` do ``measure``.
        t: instante de início, em semínimas, desde o começo da parte.
        midi: altura escrita em clave de sol simples, em MIDI.
        duracao: duração em semínimas (0 para nota de graça).
        tipo: texto de ``type`` (figura), ou None.
        pontuada: se há ``<dot/>``.
        ornamento: True para nota de graça (``<grace/>``).
        pauta: número do ``staff`` (1 se ausente).
    """

    parte: int
    compasso: str
    t: float
    midi: int
    duracao: float
    tipo: str | None
    pontuada: bool
    ornamento: bool
    pauta: int


@dataclass
class PartituraXML:
    """Resultado do parser de um MusicXML.

    Attributes:
        partes: quantas ``part`` o arquivo tem.
        compassos: maior número de ``measure`` entre as partes.
        notas: todas as notas com altura, de todas as partes.
        alertas: transposição (registrada, não aplicada) e oitavas de clave (aplicadas).
    """

    partes: int
    compassos: int
    notas: list[NotaXML]
    alertas: list[str] = field(default_factory=list)


def _midi_do_pitch(pitch: ET.Element) -> int:
    """Converte um elemento ``<pitch>`` em MIDI.

    Args:
        pitch: elemento ``pitch`` com ``step``, ``octave`` e opcionalmente ``alter``.

    Returns:
        Altura MIDI: 12 * (octave + 1) + semitons da nota + alteração.
    """
    step = pitch.findtext("step", "").strip()
    octava = int(pitch.findtext("octave", "4"))
    alteracao = pitch.findtext("alter")
    alter = round(float(alteracao)) if alteracao is not None else 0
    return 12 * (octava + 1) + SEMITONS[step] + alter


def _ler_parte(
    parte: ET.Element, numero: int, alertas: list[str]
) -> tuple[list[NotaXML], int]:
    """Lê uma ``part``: percorre os compassos e mantém o tempo corrente.

    Args:
        parte: elemento ``part``.
        numero: número da parte (1-based), para os registros.
        alertas: lista onde são anotadas transposição e oitavas de clave.
            A oitava de clave (``clef-octave-change``) é aplicada: a altura volta
            para a escrita em clave de sol simples. A transposição não é aplicada.

    Returns:
        ``(notas, compassos)`` da parte.
    """
    divisions = 1.0
    base = 0.0
    oitava_clave: dict[str, int] = {}
    notas: list[NotaXML] = []
    compassos = parte.findall("measure")
    for compasso in compassos:
        nome = compasso.get("number", "?")
        cursor = 0.0
        fim = 0.0
        inicio_anterior: float | None = None
        for filho in compasso:
            if filho.tag == "attributes":
                if filho.findtext("divisions"):
                    divisions = float(filho.findtext("divisions"))
                for transposicao in filho.findall("transpose"):
                    oitava = transposicao.findtext("octave-change")
                    if oitava and int(oitava) != 0:
                        alertas.append(
                            f"parte {numero} compasso {nome}: "
                            f"transpose octave-change={oitava} (não aplicado)"
                        )
                for clave in filho.findall("clef"):
                    oitava = clave.findtext("clef-octave-change")
                    oitava_clave[clave.get("number", "1")] = int(oitava or 0)
                    if oitava and int(oitava) != 0:
                        alertas.append(
                            f"parte {numero} compasso {nome}: "
                            f"clef-octave-change={oitava} (aplicado)"
                        )
            elif filho.tag == "backup":
                cursor -= float(filho.findtext("duration", "0")) / divisions
            elif filho.tag == "forward":
                cursor += float(filho.findtext("duration", "0")) / divisions
                fim = max(fim, cursor)
            elif filho.tag == "note":
                duracao_el = filho.findtext("duration")
                duracao = float(duracao_el) / divisions if duracao_el else 0.0
                grace = filho.find("grace") is not None
                acorde = filho.find("chord") is not None
                if acorde and inicio_anterior is not None:
                    inicio = inicio_anterior
                else:
                    inicio = cursor
                pitch = filho.find("pitch")
                if pitch is not None:
                    pauta = filho.findtext("staff", "1")
                    # Clave com 8 embaixo: o MusicXML grava a altura soada; a
                    # referência é a escrita na clave de sol simples.
                    escrita = _midi_do_pitch(pitch) - 12 * oitava_clave.get(pauta, 0)
                    notas.append(
                        NotaXML(
                            parte=numero,
                            compasso=nome,
                            t=base + inicio,
                            midi=escrita,
                            duracao=0.0 if grace else duracao,
                            tipo=filho.findtext("type"),
                            pontuada=filho.find("dot") is not None,
                            ornamento=grace,
                            pauta=int(pauta),
                        )
                    )
                if not acorde:
                    inicio_anterior = cursor
                    if not grace:
                        cursor += duracao
                fim = max(fim, cursor)
        base += fim
    return notas, len(compassos)


def ler_musicxml(caminho: Path) -> PartituraXML:
    """Lê um MusicXML ``score-partwise`` e devolve as notas com seus instantes.

    O tempo é contado em semínimas (``duration / divisions``). Acorde (``<chord/>``)
    começa no mesmo instante da nota anterior e não avança o tempo. ``<backup>`` volta
    e ``<forward>`` avança. Ao fim de cada compasso, o próximo começa no maior tempo
    atingido. Se há mais de uma parte, cada uma é lida do próprio zero.

    Args:
        caminho: arquivo ``.musicxml``.

    Returns:
        A partitura lida, com as alertas de transposição e oitava de clave.

    Raises:
        ValueError: se a raiz não é ``score-partwise``.
        xml.etree.ElementTree.ParseError: se o XML não abre.
    """
    raiz = ET.parse(caminho).getroot()
    if raiz.tag != "score-partwise":
        raise ValueError(f"raiz {raiz.tag!r}, esperado score-partwise")
    alertas: list[str] = []
    notas: list[NotaXML] = []
    compassos = 0
    partes = raiz.findall("part")
    for numero, parte in enumerate(partes, start=1):
        notas_da_parte, n_compassos = _ler_parte(parte, numero, alertas)
        notas.extend(notas_da_parte)
        compassos = max(compassos, n_compassos)
    pautas = {n.pauta for n in notas}
    if len(pautas) > 1:
        alertas.append(f"mais de uma pauta nas notas: {sorted(pautas)}")
    return PartituraXML(
        partes=len(partes), compassos=compassos, notas=notas, alertas=alertas
    )


def eventos_da_biblioteca(notas: list[NotaXML]) -> list[Evento]:
    """Agrupa as notas da biblioteca por instante de início.

    Notas de graça (``ornamento``) não entram na sequência: a referência não as tem.

    Args:
        notas: notas lidas do MusicXML.

    Returns:
        Lista de conjuntos de alturas MIDI, na ordem do tempo.
    """
    por_instante: dict[float, set[int]] = {}
    for nota in notas:
        if nota.ornamento:
            continue
        por_instante.setdefault(round(nota.t, 6), set()).add(nota.midi)
    return [frozenset(por_instante[t]) for t in sorted(por_instante)]


def referencia_do_recorte(
    notas_da_tela: list[dict], x0: float, x1: float
) -> list[Evento]:
    """Monta a sequência de referência de uma tela do ouro, dentro de uma janela em x.

    Cada nota vira a altura escrita (MIDI soado + 12). As notas são ordenadas por
    ``x_centro_quadro`` e agrupadas em instantes: uma nota a até 6 px da anterior
    pertence ao mesmo instante.

    Args:
        notas_da_tela: lista ``notas`` da tela do gabarito.
        x0: início da janela horizontal (``caixa_recorte[0]``).
        x1: fim da janela horizontal (``caixa_recorte[2]``).

    Returns:
        Lista de conjuntos de alturas MIDI escritas, na ordem de x.
    """
    pontos: list[tuple[float, int]] = []
    for nota in notas_da_tela:
        x = float(nota["x_centro_quadro"])
        if not x0 <= x <= x1:
            continue
        soado = midi_da_corda(int(nota["corda"]), int(nota["casa"]))
        if soado is None:
            continue
        pontos.append((x, soado + SEMITONS_ESCRITA))
    pontos.sort()
    grupos: list[tuple[float, set[int]]] = []
    for x, midi in pontos:
        if grupos and x - grupos[-1][0] <= DISTANCIA_AGRUPAMENTO_PX:
            grupos[-1] = (x, grupos[-1][1] | {midi})
        else:
            grupos.append((x, {midi}))
    return [frozenset(conjunto) for _, conjunto in grupos]


def _custo(a: Evento, b: Evento) -> float:
    """Custo de casar dois eventos: 1 - Jaccard das alturas.

    Args:
        a: evento da biblioteca.
        b: evento da referência.

    Returns:
        Valor em [0, 1]; 0 é igual.
    """
    uniao = len(a | b)
    if uniao == 0:
        return 1.0
    return 1.0 - len(a & b) / uniao


def alinhar(lib: list[Evento], ref: list[Evento]) -> list[tuple[str, int, int]]:
    """Alinhamento global (Needleman-Wunsch) entre duas sequências de eventos.

    Casar dois eventos custa ``1 - Jaccard``; pular um evento de qualquer lado custa 1.
    No empate, o traceback prefere casar (diagonal), depois pular da biblioteca.

    Args:
        lib: sequência da biblioteca.
        ref: sequência da referência.

    Returns:
        Lista de operações ``(op, i, j)`` na ordem da sequência, com ``op`` em
        ``casa`` (i, j), ``inv`` (só i, da biblioteca) e ``fal`` (só j, da referência).
        Índices ausentes valem -1.
    """
    n, m = len(lib), len(ref)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = float(i)
    for j in range(1, m + 1):
        dp[0][j] = float(j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = min(
                dp[i - 1][j - 1] + _custo(lib[i - 1], ref[j - 1]),
                dp[i - 1][j] + 1.0,
                dp[i][j - 1] + 1.0,
            )
    ops: list[tuple[str, int, int]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if (
            i > 0
            and j > 0
            and abs(dp[i][j] - (dp[i - 1][j - 1] + _custo(lib[i - 1], ref[j - 1])))
            < EPSILON
        ):
            ops.append(("casa", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and abs(dp[i][j] - (dp[i - 1][j] + 1.0)) < EPSILON:
            ops.append(("inv", i - 1, -1))
            i -= 1
        else:
            ops.append(("fal", -1, j - 1))
            j -= 1
    ops.reverse()
    return ops


def _distancia_exata(a: int, b: int) -> int:
    """Distância em semitons entre duas alturas MIDI."""
    return abs(a - b)


def _distancia_classe(a: int, b: int) -> int:
    """Distância circular entre duas classes de altura (0–11)."""
    d = abs(a - b) % 12
    return min(d, 12 - d)


def contar(
    lib: list[Evento],
    ref: list[Evento],
    modo: str,
) -> tuple[dict[str, int], list[tuple[int, int]]]:
    """Conta, por nota, certas, altura errada, faltando e inventada.

    ``modo`` é ``exato`` (MIDI) ou ``classe`` (MIDI mod 12). Os conjuntos são
    convertidos para o modo antes do alinhamento. Dentro de um par de eventos casados,
    as sobras de cada lado são emparelhadas uma a uma por proximidade (guloso, pela
    menor distância primeiro): cada par vira ``altura_errada``; a sobra da biblioteca é
    ``inventada`` e a da referência é ``faltando``. Eventos não casados contam inteiros.

    Args:
        lib: sequência da biblioteca (MIDI).
        ref: sequência da referência (MIDI).
        modo: ``exato`` ou ``classe``.

    Returns:
        ``(contagens, pares)``, em que ``contagens`` tem ``referencia``, ``certas``,
        ``altura_errada``, ``faltando`` e ``inventada``, e ``pares`` lista
        ``(altura_biblioteca, altura_referencia)`` de cada altura errada (no modo exato
        é o histograma de deslocamento).

    Raises:
        ValueError: se ``modo`` não é ``exato`` nem ``classe``.
    """
    if modo == "exato":
        distancia = _distancia_exata
        lib_m = lib
        ref_m = ref
    elif modo == "classe":
        distancia = _distancia_classe
        lib_m = [frozenset(x % 12 for x in e) for e in lib]
        ref_m = [frozenset(x % 12 for x in e) for e in ref]
    else:
        raise ValueError(f"modo desconhecido: {modo}")

    cont = {
        "referencia": sum(len(e) for e in ref_m),
        "certas": 0,
        "altura_errada": 0,
        "faltando": 0,
        "inventada": 0,
    }
    pares: list[tuple[int, int]] = []
    for op, i, j in alinhar(lib_m, ref_m):
        if op == "inv":
            cont["inventada"] += len(lib_m[i])
        elif op == "fal":
            cont["faltando"] += len(ref_m[j])
        else:
            a, b = lib_m[i], ref_m[j]
            cont["certas"] += len(a & b)
            sobra_a = sorted(a - b)
            sobra_b = sorted(b - a)
            candidatos = sorted(
                (distancia(x, y), x, y) for x in sobra_a for y in sobra_b
            )
            usados_a: set[int] = set()
            usados_b: set[int] = set()
            for _, x, y in candidatos:
                if x in usados_a or y in usados_b:
                    continue
                usados_a.add(x)
                usados_b.add(y)
                cont["altura_errada"] += 1
                pares.append((x, y))
            cont["inventada"] += len(sobra_a) - len(usados_a)
            cont["faltando"] += len(sobra_b) - len(usados_b)
    return cont, pares


def somar(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    """Soma duas contagens campo a campo.

    Args:
        a: contagem acumulada.
        b: contagem a somar.

    Returns:
        Nova contagem com a soma.
    """
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def _zero() -> dict[str, int]:
    """Contagem zerada, com os campos de ``contar``."""
    return {
        "referencia": 0,
        "certas": 0,
        "altura_errada": 0,
        "faltando": 0,
        "inventada": 0,
    }


def _carregar_ouro() -> dict[str, list[dict]]:
    """Lê os gabaritos de tablatura, indexados pelo campo ``video``.

    Dois arquivos podem declarar o mesmo vídeo (versões do mesmo gabarito); o erro só
    aparece se um recorte ouro usar esse vídeo (ver ``_referencia_do_item``).

    Returns:
        Mapa ``video`` -> lista de JSONs de gabarito que declaram esse vídeo.
    """
    mapa: dict[str, list[dict]] = {}
    for caminho in sorted(OURO_VIDEO.glob("*.json")):
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        mapa.setdefault(dados["video"], []).append(dados)
    return mapa


def _referencia_do_item(item: dict, ouro: dict[str, list[dict]]) -> list[Evento]:
    """Referência do recorte ``ouro``, a partir da tela e da caixa dele.

    Args:
        item: entrada do índice com ``video``, ``tela`` e ``caixa_recorte``.
        ouro: mapa ``video`` -> gabaritos.

    Returns:
        Sequência de referência do recorte.

    Raises:
        ValueError: se o vídeo tem mais de um gabarito.
        StopIteration: se a tela não existe no gabarito.
    """
    candidatos = ouro[item["video"]]
    if len(candidatos) != 1:
        raise ValueError(f"vídeo com {len(candidatos)} gabaritos: {item['video']}")
    gabarito = candidatos[0]
    tela = next(t for t in gabarito["telas"] if t["id"] == item["tela"])
    x0, _, x1, _ = item["caixa_recorte"]
    return referencia_do_recorte(tela["notas"], x0, x1)


def _rotulo_video(video: str) -> str:
    """Nome curto do vídeo para as tabelas (o trecho depois da barra do canal)."""
    return video.split("/", 1)[-1].removesuffix(".mp4")[:48]


def avaliar_combinacao(
    biblioteca: str,
    condicao: str,
    indice: list[dict],
    ouro: dict[str, list[dict]],
) -> dict | None:
    """Avalia uma combinação biblioteca × condição sobre todos os recortes.

    Args:
        biblioteca: ``homr``, ``audiveris`` ou ``oemer``.
        condicao: ``nativo`` ou ``x2``.
        indice: entradas de ``indice.json``.
        ouro: mapa ``video`` -> gabaritos.

    Returns:
        Dict com totais e por recorte (exato e classe), histograma de deslocamento,
        tempos, falhas e alertas; None se a combinação ainda não foi rodada.
    """
    pasta = PASTA_OMR / biblioteca / condicao
    caminho_exec = pasta / "execucao.json"
    if not caminho_exec.exists():
        return None
    execucoes = {
        r["id"]: r for r in json.loads(caminho_exec.read_text(encoding="utf-8"))
    }
    resultado: dict = {
        "exato": {"total": _zero(), "por_video": {}, "por_recorte": {}},
        "classe": {"total": _zero(), "por_video": {}, "por_recorte": {}},
        "deslocamento": {"total": {}, "por_video": {}},
        "tempo": {},
        "falhas": [],
        "alertas": {},
        "partes": {},
        "sem_referencia": {},
    }
    tempos: list[float] = []
    for item in indice:
        id_ = item["id"]
        exec_ = execucoes.get(id_)
        if exec_ is None:
            resultado["falhas"].append({"id": id_, "motivo": "não rodado"})
            continue
        tempos.append(float(exec_["segundos"]))
        notas: list[NotaXML] = []
        if exec_["ok"]:
            try:
                partitura = ler_musicxml(RAIZ / exec_["saida"])
            except (ET.ParseError, ValueError, KeyError) as erro:
                # Saída ilegível conta como falha: a referência inteira fica faltando.
                resultado["falhas"].append(
                    {"id": id_, "motivo": f"MusicXML ilegível: {erro}"}
                )
            else:
                notas = partitura.notas
                resultado["partes"][id_] = partitura.partes
                if partitura.alertas:
                    resultado["alertas"][id_] = partitura.alertas
                resultado["sem_referencia"][id_] = {
                    "saida": True,
                    "notas": sum(1 for n in notas if not n.ornamento),
                    "compassos": partitura.compassos,
                }
        else:
            resultado["falhas"].append({"id": id_, "motivo": exec_["motivo"]})
            resultado["sem_referencia"][id_] = {
                "saida": False,
                "notas": 0,
                "compassos": 0,
            }
        if item["origem"] != "ouro":
            continue
        lib = eventos_da_biblioteca(notas)
        ref = _referencia_do_item(item, ouro)
        video = _rotulo_video(item["video"])
        for modo, chave in (("exato", "exato"), ("classe", "classe")):
            cont, pares = contar(lib, ref, modo)
            bloco = resultado[chave]
            bloco["total"] = somar(bloco["total"], cont)
            bloco["por_recorte"][id_] = cont
            bloco["por_video"][video] = somar(
                bloco["por_video"].get(video, _zero()), cont
            )
            if modo == "exato":
                resultado["deslocamento"]["total"] = _somar_histograma(
                    resultado["deslocamento"]["total"], pares
                )
                resultado["deslocamento"]["por_video"][video] = _somar_histograma(
                    resultado["deslocamento"]["por_video"].get(video, {}), pares
                )
    resultado["tempo"] = {
        "n": len(tempos),
        "media": round(sum(tempos) / len(tempos), 2) if tempos else None,
        "max": round(max(tempos), 2) if tempos else None,
    }
    return resultado


def _somar_histograma(
    hist: dict[str, int], pares: list[tuple[int, int]]
) -> dict[str, int]:
    """Soma pares (biblioteca, referência) num histograma de deslocamento em semitons.

    Args:
        hist: histograma acumulado, com chaves ``"+k"`` ou ``"-k"`` (texto).
        pares: pares ``(altura_biblioteca, altura_referencia)`` de alturas erradas.

    Returns:
        Novo histograma.
    """
    contagem = Counter(hist)
    for lib, ref in pares:
        delta = lib - ref
        contagem[f"{delta:+d}"] += 1
    return dict(sorted(contagem.items(), key=lambda kv: int(kv[0])))


def avaliar_tudo() -> dict:
    """Avalia todas as combinações que têm ``execucao.json`` e grava ``avaliacao.json``.

    Returns:
        O documento completo que vai para ``avaliacao.json``.
    """
    indice = json.loads((PASTA_RECORTES / "indice.json").read_text(encoding="utf-8"))
    ouro = _carregar_ouro()
    referencia_ids = [i["id"] for i in indice if i["origem"] == "ouro"]
    combinacoes = {}
    for biblioteca in BIBLIOTECAS:
        for condicao in CONDICOES:
            resultado = avaliar_combinacao(biblioteca, condicao, indice, ouro)
            if resultado is not None:
                combinacoes[f"{biblioteca}/{condicao}"] = resultado
    documento = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "referencia": {
            "fonte": "data/gold/ouro_video (telas, notas por corda e casa)",
            "ids": referencia_ids,
            "janela": "x_centro_quadro dentro de caixa_recorte[0..2]",
            "agrupamento_px": DISTANCIA_AGRUPAMENTO_PX,
            "soa_uma_oitava_abaixo": SEMITONS_ESCRITA,
        },
        "ids_sem_referencia": [i["id"] for i in indice if i["origem"] != "ouro"],
        "combinacoes": combinacoes,
    }
    AVALIACAO.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return documento


def _linha(nome: str, bloco: dict) -> str:
    """Formata uma linha da tabela para um bloco ``exato`` ou ``classe``."""
    t = bloco["total"]
    return (
        f"{nome:<18} {t['certas']:>4}/{t['referencia']:<4} "
        f"{t['altura_errada']:>8} {t['faltando']:>8} {t['inventada']:>9}"
    )


def imprimir(documento: dict) -> None:
    """Imprime a tabela de avaliação no terminal.

    Args:
        documento: o que ``avaliar_tudo`` devolveu.
    """
    for combo, res in documento["combinacoes"].items():
        print(f"\n== {combo} ==")
        print(
            f"{'modo':<18} {'certas/ref':>9} {'errada':>8} {'faltando':>8} "
            f"{'inventada':>9}"
        )
        for modo in ("exato", "classe"):
            print(_linha(modo, res[modo]))
        print(
            f"tempo: média {res['tempo']['media']} s, máx {res['tempo']['max']} s "
            f"(n={res['tempo']['n']})"
        )
        if res["deslocamento"]["total"]:
            print(
                f"deslocamento (biblioteca - referência): "
                f"{res['deslocamento']['total']}"
            )
        for falha in res["falhas"]:
            print(f"  falha {falha['id']}: {falha['motivo']}")
        for id_, alertas in res["alertas"].items():
            for alerta in alertas:
                print(f"  alerta {id_}: {alerta}")
        for id_, info in res["sem_referencia"].items():
            if id_ in documento["ids_sem_referencia"]:
                print(
                    f"  {id_}: saída={info['saida']} notas={info['notas']} "
                    f"compassos={info['compassos']}"
                )


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI: avalia tudo, grava o JSON e imprime a tabela.

    Args:
        argv: argumentos (não usados; a CLI não tem opções).

    Returns:
        0 ao terminar.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    documento = avaliar_tudo()
    imprimir(documento)
    print(f"\ngravado: {AVALIACAO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
