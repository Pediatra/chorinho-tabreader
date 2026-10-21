"""Tempo por quadro do RTMPose Wholebody na GPU, com checagem de pontos contra a CPU (M1).

Reusa de ``sonda_rtm.py``: ``rodar_wb`` (detector e pose em chamadas separadas),
``caminho_quadro`` (PNG no cache) e as constantes de faixa. Compara os pontos das mãos
com ``sonda_rtm.json`` (CPU), mesmos 20 primeiros quadros do rótulo do piloto.

Roda dentro do container ``chorinho-maos-rtm-gpu:dev``::

    python data/saida/maos/m1/tempo_gpu.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from rtmlib import Wholebody

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sonda_rtm as sonda  # noqa: E402

RAIZ = Path("/app")
ROTULO = RAIZ / "data/saida/maos/rotulo_agente_piloto.json"
CENSO = RAIZ / "data/saida/maos/piloto_c0.3_b2.jsonl"
REFERENCIA_CPU = RAIZ / "data/saida/maos/m1/sonda_rtm.json"
SAIDA = RAIZ / "data/saida/maos/m1/tempo_gpu.json"

N_QUADROS = 20
N_AQUECER = 3
N_VOLTAS = 2


def memoria_gpu_mib() -> int | None:
    """Memória de GPU usada, em MiB, pelo ``nvidia-smi`` (None se indisponível).

    Returns:
        Memória usada em MiB, ou None quando o ``nvidia-smi`` não responde.
    """
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return int(r.stdout.strip().splitlines()[0])


class Amostrador:
    """Amostra a memória da GPU em segundo plano e guarda o máximo visto."""

    def __init__(self, intervalo_s: float = 0.2) -> None:
        """Cria o amostrador (ainda não inicia).

        Args:
            intervalo_s: intervalo entre amostras, em segundos.
        """
        self.intervalo_s = intervalo_s
        self.maximo: int | None = None
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._laco, daemon=True)

    def _laco(self) -> None:
        """Loop da thread: amostra até ser parado."""
        while not self._parar.is_set():
            v = memoria_gpu_mib()
            if v is not None and (self.maximo is None or v > self.maximo):
                self.maximo = v
            self._parar.wait(self.intervalo_s)

    def iniciar(self) -> None:
        """Começa a amostrar."""
        self._thread.start()

    def parar(self) -> int | None:
        """Para a amostragem.

        Returns:
            Máximo de memória usada observado, em MiB.
        """
        self._parar.set()
        self._thread.join()
        return self.maximo


def carregar_quadros() -> list[dict]:
    """Os primeiros ``N_QUADROS`` quadros do rótulo, com a imagem lida do cache.

    Returns:
        Lista de dicionários com ``rot``, ``png`` e ``img`` (BGR).
    """
    rotulos = json.loads(ROTULO.read_text(encoding="utf-8"))["rotulos"][:N_QUADROS]
    censo = {}
    for linha in CENSO.read_text(encoding="utf-8").splitlines():
        reg = json.loads(linha)
        censo[reg["arquivo"]] = reg
    itens = []
    for rot in rotulos:
        arq = sonda.caminho_quadro(censo[rot["arquivo"]]["chave"], rot["quadro"])
        img = cv2.imread(str(arq))
        if img is None:
            raise SystemExit(f"PNG do quadro nao encontrado ou ilegivel: {arq}")
        itens.append({"rot": rot, "png": str(arq), "img": img})
    return itens


def diferencas(gpu: dict, cpu: dict) -> dict:
    """Diferenças de pontos (px) entre o resultado da GPU e o da CPU de um quadro.

    Pessoas são pareadas por ordem. Mede a distância euclidiana dos 21 pontos de cada
    mão e a diferença da média de score da mão.

    Args:
        gpu: saída de ``sonda.rodar_wb`` na GPU (campo ``pessoas``).
        cpu: mesmo campo, lido de ``sonda_rtm.json``.

    Returns:
        ``pessoas_gpu``, ``pessoas_cpu``, ``dist_px`` (lista de distâncias) e
        ``dif_score`` (lista de diferenças de média de score).
    """
    res = {
        "pessoas_gpu": len(gpu["pessoas"]),
        "pessoas_cpu": len(cpu["pessoas"]),
        "dist_px": [],
        "dif_score": [],
        "detalhe": [],
    }
    for pessoa, (a, b) in enumerate(zip(gpu["pessoas"], cpu["pessoas"])):
        for lado in ("esquerda", "direita"):
            pa = np.array([p[:2] for p in a[lado]["pts"]], dtype=float)
            pb = np.array([p[:2] for p in b[lado]["pts"]], dtype=float)
            dist = np.linalg.norm(pa - pb, axis=1).tolist()
            res["dist_px"].extend(dist)
            res["dif_score"].append(abs(a[lado]["media"] - b[lado]["media"]))
            for k, d_k in enumerate(dist):
                res["detalhe"].append(
                    {
                        "pessoa": pessoa,
                        "lado": lado,
                        "ponto": k,
                        "dist_px": d_k,
                        "score_gpu": a[lado]["pts"][k][2],
                        "score_cpu": b[lado]["pts"][k][2],
                        "gpu_xy": a[lado]["pts"][k][:2],
                        "cpu_xy": b[lado]["pts"][k][:2],
                    }
                )
    return res


def main() -> None:
    """Confere os providers, aquece, mede duas voltas e compara com a CPU."""
    itens = carregar_quadros()
    print(f"{len(itens)} quadros lidos do cache (BGR).", flush=True)

    mem_antes_modelo = memoria_gpu_mib()
    inicio = time.perf_counter()
    wb = Wholebody(backend="onnxruntime", device="cuda", to_openpose=False)
    print(f"modelos carregados em {time.perf_counter() - inicio:.1f} s", flush=True)
    mem_depois_modelo = memoria_gpu_mib()

    provedores = {
        "det_pessoa": wb.det_model.session.get_providers(),
        "pose": wb.pose_model.session.get_providers(),
    }
    print("providers da sessao (get_providers):", provedores, flush=True)
    for nome, prov in provedores.items():
        if not prov or prov[0] != "CUDAExecutionProvider":
            raise SystemExit(f"sessao {nome} NAO esta na GPU: {prov}")

    print(
        f"memoria GPU (MiB): antes dos modelos {mem_antes_modelo}, "
        f"depois dos modelos {mem_depois_modelo}",
        flush=True,
    )

    # Aquecimento: não medido, não gravado.
    for it in itens[:N_AQUECER]:
        sonda.rodar_wb(wb, it["img"])

    amostrador = Amostrador()
    amostrador.iniciar()
    tempos_det_pose: list[float] = []
    tempos_wall: list[float] = []
    ultima_volta: list[dict] = []
    for volta in range(1, N_VOLTAS + 1):
        ini_volta = time.perf_counter()
        saidas = []
        for it in itens:
            r = sonda.rodar_wb(wb, it["img"])
            saidas.append(r)
            tempos_det_pose.append(r["tempo_s"])
        tempos_wall.append((time.perf_counter() - ini_volta) / len(itens))
        ultima_volta = saidas
        print(
            f"volta {volta}: media det+pose {np.mean([r['tempo_s'] for r in saidas]):.3f} s/quadro, "
            f"wall (sem leitura de PNG) {tempos_wall[-1]:.3f} s/quadro",
            flush=True,
        )
    maximo_gpu = amostrador.parar()

    # Comparação com a CPU, mesmos quadros (ordem do rótulo).
    referencia = json.loads(REFERENCIA_CPU.read_text(encoding="utf-8"))["quadros"]
    ref_por_chave = {(q["arquivo"], q["quadro"]): q for q in referencia}
    todas_dist: list[float] = []
    todas_score: list[float] = []
    todos_detalhes: list[dict] = []
    dif_pessoas = []
    quadros_sem_ref = 0
    for it, r in zip(itens, ultima_volta):
        q_cpu = ref_por_chave.get((it["rot"]["arquivo"], it["rot"]["quadro"]))
        if q_cpu is None:
            quadros_sem_ref += 1
            continue
        d = diferencas(r, q_cpu["wholebody"])
        dif_pessoas.append(
            {"n": it["rot"]["n"], "pessoas_gpu": d["pessoas_gpu"], "pessoas_cpu": d["pessoas_cpu"]}
        )
        todas_dist.extend(d["dist_px"])
        todas_score.extend(d["dif_score"])
        for det in d["detalhe"]:
            det["n"] = it["rot"]["n"]
            det["quadro"] = it["rot"]["quadro"]
            todos_detalhes.append(det)

    dist = np.array(todas_dist) if todas_dist else np.array([np.nan])
    score = np.array(todas_score) if todas_score else np.array([np.nan])
    tempo_det_pose = float(np.mean(tempos_det_pose))
    resumo = {
        "quadros": len(itens),
        "voltas": N_VOLTAS,
        "aquecimento_quadros": N_AQUECER,
        "tempo_medio_det_pose_s": tempo_det_pose,
        "tempo_medio_wall_por_quadro_s_por_volta": tempos_wall,
        "pontos_maos_comparados": int(len(todas_dist)),
        "dist_px_max": float(np.nanmax(dist)),
        "dist_px_media": float(np.nanmean(dist)),
        "dif_media_score_max": float(np.nanmax(score)),
        "dif_media_score_media": float(np.nanmean(score)),
        "quadros_sem_referencia_cpu": quadros_sem_ref,
        "pessoas_por_quadro": dif_pessoas,
        "maiores_desvios": sorted(todos_detalhes, key=lambda x: -x["dist_px"])[:15],
        "pontos_acima_de_2px": int(sum(1 for x in todos_detalhes if x["dist_px"] > 2.0)),
        "memoria_gpu_mib": {
            "antes_modelos": mem_antes_modelo,
            "depois_modelos": mem_depois_modelo,
            "maximo_durante_medicao": maximo_gpu,
        },
        "providers": provedores,
    }
    SAIDA.write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")

    print()
    print(f"tempo medio det+pose por quadro na GPU ({N_VOLTAS} voltas x {len(itens)} quadros): "
          f"{tempo_det_pose:.3f} s")
    print(f"wall por quadro, por volta: {[round(t, 3) for t in tempos_wall]}")
    print(
        f"diferenca de pontos das maos vs CPU: max {resumo['dist_px_max']:.3f} px, "
        f"media {resumo['dist_px_media']:.4f} px ({resumo['pontos_maos_comparados']} pontos)"
    )
    print(
        f"diferenca da media de score da mao: max {resumo['dif_media_score_max']:.5f}, "
        f"media {resumo['dif_media_score_media']:.6f}"
    )
    print("maiores desvios (n, pessoa, lado, ponto, px, score GPU/CPU):")
    for x in resumo["maiores_desvios"][:8]:
        print(
            f"  n={x['n']} pessoa={x['pessoa']} {x['lado']} ponto={x['ponto']} "
            f"{x['dist_px']:.2f} px, score {x['score_gpu']:.3f}/{x['score_cpu']:.3f}"
        )
    print(f"pontos com desvio > 2 px: {resumo['pontos_acima_de_2px']} de {len(todas_dist)}")
    print(f"pessoas por quadro (GPU x CPU): {[(p['pessoas_gpu'], p['pessoas_cpu']) for p in dif_pessoas]}")
    print(f"memoria GPU maxima durante a medicao (nvidia-smi, total da GPU): {maximo_gpu} MiB")
    print(f"resumo gravado em {SAIDA}", flush=True)


if __name__ == "__main__":
    main()
