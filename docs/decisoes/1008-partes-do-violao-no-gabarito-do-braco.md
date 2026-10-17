# 1008 — Partes do violão e painéis da tela no gabarito do braço

**Data**: 2026-10-17. **Decisão do dono**:
- No chat: "não seria bom marcar outras partes, o buraco do violão, cavalete…".
- Depois, a caixa no lugar da linha: "às vezes só tem a câmera da mão direita em cima da
  câmera da mão esquerda".

## Contexto

- O gabarito do braço (`data/gold/maos/braco.json`, rodada
  [1005](../rodadas/1005-gabarito-do-braco.md)) tinha só o braço:
  - cordas 1 e 6;
  - pestana (nut);
  - trastes.
- A base das mãos ([1006](1006-maos-viram-base-de-treino.md)) precisa de duas coisas:
  - as cordas também onde a mão direita ataca (checagem K3);
  - um teste de "estou vendo o violão" mais forte do que o braço sozinho.
- O tampo é rígido: pestana, saddle, cavalete e boca têm posições fixas entre si. Várias partes
  achadas que se encaixam num violão só dão mais certeza do que uma parte.
- Alguns canais (sky guitar, guitar dell'arte) mostram duas câmeras:
  - lado a lado;
  - ou com a câmera de uma mão como janela por cima da outra.

  Uma reta do braço não continua de um painel para o outro.

## Opções

1. **Só o braço** (como estava). Contra: as cordas na boca e o saddle ficam sem rótulo.
2. **Todas as partes, inclusive as tarraxas.** Contra: as tarraxas ficam longe das mãos e quase
   sempre fora do quadro. A pestana já marca aquela ponta.
3. **Saddle das cordas 1 e 6, cavalete, boca e painéis.** Campos opcionais, com "oculto".

## Decisão

Opção 3. Os campos por quadro, na ferramenta `tab.maos_braco_gabarito` (commits `3320d46a`,
`f088bdb6`, `e217e4e6`):

| campo | valor |
| --- | --- |
| `saddle1`, `saddle6` | ponto onde a corda cruza o rastilho, ou `"oculto"` |
| `cavalete` | 2 pontos (primeiro o lado da corda 6), ou `"oculto"` |
| `boca` | 5 a 8 pontos na borda, ou `"oculto"`. Com 5, define a elipse da boca vista em perspectiva |
| `paineis` | `"nao"` (uma câmera), ou 2 a 3 caixas `[[x, y], [x, y]]`. Na sobreposição, vale a menor |
| `divisao` | linha antiga (q02, q07, q13, q21, q22, q23): guardada, não editável, refeita como `paineis` |

**Convenções do dono ao marcar** (chat, 2026-10-17). Elas valem como contrato do rótulo:

1. **Cavalete e boca: só a parte visível.**
   - Quando a mão ou a borda da câmera cortam, os pontos ficam no trecho que aparece.
   - Os 2 pontos do cavalete dão a **reta** do cavalete. Eles **não** são as pontas físicas
     dele.
   - Os pontos da boca ficam no arco visível. Bastam para ajustar a elipse, mas não ficam
     espalhados pela volta inteira.
2. **Painéis: a caixa 1 é a câmera da mão direita, a caixa 2 é a da mão esquerda.** A ordem
   das caixas tem significado.
3. **Trastes debaixo da mão são marcados assim mesmo, por estimativa.**
   - O dono estima a posição pela noção dos outros trastes, da pestana, de pedaços visíveis do
     traste e dos quadros anteriores.
   - Esses pontos são estimados, não vistos. Estão registrados nas observações de q55, q56,
     q60 e q61, e acontecem em outros quadros sem nota.
   - Consequência para a medida: o erro de um detector num traste coberto inclui o erro da
     estimativa do dono.
   - Um detector por imagem pode, com razão, não achar um traste coberto. Isso não conta
     como erro dele se ele disser "não achei".

**Outras notas do dono que entram na base:**
- **Capotraste**:
  - casa 2: q04 e q42–q46 (kenneth acoustic, mesmo vídeo) e q10;
  - casa 1: q14.

  Fonte para `violao.capotraste` ([1007](1007-formato-da-base-das-maos.md)), com
  `capotraste_fonte = "dono"`.
- **q39**: não há mão direita no quadro.

## Consequências

- `registro_completo` (o braço) não mudou. A rodada [1015](../rodadas/1015-m11a-braco-rastreado.md)
  mede só as marcas do braço, e as partes não entram nos critérios dela.
- Detector das partes e encaixe no violão-molde ficam para depois do M11a. Uma rodada própria,
  com critérios escritos antes, vai dizer:
  - quais partes entram;
  - como fica a regra de "não achei";
  - como a reta do cavalete, e não as pontas dele, entra no encaixe.
- Nos vídeos com painéis, nenhuma geometria atravessa de uma caixa para outra. Cada painel é
  uma câmera.
