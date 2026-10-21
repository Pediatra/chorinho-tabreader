"""Mede o transcritor livre contra os gabaritos de tablatura (rodada 2018).

O transcritor (``tab.audio_transcrever``) só ouve o áudio. Aqui as notas ouvidas são
comparadas com as notas que o dono conferiu na tela, pela física: **MIDI = corda solta +
casa + capo** (afinação padrão). O método está fixado no pré-registro
``docs/rodadas/2018-transcritor-livre-basic-pitch.md``:

1. as notas do gabarito viram colunas (mesma coluna se o x dista ≤ 0,5 passo), em ordem;
2. as notas ouvidas na janela da exibição viram eventos (inícios encadeados a ≤ 60 ms);
3. um pareamento monotônico (programação dinâmica) liga colunas a eventos, maximizando as
   alturas iguais;
4. por tela, vale a exibição com mais alturas pareadas.

Uso (container base)::

    python -m tab.audio_som_medir --lista data/saida/audio/r2018/lista.json \
        --som data/saida/audio/r2018/som --saida data/saida/audio/r2018/medida.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

from .caminhos import (
    CAPO_POR_VIDEO,
    GABARITO_AUDIO,
    OURO_VIDEO,
    PRE_OURO_VIDEO,
    SAIDA_AUDIO,
)

#: Altura MIDI de cada corda solta, afinação padrão (E4 B3 G3 D3 A2 E2).
ALTURA_SOLTA = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}

#: Inícios a até esta distância (s), em cadeia, formam um evento (acorde rasgueado).
JUNTAR_S = 0.06

#: Folga da janela da exibição, para cada lado (s).
FOLGA_S = 0.25

#: Ponto de escuta acertado se há início de nota a até esta distância (s).
INSTANTE_S = 0.10

#: Corte de confiança do transcritor (amplitude do Basic Pitch), escolhido só no vídeo de
#: desenvolvimento pela regra da emenda 1 da rodada 2018: o menor corte com precisão
#: ≥ 0,70 e revocação ≥ 0,90 (deu 0,50: 0,904 e 0,765). ``0`` é o transcritor cru.
AMPLITUDE_MINIMA = 0.50

#: Coluna de acorde cheio: pelo menos estas cordas.
CORDAS_ACORDE_CHEIO = 5

#: Casa do capo por vídeo (dado das mãos; nome antigo mantido para quem importa).
CAPO = CAPO_POR_VIDEO


def midi_da_nota(corda: int, casa: int, capo: int = 0) -> int:
    """Altura MIDI de uma nota da tablatura.

    Args:
        corda: 1 (mais aguda) a 6.
        casa: casa escrita na tela (contada a partir do capo).
        capo: casa do capo (0 sem capo).

    Returns:
        ``ALTURA_SOLTA[corda] + casa + capo``.
    """
    return ALTURA_SOLTA[corda] + casa + capo


def casa_inteira(casa: object) -> int | None:
    """A casa como inteiro, ou ``None`` se não for número (X, vazio...).

    Args:
        casa: valor gravado no gabarito (``int`` ou texto).

    Returns:
        O inteiro, ou ``None``.
    """
    if isinstance(casa, bool):
        return None
    if isinstance(casa, int):
        return casa
    texto = str(casa).strip()
    return int(texto) if texto.isdigit() else None


def colunas_do_gabarito(notas: list[dict], passo: float, capo: int) -> list[list[dict]]:
    """Agrupa as notas de uma tela em colunas, em ordem de x.

    Args:
        notas: notas com ``corda``, ``casa`` e ``x_centro_quadro`` (as removidas e as sem
            casa numérica ficam de fora).
        passo: distância entre cordas, em px; mesma coluna se o x dista ≤ 0,5 passo do
            anterior.
        capo: casa do capo.

    Returns:
        Lista de colunas; cada nota é ``{corda, casa, midi, x}``.
    """
    validas = []
    for n in notas:
        casa = casa_inteira(n.get("casa"))
        if n.get("removida") or casa is None or n.get("corda") not in ALTURA_SOLTA:
            continue
        validas.append(
            {
                "corda": int(n["corda"]),
                "casa": casa,
                "midi": midi_da_nota(int(n["corda"]), casa, capo),
                "x": float(n["x_centro_quadro"]),
            }
        )
    validas.sort(key=lambda n: (n["x"], n["corda"]))
    colunas: list[list[dict]] = []
    for n in validas:
        if colunas and n["x"] - colunas[-1][-1]["x"] <= 0.5 * passo:
            colunas[-1].append(n)
        else:
            colunas.append([n])
    return colunas


def eventos_do_som(
    notas: list[dict], t0: float, t1: float, juntar: float = JUNTAR_S
) -> list[list[dict]]:
    """As notas ouvidas numa janela, agrupadas em eventos por cadeia de inícios.

    Args:
        notas: notas do transcritor (``t_ini``, ``midi``), em ordem de início.
        t0: início da janela (s), já com a folga.
        t1: fim da janela (s), já com a folga.
        juntar: distância máxima entre inícios seguidos do mesmo evento (s).

    Returns:
        Lista de eventos, cada um uma lista de notas.
    """
    dentro = sorted(
        (n for n in notas if t0 <= n["t_ini"] <= t1), key=lambda n: n["t_ini"]
    )
    eventos: list[list[dict]] = []
    for n in dentro:
        if eventos and n["t_ini"] - eventos[-1][-1]["t_ini"] <= juntar:
            eventos[-1].append(n)
        else:
            eventos.append([n])
    return eventos


def iguais(coluna: list[dict], evento: list[dict], desvio: int = 0) -> int:
    """Quantas alturas da coluna (somadas ``desvio``) estão no evento, como multiconjunto.

    Args:
        coluna: notas do gabarito.
        evento: notas ouvidas.
        desvio: semitons somados ao gabarito (0; +1 no controle negativo).

    Returns:
        O tamanho da interseção dos multiconjuntos de alturas.
    """
    a = Counter(n["midi"] + desvio for n in coluna)
    b = Counter(n["midi"] for n in evento)
    return sum((a & b).values())


def parear(
    colunas: list[list[dict]], eventos: list[list[dict]], desvio: int = 0
) -> list[tuple[int, int, int]]:
    """Pareamento monotônico que maximiza as alturas iguais (programação dinâmica).

    Args:
        colunas: colunas do gabarito, em ordem.
        eventos: eventos do som, em ordem.
        desvio: semitons somados ao gabarito.

    Returns:
        Pares ``(i_coluna, j_evento, alturas_iguais)`` com ``alturas_iguais > 0``, em
        ordem. Empate: a primeira solução encontrada pela ordem de varredura.
    """
    n, m = len(colunas), len(eventos)
    melhor = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            par = melhor[i - 1][j - 1] + iguais(colunas[i - 1], eventos[j - 1], desvio)
            melhor[i][j] = max(melhor[i - 1][j], melhor[i][j - 1], par)
    pares = []
    i, j = n, m
    while i > 0 and j > 0:
        g = iguais(colunas[i - 1], eventos[j - 1], desvio)
        if g > 0 and melhor[i][j] == melhor[i - 1][j - 1] + g:
            pares.append((i - 1, j - 1, g))
            i, j = i - 1, j - 1
        elif melhor[i][j] == melhor[i - 1][j]:
            i -= 1
        else:
            j -= 1
    pares.reverse()
    return pares


def medir_exibicao(
    colunas: list[list[dict]],
    som: list[dict],
    t0: float,
    t1: float,
    desvio: int = 0,
) -> dict:
    """Mede uma exibição: revocação, precisão no trecho pareado e acordes cheios.

    Args:
        colunas: colunas do gabarito da tela.
        som: todas as notas do transcritor no vídeo.
        t0: início da exibição (s).
        t1: fim da exibição (s).
        desvio: semitons somados ao gabarito (controle negativo).

    Returns:
        ``{n_gabarito, n_pareadas, n_som_trecho, n_som_pareadas, acordes, oitava,
        semitom, t0, t1}``. ``acordes`` traz a fração achada de cada coluna de 5-6 cordas.
    """
    eventos = eventos_do_som(som, t0 - FOLGA_S, t1 + FOLGA_S)
    pares = parear(colunas, eventos, desvio)
    n_gab = sum(len(c) for c in colunas)
    n_par = sum(g for _, _, g in pares)
    if pares:
        j0, j1 = pares[0][1], pares[-1][1]
        n_som = sum(len(eventos[j]) for j in range(j0, j1 + 1))
    else:
        n_som = 0
    por_coluna = {i: (j, g) for i, j, g in pares}
    acordes, oitava, semitom = [], 0, 0
    for i, coluna in enumerate(colunas):
        j, g = por_coluna.get(i, (None, 0))
        if len({n["corda"] for n in coluna}) >= CORDAS_ACORDE_CHEIO:
            acordes.append(round(g / len(coluna), 4))
        if j is None or g == len(coluna):
            continue
        ouvidas = Counter(n["midi"] for n in eventos[j])
        sobra = Counter(n["midi"] + desvio for n in coluna) - ouvidas
        for alt, k in sobra.items():
            if ouvidas[alt - 12] or ouvidas[alt + 12]:
                oitava += k
            elif ouvidas[alt - 1] or ouvidas[alt + 1]:
                semitom += k
    return {
        "t0": t0,
        "t1": t1,
        "n_gabarito": n_gab,
        "n_pareadas": n_par,
        "n_som_trecho": n_som,
        "n_som_pareadas": n_par,
        "acordes": acordes,
        "oitava": oitava,
        "semitom": semitom,
    }


def melhor_exibicao(
    colunas: list[list[dict]],
    som: list[dict],
    exibicoes: list[tuple[float, float]],
    desvio: int = 0,
) -> dict | None:
    """A exibição com mais alturas pareadas (empate: a primeira).

    Args:
        colunas: colunas do gabarito da tela.
        som: notas do transcritor no vídeo.
        exibicoes: janelas ``(t0, t1)`` da tela.
        desvio: semitons somados ao gabarito.

    Returns:
        A medida da melhor exibição, ou ``None`` sem exibição.
    """
    melhor = None
    for t0, t1 in exibicoes:
        m = medir_exibicao(colunas, som, t0, t1, desvio)
        if melhor is None or m["n_pareadas"] > melhor["n_pareadas"]:
            melhor = m
    return melhor


def capo_do_video(video: str, capos: dict) -> int:
    """Casa do capo de um vídeo pelo ``capo_por_video.json`` (sem entrada: 0).

    Args:
        video: caminho relativo do vídeo no acervo.
        capos: conteúdo do ``capo_por_video.json``.

    Returns:
        A casa do capo.
    """
    for v in capos.get("videos", []):
        if v["arquivo"] == video:
            return int(v["casa"])
    return 0


def pontos_de_escuta(pasta: Path) -> list[dict]:
    """Os pontos "certo" das folhas de escuta, sem controles e sem repetição.

    Mesma regra da rodada 2017: folhas 1 e 2 com ``resposta_dono == "certo"``; da folha 3,
    os itens em que o dono escolheu o alinhador com diferença ≥ 100 ms.

    Args:
        pasta: ``data/gold/audio``.

    Returns:
        ``{id, video, t}`` por ponto.
    """
    pontos: dict[tuple, dict] = {}
    for nome in ("folha1", "folha2"):
        doc = json.loads((pasta / f"{nome}.json").read_text(encoding="utf-8"))
        for it in doc["itens"]:
            if it.get("controle") or it["resposta_dono"] != "certo":
                continue
            chave = (it["video"], it["tela"], it["exibicao"], it["coluna"])
            pontos.setdefault(
                chave, {"id": it["id"], "video": it["video"], "t": it["t_clique"]}
            )
    doc = json.loads((pasta / "folha3.json").read_text(encoding="utf-8"))
    for it in doc["itens"]:
        if it.get("escolheu") != "alinhador" or abs(int(it["d_ms"])) < 100:
            continue
        chave = (it["video"], it["tela"], it["exibicao"], it["coluna"])
        pontos.setdefault(
            chave, {"id": it["id"], "video": it["video"], "t": it["t_alinhador"]}
        )
    return list(pontos.values())


def instante_acertado(
    t: float, som: list[dict], tolerancia: float = INSTANTE_S
) -> bool:
    """Diz se há início de nota ouvida a até ``tolerancia`` de ``t``.

    Args:
        t: instante do ponto de escuta (s).
        som: notas do transcritor.
        tolerancia: distância máxima (s).

    Returns:
        ``True`` se houver.
    """
    return any(abs(n["t_ini"] - t) <= tolerancia for n in som)


def telas_do_ouro(nome: str) -> tuple[list[dict], dict[int, dict]]:
    """Telas conferidas de um gabarito de tablatura e as telas do ``pre.json`` dele.

    Args:
        nome: nome do arquivo em ``data/gold/ouro_video`` sem ``.json``.

    Returns:
        ``(telas_conferidas, pre_por_id)``.
    """
    ouro = json.loads((OURO_VIDEO / f"{nome}.json").read_text("utf-8"))
    if ouro.get("juntadas"):
        raise ValueError(f"{nome}: telas juntadas não previstas no pré-registro")
    pre = json.loads((PRE_OURO_VIDEO / nome / "pre.json").read_text(encoding="utf-8"))
    return [t for t in ouro["telas"] if t.get("conferida")], {
        t["id"]: t for t in pre["telas"]
    }


def telas_dos_acordes(pasta: Path) -> list[tuple[str, dict, dict, list]]:
    """As telas do gabarito de acorde cheio, com a exibição do produto da 2017.

    Args:
        pasta: pasta do material (``indice.json`` e ``pre.json``).

    Returns:
        ``(nome_do_produto, tela_do_ouro, tela_do_pre, exibicoes)`` por tela conferida.
    """
    ouro = json.loads((GABARITO_AUDIO / "acordes_2018.json").read_text("utf-8"))
    indice = {
        i["id"]: i
        for i in json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
    }
    pre = {
        t["id"]: t
        for t in json.loads((pasta / "pre.json").read_text(encoding="utf-8"))["telas"]
    }
    saida = []
    for t in ouro["telas"]:
        if not t.get("conferida"):
            continue
        ind = indice[t["id"]]
        prod = json.loads(
            (SAIDA_AUDIO / "r2017" / "produtos" / f"{ind['produto']}.json").read_text(
                encoding="utf-8"
            )
        )
        tela_p = next(x for x in prod["telas"] if x["id"] == ind["tela_produto"])
        exib = [(e["t0"], e["t1"]) for e in tela_p["exibicoes"]]
        saida.append((ind["produto"], t, pre[t["id"]], exib))
    return saida


def somar(medidas: list[dict]) -> dict:
    """Soma as contagens de várias telas e calcula revocação e precisão.

    Args:
        medidas: medidas por tela (``medir_exibicao``).

    Returns:
        ``{telas, n_gabarito, n_pareadas, n_som_trecho, revocacao, precisao, oitava,
        semitom}``.
    """
    g = sum(m["n_gabarito"] for m in medidas)
    p = sum(m["n_pareadas"] for m in medidas)
    s = sum(m["n_som_trecho"] for m in medidas)
    return {
        "telas": len(medidas),
        "n_gabarito": g,
        "n_pareadas": p,
        "n_som_trecho": s,
        "revocacao": round(p / g, 4) if g else None,
        "precisao": round(p / s, 4) if s else None,
        "oitava": sum(m["oitava"] for m in medidas),
        "semitom": sum(m["semitom"] for m in medidas),
    }


def medir(
    lista: list[dict],
    pasta_som: Path,
    pasta_acordes: Path,
    amplitude_minima: float = AMPLITUDE_MINIMA,
) -> dict:
    """Mede todos os vídeos da lista, com o controle negativo (+1 semitom).

    Args:
        lista: ``[{papel, nome, video, flac}]`` (papel ``ouro`` ou ``acordes``).
        pasta_som: pasta com ``<nome>.json`` do transcritor.
        pasta_acordes: pasta do material do gabarito de acorde cheio.
        amplitude_minima: notas ouvidas abaixo desta amplitude ficam de fora.

    Returns:
        Medida por vídeo (real e controle), acordes cheios e pontos de escuta.
    """
    capos = json.loads(CAPO.read_text(encoding="utf-8"))
    por_video, acordes, som_por_video = {}, [], {}
    for item in lista:
        som = json.loads((pasta_som / f"{item['nome']}.json").read_text("utf-8"))
        som["notas"] = [n for n in som["notas"] if n["amplitude"] >= amplitude_minima]
        som_por_video[item["video"]] = som["notas"]
        capo = capo_do_video(item["video"], capos)
        if item["papel"] == "ouro":
            conferidas, pre = telas_do_ouro(item["nome"])
            telas = [
                (
                    t["id"],
                    t["notas"],
                    float(pre[t["id"]]["passo"]),
                    [tuple(e) for e in pre[t["id"]]["exibicoes"]],
                )
                for t in conferidas
            ]
        else:
            telas = [
                (t["id"], t["notas"], float(tp["passo"]), exib)
                for prod, t, tp, exib in telas_dos_acordes(pasta_acordes)
                if prod == item["nome"]
            ]
        real, controle = [], []
        for tela_id, notas, passo, exib in telas:
            colunas = colunas_do_gabarito(notas, passo, capo)
            m = melhor_exibicao(colunas, som["notas"], exib)
            c = melhor_exibicao(colunas, som["notas"], exib, desvio=1)
            if m is None:
                continue
            m["tela"] = tela_id
            real.append(m)
            controle.append(c)
            acordes.extend(
                {"video": item["nome"], "tela": tela_id, "fracao": f}
                for f in m["acordes"]
            )
        por_video[item["nome"]] = {
            "papel": item["papel"],
            "video": item["video"],
            "capo": capo,
            "real": somar(real),
            "controle": somar(controle),
            "telas": real,
        }
    pontos = []
    for p in pontos_de_escuta(GABARITO_AUDIO):
        if p["video"] in som_por_video:
            p["acertado"] = instante_acertado(p["t"], som_por_video[p["video"]])
            pontos.append(p)
    return {
        "amplitude_minima": amplitude_minima,
        "por_video": por_video,
        "acordes": acordes,
        "pontos": pontos,
    }


def resumo(medida: dict, desenvolvimento: str) -> str:
    """Texto curto com os números dos critérios da 2018.

    Args:
        medida: saída de ``medir``.
        desenvolvimento: nome do vídeo de desenvolvimento (fora dos critérios).

    Returns:
        O texto.
    """
    linhas = [f"amplitude mínima {medida['amplitude_minima']}"]
    prova = []
    for nome, v in medida["por_video"].items():
        r, c = v["real"], v["controle"]
        linhas.append(
            f"{nome[:40]:40s} {v['papel']:8s} capo {v['capo']} | "
            f"{r['n_pareadas']}/{r['n_gabarito']} rev {r['revocacao']} "
            f"prec {r['n_pareadas']}/{r['n_som_trecho']} {r['precisao']} | "
            f"controle rev {c['revocacao']} | oitava {r['oitava']} semitom {r['semitom']}"
        )
        if v["papel"] == "ouro" and nome != desenvolvimento:
            prova.append(v)
    if prova:
        g = sum(v["real"]["n_gabarito"] for v in prova)
        p = sum(v["real"]["n_pareadas"] for v in prova)
        s = sum(v["real"]["n_som_trecho"] for v in prova)
        gc = sum(v["controle"]["n_gabarito"] for v in prova)
        pc = sum(v["controle"]["n_pareadas"] for v in prova)
        bons = sum(1 for v in prova if (v["real"]["revocacao"] or 0) >= 0.70)
        linhas.append(
            f"PROVA: C1 rev {p}/{g} = {p / g:.3f}; vídeos >= 0,70: {bons}/{len(prova)} | "
            f"C2 prec {p}/{s} = {p / s:.3f} | V controle {pc}/{gc} = {pc / gc:.3f}"
        )
    fr = [a["fracao"] for a in medida["acordes"]]
    if fr:
        linhas.append(
            f"C3 acordes cheios: {len(fr)} colunas, mediana {statistics.median(fr):.3f}"
        )
    dev = medida["por_video"].get(desenvolvimento, {}).get("video")
    pts = [x for x in medida["pontos"] if x["video"] != dev]
    linhas.append(
        f"C4 escuta (sem o desenvolvimento): "
        f"{sum(x['acertado'] for x in pts)}/{len(pts)}"
    )
    return "\n".join(linhas)


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lista", type=Path, required=True)
    ap.add_argument("--som", type=Path, required=True, help="pasta com <nome>.json")
    ap.add_argument(
        "--acordes",
        type=Path,
        default=SAIDA_AUDIO / "r2018" / "ferramenta_acordes",
        help="material do gabarito de acorde cheio",
    )
    ap.add_argument("--so", nargs="*", default=None, help="só estes nomes da lista")
    ap.add_argument("--desenvolvimento", default="retrato_brasileiro_v2")
    ap.add_argument("--amplitude-minima", type=float, default=AMPLITUDE_MINIMA)
    ap.add_argument("--saida", type=Path, required=True)
    args = ap.parse_args()
    lista = json.loads(args.lista.read_text(encoding="utf-8"))
    if args.so:
        lista = [x for x in lista if x["nome"] in args.so]
    medida = medir(lista, args.som, args.acordes, args.amplitude_minima)
    args.saida.write_text(
        json.dumps(medida, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    texto = resumo(medida, args.desenvolvimento)
    args.saida.with_suffix(".txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
