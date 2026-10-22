"""Pontas dos dedos em cada instante das notas pisadas (M3c, passo 1).

Para cada instante ``t_ini`` distinto de uma nota pisada do MVP (casa maior que 0),
extrai o quadro do vídeo com o ffmpeg e roda o ``DetectorMaos`` (GPU). Grava TODAS as
mãos do quadro (lado, origem, caixa, média, score por ponto e os 21 pontos), sem
filtrar: a escolha da mão e das pontas fica para a etapa de calibração
(``tab.maos_calibrar_por_notas``).

Não usa o gabarito de dedos: o conjunto de instantes vem só do MVP. Quem quiser medir
com os instantes do gabarito excluídos filtra no passo seguinte, pelo campo ``notas``.

Fica fora do gate: precisa de GPU e do acervo montado.

Uso::

    python -m tab.maos_pontas_notas --dispositivo cuda
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tab.comum.caminhos import MAOS_M3, MVP
from tab.maos.detector import DetectorMaos
from tab.maos.visao_dedos import VIDEO_PADRAO, quadro_bgr

#: Pasta de saída do passo 1 (visível no host).
SAIDA_PADRAO = MAOS_M3.parent / "m3c" / "pontas_mvp.json"

#: Quantos instantes entre gravações parciais (evita perder a corrida num erro).
INTERVALO_GRAVACAO = 50


def _numero(valor: Any) -> float | None:
    """Converte um escalar (inclusive numpy) em ``float`` para o JSON.

    Args:
        valor: número, ``numpy`` escalar ou ``None``.

    Returns:
        ``float`` arredondado a 3 casas, ou ``None``.
    """
    if valor is None:
        return None
    return round(float(valor), 3)


def mao_para_registro(mao: dict[str, Any]) -> dict[str, Any]:
    """Converte uma mão do ``DetectorMaos`` para um registro serializável.

    Args:
        mao: mão de ``combinar`` com ``lado``, ``origem``, ``caixa``, ``pts``,
            ``scores`` (ou None) e ``media`` (ou None).

    Returns:
        Dicionário com ``lado``, ``origem``, ``caixa``, ``media``, ``scores`` e ``pts``.
    """
    scores = mao.get("scores")
    return {
        "lado": mao["lado"],
        "origem": mao["origem"],
        "caixa": [_numero(v) for v in mao["caixa"]],
        "media": _numero(mao.get("media")),
        "scores": None if scores is None else [_numero(s) for s in scores],
        "pts": [[_numero(x), _numero(y)] for x, y in mao["pts"]],
    }


def instantes_das_pisadas(mvp: list[dict[str, Any]]) -> dict[float, list[dict]]:
    """Agrupa as notas pisadas do MVP pelo instante ``t_ini`` (3 casas).

    Args:
        mvp: lista ``notas`` do MVP, com ``corda``, ``casa`` e ``t_ini``.

    Returns:
        ``t_ini`` -> lista das notas pisadas naquele instante, com ``indice_mvp``,
        ``corda`` e ``casa``. Instantes em ordem crescente na inserção.
    """
    grupos: dict[float, list[dict]] = {}
    for indice, nota in enumerate(mvp):
        t = nota.get("t_ini")
        if t is None or nota["casa"] <= 0:
            continue
        grupos.setdefault(round(float(t), 3), []).append(
            {"indice_mvp": indice, "corda": nota["corda"], "casa": nota["casa"]}
        )
    return dict(sorted(grupos.items()))


def gravar(
    saida: Path,
    video: Path,
    registros: list[dict[str, Any]],
    deslocamento: float = 0.0,
) -> None:
    """Grava o JSON de pontas (sobrescreve a cada chamada).

    Args:
        saida: arquivo de destino (a pasta é criada se faltar).
        video: vídeo de origem, gravado para conferência.
        registros: um por instante, já serializado.
        deslocamento: segundos somados ao ``t_ini`` para achar o quadro (0 = o próprio).
    """
    saida.parent.mkdir(parents=True, exist_ok=True)
    dados = {
        "video": str(video),
        "gerado_por": "tab.maos_pontas_notas",
        "deslocamento": deslocamento,
        "rect_tab": None,
        "instantes": registros,
    }
    saida.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    """Roda o detector nos instantes das notas pisadas e grava todas as mãos."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--video", type=Path, default=VIDEO_PADRAO)
    parser.add_argument("--mvp", type=Path, default=MVP)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--dispositivo", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument(
        "--deslocamento",
        type=float,
        default=0.0,
        help="o quadro lido fica em t_ini + deslocamento (ex.: -0.1 para o voto)",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=0,
        help="só os N primeiros instantes (0 = todos); para teste",
    )
    args = parser.parse_args()

    mvp = json.loads(args.mvp.read_text(encoding="utf-8"))["notas"]
    instantes = instantes_das_pisadas(mvp)
    chaves = list(instantes)
    if args.limite:
        chaves = chaves[: args.limite]
    print(f"{len(chaves)} instantes com nota pisada", flush=True)

    det = DetectorMaos(args.dispositivo)
    registros: list[dict[str, Any]] = []
    for i, t in enumerate(chaves, start=1):
        t_quadro = round(max(t + args.deslocamento, 0.0), 3)
        bgr = quadro_bgr(args.video, t_quadro)
        achado = det.detectar(bgr, None)
        registros.append(
            {
                "t_ini": t,
                "t_quadro": t_quadro,
                "notas": instantes[t],
                "maos": [mao_para_registro(m) for m in achado["maos"]],
            }
        )
        if i % INTERVALO_GRAVACAO == 0 or i == len(chaves):
            gravar(args.saida, args.video, registros, args.deslocamento)
            print(f"{i}/{len(chaves)} instantes gravados", flush=True)
    sem_mao = sum(1 for r in registros if not r["maos"])
    print(f"sem nenhuma mão: {sem_mao}/{len(registros)}; saída em {args.saida}")


if __name__ == "__main__":
    main()
