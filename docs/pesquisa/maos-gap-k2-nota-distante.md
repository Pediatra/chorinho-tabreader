# Tarefa delegada — A checagem K2 recusa pelo menos uma nota de outro trecho da música?

**Data**: 2026-10-24. **Trilha**: mãos (rodadas `1NNN`). **Quem escreveu**: a sessão principal das
mãos. **Para quem**: um agente que **não** viu a conversa. Tudo o que você precisa está aqui; se
algo não estiver, **pare e pergunte ao dono**, não suponha.

**Tempo máximo**: 3 horas de trabalho. Passou disso, pare e entregue o relatório com o que tem.

**Esta tarefa continua outra**: `docs/pesquisa/maos-gap-k2-nota-vizinha.md` (leia-a primeiro,
seções 1, 2, 4 e 5: o projeto, a K2, os dados e como rodar Python aqui). O relatório dela
está em `data/saida/maos/m49/k2_vizinha/` (`relatorio.md` e `revisao-metodologica.md`).

---

## 1. O que a tarefa anterior achou (e a sessão principal conferiu)

- Nas 449 notas ouro do vídeo do MVP, se a gente troca a célula (corda, casa) da nota pela
  célula da nota **anterior ou seguinte no tempo**, a K2 **ainda passa** em 654 de 895 trocas
  (73 %). Mesmo com a vizinha a 2 casas ou 3 cordas de distância, passa em 226 de 367 (62 %).
- A causa é física: a mão esquerda fica com vários dedos plantados em várias casas ao mesmo
  tempo. A K2 não confirma "este dedo tocou esta nota"; no máximo confirma "a mão está na
  região do braço onde a nota fica".

## 2. A pergunta desta tarefa

A K2 confirma **pelo menos a região da mão**? Isto é: se a gente põe na nota a célula de uma
nota de **outro trecho** da música (a ≥ 3 s de distância), com a casa **longe** da casa da nota,
a K2 recusa?

Se nem isso ela recusar, ela não protege nada e sai do portão do ouro. Quem decide é a sessão
principal; você mede e relata.

## 3. Os dados

Os mesmos da tarefa anterior, na pasta `data/saida/maos/m49/mvp/execucao_1/`:
`retrato brasileiro - tab & lesson.maos.json` e `.maos.npz` (nomes com espaço e `&`: **sempre
entre aspas**). Eles foram **regerados em 2026-10-24 06:05 com o capo certo** (449 ouro, 295
prata, 19 recusado). Confira isso com o `resumo` do JSON antes de começar; se der
`ouro: 0`, pare e relate (é a versão velha).

## 4. O que fazer

Escreva **um** script: `data/saida/maos/m49/k2_distante/medir.py` (crie a pasta). Não edite nada
dentro de `tab/`. Use a K2 de verdade: `from tab.maos.base import checar_k2`.

1. Carregue o JSON e o `.npz` (`np.load(caminho, allow_pickle=False)`; transforme em
   `dict` com `{k: d[k] for k in d.files}`).
2. **As notas `e`**: as de `nivel == "ouro"` (devem ser 449).
3. **As iscas de cada `e`**: toda nota `v` do JSON com `casa > 0`, `t_som` não nulo e
   `|v.t_som − e.t_som| ≥ 3,0 s`, com `(v.corda, v.casa) != (e.corda, e.casa)`.
4. **Faixa da isca** pela distância de casa `Δ = |v.casa − e.casa|`: `0` (mesma casa, outra
   corda), `1`, `2`, `3-4`, `5+`.
5. Para cada par `(e, v)`: `r = checar_k2(denso, tuple(e["janela"]), e["t_som"], v["corda"],
   v["casa"])`. A isca **passa** se `r["passou"] is True`. A janela, o `t_som` e o braço são os
   de `e`; a isca só empresta a célula.
   - **Confira o script antes**: com a célula da própria `e`, `checar_k2` tem que dar
     `passou: True` nas 449. Se não der, o script está errado: conserte (no máximo 3
     tentativas, seção 6).
6. **Tabela**, uma linha por faixa:
   - `pares`: quantos pares `(e, v)`;
   - `passa`: quantos passam, e a fração;
   - `notas_com_isca`: quantas `e` têm pelo menos uma isca naquela faixa;
   - `notas_alguma_passa`: dessas, quantas têm pelo menos uma isca que passa.
7. **Por posição**: para cada `e`, a fração das suas iscas `5+` que passa. Mostre a
   distribuição (mínimo, mediana, máximo) e os 5 piores casos (`tela`, `coluna`, `corda`,
   `casa`, `t_som`).
8. **Folha**: 12 pares `5+` que passam (sorteio com `random.Random(20261050)`; todos, se forem
   menos). Use o desenho do código: copie a lógica de `folha` em `tab/maos/base_gpu.py`
   (funções `_quadro_da_k2` e `_celula_na_corda`), desenhando a célula de `e` em vermelho e a
   da isca em azul, no quadro em que a ponta chega mais perto da célula **da isca**. Precisa da
   imagem `localhost/chorinho-maos:dev` e do acervo montado somente leitura (comando na tarefa
   anterior, seção 5). Grave `data/saida/maos/m49/k2_distante/folha.jpg`. **Olhe a folha**.

## 5. Regra de decisão (escrita antes de medir; não mude depois)

| resultado | conclusão |
| --- | --- |
| faixa `5+` passa em ≤ 10 % dos pares **e** faixa `3-4` em ≤ 25 % | "a K2 confere a **região da mão** (umas 2 casas)" |
| faixa `5+` passa em > 10 % | "a K2 **não confere nem a região**" |
| menos de 100 notas `e` com alguma isca `5+` | "o vídeo não tem trechos longe o bastante para responder"; relate a faixa `3-4` e pare |

Você **recomenda**; quem muda a K2 ou o portão do ouro é a sessão principal, com uma rodada nova.

**Aceite da tarefa** (você terminou quando tem tudo isto):

1. `medir.py` roda do zero e grava `data/saida/maos/m49/k2_distante/resultado.json` com a tabela
   e a distribuição;
2. a conferência do passo 5 deu "449 de 449";
3. `folha.jpg`, e você a olhou;
4. `relatorio.md` na mesma pasta (formato na seção 7).

## 6. Como não se perder (regras contra loop)

- Trabalhe na pasta principal (`/var/home/gabriel/Projects/chorinho-dataset`): você só **cria**
  arquivos em `data/saida/maos/m49/k2_distante/`. **Não** edite `tab/`, `tests/`, `docs/`,
  `data/gold/` ou o acervo. Nada de `git`.
- **Um erro igual duas vezes** (a mesma mensagem ou o mesmo número errado): pare, escreva o que
  tentou e entregue.
- **No máximo 3 tentativas** para a conferência do passo 5 bater.
- **Não invente faixa nova** nem outro limite de tempo além de 3,0 s. Se achar que outro seria
  melhor, escreva como sugestão, sem medir.
- **Não rode nada na GPU.** A folha só lê quadros do vídeo (CPU).
- Se um número parecer bom ou ruim demais, **olhe a folha** antes de concluir.

## 7. Quando parar e o que entregar

Pare quando o aceite estiver completo, quando bater a seção 6, ou depois de 3 horas.

`relatorio.md`, em português simples:

```text
# K2 contra nota de outro trecho — relatório
## Resposta curta (3 linhas)
## Números (a tabela por faixa, com "X de Y")
## Por posição (distribuição e os 5 piores)
## O que vi na folha
## Conclusão pela regra da seção 5 (copie a linha da regra que vale)
## Limites e sugestões (sem medir)
```
