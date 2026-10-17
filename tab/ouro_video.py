"""Ouro de vídeo: prepara o material e serve a ferramenta que GRAVA a cada clique.

Fase 2 / T2.1 + T2.2 do plano do produto. O ouro tem duas partes independentes:

1. **telas**: as telas distintas de tablatura do vídeo e, em cada uma, as notas
   (corda, casa, x). Mede a casa;
2. **instantes**: ~40 instantes sorteados onde há tablatura e, em cada um, qual coluna
   está acesa (ou "nenhuma", ou "sem tablatura"). Mede o tempo.

Por que a ferramenta grava a cada alteração: as 200 respostas da auditoria do pool se
perderam porque viveram só no navegador (CONTEXTO §18.2). Aqui o servidor escreve o
JSON do ouro em disco (atômico: arquivo temporário + ``os.replace``) a cada mudança, e a
página ainda tem um botão "baixar JSON" de reserva.

Coordenadas do JSON do ouro são SEMPRE do QUADRO. A conversão do clique na imagem
ampliada para o quadro é ``x_quadro = origem_x + x_img / escala``.

Convenção de x das notas: a nota pré-lida traz ``x_quadro`` = borda esquerda do token,
EXATAMENTE como o ``tab.transcrever`` (assim a régua compara igual com igual) e também
``x_centro_quadro``. A nota acrescentada por clique traz ``x_centro_quadro`` = o clique e
``x_quadro`` estimado = clique menos meia largura típica de algarismo.

Uso:
    python -m tab.ouro_video preparar VIDEO --saida data/saida/ouro_video/<slug>/
    python -m tab.ouro_video completar VIDEO --ouro-v1 data/gold/ouro_video/<slug>.json \
        --ouro-v2 data/gold/ouro_video/<slug>_v2.json --saida data/saida/ouro_video/<slug>_v2/
    python -m tab.ouro_video completar VIDEO --ouro-v2 data/gold/ouro_video/<slug>.json \
        --saida data/saida/ouro_video/<slug>/   # vídeo NOVO, sem ouro v1
    python -m tab.ouro_video servir --pasta data/saida/ouro_video/<slug>/ \
        --ouro data/gold/ouro_video/<slug>.json --porta 8099
"""

from __future__ import annotations

import argparse
import copy
import datetime
import http.server
import json
import math
import os
import random
import re
import sys
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import cv2
import numpy as np

from . import leitor
from . import telas as segmentacao
from .caminhos import MODELO_PADRAO, RAIZ, SAIDA, acervo
from .digito import carregar
from .esquema import MOTIVOS_COM_ATAQUE, MOTIVOS_SEM_ATAQUE, MOTIVOS_SEM_PAR
from .painel import PASSO_MAXIMO_PX, PASSO_MINIMO_PX, Candidato, escolher
from .reconhecer import ALGARISMOS, carregar_modelo, reconhecer_linha
from .tabseg import segmentar

#: Retângulo ``(x0, y0, x1, y1)`` no espaço do QUADRO.
Retangulo = tuple[int, int, int, int]

#: Ampliação das imagens de tela (o dono lê algarismo de ~20 px).
ESCALA_TELA = 2

#: Saturação HSV (0-255) a partir da qual o pixel é "colorido" = marcador, e fica de fora
#: da diferença entre quadros. MEDIDO no `retrato brasileiro`: o marcador é uma faixa azul
#: PÁLIDA (S ~ 40-80) mais o algarismo colorido; com o limite antigo (90) a faixa contava
#: como diferença e cada quadro virava uma tela. Fundo branco e tinta preta têm S < 10.
SATURACAO_MINIMA = 25

#: Painel de verdade tem fundo liso e pouco saturado: MEDIDO, a saturação mediana do
#: recorte é 3 na tablatura e 41-159 no braço do violão/vídeo, que o `painel.escolher`
#: também aceita (6 "linhas" = cordas). Acima disto o candidato não é painel. Limite
#: conhecido: um canal com fundo de tablatura colorido seria recusado.
SATURACAO_MEDIANA_MAXIMA = 25

#: Recorte quase preto (letterbox/tela preta) também é aceito pelo `painel.escolher` e
#: virou a "tela 1" de 46 s a 238 s no `retrato brasileiro`. Fundo de tablatura, claro ou
#: escuro, tem cinza mediano acima disto.
CINZA_MEDIANO_MINIMO = 20

#: Pixels coloridos são alargados em volta (antialiasing da borda do marcador).
DILATACAO_COLORIDO = 7

#: Abaixo desta fração de pixels não coloridos, o fundo todo é colorido: mede-se com todos
#: os pixels (errar para MAIS telas; o dono junta).
FRACAO_MINIMA_VALIDOS = 0.2

#: Limiar da diferença média absoluta (cinza, 0-255) entre um quadro e o quadro de
#: referência da tela. MEDIDO no `retrato brasileiro` (ver ESTADO.md, Fase 2 / T2.1).
LIMIAR_DIFERENCA = 2.0

#: Largura típica de um algarismo, em passos (mediana medida nas notas pré-lidas).
LARGURA_ALGARISMO_PASSOS = 0.5

#: Tolerância (px) para considerar que o painel "não mudou de lugar" entre quadros.
TOLERANCIA_RETANGULO = 6

#: Folga vertical (px) em volta do painel do ``tab.telas`` ao procurar o painel só na
#: faixa dele (``_candidato_na_faixa``): sem ela a escolha cai no braço do violão.
FOLGA_FAIXA_PX = 60

#: Folga (px) em volta de caixas que ficariam fora do painel da tela.
MARGEM_PAINEL_PX = 8

#: Técnicas que o dono pode marcar numa nota (código -> descrição). Convenção: h, p,
#: slide e ligada vão na nota de CHEGADA, a que não é atacada de novo; o símbolo é o que
#: está desenhado, não o que se ouve. Gabarito dos símbolos (Fase 10, item 1).
TECNICAS = {
    "h": "hammer-on",
    "p": "pull-off",
    "/": "slide subindo",
    "\\": "slide descendo",
    "lig": "ligada: arco, a nota continua soando",
    "(n)": "nota entre parênteses",
    "harm": "harmônico",
    "bend": "bend",
    "vib": "vibrato",
    "x": "abafada",
}

#: Técnicas de REGIÃO: marcas que cobrem várias cordas e/ou colunas (arrastar um
#: retângulo na página). Todas as de nota valem, mais as que só existem em região.
TECNICAS_REGIAO = {
    **TECNICAS,
    "arpejo": "arpejo (linha ondulada vertical)",
    "pestana": "pestana/barra (B, C, BIII...)",
    "rasg": "rasgueado/palhetada (setas)",
    "let ring": "deixar soar (let ring)",
    "pm": "palm mute (P.M.)",
    "trem": "trêmolo",
    "outra": "outra (descreva na observação)",
}

#: Páginas servidas: só estes tipos saem da pasta (nada de listar diretório).
_TIPOS = {".png": "image/png", ".json": "application/json; charset=utf-8"}


# ---------------------------------------------------------------------------------
# Funções puras: geometria e agrupamento
# ---------------------------------------------------------------------------------


def clique_para_quadro(x_img: float, escala: float, origem: float) -> float:
    """Converte uma coordenada na imagem ampliada para o espaço do QUADRO.

    Args:
        x_img: coordenada (px) na imagem como gravada em disco (não na tela).
        escala: ampliação com que a imagem foi gravada (2 para as telas).
        origem: coordenada do quadro em que a imagem começa (``recorte[0]``).

    Returns:
        A coordenada no quadro.
    """
    return origem + x_img / escala


def corda_mais_proxima(y_quadro: float, linhas_y: list[float]) -> int:
    """Corda (1 = aguda, de cima) cuja linha está mais perto de ``y_quadro``.

    Args:
        y_quadro: ordenada no quadro.
        linhas_y: ordenadas das 6 linhas, no quadro, de cima para baixo.

    Returns:
        Número da corda, de 1 a ``len(linhas_y)``.
    """
    melhor = min(range(len(linhas_y)), key=lambda k: abs(linhas_y[k] - y_quadro))
    return melhor + 1


def recortar(quadro: np.ndarray, rect: Retangulo) -> np.ndarray:
    """Recorte do quadro, com o retângulo limitado às bordas.

    Args:
        quadro: imagem BGR.
        rect: ``(x0, y0, x1, y1)``.

    Returns:
        A vista recortada.
    """
    x0, y0, x1, y1 = rect
    altura, largura = quadro.shape[:2]
    return quadro[max(0, y0) : min(altura, y1), max(0, x0) : min(largura, x1)]


def mascara_colorida(bgr: np.ndarray) -> np.ndarray:
    """Pixels coloridos (saturação alta = marcador), alargados em volta.

    Args:
        bgr: recorte BGR.

    Returns:
        Máscara booleana, ``True`` onde há cor.
    """
    saturacao = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1]
    cor = (saturacao > SATURACAO_MINIMA).astype(np.uint8)
    kernel = np.ones((DILATACAO_COLORIDO, DILATACAO_COLORIDO), np.uint8)
    return cv2.dilate(cor, kernel) > 0


def diferenca_cinza(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Diferença média absoluta em cinza, IGNORANDO pixels coloridos de qualquer lado.

    Medida simples e independente do sistema que vai ser testado: não usa o cursor, o
    estado nem o classificador. Um marcador colorido andando por cima não muda a tela.

    Args:
        a: recorte BGR.
        b: recorte BGR do mesmo tamanho.

    Returns:
        ``(diferenca, fracao_colorida_de_a)``; a diferença é 255 se os tamanhos diferem.
    """
    if a.shape != b.shape:
        return 255.0, 0.0
    colorido_a = mascara_colorida(a)
    validos = ~(colorido_a | mascara_colorida(b))
    if validos.mean() < FRACAO_MINIMA_VALIDOS:
        validos = np.ones_like(validos)
    cinza_a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.int16)
    cinza_b = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.int16)
    dif = np.abs(cinza_a - cinza_b)[validos]
    return float(dif.mean()), float(colorido_a.mean())


def mesmo_retangulo(
    a: Retangulo, b: Retangulo, tol: int = TOLERANCIA_RETANGULO
) -> bool:
    """Os dois retângulos coincidem dentro da tolerância?

    Args:
        a: primeiro retângulo.
        b: segundo retângulo.
        tol: folga, em px, em cada coordenada.

    Returns:
        ``True`` se o painel não mudou de lugar.
    """
    return all(abs(p - q) <= tol for p, q in zip(a, b, strict=True))


@dataclass
class TelaAgrupada:
    """Uma tela distinta: do primeiro ao último quadro que a mostram."""

    id: int
    rect: Retangulo
    ref: np.ndarray
    t_ini: float
    t_fim: float
    carga0: object = None
    melhor_t: float = 0.0
    melhor_colorido: float = 2.0
    melhor_quadro: np.ndarray | None = None
    n_quadros: int = 1
    diferencas: list[float] = field(default_factory=list)


class Agrupador:
    """Agrupa quadros consecutivos "iguais" em telas, sem depender do sistema testado.

    Cada quadro é comparado ao quadro de REFERÊNCIA da tela atual (o primeiro dela), e
    não ao quadro anterior: um desvanecer lento não escapa em passos pequenos. Se a
    tablatura some e volta igual, a tela é a mesma (a comparação é com a última tela).

    Args:
        limiar: diferença média absoluta (cinza) acima da qual a tela é outra.
        detectar: ``quadro -> (retangulo, carga) | None``; só é chamado quando o quadro
            NÃO é igual à tela atual (é o passo caro: ``painel.escolher``).
        ao_fechar: chamado com a tela quando ela é substituída por outra (e em
            ``encerrar``); depois disso o quadro guardado é liberado.
    """

    def __init__(
        self,
        limiar: float,
        detectar: Callable[[np.ndarray], tuple[Retangulo, object] | None],
        ao_fechar: Callable[[TelaAgrupada], None] | None = None,
    ) -> None:
        """Cria o agrupador vazio."""
        self.limiar = limiar
        self.detectar = detectar
        self.ao_fechar = ao_fechar
        self.telas: list[TelaAgrupada] = []
        self.atual: TelaAgrupada | None = None
        self.diferencas: list[float] = []

    def alimentar(self, t: float, quadro: np.ndarray) -> int | None:
        """Consome um quadro.

        Args:
            t: instante, em segundos.
            quadro: quadro BGR inteiro.

        Returns:
            O id da tela mostrada, ou ``None`` se não há tablatura no quadro.
        """
        ref = self.atual
        if ref is not None:
            recorte = recortar(quadro, ref.rect)
            dif, colorido = diferenca_cinza(recorte, ref.ref)
            self.diferencas.append(dif)
            ref.diferencas.append(dif)
            if dif <= self.limiar:
                ref.t_fim = t
                ref.n_quadros += 1
                if colorido < ref.melhor_colorido:
                    ref.melhor_t, ref.melhor_colorido = t, colorido
                    ref.melhor_quadro = quadro.copy()
                return ref.id
        achado = self.detectar(quadro)
        if achado is None:
            return None
        rect, carga = achado
        if ref is not None:
            self._fechar(ref)
        nova = TelaAgrupada(
            id=len(self.telas) + 1,
            rect=rect,
            ref=recortar(quadro, rect).copy(),
            t_ini=t,
            t_fim=t,
            carga0=carga,
            melhor_t=t,
            melhor_colorido=float(mascara_colorida(recortar(quadro, rect)).mean()),
            melhor_quadro=quadro.copy(),
        )
        self.telas.append(nova)
        self.atual = nova
        return nova.id

    def encerrar(self) -> None:
        """Fecha a última tela (chame ao fim do vídeo)."""
        if self.atual is not None:
            self._fechar(self.atual)
            self.atual = None

    def _fechar(self, tela: TelaAgrupada) -> None:
        """Entrega a tela ao ``ao_fechar`` e libera o quadro guardado."""
        if self.ao_fechar is not None:
            self.ao_fechar(tela)
        tela.melhor_quadro = None


def agrupar_telas(
    amostras: list[tuple[float, np.ndarray]],
    limiar: float,
    rect: Retangulo,
) -> list[int | None]:
    """Atalho puro: ids de tela por quadro, com o painel fixo em ``rect``.

    Um quadro "tem tablatura" se o recorte não é uniformemente escuro-zero; serve para
    testar o agrupamento sem o detector de painel.

    Args:
        amostras: ``[(t, quadro)]`` em ordem de tempo; ``quadro`` ``None`` = ausente.
        limiar: ver ``Agrupador``.
        rect: onde está o painel.

    Returns:
        Uma lista de ids (ou ``None``) do mesmo tamanho de ``amostras``.
    """

    def detectar(quadro: np.ndarray) -> tuple[Retangulo, object] | None:
        return (rect, None) if recortar(quadro, rect).max() > 0 else None

    agrupador = Agrupador(limiar, detectar)
    return [agrupador.alimentar(t, q) for t, q in amostras]


def sortear_instantes(
    tela_por_quadro: list[int | None], passo_s: float, n: int, seed: int
) -> list[tuple[float, int]]:
    """Sorteia instantes DENTRO dos trechos com tablatura e os EMBARALHA com a semente.

    Args:
        tela_por_quadro: tela de cada quadro amostrado (``None`` = sem tablatura).
        passo_s: intervalo entre quadros, em segundos.
        n: quantos instantes (menos, se houver poucos quadros com tablatura).
        seed: semente do sorteio e do embaralhamento.

    Returns:
        ``[(t, tela)]`` na ordem EMBARALHADA em que o dono verá os instantes.
    """
    presentes = [k for k, tela in enumerate(tela_por_quadro) if tela is not None]
    rng = random.Random(seed)
    escolhidos = rng.sample(presentes, min(n, len(presentes)))
    rng.shuffle(escolhidos)
    return [(round(k * passo_s, 3), tela_por_quadro[k]) for k in escolhidos]


def histograma(valores: list[float]) -> dict[str, int]:
    """Histograma em bins fixos (a distribuição que justifica o limiar).

    Args:
        valores: diferenças medidas.

    Returns:
        ``{"[a,b)": contagem}`` em ordem crescente.
    """
    bordas = [0, 0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 32, 64, 256]
    contagens, _ = np.histogram(valores, bins=bordas)
    return {f"[{bordas[i]},{bordas[i + 1]})": int(c) for i, c in enumerate(contagens)}


# ---------------------------------------------------------------------------------
# Montagem e validação do JSON do ouro
# ---------------------------------------------------------------------------------


def _numero(valor: object) -> bool:
    """``True`` se for número de verdade (``bool`` não conta)."""
    return isinstance(valor, int | float) and not isinstance(valor, bool)


def validar_ouro(ouro: dict) -> list[str]:
    """Confere o formato do plano; devolve a lista de problemas (vazia = válido).

    Args:
        ouro: o dicionário do ouro.

    Returns:
        Mensagens de problema, uma por violação.
    """
    erros: list[str] = []
    if not isinstance(ouro.get("video"), str) or not ouro.get("video"):
        erros.append("video ausente")
    if not ouro.get("como_foi_rotulado"):
        erros.append("como_foi_rotulado ausente")
    ids: set[int] = set()
    for tela in ouro.get("telas") or []:
        if not isinstance(tela.get("id"), int) or tela["id"] in ids:
            erros.append(f"id de tela inválido ou repetido: {tela.get('id')!r}")
            continue
        ids.add(tela["id"])
        if not _numero(tela.get("quadro_ref_s")):
            erros.append(f"tela {tela['id']}: quadro_ref_s inválido")
        for nota in tela.get("notas") or []:
            corda, casa = nota.get("corda"), nota.get("casa")
            if not isinstance(corda, int) or not 1 <= corda <= 6:
                erros.append(f"tela {tela['id']}: corda inválida {corda!r}")
            if not (isinstance(casa, int) and not isinstance(casa, bool)) and not (
                isinstance(casa, str) and casa
            ):
                erros.append(f"tela {tela['id']}: casa inválida {casa!r}")
            if not _numero(nota.get("x_quadro")):
                erros.append(f"tela {tela['id']}: x_quadro inválido")
            tecnica = nota.get("tecnica", [])
            if not isinstance(tecnica, list) or not set(tecnica) <= TECNICAS.keys():
                erros.append(f"tela {tela['id']}: técnica inválida {tecnica!r}")
        for regiao in tela.get("regioes") or []:
            cordas = regiao.get("cordas")
            if not (
                isinstance(cordas, list)
                and len(cordas) == 2
                and all(isinstance(c, int) and 1 <= c <= 6 for c in cordas)
            ):
                erros.append(
                    f"tela {tela['id']}: região com cordas inválidas {cordas!r}"
                )
            tecnica = regiao.get("tecnica", [])
            if (
                not isinstance(tecnica, list)
                or not set(tecnica) <= TECNICAS_REGIAO.keys()
            ):
                erros.append(
                    f"tela {tela['id']}: técnica de região inválida {tecnica!r}"
                )
    for inst in ouro.get("instantes") or []:
        if not _numero(inst.get("t")):
            erros.append("instante com t inválido")
        if inst.get("tela") is not None and inst["tela"] not in ids:
            erros.append(f"instante t={inst.get('t')}: tela {inst['tela']} não existe")
        coluna = inst.get("coluna_x_quadro")
        if coluna is not None and not _numero(coluna):
            erros.append(f"instante t={inst.get('t')}: coluna_x_quadro inválida")
    return erros


def _casa(texto: object) -> int | str | None:
    """Casa digitada: inteiro se for dígito, texto se for outro (ex.: ``x``), senão None."""
    if texto is None:
        return None
    limpo = str(texto).strip()
    if not limpo:
        return None
    return int(limpo) if limpo.isdigit() else limpo


def _raiz_da_juncao(juntadas: dict[int, int], id_: int) -> int:
    """Segue ``igual a`` até a tela que fica (com guarda contra ciclo)."""
    visto = {id_}
    while id_ in juntadas and juntadas[id_] not in visto:
        id_ = juntadas[id_]
        visto.add(id_)
    return id_


def _confirmacao(instante: dict) -> dict:
    """Campos do v2 do instante (``tela_confirmada``, ``pagina_sugerida``), se houver."""
    if "tela_confirmada" not in instante:
        return {}
    campos = {"tela_confirmada": bool(instante["tela_confirmada"])}
    if "pagina_sugerida" in instante:
        campos["pagina_sugerida"] = bool(instante["pagina_sugerida"])
    return campos


def montar_ouro(
    pre: dict,
    estado: dict,
    agora: str | None = None,
    como_foi_rotulado: str | None = None,
) -> dict:
    """Monta o JSON do ouro (formato do plano) a partir do estado da ferramenta.

    Notas removidas ("não é nota") e notas SEM casa não entram. Telas marcadas "igual a
    outra" não entram, e os instantes delas passam à tela que fica. Um instante com
    coluna e sem tela recebe a tela cujo ``quadro_ref_s`` é o mais próximo no tempo.
    O estado completo vai junto em ``ferramenta`` (para retomar o trabalho).

    Args:
        pre: o ``pre.json`` da pasta.
        estado: o estado da página (``telas``, ``instantes``, ...).
        agora: carimbo de tempo (para teste); padrão, agora.
        como_foi_rotulado: texto a manter (ex.: o do ouro gravado, com acréscimos do
            dono); padrão, o do ``pre.json``.

    Returns:
        O dicionário do ouro, já validado.

    Raises:
        ValueError: se o resultado violar o formato.
    """
    ref_s = {t["id"]: t["quadro_ref_s"] for t in pre["telas"]}
    juntadas = {
        int(t["id"]): int(t["junta_em"])
        for t in estado.get("telas", [])
        if t.get("junta_em")
    }
    telas = []
    for t in estado.get("telas", []):
        if t["id"] in juntadas:
            continue
        notas = []
        for n in t.get("notas", []):
            casa = _casa(n.get("casa"))
            if n.get("removida") or casa is None:
                continue
            nota = {
                "corda": int(n["corda"]),
                "casa": casa,
                "x_quadro": round(float(n["x_quadro"]), 1),
            }
            if n.get("x_centro_quadro") is not None:
                nota["x_centro_quadro"] = round(float(n["x_centro_quadro"]), 1)
            marcadas = set(n.get("tecnica") or [])
            if marcadas:
                nota["tecnica"] = [k for k in TECNICAS if k in marcadas]
            notas.append(nota)
        notas.sort(key=lambda n: (n["x_quadro"], n["corda"]))
        regioes = []
        for r in t.get("regioes", []):
            marcadas = set(r.get("tecnica") or [])
            obs = str(r.get("obs") or "").strip()
            if not marcadas and not obs:
                continue
            regiao = {
                "cordas": sorted([int(r["corda_ini"]), int(r["corda_fim"])]),
                "x_quadro": sorted(
                    [round(float(r["x0"]), 1), round(float(r["x1"]), 1)]
                ),
                "tecnica": [k for k in TECNICAS_REGIAO if k in marcadas],
            }
            if obs:
                regiao["obs"] = obs
            regioes.append(regiao)
        regioes.sort(key=lambda r: (r["x_quadro"][0], r["cordas"][0]))
        tela = {
            "id": int(t["id"]),
            "quadro_ref_s": ref_s[t["id"]],
            "conferida": bool(t.get("conferida")),
            "notas": notas,
        }
        if regioes:
            tela["regioes"] = regioes
        if t.get("origem"):
            tela["origem"] = t["origem"]
            tela["v1_telas"] = t.get("v1_telas") or []
        telas.append(tela)
    ids = {t["id"] for t in telas}
    instantes = []
    for i in estado.get("instantes", []):
        situacao = i.get("estado")
        if situacao is None:
            continue
        if situacao == "sem_tablatura":
            instantes.append(
                {
                    "t": i["t"],
                    "tela": None,
                    "coluna_x_quadro": None,
                    "obs": "sem tablatura",
                    **_confirmacao(i),
                }
            )
            continue
        tela = i.get("tela")
        if tela is not None:
            tela = _raiz_da_juncao(juntadas, int(tela))
        elif ids and situacao == "coluna":
            tela = min(ids, key=lambda k: abs(ref_s[k] - i["t"]))
        item = {
            "t": i["t"],
            "tela": tela,
            "coluna_x_quadro": None
            if situacao == "nenhuma"
            else round(float(i["coluna_x_quadro"]), 1),
            "obs": "nenhuma acesa" if situacao == "nenhuma" else i.get("obs", ""),
            **_confirmacao(i),
        }
        instantes.append(item)
    instantes.sort(key=lambda i: i["t"])
    ouro = {
        "video": pre["video"],
        "como_foi_rotulado": como_foi_rotulado
        or pre.get("como_foi_rotulado")
        or (
            f"pre-preenchido pelo modelo {pre['modelo']}; conferido e corrigido "
            "pelo dono por leitura visual"
        ),
        "rotulado_em": agora or datetime.datetime.now().isoformat(timespec="seconds"),
        "telas": telas,
        "instantes": instantes,
        "juntadas": {str(k): v for k, v in sorted(juntadas.items())},
        "ferramenta": estado,
    }
    erros = validar_ouro(ouro)
    if erros:
        raise ValueError("; ".join(erros[:5]))
    return ouro


def gravar_atomico(destino: Path, conteudo: dict) -> None:
    """Grava JSON de forma atômica: temporário no mesmo diretório + ``os.replace``.

    Args:
        destino: arquivo final.
        conteudo: dicionário serializável.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, destino)


def _notas_sem_par(a: list[dict], b: list[dict]) -> list[dict]:
    """Notas de ``a`` que não têm uma igual em ``b`` (contando repetições).

    Args:
        a: notas a percorrer.
        b: notas em que procurar o par.

    Returns:
        As notas de ``a`` sem par, na ordem de ``a``.
    """
    restantes = [json.dumps(n, sort_keys=True) for n in b]
    sem_par = []
    for n in a:
        chave = json.dumps(n, sort_keys=True)
        if chave in restantes:
            restantes.remove(chave)
        else:
            sem_par.append(n)
    return sem_par


def _rotulo_nota(nota: dict) -> str:
    """Nota como ``(corda, casa, x_centro_quadro)`` (ou ``x_quadro`` se não há centro)."""
    x = nota.get("x_centro_quadro", nota.get("x_quadro"))
    return f"({nota['corda']}, {nota['casa']}, {x})"


def divergencias_do_estado(pre: dict, ouro: dict) -> list[str]:
    """Diferenças entre o ouro gravado e o que a ferramenta remontaria a partir do estado.

    O ouro é refeito com ``montar_ouro`` a partir de ``ouro["ferramenta"]``; se as telas,
    os instantes ou as juntadas do arquivo não baterem com isso, a primeira gravação da
    ferramenta desfaria as edições feitas fora dela. ``como_foi_rotulado`` não entra na
    comparação.

    Args:
        pre: o ``pre.json`` da pasta.
        ouro: o ouro gravado em disco.

    Returns:
        Uma linha por diferença (id da tela e o que difere); lista vazia = coerente, ou
        sem bloco ``ferramenta`` para comparar.
    """
    if "ferramenta" not in ouro:
        return []
    try:
        montado = montar_ouro(pre, ouro["ferramenta"], agora=ouro.get("rotulado_em"))
    except ValueError as erro:
        return [f"o estado da ferramenta não monta um ouro válido: {erro}"]
    linhas: list[str] = []
    telas_ouro = {t["id"]: t for t in ouro.get("telas") or []}
    telas_estado = {t["id"]: t for t in montado["telas"]}
    for id_ in sorted(set(telas_ouro) | set(telas_estado)):
        if id_ not in telas_estado:
            linhas.append(f"tela {id_}: existe só no ouro gravado")
            continue
        if id_ not in telas_ouro:
            linhas.append(f"tela {id_}: existe só no estado da ferramenta")
            continue
        a, b = telas_ouro[id_], telas_estado[id_]
        if bool(a.get("conferida")) != bool(b.get("conferida")):
            linhas.append(
                f"tela {id_}: conferida difere (ouro={a.get('conferida')}, "
                f"estado={b.get('conferida')})"
            )
        for nota in _notas_sem_par(a.get("notas") or [], b["notas"]):
            linhas.append(f"tela {id_}: nota a mais no ouro {_rotulo_nota(nota)}")
        for nota in _notas_sem_par(b["notas"], a.get("notas") or []):
            linhas.append(f"tela {id_}: nota a menos no ouro {_rotulo_nota(nota)}")
        for campo in sorted((set(a) | set(b)) - {"id", "conferida", "notas"}):
            if a.get(campo) != b.get(campo):
                linhas.append(f"tela {id_}: campo '{campo}' difere do estado")
    instantes_ouro = {i["t"]: i for i in ouro.get("instantes") or []}
    instantes_estado = {i["t"]: i for i in montado["instantes"]}
    for t in sorted(set(instantes_ouro) | set(instantes_estado)):
        if t not in instantes_estado:
            linhas.append(f"instante t={t}: existe só no ouro gravado")
        elif t not in instantes_ouro:
            linhas.append(f"instante t={t}: existe só no estado da ferramenta")
        elif instantes_ouro[t] != instantes_estado[t]:
            linhas.append(f"instante t={t}: difere do estado da ferramenta")
    if (ouro.get("juntadas") or {}) != montado["juntadas"]:
        linhas.append(
            f"juntadas diferem (ouro={ouro.get('juntadas')}, "
            f"estado={montado['juntadas']})"
        )
    return linhas


# ---------------------------------------------------------------------------------
# Ouro v2: páginas do tab.telas + notas herdadas do ouro v1 (decisão do dono)
# ---------------------------------------------------------------------------------

#: Tolerância (px, no quadro) em x para duas notas rotuladas serem "a mesma nota".
TOLERANCIA_X_NOTA_PX = 6.0

#: Passo (px) usado só se a página não traz o dela (para a caixa de nota sem caixa).
PASSO_PADRAO_PX = 20.0

#: Folga (s) em volta de uma exibição para tratar a tela v1 como "na borda": o tempo do
#: ``quadro_ref_s`` do v1 (``leitor.quadros``) difere do do ``tab.telas`` (``quadro_em``) em
#: ~0,25 s (ESTADO.md, Fase 3) e MEDIDO aqui até 0,75 s (tela v1 4: ref 406,0 mostra a página
#: que começa em 406,75). Quem decide entre as candidatas são as notas, não o tempo.
FOLGA_BORDA_S = 1.5

ORIGEM_V1 = "ouro_v1 (dono)"
ORIGEM_MODELO = "modelo — a rotular"


def pagina_em(paginas: list[dict], t: float) -> int | None:
    """Id da página cuja exibição contém ``t`` (``None`` se nenhuma).

    Args:
        paginas: páginas com ``id`` e ``exibicoes`` (lista de ``[t0, t1]``).
        t: instante, em segundos.

    Returns:
        O id da página, ou ``None``.
    """
    for p in paginas:
        for t0, t1 in p["exibicoes"]:
            if t0 <= t < t1:
                return int(p["id"])
    return None


def comparar_notas(
    a: list[dict], b: list[dict], tol_x: float = TOLERANCIA_X_NOTA_PX
) -> dict:
    """Compara duas listas de notas rotuladas (mesma corda, casa e x dentro de ``tol_x``).

    Args:
        a: notas (``corda``, ``casa``, ``x_quadro``).
        b: notas a comparar com ``a``.
        tol_x: tolerância de x, em px.

    Returns:
        ``{"iguais": n, "so_a": [...], "so_b": [...]}``, notas como ``(corda, casa, x)``.
    """
    restantes = list(b)
    so_a, iguais = [], 0
    for n in sorted(a, key=lambda n: (n["x_quadro"], n["corda"])):
        achou = None
        for m in restantes:
            if (
                m["corda"] == n["corda"]
                and str(m["casa"]) == str(n["casa"])
                and abs(float(m["x_quadro"]) - float(n["x_quadro"])) <= tol_x
            ):
                achou = m
                break
        if achou is None:
            so_a.append((n["corda"], str(n["casa"]), round(float(n["x_quadro"]), 1)))
        else:
            restantes.remove(achou)
            iguais += 1
    so_b = [
        (m["corda"], str(m["casa"]), round(float(m["x_quadro"]), 1)) for m in restantes
    ]
    return {"iguais": iguais, "so_a": so_a, "so_b": so_b}


def _notas_herdadas(
    ouro_v1: dict, tela_v1: dict, pagina: dict, prefixo: str
) -> list[dict]:
    """Notas do ouro v1 no formato de estado da ferramenta (com caixa, se o v1 a tem).

    Args:
        ouro_v1: o ouro v1 inteiro (``ferramenta`` dá caixa e origem da nota).
        tela_v1: a tela do v1 de onde copiar.
        pagina: a página nova (dá o passo, se faltar caixa).
        prefixo: prefixo dos ids das notas copiadas.

    Returns:
        Notas do estado (``removida`` falso), em ordem de x.
    """
    ferr = next(
        (
            t
            for t in (ouro_v1.get("ferramenta") or {}).get("telas", [])
            if t["id"] == tela_v1["id"]
        ),
        {},
    )
    por_chave = {
        (n["corda"], round(float(n["x_quadro"]), 1)): n
        for n in ferr.get("notas", [])
        if not n.get("removida")
    }
    passo = float(pagina.get("passo") or PASSO_PADRAO_PX)
    notas = []
    for i, n in enumerate(tela_v1["notas"]):
        fn = por_chave.get((n["corda"], round(float(n["x_quadro"]), 1)), {})
        centro = n.get("x_centro_quadro", fn.get("x_centro_quadro"))
        if centro is None:
            centro = float(n["x_quadro"]) + 0.25 * passo
        nota = {
            "id": f"{prefixo}{i}",
            "corda": int(n["corda"]),
            "casa": str(n["casa"]),
            "x_quadro": n["x_quadro"],
            "x_centro_quadro": centro,
            "origem": fn.get("origem", "dono"),
            "removida": False,
        }
        if fn.get("caixa"):
            nota["caixa"] = list(fn["caixa"])
        notas.append(nota)
    notas.sort(key=lambda n: (n["x_quadro"], n["corda"]))
    return notas


def _estado_do_instante(i: dict) -> str:
    """Estado do instante do ouro (``coluna``, ``nenhuma`` ou ``sem_tablatura``)."""
    if i.get("coluna_x_quadro") is not None:
        return "coluna"
    if i.get("tela") is None:
        return "sem_tablatura"
    return "nenhuma"


def pagina_do_quadro_ref(paginas: list[dict], tela_v1: dict) -> tuple[int | None, dict]:
    """Página de uma tela do v1, desempatando as de borda pelas notas.

    O ``quadro_ref_s`` do v1 vem de ``leitor.quadros`` e a troca de página do ``tab.telas``
    de ``leitor.quadro_em``; as duas leituras diferem ~0,25 s (ESTADO.md, Fase 3). Perto da
    troca (até ``FOLGA_BORDA_S``) mais de uma página é candidata: fica a cuja leitura do
    modelo mais CONCORDA com as notas do dono (empate: a que contém o instante).

    Args:
        paginas: páginas com ``exibicoes`` e ``notas`` do modelo.
        tela_v1: tela do v1 (``quadro_ref_s`` e ``notas``).

    Returns:
        ``(id da página ou None, {})`` ou, se houve desempate, ``(id, detalhe)`` com os
        candidatos e as concordâncias.
    """
    ref = float(tela_v1["quadro_ref_s"])
    dentro = pagina_em(paginas, ref)
    candidatas = [
        int(p["id"])
        for p in paginas
        if any(
            t0 - FOLGA_BORDA_S <= ref < t1 + FOLGA_BORDA_S for t0, t1 in p["exibicoes"]
        )
    ]
    if len(candidatas) <= 1:
        return (candidatas[0] if candidatas else dentro), {}
    por_id = {int(p["id"]): p for p in paginas}
    pontos = {
        k: comparar_notas(tela_v1["notas"], por_id[k]["notas"])["iguais"]
        for k in candidatas
    }
    melhor = max(candidatas, key=lambda k: (pontos[k], k == dentro))
    detalhe = {"contem_o_instante": dentro, "iguais_com_o_modelo": pontos}
    return melhor, detalhe


def _tela_do_modelo(pagina: dict) -> dict:
    """Tela do estado com as notas do modelo, a rotular (``conferida`` falso).

    Args:
        pagina: página com ``id`` e ``notas`` do modelo.

    Returns:
        A tela no formato do estado da ferramenta, origem ``ORIGEM_MODELO``.
    """
    notas = [
        {
            "id": f"m{i}",
            "corda": n["corda"],
            "casa": str(n["casa"]),
            "x_quadro": n["x_quadro"],
            "x_centro_quadro": n.get("x_centro_quadro"),
            "origem": "modelo",
            "removida": False,
            "caixa": n.get("caixa"),
        }
        for i, n in enumerate(pagina["notas"])
    ]
    return {
        "id": int(pagina["id"]),
        "conferida": False,
        "junta_em": None,
        "origem": ORIGEM_MODELO,
        "v1_telas": [],
        "notas": notas,
    }


def fundir_ouro(ouro_v1: dict, paginas: list[dict]) -> tuple[dict, dict]:
    """Funde o ouro v1 com as páginas do ``tab.telas``: o estado da ferramenta do v2.

    Regras (decisão do dono): a tela v1 cujo ``quadro_ref_s`` cai numa exibição da página
    dá as notas à página (``conferida``). Se mais de uma tela v1 cai na mesma página, usa-se
    a de ``quadro_ref_s`` mais próximo do da página e as outras só são COMPARADAS: a
    divergência vai para ``conflitos`` (não se resolve sozinho). Página sem tela v1 fica
    com as notas do modelo (``paginas[i]["notas"]``), a rotular. Os instantes mantêm
    ``t``, coluna e obs do dono; a ``tela`` passa a ser a página cuja exibição contém ``t``,
    com ``tela_confirmada`` falso.

    Args:
        ouro_v1: o ouro v1 (não é alterado).
        paginas: páginas com ``id``, ``exibicoes``, ``quadro_ref_s`` e ``notas`` do modelo
            (com ``corda``, ``casa``, ``x_quadro``, ``x_centro_quadro``, ``caixa``).

    Returns:
        ``(estado, relatorio)``; ``estado`` é o da ferramenta (``telas``, ``instantes``...).
    """
    tela_v1_por_id = {int(t["id"]): t for t in ouro_v1["telas"]}
    do_v1: dict[int, list[int]] = {}
    v1_sem_pagina = []
    pagina_do_v1 = {}
    ambiguas = []
    for t in ouro_v1["telas"]:
        pid, ambigua = pagina_do_quadro_ref(paginas, t)
        if ambigua:
            ambiguas.append({"tela_v1": int(t["id"]), "pagina": pid, **ambigua})
        pagina_do_v1[int(t["id"])] = pid
        if pid is None:
            v1_sem_pagina.append(int(t["id"]))
        else:
            do_v1.setdefault(pid, []).append(int(t["id"]))
    telas, conflitos, herdadas = [], [], []
    for p in paginas:
        candidatas = do_v1.get(int(p["id"]), [])
        if not candidatas:
            telas.append(_tela_do_modelo(p))
            continue
        usada = min(
            candidatas,
            key=lambda k: (
                abs(
                    float(tela_v1_por_id[k]["quadro_ref_s"]) - float(p["quadro_ref_s"])
                ),
                k,
            ),
        )
        for outra in candidatas:
            if outra == usada:
                continue
            cmp = comparar_notas(
                tela_v1_por_id[usada]["notas"], tela_v1_por_id[outra]["notas"]
            )
            if cmp["so_a"] or cmp["so_b"]:
                conflitos.append(
                    {
                        "pagina": int(p["id"]),
                        "usada_v1": usada,
                        "outra_v1": outra,
                        "iguais": cmp["iguais"],
                        "so_na_usada": cmp["so_a"],
                        "so_na_outra": cmp["so_b"],
                    }
                )
        herdadas.append(int(p["id"]))
        em_conflito = any(c["pagina"] == int(p["id"]) for c in conflitos)
        telas.append(
            {
                "id": int(p["id"]),
                "conferida": not em_conflito,  # conflito: o dono decide, não eu
                "junta_em": None,
                "origem": ORIGEM_V1,
                "v1_telas": candidatas,
                "v1_usada": usada,
                "notas": _notas_herdadas(
                    ouro_v1, tela_v1_por_id[usada], p, f"h{int(p['id'])}_"
                ),
            }
        )
    instantes, reatribuidos, sem_pagina = [], [], []
    for i in sorted(ouro_v1["instantes"], key=lambda i: i["t"]):
        estado = _estado_do_instante(i)
        pagina = (
            None if estado == "sem_tablatura" else pagina_em(paginas, float(i["t"]))
        )
        if estado != "sem_tablatura" and pagina is None:
            sem_pagina.append(i["t"])
        v1 = i.get("tela")
        if estado != "sem_tablatura" and pagina_do_v1.get(v1) != pagina:
            reatribuidos.append({"t": i["t"], "tela_v1": v1, "pagina": pagina})
        instantes.append(
            {
                "t": i["t"],
                "estado": estado,
                "tela": pagina,
                "tela_v1": v1,
                "coluna_x_quadro": i.get("coluna_x_quadro"),
                "obs": i.get("obs", ""),
                "tela_confirmada": False,
            }
        )
    estado = {
        "proximo": 1,
        "tela_atual": paginas[0]["id"] if paginas else None,
        "inst_atual": 0,
        "telas": telas,
        "instantes": instantes,
    }
    a_rotular = [t for t in telas if t["origem"] == ORIGEM_MODELO]
    relatorio = {
        "n_paginas": len(paginas),
        "herdadas": herdadas,
        "a_rotular": [t["id"] for t in a_rotular],
        "notas_a_rotular": sum(len(t["notas"]) for t in a_rotular),
        "notas_herdadas": sum(len(t["notas"]) for t in telas if t["id"] in herdadas),
        "conflitos": conflitos,
        "telas_v1_sem_pagina": v1_sem_pagina,
        "telas_v1_na_borda": ambiguas,
        "pagina_do_v1": {str(k): v for k, v in pagina_do_v1.items()},
        "instantes_reatribuidos": reatribuidos,
        "instantes_sem_pagina": sem_pagina,
    }
    return estado, relatorio


def fundir_sem_v1(
    paginas: list[dict], duracao_s: float, passo_s: float, n: int, seed: int
) -> tuple[dict, dict]:
    """Estado da ferramenta para um vídeo SEM ouro v1: tudo a rotular pelo dono.

    Cada página traz as notas do modelo (``conferida`` falso, origem "modelo — a
    rotular"). Os instantes são sorteados DENTRO da presença de tablatura (as exibições
    das páginas, numa grade de ``passo_s``) por ``sortear_instantes``, e a página é
    SUGERIDA pelo tempo (``pagina_sugerida`` verdadeiro, ``tela_confirmada`` falso): o
    dono confirma a página e clica a coluna acesa. Sugerir cria viés de confirmação;
    o campo existe para isso ficar registrado no ouro.

    Args:
        paginas: páginas com ``id``, ``exibicoes`` e ``notas`` do modelo.
        duracao_s: duração do vídeo, em segundos.
        passo_s: intervalo da grade de onde se sorteia, em segundos.
        n: quantos instantes sortear.
        seed: semente do sorteio.

    Returns:
        ``(estado, relatorio)``, com as mesmas chaves de ``fundir_ouro``.
    """
    grade = [pagina_em(paginas, k * passo_s) for k in range(int(duracao_s / passo_s))]
    sorteio = sortear_instantes(grade, passo_s, n, seed)
    telas = [_tela_do_modelo(p) for p in paginas]
    instantes = [
        {
            "t": t,
            "estado": None,
            "tela": pagina,
            "tela_v1": None,
            "coluna_x_quadro": None,
            "obs": "",
            "tela_confirmada": False,
            "pagina_sugerida": True,
        }
        for t, pagina in sorteio
    ]
    estado = {
        "proximo": 1,
        "tela_atual": paginas[0]["id"] if paginas else None,
        "inst_atual": 0,
        "telas": telas,
        "instantes": instantes,
    }
    relatorio = {
        "n_paginas": len(paginas),
        "herdadas": [],
        "a_rotular": [t["id"] for t in telas],
        "notas_a_rotular": sum(len(t["notas"]) for t in telas),
        "notas_herdadas": 0,
        "conflitos": [],
        "sem_v1": True,
        "n_instantes": len(instantes),
        "seed": seed,
        "passo_s": passo_s,
    }
    return estado, relatorio


def texto_sem_v1(relatorio: dict) -> str:
    """Frase do ``como_foi_rotulado`` do ouro v2 de um vídeo sem v1.

    Args:
        relatorio: o relatório de ``fundir_sem_v1``.

    Returns:
        O texto explicando a origem do pré-preenchimento e o viés da sugestão.
    """
    return (
        "v2 sem v1: páginas do tab.telas (1 - IoU da tinta, limiar 0,3), todas com as "
        f"notas do modelo, a rotular (origem '{ORIGEM_MODELO}', conferida=false). "
        f"{relatorio['n_instantes']} instantes sorteados dentro da presença de "
        f"tablatura (semente {relatorio['seed']}, grade de {relatorio['passo_s']} s); a "
        "página de cada um foi SUGERIDA pelo tempo (pagina_sugerida=true, "
        "tela_confirmada=false até o dono confirmar): há viés de confirmação. A coluna "
        "acesa é do dono."
    )


def texto_fusao(relatorio: dict, video_v1: str) -> str:
    """Frase do ``como_foi_rotulado`` do ouro v2.

    Args:
        relatorio: o relatório de ``fundir_ouro``.
        video_v1: nome do arquivo do ouro v1 (para citar).

    Returns:
        O texto explicando a fusão v1 para v2.
    """
    return (
        f"v2 = fusão do {video_v1} (rotulado pelo dono olhando o quadro_ref_s de cada "
        "tela, agrupadas por diferença média em cinza, que juntou páginas diferentes de "
        "mesmo leiaute) com as páginas do tab.telas (1 - IoU da tinta, limiar 0,3). "
        f"{len(relatorio['herdadas'])} páginas herdam as notas do dono (tela v1 com "
        "quadro_ref_s dentro da exibição; origem 'ouro_v1 (dono)'); "
        f"{len(relatorio['a_rotular'])} vêm pré-preenchidas pelo modelo e esperam o dono "
        "(origem 'modelo — a rotular'). Instantes: t, coluna e obs são do dono; a página "
        "foi reatribuída pelo tempo (tela_confirmada=false até o dono confirmar)."
    )


# ---------------------------------------------------------------------------------
# preparar
# ---------------------------------------------------------------------------------


def fazer_slug(texto: str) -> str:
    """Nome de pasta/arquivo seguro a partir do nome do vídeo.

    Args:
        texto: nome do vídeo (com ou sem extensão).

    Returns:
        Minúsculas, sem acento, só ``[a-z0-9_]``.
    """
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_") or "video"


def retangulo_do_painel(cand: Candidato, forma: tuple[int, ...]) -> Retangulo:
    """Retângulo do painel no QUADRO: cordas com 1,5 passo de folga, largura do ROI.

    Args:
        cand: painel escolhido.
        forma: ``quadro.shape``.

    Returns:
        ``(x0, y0, x1, y1)`` no espaço do quadro.
    """
    linhas = list(cand.grade.linhas_y)
    folga = round(1.5 * cand.passo)
    y0 = max(0, cand.y0 + min(linhas) - folga)
    y1 = min(forma[0], cand.y0 + max(linhas) + folga)
    x0 = cand.x0
    x1 = min(forma[1], x0 + cand.roi.shape[1])
    return int(x0), int(y0), int(x1), int(y1)


def painel_com_caixas(
    rect: Retangulo,
    caixas: list[list[float]],
    forma: tuple[int, ...],
    margem: int = MARGEM_PAINEL_PX,
) -> Retangulo:
    """Painel final da tela: ``rect`` ampliado até conter TODAS as caixas (mais margem).

    O recorte da imagem e as caixas têm de sair do mesmo painel; se o painel do primeiro
    quadro da tela é mais estreito que o do quadro de referência, a imagem cortava notas.

    Args:
        rect: painel candidato, no quadro.
        caixas: caixas ``[x0, y0, x1, y1]`` no quadro.
        forma: ``quadro.shape`` (limita o resultado às bordas).
        margem: folga, em px, em volta das caixas que sobraram fora de ``rect``.

    Returns:
        ``(x0, y0, x1, y1)`` que contém ``rect`` e todas as caixas.
    """
    x0, y0, x1, y1 = rect
    for c in caixas:
        x0, y0 = min(x0, int(c[0]) - margem), min(y0, int(c[1]) - margem)
        x1, y1 = max(x1, int(c[2]) + margem), max(y1, int(c[3]) + margem)
    return max(0, x0), max(0, y0), min(forma[1], x1), min(forma[0], y1)


#: Folga, em passos, ACIMA da corda 1 no recorte da tela. Os arcos de ligadura da corda 1
#: sobem acima da linha e sumiam do recorte (``painel_com_caixas`` só olha as caixas).
FOLGA_ACIMA_PASSOS = 1.5


def folga_acima_da_corda1(rect: Retangulo, passo: float) -> Retangulo:
    """Sobe o topo do painel ``FOLGA_ACIMA_PASSOS`` passos, para caber o arco da corda 1.

    Args:
        rect: painel no quadro, ``(x0, y0, x1, y1)``.
        passo: distância entre cordas, em px.

    Returns:
        O mesmo painel com ``y0`` menor em ``ceil(1,5 * passo)`` px, nunca abaixo de 0.
    """
    x0, y0, x1, y1 = rect
    return x0, max(0, y0 - math.ceil(FOLGA_ACIMA_PASSOS * passo)), x1, y1


def ler_notas(cand: Candidato, modelo, rotulos, dev, discriminador) -> dict:
    """Pré-leitura de uma tela: algarismos viram nota, o resto vira ``nao_nota``.

    Usa ``reconhecer_linha`` e ``cand.x0``, como o ``tab.transcrever``. As caixas vêm
    do ``segmentar`` (o mesmo que o ``reconhecer_linha`` usa por dentro).

    Args:
        cand: painel escolhido no quadro.
        modelo: classificador de glifos.
        rotulos: classes do modelo.
        dev: dispositivo.
        discriminador: função "isto é algarismo?".

    Returns:
        ``{"passo", "linhas_y" (no quadro), "notas", "nao_nota"}``.
    """
    r = reconhecer_linha(cand.roi, modelo, rotulos, dev, discriminador=discriminador)
    grade = segmentar(cand.roi)
    caixas = {(g.corda, g.x0): (g.x0, g.y0, g.x1, g.y1) for g in grade.glifos}
    passo = float(r["passo"])
    linhas = [cand.y0 + y for y in r["linhas_y"]]
    notas, nao_nota = [], []
    for n in r["notas"]:
        caixa = n.get("caixa") or caixas.get((n["corda"], n["x"]))
        if caixa is None:
            largura = LARGURA_ALGARISMO_PASSOS * passo
            y = r["linhas_y"][n["corda"] - 1]
            caixa = (n["x"], y - 0.4 * passo, n["x"] + largura, y + 0.4 * passo)
        x0, y0, x1, y1 = caixa
        item = {
            "corda": int(n["corda"]),
            "casa": n["casa"],
            "x_quadro": int(cand.x0 + n["x"]),
            "x_centro_quadro": round(cand.x0 + (x0 + x1) / 2, 1),
            "caixa": [
                round(cand.x0 + x0),
                round(cand.y0 + y0),
                round(cand.x0 + x1),
                round(cand.y0 + y1),
            ],
            "confianca": n.get("confianca"),
        }
        if n.get("casa") in ALGARISMOS and n.get("origem") != "simbolo":
            notas.append(item)
        else:
            nao_nota.append(item)
    return {"passo": passo, "linhas_y": linhas, "notas": notas, "nao_nota": nao_nota}


def _log(msg: str) -> None:
    """Progresso no stderr (o stdout fica para o resultado)."""
    print(msg, file=sys.stderr, flush=True)


def preparar(
    video: str,
    saida: Path,
    passo_s: float = 2.0,
    n_instantes: int = 40,
    seed: int = 0,
    limiar: float = LIMIAR_DIFERENCA,
    modelo_caminho: Path = MODELO_PADRAO,
) -> dict:
    """Prepara o material a rotular (T2.1): telas, instantes e ``pre.json``.

    Args:
        video: caminho do vídeo.
        saida: pasta de saída (``telas/``, ``instantes/``, ``pre.json``).
        passo_s: intervalo entre quadros amostrados, em segundos.
        n_instantes: quantos instantes sortear.
        seed: semente do sorteio.
        limiar: diferença média absoluta que separa uma tela de outra.
        modelo_caminho: pesos do classificador de glifos.

    Returns:
        O conteúdo gravado em ``pre.json``.
    """
    inicio = time.time()
    (saida / "telas").mkdir(parents=True, exist_ok=True)
    (saida / "instantes").mkdir(parents=True, exist_ok=True)
    meta = leitor.info(video)
    duracao = float(meta["duracao_s"] or 0.0)
    modelo, rotulos, dev = carregar_modelo(str(modelo_caminho))
    discriminador = carregar()

    def detectar(quadro: np.ndarray) -> tuple[Retangulo, object] | None:
        cand = escolher(quadro)
        if cand is None or not PASSO_MINIMO_PX <= cand.passo <= PASSO_MAXIMO_PX:
            return None  # fora de 14-45 px não é tablatura (braço do violão: ~10 px)
        rect = retangulo_do_painel(cand, quadro.shape)
        saturacao = cv2.cvtColor(recortar(quadro, rect), cv2.COLOR_BGR2HSV)[:, :, 1]
        cinza = cv2.cvtColor(recortar(quadro, rect), cv2.COLOR_BGR2GRAY)
        if (
            np.median(saturacao) > SATURACAO_MEDIANA_MAXIMA
            or np.median(cinza) < CINZA_MEDIANO_MINIMO
        ):
            return None
        return rect, cand

    pre_telas: list[dict] = []

    def fechar(tela: TelaAgrupada) -> None:
        cand = tela.carga0
        if tela.melhor_t != tela.t_ini and tela.melhor_quadro is not None:
            melhor = escolher(tela.melhor_quadro)
            cand = melhor if melhor is not None else cand
        pre = ler_notas(cand, modelo, rotulos, dev, discriminador)
        forma = tela.melhor_quadro.shape
        rect = retangulo_do_painel(cand, forma)
        rect = (
            min(rect[0], tela.rect[0]),
            min(rect[1], tela.rect[1]),
            max(rect[2], tela.rect[2]),
            max(rect[3], tela.rect[3]),
        )
        caixas = [n["caixa"] for n in pre["notas"] + pre["nao_nota"]]
        rect = painel_com_caixas(rect, caixas, forma)
        rect = folga_acima_da_corda1(rect, pre["passo"])
        miolo = recortar(tela.melhor_quadro, rect)
        ampliada = cv2.resize(
            miolo, None, fx=ESCALA_TELA, fy=ESCALA_TELA, interpolation=cv2.INTER_CUBIC
        )
        arquivo = f"telas/{tela.id:03d}.png"
        cv2.imwrite(str(saida / arquivo), ampliada)
        pre_telas.append(
            {
                "id": tela.id,
                "arquivo": arquivo,
                "quadro_ref_s": tela.melhor_t,
                "t_ini": tela.t_ini,
                "t_fim": tela.t_fim,
                "n_quadros": tela.n_quadros,
                "painel": list(rect),
                "escala": ESCALA_TELA,
                **pre,
            }
        )
        _log(
            f"tela {tela.id:03d}: {tela.t_ini:.0f}-{tela.t_fim:.0f}s "
            f"{len(pre['notas'])} notas pré-lidas, {len(pre['nao_nota'])} não-nota"
        )

    agrupador = Agrupador(limiar, detectar, fechar)
    tela_por_quadro: list[int | None] = []
    n_quadros = int(duracao / passo_s)
    for k, (_t, quadro) in enumerate(
        leitor.quadros(video, 0.0, duracao, 1.0 / passo_s)
    ):
        tela_por_quadro.append(agrupador.alimentar(k * passo_s, quadro))
        if k % 50 == 0:
            _log(f"quadro {k}/{n_quadros} ({time.time() - inicio:.0f}s)")
    agrupador.encerrar()

    retangulos = {t["id"]: tuple(t["painel"]) for t in pre_telas}
    pre_instantes = []
    sorteio = sortear_instantes(tela_por_quadro, passo_s, n_instantes, seed)
    for ordem, (t, tela) in enumerate(sorteio, start=1):
        quadro = leitor.quadro_em(video, t)
        if quadro is None:
            _log(f"instante {t}s: sem quadro, pulado")
            continue
        _, y0, _, y1 = retangulos[tela]
        faixa = recortar(quadro, (0, y0, quadro.shape[1], y1))
        arquivo = f"instantes/{ordem:03d}.png"
        cv2.imwrite(str(saida / arquivo), faixa)
        pre_instantes.append(
            {
                "t": t,
                "arquivo": arquivo,
                "tela_sugerida": tela,
                "recorte": [0, y0, int(quadro.shape[1]), y1],
                "escala": 1,
            }
        )
    try:
        nome_video = str(Path(video).resolve().relative_to(acervo().resolve()))
    except ValueError:
        nome_video = video
    try:
        modelo_txt = str(Path(modelo_caminho).resolve().relative_to(RAIZ))
    except ValueError:
        modelo_txt = str(modelo_caminho)
    dif = agrupador.diferencas
    pre = {
        "video": nome_video,
        "modelo": modelo_txt,
        "preparado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "duracao_s": duracao,
        "codec": meta["codec"],
        "passo_s": passo_s,
        "seed": seed,
        "limiar_diferenca": limiar,
        "medida_diferencas": {
            "n": len(dif),
            "histograma": histograma(dif),
            "acima_do_limiar": sum(1 for d in dif if d > limiar),
        },
        "tempo_execucao_s": round(time.time() - inicio, 1),
        "telas": pre_telas,
        "instantes": pre_instantes,
    }
    gravar_atomico(saida / "pre.json", pre)
    _log(
        f"pronto: {len(pre_telas)} telas, {len(pre_instantes)} instantes, "
        f"{pre['tempo_execucao_s']}s"
    )
    return pre


def detector_na_faixa(
    faixa: tuple[int, int],
) -> Callable[[np.ndarray], segmentacao.Retangulo | None]:
    """Detector de painel do ``tab.telas`` que só olha a faixa vertical ``faixa``.

    Para preparar o ouro de um vídeo em que o detector escolhe o braço do violão (fundo
    claro atrás das cordas) e deixa a tablatura de lado: quem prepara OLHA o quadro e
    diz em que faixa a tablatura está (``--faixa Y0 Y1``). É ajuda de rotulagem, como o
    dono apontar a tablatura; não muda o produto, que é medido contra o ouro.

    Args:
        faixa: ``(y0, y1)`` no quadro, em px.

    Returns:
        ``quadro -> retângulo | None``, com o retângulo no espaço do quadro.
    """
    y0, y1 = faixa

    def detectar(quadro: np.ndarray) -> segmentacao.Retangulo | None:
        rect = segmentacao.painel_do_quadro(quadro[y0:y1])
        if rect is None:
            return None
        return (rect[0], rect[1] + y0, rect[2], rect[3] + y0)

    return detectar


def _candidato_na_faixa(quadro: np.ndarray, painel: Retangulo) -> Candidato | None:
    """Painel escolhido SÓ na faixa vertical que o ``tab.telas`` deu à página.

    O ``painel.escolher`` olha o quadro inteiro e, com a câmera mostrando o braço do violão
    (6 cordas, passo ~6 px), escolhe o braço e deixa a tablatura de lado. Aqui o quadro é
    cortado na faixa do painel (mais ``FOLGA_FAIXA_PX``) e a escolha é refeita; o ``y0`` do
    candidato volta para o espaço do quadro.

    Args:
        quadro: quadro BGR inteiro.
        painel: painel da página, no quadro (``tab.telas``).

    Returns:
        O candidato (``y0`` no quadro) ou ``None`` se a faixa não tem tablatura.
    """
    topo = max(0, painel[1] - FOLGA_FAIXA_PX)
    base = min(quadro.shape[0], painel[3] + FOLGA_FAIXA_PX)
    cand = escolher(quadro[topo:base, :])
    if cand is None or not PASSO_MINIMO_PX <= cand.passo <= PASSO_MAXIMO_PX:
        return None
    return replace(cand, y0=cand.y0 + topo, y1=cand.y1 + topo)


def _candidato_da_pagina(
    video: str, pagina: dict, so_na_faixa: bool = False
) -> tuple[np.ndarray, Candidato]:
    """Quadro e painel da página: tenta o ``quadro_ref_s`` e depois o meio das exibições.

    Primeiro o quadro inteiro (``painel.escolher``); se nenhum instante da página dá
    painel com passo de tablatura, tenta de novo só na faixa do painel do ``tab.telas``.

    Args:
        video: caminho do vídeo.
        pagina: página com ``quadro_ref_s``, ``exibicoes`` e ``painel``.
        so_na_faixa: pula o quadro inteiro (com ``--faixa``, o quadro inteiro é o
            que escolhe o braço do violão).

    Returns:
        ``(quadro, candidato)``.

    Raises:
        RuntimeError: se nenhum quadro da página tem painel.
    """
    instantes = [float(pagina["quadro_ref_s"])] + [
        (a + b) / 2 for a, b in pagina["exibicoes"]
    ]
    quadros = []
    for t in instantes:
        quadro = leitor.quadro_em(video, t)
        if quadro is None:
            continue
        quadros.append(quadro)
        if so_na_faixa:
            continue
        cand = escolher(quadro)
        if cand is not None and PASSO_MINIMO_PX <= cand.passo <= PASSO_MAXIMO_PX:
            return quadro, cand
    for quadro in quadros:
        cand = _candidato_na_faixa(quadro, tuple(pagina["painel"]))
        if cand is not None:
            return quadro, cand
    raise RuntimeError(f"página {pagina['id']}: nenhum quadro com painel")


def completar(
    video: str,
    ouro_v1: Path | None,
    saida: Path,
    ouro_v2: Path,
    telas_json: Path | None = None,
    modelo_caminho: Path = MODELO_PADRAO,
    passo_s: float = 2.0,
    n_instantes: int = 40,
    seed: int = 0,
    faixa: tuple[int, int] | None = None,
) -> dict:
    """Prepara o ouro v2: páginas do ``tab.telas`` + notas do dono herdadas do v1.

    Grava ``saida/telas/NNN.png``, ``saida/instantes/NNN.png`` e ``saida/pre.json``, e o
    ouro v2 inicial em ``ouro_v2`` (NUNCA o v1, que só é lido; o v2 existente não é
    sobrescrito, pois guarda trabalho do dono). Sem ``ouro_v1`` (vídeo novo), todas as
    páginas ficam com as notas do modelo a rotular e os instantes são sorteados na
    presença de tablatura (``fundir_sem_v1``).

    Args:
        video: caminho do vídeo.
        ouro_v1: ouro v1 (só leitura), ou ``None`` para um vídeo sem ouro anterior.
        saida: pasta de saída.
        ouro_v2: ouro v2 a criar.
        telas_json: saída já pronta de ``python -m tab.telas`` (pula a segmentação).
        modelo_caminho: pesos do classificador de glifos.
        passo_s: grade do sorteio de instantes (só sem ``ouro_v1``).
        n_instantes: quantos instantes sortear (só sem ``ouro_v1``).
        seed: semente do sorteio (só sem ``ouro_v1``).
        faixa: ``(y0, y1)`` onde a tablatura está, vista por quem prepara; a
            segmentação e o painel de cada página só olham essa faixa
            (``detector_na_faixa``). ``None``: o quadro inteiro.

    Returns:
        O ``pre.json`` gravado (com ``fusao``).

    Raises:
        FileExistsError: se ``ouro_v2`` já existe.
        RuntimeError: com ``ouro_v1``, se uma página não tem painel (sem v1 a página é
            descartada e listada em ``fusao["paginas_descartadas"]``).
    """
    if ouro_v2.exists():
        raise FileExistsError(f"{ouro_v2} já existe; não sobrescrevo trabalho do dono")
    v1 = json.loads(ouro_v1.read_text(encoding="utf-8")) if ouro_v1 else None
    if telas_json is not None:
        previstas = json.loads(telas_json.read_text(encoding="utf-8"))["telas"]
    else:
        detectar = (
            segmentacao.painel_do_quadro if faixa is None else detector_na_faixa(faixa)
        )
        previstas = [asdict(t) for t in segmentacao.telas(video, detectar=detectar)]
    (saida / "telas").mkdir(parents=True, exist_ok=True)
    (saida / "instantes").mkdir(parents=True, exist_ok=True)
    meta = leitor.info(video)
    modelo, rotulos, dev = carregar_modelo(str(modelo_caminho))
    discriminador = carregar()
    paginas, quadros, descartadas = [], {}, []
    for p in previstas:
        try:
            quadro, cand = _candidato_da_pagina(video, p, faixa is not None)
        except RuntimeError as erro:
            if v1 is not None:
                raise
            # vídeo novo: o dono não tem como rotular uma "página" sem tablatura
            # (falso positivo da presença do tab.telas); fica registrada no pre.json
            descartadas.append({"id": int(p["id"]), "exibicoes": p["exibicoes"]})
            _log(f"página {p['id']:02d}: DESCARTADA ({erro})")
            continue
        pre_leitura = ler_notas(cand, modelo, rotulos, dev, discriminador)
        rect = retangulo_do_painel(cand, quadro.shape)
        painel = tuple(p["painel"])
        rect = (
            min(rect[0], painel[0]),
            min(rect[1], painel[1]),
            max(rect[2], painel[2]),
            max(rect[3], painel[3]),
        )
        if v1 is None:
            # vídeo novo: o painel do tab.telas pode vir parcial na horizontal (2 de 7
            # vídeos da Fase 8) ou alto demais, com o vídeo e a partitura juntos (South
            # American Music: 9 a 11 vezes a altura da TAB). A tela vai de borda a borda,
            # e na vertical fica só a faixa onde o painel achou as cordas.
            vertical = retangulo_do_painel(cand, quadro.shape)
            rect = (0, vertical[1], int(quadro.shape[1]), vertical[3])
        paginas.append(
            {
                "id": int(p["id"]),
                "quadro_ref_s": float(p["quadro_ref_s"]),
                "exibicoes": [list(e) for e in p["exibicoes"]],
                "painel": rect,
                "modo": p.get("modo", "estatico"),
                **pre_leitura,
            }
        )
        quadros[int(p["id"])] = quadro
        _log(f"página {p['id']:02d}: {len(pre_leitura['notas'])} notas pré-lidas")
    if v1 is None:
        estado, fusao = fundir_sem_v1(
            paginas, float(meta["duracao_s"] or 0.0), passo_s, n_instantes, seed
        )
        fusao["paginas_descartadas"] = descartadas
        texto = texto_sem_v1(fusao)
        if faixa is not None:
            fusao["faixa"] = list(faixa)
            texto += (
                f" Faixa da tablatura dada por quem preparou, por leitura visual: y "
                f"{faixa[0]}-{faixa[1]} (o detector escolhia o braço do violão)."
            )
    else:
        estado, fusao = fundir_ouro(v1, paginas)
        texto = texto_fusao(fusao, ouro_v1.name)
    caixas_v1 = {
        t["id"]: [n["caixa"] for n in t["notas"] if n.get("caixa")]
        for t in estado["telas"]
    }
    pre_telas = []
    for p in paginas:
        caixas = [n["caixa"] for n in p["notas"] + p["nao_nota"]] + caixas_v1[p["id"]]
        rect = painel_com_caixas(p["painel"], caixas, quadros[p["id"]].shape)
        rect = folga_acima_da_corda1(rect, p["passo"])
        miolo = recortar(quadros[p["id"]], rect)
        ampliada = cv2.resize(
            miolo, None, fx=ESCALA_TELA, fy=ESCALA_TELA, interpolation=cv2.INTER_CUBIC
        )
        arquivo = f"telas/{p['id']:03d}.png"
        cv2.imwrite(str(saida / arquivo), ampliada)
        exib = p["exibicoes"]
        pre_telas.append(
            {
                "id": p["id"],
                "arquivo": arquivo,
                "quadro_ref_s": p["quadro_ref_s"],
                "t_ini": exib[0][0],
                "t_fim": exib[-1][1],
                "exibicoes": exib,
                "modo": p["modo"],
                "painel": list(rect),
                "escala": ESCALA_TELA,
                "passo": p["passo"],
                "linhas_y": p["linhas_y"],
                "notas": p["notas"],
                "nao_nota": p["nao_nota"],
            }
        )
    por_id = {p["id"]: p for p in pre_telas}
    pre_instantes = []
    for ordem, i in enumerate(estado["instantes"], start=1):
        quadro = leitor.quadro_em(video, float(i["t"]))
        if quadro is None:
            raise RuntimeError(f"instante {i['t']}s: sem quadro")
        ref = por_id.get(i["tela"]) or pre_telas[0]
        _, y0, _, y1 = ref["painel"]
        cv2.imwrite(
            str(saida / f"instantes/{ordem:03d}.png"),
            recortar(quadro, (0, y0, quadro.shape[1], y1)),
        )
        pre_instantes.append(
            {
                "t": i["t"],
                "arquivo": f"instantes/{ordem:03d}.png",
                "tela_sugerida": i["tela"],
                "tela_v1": i["tela_v1"],
                "pagina_sugerida": bool(i.get("pagina_sugerida", False)),
                "recorte": [0, y0, int(quadro.shape[1]), y1],
                "escala": 1,
            }
        )
    try:
        nome_video = str(Path(video).resolve().relative_to(acervo().resolve()))
    except ValueError:
        nome_video = video
    try:
        modelo_txt = str(Path(modelo_caminho).resolve().relative_to(RAIZ))
    except ValueError:
        modelo_txt = str(modelo_caminho)
    pre = {
        "video": nome_video,
        "modelo": modelo_txt,
        "preparado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "duracao_s": float(meta["duracao_s"] or 0.0),
        "codec": meta["codec"],
        "segmentacao": "telas",
        "como_foi_rotulado": texto,
        "telas": pre_telas,
        "instantes": pre_instantes,
        "estado_inicial": estado,
        "fusao": fusao,
    }
    gravar_atomico(saida / "pre.json", pre)
    gravar_atomico(ouro_v2, montar_ouro(pre, estado))
    _log(
        f"pronto: {fusao['n_paginas']} páginas, {len(fusao['herdadas'])} herdadas, "
        f"{len(fusao['a_rotular'])} a rotular, {len(fusao['conflitos'])} conflitos"
    )
    return pre


# ---------------------------------------------------------------------------------
# servir
# ---------------------------------------------------------------------------------


def _como_foi_rotulado_gravado(ouro: Path) -> str | None:
    """``como_foi_rotulado`` do ouro já gravado em disco, se houver (senão ``None``).

    Args:
        ouro: arquivo do ouro.

    Returns:
        O texto gravado, para o servidor não apagar o que o dono acrescentou.
    """
    if not ouro.exists():
        return None
    return json.loads(ouro.read_text(encoding="utf-8")).get("como_foi_rotulado") or None


#: Letra da marca quando ``ataque`` é "nao", por motivo (o que a mão direita não faz).
LETRA_SEM_ATAQUE = {
    "h": "h",
    "p": "p",
    "mordente": "m",
    "prolongamento": "l",
    "slide_ligado": "s",
}

#: Marca quando ``ataque`` é "sim" e o motivo não é o normal.
MARCA_COM_ATAQUE = {
    "x": "x",
    "harmonico": "◇",
    "slide_entrada": "e",
    "rasgueado": "r",
    "arpejo": "a",
    "sustentada": "~",
}

#: Motivos do seletor do modo ataque, na ordem em que aparecem.
MOTIVOS_SELETOR = (
    "normal",
    "h",
    "p",
    "mordente",
    "prolongamento",
    "slide_ligado",
    "slide_entrada",
    "x",
    "harmonico",
    "rasgueado",
    "arpejo",
    "sustentada",
    "nao_sei",
)


def ataque_do_motivo(motivo: str) -> tuple[str, str]:
    """Traduz o motivo do seletor no par ``(ataque, ataque_motivo)`` gravado.

    Args:
        motivo: um valor de ``MOTIVOS_SELETOR``.

    Returns:
        O par, coerente com a tabela da seção 3 do plano.

    Raises:
        ValueError: se o motivo não está no seletor.
    """
    if motivo == "nao_sei":
        return "nao_sei", "tinta_sem_explicacao"
    if motivo in MOTIVOS_SEM_ATAQUE:
        return "nao", motivo
    if motivo in MOTIVOS_COM_ATAQUE:
        return "sim", motivo
    raise ValueError(f"motivo fora do seletor: {motivo!r}")


def coerente(ataque: str, motivo: str) -> bool:
    """Diz se ``ataque`` e ``ataque_motivo`` combinam (plano, seção 3).

    Args:
        ataque: "sim", "nao" ou "nao_sei".
        motivo: um valor de ``ATAQUE_MOTIVOS``.

    Returns:
        True se o par é coerente.
    """
    if motivo in MOTIVOS_SEM_ATAQUE:
        return ataque == "nao"
    if motivo in MOTIVOS_COM_ATAQUE:
        return ataque == "sim"
    return motivo in MOTIVOS_SEM_PAR and ataque == "nao_sei"


def rotulo_do_ataque(nota: dict | None, ambigua: bool) -> tuple[str, str]:
    """Marca e classe que a página mostra sobre uma nota no modo ataque.

    Args:
        nota: a entrada da nota no arquivo do ataque, ou None se ela não está nele.
        ambigua: True se a nota veio de um ambíguo (a região do dono).

    Returns:
        ``(texto, classe)``. Classe "nao" (letra forte), "sim" (x, harmônico, slide
        de entrada) ou "duvida" (? amarelo). ``("", "")`` quando não há marca.
    """
    if ambigua:
        return "?", "duvida"
    if nota is None:
        return "", ""
    ataque, motivo = nota.get("ataque"), nota.get("motivo")
    if ataque == "nao":
        letra = LETRA_SEM_ATAQUE.get(motivo)
        return (letra, "nao") if letra else ("?", "duvida")
    if ataque == "sim" and motivo in MARCA_COM_ATAQUE:
        return MARCA_COM_ATAQUE[motivo], "sim"
    if ataque == "nao_sei":
        return "?", "duvida"
    return "", ""


def rotulos_do_ataque(doc: dict, ambiguos: list[dict]) -> dict[str, list[str]]:
    """Marca de cada nota do ataque, pela chave ``t<tela>-n<k>``.

    Args:
        doc: o arquivo do ataque (lista ``notas``).
        ambiguos: os ambíguos da fonte (cada um com ``notas``, pode ser vazia).

    Returns:
        Mapa chave -> ``[texto, classe]``. Ambíguo sem decisão do dono ganha "?"; com
        decisão do dono (``fonte`` "dono"), vale a marca da entrada. Nota fora do
        arquivo e fora dos ambíguos não aparece.
    """
    decididas = {n["nota"] for n in doc.get("notas", []) if n.get("fonte") == "dono"}
    ambiguas = {chave for a in ambiguos for chave in a.get("notas", [])} - decididas
    rotulos = {
        n["nota"]: list(rotulo_do_ataque(n, n["nota"] in ambiguas))
        for n in doc.get("notas", [])
    }
    for chave in ambiguas:
        rotulos[chave] = list(rotulo_do_ataque(None, True))
    return rotulos


def visao_do_ataque(doc: dict, ambiguos: list[dict]) -> dict:
    """O que a página recebe: o arquivo, os ambíguos e a marca de cada nota.

    Args:
        doc: o arquivo do ataque.
        ambiguos: os ambíguos da fonte.

    Returns:
        Cópia rasa do arquivo com ``ambiguos`` e ``rotulos``.
    """
    return {**doc, "ambiguos": ambiguos, "rotulos": rotulos_do_ataque(doc, ambiguos)}


def carregar_ataque(caminho: Path) -> tuple[dict, list[dict]]:
    """Lê o arquivo do ataque e os ambíguos da fonte.

    Os ambíguos vêm da chave ``ambiguos`` do próprio arquivo, se houver; senão, de
    ``fontes[<fonte>].ambiguos`` do ``resumo.json`` na mesma pasta (é onde o
    ``converter.py`` os grava).

    Args:
        caminho: o ``ataque_<fonte>.json``.

    Returns:
        ``(arquivo, ambiguos)``.

    Raises:
        ValueError: se o arquivo não tem a lista ``notas``.
    """
    doc = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(doc.get("notas"), list):
        raise ValueError(f"{caminho}: sem a lista 'notas'")
    if "ambiguos" in doc:
        return doc, doc["ambiguos"]
    resumo = caminho.with_name("resumo.json")
    if not resumo.exists():
        return doc, []
    dados = json.loads(resumo.read_text(encoding="utf-8"))
    fonte = dados.get("fontes", {}).get(doc.get("fonte"), {})
    return doc, fonte.get("ambiguos", [])


def aplicar_escolha(
    doc: dict,
    tela: int,
    nota: str,
    motivo: str,
    corda: int,
    casa: object,
    x_centro_quadro: float | None,
) -> dict:
    """Devolve uma cópia do arquivo do ataque com a escolha do dono numa nota.

    A nota é trocada se já está no arquivo, ou acrescentada se não está. Os campos
    ``regiao`` e os demais da nota existente são mantidos. ``fonte`` da nota vira
    "dono". O original não é alterado, e o ouro não entra aqui.

    Args:
        doc: o arquivo do ataque.
        tela: id da tela (inteiro).
        nota: chave ``t<tela>-n<k>``; tem de ser da tela ``tela``.
        motivo: um valor de ``MOTIVOS_SELETOR``.
        corda: corda (1 a 6).
        casa: casa digitada (número ou "x").
        x_centro_quadro: x do centro da nota no quadro, ou None.

    Returns:
        O arquivo novo.

    Raises:
        ValueError: motivo fora do seletor, chave de outra tela, ou nota sem casa.
    """
    if not isinstance(tela, int) or not re.fullmatch(rf"t{tela}-n\d+", str(nota)):
        raise ValueError(f"nota {nota!r} não é da tela {tela!r}")
    ataque, motivo_gravado = ataque_do_motivo(motivo)
    casa_lida = _casa(casa)
    if casa_lida is None:
        raise ValueError(f"nota {nota} sem casa")
    novo = copy.deepcopy(doc)
    notas = novo.setdefault("notas", [])
    entrada = next((n for n in notas if n.get("nota") == nota), None)
    if entrada is None:
        entrada = {"nota": nota, "tela": tela, "regiao": None}
        notas.append(entrada)
    entrada.update(
        {
            "corda": int(corda),
            "casa": casa_lida,
            "x_centro_quadro": None
            if x_centro_quadro is None
            else round(float(x_centro_quadro), 1),
            "ataque": ataque,
            "motivo": motivo_gravado,
            "fonte": "dono",
        }
    )
    return novo


def aplicar_conferencia(doc: dict, tela: int, valor: bool) -> dict:
    """Devolve uma cópia do arquivo do ataque com a tela marcada (ou desmarcada).

    Args:
        doc: o arquivo do ataque.
        tela: id da tela.
        valor: True para "tela de ataque conferida".

    Returns:
        O arquivo novo, com ``telas_conferidas``.
    """
    novo = copy.deepcopy(doc)
    novo.setdefault("telas_conferidas", {})[str(int(tela))] = bool(valor)
    return novo


def criar_servidor(
    pasta: Path,
    ouro: Path,
    porta: int = 8099,
    host: str = "127.0.0.1",
    ataque: Path | None = None,
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor (não o inicia). Escuta em 127.0.0.1 (ou ``host``).

    Sem ``ataque``, o servidor é o de sempre. Com ele, expõe ``GET /ataque.json`` e
    ``POST /salvar_ataque``, que gravam SÓ nesse arquivo (nunca no ouro).

    Args:
        pasta: pasta do ``preparar`` (``pre.json``, ``telas/``, ``instantes/``).
        ouro: arquivo do ouro, gravado a cada ``POST /salvar``.
        porta: porta TCP (0 = uma livre).
        host: endereço de escuta; ``0.0.0.0`` só dentro de container, com a porta
            publicada em 127.0.0.1 do host (o cabeçalho Host continua checado).
        ataque: ``ataque_<fonte>.json`` do ``converter.py`` (opcional).

    Returns:
        O servidor; ``servidor.server_address[1]`` é a porta real.
    """
    pasta = pasta.resolve()
    pre = json.loads((pasta / "pre.json").read_text(encoding="utf-8"))
    trava = threading.Lock()

    class Manipulador(http.server.BaseHTTPRequestHandler):
        """Serve a página e as imagens, e grava o ouro em ``POST /salvar``."""

        server_version = "ouro_video"

        def log_message(self, formato: str, *args: object) -> None:
            """Silencia o log por requisição (o autosave faria uma linha por clique)."""

        def _responder(self, codigo: int, tipo: str, corpo: bytes) -> None:
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, codigo: int, dados: dict) -> None:
            corpo = json.dumps(dados, ensure_ascii=False).encode()
            self._responder(codigo, _TIPOS[".json"], corpo)

        def _host_ok(self) -> bool:
            """Recusa Host/Origin que não sejam a máquina local (rebinding, CSRF)."""
            local = {"127.0.0.1", "localhost"}
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            origem = self.headers.get("Origin")
            if host not in local:
                return False
            if origem is None:
                return True
            return (
                re.fullmatch(r"http://(127\.0\.0\.1|localhost)(:\d+)?", origem)
                is not None
            )

        def do_GET(self) -> None:
            """Página, ``pre.json``, ouro salvo e imagens da pasta."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            caminho = self.path.split("?", 1)[0]
            if caminho in {"/", "/index.html"}:
                self._responder(200, "text/html; charset=utf-8", PAGINA.encode())
                return
            if caminho == "/ouro.json":
                if ouro.exists():
                    self._responder(200, _TIPOS[".json"], ouro.read_bytes())
                else:
                    self._json(200, {})
                return
            if caminho == "/ataque.json" and ataque is not None:
                doc, ambiguos = carregar_ataque(ataque)
                self._json(200, visao_do_ataque(doc, ambiguos))
                return
            alvo = (pasta / caminho.lstrip("/")).resolve()
            if alvo.suffix in _TIPOS and alvo.is_relative_to(pasta) and alvo.is_file():
                self._responder(200, _TIPOS[alvo.suffix], alvo.read_bytes())
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def _salvar_ataque(self) -> None:
            """``/salvar_ataque``: grava a escolha ou a conferência SÓ no arquivo do ataque."""
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= 16_000_000:
                    raise ValueError("corpo ausente ou grande demais")
                pedido = json.loads(self.rfile.read(tamanho))
                with trava:
                    doc, ambiguos = carregar_ataque(ataque)
                    if pedido["acao"] == "conferida":
                        novo = aplicar_conferencia(doc, pedido["tela"], pedido["valor"])
                    elif pedido["acao"] == "escolha":
                        novo = aplicar_escolha(
                            doc,
                            pedido["tela"],
                            pedido["nota"],
                            pedido["motivo"],
                            pedido["corda"],
                            pedido["casa"],
                            pedido.get("x_centro_quadro"),
                        )
                    else:
                        raise ValueError(f"ação desconhecida: {pedido['acao']!r}")
                    gravar_atomico(ataque, novo)
            except (ValueError, KeyError, TypeError) as erro:
                self._json(400, {"ok": False, "erro": f"{type(erro).__name__}: {erro}"})
                return
            self._json(200, {"ok": True, **visao_do_ataque(novo, ambiguos)})

        def do_POST(self) -> None:
            """``/salvar``: monta, valida e grava o ouro de forma atômica."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            if self.path == "/salvar_ataque" and ataque is not None:
                self._salvar_ataque()
                return
            if self.path != "/salvar":
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= 16_000_000:
                    raise ValueError("corpo ausente ou grande demais")
                estado = json.loads(self.rfile.read(tamanho))
                with trava:
                    documento = montar_ouro(
                        pre,
                        estado,
                        como_foi_rotulado=_como_foi_rotulado_gravado(ouro),
                    )
                    gravar_atomico(ouro, documento)
            except (ValueError, KeyError, TypeError) as erro:
                self._json(400, {"ok": False, "erro": f"{type(erro).__name__}: {erro}"})
                return
            self._json(
                200,
                {
                    "ok": True,
                    "salvo_em": documento["rotulado_em"],
                    "n_telas": len(documento["telas"]),
                    "n_instantes": len(documento["instantes"]),
                    "ouro": documento,
                },
            )

    return http.server.ThreadingHTTPServer((host, porta), Manipulador)


PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ouro de vídeo</title>
<style>
:root{--fundo:#fff;--texto:#1b1b1b;--suave:#666;--borda:#c9c9c9;--acento:#0b6bcb;--ok:#1a7f37;--ruim:#c62828;--caixa:#e53935;--painel:#f4f4f4}
@media (prefers-color-scheme:dark){:root{--fundo:#161616;--texto:#e8e8e8;--suave:#999;--borda:#444;--acento:#5aa9ff;--ok:#4cc26a;--ruim:#ff6b6b;--caixa:#ff6b5e;--painel:#222}}
*{box-sizing:border-box}
body{margin:0;background:var(--fundo);color:var(--texto);font:15px/1.4 system-ui,sans-serif}
header{display:flex;gap:12px;align-items:center;padding:8px 16px;border-bottom:1px solid var(--borda);position:sticky;top:0;background:var(--fundo);z-index:5;flex-wrap:wrap}
button,select,input{font:inherit;color:inherit;background:var(--painel);border:1px solid var(--borda);border-radius:6px;padding:4px 10px}
button{cursor:pointer}button.on{background:var(--acento);color:#fff;border-color:var(--acento)}
button.ok{background:var(--ok);color:#fff;border-color:var(--ok)}
#status{margin-left:auto;font-weight:600}#status.ruim{color:var(--ruim)}#status.ok{color:var(--ok)}
main{display:flex;gap:16px;padding:12px 16px}
#lista{flex:0 0 150px;max-height:calc(100vh - 70px);overflow:auto;display:flex;flex-direction:column;gap:4px}
#lista button{text-align:left}
#conteudo{flex:1;min-width:0}
.moldura{position:relative;display:inline-block;max-width:100%;border:1px solid var(--borda);cursor:crosshair;line-height:0}
.moldura img{max-width:100%;height:auto;display:block}
.caixa{position:absolute;outline:2px solid var(--caixa);outline-offset:4px;cursor:pointer}.caixa.nao{pointer-events:none}.caixa.editando{outline-width:3px;outline-color:#1565c0}
.editor{position:absolute;z-index:4;display:flex;gap:4px;align-items:center;background:var(--fundo);border:1px solid var(--borda);border-radius:6px;padding:4px;box-shadow:0 2px 8px rgba(0,0,0,.3);line-height:normal;cursor:default}.editor input{width:4.5em;font-size:16px}
.caixa.nao{outline:1px dashed var(--suave)}.caixa.removida{opacity:.25}.caixa.dono{outline-style:dotted}
.caixa b{position:absolute;left:-6px;top:-22px;background:var(--caixa);color:#fff;font-size:11px;line-height:14px;padding:0 3px;border-radius:3px}
.copia{margin-top:6px;cursor:default;background:#fff}.copia img{opacity:.18}
.copia span{position:absolute;transform:translate(-50%,-50%);color:#1565c0;font-weight:700;font-size:clamp(11px,1.15vw,18px);line-height:1;white-space:nowrap;background:#fff;padding:0 2px;border-radius:3px}
.editor{flex-wrap:wrap;max-width:min(560px,90vw)}.editor button.tec{padding:2px 6px;font-family:monospace}.editor button.tec.ligado{background:#7b1fa2;color:#fff;border-color:#7b1fa2}
.copia span sup.tec{color:#7b1fa2;font-size:.7em}
.regiao{position:absolute;outline:2px dashed #7b1fa2;background:rgba(123,31,162,.08);cursor:pointer;z-index:2}.regiao.editando{outline-width:3px;outline-style:solid}
.regiao b{position:absolute;left:0;top:0;transform:translateY(-100%);background:#7b1fa2;color:#fff;font-size:11px;line-height:1.3;padding:0 3px;border-radius:3px 3px 0 0;white-space:nowrap}
.regiao.nova{pointer-events:none;outline-style:solid}.copia .regiao{pointer-events:none}
.moldura.modo-regiao{cursor:cell}.moldura.modo-regiao .caixa{pointer-events:none}
button.regiao-ligado{background:#7b1fa2;color:#fff;border-color:#7b1fa2}
.copia span.mudou{color:#e65100}.copia span.dono{color:#1a7f37}.copia span.removida{text-decoration:line-through;opacity:.45}
.coluna{position:absolute;top:0;bottom:0;width:0;border-left:3px solid var(--caixa);pointer-events:none}
table{border-collapse:collapse;margin-top:10px}td,th{padding:3px 8px;border-bottom:1px solid var(--borda);text-align:left}
td input{width:5em}tr.removida td{opacity:.4;text-decoration:line-through}tr.removida td:last-child{text-decoration:none;opacity:1}
.linha{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}
.suave{color:var(--suave)}
#lista button.herdada{border-left:5px solid var(--ok)}#lista button.rotular{border-left:5px solid var(--ruim)}
.par{display:flex;gap:12px;align-items:flex-start;flex-wrap:nowrap}.par>div{min-width:0}.par.vertical{flex-direction:column}
.ok-txt{color:var(--ok);font-weight:600}.ruim-txt{color:var(--ruim);font-weight:600}
.ataque-nota{position:absolute;border:2px solid;border-radius:3px;pointer-events:none;z-index:3}
.ataque-nota.nao{border-color:#d84315}.ataque-nota.sim{border-color:#1565c0}.ataque-nota.duvida{border-color:#f9a825}
.ataque-marca{position:absolute;transform:translate(-50%,-100%);font:700 11px/1 system-ui,sans-serif;padding:1px 3px;border-radius:3px;pointer-events:none;white-space:nowrap;z-index:3}
.ataque-marca.nao{background:#d84315;color:#fff}.ataque-marca.sim{background:#1565c0;color:#fff}.ataque-marca.duvida{background:#ffeb3b;color:#000}
.ataque-regiao{position:absolute;border:1px solid #f9a825;background:rgba(249,168,37,.10);pointer-events:none;z-index:2}
@media (max-width:700px){main{flex-direction:column}#lista{flex:none;flex-direction:row;max-height:none}}
</style></head><body>
<header>
<b>Ouro de vídeo</b><span id="video" class="suave"></span>
<button id="aba-telas">Telas</button><button id="aba-inst">Instantes</button>
<button id="baixar">baixar JSON</button>
<span id="status">carregando…</span>
</header>
<main><div id="lista"></div><div id="conteudo"></div></main>
<script>
"use strict";
const TECNICAS = __TECNICAS__;
const TECNICAS_REGIAO = __TECNICAS_REGIAO__;
let MODO_REGIAO = false;  /* arrastar na página desenha uma região de técnica */
let ATAQUE = null, MODO_ATAQUE = false, ESCOLHA = null, BOTAO_ATAQUE = null, CONTADOR_ATAQUE = null;
let PRE = null, E = null, SO_ROTULAR = false, EMPILHAR = false, OUTRA = false, ABA = "telas", sujo = false, versao = 0, ultimoOuro = null, temporizador = null;

function h(tag, attrs, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "class") e.className = v;
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) if (f != null) e.append(f.nodeType ? f : document.createTextNode(String(f)));
  return e;
}

/* Conversão: espelho de clique_para_quadro() / corda_mais_proxima() do Python. */
function cliqueParaQuadro(xImg, escala, origem) { return origem + xImg / escala; }
function cordaMaisProxima(y, linhas) {
  let m = 0;
  linhas.forEach((l, k) => { if (Math.abs(l - y) < Math.abs(linhas[m] - y)) m = k; });
  return m + 1;
}

function estadoInicial() {
  if (PRE.estado_inicial) return JSON.parse(JSON.stringify(PRE.estado_inicial));
  return {
    proximo: 1, tela_atual: PRE.telas.length ? PRE.telas[0].id : null, inst_atual: 0,
    telas: PRE.telas.map(t => ({
      id: t.id, conferida: false, junta_em: null,
      notas: t.notas.map((n, i) => ({id: "m" + i, corda: n.corda, casa: String(n.casa),
        x_quadro: n.x_quadro, x_centro_quadro: n.x_centro_quadro, origem: "modelo", removida: false, caixa: n.caixa}))
    })),
    instantes: PRE.instantes.map(i => ({t: i.t, estado: null, tela: i.tela_sugerida, coluna_x_quadro: null, obs: ""}))
  };
}

/* ---- gravação: a cada alteração; o servidor escreve em disco ---- */
function mudou() {
  sujo = true; versao++;
  setStatus("alterado, gravando…", "");
  clearTimeout(temporizador); temporizador = setTimeout(salvar, 200);
}
async function salvar() {
  const minha = versao;
  try {
    const r = await fetch("/salvar", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(E)});
    const j = await r.json();
    if (!j.ok) throw new Error(j.erro);
    ultimoOuro = j.ouro;
    if (minha === versao) { sujo = false; setStatus("salvo em disco " + j.salvo_em.slice(11) + " (" + j.n_telas + " telas, " + j.n_instantes + " instantes)", "ok"); }
  } catch (e) {
    setStatus("NÃO SALVO (" + e.message + ") — tentando de novo; use baixar JSON", "ruim");
    clearTimeout(temporizador); temporizador = setTimeout(salvar, 3000);
  }
}
function setStatus(t, c) { const s = document.getElementById("status"); s.textContent = t; s.className = c; }
window.addEventListener("beforeunload", ev => { if (sujo) { ev.preventDefault(); ev.returnValue = ""; } });
document.getElementById("baixar").onclick = () => {
  const doc = ultimoOuro || {video: PRE.video, ferramenta: E};
  const a = h("a", {href: URL.createObjectURL(new Blob([JSON.stringify(doc, null, 1)], {type: "application/json"})), download: "ouro_video.json"});
  document.body.append(a); a.click(); a.remove();
};

/* ---- aba TELAS ---- */
function herdada(t) { return !!t.origem && t.origem.startsWith("ouro_v1"); }
function telaPre(id) { return PRE.telas.find(t => t.id === id); }
function telaEst(id) { return E.telas.find(t => t.id === id); }

function listaTelas() {
  const l = document.getElementById("lista"); l.replaceChildren();
  const v2 = E.telas.some(t => t.origem);
  if (v2) l.append(h("label", {class: "suave"}, h("input", {type: "checkbox", checked: SO_ROTULAR, onchange: ev => { SO_ROTULAR = ev.target.checked; desenhar(); }}), " só a rotular"));
  for (const t of E.telas) {
    if (SO_ROTULAR && (herdada(t) || t.conferida) && t.id !== E.tela_atual) continue;
    const n = t.notas.filter(x => !x.removida).length;
    const rot = String(t.id).padStart(3, "0") + (herdada(t) ? " ★" : "") + (t.conferida ? " ✓" : "") + (t.junta_em ? " = " + t.junta_em : "") + " · " + n;
    const cls = (t.id === E.tela_atual ? "on " : "") + (herdada(t) ? "herdada" : t.origem ? "rotular" : "");
    l.append(h("button", {class: cls, title: t.origem || "", onclick: () => { ESCOLHA = null; E.tela_atual = t.id; desenhar(); }}, rot));
  }
}
function listaInstantes() {
  const l = document.getElementById("lista"); l.replaceChildren();
  E.instantes.forEach((i, k) => {
    const marca = i.estado === null ? "" : i.estado === "coluna" ? " ●" : i.estado === "nenhuma" ? " ○" : " ∅";
    const pag = i.tela_confirmada === undefined ? "" : i.tela_confirmada ? " ✓" : " ?";
    l.append(h("button", {class: k === E.inst_atual ? "on" : "", onclick: () => { E.inst_atual = k; OUTRA = false; desenhar(); }}, String(k + 1).padStart(2, "0") + marca + pag));
  });
}

function caixaDe(tp, n) {  /* retângulo da nota em % da imagem */
  const [rx0, ry0, rx1, ry1] = tp.painel, w = rx1 - rx0, hh = ry1 - ry0;
  let c = n.caixa;
  if (!c) { const p = tp.passo, y = tp.linhas_y[n.corda - 1]; c = [n.x_centro_quadro - 0.3 * p, y - 0.4 * p, n.x_centro_quadro + 0.3 * p, y + 0.4 * p]; }
  return {left: (c[0] - rx0) / w * 100, top: (c[1] - ry0) / hh * 100, width: (c[2] - c[0]) / w * 100, height: (c[3] - c[1]) / hh * 100};
}
function pintarRotulo(el, tp, n) {  /* cópia de baixo: azul = modelo; laranja = "modelo→dono"; verde = do dono */
  const atual = String(n.casa).trim();
  if (n.origem !== "modelo") { el.textContent = atual || "?"; el.className = "dono"; marcarTecnica(el, n); return; }
  const lido = String((tp.notas[Number(n.id.slice(1))] || {}).casa ?? "");
  const trocou = atual !== lido;
  el.textContent = trocou ? lido + "→" + (atual || "?") : lido;
  el.className = (trocou ? "mudou" : "") + (n.removida ? " removida" : "");
  marcarTecnica(el, n);
}
function marcarTecnica(el, n) {  /* técnicas marcadas pelo dono, em roxo, depois da casa */
  if (n.tecnica && n.tecnica.length) el.append(h("sup", {class: "tec"}, " " + n.tecnica.join(" ")));
}
function estiloCaixa(r) { return `left:${r.left}%;top:${r.top}%;width:${r.width}%;height:${r.height}%`; }
/* Largura/altura naturais no atributo: sem isso a moldura tem 2 px até a PNG decodificar
   (imagem de 3504 px) e o editor, em % dela, aparece na borda esquerda, longe do clique. */
function imagemTela(tp) {
  return h("img", {src: "/" + tp.arquivo, width: (tp.painel[2] - tp.painel[0]) * tp.escala, height: (tp.painel[3] - tp.painel[1]) * tp.escala, draggable: "false"});
}
function imagemInstante(ip) {  /* o recorte de instante já está na escala 1 do quadro */
  return h("img", {src: "/" + ip.arquivo, width: ip.recorte[2] - ip.recorte[0], height: ip.recorte[3] - ip.recorte[1], draggable: "false"});
}
/* Editor preso à área da moldura: não sai pela direita (nem pela esquerda). */
function posicaoEditor(r) { return `left:max(0px,min(${r.left}%,calc(100% - min(560px,90vw))));`; }

let EDITAR = null;  /* id da nota com o editor aberto sobre a imagem */
let IGNORAR_CLIQUE = false;  /* o clique que fechou o editor não acrescenta nota */
function fecharEditor(redesenhar = true) {
  if (EDITAR === null) return;
  EDITAR = null;
  if (redesenhar) desenhar();
  else {  /* sem redesenhar: o clique que fechou segue para o botão onde caiu */
    document.querySelectorAll(".editor").forEach(e => e.remove());
    document.querySelectorAll(".caixa.editando").forEach(e => e.classList.remove("editando"));
  }
  window.scrollTo({top: 0});
}
document.addEventListener("mousedown", ev => {
  IGNORAR_CLIQUE = false;
  if (EDITAR === null || ev.target.closest(".editor")) return;
  if (ev.target.closest(".caixa, .regiao")) return;  /* outra caixa: ela mesma troca o editor */
  IGNORAR_CLIQUE = !!ev.target.closest(".moldura");  /* fechar não acrescenta nota */
  fecharEditor(false);
}, true);
function abrirEditor(mold, tp, te, n, r) {
  const caixa = mold.querySelector(`[data-caixa="${n.id}"]`); if (caixa) caixa.classList.add("editando");
  const campo = h("input", {value: n.casa, inputmode: "numeric", oninput: ev => {
    n.casa = ev.target.value; mudou();
    const el = document.querySelector(`[data-rotulo="${n.id}"]`); if (el) pintarRotulo(el, tp, n);
    const tab = document.querySelector(`td input[data-nota="${n.id}"]`); if (tab) tab.value = n.casa;
  }, onkeydown: ev => { if (ev.key === "Enter" || ev.key === "Escape") fecharEditor(); }});
  const acao = h("button", {onclick: () => {
    if (n.origem === "dono") te.notas.splice(te.notas.indexOf(n), 1); else n.removida = !n.removida;
    mudou(); fecharEditor(); }}, n.origem === "dono" ? "apagar" : n.removida ? "restaurar" : "não é nota");
  const tecs = Object.entries(TECNICAS).map(([k, d]) => h("button", {class: "tec" + ((n.tecnica || []).includes(k) ? " ligado" : ""), title: d,
    onclick: ev => {
      const l = new Set(n.tecnica || []); if (l.has(k)) l.delete(k); else l.add(k);
      n.tecnica = Object.keys(TECNICAS).filter(c => l.has(c)); mudou();
      ev.currentTarget.classList.toggle("ligado", l.has(k));
      const el = document.querySelector(`[data-rotulo="${n.id}"]`); if (el) pintarRotulo(el, tp, n);
      campo.focus();
    }}, k));
  const ed = h("div", {class: "editor", style: `${posicaoEditor(r)}top:calc(${r.top + r.height}% + 8px)`},
    h("span", {class: "suave"}, "corda " + n.corda), campo, acao, h("span", {class: "suave"}, "técnica:"), tecs);
  mold.append(ed);
  campo.focus(); campo.select();
}

function fracParaQuadro(tp, fx, fy) {  /* fração da moldura -> px do QUADRO */
  const xImg = fx * (tp.painel[2] - tp.painel[0]) * tp.escala, yImg = fy * (tp.painel[3] - tp.painel[1]) * tp.escala;
  return [cliqueParaQuadro(xImg, tp.escala, tp.painel[0]), cliqueParaQuadro(yImg, tp.escala, tp.painel[1])];
}
function pctRegiao(tp, r) {  /* região (px do quadro) em % da imagem */
  const [rx0, ry0, rx1, ry1] = tp.painel, w = rx1 - rx0, hh = ry1 - ry0;
  const x0 = Math.min(r.x0, r.x1), x1 = Math.max(r.x0, r.x1), y0 = Math.min(r.y0, r.y1), y1 = Math.max(r.y0, r.y1);
  return {left: (x0 - rx0) / w * 100, top: (y0 - ry0) / hh * 100, width: (x1 - x0) / w * 100, height: (y1 - y0) / hh * 100};
}
function rotuloRegiao(r) { return (r.tecnica && r.tecnica.length ? r.tecnica.join(" ") : "?") + (r.obs ? " · " + r.obs : ""); }
function abrirEditorRegiao(mold, tp, te, r) {
  const div = mold.querySelector(`[data-regiao="${r.id}"]`); if (div) div.classList.add("editando");
  const p = pctRegiao(tp, r);
  const atualizar = () => { mudou(); document.querySelectorAll(`[data-rotulo-regiao="${r.id}"]`).forEach(e => { e.textContent = rotuloRegiao(r); }); };
  const tecs = Object.entries(TECNICAS_REGIAO).map(([k, d]) => h("button", {class: "tec" + ((r.tecnica || []).includes(k) ? " ligado" : ""), title: d,
    onclick: ev => {
      const l = new Set(r.tecnica || []); if (l.has(k)) l.delete(k); else l.add(k);
      r.tecnica = Object.keys(TECNICAS_REGIAO).filter(c => l.has(c));
      ev.currentTarget.classList.toggle("ligado", l.has(k)); atualizar();
    }}, k));
  const obs = h("input", {value: r.obs || "", placeholder: "observação", style: "width:10em", oninput: ev => { r.obs = ev.target.value; atualizar(); },
    onkeydown: ev => { if (ev.key === "Enter" || ev.key === "Escape") fecharEditor(); }});
  const apagar = h("button", {onclick: () => { te.regioes.splice(te.regioes.indexOf(r), 1); mudou(); fecharEditor(); }}, "apagar região");
  mold.append(h("div", {class: "editor", style: `${posicaoEditor(p)}top:calc(${p.top + p.height}% + 8px)`},
    h("span", {class: "suave"}, `cordas ${Math.min(r.corda_ini, r.corda_fim)}–${Math.max(r.corda_ini, r.corda_fim)}`), tecs, obs, apagar));
}

function desenharTela() {
  const c = document.getElementById("conteudo"); c.replaceChildren();
  if (E.tela_atual === null) { c.append("Sem telas."); return; }
  const tp = telaPre(E.tela_atual), te = telaEst(E.tela_atual);
  const mold = h("div", {class: "moldura"}, imagemTela(tp));
  tp.nao_nota.forEach(n => { const r = caixaDe(tp, n); mold.append(h("div", {class: "caixa nao", style: estiloCaixa(r), title: "não é nota: " + n.casa})); });
  /* cópia logo abaixo, alinhada: a mesma faixa apagada com a leitura em cima de cada nota */
  const copia = h("div", {class: "moldura copia"}, imagemTela(tp));
  if (!te.regioes) te.regioes = [];
  if (MODO_REGIAO) mold.classList.add("modo-regiao");
  te.regioes.forEach(rg => {
    const p = pctRegiao(tp, rg);
    mold.append(h("div", {class: "regiao", "data-regiao": rg.id, style: estiloCaixa(p), title: "região de técnica — clique para editar",
      onmousedown: ev => ev.stopPropagation(),
      onclick: ev => { ev.stopPropagation(); EDITAR = rg.id; desenhar(); }}, h("b", {"data-rotulo-regiao": rg.id}, rotuloRegiao(rg))));
    copia.append(h("div", {class: "regiao", style: estiloCaixa(p)}, h("b", {"data-rotulo-regiao": rg.id}, rotuloRegiao(rg))));
  });
  mold.addEventListener("mousedown", ev => {  /* modo região: arrastar desenha o retângulo */
    if (!MODO_REGIAO || ev.button !== 0 || ev.target.closest(".editor, .regiao")) return;
    ev.preventDefault();
    const rc = mold.querySelector("img").getBoundingClientRect();
    if (rc.width < 50) return;
    const fr = e => [Math.min(1, Math.max(0, (e.clientX - rc.left) / rc.width)), Math.min(1, Math.max(0, (e.clientY - rc.top) / rc.height))];
    const [ax, ay] = fr(ev);
    const fantasma = h("div", {class: "regiao nova"}); mold.append(fantasma);
    const mover = e => { const [bx, by] = fr(e);
      fantasma.style.cssText = `left:${Math.min(ax, bx) * 100}%;top:${Math.min(ay, by) * 100}%;width:${Math.abs(bx - ax) * 100}%;height:${Math.abs(by - ay) * 100}%`; };
    const soltar = e => {
      document.removeEventListener("mousemove", mover); document.removeEventListener("mouseup", soltar); fantasma.remove();
      const [bx, by] = fr(e);
      if (Math.abs(bx - ax) * rc.width < 6 && Math.abs(by - ay) * rc.height < 6) return;  /* clique, não arrasto */
      const [x0, y0] = fracParaQuadro(tp, ax, ay), [x1, y1] = fracParaQuadro(tp, bx, by);
      const rg = {id: "r" + (E.proximo++), x0: Math.round(x0 * 10) / 10, x1: Math.round(x1 * 10) / 10, y0: Math.round(y0 * 10) / 10, y1: Math.round(y1 * 10) / 10,
        corda_ini: cordaMaisProxima(Math.min(y0, y1), tp.linhas_y), corda_fim: cordaMaisProxima(Math.max(y0, y1), tp.linhas_y), tecnica: [], obs: ""};
      te.regioes.push(rg); EDITAR = rg.id; mudou(); desenhar();
    };
    document.addEventListener("mousemove", mover); document.addEventListener("mouseup", soltar);
  });
  te.notas.forEach((n, i) => {
    const r = caixaDe(tp, n);
    mold.append(h("div", {class: "caixa" + (n.removida ? " removida" : "") + (n.origem === "dono" ? " dono" : ""), style: estiloCaixa(r),
      title: "#" + (i + 1) + " — clique para corrigir", "data-caixa": n.id,
      onclick: ev => { ev.stopPropagation(); if (MODO_ATAQUE && ATAQUE) { ESCOLHA = mapaChaves(te).has(n.id) ? n.id : null; EDITAR = null; } else EDITAR = n.id; desenhar(); }}));
    const rotulo = h("span", {"data-rotulo": n.id, title: "#" + (i + 1), style: `left:${r.left + r.width / 2}%;top:${r.top + r.height / 2}%`});
    pintarRotulo(rotulo, tp, n);
    copia.append(rotulo);
  });
  if (ATAQUE && MODO_ATAQUE) desenharAtaque(mold, tp, te);
  mold.addEventListener("click", ev => {
    if (IGNORAR_CLIQUE) { IGNORAR_CLIQUE = false; return; }
    if (MODO_REGIAO || (ATAQUE && MODO_ATAQUE)) return;
    if (ev.target.closest(".editor")) return;
    const rc = mold.querySelector("img").getBoundingClientRect();
    if (rc.width < 50) return;  /* imagem ainda não carregou */
    const fx = (ev.clientX - rc.left) / rc.width, fy = (ev.clientY - rc.top) / rc.height;
    const xImg = fx * (tp.painel[2] - tp.painel[0]) * tp.escala, yImg = fy * (tp.painel[3] - tp.painel[1]) * tp.escala;
    const xq = cliqueParaQuadro(xImg, tp.escala, tp.painel[0]), yq = cliqueParaQuadro(yImg, tp.escala, tp.painel[1]);
    te.notas.push({id: "d" + (E.proximo++), corda: cordaMaisProxima(yq, tp.linhas_y), casa: "", x_centro_quadro: Math.round(xq * 10) / 10,
      x_quadro: Math.round((xq - 0.25 * tp.passo) * 10) / 10, origem: "dono", removida: false});
    EDITAR = te.notas[te.notas.length - 1].id;
    mudou(); desenhar();
  });
  const outras = E.telas.filter(t => t.id !== te.id);
  const sel = h("select", {onchange: ev => { te.junta_em = ev.target.value ? Number(ev.target.value) : null; mudou(); desenhar(); }},
    h("option", {value: ""}, "— única —"), outras.map(t => h("option", {value: t.id, selected: te.junta_em === t.id}, "igual à tela " + t.id)));
  const tabela = h("table", {}, h("tr", {}, h("th", {}, "#"), h("th", {}, "corda"), h("th", {}, "casa"), h("th", {}, ""), h("th", {}, "")));
  te.notas.forEach((n, i) => {
    const campo = h("input", {value: n.casa, "data-nota": n.id, inputmode: "numeric", oninput: ev => {
      n.casa = ev.target.value; mudou();
      const el = document.querySelector(`[data-rotulo="${n.id}"]`); if (el) pintarRotulo(el, tp, n);
    }});
    const acao = h("button", {onclick: () => {
      if (n.origem === "dono") te.notas.splice(i, 1); else n.removida = !n.removida;
      mudou(); desenhar(true); }}, n.origem === "dono" ? "apagar" : n.removida ? "restaurar" : "não é nota");
    tabela.append(h("tr", {class: n.removida ? "removida" : ""}, h("td", {}, i + 1), h("td", {}, n.corda), h("td", {}, campo),
      h("td", {}, n.origem === "dono" ? "acrescentada" : "modelo"), h("td", {}, acao)));
  });
  const sem = te.notas.filter(n => !n.removida && !String(n.casa).trim()).length;
  c.append(
    h("div", {class: "linha"}, h("b", {}, "Tela " + tp.id), h("span", {class: "suave"}, `ref. ${tp.quadro_ref_s}s · vista de ${tp.t_ini}s a ${tp.t_fim}s`),
      te.origem ? h("span", {class: herdada(te) ? "ok-txt" : "ruim-txt"}, te.origem + (te.v1_telas && te.v1_telas.length ? " (tela v1 " + te.v1_telas.join(", ") + ")" : "")) : "",
      tp.exibicoes ? h("span", {class: "suave"}, "exibições: " + tp.exibicoes.map(e => Math.round(e[0]) + "-" + Math.round(e[1])).join(", ")) : ""),
    h("div", {class: "linha"},
      h("button", {class: te.conferida ? "ok" : "", onclick: () => { te.conferida = !te.conferida; mudou(); desenhar(); }}, te.conferida ? "✓ conferida" : "tela conferida"),
      sel,
      h("button", {onclick: () => { const p = E.telas.find(t => !t.conferida && !t.junta_em && t.id !== te.id); if (p) { E.tela_atual = p.id; desenhar(); } }}, "próxima não conferida"),
      h("button", {class: MODO_REGIAO ? "regiao-ligado" : "", title: "arraste um retângulo sobre as cordas/colunas que a técnica cobre",
        onclick: () => { MODO_REGIAO = !MODO_REGIAO; desenhar(); }}, MODO_REGIAO ? "▭ modo região LIGADO (clique para sair)" : "▭ marcar região de técnica"),
      ATAQUE && MODO_ATAQUE ? h("button", {class: ataqueConferida(te.id) ? "ok" : "", onclick: () => marcarTelaAtaque(te.id, !ataqueConferida(te.id))},
        ataqueConferida(te.id) ? "✓ tela de ataque conferida" : "tela de ataque conferida") : null),
    h("div", {class: "suave"}, "Clique numa caixa vermelha para corrigir a casa (Enter ou clique fora fecha). Técnica (opcional, em roxo): h, p, slide e ligada vão na nota de CHEGADA, a que não é atacada de novo; marque o que está desenhado. Técnica que cobre várias cordas ou colunas (arpejo, pestana, rasgueado, let ring...): ligue ▭ marcar região de técnica e arraste um retângulo. Clique fora das caixas para acrescentar uma nota que faltou (a corda sai da linha mais próxima)."),
    mold, copia, sem ? h("div", {class: "linha", style: "color:var(--ruim)"}, sem + " nota(s) sem casa não serão gravadas") : "", tabela);
  if (ESCOLHA !== null && ATAQUE && MODO_ATAQUE) {
    const n = te.notas.find(x => x.id === ESCOLHA), chave = n && mapaChaves(te).get(n.id);
    if (n && chave) abrirSeletorAtaque(mold, tp, te, n, chave);
    else ESCOLHA = null;
  }
  const editando = te.notas.find(n => n.id === EDITAR), regiao = te.regioes.find(r => r.id === EDITAR);
  if (editando) abrirEditor(mold, tp, te, editando, caixaDe(tp, editando));
  else if (regiao) abrirEditorRegiao(mold, tp, te, regiao);
  else EDITAR = null;
}

/* ---- modo ATAQUE: o ataque de cada nota (só o arquivo do --ataque; nunca o ouro) ---- */
const ROTULO_MOTIVO = {normal: "normal", h: "h", p: "p", mordente: "mordente", prolongamento: "prolongamento", slide_ligado: "slide ligado", slide_entrada: "slide de entrada", x: "X", harmonico: "harmônico", nao_sei: "não sei"};
const MOTIVOS_SELETOR = __MOTIVOS_SELETOR__;
function ataqueConferida(id) { return !!(ATAQUE && ATAQUE.telas_conferidas && ATAQUE.telas_conferidas[String(id)]); }
/* Espelho de montar_ouro(): a nota de índice k no ouro da tela é "t<id>-n<k>" (sem removidas
   e sem casa vazia; ordenadas por x_quadro arredondado a 0,1 e depois pela corda). */
function mapaChaves(te) {
  const vivas = [];
  te.notas.forEach((n, i) => { if (!n.removida && String(n.casa ?? "").trim() !== "") vivas.push({n, i, x: Math.round(Number(n.x_quadro) * 10) / 10}); });
  vivas.sort((a, b) => (a.x - b.x) || (Number(a.n.corda) - Number(b.n.corda)) || (a.i - b.i));
  const mapa = new Map();
  vivas.forEach((v, k) => mapa.set(v.n.id, "t" + te.id + "-n" + k));
  return mapa;
}
async function enviarAtaque(corpo) {
  try {
    const r = await fetch("/salvar_ataque", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(corpo)});
    const j = await r.json();
    if (!j.ok) throw new Error(j.erro);
    ATAQUE = j;
    setStatus("ataque gravado no arquivo do ataque (o ouro não mudou)", "ok");
  } catch (e) {
    setStatus("ATAQUE NÃO GRAVADO (" + e.message + ")", "ruim");
  }
  desenhar();
}
function regiaoDoAmbiguo(tp, a) {  /* região do dono (x_quadro e cordas) em % da imagem: retângulo fino */
  const c0 = Math.min(...a.cordas), c1 = Math.max(...a.cordas);
  return pctRegiao(tp, {x0: a.x_quadro[0], x1: a.x_quadro[1], y0: tp.linhas_y[c0 - 1] - tp.passo / 2, y1: tp.linhas_y[c1 - 1] + tp.passo / 2});
}
function desenharAtaque(mold, tp, te) {  /* marcas do ataque sobre a imagem (só no modo ataque) */
  ATAQUE.ambiguos.filter(a => a.tela === te.id).forEach(a => {
    mold.append(h("div", {class: "ataque-regiao", style: estiloCaixa(regiaoDoAmbiguo(tp, a)), title: a.tipo + " · " + a.regiao}));
  });
  const mapa = mapaChaves(te);
  te.notas.forEach(n => {
    const chave = mapa.get(n.id), rot = chave && ATAQUE.rotulos[chave];
    if (!rot || !rot[0]) return;
    const r = caixaDe(tp, n);
    mold.append(h("div", {class: "ataque-nota " + rot[1], style: estiloCaixa(r), title: chave}));  /* contorno em cima do número */
    mold.append(h("span", {class: "ataque-marca " + rot[1], style: `left:${r.left + r.width / 2}%;top:${r.top}%`, title: chave}, rot[0]));
  });
}
function abrirSeletorAtaque(mold, tp, te, n, chave) {  /* seletor pequeno: escolhe o motivo da nota */
  const atual = ATAQUE.notas.find(x => x.nota === chave);
  const botoes = MOTIVOS_SELETOR.map(m => {
    const marcado = !!atual && (m === "nao_sei" ? atual.ataque === "nao_sei" : atual.motivo === m);
    return h("button", {class: marcado ? "on" : "", onclick: () => { ESCOLHA = null; enviarAtaque({acao: "escolha", tela: te.id, nota: chave, motivo: m, corda: n.corda, casa: n.casa, x_centro_quadro: n.x_centro_quadro ?? n.x_quadro}); }}, ROTULO_MOTIVO[m]);
  });
  const r = caixaDe(tp, n);
  mold.append(h("div", {class: "editor", style: `${posicaoEditor(r)}top:calc(${r.top + r.height}% + 8px)`},
    h("span", {class: "suave"}, chave + " · corda " + n.corda + " · casa " + n.casa), botoes,
    h("button", {onclick: () => { ESCOLHA = null; desenhar(); }}, "fechar")));
}
function alternarAtaque() {
  MODO_ATAQUE = !MODO_ATAQUE; ESCOLHA = null; EDITAR = null;
  desenhar();
}
function marcarTelaAtaque(id, valor) {
  ESCOLHA = null;
  enviarAtaque({acao: "conferida", tela: id, valor: valor});
}
function atualizarAtaque() {  /* botão e contador do modo ataque no topo */
  if (!ATAQUE) return;
  BOTAO_ATAQUE.className = MODO_ATAQUE ? "on" : "";
  const nao = ATAQUE.notas.filter(n => n.ataque === "nao").length;
  const duvidas = Object.values(ATAQUE.rotulos).filter(r => r[1] === "duvida").length;
  const conferidas = Object.values(ATAQUE.telas_conferidas || {}).filter(Boolean).length;
  CONTADOR_ATAQUE.textContent = "nao " + nao + " · ? " + duvidas + " · telas de ataque conferidas " + conferidas + "/" + PRE.telas.length;
}
async function carregarAtaque() {  /* sem --ataque o servidor responde 404 e nada aparece */
  const r = await fetch("/ataque.json");
  if (!r.ok) return;
  ATAQUE = await r.json();
  const cab = document.querySelector("header"), status = document.getElementById("status");
  BOTAO_ATAQUE = h("button", {onclick: alternarAtaque}, "modo ataque (A)");
  CONTADOR_ATAQUE = h("span", {class: "suave"});
  cab.insertBefore(BOTAO_ATAQUE, status);
  cab.insertBefore(CONTADOR_ATAQUE, status);
}
document.addEventListener("keydown", ev => {
  if (!ATAQUE || ABA !== "telas" || ev.target.tagName === "INPUT" || ev.target.tagName === "SELECT") return;
  if (ev.key.toLowerCase() === "a") alternarAtaque();
});

/* ---- aba INSTANTES ---- */
function desenharInstante() {
  const c = document.getElementById("conteudo"); c.replaceChildren();
  const k = E.inst_atual, ie = E.instantes[k], ip = PRE.instantes[k];
  if (!ie) { c.append("Sem instantes."); return; }
  const v2 = ie.tela_confirmada !== undefined;
  const mold = h("div", {class: "moldura"}, imagemInstante(ip));
  const w = ip.recorte[2] - ip.recorte[0];
  if (ie.estado === "coluna") mold.append(h("div", {class: "coluna", style: `left:${(ie.coluna_x_quadro - ip.recorte[0]) / w * 100}%`}));
  const avancar = () => { OUTRA = false; if (E.inst_atual < E.instantes.length - 1) E.inst_atual++; desenhar(); };
  mold.addEventListener("click", ev => {
    if (IGNORAR_CLIQUE) { IGNORAR_CLIQUE = false; return; }
    if (ev.target.closest(".editor")) return;
    const rc = mold.querySelector("img").getBoundingClientRect(); if (rc.width < 50) return;
    const fx = (ev.clientX - rc.left) / rc.width;
    ie.estado = "coluna"; ie.coluna_x_quadro = Math.round(cliqueParaQuadro(fx * w * ip.escala, ip.escala, ip.recorte[0]) * 10) / 10;
    if (ie.tela == null) ie.tela = ip.tela_sugerida;
    mudou(); if (v2) desenhar(); else avancar();
  });
  const marcar = (estado) => { ie.estado = estado; ie.coluna_x_quadro = null; if (estado === "sem_tablatura") ie.tela = null; else if (ie.tela == null) ie.tela = ip.tela_sugerida; mudou(); if (v2) desenhar(); else avancar(); };
  const feitos = E.instantes.filter(i => i.estado !== null).length;
  const atual = ie.estado === null ? "ainda sem resposta" : ie.estado === "coluna" ? "coluna em x=" + ie.coluna_x_quadro : ie.estado === "nenhuma" ? "nenhuma acesa" : "sem tablatura";
  const conf = E.instantes.filter(i => i.tela_confirmada).length;
  const linhas = [
    h("div", {class: "linha"}, h("b", {}, `Instante ${k + 1}/${E.instantes.length} · t=${ie.t}s`), h("span", {class: "suave"}, `${feitos} respondidos · agora: ${atual}` + (v2 ? ` · ${conf}/${E.instantes.length} páginas confirmadas` : ""))),
    h("div", {class: "linha"},
      h("button", {onclick: () => { OUTRA = false; if (E.inst_atual > 0) E.inst_atual--; desenhar(); }}, "← anterior"),
      h("button", {onclick: () => marcar("nenhuma")}, "nenhuma acesa (N)"),
      h("button", {onclick: () => marcar("sem_tablatura")}, "sem tablatura (S)"),
      h("button", {onclick: () => { ie.estado = null; ie.coluna_x_quadro = null; mudou(); desenhar(); }}, "limpar"),
      h("button", {onclick: avancar}, "próximo →"),
      v2 ? h("label", {class: "suave"}, h("input", {type: "checkbox", checked: EMPILHAR, onchange: ev => { EMPILHAR = ev.target.checked; desenhar(); }}), " empilhar") : ""),
    h("div", {class: "suave"}, "Clique na COLUNA ACESA (a nota que está marcada agora)." + (v2 ? " À direita, a página atribuída: confirme ou troque." : " Depois da resposta a página avança.")),
  ];
  if (!v2) { c.append(...linhas, mold); c._atalhos = {n: () => marcar("nenhuma"), s: () => marcar("sem_tablatura")}; return; }
  const tp = ie.tela == null ? null : telaPre(ie.tela);
  const lado = h("div", {});
  if (ie.estado === "sem_tablatura") {
    lado.append(h("div", {class: "suave"}, "sem tablatura: não há página a confirmar."));
  } else if (tp) {
    const mp = h("div", {class: "moldura", style: "cursor:default"}, imagemTela(tp));
    if (ie.estado === "coluna") mp.append(h("div", {class: "coluna", style: `left:${(ie.coluna_x_quadro - tp.painel[0]) / (tp.painel[2] - tp.painel[0]) * 100}%`}));
    lado.append(h("div", {class: "linha"}, h("b", {}, "Página " + tp.id), h("span", {class: "suave"}, "exibições: " + tp.exibicoes.map(e => Math.round(e[0]) + "-" + Math.round(e[1])).join(", ")),
      h("span", {class: ie.tela_confirmada ? "ok-txt" : "ruim-txt"}, ie.tela_confirmada ? "confirmada" : "a confirmar")), mp);
  } else {
    lado.append(h("div", {class: "ruim-txt"}, "nenhuma página cobre t=" + ie.t + "s: escolha em 'outra página'."));
  }
  if (ie.estado !== "sem_tablatura" || ie.tela_confirmada !== undefined) {
    const botoes = h("div", {class: "linha"},
      h("button", {class: ie.tela_confirmada ? "ok" : "", onclick: () => { ie.tela_confirmada = true; mudou(); avancar(); }}, "é esta página"),
      h("button", {class: OUTRA ? "on" : "", onclick: () => { OUTRA = !OUTRA; desenhar(); }}, "outra página"));
    if (OUTRA) botoes.append(h("select", {onchange: ev => { if (!ev.target.value) return; ie.tela = Number(ev.target.value); ie.tela_confirmada = true; mudou(); avancar(); }},
      h("option", {value: ""}, "— escolher —"),
      PRE.telas.map(t => h("option", {value: t.id, selected: ie.tela === t.id}, "página " + t.id + " (" + t.exibicoes.map(e => Math.round(e[0]) + "-" + Math.round(e[1])).join(", ") + ")"))));
    lado.prepend(botoes);
  }
  const par = h("div", {class: "par" + (EMPILHAR ? " vertical" : "")}, h("div", {style: EMPILHAR ? "" : "flex:3 1 0"}, mold), h("div", {style: EMPILHAR ? "" : "flex:2 1 0"}, lado));
  c.append(...linhas, par);
  c._atalhos = {n: () => marcar("nenhuma"), s: () => marcar("sem_tablatura"), c: () => { ie.tela_confirmada = true; mudou(); avancar(); }};
}
document.addEventListener("keydown", ev => {
  if (ABA !== "instantes" || ev.target.tagName === "INPUT" || ev.target.tagName === "SELECT") return;
  const c = document.getElementById("conteudo");
  if (ev.key === "ArrowRight" && E.inst_atual < E.instantes.length - 1) { E.inst_atual++; desenhar(); }
  else if (ev.key === "ArrowLeft" && E.inst_atual > 0) { E.inst_atual--; desenhar(); }
  else if (c._atalhos && ev.key.toLowerCase() in c._atalhos) c._atalhos[ev.key.toLowerCase()]();
});

function desenhar(focarUltima) {
  document.getElementById("aba-telas").className = ABA === "telas" ? "on" : "";
  document.getElementById("aba-inst").className = ABA === "instantes" ? "on" : "";
  atualizarAtaque();
  try {
    if (ABA === "telas") { listaTelas(); desenharTela(); if (focarUltima) { const campos = document.querySelectorAll("td input"); const u = campos[campos.length - 1]; if (u && !u.value) u.focus(); } }
    else { listaInstantes(); desenharInstante(); }
  } catch (e) {  /* erro de desenho aparece na página, não só no console */
    document.getElementById("conteudo").replaceChildren(h("div", {class: "ruim-txt"}, "erro ao desenhar a aba " + ABA + ": " + e.message));
    console.error(e);
  }
}
function irParaAba(nome) { ABA = nome; OUTRA = false; desenhar(); }
document.getElementById("aba-telas").addEventListener("click", () => irParaAba("telas"));
document.getElementById("aba-inst").addEventListener("click", () => irParaAba("instantes"));

(async function () {
  PRE = await (await fetch("/pre.json")).json();
  const salvo = await (await fetch("/ouro.json")).json();
  E = salvo.ferramenta && salvo.ferramenta.telas ? salvo.ferramenta : estadoInicial();
  if (salvo.ferramenta) ultimoOuro = salvo;
  await carregarAtaque();
  document.getElementById("video").textContent = PRE.video;
  setStatus(salvo.ferramenta ? "trabalho anterior retomado" : "novo (nada salvo ainda)", "ok");
  desenhar();
})();
</script></body></html>
"""
PAGINA = (
    PAGINA.replace("__TECNICAS__", json.dumps(TECNICAS, ensure_ascii=False))
    .replace("__TECNICAS_REGIAO__", json.dumps(TECNICAS_REGIAO, ensure_ascii=False))
    .replace(
        "__MOTIVOS_SELETOR__", json.dumps(list(MOTIVOS_SELETOR), ensure_ascii=False)
    )
)


def servir(
    pasta: Path,
    ouro: Path,
    porta: int,
    host: str = "127.0.0.1",
    ataque: Path | None = None,
) -> int:
    """Sobe o servidor e fica nele até Ctrl+C.

    Antes de subir, confere o ouro gravado com o estado da ferramenta
    (``divergencias_do_estado``): se diferirem, não sobe e sai com código 3.

    Args:
        pasta: pasta do ``preparar``.
        ouro: arquivo do ouro.
        porta: porta TCP.
        host: endereço de escuta (``0.0.0.0`` só dentro de container).
        ataque: ``ataque_<fonte>.json`` para conferir o ataque (opcional). Só esse
            arquivo é gravado pelo modo ataque.

    Returns:
        Código de saída: 0 normal, 2 sem ``pre.json`` ou sem o arquivo do ataque,
        3 ouro divergente do estado.
    """
    if not (pasta / "pre.json").exists():
        print(f"sem pre.json em {pasta}; rode `preparar` antes", file=sys.stderr)
        return 2
    if ataque is not None and not ataque.exists():
        print(f"sem o arquivo do ataque {ataque}", file=sys.stderr)
        return 2
    if ouro.exists():
        pre = json.loads((pasta / "pre.json").read_text(encoding="utf-8"))
        atual = json.loads(ouro.read_text(encoding="utf-8"))
        divergencias = divergencias_do_estado(pre, atual)
        if divergencias:
            print(
                f"o ouro {ouro} não bate com o estado da ferramenta; o servidor NÃO "
                "subiu, porque a primeira gravação desfaria essas edições feitas fora "
                "da ferramenta:",
                file=sys.stderr,
            )
            for linha in divergencias:
                print(f"  - {linha}", file=sys.stderr)
            return 3
    servidor = criar_servidor(pasta, ouro, porta, host, ataque)
    print(f"ferramenta do ouro: http://127.0.0.1:{servidor.server_address[1]}/")
    print(f"o ouro é gravado a cada alteração em: {ouro}")
    if ataque is not None:
        print(f"modo ataque (tecla A) grava SÓ em: {ataque}")
    print(
        "ATENÇÃO: rode isto como JOB DE FUNDO GERENCIADO (processo solto morre com "
        "o shell e o trabalho para de ser gravado).",
        flush=True,
    )
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


def main() -> int:
    """Ponto de entrada: ``preparar``, ``completar`` ou ``servir``.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("preparar", help="gera telas, instantes e pre.json")
    p.add_argument("video")
    p.add_argument("--saida", type=Path, default=None)
    p.add_argument("--passo-s", type=float, default=2.0)
    p.add_argument("--n-instantes", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--limiar", type=float, default=LIMIAR_DIFERENCA)
    p.add_argument("--modelo", type=Path, default=MODELO_PADRAO)
    c = sub.add_parser(
        "completar", help="ouro v2: páginas do tab.telas + notas do dono herdadas do v1"
    )
    c.add_argument("video")
    c.add_argument("--ouro-v1", type=Path, default=None, help="omita em vídeo novo")
    c.add_argument("--ouro-v2", type=Path, required=True)
    c.add_argument("--saida", type=Path, required=True)
    c.add_argument("--telas-json", type=Path, default=None)
    c.add_argument("--modelo", type=Path, default=MODELO_PADRAO)
    c.add_argument(
        "--faixa",
        type=int,
        nargs=2,
        metavar=("Y0", "Y1"),
        default=None,
        help="faixa vertical onde a tablatura está (vídeo em que o detector acha o braço)",
    )
    c.add_argument(
        "--passo-s", type=float, default=2.0, help="sem v1: grade do sorteio"
    )
    c.add_argument("--n-instantes", type=int, default=40, help="sem v1")
    c.add_argument("--seed", type=int, default=0, help="sem v1")
    s = sub.add_parser("servir", help="serve a ferramenta de rotular (autosave)")
    s.add_argument("--pasta", type=Path, required=True)
    s.add_argument("--ouro", type=Path, required=True)
    s.add_argument("--porta", type=int, default=8099)
    s.add_argument("--host", default="127.0.0.1", help="0.0.0.0 só dentro de container")
    s.add_argument(
        "--ataque",
        type=Path,
        default=None,
        help="ataque_<fonte>.json: liga o modo ataque (só esse arquivo é gravado)",
    )
    args = ap.parse_args()
    if args.comando == "completar":
        pre = completar(
            args.video,
            args.ouro_v1,
            args.saida,
            args.ouro_v2,
            telas_json=args.telas_json,
            modelo_caminho=args.modelo,
            passo_s=args.passo_s,
            n_instantes=args.n_instantes,
            seed=args.seed,
            faixa=tuple(args.faixa) if args.faixa else None,
        )
        print(json.dumps(pre["fusao"], ensure_ascii=False, indent=1))
        return 0
    if args.comando == "preparar":
        saida = args.saida or SAIDA / "ouro_video" / fazer_slug(Path(args.video).stem)
        preparar(
            args.video,
            saida,
            passo_s=args.passo_s,
            n_instantes=args.n_instantes,
            seed=args.seed,
            limiar=args.limiar,
            modelo_caminho=args.modelo,
        )
        return 0
    return servir(args.pasta, args.ouro, args.porta, args.host, args.ataque)


if __name__ == "__main__":
    sys.exit(main())
