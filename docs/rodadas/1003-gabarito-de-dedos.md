# Rodada 1003: gabarito de dedos do dono (M2)

Data: 2026-10-12. Trilha das mãos, M2 (ver `docs/guias/contexto-maos.md`, seção M2).
Próxima rodada: [1004, dedo por visão](1004-dedo-por-visao.md) (M3).

## Objetivo

Medir a ligação nota → dedo: para cada nota da tablatura tocada, qual dedo da mão esquerda
pisa e qual dedo da mão direita toca. O rótulo é do dono e é **contrato**: o agente não
rotula, não infere e não relabela por proxy. Todo número da M3 depende deste gabarito.

## Vídeo escolhido

`sky guitar/retrato brasileiro - tab & lesson.mp4`, o vídeo do MVP. Escolhido porque:

- já tem a tablatura e as notas com `t_ini` (`tab.mvp`), sem transcrição nova;
- mostra as mãos: a direita numa câmera e a esquerda na câmera do braço, que é frontal e
  fixa.

Ele é um vídeo só. A amostra não cobre outros canais nem outros enquadramentos.

## Ferramenta

Módulos: `tab/maos_gabarito.py` (amostra, registro, servidor), `tab/maos_gabarito_preparar.py`
(material por ataque, na GPU). Caminhos em `tab/caminhos.py` (`GABARITO_DEDOS`, `MAOS_DEDOS`).

- **Amostra**: 40 itens sorteados com semente 20261012 (`amostrar_notas`): 32 notas com casa
  maior que 0 e 8 de corda solta (casa 0). Dentro de cada grupo, as notas são ordenadas por
  `t_ini` e divididas em faixas de contagem igual; sorteia-se uma por faixa. A amostra é
  estratificada no tempo.
- **Unidade é o ataque**: notas com a mesma tela, coluna e `t_ini`, ou seja, uma batida de
  acorde. Os 40 itens sorteados viraram **40 ataques e 56 notas** (28 ataques de uma nota,
  12 de 2 a 4 notas). Num acorde, todas as notas soam com os dedos no mesmo quadro.
- **Pestana por ataque**: `nao`, `sim` ou `?`. Com `sim`, o dono informa o dedo, a casa e as
  cordas de/até. A pestana é um campo do ataque, não de cada nota.
- **Recortes**: a mão esquerda em `t_ini` e a direita em `t_ini - 0,15 s`, `t_ini` e
  `t_ini + 0,15 s`, com a mesma caixa, ampliada 40 % para cada lado. O quadro mostra um
  retângulo só no algarismo de cada nota, com o rótulo da corda.
- **Gravação**: a cada clique, em escrita atômica (`gravar_atomico`), no padrão de
  `tab.ouro_video`. Nunca apaga resposta existente. Gabarito no formato 3.

## Três correções do dono durante o uso

O dono usou a ferramenta e apontou três defeitos. Cada um foi corrigido num commit próprio:

1. **Marcava a coluna inteira da tablatura** (`423b9011`). Em acorde, o dono não sabia qual
   nota estava sendo perguntada. Agora um retângulo pequeno marca só o algarismo da corda da
   nota, com as linhas achadas por `tabseg.segmentar`.
2. **Perguntava uma nota só do acorde** (`b4461d45`). Jogava fora informação, porque num acorde
   todas as notas soam. A unidade passou a ser o ataque: uma linha de botões por nota, linha
   ativa no teclado (setas cima e baixo), avanço automático quando o ataque fica completo.
3. **Pestana não preenchia o dedo das notas cobertas e não avançava** (`561028ca`). Com
   `sim`, cada nota na casa da pestana, entre as cordas de/até e ainda sem dedo da esquerda,
   recebe o dedo da pestana (nunca sobrescreve resposta), e o ataque completo avança.

**Lição**: testar a ferramenta como o dono vai usar, com acorde e pestana, antes de entregar.
Os três defeitos foram achados pelo dono, depois da entrega, e não pelo gate (que passava
com 464 a 507 testes nos commits da fase).

## Resultado

Gabarito `data/gold/maos/dedos_retrato_brasileiro.json`, formato 3, dono em 2026-10-12.
Distribuições (commit `9fa22548`):

- **Esquerda** (56 notas): 1 = 14, 0 = 13, 2 = 10, 3 = 8, 4 = 8, ? = 3.
- **Direita** (56 notas): p = 17, a = 16, m = 10, i = 10, ? = 3.
- **Pestana** (40 ataques): sim = 6, não = 33, ? = 1. As seis `sim` têm dedo 1, casas 2, 2, 5,
  4, 2 e 7, e cobrem de 3 a 6 cordas.

Migração pura e idempotente: as 6 respostas de nota que o dono já tinha (`7be3a880`) foram
preservadas campo a campo.

## Confiabilidade

Dita pelo dono no bloco `confiabilidade` do gabarito:

- **Esquerda: alta**, lida no quadro pelo dono.
- **Direita: PARCIAL**. Poucos quadros por ataque. Parte das respostas foi inferida pelo dono
  pela distância e pela corda preferida de cada dedo, sem marcar quais. Usar só como
  indicativo. Três notas trazem essa dúvida na `obs`: `n05` ("dou 65% anelar"), `n08` e `n12`
  ("pela lógica é médio").
- **`n19` excluída**: "a casa 3 da corda 3 não está sendo apertada nesse instante". A nota e
  o tempo do produto estão errados ali.
- **`a22` duplicada**: é o mesmo ataque que o `a21` (o sorteio caiu duas vezes no mesmo
  acorde). A medição deduplica pela nota física.

## Comandos

Material, na GPU (dentro do container, como no M1):

```bash
python -m tab.maos_gabarito_preparar --video "/acervo/sky guitar/retrato brasileiro - tab & lesson.mp4"
```

O `--video` é o padrão; o material vai para `data/saida/maos/m2/dedos` e o gabarito é criado
ou atualizado sem apagar respostas.

Servidor de rotulagem (grava a cada clique):

```bash
python -m tab.maos_gabarito servir --pasta data/saida/maos/m2/dedos \
    --ouro data/gold/maos/dedos_retrato_brasileiro.json --porta 8098
```

No host (distrobox), o servidor roda em segundo plano na imagem das mãos:

```bash
host-spawn -no-pty -cwd /var/home/gabriel/Projects/chorinho-dataset sh -c "podman run -d --name maos-dedos --rm --security-opt label=disable -e PYTHONPATH=/app -w /app -v /var/home/gabriel/Projects/chorinho-dataset:/app -p 127.0.0.1:8098:8098 localhost/chorinho-maos:dev python -m tab.maos_gabarito servir --pasta data/saida/maos/m2/dedos --ouro data/gold/maos/dedos_retrato_brasileiro.json --porta 8098 --host 0.0.0.0"
```

Abrir `http://127.0.0.1:8098/`; parar com `podman stop maos-dedos`. Não usar `-it` via
host-spawn (sem terminal, o container não sobe). O servidor carrega a página na partida:
depois de mudar o código, reiniciar o servidor e recarregar a aba.

## Artefatos

- Gabarito: `data/gold/maos/dedos_retrato_brasileiro.json`.
- Material: `data/saida/maos/m2/dedos/` (quadros e recortes por ataque); logs
  `data/saida/maos/m2/preparar*.log`.
- Código: `tab/maos_gabarito.py`, `tab/maos_gabarito_preparar.py`, `tab/caminhos.py`.
- Commits: `9ba059ce` (ferramenta), `423b9011`, `b4461d45`, `7be3a880`, `561028ca` (correções),
  `9fa22548` (gabarito rotulado).
