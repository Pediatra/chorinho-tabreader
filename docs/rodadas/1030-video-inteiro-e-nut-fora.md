# 1030 — Consenso com o vídeo inteiro e numeração com o nut fora da imagem (desenvolvimento)

**Data**: 2026-10-18 (pré-registro feito antes da janela autônoma de 2026-10-19). **Estado**:
regras a priori. Esta rodada é **só de desenvolvimento**: não há prova, e nada aqui entra num
ciclo sem uma rodada própria.

## Parte A — consenso com o vídeo inteiro

**Pergunta**: com centenas de quadros por vídeo, em vez de 8, o consenso por tomada (P3 da 1028)
sinaliza ou corrige os erros isolados, como o q17 da 1027, sem atrapalhar os certos?

**Dados**: os 16 vídeos já revisados, 8 da 1026 e 8 da 1027.
- O detector roda em **2 quadros por segundo** do vídeo inteiro.
- São os **mesmos pesos dos ciclos**: `L2_todos_s1` + `A3_100_todos_s1`, sem retreino. Esses
  vídeos estão no treino da `L3`/`A4`, e por isso a `L3`/`A4` não é usada aqui.
- Quadros dentro de ±0,25 s de um quadro revisado recebem a marca do dono para a medida.

**Medidas**:
- Para os quadros revisados (128): a classe de cada quadro sozinho, contra a classe com o S4 do
  consenso denso.
- O consenso denso tem um modo **só sinaliza** (S4) e um modo **corrige**.
  - No modo corrige, um quadro com deslocamento inteiro k em relação à tomada é renumerado pelo
    k, e o nut, quando a tomada o viu, vem da tomada.
  - A correção é medida, mas não liga nada: só registro.
- Sem rótulo, em todos os quadros: a fração de quadros por tomada, o tamanho das tomadas e a
  fração de quadros que discordam da tomada.

**Critério (registro, para decidir se o consenso denso vai a um ciclo)**:
- O modo corrige **não** pode transformar nenhum certo em falso nos 128.
- E ele precisa transformar ≥ 1 falso em certo.
- Se isso acontecer, o consenso denso é proposto para o ciclo seguinte. Senão, fica só o S4.

## Parte B — numeração com o nut fora da imagem

**Pergunta**: quando o nut não aparece, dá para numerar os trastes por outras referências, sem
confundir o 1º traste ou o capo com o nut?

**Dados de desenvolvimento**:
- os quadros com nut "fora" e `traste_referencia` marcados pelo dono: 8 na 1027, os da 1025, a
  M11b e o C;
- os quadros da 1029, quando o dono revisar.

**Métodos candidatos**, todos sem treino novo e sem marcação nova:
1. **Detectar o nut ausente**: o nut é dado como ausente quando a ponta das cordas do lado do
   nut toca a borda da imagem (a ≤ 2 % da borda) ou quando o canal do nut é fraco (< 0,3). Nesse
   caso, o decodificador **não** prende b no nut.
2. **Ajuste com b livre**: o modelo projetivo com 3 parâmetros, sobre todos os picos. O número
   do 1º pico visível é escolhido entre 1 e 5 pela razão dos espaços entre trastes vizinhos. A
   razão de 2^(1/12) é igual em toda parte, mas o encurtamento da perspectiva muda, e a melhor
   hipótese é a que encaixa mais picos com o menor resíduo.
3. **Fim do braço**: o último traste antes da boca, ou do corpo, é o 19 ou o 20 num violão de
   aço e o 18 ou o 19 num clássico. Ele entra como uma hipótese a mais, nunca como verdade.
4. **Tomada**: se outro quadro da mesma tomada viu o nut, a numeração vem dele (Parte A).

**Medida**: em cada quadro de desenvolvimento, a numeração de cada método contra a do dono
(acerto exato do número do 1º traste visível). Também conta quantas vezes o método **se
recusa** (sinaliza).

**Critério para levar a um ciclo**: o método que tiver **0 numerações erradas não sinalizadas**
e o maior número de acertos. Com 0 acertos, nenhum vai, e o "nut ausente" (método 1) passa a
apenas **sinalizar**. Esse sinal sozinho já teria pego os 2 falsos da 1027.

## Riscos declarados antes

- **Poucos quadros com nut fora** (cerca de 10 a 20): é desenvolvimento, não prova.
- **Os 16 vídeos estão no treino dos pesos novos**, por isso a Parte A usa os pesos antigos.
- **2 quadros por segundo de 16 vídeos** são cerca de 4 a 8 mil quadros, de 1 a 2 h de GPU
  dividida.

## Emenda 1 (2026-10-18 23h, antes de ver qualquer número da Parte B)

**Achado (verificado na álgebra)**: com s(n) = 1 − 2^(−n/12), um deslocamento na numeração dá

    s(n + k) = 1 − 2^(−k/12) · 2^(−n/12) = (1 − 2^(−k/12)) + 2^(−k/12) · s(n)

Isso é uma função **afim** de s(n). O modelo projetivo t = (a·s + b)/(c·s + 1) com b livre
absorve esse afim, então **todo k encaixa os picos igualmente bem**. A razão entre espaços
vizinhos também não decide, pelo mesmo motivo.
- **Consequência**: sem o nut, o espaçamento sozinho **não numera** os trastes.
- Os métodos 2 (b livre) e 3 só funcionam com uma **âncora absoluta**: o fim do braço, uma
  marcação (como a dupla da 12ª) ou o nut visto em outro quadro da tomada.
- **Regra de empate**: hipóteses com números diferentes e resíduos que diferem menos de
  0,001 do espaço viram **recusa**, ou seja, sinalização.
  - O agente pôs essa regra no código antes da medida (commit c990bcd0).
  - Ela fica registrada aqui como parte do método.
- A medida guarda também a previsão "bruta" (sem a recusa), para mostrar quanto ela erraria.

**Outro registro**: a Parte B só tem **9 quadros** com nut fora e referência (8 da 1027 e o q34
da M11b).
- O C tem 4 quadros com nut fora, mas sem referência, e fica de fora.

**A GPU caiu às 23h09** (driver, "No devices were found"), e ela só volta quando o PC for
reiniciado.
- A Parte B e o P2/P3 da 1028 rodam na **CPU** (`CHORINHO_MAOS_CPU=1`), em fp32. Na GPU é fp16,
  e os números podem diferir um pouco.
- A Parte A (vídeo inteiro) fica para quando a GPU voltar.
