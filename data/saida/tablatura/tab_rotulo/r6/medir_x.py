"""0218: o X empilhado nos ouros (escolha) e na T8.6 (prova lacrada, uma vez só).

``ouros``: para ``atqs`` e ``atqx`` e as 3 sementes, lê com a dobra 4 (EOB e Room 335 fora do
treino) as telas conferidas dos dois vídeos que têm X do dono (``correcoes/x_dono.json``) e
conta o X lido e o X falso. Grava ``r6/medida_x_ouros.json``.

``t86``: só com ``r6/t86_x_liberada.json``, e uma vez só. Para ``atqx`` (dobra 0, 3 sementes):
X lido e X falso nas 28 telas conferidas da T8.6; o ataque e a casa como na 0215
(``tab.ataque_r4.contar`` no ``L`` de ``r6/decisao.json``). Grava ``r6/medida_t86_x.json``.

- **X lido**: nota X do dono com uma nota prevista de casa ``x`` na mesma corda, a até
  0,5 passo.
- **X falso**: nota numérica do dono cuja nota prevista mais perto (mesma corda, até 0,5
  passo) tem casa ``x``.

Uso (container): env PYTHONPATH=/app python /app/data/saida/tablatura/tab_rotulo/r6/medir_x.py ouros|t86
"""

import json
import sys
from collections import Counter
from pathlib import Path

from tab.comum import caminhos
from tab.comum.gpu import trava_gpu
from tab.tablatura.ataque import r4 as A
from tab.tablatura.leitura import detector_tab

R6 = caminhos.TAB_ROTULO / "r6"
X_DONO = caminhos.SAIDA / "tablatura" / "correcoes" / "x_dono.json"
OURO = Path("/app/data/gold/ouro_video")
OUROS = (
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
    "tabroom_335_larry_carlton_fingerstyle_guitar",
)
T86 = caminhos.SAIDA / "tablatura" / "t86" / "ferramenta"
GAB_T86 = caminhos.TAB_ROTULO / "r2" / "conferir_t86" / "ataque_t86.json"


def contar_x(dono: list[dict], pred: list[dict], passo: float) -> Counter:
    """Conta o X lido e o X falso de uma tela.

    Args:
        dono: notas da tela conferida (``corda``, ``casa``, ``x_centro_quadro``).
        pred: notas previstas (``corda``, ``casa``, ``x_centro_quadro``).
        passo: passo da tela.

    Returns:
        ``x``, ``x_lido``, ``numericas`` e ``x_falso``.
    """
    c: Counter = Counter()
    for n in dono:
        perto = [
            p
            for p in pred
            if p["corda"] == int(n["corda"])
            and abs(p["x_centro_quadro"] - float(n["x_centro_quadro"])) <= 0.5 * passo
        ]
        if str(n["casa"]).lower() in ("x", "xs"):
            c["x"] += 1
            c["x_lido"] += any(p["casa"] == "x" for p in perto)
        else:
            c["numericas"] += 1
            if perto:
                mais = min(
                    perto,
                    key=lambda p: abs(
                        p["x_centro_quadro"] - float(n["x_centro_quadro"])
                    ),
                )
                c["x_falso"] += mais["casa"] == "x"
    return c


def medir_ouros() -> int:
    """Mede ``atqs`` e ``atqx`` nos dois ouros, grava e imprime."""
    xs = json.loads(X_DONO.read_text(encoding="utf-8"))["treino"]
    saida: dict = {}
    for versao in ("atqs", "atqx"):
        for s in (1, 2, 3):
            modelo = detector_tab.carregar(A.modelo_da_dobra(versao, 4, s))
            soma: Counter = Counter()
            for slug in OUROS:
                ouro = json.loads((OURO / f"{slug}.json").read_text(encoding="utf-8"))
                video = caminhos.acervo() / ouro["video"]
                for tela in ouro["telas"]:
                    if str(tela["id"]) not in xs[slug]:
                        continue
                    pred, passo = A.ler_tela(modelo, video, float(tela["quadro_ref_s"]))
                    soma += contar_x(tela["notas"], pred, passo)
            saida[f"{versao}_s{s}"] = dict(soma)
            print(versao, s, dict(soma), flush=True)
    (R6 / "medida_x_ouros.json").write_text(
        json.dumps(saida, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


def medir_t86() -> int:
    """A prova lacrada: mede o ``atqx`` na T8.6 uma vez, grava e imprime."""
    destino = R6 / "medida_t86_x.json"
    if not (R6 / "t86_x_liberada.json").exists():
        raise SystemExit(
            "a T8.6 espera a escolha nos ouros (falta r6/t86_x_liberada.json)"
        )
    if destino.exists():
        raise SystemExit(f"{destino.name} já existe: a T8.6 se mede uma vez só")
    decisao = json.loads((R6 / "decisao.json").read_text(encoding="utf-8"))
    if not decisao["atqx_passa_nos_ouros"]:
        raise SystemExit("o atqx não passou nos ouros: a T8.6 não se gasta")
    L = decisao["versoes"]["atqx"]["L"]
    conf = json.loads((T86 / "conferencia_t86.json").read_text(encoding="utf-8"))
    telas = {int(t["id"]): t for t in conf["telas"] if t.get("conferida")}
    indice = {int(r["id"]): r for r in json.loads((T86 / "indice.json").read_text())}
    gab = A.gabarito_por_tela(GAB_T86)
    saida: dict = {"L": L, "sementes": {}}
    soma_x: Counter = Counter()
    soma_a: Counter = Counter()
    casa = [0, 0]
    for s in (1, 2, 3):
        modelo = detector_tab.carregar(A.modelo_da_dobra("atqx", 0, s))
        cx: Counter = Counter()
        ca: Counter = Counter()
        for tid, tela in sorted(telas.items()):
            r = indice[tid]
            pred, passo = A.ler_tela(
                modelo, caminhos.acervo() / r["video"], float(r["t"])
            )
            cx += contar_x(tela["notas"], pred, passo)
            if tid in gab:
                ca += A.contar(gab[tid], A.com_limiar(pred, L), passo)
        m = A.regra(ca)
        soma_x += cx
        soma_a += m
        casa[0] += ca["casa_certa"]
        casa[1] += ca["casadas"]
        saida["sementes"][s] = {"x": dict(cx), "ataque": dict(ca)}
        print(
            f"atqx s{s}: {dict(cx)} | casa {ca['casa_certa']}/{ca['casadas']}",
            flush=True,
        )
    sf = (soma_a["nao|sim"], soma_a["nao|sim"] + soma_a["nao|nao"])
    custo = (soma_a["sim|nao"], soma_a["sim|nao"] + soma_a["sim|sim"])
    saida.update(
        {"x_soma": dict(soma_x), "sim_falso": sf, "custo": custo, "casa": casa}
    )
    print(json.dumps(saida | {"sementes": "…"}, indent=1), flush=True)
    destino.write_text(
        json.dumps(saida, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    with trava_gpu("tablatura", "medida do X (0218)"):
        codigo = medir_ouros() if sys.argv[1] == "ouros" else medir_t86()
    raise SystemExit(codigo)
