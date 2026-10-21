"""Transcritor livre: as notas que o som tem, sem ver a tablatura (rodada 2018).

Roda **só** na imagem ``chorinho-som:dev`` (``Dockerfile.som``: Python 3.10 e Basic Pitch
0.4.0). Por isso importa apenas a biblioteca padrão, numpy e ``basic_pitch``: nada do
resto do pacote ``tab``, que pede o Python e as bibliotecas da imagem base.

Entrada: o FLAC do cache de áudio (``tab.audio_extrair``) e o meta dele, ao lado
(``.json``). Saída: um JSON com as notas ouvidas, no tempo do **vídeo**
(``t = t_amostra0 + t_no_arquivo``, a convenção de ``tab.audio_extrair.instante_de``).
O formato é provisório (proposta ``chorinho/som@1``, decisão 2005).

Uso (container ``chorinho-som:dev``, com o cache montado em ``/cache``)::

    python -m tab.audio_transcrever /cache/audio/<chave>.flac --saida <arquivo>.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import basic_pitch
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict

#: Versão do formato provisório.
ESQUEMA = "chorinho/som@0-provisorio"

#: Tessitura do violão em MIDI (E2 a E6: casa 17 com capo 7 na corda 1). Fora disso a
#: nota vai para ``fora_do_violao`` (regra de domínio fixada no pré-registro da 2018).
MIDI_MINIMO = 40
MIDI_MAXIMO = 88


def separar_por_tessitura(
    notas: list[dict], minimo: int = MIDI_MINIMO, maximo: int = MIDI_MAXIMO
) -> tuple[list[dict], list[dict]]:
    """Separa as notas dentro e fora da tessitura do violão.

    Args:
        notas: notas com ``midi``.
        minimo: menor MIDI aceito.
        maximo: maior MIDI aceito.

    Returns:
        ``(dentro, fora)``, cada uma na ordem de entrada.
    """
    dentro = [n for n in notas if minimo <= n["midi"] <= maximo]
    fora = [n for n in notas if not minimo <= n["midi"] <= maximo]
    return dentro, fora


def notas_no_tempo_do_video(eventos: list, t_amostra0: float) -> list[dict]:
    """Converte as notas do Basic Pitch para o tempo do vídeo, em ordem.

    Args:
        eventos: tuplas ``(inicio_s, fim_s, midi, amplitude, bends)`` do ``predict``.
        t_amostra0: instante do vídeo da primeira amostra do FLAC.

    Returns:
        Notas ``{t_ini, t_fim, midi, amplitude}``, ordenadas por início e altura.
    """
    notas = [
        {
            "t_ini": round(t_amostra0 + float(e[0]), 4),
            "t_fim": round(t_amostra0 + float(e[1]), 4),
            "midi": int(e[2]),
            "amplitude": round(float(e[3]), 4),
        }
        for e in eventos
    ]
    notas.sort(key=lambda n: (n["t_ini"], n["midi"]))
    return notas


def transcrever(flac: Path) -> dict:
    """Transcreve um FLAC do cache com os parâmetros padrão do Basic Pitch.

    Args:
        flac: caminho do FLAC; o meta do cache fica ao lado, com ``.json``.

    Returns:
        O documento de saída, com ``notas`` e ``fora_do_violao``.
    """
    meta = json.loads(flac.with_suffix(".json").read_text(encoding="utf-8"))
    _, _, eventos = predict(str(flac), ICASSP_2022_MODEL_PATH)
    todas = notas_no_tempo_do_video(eventos, float(meta["t_amostra0"]))
    dentro, fora = separar_por_tessitura(todas)
    return {
        "esquema": ESQUEMA,
        "video": meta["caminho"],
        "chave_cache": meta["chave"],
        "transcritor": {
            "nome": "basic-pitch",
            "versao": getattr(basic_pitch, "__version__", "0.4.0"),
            "modelo": os.path.basename(str(ICASSP_2022_MODEL_PATH)),
            "parametros": "padrão de basic_pitch.inference.predict",
        },
        "t_amostra0": float(meta["t_amostra0"]),
        "notas": dentro,
        "fora_do_violao": fora,
    }


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        Código de saída.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("flac", type=Path, help="FLAC do cache de áudio")
    ap.add_argument("--saida", type=Path, required=True, help="JSON de saída")
    args = ap.parse_args()
    doc = transcrever(args.flac)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.saida.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, args.saida)
    print(f"{args.saida}: {len(doc['notas'])} notas, {len(doc['fora_do_violao'])} fora")
    return 0


if __name__ == "__main__":
    sys.exit(main())
