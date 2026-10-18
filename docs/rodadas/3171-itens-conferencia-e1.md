# 3171 — E1: itens da conferência do dono (porta 8122)

Frente E, itens para a conferência, a partir da main (80ec5487, com a E1 já mesclada).

**O que entra.** Só os símbolos que o dono confere:
- as notas completadas pela tab **com figura** (22 de 56 contadas na 3170); as 34 com figura
  `null` ficam fora e contadas à parte, como pediu a sessão principal;
- as 32 notas do homr de R01–R12 que o pareamento acrescentou (`origem` `homr`).

**Itens gerados** (`tab/partitura_completar_itens.py`, saída em `data/saida/part_frentes/fe_completar/`):
- `itens_e1.json`: 17 itens (um por recorte com símbolo a julgar), formato 1;
- `ouro_e1_copia.json`: cópia vazia do gabarito. O gabarito real (`data/gold`) não é tocado.

**Teste.** `python -m tab.partitura_gabarito servir --itens ... --ouro ... --porta 8122 --host 0.0.0.0`
num container de teste, com `-p 127.0.0.1:8122:8122`. A página respondeu 200 dentro do container.
O container foi parado depois.

**Limites declarados.**
- As notas completadas não estão no MusicXML, então não aparecem desenhadas na partitura. Aparecem
  como símbolos na lista de cada compasso, com a origem `tab_completada`. O dono confere pelo
  recorte e pela lista.
- As notas do homr também não estão no MusicXML da leitura; ficam na lista, com origem `homr`.
- A figura de cada item é a da própria voz (correção da 3170). Notas cuja voz não existe na
  leitura não entram, porque a figura não tem de onde vir.

**Conferência.** O dono marca cada símbolo como `certo` ou `figura_errada` (os dois estados que
a E1 usa). A medida é do dono; nada aqui é aceito por mim.
