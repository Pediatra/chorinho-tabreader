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
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import time

import numpy as np

from . import leitor, telas, varredura
from .caminhos import SAIDA, acervo
from .cursor import detectar_cursor

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


def medir_janela(
    caminho: str, t0: float, t1: float, rect: list[int] | tuple[int, ...]
) -> dict:
    """Mede a janela ``[t0, t1)`` do painel ``rect``: faixa, cor, troca e rolagem.

    Args:
        caminho: vídeo.
        t0: início da janela, em segundos.
        t1: fim da janela, em segundos.
        rect: caixa do painel no quadro, ``(x0, y0, x1, y1)``.

    Returns:
        Dicionário com ``t0``, ``t1``, ``quadros`` e as quatro medidas booleanas.
    """
    recorte_rect = tuple(int(v) for v in rect)
    recortes = [
        telas.recortar(quadro, recorte_rect)
        for _t, quadro in leitor.quadros(caminho, t0, t1, QPS_JANELA)
    ]
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


def censar_video(caminho: str, raiz: str, com_janelas: bool = True) -> dict:
    """Censo de um vídeo: uma linha JSON (a ser gravada pelo ``main``).

    Args:
        caminho: caminho absoluto do vídeo.
        raiz: raiz do acervo.
        com_janelas: se False, mede só a presença (estratificação); ``janelas`` vem vazio
            e ``janelas_medidas`` é False.

    Returns:
        O registro do vídeo. Falha declarada vai em ``erro``; o que já foi medido fica.
    """
    rel = os.path.relpath(caminho, raiz)
    st = os.stat(caminho)
    registro: dict = {
        "chave": chave_de(rel, st.st_size, st.st_mtime),
        "arquivo": rel,
        "canal": rel.split(os.sep)[0],
        "tamanho": int(st.st_size),
        "mtime": int(st.st_mtime),
    }
    try:
        info = leitor.info(caminho)
        registro["info"] = info
        registro["av1"] = info.get("codec") == "av1"
        duracao = float(info.get("duracao_s") or 0.0)
        if duracao <= 0.0:
            registro["erro"] = "duracao_desconhecida"
            return registro
        instantes: list[dict] = []
        lei = leitor.Leitor(caminho)
        try:
            for f in FRACOES_PRESENCA:
                t = round(duracao * f, 2)
                quadro = lei.ler(t)
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
            lei.fechar()
        registro["instantes"] = instantes
        janelas: list[dict] = []
        if com_janelas:
            for inst in escolher_instantes_com_tab(instantes):
                t0, t1 = janela_em(inst["t"], duracao)
                try:
                    janelas.append(medir_janela(caminho, t0, t1, inst["rect"]))
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
    except Exception as exc:  # declarado no registro, nunca silenciado
        registro["erro"] = f"{type(exc).__name__}: {exc}"
    return registro


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
    ap.add_argument("--saida", default=str(SAIDA / "censo" / "censo.jsonl"))
    ap.add_argument("--canais", nargs="*", default=None)
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
        "--sem-janelas",
        action="store_true",
        help="mede só a presença (medição de custo)",
    )
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    por_canal = varredura.canais_e_videos(args.raiz, args.canais)
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
    feitas = ja_feitas(args.saida)
    pendentes = []
    for v in todos:
        if chave_do_arquivo(v, args.raiz) not in feitas:
            pendentes.append(v)
    print(
        f"vídeos: {len(todos)} | já feitos: {len(todos) - len(pendentes)} | "
        f"pendentes: {len(pendentes)} -> {args.saida}",
        flush=True,
    )

    t_inicio = time.time()
    processados = 0
    erros = 0
    with open(args.saida, "a", encoding="utf-8") as fh:
        for v in pendentes:
            if args.limite and processados >= args.limite:
                break
            try:
                registro = censar_video(v, args.raiz, v in com_janela)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
