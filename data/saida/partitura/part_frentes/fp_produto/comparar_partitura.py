"""Aceite da P4: compara os 3 documentos novos com os atuais, nota a nota (rodada 3027).

Só lê. Compara ``/app/data/saida/partitura/video`` (atual) com
``/app/data/saida/part_frentes/fp_produto/video`` (novo), e cruza as contagens de
completadas com o ``e1.json`` regerado. Imprime o que mudou e as contagens do aceite.

Uso (dentro do container): python comparar_partitura.py
"""

import collections
import json
from pathlib import Path

ATUAL = Path("/app/data/saida/partitura/video")
NOVO = Path("/app/data/saida/part_frentes/fp_produto/video")
E1 = Path("/app/data/saida/part_frentes/fp_produto/e1_passo2.json")
GYM = "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar"
STEMS = [
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    GYM,
]
CAMPOS_NOVOS_PAUTA = {"pauta_pequena", "leitura_ok"}
CAMPOS_NOVOS_RESUMO = {
    "completadas_acorde",
    "completadas_isolado",
    "nao_completadas_harmonico",
    "nao_completadas_ligada",
    "nao_completadas_pausa",
    "nao_completadas_cabecalho",
    "nao_completadas_oitava",
    "pautas_pequenas",
}


def carregar(raiz, stem):
    caminho = raiz / stem / f"{stem}.partitura.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


def eh_tab(evento):
    """Evento novo da tab (isolado): par com metodo tab."""
    return evento["par"] is not None and evento["par"]["metodo"] == "tab"


def comparar_documento(stem, antigo, novo, problemas):
    """Campo a campo: o que existia fica igual; só entram os campos novos do item 3."""
    for chave in antigo:
        if chave not in ("pautas", "resumo", "gerado_por") and antigo[chave] != novo.get(chave):
            problemas.append(f"{stem}: campo do topo {chave} mudou")
    if set(novo) - set(antigo):
        problemas.append(f"{stem}: campos novos no topo {set(novo) - set(antigo)}")
    if set(novo["gerado_por"]) - set(antigo["gerado_por"]) != {"completar_tab"}:
        problemas.append(f"{stem}: gerado_por fora do esperado")
    for chave in antigo["gerado_por"]:
        if antigo["gerado_por"][chave] != novo["gerado_por"].get(chave):
            problemas.append(f"{stem}: gerado_por.{chave} mudou")
    for chave in antigo["resumo"]:
        if antigo["resumo"][chave] != novo["resumo"].get(chave):
            problemas.append(
                f"{stem}: resumo.{chave} {antigo['resumo'][chave]} -> {novo['resumo'].get(chave)}"
            )
    if set(novo["resumo"]) - set(antigo["resumo"]) != CAMPOS_NOVOS_RESUMO:
        problemas.append(f"{stem}: campos novos do resumo fora do esperado")
    if len(antigo["pautas"]) != len(novo["pautas"]):
        problemas.append(f"{stem}: número de pautas mudou")
        return
    for pa, pn in zip(antigo["pautas"], novo["pautas"], strict=True):
        rec = pa["recorte"]
        if set(pn) - set(pa) != CAMPOS_NOVOS_PAUTA:
            problemas.append(f"{stem} {rec}: campos novos da pauta fora do esperado")
        for chave in pa:
            if chave != "eventos" and pa[chave] != pn[chave]:
                problemas.append(f"{stem} {rec}: pauta.{chave} mudou")
        antigos = pa["eventos"]
        novos = [e for e in pn["eventos"] if not eh_tab(e)]
        if len(antigos) != len(novos):
            problemas.append(f"{stem} {rec}: eventos existentes {len(antigos)} -> {len(novos)}")
            continue
        for eo, en in zip(antigos, novos, strict=True):
            for chave in eo:
                if chave != "simbolos" and eo[chave] != en[chave]:
                    problemas.append(f"{stem} {rec} x={eo['x_quadro']}: {chave} mudou")
            n = len(eo["simbolos"])
            if en["simbolos"][:n] != eo["simbolos"]:
                problemas.append(f"{stem} {rec} x={eo['x_quadro']}: símbolo existente mudou")
            if any(s["origem"] != "tab_completada" for s in en["simbolos"][n:]):
                problemas.append(f"{stem} {rec} x={eo['x_quadro']}: símbolo novo sem tab_completada")
        for en in pn["eventos"]:
            if eh_tab(en) and (en["t"] is not None or en["par"]["confere_x"] is not True):
                problemas.append(f"{stem} {rec}: evento novo fora do padrão em x={en['x_quadro']}")
            if eh_tab(en) and (en["trocadas"] or not en["simbolos"]):
                problemas.append(f"{stem} {rec}: evento novo com trocadas ou sem símbolo")
        xs_antigo = [e["x_quadro"] for e in antigos]
        xs_novo = [e["x_quadro"] for e in pn["eventos"]]
        if xs_antigo == sorted(xs_antigo) and xs_novo != sorted(xs_novo):
            problemas.append(f"{stem} {rec}: ordem em x quebrada")
        if xs_antigo != sorted(xs_antigo):
            print(f"  nota: {rec} já estava fora de ordem em x no atual (mantida como está)")


def contar(stem, novo):
    """Completadas do documento novo, por tipo e por tela, com as checagens de figura."""
    contagem = collections.Counter()
    nao_nulas = harmonicos = nulos = 0
    for pauta in novo["pautas"]:
        for evento in pauta["eventos"]:
            for simbolo in evento["simbolos"]:
                if simbolo["origem"] != "tab_completada":
                    continue
                tipo = "isolado" if eh_tab(evento) else "acorde"
                parte = "tela10" if stem == GYM and pauta["tela"] == 10 else "contada"
                contagem[(tipo, parte)] += 1
                nao_nulas += simbolo["figura"] is not None
                harmonicos += bool(simbolo.get("harmonico"))
                nulos += evento["compasso"] is None
    return contagem, nao_nulas, harmonicos, nulos


def main():
    problemas: list = []
    e1 = json.loads(E1.read_text(encoding="utf-8"))
    contadas_e1 = collections.Counter((n["video"], n["tipo"]) for n in e1["completadas"])
    tela10_e1 = e1["a_parte"]["tela_10_gym"]
    print(
        "vídeo | pautas | pequenas | acorde | isolado | harm | lig | tela 10 (à parte) |"
        " figura não null | harm marcado"
    )
    total = 0
    for stem in STEMS:
        antigo = carregar(ATUAL, stem)
        novo = carregar(NOVO, stem)
        comparar_documento(stem, antigo, novo, problemas)
        contagem, nao_nulas, harmonicos, nulos = contar(stem, novo)
        total += sum(contagem.values())
        res = novo["resumo"]
        pequenas = sum(p["pauta_pequena"] for p in novo["pautas"])
        print(
            f"{stem[:24]} | {len(novo['pautas'])} | {pequenas} |"
            f" {res['completadas_acorde']} | {res['completadas_isolado']} |"
            f" {res['nao_completadas_harmonico']} | {res['nao_completadas_ligada']} |"
            f" {contagem[('acorde', 'tela10')] + contagem[('isolado', 'tela10')]} |"
            f" {nao_nulas} | {harmonicos}"
        )
        if nulos:
            problemas.append(f"{stem}: {nulos} completadas com compasso nulo")
        if not all(p["leitura_ok"] for p in novo["pautas"]):
            problemas.append(f"{stem}: pauta com leitura_ok falso")
        if nao_nulas:
            problemas.append(f"{stem}: {nao_nulas} completadas com figura não null")
        for tipo in ("acorde", "isolado"):
            e1_n = contadas_e1[(stem, tipo)]
            novo_n = contagem[(tipo, "contada")]
            if e1_n != novo_n:
                problemas.append(f"{stem}: {tipo} contadas E1 {e1_n} != novo {novo_n}")
    print()
    print(f"completadas no documento novo (3 vídeos): {total}")
    print(f"tela 10 da Gymnopédie: E1 à parte {tela10_e1}")
    print(f"diferenças do aceite: {len(problemas)}")
    for linha in problemas[:80]:
        print("  -", linha)


if __name__ == "__main__":
    main()
