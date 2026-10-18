"""E1 da partitura: itens da conferência do dono, servidos por ``partitura_gabarito servir``.

Um item por recorte com símbolos a julgar. Entram só os símbolos que o dono confere:

- as notas completadas pela tab **com figura** (``figura`` não ``None`` em ``e1.json``); as
  que ficam ``null`` não vão para a conferência (regra da sessão principal);
- as notas do homr de R01–R12 que o pareamento acrescentou (``origem`` ``homr``).

O desenho de cada item tem só as notas a julgar, cada uma com a sua figura, uma após a
outra em cada compasso (``_musicxml_das_julgadas``): o dono clica nelas e compara com a
imagem do recorte. O dono marca ``certo`` ou ``figura_errada``.

Grava ``itens_e1.json`` e a cópia vazia do gabarito (``ouro_e1_copia.json``) na pasta da
frente E. O gabarito real (``data/gold``) não é tocado.

Uso (dentro do container, na raiz do projeto)::

    python -m tab.partitura_completar_itens
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .caminhos import PART_FRENTE_E, SAIDA
from .partitura_completar import SAIDA_JSON as E1_JSON
from .partitura_completar import STEMS
from .partitura_gabarito import _relativo_a_raiz, gabarito_vazio, ler_partitura
from .partitura_pareamento import INDICE, _carregar_ouro, _parear_recorte
from .partitura_video import PASTA_VIDEO

ITENS = PART_FRENTE_E / "itens_e1.json"
OURO_COPIA = PART_FRENTE_E / "ouro_e1_copia.json"
FORMATO_ITENS = 1
DURACAO = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "16th": 0.25,
    "32nd": 0.125,
}
NOMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _nome(midi: int) -> str:
    """Nome de uma altura MIDI, como ``E5`` (oitava científica).

    Args:
        midi: altura escrita em MIDI.

    Returns:
        Nome da nota com a oitava.
    """
    return f"{NOMES[midi % 12]}{midi // 12 - 1}"


def _simbolo(
    idx: int,
    compasso: str,
    nome: str,
    midi: int,
    figura: str | None,
    pontuada: bool,
    voz: str,
    origem: str,
    x: float | None,
) -> dict:
    """Símbolo no formato que a conferência usa (campos de ``_palpite`` completos).

    Args:
        idx: posição do símbolo no item.
        compasso: número do compasso.
        nome: nome da nota.
        midi: altura escrita.
        figura: figura do MusicXML, ou ``None``.
        pontuada: se a figura é pontuada.
        voz: voz.
        origem: ``tab_completada`` ou ``homr``.
        x: posição x no quadro (ordena as julgadas no compasso), ou None.

    Returns:
        Símbolo com ``idx`` e os campos da leitura.
    """
    return {
        "idx": idx,
        "compasso": compasso,
        "t": 0.0,
        "t_global": 0.0,
        "pausa": False,
        "midi": midi,
        "nome": nome,
        "figura": figura,
        "pontuada": pontuada,
        "duracao": DURACAO.get(figura, 0.0) * (1.5 if pontuada else 1.0),
        "acorde": False,
        "voz": str(voz),
        "ligadura_inicio": False,
        "ligadura_fim": False,
        "graca": False,
        "notacoes": [],
        "origem": origem,
        "x": x,
    }


#: Divisões por semínima no MusicXML gerado (cobre a fusa).
DIVISOES = 8
PASSOS = [
    ("C", 0),
    ("C", 1),
    ("D", 0),
    ("D", 1),
    ("E", 0),
    ("F", 0),
    ("F", 1),
    ("G", 0),
    ("G", 1),
    ("A", 0),
    ("A", 1),
    ("B", 0),
]
PASSOS_BEMOL = [
    ("C", 0),
    ("D", -1),
    ("D", 0),
    ("E", -1),
    ("E", 0),
    ("F", 0),
    ("G", -1),
    ("G", 0),
    ("A", -1),
    ("A", 0),
    ("B", -1),
    ("B", 0),
]


def _musicxml_das_julgadas(leitura: dict, compassos: list[dict]) -> str:
    """MusicXML com só as notas a julgar, uma após a outra em cada compasso.

    A conferência casa nota desenhada e símbolo pela altura dentro do compasso. Com a
    leitura inteira do Audiveris desenhada, as poucas notas a julgar casavam com notas que
    não eram delas. Desenhando só as julgadas, cada nota desenhada é um símbolo, com a
    figura que o dono confere contra a imagem. Compasso sem nota leva pausa de compasso.

    Args:
        leitura: leitura do recorte (``clave``, ``armadura``, ``compasso_formula``).
        compassos: compassos do item, com os ``simbolos`` a julgar já em ordem.

    Returns:
        O documento MusicXML (partwise, uma parte).
    """
    armadura = leitura["armadura"] or 0
    passos = PASSOS_BEMOL if armadura < 0 else PASSOS
    clave = leitura["clave"] or {"sign": "G", "line": 2}
    formula = leitura["compasso_formula"]
    medidas = []
    for k, compasso in enumerate(compassos):
        partes = []
        if k == 0:
            tempo = (
                f"<time><beats>{formula['beats']}</beats>"
                f"<beat-type>{formula['beat_type']}</beat-type></time>"
                if formula
                else ""
            )
            partes.append(
                f"<attributes><divisions>{DIVISOES}</divisions>"
                f"<key><fifths>{armadura}</fifths></key>{tempo}"
                f"<clef><sign>{clave['sign']}</sign><line>{clave['line']}</line></clef>"
                "</attributes>"
            )
        if not compasso["simbolos"]:
            partes.append(
                f'<note><rest measure="yes"/><duration>{DIVISOES * 4}</duration>'
                "<voice>1</voice></note>"
            )
        for s in compasso["simbolos"]:
            passo, alter = passos[s["midi"] % 12]
            oitava = s["midi"] // 12 - 1
            duracao = max(1, round(s["duracao"] * DIVISOES))
            altera = f"<alter>{alter}</alter>" if alter else ""
            ponto = "<dot/>" if s["pontuada"] else ""
            partes.append(
                f"<note><pitch><step>{passo}</step>{altera}<octave>{oitava}</octave>"
                f"</pitch><duration>{duracao}</duration><voice>1</voice>"
                f"<type>{s['figura']}</type>{ponto}</note>"
            )
        medidas.append(f'<measure number="{k + 1}">{"".join(partes)}</measure>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<score-partwise version="3.1"><part-list><score-part id="P1">'
        "<part-name>E1</part-name></score-part></part-list>"
        f'<part id="P1">{"".join(medidas)}</part></score-partwise>'
    )


def _item(
    id_: str,
    origem: str,
    video: str,
    tela: int,
    xml,
    png,
    simbolos_a_julgar: list[dict],
) -> dict:
    """Item de um recorte: leitura em MusicXML e a lista dos símbolos a julgar.

    Args:
        id_: id do recorte.
        origem: ``ouro`` (R01–R12) ou ``produto``.
        video: ``canal/arquivo``.
        tela: tela do recorte.
        xml: MusicXML da leitura (``x2_margem_herdada``).
        png: PNG do recorte.
        simbolos_a_julgar: símbolos com ``compasso`` e ``idx`` já definidos.

    Returns:
        Item no formato da conferência.
    """
    leitura = ler_partitura(xml)
    por_compasso: dict[str, list[dict]] = {}
    for s in simbolos_a_julgar:
        por_compasso.setdefault(s["compasso"], []).append(s)
    compassos = [
        {
            "numero": c["numero"],
            "duracao": c["duracao"],
            "simbolos": por_compasso.get(c["numero"], []),
        }
        for c in leitura["compassos"]
    ]
    # símbolos cujo compasso não existe na leitura entram num compasso extra, para não sumir
    numeros = {c["numero"] for c in leitura["compassos"]}
    extra = [s for c, lista in por_compasso.items() if c not in numeros for s in lista]
    if extra:
        compassos.append({"numero": "extra", "duracao": 0.0, "simbolos": extra})
    # Em cada compasso, as julgadas uma após a outra, pela posição x: o t é o do desenho.
    for compasso in compassos:
        compasso["simbolos"].sort(key=lambda s: (s["x"] is None, s["x"] or 0.0))
        t = 0.0
        for s in compasso["simbolos"]:
            s["t"] = t
            t += s["duracao"]
    return {
        "id": id_,
        "origem": origem,
        "canal": video.split("/", 1)[0],
        "video": video,
        "tela": tela,
        "fonte": "tab_completada",
        "png": _relativo_a_raiz(png),
        "largura_png": _tamanho_png(png)[0],
        "altura_png": _tamanho_png(png)[1],
        "musicxml": _musicxml_das_julgadas(leitura, compassos),
        "clave": leitura["clave"],
        "armadura": leitura["armadura"],
        "compasso_formula": leitura["compasso_formula"],
        "compassos": compassos,
        "n_compassos": len(compassos),
        "n_notas": len(simbolos_a_julgar),
        "n_pausas": 0,
        "discordancias": 0,
    }


def _tamanho_png(caminho: Path) -> tuple[int, int]:
    """Largura e altura de um PNG, lidas do cabeçalho IHDR.

    Args:
        caminho: arquivo PNG.

    Returns:
        ``(largura, altura)`` em pixels.
    """
    with caminho.open("rb") as arquivo:
        cabecalho = arquivo.read(24)
    return int.from_bytes(cabecalho[16:20], "big"), int.from_bytes(
        cabecalho[20:24], "big"
    )


def _completadas_com_figura() -> list[dict]:
    """Notas completadas da E1 que têm figura (as que vão para a conferência).

    Returns:
        Lista do ``e1.json`` com ``figura`` não ``None``.
    """
    documento = json.loads(E1_JSON.read_text(encoding="utf-8"))
    return [n for n in documento["completadas"] if n["figura"] is not None]


def main(argv: list[str] | None = None) -> int:
    """Gera os itens da E1 e a cópia vazia do gabarito.

    Args:
        argv: sem argumentos.

    Returns:
        Zero.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    completadas = _completadas_com_figura()
    itens: list[dict] = []
    total_completadas = 0
    total_homr = 0
    ouro = _carregar_ouro()
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    # R01–R12: notas do homr (origem homr) + completadas com figura
    for entrada in [e for e in indice if e["origem"] == "ouro"]:
        rid = entrada["id"]
        doc = _parear_recorte(entrada, ouro)
        julgar: list[dict] = []
        for evento in doc["partitura"]:
            for s in evento["simbolos"]:
                if s.get("origem") == "homr":
                    total_homr += 1
                    julgar.append(
                        _simbolo(
                            0,
                            str(evento["compasso"]),
                            s.get("nome", "?"),
                            int(s["midi"]),
                            s.get("figura"),
                            bool(s.get("pontuada")),
                            str(s.get("voz", "1")),
                            "homr",
                            evento.get("x_quadro"),
                        )
                    )
        for n in [c for c in completadas if c["recorte"] == rid]:
            total_completadas += 1
            julgar.append(
                _simbolo(
                    0,
                    str(n["compasso"]),
                    _nome(n["midi"]),
                    n["midi"],
                    n["figura"],
                    bool(n["pontuada"]),
                    str(n["voz"]),
                    "tab_completada",
                    n["x"],
                )
            )
        if not julgar:
            continue
        for k, s in enumerate(julgar):
            s["idx"] = k
        xml = (
            SAIDA
            / "partitura"
            / "p1"
            / "omr"
            / "audiveris"
            / "x2_margem_herdada"
            / rid
            / "saida.musicxml"
        )
        png = SAIDA / "partitura" / "p1" / "recortes_margem" / f"{rid}.png"
        itens.append(
            _item(rid, "ouro", entrada["video"], entrada["tela"], xml, png, julgar)
        )
    # produtos: as completadas com figura, por recorte T
    for stem in STEMS:
        pasta = PASTA_VIDEO / stem
        recortes = sorted({c["recorte"] for c in completadas if c["video"] == stem})
        for rec in recortes:
            julgar = []
            tela = next(
                c["tela"]
                for c in completadas
                if c["video"] == stem and c["recorte"] == rec
            )
            for n in [
                c for c in completadas if c["video"] == stem and c["recorte"] == rec
            ]:
                total_completadas += 1
                julgar.append(
                    _simbolo(
                        0,
                        str(n["compasso"]),
                        _nome(n["midi"]),
                        n["midi"],
                        n["figura"],
                        bool(n["pontuada"]),
                        str(n["voz"]),
                        "tab_completada",
                        n["x"],
                    )
                )
            for k, s in enumerate(julgar):
                s["idx"] = k
            xml = (
                pasta
                / "omr"
                / "audiveris"
                / "x2_margem_herdada"
                / rec
                / "saida.musicxml"
            )
            png = pasta / "recortes" / f"{rec}.png"
            itens.append(
                _item(
                    f"{stem[:20]}__{rec}",
                    "produto",
                    f"{stem}.mp4",
                    tela,
                    xml,
                    png,
                    julgar,
                )
            )
    documento = {
        "formato": FORMATO_ITENS,
        "gerado_por": "tab.partitura_completar_itens",
        "itens": itens,
    }
    ITENS.parent.mkdir(parents=True, exist_ok=True)
    ITENS.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OURO_COPIA.write_text(
        json.dumps(gabarito_vazio(ITENS), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"itens {len(itens)}; completadas com figura {total_completadas}; "
        f"homr R01–R12 {total_homr}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
