"""Folhas de auditoria do painel escolhido pelo produto r2021 (rodada 0216).

Para cada tela com passo do produto (``data/saida/audio/r2021/produtos``), lê o quadro
no meio da primeira exibição, roda ``escolher_ou_mascara`` e desenha o painel no quadro
inteiro: retângulo verde no recorte e linhas das cordas em vermelho. Os quadros viram
folhas de 4 colunas por 3 linhas em ``folhas_r2021/``, e as medidas de cada tela vão para
``telas_r2021.json``.

Uso:
    python data/saida/tablatura/recusa/folhas_r2021.py
"""

from __future__ import annotations

import json
import math
import time
import unicodedata
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tab.comum.arquivos import gravar_atomico, ler_json
from tab.comum.caminhos import acervo
from tab.comum.leitor import quadro_em
from tab.tablatura.leitura import painel

RAIZ = Path(__file__).resolve().parents[4]
PRODUTOS = RAIZ / "data/saida/audio/r2021/produtos"
SAIDA = Path(__file__).resolve().parent
FOLHAS = SAIDA / "folhas_r2021"
TELAS_JSON = SAIDA / "telas_r2021.json"
LEIAME = SAIDA / "LEIAME.json"

LARGURA_TILE = 480
ALTURA_FAIXA = 22
COLUNAS = 4
LINHAS = 3
POR_FOLHA = COLUNAS * LINHAS
QUALIDADE_JPEG = 80
COR_RETANGULO = (0, 200, 0)
COR_CORDAS = (0, 0, 255)


def ascii_seguro(texto: str) -> str:
    """Troca cada caractere não-ASCII por ``?``, mantendo o comprimento.

    Args:
        texto: texto de entrada.

    Returns:
        O texto só com caracteres ASCII.
    """
    return "".join(c if ord(c) < 128 else "?" for c in texto)


def caminho_do_video(arquivo: str) -> Path:
    """Caminho do vídeo no acervo, tolerando NFC e NFD no nome.

    Args:
        arquivo: caminho relativo ao acervo, como está no produto.

    Returns:
        O primeiro caminho que existe; se nenhum existir, o caminho cru.
    """
    raiz = acervo()
    cru = raiz / arquivo
    if cru.exists():
        return cru
    for forma in ("NFC", "NFD"):
        alternativo = raiz / unicodedata.normalize(forma, arquivo)
        if alternativo.exists():
            return alternativo
    return cru


def _texto(
    img: np.ndarray,
    texto: str,
    pos: tuple[int, int],
    escala: float,
    cor: tuple[int, int, int],
    espessura: int,
) -> None:
    """Escreve ASCII numa imagem (atalho para ``cv2.putText``).

    Args:
        img: imagem onde escrever (alterada no lugar).
        texto: texto ASCII.
        pos: posição (x, y) da base do texto.
        escala: escala da fonte.
        cor: cor BGR.
        espessura: espessura da linha do texto.
    """
    cv2.putText(
        img,
        texto,
        pos,
        cv2.FONT_HERSHEY_SIMPLEX,
        escala,
        cor,
        espessura,
        cv2.LINE_AA,
    )


def montar_tile(
    quadro: np.ndarray | None,
    candidato: painel.Candidato | None,
    rotulo: str,
) -> np.ndarray:
    """Um tile da folha: o quadro reduzido a 480 px, com o painel desenhado.

    Args:
        quadro: quadro inteiro em BGR, ou None se o vídeo não deu quadro.
        candidato: painel escolhido, ou None se não houve painel.
        rotulo: texto ASCII da faixa branca do topo.

    Returns:
        A imagem do tile (faixa branca em cima, quadro embaixo).
    """
    if quadro is None:
        img = np.zeros((270, LARGURA_TILE, 3), np.uint8)
        _texto(img, "SEM QUADRO", (130, 140), 1.0, COR_CORDAS, 2)
    else:
        altura, largura = quadro.shape[:2]
        s = LARGURA_TILE / largura
        img = cv2.resize(
            quadro,
            (LARGURA_TILE, round(altura * s)),
            interpolation=cv2.INTER_AREA,
        )
        if candidato is not None:
            x0, y0 = candidato.x0, candidato.y0
            w = candidato.roi.shape[1]
            h = candidato.roi.shape[0]
            cv2.rectangle(
                img,
                (round(x0 * s), round(y0 * s)),
                (round((x0 + w) * s), round((y0 + h) * s)),
                COR_RETANGULO,
                2,
            )
            for ly in candidato.grade.linhas_y:
                yy = round((y0 + int(ly)) * s)
                cv2.line(
                    img,
                    (round(x0 * s), yy),
                    (round((x0 + w) * s), yy),
                    COR_CORDAS,
                    1,
                )
        else:
            _texto(img, "SEM PAINEL", (120, img.shape[0] // 2), 1.0, COR_CORDAS, 2)
    faixa = np.full((ALTURA_FAIXA, LARGURA_TILE, 3), 255, np.uint8)
    _texto(faixa, rotulo, (4, 15), 0.5, (0, 0, 0), 1)
    return np.vstack([faixa, img])


def montar_folha(tiles: list[np.ndarray]) -> np.ndarray:
    """Junta até 12 tiles numa folha de 4 colunas por 3 linhas.

    Args:
        tiles: os tiles da folha, na ordem de leitura.

    Returns:
        A folha em BGR; as células vazias ficam pretas.
    """
    altura = max(t.shape[0] for t in tiles)
    folha = np.zeros((LINHAS * altura, COLUNAS * LARGURA_TILE, 3), np.uint8)
    for i, tile in enumerate(tiles):
        lin, col = divmod(i, COLUNAS)
        y = lin * altura
        x = col * LARGURA_TILE
        folha[y : y + tile.shape[0], x : x + LARGURA_TILE] = tile
    return folha


def _e_pauta(candidato: painel.Candidato) -> bool | None:
    """``painel.e_pauta`` do recorte escolhido, ou None se a medida falhar.

    Args:
        candidato: painel escolhido.

    Returns:
        True ou False, ou None se ``e_pauta`` levantar exceção.
    """
    try:
        return painel.e_pauta(candidato.roi, [int(y) for y in candidato.grade.linhas_y])
    except Exception:
        return None


def registro_da_tela(
    produto: str,
    k: int,
    tela: dict[str, Any],
    t: float,
    arquivo: str,
    folha: str,
    candidato: painel.Candidato | None,
    notas: list[dict[str, Any]],
    erro: str | None,
) -> dict[str, Any]:
    """Uma linha de ``telas_r2021.json``, com as medidas da tela.

    Args:
        produto: slug do produto (nome do json sem extensão, 30 chars ASCII).
        k: índice do produto (1 a 35).
        tela: a tela do produto.
        t: instante lido, em segundos.
        arquivo: caminho do vídeo, relativo ao acervo.
        folha: nome do arquivo da folha onde o tile caiu.
        candidato: painel escolhido, ou None.
        notas: notas do produto (filtradas pela tela aqui).
        erro: mensagem se ``escolher_ou_mascara`` levantou exceção.

    Returns:
        O registro da tela.
    """
    tid = tela["id"]
    da_tela = [n for n in notas if n.get("tela") == tid]
    confs = [float(n["confianca"]) for n in da_tela if n.get("confianca") is not None]
    conf_media = round(sum(confs) / len(confs), 4) if confs else None
    if candidato is None:
        medidas: dict[str, Any] = {
            "x0": None,
            "y0": None,
            "largura": None,
            "altura": None,
            "linhas_y": None,
            "e_pauta": None,
            "papel_branco": None,
            "uniformidade": None,
        }
    else:
        medidas = {
            "x0": int(candidato.x0),
            "y0": int(candidato.y0),
            "largura": int(candidato.roi.shape[1]),
            "altura": int(candidato.roi.shape[0]),
            "linhas_y": [int(candidato.y0) + int(y) for y in candidato.grade.linhas_y],
            "e_pauta": _e_pauta(candidato),
            "papel_branco": round(painel.papel_branco(candidato.roi), 4),
            "uniformidade": round(painel.uniformidade(candidato.roi), 4),
        }
    return {
        "produto": produto,
        "k": k,
        "tela": tid,
        "t": round(t, 3),
        "video": arquivo,
        "folha": folha,
        "tem_painel": candidato is not None,
        **medidas,
        "passo": tela.get("passo"),
        "n_notas": len(da_tela),
        "conf_media": conf_media,
        "erro": erro,
    }


def main() -> None:
    """Gera as folhas de auditoria, ``telas_r2021.json`` e o ``LEIAME.json``."""
    inicio = time.monotonic()
    FOLHAS.mkdir(parents=True, exist_ok=True)
    produtos = sorted(PRODUTOS.glob("*.json"))
    tiles: list[np.ndarray] = []
    telas: list[dict[str, Any]] = []
    sem_exibicao = 0
    for k, caminho in enumerate(produtos, start=1):
        dados = ler_json(caminho)
        slug = ascii_seguro(caminho.stem)[:30]
        arquivo = dados["video"]["arquivo"]
        video = caminho_do_video(arquivo)
        notas = dados.get("notas", [])
        n_telas = 0
        n_sem_painel = 0
        t_prod = time.monotonic()
        for tela in dados.get("telas", []):
            if tela.get("passo") is None:
                continue
            exibicoes = tela.get("exibicoes") or []
            if not exibicoes:
                sem_exibicao += 1
                print(f"  sem exibicao: {slug} tela {tela.get('id')}", flush=True)
                continue
            tid = tela["id"]
            t = (exibicoes[0]["t0"] + exibicoes[0]["t1"]) / 2
            quadro = quadro_em(str(video), t)
            candidato = None
            erro = None
            if quadro is not None:
                try:
                    candidato = painel.escolher_ou_mascara(quadro)
                except Exception as exc:
                    erro = f"{type(exc).__name__}: {exc}"
            if candidato is None:
                n_sem_painel += 1
            folha = f"folha_{len(tiles) // POR_FOLHA + 1:03d}.jpg"
            rotulo = ascii_seguro(f"p{k} t{tid} {slug}")
            tiles.append(montar_tile(quadro, candidato, rotulo))
            telas.append(
                registro_da_tela(
                    slug, k, tela, t, arquivo, folha, candidato, notas, erro
                )
            )
            n_telas += 1
        print(
            f"[{k:02d}/{len(produtos)}] {slug}: telas={n_telas} "
            f"sem_painel={n_sem_painel} ({time.monotonic() - t_prod:.0f} s)",
            flush=True,
        )

    n_folhas = math.ceil(len(tiles) / POR_FOLHA)
    for f in range(n_folhas):
        grupo = tiles[f * POR_FOLHA : (f + 1) * POR_FOLHA]
        destino = FOLHAS / f"folha_{f + 1:03d}.jpg"
        ok = cv2.imwrite(
            str(destino),
            montar_folha(grupo),
            [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPEG],
        )
        if not ok:
            raise OSError(f"falha ao gravar {destino}")
    print(f"folhas gravadas: {n_folhas}", flush=True)

    TELAS_JSON.write_text(
        json.dumps(telas, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    gravar_atomico(
        LEIAME,
        {
            "nome": "recusa",
            "trilha": "tablatura",
            "classe": "manter",
            "motivo": (
                "rodada 0216: recusa segura do painel errado antes do rollout; "
                "folhas de auditoria das telas do produto r2021"
            ),
            "comando": ["python data/saida/tablatura/recusa/folhas_r2021.py"],
            "regeneravel": "sim",
            "rodadas": ["docs/rodadas/0216-recusa-do-painel.md"],
            "citado_por": [],
            "modificado": "2026-10-23",
        },
    )
    sem = sum(1 for t in telas if not t["tem_painel"])
    print(
        f"total de telas={len(telas)} sem_painel={sem} "
        f"sem_exibicao={sem_exibicao} folhas={n_folhas} "
        f"tempo={time.monotonic() - inicio:.0f} s",
        flush=True,
    )


if __name__ == "__main__":
    main()
