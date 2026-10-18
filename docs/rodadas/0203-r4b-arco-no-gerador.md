# 0203 — R4b: os estilos de arco que o gerador não desenha

Segue a [0202](0202-r4a-arco-real-no-ajuste-fino.md), que não passou: o "sim" falso ficou em
37–41 % nos ouros e 51–54 % na T8.2. Escrito **antes** de mexer no gerador e de treinar.

## A folha dos erros do R4a (2026-10-18)

Script `data/saida/tab_rotulo/r4a/folha_erros.py`. Saída em `data/saida/tab_rotulo/r4a/erros/`:
`erros.json` e as folhas `folha_perdida_*.png` e `folha_alarme_*.png`, olhadas **inteiras**.
Uma nota "não" conta como perdida quando 2 ou mais das 3 sementes do `_atq` a leem atacada.

### Perdidas: 57 notas "não" lidas como atacadas

| motivo | perdidas | escore < 0,1 |
| --- | --- | --- |
| mordente | 33 | 25 |
| h | 10 | 8 |
| p | 8 | 6 |
| prolongamento | 3 | 3 |
| slide_ligado | 3 | 3 |

O escore é o maior sigmóide das 7 técnicas sem ataque no bin da nota. **Não é limiar**: em 45
das 57, o sinal está abaixo de 0,1.

O que a folha mostra, e o gerador não desenha (`tab/sintetico_sistema.py`):

1. **Arco abaixo da corda.** Room 335 (os mordentes), Retrato (`2-3-2`), Kenneth, Serge
   Kottelat. O gerador só desenha arco **acima**: `y − 0,5 passo − 0,35 passo·sen`, em
   `_desenhar_tecnicas_pares` e no tie.
2. **Arco longo.** Room 335 t4, t6, t27 e Shin Izumi: o arco liga notas a 3–6 passos uma da
   outra. O gerador só liga colunas vizinhas.
3. **Arco de três notas** (o mordente do dono: `2-3-2` sob um arco só, e `2·4·2` no La Vie en
   Rose). O gerador não tem esse desenho. O `orn` dele é outra coisa: o algarismo pequeno do
   enfeite antes da nota.
4. **Forma.** Arcos rasos, que encostam na linha da corda, e arcos finos de curva alta (Mr.
   Tabs). O gerador usa uma altura fixa.

### Alarmes: 35 notas "sim" lidas como não atacadas

| causa | alarmes |
| --- | --- |
| slide de entrada (`/7` sem nota antes; o dono diz que é atacada) | 10 |
| arco que sai da nota para o vazio (sustentada) | 4 |
| traço `3-0-3` ligando algarismos, sem arco (South American) | 5 |
| zigue-zague de mordente sobre a nota (Robert Lunn; o dono diz que é atacada) | 1 |
| parênteses, bend/soltura e arco que começa na nota (decididos abaixo) | 7 |
| outros | 8 |

- **Slide de entrada.** O modelo vê o `/` e o produto chama de "não", porque a técnica fica
  na nota de chegada. Só que não há nota de partida.
- **Zigue-zague.** O gerador só desenha o zigue-zague **junto** do enfeite `orn`. Por isso o
  modelo aprendeu "zigue-zague = sem ataque", o contrário da regra do dono.

### Decidido com o dono (2026-10-18)

Os 7 casos "a decidir" ficam como estão no gabarito ("sim"). São alarmes do modelo:

- `(3)` e `(0)` entre parênteses (ギタロー, T8.2 t36) são nota opcional ou fantasma: tocada
  fraca ou deixada soar. É ataque.
- `b9r8` (o `8` da soltura do bend) e `7\` (slide que sai da nota), no Cifra Club, T8.2 t2: são
  ataque, pela confirmação do dono.
- From This Place `4·4` (t4-n70, t5-n3): o arco **começa** nesse 4 e passa a barra, então ele é
  atacado. t1-n63 é `5-4-2-0`, só com traços, sem arco. O gabarito está certo nos três (lido no
  recorte largo, `data/saida/tab_rotulo/r4a/duvidas/`).

## O que muda

### Passo A — regra do slide sem origem (sem treino, CPU)

No produto, `/` ou `\` numa nota **sem** nota na mesma corda até 3 passos à esquerda vira
ataque "sim" (`slide_entrada`). Mede-se nas leituras do `_atq` já gravadas. Esperado: −10
alarmes no Room 335, e nenhuma perdida a mais. É a regra do dono, e não um ajuste ao teste.

### Passo B — gerador (`tab/sintetico_sistema.py`)

| id | mudança | rótulo |
| --- | --- | --- |
| G1 | arco de h, p e tie **abaixo** da corda (chance 0,4) | o de hoje |
| G2 | arco **longo**: h, p ou tie entre notas a 2–5 colunas, com colunas vazias no meio | o de hoje, na nota de chegada |
| G3 | **forma** sorteada: altura 0,15–0,7 passo, deslocamento 0,1–0,6 passo, ponta no centro ou na borda da caixa | o de hoje |
| G4 | **mordente de três notas**: `a-b-a` na mesma corda, um arco só acima ou abaixo das três | `orn` na 2ª e na 3ª |
| G5 | **zigue-zague sozinho** sobre uma nota comum | nenhuma técnica (atacada) |
| G6 | **traço** `-` entre algarismos da mesma corda (distrator) | nenhum |

Antes de treinar: uma folha de 24 sistemas gerados, olhada inteira, com cada mudança presente.
O casamento do rótulo é conferido em 5 casos de cada mudança.

### Treino e medida

- Igual ao R4a (`--ataque`, as mesmas dobras e passos), com o gerador novo. São 15 treinos
  (5 dobras × 3 sementes), cerca de 7 h de GPU. Nome: `_atqg_s<semente>`.
- A medida é a mesma (`tab.ataque_r4 medir`, com a versão `atqg`), com a regra do passo A.
- **Base**: o `_atq` do R4a, com a mesma regra do passo A.

## Aceite (o do plano, sem mudança)

Nos ouros fora da dobra e na T8.2, separados:

- "sim" falso **≤ 5 %**;
- "não" em nota atacada **≤ 10 %**;
- a casa não piora além da amplitude das sementes.

**Pare se** o "sim" falso na T8.2 não cair além da amplitude do `_atq` (51–54 %). Nesse caso
o problema não é o estilo de arco, e o próximo passo é o arco como objeto próprio (uma saída
de começo e fim de arco, a A2 antiga).

## Feito antes do treino (2026-10-18)

### Passo A: regra do slide sem origem

`tab.ataque_r4.ataque_com_regra`, com `ORIGEM_SLIDE_MAX = 3` passos, medido nas leituras do
`_atq` (o campo `regra` de `medida_atq_s<semente>.json`):

| teste | medida | sem a regra | com a regra |
| --- | --- | --- | --- |
| 8 ouros | "sim" falso | 31 · 34 · 33 /84 | 31 · 34 · 33 /84 |
| 8 ouros | "não" em atacada | 18 · 19 · 22 | **7 · 7 · 10** |
| T8.2 | "sim" falso | 21 · 22 · 22 /41 | 23 · 24 · 24 /41 |
| T8.2 | "não" em atacada | 8 · 7 · 8 | 6 · 5 · 6 |

Nos ouros, a regra tira 11 ou 12 alarmes e não perde nenhum ligado. Na T8.2, ela perde 2
slides ligados em cada semente e tira 2 alarmes. A distância de 3 passos fica como foi
registrada; não é ajustada olhando a T8.2.

### Passo B: o gerador

As mudanças estão em `tab/sintetico_sistema.py`. As chances ficam nas constantes `P_ARCO_*`,
`P_PAR_LONGO`, `P_MORDENTE_TRES`, `P_ZIGUE_SOZINHO` e `P_APERTADO`.

- **G1 e G3**: `_pontos_arco` sorteia o lado, a ponta (na borda das caixas ou no centro da
  nota), o afastamento da corda e a altura. Vale para h, p, tie e o mordente de três notas.
- **G2**: no par longo, as notas da corda que estão no meio saem.
- **G4**: `_sortear_mordente_tres` e `_desenhar_mordentes_tres`.
- **G5**: `_sortear_zigues` e `_desenhar_zigues`. O desenho do zigue-zague foi para `_zigue`.
- **G6**: colunas apertadas, com espaço de 0,6 a 1,1 passo. A primeira coluna fica onde ficaria
  com o maior espaço de antes (2,6 passos), para a fórmula não encostar nela.
- **G7** (novo, pela decisão do dono sobre os parênteses): `(n)` deixa de ser a técnica
  `lig`. Agora é nota atacada (`parenteses`). O tie continua `lig`.
  - Dívida: o modelo deixa de dizer "parênteses". A informação volta quando houver uma classe
    própria, que muda a cabeça do modelo.
- **Correção de passagem**: o diagrama de acorde agora evita também o enfeite (usava
  `medidas`, e não `alvos`). O teste `test_distratores_grandes_nao_cobrem_notas` pegou isso
  com a nova sequência de sorteios.

Frequência em 300 sistemas: arco abaixo 94, arco no centro 118, arco longo 35, mordente de três
notas 47, zigue-zague sozinho 87, colunas apertadas 65.

Folha: `data/saida/tab_rotulo/r4b/folha_gerador_{1,2,3}.png` (`folha_gerador.py`), com 4
sistemas de cada variante. Todas as notas sem ataque estão sublinhadas, com o nome da técnica,
e foram olhadas. O rótulo cai na nota certa: a chegada do arco longo e a 2ª e a 3ª do
mordente de três notas. As colunas apertadas, com enfeite, chegam a encostar os algarismos
pequenos.

## Resultado

(a preencher)
