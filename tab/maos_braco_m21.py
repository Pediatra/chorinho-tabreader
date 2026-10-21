"""Dados do piloto do detector do braço (rodada 1021, parte 1).

Quatro fontes, todas em ``MAOS_M21``:

- ``G``: os 66 quadros do dono em ``braco.json``, como faixa retificada com erro
  simulado (``gabarito``);
- ``R``: alvos do rastreador congelado, em t_chave ± 3·k s (k = 1..10), a partir de
  cada quadro G (``rastreador``). Só entra o que o rastreador acha;
- ``S``: braços sintéticos com rótulo exato (``sintetico``);
- ``fundos``: quadros de vídeos do acervo fora da M11b, para o fundo de S (``fundos``).

``folha`` monta uma folha de 24 faixas por fonte, com os rótulos desenhados, para
conferir a olho. A M11b é uma barreira: nenhum vídeo dela entra em S, R ou G.

CLI: ``python -m tab.maos_braco_m21 {fundos,gabarito,rastreador,sintetico,folha}``.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, MAOS_M3B, MAOS_M3B_QUADROS, MAOS_M21, acervo
from .maos_braco_cadeia import PARAMETROS_PADRAO, rastrear_cadeia, sequencia_ate_alvo
from .maos_braco_faixa import (
    eixo_da_faixa,
    matriz_da_faixa,
    perturbar,
    recortar,
    rotulo_na_faixa,
)
from .maos_braco_sintetico import (
    conferir_fora_m11b,
    duracao_do_video,
    fundos,
    gerar,
    quadro_em,
    videos_proibidos,
)
from .maos_braco_tempo import Marcas, marcas_do_registro, transformar

#: Semente da rodada 1021 (prefixo dos sorteios de cada fonte).
SEMENTE = 20261021
#: Processos paralelos do rastreador e do sintético.
PROCESSOS = 4
#: Quadros de pele tentados por amostra S, até achar um componente de pele.
QUADROS_PELE = 4
#: Alvos do rastreador: k = 1..K_MAXIMO, a cada INTERVALO_S segundos.
K_MAXIMO = 10
INTERVALO_S = 3.0
#: Quadros de fundo para S.
QUANTIDADE_FUNDOS = 300
#: Amostras por fonte na folha.
AMOSTRAS_NA_FOLHA = 24
COLUNAS_NA_FOLHA = 2
#: Pastas de saída.
DIR_G = MAOS_M21 / "G"
DIR_R = MAOS_M21 / "R"
DIR_S = MAOS_M21 / "S"
DIR_FUNDOS = MAOS_M21 / "fundos"
#: Contexto dos processos do pool (preenchido por ``_iniciar_contexto``).
_CONTEXTO: dict = {}


def _quadros_do_gabarito() -> tuple[dict, dict]:
    """Registros do dono com nut marcado e o índice dos quadros (canal, arquivo e instante).

    Returns:
        ``(quadros, indice)``: ``quadros`` é id -> registro do gabarito, e ``indice``
        é id -> item de ``indice.json``.
    """
    bruto = json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))["quadros"]
    # Sem nut marcado (nut "fora") não há eixo da faixa: o quadro sai de G e do rastreio.
    quadros = {k: v for k, v in bruto.items() if isinstance(v.get("nut"), list)}
    excluidos = sorted(set(bruto) - set(quadros))
    if excluidos:
        print(f"fora de G e do rastreio (sem nut): {excluidos}", file=sys.stderr)
    itens = json.loads((MAOS_M3B / "indice.json").read_text(encoding="utf-8"))
    indice = {item["id"]: item for item in itens["quadros"]}
    return quadros, indice


def _imagem(caminho: Path) -> np.ndarray:
    """Lê uma imagem BGR, ou levanta erro se ela não existe.

    Args:
        caminho: arquivo da imagem.

    Returns:
        Imagem BGR.

    Raises:
        FileNotFoundError: se o arquivo não pode ser lido.
    """
    img = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(caminho)
    return img


def _registro_de(marcas: Marcas) -> dict:
    """Marcas em formato de registro (o mesmo do gabarito), para o rótulo do rastreador.

    Args:
        marcas: marcas com nut (já transformadas).

    Returns:
        Registro com ``braco``, ``nut``, ``corda1``, ``corda6`` e ``trastes`` em ordem de
        número, contíguos a partir do 1.
    """
    return {
        "braco": "sim",
        "nut": marcas.nut.tolist(),
        "corda1": marcas.corda1.tolist(),
        "corda6": marcas.corda6.tolist(),
        "trastes": [marcas.trastes[n].tolist() for n in sorted(marcas.trastes)],
    }


def gabarito() -> int:
    """Grava a faixa perturbada (G) dos 66 quadros do dono e o rótulo de cada um.

    O erro do eixo vem de ``random.Random("20261021:G:<id>")``. Retomável: pula o que
    já existe.

    Returns:
        Quantidade de quadros de G.
    """
    quadros, indice = _quadros_do_gabarito()
    proibidos = videos_proibidos()
    DIR_G.mkdir(parents=True, exist_ok=True)
    for identificador in sorted(quadros):
        item = indice[identificador]
        conferir_fora_m11b(item["arquivo"], proibidos)
        destino = DIR_G / f"{identificador}.png"
        if destino.exists() and (DIR_G / f"{identificador}.json").exists():
            continue
        marcas = marcas_do_registro(quadros[identificador])
        if marcas is None:
            raise ValueError(f"{identificador} sem marcas completas")
        eixo = perturbar(
            eixo_da_faixa(marcas),
            random.Random(f"{SEMENTE}:G:{identificador}"),
        )
        matriz = matriz_da_faixa(eixo)
        imagem = _imagem(MAOS_M3B / item["png"])
        cv2.imwrite(str(destino), recortar(imagem, matriz))
        registro = {
            "id": identificador,
            "canal": item["canal"],
            "arquivo": item["arquivo"],
            "matriz": matriz.tolist(),
            "rotulo_na_faixa": rotulo_na_faixa(marcas, matriz),
        }
        (DIR_G / f"{identificador}.json").write_text(
            json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return len(quadros)


def _alvos_do_rastreio(
    quadros: dict, indice: dict, duracoes: dict[str, float]
) -> list[dict]:
    """Tarefas do rastreador: alvos em t_chave ± 3·k s, dentro da duração do vídeo.

    Args:
        quadros: registros do gabarito.
        indice: item de ``indice.json`` por id.
        duracoes: duração de cada arquivo, em segundos.

    Returns:
        Uma tarefa por alvo, na ordem de id, k e sinal.
    """
    tarefas = []
    for identificador in sorted(quadros):
        item = indice[identificador]
        dur = duracoes[item["arquivo"]]
        for k in range(1, K_MAXIMO + 1):
            for sinal in (1, -1):
                t_alvo = float(item["t"]) + sinal * INTERVALO_S * k
                if not 0.0 <= t_alvo < dur:
                    continue
                sinal_texto = "+" if sinal > 0 else "-"
                tarefas.append(
                    {
                        "nome": f"{identificador}_{sinal_texto}{k}",
                        "chave": identificador,
                        "canal": item["canal"],
                        "arquivo": item["arquivo"],
                        "t_chave": float(item["t"]),
                        "t_alvo": t_alvo,
                        "registro": quadros[identificador],
                    }
                )
    return tarefas


def _rodar_alvo(tarefa: dict) -> str:
    """Roda o rastreador num alvo e grava o resultado (função de processo).

    Achou: grava o quadro alvo em JPEG 95 e um JSON com o registro transformado. Não
    achou: grava só o JSON, com ``achou`` falso, para não repetir na retomada.

    Args:
        tarefa: entrada de ``_alvos_do_rastreio``.

    Returns:
        ``achou``, ``nao_achou``, ``sem_quadro`` ou ``erro``.
    """
    try:
        return _rastrear_um_alvo(tarefa)
    except Exception as erro:
        print(f"erro em {tarefa['nome']}: {erro}", file=sys.stderr)
        return "erro"


def _rastrear_um_alvo(tarefa: dict) -> str:
    """Corpo de ``_rodar_alvo``, sem a guarda de erro.

    Args:
        tarefa: entrada de ``_alvos_do_rastreio``.

    Returns:
        ``achou``, ``nao_achou`` ou ``sem_quadro``.
    """
    conferir_fora_m11b(tarefa["arquivo"], _CONTEXTO["proibidos"])
    video = acervo() / tarefa["arquivo"]
    img_alvo = quadro_em(video, tarefa["t_alvo"])
    if img_alvo is None:
        return "sem_quadro"
    img_chave = _imagem(MAOS_M3B_QUADROS / f"{tarefa['chave']}.png")
    marcas_chave = marcas_do_registro(tarefa["registro"])
    quadros = sequencia_ate_alvo(
        video,
        tarefa["t_chave"],
        tarefa["t_alvo"],
        img_alvo,
        PARAMETROS_PADRAO.passo_s,
        PARAMETROS_PADRAO.bloco_s,
    )
    h, info = rastrear_cadeia(
        quadros,
        img_chave,
        marcas_chave,
        tarefa["registro"].get("paineis"),
        PARAMETROS_PADRAO,
    )
    base = {
        "chave": tarefa["chave"],
        "canal": tarefa["canal"],
        "arquivo": tarefa["arquivo"],
        "t": tarefa["t_alvo"],
        "info": info,
    }
    if h is None:
        base["achou"] = False
        (DIR_R / f"{tarefa['nome']}.json").write_text(
            json.dumps(base, ensure_ascii=False), encoding="utf-8"
        )
        return "nao_achou"
    base["achou"] = True
    base["registro"] = _registro_de(transformar(marcas_chave, h))
    cv2.imwrite(
        str(DIR_R / f"{tarefa['nome']}.jpg"),
        img_alvo,
        [cv2.IMWRITE_JPEG_QUALITY, 95],
    )
    (DIR_R / f"{tarefa['nome']}.json").write_text(
        json.dumps(base, ensure_ascii=False), encoding="utf-8"
    )
    return "achou"


def _iniciar_contexto(proibidos: frozenset[str]) -> None:
    """Preenche o contexto do processo (a M11b, para a barreira).

    Args:
        proibidos: conjunto de ``videos_proibidos``.
    """
    _CONTEXTO["proibidos"] = proibidos


def rastreador(chaves: frozenset[str] | None = None) -> int:
    """Roda o rastreador a partir de cada quadro G e imprime o resumo por canal.

    Retomável: as tarefas cujo JSON já existe não rodam de novo. O resumo conta os
    alvos planejados, os que achou e os que não achou, e os que não tiveram resultado
    (sem quadro ou erro).

    Args:
        chaves: se dado, só estes quadros-chave (rodada 1037: as chaves com capo,
            remarcadas pela decisão 1010).

    Returns:
        0 ao terminar.
    """
    quadros, indice = _quadros_do_gabarito()
    if chaves is not None:
        quadros = {k: v for k, v in quadros.items() if k in chaves}
    proibidos = videos_proibidos()
    arquivos = sorted({indice[i]["arquivo"] for i in quadros})
    for arquivo in arquivos:
        conferir_fora_m11b(arquivo, proibidos)
    duracoes = {arq: duracao_do_video(acervo() / arq) for arq in arquivos}
    tarefas = _alvos_do_rastreio(quadros, indice, duracoes)
    DIR_R.mkdir(parents=True, exist_ok=True)
    pendentes = [t for t in tarefas if not (DIR_R / f"{t['nome']}.json").exists()]
    inicio = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=PROCESSOS,
        initializer=_iniciar_contexto,
        initargs=(proibidos,),
    ) as executor:
        list(executor.map(_rodar_alvo, pendentes, chunksize=1))
    print(f"rastreio: {time.perf_counter() - inicio:.1f} s", file=sys.stderr)
    _resumir_rastreio(tarefas)
    return 0


def _resumir_rastreio(tarefas: list[dict]) -> None:
    """Imprime, por canal, os alvos, os que achou e os que não achou.

    Args:
        tarefas: todas as tarefas planejadas (com ou sem resultado no disco).
    """
    por_canal: dict[str, dict[str, int]] = {}
    for tarefa in tarefas:
        contagem = por_canal.setdefault(
            tarefa["canal"], {"alvos": 0, "achou": 0, "nao_achou": 0}
        )
        contagem["alvos"] += 1
        caminho = DIR_R / f"{tarefa['nome']}.json"
        if caminho.exists():
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            chave = "achou" if dados["achou"] else "nao_achou"
            contagem[chave] += 1
    print(f"{'canal':<22}{'alvos':>7}{'achou':>7}{'nao':>7}{'sem':>7}")
    for canal in sorted(por_canal):
        c = por_canal[canal]
        sem = c["alvos"] - c["achou"] - c["nao_achou"]
        print(f"{canal:<22}{c['alvos']:>7}{c['achou']:>7}{c['nao_achou']:>7}{sem:>7}")
    total = {k: sum(c[k] for c in por_canal.values()) for k in ("alvos", "achou")}
    total["nao_achou"] = sum(c["nao_achou"] for c in por_canal.values())
    print(
        f"{'total':<22}{total['alvos']:>7}{total['achou']:>7}"
        f"{total['nao_achou']:>7}{total['alvos'] - total['achou'] - total['nao_achou']:>7}"
    )


def _amostra_sintetica(i: int) -> str:
    """Gera a amostra S de índice ``i`` (função de processo).

    O fundo é sorteado com ``random.Random("20261021:S:<i>")``. Retomável: não faz nada
    se os dois arquivos já existem.

    Args:
        i: índice da amostra.

    Returns:
        ``feita`` ou ``existente``.
    """
    base = DIR_S / f"{i:05d}"
    if base.with_suffix(".jpg").exists() and base.with_suffix(".json").exists():
        return "existente"
    base.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(f"{SEMENTE}:S:{i}")
    indice = _CONTEXTO["fundos"]
    entrada = indice[rng.randrange(len(indice))]
    entradas_mao = [indice[rng.randrange(len(indice))] for _ in range(QUADROS_PELE)]
    conferir_fora_m11b(entrada["arquivo"], _CONTEXTO["proibidos"])
    for entrada_mao in entradas_mao:
        conferir_fora_m11b(entrada_mao["arquivo"], _CONTEXTO["proibidos"])
    fundo = _imagem(DIR_FUNDOS / entrada["jpg"])
    fundos_mao = [_imagem(DIR_FUNDOS / e["jpg"]) for e in entradas_mao]
    imagem, registro = gerar(rng, fundo, fundos_mao)
    registro["fundo"] = entrada["arquivo"]
    registro["fundos_mao"] = [e["arquivo"] for e in entradas_mao]
    cv2.imwrite(str(base.with_suffix(".jpg")), imagem, [cv2.IMWRITE_JPEG_QUALITY, 95])
    base.with_suffix(".json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return "feita"


def _iniciar_sintetico(fundos_indice: list[dict], proibidos: frozenset[str]) -> None:
    """Preenche o contexto do processo do sintético (fundos e M11b).

    Args:
        fundos_indice: entradas de ``fundos``.
        proibidos: conjunto de ``videos_proibidos``.
    """
    _CONTEXTO["fundos"] = fundos_indice
    _CONTEXTO["proibidos"] = proibidos


def sintetico(n: int) -> int:
    """Gera ``n`` amostras S, em paralelo e retomáveis.

    Args:
        n: quantidade de amostras (índices 0 a n-1).

    Returns:
        0 ao terminar.

    Raises:
        FileNotFoundError: se os fundos ainda não foram gerados.
    """
    indice_fundos = DIR_FUNDOS / "indice.json"
    if not indice_fundos.exists():
        raise FileNotFoundError("rode antes: python -m tab.maos_braco_m21 fundos")
    fundos_lista = json.loads(indice_fundos.read_text(encoding="utf-8"))["fundos"]
    proibidos = videos_proibidos()
    DIR_S.mkdir(parents=True, exist_ok=True)
    inicio = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=PROCESSOS,
        initializer=_iniciar_sintetico,
        initargs=(fundos_lista, proibidos),
    ) as executor:
        resultados = list(executor.map(_amostra_sintetica, range(n), chunksize=16))
    feitas = resultados.count("feita")
    print(
        f"sintetico: {feitas} feitas, {n - feitas} existentes, "
        f"{time.perf_counter() - inicio:.1f} s",
        file=sys.stderr,
    )
    return 0


def _faixa_de_registro(
    caminho: Path, registro: dict, rng: random.Random
) -> tuple[np.ndarray, dict]:
    """Faixa de um quadro inteiro (R ou S) com o erro sorteado e os rótulos.

    Args:
        caminho: JPEG do quadro inteiro.
        registro: marcas do quadro (formato de registro).
        rng: gerador do erro do eixo.

    Returns:
        ``(faixa, rotulo)``.
    """
    marcas = marcas_do_registro(registro)
    if marcas is None:
        raise ValueError(f"{caminho.name} sem marcas completas")
    matriz = matriz_da_faixa(perturbar(eixo_da_faixa(marcas), rng))
    return recortar(_imagem(caminho), matriz), rotulo_na_faixa(marcas, matriz)


def _desenhar_faixa(faixa: np.ndarray, rotulo: dict, titulo: str) -> np.ndarray:
    """Desenha os rótulos sobre a faixa, para a folha de conferência.

    Corda 1 em vermelho, corda 6 em azul, trastes em amarelo com o número, e o nut em
    verde (zero).

    Args:
        faixa: faixa BGR de 192 x 1024.
        rotulo: dicionário de ``rotulo_na_faixa``.
        titulo: texto no canto da faixa.

    Returns:
        Cópia da faixa com os desenhos.
    """
    img = faixa.copy()

    def ponto(p: list) -> tuple[int, int]:
        """Ponto inteiro para o desenho do OpenCV."""
        return round(p[0]), round(p[1])

    cv2.line(
        img, ponto(rotulo["corda1"][0]), ponto(rotulo["corda1"][1]), (0, 0, 255), 1
    )
    cv2.line(
        img, ponto(rotulo["corda6"][0]), ponto(rotulo["corda6"][1]), (255, 0, 0), 1
    )
    for numero, x, y in rotulo["trastes"]:
        if numero == 0:
            cv2.circle(img, (round(x), round(y)), 5, (0, 255, 0), 2)
            continue
        cv2.circle(img, (round(x), round(y)), 3, (0, 255, 255), -1)
        cv2.putText(
            img,
            str(numero),
            (round(x) + 4, round(y) - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
        )
    cv2.putText(img, titulo, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return img


def _itens_da_folha(fonte: str) -> list[str]:
    """Identificadores disponíveis para a folha de uma fonte.

    Args:
        fonte: ``G``, ``R`` ou ``S``.

    Returns:
        Nomes (sem extensão), ordenados. Em R, só os que acharam.
    """
    pasta = {"G": DIR_G, "R": DIR_R, "S": DIR_S}[fonte]
    nomes = []
    for caminho in sorted(pasta.glob("*.json")):
        if fonte == "R":
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            if not dados["achou"]:
                continue
        nomes.append(caminho.stem)
    return nomes


def _celula(fonte: str, nome: str) -> np.ndarray:
    """Faixa com rótulos de uma amostra da folha.

    Args:
        fonte: ``G``, ``R`` ou ``S``.
        nome: identificador da amostra (sem extensão).

    Returns:
        Faixa BGR com os rótulos.
    """
    if fonte == "G":
        faixa = _imagem(DIR_G / f"{nome}.png")
        dados = json.loads((DIR_G / f"{nome}.json").read_text(encoding="utf-8"))
        rotulo = dados["rotulo_na_faixa"]
        titulo = f"G {nome} {dados['canal']}"
    else:
        pasta = DIR_R if fonte == "R" else DIR_S
        dados = json.loads((pasta / f"{nome}.json").read_text(encoding="utf-8"))
        registro = dados["registro"] if fonte == "R" else dados
        rng = random.Random(f"{SEMENTE}:F:{fonte}:{nome}")
        faixa, rotulo = _faixa_de_registro(pasta / f"{nome}.jpg", registro, rng)
        titulo = f"{fonte} {nome}"
    return _desenhar_faixa(faixa, rotulo, titulo)


def folha() -> int:
    """Monta as folhas de conferência de G, R e S (24 faixas cada, sorteio fixo).

    Returns:
        0 ao terminar.
    """
    for fonte in ("G", "R", "S"):
        disponiveis = _itens_da_folha(fonte)
        escolhidos = random.Random(f"{SEMENTE}:F:{fonte}").sample(
            disponiveis, min(AMOSTRAS_NA_FOLHA, len(disponiveis))
        )
        celulas = [_celula(fonte, nome) for nome in escolhidos]
        if not celulas:
            print(f"folha {fonte}: sem amostras", file=sys.stderr)
            continue
        linhas = math.ceil(len(celulas) / COLUNAS_NA_FOLHA)
        altura, largura = celulas[0].shape[:2]
        pagina = np.full(
            (linhas * (altura + 6), COLUNAS_NA_FOLHA * (largura + 6), 3),
            40,
            dtype=np.uint8,
        )
        for indice, celula in enumerate(celulas):
            linha, coluna = divmod(indice, COLUNAS_NA_FOLHA)
            y, x = linha * (altura + 6), coluna * (largura + 6)
            pagina[y : y + altura, x : x + largura] = celula
        destino = MAOS_M21 / f"folha_{fonte}.jpg"
        cv2.imwrite(str(destino), pagina, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"folha {fonte}: {len(celulas)} amostras em {destino}", file=sys.stderr)
    return 0


def _cronometrar(etapa: str, funcao: object, *args: object) -> int:
    """Roda uma etapa e informa o tempo dela.

    Args:
        etapa: nome da etapa para o log.
        funcao: etapa a rodar.
        *args: argumentos da etapa.

    Returns:
        O código de retorno da etapa.
    """
    inicio = time.perf_counter()
    codigo = funcao(*args)
    print(f"{etapa}: {time.perf_counter() - inicio:.1f} s", file=sys.stderr)
    return codigo


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subcomandos = parser.add_subparsers(dest="comando", required=True)
    subcomandos.add_parser("fundos", help="quadros de fundo para S (fora da M11b)")
    subcomandos.add_parser("gabarito", help="faixas G, com erro simulado")
    rastreio = subcomandos.add_parser(
        "rastreador", help="alvos R a partir de cada quadro G"
    )
    rastreio.add_argument(
        "--chaves", help="só estes quadros-chave, separados por vírgula (ex.: q04,q10)"
    )
    sint = subcomandos.add_parser("sintetico", help="amostras S")
    sint.add_argument("--n", type=int, default=20000)
    subcomandos.add_parser("folha", help="folhas de conferência de G, R e S")
    args = parser.parse_args()
    if args.comando == "fundos":
        _cronometrar(
            "fundos",
            lambda: len(fundos(QUANTIDADE_FUNDOS, random.Random(f"{SEMENTE}:fundos"))),
        )
        return 0
    if args.comando == "gabarito":
        _cronometrar("gabarito", gabarito)
        return 0
    if args.comando == "rastreador":
        chaves = frozenset(args.chaves.split(",")) if args.chaves else None
        _cronometrar("rastreador", rastreador, chaves)
        return 0
    if args.comando == "sintetico":
        _cronometrar("sintetico", sintetico, args.n)
        return 0
    _cronometrar("folha", folha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
