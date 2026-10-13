# 2014 — Áudio: por que o alinhador fica com um trecho curto nas exibições recusadas

Data: 2026-10-13. Só medição; nada mudou em `tab/`. Script, resultados, log e figuras em
`data/saida/audio/a4/dp_trecho/` (`medir_dp_trecho.py`, `resultados.json`, `saida.log`,
`figuras/`). Sem o *campanitas* (descartado pelo dono).

## Pergunta

Em telas claramente tocadas, o alinhador v2.1 fica com 1 a 3 colunas e recusa a exibição.
Hipótese: a leitura perde colunas, as notas que sobram ficam mais espaçadas do que o
andamento `T` espera, e o termo de andamento (`LAMBDA_ANDAMENTO · |log(dt/(dc·T))|`) pune
cada buraco. Com isso o DP prefere um trecho curto.

## Casos

- 6 exibições recusadas: room 335, telas 33, 12 e 25; giant steps, telas 5, 13 e 9.
- 4 exibições boas de controle: MVP, tela 3; iwaki *la vie en rose*, tela 3. Duas
  exibições de cada.
- A tela 33 do room 335 tem uma gêmea aceita, a tela 35. Foi o único par de gêmeas achado
  nos 13 vídeos.

## Resultado

1. **Reprodução.** O script chama o próprio alinhador e chega ao JSON gravado: 1787 de 1787
   colunas e 97 de 97 exibições idênticas, nos 4 vídeos.
2. **Qual termo derruba o caminho que cobre a página.** Foi medido para os 6 casos.
   | caso | escolhido | caminho forçado a cobrir tudo | termo que mais pesa |
   | --- | --- | --- | --- |
   | room 335 t33 | 3 casadas, 1,38 | 13 casadas, −0,57 (gêmea c17–25: 0,68) | andamento |
   | room 335 t12 | 1, 0,46 | 3, −0,08 | andamento |
   | room 335 t25 | 3, 1,13 | 7, −0,33 | coluna sem ataque |
   | giant t5 | 2, 0,61 | 5, −0,41 | coluna sem ataque |
   | giant t13 | 1, 0,57 | 1, −0,23 | coluna sem ataque |
   | giant t9 | 1, 0,57 | 10, −1,02 | andamento |

   O custo de pular pico nunca é o que mais pesa. Nos caminhos forçados, o intervalo entre
   ataques erra o `T` esperado em 30 a 70 % (mediana de |log| de 0,25 a 0,54). Isso combina
   com colunas que faltam na leitura.
3. **Afrouxar os custos (sensibilidade).** As exibições recusadas contam como aceitas com
   ≥ 4 casadas. Nas boas, conta quantas colunas tiveram o tempo mudado em mais de 30 ms.
   | configuração | recusadas que passariam | colunas boas que mudam > 30 ms |
   | --- | --- | --- |
   | como está (λ 0,5; sem ataque 0,2) | 0 de 6 | 0 de 112 |
   | λ × 0,5 | 3 de 6 | 10 de 112 |
   | λ × 0,25 | 5 de 6 | 11 de 112 |
   | λ = 0 | 5 de 6 | 15 de 112 |
   | sem ataque × 0,5 | 1 de 6 | 0 de 112 |
4. **Achado lateral, conferido por mim.**
   - A janela de busca é a página com 0,5 s a mais de cada lado (`MARGEM_JANELA_S`).
   - Na tela 33, as 3 colunas escolhidas (c24–c27, o fim da página) caem **antes de a página
     aparecer**. Musicalmente isso não faz sentido; o que casou foi a página anterior, que
     termina parecido.
   - Nos 13 vídeos, **8 de 49** exibições recusadas têm o trecho escolhido inteiro fora da
     página, na margem. Todas as 8 têm alarme de leitura, ou seja, **8 de 42 alarmes**.
   - Esses 8 alarmes medem o casamento com a página vizinha, não a leitura desta página.

## Leitura

- **Nenhuma troca de custo resolve.** Baixar λ aceita até 5 de 6 casos, mas muda o tempo de
  10 a 15 das 112 colunas boas. Não há gabarito para saber se isso melhora ou piora.
  Baixar só o custo de coluna sem ataque não muda as boas, mas também quase não aceita
  nada.
- A causa está na entrada: colunas que faltam na leitura (já vistas na imagem do room 335 e
  do giant steps, rodadas 2009 e 2011) e, talvez, ataques fracos no áudio. O alinhador
  recusar essas páginas é o comportamento certo. O conserto é o da leitura (decisão 2004).
- Ideia não medida: um termo de andamento que não puna buracos de 2T, 3T…, que é o que uma
  coluna perdida produz.

## Consequências

1. O alinhador fica como está (v2.1).
2. Proposta pequena: o alarme de leitura passa a ignorar exibições cujo trecho caiu todo na
   margem. Isso tira 8 alarmes falsos dos 42, e a lista de telas da decisão 2004 perde, por
   exemplo, room 335 telas 6, 24, 31 e 34 e giant steps telas 13 e 15. Ainda não feito.

## Limites

- 6 casos e 2 vídeos ruins; só 1 par de gêmeas.
- Os tempos novos da sensibilidade não foram conferidos de ouvido.
- A aceitação contou só ≥ 4 casadas, sem o limiar de cos 0,40.
- Não dá para separar coluna faltando de ataque faltando sem gabarito.
