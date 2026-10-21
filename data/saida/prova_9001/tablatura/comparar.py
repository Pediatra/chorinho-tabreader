"""Compara duas pastas de saida da prova de antes/depois (decisao 9001).

Uso: python3 comparar.py <pasta_a> <pasta_b>

Regras:
- os produto_*.json tem apenas gerado_por.em e gerado_por.commit removidos
  (mudam por construcao: data/hora e hash do commit). O resto do JSON e
  comparado byte a byte depois de re-serializado do mesmo jeito nos dois lados.
- todos os outros arquivos (avaliar_*.json, *.txt) sao comparados byte a byte,
  sem nenhuma alteracao.
- nos .txt, o caminho da pasta de saida de cada lado (host ou /app/...) vira
  <PASTA>; o resto da linha continua byte a byte.
- para .txt diferentes, mostra as linhas que mudam (nada e escondido).

Sai com 0 se IGUAL e 1 se houver diferenca.
"""

import difflib
import json
import os
import re
import sys

CAMPOS_IGNORADOS = ("em", "commit")
# raiz do repositorio: data/saida/prova_9001/tablatura/comparar.py -> 4 niveis
REPO_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def listar(pasta: str) -> set[str]:
    """Lista os arquivos (caminhos relativos) de uma pasta, recursivamente.

    Args:
        pasta: diretorio a percorrer.

    Returns:
        Conjunto de caminhos relativos a pasta.
    """
    achados = set()
    for raiz, _, nomes in os.walk(pasta):
        for nome in nomes:
            completo = os.path.join(raiz, nome)
            achados.add(os.path.relpath(completo, pasta))
    return achados


def marcar_pasta(texto: str, pasta: str) -> str:
    """Troca o caminho da pasta de saida, do lado dado, pelo marcador <PASTA>.

    O programa imprime o caminho que recebe (ex.: relatorio salvo em ...). Os
    caminhos trocados sao o absoluto no host e o absoluto dentro do container
    (/app/...). So o prefixo da pasta e trocado; o resto da linha fica igual.

    Args:
        texto: conteudo de um .txt.
        pasta: pasta de saida deste lado da comparacao.

    Returns:
        O texto com o caminho da pasta trocado por <PASTA>.
    """
    absoluta = os.path.abspath(pasta)
    no_container = "/app/" + os.path.relpath(absoluta, REPO_RAIZ)
    for caminho in sorted({absoluta, no_container}, key=len, reverse=True):
        texto = re.sub(re.escape(caminho) + r"(?![\w.\-])", "<PASTA>", texto)
    return texto


def conteudo(pasta: str, rel: str) -> bytes:
    """Le o conteudo de um arquivo; produto_*.json sai sem os campos de data e commit.

    Args:
        pasta: pasta base.
        rel: caminho relativo do arquivo.

    Returns:
        Os bytes a comparar.
    """
    with open(os.path.join(pasta, rel), "rb") as f:
        bruto = f.read()
    nome = os.path.basename(rel)
    if nome.startswith("produto_") and nome.endswith(".json"):
        dados = json.loads(bruto.decode("utf-8"))
        gerado = dados.get("gerado_por")
        if isinstance(gerado, dict):
            for campo in CAMPOS_IGNORADOS:
                gerado.pop(campo, None)
        return json.dumps(dados, ensure_ascii=False, indent=2).encode("utf-8")
    if nome.endswith(".txt"):
        return marcar_pasta(bruto.decode("utf-8"), pasta).encode("utf-8")
    return bruto


def linhas_diferentes(a: bytes, b: bytes) -> list[str]:
    """Mostra as linhas de texto que mudam entre dois conteudos.

    Args:
        a: conteudo da pasta A.
        b: conteudo da pasta B.

    Returns:
        Linhas do diff (sem o cabecalho), no formato do difflib.
    """
    la = a.decode("utf-8", errors="replace").splitlines()
    lb = b.decode("utf-8", errors="replace").splitlines()
    diff = difflib.unified_diff(la, lb, "A", "B", lineterm="", n=0)
    return [linha for linha in diff if not linha.startswith(("---", "+++"))][:30]


def main(argv: list[str]) -> int:
    """Compara as duas pastas e imprime o resultado.

    Args:
        argv: argumentos da linha de comando (duas pastas).

    Returns:
        0 se IGUAL, 1 se houver diferenca, 2 em uso errado.
    """
    if len(argv) != 2:
        print("uso: comparar.py <pasta_a> <pasta_b>", file=sys.stderr)
        return 2
    a, b = argv
    arquivos_a = listar(a)
    arquivos_b = listar(b)
    diferentes = []
    for rel in sorted(arquivos_a | arquivos_b):
        if rel not in arquivos_a or rel not in arquivos_b:
            lado = "so em A" if rel in arquivos_a else "so em B"
            diferentes.append(f"{rel} ({lado})")
            continue
        ca = conteudo(a, rel)
        cb = conteudo(b, rel)
        if ca != cb:
            diferentes.append(rel)
            if rel.endswith(".txt"):
                for linha in linhas_diferentes(ca, cb):
                    print(f"  {rel}: {linha}")
    if not diferentes:
        print(f"IGUAL ({len(arquivos_a)} arquivos comparados)")
        return 0
    print("DIFERENTES:")
    for nome in diferentes:
        print(f"  {nome}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
