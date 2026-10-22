"""Arquivo irmão do produto: o tempo do som por coluna (decisão 2003, ``chorinho/audio@1``).

O produto ``chorinho/video@1`` diz o que a tablatura é; este arquivo diz quando cada coluna
soa, segundo o alinhador v2 (``tab.audio_alinhar``). Há uma entrada em ``colunas`` para cada
(tela, exibição, coluna) que o alinhamento tem. As colunas recusadas entram com ``t_audio``
nulo e ``motivo`` preenchido: nada é descartado.

O tempo é instante na linha do tempo do vídeo (a mesma do ``t_ini``), na convenção
``t_amostra0`` que o alinhamento já traz em ``video``. Se o alinhamento não trouxer
``t_amostra0``, o campo fica nulo e isso é declarado, não inventado.

Uso::

    python -m tab.audio_produto --produto P --alinhado A --saida S [--commit H]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

from tab.comum.caminhos import GABARITO_AUDIO, RAIZ

#: Esquema do arquivo irmão.
ESQUEMA = "chorinho/audio@1"

#: Método do alinhador que gerou o tempo (o v2 de ``tab.audio_alinhar``, método ``onsets``).
METODO = "onsets_v2"

#: O alinhador v2 só vê a primeira passagem de cada exibição.
PASSAGENS = "so_primeira"

#: Nível de aferição: a escuta A/B (folha 3, rodada 2008) conferiu o tempo a ~100 ms.
NIVEL_AFERICAO = "ms"

#: Resolução da escuta, em ms: 200 e 100 ms separados, 50 ms não (rodada 2008).
RESOLUCAO_ESCUTA_MS = 100

#: Cosseno médio a partir do qual uma exibição recusada vira alarme de leitura (rodada 2009:
#: as notas que casam, casam bem, mas casam poucas; aponta colunas faltando ou erradas).
LIMIAR_ALARME_COS = 0.7

#: Chaves obrigatórias no topo do arquivo.
CHAVES_TOPO = (
    "esquema",
    "produto",
    "produto_sha256",
    "video",
    "gerado_por",
    "exibicoes",
    "colunas",
    "afericao",
)
CHAVES_VIDEO = ("arquivo", "t_amostra0")
CHAVES_GERADO_POR = (
    "metodo",
    "alinhamento",
    "alinhamento_sha256",
    "parametros",
    "transposicao",
    "commit",
    "passagens",
)
CHAVES_EXIBICAO = (
    "tela",
    "exibicao",
    "trecho_colunas",
    "T_s",
    "recusada",
    "motivo",
    "cos_medio",
    "n_casadas",
    "n_abafadas_casadas",
    "rasgueado",
    "fora_da_pagina",
    "alarme_leitura",
)
CHAVES_COLUNA = (
    "tela",
    "exibicao",
    "coluna",
    "t_audio",
    "confianca",
    "cos",
    "motivo",
    "tipo",
)
CHAVES_AFERICAO = ("gabarito", "nivel", "resolucao_escuta_ms")


def sha256_arquivo(caminho: str | Path) -> str:
    """Sha256 dos bytes de um arquivo.

    Args:
        caminho: arquivo a ler.

    Returns:
        Sha256 em hexadecimal, em minúsculas.
    """
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def _ler_json(caminho: str | Path) -> tuple[dict, str]:
    """Lê um JSON e devolve o conteúdo com o sha256 dos bytes lidos.

    Args:
        caminho: arquivo JSON.

    Returns:
        ``(dados, sha256)``: o objeto decodificado e o sha256 dos bytes do mesmo arquivo.
    """
    bruto = Path(caminho).read_bytes()
    return json.loads(bruto.decode("utf-8")), hashlib.sha256(bruto).hexdigest()


def gabarito_existente() -> list[str]:
    """Folhas de escuta que existem hoje, como caminhos relativos à raiz do projeto.

    Returns:
        Lista ordenada de ``data/gold/audio/folha*.json`` que existem (pode ser vazia).
    """
    return sorted(str(p.relative_to(RAIZ)) for p in GABARITO_AUDIO.glob("folha*.json"))


def _commit_do_git() -> str:
    """Hash do HEAD do git, se houver git e repositório; senão ``desconhecido``.

    Não chama o git quando ele não existe no ambiente (o container não tem git).

    Returns:
        O hash do commit, ou ``"desconhecido"``.
    """
    if shutil.which("git") is None:
        return "desconhecido"
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return "desconhecido"
    return proc.stdout.strip()


def _chave_coluna(registro: dict) -> tuple[int, int, int]:
    """Chave de ordem estável de uma linha de coluna.

    Args:
        registro: linha com ``tela``, ``exibicao`` e ``coluna``.

    Returns:
        ``(tela, exibicao, coluna)`` como inteiros.
    """
    return (int(registro["tela"]), int(registro["exibicao"]), int(registro["coluna"]))


def trecho_fora_da_pagina(
    janela: list[float] | None, trecho_tempo: list[float] | None, margem: float
) -> bool:
    """Trecho escolhido cai inteiro na margem da janela, fora da página (rodada 2014).

    O alinhador procura a página numa janela ``[t0 - margem, t1 + margem]``. Em 8 de 42
    alarmes da rodada 2014 o trecho escolhido estava todo na margem: casou a página vizinha,
    e o alarme era falso. Um trecho que atravessa a borda da página não conta como fora.

    Args:
        janela: ``[t0 - margem, t1 + margem]`` da exibição, ou ``None``.
        trecho_tempo: ``[início, fim]`` do trecho escolhido, ou ``None``.
        margem: a margem da janela, em segundos (``MARGEM_JANELA_S``).

    Returns:
        ``True`` se o trecho termina antes de ``t0`` ou começa depois de ``t1``; ``False`` se
        algum dos dois é ``None`` ou se o trecho está (ao menos em parte) na página.
    """
    if janela is None or trecho_tempo is None:
        return False
    inicio, fim = trecho_tempo
    return fim < janela[0] + margem or inicio > janela[1] - margem


def _linhas_exibicoes(alinhado: dict) -> list[dict]:
    """Uma linha de ``exibicoes[]`` por exibição do alinhamento, em ordem estável.

    Alinhamentos anteriores à v2.1 não trazem ``rasgueado`` nem ``n_abafadas_casadas``: nesses
    casos vale ``False`` e ``0``, que é o que a v2 fazia. Alinhamentos sem ``janela`` ou
    ``trecho_tempo`` dão ``fora_da_pagina`` ``False``.

    Args:
        alinhado: saída do ``tab.audio_alinhar``.

    Returns:
        Lista com ``tela``, ``exibicao``, ``trecho_colunas``, ``T_s``, ``recusada``,
        ``motivo``, ``cos_medio``, ``n_casadas``, ``n_abafadas_casadas``, ``rasgueado``,
        ``fora_da_pagina`` e ``alarme_leitura``, ordenada por (tela, exibicao).
    """
    margem = float(alinhado["parametros"].get("MARGEM_JANELA_S", 0.5))
    linhas = []
    for e in alinhado["exibicoes"]:
        recusada = bool(e["recusada_exibicao"])
        cos_medio = e.get("cos_medio")
        rasgueado = bool(e.get("rasgueado", False))
        fora = trecho_fora_da_pagina(e.get("janela"), e.get("trecho_tempo"), margem)
        linhas.append(
            {
                "tela": int(e["tela"]),
                "exibicao": int(e["exibicao"]),
                "trecho_colunas": e.get("trecho_colunas"),
                "T_s": e.get("T_usado_s"),
                "recusada": recusada,
                "motivo": e.get("motivo_exibicao"),
                "cos_medio": cos_medio,
                "n_casadas": e.get("n_casadas"),
                "n_abafadas_casadas": int(e.get("n_abafadas_casadas", 0)),
                "rasgueado": rasgueado,
                "fora_da_pagina": fora,
                "alarme_leitura": alarme_leitura(recusada, cos_medio, rasgueado, fora),
            }
        )
    return sorted(linhas, key=lambda e: (e["tela"], e["exibicao"]))


def alarme_leitura(
    recusada: bool,
    cos_medio: float | None,
    rasgueado: bool = False,
    fora_da_pagina: bool = False,
) -> bool:
    """Exibição recusada em que as colunas casadas casam bem: sinal de leitura com falhas.

    Medido na rodada 2009 (shin izumi, corda 1 perdida) e na 2010 (guitarous, cordas
    deslocadas): a recusa vem de poucas colunas casadas, com cosseno alto. Um rasgueado
    (``rasgueado``) não dispara: a recusa vem das colunas abafadas, que não têm altura e
    que o alinhador não casa como nota, e a leitura está certa. Na rodada 2014, um trecho
    todo fora da página (``fora_da_pagina``) também não dispara: casou a página vizinha,
    e o cosseno alto é de outra página.

    Args:
        recusada: a exibição foi recusada pelo alinhador.
        cos_medio: cosseno médio das colunas casadas (``None`` se nenhuma casou).
        rasgueado: a exibição é um rasgueado (fração de colunas abafadas no limite).
        fora_da_pagina: o trecho escolhido está inteiro na margem da janela (rodada 2014).

    Returns:
        ``True`` se recusada, não rasgueado, não fora da página e
        ``cos_medio >= LIMIAR_ALARME_COS``.
    """
    return bool(
        recusada
        and not rasgueado
        and not fora_da_pagina
        and cos_medio is not None
        and cos_medio >= LIMIAR_ALARME_COS
    )


def _linhas_colunas(alinhado: dict) -> list[dict]:
    """Uma linha de ``colunas[]`` por (tela, exibição, coluna) do alinhamento.

    Inclui as recusadas, com ``t_audio`` nulo e ``motivo``. ``tipo`` é ``abafada`` (ataque sem
    altura, rasgueado) ou ``nota``; alinhamento anterior à v2.1 traz ``nota`` por padrão.

    Args:
        alinhado: saída do ``tab.audio_alinhar``.

    Returns:
        Lista com ``tela``, ``exibicao``, ``coluna``, ``t_audio``, ``confianca``, ``cos``,
        ``motivo`` e ``tipo``, ordenada por (tela, exibicao, coluna).
    """
    linhas = [
        {
            "tela": int(c["tela"]),
            "exibicao": int(c["exibicao"]),
            "coluna": int(c["coluna"]),
            "t_audio": c["t_audio"],
            "confianca": c["confianca"],
            "cos": c.get("cos"),
            "motivo": c["motivo"],
            "tipo": c.get("tipo", "nota"),
        }
        for c in alinhado["colunas"]
    ]
    return sorted(linhas, key=_chave_coluna)


def _montar(
    produto_caminho: str,
    produto_sha256: str,
    alinhado: dict,
    alinhado_caminho: str,
    alinhado_sha256: str,
    commit: str,
    gabarito: list[str],
) -> dict:
    """Monta o arquivo ``chorinho/audio@1`` a partir dos dados já lidos.

    Args:
        produto_caminho: caminho do produto, como foi passado.
        produto_sha256: sha256 dos bytes do produto.
        alinhado: saída do ``tab.audio_alinhar``.
        alinhado_caminho: caminho do alinhamento, como foi passado.
        alinhado_sha256: sha256 dos bytes do alinhamento.
        commit: hash do commit do código que gerou o arquivo.
        gabarito: folhas de escuta usadas na aferição.

    Returns:
        Dicionário no formato ``chorinho/audio@1``, pronto para ``validar``.
    """
    video = alinhado["video"]
    return {
        "esquema": ESQUEMA,
        "produto": produto_caminho,
        "produto_sha256": produto_sha256,
        "video": {
            "arquivo": video["arquivo"],
            "t_amostra0": video.get("t_amostra0"),
        },
        "gerado_por": {
            "metodo": METODO,
            "alinhamento": alinhado_caminho,
            "alinhamento_sha256": alinhado_sha256,
            "parametros": dict(alinhado["parametros"]),
            "transposicao": alinhado["transposicao"],
            "commit": commit,
            "passagens": PASSAGENS,
        },
        "exibicoes": _linhas_exibicoes(alinhado),
        "colunas": _linhas_colunas(alinhado),
        "afericao": {
            "gabarito": list(gabarito),
            "nivel": NIVEL_AFERICAO,
            "resolucao_escuta_ms": RESOLUCAO_ESCUTA_MS,
        },
    }


def montar(
    produto_caminho: str,
    alinhado_caminho: str,
    *,
    commit: str = "desconhecido",
    gabarito: list[str] | None = None,
) -> dict:
    """Lê o produto e o alinhamento do disco e monta o ``chorinho/audio@1``.

    Args:
        produto_caminho: JSON do ``chorinho/video@1``.
        alinhado_caminho: JSON do alinhamento do ``tab.audio_alinhar``.
        commit: hash do commit do código (``desconhecido`` se não souber).
        gabarito: folhas de escuta; se ``None``, usa ``gabarito_existente()``.

    Returns:
        Dicionário no formato ``chorinho/audio@1``. Não valida: use ``validar``.
    """
    produto_sha = sha256_arquivo(produto_caminho)
    alinhado, alinhado_sha = _ler_json(alinhado_caminho)
    if gabarito is None:
        gabarito = gabarito_existente()
    return _montar(
        produto_caminho,
        produto_sha,
        alinhado,
        alinhado_caminho,
        alinhado_sha,
        commit,
        gabarito,
    )


def confere_produto(d: dict, caminho_produto: str | Path) -> bool:
    """Diz se o produto no disco é o mesmo que o arquivo irmão amarrou.

    Args:
        d: arquivo ``chorinho/audio@1``.
        caminho_produto: caminho do produto a conferir.

    Returns:
        ``True`` se o sha256 dos bytes do produto bate com ``produto_sha256``; ``False`` se
        bate diferente ou se o produto não existe.
    """
    if not Path(caminho_produto).is_file():
        return False
    return sha256_arquivo(caminho_produto) == d.get("produto_sha256")


def _numero(valor: object) -> bool:
    """Diz se o valor é um número finito (booleano não conta).

    Args:
        valor: valor a testar.

    Returns:
        ``True`` para int ou float finito, exceto ``bool``.
    """
    return (
        isinstance(valor, int | float)
        and not isinstance(valor, bool)
        and math.isfinite(valor)
    )


def _faltando(obj: object, chaves: tuple[str, ...], onde: str) -> list[str]:
    """Erros de chaves obrigatórias ausentes em um objeto.

    Args:
        obj: objeto a conferir.
        chaves: chaves obrigatórias.
        onde: rótulo do objeto, para a mensagem.

    Returns:
        Lista de mensagens (vazia se não falta nada).
    """
    if not isinstance(obj, dict):
        return [f"{onde}: não é objeto"]
    return [f"{onde}: chave ausente: {c}" for c in chaves if c not in obj]


def _validar_colunas(colunas: list, erros: list[str]) -> set[tuple[int, int, int]]:
    """Regras de cada linha de ``colunas[]`` que não dependem do produto.

    Args:
        colunas: a lista ``colunas``.
        erros: lista onde os erros são acumulados.

    Returns:
        Chaves (tela, exibicao, coluna) das linhas com todas as chaves obrigatórias.
    """
    vistas: set[tuple[int, int, int]] = set()
    for i, c in enumerate(colunas):
        falta = _faltando(c, CHAVES_COLUNA, f"colunas[{i}]")
        if falta:
            erros.extend(falta)
            continue
        t = c["t_audio"]
        motivo = c["motivo"]
        onde = f"colunas[{i}] (tela {c['tela']}, exibição {c['exibicao']}, coluna {c['coluna']})"
        if t is not None and not _numero(t):
            erros.append(f"{onde}: t_audio não é número nem null")
        if t is None and motivo is None:
            erros.append(f"{onde}: t_audio null sem motivo")
        if t is not None and motivo is not None:
            erros.append(f"{onde}: t_audio afirmado com motivo {motivo!r}")
        conf = c["confianca"]
        if conf is not None and not (_numero(conf) and 0 <= conf <= 1):
            erros.append(f"{onde}: confianca fora de [0, 1]: {conf!r}")
        chave = _chave_coluna(c)
        if chave in vistas:
            erros.append(f"{onde}: entrada repetida")
        vistas.add(chave)
    return vistas


def _validar_monotonia(colunas: list, erros: list[str]) -> None:
    """Tempos não-nulos crescentes com a coluna, dentro de cada (tela, exibição).

    Args:
        colunas: a lista ``colunas`` (já com as chaves obrigatórias).
        erros: lista onde os erros são acumulados.
    """
    grupos: dict[tuple[int, int], list[tuple[int, float]]] = {}
    for c in colunas:
        if not all(k in c for k in CHAVES_COLUNA) or not _numero(c["t_audio"]):
            continue
        grupos.setdefault((c["tela"], c["exibicao"]), []).append(
            (c["coluna"], c["t_audio"])
        )
    for (tela, exibicao), pares in sorted(grupos.items()):
        pares.sort()
        for (c1, t1), (c2, t2) in pairwise(pares):
            if t2 <= t1:
                erros.append(
                    f"tela {tela}, exibição {exibicao}: tempo não crescente entre "
                    f"coluna {c1} ({t1}) e coluna {c2} ({t2})"
                )


def _validar_contra_produto(
    d: dict, produto: dict, chaves_colunas: set[tuple[int, int, int]], erros: list[str]
) -> None:
    """Regras que precisam do produto: existência, janela de tempo e cobertura das notas.

    Args:
        d: arquivo ``chorinho/audio@1``.
        produto: JSON do ``chorinho/video@1``.
        chaves_colunas: chaves (tela, exibicao, coluna) já presentes em ``colunas``.
        erros: lista onde os erros são acumulados.
    """
    telas = {int(t["id"]): t for t in produto["telas"]}
    notas_por_tela: dict[int, set[int]] = {}
    for n in produto.get("notas", []):
        notas_por_tela.setdefault(int(n["tela"]), set()).add(int(n["coluna"]))

    cobertas: set[tuple[int, int]] = set()
    for e in d.get("exibicoes", []):
        if not all(k in e for k in CHAVES_EXIBICAO):
            continue
        cobertas.add((int(e["tela"]), int(e["exibicao"])))

    def _existe(tela: int, exibicao: int) -> dict | None:
        """Exibição do produto, ou ``None`` se a tela ou a exibição não existir."""
        tela_p = telas.get(tela)
        if tela_p is None:
            return None
        exibicoes = tela_p["exibicoes"]
        if not 0 <= exibicao < len(exibicoes):
            return None
        return exibicoes[exibicao]

    for e in d.get("exibicoes", []):
        if not all(k in e for k in CHAVES_EXIBICAO):
            continue
        if _existe(int(e["tela"]), int(e["exibicao"])) is None:
            erros.append(
                f"exibicoes: tela {e['tela']}, exibição {e['exibicao']} não existe no produto"
            )

    for c in d.get("colunas", []):
        if not all(k in c for k in CHAVES_COLUNA):
            continue
        ex = _existe(int(c["tela"]), int(c["exibicao"]))
        if ex is None:
            erros.append(
                f"colunas: tela {c['tela']}, exibição {c['exibicao']} não existe no produto"
            )
            continue
        t = c["t_audio"]
        if _numero(t) and not (float(ex["t0"]) - 1 <= t <= float(ex["t1"]) + 1):
            erros.append(
                f"tela {c['tela']}, exibição {c['exibicao']}, coluna {c['coluna']}: "
                f"t_audio {t} fora da janela [{ex['t0']} - 1, {ex['t1']} + 1]"
            )

    for tela, exibicao in sorted(cobertas):
        for coluna in sorted(notas_por_tela.get(tela, ())):
            if (tela, exibicao, coluna) not in chaves_colunas:
                erros.append(
                    f"nota sem entrada em colunas: tela {tela}, coluna {coluna}, "
                    f"exibição {exibicao}"
                )


def validar(d: dict, produto: dict | None = None) -> list[str]:
    """Confere um arquivo ``chorinho/audio@1`` contra as regras do esquema.

    Args:
        d: arquivo a validar.
        produto: JSON do ``chorinho/video@1``; se dado, confere também a cobertura das notas,
            a existência de tela e exibição e a janela de tempo.

    Returns:
        Lista de erros em português. Lista vazia quer dizer que o arquivo está válido.
    """
    erros: list[str] = []
    if d.get("esquema") != ESQUEMA:
        erros.append(f"esquema {d.get('esquema')!r} diferente de {ESQUEMA!r}")
    erros.extend(_faltando(d, CHAVES_TOPO, "topo"))
    if "video" in d:
        erros.extend(_faltando(d["video"], CHAVES_VIDEO, "video"))
    if "gerado_por" in d:
        erros.extend(_faltando(d["gerado_por"], CHAVES_GERADO_POR, "gerado_por"))
    if "afericao" in d:
        erros.extend(_faltando(d["afericao"], CHAVES_AFERICAO, "afericao"))

    exibicoes = d.get("exibicoes", [])
    colunas = d.get("colunas", [])
    if not isinstance(exibicoes, list):
        erros.append("exibicoes não é lista")
        exibicoes = []
    if not isinstance(colunas, list):
        erros.append("colunas não é lista")
        colunas = []
    for i, e in enumerate(exibicoes):
        erros.extend(_faltando(e, CHAVES_EXIBICAO, f"exibicoes[{i}]"))
        chaves_alarme = (
            "recusada",
            "cos_medio",
            "rasgueado",
            "fora_da_pagina",
            "alarme_leitura",
        )
        coerente = (
            not isinstance(e, dict)
            or not all(k in e for k in chaves_alarme)
            or e["alarme_leitura"]
            == alarme_leitura(
                e["recusada"], e["cos_medio"], e["rasgueado"], e["fora_da_pagina"]
            )
        )
        if not coerente:
            erros.append(f"exibicoes[{i}]: alarme_leitura incoerente com recusa e cos")

    chaves = _validar_colunas(colunas, erros)
    _validar_monotonia(colunas, erros)
    if produto is not None:
        _validar_contra_produto(d, produto, chaves, erros)
    return erros


def escrever(d: dict, saida: str | Path) -> None:
    """Grava o arquivo em JSON de forma atômica (temporário e ``os.replace``).

    Args:
        d: arquivo ``chorinho/audio@1``, já validado.
        saida: caminho do arquivo final; a pasta é criada se faltar.
    """
    destino = Path(saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(f".{destino.name}.tmp")
    temporario.write_text(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    os.replace(temporario, destino)


def resumo(d: dict) -> list[str]:
    """Linhas de resumo para a CLI: colunas com tempo, recusas por motivo e exibições.

    Args:
        d: arquivo ``chorinho/audio@1``.

    Returns:
        Linhas de texto, em português.
    """
    colunas = d["colunas"]
    com_tempo = sum(1 for c in colunas if c["t_audio"] is not None)
    por_motivo = Counter(c["motivo"] for c in colunas if c["t_audio"] is None)
    exibicoes = d["exibicoes"]
    recusadas = [e for e in exibicoes if e["recusada"]]
    linhas = [
        f"colunas com tempo {com_tempo} de {len(colunas)}",
        "recusadas por motivo: "
        + (", ".join(f"{m} {n}" for m, n in por_motivo.most_common()) or "nenhuma"),
        f"exibições recusadas: {len(recusadas)} de {len(exibicoes)}",
    ]
    for e in recusadas:
        linhas.append(f"  tela {e['tela']}, exibição {e['exibicao']}: {e['motivo']}")
    rasgueados = sum(1 for e in exibicoes if e["rasgueado"])
    linhas.append(
        f"rasgueados (colunas abafadas): {rasgueados} de {len(exibicoes)} exibições"
    )
    alarmes = sorted({e["tela"] for e in exibicoes if e["alarme_leitura"]})
    linhas.append(
        f"alarmes de leitura: {sum(e['alarme_leitura'] for e in exibicoes)} de "
        f"{len(exibicoes)} exibições"
        + (f" (telas {', '.join(str(t) for t in alarmes)})" if alarmes else "")
    )
    fora = [e for e in exibicoes if e["fora_da_pagina"]]
    linhas.append(
        f"fora da página (trecho na margem): {len(fora)} de {len(exibicoes)} exibições, "
        f"{sum(1 for e in fora if e['recusada'])} delas recusadas"
    )
    return linhas


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI: monta, valida, grava e imprime o resumo.

    Args:
        argv: argumentos (``None`` usa ``sys.argv``).

    Returns:
        ``0`` se gravou; ``1`` se o arquivo montado não passou na validação (nada é gravado).
    """
    parser = argparse.ArgumentParser(
        description="Escreve e valida o arquivo irmão chorinho/audio@1."
    )
    parser.add_argument("--produto", required=True, help="JSON do chorinho/video@1")
    parser.add_argument("--alinhado", required=True, help="saída do tab.audio_alinhar")
    parser.add_argument("--saida", required=True, help="arquivo .audio.json a gravar")
    parser.add_argument(
        "--commit", default=None, help="hash do commit (padrão: git HEAD, se houver)"
    )
    args = parser.parse_args(argv)

    commit = args.commit or _commit_do_git()
    d = montar(args.produto, args.alinhado, commit=commit)
    produto, _ = _ler_json(args.produto)
    erros = validar(d, produto)
    if erros:
        for erro in erros:
            print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    escrever(d, args.saida)
    for linha in resumo(d):
        print(linha)
    print(f"gravado: {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
