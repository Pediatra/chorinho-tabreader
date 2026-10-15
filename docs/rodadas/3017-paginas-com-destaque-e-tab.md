# 3017 — paginar: destaque colorido e tablatura confundida com pauta

Trilha partitura, passo 4 (vídeo com pauta e sem produto da tab). Continua a rodada 3016.

## Problema

O piloto da 3016 em 11 vídeos de 11 canais (`diag/piloto_videos.txt`) mostrou três defeitos.
Eu os conferi olhando as folhas de contato (`diag/piloto_*.jpg`):

1. **A mesma página quebra em várias quando o destaque anda.** Exemplos: no canon, P03–P05
   são a mesma página com o destaque amarelo em outro compasso; no beam of light, a mesma
   página com o destaque rosa aparece repetida em várias páginas.
   - Causa medida (`diag/diag_destaque.py`, `diag_tophat.txt`): sob o destaque, a compressão
     do vídeo tinge de cor o traço preto fino. Com isso, linhas e notas saíam da máscara de
     tinta (pela saturação na primeira tentativa, pela mediana da linha na 3016).
   - Efeito: só o destaque andar já dava diferença de até 0,74, acima do limiar de 0,25.
2. **A tablatura era recortada como se fosse pauta** (iwaki, amazing grace). O detector
   acha 5 das 6 cordas.
3. **sky guitar dava 0 páginas.** O nome do arquivo no disco está em NFD e a lista estava em
   NFC.

## O que mudou (`tab/partitura_video.py`)

- **Tinta = contraste com o fundo local.**
  - É o top-hat do canal V, com elemento quadrado de 2·entrelinha + 1 px e corte > 60.
  - Em fundo claro usa o black-hat; em fundo escuro, o top-hat.
  - O destaque, o cursor vermelho e a cor da compressão mudam a cor, mas não o contraste.
- **Teste de tablatura** (`e_tablatura`): a pauta é descartada se aparece uma 6ª linha uma
  entrelinha abaixo ou acima.
  - Força de uma linha: divide a largura em 10 trechos e pega o 2º pior.
  - A linha da tablatura atravessa a largura toda. A viga de semicolcheia acima da pauta
    cobre só parte dela.
  - Limiar: 0,75 da força das 5 linhas.
- `_verificar_video`: um nome que não existe no disco agora gera erro. A mensagem diz o nome
  certo se a diferença for só NFC/NFD. Antes saíam 0 páginas em silêncio.

## Medições

**Diferença de assinatura** (`diag_tophat.txt`), em trechos medidos a cada segundo:

| caso | regra antiga | top-hat |
| --- | ---: | ---: |
| só o destaque anda (canon, beam) | até 0,74 | ≤ 0,06 |
| troca real de página (beam) | 0,65–0,74 | 0,49–0,55 |

**Teste de tablatura** (`diag/razoes_trechos.txt`; 8 tablaturas, 244 pautas reais):

| regra | tablaturas | pautas reais |
| --- | --- | --- |
| largura toda (antes) | ≥ 0,80 | até 0,68: vigas do amazing grace descartavam 7 pautas reais |
| 2º pior de 10 trechos | ≥ 0,88 | ≤ 0,65 |

Duas regras testadas antes perderam, porque a 1ª linha da tab do iwaki é cortada por muitos
algarismos:

| regra | por que perdeu | arquivo |
| --- | --- | --- |
| abertura com traço longo | também apaga essa linha | `razoes_aberta.txt` |
| espessura do traço | sobreposição de 0,63 contra 0,67 | `razoes_fina.txt` |

**Validação nos 3 vídeos com produto** (`conferir_paginas.py`):

- greensleeves 4/4, south american 3/3, gymnopédie 12/12;
- caixas idênticas às do produto, nenhuma página sobrando, 0 tabs descartadas.

**Piloto**, em páginas (`diag/piloto_paginar3.txt`). As colunas são: 3016 = regra
commitada; 1ª tent. = HSV, não commitada; 3017 = esta rodada.

| vídeo | 3016 | 1ª tent. | 3017 | olhando a folha |
| --- | ---: | ---: | ---: | --- |
| agua de beber | 10 | 10 | 10 | ok |
| amazing grace | 13 | 15 | 13 | todas as pautas reais; 6 tabs fora; nenhuma pauta real fora |
| free tab (lonelypicker) | 13 | 17 | 14 | página corrida; ver limites |
| canon | 6 | 16 | 6 | 6 páginas distintas |
| blackbird | 20 | 45 | 20 | faixa que rola; ver limites |
| beam of light | 8 | 21 | 6 | P01=P04 e P02=P05 (intro em outra escala) |
| giant steps | 10 | 13 | 13 | faixa que rola |
| sky guitar | 0 | 10 | 10 | (NFD corrigido) |
| amores hallaras | 12 | 13 | 12 | — |
| athletic theme | 8 | 8 | 8 | — |
| mela (guitarous) | 19 | 30 | 20 | página corrida; ver limites |

Pares de páginas abaixo do limiar (`diag/duplicatas3.txt`): só mela P19×P20 (0,140).

## Limites (o que ainda não está bom)

- **A pauta sob o destaque às vezes não é achada** no quadro escolhido. Isso é perda de dado:
  - free tab P02: a pauta de cima não foi achada;
  - mela P03, P06 e P14: a pauta de cima não foi achada; mela P05: a de baixo não foi achada;
  - a falha está em `achar_pautas`, sob destaque amarelo. Próxima rodada: escolher, dentro
    das exibições da página, o quadro com mais pautas achadas.
- **Mesma página em outra escala ou posição não se junta.** Exemplo: a introdução do beam
  of light. Sai como página duplicada (custo de leitura), não como perda.
- **Faixa que rola** (blackbird, giant steps) e **página corrida** (mela, free tab): a página
  não é uma unidade fixa, e o conteúdo se repete entre páginas vizinhas. Fica marcado como
  limitação. Quem consome tem de juntar compassos repetidos.
- O teste de tablatura foi visto em um só caso real (iwaki).
