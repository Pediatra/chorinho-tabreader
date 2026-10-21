"""Checa páginas duplicadas nos recortes de ``paginar`` do piloto.

Para cada vídeo de ``piloto_videos.txt`` que tem ``recortes/indice.json`` em
``sem_produto/<slug>``, lê o instante ``t`` de cada página, lê o quadro (``quadro_em``),
calcula a assinatura nova (``assinatura``) e compara todos os pares de páginas com
``diferenca``. Imprime os pares com diferença menor que 0,4, em ordem, e os 5 menores pares
de cada vídeo (a folga em relação a ``LIMIAR_PAGINA``).

Nota: o agrupamento compara a assinatura da primeira amostra de cada exibição, não a do
instante ``t``; por isso uma diferença pequena aqui não é, por si, prova de duplicata.

    python data/saida/partitura/diag/duplicatas.py
"""

import json
from pathlib import Path

from tab.caminhos import RAIZ, acervo
from tab.leitor import quadro_em
from tab.partitura_pauta import achar_pautas
from tab.partitura_video import LIMIAR_PAGINA, assinatura, diferenca
from tab.video import _slug

DIAG = RAIZ / "data" / "saida" / "partitura" / "diag"
SEM_PRODUTO = RAIZ / "data" / "saida" / "partitura" / "sem_produto"
LIMIAR_IMPRESSAO = 0.4


def main() -> None:
    """Imprime os pares próximos de cada vídeo do piloto."""
    linhas = (DIAG / "piloto_videos.txt").read_text(encoding="utf-8").splitlines()
    print(f"LIMIAR_PAGINA = {LIMIAR_PAGINA}")
    for video in linhas:
        pasta = SEM_PRODUTO / _slug(video) / "recortes" / "indice.json"
        if not pasta.exists():
            print(f"== {video}: sem indice.json")
            continue
        indice = json.loads(pasta.read_text(encoding="utf-8"))
        paginas: dict[int, float] = {}
        for entrada in indice:
            paginas.setdefault(entrada["pagina"], entrada["t"])
        assinaturas = {}
        caminho = str(acervo() / video)
        for numero, t in sorted(paginas.items()):
            quadro = quadro_em(caminho, t)
            if quadro is None:
                continue
            sig = assinatura(quadro, achar_pautas(quadro))
            if sig is not None:
                assinaturas[numero] = sig
        pares = []
        numeros = sorted(assinaturas)
        for i, a in enumerate(numeros):
            for b in numeros[i + 1 :]:
                pares.append((diferenca(assinaturas[a], assinaturas[b]), a, b))
        pares.sort()
        print(f"== {video}: paginas com assinatura {len(assinaturas)}")
        abaixo = [p for p in pares if p[0] < LIMIAR_IMPRESSAO]
        for dif, a, b in abaixo:
            print(f"  P{a:02d} x P{b:02d}: {dif:.3f}")
        if not abaixo:
            print(f"  nenhum par abaixo de {LIMIAR_IMPRESSAO}")
        for dif, a, b in pares[:5]:
            print(f"  menor P{a:02d} x P{b:02d}: {dif:.3f}")


if __name__ == "__main__":
    main()
