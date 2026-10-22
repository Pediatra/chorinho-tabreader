"""Intervalos de notação: o vídeo não é uma coisa só.

O dono do projeto descreveu e a medição confirmou: a tablatura **aparece e desaparece**.
No `sky guitar` ela aparece da metade para o fim (20 de 20 vídeos chamados de "sem
tablatura" por um instante único têm tablatura em algum instante). Então a saída é uma
lista de intervalos, não um JSON do vídeo.

Estes testes cobrem a parte pura (agrupamento e escolha da melhor amostra); o resto do
caminho lê vídeo e é aferido em vídeo real.
"""

from __future__ import annotations

from tab.tablatura.produto.pipeline import Intervalo, agrupar_intervalos


def _amostra(t: float, tem: bool, uniformidade: float = 0.9, glifos: int = 20) -> dict:
    return {
        "t": t,
        "tem_notacao": tem,
        "uniformidade": uniformidade,
        "glifos": glifos,
        "passo": 20.0,
    }


def test_sem_notacao_nao_gera_intervalo() -> None:
    """Vídeo inteiro sem notação não vira intervalo nenhum."""
    assert agrupar_intervalos([_amostra(10, False), _amostra(20, False)]) == []


def test_amostras_vizinhas_viram_um_intervalo() -> None:
    """Duas amostras com notação perto viram um intervalo contíguo."""
    intervalos = agrupar_intervalos(
        [_amostra(0, False), _amostra(60, True), _amostra(70, True)], folga_s=20
    )
    assert len(intervalos) == 1
    assert intervalos[0].t0 == 40
    assert intervalos[0].t1 == 90
    assert len(intervalos[0].amostras) == 2


def test_amostras_distantes_viram_intervalos_separados() -> None:
    """Dois trechos com notação, longe um do outro, são dois intervalos."""
    intervalos = agrupar_intervalos(
        [_amostra(60, True), _amostra(300, True)], folga_s=20
    )
    assert len(intervalos) == 2
    assert [i.t0 for i in intervalos] == [40, 280]


def test_melhor_amostra_prefere_o_painel_mais_confiavel() -> None:
    """Entre as amostras com notação, vale a de maior uniformidade (e mais glifos)."""
    intervalo = Intervalo(
        t0=0,
        t1=100,
        amostras=[
            _amostra(10, False),
            _amostra(20, True, uniformidade=0.80, glifos=40),
            _amostra(30, True, uniformidade=0.93, glifos=10),
        ],
    )
    melhor = intervalo.melhor_amostra()
    assert melhor is not None
    assert melhor["t"] == 30


def test_intervalo_sem_notacao_nao_tem_melhor_amostra() -> None:
    """Sem notação, `melhor_amostra` é None — não se inventa painel."""
    intervalo = Intervalo(t0=0, t1=10, amostras=[_amostra(5, False)])
    assert intervalo.melhor_amostra() is None


def test_amostra_com_passo_implausivel_e_descartada() -> None:
    """Passo de 7,6 px é painel falso: a faixa medida no acervo é 14–45 px.

    Medido no `sky guitar` (henze): a amostra suspeita tinha a MAIOR uniformidade (0,877
    contra 0,867) e era escolhida, apesar de ter metade dos glifos e passo fora da faixa.
    """
    intervalo = Intervalo(
        t0=0,
        t1=100,
        amostras=[
            {
                "t": 10,
                "tem_notacao": True,
                "uniformidade": 0.877,
                "passo": 7.6,
                "glifos": 67,
            },
            {
                "t": 20,
                "tem_notacao": True,
                "uniformidade": 0.867,
                "passo": 16.0,
                "glifos": 114,
            },
        ],
    )
    melhor = intervalo.melhor_amostra()
    assert melhor is not None
    assert melhor["t"] == 20
