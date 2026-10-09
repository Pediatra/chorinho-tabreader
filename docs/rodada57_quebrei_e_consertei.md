# Rodada 57 — quebrei o gerador e consertei na mesma rodada; o portão segurou de novo

## 1. O que aconteceu

Tentei inserir no `tools/sintetico.py` a barra de técnica que **atravessa** o algarismo. A inserção
saiu com **indentação errada** e o arquivo passou a **não compilar** (`IndentationError`, linha 286).

**Remédio imediato:** removi as 4 linhas inseridas e verifiquei, nesta ordem:

| verificação | resultado |
| --- | --- |
| `ast.parse` (sintaxe) | **OK** |
| `import sintetico` | **OK** |
| medição roda de novo | **OK** (683 tokens contados) |

O gerador está íntegro. Nada foi deixado quebrado.

## 2. O portão segurou outra vez

| | |
| --- | --- |
| tokens | 683 |
| receberiam o rótulo `tecnica` | **22 (3,2 %)** |
| limiar que eu estabeleci | 10 % |
| **treinar?** | **não** |

Com o gerador reparado, a marca continua sendo desenhada **com folga** — ela não encosta no
algarismo, então o token não funde e a classe `tecnica` não nasceria. Treinar aqui seria repetir o
erro da rodada 18.

## 3. O que falta, e agora é preciso

A correção é desenhar a marca **intersectando a tinta do algarismo** — e o meu erro nesta rodada
mostra o cuidado necessário:

1. editar com a **indentação do bloco correto** (a inserção tem de ficar dentro do laço do glifo, no
   mesmo nível do `d.arc`);
2. **verificar `ast.parse` + `import` na mesma rodada** — antes de qualquer medição;
3. medir a fração de tokens com `tecnica`; só treinar se passar de 10 %.

## 4. Estado do goal

| anexo | estado |
| --- | --- |
| **tablatura** — casas | **0,885** bruto · **0,955** sobre os rótulos alcançáveis |
| **canais limpos** | `iwaki` 27/27, `sky` 15/15, `paolo` 30/30 |
| **`raman`** | 13/17 — causa medida (3,2 % no sintético × 74 % no canal) |
| **classe `tecnica`** | rótulo preparado; **não treinada** (o fenômeno não é produzido) |
| **tempo** | faixa (`skyguitar`, 0,16 s) e cor (`cifra club`, 41/41 onsets) |
| **gerador** | **íntegro** (sintaxe e import verificados após o reparo) |

## 5. O que esta rodada vale

Duas disciplinas exercidas, uma delas por necessidade:

- **o portão de medição** evitou um segundo treino inútil;
- **a verificação imediata** pegou um arquivo quebrado — e eu não o deixei assim.

Registro o erro com o mesmo peso do resto: eu ia inserir código sem checar a indentação, e o que
salvou foi medir logo em seguida. A partir daqui, edição de gerador vem com `ast.parse` antes de
qualquer número.
