"""Inventário da fase 1b da decisão 9001 (trilha tablatura).

Escreve, sem mover, renomear nem apagar nada:

- ``data/saida/<pasta>/LEIAME.json``, uma por pasta de primeiro nível da tablatura;
- ``data/saida/LEIAME_tablatura_soltos.json``, uma por arquivo solto da tablatura;
- ``artefatos/tablatura/EM_USO.json``, os pesos em uso e o histórico.

Determinístico: a mesma entrada dá o mesmo JSON. Se algum destino já existir com
conteúdo diferente, o script para antes de gravar qualquer coisa. Rodar de novo
sobre o próprio resultado não muda nada (o ``LEIAME.json`` fica fora das contas).

Uso, no host, na raiz do repositório:
    python3 data/saida/tab_rotulo/diag/leiame_9001.py
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
SAIDA = RAIZ / "data" / "saida"
ARTEFATOS = RAIZ / "artefatos"
DATA = "2026-10-21"
TRILHA = "tablatura"

NAO_TABLATURA = {"maos", "audio", "partitura", "part_frentes"}
NOME_LEIAME = "LEIAME.json"
NOME_SOLTOS = "LEIAME_tablatura_soltos.json"
TRILHA_DIAG = Path("tab_rotulo") / "diag"
EXTS_TEXTO_GOLD = {".json", ".jsonl", ".txt", ".md", ".yaml", ".yml", ".py", ".csv", ".sh"}
GOLD_NAO_TAB = {"maos", "audio", "partitura"}

REGEN_HD = "sim, relendo o HD"
REGEN_SNAPSHOT = "nao (cópia de código de 10/10; os arquivos únicos só existem lá)"
MOTIVO_HIST_DATA = "histórico de 08–14/10"
MOTIVO_HIST_ESTADO = "histórico citado no ESTADO.md, regenerável só relendo o HD"
SUFIXO_RODADA = "; citada por rodada: nunca apagar, só arquivar"

# MANTER explícito: (nomes, motivo, regeneravel).
MANTER_GRUPOS = [
    (["t82", "t83", "t84", "tab_rotulo"], "rótulo do dono e gabarito de ataque", "nao"),
    (["n4", "n3", "barline_fina"], "treino e medida vivos (rodadas 0211–0213)", "caro"),
    (
        ["ouro_video", "censo", "produto", "fase8", "conserto_v2", "fase5"],
        "ferramenta dos 8 ouros, censo, MVP e FASE8_GER lidos por outras trilhas, um teste",
        "caro",
    ),
    (
        [
            "frames", "portao_casos", "auditoria_simbolo", "simbolos", "paineis",
            "c1b", "diag_v2", "presenca", "presenca_7_1", "t500",
        ],
        "imagem do rótulo ou citada pelo ouro",
        "caro",
    ),
    (["tab_frentes"], "TAB_FRENTE_* e rodadas 0101–0170", "caro"),
]
MANTER_EXPL = {n: (motivo, regen) for nomes, motivo, regen in MANTER_GRUPOS for n in nomes}

# Cópias inteiras do repositório (arquivar), com os arquivos do ouro que ficam no lugar.
SNAPSHOT_FICAM = {
    "fase4_13": [],
    "cifra": ["cifra/vn_suspeitos.jpg"],
    "fn05": ["fn05/folha_novas.jpg"],
}
HIST_EXPL = {"painel_braco", "afinacao", "serif", "fase5_moldura", "n1", "fase4_arco"}

# Pesos em uso (EM_USO.json).
ATQ = ["atqa", "atqt", "atqe"]
ROTULO_ATAQUE = "detector_tab_final_atqt_s1"
ARTEFATOS_FORA = {"m21", "torch", "riley_guitar", "part_frentes", "audio"}
ARTEFATOS_ARQUIVO_EXTRA = "glifo_sint.pt"
NOTA_HISTORICO = (
    "arquivar só depois de a 0211 fechar; ir para o frio só em .tar "
    "(det_C tem maiúscula e o HD é NTFS)"
)


def _rel(caminho: Path) -> str:
    """Caminho relativo à raiz, com barras normais."""
    return caminho.relative_to(RAIZ).as_posix()


def _pad_saida(nome: str) -> list[re.Pattern[str]]:
    """Padrões de código e gabarito que citam ``data/saida/<nome>`` ou a constante."""
    n = re.escape(nome)
    return [
        re.compile(r"data/saida/" + n + r"(?![A-Za-z0-9_])"),
        re.compile(r"SAIDA\s*/\s*[\"']" + n + r"[\"']"),
        re.compile(r"[\"']saida[\"']\s*[,/]\s*[\"']" + n + r"[\"']"),
    ]


def _pad_rodada(nome: str) -> list[re.Pattern[str]]:
    """Padrões de rodada e decisão: ``data/saida/<nome>`` ou ``saida/<nome>/``."""
    n = re.escape(nome)
    return [
        re.compile(r"data/saida/" + n + r"(?![A-Za-z0-9_])"),
        re.compile(r"(?<![A-Za-z0-9_])saida/" + n + r"/"),
    ]


def _ler_textos() -> dict[str, dict[str, str]]:
    """Lê uma vez os textos onde se procura (chave: caminho relativo)."""

    def ler(arquivos: list[Path]) -> dict[str, str]:
        return {_rel(a): a.read_text(encoding="utf-8", errors="replace") for a in arquivos}

    gold = RAIZ / "data" / "gold"
    gold_arquivos = [
        a
        for a in sorted(gold.rglob("*"))
        if a.is_file()
        and a.suffix in EXTS_TEXTO_GOLD
        and a.relative_to(gold).parts[0] not in GOLD_NAO_TAB
    ]
    return {
        "rodadas": ler(
            sorted((RAIZ / "docs" / "rodadas").glob("*.md"))
            + sorted((RAIZ / "docs" / "decisoes").glob("*.md"))
        ),
        "tab": ler(sorted((RAIZ / "tab").rglob("*.py"))),
        "tests": ler(sorted((RAIZ / "tests").rglob("*.py"))),
        "gold": ler(gold_arquivos),
        "estado": ler([RAIZ / "ESTADO.md"]),
    }


def _citantes(padroes: list[re.Pattern[str]], textos: dict[str, str]) -> list[str]:
    """Caminhos cujo texto casa com algum dos padrões, ordenados."""
    return sorted(rel for rel, txt in textos.items() if any(p.search(txt) for p in padroes))


def _mb(caminho: Path) -> int:
    """Tamanho em MB inteiros, como ``du -sm``, sem contar o ``LEIAME.json``."""
    cmd = ["du", "-sm"]
    if caminho.is_dir():
        cmd.append("--exclude=" + NOME_LEIAME)
    cmd.append(str(caminho))
    saida = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return int(saida.split()[0])


def _modificado(caminho: Path) -> str | None:
    """Data do arquivo mais recente dentro da pasta, sem o ``LEIAME.json``.

    Devolve ``None`` quando não há nenhum arquivo além do ``LEIAME.json``.
    """
    if caminho.is_file():
        return datetime.datetime.fromtimestamp(caminho.stat().st_mtime).date().isoformat()
    ts = None
    for raiz, _dirs, arquivos in os.walk(caminho):
        for f in arquivos:
            if f == NOME_LEIAME:
                continue
            # lstat: um link simbólico quebrado não derruba a conta (du também não segue).
            m = os.lstat(os.path.join(raiz, f)).st_mtime
            ts = m if ts is None else max(ts, m)
    if ts is None:
        return None
    return datetime.datetime.fromtimestamp(ts).date().isoformat()


def _comando_script(caminho: Path) -> str | None:
    """``python <caminho>`` ou ``sh <caminho>`` para um script."""
    if caminho.suffix == ".py":
        return "python " + _rel(caminho)
    if caminho.suffix == ".sh":
        return "sh " + _rel(caminho)
    return None


def _comando_rodada(nome: str, rodadas: dict[str, str]) -> str:
    """Primeira linha de ``docs/rodadas`` com ``python -m tab.`` que cita a pasta."""
    padrao = re.compile(r"(?<![A-Za-z0-9_])saida/" + re.escape(nome) + r"(?![A-Za-z0-9_])")
    for rel in sorted(rodadas):
        if not rel.startswith("docs/rodadas/"):
            continue
        for linha in rodadas[rel].splitlines():
            if "python -m tab." in linha and padrao.search(linha):
                i = linha.index("python -m tab.")
                # Para no primeiro crase: o comando vem entre crases na rodada.
                fim = linha.find("`", i)
                trecho = linha[i:] if fim < 0 else linha[i:fim]
                return trecho.rstrip(" |\t")
    return "não registrado"


def _motivo_snapshot(ficam: list[str]) -> str:
    """Motivo das três cópias inteiras do repositório."""
    base = "cópia inteira do repositório de 10/10 (snapshot); vai em .tar para o frio."
    if not ficam:
        return base + " Nenhum arquivo do ouro fica no lugar."
    return base + " Ficam no lugar os arquivos que o ouro cita: " + " e ".join(ficam) + "."


def _classificar_pasta(
    nome: str, pasta: Path, cod: bool, gold: bool
) -> tuple[str, str, str, bool, list[str] | None]:
    """Devolve (classe, regeneravel, motivo, veio_da_regra_extra, ficam_no_lugar)."""
    if nome in MANTER_EXPL:
        motivo, regen = MANTER_EXPL[nome]
        return "manter", regen, motivo, False, None
    if nome == "presenca_v2":
        if any(p.name != NOME_LEIAME for p in pasta.iterdir()):
            raise SystemExit(f"ERRO: {nome} não está vazia; não é apagável")
        return "apagar", "sim", "vazia", False, None
    if nome in SNAPSHOT_FICAM:
        ficam = SNAPSHOT_FICAM[nome]
        return "arquivar", REGEN_SNAPSHOT, _motivo_snapshot(ficam), False, ficam
    if nome in HIST_EXPL or nome.startswith("simbolos_"):
        return "arquivar", REGEN_HD, MOTIVO_HIST_ESTADO, False, None
    # REGRA EXTRA: pasta fora das listas, lida pelo código ou citada pelo gabarito.
    if cod:
        return "manter", "caro", "lido pelo código", True, None
    if gold:
        return "manter", "caro", "citado pelo gabarito", True, None
    if nome == "video":
        return "arquivar", REGEN_HD, MOTIVO_HIST_ESTADO, False, None
    return "arquivar", REGEN_HD, MOTIVO_HIST_DATA, False, None


def _json(obj: object) -> str:
    """Serialização canônica: a mesma entrada dá o mesmo texto."""
    return json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def _montar_em_uso() -> tuple[dict, list[str]]:
    """Monta ``EM_USO.json``. Devolve também a lista de pastas que faltam em ``artefatos/``."""
    faltam: list[str] = []

    def existem(nomes: list[str]) -> list[str]:
        presentes = []
        for n in nomes:
            (presentes if (ARTEFATOS / n).exists() else faltam).append(n)
        return sorted(presentes)

    grupo_0211 = [f"detector_tab_final_{a}_s{s}" for s in (1, 2, 3) for a in ATQ]
    grupo_0211 += [
        f"detector_tab_v3ft_d{d}_{a}_s{s}" for s in (1, 2, 3) for d in (1, 2, 3, 4) for a in ATQ
    ]
    if len(grupo_0211) != 45:
        raise SystemExit(f"ERRO: a lista da 0211 tem {len(grupo_0211)} nomes, esperado 45")
    # O rótulo de ataque já é usado pelo produto de rótulo: entra só uma vez.
    grupo_0211 = [n for n in grupo_0211 if n != ROTULO_ATAQUE]

    grupo_0212 = [f"detector_tab_v3ft_d{d}_ger{suf}" for suf in ("", "_s2", "_s3") for d in (1, 2, 3, 4)]
    grupo_0212 += ["detector_tab_final_s2_ger", "detector_tab_final_s3_ger"]

    em_uso = [
        {"uso": "produto, leitura comum (caminhos.DETECTOR_PADRAO)", "pastas": existem(["detector_tab_final_s1_ger"])},
        {"uso": "rótulo de ataque (ataque_rotulo.DETECTOR_CALIBRADO)", "pastas": existem([ROTULO_ATAQUE])},
        {"uso": "validação pendente da 0211 na T8.4 e troca proposta do produto", "pastas": existem(grupo_0211)},
        {"uso": "comparação da 0212", "pastas": existem(grupo_0212)},
        {"uso": "partida do ajuste fino (n4/treinar_ft.py PARTIDA)", "pastas": existem(["detector_tab_v3_s1"])},
        {"uso": "leitor glifos e ferramentas antigas", "pastas": existem(["oficial_3", "oficial_2", "digito_2", "simbolo_2"])},
        {"uso": "pesos das frentes de pesquisa (TAB_FRENTES_PESOS)", "pastas": existem(["tab_frentes"])},
    ]
    usados = {p for bloco in em_uso for p in bloco["pastas"]}

    # Histórico: toda pasta de artefatos/ da tablatura que não está em uso.
    tab_pastas = sorted(
        p.name
        for p in ARTEFATOS.iterdir()
        if p.is_dir() and p.name not in ARTEFATOS_FORA | {TRILHA}
    )
    historico = [n for n in tab_pastas if n not in usados]
    if ARTEFATOS_ARQUIVO_EXTRA in [p.name for p in ARTEFATOS.iterdir()]:
        historico.append(ARTEFATOS_ARQUIVO_EXTRA)

    obj = {
        "trilha": TRILHA,
        "data": DATA,
        "raiz_hoje": "artefatos/ (cada peso é uma pasta com modelo.pt + config.json)",
        "em_uso": em_uso,
        "historico": {"pastas": sorted(historico), "nota": NOTA_HISTORICO},
    }
    return obj, faltam


def main() -> int:
    """Gera os LEIAME, confere os destinos e grava."""
    if not (RAIZ / "AGENTS.md").is_file():
        raise SystemExit("ERRO: raiz do repositório não encontrada")
    textos = _ler_textos()
    destinos: dict[Path, str] = {}
    contagem_pasta: dict[str, list[tuple[str, int]]] = {"manter": [], "arquivar": [], "apagar": []}
    contagem_solto: dict[str, list[tuple[str, int]]] = {"manter": [], "arquivar": [], "apagar": []}
    regra_extra: list[tuple[str, str]] = []

    # --- pastas de primeiro nível ---------------------------------------
    for pasta in sorted(SAIDA.iterdir()):
        nome = pasta.name
        if not pasta.is_dir() or nome in NAO_TABLATURA:
            continue
        pad = _pad_saida(nome)
        cod = bool(_citantes(pad, textos["tab"]) or _citantes(pad, textos["tests"]))
        gold = bool(_citantes(pad, textos["gold"]))
        rodadas = _citantes(_pad_rodada(nome), textos["rodadas"])
        citado_por = sorted(
            set(
                _citantes(pad, textos["estado"])
                + _citantes(pad, textos["tab"])
                + _citantes(pad, textos["tests"])
                + _citantes(pad, textos["gold"])
            )
        )
        classe, regen, motivo, pela_regra, ficam = _classificar_pasta(nome, pasta, cod, gold)
        if classe == "arquivar" and rodadas:
            # Tira o ponto final do motivo antes de emendar (evita ".;").
            motivo = motivo.rstrip(".") + SUFIXO_RODADA
        if pela_regra:
            regra_extra.append((nome, motivo))

        scripts = sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix in {".py", ".sh"})
        comando: object
        if scripts:
            comando = [_comando_script(p) for p in scripts]
        else:
            comando = _comando_rodada(nome, textos["rodadas"])

        destino = pasta / NOME_LEIAME
        modificado = _modificado(pasta)
        if modificado is None and destino.exists():
            # Pasta vazia: a data gravada na primeira rodada é a que vale.
            modificado = json.loads(destino.read_text(encoding="utf-8"))["modificado"]
        if modificado is None:
            modificado = datetime.datetime.fromtimestamp(pasta.stat().st_mtime).date().isoformat()

        item: dict = {
            "trilha": TRILHA,
            "nome": nome,
            "tamanho_mb": _mb(pasta),
            "modificado": modificado,
            "rodadas": rodadas,
            "citado_por": citado_por,
            "comando": comando,
            "regeneravel": regen,
            "classe": classe,
            "motivo": motivo,
        }
        if ficam is not None:
            item["ficam_no_lugar"] = ficam
        destinos[destino] = _json(item)
        contagem_pasta[classe].append((nome, item["tamanho_mb"]))

    # --- arquivos soltos -------------------------------------------------
    soltos = []
    for arq in sorted(SAIDA.iterdir()):
        if not arq.is_file() or arq.name.startswith("gpu.lock") or arq.name == NOME_SOLTOS:
            continue
        pad = _pad_saida(arq.name)
        cod = bool(_citantes(pad, textos["tab"]) or _citantes(pad, textos["tests"]))
        if cod:
            classe, regen, motivo = "manter", "caro", "lido pelo código"
        else:
            classe, regen, motivo = "arquivar", REGEN_HD, MOTIVO_HIST_DATA
        script = _comando_script(arq)
        comando_solto: object = [script] if script else _comando_rodada(arq.name, textos["rodadas"])
        item = {
            "trilha": TRILHA,
            "nome": arq.name,
            "tamanho_mb": _mb(arq),
            "modificado": _modificado(arq),
            "rodadas": _citantes(_pad_rodada(arq.name), textos["rodadas"]),
            "citado_por": sorted(
                set(
                    _citantes(pad, textos["estado"])
                    + _citantes(pad, textos["tab"])
                    + _citantes(pad, textos["tests"])
                    + _citantes(pad, textos["gold"])
                )
            ),
            "comando": comando_solto,
            "regeneravel": regen,
            "classe": classe,
            "motivo": motivo,
        }
        soltos.append(item)
        contagem_solto[classe].append((arq.name, item["tamanho_mb"]))
    destinos[SAIDA / NOME_SOLTOS] = _json(soltos)

    # --- pesos em uso ----------------------------------------------------
    em_uso, faltam = _montar_em_uso()
    if faltam:
        raise SystemExit("ERRO: pastas de EM_USO que não existem: " + ", ".join(faltam))
    destinos[ARTEFATOS / TRILHA / "EM_USO.json"] = _json(em_uso)

    # --- conferência e gravação -----------------------------------------
    conflitos = [
        str(d) for d, txt in destinos.items() if d.exists() and d.read_text(encoding="utf-8") != txt
    ]
    if conflitos:
        print("PARADO: destinos que já existem e diferem (nada foi gravado):")
        for c in conflitos:
            print("  " + c)
        return 2
    # Pasta sem permissão de escrita (dona nobody): o LEIAME vai para um arquivo único.
    bloqueados: dict[str, str] = {}
    gravados = iguais = 0
    for dest, txt in sorted(destinos.items()):
        if dest.exists():
            iguais += 1
            continue
        if not os.access(dest.parent, os.W_OK):
            bloqueados[_rel(dest.parent)] = txt
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(txt, encoding="utf-8")
        gravados += 1
    arq_bloq = SAIDA / TRILHA_DIAG / "LEIAME_9001_bloqueados.json"
    if bloqueados:
        novo = _json({k: json.loads(v) for k, v in sorted(bloqueados.items())})
        if arq_bloq.exists() and arq_bloq.read_text(encoding="utf-8") != novo:
            print("PARADO: " + _rel(arq_bloq) + " existe e difere (nada mais foi gravado)")
            return 2
        if not arq_bloq.exists():
            arq_bloq.write_text(novo, encoding="utf-8")
            gravados += 1
    print(f"pastas sem permissao de escrita (LEIAME no arquivo unico): {len(bloqueados)}")

    # --- resumo ----------------------------------------------------------
    print(f"gravados: {gravados}; ja iguais: {iguais}")
    print(f"LEIAME de pasta: {len(contagem_pasta['manter']) + len(contagem_pasta['arquivar']) + len(contagem_pasta['apagar'])}")
    print(f"itens soltos: {len(soltos)}")
    for nome_grupo, grupo in (("pastas", contagem_pasta), ("soltos", contagem_solto)):
        for classe in ("manter", "arquivar", "apagar"):
            itens = grupo[classe]
            mb = sum(t for _, t in itens)
            print(f"{nome_grupo} {classe}: {len(itens)} itens, {mb} MB")
    print("REGRA EXTRA (pastas que viraram manter):")
    for nome, motivo in regra_extra:
        print(f"  {nome}: {motivo}")
    print(
        "EM_USO: em_uso={}, historico={}, total={}, artefatos/ (tablatura)={}".format(
            sum(len(b["pastas"]) for b in em_uso["em_uso"]),
            len(em_uso["historico"]["pastas"]),
            sum(len(b["pastas"]) for b in em_uso["em_uso"]) + len(em_uso["historico"]["pastas"]),
            len(
                [
                    p
                    for p in ARTEFATOS.iterdir()
                    if not p.name.startswith(".")
                    and p.name not in ARTEFATOS_FORA | {TRILHA, "riley_guitar.md", "LEIA-ME.md"}
                ]
            ),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
