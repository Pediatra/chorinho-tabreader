"""R4b: o que muda nos ataque_*.json conferidos com o conversor corrigido (2026-10-18).

O conversor (r2/converter.py) agora tenta a corda de cima quando a caixa do dono cai
abaixo das notas (arco por baixo). Este script roda o conversor nas cópias conferidas
(r2/conferir e r2/conferir_novos) e lista as notas que mudam. Nota com ``fonte: dono``
(clique do dono no modo ataque) nunca muda. Com --gravar, aplica as mudanças.

Uso (host ou container): python data/saida/tab_rotulo/r4b/corrigir_ataque.py [--gravar]
"""

import json
import sys
from pathlib import Path

R2 = Path(__file__).resolve().parents[1] / "r2"
sys.path.insert(0, str(R2))
import converter as cv  # noqa: E402

PARES = {
    "end_of_beginning": "conferir",
    "tabroom_335": "conferir",
    "pat_metheny": "conferir",
    "la_vie_en_rose": "conferir",
    "t82": "conferir_novos",
}


def main() -> int:
    """Lista (e com --gravar aplica) as mudanças."""
    gravar = "--gravar" in sys.argv
    for nome, sub in PARES.items():
        if nome == "t82":
            origem = R2 / sub / "conferencia_t82.json"
        else:
            origem = R2 / sub / cv.FONTES[nome].name
        arq = R2 / sub / f"ataque_{nome}.json"
        atual = json.loads(arq.read_text(encoding="utf-8"))
        conferidas = {k for k, v in atual.get("telas_conferidas", {}).items() if v}
        novo, _ = cv.processar_fonte(nome, origem)
        por_nota = {n["nota"]: n for n in novo["notas"]}
        mudou = 0
        for n in atual["notas"]:
            m = por_nota.get(n["nota"])
            if m is None or n.get("fonte") == "dono":
                continue
            if (m["ataque"], m["motivo"]) != (n["ataque"], n["motivo"]):
                print(f"{nome} {n['nota']} corda {n['corda']} casa {n['casa']}: "
                      f"{n['ataque']}/{n['motivo']} -> {m['ataque']}/{m['motivo']} "
                      f"({m['regiao']}) conferida={str(n['tela']) in conferidas}")
                mudou += 1
                if gravar:
                    n.update(ataque=m["ataque"], motivo=m["motivo"], regiao=m["regiao"],
                             fonte="conversor_2026-10-18")
        print(nome, "mudam", mudou)
        if gravar and mudou:
            arq.write_text(json.dumps(atual, ensure_ascii=False, indent=1, sort_keys=True)
                           + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
