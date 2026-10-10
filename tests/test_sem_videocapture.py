"""Trava da Fase 1 / T1.2: `cv2.VideoCapture(` só existe em `tab/leitor.py`.

O AV1 abre no `cv2.VideoCapture` e não decodifica (falha calada). Quem lê vídeo tem de passar
pelo `tab.leitor`, que decide o caminho que de fato funciona.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_videocapture_so_no_leitor() -> None:
    """Nenhum módulo de `tab/` além de `leitor.py` chama `cv2.VideoCapture(`."""
    infratores = []
    for arq in sorted((RAIZ / "tab").glob("*.py")):
        if arq.name == "leitor.py":
            continue
        if "VideoCapture(" in arq.read_text(encoding="utf-8"):
            infratores.append(arq.name)
    assert not infratores, (
        "cv2.VideoCapture( fora de tab/leitor.py em: "
        + ", ".join(infratores)
        + " (leia o vídeo pelo tab.leitor)"
    )
