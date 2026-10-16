# 1151 — C1b: o β com máscara de parciais e normalizado pela casa separa as cordas de mesma altura?

**Data**: 2026-10-16. Frente C1b da onda 2 (`docs/pesquisa/maos-onda2-briefings.md`), worktree
`chorinho-wt-c1`, branch `maos/c1-inarmonicidade`. Antecedente: rodada 1150 (inconclusiva, 0 pares
elegíveis nos 4 vídeos). Referência de uso: D1 do M8 (`data/saida/maos/m8/corda_sem_direita.json`).
Código: `tab/maos_timbre_mascara.py` (estimador com máscara), `tab/maos_timbre_c1b.py` (medida),
`tab/maos_timbre_c1b_controle.py` (controle). Saída: `data/saida/maos/frentes/fc_audio/`.

## Pergunta

Com a máscara de parciais que soam e o β normalizado pela casa (β0 = β / 2^(casa/6)), a AUC do β0
separa as cordas candidatas de mesma altura, fora da metade de calibração, em pelo menos 3 dos 4
vídeos? E o β escolhe a corda certa nas ambíguas com mais acertos e menos erros do que o D1?

## Regras e pesos a priori

Escritas e commitadas sozinhas antes de qualquer medida (controle inclusive). Nada abaixo foi
escolhido depois de ver número de C1b.

**Dados e isolamento** (igual à C1, exceto a regra do alinhador)

1. Áudio: `MAOS_FRENTE_C/audio_48k/<video>.flac` (48 kHz, sem reamostrar). Instante do som: `t_audio`
   de `data/saida/maos/m7/audio/ataques_audio.json`.
2. **Regra do alinhador (nova, descarta a nota)**: se `t_audio − t_ini` cai fora de [−0,1 s; 1,0 s],
   a nota é descartada e conta-se à parte. Pelo censo de 4 vídeos feito agora, são 26 ataques fora
   (retrato 2, noturno 4, lacrimosa 11, glimpse 9), e esses são os saltos de −9,6 s e +18 s. Sem
   `t_audio`, a nota é descartada (como na C1).
3. Isolamento igual à C1: um ataque com uma nota só, e nenhum outro ataque com som em
   [t_audio − 0,15 s; t_audio + 0,25 s] (outro ataque sem `t_audio` usa a faixa
   [t_ini + 0,05; t_ini + 0,33]).
4. Janela de medida: [t_audio + 0,025 s; t_audio + 0,25 s]. Estimador: o da C1
   (`tab/maos_timbre_beta.py`), com os mesmos parâmetros congelados (quadro 4.096, passo 1.024, FFT
   16.384, K ≤ 16, até 6 kHz, razão pico/piso ≥ 3, ≥ 3 quadros por parcial, ≥ 6 parciais, β > 0).
   Só o estimador muda pela máscara (item 5); a rodada da C1 não é alterada.

**Máscara de parciais que soam**

5. Duas máscaras, as duas com notas atacadas em [t_audio − 2,0 s; t_audio + 0,25 s] (alturas da
   tablatura, parciais nominais k·f_nom até 6 kHz):
   - (i) **por quadro**, como na C1: o pico de um quadro a menos de 30 cents de um parcial alheio é
     descartado naquele quadro. Mantida, para a C1b ser a C1 com uma máscara a mais.
   - (ii) **por parcial (nova)**: depois do ajuste de rodada final, o parcial k cuja frequência
     mediana fica a menos de 30 cents de um parcial alheio sai do ajuste inteiro. Refaz-se o ajuste
     só com os parciais que sobram (com as frequências medidas). Exigem-se ≥ 6 parciais depois da
     máscara (ii). Conta-se à parte quantas notas caem em "poucos parciais" antes e depois de (ii).
6. Diagnóstico, fora do critério: a mesma medida sem a máscara (ii), para mostrar o efeito dela.

**β normalizado pela casa e inclinação**

7. β0 = β / 2^(casa/6), por nota. Inclinação de ln β × casa **por corda** (regressão simples em cada
   corda, com n). Inclinação pooled com efeito fixo por corda (como na C1), com IC95, e
   compatibilidade com ln 2 / 6 = 0,1155.
8. Corda 4 tem de ser conferida: cinco espectros das cinco primeiras notas medidas da corda 4, na
   ordem do vídeo (retrato, depois os outros), com os parciais usados marcados. Imagens e
   inspeção registradas na rodada.

**Calibração, teste e pares**

9. Calibração: metade do áudio do vídeo, por `t_audio` (como na C1). Teste: a outra metade.
10. Par elegível: duas cordas com a mesma altura **com ≥ 8 notas medidas de cada corda na calibração
    e ≥ 8 notas medidas de cada corda no teste** (leitura de "nas DUAS metades"; a C1 exigia só ≥ 8
    no total).
11. AUC por par: direção = sinal da diferença das médias de ln β0 na calibração; escore na metade de
    teste; AUC = P(escore da corda A > escore da corda B), com empate contando meio. A AUC não
    depende do ponto médio da calibração.

**Aceite (congelado, CA da frente C)**

12. Por vídeo, passa se a AUC ≥ 0,80 em pelo menos metade dos pares elegíveis.
13. **Aprova** se passam ≥ 3 dos 4 vídeos e a inclinação pooled é compatível com ln 2 / 6 (critério
    de seção 7 da frente C, "a curva segue 2^(n/6)").
14. **Para** se a AUC < 0,65 na maioria dos pares (somando os 4 vídeos).
15. **Fecha como "sem amostra nos 4 vídeos"** se ≥ 2 vídeos ficarem sem par elegível. O mínimo de 8 não
    é afrouxado.

**Medida de uso (relatório, não critério)**

16. Universo: notas ambíguas (≥ 2 cordas possíveis para a altura, casa 0 a 19) da **metade de teste**,
    com β medido.
17. Previsão por candidato (corda s, casa n): ln β̂ = mediana de ln β0 das notas da corda s na
    calibração do mesmo vídeo (≥ 2 notas) + ln 2 · n / 6. O β escolhe o candidato de menor
    |ln β − ln β̂|. Nota com menos de 2 candidatos previstos fica **sem decisão**, fora da contagem.
18. Referência: D1 do M8 com os pesos a priori (α 1, β 3, γ 5, δ 0,5; no D1, β = 0), por
    `decodar(v, "D1", PESOS_PRIORI)`, nas mesmas notas. Conta-se: acerto do β, acerto do D1,
    consertadas (β certo, D1 errado) e quebradas (β errado, D1 certo). Também só com casa ≤ 7.

**CA1 (reprodução, antes de tudo)**

19. D0 e D1 reproduzidos **exatamente** (n, acertos, erros, janela) nos 4 vídeos. Se não bater, pare.
    Verificação de 2026-10-16 (rascunho `scratch_c1b/ca1_d1.py`, fora do commit): **bateu nos 8 casos**
    (D1: 50, 129, 60, 46 erros = 285).

**Controle sintético (antes de medir os vídeos)**

20. (a) Reexecução do controle da C1 com o estimador novo, mesmas sementes. Sem notas alheias, a
    máscara não atua: os números têm de ser **idênticos** aos de `c1_controle.json`.
21. (b) **Cenário sobreposto**: cada nota recebe uma nota alheia de outra altura (sorteio com semente
    fixa) que começou 1,0 s antes; a máscara recebe os parciais dela. Mesmo critério da C1 (central, em
    cada bitrate: ≥ 90 % medidas e mediana de r < 0,5). Reprovação aqui para a C1b, sem medida em vídeo.

**Parada, pelo que foi escrito**

- CA1 falha → para. Controle (a) não reproduz, ou (b) reprova → para.
- Veredito pelos itens 12–15, sem re-escolha de parâmetro.

## Limites declarados (valem para toda a rodada)

- A altura, a corda verdadeira e as notas isoladas vêm da tablatura: **limite superior** de viabilidade
  (como na C1). A frequência de busca de cada parcial também vem da tablatura; β não depende do f0
  da tablatura, que é estimado pelo ajuste.
- A calibração (β0 por corda, previsão de uso) usa rótulos da tablatura na metade de calibração.
- Só `sky guitar`, 4 vídeos, um violonista. Nada sobre técnica ou dedilhado.

## Resultados

**Parada no controle (item 21b, 161 kb/s). A medida nos 4 vídeos não foi rodada.** Não há número
de C1b em vídeo nesta rodada.

Sementes fixadas no código antes do controle (não estavam no a priori): (a) 1150 e 1160, como na
C1; (b) 1151 e 1161. Arquivo: `data/saida/maos/frentes/fc_audio/c1b_controle.json`.

**(a) Reprodução da C1 com o estimador novo (item 20): passou.** Os β medidos são idênticos aos de
`c1_controle.json` nas 117 notas, nos dois bitrates (0 diferenças).

**(b) Cenário sobreposto central (item 21, nota alheia 1,0 s antes): reprovou em 161 kb/s.**

| bitrate | notas | medidas | fração | mediana r | P90 r | critério (≥ 90 % e r < 0,5) |
| --- | --- | --- | --- | --- | --- | --- |
| 121 kb/s | 117 | 109 | 0,932 | 0,00109 | 0,0030 | aprovado |
| 161 kb/s | 117 | 99 | 0,846 | 0,00088 | 0,0041 | **reprovado** (fração < 0,90) |

Pelo item 21, a C1b para aqui. O erro de r continua baixo; a reprovação é de cobertura: 15 % das
notas sem medida em 161 kb/s.

**Achado sobre a máscara por parcial (item 5, ii).** Em nenhuma das 234 notas do cenário sobreposto
(117 por bitrate) a máscara por parcial tirou um parcial do ajuste (`notas_com_parcial_mascarado` = 0).
A máscara por quadro (i), a da C1, já descarta os quadros cujo pico cai a menos de 30 cents de um
parcial alheio, e então o parcial não chega à mediana. Nesta implementação, (ii) não atuou.

**Veredito.** Nenhum da C1b. A frente C não vai para a C2 por esta rodada.

## Não repetir

- Esperar que a máscara por parcial (ii) acrescente algo à máscara por quadro (i): no controle
  sobreposto ela não atuou nenhuma vez.
