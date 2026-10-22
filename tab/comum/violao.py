"""A física do violão que mais de uma trilha usa (decisão 9001).

``AFINACAO_MIDI`` é a altura MIDI de cada corda solta na afinação padrão. Ela existia em 4
cópias iguais (``audio_onsets.MIDI_CORDA``, ``audio_som_medir.ALTURA_SOLTA``,
``maos_corda_sem_direita.AFINACAO_MIDI`` e ``maos_direita_desempate.AFINACAO_MIDI``), que
agora reexportam esta. O ``musicxml`` guarda a mesma afinação em notas (``E4``…``E2``), e um
teste confere que as duas dão a mesma altura.

A altura que soa é corda solta + casa da tab + casa do capo (AGENTS §11). O capo é sempre
somado por quem chama, nunca aqui dentro.
"""

from __future__ import annotations

#: Corda (1 = aguda) -> MIDI da corda solta, na afinação padrão.
AFINACAO_MIDI = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
