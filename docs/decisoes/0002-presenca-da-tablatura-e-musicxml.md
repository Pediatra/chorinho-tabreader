# 0002 — A tablatura aparece e desaparece; a saída é MusicXML

**Data:** 2026-10-08 · **Status:** aceita · **Origem:** respostas do dono do projeto em
`PERGUNTAS.md` (2ª e 3ª rodadas)

## Contexto

Duas informações do dono do projeto mudam o desenho, e as duas foram dadas de forma
inequívoca:

1. *"Praticamente todos os vídeos do canal contém tablatura em algum momento do vídeo,
   são vários formatos, tipos, cores, marcadores diferentes, e além disso eles
   **aparecem ou desaparecem em certos momentos** da tela do vídeo."*
2. O produto final é **MusicXML** — o dono entregou o esqueleto desejado:
   `score-partwise` versão **4.0**, `part-name` "Guitarra (Tab)", `clef` `TAB` linha 5,
   `staff-details` com `staff-lines: 6` e `staff-tuning` por linha, e cada `note` com
   `notations/technical/{string, fret}`.
3. A **afinação varia** (drop D, DADGAD, capotraste) e **às vezes está escrita na tela no
   começo do vídeo** (texto de *tuning*/afinação).
4. O tempo é **só onset** (o dono confirmou): não há duração medida.

## Decisão

### 1. Presença, não "o painel do vídeo"

O que existe é um conjunto de **intervalos de presença** por vídeo. A varredura
(`tab/varredura.py`) amostra N instantes e mede cada um; a decisão de formato
(faixa, máscara, marcador) é tomada **por trecho**, porque o formato pode mudar dentro
do mesmo vídeo.

Consequência imediata e desconfortável: **"este vídeo tem tablatura" medido em um único
quadro subestima a cobertura** — o inventário anterior (rodada 3, "96 % com tablatura")
foi medido assim e é um piso, não o valor.

### 2. MusicXML é o produto; o JSON continua sendo a medição

O JSON interno (corda, casa, coluna, confiança, símbolo cru, técnica, tempo, mecanismo do
marcador) **não é substituído** — ele é a medição auditável. O MusicXML é uma
**exportação** dele. Isso mantém a regra "símbolo não se descarta": nem todo símbolo tem
lugar em `notations/technical`, mas todos continuam no JSON.

### 3. `duration` é INFERIDA, e isso tem de estar declarado

Medimos **onset**, não duração. Então a duração de uma nota no MusicXML é o **intervalo
até o próximo onset** — uma inferência, não uma medida. Regras:

- `divisions` derivam do andamento medido (mediana entre onsets, campo que já existe);
- onde **não houver andamento**, o exportador declara a hipótese usada em vez de inventar
  um número silencioso;
- a última nota de um trecho não tem próximo onset: ou recebe uma duração declarada como
  suposta, ou é omitida da exportação com aviso.

### 4. `staff-tuning` exige medir a afinação

Passa a ser item de medição: procurar no **começo do vídeo** o texto de *tuning*/
afinação na tela. Sem isso o `staff-tuning` do MusicXML seria sempre "standard" — e
estaria errado em todo vídeo com drop D, DADGAD ou capotraste. Enquanto não estiver
implementado, o exportador escreve `standard` **e registra que assumiu**.

### 5. Técnicas viram `notations/technical`

`hammer-on`, `pull-off`, `slide`, `harmonic`, `bend`, … é o destino natural do mapa de
símbolos por canal (`configs/simbolos.yaml`). Símbolo sem equivalente MusicXML fica no
JSON como cru, com `mapeado: false`.

## Consequências

- a métrica oficial **não muda** de natureza (continua glifo a glifo no gabarito): o
  MusicXML é produto, não métrica;
- a varredura completa passa a ser pré-requisito de qualquer trabalho em escala: é ela
  que diz, por trecho, qual extrator usar;
- o alvo declarado pelo dono é **"um vídeo inteiro correto já me serve"** (MVP), e o
  canal de referência é **`sky guitar`** ("as melhores tablaturas e vídeos explicativos").
  Isso dá um critério de pronto concreto: **um vídeo do `sky guitar`, do começo ao fim,
  vira MusicXML sem nota inventada**;
- o **`duration` inferido** tem de aparecer no relatório do exportador; número inferido
  apresentado como medido é exatamente o erro que este projeto já cometeu duas vezes.

## Verificação

Pendente (trabalho da noite de 2026-10-08):
1. varredura completa gravando presença por instante — em andamento;
2. exportador MusicXML com um vídeo do `sky guitar` como alvo;
3. detecção do texto de afinação no começo do vídeo.
