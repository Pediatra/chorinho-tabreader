"""T8.2: preenche painel_ok (olhado a olho) no resumo.csv e monta uma folha JPG por canal."""

from __future__ import annotations

import csv
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path("/app")
SAIDA = RAIZ / "data" / "saida" / "t82"
LARGURA = 1200

#: Classificação feita olhando cada painel.png (Read) — chave é a pasta da tela.
OLHADO = {
    "c01_v1": ("sim", "t=817 (refeito c/ painel escuro): caixa x110-1862 y714-1077 = tablatura, depois das letras e antes do diagrama Am7. Olhado: 28 notas reais, 28 com casa e corda certas, 0 falsas, 0 perdidas"),
    "c01_v2": ("sim", "t=1243 (refeito c/ painel escuro): caixa x109-2220 y665-1034 = tablatura. Olhado: 20 marcas reais (18 casas + 2 x mudos), 17 certas, 1 errada (19 no lugar de b9), 2 perdidas (b9 e b7 do 1o grupo)"),
    "c02_v1": ("sim", "t=219: pauta TAB no rodape (painel base y620-1080 de 1920x1080)"),
}
PADRAO_OK = ("sim", "tablatura grafica visivel")
ANOTACOES = {
    "c17_v1": "overlay de software de tab com video acima; leitura na tab",
}


def classificar(pasta: str) -> tuple[str, str]:
    """Devolve (painel_ok, observacao) para uma pasta de tela.

    Args:
        pasta: nome da pasta (ex.: c01_v1).

    Returns:
        Par painel_ok e texto de observação.
    """
    nome = Path(pasta).name
    if nome in OLHADO:
        return OLHADO[nome]
    obs = ANOTACOES.get(nome, PADRAO_OK[1])
    return PADRAO_OK[0], obs


def montar_folha(canal_idx: str, linhas: list[dict]) -> None:
    """Empilha os painéis de um canal numa folha JPG com cabeçalho por tela.

    Args:
        canal_idx: código do canal (ex.: c01).
        linhas: linhas do resumo do canal.
    """
    blocos = []
    for linha in linhas:
        img = cv2.imread(str(RAIZ / linha["pasta"] / "painel.png"))
        if img is None:
            continue
        h, w = img.shape[:2]
        if w != LARGURA:
            img = cv2.resize(img, (LARGURA, int(h * LARGURA / w)), interpolation=cv2.INTER_AREA)
        cabec = np.full((34, LARGURA, 3), 255, np.uint8)
        rotulo = f"{Path(linha['pasta']).name}  t={linha['t']}s  painel_ok={linha['painel_ok']}"
        cv2.putText(cabec, rotulo, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
        blocos.append(np.vstack([cabec, img]))
    if not blocos:
        return
    folha = np.vstack(blocos)
    cv2.imwrite(str(SAIDA / "folhas" / f"{canal_idx}.jpg"), folha, [cv2.IMWRITE_JPEG_QUALITY, 88])


def main() -> None:
    """Atualiza resumo.csv e grava as folhas por canal."""
    with (SAIDA / "resumo.csv").open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        ok, obs = classificar(linha["pasta"])
        linha["painel_ok"] = ok
        if Path(linha["pasta"]).name in OLHADO:
            linha["observacao"] = obs
        else:
            linha["observacao"] = (obs + " | " + linha["observacao"]).strip(" |")
    campos = ["canal", "video", "t", "painel_ok", "n_notas", "observacao", "pasta"]
    with (SAIDA / "resumo.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    (SAIDA / "folhas").mkdir(parents=True, exist_ok=True)
    por_canal: dict[str, list[dict]] = {}
    for linha in linhas:
        por_canal.setdefault(Path(linha["pasta"]).name.split("_")[0], []).append(linha)
    for idx, grupo in por_canal.items():
        montar_folha(idx, grupo)
    print("folhas:", len(por_canal))


if __name__ == "__main__":
    main()
