"""Roda os modelos SMT (Sheet Music Transformer) nos recortes de pauta da P1, sem treino.

Para cada recorte, um processo do venv ``/opt/smt`` (Python 3.11, torch CPU, transformers
4.49.0, music21) prepara a imagem como o repositório SMT prepara no treino e na avaliação,
roda ``predict`` e converte o kern gerado em MusicXML. A saída fica em
``data/saida/partitura/p1/omr/smt/<modelo_curto>/crop/<id>/``:

- ``entrada.png``: a imagem que o modelo recebeu de fato (cinza, uint8, já redimensionada);
- ``saida.krn``: o texto kern cru, juntado dos tokens do modelo (sem cabeçalho acrescentado);
- ``saida.musicxml``: o MusicXML convertido por music21 (só se a conversão deu certo);
- ``saida_spines.json``: quantas spines e notas há em cada parte do MusicXML;
- ``stdout.log`` e ``stderr.log``: o que o processo imprimiu.

Ao fim, ``execucao.json`` na pasta ``crop/`` lista, por id, ``ok``, ``motivo``, ``segundos``,
``codigo`` e ``saida`` (relativa à raiz do repositório), no mesmo formato de
``tab.partitura_omr``.

Pré-processamento (entrada do modelo, AGENTS.md regra 9), replicado de ``data.py`` do
repositório SMT. Os pesos de antoniorv6 pedem o código de d25acd4 (2024) e os de
PRAIG pedem o de 20d8240 (master, 2025); medido, ver ``Modelo.fonte``:

- modelos de sistema (``prepare_data``): altura = ``ceil(max(h, 256) * reduce_ratio)``,
  largura = ``ceil(min(w, 3056) * reduce_ratio)``;
- modelos de página (``prepare_fp_data``): altura e largura = ``ceil(dim * reduce_ratio)``,
  sem altura mínima;
- imagem em RGB, redimensionada por ``cv2.resize`` e convertida pelo
  ``convert_img_to_tensor`` do repositório (PIL: escala de cinza, tensor em [0, 1]).

Os modelos de página (``PRAIG/smt-fp-*``) usam o mesmo ``predict`` e a mesma junção de
tokens. Como a entrada não é uma página, o recorte de um sistema faz esse papel. O kern
bekern de página não tem cabeçalho na saída (o treino removeu as quatro primeiras
linhas de tokens), então acrescenta-se ``**kern`` por spine, com o número de spines
lido da primeira linha de tokens. O registro em ``saida_spines.json`` diz isso.

Roda na imagem ``chorinho-partitura:smt``. O processo de orquestração usa o Python da
imagem base, e cada recorte roda em ``/opt/smt/bin/python -m tab.partitura_smt inferir``.
Os caminhos ``/opt/smt*`` ficam aqui porque ``tab/caminhos.py`` descreve o acervo e a
saída, não o ambiente da imagem (o mesmo acontece com ``EXECUTAVEIS`` em
``tab/partitura_omr.py``).

Uso:
    python -m tab.partitura_smt rodar --modelo antoniorv6/smt-grandstaff
    python -m tab.partitura_smt rodar --modelo PRAIG/smt-fp-grandstaff --ids R01,R02
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import PARTITURA_P1, RAIZ

try:  # só o venv /opt/smt tem o music21; a imagem base do gate não tem
    from music21 import converter
except ImportError:
    converter = None

try:  # só o venv /opt/smt tem torch com transformers e o código do SMT
    import torch
    from data_augmentation.data_augmentation import convert_img_to_tensor
    from smt_model import SMTModelForCausalLM
except ImportError:
    torch = None
    convert_img_to_tensor = None
    SMTModelForCausalLM = None

#: Python do venv SMT na imagem ``chorinho-partitura:smt``.
PYTHON_SMT = Path("/opt/smt/bin/python")

#: Clones do repositório SMT, nos dois commits que os pesos pedem (ver ``Modelo.fonte``).
#: ``/opt/smt-src`` é o ``master`` em 20d8240 (código de 2025); ``/opt/smt-src-2024`` é
#: d25acd4 (código de 2024, o que os checkpoints de antoniorv6 de 2024-09 usam).
FONTE_SMT_2025 = Path("/opt/smt-src")
FONTE_SMT_2024 = Path("/opt/smt-src-2024")

#: Pesos do HF baixados no build, uma pasta por modelo (``<modelo_curto>``).
MODELOS_DIR = Path("/opt/smt-modelos")

#: Recortes gerados por ``tab.partitura_recortes``.
PASTA_RECORTES = PARTITURA_P1 / "recortes"

#: Saída das bibliotecas: ``smt/<modelo_curto>/crop/<id>/``.
PASTA_OMR = PARTITURA_P1 / "omr"

#: Os 12 recortes com gabarito de tablatura (R01 a R12).
IDS_REFERENCIA = tuple(f"R{n:02d}" for n in range(1, 13))

#: Segundos de parede para refazer só a conversão (music21, sem o modelo).
TIMEOUT_CONVERSAO = 300

#: Segundos de parede antes de matar o processo de um recorte. Acima disto, o modelo
#: para (ver ``rodar``), conforme a regra da fase.
TIMEOUT_RECORTE = 600

#: Limites do ``prepare_data`` do repositório SMT (modelos de sistema).
ALTURA_MINIMA_SISTEMA = 256
LARGURA_MAXIMA_SISTEMA = 3056


@dataclass(frozen=True)
class Modelo:
    """Um checkpoint SMT público, com o pré-processamento que a configuração pede.

    Attributes:
        id_hf: referência no Hugging Face (``autor/nome``).
        curto: nome da pasta em ``PASTA_OMR`` e em ``MODELOS_DIR``.
        revisao: hash do commit do modelo no HF, fixado no build.
        tipo: ``sistema`` (``prepare_data``) ou ``pagina`` (``prepare_fp_data``).
        reduce_ratio: fator de redução da configuração de treino.
        origem_config: de onde saiu o ``reduce_ratio``.
        bekern: se a saída é bekern e precisa de cabeçalho para o music21.
        fonte: clone do SMT cujo código carrega os pesos sem camada faltando. Medido:
            com o código de 2025 os pesos de antoniorv6 deixam o decoder aleatório
            ("newly initialized"), e com o de 2024 os pesos de PRAIG deixam.
    """

    id_hf: str
    curto: str
    revisao: str
    tipo: str
    reduce_ratio: float
    origem_config: str
    bekern: bool
    fonte: Path


#: Os quatro modelos que têm pesos baixáveis sem login. Os outros três estão fora desta
#: lista e a razão está em ``docs/decisoes/3001-imagem-derivada-partitura.md``.
MODELOS = (
    Modelo(
        id_hf="antoniorv6/smt-grandstaff",
        curto="antoniorv6-smt-grandstaff",
        revisao="2eb5a45c29d63bdf063cd0427175f57675e7da9e",
        tipo="sistema",
        reduce_ratio=1.0,
        origem_config="config/GrandStaff/grandstaff.json (reduce_ratio 1.0)",
        bekern=False,
        fonte=FONTE_SMT_2024,
    ),
    Modelo(
        id_hf="antoniorv6/smt-camera-grandstaff",
        curto="antoniorv6-smt-camera-grandstaff",
        revisao="9c1355631fbddc297d3d10fe4e6e5d3b5d3126b7",
        tipo="sistema",
        reduce_ratio=0.85,
        origem_config="config/Camera_GrandStaff/c_grandstaff.json (reduce_ratio 0.85)",
        bekern=False,
        fonte=FONTE_SMT_2024,
    ),
    Modelo(
        id_hf="PRAIG/smt-grandstaff",
        curto="praig-smt-grandstaff",
        revisao="fd3d512a64aab51ee4048435d44c0455d6cc0abd",
        tipo="sistema",
        reduce_ratio=1.0,
        origem_config="PREMISSA: nenhuma configuração publicada; igual a GrandStaff (1.0)",
        bekern=False,
        fonte=FONTE_SMT_2025,
    ),
    Modelo(
        id_hf="PRAIG/smt-fp-grandstaff",
        curto="praig-smt-fp-grandstaff",
        revisao="6f8d5c093d218a71117ef51492efc2952adcc217",
        tipo="pagina",
        reduce_ratio=1.0,
        origem_config="config/FP-GrandStaff/finetuning.json (reduce_ratio 1.0, bekern)",
        bekern=True,
        fonte=FONTE_SMT_2025,
    ),
)


def modelo_por_id(id_hf: str) -> Modelo:
    """Acha o modelo da lista pelo id do Hugging Face.

    Args:
        id_hf: ``autor/nome`` do modelo.

    Returns:
        O ``Modelo`` correspondente.

    Raises:
        ValueError: se o modelo não está em ``MODELOS``.
    """
    for modelo in MODELOS:
        if modelo.id_hf == id_hf:
            return modelo
    raise ValueError(f"modelo fora da lista: {id_hf}")


def dimensoes_sistema(
    altura: int, largura: int, reduce_ratio: float
) -> tuple[int, int]:
    """Calcula a nova altura e largura de um modelo de sistema (``prepare_data``).

    Args:
        altura: altura do recorte, em px.
        largura: largura do recorte, em px.
        reduce_ratio: fator da configuração de treino.

    Returns:
        ``(altura, largura)`` depois do redimensionamento.
    """
    nova_largura = math.ceil(min(largura, LARGURA_MAXIMA_SISTEMA) * reduce_ratio)
    nova_altura = math.ceil(max(altura, ALTURA_MINIMA_SISTEMA) * reduce_ratio)
    return nova_altura, nova_largura


def dimensoes_pagina(altura: int, largura: int, reduce_ratio: float) -> tuple[int, int]:
    """Calcula a nova altura e largura de um modelo de página (``prepare_fp_data``).

    Args:
        altura: altura do recorte, em px.
        largura: largura do recorte, em px.
        reduce_ratio: fator da configuração de treino.

    Returns:
        ``(altura, largura)`` depois do redimensionamento.
    """
    return math.ceil(altura * reduce_ratio), math.ceil(largura * reduce_ratio)


def redimensionar(caminho: Path, modelo: Modelo) -> np.ndarray:
    """Lê o recorte em RGB e o redimensiona como o treino do modelo fez.

    Args:
        caminho: PNG do recorte.
        modelo: modelo que vai receber a imagem.

    Returns:
        Array RGB uint8 com a forma que o modelo espera.

    Raises:
        ValueError: se a imagem não abre.
    """
    imagem = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if imagem is None:
        raise ValueError(f"imagem ilegível: {caminho}")
    rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
    altura, largura = rgb.shape[:2]
    if modelo.tipo == "sistema":
        nova = dimensoes_sistema(altura, largura, modelo.reduce_ratio)
    else:
        nova = dimensoes_pagina(altura, largura, modelo.reduce_ratio)
    return cv2.resize(rgb, (nova[1], nova[0]))


def juntar_tokens(tokens: list[str]) -> str:
    """Junta os tokens do modelo no texto kern, como o trainer do repositório faz.

    Args:
        tokens: saída de ``SMTModelForCausalLM.predict`` com ``convert_to_str=True``.

    Returns:
        Texto com ``<b>`` virando quebra de linha, ``<s>`` virando espaço e ``<t>``
        virando tab.
    """
    texto = "".join(tokens)
    return texto.replace("<t>", "\t").replace("<b>", "\n").replace("<s>", " ")


def acrescentar_cabecalho(krn: str) -> tuple[str, int]:
    """Acrescenta o cabeçalho ``**kern`` que o treino de página tirou da saída.

    O número de spines é o de tokens da primeira linha do texto (cada linha de
    interpretação tem um token por spine).

    Args:
        krn: texto kern sem cabeçalho.

    Returns:
        ``(texto com cabeçalho, número de spines)``.
    """
    primeira = krn.split("\n", 1)[0]
    spines = primeira.count("\t") + 1
    cabecalho = "\t".join(["**kern"] * spines)
    return f"{cabecalho}\n{krn}", spines


def normalizar_ekern(krn: str) -> tuple[str, bool]:
    """Troca o cabeçalho ``**ekern*`` por ``**kern`` na primeira linha.

    O treino dos modelos de sistema tirou os ``·`` do ekern (``data.prepare_data``
    faz ``gt.replace("·", "")``), então a saída já é kern simples com rótulo ekern.
    O music21 não lê esse rótulo (medido: 0 notas; com ``**kern``, 47 notas no
    mesmo texto). Só o cabeçalho muda; as linhas de dados ficam como estão.

    Args:
        krn: texto kern com cabeçalho na primeira linha.

    Returns:
        ``(texto, trocou)``; ``trocou`` diz se havia rótulo ekern.
    """
    primeira, _, resto = krn.partition("\n")
    tokens = primeira.split("\t")
    if not any(t.startswith("**ekern") for t in tokens):
        return krn, False
    tokens = ["**kern" if t.startswith("**ekern") else t for t in tokens]
    cabecalho = "\t".join(tokens)
    return (f"{cabecalho}\n{resto}" if "\n" in krn else cabecalho), True


def resumo_partes(partitura) -> list[dict]:
    """Conta eventos, notas e compassos de cada parte do music21.

    Args:
        partitura: ``music21.stream.Score`` lido do kern.

    Returns:
        Uma ``dict`` por parte, com ``parte``, ``nome``, ``eventos``, ``notas``
        e ``compassos``. ``notas`` conta cada altura de um acorde.
    """
    partes = []
    for indice, parte in enumerate(partitura.parts, start=1):
        eventos = 0
        notas = 0
        for elemento in parte.recurse().notes:
            eventos += 1
            notas += len(elemento.pitches)
        partes.append(
            {
                "parte": indice,
                "nome": str(parte.id),
                "eventos": eventos,
                "notas": notas,
                "compassos": len(parte.getElementsByClass("Measure")),
            }
        )
    return partes


def krn_para_musicxml(krn: str, destino: Path) -> list[dict]:
    """Converte o kern em MusicXML e devolve o resumo de cada parte.

    Args:
        krn: texto kern com cabeçalho ``**kern`` em cada spine.
        destino: arquivo ``.musicxml`` a escrever.

    Returns:
        O resumo de ``resumo_partes``.

    Raises:
        Exception: qualquer erro do music21 ao ler o kern (kern malformado).
        ValueError: se o music21 leu o kern mas não achou nenhuma nota. Ele devolve
            um ``Score`` vazio em vez de erro, e isso não é um MusicXML útil.
    """
    partitura = converter.parseData(krn, format="humdrum")
    resumo = resumo_partes(partitura)
    if sum(parte["notas"] for parte in resumo) == 0:
        raise ValueError("music21 não leu nenhuma nota")
    partitura.write("musicxml", fp=str(destino))
    return resumo


def inferir(modelo: Modelo, entrada: Path, pasta: Path) -> dict:
    """Roda o modelo em um recorte e grava os arquivos da pasta do id.

    Só funciona dentro do venv ``/opt/smt``, onde torch, transformers e music21 existem.

    Args:
        modelo: modelo a rodar.
        entrada: PNG do recorte.
        pasta: pasta ``crop/<id>/`` de saída (já criada).

    Returns:
        Dict com ``ok`` e ``motivo``.

    Raises:
        RuntimeError: se as dependências do SMT não estão disponíveis.
    """
    if SMTModelForCausalLM is None or converter is None:
        raise RuntimeError("dependências do SMT ausentes: rodar em /opt/smt/bin/python")
    rgb = redimensionar(entrada, modelo)
    tensor = convert_img_to_tensor(rgb)
    cinza = (tensor.squeeze(0).numpy() * 255).round().astype(np.uint8)
    cv2.imwrite(str(pasta / "entrada.png"), cinza)

    modelo_local = SMTModelForCausalLM.from_pretrained(str(MODELOS_DIR / modelo.curto))
    modelo_local.eval()
    with torch.inference_mode():
        tokens, _ = modelo_local.predict(tensor.unsqueeze(0), convert_to_str=True)
    krn = juntar_tokens(tokens)
    (pasta / "saida.krn").write_text(krn, encoding="utf-8")

    return converter_krn(krn, modelo, pasta)


def converter_krn(krn: str, modelo: Modelo, pasta: Path) -> dict:
    """Converte o texto cru do modelo em ``saida.musicxml`` e ``saida_spines.json``.

    Só funciona no venv ``/opt/smt``. Apaga antes as saídas de conversões antigas da
    pasta, para que uma falha não deixe um MusicXML de rodada anterior.

    Args:
        krn: texto cru do modelo (o que está em ``saida.krn``).
        modelo: modelo que gerou o texto (define o cabeçalho de página).
        pasta: pasta ``crop/<id>/`` de saída.

    Returns:
        Dict com ``ok`` e ``motivo``.
    """
    for antigo in ("saida.musicxml", "saida_spines.json"):
        (pasta / antigo).unlink(missing_ok=True)
    cabecalho = None
    if modelo.bekern:
        texto, spines_krn = acrescentar_cabecalho(krn)
        cabecalho = texto.split("\n", 1)[0]
    else:
        texto = krn
        spines_krn = sum(
            1 for token in krn.split("\n", 1)[0].split("\t") if token.startswith("**")
        )
    texto, trocou = normalizar_ekern(texto)
    try:
        resumo = krn_para_musicxml(texto, pasta / "saida.musicxml")
    except Exception as erro:  # music21 não tem tipo de erro único para kern ruim
        return {"ok": False, "motivo": f"kern malformado: {erro}"}
    detalhe = {
        "spines_krn": spines_krn,
        "partes_musicxml": len(resumo),
        "cabecalho_acrescentado": cabecalho,
        "cabecalho_ekern_trocado": trocou,
        "partes": resumo,
        "notas_total": sum(p["notas"] for p in resumo),
    }
    (pasta / "saida_spines.json").write_text(
        json.dumps(detalhe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"ok": True, "motivo": None}


def _matar_grupo(processo: subprocess.Popen) -> None:
    """Mata o processo e os filhos dele.

    Args:
        processo: processo iniciado com ``start_new_session=True``.
    """
    with contextlib.suppress(ProcessLookupError):
        os.killpg(processo.pid, signal.SIGKILL)
    processo.wait()


def _executar(
    cmd: list[str], limite: int, env: dict[str, str]
) -> tuple[int | None, str, str, str | None]:
    """Roda um comando com timeout e devolve código, saídas e motivo de parada.

    Args:
        cmd: linha de comando.
        limite: segundos antes de matar o grupo de processos.
        env: ambiente do processo.

    Returns:
        ``(codigo, stdout, stderr, motivo)``; ``codigo`` é None em timeout.
    """
    processo = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(RAIZ),
        env=env,
        start_new_session=True,
    )
    try:
        out, err = processo.communicate(timeout=limite)
    except subprocess.TimeoutExpired:
        _matar_grupo(processo)
        out, err = processo.communicate()
        return None, out or "", err or "", f"timeout {limite} s"
    return processo.returncode, out or "", err or "", None


def _ler_resultado(stdout: str) -> dict | None:
    """Lê a linha ``RESULTADO {...}`` que o processo de inferência imprime.

    Args:
        stdout: saída padrão do processo.

    Returns:
        O dict da última linha ``RESULTADO``, ou None se não há.
    """
    linhas = [ln for ln in stdout.splitlines() if ln.startswith("RESULTADO ")]
    if not linhas:
        return None
    return json.loads(linhas[-1][len("RESULTADO ") :])


def rodar_recorte(modelo: Modelo, id_: str, pasta_base: Path) -> dict:
    """Roda o modelo em um recorte, em processo próprio, e devolve o registro.

    Args:
        modelo: modelo a rodar.
        id_: id do recorte (``R01``...).
        pasta_base: ``smt/<modelo_curto>/crop`` em ``PASTA_OMR``.

    Returns:
        Dict com ``id``, ``ok``, ``motivo``, ``segundos``, ``codigo`` e ``saida``.
    """
    pasta = pasta_base / id_
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)
    entrada = PASTA_RECORTES / f"{id_}.png"
    cmd = [
        str(PYTHON_SMT),
        "-m",
        "tab.partitura_smt",
        "inferir",
        "--modelo",
        modelo.id_hf,
        "--entrada",
        str(entrada),
        "--pasta",
        str(pasta),
    ]
    env = {**os.environ, "PYTHONPATH": f"{RAIZ}{os.pathsep}{modelo.fonte}"}
    inicio = time.perf_counter()
    codigo, out, err, parada = _executar(cmd, TIMEOUT_RECORTE, env)
    segundos = time.perf_counter() - inicio
    (pasta / "stdout.log").write_text(out, encoding="utf-8")
    (pasta / "stderr.log").write_text(err, encoding="utf-8")

    return _registro(id_, pasta, codigo, out, parada, segundos)


def _registro(
    id_: str,
    pasta: Path,
    codigo: int | None,
    out: str,
    parada: str | None,
    segundos: float,
) -> dict:
    """Monta o registro de um recorte a partir do que o processo deixou.

    Args:
        id_: id do recorte.
        pasta: ``crop/<id>/``.
        codigo: código de saída do processo (None se parou por timeout).
        out: saída padrão do processo.
        parada: motivo de parada forçada (timeout), ou None.
        segundos: tempo gasto no processo.

    Returns:
        Dict com ``id``, ``ok``, ``motivo``, ``segundos``, ``codigo`` e ``saida``.
    """
    resultado = _ler_resultado(out)
    if parada is not None:
        ok, motivo = False, parada
    elif resultado is None:
        ok, motivo = False, f"exit {codigo} sem RESULTADO"
    else:
        ok, motivo = resultado["ok"], resultado["motivo"]
    saida = pasta / "saida.musicxml"
    if ok and not saida.exists():
        ok, motivo = False, "MusicXML não foi gravado"
    return {
        "id": id_,
        "ok": ok,
        "motivo": motivo,
        "segundos": round(segundos, 2),
        "codigo": codigo,
        "saida": str(saida.relative_to(RAIZ)) if ok else None,
    }


def reconverter_recorte(modelo: Modelo, id_: str, pasta_base: Path) -> dict | None:
    """Refaz só a conversão de um recorte, a partir do ``saida.krn`` já gravado.

    O modelo não roda de novo. O tempo de inferência do registro anterior é mantido e
    somado ao da conversão.

    Args:
        modelo: modelo que gerou o ``saida.krn``.
        id_: id do recorte.
        pasta_base: ``smt/<modelo_curto>/crop`` em ``PASTA_OMR``.

    Returns:
        O registro novo, ou None se não há ``saida.krn`` (a inferência não terminou).
    """
    pasta = pasta_base / id_
    if not (pasta / "saida.krn").exists():
        return None
    anterior = {r["id"]: r for r in _ler_execucao(pasta_base)}.get(id_, {})
    cmd = [
        str(PYTHON_SMT),
        "-m",
        "tab.partitura_smt",
        "converter",
        "--modelo",
        modelo.id_hf,
        "--pasta",
        str(pasta),
    ]
    env = {**os.environ, "PYTHONPATH": f"{RAIZ}{os.pathsep}{modelo.fonte}"}
    inicio = time.perf_counter()
    codigo, out, err, parada = _executar(cmd, TIMEOUT_CONVERSAO, env)
    segundos = time.perf_counter() - inicio
    (pasta / "conversao.log").write_text(out + err, encoding="utf-8")
    total = float(anterior.get("segundos") or 0.0) + segundos
    return _registro(id_, pasta, codigo, out, parada, total)


def _ler_execucao(pasta_base: Path) -> list[dict]:
    """Lê ``execucao.json`` da pasta, ou devolve lista vazia.

    Args:
        pasta_base: ``smt/<modelo_curto>/crop`` em ``PASTA_OMR``.

    Returns:
        Os registros gravados, ou ``[]``.
    """
    caminho = pasta_base / "execucao.json"
    if not caminho.exists():
        return []
    return json.loads(caminho.read_text(encoding="utf-8"))


def gravar_execucao(pasta_base: Path, registros: list[dict]) -> None:
    """Grava ``execucao.json``, mantendo os ids que não foram rodados agora.

    Args:
        pasta_base: ``smt/<modelo_curto>/crop`` em ``PASTA_OMR``.
        registros: registros recém-produzidos (substituem os de mesmo id).
    """
    caminho = pasta_base / "execucao.json"
    antigos = {}
    if caminho.exists():
        antigos = {r["id"]: r for r in json.loads(caminho.read_text(encoding="utf-8"))}
    for registro in registros:
        antigos[registro["id"]] = registro
    ordem = sorted(antigos.values(), key=lambda r: r["id"])
    caminho.write_text(
        json.dumps(ordem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def rodar(modelo: Modelo, ids: list[str]) -> list[dict]:
    """Roda um modelo em uma lista de recortes, parando se um recorte estoura o timeout.

    Args:
        modelo: modelo a rodar.
        ids: ids dos recortes, na ordem de execução.

    Returns:
        Os registros dos recortes que foram rodados.

    Raises:
        ValueError: se algum id não tem recorte em ``PASTA_RECORTES``.
    """
    faltam = [i for i in ids if not (PASTA_RECORTES / f"{i}.png").exists()]
    if faltam:
        raise ValueError(f"recortes ausentes: {faltam}")
    pasta_base = PASTA_OMR / "smt" / modelo.curto / "crop"
    pasta_base.mkdir(parents=True, exist_ok=True)
    registros = []
    for id_ in ids:
        registro = rodar_recorte(modelo, id_, pasta_base)
        registros.append(registro)
        print(
            f"{modelo.curto} {id_}: {'ok' if registro['ok'] else 'FALHA'} "
            f"{registro['segundos']} s"
            f"{'' if registro['motivo'] is None else ' (' + registro['motivo'] + ')'}",
            flush=True,
        )
        if registro["motivo"] and registro["motivo"].startswith("timeout"):
            print(
                f"{modelo.curto}: parado em {id_} por timeout; os demais não foram rodados",
                flush=True,
            )
            break
    gravar_execucao(pasta_base, registros)
    return registros


def reconverter(modelo: Modelo, ids: list[str]) -> list[dict]:
    """Refaz a conversão de cada recorte que tem ``saida.krn`` e atualiza ``execucao.json``.

    Args:
        modelo: modelo que gerou as saídas.
        ids: ids dos recortes; os que não têm ``saida.krn`` são pulados.

    Returns:
        Os registros refeitos.
    """
    pasta_base = PASTA_OMR / "smt" / modelo.curto / "crop"
    registros = []
    for id_ in ids:
        registro = reconverter_recorte(modelo, id_, pasta_base)
        if registro is None:
            print(f"{modelo.curto} {id_}: sem saida.krn, pulado", flush=True)
            continue
        registros.append(registro)
        print(
            f"{modelo.curto} {id_}: {'ok' if registro['ok'] else 'FALHA'} "
            f"{registro['segundos']} s"
            f"{'' if registro['motivo'] is None else ' (' + registro['motivo'] + ')'}",
            flush=True,
        )
    gravar_execucao(pasta_base, registros)
    return registros


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI.

    Args:
        argv: argumentos (None = ``sys.argv``).

    Returns:
        0 se todos os recortes rodados geraram MusicXML, 1 caso contrário.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    ids_modelos = [m.id_hf for m in MODELOS]

    rod = sub.add_parser("rodar", help="roda um modelo nos recortes de referência")
    rod.add_argument("--modelo", choices=ids_modelos, required=True)
    rod.add_argument("--ids", default=None, help="ex.: R01,R08 (padrão: R01 a R12)")

    inf = sub.add_parser("inferir", help="uso interno: um recorte, no venv /opt/smt")
    inf.add_argument("--modelo", choices=ids_modelos, required=True)
    inf.add_argument("--entrada", type=Path, required=True)
    inf.add_argument("--pasta", type=Path, required=True)

    conv = sub.add_parser("converter", help="uso interno: converte um saida.krn")
    conv.add_argument("--modelo", choices=ids_modelos, required=True)
    conv.add_argument("--pasta", type=Path, required=True)

    refaz = sub.add_parser("reconverter", help="refaz a conversão sem rodar o modelo")
    refaz.add_argument("--modelo", choices=ids_modelos, required=True)
    refaz.add_argument("--ids", default=None, help="ex.: R01,R08 (padrão: R01 a R12)")

    args = parser.parse_args(argv)
    if args.comando == "converter":
        modelo = modelo_por_id(args.modelo)
        krn = (args.pasta / "saida.krn").read_text(encoding="utf-8")
        try:
            resultado = converter_krn(krn, modelo, args.pasta)
        except Exception as erro:  # o motivo vai para execucao.json, não some
            resultado = {"ok": False, "motivo": f"conversão falhou: {erro}"}
        print("RESULTADO " + json.dumps(resultado, ensure_ascii=False), flush=True)
        return 0 if resultado["ok"] else 1
    if args.comando == "reconverter":
        modelo = modelo_por_id(args.modelo)
        ids = args.ids.split(",") if args.ids else list(IDS_REFERENCIA)
        registros = reconverter(modelo, ids)
        falhas = [r for r in registros if not r["ok"]]
        print(
            f"{modelo.curto}: {len(registros) - len(falhas)}/{len(registros)} "
            "com MusicXML (refeitos)",
            file=sys.stderr,
        )
        return 0 if not falhas else 1
    if args.comando == "inferir":
        modelo = modelo_por_id(args.modelo)
        try:
            resultado = inferir(modelo, args.entrada, args.pasta)
        except Exception as erro:  # o motivo vai para execucao.json, não some
            resultado = {"ok": False, "motivo": f"inferência falhou: {erro}"}
        print("RESULTADO " + json.dumps(resultado, ensure_ascii=False), flush=True)
        return 0 if resultado["ok"] else 1

    modelo = modelo_por_id(args.modelo)
    ids = args.ids.split(",") if args.ids else list(IDS_REFERENCIA)
    registros = rodar(modelo, ids)
    falhas = [r for r in registros if not r["ok"]]
    print(
        f"{modelo.curto}: {len(registros) - len(falhas)}/{len(registros)} com MusicXML",
        file=sys.stderr,
    )
    return 0 if not falhas else 1


if __name__ == "__main__":
    raise SystemExit(main())
