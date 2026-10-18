"""Conferência da leitura de partitura (trilha partitura, P1): o dono confere o Audiveris.

Dois subcomandos:

- ``preparar``: lê os MusicXML das leituras (Audiveris x2 sobre o recorte com margem
  7/7; homr nativo quando o Audiveris não tem saída) símbolo a símbolo e grava
  ``itens.json``. Cada símbolo traz altura, figura, pausa, ligadura e se o homr e a
  tablatura concordam com ele.
- ``servir``: página local com o recorte original (zoom, com marcação de notas que
  faltaram) e a leitura desenhada e tocável, em que o dono clica em cada nota ou pausa
  e diz o que está errado. Cada recorte confirmado vai para o gabarito (formato 3), em
  escrita atômica. Re-confirmar um recorte sobrescreve só ele.

Não usa GPU nem roda as bibliotecas de OMR. O gabarito real (``data/gold``) só é gravado
quando o dono confirma pela página; o servidor exige ``--ouro`` explícito. Os testes
usam ``tmp_path``.

``preparar --sem-produto SLUG:ID`` (repetível) faz o mesmo para recortes de vídeos sem
produto de tablatura (``PASTA_SEM_PRODUTO``), com a leitura herdada do Audiveris.

Uso::

    python -m tab.partitura_gabarito preparar
    python -m tab.partitura_gabarito preparar --saida CAMINHO --sem-produto SLUG:ID
    python -m tab.partitura_gabarito servir --ouro CAMINHO --porta 8098 --host 127.0.0.1
"""

from __future__ import annotations

import argparse
import copy
import datetime
import http.server
import json
import os
import re
import struct
import sys
import threading
from pathlib import Path
from xml.etree import ElementTree as ET

from tab.caminhos import RAIZ, SAIDA
from tab.partitura_avaliar import (
    NotaXML,
    _carregar_ouro,
    _referencia_do_item,
    alinhar,
    eventos_da_biblioteca,
)

#: Pastas da trilha partitura P1 (recortes, leituras do OMR e a conferência). A
#: conferência usa o recorte com margem 7/7, a melhor entrada medida (rodada 3003).
PASTA_PARTITURA = SAIDA / "partitura" / "p1"
PASTA_RECORTES = PASTA_PARTITURA / "recortes_margem"
PASTA_OMR = PASTA_PARTITURA / "omr"
PASTA_CONFERENCIA = PASTA_PARTITURA / "conferencia"

#: Índice dos recortes (R01–R21), gerado antes pela P1.
INDICE_RECORTES = PASTA_RECORTES / "indice.json"

#: Condição do Audiveris lida na conferência (x2 sobre o recorte com margem).
CONDICAO_AUDIVERIS = "x2_margem"

#: Nome da fonte quando a leitura vem do Audiveris.
FONTE_AUDIVERIS = f"audiveris/{CONDICAO_AUDIVERIS}"

#: Itens da conferência, gerados por ``preparar``.
ITENS = PASTA_CONFERENCIA / "itens.json"

#: Vídeos SEM produto de tablatura: uma pasta por vídeo, com ``recortes/indice.json``,
#: ``recortes/<id>.png`` e a leitura herdada do Audiveris (armadura do vídeo aplicada) em
#: ``omr/audiveris/x2_margem_herdada/<id>/saida.musicxml``.
PASTA_SEM_PRODUTO = SAIDA / "partitura" / "sem_produto"

#: Condição da leitura herdada dos vídeos sem produto, e o nome da fonte no item.
CONDICAO_HERDADA = "x2_margem_herdada"
FONTE_HERDADA = f"audiveris/{CONDICAO_HERDADA}"

#: Formato do arquivo de gabarito (``--ouro``): uma entrada por recorte, e cada
#: símbolo com ``notacoes_dono`` (formato 3).
FORMATO_GABARITO = 3

#: Estados que o dono pode dar a um símbolo (a página mostra "inventada" no último).
ESTADOS = ("certo", "altura_errada", "figura_errada", "nao_existe")

#: Estados de cada notação (fermata, ponto, dedilhado...). Ausente vale "certo".
ESTADOS_NOTACAO = ("certo", "errado", "inventado")

#: Tamanho máximo da observação de um recorte.
TAMANHO_OBS_MAXIMO = 500

#: Maior número de pontos de notas faltando que o dono pode marcar num recorte.
FALTANDO_PONTOS_MAXIMO = 200

#: Campos que ficam só na conferência (não entram no ``palpite``).
CAMPOS_DA_CONFERENCIA = ("idx", "homr_concorda", "tab_concorda")

#: Semitons de cada nota natural a partir de dó (MIDI mod 12).
SEMITONS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

#: Tipos de arquivo que o servidor entrega (só PNG dos recortes e a página).
_TIPO_PNG = "image/png"

#: Assinatura de todo arquivo PNG.
_ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"

_HOSTS_LOCAIS = {"127.0.0.1", "localhost"}


# ---------------------------------------------------------------------------------
# Leitura do MusicXML
# ---------------------------------------------------------------------------------


def _ligadura(filho: ET.Element) -> tuple[bool, bool]:
    """Diz se a nota começa e se termina uma ligadura (``tie`` ou ``tied``).

    Args:
        filho: elemento ``note``.

    Returns:
        ``(inicio, fim)``.
    """
    tipos = [e.get("type") for e in filho.findall("tie")]
    tipos += [e.get("type") for e in filho.findall("notations/tied")]
    return "start" in tipos, "stop" in tipos


def _ligaduras_notacao(filho: ET.Element) -> list[str]:
    """Nomes ``tie-start``/``tie-stop`` de uma nota, sem contar a mesma ligadura duas vezes.

    O MusicXML repete a ligadura em ``tie`` (som) e em ``notations/tied`` (desenho).
    Conta-se, por tipo, o maior dos dois, para que cada ligadura apareça uma vez.

    Args:
        filho: elemento ``note``.

    Returns:
        Nomes na ordem ``tie-start``, ``tie-stop``, com repetição se houver mais de um.
    """
    nomes: list[str] = []
    for tipo in ("start", "stop"):
        som = sum(1 for e in filho.findall("tie") if e.get("type") == tipo)
        desenho = sum(
            1 for e in filho.findall("notations/tied") if e.get("type") == tipo
        )
        nomes += [f"tie-{tipo}"] * max(som, desenho)
    return nomes


def _notacoes(filho: ET.Element) -> list[str]:
    """Símbolos que não são a nota em si, lidos do XML, um nome por ocorrência.

    A ordem é fixa: ligaduras, acidente desenhado, pontos, fermatas, articulações,
    ornamentos, técnica (dedilhado e corda), ligaduras de expressão e arpejo. Cada
    ``dot`` vira ``ponto``, cada ``accidental`` vira ``acidente:<texto>``, cada
    ``fingering`` vira ``fingering:<texto>`` e cada ``string`` vira ``string:<texto>``.
    Os outros filhos de ``technical``, ``articulations`` e ``ornaments`` valem pelo
    próprio nome. Os nomes repetidos são desambiguados depois, por
    ``chaves_notacoes``.

    Args:
        filho: elemento ``note``.

    Returns:
        Lista de nomes curtos, na ordem acima.
    """
    nomes = _ligaduras_notacao(filho)
    nomes += [f"acidente:{(e.text or '').strip()}" for e in filho.findall("accidental")]
    nomes += ["ponto"] * len(filho.findall("dot"))
    notacoes = filho.findall("notations")
    for nota in notacoes:
        nomes += ["fermata"] * len(nota.findall("fermata"))
    for nota in notacoes:
        nomes += [a.tag for a in nota.findall("articulations/*")]
    for nota in notacoes:
        nomes += [o.tag for o in nota.findall("ornaments/*")]
    for nota in notacoes:
        for t in nota.findall("technical/*"):
            if t.tag in ("fingering", "string"):
                nomes.append(f"{t.tag}:{(t.text or '').strip()}")
            else:
                nomes.append(t.tag)
    for nota in notacoes:
        for s in nota.findall("slur"):
            if s.get("type") in ("start", "stop"):
                nomes.append(f"slur-{s.get('type')}")
    for nota in notacoes:
        nomes += ["arpeggiate"] * len(nota.findall("arpeggiate"))
    return nomes


def chaves_notacoes(nomes: list[str]) -> list[str]:
    """Chave de cada notação: o nome, e ``nome#2``, ``nome#3`` para as repetições.

    Args:
        nomes: lista de ``notacoes`` de um símbolo.

    Returns:
        Chaves na mesma ordem, todas distintas dentro do símbolo.
    """
    vistos: dict[str, int] = {}
    chaves: list[str] = []
    for nome in nomes:
        vistos[nome] = vistos.get(nome, 0) + 1
        chaves.append(nome if vistos[nome] == 1 else f"{nome}#{vistos[nome]}")
    return chaves


def _altura(pitch: ET.Element, oitava_clave: int) -> tuple[int, str]:
    """Altura escrita (MIDI) e nome da nota, com a oitava de clave aplicada.

    O MusicXML grava a altura soada. Com ``clef-octave-change`` = -1 (clave com 8
    embaixo), a altura escrita é a soada + 12, igual a ``tab.partitura_avaliar``.
    O nome usa a grafia do XML e a oitava escrita, então é coerente com o MIDI.

    Args:
        pitch: elemento ``pitch`` (``step``, ``octave``, ``alter`` opcional).
        oitava_clave: ``clef-octave-change`` da pauta da nota.

    Returns:
        ``(midi_escrito, nome)``, por exemplo ``(66, "F#4")``.

    Raises:
        ValueError: se o ``step`` não é uma nota (A a G).
    """
    step = pitch.findtext("step", "").strip()
    if step not in SEMITONS:
        raise ValueError(f"passo inválido: {step!r}")
    octava = int(pitch.findtext("octave", "4"))
    alter_txt = pitch.findtext("alter")
    alter = round(float(alter_txt)) if alter_txt is not None else 0
    midi_soado = 12 * (octava + 1) + SEMITONS[step] + alter
    midi = midi_soado - 12 * oitava_clave
    oitava_escrita = octava - oitava_clave
    acidente = "#" * alter if alter > 0 else "b" * -alter
    return midi, f"{step}{acidente}{oitava_escrita}"


def _texto_inteiro(elemento: ET.Element | None, etiqueta: str) -> int | None:
    """Lê um filho com texto inteiro, ou ``None`` se ausente.

    Args:
        elemento: pai onde procurar (pode ser ``None``).
        etiqueta: nome do filho.

    Returns:
        O inteiro, ou ``None``.
    """
    if elemento is None:
        return None
    texto = elemento.findtext(etiqueta)
    if texto is None or not texto.strip():
        return None
    return int(texto)


def _ler_nota(
    filho: ET.Element, numero: str, divisions: float, coc: dict[str, int]
) -> dict | None:
    """Um símbolo (nota, acorde, grace ou pausa) de um elemento ``note``.

    Args:
        filho: elemento ``note``.
        numero: número do compasso (atributo ``number``).
        divisions: divisões por semínima da parte, no momento da nota.
        coc: ``clef-octave-change`` por número de clave.

    Returns:
        O símbolo sem ``t`` (preenchido por quem chama), ou ``None`` para um elemento
        sem altura e sem pausa (por exemplo, nota sem altura de percussão).
    """
    pitch = filho.find("pitch")
    pausa = filho.find("rest") is not None
    if pitch is None and not pausa:
        return None
    dur_txt = filho.findtext("duration")
    duracao = float(dur_txt) / divisions if dur_txt else 0.0
    graca = filho.find("grace") is not None
    pauta = filho.findtext("staff", "1").strip()
    midi: int | None = None
    nome: str | None = None
    if pitch is not None:
        midi, nome = _altura(pitch, coc.get(pauta, 0))
    ligada_inicio, ligada_fim = _ligadura(filho)
    figura = (filho.findtext("type") or "").strip() or None
    return {
        "compasso": numero,
        "t": 0.0,
        "t_global": 0.0,
        "pausa": pausa,
        "midi": midi,
        "nome": nome,
        "figura": figura,
        "pontuada": filho.find("dot") is not None,
        "duracao": 0.0 if graca else round(duracao, 6),
        "acorde": filho.find("chord") is not None,
        "voz": filho.findtext("voice", "1").strip(),
        "ligadura_inicio": ligada_inicio,
        "ligadura_fim": ligada_fim,
        "graca": graca,
        "notacoes": _notacoes(filho),
    }


def _ler_atributos(
    filho: ET.Element,
    divisions: float,
    coc: dict[str, int],
    cabecalho: dict,
) -> float:
    """Lê um elemento ``attributes``: divisões, claves, armadura e compasso.

    A clave, a armadura e a fórmula de compasso são guardadas só na primeira vez em
    que aparecem em ``cabecalho`` (a parte 1). Claves seguintes só atualizam ``coc``.

    Args:
        filho: elemento ``attributes``.
        divisions: divisões atuais da parte.
        coc: ``clef-octave-change`` por número de clave (alterado em lugar).
        cabecalho: onde guardar clave, armadura e fórmula (alterado em lugar).

    Returns:
        As divisões depois do elemento.
    """
    novas = filho.findtext("divisions")
    if novas and novas.strip():
        divisions = float(novas)
    for clave in filho.findall("clef"):
        numero = clave.get("number", "1")
        coc[numero] = int(clave.findtext("clef-octave-change") or 0)
        if cabecalho.get("clave") is None:
            linha = _texto_inteiro(clave, "line")
            cabecalho["clave"] = {
                "sign": clave.findtext("sign"),
                "line": linha,
                "octave_change": coc[numero],
            }
    chave = filho.find("key")
    if cabecalho.get("armadura") is None:
        fifths = _texto_inteiro(chave, "fifths")
        if fifths is not None:
            cabecalho["armadura"] = fifths
    compasso = filho.find("time")
    if cabecalho.get("compasso_formula") is None and compasso is not None:
        beats = _texto_inteiro(compasso, "beats")
        beat_type = _texto_inteiro(compasso, "beat-type")
        if beats is not None and beat_type is not None:
            cabecalho["compasso_formula"] = {"beats": beats, "beat_type": beat_type}
    return divisions


def _ler_parte(parte: ET.Element, cabecalho: dict) -> list[dict]:
    """Lê uma ``part``: uma lista de compassos, cada um com os símbolos em ordem.

    O tempo é contado como no ``tab.partitura_avaliar``: ``duration / divisions``,
    acorde começa com a nota anterior, ``backup`` volta, ``forward`` avança, e o
    próximo compasso começa no maior tempo atingido. Notas de graça não avançam.

    Args:
        parte: elemento ``part``.
        cabecalho: onde guardar clave, armadura e fórmula (só para a parte 1).

    Returns:
        Lista de ``{"numero", "duracao", "simbolos"}``, um por compasso. ``t`` de cada
        símbolo é dentro do compasso; ``t_global`` é desde o começo da parte.
    """
    divisions = 1.0
    coc: dict[str, int] = {}
    medidas: list[dict] = []
    inicio_parte = 0.0
    for medida in parte.findall("measure"):
        numero = medida.get("number", "?")
        inicio_medida = inicio_parte
        cursor = 0.0
        fim = 0.0
        inicio_anterior: float | None = None
        simbolos: list[dict] = []
        for filho in medida:
            if filho.tag == "attributes":
                divisions = _ler_atributos(filho, divisions, coc, cabecalho)
            elif filho.tag == "backup":
                cursor -= float(filho.findtext("duration", "0")) / divisions
            elif filho.tag == "forward":
                cursor += float(filho.findtext("duration", "0")) / divisions
                fim = max(fim, cursor)
            elif filho.tag == "note":
                simbolo = _ler_nota(filho, numero, divisions, coc)
                if simbolo is None:
                    continue
                acorde = simbolo["acorde"]
                if acorde and inicio_anterior is not None:
                    inicio_nota = inicio_anterior
                else:
                    inicio_nota = cursor
                simbolo["t"] = round(inicio_nota, 6)
                simbolo["t_global"] = round(inicio_medida + inicio_nota, 6)
                simbolos.append(simbolo)
                if not acorde:
                    inicio_anterior = cursor
                    if not simbolo["graca"]:
                        cursor += simbolo["duracao"]
                fim = max(fim, cursor)
        medidas.append(
            {"numero": numero, "duracao": round(fim, 6), "simbolos": simbolos}
        )
        inicio_parte += fim
    return medidas


def ler_partitura(caminho: Path) -> dict:
    """Lê um MusicXML ``score-partwise`` em compassos e símbolos.

    Se há mais de uma parte, o compasso ``k`` junta os símbolos de todas as partes
    (pela ordem), e a duração do compasso é a maior delas. Cada símbolo guarda o
    ``t_global`` da própria parte. Nenhuma leitura até hoje tem mais de uma parte.

    Args:
        caminho: arquivo ``.musicxml``.

    Returns:
        ``{"partes", "clave", "armadura", "compasso_formula", "compassos"}``, em que
        ``compassos`` é uma lista de ``{"numero", "duracao", "simbolos"}``. A clave é
        ``{"sign", "line", "octave_change"}``, a armadura é o número de ``fifths`` e a
        fórmula é ``{"beats", "beat_type"}``; cada um é ``None`` se o XML não traz.

    Raises:
        ValueError: se a raiz não é ``score-partwise`` ou não há ``part``.
        xml.etree.ElementTree.ParseError: se o XML não abre.
    """
    raiz = ET.parse(caminho).getroot()
    if raiz.tag != "score-partwise":
        raise ValueError(f"raiz {raiz.tag!r}, esperado score-partwise")
    partes = raiz.findall("part")
    if not partes:
        raise ValueError("MusicXML sem nenhuma part")
    cabecalho: dict = {"clave": None, "armadura": None, "compasso_formula": None}
    lidas = [
        _ler_parte(parte, cabecalho if indice == 0 else {})
        for indice, parte in enumerate(partes)
    ]
    compassos: list[dict] = []
    for k in range(max(len(medidas) for medidas in lidas)):
        presentes = [medidas[k] for medidas in lidas if k < len(medidas)]
        numero = presentes[0]["numero"]
        simbolos = [s for medida in presentes for s in medida["simbolos"]]
        for simbolo in simbolos:
            simbolo["compasso"] = numero
        simbolos.sort(key=lambda s: s["t"])
        compassos.append(
            {
                "numero": numero,
                "duracao": max(medida["duracao"] for medida in presentes),
                "simbolos": simbolos,
            }
        )
    return {
        "partes": len(partes),
        "clave": cabecalho["clave"],
        "armadura": cabecalho["armadura"],
        "compasso_formula": cabecalho["compasso_formula"],
        "compassos": compassos,
    }


# ---------------------------------------------------------------------------------
# Concordância entre leituras
# ---------------------------------------------------------------------------------


def _e_nota(simbolo: dict) -> bool:
    """Se o símbolo entra na concordância: tem altura e não é nota de graça.

    Args:
        simbolo: símbolo lido do MusicXML.

    Returns:
        True para nota com altura, que não é pausa nem graça.
    """
    return not simbolo["pausa"] and not simbolo["graca"] and simbolo["midi"] is not None


def _como_notas(simbolos: list[dict]) -> list[NotaXML]:
    """Converte as notas (sem pausa e sem graça) em ``NotaXML``, no tempo global.

    Usa o formato de ``tab.partitura_avaliar`` para reaproveitar ``eventos_da_biblioteca``
    e ``alinhar``, de modo que a conta é a mesma que a da avaliação.

    Args:
        simbolos: símbolos de uma leitura (todos os compassos, em ordem).

    Returns:
        Uma ``NotaXML`` por nota com altura, na ordem recebida.
    """
    return [
        NotaXML(
            parte=1,
            compasso=s["compasso"],
            t=s["t_global"],
            midi=s["midi"],
            duracao=s["duracao"],
            tipo=s["figura"],
            pontuada=s["pontuada"],
            ornamento=False,
            pauta=1,
        )
        for s in simbolos
        if _e_nota(s)
    ]


def eventos_da_leitura(simbolos: list[dict]) -> list[frozenset]:
    """Sequência de eventos (alturas que soam juntas) de uma leitura inteira.

    Args:
        simbolos: símbolos de uma leitura, de todos os compassos.

    Returns:
        Conjuntos de alturas MIDI, em ordem de tempo.
    """
    return eventos_da_biblioteca(_como_notas(simbolos))


def marcar_concordancia(
    simbolos: list[dict], outra: list[frozenset] | None, campo: str
) -> None:
    """Marca, em cada nota, se a outra sequência tem a mesma altura no evento casado.

    A nota concorda quando o evento da outra leitura, casado com o evento dela pelo
    alinhamento global, contém a mesma altura. Nota que a outra leitura não casa (ou
    que ficou de fora do alinhamento) é discordante: a outra não viu a nota ali. Pausa
    e nota de graça recebem ``None``, assim como todos os símbolos se ``outra`` é
    ``None`` (não há outra leitura para comparar).

    Args:
        simbolos: símbolos da leitura conferida (alterados em lugar, no campo).
        outra: sequência de eventos da outra leitura, ou ``None``.
        campo: nome do campo a gravar (``homr_concorda`` ou ``tab_concorda``).
    """
    for simbolo in simbolos:
        simbolo[campo] = None
    notas = [s for s in simbolos if _e_nota(s)]
    if outra is None or not notas:
        return
    lib_notas = _como_notas(notas)
    lib = eventos_da_biblioteca(lib_notas)
    chaves = {c: k for k, c in enumerate(sorted({round(n.t, 6) for n in lib_notas}))}
    casados = {i: j for op, i, j in alinhar(lib, outra) if op == "casa"}
    for simbolo in notas:
        i = chaves[round(simbolo["t_global"], 6)]
        j = casados.get(i)
        simbolo[campo] = j is not None and simbolo["midi"] in outra[j]


# ---------------------------------------------------------------------------------
# preparar
# ---------------------------------------------------------------------------------


def _gravar_atomico(destino: Path, conteudo: dict) -> None:
    """Grava JSON de forma atômica: temporário no mesmo diretório e ``os.replace``.

    Args:
        destino: arquivo final.
        conteudo: dicionário serializável.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, destino)


def _fonte_da_leitura(id_: str, execucao: dict[str, bool]) -> tuple[str, Path]:
    """Escolhe a leitura de um recorte: Audiveris, ou homr nativo se não houver.

    Args:
        id_: id do recorte (``R01``).
        execucao: ``ok`` da execução do Audiveris, por id.

    Returns:
        ``(fonte, caminho)``, com ``fonte`` ``FONTE_AUDIVERIS`` ou ``homr/nativo``.

    Raises:
        FileNotFoundError: se nenhuma das duas leituras existe.
    """
    audiveris = PASTA_OMR / "audiveris" / CONDICAO_AUDIVERIS / id_ / "saida.musicxml"
    if audiveris.exists() and execucao.get(id_, True):
        return FONTE_AUDIVERIS, audiveris
    homr = PASTA_OMR / "homr" / "nativo" / id_ / "saida.musicxml"
    if not homr.exists():
        raise FileNotFoundError(f"{id_}: sem MusicXML do Audiveris nem do homr")
    return "homr/nativo", homr


def _carregar_execucao() -> dict[str, bool]:
    """Status ``ok`` da execução do Audiveris, por id (vazio se não há arquivo).

    Returns:
        Mapa id -> se a execução gerou saída.
    """
    caminho = PASTA_OMR / "audiveris" / CONDICAO_AUDIVERIS / "execucao.json"
    if not caminho.exists():
        return {}
    registros = json.loads(caminho.read_text(encoding="utf-8"))
    return {r["id"]: bool(r["ok"]) for r in registros}


def _tamanho_png(caminho: Path) -> tuple[int, int]:
    """Largura e altura de um PNG, lidas do cabeçalho IHDR.

    Args:
        caminho: arquivo PNG.

    Returns:
        ``(largura, altura)`` em pixels.

    Raises:
        ValueError: se o arquivo não começa com a assinatura de PNG.
    """
    cabecalho = caminho.read_bytes()[:24]
    if cabecalho[:8] != _ASSINATURA_PNG or cabecalho[12:16] != b"IHDR":
        raise ValueError(f"{caminho} não é PNG")
    largura, altura = struct.unpack(">II", cabecalho[16:24])
    return largura, altura


def _relativo_a_raiz(caminho: Path) -> str:
    """Caminho em texto, relativo à raiz do projeto (absoluto se estiver fora dela).

    Args:
        caminho: arquivo ou pasta.

    Returns:
        ``caminho`` relativo a ``RAIZ``, ou ``str(caminho)`` se não está dentro dela
        (o que acontece nos testes, com ``tmp_path``).
    """
    try:
        return str(caminho.relative_to(RAIZ))
    except ValueError:
        return str(caminho)


def _conferir_png(png: Path, entrada: dict) -> tuple[int, int]:
    """Confere que o PNG tem o tamanho que o índice diz, e devolve esse tamanho.

    Args:
        png: PNG do recorte.
        entrada: entrada do ``indice.json`` (com ``id``, ``largura`` e ``altura``).

    Returns:
        ``(largura, altura)`` do PNG, em pixels.

    Raises:
        ValueError: se o PNG não bate com ``largura``/``altura`` do índice.
    """
    largura, altura = _tamanho_png(png)
    if (largura, altura) != (entrada["largura"], entrada["altura"]):
        raise ValueError(f"{entrada['id']}: PNG {largura}x{altura} != índice")
    return largura, altura


def _eventos_do_homr(id_: str) -> list[frozenset]:
    """Eventos do homr nativo de um recorte, para a concordância entre leituras.

    Args:
        id_: id do recorte (``R01``).

    Returns:
        Eventos de ``eventos_da_leitura`` da leitura do homr.
    """
    homr = ler_partitura(PASTA_OMR / "homr" / "nativo" / id_ / "saida.musicxml")
    return eventos_da_leitura(_todos(homr["compassos"]))


def _montar_item(
    *,
    id_: str,
    origem: str,
    canal: str,
    video: str,
    tela: int | None,
    fonte: str,
    caminho: Path,
    png: Path,
    largura: int,
    altura: int,
    eventos_homr: list[frozenset] | None,
    referencia: list[frozenset] | None,
) -> dict:
    """Monta o item de conferência a partir do MusicXML de uma leitura.

    Comum a ``preparar`` (recortes da P1) e a ``preparar --sem-produto``. Cada símbolo
    recebe ``homr_concorda`` e ``tab_concorda``; vale ``None`` quando a leitura de
    comparação não existe (sem homr, sem tablatura de referência).

    Args:
        id_: id do item, único no ``itens.json``.
        origem: ``ouro``, ``p1`` ou ``sem_produto``.
        canal: canal do vídeo.
        video: nome do vídeo.
        tela: tela (ou página) do recorte, ou ``None``.
        fonte: nome da leitura (``audiveris/x2_margem``...).
        caminho: MusicXML da leitura conferida.
        png: PNG original do recorte.
        largura: largura do PNG, em pixels.
        altura: altura do PNG, em pixels.
        eventos_homr: eventos do homr, ou ``None`` se não há leitura do homr.
        referencia: eventos da tablatura de referência, ou ``None``.

    Returns:
        Item com a leitura conferida (símbolos e concordâncias), a clave, a armadura e
        os contadores.

    Raises:
        ValueError: se a leitura tem dois compassos com o mesmo número.
    """
    leitura = ler_partitura(caminho)
    numeros = [c["numero"] for c in leitura["compassos"]]
    if len(set(numeros)) != len(numeros):
        raise ValueError(f"{id_}: número de compasso repetido na leitura")
    lista: list[dict] = []
    for compasso in leitura["compassos"]:
        for simbolo in compasso["simbolos"]:
            simbolo["idx"] = len(lista)
            lista.append(simbolo)
    marcar_concordancia(lista, eventos_homr, "homr_concorda")
    marcar_concordancia(lista, referencia, "tab_concorda")
    discordancias = sum(
        1 for s in lista if s["homr_concorda"] is False or s["tab_concorda"] is False
    )
    return {
        "id": id_,
        "origem": origem,
        "canal": canal,
        "video": video,
        "tela": tela,
        "fonte": fonte,
        "png": _relativo_a_raiz(png),
        "largura_png": largura,
        "altura_png": altura,
        "musicxml": caminho.read_bytes().decode("utf-8"),
        "clave": leitura["clave"],
        "armadura": leitura["armadura"],
        "compasso_formula": leitura["compasso_formula"],
        "compassos": [
            {"numero": c["numero"], "duracao": c["duracao"], "simbolos": c["simbolos"]}
            for c in leitura["compassos"]
        ],
        "n_compassos": len(leitura["compassos"]),
        "n_notas": sum(1 for s in lista if not s["pausa"]),
        "n_pausas": sum(1 for s in lista if s["pausa"]),
        "discordancias": discordancias,
    }


def _item(entrada: dict, execucao: dict[str, bool], ouro: dict) -> dict:
    """Monta o item de conferência de um recorte da P1.

    Args:
        entrada: entrada do ``indice.json``.
        execucao: ``ok`` do Audiveris, por id.
        ouro: mapa ``video`` -> gabaritos (só usado para recortes ``ouro``).

    Returns:
        Item com a leitura conferida (símbolos e concordâncias), a clave, a armadura e
        os contadores.

    Raises:
        ValueError: se o recorte tem dois compassos com o mesmo número, ou se o PNG
            não bate com ``largura``/``altura`` do índice.
    """
    id_ = entrada["id"]
    fonte, caminho = _fonte_da_leitura(id_, execucao)
    png = PASTA_RECORTES / f"{id_}.png"
    largura, altura = _conferir_png(png, entrada)
    eventos_homr = _eventos_do_homr(id_) if fonte == FONTE_AUDIVERIS else None
    referencia = (
        _referencia_do_item(entrada, ouro) if entrada["origem"] == "ouro" else None
    )
    return _montar_item(
        id_=id_,
        origem=entrada["origem"],
        canal=entrada["canal"],
        video=entrada["video"],
        tela=entrada.get("tela"),
        fonte=fonte,
        caminho=caminho,
        png=png,
        largura=largura,
        altura=altura,
        eventos_homr=eventos_homr,
        referencia=referencia,
    )


def _item_sem_produto(slug: str, id_: str) -> dict:
    """Item de conferência de um recorte de vídeo sem produto de tablatura.

    A leitura é a herdada do Audiveris (``x2_margem_herdada``, com a armadura do vídeo
    aplicada). Não há homr nem tablatura nessas pastas, então as concordâncias ficam
    ``None``. O id é ``SLUG[:16]_ID``, estável e único entre os itens da execução.

    Args:
        slug: nome da pasta do vídeo em ``PASTA_SEM_PRODUTO``.
        id_: id do recorte no índice (``P01a``).

    Returns:
        Item no formato de ``_item``, com ``pasta`` (relativa à raiz) e ``recorte``.

    Raises:
        ValueError: se o recorte não está no índice, ou o PNG não bate com ele.
        FileNotFoundError: se o recorte não tem leitura herdada do Audiveris.
    """
    pasta = PASTA_SEM_PRODUTO / slug
    indice = json.loads(
        (pasta / "recortes" / "indice.json").read_text(encoding="utf-8")
    )
    casam = [e for e in indice if e["id"] == id_]
    if not casam:
        raise ValueError(f"{slug}: recorte {id_} não está em recortes/indice.json")
    entrada = casam[0]
    caminho = pasta / "omr" / "audiveris" / CONDICAO_HERDADA / id_ / "saida.musicxml"
    if not caminho.exists():
        raise FileNotFoundError(f"{slug}:{id_}: sem leitura herdada em {caminho}")
    png = pasta / "recortes" / f"{id_}.png"
    largura, altura = _conferir_png(png, entrada)
    video = entrada["video"]
    item = _montar_item(
        id_=f"{slug[:16]}_{id_}",
        origem="sem_produto",
        canal=video.split("/", 1)[0],
        video=video,
        tela=entrada["pagina"],
        fonte=FONTE_HERDADA,
        caminho=caminho,
        png=png,
        largura=largura,
        altura=altura,
        eventos_homr=None,
        referencia=None,
    )
    item["pasta"] = _relativo_a_raiz(pasta)
    item["recorte"] = id_
    return item


def _todos(compassos: list[dict]) -> list[dict]:
    """Todos os símbolos de uma leitura, na ordem dos compassos.

    Args:
        compassos: lista de compassos de ``ler_partitura``.

    Returns:
        Símbolos concatenados.
    """
    return [s for compasso in compassos for s in compasso["simbolos"]]


def preparar(indice: Path = INDICE_RECORTES, saida: Path = ITENS) -> list[dict]:
    """Gera ``itens.json`` com a leitura de cada recorte, sem tocar no gabarito.

    Args:
        indice: ``indice.json`` dos recortes.
        saida: onde gravar ``itens.json``.

    Returns:
        Os itens gerados, na ordem do índice.
    """
    entradas = json.loads(indice.read_text(encoding="utf-8"))
    execucao = _carregar_execucao()
    ouro = _carregar_ouro() if any(e["origem"] == "ouro" for e in entradas) else {}
    itens = [_item(entrada, execucao, ouro) for entrada in entradas]
    _gravar_atomico(
        saida,
        {
            "formato": 1,
            "gerado_por": "tab.partitura_gabarito preparar",
            "itens": itens,
        },
    )
    return itens


def preparar_sem_produto(
    pares: list[tuple[str, str]], saida: Path = ITENS
) -> list[dict]:
    """Gera ``itens.json`` só com os recortes pedidos de vídeos sem produto.

    Args:
        pares: ``(slug, id)`` de cada recorte, na ordem desejada.
        saida: onde gravar ``itens.json``.

    Returns:
        Os itens gerados, na ordem dos pares.

    Raises:
        ValueError: se dois itens ganham o mesmo id (slugs com o mesmo prefixo).
    """
    itens = [_item_sem_produto(slug, id_) for slug, id_ in pares]
    ids = [it["id"] for it in itens]
    if len(set(ids)) != len(ids):
        raise ValueError(f"ids repetidos entre os recortes pedidos: {ids}")
    _gravar_atomico(
        saida,
        {
            "formato": 1,
            "gerado_por": "tab.partitura_gabarito preparar --sem-produto",
            "itens": itens,
        },
    )
    return itens


def _tabela(itens: list[dict]) -> str:
    """Tabela de uma linha por recorte, para o terminal.

    A largura das colunas ``recorte`` e ``fonte`` acompanha o maior valor, para que
    os ids longos (com ``_``) e a fonte herdada não desalinhem a tabela.

    Args:
        itens: itens de ``preparar``.

    Returns:
        Texto da tabela.
    """
    w_id = max([len("recorte")] + [len(it["id"]) for it in itens]) + 2
    w_fonte = max([len("fonte")] + [len(it["fonte"]) for it in itens]) + 2
    linhas = [
        f"{'recorte':<{w_id}}{'fonte':<{w_fonte}}{'compassos':>10}{'notas':>8}"
        f"{'pausas':>8}{'discord.':>10}  canal"
    ]
    for it in itens:
        linhas.append(
            f"{it['id']:<{w_id}}{it['fonte']:<{w_fonte}}{it['n_compassos']:>10}"
            f"{it['n_notas']:>8}{it['n_pausas']:>8}{it['discordancias']:>10}  "
            f"{it['canal']}"
        )
    total = sum(it["discordancias"] for it in itens)
    linhas.append(f"total de discordâncias: {total}")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------------
# Gabarito: validação, aplicação e progresso (funções puras)
# ---------------------------------------------------------------------------------


def gabarito_vazio(itens: Path = ITENS) -> dict:
    """Gabarito sem nenhuma resposta (formato 3).

    Args:
        itens: ``itens.json`` servido na conferência, gravado em ``fonte_itens``
            (relativo à raiz do projeto quando está dentro dela).

    Returns:
        Dicionário com ``formato``, ``fonte_itens`` e ``recortes`` vazio.
    """
    return {
        "formato": FORMATO_GABARITO,
        "fonte_itens": _relativo_a_raiz(itens.resolve()),
        "recortes": {},
    }


def carregar_gabarito(caminho: Path, itens: Path = ITENS) -> dict:
    """Lê o gabarito do disco, ou devolve um vazio se o arquivo não existe.

    Args:
        caminho: arquivo de gabarito (``--ouro``).
        itens: ``itens.json`` servido, para o ``fonte_itens`` de um gabarito novo.

    Returns:
        Gabarito formato 3.

    Raises:
        ValueError: se o arquivo existe e não está no formato 3 (por exemplo, um
            gabarito do formato 1 ou 2, que este código não converte).
    """
    if not caminho.exists():
        return gabarito_vazio(itens)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if dados.get("formato") != FORMATO_GABARITO:
        raise ValueError(
            f"{caminho} está no formato {dados.get('formato')}, "
            f"esperado {FORMATO_GABARITO}"
        )
    dados.setdefault("recortes", {})
    return dados


def validar_obs(valor: object) -> str:
    """Confere a observação de um recorte.

    Args:
        valor: texto enviado pela página, ou ``None``.

    Returns:
        O texto sem espaços nas pontas (``""`` se vazio).

    Raises:
        ValueError: se não for texto ou passar de ``TAMANHO_OBS_MAXIMO``.
    """
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ValueError("obs deve ser texto")
    if len(valor) > TAMANHO_OBS_MAXIMO:
        raise ValueError(f"obs com mais de {TAMANHO_OBS_MAXIMO} caracteres")
    return valor.strip()


def _numero(valor: object) -> float:
    """Lê um número (inteiro ou real, sem booleano).

    Args:
        valor: valor enviado pela página.

    Returns:
        O valor como ``float``.

    Raises:
        ValueError: se não for número.
    """
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise ValueError("x e y devem ser números")
    return float(valor)


def validar_faltando(valor: object, largura: int, altura: int) -> list[dict]:
    """Confere os pontos de notas que faltaram, marcados na imagem original.

    Args:
        valor: lista de ``{"x", "y"}`` enviada pela página (ausente vale lista vazia).
        largura: largura do PNG original do recorte, em pixels.
        altura: altura do PNG original do recorte, em pixels.

    Returns:
        Lista de ``{"x": float, "y": float}``, na ordem recebida.

    Raises:
        ValueError: se não for lista, se passar de ``FALTANDO_PONTOS_MAXIMO``, se um
            ponto não tiver ``x`` e ``y`` numéricos, ou se estiver fora da imagem.
    """
    if valor is None:
        return []
    if not isinstance(valor, list):
        raise ValueError("faltando deve ser uma lista de pontos")
    if len(valor) > FALTANDO_PONTOS_MAXIMO:
        raise ValueError(f"faltando com mais de {FALTANDO_PONTOS_MAXIMO} pontos")
    pontos = []
    for ponto in valor:
        if not isinstance(ponto, dict):
            raise ValueError("cada ponto de faltando deve ser um objeto")
        x = _numero(ponto.get("x"))
        y = _numero(ponto.get("y"))
        if not (0 <= x <= largura and 0 <= y <= altura):
            raise ValueError(f"ponto ({x}, {y}) fora da imagem {largura}x{altura}")
        pontos.append({"x": x, "y": y})
    return pontos


def validar_simbolos(lista: object, simbolos: list[dict]) -> dict[int, str]:
    """Confere o estado dado pelo dono a cada símbolo do recorte.

    Args:
        lista: lista de ``{"idx", "dono"}`` enviada pela página.
        simbolos: todos os símbolos do recorte em ``itens.json``.

    Returns:
        Mapa ``idx`` -> estado.

    Raises:
        ValueError: se a lista não for lista, se um estado não for um dos quatro, se um
            ``idx`` se repetir ou se os ``idx`` não forem exatamente os do recorte.
    """
    if not isinstance(lista, list):
        raise ValueError("simbolos deve ser uma lista")
    donos: dict[int, str] = {}
    for item in lista:
        if not isinstance(item, dict):
            raise ValueError("cada símbolo deve ser um objeto")
        idx = item.get("idx")
        if isinstance(idx, bool) or not isinstance(idx, int):
            raise ValueError("idx deve ser inteiro")
        dono = item.get("dono")
        if dono not in ESTADOS:
            raise ValueError(f"estado inválido: {dono!r}")
        if idx in donos:
            raise ValueError(f"idx repetido: {idx}")
        donos[idx] = dono
    esperados = {s["idx"] for s in simbolos}
    if set(donos) != esperados:
        raise ValueError(
            f"idx não batem com os do recorte: {sorted(donos)} != {sorted(esperados)}"
        )
    return donos


def validar_notacoes_recorte(
    lista: list[dict], simbolos: list[dict]
) -> dict[int, dict[str, str]]:
    """Confere o estado de cada notação (fermata, ponto...) dado pelo dono.

    Chamada depois de ``validar_simbolos``, então todo ``idx`` de ``lista`` existe em
    ``simbolos``. Ausente (``notacoes`` sem a chave) vale ``{}``: tudo certo.

    Args:
        lista: itens de símbolos enviados pela página; cada um pode ter ``notacoes``,
            um objeto ``{chave: estado}``.
        simbolos: todos os símbolos do recorte em ``itens.json``.

    Returns:
        Mapa ``idx`` -> ``{chave: estado}``, só com as chaves enviadas.

    Raises:
        ValueError: se ``notacoes`` não for objeto, se uma chave não existir no símbolo,
            ou se um estado não for um dos três.
    """
    por_idx = {s["idx"]: s for s in simbolos}
    saida: dict[int, dict[str, str]] = {}
    for item in lista:
        valor = item.get("notacoes")
        if valor is None:
            valor = {}
        if not isinstance(valor, dict):
            raise ValueError("notacoes deve ser um objeto {chave: estado}")
        existentes = set(chaves_notacoes(por_idx[item["idx"]].get("notacoes", [])))
        for chave, estado in valor.items():
            if chave not in existentes:
                raise ValueError(
                    f"notação {chave!r} não existe no símbolo {item['idx']}"
                )
            if estado not in ESTADOS_NOTACAO:
                raise ValueError(f"estado de notação inválido: {estado!r}")
        saida[item["idx"]] = dict(valor)
    return saida


def _booleano(valor: object, padrao: bool) -> bool:
    """Lê um campo booleano; ausente vale ``padrao``.

    Args:
        valor: valor enviado (``None`` se ausente).
        padrao: valor quando ausente.

    Returns:
        O booleano.

    Raises:
        ValueError: se veio e não é booleano.
    """
    if valor is None:
        return padrao
    if not isinstance(valor, bool):
        raise ValueError("campo deve ser verdadeiro ou falso")
    return valor


def _palpite(simbolo: dict) -> dict:
    """O que o dono viu de um símbolo: a leitura, sem os campos da conferência.

    Args:
        simbolo: símbolo de ``itens.json``.

    Returns:
        Cópia do símbolo sem ``idx`` nem as concordâncias.
    """
    return {k: v for k, v in simbolo.items() if k not in CAMPOS_DA_CONFERENCIA}


def aplicar_resposta(
    gabarito: dict,
    itens_por_id: dict[str, dict],
    dados: object,
    agora: str,
) -> dict:
    """Grava a conferência de um recorte inteiro, sem tocar nos outros.

    Toda a validação acontece antes de qualquer mudança: se der erro, o gabarito fica
    como estava. Um recorte já confirmado é sobrescrito; os outros são preservados.

    Args:
        gabarito: gabarito formato 3, alterado em lugar.
        itens_por_id: itens de ``preparar`` indexados por id de recorte.
        dados: corpo do POST: ``recorte``, ``simbolos`` (todos os símbolos do recorte,
            cada um com ``idx``, ``dono`` e opcionalmente ``notacoes``), e
            opcionalmente ``faltando``, ``obs``, ``clave_certa`` e ``armadura_certa``.
        agora: carimbo da resposta (ISO).

    Returns:
        O registro do recorte gravado.

    Raises:
        ValueError: se qualquer campo estiver errado (recorte desconhecido, estado
            inválido, idx errado, notação inexistente, ponto fora da imagem, obs longa).
    """
    if not isinstance(dados, dict):
        raise ValueError("o corpo deve ser um objeto JSON")
    recorte_id = dados.get("recorte")
    if not isinstance(recorte_id, str) or recorte_id not in itens_por_id:
        raise ValueError(f"recorte desconhecido: {recorte_id!r}")
    item = itens_por_id[recorte_id]
    simbolos = [s for c in item["compassos"] for s in c["simbolos"]]
    lista = dados.get("simbolos")
    donos = validar_simbolos(lista, simbolos)
    notas = validar_notacoes_recorte(lista, simbolos)
    pontos = validar_faltando(
        dados.get("faltando"), item["largura_png"], item["altura_png"]
    )
    obs = validar_obs(dados.get("obs"))
    recortes = gabarito.setdefault("recortes", {})
    atual = recortes.get(recorte_id, {})
    clave_certa = _booleano(dados.get("clave_certa"), atual.get("clave_certa", True))
    armadura_certa = _booleano(
        dados.get("armadura_certa"), atual.get("armadura_certa", True)
    )
    registro = {
        "fonte": item["fonte"],
        "clave_certa": clave_certa,
        "armadura_certa": armadura_certa,
        "simbolos": [
            {
                "idx": s["idx"],
                "compasso": s["compasso"],
                "palpite": _palpite(s),
                "dono": donos[s["idx"]],
                "notacoes_dono": {
                    chave: notas.get(s["idx"], {}).get(chave, "certo")
                    for chave in chaves_notacoes(s.get("notacoes", []))
                },
            }
            for s in simbolos
        ],
        "faltando": pontos,
        "largura_png": item["largura_png"],
        "altura_png": item["altura_png"],
        "obs": obs,
        "confirmado": True,
        "respondido_em": agora,
    }
    recortes[recorte_id] = registro
    return registro


def confirmado_recorte(gabarito: dict, recorte_id: str) -> bool:
    """Se o recorte já foi confirmado no gabarito.

    Args:
        gabarito: gabarito formato 3.
        recorte_id: id do recorte.

    Returns:
        True se ``confirmado`` é verdadeiro para o recorte.
    """
    registro = gabarito.get("recortes", {}).get(recorte_id, {})
    return registro.get("confirmado") is True


def progresso(itens: list[dict], gabarito: dict) -> dict:
    """Quantos recortes estão confirmados, e quais.

    Args:
        itens: itens de ``preparar``.
        gabarito: gabarito formato 3.

    Returns:
        ``{"confirmados", "total", "por_recorte": {id: bool}}``.
    """
    por_recorte = {it["id"]: confirmado_recorte(gabarito, it["id"]) for it in itens}
    return {
        "confirmados": sum(por_recorte.values()),
        "total": len(itens),
        "por_recorte": por_recorte,
    }


def proximo_pendente_recorte(
    itens: list[dict], gabarito: dict, atual: str | None
) -> str | None:
    """Próximo recorte não confirmado depois de ``atual``, dando a volta se preciso.

    Args:
        itens: itens na ordem da página.
        gabarito: gabarito formato 3.
        atual: id do recorte de partida, ou ``None``.

    Returns:
        O id do próximo pendente, ou ``None`` se não há nenhum.
    """
    ids = [it["id"] for it in itens]
    inicio = ids.index(atual) + 1 if atual in ids else 0
    for recorte_id in ids[inicio:] + ids[:inicio]:
        if recorte_id != atual and not confirmado_recorte(gabarito, recorte_id):
            return recorte_id
    return None


# ---------------------------------------------------------------------------------
# Servidor e página
# ---------------------------------------------------------------------------------


def _host_ok(host: str | None, origem: str | None) -> bool:
    """Aceita só Host e Origin da máquina local (contra rebinding e CSRF).

    Args:
        host: cabeçalho ``Host``.
        origem: cabeçalho ``Origin``, ou ``None``.

    Returns:
        True se a requisição veio da máquina local.
    """
    host_sem_porta = (host or "").rsplit(":", 1)[0]
    if host_sem_porta not in _HOSTS_LOCAIS:
        return False
    if origem is None:
        return True
    return re.fullmatch(r"http://(127\.0\.0\.1|localhost)(:\d+)?", origem) is not None


def criar_servidor(
    itens_caminho: Path,
    ouro: Path,
    porta: int = 8098,
    host: str = "127.0.0.1",
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor (não o inicia). Por padrão escuta SOMENTE em 127.0.0.1.

    Os recortes são ordenados por discordâncias (decrescente, depois pelo id). O
    gabarito é lido agora e regravado a cada confirmação de recorte.

    Args:
        itens_caminho: ``itens.json`` gerado por ``preparar``.
        ouro: arquivo de gabarito (``--ouro``); se não existe, começa vazio.
        porta: porta TCP (0 = uma livre).
        host: endereço de escuta (``0.0.0.0`` só dentro de container).

    Returns:
        O servidor; ``servidor.server_address[1]`` é a porta real.

    Raises:
        ValueError: se o gabarito existe e não está no formato 3.
    """
    itens_todos = json.loads(itens_caminho.read_text(encoding="utf-8"))["itens"]
    ordem = sorted(itens_todos, key=lambda it: (-it["discordancias"], it["id"]))
    por_id = {it["id"]: it for it in ordem}
    gabarito = carregar_gabarito(ouro, itens_caminho)
    trava = threading.Lock()

    class Manipulador(http.server.BaseHTTPRequestHandler):
        """Serve a página, os itens e os PNG dos recortes; grava confirmações."""

        server_version = "partitura_gabarito"

        def log_message(self, formato: str, *args: object) -> None:
            """Silencia o log por requisição."""

        def _json(self, codigo: int, dados: dict) -> None:
            """Responde com um objeto JSON.

            Args:
                codigo: status HTTP.
                dados: corpo.
            """
            corpo = json.dumps(dados, ensure_ascii=False).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _recusada(self) -> bool:
            """Responde 403 se o Host ou o Origin não forem da máquina local.

            Returns:
                True se a requisição foi recusada (e a resposta já foi enviada).
            """
            if _host_ok(self.headers.get("Host"), self.headers.get("Origin")):
                return False
            self._json(403, {"ok": False, "erro": "host recusado"})
            return True

        def _png(self, recorte_id: str) -> None:
            """Entrega o PNG original de um recorte.

            Só entrega arquivo dentro de ``PASTA_RECORTES`` (P1) ou de
            ``PASTA_SEM_PRODUTO``; qualquer outro caminho vira 404.

            Args:
                recorte_id: id do recorte (já conferido contra os itens).
            """
            alvo = (RAIZ / por_id[recorte_id]["png"]).resolve()
            pastas = (PASTA_RECORTES.resolve(), PASTA_SEM_PRODUTO.resolve())
            if not any(alvo.is_relative_to(p) for p in pastas) or not alvo.is_file():
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            corpo = alvo.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", _TIPO_PNG)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self) -> None:
            """Página, itens com o estado do gabarito, e o PNG de cada recorte."""
            if self._recusada():
                return
            caminho = self.path.split("?", 1)[0]
            if caminho in {"/", "/index.html"}:
                corpo = PAGINA.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(corpo)
                return
            if caminho == "/itens":
                with trava:
                    estado = copy.deepcopy(gabarito)
                    prog = progresso(ordem, gabarito)
                self._json(
                    200,
                    {"itens": ordem, "gabarito": estado, "progresso": prog},
                )
                return
            casa = re.fullmatch(r"/recorte/([^/]+)\.png", caminho)
            if casa and casa.group(1) in por_id:
                self._png(casa.group(1))
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def do_POST(self) -> None:
            """``/salvar``: grava a conferência de um recorte, em escrita atômica."""
            if self._recusada():
                return
            if self.path != "/salvar":
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= 64_000:
                    raise ValueError("corpo ausente ou grande demais")
                dados = json.loads(self.rfile.read(tamanho))
                agora = datetime.datetime.now().isoformat(timespec="seconds")
                with trava:
                    anterior = copy.deepcopy(gabarito)
                    try:
                        registro = aplicar_resposta(gabarito, por_id, dados, agora)
                        _gravar_atomico(ouro, gabarito)
                    except OSError:
                        gabarito.clear()
                        gabarito.update(anterior)
                        raise
                    prog = progresso(ordem, gabarito)
                    proximo = proximo_pendente_recorte(
                        ordem, gabarito, dados["recorte"]
                    )
            except (ValueError, KeyError, TypeError) as erro:
                self._json(400, {"ok": False, "erro": f"{type(erro).__name__}: {erro}"})
                return
            except OSError as erro:
                self._json(500, {"ok": False, "erro": f"não gravou em disco: {erro}"})
                return
            self._json(
                200,
                {
                    "ok": True,
                    "registro": registro,
                    "progresso": prog,
                    "proximo": {"recorte": proximo} if proximo else None,
                    "salvo_em": agora,
                },
            )

    return http.server.ThreadingHTTPServer((host, porta), Manipulador)


PAGINA = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conferência da partitura</title>
<style>
:root {
  --fundo: #f6f5f1; --texto: #1d1d1b; --borda: #c9c6bb; --cartao: #ffffff;
  --certo: #e8f3e8; --altura: #fbe0dc; --figura: #fde9c9; --nao: #e6e0f5;
  --discorda: #f2c200; --destaque: #2d5b8a;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --fundo: #1b1c1e; --texto: #ececea; --borda: #46484c; --cartao: #26282b;
    --certo: #203322; --altura: #4a2421; --figura: #4a3819; --nao: #332c48;
    --discorda: #f2c200; --destaque: #7fb0e0;
  }
}
:root[data-theme="dark"] {
  --fundo: #1b1c1e; --texto: #ececea; --borda: #46484c; --cartao: #26282b;
  --certo: #203322; --altura: #4a2421; --figura: #4a3819; --nao: #332c48;
  --discorda: #f2c200; --destaque: #7fb0e0;
}
body { margin: 0; background: var(--fundo); color: var(--texto);
  font: 15px/1.4 system-ui, sans-serif; display: grid;
  grid-template-columns: 300px 1fr; min-height: 100vh; }
aside { border-right: 1px solid var(--borda); padding: 12px; overflow-y: auto;
  max-height: 100vh; position: sticky; top: 0; }
main { padding: 16px; min-width: 0; }
h1 { font-size: 17px; margin: 0 0 6px; }
#progresso { font-weight: 600; margin-bottom: 10px; }
#recortes { list-style: none; padding: 0; margin: 0; }
#recortes li { border: 1px solid var(--borda); border-radius: 6px; padding: 8px;
  margin-bottom: 6px; cursor: pointer; background: var(--cartao); }
#recortes li.ativo { border-color: var(--destaque); box-shadow: 0 0 0 1px var(--destaque); }
#recortes .linha2 { font-size: 12px; opacity: .75; }
#titulo { font-weight: 600; margin-bottom: 8px; }
#png-rolagem { overflow-x: auto; border: 1px solid var(--borda); border-radius: 4px;
  background: #fff; }
#png-caixa { position: relative; width: 150%; }
#png { display: block; width: 100%; height: auto; user-select: none; cursor: crosshair; }
.falta { position: absolute; width: 14px; height: 14px; border-radius: 50%;
  transform: translate(-50%, -50%); background: rgba(214, 40, 40, .55);
  border: 1px solid #b01c1c; cursor: pointer; }
#osmd { background: #fff; border: 1px solid var(--borda); border-radius: 4px;
  margin: 10px 0; overflow-x: auto; min-height: 60px; }
#osmd svg { cursor: default; }
.aviso { color: #a33; font-size: 13px; min-height: 1em; }
.dica { font-size: 13px; opacity: .8; margin: 4px 0; }
.barra { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0; }
button { font: inherit; padding: 6px 10px; border-radius: 6px;
  border: 1px solid var(--borda); background: var(--cartao); color: var(--texto);
  cursor: pointer; }
button.principal { background: var(--destaque); color: #fff; border-color: var(--destaque); }
.caixas label { margin-right: 14px; }
.campos { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 8px; }
.campos input[type="text"] { width: 360px; max-width: 100%; }
.msg { font-size: 13px; min-height: 1em; margin-top: 4px; }
.status { font-size: 13px; min-height: 1em; margin: 4px 0; }
details { margin-top: 12px; }
details summary { cursor: pointer; font-weight: 600; }
.compasso { border: 1px solid var(--borda); border-radius: 8px; padding: 10px;
  margin: 10px 0; background: var(--cartao); }
.compasso .cab { display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  margin-bottom: 6px; }
.grade { display: flex; flex-wrap: wrap; gap: 6px; align-items: flex-start; }
.coluna { display: flex; flex-direction: column; gap: 4px; }
.chip { display: flex; flex-direction: column; align-items: flex-start; min-width: 110px;
  text-align: left; border-width: 2px; }
.chip small { font-size: 11px; opacity: .8; }
.chip.estado-certo { background: var(--certo); }
.chip.estado-altura_errada { background: var(--altura); }
.chip.estado-figura_errada { background: var(--figura); }
.chip.estado-nao_existe { background: var(--nao); text-decoration: line-through; }
.chip.discorda { border-color: var(--discorda); }
.menu { position: fixed; z-index: 10; background: var(--cartao); color: var(--texto);
  border: 1px solid var(--borda); border-radius: 8px; padding: 6px; min-width: 190px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, .25); display: flex; flex-direction: column;
  gap: 4px; }
.menu[hidden] { display: none; }
.menu .titulo-menu { font-size: 12px; opacity: .8; padding: 2px 4px; }
.menu button { text-align: left; display: flex; justify-content: space-between; }
.menu kbd { opacity: .6; font: inherit; font-size: 12px; }
.legenda span { display: inline-block; margin-right: 12px; }
.legenda i { display: inline-block; width: 12px; height: 12px; vertical-align: middle;
  margin-right: 4px; border: 1px solid var(--borda); }
g.vf-stavenote { cursor: pointer; }
/* O OSMD põe pointer-events: bounding-box no g.vf-note: a caixa do acorde inteiro
   (com a haste) roubaria o clique das fermatas e pontos das notas vizinhas. */
#osmd g.vf-note { pointer-events: none; }
#osmd g.vf-modifiers * { pointer-events: all; }
.resumo { font-size: 13px; font-weight: 600; margin: 8px 0 0; }
.menu-vazio { font-size: 12px; opacity: .8; padding: 2px 4px; }
.menu-rotulo { font-size: 12px; font-weight: 600; padding: 4px 4px 0; }
.menu .linha-menu { display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
  font-size: 13px; padding: 2px 4px; }
.menu .linha-menu span { flex: 1 1 120px; }
.menu .linha-menu button { padding: 3px 6px; font-size: 12px; }
.menu .linha-menu button.ativo { background: var(--destaque); color: #fff;
  border-color: var(--destaque); }
.menu[hidden], .menu [hidden] { display: none; }
.chip .notas-chip { font-size: 11px; opacity: .85; }
@media (max-width: 800px) {
  body { grid-template-columns: 1fr; }
  aside { position: static; max-height: none; border-right: none;
    border-bottom: 1px solid var(--borda); }
}
</style>
</head>
<body>
<aside>
  <h1>Conferência da leitura</h1>
  <div id="progresso"></div>
  <ul id="recortes"></ul>
</aside>
<main>
  <div id="titulo"></div>
  <div class="barra">
    <label>zoom da imagem
      <input type="range" id="zoom" min="100" max="300" step="10" value="150"></label>
    <span id="zoom-valor">150%</span>
    <span id="contagem-faltando">faltando: 0</span>
  </div>
  <div class="dica">Imagem original: clique onde faltou nota (aparece uma bolinha
    vermelha). Clique numa bolinha para remover.</div>
  <div id="png-rolagem"><div id="png-caixa">
    <img id="png" alt="recorte original da pauta" draggable="false">
  </div></div>

  <div id="resumo" class="resumo"></div>
  <div id="aviso-clave" class="aviso"></div>
  <div id="osmd"></div>
  <div class="dica">Leitura desenhada numa linha, rolada junto com a imagem. Clique
    numa cabeça de nota para marcar a nota. Clique na haste, na fermata, no ponto,
    no acidente ou em outro símbolo do grupo para marcar os símbolos.</div>
  <div class="barra">
    <button type="button" id="tocar-leitura" class="principal">tocar leitura</button>
    <button type="button" id="botao-parar">parar</button>
  </div>
  <div class="legenda dica">
    <span><i style="background:#fff"></i>certo</span>
    <span><i style="background:#e67e22"></i>altura errada</span>
    <span><i style="background:#2b6cb0"></i>figura errada</span>
    <span><i style="background:#d62828"></i>inventada</span>
    <span><i style="background:#f2c200"></i>discordância entre leituras</span>
  </div>
  <div id="aviso" class="aviso"></div>

  <div class="caixas barra" id="caixas"></div>
  <div class="campos">
    <label>obs <input type="text" id="obs" maxlength="500"
      placeholder="observação do trecho (opcional)"></label>
    <button type="button" id="confirmar" class="principal">confirmar trecho</button>
  </div>
  <div id="msg" class="msg"></div>
  <div id="status" class="status"></div>

  <details id="lista-simbolos">
    <summary>lista de símbolos</summary>
    <div id="simbolos"></div>
  </details>
</main>

<div id="menu" class="menu" role="menu" hidden>
  <div class="titulo-menu" id="menu-titulo"></div>
  <div id="menu-estados">
    <button type="button" data-estado="certo">certo <kbd>1</kbd></button>
    <button type="button" data-estado="altura_errada">altura errada <kbd>2</kbd></button>
    <button type="button" data-estado="figura_errada">figura errada <kbd>3</kbd></button>
    <button type="button" data-estado="nao_existe">inventada <kbd>4</kbd></button>
  </div>
  <div id="menu-simbolos" hidden></div>
</div>

<script src="https://cdn.jsdelivr.net/npm/opensheetmusicdisplay@1.8.6/build/opensheetmusicdisplay.min.js"></script>
<script>
"use strict";
const SVG_NS = "http://www.w3.org/2000/svg";
const ROTULO_ESTADO = {
  certo: "certo", altura_errada: "altura errada",
  figura_errada: "figura errada", nao_existe: "inventada"
};
const COR_ESTADO = {altura_errada: "#e67e22", figura_errada: "#2b6cb0", nao_existe: "#d62828"};
const TECLA_ESTADO = {"1": "certo", "2": "altura_errada", "3": "figura_errada", "4": "nao_existe"};
const FIGURAS = {
  breve: "breve", whole: "semibreve", half: "mínima", quarter: "semínima",
  eighth: "colcheia", "16th": "semicolcheia", "32nd": "fusa",
  "64th": "semifusa", "128th": "sem-fusa"
};
const SEG_SEMINIMA = 60 / 72;
const PONTOS_MAXIMO = 200;
const ELEMENTOS_DE_TINTA = "path, ellipse, rect, polygon, polyline, line, circle";

const OPCOES_NOTA = [
  ["certo", "certo"], ["altura_errada", "altura errada"],
  ["figura_errada", "figura errada"], ["nao_existe", "inventada"]
];
const COR_NOTACAO = {errado: "#e67e22", inventado: "#d62828"};
let marcaClicada = null;
const OPCOES_NOTACAO = [["certo", "certo"], ["errado", "errado"], ["inventado", "inventado"]];

let itens = [];
let porId = {};
let gabarito = {recortes: {}};
let rascunho = {};
let atual = null;
let mapaAtual = null;
let osmdAtual = null;
let tokenDesenho = 0;
let menu = null;
let ignorarRolagem = null;
let contextoAudio = null;
let mestre = null;
window.mapeamento = {};

const dom = (id) => document.getElementById(id);

function el(tag, props, filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "texto") e.textContent = v;
    else if (k === "classe") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const f of filhos || []) if (f !== null && f !== undefined) e.append(f);
  return e;
}

function aviso(texto) { dom("aviso").textContent = texto; }
function mostrarStatus(texto) { dom("status").textContent = texto; }

function rotuloFigura(s) {
  const base = FIGURAS[s.figura] || s.figura || "figura?";
  return s.pontuada ? base + "." : base;
}

function rotuloSimbolo(s) {
  if (s.pausa) return "pausa de " + rotuloFigura(s);
  return s.nome + " · " + rotuloFigura(s);
}

function textoClave(c) {
  if (!c || !c.sign) return "sem clave lida";
  let t = "clave " + c.sign + (c.line === null || c.line === undefined ? "" : c.line);
  if (c.octave_change) t += " (com " + c.octave_change + " de oitava)";
  return t;
}

function textoArmadura(a) {
  if (a === null || a === undefined) return "armadura não lida";
  if (a > 0) return a + " sustenido(s)";
  if (a < 0) return (-a) + " bemol(óis)";
  return "sem alterações";
}

function todosSimbolos(it) {
  return it.compassos.flatMap((c) => c.simbolos);
}

function gravadoDoRecorte(id) {
  return (gabarito.recortes || {})[id] || {};
}

function confirmado(id) {
  return gravadoDoRecorte(id).confirmado === true;
}

// Mesma regra de tab/partitura_gabarito.py (chaves_notacoes): nome, e nome#2, nome#3...
function chavesNotacoes(nomes) {
  const vistos = {};
  return (nomes || []).map((nome) => {
    vistos[nome] = (vistos[nome] || 0) + 1;
    return vistos[nome] === 1 ? nome : nome + "#" + vistos[nome];
  });
}

function inicializarRascunho() {
  rascunho = {};
  for (const it of itens) {
    const gr = gravadoDoRecorte(it.id);
    const donos = {};
    const notas = {};
    for (const s of todosSimbolos(it)) {
      donos[s.idx] = "certo";
      notas[s.idx] = {};
      for (const chave of chavesNotacoes(s.notacoes)) notas[s.idx][chave] = "certo";
    }
    for (const x of gr.simbolos || []) {
      donos[x.idx] = x.dono;
      for (const [chave, estado] of Object.entries(x.notacoes_dono || {})) {
        if (chave in notas[x.idx]) notas[x.idx][chave] = estado;
      }
    }
    rascunho[it.id] = {
      clave: gr.clave_certa !== false,
      armadura: gr.armadura_certa !== false,
      donos: donos,
      notas: notas,
      faltando: (gr.faltando || []).map((p) => ({x: p.x, y: p.y})),
      obs: gr.obs || "",
      // Só para pintar na página: qual marca desenhada foi clicada para cada notação.
      marcas: {},
    };
  }
}

function desenharLista() {
  const ul = dom("recortes");
  ul.textContent = "";
  for (const it of itens) {
    const feito = confirmado(it.id);
    ul.append(el("li", {classe: it.id === atual ? "ativo" : "",
                        onclick: () => abrir(it.id)}, [
      el("div", {texto: (feito ? "✓ " : "") + it.id + " · discordâncias " + it.discordancias}),
      el("div", {classe: "linha2", texto: it.canal + " · " +
                 (feito ? "conferido" : "pendente")}),
    ]));
  }
  const n = itens.filter((it) => confirmado(it.id)).length;
  dom("progresso").textContent = n + " de " + itens.length + " trechos conferidos";
}

function desenharCaixas(it) {
  const r = rascunho[it.id];
  const area = dom("caixas");
  area.textContent = "";
  const caixa = (texto, marcado, aoMudar) => {
    const cb = el("input", {type: "checkbox", onchange: (ev) => aoMudar(ev.target.checked)});
    cb.checked = marcado;
    return el("label", {}, [cb, " " + texto]);
  };
  area.append(caixa("clave certa (lido: " + textoClave(it.clave) + ")", r.clave,
                    (v) => { r.clave = v; }));
  area.append(caixa("armadura certa (lido: " + textoArmadura(it.armadura) + ")", r.armadura,
                    (v) => { r.armadura = v; }));
}

function desenharFaltando() {
  const it = porId[atual];
  const r = rascunho[atual];
  const caixa = dom("png-caixa");
  caixa.querySelectorAll(".falta").forEach((b) => b.remove());
  r.faltando.forEach((p, i) => {
    const bolinha = el("div", {classe: "falta", title: "clique para remover"});
    bolinha.style.left = (p.x / it.largura_png * 100) + "%";
    bolinha.style.top = (p.y / it.altura_png * 100) + "%";
    bolinha.addEventListener("click", (ev) => {
      ev.stopPropagation();
      r.faltando.splice(i, 1);
      desenharFaltando();
    });
    caixa.append(bolinha);
  });
  dom("contagem-faltando").textContent = "faltando: " + r.faltando.length;
}

function aplicarZoom() {
  const pct = dom("zoom").value;
  dom("png-caixa").style.width = pct + "%";
  dom("zoom-valor").textContent = pct + "%";
}

function marcarNaImagem(ev) {
  const img = dom("png");
  if (atual === null || !img.naturalWidth) return;
  const it = porId[atual];
  const r = rascunho[atual];
  if (r.faltando.length >= PONTOS_MAXIMO) {
    dom("msg").textContent = "limite de " + PONTOS_MAXIMO + " pontos por trecho";
    return;
  }
  const caixa = img.getBoundingClientRect();
  const x = (ev.clientX - caixa.left) / caixa.width * it.largura_png;
  const y = (ev.clientY - caixa.top) / caixa.height * it.altura_png;
  r.faltando.push({
    x: Math.round(Math.min(Math.max(x, 0), it.largura_png) * 10) / 10,
    y: Math.round(Math.min(Math.max(y, 0), it.altura_png) * 10) / 10,
  });
  desenharFaltando();
}

function tipoDoSimbolo(s) {
  if (s.pausa) return "pausa";
  if (s.graca) return "graca";
  return "nota";
}

function chip(it, s, r) {
  const estado = r.donos[s.idx] || "certo";
  const motivos = [];
  if (s.homr_concorda === false) motivos.push("homr discorda");
  if (s.tab_concorda === false) motivos.push("tab discorda");
  const notas = r.notas[s.idx] || {};
  const linhas = chavesNotacoes(s.notacoes).map((chave) =>
    el("small", {classe: "notas-chip", texto: chave + ": " + (notas[chave] || "certo")}));
  return el("button", {
    type: "button",
    classe: "chip estado-" + estado + (motivos.length ? " discorda" : ""),
    title: motivos.join("; "),
    onclick: (ev) => abrirMenuSimbolos(ev, [s.idx]),
  }, [
    el("span", {texto: rotuloSimbolo(s)}),
    el("small", {texto: ROTULO_ESTADO[estado] +
                 (motivos.length ? " · " + motivos.join(", ") : "")}),
    ...linhas,
  ]);
}

function desenharSimbolos(it) {
  const area = dom("simbolos");
  const r = rascunho[it.id];
  area.textContent = "";
  for (const c of it.compassos) {
    const grade = el("div", {classe: "grade"});
    let coluna = null;
    let tempoAtual = null;
    for (const s of c.simbolos) {
      if (coluna === null || s.t !== tempoAtual) {
        coluna = el("div", {classe: "coluna"});
        grade.append(coluna);
        tempoAtual = s.t;
      }
      coluna.append(chip(it, s, r));
    }
    if (c.simbolos.length === 0) grade.append(el("em", {texto: "sem símbolos neste compasso"}));
    area.append(el("section", {classe: "compasso"}, [
      el("div", {classe: "cab"}, [
        el("strong", {texto: "compasso " + c.numero}),
        el("button", {type: "button", texto: "tocar compasso",
                      onclick: () => tocarTrecho([c])}),
      ]),
      grade,
    ]));
  }
}

function notasDaMedida(pautas) {
  const saida = [];
  for (const medida of pautas || []) {
    for (const se of medida.staffEntries || []) {
      for (const gve of se.graphicalVoiceEntries || []) {
        for (const gn of gve.notes || []) {
          const sn = gn.sourceNote;
          const repouso = sn.isRest();
          // O timestamp do OSMD é em semibreves, relativo ao compasso; ×4 dá semínimas.
          saida.push({
            gn: gn,
            t: sn.voiceEntry.Timestamp.RealValue * 4,
            repouso: repouso,
            graca: sn.IsGraceNote === true,
            altura: repouso ? null : sn.halfTone,
          });
        }
      }
    }
  }
  return saida;
}

function agrupar(lista, tipo) {
  const grupos = new Map();
  for (const x of lista) {
    const chave = tipo(x) + "@" + Math.round(x.t * 1000);
    if (!grupos.has(chave)) grupos.set(chave, []);
    grupos.get(chave).push(x);
  }
  return grupos;
}

function mapear(o, it) {
  const medidas = (o.GraphicSheet && o.GraphicSheet.MeasureList) || [];
  const porIdx = new Map();
  for (let k = 0; k < it.compassos.length; k++) {
    const simbolos = it.compassos[k].simbolos.map((s) => ({
      ref: s, t: s.t, altura: s.midi, ordem: s.idx,
    }));
    const desenhadas = notasDaMedida(medidas[k]).map((d) => ({
      ref: d, t: d.t, altura: d.altura, ordem: 0,
    }));
    const gs = agrupar(simbolos, (x) => tipoDoSimbolo(x.ref));
    const gd = agrupar(desenhadas, (x) => x.ref.repouso ? "pausa" : x.ref.graca ? "graca" : "nota");
    for (const [chave, lista] of gs) {
      const outra = gd.get(chave) || [];
      const ordS = [...lista].sort((p, q) => (p.altura ?? 0) - (q.altura ?? 0) || p.ordem - q.ordem);
      const ordD = [...outra].sort((p, q) => (p.altura ?? 0) - (q.altura ?? 0));
      const n = Math.min(ordS.length, ordD.length);
      for (let i = 0; i < n; i++) porIdx.set(ordS[i].ref.idx, ordD[i].ref.gn);
    }
  }
  return {porIdx: porIdx, total: todosSimbolos(it).length};
}

function criarHalo(g) {
  const caixa = g.getBBox();
  const r = document.createElementNS(SVG_NS, "rect");
  r.setAttribute("x", caixa.x - 3);
  r.setAttribute("y", caixa.y - 3);
  r.setAttribute("width", caixa.width + 6);
  r.setAttribute("height", caixa.height + 6);
  r.setAttribute("rx", 4);
  r.setAttribute("fill", "#f2c200");
  r.setAttribute("fill-opacity", "0.4");
  r.setAttribute("pointer-events", "none");
  const transformacao = g.getAttribute("transform");
  if (transformacao) r.setAttribute("transform", transformacao);
  g.parentNode.insertBefore(r, g);
}

function elementosDasNotas(porNota) {
  // Devolve {alvos, grupos}. alvos: idx -> cabeça da nota no SVG. O VexFlow desenha
  // um acorde num único grupo (vf-stavenote); nele, cada nota é uma cabeça
  // (vf-notehead). As cabeças são casadas com as notas pela altura: a mais baixa na
  // tela é a de menor halfTone. Pausa (sem cabeça) usa o grupo inteiro.
  // grupos: grupo vf-stavenote -> idx das notas dele (para o clique fora da cabeça).
  const porGrupo = new Map();
  for (const [idx, gn] of porNota) {
    const g = gn.getSVGGElement ? gn.getSVGGElement() : null;
    if (!g) continue;
    if (!porGrupo.has(g)) porGrupo.set(g, []);
    porGrupo.get(g).push([idx, gn]);
  }
  const alvos = new Map();
  const grupos = new Map();
  for (const [g, notas] of porGrupo) {
    grupos.set(g, notas.map(([idx]) => idx));
    const cabecas = [...g.querySelectorAll(".vf-notehead")];
    // A cabeça, e não o grupo: o grupo inclui haste e fermata, e a caixa dele
    // cobriria as notas vizinhas.
    if (cabecas.length !== notas.length) {
      for (const [idx] of notas) alvos.set(idx, g);
      continue;
    }
    notas.sort((a, b) => a[1].sourceNote.halfTone - b[1].sourceNote.halfTone);
    cabecas.sort((a, b) => b.getBBox().y - a.getBBox().y);
    notas.forEach(([idx], k) => alvos.set(idx, cabecas[k]));
  }
  return {alvos: alvos, grupos: grupos};
}

function criarAlvo(g, idx) {
  // A cabeça da nota tem ~12x10 px; um retângulo transparente por cima amplia o clique.
  const caixa = g.getBBox();
  const r = document.createElementNS(SVG_NS, "rect");
  r.setAttribute("x", caixa.x - 6);
  r.setAttribute("y", caixa.y - 3);
  r.setAttribute("width", caixa.width + 12);
  r.setAttribute("height", caixa.height + 6);
  r.setAttribute("fill", "transparent");
  r.setAttribute("pointer-events", "all");
  r.style.cursor = "pointer";
  const transformacao = g.getAttribute("transform");
  if (transformacao) r.setAttribute("transform", transformacao);
  r.addEventListener("click", (ev) => abrirMenuNota(ev, idx));
  g.parentNode.appendChild(r);
}

function pintarNota(g, cor) {
  const elementos = g.matches(ELEMENTOS_DE_TINTA) ? [g] : g.querySelectorAll(ELEMENTOS_DE_TINTA);
  for (const e of elementos) {
    if (!e.__original) {
      e.__original = {fill: e.getAttribute("fill"), stroke: e.getAttribute("stroke")};
    }
    const original = e.__original;
    for (const [atributo, valor] of [["fill", original.fill], ["stroke", original.stroke]]) {
      if (valor === null) e.removeAttribute(atributo);
      else if (cor && valor !== "none") e.setAttribute(atributo, cor);
      else e.setAttribute(atributo, valor);
    }
  }
}

function pintarPartitura() {
  if (!mapaAtual || mapaAtual.id !== atual) return;
  const r = rascunho[atual];
  for (const [idx, g] of mapaAtual.porIdx) {
    pintarNota(g, COR_ESTADO[r.donos[idx]] || null);
  }
  // Notação marcada a partir de um clique na própria marca: pinta essa marca.
  for (const [chave, onde] of Object.entries(r.marcas)) {
    const [idx, nome] = [Number(chave.split("|")[0]), chave.split("|").slice(1).join("|")];
    const marca = (mapaAtual.marcasDoGrupo.get(onde.grupo) || [])[onde.pos];
    if (marca) pintarNota(marca, COR_NOTACAO[(r.notas[idx] || {})[nome]] || null);
  }
}

function atualizarMarcacoes() {
  pintarPartitura();
  desenharSimbolos(porId[atual]);
  desenharMenuSimbolos();
}

function fecharMenu() {
  menu = null;
  dom("menu").hidden = true;
}

function posicionarMenu(ev) {
  const m = dom("menu");
  m.hidden = false;
  const x = Math.min(ev.clientX + 8, window.innerWidth - m.offsetWidth - 8);
  const y = Math.min(ev.clientY + 8, window.innerHeight - m.offsetHeight - 8);
  m.style.left = Math.max(8, x) + "px";
  m.style.top = Math.max(8, y) + "px";
}

function simbolosDosIdx(idxs) {
  const todos = todosSimbolos(porId[atual]);
  return idxs.map((i) => todos.find((s) => s.idx === i)).filter((s) => s);
}

function abrirMenuNota(ev, idx) {
  // Clique na cabeça: o menu de nota (4 estados), como antes.
  ev.stopPropagation();
  const [s] = simbolosDosIdx([idx]);
  menu = {modo: "nota", idxs: [idx]};
  dom("menu-titulo").textContent = s ? rotuloSimbolo(s) : "";
  dom("menu-estados").hidden = false;
  dom("menu-simbolos").hidden = true;
  posicionarMenu(ev);
}

function abrirMenuSimbolos(ev, idxs) {
  // Clique fora da cabeça (haste, fermata, ponto...) ou numa linha da lista de
  // reserva: o menu de símbolos do grupo de notas.
  ev.stopPropagation();
  menu = {modo: "simbolos", idxs: idxs.slice(), marca: marcaClicada};
  marcaClicada = null;
  dom("menu-estados").hidden = true;
  dom("menu-simbolos").hidden = false;
  desenharMenuSimbolos();
  posicionarMenu(ev);
}

function rotuloGrupo(simbolos) {
  if (simbolos.length === 0) return "";
  const notas = simbolos.map((s) => (s.pausa ? "pausa" : s.nome)).join(" ");
  return notas + " · " + rotuloFigura(simbolos[0]);
}

function linhaMenu(rotulo, opcoes, atualEstado, aoEscolher) {
  return el("div", {classe: "linha-menu"}, [
    el("span", {texto: rotulo}),
    ...opcoes.map(([valor, texto]) => el("button", {
      type: "button",
      classe: atualEstado === valor ? "ativo" : "",
      texto: texto,
      onclick: () => aoEscolher(valor),
    })),
  ]);
}

function desenharMenuSimbolos() {
  if (!menu || menu.modo !== "simbolos" || atual === null) return;
  const r = rascunho[atual];
  const simbolos = simbolosDosIdx(menu.idxs);
  dom("menu-titulo").textContent = rotuloGrupo(simbolos);
  const area = dom("menu-simbolos");
  area.textContent = "";
  const multi = simbolos.length > 1;
  let total = 0;
  for (const s of simbolos) {
    const notas = r.notas[s.idx];
    for (const chave of chavesNotacoes(s.notacoes)) {
      total++;
      area.append(linhaMenu(chave + (multi ? " · " + s.nome : ""), OPCOES_NOTACAO,
                            notas[chave] || "certo", (novo) => {
        notas[chave] = novo;
        if (menu.marca) r.marcas[s.idx + "|" + chave] = menu.marca;
        atualizarMarcacoes();
      }));
    }
  }
  if (total === 0) area.append(el("div", {classe: "menu-vazio", texto: "sem símbolos lidos aqui"}));
  area.append(el("div", {classe: "menu-rotulo", texto: "notas do grupo:"}));
  for (const s of simbolos) {
    const rotulo = s.pausa ? "pausa" : "nota " + s.nome;
    area.append(linhaMenu(rotulo, OPCOES_NOTA, r.donos[s.idx] || "certo", (novo) => {
      r.donos[s.idx] = novo;
      atualizarMarcacoes();
    }));
  }
}

function escolherEstado(estado) {
  if (!menu || menu.modo !== "nota" || atual === null) return;
  rascunho[atual].donos[menu.idxs[0]] = estado;
  fecharMenu();
  atualizarMarcacoes();
}

function renderizarPartitura(it) {
  // Desenha de novo (zoom ou resize) e reaplica mapeamento, halos, alvos e cores.
  // A escala é a que faz o desenho ter a mesma largura da imagem no mesmo zoom: o
  // OSMD desenha de primeiro em zoom 1, mede, e o zoom passa a ser a razão entre a
  // largura da imagem a 100% e a largura desse desenho, vezes o zoom do slider.
  const o = osmdAtual;
  o.Zoom = 1;
  o.render();
  const svg = dom("osmd").querySelector("svg");
  const larguraBase = svg ? svg.getBoundingClientRect().width : 0;
  const ajuste = larguraBase > 0 ? dom("png-rolagem").clientWidth / larguraBase : 1;
  o.Zoom = ajuste * Number(dom("zoom").value) / 100;
  o.render();
  const mapa = mapear(o, it);
  const simbolos = todosSimbolos(it);
  const {alvos, grupos} = elementosDasNotas(mapa.porIdx);
  for (const [idx, g] of alvos) {
    const s = simbolos.find((x) => x.idx === idx);
    if (s && (s.homr_concorda === false || s.tab_concorda === false)) criarHalo(g);
  }
  // Alvos depois de todos os halos, para ficarem por cima de tudo. Só as cabeças
  // têm alvo próprio; pausa (sem cabeça) é clicada pelo grupo.
  for (const [idx, g] of alvos) {
    if (g.classList.contains("vf-notehead")) criarAlvo(g, idx);
  }
  const marcasDoGrupo = new Map();
  // Clique no grupo (haste, fermata, ponto, acidente...) abre o menu de símbolos.
  // A haste é uma linha de 1 px: um alvo transparente mais largo cobre a caixa dela.
  for (const [g, idxs] of grupos) {
    g.addEventListener("click", (ev) => abrirMenuSimbolos(ev, idxs));
    const haste = g.querySelector("g.vf-stem");
    if (haste && haste.parentNode) {
      const caixa = haste.getBBox();
      const r = document.createElementNS(SVG_NS, "rect");
      r.setAttribute("x", caixa.x - 4);
      r.setAttribute("y", caixa.y);
      r.setAttribute("width", caixa.width + 8);
      r.setAttribute("height", caixa.height);
      r.setAttribute("fill", "transparent");
      r.setAttribute("pointer-events", "all");
      haste.parentNode.appendChild(r);
    }
    // Ponto e fermata têm 3 a 17 px: cada um ganha um alvo transparente com folga
    // (o clique sobe até o grupo e abre o mesmo menu de símbolos).
    const marcas = [...g.querySelectorAll("g.vf-modifiers > path")];
    marcasDoGrupo.set(idxs[0], marcas);
    for (const [pos, marca] of marcas.entries()) {
      const caixa = marca.getBBox();
      const r = document.createElementNS(SVG_NS, "rect");
      r.setAttribute("x", caixa.x - 7);
      r.setAttribute("y", caixa.y - 7);
      r.setAttribute("width", caixa.width + 14);
      r.setAttribute("height", caixa.height + 14);
      r.setAttribute("fill", "transparent");
      r.setAttribute("pointer-events", "all");
      r.style.cursor = "pointer";
      r.addEventListener("click", () => { marcaClicada = {grupo: idxs[0], pos: pos}; });
      marca.parentNode.appendChild(r);
    }
  }
  mapaAtual = {id: it.id, porIdx: alvos, marcasDoGrupo: marcasDoGrupo};
  const mapeados = alvos.size;
  window.mapeamento[it.id] = [mapeados, mapa.total];
  const falta = mapa.total - mapeados;
  aviso(it.so_lista === true
    ? "O desenho é a leitura do Audiveris, só para referência: marque cada nota na lista de símbolos."
    : (falta ? falta + " símbolos sem posição na partitura (estão na lista de símbolos)" : ""));
  pintarPartitura();
}

async function desenharPartitura(it) {
  const alvo = dom("osmd");
  const meu = ++tokenDesenho;
  alvo.textContent = "";
  mapaAtual = null;
  osmdAtual = null;
  // Item que se julga pela lista (ex.: notas completadas pela tab, que não estão na
  // leitura desenhada): a lista abre sozinha.
  dom("lista-simbolos").open = !it.musicxml || it.so_lista === true;
  if (!it.musicxml) {
    aviso("Sem leitura desenhada neste trecho: marque cada nota na lista de símbolos.");
    return;
  }
  if (typeof opensheetmusicdisplay === "undefined" || !opensheetmusicdisplay.OpenSheetMusicDisplay) {
    aviso("Leitura desenhada indisponível (a biblioteca de desenho não carregou). Use a lista de símbolos.");
    return;
  }
  try {
    const o = new opensheetmusicdisplay.OpenSheetMusicDisplay(alvo, {
      autoResize: false, drawTitle: false, drawPartNames: false,
      renderSingleHorizontalStaffline: true,
    });
    await o.load(it.musicxml);
    if (meu !== tokenDesenho) return;
    // Sem fórmula lida, não desenha o 4/4 padrão do OSMD (não é leitura).
    o.EngravingRules.RenderTimeSignatures = it.compasso_formula !== null;
    osmdAtual = o;
    renderizarPartitura(it);
  } catch (erro) {
    if (meu === tokenDesenho) aviso("Leitura desenhada falhou: " + erro);
  }
}

function avisoLeitura(it) {
  const partes = [];
  if (!it.clave) partes.push("clave");
  if (!it.compasso_formula) partes.push("fórmula de compasso");
  if (partes.length === 0) {
    dom("aviso-clave").textContent = "";
    return;
  }
  let texto = "o Audiveris não leu " + partes.join(" nem ") + " neste trecho";
  if (!it.clave) texto += "; a clave de sol desenhada é padrão do desenho, não leitura";
  if (!it.compasso_formula) texto += "; a fórmula de compasso não foi desenhada (não há leitura)";
  dom("aviso-clave").textContent = texto + ".";
}

function sincronizarRolagens(a, b) {
  // Rolar um rola o outro na mesma proporção. ignorarRolagem evita o laço infinito:
  // o scroll que a gente mesmo causa no outro elemento não é repassado de volta.
  const seguir = (origem, destino) => () => {
    if (ignorarRolagem === origem) {
      ignorarRolagem = null;
      return;
    }
    const maxOrigem = origem.scrollWidth - origem.clientWidth;
    const maxDestino = destino.scrollWidth - destino.clientWidth;
    const proporcao = maxOrigem > 0 ? origem.scrollLeft / maxOrigem : 0;
    const alvo = proporcao * maxDestino;
    if (Math.abs(destino.scrollLeft - alvo) < 1) return;
    ignorarRolagem = destino;
    destino.scrollLeft = alvo;
  };
  a.addEventListener("scroll", seguir(a, b));
  b.addEventListener("scroll", seguir(b, a));
}

async function abrir(id) {
  atual = id;
  fecharMenu();
  const it = porId[id];
  const r = rascunho[id];
  dom("titulo").textContent = id + " · " + it.canal + " · leitura " + it.fonte +
    " · discordâncias " + it.discordancias;
  dom("png").src = "/recorte/" + id + ".png";
  dom("obs").value = r.obs;
  const gr = gravadoDoRecorte(id);
  dom("msg").textContent = confirmado(id) ?
    "trecho já conferido em " + gr.respondido_em + "; confirmar de novo sobrescreve" : "";
  desenharFaltando();
  desenharCaixas(it);
  desenharLista();
  desenharSimbolos(it);
  dom("resumo").textContent = "leitura: " + it.n_compassos + " compassos, " +
    it.n_notas + " notas, " + it.n_pausas + " pausas";
  avisoLeitura(it);
  await desenharPartitura(it);
}

async function confirmarTrecho() {
  if (atual === null) return;
  const it = porId[atual];
  const r = rascunho[atual];
  const msg = dom("msg");
  const corpo = {
    recorte: it.id,
    simbolos: todosSimbolos(it).map((s) => ({
      idx: s.idx, dono: r.donos[s.idx] || "certo", notacoes: r.notas[s.idx] || {},
    })),
    faltando: r.faltando,
    obs: r.obs,
    clave_certa: r.clave,
    armadura_certa: r.armadura,
  };
  msg.textContent = "gravando...";
  let resposta, dados;
  try {
    resposta = await fetch("/salvar", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(corpo),
    });
    dados = await resposta.json().catch(() => ({}));
  } catch (erro) {
    msg.textContent = "não gravou: sem conexão com o servidor (" + erro + ")";
    return;
  }
  if (!resposta.ok || !dados.ok) {
    msg.textContent = "não gravou: " + (dados.erro || resposta.status);
    return;
  }
  gabarito.recortes[it.id] = dados.registro;
  const p = dados.proximo;
  const texto = "gravado às " + dados.salvo_em + " · " + dados.progresso.confirmados +
    " de " + dados.progresso.total + " trechos conferidos";
  if (p) {
    await abrir(p.recorte);
    mostrarStatus(texto);
  } else {
    await abrir(it.id);
    mostrarStatus(texto + " · todos os trechos conferidos");
  }
  desenharLista();
}

function audio() {
  if (!contextoAudio) {
    contextoAudio = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (contextoAudio.state === "suspended") contextoAudio.resume();
  return contextoAudio;
}

function frequencia(midi) {
  return 440 * Math.pow(2, (midi - 69) / 12);
}

function pararTudo() {
  if (mestre) {
    mestre.disconnect();
    mestre = null;
  }
}

function tom(c, destino, freq, inicio, duracao) {
  const osc = c.createOscillator();
  osc.type = "triangle";
  osc.frequency.value = freq;
  const ganho = c.createGain();
  ganho.gain.setValueAtTime(0, inicio);
  ganho.gain.linearRampToValueAtTime(0.3, inicio + 0.01);
  ganho.gain.linearRampToValueAtTime(0, inicio + duracao);
  osc.connect(ganho);
  ganho.connect(destino);
  osc.start(inicio);
  osc.stop(inicio + duracao + 0.05);
}

function tocarTrecho(compassos) {
  pararTudo();
  const c = audio();
  mestre = c.createGain();
  mestre.gain.value = 0.9;
  mestre.connect(c.destination);
  const t0 = c.currentTime + 0.15;
  let deslocamento = 0;
  for (const comp of compassos) {
    for (const s of comp.simbolos) {
      if (s.pausa || s.midi === null || s.midi === undefined) continue;
      const inicio = t0 + (deslocamento + s.t) * SEG_SEMINIMA;
      const duracao = s.graca ? 0.12 : Math.max(0.12, s.duracao * SEG_SEMINIMA * 0.9);
      tom(c, mestre, frequencia(s.midi), inicio, duracao);
    }
    deslocamento += comp.duracao;
  }
}

async function iniciar() {
  let d;
  try {
    const resposta = await fetch("/itens");
    d = await resposta.json();
  } catch (erro) {
    mostrarStatus("não carregou os itens: " + erro);
    return;
  }
  itens = d.itens;
  gabarito = d.gabarito;
  porId = Object.fromEntries(itens.map((it) => [it.id, it]));
  inicializarRascunho();
  const n = itens.filter((it) => confirmado(it.id)).length;
  mostrarStatus(n + " de " + itens.length + " trechos conferidos");
  const pendente = itens.find((it) => !confirmado(it.id));
  await abrir(pendente ? pendente.id : itens[0].id);
}

dom("zoom").addEventListener("input", aplicarZoom);
dom("png").addEventListener("click", marcarNaImagem);
dom("obs").addEventListener("input", (ev) => {
  if (atual !== null) rascunho[atual].obs = ev.target.value;
});
dom("confirmar").addEventListener("click", confirmarTrecho);
dom("tocar-leitura").addEventListener("click", () => {
  const it = porId[atual];
  if (it) tocarTrecho(it.compassos);
});
dom("botao-parar").addEventListener("click", pararTudo);
dom("menu").querySelectorAll("button[data-estado]").forEach((b) => {
  b.addEventListener("click", () => escolherEstado(b.dataset.estado));
});
document.addEventListener("keydown", (ev) => {
  if (menu === null) return;
  if (ev.key === "Escape") {
    fecharMenu();
  } else if (menu.modo === "nota" && TECLA_ESTADO[ev.key]) {
    ev.preventDefault();
    escolherEstado(TECLA_ESTADO[ev.key]);
  }
});
document.addEventListener("click", (ev) => {
  // composedPath é lido antes dos listeners: o botão clicado pode já ter saído do DOM
  // (o menu é redesenhado a cada marcação), e contains() daria falso.
  if (menu !== null && !ev.composedPath().includes(dom("menu"))) fecharMenu();
});
dom("zoom").addEventListener("change", () => {
  if (osmdAtual && atual !== null && mapaAtual) renderizarPartitura(porId[atual]);
});
sincronizarRolagens(dom("png-rolagem"), dom("osmd"));
let temporizador = null;
window.addEventListener("resize", () => {
  clearTimeout(temporizador);
  temporizador = setTimeout(() => {
    if (atual !== null) desenharPartitura(porId[atual]);
  }, 250);
});
aplicarZoom();
iniciar();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------


def servir(itens: Path, ouro: Path, porta: int, host: str) -> int:
    """Sobe o servidor e fica nele até Ctrl+C.

    Args:
        itens: ``itens.json`` gerado por ``preparar``.
        ouro: arquivo de gabarito (``--ouro``); criado na primeira confirmação.
        porta: porta TCP.
        host: endereço de escuta.

    Returns:
        Código de saída.
    """
    if not itens.exists():
        print(f"sem {itens}; rode o preparar antes", file=sys.stderr)
        return 2
    servidor = criar_servidor(itens, ouro, porta, host)
    print(f"conferência da partitura: http://127.0.0.1:{servidor.server_address[1]}/")
    print(f"escutando em {host}; cada confirmação é gravada em: {ouro}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


def _par_sem_produto(texto: str) -> tuple[str, str]:
    """Lê ``SLUG:ID`` de ``--sem-produto``; o id é o que vem depois do último ``:``.

    Args:
        texto: valor do argumento.

    Returns:
        ``(slug, id)``.

    Raises:
        argparse.ArgumentTypeError: se falta o slug ou o id.
    """
    slug, sep, id_ = texto.rpartition(":")
    if not sep or not slug or not id_:
        raise argparse.ArgumentTypeError(f"esperado SLUG:ID, veio {texto!r}")
    return slug, id_


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada do CLI: ``preparar`` ou ``servir``.

    Args:
        argv: argumentos (``None`` usa ``sys.argv``).

    Returns:
        Código de saída.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    preparar_p = sub.add_parser("preparar", help="gera itens.json com as leituras")
    preparar_p.add_argument("--saida", type=Path, default=ITENS)
    preparar_p.add_argument(
        "--sem-produto",
        type=_par_sem_produto,
        action="append",
        metavar="SLUG:ID",
        help="recorte de vídeo sem produto (repetível); sem ele, são os da P1",
    )
    servidor = sub.add_parser("servir", help="servidor da conferência")
    servidor.add_argument("--ouro", type=Path, required=True)
    servidor.add_argument("--itens", type=Path, default=ITENS)
    servidor.add_argument("--porta", type=int, default=8098)
    servidor.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)
    if args.comando == "preparar":
        if args.sem_produto:
            itens = preparar_sem_produto(args.sem_produto, args.saida)
        else:
            itens = preparar(saida=args.saida)
        print(_tabela(itens))
        print(f"gravado: {args.saida}")
        return 0
    return servir(args.itens, args.ouro, args.porta, args.host)


if __name__ == "__main__":
    raise SystemExit(main())
