"""9001, fase 1b: grava o LEIAME.json de cada pasta da partitura em data/saida.

Classe por item (manter / arquivar / apagar) com o motivo; "citado_por" é a lista de
rodadas (docs/rodadas/3*.md) e decisões que citam o caminho do item. Só lê e grava LEIAME.
Uso (na raiz): python data/saida/partitura/diag/r9001/leiame.py
"""
import glob
import json
import os
from pathlib import Path

DOCS = {p: Path(p).read_text(encoding="utf-8") for p in
        glob.glob("docs/rodadas/3*.md") + glob.glob("docs/decisoes/3*.md")}


def citado(caminho: str) -> list[str]:
    nome = caminho.split("data/saida/", 1)[-1]
    curto = "/".join(nome.split("/")[-2:])
    return sorted(Path(p).stem.split("-")[0] for p, t in DOCS.items()
                  if nome in t or (len(curto) > 12 and curto in t))


def tamanho(caminho: str) -> float:
    if os.path.isfile(caminho):
        return round(os.path.getsize(caminho) / 1e6, 2)
    total = 0
    for raiz, _, arqs in os.walk(caminho):
        total += sum(os.path.getsize(os.path.join(raiz, a)) for a in arqs
                     if not os.path.islink(os.path.join(raiz, a)))
    return round(total / 1e6, 1)


def item(caminho, classe, motivo, regeneravel, comando=None):
    return {"classe": classe, "motivo": motivo, "regeneravel": regeneravel,
            "comando": comando, "mb": tamanho(caminho), "citado_por": citado(caminho)}


def gravar(pasta: str, rodada: str, itens: dict, nota: str = "") -> None:
    doc = {"trilha": "partitura", "rodada": rodada, "gerado": "2026-10-21 (decisão 9001, fase 1b)",
           "nota": nota, "itens": itens}
    Path(pasta, "LEIAME.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                                          encoding="utf-8")
    print(pasta, len(itens), "itens")


P, F = "data/saida/partitura", "data/saida/part_frentes"
ALVO_LIDO = "lido pelo código"

# --- data/saida/partitura (itens do topo) ---
top = {}
for nome in sorted(os.listdir(P)):
    c = f"{P}/{nome}"
    if nome == "LEIAME.json":
        continue
    if nome == "p0":
        top[nome] = item(c, "manter", "censo P0: resumo.json e amostra.jsonl lidos por partitura_amostra e partitura_recortes (PARTITURA_P0)", False, "python -m tab.partitura_censo --por-canal 30 --semente 0 --saida data/saida/partitura/p0 (relê o HD)")
    elif nome == "p1":
        top[nome] = item(c, "manter", "P1: recortes, leituras e conferência; ver p1/LEIAME.json", False)
    elif nome == "p3":
        top[nome] = item(c, "manter", "pareamento P3 (PARTITURA_P3), rodada 3010", True, "python -m tab.partitura_pareamento")
    elif nome == "video":
        top[nome] = item(c, "manter", "os 3 documentos finais chorinho/partitura@1 com recortes e leituras (PARTITURA_VIDEO); prova byte a byte da 9001", False, "python -m tab.partitura_video recortar|ler|parear --produto data/saida/fase8/rede/<stem>.json")
    elif nome == "sem_produto":
        top[nome] = item(c, "manter", "piloto sem produto (PARTITURA_SEM_PRODUTO): ouro leitura_sem_produto, CA1 linhas D e F, rodadas 3016-3025", False, "python -m tab.partitura_video paginar --video ... e ler --pasta ... (relê o HD)")
    elif nome == "diag":
        top[nome] = item(c, "manter", "diagnósticos; ver diag/LEIAME.json item a item", False)
    elif nome == "pauta_por_canal_dono.json":
        top[nome] = item(c, "manter", "rótulo do dono transcrito do chat (a confirmar); vai para data/gold/partitura na fase 4", False)
    elif nome in ("p0_rodada3", "p0_rodada4", "p0_teste", "p0_olhar"):
        top[nome] = item(c, "arquivar", "versões anteriores do censo P0 (rodada 3001); a final é p0/", False)
    elif nome.startswith("msg") and nome.endswith(".txt"):
        top[nome] = item(c, "apagar", "mensagem de commit já usada", True)
    elif nome.endswith(".log") or nome.endswith(".txt"):
        top[nome] = item(c, "arquivar", "log de rodada antiga", False)
    else:
        top[nome] = item(c, "arquivar", "sem classe definida", False)
gravar(P, "3001-3027", top, "Pasta da trilha partitura. O alvo da 9001 (data/saida/partitura/) é onde ela já está.")

# --- p1 ---
p1 = {}
for nome in sorted(os.listdir(f"{P}/p1")):
    c = f"{P}/p1/{nome}"
    if nome == "LEIAME.json":
        continue
    regra = {
        "conferencia": ("manter", "itens.json citado pelo ouro leitura_p1 (fonte_itens); versionado", False, "python -m tab.partitura_gabarito preparar"),
        "omr": ("manter", "leituras Audiveris/homr da P1, lidas por avaliar, pareamento, gabarito, omr, smt e CA1", False, "python -m tab.partitura_omr rodar / herdar"),
        "recortes": ("manter", "recortes da P1 (PASTA_RECORTES), lista de permissão da ferramenta", False, "python -m tab.partitura_recortes"),
        "recortes_margem": ("manter", "recortes com margem: entrada da condição x2_margem e PNG que o ouro leitura_p1 cita; versionado", False, "python -m tab.partitura_recortes --margem-cima 7 --margem-baixo 7"),
        "variantes": ("manter", "rodada 3003 (comparativo das variantes)", False, None),
        "fumaca": ("arquivar", "teste de fumaça dos leitores (rodada 3002)", False, None),
        "recortes_teste": ("arquivar", "recortes de teste antigos da P1", True, None),
    }.get(nome, ("arquivar", "log antigo", False, None))
    p1[nome] = item(c, *regra)
gravar(f"{P}/p1", "3002-3006", p1)

# --- diag (item a item) ---
manter_diag = {
    "ca1": "aceite CA1 das frentes (ca1.py e a saída de referência ca1.txt); prova da 9001",
    "troca_homr": "itens.json citado pelo ouro compassos_homr; versionado (teste_remarcar.json é cópia igual do ouro: apagar depois do .tar)",
    "conferencia_sem_produto": "itens.json citado pelo ouro leitura_sem_produto; versionado",
    "qualidade_imagem": "rodada 3026: scripts e json ficam; as pastas de PNG e leituras saem (ver nota)",
    "p4_antes": "rodada 3027: os documentos de antes da P4, completadas_vs_ouro.py e CA1 depois",
    "r9001": "inventário e prova da 9001",
    "medir_sem_produto": "medida do ouro sem produto (rodada 3023)",
}
diag = {}
for nome in sorted(os.listdir(f"{P}/diag")):
    c = f"{P}/diag/{nome}"
    if nome == "LEIAME.json":
        continue
    if nome in manter_diag:
        diag[nome] = item(c, "manter", manter_diag[nome], False)
    elif nome.endswith((".py", ".sh")):
        diag[nome] = item(c, "manter", "script de diagnóstico (código vivo ou procedência de rodada); versionado", False)
    elif nome.endswith((".txt", ".json", ".log")) and os.path.isfile(c):
        diag[nome] = item(c, "manter", "saída de texto pequena de um script de diagnóstico", True, "o script de mesmo prefixo")
    elif nome.endswith((".png", ".jpg")):
        diag[nome] = item(c, "arquivar", "imagem de diagnóstico olhada numa rodada", True, "o script diag_* correspondente")
    else:
        diag[nome] = item(c, "arquivar", "pasta de diagnóstico de rodada fechada", False)
diag_nota = ("qualidade_imagem/{reduzido,mediana,leituras,leituras_mediana}: APAGAR (72 MB), "
             "refeitos pelos scripts reduzir.py e mediana.py, que ficam.")
gravar(f"{P}/diag", "3003-3027", diag, diag_nota)

# --- part_frentes ---
pf = {
    "f0_regua": ("manter", "frente F0 (rodadas 3101-3103), PART_FRENTE_0", False, None),
    "fa_imagem": ("arquivar", "frente A1 reprovada (rodada 3110), PART_FRENTE_A", False, "python -m tab.partitura_imagem / partitura_imagem_mediana (relê o HD)"),
    "fb_fusao": ("apagar", "pasta vazia (frente B não rodou)", True, None),
    "fc_polifonico": ("apagar", "pasta vazia (frente C não rodou)", True, None),
    "fd_gabarito": ("manter", "frente D1: recortes e leituras do ouro leitura_d1; itens_d1.json citado pelo ouro (versionado); videos_v1_INVALIDA arquivar; ouro_d1_copia.json apagar (cópia de teste vazia)", False, None),
    "fe_completar": ("manter", "frente E1: e1.json e itens_e1.json citado pelo ouro figura_e1 (versionado); ouro_e1_copia.json apagar (cópia de teste vazia)", False, None),
    "fp_produto": ("manter", "P4 (rodada 3027): scripts e casos; a subpasta video/ é cópia de partitura/video (apagar, 29 MB)", False, None),
}
gravar(F, "3101-3172, 3027", {n: item(f"{F}/{n}", *v) for n, v in pf.items() if os.path.exists(f"{F}/{n}")},
       "Na fase 4 da 9001 vai para data/saida/partitura/frentes/, pelos PART_FRENTE_* do caminhos.py.")
