"""As funções unificadas em ``tab/comum`` (decisão 9001, regras 13 e 14).

1. Cada nome antigo continua no módulo de origem e é o mesmo objeto do comum. Isso também
   impede um ``ruff --fix`` de apagar uma reexportação calado.
2. A altura das notas sai igual por todos os caminhos, em toda corda e casa, e o capo só
   entra quando quem chama passa o capo.
"""

from __future__ import annotations

import importlib

import pytest

from tab.audio import onsets, som_medir
from tab.comum import acervo, arquivos, semente, violao
from tab.tablatura.produto import musicxml

REEXPORTACOES = [
    ("tab.maos.gabarito", "gravar_atomico", arquivos.gravar_atomico),
    ("tab.tablatura.ouro.ouro_video", "gravar_atomico", arquivos.gravar_atomico),
    ("tab.maos.braco.ciclo", "_ler_json", arquivos.ler_json),
    ("tab.maos.braco.detector", "_ler_json", arquivos.ler_json),
    ("tab.maos.padroes_preparar", "_ler_json", arquivos.ler_json),
    ("tab.maos.braco.capo_imagem", "_nfc", arquivos.nfc),
    ("tab.maos.braco.nut_fora", "_nfc", arquivos.nfc),
    ("tab.maos.braco.regua", "_nfc", arquivos.nfc),
    ("tab.maos.braco.retreino", "_nfc", arquivos.nfc),
    ("tab.maos.braco.retreino_capo3", "_nfc", arquivos.nfc),
    ("tab.tablatura.produto.video", "_slug", arquivos.slug),
    ("tab.tablatura.censo.censo", "chave_de", acervo.chave_de),
    ("tab.tablatura.censo.censo", "chave_do_arquivo", acervo.chave_do_arquivo),
    ("tab.tablatura.censo.censo", "ler_rollout", acervo.ler_rollout),
    ("tab.tablatura.censo.censo", "canais_fora", acervo.canais_fora),
    ("tab.tablatura.treino.sintetico", "fixar_semente", semente.fixar_semente),
    ("tab.audio.onsets", "MIDI_CORDA", violao.AFINACAO_MIDI),
    ("tab.audio.som_medir", "ALTURA_SOLTA", violao.AFINACAO_MIDI),
    ("tab.maos.corda_sem_direita", "AFINACAO_MIDI", violao.AFINACAO_MIDI),
    ("tab.maos.direita.desempate", "AFINACAO_MIDI", violao.AFINACAO_MIDI),
]


@pytest.mark.parametrize(
    ("modulo", "nome", "objeto"), REEXPORTACOES, ids=lambda x: str(x)[:40]
)
def test_o_nome_antigo_continua_no_modulo_de_origem(modulo, nome, objeto):
    assert getattr(importlib.import_module(modulo), nome) is objeto


def test_a_afinacao_e_a_de_sempre():
    assert violao.AFINACAO_MIDI == {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}


@pytest.mark.parametrize("corda", range(1, 7))
def test_a_altura_sai_igual_por_todos_os_caminhos(corda):
    for casa in range(25):
        esperado = violao.AFINACAO_MIDI[corda] + casa
        assert musicxml.midi_da_corda(corda, casa) == esperado
        assert onsets.midi_da_nota(corda, casa) == esperado
        assert som_medir.midi_da_nota(corda, casa) == esperado


def test_o_capo_so_entra_quando_quem_chama_passa():
    assert som_medir.midi_da_nota(1, 3, capo=2) == 64 + 3 + 2
    assert onsets.midi_da_nota(1, 3, transposicao=2) == 64 + 3 + 2
    assert musicxml.midi_da_corda(1, 3) == 64 + 3


def test_slug_e_nfc_como_antes():
    assert arquivos.slug("/acervo/canal/vídeo: ótimo!.mp4") == "vídeo_ótimo"
    assert arquivos.slug("/x/!!!.mp4") == "video"
    assert arquivos.nfc("á") == "á"
