"""Gabarito do braço (M3b): amostra, conversão de clique, trastes, respostas e servidor."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import pytest

from tab.cache import ModoCache, caminho_do_quadro, pasta_do_video
from tab.caminhos import CENSO_MAOS
from tab.maos_braco_gabarito import (
    ARQUIVO_MVP,
    CAMPOS_PARTES,
    CANAL_MVP,
    PAGINA,
    acrescentar,
    acrescentar_gabarito,
    acrescentar_indice,
    amostrar_quadros,
    aplicar_acao,
    completar_campos,
    completos,
    converter_clique,
    criar_servidor,
    entrada_do_indice,
    gabarito_novo,
    ler_pares,
    mesclar_gabarito,
    numerar_trastes,
    ordenar_trastes,
    partes_completas,
    partes_faltando,
    preparar,
    proximo_id,
    registro_completo,
    registro_em_branco,
    resumo,
    validar_no_quadro,
)
from tab.maos_braco_regra import s_do_traste

DIMENSOES = (1920, 1080)


def _maos(n: int) -> list[dict]:
    """Lista de mãos (só o número importa para a amostra).

    Args:
        n: quantas mãos.

    Returns:
        Lista com ``n`` entradas fictícias.
    """
    return [{"lado": "L"} for _ in range(n)]


def _censo_sintetico(canais: int = 12, videos_por_canal: int = 5) -> list[dict]:
    """Censo com vários canais; o canal do MVP tem o vídeo do MVP com quadros tab.

    Args:
        canais: quantos canais além do MVP.
        videos_por_canal: vídeos por canal.

    Returns:
        Linhas no formato do censo (``chave``, ``arquivo``, ``canal``, ``quadros``).
    """
    linhas = []
    nomes = [f"canal {k:02d}" for k in range(canais)] + [CANAL_MVP]
    for canal in nomes:
        n_videos = videos_por_canal + (2 if canal == CANAL_MVP else 0)
        for v in range(n_videos):
            arquivo = f"{canal}/video {v}.mp4"
            if canal == CANAL_MVP and v == 0:
                arquivo = ARQUIVO_MVP
            quadros = []
            for i in range(12):
                tab = canal == CANAL_MVP and i >= 4
                quadros.append(
                    {
                        "i": i,
                        "t": 10.0 + i,
                        "tab": tab,
                        "rect": None,
                        "maos": _maos(2 if i % 3 else 1),
                        "rostos": [],
                    }
                )
            linhas.append(
                {
                    "chave": f"{arquivo}|1|2",
                    "arquivo": arquivo,
                    "canal": canal,
                    "altura": 1080,
                    "largura": 1920,
                    "quadros": quadros,
                    "faltam": [],
                }
            )
    return linhas


# ---------------------------------------------------------------------------------
# Amostra
# ---------------------------------------------------------------------------------


def test_amostra_tem_20_quadros_de_8_canais_com_videos_distintos() -> None:
    """20 quadros, 8 canais, e um vídeo não se repete dentro do canal."""
    amostra = amostrar_quadros(_censo_sintetico())
    assert len(amostra) == 20
    assert len({a["canal"] for a in amostra}) == 8
    assert len({a["chave"] for a in amostra}) == 20
    assert [a["id"] for a in amostra] == [f"q{k:02d}" for k in range(1, 21)]


def test_amostra_inclui_mvp_com_quadro_com_tab() -> None:
    """Exatamente um quadro do MVP, e ele tem tab (controle)."""
    amostra = amostrar_quadros(_censo_sintetico())
    mvp = [a for a in amostra if a["mvp"]]
    assert len(mvp) == 1
    assert mvp[0]["arquivo"] == ARQUIVO_MVP
    assert mvp[0]["tab"] is True


def test_amostra_e_reproduzivel_pela_semente() -> None:
    """Mesma semente, mesma amostra; outra semente muda o sorteio."""
    censo = _censo_sintetico()
    assert amostrar_quadros(censo, semente=7) == amostrar_quadros(censo, semente=7)
    assert amostrar_quadros(censo, semente=7) != amostrar_quadros(censo, semente=8)


def test_amostra_recusa_canal_do_mvp_fora_dos_maiores() -> None:
    """Se o canal do MVP não couber nos canais escolhidos, a amostra recusa."""
    censo = _censo_sintetico(canais=12, videos_por_canal=5)
    for linha in censo:
        if linha["canal"] == CANAL_MVP:
            linha["quadros"] = []  # sem quadros elegíveis: o canal some
    with pytest.raises(ValueError):
        amostrar_quadros(censo)


# ---------------------------------------------------------------------------------
# Coordenadas
# ---------------------------------------------------------------------------------


def test_converter_clique_divide_pela_escala() -> None:
    """x_quadro = x_img / escala; a imagem mostrada é metade da original."""
    assert converter_clique([300, 150], 0.5) == [600.0, 300.0]


def test_converter_clique_recusa_escala_invalida() -> None:
    """Escala zero, negativa, NaN, booleana ou texto são recusadas."""
    for escala in (0, -1, float("nan"), True, "0.5"):
        with pytest.raises(ValueError):
            converter_clique([10, 10], escala)


def test_clique_fora_do_quadro_e_recusado() -> None:
    """Ponto além da largura ou com coordenada negativa não entra no gabarito."""
    validar_no_quadro([1919.0, 1079.0], DIMENSOES)
    with pytest.raises(ValueError):
        validar_no_quadro([1921.0, 10.0], DIMENSOES)
    with pytest.raises(ValueError):
        validar_no_quadro([-5.0, 10.0], DIMENSOES)


# ---------------------------------------------------------------------------------
# Trastes e numeração
# ---------------------------------------------------------------------------------


def test_trastes_com_nut_numeram_do_mais_perto_para_fora() -> None:
    """Com o nut visível, o traste mais perto do nut é o 1, mesmo clicado fora de ordem."""
    registro = registro_em_branco("c")
    registro["nut"] = [100.0, 500.0]
    registro["trastes"] = [[400.0, 500.0], [160.0, 500.0], [260.0, 500.0]]
    numeros = [(n["numero"], n["ponto"][0]) for n in numerar_trastes(registro)]
    assert numeros == [(1, 160.0), (2, 260.0), (3, 400.0)]


def test_trastes_sem_nut_usam_referencia_e_espacamento() -> None:
    """Nut fora: a referência fixa um traste, o espaçamento fixa o sentido.

    Os trastes ficam mais juntos para o corpo, então o lado do nut tem intervalos
    maiores. Aqui os intervalos de x=0 a x=310 são 60, 70, 80, 100: crescem para a
    direita, logo o nut está em x=310. Com a referência (130 é o traste 3), a
    numeração sai 310=1, 210=2, 130=3, 60=4, 0=5.
    """
    trastes = [[310.0, 0.0], [0.0, 0.0], [130.0, 0.0], [60.0, 0.0], [210.0, 0.0]]
    registro = registro_em_branco("c")
    registro["nut"] = "fora"
    registro["trastes"] = trastes
    registro["traste_referencia"] = {"ponto": [130.0, 0.0], "numero": 3}
    numeros = {n["ponto"][0]: n["numero"] for n in numerar_trastes(registro)}
    assert numeros == {310.0: 1, 210.0: 2, 130.0: 3, 60.0: 4, 0.0: 5}


def test_trastes_sem_nut_e_sem_referencia_nao_numeram() -> None:
    """Sem nut visível e sem referência, nenhum traste recebe número."""
    registro = registro_em_branco("c")
    registro["nut"] = "fora"
    registro["trastes"] = [[0.0, 0.0], [100.0, 0.0]]
    assert all(n["numero"] is None for n in numerar_trastes(registro))


def test_referencia_abaixo_de_1_vira_none() -> None:
    """Quando a referência empurra os números para zero ou menos, esses saem sem número."""
    registro = registro_em_branco("c")
    registro["nut"] = "fora"
    registro["trastes"] = [[0.0, 0.0], [100.0, 0.0], [180.0, 0.0]]
    registro["traste_referencia"] = {"ponto": [100.0, 0.0], "numero": 1}
    numeros = [n["numero"] for n in numerar_trastes(registro)]
    assert None in numeros
    assert 1 in numeros


def test_ordenar_trastes_sem_nut_e_um_so() -> None:
    """Um traste só sai como está."""
    assert ordenar_trastes([[5.0, 6.0]], None) == [[5.0, 6.0]]


# ---------------------------------------------------------------------------------
# Completo
# ---------------------------------------------------------------------------------


def _completo(braco: str = "sim") -> dict:
    """Registro com cordas, nut e 2 trastes marcados.

    Args:
        braco: valor de ``braco``.

    Returns:
        Registro pronto para contar como completo (quando ``braco`` é sim/parcial).
    """
    registro = registro_em_branco("c")
    registro["braco"] = braco
    registro["corda1"] = [[100.0, 200.0], [1800.0, 260.0]]
    registro["corda6"] = [[100.0, 400.0], [1800.0, 460.0]]
    registro["nut"] = [120.0, 300.0]
    registro["trastes"] = [[300.0, 300.0], [500.0, 300.0]]
    return registro


def test_completo_com_braco_sim_e_tudo_marcado() -> None:
    """Braço sim, cordas, nut e 2 trastes: completo."""
    assert registro_completo(_completo("sim"))
    assert registro_completo(_completo("parcial"))


def test_braco_nao_ou_interrogacao_e_completo_sem_geometria() -> None:
    """Braço não aparece (ou ?): basta essa resposta."""
    assert registro_completo(registro_em_branco("c") | {"braco": "nao"})
    assert registro_completo(registro_em_branco("c") | {"braco": "?"})


def test_incompleto_sem_braco_ou_sem_uma_corda_ou_sem_trastes() -> None:
    """Falta uma coisa de cada vez: não está completo."""
    assert not registro_completo(registro_em_branco("c"))
    reg = _completo()
    reg["corda6"] = [[100.0, 400.0]]
    assert not registro_completo(reg)
    reg = _completo()
    reg["trastes"] = [[300.0, 300.0]]
    assert not registro_completo(reg)


def test_nut_fora_precisa_de_referencia() -> None:
    """Nut fora conta como completo só com ``traste_referencia``."""
    reg = _completo()
    reg["nut"] = "fora"
    assert not registro_completo(reg)
    reg["traste_referencia"] = {"ponto": [300.0, 300.0], "numero": 4}
    assert registro_completo(reg)


# ---------------------------------------------------------------------------------
# Aplicar ações
# ---------------------------------------------------------------------------------


def _gabarito_com(ids: list[str]) -> dict:
    """Gabarito sem respostas para os ids dados.

    Args:
        ids: ids dos quadros.

    Returns:
        Gabarito novo com essas amostras.
    """
    indice = [{"id": i, "chave": f"v{i}"} for i in ids]
    return gabarito_novo(indice, semente=1)


def test_dois_cliques_na_corda_fazem_o_par_e_terceiro_comeca_outro() -> None:
    """Corda 1: dois cliques formam o par; o terceiro começa outro par."""
    g = _gabarito_com(["q01"])
    for ponto in ([100, 200], [1800, 260]):
        aplicar_acao(
            g,
            "q01",
            {"acao": "clique", "modo": "corda1", "ponto_img": ponto, "escala": 1.0},
            DIMENSOES,
            "t",
        )
    assert g["quadros"]["q01"]["corda1"] == [[100.0, 200.0], [1800.0, 260.0]]
    aplicar_acao(
        g,
        "q01",
        {"acao": "clique", "modo": "corda1", "ponto_img": [50, 50], "escala": 1.0},
        DIMENSOES,
        "t",
    )
    assert g["quadros"]["q01"]["corda1"] == [[50.0, 50.0]]


def test_clique_comum_sempre_adiciona_mesmo_perto_de_outro_traste() -> None:
    """Trastes juntos (perto do corpo): clique a 2 px de outro adiciona, não remove."""
    g = _gabarito_com(["q01"])
    clique = {"acao": "clique", "modo": "trastes", "escala": 1.0}
    aplicar_acao(g, "q01", clique | {"ponto_img": [400, 300]}, DIMENSOES, "t")
    aplicar_acao(g, "q01", clique | {"ponto_img": [402, 301]}, DIMENSOES, "t")
    assert len(g["quadros"]["q01"]["trastes"]) == 2


def test_remover_tira_o_traste_mais_perto() -> None:
    """Com ``remover``, sai o traste marcado mais perto; longe de todos, nada muda."""
    g = _gabarito_com(["q01"])
    clique = {"acao": "clique", "modo": "trastes", "escala": 1.0}
    aplicar_acao(g, "q01", clique | {"ponto_img": [400, 300]}, DIMENSOES, "t")
    aplicar_acao(g, "q01", clique | {"ponto_img": [600, 300]}, DIMENSOES, "t")
    tirar = clique | {"remover": True}
    aplicar_acao(g, "q01", tirar | {"ponto_img": [402, 301]}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["trastes"] == [[600.0, 300.0]]
    aplicar_acao(g, "q01", tirar | {"ponto_img": [100, 100]}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["trastes"] == [[600.0, 300.0]]


def test_desfazer_restaura_o_clique_anterior() -> None:
    """Desfazer volta ao estado antes do último clique, até acabar a pilha."""
    g = _gabarito_com(["q01"])
    aplicar_acao(
        g,
        "q01",
        {"acao": "clique", "modo": "nut", "ponto_img": [10, 10], "escala": 1.0},
        DIMENSOES,
        "t",
    )
    aplicar_acao(
        g,
        "q01",
        {"acao": "clique", "modo": "nut", "ponto_img": [20, 20], "escala": 1.0},
        DIMENSOES,
        "t",
    )
    aplicar_acao(g, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["nut"] == [10.0, 10.0]
    aplicar_acao(g, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["nut"] is None
    with pytest.raises(ValueError):
        aplicar_acao(g, "q01", {"acao": "desfazer"}, DIMENSOES, "t")


def test_limpar_apaga_as_marcas_e_o_desfazer_traz_de_volta() -> None:
    """Limpar zera cordas, nut e trastes de uma vez; um desfazer restaura tudo."""
    g = _gabarito_com(["q01"])
    aplicar_acao(
        g,
        "q01",
        {"acao": "clique", "modo": "nut", "ponto_img": [10, 10], "escala": 1.0},
        DIMENSOES,
        "t",
    )
    g["quadros"]["q01"]["obs"] = "nota"
    aplicar_acao(g, "q01", {"acao": "limpar"}, DIMENSOES, "t")
    registro = g["quadros"]["q01"]
    assert registro["nut"] is None
    assert registro["trastes"] == []
    assert registro["corda1"] is None
    assert registro["obs"] == "nota"
    aplicar_acao(g, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["nut"] == [10.0, 10.0]


def test_mover_arrasta_ponta_de_corda_nut_e_traste() -> None:
    """Mover troca só o ponto escolhido; o desfazer volta; traste previsto vira do dono."""
    g = _gabarito_com(["q01"])
    clique = {"acao": "clique", "escala": 1.0}
    aplicar_acao(
        g, "q01", clique | {"modo": "corda1", "ponto_img": [10, 10]}, DIMENSOES, "t"
    )
    aplicar_acao(
        g, "q01", clique | {"modo": "corda1", "ponto_img": [300, 20]}, DIMENSOES, "t"
    )
    aplicar_acao(
        g, "q01", clique | {"modo": "nut", "ponto_img": [5, 5]}, DIMENSOES, "t"
    )
    aplicar_acao(
        g, "q01", clique | {"modo": "trastes", "ponto_img": [50, 12]}, DIMENSOES, "t"
    )
    g["quadros"]["q01"]["trastes_previstos"] = [[50.0, 12.0]]
    mover = {"acao": "mover", "escala": 1.0}
    aplicar_acao(
        g,
        "q01",
        mover | {"campo": "corda1", "indice": 1, "ponto_img": [310, 30]},
        DIMENSOES,
        "t",
    )
    aplicar_acao(
        g, "q01", mover | {"campo": "nut", "ponto_img": [6, 7]}, DIMENSOES, "t"
    )
    aplicar_acao(
        g,
        "q01",
        mover | {"campo": "trastes", "indice": 0, "ponto_img": [55, 13]},
        DIMENSOES,
        "t",
    )
    registro = g["quadros"]["q01"]
    assert registro["corda1"] == [[10.0, 10.0], [310.0, 30.0]]
    assert registro["nut"] == [6.0, 7.0]
    assert registro["trastes"] == [[55.0, 13.0]]
    assert registro["trastes_previstos"] is None
    aplicar_acao(g, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["trastes"] == [[50.0, 12.0]]
    with pytest.raises(ValueError):
        aplicar_acao(
            g,
            "q01",
            mover | {"campo": "corda6", "indice": 0, "ponto_img": [1, 1]},
            DIMENSOES,
            "t",
        )


def test_braco_nao_limpa_a_geometria_e_volta_sem_ela() -> None:
    """Braço "nao" zera cordas, nut, trastes e referência."""
    g = _gabarito_com(["q01"])
    g["quadros"]["q01"] = _completo()
    aplicar_acao(g, "q01", {"campo": "braco", "valor": "nao"}, DIMENSOES, "t")
    reg = g["quadros"]["q01"]
    assert reg["braco"] == "nao"
    assert reg["corda1"] is None and reg["nut"] is None and reg["trastes"] is None
    aplicar_acao(g, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["braco"] == "sim"


def test_referencia_precisa_ser_traste_marcado_e_numero_valido() -> None:
    """Referência fora dos trastes, ou número 0 / 31 / bool / texto: recusada."""
    g = _gabarito_com(["q01"])
    g["quadros"]["q01"] = _completo()
    g["quadros"]["q01"]["nut"] = "fora"
    casos = [
        {"ponto": [1.0, 1.0], "numero": 4},
        {"ponto": [300.0, 300.0], "numero": 0},
        {"ponto": [300.0, 300.0], "numero": 31},
        {"ponto": [300.0, 300.0], "numero": True},
        {"ponto": [300.0, 300.0], "numero": "4"},
        {"ponto": [300.0, 300.0]},
    ]
    for valor in casos:
        with pytest.raises(ValueError):
            aplicar_acao(
                g, "q01", {"campo": "traste_referencia", "valor": valor}, DIMENSOES, "t"
            )
    aplicar_acao(
        g,
        "q01",
        {"campo": "traste_referencia", "valor": {"ponto": [300.0, 300.0], "numero": 4}},
        DIMENSOES,
        "t",
    )
    assert g["quadros"]["q01"]["traste_referencia"]["numero"] == 4


def test_remover_traste_de_referencia_limpa_a_referencia() -> None:
    """Se o traste da referência é removido pelo clique, a referência some junto."""
    g = _gabarito_com(["q01"])
    g["quadros"]["q01"] = _completo()
    g["quadros"]["q01"]["nut"] = "fora"
    aplicar_acao(
        g,
        "q01",
        {"campo": "traste_referencia", "valor": {"ponto": [300.0, 300.0], "numero": 4}},
        DIMENSOES,
        "t",
    )
    aplicar_acao(
        g,
        "q01",
        {
            "acao": "clique",
            "modo": "trastes",
            "remover": True,
            "ponto_img": [300, 300],
            "escala": 1.0,
        },
        DIMENSOES,
        "t",
    )
    assert g["quadros"]["q01"]["traste_referencia"] is None


def test_entrada_invalida_nao_muda_o_gabarito() -> None:
    """Valor inválido recusa e deixa o registro exatamente como estava."""
    g = _gabarito_com(["q01"])
    antes = copy.deepcopy(g)
    invalidas = [
        {"campo": "braco", "valor": "talvez"},
        {"campo": "nut", "valor": "perto"},
        {"campo": "obs", "valor": "x" * 501},
        {"campo": "obs", "valor": 7},
        {"campo": "sei_la", "valor": 1},
        {"acao": "clique", "modo": "corda9", "ponto_img": [1, 1], "escala": 1.0},
        {"acao": "clique", "modo": "nut", "ponto_img": [1, 1], "escala": 0},
        {"acao": "clique", "modo": "nut", "ponto_img": [1, 1, 1], "escala": 1.0},
        {"acao": "clique", "modo": "nut", "ponto_img": [9999, 1], "escala": 1.0},
        {"acao": "pular"},
    ]
    for dados in invalidas:
        with pytest.raises(ValueError):
            aplicar_acao(g, "q01", dados, DIMENSOES, "t")
        assert g == antes


def test_obs_guarda_texto_e_vazio_vira_null() -> None:
    """Observação é texto aparado; vazia volta a null."""
    g = _gabarito_com(["q01"])
    aplicar_acao(g, "q01", {"campo": "obs", "valor": "  pestana  "}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["obs"] == "pestana"
    aplicar_acao(g, "q01", {"campo": "obs", "valor": "   "}, DIMENSOES, "t")
    assert g["quadros"]["q01"]["obs"] is None


# ---------------------------------------------------------------------------------
# Mesclagem
# ---------------------------------------------------------------------------------


def test_mesclagem_preserva_respostas_do_disco() -> None:
    """Um quadro respondido no disco continua respondido após nova amostra."""
    antigo = _gabarito_com(["q01", "q02"])
    antigo["quadros"]["q01"]["braco"] = "sim"
    antigo["quadros"]["q01"]["respondido_em"] = "2026-10-12T10:00:00"
    novo = _gabarito_com(["q01", "q02"])
    mesclado = mesclar_gabarito(novo, antigo)
    assert mesclado["quadros"]["q01"]["braco"] == "sim"
    assert mesclado["quadros"]["q02"]["braco"] is None


def test_mesclagem_recusa_resposta_de_outro_video() -> None:
    """Se a chave do quadro mudou e há resposta, não mescla em silêncio."""
    antigo = _gabarito_com(["q01"])
    antigo["quadros"]["q01"]["braco"] = "sim"
    antigo["quadros"]["q01"]["respondido_em"] = "2026-10-12T10:00:00"
    novo = _gabarito_com(["q01"])
    novo["quadros"]["q01"]["chave"] = "outro"
    with pytest.raises(ValueError):
        mesclar_gabarito(novo, antigo)


def test_mesclagem_recusa_formato_antigo() -> None:
    """Gabarito de outro formato não é reaproveitado."""
    antigo = {"formato": 3, "quadros": {}}
    with pytest.raises(ValueError):
        mesclar_gabarito(_gabarito_com(["q01"]), antigo)


def test_completos_e_resumo_contam_os_quadros_prontos() -> None:
    """O resumo mostra quantos quadros estão completos, de quantos."""
    g = _gabarito_com(["q01", "q02"])
    g["quadros"]["q01"] = _completo()
    indice = [{"id": "q01"}, {"id": "q02"}]
    assert completos(g) == ["q01"]
    r = resumo(g, indice)
    assert r["concluidos"] == 1 and r["total"] == 2
    assert r["quadros"]["q01"]["completo"] is True


# ---------------------------------------------------------------------------------
# Preparar com cache sintético
# ---------------------------------------------------------------------------------


def _cache_e_censo(tmp_path: Path, censo: list[dict]) -> tuple[Path, Path]:
    """Grava o censo e um cache com um PNG pequeno por quadro (no caminho real).

    Args:
        tmp_path: pasta de teste.
        censo: linhas do censo sintético.

    Returns:
        ``(caminho_do_censo, raiz_do_cache)``.
    """
    raiz = tmp_path / "cache"
    modo = ModoCache(raiz=raiz)
    for linha in censo:
        pasta = pasta_do_video(linha["chave"], modo)
        pasta.mkdir(parents=True, exist_ok=True)
        for q in linha["quadros"]:
            img = np.full((60, 80, 3), q["i"] * 10, dtype=np.uint8)
            cv2.imwrite(
                str(caminho_do_quadro(pasta, f"presenca_{q['i']:02d}", "png")), img
            )
    arq = tmp_path / "censo.jsonl"
    arq.write_text("\n".join(json.dumps(x) for x in censo) + "\n", encoding="utf-8")
    return arq, raiz


def test_preparar_copia_quadros_grava_indice_e_gabarito(tmp_path: Path) -> None:
    """Preparar: 20 PNG copiados, indice com tamanho, gabarito com respostas null."""
    arq, raiz = _cache_e_censo(tmp_path, _censo_sintetico())
    pasta = tmp_path / "m3b"
    ouro = tmp_path / "braco.json"
    total = preparar(arq, raiz, pasta, ouro, semente=5)
    assert total == 20
    indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))["quadros"]
    assert len(indice) == 20
    assert all((pasta / q["png"]).is_file() for q in indice)
    assert indice[0]["largura"] == 80 and indice[0]["altura"] == 60
    gabarito = json.loads(ouro.read_text(encoding="utf-8"))
    assert gabarito["formato"] == 1
    assert all(reg["braco"] is None for reg in gabarito["quadros"].values())


def test_preparar_nao_apaga_respostas_ao_rodar_de_novo(tmp_path: Path) -> None:
    """Segunda execução com a mesma semente mantém as respostas já dadas."""
    arq, raiz = _cache_e_censo(tmp_path, _censo_sintetico())
    pasta = tmp_path / "m3b"
    ouro = tmp_path / "braco.json"
    preparar(arq, raiz, pasta, ouro, semente=5)
    gabarito = json.loads(ouro.read_text(encoding="utf-8"))
    gabarito["quadros"]["q01"]["braco"] = "parcial"
    gabarito["quadros"]["q01"]["respondido_em"] = "2026-10-12T10:00:00"
    ouro.write_text(json.dumps(gabarito), encoding="utf-8")
    preparar(arq, raiz, pasta, ouro, semente=5)
    again = json.loads(ouro.read_text(encoding="utf-8"))
    assert again["quadros"]["q01"]["braco"] == "parcial"


def test_preparar_recusa_quadro_fora_do_cache(tmp_path: Path) -> None:
    """Quadro sorteado que não está no cache é erro explícito."""
    arq, raiz = _cache_e_censo(tmp_path, _censo_sintetico())
    for arquivo in raiz.rglob("presenca_*.png"):
        arquivo.unlink()
    with pytest.raises(FileNotFoundError):
        preparar(arq, raiz, tmp_path / "m3b", tmp_path / "braco.json", semente=5)


# ---------------------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------------------


def _post(porta: int, corpo: dict | str) -> tuple[int, dict]:
    """POST no servidor de teste; devolve o código e o JSON da resposta.

    Args:
        porta: porta local do servidor.
        corpo: objeto a enviar (ou texto cru, para testar JSON inválido).

    Returns:
        ``(código HTTP, corpo decodificado)``.
    """
    dados = corpo if isinstance(corpo, str) else json.dumps(corpo)
    pedido = urllib.request.Request(
        f"http://127.0.0.1:{porta}/responder",
        data=dados.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read())


def test_servidor_grava_e_recusa_entrada_ruim(tmp_path: Path) -> None:
    """POST válido grava no arquivo; POST inválido responde 400 e não grava."""
    arq, raiz = _cache_e_censo(tmp_path, _censo_sintetico())
    pasta = tmp_path / "m3b"
    ouro = tmp_path / "braco.json"
    preparar(arq, raiz, pasta, ouro, semente=5)
    servidor = criar_servidor(pasta, ouro, porta=0, host="127.0.0.1")
    porta = servidor.server_address[1]
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        codigo, dados = _post(
            porta,
            {"quadro": "q01", "campo": "braco", "valor": "sim"},
        )
        assert codigo == 200 and dados["ok"] is True
        codigo, dados = _post(
            porta,
            {
                "quadro": "q01",
                "acao": "clique",
                "modo": "nut",
                "ponto_img": [20, 20],
                "escala": 0.5,
            },
        )
        assert codigo == 200
        assert dados["quadros"]["q01"]["registro"]["nut"] == [40.0, 40.0]
        gravado_nut = json.loads(ouro.read_text(encoding="utf-8"))["quadros"]["q01"][
            "nut"
        ]
        assert gravado_nut == [40.0, 40.0]
        codigo, _ = _post(porta, {"quadro": "q99", "campo": "braco", "valor": "sim"})
        assert codigo == 400
        codigo, _ = _post(porta, {"quadro": "q01", "campo": "braco", "valor": "x"})
        assert codigo == 400
        codigo, _ = _post(porta, "{não é json")
        assert codigo == 400
        codigo, _ = _post(porta, {"quadro": "q01", "acao": "clique", "modo": "nut"})
        assert codigo == 400
        gravado = json.loads(ouro.read_text(encoding="utf-8"))
        assert gravado["quadros"]["q01"]["braco"] == "sim"
        assert gravado["quadros"]["q02"]["braco"] is None
    finally:
        servidor.shutdown()
        servidor.server_close()


@pytest.mark.integration
def test_amostra_real_do_censo_tem_20_quadros_com_mvp() -> None:
    """Sobre o censo de verdade: 20 quadros, 8 canais e o MVP com tab."""
    if not CENSO_MAOS.exists():
        pytest.skip("sem censo de mãos neste checkout")
    linhas = [
        json.loads(x) for x in CENSO_MAOS.read_text(encoding="utf-8").splitlines()
    ]
    amostra = amostrar_quadros(linhas)
    assert len(amostra) == 20
    assert len({a["canal"] for a in amostra}) == 8
    assert any(a["mvp"] and a["tab"] for a in amostra)


# ---------------------------------------------------------------------------------
# Acrescentar quadros depois da amostra
# ---------------------------------------------------------------------------------


def _registros_em_bytes(gabarito: dict, ids: list[str]) -> list[str]:
    """Registros serializados como o ``gravar_atomico`` faz, para comparar bytes.

    Args:
        gabarito: gabarito com ``quadros``.
        ids: ids a serializar, na ordem.

    Returns:
        Um texto JSON por registro.
    """
    return [
        json.dumps(gabarito["quadros"][i], ensure_ascii=False, indent=1) for i in ids
    ]


def _indice_com(n: int) -> dict:
    """Índice fictício com ``n`` quadros ``q01``..``qNN`` de vídeos distintos.

    Args:
        n: quantos quadros.

    Returns:
        Dicionário no formato do ``indice.json``.
    """
    return {
        "semente": 1,
        "quadros": [
            {
                "id": f"q{k:02d}",
                "chave": f"canal/v{k}.mp4|10|20",
                "arquivo": f"canal/v{k}.mp4",
                "canal": "canal",
                "indice": k,
                "t": 1.0 + k,
                "tab": True,
                "n_maos": 1,
                "mvp": False,
                "png": f"quadros/q{k:02d}.png",
                "largura": 320,
                "altura": 240,
            }
            for k in range(1, n + 1)
        ],
    }


def test_proximo_id_continua_a_numeracao() -> None:
    """O id novo vem depois do maior existente, com dois dígitos."""
    assert proximo_id(_indice_com(20)["quadros"]) == "q21"
    assert proximo_id([]) == "q01"


def test_acrescentar_gabarito_nao_mexe_nos_registros_existentes() -> None:
    """Os registros q01 a q20 ficam iguais, byte a byte; o novo entra em branco."""
    ids = [f"q{k:02d}" for k in range(1, 21)]
    gabarito = _gabarito_com(ids)
    gabarito["quadros"]["q07"]["braco"] = "sim"
    gabarito["quadros"]["q07"]["respondido_em"] = "2026-10-12T10:00:00"
    antes = _registros_em_bytes(gabarito, ids)
    novo = acrescentar_gabarito(gabarito, "q21", "canal/x.mp4|1|2")
    assert _registros_em_bytes(novo, ids) == antes
    assert novo["quadros"]["q21"] == registro_em_branco("canal/x.mp4|1|2")
    assert list(gabarito["quadros"]) == ids


def test_acrescentar_gabarito_recusa_id_repetido() -> None:
    """Um id que já tem registro não é sobrescrito."""
    with pytest.raises(ValueError):
        acrescentar_gabarito(_gabarito_com(["q01"]), "q01", "x")


def test_acrescentar_indice_recusa_id_e_par_repetidos() -> None:
    """Id repetido, ou o mesmo vídeo no mesmo instante, não entram; nada muda."""
    indice = _indice_com(20)
    antes = copy.deepcopy(indice)
    com_id_repetido = entrada_do_indice("q01", "c|1|2", "c/n.mp4", 5.0, None, 320, 240)
    with pytest.raises(ValueError):
        acrescentar_indice(indice, [com_id_repetido])
    mesmo_par = entrada_do_indice(
        "q21", indice["quadros"][0]["chave"], "canal/v1.mp4", 2.0, None, 320, 240
    )
    with pytest.raises(ValueError):
        acrescentar_indice(indice, [mesmo_par])
    assert indice == antes


def test_acrescentar_indice_anexa_no_fim_e_preserva_os_antigos() -> None:
    """Os itens antigos ficam como estavam; o novo traz os campos não medidos como None."""
    indice = _indice_com(20)
    antes = copy.deepcopy(indice["quadros"])
    nova = entrada_do_indice("q21", "novo|1|2", "novo/a.mp4", 3.5, True, 1920, 1080)
    feito = acrescentar_indice(indice, [nova])
    assert feito["quadros"][:20] == antes
    item = feito["quadros"][20]
    assert item["id"] == "q21"
    assert item["canal"] == "novo"
    assert item["indice"] is None
    assert item["n_maos"] is None
    assert item["mvp"] is False
    assert item["png"] == "quadros/q21.png"


def test_ler_pares_recusa_quantidades_diferentes_e_instante_invalido() -> None:
    """``--video`` e ``--t`` precisam bater; instante booleano ou negativo é recusado."""
    with pytest.raises(ValueError):
        ler_pares(["a.mp4", "b.mp4"], [1.0])
    with pytest.raises(ValueError):
        ler_pares(["a.mp4"], [True])
    with pytest.raises(ValueError):
        ler_pares(["a.mp4"], [-1.0])
    assert ler_pares(["a.mp4"], [2]) == [{"arquivo": "a.mp4", "t": 2.0, "tab": None}]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="precisa do ffmpeg")
def test_acrescentar_grava_png_indice_e_gabarito(tmp_path: Path) -> None:
    """Dois quadros novos viram q21 e q22; q01 a q20 ficam como estavam.

    Um segundo pedido igual é recusado e não altera o índice.
    """
    raiz = tmp_path / "acervo"
    (raiz / "novo").mkdir(parents=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=10",
            "-t",
            "3",
            "-c:v",
            "mpeg4",
            str(raiz / "novo" / "a.mp4"),
        ],
        check=True,
    )
    pasta = tmp_path / "m3b"
    (pasta / "quadros").mkdir(parents=True)
    indice = _indice_com(20)
    (pasta / "indice.json").write_text(json.dumps(indice), encoding="utf-8")
    ids = [f"q{k:02d}" for k in range(1, 21)]
    ouro = tmp_path / "braco.json"
    gabarito = _gabarito_com(ids)
    ouro.write_text(json.dumps(gabarito), encoding="utf-8")
    antes = _registros_em_bytes(gabarito, ids)

    pedidos = [
        {"arquivo": "novo/a.mp4", "t": 1.0, "tab": True},
        {"arquivo": "novo/a.mp4", "t": 2.0, "tab": None},
    ]
    assert acrescentar(pedidos, raiz, pasta, ouro) == ["q21", "q22"]

    imagem = cv2.imread(str(pasta / "quadros" / "q21.png"))
    assert imagem.shape[:2] == (240, 320)
    depois = json.loads(ouro.read_text(encoding="utf-8"))
    assert _registros_em_bytes(depois, ids) == antes
    assert depois["quadros"]["q22"] == registro_em_branco(
        depois["quadros"]["q22"]["chave"]
    )
    itens = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))["quadros"]
    assert itens[:20] == indice["quadros"]
    assert [i["id"] for i in itens[20:]] == ["q21", "q22"]
    assert itens[20]["tab"] is True
    assert itens[21]["tab"] is None

    antes_indice = (pasta / "indice.json").read_bytes()
    with pytest.raises(ValueError):
        acrescentar(pedidos[:1], raiz, pasta, ouro)
    assert (pasta / "indice.json").read_bytes() == antes_indice


def test_acrescentar_recusa_video_fora_do_acervo(tmp_path: Path) -> None:
    """Vídeo que não existe no acervo para antes de gravar qualquer coisa."""
    pasta = tmp_path / "m3b"
    (pasta / "quadros").mkdir(parents=True)
    (pasta / "indice.json").write_text(json.dumps(_indice_com(20)), encoding="utf-8")
    ouro = tmp_path / "braco.json"
    ouro.write_text(json.dumps(_gabarito_com(["q01"])), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        acrescentar(
            [{"arquivo": "nao/existe.mp4", "t": 1.0, "tab": None}],
            tmp_path,
            pasta,
            ouro,
        )
    assert not list((pasta / "quadros").iterdir())


# ---------------------------------------------------------------------------------
# Partes do violão e painéis (saddle, cavalete, boca, paineis): campos opcionais
# ---------------------------------------------------------------------------------


def _clicar_parte(gabarito: dict, id_q: str, modo: str, x: float, y: float) -> None:
    """Clique de um modo de parte, em coordenadas do quadro (escala 1).

    Args:
        gabarito: gabarito, alterado em lugar.
        id_q: id do quadro.
        modo: modo de clique.
        x: coordenada x no quadro.
        y: coordenada y no quadro.
    """
    dados = {"acao": "clique", "modo": modo, "ponto_img": [x, y], "escala": 1.0}
    aplicar_acao(gabarito, id_q, dados, DIMENSOES, "t")


def _partes_todas_respondidas() -> dict:
    """Registro com as 5 partes respondidas (pontos válidos ou oculto/nao).

    Returns:
        Registro em branco com ``saddle``, ``cavalete``, ``boca`` e ``paineis`` prontos.
    """
    registro = registro_em_branco("c")
    registro["saddle1"] = [10.0, 10.0]
    registro["saddle6"] = "oculto"
    registro["cavalete"] = [[20.0, 20.0], [30.0, 30.0]]
    registro["boca"] = [
        [100.0, 100.0],
        [200.0, 100.0],
        [250.0, 150.0],
        [200.0, 200.0],
        [100.0, 200.0],
    ]
    registro["paineis"] = "nao"
    return registro


def test_registro_antigo_ganha_as_partes_com_none_sem_mudar_o_resto() -> None:
    """Registro sem as chaves novas: completar_campos põe None e não mexe no resto."""
    antigo = registro_em_branco("c")
    antigo["braco"] = "sim"
    antigo["corda1"] = [[1.0, 2.0], [3.0, 4.0]]
    antigo["historico"] = [{"braco": None, "corda1": None}]
    for campo in CAMPOS_PARTES:
        del antigo[campo]
    original = copy.deepcopy(antigo)
    completar_campos(antigo)
    assert {c: antigo[c] for c in CAMPOS_PARTES} == dict.fromkeys(CAMPOS_PARTES)
    for campo in CAMPOS_PARTES:
        del antigo[campo]
    assert antigo == original


def test_completar_campos_nao_sobrescreve_partes_respondidas() -> None:
    """Chave que já existe com valor fica como está."""
    registro = registro_em_branco("c") | {"saddle1": [5.0, 6.0]}
    completar_campos(registro)
    assert registro["saddle1"] == [5.0, 6.0]


def test_registro_em_branco_tem_as_partes_em_none() -> None:
    """Registro novo já nasce com as 5 partes em None."""
    registro = registro_em_branco("c")
    assert all(registro[c] is None for c in CAMPOS_PARTES)


def test_saddles_gravam_pontos_e_respondem_oculto() -> None:
    """Cada clique de saddle grava um ponto; 'oculto' é mudança de campo."""
    gabarito = _gabarito_com(["q01"])
    _clicar_parte(gabarito, "q01", "saddle1", 100, 200)
    assert gabarito["quadros"]["q01"]["saddle1"] == [100.0, 200.0]
    _clicar_parte(gabarito, "q01", "saddle1", 110, 210)
    assert gabarito["quadros"]["q01"]["saddle1"] == [110.0, 210.0]
    _clicar_parte(gabarito, "q01", "saddle6", 300, 400)
    assert gabarito["quadros"]["q01"]["saddle6"] == [300.0, 400.0]
    aplicar_acao(
        gabarito, "q01", {"campo": "saddle6", "valor": "oculto"}, DIMENSOES, "t"
    )
    assert gabarito["quadros"]["q01"]["saddle6"] == "oculto"


def test_cavalete_segue_a_logica_do_par_da_corda() -> None:
    """Dois cliques formam o par; o terceiro começa outro (como corda1)."""
    gabarito = _gabarito_com(["q01"])
    _clicar_parte(gabarito, "q01", "cavalete", 100, 100)
    _clicar_parte(gabarito, "q01", "cavalete", 1800, 900)
    assert gabarito["quadros"]["q01"]["cavalete"] == [[100.0, 100.0], [1800.0, 900.0]]
    _clicar_parte(gabarito, "q01", "cavalete", 500, 500)
    assert gabarito["quadros"]["q01"]["cavalete"] == [[500.0, 500.0]]


def test_paineis_duas_caixas_por_quatro_cliques() -> None:
    """Dois cliques por caixa; a segunda caixa começa depois do 2º canto da primeira."""
    gabarito = _gabarito_com(["q01"])
    for x, y in ((100, 100), (500, 400), (600, 100), (900, 400)):
        _clicar_parte(gabarito, "q01", "paineis", x, y)
    assert gabarito["quadros"]["q01"]["paineis"] == [
        [[100.0, 100.0], [500.0, 400.0]],
        [[600.0, 100.0], [900.0, 400.0]],
    ]
    assert partes_faltando(gabarito["quadros"]["q01"]) == [
        "saddle1",
        "saddle6",
        "cavalete",
        "boca",
    ]


def test_quarta_caixa_recusada_sem_mudar_o_registro() -> None:
    """Com 3 caixas, o clique que abriria a 4ª dá ValueError e nada muda."""
    gabarito = _gabarito_com(["q01"])
    for x in (100, 300, 500):
        _clicar_parte(gabarito, "q01", "paineis", x, 100)
        _clicar_parte(gabarito, "q01", "paineis", x + 50, 200)
    antes = copy.deepcopy(gabarito["quadros"]["q01"])
    with pytest.raises(ValueError, match="no máximo 3"):
        _clicar_parte(gabarito, "q01", "paineis", 700, 100)
    assert gabarito["quadros"]["q01"] == antes


def test_caixa_sem_area_e_recusada() -> None:
    """Dois cantos com o mesmo x ou o mesmo y não formam caixa: recusa, sem mudança."""
    gabarito = _gabarito_com(["q01"])
    _clicar_parte(gabarito, "q01", "paineis", 100, 100)
    antes = copy.deepcopy(gabarito["quadros"]["q01"])
    with pytest.raises(ValueError, match="sem área"):
        _clicar_parte(gabarito, "q01", "paineis", 100, 300)
    with pytest.raises(ValueError, match="sem área"):
        _clicar_parte(gabarito, "q01", "paineis", 300, 100)
    assert gabarito["quadros"]["q01"] == antes


def test_paineis_so_respondem_com_duas_ou_tres_caixas_completas() -> None:
    """Caixa incompleta não conta; 1 caixa completa não conta; 2 ou 3 contam; 'nao' conta."""
    base = registro_em_branco("c")
    caixa = [[1.0, 2.0], [30.0, 40.0]]
    incompleta = [[5.0, 6.0]]
    casos = {
        "uma completa": [caixa],
        "completa e em construcao": [caixa, incompleta],
        "duas completas": [caixa, [[50.0, 60.0], [70.0, 80.0]]],
        "tres completas": [caixa, caixa, caixa],
    }
    esperado = {
        "uma completa": False,
        "completa e em construcao": False,
        "duas completas": True,
        "tres completas": True,
    }
    for nome, valor in casos.items():
        assert ("paineis" not in partes_faltando(base | {"paineis": valor})) is (
            esperado[nome]
        ), nome
    assert "paineis" not in partes_faltando(base | {"paineis": "nao"})
    assert "paineis" in partes_faltando(base | {"paineis": None})


def test_completar_campos_migra_divisao_nao_para_paineis_nao() -> None:
    """Registro com divisao 'nao' e sem a chave paineis ganha paineis 'nao'."""
    registro = registro_em_branco("c")
    del registro["paineis"]
    registro["divisao"] = "nao"
    completar_campos(registro)
    assert registro["paineis"] == "nao"
    assert registro["divisao"] == "nao"


def test_completar_campos_divisao_com_pontos_vira_paineis_none() -> None:
    """Divisão com pontos não vira painel: paineis None e a divisão fica igual."""
    registro = registro_em_branco("c")
    del registro["paineis"]
    registro["divisao"] = [[1.0, 2.0], [3.0, 4.0]]
    completar_campos(registro)
    assert registro["paineis"] is None
    assert registro["divisao"] == [[1.0, 2.0], [3.0, 4.0]]


def test_completar_campos_nao_mexe_em_paineis_ja_existentes() -> None:
    """Chave paineis presente (com caixas ou com None após 'limpar') não é tocada.

    Se o None do 'limpar painéis' voltasse a 'nao' no carregamento, o dono perderia a
    limpeza a cada reinício; por isso a migração só roda quando a chave falta.
    """
    com_caixas = registro_em_branco("c") | {
        "divisao": "nao",
        "paineis": [[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]]],
    }
    completar_campos(com_caixas)
    assert com_caixas["paineis"] == [
        [[1.0, 2.0], [3.0, 4.0]],
        [[5.0, 6.0], [7.0, 8.0]],
    ]
    limpo = registro_em_branco("c") | {"divisao": "nao", "paineis": None}
    completar_campos(limpo)
    assert limpo["paineis"] is None


def test_desfazer_volta_o_clique_de_painel() -> None:
    """Cada desfazer volta um clique: caixa fechada, depois só o 1º canto, depois vazio."""
    gabarito = _gabarito_com(["q01"])
    _clicar_parte(gabarito, "q01", "paineis", 100, 100)
    _clicar_parte(gabarito, "q01", "paineis", 500, 400)
    _clicar_parte(gabarito, "q01", "paineis", 600, 100)
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert gabarito["quadros"]["q01"]["paineis"] == [[[100.0, 100.0], [500.0, 400.0]]]
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert gabarito["quadros"]["q01"]["paineis"] == [[[100.0, 100.0]]]
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert gabarito["quadros"]["q01"]["paineis"] is None


def test_desfazer_de_foto_sem_paineis_restaura_o_que_a_migracao_daria() -> None:
    """Foto de antes dos painéis com divisão 'nao': desfazer põe paineis 'nao'."""
    gabarito = _gabarito_com(["q01"])
    registro = gabarito["quadros"]["q01"]
    registro["divisao"] = "nao"
    registro["paineis"] = [[[1.0, 2.0], [3.0, 4.0]]]
    registro["historico"] = [{"braco": None, "corda1": None}]
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert registro["paineis"] == "nao"


def test_braco_nao_nao_apaga_os_paineis() -> None:
    """Braço 'nao' limpa a geometria, mas as caixas de painel ficam."""
    gabarito = _gabarito_com(["q01"])
    aplicar_acao(gabarito, "q01", {"campo": "paineis", "valor": "nao"}, DIMENSOES, "t")
    aplicar_acao(gabarito, "q01", {"campo": "braco", "valor": "nao"}, DIMENSOES, "t")
    assert gabarito["quadros"]["q01"]["paineis"] == "nao"


def test_divisao_antiga_nao_muda_com_os_cliques_e_o_desfazer() -> None:
    """O rótulo antigo 'divisao' é só guardado: nenhum clique ou desfazer o toca."""
    gabarito = _gabarito_com(["q01"])
    registro = gabarito["quadros"]["q01"]
    registro["divisao"] = [[1.0, 2.0], [3.0, 4.0]]
    _clicar_parte(gabarito, "q01", "paineis", 100, 100)
    _clicar_parte(gabarito, "q01", "paineis", 500, 400)
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert registro["divisao"] == [[1.0, 2.0], [3.0, 4.0]]


def test_registro_novo_nao_tem_divisao() -> None:
    """Registro em branco não traz a chave antiga 'divisao', mas traz 'paineis'."""
    registro = registro_em_branco("c")
    assert "divisao" not in registro
    assert registro["paineis"] is None


def test_cavalete_nao_mistura_com_valor_oculto_ao_clicar() -> None:
    """Um cavalete 'oculto' não vira ponto de lista quando o clique chega."""
    gabarito = _gabarito_com(["q01"])
    aplicar_acao(
        gabarito, "q01", {"campo": "cavalete", "valor": "oculto"}, DIMENSOES, "t"
    )
    _clicar_parte(gabarito, "q01", "cavalete", 100, 100)
    assert gabarito["quadros"]["q01"]["cavalete"] == [[100.0, 100.0]]


def test_boca_acrescenta_e_remove_o_ponto_perto_do_clique() -> None:
    """Clique longe acrescenta; clique dentro do raio do traste remove o mais perto."""
    gabarito = _gabarito_com(["q01"])
    _clicar_parte(gabarito, "q01", "boca", 100, 100)
    _clicar_parte(gabarito, "q01", "boca", 300, 100)
    _clicar_parte(gabarito, "q01", "boca", 200, 300)
    assert len(gabarito["quadros"]["q01"]["boca"]) == 3
    _clicar_parte(gabarito, "q01", "boca", 105, 103)
    assert gabarito["quadros"]["q01"]["boca"] == [[300.0, 100.0], [200.0, 300.0]]


def test_boca_recusa_nono_ponto_sem_mudar_o_quadro() -> None:
    """Com 8 pontos, o 9º clique (longe de todos) é recusado e nada muda."""
    gabarito = _gabarito_com(["q01"])
    for k in range(8):
        _clicar_parte(gabarito, "q01", "boca", 100 + 200 * k, 100)
    antes = copy.deepcopy(gabarito["quadros"]["q01"])
    with pytest.raises(ValueError, match="máximo 8"):
        _clicar_parte(gabarito, "q01", "boca", 100, 900)
    assert gabarito["quadros"]["q01"] == antes


def test_partes_completas_exige_as_cinco_partes_e_boca_com_cinco_pontos() -> None:
    """partes_completas: 5 partes respondidas; boca com 4 pontos ainda falta."""
    registro = _partes_todas_respondidas()
    assert partes_completas(registro)
    assert partes_faltando(registro) == []
    registro["boca"] = [[1.0, 1.0], [2.0, 2.0], [3.0, 1.0], [2.0, 0.0]]
    assert not partes_completas(registro)
    assert partes_faltando(registro) == ["boca"]
    registro["boca"] = "oculto"
    assert partes_completas(registro)
    assert not partes_completas(registro_em_branco("c"))
    assert partes_faltando(registro_em_branco("c")) == list(CAMPOS_PARTES)


def test_braco_nao_nao_apaga_as_partes() -> None:
    """Mudar braco para 'nao' limpa a geometria, mas saddle e boca ficam."""
    gabarito = _gabarito_com(["q01"])
    _clicar_parte(gabarito, "q01", "saddle1", 50, 60)
    _clicar_parte(gabarito, "q01", "boca", 100, 100)
    aplicar_acao(gabarito, "q01", {"campo": "braco", "valor": "nao"}, DIMENSOES, "t")
    registro = gabarito["quadros"]["q01"]
    assert registro["saddle1"] == [50.0, 60.0]
    assert registro["boca"] == [[100.0, 100.0]]


def test_registro_completo_nao_muda_com_as_partes() -> None:
    """registro_completo dá o mesmo resultado com e sem as partes respondidas."""
    sem = _completo("sim")
    com = _completo("sim") | {c: _partes_todas_respondidas()[c] for c in CAMPOS_PARTES}
    assert registro_completo(sem) is True
    assert registro_completo(com) is True
    vazio = _completo("sim") | dict.fromkeys(CAMPOS_PARTES)
    assert registro_completo(vazio) is True
    assert registro_completo(_completo("nao") | {"saddle1": None}) is True


def test_valores_invalidos_das_partes_dao_valueerror() -> None:
    """'oculto' em painéis, 'nao' em saddle, lista em valor de campo, 'divisao' e ponto ruim."""
    gabarito = _gabarito_com(["q01"])
    casos = [
        {"campo": "paineis", "valor": "oculto"},
        {"campo": "paineis", "valor": [[[1, 2], [3, 4]]]},
        {"campo": "divisao", "valor": "nao"},
        {"campo": "saddle1", "valor": "nao"},
        {"campo": "cavalete", "valor": [[1, 2], [3, 4]]},
        {"campo": "boca", "valor": "sim"},
    ]
    for dados in casos:
        with pytest.raises(ValueError):
            aplicar_acao(gabarito, "q01", dados, DIMENSOES, "t")
    with pytest.raises(ValueError):
        _clicar_parte_bruta(gabarito, "q01", "saddle1", [1])
    with pytest.raises(ValueError):
        _clicar_parte(gabarito, "q01", "saddle1", 5000, 10)
    assert gabarito["quadros"]["q01"]["saddle1"] is None
    assert gabarito["quadros"]["q01"]["paineis"] is None


def _clicar_parte_bruta(
    gabarito: dict, id_q: str, modo: str, ponto_img: list[float]
) -> None:
    """Clique de parte com ``ponto_img`` cru (para testar ponto mal formado).

    Args:
        gabarito: gabarito, alterado em lugar.
        id_q: id do quadro.
        modo: modo de clique.
        ponto_img: o ponto como chegou (pode estar errado de propósito).
    """
    dados = {"acao": "clique", "modo": modo, "ponto_img": ponto_img, "escala": 1.0}
    aplicar_acao(gabarito, id_q, dados, DIMENSOES, "t")


def test_desfazer_volta_a_parte_anterior() -> None:
    """Desfazer restaura saddle e a lista do cavalete como estavam antes."""
    gabarito = _gabarito_com(["q01"])
    _clicar_parte(gabarito, "q01", "saddle1", 10, 10)
    _clicar_parte(gabarito, "q01", "saddle1", 20, 20)
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert gabarito["quadros"]["q01"]["saddle1"] == [10.0, 10.0]
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert gabarito["quadros"]["q01"]["saddle1"] is None
    _clicar_parte(gabarito, "q01", "cavalete", 1, 1)
    _clicar_parte(gabarito, "q01", "cavalete", 2, 2)
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert gabarito["quadros"]["q01"]["cavalete"] == [[1.0, 1.0]]


def test_desfazer_de_historico_antigo_sem_as_partes_nao_quebra() -> None:
    """Foto gravada antes das partes (sem as chaves): desfazer põe None, sem erro."""
    gabarito = _gabarito_com(["q01"])
    registro = gabarito["quadros"]["q01"]
    antiga = dict.fromkeys(
        ("braco", "corda1", "corda6", "nut", "trastes", "traste_referencia")
    )
    registro["braco"] = "sim"
    registro["historico"] = [antiga]
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert registro["braco"] is None
    assert registro["saddle1"] is None


def test_resumo_conta_quadros_com_as_partes() -> None:
    """resumo: 'partes' lista os quadros com as 5 partes; 'partes_concluidas' conta."""
    gabarito = _gabarito_com(["q01", "q02"])
    gabarito["quadros"]["q01"] = _partes_todas_respondidas()
    dados = {"partes": ["q01"], "partes_concluidas": 1, "total": 2}
    resultado = resumo(gabarito, [{"id": "q01"}, {"id": "q02"}])
    assert {k: resultado[k] for k in dados} == dados
    assert resultado["quadros"]["q02"]["partes_faltando"] == list(CAMPOS_PARTES)
    assert resultado["quadros"]["q01"]["partes_completas"] is True


def test_mesclar_mantem_as_partes_do_disco() -> None:
    """Mesclagem copia as partes respondidas e aceita registro antigo sem elas."""
    novo = _gabarito_com(["q01"])
    existente = _gabarito_com(["q01"])
    registro = existente["quadros"]["q01"]
    registro["respondido_em"] = "2026-10-16T10:00:00"
    registro["saddle1"] = [7.0, 8.0]
    registro["divisao"] = [[1.0, 2.0], [3.0, 4.0]]
    for c in ("saddle6", "cavalete", "boca", "paineis"):
        del registro[c]
    mesclado = mesclar_gabarito(novo, existente)
    assert mesclado["quadros"]["q01"]["saddle1"] == [7.0, 8.0]
    assert mesclado["quadros"]["q01"]["paineis"] is None
    assert mesclado["quadros"]["q01"]["divisao"] == [[1.0, 2.0], [3.0, 4.0]]


def test_mesclar_migra_divisao_nao_do_disco_para_paineis() -> None:
    """Quadro respondido com divisão 'nao' no disco entra como paineis 'nao'."""
    novo = _gabarito_com(["q01"])
    existente = _gabarito_com(["q01"])
    registro = existente["quadros"]["q01"]
    registro["respondido_em"] = "2026-10-16T10:00:00"
    registro["divisao"] = "nao"
    del registro["paineis"]
    mesclado = mesclar_gabarito(novo, existente)
    assert mesclado["quadros"]["q01"]["paineis"] == "nao"
    assert mesclado["quadros"]["q01"]["divisao"] == "nao"


def test_servidor_completa_partes_de_gabarito_antigo(tmp_path: Path) -> None:
    """Servidor carrega gabarito sem as partes: estado mostra 0 e a gravação funciona."""
    arq, raiz = _cache_e_censo(tmp_path, _censo_sintetico())
    pasta = tmp_path / "m3b"
    ouro = tmp_path / "braco.json"
    preparar(arq, raiz, pasta, ouro, semente=5)
    dados = json.loads(ouro.read_text(encoding="utf-8"))
    for reg in dados["quadros"].values():
        for c in CAMPOS_PARTES:
            del reg[c]
    ouro.write_text(json.dumps(dados), encoding="utf-8")
    servidor = criar_servidor(pasta, ouro, porta=0, host="127.0.0.1")
    porta = servidor.server_address[1]
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/estado.json") as r:
            estado = json.loads(r.read())
        assert estado["partes_concluidas"] == 0
        codigo, resposta = _post(
            porta, {"quadro": "q01", "campo": "paineis", "valor": "nao"}
        )
        assert codigo == 200
        assert resposta["quadros"]["q01"]["registro"]["paineis"] == "nao"
        gravado = json.loads(ouro.read_text(encoding="utf-8"))["quadros"]["q01"]
        assert gravado["paineis"] == "nao"
        assert gravado["saddle1"] is None
    finally:
        servidor.shutdown()
        servidor.server_close()


def _clique_sintetico(n: int) -> list[float]:
    """Clique sintético do traste ``n`` sobre o eixo do braço de teste (y = 150).

    Args:
        n: número do traste.

    Returns:
        ``[x, y]`` arredondado a 1 casa, como um clique da página.
    """
    s = s_do_traste(n)
    t = (1200.0 * s - 400.0) / (0.3 * s + 1.0)
    return [round(500.0 + t, 1), 150.0]


def _registro_com_ancoras() -> dict:
    """Registro de braço com pestana, cordas e 2 trastes âncora (5 e 12).

    Returns:
        Registro pronto para ``prever_trastes``; as âncoras vêm na ordem 12, 5.
    """
    reg = registro_em_branco("chave")
    reg["braco"] = "sim"
    reg["corda1"] = [[0.0, 100.0], [1000.0, 100.0]]
    reg["corda6"] = [[0.0, 200.0], [1000.0, 200.0]]
    reg["nut"] = [100.0, 150.0]
    reg["trastes"] = [_clique_sintetico(12), _clique_sintetico(5)]
    return reg


def test_registro_em_branco_tem_trastes_previstos_none() -> None:
    """Registro novo começa sem previstos."""
    assert registro_em_branco("c")["trastes_previstos"] is None


def test_completar_campos_acrescenta_trastes_previstos() -> None:
    """Registro antigo sem a chave ganha None; um valor existente fica como está."""
    antigo = registro_em_branco("c")
    del antigo["trastes_previstos"]
    completar_campos(antigo)
    assert antigo["trastes_previstos"] is None
    com_valor = registro_em_branco("c")
    com_valor["trastes_previstos"] = [[1.0, 2.0]]
    completar_campos(com_valor)
    assert com_valor["trastes_previstos"] == [[1.0, 2.0]]


def test_prever_trastes_numera_1_a_19_e_marca_os_previstos() -> None:
    """Depois da ação: 1..19 em ordem, âncoras com o clique, previstos sem as âncoras."""
    reg = _registro_com_ancoras()
    gabarito = {"quadros": {"q01": reg}}
    aplicar_acao(gabarito, "q01", {"acao": "prever_trastes"}, DIMENSOES, "t1")
    numeracao = numerar_trastes(reg)
    assert [item["numero"] for item in numeracao] == list(range(1, 20))
    por_numero = {item["numero"]: item["ponto"] for item in numeracao}
    assert por_numero[5] == _clique_sintetico(5)
    assert por_numero[12] == _clique_sintetico(12)
    ancoras = [_clique_sintetico(5), _clique_sintetico(12)]
    assert len(reg["trastes_previstos"]) == 17
    assert all(p not in ancoras for p in reg["trastes_previstos"])
    assert reg["respondido_em"] == "t1"
    assert len(reg["historico"]) == 1


def test_prever_trastes_recusa_sem_duas_ancoras_sem_mudar_nada() -> None:
    """Com um traste só marcado a ação recusa, e o registro fica como estava."""
    reg = _registro_com_ancoras()
    reg["trastes"] = [_clique_sintetico(12)]
    gabarito = {"quadros": {"q01": reg}}
    antes = copy.deepcopy(reg)
    with pytest.raises(ValueError, match="exatamente 2 trastes"):
        aplicar_acao(gabarito, "q01", {"acao": "prever_trastes"}, DIMENSOES, "t")
    assert reg == antes


def test_prever_trastes_recusa_numeros_iguais_e_invalidos() -> None:
    """Números repetidos ou que não são inteiros não passam."""
    gabarito = {"quadros": {"q01": _registro_com_ancoras()}}
    for numeros in ([5, 5], [5, "12"], [5]):
        with pytest.raises(ValueError):
            aplicar_acao(
                gabarito,
                "q01",
                {"acao": "prever_trastes", "numeros": numeros},
                DIMENSOES,
                "t",
            )
    assert gabarito["quadros"]["q01"]["historico"] == []


def test_prever_trastes_desfazer_volta_as_duas_ancoras() -> None:
    """Desfazer depois da previsão devolve as 2 âncoras e tira os previstos."""
    reg = _registro_com_ancoras()
    antes = list(reg["trastes"])
    gabarito = {"quadros": {"q01": reg}}
    aplicar_acao(gabarito, "q01", {"acao": "prever_trastes"}, DIMENSOES, "t")
    aplicar_acao(gabarito, "q01", {"acao": "desfazer"}, DIMENSOES, "t")
    assert reg["trastes"] == antes
    assert reg["trastes_previstos"] is None


def test_remover_traste_previsto_o_tira_da_lista() -> None:
    """Botão direito num laranja remove o traste e o tira de ``trastes_previstos``."""
    reg = _registro_com_ancoras()
    gabarito = {"quadros": {"q01": reg}}
    aplicar_acao(gabarito, "q01", {"acao": "prever_trastes"}, DIMENSOES, "t")
    alvo = _clique_sintetico(8)
    assert alvo in reg["trastes_previstos"]
    aplicar_acao(
        gabarito,
        "q01",
        {
            "acao": "clique",
            "modo": "trastes",
            "remover": True,
            "ponto_img": alvo,
            "escala": 1.0,
        },
        DIMENSOES,
        "t",
    )
    assert alvo not in reg["trastes"]
    assert alvo not in reg["trastes_previstos"]
    assert len(reg["trastes_previstos"]) == 16


def test_clique_novo_nao_muda_os_previstos() -> None:
    """Acrescentar um traste clicado deixa os previstos como estão."""
    reg = _registro_com_ancoras()
    gabarito = {"quadros": {"q01": reg}}
    aplicar_acao(gabarito, "q01", {"acao": "prever_trastes"}, DIMENSOES, "t")
    previstos = copy.deepcopy(reg["trastes_previstos"])
    aplicar_acao(
        gabarito,
        "q01",
        {
            "acao": "clique",
            "modo": "trastes",
            "ponto_img": [1500.0, 150.0],
            "escala": 1.0,
        },
        DIMENSOES,
        "t",
    )
    assert reg["trastes_previstos"] == previstos
    assert [1500.0, 150.0] in reg["trastes"]


def test_pagina_tem_a_tecla_r_e_a_acao_de_prever() -> None:
    """A página chama ``prever_trastes`` pela tecla r e mostra os previstos em laranja."""
    assert 'ev.key === "r"' in PAGINA
    assert 'acao: "prever_trastes"' in PAGINA
    assert "#ff9f1c" in PAGINA
