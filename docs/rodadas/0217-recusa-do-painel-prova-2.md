# 0217 — A regra de recusa do painel, numa segunda prova

**Data**: 2026-10-24. **Trilha**: tablatura. **Estado**: pré-registro (nada medido na prova).

## A pergunta

A regra da 0216 passa nos três critérios em vídeos novos, com uma conferência que não deixa
painel errado passar como certo?

Na 0216, ela reprovou por pouco: 1,1 % das notas certas perdidas, para um teto de 1 %. Depois
da medida, 4 telas que a triagem chamou de certas se mostraram painéis errados. Com elas
corrigidas, a regra passa (0,72 %), mas uma correção feita depois de ver o resultado não
decide sozinha.

## A regra (a mesma da 0216, sem mudar nada)

```
painel == faixa fixa "topo" (0–400) ou "meio" (300–750) inteira, sem recorte
OU  n_notas / (largura / passo) <= 0,0916
```

## A prova (lacrada)

- **Amostra**:
  - 30 vídeos sorteados com `random.Random(17)` do `data/saida/tablatura/censo/censo_cache.jsonl`;
  - só os que têm `tablatura` verdadeiro, com no máximo 3 por canal;
  - as mesmas exclusões da 0216 (rollout `fora`, `raman korshun`, `campanitas`, r2021, r2017,
    `data/gold/ouro_video`, T8.2–T8.6, `cifra club` sem tab no `censo_v2`);
  - **e os 30 vídeos da 0216**.
- **Leitura**: o produto atual, em CPU (como na 0216).
- **Conferência do painel**, que precisa fechar antes de a regra ser aplicada:
  1. **dois Haiku fazem a triagem em separado**, sem ver um o resultado do outro, com o critério
     "o retângulo verde está sobre a tablatura da tela?";
  2. a sessão principal confere **toda tela que um dos dois não chamou de certa**;
  3. a sessão principal confere 1 folha em cada 10 das outras (`Random(17)`).
- **Depois de aplicar a regra**, a sessão principal confere **toda tela que ela recusar**. Um
  rótulo que mudar nessa etapa entra na conta e fica registrado à parte, com o número antes e
  depois. Assim o custo é medido com todas as telas recusadas conferidas.

## O critério (o mesmo da 0216)

1. **Custo**:
   - certas recusadas ≤ **3 %** das certas;
   - notas certas perdidas ≤ **1 %**.
2. **Pega**: recusadas ≥ **60 %** das erradas.

- **Os dois passam** → a regra entra no produto (`tab.tablatura.produto.video`):
  - a tela recusada fica com `recusado` e o motivo (`painel_faixa_fixa` ou
    `painel_poucas_notas`);
  - ela ganha teste no gate.
- **O custo passa, a pega não** → entra mesmo assim (não piora nada); o que escapou vira rodada.
- **O custo reprova** → não entra, e vai para "não repetir".
