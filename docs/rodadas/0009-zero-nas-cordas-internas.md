# Rodada 0009: o `0` perdido nas cordas internas (cobertura de escala do gerador)

Data: 2026-10-10. Referência de gabarito: `oficial_1/2/3` = 66, 71, 68 (72 glifos).
Árvore de medição: HEAD `c15cd72e` + as mudanças desta rodada (não commitadas no momento
da medição de treino; ver "Código" abaixo).

## Pergunta

No `retrato brasileiro` (ouro `retrato_brasileiro_v2`, 491 notas), seis notas somem do MVP:
`0`, `1` e `2` nas cordas internas 3 e 4, glifo próprio e limpo, com a linha da corda passando
por dentro. O classificador lê `harmonico`/`tecnica`/`12` e o algarismo certo nem entra no
top-3. Hipótese da tarefa: o gerador só desenha algarismo **estreito** com corda cortando no
meio, e falta cobertura. Medida antes de treinar (regra 2 do AGENTS).

## Medição da amostra (regra 2)

Script: `data/saida/rodada0009/medir_amostra.py` (saída: `amostra.json`, `lint_e_amostra.txt`).
Unidade: passos (`largura/passo`, `altura/passo`). `cruza` = fração em que a linha de corda
da grade cai dentro da caixa do glifo; `part2` = fração com 2 ou mais componentes.

| rótulo | origem | n | larg. med | alt. med | alt. p90 | cruza | part2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | **real** (ouro) | 150 | 0,64 | **0,93** | 0,97 | 1,00 | **0,00** |
| 0 | sintético oficial | 766 | 0,40 | 0,54 | 0,75 | 0,58 | 0,14 |
| 0 | sintético `--escala larga` | 749 | 0,50 | 0,75 | 0,94 | 0,77 | 0,31 |
| 2 | **real** | 144 | 0,65 | **0,93** | 1,01 | 1,00 | **0,00** |
| 2 | sintético oficial | 491 | 0,40 | 0,53 | 0,72 | 0,53 | 0,14 |
| 2 | sintético `--escala larga` | 454 | 0,50 | 0,72 | 0,94 | 0,74 | 0,25 |
| 1 | **real** | 51 | 0,37 | **0,93** | 0,97 | 1,00 | **0,00** |
| 1 | sintético oficial | 484 | 0,36 | 0,55 | 0,72 | 0,57 | 0,17 |
| 1 | sintético `--escala larga` | 468 | 0,46 | 0,75 | 0,93 | 0,77 | 0,29 |

Os outros algarismos (3–9) seguem o mesmo padrão: real com altura mediana 0,93 em todos os
rótulos com n ≥ 10, sintético com 0,50–0,57. O rótulo `harmonico` não tem amostra real no
ouro (0 notas com essa técnica), então não há comparação para ele.

**Leitura:**

1. **O algarismo real não é estreito em relação ao sintético.** A proporção largura/altura
   é parecida (real 0,69; sintético 0,74). O que falta é **escala**: o real tem altura
   0,93 passo, o sintético oficial no máximo 0,75 (fonte de 1,0 passo). A hipótese de
   "estreito" não se confirma; a de "pequeno" se confirma.
2. **A corda passa por cima do algarismo no sky guitar.** Nenhum glifo real partido
   (`part2` = 0,00 em 150 zeros, 144 dois, 51 um); o sintético parte 14–18 % dos glifos, porque
   metade das linhas corta a corda com um buraco em volta do algarismo. Esse é o modo "corda
   cortada" do gerador, que o MuseScore usa. O sky guitar desenha a corda por cima. A
   fração do real aqui vem de um canal só (um vídeo), não cobre os outros canais do gabarito.
3. **Escala larga aproxima a altura, mas traz a corda cortada junto.** Com `--escala larga`
   a altura p90 vai a 0,94 (real 0,97), e a mediana sobe de 0,54 para 0,75 (real 0,93). Porém
   `part2` sobe para 0,25–0,31, justamente o que o real não tem.

## Código (opt-in, padrão intacto)

- `tab/sintetico.py`: `gerar_linha(..., escala_larga=False)`; com a flag, metade das linhas
  desenha algarismo de 1,0 a 1,4 passo (fonte). Sem a flag não há sorteio extra: a sequência é
  a de antes. CLI: `--escala {normal,larga}` (padrão `normal`).
- `tests/test_escala_sintetica.py`: padrão idêntico à chamada sem a flag, reprodutibilidade
  com a flag, e padrão da CLI.
- Lint: `All checks passed!` e `78 files already formatted`. Testes: `343 passed, 3 deselected`
  (`data/saida/rodada0009/pytest.txt`).

## Treino (comando oficial + `--escala larga`, GPU, `--n-linhas 320 --epocas 22`)

```bash
python -m tab.sintetico --n-linhas 320 --epocas 22 --seed S --escala larga \
    --saida artefatos/candidato_0perdido_S
python -m tab.avaliar --modelo artefatos/candidato_0perdido_S/glifo_sint.pt
```

Sementes S = 1, 2, 3. Pesos em `artefatos/candidato_0perdido_{1,2,3}/`. Log:
`data/saida/rodada0009/treino_candidato.txt`.

| semente | candidato | referência `oficial_S` | diferença |
| --- | --- | --- | --- |
| 1 | **64/72** = 0,889 | 66 | −2 |
| 2 | **68/72** = 0,944 | 71 | −3 |
| 3 | **71/72** = 0,986 | 68 | +3 |
| **média** | **67,7/72 = 0,940** (203/216) | **0,949** (205/216) | **−0,009** |

Amplitude do candidato: 7 glifos (0,097). Amplitude das referências: 5 glifos (0,069).

## Aceite

| critério | resultado |
| --- | --- |
| média ≥ 0,949 (205/216) | **não passa**: 203/216 |
| nenhuma semente abaixo da referência em mais de 1 glifo | **não passa**: semente 1 (−2) e semente 2 (−3) |
| MVP (revocação > 485/491, 0 inventadas, casa ≥ 483/485, estado 39/40, falso 0) | **não rodado**: o critério do gabarito já reprova, e a regra manda não adotar |
| harmônico `<12>` da tela 12 fica em `nao_notas` | não medido (depende do MVP) |
| gate verde | ok (lint e 343 testes) |

**Decisão: não adotado.** `MODELO_PADRAO` continua `artefatos/oficial_3`, e os `oficial_*`
não mudam. A opção `--escala larga` fica no código, desligada, para não perder a medição.

## O que isto ensina (não repetir)

- **Cobertura de escala por si só não resolve o `0` perdido.** O ganho de altura não se
  converte em acerto no gabarito, e a semente 3 subiu +3 enquanto as outras caíram: a
  variação entre sementes continua maior do que o efeito medido (amplitude 0,097 contra
  um efeito de −0,009). Pela regra 1, não há como separar o efeito do ruído com 3 sementes.
- **O gargalo provável é o modo "corda por cima".** A amostra real não tem glifo partido,
  e o sintético parte 14–31 % dos glifos. Essa é a próxima hipótese a medir, e ela é de
  dado (fração do modo "corda cortada" por canal), não de escala. Não foi testada aqui.
- **Medição de "cruza" é sensível à definição.** Ela usa a grade de cordas, não os pixels,
  então 1,00 no real pode ser só o algarismo estar centrado na corda. Não serve sozinha para
  afirmar que a corda atravessa o glifo; a conclusão 2 se apoia em `part2`, que é mais limpa.

## Limites declarados

- A amostra real vem de **um** vídeo (sky guitar, retrato brasileiro), 491 notas ligadas a
  glifos. Outros canais não foram medidos nesta rodada.
- O ouro não tem `harmonico` com glifo real, então o rótulo `harmonico` não foi comparado.
- Não foi rodado o MVP com o candidato. Se o critério do gabarito virar aprovação em outra
  rodada, o MVP passa a ser obrigatório antes de adotar.
- Sem commit de `data/saida/` (fora do git por padrão). Os números estão nesta rodada e em
  `data/saida/rodada0009/`.

## Artefatos

- Medição: `data/saida/rodada0009/medir_amostra.py`, `amostra.json`, `lint_e_amostra.txt`.
- Treino e avaliação: `data/saida/rodada0009/treino_candidato.txt`.
- Pesos (não versionados, `*.pt`): `artefatos/candidato_0perdido_{1,2,3}/`.
- Testes: `data/saida/rodada0009/pytest.txt`.
