# 0003 — O painel é um retângulo, e a máscara depende do recorte

**Data:** 2026-10-08/09 (noite) · **Status:** aceita · **Origem:** medição no acervo novo

## Contexto

A primeira varredura do acervo novo (3.993 vídeos, 17 canais) deu **96,5 % com
tablatura** e expôs dois erros de critério na escolha do painel, os dois conferidos
**desenhando as caixas no quadro** e olhando.

### Erro 1 — o braço do violão ganhava

Num quadro real do `sky guitar` (t=88 s):

| faixa | o que é | linhas | glifos | centrados | uniformidade |
| --- | --- | --- | --- | --- | --- |
| `meio` | **a tablatura** | 6 | 36 | 29 | **0,888** |
| `base` | **braço + mão + corpo** | 6 | 39 | **34** | 0,842 |

O critério antigo ordenava por `(glifos_centrados, n_glifos)` → escolhia o **braço**.
E a lógica estava em **três cópias** (`inventario`, `transcrever`, `varredura`), todas
com o mesmo erro. A uniformidade do fundo separa os dois, e já tinha sido medida nas
rodadas 42–45 — mas nunca entrou no código.

### Erro 2 — o cursor era procurado no quadro inteiro

`detectar_cursor` tem portão de altura (>= 50 % da imagem). Chamado no **quadro**
(1080 px), exige faixa de 540 px; o cursor tem a altura do **painel** (~150 px).
Resultado medido: cursor em **69 de 3.993** vídeos, quando o histórico falava de ~50 %
dos quadros. Procurando **dentro do ROI da faixa**, o mesmo vídeo passou a dar
`janelas_com_cursor: [[0.5, 4.0], [5.0, 10.0]]`.

### Erro 3 (o mais profundo) — a máscara depende da largura do recorte

Com o painel estreitado ao retângulo onde as linhas existem, mediu-se a segmentação em
função da largura do recorte, **no mesmo quadro**:

| recorte | máscara escolhida | glifos | o que são |
| --- | --- | --- | --- |
| 570–594 px | `otsu` | **3** | **os 3 algarismos reais** (`0 2 3` na 5ª corda) |
| 700 px | `contraste_k21_d12` | 7 | 3 reais + 4 do vídeo |
| 1000 px | `contraste_k31_d25` | 12 | 3 reais + 9 do vídeo |
| 1920 px (tira inteira) | `contraste_k31_d25` | 36 | 3 reais + **33 lixo** |

Ou seja: **a cascata de máscaras muda com o recorte**, e o recorte largo faz o extrator
preferir uma máscara que arrasta o vídeo vizinho. O painel apertado não é "menos
informação": é a leitura **correta** daquele painel, com confiança 0,996 / 0,931 / 0,999
nos três algarismos.

## Decisão

1. **`tab/painel.py` é a implementação única**: uniformidade do fundo primeiro,
   glifos centrados depois, sem limiar fixo. `inventario`, `transcrever` e `varredura`
   importam de lá;
2. **o cursor é procurado no ROI da faixa escolhida**, nunca no quadro inteiro;
3. **o painel é estreitado em x** ao maior trecho onde **quatro ou mais** das seis
   cordas coexistem (`extensao_das_linhas`). Exigir tinta em *qualquer* linha não
   separa (o braço tem cordas com espaçamento parecido); usar a uniformidade por coluna
   também não (o trecho mais liso do quadro é a **margem vazia** ao lado);
4. **painel pequeno é painel**: o piso de 5 glifos valia para achar candidatos, não para
   aceitar o recorte refinado — baixado para 1 no refino. Um painel com 3 notas é o que
   a tela mostra e tem de ser lido como 3 notas.

## Consequências

- a varredura passa a **gravar a uniformidade de cada faixa**, para que a reordenação
  possa ser refeita depois **sem reabrir vídeo**. Foi exatamente o que faltou nesta
  noite: a primeira varredura mediu as faixas mas não gravou o critério novo, e teve de
  ser refeita;
- o custo do refino é **um `segmentar` a mais por quadro com painel**, e o custo da
  uniformidade é um `medianBlur` por faixa: a varredura continua na casa de 1–2 s por
  vídeo. O que a deixou 30× mais lenta nesta noite foi rodar transcrições ponta a ponta
  **em paralelo** — cada uma lê o vídeo quadro a quadro;
- o número oficial (0,889) **não muda** com isto: ele é medido em recortes já extraídos
  do gabarito. O que muda é o que o pipeline lê em vídeo novo.

## Verificação

- `tests/test_painel.py`: fundo liso separa painel de braço (0,967 × 0,683 no dado
  sintético), o painel ganha quando o braço também tem 6 linhas aparentes, e quadro
  vazio não vira painel;
- ponta a ponta num vídeo do `sky guitar` (`#4 (beginner) free pdf.mp4`, t≈88 s):
  painel `meio`, passo 29,4, **3 notas — corda 5, casas 0, 2 e 3** com confiança
  0,996 / 0,931 / 0,999, que é **exatamente** o que se vê no quadro zoomado;
- exportação MusicXML válida (score-partwise 4.0, clef TAB linha 5, 6 linhas,
  `staff-tuning`, `technical/string`+`fret`), com o relatório declarando
  `tempo_medido: false` porque os 3 onsets saíram no mesmo instante.

## O que continua aberto (bloqueio do MVP)

**A resolução do onset por nota.** O cursor é encontrado, as janelas existem, mas
`tempos_do_cursor` devolve o **mesmo instante** para notas diferentes: 3 instantes
distintos para 36 notas, e 1 para 3. O critério de pronto do dono do projeto é "um vídeo
inteiro correto", e sem onset por nota o MusicXML sai com duração constante declarada —
honesto, porém não é a transcrição com tempo. É o próximo alvo.
