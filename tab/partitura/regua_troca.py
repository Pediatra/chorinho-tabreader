"""F0.2 da partitura: a troca do compasso pelo homr, julgada pela tab (rodada 3102).

Aplica ``trocar_compassos_pelo_homr`` (rodada 3025, razão ``RAZAO_TROCA_HOMR``) às leituras
do Audiveris com armadura herdada, usando a leitura do homr, **sem** olhar a tab. Depois
julga o resultado **com** a tab, com ``contar`` no modo ``exato``: conta consertadas,
quebradas, inventadas novas e compassos trocados, por recorte, por tela e por vídeo.

Conjuntos: R01–R12 (índice ``ouro``) e as 7 telas novas da Gymnopédie (telas 2, 4, 6, 8,
10, 11 e 12). Só lê o que está gravado e só grava o JSON na pasta da frente 0.

Uso (na raiz do projeto)::

    python -m tab.partitura_regua_troca
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from tab.comum.caminhos import PART_FRENTE_0
from tab.partitura.avaliar import _carregar_ouro, alinhar, contar, referencia_do_recorte
from tab.partitura.gabarito import ler_partitura
from tab.partitura.pareamento import (
    CONDICAO_MUSICXML,
    CONDICAO_OMR,
    INDICE,
    RAZAO_TROCA_HOMR,
    eventos_da_partitura,
    trocar_compassos_pelo_homr,
)
from tab.partitura.video import CONDICAO_HOMR, PASTA_VIDEO

#: Vídeo da Gymnopédie no acervo de pautas (pasta em ``PASTA_VIDEO``).
STEM_GYMNOPEDIE = "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"

#: Telas da Gymnopédie que não estão em R01–R12 (as telas 1, 3, 5, 7 e 9 são R08–R12).
TELAS_NOVAS = [2, 4, 6, 8, 10, 11, 12]

#: Número de verificação da referência só Audiveris em R01–R12 (CA1).
ANTES_ESPERADO = [546, 496, 9, 41, 3]

SAIDA_JSON = PART_FRENTE_0 / "troca.json"
ESCALA = 2.0
CHAVES = ["referencia", "certas", "altura_errada", "faltando", "inventada"]


def _midis(eventos: list) -> list[frozenset[int]]:
    """Alturas (MIDI) de cada evento, na ordem.

    Args:
        eventos: eventos de ``eventos_da_partitura`` ou de ``trocar_compassos_pelo_homr``.

    Returns:
        Um conjunto de alturas por evento.
    """
    return [frozenset(e.midis) for e in eventos]


def _numeros(musicxml: Path) -> list[int]:
    """Número de cada compasso de uma leitura, na ordem.

    Args:
        musicxml: leitura ``score-partwise``.

    Returns:
        Os números dos compassos, como os dá ``ler_partitura``.
    """
    return [medida["numero"] for medida in ler_partitura(musicxml)["compassos"]]


def _certos(
    lib: list[frozenset[int]], ref: list[frozenset[int]]
) -> list[frozenset[int]]:
    """Para cada evento da tab, as alturas que a leitura acertou (nota a nota).

    Usa o mesmo alinhamento de ``contar`` (``alinhar``), no modo exato: a nota certa é a
    que está nos dois lados do par casado, como em ``certas`` do ``contar``.

    Args:
        lib: alturas da leitura, na ordem.
        ref: alturas da tab, na ordem.

    Returns:
        Um conjunto de alturas certas por evento da tab, na ordem da tab.
    """
    certo: list[frozenset[int]] = [frozenset()] * len(ref)
    for op, i, j in alinhar(lib, ref):
        if op == "casa":
            certo[j] = lib[i] & ref[j]
    return certo


def _oitavas(lib: list[frozenset[int]], ref: list[frozenset[int]]) -> int:
    """Eventos casados que diferem da tab por exatamente uma oitava (harmônico, 3013).

    Args:
        lib: alturas da leitura, na ordem.
        ref: alturas da tab, na ordem.

    Returns:
        Quantos eventos casados têm todas as alturas deslocadas de 12 semitons da tab.
    """
    total = 0
    for op, i, j in alinhar(lib, ref):
        if op != "casa" or lib[i] == ref[j]:
            continue
        acima = frozenset(m + 12 for m in ref[j])
        abaixo = frozenset(m - 12 for m in ref[j])
        if lib[i] in (acima, abaixo):
            total += 1
    return total


def _figuras(
    aud_eventos: list,
    homr_eventos: list,
    trocados: list[int],
    na: list[int],
    nh: list[int],
) -> dict[str, int]:
    """Compara a figura do homr com a do Audiveris, nos compassos trocados.

    Para cada símbolo do homr num compasso trocado, procura o símbolo do Audiveris de mesma
    altura no mesmo compasso. A tab não vê figura: essa conta é só a das notas trocadas.
    O compasso do homr é o da mesma posição do Audiveris (``nh[k]`` para ``na[k]``).

    Args:
        aud_eventos: eventos do Audiveris (antes da troca).
        homr_eventos: eventos do homr.
        trocados: números dos compassos trocados (do Audiveris).
        na: número de cada compasso do Audiveris, na ordem.
        nh: número de cada compasso do homr, na ordem.

    Returns:
        ``{"notas": n, "sem_par": n, "figura_diferente": n}``.
    """
    contagem = {"notas": 0, "sem_par": 0, "figura_diferente": 0}
    for compasso_aud in trocados:
        compasso_homr = nh[na.index(compasso_aud)]
        figura_aud: dict[int, str] = {}
        for evento in aud_eventos:
            if evento.compasso != compasso_aud:
                continue
            for simbolo in evento.simbolos:
                figura_aud.setdefault(simbolo["midi"], simbolo["figura"])
        for evento in homr_eventos:
            if evento.compasso != compasso_homr:
                continue
            for simbolo in evento.simbolos:
                contagem["notas"] += 1
                figura = figura_aud.get(simbolo["midi"])
                if figura is None:
                    contagem["sem_par"] += 1
                elif figura != simbolo["figura"]:
                    contagem["figura_diferente"] += 1
    return contagem


def _medir(
    rid: str,
    video: str,
    tela: int,
    notas: list[dict],
    aud_xml: Path,
    omr: Path,
    homr_xml: Path,
    x0: float,
    x1: float,
) -> dict:
    """Mede um recorte: antes (só Audiveris) e depois (troca pelo homr), contra a tab.

    Args:
        rid: identificador do recorte (``R01`` ou ``T02``).
        video: campo ``video`` do gabarito.
        tela: número da tela no gabarito.
        notas: notas da tela no gabarito de tab.
        aud_xml: leitura Audiveris com armadura herdada (``saida.musicxml``).
        omr: ``.omr`` da mesma imagem (``entrada.omr``).
        homr_xml: leitura do homr (``saida.musicxml``); pode não existir.
        x0: início da janela horizontal do recorte.
        x1: fim da janela horizontal do recorte.

    Returns:
        Documento com ``antes``, ``depois``, ``consertadas``, ``quebradas``,
        ``inventadas_novas``, ``trocados``, ``compasso_nao_troca``, ``oitavas``,
        ``figuras`` e ``erro`` quando o homr não é lido.
    """
    ref_eventos = referencia_do_recorte(notas, x0, x1)
    ref = [frozenset(e) for e in ref_eventos]
    aud = eventos_da_partitura(aud_xml, omr, x0, ESCALA)
    lib_antes = _midis(aud)
    antes, _ = contar(lib_antes, ref, "exato")
    doc: dict = {
        "id": rid,
        "video": video,
        "tela": tela,
        "caixa_recorte": [x0, x1],
        "antes": antes,
        "trocados": [],
        "compasso_nao_troca": False,
        "figuras": {"notas": 0, "sem_par": 0, "figura_diferente": 0},
        "erro": None,
    }
    depois_eventos = aud
    homr_eventos: list = []
    if homr_xml.exists():
        try:
            na = _numeros(aud_xml)
            nh = _numeros(homr_xml)
            homr_eventos = eventos_da_partitura(homr_xml, None, x0, ESCALA)
        except (ValueError, OSError) as falha:
            doc["erro"] = f"homr: {falha}"
        else:
            doc["compasso_nao_troca"] = len(na) != len(nh)
            depois_eventos, trocados = trocar_compassos_pelo_homr(
                aud, na, homr_eventos, nh, RAZAO_TROCA_HOMR
            )
            doc["trocados"] = trocados
            doc["figuras"] = _figuras(aud, homr_eventos, trocados, na, nh)
    else:
        doc["erro"] = "sem homr"
    lib_depois = _midis(depois_eventos)
    depois, _ = contar(lib_depois, ref, "exato")
    certo_antes = _certos(lib_antes, ref)
    certo_depois = _certos(lib_depois, ref)
    consertadas = [
        (j, m)
        for j in range(len(ref))
        for m in sorted(certo_depois[j] - certo_antes[j])
    ]
    quebradas = [
        (j, m)
        for j in range(len(ref))
        for m in sorted(certo_antes[j] - certo_depois[j])
    ]
    doc.update(
        {
            "depois": depois,
            "consertadas": len(consertadas),
            "quebradas": len(quebradas),
            "inventadas_novas": depois["inventada"] - antes["inventada"],
            "oitavas": _oitavas(lib_depois, ref),
            "casos": {
                "consertadas": [{"evento": j, "midi": m} for j, m in consertadas],
                "quebradas": [{"evento": j, "midi": m} for j, m in quebradas],
            },
        }
    )
    return doc


def _recortes_ouro(ouro: dict[str, list[dict]]) -> list[dict]:
    """Os 12 recortes de R01–R12, medidos com o gabarito de tab.

    Args:
        ouro: mapa ``video`` -> gabaritos, de ``_carregar_ouro``.

    Returns:
        Um documento por recorte (ver ``_medir``).
    """
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    base = Path(INDICE).parent.parent
    documentos = []
    for entrada in [e for e in indice if e["origem"] == "ouro"]:
        rid = entrada["id"]
        gabarito = ouro[entrada["video"]][0]
        tela = next(t for t in gabarito["telas"] if t["id"] == entrada["tela"])
        x0, _, x1, _ = entrada["caixa_recorte"]
        pasta = base / "omr"
        documentos.append(
            _medir(
                rid,
                entrada["video"],
                entrada["tela"],
                tela["notas"],
                pasta / "audiveris" / f"{CONDICAO_MUSICXML}" / rid / "saida.musicxml",
                pasta / "audiveris" / CONDICAO_OMR / rid / "entrada.omr",
                pasta / "homr" / CONDICAO_HOMR / rid / "saida.musicxml",
                x0,
                x1,
            )
        )
    return documentos


def _recortes_gymnopedie(ouro: dict[str, list[dict]]) -> list[dict]:
    """As 7 telas novas da Gymnopédie, medidas com o gabarito de tab.

    Args:
        ouro: mapa ``video`` -> gabaritos, de ``_carregar_ouro``.

    Returns:
        Um documento por tela nova (ver ``_medir``).
    """
    pasta_video = PASTA_VIDEO / STEM_GYMNOPEDIE
    doc = json.loads(
        (pasta_video / f"{STEM_GYMNOPEDIE}.partitura.json").read_text(encoding="utf-8")
    )
    video = next(
        e["video"]
        for e in json.loads(INDICE.read_text(encoding="utf-8"))
        if e["origem"] == "ouro" and e["id"] == "R08"
    )
    gabarito = ouro[video][0]
    documentos = []
    for pauta in doc["pautas"]:
        if pauta["tela"] not in TELAS_NOVAS:
            continue
        rid = pauta["recorte"]
        tela = next(t for t in gabarito["telas"] if t["id"] == pauta["tela"])
        x0, _, x1, _ = pauta["caixa_quadro"]
        omr = pasta_video / "omr"
        documentos.append(
            _medir(
                rid,
                video,
                pauta["tela"],
                tela["notas"],
                omr / "audiveris" / f"{CONDICAO_MUSICXML}" / rid / "saida.musicxml",
                omr / "audiveris" / CONDICAO_OMR / rid / "entrada.omr",
                omr / "homr" / CONDICAO_HOMR / rid / "saida.musicxml",
                x0,
                x1,
            )
        )
    return documentos


def _somar_grupo(documentos: list[dict]) -> dict:
    """Totais de um conjunto de recortes: contagens da tab e os números da F0.2.

    Args:
        documentos: saída de ``_medir``.

    Returns:
        Totais de ``antes``, ``depois``, consertadas, quebradas, inventadas novas, trocados,
        compassos sem troca possível, oitavas e figuras.
    """
    antes = defaultdict(int)
    depois = defaultdict(int)
    grupo: dict = {
        "recortes": len(documentos),
        "consertadas": 0,
        "quebradas": 0,
        "inventadas_novas": 0,
        "compassos_trocados": 0,
        "compasso_nao_troca": 0,
        "oitavas": 0,
        "figuras": {"notas": 0, "sem_par": 0, "figura_diferente": 0},
        "sem_homr": 0,
    }
    for d in documentos:
        for chave in CHAVES:
            antes[chave] += d["antes"].get(chave, 0)
            depois[chave] += d["depois"].get(chave, 0) if "depois" in d else 0
        grupo["consertadas"] += d["consertadas"]
        grupo["quebradas"] += d["quebradas"]
        grupo["inventadas_novas"] += d["inventadas_novas"]
        grupo["compassos_trocados"] += len(d["trocados"])
        grupo["compasso_nao_troca"] += int(d["compasso_nao_troca"])
        grupo["oitavas"] += d["oitavas"]
        for chave, valor in d["figuras"].items():
            grupo["figuras"][chave] += valor
        grupo["sem_homr"] += int(d["erro"] == "sem homr")
    grupo["antes"] = dict(antes)
    grupo["depois"] = dict(depois)
    grupo["saldo"] = (
        grupo["consertadas"] - grupo["quebradas"] - grupo["inventadas_novas"]
    )
    return grupo


def _videos(documentos: list[dict]) -> dict[str, list[dict]]:
    """Agrupa os recortes por vídeo (campo ``video``).

    Args:
        documentos: saída de ``_medir``.

    Returns:
        Mapa ``video`` -> lista de recortes.
    """
    grupos: dict[str, list[dict]] = defaultdict(list)
    for d in documentos:
        grupos[d["video"]].append(d)
    return grupos


def medir_tudo() -> dict:
    """Roda a F0.2 nos conjuntos definidos e devolve o documento de saída.

    Returns:
        Documento com ``recortes`` (todos), ``por_video``, ``total``, ``sem_gymnopedie``,
        ``antes_esperado`` e ``antes_ok``.
    """
    ouro = _carregar_ouro()
    documentos = _recortes_ouro(ouro) + _recortes_gymnopedie(ouro)
    sem_gym = [d for d in documentos if d["video"] != _gym_video(ouro)]
    antes_r = [d for d in documentos if d["id"].startswith("R")]
    antes_total = _somar_grupo(antes_r)["antes"]
    antes_vetor = [antes_total.get(c, 0) for c in CHAVES]
    return {
        "frente": "F0.2",
        "rodada": 3102,
        "razao": RAZAO_TROCA_HOMR,
        "recortes": documentos,
        "total_r01_r12": _somar_grupo(antes_r),
        "total_novas_gym": _somar_grupo(
            [d for d in documentos if d["id"].startswith("T")]
        ),
        "por_video": {v: _somar_grupo(g) for v, g in _videos(documentos).items()},
        "sem_gymnopedie": _somar_grupo(sem_gym),
        "antes_esperado": ANTES_ESPERADO,
        "antes_ok": antes_vetor == ANTES_ESPERADO,
    }


def _gym_video(ouro: dict[str, list[dict]]) -> str:
    """Campo ``video`` da Gymnopédie (o do recorte R08).

    Args:
        ouro: mapa ``video`` -> gabaritos, de ``_carregar_ouro``.

    Returns:
        O campo ``video`` do índice para o recorte R08.
    """
    return next(
        e["video"]
        for e in json.loads(INDICE.read_text(encoding="utf-8"))
        if e["origem"] == "ouro" and e["id"] == "R08"
    )


def main(argv: list[str] | None = None) -> int:
    """Roda a F0.2 e grava ``troca.json`` na pasta da frente 0.

    Args:
        argv: argumentos da linha de comando (não há opções).

    Returns:
        Zero em caso de sucesso.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    documento = medir_tudo()
    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_JSON.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2, default=list),
        encoding="utf-8",
    )
    print(
        f"antes R01-R12 {documento['total_r01_r12']['antes']}"
        f" (esperado {ANTES_ESPERADO}, ok={documento['antes_ok']})"
    )
    for nome in ("total_r01_r12", "total_novas_gym", "sem_gymnopedie"):
        g = documento[nome]
        print(
            f"{nome}: recortes {g['recortes']}, consertadas {g['consertadas']},"
            f" quebradas {g['quebradas']}, inventadas novas {g['inventadas_novas']},"
            f" saldo {g['saldo']}, trocados {g['compassos_trocados']},"
            f" sem troca {g['compasso_nao_troca']}, oitavas {g['oitavas']},"
            f" figuras {g['figuras']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
