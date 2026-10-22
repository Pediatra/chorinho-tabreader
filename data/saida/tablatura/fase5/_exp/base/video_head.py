"""VÍDEO -> JSON v1: lê cada tela de um vídeo inteiro (Fase 4 do plano do produto).

Cadeia, por tela (``tab.telas``, Fase 3):

1. imagem limpa: o quadro de referência (``quadro_ref_s``) ou a mediana temporal de alguns
   quadros da maior exibição, que apaga o marcador;
2. painel: ``tab.painel.escolher`` nessa imagem; o ``roi`` dele dá o x no espaço do QUADRO;
3. ``reconhecer_linha`` no ``roi``: tokens com corda, casa e símbolo cru;
4. colunas (um acorde é uma coluna) e compasso, pelas barlines da tela.

Algarismo vai para ``notas``; o resto vai para ``nao_notas`` com a classe e o símbolo cru,
porque símbolo não se descarta. O tempo ainda não é medido aqui (Fase 5): cada nota sai com
``t_ini`` nulo e a tela declara o motivo.

Uso:
    python -m tab.video VIDEO --json saida.json [--imagem quadro|mediana] [--modelo CAMINHO]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

from tab import leitor
from tab.caminhos import MODELO_PADRAO, RAIZ, SAIDA, acervo
from tab.colunas import agrupar_colunas
from tab.digito import carregar
from tab.painel import PASSO_MAXIMO_PX, PASSO_MINIMO_PX, escolher
from tab.reconhecer import ALGARISMOS, carregar_modelo, reconhecer_linha
from tab.telas import Tela, telas

#: Identificador do formato, lido por ``tab.avaliar_video``.
ESQUEMA = "chorinho/video@1"

#: Maneiras de obter a imagem limpa de uma tela (T4.1).
IMAGENS = ("quadro", "mediana")

#: Imagem usada por padrão. Escolhida pela medição no ouro (ver ``ESTADO.md``, Fase 4).
IMAGEM_PADRAO = "quadro"

#: Quadros da mediana temporal, espalhados pela maior exibição da tela.
MEDIANA_QUADROS = 7

#: Motivo declarado enquanto o tempo por exibição não existe (Fase 5).
MOTIVO_TEMPO = "tempo por exibicao ainda nao implementado (Fase 5)"


def mediana_temporal(quadros: list[np.ndarray]) -> np.ndarray:
    """Mediana, pixel a pixel, de quadros do mesmo tamanho.

    O marcador anda, então cada posição dele fica acesa só num pedaço dos quadros, e a
    mediana a apaga. A tinta fixa (algarismo, corda) aparece em todos e fica.

    Args:
        quadros: quadros BGR de mesmas dimensões (ao menos um).

    Returns:
        O quadro mediano, em ``uint8``.

    Raises:
        ValueError: se a lista estiver vazia.
    """
    if not quadros:
        raise ValueError("a mediana temporal precisa de ao menos um quadro")
    return np.median(np.stack(quadros), axis=0).astype(np.uint8)


def tokens_do_quadro(r: dict, x0: int) -> list[dict]:
    """Tokens de uma linha lida, com o x no espaço do QUADRO.

    Args:
        r: resultado de ``reconhecer_linha``; o x vem em pixels do ``roi``.
        x0: deslocamento em x do ``roi`` no quadro (``Candidato.x0``).

    Returns:
        Um dict por token, na ordem de ``r["notas"]``, com ``corda``, ``classe``,
        ``x_quadro`` (borda esquerda), ``x_centro_quadro``, ``confianca``, ``tecnica``,
        e ``simbolo_cru`` e ``casa_recuperada`` quando houver.
    """
    tokens = []
    for n in r.get("notas", []):
        tokens.append(
            {
                "corda": int(n["corda"]),
                "classe": str(n["casa"]),
                "x_quadro": int(x0) + int(n["x"]),
                "x_centro_quadro": round(int(x0) + float(n["x_centro"]), 1),
                "confianca": float(n["confianca"]),
                "tecnica": n.get("tecnica"),
                "simbolo_cru": n.get("simbolo_cru"),
                "casa_recuperada": n.get("casa_recuperada"),
            }
        )
    return tokens


def colunas_do_quadro(tokens: list[dict], passo: float) -> list[int]:
    """Coluna de cada token da tela, numerada de 1 em diante, em ordem de x.

    Uma coluna são os tokens com o mesmo x (um acorde). Todos entram, algarismo ou não:
    a coluna é uma posição do marcador no quadro.

    Args:
        tokens: saída de ``tokens_do_quadro`` para uma tela.
        passo: passo entre cordas da tela, em px.

    Returns:
        A coluna de cada token, na mesma ordem de ``tokens``.
    """
    if not tokens:
        return []
    colunas = agrupar_colunas([t["x_quadro"] for t in tokens], passo)
    saida = [0] * len(tokens)
    for numero, coluna in enumerate(colunas, start=1):
        for i in coluna.indices:
            saida[i] = numero
    return saida


def compasso_de(x_quadro: int, barlines_x: list[int]) -> int:
    """Compasso, a partir de 1, de um x do quadro.

    Mesma regra do ``reconhecer.completar``: a primeira barline é o início da pauta.

    Args:
        x_quadro: x do token no quadro.
        barlines_x: barlines da tela, no quadro, em ordem crescente.

    Returns:
        O número do compasso.
    """
    return 1 + sum(1 for bx in barlines_x[1:] if bx < x_quadro)


def montar_v1(
    *,
    video: dict,
    gerado_por: dict,
    telas_v1: list[dict],
    notas: list[dict],
    nao_notas: list[dict],
) -> dict:
    """Monta o JSON v1 a partir do que já foi lido. Função pura.

    Args:
        video: bloco ``video`` (arquivo, canal, duracao_s, codec).
        gerado_por: bloco ``gerado_por`` (modelo, commit, imagem, em).
        telas_v1: uma entrada por tela (id, painel, passo, modo, barlines_x, exibicoes, tempo).
        notas: notas numéricas, com ``casa`` inteiro e ``t_ini`` (``None`` sem tempo).
        nao_notas: tokens que não são algarismo, com ``classe`` e o símbolo cru.

    Returns:
        O dicionário do esquema ``chorinho/video@1``, com ``resumo`` calculado daí.
    """
    instantes = {n["t_ini"] for n in notas if n["t_ini"] is not None}
    return {
        "esquema": ESQUEMA,
        "video": video,
        "gerado_por": gerado_por,
        "telas": telas_v1,
        "notas": notas,
        "nao_notas": nao_notas,
        "resumo": {
            "telas": len(telas_v1),
            "exibicoes": sum(len(t["exibicoes"]) for t in telas_v1),
            "notas": len(notas),
            "notas_com_tempo": sum(1 for n in notas if n["t_ini"] is not None),
            "instantes_distintos": len(instantes),
            "telas_sem_tempo": sum(1 for t in telas_v1 if not t["tempo"]["medido"]),
            "nao_notas": len(nao_notas),
        },
    }


def imagem_da_tela(video: str, tela: Tela, modo: str) -> np.ndarray | None:
    """Imagem limpa de uma tela, no modo pedido (T4.1).

    Args:
        video: caminho do vídeo.
        tela: tela de ``tab.telas``.
        modo: ``"quadro"`` (o ``quadro_ref_s``) ou ``"mediana"`` (mediana de quadros da
            maior exibição).

    Returns:
        O quadro BGR, ou ``None`` se o vídeo não der quadro no instante.

    Raises:
        ValueError: se ``modo`` não for conhecido.
    """
    if modo not in IMAGENS:
        raise ValueError(f"imagem desconhecida: {modo!r}")
    if modo == "quadro" or not tela.exibicoes:
        return leitor.quadro_em(video, tela.quadro_ref_s)
    k = max(
        range(len(tela.exibicoes)),
        key=lambda i: tela.exibicoes[i][1] - tela.exibicoes[i][0],
    )
    t0, t1 = tela.exibicoes[k]
    instantes = [
        t0 + (t1 - t0) * (i + 1) / (MEDIANA_QUADROS + 1) for i in range(MEDIANA_QUADROS)
    ]
    quadros = [q for t in instantes if (q := leitor.quadro_em(video, t)) is not None]
    return mediana_temporal(quadros) if quadros else None


def ler_tela(
    imagem: np.ndarray | None,
    tela: Tela,
    modelo,
    rotulos,
    dev,
    discriminador,
    dir_simbolos: str,
) -> tuple[dict, list[dict], list[dict]]:
    """Lê uma tela: painel, tokens, colunas e compasso, no espaço do quadro.

    Args:
        imagem: imagem limpa da tela (``None`` se o vídeo não deu quadro).
        tela: tela de ``tab.telas``.
        modelo: classificador de glifos carregado.
        rotulos: classes na ordem de saída do modelo.
        dev: dispositivo do modelo.
        discriminador: função "é algarismo?" (``tab.digito.carregar``).
        dir_simbolos: pasta dos recortes crus de símbolo.

    Returns:
        ``(entrada da tela, notas, nao_notas)``. Sem painel legível, as listas saem vazias
        e a entrada declara ``leitura`` com o motivo.
    """
    exibicoes = [{"t0": round(t0, 3), "t1": round(t1, 3)} for t0, t1 in tela.exibicoes]
    tempo = {"medido": False, "motivo": MOTIVO_TEMPO}
    m = escolher(imagem) if imagem is not None else None
    if m is None or not PASSO_MINIMO_PX <= m.passo <= PASSO_MAXIMO_PX:
        entrada = {
            "id": tela.id,
            "painel": list(tela.painel),
            "passo": None,
            "modo": tela.modo,
            "barlines_x": [],
            "exibicoes": exibicoes,
            "tempo": tempo,
            "leitura": "sem painel legível na imagem limpa",
        }
        return entrada, [], []

    altura, largura = m.roi.shape[:2]
    r = reconhecer_linha(
        m.roi,
        modelo,
        rotulos,
        dev,
        dir_simbolos=dir_simbolos,
        prefixo="",
        discriminador=discriminador,
    )
    tokens = tokens_do_quadro(r, m.x0)
    colunas = colunas_do_quadro(tokens, m.passo)
    barlines = [m.x0 + int(bx) for bx in r.get("barlines_x") or []]
    entrada = {
        "id": tela.id,
        "painel": [m.x0, m.y0, m.x0 + largura, m.y0 + altura],
        "passo": round(m.passo, 2),
        "modo": tela.modo,
        "barlines_x": barlines,
        "exibicoes": exibicoes,
        "tempo": tempo,
        "leitura": "ok",
    }
    notas: list[dict] = []
    nao_notas: list[dict] = []
    for tk, coluna in zip(tokens, colunas, strict=True):
        comum = {
            "tela": tela.id,
            "coluna": coluna,
            "corda": tk["corda"],
            "x_quadro": tk["x_quadro"],
            "x_centro_quadro": tk["x_centro_quadro"],
        }
        confianca = round(tk["confianca"], 3)
        if tk["classe"] in ALGARISMOS:
            notas.append(
                {
                    **comum,
                    "passagem": 1,
                    "compasso": compasso_de(tk["x_quadro"], barlines),
                    "casa": int(tk["classe"]),
                    "tecnica": None,
                    "confianca": confianca,
                    "t_ini": None,
                }
            )
            continue
        registro = {**comum, "classe": tk["classe"], "confianca": confianca}
        if tk["simbolo_cru"] is not None:
            registro["simbolo_cru"] = tk["simbolo_cru"]
        if tk["casa_recuperada"] is not None:
            registro["casa_recuperada"] = tk["casa_recuperada"]
        nao_notas.append(registro)
    return entrada, notas, nao_notas


def transcrever_video(
    caminho: str,
    modelo: str | Path = MODELO_PADRAO,
    imagem: str = IMAGEM_PADRAO,
    telas_lidas: list[Tela] | None = None,
) -> dict:
    """Lê todas as telas de um vídeo e devolve o JSON v1.

    Args:
        caminho: caminho do vídeo (sempre lido por ``tab.leitor``).
        modelo: classificador de glifos.
        imagem: ``"quadro"`` ou ``"mediana"`` (ver ``imagem_da_tela``).
        telas_lidas: telas já medidas por ``tab.telas``; se ``None``, o vídeo é segmentado
            aqui. Serve para medir variantes sem refazer a presença.

    Returns:
        O dicionário do esquema ``chorinho/video@1``.
    """
    rede, rotulos, dev = carregar_modelo(str(modelo))
    discriminador = carregar()
    dir_simbolos = str(SAIDA / "video" / _slug(caminho))
    lista = telas_lidas if telas_lidas is not None else telas(caminho)
    telas_v1: list[dict] = []
    notas: list[dict] = []
    nao_notas: list[dict] = []
    for tela in lista:
        img = imagem_da_tela(caminho, tela, imagem)
        entrada, nts, nns = ler_tela(
            img, tela, rede, rotulos, dev, discriminador, dir_simbolos
        )
        telas_v1.append(entrada)
        notas.extend(nts)
        nao_notas.extend(nns)
    info = leitor.info(caminho)
    arquivo = _relativo(caminho, acervo())
    partes = arquivo.split("/")
    return montar_v1(
        video={
            "arquivo": arquivo,
            "canal": partes[0] if len(partes) > 1 else None,
            "duracao_s": round(float(info.get("duracao_s") or 0.0), 2),
            "codec": info.get("codec"),
        },
        gerado_por={
            "modelo": _relativo(str(modelo), RAIZ),
            "commit": _commit(),
            "imagem": imagem,
            "em": datetime.now().isoformat(timespec="seconds"),
        },
        telas_v1=telas_v1,
        notas=notas,
        nao_notas=nao_notas,
    )


def _slug(caminho: str) -> str:
    """Nome de pasta seguro para o vídeo (usado nos recortes de símbolo).

    Args:
        caminho: caminho do vídeo.

    Returns:
        O nome do arquivo sem extensão, com caracteres especiais trocados por ``_``.
    """
    return re.sub(r"[^\w.-]+", "_", Path(caminho).stem).strip("_") or "video"


def _relativo(caminho: str, base: Path) -> str:
    """Caminho relativo a ``base``, ou só o nome do arquivo se estiver fora dela.

    Args:
        caminho: caminho a relativizar.
        base: pasta de referência.

    Returns:
        O caminho relativo, em barras ``/``.
    """
    try:
        return Path(caminho).resolve().relative_to(base.resolve()).as_posix()
    except OSError, ValueError:
        return Path(caminho).name


def _commit() -> str:
    """Hash curto do HEAD do git, ou ``desconhecido`` se não houver git.

    Returns:
        O hash curto do commit atual.
    """
    try:
        saida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except OSError, subprocess.SubprocessError:
        return "desconhecido"
    return saida.stdout.strip() or "desconhecido"


def _json_seguro(valor: object) -> object:
    """Converte tipos numpy que o ``json`` não serializa.

    Args:
        valor: objeto que o ``json`` não sabe escrever.

    Returns:
        O equivalente nativo do Python.

    Raises:
        TypeError: se o tipo não for conhecido.
    """
    if isinstance(valor, np.generic):
        return valor.item()
    if isinstance(valor, np.ndarray):
        return valor.tolist()
    raise TypeError(f"não serializável: {type(valor).__name__}")


def main() -> int:
    """CLI: ``python -m tab.video VIDEO --json saida.json``.

    Returns:
        ``0`` ao gravar o JSON.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video")
    ap.add_argument("--json", required=True, help="onde gravar o JSON v1")
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    ap.add_argument("--imagem", choices=IMAGENS, default=IMAGEM_PADRAO)
    args = ap.parse_args()
    dados = transcrever_video(args.video, modelo=args.modelo, imagem=args.imagem)
    destino = Path(args.json)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1, default=_json_seguro),
        encoding="utf-8",
    )
    r = dados["resumo"]
    gerado = dados["gerado_por"]
    print(
        f"modelo {gerado['modelo']} | commit {gerado['commit']} | imagem {gerado['imagem']}"
    )
    print(
        f"{r['telas']} telas, {r['notas']} notas, {r['nao_notas']} nao-notas "
        f"-> {destino}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
