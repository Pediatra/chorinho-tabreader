"""Recorta os erros de leitura da rede (t82) para conferência visual.

Lê as cópias pre.json e conferencia_t82.json desta pasta, casa notas por
(corda, x_centro_quadro), classifica em casa_errada / falsa / faltando e
grava recortes ampliados 3x com legenda, além das folhas por classe.
"""

import json
import os
import unicodedata

import cv2
import numpy as np

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
PASTA = os.path.dirname(os.path.abspath(__file__))
LARGURA_FOLHA = 1400
ESCALA = 3
COR = {
    "casa_errada": (0, 0, 255),
    "falsa": (255, 0, 255),
    "faltando": (0, 200, 0),
}
ORDEM = ["casa_errada", "falsa", "faltando"]


def carregar(nome: str) -> dict:
    """Lê um JSON desta pasta.

    Args:
        nome: nome do arquivo dentro de erros/.

    Returns:
        Conteúdo decodificado.
    """
    with open(os.path.join(PASTA, nome), encoding="utf-8") as f:
        return json.load(f)


def classificar(pre: dict, conf: dict) -> list[dict]:
    """Casa as notas lidas com a conferência do dono.

    Args:
        pre: conteúdo de pre.json.
        conf: conteúdo de conferencia_t82.json.

    Returns:
        Lista de erros com classe, tela, corda, x e casas.
    """
    telas_pre = {t["id"]: t for t in pre["telas"]}
    erros = []
    for tc in conf["telas"]:
        if tc.get("conferida") is not True:
            continue
        tp = telas_pre[tc["id"]]
        lidas = {(n["corda"], n["x_centro_quadro"]): n for n in tp["notas"]}
        dono = {(n["corda"], n["x_centro_quadro"]): n for n in tc["notas"]}
        for k, n in lidas.items():
            if k not in dono:
                erros.append(_erro("falsa", tp, k, str(n["casa"]), None))
            elif str(dono[k]["casa"]) != str(n["casa"]):
                erros.append(
                    _erro("casa_errada", tp, k, str(n["casa"]), str(dono[k]["casa"]))
                )
        for k, n in dono.items():
            if k not in lidas:
                erros.append(_erro("faltando", tp, k, None, str(n["casa"])))
    return erros


def _erro(classe: str, tela: dict, chave: tuple, lida: str | None, dono: str | None) -> dict:
    """Monta o registro de um erro.

    Args:
        classe: classe do erro.
        tela: tela de pre.json onde ocorreu.
        chave: (corda, x_centro_quadro).
        lida: casa lida pela rede, ou None.
        dono: casa dada pelo dono, ou None.

    Returns:
        Dicionário com os dados do erro.
    """
    return {
        "classe": classe,
        "tela": tela["id"],
        "passo": tela["passo"],
        "painel": tela["painel"],
        "linhas_y": tela["linhas_y"],
        "corda": chave[0],
        "x": chave[1],
        "lida": lida,
        "dono": dono,
    }


def canal_ascii(texto: str) -> str:
    """Reduz o nome do canal a ASCII para caber na legenda.

    Args:
        texto: nome original do canal.

    Returns:
        Nome em ASCII, sem espaços nas pontas.
    """
    limpo = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(limpo.split()).strip()


def recortar(erro: dict, pasta_quadro: str, canal: str, n: int) -> np.ndarray:
    """Gera o recorte ampliado de um erro, com retângulo e legenda.

    Args:
        erro: registro do erro.
        pasta_quadro: caminho do quadro.png.
        canal: nome do canal da tela.
        n: número sequencial do erro.

    Returns:
        Imagem BGR do recorte com legenda.
    """
    quadro = cv2.imread(pasta_quadro)
    if quadro is None:
        raise FileNotFoundError(pasta_quadro)
    h, w = quadro.shape[:2]
    p = erro["passo"]
    x0p, y0p, x1p, y1p = erro["painel"]
    xc = erro["x"]
    yc = erro["linhas_y"][erro["corda"] - 1]
    ex0 = int(max(0, round(xc - 4 * p)))
    ex1 = int(min(w, round(xc + 4 * p)))
    ey0 = int(max(0, round(y0p - 2 * p)))
    ey1 = int(min(h, round(y1p + p)))
    recorte = quadro[ey0:ey1, ex0:ex1].copy()
    cor = COR[erro["classe"]]
    cx = int(round(xc - ex0))
    cy = int(round(yc - ey0))
    meia_l = max(2, int(round(p * 0.5)))
    meia_a = max(2, int(round(p * 0.4)))
    grande = cv2.resize(
        recorte, None, fx=ESCALA, fy=ESCALA, interpolation=cv2.INTER_CUBIC
    )
    cv2.rectangle(
        grande,
        ((cx - meia_l) * ESCALA, (cy - meia_a) * ESCALA),
        ((cx + meia_l) * ESCALA, (cy + meia_a) * ESCALA),
        cor,
        2,
    )
    faixa = np.full((46, grande.shape[1], 3), 255, dtype=np.uint8)
    lida = erro["lida"] if erro["lida"] is not None else "-"
    dono = erro["dono"] if erro["dono"] is not None else "-"
    texto = (
        f"{erro['classe']} | tela {erro['tela']} {canal_ascii(canal)} | "
        f"corda {erro['corda']} | lida {lida} -> dono {dono}"
    )
    cv2.putText(
        faixa, texto, (8, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA
    )
    return np.vstack([grande, faixa])


def folha(imagens: list[np.ndarray]) -> np.ndarray:
    """Empilha recortes numa folha de largura uniforme.

    Args:
        imagens: recortes já prontos.

    Returns:
        Folha com LARGURA_FOLHA de largura.
    """
    ajustadas = []
    for im in imagens:
        f = LARGURA_FOLHA / im.shape[1]
        ajustadas.append(cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA))
    sep = np.full((12, LARGURA_FOLHA, 3), 60, dtype=np.uint8)
    partes = []
    for im in ajustadas:
        partes.append(im)
        partes.append(sep)
    return np.vstack(partes)


def main() -> None:
    """Gera recortes individuais, folhas por classe e lista de erros em JSON."""
    pre = carregar("pre.json")
    conf = carregar("conferencia_t82.json")
    indice = {d["id"]: d for d in carregar_indice()}
    erros = classificar(pre, conf)
    erros.sort(key=lambda e: (ORDEM.index(e["classe"]), e["tela"], e["corda"]))
    contagem = {c: sum(1 for e in erros if e["classe"] == c) for c in ORDEM}
    print("contagem", contagem, "total", len(erros))
    por_classe: dict[str, list[np.ndarray]] = {c: [] for c in ORDEM}
    lista = []
    for i, e in enumerate(erros, start=1):
        info = indice[e["tela"]]
        quadro = os.path.join(RAIZ, info["pasta"], "quadro.png")
        im = recortar(e, quadro, info["canal"], i)
        nome = f"{i:02d}_{e['classe']}.png"
        cv2.imwrite(os.path.join(PASTA, nome), im)
        por_classe[e["classe"]].append(im)
        lista.append({**e, "n": i, "canal": info["canal"], "arquivo": nome})
    for c in ORDEM:
        if por_classe[c]:
            cv2.imwrite(os.path.join(PASTA, f"folha_{c}.png"), folha(por_classe[c]))
    with open(os.path.join(PASTA, "_lista.json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)


def carregar_indice() -> list[dict]:
    """Lê o índice de telas (cópia local do que está em ferramenta/).

    Returns:
        Lista de entradas do indice.json.
    """
    with open(
        os.path.join(RAIZ, "data/saida/t82/ferramenta/indice.json"), encoding="utf-8"
    ) as f:
        return json.load(f)


if __name__ == "__main__":
    main()
