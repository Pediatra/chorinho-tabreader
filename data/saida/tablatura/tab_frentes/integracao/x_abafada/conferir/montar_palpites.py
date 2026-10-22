"""Palpites de nota abafada (X) em cópias do ouro, para o dono conferir.

Lê o ouro gravado e o ``pre.json`` (só leitura). Para cada tela com região de X,
roda o modelo ``detector_tab_v3ft_d4_ger`` no quadro de referência e mantém os
rótulos ``x`` que caem numa região (palpite do modelo). Região sem nenhum rótulo
ganha um X por corda, no centro (palpite da regra). Grava a cópia do ouro e uma
folha PNG com os palpites, em ``conferir/``.
"""

import copy
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "/app")
from tab import caminhos, detector_tab, leitor, ouro_video, painel  # noqa: E402

GOLD = Path("/app/data/gold/ouro_video")
PRE = Path("/app/data/saida/ouro_video")
CONFERIR = Path(
    "/app/data/saida/tab_frentes/integracao/x_abafada/conferir"
)
MODELO = Path("/app/artefatos/detector_tab_v3ft_d4_ger/modelo.pt")
SLUGS = [
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
    "tabroom_335_larry_carlton_fingerstyle_guitar",
]
VERMELHO = (0, 0, 255)
AZUL = (255, 0, 0)
CINZA = (160, 160, 160)


def _regioes_x(tela: dict) -> list[dict]:
    """Regiões da tela marcadas só com a técnica ``x``.

    Args:
        tela: uma tela do ouro.

    Returns:
        As regiões de X, na ordem do ouro.
    """
    return [r for r in tela.get("regioes", []) if r.get("tecnica") == ["x"]]


def _regiao_do_ponto(
    xq: float, corda: int, regioes: list[dict], passo: float
) -> int | None:
    """Índice da região de X que contém o ponto, com folga de meio passo em x.

    Args:
        xq: x no quadro do rótulo.
        corda: corda do rótulo (1 em cima).
        regioes: regiões de X da tela.
        passo: distância entre cordas, em px.

    Returns:
        O índice da primeira região que contém o ponto, ou None.
    """
    for i, r in enumerate(regioes):
        a, b = r["cordas"]
        x0, x1 = r["x_quadro"]
        if a <= corda <= b and x0 - 0.5 * passo <= xq <= x1 + 0.5 * passo:
            return i
    return None


def _livre(aceitos: list[tuple[int, float]], corda: int, xc: float, passo: float) -> bool:
    """Diz se não há X já aceito na mesma corda a menos de meio passo.

    Args:
        aceitos: pares (corda, x_centro) já aceitos.
        corda: corda do candidato.
        xc: x centro do candidato.
        passo: distância entre cordas, em px.

    Returns:
        True se o candidato pode entrar.
    """
    return all(
        not (c == corda and abs(xc - x) < 0.5 * passo) for c, x in aceitos
    )


def _quadro_e_painel(video: str, t_s: float) -> object | None:
    """Recorte do painel de tablatura no quadro de referência.

    Args:
        video: caminho do vídeo no acervo.
        t_s: instante do quadro, em segundos.

    Returns:
        O ``Candidato`` do painel, ou None se o quadro não tem tablatura.
    """
    quadro = leitor.quadro_em(video, t_s)
    if quadro is None:
        return None
    return painel.escolher_ou_mascara(quadro)


def _folha(
    slug: str, blocos: list[tuple[str, object | None, dict, list[tuple[int, float, str]], dict]]
) -> None:
    """Grava a folha PNG com os recortes e os palpites desenhados.

    Args:
        slug: nome do vídeo (para o arquivo).
        blocos: por tela, (rótulo, recorte do painel, pre da tela, palpites, regiões).
    """
    imagens = []
    for rotulo, c, pre_tela, palpites, regioes in blocos:
        if c is None:
            faixa = np.full((60, 1200, 3), 255, np.uint8)
            cv2.putText(faixa, f"{rotulo}: sem painel", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
            imagens.append(faixa)
            continue
        roi = c.roi if c.roi.ndim == 3 else cv2.cvtColor(c.roi, cv2.COLOR_GRAY2BGR)
        img = roi.copy()
        passo = float(pre_tela["passo"])
        linhas = pre_tela["linhas_y"]
        for r in regioes:
            a, b = r["cordas"]
            x0, x1 = r["x_quadro"]
            ya = linhas[a - 1] - passo / 2 - c.y0
            yb = linhas[b - 1] + passo / 2 - c.y0
            cv2.rectangle(
                img,
                (int(x0 - c.x0), int(ya)),
                (int(x1 - c.x0), int(yb)),
                CINZA,
                1,
            )
        for corda, xc, origem in palpites:
            cor = VERMELHO if origem == "palpite_x_modelo" else AZUL
            px = int(round(xc - c.x0))
            py = int(round(linhas[corda - 1] - c.y0))
            cv2.circle(img, (px, py), 9, cor, 2)
        cabecalho = np.full((28, img.shape[1], 3), 255, np.uint8)
        nm = sum(1 for p in palpites if p[2] == "palpite_x_modelo")
        nr = sum(1 for p in palpites if p[2] == "palpite_x_regra")
        cv2.putText(
            cabecalho,
            f"{rotulo}  modelo {nm} (vermelho)  regra {nr} (azul)",
            (8, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            1,
        )
        imagens.append(np.vstack([cabecalho, img]))
    largura = max(i.shape[1] for i in imagens)
    tela = []
    for i in imagens:
        if i.shape[1] < largura:
            i = np.hstack([i, np.full((i.shape[0], largura - i.shape[1], 3), 255, np.uint8)])
        tela.append(i)
        tela.append(np.full((10, largura, 3), 200, np.uint8))
    CONFERIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(CONFERIR / f"{slug}_folha.png"), np.vstack(tela))


def processar(slug: str, modelo: object) -> dict:
    """Monta a cópia do ouro com palpites de X e a folha, para um vídeo.

    Args:
        slug: nome do vídeo (sem extensão) em ``data/gold/ouro_video``.
        modelo: ``DetectorTab`` já carregado.

    Returns:
        Resumo com as contagens e as divergências antes e depois.
    """
    gold = json.loads((GOLD / f"{slug}.json").read_text(encoding="utf-8"))
    pre = json.loads((PRE / slug / "pre.json").read_text(encoding="utf-8"))
    pre_telas = {t["id"]: t for t in pre["telas"]}
    video = str(caminhos.acervo() / gold["video"])
    copia = copy.deepcopy(gold)
    ferr = {t["id"]: t for t in copia["ferramenta"]["telas"]}
    base = ouro_video.divergencias_do_estado(pre, gold)
    px = 0
    resumo = {
        "telas_com_x": 0,
        "regioes_x": 0,
        "detec_modelo_bruto": 0,
        "palpites_modelo": 0,
        "palpites_regra": 0,
        "descartados_fora_regiao": 0,
        "descartados_colisao": 0,
        "telas_sem_painel": [],
        "telas_marcadas": [],
        "divergencias_antes": base,
    }
    blocos = []
    for tela in copia["telas"]:
        regioes = _regioes_x(tela)
        if not regioes:
            continue
        pre_tela = pre_telas[tela["id"]]
        passo = float(pre_tela["passo"])
        linhas = pre_tela["linhas_y"]
        resumo["telas_com_x"] += 1
        resumo["regioes_x"] += len(regioes)
        if ferr[tela["id"]].get("junta_em"):
            raise ValueError(f"tela {tela['id']} está juntada; não cabe palpite")
        c = _quadro_e_painel(video, pre_tela["quadro_ref_s"])
        if c is None:
            resumo["telas_sem_painel"].append(tela["id"])
            detec = []
        else:
            detec = []
            bruto = detector_tab.detectar(modelo, c.roi, c.grade.linhas_y, c.passo)
            for p in bruto:
                if p["rotulo"] == "x":
                    detec.append((int(p["corda"]), float(p["x"]) + c.x0))
            resumo["detec_modelo_bruto"] += len(detec)
        aceitos: list[tuple[int, float]] = []
        palpites: list[tuple[int, float, str]] = []
        com_detec: set[int] = set()
        for corda, xq in detec:
            i = _regiao_do_ponto(xq, corda, regioes, passo)
            if i is None:
                resumo["descartados_fora_regiao"] += 1
                continue
            com_detec.add(i)
            xc = round(xq, 1)
            if _livre(aceitos, corda, xc, passo):
                aceitos.append((corda, xc))
                palpites.append((corda, xc, "palpite_x_modelo"))
                resumo["palpites_modelo"] += 1
            else:
                resumo["descartados_colisao"] += 1
        for i, r in enumerate(regioes):
            if i in com_detec:
                continue
            xc = round((r["x_quadro"][0] + r["x_quadro"][1]) / 2, 1)
            a, b = r["cordas"]
            for corda in range(a, b + 1):
                if _livre(aceitos, corda, xc, passo):
                    aceitos.append((corda, xc))
                    palpites.append((corda, xc, "palpite_x_regra"))
                    resumo["palpites_regra"] += 1
                else:
                    resumo["descartados_colisao"] += 1
        if not palpites:
            continue
        resumo["telas_marcadas"].append(tela["id"])
        tela["conferida"] = False
        ferr[tela["id"]]["conferida"] = False
        for corda, xc, origem in palpites:
            x_q = round(xc - passo / 3, 1)
            tela["notas"].append(
                {"corda": corda, "casa": "x", "x_quadro": x_q, "x_centro_quadro": xc}
            )
            px += 1
            yc = linhas[corda - 1]
            meia = passo / 2
            ferr[tela["id"]]["notas"].append(
                {
                    "id": f"px{px}",
                    "corda": corda,
                    "casa": "x",
                    "x_quadro": x_q,
                    "x_centro_quadro": xc,
                    "origem": origem,
                    "removida": False,
                    "caixa": [
                        round(xc - meia, 1),
                        round(yc - meia, 1),
                        round(xc + meia, 1),
                        round(yc + meia, 1),
                    ],
                }
            )
        tela["notas"].sort(key=lambda n: (n["x_quadro"], n["corda"]))
        blocos.append(
            (f"tela {tela['id']}", c, pre_tela, palpites, regioes)
        )
    destino = CONFERIR / f"{slug}.json"
    CONFERIR.mkdir(parents=True, exist_ok=True)
    ouro_video.gravar_atomico(destino, copia)
    resumo["divergencias_depois"] = ouro_video.divergencias_do_estado(
        pre, json.loads(destino.read_text(encoding="utf-8"))
    )
    _folha(slug, blocos)
    return resumo


def main() -> int:
    """Roda os dois vídeos e imprime o resumo.

    Returns:
        Código de saída (0).
    """
    modelo = detector_tab.carregar(MODELO)
    for slug in SLUGS:
        resumo = processar(slug, modelo)
        print(f"== {slug}", flush=True)
        for chave, valor in resumo.items():
            print(f"  {chave}: {valor}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
