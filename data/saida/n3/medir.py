"""Medição n3: BASE (pré-preenchimento do ouro) x DETECTOR neural, no mesmo quadro.

Para cada tela conferida do ouro (data/gold/ouro_video/<slug>.json):
  quadro em quadro_ref_s -> painel (escolher_ou_mascara) -> segmentar(roi) (passo,
  linhas_y) -> BASE = ler_notas (glifo oficial_3) e DETECTOR = detectar(modelo, roi,
  linhas_y, passo) com x somado ao x0 do painel. Casamento e métricas pela função de
  tab.avaliar_video (_metricas_par, meia = FRACAO_PASSO * passo).

Saídas em data/saida/n3/: tabela.txt e vis_*.png (2 vídeos de maior |dF1|).

Uso (dentro do container, cwd /app):
    python /app/data/saida/n3/medir.py
    MEDIR_CPU=1 python ...   # força CPU (VRAM insuficiente)
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from collections import Counter
from pathlib import Path

if os.environ.get("MEDIR_CPU"):
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

sys.path.insert(0, "/app")

import cv2  # noqa: E402

from tab import caminhos, detector_tab, leitor  # noqa: E402
from tab.avaliar_video import (  # noqa: E402
    FRACAO_PASSO,
    NotaPrevista,
    _metricas_par,
    casar_notas,
)
from tab.digito import carregar as carregar_discriminador  # noqa: E402
from tab.ouro_video import ler_notas  # noqa: E402
from tab.painel import escolher_ou_mascara  # noqa: E402
from tab.reconhecer import ALGARISMOS, carregar_modelo  # noqa: E402
from tab.tabseg import segmentar  # noqa: E402

RAIZ = caminhos.RAIZ
SAIDA = caminhos.SAIDA / "n3"
OURO = caminhos.OURO_VIDEO
MODELO_BASE = caminhos.MODELO_PADRAO
DETECTORES_CAMINHO = {
    "s1": caminhos.PESOS_TABLATURA / "detector_tab_s1" / "modelo.pt",
    "s2": caminhos.PESOS_TABLATURA / "detector_tab_s2" / "modelo.pt",
    "s3": caminhos.PESOS_TABLATURA / "detector_tab_s3" / "modelo.pt",
    "v2_s1": caminhos.PESOS_TABLATURA / "detector_tab_v2_s1" / "modelo.pt",
    "v2_s2": caminhos.PESOS_TABLATURA / "detector_tab_v2_s2" / "modelo.pt",
    "v2_s3": caminhos.PESOS_TABLATURA / "detector_tab_v2_s3" / "modelo.pt",
    "v3_s1": caminhos.PESOS_TABLATURA / "detector_tab_v3_s1" / "modelo.pt",
    "v3_s2": caminhos.PESOS_TABLATURA / "detector_tab_v3_s2" / "modelo.pt",
    "v3_s3": caminhos.PESOS_TABLATURA / "detector_tab_v3_s3" / "modelo.pt",
}
SAIDA_TABELA = "tabela_v3.txt"
COR_OURO = (0, 200, 0)  # verde (BGR)
COR_BASE = (255, 0, 0)  # azul
COR_DET = (0, 0, 255)  # vermelho
CONTAGENS = ("notas_ouro", "entregues", "casadas", "casa_certa", "inventadas", "perdidas")
EXTRA_SLUG = "tabroom_335_larry_carlton_fingerstyle_guitar"
FRACAO_LABEL = 0.3  # deslocamento vertical (fração do passo) para não sobrepor marcas


def log(msg: str) -> None:
    """Imprime progresso com descarga imediata."""
    print(msg, flush=True)


#: Os 7 ouros das linhas `rodada` de barline_fina/run.sh, na ordem de lá (decisão 9001,
#: fase 1b: o vídeo vem do campo `video` do próprio ouro, e o run.sh deixa de ser lido).
SLUGS_DO_RUN = (
    "retrato_brasileiro_v2",
    "greensleeves_guia_de_estudio_partitura_tab_pdf",
    "gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar",
    "south_american_music_easy_guitar_tutorial_with_sheet_and_tab",
    "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover",
    "la_vie_en_rose_edith_piaf_tab",
    "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics",
)


def videos_do_run() -> dict[str, str]:
    """Slug -> caminho do vídeo no container, pelo campo `video` de cada ouro."""
    return {
        slug: "/acervo/"
        + json.loads((OURO / f"{slug}.json").read_text(encoding="utf-8"))["video"]
        for slug in SLUGS_DO_RUN
    }


def carregar_detectores() -> dict[int, object]:
    """Carrega os detectores cujos pesos existem; os ausentes são listados."""
    carregados: dict[int, object] = {}
    for k, caminho in DETECTORES_CAMINHO.items():
        if caminho.exists():
            log(f"detector {k}: carregando {caminho}")
            carregados[k] = detector_tab.carregar(caminho)
        else:
            log(f"detector {k}: ausente ({caminho}), não medido")
    return carregados


def _casadas_por_corda(notas_ouro: list[dict], previstas, meia: float) -> Counter:
    """Conta, por corda do ouro, as notas do ouro casadas com alguma previsão."""
    pares = casar_notas(notas_ouro, previstas, meia)
    return Counter(int(notas_ouro[i]["corda"]) for i, _ in pares)


def medir_tela(tela: dict, video: str, base, detectores, disc) -> dict:
    """Mede uma tela do ouro: base e detectores no mesmo quadro."""
    modelo, rotulos, dev = base
    reg: dict = {
        "id": tela["id"],
        "quadro_ref_s": float(tela["quadro_ref_s"]),
        "notas_ouro": tela["notas"],
        "cand": None,
        "passo": 0.0,
        "linhas": [],
        "base": [],
        "det": {},
        "tecnicas": {},
        "sem_painel": False,
        "corda_base": Counter(),
        "corda_det": {},
        "det_prev": {},
        "det_raw": {},
        "meia": 0.0,
    }
    frame = leitor.quadro_em(video, reg["quadro_ref_s"])
    cand = escolher_ou_mascara(frame) if frame is not None else None
    grade = segmentar(cand.roi) if cand is not None else None
    if cand is None or grade is None or grade.passo <= 0:
        reg["sem_painel"] = True
        reg["m_base"] = _metricas_par(tela["notas"], [], 0.0)
        reg["m_det"] = {
            k: _metricas_par(tela["notas"], [], 0.0) for k in detectores
        }
        return reg

    passo = float(grade.passo)
    meia = FRACAO_PASSO * passo
    lida = ler_notas(cand, modelo, rotulos, dev, disc)
    previstas_base = [
        NotaPrevista(
            int(n["corda"]), int(n["casa"]), float(n["x_centro_quadro"]), None
        )
        for n in lida["notas"]
    ]
    reg.update(
        cand=cand,
        passo=passo,
        linhas=list(grade.linhas_y),
        base=[
            (int(n["corda"]), int(n["casa"]), float(n["x_centro_quadro"]))
            for n in lida["notas"]
        ],
    )
    reg["m_base"] = _metricas_par(tela["notas"], previstas_base, meia)
    reg["meia"] = meia
    reg["corda_base"] = _casadas_por_corda(tela["notas"], previstas_base, meia)

    reg["m_det"] = {}
    for k, modelo_det in detectores.items():
        notas_d = detector_tab.detectar(modelo_det, cand.roi, grade.linhas_y, passo)
        numericas = [n for n in notas_d if n["rotulo"] in ALGARISMOS]
        previstas = [
            NotaPrevista(
                int(n["corda"]), int(n["rotulo"]), cand.x0 + float(n["x"]), None
            )
            for n in numericas
        ]
        reg["det"][k] = [
            (p.corda, p.casa, p.x) for p in previstas
        ]
        reg["tecnicas"][k] = Counter(t for n in notas_d for t in n["tecnica"])
        reg["m_det"][k] = _metricas_par(tela["notas"], previstas, meia)
        reg["corda_det"][k] = _casadas_por_corda(tela["notas"], previstas, meia)
        reg["det_prev"][k] = previstas
        reg["det_raw"][k] = numericas
    return reg


def medir_video(slug: str, video: str, base, detectores, disc) -> list[dict]:
    """Mede todas as telas conferidas de um vídeo."""
    ouro = json.loads((OURO / f"{slug}.json").read_text(encoding="utf-8"))
    telas = [t for t in ouro["telas"] if t.get("conferida")]
    regs = []
    for tela in telas:
        try:
            reg = medir_tela(tela, video, base, detectores, disc)
        except Exception:  # noqa: BLE001 - registra e segue
            log(f"  FALHA tela {tela['id']}:\n{traceback.format_exc()}")
            reg = {
                "id": tela["id"],
                "quadro_ref_s": float(tela["quadro_ref_s"]),
                "notas_ouro": tela["notas"],
                "cand": None,
                "passo": 0.0,
                "linhas": [],
                "base": [],
                "det": {},
                "tecnicas": {},
                "sem_painel": True,
                "erro": True,
                "m_base": _metricas_par(tela["notas"], [], 0.0),
                "m_det": {k: _metricas_par(tela["notas"], [], 0.0) for k in detectores},
            }
        log(
            f"  tela {reg['id']} t={reg['quadro_ref_s']:.2f}s "
            f"painel={'nao' if reg['sem_painel'] else 'sim'} "
            f"base={reg['m_base']['casadas']}/{reg['m_base']['entregues']}"
            + "".join(
                f" {k}={reg['m_det'][k]['casadas']}/{reg['m_det'][k]['entregues']}"
                for k in detectores
            )
            + f" ouro={len(tela['notas'])}"
        )
        regs.append(reg)
    return regs


def resumo(ms: list[dict]) -> dict:
    """Soma as contagens de métricas por tela e calcula as razões."""
    s = {k: sum(m[k] for m in ms) for k in CONTAGENS}
    s["P"] = s["casadas"] / s["entregues"] if s["entregues"] else None
    s["R"] = s["casadas"] / s["notas_ouro"] if s["notas_ouro"] else None
    s["AC"] = s["casa_certa"] / s["casadas"] if s["casadas"] else None
    return s


def fmt(v: float | None) -> str:
    """Formata razão com três casas, ou '-' se o denominador é zero."""
    return "  -  " if v is None else f"{v:.3f}"


def linha_resumo(nome: str, s: dict) -> str:
    """Uma linha da tabela: contagens e razões."""
    return (
        f"  {nome:<8} ouro={s['notas_ouro']:>4} entregues={s['entregues']:>4} "
        f"casadas={s['casadas']:>4} casa_certa={s['casa_certa']:>4} "
        f"inventadas={s['inventadas']:>4} perdidas={s['perdidas']:>4} | "
        f"P={fmt(s['P'])} R={fmt(s['R'])} casa={fmt(s['AC'])}"
    )


def f1(s: dict) -> float:
    """F1 a partir de precisão e revocação (0 se alguma é None ou zero)."""
    p, r = s["P"], s["R"]
    return 2 * p * r / (p + r) if p and r else 0.0


def desenhar(reg: dict, slug: str, nome_arquivo: Path, k_det: int) -> None:
    """Imagem do painel: ouro verde, base azul, detector vermelho (sk_det)."""
    cand = reg["cand"]
    escala = 2
    img = cv2.resize(
        cand.roi, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC
    )
    passo = reg["passo"]
    linhas = reg["linhas"]

    def ponto(corda: int, x_quadro: float, desloc: float) -> tuple[int, int]:
        x = x_quadro - cand.x0
        y = linhas[corda - 1] + desloc * passo
        return int(x * escala), int(y * escala)

    for n in reg["notas_ouro"]:
        corda, casa = int(n["corda"]), int(n["casa"])
        x = float(n["x_centro_quadro"])
        px, py = ponto(corda, x, -FRACAO_LABEL)
        cv2.circle(img, (px, py), 7, COR_OURO, 2)
        cv2.putText(
            img, str(casa), (px + 8, py - 6),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, COR_OURO, 1,
        )
    for corda, _casa, x in reg["base"]:
        cv2.circle(img, ponto(corda, x, 0.0), 5, COR_BASE, 2)
    for corda, _casa, x in reg.get("det", {}).get(k_det, []):
        cv2.circle(img, ponto(corda, x, FRACAO_LABEL), 5, COR_DET, 2)
    legenda = [
        ("ouro (verde)", COR_OURO),
        ("base oficial_3 (azul)", COR_BASE),
        (f"detector s{k_det} (vermelho)", COR_DET),
    ]
    for i, (texto, cor) in enumerate(legenda):
        cv2.putText(
            img, texto, (10, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2
        )
    cv2.putText(
        img, f"{slug} tela {reg['id']} t={reg['quadro_ref_s']:.2f}s",
        (10, img.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
    )
    cv2.imwrite(str(nome_arquivo), img)


def main() -> int:
    """Roda a medição, grava tabela.txt e as imagens dos dois vídeos de maior |dF1|."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    videos = videos_do_run()
    extra = json.loads((OURO / f"{EXTRA_SLUG}.json").read_text(encoding="utf-8"))
    videos[EXTRA_SLUG] = "/acervo/" + extra["video"]
    detectores = carregar_detectores()
    log("carregando base (oficial_3) e discriminador de dígito")
    base = carregar_modelo(str(MODELO_BASE))
    disc = carregar_discriminador()

    por_video: dict[str, list[dict]] = {}
    videos_por_slug: dict[str, str] = {}
    for slug, video in videos.items():
        if not (OURO / f"{slug}.json").exists():
            log(f"sem ouro: {slug}")
            continue
        log(f"== {slug}")
        videos_por_slug[slug] = video
        por_video[slug] = medir_video(slug, video, base, detectores, disc)

    ks = sorted(detectores)
    linhas: list[str] = []
    w = linhas.append
    w("Medição n3: BASE (pré-preenchimento, glifo oficial_3) x DETECTOR neural.")
    w("Mesmo quadro (quadro_ref_s de cada tela conferida), mesmo painel e mesma grade")
    w("(escolher_ou_mascara + segmentar). Casamento: tab.avaliar_video._metricas_par,")
    w("meia = 0,5 * passo, x = centro do token, mesma corda. Casa certa = entre casadas.")
    w(f"Detectores medidos: {ks or 'nenhum (pesos ausentes)'}")
    w("Técnica: NÃO medível. O ouro não tem campo de técnica nas notas (só corda, casa,")
    w("x_quadro, x_centro_quadro); só há a contagem de técnicas que o detector prevê.")
    w("")

    def bloco(nome: str, regs: list[dict]) -> list[dict]:
        """Escreve um vídeo ou o total; devolve os resumos [base, s1, s2, s3]."""
        resumos = {"base": resumo([r["m_base"] for r in regs])}
        for k in ks:
            resumos[k] = resumo([r["m_det"][k] for r in regs])
        w(f"## {nome}")
        w(linha_resumo("BASE", resumos["base"]))
        for k in ks:
            w(linha_resumo(k, resumos[k]))
        for k in ks:
            pior = []
            for metrica in ("P", "R"):
                b = resumos["base"][metrica] or 0.0
                d = resumos[k][metrica] or 0.0
                if d < b:
                    pior.append(f"{metrica} {d:.3f}<{b:.3f}")
            if pior:
                w(f"  !! {k} PIOR que a base em: {'; '.join(pior)}")
        if ks:
            tec = Counter()
            for r in regs:
                for k in ks:
                    tec.update(r["tecnicas"].get(k, Counter()))
            w(f"  tecnicas previstas pelo detector (sem gabarito): {dict(tec)}")
        if nome.startswith(EXTRA_SLUG):
            w("  revocacao por corda (casadas / notas do ouro na corda):")
            ouro_corda: Counter = Counter()
            for r in regs:
                ouro_corda.update(int(n["corda"]) for n in r["notas_ouro"])
            for c in range(1, 7):
                tot = ouro_corda.get(c, 0)
                cb = sum(r["corda_base"].get(c, 0) for r in regs)
                linha = f"    corda {c}: ouro={tot:>3}  BASE {cb:>3}/{tot:<3} " + (
                    f"{cb / tot:.3f}" if tot else "  -  "
                )
                for k in ks:
                    cd = sum(r["corda_det"].get(k, Counter()).get(c, 0) for r in regs)
                    linha += f"  {k} {cd:>3}/{tot:<3} " + (
                        f"{cd / tot:.3f}" if tot else "  -  "
                    )
                w(linha)
        n_sem = sum(1 for r in regs if r["sem_painel"])
        if n_sem:
            w(f"  telas sem painel (todas as notas do ouro contam como perdidas): {n_sem}")
        w("")
        return [resumos]

    todos: list[dict] = []
    for slug in por_video:
        regs = por_video[slug]
        todos.extend(regs)
        bloco(slug, regs)
    bloco("TOTAL (todos os vídeos)", todos)

    # Dois vídeos de maior |dF1| (detector s-primeiro-disponível vs base)
    if ks:
        k0 = ks[0]
        dif = {}
        for slug, regs in por_video.items():
            fb = f1(resumo([r["m_base"] for r in regs]))
            fd = f1(resumo([r["m_det"][k0] for r in regs]))
            dif[slug] = fd - fb
        escolhidos = sorted(dif, key=lambda s: abs(dif[s]), reverse=True)[:2]
        w(f"Vídeos para imagem (maior |dF1| do s{k0} contra a base):")
        for slug in escolhidos:
            w(f"  {slug}: dF1={dif[slug]:+.3f}")
        w("")
        for slug in escolhidos:
            curto = slug[:24]
            for reg in por_video[slug]:
                if reg["sem_painel"] or reg["cand"] is None:
                    continue
                destino = SAIDA / f"vis_{curto}_t{reg['id']}.png"
                desenhar(reg, slug, destino, k0)
                w(f"imagem: {destino}")
    (SAIDA / SAIDA_TABELA).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    log("gravado: " + str(SAIDA / SAIDA_TABELA))
    return 0


if __name__ == "__main__":
    sys.exit(main())
