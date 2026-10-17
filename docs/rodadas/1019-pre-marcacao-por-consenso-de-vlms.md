# 1019 — Pré-marcação do braço por consenso de 6 modelos de visão

**Data**: 2026-10-17. **Estado**: regras a priori. Este documento ganha commit antes de
qualquer pedido de marcação aos modelos.

**Pedido do dono**: o dono tem 6 modelos de visão gratuitos atrás de um proxy local
(`http://127.0.0.1:8787/v1/chat/completions`, formato OpenAI). A ideia é usar as respostas
cruzadas deles como pré-marcação: o dono só revisaria, sem o teto de 500 marcas.

**Antecedente**: na [1016](1016-llm-marca-o-braco.md), o Opus marcou pixels e reprovou.
Nos braços diagonais, errou o braço inteiro.

## Pergunta

Quando os modelos concordam entre si, a marcação deles está certa? Se sim, em quantos
quadros isso acontece? Isso decide se vale montar a pré-revisão: o dono confere só os
quadros de consenso, e o resto ele marca como hoje.

## Modelos e acesso

| modelo | id no proxy |
| --- | --- |
| GLM | `glm-5.3-flash-free` |
| DeepSeek | `deepseek-v4.1-flash-free` |
| LongCat | `longcat-2.5-preview-free` |
| MiMo | `mimo-v2.6-flash-free` |
| Space Bunny | `space-bunny-free` |
| Nemotron | `nemotron-3.5-super-vl-free` |

- Os 6 são gratuitos, e os quadros saem para os servidores deles; o dono montou o proxy
  para isso.
- Todos os pedidos usam `temperature 0`.
- O GLM devolveu 429 (limite de taxa) na sonda, e o Nemotron levou 113 s. Por isso, cada
  pedido tem até 4 tentativas com espera crescente e limite de 300 s. Falha final vale
  "não respondeu".

**Sonda de coordenadas** (feita antes deste documento, numa imagem sintética e sem nada do
gabarito):
- Formato: dois círculos em posições conhecidas, coordenadas pedidas de 0 a 1000.
- Resultado: os 5 modelos que responderam erraram no máximo 25 milésimos.
- A convenção 0–1000 fica fixada.

## Amostra

- Os 66 quadros do gabarito do braço (`data/gold/maos/braco.json`,
  `data/saida/maos/m3b/quadros/`), todos com braço `sim`.
- Por isso a presença do braço **não** é medida nesta rodada.
- Os quadros do teste M11b não entram.
- **Divisão** (semente 20261019, `random.Random(20261019).sample` da lista ordenada de
  ids): 33 de **desenvolvimento** e 33 de **teste**.
  - O limiar de concordância é escolhido só no desenvolvimento.
  - O teste é medido uma vez, com o limiar congelado.

## Pedido a cada modelo

- Quadro reduzido a 1280×720, em JPEG de qualidade 92.
- Prompt único, escrito antes da coleta e guardado no código. Ele pede JSON com:
  - `braco` (`sim`, `parcial` ou `nao`);
  - `nut` (ponto, ou `"fora"`);
  - `corda1` e `corda6`: 2 pontos cada, nas pontas do trecho visível **no braço**, que é a
    regra do dono. A corda 1 é a mais fina (Mi agudo); a 6 é a mais grossa (Mi grave);
  - `traste5` e `traste12`: o ponto no meio de cada traste, ou `null`.
- Os 7 pontos ficam em coordenadas de 0 a 1000.
- Os outros trastes saem pela regra das 12 notas (`tab.maos_braco_regra.prever_trastes`,
  98,8 % dentro de 1/4 de casa com os pontos do dono).

## Filtro automático (antes de qualquer comparação com o gabarito)

Uma resposta é **descartada** se:
- o JSON não é válido;
- falta ponto;
- `nut` é `"fora"`;
- algum ponto está fora da imagem;
- as cordas 1 e 6 se cruzam entre as pontas;
- `prever_trastes` recusa;
- a razão `(t5 − t_nut)/(t12 − t_nut)` fica fora de [0,35; 0,70]. No gabarito do dono, ela
  vai de 0,417 a 0,603, com mediana 0,510.

## Medidas

São as da 1015, com `tab.maos_braco_tempo.erros` e `classificar`:
- nut e pior traste em casas;
- cordas na perpendicular, em vãos.

| classe | regra |
| --- | --- |
| certo | tudo < 0,25 |
| falso | algo > 0,5 |
| impreciso | o resto |
| não achou | descartado ou sem resposta |

**Por modelo** (nos 66 quadros):
- distribuição das classes;
- trocas de corda 1 com corda 6, contadas à parte.

**Consenso**, por quadro:
- **Entrada**: entram as respostas que passaram no filtro, e é preciso ter **≥ 3**.
- **Ponto de consenso**: a mediana, coordenada a coordenada, de cada um dos 7 pontos.
- **Dispersão**: para cada modelo, a maior distância de um ponto dele ao ponto de consenso,
  dividida pelo vão do consenso (distância entre as cordas 1 e 6 ÷ 5, no meio do braço). A
  dispersão do quadro é a **mediana** desses valores entre os modelos.
- **Aceito**: ≥ 3 respostas válidas e dispersão ≤ L.
- **Escolha de L**: o maior limiar da lista {0,25; 0,5; 0,75; 1,0; 1,5} que, no
  desenvolvimento, dá 0 falsos e ≥ 90 % de certos entre os aceitos.
  - Se nenhum limiar passar, a rodada reprova no desenvolvimento.
  - Nesse caso, o teste não é rodado.

## Critérios de aceite (no teste, 33 quadros, L congelado)

| | critério |
| --- | --- |
| P1 | **0 falsos** entre os quadros aceitos |
| P2 | certos ≥ **90 %** dos aceitos |
| P3 | **cobertura**: aceitos ≥ **30 %** dos 33 quadros (≥ 10) |
| P4 | relatório por modelo e por canal, com denominador |

**Vale a pena se P1, P2 e P3 passam.** Nesse caso, a próxima rodada mede o tempo de
revisão do dono com cronômetro. Limiar mudado depois da medida invalida a rodada.

## Riscos declarados antes

- **33 quadros de teste são poucos.** Se P1 passar com 0 falsos em 10 aceitos, o limite
  superior de 95 % da taxa de falsos ainda é de cerca de 26 %. Uma aprovação aqui só libera
  um piloto com revisão total, nunca aceite sem olhar.
- **Os modelos gratuitos podem mudar sem aviso** (versão e limite de taxa). O resultado vale
  para a data da coleta, e as respostas brutas ficam gravadas.
- **Concordância não prova acerto.** Se os modelos erram do mesmo jeito (por exemplo,
  trocando as cordas 1 e 6), o consenso erra junto. É exatamente o que P1 e P2 medem.
