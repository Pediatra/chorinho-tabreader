"""Esquema da base das mãos (``chorinho/maos@1``): o que é um par bem formado.

A base das mãos (decisão 1007) guarda, por vídeo, dois arquivos lado a lado:
``<nome>.maos.json``, com os eventos (uma nota do produto cada), as checagens e o
nível; e ``<nome>.maos.npz``, o denso: mãos, corpo, braço do violão e caixa da
tablatura, quadro a quadro. Este módulo diz o que cada um precisa ter e devolve a
lista de erros. Não importa o motor nem o OpenCV: usa só numpy e a biblioteca padrão.

O par junta-se pela chave do evento (``chorinho/video@1``). A partitura entra pela
chave da coluna e não tem campo aqui.

Uso pela linha de comando::

    python -m tab.maos_esquema ARQUIVO.maos.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np

ESQUEMA = "chorinho/maos@1"

#: Níveis de um evento, do melhor ao recusado.
NIVEIS = ("ouro", "prata", "recusado")

#: Checagens de cada evento. Todas precisam estar presentes.
CHECAGENS = ("K1", "K2", "K3", "K4")

#: Origens aceitas do capotraste.
FONTES_CAPOTRASTE = ("tela", "canal", "imagem", "dono")

#: Matrizes do ``.npz``: nome -> (forma sem o N, dtype).
MATRIZES: dict[str, tuple[tuple[int, ...], type]] = {
    "pts": ((), np.float64),
    "maos": ((2, 21, 3), np.float32),
    "maos_origem": ((2,), np.int8),
    "maos_trilha": ((2,), np.int16),
    "corpo": ((6, 3), np.float32),
    "braco_trastes": ((25, 2), np.float32),
    "braco_corda1": ((2, 2), np.float32),
    "braco_corda6": ((2, 2), np.float32),
    "braco_conf": ((), np.float32),
    "braco_achou": ((), np.bool_),
    "tab_caixa": ((4,), np.float32),
}

#: Folga, em fração da largura e da altura, além da qual um ponto está fora do quadro.
FOLGA = 0.05

#: Campos que identificam um evento (a chave de ``chorinho/video@1``).
CHAVE_EVENTO = ("tela", "passagem", "exibicao", "coluna", "corda", "t_ini")

_CHAVES_RAIZ = (
    "esquema",
    "produto",
    "produto_sha256",
    "audio",
    "audio_sha256",
    "denso",
    "denso_sha256",
    "video",
    "gerado_por",
    "violao",
    "eventos",
    "resumo",
)

_HEX64 = re.compile(r"[0-9a-f]{64}")


def _inteiro(valor: object) -> bool:
    """Inteiro de verdade (``bool`` não conta).

    Args:
        valor: qualquer objeto.

    Returns:
        ``True`` se ``valor`` é ``int`` e não ``bool``.
    """
    return isinstance(valor, int) and not isinstance(valor, bool)


def _inteiro_entre(valor: object, minimo: int, maximo: int | None = None) -> bool:
    """Inteiro dentro de um intervalo fechado (``maximo`` ``None`` = sem teto).

    Args:
        valor: qualquer objeto.
        minimo: menor valor aceito.
        maximo: maior valor aceito, ou ``None``.

    Returns:
        ``True`` se ``valor`` é inteiro e está no intervalo.
    """
    if not _inteiro(valor) or valor < minimo:
        return False
    return maximo is None or valor <= maximo


def _real(valor: object) -> bool:
    """Número real finito (``bool`` não conta).

    Args:
        valor: qualquer objeto.

    Returns:
        ``True`` se ``valor`` é ``int`` ou ``float``, não é ``bool`` e é finito.
    """
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return False
    return math.isfinite(valor)


def _nao_negativo(valor: object) -> bool:
    """Número real finito maior ou igual a zero.

    Args:
        valor: qualquer objeto.

    Returns:
        ``True`` se ``valor`` é real finito e ``>= 0``.
    """
    return _real(valor) and valor >= 0


def _opcional(valor: object, teste: Callable[[object], bool]) -> bool:
    """Aceita ``None`` ou um valor que passa em ``teste``.

    Args:
        valor: qualquer objeto.
        teste: função que diz se um valor não nulo é aceito.

    Returns:
        ``True`` se ``valor`` é ``None`` ou passa em ``teste``.
    """
    return valor is None or teste(valor)


def _texto(valor: object) -> bool:
    """Texto não vazio (espaços não contam).

    Args:
        valor: qualquer objeto.

    Returns:
        ``True`` se ``valor`` é ``str`` com algum caractere além de espaços.
    """
    return isinstance(valor, str) and valor.strip() != ""


def _hash(valor: object) -> bool:
    """SHA-256 em hexadecimal minúsculo, com 64 caracteres.

    Args:
        valor: qualquer objeto.

    Returns:
        ``True`` se ``valor`` é texto de 64 dígitos hexadecimais minúsculos.
    """
    return isinstance(valor, str) and _HEX64.fullmatch(valor) is not None


def _janela_valida(valor: object) -> bool:
    """Janela ``[i0, i1]`` com inteiros e ``0 <= i0 < i1``.

    Args:
        valor: o campo ``janela`` de um evento, não nulo.

    Returns:
        ``True`` se é uma lista de dois inteiros bem ordenados.
    """
    if not isinstance(valor, list) or len(valor) != 2:
        return False
    if not all(_inteiro(v) for v in valor):
        return False
    return 0 <= valor[0] < valor[1]


def _passou(checagens: dict, chave: str) -> object:
    """Valor de ``passou`` de uma checagem, ou ``None`` se ela não existe.

    Args:
        checagens: o dicionário ``checagens`` de um evento.
        chave: ``K1``, ``K2``, ``K3`` ou ``K4``.

    Returns:
        O ``passou`` da checagem, ou ``None``.
    """
    bloco = checagens.get(chave)
    return bloco.get("passou") if isinstance(bloco, dict) else None


def nivel_esperado(checagens: dict) -> str:
    """Nível que as checagens de um evento determinam (decisão 1007).

    ``ouro`` exige as quatro com ``passou`` true. ``prata`` exige K1, K3 e K4 true e K2
    diferente de true. Todo o resto é ``recusado``.

    Args:
        checagens: o dicionário ``checagens`` de um evento, com K1 a K4.

    Returns:
        ``"ouro"``, ``"prata"`` ou ``"recusado"``.
    """
    if not isinstance(checagens, dict):
        return "recusado"
    passou = {chave: _passou(checagens, chave) for chave in CHECAGENS}
    if all(valor is True for valor in passou.values()):
        return "ouro"
    if (
        passou["K1"] is True
        and passou["K3"] is True
        and passou["K4"] is True
        and passou["K2"] is not True
    ):
        return "prata"
    return "recusado"


def _json_raiz(doc: dict) -> list[str]:
    """Esquema e presença dos campos obrigatórios da raiz.

    Args:
        doc: o JSON já carregado.

    Returns:
        Lista de erros; vazia se o esquema é ``chorinho/maos@1`` e nenhum campo falta.
    """
    erros: list[str] = []
    if doc.get("esquema") != ESQUEMA:
        erros.append(f"esquema {doc.get('esquema')!r}, esperado {ESQUEMA!r}")
    for campo in _CHAVES_RAIZ:
        if campo not in doc:
            erros.append(f"falta o campo '{campo}'")
    return erros


def _json_fontes(doc: dict) -> list[str]:
    """Caminhos e hashes dos arquivos de origem (produto, áudio e denso).

    Args:
        doc: o JSON já carregado.

    Returns:
        Lista de erros dos caminhos e hashes.
    """
    erros: list[str] = []
    for campo in ("produto", "denso"):
        if not _texto(doc.get(campo)):
            erros.append(f"{campo} ausente ou vazio")
    for campo in ("produto_sha256", "denso_sha256"):
        if not _hash(doc.get(campo)):
            erros.append(f"{campo} não é 64 hexadecimais minúsculos")
    audio, audio_sha = doc.get("audio"), doc.get("audio_sha256")
    if (audio is None) != (audio_sha is None):
        erros.append("audio e audio_sha256 devem ser nulos juntos")
    elif audio is not None and not _texto(audio):
        erros.append("audio deve ser texto ou null")
    elif audio_sha is not None and not _hash(audio_sha):
        erros.append("audio_sha256 não é 64 hexadecimais minúsculos")
    return erros


def _json_video(video: object) -> list[str]:
    """Bloco ``video``: arquivo, fps e dimensões do quadro.

    Args:
        video: o campo ``video``.

    Returns:
        Lista de erros do bloco.
    """
    if not isinstance(video, dict):
        return ["video não é objeto"]
    erros: list[str] = []
    if not _texto(video.get("arquivo")):
        erros.append("video.arquivo ausente ou vazio")
    fps = video.get("fps")
    if not (_real(fps) and fps > 0):
        erros.append("video.fps deve ser número positivo")
    for campo in ("largura", "altura"):
        if not _inteiro_entre(video.get(campo), 1):
            erros.append(f"video.{campo} deve ser inteiro positivo")
    return erros


def _json_gerado(gerado: object) -> list[str]:
    """Bloco ``gerado_por``: commit e detectores usados.

    Args:
        gerado: o campo ``gerado_por``.

    Returns:
        Lista de erros do bloco.
    """
    if not isinstance(gerado, dict):
        return ["gerado_por não é objeto"]
    erros = [
        f"gerado_por.{campo} ausente ou vazio"
        for campo in ("commit", "detector_maos", "detector_braco")
        if not _texto(gerado.get(campo))
    ]
    if not isinstance(gerado.get("parametros"), dict):
        erros.append("gerado_por.parametros não é objeto")
    return erros


def _json_violao(violao: object) -> list[str]:
    """Bloco ``violao``: canhoto, capotraste e a origem do capotraste.

    Args:
        violao: o campo ``violao``.

    Returns:
        Lista de erros do bloco.
    """
    if not isinstance(violao, dict):
        return ["violao não é objeto"]
    erros: list[str] = []
    canhoto = violao.get("canhoto")
    if canhoto is not None and not isinstance(canhoto, bool):
        erros.append("violao.canhoto deve ser booleano ou null")
    capo = violao.get("capotraste")
    fonte = violao.get("capotraste_fonte")
    if capo is None:
        if fonte is not None:
            erros.append(
                "violao.capotraste_fonte deve ser null quando capotraste é null"
            )
    elif not _inteiro_entre(capo, 0, 12):
        erros.append("violao.capotraste deve ser inteiro de 0 a 12 ou null")
    elif fonte not in FONTES_CAPOTRASTE:
        erros.append(f"violao.capotraste_fonte {fonte!r} inválida")
    return erros


def _json_chave(ev: dict, onde: str) -> list[str]:
    """Tipos e faixas dos campos de um evento (chave, tempos e janela).

    Args:
        ev: o evento.
        onde: texto para localizar o erro (ex.: ``evento 3``).

    Returns:
        Lista de erros dos campos do evento.
    """
    testes = [
        ("tela", _inteiro_entre(ev.get("tela"), 1), "inteiro ≥ 1"),
        (
            "passagem",
            _opcional(ev.get("passagem"), lambda v: _inteiro_entre(v, 1)),
            "inteiro ≥ 1 ou null",
        ),
        (
            "exibicao",
            _opcional(ev.get("exibicao"), lambda v: _inteiro_entre(v, 0)),
            "inteiro ≥ 0 ou null",
        ),
        ("coluna", _inteiro_entre(ev.get("coluna"), 1), "inteiro ≥ 1"),
        ("corda", _inteiro_entre(ev.get("corda"), 1, 6), "inteiro de 1 a 6"),
        ("casa", _inteiro_entre(ev.get("casa"), 0, 24), "inteiro de 0 a 24"),
        (
            "t_ini",
            _opcional(ev.get("t_ini"), _nao_negativo),
            "número ≥ 0 ou null",
        ),
        (
            "t_som",
            _opcional(ev.get("t_som"), _nao_negativo),
            "número ≥ 0 ou null",
        ),
        (
            "janela",
            _opcional(ev.get("janela"), _janela_valida),
            "[i0, i1] com 0 ≤ i0 < i1, ou null",
        ),
    ]
    return [
        f"{onde}: {campo} inválido (esperado {esperado})"
        for campo, valido, esperado in testes
        if not valido
    ]


def _json_checagens(checagens: object, onde: str) -> list[str]:
    """Bloco ``checagens``: K1 a K4, cada uma com ``passou`` e ``valor``.

    Args:
        checagens: o campo ``checagens`` do evento.
        onde: texto para localizar o erro.

    Returns:
        Lista de erros do bloco; vazia se as quatro estão bem formadas.
    """
    if not isinstance(checagens, dict):
        return [f"{onde}: checagens não é objeto"]
    erros: list[str] = []
    if set(checagens) != set(CHECAGENS):
        erros.append(f"{onde}: checagens devem ser exatamente {', '.join(CHECAGENS)}")
    for chave in CHECAGENS:
        bloco = checagens.get(chave)
        if not isinstance(bloco, dict) or set(bloco) != {"passou", "valor"}:
            erros.append(f"{onde}: {chave} deve ser {{passou, valor}}")
            continue
        if bloco["passou"] is not None and not isinstance(bloco["passou"], bool):
            erros.append(f"{onde}: {chave}.passou deve ser booleano ou null")
        if bloco["valor"] is not None and not _real(bloco["valor"]):
            erros.append(f"{onde}: {chave}.valor deve ser número finito ou null")
    return erros


def _json_regras(ev: dict, onde: str) -> list[str]:
    """Regras que ligam o tempo e a janela às checagens.

    Args:
        ev: o evento, com ``checagens`` bem formadas.
        onde: texto para localizar o erro.

    Returns:
        Lista de erros; vazia se as ligações batem.
    """
    erros: list[str] = []
    checagens = ev["checagens"]
    if ev.get("t_som") is None and _passou(checagens, "K1") is True:
        erros.append(f"{onde}: t_som null, mas K1.passou é true")
    if ev.get("janela") is None:
        for chave in ("K2", "K3"):
            if _passou(checagens, chave) is True:
                erros.append(f"{onde}: janela null, mas {chave}.passou é true")
    return erros


def _json_nivel(ev: dict, onde: str, checagens_ok: bool) -> list[str]:
    """Nível declarado, comparado às checagens, e regras de ``motivo``.

    Args:
        ev: o evento.
        onde: texto para localizar o erro.
        checagens_ok: se ``False``, o nível não é comparado (as checagens estão ruins).

    Returns:
        Lista de erros do nível e do motivo.
    """
    nivel = ev.get("nivel")
    motivo = ev.get("motivo")
    if nivel not in NIVEIS:
        return [f"{onde}: nivel {nivel!r} desconhecido"]
    erros: list[str] = []
    if checagens_ok:
        esperado = nivel_esperado(ev["checagens"])
        if nivel != esperado:
            erros.append(f"{onde}: nivel {nivel!r}, mas as checagens dão {esperado!r}")
    if nivel == "recusado":
        if not _texto(motivo):
            erros.append(f"{onde}: recusado sem motivo")
    elif motivo is not None:
        erros.append(f"{onde}: {nivel} com motivo (deve ser null)")
    return erros


def _json_evento(i: int, ev: object) -> list[str]:
    """Checa um evento inteiro: campos, checagens, regras e nível.

    Args:
        i: posição do evento na lista.
        ev: a entrada de ``eventos``.

    Returns:
        Lista de erros do evento.
    """
    onde = f"evento {i}"
    if not isinstance(ev, dict):
        return [f"{onde}: não é objeto"]
    erros = _json_chave(ev, onde)
    erros_checagens = _json_checagens(ev.get("checagens"), onde)
    erros += erros_checagens
    if not erros_checagens:
        erros += _json_regras(ev, onde)
    erros += _json_nivel(ev, onde, checagens_ok=not erros_checagens)
    return erros


def _json_eventos(eventos: list) -> list[str]:
    """Checa a lista de eventos, inclusive a unicidade da chave.

    Args:
        eventos: o campo ``eventos``.

    Returns:
        Lista de erros da lista.
    """
    erros: list[str] = []
    vistas: set[tuple[str, ...]] = set()
    for i, ev in enumerate(eventos):
        erros += _json_evento(i, ev)
        if not isinstance(ev, dict):
            continue
        chave = tuple(repr(ev.get(campo)) for campo in CHAVE_EVENTO)
        if chave in vistas:
            erros.append(f"evento {i}: chave repetida {CHAVE_EVENTO}")
        vistas.add(chave)
    return erros


def _json_resumo(resumo: object, eventos: list) -> list[str]:
    """Confere o ``resumo`` contra os eventos, inclusive ``motivos``.

    Args:
        resumo: o campo ``resumo``.
        eventos: a lista ``eventos`` já validada em tipo.

    Returns:
        Lista de erros; vazia se as contagens batem.
    """
    if not isinstance(resumo, dict):
        return ["resumo não é objeto"]
    niveis = Counter(
        ev.get("nivel")
        for ev in eventos
        if isinstance(ev, dict) and ev.get("nivel") in NIVEIS
    )
    esperado = {
        "eventos": len(eventos),
        "ouro": niveis["ouro"],
        "prata": niveis["prata"],
        "recusado": niveis["recusado"],
    }
    erros = [
        f"resumo.{campo} = {resumo.get(campo)!r}, mas os eventos dão {valor}"
        for campo, valor in esperado.items()
        if not (_inteiro(resumo.get(campo)) and resumo.get(campo) == valor)
    ]
    motivos = Counter(
        ev["motivo"]
        for ev in eventos
        if isinstance(ev, dict)
        and ev.get("nivel") == "recusado"
        and _texto(ev.get("motivo"))
    )
    dado = resumo.get("motivos")
    if not (
        isinstance(dado, dict)
        and all(_inteiro(v) for v in dado.values())
        and dado == dict(motivos)
    ):
        erros.append(f"resumo.motivos = {dado!r}, mas os eventos dão {dict(motivos)!r}")
    return erros


def validar_json(doc: object) -> list[str]:
    """Confere um ``<nome>.maos.json`` (``chorinho/maos@1``) e devolve os erros.

    Não lança exceção para entrada malformada: qualquer forma errada vira uma mensagem.
    As regras de ``denso`` (npz) não entram aqui; ver ``validar_denso``.

    Args:
        doc: o JSON, já carregado como dicionário.

    Returns:
        Lista de textos, um por erro. Lista vazia significa que o JSON é válido.
    """
    if not isinstance(doc, dict):
        return ["raiz não é um objeto"]
    erros = _json_raiz(doc)
    erros += _json_fontes(doc)
    erros += _json_video(doc.get("video"))
    erros += _json_gerado(doc.get("gerado_por"))
    erros += _json_violao(doc.get("violao"))
    eventos = doc.get("eventos")
    if not isinstance(eventos, list):
        erros.append("eventos não é lista")
        return erros
    erros += _json_eventos(eventos)
    erros += _json_resumo(doc.get("resumo"), eventos)
    return erros


def _forma_erro(
    nome: str, matriz: object, forma: tuple[int, ...], dtype: type
) -> str | None:
    """Confere tipo, dtype e forma exatos de uma matriz do ``.npz``.

    Args:
        nome: nome da matriz, para a mensagem.
        matriz: o objeto lido do ``.npz``.
        forma: forma esperada, já com o N.
        dtype: dtype numpy esperado.

    Returns:
        Texto do erro, ou ``None`` se a matriz está certa.
    """
    if not isinstance(matriz, np.ndarray):
        return f"{nome}: não é matriz numpy"
    if matriz.dtype != np.dtype(dtype):
        return f"{nome}: dtype {matriz.dtype}, esperado {np.dtype(dtype)}"
    if matriz.shape != forma:
        return f"{nome}: forma {matriz.shape}, esperado {forma}"
    return None


def _quadros(mascara: np.ndarray, nome: str, descricao: str) -> list[str]:
    """Relata, em uma mensagem só, os quadros onde a máscara acusa algo.

    Args:
        mascara: booleana com N no primeiro eixo.
        nome: matriz de origem, para a mensagem.
        descricao: o que a máscara acusa, em texto.

    Returns:
        Lista vazia, ou uma mensagem com a contagem de quadros e o primeiro deles.
    """
    por_quadro = mascara.reshape(mascara.shape[0], -1).any(axis=1)
    total = int(por_quadro.sum())
    if total == 0:
        return []
    primeiro = int(np.argmax(por_quadro))
    plural = "quadros" if total != 1 else "quadro"
    return [f"{nome}: {total} {plural} {descricao} (primeiro: {primeiro})"]


def _fora(xy: np.ndarray, largura: int, altura: int) -> np.ndarray:
    """Pontos finitos fora do quadro, com a folga ``FOLGA``.

    Args:
        xy: pontos com x e y no último eixo.
        largura: largura do quadro em px.
        altura: altura do quadro em px.

    Returns:
        Máscara booleana com a forma de ``xy`` sem o último eixo. NaN não conta.
    """
    x, y = xy[..., 0], xy[..., 1]
    fora_x = (x < -FOLGA * largura) | (x > (1 + FOLGA) * largura)
    fora_y = (y < -FOLGA * altura) | (y > (1 + FOLGA) * altura)
    return np.isfinite(x) & np.isfinite(y) & (fora_x | fora_y)


def _pontos(arr: np.ndarray, nome: str, largura: int, altura: int) -> list[str]:
    """Pontos (x, y[, score]) no último eixo: infinito, NaN pela metade, fora.

    Args:
        arr: matriz de pontos, com x e y nas duas primeiras posições do último eixo.
        nome: nome da matriz, para a mensagem.
        largura: largura do quadro em px.
        altura: altura do quadro em px.

    Returns:
        Lista de erros da matriz.
    """
    erros = _quadros(np.isinf(arr).any(axis=-1), nome, "com valor infinito")
    nan = np.isnan(arr)
    parcial = nan.any(axis=-1) & ~nan.all(axis=-1)
    erros += _quadros(parcial, nome, "com ponto NaN pela metade")
    fora = _fora(arr[..., :2], largura, altura)
    erros += _quadros(fora, nome, f"com ponto fora do quadro (folga {FOLGA:.0%})")
    return erros


def _escore(arr: np.ndarray, nome: str) -> list[str]:
    """Score (último eixo, posição 2) finito fora de [0, 1].

    Args:
        arr: matriz com x, y e score no último eixo.
        nome: nome da matriz, para a mensagem.

    Returns:
        Lista de erros de score.
    """
    escore = arr[..., 2]
    fora = np.isfinite(escore) & ((escore < 0) | (escore > 1))
    return _quadros(fora, nome, "com score fora de [0, 1]")


def _maos_presenca(
    maos: np.ndarray, origem: np.ndarray, trilha: np.ndarray
) -> list[str]:
    """Origem, trilha e pontos de cada mão batem: ausente é 0, −1 e NaN.

    Args:
        maos: as mãos, (N, 2, 21, 3).
        origem: origem de cada mão, (N, 2).
        trilha: id da trilha de cada mão, (N, 2).

    Returns:
        Lista de erros de presença.
    """
    erros = _quadros(
        ~np.isin(origem, (0, 1, 2)),
        "maos_origem",
        "com valor fora de 0, 1 e 2",
    )
    ausente = origem == 0
    sem_id = trilha == -1
    erros += _quadros(
        ausente != sem_id,
        "maos_trilha",
        "com origem e trilha discordando (0 ⇔ −1)",
    )
    erros += _quadros(
        ~ausente & (trilha < -1),
        "maos_trilha",
        "com id de trilha negativo diferente de −1",
    )
    todo_nan = np.isnan(maos).all(axis=(2, 3))
    todo_finito = np.isfinite(maos).all(axis=(2, 3))
    erros += _quadros(ausente & ~todo_nan, "maos", "com origem 0 e pontos não NaN")
    erros += _quadros(
        ~ausente & ~todo_finito,
        "maos",
        "com origem presente e algum ponto NaN ou infinito",
    )
    return erros


def _braco_conf(conf: np.ndarray, achou: np.ndarray) -> list[str]:
    """Confiança do braço: finita em [0, 1] onde achou, NaN onde não achou.

    Args:
        conf: ``braco_conf``, (N,).
        achou: ``braco_achou``, (N,).

    Returns:
        Lista de erros da confiança.
    """
    valida = np.isfinite(conf) & (conf >= 0) & (conf <= 1)
    erros = _quadros(
        achou & ~valida,
        "braco_conf",
        "com braço achado e confiança fora de [0, 1] ou NaN",
    )
    erros += _quadros(
        ~achou & ~np.isnan(conf),
        "braco_conf",
        "sem braço achado e confiança não NaN",
    )
    return erros


def _caixa(caixa: np.ndarray, largura: int, altura: int) -> list[str]:
    """Caixa da tablatura: NaN inteira ou finita, em ordem e dentro do quadro.

    Args:
        caixa: ``tab_caixa``, (N, 4) com x0, y0, x1, y1.
        largura: largura do quadro em px.
        altura: altura do quadro em px.

    Returns:
        Lista de erros da caixa.
    """
    nan = np.isnan(caixa)
    parcial = nan.any(axis=1) & ~nan.all(axis=1)
    erros = _quadros(parcial, "tab_caixa", "com coordenadas NaN pela metade")
    erros += _quadros(np.isinf(caixa).any(axis=1), "tab_caixa", "com valor infinito")
    cantos = caixa.reshape(caixa.shape[0], 2, 2)
    erros += _quadros(
        _fora(cantos, largura, altura),
        "tab_caixa",
        f"com canto fora do quadro (folga {FOLGA:.0%})",
    )
    finita = np.all(np.isfinite(caixa), axis=1)
    x0, y0, x1, y1 = caixa[:, 0], caixa[:, 1], caixa[:, 2], caixa[:, 3]
    erros += _quadros(
        finita & ((x0 >= x1) | (y0 >= y1)),
        "tab_caixa",
        "com x0 ≥ x1 ou y0 ≥ y1",
    )
    return erros


def _denso_pts(pts: np.ndarray) -> list[str]:
    """``pts``: finitos e estritamente crescentes.

    Args:
        pts: os PTS de cada quadro, em segundos.

    Returns:
        Lista de erros de ``pts``.
    """
    if not np.all(np.isfinite(pts)):
        return ["pts: há valores não finitos"]
    if pts.size > 1 and not np.all(np.diff(pts) > 0):
        return ["pts: não é estritamente crescente"]
    return []


def _denso_conteudo(
    arr: dict[str, np.ndarray], validas: set[str], largura: int, altura: int
) -> list[str]:
    """Regras de conteúdo das matrizes cujo formato e dtype já estão certos.

    Args:
        arr: as matrizes do ``.npz``.
        validas: nomes das matrizes com forma e dtype certos.
        largura: largura do quadro em px.
        altura: altura do quadro em px.

    Returns:
        Lista de erros de conteúdo.
    """
    erros: list[str] = []
    if "pts" in validas:
        erros += _denso_pts(arr["pts"])
    if "maos" in validas:
        maos = arr["maos"]
        erros += _pontos(maos, "maos", largura, altura)
        erros += _escore(maos, "maos")
        if {"maos_origem", "maos_trilha"} <= validas:
            erros += _maos_presenca(maos, arr["maos_origem"], arr["maos_trilha"])
    if "corpo" in validas:
        erros += _pontos(arr["corpo"], "corpo", largura, altura)
        erros += _escore(arr["corpo"], "corpo")
    for nome in ("braco_trastes", "braco_corda1", "braco_corda6"):
        if nome in validas:
            erros += _pontos(arr[nome], nome, largura, altura)
    if {"braco_conf", "braco_achou"} <= validas:
        erros += _braco_conf(arr["braco_conf"], arr["braco_achou"])
    if "tab_caixa" in validas:
        erros += _caixa(arr["tab_caixa"], largura, altura)
    return erros


def validar_denso(arr: dict[str, np.ndarray], largura: int, altura: int) -> list[str]:
    """Confere um ``<nome>.maos.npz`` (o denso) e devolve os erros.

    Não lança exceção para entrada malformada. Relata poucos erros por regra: uma
    mensagem por regra, com a contagem de quadros e o primeiro deles.

    Args:
        arr: as matrizes lidas do ``.npz``, por nome.
        largura: largura do quadro do vídeo, em px.
        altura: altura do quadro do vídeo, em px.

    Returns:
        Lista de textos, um por regra violada. Lista vazia significa que é válido.
    """
    if not isinstance(arr, dict):
        return ["denso: não é um dicionário de matrizes"]
    if not (_inteiro_entre(largura, 1) and _inteiro_entre(altura, 1)):
        return ["denso: largura e altura do vídeo devem ser inteiros positivos"]
    erros: list[str] = []
    faltam = [nome for nome in MATRIZES if nome not in arr]
    if faltam:
        erros.append(f"denso: faltam as matrizes {', '.join(faltam)}")
    extras = sorted(nome for nome in arr if nome not in MATRIZES)
    if extras:
        erros.append(f"denso: matrizes desconhecidas {', '.join(extras)}")
    pts = arr.get("pts")
    if not (isinstance(pts, np.ndarray) and pts.ndim == 1):
        return [*erros, "pts: deve ser vetor (N,); N desconhecido"]
    n = pts.shape[0]
    if n == 0:
        return [*erros, "denso: sem quadros (N = 0)"]
    validas: set[str] = set()
    for nome, (forma, dtype) in MATRIZES.items():
        if nome not in arr:
            continue
        erro = _forma_erro(nome, arr[nome], (n, *forma), dtype)
        if erro is None:
            validas.add(nome)
        else:
            erros.append(erro)
    erros += _denso_conteudo(arr, validas, largura, altura)
    return erros


def _janelas_no_denso(doc: dict, n: int) -> list[str]:
    """Janelas dos eventos com ``i1`` passando do N do denso.

    Args:
        doc: o JSON já carregado.
        n: número de quadros amostrados (N).

    Returns:
        Lista de erros; vazia se nenhuma janela passa de N.
    """
    erros: list[str] = []
    eventos = doc.get("eventos")
    if not isinstance(eventos, list):
        return erros
    for i, ev in enumerate(eventos):
        janela = ev.get("janela") if isinstance(ev, dict) else None
        if (
            isinstance(janela, list)
            and len(janela) == 2
            and _inteiro(janela[1])
            and janela[1] > n
        ):
            erros.append(f"evento {i}: janela {janela} passa de N = {n} quadros")
    return erros


def validar_par(doc: dict, arr: dict[str, np.ndarray]) -> list[str]:
    """Confere o par: ``validar_json`` mais ``validar_denso`` e as janelas contra N.

    Args:
        doc: o JSON já carregado.
        arr: as matrizes do ``.npz``, por nome.

    Returns:
        Lista de textos, um por erro. Lista vazia significa que o par é válido.
    """
    erros = validar_json(doc)
    if not isinstance(arr, dict):
        return [*erros, "denso: não é um dicionário de matrizes"]
    video = doc.get("video") if isinstance(doc, dict) else None
    tem_dimensoes = (
        isinstance(video, dict)
        and _inteiro(video.get("largura"))
        and _inteiro(video.get("altura"))
    )
    if not tem_dimensoes:
        erros.append("video: largura e altura ausentes; denso não conferido")
        return erros
    erros += validar_denso(arr, video["largura"], video["altura"])
    return erros + _janelas_se_houver_n(doc, arr)


def _janelas_se_houver_n(doc: dict, arr: dict[str, np.ndarray]) -> list[str]:
    """Aplica ``_janelas_no_denso`` se ``pts`` deu para ler o N.

    Args:
        doc: o JSON já carregado.
        arr: as matrizes do ``.npz``, por nome.

    Returns:
        Lista de erros das janelas; vazia se N não se conhece ou nada passa.
    """
    pts = arr.get("pts")
    if isinstance(pts, np.ndarray) and pts.ndim == 1:
        return _janelas_no_denso(doc, pts.shape[0])
    return []


def _constante_proibida(nome: str) -> object:
    """Rejeita ``NaN``, ``Infinity`` e ``-Infinity``, que não são JSON.

    Args:
        nome: a constante lida pelo parser.

    Raises:
        ValueError: sempre.
    """
    raise ValueError(f"constante {nome} não é JSON válido")


def carregar(caminho_json: Path) -> tuple[dict, dict[str, np.ndarray]]:
    """Lê o ``.maos.json`` e o ``.npz`` apontado por ``doc["denso"]``.

    O ``.npz`` é lido com ``allow_pickle=False`` e fica na mesma pasta do JSON.

    Args:
        caminho_json: caminho do ``<nome>.maos.json``.

    Returns:
        ``(doc, arr)``: o JSON já carregado e as matrizes do ``.npz``, por nome.

    Raises:
        OSError: se o JSON ou o ``.npz`` não pode ser lido.
        ValueError: se o JSON não é texto JSON válido ou ``denso`` não é texto.
    """
    texto = caminho_json.read_text(encoding="utf-8")
    doc = json.loads(texto, parse_constant=_constante_proibida)
    if not isinstance(doc, dict) or not isinstance(doc.get("denso"), str):
        raise ValueError("campo 'denso' ausente ou não é texto")
    with np.load(caminho_json.parent / doc["denso"], allow_pickle=False) as npz:
        arr = {nome: npz[nome] for nome in npz.files}
    return doc, arr


def _erros_sha(doc: dict, caminho_npz: Path) -> list[str]:
    """Confere ``denso_sha256`` contra o SHA-256 do ``.npz`` em disco.

    Args:
        doc: o JSON já carregado.
        caminho_npz: caminho do ``.npz`` apontado por ``doc["denso"]``.

    Returns:
        Lista de erros; vazia se o hash bate.
    """
    real = hashlib.sha256(caminho_npz.read_bytes()).hexdigest()
    if doc.get("denso_sha256") != real:
        return [
            f"denso_sha256 {doc.get('denso_sha256')!r} não bate com o arquivo ({real})"
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    """CLI: confere um par e imprime ``ok`` ou os erros, um por linha.

    Args:
        argv: argumentos da linha de comando; ``None`` lê ``sys.argv``.

    Returns:
        ``0`` se o par é válido, ``1`` caso contrário.
    """
    parser = argparse.ArgumentParser(
        prog="python -m tab.maos_esquema",
        description="Confere um par chorinho/maos@1 (.maos.json + .maos.npz).",
    )
    parser.add_argument("arquivo", type=Path, help="o <nome>.maos.json")
    args = parser.parse_args(argv)
    try:
        doc, arr = carregar(args.arquivo)
    except (OSError, ValueError) as exc:
        print(f"{args.arquivo}: {exc}")
        return 1
    erros = validar_par(doc, arr)
    erros += _erros_sha(doc, args.arquivo.parent / doc["denso"])
    if erros:
        for erro in erros:
            print(erro)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
