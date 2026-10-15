# 0010 — O leitor de notas do produto passa a ser a rede de sistema inteiro

Estado: **aprovada pelo dono em 2026-10-14** ("trocar é a escolha certa").

## Contexto

O leitor antigo (`reconhecer_linha`) segmenta a tablatura em glifos por regra geométrica e
classifica cada glifo com uma rede pequena. Os erros que sobram vêm todos da segmentação:

- algarismo encostado em haste ou em barline é descartado;
- números de dois algarismos se partem em dois;
- acorde empilhado ou fundo cinza vira barline.

Seis tentativas de regra geométrica deram 0 ou pioraram (tabela "não repetir" do
`ESTADO.md`).

O `tab.detector_tab` lê o sistema inteiro de uma vez. A geometria é a mesma do produto
(`escolher_ou_mascara` → `segmentar`), e a rede marca centro, casa e técnica em cada corda.
Foi treinado em sintético e ajustado com os 8 gabaritos de vídeo.

## Medição (validação cruzada por vídeo)

São 8 gabaritos e 2.689 notas. Cada vídeo foi medido por um modelo que não o viu. A régua é
`casar_notas`, com folga de 1,6× para casa de dois algarismos.

| leitor | precisão | revocação | casa |
| --- | --- | --- | --- |
| glifos (`oficial_3`) | 0,962 | 0,830 | 0,943 |
| rede (`v3ft`, CV) | 0,974 | 0,949 | 0,987 |

Só dois vídeos pioram, e as diferenças são estáveis nas 3 sementes:

- retrato: precisão 1,000 → 0,998, uma nota;
- La Vie: casa 1,000 → 0,993, 1–2 notas.

Tempo nos 3 vídeos com marcador (mesmo HEAD, a rede pelo modelo da dobra que não viu o
vídeo):

| vídeo | glifos | rede |
| --- | --- | --- |
| MVP | 40/40 | 40/40 |
| Greensleeves | 34/40 | 38/40 |
| South American | 37/40 | 38/40 |

Nenhum dos três tem tempo falso. Detalhe em `data/saida/n4/avaliacao_regua2.txt` e no `ESTADO.md` (seção do detector, N1–N4).

## Opções

1. Manter o leitor de glifos e continuar consertando a segmentação. Medido 6 vezes, sem ganho.
2. **Trocar pelo leitor `rede` e manter o de glifos como reserva** (`--leitor glifos`).
3. Usar só a rede e apagar o leitor de glifos. Isso perde a comparação e o `simbolo_cru`.

## Decisão

Opção 2:

- `tab.video` e `tab.transcrever` ganham `--leitor rede|glifos`, e o padrão é `rede`;
- os pesos ficam em `artefatos/detector_tab_final_s1/`. São o ajuste fino com os 8
  gabaritos e o sintético, gerados por `data/saida/n4/treinar_ft.py --dobra 0`;
- a semente 1 foi declarada antes de medir. Escolher a melhor semente pela régua seria
  sobreajustar a ela, o mesmo motivo da decisão 0008;
- o `gerado_por` do JSON passa a ter `leitor`, e `modelo` aponta para os pesos usados.
- **atualização (2026-10-15)**: os pesos passam a ser `artefatos/detector_tab_final_s1_ger/`,
  a mesma receita com o gerador de pausa entre cordas e cinza (ver `ESTADO.md`, fase 8).

## Consequências

- **O X (nota abafada) muda de classe.** No leitor de glifos ele saía em `nao_notas` como
  `classe: "tecnica"`, com top-1 `"15"` no `simbolo_cru`. No leitor `rede` ele sai em
  `nao_notas` como **`classe: "x"`**, sem `simbolo_cru`. Isso responde ao pedido 9 da decisão
  2004 ("dar ao X classe própria"). Ver o aviso à trilha áudio abaixo.
- **`tecnica` da nota passa a vir preenchida** quando a rede vê alguma técnica: `h`, `p`,
  `/`, `\`, `harm`, `lig`, `bend`, `vib`, `orn` ou `enfeite`, várias unidas por `+`.
  **Não está validada**: o gabarito guarda técnica só por região, não por nota. Até haver
  métrica, trate o campo como pista, não como dado.
- **Sem `simbolo_cru` no leitor `rede`.** A rede não recorta glifos. O símbolo que ela não
  classifica como nota não aparece em `nao_notas`; só o X aparece. Isso é perda de
  informação em relação ao leitor de glifos (regra "símbolo não se descarta"). Quem precisar
  do recorte cru roda `--leitor glifos`. É dívida registrada.
- As barlines vêm direto da grade (`grade.barlines_x`), as mesmas que o leitor de glifos usa.
- A métrica oficial de 72 glifos (`tab.avaliar`) mede o classificador de glifos e não muda.
  A régua do leitor `rede` é o `tab.avaliar_video` nos 8 gabaritos.

## Aviso à trilha áudio (para o dono repassar)

> A partir do commit desta decisão, o produto (`tab.video` / `tab.transcrever`) usa por
> padrão o leitor `rede`. Para vocês, muda uma coisa: **o X do rasgueado deixa de sair como
> `nao_notas` de classe `tecnica` com top-1 `"15"`, e passa a sair como `nao_notas` de
> classe `"x"`**, sem `simbolo_cru`. Hoje `colunas_abafadas` (em `tab/audio_alinhar.py`) não
> acharia nenhuma coluna abafada num JSON novo. Sugestão: contar como abafado o glifo com
> `classe == "x"`, ou, enquanto isso, o glifo com top-1 `TOP1_ABAFADA` (mantém os JSONs
> antigos). Para gerar JSON no formato antigo, use `--leitor glifos`. As notas também mudam:
> revocação 0,83 → 0,95 nos 8 gabaritos, o que deve aumentar as colunas que o alinhador casa.
