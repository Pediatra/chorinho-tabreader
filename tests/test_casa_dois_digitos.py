"""Casa de dois algarismos (`12`, `10`) pela forma das partes, e não só pelo vão.

Medido no ouro v2 (`docs/rodadas/0005-casa-dois-algarismos-vao.md`): o `12` fundido caía em
`tecnica` porque `compativel` exige dois componentes com haste, e o `2` não tem. Aqui a casa
sai da leitura das partes, e o vão entre dois algarismos só decide se eles são tentados
como um número (`_fundir_pares_de_digitos`).

Os testes de decisão e de fusão usam probabilidades fixas (sem GPU e sem pesos). O teste
ponta a ponta com o modelo real fica em `integration`, porque `artefatos/` não é versionado.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from tab import reconhecer
from tab.caminhos import PESOS_TABLATURA
from tab.reconhecer import (
    _casa_das_partes,
    _fundir_pares_de_digitos,
    _numero_de_dois_digitos,
    carregar_modelo,
    reconhecer_linha,
)
from tab.sintetico import FONTES

#: Classes do classificador oficial (mesmo conjunto que `artefatos/oficial_3`).
ROTULOS = [str(n) for n in range(10)] + [
    "10",
    "12",
    "14",
    "15",
    "17",
    "19",
    "21",
    "24",
    "harmonico",
    "tecnica",
]
PASSO = 20.0
MODELO_OFICIAL = PESOS_TABLATURA / "oficial_3" / "glifo_sint.pt"


def _vetor(pesos: dict[str, float]) -> np.ndarray:
    """Probabilidades por classe, com as classes dadas e o resto zerado."""
    v = np.zeros(len(ROTULOS))
    for classe, p in pesos.items():
        v[ROTULOS.index(classe)] = p
    return v


class _Glifo:
    """Token mínimo com a geometria que `_fundir_pares_de_digitos` lê."""

    def __init__(self, x0: float, x1: float, corda: int = 1) -> None:
        self.x0 = x0
        self.x1 = x1
        self.y0 = 10
        self.y1 = 30
        self.corda = corda
        self.coluna = x0
        self.area = 40
        self.partes = 1
        self.partes_digito = 1
        self.componentes = ((x0, 10, x1, 30),)


def _fundir_com(
    monkeypatch, tokens, filas: list[np.ndarray]
) -> tuple[list, set[int], dict[int, str], list[int]]:
    """Roda a fusão com `_probs` trocado por `filas` (um vetor por recorte) e conta as chamadas.

    Devolve ``(tokens_de_saida, ids_inseguros, fora_do_modelo, tamanhos_dos_lotes)``.
    """
    chamadas: list[int] = []

    def _probs(recortes, modelo, dev):
        chamadas.append(len(recortes))
        return np.stack(filas[: len(recortes)])

    monkeypatch.setattr(reconhecer, "_probs", _probs)
    saida, inseguros, fora = _fundir_pares_de_digitos(
        tokens, np.zeros((60, 200), np.uint8), PASSO, None, ROTULOS, "cpu"
    )
    return saida, inseguros, fora, chamadas


def test_casa_das_partes_12_com_confianca_vira_12() -> None:
    """Partes `1` e `2`, e o token inteiro dá 0,89 a `12`: a casa é `12`."""
    probs = _vetor({"12": 0.89, "tecnica": 0.11})
    assert _casa_das_partes(["1", "2"], probs, ROTULOS) == "12"


def test_casa_das_partes_sem_confianca_nao_vira_casa() -> None:
    """Mesmas partes, mas o token dá só 0,5 a `12`: não é número confiável."""
    probs = _vetor({"12": 0.5, "tecnica": 0.4})
    assert _casa_das_partes(["1", "2"], probs, ROTULOS) is None


def test_casa_das_partes_numero_que_o_modelo_nao_conhece_nao_vira_casa() -> None:
    """`13` não é classe do modelo: a casa de um glifo só sai de classe do modelo."""
    probs = _vetor({"tecnica": 0.9})
    assert _casa_das_partes(["1", "3"], probs, ROTULOS) is None


def test_casa_das_partes_20_de_um_glifo_fora_do_modelo_nao_vira_casa() -> None:
    """Um `3` de dois componentes lidos como `2` e `0` não vira `20`: `20` não é classe.

    Medido no gabarito de glifos (paolo, amostra 3): a regra fora do modelo, aplicada ao glifo
    de dois componentes, trocava um `3` certo por `20`.
    """
    probs = _vetor({"3": 0.9})
    assert _casa_das_partes(["2", "0"], probs, ROTULOS) is None


def test_casa_das_partes_so_com_algarismos() -> None:
    """Uma parte que não é algarismo (símbolo) impede a casa de dois dígitos."""
    probs = _vetor({"12": 0.95})
    assert _casa_das_partes(["1", "tecnica"], probs, ROTULOS) is None


def test_casa_das_partes_digito_unico_nao_vira_casa() -> None:
    """Um só componente nunca forma casa de dois dígitos."""
    probs = _vetor({"7": 0.95})
    assert _casa_das_partes(["7"], probs, ROTULOS) is None


def test_fundir_12_com_vao_entre_os_limites_funde(monkeypatch) -> None:
    """`1` e `2` com vão de 0,3 passo: o par vira um token só quando o número é `12`."""
    tokens = [_Glifo(0, 10), _Glifo(16, 28)]
    filas = [
        _vetor({"1": 0.9}),
        _vetor({"2": 0.9}),
        _vetor({"12": 0.9, "tecnica": 0.05}),
    ]
    saida, _, _, _ = _fundir_com(monkeypatch, tokens, filas)
    assert len(saida) == 1
    assert saida[0].partes == 2
    assert (saida[0].x0, saida[0].x1) == (0, 28)


def test_fundir_13_sem_classe_funde_quando_as_partes_sao_seguras(monkeypatch) -> None:
    """`1` (0,62) e `3` (0,99) com vão de 0,3 passo viram `13`, que o modelo não tem como classe."""
    tokens = [_Glifo(0, 10), _Glifo(16, 28)]
    filas = [_vetor({"1": 0.62}), _vetor({"3": 0.99}), _vetor({"tecnica": 0.9})]
    saida, inseguros, fora, _ = _fundir_com(monkeypatch, tokens, filas)
    assert len(saida) == 1
    assert saida[0].partes == 2
    assert inseguros == set()
    assert fora == {id(saida[0]): "13"}


def test_fundir_par_inseguro_nao_funde_e_vai_para_inseguros(monkeypatch) -> None:
    """`1` com 0,40 de confiança e vão de 0,3 passo: o par `1x` fica separado e marcado.

    A concatenação é casa possível, então o par não pode virar duas notas: quem chama o manda
    para símbolo cru (`nao_notas`).
    """
    tokens = [_Glifo(0, 10), _Glifo(16, 28)]
    filas = [
        _vetor({"1": 0.40, "7": 0.35}),
        _vetor({"3": 0.99}),
        _vetor({"tecnica": 0.9}),
    ]
    saida, inseguros, fora, _ = _fundir_com(monkeypatch, tokens, filas)
    assert len(saida) == 2
    assert inseguros == {id(tokens[0]), id(tokens[1])}
    assert fora == {}


def test_par_de_notas_distintas_fora_da_faixa_nao_e_inseguro(monkeypatch) -> None:
    """`2` e `7` (pág. 5): `27` não é casa, então não é par inseguro, só duas notas."""
    tokens = [_Glifo(0, 10), _Glifo(17, 27)]
    filas = [
        _vetor({"2": 0.93}),
        _vetor({"7": 0.97}),
        _vetor({"14": 0.08, "tecnica": 0.8}),
    ]
    saida, inseguros, fora, _ = _fundir_com(monkeypatch, tokens, filas)
    assert len(saida) == 2
    assert inseguros == set()
    assert fora == {}


def test_numero_de_dois_digitos_limites() -> None:
    """Casa é o número de 10 a 24 com dois algarismos: 09, 25 e 27 não são."""
    assert _numero_de_dois_digitos(["1", "0"])
    assert _numero_de_dois_digitos(["2", "4"])
    assert _numero_de_dois_digitos(["1", "3"])
    assert not _numero_de_dois_digitos(["0", "9"])
    assert not _numero_de_dois_digitos(["2", "5"])
    assert not _numero_de_dois_digitos(["2", "7"])
    assert not _numero_de_dois_digitos(["1", "tecnica"])


def test_fundir_nao_funde_dois_algarismos_de_notas_distintas(monkeypatch) -> None:
    """`2` e `7` com vão de 0,35 passo (pág. 5 do ouro) não viram `27`: não é classe."""
    tokens = [_Glifo(0, 10), _Glifo(17, 27)]
    filas = [
        _vetor({"2": 0.93}),
        _vetor({"7": 0.97}),
        _vetor({"14": 0.08, "tecnica": 0.8}),
    ]
    saida, _, _, _ = _fundir_com(monkeypatch, tokens, filas)
    assert len(saida) == 2


def test_vao_no_limiar_do_agrupar_nao_e_tocado(monkeypatch) -> None:
    """Vão de 0,2 passo já é fundido por `agrupar_tokens`: esta função não olha esse par."""
    tokens = [_Glifo(0, 10), _Glifo(14, 24)]
    saida, _, _, chamadas = _fundir_com(monkeypatch, tokens, [])
    assert saida == tokens
    assert chamadas == []


def test_vao_grande_demais_nao_e_tentado(monkeypatch) -> None:
    """Vão de 0,5 passo é nota distinta: nem chega ao classificador."""
    tokens = [_Glifo(0, 10), _Glifo(20, 30)]
    saida, _, _, chamadas = _fundir_com(monkeypatch, tokens, [])
    assert saida == tokens
    assert chamadas == []


def test_digito_unico_isolado_nao_muda(monkeypatch) -> None:
    """Um `7` sozinho passa intacto: a regra de casa de dois dígitos não toca dígito único."""
    tokens = [_Glifo(0, 10), _Glifo(40, 50, corda=2)]
    saida, _, _, chamadas = _fundir_com(monkeypatch, tokens, [])
    assert saida == tokens
    assert chamadas == []


def _linha_com_digitos(colunas: list[tuple[int, str]], passo: int = 24) -> np.ndarray:
    """Linha de tablatura sintética desenhada como o gerador (Liberation Bold, corda 2)."""
    larg, alt = 900, int(passo * 7.6)
    img = Image.new("RGB", (larg, alt), (255, 255, 255))
    d = ImageDraw.Draw(img)
    ys = [int(passo * 0.8) + i * passo for i in range(6)]
    for y in ys:
        d.line([(30, y), (larg - 30, y)], fill=(60, 60, 60), width=2)
    fonte = ImageFont.truetype(FONTES[0], int(passo * 0.75))
    for x, txt in colunas:
        bb = d.textbbox((0, 0), txt, font=fonte)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        px, py = int(x - w / 2), int(ys[1] - h / 2 - bb[1])
        d.rectangle(
            [px - 2, ys[1] - passo * 0.3, px + w + 2, ys[1] + passo * 0.3],
            fill=(255, 255, 255),
        )
        d.text((px, py), txt, font=fonte, fill=(0, 0, 0))
    return np.array(img)[:, :, ::-1].copy()


@pytest.mark.integration
@pytest.mark.skipif(
    not MODELO_OFICIAL.exists() or not FONTES,
    reason="precisa do modelo oficial (artefatos/ não é versionado) e das fontes Liberation",
)
def test_ponta_a_ponta_12_e_dois_separados() -> None:
    """Com o modelo real e o desenho do gerador: `12` sai como uma casa; `1  2`, duas notas."""
    modelo, rotulos, dev = carregar_modelo(str(MODELO_OFICIAL))
    casas_12 = [
        n["casa"]
        for n in reconhecer_linha(
            _linha_com_digitos([(300, "12")], passo=20), modelo, rotulos, dev
        )["notas"]
    ]
    casas_sep = [
        n["casa"]
        for n in reconhecer_linha(
            _linha_com_digitos([(290, "1"), (330, "2")], passo=20), modelo, rotulos, dev
        )["notas"]
    ]
    assert casas_12 == ["12"]
    assert casas_sep == ["1", "2"]
