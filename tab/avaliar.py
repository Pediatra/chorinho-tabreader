"""Aferição padronizada no gabarito real — é o número oficial do projeto.

Roda as 4 amostras rotuladas à mão (96 glifos) e imprime o acerto por canal. O
AGENTS.md manda reportar a **média de 3 sementes**, nunca uma execução só.

Uso:
    python -m tab.avaliar [--modelo CAMINHO]
"""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np

from .caminhos import GABARITO, MODELO_PADRAO, PARTES, acervo
from .inventario import ler_quadro
from .reconhecer import carregar_modelo, reconhecer_linha

#: Recorte de onde a amostra da `sky guitar` foi rotulada.
RECORTE_SKY = PARTES / "clipes" / "-6rawhontyg_000120_000200" / "linha_01_tablatura.png"


def imagem_da_amostra(am: dict) -> np.ndarray:
    """Imagem que originou os rótulos de uma amostra do gabarito.

    A amostra da `sky guitar` foi rotulada de um recorte local; as outras vêm do
    quadro do vídeo no acervo, na faixa (topo/base) registrada no gabarito.

    Args:
        am: uma entrada de ``amostras`` do gabarito.

    Returns:
        Imagem BGR (ou em tons de cinza, no caso do recorte local).
    """
    if not am.get("video") or am["video"].startswith("sky guitar"):
        return cv2.imread(str(RECORTE_SKY), cv2.IMREAD_UNCHANGED)
    frame, _ = ler_quadro(str(acervo() / am["video"]), 0.5)
    return frame[620:1080, :] if am["faixa"] == "base" else frame[0:400, :]


def avaliar_com_modelo(
    modelo, rotulos: list[str], dev: str, usar_recuperada: bool = False
) -> list[tuple[str, int, int]]:
    """Aferição glifo a glifo no gabarito, com o modelo já carregado.

    Args:
        modelo: classificador de glifos.
        rotulos: classes na ordem de saída do modelo.
        dev: dispositivo onde o modelo está.
        usar_recuperada: compara `casa_recuperada` (a casa achada DENTRO de um
            símbolo fundido) em vez de `casa`. **Experimento medido e REPROVADO**:
            a média cai de 0,889 para 0,687 (pior nas 3 sementes; no `paolo`, 25→10),
            porque em token fundido por fragmento de corda o pedaço escolhido não é o
            algarismo. O campo continua gravado como informação, nunca como padrão.

    Returns:
        Uma tupla ``(canal, acertos, total)`` por amostra do gabarito.
    """
    # Obrigatório: em modo `train()` o Dropout(0.15) da rede segue ativo e a
    # aferição despenca. Medido nos MESMOS pesos e na MESMA imagem: 0,865 em
    # `eval()` contra 0,812 em `train()`. Era daí que vinha o número deprimido que
    # o treino reportava sobre o próprio modelo (0,771) enquanto o disco dava 0,865.
    modelo.eval()
    dados = json.loads(GABARITO.read_text(encoding="utf-8"))
    linhas: list[tuple[str, int, int]] = []
    for am in dados["amostras"]:
        img = imagem_da_amostra(am)
        r = reconhecer_linha(img, modelo, rotulos, dev)
        campo = "casa_recuperada" if usar_recuperada else "casa"
        previsto = [n.get(campo) or n["casa"] for n in r["notas"]]
        indices = sorted(int(k) for k in am["rotulos"])
        # Token que a segmentação não produziu conta como erro, não como exceção.
        acertos = sum(
            1
            for i in indices
            if i < len(previsto) and previsto[i] == am["rotulos"][str(i)]
        )
        linhas.append((am["canal"], acertos, len(indices)))
    return linhas


def avaliar(
    caminho_modelo: str, usar_recuperada: bool = False
) -> list[tuple[str, int, int]]:
    """Aferição glifo a glifo, carregando o modelo do disco.

    Args:
        caminho_modelo: pesos do classificador de glifos.

    Returns:
        Uma tupla ``(canal, acertos, total)`` por amostra do gabarito.
    """
    modelo, rotulos, dev = carregar_modelo(caminho_modelo)
    return avaliar_com_modelo(modelo, rotulos, dev, usar_recuperada)


def main() -> int:
    """Imprime o acerto por canal e o total."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    ap.add_argument(
        "--recuperada",
        action="store_true",
        help="usa a casa recuperada de dentro do simbolo (experimento)",
    )
    args = ap.parse_args()

    linhas = avaliar(args.modelo, usar_recuperada=args.recuperada)
    acertos = sum(o for _, o, _ in linhas)
    total = sum(t for _, _, t in linhas)
    resumo = " ".join(f"{c.split()[0][:6]}={o}/{t}" for c, o, t in linhas)
    print(f"RESULTADO {resumo} | TOTAL={acertos}/{total}={acertos / total:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
