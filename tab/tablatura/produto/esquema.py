"""Esquema do JSON v1 (``chorinho/video@1``): o que é um arquivo bem formado.

O JSON é o produto. Este módulo diz o que um JSON v1 precisa ter e devolve a lista de
erros. Não importa numpy, OpenCV nem o motor: qualquer leitor do arquivo (o MusicXML, a
folha de conferência, uma planilha) usa esta mesma definição.

As regras seguem o que ``tab.video.transcrever_video`` emite hoje, e não o rascunho do
plano: uma entrada por passagem e exibição (decisão D2), ``t_ini`` por nota e
``simbolo_cru`` por não-nota. ``afinacao`` e ``casa_validada`` do plano ainda não são
emitidos, então não são exigidos.
"""

from __future__ import annotations

ESQUEMA = "chorinho/video@1"

#: Modos de tela que ``tab.telas`` declara.
MODOS = ("paginado", "rolante", "estatico")

#: Imagens limpas que ``tab.video`` sabe produzir.
IMAGENS = ("quadro", "mediana")

#: Observadores de tempo por exibição (``tab.video.OBSERVADORES``).
OBSERVADORES = ("posicao", "cor_acende", "cor")

#: Cordas do violão, contadas de 1 (aguda) a 6 (grave).
CORDAS = range(1, 7)

#: Algarismos que o leitor pode devolver: ``tab.reconhecer.ALGARISMOS`` (0 a 24).
CASAS = range(0, 25)

#: Valores de ``ataque`` (rótulo opcional por nota; plano-rotulo-tablatura, seção 3).
ATAQUES = ("sim", "nao", "nao_sei")

#: Valores de ``ataque_motivo`` (rótulo opcional por nota).
ATAQUE_MOTIVOS = (
    "normal",
    "h",
    "p",
    "mordente",
    "prolongamento",
    "slide_ligado",
    "slide_entrada",
    "x",
    "harmonico",
    "rasgueado",
    "arpejo",
    "sustentada",
    "mordente_simbolo",
    "arco_sem_par",
    "tinta_sem_explicacao",
)

#: Motivos que só existem com ``ataque`` "nao".
MOTIVOS_SEM_ATAQUE = ("h", "p", "mordente", "prolongamento", "slide_ligado")

#: Motivos que só existem com ``ataque`` "sim".
MOTIVOS_COM_ATAQUE = (
    "normal",
    "slide_entrada",
    "x",
    "harmonico",
    "rasgueado",
    "arpejo",
    "sustentada",
    "mordente_simbolo",
)

#: Motivos que só existem com ``ataque`` "nao_sei" (sem par claro ou sem explicação).
MOTIVOS_SEM_PAR = ("arco_sem_par", "tinta_sem_explicacao")

#: Valores de ``nivel_rotulo``: ouro, prata ou recusado.
NIVEIS_ROTULO = ("ouro", "prata", "recusado")

#: Classe de ``nao_notas`` para o arco, que exige ``x_ini``, ``x_fim`` e ``confianca``.
CLASSE_ARCO = "arco"

#: Tolerância para comparar instantes reescritos em JSON (3 casas decimais).
_EPS = 1e-6

_CHAVES_RAIZ = ("video", "gerado_por", "telas", "notas", "nao_notas", "resumo")


def _inteiro(valor: object) -> bool:
    """Inteiro de verdade (``bool`` não conta).

    Args:
        valor: qualquer objeto.

    Returns:
        ``True`` se ``valor`` é ``int`` e não ``bool``.
    """
    return isinstance(valor, int) and not isinstance(valor, bool)


def _numero(valor: object) -> bool:
    """Número real (``bool`` não conta).

    Args:
        valor: qualquer objeto.

    Returns:
        ``True`` se ``valor`` é ``int`` ou ``float`` e não ``bool``.
    """
    return isinstance(valor, int | float) and not isinstance(valor, bool)


def _id_de_tela(valor: object, telas: dict[int, dict]) -> bool:
    """Se ``valor`` é o id inteiro de uma tela conhecida (sem levantar exceção).

    Args:
        valor: o campo ``tela`` de uma nota ou não-nota.
        telas: telas por id.

    Returns:
        ``True`` se ``valor`` é inteiro e existe em ``telas``.
    """
    return _inteiro(valor) and valor in telas


def _tempo(bloco: object, onde: str, por_exibicao: bool) -> list[str]:
    """Checa um bloco ``tempo`` (de tela ou de exibição).

    Args:
        bloco: o dicionário ``tempo``.
        onde: texto para localizar o erro (ex.: ``tela 3 exibicao 1``).
        por_exibicao: se ``True``, medido exige ``observador`` e ``coerencia``.

    Returns:
        Lista de erros do bloco; vazia se ele está bem formado.
    """
    if not isinstance(bloco, dict):
        return [f"{onde}: tempo não é objeto"]
    erros: list[str] = []
    medido = bloco.get("medido")
    if not isinstance(medido, bool):
        return [f"{onde}: tempo.medido não é booleano"]
    if not medido:
        motivo = bloco.get("motivo")
        if not isinstance(motivo, str) or not motivo.strip():
            erros.append(f"{onde}: medido false sem motivo")
    elif por_exibicao:
        if bloco.get("observador") not in OBSERVADORES:
            erros.append(f"{onde}: observador {bloco.get('observador')!r} desconhecido")
        if not _numero(bloco.get("coerencia")):
            erros.append(f"{onde}: coerencia ausente")
    return erros


def _exibicao(ex: object, onde: str) -> tuple[list[str], bool]:
    """Checa uma exibição (uma aparição da tela na tela do vídeo).

    Args:
        ex: entrada de ``telas[i].exibicoes``.
        onde: texto para localizar o erro.

    Returns:
        ``(erros, medida)``: ``medida`` diz se a exibição tem tempo.
    """
    if not isinstance(ex, dict):
        return [f"{onde}: não é objeto"], False
    erros: list[str] = []
    t0, t1 = ex.get("t0"), ex.get("t1")
    if not (_numero(t0) and _numero(t1) and t0 <= t1):
        erros.append(f"{onde}: t0/t1 inválidos ({t0!r}, {t1!r})")
    erros += _tempo(ex.get("tempo"), onde, por_exibicao=True)
    medida = isinstance(ex.get("tempo"), dict) and ex["tempo"].get("medido") is True
    passagens = ex.get("passagens")
    if not isinstance(passagens, list):
        return [*erros, f"{onde}: passagens não é lista"], medida
    if not medida and passagens:
        erros.append(f"{onde}: sem tempo medido mas com passagens")
    for p, passagem in enumerate(passagens, start=1):
        if not isinstance(passagem, list):
            erros.append(f"{onde} passagem {p}: não é lista")
            continue
        ts: list[float] = []
        for item in passagem:
            if not (
                isinstance(item, dict)
                and _inteiro(item.get("coluna"))
                and item["coluna"] >= 1
                and _numero(item.get("t_ini"))
            ):
                erros.append(f"{onde} passagem {p}: item malformado {item!r}")
                continue
            ts.append(item["t_ini"])
            if (
                _numero(t0)
                and _numero(t1)
                and not t0 - _EPS <= item["t_ini"] <= t1 + _EPS
            ):
                erros.append(
                    f"{onde} passagem {p}: t_ini {item['t_ini']} fora de [{t0}, {t1}]"
                )
        if ts != sorted(ts):
            erros.append(f"{onde} passagem {p}: onsets decrescem")
    return erros, medida


def _telas(telas: list) -> tuple[list[str], dict[int, dict], dict[tuple, float]]:
    """Checa as telas e indexa os onsets por ``(tela, exibicao, passagem, coluna)``.

    Args:
        telas: o bloco ``telas`` do JSON.

    Returns:
        ``(erros, por_id, onsets)``: ``por_id`` leva o id da tela à tela; ``onsets``
        leva a chave de passagem ao ``t_ini`` declarado.
    """
    erros: list[str] = []
    por_id: dict[int, dict] = {}
    onsets: dict[tuple, float] = {}
    for t in telas:
        if not isinstance(t, dict) or not _inteiro(t.get("id")):
            erros.append(f"tela malformada: {t!r:.80}")
            continue
        tid = t["id"]
        onde = f"tela {tid}"
        por_id[tid] = t
        painel = t.get("painel")
        if not (
            isinstance(painel, list)
            and len(painel) == 4
            and all(_inteiro(v) for v in painel)
        ):
            erros.append(f"{onde}: painel deve ser [x0, y0, x1, y1] inteiros")
        if t.get("passo") is not None and not _numero(t.get("passo")):
            erros.append(f"{onde}: passo inválido")
        if t.get("modo") not in MODOS:
            erros.append(f"{onde}: modo {t.get('modo')!r} desconhecido")
        barlines = t.get("barlines_x")
        if not (isinstance(barlines, list) and all(_inteiro(b) for b in barlines)):
            erros.append(f"{onde}: barlines_x deve ser lista de inteiros")
        if "leitura" in t and not isinstance(t["leitura"], str):
            erros.append(f"{onde}: leitura deve ser texto")
        exibicoes = t.get("exibicoes")
        if not isinstance(exibicoes, list):
            erros.append(f"{onde}: exibicoes não é lista")
            continue
        medidas: list[bool] = []
        for e, ex in enumerate(exibicoes):
            erros_ex, medida = _exibicao(ex, f"{onde} exibicao {e}")
            erros += erros_ex
            medidas.append(medida)
            if not isinstance(ex, dict) or not isinstance(ex.get("passagens"), list):
                continue
            for p, passagem in enumerate(ex["passagens"], start=1):
                for item in passagem if isinstance(passagem, list) else []:
                    if isinstance(item, dict) and _inteiro(item.get("coluna")):
                        valor = item.get("t_ini")
                        onsets[(tid, e, p, item["coluna"])] = (
                            valor if _numero(valor) else None
                        )
        erros += _tempo(t.get("tempo"), onde, por_exibicao=False)
        tempo = t.get("tempo")
        if isinstance(tempo, dict) and tempo.get("medido") != any(medidas):
            erros.append(f"{onde}: tempo.medido não bate com as exibições")
    return erros, por_id, onsets


def _coerencia_motivo(motivo: str, ataque: str, onde: str) -> list[str]:
    """Confere se ``ataque_motivo`` combina com ``ataque`` (plano, seção 3).

    Args:
        motivo: um valor de ``ATAQUE_MOTIVOS``.
        ataque: um valor de ``ATAQUES``.
        onde: texto para localizar o erro.

    Returns:
        Lista com um erro se o par é incoerente; vazia se combina.
    """
    if motivo in MOTIVOS_SEM_ATAQUE:
        exigido = "nao"
    elif motivo in MOTIVOS_COM_ATAQUE:
        exigido = "sim"
    else:
        exigido = "nao_sei"
    if ataque == exigido:
        return []
    return [
        f"{onde}: ataque_motivo {motivo!r} exige ataque {exigido!r}, não {ataque!r}"
    ]


def _rotulo(n: dict, onde: str) -> list[str]:
    """Checa os campos opcionais de rótulo de uma nota.

    ``ataque``, ``ataque_motivo`` e ``nivel_rotulo`` são opcionais: nota sem eles é
    válida e nada muda. Quando presentes, valem as regras de coerência do plano.

    Args:
        n: entrada de ``notas`` já com os campos básicos checados.
        onde: texto para localizar o erro.

    Returns:
        Lista de erros do rótulo; vazia se ele está bem formado ou ausente.
    """
    erros: list[str] = []
    ataque = n.get("ataque")
    if "ataque" in n and ataque not in ATAQUES:
        erros.append(f"{onde}: ataque {ataque!r} desconhecido")
    if "ataque_motivo" in n:
        motivo = n["ataque_motivo"]
        if motivo not in ATAQUE_MOTIVOS:
            erros.append(f"{onde}: ataque_motivo {motivo!r} desconhecido")
        elif "ataque" not in n:
            erros.append(f"{onde}: ataque_motivo sem ataque")
        elif ataque in ATAQUES:
            erros += _coerencia_motivo(motivo, ataque, onde)
    if "nivel_rotulo" in n:
        nivel = n["nivel_rotulo"]
        if nivel not in NIVEIS_ROTULO:
            erros.append(f"{onde}: nivel_rotulo {nivel!r} desconhecido")
        elif nivel == "ouro" and ataque == "nao_sei":
            erros.append(f"{onde}: nivel_rotulo 'ouro' com ataque 'nao_sei'")
    return erros


def _nota(n: object, onde: str, telas: dict[int, dict], onsets: dict) -> list[str]:
    """Checa uma nota e a sua consistência com as passagens da tela.

    Args:
        n: entrada de ``notas``.
        onde: texto para localizar o erro.
        telas: telas por id.
        onsets: onsets por ``(tela, exibicao, passagem, coluna)``.

    Returns:
        Lista de erros da nota.
    """
    if not isinstance(n, dict):
        return [f"{onde}: não é objeto"]
    erros: list[str] = []
    campos_inteiros = {
        "tela": (_inteiro, None),
        "passagem": (_inteiro, 1),
        "coluna": (_inteiro, 1),
        "compasso": (_inteiro, 1),
    }
    for campo, (teste, minimo) in campos_inteiros.items():
        valor = n.get(campo)
        if not teste(valor) or (minimo is not None and valor < minimo):
            erros.append(f"{onde}: {campo} inválido ({valor!r})")
    if not _id_de_tela(n.get("tela"), telas):
        erros.append(f"{onde}: tela {n.get('tela')!r} não existe")
    if erros:
        return erros
    if n.get("corda") not in CORDAS:
        erros.append(f"{onde}: corda {n.get('corda')!r} fora de 1 a 6")
    casa = n.get("casa")
    if not _inteiro(casa) or casa not in CASAS:
        erros.append(f"{onde}: casa {casa!r} fora de 0 a 24")
    if n.get("tecnica") is not None and not isinstance(n.get("tecnica"), str):
        erros.append(f"{onde}: tecnica deve ser nula ou texto")
    erros += _rotulo(n, onde)
    confianca = n.get("confianca")
    if not (_numero(confianca) and 0 <= confianca <= 1):
        erros.append(f"{onde}: confianca fora de [0, 1]")
    for campo in ("x_quadro", "x_centro_quadro"):
        if not _numero(n.get(campo)):
            erros.append(f"{onde}: {campo} ausente")
    t_ini = n.get("t_ini")
    exibicao = n.get("exibicao")
    if t_ini is None:
        if exibicao is not None:
            erros.append(f"{onde}: exibicao sem t_ini")
        return erros
    if not _numero(t_ini) or not _inteiro(exibicao):
        return [*erros, f"{onde}: t_ini sem exibicao inteira"]
    chave = (n.get("tela"), exibicao, n.get("passagem"), n.get("coluna"))
    if chave not in onsets:
        erros.append(f"{onde}: nenhuma passagem da tela tem essa coluna")
    elif not _numero(onsets[chave]) or abs(onsets[chave] - t_ini) > _EPS:
        erros.append(f"{onde}: t_ini {t_ini} difere do da passagem ({onsets[chave]})")
    return erros


def _notas(notas: list, telas: dict[int, dict], onsets: dict) -> list[str]:
    """Checa o bloco ``notas``, inclusive duplicatas.

    Args:
        notas: o bloco ``notas``.
        telas: telas por id.
        onsets: onsets por ``(tela, exibicao, passagem, coluna)``.

    Returns:
        Lista de erros do bloco.
    """
    erros: list[str] = []
    vistas: set[tuple] = set()
    for i, n in enumerate(notas):
        erros_nota = _nota(n, f"nota {i}", telas, onsets)
        erros += erros_nota
        if isinstance(n, dict) and not erros_nota:
            chave = (
                n.get("tela"),
                n.get("exibicao"),
                n.get("passagem"),
                n.get("coluna"),
                n.get("corda"),
            )
            if chave in vistas:
                erros.append(f"nota {i}: repetida na mesma passagem {chave}")
            vistas.add(chave)
    return erros


def _arco(m: dict, onde: str) -> list[str]:
    """Checa a classe ``arco`` de ``nao_notas``: corda, ``x_ini``, ``x_fim``, confiança.

    Args:
        m: entrada de ``nao_notas`` com ``classe`` igual a ``CLASSE_ARCO``.
        onde: texto para localizar o erro.

    Returns:
        Lista de erros do arco; vazia se ele está bem formado.
    """
    erros: list[str] = []
    corda = m.get("corda")
    if not (_inteiro(corda) and corda in CORDAS):
        erros.append(f"{onde}: arco com corda {corda!r} fora de inteiro 1 a 6")
    x_ini, x_fim = m.get("x_ini"), m.get("x_fim")
    if not (_numero(x_ini) and _numero(x_fim)):
        erros.append(f"{onde}: arco sem x_ini/x_fim numéricos")
    elif x_ini > x_fim:
        erros.append(f"{onde}: arco com x_ini {x_ini} maior que x_fim {x_fim}")
    confianca = m.get("confianca")
    if _numero(confianca) and not 0 <= confianca <= 1:
        erros.append(f"{onde}: arco com confianca {confianca} fora de [0, 1]")
    return erros


def _nao_nota(m: object, onde: str, telas: dict[int, dict]) -> list[str]:
    """Checa uma não-nota (símbolo, harmônico, técnica): nada se descarta.

    Args:
        m: entrada de ``nao_notas``.
        onde: texto para localizar o erro.
        telas: telas por id.

    Returns:
        Lista de erros da entrada.
    """
    if not isinstance(m, dict):
        return [f"{onde}: não é objeto"]
    erros: list[str] = []
    if not _id_de_tela(m.get("tela"), telas):
        erros.append(f"{onde}: tela {m.get('tela')!r} não existe")
    if not _inteiro(m.get("coluna")) or m["coluna"] < 1:
        erros.append(f"{onde}: coluna inválida")
    if m.get("corda") not in CORDAS:
        erros.append(f"{onde}: corda {m.get('corda')!r} fora de 1 a 6")
    for campo in ("x_quadro", "x_centro_quadro", "confianca"):
        if not _numero(m.get(campo)):
            erros.append(f"{onde}: {campo} ausente")
    if not isinstance(m.get("classe"), str) or not m["classe"]:
        erros.append(f"{onde}: classe ausente")
    if m.get("classe") == CLASSE_ARCO:
        erros += _arco(m, onde)
    if "simbolo_cru" in m and not isinstance(m["simbolo_cru"], dict | str):
        erros.append(f"{onde}: simbolo_cru deve ser objeto ou texto")
    if "casa_recuperada" in m and not isinstance(m["casa_recuperada"], str):
        erros.append(f"{onde}: casa_recuperada deve ser texto")
    return erros


def _resumo(dados: dict, telas: list, notas: list, nao_notas: list) -> list[str]:
    """Confere o ``resumo`` contra o que o bloco realmente contém.

    Args:
        dados: o JSON inteiro (para ler o ``resumo``).
        telas: bloco ``telas``.
        notas: bloco ``notas``.
        nao_notas: bloco ``nao_notas``.

    Returns:
        Lista de erros; vazia se o resumo bate com os blocos.
    """
    resumo = dados.get("resumo")
    if not isinstance(resumo, dict):
        return ["resumo ausente"]
    instantes = {n.get("t_ini") for n in notas if n.get("t_ini") is not None}
    esperado = {
        "telas": len(telas),
        "exibicoes": sum(
            len(t.get("exibicoes", [])) for t in telas if isinstance(t, dict)
        ),
        "notas": len(notas),
        "notas_com_tempo": sum(1 for n in notas if n.get("t_ini") is not None),
        "instantes_distintos": len(instantes),
        "telas_sem_tempo": sum(
            1
            for t in telas
            if isinstance(t, dict)
            and isinstance(t.get("tempo"), dict)
            and t["tempo"].get("medido") is False
        ),
        "nao_notas": len(nao_notas),
    }
    return [
        f"resumo.{k} = {resumo.get(k)!r}, mas o JSON tem {v}"
        for k, v in esperado.items()
        if resumo.get(k) != v
    ]


def validar(d: dict) -> list[str]:
    """Confere um JSON ``chorinho/video@1`` e devolve a lista de erros.

    Não lança exceção para entrada malformada: qualquer forma errada vira uma mensagem.
    A forma é a mesma em todos os caminhos (com posição, com cor e sem marcador); o que
    muda é o conteúdo de ``t_ini`` e ``tempo``.

    Args:
        d: o JSON, já carregado como dicionário.

    Returns:
        Lista de textos, um por erro. Lista vazia significa que o arquivo é válido.
    """
    if not isinstance(d, dict):
        return ["raiz não é um objeto"]
    erros: list[str] = []
    if d.get("esquema") != ESQUEMA:
        erros.append(f"esquema {d.get('esquema')!r}, esperado {ESQUEMA!r}")
    for chave in _CHAVES_RAIZ:
        if chave not in d:
            erros.append(f"falta o bloco '{chave}'")
    if erros:
        return erros

    video = d["video"]
    if not isinstance(video, dict) or not isinstance(video.get("arquivo"), str):
        erros.append("video.arquivo ausente")
    elif not _numero(video.get("duracao_s")):
        erros.append("video.duracao_s ausente")

    gerado = d["gerado_por"]
    if not isinstance(gerado, dict):
        erros.append("gerado_por não é objeto")
    else:
        if gerado.get("imagem") not in IMAGENS:
            erros.append(f"gerado_por.imagem {gerado.get('imagem')!r} desconhecida")
        for campo in ("modelo", "commit", "em"):
            if not isinstance(gerado.get(campo), str):
                erros.append(f"gerado_por.{campo} ausente")

    telas, notas, nao_notas = d["telas"], d["notas"], d["nao_notas"]
    if not (isinstance(telas, list) and isinstance(notas, list)):
        return [*erros, "telas e notas devem ser listas"]
    if not isinstance(nao_notas, list):
        return [*erros, "nao_notas deve ser lista"]

    erros_telas, por_id, onsets = _telas(telas)
    erros += erros_telas
    erros += _notas(notas, por_id, onsets)
    for i, m in enumerate(nao_notas):
        erros += _nao_nota(m, f"nao_nota {i}", por_id)
    erros += _resumo(d, telas, notas, nao_notas)
    return erros
