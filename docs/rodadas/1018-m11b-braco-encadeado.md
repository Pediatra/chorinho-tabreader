# 1018 — M11b: braço rastreado em cadeia, com busca local

**Data**: 2026-10-17. **Estado**: regras a priori. Este documento ganha commit **antes** de os
quadros de teste serem sorteados, marcados ou medidos. Contexto:
[1015](1015-m11a-braco-rastreado.md) (M11a reprovou no CA2), estratégia
[1009](../decisoes/1009-estrategia-do-braco-quadro-a-quadro.md), medidas
[1017](1017-molde-e-cortes.md).

## Pergunta

Partindo de **um** quadro-chave do dono por vídeo, o rastreio em cadeia com busca local acha o
braço ao longo do vídeo, inclusive em câmera aberta e depois de trocas de plano? E ele diz
"não achei" quando não acha?

## Método (os detalhes são ajustados só no desenvolvimento e congelados antes do teste)

- **Cadeia**: o rastreador anda do quadro-chave até o alvo em passos fixos de tempo. Em cada
  passo, ele procura os pontos só numa janela em volta do braço do passo anterior. A janela é
  o polígono das cordas 1 e 6 alargado e estendido até a pestana. Esta é a correção da falha
  do M11a, em que os pontos iam para a tablatura.
- **Âncora**: a cada passo, o casamento é tentado contra o quadro-chave, dentro da janela
  prevista. Só quando isso falha vale o casamento com o passo anterior. Isso evita deriva.
  Se a cadeia e a âncora discordarem, a resposta é "não achei".
- **Troca de plano**: é detectada pela geometria (queda de inliers ou salto da homografia),
  não pela cor; a 1017 mostrou que a cor perde o zoom na mesma cena. Depois de uma troca, a
  cadeia para. Ela só volta a "achei" com um casamento direto contra o quadro-chave.
- **Painéis**: nos vídeos com caixas, a busca fica dentro da caixa do painel que contém o
  braço no quadro-chave ([1008](../decisoes/1008-partes-do-violao-no-gabarito-do-braco.md)).
- Determinístico, sem treino, sem nada da tablatura e sem dependência nova.
- O "não achei" do M11a pelo determinante (zoom tomado como erro, q55) é revisto no
  desenvolvimento.

## Divisão

- **Desenvolvimento**: os 66 quadros do gabarito do braço (q01–q66) e os vídeos deles. Todos
  já foram vistos.
- **Teste**: 8 vídeos novos, de 8 canais que **não** estão no gabarito do braço. Por vídeo,
  são 1 quadro-chave e 4 alvos, 40 marcas no total, num gabarito separado
  (`data/gold/maos/braco_m11b.json`). Os ids desse arquivo são q01, q02… da
  ferramenta de marcação; não se confundem com os q01–q66 do desenvolvimento porque o arquivo
  é outro.
  - **Sorteio** (semente 20261018), feito por código e antes de qualquer marca:
    - canais do censo das mãos fora do gabarito do braço;
    - 1 vídeo por canal;
    - 8 canais.
  - **Quadro-chave**: o primeiro instante sorteado (a partir de 10 % da duração) em que o
    dono vê o braço (`sim` ou `parcial`). Se o braço não aparece, passa-se ao próximo instante
    da lista sorteada. O dono não escolhe a dedo.
  - **Alvos**: 4 instantes sorteados uniformemente entre o quadro-chave + 5 s e o fim do vídeo.
    Eles **não** são trocados se o braço sumir: um alvo sem braço vale como teste do
    "não achei".
- O teste roda **uma vez**, com tudo congelado.

## Sorteio feito (2026-10-17, antes de qualquer marca)

`python -m tab.maos_braco_m11b etapa1` → `data/saida/maos/m11b/` (`sorteio.json`, 40 quadros
candidatos, 5 por vídeo, q01–q40 na ordem do sorteio). Vídeos: pablo romé (vals de fortea),
serge kottelat (love of my life), lonelypicker (it's a heartache), tv on guitar (mario wonder),
paolo d'angelo (dust in the wind), transcriptor (tárrega, estudo em mi menor), kimny's guitar
(valsa sem nome), vvxofingerstyletab (resister). Os alvos só são sorteados depois que o dono
marca os candidatos (`etapa2`).

**Emenda (2026-10-17, antes de qualquer execução do rastreador no teste):**
- O vídeo do serge kottelat é Brian May na guitarra elétrica. O dono deixou os 5 candidatos
  (q06–q10) em branco e pediu um substituto, coerente com o descarte do raman korshun.
- O substituto foi sorteado por código: `python -m tab.maos_braco_m11b substituir`, com
  gerador `"20261018:substituto:serge kottelat"` sobre os canais elegíveis que ainda não
  foram usados. Saiu **mr. tabs** (guns n' roses, patience; violão acústico). Os candidatos
  são q41–q45, e o vídeo trocado fica registrado em `substituicoes` no `sorteio.json`.
- O teste continua com 8 vídeos e 32 alvos. Os critérios não mudam.
- O dono marcou completo os 5 candidatos de cada vídeo, e não só até o primeiro com braço.
  Os candidatos que não viram quadro-chave **não** entram nos critérios.

**Emenda 2 (2026-10-17, antes de qualquer execução do rastreador no teste):**
- O sorteio uniforme dos alvos não exigia distância entre eles, e alguns caíram colados:
  - kimny's guitar: 151,66 e 151,71 s;
  - pablo romé: 181,38 e 181,54 s;
  - paolo d'angelo: 402,06 e 402,72 s.
- A pedido do dono, os alvos dos 4 vídeos ainda não marcados foram sorteados de novo por
  código (`python -m tab.maos_braco_m11b refazer`): paolo d'angelo, transcriptor, kimny's
  guitar e vvxofingerstyletab.
  - Gerador: `alvos_espacados`, com distância mínima de 10 s entre alvos. Em vídeo curto, a
    distância cai para o intervalo dividido por 4.
  - Os alvos antigos ficam em `refeitos` no `chaves.json`. As imagens antigas estão em
    `data/saida/maos/m11b/descartados_alvos_colados/`, e os ids q62–q77 foram reusados.
- Os 4 vídeos já marcados ficam como estavam: pablo romé, mr. tabs, lonelypicker e tv on
  guitar.
  - Dois pares seguem quase repetidos: pablo romé (0,16 s) e lonelypicker (1 s).
  - Por isso, os 32 alvos equivalem a cerca de 30 independentes, e o limite superior da
    taxa de falsos com 0 falsos fica um pouco acima dos 9 % escritos.
- Os alvos do vvxofingerstyletab q75–q77 caem de novo na tela final, sem violão. O vídeo
  termina logo depois do quadro-chave, então ficam como teste do "não achei".
- **Regra para os próximos sorteios:** alvos com distância mínima desde o início.

**Emenda 3 (2026-10-17, antes de qualquer execução do rastreador no teste):**
- O dono achou que marcar os 4 alvos de cada um dos 4 vídeos restantes não acrescentava
  informação: são alvos do mesmo vídeo, a 10–20 s um do outro.
- Ficou 1 alvo por vídeo, o mais afastado do quadro-chave (o caso mais difícil):
  - **q65**: paolo d'angelo, +63,6 s;
  - **q69**: transcriptor, +41,2 s;
  - **q73**: kimny's guitar, +87,5 s;
  - **q74**: vvxofingerstyletab. É o único com violão nesse vídeo.
- Mais **q77**, com braço `nao`, para testar o "não achei".
- Os outros 11 (q62–q64, q66–q68, q70–q72, q75 e q76) ficam **fora do teste**, sem marca.
- O teste passa a ter **20 alvos com braço**, 16 dos 4 vídeos já marcados e 4 dos outros,
  **mais 1 sem braço**. Os 8 canais seguem cobertos.
- O CA2 passa a ser "0 falsos nos 21 alvos". Com 0 falsos em ~19 alvos independentes, o
  limite superior de 95 % da taxa de falsos fica em cerca de 15 %. Os limiares não mudam.

## Métricas

**Como o dono marca as cordas** (esclarecido pelo dono em 2026-10-17): os 2 pontos das cordas
1 e 6 ficam no **braço**, da pestana até onde o braço é visível, e não vão até o cavalete. Vale
para os 66 quadros do desenvolvimento e para este teste. Por isso o erro perpendicular só é
conferido no braço, que é onde está a mão esquerda. O trecho até o rastilho é uma
extrapolação; a 1017 mediu que ela erra de 0,07 a 0,39 vão (mediana por canal).

São as mesmas da 1015: pestana e pior traste em casas, cordas 1 e 6 na perpendicular em vãos.
- **certo**: tudo < 1/4.
- **falso**: algo > 1/2, ou "achei" onde o dono marcou braço `nao`.
- **impreciso**: o resto.

## Critérios de aceite (no teste)

| | critério |
| --- | --- |
| CA1 | certos ≥ 95 % dos "achei" |
| CA2 | **0 falsos** nos 21 alvos (emenda 3; eram 32) |
| CA3 | **cobertura**: certos ≥ 50 % dos alvos com braço `sim` (decisão do dono, 2026-10-17) |
| CA4 | cobertura e falsos relatados por canal, com denominador; alvos `parcial` só aqui |
| CA5 | duas execuções idênticas (`cmp`) |
| CA6 | gate verde |

**Passa se CA1, CA2, CA3, CA5 e CA6 passam.** Limiar mudado depois da medida invalida a
rodada.

## Riscos declarados antes

- **O erro do clique do dono não foi medido.** O dono recusou a remarcação de repetição: "eu
  não erro uma coisa simples dessas". Se o CA1 reprovar por imprecisos entre 0,25 e 0,35 vão,
  a rodada reprova assim mesmo. A remarcação fica como o primeiro diagnóstico a pedir nesse
  caso.
- **Com 32 alvos, 0 falsos não prova uma taxa baixa.** O limite superior de 95 % para a taxa
  de falsos fica em cerca de 9 %. A rodada mede se o método funciona; a taxa do rollout será
  medida na auditoria do ciclo de rótulos.
- **Desenvolvimento e teste diferem.** O desenvolvimento tem sky guitar, cifra club e outros
  canais vistos. O teste tem só canais novos, o que é proposital: mede se o método passa para
  outros canais.

## Resultado no teste (2026-10-17, cfg2 congelada, commit 1bcb9b35; emenda 3)

```
python -m tab.maos_braco_cadeia pares --indice data/saida/maos/m11b/indice.json \
  --ouro data/gold/maos/braco_m11b.json --pares data/saida/maos/m11b/pares_teste_emenda3.json \
  --pasta-quadros data/saida/maos/m11b/quadros --saida data/saida/maos/m11b/teste_cadeia_a.json
```

| canal | alvos | certo | impreciso | falso | não achou |
| --- | --- | --- | --- | --- | --- |
| pablo romé | 4 | 3 | 1 | 0 | 0 |
| mr. tabs | 4 | 1 | 3 | 0 | 0 |
| lonelypicker | 4 | 1 | 0 | 0 | 3 |
| tv on guitar | 4 | 1 | 1 | **1** | 1 |
| paolo d'angelo | 1 | 1 | 0 | 0 | 0 |
| transcriptor | 1 | 1 | 0 | 0 | 0 |
| kimny's guitar | 1 | 0 | 1 | 0 | 0 |
| vvxofingerstyletab | 1 + 1 sem braço | 1 | 0 | 0 | 1 (o q77, sem braço: correto) |
| **total** | **21** | **9** | **6** | **1** | **5** |

| | critério | medido | |
| --- | --- | --- | --- |
| CA1 | certos ≥ 95 % dos "achei" | 9/16 = **56 %** | **reprova** |
| CA2 | 0 falsos nos 21 | **1** (q58: pior traste 1,44 casa, cordas 0,65 vão) | **reprova** |
| CA3 | certos ≥ 50 % dos 20 com braço | 9/20 = **45 %** | **reprova** |
| CA5 | duas execuções idênticas | `cmp` idêntico | passa |
| CA6 | gate verde | sim | passa |

**Veredito: reprova.** No desenvolvimento, o rastreador deu 26 certos de 27 achados, mas fora
da amostra caiu para 9 de 16.
- **Imprecisos**: os 6 ficam nas cordas, entre 0,25 e 0,36 vão; os trastes ficam
  ≤ 0,14 casa. É o caso que esta rodada declarou de antemão: reprova assim mesmo.
- **Falso**: o do q58 é de trastes, depois de 67 passos com 13 perdidos.

**Consequência para a 1021**: os rótulos R do piloto vêm deste rastreador. Fora da amostra, o
erro deles nas cordas costuma ficar entre 0,25 e 0,36 vão. O A1 (só sintético) e o A2 (só R)
separam esse efeito, e o critério da 1021 não muda.

### Diagnóstico depois do veredito: repetibilidade do dono (remarcação cega)

O dono remarcou às cegas 10 alvos do teste, com ids embaralhados e renomeados (r01–r10), numa
cópia em `data/saida/maos/m11b/remarca/`. O alvo original dele é a referência.

| | cordas (vão) | nut (casa) | pior traste (casa) |
| --- | --- | --- | --- |
| dono contra dono | mediana **0,14**, máximo 0,21 | ≤ 0,03 | ≤ 0,11 |
| rastreador contra dono, nos 6 imprecisos | 0,25–0,36 | — | — |

- **Os 10 de 10 dão "certo"** quando o dono é comparado com ele mesmo.
- **A régua de 1/4 de vão está acima do ruído do gabarito.** A diferença entre as duas
  marcações do dono é de 0,14 vão, o que dá ~0,1 vão de ruído por marcação.
- **Os imprecisos do rastreador são erro real dele**, cerca de 2 vezes o ruído do dono. Não
  são efeito da régua. O veredito fica como está.
