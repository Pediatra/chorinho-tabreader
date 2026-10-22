"""E1 da partitura: completar pela tab o que a pauta não leu (rodada 3170).

Para cada evento da tab sem nota da partitura com aquela altura, a nota entra:

- **acorde**: há evento da partitura pareado no mesmo x (par conferido). A nota entra nele,
  com a figura e a voz do evento (voz 2 para as cordas 4 a 6, quando o compasso já tem duas
  vozes);
- **ataque isolado**: não há evento pareado. A figura vem do déficit do compasso (duração
  esperada menos a maior soma por voz), se o déficit cabe numa figura só. Senão a figura fica
  ``None``;
- nunca se descarta nota.

Conjuntos: as 19 telas dos 3 produtos (tab do produto) e R01–R12 (tab do gabarito, com o
pareamento em memória de ``_parear_recorte``, como o bloco A do CA1).

Só lê o que está gravado. Não reescreve nenhum ``.partitura.json``: grava ``e1.json`` na
pasta da frente E, com só as notas completadas (``origem`` ``tab_completada``).

A função de completar mora em ``tab/partitura_completar_pauta.py`` (pura, sem import de
``partitura_video``). Este módulo só monta os conjuntos e grava o ``e1.json``.

Uso (na raiz do projeto)::

    python -m tab.partitura_completar [--saida CAMINHO]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from tab.comum.caminhos import FASE8_REDE, PART_FRENTE_E, PARTITURA_P1, PARTITURA_VIDEO
from tab.partitura.completar_pauta import (
    TECNICA_HARMONICO,
    TOLERANCIA_PX,
    _completar,
    _normalizar,
)
from tab.partitura.gabarito import ler_partitura
from tab.partitura.pareamento import INDICE, _carregar_ouro, _parear_recorte
from tab.partitura.video import _compassos_do_recorte, eventos_do_produto
from tab.tablatura.produto.musicxml import midi_da_corda

STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]
PASTA_PRODUTO = FASE8_REDE
PASTA_PARTITURA = PARTITURA_VIDEO
SAIDA_JSON = PART_FRENTE_E / "e1.json"


def _herda_erro(midi: int, x: float, notas_gabarito: list[dict]) -> bool:
    """Diz se a altura completada não existe no gabarito de tab no mesmo x.

    Args:
        midi: altura escrita da nota completada.
        x: posição x da coluna da tab do produto.
        notas_gabarito: notas da tela no gabarito de tab (``x_centro_quadro``, ``corda``,
            ``casa``).

    Returns:
        True se nenhuma nota do gabarito a até ``TOLERANCIA_PX`` tem essa altura escrita.
    """
    for nota in notas_gabarito:
        if abs(float(nota["x_centro_quadro"]) - x) <= TOLERANCIA_PX:
            som = midi_da_corda(int(nota["corda"]), int(nota["casa"]))
            if som is not None and som + 12 == midi:
                return False
    return True


def _grupo_produtos() -> list[dict]:
    """Notas completadas das 19 telas dos 3 produtos, contra a tab do produto.

    Returns:
        Lista de notas completadas (ver ``_completar``).
    """
    resultado = []
    for stem in STEMS:
        produto = json.loads(
            (PASTA_PRODUTO / f"{stem}.json").read_text(encoding="utf-8")
        )
        doc = json.loads(
            (PASTA_PARTITURA / stem / f"{stem}.partitura.json").read_text(
                encoding="utf-8"
            )
        )
        for pauta in doc["pautas"]:
            tela = pauta["tela"]
            x0, _, x1, _ = pauta["caixa_quadro"]
            eventos = []
            pares: dict[int, int] = {}
            colunas_pareadas: dict[int, int] = {}
            for k, ev in enumerate(pauta["eventos"]):
                par = ev.get("par") or {}
                eventos.append(
                    {
                        "compasso": ev["compasso"],
                        "x": ev["x_quadro"],
                        "simbolos": _normalizar(ev["simbolos"]),
                        "midis": {s["midi"] for s in _normalizar(ev["simbolos"])},
                    }
                )
                if par.get("tela") == tela and par.get("confere_x") is True:
                    colunas_pareadas.setdefault(par["coluna"], k)
            tab = eventos_do_produto(produto["notas"], tela, x0, x1)
            notas_tab = []
            for j, evento in enumerate(tab):
                cordas: dict[int, int] = {}
                for nota in evento.notas:
                    som = midi_da_corda(int(nota["corda"]), int(nota["casa"]))
                    if som is not None:
                        cordas.setdefault(som + 12, int(nota["corda"]))
                coluna = evento.notas[0]["coluna"]
                notas_tab.append(
                    {
                        "x": evento.x_quadro,
                        "midis": set(evento.midis),
                        "cordas": cordas,
                        "harmonico_tab": any(
                            n.get("tecnica") == TECNICA_HARMONICO for n in evento.notas
                        ),
                    }
                )
                if coluna in colunas_pareadas:
                    pares[j] = colunas_pareadas[coluna]
            compassos = [
                {
                    "numero": c["numero"],
                    "fracao": c.get("fracao"),
                    "x_quadro": c["x_quadro"],
                }
                for c in pauta["compassos"]
            ]
            resultado.extend(
                _completar(
                    notas_tab,
                    eventos,
                    pares,
                    compassos,
                    {"video": stem, "tela": tela, "recorte": pauta["recorte"]},
                )
            )
    return resultado


def _grupo_r01_r12() -> list[dict]:
    """Notas completadas de R01–R12, contra a tab do gabarito (pareamento em memória).

    Returns:
        Lista de notas completadas (ver ``_completar``).
    """
    ouro = _carregar_ouro()
    indice = json.loads(INDICE.read_text(encoding="utf-8"))
    resultado = []
    for entrada in [e for e in indice if e["origem"] == "ouro"]:
        doc = _parear_recorte(entrada, ouro)
        rid = entrada["id"]
        x0 = entrada["caixa_recorte"][0]
        eventos = [
            {
                "compasso": str(e["compasso"]),
                "x": e["x_quadro"],
                "simbolos": _normalizar(e["simbolos"]),
                "midis": set(e["midis"]),
            }
            for e in doc["partitura"]
        ]
        notas_tab = []
        for e in doc["tab"]:
            cordas: dict[int, int] = {}
            for nota in e["notas"]:
                som = midi_da_corda(int(nota["corda"]), int(nota["casa"]))
                if som is not None:
                    cordas.setdefault(som + 12, int(nota["corda"]))
            notas_tab.append(
                {
                    "x": e["x_quadro"],
                    "midis": set(e["midis"]),
                    "cordas": cordas,
                    "harmonico_tab": any(n.get("harmonico") for n in e["notas"]),
                }
            )
        pares = {
            p["par_tab"]: p["indice"]
            for p in doc["pares"]
            if p["par_tab"] is not None and p["confere_x"] is True
        }
        leitura = ler_partitura(
            PARTITURA_P1
            / "omr"
            / "audiveris"
            / "x2_margem_herdada"
            / rid
            / "saida.musicxml"
        )
        compassos = _compassos_do_recorte(
            leitura,
            PARTITURA_P1 / "omr" / "audiveris" / "x2_margem" / rid / "entrada.omr",
            x0,
        )
        resultado.extend(
            _completar(
                notas_tab,
                eventos,
                pares,
                [
                    {
                        "numero": c["numero"],
                        "fracao": c["fracao"],
                        "x_quadro": c["x_quadro"],
                    }
                    for c in compassos
                ],
                {"video": entrada["video"], "tela": entrada["tela"], "recorte": rid},
            )
        )
    return resultado


def _marcar(completadas: list[dict]) -> None:
    """Marca, em cada nota completada, tela 10 da Gymnopédie e herança de erro da tab.

    ``herda_erro_tab`` é a comparação com o gabarito de tab no mesmo x (tolerância de
    ``TOLERANCIA_PX``), só para as notas dos produtos. Nas R01–R12 a altura vem do próprio
    gabarito, então o campo fica ``None`` (circular, rodada 3170).

    Args:
        completadas: notas completadas, alteradas no lugar.
    """
    ouro = _carregar_ouro()
    gym = STEMS[2]
    for nota in completadas:
        nota["tela_10_gym"] = nota["video"] == gym and nota["tela"] == 10
        if nota["video"] in STEMS:
            produto = json.loads(
                (PASTA_PRODUTO / f"{nota['video']}.json").read_text(encoding="utf-8")
            )
            gabarito = ouro[produto["video"]["arquivo"]][0]
            tela = next(t for t in gabarito["telas"] if t["id"] == nota["tela"])
            nota["herda_erro_tab"] = _herda_erro(nota["midi"], nota["x"], tela["notas"])
        else:
            nota["herda_erro_tab"] = None


def medir() -> dict:
    """Roda a E1 nos dois conjuntos e devolve o documento de saída.

    Harmônico e tela 10 da Gymnopédie saem da conta e são contados à parte. Nota ligada não
    é detectável neste produto (``tecnica`` é ``None``), então fica declarada, com 0.

    Returns:
        Documento com ``completadas`` (as contadas), ``a_parte`` (harmônico, tela 10),
        ``contagens`` por conjunto e tipo, e ``herdam_erro_tab`` (produtos).
    """
    produtos = _grupo_produtos()
    r = _grupo_r01_r12()
    todas = produtos + r
    _marcar(todas)
    contadas = [n for n in todas if not n["harmonico"] and not n["tela_10_gym"]]
    a_parte = {
        "harmonico": sum(1 for n in todas if n["harmonico"]),
        "tela_10_gym": sum(1 for n in todas if n["tela_10_gym"] and not n["harmonico"]),
        "harmonico_nao_detectado_candidatos_oitava": sum(
            1 for n in contadas if n["candidato_oitava"]
        ),
        "nota_ligada": "não detectável: tecnica é None no produto",
    }
    contagens: dict[str, dict] = {}
    for nome, grupo in (
        ("produtos_19_telas", [n for n in contadas if n["video"] in STEMS]),
        ("R01_R12", [n for n in contadas if n["video"] not in STEMS]),
    ):
        c: dict = defaultdict(int)
        for n in grupo:
            c[n["tipo"]] += 1
            c["figura_nula" if n["figura"] is None else "com_figura"] += 1
        contagens[nome] = dict(c)
    herdam = sum(1 for n in contadas if n["herda_erro_tab"] is True)
    return {
        "frente": "E1",
        "rodada": 3170,
        "completadas": contadas,
        "a_parte": a_parte,
        "contagens": contagens,
        "herdam_erro_tab": herdam,
        "tolerancia_px": TOLERANCIA_PX,
    }


def main(argv: list[str] | None = None) -> int:
    """Roda a E1 e grava ``e1.json`` na pasta da frente E (ou no ``--saida``).

    Args:
        argv: argumentos da linha de comando (``--saida``, opcional).

    Returns:
        Zero em caso de sucesso.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--saida",
        type=Path,
        default=SAIDA_JSON,
        help="arquivo e1.json de saída (padrão: a pasta da frente E)",
    )
    args = parser.parse_args(argv)
    documento = medir()
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2, default=list),
        encoding="utf-8",
    )
    for nome, c in documento["contagens"].items():
        print(f"{nome}: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
