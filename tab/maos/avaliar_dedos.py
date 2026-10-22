"""Avaliador dos dedos (M3): mede um método contra o gabarito do dono.

Compara, nota a nota, a predição de um método com o gabarito de dedos
(``GABARITO_DEDOS``). Todas as variantes da trilha das mãos passam por aqui, para que
os números sejam comparáveis entre si.

Regras da conta (são as mesmas para todo método):

1. Sai a nota listada em ``confiabilidade.excluir`` (hoje ``n19``: o dono disse que a
   casa 3 da corda 3 não está sendo apertada nesse instante).
2. Saem as notas dos ataques listados em ``confiabilidade.duplicadas`` (hoje ``a22``,
   que é o mesmo ataque que o ``a21``): a nota física já é medida pelo ``a21``.
3. Cada NOTA FÍSICA conta uma vez: dedup por ``indice_mvp``. Se duas entradas têm o
   mesmo índice e respostas diferentes, sai um aviso e fica a da nota ``sorteada``.
4. Resposta ``"?"`` do gabarito fica fora da conta DAQUELA mão. Uma nota com esquerda
   "?" e direita conhecida entra na conta da direita, e o inverso.
5. Predição ``None`` significa que o método NÃO decidiu. Conta como erro no acerto
   total e fica fora da acurácia entre as decididas (que aparece à parte).

Métricas da esquerda: acerto total (sobre as notas válidas), acerto nas PISADAS
(gabarito diferente de ``"0"``), cobertura (fração decidida) e acerto entre as
decididas. Matriz de confusão 0-4, com ``-`` para "não decidiu".

Métricas da direita: acerto total e matriz p/i/m/a/c. A direita é SEMPRE impressa com
o aviso de gabarito parcial: parte das respostas foi inferida pelo dono.

Uso::

    python -m tab.maos_avaliar_dedos --predicao data/saida/maos/m3/pred_X.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tab.comum.caminhos import GABARITO_DEDOS, MAOS_M3

#: Respostas válidas da esquerda: dedos 1 a 4 e ``"0"`` para corda solta.
ESQUERDA_VALIDAS: tuple[str, ...] = ("0", "1", "2", "3", "4")

#: Respostas válidas da direita: polegar, indicador, médio, anelar e ``c``.
DIREITA_VALIDAS: tuple[str, ...] = ("p", "i", "m", "a", "c")

#: Aviso impresso sempre que a direita aparece.
AVISO_DIREITA = "gabarito parcial (inferido em parte)"

_NOME_METODO = re.compile(r"^[a-z0-9_]+$")


def carregar_json(caminho: Path) -> dict[str, Any]:
    """Lê um arquivo JSON em UTF-8.

    Args:
        caminho: arquivo a ler.

    Returns:
        O conteúdo como dicionário.
    """
    return json.loads(caminho.read_text(encoding="utf-8"))


def montar_predicao(
    metodo: str, decisoes: dict[int, tuple[str | None, str | None]]
) -> dict[str, Any]:
    """Monta o JSON de predição no formato que o avaliador lê.

    Args:
        metodo: nome do método (``[a-z0-9_]+``), usado no nome do arquivo.
        decisoes: ``indice_mvp`` -> ``(esquerda, direita)``; ``None`` = não decidiu.

    Returns:
        Dicionário ``{"metodo", "notas"}`` com as chaves do ``indice_mvp`` em texto.

    Raises:
        ValueError: se o nome do método tem caracteres fora de ``[a-z0-9_]``.
    """
    if not _NOME_METODO.match(metodo):
        raise ValueError(f"nome de método inválido: {metodo!r}")
    notas = {
        str(indice): {"esquerda": esq, "direita": dir_}
        for indice, (esq, dir_) in sorted(decisoes.items())
    }
    return {"metodo": metodo, "notas": notas}


def carregar_predicao(caminho: Path) -> dict[str, Any]:
    """Lê e valida uma predição JSON.

    Args:
        caminho: arquivo de predição.

    Returns:
        O dicionário da predição, já validado.

    Raises:
        ValueError: se o nome do método, o formato das notas ou alguma resposta
            estiver fora do vocabulário.
    """
    pred = carregar_json(caminho)
    metodo = pred.get("metodo")
    if not isinstance(metodo, str) or not _NOME_METODO.match(metodo):
        raise ValueError(f"{caminho}: 'metodo' ausente ou inválido")
    if not isinstance(pred.get("notas"), dict):
        raise ValueError(f"{caminho}: 'notas' deve ser um objeto")
    for indice, entrada in pred["notas"].items():
        esq = entrada.get("esquerda")
        dir_ = entrada.get("direita")
        if esq is not None and esq not in ESQUERDA_VALIDAS:
            raise ValueError(f"{caminho}: nota {indice} com esquerda {esq!r}")
        if dir_ is not None and dir_ not in DIREITA_VALIDAS:
            raise ValueError(f"{caminho}: nota {indice} com direita {dir_!r}")
    return pred


def _razao(parte: int, todo: int) -> float | None:
    """Razão entre duas contagens, ou ``None`` quando o total é zero.

    Args:
        parte: contagem do numerador.
        todo: contagem do denominador.

    Returns:
        ``parte / todo``, ou ``None`` se ``todo`` é zero.
    """
    return parte / todo if todo else None


def notas_fisicas(
    gabarito: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Lista as notas do gabarito que entram na conta, uma vez por nota física.

    Aplica as regras 1 a 3 da docstring do módulo, nesta ordem: exclusão por id,
    exclusão de ataque duplicado, dedup por ``indice_mvp``. A regra 4 (``"?"``) é
    aplicada depois, por mão, em :func:`_acerto_mao`.

    Args:
        gabarito: o JSON do gabarito (formato 3).

    Returns:
        ``(notas, meta)``. ``notas`` são as entradas do gabarito escolhidas, em ordem
        de ``indice_mvp``. ``meta`` tem ``contagem`` (o que saiu e por quê, para
        conferir o significado do número, regra 3 do AGENTS.md) e ``avisos``.
    """
    confiab = gabarito.get("confiabilidade", {})
    excluir = set(confiab.get("excluir", {}))
    duplicadas = set(confiab.get("duplicadas", {}))
    no_gabarito = gabarito["notas"]
    sai_por_id = [n["id"] for n in no_gabarito if n["id"] in excluir]
    sai_por_ataque = [
        n["id"]
        for n in no_gabarito
        if n["id"] not in excluir and n["ataque"] in duplicadas
    ]
    candidatas = [
        n
        for n in no_gabarito
        if n["id"] not in excluir and n["ataque"] not in duplicadas
    ]
    grupos: dict[int, list[dict[str, Any]]] = {}
    for nota in candidatas:
        grupos.setdefault(nota["indice_mvp"], []).append(nota)
    avisos: list[str] = []
    notas: list[dict[str, Any]] = []
    for indice in sorted(grupos):
        grupo = grupos[indice]
        escolhida = next((n for n in grupo if n["sorteada"]), grupo[0])
        respostas = {(n["esquerda"], n["direita"]) for n in grupo}
        if len(grupo) > 1 and len(respostas) > 1:
            avisos.append(
                f"indice_mvp {indice}: {len(grupo)} entradas com respostas "
                f"diferentes; ficou {escolhida['id']} (sorteada)"
            )
        notas.append(escolhida)
    contagem = {
        "notas_no_gabarito": len(no_gabarito),
        "excluidas_por_id": sai_por_id,
        "excluidas_por_ataque_duplicado": sai_por_ataque,
        "notas_fisicas": len(notas),
    }
    return notas, {"contagem": contagem, "avisos": avisos}


def _acerto_mao(
    notas: list[dict[str, Any]],
    pred: dict[str, Any],
    mao: str,
    rotulos: tuple[str, ...],
) -> dict[str, Any]:
    """Métricas de uma mão: acerto, cobertura, matriz e lista de erros.

    Args:
        notas: notas físicas já deduplicadas.
        pred: predição validada.
        mao: ``"esquerda"`` ou ``"direita"``.
        rotulos: vocabulário da mão, sem o ``"-"`` de "não decidiu".

    Returns:
        Dicionário com as contagens, as razões, a matriz e os erros.
    """
    validas = [n for n in notas if n[mao] != "?"]
    matriz = {g: dict.fromkeys((*rotulos, "-"), 0) for g in rotulos}
    erros: list[dict[str, Any]] = []
    acertos = 0
    decididas = 0
    for nota in validas:
        gab = nota[mao]
        entrada = pred["notas"].get(str(nota["indice_mvp"]), {})
        predito = entrada.get(mao)
        if predito is not None:
            decididas += 1
        chave = predito if predito is not None else "-"
        matriz[gab][chave] += 1
        if predito == gab:
            acertos += 1
        else:
            erros.append(
                {
                    "id": nota["id"],
                    "ataque": nota["ataque"],
                    "corda": nota["corda"],
                    "casa": nota["casa"],
                    "gabarito": gab,
                    "predito": predito,
                }
            )
    n = len(validas)
    return {
        "n_validas": n,
        "decididas": decididas,
        "cobertura": _razao(decididas, n),
        "acertos": acertos,
        "acerto_total": _razao(acertos, n),
        # Um acerto exige predito igual ao gabarito (que não é None), logo todo acerto
        # está entre as decididas.
        "acerto_entre_decididas": _razao(acertos, decididas),
        "matriz": matriz,
        "erros": erros,
    }


def avaliar(gabarito: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    """Compara uma predição com o gabarito de dedos e devolve o relatório.

    Args:
        gabarito: o JSON do gabarito (formato 3).
        pred: predição validada (ver :func:`carregar_predicao`).

    Returns:
        Dicionário com ``metodo``, ``contagem``, ``avisos``, ``esquerda`` (com
        ``acerto_pisadas``), ``direita`` (com ``aviso``).
    """
    notas, meta = notas_fisicas(gabarito)
    esquerda = _acerto_mao(notas, pred, "esquerda", ESQUERDA_VALIDAS)
    pisadas = [n for n in notas if n["esquerda"] not in ("?", "0")]
    acertos_pisadas = sum(
        1
        for n in pisadas
        if pred["notas"].get(str(n["indice_mvp"]), {}).get("esquerda") == n["esquerda"]
    )
    esquerda["n_pisadas"] = len(pisadas)
    esquerda["acertos_pisadas"] = acertos_pisadas
    esquerda["acerto_pisadas"] = _razao(acertos_pisadas, len(pisadas))
    direita = _acerto_mao(notas, pred, "direita", DIREITA_VALIDAS)
    direita["aviso"] = AVISO_DIREITA
    contagem = {
        **meta["contagem"],
        "pisadas_esquerda": len(pisadas),
    }
    return {
        "metodo": pred["metodo"],
        "contagem": contagem,
        "avisos": meta["avisos"],
        "esquerda": esquerda,
        "direita": direita,
    }


def porcentagem(valor: float | None) -> str:
    """Formata uma razão como porcentagem com uma casa, ou ``-`` se não há base.

    Args:
        valor: razão em [0, 1], ou ``None``.

    Returns:
        Texto como ``"94,3%"``, ou ``"-"``.
    """
    if valor is None:
        return "-"
    return f"{100 * valor:.1f}%".replace(".", ",")


def _tabela_matriz(matriz: dict[str, dict[str, int]]) -> list[str]:
    """Matriz de confusão em Markdown: gabarito nas linhas, predito nas colunas.

    Args:
        matriz: ``gabarito -> predito -> contagem``, com ``"-"`` para não decidiu.

    Returns:
        As linhas da tabela.
    """
    colunas = list(next(iter(matriz.values())).keys())
    linhas = [
        "| gabarito \\ predito | " + " | ".join(colunas) + " |",
        "|" + "---|" * (len(colunas) + 1),
    ]
    for gab, linha in matriz.items():
        celulas = " | ".join(str(linha[c]) for c in colunas)
        linhas.append(f"| {gab} | {celulas} |")
    return linhas


def relatorio_markdown(rel: dict[str, Any]) -> str:
    """Relatório do avaliador em Markdown, pronto para o stdout.

    Args:
        rel: o dicionário devolvido por :func:`avaliar`.

    Returns:
        Texto com a contagem, as métricas da esquerda, a matriz e a direita.
    """
    c = rel["contagem"]
    esq = rel["esquerda"]
    dir_ = rel["direita"]
    linhas = [
        f"## Avaliação: {rel['metodo']}",
        "",
        f"Notas no gabarito: {c['notas_no_gabarito']}. Excluídas por id: "
        f"{c['excluidas_por_id'] or '-'}. Excluídas por ataque duplicado: "
        f"{c['excluidas_por_ataque_duplicado'] or '-'}. Notas físicas na conta: "
        f"{c['notas_fisicas']}. Pisadas (esquerda != 0): {c['pisadas_esquerda']}.",
    ]
    for aviso in rel["avisos"]:
        linhas.append(f"Aviso: {aviso}")
    linhas += [
        "",
        "### Esquerda",
        "",
        "| métrica | valor |",
        "|---|---|",
        f"| acerto total | {esq['acertos']}/{esq['n_validas']} "
        f"({porcentagem(esq['acerto_total'])}) |",
        f"| acerto nas pisadas | {esq['acertos_pisadas']}/{esq['n_pisadas']} "
        f"({porcentagem(esq['acerto_pisadas'])}) |",
        f"| cobertura | {esq['decididas']}/{esq['n_validas']} "
        f"({porcentagem(esq['cobertura'])}) |",
        f"| acerto entre decididas | {porcentagem(esq['acerto_entre_decididas'])} |",
        "",
        *_tabela_matriz(esq["matriz"]),
        "",
        f"### Direita ({dir_['aviso']})",
        "",
        f"Acerto total: {dir_['acertos']}/{dir_['n_validas']} "
        f"({porcentagem(dir_['acerto_total'])}). Cobertura: {dir_['decididas']}/"
        f"{dir_['n_validas']} ({porcentagem(dir_['cobertura'])}).",
        "",
        *_tabela_matriz(dir_["matriz"]),
    ]
    return "\n".join(linhas)


def gravar_avaliacao(rel: dict[str, Any], pasta: Path) -> Path:
    """Grava o relatório como ``avaliacao_<metodo>.json`` na pasta indicada.

    Args:
        rel: o dicionário devolvido por :func:`avaliar`.
        pasta: diretório de saída (criado se faltar).

    Returns:
        O caminho do arquivo gravado.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"avaliacao_{rel['metodo']}.json"
    destino.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def main() -> None:
    """Avalia um arquivo de predição contra o gabarito e grava o relatório."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predicao", type=Path, required=True)
    parser.add_argument("--gabarito", type=Path, default=GABARITO_DEDOS)
    args = parser.parse_args()
    pred = carregar_predicao(args.predicao)
    rel = avaliar(carregar_json(args.gabarito), pred)
    print(relatorio_markdown(rel))
    destino = gravar_avaliacao(rel, MAOS_M3)
    print(f"\nJSON: {destino}")


if __name__ == "__main__":
    main()
