"""Geometria do braço (M3b): eixo, modelo físico dos trastes e previsão.

Mede a ideia do dono (rodada 1005): a distância do nut ao traste ``n`` é
``L * (1 - 2 ** (-n / 12))``. Com o nut e poucos trastes, o resto sai por cálculo?
A câmera distorce o braço ao longo do eixo, então o modelo sai em duas formas:
afim (``t = a*s + b``, 2 âncoras) e projetivo 1D (``t = (a*s + b) / (c*s + 1)``,
3 âncoras). Cada variante ajusta o modelo em algumas âncoras e mede o erro nos
trastes que ficaram de fora. Os pisos ajustam em todos os pontos: medem o ruído do
clique e do modelo, não são previsão.

Funções puras (testadas em ``tests/test_maos_braco_geometria.py``) e a CLI
``python -m tab.maos_braco_geometria``, que grava em ``data/saida/maos/m3b/geometria``
o ``resultado.json``, as imagens dos quadros suspeitos e a folha.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from tab.comum.caminhos import GABARITO_BRACO, MAOS_M3B
from tab.maos.braco.gabarito import numerar_trastes, registro_completo

PASTA_QUADROS = MAOS_M3B / "quadros"
PASTA_GEOMETRIA = MAOS_M3B / "geometria"

#: Fração da largura da casa dentro da qual o dedo cai na casa certa.
FRACAO_CASA = 0.25
#: Resíduo do piso (em fração da casa) acima do qual o quadro é suspeito.
FRACAO_SUSPEITA = 0.15
#: Versão do formato do ``resultado.json``.
FORMATO_RESULTADO = 1
#: Variantes de previsão: nome -> (modelo, números dos trastes âncora).
VARIANTES: dict[str, tuple[str, tuple[int, ...]]] = {
    "afim_nut_5": ("afim", (5,)),
    "afim_nut_12": ("afim", (12,)),
    "proj_nut_5_12": ("proj", (5, 12)),
    "proj_nut_3_7": ("proj", (3, 7)),
}
#: Pisos: ajuste em todos os pontos. Não são previsão, medem o ruído.
PISOS: dict[str, str] = {"proj_todos": "proj", "afim_todos": "afim"}
#: Variante desenhada na folha e nas imagens de diagnóstico (vermelho).
VARIANTE_DESENHO = "proj_nut_5_12"
#: Cores em BGR (OpenCV).
COR_CLIQUE = (0, 255, 0)
COR_PREVISAO = (0, 0, 255)
COR_PISO = (0, 255, 255)
COR_CORDA = (255, 180, 0)
COR_EIXO = (200, 200, 200)
COR_NUT = (255, 0, 255)


@dataclasses.dataclass(frozen=True)
class Traste:
    """Um traste clicado e numerado.

    Attributes:
        numero: número do traste (1 é o mais perto do nut).
        t: posição ao longo do eixo, em px, a partir da âncora (sinal para o corpo).
        ponto: clique no espaço do quadro.
    """

    numero: int
    t: float
    ponto: np.ndarray


@dataclasses.dataclass(frozen=True)
class Geometria:
    """Eixo e trastes de um quadro, prontos para o ajuste.

    Attributes:
        id: id do quadro (``qNN``).
        u: vetor unitário do eixo, no sentido do corpo.
        origem: projeção da âncora sobre o eixo (t = 0 em ``Traste.t``).
        ancora_n: número da âncora: 0 com o nut visível; com o nut fora, o número do
            traste de referência.
        trastes: trastes numerados (número >= 1), na ordem do nut para fora.
        com_nut: se a âncora é o nut visível (senão é o traste de referência).
    """

    id: str
    u: np.ndarray
    origem: np.ndarray
    ancora_n: int
    trastes: tuple[Traste, ...]
    com_nut: bool


@dataclasses.dataclass(frozen=True)
class Previsao:
    """Previsão de um traste (ou resíduo de um ponto do ajuste).

    Attributes:
        numero: número do traste (0 é o nut).
        t_previsto: posição prevista pelo modelo, em px.
        t_medido: posição clicada, em px.
        erro_px: ``|t_previsto - t_medido|``.
        erro_fracao: ``erro_px`` dividido pela largura local da casa.
    """

    numero: int
    t_previsto: float
    t_medido: float
    erro_px: float
    erro_fracao: float


@dataclasses.dataclass
class Analise:
    """Tudo o que a análise produz para um gabarito.

    Attributes:
        registros: respostas do gabarito (``quadros``), por id.
        geometrias: quadros com braço e geometria completa, por id.
        sem_geometria: ids dos quadros que ficaram de fora (braço ``nao``/``?``).
        larguras: largura local da casa (px), por quadro e número de traste.
        previsoes: variante -> quadro -> previsões (só quadros que a variante usou).
        pulados: variante -> ids dos quadros sem a âncora pedida.
        residuos: piso -> quadro -> resíduos de todos os pontos do ajuste.
    """

    registros: dict[str, dict]
    geometrias: dict[str, Geometria]
    sem_geometria: list[str]
    larguras: dict[str, dict[int, float]]
    previsoes: dict[str, dict[str, list[Previsao]]]
    pulados: dict[str, list[str]]
    residuos: dict[str, dict[str, list[Previsao]]]


# ---------------------------------------------------------------------------------
# Modelo físico
# ---------------------------------------------------------------------------------


def s_do_traste(n: int) -> float:
    """Posição física do traste ``n``, como fração do comprimento da escala.

    Args:
        n: número do traste (0 é o nut).

    Returns:
        ``1 - 2 ** (-n / 12)``: 0 no nut e 0,5 no traste 12.
    """
    return 1.0 - 2.0 ** (-n / 12.0)


def ajustar(pontos: list[tuple[int, float]], modelo: str) -> np.ndarray:
    """Ajusta o modelo dos trastes por mínimos quadrados.

    O modelo afim (``t = a*s + b``) é linear em ``(a, b)``. O projetivo
    (``t = (a*s + b) / (c*s + 1)``) vira linear em ``(a, b, c)`` escrevendo
    ``a*s + b - c*s*t = t``. Com 3 pontos independentes o projetivo é exato.

    Args:
        pontos: pares ``(número, t)``; o número 0 é o nut.
        modelo: ``"afim"`` ou ``"proj"``.

    Returns:
        ``[a, b]`` (afim) ou ``[a, b, c]`` (projetivo).

    Raises:
        ValueError: se o modelo for desconhecido.
    """
    s = np.array([s_do_traste(n) for n, _ in pontos], dtype=float)
    t = np.array([valor for _, valor in pontos], dtype=float)
    um = np.ones_like(s)
    if modelo == "afim":
        matriz = np.column_stack([s, um])
    elif modelo == "proj":
        matriz = np.column_stack([s, um, -t * s])
    else:
        raise ValueError(f"modelo desconhecido: {modelo}")
    params, *_ = np.linalg.lstsq(matriz, t, rcond=None)
    return params


def prever(params: np.ndarray, modelo: str, n: int) -> float:
    """Posição prevista do traste ``n`` pelo modelo ajustado.

    Args:
        params: saída de ``ajustar``.
        modelo: ``"afim"`` ou ``"proj"``.
        n: número do traste (0 é o nut).

    Returns:
        ``t`` previsto, em px a partir da âncora.
    """
    s = s_do_traste(n)
    if modelo == "afim":
        return float(params[0] * s + params[1])
    return float((params[0] * s + params[1]) / (params[2] * s + 1.0))


# ---------------------------------------------------------------------------------
# Eixo e geometria do quadro
# ---------------------------------------------------------------------------------


def _unitario(vetor: np.ndarray) -> np.ndarray:
    """Vetor unitário de ``vetor``.

    Args:
        vetor: vetor 2D.

    Returns:
        ``vetor / |vetor|``.

    Raises:
        ValueError: se o vetor for nulo.
    """
    tamanho = float(np.linalg.norm(vetor))
    if tamanho == 0.0:
        raise ValueError("vetor nulo não tem direção")
    return vetor / tamanho


def eixo_do_braco(corda1: list, corda6: list) -> tuple[np.ndarray, np.ndarray]:
    """Eixo do braço: a linha média entre as retas das cordas 1 e 6.

    A direção é a bissetriz das duas cordas (cada uma com o sinal que a alinha à
    outra). A origem é o ponto médio dos pontos médios das duas cordas.

    Args:
        corda1: dois pontos ``[x, y]`` da corda 1.
        corda6: dois pontos ``[x, y]`` da corda 6.

    Returns:
        ``(origem, u)``: um ponto do eixo e o vetor unitário (sentido ainda não
        definido; ``montar_geometria`` o orienta para o corpo).
    """
    c1 = np.asarray(corda1, dtype=float)
    c6 = np.asarray(corda6, dtype=float)
    d1 = _unitario(c1[1] - c1[0])
    d6 = _unitario(c6[1] - c6[0])
    if float(np.dot(d1, d6)) < 0.0:
        d6 = -d6
    u = _unitario(d1 + d6)
    origem = (c1.mean(axis=0) + c6.mean(axis=0)) / 2.0
    return origem, u


def montar_geometria(id_quadro: str, registro: dict) -> Geometria | None:
    """Monta o eixo e os trastes numerados de um quadro do gabarito.

    Entram só quadros com o braço marcado (``sim`` ou ``parcial``) e completos. Com o
    nut visível, a âncora é o nut (número 0). Com o nut fora (q09), a âncora é o
    traste de referência, com o número que o dono deu a ele: a origem do ``t`` fica
    nele e o modelo não tem o nut para fixar o zero, então o projetivo usa o
    traste de referência mais dois trastes.

    O sentido do eixo aponta para o corpo: a média dos trastes fica do lado oposto
    à âncora.

    Args:
        id_quadro: id do quadro (ex.: ``q01``).
        registro: resposta do quadro no gabarito.

    Returns:
        A geometria, ou ``None`` se o quadro não tem braço ou não está completo.
    """
    if registro.get("braco") not in ("sim", "parcial"):
        return None
    if not registro_completo(registro):
        return None
    nut = registro.get("nut")
    com_nut = isinstance(nut, list)
    if com_nut:
        ancora_ponto = np.asarray(nut, dtype=float)
        ancora_n = 0
    else:
        ref = registro["traste_referencia"]
        ancora_ponto = np.asarray(ref["ponto"], dtype=float)
        ancora_n = int(ref["numero"])
    origem0, u = eixo_do_braco(registro["corda1"], registro["corda6"])
    media_trastes = np.asarray(registro["trastes"], dtype=float).mean(axis=0)
    if float(np.dot(media_trastes - ancora_ponto, u)) < 0.0:
        u = -u
    origem = origem0 + float(np.dot(ancora_ponto - origem0, u)) * u
    t_ancora = float(np.dot(ancora_ponto, u))
    trastes = tuple(
        Traste(
            numero=int(item["numero"]),
            t=float(np.dot(np.asarray(item["ponto"], dtype=float), u)) - t_ancora,
            ponto=np.asarray(item["ponto"], dtype=float),
        )
        for item in numerar_trastes(registro)
        if item["numero"] is not None
    )
    return Geometria(
        id=id_quadro,
        u=u,
        origem=origem,
        ancora_n=ancora_n,
        trastes=trastes,
        com_nut=com_nut,
    )


def larguras_locais(geo: Geometria) -> dict[int, float]:
    """Largura local da casa de cada traste, medida entre cliques vizinhos.

    A largura do traste ``n`` é a distância ao traste ``n + 1`` clicado (ou ao
    ``n - 1``, no último traste). É a medida que o erro de previsão divide para virar
    fração da casa.

    Args:
        geo: geometria do quadro.

    Returns:
        Largura em px, por número de traste (o último traste sem vizinho fica de
        fora, mas com dois trastes ou mais sempre há largura).
    """
    ordenados = sorted(geo.trastes, key=lambda tr: tr.numero)
    larguras: dict[int, float] = {}
    for i, tr in enumerate(ordenados):
        if i + 1 < len(ordenados):
            vizinho = ordenados[i + 1]
        elif i > 0:
            vizinho = ordenados[i - 1]
        else:
            continue
        larguras[tr.numero] = abs(vizinho.t - tr.t)
    return larguras


# ---------------------------------------------------------------------------------
# Previsão, pisos e métricas
# ---------------------------------------------------------------------------------


def ajustar_ancoras(
    geo: Geometria, modelo: str, ancoras: tuple[int, ...]
) -> np.ndarray | None:
    """Ajusta o modelo na âncora inicial mais os trastes pedidos.

    Args:
        geo: geometria do quadro.
        modelo: ``"afim"`` ou ``"proj"``.
        ancoras: números dos trastes âncora (ex.: ``(5, 12)``).

    Returns:
        Os parâmetros do ajuste, ou ``None`` se o quadro não tem algum traste pedido.
    """
    por_numero = {tr.numero: tr for tr in geo.trastes}
    if any(n not in por_numero for n in ancoras):
        return None
    pontos = [(geo.ancora_n, 0.0), *((n, por_numero[n].t) for n in ancoras)]
    return ajustar(pontos, modelo)


def prever_quadro(
    geo: Geometria, larguras: dict[int, float], modelo: str, ancoras: tuple[int, ...]
) -> list[Previsao] | None:
    """Prevê os trastes que ficaram de fora do ajuste.

    Args:
        geo: geometria do quadro.
        larguras: largura local por número de traste (``larguras_locais``).
        modelo: ``"afim"`` ou ``"proj"``.
        ancoras: números dos trastes usados no ajuste.

    Returns:
        Uma ``Previsao`` por traste que não é âncora, ou ``None`` se o quadro não
        tem alguma âncora pedida (o chamador conta o quadro como pulado).
    """
    params = ajustar_ancoras(geo, modelo, ancoras)
    if params is None:
        return None
    previsoes: list[Previsao] = []
    for tr in geo.trastes:
        if tr.numero in ancoras or tr.numero == geo.ancora_n:
            continue
        largura = larguras.get(tr.numero)
        if largura is None or largura == 0.0:
            continue
        t_previsto = prever(params, modelo, tr.numero)
        erro = abs(t_previsto - tr.t)
        previsoes.append(
            Previsao(
                numero=tr.numero,
                t_previsto=t_previsto,
                t_medido=tr.t,
                erro_px=erro,
                erro_fracao=erro / largura,
            )
        )
    return previsoes


def residuos_piso(
    geo: Geometria, larguras: dict[int, float], modelo: str
) -> list[Previsao]:
    """Resíduo de cada ponto do ajuste em todos os pontos do quadro.

    É o piso: o erro que sobra mesmo quando o modelo usa tudo o que foi clicado.
    Inclui a âncora (o nut, ou o traste de referência). Não é previsão.

    Args:
        geo: geometria do quadro.
        larguras: largura local por número de traste.
        modelo: ``"afim"`` ou ``"proj"``.

    Returns:
        Um ``Previsao`` por ponto (a âncora com número ``ancora_n``).
    """
    pontos = [
        (geo.ancora_n, 0.0),
        *((tr.numero, tr.t) for tr in geo.trastes if tr.numero != geo.ancora_n),
    ]
    params = ajustar(pontos, modelo)
    residuos: list[Previsao] = []
    for n, t in pontos:
        largura = larguras.get(max(n, 1))
        if largura is None or largura == 0.0:
            continue
        t_previsto = prever(params, modelo, n)
        erro = abs(t_previsto - t)
        residuos.append(
            Previsao(
                numero=n,
                t_previsto=t_previsto,
                t_medido=t,
                erro_px=erro,
                erro_fracao=erro / largura,
            )
        )
    return residuos


def prever_todos(geo: Geometria, modelo: str) -> dict[int, float]:
    """Posição de todos os trastes segundo o ajuste de piso (para desenhar).

    Args:
        geo: geometria do quadro.
        modelo: ``"afim"`` ou ``"proj"``.

    Returns:
        ``t`` previsto por número de traste.
    """
    pontos = [
        (geo.ancora_n, 0.0),
        *((tr.numero, tr.t) for tr in geo.trastes if tr.numero != geo.ancora_n),
    ]
    params = ajustar(pontos, modelo)
    return {tr.numero: prever(params, modelo, tr.numero) for tr in geo.trastes}


def analisar(gabarito: dict) -> Analise:
    """Roda as variantes e os pisos sobre todos os quadros do gabarito.

    Args:
        gabarito: conteúdo de ``data/gold/maos/braco.json``.

    Returns:
        A análise completa, pronta para o relatório e as imagens.
    """
    registros: dict[str, dict] = gabarito["quadros"]
    geometrias: dict[str, Geometria] = {}
    sem_geometria: list[str] = []
    for id_q, registro in registros.items():
        geo = montar_geometria(id_q, registro)
        if geo is None:
            sem_geometria.append(id_q)
        else:
            geometrias[id_q] = geo
    larguras = {id_q: larguras_locais(geo) for id_q, geo in geometrias.items()}

    previsoes: dict[str, dict[str, list[Previsao]]] = {}
    pulados: dict[str, list[str]] = {}
    for nome, (modelo, ancoras) in VARIANTES.items():
        previsoes[nome] = {}
        pulados[nome] = []
        for id_q, geo in geometrias.items():
            lista = prever_quadro(geo, larguras[id_q], modelo, ancoras)
            if lista is None:
                pulados[nome].append(id_q)
            else:
                previsoes[nome][id_q] = lista

    residuos = {
        nome: {
            id_q: residuos_piso(geo, larguras[id_q], modelo)
            for id_q, geo in geometrias.items()
        }
        for nome, modelo in PISOS.items()
    }
    return Analise(
        registros=registros,
        geometrias=geometrias,
        sem_geometria=sem_geometria,
        larguras=larguras,
        previsoes=previsoes,
        pulados=pulados,
        residuos=residuos,
    )


def _estatisticas(valores: list[float]) -> dict[str, float | None]:
    """Mediana, 90o percentil e máximo, arredondados em 3 casas.

    Args:
        valores: amostra (pode ser vazia).

    Returns:
        ``{"mediana", "p90", "max"}``; ``None`` quando a amostra é vazia.
    """
    if not valores:
        return {"mediana": None, "p90": None, "max": None}
    v = np.asarray(valores, dtype=float)
    return {
        "mediana": round(float(np.median(v)), 3),
        "p90": round(float(np.percentile(v, 90)), 3),
        "max": round(float(v.max()), 3),
    }


def _resumo_variante(
    modelo: str,
    ancoras: tuple[int, ...],
    previsoes: dict[str, list[Previsao]],
    pulados: list[str],
) -> dict:
    """Métricas de uma variante sobre todos os trastes previstos.

    Args:
        modelo: ``"afim"`` ou ``"proj"``.
        ancoras: números dos trastes âncora.
        previsoes: quadro -> previsões dos trastes de fora.
        pulados: quadros que não tinham alguma âncora.

    Returns:
        Dicionário com as métricas da variante e o pior traste.
    """
    todas = [(id_q, p) for id_q, lista in previsoes.items() for p in lista]
    frac = [p.erro_fracao for _, p in todas]
    px = [p.erro_px for _, p in todas]
    pior = max(todas, key=lambda par: par[1].erro_fracao, default=None)
    return {
        "modelo": modelo,
        "ancoras": list(ancoras),
        "quadros_usados": len(previsoes),
        "quadros_pulados": pulados,
        "trastes_previstos": len(todas),
        "erro_px": _estatisticas(px),
        "erro_fracao": _estatisticas(frac),
        "fracao_dentro_de_quarto_de_casa": (
            round(float(np.mean(np.asarray(frac) < FRACAO_CASA)), 3) if frac else None
        ),
        "pior_traste": (
            None
            if pior is None
            else {
                "quadro": pior[0],
                "numero": pior[1].numero,
                "erro_fracao": round(pior[1].erro_fracao, 3),
            }
        ),
    }


def _resumo_piso(modelo: str, residuos: dict[str, list[Previsao]]) -> dict:
    """Resíduo do piso sobre todos os pontos de todos os quadros.

    Args:
        modelo: ``"afim"`` ou ``"proj"``.
        residuos: quadro -> resíduos por ponto.

    Returns:
        Dicionário com as estatísticas do resíduo em px e em fração da casa.
    """
    todos = [r for lista in residuos.values() for r in lista]
    frac = [r.erro_fracao for r in todos]
    return {
        "modelo": modelo,
        "quadros": len(residuos),
        "pontos": len(todos),
        "residuo_px": _estatisticas([r.erro_px for r in todos]),
        "residuo_fracao": _estatisticas(frac),
        "fracao_dentro_de_quarto_de_casa": (
            round(float(np.mean(np.asarray(frac) < FRACAO_CASA)), 3) if frac else None
        ),
    }


def _pior_residuo(residuos: list[Previsao]) -> Previsao | None:
    """Ponto com maior resíduo em fração da casa.

    Args:
        residuos: resíduos de um quadro.

    Returns:
        O ponto com maior ``erro_fracao``, ou ``None`` se a lista é vazia.
    """
    return max(residuos, key=lambda r: r.erro_fracao, default=None)


def _linha_quadro(analise: Analise, id_q: str) -> dict:
    """Uma linha da tabela por quadro: âncora, larguras, variantes e piso.

    Args:
        analise: análise completa.
        id_q: id do quadro.

    Returns:
        Dicionário pronto para o JSON.
    """
    registro = analise.registros[id_q]
    chave = str(registro.get("chave") or "")
    canal = chave.split("/")[0] if "/" in chave else chave
    if id_q not in analise.geometrias:
        return {"canal": canal, "braco": registro.get("braco"), "sem_geometria": True}
    geo = analise.geometrias[id_q]
    larguras = list(analise.larguras[id_q].values())
    variantes = {}
    for nome in VARIANTES:
        lista = analise.previsoes[nome].get(id_q)
        variantes[nome] = (
            None
            if lista is None or not lista
            else round(float(np.median([p.erro_fracao for p in lista])), 3)
        )
    pior = _pior_residuo(analise.residuos["proj_todos"].get(id_q, []))
    return {
        "canal": canal,
        "ancora": "nut" if geo.com_nut else f"referencia_n{geo.ancora_n}",
        "trastes_numerados": len(geo.trastes),
        "largura_mediana_px": (
            round(float(np.median(larguras)), 1) if larguras else None
        ),
        "mediana_fracao_por_variante": variantes,
        "piso_proj_todos_max_fracao": None
        if pior is None
        else round(pior.erro_fracao, 3),
        "piso_proj_todos_ponto": None if pior is None else pior.numero,
        "suspeito": bool(pior is not None and pior.erro_fracao > FRACAO_SUSPEITA),
    }


def relatorio(analise: Analise, caminho_gabarito: Path) -> dict:
    """Relatório JSON-pronto da análise.

    Args:
        analise: análise completa.
        caminho_gabarito: arquivo do gabarito lido (para o registro).

    Returns:
        Dicionário com as variantes, os pisos, os suspeitos e a tabela por quadro.
    """
    variantes = {
        nome: _resumo_variante(
            modelo, ancoras, analise.previsoes[nome], analise.pulados[nome]
        )
        for nome, (modelo, ancoras) in VARIANTES.items()
    }
    pisos = {
        nome: _resumo_piso(modelo, analise.residuos[nome])
        for nome, modelo in PISOS.items()
    }
    suspeitos = []
    for id_q, lista in analise.residuos["proj_todos"].items():
        pior = _pior_residuo(lista)
        if pior is not None and pior.erro_fracao > FRACAO_SUSPEITA:
            suspeitos.append(
                {
                    "quadro": id_q,
                    "ponto": pior.numero,
                    "residuo_fracao": round(pior.erro_fracao, 3),
                    "residuo_px": round(pior.erro_px, 2),
                }
            )
    por_quadro = {
        id_q: _linha_quadro(analise, id_q) for id_q in sorted(analise.registros)
    }
    return {
        "formato": FORMATO_RESULTADO,
        "gabarito": str(caminho_gabarito),
        "limiar_suspeita_fracao": FRACAO_SUSPEITA,
        "limiar_casa_fracao": FRACAO_CASA,
        "quadros_com_geometria": len(analise.geometrias),
        "sem_geometria": analise.sem_geometria,
        "variantes": variantes,
        "pisos": pisos,
        "suspeitos": suspeitos,
        "por_quadro": por_quadro,
    }


# ---------------------------------------------------------------------------------
# Imagens de diagnóstico
# ---------------------------------------------------------------------------------


def _segmento_do_traste(
    geo: Geometria, t: float, corda1: np.ndarray, corda6: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Segmento do traste previsto: perpendicular ao eixo, entre as cordas 1 e 6.

    Args:
        geo: geometria do quadro.
        t: posição prevista ao longo do eixo.
        corda1: dois pontos da corda 1.
        corda6: dois pontos da corda 6.

    Returns:
        As duas pontas do segmento no espaço do quadro.
    """
    q = geo.origem + t * geo.u
    v = np.array([-geo.u[1], geo.u[0]])
    extremos = []
    for corda in (corda1, corda6):
        d = _unitario(corda[1] - corda[0])
        matriz = np.column_stack([v, -d])
        lam, _ = np.linalg.solve(matriz, corda[0] - q)
        extremos.append(q + lam * v)
    return extremos[0], extremos[1]


def _caixa_do_braco(
    registro: dict, margem: int, altura: int, largura: int
) -> tuple[int, int, int, int]:
    """Caixa do recorte: todos os cliques do braço mais uma margem.

    Args:
        registro: resposta do quadro.
        margem: margem em px em torno dos cliques.
        altura: altura da imagem.
        largura: largura da imagem.

    Returns:
        ``(x0, y0, x1, y1)`` dentro da imagem.
    """
    pontos = [*registro["corda1"], *registro["corda6"], *registro["trastes"]]
    if isinstance(registro["nut"], list):
        pontos.append(registro["nut"])
    if registro.get("traste_referencia"):
        pontos.append(registro["traste_referencia"]["ponto"])
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    x0 = max(0, int(min(xs)) - margem)
    y0 = max(0, int(min(ys)) - margem)
    x1 = min(largura, int(max(xs)) + margem)
    y1 = min(altura, int(max(ys)) + margem)
    return x0, y0, x1, y1


def desenhar_quadro(
    imagem: np.ndarray,
    geo: Geometria,
    registro: dict,
    camadas: list[tuple[dict[int, float], tuple[int, int, int]]],
    margem: int = 60,
) -> np.ndarray:
    """Recorte do braço com os cliques (verde) e as camadas previstas.

    Args:
        imagem: quadro original (BGR).
        geo: geometria do quadro.
        registro: resposta do quadro no gabarito.
        camadas: pares ``(t previsto por número, cor BGR)``; cada uma vira um
            conjunto de segmentos de traste.
        margem: margem do recorte, em px.

    Returns:
        Imagem recortada e desenhada.
    """
    altura, largura = imagem.shape[:2]
    x0, y0, x1, y1 = _caixa_do_braco(registro, margem, altura, largura)
    recorte = imagem[y0:y1, x0:x1].copy()
    fonte = max(0.5, (x1 - x0) / 900.0)
    espessura = max(1, round(fonte * 2))

    def ponto(p: np.ndarray | list) -> tuple[int, int]:
        return round(float(p[0]) - x0), round(float(p[1]) - y0)

    c1 = np.asarray(registro["corda1"], dtype=float)
    c6 = np.asarray(registro["corda6"], dtype=float)
    cv2.line(recorte, ponto(c1[0]), ponto(c1[1]), COR_CORDA, espessura)
    cv2.line(recorte, ponto(c6[0]), ponto(c6[1]), COR_CORDA, espessura)
    eixo_a = geo.origem - 2000.0 * geo.u
    eixo_b = geo.origem + 2000.0 * geo.u
    cv2.line(recorte, ponto(eixo_a), ponto(eixo_b), COR_EIXO, 1)

    for previstos, cor in camadas:
        for n, t in previstos.items():
            a, b = _segmento_do_traste(geo, t, c1, c6)
            cv2.line(recorte, ponto(a), ponto(b), cor, espessura)
            cv2.putText(
                recorte,
                str(n),
                (ponto(b)[0] + 4, ponto(b)[1] + round(14 * fonte)),
                cv2.FONT_HERSHEY_SIMPLEX,
                fonte * 0.7,
                cor,
                espessura,
            )

    for tr in geo.trastes:
        cv2.circle(recorte, ponto(tr.ponto), max(3, round(4 * fonte)), COR_CLIQUE, -1)
        cv2.putText(
            recorte,
            str(tr.numero),
            (ponto(tr.ponto)[0] - round(10 * fonte), ponto(tr.ponto)[1] - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            fonte * 0.7,
            COR_CLIQUE,
            espessura,
        )
    if isinstance(registro["nut"], list):
        marca = registro["nut"]
    else:
        marca = registro["traste_referencia"]["ponto"]
    cv2.circle(recorte, ponto(marca), max(4, round(5 * fonte)), COR_NUT, -1)
    return recorte


def _camadas_do_quadro(analise: Analise, id_q: str) -> list:
    """Camadas do desenho: previsão da variante da folha e o piso.

    Args:
        analise: análise completa.
        id_q: id do quadro.

    Returns:
        Lista de ``(t por número, cor)``. Vazia se o quadro não tem geometria.
    """
    geo = analise.geometrias[id_q]
    modelo, ancoras = VARIANTES[VARIANTE_DESENHO]
    params = ajustar_ancoras(geo, modelo, ancoras)
    camadas = []
    if params is not None:
        previstos = {tr.numero: prever(params, modelo, tr.numero) for tr in geo.trastes}
        camadas.append((previstos, COR_PREVISAO))
    piso = prever_todos(geo, PISOS["proj_todos"])
    camadas.append((piso, COR_PISO))
    return camadas


def _carregar_quadro(pasta: Path, id_q: str) -> np.ndarray:
    """Lê o quadro original do cache de ``m3b``.

    Args:
        pasta: pasta com ``qNN.png``.
        id_q: id do quadro.

    Returns:
        Imagem BGR.

    Raises:
        FileNotFoundError: se o quadro não existe na pasta.
    """
    imagem = cv2.imread(str(pasta / f"{id_q}.png"))
    if imagem is None:
        raise FileNotFoundError(f"quadro não encontrado: {pasta / f'{id_q}.png'}")
    return imagem


def montar_folha(
    analise: Analise, pasta_quadros: Path, saida: Path, colunas: int = 4
) -> int:
    """Folha com os recortes dos 20 quadros, cliques (verde) e previsão (vermelho).

    Args:
        analise: análise completa.
        pasta_quadros: pasta com os quadros originais (``qNN.png``).
        saida: arquivo JPEG de saída.
        colunas: quantos recortes por linha.

    Returns:
        Quantos recortes entraram na folha.
    """
    largura_tile = 600
    tiles: list[np.ndarray] = []
    ids = sorted(analise.geometrias)
    for id_q in ids:
        imagem = _carregar_quadro(pasta_quadros, id_q)
        recorte = desenhar_quadro(
            imagem,
            analise.geometrias[id_q],
            analise.registros[id_q],
            [(_previstos_da_variante(analise, id_q), COR_PREVISAO)],
        )
        escala = largura_tile / recorte.shape[1]
        tile = cv2.resize(
            recorte,
            (largura_tile, round(recorte.shape[0] * escala)),
            interpolation=cv2.INTER_AREA,
        )
        cv2.putText(
            tile,
            id_q,
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.4,
            (0, 255, 255),
            3,
        )
        tiles.append(tile)

    linhas = []
    for inicio in range(0, len(tiles), colunas):
        linha = tiles[inicio : inicio + colunas]
        altura = max(t.shape[0] for t in linha)
        blocos = []
        for tile in linha:
            bloco = np.full((altura, largura_tile, 3), 30, dtype=np.uint8)
            bloco[: tile.shape[0], : tile.shape[1]] = tile
            blocos.append(bloco)
        while len(blocos) < colunas:
            blocos.append(np.full((altura, largura_tile, 3), 30, dtype=np.uint8))
        separador = np.full((altura, 10, 3), 30, dtype=np.uint8)
        partes: list[np.ndarray] = []
        for bloco in blocos:
            partes.extend([bloco, separador])
        linhas.append(np.hstack(partes[:-1]))
    folha = np.vstack(linhas)
    saida.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(saida), folha, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return len(ids)


def _previstos_da_variante(analise: Analise, id_q: str) -> dict[int, float]:
    """``t`` previsto pela variante de desenho, para todos os trastes do quadro.

    Args:
        analise: análise completa.
        id_q: id do quadro.

    Returns:
        ``t`` previsto por número. Vazio se a variante não cobre o quadro.
    """
    geo = analise.geometrias[id_q]
    modelo, ancoras = VARIANTES[VARIANTE_DESENHO]
    params = ajustar_ancoras(geo, modelo, ancoras)
    if params is None:
        return {}
    return {tr.numero: prever(params, modelo, tr.numero) for tr in geo.trastes}


def gravar_diagnosticos(
    analise: Analise, pasta_quadros: Path, saida: Path
) -> list[str]:
    """Grava a imagem dos quadros suspeitos, do q09 e do pior caso de previsão.

    Args:
        analise: análise completa.
        pasta_quadros: pasta com os quadros originais.
        saida: pasta de destino (``qNN.jpg``).

    Returns:
        Ids dos quadros gravados.
    """
    alvos = {s["quadro"] for s in relatorio_suspeitos(analise)}
    alvos |= {
        id_q for id_q in analise.geometrias if not analise.geometrias[id_q].com_nut
    }
    pior = _pior_residuo(
        [p for lista in analise.previsoes[VARIANTE_DESENHO].values() for p in lista]
    )
    if pior is not None:
        alvos |= {
            id_q
            for id_q, lista in analise.previsoes[VARIANTE_DESENHO].items()
            if pior in lista
        }
    saida.mkdir(parents=True, exist_ok=True)
    for id_q in sorted(alvos):
        imagem = _carregar_quadro(pasta_quadros, id_q)
        recorte = desenhar_quadro(
            imagem,
            analise.geometrias[id_q],
            analise.registros[id_q],
            _camadas_do_quadro(analise, id_q),
            margem=120,
        )
        cv2.imwrite(str(saida / f"{id_q}.jpg"), recorte, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return sorted(alvos)


def relatorio_suspeitos(analise: Analise) -> list[dict]:
    """Quadros com resíduo do piso acima do limiar, do maior para o menor.

    Args:
        analise: análise completa.

    Returns:
        Dicionários com o quadro, o ponto de maior resíduo e o resíduo.
    """
    suspeitos = []
    for id_q, lista in analise.residuos["proj_todos"].items():
        pior = _pior_residuo(lista)
        if pior is not None and pior.erro_fracao > FRACAO_SUSPEITA:
            suspeitos.append(
                {
                    "quadro": id_q,
                    "ponto": pior.numero,
                    "residuo_fracao": pior.erro_fracao,
                }
            )
    return sorted(suspeitos, key=lambda s: -s["residuo_fracao"])


def _imprimir(rel: dict) -> None:
    """Resumo legível no terminal.

    Args:
        rel: relatório de ``relatorio``.
    """
    print(
        f"quadros com geometria: {rel['quadros_com_geometria']}; sem: {rel['sem_geometria']}"
    )
    print(
        "variante          modelo quad  trast  px med  px p90  fr med  fr p90  <0,25  pior"
    )
    for nome, v in rel["variantes"].items():
        ef = v["erro_fracao"]
        ep = v["erro_px"]
        pior = v["pior_traste"]
        pior_txt = (
            "-"
            if pior is None
            else f"{pior['quadro']}/n{pior['numero']}={pior['erro_fracao']}"
        )
        print(
            f"{nome:17s} {v['modelo']:6s} {v['quadros_usados']:4d} {v['trastes_previstos']:6d} "
            f"{ep['mediana']!s:>7} {ep['p90']!s:>7} {ef['mediana']!s:>7} {ef['p90']!s:>7} "
            f"{v['fracao_dentro_de_quarto_de_casa']!s:>6}  {pior_txt}"
        )
        if v["quadros_pulados"]:
            print(f"    pulados: {v['quadros_pulados']}")
    for nome, p in rel["pisos"].items():
        print(
            f"piso {nome}: residuo fr med={p['residuo_fracao']['mediana']} p90={p['residuo_fracao']['p90']} px med={p['residuo_px']['mediana']} <0,25={p['fracao_dentro_de_quarto_de_casa']}"
        )
    print(
        f"suspeitos (proj_todos > {rel['limiar_suspeita_fracao']} casa): {rel['suspeitos']}"
    )


def main() -> int:
    """CLI: roda a análise e grava ``resultado.json``, diagnósticos e a folha.

    Returns:
        0 em sucesso.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gabarito", type=Path, default=GABARITO_BRACO)
    ap.add_argument("--quadros", type=Path, default=PASTA_QUADROS)
    ap.add_argument("--saida", type=Path, default=PASTA_GEOMETRIA)
    args = ap.parse_args()
    gabarito = json.loads(args.gabarito.read_text(encoding="utf-8"))
    analise = analisar(gabarito)
    rel = relatorio(analise, args.gabarito)
    args.saida.mkdir(parents=True, exist_ok=True)
    (args.saida / "resultado.json").write_text(
        json.dumps(rel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    diagnosticos = gravar_diagnosticos(analise, args.quadros, args.saida)
    total = montar_folha(analise, args.quadros, args.saida / "folha.jpg")
    _imprimir(rel)
    print(f"diagnósticos: {diagnosticos}; folha com {total} recortes; {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
