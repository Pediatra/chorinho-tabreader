import hashlib
import json
import pathlib

PRINC = pathlib.Path("/app")
RAIZ = PRINC / "data/saida/audio"
indice = json.loads(
    (PRINC / "data/saida/t82/ferramenta/indice.json").read_text(encoding="utf-8")
)
t82_videos = {}
for r in indice:
    t82_videos.setdefault(r["video"], []).append((r["id"], r["t"]))

arquivos = []
for pasta in ["a5", "a4/lote1", "a4/lote2"]:
    arquivos += sorted((RAIZ / pasta).glob("*.audio.json"))
for arq in arquivos:
    d = json.loads(arq.read_text())
    if arq.name.startswith("v21_"):
        continue
    prod = PRINC / d["produto"]
    existe = prod.exists()
    sha_ok = None
    if existe:
        sha_ok = hashlib.sha256(prod.read_bytes()).hexdigest() == d["produto_sha256"]
    g = d["gerado_por"]
    print(
        "==",
        arq.name,
        "| produto existe:",
        existe,
        "| sha bate:",
        sha_ok,
        "| transposicao:",
        g.get("transposicao"),
        "| param t0/t1 nao usado",
    )
    print("    video:", d["video"]["arquivo"])
    vid = d["video"]["arquivo"]
    chave = [k for k in t82_videos if k and k in vid or vid.endswith(k)]
    for k in chave:
        print("    >> T8.2:", t82_videos[k])
    if existe:
        p = json.loads(prod.read_text())
        print(
            "    produto chaves:",
            list(p.keys())[:12],
            "| telas:",
            len(p.get("telas", [])),
            "| notas:",
            len(p.get("notas", [])),
        )
        print(
            "    produto esquema:",
            p.get("esquema"),
            "| video:",
            json.dumps(p.get("video", {}), ensure_ascii=False)[:200],
        )
    print("    alinhamento params:", json.dumps(g.get("parametros", {}))[:200])
