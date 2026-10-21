# guarda os quadros com braço dos vídeos 1-16 da 1030 (menos o 15), para desenvolver a regra J
import json
from tab.caminhos import MAOS_M30, MAOS_M31
from tab.maos_braco_nut_fora import guardar_quadros
from tab.maos_braco_video import ler_jsonl, nome_jsonl, videos_revisados
for v in videos_revisados():
    nome=f"v{v.numero:02d}"
    if v.numero==15 or (MAOS_M31/f"dimensoes_{nome}.json").exists(): continue
    regs=ler_jsonl(MAOS_M30/nome_jsonl(v.numero))
    d=guardar_quadros(v,regs,nome)
    (MAOS_M31/f"dimensoes_{nome}.json").write_text(json.dumps(d))
    print(nome,len(d),flush=True)
