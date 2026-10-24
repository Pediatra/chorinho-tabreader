# Tarefa delegada — Três leituras erradas do leitor `rede` (pedidos 13, 14 e 15 da decisão 2004)

**Data**: 2026-10-23. **Trilha**: **tablatura** (rodadas `0NNN`). **Quem escreveu**: a sessão das
mãos, que não mexe nos arquivos da tablatura; o dono leva este documento a um agente que
trabalha **como a trilha tablatura**. **Para quem**: um agente que **não** viu a conversa. Se
algo não estiver aqui, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 2 dias de trabalho, em duas etapas com parada no meio (seção 6).

---

## 1. Por que isto importa mais que quase tudo

- O projeto monta uma base de dados de violão para treinar um modelo que recebe vídeo e som e
  devolve a tablatura.
- O **rótulo** de cada nota (corda e casa) vem da **leitura da tablatura da tela**. É a
  trilha tablatura que faz essa leitura, com o leitor `rede` (`tab/tablatura/leitura/
  detector_tab.py`, treinado com `tab/tablatura/treino/sintetico_sistema.py`).
- Uma casa lida errada vira **rótulo errado** na base, e rótulo errado é o pior erro possível:
  o modelo aprende a coisa errada com confiança (`AGENTS.md`, seção 1, princípio 2: "falso
  positivo é o pior erro").
- O leitor é bom: precisão 0,974, revocação 0,949 e casa 0,987 nos 8 vídeos com gabarito do dono
  (2.689 notas, validação cruzada por vídeo). Mas a trilha do áudio achou três tipos de erro
  **fora** desses 8 vídeos, e eles afirmam casa errada sem avisar.

## 2. Os três erros (copiados da decisão 2004; abra as imagens)

| pedido | o erro | onde | imagem |
| --- | --- | --- | --- |
| **13** | dois algarismos ligados por um tracinho ("2·3", "2·4") viram **um** número (23, 24): casa errada afirmada. O vídeo tem 32 notas com casa ≥ 13 no `rede` (24 no leitor antigo de glifos); nem todas foram olhadas | kimny's guitar, *bach prelude* (passo 20,6; telas 1, 3, 5, 6) | `data/saida/audio/r2017/quadros/bach_t5_zoom.png` |
| **14** | o "10" da corda 1 é **perdido**, e uma nota pequena de ornamento (o 10 do ligado H) é lida como coluna | shin izumi, *room 335*, tela 20 (x ≈ 365 e 595 perdidos; x ≈ 455 e 958 são ornamento) | `data/saida/audio/r2017/quadros/room335_t20_a.png` e `_b.png` |
| **15** | a ponta da **seta de rasgueado** é lida como "4" na corda 1 (3 de 6 setas da tela) | transcriptor, *charagua*, tela 6 (x ≈ 392, 743 e 1452) | `data/saida/audio/r2020/charagua_tela3_setas.png` |

Fonte completa: `docs/decisoes/2004-pedidos-de-leitura-a-trilha-tablatura.md` (leia a tabela
inteira e a seção "Como medir o efeito").

## 3. Leia antes de qualquer coisa

1. `AGENTS.md` inteiro. Em especial: seção 6 (como uma rodada funciona: **pré-registro antes de
   medir**), seção 7 (regras 1, 2, 5, 8 e 9: ≥ 3 sementes, olhar a entrada real do modelo, o
   gargalo histórico é a **cobertura do gerador**, não regra de visão), seção 8 (o gabarito do
   dono é contrato), seção 9 (git e gate).
2. `docs/estado/tablatura.md`, a seção "2026-10-14 — detector neural de sistema (N1–N4)" e o
   que vier depois dela.
3. `docs/guias/plano-rotulo-tablatura.md`.
4. `docs/decisoes/2004-pedidos-de-leitura-a-trilha-tablatura.md`.

## 4. Passo 0: isto já foi feito?

A trilha tablatura pode já estar mexendo nisso: em 2026-10-23 havia mudanças não commitadas em
`tab/tablatura/treino/sintetico_sistema.py`.

- Rode `host-spawn -no-pty git log --oneline -20 -- tab/tablatura/` e
  `host-spawn -no-pty git status --short tab/tablatura/`.
- Procure "13", "14", "15", "tracinho", "seta" e "ornamento" em `docs/estado/tablatura.md` e
  em `docs/rodadas/0*.md`.
- **Se outra sessão estiver mexendo nesses arquivos agora** (mudança não commitada que não é
  sua), **pare** e pergunte ao dono antes de editar qualquer coisa: duas sessões no mesmo
  arquivo se atropelam.
- Se os três pedidos já tiverem rodada com resultado, escreva isso no relatório e pare.

## 5. Ambiente

- O agente roda num distrobox **sem** `git` e `podman`: rode-os no host com
  `host-spawn -no-pty ...`.
- Todo Python roda em container (`AGENTS.md`, seção 4). Modelo:

  ```bash
  cd /var/home/gabriel/Projects/chorinho-dataset
  host-spawn -no-pty podman run --rm --security-opt label=disable \
      --device nvidia.com/gpu=all --shm-size=2g \
      -v "$PWD":/app -v /run/media/gabriel/3014CD4714CD1130/chorinho:/acervo:ro \
      -w /app -e PYTHONPATH=/app docker.io/library/chorinho:dev python -m ...
  ```

- GPU: sempre dentro de `tab.comum.gpu.trava_gpu("tablatura", "estimativa")`. Ela divide a GPU
  pela memória (≥ 3 GB livres). Até ~05h30 de 2026-10-24 a trilha mãos usa a GPU; treino longo,
  combine o horário com o dono.
- O acervo é **somente leitura**. Nunca escreva em `data/gold/`.

## 6. O que fazer: duas etapas, com parada entre elas

### Etapa A — o tamanho do problema (sem treinar nada; ~meio dia)

1. Para cada pedido, **olhe as imagens** citadas e confirme o erro com os seus olhos. Se não
   conseguir ver o erro, escreva isso e não siga com aquele pedido.
2. **Conte** quantas notas de cada tipo de erro existem:
   - nos 3 vídeos citados, tela por tela (pedido 13: toda nota com casa ≥ 13 no *bach prelude*
     — olhe cada uma no quadro; pedido 14: todos os "10" na corda 1 do *room 335*; pedido 15:
     toda seta de rasgueado no *charagua*);
   - nos 8 vídeos com gabarito do dono (`data/gold/ouro_video/`): quantas vezes o padrão
     aparece na tela (tracinho entre algarismos, "10" na corda 1, nota de ornamento, seta).
3. **Pare e entregue** um relatório parcial (`relatorio_etapa_a.md`, formato na seção 9) com as
   contagens. **O dono decide** se a etapa B vale a pena.

### Etapa B — o conserto (só com o OK do dono)

1. **Pré-registro** num documento de rodada novo da trilha tablatura (`docs/rodadas/0NNN-...md`,
   com o próximo número livre da faixa `0NNN`), commitado **antes** de treinar: a pergunta, o
   que muda, a amostra, os critérios da seção 7 e o que fazer em cada resultado.
2. O caminho preferido é o **gerador** (`sintetico_sistema.py`): ensinar a rede com exemplos
   sintéticos do padrão que falta (algarismos com tracinho, "10" na corda 1, ornamento pequeno,
   seta de rasgueado como "não nota"). Esse foi o caminho que funcionou nas vezes anteriores;
   regras geométricas por cima da rede deram 0 ou piora em 6 tentativas (`AGENTS.md`, seção 7,
   regra 9).
3. Antes de treinar, **desenhe** exemplos do gerador novo e confira que o padrão aparece como
   na tela (regra 2: "meça a amostra antes de gastar treino").
4. Treine com **3 sementes** e reporte média e amplitude (regra 1).

## 7. Critérios de aceitação (etapa B)

| critério | o que precisa |
| --- | --- |
| **1. Conserta** | nas telas citadas dos 3 vídeos, os casos contados na etapa A saem certos em ≥ 80 % (ex.: "2·3" lido como 2 e 3, não 23), na média das 3 sementes |
| **2. Não inventa** | as setas de rasgueado do *charagua* não viram nota (0 em 6, na tela 6) e o ornamento não vira coluna |
| **3. Não piora o resto** | nos 8 vídeos com gabarito, pela mesma medida da tabela N1–N4 (validação cruzada por vídeo): precisão, revocação e casa **não caem mais que 0,002** cada, na média das 3 sementes |

- Se 1 e 2 passam e 3 falha: não adotar; relatar onde piorou (vídeo e tela).
- O leitor do produto só muda com decisão do dono: trocar o leitor muda colunas que o áudio
  usa (o X do rasgueado, "15").

## 8. Como não se perder (regras contra loop)

- **Não treine na etapa A.** A etapa A é olhar e contar.
- **Pare na fronteira A → B** e espere o dono.
- **No máximo 2 versões do gerador** na etapa B. Se a 2ª não passar no critério 1, pare e
  entregue o que aprendeu.
- **Um erro igual duas vezes** (mesma mensagem): pare, escreva no relatório, entregue.
- **Nunca** mude limiar ou critério depois de ver o resultado. Se achar que o critério está
  errado, escreva por quê e pare.
- **Não edite** arquivos das trilhas mãos, áudio ou partitura, nem `data/gold/`.
- Gate antes de todo commit, julgado pelo código de saída (`AGENTS.md`, seção 9). `git add`
  só por nome.

## 9. Quando parar e o que entregar

Pare quando:
- a etapa A terminar (sempre, para o dono decidir); **ou**
- a etapa B cumprir a seção 7, ou bater a seção 8; **ou**
- passar o tempo máximo.

Relatório, em português simples, na pasta de saída que você criar em `data/saida/tablatura/`
(com um `LEIAME.json`, `AGENTS.md` seção 10):

```text
# Pedidos 13–15 — relatório (etapa A ou B)
## Resposta curta (3 linhas)
## O que vi nas imagens (por pedido)
## Contagens (por pedido, por vídeo, "X de Y")
## (etapa B) Critérios 1–3 com os números, 3 sementes, média e amplitude
## Commits (hash e mensagem)
## O que não deu certo / próximos passos
```
