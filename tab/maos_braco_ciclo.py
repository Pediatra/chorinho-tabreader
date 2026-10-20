"""Ciclo de revisão do braço (rodadas 1026, 1027 e 1029): sorteio, previsão e medida.

Pré-registros: ``docs/rodadas/1026-ciclo-de-revisao-sky-guitar.md`` (commit 1a70e34c),
``docs/rodadas/1027-ciclo-de-revisao-guitarous.md`` (commit 32c4a644) e
``docs/rodadas/1029-ciclo-de-revisao-pablo-rome.md`` (commit 7332f4d8).

CLI: ``python -m tab.maos_braco_ciclo {sortear,prever,medir,escolher-pesos}
[--rodada 1026|1027|1029]`` (padrão 1026). Cada rodada tem canal, semente, pasta e
gabarito na tabela ``RODADAS``. A 1029 escolhe os pesos antes de prever (``escolher-pesos``,
que roda a M11b na GPU) e pode ligar o P2 (um braço só) e o P3 (consenso S4).

1. ``sortear``: 8 vídeos do canal da rodada fora das amostras anteriores (M3b, M21 R,
   M25 treino e prova, e as rodadas de ciclo já feitas), 8 instantes por vídeo entre
   0,15 e 0,85 da duração. Cria a pasta da rodada e o gabarito vazio, e acrescenta os
   quadros pelo ``acrescentar`` da ferramenta do braço.
2. ``prever`` (GPU): cadeia com ``L2_todos_s1`` e ``A3_100_todos_s1``, decodificação
   conjunta. Grava ``previsto.json`` (a previsão completa) e preenche o gabarito com a
   previsão, cortada no primeiro traste fora da imagem (``braco`` fica vazio: o dono
   confirma). Os sinalizados vão primeiro na lista da página.
3. ``medir``: compara ``previsto.json`` com o gabarito final do dono. Não é rodado
   na 1027 até o dono terminar a revisão.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

from .caminhos import (
    GABARITO_BRACO_M11B,
    GABARITO_BRACO_M26,
    GABARITO_BRACO_M27,
    GABARITO_BRACO_M29,
    GABARITO_BRACO_M32,
    MAOS_M3B,
    MAOS_M11B,
    MAOS_M21,
    MAOS_M25,
    MAOS_M26,
    MAOS_M27,
    MAOS_M29,
    MAOS_M32,
    acervo,
)
from .maos_braco_consenso import SINAL_S4, consenso
from .maos_braco_detector import (
    DIR_PESOS,
    PASSOS,
    QUADROS_PROVA,
    _carregar_pesos,
    _imagem,
    _no_quadro,
    _trava_gpu,
)
from .maos_braco_gabarito import (
    CAMPOS_GEOMETRIA,
    FORMATO_GABARITO,
    acrescentar,
    numerar_trastes,
    tem_resposta,
)
from .maos_braco_localizador import (
    QUADRO_BRACO_NAO,
    _carregar_localizador,
    cadeia,
    sinalizado,
)
from .maos_braco_sinal_nut import (
    FRACAO_V2,
    distancia_da_ponta,
    linhas_de_painel,
    suspeito,
)
from .maos_braco_tempo import Marcas, classificar, erros, marcas_do_registro
from .maos_gabarito import gravar_atomico


@dataclasses.dataclass(frozen=True)
class Rodada:
    """Parâmetros de uma rodada do ciclo: canal, semente, pasta e gabarito.

    Attributes:
        canal: pasta do canal no acervo (o lote é sorteado só dentro dela).
        semente: semente do sorteio dos vídeos.
        pasta: pasta da rodada (``indice.json``, ``quadros/``, ``previsto.json``).
        gabarito: gabarito que o dono confere.
        proxima: rodada que vem depois, para a frase do critério.
    """

    canal: str
    semente: int
    pasta: Path
    gabarito: Path
    proxima: str


#: Uma linha por rodada. A 1026 é a primeira; a 1027 usa o mesmo detector, sem mudança.
RODADAS: dict[str, Rodada] = {
    "1026": Rodada(
        canal="sky guitar",
        semente=20261026,
        pasta=MAOS_M26,
        gabarito=GABARITO_BRACO_M26,
        proxima="1027",
    ),
    "1027": Rodada(
        canal="ギタロー ⧸ guitarous",
        semente=20261027,
        pasta=MAOS_M27,
        gabarito=GABARITO_BRACO_M27,
        proxima="1028",
    ),
    "1029": Rodada(
        canal="pablo romé",
        semente=20261029,
        pasta=MAOS_M29,
        gabarito=GABARITO_BRACO_M29,
        proxima="rodada seguinte",
    ),
    "1032": Rodada(
        canal="kenneth acoustic",
        semente=20261032,
        pasta=MAOS_M32,
        gabarito=GABARITO_BRACO_M32,
        proxima="rodada seguinte",
    ),
}

#: Rodada usada quando a CLI não recebe ``--rodada``.
RODADA_PADRAO = "1026"

#: Rodadas com pesos escolhidos por ``escolher-pesos`` (a 1026 e a 1027 ficam com os fixos).
RODADAS_COM_ESCOLHA = ("1029", "1032")
#: Rodadas cuja escolha considera também os pesos A5 do estágio 2 (rodada 1031).
RODADAS_COM_A5 = ("1032",)
#: Rodadas que sinalizam o quadro com o nut suspeito de estar fora da imagem (a regra de
#: borda da 1030, só como sinal; pré-registro da 1031).
RODADAS_SINAL_NUT = ("1032",)
#: Rodadas que usam o sinal v2 (bordas do quadro e linhas de painel; rodada 1033, que o pôs
#: no lugar do v1 na 1032).
RODADAS_SINAL_NUT_V2 = ("1032",)
#: Nut suspeito: ponta das cordas do lado do nut a até esta fração da borda menor.
FRACAO_BORDA_NUT_SUSPEITO = 0.02

#: Sementes dos pesos L3 e A4 que a escolha considera (``*_todos_s<k>``).
SEMENTES_PESOS = (1, 2, 3)
#: Nomes dos pesos de cada estágio na escolha da 1029.
PREFIXO_L3 = "L3_todos_s"
PREFIXO_A4 = "A4_100_todos_s"
PREFIXO_A5 = "A5_100_todos_s"
#: Arquivo com a escolha de pesos da 1029 (dentro da pasta da rodada).
ARQUIVO_ESCOLHA = "escolha_pesos.json"
#: Previsão com os pesos antigos (L2_s1 + A3_s1), para a comparação da 1029.
ARQUIVO_PREVISTO_ANTIGO = "previsto_antigo.json"
#: Fontes de vídeos que a 1029 exclui além de ``arquivos_ja_usados``: a 1027 e a M11b.
ARQUIVO_INDICE_M27 = MAOS_M27 / "indice.json"
ARQUIVO_CHAVES_M11B = MAOS_M11B / "chaves.json"

#: Vídeos do lote e quadros por vídeo.
N_VIDEOS = 8
N_INSTANTES = 8

#: Janela dos instantes, como fração da duração (inclusive nas pontas).
FRACAO_INICIO = 0.15
FRACAO_FIM = 0.85

#: Extensões que contam como vídeo no acervo.
EXTENSOES_VIDEO = (".mp4", ".webm", ".mkv")

#: Pesos do detector congelados (sem mudança nesta rodada).
ESTAGIO1 = "L2_todos_s1"
ESTAGIO2 = "A3_100_todos_s1"

#: Critérios do pré-registro (tabela "Critério para seguir").
LIMITE_FALSOS_CICLO = 0.05
LIMITE_SINALIZADOS_CICLO = 0.50

#: Observação que tira o quadro da medida (violão de 7 cordas, fora do lote).
MARCA_SETE_CORDAS = "7 cordas"

#: Observações gravadas nos quadros previstos.
OBS_SINALIZADO = "previsto (sinalizado)"
OBS_NAO_SINALIZADO = "previsto (não sinalizado)"
OBS_SEM_BRACO = "previsto: sem braço (sinalizado)"

ARQUIVO_INDICE = "indice.json"
ARQUIVO_PREVISTO = "previsto.json"
ARQUIVO_MEDIDA = "medida.json"
ARQUIVO_SORTEIO = "sorteio.json"


def como_foi_rotulado(numero: str) -> str:
    """Texto do gabarito que diz como os quadros foram rotulados.

    Args:
        numero: rodada (``"1026"`` ou ``"1027"``).

    Returns:
        A frase gravada em ``como_foi_rotulado`` do gabarito.
    """
    return (
        f"dono, por quadro, na ferramenta tab.maos_braco_gabarito (rodada {numero}, "
        "ciclo de revisão: a previsão do detector já vem preenchida, o dono confere); "
        "coordenadas no espaço do quadro original (x_quadro = x_img / escala)"
    )


# ---------------------------------------------------------------------------------
# Sorteio
# ---------------------------------------------------------------------------------


def fracoes_instantes() -> list[float]:
    """Frações da duração dos 8 instantes, igualmente espaçadas de 0,15 a 0,85.

    Returns:
        ``N_INSTANTES`` frações, a primeira em ``FRACAO_INICIO`` e a última em
        ``FRACAO_FIM``.
    """
    passo = (FRACAO_FIM - FRACAO_INICIO) / (N_INSTANTES - 1)
    return [round(FRACAO_INICIO + k * passo, 6) for k in range(N_INSTANTES)]


def escolher_videos(
    candidatos: list[str],
    excluidos: set[str],
    semente: int,
    n: int = N_VIDEOS,
) -> list[str]:
    """Sorteia ``n`` vídeos fora de ``excluidos``, reproduzível pela semente.

    Args:
        candidatos: caminhos relativos ao acervo (``canal/arquivo``).
        excluidos: caminhos que já apareceram em amostras anteriores.
        semente: semente do sorteio.
        n: quantos vídeos sortear.

    Returns:
        Os ``n`` vídeos sorteados, na ordem do sorteio.

    Raises:
        ValueError: se não houver ``n`` vídeos livres.
    """
    livres = sorted(v for v in set(candidatos) if v not in excluidos)
    if len(livres) < n:
        raise ValueError(f"{len(livres)} vídeos livres para sortear {n}")
    return random.Random(semente).sample(livres, n)


def itens_do_sorteio(videos: list[str], duracoes: dict[str, float]) -> list[dict]:
    """Um item por quadro: cada vídeo nos ``N_INSTANTES`` instantes da janela.

    Args:
        videos: vídeos sorteados (caminhos relativos ao acervo).
        duracoes: duração de cada vídeo, em segundos.

    Returns:
        Itens ``{arquivo, t, tab}`` no formato de ``acrescentar``, vídeo a vídeo.
    """
    return [
        {"arquivo": video, "t": round(fracao * duracoes[video], 2), "tab": None}
        for video in videos
        for fracao in fracoes_instantes()
    ]


def arquivos_ja_usados() -> set[str]:
    """Vídeos que já aparecem nas amostras anteriores e nos ciclos de revisão.

    Fontes: M3b, M21 R, M25 treino e prova (o teste da 1025), e os índices do ciclo da
    1026 (``m26``). A 1027 não pode repetir nenhum deles.

    Returns:
        Caminhos relativos ao acervo que não podem voltar no lote.
    """
    usados = {
        item["arquivo"] for item in _ler_json(MAOS_M3B / ARQUIVO_INDICE)["quadros"]
    }
    usados |= {
        item["arquivo"]
        for item in _ler_json(MAOS_M25 / "treino" / ARQUIVO_INDICE)["quadros"]
    }
    usados |= {
        item["arquivo"]
        for item in _ler_json(MAOS_M25 / "prova" / ARQUIVO_INDICE)["quadros"]
    }
    usados |= {
        item["arquivo"] for item in _ler_json(MAOS_M26 / ARQUIVO_INDICE)["quadros"]
    }
    for caminho in sorted((MAOS_M21 / "R").glob("*.json")):
        usados.add(_ler_json(caminho)["arquivo"])
    return usados


def arquivos_da_1027_e_m11b(
    indice_m27: Path = ARQUIVO_INDICE_M27, chaves_m11b: Path = ARQUIVO_CHAVES_M11B
) -> set[str]:
    """Vídeos da 1027 (``m27/indice.json``) e da M11b (``m11b/chaves.json``).

    Args:
        indice_m27: ``indice.json`` da 1027 (campo ``arquivo`` de cada quadro).
        chaves_m11b: ``chaves.json`` da M11b (campo ``arquivo`` de cada vídeo).

    Returns:
        Caminhos relativos ao acervo que a 1029 não pode sortear.
    """
    da_1027 = {item["arquivo"] for item in _ler_json(indice_m27)["quadros"]}
    da_m11b = {item["arquivo"] for item in _ler_json(chaves_m11b)["videos"]}
    return da_1027 | da_m11b


def excluidos_da_rodada(numero: str) -> set[str]:
    """Vídeos que a rodada não pode sortear: as amostras anteriores e os ciclos já feitos.

    A partir da 1029 saem também a 1027 e a M11b; a partir da 1032, também a 1029.

    Args:
        numero: rodada (chave de ``RODADAS``).

    Returns:
        Caminhos relativos ao acervo excluídos do sorteio.
    """
    usados = arquivos_ja_usados()
    if numero not in ("1026", "1027"):
        usados |= arquivos_da_1027_e_m11b()
    if numero not in ("1026", "1027", "1029"):
        usados |= {
            item["arquivo"] for item in _ler_json(MAOS_M29 / ARQUIVO_INDICE)["quadros"]
        }
    return usados


def _candidatos(raiz: Path, canal: str) -> list[str]:
    """Vídeos do canal do lote no acervo.

    Args:
        raiz: raiz do acervo (só leitura).
        canal: pasta do canal dentro do acervo.

    Returns:
        Caminhos relativos ao acervo, em ordem.
    """
    nomes = os.listdir(raiz / canal)
    return sorted(
        f"{canal}/{nome}" for nome in nomes if nome.lower().endswith(EXTENSOES_VIDEO)
    )


def _duracao(caminho: Path) -> float:
    """Duração de um vídeo, em segundos, lida pelo ffprobe.

    Args:
        caminho: arquivo do acervo.

    Returns:
        A duração do formato.

    Raises:
        RuntimeError: se o ffprobe falhar.
    """
    resultado = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(caminho),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0 or not resultado.stdout.strip():
        raise RuntimeError(f"ffprobe falhou em {caminho}: {resultado.stderr.strip()}")
    return float(resultado.stdout.strip())


def gabarito_vazio(numero: str) -> dict:
    """Gabarito do ciclo sem nenhuma resposta (os quadros entram pelo ``acrescentar``).

    Args:
        numero: rodada (``"1026"`` ou ``"1027"``).

    Returns:
        Dicionário no formato da ferramenta, com ``quadros`` vazio.
    """
    return {
        "formato": FORMATO_GABARITO,
        "como_foi_rotulado": como_foi_rotulado(numero),
        "semente": RODADAS[numero].semente,
        "ferramenta": "tab.maos_braco_gabarito",
        "quadros": {},
    }


def sortear(numero: str = RODADA_PADRAO, raiz: Path | None = None) -> list[str]:
    """Sorteia o lote, cria a pasta e o gabarito vazios e acrescenta os quadros.

    Recusa se a pasta ou o gabarito já existirem: nada é sobrescrito.

    Args:
        numero: rodada (chave de ``RODADAS``).
        raiz: raiz do acervo; padrão é ``acervo()``.

    Returns:
        Os ids dos quadros criados, na ordem do sorteio.

    Raises:
        FileExistsError: se a pasta ou o gabarito já existirem.
    """
    rodada = RODADAS[numero]
    pasta, ouro = rodada.pasta, rodada.gabarito
    raiz = raiz or acervo()
    if (pasta / ARQUIVO_INDICE).exists() or ouro.exists():
        raise FileExistsError(f"já existe índice ou gabarito em {pasta} / {ouro}")
    usados = excluidos_da_rodada(numero)
    candidatos = _candidatos(raiz, rodada.canal)
    videos = escolher_videos(candidatos, usados, rodada.semente)
    duracoes = {video: _duracao(raiz / video) for video in videos}
    itens = itens_do_sorteio(videos, duracoes)
    pasta.mkdir(parents=True, exist_ok=True)
    gravar_atomico(pasta / ARQUIVO_INDICE, {"semente": rodada.semente, "quadros": []})
    gravar_atomico(ouro, gabarito_vazio(numero))
    ids = acrescentar(itens, raiz, pasta, ouro)
    gravar_atomico(
        pasta / ARQUIVO_SORTEIO,
        {
            "semente": rodada.semente,
            "canal": rodada.canal,
            "fracoes": fracoes_instantes(),
            "candidatos": len(candidatos),
            "excluidos": len(usados),
            "videos": [{"arquivo": v, "duracao_s": duracoes[v]} for v in videos],
        },
    )
    return ids


# ---------------------------------------------------------------------------------
# Previsão
# ---------------------------------------------------------------------------------


def _sinal(valor: float) -> float | None:
    """Sinal da regra como número; infinito (sem braço) vira ``None``.

    Args:
        valor: S1, S2 ou S3 da cadeia.

    Returns:
        O valor, ou ``None`` quando é infinito.
    """
    return None if math.isinf(valor) else float(valor)


def _ponto(valor: object) -> list[float]:
    """Ponto ``[x, y]`` como lista de floats (para o JSON e para o gabarito).

    Args:
        valor: array ``(2,)`` ou sequência de dois números.

    Returns:
        ``[x, y]`` em float.
    """
    return [float(valor[0]), float(valor[1])]


def previsto_do_resultado(item: dict, resultado: dict, sinal: bool) -> dict:
    """Entrada de ``previsto.json`` para um quadro, a partir da saída da cadeia.

    Args:
        item: item do ``indice.json`` (``id``, ``arquivo``).
        resultado: saída de ``cadeia``.
        sinal: se a regra congelada manda o quadro para revisão.

    Returns:
        Dicionário com ``achou``, ``sinalizado``, os sinais, e as marcas no quadro
        (``nut``, ``corda1``, ``corda6`` e ``trastes`` com ``numero``), ou ``None``
        quando não há braço.
    """
    base = {
        "arquivo": item["arquivo"],
        "achou": bool(resultado["achou"]),
        "sinalizado": bool(sinal),
        "motivo": resultado.get("motivo"),
        "S1": _sinal(resultado["S1"]),
        "S2": _sinal(resultado["S2"]),
        "S3": _sinal(resultado["S3"]),
    }
    if not resultado["achou"]:
        return {**base, "nut": None, "corda1": None, "corda6": None, "trastes": None}
    marcas = _no_quadro(resultado["dec"], resultado["matriz"])
    return {
        **base,
        "nut": _ponto(marcas.nut),
        "corda1": [_ponto(p) for p in marcas.corda1],
        "corda6": [_ponto(p) for p in marcas.corda6],
        "trastes": [
            {"numero": int(n), "ponto": _ponto(marcas.trastes[n])}
            for n in sorted(marcas.trastes)
        ],
    }


def marcas_do_previsto(previsto: dict) -> Marcas | None:
    """Marcas previstas de um quadro (``Marcas`` do ``tab.maos_braco_tempo``).

    Args:
        previsto: entrada de ``previsto.json``.

    Returns:
        As marcas, ou ``None`` quando a cadeia não achou o braço.
    """
    if not previsto["achou"]:
        return None
    return Marcas(
        nut=np.asarray(previsto["nut"], dtype=float),
        trastes={
            item["numero"]: np.asarray(item["ponto"], dtype=float)
            for item in previsto["trastes"]
        },
        corda1=np.asarray(previsto["corda1"], dtype=float),
        corda6=np.asarray(previsto["corda6"], dtype=float),
    )


def trastes_visiveis(previsto: dict, dimensoes: tuple[int, int]) -> list[dict]:
    """Trastes previstos que o gabarito mostra: até o primeiro fora da imagem.

    A lista é cortada no primeiro ponto com ``x`` fora de ``[0, largura)`` ou ``y`` fora
    de ``[0, altura)``, e tudo depois dele sai (mesma regra com que o corte de 1026 foi
    feito à mão). A previsão completa continua em ``previsto.json``.

    Args:
        previsto: entrada de ``previsto.json`` (com ``achou`` verdadeiro).
        dimensoes: ``(largura, altura)`` do quadro original.

    Returns:
        Os itens ``{numero, ponto}`` do início da lista, na mesma ordem.
    """
    largura, altura = dimensoes
    for k, item in enumerate(previsto["trastes"]):
        x, y = item["ponto"]
        if not (0 <= x < largura and 0 <= y < altura):
            return previsto["trastes"][:k]
    return previsto["trastes"]


def registro_previsto(
    base: dict, previsto: dict, sinalizado_: bool, dimensoes: tuple[int, int]
) -> dict:
    """Registro do gabarito com a previsão: cordas, nut e trastes, ``braco`` vazio.

    Os trastes entram na ordem do número (1 a N, do nut para fora), que é a forma que
    ``numerar_trastes`` relê, e são cortados no primeiro fora da imagem
    (``trastes_visiveis``). ``trastes_previstos`` recebe a mesma lista cortada. Sem
    braço, a geometria fica vazia.

    Args:
        base: registro em branco do quadro (com ``chave``).
        previsto: entrada de ``previsto.json``.
        sinalizado_: se o quadro foi sinalizado (vai para a observação).
        dimensoes: ``(largura, altura)`` do quadro original.

    Returns:
        O novo registro (cópia; ``base`` não muda).
    """
    registro = copy.deepcopy(base)
    registro["braco"] = None
    registro["traste_referencia"] = None
    registro["capo"] = None
    if not previsto["achou"]:
        for campo in CAMPOS_GEOMETRIA:
            registro[campo] = None
        registro["obs"] = OBS_SEM_BRACO
        return registro
    pontos = [item["ponto"] for item in trastes_visiveis(previsto, dimensoes)]
    registro["corda1"] = copy.deepcopy(previsto["corda1"])
    registro["corda6"] = copy.deepcopy(previsto["corda6"])
    registro["nut"] = copy.deepcopy(previsto["nut"])
    registro["trastes"] = copy.deepcopy(pontos)
    registro["trastes_previstos"] = copy.deepcopy(pontos)
    registro["obs"] = OBS_SINALIZADO if sinalizado_ else OBS_NAO_SINALIZADO
    return registro


def conferir_numeracao(
    registro: dict, previsto: dict, dimensoes: tuple[int, int]
) -> None:
    """Confere que a ferramenta relê os trastes visíveis com os números da previsão.

    Args:
        registro: registro montado por ``registro_previsto``.
        previsto: a previsão do mesmo quadro.
        dimensoes: ``(largura, altura)`` do quadro original.

    Quadro sem braço não tem trastes: nada a conferir.

    Raises:
        ValueError: se ``numerar_trastes`` der outra numeração ou outros pontos.
    """
    if not previsto["achou"]:
        return
    esperado = [
        (item["numero"], item["ponto"])
        for item in trastes_visiveis(previsto, dimensoes)
    ]
    relido = [(item["numero"], item["ponto"]) for item in numerar_trastes(registro)]
    if relido != esperado:
        raise ValueError(f"numeração dos trastes diverge da previsão: {relido}")


def ordenar_por_sinalizado(ids: list[str], sinalizados: dict[str, bool]) -> list[str]:
    """Ordem da lista da página: sinalizados primeiro, cada grupo na ordem original.

    Args:
        ids: ids na ordem do ``indice.json``.
        sinalizados: id -> se o quadro foi sinalizado.

    Returns:
        Os ids com os sinalizados na frente.
    """
    return [i for i in ids if sinalizados[i]] + [i for i in ids if not sinalizados[i]]


def _ler_json(caminho: Path) -> dict:
    """Lê um JSON em UTF-8.

    Args:
        caminho: arquivo.

    Returns:
        O conteúdo.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def _sem_resposta(gabarito: dict) -> None:
    """Recusa o gabarito se algum quadro já tem resposta ou histórico do dono.

    Args:
        gabarito: gabarito do ciclo.

    Raises:
        ValueError: se houver resposta ou histórico.
    """
    for id_q, registro in gabarito["quadros"].items():
        if tem_resposta(registro) or registro.get("historico"):
            raise ValueError(
                f"{id_q} já tem resposta do dono; a previsão não sobrescreve"
            )


@dataclasses.dataclass(frozen=True)
class Pesos:
    """Pesos de uma rodada e as opções ligadas (P2 e P3).

    Attributes:
        estagio1: nome do localizador (estágio 1).
        estagio2: nome do detector (estágio 2).
        p2: se o estágio 1 usa o P2 (um braço só).
        p3: se o consenso S4 (P3) entra no lote.
    """

    estagio1: str
    estagio2: str
    p2: bool = False
    p3: bool = False


def pesos_da_rodada(numero: str) -> Pesos:
    """Pesos que a rodada usa: fixos na 1026 e na 1027, escolhidos na 1029.

    Args:
        numero: rodada (chave de ``RODADAS``).

    Returns:
        ``Pesos`` com os nomes dos estágios e as opções P2 e P3.

    Raises:
        ValueError: se a rodada escolhe os pesos e ``escolha_pesos.json`` não existe.
    """
    if numero not in RODADAS_COM_ESCOLHA:
        return Pesos(ESTAGIO1, ESTAGIO2)
    caminho = RODADAS[numero].pasta / ARQUIVO_ESCOLHA
    if not caminho.exists():
        raise ValueError(
            f"falta {caminho}: rode `escolher-pesos --rodada {numero}` antes de `prever`"
        )
    escolha = _ler_json(caminho)
    return Pesos(
        estagio1=escolha["estagio1"],
        estagio2=escolha["estagio2"],
        p2=bool(escolha["p2"]),
        p3=bool(escolha["p3"]),
    )


def pesos_do_documento(pesos: Pesos) -> dict:
    """Bloco ``pesos`` do ``previsto.json``; P2 e P3 só aparecem quando ligados.

    Args:
        pesos: pesos da rodada.

    Returns:
        ``estagio1``, ``estagio2`` e ``conjunta``, com ``um_braco`` e ``consenso``
        quando as opções estão ligadas.
    """
    doc: dict = {
        "estagio1": pesos.estagio1,
        "estagio2": pesos.estagio2,
        "conjunta": True,
    }
    if pesos.p2:
        doc["um_braco"] = True
    if pesos.p3:
        doc["consenso"] = SINAL_S4
    return doc


def _prever_quadros(
    pasta: Path, indice: dict, estagio1: str, estagio2: str, um_braco: bool
) -> dict[str, dict]:
    """Roda a cadeia (GPU) em cada quadro do índice e devolve a previsão de cada um.

    Args:
        pasta: pasta da rodada (os quadros estão em ``pasta / item["png"]``).
        indice: ``indice.json`` da rodada (``quadros`` com id, arquivo, png e t).
        estagio1: nome do localizador.
        estagio2: nome do detector.
        um_braco: se True, o estágio 1 usa o P2 (um braço só).

    Returns:
        ``{id: entrada de previsto.json}``, na ordem do índice.
    """
    previstos: dict[str, dict] = {}
    with _trava_gpu():
        loc = _carregar_localizador(estagio1)
        dois, _ = _carregar_pesos(estagio2, PASSOS)
        for item in indice["quadros"]:
            imagem = _imagem(pasta / item["png"])
            resultado = cadeia(
                loc, dois, imagem, item["id"], conjunta=True, um_braco=um_braco
            )
            sinal = sinalizado(resultado)
            previstos[item["id"]] = previsto_do_resultado(item, resultado, sinal)
            print(
                f"{item['id']} {item['arquivo']} t={item['t']}: "
                f"achou={previstos[item['id']]['achou']} sinalizado={sinal}",
                flush=True,
            )
    return previstos


def aplicar_consenso(doc: dict, dimensoes: dict[str, tuple[int, int]]) -> dict:
    """Aplica o P3 a uma previsão: sinaliza os quadros com S4.

    Movida de ``tab.maos_braco_p23`` (rodada 1028) para cá, para a 1029 usar o mesmo código.

    Args:
        doc: previsão no formato de ``previsto.json``.
        dimensoes: ``{id: (largura, altura)}`` de cada quadro.

    Returns:
        Cópia de ``doc`` com ``sinalizado`` atualizado e ``S4`` (k e referência) por quadro.
    """
    lista = []
    for id_q in doc["ordem"]:
        previsto = doc["quadros"][id_q]
        lista.append(
            {
                "id": id_q,
                "arquivo": previsto["arquivo"],
                "achou": previsto["achou"],
                "sinalizado": previsto["sinalizado"],
                "nut": previsto.get("nut"),
                "corda1": previsto.get("corda1"),
                "corda6": previsto.get("corda6"),
                "trastes": trastes_visiveis(previsto, dimensoes[id_q])
                if previsto["achou"]
                else [],
            }
        )
    sinais = consenso(lista)
    novo = copy.deepcopy(doc)
    for id_q in doc["ordem"]:
        sinal = sinais.get(id_q)
        if sinal is None:
            continue
        quadro = novo["quadros"][id_q]
        quadro["S4"] = sinal
        if sinal["S4"]:
            quadro["sinalizado"] = True
    return novo


def nut_suspeito_previsto(previsto: dict, dimensoes: tuple[int, int] | None) -> bool:
    """Regra de borda da 1030 (só sinal): nut ausente ou ponta das cordas rente à borda.

    Args:
        previsto: entrada de ``previsto.json`` (``nut``, ``corda1``, ``corda6``).
        dimensoes: ``(largura, altura)`` do quadro, ou None.

    Returns:
        True se o braço foi achado e o nut é suspeito de estar fora da imagem.
    """
    if not previsto.get("achou"):
        return False
    nut = previsto.get("nut")
    if nut is None or not dimensoes:
        return True
    largura, altura = dimensoes
    margem = FRACAO_BORDA_NUT_SUSPEITO * min(largura, altura)
    alvo = np.asarray(nut, dtype=float)
    for corda in (previsto["corda1"], previsto["corda6"]):
        pontas = np.asarray(corda, dtype=float)
        x, y = pontas[int(np.argmin(np.linalg.norm(pontas - alvo, axis=1)))]
        if min(x, y, largura - x, altura - y) <= margem:
            return True
    return False


def prever(numero: str = RODADA_PADRAO) -> dict[str, bool]:
    """Roda a cadeia em cada quadro e preenche o gabarito com a previsão (GPU).

    Grava ``previsto.json`` (completo), o gabarito (com os trastes cortados no primeiro
    fora da imagem) e o ``indice.json`` com a lista reordenada (sinalizados primeiro).
    Os ids não mudam.

    Args:
        numero: rodada (chave de ``RODADAS``); o gabarito já tem os quadros do ``sortear``.

    Returns:
        id -> sinalizado, na ordem em que a página mostra os quadros.

    Raises:
        ValueError: se o gabarito tiver formato errado, respostas do dono, ou se a
            numeração dos trastes não bater com a previsão.
    """
    rodada = RODADAS[numero]
    pasta, ouro = rodada.pasta, rodada.gabarito
    indice = _ler_json(pasta / ARQUIVO_INDICE)
    gabarito = _ler_json(ouro)
    if gabarito.get("formato") != FORMATO_GABARITO:
        raise ValueError(f"gabarito fora do formato {FORMATO_GABARITO}")
    _sem_resposta(gabarito)
    ids = [item["id"] for item in indice["quadros"]]
    if set(ids) != set(gabarito["quadros"]):
        raise ValueError("ids do indice.json e do gabarito não batem")
    dimensoes = {q["id"]: (q["largura"], q["altura"]) for q in indice["quadros"]}
    pesos = pesos_da_rodada(numero)
    previstos = _prever_quadros(pasta, indice, pesos.estagio1, pesos.estagio2, pesos.p2)
    if pesos.p3:
        previstos = aplicar_consenso({"ordem": ids, "quadros": previstos}, dimensoes)[
            "quadros"
        ]
    if numero in RODADAS_SINAL_NUT_V2:
        por_id_indice = {item["id"]: item for item in indice["quadros"]}
        for id_q in ids:
            if not previstos[id_q]["achou"]:
                continue
            paineis = linhas_de_painel(_imagem(pasta / por_id_indice[id_q]["png"]))
            distancia = distancia_da_ponta(previstos[id_q], dimensoes[id_q], paineis)
            if suspeito(distancia, dimensoes[id_q], FRACAO_V2):
                previstos[id_q]["nut_suspeito"] = True
                previstos[id_q]["sinalizado"] = True
    elif numero in RODADAS_SINAL_NUT:
        for id_q in ids:
            if nut_suspeito_previsto(previstos[id_q], dimensoes[id_q]):
                previstos[id_q]["nut_suspeito"] = True
                previstos[id_q]["sinalizado"] = True
    sinalizados = {id_q: previstos[id_q]["sinalizado"] for id_q in ids}
    ordem = ordenar_por_sinalizado(ids, sinalizados)
    novo_gabarito = dict(gabarito, quadros={})
    for id_q in ordem:
        registro = registro_previsto(
            gabarito["quadros"][id_q],
            previstos[id_q],
            sinalizados[id_q],
            dimensoes[id_q],
        )
        conferir_numeracao(registro, previstos[id_q], dimensoes[id_q])
        novo_gabarito["quadros"][id_q] = registro
    por_id = {item["id"]: item for item in indice["quadros"]}
    novo_indice = dict(indice, quadros=[por_id[id_q] for id_q in ordem])
    previsto_doc = {
        "formato": FORMATO_GABARITO,
        "semente": indice["semente"],
        "pesos": pesos_do_documento(pesos),
        "ordem": ordem,
        "quadros": {id_q: previstos[id_q] for id_q in ordem},
    }
    gravar_atomico(pasta / ARQUIVO_PREVISTO, previsto_doc)
    gravar_atomico(ouro, novo_gabarito)
    gravar_atomico(pasta / ARQUIVO_INDICE, novo_indice)
    return sinalizados


# ---------------------------------------------------------------------------------
# Escolha de pesos (rodada 1029): GPU, rodar uma vez antes de `prever --rodada 1029`
# ---------------------------------------------------------------------------------

#: Critério de escolha, como ficou no pré-registro 1029 (registrado no json).
CRITERIO_ESCOLHA = (
    "menos falsos não sinalizados na M11b; desempates: mais certos não sinalizados, "
    "menos sinalizados, menor soma de sementes"
)


def _peso_existe(nome: str, diretorio: Path) -> bool:
    """Se um peso tem o ``.pt`` e o ``.json`` (metadados) no diretório.

    Args:
        nome: nome do peso, sem extensão.
        diretorio: pasta dos pesos.

    Returns:
        True quando os dois arquivos existem.
    """
    return (diretorio / f"{nome}.pt").is_file() and (
        diretorio / f"{nome}.json"
    ).is_file()


def _semente(nome: str) -> int:
    """Semente de um peso ``*_s<k>``.

    Args:
        nome: nome do peso, como ``L3_todos_s2``.

    Returns:
        O ``k`` do sufixo.
    """
    return int(nome.rsplit("_s", 1)[1])


def combinacoes_existentes(
    diretorio: Path = DIR_PESOS, com_a5: bool = False
) -> list[tuple[str, str]]:
    """Pares ``(L3, A4)`` das sementes cujos pesos existem (produto cartesiano).

    Um peso que não existe (treino que falhou) sai da lista; as combinações restantes
    entram normalmente. Com ``com_a5``, os A5 que existirem entram depois dos A4.

    Args:
        diretorio: pasta dos pesos (``artefatos/m21``).
        com_a5: se os pesos A5 (rodada 1031) também são candidatos.

    Returns:
        Os pares de nomes, na ordem das sementes.
    """
    l3 = [
        f"{PREFIXO_L3}{s}"
        for s in SEMENTES_PESOS
        if _peso_existe(f"{PREFIXO_L3}{s}", diretorio)
    ]
    prefixos = (PREFIXO_A4, PREFIXO_A5) if com_a5 else (PREFIXO_A4,)
    a4 = [
        f"{prefixo}{s}"
        for prefixo in prefixos
        for s in SEMENTES_PESOS
        if _peso_existe(f"{prefixo}{s}", diretorio)
    ]
    return [(i, j) for i in l3 for j in a4]


def escolher_combinacao(tabela: list[dict]) -> dict:
    """Linha vencedora pelo critério do pré-registro 1029.

    Ordem das chaves: menos ``falsos_passam_n``; depois mais ``entregue_certo``; depois
    menos ``sinalizados``; depois a menor ``soma_sementes``. Empate total fica com a
    primeira linha.

    Args:
        tabela: uma linha por combinação, com as chaves acima.

    Returns:
        A linha escolhida.

    Raises:
        ValueError: se a tabela estiver vazia.
    """
    if not tabela:
        raise ValueError("tabela de combinações vazia")
    return min(
        tabela,
        key=lambda linha: (
            linha["falsos_passam_n"],
            -linha["entregue_certo"],
            linha["sinalizados"],
            linha["soma_sementes"],
        ),
    )


def _quadros_m11b() -> tuple[list[dict], dict[str, dict]]:
    """Quadros da M11b usados na escolha: os 28 do detector mais o q77 (braço "não").

    Desenvolvimento, não prova: a M11b já foi muito vista e só serve para escolher os pesos.

    Returns:
        ``(itens, registros)``: itens do ``indice.json`` da M11b e os registros do gabarito
        por id, na mesma ordem.

    Raises:
        ValueError: se algum quadro não estiver no índice ou no gabarito.
    """
    ids = (*QUADROS_PROVA, QUADRO_BRACO_NAO)
    indice = {
        item["id"]: item for item in _ler_json(MAOS_M11B / ARQUIVO_INDICE)["quadros"]
    }
    gabarito = _ler_json(GABARITO_BRACO_M11B)["quadros"]
    faltam = [i for i in ids if i not in indice or i not in gabarito]
    if faltam:
        raise ValueError(f"quadros da M11b fora do índice ou do gabarito: {faltam}")
    return [indice[i] for i in ids], {i: gabarito[i] for i in ids}


def avaliar_combinacao(
    estagio1: str, estagio2: str, itens: list[dict], registros: dict[str, dict]
) -> dict:
    """Mede uma combinação de pesos nos quadros da M11b (cadeia completa, GPU).

    Args:
        estagio1: nome do localizador (``L3_todos_s<k>``).
        estagio2: nome do detector (``A4_100_todos_s<k>``).
        itens: quadros da M11b (``indice.json``), na ordem da medida.
        registros: resposta do dono por id (``braco_m11b.json``).

    Returns:
        Uma linha da tabela: os pesos, a soma das sementes e os totais da medida.
    """
    previstos: dict[str, dict] = {}
    with _trava_gpu():
        loc = _carregar_localizador(estagio1)
        dois, _ = _carregar_pesos(estagio2, PASSOS)
        for item in itens:
            imagem = _imagem(MAOS_M11B / item["png"])
            resultado = cadeia(loc, dois, imagem, item["id"], conjunta=True)
            previstos[item["id"]] = previsto_do_resultado(
                item, resultado, sinalizado(resultado)
            )
    doc = {"ordem": [i["id"] for i in itens], "quadros": previstos}
    totais = medir_quadros(doc, {"quadros": registros}, RODADAS["1029"].proxima)[
        "totais"
    ]
    return {
        "estagio1": estagio1,
        "estagio2": estagio2,
        "soma_sementes": _semente(estagio1) + _semente(estagio2),
        "medidos": totais["medidos"],
        "falsos_passam_n": totais["falsos_passam_n"],
        "entregue_certo": totais["entregue_certo"],
        "sinalizados": totais["sinalizados"],
    }


def escolher_pesos(
    p2: bool, p3: bool, pasta: Path = MAOS_M29, com_a5: bool = False
) -> dict:
    """Escolhe os pesos da 1029 pela M11b e grava ``escolha_pesos.json`` (GPU).

    Sem nenhum L3 ou A4 em ``artefatos/m21``, cai para ``L2_todos_s1`` + ``A3_100_todos_s1``
    (os da 1026 e da 1027), sem rodar a GPU, e isso fica registrado no json.

    Args:
        p2: se o P2 (um braço só) entra no ciclo (decidido pelo dono com a 1028).
        p3: se o P3 (consenso S4) entra no ciclo.
        pasta: pasta da rodada, onde a escolha é gravada.
        com_a5: se os pesos A5 entram como candidatos do estágio 2 (rodada 1032).

    Returns:
        O conteúdo gravado: ``estagio1``, ``estagio2``, ``p2``, ``p3``, ``fonte``,
        ``criterio`` e ``tabela`` (uma linha por combinação avaliada).
    """
    combos = combinacoes_existentes(com_a5=True) if com_a5 else combinacoes_existentes()
    if not combos:
        escolha: dict = {
            "estagio1": ESTAGIO1,
            "estagio2": ESTAGIO2,
            "fonte": "fallback: nenhum L3/A4 existe; pesos da 1026/1027",
            "tabela": [],
        }
    else:
        itens, registros = _quadros_m11b()
        tabela = [avaliar_combinacao(l3, a4, itens, registros) for l3, a4 in combos]
        vencedora = escolher_combinacao(tabela)
        escolha = {
            "estagio1": vencedora["estagio1"],
            "estagio2": vencedora["estagio2"],
            "fonte": f"tabela M11b ({len(combos)} combinações)",
            "tabela": tabela,
        }
    escolha.update({"p2": bool(p2), "p3": bool(p3), "criterio": CRITERIO_ESCOLHA})
    pasta.mkdir(parents=True, exist_ok=True)
    gravar_atomico(pasta / ARQUIVO_ESCOLHA, escolha)
    return escolha


# ---------------------------------------------------------------------------------
# Medida (rodar só depois da revisão final do dono)
# ---------------------------------------------------------------------------------


def classe_do_quadro(previsto: dict, registro: dict) -> tuple[str, bool]:
    """Classe de um quadro previsto contra a resposta final do dono.

    Com braço ``nao`` do dono, achar é falso. Com braço ``sim`` ou ``parcial``, a
    classe é a de ``classificar`` contra ``marcas_do_registro``. Sem braço previsto,
    é ``nao_achou``.

    Args:
        previsto: entrada de ``previsto.json``.
        registro: resposta final do dono no gabarito (com ``braco`` e as marcas).

    Returns:
        ``(classe, correto)``. ``correto`` vale quando o veredito do braço está certo:
        ``nao`` do dono com braço não achado, ou classe ``certo``.
    """
    braco = registro["braco"]
    if braco == "nao":
        if previsto["achou"]:
            return "falso", False
        return "nao_achou", True
    alvo = marcas_do_registro(registro)
    if not previsto["achou"]:
        return "nao_achou", False
    try:
        medida = erros(marcas_do_previsto(previsto), alvo)
    except ValueError:
        return "erro", False
    classe = classificar(medida, True, braco)
    return classe, classe == "certo"


def criterio(
    falsos_passam: float | None, sinalizados: float | None, proxima: str
) -> str:
    """Ação pelo critério do pré-registro, com a ordem da tabela.

    Args:
        falsos_passam: falsos não sinalizados ÷ quadros medidos.
        sinalizados: sinalizados ÷ quadros medidos.
        proxima: rodada que retreina, se o ciclo funcionar (``"1027"`` na 1026).

    Returns:
        A ação da tabela "Critério para seguir para a rodada de retreino".
    """
    if falsos_passam is None or sinalizados is None:
        return "sem medida"
    if falsos_passam > LIMITE_FALSOS_CICLO:
        return "parar o ciclo: investigar por tipo de erro antes de qualquer retreino"
    if sinalizados > LIMITE_SINALIZADOS_CICLO:
        return (
            "ciclo seguro, mas caro: registrar e propor a melhora que mais reduz os "
            "sinalizados"
        )
    return (
        f"o ciclo funciona: a {proxima} retreina os estágios 1 e 2 com as marcas finais "
        "e mede de novo num lote novo"
    )


def medir_quadros(previsto_doc: dict, gabarito: dict, proxima: str) -> dict:
    """Mede a previsão contra o gabarito final do dono, quadro a quadro.

    Sai da medida (e vai para ``excluidos``, com o motivo): quadro sem registro,
    observação ``7 cordas``, braço sem resposta ou ``?``, e gabarito incompleto.

    Args:
        previsto_doc: conteúdo de ``previsto.json``.
        gabarito: gabarito final do dono (``braco_m26.json`` ou ``braco_m27.json``).
        proxima: rodada que vem depois (para a frase do critério).

    Returns:
        ``linhas`` (uma por quadro medido), ``excluidos``, ``totais`` e ``criterio``.
    """
    linhas: list[dict] = []
    excluidos: list[dict] = []
    for id_q in previsto_doc["ordem"]:
        previsto = previsto_doc["quadros"][id_q]
        registro = gabarito["quadros"].get(id_q)
        if registro is None:
            excluidos.append({"id": id_q, "motivo": "sem registro no gabarito"})
            continue
        if MARCA_SETE_CORDAS in (registro.get("obs") or ""):
            excluidos.append({"id": id_q, "motivo": MARCA_SETE_CORDAS})
            continue
        braco = registro.get("braco")
        if braco is None or braco == "?":
            excluidos.append({"id": id_q, "motivo": f"sem resposta (braco {braco})"})
            continue
        if braco in ("sim", "parcial") and marcas_do_registro(registro) is None:
            excluidos.append({"id": id_q, "motivo": "gabarito incompleto"})
            continue
        classe, correto = classe_do_quadro(previsto, registro)
        sinal = bool(previsto["sinalizado"])
        linhas.append(
            {
                "id": id_q,
                "arquivo": previsto["arquivo"],
                "braco": braco,
                "achou": previsto["achou"],
                "sinalizado": sinal,
                "classe": classe,
                "correto": correto,
                "sinalizado_ja_correto": sinal and correto,
            }
        )
    totais = _totais(linhas)
    totais["criterio"] = criterio(
        totais["falsos_passam"], totais["sinalizados_fracao"], proxima
    )
    return {"linhas": linhas, "excluidos": excluidos, "totais": totais}


def _totais(linhas: list[dict]) -> dict:
    """Totais da medida: entregue certo, falsos que passam e trabalho do dono.

    Args:
        linhas: uma por quadro medido.

    Returns:
        Contagens e frações (``None`` onde o denominador é zero).
    """
    medidos = len(linhas)
    com_braco = [linha for linha in linhas if linha["braco"] in ("sim", "parcial")]
    nao_sinalizados = [linha for linha in linhas if not linha["sinalizado"]]
    sinalizados = [linha for linha in linhas if linha["sinalizado"]]
    entregue_certo = sum(
        1
        for linha in nao_sinalizados
        if linha["braco"] in ("sim", "parcial") and linha["classe"] == "certo"
    )
    falsos = sum(1 for linha in nao_sinalizados if linha["classe"] == "falso")
    ja_certos = sum(1 for linha in sinalizados if linha["sinalizado_ja_correto"])
    por_classe: dict[str, int] = {}
    for linha in linhas:
        por_classe[linha["classe"]] = por_classe.get(linha["classe"], 0) + 1
    return {
        "medidos": medidos,
        "com_braco": len(com_braco),
        "nao_sinalizados": len(nao_sinalizados),
        "sinalizados": len(sinalizados),
        "entregue_certo": entregue_certo,
        "entregue_certo_fracao": _fracao(entregue_certo, len(com_braco)),
        "falsos_passam": _fracao(falsos, medidos),
        "falsos_passam_n": falsos,
        "sinalizados_fracao": _fracao(len(sinalizados), medidos),
        "sinalizados_ja_certos": ja_certos,
        "sinalizados_ja_certos_fracao": _fracao(ja_certos, len(sinalizados)),
        "por_classe": por_classe,
    }


def _fracao(parte: int, todo: int) -> float | None:
    """Fração ``parte / todo``, ou ``None`` se não houver denominador.

    Args:
        parte: numerador.
        todo: denominador.

    Returns:
        A fração, ou ``None``.
    """
    return None if todo == 0 else parte / todo


def medir_antigo(numero: str, previsto_doc: dict, gabarito: dict) -> dict:
    """Mede os pesos antigos (``L2_todos_s1`` + ``A3_100_todos_s1``) nos mesmos quadros (GPU).

    Sem P2 e sem P3: é a comparação pedida no pré-registro 1029 (o ganho do retreino num
    canal pouco visto). Grava ``previsto_antigo.json`` na pasta da rodada.

    Args:
        numero: rodada (chave de ``RODADAS``).
        previsto_doc: ``previsto.json`` da rodada (define a ordem dos quadros).
        gabarito: gabarito final do dono.

    Returns:
        ``{"pesos", "totais"}``: os pesos usados e os totais da medida.
    """
    rodada = RODADAS[numero]
    indice = _ler_json(rodada.pasta / ARQUIVO_INDICE)
    por_id = {item["id"]: item for item in indice["quadros"]}
    ordem = list(previsto_doc["ordem"])
    previstos = _prever_quadros(
        rodada.pasta,
        {"quadros": [por_id[id_q] for id_q in ordem]},
        ESTAGIO1,
        ESTAGIO2,
        False,
    )
    doc = {
        "formato": FORMATO_GABARITO,
        "semente": indice["semente"],
        "pesos": pesos_do_documento(Pesos(ESTAGIO1, ESTAGIO2)),
        "ordem": ordem,
        "quadros": previstos,
    }
    gravar_atomico(rodada.pasta / ARQUIVO_PREVISTO_ANTIGO, doc)
    medida = medir_quadros(doc, gabarito, rodada.proxima)
    return {"pesos": doc["pesos"], "totais": medida["totais"]}


def medir(numero: str = RODADA_PADRAO, comparar_antigo: bool = False) -> dict:
    """Compara ``previsto.json`` com o gabarito final e grava ``medida.json``.

    Args:
        numero: rodada (chave de ``RODADAS``).
        comparar_antigo: se True, mede também os pesos antigos nos mesmos quadros
            (``medir_antigo``, GPU) e grava o resultado em ``antigo``.

    Returns:
        O resultado gravado em ``medida.json``.

    Raises:
        ValueError: se o gabarito tiver formato errado.
    """
    rodada = RODADAS[numero]
    pasta = rodada.pasta
    previsto_doc = _ler_json(pasta / ARQUIVO_PREVISTO)
    gabarito = _ler_json(rodada.gabarito)
    if gabarito.get("formato") != FORMATO_GABARITO:
        raise ValueError(f"gabarito fora do formato {FORMATO_GABARITO}")
    resultado = medir_quadros(previsto_doc, gabarito, rodada.proxima)
    if comparar_antigo:
        resultado["antigo"] = medir_antigo(numero, previsto_doc, gabarito)
    gravar_atomico(pasta / ARQUIVO_MEDIDA, resultado)
    return resultado


# ---------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------


def main() -> int:
    """Ponto de entrada: ``sortear``, ``escolher-pesos``, ``prever`` e ``medir``.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    ajuda_rodada = "rodada do ciclo (padrão 1026)"
    for nome, ajuda in (
        ("sortear", "sorteia o lote e acrescenta os quadros"),
        ("escolher-pesos", "escolhe os pesos L3/A4 pela M11b (GPU; só 1029)"),
        ("prever", "roda a cadeia (GPU) e preenche o gabarito"),
        ("medir", "compara a previsão com o gabarito final do dono"),
    ):
        sp = sub.add_parser(nome, help=ajuda)
        sp.add_argument(
            "--rodada", choices=list(RODADAS), default=RODADA_PADRAO, help=ajuda_rodada
        )
        if nome == "escolher-pesos":
            sp.add_argument("--p2", action="store_true", help="liga o P2 (um braço só)")
            sp.add_argument("--p3", action="store_true", help="liga o P3 (consenso S4)")
        if nome == "medir":
            sp.add_argument(
                "--comparar-antigo",
                action="store_true",
                help="mede também os pesos antigos nos mesmos quadros (GPU)",
            )
    args = ap.parse_args()
    numero = args.rodada
    try:
        if args.comando == "sortear":
            ids = sortear(numero)
            print(f"sorteados {len(ids)} quadros: {', '.join(ids)}")
            return 0
        if args.comando == "escolher-pesos":
            if numero not in RODADAS_COM_ESCOLHA:
                raise ValueError(f"escolher-pesos só existe para {RODADAS_COM_ESCOLHA}")
            escolha = escolher_pesos(
                args.p2, args.p3, RODADAS[numero].pasta, numero in RODADAS_COM_A5
            )
            print(
                f"escolhidos {escolha['estagio1']} + {escolha['estagio2']} "
                f"(p2={escolha['p2']}, p3={escolha['p3']}); {escolha['fonte']}"
            )
            return 0
        if args.comando == "prever":
            sinalizados = prever(numero)
            previsto = _ler_json(RODADAS[numero].pasta / ARQUIVO_PREVISTO)["quadros"]
            achados = sum(1 for p in previsto.values() if p["achou"])
            print(
                f"previstos {len(sinalizados)}; com braço {achados}; "
                f"sinalizados {sum(sinalizados.values())}"
            )
            return 0
        resultado = medir(numero, comparar_antigo=args.comparar_antigo)
        totais = resultado["totais"]
        print(json.dumps(totais, ensure_ascii=False, indent=1))
        if "antigo" in resultado:
            print("antigo (L2_s1 + A3_s1, sem P2/P3):", file=sys.stderr)
            print(
                json.dumps(resultado["antigo"]["totais"], ensure_ascii=False, indent=1)
            )
        return 0
    except (ValueError, FileExistsError, FileNotFoundError, RuntimeError) as erro:
        print(f"não rodou: {erro}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
