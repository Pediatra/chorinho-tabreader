"""Transcritor livre de violão do Riley (rodada 2019): as notas do som, sem ver a tela.

Roda **só** na imagem ``chorinho-som:dev`` (``Dockerfile.som``: Python 3.10, torch CPU e o
fork ``piano_transcription_inference`` de xavriley, MIT). Importa apenas a biblioteca
padrão, numpy, soundfile, librosa, torch e o fork: nada do resto do pacote ``tab``.

O modelo é o CRNN de alta resolução (Kong et al.) adaptado ao violão por Riley et al.
(ICASSP 2024 e ISMIR 2024). Os pesos ficam em ``artefatos/riley_guitar/`` (procedência em
``artefatos/riley_guitar.md``) e são lidos com ``torch.load(weights_only=True)``: o arquivo
é um pickle, e esse modo não executa código dele. O fork carrega com ``weights_only=False``;
por isso a classe dele é montada aqui sem o ``__init__``.

Entrada: o FLAC do cache de áudio (22.050 Hz, mono), reamostrado para 16 kHz com
``soxr_hq`` (o mesmo de ``librosa.load``, que o pacote do autor usa). Saída: o mesmo formato
provisório de ``tab.audio_transcrever``, no tempo do vídeo. ``amplitude`` é a velocidade
MIDI / 127, para a comparação aceitar os dois transcritores.

Uso (container ``chorinho-som:dev``)::

    python -m tab.audio_transcrever_riley /cache/audio/<chave>.flac \
        --pesos artefatos/riley_guitar/guitar-fl.pth --saida <arquivo>.json
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile
import torch
from piano_transcription_inference import PianoTranscription, sample_rate
from piano_transcription_inference.models import (
    Regress_onset_offset_frame_velocity_CRNN,
)

#: Versão do formato provisório (a mesma de ``tab.audio_transcrever``).
ESQUEMA = "chorinho/som@0-provisorio"

#: Tessitura do violão em MIDI (a mesma regra da rodada 2018).
MIDI_MINIMO = 40
MIDI_MAXIMO = 88

#: Limiares padrão do pacote do autor (``hf_midi_transcription``), sem ajuste.
LIMIARES = {"onset": 0.3, "offset": 0.3, "frame": 0.1, "pedal_offset": 0.2}

#: Tipos que o pickle dos pesos pode montar além dos tensores: arrays numpy (contadores
#: do treino guardados ao lado do ``model``). Conferido com ``pickletools`` antes de
#: carregar: os dois ``.pth`` só pedem estes globais, nenhum executa código.
GLOBAIS_PERMITIDOS = [
    np.core.multiarray._reconstruct,
    np.ndarray,
    np.dtype,
    np.dtypes.Int64DType,
    np.dtypes.Float64DType,
    np.dtypes.Float32DType,
    codecs.encode,
]

#: Segmento de 10 s, como no pacote do autor.
SEGMENTO_S = 10


def separar_por_tessitura(notas: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separa as notas dentro e fora da tessitura do violão.

    Args:
        notas: notas com ``midi``.

    Returns:
        ``(dentro, fora)``.
    """
    dentro = [n for n in notas if MIDI_MINIMO <= n["midi"] <= MIDI_MAXIMO]
    fora = [n for n in notas if not MIDI_MINIMO <= n["midi"] <= MIDI_MAXIMO]
    return dentro, fora


def notas_no_tempo_do_video(eventos: list[dict], t_amostra0: float) -> list[dict]:
    """Converte os eventos do modelo para o tempo do vídeo, em ordem.

    Args:
        eventos: ``{onset_time, offset_time, midi_note, velocity}`` do pós-processamento.
        t_amostra0: instante do vídeo da primeira amostra do FLAC.

    Returns:
        Notas ``{t_ini, t_fim, midi, velocidade, amplitude}``.
    """
    notas = [
        {
            "t_ini": round(t_amostra0 + float(e["onset_time"]), 4),
            "t_fim": round(t_amostra0 + float(e["offset_time"]), 4),
            "midi": int(e["midi_note"]),
            "velocidade": int(e["velocity"]),
            "amplitude": round(int(e["velocity"]) / 127, 4),
        }
        for e in eventos
    ]
    notas.sort(key=lambda n: (n["t_ini"], n["midi"]))
    return notas


def carregar_modelo(pesos: Path) -> tuple[torch.nn.Module, dict]:
    """Monta o CRNN e carrega os pesos sem executar código do arquivo.

    Args:
        pesos: ``.pth`` do autor.

    Returns:
        ``(modelo em eval, relatorio_do_carregamento)``.

    Raises:
        RuntimeError: se faltar alguma chave do modelo no arquivo.
    """
    modelo = Regress_onset_offset_frame_velocity_CRNN(
        frames_per_second=100, classes_num=88
    )
    with torch.serialization.safe_globals(GLOBAIS_PERMITIDOS):
        ponto = torch.load(str(pesos), map_location="cpu", weights_only=True)
    estado = ponto.get("model", ponto)
    faltando, sobrando = modelo.load_state_dict(estado, strict=False)
    if faltando:
        raise RuntimeError(f"pesos sem as chaves {faltando[:5]}...")
    modelo.eval()
    return modelo, {"chaves_sobrando": list(sobrando)}


def transcritor(modelo: torch.nn.Module) -> PianoTranscription:
    """A classe do fork, montada sem o ``__init__`` (que carrega o pickle inseguro).

    Args:
        modelo: o CRNN já carregado.

    Returns:
        Um ``PianoTranscription`` pronto para ``transcribe``.
    """
    pt = PianoTranscription.__new__(PianoTranscription)
    pt.segment_samples = SEGMENTO_S * sample_rate
    pt.frames_per_second = 100
    pt.classes_num = 88
    pt.onset_threshold = LIMIARES["onset"]
    pt.offset_threshod = LIMIARES["offset"]  # (sic) o nome do atributo no fork
    pt.frame_threshold = LIMIARES["frame"]
    pt.pedal_offset_threshold = LIMIARES["pedal_offset"]
    pt.batch_size = 8
    pt.model = modelo
    return pt


def transcrever(flac: Path, pesos: Path) -> dict:
    """Transcreve um FLAC do cache com os pesos dados.

    Args:
        flac: FLAC do cache; o meta fica ao lado, com ``.json``.
        pesos: ``.pth`` do autor.

    Returns:
        O documento de saída, com ``notas`` e ``fora_do_violao``.
    """
    torch.manual_seed(0)
    meta = json.loads(flac.with_suffix(".json").read_text(encoding="utf-8"))
    audio, taxa = soundfile.read(str(flac), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = librosa.resample(
        audio, orig_sr=taxa, target_sr=sample_rate, res_type="soxr_hq"
    )
    modelo, relatorio = carregar_modelo(pesos)
    saida = transcritor(modelo).transcribe(np.asarray(audio, dtype=np.float32), None)
    todas = notas_no_tempo_do_video(saida["est_note_events"], float(meta["t_amostra0"]))
    dentro, fora = separar_por_tessitura(todas)
    return {
        "esquema": ESQUEMA,
        "video": meta["caminho"],
        "chave_cache": meta["chave"],
        "transcritor": {
            "nome": "riley-guitar (CRNN de alta resolução)",
            "pesos": pesos.name,
            "limiares": LIMIARES,
            "carregamento": relatorio,
            "torch": torch.__version__,
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
    ap.add_argument("--pesos", type=Path, required=True, help=".pth do autor")
    ap.add_argument("--saida", type=Path, required=True, help="JSON de saída")
    args = ap.parse_args()
    doc = transcrever(args.flac, args.pesos)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.saida.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, args.saida)
    print(f"{args.saida}: {len(doc['notas'])} notas, {len(doc['fora_do_violao'])} fora")
    return 0


if __name__ == "__main__":
    sys.exit(main())
