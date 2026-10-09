# Rodada 42 — o painel não está onde eu estimo; e estimar é o problema

## 1. O que eu fiz

Testei três sub-regiões candidatas do quadro do `a banda — chico buarque` procurando as 6 cordas:

| região | tinta | picos crus | `segmentar` |
| --- | --- | --- | --- |
| y 540–700 | 8 % | 1 | 0 linhas |
| y 560–720 | 3 % | 0 | 0 linhas |
| y 500–760 | 16 % | 5 | 0 linhas |

Nenhuma dá 6 linhas. E em y 480–660 o perfil era um **platô de 68–70 %** em ~80 px — isso não são
6 linhas finas, é uma **região preenchida** (o vídeo do violão).

## 2. O que eu já sei com certeza

- **o painel existe e eu o vi**: o recorte `fr[500:900, 40:1500]` mostra a tablatura inteira —
  rótulos e/B/G/D/A/E em laranja, cordas tracejadas, algarismos brancos e laranja;
- **o mecanismo do marcador está confirmado**: os algarismos passam de branco a laranja conforme são
  tocados (rodada 40, visto em imagem);
- **dentro de y 500–900 há linhas fortes** (perfil de até 0,81 medido com `binarizar`).

Então o painel está nessa faixa — mas eu **não acerto o y exato por estimativa**, e cada tentativa
gasta uma rodada. Tentar `y=X` a `Y` é chute, e eu já gastei três.

## 3. A conclusão que importa

**O problema não é o segmentador: é eu estar escolhendo a região por estimativa visual.**
O caminho certo — que eu já identifiquei duas vezes e ainda não implementei — é **detectar o painel
pelas suas propriedades**, não pelo meu palpite de coordenada:

- o painel é uma **faixa horizontal grande e uniforme** (fundo escuro liso, variância baixa);
- o vídeo é **textura** (variância alta);
- logo: calcular a variância local por linha/coluna e achar a faixa uniforme resolve as duas coisas
  de uma vez — **localiza o painel** e **rejeita o braço do violão** (que foi o erro das rodadas 33
  e 39).

Isso é uma função pequena e determinística, e substitui três rodadas de tentativa por coordenada.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** (corda, casa, técnica) | **0,805** nos 4 canais com gabarito |
| **geometria** | funciona nos recortes e em painéis que ocupam o quadro; **falha quando eu erro a região** |
| **tempo** | mecanismo confirmado (branco → laranja); bloqueado pela localização do painel |

## 5. Próximo passo, e não é tentativa

Implementar **detecção do painel por uniformidade de fundo** (variância local baixa em faixa
horizontal), e usá-la como:
1. **entrada** do segmentador (recorta o painel antes de procurar as cordas);
2. **portão** contra vídeo (braço/corpo do violão);
3. **caixa desenhada em todo resultado** — para que a região analisada seja visível na saída, e um
   erro de região nunca mais passe despercebido.

Depois disso, a série de cor (já implementada) roda na região certa e o tempo sai — ou eu descubro,
com prova visual, que aquele painel tem outra particularidade.
