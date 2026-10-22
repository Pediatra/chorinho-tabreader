import json
import sys

ouro = json.load(open(sys.argv[1], encoding="utf-8"))
tel_ferr = ouro.get("ferramenta", {}).get("telas", [])
notas = sum(len(t.get("notas", [])) for t in tel_ferr)
print(f"telas_ouro={len(ouro.get('telas', []))} telas_ferr={len(tel_ferr)} notas_ferr={notas} instantes={len(ouro.get('instantes', []))}")
if len(sys.argv) > 2:
    pre = json.load(open(sys.argv[2], encoding="utf-8"))
    print("pre_chaves=" + ",".join(pre.keys() if isinstance(pre, dict) else []))
    print("pre_modelo=" + str(pre.get("modelo")))
    print("pre_telas=" + str(len(pre.get("telas", []))))
    print("pre_instantes=" + str(len(pre.get("instantes", []))))
