# 2006 — Formato `chorinho/som@1`: as notas que o som tem, sem a tela

**Data**: 2026-10-21. **Estado**: decisão da trilha áudio. O formato é da trilha áudio e não
edita o esquema de nenhuma outra trilha. **Origem**: rodada [2019](../rodadas/2019-transcritor-livre-riley.md)
(o transcritor do Riley passou) e decisão [2005](2005-validacao-cruzada-tela-som-maos.md)
(triangulação, Regra 2).

## Contexto

- A triangulação pede uma fonte "som" que **não use a tela** (Regra 1 da 2005). O
  transcritor de violão do Riley (`guitar-fl.pth`, pesos MIT) passou nos critérios da 2019:
  revocação 0,804, precisão 0,877, acorde cheio 4/6 e escuta 30/31.
- O `chorinho/audio@1` (decisão 2003) é outra coisa: ele dá o `t_audio` **das colunas da
  tela** e depende do produto da tablatura. O som livre depende só do vídeo.

## Opções

1. **Campos novos no `chorinho/audio@1`.**
   - Contra: mistura uma fonte que depende da tela com uma que não depende, e o arquivo
     teria de ser refeito a cada leitura nova da tela.
2. **Um arquivo por vídeo, `chorinho/som@1`, que só depende do áudio.**
   - A favor: ele se gera uma vez por vídeo e por versão do transcritor, e vale para
     qualquer leitura da tela, das mãos ou da partitura.
   - Contra: quem cruza junta mais um arquivo. Isso é justamente o que a etapa de
     cruzamento faz.

## Decisão

**Opção 2.** Um arquivo por vídeo e por transcritor:

```json
{
  "esquema": "chorinho/som@1",
  "video": "<caminho relativo no acervo>",
  "chave_cache": "<chave do cache de áudio: relativo|tamanho|mtime>",
  "t_amostra0": 0.0,
  "transcritor": {
    "nome": "riley-guitar (CRNN de alta resolução)",
    "pesos": "guitar-fl.pth",
    "pesos_sha256": "50d93dba…",
    "limiares": {"onset": 0.3, "offset": 0.3, "frame": 0.1, "pedal_offset": 0.2},
    "torch": "2.5.1+cpu"
  },
  "afericao": {"rodada": "2019", "revocacao": 0.804, "precisao": 0.877},
  "notas": [{"t_ini": 12.3456, "t_fim": 12.9, "midi": 64, "velocidade": 77}],
  "fora_do_violao": []
}
```

Regras:
- **Nada da tela entra.** O arquivo depende só do áudio do vídeo (Regra 1 da 2005). O capo
  também fica de fora: altura é altura.
- **`t_ini` e `t_fim`** estão no tempo do **vídeo** (`t_amostra0` + tempo no áudio), a
  mesma linha do `t_ini` da tela e do `t_audio`.
- **`midi`** é a altura ouvida, em semitons. O som não sabe a corda.
- **`velocidade`** (0–127) é a saída do modelo, e **não é probabilidade**. Cada nota leva
  também `amplitude` = velocidade / 127, só para a régua `tab.audio_som_medir` aceitar os
  dois transcritores. A probabilidade calibrada que a Regra 2 pede vem depois, medida no
  cruzamento.
- **`fora_do_violao`**: notas fora de MIDI 40–88. Ficam guardadas, nada some.
- **Onde fica**: `data/saida/audio/som/<slug>.som.json`. Ele é regenerável, então não vai
  para o git.
- **Quem gera**: `tab.audio_transcrever_riley`, na imagem `chorinho-som:dev`.
- **Versão**: trocar de transcritor ou de pesos gera outro arquivo, com o seu `transcritor`.
  A aferição só vale para os pesos medidos.

## Consequências

- `tab.audio_transcrever_riley` passa a gravar `chorinho/som@1`, com `pesos_sha256` e
  `afericao`. O Basic Pitch (2018, reprovado) fica no formato provisório.
- O cruzamento tela × som lê o produto da tela e o `chorinho/som@1`, e nada mais.
- A trilha mãos e a trilha partitura podem ler o mesmo arquivo para as conferências delas.
  Ele não depende de nenhuma das duas.
