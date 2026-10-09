# 0001 — Semente fixa não bastava: o treino era nondeterminístico

**Data:** 2026-10-08 · **Status:** aceita · **Substitui:** a premissa da regra nº 1 do
`AGENTS.md`

## Contexto

A regra nº 1 do projeto manda "fixar a semente e medir ≥3 execuções, reportando média e
amplitude". Ela foi adotada na rodada 20, quando o mesmo código, sem semente, deu 0,729 e
0,854. A conclusão registrada foi: *"sem semente fixa, o número é ruído"*.

Ao reproduzir o número oficial dentro do container recém-criado, treinei a **semente 2**
três vezes com **o mesmo comando e os mesmos dados**:

| execução (seed 2) | treino (acc final) | total | raman | paolo |
| --- | --- | --- | --- | --- |
| 1ª | 0,8434 | 0,927 (89/96) | 17/24 | 30/30 |
| 2ª | 0,8478 | **0,948** (91/96) | **20/24** | 29/30 |
| 3ª | 0,8453 | **0,896** (86/96) | 17/24 | 27/30 |

**Amplitude de 0,052 na mesma semente** — maior que boa parte dos "ganhos" que o projeto
atribuiu a mudanças de código (a mudança de fonte variável valeu +0,046; a rejeição por
assinatura, +0,038). Ou seja: parte da variação chamada de "efeito de semente" era, na
verdade, variação da GPU.

## Causa

`torch.manual_seed` controla a inicialização e o sorteio, mas **não** o resultado das
operações em CUDA: a convolução do cuDNN usa `atomicAdd` e escolhe algoritmo por
heurística. Nada no código desligava isso (`torch.backends.cudnn.deterministic` nunca era
definido).

## Opções

1. **Aumentar o número de execuções** e reportar distribuição. Não resolve: encarece cada
   medição sem tornar duas rodadas comparáveis.
2. **Desligar o nondeterminismo da GPU** (`cudnn.deterministic=True`,
   `cudnn.benchmark=False`, `use_deterministic_algorithms(True, warn_only=True)` e
   `CUBLAS_WORKSPACE_CONFIG=:4096:8`).
3. **Treinar em CPU.** Determinístico por natureza, mas joga fora a GPU e o modelo é
   pequeno demais para precisar disso.

## Decisão

**Opção 2**, numa função única (`tab.sintetico.fixar_semente`) chamada por `treinar`, com
`warn_only=True` para que um op sem caminho determinístico apareça como aviso em vez de
abortar o treino. As 3 sementes continuam sendo exigidas.

## Verificação

Repeti a semente 2 mais duas vezes **depois** do conserto: perda por época idêntica até a
4ª casa (0,6213 → 0,5488), acurácia de treino idêntica (0,8453) e **mesmo total (0,896)**
nas duas. `tests/test_determinismo.py` trava os flags e a reprodutibilidade da
inicialização.

## Consequências

- **Todo número medido antes desta decisão tem ruído de até ~0,05 embutido** e só pode ser
  comparado com folga maior que isso. Comparações apertadas do histórico (ex.: +0,038,
  +0,046) estão dentro do ruído e não deveriam ter sido tratadas como ganho;
- o número oficial foi **remedido** com o treino determinístico (ver `ESTADO.md`);
- o treino fica marginalmente mais lento, o que é irrelevante para este modelo;
- a regra nº 1 do `AGENTS.md` passou a exigir **semente + determinismo + 3 execuções**,
  nessa ordem: sem o segundo item, o primeiro não significa nada.
