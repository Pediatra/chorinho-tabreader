"""Rodada 3025: itens de conferência dos recortes com compasso trocado pelo homr.

Para cada pauta com ``compassos_homr`` no documento, monta um MusicXML fundido: a
leitura herdada do Audiveris com os compassos trocados vindos do homr (com as
``divisions`` do homr declaradas no compasso trocado e as do Audiveris restauradas no
seguinte). A página de conferência desenha essa fusão ao lado do recorte.
"""
import copy
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from tab.partitura_gabarito import _conferir_png, _montar_item, _relativo_a_raiz
from tab.partitura_pareamento import trocar_compassos_pelo_homr
from tab.partitura_gabarito import ler_partitura

SP = Path("data/saida/partitura/sem_produto").resolve()
SAIDA = Path("data/saida/partitura/diag/troca_homr").resolve()


def divisoes(parte: ET.Element) -> list[str]:
    """``divisions`` em vigor em cada compasso da parte."""
    atual, lista = "1", []
    for medida in parte.findall("measure"):
        d = medida.find("attributes/divisions")
        if d is not None:
            atual = d.text
        lista.append(atual)
    return lista


def fundir(aud: Path, homr: Path, trocar: set[int], destino: Path) -> None:
    """Grava o MusicXML do Audiveris com as medidas de posição ``trocar`` do homr."""
    arvore = ET.parse(aud)
    pa = arvore.getroot().find("part")
    ph = ET.parse(homr).getroot().find("part")
    ma, mh = pa.findall("measure"), ph.findall("measure")
    da, dh = divisoes(pa), divisoes(ph)
    for k in sorted(trocar):
        nova = copy.deepcopy(mh[k])
        nova.set("number", ma[k].get("number"))
        for at in nova.findall("attributes"):
            nova.remove(at)
        attr = copy.deepcopy(ma[k].find("attributes"))
        if attr is None:
            attr = ET.Element("attributes")
        d = attr.find("divisions")
        if d is None:
            d = ET.Element("divisions")
            attr.insert(0, d)
        d.text = dh[k]
        nova.insert(0, attr)
        for el in list(nova):
            if el.tag in ("print",):
                nova.remove(el)
        indice = list(pa).index(ma[k])
        pa.remove(ma[k])
        pa.insert(indice, nova)
        if k + 1 < len(ma) and k + 1 not in trocar:
            seg = ma[k + 1]
            a2 = seg.find("attributes")
            if a2 is None:
                a2 = ET.Element("attributes")
                seg.insert(0, a2)
            d2 = a2.find("divisions")
            if d2 is None:
                d2 = ET.Element("divisions")
                a2.insert(0, d2)
            d2.text = da[k + 1]
    destino.parent.mkdir(parents=True, exist_ok=True)
    arvore.write(destino, encoding="utf-8", xml_declaration=True)


itens = []
linhas = []
for doc_path in sorted(SP.glob("*/*.partitura.json")):
    pasta = doc_path.parent
    doc = json.loads(doc_path.read_text("utf-8"))
    indice = {e["id"]: e for e in json.loads((pasta / "recortes/indice.json").read_text("utf-8"))}
    for pauta in doc["pautas"]:
        if not pauta["compassos_homr"]:
            continue
        rid = pauta["recorte"]
        aud = pasta / "omr/audiveris/x2_margem_herdada" / rid / "saida.musicxml"
        homr = pasta / "omr/homr/nativo" / rid / "saida.musicxml"
        numeros = [c["numero"] for c in ler_partitura(aud)["compassos"]]
        trocar = {numeros.index(n) for n in pauta["compassos_homr"]}
        destino = SAIDA / "fusao" / pasta.name[:16] / rid / "saida.musicxml"
        fundir(aud, homr, trocar, destino)
        fundida = ler_partitura(destino)
        assert len(fundida["compassos"]) == len(numeros), (pasta.name, rid)
        posicoes = ", ".join(str(k + 1) for k in sorted(trocar))
        entrada = indice[rid]
        png = pasta / "recortes" / f"{rid}.png"
        largura, altura = _conferir_png(png, entrada)
        item = _montar_item(
            id_=f"{pasta.name[:16]}_{rid}",
            origem="sem_produto",
            canal=entrada["video"].split("/", 1)[0],
            video=entrada["video"],
            tela=entrada["pagina"],
            fonte=f"audiveris + homr no(s) compasso(s) {posicoes} da pauta",
            caminho=destino,
            png=png,
            largura=largura,
            altura=altura,
            eventos_homr=None,
            referencia=None,
        )
        item["pasta"] = _relativo_a_raiz(pasta)
        item["recorte"] = rid
        item["compassos_homr"] = sorted(k + 1 for k in trocar)
        itens.append(item)
        notas = sum(
            1 for c in fundida["compassos"] for i, s in enumerate(c["simbolos"])
            if numeros.index(c["numero"]) in trocar and not s["pausa"]
        )
        linhas.append(f"{pasta.name[:30]} {rid}: compassos {posicoes} de {len(numeros)}, notas do homr {notas}")
(SAIDA / "itens.json").write_text(json.dumps({"formato": 1, "gerado_por": "diag troca_homr/conferencia.py (rodada 3025)", "itens": itens}, ensure_ascii=False, indent=1), "utf-8")
print("\n".join(linhas))
print(f"{len(itens)} recortes, {sum(len(i['compassos_homr']) for i in itens)} compassos")
