"""Revisão do modo ataque (2026-10-23): renumera as chaves depois das notas novas do dono.

Na revisão, o dono acrescentou ou tirou notas no modo normal em três telas (T8.3 tela 25,
T8.2 tela 10, Pat Metheny tela 4). A chave ``t<tela>-n<k>`` é a posição da nota no ouro, e
as entradas do ataque ficaram apontando para a nota vizinha. Cada entrada guarda a corda,
a casa e o x da nota dela: aqui ela volta para a nota de mesma corda e casa, a até 1 px.
Nenhum rótulo muda. Grava cópia ``*_antes_renumerar.json`` e imprime as notas novas, que
ficam sem entrada até o dono marcar.

Uso (container): python data/saida/tablatura/tab_rotulo/revisao_ataque/renumerar.py
"""

import json
import shutil
from pathlib import Path

R = Path("/app/data/saida/tablatura")
G = Path("/app/data/gold/ouro_video")
FONTES = (
    (R / "t83/ferramenta/conferencia_t83.json", R / "tab_rotulo/r2/conferir_t83/ataque_t83.json"),
    (R / "t82/ferramenta/conferencia_t82.json", R / "tab_rotulo/r2/conferir_novos/ataque_t82.json"),
    (
        G / "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover.json",
        R / "tab_rotulo/r2/conferir/ataque_pat_metheny.json",
    ),
)


def main() -> None:
    """Renumera e grava."""
    for ouro_p, ataque_p in FONTES:
        ouro = json.loads(ouro_p.read_text(encoding="utf-8"))
        doc = json.loads(ataque_p.read_text(encoding="utf-8"))
        telas = {int(t["id"]): t["notas"] for t in ouro["telas"]}
        trocas, perdidas, alvo = 0, [], {}
        for e in doc["notas"]:
            notas = telas[int(e["tela"])]
            cand = [
                k for k, n in enumerate(notas)
                if (n["corda"], str(n["casa"])) == (e["corda"], str(e["casa"]))
                and abs(float(n["x_centro_quadro"]) - float(e["x_centro_quadro"])) <= 1.0
            ]
            if len(cand) != 1:
                perdidas.append((e["nota"], e["corda"], e["casa"], e["x_centro_quadro"], len(cand)))
                continue
            alvo[id(e)] = f"t{e['tela']}-n{cand[0]}"
        # Duas entradas para a mesma nota: uma é a escolha que o dono fez depois da nota
        # nova (a chave já é a da nota que ele clicou) e a outra é a antiga, deslocada.
        # Fica a do dono; a antiga sai e é impressa.
        alinhadas = {alvo[id(e)] for e in doc["notas"] if alvo[id(e)] == e["nota"]}
        saem = [e for e in doc["notas"] if alvo[id(e)] != e["nota"] and alvo[id(e)] in alinhadas]
        for e in saem:
            print("  sai (antiga, deslocada):", e["nota"], "->", alvo[id(e)], e["ataque"], e["motivo"])
        doc["notas"] = [e for e in doc["notas"] if all(e is not x for x in saem)]
        for e in doc["notas"]:
            if alvo[id(e)] != e["nota"]:
                e["nota"] = alvo[id(e)]
                trocas += 1
        assert not perdidas, perdidas
        # A escolha do dono numa chave deslocada apagou a entrada da nota vizinha. Essas
        # notas voltam com a entrada de antes da revisão (``*_antes_revisao.json``), achada
        # pela mesma corda, casa e x.
        antes = json.loads(
            ataque_p.with_name(ataque_p.stem + "_antes_revisao.json").read_text(encoding="utf-8")
        )
        com = {e["nota"] for e in doc["notas"]}
        for tid, notas in telas.items():
            for k, n in enumerate(notas):
                chave = f"t{tid}-n{k}"
                if chave in com:
                    continue
                velhas = [
                    e for e in antes["notas"] if int(e["tela"]) == tid
                    and (e["corda"], str(e["casa"])) == (n["corda"], str(n["casa"]))
                    and abs(float(e["x_centro_quadro"]) - float(n["x_centro_quadro"])) <= 1.0
                ]
                if len(velhas) == 1:
                    doc["notas"].append(dict(velhas[0], nota=chave))
                    print("  volta de antes da revisão:", chave, velhas[0]["ataque"], velhas[0]["motivo"])
        com = {e["nota"] for e in doc["notas"]}
        conferidas = {int(k) for k, v in (doc.get("telas_conferidas") or {}).items() if v}
        novas = [
            (f"t{tid}-n{k}", n["corda"], n["casa"])
            for tid, notas in telas.items() if tid in {int(e["tela"]) for e in doc["notas"]}
            for k, n in enumerate(notas) if f"t{tid}-n{k}" not in com
        ]
        chaves = [e["nota"] for e in doc["notas"]]
        assert len(chaves) == len(set(chaves)), "chave repetida"
        copia = ataque_p.with_name(ataque_p.stem + "_antes_renumerar_revisao.json")
        assert not copia.exists()
        shutil.copy(ataque_p, copia)
        ataque_p.write_text(
            json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"{ataque_p.name}: {trocas} chaves renumeradas; notas sem entrada: {novas}"
              f" (telas conferidas {sorted(conferidas)[:3]}...)", flush=True)


if __name__ == "__main__":
    main()
