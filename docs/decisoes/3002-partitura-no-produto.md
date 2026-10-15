# 3002 — P3: como a partitura entra no produto

Estado: **proposta da trilha partitura**. O esquema (`tab/esquema.py`, `chorinho/video@1`) e
`tab/musicxml.py` são da trilha tablatura. Esta proposta não os edita.

## Contexto

- A saída de `python -m tab.partitura_pareamento` tem uma lista de eventos por recorte de
  pauta (rodadas 3010–3013):
  - leitura do Audiveris com a armadura do vídeo;
  - notas do homr confirmadas pela tab;
  - notas que a tab desmente, guardadas em `trocadas`;
  - um par com a coluna da tab, conferido pelo x do quadro (336 de 337 no mesmo x).
- O que a partitura acrescenta à tab é **ritmo** (figura, ponto, ligadura, compasso, voz) e a
  altura escrita. O ritmo lido está certo em ~99 % dos símbolos (rodada 3004).
- O **tempo** não é medido pela partitura. Pela regra do dono, ele vem da coluna da tab
  pareada (`t_ini` da nota no produto).
- Hoje o pareamento usa o **gabarito** da tab (`data/gold/ouro_video`), que agrupa por x e não
  traz `t_ini`. O produto (`chorinho/video@1`) tem `tela`, `passagem`, `exibicao`, `coluna` e
  `t_ini` por nota.

## Opções

1. **Campos novos por nota** no `chorinho/video@2`: `figura`, `pontuada`, `compasso_pauta`...
   - A favor: um arquivo só.
   - Contra: muda o esquema da outra trilha.
   - Contra: nota da pauta sem par na tab (pausa, nota que a tab não tem) não teria onde
     ficar.
2. **Arquivo irmão** `<produto>.partitura.json`, esquema `chorinho/partitura@1`, com uma
   entrada por evento da pauta e a chave da coluna da tab pareada.
   - A favor: não toca no `chorinho/video@1`, e cada trilha regera o seu arquivo.
   - A favor: guarda pausa, evento sem par, origem da nota e trocas.
   - Contra: quem consome junta dois arquivos.
3. **Copiar `t_ini` para a partitura.**
   - Contra: duplica o tempo. Quando a trilha tablatura conserta o tempo, a cópia fica velha.

## Proposta

**Opção 2**, sem copiar tempo. Quem consome busca o `t_ini` no produto pela chave da coluna.
É o mesmo desenho da decisão 2003 (áudio).

```json
{
  "esquema": "chorinho/partitura@1",
  "produto": "<caminho do chorinho/video@1 usado>",
  "produto_sha256": "…",
  "gerado_por": {"leitor": "audiveris x2_margem + armadura do vídeo",
                 "completar": "homr nativo confirmado pela tab", "commit": "…"},
  "pautas": [
    {"tela": 3, "caixa_quadro": [0, 578, 1920, 894], "entrelinha": 19.0,
     "fifths": 4, "fifths_origem": "leitura | video",
     "compassos": [{"numero": 1, "fracao": "4/4", "x_quadro": 290.0}],
     "eventos": [
       {"compasso": 1, "t": 0.0, "x_quadro": 317.0,
        "par": {"tela": 3, "coluna": 1, "distancia_x": 1.5, "confere_x": true},
        "simbolos": [{"nome": "A4", "midi_escrito": 69, "figura": "quarter",
                      "pontuada": false, "voz": "1", "ligadura_inicio": false,
                      "ligadura_fim": false, "notacoes": [], "origem": "audiveris"}],
        "trocadas": []}
     ]}
  ],
  "resumo": {"eventos": 0, "com_par": 0, "com_x_conferido": 0, "notas_homr": 0,
             "trocadas": 0}
}
```

Regras:

- **Chave de junção:** `(tela, coluna)` do `chorinho/video@1`. O `t_ini` de cada passagem e de
  cada exibição sai das notas do produto com essa chave. Uma coluna tocada em duas passagens
  dá dois instantes para o mesmo evento da pauta, como na tab.
- **Evento sem par** (pausa, nota que a tab não tem) fica com `par: null`. Nada é descartado,
  como na regra do glifo cru.
- **Altura escrita, não soada:** `midi_escrito` é a nota como está desenhada (violão soa uma
  oitava abaixo). A altura que soa continua sendo a da tab.
- **`origem` e `trocadas` ficam no arquivo.** O consumidor sabe que nota veio de que leitor e o
  que a tab corrigiu.
- **Vídeo sem tab** (R13–R21, 8 canais): o mesmo arquivo, com `par: null` em tudo, sem homr
  confirmado e sem troca. Esses eventos têm ritmo e não têm tempo.

## O que falta para gerar o arquivo de verdade

1. **Parear com o produto em vez do gabarito.** As colunas viriam de `notas[].coluna` por
   tela, em vez do agrupamento por x de 6 px. Cabe à trilha partitura, que só lê o produto.
2. **Recortar todas as telas de pauta do vídeo**, não só os 21 recortes da P1. Tem de achar
   a pauta acima do retângulo da tab em cada tela do produto.
3. **`t_ini` aferido no produto desses vídeos.** Depende da trilha tablatura: hoje a
   `fase8/medida` dos vídeos com pauta tem 0 notas com tempo.

## Consequência

- A trilha tablatura não muda nada até o dono aprovar um esquema único.
- Se um dia as trilhas quiserem um arquivo só, a opção 1 nasce desta, com a mesma chave.
