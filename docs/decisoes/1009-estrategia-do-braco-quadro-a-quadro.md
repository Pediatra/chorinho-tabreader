# 1009 — Estratégia do braço quadro a quadro (depois do M11a)

**Data**: 2026-10-17. **Origem**: conversa de ideias com o dono depois da reprovação do M11a
([1015](../rodadas/1015-m11a-braco-rastreado.md)), com uma pesquisa sobre visão computacional
em violão trazida por ele.

## Contexto

O M11a reprovou no CA2:
- 8 de 11 "achei" saíram certos;
- nenhum "achei" foi falso, em 30 quadros;
- a cobertura foi zero nos 3 canais com câmera aberta, porque os pontos do quadro alvo iam para
  a tablatura.

O rastreador parte de um quadro-chave do dono **por vídeo**. Isso não escala para os 3.899
vídeos.

**Respostas do dono** (chat, 2026-10-17):
1. **Capacidade de marcar**: ~50 quadros-chave por hora sem cansar; até ~500 no total, em
   alguns dias.
2. **Câmera**: a maioria dos vídeos-aula tem câmera parada. É impressão dele, ainda não medida.
3. **Precisão**: errar a casa ou a corda vizinha é inaceitável. Ficar "sem braço" num quadro é
   aceitável, porque a nota só perde o nível ouro.
4. **Vibração da corda**: vale testar no futuro, como peso de confiança.

## Decisão (estratégia; cada passo vira rodada com critérios escritos antes)

1. **Ciclo de rótulos.** O rastreador produz rótulos; ele não roda no acervo.
   1. O dono marca poucos quadros-chave, até ~500, em vários canais.
   2. O rastreador estende cada um a muitos quadros, só os de alta confiança.
   3. O dono audita uma amostra.
   4. Com isso, treina-se um **detector do braço sem quadro-chave**.
   5. O detector dá o início em cada vídeo, e o rastreador segue dali.

   O detector exige dependência nova, com aprovação do dono. A ultralytics, por exemplo, é
   AGPL. A calibração pela música só entra como rótulo ou validação do detector, como diz a
   1006.
2. **Rastreio encadeado.**
   - Procurar os pontos só perto do braço do quadro anterior. Isso resolve a falha do M11a.
   - Reancorar de tempos em tempos, no quadro-chave ou no violão molde. Se a corrente e a
     âncora discordarem, vale "não achei".
   - Corte de câmera: recomeçar, nunca seguir através dele.
   - Vídeo com painéis: rastrear dentro da caixa do painel
     ([1008](1008-partes-do-violao-no-gabarito-do-braco.md)).
   - Rever o "não achei" pelo determinante, que pode confundir zoom com erro (q55: 105 inliers e
     recusado).
3. **Violão molde.**
   - As cordas são retas da pestana ao saddle. As cordas 1 e 6 nesses dois pontos dão o plano
     das cordas: as 6 cordas em leque e os trastes pela regra das 12 notas **com perspectiva**.
   - A "fórmula do luthier" sem perspectiva da pesquisa não serve. A 1005 mediu: o modelo afim
     descreve no máximo 77,8 % dos trastes, e o projetivo descreve 100 %.
   - Boca e cavalete conferem o encaixe ("não achei" geométrico) e reancoram quando o braço está
     coberto.
   - Dois moldes: náilon, com o braço encontrando o corpo na casa 12, e aço, na casa 14.
4. **Cordas.**
   - Bastam as cordas 1 e 6; as do meio saem pelo leque.
   - No náilon, as agudas quase não aparecem. Os bordões são a âncora.
   - Nada de máscara de pele por cor: tampo e escala claros têm cor de pele. A máscara sai dos
     pontos da mão detectada.
5. **Mãos que somem.**
   - O dado cru nunca é inventado. Lacuna curta preenchida fica marcada como preenchida.
   - Mão ausente perto do instante do som tira o nível ouro da nota.
   - Identidade da mão: pela posição (a mão no braço é a mão do braço). Nos painéis, pela caixa:
     a caixa 1 é a mão direita.
6. **K2 (ponta do dedo na célula)**: casa com rigor, corda com tolerância.
   - Na câmera única, a ponta do dedo dobrado aparece sobre a corda de cima (paralaxe), e não dá
     para saber se o dedo aperta ou paira.
   - A tablatura e o áudio dão a resposta. A visão só não pode contradizer.
7. **Para depois**:
   - corda vibrando, ou borrada logo depois do ataque em close, como peso de confiança (ideia
     aprovada pelo dono para testar);
   - TabCNN e GuitarSet, na fase do áudio e do modelo.
8. **Descartado agora**:
   - câmera de profundidade, câmera dupla e sensor no braço (o acervo é do YouTube);
   - detecção de linha com precisão de subpixel (o vão de corda é de 10 a 30 px; o limite que
     importa é 1/4 de vão).

## Consequências

Duas medidas baratas antes de escrever a próxima rodada:
- **(a) Violão molde nas 66 marcas do dono.**
  - A corda marcada no braço, prolongada, passa pelo saddle?
  - O saddle cai onde a regra das 12 notas com perspectiva manda?
  - As proporções da boca são estáveis por tipo de violão?
- **(b) Cortes de câmera numa amostra do acervo**: a impressão de "câmera parada" é medida.

A rodada M11b (rastreio encadeado) é escrita depois de (a) e (b), com quadros de teste novos.
Os q37–q66 viram material de ajuste.
