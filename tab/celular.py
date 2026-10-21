"""Abre uma ferramenta de gabarito fora de casa: Tailscale (privado) ou Cloudflare.

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

``subir --cloudflare`` (pedido do dono, 2026-10-21): para um aparelho fora do Tailscale
(ex.: o PC da empresa). Abre um túnel rápido da Cloudflare (``cloudflared``, sem conta e
sem sudo, em ``~/.local/bin``) para o intermediário. O endereço é **público**, então o
intermediário exige uma chave aleatória: o link com ``?chave=`` grava um cookie, e pedido
sem a chave certa leva 403 (não chega à ferramenta, nem lê, nem grava). Cada ``subir``
gera endereço e chave novos; Ctrl-C fecha o túnel.

Uso (host, na raiz do repositório)::

    python3 -m tab.celular subir 8126      # mostra o endereço; deixe rodando
    python3 -m tab.celular subir 8126 --cloudflare   # link público com chave
    python3 -m tab.celular listar          # o que está aberto no celular
    python3 -m tab.celular descer 8126     # fecha (se o subir morreu sem fechar)
"""

import argparse
import hmac
import http.client
import http.cookies
import http.server
import json
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path

#: Porta do intermediário = porta da ferramenta + isto (Tailscale).
DESLOCAMENTO = 10000
#: Porta do intermediário do túnel da Cloudflare = porta da ferramenta + isto.
DESLOCAMENTO_CLOUDFLARE = 20000
#: Onde o ``cloudflared`` foi instalado (binário oficial, sem sudo).
CLOUDFLARED = Path.home() / ".local" / "bin" / "cloudflared"
#: Nome do parâmetro e do cookie da chave.
CHAVE = "chave"
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


def chave_do_pedido(
    caminho: str, cookie: str | None, referer: str | None = None
) -> tuple[str | None, bool]:
    """A chave que o pedido traz, e se ela veio no link.

    Args:
        caminho: caminho do pedido, com a consulta (``/x?chave=...``).
        cookie: cabeçalho ``Cookie`` do pedido.
        referer: cabeçalho ``Referer``; os pedidos da página aberta com ``?chave=``
            levam o link dela aqui (vale quando o navegador não guarda o cookie).

    Returns:
        (chave ou None, True se veio em ``?chave=`` no link).
    """
    consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(caminho).query)
    if consulta.get(CHAVE):
        return consulta[CHAVE][0], True
    da_pagina = urllib.parse.parse_qs(urllib.parse.urlsplit(referer or "").query)
    if da_pagina.get(CHAVE):
        return da_pagina[CHAVE][0], False
    biscoitos = http.cookies.SimpleCookie()
    try:
        biscoitos.load(cookie or "")
    except http.cookies.CookieError:
        return None, False
    return (biscoitos[CHAVE].value if CHAVE in biscoitos else None), False


def sem_chave(caminho: str) -> str:
    """O caminho sem o parâmetro da chave (para não ficar na barra do navegador).

    Args:
        caminho: caminho do pedido, com a consulta.

    Returns:
        O caminho com a consulta sem ``chave``.
    """
    partes = urllib.parse.urlsplit(caminho)
    resto = [(k, v) for k, v in urllib.parse.parse_qsl(partes.query) if k != CHAVE]
    consulta = urllib.parse.urlencode(resto)
    return (partes.path or "/") + (f"?{consulta}" if consulta else "")


def url_do_tunel(linha: str) -> str | None:
    """O endereço do túnel rápido numa linha do log do ``cloudflared``.

    Args:
        linha: uma linha do log.

    Returns:
        ``https://<nome>.trycloudflare.com`` ou None.
    """
    achado = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linha)
    return achado.group(0) if achado else None


def intermediario(
    porta: int, chave: str | None = None, deslocamento: int = DESLOCAMENTO
) -> http.server.ThreadingHTTPServer:
    """Servidor em 127.0.0.1 que repassa à ferramenta com os cabeçalhos locais.

    Args:
        porta: porta da ferramenta.
        chave: se dada, todo pedido precisa dela (no link ou no cookie); sem ela, 403.
        deslocamento: porta do intermediário = ``porta`` + isto.

    Returns:
        O servidor (não iniciado), na porta ``porta + deslocamento``.
    """

    class Repasse(http.server.BaseHTTPRequestHandler):
        """Repassa cada pedido à ferramenta e devolve a resposta dela."""

        def _chave_ok(self) -> bool:
            """Confere a chave; no link certo, grava o cookie e tira a chave da barra."""
            self._cookie = None
            if chave is None:
                return True
            dada, no_link = chave_do_pedido(
                self.path, self.headers.get("Cookie"), self.headers.get("Referer")
            )
            if dada is None or not hmac.compare_digest(dada, chave):
                corpo = b"chave ausente ou errada\n"
                self.send_response(403)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
                return False
            if no_link:  # a página fica com ?chave= no link: os pedidos dela a levam
                self.path = sem_chave(self.path)
                self._cookie = (
                    f"{CHAVE}={chave}; Path=/; HttpOnly; Secure; SameSite=Lax"
                )
            return True

        def _repassar(self) -> None:
            if not self._chave_ok():
                return
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
            self.send_header("Referrer-Policy", "same-origin")
            if self._cookie:
                self.send_header("Set-Cookie", self._cookie)
            self.end_headers()
            self.wfile.write(dados)

        do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _repassar

        def log_message(self, formato: str, *args: object) -> None:
            """Silencia o log por pedido."""

    return http.server.ThreadingHTTPServer(("127.0.0.1", porta + deslocamento), Repasse)


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


def _subir_cloudflare(porta: int) -> int:
    """Abre o túnel rápido da Cloudflare com chave e fica rodando até Ctrl-C.

    Args:
        porta: porta da ferramenta.

    Returns:
        Código de saída.
    """
    binario = shutil.which("cloudflared") or str(CLOUDFLARED)
    if not Path(binario).exists():
        raise SystemExit(f"cloudflared não encontrado (esperado em {CLOUDFLARED})")
    chave = secrets.token_urlsafe(18)
    servidor = intermediario(porta, chave, DESLOCAMENTO_CLOUDFLARE)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    tunel = subprocess.Popen(
        [
            binario,
            "tunnel",
            "--no-autoupdate",
            "--url",
            f"http://127.0.0.1:{porta + DESLOCAMENTO_CLOUDFLARE}",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
    )
    signal.signal(signal.SIGTERM, _parar)
    try:
        url = None
        for linha in tunel.stderr:
            url = url_do_tunel(linha)
            if url:
                break
        if url is None:
            print("o cloudflared saiu sem dar endereço", file=sys.stderr)
            return 1
        print("Abra no navegador (link com a chave; não compartilhe):", flush=True)
        print(f"  {url}/?{CHAVE}={chave}", flush=True)
        print("Deixe rodando; Ctrl-C fecha.", flush=True)
        for _ in tunel.stderr:  # drena o log até o túnel acabar
            pass
        return tunel.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        tunel.terminate()
        servidor.shutdown()
        print("túnel fechado", flush=True)


def _parar(*_: object) -> None:
    """Trata o SIGTERM como Ctrl-C, para o ``finally`` fechar a porta."""
    raise KeyboardInterrupt


def main() -> int:
    """Sobe, lista ou fecha uma ferramenta no celular."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="acao", required=True)
    s = sub.add_parser("subir", help="abre a ferramenta da porta no celular")
    s.add_argument("porta", type=int)
    s.add_argument(
        "--cloudflare",
        action="store_true",
        help="link público com chave (fora do Tailscale)",
    )
    d = sub.add_parser("descer", help="fecha a porta no celular")
    d.add_argument("porta", type=int)
    sub.add_parser("listar", help="mostra o que está aberto no celular")
    args = ap.parse_args()
    if args.acao == "subir" and args.cloudflare:
        if not _porta_responde(args.porta):
            print(f"aviso: nada responde em 127.0.0.1:{args.porta}", file=sys.stderr)
        return _subir_cloudflare(args.porta)
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
