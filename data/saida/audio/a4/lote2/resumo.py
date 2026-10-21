"""Resumo do lote 2 da rodada A4: produto, alinhamento, arquivo irmao e som x marcador.

Leitura apenas. Grava resumo.json no proprio lote e imprime a tabela.
A medida som x marcador junta, por (tela, exibicao, coluna), o t_audio do alinhado
com o t_ini das notas do produto (primeira passagem; mediana se a coluna tiver
varios t_ini). Mede concordancia entre som e marcador, em ms, depois de tirar a
mediana (atraso fixo).
"""

import collections
import json
import re
import statistics
from pathlib import Path

RAIZ = Path("/var/home/gabriel/Projects/chorinho-dataset")
L = RAIZ / "data/saida/audio/a4/lote2"
APELIDOS = json.loads((L / "apelidos.json").read_text("utf-8"))
MVP_PRODUTO = RAIZ / "data/saida/conserto_v2/mvp.json"
MVP_ALINHADO = RAIZ / "data/saida/audio/a2/alinhado_v21_mvp.json"


def carregar(caminho):
    """Le um JSON, ou devolve None se nao existir."""
    try:
        return json.loads(caminho.read_text("utf-8"))
    except (OSError, ValueError):
        return None


def meta_video(ap):
    """Codec de video, audio e duracao, lidos do log do ffprobe."""
    texto = (L / "logs" / f"{ap}_meta.log").read_text("utf-8", errors="replace")
    inicio = texto.find("{")
    dados = json.loads(texto[inicio:]) if inicio >= 0 else {}
    codecs = {s["codec_type"]: s.get("codec_name") for s in dados.get("streams", [])}
    dur = dados.get("format", {}).get("duration")
    return codecs.get("video"), codecs.get("audio"), float(dur) if dur else None


def status_rc(ap):
    """RC e tempo de cada passo, lidos do lote2.log."""
    rc = {}
    for linha in (L / "lote2.log").read_text("utf-8").splitlines():
        m = re.match(r"\[(\S+)\] (\w+) RC=(\d+) TEMPO_S=(\d+)", linha)
        if m and m.group(1) == ap:
            rc[m.group(2)] = (int(m.group(3)), int(m.group(4)))
    return rc


def erro_tail(ap, passo):
    """Ultimas 20 linhas do log de um passo que falhou."""
    caminho = L / "logs" / f"{ap}_{passo}.log"
    if not caminho.exists():
        return ""
    linhas = caminho.read_text("utf-8", errors="replace").splitlines()
    return "\n".join(linhas[-20:])


def pares_som_marcador(produto, alinhado):
    """Pares (t_audio - t_ini) em segundos, por coluna da mesma exibicao.

    Por coluna, usa so as notas da primeira passagem (menor ``passagem`` entre as
    que tem ``t_ini``); se houver varios ``t_ini``, usa a mediana.
    """
    grupos = collections.defaultdict(list)
    for n in produto.get("notas", []):
        if n.get("t_ini") is None or n.get("exibicao") is None:
            continue
        grupos[(n["tela"], n["exibicao"], n["coluna"])].append(n)
    t_ini = {}
    for chave, notas in grupos.items():
        primeira = min(n.get("passagem") or 1 for n in notas)
        valores = [n["t_ini"] for n in notas if (n.get("passagem") or 1) == primeira]
        t_ini[chave] = statistics.median(valores)
    pares = []
    for c in alinhado.get("colunas", []):
        if c.get("t_audio") is None:
            continue
        chave = (c["tela"], c["exibicao"], c["coluna"])
        if chave in t_ini:
            pares.append(c["t_audio"] - t_ini[chave])
    return pares


def estatisticas_pares(pares):
    """Mediana (ms) e fracao dentro de 100 e 200 ms da mediana."""
    if not pares:
        return {"n": 0, "mediana_ms": None, "ate_100_ms": None, "ate_200_ms": None}
    med = statistics.median(pares)
    dif = [abs(d - med) * 1000 for d in pares]
    return {
        "n": len(pares),
        "mediana_ms": round(med * 1000, 1),
        "ate_100_ms": round(sum(x <= 100 for x in dif) / len(dif), 3),
        "ate_200_ms": round(sum(x <= 200 for x in dif) / len(dif), 3),
    }


resultados = []
todos_pares = []
for ap, caminho_video in APELIDOS.items():
    rc = status_rc(ap)
    codec_v, codec_a, duracao = (
        meta_video(ap) if (L / "logs" / f"{ap}_meta.log").exists() else (None, None, None)
    )
    linha = {
        "apelido": ap,
        "canal": caminho_video.split("/")[0],
        "video": caminho_video,
        "codec_video": codec_v,
        "codec_audio": codec_a,
        "duracao_s": round(duracao, 1) if duracao else None,
        "passos_rc": {k: v[0] for k, v in rc.items()},
        "passos_tempo_s": {k: v[1] for k, v in rc.items()},
        "erros": {p: erro_tail(ap, p) for p, (cod, _) in rc.items() if cod != 0},
    }

    produto = carregar(L / f"{ap}.json")
    if produto:
        telas = produto.get("telas", [])
        notas = produto.get("notas", [])
        por_corda = collections.Counter(n["corda"] for n in notas)
        total = len(notas)
        frac = {c: round(por_corda.get(c, 0) / total, 3) if total else None for c in range(1, 7)}
        com_marcador = sum(1 for n in notas if n.get("t_ini") is not None)
        linha["produto"] = {
            "telas": len(telas),
            "notas": total,
            "fracao_por_corda": frac,
            "notas_com_t_ini": com_marcador,
            "instantes_distintos_t_ini": len({n["t_ini"] for n in notas if n.get("t_ini") is not None}),
            "sem_exibicao": sum(1 for n in notas if n.get("exibicao") is None),
        }

    alinhado = carregar(L / f"alinhado_{ap}.json")
    if alinhado:
        exib = alinhado.get("exibicoes", [])
        colunas = alinhado.get("colunas", [])
        recusadas = [e for e in exib if e.get("recusada_exibicao")]
        aceitas = [e for e in exib if not e.get("recusada_exibicao")]
        com_tempo = sum(1 for c in colunas if c.get("t_audio") is not None)
        cos_aceitas = [e["cos_medio"] for e in aceitas if e.get("cos_medio") is not None]
        linha["alinhamento"] = {
            "exibicoes": len(exib),
            "recusadas": len(recusadas),
            "colunas_com_tempo": com_tempo,
            "colunas_total": len(colunas),
            "fracao_colunas_com_tempo": round(com_tempo / len(colunas), 3) if colunas else None,
            "cos_medio_mediana_aceitas": round(statistics.median(cos_aceitas), 4) if cos_aceitas else None,
        }
        if produto and alinhado:
            pares = pares_som_marcador(produto, alinhado)
            linha["som_marcador"] = estatisticas_pares(pares)
            todos_pares.extend(pares)

    sibling = carregar(L / f"{ap}.audio.json")
    if sibling:
        ex_sib = sibling.get("exibicoes", [])
        linha.setdefault("alinhamento", {})["alarmes"] = sum(
            1 for e in ex_sib if e.get("alarme_leitura")
        )
        linha["alinhamento"]["fora_da_pagina"] = sum(1 for e in ex_sib if e.get("fora_da_pagina"))
    linha["sibling_gerado"] = sibling is not None
    resultados.append(linha)

# MVP como referencia
mvp_prod = carregar(MVP_PRODUTO)
mvp_alin = carregar(MVP_ALINHADO)
mvp = estatisticas_pares(pares_som_marcador(mvp_prod, mvp_alin)) if mvp_prod and mvp_alin else None

resumo = {
    "videos": resultados,
    "som_marcador_total": estatisticas_pares(todos_pares),
    "som_marcador_mvp": mvp,
}
(L / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), "utf-8")

print("apelido | dur | notas | c1 | notas c/t_ini | exib rec/tot | colunas | cos_med | alarme | fora_pag | som-marc n | med ms | <=100 | <=200")
for r in resultados:
    p = r.get("produto", {})
    a = r.get("alinhamento", {})
    s = r.get("som_marcador", {})
    fc = p.get("fracao_por_corda", {})
    print(
        f"{r['apelido']} | {r['duracao_s']} | {p.get('notas')} | {fc.get(1)} | {p.get('notas_com_t_ini')} | "
        f"{a.get('recusadas')}/{a.get('exibicoes')} | "
        f"{a.get('colunas_com_tempo')} de {a.get('colunas_total')} | "
        f"{a.get('cos_medio_mediana_aceitas')} | {a.get('alarmes')} | {a.get('fora_da_pagina')} | "
        f"{s.get('n')} | {s.get('mediana_ms')} | {s.get('ate_100_ms')} | {s.get('ate_200_ms')}"
    )
print("TOTAL som-marcador:", resumo["som_marcador_total"])
print("MVP som-marcador:", mvp)
