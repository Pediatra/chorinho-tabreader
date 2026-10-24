# 1049 — A base das mãos de ponta a ponta num vídeo (o do MVP)

**Data**: 2026-10-23. O pré-registro é commitado antes do código.

**A pergunta**: com as peças que já existem (produto da tablatura, `t_audio` da trilha do
áudio, detector de mãos do M1 e a cadeia do braço da 1047), sai um `chorinho/maos@1`
completo e válido (decisão 1007) para um vídeo inteiro, em quanto tempo de GPU, e com que
fração de eventos ouro, prata e recusado?

**Por que**: o dono congelou o capo (2026-10-23) e pediu para a trilha andar para a base. Esta
rodada é engenharia num vídeo; a medida de contaminação (M14, auditoria de 100 eventos pelo
dono) é a do piloto de 20 vídeos, na rodada seguinte.

## Entradas (nenhuma é calculada pelas mãos)

- **Vídeo**: `sky guitar/retrato brasileiro - tab & lesson.mp4` (679 s, h264, 1920 × 1080).
- **Produto**: `data/saida/tablatura/produto/mvp.json` (`chorinho/video@1`, 763 notas).
- **Som**: um `chorinho/audio@1` gerado pela CLI da trilha do áudio (`tab.audio.produto`),
  sem editá-la, sobre o alinhamento que ela já tem para o MVP. Ela só dá tempo à 1ª
  passagem (`passagens: so_primeira`).
- **Capotraste**: 0, fonte `dono`, **só se o dono confirmar** que o sky guitar não usa capo;
  sem confirmação, `null` e K4 falha em todos os eventos.

**Emenda (antes de medir, 2026-10-23)**: o teste de fumaça (8 s do vídeo, fora da medida)
mostrou que a trilha do áudio dá tempo à passagem **primeira no tempo**, e que a numeração
`passagem` do produto não segue o tempo (a 1ª nota do vídeo é `passagem: 2`). A regra passa a
ser: o `t_audio` de uma coluna vai para a passagem cujo `t_ini` fica mais perto dele; as
outras passagens da coluna ficam com `t_som` `null`. Também: o detector de mãos roda dentro
da `trava_gpu("maos")`.

## O denso (`.maos.npz`)

- **Quadros**: os PTS nativos mais próximos de uma grade de **10 qps** (`leitor.quadros_pts`),
  nas exibições das telas do produto com 1 s de folga de cada lado.
- **Mãos** (todos os quadros): o `DetectorMaos` do M1 (Wholebody + MediaPipe, GPU), com a caixa
  da tablatura da tela. O violonista é destro: a **mão do braço** é a `esquerda` do
  `combinar`, a **do ataque** é a `direita`; `incerto` fica de fora. Trilha: o mesmo lado
  seguido, com nova trilha depois de 0,5 s sem a mão. Corpo: ombros, cotovelos e pulsos da
  pessoa do Wholebody com a maior caixa.
- **Braço** (1 quadro a cada 10, ~1 qps): a cadeia da 1047 (22 hipóteses, validadores, sem a
  tomada), sem mudar nada. `braco_achou` = a cadeia achou; `braco_conf` = 1 se entregue, 0 se
  sinalizado. Nos outros quadros, NaN e `achou` falso.
  - Motivo: a sondagem de custo mediu 1,07 s por quadro para **um** par (22 pares ≈ 24 s); o
    braço em todos os quadros a 10 qps custaria ~30 h para este vídeo.
- **Caixa da tablatura**: o `painel` da tela do produto nos quadros dentro de uma exibição.

## Os eventos (`.maos.json`)

Um evento por nota do produto, com a chave do `chorinho/video@1`.

- **`t_som`**: o `t_audio` da coluna `(tela, exibição, coluna)`, na passagem de `t_ini` mais
  perto dele (emenda acima); nas outras, `null`.
- **Janela**: os quadros com PTS em `[t_som − 0,5 s, t_som + 0,5 s]`.
- **K1 (som)**: passa se `t_som` existe; valor = a `confianca` da trilha do áudio.
- **K2 (mão do braço na casa)**: só nota presa (casa > 0; corda solta → `null`).
  - O braço: o quadro de braço **entregue** mais perto de `t_som`, a ≤ 0,5 s; sem ele,
    `null`.
  - A célula: ao longo do braço, entre o traste `casa − 1` (o nut se `casa` = 1) e o traste
    `casa` + ¼ de casa; na direção das cordas, a até **1 vão** da reta da corda (a ponta do
    detector fica deslocada para a corda 6, ~1 vão no q16 do M3).
  - Passa se alguma ponta (indicador a mínimo) da mão do braço cai na célula em algum quadro
    da janela; valor = a menor distância normalizada.
- **K3 (mão do ataque)**: passa se a mão do ataque está em ≥ 50 % dos quadros da janela;
  valor = essa fração. O pico de movimento perto de `t_som` (plano, seção 3) fica para
  depois de medido: aqui é só registrado como pendência.
- **K4 (quadro limpo)**: passa se não há corte de cena na janela (distância de Bhattacharyya
  entre quadros seguidos ≤ 0,30, a `LIMIAR_CORTE` da 1009-b, sobre a assinatura do
  `tab.maos.cortes` com a tablatura mascarada), se há caixa da tablatura em `t_som` e se o
  capotraste é conhecido.
- **Nível e motivo**: as regras do validador (`tab.maos.esquema`).

## O que se mede (sem limiar de aprovação: é engenharia)

| item | o que precisa |
| --- | --- |
| **validade** | o validador `tab.maos.esquema` aceita o par, com o sha256 do denso |
| **determinismo** | duas execuções dão o mesmo `.maos.json` e o mesmo `.npz` (byte a byte); se não, onde diferem |
| **custo** | GPU e relógio, por etapa (mãos, braço, resto), por minuto de vídeo |
| **níveis** | ouro, prata e recusado, com os motivos, por passagem e por casa (solta / presa) |
| **olhar** | uma folha de 20 eventos ouro sorteados (semente 20261049), com a célula, as pontas e o braço desenhados; o agente olha e registra o que viu, **não é medida de contaminação** |

| resultado | o que fazer |
| --- | --- |
| válido, determinístico e custo cabível (≤ 2 h de GPU por hora de vídeo) | pré-registrar o piloto de 20 vídeos (M14) |
| válido, mas caro | baixar o custo do braço antes do piloto (lote de quadros na GPU, ou 0,5 qps) e medir de novo aqui |
| inválido ou não determinístico | corrigir, sem mudar as checagens, e rodar de novo |

## Riscos declarados antes

- A mão do braço trocada de lado pelo MediaPipe (visto no M0) faz K2 falhar sem ser erro do
  braço.
- O braço a 1 qps supõe o braço parado por até 0,5 s; no sky guitar a câmera é fixa.
- K2 com 1 vão de folga não separa a corda vizinha: ele confere a associação nota ↔ mão, não
  a corda.

## Resultado (2026-10-24, código bb61507a)

Duas execuções completas (`data/saida/maos/m49/mvp/rodar.sh`), relógio 20.493 s e 19.220 s.
A 1ª começou antes do capo do dono entrar no código (`CAPO_DONO`), então o `montar` (sem GPU)
foi refeito nas duas pastas com o mesmo código; o denso bruto não depende do capo.

| item | resultado |
| --- | --- |
| **validade** | o validador aceita o par (0 erros) |
| **determinismo** | `denso_bruto.npz`, `.maos.npz` e `.maos.json` **idênticos byte a byte** nas duas execuções (sha256) |
| **custo** | mãos 1.254 s + braço 19.224 s de GPU para 679 s de vídeo (4.364 quadros; braço em 437) = **~30 h de GPU por hora de vídeo**; o braço é 94 % (44 s por quadro, o dobro dos ~20 s da sondagem, com a GPU dividida) |

**Níveis** (763 eventos): **449 ouro, 295 prata, 19 recusados**.

| | ouro | prata | recusado |
| --- | --- | --- | --- |
| presa (casa > 0), 536 | 449 | 68 (K2 falhou 67; sem braço a ≤ 0,5 s 1) | 19 (sem `t_audio`) |
| solta, 227 | — | 227 (K2 não se aplica) | 0 |
| passagem 1, 728 | 431 | 278 | 19 |
| passagem 2, 35 | 18 | 17 | 0 |

- Das presas com som, **449 de 517 (86,8 %)** passam na K2. Das 67 que falham, 27 têm a ponta
  a 1–2 vãos da corda e 40 a mais de 2 vãos ou fora da casa.
- O braço: 435 de 437 quadros achados, os 435 entregues, 0 sinalizados (câmera fixa, sem capo).
- A mão do braço está em 4.308 de 4.364 quadros (4.306 pelo Wholebody), a do ataque em 4.346.
- **K3 e K4 não separam nada neste vídeo**: K3 = 1,0 em todos os eventos com som, e a maior
  distância de corte é 0,16 (limiar 0,30). Câmera fixa e mãos sempre visíveis; elas vão
  pesar em outros vídeos, não aqui.
- Contagens: `data/saida/maos/m49/mvp/contagens.py`.

**Leitura pela regra da rodada**: válido e determinístico, mas **caro** (30 h ≫ 2 h de GPU por
hora de vídeo). Ação pré-registrada: baixar o custo do braço antes do piloto e medir de novo
aqui. Só o ganho de velocidade sem mudar a resposta (tarefa delegada
`docs/pesquisa/maos-gap-custo-do-braco.md`, meta 3×) leva a ~11 h por hora de vídeo, ainda
acima de 2 h: o piloto vai precisar também de **menos hipóteses ou menos quadros de braço**,
e isso muda a resposta, então é rodada nova com prova.

### Olhar (a folha de 20 ouro, semente 20261049; não é medida de contaminação)

- A 1ª versão da folha desenhava a casa sobre a linha dos pontos de traste (o meio do braço),
  não sobre a corda da nota: em corda 1 a célula parecia vazia. Corrigido só no desenho
  (`folha`): a célula vai sobre a reta da corda, com a mesma conta da K2 (`distancia_na_celula`),
  e o quadro mostrado é o da janela em que a ponta chega mais perto da célula. As checagens
  não mudaram.
- Triagem por Haiku célula a célula, com a 01 conferida por mim: **20 de 20 com uma ponta do
  detector sobre a célula e um dedo de verdade ali**; braço certo em 20 de 20; mão trocada em 0.
- O vídeo é de **tela dividida**: a mão do ataque vem de uma câmera (painel esquerdo) e o
  braço de outra (painel direito). As coordenadas das duas mãos não estão no mesmo espaço
  físico; para o modelo futuro isso é entrada como ela é, mas a geometria entre as mãos não
  vale neste vídeo (a tarefa delegada da troca de mãos precisa saber disto).
- Na 01 (corda 3 casa 4), o quadro em que a ponta cai na célula está ~0,3 s antes do som, com o
  cursor da tela ainda na coluna anterior: o dedo já se prepara para a nota seguinte. A K2
  passa por isso com a janela de ±0,5 s; é o risco da nota vizinha, medido na tarefa delegada
  `docs/pesquisa/maos-gap-k2-nota-vizinha.md` antes do piloto.

**Próximo**: o piloto de 20 vídeos espera (1) o custo do braço (tarefa delegada) e uma rodada
de corte de custo que mude a resposta (menos pares ou braço a menos qps), com prova; (2) a
resposta da nota vizinha, que pode estreitar a janela da K2.
