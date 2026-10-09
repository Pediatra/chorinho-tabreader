# Rodada 43 — o painel está em y≈640–865 e o que falha é o limiar dos picos

## 1. A detecção por uniformidade funcionou

Apliquei o critério que eu vinha prometendo — **faixa horizontal de fundo uniforme** (fração de
pixels perto da mediana da linha > 0,82) — no quadro do `a banda — chico buarque`:

```
(557, 642, 85)   ← área com os nomes de acorde
(646, 687, 41)   ← vão entre corda 1 e 2
(690, 731, 41)   ← vão entre 2 e 3
(734, 775, 41)   ← vão entre 3 e 4
(778, 819, 41)   ← vão entre 4 e 5
(823, 863, 40)   ← vão entre 5 e 6
```

Cinco faixas uniformes de **altura 41** com espaçamento regular: **são os vãos entre as 6 cordas**.
Logo as cordas estão em **y ≈ 643, 688, 732, 776, 820, 864** — **passo ≈ 44 px**, e não os 8–13 px
que eu tinha suposto.

Isso de uma vez:
- **localiza o painel** (y ≈ 640–865);
- **rejeita o vídeo do violão** (textura = sem faixa uniforme longa);
- e mostra que o painel **não ocupa a largura toda** (a tab vai até x ≈ 1500 de 2220).

## 2. E o que impede o segmentador de achar as cordas

Dentro do painel (y 600–900), a `binarizar` dá **3 % de tinta** e **0 picos** acima de 0,30.
Fazendo a conta: 6 cordas tracejadas, cada uma cobrindo ~50 % da largura da tab (que é 66 % do
quadro) → **~0,33 de cobertura por linha relativamente ao quadro inteiro**. Meu limiar de pico é
**0,30** — ou seja, as cordas ficam **exatamente no limite**, e com a suavização caem abaixo.

## 3. A correção é de parâmetros, em dois pontos

1. **Restringir x ao painel** (x ≈ 40–1500) antes de medir cobertura — aí a mesma corda passa de
   0,33 para **~0,5**, com folga;
2. **Baixar o limiar de pico** (0,30 → ~0,15) para painéis de linha tracejada e fina, que é o caso
   do `cifra club` (e possivelmente de `tv cifras`, do mesmo estilo);
3. usar a **faixa uniforme como entrada** do segmentador, em vez de faixas fixas de y.

Nada disso é modelo, e nada disso é novo em conceito: é o que eu tinha concluído, agora com os
números que faltavam (y, passo, largura e cobertura).

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** nos 4 canais com gabarito |
| **localização do painel** | **método funcionando**: uniformidade acha o painel e rejeita o vídeo |
| **geometria neste painel** | bloqueada por **dois parâmetros** (limiar de pico e recorte em x) — causa medida |
| **tempo** | mecanismo confirmado (branco → laranja); destrava quando a grade for lida |

## 5. Próximo passo, com os números na mão

1. recortar x ao painel (40–1500) e refazer o perfil → esperado ~0,5 por linha;
2. baixar o limiar de pico para 0,15 e refazer a progressão de 6 linhas → esperado passo ~44 px;
3. com a grade lida, rodar a **série de cor por token** (branco ↔ laranja) e medir o avanço;
4. desenhar a **caixa do painel detectado** em todo resultado.

Esta rodada trocou três rodadas de tentativa por coordenada por **um número medido**: o painel está
em y 640–865, passo 44 px, largura até x≈1500. O resto é ajuste.
