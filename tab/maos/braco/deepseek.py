"""DeepSeek direto na API: o recorte do braço resolve as cordas? (rodada 1020).

Quatro experimentos sobre os 33 quadros de desenvolvimento da 1019 (os 33 de teste
ficam lacrados e não são pedidos nem medidos). ``e0`` é uma sonda sintética de
espaçamento entre cordas. ``e1`` e ``e2`` mandam o quadro inteiro, com o raciocínio
desligado e ligado. ``e3`` faz duas etapas: a caixa do braço no quadro inteiro e, depois,
o recorte ampliado com o mesmo JSON da 1019. ``avaliar`` aplica o filtro e a medida da
1019 e grava ``m20/resultado.json``.

A chave vem de ``DEEPSEEK_API_KEY`` ou de ``/run/secrets/deepseek`` (montada só para
leitura no container). Ela nunca é impressa nem gravada.

Uso:
    python -m tab.maos_braco_deepseek e0
    python -m tab.maos_braco_deepseek {e1,e2} [--quadros q01,q02] [--limite N]
    python -m tab.maos_braco_deepseek e3 [--quadros q01,q02] [--limite N] [--pensar on]
    python -m tab.maos_braco_deepseek avaliar
"""

from __future__ import annotations

import argparse
import base64
import collections
import concurrent.futures
import functools
import http.client
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from tab.comum.caminhos import GABARITO_BRACO, MAOS_M3B_QUADROS, MAOS_M20
from tab.maos.braco.tempo import Marcas, marcas_do_registro
from tab.maos.braco.vlm import (
    LIMITE_TROCA,
    PROMPT,
    QUALIDADE_JPEG,
    SEMENTE,
    _carregar,
    _corda,
    _distancia_a_reta,
    _gravar_json,
    _indice,
    _ponto,
    analisar,
    dividir,
    interpretar,
    marcas_previstas,
    medir,
    preparar_envio,
)

#: Modelo, endereço e chave da API direta da DeepSeek.
MODELO = "deepseek-flash"
URL_API = "https://api.deepseek.com/chat/completions"
CHAVE_CONTAINER = Path("/run/secrets/deepseek")
VARIAVEL_CHAVE = "DEEPSEEK_API_KEY"
#: Preço em US$ por milhão de tokens (entrada e saída), fora do pico.
PRECO_ENTRADA = 0.15
PRECO_SAIDA = 0.60
#: Pedidos em paralelo; tentativas por pedido (a primeira incluída) e esperas entre elas.
PARALELOS = 4
TENTATIVAS = 3
ESPERAS_S = (10, 30)
#: Tempo limite de cada pedido, em segundos.
LIMITE_S = 300
#: Recorte ampliado do E3: largura máxima e lado maior máximo, em pixels.
LARGURA_RECORTE = 1280
LADO_RECORTE = 1300
#: Margem de cada lado da caixa do braço, como fração da caixa (E3).
MARGEM_RECORTE = 0.10
#: Sonda sintética do E0: 6 linhas paralelas, inclinadas, sobre fundo marrom.
ESPACAMENTOS = (8, 14, 20, 30)
INCLINACOES = (0.0, 12.0)
N_LINHAS = 6
LARGURA_E0 = 1280
ALTURA_E0 = 720
COMPRIMENTO_E0 = 900
FATOR_SUPER = 4
COR_FUNDO_E0 = (40, 70, 110)
COR_LINHA_E0 = (230, 230, 230)
#: Quadros do E0: ``{id: (espaçamento, inclinação)}``.
QUADROS_E0 = {
    f"s{espacamento:02d}_a{int(inclinacao):02d}": (espacamento, inclinacao)
    for espacamento in ESPACAMENTOS
    for inclinacao in INCLINACOES
}
#: Experimentos, na ordem da CLI.
EXPERIMENTOS = ("e0", "e1", "e2", "e3")
#: Texto que abre a 2ª etapa do E3, antes do PROMPT da 1019.
PREFIXO_E3 = "Esta imagem é um recorte ampliado do braço.\n"

PROMPT_CAIXA = """Você vê um quadro de um vídeo-aula de violão ({largura}x{altura} pixels). Marque a caixa que contém o braço inteiro do violão: da pestana (ou da cabeça) até onde o braço encontra o corpo.
Coordenadas normalizadas de 0 a 1000: x vai da esquerda (0) para a direita (1000); y vai de cima (0) para baixo (1000).
Responda SÓ com JSON, sem nenhum texto antes ou depois:
{{"caixa": [x0, y0, x1, y1]}}"""

PROMPT_E0 = """Esta imagem tem 6 linhas claras e paralelas sobre um fundo marrom. A linha 1 é a mais fina e a linha 6 é a mais grossa.
Coordenadas normalizadas de 0 a 1000: x vai da esquerda (0) para a direita (1000); y vai de cima (0) para baixo (1000).
Dê as duas pontas da linha 1 e as duas pontas da linha 6.
Responda SÓ com JSON, sem nenhum texto antes ou depois:
{{"linha1": [[x, y], [x, y]], "linha6": [[x, y], [x, y]]}}"""


class ChaveAusente(RuntimeError):
    """A chave da DeepSeek não está no ambiente nem no arquivo montado."""


# ---------------------------------------------------------------------------------
# Chave e pedido à API
# ---------------------------------------------------------------------------------


def ler_chave(caminho: Path | None = None) -> str:
    """Lê a chave: ``DEEPSEEK_API_KEY`` se existir, senão o arquivo montado.

    A mensagem de erro cita o caminho, nunca o conteúdo da chave.

    Args:
        caminho: arquivo com a chave; ``None`` para ``/run/secrets/deepseek``.

    Returns:
        A chave, sem espaços em volta.

    Raises:
        ChaveAusente: se não há chave no ambiente nem no arquivo.
    """
    do_ambiente = os.environ.get(VARIAVEL_CHAVE, "").strip()
    if do_ambiente:
        return do_ambiente
    arquivo = CHAVE_CONTAINER if caminho is None else caminho
    try:
        chave = arquivo.read_text(encoding="utf-8").strip()
    except OSError as erro:
        raise ChaveAusente(
            f"chave da DeepSeek ausente: não lida de {arquivo}"
        ) from erro
    if not chave:
        raise ChaveAusente(f"chave da DeepSeek vazia em {arquivo}")
    return chave


def corpo_pedido(conteudo: list[dict], pensar: bool) -> dict:
    """Corpo do pedido no formato de chat, com ``temperature 0``.

    Args:
        conteudo: partes da mensagem do usuário (texto e imagem).
        pensar: se o raciocínio fica ligado.

    Returns:
        O dicionário que vira o JSON do pedido.
    """
    return {
        "model": MODELO,
        "temperature": 0,
        "messages": [{"role": "user", "content": conteudo}],
        "thinking": {"type": "enabled" if pensar else "disabled"},
    }


def bloco_imagem(base64_jpeg: str) -> dict:
    """Parte de imagem do pedido, em JPEG base64 com ``detail`` alto.

    Args:
        base64_jpeg: JPEG codificado em base64.

    Returns:
        O bloco ``image_url`` do formato de chat.
    """
    return {
        "type": "image_url",
        "image_url": {
            "url": "data:image/jpeg;base64," + base64_jpeg,
            "detail": "high",
        },
    }


def codificar_jpeg(imagem: np.ndarray) -> str:
    """Codifica uma imagem em JPEG (qualidade da 1019) e devolve em base64.

    Args:
        imagem: matriz BGR.

    Returns:
        O JPEG em base64, como texto.

    Raises:
        ValueError: se a codificação falhar.
    """
    ok, buffer = cv2.imencode(
        ".jpg", imagem, [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG]
    )
    if not ok:
        raise ValueError("falha ao codificar o JPEG")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


def montar_requisicao(corpo: dict, chave: str) -> urllib.request.Request:
    """Monta o POST para a API, com o cabeçalho ``Authorization``.

    Args:
        corpo: corpo do pedido (ver ``corpo_pedido``).
        chave: chave da DeepSeek.

    Returns:
        A requisição, pronta para ``urlopen``.
    """
    return urllib.request.Request(
        URL_API,
        data=json.dumps(corpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {chave}",
        },
        method="POST",
    )


def _chamar(corpo: dict, chave: str) -> dict:
    """Faz um pedido à API e devolve o JSON da resposta.

    Args:
        corpo: corpo do pedido.
        chave: chave da DeepSeek.

    Returns:
        O objeto JSON da resposta.

    Raises:
        OSError: erro de rede, HTTP ou tempo limite.
        ValueError: resposta que não é JSON.
    """
    with urllib.request.urlopen(
        montar_requisicao(corpo, chave), timeout=LIMITE_S
    ) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("resposta que não é um objeto JSON")
    return dados


def _extrair(dados: dict) -> tuple[str, str | None, dict | None]:
    """Texto, raciocínio (se vier) e uso de uma resposta da API.

    Args:
        dados: objeto JSON da resposta.

    Returns:
        ``(conteudo, reasoning_content, usage)``.

    Raises:
        KeyError: resposta sem ``choices``.
        IndexError: ``choices`` vazio.
        TypeError: mensagem que não é um objeto.
    """
    mensagem = dados["choices"][0]["message"]
    texto = mensagem.get("content") or ""
    return texto, mensagem.get("reasoning_content"), dados.get("usage")


def _eh_transitorio(falha: Exception) -> bool:
    """Se a falha vale nova tentativa.

    Vale para 429, 5xx, tempo limite, conexão recusada ou resetada. Outro 4xx é final.

    Args:
        falha: exceção levantada pelo pedido.

    Returns:
        True se a falha é transitória.
    """
    if isinstance(falha, urllib.error.HTTPError):
        return falha.code == 429 or falha.code >= 500
    return isinstance(
        falha,
        urllib.error.URLError
        | TimeoutError
        | ConnectionError
        | http.client.RemoteDisconnected,
    )


def _descrever(falha: Exception) -> str:
    """Texto curto da falha, para gravar no registro.

    Args:
        falha: exceção do pedido.

    Returns:
        ``HTTP <código>`` ou ``<tipo>: <mensagem>``.
    """
    if isinstance(falha, urllib.error.HTTPError):
        return f"HTTP {falha.code}"
    return f"{type(falha).__name__}: {falha}"


def pedir(corpo: dict, chave: str) -> dict:
    """Pede a resposta à API, com até 2 tentativas extras para falhas transitórias.

    Args:
        corpo: corpo do pedido.
        chave: chave da DeepSeek.

    Returns:
        ``conteudo``, ``raciocinio``, ``segundos``, ``tentativas``, ``erro`` (``None``
        quando respondeu) e ``uso``. A chave não entra no resultado.
    """
    inicio = time.monotonic()
    texto, raciocinio, uso = "", None, None
    erro: str | None = None
    tentativas = 0
    for tentativas in range(1, TENTATIVAS + 1):
        try:
            texto, raciocinio, uso = _extrair(_chamar(corpo, chave))
            erro = None
            break
        except (OSError, ValueError, KeyError, IndexError, TypeError) as falha:
            erro = _descrever(falha)
            texto, raciocinio, uso = "", None, None
            if not _eh_transitorio(falha) or tentativas == TENTATIVAS:
                break
            time.sleep(ESPERAS_S[tentativas - 1])
    return {
        "conteudo": texto,
        "raciocinio": raciocinio,
        "segundos": round(time.monotonic() - inicio, 1),
        "tentativas": tentativas,
        "erro": erro,
        "uso": uso,
    }


def _registro(exp: str, quadro: str, resposta: dict) -> dict:
    """Registro gravado de um pedido: identificação mais a resposta.

    Args:
        exp: nome do experimento (``e0``...``e3``).
        quadro: id do quadro (ou da sonda).
        resposta: saída de ``pedir``.

    Returns:
        Dicionário com ``exp``, ``quadro`` e os campos da resposta.
    """
    return {"exp": exp, "quadro": quadro, **resposta}


def _status(resposta: dict) -> str:
    """Texto curto do resultado de um pedido, para a linha de progresso.

    Args:
        resposta: saída de ``pedir``.

    Returns:
        ``ok`` ou ``erro <descrição>``.
    """
    return "ok" if resposta["erro"] is None else f"erro {resposta['erro']}"


# ---------------------------------------------------------------------------------
# Arquivos, desenvolvimento e execução paralela
# ---------------------------------------------------------------------------------


def _caminho(exp: str, nome: str) -> Path:
    """Arquivo de um pedido em ``MAOS_M20/<exp>/<nome>.json``.

    Args:
        exp: nome do experimento.
        nome: id do quadro, com sufixo ``_caixa`` na 1ª etapa do E3.

    Returns:
        Caminho do arquivo (a pasta pode não existir ainda).
    """
    return MAOS_M20 / exp / f"{nome}.json"


def _ler_arquivo(caminho: Path) -> dict | None:
    """Lê um registro gravado, se existir e for legível.

    Args:
        caminho: arquivo JSON.

    Returns:
        O dicionário, ou ``None`` se não existe ou não é um objeto JSON.
    """
    if not caminho.exists():
        return None
    try:
        dados = _carregar(caminho)
    except ValueError:
        return None
    return dados if isinstance(dados, dict) else None


def _pronto(caminho: Path) -> dict | None:
    """Registro que dispensa novo pedido: existe e não tem erro.

    Args:
        caminho: arquivo do pedido.

    Returns:
        O registro, ou ``None`` se é preciso pedir de novo.
    """
    registro = _ler_arquivo(caminho)
    if registro is None or registro.get("erro") is not None:
        return None
    return registro


def _quadros_dev() -> list[str]:
    """Os 33 quadros de desenvolvimento da 1019 (mesma divisão, mesma semente).

    Returns:
        Ids em ordem alfabética.
    """
    ids = sorted(_carregar(GABARITO_BRACO)["quadros"])
    return dividir(ids)[0]


def exigir_dev(quadros: list[str], dev: list[str]) -> None:
    """Recusa quadros que não são de desenvolvimento (o teste fica lacrado).

    Args:
        quadros: ids pedidos na linha de comando.
        dev: ids de desenvolvimento.

    Raises:
        ValueError: se algum id não está em ``dev``.
    """
    fora = [quadro for quadro in quadros if quadro not in dev]
    if fora:
        raise ValueError(
            "quadros fora do desenvolvimento (teste lacrado): " + ", ".join(fora)
        )


def escolher_quadros(
    pedidos: list[str] | None, limite: int | None, dev: list[str]
) -> list[str]:
    """Quadros a pedir: os informados (só de dev) ou os primeiros ``limite`` de dev.

    Args:
        pedidos: ids da linha de comando, ou ``None``.
        limite: quantos quadros de dev pedir, ou ``None`` para todos.
        dev: ids de desenvolvimento, em ordem.

    Returns:
        Ids a pedir.

    Raises:
        ValueError: se um id pedido não é de desenvolvimento.
    """
    if pedidos is not None:
        exigir_dev(pedidos, dev)
        return pedidos
    return dev if limite is None else dev[:limite]


def _em_paralelo(itens: list[str], trabalho: Callable[[str], str]) -> None:
    """Roda ``trabalho`` em cada item, até ``PARALELOS`` por vez, e mostra o andamento.

    Args:
        itens: ids a processar.
        trabalho: função que recebe o id e devolve um texto de status.
    """
    total = len(itens)
    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALELOS) as pool:
        futuros = {pool.submit(trabalho, item): item for item in itens}
        for feitos, futuro in enumerate(
            concurrent.futures.as_completed(futuros), start=1
        ):
            print(f"{feitos}/{total} {futuros[futuro]}: {futuro.result()}", flush=True)


# ---------------------------------------------------------------------------------
# E0: sonda sintética
# ---------------------------------------------------------------------------------


def geometria_e0(espacamento: int, inclinacao: float) -> list[np.ndarray]:
    """Pontas das 6 linhas verdadeiras da sonda, em pixels do quadro 1280x720.

    A linha 1 é a de índice 0 (a mais fina) e a linha 6 é a de índice 5.

    Args:
        espacamento: distância perpendicular entre linhas vizinhas, em pixels.
        inclinacao: ângulo das linhas, em graus.

    Returns:
        Lista de 6 arrays ``(2, 2)``: as duas pontas de cada linha.
    """
    teta = math.radians(inclinacao)
    direcao = np.array([math.cos(teta), math.sin(teta)])
    normal = np.array([-direcao[1], direcao[0]])
    centro = np.array([LARGURA_E0 / 2, ALTURA_E0 / 2])
    meio = COMPRIMENTO_E0 / 2
    linhas: list[np.ndarray] = []
    for indice in range(N_LINHAS):
        c = centro + (indice - (N_LINHAS - 1) / 2) * espacamento * normal
        linhas.append(np.array([c - meio * direcao, c + meio * direcao]))
    return linhas


def desenhar_e0(espacamento: int, inclinacao: float) -> np.ndarray:
    """Desenha a sonda: 6 linhas claras de 1 a 3 px sobre fundo marrom.

    Desenha em ``FATOR_SUPER`` vezes a resolução e reduz com média, para a espessura
    fracionária sair certa.

    Args:
        espacamento: distância perpendicular entre linhas, em pixels.
        inclinacao: ângulo das linhas, em graus.

    Returns:
        Imagem BGR de 1280x720.
    """
    fator = FATOR_SUPER
    tela = np.full(
        (ALTURA_E0 * fator, LARGURA_E0 * fator, 3), COR_FUNDO_E0, dtype=np.uint8
    )
    espessuras = np.linspace(1.0, 3.0, N_LINHAS)
    for linha, espessura in zip(
        geometria_e0(espacamento, inclinacao), espessuras, strict=True
    ):
        ponta_a, ponta_b = (tuple(round(v) for v in ponto * fator) for ponto in linha)
        cv2.line(
            tela,
            ponta_a,
            ponta_b,
            COR_LINHA_E0,
            thickness=round(espessura * fator),
            lineType=cv2.LINE_AA,
        )
    return cv2.resize(tela, (LARGURA_E0, ALTURA_E0), interpolation=cv2.INTER_AREA)


def erros_e0(conteudo: str, espacamento: int, inclinacao: float) -> dict | None:
    """Erro das linhas 1 e 6 da sonda, em espaçamentos, e a troca entre elas.

    O erro de cada linha é o maior desvio perpendicular das 2 pontas à linha verdadeira,
    dividido pelo espaçamento. A troca vale quando, com 1 e 6 trocadas, o erro fica
    abaixo de ``LIMITE_TROCA`` e o normal fica acima.

    Args:
        conteudo: texto cru do modelo (JSON com ``linha1`` e ``linha6``).
        espacamento: espaçamento do quadro, em pixels.
        inclinacao: inclinação do quadro, em graus.

    Returns:
        ``{"erro1", "erro6", "trocou"}``, ou ``None`` se a resposta não tem as duas linhas.
    """
    dados = interpretar(conteudo)
    if dados is None:
        return None
    linha1 = _corda(dados.get("linha1"))
    linha6 = _corda(dados.get("linha6"))
    if linha1 is None or linha6 is None:
        return None
    verdadeiras = geometria_e0(espacamento, inclinacao)
    reta1, reta6 = verdadeiras[0], verdadeiras[-1]
    pontos1 = [
        np.array([x * LARGURA_E0 / 1000, y * ALTURA_E0 / 1000]) for x, y in linha1
    ]
    pontos6 = [
        np.array([x * LARGURA_E0 / 1000, y * ALTURA_E0 / 1000]) for x, y in linha6
    ]

    def maior_desvio(pontos: list[np.ndarray], reta: np.ndarray) -> float:
        return max(_distancia_a_reta(p, reta[0], reta[1]) for p in pontos) / espacamento

    erro1 = maior_desvio(pontos1, reta1)
    erro6 = maior_desvio(pontos6, reta6)
    trocado = max(maior_desvio(pontos1, reta6), maior_desvio(pontos6, reta1))
    normal = max(erro1, erro6)
    return {
        "erro1": erro1,
        "erro6": erro6,
        "trocou": bool(trocado < LIMITE_TROCA and normal > LIMITE_TROCA),
    }


def _pedido_e0(quadro: str, chave: str) -> str:
    """Gera a sonda de um quadro, grava a imagem e pede a resposta (sem raciocínio).

    Args:
        quadro: id da sonda (ex.: ``s08_a00``).
        chave: chave da DeepSeek.

    Returns:
        Texto de status.
    """
    caminho = _caminho("e0", quadro)
    if _pronto(caminho) is not None:
        return "pulado"
    espacamento, inclinacao = QUADROS_E0[quadro]
    imagem = desenhar_e0(espacamento, inclinacao)
    png = MAOS_M20 / "e0" / f"{quadro}.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(png), imagem)
    conteudo = [
        {"type": "text", "text": PROMPT_E0},
        bloco_imagem(codificar_jpeg(imagem)),
    ]
    resposta = pedir(corpo_pedido(conteudo, pensar=False), chave)
    _gravar_json(caminho, _registro("e0", quadro, resposta))
    return _status(resposta)


def rodar_e0(chave: str) -> int:
    """Roda o E0: as 8 sondas, sem raciocínio.

    Args:
        chave: chave da DeepSeek.

    Returns:
        Código de saída (0).
    """
    _em_paralelo(list(QUADROS_E0), functools.partial(_pedido_e0, chave=chave))
    return 0


# ---------------------------------------------------------------------------------
# E1 e E2: quadro inteiro
# ---------------------------------------------------------------------------------


def conteudo_quadro(quadro: str) -> list[dict]:
    """Prompt da 1019 e o quadro inteiro, reduzido à largura de envio.

    Args:
        quadro: id do quadro.

    Returns:
        Partes da mensagem: texto e imagem.
    """
    base64_jpeg, largura, altura = preparar_envio(MAOS_M3B_QUADROS / f"{quadro}.png")
    return [
        {"type": "text", "text": PROMPT.format(largura=largura, altura=altura)},
        bloco_imagem(base64_jpeg),
    ]


def _pedido_quadro(exp: str, quadro: str, pensar: bool, chave: str) -> str:
    """Pede a marcação de um quadro inteiro (E1 ou E2).

    Args:
        exp: ``e1`` ou ``e2``.
        quadro: id do quadro.
        pensar: se o raciocínio fica ligado.
        chave: chave da DeepSeek.

    Returns:
        Texto de status.
    """
    caminho = _caminho(exp, quadro)
    if _pronto(caminho) is not None:
        return "pulado"
    resposta = pedir(corpo_pedido(conteudo_quadro(quadro), pensar), chave)
    _gravar_json(caminho, _registro(exp, quadro, resposta))
    return _status(resposta)


# ---------------------------------------------------------------------------------
# E3: caixa do braço e recorte ampliado
# ---------------------------------------------------------------------------------


def caixa_da_resposta(conteudo: str) -> tuple[float, float, float, float] | None:
    """Caixa ``[x0, y0, x1, y1]`` de 0 a 1000 da 1ª etapa, limitada e ordenada.

    Args:
        conteudo: texto cru do modelo.

    Returns:
        ``(x0, y0, x1, y1)`` em 0 a 1000, ou ``None`` se a caixa não é válida.
    """
    dados = interpretar(conteudo)
    if dados is None:
        return None
    valor = dados.get("caixa")
    if not isinstance(valor, list) or len(valor) != 4:
        return None
    if any(isinstance(v, bool) or not isinstance(v, int | float) for v in valor):
        return None
    numeros = [float(v) for v in valor]
    if not all(math.isfinite(v) for v in numeros):
        return None
    x0, x1 = sorted(min(max(v, 0.0), 1000.0) for v in numeros[0::2])
    y0, y1 = sorted(min(max(v, 0.0), 1000.0) for v in numeros[1::2])
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def caixa_com_margem(
    caixa: tuple[float, float, float, float], largura: int, altura: int
) -> tuple[int, int, int, int]:
    """Caixa em pixels do original, com ``MARGEM_RECORTE`` de cada lado, dentro da imagem.

    A margem é fração do tamanho da caixa. Onde a caixa encosta na borda, a margem é
    cortada, e o recorte não sai da imagem.

    Args:
        caixa: ``(x0, y0, x1, y1)`` em 0 a 1000 do quadro.
        largura: largura do quadro original, em pixels.
        altura: altura do quadro original, em pixels.

    Returns:
        ``(x0, y0, x1, y1)`` inteiros em pixels do original, com ``x1 > x0`` e ``y1 > y0``.
    """
    x0, y0, x1, y1 = (
        caixa[0] * largura / 1000,
        caixa[1] * altura / 1000,
        caixa[2] * largura / 1000,
        caixa[3] * altura / 1000,
    )
    margem_x = MARGEM_RECORTE * (x1 - x0)
    margem_y = MARGEM_RECORTE * (y1 - y0)
    x0 = max(0.0, x0 - margem_x)
    y0 = max(0.0, y0 - margem_y)
    x1 = min(float(largura), x1 + margem_x)
    y1 = min(float(altura), y1 + margem_y)
    return (
        math.floor(x0),
        math.floor(y0),
        min(largura, math.ceil(x1)),
        min(altura, math.ceil(y1)),
    )


def dimensoes_recorte(largura: int, altura: int) -> tuple[int, int, float]:
    """Tamanho do recorte ampliado: largura até 1280, lado maior até 1300.

    Args:
        largura: largura do recorte no original, em pixels.
        altura: altura do recorte no original, em pixels.

    Returns:
        ``(nova_largura, nova_altura, escala)``, em que ``escala`` é a razão efetiva
        ``nova_largura / largura``.
    """
    escala = min(LARGURA_RECORTE / largura, LADO_RECORTE / max(largura, altura))
    nova_largura = min(LARGURA_RECORTE, max(1, round(largura * escala)))
    nova_altura = max(1, round(altura * escala))
    return nova_largura, nova_altura, nova_largura / largura


def ponto_do_recorte(
    ponto: tuple[float, float], recorte: tuple[int, int, int, int]
) -> tuple[float, float]:
    """Converte um ponto de 0 a 1000 do recorte para pixels do quadro original.

    Args:
        ponto: ``(x, y)`` de 0 a 1000 relativo ao recorte.
        recorte: ``(x0, y0, x1, y1)`` do recorte, em pixels do original.

    Returns:
        ``(x, y)`` em pixels do quadro original.
    """
    x0, y0, x1, y1 = recorte
    return (
        x0 + ponto[0] * (x1 - x0) / 1000.0,
        y0 + ponto[1] * (y1 - y0) / 1000.0,
    )


def _ao_quadro(
    valor: object, recorte: tuple[int, int, int, int], largura: int, altura: int
) -> object:
    """Um ponto do recorte, em 0 a 1000 do quadro original. Valor inválido volta igual.

    Args:
        valor: o campo lido do JSON da 2ª etapa.
        recorte: caixa do recorte, em pixels do original.
        largura: largura do quadro original.
        altura: altura do quadro original.

    Returns:
        ``[x, y]`` de 0 a 1000 do quadro, ou o próprio valor se não é um ponto.
    """
    ponto = _ponto(valor)
    if ponto is None:
        return valor
    x, y = ponto_do_recorte(ponto, recorte)
    return [x * 1000.0 / largura, y * 1000.0 / altura]


def converter_resposta_recorte(
    conteudo: str, recorte: tuple[int, int, int, int], largura: int, altura: int
) -> str | None:
    """Reescreve o JSON da 2ª etapa em 0 a 1000 do quadro original.

    Campos que não são pontos (``"fora"``, ``null``, ``braco``) são mantidos como estão,
    para a validação da 1019 decidir.

    Args:
        conteudo: texto cru da 2ª etapa (coordenadas do recorte).
        recorte: caixa do recorte, em pixels do original.
        largura: largura do quadro original.
        altura: altura do quadro original.

    Returns:
        JSON como texto, ou ``None`` se o conteúdo não tem um objeto JSON.
    """
    dados = interpretar(conteudo)
    if dados is None:
        return None

    def converter_corda(valor: object) -> object:
        if not isinstance(valor, list) or len(valor) != 2:
            return valor
        return [_ao_quadro(p, recorte, largura, altura) for p in valor]

    convertido = {
        "braco": dados.get("braco"),
        "nut": _ao_quadro(dados.get("nut"), recorte, largura, altura),
        "corda1": converter_corda(dados.get("corda1")),
        "corda6": converter_corda(dados.get("corda6")),
        "traste5": _ao_quadro(dados.get("traste5"), recorte, largura, altura),
        "traste12": _ao_quadro(dados.get("traste12"), recorte, largura, altura),
    }
    return json.dumps(convertido, ensure_ascii=False)


def _quadro_original(quadro: str) -> np.ndarray:
    """Imagem original do quadro (sem redução), para recortar.

    Args:
        quadro: id do quadro.

    Returns:
        Matriz BGR do PNG original.

    Raises:
        FileNotFoundError: se o PNG não pode ser lido.
    """
    imagem = cv2.imread(str(MAOS_M3B_QUADROS / f"{quadro}.png"))
    if imagem is None:
        raise FileNotFoundError(f"quadro ilegível: {quadro}")
    return imagem


def conteudo_caixa(quadro: str) -> list[dict]:
    """Prompt da 1ª etapa do E3 (a caixa do braço) e o quadro inteiro reduzido.

    Args:
        quadro: id do quadro.

    Returns:
        Partes da mensagem: texto e imagem.
    """
    base64_jpeg, largura, altura = preparar_envio(MAOS_M3B_QUADROS / f"{quadro}.png")
    return [
        {"type": "text", "text": PROMPT_CAIXA.format(largura=largura, altura=altura)},
        bloco_imagem(base64_jpeg),
    ]


def _pedido_e3(quadro: str, chave: str, pensar: bool) -> str:
    """As duas etapas do E3 para um quadro: a caixa e o recorte com o JSON da 1019.

    Grava ``<id>_caixa.json`` (1ª etapa) e ``<id>.json`` (2ª, com ``recorte`` e
    ``escala``). Se a caixa não é válida, grava ``motivo`` e não pede a 2ª etapa.

    Args:
        quadro: id do quadro.
        chave: chave da DeepSeek.
        pensar: se o raciocínio fica ligado nas duas etapas.

    Returns:
        Texto de status.
    """
    caminho = _caminho("e3", quadro)
    if _pronto(caminho) is not None:
        return "pulado"
    caminho_caixa = _caminho("e3", f"{quadro}_caixa")
    registro_caixa = _pronto(caminho_caixa)
    if registro_caixa is None:
        resposta = pedir(corpo_pedido(conteudo_caixa(quadro), pensar), chave)
        registro_caixa = _registro("e3", quadro, resposta)
        _gravar_json(caminho_caixa, registro_caixa)
    if registro_caixa["erro"] is not None:
        _gravar_json(
            caminho,
            {
                **_registro("e3", quadro, _vazio(registro_caixa["erro"])),
                "recorte": None,
                "escala": None,
            },
        )
        return _status(registro_caixa)
    caixa = caixa_da_resposta(registro_caixa["conteudo"])
    if caixa is None:
        _gravar_json(
            caminho,
            {
                **_registro("e3", quadro, _vazio(None)),
                "motivo": "caixa_invalida",
                "recorte": None,
                "escala": None,
            },
        )
        return "caixa_invalida"
    imagem = _quadro_original(quadro)
    altura, largura = imagem.shape[:2]
    recorte = caixa_com_margem(caixa, largura, altura)
    x0, y0, x1, y1 = recorte
    nova_largura, nova_altura, escala = dimensoes_recorte(x1 - x0, y1 - y0)
    ampliado = cv2.resize(
        imagem[y0:y1, x0:x1],
        (nova_largura, nova_altura),
        interpolation=cv2.INTER_CUBIC if escala > 1 else cv2.INTER_AREA,
    )
    texto = PREFIXO_E3 + PROMPT.format(largura=nova_largura, altura=nova_altura)
    conteudo = [{"type": "text", "text": texto}, bloco_imagem(codificar_jpeg(ampliado))]
    resposta = pedir(corpo_pedido(conteudo, pensar), chave)
    _gravar_json(
        caminho,
        {
            **_registro("e3", quadro, resposta),
            "recorte": list(recorte),
            "escala": escala,
        },
    )
    return _status(resposta)


def _vazio(erro: str | None) -> dict:
    """Resposta vazia, usada quando a 1ª etapa falhou ou a caixa não é válida.

    Args:
        erro: descrição da falha, ou ``None``.

    Returns:
        Dicionário no formato de ``pedir``, sem conteúdo.
    """
    return {
        "conteudo": "",
        "raciocinio": None,
        "segundos": 0.0,
        "tentativas": 0,
        "erro": erro,
        "uso": None,
    }


# ---------------------------------------------------------------------------------
# Avaliação
# ---------------------------------------------------------------------------------


def _descarte(motivo: str) -> dict:
    """Resultado de uma resposta descartada pelo filtro.

    Args:
        motivo: razão do descarte.

    Returns:
        Registro com classe ``nao_achou``.
    """
    return {"motivo": motivo, "classe": "nao_achou", "trocou": False, "erros": None}


def avaliar_resposta(
    conteudo: str, erro: str | None, largura: int, altura: int, alvo: Marcas
) -> dict:
    """Filtra e mede uma resposta contra o gabarito, pelo mesmo caminho da 1019.

    Args:
        conteudo: texto cru da resposta (já no quadro original, 0 a 1000).
        erro: falha do pedido, ou ``None``.
        largura: largura do quadro original.
        altura: altura do quadro original.
        alvo: marcas do gabarito do quadro (``Marcas``).

    Returns:
        ``motivo`` (``None`` se válida), ``classe``, ``trocou`` e ``erros`` (medida da
        1019, ou ``None``).
    """
    if erro:
        return _descarte("erro_proxy")
    analise, motivo = analisar(conteudo or "", largura, altura)
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
        "erros": medida["erros"],
    }


def custo_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Custo estimado em dólares, pelos preços do pré-registro.

    Args:
        prompt_tokens: tokens de entrada.
        completion_tokens: tokens de saída.

    Returns:
        Custo em US$.
    """
    return (
        prompt_tokens * PRECO_ENTRADA / 1_000_000
        + completion_tokens * PRECO_SAIDA / 1_000_000
    )


def _uso(registro: dict | None) -> tuple[int, int]:
    """Tokens de entrada e saída de um registro (zero se não há uso).

    Args:
        registro: registro gravado, ou ``None``.

    Returns:
        ``(prompt_tokens, completion_tokens)``.
    """
    uso = (registro or {}).get("uso") or {}
    return int(uso.get("prompt_tokens", 0)), int(uso.get("completion_tokens", 0))


def _resumo(valores: list[float]) -> dict | None:
    """Mediana, máximo e contagem de uma lista; ``None`` se vazia.

    Args:
        valores: números.

    Returns:
        ``{"mediana", "maximo", "n"}`` ou ``None``.
    """
    if not valores:
        return None
    return {
        "mediana": float(np.median(valores)),
        "maximo": float(max(valores)),
        "n": len(valores),
    }


def avaliar_experimento(
    exp: str, dev: list[str], indice: dict[str, dict], gabarito: dict[str, dict]
) -> dict:
    """Classes, medidas, tempo e custo de um experimento (E1, E2 ou E3).

    Quadro sem arquivo conta como ``nao_achou`` com motivo ``sem_resposta``.

    Args:
        exp: ``e1``, ``e2`` ou ``e3``.
        dev: ids de desenvolvimento.
        indice: ``{id: entrada}`` de ``_indice()``.
        gabarito: ``{id: registro}`` do gabarito do braço.

    Returns:
        Dicionário com ``presentes``, ``classes``, ``motivos``, medidas, ``trocas``,
        ``tempo_mediano_s``, tokens e ``custo_usd``.
    """
    classes: collections.Counter[str] = collections.Counter()
    motivos: collections.Counter[str] = collections.Counter()
    perp: list[float] = []
    nut: list[float] = []
    pior: list[float] = []
    tempos: list[float] = []
    trocas = presentes = prompt_total = completion_total = 0
    for quadro in dev:
        registro = _ler_arquivo(_caminho(exp, quadro))
        if registro is None:
            classes["nao_achou"] += 1
            motivos["sem_resposta"] += 1
            continue
        presentes += 1
        caixa = _ler_arquivo(_caminho(exp, f"{quadro}_caixa")) if exp == "e3" else None
        entrada = indice[quadro]
        alvo = marcas_do_registro(gabarito[quadro])
        if registro.get("motivo"):
            resultado = _descarte(registro["motivo"])
        else:
            conteudo = registro["conteudo"]
            if exp == "e3":
                conteudo = (
                    ""
                    if registro.get("recorte") is None
                    else converter_resposta_recorte(
                        conteudo,
                        tuple(registro["recorte"]),
                        entrada["largura"],
                        entrada["altura"],
                    )
                    or ""
                )
            resultado = avaliar_resposta(
                conteudo, registro["erro"], entrada["largura"], entrada["altura"], alvo
            )
        classes[resultado["classe"]] += 1
        if resultado["motivo"] is not None:
            motivos[resultado["motivo"]] += 1
        if resultado["trocou"]:
            trocas += 1
        if resultado["erros"] is not None:
            perp.append(resultado["erros"]["perp_cordas"])
            if resultado["erros"]["nut_casas"] is not None:
                nut.append(resultado["erros"]["nut_casas"])
            if resultado["erros"]["pior_traste_casas"] is not None:
                pior.append(resultado["erros"]["pior_traste_casas"])
        tempo = float(registro.get("segundos") or 0.0)
        for etapa in (registro, caixa):
            p, c = _uso(etapa)
            prompt_total += p
            completion_total += c
        if caixa is not None:
            tempo += float(caixa.get("segundos") or 0.0)
        tempos.append(tempo)
    return {
        "presentes": presentes,
        "classes": {
            k: classes[k] for k in ("certo", "impreciso", "falso", "nao_achou")
        },
        "motivos": dict(motivos),
        "perp_cordas": _resumo(perp),
        "nut_casas": _resumo(nut),
        "pior_traste_casas": _resumo(pior),
        "trocas": trocas,
        "tempo_mediano_s": float(np.median(tempos)) if tempos else None,
        "tokens_prompt": prompt_total,
        "tokens_completion": completion_total,
        "custo_usd": custo_usd(prompt_total, completion_total),
    }


def avaliar_e0() -> dict:
    """Tabela do E0 por espaçamento e inclinação, e tokens somados.

    Returns:
        Dicionário com ``linhas`` (uma por sonda) e os tokens e o custo.
    """
    linhas: list[dict] = []
    prompt_total = completion_total = 0
    for quadro, (espacamento, inclinacao) in sorted(
        QUADROS_E0.items(), key=lambda item: (item[1][0], item[1][1])
    ):
        registro = _ler_arquivo(_caminho("e0", quadro))
        p, c = _uso(registro)
        prompt_total += p
        completion_total += c
        linha = {
            "quadro": quadro,
            "espacamento": espacamento,
            "inclinacao": inclinacao,
            "erro1": None,
            "erro6": None,
            "trocou": None,
            "motivo": None,
        }
        if registro is None:
            linha["motivo"] = "sem_resposta"
        elif registro.get("erro") is not None:
            linha["motivo"] = "erro_proxy"
        else:
            medida = erros_e0(registro["conteudo"], espacamento, inclinacao)
            if medida is None:
                linha["motivo"] = "json_invalido"
            else:
                linha.update(medida)
        linhas.append(linha)
    return {
        "linhas": linhas,
        "tokens_prompt": prompt_total,
        "tokens_completion": completion_total,
        "custo_usd": custo_usd(prompt_total, completion_total),
    }


def _formatar(valor: float | None, casas: int = 2) -> str:
    """Número com casas decimais, ou um traço se ``None``.

    Args:
        valor: número ou ``None``.
        casas: casas decimais.

    Returns:
        Texto do número.
    """
    return "—" if valor is None else f"{valor:.{casas}f}"


def _imprimir_e0(resumo: dict) -> None:
    """Imprime a tabela do E0 por espaçamento e inclinação.

    Args:
        resumo: saída de ``avaliar_e0``.
    """
    print("E0 (sonda sintética): erro em espaçamentos; troca 1<->6")
    print(
        f"{'esp':>4} {'incl':>5} {'erro1':>7} {'erro6':>7} {'troca':>6} {'motivo':>12}"
    )
    for linha in resumo["linhas"]:
        troca = (
            "—" if linha["trocou"] is None else ("sim" if linha["trocou"] else "não")
        )
        print(
            f"{linha['espacamento']:>4} {linha['inclinacao']:>5.1f} "
            f"{_formatar(linha['erro1']):>7} {_formatar(linha['erro6']):>7} "
            f"{troca:>6} {linha['motivo'] or '':>12}"
        )
    print(
        f"  tokens: prompt {resumo['tokens_prompt']}, saída "
        f"{resumo['tokens_completion']}; custo US$ {resumo['custo_usd']:.4f}"
    )


def _imprimir_experimento(nome: str, resumo: dict, total: int) -> None:
    """Imprime o resumo de um experimento E1, E2 ou E3.

    Args:
        nome: nome do experimento.
        resumo: saída de ``avaliar_experimento``.
        total: quadros de desenvolvimento.
    """
    print(
        f"\n{nome.upper()} ({resumo['presentes']} respostas de {total} quadros de dev)"
    )
    classes = resumo["classes"]
    print("  classes: " + " | ".join(f"{k} {v}" for k, v in classes.items()))
    print(f"  motivos de descarte: {resumo['motivos'] or '—'}")
    for chave, rotulo in (
        ("perp_cordas", "perp_cordas (vãos)"),
        ("nut_casas", "nut_casas"),
        ("pior_traste_casas", "pior_traste_casas"),
    ):
        r = resumo[chave]
        if r is None:
            print(f"  {rotulo}: sem respostas válidas")
        else:
            print(
                f"  {rotulo}: mediana {r['mediana']:.2f}, máximo {r['maximo']:.2f} "
                f"(n={r['n']})"
            )
    print(f"  trocas de cordas: {resumo['trocas']}")
    print(f"  tempo mediano: {_formatar(resumo['tempo_mediano_s'], 1)} s")
    print(
        f"  tokens: prompt {resumo['tokens_prompt']}, saída "
        f"{resumo['tokens_completion']}; custo US$ {resumo['custo_usd']:.4f}"
    )


def avaliar() -> int:
    """Avalia E0, E1, E2 e E3 e grava ``m20/resultado.json``.

    Returns:
        Código de saída (0).
    """
    gabarito = _carregar(GABARITO_BRACO)["quadros"]
    dev = _quadros_dev()
    indice = _indice()
    resultado: dict[str, object] = {"semente": SEMENTE, "dev": dev}
    e0 = avaliar_e0()
    _imprimir_e0(e0)
    resultado["e0"] = e0
    custo_total = e0["custo_usd"]
    for exp in ("e1", "e2", "e3"):
        resumo = avaliar_experimento(exp, dev, indice, gabarito)
        if resumo["presentes"] == 0:
            continue
        _imprimir_experimento(exp, resumo, len(dev))
        resultado[exp] = resumo
        custo_total += resumo["custo_usd"]
    resultado["custo_total_usd"] = custo_total
    print(f"\nCusto total estimado: US$ {custo_total:.4f}")
    _gravar_json(MAOS_M20 / "resultado.json", resultado)
    print(f"Gravado: {MAOS_M20 / 'resultado.json'}")
    return 0


# ---------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI: ``e0``, ``e1``, ``e2``, ``e3`` ou ``avaliar``.

    Args:
        argv: argumentos da linha de comando; ``None`` usa ``sys.argv``.

    Returns:
        Código de saída: 0, 2 se a chave não existe.
    """
    parser = argparse.ArgumentParser(
        description="DeepSeek direto: o recorte do braço (rodada 1020)."
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("e0", help="sonda sintética: 8 imagens, sem raciocínio")
    for nome, ajuda in (
        ("e1", "quadro inteiro, raciocínio desligado"),
        ("e2", "quadro inteiro, raciocínio ligado"),
        ("e3", "caixa do braço e recorte ampliado, em duas etapas"),
    ):
        parser_exp = sub.add_parser(nome, help=ajuda)
        parser_exp.add_argument(
            "--quadros", help="ids separados por vírgula (só de dev)"
        )
        parser_exp.add_argument("--limite", type=int, help="quantos quadros de dev")
        if nome == "e3":
            parser_exp.add_argument(
                "--pensar",
                choices=("on", "off"),
                default="off",
                help="raciocínio nas duas etapas (padrão off)",
            )
    sub.add_parser("avaliar", help="filtra, mede e grava m20/resultado.json")
    args = parser.parse_args(argv)
    if args.comando == "avaliar":
        return avaliar()
    try:
        chave = ler_chave()
    except ChaveAusente as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 2
    if args.comando == "e0":
        return rodar_e0(chave)
    dev = _quadros_dev()
    pedidos = args.quadros.split(",") if args.quadros else None
    quadros = escolher_quadros(pedidos, args.limite, dev)
    if args.comando == "e1":
        trabalho = functools.partial(_pedido_quadro, "e1", pensar=False, chave=chave)
    elif args.comando == "e2":
        trabalho = functools.partial(_pedido_quadro, "e2", pensar=True, chave=chave)
    else:
        trabalho = functools.partial(
            _pedido_e3, chave=chave, pensar=args.pensar == "on"
        )
    _em_paralelo(quadros, trabalho)
    return 0


if __name__ == "__main__":
    sys.exit(main())
