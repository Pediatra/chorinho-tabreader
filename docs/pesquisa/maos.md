# Sistemas Computacionais de Transcrição Musical, Modelação Biomecânica de Dedilhação e Fusão Multimodal Áudio-Visual

**Documento de pesquisa** (revisão de literatura) da trilha das mãos.
**Data**: 2026-10-15. **Fonte**: texto do dono do projeto. **Formatação**: agente da frente mãos —
o conteúdo não foi alterado, só a estrutura (títulos, tabelas, blocos de equação e pontuação
segundo o estilo do repo).

> **Duas notas de leitura.**
> (1) As equações aparecem em blocos `$$…$$` (LaTeX); no texto corrido os símbolos vão em
> Unicode (β, f₀, 2^(n/6)), para o documento continuar legível sem renderizador de matemática.
> (2) Os marcadores `[cite: N]` vêm do texto original; a lista de referências não foi fornecida
> com ele.

**Sumário**

1. O problema da redundância espacial-acústica e a transcrição musical automática (AMT)
2. Desambiguação acústica via inarmonicidade e classificação de técnicas expressivas
3. Biomecânica da execução instrumental e ergonomia cognitiva
   - 3.1 Coordenação inter-manual e controlo motor em escalas e passagens rápidas
4. Otimização algorítmica da dedilhação: da programação dinâmica aos modelos de sequência profundos
   - 4.1 Engenharia de funções de custo e *Path Difference Learning* (PDL)
   - 4.2 Modelos ocultos de Markov e o algoritmo Minimax Viterbi
   - 4.3 Redes neuronais profundas, *probabilistic fretboards* e Transformers
5. Perceção visual computacional e extração sub-pixel de estruturas lineares
   - 5.1 Reconstrução geométrica do braço e invariância 12-TET
   - 5.2 Deteção sub-pixel de estruturas curvilíneas finas: o algoritmo de Steger
6. Arquiteturas de fusão multimodal áudio-visual
   - 6.1 Transcrição espacial em instrumentos de cordas dedilhadas e friccionadas
   - 6.2 Fusão grafo-esquelética e áudio na transcrição de piano (HandSkeletonNet e PianoVAM)
7. Síntese analítica e direções futuras para sistemas interativos

---

## 1. O problema da redundância espacial-acústica e a transcrição musical automática (AMT)

A **Transcrição Musical Automática** (*Automatic Music Transcription* — AMT) consiste no processo
computacional de converter um sinal de áudio bruto, resultante de uma execução instrumental ou
vocal, numa representação simbólica estruturada, tal como uma partitura convencional, ficheiros
MIDI ou tablaturas. Na literatura de **Recuperação de Informação Musical** (*Music Information
Retrieval* — MIR), o problema da transcrição organiza-se hierarquicamente em quatro níveis de
abstração:

| nível | nome |
| --- | --- |
| 1 | nível de trama (*frame-level*) |
| 2 | nível de nota (*note-level*) |
| 3 | nível de fluxo (*stream-level*) |
| 4 | nível de notação (*notation-level*) |

A extração de melodia geral ou vocal opera predominantemente ao **nível da trama**, recorrendo a
redes convolucionais profundas (DCNN) com convoluções dilatadas, redes de alta resolução (HRNet)
para separação de fontes, esquemas de aprendizagem semi-supervisionada do tipo professor-aluno
(*teacher-student*) ou segmentação semântica pixel a pixel sobre imagens tempo-frequência para
estimar a frequência fundamental (f₀). Já a conversão para o **nível de notação** exige a
resolução de ambiguidades físicas e motoras intrínsecas ao instrumento musical.

Em instrumentos de teclado como o piano, existe uma correspondência bijetiva estrita entre a
altura tonal (*pitch*) e o atuador mecânico: há uma única tecla para cada frequência fundamental,
o que permitiu que arquiteturas baseadas em redes neuronais convolucionais e recorrentes
atingissem elevada precisão ao nível da nota. Contudo, mesmo no piano, a transição da sequência
de notas para a execução física requer um mapeamento complexo de dedilhação (*fingering*), onde o
espaço de estados das duas mãos não está explicitamente codificado no sinal acústico.

Em instrumentos de cordas dedilhadas ou friccionadas — guitarra clássica, guitarra elétrica,
baixo elétrico e violino —, o problema adquire uma dimensão adicional de indeterminação: a
**redundância espacial de altura tonal** (*pitch redundancy*).

Numa guitarra de seis cordas com afinação padrão (E₄–B₃–G₃–D₃–A₂–E₂), cujos números de nota MIDI
para as cordas soltas correspondem ao conjunto O = {64, 59, 55, 50, 45, 40}, a altura tonal MIDI
*n* produzida num determinado par corda-traste (s, f) é governada pela relação linear simples:

$$
n = \mathcal{O}[s] + f
$$

Devido à sobreposição de intervalos entre cordas adjacentes (maioritariamente quartas justas, ou
cinco semitons, exceto a terça maior entre G₃ e B₃), a mesma frequência fundamental — como a nota
E₃ (164,81 Hz) — pode ser articulada em múltiplas combinações de corda e traste ao longo do braço
do instrumento.

Considerando que cada posição espacial pode ainda ser pressionada por qualquer um dos quatro
dedos ativos da mão esquerda (indicador, médio, anelar e mínimo), uma única nota isolada num
instrumento de cordas admite **até quatro localizações espaciais distintas** e, no pior caso,
**até 16 configurações de dedilhação** possíveis. Quando o problema é expandido para a execução
polifónica num braço de 6 cordas por 17 a 25 trastes, o número de estados combinatórios cresce
exponencialmente, inviabilizando abordagens determinísticas ingénuas.

A resolução deste espaço de estados requer arquiteturas integradas que processem paralelamente:

- **indícios acústicos** — estimação multi-f₀, análise de inarmonicidade e classificação de
  técnicas expressivas;
- **indícios visuais** — reconstrução geométrica do braço em precisão sub-pixel e rastreio do
  grafo esquelético da mão;

fundindo ambas as modalidades num **descodificador sequencial sujeito a restrições
biomecânicas**, para produzir tablaturas e dedilhações fisicamente exequíveis.

## 2. Desambiguação acústica via inarmonicidade e classificação de técnicas expressivas

Quando apenas o sinal de áudio está disponível, a resolução da redundância corda-traste não pode
depender exclusivamente da frequência fundamental f₀, exigindo a análise da microestrutura
espectral do timbre da corda.

A física das cordas vibrantes reais demonstra que a rigidez mecânica do material introduz uma
dispersão de fase que afasta as frequências dos parciais harmónicos dos múltiplos inteiros ideais
da frequência fundamental — um fenómeno designado por **inarmonicidade**. De acordo com a
formulação estabelecida por **Barbancho et al.**, a frequência esperada do *k*-ésimo parcial,
f*ₖ(s, n), para uma nota executada na corda *s* e no traste *n*, obedece à equação de dispersão:

$$
f_k^*(s, n) = k \cdot f_0(s, n) \cdot \sqrt{1 + \beta(s, n) \cdot k^2}
$$

O coeficiente de inarmonicidade β(s, n) encapsula as propriedades físicas e geométricas da porção
vibrante da corda, sendo diretamente proporcional ao módulo de Young *Q* do material e à quarta
potência do diâmetro da corda *d*, e inversamente proporcional à tensão *T* e ao quadrado do
comprimento efetivo de vibração *l*:

$$
\beta = \frac{\pi \cdot Q \cdot d^4}{64 \cdot l^2 \cdot T}
$$

Uma vez que o espaçamento dos trastes segue a escala temperada de doze semitons (12-TET), na qual
a razão entre frequências de trastes adjacentes é 2^(1/12) e o comprimento vibrante *l* reduz
inversamente na mesma proporção mantendo a tensão *T* constante, o coeficiente de inarmonicidade
varia deterministicamente ao longo do braço. Especificamente, o coeficiente β(s, n) no traste *n*
relaciona-se com o coeficiente da corda solta β(s, 0) através de uma progressão geométrica de
razão 2^(1/6) por cada traste avançado:

$$
\beta(s, n) = \beta(s, 0) \cdot 2^{\frac{n}{6}}
$$

Esta propriedade física permite calibrar um sistema de transcrição estimando apenas os **seis
valores basais β(s, 0)** das cordas soltas e deduzindo analiticamente toda a matriz de
inarmonicidade β(s, n) do instrumento.

Como o desvio espectral cresce quadraticamente com o índice do parcial *k*, a análise dos
parciais superiores permite identificar em qual par (s, n) a nota foi efetivamente gerada. Os
parâmetros operacionais medidos nesse tipo de sistema são:

- **exclusão das primeiras 5 tramas** de cada evento de nota, para evitar a contaminação pelos
  transitórios ruidosos de ataque;
- **sobreposição de trama de 75 %** e **passo temporal (*hopsize*) de 5 ms** a 44100 Hz;
- **medida-F de deteção de onset de 98,5 %**.

Para além da localização espacial, a transcrição fidedigna para tablatura exige a captura de
**técnicas expressivas de articulação**, que são sistematicamente ignoradas por modelos
convencionais de conversão áudio-para-MIDI.

A arquitetura **TART** (*Technique-Aware Audio-to-tab Representation Tool*) resolve esta lacuna
através de um *pipeline* sequencial de quatro estágios:

1. conversão de áudio bruto em eventos MIDI de nota com tempos de ataque (*onset*) e extinção
   (*offset*), utilizando um modelo base de transcrição de piano;
2. classificação acústica de técnicas expressivas ao nível da nota — *hammer-on*, *pull-off*,
   *tapping*, *slides*, *bends*, harmónicos e golpes percussivos;
3. predição de corda e traste a partir da sequência MIDI, mediante um modelo Transformer;
4. fusão pós-processada dos dados recolhidos para síntese da tablatura final.

Em sistemas complementares de filtragem de plausibilidade intra-nota (*Intra-Note Plausibility
Filter*), restrições acústico-temporais e cinemáticas são impostas para evitar falsos positivos:

- notas abafadas (*dead notes*) com duração superior a **0,6 s** são automaticamente rejeitadas e
  reclassificadas na segunda classe de expressão mais provável;
- **harmónicos** usam o centroide geométrico do braço para localizar a posição alternativa em que
  a mão toca a corda;
- ***pull-off*** é validado apenas se precedido por uma nota mais aguda na mesma corda executada
  por um dedo de índice superior (sendo sempre viável entre uma corda premida e uma corda solta);
- ***slide legato*** requer notas consecutivas na mesma corda articuladas pelo mesmo dedo em
  trastes distintos;
- ***vibrato*** é avaliado mediante dois limiares temporais personalizáveis de duração mínima,
  sendo estritamente proibido em cordas soltas.

| Componente do sistema / método | Mecanismo técnico principal | Restrições e parâmetros operacionais | Limitações identificadas na literatura |
| --- | --- | --- | --- |
| **Análise de inarmonicidade** (Barbancho et al. / Kehling et al.) | Estimação do desvio espectral dos parciais via β(s, n) = β(s, 0) · 2^(n/6) e rastreio de picos parciais. | Exclusão das 5 tramas iniciais (transitório de ataque); sobreposição de trama de 75 %; *hopsize* de 5 ms a 44100 Hz (medida-F de onset de 98,5 %). | Sensível a sobreposição espectral severa em acordes densos; requer conhecimento ou calibração de β(s, 0). |
| **Pipeline TART** (*Technique-Aware Audio-to-Tab*) | Arquitetura em 4 estágios combinando transcritor de piano (áudio → MIDI), classificador expressivo e Transformer. | Integra altura tonal, onset, offset, técnicas expressivas (*bends*, *tapping*, *slides*) e atribuição corda-traste. | Dependência da precisão do estágio inicial áudio-para-MIDI; propagação de erros se o onset falhar. |
| **Filtro de plausibilidade intra-nota e regras expressivas** [cite: 17, 18] | Validação pós-classificação baseada em limites temporais e viabilidade biomecânica de articulação. | *Dead notes* limitadas a < 0,6 s; vibrato proibido em cordas soltas; *slide legato* exige mesma corda e mesmo dedo. | Modelação de *bends* permanece altamente complexa, exigindo árvores de decisão sobre 25 atributos de contexto. |
| **Fusão áudio-visual determinística** (Paleari et al.) | Extração de contornos Canny/Hough, fluxo ótico Lucas-Kanade e limiar de ocupação de pele na grelha. | Ocupação mínima de 60 % de píxeis de mão por célula corda-traste (0 % falsos positivos); vídeo a 640 × 480, 25 fps. | Desambigua 89 % das notas em execuções monofónicas; confunde pestanas (*barré*) com pontas de dedos isoladas. |

## 3. Biomecânica da execução instrumental e ergonomia cognitiva

A seleção de uma sequência de dedilhação por um executante humano não é um mero exercício
combinatório, mas sim um processo de **controlo motor** que procura minimizar o custo biomecânico
e otimizar a qualidade acústica e tímbrica sob severas restrições anatómicas.

O estudo empírico da complexidade motora na guitarra clássica, conduzido por **Heijink e
Meulenbroek**, demonstra que a dificuldade biomecânica dos movimentos da mão esquerda é governada
por três fatores estruturais primários:

1. a **posição longitudinal da mão** ao longo do braço do instrumento (*hand position*),
   convencionalmente anotada em algarismos romanos segundo o traste ocupado pelo dedo indicador;
2. a **amplitude de abertura interdigital** (*finger span*);
3. a necessidade de **reposicionamento do segmento do membro superior** (*hand repositioning*) ao
   longo da escala.

A geometria física do braço impõe uma variação contínua na exigência de precisão espacial: numa
guitarra clássica padrão, o espaçamento inter-trastes diminui progressivamente de **36,5 mm** junto
à pestana (primeira posição) para **12,9 mm** nas posições agudas junto à boca do instrumento
(*soundhole*). Daí decorre o mapa ergonómico do braço:

| zona | posições | o que o executante enfrenta |
| --- | --- | --- |
| posições baixas | I a IV | elevados custos de extensão e abdução digital |
| **zona média (ótima)** | **V a XII** | região ergonómica de conforto motor |
| posições extremas | acima de XII | espaço reduzido; *cramping* e colisão física com a caixa de ressonância |

O traste XIX, em particular, é frequentemente dividido pela boca do instrumento nas terceira e
quarta cordas. A literatura biomecânica e musicológica converge, assim, na identificação da
**zona média do braço (posições V a XII)** como a região ergonómica ótima de conforto motor.

Além disso, a **colocação micro-espacial do dedo dentro do traste** é crítica:

- posicionar o dedo demasiado afastado do traste (para a esquerda, longe da boca) gera
  **trastejamento** (*buzzing*) quando a corda é dedilhada;
- posicioná-lo demasiado para a direita (diretamente sobre o filete metálico) **amortece** as
  oscilações da corda.

### 3.1 Coordenação inter-manual e controlo motor em escalas e passagens rápidas

Uma limitação recorrente nos modelos computacionais elementares é o tratamento isolado da mão que
define a altura tonal (mão esquerda nas cordas), ignorando o **acoplamento cinemático** entre
ambas as mãos. Na realidade física da execução, a temporização é controlada conjuntamente: o dedo
da mão esquerda deve **estabilizar a corda numa fração de tempo precisa antes** de o dedo da mão
direita a dedilhar e produzir o som.

A sistematização biomecânica desenvolvida por **Narciso Yepes** para a execução de escalas rápidas
com três dedos (i–m–a: indicador, médio e anelar) ilustra como a dedilhação da mão esquerda ("o
operário") deve ser subordinada à eficiência mecânica da mão direita ("o artista").

Na mão direita, a sequência convencional **i → m → a** aplicada a escalas contradiz os princípios
fundamentais da biomecânica manual e do controlo motor durante mudanças de corda (*string
crossings*), sendo adequada para arpejos mas contraproducente em escalas. Como os dedos possuem
comprimentos anatómicos distintos — o médio (*m*) mais longo que o indicador (*i*) e o anelar
(*a*) —, as transições ascendentes entre cordas apresentam assimetrias biomecânicas acentuadas:

- o cruzamento ascendente **m → i** obriga o dedo mais longo (*m*) a fletir enquanto o dedo mais
  curto (*i*) se estende para alcançar a corda adjacente, gerando uma configuração motora
  genuinamente desconfortável e ineficiente;
- em contrapartida, o cruzamento ascendente **a → m** permite que o dedo mais longo (*m*) ultrapasse
  naturalmente o dedo mais curto (*a*), resultando numa transição biomecanicamente neutra a
  vantajosa.

Para explorar esta vantagem utilizando padrões cíclicos triplos (**a–m–i**, **m–i–a** e
**i–a–m**) estabilizados pela posição de **"polegar interno"** (*thumb-inside* ou *thumb-under*, na
qual o polegar é recolhido em direção à palma e repousa levemente na corda grave adjacente,
acompanhando a subida ou descida da escala, ou recebe diretamente o toque com apoio leve —
*apoyando* — dos dedos sem plantação prévia), a dedilhação da mão esquerda tem de ser desenhada
para maximizar cruzamentos eficientes e minimizar abduções ou deslocamentos desnecessários.

Quando mudanças de posição longitudinal (*shifts*) na mão esquerda são inevitáveis, a biomecânica
dita regras estritas de estabilidade articular:

- as translações devem ser executadas prioritariamente com o **dedo médio (2) ou o indicador (1)**,
  que possuem maior força e estabilidade em ambas as direções;
- o **dedo anelar (3)** deve ser evitado em mudanças de posição, por ser anatomicamente o mais
  fraco e menos seguro;
- o **dedo mínimo (4)** deve ser evitado em deslocamentos ascendentes, por ser significativamente
  menos estável a subir do que a descer.

Adicionalmente, o uso inteligente de **cordas soltas** e **ligados** (*slurs*) durante passagens
rápidas funciona como um mecanismo de transição cinemática — mesmo introduzindo um cruzamento
ascendente a → m para uma corda solta aguda no meio de uma escala descendente, como documentado na
edição de Yepes para *La joia* (compasso 84 de *Col·lectici íntim*) de Vicente Asencio: permite à
mão esquerda mudar da posição V para a posição I durante a ressonância da corda solta E e utilizar
um ligado no B agudo para alternar da sequência a–m–i para o padrão i–a–m.

Estes princípios de transferência anatómica manifestam-se de forma análoga noutros instrumentos:

- **piano** — a seleção digital depende estritamente do intervalo de altura entre notas vizinhas e
  da direção do movimento: numa escala descendente executada pela mão direita sem translação da
  mão, a transição do dedo 1 → 2 é perfeitamente viável, mas a transição do dedo 2 → 3 é
  fisicamente impossível sem deslocar a mão, constituindo uma sequência "não jogável"
  (*unplayable*);
- **violino** — a ausência de trastes exige que a modelação da mão esquerda recorra a Modelos
  Ocultos de Markov para traduzir partituras em padrões de dedilhação calibrados especificamente
  para o nível de proficiência técnica desejado pelo executante, ou a modelos de geração de
  movimento como o **SyncViolinist**, que integram simultaneamente arcada (*bowing*) e dedilhação.

## 4. Otimização algorítmica da dedilhação: da programação dinâmica aos modelos de sequência profundos

A formalização matemática do problema da dedilhação em instrumentos de cordas teve a sua génese no
trabalho seminal de **Samir Sayegh (1989)**, que introduziu o **Paradigma do Caminho Ótimo**
(*Optimum Path Paradigm* — OPP) para música homofónica. Sayegh estruturou o problema num
procedimento de quatro etapas que culmina na **pesquisa de caminho mais curto** (*shortest path
problem*) num grafo acíclico dirigido (DAG) em camadas, onde:

- cada **camada temporal** corresponde a uma nota da partitura;
- cada **nó** representa uma configuração possível de dedilhação ⟨corda, traste, dedo⟩;
- as **arestas** entre camadas adjacentes possuem pesos determinados por uma função de custo de
  transição.

Embora a abordagem de otimização global de Sayegh encontre a trajetória de menor custo acumulado ao
longo de toda a peça musical via **Programação Dinâmica (DP)**, investigações subsequentes de
**Radicioni e Lombardo** demonstraram que os executantes humanos não processam uma obra musical como
um bloco monolítico. Em vez disso, os músicos aplicam um princípio de **segmentação cognitiva**,
dividindo a partitura em frases musicais (*phrase splitting*) segundo estruturas de agrupamento
percetivo. Ao construir um grafo independente para cada segmento frásico, calcular o caminho mais
curto localmente e fixar o último nó ótimo do fragmento anterior como primeiro nó do segmento
seguinte, obtêm-se dedilhações cognitivamente mais fiáveis e próximas das escolhas de intérpretes
reais do que aquelas geradas por otimização global irrestrita.

### 4.1 Engenharia de funções de custo e *Path Difference Learning* (PDL)

Nos sistemas clássicos baseados em Programação Dinâmica, a qualidade da tablatura ou dedilhação
gerada depende criticamente da formulação da **função de custo**. Em modelos orientados por
regras — como o sistema parametrizado segundo as diretrizes pedagógicas de **Mårten Falk** e
avaliado por **Anders Eriksson** em cinco peças clássicas, ou o modelo de **Itoh e Hayashida**,
que estima o custo de movimento da mão através da distância de Manhattan —, cada nó do grafo é
definido por um tuplo contendo:

- número da **corda**;
- número do **traste**;
- **dedo** atribuído;
- **duração** da nota;
- **posição longitudinal da mão**.

A função de custo aplica penalizações quando os dedos se desviam da sua **posição natural**
(definida como a colocação do indicador no primeiro traste relativo da posição, o médio no segundo,
e o anelar e o mínimo no segundo, terceiro ou quarto trastes), penalizando:

- proporcionalmente a uma potência do deslocamento, as **compressões** (*cramping*) e **extensões**
  físicas (*stretching*);
- o **uso consecutivo do mesmo dedo em duas cordas diferentes**;
- a execução em **trastes elevados** para iniciantes.

Contudo, a definição manual de pesos para funções de custo enfrenta **limitações estruturais
severas** que comprometem a sua generalização.

**Primeira limitação — miopia temporal (*short-sightedness*).** Quando a função de custo avalia
apenas transições locais entre notas imediatamente adjacentes, a restrição de horizonte impede o
sistema de considerar o custo biomecânico de preparar ou libertar pestanas (*barré chords*),
levando a erros como manter o dedo indicador em pestana sobre a primeira corda num instante
imediatamente anterior a uma nota que exige que essa mesma primeira corda soe solta.

**Segunda limitação — explosão combinatória de estados polifónicos.** Para modelar acordes, é
necessário introduzir um **termo de custo estático** (*static cost*) que quantifique a dificuldade
mecânica instantânea da postura da mão, em adição ao custo dinâmico de transição entre acordes. Na
aplicação do algoritmo de Viterbi a sequências harmónicas (como a progressão de cinco acordes
C → G → F → Am → C), o processo divide-se em quatro etapas:

1. enumeração de todas as disposições (*voicings*) candidatas;
2. filtragem de configurações fisicamente impossíveis mediante **regras rígidas** (*hard rules*);
3. pontuação das disposições viáveis por **regras suaves** (*soft rules*);
4. pesquisa dinâmica do caminho global que maximiza a soma da qualidade estática com a pontuação de
   transição:

$$
\text{best}[i][c] = \text{quality}(i, c) + \max_p \left( \text{best}[i-1][p] + \text{transition}(p, c) \right)
$$

Neste esquema, a função de pontuação recompensa disposições ressonantes atribuindo, por exemplo,
**+1,2 por cada corda que soa** e **+0,5 adicionais por cada corda solta ativa**, enquanto aplica
penalizações de transição (como **−5**) quando a mão é forçada a alternar entre uma forma aberta
(qualidade **+7**) e uma forma de pestana no quinto traste (qualidade **+3**).

**Terceira limitação — subjetividade estilística e tímbrica.** As diretrizes variam
significativamente entre o repertório Barroco, Clássico, Folk ou Rock. Enquanto heurísticas
puramente mecânicas dão preferência absoluta a cordas soltas (por não restringirem a posição da mão
nem contribuírem para a métrica de estiramento, *stretch* = 0), formulações orientadas à qualidade
acústica tratam a frequência de utilização de cordas soltas como um **atributo tímbrico ajustável**
ao gosto do intérprete. Consequentemente, alterar a hierarquia relativa de pesos entre **mudança de
corda** (*String Change* — SC), **abertura da mão** (*Hand Spread* — HS) e **mudança de posição**
(*Position Change* — PC) — por exemplo, configurando HS = 2 × SC e PC = 2 × HS, ou invertendo os
pesos para PC = 2 × HS e SC = 2 × PC — produz soluções de dedilhação **topologicamente distintas**
para a mesma passagem musical.

Para eliminar a arbitrariedade na atribuição manual destes coeficientes num espaço polifónico de
6 × 17 trastes, **Radisavljevic e Driessen** desenvolveram o método de **Aprendizagem por Diferença
de Caminho** (*Path Difference Learning* — PDL). Em vez de armazenar custos para todas as transições
de estados possíveis (o que causaria exaustão de memória), o PDL:

- extrai **características estáticas** (como o número de trastes entre dedos consecutivos) e
  **características dinâmicas de transição** (como o número de trastes percorridos por um dedo
  específico ou a mudança de estado de um dedo de utilizado para não utilizado);
- compara iterativamente o caminho ótimo atual gerado pela Programação Dinâmica, P_actual, com a
  dedilhação de referência anotada na tablatura, P_desired, isolando exclusivamente os **segmentos
  divergentes** onde os dois caminhos competem (tais como os pares de sub-trajetórias
  {(1,2,3,4), (1,8,9,4)} e {(5,6,7), (5,10,7)});
- através de **descida de gradiente** (*gradient descent*) analítica executada ao longo de L_k
  iterações por ronda (tipicamente 10 rondas de 200 iterações, como demonstrado na convergência
  para o *Adagio* de Albinoni), atualiza os pesos **w** das funções de custo para diminuir o custo
  cumulativo do caminho desejado e aumentar o custo do caminho ótimo concorrente, até que a lista
  de diferenças de caminho estabilize numa pequena fração do espaço de estados total.

### 4.2 Modelos ocultos de Markov e o algoritmo Minimax Viterbi

Na formulação probabilística do problema, a decisão de dedilhação e o arranjo musical são
unificados como um problema de descodificação num **Modelo Oculto de Markov** (*Hidden Markov
Model* — HMM), onde as notas da partitura constituem a sequência de símbolos observados Y_t e as
configurações biomecânicas da mão constituem a sequência de estados ocultos X_t.

No modelo de **Hori e Sagayama** para uma guitarra clássica de 6 cordas e 19 trastes, cada estado
oculto (ou "forma" q_i) é definido pelo par corda-traste (s_i, f_i) e pelo dedo da mão esquerda
h_i ∈ {1, 2, 3, 4} — com um estado adicional para a corda solta, onde o índice digital não se
aplica —, resultando em exatamente

$$
6 \times (19 \times 4 + 1) = 462
$$

estados ocultos teóricos (sendo o número efetivo ligeiramente inferior, porque o 19.º traste é
frequentemente dividido pela boca do instrumento nas terceira e quarta cordas e os músicos raramente
posicionam o indicador no 19.º traste ou o mínimo no 1.º traste).

Para capturar a cinemática longitudinal da mão esquerda, Hori e Sagayama definem a **posição do dedo
indicador** (*index finger position* — ifp) associada ao estado q_i como:

$$
\text{ifp}(q_i) = f_i - h_i + 1
$$

A probabilidade de transição a_ij(dt) = P(X_t = q_j | X_{t−1} = q_i, dt) entre dois estados ocultos
reflete a facilidade biomecânica do movimento, sendo modelada pelo **produto de três componentes**:

1. uma **distribuição esparsa centrada em zero** (como a distribuição de Laplace), parametrizada
   pelo intervalo temporal *dt* entre os ataques (*onsets*) das notas *t−1* e *t* — refletindo o
   facto de a mão esquerda permanecer tipicamente fixa numa posição durante várias notas antes de
   saltar alguns trastes;
2. um **termo de dificuldade de mudança entre cordas** dado pela função 1 / (1 + |s_i − s_j|), que
   apresenta menor esparsidade que a distribuição de Laplace;
3. uma **probabilidade p_H(h_j)** que pondera a dificuldade diferencial entre os dedos (como a maior
   facilidade de utilização do indicador face ao mínimo).

Como cada estado oculto emite deterministicamente uma única altura tonal MIDI,
note(q_i) = n_{s_i} + f_i, a probabilidade de emissão b_ik = P(Y_t = o_k | X_t = q_i) é **binária**
(1 se o_k = note(q_i), e 0 caso contrário) — embora em modelos de geração de tablatura *fingerstyle*
a partir de *lead sheets* o custo de emissão seja formulado para garantir que a forma q_n emita
simultaneamente a nota da melodia x_n e o maior número possível de notas do acorde c_n, para
produzir uma harmonia rica.

A contribuição teórica mais profunda de Hori e Sagayama reside na **reformulação do próprio
critério de otimização dinâmica**. O algoritmo de Viterbi convencional seleciona o caminho que
maximiza o **produto** das probabilidades de transição ao longo de toda a sequência:

$$
\delta_{j, t+1} = \max_i (\delta_{i, t} \cdot a_{ij}) \cdot b_j(y_{t+1})
$$

Do ponto de vista biomecânico, maximizar o produto global permite que uma sequência contenha uma
transição pontual extremamente difícil, desde que seja matematicamente compensada por movimentos
fáceis no resto da frase. Contudo, **a exequibilidade prática de uma passagem musical é determinada
pelo seu movimento mais difícil**. Para resolver este problema, os autores introduziram o
**Algoritmo Minimax Viterbi**, que substitui o produto pela operação de **mínimo** na recursão,
procurando a sequência de estados ocultos que maximiza a probabilidade de transição mínima (isto é,
minimiza a dificuldade máxima de movimento exigida ao longo da frase):

$$
\delta_{j, t+1} = \max_i \left( \min(\delta_{i, t}, a_{ij}) \right) \cdot b_j(y_{t+1})
$$

Esta abordagem foi subsequentemente estendida para uma família parametrizada designada por
**algoritmos L_p-Viterbi**, baseada na norma-p do vetor das probabilidades de transição
logarítmicas, interpolando continuamente entre o algoritmo de Viterbi convencional (soma absoluta
dos elementos para p = 1) e o algoritmo Minimax Viterbi (valor absoluto máximo para p = ∞).

Paralelamente, na literatura de piano, **Nakamura et al.** construíram o primeiro conjunto de dados
público de dedilhação de piano e propuseram o *Merged-Output HMM* (bem como HMMs de ordem superior)
para automatizar a separação e rotulagem de partes de mão esquerda e mão direita em partituras
indiferenciadas, enquanto **Li Qiang et al.** combinaram regras de dedilhação com uma função de
julgamento para otimizar o algoritmo de Viterbi.

### 4.3 Redes neuronais profundas, *probabilistic fretboards* e Transformers

Apesar da eficácia dos HMMs em restrições locais, a incapacidade das observações independentes em
capturar relações de longo alcance impulsionou a adoção de arquiteturas de aprendizagem profunda em
**três frentes distintas**.

**Primeira frente — braço probabilístico (*probabilistic fretboard*).** Redes neuronais que
realizam desconvoluções no estágio final, treinadas sobre parte do corpus **DadaGP** (incluindo
aumento artificial de dados para notas fora da tessitura da guitarra), mapeiam um conjunto de
alturas MIDI **m** num "braço probabilístico" p ∈ ℝ^(6 × 25). Para converter esta representação
contínua numa tablatura binária efetiva b_k ∈ {0, 1}^(6 × 25), um algoritmo analítico:

1. transpõe todas as notas de **m** para dentro do alcance do braço em incrementos de oitava;
2. fixa o número de notas a preservar em N = min(|m|, 6);
3. gera todas as combinações binárias de N notas que cumpram dois critérios estritos de
   jogabilidade: **no máximo uma nota por corda** e **todas as notas de cordas não soltas contidas
   numa janela máxima de 6 trastes**;
4. caso nenhuma configuração binária satisfaça estes critérios, reduz N iterativamente em uma
   unidade até que sejam encontradas soluções válidas;
5. seleciona a matriz b_k que maximiza a soma de valores na tablatura probabilística ou o produto
   interno normalizado:

$$
\frac{\vec{p} \cdot \vec{b}}{\|\vec{p}\| \, \|\vec{b}\|}
$$

Os resultados experimentais demonstram que esta priorização rígida do número máximo de notas N pode
forçar a escolha de uma combinação de seis notas com probabilidade quase nula no conjunto de dados,
evidenciando a necessidade de permitir soluções com **menos notas mas maior plausibilidade
ergonómica**.

**Segunda frente — redes recorrentes (LSTM e Bi-LSTM)**, para incorporar memória de longo prazo
sobre intervalos melódicos. No domínio do piano, o modelo de correspondência de dedilhação por
diferença de altura (*Pitch-Difference Fingering* — PdF) substitui as notas absolutas pelos
**intervalos entre pares de notas adjacentes**, reduzindo a variação nas sequências simbólicas e
facilitando o ajuste da rede com conjuntos de dados reduzidos. Como as redes LSTM convencionais não
impedem por si sós transições anatómicas impossíveis em escalas compactas sem movimento da mão, o
modelo PdF integra uma camada adicional de conhecimento de transferência digital, utiliza um HMM
para aumentar estatisticamente os dados de treino e avalia os resultados através de uma métrica
dedicada de **inexequibilidade de dedilhação** (*fingering unplayability*).

**Terceira frente — modelos Transformer codificador-descodificador**, que capturam simultaneamente o
contexto passado e as configurações futuras da mão. Estes modelos são treinados sob paradigmas de
**modelação de linguagem mascarada** (*Masked Language Modeling*) para atribuir notas a cordas, ou
condicionados ao estilo de guitarristas específicos para geração de tablatura (como no sistema
**ShredGP**) e continuação de guitarra rítmica. Quando integrados com regras de refinamento local
numa sequência de notas, calcula-se o valor médio do traste da passagem (excluindo cordas soltas do
cálculo); se uma nota intermédia exceder o traste máximo (MAX_FRET) ou o desvio máximo permitido
(MAX_DEVIATION), o sistema identifica as cordas disponíveis sem notas concorrentes, seleciona uma
corda solta caso exista ou, em alternativa, atribui a corda que resulta num traste mais próximo da
média da vizinhança.

## 5. Perceção visual computacional e extração sub-pixel de estruturas lineares

Quando o objetivo da transcrição não é sintetizar uma dedilhação teoricamente ótima a partir de uma
partitura, mas sim **recuperar exatamente a dedilhação executada por um intérprete específico** numa
gravação audiovisual ou vídeo online, os métodos puramente acústicos ou simbólicos revelam-se
insuficientes. A modalidade visual permite observar diretamente a posição física dos dedos, mas
exige a resolução de problemas complexos de visão computacional: as cordas e os trastes constituem
**estruturas curvilíneas extremamente finas**, frequentemente afetadas por baixo contraste,
iluminação assimétrica, distorção de perspetiva tridimensional e **oclusão constante pela mão do
músico**.

### 5.1 Reconstrução geométrica do braço e invariância 12-TET

Nos sistemas de transcrição visual de guitarra e baixo sem recurso a marcadores físicos (*markerless
tracking*), a reconstrução da grelha do braço segue duas metodologias geométricas principais.

**Metodologia A — Paleari et al.** (vídeo de qualidade webcam a 640 × 480 píxeis e 25 fps):

1. a primeira trama é analisada pelo detetor de contornos de **Canny** e pela **Transformada de
   Hough**, para determinar a orientação dominante do braço e rodar a imagem até alinhar o braço com
   o eixo horizontal;
2. após recortar a região do braço por projeção horizontal, aplica-se uma **transformação de
   cisalhamento** (*skewing*) até maximizar as projeções verticais, corrigindo o efeito de
   perspetiva que impede os trastes de parecerem retilíneos;
3. os pares de pontos extremos de cada traste são identificados procurando o **caminho de energia
   máxima** entre as bordas superior e inferior, e seguidos ao longo do vídeo pelo algoritmo de
   **fluxo ótico de Tomasi-Lucas-Kanade**;
4. para evitar que o movimento da mão sobre o braço corrompa o seguimento dos pontos, aplicam-se
   técnicas de **correspondência de modelo** (*template matching*) que impõem duas restrições
   invariantes a escala, translação e rotações 3D: a **restrição de alinhamento**, que exige que
   todos os pontos que definem os limites superior e inferior do braço estejam colineares, e a
   **restrição de modelo linear**, que valida os comprimentos e distâncias dos trastes face à
   pestana.

**Metodologia B — baixo elétrico em vídeos do YouTube.** A deteção das cordas utiliza a função
`houghlines` do OpenCV, que devolve a distância *r* ao canto superior esquerdo da imagem e o ângulo
*θ* de cada linha detetada. Para remover linhas irrelevantes do fundo (como secretárias ou janelas):

1. excluem-se primeiro os *outliers* aplicando a **regra 3σ** sobre os valores de θ;
2. aplica-se **agrupamento por k-means** (k = 4 para um baixo de 4 cordas), representando cada corda
   pelo centro (r, θ) do respetivo grupo.

Como os trastes são curtos e ocluídos pelas cordas, aparecendo como linhas fragmentadas impossíveis
de extrair diretamente de forma fiável, o sistema deteta as **marcas circulares de posição**
regularmente espaçadas no braço e calcula matematicamente a posição de cada traste explorando a
geometria do sistema temperado de 12 tons (12-TET). Definindo a razão de escala R = 2^(−1/12) (uma
vez que uma oitava duplica a frequência a cada 12 notas, em relação inversa com o comprimento) e
medindo a distância *d* entre a *i*-ésima e a *j*-ésima marca de posição, a distância *L* da ponte à
cabeça do instrumento e a distância L_{i−1} da ponte ao *i*-ésimo traste são obtidas por:

$$
L = L_{i-1} \cdot R^{1-i}, \qquad L_{i-1} = \frac{2d}{1 + R - R^{j-i} - R^{j-i+1}}
$$

### 5.2 Deteção sub-pixel de estruturas curvilíneas finas: o algoritmo de Steger

Para aplicações que requerem localização de altíssima precisão de estruturas finas como cordas, fios
(*wires*) ou defeitos lineares de baixo contraste, os detetores de arestas convencionais falham
devido à variação de largura e perfis de intensidade assimétricos. O método de referência para
extração **sub-pixel não enviesada** de estruturas curvilíneas é o algoritmo de **Carsten Steger**,
baseado na análise de **espaço-escala Gaussiano** e na **matriz Hessiana**.

No modelo analítico de Steger, o perfil transversal unidimensional de uma linha curvilínea de
semi-largura *w*, contraste *h* e parâmetro de assimetria a ∈ [0, 1) é representado por um perfil em
**barra de igual polaridade** f_a(x) (ou por um perfil em **degrau de polaridade distinta** f_s(x)):

$$
f_a(x) = \begin{cases} 0, & x < -w \\ 1, & |x| \le w \\ a, & x > w \end{cases}
$$

A convolução deste perfil com um núcleo Gaussiano g_σ(x) = (1 / √(2π)σ) · exp(−x² / 2σ²) — onde
φ_σ(x) é o integral de g_σ(x) — produz o perfil suavizado

$$
r_a(x, \sigma, w, a) = \phi_\sigma(x+w) + (a-1)\,\phi_\sigma(x-w)
$$

cuja primeira e segunda derivadas são dadas por:

$$
r'_a(x, \sigma, w, a) = g_\sigma(x+w) + (a-1)\,g_\sigma(x-w)
$$

$$
r''_a(x, \sigma, w, a) = g'_\sigma(x+w) + (a-1)\,g'_\sigma(x-w)
$$

Para garantir que o filtro Gaussiano preserve um único pico central saliente sobre a linha —
evitando que uma largura de modelo inferior à largura da estrutura divida a resposta em picos
duplos —, o parâmetro de escala σ deve satisfazer a condição teórica **σ > w / √3** (ou, em
implementações industriais discretas para semi-largura W, **σ ≥ W / 3**).

Em imagens bidimensionais I(x, y) — ou sobre uma imagem de gradiente direcional
f(x, y) = I₁(x, y) ∗ G(x, y), obtida pela convolução com um modelo Sobel vertical 5 × 5 após remoção
de uma borda de 4 píxeis, para isolar cristas positivas e negativas —, a curvatura de segunda ordem
é capturada pela **Matriz Hessiana** H(x, y), construída pela convolução com os operadores derivados
de segunda ordem do Gaussiano:

$$
g_x = -\frac{x}{2\pi\sigma^4} e^{-\frac{x^2+y^2}{2\sigma^2}}, \qquad
g_y = -\frac{y}{2\pi\sigma^4} e^{-\frac{x^2+y^2}{2\sigma^2}}
$$

$$
g_{xx} = \left(\frac{x^2}{\sigma^4} - \frac{1}{\sigma^2}\right) \frac{1}{2\pi\sigma^2} e^{-\frac{x^2+y^2}{2\sigma^2}}, \quad
g_{yy} = \left(\frac{y^2}{\sigma^4} - \frac{1}{\sigma^2}\right) \frac{1}{2\pi\sigma^2} e^{-\frac{x^2+y^2}{2\sigma^2}}, \quad
g_{xy} = \frac{xy}{2\pi\sigma^6} e^{-\frac{x^2+y^2}{2\sigma^2}}
$$

$$
H(x, y) = \begin{bmatrix} g_{xx} & g_{xy} \\ g_{xy} & g_{yy} \end{bmatrix} * f(x, y)
$$

A direção perpendicular à estrutura linear (n_x, n_y) é extraída diretamente do vetor próprio
associado ao **maior valor próprio** da matriz Hessiana, cuja solução algébrica fechada é:

$$
\frac{1}{2}\left(H_{xx} + H_{yy} + \sqrt{H_{xx}^2 + 4H_{xy}^2 - 2H_{xx}H_{yy} + H_{yy}^2}\right)
$$

Realizando uma expansão em série de Taylor de segunda ordem na vizinhança do ponto central
(x₀, y₀) ao longo de (n_x, n_y) e igualando a derivada parcial em ordem a *t* a zero
(∂/∂t · f(t n_x + x₀, t n_y + y₀) = 0), obtém-se a **coordenada sub-pixel** do extremo local:

$$
t = -\frac{n_x g_x + n_y g_y}{n_x^2 g_{xx} + 2 n_x n_y g_{xy} + n_y^2 g_{yy}}
$$

Se o deslocamento sub-pixel satisfizer

$$
(t\,n_x, t\,n_y) \in \left[-\tfrac{1}{2}, \tfrac{1}{2}\right] \times \left[-\tfrac{1}{2}, \tfrac{1}{2}\right]
$$

o ponto é retido e conectado aos pontos vizinhos na vizinhança de 8 píxeis através de
**limiarização por histerese**, gerando os conjuntos de linhas claras L_light e escuras L_dark.

Quando existe **assimetria de contraste lateral** (a ≠ 0), a posição da linha definida por
r'_a(x, σ, w, a) = 0 apresenta um enviesamento analítico em direção ao lado de menor contraste,
dado por:

$$
l = -\frac{\sigma^2}{2w} \ln(1 - a)
$$

Através da **normalização de escala** (l_σ = l / σ, w_σ = w / σ) e da inversão numérica da função
f: (w_σ, a) ↦ (v_σ, r), que mapeia a largura extraída entre bordas v_σ (zeros da segunda derivada
r''_a = 0 com r'''_a · r'_a < 0) e a razão de gradientes *r*, o algoritmo de Steger **remove
completamente este enviesamento**.

Complementarmente, métodos baseados em **sistemas de α-moléculas** e **congruência de fase**
utilizam polinómios de Hermite H_k(x) e Transformadas de Hilbert para detetar cristas e arestas com
invariância ao contraste, refinando a localização do pico máximo através de **ajuste parabólico**
sobre três pontos de amostragem adjacentes:

$$
f(x) = c_2 (x - x_{n^*})^2 + c_1 (x - x_{n^*}) + c_0
$$

## 6. Arquiteturas de fusão multimodal áudio-visual

Na análise multimodal de atuações musicais, a integração de informação acústica e visual divide-se
estruturalmente em duas famílias:

| família | como funciona | onde é usada |
| --- | --- | --- |
| **fusão precoce** (*early fusion*) | projeta e concatena múltiplas modalidades num espaço de características conjunto, frequentemente através de camadas finais de redes convolucionais | tarefas em que as duas modalidades estão sempre disponíveis e alinhadas |
| **fusão tardia** ou ao nível da decisão (*late fusion*) | combina as saídas de algoritmos especializados para cada modalidade | transcrição espacial, deteção de ataques (*onset*), estimação multi-f₀, alinhamento áudio-partitura e separação de fontes informada pela partitura |

A **fusão tardia** oferece maior flexibilidade de ajuste modal e **resiliência a falhas de
sensores**, sendo amplamente adotada.

### 6.1 Transcrição espacial em instrumentos de cordas dedilhadas e friccionadas

Nos sistemas de transcrição áudio-visual de guitarra e baixo, a **sincronização entre os fluxos de
vídeo e áudio é ancorada pela deteção de ataques (*onsets*) no sinal acústico**. A evolução da área
passa por três gerações:

- **Burns e Wanderley** — câmaras acopladas à cabeça da guitarra e Transformada de Hough circular
  para detetar pontas de dedos, mas **apenas nos primeiros 5 trastes**;
- **Paleari et al.** — filtragem de cor da pele exigindo que **pelo menos 60 % da célula retangular
  corda-traste** contivesse píxeis da mão, alcançando **0 % de falsos positivos** e desambiguando
  deterministicamente **89 % das notas monofónicas**;
- **arquiteturas modernas** — redes de estimação de pose anatómica.

No *framework* áudio-visual para **baixo elétrico** avaliado sobre **21 vídeos do YouTube de 10
executantes distintos**:

1. a posição de cada dedo é rastreada com o **Google MediaPipe Hand Landmarks**, adicionando-se uma
   margem de tolerância (*padding*) de **10 % do espaçamento do traste** a ambos os lados dos marcos
   da mão esquerda, para compensar variações de contacto;
2. em paralelo, os modelos **CREPE** e **CREPE Note** extraem do áudio a altura tonal, a confiança
   espectral e o instante de *note-on*;
3. a fusão correlaciona o instante e a frequência da nota (ou a zona correspondente num modelo de
   guitarra que divide o braço em 12 zonas segundo ZONE = f / (max_frets / num_zones)) com as
   coordenadas espaciais dos dedos sobre a grelha 12-TET;
4. uma rede **Bi-LSTM** estima a sequência ótima de dedilhação.

Em instrumentos de **cordas friccionadas e música de câmara**, a modalidade visual resolve o
problema de atribuição indevida de notas através da deteção de atividade **Tocar / Não-Tocar**
(*Playing / Non-Playing* — P/NP). No sistema de **Estimação Multi-Pitch Visualmente Informada**
(*Visually Informed MPS*) desenvolvido por **Dinesh, Bazzica et al.**, uma análise de **fluxo ótico**
identifica regiões de elevado movimento na mão do arco de cada músico, para determinar a polifonia
instantânea de cada trama de áudio. Esta informação P/NP é injetada num **estimador acústico de
máxima verosimilhança** (que modela picos espectrais e regiões de não-pico com convergência
garantida), impedindo matematicamente a atribuição de alturas tonais a instrumentistas
momentaneamente inativos.

### 6.2 Fusão grafo-esquelética e áudio na transcrição de piano (HandSkeletonNet e PianoVAM)

A complementaridade entre visão e áudio atinge elevada sofisticação na transcrição de piano solo
através da arquitetura **HandSkeletonNet** e do conjunto de dados multimodal **PianoVAM**.

No modelo **HandSkeletonNet**:

1. as coordenadas 2D dos **21 pontos anatómicos por mão** estimadas pelo MediaPipe Hands são
   normalizadas pela largura e altura da imagem para o intervalo [0, 1], preenchendo-se com zeros
   (*zero padding*) qualquer mão ausente, para manter uma estrutura fixa de **42 nós por trama**;
2. utilizando uma janela deslizante temporal de passo 1 centrada no instante *t*, constrói-se uma
   sequência de grafos cujas arestas seguem a **topologia esquelética** de cada mão;
3. em cada trama, **duas camadas de Redes Convolucionais de Grafos** (*Graph Convolutional
   Network* — GCN) com ativação ReLU extraem características ao nível do nó, que são agregadas num
   único vetor de *embedding* ao nível do grafo por ***mean pooling***, para permitir o
   reconhecimento conjunto da forma de ambas as mãos;
4. a dimensão temporal é então agregada por uma **convolução temporal separável em profundidade**
   (*depthwise temporal convolution*), extraindo-se o vetor do instante central para alimentar uma
   camada totalmente conectada que produz os **88 logits** de probabilidade de ativação de *onset*
   das teclas do piano.

Na etapa de **fusão tardia com o descodificador acústico Omnizart**, as probabilidades do esqueleto
manual são convertidas num **mapa de pesos contínuo W**, regulado por dois hiperparâmetros
fundamentais:

- **Weight Floor** — impõe um limite inferior a W, para garantir que o fluxo de áudio mantenha uma
  contribuição mínima mesmo quando as deteções da mão falham ou têm baixa confiança;
- **Weight Gamma** — expoente aplicado às probabilidades do esqueleto, para enfatizar regiões de
  elevada confiança visual antes da aplicação dos limiares de decisão (**Onset Threshold** e
  **Duration Threshold**) na conversão final para MIDI.

A avaliação sistemática no *benchmark* **PianoVAM** está estruturada numa **divisão temporal
rigorosa de 80/10/10** (73 ficheiros de treino, 19 de validação e 14 de teste), **sem repetição de
composições entre partições** para impedir *data leakage*, utilizando o pacote `mir_eval` com
tolerância de *onset* de **±50 ms** e tempos de *offset* ajustados à libertação do pedal de
sustentação.

Quando o modelo *Onsets and Frames* é treinado exclusivamente no conjunto padrão MAESTROv3 e
avaliado no conjunto de teste PianoVAM, alcança uma pontuação F1 de 93,4 % em *Note Onset* e 90,3 %
em *Note w/ Velocity*, mas sofre uma degradação acentuada na duração das notas, registando apenas
62,3 % em *Note w/ Offset* e 78,2 % em *Frame F1*. Os números completos:

| Treino | Note Onset (F1) | Note w/ Velocity (F1) | Note w/ Offset (F1) | Frame F1 |
| --- | --- | --- | --- | --- |
| MAESTROv3 | 93,4 % | 90,3 % | 62,3 % | 78,2 % |
| PianoVAM | **95,8 %** | **93,9 %** | 60,4 % | 80,0 % |
| **Combinado** (MAESTROv3 + PianoVAM) | 95,2 % | 93,0 % | **73,5 %** | **86,9 %** |

O treino direto no PianoVAM eleva o F1 de *Note Onset* para 95,8 % e *Note w/ Velocity* para 93,9 %
(superando significativamente o MAESTROv3 segundo o teste de Friedman, p < 0,001, e testes post-hoc
de Wilcoxon com correção de Bonferroni, α = 0,0167), mantendo um *Note w/ Offset* de 60,4 % e
*Frame F1* de 80,0 %.

Contudo, o treino no conjunto **Combinado** (MAESTROv3 + PianoVAM) gera um **ganho sinérgico
decisivo na modelação temporal da sustentação**, elevando o F1 de *Note w/ Offset* para 73,5 % e o
*Frame F1* para 86,9 %, superando de forma estatisticamente significativa ambos os treinos isolados.

Nos sistemas multimodais que integram o HandSkeletonNet, os **erros remanescentes** sob mudança de
domínio devem-se maioritariamente a ligeiros **desalinhamentos temporais** e à **fragmentação de
notas** na descodificação MIDI quando ocorrem falhas momentâneas na deteção da mão — confirmando que
a **robustez à oclusão manual** e o **alinhamento temporal explícito** constituem as direções
prioritárias de investigação.

| Arquitetura / conjunto de dados | Domínio instrumental | Modalidades e representação de entrada | Métricas de desempenho e resultados quantitativos |
| --- | --- | --- | --- |
| **HandSkeletonNet + Omnizart** [cite: 16] | Piano solo (88 teclas) | Áudio + grafo esquelético 2D (MediaPipe, 42 nós, 2 camadas GCN + convolução temporal em profundidade). | Fusão tardia ponderada por mapa contínuo W (*Weight Floor* e *Weight Gamma*); tolerância de onset de ±50 ms. |
| ***Onsets and Frames*** (**benchmark PianoVAM**) [cite: 44] | Piano solo (partição 73/19/14 ficheiros) | Espectrogramas de áudio e validação áudio-visual (com ajuste de *offset* ao pedal de sustentação). | MAESTROv3: Nota 93,4 %, Offset 62,3 %, Vel. 90,3 %, Frame 78,2 %.<br>PianoVAM: Nota 95,8 %, Offset 60,4 %, Vel. 93,9 %, Frame 80,0 %.<br>Combinado: Nota 95,2 %, Offset 73,5 %, Vel. 93,0 %, Frame 86,9 %. |
| ***Framework* áudio-visual de baixo** (UIST) [cite: 5] | Baixo elétrico (4 cordas, 20 trastes) | Vídeo (Hough + 3σ + k-means; marcas 12-TET; MediaPipe + 10 % de *padding*) + áudio (CREPE Note) → Bi-LSTM. | Avaliado em 21 vídeos do YouTube (10 executantes); correspondência simultânea exata de dedo, corda e traste. |
| **Visually Informed MPS** (Dinesh, Bazzica et al.) | Cordas friccionadas / música de câmara | Fluxo ótico (deteção P/NP na mão do arco) + máxima verosimilhança espectral no áudio. | Convergência provada; elimina falsos positivos de altura tonal em instrumentos momentaneamente silenciosos. |

## 7. Síntese analítica e direções futuras para sistemas interativos

A evolução convergente entre processamento de sinal acústico, modelação biomecânica e visão
computacional sub-pixel evidencia uma **mudança de paradigma** na transcrição musical automática: a
transição de métricas puramente centradas na **altura tonal** para critérios de **viabilidade física
e ergonómica**.

A substituição da otimização cumulativa convencional pela norma L∞ no **algoritmo Minimax Viterbi** e
a criação de métricas específicas de **inexequibilidade de dedilhação** (*fingering unplayability*)
demonstram que **a utilidade prática de uma tablatura ou partitura gerada por inteligência artificial
é governada pelo seu ponto de maior estrangulamento biomecânico**. Sem treino explícito ou
restrições estruturais sobre a anatomia manual, modelos generativos e grandes modelos de linguagem
(LLMs) tendem a selecionar soluções matematicamente corretas em termos de altura tonal, mas
**fisicamente impossíveis** de articular por um executante humano, devido a:

- saltos de posição abruptos;
- extensões superiores a seis trastes;
- cruzamentos tendinosos adversos entre cordas.

Um **segundo vetor crítico** de evolução reside na resolução da transcrição de obras não nativas do
instrumento através da **transposição de oitava consciente do fluxo** (*stream-aware octave
transposition*). Quando se transcrevem para guitarra peças polifónicas densas ou obras orquestrais
cujas notas excedem o limite de seis cordas ou o alcance do braço, a simples rejeição de notas ou a
alteração isolada de oitava destrói a coerência contrapontística. Para superar esta limitação, as
arquiteturas de transcrição ao nível da notação necessitam de integrar **módulos de separação ao
nível do fluxo** (*stream-level transcription*), identificando primeiro a qual linha melódica ou voz
pertence a nota inexequível e aplicando a transposição de oitava de forma coesa a todas as notas
desse fluxo melódico, preservando a integridade musical enquanto satisfaz as restrições
combinatórias e probabilísticas do braço.

Finalmente, a consolidação destes modelos desbloqueia **aplicações transformadoras** em pedagogia
interativa, animação procedural tridimensional e personalização paramétrica de instrumentos:

- **pedagogia interativa** — sistemas de Realidade Aumentada (AR) e interfaces hápticas
  áudio-visuais utilizam o seguimento sem marcadores da cabeça e do braço da guitarra para projetar
  instruções codificadas por cores diretamente sobre a corda e o traste corretos (em visualização
  espelhada), recorrendo a **classificadores Bayesianos** para validar em tempo real se o acorde está
  a ser executado corretamente, permitindo ao estudante consolidar a memória muscular da posição da
  mão sem necessidade de olhar diretamente para a escala;
- **computação gráfica e síntese de movimento** — em *pipelines* automatizados (como em Blender via
  Python/PyYAML, ou no sistema SyncViolinist), ficheiros estruturados que combinam tablatura, dados
  MIDI, dedilhação de ambas as mãos, indicações de pestana (*barré*) e direção de ataque
  (*upstroke*/*downstroke*, como no formato Guitar Pro) permitem acionar bibliotecas de poses e
  restrições de ação para animar avatares digitais realistas, sincronizando a cinemática da mão
  esquerda com osciladores de vibração de corda;
- **personalização paramétrica do instrumento** — uma vez que a introdução de um **capotraste**
  (*capo*) ou a mudança para **afinações alternativas** equivale matematicamente a uma simples adição
  ou modificação dos valores do vetor de cordas soltas O, os motores de otimização dinâmica podem
  varrer instantaneamente diferentes configurações de afinação e posições de capotraste, para
  identificar a parametrização física do instrumento que minimiza o esforço biomecânico de uma peça
  ou para sintetizar exercícios técnicos adaptados ao perfil motor de cada músico.
