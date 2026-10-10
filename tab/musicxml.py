"""Exporta a transcrição para MusicXML (score-partwise 4.0, clef TAB).

O alvo foi dado pelo dono do projeto: `score-partwise` 4.0, `part-name` "Guitarra
(Tab)", `clef` TAB linha 5, `staff-details` com 6 linhas e `staff-tuning`, e cada nota
com `notations/technical/{string, fret}`.

Três honestidades que o formato exige e que este módulo **declara** em vez de esconder:

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


def _notas_do_v1(r: dict) -> list[dict]:
    """Notas distintas do JSON v1, em ordem de tempo.

    O v1 tem uma entrada por passagem e exibição (D2): a mesma nota (tela, coluna, corda)
    aparece várias vezes. Cada nota conta uma vez, com o menor ``t_ini`` declarado. As
    com tempo vêm em ordem de ``t_ini``; as sem tempo, depois, em ordem de tela e coluna.
    O compasso do v1 se repete a cada tela, então é renumerado em sequência. Notas no
    mesmo ``t_ini`` são acorde (``acorde``).

    Args:
        r: JSON ``chorinho/video@1``.

    Returns:
        Lista de notas no formato que ``exportar`` lê (``casa`` como texto).
    """
    por_chave: dict[tuple, dict] = {}
    for n in r.get("notas", []):
        chave = (n["tela"], n["coluna"], n["corda"])
        t = n.get("t_ini")
        atual = por_chave.get(chave)
        if atual is None or (
            t is not None and (atual["t_ini"] is None or t < atual["t_ini"])
        ):
            por_chave[chave] = {**n, "t_ini": t}
    distintas = list(por_chave.values())
    com_tempo = sorted(
        (n for n in distintas if n["t_ini"] is not None),
        key=lambda n: (n["t_ini"], n["tela"], n["coluna"], n["corda"]),
    )
    sem_tempo = sorted(
        (n for n in distintas if n["t_ini"] is None),
        key=lambda n: (n["tela"], n["coluna"], n["corda"]),
    )
    ordem = com_tempo + sem_tempo
    compassos: dict[tuple, int] = {}
    anterior = None
    for n in ordem:
        chave = (n["tela"], n["compasso"])
        compassos.setdefault(chave, len(compassos) + 1)
        n["compasso"] = compassos[chave]
        n["casa"] = str(n["casa"])
        n["acorde"] = n["t_ini"] is not None and n["t_ini"] == anterior
        anterior = n["t_ini"]
    return ordem


def _notas_exportaveis(r: dict) -> tuple[list[dict], list[dict]]:
    """Separa o que vira nota do que não vira (e nunca é inventado)."""
    boas, recusadas = [], []
    origem = _notas_do_v1(r) if r.get("esquema") == ESQUEMA else r.get("notas", [])
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


def _duracoes_v1(notas: list[dict], pulso: float | None) -> list[float]:
    """Duração de cada nota do v1: o intervalo até o PRÓXIMO ATAQUE distinto.

    Notas do mesmo acorde dividem a duração (o intervalo até o ataque seguinte). Sem
    próximo ataque, ou sem tempo, vale o pulso (suposição declarada).
    """
    ataques = sorted({n["t_ini"] for n in notas if n["t_ini"] is not None})
    proximo = dict(itertools.pairwise(ataques))
    return [
        proximo[n["t_ini"]] - n["t_ini"]
        if n["t_ini"] is not None and n["t_ini"] in proximo
        else (pulso or 1.0)
        for n in notas
    ]


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
    notas, recusadas = _notas_exportaveis(r)
    v1 = r.get("esquema") == ESQUEMA
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
    duracoes = _duracoes_v1(notas, pulso) if v1 else _duracoes(notas, pulso)
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
