"""Aplica as edições do passo 2 em tab/audio_alinhar.py (cada trecho deve casar uma vez)."""

import pathlib

ARQ = pathlib.Path("/var/home/gabriel/Projects/chorinho-dataset/tab/audio_alinhar.py")
s = ARQ.read_text(encoding="utf-8")


def troca(antigo: str, novo: str) -> None:
    global s
    n = s.count(antigo)
    assert n == 1, f"trecho casa {n} vezes: {antigo[:70]!r}"
    s = s.replace(antigo, novo)


# 1. docstring do módulo
troca(
    """Métodos:

- ``onsets`` (padrão)""",
    """Colunas abafadas (v2.1, rasgueado): pilhas de X sem altura (``colunas_abafadas``). Entram na
sequência da tela como ataques sem altura. Casam a um pico de fluxo forte com cosseno fixo
``COS_ABAFADA`` (nunca o cosseno de altura), não contam no cosseno médio nem em
``MIN_COLUNAS_CASADAS``, e a exibição é marcada ``rasgueado`` se ``LIMIAR_RASGUEADO`` ou mais das
suas colunas forem abafadas.

Métodos:

- ``onsets`` (padrão)""",
)

# 2. constantes novas, antes de N_POSICOES
troca(
    """#: Número de posições do perfil (MIDI_MIN a MIDI_MAX).
N_POSICOES = MIDI_MAX - MIDI_MIN + 1
""",
    """#: [v2.1] Cosseno fixo de uma coluna abafada (ataque sem altura) contra um pico de fluxo forte.
#: Não é cosseno de altura: entra só no DP, como ganho ``COS_ABAFADA - BASE_COS``. Fixado antes de
#: medir o efeito no acervo.
COS_ABAFADA = 0.5

#: [v2.1] Regra de coluna abafada (``colunas_abafadas``): cordas distintas e glifos com top-1
#: ``TOP1_ABAFADA`` que a coluna precisa ter. Com 3 cordas a regra pegava dígitos de acorde.
MIN_CORDAS_ABAFADA = 4
MIN_QUINZE_ABAFADA = 4
TOP1_ABAFADA = "15"

#: [v2.1] Fração de colunas abafadas a partir da qual a exibição é um rasgueado.
LIMIAR_RASGUEADO = 0.20

#: Número de posições do perfil (MIDI_MIN a MIDI_MAX).
N_POSICOES = MIDI_MAX - MIDI_MIN + 1
""",
)

# 3. parâmetros gravados na saída
troca(
    """        "RAIO_ENCAIXE_S": RAIO_ENCAIXE_S,
    }
""",
    """        "RAIO_ENCAIXE_S": RAIO_ENCAIXE_S,
        "COS_ABAFADA": COS_ABAFADA,
        "MIN_CORDAS_ABAFADA": MIN_CORDAS_ABAFADA,
        "MIN_QUINZE_ABAFADA": MIN_QUINZE_ABAFADA,
        "TOP1_ABAFADA": TOP1_ABAFADA,
        "LIMIAR_RASGUEADO": LIMIAR_RASGUEADO,
    }
""",
)

# 4. esconder_marcador passa a incluir as abafadas, e helpers novos
troca(
    '''def esconder_marcador(produto: dict) -> dict:
    """Cópia do produto só com o que o alinhador pode ver.

    Por tela, guarda ``id``, as exibições (só ``t0`` e ``t1``) e as colunas únicas da tela
    (coluna -> lista de pares ``[corda, casa]``, ordenados). Descarta tudo o mais, inclusive
    ``t_ini``, ``passagens``, ``tempo``, ``observadores``, ``passagem`` e ``exibicao`` das notas.

    Args:
        produto: JSON do produto (``tab.esquema``), com ``telas`` e ``notas``.

    Returns:
        ``{"telas": [{"id", "exibicoes": [{"t0", "t1"}], "colunas": {coluna: [[corda, casa]]}}]}``.
    """
    colunas_por_tela: dict[int, dict[int, set[tuple[int, int]]]] = {}
''',
    '''def colunas_abafadas(produto: dict) -> set[tuple[int, int]]:
    """Colunas abafadas (rasgueado): pilhas de X sem nota, como ``(tela, coluna)``.

    Uma coluna é abafada se tem ao menos ``MIN_CORDAS_ABAFADA`` ``nao_notas`` de classe
    ``tecnica`` em cordas distintas, nenhuma ``nota`` na mesma tela e coluna, e ao menos
    ``MIN_QUINZE_ABAFADA`` desses glifos com top-1 ``TOP1_ABAFADA`` no classificador. A regra
    foi medida em ``data/saida/audio/a4/rasgueado/medicao.txt``.

    Args:
        produto: JSON do produto (``tab.esquema``), com ``notas`` e ``nao_notas``.

    Returns:
        Conjunto de pares ``(tela, coluna)`` abafados; vazio se não houver.
    """
    notas_pos = {(int(n["tela"]), int(n["coluna"])) for n in produto.get("notas", [])}
    grupos: dict[tuple[int, int], list[dict]] = {}
    for nao_nota in produto.get("nao_notas", []):
        if nao_nota.get("classe") != "tecnica":
            continue
        chave = (int(nao_nota["tela"]), int(nao_nota["coluna"]))
        grupos.setdefault(chave, []).append(nao_nota)
    abafadas: set[tuple[int, int]] = set()
    for chave, glifos in grupos.items():
        if chave in notas_pos:
            continue
        cordas = {int(g["corda"]) for g in glifos}
        quinze = sum(1 for g in glifos if _top1(g) == TOP1_ABAFADA)
        if len(cordas) >= MIN_CORDAS_ABAFADA and quinze >= MIN_QUINZE_ABAFADA:
            abafadas.add(chave)
    return abafadas


def _top1(nao_nota: dict) -> str | None:
    """Top-1 do classificador de glifo de um ``nao_notas``.

    Args:
        nao_nota: registro de ``nao_notas`` do produto.

    Returns:
        Rótulo de maior confiança, ou ``None`` se o registro não trouxer ``simbolo_cru``.
    """
    simbolo = nao_nota.get("simbolo_cru") or {}
    top3 = simbolo.get("top3") or [[None]]
    return top3[0][0]


def _cos_abafada(fluxo_picos: np.ndarray) -> np.ndarray:
    """Cosseno de uma coluna abafada contra cada pico da exibição.

    Só pico com fluxo maior ou igual à mediana do fluxo dos picos da exibição vale
    ``COS_ABAFADA``. Os demais valem ``-inf``, o que impede o casamento: a coluna fica sem ataque.

    Args:
        fluxo_picos: fluxo espectral de cada candidato da exibição (não vazio).

    Returns:
        Vetor ``[candidatos]`` com ``COS_ABAFADA`` ou ``-inf``.
    """
    forte = fluxo_picos >= float(np.median(fluxo_picos))
    return np.where(forte, COS_ABAFADA, -np.inf)


def e_rasgueado(n_abafadas: int, n_colunas: int) -> bool:
    """Se a exibição é um rasgueado: fração de colunas abafadas em ``LIMIAR_RASGUEADO`` ou mais.

    Args:
        n_abafadas: colunas abafadas na sequência da exibição.
        n_colunas: total de colunas da sequência da exibição.

    Returns:
        ``True`` se ``n_abafadas / n_colunas >= LIMIAR_RASGUEADO``; ``False`` sem colunas.
    """
    if n_colunas <= 0:
        return False
    return n_abafadas / n_colunas >= LIMIAR_RASGUEADO


def esconder_marcador(produto: dict) -> dict:
    """Cópia do produto só com o que o alinhador pode ver.

    Por tela, guarda ``id``, as exibições (só ``t0`` e ``t1``), as colunas únicas da tela
    (coluna -> lista de pares ``[corda, casa]``, ordenados) e as colunas abafadas (``abafadas``,
    lista de colunas). Descarta tudo o mais, inclusive ``t_ini``, ``passagens``, ``tempo``,
    ``observadores``, ``passagem`` e ``exibicao`` das notas.

    Args:
        produto: JSON do produto (``tab.esquema``), com ``telas`` e ``notas``.

    Returns:
        ``{"telas": [{"id", "exibicoes": [{"t0", "t1"}], "colunas": {coluna: [[corda, casa]]},
        "abafadas": [coluna]}]}``.
    """
    abafadas_por_tela: dict[int, list[int]] = {}
    for tela_ab, coluna_ab in sorted(colunas_abafadas(produto)):
        abafadas_por_tela.setdefault(tela_ab, []).append(coluna_ab)
    colunas_por_tela: dict[int, dict[int, set[tuple[int, int]]]] = {}
''',
)

troca(
    """                "colunas": {
                    coluna: [[c, s] for c, s in sorted(pares)]
                    for coluna, pares in sorted(colunas.items())
                },
            }
""",
    """                "colunas": {
                    coluna: [[c, s] for c, s in sorted(pares)]
                    for coluna, pares in sorted(colunas.items())
                },
                "abafadas": sorted(abafadas_por_tela.get(tela, [])),
            }
""",
)

# 5. _decidir_onsets_v2: abafadas fora do cosseno médio e do mínimo de colunas
troca(
    '''def _decidir_onsets_v2(
    tela: int,
    exibicao: int,
    sequencia: list[tuple[int, list[int]]],
    resumo: dict,
    cos_pk: np.ndarray,
    t_pk: np.ndarray,
    duracao: float,
) -> tuple[dict, list[dict]]:
    """Decisão do método ``onsets`` (v2): trecho, T iterativo e recusas.

    Args:
        tela: id da tela.
        exibicao: índice da exibição.
        sequencia: ``(coluna, [midis])`` da tela, em ordem crescente.
        resumo: resumo da exibição (preenchido aqui).
        cos_pk: cossenos ``[colunas, candidatos]``.
        t_pk: instantes dos candidatos.
        duracao: ``t1 - t0`` da exibição, em segundos.

    Returns:
        ``(resumo, registros)``.
    """
    n_col = len(sequencia)
    t0_periodo = periodo_todos_intervalos(t_pk, duracao, n_col)
    res = alinhar_trecho_iterativo(cos_pk, t_pk, t0_periodo)
    atrib = res["atribuicao"]
    trecho = res["trecho"]
    casados = [c for c in range(n_col) if atrib[c] is not None]
''',
    '''def _decidir_onsets_v2(
    tela: int,
    exibicao: int,
    sequencia: list[tuple[int, list[int]]],
    resumo: dict,
    cos_pk: np.ndarray,
    t_pk: np.ndarray,
    duracao: float,
    abafadas: set[int],
) -> tuple[dict, list[dict]]:
    """Decisão do método ``onsets`` (v2): trecho, T iterativo e recusas.

    Colunas abafadas casam com ``COS_ABAFADA`` e ficam fora do cosseno médio e de
    ``MIN_COLUNAS_CASADAS``, que contam só as colunas com altura.

    Args:
        tela: id da tela.
        exibicao: índice da exibição.
        sequencia: ``(coluna, [midis])`` da tela, em ordem crescente (abafada: ``[]``).
        resumo: resumo da exibição (preenchido aqui).
        cos_pk: cossenos ``[colunas, candidatos]``.
        t_pk: instantes dos candidatos.
        duracao: ``t1 - t0`` da exibição, em segundos.
        abafadas: colunas abafadas da tela.

    Returns:
        ``(resumo, registros)``.
    """
    n_col = len(sequencia)
    t0_periodo = periodo_todos_intervalos(t_pk, duracao, n_col)
    res = alinhar_trecho_iterativo(cos_pk, t_pk, t0_periodo)
    atrib = res["atribuicao"]
    trecho = res["trecho"]
    eh_abafada = [coluna in abafadas for coluna, _ in sequencia]
    casados = [c for c in range(n_col) if atrib[c] is not None and not eh_abafada[c]]
    casados_abafadas = [
        c for c in range(n_col) if atrib[c] is not None and eh_abafada[c]
    ]
''',
)

troca(
    """            "n_casadas": len(casados),
            "trecho_colunas": (""",
    """            "n_casadas": len(casados),
            "n_abafadas_casadas": len(casados_abafadas),
            "trecho_colunas": (""",
)

# 6. _alinhar_exibicao: abafadas recebem o cosseno fixo; repassa ao v2
troca(
    '''    t_amostra0: float,
    metodo: str,
) -> tuple[dict, list[dict]]:
    """Alinha as colunas de uma exibição ao áudio da janela ``[t0 - m, t1 + m]``.
''',
    '''    t_amostra0: float,
    metodo: str,
    abafadas: set[int],
) -> tuple[dict, list[dict]]:
    """Alinha as colunas de uma exibição ao áudio da janela ``[t0 - m, t1 + m]``.
''',
)
troca(
    """        metodo: ``"onsets"`` ou ``"dtw"``.

    Returns:
        ``(resumo_da_exibicao, registros_por_coluna)``.""",
    """        metodo: ``"onsets"`` ou ``"dtw"``.
        abafadas: colunas abafadas da tela (vazio fora do método ``onsets``).

    Returns:
        ``(resumo_da_exibicao, registros_por_coluna)``.""",
)
troca(
    """    cos_pk = moldes @ p_pk.T
    if metodo == "onsets":
        return _decidir_onsets_v2(
            tela, exibicao, sequencia, resumo, cos_pk, t_pk, t1 - t0
        )
""",
    """    cos_pk = moldes @ p_pk.T
    linhas_abafadas = [c for c, (coluna, _) in enumerate(sequencia) if coluna in abafadas]
    if linhas_abafadas:
        cos_pk[linhas_abafadas] = _cos_abafada(f_pk)
    if metodo == "onsets":
        return _decidir_onsets_v2(
            tela, exibicao, sequencia, resumo, cos_pk, t_pk, t1 - t0, abafadas
        )
""",
)

# 7. alinhar(): sequência com abafadas, flags e tipo por coluna
troca(
    """    for tela in oculto["telas"]:
        sequencia = [
            (int(coluna), [midi_da_nota(c, s, transposicao) for c, s in pares])
            for coluna, pares in sorted(tela["colunas"].items())
        ]
        for idx, ex in enumerate(tela["exibicoes"]):
            resumo, regs = _alinhar_exibicao(
                int(tela["id"]),
                idx,
                float(ex["t0"]),
                float(ex["t1"]),
                sequencia,
                amostras,
                taxa,
                t_amostra0,
                metodo,
            )
            exibicoes.append(resumo)
            colunas.extend(regs)
""",
    """    for tela in oculto["telas"]:
        abafadas = set(tela.get("abafadas", [])) if metodo == "onsets" else set()
        sequencia = [
            (
                int(coluna),
                [midi_da_nota(c, s, transposicao) for c, s in tela["colunas"].get(coluna, [])],
            )
            for coluna in sorted(set(tela["colunas"]) | abafadas)
        ]
        n_ab = sum(1 for coluna, _ in sequencia if coluna in abafadas)
        for idx, ex in enumerate(tela["exibicoes"]):
            resumo, regs = _alinhar_exibicao(
                int(tela["id"]),
                idx,
                float(ex["t0"]),
                float(ex["t1"]),
                sequencia,
                amostras,
                taxa,
                t_amostra0,
                metodo,
                abafadas,
            )
            resumo.setdefault("n_abafadas_casadas", 0)
            resumo["rasgueado"] = e_rasgueado(n_ab, len(sequencia))
            for reg in regs:
                reg["tipo"] = "abafada" if reg["coluna"] in abafadas else "nota"
            exibicoes.append(resumo)
            colunas.extend(regs)
""",
)

# 8. CLI: conta também as abafadas afirmadas
troca(
    """    afirmadas = sum(1 for c in saida["colunas"] if c["t_audio"] is not None)
    print(
        f"metodo={args.metodo} exibicoes={len(saida['exibicoes'])} "
        f"colunas={len(saida['colunas'])} afirmadas={afirmadas} "
        f"recusadas={len(saida['colunas']) - afirmadas}"
    )""",
    """    afirmadas = sum(1 for c in saida["colunas"] if c["t_audio"] is not None)
    abafadas_afirmadas = sum(
        1
        for c in saida["colunas"]
        if c["tipo"] == "abafada" and c["t_audio"] is not None
    )
    print(
        f"metodo={args.metodo} exibicoes={len(saida['exibicoes'])} "
        f"colunas={len(saida['colunas'])} afirmadas={afirmadas} "
        f"recusadas={len(saida['colunas']) - afirmadas} "
        f"abafadas_afirmadas={abafadas_afirmadas}"
    )""",
)

ARQ.write_text(s, encoding="utf-8")
print("ok", len(s))
