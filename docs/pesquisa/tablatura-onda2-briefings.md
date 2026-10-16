# Onda 2 das frentes da tablatura — briefings

**Data**: 2026-10-16. **Plano**: [`tablatura-frentes.md`](tablatura-frentes.md), seções 4 e 7.
**Antes**: a onda 1 ([`tablatura-onda1-briefings.md`](tablatura-onda1-briefings.md)) fechou. O
resumo está no `ESTADO.md`, seção "Tablatura — 2026-10-16 — onda 1 das frentes".

## O que a onda 1 decidiu

- **A1 não abre.** A rede acha o ligado em 25 de 139 regiões, com classe certa em 4. Não é por
  limiar, e o ajuste fino não apagou o ligado (rodadas 0101–0104). O caminho é a B (estilo do arco
  no gerador) ou a A2 (detector de arco). A **B1 vem primeiro**: é barata e testa a causa que mais
  vezes se confirmou no projeto (cobertura do gerador). A A2 espera a B1.
- **C1 sai desta onda** (rodadas 0150–0153): aliasing de período de 2 compassos no mr. tabs.
- **D1 encerrada** (rodada 0170), sem D2.
- O dono **aprovou a dependência do AlphaTab** para a B1 em 2026-10-16.

## Worktrees

| frente | worktree | branch |
| --- | --- | --- |
| B1 — sonda AlphaTab | `../chorinho-wt-tab-b1` | `tab/b1-alphatab` |
| E1 + E2 — sondas de modelos prontos | `../chorinho-wt-tab-e` | `tab/e-sondas` |

```bash
git worktree add ../chorinho-wt-tab-b1 -b tab/b1-alphatab main
```

## Regras comuns

As da onda 1 valem inteiras (montagem, proibições, entrega). Duas mudanças:

- **CA1 com o ouro corrigido** (commit `3e7d4d74`):
  - **T8.2**: ouro 1573, entregues 1566, casadas 1557, casa 1551/1557, inventadas 9, perdidas 16.
  - **Dobras**: ouro 1771, entregues 1799, casadas 1761, casa certa 1744, inventadas 38,
    perdidas 10.
- **GPU**: nenhuma das duas usa. Se precisar, pare e pergunte à sessão principal; respeite
  `data/saida/gpu.lock`.

---

## Briefing — B1 (o modelo atual num renderizador que ele nunca viu)

```text
Você trabalha na worktree da frente B1 da tablatura do projeto chorinho
(../chorinho-wt-tab-b1, branch tab/b1-alphatab). Leia inteiro antes de rodar qualquer coisa:
AGENTS.md; docs/pesquisa/tablatura-frentes.md (seções 5, 6, 8, 9 e a Frente B na seção 7);
docs/pesquisa/tablatura-onda1-briefings.md (regras comuns) e
docs/pesquisa/tablatura-onda2-briefings.md (mudanças da onda 2); as rodadas 0101 e 0103
(números da régua de técnica por classe, folga 0,5, que entram no critério da B2).

Tarefa: a B1, na ordem do "Como" da Frente B. Faça o CA1 primeiro, com os números da onda 2.

Dependência (aprovada pelo dono em 2026-10-16): AlphaTab (@coderline/alphatab), em Node.js.
- NÃO mude o Dockerfile nem a imagem chorinho:dev. Rode o AlphaTab num container Node à parte
  (imagem oficial node, versão LTS com tag exata), com o pacote em versão exata. Registre na
  rodada as versões, o comando e a licença do pacote (confira no package.json do pacote; se não
  for compatível com uso no projeto, pare).
- O código JS e o package.json ficam em tab/gerador_alphatab/ (o prefixo da frente); o
  node_modules não entra no git.
- Saída do renderizador (imagens + caixas de cada nota) vai para TAB_FRENTE_B
  (data/saida/tab_frentes/fb_gerador/b1/); a leitura no modelo roda no container chorinho.

Passo 1 decide tudo: o AlphaTab dá a caixa de cada nota renderizada (boundsLookup ou
equivalente), com corda e casa? E a de cada técnica (ligado, slide, harmônico)? Se não der a de
nota, pare. Se der a de nota e não a de técnica, siga só com casa e registre.

Os 20 trechos em AlphaTex são escritos à mão por você, sem música de terceiros: técnicas da
régua (h, p, slide, ligadura, harmônico, bend, arpejo, rasgueado), casas 0 a 19, pelo menos
30 % de dois algarismos. Renderize e passe para o formato de entrada do modelo pelo mesmo
caminho das telas reais (escolher_ou_mascara / segmentar, ou normalizar_sistema com as linhas
das cordas tiradas das caixas do AlphaTab; diga qual). Aplique as degradações de vídeo que o
gerador sintético já usa (as mesmas do treinar_ft: brilho/contraste, JPEG 40-95, desfoque leve)
e meça também sem degradação. Modelo: artefatos/detector_tab_final_s1_ger.

Critério (congelado, do plano): a sonda não tem aceite; a B2 só abre se casa < 0,98 no
AlphaTab, ou se uma classe de técnica da régua tiver acerto 0,2 abaixo do acerto dela nas marcas
do dono (rodada 0101, folga 0,5). Escreva na rodada 0130 antes de medir: pareamento (corda igual,
|dx| ≤ 0,5 passo, guloso como em t82_comparar.py), os números da 0101 por classe que servem de
comparação, e o que conta como técnica achada.

Olhe as imagens: monte uma folha com os 20 trechos renderizados e outra com os erros, e
descreva em que o estilo do AlphaTab difere das telas reais e do nosso gerador (fonte, arco,
espessura, espaçamento). "Estilo padrão não é estilo de canal": diga isso nos limites.

Território: tab/gerador_*.py e tab/gerador_alphatab/, tests/test_gerador_*.py, TAB_FRENTE_B,
rodadas 0130–0149. Proibido: tab/sintetico*.py (o gerador do produto), DETECTOR_PADRAO,
data/gold/, commit na main, GPU.

Entregue: a rodada 0130 com casa e técnica por classe (degradado e limpo), as folhas, a
recomendação (B2 abre ou não, pelo critério), gate verde, commit no branch, resumo curto em
português com o hash.
```

---

## Briefing — E1 + E2 (sondas de modelos prontos)

```text
Você trabalha na worktree das sondas da tablatura do projeto chorinho (../chorinho-wt-tab-e,
branch tab/e-sondas). Leia inteiro antes de rodar qualquer coisa: AGENTS.md;
docs/pesquisa/tablatura-frentes.md (seções 5, 6, 8, 9 e a Frente E na seção 7);
docs/pesquisa/tablatura-onda1-briefings.md (regras comuns) e
docs/pesquisa/tablatura-onda2-briefings.md (mudanças da onda 2).

Expectativa baixa: são sondas. Faça o CA1 primeiro, com os números da onda 2.

E1 — guitar-tab-omr como segunda leitura no resíduo (rodada 0180).
- Antes de baixar qualquer peso: confira a licença dos pesos no Hugging Face. Sem licença
  clara que permita o uso, pare e relate (é uma resposta válida). Registre o repositório, a
  revisão (hash) e a licença.
- Siga o "Como" e o aceite da E1 do plano. As 31 falhas da T8.2: tire da comparação em
  data/saida/fase8/ger/t82_comparar.json (só leitura; o "novo" é o produto); confira que são
  31 antes de usar. As 100 notas certas: sorteio com semente fixa, escrita na rodada antes.
- Pareamento por ordem na corda; relate quantos pares ficaram ambíguos.

E2 — máscara de ligadura do homr em recorte de tablatura (rodada 0181).
- O homr é da trilha partitura. Descubra onde está instalado e se expõe a máscara de ligadura,
  só lendo; NÃO edite tab/partitura_* nem nada da trilha partitura; não mexa em
  data/gold/partitura/. Se ele não expuser a máscara sem editar o código dele, pare e relate.
- 20 telas com arcos marcados pelo dono: as regiões h, p e ligadura do ouro (EOB, Room 335,
  From This Place, La Vie). Liste as telas na rodada antes de rodar.
- Aceite do plano: 70 % dos arcos do dono ou mais, com 1 marca falsa por tela ou menos. O arco
  tem de casar com o par de números certo, não só acender perto.

Território: tab/sonda_*.py, tests/test_sonda_*.py, TAB_FRENTE_E
(data/saida/tab_frentes/fe_sondas/), rodadas 0180–0189. Pesos baixados vão para
artefatos/tab_frentes/ (fora do git), nunca para /tmp. Dependência nova de Python: pare e
pergunte antes de instalar. Proibido: GPU, data/gold/, DETECTOR_PADRAO, commit na main.

Entregue: rodadas 0180 e 0181 com os números contra o aceite, folhas olhadas, gate verde,
commit no branch, resumo curto em português com os hashes.
```
