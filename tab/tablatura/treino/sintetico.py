"""Gerador sintético de tablatura + treino + aferição no gabarito real.

Por que sintético: o único número ruim do sistema é o reconhecimento do algarismo em
canal NOVO (0,70). Dado real rotulado é caro; dado sintético tem rótulo EXATO e cobre
as famílias medidas (claro/escuro, linha sólida/tracejada, passo 14-36 px, acorde
empilhado, cor de voz, harmônico `<n>`, ligado, rótulo TAB).

Ponto central: o sintético NÃO é usado cru. Ele passa pelo MESMO extrator
(`tabseg.segmentar`) e o rótulo vem do que foi desenhado — assim a distribuição de
treino é idêntica à de inferência (inclusive os cortes da faixa da corda).

Uso:
    python -m tab.sintetico --n-linhas 400 --epocas 25 --saida artefatos
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import random
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont

from tab.comum.caminhos import GABARITO, PESOS_TABLATURA
from tab.comum.semente import fixar_semente
from tab.tablatura.leitura.glyph_bench import GlifoCNN
from tab.tablatura.leitura.glyphset import normalizar
from tab.tablatura.leitura.tabseg import segmentar
from tab.tablatura.ouro.avaliar import avaliar_com_modelo

# Exigido pelo cuBLAS no modo determinístico (ver `fixar_semente`). Precisa estar
# definido ANTES da primeira multiplicação de matrizes na GPU, por isso fica aqui
# e não dentro da função.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

#: Fontes do gerador. Fonte aqui é dependência de DADO: trocar de fonte muda a
#: distribuição do treino e, portanto, o número medido.
NOMES_FONTES = ("LiberationSans-Bold.ttf", "LiberationSerif-Bold.ttf")

#: Presets de fonte aceitos por `--fontes`: (nomes, chance de o buraco cortar a corda
#: sob a fonte `Regular`, se a fonte `Regular` é desenhada GRANDE: 1,0 a 1,4 passo, como
#: o algarismo de 0,85 passo do robert lunn, e se metade das linhas leva desfoque
#: gaussiano 0,5-0,9 px: o traço fino do vídeo vira cinza e quebra na binarização). `padrao` reproduz os pesos `oficial_*`. `fina` acrescenta
#: `LiberationSerif-Regular` (serifa fina, tipo Times, do canal robert lunn; o `0`
#: lido como `8` e o `4`/`2` como `tecnica` no ouro da Gymnopédie). `fina2` dobra o
#: peso da fonte fina e faz a corda passar por cima dela quase sempre (como no vídeo).
#: As fontes vêm do pacote `fonts-liberation` que o container já instala.
PRESETS_FONTES = {
    "padrao": (NOMES_FONTES, 0.5, False, False),
    "fina": ((*NOMES_FONTES, "LiberationSerif-Regular.ttf"), 0.5, False, False),
    "fina2": (
        (*NOMES_FONTES, *("LiberationSerif-Regular.ttf",) * 2),
        0.15,
        False,
        False,
    ),
    "fina3": (
        (*NOMES_FONTES, *("LiberationSerif-Regular.ttf",) * 2),
        0.15,
        True,
        False,
    ),
    "fina4": ((*NOMES_FONTES, *("LiberationSerif-Regular.ttf",) * 2), 0.15, True, True),
}

#: Onde cada distribuição instala as fontes Liberation: Fedora/openSUSE (host) e
#: Debian/Ubuntu (container). Os caminhos eram fixos do host e o treino passou a
#: falhar dentro do container — melhor falhar do que treinar com outra fonte.
DIRETORIOS_FONTES = (
    "/usr/share/fonts/liberation-sans-fonts",
    "/usr/share/fonts/liberation-serif-fonts",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/TTF",
)


def _resolver_fontes(nomes: tuple[str, ...] = NOMES_FONTES) -> list[str]:
    """Caminhos das fontes do gerador, procurando nos diretórios conhecidos.

    Args:
        nomes: nomes de arquivo das fontes (com repetição = peso).

    Returns:
        Um caminho por nome que for encontrado, na mesma ordem.
    """
    achadas: list[str] = []
    for nome in nomes:
        for diretorio in DIRETORIOS_FONTES:
            caminho = os.path.join(diretorio, nome)
            if os.path.exists(caminho):
                achadas.append(caminho)
                break
    return achadas


FONTES = _resolver_fontes()
CORES_VOZ = [(0, 0, 0), (41, 89, 197), (23, 148, 95), (200, 40, 40)]

#: Casas desenhadas pelo gerador (com repetição = peso) na lista OFICIAL: é a que
#: gerou os pesos `oficial_*` e a régua de 0,949. Não mexer sem trocar o comando
#: registrado em `artefatos/LEIA-ME.md`. Casas 0-10, 12, 14, 15, 17, 19, 21, 24.
CASAS_OFICIAIS = (
    0,
    0,
    0,
    1,
    1,
    2,
    2,
    3,
    3,
    4,
    5,
    5,
    6,
    7,
    8,
    9,
    10,
    12,
    12,
    14,
    15,
    17,
    19,
    21,
    24,
)

#: Lista EXPERIMENTAL com casas 0-24 (cada casa nova uma vez; as baixas seguem com
#: mais peso). Entrou em 2026-10-10 e só é usada com `--casas todas`: os pesos
#: `casas24_*` saíram dela. Não é o padrão porque mudou a distribuição do treino e
#: não melhorou o ouro de vídeo (ver ESTADO.md, 2026-10-10).
CASAS_TODAS = (
    0,
    0,
    0,
    1,
    1,
    2,
    2,
    3,
    3,
    4,
    5,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
)

#: Listas de casas aceitas por `--casas`. O padrão é `oficial`.
LISTAS_CASAS = {"oficial": CASAS_OFICIAIS, "todas": CASAS_TODAS}


def gerar_linha(
    rng: random.Random,
    casas: tuple[int, ...] = CASAS_OFICIAIS,
    escala_larga: bool = False,
    fontes: list[str] | None = None,
    p_buraco_fina: float = 0.5,
    fina_grande: bool = False,
    borrar: bool = False,
) -> tuple[np.ndarray, list[dict]]:
    """Desenha uma linha de tablatura aleatória e devolve (imagem, notas).

    Args:
        rng: gerador aleatório; a sequência de sorteios depende só dele e de ``casas``.
        casas: lista de casas sorteáveis (com repetição = peso).
        escala_larga: se ``True``, metade das linhas desenha algarismo MAIOR que o
            passo (fonte 1,0 a 1,4 passo). Desligado por padrão: com ``False`` a
            sequência de sorteios é a de antes, e os pesos ``oficial_*`` reproduzem.
        fontes: caminhos das fontes (padrão: ``FONTES``).
        p_buraco_fina: chance de a corda ser cortada sob uma fonte ``Regular``.
        borrar: se ``True``, metade das linhas leva desfoque gaussiano de 0,5 a 0,9 px.
        fina_grande: se ``True``, a fonte ``Regular`` é desenhada com 1,0 a 1,4 passo.

    Returns:
        Tupla (imagem BGR, lista de notas desenhadas).
    """
    fontes = FONTES if fontes is None else fontes
    passo = rng.choice([14, 16, 18, 20, 22, 24, 28, 30, 36])
    n_compassos = rng.randint(2, 5)
    n_col = rng.randint(8, 26)
    ti = rng.choice([2, 3])  # espessura da corda
    escuro = rng.random() < 0.45
    tracejada = rng.random() < 0.2 and not escuro
    borda = rng.randint(20, 60)
    larg = borda * 2 + n_col * int(passo * 1.9)
    alt = int(passo * 6 + passo * 1.6)
    fundo = (18, 18, 18) if escuro else (255, 255, 255)
    cor_linha = (200, 200, 200) if escuro else (60, 60, 60)
    img = Image.new("RGB", (int(larg), alt), fundo)
    d = ImageDraw.Draw(img)
    y0 = int(passo * 0.8)
    ys = [y0 + i * passo for i in range(6)]

    for y in ys:  # cordas
        if tracejada:
            x = borda // 2
            while x < larg - borda // 2:
                d.line([(x, y), (x + passo * 0.8, y)], fill=cor_linha, width=ti)
                x += passo * 1.6
        else:
            d.line([(borda // 2, y), (larg - borda // 2, y)], fill=cor_linha, width=ti)
    if rng.random() < 0.5:  # rótulo TAB
        f = ImageFont.truetype(rng.choice(fontes), int(passo * 1.15))
        for j, ch in enumerate("TAB"):
            d.text((borda * 0.25, ys[j] - passo * 0.5), ch, font=f, fill=cor_linha)
    for c in range(1, n_compassos):  # barlines
        x = borda + c * (larg - 2 * borda) / n_compassos
        d.line(
            [(x, ys[0] - passo * 0.2), (x, ys[-1] + passo * 0.2)],
            fill=cor_linha,
            width=max(1, ti - 1),
        )

    # Lixo deliberado: no canal raman korshun sobrevivem ao extrator traços verticais
    # curtos (pedaço de barline dupla / haste), e o modelo era OBRIGADO a chamá-los de
    # algarismo (erros `junk -> 1`, `junk -> 5`). Colher sobras não funciona: medido, o
    # sintético não gera nenhuma. Então o lixo é desenhado de propósito e rotulado "junk".
    notas = []
    # Tamanho da fonte VARIA: o acervo real tem algarismo de 0,38 passo (medido no
    # painel do cifra club) e de 0,6 passo (skyguitar). Com fonte fixa em 0,95 o
    # modelo confundia algarismo pequeno com harmonico <n>.
    tam_fonte = max(6, int(passo * rng.uniform(0.55, 1.0)))
    # Medido (rodada 0009, ouro retrato_brasileiro_v2): o algarismo real tem altura
    # mediana de 0,93 passo; o gerador, no máximo 1,0 de fonte, dava ~0,54 (p90 0,75).
    # Só com `escala_larga` a linha ganha algarismo grande; sem a flag, nenhum sorteio
    # extra acontece e a sequência é a de sempre.
    if escala_larga and rng.random() < 0.5:
        tam_fonte = max(6, int(passo * rng.uniform(1.0, 1.4)))
    for col in range(n_col):
        x = borda + int((col + 0.5) * (larg - 2 * borda) / n_col)
        n_cordas = 1 if rng.random() < 0.6 else rng.randint(2, 4)
        cordas = rng.sample(range(6), n_cordas)
        cor = rng.choice(CORES_VOZ) if rng.random() < 0.25 else (0, 0, 0)
        if escuro and cor == (0, 0, 0):
            cor = (255, 255, 255)
        for c in cordas:
            casa = rng.choice(casas)
            tecnica = None
            txt = str(casa)
            if rng.random() < 0.10:  # harmônico <n>
                tecnica, txt = "harmonico", f"<{casa % 13}>"
            elif rng.random() < 0.35:
                tecnica, txt = rng.choice(["hammer_on", "pull_off"]), str(casa)
            caminho_fonte = rng.choice(fontes)
            tam_glifo = tam_fonte
            if fina_grande and "Regular" in caminho_fonte:
                tam_glifo = max(6, int(passo * rng.uniform(1.0, 1.4)))
            f = ImageFont.truetype(caminho_fonte, tam_glifo)
            bb = d.textbbox((0, 0), txt, font=f)
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            px, py = int(x - w / 2), int(ys[c] - h / 2 - bb[1])
            # Como a corda se comporta no algarismo VARIA por canal (medido):
            #   - MuseScore/Guitar Pro: a corda é CORTADA (buraco) onde o algarismo entra;
            #   - outros canais (ex.: paolo d'angelo): a corda PASSA POR CIMA do algarismo,
            #     o que acrescenta um traço horizontal e fazia `1` ser lido como `4`.
            # O gerador agora sorteia os dois casos; antes só existia o buraco.
            p_buraco = p_buraco_fina if "Regular" in caminho_fonte else 0.5
            if rng.random() < p_buraco:
                d.rectangle(
                    [px - 2, ys[c] - passo * 0.30, px + w + 2, ys[c] + passo * 0.30],
                    fill=fundo,
                )
            d.text((px, py), txt, font=f, fill=cor)
            notas.append(
                {
                    "corda": c + 1,
                    "casa": casa,
                    "tecnica": tecnica,
                    "x": int(x),
                    "x0": int(px),
                    "x1": int(px + w),
                    "texto": txt,
                }
            )
            if tecnica in ("hammer_on", "pull_off") and rng.random() < 0.6:  # ligado
                d.arc(
                    [
                        px - passo * 0.9,
                        ys[c] + passo * 0.25,
                        px + w + passo * 0.9,
                        ys[c] + passo * 1.1,
                    ],
                    200,
                    340,
                    fill=(0, 0, 0) if not escuro else (255, 255, 255),
                    width=max(1, ti - 1),
                )
                if (
                    rng.random() < 0.8
                ):  # diagonal ATRAVESSANDO o algarismo (caso do canal real)
                    d.line(
                        [
                            (px - passo * 0.15, ys[c] - passo * 0.45),
                            (px + w + passo * 0.15, ys[c] + passo * 0.45),
                        ],
                        fill=(0, 0, 0) if not escuro else (255, 255, 255),
                        width=max(1, ti - 1),
                    )
    saida = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    if borrar and rng.random() < 0.5:
        saida = cv2.GaussianBlur(saida, (0, 0), rng.uniform(0.5, 0.9))
    return saida, notas


def conferir_fontes(nomes: tuple[str, ...] = NOMES_FONTES) -> None:
    """Falha cedo e com mensagem útil se as fontes do gerador não existirem.

    Fonte aqui é dependência de DADO, não de desenho: trocar de fonte muda a
    distribuição do sintético e, portanto, o número medido. Melhor quebrar do que
    treinar com outra fonte em silêncio.

    Args:
        nomes: nomes de arquivo exigidos (padrão: ``NOMES_FONTES``).

    Raises:
        SystemExit: se alguma das fontes não for encontrada.
    """
    achadas = _resolver_fontes(nomes)
    if len(achadas) != len(nomes):
        faltando = [n for n in nomes if not any(n in f for f in achadas)]
        raise SystemExit(
            "fontes do gerador ausentes (instale `fonts-liberation` na imagem): "
            + ", ".join(faltando)
            + " | procuradas em: "
            + ", ".join(DIRETORIOS_FONTES)
        )


def montar(
    n_linhas: int,
    seed: int = 0,
    casas: tuple[int, ...] = CASAS_OFICIAIS,
    escala_larga: bool = False,
    preset_fontes: str = "padrao",
) -> tuple[list, list, list]:
    """Gera linhas, passa pelo extrator e casa cada glifo extraído com a nota desenhada.

    Args:
        n_linhas: quantas linhas desenhar (as que não têm 6 cordas são descartadas).
        seed: semente do ``random.Random`` que sorteia as linhas.
        casas: lista de casas do gerador; ver ``LISTAS_CASAS``.
        escala_larga: algarismo maior que o passo em metade das linhas; ver
            ``gerar_linha``.
        preset_fontes: chave de ``PRESETS_FONTES``.

    Returns:
        Tupla (glifos normalizados, rótulos, identificadores de canal).
    """
    nomes, p_buraco_fina, fina_grande, borrar = PRESETS_FONTES[preset_fontes]
    conferir_fontes(nomes)
    fontes = _resolver_fontes(nomes)
    rng = random.Random(seed)
    X, y, canais = [], [], []
    for i in range(n_linhas):
        img, notas = gerar_linha(
            rng,
            casas,
            escala_larga=escala_larga,
            fontes=fontes,
            p_buraco_fina=p_buraco_fina,
            fina_grande=fina_grande,
            borrar=borrar,
        )
        g = segmentar(img)
        if len(g.linhas_y) != 6:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        for gl in g.glifos:
            alvo = None
            for n in notas:
                if n["corda"] == gl.corda and n["x0"] - 2 <= gl.cx <= n["x1"] + 2:
                    alvo = n
                    break
            if alvo is None:
                # Token que não casa com nenhuma nota DESENHADA é, por definição,
                # lixo (resto de corda, pedaço de barline). Antes isso era descartado;
                # agora vira a classe de rejeição — o modelo aprende a dizer "não é
                # algarismo" em vez de ser obrigado a escolher um. Era a maior fonte de
                # erro no canal raman korshun (junk -> "1", junk -> "5").
                continue
            crop = gray[max(0, gl.y0 - 1) : gl.y1 + 1, max(0, gl.x0 - 1) : gl.x1 + 1]
            norm = normalizar(crop)
            if norm is None:
                continue
            if alvo is not None:
                rot = (
                    alvo["tecnica"] if alvo["tecnica"] == "harmonico" else alvo["texto"]
                )
                # Marca FUNDIDA ao algarismo: o token recebe a classe 'tecnica', nao o
                # algarismo. Na rodada 14 eu mantive o rotulo do algarismo e a classe '1'
                # degradou; sinalizando o caso, o algarismo e re-lido do componente dominante.
                if alvo.get("tecnica") in ("hammer_on", "pull_off") and gl.partes >= 2:
                    rot = "tecnica"
            X.append(norm)
            y.append(rot)
            canais.append(f"sint{i}")
    return X, y, canais


def carregar_gabarito(caminho: str | Path = GABARITO):
    """Glifos reais rotulados à mão (só os que têm rótulo)."""
    if not os.path.exists(caminho):
        return [], []
    X, y = [], []
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    for am in dados["amostras"]:
        if am["canal"] == "iwaki":
            continue  # iwaki é usado como calibração, ver abaixo
        for i, rot in am["rotulos"].items():
            X.append((am["canal"], int(i), rot))
            y.append(rot)
    return X, y


def avaliar_no_gabarito(modelo, rotulos, dev) -> dict:
    """Aferição nos glifos REAIS rotulados à mão (nunca vistos no treino sintético).

    Delega para :mod:`tab.avaliar` de propósito: havia **duas** implementações de
    aferição e a que vivia aqui estava errada de dois modos — assumia índices
    contíguos no gabarito (KeyError no `raman`) e avaliava `raman` e `paolo`
    contra o recorte da `sky guitar`, ou seja, contra a imagem errada. Número
    oficial tem uma fonte só.

    Args:
        modelo: classificador já treinado.
        rotulos: classes na ordem de saída do modelo.
        dev: dispositivo onde o modelo está.

    Returns:
        Dicionário com ``acertos`` e ``total``.
    """
    linhas = avaliar_com_modelo(modelo, rotulos, dev)
    for canal, acertos, total in linhas:
        taxa = acertos / total if total else 0.0
        print(f"  canal {canal:<14} {acertos}/{total} = {taxa:.2f}")
    acertos = sum(o for _, o, _ in linhas)
    total = sum(t for _, _, t in linhas)
    print(f"  TOTAL gabarito real: {acertos}/{total} = {acertos / max(1, total):.3f}")
    return {"acertos": acertos, "total": total}


def treinar(X, y, saida: str, epocas: int, lote: int = 128, seed: int = 0):
    fixar_semente(seed)
    rotulos = sorted(set(y))
    idx = {r: i for i, r in enumerate(rotulos)}
    xt = torch.tensor(np.stack(X)[:, None].astype(np.float32) / 255.0)
    yt = torch.tensor([idx[v] for v in y])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = GlifoCNN(len(rotulos)).to(dev)
    otim = torch.optim.AdamW(modelo.parameters(), lr=2e-3, weight_decay=1e-4)
    xt, yt = xt.to(dev), yt.to(dev)
    for ep in range(epocas):
        modelo.train()
        perm = torch.randperm(len(xt), device=dev)
        perda_tot = 0.0
        for i in range(0, len(xt), lote):
            b = perm[i : i + lote]
            otim.zero_grad()
            perda = F.cross_entropy(modelo(xt[b]), yt[b])
            perda.backward()
            otim.step()
            perda_tot += float(perda.detach()) * len(b)
        if (ep + 1) % max(1, epocas // 5) == 0:
            modelo.eval()
            with torch.no_grad():
                acc = float((modelo(xt).argmax(1) == yt).float().mean())
            print(
                f"  época {ep + 1:>3}/{epocas} perda={perda_tot / len(xt):.4f} acc_treino={acc:.4f}",
                flush=True,
            )
    os.makedirs(saida, exist_ok=True)
    # Devolve em modo de avaliação: quem chama vai AFERIR este modelo na sequência,
    # e com Dropout ativo a aferição sai deprimida (medido: 0,771 × 0,865 no disco).
    modelo.eval()
    torch.save(
        {"state_dict": modelo.state_dict(), "rotulos": rotulos},
        os.path.join(saida, "glifo_sint.pt"),
    )
    return modelo, rotulos, dev


def _parser() -> argparse.ArgumentParser:
    """Monta os argumentos da CLI (o padrão de ``--casas`` é ``oficial``).

    Returns:
        O ``ArgumentParser`` do módulo.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-linhas", type=int, default=400)
    ap.add_argument("--epocas", type=int, default=25)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--saida", default=str(PESOS_TABLATURA))
    ap.add_argument("--gabarito", default=str(GABARITO))
    ap.add_argument(
        "--casas",
        choices=sorted(LISTAS_CASAS),
        default="oficial",
        help="oficial = pesos oficial_* (padrão); todas = 0-24 (pesos casas24_*)",
    )
    ap.add_argument(
        "--escala",
        choices=["normal", "larga"],
        default="normal",
        help="normal = pesos oficial_* (padrão); larga = metade das linhas com algarismo "
        "de 1,0 a 1,4 passo (candidato da rodada 0009)",
    )
    ap.add_argument(
        "--fontes",
        choices=sorted(PRESETS_FONTES),
        default="padrao",
        help="padrao = pesos oficial_*; fina = + LiberationSerif-Regular (robert lunn); "
        "fina2 = fonte fina com o dobro do peso e corda por cima quase sempre; "
        "fina3 = fina2 com a fonte fina GRANDE (1,0 a 1,4 passo); "
        "fina4 = fina3 + desfoque em metade das linhas",
    )
    return ap


def main() -> int:
    args = _parser().parse_args()

    X, y, _ = montar(
        args.n_linhas,
        seed=1,
        casas=LISTAS_CASAS[args.casas],
        escala_larga=args.escala == "larga",
        preset_fontes=args.fontes,
    )
    print(
        f"sintético: {len(X)} glifos extraídos de {args.n_linhas} linhas | "
        f"{len(set(y))} classes"
    )
    print("  distribuição:", collections.Counter(y).most_common(12))
    modelo, rotulos, dev = treinar(X, y, args.saida, args.epocas, seed=args.seed)

    print("\n=== aferição no gabarito real (nunca visto no treino) ===")
    avaliar_no_gabarito(modelo, rotulos, dev)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
