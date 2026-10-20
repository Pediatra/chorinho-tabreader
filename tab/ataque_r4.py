"""R4a: o arco real no ajuste fino (rodada 0202) — alvos de técnica e medida.

Duas partes:

- **alvos**: a técnica que cada nota real do cache do ajuste fino
  (``data/saida/n4/cache``) ensina, tirada do gabarito de ataque do R2;
- **medida**: lê as telas conferidas com o modelo da dobra que não viu o vídeo (a T8.2 com
  a dobra 0) e monta a matriz ouro × previsto do ataque e o acerto da casa.

Uso::

    python -m tab.ataque_r4 medir --versao atq --semente 1
"""

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from tab import caminhos, detector_tab, leitor, painel
from tab.ataque_base import ataque_previsto, parear, taxas

#: Técnicas do modelo que tiram o ataque: só elas são supervisionadas nas telas reais.
TECNICAS_SUPERVISIONADAS = ("h", "p", "/", "\\", "lig", "orn", "enfeite")

#: Motivo do dono (nota "nao") -> técnica do modelo na nota de chegada. Slide à parte.
TECNICA_DO_MOTIVO = {"h": "h", "p": "p", "prolongamento": "lig", "mordente": "orn"}

#: Vídeos fora do treino de cada dobra (igual a ``DOBRAS`` de ``n4/treinar_ft.py``).
DOBRAS = {
    1: ("retrato_brasileiro_v2", "la_vie_en_rose_edith_piaf_tab"),
    2: (
        "greensleeves_guia_de_estudio_partitura_tab_pdf",
        "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
    ),
    3: (
        "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
        "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
    ),
    4: (
        "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
        "tabroom_335_larry_carlton_fingerstyle_guitar",
    ),
}

#: Slug do ouro -> (subpasta de ``TAB_ROTULO/r2``, fonte do arquivo ``ataque_<fonte>``).
GABARITOS = {
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics": (
        "conferir",
        "end_of_beginning",
    ),
    "tabroom_335_larry_carlton_fingerstyle_guitar": ("conferir", "tabroom_335"),
    "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover": (
        "conferir",
        "pat_metheny",
    ),
    "la_vie_en_rose_edith_piaf_tab": ("conferir", "la_vie_en_rose"),
    "greensleeves_guia_de_estudio_partitura_tab_pdf": (
        "conferir_novos",
        "greensleeves",
    ),
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar": (
        "conferir_novos",
        "gymnopedie",
    ),
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab": (
        "conferir_novos",
        "south_american",
    ),
    "retrato_brasileiro_v2": ("conferir_novos", "retrato"),
}

#: Folga do casamento nota do cache × nota do gabarito, em passos.
FOLGA = 0.5

#: Limiares da técnica medidos além do 0,5 (rodada 0203): o escolhido sai dos ouros.
LIMIARES = tuple(round(0.10 + 0.05 * i, 2) for i in range(9))

#: Limiares baixos da faixa "não sei" (rodada 0205): a nota só é "sim" com todas as
#: técnicas sem ataque abaixo do limiar; entre ele e o limiar da técnica, "não sei".
LIMIARES_NAO_SEI = (0.01, 0.02, 0.03, 0.05, 0.07)

#: Todos os limiares gravados em ``por_limiar``.
LIMIARES_MEDIDOS = LIMIARES_NAO_SEI + LIMIARES

#: Slide sem nota de origem na mesma corda até esta distância à esquerda (passos) é
#: slide de entrada: a nota é atacada (regra do dono; rodada 0203, passo A).
ORIGEM_SLIDE_MAX = 3.0

#: Recortes de ``ler_tela``: "alto" (desde a 0210) e "painel" (até a 0209).
RECORTES = ("alto", "painel")


def tecnica_alvo(nota: dict) -> str | None:
    """Técnica que a nota do gabarito ensina ao modelo (na nota de chegada).

    Args:
        nota: nota do arquivo de ataque, com ``ataque``, ``motivo``, ``casa`` e
            ``casa_vizinha_esq``.

    Returns:
        A técnica do modelo, ou None se a nota é atacada (nenhuma das supervisionadas).
    """
    if nota["ataque"] != "nao":
        return None
    if nota["motivo"] == "slide_ligado":
        try:
            desce = int(nota["casa"]) < int(nota["casa_vizinha_esq"])
        except TypeError, ValueError:
            desce = False
        return "\\" if desce else "/"
    return TECNICA_DO_MOTIVO.get(nota["motivo"])


def gabarito_por_tela(arquivo: Path) -> dict[int, list[dict]]:
    """Notas do gabarito de ataque, só das telas conferidas, agrupadas por tela.

    Args:
        arquivo: ``ataque_<fonte>.json``.

    Returns:
        Mapa tela -> notas.
    """
    doc = json.loads(arquivo.read_text(encoding="utf-8"))
    conferidas = {int(k) for k, v in (doc.get("telas_conferidas") or {}).items() if v}
    saida: dict[int, list[dict]] = {}
    for n in doc["notas"]:
        if int(n["tela"]) in conferidas:
            saida.setdefault(int(n["tela"]), []).append(n)
    return saida


def alvos_da_tela(
    notas_cache: Sequence[dict], x0: float, passo: float, gabarito: Sequence[dict]
) -> list[tuple[bool, str | None]]:
    """Alvo de técnica de cada nota do cache, casada com o gabarito.

    Casa por corda igual e ``|x_roi + x0 − x_centro_quadro| ≤ FOLGA·passo``, guloso pela
    menor distância.

    Args:
        notas_cache: notas da tela no cache (``corda``, ``x_roi``).
        x0: deslocamento do roi no quadro.
        passo: passo da tela.
        gabarito: notas do gabarito da mesma tela (vazio se a tela não foi conferida).

    Returns:
        Por nota do cache, ``(supervisionada, técnica)``. Sem par no gabarito:
        ``(False, None)``.
    """
    quadro = [{**n, "x_centro_quadro": float(n["x_roi"]) + x0} for n in notas_cache]
    pares = parear(quadro, gabarito, passo) if gabarito else {}
    return [
        (True, tecnica_alvo(gabarito[pares[i]])) if i in pares else (False, None)
        for i in range(len(notas_cache))
    ]


def modelo_da_dobra(versao: str, dobra: int, semente: int) -> Path:
    """Caminho dos pesos de uma versão, dobra e semente.

    Args:
        versao: "ger" (o ajuste fino de hoje), "atq" (com o arco real, R4a) ou "atqg"
            (com o arco real e o gerador do R4b).
        dobra: 0 (os 8 ouros no treino) a 4.
        semente: 1, 2 ou 3.

    Returns:
        O ``modelo.pt``.
    """
    if versao != "ger":
        nome = (
            f"detector_tab_final_{versao}_s{semente}"
            if dobra == 0
            else f"detector_tab_v3ft_d{dobra}_{versao}_s{semente}"
        )
    elif dobra == 0:
        nome = f"detector_tab_final_s{semente}_ger"
    else:
        nome = f"detector_tab_v3ft_d{dobra}_ger" + (
            "" if semente == 1 else f"_s{semente}"
        )
    return caminhos.ARTEFATOS / nome / "modelo.pt"


def ler_tela(
    modelo: detector_tab.DetectorTab, video: Path, t_s: float, recorte: str = "alto"
) -> tuple:
    """Lê uma tela: quadro, painel do produto e detector.

    Args:
        modelo: detector carregado.
        video: caminho do vídeo.
        t_s: instante do quadro.
        recorte: "alto" (``painel.recorte_alto``, rodada 0210) ou "painel" (o ``roi`` do
            candidato, como até a 0209).

    Returns:
        ``(notas previstas com x_centro_quadro, passo)`` ou ``([], 0.0)`` sem painel.

    Raises:
        ValueError: recorte desconhecido.
    """
    if recorte not in RECORTES:
        raise ValueError(f"recorte desconhecido: {recorte!r}")
    quadro = leitor.quadro_em(str(video), t_s)
    c = painel.escolher_ou_mascara(quadro) if quadro is not None else None
    if c is None:
        return [], 0.0
    roi, linhas_y = (
        painel.recorte_alto(quadro, c)
        if recorte == "alto"
        else (c.roi, c.grade.linhas_y)
    )
    pred = [
        {
            "corda": int(d["corda"]),
            "casa": str(d["rotulo"]),
            "tecnica": d["tecnica"],
            "x_centro_quadro": float(d["x"]) + c.x0,
            "tecnica_p": d["tecnica_p"],
        }
        for d in detector_tab.detectar(modelo, roi, linhas_y, c.passo, com_escores=True)
    ]
    return pred, float(c.passo)


def com_limiar(pred: Sequence[dict], limiar: float) -> list[dict]:
    """As notas previstas com a técnica refeita por outro limiar (o centro não muda).

    Args:
        pred: notas de ``ler_tela`` (com ``tecnica_p``).
        limiar: limiar das técnicas.

    Returns:
        Cópias das notas, com ``tecnica`` = técnicas de probabilidade acima do limiar.
    """
    return [
        {
            **p,
            "tecnica": [
                t
                for t, v in zip(
                    detector_tab.TECNICAS_MODELO, p["tecnica_p"], strict=True
                )
                if v > limiar
            ],
        }
        for p in pred
    ]


def ataque_com_regra(pred: Sequence[dict], j: int, passo: float) -> str:
    """Ataque da nota ``j`` com a regra do slide sem origem.

    Um slide (``/`` ou ``\\``) sem outra técnica sem ataque e sem nota na mesma corda até
    ``ORIGEM_SLIDE_MAX`` passos à esquerda é slide de entrada: atacada.

    Args:
        pred: notas previstas da tela (``corda``, ``x_centro_quadro``, ``tecnica``).
        j: índice da nota.
        passo: passo da tela.

    Returns:
        "sim" ou "nao".
    """
    p = pred[j]
    base = ataque_previsto(p["tecnica"])
    if base == "sim" or not set(p["tecnica"]) <= {"/", "\\"}:
        return base
    origem = any(
        q["corda"] == p["corda"]
        and 0 < p["x_centro_quadro"] - q["x_centro_quadro"] <= ORIGEM_SLIDE_MAX * passo
        for q in pred
    )
    return base if origem else "sim"


def contar(gabarito: Sequence[dict], pred: Sequence[dict], passo: float) -> Counter:
    """Matriz do ataque e acerto da casa de uma tela.

    Args:
        gabarito: notas do arquivo de ataque da tela.
        pred: notas previstas.
        passo: passo da tela.

    Returns:
        Contagem ``"<ouro>|<previsto>"``, a mesma com a regra do slide sem origem
        (``"regra:<ouro>|<previsto>"``), ``casa_certa`` e ``casadas``.
    """
    pares = parear(gabarito, pred, passo)
    c: Counter = Counter()
    for i, n in enumerate(gabarito):
        if i not in pares:
            c[f"{n['ataque']}|nao_lida"] += 1
            c[f"regra:{n['ataque']}|nao_lida"] += 1
            continue
        p = pred[pares[i]]
        c[f"{n['ataque']}|{ataque_previsto(p['tecnica'])}"] += 1
        c[f"regra:{n['ataque']}|{ataque_com_regra(pred, pares[i], passo)}"] += 1
        c["casadas"] += 1
        c["casa_certa"] += int(str(n["casa"]) == p["casa"])
    return c


def regra(matriz: Counter) -> Counter:
    """A parte ``"regra:"`` de uma matriz de ``contar``, sem o prefixo.

    Args:
        matriz: saída de ``contar`` (ou soma delas).

    Returns:
        Matriz ``"<ouro>|<previsto>"`` com a regra do slide sem origem.
    """
    return Counter(
        {
            k.removeprefix("regra:"): v
            for k, v in matriz.items()
            if k.startswith("regra:")
        }
    )


def medir(versao: str, semente: int, recorte: str = "alto") -> dict:
    """Mede uma versão e semente nos 8 ouros (dobra fora) e na T8.2 (dobra 0).

    Args:
        versao: "ger", "atq", "atqg", "atqc", "atqt", "atqe" ou "atqa".
        semente: 1, 2 ou 3.
        recorte: o de ``ler_tela``.

    Returns:
        Dict fonte -> matriz e taxas (no limiar 0,5 e em ``por_limiar``), mais ``ouros``
        (soma dos 8) e ``t82``.
    """
    r2 = caminhos.TAB_ROTULO / "r2"
    dobra_de = {slug: d for d, slugs in DOBRAS.items() for slug in slugs}
    saida: dict = {}
    soma: Counter = Counter()
    soma_l: dict[float, Counter] = {lim: Counter() for lim in LIMIARES_MEDIDOS}
    for slug, (sub, fonte) in GABARITOS.items():
        modelo = detector_tab.carregar(modelo_da_dobra(versao, dobra_de[slug], semente))
        ouro = json.loads((r2 / sub / f"{slug}.json").read_text(encoding="utf-8"))
        video = caminhos.acervo() / ouro["video"]
        quadro = {int(t["id"]): float(t["quadro_ref_s"]) for t in ouro["telas"]}
        c: Counter = Counter()
        por_l: dict[float, Counter] = {lim: Counter() for lim in LIMIARES_MEDIDOS}
        for tela, notas in sorted(
            gabarito_por_tela(r2 / sub / f"ataque_{fonte}.json").items()
        ):
            pred, passo = ler_tela(modelo, video, quadro[tela], recorte)
            c += contar(notas, pred, passo)
            for lim in LIMIARES_MEDIDOS:
                por_l[lim] += contar(notas, com_limiar(pred, lim), passo)
        saida[fonte] = {
            "matriz": dict(c),
            "taxas": taxas(c),
            "regra": taxas(regra(c)),
            "por_limiar": {str(lim): dict(m) for lim, m in por_l.items()},
        }
        soma += c
        for lim in LIMIARES_MEDIDOS:
            soma_l[lim] += por_l[lim]
        print(versao, semente, fonte, dict(c), flush=True)
    saida["ouros"] = {
        "matriz": dict(soma),
        "taxas": taxas(soma),
        "regra": taxas(regra(soma)),
        "por_limiar": {str(lim): dict(m) for lim, m in soma_l.items()},
    }
    ferr = caminhos.SAIDA / "t82" / "ferramenta"
    indice = {
        int(r["id"]): r
        for r in json.loads((ferr / "indice.json").read_text(encoding="utf-8"))
    }
    modelo = detector_tab.carregar(modelo_da_dobra(versao, 0, semente))
    c = Counter()
    por_l = {lim: Counter() for lim in LIMIARES_MEDIDOS}
    gab = gabarito_por_tela(r2 / "conferir_novos" / "ataque_t82.json")
    for tela, notas in sorted(gab.items()):
        r = indice[tela]
        pred, passo = ler_tela(
            modelo, caminhos.acervo() / r["video"], float(r["t"]), recorte
        )
        c += contar(notas, pred, passo)
        for lim in LIMIARES_MEDIDOS:
            por_l[lim] += contar(notas, com_limiar(pred, lim), passo)
    saida["t82"] = {
        "matriz": dict(c),
        "taxas": taxas(c),
        "regra": taxas(regra(c)),
        "por_limiar": {str(lim): dict(m) for lim, m in por_l.items()},
    }
    print(versao, semente, "t82", dict(c), flush=True)
    return saida


def escolher_limiar(medidas: Sequence[dict], teto: float = 0.01) -> float:
    """O menor limiar com "não" em atacada até ``teto`` nos ouros (rodada 0203).

    As sementes entram somadas. Usa a regra do slide sem origem.

    Args:
        medidas: saídas de ``medir`` de uma versão (uma por semente).
        teto: fração máxima de notas atacadas lidas como "não".

    Returns:
        O limiar escolhido; 0,5 se nenhum menor serve.
    """
    for lim in LIMIARES:
        soma: Counter = Counter()
        for m in medidas:
            soma.update(m["ouros"]["por_limiar"][str(lim)])
        n, d = taxas(regra(soma))["nao_falso"]
        if d and n / d <= teto:
            return lim
    return 0.5


def escolher_nao_sei(medidas: Sequence[dict], teto: float = 0.05) -> float:
    """O menor limiar do "sim" com "não" ou "não sei" em atacada até ``teto`` (0205).

    Nota atacada lida acima do limiar baixo é "não" ou "não sei": as duas custam
    cobertura. Escolhido só nos ouros, com as sementes somadas e a regra do slide.

    Args:
        medidas: saídas de ``medir`` de uma versão (uma por semente).
        teto: fração máxima de notas atacadas sem "sim".

    Returns:
        O limiar escolhido; 0,5 se nenhum menor serve.
    """
    for lim in sorted(LIMIARES_MEDIDOS):
        soma: Counter = Counter()
        for m in medidas:
            soma.update(m["ouros"]["por_limiar"][str(lim)])
        n, d = taxas(regra(soma))["nao_falso"]
        if d and n / d <= teto:
            return lim
    return 0.5


def main() -> int:
    """Grava ``TAB_ROTULO/r4a/medida_<versao>_s<semente>.json``.

    Returns:
        0.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    m = sub.add_parser("medir", help="mede uma versão e semente")
    m.add_argument(
        "--versao",
        choices=("ger", "atq", "atqg", "atqc", "atqt", "atqe", "atqa"),
        required=True,
    )
    m.add_argument("--semente", type=int, required=True)
    m.add_argument(
        "--recorte",
        choices=RECORTES,
        default="alto",
        help='"painel" refaz as medidas até a 0209 (arquivo sem o sufixo "_alto")',
    )
    args = ap.parse_args()
    resultado = medir(args.versao, args.semente, args.recorte)
    pasta = caminhos.TAB_ROTULO / "r4a"
    pasta.mkdir(parents=True, exist_ok=True)
    sufixo = "_alto" if args.recorte == "alto" else ""
    (pasta / f"medida_{args.versao}_s{args.semente}{sufixo}.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
