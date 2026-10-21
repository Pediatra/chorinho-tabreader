"""Roda ``tab.transcrever`` num vídeo, no controle (constante = inf) ou na variante (código).

Uso (dentro do container, a partir de /app):
    python data/saida/barline_fina/rodar.py VIDEO SAIDA_JSON {controle,variante}

No controle, ``tabseg.LARGURA_MAX_BARLINE_PASSOS`` vira ``inf``, o que reproduz o descarte
antigo (qualquer largura numa coluna de barline era descartada). Na variante nada é
remendado: vale o valor do código. ``_glifos_por_faixa`` lê a constante do globals do
módulo em tempo de chamada, então o remendo pega. Nenhum módulo de ``tab`` importa a
constante por nome (conferido com grep).
"""

import sys

from tab import tabseg
from tab import transcrever


def main() -> int:
    """Aplica o modo, chama ``tab.transcrever.main`` sem ``--modelo`` (usa o padrão).

    Returns:
        Código de saída de ``tab.transcrever.main``.
    """
    video, saida, modo = sys.argv[1], sys.argv[2], sys.argv[3]
    if modo == "controle":
        tabseg.LARGURA_MAX_BARLINE_PASSOS = float("inf")
    elif modo != "variante":
        raise SystemExit(f"modo desconhecido: {modo}")
    print(f"modo={modo} LARGURA_MAX_BARLINE_PASSOS={tabseg.LARGURA_MAX_BARLINE_PASSOS}")
    sys.argv = ["tab.transcrever", video, "--json", saida]
    return transcrever.main()


if __name__ == "__main__":
    sys.exit(main())
