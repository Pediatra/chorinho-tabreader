"""Abre uma ferramenta de gabarito no celular, pela rede privada do Tailscale.

Serve para qualquer ferramenta que já esteja rodando numa porta local do PC
(``tab.ouro_video servir``, ``tab.maos_braco_gabarito servir``...). O
``tailscale serve`` repassa a porta só para os aparelhos da conta do dono: nada fica
público, e a ferramenta não muda. Roda **no host** (o Tailscale é do host), só com a
biblioteca padrão.

Uso (host, na raiz do repositório)::

    python3 -m tab.celular subir 8126      # mostra o endereço para abrir no celular
    python3 -m tab.celular listar          # o que está aberto no celular
    python3 -m tab.celular descer 8126     # fecha
"""

import argparse
import json
import subprocess
import sys


def comando_subir(porta: int) -> list[str]:
    """Comando do Tailscale que repassa a porta local para a rede privada.

    Args:
        porta: porta local da ferramenta (a mesma do lado do celular).

    Returns:
        A linha de comando, em HTTP (o túnel do Tailscale já é cifrado).
    """
    return [
        "tailscale",
        "serve",
        "--bg",
        f"--http={porta}",
        f"http://127.0.0.1:{porta}",
    ]


def comando_descer(porta: int) -> list[str]:
    """Comando do Tailscale que fecha a porta na rede privada.

    Args:
        porta: porta aberta por ``comando_subir``.

    Returns:
        A linha de comando.
    """
    return ["tailscale", "serve", f"--http={porta}", "off"]


def enderecos(status: dict, porta: int) -> list[str]:
    """Endereços da ferramenta para o celular, pelo status do Tailscale.

    Args:
        status: saída de ``tailscale status --json``.
        porta: porta da ferramenta.

    Returns:
        O endereço pelo nome do PC (se houver) e o pelo IP IPv4 do Tailscale.
    """
    eu = status.get("Self") or {}
    saida = []
    nome = (eu.get("DNSName") or "").rstrip(".")
    if nome:
        saida.append(f"http://{nome}:{porta}/")
    saida += [
        f"http://{ip}:{porta}/" for ip in eu.get("TailscaleIPs") or [] if "." in ip
    ]
    return saida


def _rodar(cmd: list[str]) -> subprocess.CompletedProcess:
    """Roda um comando e devolve o resultado, com a saída em texto."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _status() -> dict:
    """Status do Tailscale; sai com uma mensagem clara se ele não estiver ligado."""
    r = _rodar(["tailscale", "status", "--json"])
    status = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    if status.get("BackendState") != "Running":
        raise SystemExit(
            "O Tailscale não está ligado neste PC. Rode `sudo tailscale up` e entre "
            "com a sua conta (a mesma do celular)."
        )
    return status


def _porta_responde(porta: int) -> bool:
    """Diz se há uma ferramenta respondendo na porta local."""
    r = _rodar(
        [
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            f"http://127.0.0.1:{porta}/",
        ]
    )
    return r.stdout.strip().startswith(("2", "3"))


def main() -> int:
    """Sobe, lista ou fecha uma ferramenta no celular."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="acao", required=True)
    s = sub.add_parser("subir", help="abre a ferramenta da porta no celular")
    s.add_argument("porta", type=int)
    d = sub.add_parser("descer", help="fecha a porta no celular")
    d.add_argument("porta", type=int)
    sub.add_parser("listar", help="mostra o que está aberto no celular")
    args = ap.parse_args()
    status = _status()
    if args.acao == "listar":
        print(_rodar(["tailscale", "serve", "status"]).stdout.strip() or "nada aberto")
        return 0
    if args.acao == "descer":
        r = _rodar(comando_descer(args.porta))
        print(r.stdout + r.stderr if r.returncode else f"porta {args.porta} fechada")
        return r.returncode
    if not _porta_responde(args.porta):
        print(
            f"aviso: nada responde em http://127.0.0.1:{args.porta}/ — a ferramenta "
            "está rodando?",
            file=sys.stderr,
        )
    r = _rodar(comando_subir(args.porta))
    if r.returncode:
        print(r.stdout + r.stderr, file=sys.stderr)
        if "access denied" in (r.stdout + r.stderr).lower():
            print("Rode uma vez: sudo tailscale set --operator=$USER", file=sys.stderr)
        return r.returncode
    print("Abra no celular (com o app Tailscale ligado):")
    for e in enderecos(status, args.porta):
        print("  " + e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
