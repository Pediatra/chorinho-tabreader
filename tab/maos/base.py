"""Rodada 1049: a base das mãos (``chorinho/maos@1``) de um vídeo, de ponta a ponta.

Junta o que já existe, sem calcular entrada pelo gabarito (princípio 1 do plano):

- **denso** (``.maos.npz``): os quadros nativos mais próximos de uma grade de ``QPS`` nas
  exibições do produto (com ``FOLGA_S`` de cada lado); as mãos do ``DetectorMaos`` (M1) em
  todos; o braço pela cadeia da 1047 (22 hipóteses, validadores, sem tomada) em 1 quadro a
  cada ``PASSO_BRACO``; a caixa da tablatura pelo painel da tela do produto;
- **eventos** (``.maos.json``): uma nota do produto cada, com o ``t_audio`` da trilha do
  áudio e as checagens K1–K4 do pré-registro.

Pré-registro: ``docs/rodadas/1049-base-das-maos-no-video-do-mvp.md``.

Este módulo é a parte pura (sem GPU); a parte que lê o vídeo e roda os detectores é o
``tab.maos.base_gpu``.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path

import numpy as np

from tab.maos.esquema import MATRIZES, nivel_esperado

#: Grade de amostragem (quadros por segundo) e o braço a cada quantos quadros dela.
QPS = 10.0
PASSO_BRACO = 10
#: Folga em volta de cada exibição, em segundos.
FOLGA_S = 1.0
#: Meia janela do evento em torno de ``t_som`` (plano, seção 3).
MEIA_JANELA_S = 0.5
#: Distância máxima entre ``t_som`` e o quadro de braço usado na K2.
BRACO_MAX_S = 0.5
#: Folga além do traste ``casa``, em fração da casa (K2).
FOLGA_CASA = 0.25
#: Distância máxima da ponta à reta da corda, em vãos entre cordas (K2).
VAOS_CORDA = 1.0
#: Fração mínima da janela com a mão do ataque (K3).
PRESENCA_ATAQUE = 0.5
#: Sem a mão por mais que isto, a trilha seguinte é outra.
LACUNA_TRILHA_S = 0.5
#: Corte de cena entre quadros seguidos (a ``LIMIAR_CORTE`` da 1009-b).
LIMIAR_CORTE = 0.30
#: Pontas do indicador ao mínimo nos 21 pontos da mão.
PONTAS = (8, 12, 16, 20)
#: Capotraste confirmado pelo dono, por canal (vazio até a confirmação).
CAPO_DONO: dict[str, int] = {}
#: Código da origem da mão no denso.
ORIGEM = {"wholebody": 1, "mediapipe": 2}
#: Índice da mão no denso: 0 = a do braço (esquerda do destro), 1 = a do ataque.
LADOS = ("esquerda", "direita")
#: Trastes guardados no denso (0 = nut).
N_TRASTES = 25


def sha256(caminho: Path) -> str:
    """O sha256 de um arquivo.

    Args:
        caminho: arquivo.

    Returns:
        64 caracteres hexadecimais.
    """
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def intervalos(produto: dict, duracao: float) -> list[tuple[float, float]]:
    """As exibições do produto com ``FOLGA_S`` de cada lado, fundidas e ordenadas.

    Args:
        produto: ``chorinho/video@1``.
        duracao: duração do vídeo, em segundos.

    Returns:
        ``[(t0, t1)]`` sem sobreposição.
    """
    brutos = sorted(
        (max(0.0, ex["t0"] - FOLGA_S), min(duracao, ex["t1"] + FOLGA_S))
        for tela in produto["telas"]
        for ex in tela.get("exibicoes", [])
    )
    fundidos: list[list[float]] = []
    for t0, t1 in brutos:
        if fundidos and t0 <= fundidos[-1][1]:
            fundidos[-1][1] = max(fundidos[-1][1], t1)
        else:
            fundidos.append([t0, t1])
    return [(a, b) for a, b in fundidos]


def caixa_em(produto: dict, t: float) -> list[float] | None:
    """O painel da tela exibida em ``t``.

    Args:
        produto: ``chorinho/video@1``.
        t: instante, em segundos.

    Returns:
        ``[x0, y0, x1, y1]``, ou None fora das exibições.
    """
    for tela in produto["telas"]:
        for ex in tela.get("exibicoes", []):
            if ex["t0"] <= t <= ex["t1"] and tela.get("painel"):
                return [float(v) for v in tela["painel"]]
    return None


def melhor_mao(maos: list[dict], lado: str) -> dict | None:
    """A mão de um lado com o maior score (Wholebody antes do MediaPipe no empate).

    Args:
        maos: saída de ``combinar``.
        lado: ``esquerda`` ou ``direita``.

    Returns:
        A mão, ou None.
    """
    candidatas = [m for m in maos if m["lado"] == lado]
    if not candidatas:
        return None
    return max(
        candidatas,
        key=lambda m: (_score_da_mao(m), m["origem"] == "wholebody"),
    )


def _score_da_mao(mao: dict) -> float:
    """O score de uma mão: a média do Wholebody, ou o score do MediaPipe.

    Args:
        mao: saída de ``combinar``.

    Returns:
        O score (0 se não há).
    """
    if mao.get("media") is not None:
        return float(mao["media"])
    return float(mao.get("score_mao") or 0.0)


def pontos_da_mao(mao: dict) -> np.ndarray:
    """Os 21 pontos de uma mão com o score de cada um.

    Args:
        mao: saída de ``combinar``.

    Returns:
        ``(21, 3)``: x, y e score (o do MediaPipe é o da mão inteira).
    """
    pts = np.asarray(mao["pts"], dtype=np.float64)[:, :2]
    if mao.get("scores") is not None:
        scores = np.asarray(mao["scores"], dtype=np.float64)
    else:
        scores = np.full(len(pts), _score_da_mao(mao))
    return np.column_stack([pts, np.clip(scores, 0.0, 1.0)])


def dentro_do_quadro(xy: np.ndarray, largura: int, altura: int) -> bool:
    """Se todos os pontos estão no quadro, com a folga do esquema (5 %).

    Args:
        xy: ``(..., 2)``.
        largura: largura do quadro.
        altura: altura do quadro.

    Returns:
        True se nenhum ponto sai.
    """
    xy = np.asarray(xy, dtype=np.float64).reshape(-1, 2)
    fx, fy = 0.05 * largura, 0.05 * altura
    return bool(
        np.all(
            (xy[:, 0] >= -fx)
            & (xy[:, 0] <= largura + fx)
            & (xy[:, 1] >= -fy)
            & (xy[:, 1] <= altura + fy)
        )
    )


def corpo_da_maior(pessoas: list[dict]) -> np.ndarray:
    """Ombros, cotovelos e pulsos da pessoa de maior caixa.

    Args:
        pessoas: ``pessoas_wb`` do detector.

    Returns:
        ``(6, 3)``, NaN sem pessoa.
    """
    if not pessoas:
        return np.full((6, 3), np.nan)
    maior = max(
        pessoas,
        key=lambda p: (p["caixa"][2] - p["caixa"][0]) * (p["caixa"][3] - p["caixa"][1]),
    )
    return np.asarray(maior["corpo"], dtype=np.float64)


def trilhas(presente: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """O id de trilha de cada mão: o mesmo lado seguido, nova trilha após uma lacuna.

    Args:
        presente: ``(N, 2)`` bool.
        pts: ``(N,)`` PTS em segundos.

    Returns:
        ``(N, 2)`` int16, −1 onde a mão está ausente.
    """
    saida = np.full(presente.shape, -1, dtype=np.int16)
    proximo = 0
    for lado in range(presente.shape[1]):
        atual, ultimo = -1, -math.inf
        for i in range(len(pts)):
            if not presente[i, lado]:
                continue
            if atual < 0 or pts[i] - ultimo > LACUNA_TRILHA_S:
                atual, proximo = proximo, proximo + 1
            saida[i, lado] = atual
            ultimo = pts[i]
    return saida


def recortar_reta(
    a: np.ndarray, b: np.ndarray, largura: int, altura: int
) -> np.ndarray | None:
    """O trecho da reta por ``a`` e ``b`` dentro do quadro (a mesma reta, pontos dentro).

    Args:
        a: ponto ``(2,)``.
        b: ponto ``(2,)``.
        largura: largura do quadro.
        altura: altura do quadro.

    Returns:
        ``(2, 2)``, ou None se a reta não cruza o quadro.
    """
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    d = b - a
    t0, t1 = -math.inf, math.inf
    for p, q in (
        (-d[0], a[0]),
        (d[0], largura - 1 - a[0]),
        (-d[1], a[1]),
        (d[1], altura - 1 - a[1]),
    ):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
    if t0 > t1 or not math.isfinite(t0) or not math.isfinite(t1):
        return None
    return np.array([a + d * t0, a + d * t1])


def braco_do_previsto(
    previsto: dict, largura: int, altura: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, bool, float]:
    """O braço de um quadro no formato do denso.

    Args:
        previsto: entrada de ``previsto.json`` da cadeia.
        largura: largura do quadro.
        altura: altura do quadro.

    Returns:
        ``(trastes (25, 2), corda1 (2, 2), corda6 (2, 2), achou, conf)``; ``conf`` é 1
        se entregue, 0 se sinalizado, NaN se não achou. Trastes fora do quadro ficam NaN;
        as cordas são a mesma reta, recortada ao quadro.
    """
    trastes = np.full((N_TRASTES, 2), np.nan)
    cordas = [np.full((2, 2), np.nan), np.full((2, 2), np.nan)]
    if not previsto.get("achou"):
        return trastes, cordas[0], cordas[1], False, math.nan
    pontos = [(0, previsto["nut"])] + [
        (t["numero"], t["ponto"]) for t in previsto.get("trastes") or []
    ]
    for numero, ponto in pontos:
        if ponto is None or not 0 <= numero < N_TRASTES:
            continue
        if dentro_do_quadro(np.asarray(ponto), largura, altura):
            trastes[numero] = ponto
    for i, nome in enumerate(("corda1", "corda6")):
        reta = recortar_reta(*previsto[nome], largura, altura)
        if reta is not None:
            cordas[i] = reta
    conf = 0.0 if previsto.get("sinalizado") else 1.0
    return trastes, cordas[0], cordas[1], True, conf


def distancia_na_celula(
    trastes: np.ndarray,
    corda1: np.ndarray,
    corda6: np.ndarray,
    corda: int,
    casa: int,
    ponto: np.ndarray,
) -> float:
    """Distância de uma ponta à célula (corda, casa), em vãos entre cordas.

    Ao longo do braço, a ponta precisa estar entre o traste ``casa − 1`` e o traste
    ``casa`` + ``FOLGA_CASA`` de casa; fora disso, a distância é infinita. Na direção das
    cordas, a distância é a da ponta à reta da corda, em vãos.

    Args:
        trastes: ``(25, 2)`` do denso (0 = nut).
        corda1: reta da corda 1 ``(2, 2)``.
        corda6: reta da corda 6 ``(2, 2)``.
        corda: 1 a 6.
        casa: ≥ 1.
        ponto: ponta ``(2,)``.

    Returns:
        A distância em vãos, ou ``inf``.
    """
    if casa >= N_TRASTES or not (
        np.all(np.isfinite(trastes[casa - 1])) and np.all(np.isfinite(trastes[casa]))
    ):
        return math.inf
    if not (np.all(np.isfinite(corda1)) and np.all(np.isfinite(corda6))):
        return math.inf
    a, b = trastes[casa - 1], trastes[casa]
    eixo = b - a
    comprimento = float(np.linalg.norm(eixo))
    if comprimento == 0:
        return math.inf
    s = float((ponto - a) @ eixo) / comprimento**2
    if not 0.0 <= s <= 1.0 + FOLGA_CASA:
        return math.inf
    f = (corda - 1) / 5.0
    p0 = corda1[0] + (corda6[0] - corda1[0]) * f
    p1 = corda1[1] + (corda6[1] - corda1[1]) * f
    return _distancia_a_reta(ponto, p0, p1) / max(_vao(corda1, corda6, ponto), 1e-6)


def _distancia_a_reta(ponto: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Distância de um ponto à reta por ``a`` e ``b``.

    Args:
        ponto: ``(2,)``.
        a: ``(2,)``.
        b: ``(2,)``.

    Returns:
        A distância em pixels.
    """
    d = b - a
    norma = float(np.linalg.norm(d))
    if norma == 0:
        return float(np.linalg.norm(ponto - a))
    return abs(float(d[0] * (ponto[1] - a[1]) - d[1] * (ponto[0] - a[0]))) / norma


def _vao(corda1: np.ndarray, corda6: np.ndarray, ponto: np.ndarray) -> float:
    """O vão entre cordas perto de um ponto: a distância entre as cordas 1 e 6 / 5.

    Args:
        corda1: ``(2, 2)``.
        corda6: ``(2, 2)``.
        ponto: ``(2,)``.

    Returns:
        O vão em pixels.
    """
    d = corda1[1] - corda1[0]
    norma = float(np.linalg.norm(d))
    t = float((ponto - corda1[0]) @ d) / norma**2 if norma else 0.0
    pe = corda1[0] + d * t
    return _distancia_a_reta(pe, corda6[0], corda6[1]) / 5.0


def janela(pts: np.ndarray, t_som: float | None) -> tuple[int, int] | None:
    """Os índices do denso com PTS em ``[t_som − MEIA_JANELA_S, t_som + MEIA_JANELA_S]``.

    Args:
        pts: ``(N,)``.
        t_som: instante do som, ou None.

    Returns:
        ``(i0, i1)`` com ``i0 < i1``, ou None.
    """
    if t_som is None:
        return None
    i0 = int(np.searchsorted(pts, t_som - MEIA_JANELA_S, side="left"))
    i1 = int(np.searchsorted(pts, t_som + MEIA_JANELA_S, side="right"))
    return (i0, i1) if i0 < i1 else None


def checar_k2(
    denso: dict, jan: tuple[int, int], t_som: float, corda: int, casa: int
) -> dict:
    """K2: alguma ponta da mão do braço na célula (corda, casa) na janela.

    Args:
        denso: as matrizes do denso.
        jan: ``(i0, i1)``.
        t_som: instante do som.
        corda: 1 a 6.
        casa: casa da tablatura.

    Returns:
        ``{"passou", "valor"}``; ``passou`` None para corda solta ou sem braço entregue a
        ≤ ``BRACO_MAX_S``.
    """
    if casa == 0:
        return {"passou": None, "valor": None}
    entregues = np.flatnonzero(denso["braco_achou"] & (denso["braco_conf"] == 1.0))
    if len(entregues) == 0:
        return {"passou": None, "valor": None}
    j = int(entregues[np.argmin(np.abs(denso["pts"][entregues] - t_som))])
    if abs(float(denso["pts"][j]) - t_som) > BRACO_MAX_S:
        return {"passou": None, "valor": None}
    melhor = math.inf
    for i in range(*jan):
        mao = denso["maos"][i, 0]
        if not np.all(np.isfinite(mao[:, :2])):
            continue
        for ponta in PONTAS:
            melhor = min(
                melhor,
                distancia_na_celula(
                    denso["braco_trastes"][j],
                    denso["braco_corda1"][j],
                    denso["braco_corda6"][j],
                    corda,
                    casa,
                    mao[ponta, :2],
                ),
            )
    valor = None if math.isinf(melhor) else round(melhor, 4)
    return {"passou": bool(melhor <= VAOS_CORDA), "valor": valor}


def checar_k3(denso: dict, jan: tuple[int, int]) -> dict:
    """K3: a mão do ataque em pelo menos ``PRESENCA_ATAQUE`` da janela.

    Args:
        denso: as matrizes do denso.
        jan: ``(i0, i1)``.

    Returns:
        ``{"passou", "valor"}``.
    """
    presente = denso["maos_origem"][jan[0] : jan[1], 1] > 0
    fracao = float(presente.mean())
    return {"passou": bool(fracao >= PRESENCA_ATAQUE), "valor": round(fracao, 4)}


def checar_k4(
    denso: dict, cortes_pares: np.ndarray, jan: tuple[int, int], t_som: float, capo
) -> dict:
    """K4: sem corte de cena na janela, caixa da tablatura em ``t_som`` e capo conhecido.

    Args:
        denso: as matrizes do denso.
        cortes_pares: ``(N,)`` distância de Bhattacharyya ao quadro anterior (0 no
            primeiro de cada intervalo).
        jan: ``(i0, i1)``.
        t_som: instante do som.
        capo: casa do capotraste, ou None.

    Returns:
        ``{"passou", "valor"}``; valor = a maior distância entre quadros da janela.
    """
    dist = cortes_pares[jan[0] + 1 : jan[1]]
    maior = float(dist.max()) if len(dist) else 0.0
    i = int(np.argmin(np.abs(denso["pts"] - t_som)))
    caixa = bool(np.all(np.isfinite(denso["tab_caixa"][i])))
    passou = maior <= LIMIAR_CORTE and caixa and capo is not None
    return {"passou": bool(passou), "valor": round(maior, 4)}


def _motivo(checagens: dict, t_som: float | None) -> str:
    """O motivo de um evento recusado.

    Args:
        checagens: K1–K4.
        t_som: instante do som.

    Returns:
        O primeiro motivo, em ordem K1, K4, K3.
    """
    if t_som is None:
        return "sem t_audio"
    if checagens["K1"]["passou"] is not True:
        return "K1"
    if checagens["K4"]["passou"] is not True:
        return "K4"
    return "K3"


def som_por_coluna(notas: list[dict], audio: dict) -> dict[tuple, tuple]:
    """O ``t_audio`` de cada coluna, na passagem cujo ``t_ini`` fica mais perto dele.

    A trilha do áudio dá tempo a uma passagem só por coluna (``passagens: so_primeira``,
    a primeira no tempo); a numeração de ``passagem`` do produto não segue o tempo.

    Args:
        notas: notas do produto.
        audio: ``chorinho/audio@1``.

    Returns:
        ``{(tela, exibicao, coluna, passagem): (t_audio, confianca)}``.
    """
    passagens: dict[tuple, dict] = {}
    for nota in notas:
        chave = (nota["tela"], nota["exibicao"], nota["coluna"])
        passagens.setdefault(chave, {})[nota.get("passagem")] = nota.get("t_ini")
    saida = {}
    for coluna in audio["colunas"]:
        chave = (coluna["tela"], coluna["exibicao"], coluna["coluna"])
        if coluna["t_audio"] is None or chave not in passagens:
            continue
        opcoes = passagens[chave]
        if len(opcoes) == 1:
            escolhida = next(iter(opcoes))
        else:
            com_tempo = {p: t for p, t in opcoes.items() if t is not None}
            if not com_tempo:
                continue
            escolhida = min(
                com_tempo, key=lambda p: abs(com_tempo[p] - coluna["t_audio"])
            )
        saida[(*chave, escolhida)] = (coluna["t_audio"], coluna.get("confianca"))
    return saida


def eventos(
    produto: dict, audio: dict, denso: dict, cortes_pares: np.ndarray, capo
) -> list[dict]:
    """Os eventos: uma nota do produto cada, com ``t_som``, janela e K1–K4.

    Args:
        produto: ``chorinho/video@1``.
        audio: ``chorinho/audio@1``.
        denso: as matrizes do denso.
        cortes_pares: distância ao quadro anterior, por quadro.
        capo: casa do capotraste, ou None.

    Returns:
        A lista de eventos do ``chorinho/maos@1``.
    """
    saida = []
    som = som_por_coluna(produto["notas"], audio)
    for nota in produto["notas"]:
        t_som, confianca = som.get(
            (nota["tela"], nota["exibicao"], nota["coluna"], nota.get("passagem")),
            (None, None),
        )
        jan = janela(denso["pts"], t_som)
        k1 = {
            "passou": t_som is not None,
            "valor": None if confianca is None else round(float(confianca), 4),
        }
        if jan is None:
            vazio = {"passou": False, "valor": None}
            checagens = {"K1": k1, "K2": dict(vazio), "K3": dict(vazio), "K4": vazio}
        else:
            checagens = {
                "K1": k1,
                "K2": checar_k2(denso, jan, t_som, nota["corda"], nota["casa"]),
                "K3": checar_k3(denso, jan),
                "K4": checar_k4(denso, cortes_pares, jan, t_som, capo),
            }
        nivel = nivel_esperado(checagens)
        saida.append(
            {
                "tela": nota["tela"],
                "passagem": nota.get("passagem"),
                "exibicao": nota.get("exibicao"),
                "coluna": nota["coluna"],
                "corda": nota["corda"],
                "t_ini": nota.get("t_ini"),
                "casa": nota["casa"],
                "t_som": None if t_som is None else round(float(t_som), 4),
                "janela": None if jan is None else list(jan),
                "checagens": checagens,
                "nivel": nivel,
                "motivo": _motivo(checagens, t_som) if nivel == "recusado" else None,
            }
        )
    return saida


def resumo(evs: list[dict]) -> dict:
    """As contagens dos eventos por nível e os motivos dos recusados.

    Args:
        evs: eventos.

    Returns:
        O ``resumo`` do ``chorinho/maos@1``.
    """
    niveis = Counter(e["nivel"] for e in evs)
    return {
        "eventos": len(evs),
        "ouro": niveis["ouro"],
        "prata": niveis["prata"],
        "recusado": niveis["recusado"],
        "motivos": dict(Counter(e["motivo"] for e in evs if e["nivel"] == "recusado")),
    }


def vazio(n: int) -> dict[str, np.ndarray]:
    """As matrizes do denso com N quadros, vazias (NaN, ausente, sem braço).

    Args:
        n: número de quadros.

    Returns:
        ``{nome: matriz}`` nas formas do esquema.
    """
    saida = {}
    for nome, (forma, tipo) in MATRIZES.items():
        if tipo is np.bool_ or np.issubdtype(tipo, np.integer):
            saida[nome] = np.zeros((n, *forma), dtype=tipo)
        else:
            saida[nome] = np.full((n, *forma), np.nan, dtype=tipo)
    return saida
