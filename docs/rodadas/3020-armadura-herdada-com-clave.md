# 3020 — armadura do vídeo também para leitura com clave e sem armadura

Trilha partitura. Data: 2026-10-15. Código: `tab/partitura_omr.py` (`herdar_condicao`,
`_tem_armadura`) e `tests/test_partitura_omr.py`.

## Problema

O recorte canon P06a mostra clave e 2 sustenidos, mas o Audiveris o leu sem `<key>`. A
herança da armadura do vídeo (rodada 3007) só valia para leituras sem clave, então o
recorte ficou em dó, e os fás e dós saíram naturais.

## Regra nova

A armadura do vídeo, quando não é 0, passa a ser aplicada se a leitura não tem clave **ou**
não tem `<key>`. Uma leitura com `<key>` escrito não muda, nem quando o `fifths` escrito é 0.

## Medições

- **Gabarito do dono (R01–R21):** `python -m tab.partitura_avaliar` deu saída idêntica antes
  e depois. Nenhum recorte do gabarito cai na regra nova: R18–R20 têm clave sem `<key>`,
  mas a armadura do vídeo deles é 0.
- **3 vídeos com produto:** nenhum `fifths_aplicado` mudou, e o `parear` deu o mesmo resumo:
  - greensleeves: 72 eventos, 72 com par;
  - gymnopédie: 186 eventos, 182 com par;
  - south american: 184 eventos, 184 com par.
- **Vídeos sem produto:** canon P06a passou de `fifths` None para 2, e 5 dos 29 eventos
  mudaram de altura (por exemplo, F4 → F#4). No athletic e no agua nada mudou.

Os backups e scripts estão em `data/saida/partitura/diag/herdar_clave/`.

## Limite

A regra assume que o recorte está na armadura da maioria do vídeo. Uma modulação para dó
lida sem `<key>` receberia a armadura errada. Ainda não foi visto no acervo.
