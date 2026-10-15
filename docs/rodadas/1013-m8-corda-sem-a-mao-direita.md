# 1013 — M8: corda sem a mão direita (decodificador + câmera do braço)

**Data**: 2026-10-15. Plano do dono depois da 1012: pausar a câmera da mão direita e medir
quanto se acerta da corda sem ela, em degraus. Código: `tab/maos_corda_sem_direita.py`
(`python -m tab.maos_corda_sem_direita`). Saída: `data/saida/maos/m8/`.

## Pergunta

Sem a mão direita, quantas notas ficam com a corda errada? O que sobra vem da imprecisão da
posição da mão esquerda ou da ambiguidade dentro da região da mão?

## Montagem

- **Notas**: as que têm `t_ini` nos 4 vídeos de trabalho (retrato, noturno nº 20, lacrimosa,
  glimpse). São 2.437 notas, das quais 2.280 (93,6 %) são ambíguas: têm 2 ou mais cordas
  possíveis pela altura, com casa de 0 a 19.
- **Gabarito**: a corda da tablatura do produto. A altura também vem dela, o que simula um áudio
  perfeito.
- **Ataque**: notas com o mesmo `t_ini` (tolerância de 0,02 s). Num ataque, duas notas nunca
  ficam na mesma corda. Nenhum ataque ficou sem combinação válida.
- **Custo**:
  - α · casa, para nota presa;
  - β · distância à janela da mão;
  - γ se a abertura das casas presas passa de 4;
  - δ · |Δposição| entre ataques, com Viterbi.
  - A corda solta custa zero, com a mão onde estiver.
  - Pesos a priori: α = 1, β = 3, γ = 5, δ = 0,5.
- **Degraus**:

| degrau | o que entra |
| --- | --- |
| D0 | casa mais baixa, nota a nota |
| D1 | decodificador sem câmera |
| D2 | D1 + janela [floor(min) − 1, ceil(max) + 1] das pontas 8/12/16/20 da mão esquerda, projetadas **só** pelo gabarito do braço do dono (q02, q16, q21, q23). Vale só onde a câmera casa com o quadro do gabarito (NCC por translação ≥ 0,8, limiar fixado antes). Fora disso, o D2 vira D1 |
| D3 | teto otimista: janela = mediana das casas presas dos vizinhos a até 1 s, ± 2, **sem** a própria nota, sem o próprio ataque e sem as cordas soltas |

A calibração do braço pela música não entra. Conferido no código: o D2 lê só `braco.json`, e
o D3 exclui o próprio ataque.

## Resultado (pesos a priori)

| vídeo | D0 | D1 | D2 | D3 | erros D0 → D1 → D3 |
| --- | --- | --- | --- | --- | --- |
| retrato | 0,919 | 0,934 | 0,934 | 0,944 | 61 → 50 → 42 |
| noturno | 0,755 | 0,776 | 0,776 | 0,870 | 141 → 129 → 75 |
| lacrimosa | 0,832 | 0,868 | 0,868 | 0,894 | 76 → 60 → 48 |
| glimpse | 0,904 | 0,930 | 0,930 | 0,925 | 63 → 46 → 49 |
| **total (2.437)** | **0,860** | **0,883** | **0,883** | **0,912** | **341 → 285 → 214** |
| ambíguas (2.280) | 0,850 | 0,875 | 0,875 | 0,906 | |

- **Cordas soltas: 690/690 em todos os degraus.** Todo erro está em nota presa.
- **Deixando um vídeo de fora** (grade de α, β e δ): D1 0,888, D2 0,891, D3 0,915. O D1 escolhe
  α = 0,5, δ = 0,5 nas 4 dobras. A diferença entre D2 e D1 está dentro do ruído de 4 vídeos.

### Por que o D2 não ganha nada

- **Cobertura.** A câmera casa com o quadro do gabarito em **96 de 1.470 ataques com nota presa
  (6,5 %)**:

| vídeo | ataques cobertos | cobertura | score mediano |
| --- | --- | --- | --- |
| retrato | 63/473 | 13,3 % | 0,67 |
| noturno | 14/394 | 3,6 % | 0,32 |
| lacrimosa | 2/256 | 0,8 % | 0,58 |
| glimpse | 17/347 | 4,9 % | 0,59 |

  Imagem conferida pelo revisor (`diag_camera.jpg`):
  - no retrato, o enquadramento é o mesmo, mas a mão cobre o braço e derruba o NCC (0,65);
  - no noturno e na lacrimosa, a câmera muda de plano (deslocamento e zoom).

  Um quadro de gabarito por vídeo, casado só por translação e com a mão dentro do modelo, não
  cobre o vídeo.
- **Largura.** Quando a janela entra, ela contém a casa verdadeira em 93–100 % das notas
  presas, mas tem **4,3–5,8 casas de largura**. A alternativa de outra corda fica a 4–5 casas,
  então a janela não desempata.
- **Limiar mais baixo** (0,6, diagnóstico, não oficial): o retrato cobre 358/473 e cai de 50 para
  48 erros; a lacrimosa cai de 60 para 54; o glimpse **piora**, de 46 para 51. Não há ganho
  consistente.

### A decomposição pedida pelo dono

| degrau | erros | janela errada (posição) | janela certa, ambiguidade dentro | sem janela |
| --- | --- | --- | --- | --- |
| D2 | 285 | 0 | 21 | 264 |
| D3 | 214 | 66 | **130** | 18 |

Mesmo com a posição da mão tirada das notas vizinhas (melhor do que a câmera dá hoje), **130
notas (5,3 %)** ficam erradas com a casa certa dentro da janela de ± 2. Essa é a sobra que só
informação da **corda** resolve: a mão direita, o timbre no áudio ou uma janela mais estreita
(o dedo, não a mão).

## Leitura

1. O decodificador sem câmera tira 56 dos 341 erros da casa mais baixa (D0 → D1). Ele é a nova
   referência.
2. A câmera do braço, do jeito que está, não ajuda. O gargalo é **cobertura** (6,5 %), não
   qualidade: onde a janela existe, ela nunca exclui a casa verdadeira.
3. O teto otimista (D3) tira mais 71 erros. Ainda sobram 130 notas de ambiguidade dentro da
   região da mão e 66 de posição.
4. O noturno concentra os erros: 129 dos 285 no D1. É o vídeo com menos cobertura da câmera.

O "casa mais baixa acerta 88 % dos empates" da 1012 era de uma amostra de 120 ataques. Em todas
as 2.280 notas ambíguas, o D0 acerta 85,0 %.

## Limitações

- O instante da janela é o `t_ini` do marcador, que vem 165–275 ms antes do som. As pontas da
  mão só existem nesse instante (`pontas_*.json`). Medir no `t_audio` exige rodar o detector de
  novo.
- A saída guarda só contagens, não a predição por nota. Quem precisar nota a nota importa o
  módulo; o cache da câmera já está em `data/saida/maos/m8/camera_*.json`.
- A medida cobre 4 vídeos e 1 canal (`sky guitar`).

## Próximos passos

As frentes de pesquisa ([`docs/pesquisa/maos-frentes.md`](../pesquisa/maos-frentes.md)) partem
desta tabela:

- rastrear o braço ao longo do vídeo, com a mão mascarada (cobertura);
- janela por dedo, mais estreita;
- timbre no áudio;
- custo aprendido da tablatura.

Voltar à câmera da mão direita só se essas frentes não reduzirem as 130 notas de ambiguidade.

## Não repetir

- Casar a câmera com o quadro do gabarito por NCC do braço **com a mão dentro do modelo**: a
  mão derruba o score até com o mesmo enquadramento.
- Janela [floor(min) − 1, ceil(max) + 1] da mão inteira para desempatar corda: larga demais
  (4–6 casas).
