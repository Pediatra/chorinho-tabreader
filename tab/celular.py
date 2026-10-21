"""Abre uma ferramenta de gabarito no celular, pela rede privada do Tailscale.

Serve para qualquer ferramenta que já esteja rodando numa porta local do PC
(``tab.ouro_video servir``, ``tab.maos_braco_gabarito servir``...). O
``tailscale serve`` repassa a porta só para os aparelhos da conta do dono: nada fica
público, e a ferramenta não muda. Roda **no host** (o Tailscale é do host), só com a
biblioteca padrão.

As ferramentas recusam ``Host``/``Origin`` que não sejam o próprio PC (proteção contra
rebinding e CSRF). Por isso o ``subir`` põe um intermediário em ``127.0.0.1`` (porta da
ferramenta + ``DESLOCAMENTO``) que reescreve esses cabeçalhos para ``127.0.0.1``; só o
``tailscale serve`` chega nele. O ``subir`` fica rodando: Ctrl-C (ou o fim do processo)
fecha a porta no celular.

Uso (host, na raiz do repositório)::

    python3 -m tab.celular subir 8126      # mostra o endereço; deixe rodando
    python3 -m tab.celular listar          # o que está aberto no celular
    python3 -m tab.celular descer 8126     # fecha (se o subir morreu sem fechar)
"""

import argparse
import http.client
import http.server
import json
import signal
import subprocess
import sys

#: Porta do intermediário = porta da ferramenta + isto.
DESLOCAMENTO = 10000
#: Cabeçalhos que não se repassam (de uma conexão só).
SALTO = {"connection", "keep-alive", "transfer-encoding", "upgrade", "proxy-connection"}


def comando_subir(porta: int) -> list[str]:
    """Comando do Tailscale que repassa o intermediário para a rede privada.

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
        f"http://127.0.0.1:{porta + DESLOCAMENTO}",
    ]


def cabecalhos_locais(cabecalhos: list[tuple[str, str]], porta: int) -> dict[str, str]:
    """Cabeçalhos do pedido do celular, como se viessem do próprio PC.

    Args:
        cabecalhos: pares (nome, valor) do pedido.
        porta: porta da ferramenta.

    Returns:
        Os cabeçalhos com ``Host``, ``Origin`` e ``Referer`` em ``127.0.0.1:porta``,
        sem os de salto.
    """
    local = f"127.0.0.1:{porta}"
    saida = {}
    for nome, valor in cabecalhos:
        chave = nome.lower()
        if chave in SALTO:
            continue
        if chave == "host":
            valor = local
        elif chave == "origin":
            valor = f"http://{local}"
        elif chave == "referer":
            resto = valor.split("://", 1)[-1].split("/", 1)
            valor = f"http://{local}/" + (resto[1] if len(resto) > 1 else "")
        saida[nome] = valor
    return saida


def intermediario(porta: int) -> http.server.ThreadingHTTPServer:
    """Servidor em 127.0.0.1 que repassa à ferramenta com os cabeçalhos locais.

    Args:
        porta: porta da ferramenta.

    Returns:
        O servidor (não iniciado), na porta ``porta + DESLOCAMENTO``.
    """

    class Repasse(http.server.BaseHTTPRequestHandler):
        """Repassa cada pedido à ferramenta e devolve a resposta dela."""

        def _repassar(self) -> None:
            tamanho = int(self.headers.get("Content-Length") or 0)
            corpo = self.rfile.read(tamanho) if tamanho else None
            conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=60)
            try:
                conexao.request(
                    self.command,
                    self.path,
                    body=corpo,
                    headers=cabecalhos_locais(list(self.headers.items()), porta),
                )
                resposta = conexao.getresponse()
                dados = resposta.read()
            except OSError as erro:
                self.send_error(502, f"ferramenta fora do ar: {erro}")
                return
            finally:
                conexao.close()
            self.send_response(resposta.status, resposta.reason)
            for nome, valor in resposta.getheaders():
                if nome.lower() not in SALTO | {"content-length"}:
                    self.send_header(nome, valor)
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _repassar

        def log_message(self, formato: str, *args: object) -> None:
            """Silencia o log por pedido."""

    return http.server.ThreadingHTTPServer(("127.0.0.1", porta + DESLOCAMENTO), Repasse)


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
        O endereço pelo nome completo do PC e pelo nome curto (o ``tailscale serve``
        responde pelo nome, não pelo IP).
    """
    nome = ((status.get("Self") or {}).get("DNSName") or "").rstrip(".")
    if not nome:
        return []
    return [f"http://{nome}:{porta}/", f"http://{nome.split('.')[0]}:{porta}/"]


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


def _parar(*_: object) -> None:
    """Trata o SIGTERM como Ctrl-C, para o ``finally`` fechar a porta."""
    raise KeyboardInterrupt


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
    servidor = intermediario(args.porta)
    r = _rodar(comando_subir(args.porta))
    if r.returncode:
        print(r.stdout + r.stderr, file=sys.stderr)
        if "access denied" in (r.stdout + r.stderr).lower():
            print("Rode uma vez: sudo tailscale set --operator=$USER", file=sys.stderr)
        return r.returncode
    signal.signal(signal.SIGTERM, _parar)
    print("Abra no celular (com o app Tailscale ligado):", flush=True)
    for e in enderecos(status, args.porta):
        print("  " + e, flush=True)
    print("Deixe rodando; Ctrl-C fecha.", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _rodar(comando_descer(args.porta))
        print(f"porta {args.porta} fechada no celular", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
