# Rodada 1004: dedo da esquerda por visão (M3)

Data: 2026-10-12. Trilha das mãos, M3 (ver `docs/guias/contexto-maos.md`, seção M3).
Gabarito: [rodada 1003](1003-gabarito-de-dedos.md). Dados: `data/saida/maos/m3/`.

## Pergunta

Dada a nota da tablatura (corda, casa, `t_ini`), qual dedo da mão esquerda pisa? Duas
perguntas: quanto a tablatura sozinha responde (linha de base por regra), e quanto a visão
da mão no quadro acrescenta, medido contra o gabarito do dono.

Só a esquerda. A direita ficou fora de escopo (ver ressalvas).

## O avaliador e a conta

`tab/maos_avaliar_dedos.py` mede qualquer método contra o gabarito, com as mesmas regras para
todos. Regras da conta da esquerda:

- sai a nota `n19` (o dono disse que a casa 3 da corda 3 não está sendo apertada);
- saem as duas notas do ataque `a22`, que duplica o `a21`;
- cada nota física conta uma vez (dedup por `indice_mvp`);
- resposta `?` fica fora da conta daquela mão;
- predição `None` (o método não decidiu) conta como erro no acerto total e fica fora do acerto
  entre decididas.

Resultado: **53 notas na conta, 40 pisadas** (as que não são corda solta). Das 53, 13 são
corda solta (casa 0), que todas as variantes acertam.

## Linha de base por regra (sem visão)

`tab/maos_regra_dedos.py`. A regra usa só a tablatura. Dedo = casa − P + 1, em 1..4, onde P é a
menor casa maior que zero do conjunto considerado. As variantes de janela tomam P entre todas
as notas do MVP com `|t_ini − t| ≤ J`. J em 0,5, 1 e 2 segundos; os três são reportados, e
nenhum foi escolhido pelo gabarito. A variante de pestana acrescenta o `"1"` quando a menor
casa do ataque é tocada por 2 ou mais notas com cordas não vizinhas.

Esquerda, 53 notas / 40 pisadas:

| método | acerto total | pisadas | cobertura | erros |
| --- | --- | --- | --- | --- |
| `regra_casa` (dedo = casa) | 25/53 | 12/40 | 48/53 | 28 |
| `regra_posicao_ataque` | 29/53 | 16/40 | 53/53 | 24 |
| `regra_posicao_janela_0_5` | 29/53 | 16/40 | 53/53 | 24 |
| `regra_posicao_janela_1` (base) | **36/53** | **23/40** | 53/53 | 17 |
| `regra_posicao_janela_2` | 34/53 | 21/40 | 52/53 | 19 |
| `regra_pestana_*` (cada base) | igual à base | igual à base | igual | igual |

A regra de pestana não muda nenhum número nesta amostra: as variantes `regra_pestana_*` dão
exatamente os números da base correspondente.

A janela de 1 segundo é a melhor das três, mas foi escolhida entre as três no mesmo gabarito
(in-sample). Não há número fora da amostra para ela.

**Por que a regra erra**: dos 17 erros da melhor regra, 9 são formas de acorde, em que o dedo
é maior que a casa (ex.: dedo 3 na casa 2). "Um dedo por casa" não representa essa forma. Não
é erro do gabarito. O teto da regra é baixo: a esquerda precisa de visão.

## A visão

### Calibração do braço (uma vez por vídeo)

`tab/maos_calibrar_braco.py` e `tab/maos_braco.py`. A câmera do braço é frontal e fixa. A
calibração lê 30 quadros espalhados a partir de 240 s, com ffmpeg (AV1 não decodifica no
OpenCV), e tira a mediana, para que a mão que se mexe seja apagada.

- **Cordas**: 6 retas `y = a + b·x`, com rms de 0,37 a 0,58 px por corda (193 a 201 pontos
  cada).
- **Trastes**: nut (traste 0) e trastes 1 a 14. Achados: 13 de 14; o traste 1 foi previsto pela
  geometria, não achado.
- **Escala**: razão medida entre casas vizinhas 0,949; teórica (temperamento igual) 0,944.
- **Câmera fixa**: deriva máxima dos trastes, entre o começo e o fim do vídeo, 4,0 px (7
  trastes comparados); das cordas, 1,08 px.

### Alvo e pontas

- **Alvo** de uma nota: a corda `c` a 70 % do caminho do traste `k−1` ao traste `k`, em direção
  ao traste `k` (`FRACAO_PISADA`).
- **Pontas**: pontos 8, 12, 16 e 20 da mão de 21 pontos, dedos 1 a 4 (indicador, médio, anelar,
  mínimo). A mão esquerda vem de `escolher_mao_esquerda`. Os 41 registros de
  `detalhes_visao.json` têm `origem_mao` = `wholebody`.
- **Dedo** = a ponta mais perto do alvo, no quadro do `t_ini`.

Variantes da visão, todas medidas no mesmo gabarito:

- `visao_ponta`: a ponta mais perto em `t_ini`;
- `visao_ponta_voto`: maioria entre os quadros de `t_ini − 0,1`, `t_ini` e `t_ini + 0,1`; empate
  fica com o quadro central;
- `visao_ou_regra`: a visão quando a ponta mais perto está a menos de meia largura de casa;
  senão, `regra_posicao_janela_1`. O limiar de meia casa é geométrico e não foi ajustado no
  gabarito.

### A ordem das cordas: história e correção

A primeira versão numerou as cordas pelo brilho ao contrário e acertou **32 de 53**. O erro
apareceu num diagnóstico contra o gabarito, não na leitura das imagens.

A correção vem da geometria. A câmera é frontal, a cabeça do violão fica à direita, e a mão
esquerda chega por baixo do braço, pelo lado das cordas agudas. Por isso a corda 1 (mi agudo)
é a linha mais próxima da mão, que na imagem é a de baixo. A conferência pelo brilho confirma:
os bordões revestidos (4 a 6) são de metal e os primas (1 a 3) são de náilon. Brilho medido da
corda 1 à 6: 90, 115, 127, 137, 149 e 176. `numerar_cordas` levanta erro se o topo não for mais
claro que a base.

Ressalva: a correção é justificada pela física e conferida pelo brilho, mas o erro foi
descoberto contra o gabarito. Ela foi feita depois de ver o gabarito, então não é independente
dele.

### Erros da visão nas pisadas

Dos 11 erros da `visao_ponta` nas 40 pisadas: 8 vieram do alvo ou das pontas, 2 da regra
"mais perto", 1 do tempo e nenhum do detector (commit `18ff0890`). O `detalhes_visao.json` tem
41 linhas: as 40 pisadas mais `n19`, que o avaliador exclui.

## Tabela final, lado a lado

Esquerda, 53 notas / 40 pisadas (`data/saida/maos/m3/avaliacao_*.json`):

| método | acerto total | pisadas | erros |
| --- | --- | --- | --- |
| `regra_posicao_janela_1` (regra, base) | 36/53 | 23/40 | 17 |
| `visao_ponta` | 42/53 | 29/40 | 11 |
| `visao_ponta_voto` | 43/53 | 30/40 | 10 |
| `visao_ou_regra` | **44/53** | **31/40** | 9 |

A melhor visão acerta 8 notas a mais que a melhor regra, no mesmo gabarito e com a mesma conta.
Com 53 notas, isso é um sinal, não uma medida fora da amostra.

**Direita (indicativo)**: `regra_direita` (corda → dedo) acerta 33 de 53 válidas, com 51
decididas (33/51 = 0,647 entre as decididas). O commit `4183fe1e` escreve "33/53", mas o JSON
tem 51 decididas. Vale o JSON. A direita é parcial no gabarito e não tem visão nesta rodada.

## Ressalvas

- **Um vídeo só**, com 53 notas e 40 pisadas. Não há conjunto separado: tudo que foi escolhido
  (janela, ordem das cordas, voto) foi visto neste mesmo gabarito.
- **A ordem das cordas foi corrigida depois de ver o gabarito** (ver acima).
- **Câmera de braço frontal e fixa** é um caso favorável. Em vídeo com câmera móvel ou sem
  câmera de braço, o mapa do braço não existe, e o método não se aplica.
- **Direita fora de escopo**: parcial no gabarito, sem visão.
- **Origem dos pontos**: as 41 mãos vieram do Wholebody (o M1 prefere o Wholebody e usa o
  MediaPipe só como complemento). A mão do COCO-WholeBody segue o mesmo esquema de 21 pontos
  do MediaPipe (0 pulso; 4, 8, 12, 16, 20 pontas do polegar ao mínimo), então os índices
  8, 12, 16 e 20 valem para os dois.

## Próximos passos

1. **Segundo gabarito, em outro vídeo ou canal**, para medir fora da amostra. Sem isso, o
   número 44/53 vale só para este vídeo.
2. **Vídeos sem câmera de braço**: sem o mapa do braço, a visão não tem alvo. Precisa de outra
   forma de achar a corda e a casa.
3. **Direita**: gabarito completo (hoje parcial) e um método com visão para a mão direita.

## Comandos

```bash
python -m tab.maos_avaliar_dedos --predicao data/saida/maos/m3/pred_visao_ou_regra.json
python -m tab.maos_regra_dedos                   # linha de base por regra
python -m tab.maos_calibrar_braco                # braço: cordas, trastes, deriva
python -m tab.maos_visao_dedos --dispositivo cuda  # predição pela visão (GPU, no container)
```

`tab/maos_visao_dedos.py` usa a GPU (detector do M1); rode no container com acesso à GPU,
como no M1.

## Artefatos

- Avaliações: `data/saida/maos/m3/avaliacao_*.json`; predições: `pred_*.json`.
- Braço: `data/saida/maos/m3/braco.json`, `braco.jpg` (cordas e trastes sobre a mediana).
- Visão: `data/saida/maos/m3/detalhes_visao.json` (uma linha por nota), `folha_visao.jpg`,
  `visao.log`.
- Código: `tab/maos_avaliar_dedos.py`, `tab/maos_regra_dedos.py`, `tab/maos_braco.py`,
  `tab/maos_calibrar_braco.py`, `tab/maos_visao_dedos.py`.
- Commits: `4183fe1e` (avaliador e linha de base), `18ff0890` (visão). Gate no commit `18ff0890`:
  562 testes passando.
