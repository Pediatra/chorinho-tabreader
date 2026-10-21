"""Trava da Fase 1 / T1.2: `cv2.VideoCapture(` só existe em `tab/leitor.py`.

O AV1 abre no `cv2.VideoCapture` e não decodifica (falha calada). Quem lê vídeo tem de passar
pelo `tab.leitor`, que decide o caminho que de fato funciona.
"""

from tab.caminhos import RAIZ

#: Piso de arquivos varridos: com os módulos em subpastas (decisão 9001), uma varredura
#: que não descesse nelas conferiria 0 arquivos e passaria calada.
MINIMO_DE_ARQUIVOS = 140


def test_videocapture_so_no_leitor() -> None:
    """Nenhum módulo de `tab/` além de `leitor.py` chama `cv2.VideoCapture(`."""
    infratores = []
    arquivos = sorted((RAIZ / "tab").rglob("*.py"))
    assert len(arquivos) >= MINIMO_DE_ARQUIVOS, len(arquivos)
    for arq in arquivos:
        if arq.name == "leitor.py":
            continue
        if "VideoCapture(" in arq.read_text(encoding="utf-8"):
            infratores.append(arq.name)
    assert not infratores, (
        "cv2.VideoCapture( fora de tab/leitor.py em: "
        + ", ".join(infratores)
        + " (leia o vídeo pelo tab.leitor)"
    )
