# Rodada 12 — tentativa que falhou (e o que ela ensinou)

## 1. O que eu tentei

Para matar o erro `7` + slide → `24` (canal `raman korshun`), impus que uma classe de
**2 dígitos** exigisse **dois componentes com altura de algarismo** (≥ 0,5 passo), raciocinando
que o risco do slide seria um fragmento fino e baixo.

## 2. Resultado medido

| canal | antes | depois |
| --- | --- | --- |
| iwaki | 27/27 = 1,00 | 27/27 = 1,00 |
| sky guitar | 15/15 = 1,00 | 15/15 = 1,00 |
| raman korshun | 12/24 = 0,50 | 12/24 = 0,50 |
| **TOTAL** | **54/66 = 0,818** | **54/66 = 0,818** |

O erro só mudou de forma: `24` virou `2`. **Não melhorou nada.**

## 3. Por que falhou — e é isso que vale

Minha premissa estava errada. Olhando os recortes do `raman korshun`, **o slide é uma
diagonal que atravessa toda a altura do algarismo** — não um fragmento baixo. Então o critério
de **altura** não separa nada: o slide conta como "componente com altura de algarismo" e a
regra continua autorizando a classe de 2 dígitos.

O critério certo é de **orientação**, não de tamanho:

- um **algarismo** tem pelo menos uma coluna com um traço vertical longo (a haste do `1`, a
  lateral do `7`) — a tinta é concentrada em poucas colunas;
- uma **diagonal** não tem nenhuma coluna com traço longo: a tinta se espalha por muitas
  colunas, cada uma com pouca altura.

Ou seja: `partes_digito` deve contar componentes que tenham **uma coluna com traço ≥ 0,6 da
altura**, não componentes altos. Isso exige guardar a máscara de cada componente (hoje o
`Glifo` só guarda a caixa), e é a correção a implementar.

Registro isto como está, sem inflar: a regra atual ficou no código porque é inofensiva (não
quebrou nenhum dos dois canais que estavam em 1,00), mas **ela não resolve o problema** e o
número do sistema continua **0,818**.

## 4. Estado do goal

| etapa | estado |
| --- | --- |
| (a) inventário do acervo | **feito** — 96 % com tablatura, 95 % com cursor |
| (b) gabarito verificado | 66 glifos / 3 canais / 9 classes |
| (c) classificador multi-classe | **0,818 real** — 2 erros de lixo→algarismo e 2 de slide→2 dígitos, por canal |
| (d) pipeline ponta a ponta | corda, casa, técnica, tempo, compasso e andamento |
| (e) escala nos 3.781 | pendente |

Próximos passos, em ordem de custo/benefício:

1. **orientação do componente** (coluna com traço longo) para separar algarismo de slide —
   correção precisa e de baixo risco;
2. **classe de rejeição** treinada no sintético com fragmentos de barline e resto de corda
   (resolve os 2 erros de lixo→algarismo);
3. reaferir os 3 canais (esperado: acima de 0,95);
4. ampliar o gabarito para 0–24 e os 12 canais;
5. rodar em escala.
