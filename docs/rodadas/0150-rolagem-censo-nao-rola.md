# 0150 — Rolagem (C1): triagem do censo; os rolantes andam em saltos

**Frente:** C1 (costura da tablatura que rola, ancorada nas barras, mapa x_partitura → t).
**Branch:** `tab/c1-rolagem`. **Pasta de saída:** `data/saida/tab_frentes/fc_rolagem/rodada0150/`.
**Status:** corrigida em 2026-10-16. A triagem e a checagem visual abaixo são **primeira leitura**:
os vídeos rolam **em saltos**, não "não rolam" como a primeira leitura concluiu (ver Correção).
O nome do arquivo ficou como estava, para não quebrar as referências à rodada.

## Pergunta

Os três rolantes indicados (mr. tabs, leonardo ramos, kenneth acoustic) rolam de fato? Se não,
o caminho rolante da C1 não tem material para medir.

## CA1 (reprodução), antes de qualquer mudança

Feito com as cópias de leitura em `fc_rolagem/ca1_r0150/` (script copiado de
`data/saida/fase8/ger/t82_comparar.py`, só o caminho de saída trocado):

- **T8.2 (modelo novo):** ouro 1573, entregues 1566, casadas 1557, casa 1551/1557, inventadas 9,
  perdidas 16. Bate com o esperado.
- **T8.2 (modelo antigo, informativo):** ouro 1573, entregues 1563, casadas 1556, casa
  1549/1556, inventadas 7, perdidas 17.
- **Dobras (6 vídeos, `tab.avaliar_video` sobre as leituras gravadas):** soma de `notas.total`
  de cada vídeo com a main atual (bc431c0f): ouro 1771, entregues 1799, casadas 1761, casa certa
  1744, inventadas 38, perdidas 10. Bate com o número da main citado no briefing da retomada.
  Saídas em `rodada0150/ca1/` (um JSON e um TXT por vídeo); a soma foi feita por script sobre
  os JSON, sem releitura de vídeo.
  - Antes, com a main de 15 de outubro, a soma era 1774/1799/1764/1747/35/10. A diferença vem
    do ouro do Room 335, de onde o dono tirou 3 notas; as 3 leituras do produto passaram a
    contar como inventadas (35 → 38). As entregues não mudaram.

CA1 passou (com os números da main atual).

## Critérios (congelados antes da medida)

Os do briefing: deslocamento com erro mediano ≤ 1 px contra 20 pares à mão por vídeo; reprovação
se o deslocamento não chegar a 1 px. A triagem abaixo usa limiares escritos no código antes de
rodar: parado |dx| < 0,3 px; anda 0,3 a 40 px; salto > 40 px ou resposta < 0,5.

## Triagem dos 66 rolantes do censo (primeira leitura)

`tab/rolagem_triagem.py`, janela de 40 s a partir do primeiro instante com tablatura, 4 quadros
por segundo (160 quadros por vídeo, lidos pelo `tab.leitor`), sobre o recorte do censo.
Resultado completo em `rodada0150/triagem.json` e `triagem.log`.

- 56 dos 66 têm passos "anda" minoritários (parados e saltos somados são maiores). Os 10 com "anda" maioritário são 7 da guitar dell'arte e 3 do mr. tabs `#shorts`.
- Os **parados** dominam nos canais leonardo ramos, kenneth acoustic e mr. tabs (ex.: leonardo
  ramos: 140 a 154 parados de 160 em quase todos; mr. tabs "no rain": 146 parados, 2 andam, 11
  saltos).
- Os 4 `#shorts` do mr. tabs e as peças da guitar dell'arte aparecem com muitos passos "anda".
  **Esse sinal é falso** (ver a checagem visual): a correlação segue a barra de cursor e o
  recorte pequeno, não a tablatura.
- Limite da triagem: a contagem não separa rolagem de salto com sobreposição de troca de página.
  Um salto grande (> 40 px) vira "salto" sem que se confira o conteúdo de antes. Por isso a
  triagem é só a primeira leitura.

## Checagem visual (olho, primeira leitura)

Quadros em `rodada0150/olho/`. Esta tabela foi lida antes da correção; a leitura dos
dois primeiros vídeos mudou (ver Correção).

| vídeo (canal) | janela | o que se vê | arquivo |
| --- | --- | --- | --- |
| aire de zamba (leonardo ramos) | 80 a 82,5 s, 6 quadros | pauta fixa; só o cursor e o destaque de compasso andam | `olho/leonardo_exp/` |
| aire de zamba (leonardo ramos) | 0 a 143 s, 36 quadros (1 a cada 4 s) | troca de página e de sistema; não há deslizar contínuo | `olho/leonardo_triagem/folha.png` |
| blind melon - no rain (mr. tabs) | 60 a 64 s, 8 quadros | **corrigido: rola em saltos** (ver Correção) | `olho/mrtabs_norain_60/folha.png` |
| location - khalid (kenneth acoustic) | 182 a 186 s, 8 quadros | **corrigido: rola em saltos** (ver Correção) | `olho/kenneth_location_182/folha.png` |
| hanging out in the upside down #shorts (mr. tabs) | 3 a 7 s, 8 quadros | pauta fixa; cursor e página trocam (não reconferido) | `olho/mrtabs_upsidedown_3/folha.png` |
| concordancias no. 1 (guitar dell'arte) | 24 a 28 s, 8 quadros | mostra o violonista, não a tablatura | `olho/dellarte_conc_24/folha.png` |

Dx medido entre quadros consecutivos (`rolagem_deslocamento`, 6 quadros por segundo):
leonardo 76 a 82 s e 20 a 24 s: |dx| < 0,02 px em todos os passos, exceto os saltos de página.
Essa medida não mascarou o cursor nem o destaque de compasso, então não separa o movimento da
tablatura do movimento do cursor. Não serve de prova de que a pauta fica parada.

## Correção (2026-10-16)

A conclusão da primeira leitura, "não rolam", está errada para os dois vídeos abaixo. Eles
**rolam em saltos**: a linha fica parada por alguns segundos e depois anda de uma vez, em 1 ou 2
passos de animação, e parte do que estava na tela continua visível depois do salto. A triagem
chamou de "troca de página" todo passo acima de 40 px, e esse foi o erro. A "Decisão" acima
(paginado com cursor) está superada por esta seção.

Os dois exemplos, nas folhas da própria rodada (quadros de 0,5 s):

- **mr. tabs, "no rain", 60 a 63,5 s** (`olho/mrtabs_norain_60/folha.png`): os compassos 37 a 41
  ficam parados nos quadros de 60,0 a 63,0 s. Entre 63,0 e 63,5 s a linha anda cerca de 675 px.
  O compasso 41 está em x ≈ 805 antes do salto e em x ≈ 130 depois, e o quadro de 63,5 s traz
  os compassos 41 a 45. Sobreposição: compasso 41.
- **kenneth acoustic, "location", 182 a 185,5 s** (`olho/kenneth_location_182/folha.png`): o
  compasso 60 fica em x ≈ 535 de 182,0 a 184,0 s. Entre 184,0 e 184,5 s a linha anda cerca de
  475 px; o compasso 60 vai para x ≈ 60 e o 59 sai pela esquerda. Entre 184,5 e 185,0 s anda
  cerca de 110 px (compasso 61 de x ≈ 350 para x ≈ 240). Dois saltos, com 0,5 s entre eles.
  Sobreposição: compassos 60 e 61.

Os números são leitura visual das folhas, não medida: a medida do deslocamento por salto é a
rodada 0151.

O que a correção muda:

- Os saltos com sobreposição são o que a C1 precisa medir. A pergunta passa a ser se o salto
  tem sobreposição e de quanto é o deslocamento, não se o vídeo rola.
- O leonardo ramos **não está confirmado** (a folha dele tem um quadro a cada 4 s, pouco para
  ver salto de 0,5 s). A rodada 0151 olha esse canal a 10 quadros por segundo em volta de duas
  mudanças; se for troca de página sem sobreposição, o canal sai e escolhemos outro.
- O `#shorts` do mr. tabs e a guitar dell'arte não foram reconferidos depois da correção.

## Não repetir

- Não usar a forma "rolante" do censo como filtro para a C1 sem conferir no olho.
- A triagem por `phaseCorrelate` marca "anda" para o cursor em movimento. Antes de contar
  movimento, mascare o cursor (faixa vertical fina) ou use a faixa sem ele.
- Saltos de página (|dx| > 40 px) são o sinal dominante no acervo para estes canais.
- Salto > 40 px não é troca de página sem conferir se o conteúdo de antes continua na tela.
  Compasso que reaparece deslocado é salto com sobreposição, não página nova.

## Limites

- Nada de deslocamento medido contra os 20 pares à mão: não foram feitos nesta rodada. Isso é
  a rodada 0151.
- Os 66 rolantes foram triados só pelos contadores, não olhados um a um. A frase "não rola" da
  primeira leitura não vale para mr. tabs "no rain" nem para kenneth "location" (ver Correção).
- A pasta `data/saida/tab_frentes/fc_rolagem/` já continha `ca1/`, `sonda/` e `_explorar.py`
  (de 15 de outubro). Só listei os nomes; não li os arquivos dela nem alterei nada lá.
