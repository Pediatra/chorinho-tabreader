"""Reconhecimento da linha de tablatura: tokens -> (corda, casa, tecnica) -> JSON.

Junta as três camadas numa ferramenta só:
  1. geometria (tabseg): grade, tokens por corda/coluna;
  2. classificador minúsculo treinado só em dado sintético (tools/sintetico.py);
  3. verificação de FORMA, que é o que impede o modelo de alucinar uma classe
     incompatível com o recorte (um "12" não cabe em meio passo; um harmônico <n>
     precisa de mais de um componente). Sem ela, a última nota do gabarito era
     classificada como "harmonico" e o acerto ficava em 14/15.

Uso:
    python -m tab.reconhecer IMAGEM [--modelo artefatos/glifo_sint.pt] [--json saida.json]
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import statistics
import sys

import cv2
import numpy as np
import torch

from .caminhos import LIMIAR_SIMBOLO, MODELO_PADRAO, RAZAO_MINIMA_SIMBOLO
from .glyph_bench import GlifoCNN
from .glyphset import normalizar
from .tabseg import segmentar

#: Classes que são algarismo (a casa). Todo o resto é símbolo e tem de ser guardado.
ALGARISMOS = frozenset(str(n) for n in range(0, 25))

#: Limiar do discriminador "isto é algarismo?" na terceira passada. Varrido no protocolo do
#: canal deixado de fora (2 sementes x 8 canais; 176 algarismos, 56 não-algarismos):
#:
#:     limiar   recuperados        lixo virando nota errada
#:     0,50     162/176 (92 %)     7/56 (12 %)
#:     0,70     162/176 (92 %)     5/56  (9 %)
#:     0,80     160/176 (91 %)     4/56  (7 %)
#:     0,90     156/176 (89 %)     3/56  (5 %)
#:     0,95     154/176 (88 %)     1/56  (2 %)
#:
#: 0,95 porque a curva não cobra o preço: 4 pontos de recuperação a menos cortam a nota
#: errada por 6x. Algarismo NÃO recuperado não se perde (o símbolo continua guardado e
#: declarado); nota errada corrompe em silêncio, que é o pior dos dois.
LIMIAR_DISCRIMINADOR = 0.95


def compativel(classe: str, tk, passo: float) -> bool:
    """A classe prevista cabe no recorte medido?"""
    larg = (tk.x1 - tk.x0) / passo
    if classe.isdigit():
        # Piso de largura: um algarismo nao pode ter 2 px num painel de passo 21.6
        # (medido: fragmentos de barline de 2 px eram classificados como "1").
        if larg < 0.22:
            return False
        if len(classe) == 1:
            return larg <= 1.15
        # 2 dígitos exigem DOIS componentes com altura de algarismo: um "7" com a barra
        # de slide fundida no token fica largo e era aceito como "24" (erro medido no
        # canal raman korshun). O risco de slide é fino, não é dígito.
        return larg >= 0.85 and tk.partes_digito >= 2
    return True


def carregar_modelo(caminho: str):
    ck = torch.load(caminho)
    rot = ck["rotulos"]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = GlifoCNN(len(rot)).to(dev)
    m.load_state_dict(ck["state_dict"])
    m.eval()
    return m, rot, dev


def _recortar(
    gray: np.ndarray, x0: int, y0: int, x1: int, y1: int, margem: int = 0
) -> np.ndarray:
    """Recorte do token, com a convenção EXATA do classificador.

    Cuidado que custou uma medição: a convenção antiga era 1 px de margem em cima e à
    esquerda e NENHUMA embaixo/à direita (`gray[y0-1 : y1+1, x0-1 : x1+1]`). Eu havia
    trocado por margem simétrica e os MESMOS pesos passaram a dar 0,844 onde davam
    0,865. O recorte é parte da medição: mexer nele é mexer no número. O parâmetro
    `margem` existe só para o PNG de auditoria, que não entra na classificação.

    Args:
        gray: imagem em tons de cinza.
        x0, y0, x1, y1: caixa do token.
        margem: margem extra para o PNG (0 = convenção do classificador).

    Returns:
        O recorte.
    """
    if margem:
        return gray[
            max(0, y0 - margem) : y1 + margem + 1, max(0, x0 - margem) : x1 + margem + 1
        ]
    return gray[max(0, y0 - 1) : y1 + 1, max(0, x0 - 1) : x1 + 1]


def _probs(recortes: list[np.ndarray], modelo, dev) -> np.ndarray:
    """Probabilidade por classe para uma lista de recortes, numa passada só."""
    X = [normalizar(c) for c in recortes]
    X = [x if x is not None else np.zeros((24, 16), np.uint8) for x in X]
    xt = torch.tensor(np.stack(X)[:, None].astype(np.float32) / 255.0).to(dev)
    with torch.no_grad():
        return torch.softmax(modelo(xt), 1).cpu().numpy()


def _top3(probs: np.ndarray, rotulos: list[str]) -> list[tuple[str, float]]:
    """As três classes mais prováveis, com a probabilidade de cada uma."""
    ordem = np.argsort(-probs)
    return [(rotulos[int(k)], round(float(probs[int(k)]), 3)) for k in ordem[:3]]


def _guardar_cru(
    gray: np.ndarray, tk, destino_dir: str, prefixo: str, sufixo: dict, caixa=None
) -> dict:
    """Grava o recorte cru do token em PNG (ampliado) e devolve o registro dele.

    Deduplica por hash do conteúdo: símbolos idênticos viram UM arquivo, com o
    número de ocorrências implícito. É assim que o vocabulário de um canal se
    forma sozinho, sem eu precisar reabrir vídeo.

    Args:
        gray: imagem em tons de cinza de onde o token veio.
        tk: token (glifo fundido) a preservar.
        destino_dir: diretório raiz dos recortes.
        prefixo: subpasta (normalmente canal ou vídeo).
        sufixo: campos extras que entram no registro.
        caixa: ``(x0, y0, x1, y1)`` a recortar em vez do token. Serve para gravar **o componente
            do símbolo** quando o token é dígito + símbolo (medido: 47 de 51 recortes que
            *pareciam* algarismo eram isso) — recortar o token inteiro mostrava o algarismo.

    Returns:
        Registro do símbolo, com caminho e hash; nunca descarta o recorte.
    """
    x0, y0, x1, y1 = caixa or (tk.x0, tk.y0, tk.x1, tk.y1)
    crop = _recortar(gray, x0, y0, x1, y1, margem=2)
    if crop.size == 0:
        return {"png": None, "hash": None, **sufixo}
    ampliado = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
    ok, png = cv2.imencode(".png", ampliado)
    if not ok:
        return {"png": None, "hash": None, **sufixo}
    digest = hashlib.sha1(png.tobytes()).hexdigest()[:16]
    relativo = os.path.join(prefixo, f"{digest}.png") if prefixo else f"{digest}.png"
    caminho = os.path.join(destino_dir, relativo)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    if not os.path.exists(caminho):
        with open(caminho, "wb") as fh:
            fh.write(png.tobytes())
    return {"png": relativo, "hash": digest, **sufixo}


def reconhecer_linha(
    img: np.ndarray,
    modelo,
    rotulos,
    dev,
    dir_simbolos: str | None = None,
    prefixo: str = "",
    discriminador=None,
    filtro_simbolo=None,
) -> dict:
    """Lê uma linha de tablatura: geometria + classificação + símbolo cru.

    O símbolo **nunca é descartado**. Um `<7>` fundido num único token vira a classe
    `harmonico` e perderia a casa 7; por isso: (a) as caixas dos componentes são
    preservadas no token (`Glifo.componentes`), (b) a casa é procurada de novo DENTRO
    do símbolo, em cada componente, e vai para `casa_recuperada`, e (c) o recorte cru
    é gravado em PNG (`dir_simbolos`) para o mapa por canal ser construído depois,
    sem reabrir vídeo.

    Args:
        img: imagem da linha (BGR ou cinza).
        modelo: classificador de glifos.
        rotulos: classes na ordem de saída do modelo.
        dev: dispositivo do modelo.
        dir_simbolos: se dado, grava o PNG dos tokens que carregam símbolo.
        prefixo: subpasta dos PNGs (canal ou vídeo).

    Returns:
        Dicionário com passo, linhas, barlines e a lista de notas.
    """
    g = segmentar(img)
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tokens = sorted(g.glifos, key=lambda x: (x.coluna, x.corda))
    if not tokens:
        return {"passo": g.passo, "linhas_y": g.linhas_y, "notas": []}
    probs = _probs(
        [_recortar(gray, t.x0, t.y0, t.x1, t.y1) for t in tokens], modelo, dev
    )
    # Assinatura de lixo POR VIDEO: fracao de tokens estreitos (< 0.3 passo). Medido:
    # apenas o canal raman korshun apresenta isso (28%); iwaki/sky/paolo dao 0%.
    # Onde ha assinatura, token estreito e recusado em vez de virar "1" ou "harmonico".
    estreitos = sum(1 for t in tokens if (t.x1 - t.x0) < 0.30 * g.passo)
    assinatura = estreitos / max(1, len(tokens))
    recusar = assinatura > 0.10

    # 1a passada: classe de cada token, com o portao de forma.
    classes: list[tuple[str, bool]] = []
    # 3a passada: o DISCRIMINADOR decide se o token que o classificador chamou de símbolo é,
    # na verdade, um algarismo. Medido no gabarito de símbolos: 33% do que virava "símbolo"
    # era algarismo puro, e o limiar de confiança NÃO separa (p_digito de 0,17 a 1,00 nos
    # algarismos e de 0,11 a 0,92 no lixo). O discriminador dedicado faz 0,879-0,940 no canal
    # deixado de fora. `discriminador` é uma FUNÇÃO (recebe recortes, devolve probabilidades):
    # assim `reconhecer` não importa `digito`, que importa `_recortar` daqui.
    if discriminador is not None:
        idx_dig = [k for k, r in enumerate(rotulos) if r in ALGARISMOS]
        # `classes` pode ter MENOS entradas que `tokens` (o primeiro passo só classifica o
        # que passou no portão de forma). Iterar sobre `tokens` estourava IndexError — medido
        # no `ギタロー/guitarous`: 41 tokens e `classes` menor. O que não foi classificado não
        # tem classe para contestar, então fica de fora.
        alvos_d = [
            i
            for i in range(min(len(tokens), len(classes)))
            if classes[i][0] not in ALGARISMOS and len(tokens[i].componentes or ()) <= 1
        ]
        if alvos_d:
            recortes_d = [
                _recortar(gray, tokens[i].x0, tokens[i].y0, tokens[i].x1, tokens[i].y1)
                for i in alvos_d
            ]
            p_dig = discriminador(recortes_d)
            for k, i in enumerate(alvos_d):
                if float(p_dig[k]) >= LIMIAR_DISCRIMINADOR:
                    p = probs[i]
                    classes[i] = (
                        rotulos[max(idx_dig, key=lambda j: p[j])],
                        classes[i][1],
                    )

    for i, tk in enumerate(tokens):
        if recusar and (tk.x1 - tk.x0) < 0.30 * g.passo:
            classes.append(("junk", True))
            continue
        classe, corrigido = None, False
        for k in np.argsort(-probs[i]):
            if compativel(rotulos[k], tk, g.passo):
                classe = rotulos[k]
                corrigido = bool(int(k) != int(np.argmax(probs[i])))
                break
        if classe is None:
            classe = rotulos[int(np.argmax(probs[i]))]
        classes.append((classe, corrigido))

    # 2a passada: dentro de símbolo (ou de token fundido), procurar a casa.
    alvos = [
        i
        for i, tk in enumerate(tokens)
        if classes[i][0] not in ALGARISMOS or tk.partes > 1
    ]
    recortes: list[np.ndarray] = []
    comp_de: dict[int, list[tuple[int, tuple[int, int, int, int]]]] = {}
    for i in alvos:
        tk = tokens[i]
        caixas = list(tk.componentes or ((tk.x0, tk.y0, tk.x1, tk.y1),))
        pares: list[tuple[int, tuple[int, int, int, int]]] = []
        for caixa in caixas:
            pares.append((len(recortes), caixa))
            recortes.append(_recortar(gray, *caixa))
        comp_de[i] = pares
    probs_comp = _probs(recortes, modelo, dev) if recortes else np.zeros((0, 1))

    notas = []
    for i, tk in enumerate(tokens):
        classe, corrigido = classes[i]
        nota: dict = {
            "ordem": i + 1,
            "corda": int(tk.corda),
            "casa": classe,
            "tecnica": "harmonico" if classe == "harmonico" else None,
            "x": int(tk.x0),
            "confianca": round(float(probs[i][int(np.argmax(probs[i]))]), 3),
            "corrigido_pela_forma": corrigido,
        }
        if i in alvos:
            casa_rec, conf_rec, topo = None, 0.0, None
            for pos, (cx0, _, cx1, _) in comp_de[i]:
                argmax = int(np.argmax(probs_comp[pos]))
                classe_comp = rotulos[argmax]
                if classe_comp in ALGARISMOS and (cx1 - cx0) >= 0.22 * g.passo:
                    conf = float(probs_comp[pos][argmax])
                    if conf > conf_rec:
                        casa_rec, conf_rec = classe_comp, conf
                if topo is None:
                    topo = _top3(probs_comp[pos], rotulos)
            caixas = tk.componentes or ((tk.x0, tk.y0, tk.x1, tk.y1),)
            sufixo = {
                "partes": tk.partes,
                "partes_digito": tk.partes_digito,
                "larguras_passo": [
                    round((cx1 - cx0) / g.passo, 2) for cx0, _, cx1, _ in caixas
                ],
                "componentes": [
                    (cx0 - tk.x0, cy0 - tk.y0, cx1 - tk.x0, cy1 - tk.y0)
                    for cx0, cy0, cx1, cy1 in caixas
                ],
                "classe": classe,
                "top3": _top3(probs[i], rotulos),
                "top3_componente": topo,
                "casa_recuperada": casa_rec,
                "confianca_recuperada": round(conf_rec, 3),
            }
            if casa_rec is not None:
                nota["casa_recuperada"] = casa_rec
            # FILTRO POSITIVO: só guarda como símbolo o que o detector diz que É símbolo — o
            # critério antigo era "não é algarismo", e o resíduo de uma tablatura é ~98 % linha,
            # borrão e dígito mal lido. O recorte usa a JANELA DO TREINO (2,4 x 1,6 passo,
            # centrado no token): moldura é entrada do modelo, não detalhe de implementação.
            # DECISÃO POR COMPONENTE, não por token. Medido: 47 dos 51 recortes que pareciam
            # algarismo eram token fundido de dígito + símbolo; e recortar o token inteiro mostra
            # o dígito. Recortar "o componente que não é algarismo" também falhou (REPROVADO na
            # verificação: o classificador por componente erra um dígito de um `11` fundido e ele
            # vira "o símbolo"). O certo é: **cada componente é um candidato**, com a janela
            # centrada nele, e quem decide é o detector — não a classe do componente.
            hx, hy = round(1.2 * g.passo), round(0.8 * g.passo)
            caixa_simbolo, p_simbolo = None, None
            componentes = comp_de.get(i) or ()
            if filtro_simbolo is not None and componentes:
                for _pos, (cx0, cy0, cx1, cy1) in componentes:
                    razao_c = (cx1 - cx0 + 1) / max(1.0, float(cy1 - cy0 + 1))
                    if razao_c < RAZAO_MINIMA_SIMBOLO:  # barra vertical: não é símbolo
                        continue
                    ccx, ccy = (cx0 + cx1) // 2, (cy0 + cy1) // 2
                    rec_c = gray[
                        max(0, ccy - hy) : ccy + hy, max(0, ccx - hx) : ccx + hx
                    ]
                    if rec_c.size == 0:
                        continue
                    pc = float(filtro_simbolo([rec_c])[0])
                    if p_simbolo is None or pc > p_simbolo:
                        p_simbolo, caixa_simbolo = pc, (cx0, cy0, cx1, cy1)
                sufixo["componentes_avaliados"] = len(componentes)
            # BARRA VERTICAL NÃO É SÍMBOLO (instrução do dono sobre o `shin izumi`: "essas barras
            # na vertical não significam nada de importante"). Medido: as barras que o detector
            # aprovava lá têm razão mediana 0,118 e os 123 símbolos verdadeiros têm 1,706 — ZERO
            # dos 123 abaixo de 0,35. Regra antes do modelo, porque é determinística e sem colateral.
            razao = (tk.x1 - tk.x0 + 1) / max(1.0, float(tk.y1 - tk.y0 + 1))
            if razao < RAZAO_MINIMA_SIMBOLO:
                sufixo["recusado_por_forma"] = f"barra_vertical (razao {razao:.2f})"
            elif filtro_simbolo is not None and p_simbolo is None:
                cx = (tk.x0 + tk.x1) // 2
                cy = (tk.y0 + tk.y1) // 2
                rec = gray[max(0, cy - hy) : cy + hy, max(0, cx - hx) : cx + hx]
                if rec.size:
                    p_simbolo = float(filtro_simbolo([rec])[0])
            if p_simbolo is not None:
                sufixo["prob_simbolo"] = round(p_simbolo, 3)
            passa = "recusado_por_forma" not in sufixo and (
                p_simbolo is None or p_simbolo >= LIMIAR_SIMBOLO
            )
            if componentes and p_simbolo is not None and p_simbolo < LIMIAR_SIMBOLO:
                caixa_simbolo = None  # nenhum componente passou: não guarda nenhum
            if passa:
                if caixa_simbolo is not None:
                    sufixo["recorte_do_componente"] = True
                nota["simbolo_cru"] = (
                    _guardar_cru(
                        gray, tk, dir_simbolos, prefixo, sufixo, caixa=caixa_simbolo
                    )
                    if dir_simbolos
                    else sufixo
                )
            else:
                # RECUSADO como símbolo. O metadado fica em chave PRÓPRIA: se ficasse em
                # `simbolo_cru`, quem conta símbolo (`[n for n in notas if "simbolo_cru" in n]`)
                # contaria o recusado também — foi o que aconteceu na primeira medição, e o
                # total não se mexeu. Conferir o que o número conta, sempre.
                nota["simbolo_recusado"] = sufixo
        notas.append(nota)
    return {
        "passo": round(g.passo, 2),
        "linhas_y": g.linhas_y,
        "barlines_x": g.barlines_x,
        "notas": notas,
    }


def completar(r: dict, tempos: list[tuple] | None = None) -> dict:
    """Acrescenta compasso (pelas barlines) e andamento (pelos onsets do cursor).

    Andamento honesto: o que a imagem e o cursor permitem medir é NOTAS POR MINUTO e
    quantas notas cabem em cada compasso. BPM só sai disso com uma suposição de figura
    (por isso vai separado, com o nome dizendo a suposição).
    """
    bl = r.get("barlines_x") or []
    for n in r["notas"]:
        n["compasso"] = 1 + sum(1 for bx in bl[1:] if bx < n["x"])
    por_compasso = {}
    for n in r["notas"]:
        por_compasso[n["compasso"]] = por_compasso.get(n["compasso"], 0) + 1
    r["notas_por_compasso"] = por_compasso
    if tempos and len(tempos) >= len(r["notas"]):
        onsets = [t[0] for t in tempos[: len(r["notas"])] if t and t[0] is not None]
        for n, t in zip(r["notas"], tempos, strict=False):
            if t and t[0] is not None:
                n["t_ini"] = round(t[0], 2)
                if t[1] is not None:
                    n["t_fim"] = round(t[1], 2)
        if len(onsets) > 2:
            dt = statistics.median([b - a for a, b in itertools.pairwise(onsets)])
            rpm = 60.0 / dt if dt > 0 else None
            r["andamento"] = {
                "notas_por_minuto": round(rpm, 1) if rpm else None,
                "intervalo_mediano_s": round(dt, 3),
                "notas_por_compasso_medido": round(
                    sum(por_compasso.values()) / max(1, len(por_compasso)), 2
                ),
                "bpm_se_1_nota_por_tempo": round(rpm, 1) if rpm else None,
            }
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("imagem")
    ap.add_argument("--modelo", default=str(MODELO_PADRAO))
    ap.add_argument("--json")
    args = ap.parse_args()
    img = cv2.imread(args.imagem, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"não abri {args.imagem}", file=sys.stderr)
        return 2
    modelo, rotulos, dev = carregar_modelo(args.modelo)
    r = reconhecer_linha(img, modelo, rotulos, dev)
    r["fonte"] = os.path.basename(args.imagem)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:900])
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
