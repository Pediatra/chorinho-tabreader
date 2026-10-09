# Resumo do projeto — pausa em 65 rodadas

**Número oficial: 0,892** de acerto no gabarito real (média de **3 sementes**: 0,844 / 0,906 / 0,927),
sobre **96 glifos rotulados à mão em 4 canais**. Melhor execução: **0,927**.

| canal | acerto | observação |
| --- | --- | --- |
| iwaki (tema escuro) | 25–27 de 27 | |
| sky guitar | 14–15 de 15 | |
| **raman korshun** (slides, lixo) | **17 de 24**, igual nas 3 sementes | **17/17 nos algarismos**; os 7 restantes são rótulos `junk` |
| paolo d'angelo | 25–30 de 30 | |

## Decisão de modelo

Não existe modelo aberto pronto para tablatura. **GOT-OCR2.0 (580 M) acertou 0 de 15** algarismos numa
linha com gabarito verificado. Arquitetura: **geometria determinística + classificador de ~74 mil
parâmetros**, treinado **só em dado sintético**.

## Os anexos do JSON

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa) | 0,892; corda, coluna e compasso robustos |
| **técnica** | classe treinada e estável; **sem ganho de acerto** (o modelo já lê algarismo com slide) |
| **tempo** | **dois mecanismos**, um medido em cada caso |
| **partitura** | **fora do escopo** desta cadeia — exige OMR próprio |

### Tempo — o marcador varia por canal

| mecanismo | canal | resultado |
| --- | --- | --- |
| faixa vertical que passa | `skyguitar` | 1 nota/s, desvio **0,16 s** |
| algarismo fica laranja (cumulativo) | `cifra club` | **41/41 onsets**, 8 ataques, intervalo 1,80 s |
| sem marcador | parte do acervo | tempo teria de vir de áudio ou manual |

O JSON **declara o mecanismo**. No marcador por cor mede-se o **onset**, não a duração.

## Acervo

3.781 vídeos, 190 GB, 12 canais. Amostra de 319: **96 % com tablatura**. **44 % não decodificam no
OpenCV** (AV1) — só com fallback por `ffmpeg`; sem isso quase metade passaria em branco.

## Geometria

5 famílias de renderização; 163/163 linhas nos recortes. Duas descobertas destravaram canais:
**máscara de tinta CLARA** (painel escuro) e **uniformidade de fundo** para achar o painel — e
**rejeitar o violão**, cujo braço tem 6 cordas e engana o detector.

## O que funcionou (medido)

| mudança | efeito |
| --- | --- |
| tokenização (juntar componentes) | 0,70 → 0,85 em canal novo |
| tamanho de fonte variável no gerador | 0,805 → 0,851 e estabilidade |
| **rejeição por assinatura de lixo** | `raman` 12 → 17/24; média 0,854 → **0,892** |

## O que foi tentado e falhou (registrado para não repetir)

| tentativa | efeito |
| --- | --- |
| regra de altura no extrator | 0 |
| regra de orientação no extrator | 0 |
| trocar arco por barra no gerador | −0,166 (revertida) |
| relabelar por proxy geométrico (`partes>=2`) | −0,1 (revertida, 2×) |
| classe `tecnica` como ganho de acerto | 0 (só estabilidade) |

## Lições (custaram rodadas)

1. **Semente fixa + 3 execuções** — sem isso o mesmo código dava 0,729 e 0,854, e eu reportei ruído.
2. **Medir a amostra antes de gastar o treino** (evitou 3 retreinos inúteis).
3. **O gargalo é cobertura do gerador, não regra de visão** — medido 6 vezes.
4. **Olhar o quadro antes de teorizar** — duas vezes medi o violão achando que era a tablatura.
5. **Conferir o significado do número** — "323 notas com tempo" eram 3 instantes.
6. **Não corrigir rótulo por proxy geométrico** — falhou 2×; ler o token acerta.

## Ferramentas e artefatos

`tools/`: `tabseg`, `cursor`, `inventario`, `ouro`, `sintetico`, `reconhecer`, `transcrever`,
`avaliar`. `gold/gabarito.json` (96 glifos, 4 canais). `saida/`: `skyguitar_linha01.json`,
`cifra_abanda.json`, `rollout/`. **~35 documentos em `docs/`** com todas as medições.

## Próximo passo

1. **ampliar o gabarito** para casas 8–24 — é o que limita a medição;
2. **rodar em escala** com a decisão por vídeo (a assinatura é uma contagem por quadro);
3. representar **`ligada` (`(6)`)** no JSON — categoria achada na leitura da rodada 62;
4. **aferir a casa** dos canais fora do gabarito (`cifra club` tem corda e tempo, não casa);
5. **medir a pegada da regra de rejeição** no acervo (medição iniciada e interrompida).

## Ressalvas

96 glifos, 4 canais, **casas 0–7**; aferição glifo a glifo, não da música inteira; **tab ASCII** e
**partitura** exigem leitor próprio; a casa dos canais fora do gabarito **não foi aferida**.
