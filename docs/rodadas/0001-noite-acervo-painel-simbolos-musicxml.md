# 0001 — Noite de 2026-10-08/09: acervo novo, painel, símbolos e MusicXML

Resumo do que foi medido e mudado enquanto o dono do projeto dormia. Cada afirmação traz
o número que a sustenta. O que **não** ficou pronto está dito no fim, sem maquiagem.

## 1. O acervo cresceu e foi varrido

**3.993 vídeos / 183 GB / 17 canais** (o dono segue baixando; a tabela dele previa ~6
canais a mais). Varredura completa: **96,5 % com tablatura** (3.855/3.993), 69,5 min.
Por canal: 100 % em `iwaki`, `kimny's guitar`, `raman korshun`, `leonardo ramos`,
`mr. tabs`, `robert lunn`, `serge kottelat`, `shin izumi`, `paolo d'angelo` e
`tv on guitar`; 99 % em `guitar dell'arte` (347/361) e `violaodecria` (1.666/1.680);
**79 % em `sky guitar` (348/440)** — o canal que o dono apontou como o melhor.

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

## 5. Tempo: a descoberta e o que falta

No `iwaki/henze` o marcador **desliza**: banda de 6 px, matiz 102, ~17 px por 0,25 s
(65 px/s), sem saltos. O onset é **invertível** — a nota começa quando ele cruza o `x`
dela. Em diagnóstico controlado: **8 instantes distintos** onde o método antigo dava 1.

E o mesmo diagnóstico **derrubou uma conclusão minha**: no `sky guitar` #4 as "janelas com
cursor" eram **artefato** (banda parada em x=0–99 por 5 s na borda do painel, e bandas em
x≈900–1084, fora do painel) — aquele vídeo **não tem marcador**. Lição: **presença e
semântica do marcador são por vídeo, não por canal**, e varredura de 1 instante mede
presença, não confiabilidade.

## O que NÃO ficou pronto

1. **onset por nota no pipeline**: o método está pronto e testado (`tab/tempo.py`, 8
   testes), a integração é conservadora e naquele vídeo declara `tempo.medido: false`
   porque o detector devolve uma banda **parada** na janela — o detector precisa
   distinguir "banda que anda" de "elemento parado do vídeo";
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
