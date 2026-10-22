"""Testes do sorteio da folha de conferência (M0): ``tab.maos_conferencia``.

Cobre só a lógica pura: ``sortear`` (estratificação por canal, maiores restos, corte,
exclusão, quadros vazios, chaves repetidas, ordem) e ``escolher_quadro``. Os vídeos são
sintéticos, com quadros mínimos; nada aqui abre disco, imagem ou MediaPipe.
"""

import random
from collections import Counter

import pytest

from tab.maos import conferencia as maos_conferencia


def _videos(canal: str, quantidade: int) -> list[dict]:
    """Vídeos sintéticos de um canal, com um quadro cada e chaves em ordem."""
    return [
        {
            "chave": f"{canal}/{k:04d}.mp4",
            "canal": canal,
            "quadros": [{"i": 0, "t": 1.0}],
        }
        for k in range(quantidade)
    ]


def _por_canal(escolhidos: list[dict]) -> Counter:
    """Quantos vídeos sorteados há em cada canal."""
    return Counter(v["canal"] for v in escolhidos)


def test_mesma_semente_da_a_mesma_lista() -> None:
    videos = _videos("alfa", 200) + _videos("beta", 100) + _videos("gama", 10)
    primeira = maos_conferencia.sortear(videos, 30, 7, set())
    segunda = maos_conferencia.sortear(videos, 30, 7, set())
    assert primeira == segunda


def test_resultado_nao_depende_da_ordem_da_entrada() -> None:
    videos = _videos("alfa", 200) + _videos("beta", 100) + _videos("gama", 10)
    direta = maos_conferencia.sortear(videos, 30, 7, set())
    invertida = maos_conferencia.sortear(list(reversed(videos)), 30, 7, set())
    assert direta == invertida


def test_semente_diferente_da_outra_lista() -> None:
    # 310 vídeos e 30 sorteados: a chance de duas sementes darem a mesma lista é
    # desprezível, e o resultado é fixo para estas duas sementes.
    videos = _videos("alfa", 200) + _videos("beta", 100) + _videos("gama", 10)
    primeira = maos_conferencia.sortear(videos, 30, 7, set())
    outra = maos_conferencia.sortear(videos, 30, 8, set())
    assert primeira != outra


def test_total_e_n_quando_ha_videos_de_sobra() -> None:
    videos = _videos("alfa", 50) + _videos("beta", 40)
    assert len(maos_conferencia.sortear(videos, 30, 1, set())) == 30


def test_canal_com_dez_ou_mais_videos_sempre_tem_um_sorteado() -> None:
    # Canal "gama" tem 10 vídeos, bem menos que os outros. Contas à mão (n=5):
    #   garantidas: alfa, beta e gama ganham 1 cada; sobra = 5 - 3 = 2.
    #   total = 200 + 100 + 10 = 310. Cotas da sobra (2 x vídeos / 310):
    #     alfa 400/310 = 1 + resto 90;  beta 200/310 = 0 + resto 200;
    #     gama  20/310 = 0 + resto  20.
    #   Partes inteiras: alfa 1, beta 0, gama 0 -> alfa 1+1 = 2, beta 1, gama 1 (4 vagas).
    #   Falta 1 vaga: maior resto é beta (200), vai para beta -> 2.
    #   Resultado esperado: alfa 2, beta 2, gama 1.
    videos = _videos("alfa", 200) + _videos("beta", 100) + _videos("gama", 10)
    escolhidos = maos_conferencia.sortear(videos, 5, 20261013, set())
    contagem = _por_canal(escolhidos)
    assert contagem["gama"] >= 1
    assert contagem == Counter({"alfa": 2, "beta": 2, "gama": 1})


def test_nenhum_video_excluido_aparece() -> None:
    videos = _videos("alfa", 20) + _videos("beta", 20)
    excluir = {v["chave"] for v in videos[:5]}
    escolhidos = maos_conferencia.sortear(videos, 10, 1, excluir)
    assert len(escolhidos) == 10
    assert not {v["chave"] for v in escolhidos} & excluir


def test_video_sem_quadros_nunca_aparece() -> None:
    vazios = [
        {"chave": f"vazio/{k}.mp4", "canal": "alfa", "quadros": []} for k in range(5)
    ]
    escolhidos = maos_conferencia.sortear(_videos("alfa", 20) + vazios, 10, 1, set())
    assert not [v for v in escolhidos if v["chave"].startswith("vazio/")]


def test_chave_repetida_entra_uma_vez() -> None:
    videos = _videos("alfa", 20) * 2
    chaves = [v["chave"] for v in maos_conferencia.sortear(videos, 10, 1, set())]
    assert len(chaves) == len(set(chaves)) == 10


def test_n_maior_que_o_disponivel_devolve_todos() -> None:
    videos = _videos("alfa", 3) + _videos("beta", 2)
    escolhidos = maos_conferencia.sortear(videos, 100, 1, set())
    assert escolhidos == sorted(videos, key=lambda v: (v["canal"], v["chave"]))


def test_saida_ordenada_por_canal_e_chave() -> None:
    videos = list(reversed(_videos("beta", 3) + _videos("alfa", 3)))
    escolhidos = maos_conferencia.sortear(videos, 4, 1, set())
    pares = [(v["canal"], v["chave"]) for v in escolhidos]
    assert pares == sorted(pares)


def test_maiores_restos_nao_arredonda_cada_canal() -> None:
    # Canais a (5), b (3), c (2): nenhum tem 10, então a sobra é toda a amostra (n=3).
    #   total = 10. Cotas: a = 3*5/10 = 1,5 (parte 1, resto 5/10);
    #                      b = 3*3/10 = 0,9 (parte 0, resto 9/10);
    #                      c = 3*2/10 = 0,6 (parte 0, resto 6/10).
    #   Partes somam 1; faltam 2 vagas, dadas aos maiores restos: b (9/10), depois c (6/10).
    #   Resultado: a 1, b 1, c 1. Arredondando cada cota (1,5 -> 2) daria 4 vagas.
    videos = _videos("a", 5) + _videos("b", 3) + _videos("c", 2)
    escolhidos = maos_conferencia.sortear(videos, 3, 1, set())
    assert _por_canal(escolhidos) == Counter({"a": 1, "b": 1, "c": 1})


def test_empate_no_resto_vai_para_o_nome_menor() -> None:
    # a (2) e b (2), n=1: total = 4. Cotas 1*2/4 = 0,5 cada, mesmo resto (1/2).
    # Empate: a vence pela ordem alfabética do nome.
    videos = _videos("a", 2) + _videos("b", 2)
    escolhidos = maos_conferencia.sortear(videos, 1, 1, set())
    assert _por_canal(escolhidos) == Counter({"a": 1})


def test_canal_nunca_recebe_mais_vagas_do_que_videos() -> None:
    # a (10) e z (290), n=299, total = 300. Sobra = 299 - 2 garantidos = 297.
    #   Cota de a = 297*10/300 = 9,9 (parte 9, resto 0,9). Com a garantida, a = 10,
    #   que é o total de a: o corte fica no limite.
    #   Cota de z = 297*290/300 = 287,1 (parte 287, resto 0,1). z = 1 + 287 = 288.
    #   Soma das partes: 10 + 288 = 298; falta 1 vaga. O maior resto é a (0,9), mas a
    #   já está no limite, então a vaga passa para z: z = 289.
    #   Resultado: a 10, z 289. Sem o corte, a receberia 11 vagas.
    videos = _videos("a", 10) + _videos("z", 290)
    escolhidos = maos_conferencia.sortear(videos, 299, 1, set())
    assert _por_canal(escolhidos) == Counter({"a": 10, "z": 289})


def test_garantidos_que_nao_cabem_levantam_erro() -> None:
    videos = _videos("alfa", 10) + _videos("beta", 10)
    with pytest.raises(ValueError, match="vaga garantida não cabe"):
        maos_conferencia.sortear(videos, 1, 1, set())


def test_escolher_quadro_devolve_um_dos_quadros() -> None:
    video = {"chave": "x", "canal": "alfa", "quadros": [{"i": k} for k in range(5)]}
    escolhido = maos_conferencia.escolher_quadro(video, random.Random(1))
    assert escolhido in video["quadros"]


def test_escolher_quadro_mesma_semente_mesma_sequencia() -> None:
    video = {"chave": "x", "canal": "alfa", "quadros": [{"i": k} for k in range(12)]}
    rng_a, rng_b = random.Random(3), random.Random(3)
    primeira = [maos_conferencia.escolher_quadro(video, rng_a) for _ in range(20)]
    segunda = [maos_conferencia.escolher_quadro(video, rng_b) for _ in range(20)]
    assert primeira == segunda
