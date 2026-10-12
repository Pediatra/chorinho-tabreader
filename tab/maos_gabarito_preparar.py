"""Passo ``preparar`` da ferramenta dos dedos (M2): material por nota, na GPU.

Para cada nota da amostra (``tab.maos_gabarito.amostrar_notas``), extrai do vídeo o
quadro em ``t_ini``, acha as mãos com o ``DetectorMaos`` (Wholebody + MediaPipe) e grava
em ``<saida>/<id>/``:

- ``quadro.jpg``: o quadro reduzido a 960 px, com um retângulo vermelho SÓ em volta do
  algarismo da nota (na linha da sua corda), e o acorde da coluna no cabeçalho;
- ``esq.jpg``: a mão esquerda em t_ini, ampliada 40% para cada lado;
- ``dir_m.jpg``, ``dir_0.jpg``, ``dir_p.jpg``: a mão direita em t_ini - 0,15 s, t_ini e
  t_ini + 0,15 s, com a MESMA caixa (a de t_ini), para comparar o movimento;
- ``material.json``: a amostra, as caixas (no quadro), a origem e os scores, a altura da
  linha da corda (``y_corda``) e de onde ela veio (``segmentacao`` ou ``reserva``).

Grava também ``<saida>/indice.json`` (a lista que a página lê) e cria ou ATUALIZA o
gabarito (``--gabarito``) sem apagar as respostas que já existem.

Só roda com GPU (``DetectorMaos("cuda")``). Importa ``tab.maos_detector``, que exige
rtmlib; por isso NÃO está no gate. Uso::

    python -m tab.maos_gabarito_preparar --video /acervo/.../video.mp4
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .caminhos import CENSO_MAOS, GABARITO_DEDOS, MAOS_DEDOS, MVP, acervo
from .maos_detector import DetectorMaos
from .maos_gabarito import (
    ALTURA_DIREITA_PX,
    ALTURA_ESQUERDA_PX,
    DESLOCAMENTOS_DIREITA_S,
    LARGURA_QUADRO_PX,
    SEMENTE_PADRAO,
    acorde_da_coluna,
    amostrar_notas,
    caixa_da_nota,
    caixa_final,
    escolher_caixa,
    gabarito_novo,
    gravar_atomico,
    mesclar_gabarito,
    perguntas,
    recortar_caixa,
    redimensionar_altura,
    texto_acorde,
    y_da_corda,
)
from .tabseg import segmentar

#: Qualidade do JPEG das imagens geradas.
QUALIDADE_JPG = 92

#: Forma (altura, largura) do quadro em que o ``mvp.json`` mede os painéis.
FORMA_QUADRO = (1080, 1920)

#: Fonte do cabeçalho do quadro.
FONTE = cv2.FONT_HERSHEY_SIMPLEX


def _log(msg: str) -> None:
    """Progresso no stderr (o stdout fica para o resumo final).

    Args:
        msg: texto da linha.
    """
    print(msg, file=sys.stderr, flush=True)


def extrair_quadro(video: Path, t: float) -> np.ndarray:
    """Quadro do vídeo no instante ``t``, em BGR, pelo ffmpeg.

    O ffmpeg é obrigatório: 44% do acervo é AV1, que o OpenCV não decodifica.

    Args:
        video: caminho do vídeo.
        t: instante, em segundos.

    Returns:
        O quadro BGR (altura x largura x 3).

    Raises:
        RuntimeError: se o ffmpeg não devolveu uma imagem.
    """
    proc = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{max(0.0, t):.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        erro = proc.stderr.decode(errors="replace")[:300]
        raise RuntimeError(f"ffmpeg falhou em t={t:.3f}: {erro}")
    quadro = cv2.imdecode(np.frombuffer(proc.stdout, np.uint8), cv2.IMREAD_COLOR)
    if quadro is None:
        raise RuntimeError(f"ffmpeg não gerou imagem em t={t:.3f}")
    return quadro


def registro_do_censo(censo: Path, chave: str) -> dict:
    """Registro do censo de presença de um vídeo (pela chave do acervo).

    Args:
        censo: ``censo_maos.jsonl``.
        chave: caminho do vídeo relativo ao acervo (campo ``arquivo``).

    Returns:
        O registro, com ``quadros`` (``t``, ``tab``, ``rect``, ``maos``...).

    Raises:
        SystemExit: se o vídeo não está no censo.
    """
    for linha in censo.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        registro = json.loads(linha)
        if registro["arquivo"] == chave:
            return registro
    raise SystemExit(f"vídeo {chave!r} não está no censo {censo}")


def tab_do_censo(
    quadros: list[dict], t: float
) -> tuple[list[int] | None, float | None]:
    """Caixa da tablatura no quadro de censo mais próximo no tempo que a tem.

    Args:
        quadros: quadros do censo do vídeo (``t`` e ``rect``, que pode ser ``None``).
        t: instante da nota, em segundos.

    Returns:
        ``(caixa, t_do_quadro)``, ou ``(None, None)`` se nenhum quadro tem tablatura.
    """
    com_tab = [q for q in quadros if q.get("rect")]
    if not com_tab:
        return None, None
    q = min(com_tab, key=lambda x: abs(x["t"] - t))
    return [int(v) for v in q["rect"]], float(q["t"])


def linhas_da_tela(quadro: np.ndarray, painel: list[int]) -> list[float] | None:
    """Y, no quadro, das linhas de corda achadas pelo ``segmentar`` dentro do painel.

    Args:
        quadro: quadro inteiro, em BGR.
        painel: ``[x0, y0, x1, y1]`` do painel, no quadro 1920x1080.

    Returns:
        As linhas no quadro (ainda não validadas), ou ``None`` se a segmentação não
        devolveu nenhuma. Quem decide se valem é ``linhas_confiaveis``.
    """
    x0, y0, x1, y1 = painel
    grade = segmentar(quadro[y0:y1, x0:x1])
    if not grade.linhas_y:
        return None
    return [float(y0 + ly) for ly in grade.linhas_y]


def desenhar_quadro(
    quadro: np.ndarray,
    item: dict,
    rect_tab: list[int] | None,
    caixa: tuple[int, int, int, int],
    linha_acorde: str,
) -> np.ndarray:
    """Quadro reduzido: a caixa da nota (vermelha), a tablatura (amarela) e o cabeçalho.

    Args:
        quadro: quadro inteiro, em BGR (1920x1080).
        item: nota da amostra (``id``, ``corda``, ``casa``, ``t_ini``).
        rect_tab: caixa da tablatura no quadro, ou ``None``.
        caixa: retângulo da nota no quadro (``caixa_da_nota``).
        linha_acorde: texto do acorde (``texto_acorde``), para o cabeçalho.

    Returns:
        Imagem BGR de ``LARGURA_QUADRO_PX`` de largura.
    """
    escala = LARGURA_QUADRO_PX / quadro.shape[1]
    img = cv2.resize(quadro, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    if rect_tab:
        x0, y0, x1, y1 = (round(v * escala) for v in rect_tab)
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 255), 1)
    bx0, by0, bx1, by1 = (round(v * escala) for v in caixa)
    cv2.rectangle(img, (bx0, by0), (bx1, by1), (0, 0, 255), 2)
    cv2.rectangle(img, (0, 0), (img.shape[1], 40), (0, 0, 0), -1)
    texto = (
        f"{item['id']}  corda {item['corda']} casa {item['casa']} t={item['t_ini']:.2f}"
    )
    cv2.putText(img, texto, (6, 16), FONTE, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(img, linha_acorde, (6, 33), FONTE, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def _avisos(escolhas: dict[str, dict]) -> list[str]:
    """Avisos para a página: mão sem detecção (fallback) e origem fraca.

    Args:
        escolhas: ``{lado: escolha}`` de ``escolher_caixa``.

    Returns:
        Uma frase por lado com caixa de fallback (lista vazia se não há).
    """
    nomes = {"esquerda": "mão esquerda", "direita": "mão direita"}
    return [
        f"{nomes[lado]}: sem mão detectada; o recorte é a metade inferior do quadro"
        for lado, e in escolhas.items()
        if e["origem"] == "fallback"
    ]


def preparar_nota(
    det: DetectorMaos,
    video: Path,
    item: dict,
    quadros_censo: list[dict],
    pasta: Path,
    notas_mvp: list[dict],
    telas: dict[int, dict],
) -> dict:
    """Material de uma nota: os 5 JPGs em ``pasta`` e o ``material.json``.

    Args:
        det: detector das mãos (GPU).
        video: caminho do vídeo.
        item: nota da amostra (``id``, ``t_ini``, ``corda``, ``casa``...).
        quadros_censo: quadros do censo deste vídeo.
        pasta: pasta da nota (criada se faltar).
        notas_mvp: todas as notas do ``mvp.json`` (para o acorde).
        telas: ``{id da tela: tela}`` do ``mvp.json`` (painel e passo).

    Returns:
        A entrada desta nota no ``indice.json`` (ids, caixas, origens e textos).

    Raises:
        ValueError: se o quadro não tem a forma 1920x1080 em que o mvp mede.
    """
    t = float(item["t_ini"])
    pasta.mkdir(parents=True, exist_ok=True)
    quadro = extrair_quadro(video, t)
    if quadro.shape[:2] != FORMA_QUADRO:
        raise ValueError(f"quadro {quadro.shape[:2]} não é {FORMA_QUADRO} (t={t:.3f})")
    forma = quadro.shape
    rect_tab, t_censo = tab_do_censo(quadros_censo, t)

    tela = telas[int(item["tela"])]
    painel, passo = [int(v) for v in tela["painel"]], float(tela["passo"])
    linhas = linhas_da_tela(quadro, painel)
    y_corda, origem_y = y_da_corda(int(item["corda"]), linhas, painel, passo)
    caixa_nota = caixa_da_nota(float(item["x_centro_quadro"]), y_corda, passo)

    indice_mvp = item["indice_mvp"]
    acorde = acorde_da_coluna(notas_mvp, indice_mvp)
    linha_acorde = texto_acorde(acorde, indice_mvp)
    pergunta_esq, pergunta_dir = perguntas(item["corda"], item["casa"])

    achado = det.detectar(quadro, rect_tab)
    escolhas = {
        lado: escolher_caixa(lado, achado["maos_mp"], achado["pessoas_wb"], forma)
        for lado in ("esquerda", "direita")
    }
    caixas = {lado: caixa_final(escolhas[lado], forma) for lado in escolhas}

    cv2.imwrite(
        str(pasta / "quadro.jpg"),
        desenhar_quadro(quadro, item, rect_tab, caixa_nota, linha_acorde),
        [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPG],
    )
    cv2.imwrite(
        str(pasta / "esq.jpg"),
        redimensionar_altura(
            recortar_caixa(quadro, caixas["esquerda"]), ALTURA_ESQUERDA_PX
        ),
        [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPG],
    )
    instantes = [t + d for d in DESLOCAMENTOS_DIREITA_S]
    for nome, instante in zip(("dir_m", "dir_0", "dir_p"), instantes, strict=True):
        img = quadro if instante == t else extrair_quadro(video, instante)
        recorte = recortar_caixa(img, caixas["direita"])
        cv2.imwrite(
            str(pasta / f"{nome}.jpg"),
            redimensionar_altura(recorte, ALTURA_DIREITA_PX),
            [cv2.IMWRITE_JPEG_QUALITY, QUALIDADE_JPG],
        )

    avisos = _avisos(escolhas)
    if origem_y == "reserva":
        avisos.append(
            f"corda {item['corda']}: linhas não detectadas; altura estimada pelo painel"
        )
    material = {
        "id": item["id"],
        "indice_mvp": indice_mvp,
        "corda": item["corda"],
        "casa": item["casa"],
        "t_ini": t,
        "tela": item.get("tela"),
        "coluna": item.get("coluna"),
        "x_centro_quadro": item.get("x_centro_quadro"),
        "painel": painel,
        "passo_mvp": passo,
        "linhas_y_segmentadas": linhas,
        "y_corda": round(y_corda, 2),
        "y_corda_origem": origem_y,
        "caixa_nota": list(caixa_nota),
        "acorde": acorde,
        "texto_acorde": linha_acorde,
        "pergunta_esquerda": pergunta_esq,
        "pergunta_direita": pergunta_dir,
        "instantes_direita": [round(v, 3) for v in instantes],
        "rect_tab": rect_tab,
        "t_quadro_censo_tab": t_censo,
        "caixas": {
            lado: {
                "caixa": list(caixas[lado]),
                "origem": escolhas[lado]["origem"],
                "score": escolhas[lado]["score"],
            }
            for lado in caixas
        },
        "maos_mediapipe": [
            {
                "lado": m["lado"],
                "score": float(m["score"]),
                "caixa": [float(v) for v in m["caixa"]],
                "na_tab": bool(m.get("na_tab")),
            }
            for m in achado["maos_mp"]
        ],
        "pessoas_wholebody": len(achado["pessoas_wb"]),
        "afirma": achado["afirma"],
    }
    (pasta / "material.json").write_text(
        json.dumps(material, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return {
        "id": item["id"],
        "pasta": item["id"],
        "corda": item["corda"],
        "casa": item["casa"],
        "t_ini": t,
        "tela": item.get("tela"),
        "rect_tab": rect_tab,
        "origem": {lado: escolhas[lado]["origem"] for lado in escolhas},
        "y_corda_origem": origem_y,
        "texto_acorde": linha_acorde,
        "pergunta_esquerda": pergunta_esq,
        "pergunta_direita": pergunta_dir,
        "avisos": avisos,
    }


def preparar(
    video: Path,
    saida: Path,
    gabarito: Path,
    mvp: Path,
    censo: Path,
    semente: int,
) -> dict:
    """Prepara a amostra inteira: material por nota, ``indice.json`` e o gabarito.

    Args:
        video: caminho do vídeo (dentro do acervo).
        saida: pasta de saída (``<id>/`` por nota e ``indice.json``).
        gabarito: arquivo do gabarito; criado se faltar, mesclado (sem perder resposta)
            se já existe.
        mvp: ``mvp.json`` do produto.
        censo: ``censo_maos.jsonl``.
        semente: semente da amostra.

    Returns:
        Resumo: contagem de origens de caixa por lado, de origens da linha da corda
        (``segmentacao`` ou ``reserva``) e os ids com aviso.

    Raises:
        SystemExit: se o vídeo não está no acervo, no censo ou no mvp.
    """
    inicio = time.time()
    try:
        chave = video.relative_to(acervo()).as_posix()
    except ValueError as erro:
        raise SystemExit(f"{video} não está dentro de {acervo()}") from erro
    produto = json.loads(mvp.read_text(encoding="utf-8"))
    if produto["video"]["arquivo"] != chave:
        raise SystemExit("o mvp.json é de outro vídeo")
    notas = produto["notas"]
    telas = {int(t["id"]): t for t in produto["telas"]}
    amostra = amostrar_notas(notas, semente)
    quadros = registro_do_censo(censo, chave)["quadros"]
    saida.mkdir(parents=True, exist_ok=True)

    det = DetectorMaos("cuda")
    indice = []
    for k, item in enumerate(amostra, start=1):
        indice.append(
            preparar_nota(det, video, item, quadros, saida / item["id"], notas, telas)
        )
        _log(
            f"{k:02d}/{len(amostra)} {item['id']} t={item['t_ini']:.2f} "
            f"{indice[-1]['origem']} y={indice[-1]['y_corda_origem']} "
            f"({time.time() - inicio:.0f}s)"
        )

    documento = {
        "video": chave,
        "semente": semente,
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "notas": indice,
    }
    gravar_atomico(saida / "indice.json", documento)

    existente = (
        json.loads(gabarito.read_text(encoding="utf-8")) if gabarito.exists() else None
    )
    novo = gabarito_novo(chave, amostra, semente)
    gravar_atomico(gabarito, mesclar_gabarito(novo, existente))

    resumo = {"notas": len(indice), "origens": {}, "com_aviso": []}
    for lado in ("esquerda", "direita"):
        contagem: dict[str, int] = {}
        for nota in indice:
            origem = nota["origem"][lado]
            contagem[origem] = contagem.get(origem, 0) + 1
        resumo["origens"][lado] = contagem
    contagem_y: dict[str, int] = {}
    for nota in indice:
        origem = nota["y_corda_origem"]
        contagem_y[origem] = contagem_y.get(origem, 0) + 1
    resumo["y_corda"] = contagem_y
    resumo["com_aviso"] = [n["id"] for n in indice if n["avisos"]]
    return resumo


def main() -> int:
    """CLI do ``preparar``: gera o material e cria ou atualiza o gabarito.

    Returns:
        Código de saída do processo.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--video",
        type=Path,
        default=acervo() / "sky guitar" / "retrato brasileiro - tab & lesson.mp4",
    )
    ap.add_argument("--saida", type=Path, default=MAOS_DEDOS)
    ap.add_argument("--gabarito", type=Path, default=GABARITO_DEDOS)
    ap.add_argument("--mvp", type=Path, default=MVP)
    ap.add_argument("--censo", type=Path, default=CENSO_MAOS)
    ap.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    args = ap.parse_args()
    resumo = preparar(
        args.video, args.saida, args.gabarito, args.mvp, args.censo, args.semente
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
