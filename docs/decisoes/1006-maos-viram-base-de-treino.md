# 1006 — Mãos: a trilha grava as mãos de cada nota (base de treino), não adivinha a corda

**Data**: 2026-10-16. **Decisão do dono** (chat: "o que eu quero é apenas associar o
movimento das mãos com o gabarito da tablatura para salvar os padrões de movimento das mãos
(um dataset de treino)").

## Contexto

- Desde o M8 (rodada 1013), a trilha tentou tirar a **corda** de cada nota pela mão, com regras
  escritas à mão:
  - janela da mão esquerda;
  - pontas da direita;
  - custo aprendido;
  - timbre do áudio;
  - ligados.

  Nada passou nos critérios congelados (rodadas 1101–1170). A única janela que parecia ganhar
  reprovou fora da amostra (rodada 1014: 153 → 146 erros).
- Todo vídeo do acervo tem a tablatura na tela (dono). A tablatura é exatamente o que é tocado
  (dono). Ela já dá a corda e a casa de cada nota.
- O objetivo do dono, já registrado em `docs/guias/contexto-maos.md` §1: treinar no futuro um
  modelo que receba vídeo e áudio **sem** tablatura e devolva tablatura ou partitura. Para isso,
  a base precisa ligar cada nota do gabarito ao movimento das duas mãos, ao braço do violão e ao
  som.
- Preocupação do dono: o modelo de visão tem de ser muito preciso. Uma associação falsa entre
  movimento e nota contamina o treino.

## Opções

1. **Continuar as ondas** (mais regras para adivinhar a corda pela mão).
   - Contra: a tablatura da tela já dá a resposta, e nove testes não renderam.
2. **Encerrar a trilha das mãos** (proposta do coordenador, recusada pelo dono).
   - Contra: perde o objetivo final, que precisa das mãos como entrada do modelo.
3. **A trilha passa a construir a base**:
   - a tablatura é o rótulo;
   - as mãos, o braço e o som são a entrada;
   - cada associação é checada, e a taxa de associação falsa é medida pelo dono.

## Decisão

**Opção 3.** Plano em [`docs/guias/plano-dataset-maos.md`](../guias/plano-dataset-maos.md),
fases M10–M16:

1. M10 — esquema e regras;
2. M11 — braço quadro a quadro;
3. M12 — mãos quadro a quadro;
4. M13 — tempo do som por nota;
5. M14 — associação e auditoria;
6. M15 — piloto e rollout;
7. M16 — o modelo, depois.

## Consequências

- As ondas de regra para adivinhar a corda param. As rodadas 1013–1014 e 1101–1170 ficam como
  registro, com a tabela "não repetir".
- O D1 do M8 (88 % da corda do professor, só pela sequência de notas) vira linha de base do
  modelo futuro.
- Nada do que entra como **entrada** na base é calculado com o gabarito. A calibração do braço
  pela música (1006–1007) só serve para criar rótulos do detector do braço ou para validá-lo.
- A associação usa o tempo do **som** (`t_audio`, trilha do áudio), não o do marcador.
- Formato em arquivos irmãos (`chorinho/maos@1` + `.npz`), sem mudar o `chorinho/video@1`.
- O dono precisa de:
  - ~40 min para o gabarito do braço no tempo (30 quadros);
  - ~30–40 min por auditoria de 100 eventos (piloto, sky guitar, cada canal novo).
