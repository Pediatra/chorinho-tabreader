"""Cache de quadros do censo (T-cache): chave, caminho, ida e volta e ``--so-cache``.

Sem acervo e sem GPU. O "vídeo" é um arquivo de lixo; o leitor é substituído por um fake
determinístico, e o teste de ``--so-cache`` quebra o leitor de propósito para provar que o
cache basta e que o vídeo não é aberto.
"""

from __future__ import annotations

import numpy as np
import pytest

from tab import cache, censo
from tab.caminhos import SAIDA, acervo, cache_quadros

LARGURA = 320
ALTURA = 240
RECT = (0, 0, LARGURA, 40)


def _quadro(t: float) -> np.ndarray:
    """Quadro determinístico em ``t``: ruído fixo, com o pixel (0,0) marcando tablatura."""
    rng = np.random.default_rng(round(t * 100))
    quadro = rng.integers(0, 256, (ALTURA, LARGURA, 3), dtype=np.uint8)
    quadro[0, 0, 0] = 255 if int(t) % 2 == 0 else 0
    return quadro


class _LeitorFalso:
    """Substitui ``tab.leitor.Leitor``: o mesmo quadro que ``_quadro`` daria no instante."""

    def __init__(self, caminho: str) -> None:
        self.caminho = caminho

    def ler(self, t: float) -> np.ndarray:
        return _quadro(t)

    def fechar(self) -> None:
        pass


def _quadros_falsos(caminho, t0, t1, qps, recorte_y=None):
    """Substitui ``tab.leitor.quadros``: 30 quadros de 10 s a 3 qps, como o real."""
    for k in range(30):
        t = t0 + k / qps
        yield t, _quadro(t)


def _painel_falso(quadro: np.ndarray):
    """Substitui ``telas.painel_do_quadro``: há tablatura quando o pixel (0,0) é 255."""
    return RECT if int(quadro[0, 0, 0]) == 255 else None


def _video_de_lixo(raiz, nome: str = "canal/video.mp4") -> str:
    """Arquivo que não é vídeo: só precisa existir para o ``os.stat`` do censo."""
    caminho = raiz / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"isto nao e video")
    return str(caminho)


def _sem_video(monkeypatch) -> None:
    """Quebra o acesso a vídeo: qualquer abertura vira falha de teste."""

    def proibido(*_a, **_k):
        raise AssertionError("o vídeo foi aberto no modo só-cache")

    monkeypatch.setattr(censo.leitor, "info", proibido)
    monkeypatch.setattr(censo.leitor, "Leitor", proibido)
    monkeypatch.setattr(censo.leitor, "quadros", proibido)
    monkeypatch.setattr(censo.leitor, "quadro_em", proibido)


def _instalar_falsos(monkeypatch) -> None:
    monkeypatch.setattr(
        censo.leitor,
        "info",
        lambda _c: {
            "codec": "h264",
            "largura": LARGURA,
            "altura": ALTURA,
            "fps": 30.0,
            "duracao_s": 120.0,
        },
    )
    monkeypatch.setattr(censo.leitor, "Leitor", _LeitorFalso)
    monkeypatch.setattr(censo.leitor, "quadros", _quadros_falsos)
    monkeypatch.setattr(censo.telas, "painel_do_quadro", _painel_falso)


def test_chave_do_cache_e_hash_estavel_e_separado_por_formato(tmp_path) -> None:
    chave = "canal/video.mp4|10|1700000000"
    padrao = cache.pasta_do_video(chave, cache.ModoCache(usar=True, raiz=tmp_path))
    assert padrao == cache.pasta_do_video(chave, cache.ModoCache(raiz=tmp_path))
    assert padrao.parent == tmp_path / "png"
    webp = cache.pasta_do_video(
        chave, cache.ModoCache(usar=True, formato="webp", raiz=tmp_path)
    )
    assert webp.parent == tmp_path / "webp"
    outra = cache.pasta_do_video("canal/outro.mp4|10|1", cache.ModoCache(raiz=tmp_path))
    assert outra != padrao


def test_caminho_do_cache_vem_do_ambiente_e_fica_fora_de_saida_e_acervo(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("CHORINHO_CACHE", str(tmp_path / "c"))
    assert cache_quadros() == tmp_path / "c"
    assert cache.ModoCache().raiz == tmp_path / "c"
    monkeypatch.delenv("CHORINHO_CACHE")
    padrao = cache_quadros().resolve()
    assert SAIDA.resolve() not in padrao.parents
    assert acervo().resolve() not in padrao.parents and padrao != acervo().resolve()


def test_formato_desconhecido_e_recusado() -> None:
    with pytest.raises(ValueError, match="formato de cache desconhecido"):
        cache.ModoCache(usar=True, formato="gif")


def test_pasta_da_janela_identifica_instante_e_caixa(tmp_path) -> None:
    pasta = tmp_path / "v"
    janela = cache.pasta_da_janela(pasta, 12.345, (0, 10, 1920, 1080))
    assert janela == pasta / "janela_1234_0-10-1920-1080"
    assert cache.pasta_da_janela(pasta, 12.345, (0, 10, 1920, 1081)) != janela


def test_ida_e_volta_sem_perda_e_identica_em_pixel(tmp_path) -> None:
    """WebP sem perda: o quadro lido é igual ao gravado, pixel a pixel (regra 9)."""
    quadro = _quadro(7.0)
    quadro[100:140, 50:300] = (40, 200, 90)  # bloco liso, como a tablatura
    for formato in ("png", "webp"):
        arquivo = cache.caminho_do_quadro(tmp_path, f"presenca_{formato}", formato)
        cache.gravar_quadro(arquivo, quadro, formato)
        lido = cache.ler_quadro(arquivo)
        assert lido.shape == quadro.shape
        assert np.array_equal(lido, quadro)


def test_quadro_corrompido_no_cache_falha_alto(tmp_path) -> None:
    arquivo = tmp_path / "ruim.webp"
    arquivo.write_bytes(b"nao e uma imagem")
    with pytest.raises(OSError, match="corrompido"):
        cache.ler_quadro(arquivo)


def test_meta_ida_e_volta_e_ausente(tmp_path) -> None:
    assert cache.ler_meta(tmp_path / "nao_existe") is None
    cache.gravar_meta(tmp_path, {"quadros": 30, "rect": [0, 1, 2, 3]})
    assert cache.ler_meta(tmp_path) == {"quadros": 30, "rect": [0, 1, 2, 3]}


def test_so_cache_sem_meta_aborta_sem_abrir_o_video(tmp_path, monkeypatch) -> None:
    _sem_video(monkeypatch)
    caminho = _video_de_lixo(tmp_path)
    modo = cache.ModoCache(so_cache=True, raiz=tmp_path / "cache")
    with pytest.raises(cache.FaltaNoCache, match="sem meta"):
        censo.censar_video(caminho, str(tmp_path), True, modo)


def test_cache_frio_e_so_cache_dao_o_mesmo_registro(tmp_path, monkeypatch) -> None:
    """A leitura fria (com vídeo) e a só-cache (sem vídeo) produzem a mesma linha."""
    raiz_cache = tmp_path / "cache"
    caminho = _video_de_lixo(tmp_path)
    _instalar_falsos(monkeypatch)
    frio = censo.censar_video(
        caminho, str(tmp_path), True, cache.ModoCache(usar=True, raiz=raiz_cache)
    )
    assert "erro" not in frio
    assert frio["janelas"] and all(j["quadros"] == 30 for j in frio["janelas"])
    assert any(i.get("tab") for i in frio["instantes"])

    _sem_video(monkeypatch)
    quente = censo.censar_video(
        caminho, str(tmp_path), True, cache.ModoCache(so_cache=True, raiz=raiz_cache)
    )
    assert quente == frio


def test_so_cache_aborta_quando_falta_um_quadro(tmp_path, monkeypatch) -> None:
    raiz_cache = tmp_path / "cache"
    caminho = _video_de_lixo(tmp_path)
    _instalar_falsos(monkeypatch)
    censo.censar_video(
        caminho, str(tmp_path), True, cache.ModoCache(usar=True, raiz=raiz_cache)
    )
    chave = censo.chave_do_arquivo(caminho, str(tmp_path))
    pasta = cache.pasta_do_video(chave, cache.ModoCache(raiz=raiz_cache))
    cache.caminho_do_quadro(pasta, "presenca_04", "png").unlink()

    _sem_video(monkeypatch)
    with pytest.raises(cache.FaltaNoCache, match="presença 4"):
        censo.censar_video(
            caminho,
            str(tmp_path),
            True,
            cache.ModoCache(so_cache=True, raiz=raiz_cache),
        )


def test_so_cache_aborta_quando_falta_uma_janela(tmp_path, monkeypatch) -> None:
    raiz_cache = tmp_path / "cache"
    caminho = _video_de_lixo(tmp_path)
    _instalar_falsos(monkeypatch)
    frio = censo.censar_video(
        caminho, str(tmp_path), True, cache.ModoCache(usar=True, raiz=raiz_cache)
    )
    chave = censo.chave_do_arquivo(caminho, str(tmp_path))
    pasta = cache.pasta_do_video(chave, cache.ModoCache(raiz=raiz_cache))
    t0 = frio["janelas"][0]["t0"]
    rect = tuple(int(v) for v in RECT)
    (cache.pasta_da_janela(pasta, t0, rect) / "meta.json").unlink()

    _sem_video(monkeypatch)
    with pytest.raises(cache.FaltaNoCache, match="janela"):
        censo.censar_video(
            caminho,
            str(tmp_path),
            True,
            cache.ModoCache(so_cache=True, raiz=raiz_cache),
        )
