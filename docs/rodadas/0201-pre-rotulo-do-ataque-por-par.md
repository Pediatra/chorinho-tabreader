# 0201 — Pré-rótulo do ataque por par de notas: regra da tinta e modelo de linguagem

Pedido do dono (2026-10-17): a conferência à mão cansa e deixa passar erro. A pergunta desta
rodada é se uma máquina pode **apontar** os pares a conferir, para o dono só confirmar.

## Pergunta

Num par de notas vizinhas da mesma corda, há um arco, slide ou símbolo ligando as duas? O par
é **ligado** quando a nota da direita tem ataque "nao" no gabarito do R2.

## Pré-registro (escrito antes de medir o modelo de linguagem; não muda depois)

### Entradas

- **Gabarito**: o mesmo da rodada 0200, mais o La Vie en Rose (4 vídeos, telas conferidas):
  849 pares, 64 ligados (`python -m tab.ataque_pares`, saída em
  `data/saida/tab_rotulo/r3_pares/`).
- **Regra da tinta** (`tab.ataque_pares.tinta_entre`): a área de tinta entre os centros das
  duas notas, de 1,6 passo acima a 1,2 passo abaixo da corda, depois de tirar:
  - as caixas das notas;
  - as cordas;
  - os traços verticais de 0,9 passo ou mais;
  - os componentes com menos de 0,25 passo de largura ou mais de 1,4 passo de altura.

  A janela e os filtros foram ajustados **olhando os recortes desses mesmos pares** (duas
  folhas de diagnóstico). Por isso a medida da regra é otimista; ela precisa ser medida de
  novo em vídeo novo.
- **Modelo de linguagem**: Claude Haiku 5.5, sem saber o rótulo. Recebe o recorte de cada par
  (as duas notas sublinhadas em vermelho) e responde `ligado` ou `solto`.
  - Amostra: os 64 ligados e 136 soltos sorteados (semente 0), embaralhados, 200 recortes em 4
    lotes de 50 (`amostra_llm.json`).
  - A pergunta é a mesma para os 4 lotes, escrita no briefing.

### O que se relata

- **Ligados achados** (o que importa para não contaminar a base) e **alarmes** (soltos
  chamados de ligados: é o trabalho do dono), cada um com o denominador.
- Para a regra: a curva por limiar. Para o modelo de linguagem: os números na amostra, e
  quanto a regra e o modelo concordam.

### Critério para virar pré-rótulo

O pré-rótulo serve se achar **95 % ou mais dos ligados** com no máximo **30 % de alarmes**.
Abaixo disso, o dono continua conferindo tela por tela.

## Resultado

### Regra da tinta

| conjunto | limiar | ligados achados | alarmes |
| --- | --- | --- | --- |
| 4 ouros (ajuste) | 0,05 | 62 / 64 (97 %) | 183 / 785 (23 %) |
| amostra de 200 | 0,05 | 62 / 64 | 26 / 136 (19 %) |
| **T8.2, 24 telas com marca (fora do ajuste)** | 0,05 | **30 / 30** | **135 / 604 (22 %)** |

Na T8.2 o rótulo vem das regiões do dono convertidas (R2), ainda sem a conferência no modo
ataque. As 2 perdas nos ouros são mordentes em que um arco cobre três notas e a nota do meio
fica embaixo dele (From This Place t3-n38, La Vie t8-n50).

### Modelo de linguagem (Haiku 5.5, amostra de 200)

- Ligados achados: 49 / 64 (77 %). Alarmes: 6 / 136 (4 %).
- 8 das 15 perdas são mordentes; as outras são h, p, slide e prolongamento.
- 3 dos 4 lotes relataram dúvida na ordem entre id e imagem, sem conferir. O número pode ter
  ruído de troca, mas fica abaixo do critério com folga.
- Regra **ou** modelo: 62 / 64 e 30 / 136. O modelo não acrescenta nada à regra.

### Decisão

- A regra passa no critério (95 % ou mais, até 30 % de alarmes), inclusive fora do ajuste.
- O modelo de linguagem não passa: perde 1 ligado em cada 4.
- A regra vira o pré-rótulo: nas telas a conferir, só a nota da direita de um par apontado
  aparece como dúvida (`?`, tipo `regra_tinta`). O dono decide essas, e o resto fica "sim".

### Achados de passagem (folhas `suspeitos_*.png`, 134 pares soltos com tinta)

- A maior parte dos alarmes é barra de compasso grossa, pausa de ritmo, hífen do estilo
  "5-4-2" e o X entre duas notas.
- **O X do End of Beginning não é nota no gabarito**: um par como "3 X 3" pula o X. O ataque
  abafado fica de fora da base (é o R5).
- Três notas "sim" do dono com arco chegando nelas, a conferir: End of Beginning t6-n24,
  Room 335 t5-n24 e From This Place t5-n22. A Room 335 t27-n25 já foi decidida pelo dono.
