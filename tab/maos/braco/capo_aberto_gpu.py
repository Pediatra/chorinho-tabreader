"""Rodada 1046, parte GPU: o par antigo e as caixas do Grounding DINO em cada quadro.

Só roda na imagem das mãos (``transformers`` e os pesos do Grounding DINO tiny, sem rede).
A parte de CPU (escolha, conta e medida) fica em ``tab.maos.braco.capo_aberto``.

CLI: ``python -m tab.maos.braco.capo_aberto_gpu bruto --rodada N`` grava ``antigo.json`` e
``caixas.json`` em ``data/saida/maos/m46/<N>/``.
"""

from __future__ import annotations

import argparse
import json
import sys

import cv2
import numpy as np
import torch
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

from tab.comum.arquivos import gravar_atomico
from tab.comum.gpu import trava_gpu
from tab.maos.braco.capo_aberto import (
    ARQUIVO_ANTIGO,
    ARQUIVO_CAIXAS,
    MODELO,
    NOTA_BRUTO,
    PAR_ANTIGO,
    REVISAO,
    TEXTOS,
    pasta_da_rodada,
)
from tab.maos.braco.ciclo import RODADAS, aplicar_sinal_nut_v2, prever_quadros


def detectar(
    modelo: object, processador: object, imagem: np.ndarray, texto: str
) -> list:
    """Caixas do Grounding DINO num quadro, com nota ≥ ``NOTA_BRUTO``.

    Args:
        modelo: ``AutoModelForZeroShotObjectDetection`` já no dispositivo.
        processador: ``AutoProcessor`` do mesmo modelo.
        imagem: quadro BGR.
        texto: o texto do detector (frases terminadas em ponto).

    Returns:
        ``[{"caixa": [x0, y0, x1, y1], "nota": float, "rotulo": str}]``.
    """
    rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
    entrada = processador(images=rgb, text=texto, return_tensors="pt").to(modelo.device)
    with torch.no_grad():
        saida = modelo(**entrada)
    altura, largura = imagem.shape[:2]
    resultado = processador.post_process_grounded_object_detection(
        saida,
        entrada.input_ids,
        threshold=NOTA_BRUTO,
        text_threshold=NOTA_BRUTO,
        target_sizes=[(altura, largura)],
    )[0]
    rotulos = resultado.get("text_labels", resultado.get("labels"))
    return [
        {"caixa": [float(v) for v in caixa], "nota": float(nota), "rotulo": str(rotulo)}
        for caixa, nota, rotulo in zip(
            resultado["boxes"].tolist(),
            resultado["scores"].tolist(),
            rotulos,
            strict=True,
        )
    ]


def bruto(numero: str) -> None:
    """Roda o par antigo e o Grounding DINO (3 textos) em cada quadro da rodada.

    Args:
        numero: rodada do ciclo.
    """
    rodada = RODADAS[numero]
    indice = json.loads((rodada.pasta / "indice.json").read_text(encoding="utf-8"))
    saida = pasta_da_rodada(numero)
    previstos = prever_quadros(rodada.pasta, indice, *PAR_ANTIGO)
    aplicar_sinal_nut_v2(previstos, rodada.pasta, indice)
    ordem = [item["id"] for item in indice["quadros"]]
    gravar_atomico(
        saida / ARQUIVO_ANTIGO,
        {"pesos": list(PAR_ANTIGO), "ordem": ordem, "quadros": previstos},
    )
    caixas: dict[str, dict] = {}
    with trava_gpu("maos", "10 min"):
        processador = AutoProcessor.from_pretrained(MODELO, revision=REVISAO)
        modelo = AutoModelForZeroShotObjectDetection.from_pretrained(
            MODELO, revision=REVISAO
        )
        modelo = modelo.to("cuda" if torch.cuda.is_available() else "cpu").eval()
        for item in indice["quadros"]:
            imagem = cv2.imread(str(rodada.pasta / item["png"]))
            caixas[item["id"]] = {
                texto: detectar(modelo, processador, imagem, texto) for texto in TEXTOS
            }
            print(
                item["id"],
                {t: len(c) for t, c in caixas[item["id"]].items()},
                flush=True,
            )
    gravar_atomico(
        saida / ARQUIVO_CAIXAS,
        {"modelo": MODELO, "revisao": REVISAO, **caixas},
    )


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p_bruto = sub.add_parser("bruto", help="par antigo e caixas (GPU)")
    p_bruto.add_argument("--rodada", required=True)
    args = parser.parse_args()
    bruto(args.rodada)
    return 0


if __name__ == "__main__":
    sys.exit(main())
