"""Dados do piloto 1021 (``tab.maos_braco_m21``): barreira da M11b, alvos e retomada."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from tab import maos_braco_m21
from tab.maos_braco_m21 import (
    _alvos_do_rastreio,
    _amostra_sintetica,
    _iniciar_sintetico,
)
from tab.maos_braco_sintetico import conferir_fora_m11b, videos_proibidos


def test_m11b_tem_videos_e_levanta_erro_para_cada_um() -> None:
    """Todo vídeo da M11b levanta erro, e um vídeo comum passa."""
    proibidos = videos_proibidos()
    assert len(proibidos) > 0
    for arquivo in proibidos:
        with pytest.raises(ValueError, match="M11b"):
            conferir_fora_m11b(arquivo, proibidos)
    conferir_fora_m11b("canal/video_comum.mp4", proibidos)


def test_alvos_ficam_dentro_da_duracao() -> None:
    """Os alvos t ± 3·k s ficam em [0, duração); t = 10 s e duração 25 s dão 7 alvos."""
    quadros = {"q01": {"braco": "sim"}}
    indice = {"q01": {"arquivo": "x.mp4", "canal": "c", "t": 10.0}}
    tarefas = _alvos_do_rastreio(quadros, indice, {"x.mp4": 25.0})
    instantes = sorted(t["t_alvo"] for t in tarefas)
    assert instantes == [1.0, 4.0, 7.0, 13.0, 16.0, 19.0, 22.0]
    assert all(0.0 <= t < 25.0 for t in instantes)


def test_sintetico_e_retomavel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A segunda rodada não refaz as amostras já gravadas."""
    pasta_s = tmp_path / "S"
    pasta_fundos = tmp_path / "fundos"
    pasta_fundos.mkdir()
    rng = np.random.default_rng(0)
    cv2.imwrite(
        str(pasta_fundos / "0000.jpg"),
        rng.integers(0, 255, (540, 960, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(maos_braco_m21, "DIR_S", pasta_s)
    monkeypatch.setattr(maos_braco_m21, "DIR_FUNDOS", pasta_fundos)
    fundos = [{"arquivo": "canal/fundo_teste.mp4", "t": 1.0, "jpg": "0000.jpg"}]
    _iniciar_sintetico(fundos, frozenset())
    assert _amostra_sintetica(0) == "feita"
    assert (pasta_s / "00000.jpg").exists()
    assert (pasta_s / "00000.json").exists()
    assert _amostra_sintetica(0) == "existente"


def test_sintetico_recusa_fundo_da_m11b(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se o fundo sorteado é de um vídeo da M11b, a amostra levanta erro."""
    pasta_fundos = tmp_path / "fundos"
    pasta_fundos.mkdir()
    cv2.imwrite(str(pasta_fundos / "0000.jpg"), np.zeros((540, 960, 3), dtype=np.uint8))
    monkeypatch.setattr(maos_braco_m21, "DIR_S", tmp_path / "S")
    monkeypatch.setattr(maos_braco_m21, "DIR_FUNDOS", pasta_fundos)
    proibido = sorted(videos_proibidos())[0]
    fundos = [{"arquivo": proibido, "t": 1.0, "jpg": "0000.jpg"}]
    _iniciar_sintetico(fundos, videos_proibidos())
    with pytest.raises(ValueError, match="M11b"):
        _amostra_sintetica(0)
