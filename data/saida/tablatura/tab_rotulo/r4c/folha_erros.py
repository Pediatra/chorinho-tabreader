"""R4c, diagnóstico: o que escapa no _atqc com o limiar 0,15 e a regra do slide (0203).

Para cada nota "não" (ouros pela dobra fora, T8.2 pela dobra 0): o previsto nas 3 sementes e
o maior escore das técnicas que tiram o ataque no bin da nota (para ver se o sinal existe
abaixo do limiar). Também as notas "sim" lidas como "não" (alarmes). Grava erros.json e
folhas PNG com o recorte de cada nota (vizinha da esquerda e nota sublinhadas).

Uso (container): env PYTHONPATH=/app python /app/data/saida/tab_rotulo/r4c/folha_erros.py
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch

from tab import ataque_r4 as A
from tab import caminhos, detector_tab, leitor, painel
from tab.ataque_base import parear

SAIDA = caminhos.TAB_ROTULO / "r4c" / "erros"
LIMIAR = 0.15
SUP = [detector_tab.TECNICA_IDX[t] for t in A.TECNICAS_SUPERVISIONADAS]


def escores(modelo, roi, linhas_y, passo):
    """Notas detectadas com o maior escore das técnicas sem ataque, em px do roi."""
    arr, escala, _ = detector_tab.normalizar_sistema(roi, linhas_y, passo)
    dispositivo = next(modelo.parameters()).device
    with torch.no_grad():
        saida = modelo(torch.from_numpy(arr)[None, None].to(dispositivo))
    tec = torch.sigmoid(saida["tecnica"][0]).cpu().numpy()
    notas = A.com_limiar(
        detector_tab._decodificar(modelo, arr, escala, com_escores=True), LIMIAR
    )
    for n in notas:
        j = int(round((n["x"] * escala - detector_tab.DESLOC) / detector_tab.STRIDE))
        j = max(0, min(tec.shape[1] - 1, j))
        n["escore"] = float(tec[n["corda"] - 1, j, SUP].max())
    return notas


def telas_de_teste():
    """(fonte, tela, dobra, video, t, notas do gabarito)."""
    r2 = caminhos.TAB_ROTULO / "r2"
    dobra_de = {s: d for d, ss in A.DOBRAS.items() for s in ss}
    for slug, (sub, fonte) in A.GABARITOS.items():
        ouro = json.loads((r2 / sub / f"{slug}.json").read_text(encoding="utf-8"))
        q = {int(t["id"]): float(t["quadro_ref_s"]) for t in ouro["telas"]}
        gab = A.gabarito_por_tela(r2 / sub / f"ataque_{fonte}.json")
        for tela, notas in sorted(gab.items()):
            yield fonte, tela, dobra_de[slug], caminhos.acervo() / ouro["video"], q[tela], notas
    ferr = caminhos.SAIDA / "t82" / "ferramenta"
    indice = {int(r["id"]): r for r in json.loads((ferr / "indice.json").read_text())}
    gab = A.gabarito_por_tela(r2 / "conferir_novos" / "ataque_t82.json")
    for tela, notas in sorted(gab.items()):
        r = indice[tela]
        yield f"t82:{r['canal']}", tela, 0, caminhos.acervo() / r["video"], float(r["t"]), notas


def recorte(roi, x0, linhas_y, passo, nota, vizinha, rotulo):
    """Recorte da corda em volta da nota, com nota (verde) e vizinha (azul) marcadas."""
    img = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR) if roi.ndim == 2 else roi.copy()
    y = int(linhas_y[nota["corda"] - 1])
    xa = (vizinha["x_centro_quadro"] if vizinha else nota["x_centro_quadro"] - 3 * passo) - x0
    xb = nota["x_centro_quadro"] - x0
    c0 = int(max(0, xa - 1.5 * passo))
    c1 = int(min(img.shape[1], xb + 1.5 * passo))
    r0 = int(max(0, y - 2.5 * passo))
    r1 = int(min(img.shape[0], y + 2.0 * passo))
    for x, cor in ((xb, (0, 170, 0)), (xa if vizinha else None, (200, 80, 0))):
        if x is not None:
            cv2.line(img, (int(x - 0.4 * passo), int(y + 0.6 * passo)),
                     (int(x + 0.4 * passo), int(y + 0.6 * passo)), cor, 2)
    sub = img[r0:r1, c0:c1]
    esc = 120 / max(1, sub.shape[0])
    sub = cv2.resize(sub, (max(1, int(sub.shape[1] * esc)), 120))
    sub = sub[:, :360] if sub.shape[1] > 360 else np.pad(
        sub, ((0, 0), (0, 360 - sub.shape[1]), (0, 0)), constant_values=255)
    faixa = np.full((22, 360, 3), 255, np.uint8)
    cv2.putText(faixa, rotulo[:58], (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    return np.vstack([faixa, sub])


def main() -> int:
    """Mede e grava."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    modelos = {
        (d, s): detector_tab.carregar(A.modelo_da_dobra("atqc", d, s))
        for d in range(5)
        for s in (1, 2, 3)
    }
    linhas = []
    imgs = defaultdict(list)
    for fonte, tela, dobra, video, t, gab in telas_de_teste():
        quadro = leitor.quadro_em(str(video), t)
        c = painel.escolher_ou_mascara(quadro) if quadro is not None else None
        if c is None:
            continue
        por_semente = {}
        for s in (1, 2, 3):
            pred = escores(modelos[(dobra, s)], c.roi, c.grade.linhas_y, c.passo)
            for p in pred:
                p["x_centro_quadro"] = p["x"] + c.x0
            pares = parear(gab, pred, c.passo)
            por_semente[s] = {
                i: {**pred[j], "ataque": A.ataque_com_regra(pred, j, c.passo)}
                for i, j in pares.items()
            }
        for i, n in enumerate(gab):
            prev = []
            for s in (1, 2, 3):
                p = por_semente[s].get(i)
                if p is None:
                    prev.append(("nao_lida", None))
                else:
                    prev.append((p["ataque"], round(p["escore"], 3)))
            n_nao = sum(1 for v, _ in prev if v == "nao")
            if n["ataque"] == "nao" or n_nao >= 2:
                viz = [m for m in gab if m["corda"] == n["corda"]
                       and m["x_centro_quadro"] < n["x_centro_quadro"]]
                vizinha = max(viz, key=lambda m: m["x_centro_quadro"]) if viz else None
                tipo = ("acerto" if n_nao >= 2 else "perdida") if n["ataque"] == "nao" \
                    else "alarme"
                esc = [e for _, e in prev if e is not None]
                linha = {
                    "fonte": fonte, "tela": tela, "nota": n["nota"], "corda": n["corda"],
                    "casa": n["casa"], "motivo": n["motivo"], "ataque": n["ataque"],
                    "previsto": [v for v, _ in prev], "escore": [e for _, e in prev],
                    "tipo": tipo,
                }
                linhas.append(linha)
                if tipo != "acerto":
                    rot = (f"{fonte[:18]} {n['nota']} {n['motivo']} "
                           f"esc {max(esc) if esc else '-'}")
                    imgs[tipo].append(recorte(c.roi, c.x0, c.grade.linhas_y, c.passo,
                                              n, vizinha, rot))
        print(fonte, tela, flush=True)
    (SAIDA / "erros.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1))
    for tipo, lista in imgs.items():
        for k in range(0, len(lista), 30):
            bloco = lista[k:k + 30]
            while len(bloco) % 3:
                bloco.append(np.full_like(bloco[0], 255))
            grade = np.vstack([np.hstack(bloco[r:r + 3]) for r in range(0, len(bloco), 3)])
            cv2.imwrite(str(SAIDA / f"folha_{tipo}_{k // 30 + 1}.png"), grade)
    resumo = Counter((ln["fonte"].split(":")[0], ln["motivo"], ln["tipo"]) for ln in linhas)
    for k, v in sorted(resumo.items()):
        print(k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
