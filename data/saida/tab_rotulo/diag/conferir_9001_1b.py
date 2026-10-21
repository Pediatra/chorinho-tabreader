"""9001 fase 1b: cada caminho novo (do caminhos.py) é igual ao que o código montava antes."""

import shlex
import sys
from pathlib import Path

sys.path.insert(0, "/app/data/saida/n3")

import medir as M  # noqa: E402
from tab import (  # noqa: E402
    ataque_r4,
    ataque_rotulo,
    avaliar,
    caminhos,
    digito,
    portao,
    presenca_aval,
    regerar_janela,
    simbolo,
    simbolos,
)

A, S, G = Path("/app/artefatos"), Path("/app/data/saida"), Path("/app/data/gold")
pares = {
    "digito.CROPS": (digito.CROPS_SIMBOLOS, S.parent / "gold" / "simbolos_crops"),
    "digito.GOLD": (digito.GOLD_SIMBOLOS, G / "simbolos.json"),
    "digito.GOLD2": (digito.GOLD_SIMBOLOS_2, G / "simbolos_2.json"),
    "frames_gold": (avaliar.FRAMES_GOLD, S / "frames" / "gold"),
    "simbolo.GOLD": (simbolo.GOLD_MARCADOS, G / "simbolos_marcados.json"),
    "simbolo.PASTA": (simbolo.PASTA, G / "simbolos_marcados"),
    "regerar.GOLD": (regerar_janela.GOLD, G / "simbolos_marcados.json"),
    "portao.GOLD": (portao.GOLD_PORTAO, caminhos.GABARITO.with_name("portao.json")),
    "portao.FOLHAS": (portao.FOLHAS_PORTAO, S / "frames"),
    "presenca": (presenca_aval.GOLD_QUADROS, G / "presenca_quadros.json"),
    "simbolos.MODELO": (simbolos.MODELO_OFICIAL, A / "oficial_2" / "glifo_sint.pt"),
    "calibrado": (ataque_rotulo.DETECTOR_CALIBRADO,
                  A / "detector_tab_final_atqt_s1" / "modelo.pt"),
    "padrao": (caminhos.DETECTOR_PADRAO, A / "detector_tab_final_s1_ger" / "modelo.pt"),
    "modelo_padrao": (caminhos.MODELO_PADRAO, A / "oficial_3" / "glifo_sint.pt"),
    "video": (caminhos.VIDEO_SIMBOLOS, S / "video"),
    "medir.OURO": (M.OURO, G / "ouro_video"),
    "medir.BASE": (M.MODELO_BASE, A / "oficial_3" / "glifo_sint.pt"),
    "medir.v3_s1": (M.DETECTORES_CAMINHO["v3_s1"], A / "detector_tab_v3_s1/modelo.pt"),
}


def _antigo(versao: str, dobra: int, semente: int) -> Path:
    """O nome do peso como o ``ataque_r4.modelo_da_dobra`` montava antes da 1b."""
    if versao != "ger":
        nome = (
            f"detector_tab_final_{versao}_s{semente}"
            if dobra == 0
            else f"detector_tab_v3ft_d{dobra}_{versao}_s{semente}"
        )
    elif dobra == 0:
        nome = f"detector_tab_final_s{semente}_ger"
    else:
        nome = f"detector_tab_v3ft_d{dobra}_ger" + ("" if semente == 1 else f"_s{semente}")
    return A / nome / "modelo.pt"


for d in range(5):
    for v in ("ger", "atqa", "atqt", "atqe"):
        for s in (1, 2, 3):
            pares[f"r4 {v} d{d} s{s}"] = (ataque_r4.modelo_da_dobra(v, d, s), _antigo(v, d, s))
            if d == 0 or v != "ger":
                assert pares[f"r4 {v} d{d} s{s}"][0].exists(), (v, d, s)
assert portao.POSITIVOS_REAIS[0] == "data/saida/frames/sky4_t88.png"
assert portao.NEGATIVOS_REAIS[3][0] == "data/saida/ouro_novos/01_guitar dell ́a/auto.json"
antigo = {}
for linha in (S / "barline_fina/run.sh").read_text(encoding="utf-8").splitlines():
    if linha.startswith("rodada "):
        _, _n, video, _f, slug = shlex.split(linha)
        antigo[slug] = video
assert list(M.videos_do_run().items()) == list(antigo.items())
ruins = [k for k, (a, b) in pares.items() if a != b]
print(f"{len(pares) + 5} conferidos; diferentes: {ruins}")
raise SystemExit(1 if ruins else 0)
