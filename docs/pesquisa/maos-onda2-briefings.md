# Onda 2 das frentes das mãos — briefings

**Data**: 2026-10-16. **Plano**: [`maos-frentes.md`](maos-frentes.md), seções 4.1 e 4.2. **Para
quem**: o dono, que abre um agente por frente e cola o briefing.

## Antes de colar

A onda 2 reaproveita as worktrees da onda 1. Cada frente continua no branch da frente de onde
veio:

| frente | worktree | branch | rodadas |
| --- | --- | --- | --- |
| B1b — pontas no instante do som | `../chorinho-wt-b1` | `maos/b1-janela-dedo` | 1131–1139 |
| C1b — β com máscara de parciais | `../chorinho-wt-c1` | `maos/c1-inarmonicidade` | 1151–1159 |
| A1/A2 — transições e L_p | `../chorinho-wt-a3` | `maos/a3-custo-aprendido` | 1111–1119 |

Rodam em paralelo. Só a B1b pode precisar de GPU, e ela pede à sessão principal (ver o
briefing).

## Regras comuns da onda 2

Valem todas as da onda 1 ([`maos-onda1-briefings.md`](maos-onda1-briefings.md) e
`maos-frentes.md`, seções 5, 6, 8 e 9). Mais estas:

- **Passo 0, antes de tudo.** O trabalho da onda 1 ainda está sem commit na worktree.
  1. Rode o gate e faça o commit dele no branch, com o número medido na mensagem.
  2. Depois traga a `main` para o branch: `git merge main`. É o que traz este arquivo e a
     seção 4.2 do plano.
- **Referência R1 = D1 do M8.** Nenhuma frente da onda 1 passou. São 285 erros, e nas ambíguas
  1.995 acertos em 2.280. O CA1 continua o mesmo: reproduzir D0 e D1 exatamente.
- **Regras a priori com commit antes da medida.**
  1. Escreva no documento da rodada a seção "Regras e pesos a priori": parâmetros, grade,
     variante principal e o que conta como aprovação.
  2. Faça o commit **só desse documento**, antes de rodar a medida.
  3. O hash desse commit é a prova da ordem. Variante escolhida depois de ver o resultado é
     diagnóstico, nunca aprovação.
- **Limiares congelados.** São os mesmos CA1–CA7. Não há afrouxamento de nenhum.

---

## Briefing — B1b (D2 com grade fixa e pontas no instante do som)

```text
Você trabalha na worktree da B1 das mãos do projeto chorinho (../chorinho-wt-b1, branch
maos/b1-janela-dedo), agora na frente B1b da onda 2. Leia inteiro, antes de rodar qualquer
coisa: AGENTS.md; docs/pesquisa/maos-onda2-briefings.md (regras comuns); docs/pesquisa/
maos-frentes.md (seções 4.2, 5, 6, a Frente B e a B1 na seção 7, e as seções 8 e 9); a sua
rodada 1130; docs/rodadas/1013-m8-corda-sem-a-mao-direita.md.

Passo 0: gate + commit da B1 no branch; git merge main.

Hipótese: o D2 com a grade fixa do quadro do dono (sem teste de câmera) já tira 285 → 242
erros com as pontas no t_ini, mas o glimpse piora (46 → 50) com 15 erros de "janela errada".
As pontas no t_ini vêm 165–275 ms antes do som: a mão pode estar na posição anterior. Com as
pontas no instante do som, a janela erra menos.

Como:
1. CA1: reproduza D0 e D1 do M8 e TAMBÉM o diagnóstico do revisor (data/saida/maos/m8/
   d2_fixo.py e d2_fixo.json): D2 fixo com 36 / 104 / 52 / 50 erros (retrato, noturno,
   lacrimosa, glimpse). O truque é importar tab.maos_corda_sem_direita e chamar
   janela_da_mao_esquerda com deslocamento (0, 0), sem o teste de câmera. Não edite o M8.
   Se não bater exatamente, pare.
2. Instante do som por ataque com nota presa: t_audio de data/saida/maos/m7/audio/
   alinhado_<slug>.json. Regra a priori para o alinhador: se t_audio − t_ini sair de
   [−0,1 s, 1,0 s], use o t_ini e conte esses ataques (há saltos de −9,6 s e +18 s).
   Variante principal: quadro no t_audio. Secundária, só diagnóstico: t_audio − 0,1 s.
3. Pontas nesses instantes: escreva tab/maos_esq_pontas_som.py espelhando
   tab.maos_pontas_notas (importe DetectorMaos, quadro_bgr e mao_para_registro; use o mesmo
   rect_tab e deslocamento dos pontas_*.json do M8). Saída: MAOS_FRENTE_B/
   pontas_som_<video>.json. Leia só os quadros necessários e registre quantos leu.
   GPU: a trava fica na data/saida da cópia principal (só leitura para você). Meça primeiro 20
   quadros em CPU. Se o total estimado for ≤ 2 h, rode em CPU. Se passar disso, PARE e peça à
   sessão principal para rodar na GPU com a lista de instantes que você gravou.
4. Decodifique o D2 fixo com as pontas do som, pesos a priori do M8 (α 1, β 3, γ 5, δ 0,5),
   sem grade de pesos. Mesmo critério de ponta válida do M8 (_ponta_valida): não mexa no
   limiar de score.
5. Meça CA1–CA7 contra o D1 (R1). Relate também contra o D2 fixo no t_ini: consertadas e
   quebradas, a decomposição dos erros (janela errada / janela certa / sem janela) por vídeo,
   e a cobertura (ataques com janela / ataques com nota presa).

Pare e relate se: a cobertura com as pontas do som cair abaixo de 90 % dos ataques com nota
presa em algum vídeo (quadro do ataque tem mão borrada); não mude o limiar para recuperar.

Pegadinhas: os q24–q31 de data/gold/maos/braco.json são teste da B3, não ajuste nada neles. Não
use a calibração pela música (tab/maos_calibrar_por_notas.py). Uma melhora só no glimpse que
quebre os outros vídeos não passa no CA3. CA6: 10 casos (5 consertados, 5 quebrados, ao menos 4
do glimpse) com o recorte da mão no t_ini e no t_som lado a lado; frase sobre imagem sem o
caminho do recorte não vale.

Território: tab/maos_esq_*.py e tests/test_maos_esq_*.py; saída só em MAOS_FRENTE_B; rodadas
1131–1139; porta 8102.

Entregue: pontas_som_*.json, b1b_medida.json, a rodada 1131 (com a seção a priori commitada
antes da medida), gate verde, commit no branch, resumo curto em português com erros por vídeo
D1 → D2 fixo (t_ini) → D2 fixo (som).
```

## Briefing — C1b (β com máscara de parciais e normalizado pela casa)

```text
Você trabalha na worktree da C1 das mãos do projeto chorinho (../chorinho-wt-c1, branch
maos/c1-inarmonicidade), agora na frente C1b da onda 2. Leia inteiro, antes de rodar qualquer
coisa: AGENTS.md; docs/pesquisa/maos-onda2-briefings.md (regras comuns); docs/pesquisa/
maos-frentes.md (seções 4.2, 5, 6, a Frente C e a C1 na seção 7, e as seções 8 e 9); a sua
rodada 1150; a §2 e a §5.2 de docs/pesquisa/maos.md.

Passo 0: gate + commit da C1 no branch; git merge main.

Contexto: a C1 mostrou que o β é mensurável no áudio do YouTube (inclinação de log β × casa =
0,94 do esperado), mas ficou sem amostra. Dois motivos: a regra "ainda soa 2 s" descartava a
NOTA inteira, e a comparação exigia a mesma altura. A variante de 0,5 s (AUC 0,94 e 0,95 em 2
vídeos) foi escolhida depois de ver o resultado: não conta, e a C1b não é ela.

Regras a priori (escreva e commite na rodada 1151 antes de medir):
1. Isolamento de ataque novo igual à C1: nenhum ataque em [−0,15 s, +0,25 s] do t_audio. Janela
   de medida igual: [t_audio + 0,025 s, t_audio + 0,25 s]. Regra do alinhador: t_audio − t_ini
   fora de [−0,1 s, 1,0 s] descarta a nota.
2. Nota que ainda soa não descarta a nota: descarta PARCIAIS. Tire do ajuste o parcial k da nota
   medida que ficar a ±30 cents de qualquer parcial (até 6 kHz) de uma nota atacada nos 2,0 s
   anteriores (alturas da tablatura). Exija ≥ 6 parciais depois da máscara.
3. β normalizado pela casa: β0 = β / 2^(casa/6), a estimativa do β da corda solta. Só vale
   porque a inclinação foi confirmada; relate a inclinação POR CORDA (na C1 a corda 4 deu
   0,008, com n = 48: confira olhando 5 espectros dela antes de confiar).
4. Calibração e teste por tempo: primeira metade do vídeo calibra, segunda testa (como na C1).
5. Medida principal: por vídeo, para cada par de cordas (s, s′) com ≥ 8 notas medidas de cada
   lado nas DUAS metades, a AUC do β0 entre s e s′ na metade de teste.
6. Medida de uso (relatório, não critério): em cada nota ambígua da metade de teste com β
   válido, escolha a candidata cujo β previsto (mediana de β0 da corda na calibração ×
   2^(casa/6)) fica mais perto do medido, em log. Compare com o D1 nas mesmas notas: quantas
   o β acerta, e quantos erros do D1 ele conserta e quantos acertos quebra.

Aceite (limiares congelados da C1): controle sintético já aprovado (reconfira com a máscara);
AUC ≥ 0,80 em pelo menos metade dos pares elegíveis, em ≥ 3 dos 4 vídeos. Pare se a AUC ficar
< 0,65 na maioria dos pares. Se de novo faltar par elegível em 2 ou mais vídeos, a frente C fecha
como "sem amostra nos 4 vídeos": não afrouxe o mínimo de 8.

Pegadinhas: β0 de cordas diferentes também difere por afinação e por erro de f0, estime o f0 pelo
ajuste, não pela tablatura. O polegar toca os bordões: use β (frequência dos parciais), nunca
timbre por amplitude. Exibições repetidas caem nas duas metades só se a divisão for por nota
sorteada, e ela é por tempo. Usar a tablatura para escolher notas e calibrar é limite superior:
declare. Só numpy e cv2.

Território: tab/maos_timbre_*.py e tests/test_maos_timbre_*.py; saída só em MAOS_FRENTE_C;
rodadas 1151–1159; porta 8103. Reaproveite o áudio já extraído em MAOS_FRENTE_C/audio_48k.

Entregue: c1b_beta.json, a figura β0 por corda (calibração × teste), a rodada 1151, gate verde,
commit no branch, resumo curto em português que diga se vale abrir a C2.
```

## Briefing — A1/A2 (transições com tempo; Minimax e L_p)

```text
Você trabalha na worktree da A3 das mãos do projeto chorinho (../chorinho-wt-a3, branch
maos/a3-custo-aprendido), agora nas frentes A1 e A2 da onda 2. Leia inteiro, antes de rodar
qualquer coisa: AGENTS.md; docs/pesquisa/maos-onda2-briefings.md (regras comuns); docs/
pesquisa/maos-frentes.md (seções 4.2, 5, 6, a Frente A, a A1 e a A2 na seção 7, e as seções 8 e
9); a sua rodada 1110; a §4.2 de docs/pesquisa/maos.md.

Passo 0: gate + commit da A3 no branch; git merge main.

A1 — rodada 1111. Regras a priori:
1. Troque só o termo δ·|Δposição| do D1 por −log Laplace(Δposição; b(dt)), com
   b(dt) = b0 + b1·dt. α = 1, γ = 5 e o resto do D1 ficam iguais. Importe o M8; não o edite.
2. dt pelo SOM: t_audio de data/saida/maos/m7/audio/alinhado_<slug>.json; se t_audio − t_ini
   sair de [−0,1 s, 1,0 s], use a diferença dos t_ini daquele par de ataques e conte.
3. Termo de corda: −log(1/(1 + |Δcorda|)), só entre as notas MAIS AGUDAS de ataques seguidos
   (a melodia). Entre baixo e melodia, a mudança de corda é a música.
4. Grade a priori: b0 ∈ {0,5; 1; 2; 4}, b1 ∈ {0; 1; 2; 4} por segundo, termo de corda ligado ou
   desligado. Escolha deixando um vídeo de fora (CA4).
5. Sanidade obrigatória (parte do CA1): com b0 = 2, b1 = 0 e o termo de corda desligado, o A1
   tem de dar EXATAMENTE o D1 (o log(2b) é constante por transição). Se não der, o código está
   errado: pare.

A2 — rodada 1112. Regras a priori:
1. Pesos do D1. Custo do caminho = Σ cᵖ dos custos por transição, p ∈ {1, 2, 4}; p = ∞ é o
   Minimax (min do máximo), com desempate pela soma (p = 1).
2. Sanidade: p = 1 tem de dar exatamente o D1.
3. A pesquisa já avisa que o Minimax foi feito para gerar dedilhado tocável, não para adivinhar
   o tocado: o teste existe para fechar a pergunta com um número. Não ajuste nada para "salvar"
   o resultado.

Aceite das duas: CA1–CA7 contra o D1 (R1), nos 4 vídeos. Relate também nas outras tablaturas
(sky_* e ouros do dono, só onde houver t_ini para o dt), como relatório. sky_4 e sky_8 são
lacrimosa e glimpse: nunca no treino ou na escolha do próprio teste.

Pegadinhas: dt do marcador cria saltos falsos (o atraso vagueia de 60 a 324 ms); por isso o
som. Produtos com casa > 7 não aferida: relate também só com casa ≤ 7. Exibições repetidas:
conte também por (tela, coluna) distinta. Não reabra a A3 nesta rodada; se achar a causa das 0
consertadas da A3, descreva no relatório, sem nova medida aprovável.

Território: tab/maos_decod_*.py e tests/test_maos_decod_*.py; saída só em MAOS_FRENTE_A;
rodadas 1111–1119; porta 8101.

Entregue: a1_medida.json e a2_medida.json, as rodadas 1111 e 1112, gate verde, commit no
branch, resumo curto em português.
```
