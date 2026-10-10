# 0008 — Qual modelo o produto usa (`MODELO_PADRAO`)

## Contexto

O produto (e o `tab.avaliar`) usavam `MODELO_PADRAO = artefatos/glifo_sint.pt`. Medido em
2026-10-10 (Fase 0 / T0.2, comando em §Comando):

| modelo | no gabarito de 72 glifos | procedência |
| --- | --- | --- |
| `artefatos/glifo_sint.pt` | **72/72 = 1,000** | **desconhecida** — não está na tabela do `artefatos/LEIA-ME.md`; não se sabe qual semente/comando o gerou |
| `artefatos/oficial_2/glifo_sint.pt` | 71/72 = 0,986 | semente 2, registrada |
| `artefatos/oficial_3/glifo_sint.pt` | **68/72 = 0,944** | semente 3, registrada (a **mediana**) |
| `artefatos/oficial_1/glifo_sint.pt` | 66/72 = 0,917 | semente 1, registrada |

**Perfeição no próprio gabarito que serve de régua não é qualidade: é sinal de sobreajuste à régua.**

## Opções

1. **Manter `glifo_sint.pt`** — melhor número na régua (1,000), **procedência desconhecida** e suspeita
   de contaminação pela régua;
2. **Apontar para a melhor semente** (`oficial_2`, 0,986) — escolher a melhor **pelo gabarito** é
   sobreajustar a régua (o próprio plano proíbe);
3. **Apontar para a semente mediana** (`oficial_3`, 0,944) — decisão do plano (`docs/guias/plano-do-produto.md`,
   T0.2);
4. **Comitê das 3 sementes** (média das probabilidades) — **opcional**, só se medido e ≥ à mediana no
   `tab.avaliar` **e**, depois da Fase 2, no ouro de vídeo.

## Decisão

**Opção 3**: `MODELO_PADRAO = ARTEFATOS / "oficial_3" / "glifo_sint.pt"` (semente **mediana**, 0,944).

## Consequência

- o produto passa a usar um modelo com **procedência registrada** (semente 3, treino determinístico);
- a leitura do algarismo **muda** em relação ao `glifo_sint.pt`: de 1,000 para **0,944** na régua. É a
  **queda esperada e aceita** — o 1,000 não era crível como medida de qualidade, e o plano não escolhe
  modelo pelo gabarito;
- `artefatos/glifo_sint.pt` **fica no repositório** (artefato não se apaga) e segue sendo comparável;
- o comitê fica em aberto, com o critério de adoção escrito na opção 4;
- **a régua não muda**: `tab.avaliar` continua reportando as 3 sementes oficiais, e o `MODELO_PADRAO` só
  decide o que o **produto** lê.

## Comando

```bash
export DOCKER_HOST=unix:///run/user/1000/podman/podman.sock
C="docker compose -f compose.yaml -f compose.podman.yaml"
$C run --rm chorinho python -m tab.avaliar --modelo artefatos/glifo_sint.pt        # 72/72 = 1,000
$C run --rm chorinho python -m tab.avaliar                                        # usa o MODELO_PADRAO novo
```
