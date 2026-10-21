"""Checagem do estimador de T com QUANTIL_PICO_FORTE 0,0 e 0,75: compara com o espaçamento da régua."""

import json
import statistics as st

from tab import audio_alinhar as aa
from tab.audio_extrair import garantir, ler

PRODUTO = "data/saida/conserto_v2/mvp.json"
VIDEO = "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
REGUA = "data/saida/audio/a1/atraso_mvp.json"


def main():
    with open(PRODUTO, encoding="utf-8") as f:
        oculto = aa.esconder_marcador(json.load(f))
    flac, meta = garantir(VIDEO)
    amostras, taxa = ler(flac)
    t_am0 = float(meta["t_amostra0"])
    reg = json.load(open(REGUA, encoding="utf-8"))
    por = {}
    for e in reg["eventos"]:
        if e["passada2"]["fluxo"]["t_som"] is not None:
            por.setdefault((e["tela"], e["exibicao"]), []).append((e["coluna"], e["passada2"]["fluxo"]["t_som"]))
    espac = {}
    for k, pts in por.items():
        pts.sort()
        d = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(pts, pts[1:]) if b[0] - a[0] == 1]
        espac[k] = st.median(d) if d else None
    for q in (0.0, 0.75):
        aa.QUANTIL_PICO_FORTE = q
        saida = aa.alinhar(oculto, amostras, taxa, t_am0, metodo="onsets")
        Ts = {(e["tela"], e["exibicao"]): e.get("T_estimado_s") for e in saida["exibicoes"]}
        ok = sum(1 for k in Ts if espac.get(k) and abs(Ts[k] / espac[k] - 1) <= 0.15)
        dobro = sum(1 for k in Ts if espac.get(k) and Ts[k] / espac[k] > 1.5)
        erro = [abs(Ts[k] / espac[k] - 1) for k in Ts if espac.get(k)]
        print(f"QUANTIL={q}: T dentro de 15% do espaçamento da régua em {ok} de {len(Ts)} exibições | T ~ dobro (>1,5x) em {dobro} | erro relativo mediano {st.median(erro):.3f}", flush=True)
        for k in sorted(Ts):
            print(f"   t{k[0]} e{k[1]}: T={Ts[k]:.3f} espac_regua={espac.get(k) and round(espac[k], 3)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
