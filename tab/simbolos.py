"""Inventário de símbolos por canal: separar o vocabulário para significar depois.

Decisão do dono do projeto (2026-10-09): *"símbolos vamos classificar com imagens
depois; separe os símbolos encontrados de todos os canais e depois a gente separa e dá
significado."* Este módulo faz a parte de **separar**:

1. amostra **3 vídeos por canal** do acervo e lê **2 instantes** de cada um (frações
   0,65 e 0,85 da duração — a tablatura costuma aparecer da metade para o fim, ver
   `ESTADO.md`);
2. em cada instante lê o quadro (`tab.inventario.ler_quadro`), escolhe o painel
   (`tab.painel.escolher`) e roda `tab.reconhecer.reconhecer_linha` **com gravação de
   símbolo**: todo token não numérico vira recorte PNG ampliado, deduplicado por hash do
   conteúdo, em ``data/saida/simbolos/<canal>/<hash>.png``;
3. agrega por canal — tokens, símbolos, fração, distribuição de `classe` e de
   `larguras_passo`, e os hashes mais frequentes com contagem;
4. desenha uma **montagem legível por canal** (grade dos recortes, com hash e contagem
   desenhados), para o dono ler no olho e dar significado.

Uso:
    python -m tab.simbolos --por-canal 3 --fracoes 0.65 0.85

O resultado do reconhecimento não é aferido aqui: o que este módulo mede é
**vocabulário e frequência**, não acerto. A acurácia continua sendo `tab.avaliar`.

Ressalva medida, que não se esconde: o portão de painel é conhecido por escolher o
**violão** e o **piano** como tablatura (`ESTADO.md`, 2026-10-09) e isso contamina a
amostra. Por isso todo quadro sai com `faixa`, `uniformidade` e `passo`, e o resumo do
canal declara `passo_mediano`, `quadros_passo_plausivel` e `simbolos_passo_plausivel`
(passo de tablatura: 14–45 px). Nada é filtrado — símbolo de painel suspeito fica no
JSON e na montagem, marcado.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import pathlib
import random
import statistics
import time
from collections.abc import Sequence
from datetime import UTC, datetime

import cv2
import numpy as np

from tab.caminhos import ARTEFATOS, SAIDA, acervo
from tab.digito import carregar
from tab.inventario import ler_quadro
from tab.painel import escolher
from tab.reconhecer import carregar_modelo, reconhecer_linha
from tab.simbolo import carregar as carregar_detector_simbolo

# O OpenCV grita a cada vídeo AV1 (44% do acervo) e isso poluiria o log da amostra.
cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)

#: Frações da duração amostradas. Medido (`ESTADO.md`): a tablatura aparece da METADE
#: para o fim, então 0,65 e 0,85 caem na janela útil e evitam vinheta e despedida.
FRACOES_PADRAO = (0.65, 0.85)

#: Modelo oficial (0,889 de média em 3 sementes) — o mesmo do ponta a ponta.
MODELO_OFICIAL = ARTEFATOS / "oficial_2" / "glifo_sint.pt"

#: Recortes crus de símbolo, uma pasta por canal (`reconhecer_linha` escreve aqui).
DIR_SIMBOLOS = SAIDA / "simbolos"

#: Extensões de vídeo varridas no acervo (as mesmas de `tab.varredura`).
EXTENSOES = ("*.mp4", "*.mkv", "*.webm")

#: Faixa de passo (px) medida no acervo para tablatura de verdade (`ESTADO.md`: "passo
#: entre cordas de 14 a 45 px"). Serve só para ROTULAR o quadro: o portão de painel é
#: conhecido por escolher violão/piano (`ESTADO.md`, 2026-10-09) e nada é descartado por
#: causa disto — o que não é plausível sai declarado no JSON, não escondido.
PASSO_MIN = 14.0
PASSO_MAX = 45.0

#: Geometria da montagem: 6 por linha limita a largura a ~1360 px e mantém o recorte
#: legível; 48 itens (8 linhas) priorizam frequência em vez de completude.
COLS_MONTAGEM = 6
MAX_MONTAGEM = 48
CAIXA_L = 220
CAIXA_A = 170
ROTULO_H = 38
LACUNA = 6

#: Fonte do OpenCV. É Hershey (ASCII): rótulo desenhado NÃO leva acento.
FONTE = cv2.FONT_HERSHEY_SIMPLEX


def slug(nome: str) -> str:
    """Nome de canal em nome seguro de arquivo.

    Args:
        nome: nome do canal como está no acervo.

    Returns:
        O nome com separadores de caminho trocados por ``_`` (espaço continua espaço).
    """
    return nome.replace(os.sep, "_").replace("/", "_")


def listar_canais(raiz: str) -> dict[str, list[str]]:
    """Vídeos por canal, em ordem estável (um canal = uma pasta do acervo).

    Args:
        raiz: raiz do acervo.

    Returns:
        Dicionário canal -> lista ordenada de caminhos de vídeo.
    """
    achados: dict[str, list[str]] = {}
    for d in sorted(glob.glob(os.path.join(raiz, "*"))):
        if not os.path.isdir(d):
            continue
        nome = os.path.basename(d)
        if nome == "derived":
            continue
        vids: list[str] = []
        for padrao in EXTENSOES:
            vids += glob.glob(os.path.join(d, "**", padrao), recursive=True)
        if vids:
            achados[nome] = sorted(vids)
    return achados


def amostrar(raiz: str, por_canal: int, seed: int = 0) -> dict[str, list[str]]:
    """Amostra ``por_canal`` vídeos de cada canal, com semente fixa.

    Semente fixa existe para a amostra ser reprodutível: comparar duas execuções só
    vale se elas olharam os mesmos vídeos.

    Args:
        raiz: raiz do acervo.
        por_canal: quantos vídeos por canal (0 ou negativo = todos).
        seed: semente do sorteio.

    Returns:
        Dicionário canal -> lista de vídeos amostrados (ordenada).
    """
    rng = random.Random(seed)
    amostra: dict[str, list[str]] = {}
    for canal, vids in listar_canais(raiz).items():
        if por_canal > 0 and len(vids) > por_canal:
            amostra[canal] = sorted(rng.sample(vids, por_canal))
        else:
            amostra[canal] = vids
    return amostra


def reconhecer_quadro(
    frame: np.ndarray,
    modelo,
    rotulos: list[str],
    dev: str,
    canal: str,
    dir_simbolos: str | None = None,
) -> dict:
    """Escolhe o painel do quadro e lê a linha, gravando o símbolo cru.

    Args:
        frame: quadro inteiro.
        modelo: classificador de glifos.
        rotulos: classes na ordem de saída do modelo.
        dev: dispositivo do modelo.
        canal: nome do canal (vira subpasta dos recortes).
        dir_simbolos: raiz dos recortes; se None, o símbolo é registrado sem PNG.

    Returns:
        Dicionário com `tab`, `faixa`, `uniformidade`, `passo`, `tokens` e `simbolos`
        (a lista de `simbolo_cru` de cada token que carrega símbolo).
    """
    c = escolher(frame)
    if c is None:
        return {"tab": False, "tokens": 0, "simbolos": []}
    r = reconhecer_linha(
        c.roi,
        modelo,
        rotulos,
        dev,
        dir_simbolos=dir_simbolos,
        prefixo=canal,
        discriminador=carregar(),
        # FILTRO POSITIVO: só guarda o que o detector diz que É símbolo. O critério antigo
        # guardava o resíduo do classificador de algarismo (~98% linha, borrão e dígito errado).
        filtro_simbolo=carregar_detector_simbolo(),
    )
    notas = r["notas"]
    return {
        "tab": True,
        "faixa": c.nome,
        "uniformidade": round(float(c.uniformidade), 3),
        "passo": r["passo"],
        "tokens": len(notas),
        "simbolos": [n["simbolo_cru"] for n in notas if "simbolo_cru" in n],
        # DELIMITADOR: o que ele recusou, por motivo. Sem isto o inventário diria quantos
        # símbolos existem sem dizer quanto lixo foi barrado — e o objetivo pede que nada
        # suma em silêncio.
        "recusados": dict(c.grade.recusados or {}),
    }


def medir_video(
    caminho: str,
    canal: str,
    raiz: str,
    modelo,
    rotulos: list[str],
    dev: str,
    fracoes: Sequence[float],
    dir_simbolos: str | None,
) -> list[dict]:
    """Lê um vídeo nos instantes pedidos; devolve um registro por instante.

    A falha é **registrada**, não escondida: quadro que não decodifica e erro de
    reconhecimento saem no registro com a chave `erro`, e o `main` aborta se o erro for
    sistemático (mais da metade dos quadros).

    Args:
        caminho: caminho do vídeo.
        canal: nome do canal.
        raiz: raiz do acervo (para gravar o caminho relativo).
        modelo: classificador de glifos.
        rotulos: classes do modelo.
        dev: dispositivo do modelo.
        fracoes: frações da duração a amostrar.
        dir_simbolos: raiz dos recortes de símbolo.

    Returns:
        Lista de registros, um por fração.
    """
    relativo = os.path.relpath(caminho, raiz) if raiz else caminho
    registros: list[dict] = []
    for frac in fracoes:
        reg: dict = {"canal": canal, "arquivo": relativo, "frac": round(float(frac), 4)}
        try:
            frame, via = ler_quadro(caminho, frac)
            reg["via"] = via
            if frame is None:
                reg.update(
                    {"tab": False, "tokens": 0, "simbolos": [], "erro": "decodificacao"}
                )
            else:
                reg.update(
                    reconhecer_quadro(frame, modelo, rotulos, dev, canal, dir_simbolos)
                )
        except Exception as exc:  # nunca derrubar a amostra inteira por um quadro
            reg.update(
                {
                    "tab": False,
                    "tokens": 0,
                    "simbolos": [],
                    "erro": f"{type(exc).__name__}: {exc}",
                }
            )
        registros.append(reg)
    return registros


def resumir_canal(registros: list[dict]) -> dict:
    """Agrega os registros de UM canal: tokens, símbolos, classes e hashes.

    O passo da grade entra como **rótulo de confiança do painel**, não como filtro: o
    portão de tablatura é conhecido por escolher violão e piano (`ESTADO.md`), e o passo
    fica fora de 14–45 px quando isso acontece. Os campos `passo_mediano`,
    `quadros_passo_plausivel` e `simbolos_passo_plausivel` deixam separar, depois, o que
    veio de painel plausível do que veio de painel suspeito, sem perder nada.

    Args:
        registros: registros de quadro do canal (ver `medir_video`).

    Returns:
        Resumo pronto para JSON, com contagens, fração, distribuições e os hashes
        ordenados por frequência decrescente.
    """
    quadros = len(registros)
    quadros_tab = sum(1 for r in registros if r.get("tab"))
    tokens = sum(int(r.get("tokens") or 0) for r in registros)
    classes: collections.Counter = collections.Counter()
    larguras: collections.Counter = collections.Counter()
    hashes: collections.Counter = collections.Counter()
    hashes_plaus: collections.Counter = collections.Counter()
    recusados: collections.Counter = collections.Counter()
    for r in registros:
        for motivo, n in (r.get("recusados") or {}).items():
            recusados[motivo] += int(n)
    png_de: dict[str, str] = {}
    classe_de: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    passos: list[float] = []
    simbolos = 0
    sem_hash = 0
    quadros_plaus = 0
    simbolos_plaus = 0
    for r in registros:
        plausivel = False
        if r.get("tab") and r.get("passo"):
            passo = float(r["passo"])
            passos.append(passo)
            plausivel = PASSO_MIN <= passo <= PASSO_MAX
            quadros_plaus += int(plausivel)
        for s in r.get("simbolos") or ():
            simbolos += 1
            simbolos_plaus += int(plausivel)
            classes[str(s.get("classe"))] += 1
            for larg in s.get("larguras_passo") or ():
                larguras[f"{float(larg):.2f}"] += 1
            chave = s.get("hash")
            if not chave:
                sem_hash += 1
                continue
            hashes[str(chave)] += 1
            hashes_plaus[str(chave)] += int(plausivel)
            png_de.setdefault(str(chave), str(s.get("png") or ""))
            classe_de[str(chave)][str(s.get("classe"))] += 1
    mais = [
        {
            "hash": h,
            "n": n,
            "n_passo_plausivel": hashes_plaus[h],
            "classe": classe_de[h].most_common(1)[0][0] if classe_de[h] else None,
            "png": png_de.get(h, ""),
        }
        for h, n in hashes.most_common()
    ]
    return {
        "quadros": quadros,
        "quadros_com_tablatura": quadros_tab,
        "tokens": tokens,
        "simbolos": simbolos,
        "fracao": round(simbolos / tokens, 4) if tokens else 0.0,
        "simbolos_sem_hash": sem_hash,
        "passo_mediano": round(float(statistics.median(passos)), 1) if passos else None,
        "quadros_passo_plausivel": quadros_plaus,
        "simbolos_passo_plausivel": simbolos_plaus,
        # ATENÇÃO ao nome: `classes` conta a classe APENAS dos SÍMBOLOS guardados, não de
        # todos os tokens. Eu li errado e acusei o `mr. tabs` de ler 5% de algarismo; medido
        # nos mesmos instantes, ele lê 95% (603 de 635 tokens). O campo não estava errado,
        # o nome é que engana. `algarismos_em_simbolos` é este número com nome honesto.
        "classes_dos_simbolos": dict(classes.most_common()),
        "classes": dict(classes.most_common()),
        "larguras_passo": dict(sorted(larguras.items(), key=lambda kv: float(kv[0]))),
        "hashes_distintos": len(hashes),
        "hashes": mais,
        # O que o DELIMITADOR recusou, por motivo. Fica no artefato para que o número de
        # símbolos não apareça sozinho: o inventário diz também quanto lixo foi barrado.
        "recusados": dict(recusados.most_common()),
        "recusados_total": int(sum(recusados.values())),
    }


def agregar(registros: list[dict]) -> dict[str, dict]:
    """Agrupa registros de quadro por canal e resume cada canal.

    Args:
        registros: registros de quadro, de um ou mais canais.

    Returns:
        Dicionário canal -> resumo (ver `resumir_canal`).
    """
    por_canal: dict[str, list[dict]] = collections.defaultdict(list)
    for r in registros:
        por_canal[str(r.get("canal"))].append(r)
    return {canal: resumir_canal(rs) for canal, rs in por_canal.items()}


def registro_publico(r: dict, raiz: str = "") -> dict:
    """Registro de um quadro sem os recortes, para o JSON do inventário.

    Args:
        r: registro de quadro (ver `medir_video`); `medir_video` já grava o caminho
            relativo à raiz, e só caminho absoluto é relativizado de novo.
        raiz: raiz do acervo, para gravar o caminho relativo.

    Returns:
        O registro sem a lista de símbolos, que vira a contagem `n_simbolos`.
    """
    arquivo = r.get("arquivo")
    if raiz and arquivo and os.path.isabs(str(arquivo)):
        arquivo = os.path.relpath(str(arquivo), raiz)
    return {
        "arquivo": arquivo,
        "frac": r.get("frac"),
        "via": r.get("via"),
        "tab": bool(r.get("tab")),
        "faixa": r.get("faixa"),
        "uniformidade": r.get("uniformidade"),
        "passo": r.get("passo"),
        "tokens": int(r.get("tokens") or 0),
        "n_simbolos": len(r.get("simbolos") or ()),
        "erro": r.get("erro"),
    }


def cobertura_de_marcas(amostra: dict[str, list[dict]]) -> dict:
    """Quantos vídeos amostrados têm tablatura MARCADA pelo dono?

    Existe por causa de um erro caro: o detector era treinado em 28 vídeos e medido em 51
    **quase disjuntos** (interseção = 1), e a validação por canal não via isso porque deixa um
    CANAL de fora mas mantém os mesmos vídeos. Sete hipóteses foram gastas antes de alguém contar
    a interseção. O inventário passa a declarar isso, para o erro não voltar em silêncio.

    Args:
        amostra: canal -> lista de itens amostrados (com `arquivo`).

    Returns:
        Contagem de vídeos amostrados, quantos têm tablatura entregue para marcar, a fração e os
        canais sem nenhuma.
    """
    marcados: set[tuple[str, str]] = set()
    for caminho in glob.glob(str(DIR_SIMBOLOS.parent / "*" / "indice*.json")):
        try:
            for r in json.loads(pathlib.Path(caminho).read_text(encoding="utf-8")):
                marcados.add(
                    (
                        str(r.get("canal")),
                        pathlib.Path(
                            str(r.get("video") or r.get("arquivo") or "")
                        ).name[:24],
                    )
                )
        except OSError, ValueError, TypeError:
            continue
    # Conta VÍDEOS ÚNICOS, não frames: a amostra tem 2 instantes por vídeo, e a primeira versão
    # deste campo dizia "videos_amostrados: 102" para 51 vídeos — número certo, legenda errada,
    # que é a armadilha que já me pegou quatro vezes neste projeto.
    vistos: dict[str, list[int]] = {}
    ja: set[tuple[str, str]] = set()
    for canal, itens in amostra.items():
        conta = vistos.setdefault(str(canal), [0, 0])
        for it in itens:
            chave = (str(canal), pathlib.Path(str(it.get("arquivo", ""))).name[:24])
            if (
                chave in ja
            ):  # deduplica TODO vídeo (antes eu deduplicava só os marcados, e
                continue  # vídeo sem marca contava 2x: 82 "vídeos" para 51 de verdade)
            ja.add(chave)
            conta[0] += 1
            if chave in marcados:
                conta[1] += 1
    total = sum(v[0] for v in vistos.values())
    n_marca = sum(v[1] for v in vistos.values())
    # Nome honesto: o que existe hoje é a tablatura ENTREGUE para marcar (o índice), não
    # necessariamente a marcada (o ouro). Chamar de "marcada" seria a legenda errada de novo.
    sem_marca = sorted(c for c, (tot, mar) in vistos.items() if tot and mar == 0)
    return {
        "videos_amostrados": total,
        "videos_com_tablatura_entregue": n_marca,
        "fracao": round(n_marca / total, 3) if total else 0.0,
        "canais_sem_nenhuma_marca": sem_marca,
    }


def montar_inventario(
    por_canal: dict[str, dict],
    amostra: dict[str, list[dict]],
    modelo: str,
    raiz: str,
    fracoes: Sequence[float],
) -> dict:
    """Monta o JSON final do inventário: resumo global, canais e amostra usada.

    Args:
        por_canal: resumo por canal (ver `resumir_canal`).
        amostra: registros públicos por canal (ver `registro_publico`).
        modelo: caminho do modelo usado.
        raiz: raiz do acervo.
        fracoes: frações amostradas.

    Returns:
        Dicionário serializável em JSON. Todo canal da amostra aparece, mesmo com zero
        símbolos — canal sem símbolo é medição, não omissão.
    """
    canais = sorted(set(amostra) | set(por_canal))
    detalhado = {c: por_canal.get(c) or resumir_canal([]) for c in canais}
    tokens = sum(int(r["tokens"]) for r in detalhado.values())
    simbolos = sum(int(r["simbolos"]) for r in detalhado.values())
    return {
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "modelo": modelo,
        "raiz": raiz,
        "fracoes": [round(float(f), 3) for f in fracoes],
        "resumo": {
            "canais": len(canais),
            "quadros": sum(int(r["quadros"]) for r in detalhado.values()),
            "quadros_com_tablatura": sum(
                int(r["quadros_com_tablatura"]) for r in detalhado.values()
            ),
            "tokens": tokens,
            "simbolos": simbolos,
            "fracao": round(simbolos / tokens, 4) if tokens else 0.0,
        },
        "por_canal": detalhado,
        "amostra": {c: amostra.get(c, []) for c in canais},
        # Declara se o par treino/teste fala da MESMA distribuição de vídeos. Foi a
        # ausência disto que fez o detector parecer perfeito e falhar no uso.
        "cobertura_de_marcas": cobertura_de_marcas(amostra),
    }


def _carregar_recorte(dir_simbolos: str, canal: str, item: dict) -> np.ndarray | None:
    """Lê o PNG de um símbolo; tenta o caminho do registro e o padrão do canal.

    Args:
        dir_simbolos: raiz dos recortes.
        canal: nome do canal.
        item: entrada de hash do resumo (com `png` e `hash`).

    Returns:
        O recorte em tons de cinza, ou None se o arquivo não existir.
    """
    candidatos: list[str] = []
    if item.get("png"):
        candidatos.append(os.path.join(dir_simbolos, str(item["png"])))
    if item.get("hash"):
        candidatos.append(
            os.path.join(dir_simbolos, slug(canal), f"{item['hash']}.png")
        )
    for caminho in candidatos:
        img = cv2.imread(caminho, cv2.IMREAD_GRAYSCALE)
        if img is not None and img.size:
            return img
    return None


def _celula(
    img: np.ndarray | None, titulo: str, sub: str, caixa_l: int, caixa_a: int
) -> np.ndarray:
    """Uma célula da montagem: recorte ampliado e duas linhas de rótulo.

    Args:
        img: recorte do símbolo em tons de cinza, ou None.
        titulo: primeira linha do rótulo (o hash).
        sub: segunda linha do rótulo (contagem e classe).
        caixa_l: largura da caixa do recorte, em px.
        caixa_a: altura da caixa do recorte, em px.

    Returns:
        A célula BGR, já com a faixa de rótulo.
    """
    cel = np.full((caixa_a + ROTULO_H, caixa_l, 3), 235, np.uint8)
    if img is not None:
        h, w = img.shape[:2]
        esc = min((caixa_l - 10) / max(1, w), (caixa_a - 10) / max(1, h), 3.0)
        alvo = (max(1, int(w * esc)), max(1, int(h * esc)))
        # Ampliar em NEAREST preserva o pixel do recorte cru (nada de pixel inventado).
        interp = cv2.INTER_AREA if esc < 1.0 else cv2.INTER_NEAREST
        grande = cv2.resize(img, alvo, interpolation=interp)
        if grande.ndim == 2:
            grande = cv2.cvtColor(grande, cv2.COLOR_GRAY2BGR)
        x = (caixa_l - alvo[0]) // 2
        y = (caixa_a - alvo[1]) // 2
        cel[y : y + alvo[1], x : x + alvo[0]] = grande
    else:
        cv2.putText(
            cel, "sem PNG", (10, caixa_a // 2), FONTE, 0.6, (0, 0, 255), 1, cv2.LINE_AA
        )
    cv2.putText(cel, titulo, (6, caixa_a + 15), FONTE, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(cel, sub, (6, caixa_a + 32), FONTE, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.rectangle(
        cel, (0, 0), (caixa_l - 1, caixa_a + ROTULO_H - 1), (150, 150, 150), 1
    )
    return cel


def _ordem_montagem(item: dict) -> tuple[int, int, int, str]:
    """Ordem de leitura da montagem: não-`junk`, painel plausível, frequência, hash.

    Args:
        item: entrada de hash do resumo do canal.

    Returns:
        Chave ordenável (menor vem primeiro).
    """
    classe = str(item.get("classe") or "?")
    return (
        1 if classe == "junk" else 0,
        -int(item.get("n_passo_plausivel") or 0),
        -int(item.get("n") or 0),
        str(item.get("hash") or ""),
    )


def montar_montagem(
    canal: str,
    resumo: dict,
    dir_simbolos: str,
    destino: str,
    max_itens: int = MAX_MONTAGEM,
) -> str:
    """Desenha a montagem dos símbolos de um canal, com hash e contagem.

    A montagem é para **leitura a olho**: legibilidade vale mais que completude. Entram
    só os ``max_itens`` recortes, com os de **classe não-`junk` primeiro** e, dentro
    disso, os de **painel plausível** (contagem em quadro de passo 14–45 px) e os mais
    frequentes. Sem essa ordem, os fragmentos de barline e de corda — que são muitos e
    únicos — ocupariam a imagem inteira e o símbolo de verdade não apareceria. O
    cabeçalho diz quantos ficaram de fora. Cada célula traz o recorte ampliado (o mesmo
    PNG gravado por `reconhecer_linha`), o hash (para casar com o JSON), a contagem
    total e a contagem em painel plausível.

    Os rótulos desenhados são ASCII: a fonte Hershey do OpenCV não desenha acento.

    Args:
        canal: nome do canal.
        resumo: saída de `resumir_canal` para o canal.
        dir_simbolos: raiz dos recortes (``<raiz>/<canal>/<hash>.png``).
        destino: caminho do PNG a gravar.
        max_itens: máximo de recortes desenhados.

    Returns:
        O caminho gravado.
    """
    todos = list(resumo.get("hashes") or [])
    itens = sorted(todos, key=_ordem_montagem)[:max_itens]
    carregados = [(_carregar_recorte(dir_simbolos, canal, h), h) for h in itens]

    linhas = (max(1, len(carregados)) + COLS_MONTAGEM - 1) // COLS_MONTAGEM
    grade_l = LACUNA + COLS_MONTAGEM * (CAIXA_L + LACUNA)
    classes = ", ".join(f"{k}={v}" for k, v in (resumo.get("classes") or {}).items())
    titulos = [
        f"{canal} - simbolos por canal ({resumo['hashes_distintos']} hashes distintos)",
        f"{resumo['simbolos']} simbolos em {resumo['tokens']} tokens "
        f"({resumo['fracao']:.1%}) | quadros com tablatura: "
        f"{resumo['quadros_com_tablatura']}/{resumo['quadros']}",
        f"passo mediano {resumo.get('passo_mediano')} px | quadros com passo 14-45: "
        f"{resumo.get('quadros_passo_plausivel')}/{resumo['quadros']} | simbolos "
        f"nesses quadros: {resumo.get('simbolos_passo_plausivel')}",
        f"classes: {classes or 'nenhuma'}"
        + (
            f" | mostrando {len(itens)} de {len(todos)} hashes"
            if len(todos) > max_itens
            else ""
        )
        + " | ordem: nao-junk, painel plausivel, frequencia | n=ocorrencias "
        "p=em painel plausivel",
    ]
    altura_titulo = 24 * len(titulos) + 12
    largura_txt = max(cv2.getTextSize(t, FONTE, 0.55, 1)[0][0] for t in titulos) + 16
    largura = max(grade_l, largura_txt)
    grade_a = LACUNA + linhas * (CAIXA_A + ROTULO_H + LACUNA)
    if not carregados:
        grade_a = LACUNA + 24
    canvas = np.full((altura_titulo + grade_a, largura, 3), 255, np.uint8)
    for i, t in enumerate(titulos):
        cv2.putText(
            canvas, t, (8, 24 * (i + 1)), FONTE, 0.55, (0, 0, 0), 1, cv2.LINE_AA
        )
    if not carregados:
        cv2.putText(
            canvas,
            "nenhum simbolo nesta amostra",
            (8, altura_titulo + 18),
            FONTE,
            0.55,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    for i, (img, item) in enumerate(carregados):
        linha, col = divmod(i, COLS_MONTAGEM)
        x = LACUNA + col * (CAIXA_L + LACUNA)
        y = altura_titulo + LACUNA + linha * (CAIXA_A + ROTULO_H + LACUNA)
        cel = _celula(
            img,
            str(item.get("hash")),
            f"n={item.get('n')} p={item.get('n_passo_plausivel')} "
            f"{item.get('classe') or '?'}",
            CAIXA_L,
            CAIXA_A,
        )
        canvas[y : y + cel.shape[0], x : x + cel.shape[1]] = cel
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    cv2.imwrite(destino, canvas)
    return destino


def main() -> int:
    """Amostra o acervo, agrega os símbolos por canal e desenha as montagens."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=str(acervo()))
    ap.add_argument("--por-canal", type=int, default=3)
    ap.add_argument("--fracoes", type=float, nargs="+", default=list(FRACOES_PADRAO))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--modelo", default=str(MODELO_OFICIAL))
    ap.add_argument("--saida", default=str(DIR_SIMBOLOS / "inventario.json"))
    ap.add_argument("--dir-simbolos", default=str(DIR_SIMBOLOS))
    ap.add_argument("--canais", nargs="*", default=None)
    ap.add_argument("--max-montagem", type=int, default=MAX_MONTAGEM)
    ap.add_argument("--sem-montagem", action="store_true")
    args = ap.parse_args()

    canais = amostrar(args.raiz, args.por_canal, args.seed)
    if args.canais:
        escolhidos = set(args.canais)
        canais = {c: v for c, v in canais.items() if c in escolhidos}
    if not canais:
        print(f"nenhum canal com vídeo em {args.raiz}", flush=True)
        return 2
    print(
        f"canais: {len(canais)} | vídeos: {sum(len(v) for v in canais.values())} | "
        f"frações: {list(args.fracoes)} | modelo: {args.modelo}",
        flush=True,
    )

    modelo, rotulos, dev = carregar_modelo(args.modelo)
    os.makedirs(args.dir_simbolos, exist_ok=True)
    t0 = time.time()
    registros: list[dict] = []
    for canal, vids in canais.items():
        for v in vids:
            for reg in medir_video(
                v,
                canal,
                args.raiz,
                modelo,
                rotulos,
                dev,
                tuple(args.fracoes),
                args.dir_simbolos,
            ):
                registros.append(reg)
                print(
                    f"[{time.time() - t0:7.1f}s] {canal[:18]:<18} "
                    f"{os.path.basename(v)[:30]:<30} frac={reg['frac']:.2f} "
                    f"via={reg.get('via')} tab={reg.get('tab')} "
                    f"tokens={reg.get('tokens')} "
                    f"simbolos={len(reg.get('simbolos') or ())}"
                    + (f" ERRO={reg['erro']}" if reg.get("erro") else ""),
                    flush=True,
                )

    erros = sum(1 for r in registros if r.get("erro"))
    if len(registros) >= 10 and erros / max(1, len(registros)) > 0.5:
        print(
            f"ABORTADO: {erros} de {len(registros)} quadros com erro — é bug "
            "sistemático, não amostra ruim",
            flush=True,
        )
        return 1

    por_canal = {
        canal: resumir_canal([r for r in registros if r["canal"] == canal])
        for canal in canais
    }
    amostra = {
        canal: [
            registro_publico(r, args.raiz) for r in registros if r["canal"] == canal
        ]
        for canal in canais
    }
    inventario = montar_inventario(
        por_canal, amostra, args.modelo, args.raiz, tuple(args.fracoes)
    )
    os.makedirs(os.path.dirname(args.saida) or ".", exist_ok=True)
    with open(args.saida, "w", encoding="utf-8") as fh:
        json.dump(inventario, fh, ensure_ascii=False, indent=1)

    print("\n=== SÍMBOLOS POR CANAL ===")
    print(
        f"{'canal':<24}{'quadros':>8}{'tab':>5}{'tokens':>8}{'simb':>6}"
        f"{'frac':>8}{'hash':>6}"
    )
    for canal, res in por_canal.items():
        print(
            f"{canal[:23]:<24}{res['quadros']:>8}{res['quadros_com_tablatura']:>5}"
            f"{res['tokens']:>8}{res['simbolos']:>6}{res['fracao']:>8.1%}"
            f"{res['hashes_distintos']:>6}"
        )
    glob_res = inventario["resumo"]
    print(
        f"\nTOTAL: {glob_res['simbolos']} símbolos em {glob_res['tokens']} tokens "
        f"({glob_res['fracao']:.1%}) | quadros com tablatura: "
        f"{glob_res['quadros_com_tablatura']}/{glob_res['quadros']}"
    )
    print(f"inventário: {args.saida}")
    if not args.sem_montagem:
        for canal, res in por_canal.items():
            destino = os.path.join(args.dir_simbolos, f"montagem_{slug(canal)}.png")
            montar_montagem(canal, res, args.dir_simbolos, destino, args.max_montagem)
        print(f"montagens: {args.dir_simbolos}/montagem_<canal>.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
