"""Portão aprendido: este recorte é uma pauta de tablatura?

Por que um modelo e não uma regra: **quatro discriminadores feitos à mão foram medidos e
os quatro falharam** (ver `docs/decisoes/0005`). O detector aceitava como tablatura:

- **teclado de piano** (`violaodecria`) — uniformidade 0,856, "fração de algarismos" 0,20;
- **cabeça do violão com tarraxas** (`shin izumi`) — uniformidade 0,925, fração 0,28;
- **corpo do violão** (`cifra club`) — uniformidade **0,974**, a mais lisa de todas;
- **a partitura** (`guitar dell'arte`).

E a tablatura real de `sky4_t120` deu fração de algarismos **0,23** enquanto a cabeça do
violão deu **0,28**: não há regra que separe.

Aqui o portão é um classificador binário pequeno sobre o recorte do painel. Positivos do
**mesmo gerador sintético** que treina o classificador de glifos (pauta clara/escura,
linha sólida/tracejada, passo 14–36, acorde, rótulo `TAB`) mais os painéis reais
confirmados; negativos sintéticos (tecla larga, madeira com veio e cordas em diagonal,
pauta de 5 linhas com notas, bloco de texto) mais os negativos reais que a rodada achou.

Os recortes REAIS rotulados à mão vivem em `data/saida/portao_casos/` e os rótulos em
`data/gold/portao.json`; as folhas de leitura (com o índice desenhado em cada célula)
ficam em `data/saida/frames/`.

Uso:
    python -m tab.portao coletar --canal "sky guitar" --n-videos 16 \
        --fracoes 0.6,0.75,0.9 --seed 11 --inicio 121
    python -m tab.portao folhas --letra E
    python -m tab.portao rotular --rotulos data/saida/portao_rotulos.json \
        --folhas data/saida/frames/folha_E.png
    python -m tab.portao treinar --gold --pesos --n 300 --epocas 12 --seed 1 \
        --saida artefatos/portao_bal_1
    python -m tab.portao locanal --n 300 --epocas 12 --seed 1
    python -m tab.portao avaliar --modelo artefatos/portao_bal_1/portao.pt
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from tab.comum.caminhos import (
    FRAMES,
    GOLD_PORTAO,
    OURO_NOVOS,
    PESOS_TABLATURA,
    RAIZ,
    SAIDA,
    acervo,
)
from tab.tablatura.leitura.inventario import ler_quadro
from tab.tablatura.leitura.painel import FAIXAS, candidatos, escolher, refinar
from tab.tablatura.treino.sintetico import fixar_semente, gerar_linha

#: Tamanho fixo da entrada. Largo e baixo, como o painel; a distorção de aspecto é
#: aceitável porque o que decide é a ESTRUTURA (linhas finas + glifos entre elas).
ALTURA, LARGURA = 64, 256

#: Casos reais conferidos no olho — viram teste permanente.
POSITIVOS_REAIS: tuple[str, ...] = (
    str((FRAMES / "sky4_t88.png").relative_to(RAIZ)),
    str((FRAMES / "sky4_t120.png").relative_to(RAIZ)),
    str((FRAMES / "asturias_t417.png").relative_to(RAIZ)),
)
NEGATIVOS_REAIS: tuple[tuple[str, float], ...] = (
    (str((OURO_NOVOS / "03_violaodecria" / "auto.json").relative_to(RAIZ)), 0.0),
    (str((OURO_NOVOS / "02_shin izumi" / "auto.json").relative_to(RAIZ)), 0.0),
    (str((OURO_NOVOS / "00_cifra club" / "auto.json").relative_to(RAIZ)), 0.0),
    (str((OURO_NOVOS / "01_guitar dell ́a" / "auto.json").relative_to(RAIZ)), 0.0),
)

#: Vídeos que COMPÕEM o conjunto de aceitação — ficam fora do treino e da validação.
#: Sem isto o conjunto de aceitação deixa de medir generalização para vídeo novo: os
#: dois positivos de `sky4_*` são de `#4 (beginner) free pdf.mp4` e `asturias_t417` é de
#: `asturias - guitar lesson + tab.mp4` (conferido comparando o quadro em t=417 s).
VIDEOS_DE_ACEITACAO: tuple[str, ...] = (
    "sky guitar/#4 (beginner) free pdf.mp4",
    "sky guitar/asturias - guitar lesson + tab.mp4",
    "cifra club/livre estou (do filme ＂frozen＂) ｜ como tocar no violão.mp4",
    "guitar dell ́arte/etude in e minor (j. ferrer) - guitar lesson, sheet and tab.mp4",
    "shin izumi/【tab】change the world - eric clapton - fingerstyle guitar ソロギター【タブ】.mp4",
    "violaodecria/cartel do 900 - mc kevin, ig, rick, menor da vg, hariel e don juan #c... [7346930985751104773].mp4",
)

#: Recortes de painel rotulados à mão (o `arquivo` de cada caso do gabarito).
CASOS_PORTAO = SAIDA / "portao_casos"

#: Gabarito do portão, acrescentado rodada a rodada; os casos antigos nunca são reescritos.

#: Folhas de leitura no olho (PNG com o índice desenhado em cada célula).
FOLHAS_PORTAO = FRAMES

#: Rótulos aceitos.
ROTULOS = ("tablatura", "nao_tablatura", "duvida")

#: Rótulos que entram no treino e na validação (`duvida` fica de fora).
ROTULOS_BINARIOS = ("tablatura", "nao_tablatura")


def preparar(roi: np.ndarray) -> np.ndarray:
    """Recorte do painel → entrada do portão (cinza, tamanho fixo, 0..1)."""
    cinza = roi if roi.ndim == 2 else cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    redimensionado = cv2.resize(cinza, (LARGURA, ALTURA), interpolation=cv2.INTER_AREA)
    return (redimensionado.astype(np.float32) / 255.0)[None, :, :]


class PortaoCNN(nn.Module):
    """Rede pequena: decide se o recorte é pauta de tablatura."""

    def __init__(self) -> None:
        super().__init__()
        self.c1 = nn.Conv2d(1, 8, 3, padding=1)
        self.c2 = nn.Conv2d(8, 16, 3, padding=1)
        self.c3 = nn.Conv2d(16, 32, 3, padding=1)
        self.drop = nn.Dropout(0.15)
        self.fc1 = nn.Linear(32 * 8 * 32, 32)
        self.fc2 = nn.Linear(32, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Logits das duas classes."""
        x = F.max_pool2d(F.relu(self.c1(x)), 2)
        x = F.max_pool2d(F.relu(self.c2(x)), 2)
        x = F.max_pool2d(F.relu(self.c3(x)), 2)
        x = self.drop(x.flatten(1))
        return self.fc2(F.relu(self.fc1(x)))


def negativo_teclado(rng: random.Random) -> np.ndarray:
    """Teclado: teclas brancas separadas por barras pretas LARGAS."""
    img = np.full((200, 900), 235, np.uint8)
    x = rng.randint(0, 20)
    while x < 900:
        largura = rng.randint(18, 46)
        cv2.rectangle(img, (x, 30), (x + largura, 190), (25, 25, 25), -1)
        x += largura + rng.randint(30, 70)
    cv2.line(img, (0, 30), (900, 30), (60, 60, 60), 3)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def negativo_madeira(rng: random.Random) -> np.ndarray:
    """Cabeça/braço: madeira com veio e cordas em diagonal."""
    gerador = np.random.default_rng(rng.randint(0, 2**31 - 1))
    base = gerador.integers(70, 200, (200, 900), dtype=np.uint8)
    veio = cv2.GaussianBlur(base, (0, 0), 1.0)
    img = cv2.cvtColor(veio, cv2.COLOR_GRAY2BGR)
    for i in range(6):
        y = 20 + i * 30
        cv2.line(img, (0, y), (900, y + rng.randint(-40, 40)), (45, 45, 45), 2)
    return img


def negativo_pauta5(rng: random.Random) -> np.ndarray:
    """Partitura: 5 linhas finas com bolinhas (notas) — sem algarismos."""
    img = np.full((200, 900, 3), 250, np.uint8)
    for i in range(5):
        cv2.line(img, (20, 60 + i * 20), (880, 60 + i * 20), (40, 40, 40), 1)
    for _ in range(rng.randint(8, 20)):
        x, y = rng.randint(40, 860), rng.randint(60, 140)
        cv2.ellipse(img, (x, y), (7, 5), 20, 0, 360, (30, 30, 30), -1)
    return img


def negativo_texto(rng: random.Random) -> np.ndarray:
    """Cifra/letra: blocos de texto sem pauta nenhuma."""
    img = np.full((200, 900, 3), 235, np.uint8)
    for linha in range(6):
        x = rng.randint(10, 60)
        y = 25 + linha * 30
        while x < 880:
            largura = rng.randint(10, 40)
            if rng.random() < 0.8:
                cv2.rectangle(img, (x, y), (x + largura, y + 16), (50, 50, 50), -1)
            x += largura + rng.randint(8, 20)
    return img


def negativo_corpo(rng: random.Random) -> np.ndarray:
    """Corpo/mão: manchas grandes e gradiente — nada de linha regular."""
    img = np.zeros((200, 900, 3), np.uint8)
    img[:, :] = (120, 150, 190)
    for _ in range(rng.randint(3, 8)):
        centro = (rng.randint(0, 900), rng.randint(0, 200))
        eixos = (rng.randint(60, 260), rng.randint(40, 150))
        cor = (rng.randint(90, 220), rng.randint(90, 220), rng.randint(90, 230))
        cv2.ellipse(img, centro, eixos, rng.randint(0, 180), 0, 360, cor, -1)
    return cv2.GaussianBlur(img, (0, 0), 6)


NEGATIVOS_SINTETICOS = (
    negativo_teclado,
    negativo_madeira,
    negativo_pauta5,
    negativo_texto,
    negativo_corpo,
)


def fundo_de_video(rng: random.Random) -> np.ndarray:
    """Fundo parecido com quadro de vídeo: cor sólida, gradiente e manchas."""
    quadro = np.zeros((1080, 1920, 3), np.uint8)
    tom = rng.randint(20, 240)
    quadro[:, :] = (tom, tom, tom)
    for _ in range(rng.randint(2, 6)):
        centro = (rng.randint(0, 1920), rng.randint(0, 1080))
        eixos = (rng.randint(80, 400), rng.randint(60, 260))
        cor = tuple(rng.randint(20, 240) for _ in range(3))
        cv2.ellipse(quadro, centro, eixos, rng.randint(0, 180), 0, 360, cor, -1)
    return cv2.GaussianBlur(quadro, (0, 0), rng.uniform(2, 8))


def cena_em_quadro(cena: np.ndarray, rng: random.Random) -> np.ndarray:
    """Cola a cena numa faixa do quadro e devolve o recorte da FAIXA.

    É o mesmo recorte que o pipeline recebe em produção: largura total do quadro,
    altura da faixa, com fundo de vídeo em volta. Sem isto o portão aprende a separar
    "desenho limpo" de "desenho limpo" e não transfere para quadro real (medido: 0 de 3
    painéis reais com acurácia de treino 1,0000).
    """
    quadro = fundo_de_video(rng)
    _, y0, y1 = FAIXAS[rng.randrange(len(FAIXAS))]
    y1 = min(y1, quadro.shape[0])
    altura = y1 - y0
    largura = min(cena.shape[1], quadro.shape[1])
    fator = rng.uniform(0.8, 1.6)
    redimensionada = cv2.resize(
        cena, (int(largura * fator), max(8, int(cena.shape[0] * fator)))
    )
    if redimensionada.shape[0] > altura:
        redimensionada = cv2.resize(redimensionada, (redimensionada.shape[1], altura))
    x = rng.randint(0, max(0, quadro.shape[1] - redimensionada.shape[1]))
    y = y0 + rng.randint(0, max(0, altura - redimensionada.shape[0]))
    h = min(redimensionada.shape[0], altura, quadro.shape[0] - y)
    w = min(redimensionada.shape[1], quadro.shape[1] - x)
    if h >= 8 and w >= 8:
        quadro[y : y + h, x : x + w] = redimensionada[:h, :w]
    return quadro[y0:y1, :]


def montar_dataset(
    n_por_classe: int, seed: int = 0, n_negativos: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Monta o conjunto com o MESMO recorte que o pipeline vê em produção.

    Positivo: linha de tablatura do gerador posta numa faixa de um quadro de vídeo
    sintético. Negativo: cena que não é tablatura (teclado, madeira com veio, pauta de
    5 linhas, texto, corpo/mão) na mesma situação. Assim o portão aprende a decisão que
    vai de fato tomar, e não a diferença entre dois desenhos limpos.

    Args:
        n_por_classe: quantos exemplos positivos (tablatura sintética).
        seed: semente do sorteio.
        n_negativos: quantos negativos; padrão igual aos positivos. Pedir **mais
            negativos que positivos** é o que cobre "foto de instrumento" sem ensinar o
            positivo a ser o desenho sintético — medido: o positivo sintético derruba a
            validação por canal (ver `docs/rodadas/`).

    Returns:
        ``(X, y)`` com X em ``(N, 1, ALTURA, LARGURA)`` e y em ``{0, 1}``.
    """
    quantos_neg = n_por_classe if n_negativos is None else n_negativos
    rng = random.Random(seed)
    X: list[np.ndarray] = []
    y: list[int] = []
    for _ in range(n_por_classe):
        linha, _ = gerar_linha(rng)
        X.append(preparar(cena_em_quadro(linha, rng)))
        y.append(1)
    for i in range(quantos_neg):
        desenhar = NEGATIVOS_SINTETICOS[i % len(NEGATIVOS_SINTETICOS)]
        X.append(preparar(cena_em_quadro(desenhar(rng), rng)))
        y.append(0)
    return np.stack(X), np.array(y)


def videos_do_canal(canal: str) -> list[str]:
    """Vídeos de um canal, ordenados, SEM os que compõem o conjunto de aceitação.

    Args:
        canal: nome do canal (diretório dentro do acervo).

    Returns:
        Caminhos absolutos, ordenados.
    """
    achados = sorted(glob.glob(str(acervo() / canal / "*.mp4")))
    fora = set(VIDEOS_DE_ACEITACAO)
    return [v for v in achados if f"{canal}/{os.path.basename(v)}" not in fora]


def coletar_canal(
    canal: str,
    n_videos: int,
    fracoes: tuple[float, ...],
    seed: int,
    inicio: int = 0,
    por_quadro: int = 2,
) -> list[dict]:
    """Gera recortes candidatos de painel de um canal e grava cada um em PNG.

    Grava o melhor candidato de cada quadro e o segundo melhor — é onde costuma
    estar o braço/corpo do violão, que serve de negativo real (sem ele o canal novo
    entra na validação deixando-um-canal-de-fora só com positivos, e a validação
    não mede falso positivo nenhum). O rótulo sai ``None``: quem rotula é a leitura
    das folhas no olho, nunca um proxy geométrico.

    Args:
        canal: nome do canal.
        n_videos: quantos vídeos sortear do canal.
        fracoes: instantes (fração da duração) amostrados em cada vídeo.
        seed: semente do sorteio de vídeos.
        inicio: índice do primeiro arquivo (continua a numeração do gabarito).
        por_quadro: candidatos por quadro (1 = só o melhor).

    Returns:
        Casos no formato de ``data/gold/portao.json``, na ordem em que foram gravados.
    """
    vids = videos_do_canal(canal)
    rng = random.Random(seed)
    if n_videos < len(vids):
        vids = sorted(rng.sample(vids, n_videos))
    os.makedirs(CASOS_PORTAO, exist_ok=True)
    casos: list[dict] = []
    indice = inicio
    for caminho in vids:
        for frac in fracoes:
            quadro, via = ler_quadro(caminho, frac)
            if quadro is None:
                continue
            achados = sorted(candidatos(quadro), key=lambda c: -c.score[0])
            for posicao, cand in enumerate(achados[:por_quadro]):
                recorte = refinar(cand)
                nome = f"{indice:03d}_{'p' if posicao == 0 else 'n'}.png"
                cv2.imwrite(str(CASOS_PORTAO / nome), recorte.roi)
                casos.append(
                    {
                        "arquivo": nome,
                        "canal": canal,
                        "video": f"{canal}/{os.path.basename(caminho)}",
                        "instante_frac": frac,
                        "via": via,
                        "faixa": recorte.nome,
                        "uniformidade": round(recorte.uniformidade, 3),
                        "passo": round(recorte.passo, 1),
                        "glifos": len(recorte.grade.glifos),
                        "posicao": posicao,
                        "rotulo": None,
                    }
                )
                indice += 1
                print(f"  {nome} via={via} {recorte.nome}", flush=True)
    return casos


def montar_folha(
    casos: list[dict],
    indices: list[int],
    caminho: str,
    cols: int = 4,
    celula: tuple[int, int] = (480, 270),
    etiquetas: list[str] | None = None,
) -> None:
    """Monta uma folha com os recortes e uma ETIQUETA grande em cada célula.

    O que é desenhado é a etiqueta da célula (``"E07"``), nunca o `_p`/`_n` do arquivo:
    quem lê não deve saber qual candidato o detector preferiu — isso enviesaria o
    rótulo, que é do olho. A ordem das células também vem embaralhada por
    `gerar_folhas`, e o mapa etiqueta → arquivo fica gravado em JSON para auditoria.

    Args:
        casos: casos coletados (cada um com ``arquivo``).
        indices: quais índices de ``casos`` entram, na ordem de leitura.
        caminho: PNG de saída.
        cols: colunas da grade.
        celula: ``(largura, altura)`` de cada célula, em px.
        etiquetas: texto de cada célula (padrão: o próprio índice).
    """
    larg, alt = celula
    faixa = 36
    linhas = max(1, (len(indices) + cols - 1) // cols)
    folha = np.full((linhas * alt, cols * larg, 3), 255, np.uint8)
    for k, idx in enumerate(indices):
        img = cv2.imread(str(CASOS_PORTAO / str(casos[idx]["arquivo"])))
        if img is None:
            continue
        lin, col = divmod(k, cols)
        y0, x0 = lin * alt, col * larg
        cv2.rectangle(
            folha, (x0, y0), (x0 + larg - 1, y0 + alt - 1), (190, 190, 190), 1
        )
        escala = min(
            (larg - 8) / img.shape[1],
            max(1, alt - faixa - 8) / img.shape[0],
        )
        nova = cv2.resize(
            img,
            (max(1, int(img.shape[1] * escala)), max(1, int(img.shape[0] * escala))),
            interpolation=cv2.INTER_AREA,
        )
        h = min(nova.shape[0], alt - faixa - 2)
        w = min(nova.shape[1], larg - 2)
        py = y0 + faixa + max(0, (alt - faixa - h) // 2)
        px = x0 + max(0, (larg - w) // 2)
        folha[py : py + h, px : px + w] = nova[:h, :w]
        texto = str(idx) if etiquetas is None else etiquetas[k]
        cv2.putText(
            folha,
            texto,
            (x0 + 8, y0 + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.1,
            (0, 0, 220),
            3,
            cv2.LINE_AA,
        )
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    cv2.imwrite(caminho, folha)


def gerar_folhas(
    casos: list[dict],
    letra: str = "D",
    por_folha: int = 16,
    cols: int = 4,
    seed: int = 0,
    destino: str | None = None,
) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Gera as folhas de leitura (ordem embaralhada) e devolve caminhos e mapa.

    Args:
        casos: casos coletados, na ordem da coleta.
        letra: letra inicial das folhas (as antigas A/B/C são preservadas).
        por_folha: recortes por folha.
        cols: colunas da grade.
        seed: semente do embaralhamento.
        destino: diretório das folhas (padrão ``data/saida/frames``).

    Returns:
        ``(caminhos, mapa)``: os PNGs gerados e, por folha, ``{etiqueta: índice}``.
    """
    raiz = destino or str(FOLHAS_PORTAO)
    ordem = list(range(len(casos)))
    random.Random(seed).shuffle(ordem)
    caminhos: list[str] = []
    mapa: dict[str, dict[str, int]] = {}
    for f, i in enumerate(range(0, len(casos), por_folha)):
        nome = chr(ord(letra) + f)
        caminho = os.path.join(raiz, f"folha_{nome}.png")
        indices = ordem[i : i + por_folha]
        etiquetas = [f"{nome}{k:02d}" for k in range(len(indices))]
        montar_folha(casos, indices, caminho, cols=cols, etiquetas=etiquetas)
        mapa[nome] = dict(zip(etiquetas, indices, strict=True))
        caminhos.append(caminho)
    return caminhos, mapa


def carregar_gold(caminho: str | None = None) -> dict:
    """Lê o gabarito do portão (`data/gold/portao.json`)."""
    with open(caminho or GOLD_PORTAO, encoding="utf-8") as fh:
        return json.load(fh)


def casos_do_gold(caminho: str | None = None) -> list[dict]:
    """Casos rotulados do gabarito do portão (inclui os ``duvida``)."""
    return list(carregar_gold(caminho)["casos"])


def acrescentar_casos(
    novos: list[dict], folhas: list[str], caminho: str | None = None
) -> dict:
    """Acrescenta casos ao gabarito SEM tocar nos que já existem.

    Args:
        novos: casos novos, já com ``rotulo``.
        folhas: folhas PNG usadas na leitura (auditoria do dono do projeto).
        caminho: gabarito de destino (padrão ``data/gold/portao.json``).

    Returns:
        O gabarito completo, como ficou no disco.
    """
    alvo = caminho or GOLD_PORTAO
    gold = carregar_gold(alvo)
    existentes = {c["arquivo"] for c in gold["casos"]}
    for caso in novos:
        if caso["arquivo"] not in existentes:
            gold["casos"].append(caso)
    for folha in folhas:
        if folha not in gold["folhas"]:
            gold["folhas"].append(folha)
    with open(alvo, "w", encoding="utf-8") as fh:
        json.dump(gold, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return gold


def dataset_real(casos: list[dict]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """PNGs rotulados (fora os ``duvida``) → ``(X, y, canais)`` do portão.

    Args:
        casos: casos do gabarito.

    Returns:
        ``X`` em ``(N, 1, ALTURA, LARGURA)``, ``y`` em ``{0, 1}`` e o canal de cada caso.
    """
    X: list[np.ndarray] = []
    y: list[int] = []
    canais: list[str] = []
    for caso in casos:
        if caso.get("rotulo") not in ROTULOS_BINARIOS:
            continue
        img = cv2.imread(str(CASOS_PORTAO / str(caso["arquivo"])))
        if img is None:
            continue
        X.append(preparar(img))
        y.append(1 if caso["rotulo"] == "tablatura" else 0)
        canais.append(str(caso["canal"]))
    if not X:
        return np.zeros((0, 1, ALTURA, LARGURA), np.float32), np.zeros(0, np.int64), []
    return np.stack(X), np.array(y, np.int64), canais


def pesos_de_classe(y: np.ndarray) -> np.ndarray:
    """Peso por classe para a perda, de modo que as duas classes contribuam igual.

    Escolhi **peso de classe**, não reamostragem: reamostrar o positivo minoritário
    seria mostrar as MESMAS imagens mais vezes por época (memorização de 26 recortes);
    o peso muda a perda sem tirar nem repetir dado. Com o sintético entrando em número
    igual por classe, é o resíduo de desbalanceamento real que o peso corrige.

    Args:
        y: rótulos.

    Returns:
        Vetor ``[peso_classe_0, peso_classe_1]`` com ``n / (2 * n_c)``.
    """
    n = float(len(y))
    return np.array(
        [n / (2.0 * max(1.0, float((y == c).sum()))) for c in (0, 1)], dtype=np.float32
    )


def montar_treino(
    casos: list[dict],
    n_sint: int,
    seed: int,
    excluir_canal: str | None = None,
    n_sint_neg: int | None = None,
    balancear: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Conjunto de treino: recortes reais rotulados + sintéticos alinhados.

    Args:
        casos: casos do gabarito.
        n_sint: positivos sintéticos (0 = só recorte real).
        seed: semente do gerador sintético.
        excluir_canal: canal deixado de fora (validação leave-one-channel-out).
        n_sint_neg: negativos sintéticos (padrão: igual a ``n_sint``).
        usar_pesos: peso de classe na perda.
        balancear: usar peso de classe na perda (``False`` = perda crua, para medir
            o efeito do balanceamento).

    Returns:
        ``(X, y, pesos)``; ``pesos`` é ``None`` quando ``balancear`` é falso.
    """
    X, y, canais = dataset_real(casos)
    if excluir_canal is not None and len(y):
        fora = np.array([c == excluir_canal for c in canais])
        X, y = X[~fora], y[~fora]
    if n_sint or n_sint_neg:
        Xs, ys = montar_dataset(n_sint, seed=seed, n_negativos=n_sint_neg)
        X = np.concatenate([X, Xs])
        y = np.concatenate([y, ys])
    return X, y, pesos_de_classe(y) if balancear else None


def treinar(
    X: np.ndarray,
    y: np.ndarray,
    saida: str,
    epocas: int,
    seed: int,
    lote: int = 64,
    pesos: np.ndarray | None = None,
    salvar: bool = True,
    extra: dict | None = None,
) -> tuple[PortaoCNN, str]:
    """Treina o portão.

    Args:
        X: entradas.
        y: rótulos (1 = tablatura).
        saida: diretório do modelo.
        epocas: passagens pelo conjunto.
        seed: semente (determinismo ligado por `fixar_semente`).
        lote: tamanho do lote.
        pesos: peso por classe na perda (``None`` = perda sem peso).
        salvar: gravar o modelo no disco (a validação por canal não grava).
        extra: metadados gravados junto dos pesos (semente, conjunto, contagens).

    Returns:
        ``(modelo, dispositivo)``.
    """
    fixar_semente(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    xt = torch.tensor(X).to(dev)
    yt = torch.tensor(y).to(dev)
    peso_t = None if pesos is None else torch.tensor(pesos).to(dev)
    modelo = PortaoCNN().to(dev)
    otim = torch.optim.AdamW(modelo.parameters(), lr=2e-3, weight_decay=1e-4)
    for ep in range(epocas):
        modelo.train()
        perm = torch.randperm(len(xt), device=dev)
        perda_tot = 0.0
        for i in range(0, len(xt), lote):
            b = perm[i : i + lote]
            otim.zero_grad()
            perda = F.cross_entropy(modelo(xt[b]), yt[b], weight=peso_t)
            perda.backward()
            otim.step()
            perda_tot += float(perda.detach()) * len(b)
        modelo.eval()
        with torch.no_grad():
            acc = float((modelo(xt).argmax(1) == yt).float().mean())
        if (ep + 1) % max(1, epocas // 4) == 0:
            print(
                f"  época {ep + 1:>3}/{epocas} perda={perda_tot / len(xt):.4f} "
                f"acc_treino={acc:.4f}",
                flush=True,
            )
    modelo.eval()
    if salvar:
        os.makedirs(saida, exist_ok=True)
        torch.save(
            {"state_dict": modelo.state_dict(), "seed": seed, "extra": extra or {}},
            os.path.join(saida, "portao.pt"),
        )
    return modelo, dev


def carregar_modelo(caminho: str):
    """Carrega o portão do disco (em modo de avaliação)."""
    ck = torch.load(caminho, map_location="cpu")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = PortaoCNN().to(dev)
    modelo.load_state_dict(ck["state_dict"])
    modelo.eval()
    return modelo, dev


def probabilidade_lote(X: np.ndarray, modelo, dev) -> np.ndarray:
    """P(tablatura) de um lote JÁ preparado, em ``(N, 1, ALTURA, LARGURA)``."""
    with torch.no_grad():
        xt = torch.tensor(X).to(dev)
        return torch.softmax(modelo(xt), 1)[:, 1].cpu().numpy()


def probabilidade(rois: list[np.ndarray], modelo, dev) -> np.ndarray:
    """Probabilidade de ser tablatura para cada recorte."""
    X = np.stack([preparar(r)[0] for r in rois])[:, None]
    return probabilidade_lote(X, modelo, dev)


def _casos_reais() -> tuple[list[np.ndarray], list[int], list[str]]:
    """Recortes reais com verdade conferida no olho."""
    rois: list[np.ndarray] = []
    rotulos: list[int] = []
    nomes: list[str] = []
    for caminho in POSITIVOS_REAIS:
        img = cv2.imread(caminho)
        if img is None:
            continue
        c = escolher(img)
        if c is None:
            continue
        rois.append(c.roi)
        rotulos.append(1)
        nomes.append(os.path.basename(caminho))
    for caminho, _ in NEGATIVOS_REAIS:
        if not os.path.exists(caminho):
            continue
        with open(caminho, encoding="utf-8") as fh:
            auto = json.load(fh)
        quadro, _ = ler_quadro(f"/acervo/{auto['video']}", auto["instante_frac"])
        if quadro is None:
            continue
        c = escolher(quadro)
        if c is None:
            continue
        rois.append(c.roi)
        rotulos.append(0)
        nomes.append(os.path.basename(os.path.dirname(caminho)))
    return rois, rotulos, nomes


def avaliar(modelo, dev) -> dict:
    """Mede o portão nos casos reais e devolve o veredito por caso."""
    rois, rotulos, nomes = _casos_reais()
    if not rois:
        return {"casos": []}
    probs = probabilidade(rois, modelo, dev)
    casos = []
    for nome, real, p in zip(nomes, rotulos, probs, strict=True):
        casos.append(
            {
                "caso": nome,
                "verdade": "tablatura" if real else "nao_tablatura",
                "p_tablatura": round(float(p), 3),
                "acertou": bool((p >= 0.5) == bool(real)),
            }
        )
    acertos = sum(1 for c in casos if c["acertou"])
    return {"casos": casos, "acertos": acertos, "total": len(casos)}


def validar_por_canal(
    casos: list[dict],
    n_sint: int,
    epocas: int,
    seed: int,
    lote: int = 64,
    n_sint_neg: int | None = None,
    usar_pesos: bool = True,
) -> dict:
    """Leave-one-channel-out: treina sem um canal e mede nele.

    É a validação que mede o que importa — generalizar para CANAL que não entrou no
    treino. A validação sorteada mede o contrário (o mesmo canal dos dois lados) e foi
    ela que produziu o 18/23 que não sobreviveu ao conjunto de aceitação.

    Args:
        casos: casos rotulados do gabarito.
        n_sint: exemplos sintéticos por classe (0 = só recorte real).
        epocas: passagens pelo conjunto.
        seed: semente do treino e do sintético.
        lote: tamanho do lote.
        n_sint_neg: negativos sintéticos (padrão: igual a ``n_sint``).
        usar_pesos: peso de classe na perda.

    Returns:
        ``{canal: {"acertos", "total", "positivos", "acertos_positivos"}}`` e a chave
        ``"total"`` com a soma de todos os casos deixados de fora. As duas contagens
        importam: acertar 65 negativos e errar 20 tablaturas não é o mesmo que o
        contrário, e o total sozinho esconde qual dos dois aconteceu.
    """
    _, _, canais = dataset_real(casos)
    resultado: dict = {}
    acertos = total = pos_total = ac_pos_total = 0
    for canal in sorted(set(canais)):
        X, y, pesos = montar_treino(
            casos,
            n_sint,
            seed,
            excluir_canal=canal,
            n_sint_neg=n_sint_neg,
            balancear=usar_pesos,
        )
        modelo, dev = treinar(
            X, y, "", epocas, seed, lote=lote, pesos=pesos, salvar=False
        )
        Xc, yc, _ = dataset_real([c for c in casos if c["canal"] == canal])
        p = probabilidade_lote(Xc, modelo, dev)
        acerto = (p >= 0.5) == (yc == 1)
        ac = int(acerto.sum())
        pos = np.asarray(yc == 1)
        resultado[canal] = {
            "acertos": ac,
            "total": len(yc),
            "positivos": int(pos.sum()),
            "acertos_positivos": int((acerto & pos).sum()),
        }
        acertos += ac
        total += len(yc)
        pos_total += int(pos.sum())
        ac_pos_total += int((acerto & pos).sum())
    resultado["total"] = {
        "acertos": acertos,
        "total": total,
        "positivos": pos_total,
        "acertos_positivos": ac_pos_total,
    }
    return resultado


def _casos_dos_manifestos(padroes: str) -> list[dict]:
    """Casos das coletas, na ordem dos manifestos (cada item aceita glob)."""
    casos: list[dict] = []
    for padrao in padroes.split(","):
        for caminho in sorted(glob.glob(padrao.strip())):
            with open(caminho, encoding="utf-8") as fh:
                casos.extend(json.load(fh))
    return casos


def main() -> int:
    """Coleta, rotula, treina, valida por canal ou avalia o portão."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "acao",
        choices=["treinar", "avaliar", "coletar", "folhas", "rotular", "locanal"],
    )
    ap.add_argument(
        "--n", type=int, default=3000, help="exemplos sintéticos por classe"
    )
    ap.add_argument("--epocas", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--saida", default=str(PESOS_TABLATURA / "portao"))
    ap.add_argument("--modelo", default=str(PESOS_TABLATURA / "portao" / "portao.pt"))
    ap.add_argument(
        "--gold", action="store_true", help="inclui os recortes reais rotulados"
    )
    ap.add_argument("--pesos", action="store_true", help="peso de classe na perda")
    ap.add_argument(
        "--n-neg",
        type=int,
        default=None,
        help="negativos sintéticos (padrão: igual a --n)",
    )
    ap.add_argument(
        "--sem-pesos", action="store_true", help="perda crua (sem peso de classe)"
    )
    ap.add_argument(
        "--canal", default="sky guitar", help="canal(is) da coleta, vírgula"
    )
    ap.add_argument("--n-videos", type=int, default=16)
    ap.add_argument("--fracoes", default="0.6,0.75,0.9")
    ap.add_argument("--inicio", type=int, default=0, help="índice do primeiro recorte")
    ap.add_argument("--por-quadro", type=int, default=2)
    ap.add_argument("--manifest", default="", help="manifesto(s) da coleta, vírgula")
    ap.add_argument("--rotulos", default="", help="JSON arquivo → rótulo")
    ap.add_argument(
        "--folhas", default="", help="folhas PNG usadas na leitura, vírgula"
    )
    ap.add_argument("--letra", default="D", help="letra inicial das folhas novas")
    args = ap.parse_args()

    if args.acao == "coletar":
        fracoes = tuple(float(f) for f in args.fracoes.split(","))
        casos: list[dict] = []
        for canal in (c.strip() for c in args.canal.split(",")):
            if not canal:
                continue
            casos.extend(
                coletar_canal(
                    canal,
                    args.n_videos,
                    fracoes,
                    args.seed,
                    inicio=args.inicio + len(casos),
                    por_quadro=args.por_quadro,
                )
            )
        destino = SAIDA / "portao_novos"
        os.makedirs(destino, exist_ok=True)
        caminho = destino / f"coleta_{args.inicio:03d}_{args.seed}.json"
        with open(caminho, "w", encoding="utf-8") as fh:
            json.dump(casos, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(
            f"{len(casos)} recortes em {caminho}; próximo índice {args.inicio + len(casos)}"
        )
        return 0

    if args.acao == "folhas":
        casos = _casos_dos_manifestos(args.manifest)
        caminhos, mapa = gerar_folhas(casos, letra=args.letra, seed=args.seed)
        destino = SAIDA / "portao_novos" / f"folhas_{args.letra}.json"
        os.makedirs(destino.parent, exist_ok=True)
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(mapa, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(json.dumps(caminhos, ensure_ascii=False, indent=1))
        return 0

    if args.acao == "rotular":
        with open(args.rotulos, encoding="utf-8") as fh:
            rotulos = json.load(fh)
        casos = _casos_dos_manifestos(args.manifest)
        novos = []
        for caso in casos:
            rotulo = rotulos.get(str(caso["arquivo"]))
            if rotulo not in ROTULOS:
                continue
            limpo = {k: v for k, v in caso.items() if k not in ("via", "posicao")}
            limpo["rotulo"] = rotulo
            novos.append(limpo)
        folhas = [f.strip() for f in args.folhas.split(",") if f.strip()]
        gold = acrescentar_casos(novos, folhas)
        contagem: dict[str, int] = {}
        for caso in gold["casos"]:
            contagem[str(caso["rotulo"])] = contagem.get(str(caso["rotulo"]), 0) + 1
        print(f"gabarito com {len(gold['casos'])} casos: {contagem}", flush=True)
        return 0

    if args.acao == "treinar":
        if args.gold:
            casos = [c for c in casos_do_gold() if c.get("rotulo") in ROTULOS_BINARIOS]
            _, y_real, _ = dataset_real(casos)
            X, y, pesos = montar_treino(casos, args.n, args.seed, n_sint_neg=args.n_neg)
            if not args.pesos:
                pesos = None
            print(
                f"conjunto: {X.shape} | tablatura {int(y.sum())} de {len(y)} | "
                f"real {int(y_real.sum())} pos / {len(y_real) - int(y_real.sum())} neg",
                flush=True,
            )
            modelo, dev = treinar(
                X,
                y,
                args.saida,
                args.epocas,
                args.seed,
                pesos=pesos,
                extra={
                    "n_sint": args.n,
                    "n_sint_neg": args.n_neg,
                    "gold": len(casos),
                    "positivos_reais": int(y_real.sum()),
                    "pesos": bool(args.pesos),
                },
            )
            print(f"\nmodelo salvo em {args.saida}", flush=True)
        else:
            X, y = montar_dataset(args.n, seed=args.seed, n_negativos=args.n_neg)
            print(
                f"conjunto: {X.shape} | tablatura {int(y.sum())} de {len(y)}",
                flush=True,
            )
            modelo, dev = treinar(X, y, args.saida, args.epocas, args.seed)
            print(f"\nmodelo salvo em {args.saida}", flush=True)
    elif args.acao == "locanal":
        casos = [c for c in casos_do_gold() if c.get("rotulo") in ROTULOS_BINARIOS]
        print(
            json.dumps(
                validar_por_canal(
                    casos,
                    args.n,
                    args.epocas,
                    args.seed,
                    n_sint_neg=args.n_neg,
                    usar_pesos=not args.sem_pesos,
                ),
                ensure_ascii=False,
                indent=1,
            ),
            flush=True,
        )
        return 0
    else:
        modelo, dev = carregar_modelo(args.modelo)

    resultado = avaliar(modelo, dev)
    print(json.dumps(resultado, ensure_ascii=False, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
