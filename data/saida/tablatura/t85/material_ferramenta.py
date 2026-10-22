"""Monta, para a ferramenta do ouro (``tab.ouro_video servir``), o material das telas t85.

Cada tela t85 vira uma "tela" da ferramenta, com as notas lidas pela rede pré-carregadas.
A caixa de cada nota é estimada pelo centro e pelo passo (a rede não devolve caixa).
Sem instantes: aqui só se confere casa. O resultado vai para ``data/saida/tablatura/t85/ferramenta/``
e o ouro gravado pela ferramenta é ``ferramenta/conferencia_t85.json`` (não é gabarito).

Uso (container): python data/saida/tablatura/t85/material_ferramenta.py
"""

import csv
import json
import sys
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ))
from tab.ouro_video import (  # noqa: E402
    ESCALA_TELA,
    folga_acima_da_corda1,
    painel_com_caixas,
)

T85 = RAIZ / "data" / "saida" / "tablatura" / "t85"
SAIDA = T85 / "ferramenta"
#: Telas que não entram, olhadas na folha (regra 4: o braço engana como tablatura).
EXCLUIR: dict[str, str] = {}


def caixa(nota: dict, linhas_y: list[float], passo: float) -> list[float]:
    """Caixa estimada ``[x0, y0, x1, y1]`` de uma nota, no quadro.

    Args:
        nota: nota com ``corda`` e ``x_centro_quadro``.
        linhas_y: y de cada corda, no quadro.
        passo: distância entre cordas, em px.

    Returns:
        A caixa, meia largura 0,3 passo e meia altura 0,42 passo.
    """
    x, y = nota["x_centro_quadro"], linhas_y[nota["corda"] - 1]
    return [
        round(x - 0.3 * passo, 1),
        round(y - 0.42 * passo, 1),
        round(x + 0.3 * passo, 1),
        round(y + 0.42 * passo, 1),
    ]


def main() -> None:
    """Grava ``telas/NNN.png``, ``pre.json`` e ``indice.json`` em ``SAIDA``."""
    (SAIDA / "telas").mkdir(parents=True, exist_ok=True)
    with (T85 / "resumo.csv").open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    pre_telas, estado_telas, indice = [], [], []
    k = 0
    for linha in linhas:
        pasta = RAIZ / linha["pasta"]
        if not (pasta / "tela.json").exists() or pasta.name in EXCLUIR:
            continue  # quadro não extraído, ou fora por EXCLUIR
        k += 1  # ids seguidos, de 1
        tela = json.loads((pasta / "tela.json").read_text(encoding="utf-8"))
        quadro = cv2.imread(str(pasta / "quadro.png"))
        p = tela["painel"]
        if p is None:
            continue
        passo, ly = tela["passo"], tela["linhas_y"]
        notas = [
            {
                "corda": n["corda"],
                "casa": str(n["casa"]),
                "x_quadro": round(n["x_centro_quadro"] - 0.3 * passo, 1),
                "x_centro_quadro": n["x_centro_quadro"],
                "caixa": caixa(n, ly, passo),
                "confianca": n["confianca"],
            }
            for n in tela["notas"]
        ]
        rect = painel_com_caixas(
            (p["x0"], p["y0"], p["x1"], p["y1"]),
            [n["caixa"] for n in notas],
            quadro.shape,
        )
        rect = folga_acima_da_corda1(rect, passo)
        x0, y0, x1, y1 = rect
        ampliada = cv2.resize(
            quadro[y0:y1, x0:x1],
            None,
            fx=ESCALA_TELA,
            fy=ESCALA_TELA,
            interpolation=cv2.INTER_CUBIC,
        )
        arquivo = f"telas/{k:03d}.png"
        cv2.imwrite(str(SAIDA / arquivo), ampliada)
        pre_telas.append(
            {
                "id": k,
                "arquivo": arquivo,
                "quadro_ref_s": tela["t"],
                "t_ini": tela["t"],
                "t_fim": tela["t"],
                "exibicoes": [[tela["t"], tela["t"]]],
                "modo": "paginado",
                "painel": list(rect),
                "escala": ESCALA_TELA,
                "passo": passo,
                "linhas_y": ly,
                "notas": notas,
                "nao_nota": [],
            }
        )
        estado_telas.append(
            {
                "id": k,
                "conferida": False,
                "junta_em": None,
                "origem": "rede — a conferir",
                "v1_telas": [],
                "notas": [
                    {
                        "id": f"m{i}",
                        "corda": n["corda"],
                        "casa": n["casa"],
                        "x_quadro": n["x_quadro"],
                        "x_centro_quadro": n["x_centro_quadro"],
                        "origem": "modelo",
                        "removida": False,
                        "caixa": n["caixa"],
                    }
                    for i, n in enumerate(notas)
                ],
            }
        )
        indice.append(
            {
                "id": k,
                "pasta": linha["pasta"],
                "canal": linha["canal"],
                "video": tela["video"],
                "t": tela["t"],
            }
        )
    pre = {
        "video": f"t85: {len(pre_telas)} telas de canais fora do ouro (ver indice.json)",
        "modelo": "artefatos/detector_tab_final_s1 (leitor rede)",
        "preparado_em": "",
        "duracao_s": 0.0,
        "codec": "",
        "segmentacao": "t85",
        "como_foi_rotulado": (
            "T8.5: uma tela por vídeo, 2 vídeos por canal fora do ouro (data/saida/t85). "
            "Notas pré-lidas pela rede; o dono confere a casa. Sem instantes."
        ),
        "telas": pre_telas,
        "instantes": [],
        "estado_inicial": {
            "proximo": 1,
            "tela_atual": 1,
            "inst_atual": 0,
            "telas": estado_telas,
            "instantes": [],
        },
        "fusao": {"sem_v1": True, "n_instantes": 0},
    }
    (SAIDA / "pre.json").write_text(
        json.dumps(pre, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (SAIDA / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(len(pre_telas), "telas;", sum(len(t["notas"]) for t in pre_telas), "notas")


if __name__ == "__main__":
    main()
