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
    CANAL_MVP,
    acrescentar,
    acrescentar_gabarito,
    acrescentar_indice,
    amostrar_quadros,
    aplicar_acao,
    completos,
    converter_clique,
    criar_servidor,
    entrada_do_indice,
    gabarito_novo,
    ler_pares,
    mesclar_gabarito,
    numerar_trastes,
    ordenar_trastes,
    preparar,
    proximo_id,
    registro_completo,
    registro_em_branco,
    resumo,
    validar_no_quadro,
)

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
