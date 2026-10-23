# 0215 — Símbolos de expressão no gerador e a T8.5 no treino

Segue a [0214](0214-r4h-ligaduras.md). Escrito **antes** de treinar e de medir (2026-10-23).

## Por que

- O `_atqr` reprovou na T8.5 só pelo custo: 454/3909 (11,6 %), com o teto de 10 %. O "sim"
  falso passou: 6/138 (4,3 %).
- No diagnóstico da semente 1 (`r4h/diagnostico_t85.py`), as 147 notas atacadas lidas como
  "não" se dividem assim:
  - 79 têm todas as técnicas abaixo de 0,05. São notas comuns que caem pelo `L` 0,01;
  - 96 têm o mordente acima do `L`;
  - 49 vêm de uma tela só, a 3 (*Smile*, guitar dell'arte);
  - o resto fica perto de um símbolo que não muda o ataque: um "p" de dinâmica, uma
    fermata ou um "harm." escrito acima, uma nota de enfeite.
- O `L` sai dos ouros, que são 8 vídeos de poucos canais. Num canal que o treino não viu, a
  probabilidade de técnica em nota comum sobe, e a faixa "não sei" fica larga demais.

## A pergunta

Com as telas da T8.5 no treino (15 canais novos) e com os símbolos de expressão no gerador, o
rótulo de ataque passa na prova lacrada T8.6?

## A mudança

**1. A T8.5 no treino** (`n4/treinar_ft.py --t85`):
- O cache sai de `n4/extrair_t85.py`, com o recorte alto: são **28 telas e 1351 notas** com
  casa numérica. As cordas do painel batem com as da ferramenta nas 28.
- A técnica vem do `r2/conferir_t85/ataque_t85.json`, revisado pelo dono. A T8.5 está gasta
  (0214) e já não serve de prova.

**2. G16 no gerador** (`tab/tablatura/treino/sintetico_sistema.py`):

| | o que é | chance |
| --- | --- | --- |
| `P_EXPRESSAO` | de 1 a 3 marcas acima da corda 1, que não mudam o ataque | 0,5 por sistema |
| `TEXTOS_EXPRESSAO` | "p", "pp", "mp", "mf", "f", "rit.", "a tempo", "cresc.", "dim." | — |
| `P_FERMATA` | a marca é uma fermata (arco com ponto) em vez de texto | 0,35 por marca |

- A marca fica entre 1,0 e 1,7 passo acima da corda 1. Ela não entra:
  - a menos de 0,2 passo de uma nota;
  - no vão de um arco (h, p, ligadura, slide ligado) ou de um arco solto, com meio passo de
    folga. Um "p" de dinâmica em cima de um arco viraria a letra do pull-off;
  - em cima de outro item de estrutura ou de um nome de acorde.
- As notas embaixo continuam com o rótulo que já tinham: a marca não muda nada.
- **A amostra, medida antes de treinar** (`tab_rotulo/r5/amostra.py`, 2000 sistemas das
  sementes de treino): **509 sistemas** com pelo menos uma marca. Olhei os exemplos em
  `r5/exemplos_g16.png`: o texto e a fermata saem acima do sistema, sem cobrir nota nem arco.

**O treino** é o do `_atqr` mais `--t85`:
`--passos 3000 --ataque --t82 --recorte-alto --t83-toda --t84 --t85`. São 5 dobras × 3
sementes, com o nome `_atqs_s<semente>`, no roteiro `r5/rodar.sh`. O `DETECTOR_PADRAO` não muda.

## A prova lacrada: T8.6

- **Sorteio:** `data/saida/tablatura/t86/gerar.py`, com `random.Random(4)`.
  - Ficam fora os vídeos do ouro e os da T8.2, da T8.3, da T8.4 e da T8.5: nenhum se repete.
  - São 2 vídeos por canal, em 15 canais, num total de 30 telas.
  - Uma tela saiu sem painel (*nostalgia*, guitar dell'arte). A ferramenta tem 29.
- **Telas com o painel errado, vistas antes de qualquer medida** (`t86/folha_paineis_*.jpg`):
  - a **3** não tem tablatura no quadro: só o violão;
  - na **28**, as cordas ficaram em cima do vídeo, e não da tablatura.

  As duas ficam fora se o dono não as conferir. Só contam as telas marcadas como conferidas.
- **Gabarito:** o dono confere as casas e depois o ataque, nos dois passes de sempre. O
  resultado vai para `r2/conferir_t86/ataque_t86.json`. **Nenhum modelo de ataque é medido
  nem mostrado na T8.6** antes da medida. O pré-preenchimento das casas é a leitura do produto,
  e não tem ataque.
- A medida espera `r5/t86_liberada.json`, gravado depois que o dono termina.

## A medida e o critério

**1. Nos ouros** (`r5/decidir.py`, sem ler a T8.6):
- O `ataque_r4 medir --versao atqs` usa as dobras fora e as 3 sementes, nos ouros revisados.
- O limiar da técnica e o `L` saem dos ouros, como sempre (`escolher_limiar` e
  `escolher_nao_sei`).
- O `_atqs` **passa nos ouros** se:
  - o custo fica ≤ 10 % em cada semente;
  - a pior semente de casa não fica mais de 2 abaixo da pior do `_atqr`;
  - o "sim" falso somado não passa o do `_atqr` (9/258) **mais 3**.

  A régua é o `_atqr` medido em 2026-10-23 (`r4a/medida_atqr_s*_alto.json`).
- **Se não passar:** a T8.6 **não se gasta**, e nada muda no produto.

**2. Na T8.6, uma vez só** (`r5/medir_t86.py atqs`, dobra 0, 3 sementes, recorte alto, `L`
dos ouros):
- O "sim" falso e o custo são contados como na 0214, com a regra do slide sem origem.
- **Aceite (o do plano):** com as 3 sementes somadas, "sim" falso ≤ 5 % e custo ≤ 10 %.
- **Se passar:**
  - o `ataque_rotulo.DETECTOR_CALIBRADO` passa a `_atqs_s1`, com os limiares dos ouros;
  - a etapa do rótulo de ataque fecha.
- **Se reprovar:** a T8.6 fica gasta, os erros viram o diagnóstico seguinte e o
  `DETECTOR_CALIBRADO` não muda.
- **Depois**, só para informar, o `_atqr` é medido na T8.6 do mesmo jeito
  (`medir_t86.py atqr`). Ele não decide nada.
- **Em nenhum caso** o `DETECTOR_PADRAO` muda sem o OK do dono.

## O que fica de fora

- As duas mudanças entram juntas, e o resultado não separa o efeito de cada uma.
- O `L` continua sendo escolhido só nos ouros, pela mesma regra. Mudar a regra agora seria
  escolher olhando a T8.5.
- Continuam como dívida:
  - o X sem número;
  - as chaves do ataque que deslizam quando o dono põe uma nota no modo normal;
  - a divergência da Gymnopédie.
