"""Testes do utilitário que abre uma ferramenta no celular pelo Tailscale."""

from tab.celular import comando_descer, comando_subir, enderecos


def test_comando_subir_repassa_a_porta_local() -> None:
    """A porta do celular é a mesma da ferramenta, só do 127.0.0.1."""
    assert comando_subir(8126) == [
        "tailscale",
        "serve",
        "--bg",
        "--http=8126",
        "http://127.0.0.1:8126",
    ]
    assert comando_descer(8126) == ["tailscale", "serve", "--http=8126", "off"]


def test_enderecos_pelo_nome_e_pelo_ip_v4() -> None:
    """Nome sem o ponto final e só o IP IPv4 (o IPv6 fica de fora)."""
    status = {
        "Self": {
            "DNSName": "pc.tail1234.ts.net.",
            "TailscaleIPs": ["100.64.0.7", "fd7a:115c:a1e0::7"],
        }
    }
    assert enderecos(status, 8126) == [
        "http://pc.tail1234.ts.net:8126/",
        "http://100.64.0.7:8126/",
    ]
    assert enderecos({}, 8126) == []
