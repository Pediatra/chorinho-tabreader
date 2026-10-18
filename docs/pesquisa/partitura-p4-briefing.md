# P4 da partitura — o documento final por vídeo — briefing

**Data**: 2026-10-18. **Origem**: onda 1 fechada (`ESTADO.md`, seção "Partitura — 2026-10-18") e
rodada 3026: a pesquisa da partitura terminou, e o que funciona entra no documento por vídeo.
**Para quem**: o dono, que abre a worktree e um agente (Haiku 5.5) e cola o briefing abaixo.

## Como abrir a worktree

```bash
git worktree add ../chorinho-wt-part-p4 -b part/p4-produto main
```

A pasta de escrita da frente já existe na cópia principal: `data/saida/part_frentes/fp_produto/`
(e `artefatos/part_frentes/fp_produto/`). A montagem é a do `partitura-frentes.md`, seção 6.1,
com `FRENTE=fp_produto`.

Quando o agente terminar, avise a sessão principal com o nome do branch. Ela confere de novo na
`main`, regera os 3 documentos na pasta de verdade (`data/saida/partitura/video/`) e consolida o
`ESTADO.md`.

## Briefing

```text
Você trabalha na worktree ../chorinho-wt-part-p4 (branch part/p4-produto) do projeto chorinho.
Leia inteiro, antes de rodar qualquer coisa: AGENTS.md; docs/pesquisa/partitura-p4-briefing.md
(este arquivo); docs/pesquisa/partitura-frentes.md, seções 6.1 e 9; docs/decisoes/3002; as
rodadas 3013, 3014, 3015, 3170, 3172 e 3026 em docs/rodadas/; tab/partitura_video.py (funções
_pauta_do_recorte, _simbolo_do_documento, _contagens_da_pauta, parear_produto, eventos_do_produto)
e tab/partitura_completar.py (_completar, _grupo_produtos).

Contexto em uma frase: o documento <stem>.partitura.json já junta a leitura do Audiveris, as
notas do homr confirmadas pela tab, o par com a coluna da tab (que dá o tempo) e a armadura do
vídeo. Falta pôr nele a nota que a tab tem e a pauta não leu, e um aviso de qualidade por pauta.

TAREFA

1. Função pura de completar, sem importar tab.partitura_video (para não criar import circular):
   crie tab/partitura_completar_pauta.py e MOVA para lá _completar e as funções de que ela
   depende (_normalizar, _duracao, _candidato_oitava, _compasso_de_x, _figura_do_deficit,
   _soma_do_compasso, _seminimas_compasso e as constantes). tab/partitura_completar.py passa a
   importar de lá. Depois de mover, `python -m tab.partitura_completar` tem de gravar um e1.json
   igual ao atual (compare campo a campo com
   /app/data/saida/part_frentes/fe_completar/e1.json; grave o seu na pasta fp_produto).

2. Em tab/partitura_video.py, _pauta_do_recorte passa a completar a pauta, depois do
   reparear_por_x. Regras (decisão do dono, rodada 3172):
   - a nota completada tem a altura e o instante da tab e "figura": null, "pontuada": false,
     SEMPRE. Não use a figura que _completar calcula: a decisão é não chutar figura;
   - tipo "acorde" (a coluna já tem evento da partitura pareado com confere_x verdadeiro): o
     símbolo entra na lista "simbolos" desse evento;
   - tipo "isolado" (a coluna não tem evento pareado): entra um evento novo, com "compasso" de
     _compasso_de_x, "t": null, "x_quadro" = x da coluna da tab, "simbolos" com as notas, e
     "par" = {"tela", "coluna", "distancia_x": 0.0, "confere_x": true, "metodo": "tab"}. Os
     eventos da pauta ficam em ordem de x_quadro;
   - o símbolo completado tem os mesmos campos de _simbolo_do_documento: "nome" (do midi, com
     _nome de tab/partitura_completar_itens.py, importada de lá), "midi_escrito", "figura": null,
     "pontuada": false, "voz" (a de _completar), "ligadura_inicio": false,
     "ligadura_fim": false, "notacoes": [], "origem": "tab_completada";
   - harmônico: no produto da tab ele é a nota com "tecnica" == "harm" (o _completar de hoje
     procura n["harmonico"], que não existe no produto: conserte no módulo novo). Se a pauta já
     tem a nota uma oitava acima no mesmo x (_candidato_oitava, regra da 3013), NÃO complete:
     ela já está lá. Senão, complete, e acrescente "harmonico": true ao símbolo;
   - nota com "tecnica" == "lig" (casa ligada, entre parênteses) não é ataque novo: não
     complete, e conte;
   - nunca descarte nem mude um símbolo que já existe. A tela 10 da Gymnopédie (tab com cordas
     deslocadas, erro da trilha da tablatura) segue a regra geral; só conte à parte.

3. Aviso de qualidade em cada pauta do documento: "pauta_pequena": entrelinha < 16.0 (rodada
   3026: abaixo disso o Audiveris perde de 5 a 8 pontos de cobertura) e "leitura_ok": false
   quando a pauta tem "erro", true quando não. No "resumo" do documento acrescente
   "completadas_acorde", "completadas_isolado", "nao_completadas_harmonico",
   "nao_completadas_ligada" e "pautas_pequenas". Em "gerado_por" acrescente
   "completar_tab": "nota da tab sem nota na pauta, figura null (rodada 3172)". O esquema
   continua "chorinho/partitura@1" (só há campos novos).

4. parear_produto ganha o parâmetro opcional pasta_video (padrão: a pasta de hoje), e a CLI
   `parear` ganha --pasta-video, só para gravar fora de data/saida/partitura/video/. Na worktree
   essa pasta é só de leitura: copie data/saida/partitura/video/<stem>/ dos 3 vídeos para
   data/saida/part_frentes/fp_produto/video/ e rode parear lá. Os 3 stems:
   greensleeves_guia_de_estudio_partitura_tab_pdf,
   south_american_music_easy_guitar_tutorial_with_sheet_and_tab,
   gymnopedie_no_1_erik_satie_includes_sheet_musictab_classical_guitar.
   Os produtos da tab ficam em data/saida/fase8/rede/<stem>.json (só leitura).

5. Testes novos em tests/test_partitura_video.py e tests/test_partitura_completar_pauta.py, sem
   data/saida, sem artefatos e sem acervo, com dados montados à mão: acorde entra no evento;
   isolado vira evento novo em ordem de x; figura sempre null; harmônico com oitava na pauta
   não entra; "lig" não entra; símbolo existente intacto.

ACEITE (congelado; escreva-o na rodada 3027 ANTES de medir)

- Os 3 documentos novos, comparados com os atuais (/app/data/saida/partitura/video/<stem>/
  <stem>.partitura.json): todos os eventos e símbolos que já existiam ficam idênticos, campo a
  campo, e nenhum evento perde o par. Só entram símbolos com origem "tab_completada", eventos
  novos com metodo "tab" e os campos novos do item 3. Escreva o script de comparação na pasta
  fp_produto e mostre a saída dele.
- Completadas fora da tela 10 da Gymnopédie: 37 na E1 (30 de acorde, 7 isoladas). O número
  novo pode ser menor só pelos harmônicos com oitava e pelas notas "lig"; explique cada
  diferença, nota a nota.
- Toda nota completada tem figura null.
- e1.json regerado igual ao atual, salvo o campo de harmônico corrigido (explique a diferença).
- python data/saida/partitura/diag/ca1/ca1.py (imagem docker.io/library/chorinho:dev) dá as
  mesmas linhas de antes; a linha "E." não conta.
- Gate verde na worktree: ruff check --no-cache . && ruff format --check --no-cache . &&
  pytest tests/ -q -p no:cacheprovider.

TERRITÓRIO

- Pode editar: tab/partitura_video.py, tab/partitura_completar.py, o novo
  tab/partitura_completar_pauta.py, os testes deles, docs/rodadas/3027-*.md.
- Escreve só em data/saida/part_frentes/fp_produto/.
- Proibido: data/gold/, ESTADO.md, tab/esquema.py, tab/musicxml.py e qualquer arquivo de outra
  trilha (tablatura, mãos, áudio); dependência nova; commit em main; GPU; ler vídeo.
- Tudo em CPU, na imagem docker.io/library/chorinho:dev (não precisa do Audiveris: as leituras
  já estão gravadas).

PARE e relate, sem contornar, se: o e1.json regerado no passo 1 não bater; algum símbolo que já
existia mudar; a montagem vier vazia (ls /app/data/saida/partitura/video tem de listar os 3
stems).

ENTREGA

Rodada docs/rodadas/3027-partitura-documento-final.md (aceite congelado, resultado com
denominadores, tabela por vídeo: pautas, pautas pequenas, completadas de acorde, isoladas,
não completadas por harmônico e por "lig", e a tela 10 da Gymnopédie à parte; e 5 notas
completadas olhadas no recorte, com o nome do arquivo); gate verde; um commit no branch com o
número na mensagem, terminado em "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>";
resumo curto em português para o dono.
```
