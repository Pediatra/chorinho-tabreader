"""Exporta a transcrição para MusicXML (score-partwise 4.0, clef TAB).

O alvo foi dado pelo dono do projeto: `score-partwise` 4.0, `part-name` "Guitarra
(Tab)", `clef` TAB linha 5, `staff-details` com 6 linhas e `staff-tuning`, e cada nota
com `notations/technical/{string, fret}`.

Para o JSON `chorinho/video@1` (o caminho do produto), a ordem é a da **partitura**, não a do
tempo: telas em ordem de id (a leitura da música), cada tela uma vez, colunas por x, e
compassos pelas barras da tela (limpas do ruído do detector). A fórmula 2/4 é declarada e
as durações são uniformes dentro do compasso; o `identification/miscellaneous` diz isso.
O tempo (`t_ini`) não entra no arquivo.

Para JSON sem esquema v1, as três honestidades abaixo valem:

1. **A duração é INFERIDA.** Medimos onset, não duração (o algarismo continua laranja
   depois de tocado). A duração de uma nota é o intervalo até o próximo onset; a última
   nota do trecho recebe o pulso mediano, declarado como suposição;
2. **o pulso é o intervalo mediano entre onsets**, não um BPM lido de partitura. O
   compasso de cada trecho sai da barline geométrica dividida por esse pulso, então o
   arquivo fecha (as durações somam o compasso) sem inventar fórmula de compasso;
3. **nota que não é algarismo NÃO vira nota.** `junk`, `harmonico` e `tecnica` são
   contados como não exportados — "sem nota inventada" é critério de pronto do MVP.

Uso:
    python -m tab.musicxml --json data/saida/sky.json --xml data/saida/sky.musicxml
"""

from __future__ import annotations

import argparse
import bisect
import itertools
import json
import os
import statistics
from collections import Counter
from xml.etree import ElementTree as ET

from .caminhos import SAIDA
from .esquema import ESQUEMA
from .reconhecer import ALGARISMOS

#: Afinação padrão, da corda 1 (aguda) à 6 (grave).
AFINACAO_PADRAO: tuple[tuple[int, str, int], ...] = (
    (1, "E", 4),
    (2, "B", 3),
    (3, "G", 3),
    (4, "D", 3),
    (5, "A", 2),
    (6, "E", 2),
)

SEMITONS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

#: Ticks por pulso. Alto o bastante para não perder resolução de onset.
DIVISOES = 1024

#: Compasso declarado no v1: 2/4 (o choro do acervo; a fórmula não é lida da tela).
TEMPOS_COMPASSO = 2
#: Ticks de um compasso 2/4 (dois tempos de ``DIVISOES``).
TICKS_COMPASSO = TEMPOS_COMPASSO * DIVISOES

#: Duas barras a menos de esta fração do passo são uma só (traço duplo, borda da pauta).
FRACAO_FUSAO = 0.75
#: Segmento de 1 a 3 notas mais estreito que esta fração da mediana é haste lida como barra.
FRACAO_HASTE = 0.5

#: Técnicas que têm elemento em `notations/technical`.
TECNICAS_XML = {
    "harmonico": "harmonic",
    "hammer_on": "hammer-on",
    "pull_off": "pull-off",
    "slide": "slide",
    "bend": "bend",
    "vibrato": "vibrato",
}


def midi_da_corda(corda: int, casa: int, afinacao=AFINACAO_PADRAO) -> int | None:
    """MIDI da nota naquela corda e casa, na afinação dada.

    Args:
        corda: 1 = aguda (linha de cima), 6 = grave.
        casa: casa pisada.
        afinacao: sequência de ``(corda, step, octava)``.

    Returns:
        Número MIDI, ou None se a corda não estiver na afinação.
    """
    for numero, step, octava in afinacao:
        if numero == corda:
            return (octava + 1) * 12 + SEMITONS[step] + casa
    return None


def pitch_de_midi(midi: int) -> tuple[str, int, int]:
    """Converte MIDI em ``(step, alter, octava)`` para o MusicXML."""
    step = NOMES[midi % 12]
    alter = 1 if "#" in step else 0
    return step[0], alter, midi // 12 - 1


def _tempo_da_transcricao(notas: list[dict]) -> float | None:
    """Pulso em segundos: a mediana dos intervalos entre onsets exportáveis.

    Só as notas que viram nota entram na conta. Medido: incluir as recusadas (o `junk`
    do `raman`, por exemplo) derrubava o pulso de 2,0 s para 1,0 s no caso de teste —
    o lixo não tem tempo de execução e não pode definir o pulso da música.
    """
    # ONSETS DISTINTOS: três notas do mesmo acorde têm o MESMO instante, e os intervalos
    # entre elas são zero. Medido no `sky guitar` (`(henze) nocturno`): 48 notas em 22
    # ataques davam pulso **0,0** (mediana dos intervalos incluindo os zeros) e o exportador
    # declarava que não havia tempo. O pulso é o intervalo entre ATAQUES, não entre notas.
    onsets = sorted({n["t_ini"] for n in notas if n.get("t_ini") is not None})
    if len(onsets) < 2:
        return None
    intervalos = [b - a for a, b in itertools.pairwise(onsets)]
    # A MEDIANA não serve em vídeo-aula: o professor para para explicar. Medido no
    # `sky guitar` (`(henze) nocturno`): intervalos de 1,0 s a 22,5 s, mediana 4,0 s — e a
    # conferência no vídeo mostra o acorde SOB o marcador, ou seja, o tempo está certo e a
    # pausa é que infla a mediana. O pulso musical é o intervalo mais FREQUENTE entre os
    # curtos (abaixo da mediana), arredondado a 0,1 s.
    mediana = statistics.median(intervalos)
    curtos = [i for i in intervalos if i <= mediana]
    contagem = Counter(round(i, 1) for i in curtos)
    modal, quantas = contagem.most_common(1)[0]
    if quantas >= 2 and modal > 0:
        return modal
    return mediana


def _notas_distintas_v1(r: dict) -> dict[int, list[dict]]:
    """Notas distintas do v1, por tela; cada nota (tela, coluna, corda) conta uma vez.

    O v1 tem uma entrada por passagem e exibição (D2), e a aula repete telas inteiras.
    A ordem da partitura não depende do tempo: é a ordem das telas (id, que é a da
    primeira aparição no vídeo, ou seja, a leitura da música) e a da coluna dentro de
    cada tela. O ``t_ini`` não entra neste arquivo. Medido na rodada 0004: a ordem por
    primeiro ``t_ini`` punha a nota de t = 239,4 s (tela 1, coluna 20, um falso
    marcador na moldura verde da ilustração de mãos) na frente do compasso 1.

    Args:
        r: JSON ``chorinho/video@1``.

    Returns:
        ``{tela: [nota, ...]}`` com as telas em ordem crescente de id.
    """
    escolhida: dict[tuple, dict] = {}
    for n in r.get("notas", []):
        chave = (n["tela"], n["coluna"], n["corda"])
        atual = escolhida.get(chave)
        if atual is None or (n.get("confianca") or 0) > (atual.get("confianca") or 0):
            escolhida[chave] = n
    por_tela: dict[int, list[dict]] = {}
    for n in escolhida.values():
        por_tela.setdefault(n["tela"], []).append(n)
    return {tela: por_tela[tela] for tela in sorted(por_tela)}


def _colunas_da_tela(notas: list[dict]) -> list[tuple[float, list[dict]]]:
    """Agrupa as notas de uma tela em colunas (acordes), em ordem de coluna.

    Args:
        notas: notas distintas de uma tela.

    Returns:
        ``[(x, notas_da_coluna), ...]``, com ``x`` a mediana do ``x_quadro`` da coluna.
    """
    por_coluna: dict[int, list[dict]] = {}
    for n in notas:
        por_coluna.setdefault(n["coluna"], []).append(n)
    saida = []
    for coluna in sorted(por_coluna):
        grupo = sorted(por_coluna[coluna], key=lambda n: n["corda"])
        x = statistics.median(n["x_quadro"] for n in grupo)
        saida.append((x, grupo))
    return saida


def _limpar_barras(
    barras: list[int], passo: float, xs: list[float]
) -> tuple[list[int], dict]:
    """Barras de compasso da tela, sem o ruído do detector de barras.

    O detector (``tab.tabseg``) lê dois tipos de falso positivo, medidos no quadro da
    tela 1 do `retrato brasileiro` (rodada 0004): (a) um traço duplo ou a borda da pauta
    vira duas barras a poucos pixels (118 e 122; 576 e 586); (b) uma haste de nota vira
    barra no meio de um compasso (1181, com 3 notas de um lado e 169 px, contra 400 a 500
    px dos outros compassos). Em (a) a segunda barra sai. Em (b) sai a barra que fecha o
    segmento curto à direita. Não se corrige o detector aqui, porque ele é a grade que
    alimenta o JSON e a régua do MVP.

    Args:
        barras: ``barlines_x`` da tela, no quadro.
        passo: passo entre cordas da tela, em px.
        xs: x de cada coluna da tela, no quadro.

    Returns:
        ``(barras_limpas, relatorio)``; o relatório diz quantas foram fundidas e quais
        hastes saíram.
    """
    fundidas: list[int] = []
    for b in sorted(barras):
        if fundidas and b - fundidas[-1] < FRACAO_FUSAO * passo:
            continue
        fundidas.append(b)
    larguras = [fundidas[i + 1] - fundidas[i] for i in range(len(fundidas) - 1)]
    contagens = [
        sum(1 for x in xs if fundidas[i] <= x < fundidas[i + 1])
        for i in range(len(fundidas) - 1)
    ]
    cheias = [w for w, c in zip(larguras, contagens, strict=True) if c >= 2]
    hastes: list[int] = []
    if cheias:
        mediana = statistics.median(cheias)
        # o último segmento fecha a tela: não é julgado por largura
        for i in range(len(larguras) - 1):
            if 1 <= contagens[i] <= 3 and larguras[i] < FRACAO_HASTE * mediana:
                hastes.append(fundidas[i + 1])
    limpas = [b for b in fundidas if b not in hastes]
    return limpas, {
        "fundidas": len(barras) - len(fundidas),
        "hastes_removidas": hastes,
    }


def _compassos_da_tela(
    colunas: list[tuple[float, list[dict]]], barras: list[int], passo: float
) -> tuple[list[list[tuple[float, list[dict]]]], dict]:
    """Divide as colunas de uma tela nos compassos delimitados pelas barras limpas.

    Antes da primeira barra e depois da última não há compasso (borda da pauta). Um
    compasso interno sem nota vira pausa de compasso (``rest``); não se inventa nota.

    Args:
        colunas: ``[(x, notas)]`` da tela, em ordem de coluna.
        barras: ``barlines_x`` da tela, no quadro.
        passo: passo entre cordas da tela, em px.

    Returns:
        ``(compassos, relatorio)``: ``compassos`` é uma lista de listas de colunas, uma
        por compasso; ``relatorio`` traz as barras fundidas e removidas e as colunas
        que caíram fora da régua (devem ser zero).
    """
    xs = [x for x, _ in colunas]
    limpas, rel = _limpar_barras(barras, passo, xs)
    if len(limpas) < 2:
        # sem barra utilizável: a tela inteira é um compasso, e isso fica declarado
        return ([colunas] if colunas else []), {**rel, "sem_barra": True, "fora": 0}
    segmentos: list[list[tuple[float, list[dict]]]] = [
        [] for _ in range(len(limpas) - 1)
    ]
    fora = 0
    for x, notas in colunas:
        if x < limpas[0] or x >= limpas[-1]:
            fora += 1
        i = min(max(bisect.bisect_right(limpas, x) - 1, 0), len(segmentos) - 1)
        segmentos[i].append((x, notas))
    # compassos vazios nas pontas (antes da 1a nota ou depois da última) não são compassos
    com_nota = [i for i, s in enumerate(segmentos) if s]
    if not com_nota:
        return [], {**rel, "sem_barra": False, "fora": fora}
    compassos = segmentos[com_nota[0] : com_nota[-1] + 1]
    return compassos, {**rel, "sem_barra": False, "fora": fora}


#: Declarações do v1 que vão para `identification/miscellaneous`. O que é inferido
#: aparece aqui, para ninguém ler como medido.
DECLARACOES_V1: tuple[tuple[str, str], ...] = (
    (
        "ordem",
        "telas em ordem de id (= ordem da primeira aparição no vídeo, que é a leitura "
        "da música); colunas por x dentro de cada tela",
    ),
    (
        "repeticoes",
        "cada tela entra UMA vez; as exibições repetidas pela aula ficam de fora",
    ),
    (
        "compasso",
        "barras da tela (barlines_x) limpas: barras a menos de 0,75 passo fundidas e "
        "haste lida como barra removida; a fórmula 2/4 é DECLARADA, não lida da tela",
    ),
    (
        "duracao",
        "NÃO medida: as colunas de cada compasso dividem os 2 tempos por igual; o "
        "ritmo real não sai do vídeo",
    ),
    ("tempo", "o tempo (t_ini) não entra neste arquivo; fica no JSON"),
    (
        "tonalidade",
        "não lida: armadura zero assumida; alterações são escritas como sustenido",
    ),
)


def _notas_exportaveis(r: dict) -> tuple[list[dict], list[dict]]:
    """Separa o que vira nota do que não vira (e nunca é inventado)."""
    boas, recusadas = [], []
    origem = r.get("notas", [])
    for n in origem:
        casa = n.get("casa")
        if casa in ALGARISMOS:
            boas.append(n)
        else:
            recusadas.append(n)
    return boas, recusadas


def _duracoes(notas: list[dict], pulso: float | None) -> list[float]:
    """Duração de cada nota em segundos: o intervalo até o próximo onset.

    A última nota não tem próximo onset; recebe o pulso (suposição declarada).
    """
    duracoes: list[float] = []
    for i, n in enumerate(notas):
        t = n.get("t_ini")
        seguinte = notas[i + 1].get("t_ini") if i + 1 < len(notas) else None
        if t is not None and seguinte is not None and seguinte > t:
            duracoes.append(seguinte - t)
        else:
            duracoes.append(pulso or 1.0)
    return duracoes


def _exportar_v1(r: dict, titulo: str, afinacao=AFINACAO_PADRAO) -> tuple[str, dict]:
    """Monta o MusicXML do v1: ordem de partitura, compassos pelas barras, 2/4 declarado.

    Cada tela entra uma vez, na ordem de id; dentro dela, as colunas em ordem de x e os
    compassos pelas barras limpas (``_compassos_da_tela``). As durações são uniformes
    dentro do compasso (os 2 tempos divididos pelas colunas) e isso está declarado.

    Args:
        r: JSON ``chorinho/video@1``.
        titulo: nome da peça (vai em ``movement-title``).
        afinacao: afinação por corda.

    Returns:
        ``(xml, relatorio)``.
    """
    telas = {t["id"]: t for t in r.get("telas", [])}
    boas: list[dict] = []
    recusadas: list[dict] = []
    for n in r.get("notas", []):
        (boas if str(n.get("casa")) in ALGARISMOS else recusadas).append(n)
    por_tela = _notas_distintas_v1({"notas": boas})

    raiz = ET.Element("score-partwise", {"version": "4.0"})
    ET.SubElement(raiz, "movement-title").text = titulo
    ident = ET.SubElement(raiz, "identification")
    misc = ET.SubElement(ident, "miscellaneous")
    for nome, valor in DECLARACOES_V1:
        campo = ET.SubElement(misc, "miscellaneous-field", {"name": nome})
        campo.text = valor
    part_list = ET.SubElement(raiz, "part-list")
    score_part = ET.SubElement(part_list, "score-part", {"id": "P1"})
    ET.SubElement(score_part, "part-name").text = "Guitarra (Tab)"
    parte = ET.SubElement(raiz, "part", {"id": "P1"})

    numero = 0
    exportadas = 0
    compassos_por_tela: dict[int, int] = {}
    relatorio_telas: dict[int, dict] = {}
    for tela_id, notas in por_tela.items():
        tela = telas.get(tela_id, {})
        passo = float(tela.get("passo") or 20.0)
        colunas = _colunas_da_tela(notas)
        compassos, rel = _compassos_da_tela(
            colunas, tela.get("barlines_x") or [], passo
        )
        relatorio_telas[tela_id] = rel
        compassos_por_tela[tela_id] = len(compassos)
        for colunas_do_compasso in compassos:
            numero += 1
            compasso = ET.SubElement(parte, "measure", {"number": str(numero)})
            if numero == 1:
                atributos = ET.SubElement(compasso, "attributes")
                ET.SubElement(atributos, "divisions").text = str(DIVISOES)
                chave = ET.SubElement(atributos, "key")
                ET.SubElement(chave, "fifths").text = "0"
                tempo = ET.SubElement(atributos, "time")
                ET.SubElement(tempo, "beats").text = str(TEMPOS_COMPASSO)
                ET.SubElement(tempo, "beat-type").text = "4"
                clef = ET.SubElement(atributos, "clef")
                ET.SubElement(clef, "sign").text = "TAB"
                ET.SubElement(clef, "line").text = "5"
                detalhes = ET.SubElement(atributos, "staff-details")
                ET.SubElement(detalhes, "staff-lines").text = "6"
                for corda, step, octava in afinacao:
                    linha = ET.SubElement(
                        detalhes, "staff-tuning", {"line": str(corda)}
                    )
                    ET.SubElement(linha, "tuning-step").text = step
                    ET.SubElement(linha, "tuning-octave").text = str(octava)
            if not colunas_do_compasso:
                # compasso interno sem nota: pausa de compasso, nada inventado
                nota = ET.SubElement(compasso, "note")
                ET.SubElement(nota, "rest", {"measure": "yes"})
                ET.SubElement(nota, "duration").text = str(TICKS_COMPASSO)
                ET.SubElement(nota, "voice").text = "1"
                continue
            n_colunas = len(colunas_do_compasso)
            for k, (_, grupo) in enumerate(colunas_do_compasso):
                inicio = TICKS_COMPASSO * k // n_colunas
                fim = TICKS_COMPASSO * (k + 1) // n_colunas
                for pos, n in enumerate(grupo):
                    nota = ET.SubElement(compasso, "note")
                    if pos > 0:
                        ET.SubElement(nota, "chord")
                    midi = midi_da_corda(int(n["corda"]), int(n["casa"]), afinacao)
                    if midi is not None:
                        step, alter, octava = pitch_de_midi(midi)
                        pitch = ET.SubElement(nota, "pitch")
                        ET.SubElement(pitch, "step").text = step
                        if alter:
                            ET.SubElement(pitch, "alter").text = str(alter)
                        ET.SubElement(pitch, "octave").text = str(octava)
                    ET.SubElement(nota, "duration").text = str(fim - inicio)
                    ET.SubElement(nota, "voice").text = "1"
                    technical = ET.SubElement(nota, "notations")
                    tecnico = ET.SubElement(technical, "technical")
                    ET.SubElement(tecnico, "string").text = str(int(n["corda"]))
                    ET.SubElement(tecnico, "fret").text = str(int(n["casa"]))
                    elemento = TECNICAS_XML.get(str(n.get("tecnica") or ""))
                    if elemento:
                        ET.SubElement(tecnico, elemento)
                    exportadas += 1

    relatorio = {
        "titulo": titulo,
        "notas_exportadas": exportadas,
        "notas_nao_exportadas": len(recusadas),
        "motivo_nao_exportada": sorted({str(n.get("casa")) for n in recusadas}),
        "compassos": numero,
        "compassos_por_tela": compassos_por_tela,
        "telas": relatorio_telas,
        "tempo_usado": False,
        "compasso": "2/4 DECLARADO (não lido da tela); barras da tela limpas",
        "duracao": "NÃO medida: colunas do compasso divididas igualmente",
        "afinacao": "padrão assumida"
        if afinacao == AFINACAO_PADRAO
        else "informada pelo chamador",
        "divisoes": DIVISOES,
    }
    return ET.tostring(raiz, encoding="unicode"), relatorio


def exportar(
    r: dict,
    titulo: str = "Transcrição",
    afinacao=AFINACAO_PADRAO,
    notas_por_compasso: int | None = None,
) -> tuple[str, dict]:
    """Monta o MusicXML da transcrição.

    Args:
        r: saída de ``tab.reconhecer.reconhecer_linha`` já passada por ``completar``.
        titulo: nome da peça (vai em ``movement-title``).
        afinacao: afinação por corda; padrão assumido se não for medida.
        notas_por_compasso: força quantas notas por compasso (senão usa o medido).

    Returns:
        ``(xml, relatorio)`` — o relatório diz o que foi inferido e o que não foi
        exportado, para nada ser apresentado como medido quando não é.
    """
    if r.get("esquema") == ESQUEMA:
        return _exportar_v1(r, titulo, afinacao)
    notas, recusadas = _notas_exportaveis(r)
    pulso = _tempo_da_transcricao(notas)
    onsets = [n["t_ini"] for n in notas if n.get("t_ini") is not None]
    distintos = len(set(onsets))
    # Tempo degenerado não é tempo. Medido nesta noite: um vídeo saiu com 144 notas
    # carimbadas no MESMO instante e o exportador teria escrito isso como se fosse
    # ritmo. É a mesma classe de erro do histórico "323 notas com tempo" (eram 3
    # instantes): o número existia, o significado não.
    # Um violão tem SEIS cordas: no máximo 6 notas podem soar no mesmo instante. Se a
    # média de notas por ataque passa disso, o tempo é degenerado (medido num vídeo: 144
    # notas no MESMO instante). O critério antigo exigia METADE das notas com onset
    # distinto, e reprovava música legítima: medido no `sky guitar` (`(henze) nocturno`),
    # 48 notas em 22 ataques = 2,2 por ataque, que é acorde/dedilhado normal — e o JSON
    # dizia `tempo medido` enquanto o MusicXML dizia que não. Dois lugares decidindo o
    # mesmo, com regras diferentes, é o bug; a regra agora é uma só.
    notas_por_ataque = len(notas) / max(1, distintos)
    tempo_util = (
        pulso is not None and pulso > 0 and distintos >= 3 and notas_por_ataque <= 6.0
    )
    if not tempo_util:
        pulso = None
    duracoes = _duracoes(notas, pulso)
    bpm = round(60.0 / pulso, 1) if pulso else None

    raiz = ET.Element("score-partwise", {"version": "4.0"})
    ET.SubElement(raiz, "movement-title").text = titulo
    part_list = ET.SubElement(raiz, "part-list")
    score_part = ET.SubElement(part_list, "score-part", {"id": "P1"})
    ET.SubElement(score_part, "part-name").text = "Guitarra (Tab)"
    parte = ET.SubElement(raiz, "part", {"id": "P1"})

    # Agrupa por compasso geométrico (o que a barline da imagem permite medir).
    por_compasso: dict[int, list[int]] = {}
    for i, n in enumerate(notas):
        por_compasso.setdefault(int(n.get("compasso", 1)), []).append(i)

    ticks_por_pulso = DIVISOES
    iniciado = False
    assinatura_anterior: tuple[int, int] | None = None
    exportadas = 0
    for numero, indices in sorted(por_compasso.items()):
        compasso = ET.SubElement(parte, "measure", {"number": str(numero)})
        ticks = [
            max(1, round(duracoes[i] / (pulso or 1.0) * ticks_por_pulso))
            for i in indices
        ]
        # acorde não soma tempo: as notas do mesmo ataque dividem o compasso
        batidas = max(
            1,
            round(
                sum(
                    t
                    for t, i in zip(ticks, indices, strict=True)
                    if not notas[i].get("acorde")
                )
                / ticks_por_pulso
            ),
        )
        assinatura = (batidas, 4)
        if not iniciado or assinatura != assinatura_anterior:
            atributos = ET.SubElement(compasso, "attributes")
            if not iniciado:
                ET.SubElement(atributos, "divisions").text = str(DIVISOES)
                chave = ET.SubElement(atributos, "key")
                ET.SubElement(chave, "fifths").text = "0"
            tempo = ET.SubElement(atributos, "time")
            ET.SubElement(tempo, "beats").text = str(assinatura[0])
            ET.SubElement(tempo, "beat-type").text = str(assinatura[1])
            if not iniciado:
                clef = ET.SubElement(atributos, "clef")
                ET.SubElement(clef, "sign").text = "TAB"
                ET.SubElement(clef, "line").text = "5"
                detalhes = ET.SubElement(atributos, "staff-details")
                ET.SubElement(detalhes, "staff-lines").text = "6"
                for corda, step, octava in afinacao:
                    linha = ET.SubElement(
                        detalhes, "staff-tuning", {"line": str(corda)}
                    )
                    ET.SubElement(linha, "tuning-step").text = step
                    ET.SubElement(linha, "tuning-octave").text = str(octava)
            assinatura_anterior = assinatura
        iniciado = True

        for pos, i in enumerate(indices):
            n = notas[i]
            nota = ET.SubElement(compasso, "note")
            if n.get("acorde"):
                ET.SubElement(nota, "chord")
            midi = midi_da_corda(int(n["corda"]), int(n["casa"]), afinacao)
            if midi is not None:
                step, alter, octava = pitch_de_midi(midi)
                pitch = ET.SubElement(nota, "pitch")
                ET.SubElement(pitch, "step").text = step
                if alter:
                    ET.SubElement(pitch, "alter").text = str(alter)
                ET.SubElement(pitch, "octave").text = str(octava)
            ET.SubElement(nota, "duration").text = str(ticks[pos])
            ET.SubElement(nota, "voice").text = "1"
            technical = ET.SubElement(nota, "notations")
            tecnico = ET.SubElement(technical, "technical")
            ET.SubElement(tecnico, "string").text = str(int(n["corda"]))
            ET.SubElement(tecnico, "fret").text = str(int(n["casa"]))
            elemento = TECNICAS_XML.get(str(n.get("tecnica") or ""))
            if elemento:
                ET.SubElement(tecnico, elemento)
            exportadas += 1

    relatorio = {
        "titulo": titulo,
        "notas_exportadas": exportadas,
        "notas_nao_exportadas": len(recusadas),
        "motivo_nao_exportada": sorted({str(n.get("casa")) for n in recusadas}),
        "tempo_medido": tempo_util,
        "instantes_distintos": distintos,
        "pulso_s": round(pulso, 3) if pulso else None,
        "bpm_derivado_do_pulso": bpm,
        "duracao": "INFERIDA (intervalo até o próximo onset; a última usa o pulso)"
        if tempo_util
        else (
            f"NÃO medida: {distintos} instante(s) distinto(s) para {len(notas)} notas "
            "— duração constante declarada, nada de ritmo inventado"
        ),
        "compasso": "derivado da barline geométrica dividida pelo pulso medido"
        if tempo_util
        else "1 compasso por barline geométrica, sem pulso medido",
        "afinacao": "padrão assumida"
        if afinacao == AFINACAO_PADRAO
        else "informada pelo chamador",
        "divisoes": DIVISOES,
    }
    return ET.tostring(raiz, encoding="unicode"), relatorio


def main() -> int:
    """Lê um JSON de transcrição e escreve o MusicXML."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", required=True)
    ap.add_argument("--xml", default=None)
    ap.add_argument("--titulo", default=None)
    args = ap.parse_args()

    with open(args.json, encoding="utf-8") as fh:
        r = json.load(fh)
    titulo = args.titulo or os.path.splitext(os.path.basename(args.json))[0]
    xml, relatorio = exportar(r, titulo=titulo)
    destino = args.xml or str(SAIDA / f"{titulo}.musicxml")
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(xml)
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    print("salvo em", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
