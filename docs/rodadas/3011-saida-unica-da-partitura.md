# 3011 — Saída única da partitura: armadura + homr confirmado + pareamento

**Data:** 2026-10-14 · **Trilha:** partitura (P3) · **Código:** `tab/partitura_pareamento.py`
(`completar_com_homr`), `tests/test_partitura_pareamento.py`

## Pergunta

As melhorias das rodadas 3006, 3009 e 3010 foram medidas cada uma sozinha. Quanto dá tudo
junto, numa saída só por recorte?

## Cadeia

1. **Leitura:** Audiveris x2 sobre o recorte com margem 7/7.
2. **Armadura:** a do vídeo, aplicada às leituras sem clave (condição `x2_margem_herdada`).
3. **homr:** notas do homr nativo que a tab confirma, no mesmo evento casado. Cada nota guarda
   `origem` (`audiveris` ou `homr`).
4. **Pareamento:** cada evento é pareado com a coluna da tab, com conferência pelo x. O
   tempo vem do `t_ini` da coluna.

```bash
python -m tab.partitura_pareamento   # data/saida/partitura/p3/pareamento/<id>.json
```

## Resultado (R01–R12, 546 notas da tab)

| | certas | altura errada | faltando | inventada | notas erradas (altura errada + inventada) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Audiveris x2_margem (3003) | 491 | 14 | 41 | 3 | 17 |
| + armadura do vídeo | 494 | 11 | 41 | 3 | 14 |
| **+ homr confirmado pela tab** | **526 (96,3 %)** | 6 | 14 | 8 | **14** |

- **Notas do homr:** 32 entraram.
- **Pareamento:** 336 de 337 pares no mesmo x do quadro. O único fora da tolerância continua o
  do R05 (rodada 3010).
- **Por que as inventadas parecem subir (3 → 8):** o número de notas erradas não muda (14).
  Em 5 eventos, o Audiveris tinha lido uma altura errada, e o homr acrescentou a certa ao lado.
  A errada continua lá e passa a contar como "inventada", em vez de "altura errada". A junção
  não traz nota nova que a tab não tenha.

## Próximo

- **Altura errada com a certa ao lado:** quando a tab confirma a nota do homr e não a do
  Audiveris no mesmo evento, a do Audiveris poderia sair. Isso é corrigir altura pela tab, e
  fica para decidir com o dono.
- **Tempo:** depende de a trilha tablatura entregar `t_ini` por nota.

## Limites

- **Amostra:** 3 vídeos e 12 recortes.
- **Régua:** a medida é contra a tab, não contra o gabarito do dono.
- **Figura:** a das 32 notas do homr não foi conferida.
