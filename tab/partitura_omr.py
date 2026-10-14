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
    ``x2``: o PNG ampliado 2x com ``cv2.resize(..., fx=2, fy=2, INTER_CUBIC)``, e mais nada;
    ``x3`` e ``x4``: o mesmo, ampliado 3x e 4x;
    ``x2_binaria``: cinza, ampliado 2x cúbico, depois limiar de Otsu (preto e branco);
    ``x2_margem``: como ``x2``, mas sobre os recortes de ``recortes_margem/`` (margem de
    7 entrelinhas em cima e embaixo, em vez de 4 e 6);
    ``x2_cabecalho``: como ``x2``, mas R06 e R07 recebem à esquerda o cabeçalho do R05
    (clave, armadura e fórmula, até ``CABECALHO_X_FIM``), alinhado pela 1ª linha da pauta.

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
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from tab.caminhos import RAIZ, SAIDA

#: Recortes e índice gerados por ``tab.partitura_recortes``.
PASTA_RECORTES = SAIDA / "partitura" / "p1" / "recortes"

#: Recortes com margem de 7 entrelinhas (``tab.partitura_recortes --margem-cima 7
#: --margem-baixo 7 --saida ...``), lidos pela condição ``x2_margem``.
PASTA_RECORTES_MARGEM = SAIDA / "partitura" / "p1" / "recortes_margem"

#: Recorte de onde sai o cabeçalho (clave, armadura, fórmula) colado em R06 e R07.
CABECALHO_ORIGEM = "R05"

#: Recortes que recebem o cabeçalho (início de sistema sem clave nem armadura).
CABECALHO_IDS = ("R06", "R07")

#: Colunas 0 a ``CABECALHO_X_FIM - 1`` do R05 vão para a frente do recorte. No R05 a
#: fórmula de compasso vai até x=93 e a primeira nota começa em x=132; 110 cai no vazio.
CABECALHO_X_FIM = 110

#: Saída das bibliotecas: ``<biblioteca>/<condicao>/<id>/``.
PASTA_OMR = SAIDA / "partitura" / "p1" / "omr"

BIBLIOTECAS = ("homr", "audiveris", "oemer")
CONDICOES = (
    "nativo",
    "x2",
    "x3",
    "x4",
    "x2_binaria",
    "x2_margem",
    "x2_cabecalho",
)

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


@dataclass(frozen=True)
class Cabecalho:
    """Cabeçalho do R05 a ser colado à esquerda de um recorte de destino.

    Attributes:
        imagem: PNG do recorte de origem (R05).
        x_fim: colunas ``0..x_fim-1`` do recorte de origem vão para a frente.
        linha_origem: linha (px, no recorte de origem) da 1ª linha da pauta.
        linha_destino: linha (px, no recorte de destino) da 1ª linha da pauta.
    """

    imagem: Path
    x_fim: int
    linha_origem: int
    linha_destino: int


def compor_cabecalho(imagem: np.ndarray, cabecalho: Cabecalho) -> np.ndarray:
    """Cola o cabeçalho à esquerda da imagem, alinhando a 1ª linha da pauta.

    A imagem de destino fica intacta à direita (a partir de ``x_fim``). Onde a
    pauta do cabeçalho cai acima ou abaixo da imagem, a tela cresce com branco.

    Args:
        imagem: recorte de destino, BGR ou cinza, em resolução nativa.
        cabecalho: origem do cabeçalho e as linhas de alinhamento.

    Returns:
        A imagem composta, com ``x_fim + largura(imagem)`` colunas.

    Raises:
        ValueError: se o cabeçalho não abre ou não tem os mesmos canais.
    """
    cab = cv2.imread(str(cabecalho.imagem), cv2.IMREAD_UNCHANGED)
    if cab is None:
        raise ValueError(f"cabeçalho ilegível: {cabecalho.imagem}")
    if cab.ndim != imagem.ndim:
        raise ValueError("cabeçalho e recorte com canais diferentes")
    cab = cab[:, : cabecalho.x_fim]
    deslocamento = cabecalho.linha_destino - cabecalho.linha_origem
    acima = max(0, -deslocamento)
    topo_cab = deslocamento + acima
    altura_dest = imagem.shape[0]
    altura = max(acima + altura_dest, topo_cab + cab.shape[0])
    forma = (altura, cabecalho.x_fim + imagem.shape[1], *imagem.shape[2:])
    tela = np.full(forma, 255, dtype=imagem.dtype)
    tela[acima : acima + altura_dest, cabecalho.x_fim :] = imagem
    tela[topo_cab : topo_cab + cab.shape[0], : cabecalho.x_fim] = cab
    return tela


def preparar_entrada(
    origem: Path,
    condicao: str,
    destino: Path,
    cabecalho: Cabecalho | None = None,
) -> Path:
    """Escreve a entrada da biblioteca na condição pedida.

    Args:
        origem: PNG do recorte (em ``PASTA_RECORTES`` ou ``PASTA_RECORTES_MARGEM``).
        condicao: uma de ``CONDICOES``.
        destino: arquivo PNG a escrever.
        cabecalho: só para ``x2_cabecalho``; se None, a condição é ``x2`` pura (é o
            que acontece com os recortes que não recebem cabeçalho).

    Returns:
        O próprio ``destino``.

    Raises:
        ValueError: se a condição não existe ou a imagem não abre.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    if condicao == "nativo":
        shutil.copyfile(origem, destino)
        return destino
    if condicao not in CONDICOES:
        raise ValueError(f"condição desconhecida: {condicao}")
    imagem = cv2.imread(str(origem), cv2.IMREAD_UNCHANGED)
    if imagem is None:
        raise ValueError(f"imagem ilegível: {origem}")
    if condicao == "x2_binaria":
        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY) if imagem.ndim == 3 else imagem
        ampliada = cv2.resize(cinza, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, saida = cv2.threshold(ampliada, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    else:
        if condicao == "x2_cabecalho" and cabecalho is not None:
            imagem = compor_cabecalho(imagem, cabecalho)
        fator = {"x3": 3, "x4": 4}.get(condicao, 2)
        saida = cv2.resize(
            imagem, None, fx=fator, fy=fator, interpolation=cv2.INTER_CUBIC
        )
    if not cv2.imwrite(str(destino), saida):
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


def cabecalho_de(item: dict, indice: dict[str, dict]) -> Cabecalho | None:
    """Cabeçalho do R05 para um recorte, se ele é um dos que recebem (``CABECALHO_IDS``).

    Args:
        item: entrada do índice original (com ``id``, ``ys`` e ``caixa_recorte``).
        indice: entradas do índice original, por id.

    Returns:
        O ``Cabecalho`` com as linhas de alinhamento, ou None para os outros ids.
    """
    if item["id"] not in CABECALHO_IDS:
        return None
    origem = indice[CABECALHO_ORIGEM]
    linha_origem = origem["ys"][0] - origem["caixa_recorte"][1]
    linha_destino = item["ys"][0] - item["caixa_recorte"][1]
    return Cabecalho(
        imagem=PASTA_RECORTES / f"{CABECALHO_ORIGEM}.png",
        x_fim=CABECALHO_X_FIM,
        linha_origem=linha_origem,
        linha_destino=linha_destino,
    )


def conferir_margem(indice: dict[str, dict]) -> None:
    """Confere que o índice com margem tem os mesmos ids e as mesmas caixas em x.

    Args:
        indice: entradas do índice original, por id.

    Raises:
        ValueError: se faltam ids ou se a caixa horizontal de algum recorte mudou.
    """
    caminho = PASTA_RECORTES_MARGEM / "indice.json"
    margem = {
        i["id"]: i
        for i in json.loads(caminho.read_text(encoding="utf-8"))
        if i.get("id")
    }
    faltam = sorted(set(indice) - set(margem))
    if faltam:
        raise ValueError(f"ids ausentes no índice com margem: {faltam}")
    for id_, original in indice.items():
        novo = margem[id_]
        if (original["caixa_recorte"][0], original["caixa_recorte"][2]) != (
            novo["caixa_recorte"][0],
            novo["caixa_recorte"][2],
        ):
            raise ValueError(f"caixa horizontal de {id_} mudou com a margem")


def rodar_um(
    biblioteca: str,
    condicao: str,
    item: dict,
    pasta_base: Path,
    origem: Path | None = None,
    cabecalho: Cabecalho | None = None,
) -> dict:
    """Roda uma biblioteca em um recorte e devolve o registro de execução.

    Args:
        biblioteca: ``homr``, ``audiveris`` ou ``oemer``.
        condicao: uma de ``CONDICOES``.
        item: entrada do ``indice.json`` (com ``id``).
        pasta_base: ``<biblioteca>/<condicao>`` em ``PASTA_OMR``.
        origem: PNG do recorte; None = ``PASTA_RECORTES/<id>.png``.
        cabecalho: cabeçalho a colar (só ``x2_cabecalho``); None = sem colar.

    Returns:
        Dict com ``id``, ``ok``, ``motivo``, ``segundos``, ``codigo``, ``saida``
        (caminho relativo à raiz, ou None) e ``entrada`` (o que foi montado).
    """
    id_ = item["id"]
    pasta = pasta_base / id_
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)
    if origem is None:
        origem = PASTA_RECORTES / f"{id_}.png"
    entrada = preparar_entrada(origem, condicao, pasta / "entrada.png", cabecalho)
    detalhe = {"origem": str(origem.relative_to(RAIZ))}
    if cabecalho is not None:
        detalhe["cabecalho"] = {
            "x_fim": cabecalho.x_fim,
            "deslocamento_px": cabecalho.linha_destino - cabecalho.linha_origem,
        }
    detalhe["largura_entrada_px"] = int(cv2.imread(str(entrada)).shape[1])
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
        "entrada": detalhe,
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
    original = {i["id"]: i for i in carregar_indice()}
    if condicao == "x2_margem":
        conferir_margem(original)
    registros = []
    for item in indice:
        origem = None
        if condicao == "x2_margem":
            origem = PASTA_RECORTES_MARGEM / f"{item['id']}.png"
        cabecalho = None
        if condicao == "x2_cabecalho":
            cabecalho = cabecalho_de(item, original)
        registro = rodar_um(biblioteca, condicao, item, pasta_base, origem, cabecalho)
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
