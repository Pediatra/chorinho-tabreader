# 1020 — DeepSeek direto na API: o recorte do braço resolve as cordas?

**Data**: 2026-10-17. **Estado**: regras a priori, com commit antes do primeiro pedido.

**Pedido do dono**: o dono tem uma chave da API da DeepSeek e quer testes leves com o
`deepseek-flash` (servido pelo DeepSeek-V4.1-Flash-1017).

**Antecedente**: na [1019](1019-pre-marcacao-por-consenso-de-vlms.md), o proxy caiu e a
coleta não terminou. Na espiada do desenvolvimento (q01 e q02), as 8 respostas válidas dos 6
modelos foram "falso":
- o nut ficou bom (< 0,4 casa);
- as cordas erraram de 0,8 a 20 vãos.

## Hipótese

A API reduz toda imagem para cerca de 1,7 megapixel (até 1024 tokens por imagem). Num quadro
1920×1080, as cordas vizinhas ficam a uns 14 px de distância depois dessa redução. A hipótese
é que o modelo não consegue separar as cordas nessa resolução.

Se a hipótese vale:
- mandar **só o recorte do braço**, ampliado, deve baixar o erro das cordas;
- numa imagem sintética, o erro deve cair quando o espaçamento das linhas aumenta.

## Acesso

| item | valor |
| --- | --- |
| endereço | `https://api.deepseek.com/chat/completions` (formato OpenAI) |
| modelo | `deepseek-flash` |
| temperatura | 0 |
| imagem | JPEG 92, base64, com `detail: "high"` |
| chave | lida de `~/.config/deepseek.key`, montada só para leitura no container |

A chave nunca vai para log, nem para arquivo de resposta, nem para commit.

## Amostra

- Só os **33 quadros de desenvolvimento** da 1019 (mesma semente 20261019). Os 33 de teste
  ficam lacrados para uma confirmação futura.
- Nenhum quadro da M11b entra.

## Experimentos

| | o que muda | quadros |
| --- | --- | --- |
| E0 | sonda sintética: 6 linhas paralelas inclinadas, em fundo marrom, com espaçamento de 8, 14, 20 e 30 px numa imagem 1280×720. Pede as pontas da linha 1 e da linha 6 | 4 imagens × 2 inclinações |
| E1 | prompt da 1019 sem mudança, quadro inteiro, raciocínio **desligado** | 33 de dev |
| E2 | o mesmo, com o raciocínio **ligado** (padrão da API) | 33 de dev |
| E3 | em duas etapas. 1ª: no quadro inteiro, pede a caixa do braço (da cabeça até o corpo). 2ª: recorta a caixa com 10 % de margem, amplia até 1280 de largura (no máximo 1300 px no lado maior) e pede o mesmo JSON nas coordenadas do recorte. Os pontos voltam para o quadro original | 33 de dev |

- No E3, o raciocínio fica no modo que tiver mais certos entre E1 e E2. Em caso de empate,
  fica desligado.
- Uma tentativa extra só para 429, 5xx, tempo limite e conexão recusada.

## Medidas

Valem as da 1019: o mesmo filtro e `tab.maos_braco_tempo.erros` / `classificar`.

**Por experimento**:
- classes;
- mediana e máximo de `perp_cordas` (em vãos), `nut_casas` e `pior_traste_casas`, nas
  respostas válidas;
- tempo e tokens.

**No E0**:
- erro perpendicular das linhas 1 e 6, em espaçamentos;
- troca de 1 com 6, contada à parte.

## Critério de decisão (no desenvolvimento)

| resultado | o que fazer |
| --- | --- |
| algum experimento com ≥ 50 % de certos e no máximo 2 falsos em 33 | vale uma confirmação nos 33 de teste, com esse experimento congelado |
| E3 baixa a mediana de `perp_cordas` em pelo menos metade em relação ao E1, sem chegar à linha acima | a resolução é parte do problema: registrar e propor um recorte mais fechado |
| nenhum dos dois | o DeepSeek não marca o braço. Encerrar a pré-marcação por modelo de linguagem, com o número |

**Custo previsto**: cerca de 140 pedidos, menos de US$ 1 nos preços de hoje (US$ 0,15 por
milhão de tokens de entrada e US$ 0,60 de saída, fora do pico).

## Resultado (2026-10-17) — reprovado; rodada encerrada pelo dono

| | n | certo | falso | não achou | cordas, mediana (vãos) | pior traste, mediana (casas) | nut, mediana (casas) | custo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1 sem raciocínio | 33 | 0 | 30 | 3 | 5,91 | 2,64 | 0,19 | US$ 0,007 |
| E2 com raciocínio | 10 (interrompido) | 0 | 10 | — | 2,33 | 1,12 | 0,30 | US$ 0,19 |

- **E0** (sonda sintética): o modelo localiza linhas desenhadas. Com espaçamento de 20 px ou
  mais, o erro fica abaixo de 0,25 espaçamento; com 14 px, fica no limite; com 8 px, erra.
  Custo: US$ 0,001.
- **E1**: sem raciocínio, as respostas são degeneradas. No q01, as duas cordas saem no mesmo
  ponto.
- **E2**: com raciocínio, cada pedido leva cerca de 145 s e 32 mil tokens de saída por
  quadro. Isso é mais caro e mais lento do que o dono marcar.
- **E3** não foi rodado. Mesmo que o recorte cortasse pela metade o erro das cordas do E2
  (2,3 vãos), o resultado ficaria em cerca de 1,2 vão, ainda "falso". Assim, nenhuma linha do
  critério de decisão fica ao alcance.
- **Veredito**: o DeepSeek não marca o braço. Encerrada a pré-marcação do braço por modelo de
  linguagem (somando a 1016, a 1019 e esta). O dono encerrou com cerca de US$ 0,20 gastos.
- **Lição para "não repetir"**: o modelo localiza linhas sintéticas limpas, mas falha nas
  cordas reais. A resolução sozinha não explica o erro: o E2 erra 2,3 vãos onde o E0 acerta.

### Adendo: E3 sem raciocínio (rodado a pedido do dono, US$ 0,01)

| | n | certo | falso | não achou | cordas, mediana (vãos) | pior traste, mediana (casas) | nut, mediana (casas) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E3 recorte, sem raciocínio | 33 | 0 | 20 | 13 | 5,54 | 1,93 | **0,06** |

- **O recorte não muda as cordas** (5,9 → 5,5 vãos). Ele melhora o nut: de 0,19 para 0,06 casa.
- **Sem raciocínio, o modelo preenche um molde em vez de olhar.**
  - A corda 1 e a corda 6 saem no mesmo lugar em 16 de 33 respostas no E1 e em 11 de 33 no
    E3.
  - A corda começa exatamente no ponto do nut.
  - Os mesmos números se repetem em quadros diferentes: `[744, 168]` aparece no q01 e no q12.
- **Conclusão**: cortes e setores não corrigem um modelo que não olha as cordas. Só o nut sai
  bom, e o nut é a marca mais barata para o dono (1 clique). Encerrada.
