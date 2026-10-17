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
| CA2 | **0 falsos** nos 32 alvos |
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
