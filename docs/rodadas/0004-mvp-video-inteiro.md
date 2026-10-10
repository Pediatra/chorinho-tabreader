# Rodada 0004: MVP, um vídeo inteiro

Data: 2026-10-10. HEAD medido: `6dda9580` (árvore com os arquivos de outro agente
não commitados em `data/gold/presenca_quadros.json` e `tests/test_presenca_aval.py`, que não entram aqui).

## Pergunta

Um vídeo inteiro do `sky guitar` sai do pipeline como JSON v1 correto (corda, casa, coluna,
compasso, técnica, tempo), sem nota inventada, e o pacote fecha o MARCO MVP do plano
(`docs/guias/plano-do-produto.md`, Fase 6)?

## Comando e tempo

```
python -m tab.transcrever "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4" --json data/saida/produto/mvp.json
```

Vídeo inteiro, um comando, dentro do container (podman). **Tempo de execução: 611 s (10 min 11 s).**
Saída: 13 telas, 22 exibições, 763 entradas de nota (485 notas distintas), 47 não-notas, 753 notas com
`t_ini`, 637 instantes distintos, `esquema: ok`.

## Critérios do MARCO MVP

| critério | meta | medido | situação |
| --- | --- | --- | --- |
| JSON completo do vídeo inteiro, num comando, `esquema.validar` ok (CA-1) | ok | ok, 13 telas, 22 exibições | cumprido |
| precisão de notas (notas entregues casadas com o ouro) (CA-3) | 1,00 | 485/485 = 1,000 | cumprido |
| inventadas (CA-6) | 0 | 0 | cumprido |
| revocação (CA-5) | ≥ 0,98 | 485/491 = 0,988 | cumprido |
| casa nas notas casadas (CA-3, casa+corda) | ≥ 0,99 | 483/485 = 0,996 | cumprido |
| estado de tempo (CA-6) | ≥ 0,95 (39/40) | 39/40 = 0,975 (acerto 38, 1 quadro antes 1, erro 1) | cumprido |
| tempo falso (CA-6) | 0 | 0 | cumprido |
| `tab.avaliar` oficial 1/2/3 (CA-8) | ≥ referência 66/71/68 | 66/72, 71/72, 68/72 | cumprido |
| `make gate` (lint + format + testes) | exit 0 | `ruff check .` ok; `ruff format --check .` 77 arquivos; `pytest tests/` 317 passed, 3 deselected | cumprido |
| folha de conferência (12 instantes, semente 0) | caixa sobre a faixa, casas batendo com o quadro | 12/12 (ver abaixo) | conferido pelo agente; **dono não olhou** |
| MusicXML abre e parseia | xml válido, notas | xml válido (`score-partwise`), 485 `<note>` = 485 notas distintas | cumprido |
| aprovação do dono por escrito (CA-10) | sim | aprovado em 2026-10-10 (frase abaixo) | cumprido |

Régua: `tab.avaliar_video` contra `data/gold/ouro_video/retrato_brasileiro_v2.json`, fps 29,97003
(lido por `ffprobe`, 30000/1001). Relatório: `data/saida/produto/avaliacao_mvp.json`.

### Folha de conferência (12 instantes, semente 0)

Olhei `data/saida/produto/conferencia_mvp.png` ampliada em duas metades. Nos 12 instantes a
caixa verde está sobre a faixa azul do marcador, e a casa lida no quadro bate com o "casas lidas"
da folha: t=271,738 c5=2; 392,392 c3=0; 419,786 c1=2; 449,783 c3=4; 486,953 c3=3; 505,238 c1=4;
518,385 c3=0; 529,362 c1=2; 567,801 c2=0; 573,773 c1=0 e c6=0; 590,623 c4=0; 640,273 c2=0.
A leitura é de imagem reduzida; o dígito dentro da caixa às vezes fica sob o traço verde, e nesses
casos conferi pelo número azul da faixa. Dois dígitos verdes fora da coluna marcada (instantes
518,385 e 567,801) não entendi o significado e não os verifiquei contra o vídeo.

## Notas perdidas e casas erradas (régua, por tela do ouro)

Seis notas do ouro não aparecem no JSON (perdidas):

| tela | corda | casa do ouro | x do ouro |
| --- | --- | --- | --- |
| 2 | 3 | 0 | 755,8 |
| 2 | 4 | 0 | 756,6 |
| 3 | 3 | 1 | 1245,5 |
| 5 | 4 | 2 | 1309,5 |
| 9 | 4 | 1 | 958,5 |
| 12 | 4 | 2 | 1264,5 |

Duas casas erradas nas notas casadas:

| tela | corda | x | ouro | previsto |
| --- | --- | --- | --- | --- |
| 4 | 5 | 1317,5 | 6 | 5 |
| 11 | 6 | 439,5 | 0 | 2 |

Não examinei a causa de cada uma. Não é objetivo desta rodada.

## Instante de tempo errado: t = 672 s

Único instante com erro (`erro: 1`). O ouro marca a coluna x 1760,2 da tela 13 em t = 672 s, e
o marcador some de 668 a 673 s. **Causa**: no JSON não há nenhuma nota da tela 13 perto de x 1760,
então o instante não tem coluna para casar. O próprio ouro também não lista nota da tela 13 nessa
faixa de x (só a coluna de t = 654 s, em x 372,6). Logo o erro está no par ouro/JSON, não no
rótulo de tempo: ou falta a nota no ouro e no JSON ao mesmo tempo, ou o instante aponta para uma
coluna sem nota. **Não resolvi**; fica para o dono confirmar.

## Decisões do dono nesta rodada

- **Régua de 1 quadro**: o rótulo de tempo pode estar até 1 quadro antes do primeiro quadro em que a
  coluna aparece (tolerância `quadros_antes = 1`, 0,033 s). Não foi afrouxada para 2 quadros.
- **Ouro t = 500 s**: corrigido pelo dono (coluna do `0` da corda 2; commit `00d87c87`). Com ele, o
  estado fica 39/40 e o tempo falso fica 0.
- **Arcos removidos**: arco de ligadura não vira nota (Fase 4; `inventadas` 21 para 1 e depois para 0).
- **Notas distintas na régua**: cada nota (tela, coluna, corda) conta uma vez. Entradas repetidas por
  passagem e exibição não entram duas vezes. Por isso 763 entradas no JSON viram 485 notas distintas,
  e o MusicXML também tem 485.

## Limites

- Medido em **um** vídeo (`retrato brasileiro`, 13 telas, 491 notas no ouro) e **um** canal
  (`sky guitar`). Não há prova de generalização para outros vídeos ou canais.
- A **casa** está validada só aqui: nos 485 casados, em casas 0 a 7 do ouro. Nos outros canais não há medição.
- A métrica é de **notas e tempo**, não cobre técnica nem símbolo (técnica do JSON vem `null` nas 763
  entradas deste vídeo).
- O tempo tem 1 erro (t = 672 s, instante sem nota). O estado 39/40 passa com o instante em 1 quadro.

## Artefatos

- `data/saida/produto/mvp.json` (JSON v1 do vídeo inteiro)
- `data/saida/produto/transcrever_mvp.log` (log do comando, com o tempo)
- `data/saida/produto/avaliacao_mvp.json` (régua)
- `data/saida/produto/diag_perdidas.py` (lista de perdidas e casas erradas, usa `tab.avaliar_video`)
- `data/saida/produto/conferencia_mvp.png` (folha de 12, semente 0); ampliações em
  `conferencia_mvp_zoom_a.png` e `conferencia_mvp_zoom_b.png`
- `data/saida/produto/mvp.musicxml` (MusicXML a partir do `mvp.json`, `tab.musicxml`)
- `artefatos/oficial_1/`, `artefatos/oficial_2/`, `artefatos/oficial_3/` (modelos da régua oficial)

## Aprovação do dono (CA-10): APROVADO

Data: 2026-10-10. Frase do dono no chat:

> "esse mvp ja ta aprovadissimo, só vou passando uns errinhos que to vendo manualmente"

Pacote aprovado: commit `0a3fdcda` (rodada 0004) e MusicXML corrigido `c15cd72e`.
Números do pacote: precisão 485/485 (0 inventadas), revocação 485/491, casa 483/485,
estado 39/40, tempo falso 0, `tab.avaliar` 66/71/68.

### Erros apontados pelo dono após a aprovação

Registrados para correção posterior; não invalidam a aprovação do pacote.

- (a) **6 lido como 5** no compasso 15 (tela 4, corda 5, x ≈ 1317). Já conhecido (linha
  "tela 4 / corda 5 / 6 do ouro / 5 previsto" acima): a alça do 6 sai partida em 2 componentes.
- (b) **Os dois 0 do acorde 3/0/0/3 da tela 2** (cordas 3 e 4, x ≈ 755,8 e 756,6): notas perdidas.
  O classificador chama esses dois dígitos de harmônico.
- (c) **Mordente 2⌒3⌒2 não interpretado como técnica.** Os símbolos ficam guardados em
  `nao_notas` com o glifo cru; a interpretação fica para o mapa de símbolos por canal
  (`configs/simbolos.yaml`).
- (d) **Tempo falso na moldura verde da ilustração de mãos** (tela 1, t = 239,4 s). Em conserto.
