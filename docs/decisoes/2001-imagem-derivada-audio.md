# 2001 — Imagem derivada da trilha áudio (`chorinho-audio:dev`)

## Contexto

A trilha áudio precisa de figuras (espectrogramas) e, provavelmente, de bibliotecas de
áudio no A2. A imagem `chorinho:dev` é compartilhada e não pode mudar por causa de uma
trilha (a das mãos se queimou quando um pacote trocou o `cv2`; decisão 1001).

## Opções

1. Pôr matplotlib no `requirements.txt` da base.
2. Desenhar com `cv2` na base.
3. Imagem derivada só da trilha áudio.

## Decisão

Opção 3: `Dockerfile.audio`, `FROM docker.io/library/chorinho:dev`, com matplotlib 3.11.2
e dependências fixadas, instalados com `--no-deps` (o pip, sem isso, trocava numpy 2.5.2
por 2.5.4). O build imprime numpy/PIL/cv2/torch antes e depois e falha se mudarem.

```bash
podman build -t chorinho-audio:dev - < Dockerfile.audio
```

Sem contexto de build (o Dockerfile não tem COPY), para não enviar `data/saida/`.

## Consequências

- Só `tab/audio_figuras.py` importa matplotlib; nenhum teste o importa, e o gate continua
  rodando na base.
- `tab/audio_onsets.py` e `tab/audio_atraso.py` são numpy puro e rodam na base.
- Biblioteca nova do A2 (scipy, librosa…) entra aqui, com o mesmo cuidado de versões.
