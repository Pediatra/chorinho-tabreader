"""Pré-marcação do braço por consenso de modelos de visão (rodada 1019).

Seis modelos de visão, atrás de um proxy local (formato OpenAI), marcam o braço de cada
quadro da amostra do gabarito. ``coletar`` grava a resposta crua de cada modelo; ``avaliar``
filtra, mede contra o gabarito e calcula o consenso, pelas regras do pré-registro
``docs/rodadas/1019-pre-marcacao-por-consenso-de-vlms.md``. Nenhum critério, limiar,
prompt, semente ou divisão é ajustado depois de medido.

Uso:
    python -m tab.maos_braco_vlm coletar [--quadros q01,q02]
    python -m tab.maos_braco_vlm avaliar
"""

from __future__ import annotations

import argparse
import base64
import collections
import concurrent.futures
import json
import math
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, MAOS_M3B, MAOS_M3B_QUADROS, MAOS_M19
from .maos_braco_regra import eixo_do_braco, prever_trastes
from .maos_braco_tempo import Marcas, classificar, erros, marcas_do_registro

#: Os seis modelos, na ordem da tabela do pré-registro.
MODELOS = (
    "glm-5.3-flash-free",
    "deepseek-v4.1-flash-free",
    "longcat-2.5-preview-free",
    "mimo-v2.6-flash-free",
    "space-bunny-free",
    "nemotron-3.5-super-vl-free",
)
#: Proxy local no formato de chat da OpenAI.
URL_PROXY = "http://127.0.0.1:8787/v1/chat/completions"
#: Semente da divisão desenvolvimento/teste (a mesma data do pré-registro).
SEMENTE = 20261019
#: Largura do quadro enviado ao modelo (a altura segue a proporção).
LARGURA_ENVIO = 1280
QUALIDADE_JPEG = 92
#: Tentativas por pedido (a primeira incluída).
TENTATIVAS = 4
#: Tempo limite de cada pedido, em segundos.
LIMITE_S = 300
#: Esperas antes da 2ª, 3ª e 4ª tentativas, em segundos.
ESPERAS_S = (10, 30, 90)
#: Faixa aceita para a razão (t5 - t_nut) / (t12 - t_nut); no gabarito vai de 0,417 a 0,603.
RAZAO_MIN = 0.35
RAZAO_MAX = 0.70
#: Limiares de dispersão candidatos, escolhidos só no desenvolvimento.
LIMIARES = (0.25, 0.5, 0.75, 1.0, 1.5)
#: Respostas válidas mínimas para formar consenso.
MIN_MODELOS = 3
#: Tamanho do desenvolvimento (o resto é teste).
TAMANHO_DEV = 33
#: Troca de cordas: perpendicular com as cordas trocadas abaixo disto, e normal acima.
LIMITE_TROCA = 0.5
#: Mínimo de aceitos certos, em décimos (9 em 10 = 90 %).
FRACAO_CERTOS = (9, 10)
#: Aceitos mínimos no teste para a cobertura (P3).
MIN_ACEITOS_TESTE = 10

PROMPT = """Você vê um quadro de um vídeo-aula de violão ({largura}x{altura} pixels). Marque o braço do violão.
Coordenadas normalizadas de 0 a 1000: x vai da esquerda (0) para a direita (1000); y vai de cima (0) para baixo (1000).
- braco: "sim" se o braço aparece, "parcial" se aparece só em parte, "nao" se não aparece.
- nut: o centro da pestana (a peça clara entre a cabeça do violão e o primeiro traste), no meio entre as cordas. Se a pestana não aparece, escreva "fora".
- corda1: a corda mais fina (Mi agudo). Dê 2 pontos sobre ela, nas pontas do trecho visível NO BRAÇO (da pestana até onde o braço encontra o corpo), o mais afastados possível. Não vá até o cavalete.
- corda6: a corda mais grossa (Mi grave), com a mesma regra.
- traste5: o ponto no meio do fio de metal do traste 5, contando a partir da pestana (a casa 5 fica entre o traste 4 e o traste 5). null se não aparece.
- traste12: o ponto no meio do fio do traste 12 (logo depois da casa 12, que costuma ter marcação dupla; no violão clássico fica perto de onde o braço encontra o corpo). null se não aparece.
Responda SÓ com JSON, sem nenhum texto antes ou depois:
{{"braco": "sim", "nut": [x, y], "corda1": [[x, y], [x, y]], "corda6": [[x, y], [x, y]], "traste5": [x, y], "traste12": [x, y]}}"""


# ---------------------------------------------------------------------------------
# Arquivos
# ---------------------------------------------------------------------------------


def _carregar(caminho: Path) -> dict:
    """Lê um JSON que tem de existir.

    Args:
        caminho: arquivo JSON.

    Returns:
        O conteúdo, como dicionário.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def _gravar_json(caminho: Path, dados: object) -> None:
    """Grava um JSON legível em UTF-8, criando as pastas.

    Args:
        caminho: arquivo de destino.
        dados: o que gravar.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _caminho_resposta(modelo: str, quadro: str) -> Path:
    """Arquivo da resposta crua de um modelo a um quadro.

    Args:
        modelo: id do modelo no proxy.
        quadro: id do quadro (ex.: ``q01``).

    Returns:
        Caminho em ``MAOS_M19/respostas``.
    """
    return MAOS_M19 / "respostas" / modelo / f"{quadro}.json"


def _ler_resposta(modelo: str, quadro: str) -> dict | None:
    """Lê a resposta gravada, se existir e estiver íntegra.

    Args:
        modelo: id do modelo.
        quadro: id do quadro.

    Returns:
        O registro gravado, ou ``None`` se não há arquivo legível.
    """
    caminho = _caminho_resposta(modelo, quadro)
    if not caminho.exists():
        return None
    try:
        dados = _carregar(caminho)
    except ValueError:
        return None
    return dados if isinstance(dados, dict) else None


def _indice() -> dict[str, dict]:
    """Índice da amostra: canal e tamanho original de cada quadro.

    Returns:
        ``{id: entrada}`` a partir de ``MAOS_M3B/indice.json``.
    """
    entradas = _carregar(MAOS_M3B / "indice.json")["quadros"]
    return {entrada["id"]: entrada for entrada in entradas}


def dividir(ids: list[str]) -> tuple[list[str], list[str]]:
    """Divide os quadros em desenvolvimento e teste, pela semente do pré-registro.

    Args:
        ids: ids dos quadros da amostra (em qualquer ordem).

    Returns:
        ``(dev, teste)``, cada um em ordem alfabética.
    """
    ordenados = sorted(ids)
    dev = set(random.Random(SEMENTE).sample(ordenados, TAMANHO_DEV))
    return (
        [i for i in ordenados if i in dev],
        [i for i in ordenados if i not in dev],
    )


# ---------------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------------


def preparar_envio(caminho: Path) -> tuple[str, int, int]:
    """Reduz o quadro para a largura de envio e codifica em JPEG, em base64.

    Args:
        caminho: PNG do quadro original.

    Returns:
        ``(base64, largura, altura)`` do JPEG enviado.

    Raises:
        FileNotFoundError: se o quadro não pode ser lido.
        ValueError: se a codificação JPEG falhar.
    """
    imagem = cv2.imread(str(caminho))
    if imagem is None:
        raise FileNotFoundError(f"quadro ilegível: {caminho}")
    altura, largura = imagem.shape[:2]
    if largura != LARGURA_ENVIO:
        nova_altura = round(altura * LARGURA_ENVIO / largura)
        imagem = cv2.resize(
            imagem, (LARGURA_ENVIO, nova_altura), interpolation=cv2.INTER_AREA
        )
    ok, buffer = cv2.imencode(
        ".jpg", imagem, [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG]
    )
    if not ok:
        raise ValueError(f"falha ao codificar o quadro: {caminho}")
    altura_envio, largura_envio = imagem.shape[:2]
    return (
        base64.b64encode(buffer.tobytes()).decode("ascii"),
        largura_envio,
        altura_envio,
    )


def _mensagens(ids: list[str]) -> dict[str, list[dict]]:
    """Conteúdo de cada pedido: prompt e imagem, na forma do formato de chat.

    Args:
        ids: ids dos quadros a enviar.

    Returns:
        ``{id: conteúdo}`` para ``messages[0]["content"]``.
    """
    mensagens: dict[str, list[dict]] = {}
    for quadro in ids:
        base64_jpeg, largura, altura = preparar_envio(
            MAOS_M3B_QUADROS / f"{quadro}.png"
        )
        mensagens[quadro] = [
            {"type": "text", "text": PROMPT.format(largura=largura, altura=altura)},
            {
                "type": "image_url",
                "image_url": {"url": "data:image/jpeg;base64," + base64_jpeg},
            },
        ]
    return mensagens


def _chamar_uma_vez(modelo: str, conteudo: list[dict]) -> str:
    """Faz um pedido ao proxy, com ``temperature 0``.

    Args:
        modelo: id do modelo.
        conteudo: conteúdo da mensagem (texto e imagem).

    Returns:
        O texto devolvido pelo modelo.

    Raises:
        OSError: erro de rede, HTTP ou tempo limite (``HTTPError`` e ``URLError`` incluídos).
        ValueError: resposta que não é JSON.
        KeyError: resposta sem ``choices``.
    """
    corpo = json.dumps(
        {
            "model": modelo,
            "temperature": 0,
            "messages": [{"role": "user", "content": conteudo}],
        }
    ).encode("utf-8")
    pedido = urllib.request.Request(
        URL_PROXY,
        data=corpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(pedido, timeout=LIMITE_S) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    return dados["choices"][0]["message"]["content"] or ""


def _eh_transitorio(falha: Exception) -> bool:
    """Se a falha vale nova tentativa (429, 5xx ou tempo limite).

    Args:
        falha: exceção levantada pelo pedido.

    Returns:
        True para 429, para HTTP 5xx e para tempo limite.
    """
    if isinstance(falha, urllib.error.HTTPError):
        return falha.code == 429 or falha.code >= 500
    if isinstance(falha, urllib.error.URLError):
        return isinstance(falha.reason, TimeoutError)
    return isinstance(falha, TimeoutError)


def _descrever(falha: Exception) -> str:
    """Texto curto da falha, para gravar no arquivo da resposta.

    Args:
        falha: exceção do pedido.

    Returns:
        ``HTTP <código>`` ou ``<tipo>: <mensagem>``.
    """
    if isinstance(falha, urllib.error.HTTPError):
        return f"HTTP {falha.code}"
    return f"{type(falha).__name__}: {falha}"


def pedir(modelo: str, quadro: str, conteudo: list[dict]) -> dict:
    """Pede a marcação de um quadro a um modelo, com novas tentativas.

    Args:
        modelo: id do modelo.
        quadro: id do quadro.
        conteudo: conteúdo da mensagem.

    Returns:
        O registro da resposta: ``modelo``, ``quadro``, ``conteudo``, ``segundos``,
        ``tentativas`` e ``erro`` (``None`` quando respondeu).
    """
    inicio = time.monotonic()
    texto = ""
    erro: str | None = None
    tentativas = 0
    for tentativas in range(1, TENTATIVAS + 1):
        try:
            texto = _chamar_uma_vez(modelo, conteudo)
            erro = None
            break
        except (OSError, ValueError, KeyError, IndexError, TypeError) as falha:
            erro = _descrever(falha)
            if not _eh_transitorio(falha) or tentativas == TENTATIVAS:
                break
            time.sleep(ESPERAS_S[tentativas - 1])
    return {
        "modelo": modelo,
        "quadro": quadro,
        "conteudo": texto,
        "segundos": round(time.monotonic() - inicio, 1),
        "tentativas": tentativas,
        "erro": erro,
    }


def _coletar_modelo(modelo: str, mensagens: dict[str, list[dict]]) -> dict:
    """Coleta todos os quadros de um modelo, em ordem; pula o que já tem resposta.

    Args:
        modelo: id do modelo.
        mensagens: ``{id: conteúdo}`` de todos os quadros.

    Returns:
        Contagens: ``ok`` (respondeu nesta execução), ``pulados`` (já havia resposta) e
        ``falhas`` (erro definitivo nesta execução).
    """
    contagem = {"ok": 0, "pulados": 0, "falhas": 0}
    total = len(mensagens)
    for feitos, (quadro, conteudo) in enumerate(mensagens.items(), start=1):
        caminho = _caminho_resposta(modelo, quadro)
        existente = _ler_resposta(modelo, quadro)
        if existente is not None and existente.get("erro") is None:
            contagem["pulados"] += 1
        else:
            registro = pedir(modelo, quadro, conteudo)
            _gravar_json(caminho, registro)
            if registro["erro"] is None:
                contagem["ok"] += 1
            else:
                contagem["falhas"] += 1
        if feitos % 10 == 0 or feitos == total:
            print(
                f"{modelo}: {feitos}/{total} (ok {contagem['ok']}, "
                f"pulados {contagem['pulados']}, falhas {contagem['falhas']})",
                flush=True,
            )
    return contagem


def coletar(quadros: list[str] | None = None) -> int:
    """Coleta as respostas dos 6 modelos para os quadros do gabarito.

    Um worker por modelo; dentro de cada modelo, os quadros em ordem.

    Args:
        quadros: ids a coletar; ``None`` para os 66 do gabarito.

    Returns:
        Código de saída (0).
    """
    ids = sorted(_carregar(GABARITO_BRACO)["quadros"]) if quadros is None else quadros
    mensagens = _mensagens(ids)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(MODELOS)) as pool:
        futuros = {
            modelo: pool.submit(_coletar_modelo, modelo, mensagens)
            for modelo in MODELOS
        }
        for modelo, futuro in futuros.items():
            resumo = futuro.result()
            print(f"{modelo}: fim {resumo}", flush=True)
    return 0


# ---------------------------------------------------------------------------------
# Interpretação da resposta
# ---------------------------------------------------------------------------------


def interpretar(conteudo: str) -> dict | None:
    """Extrai o objeto JSON de uma resposta, tirando cercas e texto em volta.

    Args:
        conteudo: texto cru devolvido pelo modelo.

    Returns:
        O dicionário, ou ``None`` se não há um objeto JSON válido.
    """
    texto = conteudo.replace("```json", "").replace("```", "")
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio < 0 or fim < inicio:
        return None
    try:
        dados = json.loads(texto[inicio : fim + 1])
    except ValueError:
        return None
    return dados if isinstance(dados, dict) else None


def _ponto(valor: object) -> tuple[float, float] | None:
    """Um ponto ``[x, y]`` com números finitos, ou ``None``.

    Args:
        valor: o campo lido do JSON.

    Returns:
        ``(x, y)`` em floats, ou ``None`` se o valor não é um ponto válido.
    """
    if not isinstance(valor, list) or len(valor) != 2:
        return None
    if any(isinstance(v, bool) or not isinstance(v, int | float) for v in valor):
        return None
    x, y = float(valor[0]), float(valor[1])
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return x, y


def _corda(valor: object) -> list[tuple[float, float]] | None:
    """Dois pontos de uma corda, ou ``None``.

    Args:
        valor: o campo ``corda1`` ou ``corda6`` lido do JSON.

    Returns:
        Lista com os 2 pontos, ou ``None``.
    """
    if not isinstance(valor, list) or len(valor) != 2:
        return None
    pontos = [_ponto(p) for p in valor]
    if any(p is None for p in pontos):
        return None
    return pontos  # type: ignore[return-value]


def _orientacao(p: list[float], q: list[float], r: list[float]) -> float:
    """Sinal da área do triângulo ``p, q, r``.

    Args:
        p: primeiro vértice.
        q: segundo vértice.
        r: terceiro vértice.

    Returns:
        Positivo, negativo ou zero, conforme a orientação.
    """
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _cruzam(a1: list[float], a2: list[float], b1: list[float], b2: list[float]) -> bool:
    """Se o segmento ``a1-a2`` cruza ``b1-b2`` entre as pontas.

    Args:
        a1: ponta do primeiro segmento.
        a2: outra ponta do primeiro segmento.
        b1: ponta do segundo segmento.
        b2: outra ponta do segundo segmento.

    Returns:
        True se os segmentos se cruzam em um ponto interno a ambos.
    """
    d1 = _orientacao(b1, b2, a1)
    d2 = _orientacao(b1, b2, a2)
    d3 = _orientacao(a1, a2, b1)
    d4 = _orientacao(a1, a2, b2)
    return d1 * d2 < 0 and d3 * d4 < 0


def _razao(
    nut: list[float],
    corda1: list[list[float]],
    corda6: list[list[float]],
    t5: list[float],
    t12: list[float],
) -> float:
    """Razão ``(t5 - t_nut) / (t12 - t_nut)`` ao longo do eixo do braço.

    O eixo vem de ``tab.maos_braco_regra.eixo_do_braco`` e é orientado do nut para o
    traste 12. Se o denominador é zero, devolve NaN (que fica fora da faixa).

    Args:
        nut: ponto da pestana, em pixels.
        corda1: dois pontos da corda 1, em pixels.
        corda6: dois pontos da corda 6, em pixels.
        t5: ponto do traste 5, em pixels.
        t12: ponto do traste 12, em pixels.

    Returns:
        A razão, em float.
    """
    origem, u = eixo_do_braco(corda1, corda6)
    p_nut = np.asarray(nut, dtype=float)
    if float(np.dot(np.asarray(t12, dtype=float) - p_nut, u)) < 0.0:
        u = -u
    t_nut = float(np.dot(p_nut - origem, u))
    t_5 = float(np.dot(np.asarray(t5, dtype=float) - origem, u))
    t_12 = float(np.dot(np.asarray(t12, dtype=float) - origem, u))
    denominador = t_12 - t_nut
    if denominador == 0.0:
        return float("nan")
    return (t_5 - t_nut) / denominador


def analisar(
    conteudo: str, largura: int, altura: int
) -> tuple[dict | None, str | None]:
    """Aplica o filtro do pré-registro a uma resposta crua.

    A ordem dos testes segue o pré-registro: JSON, pontos faltando, nut ``fora``, pontos
    fora da imagem, cordas que se cruzam, recusa de ``prever_trastes`` e faixa da razão.
    As coordenadas de 0 a 1000 viram pixels do quadro original.

    Args:
        conteudo: texto cru do modelo.
        largura: largura do quadro original, em pixels.
        altura: altura do quadro original, em pixels.

    Returns:
        ``(resultado, None)`` para resposta válida, com ``nut``, ``corda1``, ``corda6``,
        ``t5``, ``t12`` (pixels) e ``previsto`` (``{traste: ponto}``); ou ``(None, motivo)``.
    """
    dados = interpretar(conteudo)
    if dados is None:
        return None, "json_invalido"
    c1 = _corda(dados.get("corda1"))
    c6 = _corda(dados.get("corda6"))
    t5 = _ponto(dados.get("traste5"))
    t12 = _ponto(dados.get("traste12"))
    if c1 is None or c6 is None or t5 is None or t12 is None:
        return None, "falta_ponto"
    nut_bruto = dados.get("nut")
    if nut_bruto == "fora":
        return None, "nut_fora"
    nut = _ponto(nut_bruto)
    if nut is None:
        return None, "falta_ponto"

    def em_pixels(p: tuple[float, float]) -> list[float]:
        return [p[0] * largura / 1000.0, p[1] * altura / 1000.0]

    nut_px = em_pixels(nut)
    t5_px = em_pixels(t5)
    t12_px = em_pixels(t12)
    c1_px = [em_pixels(p) for p in c1]
    c6_px = [em_pixels(p) for p in c6]
    todos = [nut_px, t5_px, t12_px, *c1_px, *c6_px]
    if any(not (0.0 <= x <= largura and 0.0 <= y <= altura) for x, y in todos):
        return None, "fora_da_imagem"
    if _cruzam(c1_px[0], c1_px[1], c6_px[0], c6_px[1]):
        return None, "cordas_se_cruzam"
    try:
        previsto = prever_trastes(
            nut_px, c1_px, c6_px, {5: t5_px, 12: t12_px}, (largura, altura)
        )
    except (ValueError, ArithmeticError, np.linalg.LinAlgError) as erro:
        return None, f"prever_recusou: {erro}"
    razao = _razao(nut_px, c1_px, c6_px, t5_px, t12_px)
    if not RAZAO_MIN <= razao <= RAZAO_MAX:
        return None, "razao_fora"
    return {
        "nut": nut_px,
        "corda1": c1_px,
        "corda6": c6_px,
        "t5": t5_px,
        "t12": t12_px,
        "previsto": previsto,
    }, None


def orientar(analise: dict) -> dict:
    """Ordena as cordas de uma resposta válida: o ponto mais perto do nut vem primeiro.

    Args:
        analise: resultado de ``analisar``.

    Returns:
        Mesmos campos, com arrays numpy e cada corda ordenada a partir do nut.
    """
    nut = np.asarray(analise["nut"], dtype=float)
    return {
        "nut": nut,
        "c1": _proximo_do_nut_primeiro(nut, analise["corda1"]),
        "c6": _proximo_do_nut_primeiro(nut, analise["corda6"]),
        "t5": np.asarray(analise["t5"], dtype=float),
        "t12": np.asarray(analise["t12"], dtype=float),
        "previsto": analise["previsto"],
    }


def _proximo_do_nut_primeiro(nut: np.ndarray, par: list[list[float]]) -> np.ndarray:
    """Ordena os 2 pontos de uma corda pela distância ao nut.

    Args:
        nut: ponto da pestana.
        par: dois pontos da corda.

    Returns:
        Array ``(2, 2)`` com o ponto mais perto do nut primeiro.
    """
    a = np.asarray(par[0], dtype=float)
    b = np.asarray(par[1], dtype=float)
    if np.linalg.norm(b - nut) < np.linalg.norm(a - nut):
        a, b = b, a
    return np.array([a, b])


# ---------------------------------------------------------------------------------
# Medida contra o gabarito
# ---------------------------------------------------------------------------------


def _lista(valor: object) -> list:
    """Converte um array ou lista em lista de floats (para ``prever_trastes``).

    Args:
        valor: array, lista ou tupla.

    Returns:
        Lista aninhada de floats.
    """
    return np.asarray(valor, dtype=float).tolist()


def marcas_previstas(
    nut: object, corda1: object, corda6: object, previsto: dict[int, list[float]]
) -> Marcas | None:
    """Monta as marcas de uma previsão no formato do gabarito, para medir.

    Os trastes entram como uma sequência contígua a partir do 1, na ordem do nut.

    Args:
        nut: ponto da pestana.
        corda1: dois pontos da corda 1.
        corda6: dois pontos da corda 6.
        previsto: saída de ``prever_trastes``.

    Returns:
        As marcas, ou ``None`` se o registro não fica completo.
    """
    sequencia: list[list[float]] = []
    numero = 1
    while numero in previsto:
        sequencia.append([float(v) for v in previsto[numero]])
        numero += 1
    registro = {
        "braco": "sim",
        "nut": _lista(nut),
        "corda1": _lista(corda1),
        "corda6": _lista(corda6),
        "trastes": sequencia,
        "traste_referencia": None,
    }
    return marcas_do_registro(registro)


def medir(previsto: Marcas, alvo: Marcas) -> dict | None:
    """Classe e troca de cordas de uma previsão, contra o gabarito.

    Args:
        previsto: marcas previstas.
        alvo: marcas do gabarito do mesmo quadro.

    Returns:
        ``{"classe", "trocou", "erros"}``, ou ``None`` se a medida não se calcula.
    """
    try:
        medida = erros(previsto, alvo)
        trocada = Marcas(
            nut=previsto.nut,
            trastes=previsto.trastes,
            corda1=previsto.corda6,
            corda6=previsto.corda1,
        )
        medida_troca = erros(trocada, alvo)
    except ValueError:
        return None
    trocou = (
        medida_troca["perp_cordas"] < LIMITE_TROCA
        and medida["perp_cordas"] > LIMITE_TROCA
    )
    return {
        "classe": classificar(medida, achou=True, braco_alvo="sim"),
        "trocou": bool(trocou),
        "erros": medida,
    }


def _descarte(motivo: str) -> dict:
    """Resultado de uma resposta descartada pelo filtro.

    Args:
        motivo: razão do descarte.

    Returns:
        Registro com classe ``nao_achou``.
    """
    return {"motivo": motivo, "classe": "nao_achou", "trocou": False, "analise": None}


def _avaliar_resposta(
    resposta: dict | None, largura: int, altura: int, alvo: Marcas
) -> dict:
    """Filtra e mede a resposta de um modelo a um quadro.

    Args:
        resposta: registro gravado pela coleta, ou ``None``.
        largura: largura original do quadro.
        altura: altura original do quadro.
        alvo: marcas do gabarito do quadro.

    Returns:
        ``motivo`` (``None`` se válida), ``classe``, ``trocou`` e ``analise`` (orientada,
        ou ``None``).
    """
    if resposta is None:
        return _descarte("sem_resposta")
    if resposta.get("erro"):
        return _descarte("erro_proxy")
    analise, motivo = analisar(resposta.get("conteudo") or "", largura, altura)
    if analise is None:
        return _descarte(motivo or "json_invalido")
    marcas = marcas_previstas(
        analise["nut"], analise["corda1"], analise["corda6"], analise["previsto"]
    )
    if marcas is None:
        return _descarte("marcas_incompletas")
    medida = medir(marcas, alvo)
    if medida is None:
        return _descarte("erro_medida")
    return {
        "motivo": None,
        "classe": medida["classe"],
        "trocou": medida["trocou"],
        "analise": orientar(analise),
    }


# ---------------------------------------------------------------------------------
# Consenso
# ---------------------------------------------------------------------------------


def _distancia_a_reta(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Distância perpendicular de um ponto à reta que passa por ``a`` e ``b``.

    Args:
        p: ponto.
        a: primeiro ponto da reta.
        b: segundo ponto da reta.

    Returns:
        Distância em pixels (sem sinal).
    """
    d = b - a
    cruz = d[0] * (p[1] - a[1]) - d[1] * (p[0] - a[0])
    return float(abs(cruz) / np.linalg.norm(d))


def consenso(validas: list[dict]) -> dict:
    """Ponto de consenso: a mediana, coordenada a coordenada, dos 7 pontos.

    Args:
        validas: respostas válidas e orientadas (de ``orientar``).

    Returns:
        ``{"nut", "c1", "c6", "t5", "t12"}`` com arrays numpy.
    """
    pontos = np.array(
        [[v["nut"], *v["c1"], *v["c6"], v["t5"], v["t12"]] for v in validas],
        dtype=float,
    )
    mediana = np.median(pontos, axis=0)
    return {
        "nut": mediana[0],
        "c1": mediana[1:3],
        "c6": mediana[3:5],
        "t5": mediana[5],
        "t12": mediana[6],
    }


def _vao(cons: dict) -> float:
    """Vão do consenso: distância entre as cordas 1 e 6, dividida por 5.

    Args:
        cons: ponto de consenso.

    Returns:
        Vão em pixels, ou infinito se as cordas coincidem.
    """
    meio1 = cons["c1"].mean(axis=0)
    meio6 = cons["c6"].mean(axis=0)
    dist = (
        _distancia_a_reta(meio1, cons["c6"][0], cons["c6"][1])
        + _distancia_a_reta(meio6, cons["c1"][0], cons["c1"][1])
    ) / 2.0
    vao = dist / 5.0
    return vao if vao > 0.0 else float("inf")


def dispersoes(validas: list[dict], cons: dict) -> list[float]:
    """Dispersão de cada modelo em relação ao consenso, em vãos.

    Para o nut e os trastes 5 e 12 é a distância euclidiana ao consenso. Para as cordas é a
    maior distância perpendicular dos 2 pontos do modelo à reta de consenso da mesma corda.
    Toma-se o máximo e divide-se pelo vão.

    Args:
        validas: respostas válidas e orientadas.
        cons: ponto de consenso.

    Returns:
        Uma dispersão por modelo, na mesma ordem de ``validas``.
    """
    vao = _vao(cons)
    saida = []
    for v in validas:
        distancias = [
            float(np.linalg.norm(v["nut"] - cons["nut"])),
            float(np.linalg.norm(v["t5"] - cons["t5"])),
            float(np.linalg.norm(v["t12"] - cons["t12"])),
        ]
        distancias += [
            _distancia_a_reta(p, cons["c1"][0], cons["c1"][1]) for p in v["c1"]
        ]
        distancias += [
            _distancia_a_reta(p, cons["c6"][0], cons["c6"][1]) for p in v["c6"]
        ]
        saida.append(max(distancias) / vao)
    return saida


def classe_consenso(
    cons: dict, largura: int, altura: int, alvo: Marcas
) -> tuple[str | None, str | None]:
    """Classe do consenso contra o gabarito, ou o motivo da recusa.

    Args:
        cons: ponto de consenso.
        largura: largura original do quadro.
        altura: altura original do quadro.
        alvo: marcas do gabarito do quadro.

    Returns:
        ``(classe, None)``, ou ``(None, motivo)`` se ``prever_trastes`` recusa o consenso.
    """
    nut = _lista(cons["nut"])
    try:
        previsto = prever_trastes(
            nut,
            _lista(cons["c1"]),
            _lista(cons["c6"]),
            {5: _lista(cons["t5"]), 12: _lista(cons["t12"])},
            (largura, altura),
        )
    except (ValueError, ArithmeticError, np.linalg.LinAlgError) as erro:
        return None, f"consenso_recusado: {erro}"
    marcas = marcas_previstas(nut, cons["c1"], cons["c6"], previsto)
    if marcas is None:
        return None, "consenso_incompleto"
    medida = medir(marcas, alvo)
    if medida is None:
        return None, "erro_medida"
    return medida["classe"], None


# ---------------------------------------------------------------------------------
# Escolha do limiar e aceite
# ---------------------------------------------------------------------------------


def _aceito(quadro: dict, limiar: float) -> bool:
    """Se o quadro é aceito com o limiar: consenso formado e dispersão dentro do limiar.

    Args:
        quadro: registro do quadro na avaliação.
        limiar: valor de L.

    Returns:
        True se o consenso existe e a dispersão é menor ou igual a ``limiar``.
    """
    return (
        quadro["consenso"] is not None
        and quadro["dispersao"] is not None
        and quadro["dispersao"] <= limiar
    )


def estatisticas(ids: list[str], quadros: dict[str, dict], limiar: float) -> dict:
    """Aceitos e suas classes para um limiar, dentro de um conjunto de quadros.

    Args:
        ids: quadros do conjunto.
        quadros: registro de cada quadro.
        limiar: valor de L.

    Returns:
        ``{"n", "aceitos", "certo", "impreciso", "falso"}``.
    """
    saida = {"n": len(ids), "aceitos": 0, "certo": 0, "impreciso": 0, "falso": 0}
    for i in ids:
        quadro = quadros[i]
        if _aceito(quadro, limiar):
            saida["aceitos"] += 1
            saida[quadro["consenso"]] += 1
    return saida


def _certos_suficientes(stats: dict) -> bool:
    """Se há aceitos e os certos são pelo menos 90 % deles.

    Args:
        stats: resultado de ``estatisticas``.

    Returns:
        True se ``aceitos >= 1`` e ``certo / aceitos >= 0,9``.
    """
    numerador, denominador = FRACAO_CERTOS
    return (
        stats["aceitos"] > 0
        and stats["certo"] * denominador >= numerador * stats["aceitos"]
    )


def escolher_limiar(busca_dev: dict[float, dict]) -> float | None:
    """Maior L com 0 falsos e certos >= 90 % dos aceitos, no desenvolvimento.

    Args:
        busca_dev: ``{L: estatisticas}`` medidas no desenvolvimento.

    Returns:
        O maior L que passa, ou ``None`` se nenhum passa.
    """
    escolhido = None
    for limiar in LIMIARES:
        stats = busca_dev[limiar]
        if stats["falso"] == 0 and _certos_suficientes(stats):
            escolhido = limiar
    return escolhido


# ---------------------------------------------------------------------------------
# Avaliação
# ---------------------------------------------------------------------------------


def _resumo_modelo(quadros: dict[str, dict], modelo: str, ids: list[str]) -> dict:
    """Contagens de um modelo no conjunto de quadros.

    Args:
        quadros: registro de cada quadro.
        modelo: id do modelo.
        ids: quadros do conjunto.

    Returns:
        ``{"n", "certo", "impreciso", "falso", "nao_achou", "trocas"}``.
    """
    saida = {"n": len(ids), "certo": 0, "impreciso": 0, "falso": 0, "nao_achou": 0}
    saida["trocas"] = 0
    for i in ids:
        registro = quadros[i]["modelos"][modelo]
        saida[registro["classe"]] += 1
        if registro["trocou"]:
            saida["trocas"] += 1
    return saida


def _linha(rotulo: str, valores: list[object]) -> str:
    """Uma linha de tabela alinhada por espaços.

    Args:
        rotulo: primeira coluna.
        valores: demais colunas.

    Returns:
        Texto da linha.
    """
    return f"{rotulo:<28}" + " ".join(f"{v!s:>10}" for v in valores)


def _imprimir_modelos(
    quadros: dict[str, dict], dev: list[str], teste: list[str]
) -> None:
    """Tabela por modelo: 66 quadros, desenvolvimento e teste.

    Args:
        quadros: registro de cada quadro.
        dev: quadros de desenvolvimento.
        teste: quadros de teste.
    """
    ids = sorted(quadros)
    cabecalho = ["n", "certo", "impreciso", "falso", "nao_achou", "trocas"]
    print("\n== Por modelo ==")
    print(_linha("modelo / recorte", cabecalho))
    for modelo in MODELOS:
        for rotulo, conjunto in (("66", ids), ("dev", dev), ("teste", teste)):
            r = _resumo_modelo(quadros, modelo, conjunto)
            valores = [r[c] for c in cabecalho]
            print(_linha(f"{modelo} {rotulo}", valores))


def _imprimir_motivos(quadros: dict[str, dict]) -> dict[str, int]:
    """Motivos de descarte, contados em todos os modelos e quadros.

    Args:
        quadros: registro de cada quadro.

    Returns:
        ``{motivo: contagem}``, em ordem decrescente.
    """
    contagem: collections.Counter[str] = collections.Counter()
    for quadro in quadros.values():
        for registro in quadro["modelos"].values():
            if registro["motivo"] is not None:
                contagem[registro["motivo"].split(":")[0]] += 1
    print("\n== Motivos de descarte (todos os modelos, 66 quadros) ==")
    for motivo, n in contagem.most_common():
        print(f"  {motivo}: {n}")
    return dict(contagem.most_common())


def _imprimir_busca(busca: dict[float, dict], escolhido: float | None) -> None:
    """Tabela de busca do L, no desenvolvimento.

    Args:
        busca: ``{L: estatisticas}`` do desenvolvimento.
        escolhido: L escolhido, ou ``None``.
    """
    print("\n== Busca de L (desenvolvimento) ==")
    print(_linha("L", ["aceitos", "certo", "impreciso", "falso", "passa"]))
    for limiar in LIMIARES:
        s = busca[limiar]
        passa = s["falso"] == 0 and _certos_suficientes(s)
        print(
            _linha(
                f"{limiar}",
                [
                    s["aceitos"],
                    s["certo"],
                    s["impreciso"],
                    s["falso"],
                    "sim" if passa else "não",
                ],
            )
        )
    print(f"L escolhido: {escolhido if escolhido is not None else 'nenhum'}")


def _imprimir_teste(teste_stats: dict, limiar: float) -> dict:
    """Critérios P1, P2 e P3 no teste, com o L congelado.

    Args:
        teste_stats: ``estatisticas`` do teste com o L escolhido.
        limiar: L escolhido.

    Returns:
        Dicionário com os resultados e os critérios.
    """
    cobertura = teste_stats["aceitos"] / teste_stats["n"]
    p1 = teste_stats["falso"] == 0
    p2 = _certos_suficientes(teste_stats)
    p3 = teste_stats["aceitos"] >= MIN_ACEITOS_TESTE
    print(f"\n== Teste (L = {limiar}) ==")
    print(
        f"aceitos {teste_stats['aceitos']}/{teste_stats['n']} "
        f"(cobertura {cobertura:.1%}); certo {teste_stats['certo']}, "
        f"impreciso {teste_stats['impreciso']}, falso {teste_stats['falso']}"
    )
    print(f"P1 (0 falsos): {'PASSA' if p1 else 'NÃO PASSA'}")
    print(f"P2 (certos >= 90% dos aceitos): {'PASSA' if p2 else 'NÃO PASSA'}")
    print(f"P3 (aceitos >= 10 de 33): {'PASSA' if p3 else 'NÃO PASSA'}")
    return {
        "stats": teste_stats,
        "cobertura": cobertura,
        "P1": p1,
        "P2": p2,
        "P3": p3,
    }


def _imprimir_p4(
    quadros: dict[str, dict], ids_teste: list[str], limiar: float | None
) -> dict:
    """P4: tabela por modelo e por canal (com denominador), e por canal no consenso.

    Args:
        quadros: registro de cada quadro.
        ids_teste: quadros de teste.
        limiar: L escolhido, ou ``None``; sem L não há tabela de consenso.

    Returns:
        ``{"modelos": ..., "consenso": ...}``.
    """
    canais = sorted({quadros[i]["canal"] for i in quadros})
    print("\n== P4: por canal (certos/n, todos os 66 quadros) ==")
    cabecalho = [m.split("-")[0] for m in MODELOS]
    print(_linha("canal", [f"{c}" for c in cabecalho]))
    por_modelo: dict[str, dict] = {}
    for canal in canais:
        ids_canal = [i for i in quadros if quadros[i]["canal"] == canal]
        celulas = []
        for modelo in MODELOS:
            certos = sum(
                1
                for i in ids_canal
                if quadros[i]["modelos"][modelo]["classe"] == "certo"
            )
            celulas.append(f"{certos}/{len(ids_canal)}")
            por_modelo.setdefault(canal, {})[modelo] = [certos, len(ids_canal)]
        print(_linha(canal, celulas))
    por_consenso: dict[str, dict] = {}
    if limiar is not None:
        print(f"\n== P4: consenso por canal (teste, L = {limiar}) ==")
        print(_linha("canal", ["n", "aceitos", "certo", "impreciso", "falso"]))
        for canal in canais:
            ids_canal = [i for i in ids_teste if quadros[i]["canal"] == canal]
            s = estatisticas(ids_canal, quadros, limiar)
            por_consenso[canal] = s
            print(
                _linha(
                    canal,
                    [s["n"], s["aceitos"], s["certo"], s["impreciso"], s["falso"]],
                )
            )
    return {"modelos": por_modelo, "consenso": por_consenso}


def avaliar() -> int:
    """Avalia as respostas gravadas: filtro, medida, consenso, limiar e teste.

    Grava ``MAOS_M19/resultado.json`` e imprime as tabelas.

    Returns:
        Código de saída (0).
    """
    gabarito = _carregar(GABARITO_BRACO)["quadros"]
    ids = sorted(gabarito)
    indice = _indice()
    dev, teste = dividir(ids)
    alvos = {i: marcas_do_registro(gabarito[i]) for i in ids}
    quadros: dict[str, dict] = {
        i: {"canal": indice[i]["canal"], "modelos": {}} for i in ids
    }
    validas_por_quadro: dict[str, list[dict]] = {i: [] for i in ids}
    for modelo in MODELOS:
        for i in ids:
            resultado = _avaliar_resposta(
                _ler_resposta(modelo, i),
                indice[i]["largura"],
                indice[i]["altura"],
                alvos[i],
            )
            quadros[i]["modelos"][modelo] = {
                "motivo": resultado["motivo"],
                "classe": resultado["classe"],
                "trocou": resultado["trocou"],
            }
            if resultado["analise"] is not None:
                validas_por_quadro[i].append(resultado["analise"])

    for i in ids:
        rec = quadros[i]
        validas = validas_por_quadro[i]
        rec["validas"] = len(validas)
        rec["dispersao"] = None
        rec["consenso"] = None
        rec["motivo_consenso"] = "menos_de_3"
        if len(validas) < MIN_MODELOS:
            continue
        cons = consenso(validas)
        rec["dispersao"] = float(np.median(dispersoes(validas, cons)))
        rec["consenso"], rec["motivo_consenso"] = classe_consenso(
            cons, indice[i]["largura"], indice[i]["altura"], alvos[i]
        )

    busca_dev = {L: estatisticas(dev, quadros, L) for L in LIMIARES}
    escolhido = escolher_limiar(busca_dev)

    print(f"Desenvolvimento: {len(dev)} quadros; teste: {len(teste)} quadros.")
    _imprimir_modelos(quadros, dev, teste)
    motivos = _imprimir_motivos(quadros)
    _imprimir_busca(busca_dev, escolhido)

    saida: dict[str, object] = {
        "semente": SEMENTE,
        "dev": dev,
        "teste": teste,
        "motivos": motivos,
        "busca_dev": {str(L): busca_dev[L] for L in LIMIARES},
        "limiar_escolhido": escolhido,
        "quadros": quadros,
    }
    if escolhido is None:
        saida["veredito"] = "reprovado no desenvolvimento"
        print("\nReprovado no desenvolvimento: o teste não foi calculado.")
    else:
        teste_stats = estatisticas(teste, quadros, escolhido)
        saida["veredito"] = "teste medido"
        saida["teste"] = _imprimir_teste(teste_stats, escolhido)
    saida["p4"] = _imprimir_p4(quadros, teste, escolhido)
    _gravar_json(MAOS_M19 / "resultado.json", saida)
    print(f"\nGravado: {MAOS_M19 / 'resultado.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI: ``coletar`` ou ``avaliar``.

    Args:
        argv: argumentos da linha de comando; ``None`` usa ``sys.argv``.

    Returns:
        Código de saída.
    """
    parser = argparse.ArgumentParser(description="Pré-marcação do braço (rodada 1019).")
    sub = parser.add_subparsers(dest="comando", required=True)
    coleta = sub.add_parser("coletar", help="pede a marcação aos 6 modelos")
    coleta.add_argument(
        "--quadros",
        help="ids separados por vírgula (ex.: q01,q02); padrão: os 66 do gabarito",
    )
    sub.add_parser("avaliar", help="filtra, mede, faz o consenso e grava o resultado")
    args = parser.parse_args(argv)
    if args.comando == "coletar":
        quadros = args.quadros.split(",") if args.quadros else None
        return coletar(quadros)
    return avaliar()


if __name__ == "__main__":
    sys.exit(main())
