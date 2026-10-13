# 2003 — A5: como o tempo do áudio entra no produto

Estado: **proposta da trilha áudio**. O esquema (`tab/esquema.py`, `chorinho/video@1`) é da
trilha tablatura; esta proposta não o edita.

## Contexto

- O `t_ini` de hoje vem do **marcador** e só existe em exibição com `tempo.medido = true`.
  No MVP, o som vem 60–324 ms depois do marcador, vagueando, ±90 ms nota a nota (rodada
  2003): `t_ini` é instante de **animação**, não de som.
- Vídeo sem marcador tem exibição com `t0`/`t1` mas sem passagens: as notas ficam sem
  `t_ini` e sem `exibicao`.
- O alinhador v2 (`tab/audio_alinhar.py`, rodada 2004) dá, por (tela, exibição, coluna),
  `t_audio` ou um motivo de recusa (`fora_do_trecho`, `sem_ataque`, exibição recusada), mais
  `cos` e `confianca`. Cobertura nos sem marcador: iwaki 245 de 273 colunas, kimny 158 de
  222, shin izumi 114 de 552 (23 de 42 exibições recusadas).
- Verdade disponível: escuta do dono (`data/gold/audio/`), que certifica **coluna certa**,
  não ±50 ms (rodada 2007). Folhas 1+2, sem marcador: 30 certos, 1 errado, 7 não sei.

## Opções

1. **Campos novos por nota** no `chorinho/video@2`: `t_audio`, `t_audio_confianca`,
   `origem_tempo` (`marcador` | `audio` | `ambos`).
   - A favor: um arquivo só.
   - Contra: muda o esquema da outra trilha, e o produto passa a depender do alinhador para ser regerado.
   - Contra: uma nota de vídeo sem marcador não tem `exibicao`, e o campo teria de ser criado também.
2. **Arquivo irmão** `<produto>.audio.json`, esquema `chorinho/audio@1`, uma entrada por
   (tela, exibição, coluna). O tempo vale para todas as notas da coluna.
   - A favor: não toca no `chorinho/video@1`; cada trilha regera o seu.
   - A favor: guarda recusas com motivo.
   - Contra: quem consome junta dois arquivos.
3. **Sobrescrever `t_ini`** com o tempo do áudio.
   - Contra: perde o marcador, que é a única fonte de identidade de coluna por passagem e de repetição (casas de volta).
   - Contra: mistura duas grandezas diferentes no mesmo campo.

## Proposta

**Opção 2 agora**; opção 1 só quando a precisão estiver medida (folha A/B) e as duas trilhas
quiserem um arquivo só.

Formato proposto (`chorinho/audio@1`):

```json
{
  "esquema": "chorinho/audio@1",
  "produto": "<caminho do chorinho/video@1 usado>",
  "produto_sha256": "…",
  "video": {"arquivo": "…", "t_amostra0": 0.0},
  "gerado_por": {"metodo": "onsets_v2", "commit": "…", "parametros": {}},
  "exibicoes": [
    {"tela": 1, "exibicao": 0, "trecho_colunas": [1, 24], "T_s": 0.65,
     "recusada": false, "motivo": null}
  ],
  "colunas": [
    {"tela": 1, "exibicao": 0, "coluna": 3, "t_audio": 245.08,
     "confianca": 0.82, "cos": 0.71, "motivo": null}
  ],
  "afericao": {"gabarito": ["data/gold/audio/folha1.json", "data/gold/audio/folha2.json",
               "data/gold/audio/folha3.json"],
               "nivel": "ms", "resolucao_escuta_ms": 100}
}
```

Regras:

- Uma coluna recusada aparece com `t_audio: null` e `motivo`. Nada é descartado, como na
  regra do glifo cru.
- `t_audio` é instante de **ataque do som**, na linha do tempo do vídeo (a mesma do
  `t_ini`), já com a convenção `t_amostra0` do A0. O viés do detector (−28 ms, rodada
  2002) **não** é descontado: a escuta não separa abaixo de ~50–100 ms (rodada 2008).
- `afericao.nivel` diz ao consumidor o que foi verificado. Era `"coluna"` (folhas 1 e 2:
  a nota certa, não o milissegundo); passou a `"ms"` com `resolucao_escuta_ms = 100` depois
  da folha A/B (rodada 2008): 200 e 100 ms separados pelo dono, 50 ms não.
- Quem junta: chave (tela, exibicao, coluna). No vídeo com marcador, a `exibicao` da nota
  já existe; no vídeo sem marcador, a nota recebe `exibicao` pelo trecho da exibição
  (`t0`–`t1`), feito por quem consome (ou por um `tab.audio_juntar` da trilha áudio).
- Repetição dentro da exibição (mais de uma passagem) não é tratada pelo alinhador v2.
  O arquivo só tem a primeira passagem; isso é declarado em `gerado_por`.
- `produto_sha256` amarra o arquivo ao produto: se a tablatura for regerada, o `.audio.json`
  fica velho e é detectável.

## Consequência

- A trilha áudio cria `tab/audio_produto.py` (escreve e valida `chorinho/audio@1`) e roda
  nos produtos que já existem; nenhum arquivo da trilha tablatura muda.
- Pendências que melhoram o arquivo, todas fora desta decisão:
  - ornamento e arco no produto (decisão 2002);
  - folha A/B para medir a precisão em ms;
  - repetição dentro da exibição.
- Se o dono preferir a opção 1, o pedido de mudança de esquema vai para a trilha tablatura
  com este formato como base.
