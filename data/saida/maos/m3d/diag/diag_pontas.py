"""Diagnóstico: onde as pontas dos dedos estão em relação ao braço do dono (só observador).

Não ajusta nada ao gabarito para a calibração da música: o gabarito só gera H_dono,
que serve de régua para medir as pontas. Saídas em data/saida/maos/m3d/diag/.
"""

import json
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import GABARITO_BRACO, MAOS_M3, MAOS_M3B, MVP
from tab.maos_braco import PONTA_DOS_DEDOS
from tab.maos_calibrar_por_notas import (
    aplicar_homografia,
    dlt_homografia,
    largura_casa,
    s_traste,
    u_casa,
    v_corda,
)

RAIZ_M3C = MAOS_M3.parent / "m3c"
Q16_CENA = MAOS_M3.parent / "m3d" / "q16_cena.json"
Q16_PONTAS = MAOS_M3.parent / "m3d" / "pontas_q16.json"
Q16_H = MAOS_M3.parent / "m3d" / "q16" / "medicao.json"
MVP_PONTAS = RAIZ_M3C / "pontas_mvp.json"
MVP_CALIB = RAIZ_M3C / "calibracao_v2.json"
DIAG = MAOS_M3.parent / "m3d" / "diag"
ACEITE = 0.6
CORES = {
    1: (0, 0, 255),
    2: (0, 165, 255),
    3: (0, 255, 255),
    4: (255, 255, 0),
    5: (255, 0, 0),
    6: (255, 0, 255),
}


def reta_y(reta, x):
    (x1, y1), (x2, y2) = reta
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)


def h_dono(reg):
    """Homografia do dono a partir do gabarito do quadro, com resíduos."""
    c1, c6 = reg["corda1"], reg["corda6"]

    def v_de(x, y):
        return (y - reta_y(c1, x)) / (reta_y(c6, x) - reta_y(c1, x))

    orig, dest, cliques = [], [], []
    nx, ny = reg["nut"]
    orig.append([0.0, v_de(nx, ny)])
    dest.append([nx, ny])
    for n, (x, y) in enumerate(reg["trastes"], start=1):
        s = s_traste(n)
        vc = v_de(x, y)
        orig.append([s, vc])
        dest.append([x, y])
        cliques.append(len(orig) - 1)
        orig.append([s, 0.0])
        dest.append([x, reta_y(c1, x)])
        orig.append([s, 1.0])
        dest.append([x, reta_y(c6, x)])
    H = dlt_homografia(np.array(orig), np.array(dest))
    res = np.linalg.norm(aplicar_homografia(H, np.array(orig)) - np.array(dest), axis=1)
    cl = np.array(cliques)
    return H, {
        "reproj_cliques_max_px": float(res[cl].max()),
        "reproj_cliques_mediana_px": float(np.median(res[cl])),
        "reproj_todos_max_px": float(res.max()),
        "n_pontos": len(orig),
        "n_trastes": len(reg["trastes"]),
    }


def pontas_esq(maos):
    """Lista (mao, dedo, (x, y)) das pontas 1 a 4 das mãos esquerdas."""
    saida = []
    for i, mao in enumerate(maos):
        if mao["lado"] != "esquerda":
            continue
        for dedo, xy in PONTA_DOS_DEDOS_XY(mao).items():
            saida.append((i, dedo, xy))
    return saida


def PONTA_DOS_DEDOS_XY(mao):
    pts = mao["pts"]
    return {d: (float(pts[i][0]), float(pts[i][1])) for d, i in PONTA_DOS_DEDOS.items()}


def notas_de(nome):
    if nome == "q16":
        notas = json.loads(Q16_CENA.read_text())["notas"]
        pontas = json.loads(Q16_PONTAS.read_text())["instantes"]
    else:
        notas = json.loads(MVP.read_text())["notas"]
        pontas = json.loads(MVP_PONTAS.read_text())["instantes"]
    mapa = {round(float(r["t_ini"]), 3): r["maos"] for r in pontas}
    return notas, mapa


def analisar(nome, H_d, H_m):
    notas, mapa = notas_de(nome)
    Hi_d = np.linalg.inv(H_d)
    reg = {
        "total_notas": 0,
        "casa_0": 0,
        "sem_ponta_no_instante": 0,
        "sem_mao_esquerda": 0,
        "instantes_distintos": set(),
        "instantes_aceitos": set(),
    }
    linhas = []  # por nota aceita (dono)
    linhas_m = []  # por nota aceita (H_musica)
    dedo_iguais = 0
    dedo_comparados = 0
    for nota in notas:
        reg["total_notas"] += 1
        if nota["casa"] <= 0:
            reg["casa_0"] += 1
            continue
        if nota.get("t_ini") is None:
            reg["sem_t_ini"] = reg.get("sem_t_ini", 0) + 1
            continue
        t = round(float(nota["t_ini"]), 3)
        reg["instantes_distintos"].add(t)
        if t not in mapa:
            reg["sem_ponta_no_instante"] += 1
            continue
        cands = pontas_esq(mapa[t])
        if not cands:
            reg["sem_mao_esquerda"] += 1
            continue
        corda, casa = nota["corda"], nota["casa"]
        vc = v_corda(corda)
        largura = float(largura_casa(H_d, np.array([casa]), np.array([vc]))[0])
        # Dono: ponta mais perto da posição esperada (u a 0,5 da casa).
        esp_d = aplicar_homografia(H_d, np.array([[u_casa(casa, 0.5), vc]]))[0]
        xy = np.array([c[2] for c in cands])
        dist = np.linalg.norm(xy - esp_d, axis=1)
        j = int(np.argmin(dist))
        ok_d = dist[j] < ACEITE * largura
        # H da música: ponta mais perto de H_m(u a 0,7 da casa).
        esp_m = aplicar_homografia(H_m, np.array([[u_casa(casa, 0.7), vc]]))[0]
        dist_m = np.linalg.norm(xy - esp_m, axis=1)
        jm = int(np.argmin(dist_m))
        if ok_d:
            reg["instantes_aceitos"].add(t)
        if ok_d:
            p = xy[j]
            u, v = aplicar_homografia(Hi_d, np.array([p]))[0]
            ua, ub = s_traste(casa - 1), s_traste(casa)
            linhas.append(
                {
                    "t": t,
                    "corda": corda,
                    "casa": casa,
                    "dedo": cands[j][1],
                    "frac": float((u - ua) / (ub - ua)),
                    "dv": float((v - vc) * 5),
                    "dist_px": float(dist[j]),
                    "largura_px": largura,
                }
            )
        dedo_comparados += 1
        dedo_iguais += int(cands[j][1] == cands[jm][1] and cands[j][0] == cands[jm][0])
        if float(dist_m[jm]) < ACEITE * largura:
            p = xy[jm]
            u, v = aplicar_homografia(Hi_d, np.array([p]))[0]
            ua, ub = s_traste(casa - 1), s_traste(casa)
            linhas_m.append(
                {
                    "corda": corda,
                    "casa": casa,
                    "frac": float((u - ua) / (ub - ua)),
                    "dv": float((v - vc) * 5),
                }
            )
    return reg, linhas, linhas_m, dedo_iguais, dedo_comparados


def quartis(xs):
    if not xs:
        return None
    a = np.array(xs)
    return [round(float(np.percentile(a, q)), 3) for q in (25, 50, 75)] + [len(a)]


def resumo(linhas):
    frac = [r["frac"] for r in linhas]
    faixas = {"1-3": (1, 3), "4-6": (4, 6), "7-9": (7, 9), "10+": (10, 99)}
    por_faixa = {
        k: quartis([r["frac"] for r in linhas if lo <= r["casa"] <= hi])
        for k, (lo, hi) in faixas.items()
    }
    por_corda = {
        c: quartis([r["dv"] for r in linhas if r["corda"] == c]) for c in range(1, 7)
    }
    return {
        "frac_q1_med_q3_n": quartis(frac),
        "frac_por_faixa": por_faixa,
        "dv_por_corda": por_corda,
        "dv_geral": quartis([r["dv"] for r in linhas]),
    }


def desenhar(nome, H_d, reg_ids, linhas, png_in, png_out):
    img = cv2.imread(str(png_in))
    n_trastes = 15
    for c in range(1, 7):
        pts = [aplicar_homografia(H_d, np.array([[u, (c - 1) / 5]]))[0]
               for u in np.linspace(0, s_traste(n_trastes), 60)]
        cv2.polylines(img, [np.round(np.array(pts)).astype(np.int32)], False, (0, 200, 0), 2)
    for n in range(0, n_trastes + 1):
        pts = [aplicar_homografia(H_d, np.array([[s_traste(n), v]]))[0]
               for v in np.linspace(0, 1, 30)]
        cv2.polylines(img, [np.round(np.array(pts)).astype(np.int32)], False, (0, 200, 0), 1)
    for r in linhas:
        xy = r["xy"]
        cv2.circle(img, (int(round(xy[0])), int(round(xy[1]))), 7, CORES[r["corda"]], -1)
        cv2.circle(img, (int(round(xy[0])), int(round(xy[1]))), 7, (0, 0, 0), 1)
    y0 = 40
    cv2.putText(img, f"{nome}: pontas aceitas por corda (verde = grade do dono)", (20, y0),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 3)
    for c in range(1, 7):
        y = y0 + 40 * c
        cv2.circle(img, (30, y - 8), 9, CORES[c], -1)
        cv2.putText(img, f"corda {c}", (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2)
    cv2.imwrite(str(png_out), img)


def main():
    DIAG.mkdir(parents=True, exist_ok=True)
    gold = json.loads(GABARITO_BRACO.read_text())["quadros"]
    H_m_q16 = np.array(json.loads(Q16_H.read_text())["H"], dtype=float)
    cal = json.loads(MVP_CALIB.read_text())["H"]
    H_m_mvp = np.array(cal["estabilizada_sem_gabarito"], dtype=float)
    saida = {}
    for nome, H_m in (("q16", H_m_q16), ("q02", H_m_mvp)):
        H_d, rep = h_dono(gold[nome])
        reg, linhas, linhas_m, iguais, comp = analisar(nome, H_d, H_m)
        # reconstrói xy das aceitas para a imagem (mesmo critério)
        ret = {
            "reproj_dono": rep,
            "H_dono": H_d.tolist(),
            "contagem": {
                "total_notas": reg["total_notas"],
                "casa_0": reg["casa_0"],
                "sem_ponta_no_instante": reg["sem_ponta_no_instante"],
                "sem_mao_esquerda": reg["sem_mao_esquerda"],
                "sem_t_ini": reg.get("sem_t_ini", 0),
                "instantes_distintos_pisados": len(reg["instantes_distintos"]),
                "instantes_com_aceita": len(reg["instantes_aceitos"]),
                "notas_aceitas_dono": len(linhas),
                "notas_aceitas_musica": len(linhas_m),
                "dedo_igual_entre_dono_e_musica": [iguais, comp],
            },
            "dono": resumo(linhas),
            "musica": resumo(linhas_m),
        }
        saida[nome] = ret
        print(nome, json.dumps(ret, ensure_ascii=False, indent=1))
        # imagem: recalcula xy das aceitas
        notas, mapa = notas_de(nome)
        marcados = []
        for nota in notas:
            if nota["casa"] <= 0 or nota.get("t_ini") is None:
                continue
            t = round(float(nota["t_ini"]), 3)
            if t not in mapa:
                continue
            cands = pontas_esq(mapa[t])
            if not cands:
                continue
            corda, casa = nota["corda"], nota["casa"]
            vc = v_corda(corda)
            largura = float(largura_casa(H_d, np.array([casa]), np.array([vc]))[0])
            esp = aplicar_homografia(H_d, np.array([[u_casa(casa, 0.5), vc]]))[0]
            xy = np.array([c[2] for c in cands])
            dist = np.linalg.norm(xy - esp, axis=1)
            j = int(np.argmin(dist))
            if dist[j] < ACEITE * largura:
                marcados.append({"corda": corda, "xy": xy[j]})
        png_in = MAOS_M3B / "quadros" / f"{nome}.png"
        desenhar(nome, H_d, None, marcados, png_in, DIAG / f"{nome}_pontas.png")
    (DIAG / "resultado.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
