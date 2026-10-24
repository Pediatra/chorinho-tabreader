"""Sinais numéricos do painel escolhido pelo produto r2021 (rodada de recusa).

Para cada tela de ``telas_r2021.json`` com ``tem_painel``, relê o quadro no instante
``t``, roda ``painel.escolher_ou_mascara`` e mede, por tela, sinais numéricos que possam
separar os painéis errados (20 pares conferidos pelo agente) dos certos (582). Cada
medida roda em seu próprio ``try``: se uma falhar, o campo vai como ``None``.

O resultado vai para ``sinais_r2021.json``, uma entrada por tela, com ``errada``.
A análise (limiares e combinações) fica em ``analise_r2021.py``.

Uso:
    python data/saida/tablatura/recusa/sinais_r2021.py
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tab.comum.caminhos import acervo
from tab.comum.leitor import quadro_em
from tab.tablatura.leitura import painel
from tab.tablatura.leitura.tabseg import _uniao_mascaras

RAIZ = Path(__file__).resolve().parents[4]
SAIDA = RAIZ / "data/saida/tablatura/recusa"
TELAS_JSON = SAIDA / "telas_r2021.json"
SINAIS_JSON = SAIDA / "sinais_r2021.json"

#: Pares (k, tela) cujo painel caiu no lugar errado, conferidos pelo agente.
ERRADAS: frozenset[tuple[int, int]] = frozenset(
    {
        (3, 2),
        (5, 11),
        (5, 12),
        (5, 13),
        (5, 15),
        (5, 19),
        (5, 20),
        (5, 21),
        (5, 22),
        (9, 1),
        (9, 2),
        (9, 11),
        (9, 12),
        (9, 13),
        (13, 19),
        (14, 17),
        (24, 9),
        (26, 9),
        (26, 20),
        (29, 44),
    }
)


def _caminho_video(video: str) -> Path:
    """Caminho do vídeo no acervo, tolerando NFC e NFD no nome.

    Args:
        video: caminho relativo ao acervo, como está em ``telas_r2021.json``.

    Returns:
        O primeiro caminho que existe; se nenhum existir, o caminho cru.
    """
    raiz = acervo()
    cru = raiz / video
    if cru.exists():
        return cru
    for forma in ("NFC", "NFD"):
        alternativo = raiz / unicodedata.normalize(forma, video)
        if alternativo.exists():
            return alternativo
    return cru


def _tentar(funcao: Any, *args: Any) -> Any:
    """Roda uma medida e devolve None se ela levantar exceção.

    Args:
        funcao: a medida a rodar.
        *args: argumentos posicionais da medida.

    Returns:
        O valor da medida, ou None.
    """
    try:
        return funcao(*args)
    except Exception:
        return None


def _medidas_do_candidato(c: painel.Candidato, tela: dict[str, Any]) -> dict[str, Any]:
    """Mede os sinais do painel escolhido (o recorte e a grade dele).

    Args:
        c: o candidato escolhido pelo produto.
        tela: a linha de ``telas_r2021.json`` da mesma tela.

    Returns:
        Um dicionário com os sinais medidos sobre o candidato.
    """
    roi = c.roi
    cordas = [int(y) for y in c.grade.linhas_y]
    passo = c.passo
    tinta = _uniao_mascaras(roi).astype(np.uint8)
    medidas: dict[str, Any] = {}

    medidas["cordas_continuas"] = _tentar(painel.cordas_continuas, roi, passo)
    deriva = _tentar(painel.deriva_das_cordas, tinta, list(cordas), passo)
    medidas["deriva_px"] = deriva
    medidas["deriva_passos"] = None if deriva is None else deriva / passo
    medidas["cordas_convergem"] = _tentar(painel._cordas_convergem, c)
    forcas = _tentar(painel.forcas_das_linhas, roi, cordas)
    medidas["forca_min"] = None if not forcas else float(min(forcas))
    medidas["forca_media"] = None if not forcas else float(np.mean(forcas))
    medidas["forca_desvio"] = None if not forcas else float(np.std(forcas))
    medidas["espacamento_regular"] = _tentar(painel.espacamento_regular, cordas)
    n_notas = tela.get("n_notas")
    largura = tela.get("largura")
    if n_notas is not None and largura and passo > 0:
        medidas["notas_por_largura"] = n_notas / (largura / passo)
    else:
        medidas["notas_por_largura"] = None
    medidas["e_tablatura"] = _tentar(painel.e_tablatura, c)
    return medidas


def _medidas_do_roi(roi: np.ndarray) -> dict[str, Any]:
    """Mede cor e borda do recorte (BGR).

    Args:
        roi: recorte BGR do painel.

    Returns:
        Saturação média e desvio do cinza, e fração de pixels de borda.
    """
    medidas: dict[str, Any] = {}
    hsv = _tentar(cv2.cvtColor, roi, cv2.COLOR_BGR2HSV)
    medidas["saturacao_media"] = None if hsv is None else float(hsv[:, :, 1].mean())
    cinza = _tentar(cv2.cvtColor, roi, cv2.COLOR_BGR2GRAY)
    medidas["cinza_desvio"] = None if cinza is None else float(cinza.std())
    bordas = None if cinza is None else _tentar(cv2.Canny, cinza, 50, 150)
    medidas["fracao_borda"] = (
        None if bordas is None else float(np.count_nonzero(bordas) / bordas.size)
    )
    return medidas


def _medir_tela(tela: dict[str, Any]) -> dict[str, Any]:
    """Relê o quadro da tela e mede todos os sinais do painel escolhido.

    Args:
        tela: uma linha de ``telas_r2021.json`` com ``tem_painel`` verdadeiro.

    Returns:
        A linha de sinais da tela, com ``errada`` e os campos do JSON de origem.
    """
    chave = (int(tela["k"]), int(tela["tela"]))
    linha: dict[str, Any] = {
        "produto": tela["produto"],
        "k": chave[0],
        "tela": chave[1],
        "t": tela["t"],
        "errada": chave in ERRADAS,
    }
    for campo in (
        "papel_branco",
        "uniformidade",
        "passo",
        "n_notas",
        "conf_media",
        "largura",
        "altura",
        "x0",
        "y0",
        "e_pauta",
    ):
        linha[campo] = tela.get(campo)

    quadro = _tentar(quadro_em, str(_caminho_video(tela["video"])), float(tela["t"]))
    linha["erro"] = None
    if quadro is None:
        linha["erro"] = "sem quadro"
        return linha
    try:
        c = painel.escolher_ou_mascara(quadro)
    except Exception as exc:
        linha["erro"] = f"{type(exc).__name__}: {exc}"
        return linha
    if c is None:
        linha["erro"] = "escolher_ou_mascara devolveu None"
        return linha

    linha.update(_medidas_do_candidato(c, tela))
    linha.update(_medidas_do_roi(c.roi))
    return linha


def main() -> None:
    """Mede os sinais de cada tela com painel e grava ``sinais_r2021.json``."""
    telas = json.loads(TELAS_JSON.read_text(encoding="utf-8"))
    com_painel = [t for t in telas if t.get("tem_painel")]
    print(f"telas com painel: {len(com_painel)}", flush=True)

    linhas: list[dict[str, Any]] = []
    for i, tela in enumerate(com_painel, start=1):
        linhas.append(_medir_tela(tela))
        if i % 25 == 0 or i == len(com_painel):
            print(f"  {i}/{len(com_painel)}", flush=True)

    encontradas = {(r["k"], r["tela"]) for r in linhas if r["errada"]}
    faltam = sorted(ERRADAS - encontradas)
    print(f"erradas encontradas: {len(encontradas)}/{len(ERRADAS)}", flush=True)
    if faltam:
        print(f"pares errados que NAO estao em com_painel: {faltam}", flush=True)
    sem_medida = sum(1 for r in linhas if r["erro"])
    print(f"telas com erro de execucao: {sem_medida}", flush=True)

    SINAIS_JSON.write_text(
        json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"gravado: {SINAIS_JSON}", flush=True)


if __name__ == "__main__":
    main()
