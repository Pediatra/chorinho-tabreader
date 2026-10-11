# 0009 — Canais fora da Fase 8: `violaodecria` e `tv cifras`

## Contexto

A Fase 8 (T8.1, `docs/guias/plano-do-produto.md`) escolhia o ouro de vídeo ampliado pelo
peso no acervo. A lista proposta tinha `violaodecria` (1.037 vídeos, o maior canal) e
`tv cifras` (522). Os dois quase não foram medidos, e o plano pedia para confirmar no censo
se havia tablatura antes de entrar.

O censo com cache (parcial: 3.589 de 5.015 vídeos) e as folhas olhadas pelo coordenador
(`data/saida/censo/olhar/violaodecria_0.jpg` e `violaodecria_1.jpg`) mostraram:

- **`tv cifras`**: 51 de 537 vídeos com tablatura. Quase só violão filmado e diagrama de acorde.
- **`violaodecria`**: 216 de 311 marcados com tablatura, mas:
  - são vídeos curtos verticais (15 a 60 s), formato TikTok;
  - a tablatura é **texto (ASCII)** minúscula no topo da tela, não a tablatura gráfica da cadeia;
  - o conteúdo é de acordes e batida, e vários vídeos não têm relação com violão;
  - a contagem está inflada: partitura de ritmo foi contada como TAB.

Tab em texto (ASCII) exige leitor próprio e está fora desta cadeia (`AGENTS.md`, "Limites
conhecidos").

## Opções

1. **Manter os dois no ouro da Fase 8**, como no T8.1. O ouro teria TAB que o pipeline não
   lê (`violaodecria`) e vídeos quase sem tablatura (`tv cifras`). A medição sairia
   contaminada e o rollout herdaria um número de cobertura falso.
2. **Tirar os dois do ouro e da primeira rodada de transcrição em massa.** (escolhida)
3. **Manter `violaodecria` como canal de "tablatura em texto"** para estudar depois. Exige
   um leitor que não existe; adiar não custa nada agora.

## Decisão

Opção 2. Decisão do dono do projeto, por escrito no chat, em 2026-10-11: `violaodecria` e
`tv cifras` ficam **fora** do gabarito da Fase 8 e da primeira rodada de transcrição em massa.
Nenhum código em `tab/` muda.

## Consequência

- `configs/canais.yaml` marca os dois com `rollout: fora` e `motivo`. Nenhum código lê esse
  arquivo (verificado por busca), então a marca é documental.
- O T8.1 passa a ter **7 canais** no ouro (`sky guitar`, `guitar dell'arte`, `cifra club`,
  `leonardo ramos`, `robert lunn`, `mr. tabs`, `iwaki`). Isso cumpre o mínimo de "≥ 7 canais"
  no limite: sair mais um canal do ouro quebra o critério.
- A escolha final do ouro sai do **censo completo**, não desta lista. Se o censo final mostrar
  outro canal com tablatura gráfica e peso, ele pode entrar, por decisão nova.
- A contagem de `violaodecria` (216 de 311) **não serve** como número de cobertura.
- Volta possível: se um dia houver leitor de tablatura em texto, `violaodecria` volta à Fase 8
  por decisão nova (esta não é editada).
