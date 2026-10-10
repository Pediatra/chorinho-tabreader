# 0005 — Casa de dois algarismos: o vão não separa (Fase 4)

**Data:** 2026-10-10. **Vídeo:** `sky guitar/retrato brasileiro - tab & lesson.mp4`, ouro v2 (`data/gold/ouro_video/retrato_brasileiro_v2.json`).
**Medições brutas:** `data/saida/fase4_digitos/` (`medicao_vaos.json`, `paginas_antes.json`, `paginas_depois.json`,
`comparar_antes.txt`, `comparar_depois.txt`, `avaliar_antes*.json`, `avaliar_depois.txt`).

## Defeito

Casas de dois algarismos (`10`, `12`, `13`, `14`) saem como duas notas. O agrupamento de `tab/tabseg.py`
(`agrupar_tokens`, limiar `gap = 0,25` passo) junta componentes da mesma corda só com vão até 0,25 passo.

## Medição (regra 2: antes de mexer)

Vão entre componentes vizinhos da mesma corda, em passos, medido sobre os componentes brutos (antes de `agrupar_tokens`)
das páginas do ouro. Cada componente foi atribuído à nota do ouro pelo centro, a menos de 0,6 passo.

| grupo | n | mín | mediana | máx |
| --- | --- | --- | --- | --- |
| (a) algarismos do mesmo número de dois dígitos | 5 | 0,231 | 0,275 | 0,324 |
| (b) notas diferentes, ambas casadas ao ouro | 403 | 0,463 | — | — |
| (d) pares com algum componente sem nota casada | 56 | −0,73 | — | 0,37 |

O grupo (b) sozinho sugeria separação entre 0,324 e 0,463. **O grupo (d) desfaz essa separação**: entram `2`→`7`
(corda 1, pág. 5) com vão 0,324 e `7`→`4` com vão 0,37, além de `5`→símbolo (corda 1, pág. 8) com vão 0,37.
O vão de 0,324 do `2`→`7` é igual ao do `13` da pág. 8 (7 px nos dois casos). Não existe limiar de vão que
separe as duas classes.

## Tentativa (revertida)

`GAP_FUSAO_PASSOS = 0,39` (meio do vão observado com (b) apenas), com testes de limite e de imagem sintética.

| métrica | antes | depois |
| --- | --- | --- |
| `avaliar` oficial_1 / 2 / 3 | 66/72, 71/72, 68/72 | 66/72, 71/72, 68/72 (sem "CONTAGEM MUDOU") |
| casa certa, páginas do ouro (pareamento direto) | 481/493 = 0,976 | 479/493 = 0,972 |
| notas inventadas | 21 | 17 (porque uma parte das notas some) |
| números de dois dígitos certos | 1 de 5 (`14`) | 2 de 5 (`14`, `10`) |

Por página: `10` da pág. 12 passou a sair certo. `12` da pág. 12 e `12` da pág. 8 saem como token `tecnica`, sem nota.
`13` da pág. 8 passou a sair como `12`. Pág. 5 perdeu `2`, `7` e `4` da corda 1: os três componentes fundidos
formam um bloco de 2,2 passos, e `delimitar_tokens` recusa blocos acima de 2,0 passos. Casa certa na pág. 5: 39 → 37.

Os testes de limite falham com 0,25 e passam com 0,39, por isso a tentativa foi bem medida. O teste de imagem
(`12` e `1  2` na mesma corda) precisou de tracking de 0,15 passo: a fonte sintética põe o vão do `12` em 0,17 passo
ou menos, e então o teste não discrimina o limiar.

**Decisão:** não implementar. Código revertido. Só este registro e a tabela "não repetir" do `ESTADO.md` entram.

## Segundo defeito (anterior ao limiar)

O token fundido de dois dígitos vai para o classificador, e ele responde `tecnica` para o `12` (pág. 8 e pág. 12).
A nota sai de `notas` e vai para `nao_nota` com o glifo cru. O `12` da pág. 8 já é fundido com o limiar atual de 0,25
(vão 0,231). Ou seja, o problema de classificação existe com o agrupamento que o projeto tem hoje.

## Régua

- `tab.transcrever --inicio 0,5 --janela 30` gera uma predição que `tab.avaliar_video` pareia só com a tela 1 do ouro
  (1 de 13). Essa tela não tem `12`, então a régua não mede o defeito. Antes: precisão 35/37, revocação 35/493.
- Com `--inicio` nos quadros de referência das páginas 8 e 12, o pareamento legado (`escolher_tela_legado`) escolhe a
  tela 5 para o quadro da página 8. A causa é que as faixas `[t_ini, t_fim]` das telas 5 a 8 se sobrepõem no
  `pre.json`, e o pareamento pega a primeira. Defeito da régua, não do modelo; não corrigido aqui.
- Por isso a comparação por página usa pareamento direto (`comparar_paginas.py`), e não a régua.

## Próximos passos (não feitos)

1. Decidir a fusão de vizinhos pelo classificador do token fundido, e não só pelo vão: aceitar dois dígitos
   quando o classificador der dois dígitos com confiança alta, e manter separados os demais.
2. Corrigir `escolher_tela_legado` para não parear por sobreposição de intervalos.
3. Antes de qualquer limiar novo, medir de novo com todos os pares (incluindo os sem nota casada).
