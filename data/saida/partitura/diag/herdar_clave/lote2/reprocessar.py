"""Reprocessa herdar_condicao e regrava o documento de 3 pastas sem produto (sem Audiveris)."""
import json
import shutil

from tab.caminhos import RAIZ, SAIDA
from tab.partitura_omr import herdar_condicao
from tab.partitura_video import (
    CONDICAO_AUDIVERIS,
    ESQUEMA_PARTITURA,
    _pauta_sem_produto,
    caminho_da_pasta,
)

DIAG = RAIZ / "data/saida/partitura/diag/herdar_clave/lote2"
PASTA_SP = SAIDA / "partitura" / "sem_produto"
SLUGS = sorted(
    p.name for p in PASTA_SP.iterdir()
    if p.name[:6] not in ("canon_", "athlet", "agua_d") and (p / "omr").exists()
)

for slug in SLUGS:
    pasta = PASTA_SP / slug
    omr = pasta / "omr"
    base = omr / "audiveris"
    destino_h = base / f"{CONDICAO_AUDIVERIS}_herdada"
    herdada_velha = json.loads((destino_h / "herdada.json").read_text(encoding="utf-8"))
    velha = {r["id"]: r for r in herdada_velha}
    doc_antes = caminho_da_pasta(pasta)
    shutil.copy2(doc_antes, DIAG / f"{slug}.partitura_antes.json")
    shutil.copy2(destino_h / "herdada.json", DIAG / f"{slug}_herdada_antes.json")
    shutil.copytree(destino_h, DIAG / f"{slug}_x2_margem_herdada_antes", dirs_exist_ok=True)

    indice = json.loads((pasta / "recortes" / "indice.json").read_text(encoding="utf-8"))
    com_pauta = [e for e in indice if not e["sem_pauta"]]
    execucao = json.loads((base / CONDICAO_AUDIVERIS / "execucao.json").read_text(encoding="utf-8"))
    no_exec = {r["id"] for r in execucao}
    do_video = [e for e in com_pauta if e["id"] in no_exec]
    nova = herdar_condicao(execucao, do_video, destino_h, RAIZ)

    print(f"== {slug}")
    for r in nova:
        a = velha.get(r["id"], {}).get("fifths_aplicado")
        if a != r["fifths_aplicado"]:
            print(f"  {r['id']}: fifths_aplicado {a} -> {r['fifths_aplicado']} (tinha_clave {r['tinha_clave']})")

    pautas = [_pauta_sem_produto(e, omr) for e in com_pauta]
    eventos = sum(len(p["eventos"]) for p in pautas)
    documento = {
        "esquema": ESQUEMA_PARTITURA,
        "produto": None,
        "produto_sha256": None,
        "video": indice[0]["video"],
        "gerado_por": {"leitor": "audiveris x2_margem + armadura do vídeo", "completar": None},
        "pautas": pautas,
        "resumo": {
            "pautas": len(pautas),
            "eventos": eventos,
            "com_erro": sum("erro" in p for p in pautas),
            "paginas": len({p["pagina"] for p in pautas}),
        },
    }
    antigo = json.loads(doc_antes.read_text(encoding="utf-8"))["pautas"]
    for p_antiga, p_nova in zip(antigo, pautas):
        if p_antiga.get("fifths") != p_nova.get("fifths"):
            print(f"  pauta {p_nova['recorte']}: fifths {p_antiga.get('fifths')} -> {p_nova.get('fifths')}")
    print(f"  resumo antes {json.loads(doc_antes.read_text(encoding='utf-8'))['resumo']}")
    print(f"  resumo depois {documento['resumo']}")
    doc_antes.write_text(json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8")
