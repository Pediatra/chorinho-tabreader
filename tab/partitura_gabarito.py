"""Conferência da leitura de partitura (trilha partitura, P1): o dono confere o Audiveris.

Dois subcomandos:

- ``preparar``: lê os MusicXML das leituras (Audiveris x2; homr nativo quando o Audiveris
  não tem saída) símbolo a símbolo e grava ``itens.json``. Cada símbolo traz altura,
  figura, pausa, ligadura e se o homr e a tablatura concordam com ele.
- ``servir``: página local com o recorte original (zoom, com marcação de notas que
  faltaram) e a leitura desenhada e tocável, em que o dono clica em cada nota ou pausa
  e diz o que está errado. Cada recorte confirmado vai para o gabarito (formato 2), em
  escrita atômica. Re-confirmar um recorte sobrescreve só ele.

Não usa GPU nem roda as bibliotecas de OMR. O gabarito real (``data/gold``) só é gravado
quando o dono confirma pela página; o servidor exige ``--ouro`` explícito. Os testes
usam ``tmp_path``.

Uso::

    python -m tab.partitura_gabarito preparar
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

#: Pastas da trilha partitura P1 (recortes, leituras do OMR e a conferência).
PASTA_PARTITURA = SAIDA / "partitura" / "p1"
PASTA_RECORTES = PASTA_PARTITURA / "recortes"
PASTA_OMR = PASTA_PARTITURA / "omr"
PASTA_CONFERENCIA = PASTA_PARTITURA / "conferencia"

#: Índice dos recortes (R01–R21), gerado antes pela P1.
INDICE_RECORTES = PASTA_RECORTES / "indice.json"

#: Itens da conferência, gerados por ``preparar``.
ITENS = PASTA_CONFERENCIA / "itens.json"

#: Formato do arquivo de gabarito (``--ouro``): uma entrada por recorte.
FORMATO_GABARITO = 2

#: Estados que o dono pode dar a um símbolo (a página mostra "inventada" no último).
ESTADOS = ("certo", "altura_errada", "figura_errada", "nao_existe")

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
    """Escolhe a leitura de um recorte: Audiveris x2, ou homr nativo se não houver.

    Args:
        id_: id do recorte (``R01``).
        execucao: ``ok`` da execução do Audiveris x2, por id.

    Returns:
        ``(fonte, caminho)``, com ``fonte`` ``audiveris/x2`` ou ``homr/nativo``.

    Raises:
        FileNotFoundError: se nenhuma das duas leituras existe.
    """
    audiveris = PASTA_OMR / "audiveris" / "x2" / id_ / "saida.musicxml"
    if audiveris.exists() and execucao.get(id_, True):
        return "audiveris/x2", audiveris
    homr = PASTA_OMR / "homr" / "nativo" / id_ / "saida.musicxml"
    if not homr.exists():
        raise FileNotFoundError(f"{id_}: sem MusicXML do Audiveris nem do homr")
    return "homr/nativo", homr


def _carregar_execucao() -> dict[str, bool]:
    """Status ``ok`` da execução do Audiveris x2, por id (vazio se não há arquivo).

    Returns:
        Mapa id -> se a execução gerou saída.
    """
    caminho = PASTA_OMR / "audiveris" / "x2" / "execucao.json"
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


def _item(entrada: dict, execucao: dict[str, bool], ouro: dict) -> dict:
    """Monta o item de conferência de um recorte.

    Args:
        entrada: entrada do ``indice.json``.
        execucao: ``ok`` do Audiveris x2, por id.
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
    largura, altura = _tamanho_png(png)
    if (largura, altura) != (entrada["largura"], entrada["altura"]):
        raise ValueError(f"{id_}: PNG {largura}x{altura} != índice")
    leitura = ler_partitura(caminho)
    numeros = [c["numero"] for c in leitura["compassos"]]
    if len(set(numeros)) != len(numeros):
        raise ValueError(f"{id_}: número de compasso repetido na leitura")
    lista: list[dict] = []
    for compasso in leitura["compassos"]:
        for simbolo in compasso["simbolos"]:
            simbolo["idx"] = len(lista)
            lista.append(simbolo)
    if fonte == "audiveris/x2":
        homr = ler_partitura(PASTA_OMR / "homr" / "nativo" / id_ / "saida.musicxml")
        marcar_concordancia(
            lista, eventos_da_leitura(_todos(homr["compassos"])), "homr_concorda"
        )
    else:
        marcar_concordancia(lista, None, "homr_concorda")
    if entrada["origem"] == "ouro":
        marcar_concordancia(lista, _referencia_do_item(entrada, ouro), "tab_concorda")
    else:
        marcar_concordancia(lista, None, "tab_concorda")
    discordancias = sum(
        1 for s in lista if s["homr_concorda"] is False or s["tab_concorda"] is False
    )
    return {
        "id": id_,
        "origem": entrada["origem"],
        "canal": entrada["canal"],
        "video": entrada["video"],
        "tela": entrada.get("tela"),
        "fonte": fonte,
        "png": str(png.relative_to(RAIZ)),
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


def _tabela(itens: list[dict]) -> str:
    """Tabela de uma linha por recorte, para o terminal.

    Args:
        itens: itens de ``preparar``.

    Returns:
        Texto da tabela.
    """
    linhas = [
        f"{'recorte':<8}{'fonte':<14}{'compassos':>10}{'notas':>8}"
        f"{'pausas':>8}{'discord.':>10}  canal"
    ]
    for it in itens:
        linhas.append(
            f"{it['id']:<8}{it['fonte']:<14}{it['n_compassos']:>10}"
            f"{it['n_notas']:>8}{it['n_pausas']:>8}{it['discordancias']:>10}  "
            f"{it['canal']}"
        )
    total = sum(it["discordancias"] for it in itens)
    linhas.append(f"total de discordâncias: {total}")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------------
# Gabarito: validação, aplicação e progresso (funções puras)
# ---------------------------------------------------------------------------------


def gabarito_vazio() -> dict:
    """Gabarito sem nenhuma resposta (formato 2).

    Returns:
        Dicionário com ``formato``, ``fonte_itens`` e ``recortes`` vazio.
    """
    return {
        "formato": FORMATO_GABARITO,
        "fonte_itens": str(ITENS.relative_to(RAIZ)),
        "recortes": {},
    }


def carregar_gabarito(caminho: Path) -> dict:
    """Lê o gabarito do disco, ou devolve um vazio se o arquivo não existe.

    Args:
        caminho: arquivo de gabarito (``--ouro``).

    Returns:
        Gabarito formato 2.

    Raises:
        ValueError: se o arquivo existe e não está no formato 2 (por exemplo, um
            gabarito do formato 1, por compasso, que este código não converte).
    """
    if not caminho.exists():
        return gabarito_vazio()
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
        gabarito: gabarito formato 2, alterado em lugar.
        itens_por_id: itens de ``preparar`` indexados por id de recorte.
        dados: corpo do POST: ``recorte``, ``simbolos`` (todos os símbolos do recorte),
            e opcionalmente ``faltando``, ``obs``, ``clave_certa`` e ``armadura_certa``.
        agora: carimbo da resposta (ISO).

    Returns:
        O registro do recorte gravado.

    Raises:
        ValueError: se qualquer campo estiver errado (recorte desconhecido, estado
            inválido, idx errado, ponto fora da imagem, obs longa).
    """
    if not isinstance(dados, dict):
        raise ValueError("o corpo deve ser um objeto JSON")
    recorte_id = dados.get("recorte")
    if not isinstance(recorte_id, str) or recorte_id not in itens_por_id:
        raise ValueError(f"recorte desconhecido: {recorte_id!r}")
    item = itens_por_id[recorte_id]
    simbolos = [s for c in item["compassos"] for s in c["simbolos"]]
    donos = validar_simbolos(dados.get("simbolos"), simbolos)
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
        gabarito: gabarito formato 2.
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
        gabarito: gabarito formato 2.

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
        gabarito: gabarito formato 2.
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
        ValueError: se o gabarito existe e não está no formato 2.
    """
    itens_todos = json.loads(itens_caminho.read_text(encoding="utf-8"))["itens"]
    ordem = sorted(itens_todos, key=lambda it: (-it["discordancias"], it["id"]))
    por_id = {it["id"]: it for it in ordem}
    gabarito = carregar_gabarito(ouro)
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

            Args:
                recorte_id: id do recorte (já conferido contra os itens).
            """
            alvo = (RAIZ / por_id[recorte_id]["png"]).resolve()
            if not alvo.is_relative_to(PASTA_RECORTES.resolve()) or not alvo.is_file():
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
            casa = re.fullmatch(r"/recorte/(R\d+)\.png", caminho)
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

  <div class="barra">
    <button type="button" id="tocar-leitura" class="principal">tocar leitura</button>
    <button type="button" id="botao-parar">parar</button>
  </div>
  <div class="dica">Clique numa nota ou pausa desenhada para marcar.</div>
  <div class="legenda dica">
    <span><i style="background:#fff"></i>certo</span>
    <span><i style="background:#e67e22"></i>altura errada</span>
    <span><i style="background:#2b6cb0"></i>figura errada</span>
    <span><i style="background:#d62828"></i>inventada</span>
    <span><i style="background:#f2c200"></i>discordância entre leituras</span>
  </div>
  <div id="aviso" class="aviso"></div>
  <div id="osmd"></div>

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
  <button type="button" data-estado="certo">certo <kbd>1</kbd></button>
  <button type="button" data-estado="altura_errada">altura errada <kbd>2</kbd></button>
  <button type="button" data-estado="figura_errada">figura errada <kbd>3</kbd></button>
  <button type="button" data-estado="nao_existe">inventada <kbd>4</kbd></button>
</div>

<script src="https://cdn.jsdelivr.net/npm/opensheetmusicdisplay@1.8.6/build/opensheetmusicdisplay.min.js"></script>
<script>
"use strict";
const SVG_NS = "http://www.w3.org/2000/svg";
const ESTADOS = ["certo", "altura_errada", "figura_errada", "nao_existe"];
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

let itens = [];
let porId = {};
let gabarito = {recortes: {}};
let rascunho = {};
let atual = null;
let mapaAtual = null;
let tokenDesenho = 0;
let notaMenu = null;
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

function inicializarRascunho() {
  rascunho = {};
  for (const it of itens) {
    const gr = gravadoDoRecorte(it.id);
    const donos = {};
    for (const s of todosSimbolos(it)) donos[s.idx] = "certo";
    for (const x of gr.simbolos || []) donos[x.idx] = x.dono;
    rascunho[it.id] = {
      clave: gr.clave_certa !== false,
      armadura: gr.armadura_certa !== false,
      donos: donos,
      faltando: (gr.faltando || []).map((p) => ({x: p.x, y: p.y})),
      obs: gr.obs || "",
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
  return el("button", {
    type: "button",
    classe: "chip estado-" + estado + (motivos.length ? " discorda" : ""),
    title: motivos.join("; "),
    onclick: () => {
      const i = ESTADOS.indexOf(r.donos[s.idx] || "certo");
      r.donos[s.idx] = ESTADOS[(i + 1) % ESTADOS.length];
      atualizarMarcacoes();
    },
  }, [
    el("span", {texto: rotuloSimbolo(s)}),
    el("small", {texto: ROTULO_ESTADO[estado] +
                 (motivos.length ? " · " + motivos.join(", ") : "")}),
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
  // idx -> cabeça da nota no SVG. O VexFlow desenha um acorde num único grupo
  // (vf-stavenote); nele, cada nota é uma cabeça (vf-notehead). As cabeças são
  // casadas com as notas pela altura: a mais baixa na tela é a de menor halfTone.
  // Pausa (sem cabeça) usa o grupo inteiro.
  const porGrupo = new Map();
  for (const [idx, gn] of porNota) {
    const g = gn.getSVGGElement ? gn.getSVGGElement() : null;
    if (!g) continue;
    if (!porGrupo.has(g)) porGrupo.set(g, []);
    porGrupo.get(g).push([idx, gn]);
  }
  const elementos = new Map();
  for (const [g, notas] of porGrupo) {
    const cabecas = [...g.querySelectorAll(".vf-notehead")];
    // A cabeça, e não o grupo: o grupo inclui haste e fermata, e a caixa dele
    // cobriria as notas vizinhas.
    if (cabecas.length !== notas.length) {
      for (const [idx] of notas) elementos.set(idx, g);
      continue;
    }
    notas.sort((a, b) => a[1].sourceNote.halfTone - b[1].sourceNote.halfTone);
    cabecas.sort((a, b) => b.getBBox().y - a.getBBox().y);
    notas.forEach(([idx], k) => elementos.set(idx, cabecas[k]));
  }
  return elementos;
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
  r.addEventListener("click", (ev) => abrirMenu(ev, idx));
  g.parentNode.appendChild(r);
}

function pintarNota(g, cor) {
  for (const e of g.querySelectorAll(ELEMENTOS_DE_TINTA)) {
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
}

function atualizarMarcacoes() {
  pintarPartitura();
  desenharSimbolos(porId[atual]);
}

function fecharMenu() {
  notaMenu = null;
  dom("menu").hidden = true;
}

function abrirMenu(ev, idx) {
  ev.stopPropagation();
  const it = porId[atual];
  const simbolo = todosSimbolos(it).find((s) => s.idx === idx);
  notaMenu = idx;
  dom("menu-titulo").textContent = simbolo ? rotuloSimbolo(simbolo) : "";
  const menu = dom("menu");
  menu.hidden = false;
  const x = Math.min(ev.clientX + 8, window.innerWidth - menu.offsetWidth - 8);
  const y = Math.min(ev.clientY + 8, window.innerHeight - menu.offsetHeight - 8);
  menu.style.left = Math.max(8, x) + "px";
  menu.style.top = Math.max(8, y) + "px";
}

function escolherEstado(estado) {
  if (notaMenu === null || atual === null) return;
  rascunho[atual].donos[notaMenu] = estado;
  fecharMenu();
  atualizarMarcacoes();
}

async function desenharPartitura(it) {
  const alvo = dom("osmd");
  const meu = ++tokenDesenho;
  alvo.textContent = "";
  mapaAtual = null;
  if (typeof opensheetmusicdisplay === "undefined" || !opensheetmusicdisplay.OpenSheetMusicDisplay) {
    aviso("Leitura desenhada indisponível (a biblioteca de desenho não carregou). Use a lista de símbolos.");
    return;
  }
  try {
    const o = new opensheetmusicdisplay.OpenSheetMusicDisplay(alvo, {
      autoResize: false, drawTitle: false,
    });
    await o.load(it.musicxml);
    if (meu !== tokenDesenho) return;
    o.render();
    const mapa = mapear(o, it);
    if (meu !== tokenDesenho) return;
    const simbolos = todosSimbolos(it);
    const porIdx = elementosDasNotas(mapa.porIdx);
    for (const [idx, g] of porIdx) {
      const s = simbolos.find((x) => x.idx === idx);
      if (s && (s.homr_concorda === false || s.tab_concorda === false)) criarHalo(g);
    }
    // Alvos depois de todos os halos, para ficarem por cima de tudo.
    for (const [idx, g] of porIdx) criarAlvo(g, idx);
    mapaAtual = {id: it.id, porIdx: porIdx};
    const mapeados = porIdx.size;
    window.mapeamento[it.id] = [mapeados, mapa.total];
    const falta = mapa.total - mapeados;
    aviso(falta ? falta + " símbolos sem posição na partitura (estão na lista de símbolos)" : "");
    pintarPartitura();
  } catch (erro) {
    if (meu === tokenDesenho) aviso("Leitura desenhada falhou: " + erro);
  }
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
  await desenharPartitura(it);
}

async function confirmarTrecho() {
  if (atual === null) return;
  const it = porId[atual];
  const r = rascunho[atual];
  const msg = dom("msg");
  const corpo = {
    recorte: it.id,
    simbolos: todosSimbolos(it).map((s) => ({idx: s.idx, dono: r.donos[s.idx] || "certo"})),
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
  if (notaMenu === null) return;
  if (ev.key === "Escape") {
    fecharMenu();
  } else if (TECLA_ESTADO[ev.key]) {
    ev.preventDefault();
    escolherEstado(TECLA_ESTADO[ev.key]);
  }
});
document.addEventListener("click", (ev) => {
  if (notaMenu !== null && !dom("menu").contains(ev.target)) fecharMenu();
});
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


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada do CLI: ``preparar`` ou ``servir``.

    Args:
        argv: argumentos (``None`` usa ``sys.argv``).

    Returns:
        Código de saída.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("preparar", help="gera itens.json com as leituras")
    servidor = sub.add_parser("servir", help="servidor da conferência")
    servidor.add_argument("--ouro", type=Path, required=True)
    servidor.add_argument("--itens", type=Path, default=ITENS)
    servidor.add_argument("--porta", type=int, default=8098)
    servidor.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)
    if args.comando == "preparar":
        itens = preparar()
        print(_tabela(itens))
        print(f"gravado: {ITENS}")
        return 0
    return servir(args.itens, args.ouro, args.porta, args.host)


if __name__ == "__main__":
    raise SystemExit(main())
