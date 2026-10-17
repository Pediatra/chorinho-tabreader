# 3102 — F0.2: troca do compasso pelo homr, julgada pela tab

Frente 0 (régua por compasso, troca do homr e tempo pelo par), item F0.2 de
`docs/pesquisa/partitura-frentes.md`, seção 7. Briefing da onda 1
(`docs/pesquisa/partitura-onda1-briefings.md`).

**Medida, sem limiar.** A regra é a 3025 (`trocar_compassos_pelo_homr`, `RAZAO_TROCA_HOMR` =
2,0, importados de `tab.partitura_pareamento`; a razão não muda). A regra é aplicada **sem a
tab**; o juízo é **com a tab** (`contar` no modo `exato`). Feita na cópia isolada
`chorinho-partitura-env/repo`. Módulo: `tab/partitura_regua_troca.py`. Saída:
`data/saida/part_frentes/f0_regua/troca.json`.

## Conjuntos (definidos antes de medir)

- **R01–R12** (`recortes_margem/indice.json`, origem `ouro`): 12 recortes em 3 vídeos.
  R01–R04 pablo romé (greensleeves), R05–R07 guitar dell'arte (south american),
  R08–R12 robert lunn = Gymnopédie, telas 1, 3, 5, 7 e 9.
- **7 telas novas da Gymnopédie**: telas 2, 4, 6, 8, 10, 11 e 12 (pautas T02, T04, T06,
  T08, T10, T11 e T12 de `video/<gymnopedie>/<stem>.partitura.json`).
- Leituras: Audiveris `x2_margem_herdada` (`saida.musicxml`) para as notas e `x2_margem`
  (`entrada.omr`) para o x; homr `nativo` (`saida.musicxml`) para a troca. Escala 2,0; `x0` =
  `caixa_recorte[0]`.
- Gabarito de tab: `data/gold/ouro_video/` (só leitura), pela tela de cada recorte.

## Referência e métricas

- **Referência antes da regra** = só Audiveris. Em R01–R12 tem de dar **`[546, 496, 9, 41,
  3]`** (ordem: referência, certas, altura errada, faltando, inventada). Esse é o número de
  verificação, não a referência do juízo do 528.
- **Juízo depois da regra** = Audiveris com os compassos trocados pelo homr, contra a tab.
- **Unidade**: nota da tab, isto é, uma altura de um evento da tab, como `certas`,
  `altura_errada`, `faltando` e `inventada` do `contar` (modo `exato`, pelo `alinhar`). Uma
  nota da tab é **certa** se aparece na leitura, no par casado com o seu evento.
- **Consertada**: nota certa depois e não antes. **Quebrada**: certa antes e não depois.
  **Inventada nova** = inventadas depois − inventadas antes (contagem do `contar`).
- A referência de notas (`referencia`) é a mesma nos dois lados; não entra na conta.
- **Compasso trocado**: número do compasso do Audiveris trocado pelo homr.
- **Compasso que não troca**: número de compassos do Audiveris e do homr diferente (a regra
  não troca nada); conta-se à parte.
- **Figura**: só para as notas trocadas, comparar a figura do homr com a do Audiveris de
  mesma altura no mesmo compasso (a tab não vê figura). Conta-se quantas diferem.
- **Oitava**: altura errada de exatamente 12 semitons conta à parte (harmônico, rodada
  3013), sem mudar o número principal.
- Por recorte, por tela e por vídeo, com denominador. Reporte também **sem a Gymnopédie**
  (CA4).
- **Casos olhados**: 5 consertados e 5 quebrados, cada um com o caminho do `entrada.png` do
  recorte.

## Não entra nesta rodada

- A linha `E.` do CA1 (`compassos_homr.json`): o arquivo não está na cópia; a sessão principal
  mede os 2 itens válidos.

## Resultado

Execução: `python -m tab.partitura_regua_troca` na cópia; duas execuções dão o mesmo
`troca.json` (`cmp`). Lint: `ruff check` e `ruff format --check` passam.

**Antes (só Audiveris), CA1:** R01–R12 dá `[546, 496, 9, 41, 3]`, igual ao número de
verificação.

| conjunto | recortes | consertadas | quebradas | inventadas novas | saldo | compassos trocados | sem troca (contagem difere) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R01–R12 | 12 | 3 | 0 | 0 | +3 | 1 | 3 |
| 7 telas novas da Gymnopédie | 7 | 0 | 0 | 0 | 0 | 0 | 1 |
| sem Gymnopédie (R01–R07) | 7 | 0 | 0 | 0 | 0 | 0 | 3 |

- Por vídeo: pablo romé (R01–R04): 0 / 0 / 0. guitar dell'arte (R05–R07): 0 / 0 / 0, com
  3 recortes em que a contagem de compassos difere. robert lunn (R08–R12 e as 7 novas):
  +3 / 0 / 0. Todo o ganho está no R08, compasso `1`.
- Figura, nas notas trocadas (só R08, 4 notas do homr): 3 não acham altura igual no Audiveris
  do mesmo compasso; 1 acha e tem a mesma figura. Nenhuma figura diferente.
- Oitavas (harmônico): 0.
- Nenhum recorte falhou na leitura do homr.

**Leitura do resultado.** A regra quase não dispara: 1 compasso trocado em 19 recortes. O
ganho são 3 notas, em 1 recorte, de 1 vídeo. Não houve quebra nem inventada nova. Com isso o
critério da seção 7 ("levar ao dono se quebradas + inventadas passarem das consertadas") não
dispara. Mas n = 3 notas não dá para decidir nada. CA4 (ganho em pelo menos 2 vídeos) não
é atingido: só 1 vídeo ganha.

**Casos olhados.** Não dá para cumprir 5 consertados e 5 quebrados: há 3 consertadas e 0
quebradas. A página do R08 foi vista (`data/saida/partitura/p1/omr/audiveris/x2_margem/R08/
entrada.png`), mas não confirmei as 3 alturas consertadas (73, 76, 80) no recorte, porque a
imagem na resolução atual não deixa ler as notas com segurança. Visto em 2026-10-17 (`casos/` da frente 0): o acorde de três notas (C#5, E5, G#5, da
tab) está na imagem, no compasso 1 do R08. O Audiveris não leu o acorde; o homr leu. A
consertada é real. A soma de 5 consertadas e 5 quebradas não se fecha: há 3 consertadas e
0 quebradas, então o CA7 de F0.2 fica parcial.

**Correção de unidade (registro).** A primeira execução contou eventos da tab (acordes
inteiros), não notas. Isso foi detectado antes de qualquer juízo e corrigido para nota, que é
a unidade pedida pelo briefing e pelo `contar`. A saída citada acima é a corrigida. A conta
por evento deu consertadas 1 em R08, contra 3 notas pela unidade certa, por causa do acorde.

## Revisão da sessão principal (2026-10-17)

Rodado de novo no container, na `main`: a saída deu igual byte a byte à da cópia (`cmp`).
