# 1007 — M10: formato da base das mãos (`chorinho/maos@1` + `.npz`)

**Data**: 2026-10-16. **Estado**: plano aprovado pelo dono ("tá aprovado, pode iniciar"); o
formato abaixo é o da seção 4 do [plano](../guias/plano-dataset-maos.md), detalhado.

## Contexto

A base das mãos ([1006](1006-maos-viram-base-de-treino.md)) guarda, por vídeo:

- os **eventos** (uma nota do produto cada), com o tempo do som, as checagens e o nível;
- o **denso**: mãos, corpo, braço do violão e caixa da tablatura, quadro a quadro.

O `chorinho/video@1` é da trilha da tablatura e não muda. É o mesmo desenho das decisões 2003
(áudio) e 3002 (partitura): arquivo irmão com a chave do evento.

## Decisão

Dois arquivos por vídeo, lado a lado: `<nome>.maos.json` e `<nome>.maos.npz`.

### `<nome>.maos.json` (esquema `chorinho/maos@1`)

```json
{
  "esquema": "chorinho/maos@1",
  "produto": "data/saida/…/x.json", "produto_sha256": "…",
  "audio": "data/saida/…/x.audio.json", "audio_sha256": "…",
  "denso": "x.maos.npz", "denso_sha256": "…",
  "video": {"arquivo": "sky guitar/….mp4", "fps": 29.97, "largura": 1920, "altura": 1080},
  "gerado_por": {"commit": "…", "detector_maos": "…", "detector_braco": "…",
                 "parametros": {}},
  "violao": {"canhoto": false, "capotraste": 0, "capotraste_fonte": "canal"},
  "eventos": [
    {"tela": 1, "passagem": 1, "exibicao": 0, "coluna": 3, "corda": 2, "t_ini": 245.011,
     "casa": 5, "t_som": 245.19, "janela": [120, 150],
     "checagens": {"K1": {"passou": true, "valor": 0.82},
                   "K2": {"passou": true, "valor": 0.4},
                   "K3": {"passou": true, "valor": -0.03},
                   "K4": {"passou": true, "valor": null}},
     "nivel": "ouro", "motivo": null}
  ],
  "resumo": {"eventos": 1, "ouro": 1, "prata": 0, "recusado": 0, "motivos": {}}
}
```

**Regras de cada campo:**
- `audio` e `audio_sha256` podem ser `null` (vídeo sem arquivo de áudio). Os outros
  caminhos e hashes são obrigatórios, e os hashes têm 64 caracteres hexadecimais.
- `violao.canhoto`: booleano ou `null` (não se sabe). `capotraste`: inteiro de 0 a 12 ou
  `null`. `capotraste_fonte`: `"tela"`, `"canal"`, `"imagem"`, `"dono"` ou `null`. Ela é
  `null` se, e só se, `capotraste` é `null`.
- **Chave do evento**: `(tela, passagem, exibicao, coluna, corda, t_ini)`, a do
  `chorinho/video@1`. Ela é única no arquivo.
  - `passagem`, `exibicao` e `t_ini` podem ser `null`, como no produto, para nota sem
    marcador.
  - `corda` vai de 1 a 6; `casa` vai de 0 a 24.
- `t_som`: número ou `null`. `janela`: `[i0, i1]`, índices de quadro do denso, com
  `0 ≤ i0 < i1 ≤ N`, ou `null`.
- `checagens`: sempre as quatro, K1–K4, cada uma `{"passou": bool | null, "valor": número |
  null}`. `null` em `passou` significa "não deu para checar".
- **Nível**, conferido pelo validador a partir das checagens:
  - `ouro`: as quatro com `passou: true`;
  - `prata`: K1, K3 e K4 com `true`, e K2 diferente de `true`;
  - `recusado`: todo o resto.
- `motivo`: texto não vazio no `recusado`; `null` no ouro e no prata.
- Se `t_som` é `null`, então K1 não passa e o nível é `recusado`.
- Se `janela` é `null`, então K2 e K3 não passam e o nível é `recusado`.
- `resumo`: contagens iguais às dos eventos. `motivos` conta os eventos recusados por motivo.

### `<nome>.maos.npz` (numpy, `allow_pickle=False`; N = quadros amostrados)

| matriz | forma | tipo | conteúdo |
| --- | --- | --- | --- |
| `pts` | (N,) | float64 | PTS de cada quadro, em segundos, estritamente crescente |
| `maos` | (N, 2, 21, 3) | float32 | x, y e score dos 21 pontos. Índice 0 = **mão do braço** (a que pisa), 1 = **mão do ataque**, para servir também a canhoto. NaN se ausente |
| `maos_origem` | (N, 2) | int8 | 0 ausente, 1 Wholebody, 2 MediaPipe |
| `maos_trilha` | (N, 2) | int16 | id da trilha da mão entre quadros, −1 se ausente |
| `corpo` | (N, 6, 3) | float32 | ombros, cotovelos e pulsos do Wholebody (COCO 5–10), x, y e score; NaN se ausente |
| `braco_trastes` | (N, 25, 2) | float32 | ponto de cada traste no eixo do braço, como no gabarito do dono. Índice 0 = pestana (nut), k = traste k; NaN se não visível |
| `braco_corda1` | (N, 2, 2) | float32 | dois pontos da reta da corda 1, como no gabarito; NaN se não achou |
| `braco_corda6` | (N, 2, 2) | float32 | idem, corda 6 |
| `braco_conf` | (N,) | float32 | confiança do braço, de 0 a 1; NaN se não achou |
| `braco_achou` | (N,) | bool | o detector do braço disse "achei" |
| `tab_caixa` | (N, 4) | float32 | x0, y0, x1, y1 da tablatura no quadro; NaN se não há |

**Regras:**
- Todas as matrizes têm o mesmo N.
- Origem 0 ⇔ trilha −1 ⇔ pontos todos NaN, mão a mão.
- Coordenadas finitas ficam dentro do quadro, com folga de 5 % da largura e da altura.
- Score em [0, 1].
- Onde `braco_achou` é falso, `braco_conf` é NaN.
- Na caixa, x0 < x1 e y0 < y1 quando finita.

As coordenadas são float32, e não float16: em float16, perto de x = 1.920 o passo é de 1 px,
cerca de 1/22 do vão entre cordas. Custo: ~1,4 kB por quadro, ou ~13 GB para as ~171 h de
tablatura na tela a 15 quadros por segundo. Isso corrige a estimativa da seção 4 do plano (0,5
kB).

### Pontos que a especificação deixava abertos (adotados no validador, na leitura mais estrita)

- Mão presente (origem 1 ou 2) tem os 21 pontos finitos: x, y e score.
- NaN pela metade (x sem y, ou score sem ponto) é erro. Infinito é sempre erro.
- `tab_caixa` é toda finita ou toda NaN em cada quadro.
- Os pontos do braço **não** são obrigados a ser NaN onde `braco_achou` é falso: o palpite
  cru pode ficar guardado (princípio 4 do plano). Só a confiança é NaN.
- Chaves extras no JSON são aceitas; no `.npz`, são recusadas. O denso tem N ≥ 1.
- `t_ini` e `t_som` ≥ 0; `tela` e `coluna` ≥ 1; `passagem` ≥ 1 ou null; `exibicao` ≥ 0 ou
  null.
- O JSON não aceita NaN nem Infinity. `denso_sha256` é conferido pela linha de comando
  (`python -m tab.maos_esquema X.maos.json`).

## Consequências

- O validador `tab/maos_esquema.py` aplica todas as regras acima e entra no gate, com testes
  sintéticos.
- Quem consome junta o `chorinho/video@1` (gabarito), o `chorinho/audio@1` (som) e este
  arquivo pela chave do evento.
- A partitura (3002) entra pela chave da coluna, sem campo aqui.
