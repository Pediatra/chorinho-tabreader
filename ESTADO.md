# ESTADO.md — número oficial, o que está medido e o que falta

Documento de entrada do projeto. **Todo número aqui é média de ≥3 sementes**, nunca
execução única — sem isso o mesmo código já deu 0,729 e 0,854. O histórico completo
das 65 rodadas está em [`docs/HISTORICO.md`](docs/HISTORICO.md).

## Número oficial

**0,892 de acerto no gabarito real** — média de 3 sementes (**0,844 / 0,906 / 0,927**),
sobre **96 glifos rotulados à mão em 4 canais, casas 0–7**.
Sobre os rótulos **alcançáveis** (excluindo os 7 `junk` do `raman`): **0,955**.

| canal | acerto | observação |
| --- | --- | --- |
| iwaki (tema escuro) | **27/27** | estável nas 3 sementes |
| sky guitar | **15/15** | estável nas 3 sementes |
| **raman korshun** (slides, lixo) | 17/24 | **17/17 nos algarismos**; os 7 restantes são `junk` |
| paolo d'angelo | 26–30/30 | passo 16 px, o painel mais denso |

Reproduzido no container em 2026-10-08 após a reestruturação: **0,927**
(`docker compose run --rm chorinho python -m tab.avaliar`).

## O que o JSON entrega

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, coluna, compasso) | 0,892; corda e coluna robustas |
| **técnica** | classe treinada e estável; **sem ganho de acerto** (o modelo já lê o algarismo com o slide junto) |
| **tempo** | **dois mecanismos**, um medido em cada caso (abaixo) |
| **partitura** (5 linhas) | **fora** desta cadeia — exige OMR próprio |

### Tempo — o marcador VARIA por canal

| mecanismo | canal verificado | resultado |
| --- | --- | --- |
| **faixa vertical** que passa | `sky guitar` | 1 nota/s, desvio **0,16 s** (corrigível para ~33 ms) |
| **algarismo fica laranja** (cumulativo) | `cifra club` | **41/41 onsets**, 8 instantes distintos, intervalo mediano 1,80 s |
| **sem marcador** | ~46% dos vídeos | tempo teria de vir de áudio ou de marcação manual |

O JSON **declara o mecanismo**. No marcador por cor mede-se o **onset**, não a
duração: `t_fim` é o **próximo onset** — o algarismo continua laranja depois de tocado.

## Geometria — o que destravou canais

- **painel claro**: máscara de tinta escura. **painel escuro** (estilo `cifra club`):
  máscara de tinta **clara** (`contraste_claro_k21_d12`);
- **uniformidade de fundo** para achar o painel **e rejeitar o violão** — o braço tem
  6 cordas e engana o detector (medi: caixa de 149 px, matiz 16, era o corpo do violão);
- 5 famílias de renderização tratadas; passo entre cordas de **14 a 45 px**;
- algarismos de **0,38 passo** (cifra club) a 0,6 passo (sky guitar).

## O que funcionou (medido)

| mudança | efeito |
| --- | --- |
| tokenização (juntar componentes da mesma corda) | 0,70 → 0,85 em canal novo; treino 0,58 → 0,985 |
| tamanho de fonte variável no gerador | 0,805 → 0,851 e estabilidade |
| **rejeição de lixo por assinatura do vídeo** | `raman` 12 → 17/24; média 0,854 → **0,892** |
| extração por faixa de corda | 6.882 → 11.594 glifos (os ~4.700 a mais eram acordes fundidos) |
| fallback `ffmpeg` para AV1 | **140 de 319** quadros só eram legíveis por ele |

## O que foi tentado e falhou (não repetir)

| tentativa | efeito |
| --- | --- |
| regra de altura no extrator | 0 (0,818 → 0,818) |
| regra de orientação no extrator | 0 (0,818 → 0,818) |
| trocar arco por barra no gerador | **−0,166** (revertida) |
| relabelar gabarito por proxy geométrico (`partes>=2`) | **−0,1**, duas vezes (revertida) |
| classe `junk` no treino | troca entre canais, não ganho (0,805 = 0,805) |
| `lim_x` por margem de barline | apagaria **506 glifos (4,3%)** em 60 linhas |

## Lições metodológicas (custaram rodadas)

1. **Semente fixa + ≥3 execuções**, reportando média e amplitude.
2. **Meça a amostra antes de gastar treino.**
3. **Confira o significado do número**: "323 notas com tempo" eram **3 instantes**.
4. **Olhe o quadro antes de teorizar** — duas vezes medi o violão achando que era a tablatura.
5. **Rótulo de gabarito só por leitura visual**, nunca por proxy geométrico.
6. **O gargalo é cobertura do gerador, não regra de visão** — medido 6 vezes.

## Ferramentas e artefatos

| caminho | o que é |
| --- | --- |
| `tab/tabseg.py` | grade: 6 cordas, barlines, tokens, 5 famílias + painel escuro |
| `tab/cursor.py` | marcador por faixa (x(t), saltos, sistemas) |
| `tab/sintetico.py` | gerador sintético + treino (`--seed`) |
| `tab/reconhecer.py` | linha → corda, casa, técnica, compasso, tempo |
| `tab/transcrever.py` | vídeo → JSON (painel, grade, marcador, tempo) |
| `tab/avaliar.py` | aferição padronizada — é o número oficial |
| `tab/inventario.py` | varre o acervo (família, painel, marcador) + fallback ffmpeg |
| `tab/caminhos.py` | acervo, gabarito, artefatos: **caminho em um lugar só** |
| `data/gold/gabarito.json` | 96 glifos rotulados à mão, 4 canais |
| `artefatos/` | pesos treinados (**nunca** em `/tmp`) |
| `configs/` | mapa por canal e mapa de símbolos (**a criar**) |

## Próximo passo

1. **símbolos e técnicas por canal** — hoje o extrator **descarta** o símbolo em volta
   do número. Decisão nova: **guardar o glifo cru** e classificar depois, com mapa por
   canal (`configs/simbolos.yaml`);
2. **ampliar o gabarito** para casas 8–24 e mais canais — é o que limita a medição;
3. **tempo onde não há marcador** (~46% do acervo) via áudio;
4. **rodar em escala** nos 3.781 vídeos, com decisão por vídeo;
5. representar **nota ligada `(6)`** e conferir a semântica de cada símbolo por canal.

## Ressalvas (não prometa além disto)

- 96 glifos, 4 canais, **casas 0–7**; aferição **glifo a glifo**, não da música inteira;
- a **casa** dos canais fora do gabarito (ex.: `cifra club`) **não foi aferida** — há
  corda e tempo, casa não;
- **tab ASCII** (Ultimate Guitar) e **partitura de 5 linhas** exigem leitor próprio;
- a métrica **não** cobre técnica nem símbolo: eles são gravados, não aferidos.
