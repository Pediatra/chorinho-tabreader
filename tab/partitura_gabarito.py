"""Conferência da leitura de partitura (trilha partitura, P1): o dono confere o Audiveris.

Dois subcomandos:

- ``preparar``: lê os MusicXML das leituras (Audiveris x2; homr nativo quando o Audiveris
  não tem saída) símbolo a símbolo e grava ``itens.json``. Cada símbolo traz altura,
  figura, pausa, ligadura e se o homr e a tablatura concordam com ele.
- ``servir``: página local em que o dono vê o recorte original, a leitura desenhada e
  tocável, e marca só o que está errado. Cada compasso confirmado vai para o gabarito
  (formato 1), em escrita atômica. Re-confirmar um compasso sobrescreve só ele.

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

#: Formato do arquivo de gabarito (``--ouro``).
FORMATO_GABARITO = 1

#: Estados que o dono pode dar a um símbolo, na ordem em que o clique cicla.
ESTADOS = ("certo", "altura_errada", "figura_errada", "nao_existe")

#: Tamanho máximo da observação de um compasso.
TAMANHO_OBS_MAXIMO = 500

#: Maior número de notas faltando que o dono pode informar num compasso.
FALTANDO_MAXIMO = 50

#: Campos que ficam só na conferência (não entram no ``palpite``).
CAMPOS_DA_CONFERENCIA = ("idx", "homr_concorda", "tab_concorda")

#: Semitons de cada nota natural a partir de dó (MIDI mod 12).
SEMITONS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

#: Tipos de arquivo que o servidor entrega (só PNG dos recortes e a página).
_TIPO_PNG = "image/png"

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
        ValueError: se o recorte tem dois compassos com o mesmo número.
    """
    id_ = entrada["id"]
    fonte, caminho = _fonte_da_leitura(id_, execucao)
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
        "png": str((PASTA_RECORTES / f"{id_}.png").relative_to(RAIZ)),
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
    """Gabarito sem nenhuma resposta (formato 1).

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
        Gabarito formato 1.

    Raises:
        ValueError: se o arquivo existe e não está no formato 1.
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
    """Confere a observação de um compasso.

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


def validar_faltando(valor: object) -> int:
    """Confere o número de notas que faltaram no compasso.

    Args:
        valor: inteiro enviado pela página (ausente vale 0).

    Returns:
        O inteiro entre 0 e ``FALTANDO_MAXIMO``.

    Raises:
        ValueError: se não for inteiro, ou estiver fora da faixa.
    """
    if valor is None:
        return 0
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError("faltando deve ser inteiro")
    if not 0 <= valor <= FALTANDO_MAXIMO:
        raise ValueError(f"faltando fora de 0..{FALTANDO_MAXIMO}: {valor}")
    return valor


def validar_simbolos(lista: object, simbolos: list[dict]) -> dict[int, str]:
    """Confere os estados dados pelo dono a cada símbolo de um compasso.

    Args:
        lista: lista de ``{"idx", "dono"}`` enviada pela página.
        simbolos: símbolos do compasso em ``itens.json``.

    Returns:
        Mapa ``idx`` -> estado.

    Raises:
        ValueError: se a lista não for lista, se um estado não for um dos quatro, se um
            ``idx`` se repetir ou se os ``idx`` não forem exatamente os do compasso.
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
            f"idx não batem com os do compasso: {sorted(donos)} != {sorted(esperados)}"
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
    """Grava a resposta do dono num compasso, sem tocar nos outros.

    Toda a validação acontece antes de qualquer mudança: se der erro, o gabarito fica
    como estava. Os compassos já confirmados de outros recortes e de outros compassos
    são preservados.

    Args:
        gabarito: gabarito formato 1, alterado em lugar.
        itens_por_id: itens de ``preparar`` indexados por id de recorte.
        dados: corpo do POST: ``recorte``, ``compasso``, ``simbolos``, e opcionalmente
            ``faltando``, ``obs``, ``clave_certa`` e ``armadura_certa``.
        agora: carimbo da resposta (ISO).

    Returns:
        O registro do compasso gravado.

    Raises:
        ValueError: se qualquer campo estiver errado (recorte ou compasso desconhecidos,
            estado inválido, idx errado, faltando fora da faixa, obs longa).
    """
    if not isinstance(dados, dict):
        raise ValueError("o corpo deve ser um objeto JSON")
    recorte_id = dados.get("recorte")
    if not isinstance(recorte_id, str) or recorte_id not in itens_por_id:
        raise ValueError(f"recorte desconhecido: {recorte_id!r}")
    item = itens_por_id[recorte_id]
    numero = dados.get("compasso")
    if isinstance(numero, bool) or not isinstance(numero, str | int):
        raise ValueError("compasso deve ser texto ou inteiro")
    numero = str(numero)
    compasso = next((c for c in item["compassos"] if c["numero"] == numero), None)
    if compasso is None:
        raise ValueError(f"compasso {numero!r} não existe no recorte {recorte_id}")
    donos = validar_simbolos(dados.get("simbolos"), compasso["simbolos"])
    faltando = validar_faltando(dados.get("faltando"))
    obs = validar_obs(dados.get("obs"))
    recortes = gabarito.setdefault("recortes", {})
    atual = recortes.get(recorte_id, {})
    clave_certa = _booleano(dados.get("clave_certa"), atual.get("clave_certa", True))
    armadura_certa = _booleano(
        dados.get("armadura_certa"), atual.get("armadura_certa", True)
    )
    registro = {
        "simbolos": [
            {
                "idx": s["idx"],
                "palpite": _palpite(s),
                "dono": donos[s["idx"]],
            }
            for s in compasso["simbolos"]
        ],
        "faltando": faltando,
        "obs": obs,
        "confirmado": True,
        "respondido_em": agora,
    }
    gravado = recortes.setdefault(
        recorte_id,
        {"fonte": item["fonte"], "compassos": {}},
    )
    gravado["clave_certa"] = clave_certa
    gravado["armadura_certa"] = armadura_certa
    gravado.setdefault("compassos", {})[numero] = registro
    return registro


def esta_confirmado(gabarito: dict, recorte_id: str, numero: str) -> bool:
    """Se o compasso já foi confirmado no gabarito.

    Args:
        gabarito: gabarito formato 1.
        recorte_id: id do recorte.
        numero: número do compasso.

    Returns:
        True se ``confirmado`` é verdadeiro para o compasso.
    """
    recorte = gabarito.get("recortes", {}).get(recorte_id, {})
    registro = recorte.get("compassos", {}).get(numero, {})
    return registro.get("confirmado") is True


def progresso(itens: list[dict], gabarito: dict) -> dict:
    """Quantos compassos estão confirmados, no total e por recorte.

    Args:
        itens: itens de ``preparar``.
        gabarito: gabarito formato 1.

    Returns:
        ``{"confirmados", "total", "por_recorte": {id: [confirmados, total]}}``.
    """
    por_recorte: dict[str, list[int]] = {}
    confirmados = 0
    total = 0
    for item in itens:
        n = sum(
            1
            for c in item["compassos"]
            if esta_confirmado(gabarito, item["id"], c["numero"])
        )
        m = len(item["compassos"])
        por_recorte[item["id"]] = [n, m]
        confirmados += n
        total += m
    return {"confirmados": confirmados, "total": total, "por_recorte": por_recorte}


def proximo_pendente(
    itens: list[dict], gabarito: dict, atual: tuple[str, str] | None
) -> dict | None:
    """Próximo compasso não confirmado depois de ``atual``, dando a volta se preciso.

    Args:
        itens: itens na ordem da página.
        gabarito: gabarito formato 1.
        atual: ``(recorte, compasso)`` de partida, ou ``None``.

    Returns:
        ``{"recorte", "compasso"}`` do próximo pendente, ou ``None`` se não há nenhum.
    """
    pares = [(it["id"], c["numero"]) for it in itens for c in it["compassos"]]
    inicio = pares.index(atual) + 1 if atual in pares else 0
    for recorte_id, numero in pares[inicio:] + pares[:inicio]:
        if (recorte_id, numero) == atual:
            continue
        if not esta_confirmado(gabarito, recorte_id, numero):
            return {"recorte": recorte_id, "compasso": numero}
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
    gabarito é lido agora e regravado a cada confirmação.

    Args:
        itens_caminho: ``itens.json`` gerado por ``preparar``.
        ouro: arquivo de gabarito (``--ouro``); se não existe, começa vazio.
        porta: porta TCP (0 = uma livre).
        host: endereço de escuta (``0.0.0.0`` só dentro de container).

    Returns:
        O servidor; ``servidor.server_address[1]`` é a porta real.

    Raises:
        ValueError: se o gabarito existe e não está no formato 1.
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
                    {
                        "itens": ordem,
                        "gabarito": estado,
                        "progresso": prog,
                    },
                )
                return
            casa = re.fullmatch(r"/recorte/(R\d+)\.png", caminho)
            if casa and casa.group(1) in por_id:
                self._png(casa.group(1))
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def do_POST(self) -> None:
            """``/salvar``: grava a resposta de um compasso, em escrita atômica."""
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
                    proximo = proximo_pendente(
                        ordem,
                        gabarito,
                        (dados["recorte"], str(dados["compasso"])),
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
                    "proximo": proximo,
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
  grid-template-columns: 320px 1fr; min-height: 100vh; }
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
#png { width: 100%; height: auto; background: #fff; border: 1px solid var(--borda);
  border-radius: 4px; display: block; }
#osmd { background: #fff; border: 1px solid var(--borda); border-radius: 4px;
  margin: 10px 0; overflow-x: auto; min-height: 60px; }
.aviso { color: #a33; font-size: 13px; min-height: 1em; }
.barra { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0; }
button { font: inherit; padding: 6px 10px; border-radius: 6px;
  border: 1px solid var(--borda); background: var(--cartao); color: var(--texto);
  cursor: pointer; }
button.principal { background: var(--destaque); color: #fff; border-color: var(--destaque); }
.caixas label { margin-right: 14px; }
.compasso { border: 1px solid var(--borda); border-radius: 8px; padding: 10px;
  margin: 10px 0; background: var(--cartao); }
.compasso.conferido { opacity: .8; }
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
.chip.discorda { border-color: var(--discorda); border-style: solid; }
.campos { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 8px; }
.campos input[type="number"] { width: 70px; }
.campos input[type="text"] { width: 320px; max-width: 100%; }
.msg { font-size: 13px; min-height: 1em; margin-top: 4px; }
.status { font-size: 13px; min-height: 1em; margin: 4px 0; }
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
  <img id="png" alt="recorte original da pauta">
  <div class="barra">
    <button type="button" id="tocar-leitura" class="principal">tocar leitura</button>
    <button type="button" id="botao-parar">parar</button>
  </div>
  <div id="aviso" class="aviso"></div>
  <div id="osmd"></div>
  <div id="caixas" class="caixas barra"></div>
  <div id="status" class="status"></div>
  <div id="compassos"></div>
</main>
<script src="https://cdn.jsdelivr.net/npm/opensheetmusicdisplay@1.8.6/build/opensheetmusicdisplay.min.js"></script>
<script>
"use strict";
const ESTADOS = ["certo", "altura_errada", "figura_errada", "nao_existe"];
const ROTULO_ESTADO = {
  certo: "certo", altura_errada: "altura errada",
  figura_errada: "figura errada", nao_existe: "não existe"
};
const FIGURAS = {
  breve: "breve", whole: "semibreve", half: "mínima", quarter: "semínima",
  eighth: "colcheia", "16th": "semicolcheia", "32nd": "fusa",
  "64th": "semifusa", "128th": "sem-fusa"
};
const SEG_SEMINIMA = 60 / 72;

let itens = [];
let porId = {};
let gabarito = {recortes: {}};
let rascunho = {};
let atual = null;
let contextoAudio = null;
let mestre = null;
let tokenDesenho = 0;

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

function gravadoDoRecorte(id) {
  return (gabarito.recortes || {})[id] || {};
}

function gravadoDoCompasso(id, numero) {
  return (gravadoDoRecorte(id).compassos || {})[numero] || null;
}

function confirmado(id, numero) {
  const g = gravadoDoCompasso(id, numero);
  return !!(g && g.confirmado === true);
}

function inicializarRascunho() {
  rascunho = {};
  for (const it of itens) {
    const gr = gravadoDoRecorte(it.id);
    const r = {clave: gr.clave_certa !== false, armadura: gr.armadura_certa !== false,
               compassos: {}};
    for (const c of it.compassos) {
      const salvo = gravadoDoCompasso(it.id, c.numero);
      const donos = {};
      for (const s of c.simbolos) donos[s.idx] = "certo";
      let faltando = "0";
      let obs = "";
      if (salvo) {
        for (const x of salvo.simbolos) donos[x.idx] = x.dono;
        faltando = String(salvo.faltando || 0);
        obs = salvo.obs || "";
      }
      r.compassos[c.numero] = {donos: donos, faltando: faltando, obs: obs};
    }
    rascunho[it.id] = r;
  }
}

function progressoGlobal() {
  let n = 0, m = 0;
  for (const it of itens) for (const c of it.compassos) {
    m++;
    if (confirmado(it.id, c.numero)) n++;
  }
  return {n: n, m: m};
}

function progressoRecorte(it) {
  let n = 0;
  for (const c of it.compassos) if (confirmado(it.id, c.numero)) n++;
  return {n: n, m: it.compassos.length};
}

function pares() {
  const saida = [];
  for (const it of itens) for (const c of it.compassos) saida.push({id: it.id, num: c.numero});
  return saida;
}

function desenharLista() {
  const ul = dom("recortes");
  ul.textContent = "";
  for (const it of itens) {
    const p = progressoRecorte(it);
    ul.append(el("li", {classe: it.id === atual ? "ativo" : "",
                        onclick: () => abrir(it.id, null)}, [
      el("div", {texto: it.id + " · discordâncias " + it.discordancias}),
      el("div", {classe: "linha2", texto: it.canal + " · " + p.n + " de " + p.m +
                 " compassos conferidos"}),
    ]));
  }
  const g = progressoGlobal();
  dom("progresso").textContent = g.n + " de " + g.m + " compassos conferidos";
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

function chip(it, c, s, r) {
  const estado = r.donos[s.idx] || "certo";
  const motivos = [];
  if (s.homr_concorda === false) motivos.push("homr discorda");
  if (s.tab_concorda === false) motivos.push("tab discorda");
  const discorda = motivos.length > 0;
  const botao = el("button", {
    type: "button",
    classe: "chip estado-" + estado + (discorda ? " discorda" : ""),
    title: motivos.join("; "),
    onclick: () => {
      const i = ESTADOS.indexOf(r.donos[s.idx] || "certo");
      r.donos[s.idx] = ESTADOS[(i + 1) % ESTADOS.length];
      trocarBloco(it, c);
    },
  }, [
    el("span", {texto: rotuloSimbolo(s)}),
    el("small", {texto: ROTULO_ESTADO[estado] + (discorda ? " · " + motivos.join(", ") : "")}),
  ]);
  return botao;
}

function blocoCompasso(it, c) {
  const r = rascunho[it.id].compassos[c.numero];
  const feito = confirmado(it.id, c.numero);
  const bloco = el("section", {
    classe: "compasso" + (feito ? " conferido" : ""),
    id: "c-" + it.id + "-" + c.numero,
  });
  const cab = el("div", {classe: "cab"}, [
    el("strong", {texto: "compasso " + c.numero}),
    el("span", {texto: feito ? "conferido" : "pendente"}),
    el("button", {type: "button", texto: "tocar compasso",
                  onclick: () => tocarTrecho([c])}),
  ]);
  const grade = el("div", {classe: "grade"});
  let coluna = null;
  let tempoAtual = null;
  for (const s of c.simbolos) {
    if (coluna === null || s.t !== tempoAtual) {
      coluna = el("div", {classe: "coluna"});
      grade.append(coluna);
      tempoAtual = s.t;
    }
    coluna.append(chip(it, c, s, r));
  }
  if (c.simbolos.length === 0) grade.append(el("em", {texto: "sem símbolos neste compasso"}));
  const campoFaltando = el("input", {type: "number", min: "0", max: "50", step: "1"});
  campoFaltando.value = r.faltando;
  campoFaltando.addEventListener("input", () => { r.faltando = campoFaltando.value; });
  const campoObs = el("input", {type: "text", maxlength: "500", placeholder: "observação (opcional)"});
  campoObs.value = r.obs;
  campoObs.addEventListener("input", () => { r.obs = campoObs.value; });
  const msg = el("div", {classe: "msg"});
  bloco.append(cab, grade, el("div", {classe: "campos"}, [
    el("label", {}, ["notas faltando ", campoFaltando]),
    el("label", {}, ["obs ", campoObs]),
    el("button", {type: "button", classe: "principal", texto: "confirmar compasso",
                  onclick: () => confirmar(it, c, msg)}),
  ]), msg);
  return bloco;
}

function trocarBloco(it, c) {
  const antigo = dom("c-" + it.id + "-" + c.numero);
  if (antigo) antigo.replaceWith(blocoCompasso(it, c));
}

function desenharCompassos(it) {
  const area = dom("compassos");
  area.textContent = "";
  for (const c of it.compassos) area.append(blocoCompasso(it, c));
}

async function desenharPartitura(it) {
  const alvo = dom("osmd");
  const meu = ++tokenDesenho;
  alvo.textContent = "";
  if (typeof opensheetmusicdisplay === "undefined" || !opensheetmusicdisplay.OpenSheetMusicDisplay) {
    aviso("Leitura desenhada indisponível (a biblioteca de desenho não carregou). Use a imagem e os chips.");
    return;
  }
  try {
    const o = new opensheetmusicdisplay.OpenSheetMusicDisplay(alvo, {
      autoResize: true, drawTitle: false,
    });
    await o.load(it.musicxml);
    if (meu !== tokenDesenho) return;
    o.render();
    aviso("");
  } catch (erro) {
    if (meu === tokenDesenho) aviso("Leitura desenhada falhou: " + erro);
  }
}

function abrir(id, numero) {
  atual = id;
  const it = porId[id];
  dom("titulo").textContent = id + " · " + it.canal + " · leitura " + it.fonte +
    " · discordâncias " + it.discordancias;
  dom("png").src = "/recorte/" + id + ".png";
  desenharLista();
  desenharCaixas(it);
  desenharCompassos(it);
  desenharPartitura(it);
  if (numero !== null && numero !== undefined) {
    const alvo = dom("c-" + id + "-" + numero);
    if (alvo) alvo.scrollIntoView({behavior: "smooth", block: "start"});
  }
}

async function confirmar(it, c, msg) {
  const r = rascunho[it.id];
  const rc = r.compassos[c.numero];
  const faltando = Number(rc.faltando || 0);
  if (!Number.isInteger(faltando) || faltando < 0 || faltando > 50) {
    msg.textContent = "notas faltando: inteiro de 0 a 50";
    return;
  }
  const corpo = {
    recorte: it.id,
    compasso: c.numero,
    simbolos: c.simbolos.map((s) => ({idx: s.idx, dono: rc.donos[s.idx] || "certo"})),
    faltando: faltando,
    obs: rc.obs,
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
  const gr = gabarito.recortes[it.id] || (gabarito.recortes[it.id] = {compassos: {}});
  gr.clave_certa = r.clave;
  gr.armadura_certa = r.armadura;
  gr.compassos[c.numero] = dados.registro;
  desenharLista();
  const p = dados.proximo;
  mostrarStatus("gravado às " + dados.salvo_em + " · " + dados.progresso.confirmados +
         " de " + dados.progresso.total + " compassos conferidos" +
         (p ? "" : " · todos os compassos conferidos"));
  if (p && p.recorte !== it.id) {
    abrir(p.recorte, p.compasso);
  } else {
    desenharCompassos(it);
    if (p) {
      const alvo = dom("c-" + it.id + "-" + p.compasso);
      if (alvo) alvo.scrollIntoView({behavior: "smooth", block: "start"});
    }
  }
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
  const pendente = pares().find((p) => !confirmado(p.id, p.num));
  abrir(pendente ? pendente.id : itens[0].id, pendente ? pendente.num : null);
  const progresso = progressoGlobal();
  mostrarStatus(progresso.n + " de " + progresso.m + " compassos conferidos");
}

dom("tocar-leitura").addEventListener("click", () => {
  const it = porId[atual];
  if (it) tocarTrecho(it.compassos);
});
dom("botao-parar").addEventListener("click", pararTudo);
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
