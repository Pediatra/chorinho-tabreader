"""Resumo do lote 1 da rodada A4: produto, alinhamento e arquivo irmao por video (leitura)."""

import collections
import json
import re
import statistics
from pathlib import Path

L = Path("/var/home/gabriel/Projects/chorinho-dataset/data/saida/audio/a4/lote1")
APELIDOS = json.loads((L / "apelidos.json").read_text("utf-8"))


def carregar(caminho):
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
    """RC de cada passo, lido do lote1.log."""
    rc = {}
    for linha in (L / "lote1.log").read_text("utf-8").splitlines():
        m = re.match(r"\[(\S+)\] (\w+) RC=(\d+) TEMPO_S=(\d+)", linha)
        if m and m.group(1) == ap:
            rc[m.group(2)] = (int(m.group(3)), int(m.group(4)))
    return rc


def erro_tail(ap, passo):
    caminho = L / "logs" / f"{ap}_{passo}.log"
    if not caminho.exists():
        return ""
    linhas = caminho.read_text("utf-8", errors="replace").splitlines()
    return "\n".join(linhas[-20:])


resultados = []
for ap, caminho_video in APELIDOS.items():
    rc = status_rc(ap)
    codec_v, codec_a, duracao = meta_video(ap) if (L / "logs" / f"{ap}_meta.log").exists() else (None, None, None)
    linha = {
        "apelido": ap,
        "canal": caminho_video.split("/")[0],
        "video": caminho_video,
        "codec_video": codec_v,
        "codec_audio": codec_a,
        "duracao_s": round(duracao, 1) if duracao else None,
        "passos_rc": {k: v[0] for k, v in rc.items()},
        "passos_tempo_s": {k: v[1] for k, v in rc.items()},
        "erros": {},
    }
    for passo, (codigo, _) in rc.items():
        if codigo != 0:
            linha["erros"][passo] = erro_tail(ap, passo)

    produto = carregar(L / f"{ap}.json")
    if produto:
        telas = produto.get("telas", [])
        notas = produto.get("notas", [])
        por_corda = collections.Counter(n["corda"] for n in notas)
        total = len(notas)
        frac = {c: round(por_corda.get(c, 0) / total, 3) if total else None for c in range(1, 7)}
        leitura_nao_ok = [
            {"tela": t["id"], "exibicao": i, "leitura": e.get("leitura")}
            for t in telas
            for i, e in enumerate(t.get("exibicoes", []))
            if e.get("leitura") not in (None, "ok")
        ]
        linha["produto"] = {
            "telas": len(telas),
            "notas": total,
            "fracao_por_corda": frac,
            "corda1_baixa": frac[1] is not None and frac[1] < 0.08,
            "leitura_nao_ok": leitura_nao_ok,
        }

    alinhado = carregar(L / f"alinhado_{ap}.json")
    if alinhado:
        exib = alinhado.get("exibicoes", [])
        colunas = alinhado.get("colunas", [])
        recusadas = [e for e in exib if e.get("recusada_exibicao")]
        aceitas = [e for e in exib if not e.get("recusada_exibicao")]
        com_tempo = sum(1 for c in colunas if c.get("t_audio") is not None)
        cos_aceitas = [e["cos_medio"] for e in aceitas if e.get("cos_medio") is not None]
        alarme = sum(
            1 for e in recusadas if e.get("cos_medio") is not None and e["cos_medio"] >= 0.7
        )
        linha["alinhamento"] = {
            "exibicoes": len(exib),
            "recusadas": len(recusadas),
            "colunas_com_tempo": com_tempo,
            "colunas_total": len(colunas),
            "fracao_colunas_com_tempo": round(com_tempo / len(colunas), 3) if colunas else None,
            "cos_medio_mediana_aceitas": round(statistics.median(cos_aceitas), 4) if cos_aceitas else None,
            "alarme_leitura": alarme,
        }

    sibling = carregar(L / f"{ap}.audio.json")
    linha["sibling_gerado"] = sibling is not None
    resultados.append(linha)

(L / "resumo.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), "utf-8")

print("apelido | video | dur | produto(telas/notas) | c1 | alinh(exib/rec) | colunas | cos_med | alarme")
for r in resultados:
    p = r.get("produto", {})
    a = r.get("alinhamento", {})
    fc = p.get("fracao_por_corda", {})
    print(
        f"{r['apelido']} | {r['codec_video']} | {r['duracao_s']} | "
        f"{p.get('telas')}/{p.get('notas')} | {fc.get(1)} | "
        f"{a.get('exibicoes')}/{a.get('recusadas')} | "
        f"{a.get('colunas_com_tempo')} de {a.get('colunas_total')} | "
        f"{a.get('cos_medio_mediana_aceitas')} | {a.get('alarme_leitura')}"
    )
