"""Para cada quadro que mudou no censo, mede as pautas completadas pela passada nova.

Imprime, por pauta nova: largura do quadro, caixa, extensão (x0, x1) de cada uma das 4
linhas fortes de origem, e a decisão de ``e_tablatura`` (a mesma do ``paginar``).

    python data/saida/partitura/diag/medir_completadas.py > .../medir_completadas.txt
"""

import json

import cv2

from tab import partitura_pauta as pp
from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_video import e_tablatura

D = RAIZ / "data" / "saida" / "partitura" / "diag"


def _mudancas() -> list[tuple[str, float]]:
    """Lê (arquivo, t) dos quadros ganhos ou com contagem diferente.

    Returns:
        Pares (vídeo relativo ao acervo, instante).
    """
    pares = []
    for linha in (D / "comparar_censo.txt").read_text(encoding="utf-8").splitlines():
        if " | " in linha and "t=" in linha and "->" in linha:
            partes = linha.split(" | ")
            video = partes[1]
            t = float(partes[2].split("t=")[1].split()[0])
            pares.append((video, t))
    return pares


def _arquivo(video: str) -> str:
    """Acha o nome exato do arquivo no censo (as linhas do txt podem truncar)."""
    for linha in (D / "censo_completar" / "amostra.jsonl").open(encoding="utf-8"):
        reg = json.loads(linha)
        if reg["arquivo"] == video:
            return reg["arquivo"]
    return video


def main() -> None:
    """Imprime a medição das pautas completadas."""
    for video, t in _mudancas():
        quadro = quadro_em(str(acervo() / _arquivo(video)), t)
        if quadro is None:
            print(f"{video[:40]} t={t}: sem quadro")
            continue
        cinza = cv2.cvtColor(quadro, cv2.COLOR_BGR2GRAY)
        largura = cinza.shape[1]
        abertas = [pp._abrir(m, largura) for m in pp._mascaras_de_tinta(cinza)]
        for k, aberta in enumerate(abertas):
            linhas = pp._linhas_da_abertura(aberta, largura, escura=(k == 0))
            fortes = [x for x in linhas if x.forte]
            antes = []
            i = 0
            while i + 5 <= len(fortes):
                g = fortes[i : i + 5]
                p = pp._pauta_do_grupo(g, largura)
                med = round(sorted(x.espessura for x in g)[2])
                if (
                    p is not None
                    and max(x.espessura for x in g) <= pp._espessura_limite(med)
                    and pp._linhas_sao_crista(g, p, cinza)
                    and not pp._ha_sexta_linha(p, linhas, largura, med)
                    and not pp._ha_sexta_na_janela(p, aberta)
                ):
                    antes.append(p)
                    i += 5
                else:
                    i += 1
            novas = pp._completar_grupos_de_quatro(linhas, aberta, cinza, largura, antes)
            for p in novas:
                origem = [
                    (round(x.y), x.x0, x.x1)
                    for x in fortes
                    if round(x.y) in p.ys
                ]
                tab = e_tablatura(cinza, list(p.ys), p.entrelinha, p.x0, p.x1 + 1)
                print(
                    f"{video[:45]} t={t} W={largura} pol={k} ys={p.ys}"
                    f" x={p.x0}..{p.x1} linhas={origem}"
                    f" {'TAB' if tab else 'pauta'}"
                )


if __name__ == "__main__":
    main()
