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
    python -m tab.ouro_video servir --pasta data/saida/ouro_video/<slug>/ \
        --ouro data/gold/ouro_video/<slug>.json --porta 8099
"""

from __future__ import annotations

import argparse
import datetime
import http.server
import json
import os
import random
import re
import sys
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import leitor
from .caminhos import MODELO_PADRAO, RAIZ, SAIDA, acervo
from .digito import carregar
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


def montar_ouro(pre: dict, estado: dict, agora: str | None = None) -> dict:
    """Monta o JSON do ouro (formato do plano) a partir do estado da ferramenta.

    Notas removidas ("não é nota") e notas SEM casa não entram. Telas marcadas "igual a
    outra" não entram, e os instantes delas passam à tela que fica. Um instante com
    coluna e sem tela recebe a tela cujo ``quadro_ref_s`` é o mais próximo no tempo.
    O estado completo vai junto em ``ferramenta`` (para retomar o trabalho).

    Args:
        pre: o ``pre.json`` da pasta.
        estado: o estado da página (``telas``, ``instantes``, ...).
        agora: carimbo de tempo (para teste); padrão, agora.

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
            notas.append(nota)
        notas.sort(key=lambda n: (n["x_quadro"], n["corda"]))
        telas.append(
            {
                "id": int(t["id"]),
                "quadro_ref_s": ref_s[t["id"]],
                "conferida": bool(t.get("conferida")),
                "notas": notas,
            }
        )
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
        }
        instantes.append(item)
    instantes.sort(key=lambda i: i["t"])
    ouro = {
        "video": pre["video"],
        "como_foi_rotulado": (
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
        caixa = caixas.get((n["corda"], n["x"]))
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
        miolo = recortar(tela.melhor_quadro, tela.rect)
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
                "painel": list(tela.rect),
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


# ---------------------------------------------------------------------------------
# servir
# ---------------------------------------------------------------------------------


def criar_servidor(
    pasta: Path, ouro: Path, porta: int = 8099
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor (não o inicia). Escuta SOMENTE em 127.0.0.1.

    Args:
        pasta: pasta do ``preparar`` (``pre.json``, ``telas/``, ``instantes/``).
        ouro: arquivo do ouro, gravado a cada ``POST /salvar``.
        porta: porta TCP (0 = uma livre).

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
            alvo = (pasta / caminho.lstrip("/")).resolve()
            if alvo.suffix in _TIPOS and alvo.is_relative_to(pasta) and alvo.is_file():
                self._responder(200, _TIPOS[alvo.suffix], alvo.read_bytes())
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def do_POST(self) -> None:
            """``/salvar``: monta, valida e grava o ouro de forma atômica."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            if self.path != "/salvar":
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= 16_000_000:
                    raise ValueError("corpo ausente ou grande demais")
                estado = json.loads(self.rfile.read(tamanho))
                documento = montar_ouro(pre, estado)
                with trava:
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

    return http.server.ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)


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
.caixa{position:absolute;border:2px solid var(--caixa);pointer-events:none}
.caixa.nao{border:1px dashed var(--suave)}.caixa.removida{opacity:.25}.caixa.dono{border-style:dotted}
.caixa b{position:absolute;left:-2px;top:-17px;background:var(--caixa);color:#fff;font-size:11px;line-height:14px;padding:0 3px;border-radius:3px}
.coluna{position:absolute;top:0;bottom:0;width:0;border-left:3px solid var(--caixa);pointer-events:none}
table{border-collapse:collapse;margin-top:10px}td,th{padding:3px 8px;border-bottom:1px solid var(--borda);text-align:left}
td input{width:5em}tr.removida td{opacity:.4;text-decoration:line-through}tr.removida td:last-child{text-decoration:none;opacity:1}
.linha{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0}
.suave{color:var(--suave)}
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
let PRE = null, E = null, ABA = "telas", sujo = false, versao = 0, ultimoOuro = null, temporizador = null;

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
function telaPre(id) { return PRE.telas.find(t => t.id === id); }
function telaEst(id) { return E.telas.find(t => t.id === id); }

function listaTelas() {
  const l = document.getElementById("lista"); l.replaceChildren();
  for (const t of E.telas) {
    const n = t.notas.filter(x => !x.removida).length;
    const rot = String(t.id).padStart(3, "0") + (t.conferida ? " ✓" : "") + (t.junta_em ? " = " + t.junta_em : "") + " · " + n;
    l.append(h("button", {class: t.id === E.tela_atual ? "on" : "", onclick: () => { E.tela_atual = t.id; desenhar(); }}, rot));
  }
}
function listaInstantes() {
  const l = document.getElementById("lista"); l.replaceChildren();
  E.instantes.forEach((i, k) => {
    const marca = i.estado === null ? "" : i.estado === "coluna" ? " ●" : i.estado === "nenhuma" ? " ○" : " ∅";
    l.append(h("button", {class: k === E.inst_atual ? "on" : "", onclick: () => { E.inst_atual = k; desenhar(); }}, String(k + 1).padStart(2, "0") + marca));
  });
}

function caixaDe(tp, n) {  /* retângulo da nota em % da imagem */
  const [rx0, ry0, rx1, ry1] = tp.painel, w = rx1 - rx0, hh = ry1 - ry0;
  let c = n.caixa;
  if (!c) { const p = tp.passo, y = tp.linhas_y[n.corda - 1]; c = [n.x_centro_quadro - 0.3 * p, y - 0.4 * p, n.x_centro_quadro + 0.3 * p, y + 0.4 * p]; }
  return {left: (c[0] - rx0) / w * 100, top: (c[1] - ry0) / hh * 100, width: (c[2] - c[0]) / w * 100, height: (c[3] - c[1]) / hh * 100};
}
function estiloCaixa(r) { return `left:${r.left}%;top:${r.top}%;width:${r.width}%;height:${r.height}%`; }

function desenharTela() {
  const c = document.getElementById("conteudo"); c.replaceChildren();
  if (E.tela_atual === null) { c.append("Sem telas."); return; }
  const tp = telaPre(E.tela_atual), te = telaEst(E.tela_atual);
  const mold = h("div", {class: "moldura"}, h("img", {src: "/" + tp.arquivo, draggable: "false"}));
  tp.nao_nota.forEach(n => { const r = caixaDe(tp, n); mold.append(h("div", {class: "caixa nao", style: estiloCaixa(r), title: "não é nota: " + n.casa})); });
  te.notas.forEach((n, i) => {
    const r = caixaDe(tp, n);
    mold.append(h("div", {class: "caixa" + (n.removida ? " removida" : "") + (n.origem === "dono" ? " dono" : ""), style: estiloCaixa(r)}, h("b", {}, i + 1)));
  });
  mold.addEventListener("click", ev => {
    const rc = mold.getBoundingClientRect();
    if (rc.width < 50) return;  /* imagem ainda não carregou */
    const fx = (ev.clientX - rc.left) / rc.width, fy = (ev.clientY - rc.top) / rc.height;
    const xImg = fx * (tp.painel[2] - tp.painel[0]) * tp.escala, yImg = fy * (tp.painel[3] - tp.painel[1]) * tp.escala;
    const xq = cliqueParaQuadro(xImg, tp.escala, tp.painel[0]), yq = cliqueParaQuadro(yImg, tp.escala, tp.painel[1]);
    te.notas.push({id: "d" + (E.proximo++), corda: cordaMaisProxima(yq, tp.linhas_y), casa: "", x_centro_quadro: Math.round(xq * 10) / 10,
      x_quadro: Math.round((xq - 0.25 * tp.passo) * 10) / 10, origem: "dono", removida: false});
    mudou(); desenhar(true);
  });
  const outras = E.telas.filter(t => t.id !== te.id);
  const sel = h("select", {onchange: ev => { te.junta_em = ev.target.value ? Number(ev.target.value) : null; mudou(); desenhar(); }},
    h("option", {value: ""}, "— única —"), outras.map(t => h("option", {value: t.id, selected: te.junta_em === t.id}, "igual à tela " + t.id)));
  const tabela = h("table", {}, h("tr", {}, h("th", {}, "#"), h("th", {}, "corda"), h("th", {}, "casa"), h("th", {}, ""), h("th", {}, "")));
  te.notas.forEach((n, i) => {
    const campo = h("input", {value: n.casa, "data-nota": n.id, inputmode: "numeric", oninput: ev => { n.casa = ev.target.value; mudou(); }});
    const acao = h("button", {onclick: () => {
      if (n.origem === "dono") te.notas.splice(i, 1); else n.removida = !n.removida;
      mudou(); desenhar(true); }}, n.origem === "dono" ? "apagar" : n.removida ? "restaurar" : "não é nota");
    tabela.append(h("tr", {class: n.removida ? "removida" : ""}, h("td", {}, i + 1), h("td", {}, n.corda), h("td", {}, campo),
      h("td", {}, n.origem === "dono" ? "acrescentada" : "modelo"), h("td", {}, acao)));
  });
  const sem = te.notas.filter(n => !n.removida && !String(n.casa).trim()).length;
  c.append(
    h("div", {class: "linha"}, h("b", {}, "Tela " + tp.id), h("span", {class: "suave"}, `ref. ${tp.quadro_ref_s}s · vista de ${tp.t_ini}s a ${tp.t_fim}s`)),
    h("div", {class: "linha"},
      h("button", {class: te.conferida ? "ok" : "", onclick: () => { te.conferida = !te.conferida; mudou(); desenhar(); }}, te.conferida ? "✓ conferida" : "tela conferida"),
      sel,
      h("button", {onclick: () => { const p = E.telas.find(t => !t.conferida && !t.junta_em && t.id !== te.id); if (p) { E.tela_atual = p.id; desenhar(); } }}, "próxima não conferida")),
    h("div", {class: "suave"}, "Clique na imagem para acrescentar uma nota que faltou (a corda sai da linha mais próxima). Corrija só a casa que estiver errada."),
    mold, sem ? h("div", {class: "linha", style: "color:var(--ruim)"}, sem + " nota(s) sem casa não serão gravadas") : "", tabela);
}

/* ---- aba INSTANTES ---- */
function desenharInstante() {
  const c = document.getElementById("conteudo"); c.replaceChildren();
  const k = E.inst_atual, ie = E.instantes[k], ip = PRE.instantes[k];
  if (!ie) { c.append("Sem instantes."); return; }
  const mold = h("div", {class: "moldura"}, h("img", {src: "/" + ip.arquivo, draggable: "false"}));
  const w = ip.recorte[2] - ip.recorte[0];
  if (ie.estado === "coluna") mold.append(h("div", {class: "coluna", style: `left:${(ie.coluna_x_quadro - ip.recorte[0]) / w * 100}%`}));
  const avancar = () => { if (E.inst_atual < E.instantes.length - 1) E.inst_atual++; desenhar(); };
  mold.addEventListener("click", ev => {
    const rc = mold.getBoundingClientRect(); if (rc.width < 50) return;
    const fx = (ev.clientX - rc.left) / rc.width;
    ie.estado = "coluna"; ie.coluna_x_quadro = Math.round(cliqueParaQuadro(fx * w * ip.escala, ip.escala, ip.recorte[0]) * 10) / 10;
    ie.tela = ip.tela_sugerida; mudou(); avancar();
  });
  const marcar = (estado) => { ie.estado = estado; ie.coluna_x_quadro = null; ie.tela = estado === "nenhuma" ? ip.tela_sugerida : null; mudou(); avancar(); };
  const feitos = E.instantes.filter(i => i.estado !== null).length;
  const atual = ie.estado === null ? "ainda sem resposta" : ie.estado === "coluna" ? "coluna em x=" + ie.coluna_x_quadro : ie.estado === "nenhuma" ? "nenhuma acesa" : "sem tablatura";
  c.append(
    h("div", {class: "linha"}, h("b", {}, `Instante ${k + 1}/${E.instantes.length}`), h("span", {class: "suave"}, `${feitos} respondidos · agora: ${atual}`)),
    h("div", {class: "linha"},
      h("button", {onclick: () => { if (E.inst_atual > 0) E.inst_atual--; desenhar(); }}, "← anterior"),
      h("button", {onclick: () => marcar("nenhuma")}, "nenhuma acesa (N)"),
      h("button", {onclick: () => marcar("sem_tablatura")}, "sem tablatura (S)"),
      h("button", {onclick: () => { ie.estado = null; ie.coluna_x_quadro = null; mudou(); desenhar(); }}, "limpar"),
      h("button", {onclick: avancar}, "próximo →")),
    h("div", {class: "suave"}, "Clique na COLUNA ACESA (a nota que está marcada agora). Depois da resposta a página avança."),
    mold);
  c._atalhos = {n: () => marcar("nenhuma"), s: () => marcar("sem_tablatura")};
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
  if (ABA === "telas") { listaTelas(); desenharTela(); if (focarUltima) { const campos = document.querySelectorAll("td input"); const u = campos[campos.length - 1]; if (u && !u.value) u.focus(); } }
  else { listaInstantes(); desenharInstante(); }
}
document.getElementById("aba-telas").onclick = () => { ABA = "telas"; desenhar(); };
document.getElementById("aba-inst").onclick = () => { ABA = "instantes"; desenhar(); };

(async function () {
  PRE = await (await fetch("/pre.json")).json();
  const salvo = await (await fetch("/ouro.json")).json();
  E = salvo.ferramenta && salvo.ferramenta.telas ? salvo.ferramenta : estadoInicial();
  if (salvo.ferramenta) ultimoOuro = salvo;
  document.getElementById("video").textContent = PRE.video;
  setStatus(salvo.ferramenta ? "trabalho anterior retomado" : "novo (nada salvo ainda)", "ok");
  desenhar();
})();
</script></body></html>
"""


def servir(pasta: Path, ouro: Path, porta: int) -> int:
    """Sobe o servidor e fica nele até Ctrl+C.

    Args:
        pasta: pasta do ``preparar``.
        ouro: arquivo do ouro.
        porta: porta TCP.

    Returns:
        Código de saída.
    """
    if not (pasta / "pre.json").exists():
        print(f"sem pre.json em {pasta}; rode `preparar` antes", file=sys.stderr)
        return 2
    servidor = criar_servidor(pasta, ouro, porta)
    print(f"ferramenta do ouro: http://127.0.0.1:{servidor.server_address[1]}/")
    print(f"o ouro é gravado a cada alteração em: {ouro}")
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
    """Ponto de entrada: ``preparar`` ou ``servir``.

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
    s = sub.add_parser("servir", help="serve a ferramenta de rotular (autosave)")
    s.add_argument("--pasta", type=Path, required=True)
    s.add_argument("--ouro", type=Path, required=True)
    s.add_argument("--porta", type=int, default=8099)
    args = ap.parse_args()
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
    return servir(args.pasta, args.ouro, args.porta)


if __name__ == "__main__":
    sys.exit(main())
