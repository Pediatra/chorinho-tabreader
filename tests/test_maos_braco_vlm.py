"""Pré-marcação por consenso de modelos (rodada 1019): filtro, consenso e escolha de L.

Tudo sintético: sem rede, sem proxy e sem acervo.
"""

from __future__ import annotations

import base64
import json
import random
import urllib.error

import cv2
import numpy as np
import pytest

from tab import maos_braco_vlm as vlm
from tab.maos_braco_tempo import Marcas

#: Geometria em pixels de um quadro 1000x1000: nut em x = 900, traste n a
#: 800 * (1 - 2^(-n/12)) do nut, cordas 1 e 6 em y = 290 e y = 310.
NUT = [900.0, 300.0]
CORDA1 = [[900.0, 290.0], [100.0, 290.0]]
CORDA6 = [[900.0, 310.0], [100.0, 310.0]]
T5 = [699.4, 300.0]
T12 = [500.0, 300.0]


def _payload(**trocas: object) -> dict:
    """Resposta válida (coordenadas 0 a 1000) com campos substituídos por ``trocas``."""
    dados: dict[str, object] = {
        "braco": "sim",
        "nut": NUT,
        "corda1": CORDA1,
        "corda6": CORDA6,
        "traste5": T5,
        "traste12": T12,
    }
    dados.update(trocas)
    return dados


def _texto(dados: dict) -> str:
    """Texto cru de uma resposta, como o modelo devolveria."""
    return json.dumps(dados)


def _marcas(previsto_pontos: dict[int, list[float]]) -> Marcas:
    """Marcas do quadro válido, a partir dos trastes previstos."""
    marcas = vlm.marcas_previstas(NUT, CORDA1, CORDA6, previsto_pontos)
    assert marcas is not None
    return marcas


def _previsto_valido() -> dict[int, list[float]]:
    """Trastes previstos do quadro válido, pela regra das 12 notas."""
    analise, motivo = vlm.analisar(_texto(_payload()), 1000, 1000)
    assert motivo is None and analise is not None
    return analise["previsto"]


# ----------------------------------------------------------------- parse e prompt


def test_interpretar_tira_cercas_e_texto_em_volta() -> None:
    """A resposta com cerca ```json e frases antes e depois vira o dicionário."""
    cru = 'Aqui está:\n```json\n{"braco": "sim", "nut": [1, 2]}\n```\nPronto.'
    assert vlm.interpretar(cru) == {"braco": "sim", "nut": [1, 2]}


def test_interpretar_recusa_sem_objeto_valido() -> None:
    """Sem chaves, ou com JSON quebrado, não há dicionário."""
    assert vlm.interpretar("nenhuma marcação aqui") is None
    assert vlm.interpretar("{não é json}") is None
    assert vlm.interpretar("[1, 2, 3]") is None


def test_prompt_formata_tamanho_e_mantem_exemplo_literal() -> None:
    """O prompt aceita o tamanho enviado e o exemplo de JSON sai com chaves simples."""
    texto = vlm.PROMPT.format(largura=1280, altura=720)
    assert "(1280x720 pixels)" in texto
    assert '{"braco": "sim", "nut": [x, y]' in texto


# ------------------------------------------------------- filtro e conversão 0-1000


def test_analisar_aceita_quadro_valido() -> None:
    """Um quadro bem marcado passa o filtro e devolve os pontos em pixels."""
    analise, motivo = vlm.analisar(_texto(_payload()), 1000, 1000)
    assert motivo is None
    assert analise is not None
    assert analise["nut"] == pytest.approx(NUT)
    assert analise["t5"] == pytest.approx(T5)
    assert set(analise["previsto"]) >= {5, 12}


def test_analisar_converte_de_0_a_1000_para_pixels_do_original() -> None:
    """Em um quadro 2000x1000, x 450 (de 0 a 1000) vira x 900 em pixels."""
    dados = _payload(
        nut=[450.0, 300.0],
        corda1=[[450.0, 290.0], [50.0, 290.0]],
        corda6=[[450.0, 310.0], [50.0, 310.0]],
        traste5=[349.7, 300.0],
        traste12=[250.0, 300.0],
    )
    analise, motivo = vlm.analisar(_texto(dados), 2000, 1000)
    assert motivo is None
    assert analise is not None
    assert analise["nut"] == pytest.approx([900.0, 300.0])
    assert analise["corda1"][1] == pytest.approx([100.0, 290.0])


def test_analisar_json_invalido() -> None:
    """Texto sem JSON é descartado como json_invalido."""
    assert vlm.analisar("sem json", 1000, 1000) == (None, "json_invalido")


def test_analisar_falta_ponto_quando_traste_e_null() -> None:
    """Traste 5 em null conta como ponto faltando."""
    _, motivo = vlm.analisar(_texto(_payload(traste5=None)), 1000, 1000)
    assert motivo == "falta_ponto"


def test_analisar_nut_fora() -> None:
    """Nut ``fora`` é descartado, com os outros pontos presentes."""
    _, motivo = vlm.analisar(_texto(_payload(nut="fora")), 1000, 1000)
    assert motivo == "nut_fora"


def test_analisar_fora_da_imagem() -> None:
    """Ponto com x maior que a largura é descartado."""
    _, motivo = vlm.analisar(_texto(_payload(nut=[1200.0, 300.0])), 1000, 1000)
    assert motivo == "fora_da_imagem"


def test_analisar_cordas_que_se_cruzam() -> None:
    """Cordas 1 e 6 com as pontas trocadas se cruzam e são descartadas."""
    dados = _payload(corda1=[[100.0, 290.0], [900.0, 310.0]])
    dados["corda6"] = [[100.0, 310.0], [900.0, 290.0]]
    _, motivo = vlm.analisar(_texto(dados), 1000, 1000)
    assert motivo == "cordas_se_cruzam"


def test_analisar_prever_recusa_corda_sem_direcao() -> None:
    """Corda com os dois pontos iguais: ``prever_trastes`` recusa, e o motivo diz isso."""
    dados = _payload(corda1=[[900.0, 290.0], [900.0, 290.0]])
    _, motivo = vlm.analisar(_texto(dados), 1000, 1000)
    assert motivo is not None
    assert motivo.startswith("prever_recusou")


def test_analisar_razao_fora_da_faixa() -> None:
    """Traste 5 a 300 px do nut (razão 0,75): fora da faixa de 0,35 a 0,70."""
    _, motivo = vlm.analisar(_texto(_payload(traste5=[600.0, 300.0])), 1000, 1000)
    assert motivo == "razao_fora"


def test_razao_do_quadro_valido_fica_perto_de_meio() -> None:
    """A razão (t5 - nut) / (t12 - nut) da geometria sintética vale cerca de 0,50."""
    razao = vlm._razao(NUT, CORDA1, CORDA6, T5, T12)
    assert razao == pytest.approx(0.5016, abs=1e-3)


# ---------------------------------------------------------- orientação e mediana


def test_orientar_coloca_o_ponto_mais_perto_do_nut_primeiro() -> None:
    """Na corda com o ponto distante primeiro, a ordem é trocada."""
    par = [[100.0, 290.0], [900.0, 290.0]]
    ordenado = vlm._proximo_do_nut_primeiro(np.array(NUT), par)
    assert ordenado[0].tolist() == [900.0, 290.0]


def test_mediana_coordenada_a_coordenada() -> None:
    """Com 3 modelos, o consenso do traste 5 é a mediana das 3 coordenadas x."""
    validas = []
    for x5 in (100.0, 200.0, 300.0):
        validas.append(
            {
                "nut": np.array(NUT),
                "c1": np.array(CORDA1),
                "c6": np.array(CORDA6),
                "t5": np.array([x5, 300.0]),
                "t12": np.array(T12),
            }
        )
    cons = vlm.consenso(validas)
    assert cons["t5"].tolist() == [200.0, 300.0]
    assert cons["nut"].tolist() == NUT


# ------------------------------------------------------------------- dispersão


def _modelo(desloc_corda: float = 0.0, desloc_perp: float = 0.0) -> dict:
    """Resposta orientada com a corda 1 deslocada ao longo dela mesma (ou em y)."""
    c1 = [[p[0] + desloc_corda, p[1] + desloc_perp] for p in CORDA1]
    return {
        "nut": np.array(NUT),
        "c1": np.array(c1),
        "c6": np.array(CORDA6),
        "t5": np.array(T5),
        "t12": np.array(T12),
    }


def test_dispersao_de_corda_deslocada_ao_longo_dela_da_zero() -> None:
    """Pontas da corda 1 deslocadas só ao longo da corda não contam como dispersão."""
    validas = [_modelo(0.0), _modelo(30.0), _modelo(-20.0)]
    cons = vlm.consenso(validas)
    disp = vlm.dispersoes(validas, cons)
    assert all(d == pytest.approx(0.0, abs=1e-9) for d in disp)


def test_dispersao_de_corda_deslocada_em_y_conta() -> None:
    """Corda deslocada perpendicularmente (em y) aparece na dispersão do modelo."""
    validas = [_modelo(0.0), _modelo(0.0), _modelo(0.0, desloc_perp=20.0)]
    cons = vlm.consenso(validas)
    disp = vlm.dispersoes(validas, cons)
    assert disp[2] > 0.5
    assert disp[0] == pytest.approx(0.0, abs=1e-9)


# -------------------------------------------------------------- medida e troca


def test_medir_quadro_igual_ao_alvo_e_certo() -> None:
    """Previsão igual ao gabarito: classe certo e sem troca de cordas."""
    alvo = _marcas(_previsto_valido())
    medida = vlm.medir(alvo, alvo)
    assert medida is not None
    assert medida["classe"] == "certo"
    assert medida["trocou"] is False


def test_medir_detecta_troca_de_cordas() -> None:
    """Previsão com as cordas 1 e 6 trocadas: a troca é contada."""
    alvo = _marcas(_previsto_valido())
    trocada = Marcas(
        nut=alvo.nut,
        trastes=alvo.trastes,
        corda1=alvo.corda6,
        corda6=alvo.corda1,
    )
    medida = vlm.medir(trocada, alvo)
    assert medida is not None
    assert medida["trocou"] is True


# ----------------------------------------------------------- escolha de L e aceite


def _busca(**por_limiar: dict) -> dict[float, dict]:
    """Monta ``{L: estatisticas}`` a partir de dicionários nomeados por L (com ``_``)."""
    saida: dict[float, dict] = {}
    for nome, stats in por_limiar.items():
        saida[float(nome.replace("_", "."))] = stats
    return saida


def _stats(aceitos: int, certo: int, impreciso: int, falso: int, n: int = 33) -> dict:
    """Estatísticas de um limiar, com o número de aceitos e as classes."""
    return {
        "n": n,
        "aceitos": aceitos,
        "certo": certo,
        "impreciso": impreciso,
        "falso": falso,
    }


def test_escolher_limiar_pega_o_maior_que_passa() -> None:
    """L = 0,75 passa (9 de 10 certos, 0 falsos), e L = 1,0 falha (um falso)."""
    busca = _busca(
        **{
            "0_25": _stats(3, 3, 0, 0),
            "0_5": _stats(4, 3, 1, 0),
            "0_75": _stats(10, 9, 1, 0),
            "1_0": _stats(12, 9, 2, 1),
            "1_5": _stats(20, 10, 9, 1),
        }
    )
    assert vlm.escolher_limiar(busca) == 0.75


def test_escolher_limiar_reprova_quando_nenhum_serve() -> None:
    """Se todo L tem falso, ou nenhum aceito, não há limiar escolhido."""
    busca = _busca(
        **{
            "0_25": _stats(0, 0, 0, 0),
            "0_5": _stats(5, 4, 0, 1),
            "0_75": _stats(5, 5, 0, 1),
            "1_0": _stats(6, 5, 0, 1),
            "1_5": _stats(6, 5, 0, 1),
        }
    )
    assert vlm.escolher_limiar(busca) is None


def test_aceito_exige_consenso_e_dispersao_dentro_do_limiar() -> None:
    """Sem consenso não há aceito; com dispersão acima do L, não há aceito."""
    sem_consenso = {"consenso": None, "dispersao": 0.1}
    alta = {"consenso": "certo", "dispersao": 0.8}
    dentro = {"consenso": "certo", "dispersao": 0.5}
    assert vlm._aceito(sem_consenso, 1.5) is False
    assert vlm._aceito(alta, 0.5) is False
    assert vlm._aceito(dentro, 0.5) is True


# ----------------------------------------------------------------- divisão


def test_divisao_e_deterministica_e_completa() -> None:
    """A divisão tem 33 de dev e o resto de teste, pela semente do pré-registro."""
    ids = [f"q{n:02d}" for n in range(1, 67)]
    dev, teste = vlm.dividir(ids)
    assert len(dev) == 33
    assert len(teste) == 33
    assert set(dev).isdisjoint(teste)
    assert sorted(dev + teste) == sorted(ids)
    esperado = set(random.Random(vlm.SEMENTE).sample(sorted(ids), 33))
    assert set(dev) == esperado
    assert vlm.dividir(list(reversed(ids))) == (dev, teste)


# ---------------------------------------------------------- coleta (sem rede)


def test_preparar_envio_reduz_para_1280_mantendo_proporcao(tmp_path) -> None:
    """Quadro 1920x1080 vira 1280x720 em JPEG, e a imagem volta decodificável."""
    caminho = tmp_path / "quadro.png"
    cv2.imwrite(str(caminho), np.full((1080, 1920, 3), 128, dtype=np.uint8))
    base64_jpeg, largura, altura = vlm.preparar_envio(caminho)
    assert (largura, altura) == (1280, 720)
    imagem = cv2.imdecode(
        np.frombuffer(base64.b64decode(base64_jpeg), dtype=np.uint8), cv2.IMREAD_COLOR
    )
    assert imagem is not None
    assert imagem.shape[:2] == (720, 1280)


def test_pedir_tenta_de_novo_em_429_e_depois_responde(monkeypatch) -> None:
    """Dois 429 seguidos e depois resposta boa: uma só entrada, com 3 tentativas."""
    respostas = [
        urllib.error.HTTPError(vlm.URL_PROXY, 429, "limite", None, None),
        urllib.error.HTTPError(vlm.URL_PROXY, 429, "limite", None, None),
        '{"braco": "sim"}',
    ]

    def falso(modelo: str, conteudo: list) -> str:
        proxima = respostas.pop(0)
        if isinstance(proxima, Exception):
            raise proxima
        return proxima

    monkeypatch.setattr(vlm, "_chamar_uma_vez", falso)
    monkeypatch.setattr(vlm.time, "sleep", lambda s: None)
    registro = vlm.pedir("modelo-x", "q01", [])
    assert registro["erro"] is None
    assert registro["tentativas"] == 3
    assert registro["conteudo"] == '{"braco": "sim"}'


def test_pedir_erro_400_nao_tenta_de_novo(monkeypatch) -> None:
    """Erro 400 não é transitório: uma tentativa e erro gravado."""

    def falso(modelo: str, conteudo: list) -> str:
        raise urllib.error.HTTPError(vlm.URL_PROXY, 400, "ruim", None, None)

    monkeypatch.setattr(vlm, "_chamar_uma_vez", falso)
    monkeypatch.setattr(vlm.time, "sleep", lambda s: None)
    registro = vlm.pedir("modelo-x", "q01", [])
    assert registro["erro"] == "HTTP 400"
    assert registro["tentativas"] == 1
