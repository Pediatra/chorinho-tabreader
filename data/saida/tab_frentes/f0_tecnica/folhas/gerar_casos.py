"""Folhas de casos da F0.1 (CA7): recortes por classe, causa e certas, para olhar.

Usa as funções de ``tab.tecnica_regua`` com a folga do plano (0,5). Escolhe, por classe
com 10 marcas ou mais: até 5 perdas (a), até 5 perdas (b) e até 3 certas. Grava os PNG
em ``folhas/casos/`` e uma folha por classe em ``folhas/folha_<classe>.png``.
"""

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from tab import caminhos, detector_tab
from tab import tecnica_regua as tr

PASTA = caminhos.TAB_FRENTE_0 / "folhas"
CLASSES = ("h", "p", "mordente", "prolongamento", "slide", "harm", "bend", "arpejo", "rasgueado")
MAX_A = 5
MAX_B = 5
MAX_CERTAS = 3
LARGURA_FOLHA = 900


def _escolher(linhas: list[dict]) -> list[tuple[str, dict]]:
    """Escolhe os casos de cada classe, na ordem do relatório.

    Args:
        linhas: linhas da leitura primária do relatório.

    Returns:
        Lista de ``(grupo, linha)``, grupo é ``<classe>_<a|b|certa>``.
    """
    por_grupo: dict[str, list[dict]] = defaultdict(list)
    for ln in linhas:
        if ln["classe"] not in CLASSES:
            continue
        if ln["certa"]:
            grupo = f"{ln['classe']}_certa"
        elif ln["causa"] in ("a", "b"):
            grupo = f"{ln['classe']}_{ln['causa']}"
        else:
            continue
        por_grupo[grupo].append(ln)
    limites = {"a": MAX_A, "b": MAX_B, "certa": MAX_CERTAS}
    escolhidos = []
    for grupo, lista in por_grupo.items():
        tipo = grupo.rsplit("_", 1)[1]
        for ln in lista[: limites[tipo]]:
            escolhidos.append((grupo, ln))
    return escolhidos


def _folha(titulo: str, imagens: list[tuple[str, np.ndarray]], caminho: Path) -> None:
    """Empilha os recortes com a legenda de cada um, numa imagem só.

    Args:
        titulo: título da folha.
        imagens: pares ``(legenda, recorte BGR)``.
        caminho: PNG de destino.
    """
    faixas = [np.full((40, LARGURA_FOLHA, 3), 255, np.uint8)]
    cv2.putText(faixas[0], titulo, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    for legenda, img in imagens:
        escala = min(1.0, (LARGURA_FOLHA - 20) / img.shape[1])
        peca = cv2.resize(img, None, fx=escala * 2, fy=escala * 2)
        if peca.shape[1] > LARGURA_FOLHA - 20:
            peca = cv2.resize(peca, (LARGURA_FOLHA - 20, int(peca.shape[0] * (LARGURA_FOLHA - 20) / peca.shape[1])))
        rotulo = np.full((30, LARGURA_FOLHA, 3), 255, np.uint8)
        cv2.putText(rotulo, legenda[:120], (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
        bloco = np.full((peca.shape[0] + 10, LARGURA_FOLHA, 3), 255, np.uint8)
        bloco[5 : 5 + peca.shape[0], 10 : 10 + peca.shape[1]] = peca
        faixas.append(rotulo)
        faixas.append(bloco)
    cv2.imwrite(str(caminho), np.vstack(faixas))


def main() -> None:
    """Gera os recortes escolhidos e as folhas por classe, e grava o índice dos casos."""
    rel = json.loads((PASTA.parent / "regua_tecnica.json").read_text(encoding="utf-8"))
    escolhidos = _escolher(rel["linhas_primaria"])
    necessarias = {(ln["fonte"], ln["tela"]) for _, ln in escolhidos}
    telas = {(t.fonte, t.id): t for t in tr.carregar_telas() if (t.fonte, t.id) in necessarias}
    modelo = detector_tab.carregar(caminhos.DETECTOR_PADRAO)
    reserva = rel["telas_lidas"]["passo_reserva"]
    folga = rel["folga"]["usada"]
    pasta_casos = PASTA / "casos"
    indice: list[dict] = []
    por_classe: dict[str, list[tuple[str, np.ndarray]]] = defaultdict(list)
    for grupo, ln in escolhidos:
        tela = telas[(ln["fonte"], ln["tela"])]
        lido = tr.ler_tela(tela, {"primaria": modelo})
        passo = lido.passo or reserva
        notas = lido.notas["primaria"]
        r = next(x for x in tela.regioes if x.indice == ln["indice"])
        av = tr.avaliar_regiao(r, notas, tela.notas_dono, passo, folga)
        recorte = tr._recorte_marca(lido, tela, r, av, notas, passo, pasta_casos)
        alcance = tr.notas_no_alcance(r, notas, passo, folga)
        tokens = [f"c{n['corda']}:{'+'.join(n['tecnica']) or '-'}" for n in alcance]
        indice.append({"grupo": grupo, "recorte": recorte, "tokens_rede": tokens, **{k: ln[k] for k in ("fonte", "tela", "indice", "classe", "causa", "rede", "tecnica_dono", "obs", "certa")}})
        if recorte:
            img = cv2.imread(str(PASTA.parent / recorte))
            legenda = f"{grupo} | {ln['fonte']} t{ln['tela']} r{ln['indice']} | dono {ln['tecnica_dono']} | rede {ln['rede']} {tokens}"
            por_classe[ln["classe"]].append((legenda, img))
    (PASTA / "casos.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    for classe in CLASSES:
        if por_classe[classe]:
            _folha(f"folha {classe} (F0.1, folga {folga})", por_classe[classe], PASTA / f"folha_{classe}.png")
    print("casos", len(indice))


if __name__ == "__main__":
    main()
