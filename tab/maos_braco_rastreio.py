"""Rastreio do braço entre quadros (M11a): homografia a partir de um quadro-chave.

A região do braço do quadro-chave (polígono das cordas 1 e 6, alargado de meio vão de
corda para cada lado, da pestana até uma casa depois do traste de maior número) gera
pontos de interesse (AKAZE ou ORB). Esses pontos são casados com os pontos do quadro
alvo inteiro, e a homografia por RANSAC leva as marcas do quadro-chave ao alvo. Nada da
tablatura e nada do gabarito do alvo entra no rastreio: o gabarito do alvo só serve para
medir.

A CLI ``python -m tab.maos_braco_rastreio dev`` roda o rastreio nos pares de
desenvolvimento e grava ``rastreio_dev_<detector>.json`` em ``MAOS_M11``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

import cv2
import numpy as np

from .caminhos import GABARITO_BRACO, MAOS_M3B_QUADROS, MAOS_M11
from .maos_braco_geometria import eixo_do_braco
from .maos_braco_tempo import (
    PARES_DESENVOLVIMENTO,
    Marcas,
    classificar,
    erros,
    linha_de_base,
    marcas_do_registro,
    transformar,
)

#: Vão de corda: distância entre as cordas 1 e 6 dividida por este número.
INTERVALOS_CORDAS = 5
#: Limites da determinante do bloco 2x2 da homografia (fora disso, é degenerada).
DETERMINANTE_MINIMA = 0.5
DETERMINANTE_MAXIMA = 2.0
#: Semente fixa do RANSAC (o cv2 usa o gerador global).
SEMENTE_RANSAC = 0
#: Mínimo de casamentos para estimar uma homografia (4 pares de pontos).
CASAMENTOS_MINIMOS = 4


@dataclasses.dataclass(frozen=True)
class Parametros:
    """Parâmetros do rastreio. Os padrões foram escolhidos no desenvolvimento (M11a).

    Attributes:
        detector: ``"akaze"`` ou ``"orb"``.
        razao_lowe: limiar do teste de razão de Lowe (casamento aceito se a melhor
            distância for menor que esta razão vezes a segunda).
        min_inliers: inliers mínimos para dizer "achei".
        max_reproj_px: erro de reprojeção mediano máximo dos inliers, em px.
        n_orb: número máximo de pontos do ORB.
        ransac_px: limiar de inlier do RANSAC, em px.
    """

    detector: str = "orb"
    razao_lowe: float = 0.8
    min_inliers: int = 15
    max_reproj_px: float = 3.0
    n_orb: int = 5000
    ransac_px: float = 3.0


PARAMETROS_PADRAO = Parametros()


def _cinza(img: np.ndarray) -> np.ndarray:
    """Converte para tons de cinza, se a imagem tiver canais.

    Args:
        img: imagem ``(h, w)`` ou ``(h, w, 3)``.

    Returns:
        Imagem ``(h, w)`` uint8.
    """
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def _distancia_a_reta(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Distância perpendicular de um ponto à reta que passa por ``a`` e ``b``.

    Args:
        p: ponto ``(2,)``.
        a: primeiro ponto da reta.
        b: segundo ponto da reta.

    Returns:
        Distância em px (sem sinal).
    """
    d = b - a
    cruz = d[0] * (p[1] - a[1]) - d[1] * (p[0] - a[0])
    return float(abs(cruz) / np.linalg.norm(d))


def _vao_px(marcas: Marcas) -> float:
    """Vão de corda do quadro: distância média entre as cordas 1 e 6, dividida por 5.

    Args:
        marcas: marcas do quadro (com cordas 1 e 6).

    Returns:
        Vão em px.

    Raises:
        ValueError: se as cordas 1 e 6 coincidem.
    """
    cruzadas = [
        _distancia_a_reta(p, marcas.corda1[0], marcas.corda1[1]) for p in marcas.corda6
    ]
    cruzadas += [
        _distancia_a_reta(p, marcas.corda6[0], marcas.corda6[1]) for p in marcas.corda1
    ]
    vao = float(np.mean(cruzadas)) / INTERVALOS_CORDAS
    if vao == 0.0:
        raise ValueError("cordas 1 e 6 coincidem: vão nulo")
    return vao


def _coordenadas(
    p: np.ndarray, origem: np.ndarray, u: np.ndarray, n: np.ndarray
) -> tuple[float, float]:
    """Coordenadas (axial, lateral) de um ponto no referencial do braço.

    Args:
        p: ponto ``(2,)``.
        origem: origem do referencial.
        u: eixo axial (vetor unitário).
        n: eixo lateral (vetor unitário, perpendicular a ``u``).

    Returns:
        Tupla ``(s, y)`` em px.
    """
    d = p - origem
    return float(np.dot(d, u)), float(np.dot(d, n))


def _lateral_da_corda(
    corda: np.ndarray, s: float, origem: np.ndarray, u: np.ndarray, n: np.ndarray
) -> float:
    """Posição lateral da corda no ponto axial ``s``, pela reta que a contém.

    Args:
        corda: dois pontos ``(2, 2)`` da corda.
        s: posição axial.
        origem: origem do referencial.
        u: eixo axial.
        n: eixo lateral.

    Returns:
        Posição lateral em px.

    Raises:
        ValueError: se a corda é perpendicular ao eixo (sem inclinação definida).
    """
    sa, ya = _coordenadas(corda[0], origem, u, n)
    sb, yb = _coordenadas(corda[1], origem, u, n)
    if abs(sb - sa) < 1e-9:
        raise ValueError("corda perpendicular ao eixo do braço")
    return ya + (yb - ya) * (s - sa) / (sb - sa)


def mascara_do_braco(marcas: Marcas, forma: tuple[int, ...]) -> np.ndarray:
    """Máscara do braço: o polígono das cordas 1 e 6, alargado, sobre o quadro.

    O polígono vai da pestana (ou do traste de menor número, sem nut) até o traste de
    maior número, mais uma casa. Cada lado é alargado de meio vão de corda, para fora
    das cordas 1 e 6.

    Args:
        marcas: marcas do quadro-chave (nut opcional, trastes, cordas 1 e 6).
        forma: forma da imagem; só ``(altura, largura)`` são usados.

    Returns:
        Array ``(altura, largura)`` uint8, com 255 dentro do braço e 0 fora.

    Raises:
        ValueError: se não há traste numerado, ou a geometria é degenerada.
    """
    if not marcas.trastes:
        raise ValueError("sem traste numerado para delimitar o braço")
    origem, u = eixo_do_braco(marcas.corda1.tolist(), marcas.corda6.tolist())
    numeros = sorted(marcas.trastes)
    n_max = numeros[-1]
    if marcas.nut is not None:
        ponto_inicio = marcas.nut
        n_inicio = 0
    else:
        ponto_inicio = marcas.trastes[numeros[0]]
        n_inicio = numeros[0]
    ponto_fim = marcas.trastes[n_max]
    delta = ponto_fim - ponto_inicio
    if float(np.dot(delta, u)) < 0.0:
        u = -u
    n = np.array([-u[1], u[0]])
    casa = abs(float(np.dot(delta, u))) / (n_max - n_inicio)
    s0 = float(np.dot(ponto_inicio - origem, u))
    s1 = float(np.dot(ponto_fim - origem, u)) + casa
    vao = _vao_px(marcas)

    canto = []
    for s in (s0, s1):
        y1 = _lateral_da_corda(marcas.corda1, s, origem, u, n)
        y6 = _lateral_da_corda(marcas.corda6, s, origem, u, n)
        canto.append((s, min(y1, y6) - vao / 2.0, max(y1, y6) + vao / 2.0))
    poligono = [
        origem + canto[0][0] * u + canto[0][1] * n,
        origem + canto[1][0] * u + canto[1][1] * n,
        origem + canto[1][0] * u + canto[1][2] * n,
        origem + canto[0][0] * u + canto[0][2] * n,
    ]
    mascara = np.zeros(forma[:2], dtype=np.uint8)
    pontos = np.round(np.array(poligono)).astype(np.int32)
    cv2.fillPoly(mascara, [pontos], 255)
    return mascara


def _detector(params: Parametros):
    """Detector de pontos e norma de distância, conforme ``params.detector``.

    Args:
        params: parâmetros do rastreio.

    Returns:
        ``(detector, norma)`` do cv2.

    Raises:
        ValueError: se o detector é desconhecido.
        RuntimeError: se o AKAZE pedido não existe nesta build do OpenCV.
    """
    if params.detector == "akaze":
        if not hasattr(cv2, "AKAZE_create"):
            raise RuntimeError("AKAZE indisponível nesta build do OpenCV (use orb)")
        return cv2.AKAZE_create(), cv2.NORM_HAMMING
    if params.detector == "orb":
        return cv2.ORB_create(nfeatures=params.n_orb), cv2.NORM_HAMMING
    raise ValueError(f"detector desconhecido: {params.detector!r}")


@dataclasses.dataclass(frozen=True, eq=False)
class _Casamento:
    """Resultado detalhado do rastreio (para medir e para desenhar).

    Attributes:
        h: homografia 3x3 do quadro-chave ao alvo, ou ``None``.
        info: diagnóstico (``n_pontos``, ``n_casamentos``, ``n_inliers``,
            ``reproj_mediana``, ``motivo``).
        kp_chave: pontos do quadro-chave.
        kp_alvo: pontos do quadro alvo.
        inliers: casamentos aceitos pelo RANSAC.
    """

    h: np.ndarray | None
    info: dict
    kp_chave: list
    kp_alvo: list
    inliers: list


def _rastrear_detalhe(
    img_chave: np.ndarray,
    marcas_chave: Marcas,
    img_alvo: np.ndarray,
    params: Parametros,
) -> _Casamento:
    """Rastreio completo, com os pontos e os casamentos (ver ``rastrear``).

    Args:
        img_chave: quadro-chave (cores ou cinza).
        marcas_chave: marcas do quadro-chave.
        img_alvo: quadro alvo (cores ou cinza).
        params: parâmetros do rastreio.

    Returns:
        ``_Casamento`` com a homografia (ou ``None``) e o diagnóstico.
    """
    cinza_chave = _cinza(img_chave)
    cinza_alvo = _cinza(img_alvo)
    mascara = mascara_do_braco(marcas_chave, cinza_chave.shape)
    detector, norma = _detector(params)
    kp_chave, des_chave = detector.detectAndCompute(cinza_chave, mascara)
    kp_alvo, des_alvo = detector.detectAndCompute(cinza_alvo, None)
    info: dict = {
        "n_pontos": {"chave": len(kp_chave), "alvo": len(kp_alvo)},
        "n_casamentos": 0,
        "n_inliers": 0,
        "reproj_mediana": None,
        "motivo": None,
    }

    def _nao_achou(motivo: str, inliers: list | None = None) -> _Casamento:
        info["motivo"] = motivo
        return _Casamento(None, info, kp_chave, kp_alvo, inliers or [])

    if des_chave is None or des_alvo is None:
        return _nao_achou("sem_pontos")
    pares = cv2.BFMatcher(norma).knnMatch(des_chave, des_alvo, k=2)
    bons = [
        p[0]
        for p in pares
        if len(p) == 2 and p[0].distance < params.razao_lowe * p[1].distance
    ]
    info["n_casamentos"] = len(bons)
    if len(bons) < CASAMENTOS_MINIMOS:
        return _nao_achou("poucos_casamentos")

    origem = np.float32([kp_chave[m.queryIdx].pt for m in bons]).reshape(-1, 1, 2)
    destino = np.float32([kp_alvo[m.trainIdx].pt for m in bons]).reshape(-1, 1, 2)
    cv2.setRNGSeed(SEMENTE_RANSAC)
    h, mascara_ransac = cv2.findHomography(
        origem, destino, cv2.RANSAC, params.ransac_px
    )
    if h is None or not np.all(np.isfinite(h)):
        return _nao_achou("sem_homografia")

    ativos = mascara_ransac.ravel().astype(bool)
    inliers = [m for m, ok in zip(bons, ativos, strict=True) if ok]
    info["n_inliers"] = len(inliers)
    if len(inliers) < params.min_inliers:
        return _nao_achou("poucos_inliers", inliers)

    previsto = cv2.perspectiveTransform(origem[ativos], h)
    erro = np.linalg.norm(previsto - destino[ativos], axis=2).ravel()
    reproj = float(np.median(erro))
    info["reproj_mediana"] = reproj
    if reproj > params.max_reproj_px:
        return _nao_achou("reproj_alta", inliers)

    determinante = float(np.linalg.det(h[:2, :2]))
    if not DETERMINANTE_MINIMA <= determinante <= DETERMINANTE_MAXIMA:
        return _nao_achou("homografia_degenerada", inliers)

    info["motivo"] = "achou"
    return _Casamento(h, info, kp_chave, kp_alvo, inliers)


def rastrear(
    img_chave: np.ndarray,
    marcas_chave: Marcas,
    img_alvo: np.ndarray,
    params: Parametros = PARAMETROS_PADRAO,
) -> tuple[np.ndarray | None, dict]:
    """Acha o braço do quadro-chave no quadro alvo, por homografia.

    Args:
        img_chave: quadro-chave.
        marcas_chave: marcas do quadro-chave (usadas só para a máscara do braço).
        img_alvo: quadro alvo inteiro.
        params: parâmetros do rastreio.

    Returns:
        ``(h, info)``: ``h`` é a homografia 3x3 do quadro-chave ao alvo, ou ``None``
        quando não achou. ``info`` traz ``n_pontos`` (``chave`` e ``alvo``),
        ``n_casamentos``, ``n_inliers``, ``reproj_mediana`` e ``motivo``.
    """
    resultado = _rastrear_detalhe(img_chave, marcas_chave, img_alvo, params)
    return resultado.h, resultado.info


def _ler(identificador: str) -> np.ndarray:
    """Lê o quadro da amostra da ferramenta do braço, em cores.

    Args:
        identificador: id do quadro (``q02``...).

    Returns:
        Imagem BGR.

    Raises:
        FileNotFoundError: se o quadro não existe na amostra.
    """
    caminho = MAOS_M3B_QUADROS / f"{identificador}.png"
    img = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(caminho)
    return img


def _classe_do_par(
    h: np.ndarray | None, marcas_chave: Marcas, marcas_alvo: Marcas | None, braco: str
) -> tuple[dict | None, str]:
    """Mede a previsão de um par e devolve o erro e a classe.

    Args:
        h: homografia (``None`` = não achou).
        marcas_chave: marcas do quadro-chave.
        marcas_alvo: marcas do dono no alvo, ou ``None`` (braço ``nao``/``?``).
        braco: valor de ``braco`` no gabarito do alvo.

    Returns:
        ``(erros, classe)``. ``erros`` é ``None`` sem medida.
    """
    if h is None:
        return None, classificar({}, False, braco)
    previsto = transformar(marcas_chave, h)
    if marcas_alvo is None:
        return None, "falso" if braco == "nao" else "sem_medida"
    e = erros(previsto, marcas_alvo)
    return e, classificar(e, True, braco)


def _formatar(valor: float | None) -> str:
    """Número com 2 casas, ou traço se ausente.

    Args:
        valor: número ou None.

    Returns:
        Texto para a tabela.
    """
    return "—" if valor is None else f"{valor:.2f}"


def _inteiro(ponto: np.ndarray) -> tuple[int, int]:
    """Arredonda um ponto para pixels inteiros (para desenhar).

    Args:
        ponto: ponto ``(2,)`` em px.

    Returns:
        Tupla ``(x, y)`` de inteiros.
    """
    x, y = np.round(ponto)
    return int(x), int(y)


def _desenhar_marcas(
    img: np.ndarray, marcas: Marcas, cor: tuple[int, int, int]
) -> None:
    """Desenha as cordas 1 e 6, o nut e os trastes de um quadro (in place).

    Args:
        img: imagem BGR onde desenhar.
        marcas: marcas a desenhar.
        cor: cor BGR.
    """
    for corda in (marcas.corda1, marcas.corda6):
        a, b = corda[0], corda[1]
        d = b - a
        cv2.line(img, _inteiro(a - 5.0 * d), _inteiro(b + 5.0 * d), cor, 2)
    if marcas.nut is not None:
        cv2.circle(img, _inteiro(marcas.nut), 8, cor, -1)
    for p in marcas.trastes.values():
        cv2.circle(img, _inteiro(p), 6, cor, 2)


def _gravar_desenhos(
    detector: str,
    chave: str,
    alvo: str,
    img_chave: np.ndarray,
    img_alvo: np.ndarray,
    marcas_chave: Marcas,
    marcas_alvo: Marcas | None,
    resultado: _Casamento,
) -> None:
    """Grava as marcas (previstas em verde, do dono em vermelho) e os casamentos.

    Args:
        detector: nome do detector (vai no nome do arquivo).
        chave: id do quadro-chave.
        alvo: id do quadro alvo.
        img_chave: quadro-chave.
        img_alvo: quadro alvo.
        marcas_chave: marcas do quadro-chave.
        marcas_alvo: marcas do dono no alvo, ou ``None``.
        resultado: resultado detalhado do rastreio.
    """
    pasta = MAOS_M11 / "desenhos"
    pasta.mkdir(parents=True, exist_ok=True)
    marcado = img_alvo.copy()
    if marcas_alvo is not None:
        _desenhar_marcas(marcado, marcas_alvo, (0, 0, 255))
    if resultado.h is not None:
        previsto = transformar(marcas_chave, resultado.h)
        _desenhar_marcas(marcado, previsto, (0, 255, 0))
    cv2.imwrite(str(pasta / f"{detector}_{chave}_{alvo}_marcas.png"), marcado)
    casados = cv2.drawMatches(
        img_chave,
        resultado.kp_chave,
        img_alvo,
        resultado.kp_alvo,
        resultado.inliers,
        None,
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
    )
    cv2.imwrite(str(pasta / f"{detector}_{chave}_{alvo}_casamentos.png"), casados)


def _rodar_dev(params: Parametros, desenhar: bool) -> int:
    """Roda o rastreio nos pares de desenvolvimento e imprime a tabela.

    Args:
        params: parâmetros do rastreio.
        desenhar: se grava os desenhos em ``MAOS_M11 / "desenhos"``.

    Returns:
        0 ao terminar.
    """
    gabarito = json.loads(GABARITO_BRACO.read_text(encoding="utf-8"))["quadros"]
    base = {
        (item["chave"], item["alvo"]): item
        for item in linha_de_base(PARES_DESENVOLVIMENTO, gabarito)
    }
    entradas = []
    print(
        f"{'par':<12}{'achou':>6}{'inl':>5}{'reproj':>8}{'nut':>7}{'pior':>7}"
        f"{'perp':>8}  {'classe':<10}{'base perp':>10}"
    )
    for chave, alvo in PARES_DESENVOLVIMENTO:
        marcas_chave = marcas_do_registro(gabarito[chave])
        marcas_alvo = marcas_do_registro(gabarito[alvo])
        if marcas_chave is None:
            raise ValueError(f"quadro-chave {chave} sem marcas")
        braco = gabarito[alvo].get("braco")
        img_chave = _ler(chave)
        img_alvo = _ler(alvo)
        resultado = _rastrear_detalhe(img_chave, marcas_chave, img_alvo, params)
        e, classe = _classe_do_par(resultado.h, marcas_chave, marcas_alvo, braco)
        if desenhar:
            _gravar_desenhos(
                params.detector,
                chave,
                alvo,
                img_chave,
                img_alvo,
                marcas_chave,
                marcas_alvo,
                resultado,
            )
        entradas.append(
            {
                "chave": chave,
                "alvo": alvo,
                "braco_alvo": braco,
                "info": resultado.info,
                "h": None if resultado.h is None else resultado.h.tolist(),
                "erros": e,
                "classe": classe,
            }
        )
        info = resultado.info
        achou = resultado.h is not None
        reproj = info["reproj_mediana"]
        perp_base = base[(chave, alvo)]["erros"]
        perp_base_txt = _formatar(
            None if perp_base is None else perp_base["perp_cordas"]
        )
        print(
            f"{chave + '->' + alvo:<12}{'sim' if achou else 'não':>6}"
            f"{info['n_inliers']:>5}"
            f"{_formatar(reproj):>8}"
            f"{_formatar(None if e is None else e['nut_casas']):>7}"
            f"{_formatar(None if e is None else e['pior_traste_casas']):>7}"
            f"{_formatar(None if e is None else e['perp_cordas']):>8}  "
            f"{classe:<10}{perp_base_txt:>10}"
        )

    MAOS_M11.mkdir(parents=True, exist_ok=True)
    saida = MAOS_M11 / f"rastreio_dev_{params.detector}.json"
    saida.write_text(
        json.dumps(
            {"parametros": dataclasses.asdict(params), "pares": entradas},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"gravado em {saida}", file=sys.stderr)
    return 0


def main() -> int:
    """Ponto de entrada da CLI.

    Returns:
        0 ao terminar.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("comando", choices=["dev"])
    parser.add_argument("--detector", choices=["akaze", "orb"], default="orb")
    parser.add_argument(
        "--desenhar",
        action="store_true",
        help="grava as imagens das marcas e dos casamentos",
    )
    args = parser.parse_args()
    params = dataclasses.replace(PARAMETROS_PADRAO, detector=args.detector)
    return _rodar_dev(params, args.desenhar)


if __name__ == "__main__":
    sys.exit(main())
