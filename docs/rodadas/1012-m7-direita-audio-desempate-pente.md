# 1012 — M7: tempo pelo áudio, métrica de desempate e pente das cordas

**Data**: 2026-10-15. Continua a [1011](1011-m7-direita-corda-pelas-pontas.md). Itens
autorizados pelo dono, com os três cuidados dele (janela recentrada no som; folga na região da
mão esquerda; pente por resposta de linha fina, não por borda).

## Item 1 — instante pelo áudio (`tab/maos_direita_audio.py`, `tab/maos_direita_tempo_audio.py`)

Alinhador da trilha do áudio (`tab.audio_alinhar`, sem modificação) rodado nos 4 vídeos sobre o
produto da M7 (o `a5/v21_mvp.audio.json` era de outro produto, sha diferente). Ataques com
`t_audio`: retrato 630/637, noturno 392/464, lacrimosa 317/322, glimpse 323/415.
`t_audio − t_ini` (mediana): 178, 275, 186, 165 ms — o marcador vem antes do som, como na A1.

Energia de movimento sincronizada ao `t_audio`: **pico entre −0,07 e 0,00 s nos 4 vídeos**
(`data/saida/maos/m7/tempo_audio.png`), curva mais estreita que a sincronizada ao `t_ini`.
Janela escolhida para o preditor: −0,10 … +0,07 s em torno do som. **O tempo do áudio é a
referência certa para a mão direita.**

## Item 2 — desempate e F1 por corda (`tab/maos_direita_desempate.py`)

Notas ambíguas só pela altura: 92–96%. Com a região da mão = casa real ±2 (ou ±3): 4,5–8%.
**Leitura minha (revisor): ±2/±3 em volta da casa REAL vaza a resposta.** Cordas vizinhas
distam 4–5 casas, então qualquer janela de ±2/±3 centrada na casa verdadeira exclui as
alternativas por construção (por isso ±2 = ±3). Não simula o erro da câmera da esquerda. A
estimativa com janela tirada das casas das notas vizinhas (±1 s, sem a própria nota) deu
25–42% (medida no chat em 2026-10-15) — também otimista, por usar a tablatura. O número real
depende da posição da mão esquerda dada pela visão (M3).

Desempate nas notas ambíguas só pela altura, nos 120 ataques: preditor visual 48% (janela
antiga) e 59% (janela depois); **base "casa mais baixa" 88%**; base "corda mais frequente" 65%.
**A visão da direita perde para uma regra trivial de posição.**

F1 por corda (6 decisões por ataque): visual 0,390 (antes) e 0,439 (depois); base corda mais
frequente 0,279.

## Item 3 — cordas pela imagem mediana + pente (`tab/maos_direita_cordas_pente.py`) — REPROVADO

Correlação de fase falhou (a câmera da direita muda de enquadramento ao longo do vídeo); o
registro por ORB+RANSAC gerou uma mediana **incoerente** (`mediana_retrato_brasileiro.png`:
pedaços de cena girados e sobrepostos — conferido pelo revisor; o relatório do agente a
descrevia como nítida). Pente de 5 parâmetros ancorado nos bordões: espaçamentos 6→5→4
incompatíveis com cordas reais (21 e 54 px; 49 e 65 px). A "crista" favoreceu o pente, mas o
olho não confirma: a crista premia qualquer estrutura clara e não serve para validar cordas.

## Não repetir

- Janela de folga centrada na casa real para simular a mão esquerda (vaza a resposta).
- Mediana temporal do painel da direita sem antes segmentar os trechos de enquadramento igual.
- "Crista" como critério de corda certa.
