"""Conferência da folha 3 (roda no container, PYTHONPATH=/app).

Para 3 pares (MVP, iwaki, kimny): diferença média de pixels entre A e B em t=1,0 s; instante
do clique em A e em B pela subtração do original (residuo) e pelo pico de energia acima de
1,5 kHz; diferença B-A comparada com o esperado (d ou -d, conforme o alinhador).
"""

import json
import subprocess

import numpy as np

from tab import audio_folha as af

FOLHA = "/app/data/saida/audio/a2/folha"
PRINCIPAIS_VIDEO = ("retrato", "la vie en rose", "from this place")
CHECAGEM = f"{FOLHA}/checagem_folha3"


def quadro(arq: str, t: float) -> np.ndarray:
    """Quadro em cinza (uint8) no instante t, em resolução nativa."""
    larg, alt, _ = af._sondar_video(arq)
    cru = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.6f}", "-i", arq,
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(cru, dtype=np.uint8).reshape(alt, larg)


def pico_acima_1500(amostras: np.ndarray, taxa: int, esperado: float, janela: float) -> float:
    """Instante (no clipe) do máximo de energia acima de 1,5 kHz perto do esperado."""
    x = amostras.astype(np.float64)
    espectro = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1.0 / taxa)
    espectro[freqs < 1500.0] = 0.0
    hp = np.fft.irfft(espectro, n=len(x))
    env = np.abs(hp)
    ini = max(0, round((esperado - janela) * taxa))
    fim = min(len(env), round((esperado + janela) * taxa))
    return (ini + int(np.argmax(env[ini:fim]))) / taxa


plano = json.loads(open(f"{FOLHA}/folha3_pedidos.json", encoding="utf-8").read())
escolhidos = {}
for par in plano:
    nome = par["rotulo"] if "rotulo" in par else None
    for v in PRINCIPAIS_VIDEO:
        if v in json.dumps(par.get("video", "")) and False:
            pass
ch = json.loads(open(f"{FOLHA}/folha3_chave.json", encoding="utf-8").read())
mapa = {c["id"]: c for c in ch}
for par in plano:
    rot = mapa[par["id"]]["video"]
    if rot in PRINCIPAIS_VIDEO and rot not in escolhidos and not par["atencao"]:
        escolhidos[rot] = par
for rot, par in escolhidos.items():
    d = par["d_ms"]
    t_al = par["t_alinhador"]
    video = par["video"]
    inicio = af._primeiro_quadro_a_partir(video, t_al - af.JANELA_S)
    _, meta = af.garantir(video)
    ca_al = af.instante_de(af.indice_de(t_al, meta), meta) - inicio
    ca_des = af.instante_de(af.indice_de(t_al + d / 1000.0, meta), meta) - inicio
    if par["alinhador_e"] == "A":
        rel_a, rel_b = ca_al, ca_des
    else:
        rel_a, rel_b = ca_des, ca_al
    esperado_ba = (rel_b - rel_a)
    a = f"{FOLHA}/folha3/{par['id']}_a.mp4"
    b = f"{FOLHA}/folha3/{par['id']}_b.mp4"
    qa = quadro(a, 1.0).astype(np.float64)
    qb = quadro(b, 1.0).astype(np.float64)
    dif_px = float(np.mean(np.abs(qa - qb)))
    orig = af._audio_mono(video, inicio) * af.GANHO_MUSICA
    resultados = {}
    for letra, arq, rel in (("A", a, rel_a), ("B", b, rel_b)):
        am = af._audio_mono(arq, None)
        lag = af._atraso_amostras(am, orig)
        res = af._residuo(am, orig, lag)
        t_sub, sim = af._achar_clique(res, rel)
        t_hp = pico_acima_1500(am, af.TAXA_MIX, rel, 0.150)
        resultados[letra] = (t_sub, t_hp, sim, rel)
    print(f"== {rot} {par['id']} d={d} alinhador_e={par['alinhador_e']} t_al={t_al:.6f}")
    print(f"  pixels |A-B| t=1.0s media abs: {dif_px:.4f}")
    for letra in "AB":
        t_sub, t_hp, sim, rel = resultados[letra]
        print(f"  clique {letra}: esperado {rel*1000:.3f} ms | subtracao {t_sub*1000:.3f} ms "
              f"(erro {(t_sub-rel)*1000:+.3f}) | pico>1.5kHz {t_hp*1000:.3f} ms "
              f"(erro {(t_hp-rel)*1000:+.3f}) | sim {sim:.3f}")
    ba_sub = resultados["B"][0] - resultados["A"][0]
    ba_hp = resultados["B"][1] - resultados["A"][1]
    print(f"  B-A esperado {esperado_ba*1000:+.3f} ms | subtracao {ba_sub*1000:+.3f} ms "
          f"(erro {(ba_sub-esperado_ba)*1000:+.3f}) | pico>1.5kHz {ba_hp*1000:+.3f} ms "
          f"(erro {(ba_hp-esperado_ba)*1000:+.3f})")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "1.0", "-i", a,
                    "-frames:v", "1", f"{CHECAGEM}/{par['id']}_a_t1s.png"], check=True)
    print(f"  quadro salvo: {CHECAGEM}/{par['id']}_a_t1s.png")
