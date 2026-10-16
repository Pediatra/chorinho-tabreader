# Onda 1 das frentes das mãos — briefings

**Data**: 2026-10-16. **Plano**: [`maos-frentes.md`](maos-frentes.md), seção 4.1. **Para quem**:
o dono, que abre uma worktree e um agente por frente e cola o briefing da frente.

## Como abrir cada worktree

Uma worktree por frente, a partir do `main` atual (o commit que trouxe este arquivo ou depois).
Nomes sugeridos:

| frente | worktree | branch |
| --- | --- | --- |
| 0 — resíduo | `../chorinho-wt-f0` | `maos/f0-residuo` |
| A3 — custo aprendido | `../chorinho-wt-a3` | `maos/a3-custo-aprendido` |
| B1 — janela por dedo | `../chorinho-wt-b1` | `maos/b1-janela-dedo` |
| C1 — inarmonicidade | `../chorinho-wt-c1` | `maos/c1-inarmonicidade` |
| D1 — ligados | `../chorinho-wt-d1` | `maos/d1-ligados` |

```bash
git worktree add ../chorinho-wt-f0 -b maos/f0-residuo main
```

As cinco frentes rodam em paralelo e não dependem umas das outras. Nenhuma precisa de GPU.
Só a C1 lê áudio do acervo, e nenhuma lê vídeo inteiro.

Quando uma frente terminar, avise a sessão principal com o nome do branch. Ela remede na `main`,
integra e consolida o `ESTADO.md`.

## Regras comuns (todas as frentes)

Estão no `maos-frentes.md` e valem inteiras. As que mais pegam:

- **Montagem**: `data/saida/` da cópia principal só para leitura e só a pasta da frente para
  escrita (seção 6.1). Confira `ls /app/data/saida/maos/m3d` dentro do container antes de medir.
- **CA1 primeiro**: reproduza exatamente D0 e D1 do M8 (341 e 285 erros em 2.437 notas) antes de
  mudar qualquer coisa.
- **Critérios congelados** (seção 5.3): pesos e limiares a priori escritos no documento da
  rodada **antes** da medida. Mudar depois de ver o resultado invalida a frente.
- **Proibido**: escrever fora da pasta da frente, editar `ESTADO.md`, `data/gold/`, o M8
  (`tab/maos_corda_sem_direita.py`) ou arquivos de outra trilha; dependência nova; commit em
  `main` (seção 6.3).
- **Entrega** (seção 9): código com o prefixo da frente e testes sem `data/saida/`; gate verde;
  documento de rodada na faixa da frente; commit no branch com o número na mensagem; resumo
  curto em português.

---

## Briefing — Frente 0 (resíduo)

```text
Você trabalha na worktree da Frente 0 das mãos do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/maos-frentes.md (seções 1 a 6, a Frente 0 na
seção 7, e as seções 8 e 9); docs/rodadas/1013-m8-corda-sem-a-mao-direita.md.

Tarefa: a Frente 0 — anatomia do resíduo do M8. Siga o "Como" da seção 7 à risca:
predição por nota de D0–D3 importando preparar_video, decodar e pontuar de
tab/maos_corda_sem_direita.py (o cache da câmera está em data/saida/maos/m8/camera_*.json;
nada lê vídeo, a não ser os 10 recortes olhados), categorias (a)–(h) por nota errada, tabela
categoria × vídeo, matriz de interseção, 10 casos olhados com recorte.

Território: módulos tab/maos_residuo*.py e tests/test_maos_residuo*.py; saída só em
MAOS_FRENTE_0 (tab/caminhos.py); rodadas 1101–1109. Sem porta.

Pare e relate se: os totais não baterem com a 1013 (CA1); "outros" passar de 30 % do resíduo
(olhe mais 20 casos e proponha categorias antes de recomendar).

Entregue: residuo.json, a rodada 1101 com a recomendação de ordem para as frentes A–D (quantas
notas do resíduo cada uma pode atacar, por vídeo e por (tela, coluna) distinta), gate verde,
commit no branch, resumo curto em português. Não some porcentagens de categorias que se
sobrepõem.
```

## Briefing — A3 (custo aprendido)

```text
Você trabalha na worktree da frente A3 das mãos do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/maos-frentes.md (seções 1 a 6, a Frente A e a A3
na seção 7, e as seções 8 e 9); docs/rodadas/1013-m8-corda-sem-a-mao-direita.md; a §4.1 de
docs/pesquisa/maos.md.

Tarefa: a A3 — pesos do custo do decodificador aprendidos da tablatura por perceptron
estruturado, sem câmera. Siga o "Como" da A3. Importe o decodificador do M8; não o edite. Fixe
features, número de épocas e taxa a priori e escreva-os na rodada antes de medir.

Treino e teste: para cada um dos 4 vídeos de teste, treine em todas as tablaturas exceto ele.
sky_4 é a lacrimosa e sky_8 é o glimpse: nunca no treino do próprio teste. Relate também o
teste deixando um canal de fora nos ouros do dono (data/gold/ouro_video, só leitura), e a
medida só com casa ≤ 7. Nada de tablatura externa (DadaGP descartado pelo dono).

Território: módulos tab/maos_decod_*.py e tests/test_maos_decod_*.py; saída só em
MAOS_FRENTE_A; rodadas 1110–1129. Porta 8101, se precisar.

Aceite: CA1–CA7 contra o D1 (seção 5.3). Reprova: não passa no CA2 ou no CA3, ou algum peso muda
de sinal entre dobras (relate a amplitude de cada peso).

Entregue: a3_pesos.json e a3_medida.json, a rodada 1110, gate verde, commit no branch, resumo
curto em português com consertadas e quebradas por vídeo.
```

## Briefing — B1 (janela por dedo)

```text
Você trabalha na worktree da frente B1 das mãos do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/guias/contexto-maos.md (seções 6 e 7);
docs/pesquisa/maos-frentes.md (seções 1 a 6, a Frente B, a B1 e a "Linha de base medida" da B3
na seção 7, e as seções 8 e 9); docs/rodadas/1013-m8-corda-sem-a-mao-direita.md; a §6.1 de
docs/pesquisa/maos.md.

Tarefa: a B1 — janela de casas pelas células das pontas dos dedos, mais estreita que a da mão
inteira do M8. Siga o "Como" da B1. O cenário principal usa a GRADE FIXA do quadro do dono em
todos os ataques (sem o teste de câmera): ao longo do braço ela erra no máximo 0,16 casa
(medido nos quadros q24–q31). Relate à parte o subconjunto em que a câmera casa (limiar 0,8 do
M8). Use só o eixo ao longo do braço; não atribua ponta a corda.

Compare três janelas: (i) a do M8; (ii) células das pontas com folga de 10 %; (iii) com 20 %.
Para cada uma: contém a casa verdadeira (%), largura média, fração das ambíguas presas com 1
candidata só, cobertura, tudo com denominador e por vídeo. As pontas existem só no t_ini:
declare. Não use a calibração pela música (tab/maos_calibrar_por_notas.py): vaza a resposta.
Os quadros q24–q31 de data/gold/maos/braco.json são teste da B3: não ajuste nada neles.

Território: módulos tab/maos_esq_*.py e tests/test_maos_esq_*.py; saída só em MAOS_FRENTE_B;
rodadas 1130–1149. Porta 8102, se precisar. Leia do acervo só os quadros dos casos olhados.

Aceite da janela (congelado): contém ≥ 95 %; 1 candidata em ≥ 70 % das ambíguas presas. Se
(ii) ou (iii) passar, rode-a no decodificador como D2 e meça CA1–CA7 contra o D1 e o D2 do M8.
Pare se alguma janela contiver < 90 %: olhe 10 casos e diga se a falha é da ponta, do braço ou
do instante.

Entregue: b1_janela.json, a rodada 1130, gate verde, commit no branch, resumo curto em
português. Diga também se a frente precisaria saber a corda de cada ponta (isso decide se a
B3 entra na onda 2).
```

## Briefing — C1 (inarmonicidade)

```text
Você trabalha na worktree da frente C1 das mãos do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/maos-frentes.md (seções 1 a 6, a Frente C e a C1
na seção 7, e as seções 8 e 9); a §2 e a §5.2 de docs/pesquisa/maos.md; a rodada 2001 em
docs/rodadas/ (regra do t_amostra0).

Tarefa: a C1 — teste de ir ou não ir: o coeficiente de inarmonicidade β medido no áudio do
YouTube separa as cordas candidatas de mesma altura? Siga o "Como" da C1 na ordem: extrair o
áudio a 48 kHz sem reamostrar (pode importar tab.audio_extrair; não edite), CONTROLE SINTÉTICO
codificado em Opus na taxa real dos vídeos (meça com ffprobe) antes de tudo, notas isoladas,
STFT longa com ajuste parabólico, ajuste linear em k², AUC por par de cordas de mesma altura.
Só numpy e cv2: a imagem não tem scipy.

Divisão de calibração e teste por tempo (primeira metade × segunda) ou por exibição, nunca por
nota sorteada. Compare só dentro da mesma altura. Use β (frequência dos parciais), não timbre
por amplitude.

Território: módulos tab/maos_timbre_*.py e tests/test_maos_timbre_*.py; saída só em
MAOS_FRENTE_C; rodadas 1150–1169. Porta 8103, se precisar. Leia só o áudio dos 4 vídeos e
registre quanto leu.

Aceite (de ir para a C2): controle sintético aprovado; AUC ≥ 0,80 fora da calibração em pelo
menos metade dos pares com amostra suficiente, em ≥ 3 dos 4 vídeos; inclinação de log β × casa
compatível com log 2^(1/6). Pare se o controle sintético falhar (a frente fecha com esse
número) ou se a AUC ficar < 0,65 na maioria dos pares.

Entregue: c1_beta.json, a figura β × casa por corda, a rodada 1150, gate verde, commit no
branch, resumo curto em português. Declare que usar a tablatura para escolher notas e calibrar
é limite superior.
```

## Briefing — D1 (ligados)

```text
Você trabalha na worktree da frente D1 das mãos do projeto chorinho. Leia inteiro, antes de
rodar qualquer coisa: AGENTS.md; docs/pesquisa/maos-frentes.md (seções 1 a 6, a Frente D na
seção 7, e as seções 8 e 9); docs/rodadas/1013-m8-corda-sem-a-mao-direita.md; a §2 de
docs/pesquisa/maos.md; configs/simbolos.yaml.

Tarefa: a D1 — nota ligada fica na mesma corda de uma nota que ainda soa, como restrição dura
no decodificador. Importe o decodificador do M8; não o edite. Meça as três fontes do rótulo
"ligada" separadas: (1) marcas l do dono em data/gold/maos/padroes_direita.json; (2) símbolos
da tablatura em nao_notas, com o significado por canal de configs/simbolos.yaml; (3) áudio sem
ataque perto do t_audio esperado (data/saida/maos/m7/audio/).

Separe ligado de altura diferente de prolongamento ((6), arco entre notas iguais): "acertar"
o prolongamento é trivial e infla o ganho. Tire os harmônicos da medida. Conte os ligados sem
nota anterior na corda e relate se os erros que sobram vêm em pares origem–ligada.

Território: módulos tab/maos_ligado_*.py e tests/test_maos_ligado_*.py; saída só em
MAOS_FRENTE_D; rodadas 1170–1179. Porta 8104, se precisar.

Aceite: CA1–CA7 contra o D1, por fonte, com quantas notas ligadas cada fonte achou e a precisão
da fonte 3 contra as fontes 1 e 2. Pare se a fonte 3 tiver precisão < 70 % contra a 2.

Entregue: d1_ligados.json, a rodada 1170, gate verde, commit no branch, resumo curto em
português.
```
