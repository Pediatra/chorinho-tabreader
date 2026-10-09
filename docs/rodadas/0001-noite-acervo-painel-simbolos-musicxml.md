# 0001 — Noite de 2026-10-08/09: acervo novo, painel, símbolos e MusicXML

Resumo do que foi medido e mudado enquanto o dono do projeto dormia. Cada afirmação traz
o número que a sustenta. O que **não** ficou pronto está dito no fim, sem maquiagem.

## 1. O acervo cresceu e foi varrido

**3.993 vídeos / 183 GB / 17 canais** (o dono segue baixando; a tabela dele previa ~6
canais a mais). Varredura completa: **96,5 % com tablatura** (3.855/3.993), 69,5 min.
Por canal: 100 % em `iwaki`, `kimny's guitar`, `raman korshun`, `leonardo ramos`,
`mr. tabs`, `robert lunn`, `serge kottelat`, `shin izumi`, `paolo d'angelo` e
`tv on guitar`; 99 % em `guitar dell'arte` (347/361) e `violaodecria` (1.666/1.680);
`sky guitar` deu 348/440 (79 %) — **contagem de antes da limpeza dele**: o dono apagou os
vídeos especiais **sem tutorial** e restaram **417, todos com tablatura**. Ou seja, aquele
"79 %" mede **falso negativo do meu detector**, não ausência de tablatura, e é uma
validação de graça.

## 2. Três erros de critério no painel (todos medidos com o quadro na mão)

| erro | evidência | correção |
| --- | --- | --- |
| ordenar por glifos centrados escolhia o **braço do violão** | faixa `base` = braço+mão: 39 "glifos", 34 "centrados", uniformidade **0,842**; a tablatura em `meio`: 36 glifos, 29 centrados, uniformidade **0,888** | `tab/painel.py`, implementação única: uniformidade primeiro |
| cursor procurado no **quadro inteiro** | 69 de 3.993 vídeos; o portão exige ≥50 % da imagem (540 px) e o cursor tem a altura do painel (~150 px) | cursor no ROI da faixa |
| faixa de **largura total** | recorte 570 px → máscara `otsu` → **3 glifos reais**; recorte 1920 px → `contraste_k31_d25` → 36 glifos, **33 de lixo** | `extensao_das_linhas` exige 4+ das 6 cordas na mesma coluna |

Duas tentativas de recorte em x foram **medidas e descartadas**: tinta em qualquer linha
não separa (o braço tem cordas com espaçamento parecido — cortou em 882 px onde a
tablatura tem ~520) e uniformidade por coluna pega a **margem vazia** (cortou em 240 px de
papel em branco).

Ponta a ponta conferido no olho (`sky guitar` #4, t≈88 s): **3 notas, corda 5, casas
0 / 2 / 3**, confiança 0,996 / 0,931 / 0,999 — exatamente o que está no quadro.

## 3. Símbolo não se descarta (implementado)

- `Glifo.componentes`: as caixas dos pedaços que formaram o token. Sem elas o símbolo já
  estava perdido na **montagem** do token, antes de qualquer modelo;
- todo token não numérico (e todo fundido) sai com `simbolo_cru`: PNG ampliado
  **deduplicado por hash**, larguras em passo, caixas relativas, classe e top-3. Já são
  **172 recortes** gerados nos testes de ponta a ponta — é assim que o vocabulário de um
  canal se forma sem reabrir vídeo;
- `casa_recuperada` (achar o algarismo dentro do símbolo): **medido e reprovado**,
  0,889 → **0,687** (pior nas 3 sementes; no `paolo`, 25→10). Fica gravado como
  informação, nunca como padrão.

## 4. MusicXML (implementado)

`tab/musicxml.py`: `score-partwise` 4.0, `part-name` "Guitarra (Tab)", `clef` TAB linha 5,
`staff-lines` 6, `staff-tuning` por corda, `notations/technical/{string, fret}` e técnica
mapeada (`harmonico` → `harmonic`).

Três honestidades embutidas: a **duração é inferida** (intervalo até o próximo onset) e
declarada como tal; **nota que não é algarismo não vira nota** (`junk`/`harmonico`/
`tecnica` são contados como não exportados); e **tempo degenerado não vira ritmo** — com
0–1 instante distinto para N notas o relatório diz `tempo_medido: false`.

## 5. Tempo: o método ficou, a evidência caiu

Escrevi aqui que o marcador do arquivo `iwaki/henze ｜ nocturno - guitar lesson + tab.mp4`
(composição de **C. Henze** — "henze" é o compositor, não o autor do vídeo, como o dono do
projeto corrigiu) **deslizava** a ~65 px/s e que isso dava **8 instantes distintos**.

**O dono corrigiu e a medição confirmou que ele está certo:**

- o canal `iwaki` **não tem marcador** — amostra de 6 vídeos × 7 instantes: **0 detecções**;
- naquele arquivo, ao longo dos 342 s, as 14 detecções estão **espalhadas** (x = 230, 285,
  341, 548, 638, 690, 844, 1184, 1491, 1527…), **sem progressão nenhuma**. Um movimento
  suave de 4 s dentro disso me enganou: a partitura está parada (diferença média de 1,14
  nível de cinza entre t=116 e t=118) e o que anda é um elemento azul que **troca de lugar**,
  não um playhead;
- `tab/tempo.resumo` agora exige **sentido único**: série que troca de direção é classificada
  como **`erratico`** e o pipeline **não** atribui tempo.

O método (inverter uma série monotônica para achar o onset) segue correto e testado; o que
faltava era **provar que existe série**, e isso passou a ser condição de aceitação.

E a mesma classe de erro apareceu no `sky guitar` #4: as "janelas com cursor" eram
**artefato** — aquele vídeo também não tem marcador. Lição: **presença e semântica do
marcador são por vídeo, não por canal**.

## O que NÃO ficou pronto

1. **onset por nota no pipeline**: o método está pronto e testado (`tab/tempo.py`, 10
   testes) e agora recusa séries sem sentido único (`erratico`). Falta o passo anterior:
   **saber quais vídeos têm marcador**, que nem a varredura de 1 instante nem o detector de
   matiz respondem hoje — `iwaki` deu 0 em 6 vídeos e o único arquivo onde eu "vi" cursor
   era artefato;
2. **gabarito não foi ampliado** (casas 8–24, canais novos): o tempo da noite foi para o
   detector de painel, que era pré-requisito para gerar montagens confiáveis;
3. **detecção do texto de afinação** não começou;
4. **varredura dos canais prioritários com o critério novo** não terminou: as medidas
   novas (uniformidade por faixa + cursor por faixa + refino) custam ~12 s por vídeo
   contra ~1 s antes — **medir mais custou 10×** e a varredura precisa de otimização
   (uniformidade em imagem reduzida, por exemplo).

## Números oficiais ao fim da noite

**0,889** no gabarito (média de 3 sementes: 0,865 / 0,917 / 0,885), reprodutível, com
**40 testes** e lint verde. O número **não mudou** nesta noite: o que mudou foi o que o
pipeline lê em vídeo novo.
