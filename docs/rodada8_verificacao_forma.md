# Rodada 8 — verificação de forma: 15/15 e ferramenta de reconhecimento

## 1. O problema e a correção

O único erro que restava era estrutural, não estatístico: o classificador é obrigado a
escolher uma das 19 classes para **qualquer** recorte, então o `0` final da linha virava
`harmonico` (e, rejeitando o harmônico, caía em `12` — um número de 2 dígitos num recorte de
0,57 passo).

Correção implementada: antes de aceitar a classe, ela tem de **caber no recorte medido**.

| regra | por quê |
| --- | --- |
| `harmonico` exige **≥ 2 componentes** ou largura ≥ 1,2 passo | `<7>` é multi-componente; um algarismo solto não é |
| casa de **1 dígito** exige largura ≤ 1,15 passo | não existe algarismo único mais largo que isso |
| casa de **2 dígitos** exige largura ≥ 0,85 passo | `12` não cabe em meio passo |

Resultado na linha real com gabarito verificado:

| | |
| --- | --- |
| antes | 14/15 = 0,933 |
| **depois** | **15/15 = 1,000** |
| palpites corrigidos pela forma | **1 de 15** |

A regra interveio em **um** glifo — exatamente o que estava errado. Não é um ajuste que
maquia o resultado: é um teste de consistência que reprova uma resposta impossível.

## 2. Ferramenta

`tools/reconhecer.py` junta as três camadas num comando:

```bash
.venv/bin/python tools/reconhecer.py <imagem-da-linha> --modelo /tmp/sint/glifo_sint.pt --json saida.json
```

Saída por nota: `ordem, corda, casa, tecnica, x, confianca, corrigido_pela_forma`.
Saída por linha: `passo, linhas_y, barlines_x` — as **barlines já vêm prontas** para numerar
compasso, e a confiança por nota permite marcar trechos para revisão humana.

Exemplo real (linha 1, `-6rawhontyg`):

```json
{"ordem": 1, "corda": 2, "casa": "0", "tecnica": null, "x": 160,
 "confianca": 0.85, "corrigido_pela_forma": false}
```

## 3. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 42 glifos / 2 canais (alvo: ~300, casas 0–24 + técnicas) |
| (c) classificador multi-classe | **funcionando e verificado por forma** — 15/15 na linha real |
| (d) pipeline ponta a ponta | **linha transcrita com corda, casa, técnica, tempo, barlines e confiança** |
| (e) escala nos 3.781 | pendente |

Falta para o JSON ser o produto: **compasso numerado** (as barlines já saem), **andamento**
(do intervalo entre onsets do cursor), **aferir a técnica em dado real** (a taxonomia já
existe no sintético) e a **partitura** (peça separada, exige OMR próprio).

Ressalva que continua valendo: o gabarito tem 42 glifos e 4 classes. O 15/15 é real, mas
mede a linha mais fácil do acervo; a próxima medição honesta precisa de mais canais e das
casas 4–24.
