"""Régua do produto: compara a predição de um vídeo com o ouro de vídeo.

O ouro (``data/gold/ouro_video/<slug>.json``) é rotulado à mão pelo dono. Esta régua mede,
contra ele, três coisas:

1. **telas**: se cada tela do ouro tem uma tela prevista que a mostra nos mesmos instantes;
2. **notas**: corda e casa, por par de telas, contando só a casa numérica entregue;
3. **tempo**: em cada instante do ouro, se a predição diz a coluna certa acesa em ``t``.

Aceita dois formatos de predição. O v1 (``esquema: chorinho/video@1``) e o legado que o
``tab.transcrever`` gera hoje, tratado como uma tela cuja exibição é o vídeo inteiro. No
legado sem ``x_quadro`` a régua diz por que não avalia notas nem tempo.

Todo número sai como "X de Y". As funções são puras; ``main`` só lê, chama e imprime.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .colunas import agrupar_colunas

FORMATO_V1 = "chorinho/video@1"

#: Tolerância de tempo, em segundos. Se a predição diz a coluna **atual** e o ouro diz a
#: coluna **imediatamente anterior** (no tempo), a régua aceita quando ``t`` está a até
#: este intervalo do onset da atual: é a resolução da amostragem do observador.
TOLERANCIA_S = 0.2

#: Fração do passo que define "mesmo x", tanto para nota quanto para coluna. É o critério
#: do plano (§6, Fase 2): ``|Δx_quadro| <= 0,5 * passo``.
FRACAO_PASSO = 0.5

CLASSES_TEMPO = (
    "acerto",
    "acerto_tolerancia",
    "erro",
    "json_sem_tempo",
    "tempo_falso",
    "ausencia_certa",
)


@dataclass
class NotaPrevista:
    """Uma nota da predição, já no espaço do quadro.

    Attributes:
        corda: número da corda (1 a 6).
        casa: casa como inteiro; ``None`` quando o símbolo não é numérico (não é entregue).
        x: ``x_quadro`` da nota; ``None`` em JSON anterior ao espaço do quadro.
        t_ini: instante de início em segundos; ``None`` quando não há tempo.
    """

    corda: int
    casa: int | None
    x: float | None
    t_ini: float | None


@dataclass
class TelaPrevista:
    """Uma tela da predição, com as exibições em que ela aparece no vídeo.

    Attributes:
        id: identificador da tela na predição.
        passo: distância vertical entre cordas, em px; ``None`` se ausente.
        exibicoes: intervalos ``(t0, t1)`` em que a tela está visível.
        medido: ``True`` quando a predição afirma tempo para esta tela.
        notas: notas da tela (numéricas e não numéricas, todas com ``x`` se avaliável).
    """

    id: int
    passo: float | None
    exibicoes: list[tuple[float, float]]
    medido: bool
    notas: list[NotaPrevista] = field(default_factory=list)


@dataclass
class Predicao:
    """A predição normalizada, independente do formato de origem.

    Attributes:
        formato: ``chorinho/video@1`` ou ``legado``.
        telas: telas da predição (no legado, uma só).
        modelo: caminho do modelo que gerou a predição, se constar.
        commit: commit do código que gerou a predição, se constar.
        video: nome do vídeo segundo a predição, se constar.
    """

    formato: str
    telas: list[TelaPrevista]
    modelo: str | None
    commit: str | None
    video: str | None


@dataclass(frozen=True)
class ColunaAtual:
    """A coluna que a predição diz estar acesa num instante.

    Attributes:
        x: ``x_quadro`` da coluna acesa.
        onset: instante em que ela passou a ser a atual (``t_ini`` mais recente).
        anterior_x: ``x_quadro`` da coluna imediatamente anterior no tempo, ou ``None``.
    """

    x: float
    onset: float
    anterior_x: float | None


def ler_predicao(dados: dict) -> Predicao:
    """Normaliza uma predição v1 ou legada.

    Args:
        dados: JSON já carregado da predição.

    Returns:
        A ``Predicao`` no formato interno da régua.

    Raises:
        ValueError: se houver tela repetida ou nota apontando para tela inexistente.
    """
    if dados.get("esquema") == FORMATO_V1:
        return _ler_v1(dados)
    return _ler_legado(dados)


def validar_ouro(ouro: dict) -> None:
    """Confere a forma mínima do ouro antes de avaliar.

    Args:
        ouro: JSON já carregado do ouro de vídeo.

    Raises:
        ValueError: se houver ids de tela repetidos, instante sem ``t``, coluna acesa sem
            tela, ou instante apontando para tela que não está em ``telas``.
    """
    ids = [int(tela["id"]) for tela in ouro.get("telas", [])]
    if len(set(ids)) != len(ids):
        raise ValueError("ids de tela repetidos no ouro")
    for instante in ouro.get("instantes", []):
        if "t" not in instante:
            raise ValueError("instante do ouro sem 't'")
        tela = instante.get("tela")
        if instante.get("coluna_x_quadro") is not None and tela is None:
            raise ValueError(f"instante t={instante['t']}: coluna acesa sem tela")
        if tela is not None and tela not in ids:
            raise ValueError(
                f"instante t={instante['t']} aponta para a tela {tela}, "
                "que não está em 'telas'"
            )


def casar_telas(
    ids_ouro: list[int], instantes: list[dict], telas: list[TelaPrevista]
) -> dict[int, int | None]:
    """Casa cada tela do ouro com a tela prevista que mais aparece nos seus instantes.

    O casamento é um a um e guloso: os pares com mais instantes em comum vêm primeiro,
    e empates saem pela ordem dos ids. Uma tela do ouro sem nenhum instante coberto
    pela predição fica sem par.

    Args:
        ids_ouro: ids das telas do ouro.
        instantes: instantes do ouro (cada um com ``t`` e ``tela``).
        telas: telas da predição.

    Returns:
        Mapa ``id da tela do ouro -> id da tela prevista`` (ou ``None``).
    """
    contagem: dict[tuple[int, int], int] = {}
    for instante in instantes:
        tela_ouro = instante.get("tela")
        if tela_ouro is None:
            continue
        for tela in telas:
            if _exibicao_em(float(instante["t"]), tela) is not None:
                par = (int(tela_ouro), tela.id)
                contagem[par] = contagem.get(par, 0) + 1
    usadas: set[int] = set()
    casadas: dict[int, int] = {}
    for _, tela_ouro, tela_prevista in sorted(
        (-n, o, p) for (o, p), n in contagem.items()
    ):
        if tela_ouro in casadas or tela_prevista in usadas:
            continue
        casadas[tela_ouro] = tela_prevista
        usadas.add(tela_prevista)
    return {tid: casadas.get(tid) for tid in ids_ouro}


def casar_notas(
    notas_ouro: list[dict], previstas: list[NotaPrevista], meia_janela: float
) -> list[tuple[int, int]]:
    """Casa notas do ouro com notas entregues: mesma corda e ``|Δx| <= meia_janela``.

    O casamento é guloso por menor distância em x. Cada nota participa de no máximo um
    par. Só as notas com casa numérica devem chegar em ``previstas``.

    Args:
        notas_ouro: notas do ouro de uma tela (com ``corda``, ``casa`` e ``x_quadro``).
        previstas: notas entregues da tela prevista (casa numérica e ``x`` presente).
        meia_janela: ``FRACAO_PASSO * passo``, em px.

    Returns:
        Pares ``(índice no ouro, índice na predição)``, na ordem em que foram casados.
    """
    candidatos: list[tuple[float, int, int]] = []
    for i, nota in enumerate(notas_ouro):
        for j, prevista in enumerate(previstas):
            if prevista.x is None or prevista.corda != nota["corda"]:
                continue
            distancia = abs(float(nota["x_quadro"]) - prevista.x)
            if distancia <= meia_janela:
                candidatos.append((distancia, i, j))
    candidatos.sort()
    usadas_ouro: set[int] = set()
    usadas_previsao: set[int] = set()
    pares: list[tuple[int, int]] = []
    for _, i, j in candidatos:
        if i in usadas_ouro or j in usadas_previsao:
            continue
        usadas_ouro.add(i)
        usadas_previsao.add(j)
        pares.append((i, j))
    return pares


def ocorrencias(tela: TelaPrevista) -> list[tuple[float, float, int]]:
    """Lista ``(t_ini, x da coluna, índice da coluna)`` das notas da tela com tempo.

    As colunas saem de ``agrupar_colunas`` sobre **todas** as notas da tela, porque o
    marcador passa por todas elas, inclusive pelas não numéricas. Só entram na lista as
    notas com ``t_ini``.

    Args:
        tela: tela prevista, com passo válido e ``x`` em todas as notas.

    Returns:
        Lista de ocorrências, na ordem das notas. Vazia se a tela não tem tempo.
    """
    if not tela.notas or tela.passo is None or tela.passo <= 0:
        return []
    colunas = agrupar_colunas([float(n.x) for n in tela.notas], tela.passo)
    coluna_de: dict[int, int] = {}
    for indice, coluna in enumerate(colunas):
        for membro in coluna.indices:
            coluna_de[membro] = indice
    return [
        (n.t_ini, colunas[coluna_de[i]].x_quadro, coluna_de[i])
        for i, n in enumerate(tela.notas)
        if n.t_ini is not None
    ]


def coluna_atual(
    t: float, tela: TelaPrevista, ocorr: list[tuple[float, float, int]]
) -> ColunaAtual | None:
    """Coluna que a predição diz estar acesa em ``t``, dentro da exibição de ``t``.

    É a coluna cujo onset é o mais recente que não passa de ``t``, considerando só as
    ocorrências da exibição que contém ``t`` (o onset não pode ser de outra exibição).

    Args:
        t: instante do ouro, em segundos.
        tela: tela prevista que está na tela em ``t``.
        ocorr: ocorrências de ``ocorrencias(tela)``.

    Returns:
        A ``ColunaAtual``, ou ``None`` se a predição não afirma coluna em ``t``.
    """
    exibicao = _exibicao_em(t, tela)
    if not tela.medido or exibicao is None:
        return None
    inicio = exibicao[0]
    dentro = [o for o in ocorr if inicio <= o[0] <= t]
    if not dentro:
        return None
    onset, x_atual, indice_atual = max(dentro, key=lambda o: (o[0], o[1]))
    anteriores = [o for o in dentro if o[0] < onset and o[2] != indice_atual]
    anterior_x = None
    if anteriores:
        anterior_x = max(anteriores, key=lambda o: (o[0], o[1]))[1]
    return ColunaAtual(x=x_atual, onset=onset, anterior_x=anterior_x)


def classificar_instante(
    t: float, coluna_ouro: float | None, atual: ColunaAtual | None, passo: float
) -> str:
    """Classifica um instante do ouro contra a coluna que a predição afirma.

    Args:
        t: instante, em segundos.
        coluna_ouro: ``coluna_x_quadro`` do ouro, ou ``None`` ("nenhuma acesa").
        atual: coluna que a predição afirma em ``t``, ou ``None``.
        passo: passo da tela prevista, em px.

    Returns:
        Uma das ``CLASSES_TEMPO``.
    """
    if coluna_ouro is None:
        return "tempo_falso" if atual is not None else "ausencia_certa"
    if atual is None:
        return "json_sem_tempo"
    limite = FRACAO_PASSO * passo
    if abs(atual.x - coluna_ouro) <= limite:
        return "acerto"
    anterior_bate = atual.anterior_x is not None and (
        abs(atual.anterior_x - coluna_ouro) <= limite
    )
    if anterior_bate and t - atual.onset <= TOLERANCIA_S:
        return "acerto_tolerancia"
    return "erro"


def avaliar(ouro: dict, predicao: Predicao) -> dict:
    """Calcula as três medidas da régua: telas, notas e tempo.

    A função é pura: a mesma entrada dá sempre o mesmo relatório.

    Args:
        ouro: JSON do ouro de vídeo, já validado por ``validar_ouro``.
        predicao: predição normalizada por ``ler_predicao``.

    Returns:
        Relatório com ``telas``, ``notas`` e ``tempo``, mais os metadados da predição.
        Notas e tempo saem com ``avaliavel: false`` e ``motivo`` quando a predição não
        tem ``x_quadro`` ou ``passo`` suficientes.
    """
    telas_ouro = ouro.get("telas", [])
    instantes = ouro.get("instantes", [])
    ids_ouro = [int(tela["id"]) for tela in telas_ouro]
    mapa = casar_telas(ids_ouro, instantes, predicao.telas)
    casadas = sum(1 for previsto in mapa.values() if previsto is not None)
    motivo = _motivo_nao_avaliavel(predicao)
    if motivo is None:
        notas = _avaliar_notas(telas_ouro, mapa, predicao.telas)
        tempo = _avaliar_tempo(instantes, mapa, predicao.telas)
    else:
        notas = {"avaliavel": False, "motivo": motivo}
        tempo = {"avaliavel": False, "motivo": motivo}
    return {
        "formato_predicao": predicao.formato,
        "modelo": predicao.modelo,
        "commit": predicao.commit,
        "video": ouro.get("video"),
        "video_predicao": predicao.video,
        "tolerancia_s": TOLERANCIA_S,
        "fracao_passo": FRACAO_PASSO,
        "telas": {
            "ouro": len(ids_ouro),
            "casadas": casadas,
            "previstas": len(predicao.telas),
            "sem_par_no_ouro": len(predicao.telas) - casadas,
            "mapa": {str(k): v for k, v in mapa.items()},
        },
        "notas": notas,
        "tempo": tempo,
    }


def linhas_do_relatorio(rel: dict) -> list[str]:
    """Monta as linhas impressas do relatório, sempre com denominadores.

    Args:
        rel: relatório de ``avaliar``, com ``ouro_caminho`` e ``predicao_caminho``.

    Returns:
        Linhas de texto, sem quebra de linha no fim.
    """
    telas = rel["telas"]
    linhas = [
        f"ouro:     {rel['ouro_caminho']}  (vídeo: {rel['video'] or 'não consta'})",
        f"predição: {rel['predicao_caminho']}  (formato: {rel['formato_predicao']};"
        f" modelo: {rel['modelo'] or 'não consta'};"
        f" commit: {rel['commit'] or 'não consta'})",
        f"telas: {telas['casadas']} de {telas['ouro']} telas do ouro com par previsto"
        f" (previstas: {telas['previstas']}; sem par no ouro:"
        f" {telas['sem_par_no_ouro']})",
    ]
    linhas += _linhas_notas(rel["notas"])
    linhas += _linhas_tempo(rel["tempo"])
    linhas.append(
        f"tolerância: {rel['tolerancia_s']} s (coluna imediatamente anterior);"
        f" casamento de x: {rel['fracao_passo']} * passo"
    )
    return linhas


def _ler_v1(dados: dict) -> Predicao:
    """Lê o formato v1 (``chorinho/video@1``).

    Args:
        dados: JSON da predição v1.

    Returns:
        A ``Predicao`` com as notas de cada tela.

    Raises:
        ValueError: se houver tela repetida ou nota apontando para tela inexistente.
    """
    telas: list[TelaPrevista] = []
    for bruta in dados.get("telas", []):
        tid = int(bruta["id"])
        if any(t.id == tid for t in telas):
            raise ValueError(f"tela {tid} repetida na predição")
        telas.append(
            TelaPrevista(
                id=tid,
                passo=_float_ou_none(bruta.get("passo")),
                exibicoes=[
                    (float(e["t0"]), float(e["t1"])) for e in bruta.get("exibicoes", [])
                ],
                medido=_medido(bruta),
            )
        )
    for bruta in dados.get("notas", []):
        tid = int(bruta["tela"])
        alvo = next((t for t in telas if t.id == tid), None)
        if alvo is None:
            raise ValueError(f"nota aponta para a tela {tid}, que não existe")
        alvo.notas.append(_nota(bruta))
    gerado = dados.get("gerado_por") or {}
    video = dados.get("video") or {}
    return Predicao(
        formato=FORMATO_V1,
        telas=telas,
        modelo=gerado.get("modelo"),
        commit=gerado.get("commit"),
        video=video.get("arquivo"),
    )


def _ler_legado(dados: dict) -> Predicao:
    """Lê o formato legado do ``tab.transcrever``: uma tela, exibição = vídeo inteiro.

    Args:
        dados: JSON da predição legada.

    Returns:
        A ``Predicao`` com uma tela de id 0 e todas as notas do JSON.
    """
    tela = TelaPrevista(
        id=0,
        passo=_float_ou_none(dados.get("passo")),
        exibicoes=[(-math.inf, math.inf)],
        medido=_medido(dados),
        notas=[_nota(n) for n in dados.get("notas", [])],
    )
    return Predicao(
        formato="legado",
        telas=[tela],
        modelo=None,
        commit=None,
        video=dados.get("video"),
    )


def _medido(bruto: dict) -> bool:
    """Diz se a predição (ou a tela) afirma tempo medido.

    Args:
        bruto: o dicionário da tela, ou o JSON legado inteiro.

    Returns:
        ``True`` só quando ``tempo.medido`` é exatamente ``True``.
    """
    tempo = bruto.get("tempo") or {}
    return tempo.get("medido") is True


def _nota(bruta: dict) -> NotaPrevista:
    """Converte uma nota do JSON para ``NotaPrevista``.

    Args:
        bruta: nota como está no JSON (v1 ou legado).

    Returns:
        A ``NotaPrevista``. A casa só é numérica se for dígitos.
    """
    return NotaPrevista(
        corda=int(bruta["corda"]),
        casa=_casa(bruta.get("casa")),
        x=_float_ou_none(bruta.get("x_quadro")),
        t_ini=_float_ou_none(bruta.get("t_ini")),
    )


def _casa(valor: object) -> int | None:
    """Devolve a casa como inteiro, ou ``None`` se o símbolo não é numérico.

    Args:
        valor: o campo ``casa`` como está no JSON (inteiro no v1, texto no legado).

    Returns:
        O inteiro, ou ``None`` para ``"harmonico"``, ``"junk"``, ``"tecnica"`` etc.
    """
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str) and valor.isascii() and valor.isdigit():
        return int(valor)
    return None


def _float_ou_none(valor: object) -> float | None:
    """Converte para float, preservando ``None``.

    Args:
        valor: número, ``None`` ou texto numérico.

    Returns:
        O valor como float, ou ``None``.
    """
    return None if valor is None else float(valor)


def _exibicao_em(t: float, tela: TelaPrevista) -> tuple[float, float] | None:
    """Devolve a primeira exibição da tela que contém ``t``.

    Args:
        t: instante, em segundos.
        tela: tela prevista.

    Returns:
        O par ``(t0, t1)``, ou ``None`` se a tela não está visível em ``t``.
    """
    for inicio, fim in tela.exibicoes:
        if inicio <= t <= fim:
            return (inicio, fim)
    return None


def tela_em_t(
    t: float,
    tela_ouro: int | None,
    mapa: dict[int, int | None],
    telas: list[TelaPrevista],
) -> TelaPrevista | None:
    """Escolhe a tela prevista que a predição mostra em ``t``.

    Se a tela prevista casada com a tela do ouro estiver visível em ``t``, ela vence.
    Senão vale a primeira visível, pela ordem da predição.

    Args:
        t: instante, em segundos.
        tela_ouro: tela do ouro no instante, ou ``None`` ("sem tablatura").
        mapa: resultado de ``casar_telas``.
        telas: telas da predição.

    Returns:
        A tela prevista visível em ``t``, ou ``None``.
    """
    visiveis = [tela for tela in telas if _exibicao_em(t, tela) is not None]
    alvo = mapa.get(tela_ouro) if tela_ouro is not None else None
    for tela in visiveis:
        if tela.id == alvo:
            return tela
    return visiveis[0] if visiveis else None


def _motivo_nao_avaliavel(predicao: Predicao) -> str | None:
    """Explica por que a predição não pode ser comparada em notas e tempo.

    Args:
        predicao: predição normalizada.

    Returns:
        O motivo em português, ou ``None`` se a predição é avaliável.
    """
    total = sum(len(t.notas) for t in predicao.telas)
    sem_x = sum(1 for t in predicao.telas for n in t.notas if n.x is None)
    if sem_x:
        return (
            f"{sem_x} de {total} notas da predição sem x_quadro (JSON anterior ao "
            "espaço do quadro): sem ele não há como casar nota nem coluna"
        )
    for tela in predicao.telas:
        if tela.passo is None or tela.passo <= 0:
            return f"tela {tela.id} sem passo válido na predição"
    return None


def _avaliar_notas(
    telas_ouro: list[dict], mapa: dict[int, int | None], telas: list[TelaPrevista]
) -> dict:
    """Mede casa e corda, por par de telas e no total.

    Args:
        telas_ouro: telas do ouro (cada uma com ``id`` e ``notas``).
        mapa: resultado de ``casar_telas``.
        telas: telas da predição.

    Returns:
        Dicionário com ``por_tela``, ``previsoes_sem_par`` e ``total``.
    """
    previstas_por_id = {t.id: [n for n in t.notas if n.casa is not None] for t in telas}
    passo_por_id = {t.id: t.passo for t in telas}
    por_tela = []
    for tela in telas_ouro:
        oid = int(tela["id"])
        pid = mapa.get(oid)
        meia = FRACAO_PASSO * (passo_por_id[pid] or 0.0) if pid is not None else 0.0
        previstas = previstas_por_id[pid] if pid is not None else []
        por_tela.append(
            {
                "ouro_tela": oid,
                "previsao_tela": pid,
                **_metricas_par(tela.get("notas", []), previstas, meia),
            }
        )
    casadas_previstas = set(mapa.values())
    sem_par = [
        {"previsao_tela": tid, "entregues": len(previstas)}
        for tid, previstas in previstas_por_id.items()
        if tid not in casadas_previstas and previstas
    ]
    total = _somar_notas(por_tela, sem_par, telas_ouro, previstas_por_id)
    return {
        "avaliavel": True,
        "motivo": None,
        "por_tela": por_tela,
        "previsoes_sem_par": sem_par,
        "total": total,
    }


def _metricas_par(
    notas_ouro: list[dict], previstas: list[NotaPrevista], meia: float
) -> dict:
    """Mede um par de telas: entregues, casadas, casa certa, inventadas e perdidas.

    Args:
        notas_ouro: notas do ouro da tela.
        previstas: notas numéricas entregues da tela prevista.
        meia: ``FRACAO_PASSO * passo``, em px.

    Returns:
        Dicionário com as contagens e as razões ``precisao``, ``revocacao`` e
        ``acerto_casa`` (``None`` quando o denominador é zero).
    """
    pares = casar_notas(notas_ouro, previstas, meia)
    casa_certa = sum(
        1 for i, j in pares if int(notas_ouro[i]["casa"]) == previstas[j].casa
    )
    return {
        "notas_ouro": len(notas_ouro),
        "entregues": len(previstas),
        "casadas": len(pares),
        "casa_certa": casa_certa,
        "inventadas": len(previstas) - len(pares),
        "perdidas": len(notas_ouro) - len(pares),
        "precisao": _razao(len(pares), len(previstas)),
        "revocacao": _razao(len(pares), len(notas_ouro)),
        "acerto_casa": _razao(casa_certa, len(pares)),
    }


def _somar_notas(
    por_tela: list[dict],
    sem_par: list[dict],
    telas_ouro: list[dict],
    previstas_por_id: dict[int, list[NotaPrevista]],
) -> dict:
    """Soma as métricas de notas de todas as telas, incluindo as previstas sem par.

    Args:
        por_tela: métricas de cada par de telas.
        sem_par: telas previstas sem par no ouro (com as notas entregues).
        telas_ouro: telas do ouro.
        previstas_por_id: notas numéricas de cada tela prevista.

    Returns:
        Dicionário com os totais e as razões.
    """
    notas_ouro = sum(len(t.get("notas", [])) for t in telas_ouro)
    entregues = sum(len(v) for v in previstas_por_id.values())
    casadas = sum(p["casadas"] for p in por_tela)
    casa_certa = sum(p["casa_certa"] for p in por_tela)
    return {
        "notas_ouro": notas_ouro,
        "entregues": entregues,
        "casadas": casadas,
        "casa_certa": casa_certa,
        "inventadas": entregues - casadas,
        "perdidas": notas_ouro - casadas,
        "precisao": _razao(casadas, entregues),
        "revocacao": _razao(casadas, notas_ouro),
        "acerto_casa": _razao(casa_certa, casadas),
        "entregues_sem_par_no_ouro": sum(p["entregues"] for p in sem_par),
    }


def _avaliar_tempo(
    instantes: list[dict], mapa: dict[int, int | None], telas: list[TelaPrevista]
) -> dict:
    """Classifica cada instante do ouro contra a coluna que a predição afirma.

    Args:
        instantes: instantes do ouro.
        mapa: resultado de ``casar_telas``.
        telas: telas da predição.

    Returns:
        Dicionário com a contagem de cada classe e os totais com e sem coluna acesa.
    """
    ocorr = {tela.id: ocorrencias(tela) for tela in telas}
    classes = dict.fromkeys(CLASSES_TEMPO, 0)
    for instante in instantes:
        t = float(instante["t"])
        coluna = instante.get("coluna_x_quadro")
        tela = tela_em_t(t, instante.get("tela"), mapa, telas)
        atual = None
        passo = 0.0
        if tela is not None:
            atual = coluna_atual(t, tela, ocorr[tela.id])
            passo = tela.passo or 0.0
        coluna_f = None if coluna is None else float(coluna)
        classes[classificar_instante(t, coluna_f, atual, passo)] += 1
    com_coluna = sum(1 for i in instantes if i.get("coluna_x_quadro") is not None)
    certos = classes["acerto"] + classes["acerto_tolerancia"]
    return {
        "avaliavel": True,
        "motivo": None,
        "instantes": len(instantes),
        "com_coluna": com_coluna,
        "sem_coluna": len(instantes) - com_coluna,
        "classes": classes,
        "estado_certo": certos,
        "ausencia_certa": classes["ausencia_certa"],
    }


def _razao(numerador: int, denominador: int) -> float | None:
    """Razão entre duas contagens, ou ``None`` sem denominador.

    Args:
        numerador: contagem de cima.
        denominador: contagem de baixo.

    Returns:
        ``numerador / denominador``, ou ``None`` se o denominador é zero.
    """
    return numerador / denominador if denominador else None


def _fmt_razao(valor: float | None) -> str:
    """Formata uma razão com vírgula decimal, ou ``sem denominador``.

    Args:
        valor: razão de ``_razao``.

    Returns:
        Texto com três casas decimais, ou ``sem denominador``.
    """
    return "sem denominador" if valor is None else f"{valor:.3f}".replace(".", ",")


def _linhas_notas(notas: dict) -> list[str]:
    """Linhas do bloco de notas, com denominadores.

    Args:
        notas: bloco ``notas`` do relatório.

    Returns:
        Linhas de texto.
    """
    if not notas["avaliavel"]:
        return [f"notas: NÃO AVALIADAS: {notas['motivo']}"]
    t = notas["total"]
    return [
        f"notas (total): precisão {t['casadas']} de {t['entregues']} entregues"
        f" = {_fmt_razao(t['precisao'])}",
        f"  revocação {t['casadas']} de {t['notas_ouro']} do ouro"
        f" = {_fmt_razao(t['revocacao'])}",
        f"  inventadas {t['inventadas']} de {t['entregues']} entregues",
        f"  perdidas {t['perdidas']} de {t['notas_ouro']} do ouro",
        f"  acerto de casa {t['casa_certa']} de {t['casadas']} casadas"
        f" = {_fmt_razao(t['acerto_casa'])}",
    ]


def _linhas_tempo(tempo: dict) -> list[str]:
    """Linhas do bloco de tempo, com denominadores.

    Args:
        tempo: bloco ``tempo`` do relatório.

    Returns:
        Linhas de texto.
    """
    if not tempo["avaliavel"]:
        return [f"tempo: NÃO AVALIADO: {tempo['motivo']}"]
    c = tempo["classes"]
    com = tempo["com_coluna"]
    sem = tempo["sem_coluna"]
    return [
        f"tempo: {tempo['estado_certo']} de {com} instantes com coluna acesa"
        f" com o estado certo (acerto {c['acerto']}, tolerância"
        f" {c['acerto_tolerancia']}, erro {c['erro']}, json sem tempo"
        f" {c['json_sem_tempo']})",
        f"  sem coluna acesa: ausência certa {c['ausencia_certa']} de {sem}"
        f" instantes; tempo falso {c['tempo_falso']} de {sem}",
    ]


def main() -> int:
    """Lê o ouro e a predição, avalia e imprime o relatório.

    Returns:
        ``0`` ao avaliar, ``2`` se o ouro ou a predição forem inválidos.
    """
    ap = argparse.ArgumentParser(
        description="Régua do produto: ouro de vídeo x predição."
    )
    ap.add_argument("--ouro", required=True, help="data/gold/ouro_video/<slug>.json")
    ap.add_argument("--pred", required=True, help="saída do tab.transcrever (JSON)")
    ap.add_argument("--json", help="grava o relatório completo neste arquivo")
    args = ap.parse_args()

    caminho_ouro = Path(args.ouro)
    caminho_pred = Path(args.pred)
    ouro = json.loads(caminho_ouro.read_text(encoding="utf-8"))
    dados = json.loads(caminho_pred.read_text(encoding="utf-8"))
    try:
        validar_ouro(ouro)
        predicao = ler_predicao(dados)
    except (ValueError, KeyError) as erro:
        print(f"entrada inválida: {erro}", file=sys.stderr)
        return 2

    rel = avaliar(ouro, predicao)
    rel["ouro_caminho"] = str(caminho_ouro)
    rel["predicao_caminho"] = str(caminho_pred)
    for linha in linhas_do_relatorio(rel):
        print(linha)
    if args.json:
        Path(args.json).write_text(
            json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print("relatório salvo em", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
