"""Testes do utilitário que abre uma ferramenta no celular pelo Tailscale."""

from tab.celular import cabecalhos_locais, comando_descer, comando_subir, enderecos


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
