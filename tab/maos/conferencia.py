"""Folha de conferência do censo de mãos (M0): um quadro por vídeo, para o dono olhar.

Por que existe: o critério de aceite do censo é o dono olhar uma folha de 30 vídeos
sorteados e dizer se o censo concorda com o que vê (meta: concordância de 90 % ou mais).
Os 30 vídeos NÃO podem ser os do piloto: os parâmetros do detector foram escolhidos
olhando o piloto, e medir no próprio conjunto de ajuste não diz nada. Por isso o sorteio
exclui as chaves do piloto (``--excluir``) e é estratificado por canal, para a folha
cobrir os canais e não só os de mais vídeos.

Cada célula mostra o quadro do cache com o que o censo afirmou: mão L em verde, mão R em
magenta, mão dentro da tablatura em cinza, rosto em ciano, painel da TAB em amarelo. O
rodapé traz o número, o canal e as afirmações (``E`` há mão L, ``D`` há mão R, ``2+``
duas mãos de qualquer lado, e a vista). O manifesto ``<saida>.json`` guarda o mesmo, mais
o campo ``dono``, que o dono preenche depois.

Uso::

    python -m tab.maos_conferencia --censo data/saida/maos/censo_maos.jsonl \\
        --excluir data/saida/maos/piloto_c0.3_b2.jsonl --n 30 --semente 20261013 \\
        --saida data/saida/maos/conferencia_30
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from tab.comum.cache import ModoCache, caminho_do_quadro, pasta_do_video
from tab.comum.caminhos import CENSO_MAOS, CONFERENCIA_MAOS_30
from tab.maos.tabela import resumo_do_quadro

#: Vídeos (depois da exclusão) para um canal ganhar 1 vaga garantida.
MINIMO_VIDEOS_CANAL = 10

#: Tamanho de uma célula da folha, e a faixa do rodapé dentro dela.
CELULA_LARGURA = 640
CELULA_ALTURA = 480
RODAPE_ALTURA = 56

#: Layout da folha: 2 colunas por 5 linhas, 10 células por arquivo.
COLUNAS = 2
POR_FOLHA = 10

#: Qualidade do JPEG da folha.
QUALIDADE_JPEG = 85

#: Cores em BGR (o OpenCV lê em BGR).
COR_L = (0, 220, 0)
COR_R = (255, 0, 255)
COR_NA_TAB = (128, 128, 128)
COR_ROSTO = (255, 255, 0)
COR_PAINEL = (0, 255, 255)
COR_POR_LADO = {"L": COR_L, "R": COR_R}


def _ordem(video: dict) -> tuple[str, str]:
    """Chave de ordenação (canal, chave) de um vídeo.

    Args:
        video: registro do censo.

    Returns:
        A dupla ``(canal, chave)``.
    """
    return (video["canal"], video["chave"])


def _alocar_vagas(
    contagem: dict[str, int], n: int, garantidos: list[str]
) -> dict[str, int]:
    """Quantas vagas cada canal recebe: garantidas, depois maiores restos.

    Método dos maiores restos (Hamilton) sobre a sobra, com corte por canal: um canal
    nunca recebe mais vagas do que tem vídeos, e a vaga cortada vai para o próximo maior
    resto que ainda tem vídeo sobrando. A conta é inteira, sem ponto flutuante: a cota de
    cada canal é ``sobra * vídeos / total``, guardada como quociente e resto.

    Args:
        contagem: vídeos elegíveis por canal (depois da exclusão).
        n: vagas pedidas; menor que o total de vídeos elegíveis.
        garantidos: canais com ``MINIMO_VIDEOS_CANAL`` ou mais vídeos.

    Returns:
        Vagas por canal; a soma é ``n``.
    """
    total = sum(contagem.values())
    sobra = n - len(garantidos)
    numeradores = {c: sobra * contagem[c] for c in contagem}
    vagas = {c: (1 if c in garantidos else 0) for c in contagem}
    for c in contagem:
        vagas[c] = min(vagas[c] + numeradores[c] // total, contagem[c])
    restam = n - sum(vagas.values())
    ordem = sorted(contagem, key=lambda c: (-(numeradores[c] % total), c))
    while restam > 0:
        for c in ordem:
            if restam == 0:
                break
            if vagas[c] < contagem[c]:
                vagas[c] += 1
                restam -= 1
    return vagas


def sortear(videos: list[dict], n: int, semente: int, excluir: set[str]) -> list[dict]:
    """Sorteia ``n`` vídeos do censo, estratificado por canal, de forma reproduzível.

    Descarta os vídeos de ``excluir`` (o piloto), os sem quadros e as chaves repetidas.
    Cada canal com ``MINIMO_VIDEOS_CANAL`` ou mais vídeos ganha 1 vaga garantida, e a
    sobra é repartida por ``_alocar_vagas``. Dentro de cada canal, a escolha usa um único
    ``random.Random(semente)``, percorrendo os canais em ordem alfabética.

    Args:
        videos: registros do censo de mãos (``chave``, ``canal``, ``quadros``).
        n: vagas pedidas. Se passar do total elegível, devolve todos.
        semente: semente do sorteio.
        excluir: chaves que não podem entrar (o piloto).

    Returns:
        Os vídeos sorteados, ordenados por (canal, chave).

    Raises:
        ValueError: se ``n`` for negativo, ou menor que o número de canais garantidos
            (a regra de 1 vaga por canal com 10 ou mais vídeos não cabe).
    """
    if n < 0:
        raise ValueError("n não pode ser negativo")
    elegiveis: list[dict] = []
    vistas: set[str] = set()
    for video in videos:
        chave = video["chave"]
        if chave in excluir or chave in vistas or not video["quadros"]:
            continue
        vistas.add(chave)
        elegiveis.append(video)
    if n >= len(elegiveis):
        return sorted(elegiveis, key=_ordem)

    por_canal: dict[str, list[dict]] = {}
    for video in elegiveis:
        por_canal.setdefault(video["canal"], []).append(video)
    canais = sorted(por_canal)
    contagem = {c: len(por_canal[c]) for c in canais}
    garantidos = [c for c in canais if contagem[c] >= MINIMO_VIDEOS_CANAL]
    if n < len(garantidos):
        raise ValueError(
            f"n={n} é menor que o número de canais com {MINIMO_VIDEOS_CANAL} ou mais "
            f"vídeos ({len(garantidos)}): a vaga garantida não cabe"
        )

    vagas = _alocar_vagas(contagem, n, garantidos)
    rng = random.Random(semente)
    escolhidos: list[dict] = []
    for canal in canais:
        candidatos = sorted(por_canal[canal], key=lambda v: v["chave"])
        escolhidos.extend(rng.sample(candidatos, vagas[canal]))
    return sorted(escolhidos, key=_ordem)


def escolher_quadro(video: dict, rng: random.Random) -> dict:
    """Escolhe um quadro do vídeo ao acaso.

    Args:
        video: registro do censo com ``quadros`` não vazia.
        rng: gerador do sorteio dos quadros.

    Returns:
        O registro do quadro escolhido.
    """
    return rng.choice(video["quadros"])


def _ascii(texto: str) -> str:
    """Texto sem acento, para o OpenCV desenhar (as fontes do OpenCV são só ASCII).

    Args:
        texto: nome em português.

    Returns:
        O mesmo texto com os acentos decompostos e descartados.
    """
    decomposto = unicodedata.normalize("NFKD", texto)
    return decomposto.encode("ascii", "ignore").decode("ascii")


def desenhar(video: dict, quadro: dict, modo: ModoCache) -> np.ndarray:
    """Quadro do cache com as afirmações do censo desenhadas por cima.

    Args:
        video: registro do censo (``chave``).
        quadro: registro do quadro (``i``, ``rect``, ``rostos``, ``maos``).
        modo: cache de onde sai o PNG do quadro.

    Returns:
        O quadro inteiro, em resolução nativa, em BGR.

    Raises:
        FileNotFoundError: se o quadro não está no cache.
    """
    pasta = pasta_do_video(video["chave"], modo)
    arquivo = caminho_do_quadro(pasta, f"presenca_{quadro['i']:02d}", modo.formato)
    img = cv2.imread(str(arquivo))
    if img is None:
        raise FileNotFoundError(f"quadro não está no cache: {arquivo}")
    esp = max(2, img.shape[1] // 400)
    if quadro["rect"]:
        x0, y0, x1, y1 = quadro["rect"]
        cv2.rectangle(img, (x0, y0), (x1, y1), COR_PAINEL, esp)
    for rosto in quadro["rostos"]:
        x0, y0, x1, y1 = rosto["caixa"]
        cv2.rectangle(img, (x0, y0), (x1, y1), COR_ROSTO, esp)
    for mao in quadro["maos"]:
        cor = COR_NA_TAB if mao["na_tab"] else COR_POR_LADO[mao["lado"]]
        for x, y in mao["pts"]:
            cv2.circle(img, (x, y), esp * 2, cor, -1)
        x0, y0, x1, y1 = mao["caixa"]
        cv2.rectangle(img, (x0, y0), (x1, y1), cor, esp)
        cv2.putText(
            img,
            mao["lado"],
            (x0, max(30, y0 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            esp * 0.8,
            cor,
            esp,
        )
    return img


def celula(video: dict, quadro: dict, numero: int, modo: ModoCache) -> np.ndarray:
    """Uma célula da folha: o quadro desenhado, reduzido, com o rodapé.

    Args:
        video: registro do censo.
        quadro: quadro escolhido do vídeo.
        numero: número da célula (1 a n), impresso no rodapé.
        modo: cache de onde sai o quadro.

    Returns:
        Imagem BGR de ``CELULA_LARGURA`` por ``CELULA_ALTURA``, com a proporção do quadro
        preservada e o resto preenchido com preto.
    """
    img = desenhar(video, quadro, modo)
    h, w = img.shape[:2]
    area = CELULA_ALTURA - RODAPE_ALTURA
    escala = min(CELULA_LARGURA / w, area / h)
    nw, nh = max(1, round(w * escala)), max(1, round(h * escala))
    cel = np.zeros((CELULA_ALTURA, CELULA_LARGURA, 3), np.uint8)
    x, y = (CELULA_LARGURA - nw) // 2, (area - nh) // 2
    cel[y : y + nh, x : x + nw] = cv2.resize(
        img, (nw, nh), interpolation=cv2.INTER_AREA
    )
    afirma = resumo_do_quadro(quadro)
    linha1 = f"{numero:02d}  {_ascii(video['canal'])[:14]}"
    linha2 = (
        f"E={int(afirma['esquerda'])} D={int(afirma['direita'])} "
        f"2+={int(afirma['duas_qualquer'])} {afirma['vista']}"
    )
    fonte = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(cel, linha1, (8, area + 22), fonte, 0.6, (255, 255, 255), 2)
    cv2.putText(cel, linha2, (8, area + 46), fonte, 0.6, (255, 255, 255), 2)
    return cel


def montar_folhas(celulas: list[np.ndarray], saida: Path) -> list[Path]:
    """Junta as células em folhas de ``POR_FOLHA`` e grava ``<saida>_<k>.jpg``.

    Args:
        celulas: células prontas, na ordem da folha.
        saida: prefixo dos arquivos (sem extensão).

    Returns:
        Os caminhos das folhas gravadas, na ordem.

    Raises:
        OSError: se o OpenCV não gravar uma folha.
    """
    vazia = np.zeros((CELULA_ALTURA, CELULA_LARGURA, 3), np.uint8)
    arquivos: list[Path] = []
    for inicio in range(0, len(celulas), POR_FOLHA):
        bloco = celulas[inicio : inicio + POR_FOLHA]
        bloco += [vazia] * (POR_FOLHA - len(bloco))
        linhas = [
            np.hstack(bloco[i : i + COLUNAS]) for i in range(0, POR_FOLHA, COLUNAS)
        ]
        arquivo = saida.parent / f"{saida.name}_{inicio // POR_FOLHA + 1}.jpg"
        ok = cv2.imwrite(
            str(arquivo),
            np.vstack(linhas),
            [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG],
        )
        if not ok:
            raise OSError(f"cv2 não gravou a folha {arquivo}")
        arquivos.append(arquivo)
    return arquivos


def _ler_jsonl(caminho: Path) -> list[dict]:
    """Lê um jsonl (um registro por linha), pulando linhas em branco.

    Args:
        caminho: arquivo jsonl.

    Returns:
        Os registros, na ordem do arquivo.
    """
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas if linha.strip()]


def main() -> int:
    """CLI: sorteia os vídeos, desenha as folhas e grava o manifesto.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--censo", type=Path, default=CENSO_MAOS)
    ap.add_argument(
        "--excluir", type=Path, help="jsonl cujas chaves ficam fora (o piloto)"
    )
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--semente", type=int, default=20261013)
    ap.add_argument("--saida", type=Path, default=CONFERENCIA_MAOS_30)
    args = ap.parse_args()

    videos = _ler_jsonl(args.censo)
    excluir = {r["chave"] for r in _ler_jsonl(args.excluir)} if args.excluir else set()
    escolhidos = sortear(videos, args.n, args.semente, excluir)
    contagem = Counter(v["canal"] for v in escolhidos)
    print(f"{len(escolhidos)} vídeos entraram (de {len(videos)} no censo):")
    for canal in sorted(contagem):
        print(f"  {canal}: {contagem[canal]}")

    modo = ModoCache()
    rng = random.Random(args.semente + 1)
    pares = [(v, escolher_quadro(v, rng)) for v in escolhidos]
    celulas = [celula(v, q, k, modo) for k, (v, q) in enumerate(pares, 1)]
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    for folha in montar_folhas(celulas, args.saida):
        print(f"folha: {folha}")

    manifesto = []
    for k, (video, quadro) in enumerate(pares, 1):
        afirma = {
            chave: valor
            for chave, valor in resumo_do_quadro(quadro).items()
            if chave != "palma_px"
        }
        manifesto.append(
            {
                "n": k,
                "canal": video["canal"],
                "arquivo": video["arquivo"],
                "chave": video["chave"],
                "quadro": quadro["i"],
                "t": quadro["t"],
                "afirma": afirma,
                "dono": {"esquerda": None, "direita": None, "obs": ""},
            }
        )
    caminho = args.saida.parent / f"{args.saida.name}.json"
    caminho.write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"manifesto: {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
