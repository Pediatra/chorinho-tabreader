"""Aferição padronizada no gabarito real — é o número oficial do projeto.

Roda as 4 amostras rotuladas à mão (96 glifos) e imprime o acerto por canal. O
AGENTS.md manda reportar a **média de 3 sementes**, nunca uma execução só.

Uso:
    python -m tab.avaliar [--modelo CAMINHO]
"""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np

from .caminhos import FRAMES_GOLD, GABARITO, MODELO_PADRAO, PARTES, acervo
from .inventario import ler_quadro
from .reconhecer import carregar_modelo, reconhecer_linha

#: Recorte de onde a amostra da `sky guitar` foi rotulada.
RECORTE_SKY = PARTES / "clipes" / "-6rawhontyg_000120_000200" / "linha_01_tablatura.png"


def imagem_da_amostra(am: dict) -> np.ndarray:
    """Imagem que originou os rótulos de uma amostra do gabarito.

    A amostra da `sky guitar` foi rotulada de um recorte local; as outras vêm do
    quadro do vídeo no acervo, na faixa (topo/base) registrada no gabarito.

    Args:
        am: uma entrada de ``amostras`` do gabarito.

    Returns:
        Imagem BGR (ou em tons de cinza, no caso do recorte local).
    """
    # O quadro é CACHEADO em disco. Motivo medido: o vídeo do `raman korshun` foi apagado do
    # acervo (o dono do projeto reorganiza e apaga) e `ler_quadro` devolveu None — o
    # avaliador estourava com TypeError e **24 dos 96 glifos do gabarito (25%) ficaram sem
    # verificação**. O número oficial passou a depender de arquivo que pode desaparecer.
    # Com o cache, o quadro lido uma vez fica ao lado do gabarito e a métrica sobrevive.
    canal = str(am.get("canal", "canal")).replace("/", "_")
    cache = FRAMES_GOLD / f"{canal}.png"
    if cache.exists():
        guardado = cv2.imread(str(cache), cv2.IMREAD_UNCHANGED)
        if guardado is not None:
            return guardado
    if not am.get("video") or am["video"].startswith("sky guitar"):
        recorte = cv2.imread(str(RECORTE_SKY), cv2.IMREAD_UNCHANGED)
        if recorte is not None:
            FRAMES_GOLD.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(cache), recorte)
        return recorte
    frame, _ = ler_quadro(str(acervo() / am["video"]), 0.5)
    if frame is None:
        return None  # vídeo ausente: quem chama PULA e declara, não estoura
    faixa = frame[620:1080, :] if am["faixa"] == "base" else frame[0:400, :]
    FRAMES_GOLD.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(cache), faixa)
    return faixa


def avaliar_com_modelo(
    modelo, rotulos: list[str], dev: str, usar_recuperada: bool = False
) -> list[tuple[str, int, int]]:
    """Aferição glifo a glifo no gabarito, com o modelo já carregado.

    Args:
        modelo: classificador de glifos.
        rotulos: classes na ordem de saída do modelo.
        dev: dispositivo onde o modelo está.
        usar_recuperada: compara `casa_recuperada` (a casa achada DENTRO de um
            símbolo fundido) em vez de `casa`. **Experimento medido e REPROVADO**:
            a média cai de 0,889 para 0,687 (pior nas 3 sementes; no `paolo`, 25→10),
            porque em token fundido por fragmento de corda o pedaço escolhido não é o
            algarismo. O campo continua gravado como informação, nunca como padrão.

    Returns:
        Uma tupla ``(canal, acertos, total)`` por amostra do gabarito.
    """
    # Obrigatório: em modo `train()` o Dropout(0.15) da rede segue ativo e a
    # aferição despenca. Medido nos MESMOS pesos e na MESMA imagem: 0,865 em
    # `eval()` contra 0,812 em `train()`. Era daí que vinha o número deprimido que
    # o treino reportava sobre o próprio modelo (0,771) enquanto o disco dava 0,865.
    modelo.eval()
    dados = json.loads(GABARITO.read_text(encoding="utf-8"))
    linhas: list[tuple[str, int, int]] = []
    for am in dados["amostras"]:
        if am.get("descartada"):
            # Fora de escopo por decisao do dono do projeto (instrumento errado), nao por
            # falha: entra como DESCARTADA, com o motivo, e nao como quadro indisponivel.
            linhas.append(
                (f"{am.get('canal', '?')} [descartada: {am['descartada'][:28]}]", 0, 0)
            )
            continue
        img = imagem_da_amostra(am)
        if img is None:
            # Vídeo ausente do acervo: PULA e DECLARA, com total negativo para o somatório
            # não contar como erro. Foi o que aconteceu com o `raman korshun`, apagado pelo
            # dono do projeto: antes disto o avaliador estourava e a aferição inteira caía.
            # total 0 = não entra no somatório (o `main` conta e declara à parte)
            linhas.append((f"{am.get('canal', '?')} SEM QUADRO", 0, 0))
            continue
        r = reconhecer_linha(img, modelo, rotulos, dev)
        campo = "casa_recuperada" if usar_recuperada else "casa"
        previsto = [n.get(campo) or n["casa"] for n in r["notas"]]
        # TRAVA DE DESLOCAMENTO: o gabarito é indexado pela POSIÇÃO do token
        # (`am["rotulos"][str(i)]`). Se a segmentação mudar de tamanho — e o delimitador
        # existe justamente para descartar token — os rótulos passam a apontar para outro
        # token e a aferição vira mentira SILENCIOSA. Medido: os 3 canais do gabarito têm
        # zero recusas hoje, por isso o número não mudou quando o delimitador entrou. A
        # partir daqui, contagem diferente é DECLARADA e fica fora da conta.
        esperado = am.get("n_tokens")
        if esperado is not None and len(previsto) != esperado:
            linhas.append(
                (
                    f"{am.get('canal', '?')} CONTAGEM MUDOU ({len(previsto)} != {esperado})",
                    0,
                    0,
                )
            )
            continue
        indices = sorted(int(k) for k in am["rotulos"])
        # Token que a segmentação não produziu conta como erro, não como exceção.
        acertos = sum(
            1
            for i in indices
            if i < len(previsto) and previsto[i] == am["rotulos"][str(i)]
        )
        linhas.append((am["canal"], acertos, len(indices)))
    return linhas


def avaliar(
    caminho_modelo: str, usar_recuperada: bool = False
) -> list[tuple[str, int, int]]:
    """Aferição glifo a glifo, carregando o modelo do disco.

    Args:
        caminho_modelo: pesos do classificador de glifos.

    Returns:
        Uma tupla ``(canal, acertos, total)`` por amostra do gabarito.
    """
    modelo, rotulos, dev = carregar_modelo(caminho_modelo)
    # O CASO `t_ini` do CONTEXTO §12 e a regra do §4.3: TODO numero diz qual modelo rodou,
    # imprimindo o caminho. O CA do T0.2 exige isto ("imprime o caminho").
    print(f"modelo carregado: {caminho_modelo}")

    return avaliar_com_modelo(modelo, rotulos, dev, usar_recuperada)


def main() -> int:
    """Imprime o acerto por canal e o total."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    ap.add_argument(
        "--recuperada",
        action="store_true",
        help="usa a casa recuperada de dentro do simbolo (experimento)",
    )
    args = ap.parse_args()

    linhas = avaliar(args.modelo, usar_recuperada=args.recuperada)
    validos = [(c, o, t) for c, o, t in linhas if t > 0]
    pulados = [c for c, _o, t in linhas if t == 0]
    acertos = sum(o for _, o, _ in validos)
    total = sum(t for _, _, t in validos)
    resumo = " ".join(f"{c.split()[0][:6]}={o}/{t}" for c, o, t in validos)
    print(f"RESULTADO {resumo} | TOTAL={acertos}/{total}={acertos / total:.3f}")
    descartadas = [c for c in pulados if "[descartada" in c]
    sem_quadro = [c for c in pulados if "[descartada" not in c]
    if descartadas:
        # Fora de ESCOPO por decisão do dono do projeto — não é falha nem falta.
        print(f"DESCARTADAS (fora de escopo): {', '.join(descartadas)}")
    if sem_quadro:
        # Sem quadro não há aferição: declarar é obrigatório, contar como erro seria mentira.
        print(f"SEM QUADRO (vídeo indisponível): {', '.join(sem_quadro)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
