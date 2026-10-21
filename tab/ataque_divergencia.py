"""Leitura do modelo nota a nota, para a ferramenta sinalizar onde ele discorda do dono.

Lê cada tela da pasta da ferramenta (``tab.ouro_video``) com o detector e a faixa de
``tab.ataque_rotulo``, pareia com as notas do arquivo do ataque e grava
``<pasta>/modelo_ataque.json``. As divergências entre o dono e o modelo
(``divergencia``):

- "nao_viu": o dono diz que a nota não é atacada e o modelo lê "sim" (não viu o símbolo);
- "viu_mais": o dono diz "sim" e o modelo lê "nao" (vê um símbolo que talvez falte marcar);
- "duvida": o dono diz "sim" e o modelo fica no "nao_sei".

A página mostra só o "nao_viu" (o pedido do dono: sinalizar o símbolo que o modelo não
identificou); os outros dois saem na contagem do terminal. O arquivo é só leitura do modelo:
não muda o ouro nem o arquivo do ataque.

Uso (container)::

    python -m tab.ataque_divergencia --pasta data/saida/t83/ferramenta \\
        --ataque data/saida/tab_rotulo/r2/conferir_t83/ataque_t83.json
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tab import ataque_rotulo, caminhos, detector_tab
from tab.ataque_base import parear
from tab.ataque_r4 import ler_tela
from tab.gpu import trava_gpu

#: Nome do arquivo gravado na pasta da ferramenta (a página o busca, se existir).
ARQUIVO = "modelo_ataque.json"


def divergencia(ataque_dono: str | None, ataque_modelo: str | None) -> str | None:
    """Tipo da divergência entre o dono e o modelo numa nota.

    Args:
        ataque_dono: "sim", "nao" ou "nao_sei" do arquivo do ataque.
        ataque_modelo: "sim", "nao" ou "nao_sei" do modelo; None se não leu a nota.

    Returns:
        "nao_viu", "viu_mais", "duvida" ou None (sem divergência a mostrar).
    """
    if ataque_dono == "nao" and ataque_modelo == "sim":
        return "nao_viu"
    if ataque_dono == "sim" and ataque_modelo == "nao":
        return "viu_mais"
    if ataque_dono == "sim" and ataque_modelo == "nao_sei":
        return "duvida"
    return None


def onde_ler(pasta: Path) -> dict[int, tuple[Path, float]]:
    """Vídeo e instante de cada tela da pasta da ferramenta.

    Usa ``indice.json`` (lotes de vários vídeos, como a T8.3) se existir; senão o
    ``video`` do ``pre.json`` e o ``quadro_ref_s`` de cada tela.

    Args:
        pasta: pasta da ferramenta.

    Returns:
        Mapa tela -> (caminho do vídeo, instante em s).
    """
    indice = pasta / "indice.json"
    if indice.exists():
        return {
            int(r["id"]): (caminhos.acervo() / r["video"], float(r["t"]))
            for r in json.loads(indice.read_text(encoding="utf-8"))
        }
    pre = json.loads((pasta / "pre.json").read_text(encoding="utf-8"))
    video = Path(pre["video"])
    if not video.is_absolute():
        video = caminhos.acervo() / video
    return {int(t["id"]): (video, float(t["quadro_ref_s"])) for t in pre["telas"]}


def ler_notas(
    modelo: detector_tab.DetectorTab, video: Path, t_s: float, notas: list[dict]
) -> dict[str, dict]:
    """A leitura do modelo em cada nota do arquivo do ataque de uma tela.

    Args:
        modelo: detector carregado.
        video: vídeo da tela.
        t_s: instante do quadro.
        notas: notas da tela no arquivo do ataque (``nota``, ``corda``,
            ``x_centro_quadro``).

    Returns:
        Chave da nota -> ``{"modelo", "motivo", "p"}``; nota não lida fica de fora.
    """
    pred, passo = ler_tela(modelo, video, t_s)
    if not pred:
        return {}
    rotulos = ataque_rotulo.rotular(pred, passo)
    validas = [n for n in notas if n.get("x_centro_quadro") is not None]
    saida = {}
    for i, j in parear(validas, pred, passo).items():
        ataque, motivo = rotulos[j]
        saida[validas[i]["nota"]] = {
            "modelo": ataque,
            "motivo": motivo,
            "p": round(max(ataque_rotulo.probabilidades(pred[j]).values()), 4),
        }
    return saida


def main() -> int:
    """Lê as telas e grava ``modelo_ataque.json`` na pasta da ferramenta."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pasta", type=Path, required=True, help="pasta da ferramenta")
    ap.add_argument("--ataque", type=Path, required=True, help="ataque_<fonte>.json")
    ap.add_argument("--modelo", type=Path, default=ataque_rotulo.DETECTOR_CALIBRADO)
    args = ap.parse_args()
    doc = json.loads(args.ataque.read_text(encoding="utf-8"))
    por_tela: dict[int, list[dict]] = {}
    for n in doc["notas"]:
        por_tela.setdefault(int(n["tela"]), []).append(n)
    leituras: dict[str, dict] = {}
    with trava_gpu("tablatura", "leitura do modelo"):
        modelo = detector_tab.carregar(args.modelo)
        for tela, (video, t_s) in sorted(onde_ler(args.pasta).items()):
            leituras.update(ler_notas(modelo, video, t_s, por_tela.get(tela, [])))
            print(f"tela {tela}", flush=True)
    contagem: dict[str, int] = {}
    for n in doc["notas"]:
        tipo = divergencia(n.get("ataque"), leituras.get(n["nota"], {}).get("modelo"))
        if tipo:
            contagem[tipo] = contagem.get(tipo, 0) + 1
    (args.pasta / ARQUIVO).write_text(
        json.dumps(
            {
                "modelo": str(args.modelo),
                "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
                "notas": leituras,
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "notas lidas", len(leituras), "de", len(doc["notas"]), "divergências", contagem
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
