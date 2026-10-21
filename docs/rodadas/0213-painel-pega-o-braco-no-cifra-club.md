# 0213 — O painel pega o braço do violão no cifra club

O diagnóstico e o pré-registro foram escritos **antes** de mudar o código (2026-10-21).

## O que se viu

- **Na T8.4, tela `c01_v1`** (cifra club, *até que durou*, t = 112,98 s): o
  `painel.escolher_ou_mascara` pegou o braço do violão, que está horizontal no topo, e o
  produto leu 14 notas falsas. A TAB escura embaixo ficou perdida. A correção está na 0211.
- **No canal inteiro** (`diag/painel_cifra.py`): 1 quadro por vídeo do cifra club com
  tablatura no censo, no instante com tab mais perto do meio da janela. São 197 vídeos.
  Olhei as **quatro folhas inteiras**:

  | o que o painel pegou | quadros |
  | --- | --- |
  | a TAB certa | 160 |
  | **o braço do violão, com uma TAB escura embaixo** | **28 (14 %)** |
  | sem painel, com uma TAB que ficou de fora (seguro) | 5 |
  | sem painel, e o quadro não tem TAB | 4 |

- **A causa** (`diag/escura_no_braco.py`, em 6 dos 28):
  - O `escolher` devolve o braço.
  - O `_cordas_convergem` dá False, porque no cifra club o braço é filmado reto.
  - Por isso a via da TAB escura (`candidatos_escuros_estreitos`) não é tentada. Quando é
    tentada, ela acha a TAB em 5 dos 6.
- **Um aviso sobre o censo:** 4 dos 197 instantes "com tab" no censo não têm TAB. Isso fica
  anotado, mas não é desta rodada.

## A mudança (só esta)

- Em `escolher_ou_mascara`, quando o escolhido **não** converge, a via da TAB escura também é
  tentada.
- Se ela achar uma TAB cujas cordas **não se sobrepõem** às do escolhido, essa TAB escura
  vence.
- Se as cordas se sobrepõem, o escolhido fica, porque é a mesma TAB. Essa é a guarda dos 160
  que já acertam e dos outros canais.
- O custo é de ~0,7 s a mais por tela: o `tab.video` chama o painel uma vez por tela.

## As amostras

1. **Desenho:** os 197 quadros acima. A regra foi pensada olhando eles, então essa amostra
   não é prova.
2. **Prova no canal:** um quadro novo por vídeo do cifra club, no instante com tab mais perto
   de 1/4 da janela de tablatura.
3. **Regressão fora do canal:** todas as telas conferidas dos 8 ouros, da T8.2 e da T8.3. A
   T8.4 fica de fora, porque está lacrada para a 0211.

Nas três, o mesmo quadro é avaliado pela regra antiga e pela nova, no mesmo processo.

## O critério

- **Desenho:** dos 28 braços, no máximo 3 continuam no braço. Nenhum dos 160 certos muda.
- **Prova no canal:**
  - os braços caem pelo menos à metade (pela posição, na metade de cima; todo quadro que
    muda é olhado na folha);
  - nenhum quadro passa de TAB para não-TAB.
- **Regressão:**
  - nenhuma tela muda de painel;
  - se alguma mudar, é olhada no quadro inteiro, e uma troca para um painel errado reprova.

## O que fazer

- **Passa:** a mudança entra em `painel.escolher_ou_mascara`, com um teste.
  - O produto muda nos vídeos do cifra club em que o painel pegava o braço: as notas falsas
    saem e a TAB passa a ser lida.
  - A leitura dos 8 ouros não muda, porque a regressão garante.
- **Não passa:** o código fica como está e a mudança vai para a tabela "não repetir".

## Resultado (2026-10-21)

Script `diag/painel_0213.py`: as duas regras rodam no mesmo quadro. Olhei as folhas de todas
as trocas (`painel_0213/folha_*.jpg`), com o painel antigo em vermelho e o novo em verde.

| amostra | quadros | braço, regra antiga | braço, regra nova | trocas | troca para pior |
| --- | --- | --- | --- | --- | --- |
| desenho | 197 | 28 | **3** | 25 | 0 |
| prova (instante a 1/4) | 197 | 25 | **5** | 20 | 0 |
| regressão (ouros, T8.2 e T8.3) | 132 | — | — | **1** | 0 |

- **Passa nos três critérios.**
  - Nas 46 trocas do cifra club, o painel sai do braço e vai para a TAB escura, e nenhuma
    troca leva a "sem painel".
  - A única troca da regressão é a `t83#2`, uma tela do cifra club na T8.3. Ela também sai do
    braço e vai para a TAB.
  - Nenhuma tela dos 8 ouros nem da T8.2 muda.
- **O que sobra:** 3 e 5 quadros continuam no braço. Neles, a via da TAB escura não acha a
  TAB (como no `k100`, de passo 10,6).
- **A mudança entra** em `painel.escolher_ou_mascara`, com 3 testes em
  `tests/test_painel_braco.py`. Os produtos já gerados para esses vídeos do cifra club só
  mudam quando forem refeitos.
- **Sobre a T8.3:** ela foi lida com o painel antigo, e a tela 2 dela estava no braço. A
  T8.3 já estava gasta (0210) e não é refeita.
