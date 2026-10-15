# 3019 — `ler --pasta`: partitura de vídeo sem produto da tab

Trilha partitura. Data: 2026-10-15.

## O que é

Muitos vídeos têm pauta e não têm produto de tablatura. Para eles, o `paginar` (rodadas
3016–3018) já acha as páginas e recorta as pautas. Faltava ler esses recortes e gravar a
partitura.

```bash
# imagem chorinho-partitura:dev, CPU (o serviço chorinho do compose não tem Audiveris)
podman run --rm --security-opt label=disable -e PYTHONPATH=/app -w /app -v "$PWD":/app \
    chorinho-partitura:dev python -m tab.partitura_video ler --pasta data/saida/partitura/sem_produto/<slug>
```

## Mudanças (`tab/partitura_video.py`)

- `ler` aceita `--pasta` como alternativa a `--produto`. Os dois são exclusivos e um é
  obrigatório.
- `ler_pasta` roda **só o Audiveris** (`x2_margem`) e aplica a armadura do vídeo
  (`herdar_condicao`), como o `ler` com produto. Não roda o homr, porque sem a tablatura
  não há como confirmar a nota que ele propõe.
- O documento `chorinho/partitura@1` é gravado em `<pasta>/<slug>.partitura.json`, com
  `produto` e `produto_sha256` nulos. Cada pauta leva `pagina`, `letra`, `exibicoes`,
  `caixa_quadro`, `entrelinha`, `fifths`, `compassos` e `eventos`.
- Cada evento sai com **`par` nulo** e sem tempo em segundos. O `t` é a posição em semínimas
  dentro do compasso. O tempo da partitura só vem do pareamento com a tablatura, e aqui não
  há tablatura. As `exibicoes` da página dizem quando ela está na tela.
- `_recortes_escolhidos` passou a ser compartilhado por `ler` e `ler_pasta`.
- 9 testes novos, com o Audiveris isolado por monkeypatch:
  - só o Audiveris é chamado, uma vez por recorte;
  - um id desconhecido não chega a rodar o leitor;
  - recorte sem leitura sai com `erro`;
  - documento sem par;
  - a CLI recusa nenhum dos dois argumentos e recusa os dois juntos.

## Medição (piloto, 3 vídeos)

| vídeo | Audiveris ok | pautas | eventos | com erro | tempo |
| --- | --- | --- | --- | --- | --- |
| agua de beber | 10/10 | 10 | 403 | 0 | 191 s |
| athletic theme | 7/8 | 8 | 301 | 1 | 92 s |
| canon de pachelbel | 6/6 | 6 | 112 | 0 | ~90 s |

São cerca de 18 s por recorte, em CPU. A falha do athletic (P05a) é do Audiveris, que saiu
com código 1 e não gerou MusicXML. A pauta aparece no documento com `erro`.

Olhei 3 recortes contra a leitura:

- **agua P01a**: está em dó, e a leitura vem sem `<key>` (`fifths` nulo), o que está certo.
  São 30 eventos em 7 compassos, plausível para a imagem.
- **canon P01a**: são 4 compassos com 2 díades de mínimas cada, 16 notas. O Audiveris leu 3
  compassos e 5 notas, e 2 eventos entraram no documento. **Perda grande de leitura.**
- **canon P06a**: a armadura tem 2 sustenidos e a leitura veio sem armadura. A herança só
  vale para recortes sem clave, e esse tem clave, então ficou `fifths` nulo. Os outros 5
  recortes do canon leram 2.

## Limites

- Sem gabarito para esses vídeos: a qualidade da leitura **não está medida**. O número da
  cadeia segue sendo o da 3014, em vídeos com produto.
- `fifths` nulo mistura dois casos: "sem armadura" (dó) e "armadura não lida".
- Sem tablatura para conferir, o Audiveris perde notas e ninguém corrige (canon P01a).
- A herança da armadura do vídeo não cobre recorte com clave e leitura sem armadura
  (canon P06a).
