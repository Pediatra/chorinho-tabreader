"""Censo do acervo: o que cada vídeo dá para entregar (Fase 7, T7.1).

Motivo: escolher o ouro da Fase 8 pelo peso real de cada canal e dimensionar o rollout.
Por vídeo, grava **mais do que precisa**, para a análise não reabrir vídeo:

- ``info``: codec, resolução, fps e duração (``tab.leitor.info``);
- presença e caixa em 12 instantes, de 0,05 a 0,95 da duração (regra 10: um instante não
  responde "tem tablatura?"). A presença é o ``tab.telas.painel_do_quadro``, que usa a
  escolha de painel atual (``tab.painel``);
- em até 3 instantes com tablatura, uma janela de 10 s a 3 quadros/s com: há faixa
  (marcador vertical, ``tab.cursor``)? há destaque de cor? há troca de tela? há rolagem?
  (as duas últimas pela assinatura de tinta de ``tab.telas``);
- ``erro``: quando algo falha, a linha diz qual erro (``"erro": "Tipo: mensagem"``); nada
  é engolido. Linha com erro é refeita na próxima execução (a última linha da chave vale).

Retomável: a chave é ``caminho_relativo|tamanho|mtime``, porque o acervo ainda cresce.
Um arquivo que muda de tamanho ou de data ganha chave nova e é refeito.

Uso:
    python -m tab.censo --raiz /acervo --saida data/saida/censo/censo.jsonl
    python -m tab.censo --amostra 20 --saida data/saida/censo/custo_amostra.jsonl
    python -m tab.censo --piloto 3 --saida data/saida/censo/piloto/censo.jsonl \
        --folhas data/saida/censo/piloto   (3 vídeos por canal, semente fixa, uma folha
        por canal com 4 instantes por vídeo)

Cache de quadros (``tab.cache``): ``--cache`` lê o vídeo UMA vez e grava os quadros em
``data/cache/quadros``; ``--so-cache`` reprocessa só do cache (nunca abre o vídeo e aborta se
faltar quadro). Refazer um canal depois de um conserto, sem reler o acervo::

    python -m tab.censo --canal "cifra club" --so-cache \
        --saida data/saida/censo/refeito/canal_cifra_club.jsonl
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import re
import time
import unicodedata
from pathlib import Path

import numpy as np

from . import cache, leitor, telas, varredura
from .cache import FORMATO_PADRAO, FORMATOS, FaltaNoCache, ModoCache
from .caminhos import SAIDA, acervo
from .cursor import detectar_cursor
from .presenca_aval import folha

#: Frações da duração em que a presença é medida (12 instantes, de 0,05 a 0,95).
FRACOES_PRESENCA: tuple[float, ...] = tuple(
    round(float(f), 3) for f in np.linspace(0.05, 0.95, 12)
)

#: Tamanho da janela de análise, em segundos, e a taxa de amostragem dela.
JANELA_S = 10.0
QPS_JANELA = 3.0

#: No máximo esta quantidade de instantes com tablatura recebe uma janela.
MAX_JANELAS = 3

#: Quadros da janela (de 30) com cursor para dizer "há faixa".
MIN_QUADROS_FAIXA = 3

#: Quadros da janela com cor acima da fração mínima para dizer "há destaque de cor".
#: NÃO calibrado: a conferência de 30 vídeos (T7.3) é quem valida este número.
MIN_QUADROS_COR = 3
FRACAO_COR_MINIMA = 0.01

#: Semente do sorteio do piloto (3 vídeos por canal). Fixa: o piloto refeito pega os mesmos.
SEMENTE_PILOTO = 20261010

#: Quais dos 12 instantes de presença vão para a folha de conferência (4 por vídeo).
INSTANTES_FOLHA: tuple[int, ...] = (2, 5, 8, 11)

#: Abortar a execução se, depois deste número de vídeos, a fração de erros passar do limite.
MIN_VIDEOS_PARA_ABORTAR = 20
LIMITE_ERROS_ABORTAR = 0.5


def chave_do_arquivo(caminho: str, raiz: str) -> str:
    """Chave de retomada de um vídeo: caminho relativo, tamanho e mtime.

    Args:
        caminho: caminho absoluto do vídeo.
        raiz: raiz do acervo (o caminho da chave é relativo a ela).

    Returns:
        Texto ``"relativo|tamanho|mtime"``.
    """
    st = os.stat(caminho)
    return chave_de(os.path.relpath(caminho, raiz), st.st_size, st.st_mtime)


def chave_de(rel: str, tamanho: int, mtime: float) -> str:
    """Monta a chave de retomada a partir de seus três campos.

    Args:
        rel: caminho relativo à raiz do acervo.
        tamanho: tamanho do arquivo, em bytes.
        mtime: data de modificação, em segundos (truncada para inteiro).

    Returns:
        Texto ``"relativo|tamanho|mtime"``.
    """
    return f"{rel}|{int(tamanho)}|{int(mtime)}"


def ja_feitas(caminho_jsonl: str) -> set[str]:
    """Chaves já censadas **sem erro** (linhas com erro são refeitas).

    Args:
        caminho_jsonl: arquivo JSONL do censo (pode não existir).

    Returns:
        Conjunto de chaves; uma linha ruim (JSON inválido) é ignorada.
    """
    feitas: set[str] = set()
    if not os.path.exists(caminho_jsonl):
        return feitas
    with open(caminho_jsonl, encoding="utf-8") as fh:
        for linha in fh:
            try:
                registro = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if "chave" in registro and "erro" not in registro:
                feitas.add(registro["chave"])
            elif "chave" in registro:
                # erro declarado: a chave sai do conjunto, para ser refeita
                feitas.discard(registro["chave"])
    return feitas


def classificar(instantes: list[dict], janelas: list[dict]) -> dict:
    """Categoria do vídeo a partir das medidas de presença e das janelas.

    Args:
        instantes: medidas de presença; cada um tem ``tab`` (bool) quando foi lido.
        janelas: medidas de janela (``faixa``, ``cor``, ``troca_tela``, ``rolagem``).

    Returns:
        ``tablatura`` (bool), ``frac_tablatura`` (fração dos instantes lidos com tablatura),
        ``marcador`` (``faixa``, ``cor``, ``sem_marcador`` ou None sem janela) e ``forma``
        (``rolante``, ``paginado``, ``fixo`` ou None sem janela).
    """
    lidos = [i for i in instantes if "tab" in i]
    com_tab = sum(1 for i in lidos if i["tab"])
    frac = round(com_tab / len(lidos), 3) if lidos else 0.0
    resultado: dict = {
        "tablatura": com_tab > 0,
        "frac_tablatura": frac,
        "marcador": None,
        "forma": None,
    }
    if com_tab == 0 or not janelas:
        return resultado
    if any(j.get("faixa") for j in janelas):
        resultado["marcador"] = "faixa"
    elif any(j.get("cor") for j in janelas):
        resultado["marcador"] = "cor"
    else:
        resultado["marcador"] = "sem_marcador"
    if any(j.get("rolagem") for j in janelas):
        resultado["forma"] = "rolante"
    elif any(j.get("troca_tela") for j in janelas):
        resultado["forma"] = "paginado"
    else:
        resultado["forma"] = "fixo"
    return resultado


def escolher_instantes_com_tab(instantes: list[dict]) -> list[dict]:
    """Até ``MAX_JANELAS`` instantes com tablatura, espalhados (início, meio e fim).

    Args:
        instantes: medidas de presença, em ordem de tempo.

    Returns:
        Os instantes escolhidos, em ordem de tempo.
    """
    com_tab = [i for i in instantes if i.get("tab")]
    if len(com_tab) <= MAX_JANELAS:
        return com_tab
    indices = [0, len(com_tab) // 2, len(com_tab) - 1]
    return [com_tab[k] for k in indices]


def janela_em(t: float, duracao: float) -> tuple[float, float]:
    """Janela de ``JANELA_S`` segundos que começa em ``t`` (recuada se passar do fim).

    Args:
        t: instante de referência, em segundos.
        duracao: duração do vídeo, em segundos.

    Returns:
        ``(t0, t1)`` em segundos, com ``0 <= t0 < t1 <= duracao``.
    """
    t0 = max(0.0, min(t, duracao - JANELA_S))
    t1 = min(duracao, t0 + JANELA_S)
    return round(t0, 2), round(t1, 2)


def medir_janela(t0: float, t1: float, recortes: list[np.ndarray]) -> dict:
    """Mede a janela ``[t0, t1)`` a partir dos recortes do painel: faixa, cor, troca, rolagem.

    Args:
        t0: início da janela, em segundos.
        t1: fim da janela, em segundos.
        recortes: recorte do painel de cada quadro da janela, em ordem de tempo.

    Returns:
        Dicionário com ``t0``, ``t1``, ``quadros`` e as quatro medidas booleanas.
    """
    faixa_n = sum(1 for r in recortes if detectar_cursor(r) is not None)
    cor_n = sum(
        1
        for r in recortes
        if float(telas.mascara_colorida(r).mean()) > FRACAO_COR_MINIMA
    )
    assinaturas = [telas.assinatura(r) for r in recortes]
    troca = False
    rolagem = False
    for (ta, va, _ca), (tb, vb, _cb) in itertools.pairwise(assinaturas):
        if telas.distancia_iou(ta, tb, va, vb) <= telas.LIMIAR_TROCA:
            continue
        if telas.deslocamento_rolagem(ta, tb) is not None:
            rolagem = True
        else:
            troca = True
    return {
        "t0": t0,
        "t1": t1,
        "quadros": len(recortes),
        "faixa": faixa_n >= MIN_QUADROS_FAIXA,
        "faixa_quadros": faixa_n,
        "cor": cor_n >= MIN_QUADROS_COR,
        "cor_quadros": cor_n,
        "troca_tela": troca,
        "rolagem": rolagem,
    }


class _Fonte:
    """Quadros de UM vídeo: do cache quando há; senão do vídeo, gravando no cache.

    O vídeo só é aberto quando o quadro não está no cache e o modo não é só-cache. Quadro que o
    vídeo não entrega vai para ``sem_quadro``, que é gravado no ``meta.json``: assim uma leitura
    só-cache distingue "não há quadro" de "o cache está incompleto".
    """

    def __init__(
        self, caminho: str, modo: ModoCache, pasta: Path | None, sem_quadro: list[int]
    ) -> None:
        """Prepara a fonte; o vídeo só é aberto quando um quadro for pedido.

        Args:
            caminho: vídeo.
            modo: como usar o cache.
            pasta: diretório do cache do vídeo, ou ``None`` sem cache.
            sem_quadro: índices de presença que o vídeo não entregou em leitura anterior.
        """
        self.caminho = caminho
        self.modo = modo
        self.pasta = pasta
        self.sem_quadro: set[int] = set(sem_quadro)
        self._lei: leitor.Leitor | None = None

    def _do_video(self, t: float) -> np.ndarray | None:
        """Quadro do vídeo no instante ``t`` (abre o vídeo na primeira vez)."""
        if self._lei is None:
            self._lei = leitor.Leitor(self.caminho)
        return self._lei.ler(t)

    def presenca(self, indice: int, t: float) -> np.ndarray | None:
        """Quadro inteiro de presença número ``indice`` (instante ``t``, em segundos).

        Args:
            indice: posição em ``FRACOES_PRESENCA``.
            t: instante, em segundos.

        Returns:
            O quadro BGR, ou ``None`` se o vídeo não entregou quadro nesse instante.

        Raises:
            FaltaNoCache: modo só-cache e o quadro não está no cache.
        """
        if self.pasta is None:
            return self._do_video(t)
        arquivo = cache.caminho_do_quadro(
            self.pasta, f"presenca_{indice:02d}", self.modo.formato
        )
        if arquivo.exists():
            return cache.ler_quadro(arquivo)
        if indice in self.sem_quadro:
            return None
        if self.modo.so_cache:
            raise FaltaNoCache(f"presença {indice} (t={t}s) ausente: {self.caminho}")
        quadro = self._do_video(t)
        if quadro is None:
            self.sem_quadro.add(indice)
        else:
            cache.gravar_quadro(arquivo, quadro, self.modo.formato)
        return quadro

    def janela(
        self, t0: float, t1: float, rect: tuple[int, ...] | list[int]
    ) -> list[np.ndarray]:
        """Recortes do painel ``rect`` em cada quadro de ``[t0, t1)`` a ``QPS_JANELA``.

        Args:
            t0: início da janela, em segundos.
            t1: fim da janela, em segundos.
            rect: caixa do painel no quadro, ``(x0, y0, x1, y1)``.

        Returns:
            Os recortes BGR, em ordem de tempo (o mesmo que ``medir_janela`` recebe).

        Raises:
            FaltaNoCache: modo só-cache e a janela não está completa no cache.
        """
        caixa = tuple(int(v) for v in rect)
        formato = self.modo.formato
        pasta = None
        if self.pasta is not None:
            pasta = cache.pasta_da_janela(self.pasta, t0, caixa)
            meta = cache.ler_meta(pasta)
            if meta is not None:
                return [
                    cache.ler_quadro(
                        cache.caminho_do_quadro(pasta, f"{k:03d}", formato)
                    )
                    for k in range(int(meta["quadros"]))
                ]
            if self.modo.so_cache:
                raise FaltaNoCache(f"janela t0={t0} ausente: {self.caminho}")
        recortes = [
            telas.recortar(quadro, caixa)
            for _t, quadro in leitor.quadros(self.caminho, t0, t1, QPS_JANELA)
        ]
        if pasta is not None:
            for k, recorte in enumerate(recortes):
                cache.gravar_quadro(
                    cache.caminho_do_quadro(pasta, f"{k:03d}", formato),
                    recorte,
                    formato,
                )
            # o meta vem por último: janela sem meta é janela incompleta
            cache.gravar_meta(
                pasta,
                {
                    "t0": t0,
                    "t1": t1,
                    "rect": list(caixa),
                    "quadros": len(recortes),
                },
            )
        return recortes

    def fechar(self) -> None:
        """Libera o decodificador do vídeo, se foi aberto."""
        if self._lei is not None:
            self._lei.fechar()
            self._lei = None


def censar_video(
    caminho: str,
    raiz: str,
    com_janelas: bool = True,
    modo: ModoCache | None = None,
) -> dict:
    """Censo de um vídeo: uma linha JSON (a ser gravada pelo ``main``).

    Args:
        caminho: caminho absoluto do vídeo.
        raiz: raiz do acervo.
        com_janelas: se False, mede só a presença (estratificação); ``janelas`` vem vazio
            e ``janelas_medidas`` é False.
        modo: uso do cache de quadros; ``None`` lê sempre do vídeo, sem cache.

    Returns:
        O registro do vídeo. Falha declarada vai em ``erro``; o que já foi medido fica.

    Raises:
        FaltaNoCache: modo só-cache e algum quadro não está no cache. Não vira ``erro`` de
            linha: aborta a execução, porque o cache está incompleto para todo o lote.
    """
    modo = modo or ModoCache()
    rel = os.path.relpath(caminho, raiz)
    st = os.stat(caminho)
    chave = chave_de(rel, st.st_size, st.st_mtime)
    registro: dict = {
        "chave": chave,
        "arquivo": rel,
        "canal": rel.split(os.sep)[0],
        "tamanho": int(st.st_size),
        "mtime": int(st.st_mtime),
    }
    pasta = cache.pasta_do_video(chave, modo) if modo.ligado else None
    fonte: _Fonte | None = None
    try:
        meta = cache.ler_meta(pasta) if pasta is not None else None
        if modo.so_cache and meta is None:
            raise FaltaNoCache(f"sem meta no cache: {rel}")
        info = meta["info"] if meta is not None else leitor.info(caminho)
        registro["info"] = info
        registro["av1"] = info.get("codec") == "av1"
        duracao = float(info.get("duracao_s") or 0.0)
        if duracao <= 0.0:
            registro["erro"] = "duracao_desconhecida"
            return registro
        instantes: list[dict] = []
        fonte = _Fonte(
            caminho,
            modo,
            pasta,
            list(meta.get("sem_quadro", [])) if meta is not None else [],
        )
        try:
            for indice, f in enumerate(FRACOES_PRESENCA):
                t = round(duracao * f, 2)
                quadro = fonte.presenca(indice, t)
                if quadro is None:
                    instantes.append({"frac": f, "t": t, "erro": "sem_quadro"})
                    continue
                rect = telas.painel_do_quadro(quadro)
                instantes.append(
                    {
                        "frac": f,
                        "t": t,
                        "tab": rect is not None,
                        "rect": list(rect) if rect is not None else None,
                    }
                )
        finally:
            fonte.fechar()
        if pasta is not None and not modo.so_cache:
            # o meta da presença vem depois dos quadros: sem ele, o cache não está pronto
            cache.gravar_meta(
                pasta,
                {
                    "chave": chave,
                    "arquivo": rel,
                    "info": info,
                    "sem_quadro": sorted(fonte.sem_quadro),
                },
            )
        registro["instantes"] = instantes
        janelas: list[dict] = []
        if com_janelas:
            for inst in escolher_instantes_com_tab(instantes):
                t0, t1 = janela_em(inst["t"], duracao)
                try:
                    recortes = fonte.janela(t0, t1, inst["rect"])
                    janelas.append(medir_janela(t0, t1, recortes))
                except FaltaNoCache:
                    raise
                except Exception as exc:  # declarado, não engolido
                    janelas.append(
                        {"t0": t0, "t1": t1, "erro": f"{type(exc).__name__}: {exc}"}
                    )
        registro["janelas"] = janelas
        registro["janelas_medidas"] = com_janelas
        registro.update(classificar(instantes, janelas))
        n_erro = sum(1 for i in instantes if "erro" in i)
        if n_erro == len(instantes):
            registro["erro"] = "nenhum_quadro_lido"
        elif n_erro:
            registro["instantes_sem_quadro"] = n_erro
    except FaltaNoCache:
        raise
    except Exception as exc:  # declarado no registro, nunca silenciado
        registro["erro"] = f"{type(exc).__name__}: {exc}"
    finally:
        if fonte is not None:
            fonte.fechar()
    return registro


def sortear_piloto(
    por_canal: dict[str, list[str]], n: int, semente: int = SEMENTE_PILOTO
) -> dict[str, list[str]]:
    """``n`` vídeos sorteados por canal, com semente fixa (o mesmo piloto sempre).

    Args:
        por_canal: vídeos por canal, em ordem estável.
        n: vídeos por canal.
        semente: semente do sorteio.

    Returns:
        Canal -> vídeos sorteados, em ordem de nome.
    """
    rng = random.Random(semente)
    return {
        canal: sorted(rng.sample(vids, min(n, len(vids))))
        for canal, vids in por_canal.items()
    }


def slug_do_canal(canal: str, indice: int) -> str:
    """Nome de arquivo para um canal: ASCII minúsculo, ou ``canal_NN`` se não sobrar nada.

    Args:
        canal: nome da pasta do canal no acervo.
        indice: posição do canal (usada no fallback).

    Returns:
        Texto com letras, dígitos e ``_``.
    """
    ascii_ = unicodedata.normalize("NFKD", canal).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")
    return slug or f"canal_{indice:02d}"


def folha_do_canal(
    canal: str,
    indice: int,
    registros: list[dict],
    raiz: str,
    pasta: Path,
    modo: ModoCache | None = None,
) -> Path | None:
    """Folha de conferência de um canal: 4 instantes por vídeo, com a caixa desenhada.

    Args:
        canal: nome do canal.
        indice: posição do canal (para o nome do arquivo no fallback).
        registros: registros do censo dos vídeos sorteados do canal.
        raiz: raiz do acervo.
        pasta: pasta de saída; grava ``folha_<canal>.jpg``.
        modo: com cache ligado, os quadros vêm do cache (o vídeo não é reaberto).

    Returns:
        O caminho gravado, ou None se não houver quadro para mostrar.
    """
    modo = modo or ModoCache()
    itens: list[tuple[np.ndarray, tuple[int, int, int, int] | None, str]] = []
    for j, reg in enumerate(registros, start=1):
        if "instantes" not in reg:
            continue
        for idx in INSTANTES_FOLHA:
            inst = reg["instantes"][idx]
            if modo.ligado and "chave" in reg:
                arq = cache.caminho_do_quadro(
                    cache.pasta_do_video(reg["chave"], modo),
                    f"presenca_{idx:02d}",
                    modo.formato,
                )
                quadro = cache.ler_quadro(arq) if arq.exists() else None
            else:
                quadro = leitor.quadro_em(os.path.join(raiz, reg["arquivo"]), inst["t"])
            if quadro is None:
                continue
            rect = tuple(int(v) for v in inst["rect"]) if inst.get("rect") else None
            legenda = f"v{j} t={inst['t']:.0f}s tab={inst.get('tab')}"
            itens.append((quadro, rect, legenda))
    if not itens:
        return None
    pasta.mkdir(parents=True, exist_ok=True)
    return folha(
        itens,
        pasta / f"folha_{slug_do_canal(canal, indice)}.jpg",
        colunas=4,
        largura=640,
    )


def amostra_espalhada(videos: list[str], n: int) -> list[str]:
    """``n`` vídeos espalhados uniformemente pela lista (determinístico).

    Args:
        videos: lista ordenada de vídeos.
        n: quantidade desejada.

    Returns:
        Até ``n`` vídeos, sem repetição, na ordem da lista.
    """
    if n >= len(videos):
        return list(videos)
    indices = np.linspace(0, len(videos) - 1, n).round().astype(int)
    return [videos[i] for i in sorted({int(k) for k in indices})]


def main() -> int:
    """Faz o censo do acervo, uma linha JSON por vídeo, retomável."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=str(acervo()))
    ap.add_argument(
        "--saida",
        default=None,
        help="JSONL de saída (padrão: censo/censo.jsonl; com --canal, censo/canal_<nome>.jsonl)",
    )
    ap.add_argument("--canais", nargs="*", default=None)
    ap.add_argument(
        "--canal",
        default=None,
        help="só este canal (nome exato da pasta); saída separada por padrão",
    )
    ap.add_argument(
        "--cache",
        action="store_true",
        help="lê o cache de quadros quando há e grava o que falta (data/cache/quadros)",
    )
    ap.add_argument(
        "--so-cache",
        action="store_true",
        help="reprocessa SÓ do cache: nunca abre o vídeo; quadro ausente aborta",
    )
    ap.add_argument(
        "--formato",
        choices=sorted(FORMATOS),
        default=FORMATO_PADRAO,
        help="formato do cache, sem perda (png é o padrão)",
    )
    ap.add_argument(
        "--amostra",
        type=int,
        default=0,
        help="só N vídeos espalhados pela lista (medição de custo); 0 = todos",
    )
    ap.add_argument("--limite", type=int, default=0, help="máximo de vídeos novos")
    ap.add_argument(
        "--janelas-por-canal",
        type=int,
        default=0,
        help="estratificação: janelas só em N vídeos espalhados por canal (0 = todos)",
    )
    ap.add_argument(
        "--piloto",
        type=int,
        default=0,
        help="N vídeos sorteados por canal (semente fixa); grava as folhas em --folhas",
    )
    ap.add_argument(
        "--folhas",
        default="",
        help="pasta das folhas de conferência por canal (usada com --piloto)",
    )
    ap.add_argument(
        "--sem-janelas",
        action="store_true",
        help="mede só a presença (medição de custo)",
    )
    args = ap.parse_args()

    canais = [args.canal] if args.canal else args.canais
    if args.saida:
        saida = args.saida
    elif args.canal:
        saida = str(SAIDA / "censo" / f"canal_{slug_do_canal(args.canal, 0)}.jsonl")
    else:
        saida = str(SAIDA / "censo" / "censo.jsonl")
    modo = ModoCache(
        usar=args.cache or args.so_cache,
        so_cache=args.so_cache,
        formato=args.formato,
    )
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    por_canal = varredura.canais_e_videos(args.raiz, canais)
    if args.canal and args.canal not in por_canal:
        print(f"canal não achado no acervo: {args.canal!r}", flush=True)
        return 2
    if args.piloto:
        por_canal = sortear_piloto(por_canal, args.piloto)
    todos = [v for canal in por_canal.values() for v in canal]
    if args.amostra:
        todos = amostra_espalhada(todos, args.amostra)
    com_janela: set[str] = set(todos)
    if args.sem_janelas:
        com_janela = set()
    elif args.janelas_por_canal:
        com_janela = set()
        for vids in por_canal.values():
            com_janela.update(amostra_espalhada(vids, args.janelas_por_canal))
    feitas = ja_feitas(saida)
    pendentes = []
    for v in todos:
        if chave_do_arquivo(v, args.raiz) not in feitas:
            pendentes.append(v)
    print(
        f"vídeos: {len(todos)} | já feitos: {len(todos) - len(pendentes)} | "
        f"pendentes: {len(pendentes)} -> {saida} | modo: {_descreve(modo)}",
        flush=True,
    )

    t_inicio = time.time()
    processados = 0
    erros = 0
    with open(saida, "a", encoding="utf-8") as fh:
        for v in pendentes:
            if args.limite and processados >= args.limite:
                break
            try:
                registro = censar_video(v, args.raiz, v in com_janela, modo)
            except FaltaNoCache as exc:
                print(f"ABORTADO (só-cache incompleto): {exc}", flush=True)
                return 1
            except OSError as exc:  # arquivo sumiu entre a listagem e a leitura
                registro = {
                    "arquivo": os.path.relpath(v, args.raiz),
                    "erro": f"{type(exc).__name__}: {exc}",
                }
            if "erro" in registro:
                erros += 1
                if (
                    processados + 1 >= MIN_VIDEOS_PARA_ABORTAR
                    and erros / (processados + 1) > LIMITE_ERROS_ABORTAR
                ):
                    print(
                        f"ABORTADO: {erros} de {processados + 1} com erro: bug "
                        f"sistemático? último: {registro['erro']}",
                        flush=True,
                    )
                    return 1
            fh.write(json.dumps(registro, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            processados += 1
            print(
                f"[{processados}/{len(pendentes)}] {registro['arquivo'][:70]} "
                f"av1={registro.get('av1')} tab={registro.get('tablatura')} "
                f"erro={registro.get('erro')} "
                f"t={time.time() - t_inicio:.0f}s",
                flush=True,
            )
    print(
        f"fim: {processados} vídeos em {(time.time() - t_inicio) / 60:.1f} min, "
        f"{erros} com erro",
        flush=True,
    )
    if args.piloto and args.folhas:
        _folhas_do_piloto(saida, args.raiz, por_canal, Path(args.folhas), modo)
    return 0


def _descreve(modo: ModoCache) -> str:
    """Texto curto do modo de cache, para a primeira linha da execução.

    Args:
        modo: modo de cache da execução.

    Returns:
        ``sem cache``, ``cache (leitura e gravação)`` ou ``só cache`` mais o formato.
    """
    if modo.so_cache:
        return f"só cache ({modo.formato})"
    if modo.usar:
        return f"cache ({modo.formato})"
    return "sem cache"


def _folhas_do_piloto(
    saida: str,
    raiz: str,
    por_canal: dict[str, list[str]],
    pasta: Path,
    modo: ModoCache | None = None,
) -> None:
    """Uma folha por canal, com o último registro de cada vídeo sorteado.

    Args:
        saida: JSONL do censo (a última linha de cada arquivo vale).
        raiz: raiz do acervo.
        por_canal: canal -> vídeos sorteados.
        pasta: pasta das folhas.
        modo: com cache ligado, as folhas saem do cache.
    """
    ultimo: dict[str, dict] = {}
    with open(saida, encoding="utf-8") as fh:
        for linha in fh:
            try:
                reg = json.loads(linha)
            except json.JSONDecodeError:
                continue
            ultimo[reg.get("arquivo", "")] = reg
    for indice, (canal, vids) in enumerate(por_canal.items(), start=1):
        registros = [
            ultimo[os.path.relpath(v, raiz)]
            for v in vids
            if os.path.relpath(v, raiz) in ultimo
        ]
        caminho = folha_do_canal(canal, indice, registros, raiz, pasta, modo)
        print(f"folha {canal}: {caminho}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
