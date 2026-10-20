# 0210 — Diagnóstico: o recorte do painel apaga os arcos acima da corda 1

Segue a [0207](0207-r4d-t82-no-ajuste-fino.md), a [0208](0208-r4e-cadeia-e-arco-alto.md) e a
[0209](0209-r4f-metade-da-t83.md). É um diagnóstico, sem treino novo e sem mudança no produto.

## O que foi visto

- `painel.candidatos` recorta o grupo de 6 linhas com **1 passo** de folga em cima e embaixo
  (`margem = round(passo)`).
- O detector lê de 2,5 passos acima da corda 1 a 2,5 passos abaixo da 6
  (`normalizar_sistema`). O que sai do recorte vira a cor da borda: branco.
- `data/saida/tab_rotulo/diag/espaco_acima.py` mede a folga real na T8.3.
  - Em 21 das 33 telas, ela é de 0,7 a 1,0 passo, inclusive no Shin Izumi (0,98) e no
    Transcriptor (0,95).
  - Nas telas lidas pelas faixas fixas, ela passa de 6 passos.
- Os arcos que sobravam nos erros ficam de 1,3 a 2,3 passos acima da corda 1. **Eles nunca
  chegavam ao modelo**: nem na leitura, nem no treino, porque o cache real usa o mesmo recorte.
  O sintético desenha 2,4 passos acima da corda 1, e o real chega em branco ali.

## Medida: mesmos pesos, recorte mais alto

`diag/recorte_alto.py` aumenta o recorte no quadro até 2,5 passos de cada lado. A grade e as
linhas são as mesmas. Os pesos da dobra 0 são lidos na T8.3, com o gabarito corrigido em
2026-10-20, a faixa de 0,15 e `L` 0,02.

| pesos | recorte | "sim" falso | custo | casa | notas-alvo vistas |
| --- | --- | --- | --- | --- | --- |
| `_atqt` | hoje | 8 · 8 · 9 /70 | 31–34 /1417 | 1480–1482 | 0 · 0 · 0 /6 |
| `_atqt` | alto | **5 · 5 · 5 /71** | 26–31 /1414–1417 | 1481–1484 | 4 · 4 · 4 /6 |
| `_atqe` (G11–G12) | hoje | 8 · 10 · 10 /70–71 | 37–41 /1416 | 1479–1482 | 0 · 0 · 0 /6 |
| `_atqe` (G11–G12) | alto | **3 · 4 · 3 /70–71** | 35–36 /1416 | 1480–1484 | 6 · 5 · 6 /6 |

## O que muda nas conclusões

- A parada da 0208 e da 0209 foi medida com o recorte que apaga os arcos. "O gerador não ensina"
  e "nem exemplo do mesmo canal ensina" **não valem**: o modelo não recebia o símbolo.
- Com o recorte alto, o G11–G12 é o que mais ajuda: 3–4 /71, perto do aceite de 5 %.
- **Cuidado: a T8.3 foi usada neste diagnóstico.** Ela não serve mais como teste limpo para
  escolher entre as versões.

## Próximo passo (proposta)

1. Recorte alto no produto: um passo único usado pelo `ataque_r4.ler_tela`, pelo `tab.video` e
   pelo cache do treino. O recorte é parte da medição (regra 9 do AGENTS), então a casa dos ouros
   tem de ser remedida.
2. Remontar o cache real (ouros, T8.2 e T8.3) com o recorte alto e retreinar o `_atqe`.
3. Escolher os limiares nos ouros, como sempre, e validar num lote novo (T8.4), que vira o teste
   limpo.
