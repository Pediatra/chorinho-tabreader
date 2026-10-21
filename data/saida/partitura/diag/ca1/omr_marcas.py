"""O que o .omr do Audiveris guarda de confiança: grade por símbolo, duração por compasso.

Conta, nos .omr da P1 (21 recortes) e do piloto sem produto (162), quantos compassos têm
duração esperada (``expected``, só existe se o Audiveris achou a fórmula de compasso),
quantos têm duração lida diferente da esperada e quantos o Audiveris marca ``abnormal``.
Só lê; não grava. Uso: python3 data/saida/partitura/diag/ca1/omr_marcas.py
"""

import collections
import glob
import re
import zipfile

GRUPOS = {
    "p1": "data/saida/partitura/p1/omr/audiveris/x2_margem/*/entrada.omr",
    "piloto": "data/saida/partitura/sem_produto/*/omr/audiveris/x2_margem/*/entrada.omr",
}


def main() -> None:
    """Imprime a contagem por grupo."""
    for grupo, padrao in GRUPOS.items():
        c = collections.Counter()
        for f in sorted(glob.glob(padrao)):
            z = zipfile.ZipFile(f)
            nomes = [n for n in z.namelist() if re.fullmatch(r"sheet#\d+/sheet#\d+\.xml", n)]
            c["omr"] += 1
            c["omr sem folha"] += not nomes
            for n in nomes:
                s = z.read(n).decode("utf-8", "replace")
                pilhas = re.findall(r"<stack [^>]*>", s)
                c["compassos"] += len(pilhas)
                c["abnormal"] += len(re.findall(r'<measure [^>]*abnormal="true"', s))
                for p in pilhas:
                    esp = re.search(r'expected="([^"]+)"', p)
                    dur = re.search(r'duration="([^"]+)"', p)
                    if not esp:
                        c["sem duracao esperada"] += 1
                    elif dur and dur.group(1) != esp.group(1):
                        c["duracao != esperada"] += 1
                notas = [float(g) for g in re.findall(r' grade="([0-9.]+)"', s)]
                c["simbolos com grade"] += len(notas)
                c["grade < 0,5"] += sum(g < 0.5 for g in notas)
        print(grupo, dict(c))


if __name__ == "__main__":
    main()
