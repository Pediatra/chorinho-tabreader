"""Inventário de símbolos por canal: agregação e montagem, SEM acervo.

O gate padrão não pode exigir o HD (`AGENTS.md`): estes testes montam um
``dir_simbolos`` temporário com PNGs falsos e conferem a agregação e a montagem. O que
se afere aqui é o encanamento — frequência, fração, distribuição e legibilidade da
montagem; o vocabulário real sai de `python -m tab.simbolos`, no acervo.
"""

from __future__ import annotations

import json

import cv2
import numpy as np

from tab.simbolos import (
    _ordem_montagem,
    agregar,
    montar_inventario,
    montar_montagem,
    registro_publico,
    resumir_canal,
)


def _png(caminho, largura: int = 40, altura: int = 30) -> None:
    """Grava um PNG falso de símbolo (quadrado escuro sobre fundo claro)."""
    img = np.full((altura, largura), 255, np.uint8)
    cv2.rectangle(img, (4, 4), (largura - 5, altura - 5), 0, 2)
    cv2.imwrite(str(caminho), img)


def _simbolo(hash_: str, classe: str, larguras: list[float], canal: str = "canal_x"):
    """Um `simbolo_cru` mínimo, com o que a agregação usa."""
    return {
        "hash": hash_,
        "png": f"{canal}/{hash_}.png",
        "classe": classe,
        "larguras_passo": list(larguras),
        "partes": 2,
    }


def _registro(canal: str, tokens: int, simbolos: list[dict], tab: bool = True) -> dict:
    """Um registro de quadro mínimo, no formato que `medir_video` produz."""
    return {
        "canal": canal,
        "arquivo": f"{canal}/video.mp4",
        "frac": 0.65,
        "tab": tab,
        "faixa": "meio",
        "uniformidade": 0.9,
        "passo": 20.0,
        "tokens": tokens,
        "simbolos": simbolos,
    }


def test_agregacao_conta_tokens_simbolos_e_fracao() -> None:
    """A fração é símbolos sobre tokens, e quadro sem tablatura não inventa token."""
    registros = [
        _registro("canal_x", 10, [_simbolo("aaaa", "tecnica", [0.4])]),
        _registro("canal_x", 30, [], tab=False),
    ]
    resumo = resumir_canal(registros)
    assert resumo["quadros"] == 2
    assert resumo["quadros_com_tablatura"] == 1
    assert resumo["tokens"] == 40
    assert resumo["simbolos"] == 1
    assert resumo["fracao"] == 0.025
    assert resumo["hashes_distintos"] == 1
    assert resumo["simbolos_sem_hash"] == 0


def test_hash_repetido_soma_e_guarda_a_classe_mais_comum() -> None:
    """Um hash é UM vocábulo: ocorrências somam e a classe vira a majoritária."""
    simbolos = [
        _simbolo("aaaa", "tecnica", [0.4]),
        _simbolo("aaaa", "tecnica", [0.4, 0.2]),
        _simbolo("aaaa", "junk", [0.4]),
        _simbolo("bbbb", "harmonico", [1.2]),
    ]
    resumo = resumir_canal([_registro("canal_x", 8, simbolos)])
    assert resumo["hashes"][0]["hash"] == "aaaa"
    assert resumo["hashes"][0]["n"] == 3
    assert resumo["hashes"][0]["classe"] == "tecnica"
    assert resumo["classes"] == {"tecnica": 2, "junk": 1, "harmonico": 1}
    assert resumo["larguras_passo"] == {"0.20": 1, "0.40": 3, "1.20": 1}


def test_simbolo_sem_hash_nao_quebra_a_agregacao() -> None:
    """Sem `dir_simbolos` o registro não tem hash; ele conta e é declarado."""
    sem_hash = {"classe": "tecnica", "larguras_passo": [0.3], "partes": 2}
    resumo = resumir_canal([_registro("canal_x", 5, [sem_hash])])
    assert resumo["simbolos"] == 1
    assert resumo["simbolos_sem_hash"] == 1
    assert resumo["hashes_distintos"] == 0


def test_agregar_separa_por_canal() -> None:
    """Cada canal tem o seu vocabulário: a agregação não mistura contagens."""
    registros = [
        _registro("canal_x", 10, [_simbolo("aaaa", "tecnica", [0.4])]),
        _registro("canal_y", 4, [_simbolo("cccc", "harmonico", [1.1])]),
    ]
    por_canal = agregar(registros)
    assert set(por_canal) == {"canal_x", "canal_y"}
    assert por_canal["canal_x"]["simbolos"] == 1
    assert por_canal["canal_y"]["tokens"] == 4
    assert por_canal["canal_y"]["hashes"][0]["hash"] == "cccc"


def test_montagem_gera_png_com_os_recortes(tmp_path) -> None:
    """A montagem lê os PNGs do diretório temporário e grava uma imagem maior."""
    dir_simbolos = tmp_path / "simbolos"
    (dir_simbolos / "canal_x").mkdir(parents=True)
    tamanhos = (("aaaa", 60, 40), ("bbbb", 30, 80), ("cccc", 200, 150))
    for hash_, largura, altura in tamanhos:
        _png(dir_simbolos / "canal_x" / f"{hash_}.png", largura, altura)
    simbolos = [_simbolo(h, "tecnica", [0.4]) for h, _, _ in tamanhos]
    resumo = resumir_canal([_registro("canal_x", 9, simbolos)])

    destino = tmp_path / "montagem_canal_x.png"
    montar_montagem("canal_x", resumo, str(dir_simbolos), str(destino), max_itens=10)

    assert destino.exists()
    img = cv2.imread(str(destino))
    assert img is not None, "a montagem não é uma imagem legível"
    assert img.shape[0] > 200 and img.shape[1] > 400


def test_montagem_sem_simbolos_ainda_gera_png(tmp_path) -> None:
    """Canal sem símbolo também tem montagem: ausência medida é informação."""
    resumo = resumir_canal([_registro("canal_y", 12, [], tab=False)])
    destino = tmp_path / "montagem_canal_y.png"
    montar_montagem("canal_y", resumo, str(tmp_path), str(destino))
    assert destino.exists()
    assert cv2.imread(str(destino)) is not None


def test_montagem_com_png_ausente_nao_quebra(tmp_path) -> None:
    """Hash registrado sem arquivo no disco vira célula "sem PNG", não exceção."""
    resumo = resumir_canal(
        [_registro("canal_z", 7, [_simbolo("ffff", "tecnica", [0.5])])]
    )
    destino = tmp_path / "montagem_canal_z.png"
    montar_montagem("canal_z", resumo, str(tmp_path), str(destino))
    assert cv2.imread(str(destino)) is not None


def test_montagem_limita_itens_e_diz_quantos_ficaram_de_fora(tmp_path) -> None:
    """Legibilidade vale mais que completude: corta por frequência e declara o corte."""
    dir_simbolos = tmp_path / "simbolos"
    (dir_simbolos / "canal_x").mkdir(parents=True)
    simbolos = []
    for i in range(8):
        hash_ = f"h{i:015d}"
        _png(dir_simbolos / "canal_x" / f"{hash_}.png", 40, 30)
        simbolos += [_simbolo(hash_, "tecnica", [0.4])] * (i + 1)
    resumo = resumir_canal([_registro("canal_x", 100, simbolos)])

    destino = tmp_path / "montagem_canal_x.png"
    montar_montagem("canal_x", resumo, str(dir_simbolos), str(destino), max_itens=3)
    img = cv2.imread(str(destino))
    assert img is not None
    # 3 itens em UMA linha: a montagem truncada é mais baixa que a completa.
    completo = tmp_path / "montagem_completa.png"
    montar_montagem("canal_x", resumo, str(dir_simbolos), str(completo), max_itens=8)
    assert img.shape[0] < cv2.imread(str(completo)).shape[0]


def test_inventario_json_e_serializavel_com_os_campos_pedidos() -> None:
    """O JSON final traz, por canal, tokens, símbolos, fração e distribuições."""
    registros = [
        _registro("canal_x", 10, [_simbolo("aaaa", "tecnica", [0.4])]),
        _registro("canal_y", 4, []),
    ]
    por_canal = agregar(registros)
    amostra = {
        "canal_x": [{"arquivo": "canal_x/video.mp4", "tokens": 10, "n_simbolos": 1}],
        "canal_y": [{"arquivo": "canal_y/video.mp4", "tokens": 4, "n_simbolos": 0}],
    }
    inventario = montar_inventario(
        por_canal, amostra, "artefatos/oficial_2/glifo_sint.pt", "/acervo", (0.65, 0.85)
    )
    volta = json.loads(json.dumps(inventario, ensure_ascii=False))
    assert set(volta["por_canal"]) == {"canal_x", "canal_y"}
    for canal in ("canal_x", "canal_y"):
        for campo in (
            "tokens",
            "simbolos",
            "fracao",
            "classes",
            "larguras_passo",
            "hashes",
            "hashes_distintos",
        ):
            assert campo in volta["por_canal"][canal], campo
    assert volta["resumo"]["tokens"] == 14
    assert volta["resumo"]["simbolos"] == 1
    assert volta["fracoes"] == [0.65, 0.85]
    assert volta["amostra"]["canal_x"][0]["arquivo"] == "canal_x/video.mp4"


def test_passo_fora_da_faixa_e_declarado_e_nao_filtrado() -> None:
    """Painel suspeito (passo fora de 14-45 px) é medido e rotulado, não descartado.

    O portão de painel escolhe violão e piano (`ESTADO.md`); sem este rótulo, símbolo de
    painel errado entraria como se fosse tablatura.
    """
    bom = _registro("canal_x", 10, [_simbolo("aaaa", "tecnica", [0.4])])
    bom["passo"] = 20.6
    ruim = _registro("canal_x", 18, [_simbolo("bbbb", "harmonico", [0.3])])
    ruim["passo"] = 51.4
    resumo = resumir_canal([bom, ruim])
    assert resumo["simbolos"] == 2, "símbolo de painel suspeito foi filtrado"
    assert resumo["quadros_passo_plausivel"] == 1
    assert resumo["simbolos_passo_plausivel"] == 1
    assert resumo["passo_mediano"] == 36.0
    por_hash = {h["hash"]: h for h in resumo["hashes"]}
    assert por_hash["aaaa"]["n_passo_plausivel"] == 1
    assert por_hash["bbbb"]["n_passo_plausivel"] == 0


def test_ordem_da_montagem_põe_junk_no_fim() -> None:
    """Fragmento de barline/corda (junk) é muito e único: não pode dominar a imagem."""
    junk = {"hash": "aaaa", "n": 50, "n_passo_plausivel": 50, "classe": "junk"}
    simbolo = {"hash": "bbbb", "n": 1, "n_passo_plausivel": 1, "classe": "tecnica"}
    assert sorted([junk, simbolo], key=_ordem_montagem)[0]["hash"] == "bbbb"
    # Dentro da mesma classe, painel plausível e frequência decidem.
    raro = {"hash": "cccc", "n": 9, "n_passo_plausivel": 0, "classe": "harmonico"}
    comum = {"hash": "dddd", "n": 1, "n_passo_plausivel": 3, "classe": "harmonico"}
    assert sorted([raro, comum], key=_ordem_montagem)[0]["hash"] == "dddd"


def test_registro_publico_nao_relativiza_caminho_ja_relativo() -> None:
    """`medir_video` já grava caminho relativo; relativizar de novo daria `../app/...`."""
    r = _registro("canal_x", 3, [])
    assert registro_publico(r, "/acervo")["arquivo"] == "canal_x/video.mp4"
    r["arquivo"] = "/acervo/canal_x/video.mp4"
    assert registro_publico(r, "/acervo")["arquivo"] == "canal_x/video.mp4"


def test_canal_da_amostra_sem_registro_aparece_zerado() -> None:
    """Canal amostrado sem nenhum registro não some do inventário."""
    inventario = montar_inventario({}, {"canal_vazio": []}, "m.pt", "/acervo", (0.65,))
    assert inventario["por_canal"]["canal_vazio"]["tokens"] == 0
    assert inventario["por_canal"]["canal_vazio"]["fracao"] == 0.0
