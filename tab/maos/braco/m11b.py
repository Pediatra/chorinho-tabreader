"""Teste do braço encadeado (M11b): sorteio dos 8 vídeos e das marcas do dono.

Rodada 1018 (``docs/rodadas/1018-m11b-braco-encadeado.md``, seção "Divisão"). O teste
roda uma vez, com tudo congelado, e o sorteio é feito por código antes de qualquer
marca. Este módulo faz só a parte do sorteio; as marcas são feitas na ferramenta
``tab.maos_braco_gabarito``.

Duas etapas:

1. ``etapa1``: sorteia 8 canais fora do gabarito do braço, 1 vídeo por canal, e 5
   instantes candidatos por vídeo (entre 10 % e 95 % da duração). Grava
   ``lista_etapa1.json`` para ``tab.maos_braco_gabarito acrescentar``, que extrai os
   40 quadros, e deixa o índice e o gabarito em branco.
2. ``etapa2``: o quadro-chave é o primeiro candidato, na ordem do sorteio, em que o
   dono marcou braço (``sim`` ou ``parcial``). Depois sorteia 4 alvos por vídeo entre
   o quadro-chave + 5 s e o fim do vídeo. Grava ``chaves.json`` e
   ``lista_etapa2.json``. Não extrai quadros: isso é outro ``acrescentar``.

Os sorteios de candidatos e de alvos usam um gerador próprio por vídeo, semeado com
``"{SEMENTE}:{arquivo}:{fase}"``. Assim a etapa 2 não depende da ordem de execução.

Uso::

    python -m tab.maos_braco_m11b etapa1
    python -m tab.maos_braco_gabarito acrescentar --lista data/saida/maos/m11b/lista_etapa1.json --pasta data/saida/maos/m11b --ouro data/gold/maos/braco_m11b.json
    python -m tab.maos_braco_m11b etapa2
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import random
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from tab.comum.caminhos import (
    CENSO_MAOS,
    GABARITO_BRACO_M11B,
    MAOS_M3B,
    MAOS_M11B,
    acervo,
)
from tab.maos.braco.gabarito import CAMPOS_RESPOSTA, gabarito_novo

#: Semente do sorteio do teste (rodada 1018).
SEMENTE = 20261018

#: Canais sorteados (um vídeo por canal).
N_CANAIS = 8

#: Instantes candidatos a quadro-chave, por vídeo, na ordem do sorteio.
N_CANDIDATOS = 5

#: Alvos por vídeo (instantes depois do quadro-chave).
N_ALVOS = 4

#: Faixa dos candidatos, como fração da duração do vídeo.
FRAC_INICIO = 0.10
FRAC_FIM = 0.95

#: Folga mínima, em segundos, entre o quadro-chave e o primeiro alvo.
FOLGA_S = 5.0

#: Margem, em segundos, antes do fim do vídeo: nenhum alvo cai nela.
MARGEM_FIM_S = 1.0

#: Distância mínima, em segundos, entre dois alvos do mesmo vídeo (emenda de 2026-10-17:
#: o sorteio uniforme pôs alvos a 0,05 s um do outro). Em vídeo curto vale o
#: comprimento do intervalo dividido por ``N_ALVOS``, se for menor.
ESPACO_MINIMO_S = 10.0

#: Tentativas do sorteio por rejeição dos alvos espaçados.
TENTATIVAS_ESPACADOS = 100_000

#: Valores de ``braco`` que contam como braço presente no quadro-chave.
BRACOS_CHAVE = ("sim", "parcial")


def canais_do_gabarito(indice_m3b: dict) -> set[str]:
    """Canais que já estão no gabarito do braço (M3b), lidos do índice.

    Args:
        indice_m3b: ``indice.json`` da amostra do braço (com ``quadros``, cada um com
            ``canal``).

    Returns:
        O conjunto de canais presentes na amostra.
    """
    return {quadro["canal"] for quadro in indice_m3b["quadros"]}


def rng_do_video(arquivo: str, fase: str) -> random.Random:
    """Gerador próprio de um vídeo e de uma fase, derivado da semente do teste.

    Args:
        arquivo: caminho relativo ao acervo.
        fase: nome da fase do sorteio (``candidatos`` ou ``alvos``).

    Returns:
        Um ``random.Random`` que não depende de outros sorteios.
    """
    return random.Random(f"{SEMENTE}:{arquivo}:{fase}")


def sortear_videos(censo: list[dict], excluir: set[str], semente: int) -> list[dict]:
    """Sorteia 1 vídeo de cada um de ``N_CANAIS`` canais elegíveis.

    Elegíveis são os canais do censo que não estão em ``excluir``, em ordem
    alfabética. O sorteio do canal é ``rng.sample``; depois, para cada canal sorteado
    (na ordem do sorteio), ``rng.choice`` entre os vídeos do canal ordenados por
    ``arquivo``.

    Args:
        censo: linhas de ``censo_maos.jsonl`` (cada uma com ``canal``, ``arquivo`` e
            ``chave``).
        excluir: canais que não podem ser sorteados (já estão no gabarito do braço).
        semente: semente do gerador deste sorteio.

    Returns:
        Uma cópia da linha de censo de cada vídeo sorteado, na ordem do sorteio.

    Raises:
        ValueError: se houver menos de ``N_CANAIS`` canais elegíveis.
    """
    elegiveis = sorted({linha["canal"] for linha in censo} - excluir)
    if len(elegiveis) < N_CANAIS:
        raise ValueError(
            f"só {len(elegiveis)} canais elegíveis; o teste precisa de {N_CANAIS}"
        )
    por_canal: dict[str, list[dict]] = {}
    for linha in censo:
        por_canal.setdefault(linha["canal"], []).append(linha)
    rng = random.Random(semente)
    sorteados = []
    for canal in rng.sample(elegiveis, N_CANAIS):
        videos = sorted(por_canal[canal], key=lambda linha: linha["arquivo"])
        sorteados.append(dict(rng.choice(videos)))
    return sorteados


def _no_intervalo(valor: float, inicio: float, fim: float) -> float:
    """Limita ``valor`` ao intervalo ``[inicio, fim]`` e arredonda a 2 casas.

    Args:
        valor: número sorteado.
        inicio: limite inferior.
        fim: limite superior.

    Returns:
        O valor limitado e arredondado.
    """
    return round(min(max(valor, inicio), fim), 2)


def candidatos(duracao: float, rng: random.Random) -> list[float]:
    """Sorteia ``N_CANDIDATOS`` instantes na faixa de ``FRAC_INICIO`` a ``FRAC_FIM``.

    Os instantes saem na ordem do sorteio e não são ordenados: o dono marca na ordem,
    e o primeiro com braço vira o quadro-chave.

    Args:
        duracao: duração do vídeo, em segundos.
        rng: gerador do sorteio deste vídeo.

    Returns:
        ``N_CANDIDATOS`` instantes, em segundos, com 2 casas, na ordem do sorteio.
    """
    inicio = FRAC_INICIO * duracao
    fim = FRAC_FIM * duracao
    return [
        _no_intervalo(rng.uniform(inicio, fim), inicio, fim)
        for _ in range(N_CANDIDATOS)
    ]


def alvos(t_chave: float, duracao: float, rng: random.Random) -> list[float]:
    """Sorteia ``N_ALVOS`` instantes entre o quadro-chave + ``FOLGA_S`` e o fim.

    Args:
        t_chave: instante do quadro-chave, em segundos.
        duracao: duração do vídeo, em segundos.
        rng: gerador do sorteio deste vídeo.

    Returns:
        ``N_ALVOS`` instantes ordenados, em segundos, com 2 casas.

    Raises:
        ValueError: se o intervalo dos alvos estiver vazio (vídeo curto demais para o
            quadro-chave escolhido).
    """
    inicio = t_chave + FOLGA_S
    fim = duracao - MARGEM_FIM_S
    if fim <= inicio:
        raise ValueError(
            f"intervalo vazio para os alvos: [{inicio:.2f}, {fim:.2f}] "
            f"(quadro-chave em {t_chave:.2f} s, duração {duracao:.2f} s)"
        )
    return sorted(
        _no_intervalo(rng.uniform(inicio, fim), inicio, fim) for _ in range(N_ALVOS)
    )


def duracao_do_video(caminho: Path) -> float:
    """Duração de um vídeo, em segundos, pelo ffprobe (sem shell).

    Args:
        caminho: arquivo no acervo (só leitura).

    Returns:
        A duração do contêiner, em segundos.

    Raises:
        RuntimeError: se o ffprobe falhar ou a duração não for um número positivo.
    """
    comando = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(caminho),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True, check=False)
    if resultado.returncode != 0:
        erro = resultado.stderr.strip()
        raise RuntimeError(f"ffprobe falhou em {caminho}: {erro}")
    try:
        duracao = float(resultado.stdout.strip())
    except ValueError as erro:
        raise RuntimeError(f"duração ilegível em {caminho}") from erro
    if not math.isfinite(duracao) or duracao <= 0:
        raise RuntimeError(f"duração inválida em {caminho}: {duracao}")
    return duracao


def _duracao_do_acervo(arquivo: str) -> float:
    """Duração de um vídeo do acervo, pelo caminho relativo a ele.

    Args:
        arquivo: caminho relativo ao acervo.

    Returns:
        A duração, em segundos.
    """
    return duracao_do_video(acervo() / arquivo)


def planejar_etapa1(
    censo: list[dict],
    excluir: set[str],
    duracao_de: Callable[[str], float],
) -> dict:
    """Monta o sorteio da etapa 1: vídeos, durações e candidatos com ordem.

    Args:
        censo: linhas de ``censo_maos.jsonl``.
        excluir: canais fora do sorteio (gabarito do braço).
        duracao_de: função que devolve a duração de um vídeo, pelo caminho relativo.

    Returns:
        Dicionário com ``semente``, ``canais_excluidos`` e ``videos``. Cada vídeo tem
        ``canal``, ``arquivo``, ``chave``, ``duracao`` e ``candidatos`` (uma lista de
        ``{"ordem", "t"}``, ordem a partir de 1).
    """
    videos = []
    for linha in sortear_videos(censo, excluir, SEMENTE):
        arquivo = linha["arquivo"]
        duracao = duracao_de(arquivo)
        cands = candidatos(duracao, rng_do_video(arquivo, "candidatos"))
        videos.append(
            {
                "canal": linha["canal"],
                "arquivo": arquivo,
                "chave": linha["chave"],
                "duracao": duracao,
                "candidatos": [
                    {"ordem": ordem, "t": t} for ordem, t in enumerate(cands, start=1)
                ],
            }
        )
    return {
        "semente": SEMENTE,
        "canais_excluidos": sorted(excluir),
        "videos": videos,
    }


def lista_da_etapa1(sorteio: dict) -> list[dict]:
    """Lista ``[{"arquivo", "t"}]`` aceita por ``acrescentar --lista``.

    Args:
        sorteio: saída de ``planejar_etapa1``.

    Returns:
        Os candidatos de cada vídeo, vídeo 1 (ordens 1..5), vídeo 2, e assim por diante.
    """
    return [
        {"arquivo": video["arquivo"], "t": cand["t"]}
        for video in sorteio["videos"]
        for cand in video["candidatos"]
    ]


def escolher_quadro_chave(
    candidatos: list[dict], bracos: dict[float, str | None]
) -> float:
    """Primeiro candidato, na ordem do sorteio, em que o dono viu braço.

    Um candidato sem resposta antes do primeiro com braço impede a escolha: o dono
    ainda não olhou aquele quadro. Respostas ``nao`` e ``?`` passam para o próximo.

    Args:
        candidatos: ``{"ordem", "t"}`` de um vídeo.
        bracos: valor de ``braco`` por instante; ``None`` se o quadro não foi respondido
            (ou não foi extraído).

    Returns:
        O instante do quadro-chave, em segundos.

    Raises:
        ValueError: se um candidato vier sem resposta antes do primeiro com braço, ou se
            nenhum candidato tiver braço.
    """
    for candidato in sorted(candidatos, key=lambda cand: cand["ordem"]):
        t = candidato["t"]
        braco = bracos.get(t)
        if braco is None:
            raise ValueError(
                f"candidato {candidato['ordem']} (t={t}) sem resposta antes do "
                "quadro-chave"
            )
        if braco in BRACOS_CHAVE:
            return t
    raise ValueError("nenhum candidato com braço (sim ou parcial)")


def montar_etapa2(
    sorteio: dict, indice: dict, gabarito: dict
) -> tuple[dict, list[dict]]:
    """Escolhe o quadro-chave de cada vídeo e sorteia os alvos.

    Args:
        sorteio: ``sorteio.json`` da etapa 1.
        indice: ``indice.json`` de ``MAOS_M11B`` (com ``quadros``: ``id``, ``arquivo``,
            ``t``).
        gabarito: gabarito ``braco_m11b.json`` (com ``quadros``: id -> registro).

    Returns:
        ``(chaves, lista)``: ``chaves`` tem ``semente`` e ``videos`` (quadro-chave e
        alvos de cada vídeo); ``lista`` é ``[{"arquivo", "t"}]`` com os alvos, para o
        ``acrescentar``.

    Raises:
        ValueError: se algum vídeo não tiver quadro-chave ou alvo possível. A mensagem
            diz qual vídeo.
    """
    id_por_par = {
        (quadro["arquivo"], quadro["t"]): quadro["id"] for quadro in indice["quadros"]
    }
    videos = []
    lista = []
    for video in sorteio["videos"]:
        arquivo = video["arquivo"]
        bracos: dict[float, str | None] = {}
        for cand in video["candidatos"]:
            id_quadro = id_por_par.get((arquivo, cand["t"]))
            registro = gabarito["quadros"].get(id_quadro) if id_quadro else None
            bracos[cand["t"]] = registro["braco"] if registro else None
        try:
            t_chave = escolher_quadro_chave(video["candidatos"], bracos)
            instantes = alvos(t_chave, video["duracao"], rng_do_video(arquivo, "alvos"))
        except ValueError as erro:
            raise ValueError(f"{arquivo}: {erro}") from erro
        videos.append(
            {
                "canal": video["canal"],
                "arquivo": arquivo,
                "duracao": video["duracao"],
                "t_chave": t_chave,
                "braco_chave": bracos[t_chave],
                "alvos": instantes,
            }
        )
        lista.extend({"arquivo": arquivo, "t": t} for t in instantes)
    return {"semente": SEMENTE, "videos": videos}, lista


def substituir_video(
    sorteio: dict,
    canal_saida: str,
    censo: list[dict],
    duracao_de: Callable[[str], float],
    motivo: str,
) -> tuple[dict, list[dict]]:
    """Troca o vídeo de um canal por um sorteado de outro canal elegível.

    O canal novo sai de um gerador próprio (``"{SEMENTE}:substituto:{canal_saida}"``),
    entre os canais do censo que não estão excluídos nem já sorteados, em ordem
    alfabética. O vídeo e os candidatos seguem as mesmas regras da etapa 1. O vídeo
    trocado fica registrado em ``substituicoes``, com o motivo.

    Args:
        sorteio: ``sorteio.json`` da etapa 1 (não é alterado).
        canal_saida: canal do vídeo que sai.
        censo: linhas de ``censo_maos.jsonl``.
        duracao_de: função que devolve a duração de um vídeo, pelo caminho relativo.
        motivo: por que o vídeo saiu (fica no registro).

    Returns:
        ``(sorteio_novo, lista)``: o sorteio com o vídeo trocado na mesma posição e a
        lista ``[{"arquivo", "t"}]`` dos 5 candidatos novos, para o ``acrescentar``.

    Raises:
        ValueError: se o canal não está no sorteio ou se não sobra canal elegível.
    """
    posicoes = [k for k, v in enumerate(sorteio["videos"]) if v["canal"] == canal_saida]
    if not posicoes:
        raise ValueError(f"canal {canal_saida} não está no sorteio")
    usados = set(sorteio["canais_excluidos"])
    usados |= {v["canal"] for v in sorteio["videos"]}
    usados |= {s["saiu"]["canal"] for s in sorteio.get("substituicoes", [])}
    elegiveis = sorted({linha["canal"] for linha in censo} - usados)
    if not elegiveis:
        raise ValueError("nenhum canal elegível sobrando para substituir")
    rng = random.Random(f"{SEMENTE}:substituto:{canal_saida}")
    canal = rng.choice(elegiveis)
    videos = sorted(
        (linha for linha in censo if linha["canal"] == canal),
        key=lambda linha: linha["arquivo"],
    )
    linha = rng.choice(videos)
    arquivo = linha["arquivo"]
    duracao = duracao_de(arquivo)
    cands = candidatos(duracao, rng_do_video(arquivo, "candidatos"))
    entrou = {
        "canal": canal,
        "arquivo": arquivo,
        "chave": linha["chave"],
        "duracao": duracao,
        "candidatos": [
            {"ordem": ordem, "t": t} for ordem, t in enumerate(cands, start=1)
        ],
    }
    novo = json.loads(json.dumps(sorteio))
    saiu = novo["videos"][posicoes[0]]
    novo["videos"][posicoes[0]] = entrou
    novo.setdefault("substituicoes", []).append(
        {"saiu": saiu, "entrou": canal, "motivo": motivo}
    )
    lista = [{"arquivo": arquivo, "t": c["t"]} for c in entrou["candidatos"]]
    return novo, lista


def alvos_espacados(t_chave: float, duracao: float, rng: random.Random) -> list[float]:
    """Sorteia ``N_ALVOS`` instantes como ``alvos``, mas com distância mínima entre eles.

    A distância mínima é ``ESPACO_MINIMO_S``, ou o comprimento do intervalo dividido
    por ``N_ALVOS`` se isso for menor. O sorteio é por rejeição: sorteia os instantes
    e só aceita se todos os vizinhos estiverem afastados.

    Args:
        t_chave: instante do quadro-chave, em segundos.
        duracao: duração do vídeo, em segundos.
        rng: gerador do sorteio deste vídeo.

    Returns:
        ``N_ALVOS`` instantes ordenados, em segundos, com 2 casas.

    Raises:
        ValueError: se o intervalo estiver vazio ou nenhuma tentativa der certo.
    """
    inicio = t_chave + FOLGA_S
    fim = duracao - MARGEM_FIM_S
    if fim <= inicio:
        raise ValueError(
            f"intervalo vazio para os alvos: [{inicio:.2f}, {fim:.2f}] "
            f"(quadro-chave em {t_chave:.2f} s, duração {duracao:.2f} s)"
        )
    espaco = min(ESPACO_MINIMO_S, (fim - inicio) / N_ALVOS)
    for _ in range(TENTATIVAS_ESPACADOS):
        instantes = sorted(
            _no_intervalo(rng.uniform(inicio, fim), inicio, fim) for _ in range(N_ALVOS)
        )
        if all(b - a >= espaco for a, b in itertools.pairwise(instantes)):
            return instantes
    raise ValueError(f"nenhum sorteio com alvos a {espaco:.2f} s uns dos outros")


def refazer_alvos(
    chaves: dict, canais: list[str], motivo: str
) -> tuple[dict, list[dict]]:
    """Sorteia de novo, com ``alvos_espacados``, os alvos dos vídeos pedidos.

    O gerador é ``rng_do_video(arquivo, "alvos_espacados")``. Os alvos antigos ficam
    registrados em ``refeitos``, com o motivo.

    Args:
        chaves: ``chaves.json`` da etapa 2 (não é alterado).
        canais: canais cujos alvos são sorteados de novo.
        motivo: por que os alvos foram refeitos.

    Returns:
        ``(chaves_novo, lista)``: as chaves com os alvos novos e a lista
        ``[{"arquivo", "t"}]`` dos alvos novos, para o ``acrescentar``.

    Raises:
        ValueError: se algum canal não estiver nas chaves.
    """
    presentes = {v["canal"] for v in chaves["videos"]}
    faltando = sorted(set(canais) - presentes)
    if faltando:
        raise ValueError(f"canais fora das chaves: {', '.join(faltando)}")
    novo = json.loads(json.dumps(chaves))
    lista: list[dict] = []
    for video in novo["videos"]:
        if video["canal"] not in canais:
            continue
        antigos = video["alvos"]
        rng = rng_do_video(video["arquivo"], "alvos_espacados")
        video["alvos"] = alvos_espacados(video["t_chave"], video["duracao"], rng)
        novo.setdefault("refeitos", []).append(
            {"canal": video["canal"], "alvos_antigos": antigos, "motivo": motivo}
        )
        lista.extend({"arquivo": video["arquivo"], "t": t} for t in video["alvos"])
    return novo, lista


def _tem_marca(registro: dict) -> bool:
    """Se algum campo de resposta do quadro tem valor (lista vazia não conta).

    Args:
        registro: resposta de um quadro.

    Returns:
        True quando o dono deixou alguma marca no quadro.
    """
    return any(registro.get(campo) not in (None, []) for campo in CAMPOS_RESPOSTA)


def remover_em_branco(
    indice: dict, gabarito: dict, pares: set[tuple[str, float]]
) -> list[str]:
    """Tira do índice e do gabarito os quadros ``(arquivo, t)`` pedidos.

    Só remove quadro sem nenhuma marca do dono (todos os campos de resposta vazios):
    rótulo do dono não se apaga. Um clique que não deixou nada (``respondido_em``
    preenchido, campos vazios) não é rótulo.

    Args:
        indice: ``indice.json`` do teste, alterado em lugar.
        gabarito: gabarito do teste, alterado em lugar.
        pares: ``(arquivo, t)`` dos quadros a remover.

    Returns:
        Os ids removidos, em ordem.

    Raises:
        ValueError: se algum quadro pedido já tem marca do dono (nada é removido).
    """
    ids = [q["id"] for q in indice["quadros"] if (q["arquivo"], q["t"]) in pares]
    respondidos = [i for i in ids if _tem_marca(gabarito["quadros"][i])]
    if respondidos:
        raise ValueError(f"quadros com marca do dono: {', '.join(respondidos)}")
    indice["quadros"] = [q for q in indice["quadros"] if q["id"] not in ids]
    for i in ids:
        del gabarito["quadros"][i]
    return ids


def _quadros_gravados(caminho: Path) -> int:
    """Quantos quadros um JSON de índice ou gabarito já tem em disco.

    Args:
        caminho: ``indice.json`` (lista em ``quadros``) ou gabarito (dicionário em
            ``quadros``).

    Returns:
        A quantidade de quadros; 0 se o arquivo não existir.
    """
    if not caminho.is_file():
        return 0
    return len(json.loads(caminho.read_text(encoding="utf-8"))["quadros"])


def _gravar_json(destino: Path, conteudo: dict | list) -> None:
    """Grava JSON de forma atômica: temporário no mesmo diretório e ``os.replace``.

    Args:
        destino: arquivo final.
        conteudo: dicionário ou lista serializável.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, destino)


def etapa1(censo: Path, indice_m3b: Path, pasta: Path, ouro: Path) -> int:
    """Sorteia os 8 vídeos e grava os arquivos da etapa 1.

    Grava ``sorteio.json`` e ``lista_etapa1.json`` em ``pasta``. Cria ``indice.json``
    (vazio) e o gabarito (em branco) se ainda não existirem, no mesmo formato que
    ``preparar`` gera.

    Args:
        censo: ``censo_maos.jsonl``.
        indice_m3b: ``indice.json`` da amostra do braço (define os canais excluídos).
        pasta: pasta de saída do teste (``MAOS_M11B``).
        ouro: gabarito do teste (``GABARITO_BRACO_M11B``).

    Returns:
        Quantos instantes candidatos foram sorteados (``N_CANAIS * N_CANDIDATOS``).

    Raises:
        ValueError: se o índice ou o gabarito já tiverem quadros (não sobrescreve).
    """
    for caminho in (pasta / "indice.json", ouro):
        if _quadros_gravados(caminho):
            raise ValueError(f"{caminho} já tem quadros; não sobrescrevo")
    linhas = [
        json.loads(linha)
        for linha in censo.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    excluir = canais_do_gabarito(json.loads(indice_m3b.read_text(encoding="utf-8")))
    sorteio = planejar_etapa1(linhas, excluir, _duracao_do_acervo)
    lista = lista_da_etapa1(sorteio)
    _gravar_json(pasta / "sorteio.json", sorteio)
    _gravar_json(pasta / "lista_etapa1.json", lista)
    if not (pasta / "indice.json").exists():
        _gravar_json(pasta / "indice.json", {"semente": SEMENTE, "quadros": []})
    if not ouro.exists():
        _gravar_json(ouro, gabarito_novo([], SEMENTE))
    return len(lista)


def etapa2(pasta: Path, ouro: Path) -> int:
    """Escolhe os quadros-chave e grava ``chaves.json`` e ``lista_etapa2.json``.

    Args:
        pasta: pasta do teste (``sorteio.json`` e ``indice.json`` já existem).
        ouro: gabarito do teste, já marcado pelo dono.

    Returns:
        Quantos alvos foram sorteados (``N_CANAIS * N_ALVOS``).

    Raises:
        ValueError: se algum vídeo não tiver quadro-chave ou alvo possível.
    """
    sorteio = json.loads((pasta / "sorteio.json").read_text(encoding="utf-8"))
    indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
    gabarito = json.loads(ouro.read_text(encoding="utf-8"))
    chaves, lista = montar_etapa2(sorteio, indice, gabarito)
    _gravar_json(pasta / "chaves.json", chaves)
    _gravar_json(pasta / "lista_etapa2.json", lista)
    return len(lista)


def main() -> int:
    """Ponto de entrada: ``etapa1`` e ``etapa2`` do teste M11b.

    Returns:
        Código de saída do processo (2 em caso de recusa ou erro).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    sub.add_parser("etapa1", help="sorteia os 8 vídeos e os 40 instantes candidatos")
    sub.add_parser("etapa2", help="escolhe os quadros-chave e sorteia os 32 alvos")
    troca = sub.add_parser("substituir", help="troca o vídeo de um canal por outro")
    troca.add_argument("--canal", required=True, help="canal do vídeo que sai")
    troca.add_argument("--motivo", required=True, help="por que o vídeo sai")
    refazer = sub.add_parser(
        "refazer", help="sorteia de novo, espaçados, os alvos de alguns canais"
    )
    refazer.add_argument("--canais", nargs="+", required=True)
    refazer.add_argument("--motivo", required=True)
    args = ap.parse_args()
    try:
        if args.comando == "refazer":
            chaves = json.loads((MAOS_M11B / "chaves.json").read_text("utf-8"))
            indice = json.loads((MAOS_M11B / "indice.json").read_text("utf-8"))
            gabarito = json.loads(GABARITO_BRACO_M11B.read_text("utf-8"))
            novo, lista = refazer_alvos(chaves, args.canais, args.motivo)
            antigos = {
                (v["arquivo"], t)
                for v in chaves["videos"]
                if v["canal"] in args.canais
                for t in v["alvos"]
            }
            removidos = remover_em_branco(indice, gabarito, antigos)
            _gravar_json(MAOS_M11B / "indice.json", indice)
            _gravar_json(GABARITO_BRACO_M11B, gabarito)
            _gravar_json(MAOS_M11B / "chaves.json", novo)
            _gravar_json(MAOS_M11B / "lista_refeita.json", lista)
            print(f"removidos {', '.join(removidos)}; {len(lista)} alvos novos")
        elif args.comando == "substituir":
            sorteio = json.loads((MAOS_M11B / "sorteio.json").read_text("utf-8"))
            linhas = [
                json.loads(linha)
                for linha in CENSO_MAOS.read_text(encoding="utf-8").splitlines()
                if linha.strip()
            ]
            novo, lista = substituir_video(
                sorteio, args.canal, linhas, _duracao_do_acervo, args.motivo
            )
            _gravar_json(MAOS_M11B / "sorteio.json", novo)
            _gravar_json(MAOS_M11B / "lista_substituto.json", lista)
            entrou = novo["substituicoes"][-1]["entrou"]
            print(
                f"{args.canal} -> {entrou}: {len(lista)} candidatos em lista_substituto"
            )
        elif args.comando == "etapa1":
            total = etapa1(
                CENSO_MAOS, MAOS_M3B / "indice.json", MAOS_M11B, GABARITO_BRACO_M11B
            )
            print(f"{total} instantes candidatos em {MAOS_M11B}")
        else:
            total = etapa2(MAOS_M11B, GABARITO_BRACO_M11B)
            print(f"{total} alvos em {MAOS_M11B / 'lista_etapa2.json'}")
    except (ValueError, FileNotFoundError, RuntimeError) as erro:
        print(f"não foi: {erro}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
