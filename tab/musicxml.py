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
from xml.etree import ElementTree as ET

from .caminhos import SAIDA
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
    onsets = sorted(n["t_ini"] for n in notas if n.get("t_ini") is not None)
    if len(onsets) < 2:
        return None
    return statistics.median([b - a for a, b in itertools.pairwise(onsets)])


def _notas_exportaveis(r: dict) -> tuple[list[dict], list[dict]]:
    """Separa o que vira nota do que não vira (e nunca é inventado)."""
    boas, recusadas = [], []
    for n in r.get("notas", []):
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
    pulso = _tempo_da_transcricao(notas)
    onsets = [n["t_ini"] for n in notas if n.get("t_ini") is not None]
    distintos = len(set(onsets))
    # Tempo degenerado não é tempo. Medido nesta noite: um vídeo saiu com 144 notas
    # carimbadas no MESMO instante e o exportador teria escrito isso como se fosse
    # ritmo. É a mesma classe de erro do histórico "323 notas com tempo" (eram 3
    # instantes): o número existia, o significado não.
    tempo_util = (
        pulso is not None and pulso > 0 and distintos >= max(2, len(notas) // 2)
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
        batidas = max(1, round(sum(ticks) / ticks_por_pulso))
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
