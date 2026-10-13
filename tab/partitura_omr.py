"""Roda as bibliotecas de OMR (homr, audiveris, oemer) nos recortes de pauta da P1.

Para cada recorte, prepara a entrada na condição pedida, roda a biblioteca com timeout e
guarda o que saiu em ``data/saida/partitura/p1/omr/<biblioteca>/<condicao>/<id>/``:

- ``entrada.png``: a imagem que a biblioteca recebeu;
- ``saida.musicxml``: o MusicXML gerado (no Audiveris, descompactado do ``.mxl``);
- ``stdout.log`` e ``stderr.log``: o que a biblioteca imprimiu.

Ao fim, ``execucao.json`` na pasta da condição lista, por id, se houve saída, o motivo de
falha, o tempo de parede e o caminho da saída. Rodar com ``--ids`` atualiza só esses ids.

Condições:
    ``nativo``: o PNG do recorte, copiado sem alteração;
    ``x2``: o PNG ampliado 2x com ``cv2.resize(..., fx=2, fy=2, INTER_CUBIC)``, e mais nada.

Roda DENTRO da imagem ``chorinho-partitura:dev``, com o ``python`` da base e
``subprocess`` chamando os executáveis dos venvs e do Audiveris.

Uso:
    python -m tab.partitura_omr rodar --biblioteca homr --condicao nativo
    python -m tab.partitura_omr rodar --biblioteca audiveris --condicao x2 --ids R01,R08
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import cv2

from tab.caminhos import RAIZ, SAIDA

#: Recortes e índice gerados por ``tab.partitura_recortes``.
PASTA_RECORTES = SAIDA / "partitura" / "p1" / "recortes"

#: Saída das bibliotecas: ``<biblioteca>/<condicao>/<id>/``.
PASTA_OMR = SAIDA / "partitura" / "p1" / "omr"

BIBLIOTECAS = ("homr", "audiveris", "oemer")
CONDICOES = ("nativo", "x2")

#: Segundos de parede antes de matar a biblioteca, por biblioteca.
TIMEOUTS = {"homr": 300, "audiveris": 300, "oemer": 900}

#: Executáveis dentro da imagem de partitura (ver ``Dockerfile.partitura``).
EXECUTAVEIS = {
    "homr": "/opt/omr/bin/homr",
    "oemer": "/opt/omr/bin/oemer",
    "audiveris": "/opt/audiveris/bin/Audiveris",
}

#: Nome do MusicXML dentro da pasta de cada id.
NOME_SAIDA = "saida.musicxml"


def carregar_indice() -> list[dict]:
    """Lê o ``indice.json`` dos recortes.

    Returns:
        Uma ``dict`` por recorte, na ordem do arquivo.
    """
    caminho = PASTA_RECORTES / "indice.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


def preparar_entrada(origem: Path, condicao: str, destino: Path) -> Path:
    """Escreve a entrada da biblioteca na condição pedida.

    Args:
        origem: PNG do recorte em resolução nativa.
        condicao: ``nativo`` (cópia) ou ``x2`` (ampliação 2x, cúbica).
        destino: arquivo PNG a escrever.

    Returns:
        O próprio ``destino``.

    Raises:
        ValueError: se a condição não existe ou a imagem não abre.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    if condicao == "nativo":
        shutil.copyfile(origem, destino)
        return destino
    if condicao != "x2":
        raise ValueError(f"condição desconhecida: {condicao}")
    imagem = cv2.imread(str(origem), cv2.IMREAD_UNCHANGED)
    if imagem is None:
        raise ValueError(f"imagem ilegível: {origem}")
    ampliada = cv2.resize(imagem, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    if not cv2.imwrite(str(destino), ampliada):
        raise ValueError(f"não consegui gravar: {destino}")
    return destino


def comando(biblioteca: str, entrada: Path, pasta: Path) -> list[str]:
    """Monta a linha de comando da biblioteca para uma entrada.

    Args:
        biblioteca: ``homr``, ``audiveris`` ou ``oemer``.
        entrada: PNG de entrada, já dentro de ``pasta``.
        pasta: pasta de saída do id.

    Returns:
        Lista de argumentos para ``subprocess``.
    """
    executavel = EXECUTAVEIS[biblioteca]
    if biblioteca == "homr":
        return [executavel, str(entrada)]
    if biblioteca == "oemer":
        return [executavel, "-o", str(pasta), str(entrada)]
    return [
        executavel,
        "-batch",
        "-export",
        "-output",
        str(pasta),
        str(entrada),
    ]


def _extrair_mxl(mxl: Path, destino: Path) -> None:
    """Extrai o MusicXML de dentro de um ``.mxl`` (ZIP com ``container.xml``).

    Args:
        mxl: arquivo ``.mxl`` gerado pelo Audiveris.
        destino: arquivo ``.musicxml`` a escrever.

    Raises:
        ValueError: se o ZIP não traz o ``rootfile`` esperado.
    """
    with zipfile.ZipFile(mxl) as zip_:
        nomes = zip_.namelist()
        if "META-INF/container.xml" in nomes:
            raiz = ET.fromstring(zip_.read("META-INF/container.xml"))
            alvo = None
            for elemento in raiz.iter():
                if elemento.tag.endswith("rootfile") and elemento.get("full-path"):
                    alvo = elemento.get("full-path")
                    break
            if alvo is None:
                raise ValueError(f"container.xml sem rootfile em {mxl.name}")
        else:
            xmls = [n for n in nomes if n.endswith((".xml", ".musicxml"))]
            if not xmls:
                raise ValueError(f"sem MusicXML dentro de {mxl.name}")
            alvo = xmls[0]
        destino.write_bytes(zip_.read(alvo))


def localizar_saida(biblioteca: str, entrada: Path, pasta: Path) -> Path | None:
    """Acha o MusicXML que a biblioteca gravou na pasta do id.

    Para o Audiveris, descompacta o ``.mxl`` em ``saida.musicxml`` e mantém o ``.mxl``.

    Args:
        biblioteca: nome da biblioteca.
        entrada: PNG de entrada.
        pasta: pasta de saída do id.

    Returns:
        Caminho de ``saida.musicxml``, ou None se a biblioteca não gravou saída.
    """
    destino = pasta / NOME_SAIDA
    if biblioteca == "homr":
        origem = entrada.with_suffix(".musicxml")
        candidatos = [origem] if origem.exists() else []
    elif biblioteca == "oemer":
        candidatos = sorted(pasta.glob("*.musicxml"))
    else:
        mxls = sorted(pasta.glob("**/*.mxl"))
        if mxls:
            _extrair_mxl(mxls[0], destino)
            return destino
        candidatos = sorted(pasta.glob("**/*.musicxml"))
    if not candidatos:
        return None
    shutil.copyfile(candidatos[0], destino)
    return destino


def _matar_grupo(processo: subprocess.Popen) -> None:
    """Mata o processo e os filhos dele (o Audiveris é um script que chama o java).

    Args:
        processo: processo iniciado com ``start_new_session=True``.
    """
    with contextlib.suppress(ProcessLookupError):
        os.killpg(processo.pid, signal.SIGKILL)
    processo.wait()


def _executar(
    cmd: list[str], limite: int, pasta: Path
) -> tuple[int | None, str, str, str | None]:
    """Roda a biblioteca com timeout e devolve código, stdout, stderr e motivo.

    Args:
        cmd: linha de comando.
        limite: segundos antes de matar o grupo de processos.
        pasta: pasta de trabalho (onde ficam os logs do id).

    Returns:
        ``(codigo, stdout, stderr, motivo)``; ``codigo`` é None se houve timeout ou
        o executável não existe, e ``motivo`` descreve esses casos.
    """
    try:
        processo = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(pasta),
            start_new_session=True,
        )
    except FileNotFoundError:
        return None, "", "", f"executável ausente: {cmd[0]}"
    try:
        out, err = processo.communicate(timeout=limite)
    except subprocess.TimeoutExpired:
        _matar_grupo(processo)
        out, err = processo.communicate()
        return None, out or "", err or "", f"timeout {limite} s"
    return processo.returncode, out or "", err or "", None


def rodar_um(biblioteca: str, condicao: str, item: dict, pasta_base: Path) -> dict:
    """Roda uma biblioteca em um recorte e devolve o registro de execução.

    Args:
        biblioteca: ``homr``, ``audiveris`` ou ``oemer``.
        condicao: ``nativo`` ou ``x2``.
        item: entrada do ``indice.json`` (com ``id``).
        pasta_base: ``<biblioteca>/<condicao>`` em ``PASTA_OMR``.

    Returns:
        Dict com ``id``, ``ok``, ``motivo``, ``segundos``, ``codigo`` e ``saida``
        (caminho relativo à raiz, ou None).
    """
    id_ = item["id"]
    pasta = pasta_base / id_
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)
    entrada = preparar_entrada(
        PASTA_RECORTES / f"{id_}.png", condicao, pasta / "entrada.png"
    )
    cmd = comando(biblioteca, entrada, pasta)
    inicio = time.perf_counter()
    codigo, out, err, motivo_proc = _executar(cmd, TIMEOUTS[biblioteca], pasta)
    segundos = time.perf_counter() - inicio
    (pasta / "stdout.log").write_text(out, encoding="utf-8")
    (pasta / "stderr.log").write_text(err, encoding="utf-8")

    saida = None
    motivo = motivo_proc
    try:
        saida = localizar_saida(biblioteca, entrada, pasta)
    except (ValueError, zipfile.BadZipFile) as erro:
        motivo = f"saída ilegível: {erro}"
    if saida is None and motivo is None:
        motivo = f"exit {codigo} sem MusicXML"
    elif saida is not None and codigo not in (0, None):
        motivo = f"exit {codigo}, MusicXML gerado"
    return {
        "id": id_,
        "ok": saida is not None,
        "motivo": motivo,
        "segundos": round(segundos, 2),
        "codigo": codigo,
        "saida": str(saida.relative_to(RAIZ)) if saida is not None else None,
    }


def _gravar_execucao(pasta_base: Path, registros: list[dict]) -> None:
    """Grava ``execucao.json``, mantendo os ids que não foram rodados agora.

    Args:
        pasta_base: ``<biblioteca>/<condicao>`` em ``PASTA_OMR``.
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


def rodar(biblioteca: str, condicao: str, ids: list[str] | None) -> list[dict]:
    """Roda uma biblioteca em uma condição sobre os recortes pedidos.

    Args:
        biblioteca: ``homr``, ``audiveris`` ou ``oemer``.
        condicao: ``nativo`` ou ``x2``.
        ids: ids dos recortes (None = todos do índice).

    Returns:
        Os registros de execução, na ordem do índice.
    """
    indice = carregar_indice()
    if ids is not None:
        desconhecidos = sorted(set(ids) - {i["id"] for i in indice})
        if desconhecidos:
            raise ValueError(f"ids fora do índice: {desconhecidos}")
        indice = [i for i in indice if i["id"] in ids]
    pasta_base = PASTA_OMR / biblioteca / condicao
    pasta_base.mkdir(parents=True, exist_ok=True)
    registros = []
    for item in indice:
        registro = rodar_um(biblioteca, condicao, item, pasta_base)
        registros.append(registro)
        print(
            f"{biblioteca} {condicao} {registro['id']}: "
            f"{'ok' if registro['ok'] else 'FALHA'} "
            f"{registro['segundos']} s"
            f"{'' if registro['motivo'] is None else ' (' + registro['motivo'] + ')'}",
            flush=True,
        )
    _gravar_execucao(pasta_base, registros)
    return registros


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI.

    Args:
        argv: argumentos (None = ``sys.argv``).

    Returns:
        Código de saída: 0 se todos os recortes geraram MusicXML, 1 caso contrário.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    rod = sub.add_parser("rodar", help="roda uma biblioteca em uma condição")
    rod.add_argument("--biblioteca", choices=BIBLIOTECAS, required=True)
    rod.add_argument("--condicao", choices=CONDICOES, required=True)
    rod.add_argument("--ids", default=None, help="ex.: R01,R08 (padrão: todos)")
    args = parser.parse_args(argv)

    ids = args.ids.split(",") if args.ids else None
    registros = rodar(args.biblioteca, args.condicao, ids)
    falhas = [r for r in registros if not r["ok"]]
    print(
        f"{args.biblioteca} {args.condicao}: {len(registros) - len(falhas)}/"
        f"{len(registros)} com MusicXML",
        file=sys.stderr,
    )
    return 0 if not falhas else 1


if __name__ == "__main__":
    raise SystemExit(main())
