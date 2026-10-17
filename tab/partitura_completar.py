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

Uso (na raiz do projeto)::

    python -m tab.partitura_completar
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from .caminhos import PART_FRENTE_E, SAIDA
from .musicxml import midi_da_corda
from .partitura_gabarito import ler_partitura
from .partitura_pareamento import INDICE, _carregar_ouro, _parear_recorte
from .partitura_regua import _seminimas
from .partitura_video import _compassos_do_recorte, eventos_do_produto

STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
]
PASTA_PRODUTO = SAIDA / "fase8" / "rede"
PASTA_PARTITURA = SAIDA / "partitura" / "video"
SAIDA_JSON = PART_FRENTE_E / "e1.json"

#: Valor em semínimas de cada figura do MusicXML.
FIGURAS = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "16th": 0.25,
    "32nd": 0.125,
}
#: Déficit que cabe numa figura só: (semínimas, nome, pontuada).
FIGURA_UNICA = [
    (4.0, "whole", False),
    (3.0, "half", True),
    (2.0, "half", False),
    (1.5, "quarter", True),
    (1.0, "quarter", False),
    (0.75, "eighth", True),
    (0.5, "eighth", False),
    (0.25, "16th", False),
    (0.125, "32nd", False),
]
TOLERANCIA_PX = 5.0
TOLERANCIA_DURACAO = 1e-6
CORDAS_VOZ_2 = {4, 5, 6}


def _duracao(simbolo: dict) -> float:
    """Duração de um símbolo em semínimas (pontuada ×1,5).

    Args:
        simbolo: símbolo normalizado (com ``figura`` e ``pontuada``).

    Returns:
        Duração em semínimas, ou 0.0 se a figura é desconhecida.
    """
    base = FIGURAS.get(simbolo.get("figura"), 0.0)
    return base * 1.5 if simbolo.get("pontuada") else base


def _normalizar(simbolos: list[dict]) -> list[dict]:
    """Símbolos com as chaves ``midi``, ``figura``, ``pontuada`` e ``voz``.

    Aceita o formato do ``.partitura.json`` (``midi_escrito``) e o de ``ler_partitura``
    (``midi``).

    Args:
        simbolos: símbolos em um dos dois formatos.

    Returns:
        Lista com as mesmas notas nas chaves padrão.
    """
    saida = []
    for s in simbolos:
        midi = s.get("midi_escrito", s.get("midi"))
        saida.append(
            {
                "midi": midi,
                "figura": s.get("figura"),
                "pontuada": bool(s.get("pontuada")),
                "voz": str(s.get("voz", "1")),
            }
        )
    return saida


def _e_harmonico(midi: int, x: float | None, eventos: list[dict]) -> bool:
    """Diz se a nota da tab é um harmônico: a pauta tem a mesma nota uma oitava acima.

    Regra da rodada 3013: a tab escreve o som e a pauta escreve a nota presa. Sem a nota
    uma oitava acima no mesmo x, não é harmônico.

    Args:
        midi: altura escrita da nota da tab que falta na pauta.
        x: posição x da coluna da tab.
        eventos: eventos normalizados da partitura do recorte ou da tela.

    Returns:
        True se algum evento da partitura no mesmo x tem ``midi + 12``.
    """
    if x is None:
        return False
    for evento in eventos:
        if (
            evento["x"] is not None
            and abs(evento["x"] - x) <= TOLERANCIA_PX
            and (midi + 12) in evento["midis"]
        ):
            return True
    return False


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


def _compasso_de_x(x: float | None, compassos: list[dict]) -> str | None:
    """Número do compasso que contém o x, pelo último compasso que começa antes dele.

    Args:
        x: posição x no quadro da nota da tab.
        compassos: lista ``{"numero", "fracao", "x_quadro"}``, na ordem.

    Returns:
        O ``numero`` do compasso, ou None se não há compasso com x até ``x``.
    """
    if x is None:
        return None
    escolhido = None
    for compasso in compassos:
        cx = compasso.get("x_quadro")
        if cx is not None and cx <= x + TOLERANCIA_PX:
            escolhido = compasso["numero"]
    return escolhido


def _figura_do_deficit(deficit: float) -> tuple[str | None, bool]:
    """Figura de um déficit de compasso, se ele cabe numa figura só.

    Args:
        deficit: esperada menos a maior soma por voz, em semínimas.

    Returns:
        ``(figura, pontuada)``, ou ``(None, False)`` se o déficit não é uma figura só.
    """
    for valor, nome, pontuada in FIGURA_UNICA:
        if abs(deficit - valor) < TOLERANCIA_DURACAO:
            return nome, pontuada
    return None, False


def _soma_do_compasso(eventos: list[dict], numero: str) -> float:
    """Maior soma por voz das durações dos eventos de um compasso (acorde conta uma vez).

    Args:
        eventos: eventos normalizados, com ``compasso`` e ``simbolos``.
        numero: número do compasso.

    Returns:
        A maior soma por voz, em semínimas.
    """
    somas: dict[str, float] = defaultdict(float)
    for evento in eventos:
        if evento["compasso"] != numero or not evento["simbolos"]:
            continue
        primeiro = evento["simbolos"][0]
        somas[primeiro["voz"]] += _duracao(primeiro)
    return max(somas.values(), default=0.0)


def _completar(
    notas_tab: list[dict],
    eventos: list[dict],
    pares: dict[int, int],
    compassos: list[dict],
    identificacao: dict,
) -> list[dict]:
    """Monta as notas completadas de um recorte ou tela.

    Args:
        notas_tab: eventos da tab; cada um tem ``x``, ``midis`` (escritas) e ``cordas``
            (corda de cada altura).
        eventos: eventos da partitura normalizados, com ``compasso``, ``x``, ``midis`` e
            ``simbolos``.
        pares: ``{indice do evento da tab: indice do evento da partitura}``, só com par
            conferido.
        compassos: ``{"numero", "fracao", "x_quadro"}`` do recorte ou da tela.
        identificacao: campos que vão para cada nota (``video``, ``tela``, ``recorte``).

    Returns:
        Uma entrada por nota completada, com ``origem`` ``tab_completada``, ``tipo``
        (``acorde`` ou ``isolado``), ``figura`` (ou None) e ``pontuada``.
    """
    completadas = []
    for j, tab in enumerate(notas_tab):
        i = pares.get(j)
        if i is not None:
            evento = eventos[i]
            faltam = sorted(m for m in tab["midis"] if m not in evento["midis"])
            if not faltam:
                continue
            primeiro = evento["simbolos"][0] if evento["simbolos"] else None
            compasso = evento["compasso"]
            tem_voz2 = any(
                s["voz"] == "2"
                for e in eventos
                if e["compasso"] == compasso
                for s in e["simbolos"]
            )
            for midi in faltam:
                cordas = tab["cordas"].get(midi, 0)
                voz = (
                    "2"
                    if cordas in CORDAS_VOZ_2 and tem_voz2
                    else (primeiro["voz"] if primeiro else "1")
                )
                completadas.append(
                    {
                        **identificacao,
                        "origem": "tab_completada",
                        "tipo": "acorde",
                        "compasso": compasso,
                        "midi": midi,
                        "figura": primeiro["figura"] if primeiro else None,
                        "pontuada": primeiro["pontuada"] if primeiro else False,
                        "voz": voz,
                        "x": tab["x"],
                        "harmonico": _e_harmonico(midi, tab["x"], eventos),
                    }
                )
        else:
            compasso = _compasso_de_x(tab["x"], compassos)
            esperada = _seminimas_compasso(compassos, compasso)
            soma = _soma_do_compasso(eventos, compasso) if compasso is not None else 0.0
            deficit = (esperada - soma) if esperada is not None else None
            figura, pontuada = (
                _figura_do_deficit(deficit)
                if deficit is not None and deficit > 0
                else (None, False)
            )
            for midi in sorted(tab["midis"]):
                completadas.append(
                    {
                        **identificacao,
                        "origem": "tab_completada",
                        "tipo": "isolado",
                        "compasso": compasso,
                        "midi": midi,
                        "figura": figura,
                        "pontuada": pontuada,
                        "voz": "1",
                        "x": tab["x"],
                        "harmonico": _e_harmonico(midi, tab["x"], eventos),
                        "deficit": deficit,
                    }
                )
    return completadas


def _seminimas_compasso(compassos: list[dict], numero: str | None) -> float | None:
    """Duração esperada de um compasso, em semínimas, pela fração.

    Args:
        compassos: ``{"numero", "fracao", "x_quadro"}`` do recorte ou da tela.
        numero: número do compasso.

    Returns:
        Semínimas do compasso, ou None se não há fração ou compasso.
    """
    for compasso in compassos:
        if compasso["numero"] == numero:
            return _seminimas(compasso.get("fracao"))
    return None


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
                    {"x": evento.x_quadro, "midis": set(evento.midis), "cordas": cordas}
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
                {"x": e["x_quadro"], "midis": set(e["midis"]), "cordas": cordas}
            )
        pares = {
            p["par_tab"]: p["indice"]
            for p in doc["pares"]
            if p["par_tab"] is not None and p["confere_x"] is True
        }
        leitura = ler_partitura(
            SAIDA
            / "partitura"
            / "p1"
            / "omr"
            / "audiveris"
            / "x2_margem_herdada"
            / rid
            / "saida.musicxml"
        )
        compassos = _compassos_do_recorte(
            leitura,
            SAIDA
            / "partitura"
            / "p1"
            / "omr"
            / "audiveris"
            / "x2_margem"
            / rid
            / "entrada.omr",
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
    """Roda a E1 e grava ``e1.json`` na pasta da frente E.

    Args:
        argv: argumentos da linha de comando (não há opções).

    Returns:
        Zero em caso de sucesso.
    """
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    documento = medir()
    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_JSON.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2, default=list),
        encoding="utf-8",
    )
    for nome, c in documento["contagens"].items():
        print(f"{nome}: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
