"""Discriminador "isto é algarismo?" — o portão do que vira símbolo.

**Por que existe.** A extração decidia "isto é símbolo" por exclusão: se o classificador de
glifos não dizia um algarismo, o recorte era guardado como símbolo cru. Medido no primeiro
gabarito de símbolos do projeto (48 recortes SORTEADOS, 6 canais, lidos no olho,
`data/gold/simbolos.json`):

- **33 % do que virava "símbolo" era algarismo puro** (`9`, `4`, `0`, `11`, `10`, `12`, …);
- 56 % era lixo (fragmento de linha, **cruz barline × corda**, foto borrada);
- 2 % era símbolo de verdade.

**Por que não é limiar de confiança.** Medido e REPROVADO: a maior probabilidade entre as
classes de algarismo (`p_digito`) é 0,17–1,00 (mediana 0,94) nos algarismos e 0,11–**0,92**
(mediana 0,42) no lixo. As distribuições se sobrepõem — em qualquer limiar ou se perde um
terço dos algarismos ou passa quase metade do lixo.

**A causa raiz, medida no top-1**: o lixo é classificado como **`7` (11 vezes)** e **`1`
(8 vezes)** — o modelo antigo **vê algarismo em pedaço de linha**. É isso que produz as duas
direções do erro.

**Este discriminador responde à pergunta certa** e generaliza: leave-one-channel-out
**0,879 / 0,940** em 8 canais (sementes 1 e 2), contra um canal nunca visto.

Uso:
    python -m tab.digito treinar --sementes 1 2 3
    python -m tab.digito avaliar
"""

from __future__ import annotations

import argparse
import json
import os

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .caminhos import ARTEFATOS, GABARITO, SAIDA
from .reconhecer import _recortar
from .sintetico import fixar_semente
from .tabseg import segmentar

#: Entrada da rede: o recorte normalizado. 32×32 mantém a forma legível e a rede pequena.
ALTURA, LARGURA = 32, 32

#: Diretório dos recortes rotulados no gabarito de símbolos, na convenção do modelo.
CROPS_SIMBOLOS = SAIDA.parent / "gold" / "simbolos_crops"

#: Gabarito de símbolos (rótulos lidos no olho).
GOLD_SIMBOLOS = SAIDA.parent / "gold" / "simbolos.json"

#: Segunda folha de símbolos (amostra estratificada por canal, 17 canais).
GOLD_SIMBOLOS_2 = SAIDA.parent / "gold" / "simbolos_2.json"

#: O que é LIXO na taxonomia auditada pelo dono do projeto. As três classes vêm da
#: leitura dele: `nada` (pedaço cinza/foto), `tablatura` (material de linha, incluindo
#: as CRUZES de barline × corda) e `partitura` (pedaço de pauta de 5 linhas). Medido em
#: duas amostras independentes: 54 % e 60 % da coleta é lixo.
CLASSES_LIXO = frozenset({"nada", "tablatura", "partitura"})


def preparar(img: np.ndarray) -> np.ndarray:
    """Recorte → entrada da rede (cinza, 32×32, 0..1).

    Args:
        img: recorte em BGR ou tons de cinza.

    Returns:
        Tensor numpy ``(1, ALTURA, LARGURA)``.
    """
    cinza = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    redimensionado = cv2.resize(cinza, (LARGURA, ALTURA), interpolation=cv2.INTER_AREA)
    return (redimensionado.astype(np.float32) / 255.0)[None]


class DigitoCNN(nn.Module):
    """Rede pequena: decide se o recorte é um algarismo de casa."""

    def __init__(self) -> None:
        super().__init__()
        self.c1 = nn.Conv2d(1, 8, 3, padding=1)
        self.c2 = nn.Conv2d(8, 16, 3, padding=1)
        self.fc1 = nn.Linear(16 * 8 * 8, 32)
        self.fc2 = nn.Linear(32, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Logits das duas classes (0 = não é algarismo, 1 = é algarismo)."""
        x = F.max_pool2d(F.relu(self.c1(x)), 2)
        x = F.max_pool2d(F.relu(self.c2(x)), 2)
        return self.fc2(F.relu(self.fc1(x.flatten(1))))


def montar_conjunto(tarefa: str = "digito") -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Monta o conjunto a partir do que está ROTULADO (nada é inferido pelo modelo).

    Positivos: os algarismos rotulados do gabarito (extraídos dos quadros cacheados, na
    convenção do modelo) mais os algarismos rotulados no gabarito de símbolos. Negativos:
    lixo e símbolo do gabarito de símbolos. Amostras em dúvida ficam **fora**.

    Returns:
        ``(X, y, canais)`` — X em ``(N, 1, ALTURA, LARGURA)``, y em ``{0, 1}``.
    """
    X: list[np.ndarray] = []
    y: list[int] = []
    canais: list[str] = []
    dados = json.loads(GABARITO.read_text(encoding="utf-8"))
    for am in dados["amostras"]:
        if am.get("descartada"):
            continue
        cache = SAIDA / "frames" / "gold" / f"{am['canal']}.png"
        if not cache.exists():
            continue
        img = cv2.imread(str(cache), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        grade = segmentar(img)
        cinza = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        for chave in am["rotulos"]:
            i = int(chave)
            if i >= len(grade.glifos):
                continue
            t = grade.glifos[i]
            X.append(preparar(_recortar(cinza, t.x0, t.y0, t.x1, t.y1)))
            y.append(1)
            canais.append(am["canal"])
    # Tarefa `digito`: positivo = algarismo; `lixo`: positivo = nada/tablatura/partitura.
    # A leitura do DONO DO PROJETO manda quando existe (ele auditou a folha 1 e separou o que
    # eu havia juntado). Sem ela, cai no meu rótulo; dúvida fica fora das duas tarefas.
    for caminho_gold, pasta in (
        (GOLD_SIMBOLOS, CROPS_SIMBOLOS),
        (GOLD_SIMBOLOS_2, None),
    ):
        if not caminho_gold.exists():
            continue
        gold = json.loads(caminho_gold.read_text(encoding="utf-8"))
        for caso in gold["casos"]:
            rotulo = caso.get("rotulo_dono") or caso["rotulo"]
            if rotulo == "duvida":
                continue
            arq = (
                pasta / f"{caso['indice']:02d}.png"
                if pasta is not None
                else SAIDA / "simbolos" / caso["canal"] / caso["arquivo"]
            )
            if not arq.exists():
                continue
            img = cv2.imread(str(arq), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            if tarefa == "lixo":
                alvo = 1 if rotulo in CLASSES_LIXO else 0
            else:
                alvo = 1 if rotulo == "algarismo" else 0
            X.append(preparar(img))
            y.append(alvo)
            canais.append(caso["canal"])
    return np.stack(X), np.array(y), canais


def treinar(
    X: np.ndarray, y: np.ndarray, idx: list[int], seed: int, epocas: int = 60
) -> tuple[DigitoCNN, str]:
    """Treina o discriminador em um subconjunto.

    Args:
        X: entradas.
        y: rótulos.
        idx: índices de treino.
        seed: semente (determinismo por `fixar_semente`).
        epocas: passagens pelo conjunto.

    Returns:
        ``(modelo, dispositivo)``.
    """
    fixar_semente(seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    xt = torch.tensor(X[idx]).to(dev)
    yt = torch.tensor(y[idx]).to(dev)
    modelo = DigitoCNN().to(dev)
    otim = torch.optim.AdamW(modelo.parameters(), lr=3e-3, weight_decay=1e-4)
    # Peso de classe: os negativos são minoria (28 de 116) e são a classe que importa aqui.
    n_pos = max(1, int((y[idx] == 1).sum()))
    n_neg = max(1, int((y[idx] == 0).sum()))
    peso = torch.tensor([len(idx) / (2 * n_neg), len(idx) / (2 * n_pos)]).to(dev)
    for _ in range(epocas):
        modelo.train()
        otim.zero_grad()
        F.cross_entropy(modelo(xt), yt, weight=peso).backward()
        otim.step()
    modelo.eval()
    return modelo, dev


def probabilidade(modelo: DigitoCNN, dev: str, X: np.ndarray) -> np.ndarray:
    """Probabilidade de "é algarismo" para cada entrada."""
    with torch.no_grad():
        return torch.softmax(modelo(torch.tensor(X).to(dev)), 1)[:, 1].cpu().numpy()


def validar_por_canal(
    X: np.ndarray, y: np.ndarray, canais: list[str], seed: int
) -> tuple[int, int, dict[str, tuple[int, int]]]:
    """Leave-one-channel-out: generalizar para canal que NÃO entrou no treino.

    Args:
        X: entradas.
        y: rótulos.
        canais: canal de cada amostra.
        seed: semente.

    Returns:
        ``(acertos, total, por_canal)``.
    """
    acertos = total = 0
    por_canal: dict[str, tuple[int, int]] = {}
    for canal in sorted(set(canais)):
        tre = [i for i in range(len(y)) if canais[i] != canal]
        tes = [i for i in range(len(y)) if canais[i] == canal]
        if len(set(y[tre])) < 2 or not tes:
            continue
        modelo, dev = treinar(X, y, tre, seed)
        p = probabilidade(modelo, dev, X[tes])
        ok = sum(1 for k, i in enumerate(tes) if (p[k] >= 0.5) == bool(y[i]))
        acertos += ok
        total += len(tes)
        por_canal[canal] = (ok, len(tes))
    return acertos, total, por_canal


def carregar(caminho: str | None = None):
    """Devolve a função discriminadora pronta: recortes -> probabilidade de "é algarismo".

    É esta função que `reconhecer_linha` recebe como `discriminador`. Existe para os
    chamadores não repetirem o carregamento nem o empilhamento da entrada.

    Args:
        caminho: checkpoint; por padrão o da semente 2 (LOCA 0,940, a melhor das três).

    Returns:
        Callable que recebe uma lista de recortes e devolve um array de probabilidades.
    """
    alvo = caminho or str(ARTEFATOS / "digito_2" / "digito.pt")
    ck = torch.load(alvo, map_location="cpu")
    modelo = DigitoCNN()
    modelo.load_state_dict(ck["state_dict"])
    modelo.eval()

    def _discriminar(recortes: list[np.ndarray]) -> np.ndarray:
        entrada = np.stack([preparar(r)[0] for r in recortes])[:, None]
        return probabilidade(modelo, "cpu", entrada)

    return _discriminar


def main() -> int:
    """Treina (3 sementes para `artefatos/`) ou mede leave-one-channel-out."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("acao", choices=["treinar", "avaliar", "loca"])
    ap.add_argument("--tarefa", choices=["digito", "lixo"], default="digito")
    ap.add_argument("--sementes", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--epocas", type=int, default=60)
    args = ap.parse_args()

    X, y, canais = montar_conjunto(args.tarefa)
    print(
        f"tarefa={args.tarefa} | "
        f"conjunto: {X.shape} | algarismos={int(y.sum())} não-algarismos={int((y == 0).sum())} "
        f"| {len(set(canais))} canais",
        flush=True,
    )
    if args.acao == "treinar":
        for seed in args.sementes:
            modelo, _dev = treinar(X, y, list(range(len(y))), seed, args.epocas)
            destino = ARTEFATOS / f"{args.tarefa}_{seed}"
            os.makedirs(destino, exist_ok=True)
            torch.save(
                {"state_dict": modelo.state_dict(), "seed": seed}, destino / "digito.pt"
            )
            print(f"  semente {seed}: salvo em {destino}", flush=True)
        return 0
    for seed in args.sementes:
        acertos, total, por_canal = validar_por_canal(X, y, canais, seed)
        detalhe = " ".join(
            f"{c.split()[0][:8]}={o}/{t}" for c, (o, t) in sorted(por_canal.items())
        )
        print(
            f"semente {seed}: LOCA {acertos}/{total} = {acertos / max(1, total):.3f} | {detalhe}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
