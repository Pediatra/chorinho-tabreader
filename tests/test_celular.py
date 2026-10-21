"""Testes do utilitário que abre uma ferramenta no celular pelo Tailscale."""

from tab.celular import (
    cabecalhos_locais,
    chave_do_pedido,
    comando_descer,
    comando_subir,
    enderecos,
    sem_chave,
    url_do_tunel,
)


def test_comando_subir_repassa_a_porta_local() -> None:
    """A porta do celular é a da ferramenta; o Tailscale fala com o intermediário."""
    assert comando_subir(8126) == [
        "tailscale",
        "serve",
        "--bg",
        "--http=8126",
        "http://127.0.0.1:18126",
    ]
    assert comando_descer(8126) == ["tailscale", "serve", "--http=8126", "off"]


def test_enderecos_pelo_nome_completo_e_curto() -> None:
    """Nome sem o ponto final; o IP não entra (o serve responde pelo nome)."""
    status = {
        "Self": {
            "DNSName": "pc.tail1234.ts.net.",
            "TailscaleIPs": ["100.64.0.7", "fd7a:115c:a1e0::7"],
        }
    }
    assert enderecos(status, 8126) == [
        "http://pc.tail1234.ts.net:8126/",
        "http://pc:8126/",
    ]
    assert enderecos({}, 8126) == []


def test_cabecalhos_locais_reescreve_host_origin_e_referer() -> None:
    """A ferramenta vê o pedido como vindo do próprio PC; o resto passa igual."""
    saida = cabecalhos_locais(
        [
            ("Host", "pc.tail1234.ts.net:8126"),
            ("Origin", "http://pc.tail1234.ts.net:8126"),
            ("Referer", "http://pc.tail1234.ts.net:8126/telas/001.png?x=1"),
            ("Content-Type", "application/json"),
            ("Connection", "keep-alive"),
        ],
        8126,
    )
    assert saida == {
        "Host": "127.0.0.1:8126",
        "Origin": "http://127.0.0.1:8126",
        "Referer": "http://127.0.0.1:8126/telas/001.png?x=1",
        "Content-Type": "application/json",
    }


def test_chave_vem_do_link_ou_do_cookie() -> None:
    """A chave do link vale (e é marcada como do link); senão, a do cookie."""
    assert chave_do_pedido("/?chave=abc", None) == ("abc", True)
    assert chave_do_pedido("/pre.json", "x=1; chave=abc") == ("abc", False)
    assert chave_do_pedido("/pre.json", None) == (None, False)
    referer = "https://x.trycloudflare.com/?chave=abc"
    assert chave_do_pedido("/pre.json", None, referer) == ("abc", False)


def test_sem_chave_tira_so_o_parametro_da_chave() -> None:
    """O resto da consulta fica; sem consulta, sai o caminho puro."""
    assert sem_chave("/?chave=abc") == "/"
    assert sem_chave("/telas/1.png?chave=abc&v=2") == "/telas/1.png?v=2"


def test_url_do_tunel_no_log_do_cloudflared() -> None:
    """O endereço sai da caixa que o cloudflared imprime."""
    linha = "2026-10-21T13:00:00Z INF |  https://abc-def-12.trycloudflare.com  |"
    assert url_do_tunel(linha) == "https://abc-def-12.trycloudflare.com"
    assert url_do_tunel("INF Requesting new quick Tunnel on trycloudflare.com") is None
