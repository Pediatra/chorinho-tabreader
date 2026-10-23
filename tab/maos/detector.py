"""Detector das mãos (M1): RTMPose Wholebody na GPU, com o MediaPipe como complemento.

Por quadro, o Wholebody (YOLOX-m para a pessoa e RTMW-DW-X-L para a pose, na rtmlib) é a
base, e o MediaPipe (censo M0, ``tab.maos_censo``) entra com as mãos que o Wholebody não
acha, ex.: a mão do braço num close do ``sky guitar``. As regras de combinação estão em
``tab.maos_combinar``, que é puro e tem teste no gate; este módulo só carrega os modelos e
roda.

Decisões deste módulo:

- O detector de pessoa e a pose são chamados em SEPARADO, como na validação. Chamar o
  ``Wholebody.__call__`` com detector vazio roda a pose no quadro inteiro e inventa pessoa.
- A imagem vai em BGR (o padrão da rtmlib). A validação mostrou 0 a 1 quadro de diferença
  entre BGR e RGB; o produto usa BGR. O MediaPipe converte para RGB sozinho.
- Só GPU no produto. GPU e CPU dão pontos um pouco diferentes (média 0,5 px, alguns até 21
  px), então a trava de CUDA (``_travar_cuda``) aborta se a sessão não estiver na GPU.

Uso::

    python -m tab.maos_detector --conjunto data/saida/maos/m1/validacao_conjunto.json \\
        --censo data/saida/censo/censo_cache.jsonl \\
        --saida data/saida/maos/m1/detector_validacao.jsonl \\
        --rotulo data/saida/maos/m1/rotulo_agente_validacao.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from rtmlib import Wholebody

from tab.comum.cache import ModoCache, caminho_do_quadro, ler_quadro, pasta_do_video
from tab.maos.censo import BLOCOS_POR_LADO, blocos, criar_detectores, detectar_maos
from tab.maos.combinar import afirmacoes, combinar
from tab.maos.tabela import dentro_da_tab, fundir_maos

#: Faixas do COCO-WholeBody sem ``to_openpose``: mão esquerda 91-111, direita 112-132.
FAIXA_ESQ = slice(91, 112)
FAIXA_DIR = slice(112, 133)
#: Ombros, cotovelos e pulsos (COCO 5–10), para o ``corpo`` da base (decisão 1007).
FAIXA_CORPO = slice(5, 11)

#: Bibliotecas CUDA do torch da imagem base, sem as quais o ONNX Runtime cai em CPU.
LD_LIBRARY_PATH_ESPERADO = (
    "/opt/venv/lib/python3.14/site-packages/nvidia/cu13/lib:"
    "/opt/venv/lib/python3.14/site-packages/nvidia/cudnn/lib"
)

#: Sessões que a trava confere: o YOLOX (pessoa) e o RTMPose (pose) do Wholebody.
_SESSOES = (("YOLOX (pessoa)", "det_model"), ("RTMPose (pose)", "pose_model"))


def _mao_da_pose(kp: np.ndarray, sc: np.ndarray) -> dict:
    """Uma mão do Wholebody: caixa dos 21 pontos, média dos scores e os pontos.

    Args:
        kp: coordenadas ``(21, 2)``.
        sc: scores ``(21,)``.

    Returns:
        ``caixa`` (x0, y0, x1, y1), ``media`` (sem arredondar) e ``pts`` ``[x, y, score]``.
    """
    caixa = [
        round(float(kp[:, 0].min()), 1),
        round(float(kp[:, 1].min()), 1),
        round(float(kp[:, 0].max()), 1),
        round(float(kp[:, 1].max()), 1),
    ]
    pts = [
        [round(float(x), 1), round(float(y), 1), float(s)]
        for (x, y), s in zip(kp, sc, strict=True)
    ]
    return {"caixa": caixa, "media": float(sc.mean()), "pts": pts}


def _travar_cuda(wb: Wholebody) -> None:
    """Aborta se alguma sessão do Wholebody não estiver na GPU.

    A rtmlib passa ``providers=["CUDAExecutionProvider"]`` ao ``ort.InferenceSession``
    (``rtmlib/tools/base.py``, linhas 85-86). Sem as bibliotecas CUDA no caminho, o ONNX
    Runtime NÃO falha: troca para ``CPUExecutionProvider`` em silêncio. A conferência é
    o primeiro provider de cada sessão (``sessao.get_providers()[0]``).

    Args:
        wb: ``rtmlib.Wholebody`` já criado; as sessões são ``det_model.session`` e
            ``pose_model.session``.

    Raises:
        RuntimeError: se alguma sessão não tiver ``CUDAExecutionProvider`` em primeiro.
    """
    for nome, atributo in _SESSOES:
        sessao = getattr(wb, atributo).session
        primeiro = sessao.get_providers()[0]
        if primeiro != "CUDAExecutionProvider":
            raise RuntimeError(
                f"{nome} não está na GPU: primeiro provider é {primeiro}. "
                "O ONNX Runtime caiu em CPU sem avisar. Confira se o LD_LIBRARY_PATH "
                f"inclui {LD_LIBRARY_PATH_ESPERADO} (valor atual: "
                f"{os.environ.get('LD_LIBRARY_PATH')!r}) e se o container recebeu a "
                "GPU (--device nvidia.com/gpu=all)."
            )


class DetectorMaos:
    """Mãos de um quadro: Wholebody na GPU, com o MediaPipe completando.

    Attributes:
        dispositivo: ``cuda`` (produto) ou ``cpu`` (só para teste de diagnóstico).
        wb: ``rtmlib.Wholebody`` (YOLOX-m humanart + RTMW-DW-X-L, modo balanced).
    """

    def __init__(self, dispositivo: str = "cuda") -> None:
        """Carrega os modelos do Wholebody e do MediaPipe.

        Args:
            dispositivo: ``cuda`` ou ``cpu``. Com ``cuda``, a trava confere a GPU.

        Raises:
            RuntimeError: com ``cuda``, se alguma sessão ONNX não ficou na GPU.
        """
        self.dispositivo = dispositivo
        self.wb = Wholebody(
            backend="onnxruntime", device=dispositivo, to_openpose=False
        )
        if dispositivo == "cuda":
            _travar_cuda(self.wb)
        criar_detectores()

    def _pessoas_wb(self, bgr: np.ndarray) -> list[dict]:
        """Pessoas e mãos do Wholebody, com detector e pose em chamadas separadas.

        Args:
            bgr: quadro inteiro em BGR.

        Returns:
            Uma entrada por pessoa: ``caixa``, ``esquerda`` e ``direita`` (cada uma com
            ``caixa``, ``media`` e ``pts``) e ``corpo`` (ombros, cotovelos e pulsos, COCO
            5–10, ``[x, y, score]``). Vazia se não há pessoa (a pose não roda).
        """
        caixas = np.asarray(self.wb.det_model(bgr), dtype=float).reshape(-1, 4)
        if len(caixas) == 0:
            return []
        kp, sc = self.wb.pose_model(bgr, bboxes=caixas)
        return [
            {
                "caixa": [round(float(v), 1) for v in c],
                "esquerda": _mao_da_pose(k[FAIXA_ESQ], s[FAIXA_ESQ]),
                "direita": _mao_da_pose(k[FAIXA_DIR], s[FAIXA_DIR]),
                "corpo": [
                    [float(x), float(y), float(v)]
                    for (x, y), v in zip(k[FAIXA_CORPO], s[FAIXA_CORPO], strict=True)
                ],
            }
            for c, k, s in zip(caixas, kp, sc, strict=True)
        ]

    def _maos_mediapipe(
        self, bgr: np.ndarray, rect_tab: list[int] | None
    ) -> list[dict]:
        """Mãos do MediaPipe pelo mesmo caminho do censo: quadro inteiro e blocos.

        Args:
            bgr: quadro inteiro em BGR.
            rect_tab: caixa do painel da tablatura, ou None.

        Returns:
            Mãos fundidas, com ``na_tab`` marcado pelo centro da caixa.
        """
        altura, largura = bgr.shape[:2]
        maos = detectar_maos(bgr, 0, 0, "inteiro")
        for x0, y0, x1, y1 in blocos(largura, altura, BLOCOS_POR_LADO):
            maos += detectar_maos(bgr[y0:y1, x0:x1], x0, y0, "bloco")
        maos = fundir_maos(maos)
        for m in maos:
            m["na_tab"] = dentro_da_tab(m["caixa"], rect_tab)
        return maos

    def detectar(self, bgr: np.ndarray, rect_tab: list[int] | None) -> dict:
        """Mãos de um quadro, com as afirmações do quadro.

        Args:
            bgr: quadro inteiro em BGR.
            rect_tab: caixa do painel da tablatura (``[x0, y0, x1, y1]``), ou None.

        Returns:
            ``pessoas_wb`` e ``maos_mp`` (os dois detectores, crus), ``maos`` (saída de
            ``combinar``) e ``afirma`` (``afirmacoes`` de ``maos``).
        """
        pessoas = self._pessoas_wb(bgr)
        maos_mp = self._maos_mediapipe(bgr, rect_tab)
        maos = combinar(pessoas, maos_mp)
        return {
            "pessoas_wb": pessoas,
            "maos_mp": maos_mp,
            "maos": maos,
            "afirma": afirmacoes(maos),
        }


def _indexar_censo(caminho: Path, chaves: set[str]) -> dict[str, dict]:
    """Registros do censo de presença para as chaves pedidas.

    Args:
        caminho: ``censo_cache.jsonl``.
        chaves: chaves dos quadros a detectar.

    Returns:
        Registro por chave (só as pedidas).

    Raises:
        SystemExit: se alguma chave pedida não está no censo.
    """
    achados: dict[str, dict] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        registro = json.loads(linha)
        if registro["chave"] in chaves:
            achados[registro["chave"]] = registro
    faltam = chaves - achados.keys()
    if faltam:
        raise SystemExit(f"{len(faltam)} chave(s) do conjunto não estão no censo")
    return achados


def _ler_quadro_do_cache(chave: str, quadro: int) -> np.ndarray:
    """Quadro de presença do cache, em BGR.

    Args:
        chave: chave de retomada do vídeo.
        quadro: índice ``i`` do quadro de presença.

    Returns:
        Quadro BGR.
    """
    modo = ModoCache()
    arq = caminho_do_quadro(
        pasta_do_video(chave, modo), f"presenca_{quadro:02d}", modo.formato
    )
    return ler_quadro(arq)


def _tabela_de_acertos(registros: list[dict], rotulo: dict) -> None:
    """Imprime a tabela de acerto contra o rótulo, com os ids errados.

    Conta: uma mão ``incerto`` NÃO é E nem D (é "não sei"). Um lado com rótulo ``null`` fica
    fora da conta. ``quadro certo`` exige que cada lado com rótulo bata com a afirmação
    (lado ``incerto`` não bate com rótulo 1, e não é falso com rótulo 0).

    Args:
        registros: linhas gravadas pelo detector, com ``id`` e ``afirma``.
        rotulo: conteúdo do JSON de rótulo (``rotulos``: id -> lado -> 0, 1 ou null).
    """
    visiveis = {"esquerda": 0, "direita": 0}
    achadas = {"esquerda": 0, "direita": 0}
    falsas = certos = total = 0
    errados: list[str] = []
    incertos: list[str] = []
    for reg in registros:
        rot = rotulo["rotulos"].get(reg["id"])
        if rot is None:
            continue
        total += 1
        afirma = reg["afirma"]
        if afirma["incerto"]:
            incertos.append(reg["id"])
        ok = True
        for lado in ("esquerda", "direita"):
            v = rot[lado]
            if v is None:
                continue
            a = afirma[lado]
            if v:
                visiveis[lado] += 1
                achadas[lado] += int(a)
            elif a:
                falsas += 1
            ok &= a == bool(v)
        certos += int(ok)
        if not ok:
            errados.append(reg["id"])
    print()
    print(
        "| detector | quadro certo | mão esquerda achada | mão direita achada | falsas |"
    )
    print("| --- | --- | --- | --- | --- |")
    print(
        f"| Wholebody + MediaPipe | {certos}/{total} | "
        f"E: {achadas['esquerda']}/{visiveis['esquerda']} | "
        f"D: {achadas['direita']}/{visiveis['direita']} | {falsas} |"
    )
    print(f"quadros com mão incerto: {len(incertos)} {incertos or ''}")
    print(f"quadros errados: {len(errados)} {errados or ''}")


def main() -> int:
    """CLI do detector das mãos: roda o conjunto e grava uma linha por quadro.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--conjunto", type=Path, required=True)
    ap.add_argument("--censo", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--rotulo", type=Path)
    ap.add_argument("--dispositivo", choices=["cuda", "cpu"], default="cuda")
    args = ap.parse_args()

    conjunto = json.loads(args.conjunto.read_text(encoding="utf-8"))
    censo = _indexar_censo(args.censo, {it["chave"] for it in conjunto})
    det = DetectorMaos(args.dispositivo)

    registros: list[dict] = []
    tempos: list[float] = []
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", encoding="utf-8") as saida:
        for it in conjunto:
            rect = censo[it["chave"]]["instantes"][it["quadro"]]["rect"]
            bgr = _ler_quadro_do_cache(it["chave"], it["quadro"])
            inicio = time.perf_counter()
            achado = det.detectar(bgr, rect)
            tempos.append(time.perf_counter() - inicio)
            registro = {
                "id": it["id"],
                "grupo": it["grupo"],
                "canal": it["canal"],
                "chave": it["chave"],
                "quadro": it["quadro"],
                "rect": rect,
                **achado,
            }
            registros.append(registro)
            saida.write(json.dumps(registro, ensure_ascii=False) + "\n")

    print(
        f"{len(registros)} quadros em {args.dispositivo}, tempo médio "
        f"{np.mean(tempos):.3f} s por quadro (detector + MediaPipe, sem ler o PNG)"
    )
    if args.rotulo:
        rotulo = json.loads(args.rotulo.read_text(encoding="utf-8"))
        _tabela_de_acertos(registros, rotulo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
