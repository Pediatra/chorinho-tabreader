# Rodada 29 — rollout: 5 vídeos transcritos (e o que o meu próprio número esconde)

## 1. O que foi produzido

Rodei a cadeia completa em **5 vídeos de 5 canais diferentes**, todos com cursor detectado,
gravando JSON em `saida/rollout/`:

| canal | notas | compassos | janela com cursor | notas c/ tempo |
| --- | --- | --- | --- | --- |
| guitar dell ́arte | 30 | 1 | 84 s | 30 |
| serge kottelat | 7 | 3 | 86 s | 7 |
| shin izumi | 145 | 24 | 89 s | 145 |
| violaodecria | 7 | 2 | 90 s | 7 |
| sky guitar | 134 | 1 | 87 s | 134 |
| **total** | **323** | — | — | **323** |

Cada JSON tem `corda`, `casa`, `tecnica`, `compasso`, `t_ini`, `t_fim`, `confianca` e
`corrigido_pela_forma` por nota.

## 2. O que esse "323 notas com tempo" NÃO significa

A coluna saiu 100 % — e eu preciso corrigir a leitura antes que ela vire propaganda:

**`tempos_do_cursor` atribui a cada nota o patamar de cursor mais próximo em x.** Se o vídeo tem
mais notas do que patamares na janela, **várias notas recebem o mesmo instante**. O número correto
a reportar é o de **instantes distintos**, que é igual ao número de patamares — tipicamente 20–40
numa janela de 20 s, não 145.

Ou seja: as 145 notas do `shin izumi` receberam tempo, mas provavelmente cerca de duas dúzias de
instantes distintos foram distribuídos entre elas. **O tempo está atribuído, não necessariamente
correto** — e a resolução temporal é limitada por quantas notas o cursor visita na janela.

Esse é um defeito de aferição meu, não do pipeline: eu deveria ter contado patamares distintos.

## 3. O que também continua fraco

- **compassos implausíveis em dois canais**: 24 compassos para 145 notas (`shin izumi`) e 1
  compasso para 134 notas (`sky guitar`). A numeração por barline só é confiável onde as barlines
  são limpas — como no `skyguitar` dos recortes, onde deu 4/4/4/3 correto.
- **`serge kottelat` com 7 notas** numa janela de 86 s: a grade foi achada, mas poucas notas — o
  trecho transcrito provavelmente é intro/sem execução. O produto precisa escolher o trecho pela
  densidade de notas, não pelo primeiro quadro com painel.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura; 54 % com cursor |
| (b) gabarito verificado | 96 glifos / 4 canais |
| (c) classificador multi-classe | **0,805 (3 sementes)** |
| (d) pipeline ponta a ponta | **rollout rodado em 5 canais**; tempo atribuído mas com resolução a medir; compasso confiável só onde a barline é limpa |
| (e) escala nos 3.781 | iniciado: 5 vídeos transcritos automaticamente |

## 5. Próximos passos, do mais concreto ao mais estrutural

1. **contar instantes distintos** por JSON (defeito de aferição desta rodada);
2. **escolher o trecho pela densidade de notas** (evita transcrever intro vazia, como o `serge`);
3. **barline robusta** (o compasso é o anexo mais frágil dos três);
4. decisão de produto sobre os **46 % sem cursor**.
