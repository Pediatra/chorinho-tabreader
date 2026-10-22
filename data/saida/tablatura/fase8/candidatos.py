"""Candidatos a ouro expandido (Fase 8, T8.1). NÃO é código do projeto.

Lê ``data/saida/censo/v2/censo_v2_completo.jsonl``, escolhe 3 vídeos por canal pelos
critérios do plano, grava ``candidatos.json`` e uma folha ``folha_<canal>.jpg`` por canal
(3 candidatos x 3 instantes com tablatura, caixa vermelha desenhada). Os quadros vêm do
cache (``tab.cache``); nada é decodificado do acervo, e nada é escrito fora de ``fase8/``.

Uso (dentro do container, a partir da raiz do repo):
    python data/saida/fase8/candidatos.py
"""

import collections
import json
import os
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tab import cache  # noqa: E402

CENSO = os.path.join(ROOT, "data", "saida", "censo", "v2", "censo_v2_completo.jsonl")
SAIDA = os.path.join(ROOT, "data", "saida", "fase8")
MODO = cache.ModoCache(usar=True, formato="png")

CANAIS = [
    "guitar dell ́arte",
    "leonardo ramos",
    "robert lunn",
    "mr. tabs",
    "iwaki",
    "kenneth acoustic",
    "shin izumi",
    "pablo romé",
    "kimny's guitar",
]
#: Canais em que a forma "rolante" precisa de ao menos 1 candidato.
EXIGE_ROLANTE = {"leonardo ramos", "mr. tabs", "kenneth acoustic"}

FRAC_MIN = 0.6
DUR_ALVO = 180.0
FAIXAS = [(90.0, 300.0), (60.0, 420.0)]
N_CANDIDATOS = 3

FRAME_L, FRAME_A = 626, 352
MARGEM = 10
CAB_LINHA = 40
CAB_QUADRO = 28
FONTE = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONTE_NEG = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def chave_canal(nome):
    """Chave de comparação: sem acentos/marcas combinantes, minúscula, espaço simples."""
    s = unicodedata.normalize("NFKD", nome)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def slug_ascii(nome):
    """Nome de arquivo ASCII do canal (ex.: 'pablo_rome')."""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else "_" for c in s.lower())
    return "_".join(p for p in s.split("_") if p)


def fmt_frac(x):
    """Fração com vírgula decimal, como no português (0,83)."""
    return f"{x:.2f}".replace(".", ",")


def carregar():
    """Lê o jsonl do censo: uma linha por vídeo."""
    with open(CENSO, encoding="utf-8") as fh:
        return [json.loads(linha) for linha in fh if linha.strip()]


def preenchido(r):
    """Forma e marcador preenchidos (o censo só os preenche em parte dos vídeos)."""
    return r.get("forma") is not None and r.get("marcador") is not None


def combo(r):
    """Par (forma, marcador) de um vídeo."""
    return (r.get("forma"), r.get("marcador"))


def passa_base(r):
    """Filtros 2 e 4: tablatura com fração mínima, e vídeo na horizontal."""
    info = r["info"]
    return (
        bool(r.get("tablatura"))
        and (r.get("frac_tablatura") or 0.0) >= FRAC_MIN
        and info["largura"] > info["altura"]
    )


def na_faixa(r, faixa):
    """Filtro 3: duração dentro da faixa (segundos)."""
    d = r["info"]["duracao_s"]
    return faixa[0] <= d <= faixa[1]


def escolher_canal(nome, rows):
    """Escolhe até 3 candidatos de um canal e devolve o registro da escolha."""
    do_canal = [r for r in rows if chave_canal(r["canal"]) == chave_canal(nome)]
    canal_real = do_canal[0]["canal"] if do_canal else nome
    preench = [r for r in do_canal if preenchido(r)]
    modal = (
        collections.Counter(combo(r) for r in preench).most_common(1)[0][0]
        if preench
        else None
    )
    filtros = {
        "videos": len(do_canal),
        "forma_marcador_preenchidos": len(preench),
        "tab_frac_ge_0_6": 0,
        "paisagem": 0,
    }
    base = [r for r in preench if bool(r.get("tablatura"))]
    base = [r for r in base if (r.get("frac_tablatura") or 0.0) >= FRAC_MIN]
    filtros["tab_frac_ge_0_6"] = len(base)
    base = [r for r in base if r["info"]["largura"] > r["info"]["altura"]]
    filtros["paisagem"] = len(base)

    usada = None
    pool = []
    for faixa in FAIXAS:
        pool = [r for r in base if na_faixa(r, faixa)]
        filtros[f"duracao_{int(faixa[0])}_{int(faixa[1])}"] = len(pool)
        if len(pool) >= N_CANDIDATOS:
            usada = faixa
            break
    if usada is None:
        usada = FAIXAS[-1]
        pool = [r for r in base if na_faixa(r, usada)]

    ordenados = sorted(
        pool,
        key=lambda r: (
            combo(r) != modal,
            -(r.get("frac_tablatura") or 0.0),
            abs(r["info"]["duracao_s"] - DUR_ALVO),
            r["arquivo"],
        ),
    )
    escolhidos = ordenados[:N_CANDIDATOS]
    nota_rolante = None
    if chave_canal(nome) in EXIGE_ROLANTE and not any(
        r.get("forma") == "rolante" for r in escolhidos
    ):
        rol = [r for r in ordenados if r.get("forma") == "rolante"]
        if rol:
            escolhidos = escolhidos[: N_CANDIDATOS - 1] + [rol[0]]
            nota_rolante = "incluído 1 rolante (regra de canal)"
        else:
            nota_rolante = "nenhum rolante passou nos filtros"
    elif chave_canal(nome) in EXIGE_ROLANTE:
        nota_rolante = "rolante já presente entre os 3"

    return {
        "canal": canal_real,
        "canal_chave": chave_canal(nome),
        "slug": slug_ascii(nome),
        "combo_modal": list(modal) if modal else None,
        "filtros": filtros,
        "faixa_duracao_usada": list(usada),
        "alargado": usada != FAIXAS[0],
        "nota_rolante": nota_rolante,
        "candidatos": [_candidato(r) for r in escolhidos],
    }


def _instantes_tab(r):
    """Índices k (0..11) dos instantes com tablatura, em ordem."""
    return [k for k, inst in enumerate(r["instantes"]) if inst.get("tab")]


def _candidato(r):
    """Registro serializável de um candidato, com os t dos instantes com TAB."""
    ks = _instantes_tab(r)
    return {
        "arquivo": r["arquivo"],
        "nome": os.path.splitext(os.path.basename(r["arquivo"]))[0],
        "duracao_s": round(r["info"]["duracao_s"], 1),
        "frac_tablatura": round(r["frac_tablatura"], 3),
        "forma": r["forma"],
        "marcador": r["marcador"],
        "av1": bool(r.get("av1")),
        "largura": r["info"]["largura"],
        "altura": r["info"]["altura"],
        "chave": r["chave"],
        "t_instantes_tab": [r["instantes"][k]["t"] for k in ks],
        "k_instantes_tab": ks,
        "caixas": {
            str(k): r["instantes"][k]["rect"] for k in ks if r["instantes"][k].get("rect")
        },
        "quadros_escolhidos": [],
    }


def _quadro(cand, k):
    """Quadro de presença do instante k (BGR), do cache; None se faltar."""
    pasta = cache.pasta_do_video(cand["chave"], MODO)
    arq = cache.caminho_do_quadro(pasta, f"presenca_{k:02d}", MODO.formato)
    if not arq.exists():
        return None
    return cache.ler_quadro(arq)


def _ajustar(img_bgr, rect):
    """Caixa vermelha no quadro nativo, depois redimensiona (letterbox) para FRAME_L x FRAME_A.

    Devolve RGB, para juntar com o texto do PIL.
    """
    if rect is not None:
        x0, y0, x1, y1 = (int(v) for v in rect)
        espessura = max(3, round(img_bgr.shape[1] / 320))
        cv2.rectangle(img_bgr, (x0, y0), (x1, y1), (0, 0, 255), espessura)
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    e = min(FRAME_L / w, FRAME_A / h)
    nw, nh = max(1, round(w * e)), max(1, round(h * e))
    red = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)
    quadro = np.full((FRAME_A, FRAME_L, 3), 24, np.uint8)
    y0, x0 = (FRAME_A - nh) // 2, (FRAME_L - nw) // 2
    quadro[y0 : y0 + nh, x0 : x0 + nw] = red
    return quadro


def _faixa_texto(largura, altura, texto, tam, negrito=False):
    """Faixa RGB com o texto (acentos e vírgula funcionam: PIL, não cv2)."""
    fonte = ImageFont.truetype(FONTE_NEG if negrito else FONTE, tam)
    tela = Image.new("RGB", (largura, altura), (30, 30, 30))
    ImageDraw.Draw(tela).text((6, altura // 2), texto, font=fonte, fill=(235, 235, 235), anchor="lm")
    return np.asarray(tela)


def _quadro_faltando(t):
    """Célula cinza, com cabeçalho de tempo, para quadro que não está no cache."""
    cab = _faixa_texto(FRAME_L, CAB_QUADRO, f"t={t:.1f}s", 18, negrito=True)
    corpo = np.full((FRAME_A, FRAME_L, 3), 60, np.uint8)
    tela = Image.fromarray(corpo)
    ImageDraw.Draw(tela).text(
        (FRAME_L // 2, FRAME_A // 2),
        "sem quadro no cache",
        font=ImageFont.truetype(FONTE, 22),
        fill=(255, 210, 120),
        anchor="mm",
    )
    return np.vstack([cab, np.asarray(tela)])


LARGURA_FOLHA = 3 * (FRAME_L + MARGEM) + MARGEM


def folha_canal(bloco, faltas):
    """Grava ``folha_<slug>.jpg``: uma linha por candidato, 3 quadros por linha."""
    fundo = (24, 24, 24)
    linhas = []
    for i, cand in enumerate(bloco["candidatos"], start=1):
        nome = cand["nome"]
        if len(nome) > 60:
            nome = nome[:57] + "..."
        cab = (
            f"C{i} {nome} | {cand['duracao_s']:.0f} s | frac {fmt_frac(cand['frac_tablatura'])}"
            f" | {cand['forma']}/{cand['marcador']}"
        )
        ks = cand["k_instantes_tab"]
        pick = [ks[0], ks[len(ks) // 2], ks[-1]]
        celulas, escolhidos = [], []
        for k in pick:
            t = cand["t_instantes_tab"][ks.index(k)]
            img = _quadro(cand, k)
            rect = cand["caixas"].get(str(k))
            if img is None:
                faltas.append(f"{cand['arquivo']} k={k}")
                celulas.append(_quadro_faltando(t))
                escolhidos.append({"k": k, "t": t, "no_cache": True, "caixa": rect})
                continue
            cab_q = _faixa_texto(FRAME_L, CAB_QUADRO, f"t={t:.1f}s", 18, negrito=True)
            celulas.append(np.vstack([cab_q, _ajustar(img, rect)]))
            escolhidos.append({"k": k, "t": t, "no_cache": False, "caixa": rect})
        cand["quadros_escolhidos"] = escolhidos
        cab_linha = _faixa_texto(LARGURA_FOLHA, CAB_LINHA, cab, 19)
        corpo = np.full((celulas[0].shape[0], LARGURA_FOLHA, 3), fundo, np.uint8)
        for j, c in enumerate(celulas):
            x = MARGEM + j * (FRAME_L + MARGEM)
            corpo[:, x : x + FRAME_L] = c
        linhas.append(np.vstack([cab_linha, corpo]))
    tela = np.vstack(
        [np.vstack([l, np.full((MARGEM, LARGURA_FOLHA, 3), fundo, np.uint8)]) for l in linhas]
    )
    caminho = os.path.join(SAIDA, f"folha_{bloco['slug']}.jpg")
    cv2.imwrite(caminho, cv2.cvtColor(tela, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return caminho


def main():
    """Escolhe os candidatos, grava ``candidatos.json`` e as folhas."""
    os.makedirs(SAIDA, exist_ok=True)
    rows = carregar()
    blocos = [escolher_canal(c, rows) for c in CANAIS]
    faltas = []
    for b in blocos:
        b["folha"] = os.path.relpath(folha_canal(b, faltas), ROOT)
    saida = {
        "gerado_por": "data/saida/fase8/candidatos.py",
        "criterios": {
            "forma_marcador": "preenchidos (não nulos)",
            "tablatura": f"true e frac_tablatura >= {FRAC_MIN}",
            "duracao": "90-300 s; 60-420 s se houver menos de 3",
            "orientacao": "largura > altura",
            "ranking": "combo modal do canal; frac desc; |dur-180| asc",
        },
        "canais": blocos,
        "quadros_faltando_no_cache": faltas,
    }
    with open(os.path.join(SAIDA, "candidatos.json"), "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2)
    for b in blocos:
        print(
            b["canal"], b["filtros"], b["faixa_duracao_usada"], b["nota_rolante"],
            [c["nome"][:40] for c in b["candidatos"]],
        )
    print("faltando no cache:", len(faltas))


if __name__ == "__main__":
    main()
