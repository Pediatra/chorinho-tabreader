"""Ferramenta dos padrões da mão direita (M5): funções puras, gabarito e servidor.

Fase M5 da trilha das mãos (``docs/decisoes/1004-m5-padroes-da-mao-direita.md``). O dono
olha, por compasso tocado, o clipe da mão direita (normal e a 0,5×) e a tablatura, e
responde: ``tipo``, ``sequencia`` (arpejo e tremolo), ``alternancia`` (melodia),
``apoio`` e ``obs``. Um item está completo quando tem ``tipo`` e ``apoio`` e, conforme o
tipo, ``sequencia`` ou ``alternancia``. O rótulo é do dono e é contrato: o agente não
rotula nem infere.

Este módulo tem:

1. funções puras (validação de resposta, completo, progresso, próximo incompleto, ação),
   testadas no gate;
2. o subcomando ``servir``: servidor ``http.server`` com uma página por compasso. Grava
   cada mudança em disco (escrita atômica, nunca apaga resposta) e atende ``Range``, que o
   navegador usa para tocar o vídeo.

O material é gerado por ``tab.maos_padroes_preparar`` (sem GPU). Só stdlib, numpy e cv2,
para caber no gate.

Uso::

    python -m tab.maos_padroes servir --pasta data/saida/maos/m5/padroes \\
        --ouro data/gold/maos/padroes_direita.json --porta 8097
"""

from __future__ import annotations

import argparse
import copy
import datetime
import http.server
import json
import re
import sys
import threading
from pathlib import Path

from .caminhos import GABARITO_PADROES, MAOS_M5
from .maos_gabarito import gravar_atomico

#: Formato do gabarito dos padrões. O servidor só aceita este.
FORMATO_GABARITO = 1

#: Tipos de padrão (rótulo do dono; ``?`` é "não sei").
TIPOS = (
    "arpejo",
    "rasgueado",
    "tremolo",
    "plaqueado",
    "melodia",
    "misto",
    "?",
)

#: Apoio do polegar/dedos da mão direita nas cordas.
APOIOS = ("apoiado", "sem_apoio", "misto", "?")

#: Alternância de dedos para melodia.
ALTERNANCIAS = ("i-m", "m-a", "i-a", "p", "outra", "?")

#: Tipos que pedem a sequência de dedos.
TIPOS_COM_SEQUENCIA = ("arpejo", "tremolo")

#: Tipo que pede a alternância.
TIPO_MELODIA = "melodia"

#: Sequência válida: dedos p, i, m, a ou ``?`` separados por ``-`` (ex.: ``p-i-m-a``).
_REGEX_SEQUENCIA = re.compile(r"[pima?](-[pima?])*")

#: Campos que a página pode gravar.
CAMPOS_EDITAVEIS = ("tipo", "sequencia", "alternancia", "apoio", "obs")

#: Tamanho máximo de ``obs``.
TAMANHO_OBS_MAXIMO = 500

#: Tipos de arquivo que o servidor entrega da pasta do material.
_TIPOS = {
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".mp4": "video/mp4",
}


# ---------------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------------


def precisa_sequencia(tipo: str | None) -> bool:
    """Se o tipo pede a sequência de dedos (arpejo e tremolo).

    Args:
        tipo: tipo marcado, ou ``None``.

    Returns:
        True para ``arpejo`` e ``tremolo``.
    """
    return tipo in TIPOS_COM_SEQUENCIA


def precisa_alternancia(tipo: str | None) -> bool:
    """Se o tipo pede a alternância de dedos (melodia).

    Args:
        tipo: tipo marcado, ou ``None``.

    Returns:
        True para ``melodia``.
    """
    return tipo == TIPO_MELODIA


def validar_resposta(campo: str, valor: object) -> object:
    """Confere o valor de um campo e devolve a forma gravada.

    ``None`` e texto vazio limpam o campo (``None``). ``obs`` aceita texto livre até
    ``TAMANHO_OBS_MAXIMO``. ``sequencia`` é normalizada (minúsculas, sem espaços).

    Args:
        campo: um de ``CAMPOS_EDITAVEIS``.
        valor: valor enviado pela página.

    Returns:
        O valor a gravar (``str`` ou ``None``).

    Raises:
        ValueError: se o campo for desconhecido, ou o valor não for permitido.
    """
    if campo not in CAMPOS_EDITAVEIS:
        raise ValueError(f"campo desconhecido: {campo!r}")
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return None
    if not isinstance(valor, str):
        raise ValueError(f"{campo} deve ser texto")
    if campo == "obs":
        if len(valor) > TAMANHO_OBS_MAXIMO:
            raise ValueError(f"obs com mais de {TAMANHO_OBS_MAXIMO} caracteres")
        return valor
    texto = valor.strip().lower().replace(" ", "")
    if campo == "sequencia":
        if not _REGEX_SEQUENCIA.fullmatch(texto):
            raise ValueError(f"sequência inválida: {valor!r} (ex.: p-i-m-a)")
        return texto
    permitidos = {
        "tipo": TIPOS,
        "apoio": APOIOS,
        "alternancia": ALTERNANCIAS,
    }[campo]
    if texto not in permitidos:
        raise ValueError(f"{campo} inválido: {valor!r}")
    return texto


def completo(registro: dict) -> bool:
    """Se o item está pronto para o gabarito.

    Pronto é ``tipo`` e ``apoio`` preenchidos (``?`` conta como resposta); com
    ``arpejo`` ou ``tremolo`` também a ``sequencia``; com ``melodia`` também a
    ``alternancia``.

    Args:
        registro: resposta de um compasso.

    Returns:
        True se o item está completo.
    """
    if registro.get("tipo") is None or registro.get("apoio") is None:
        return False
    falta_sequencia = (
        precisa_sequencia(registro["tipo"]) and registro.get("sequencia") is None
    )
    falta_alternancia = (
        precisa_alternancia(registro["tipo"]) and registro.get("alternancia") is None
    )
    return not (falta_sequencia or falta_alternancia)


def progresso(gabarito: dict) -> tuple[int, int]:
    """Quantos itens estão completos, de quantos.

    Args:
        gabarito: gabarito com ``itens``.

    Returns:
        ``(completos, total)``.
    """
    itens = gabarito["itens"]
    return sum(1 for reg in itens.values() if completo(reg)), len(itens)


def proximo_incompleto(
    ordem: list[str], gabarito: dict, atual: str | None
) -> str | None:
    """Próximo item incompleto depois de ``atual``, dando a volta se preciso.

    O próprio ``atual`` nunca é devolvido.

    Args:
        ordem: ids dos itens, na ordem da página.
        gabarito: gabarito com ``itens``.
        atual: id do item de partida, ou ``None`` para começar do início.

    Returns:
        O id do próximo incompleto, ou ``None`` se não há nenhum.
    """
    inicio = ordem.index(atual) + 1 if atual in ordem else 0
    candidatos = ordem[inicio:] + ordem[:inicio]
    for id_item in candidatos:
        if id_item == atual:
            continue
        if not completo(gabarito["itens"][id_item]):
            return id_item
    return None


def aplicar_acao(
    gabarito: dict, id_item: str, campo: str, valor: object, agora: str
) -> dict:
    """Grava um campo de um item e devolve o registro atualizado.

    Args:
        gabarito: gabarito, alterado em lugar.
        id_item: id do compasso (``cNN``).
        campo: um de ``CAMPOS_EDITAVEIS``.
        valor: valor enviado (validado por ``validar_resposta``).
        agora: carimbo da resposta.

    Returns:
        O registro do item depois da mudança.

    Raises:
        KeyError: se o item não existe no gabarito.
        ValueError: se o campo ou o valor forem inválidos.
    """
    registro = gabarito["itens"][id_item]
    registro[campo] = validar_resposta(campo, valor)
    registro["respondido_em"] = agora
    return registro


def registro_em_branco(item: dict) -> dict:
    """Resposta de um compasso, sem nada marcado.

    Args:
        item: entrada do ``indice.json`` (``video``, ``tela``, ``compasso``, ``exibicao``).

    Returns:
        Registro com os campos de resposta em ``None``.
    """
    return {
        "video": item["video"],
        "tela": item["tela"],
        "compasso": item["compasso"],
        "exibicao": item["exibicao"],
        "tipo": None,
        "sequencia": None,
        "alternancia": None,
        "apoio": None,
        "obs": None,
        "respondido_em": None,
    }


def gabarito_novo(itens: list[dict], semente: int) -> dict:
    """Gabarito sem respostas para a amostra dada (formato 1).

    Args:
        itens: entradas do ``indice.json``.
        semente: semente do sorteio.

    Returns:
        Dicionário no formato do gabarito, com um registro por id.
    """
    return {
        "formato": FORMATO_GABARITO,
        "como_foi_rotulado": (
            "dono, por compasso tocado, na ferramenta tab.maos_padroes servir"
        ),
        "semente": semente,
        "ferramenta": "tab.maos_padroes",
        "itens": {it["id"]: registro_em_branco(it) for it in itens},
    }


def mesclar_gabarito(novo: dict, existente: dict | None) -> dict:
    """Mescla o gabarito recém-sorteado com o que já está no disco, sem apagar nada.

    Args:
        novo: gabarito gerado pela amostra atual.
        existente: gabarito do disco, ou ``None``.

    Returns:
        O gabarito novo, com as respostas do existente.

    Raises:
        ValueError: se o formato for outro, ou se uma resposta não couber na amostra.
    """
    if existente is None:
        return novo
    if existente.get("formato") != FORMATO_GABARITO:
        raise ValueError(
            f"gabarito existente tem formato {existente.get('formato')}, "
            f"esperado {FORMATO_GABARITO}"
        )
    for id_item, antigo in existente.get("itens", {}).items():
        if antigo.get("respondido_em") is None:
            continue
        if id_item not in novo["itens"]:
            raise ValueError(f"{id_item} tem resposta mas não está na amostra nova")
        atual = novo["itens"][id_item]
        for campo in ("video", "tela", "compasso", "exibicao"):
            if antigo.get(campo) != atual[campo]:
                raise ValueError(f"{id_item} tem resposta de outro compasso")
        for campo in (*CAMPOS_EDITAVEIS, "respondido_em"):
            atual[campo] = copy.deepcopy(antigo.get(campo))
    return novo


# ---------------------------------------------------------------------------------
# Servidor e página
# ---------------------------------------------------------------------------------


def criar_servidor(
    pasta: Path, ouro: Path, porta: int = 8097, host: str = "127.0.0.1"
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor (não o inicia). Por padrão escuta SOMENTE em 127.0.0.1.

    Args:
        pasta: pasta do ``preparar`` (``indice.json`` e as pastas ``cNN/``).
        ouro: gabarito; é carregado agora e gravado a cada resposta.
        porta: porta TCP (0 = uma livre).
        host: endereço de escuta (``0.0.0.0`` só dentro de container).

    Returns:
        O servidor; ``servidor.server_address[1]`` é a porta real.
    """
    pasta = pasta.resolve()
    indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
    estado = json.loads(ouro.read_text(encoding="utf-8"))
    ordem = [it["id"] for it in indice["itens"]]
    trava = threading.Lock()

    class Manipulador(http.server.BaseHTTPRequestHandler):
        """Serve a página, o gabarito, os arquivos do material e grava respostas."""

        server_version = "maos_padroes"

        def log_message(self, formato: str, *args: object) -> None:
            """Silencia o log por requisição (cada clique faria uma linha)."""

        def _json(self, codigo: int, dados: dict) -> None:
            """Responde com um objeto JSON.

            Args:
                codigo: status HTTP.
                dados: corpo.
            """
            corpo = json.dumps(dados, ensure_ascii=False).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", _TIPOS[".json"])
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _host_ok(self) -> bool:
            """Recusa Host e Origin que não sejam a máquina local (rebinding, CSRF).

            Returns:
                True se a requisição vem da máquina local.
            """
            local = {"127.0.0.1", "localhost"}
            host_cabecalho = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            origem = self.headers.get("Origin")
            if host_cabecalho not in local:
                return False
            if origem is None:
                return True
            return (
                re.fullmatch(r"http://(127\.0\.0\.1|localhost)(:\d+)?", origem)
                is not None
            )

        def _arquivo(self, alvo: Path) -> None:
            """Entrega um arquivo do material, com suporte a ``Range`` (vídeo).

            Args:
                alvo: arquivo dentro da pasta do material.
            """
            tamanho = alvo.stat().st_size
            inicio, fim, codigo = 0, tamanho - 1, 200
            cabecalho = self.headers.get("Range")
            if cabecalho:
                casa = re.fullmatch(r"bytes=(\d*)-(\d*)", cabecalho.strip())
                if casa is None or (not casa.group(1) and not casa.group(2)):
                    self._faixa_invalida(tamanho)
                    return
                if casa.group(1):
                    inicio = int(casa.group(1))
                    if casa.group(2):
                        fim = min(int(casa.group(2)), tamanho - 1)
                else:
                    inicio = max(0, tamanho - int(casa.group(2)))
                if inicio > fim or inicio >= tamanho:
                    self._faixa_invalida(tamanho)
                    return
                codigo = 206
            with alvo.open("rb") as f:
                f.seek(inicio)
                corpo = f.read(fim - inicio + 1)
            self.send_response(codigo)
            self.send_header("Content-Type", _TIPOS[alvo.suffix])
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            if codigo == 206:
                self.send_header("Content-Range", f"bytes {inicio}-{fim}/{tamanho}")
            self.end_headers()
            self.wfile.write(corpo)

        def _faixa_invalida(self, tamanho: int) -> None:
            """Responde 416 para um ``Range`` que não cabe no arquivo.

            Args:
                tamanho: tamanho do arquivo, em bytes.
            """
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{tamanho}")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:
            """Página, gabarito atual, índice e arquivos do material."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            caminho = self.path.split("?", 1)[0]
            if caminho in {"/", "/index.html"}:
                corpo = PAGINA.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(corpo)
                return
            if caminho == "/gabarito.json":
                with trava:
                    self._json(200, estado)
                return
            alvo = (pasta / caminho.lstrip("/")).resolve()
            if alvo.suffix in _TIPOS and alvo.is_relative_to(pasta) and alvo.is_file():
                self._arquivo(alvo)
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def do_POST(self) -> None:
            """``/responder``: grava um campo de um compasso, em escrita atômica."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            if self.path != "/responder":
                self._json(404, {"ok": False, "erro": "não encontrado"})
                return
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                if not 0 < tamanho <= 16_000:
                    raise ValueError("corpo ausente ou grande demais")
                dados = json.loads(self.rfile.read(tamanho))
                if not isinstance(dados, dict):
                    raise ValueError("o corpo deve ser um objeto JSON")
                id_item = dados["id"]
                agora = datetime.datetime.now().isoformat(timespec="seconds")
                with trava:
                    anterior = copy.deepcopy(estado)
                    era_completo = completo(estado["itens"][id_item])
                    try:
                        registro = aplicar_acao(
                            estado, id_item, dados["campo"], dados.get("valor"), agora
                        )
                        gravar_atomico(ouro, estado)
                    except OSError:
                        estado.clear()
                        estado.update(anterior)
                        raise
                    feitos, total = progresso(estado)
                    agora_completo = completo(registro)
                    proximo = (
                        proximo_incompleto(ordem, estado, id_item)
                        if agora_completo and not era_completo
                        else None
                    )
            except (ValueError, KeyError, TypeError) as erro:
                self._json(400, {"ok": False, "erro": f"{type(erro).__name__}: {erro}"})
                return
            except OSError as erro:
                self._json(500, {"ok": False, "erro": f"não gravou em disco: {erro}"})
                return
            self._json(
                200,
                {
                    "ok": True,
                    "id": id_item,
                    "registro": registro,
                    "completo": agora_completo,
                    "completos": feitos,
                    "total": total,
                    "proximo": proximo,
                    "salvo_em": agora,
                },
            )

    return http.server.ThreadingHTTPServer((host, porta), Manipulador)


PAGINA = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Padrões da mão direita</title>
<style>
:root { --fundo:#f6f5f2; --texto:#1d1d1b; --cartao:#ffffff; --borda:#d9d6cc;
  --destaque:#2f6fb0; --feito:#2e7d4f; --apagado:#9a9a94; --aviso:#8a5a00; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --fundo:#1b1c1e; --texto:#ecebe6; --cartao:#26282b;
    --borda:#3b3e43; --destaque:#6aa6e8; --feito:#6cc08f; --apagado:#77787c; --aviso:#e0b15a; }
}
:root[data-theme="dark"] { --fundo:#1b1c1e; --texto:#ecebe6; --cartao:#26282b;
  --borda:#3b3e43; --destaque:#6aa6e8; --feito:#6cc08f; --apagado:#77787c; --aviso:#e0b15a; }
body { margin:0; background:var(--fundo); color:var(--texto);
  font-family: system-ui, "Liberation Sans", Arial, sans-serif; line-height:1.4; }
main { max-width: 1100px; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.35rem; margin: 4px 0 8px; }
h2 { font-size: 1.05rem; margin: 0 0 8px; }
.tutorial { background:var(--cartao); border:1px solid var(--borda); border-radius:10px;
  padding:12px 16px; margin-bottom:14px; }
.tutorial ol { margin:6px 0 0 20px; padding:0; }
.tutorial li { margin: 3px 0; }
.barra { display:flex; flex-wrap:wrap; gap:8px; align-items:center; justify-content:space-between;
  margin-bottom:12px; }
.contador { font-weight:600; }
.cartao { background:var(--cartao); border:1px solid var(--borda); border-radius:10px;
  padding:14px; margin-bottom:14px; }
.info { color:var(--apagado); font-size:.92rem; }
.videos { display:grid; grid-template-columns: minmax(0,2fr) minmax(0,1fr); gap:10px; }
.videos figure { margin:0; }
.videos figcaption { font-size:.85rem; color:var(--apagado); margin-bottom:4px; }
.videos video { width:100%; border-radius:6px; background:#000; display:block; }
.tab img { width:100%; border-radius:6px; background:#fff; display:block; }
.campo { margin: 12px 0; }
.campo > label, .campo > .rotulo { display:block; font-weight:600; margin-bottom:6px; }
.opcoes { display:flex; flex-wrap:wrap; gap:6px; }
button { font: inherit; padding: 8px 12px; border-radius:7px; border:1px solid var(--borda);
  background:var(--cartao); color:var(--texto); cursor:pointer; min-height: 40px; }
button:hover { border-color: var(--destaque); }
button.marcado { background: var(--destaque); border-color: var(--destaque); color:#fff; }
button:disabled { opacity:.45; cursor:not-allowed; }
button.pequeno { min-height: 36px; padding: 6px 10px; }
.seq { display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.seq input { font: inherit; font-size:1.1rem; padding:8px; min-width: 220px; flex:1;
  border:1px solid var(--borda); border-radius:7px; background:var(--cartao); color:var(--texto); }
.dica { font-size:.88rem; color:var(--apagado); margin-top:4px; }
.inativo { opacity:.55; }
textarea { width:100%; box-sizing:border-box; font:inherit; padding:8px; min-height:60px;
  border:1px solid var(--borda); border-radius:7px; background:var(--cartao); color:var(--texto); }
.nav { display:flex; flex-wrap:wrap; gap:8px; justify-content:space-between; margin-top:10px; }
.feito { color: var(--feito); font-weight:600; }
.erro { color: #b3261e; font-weight:600; min-height:1.2em; }
.salvo { color: var(--apagado); font-size:.9rem; min-height:1.2em; }
@media (max-width: 720px) {
  main { padding: 12px; }
  .videos { grid-template-columns: 1fr; }
}
</style></head>
<body><main>
<h1>Padrões da mão direita</h1>
<section class="tutorial">
  <strong>Como responder (cada compasso):</strong>
  <ol>
    <li>Assista ao vídeo <em>lento</em> (grande), que é a 0,5 de velocidade. O menor é o normal.</li>
    <li>Olhe a tablatura embaixo: o retângulo vermelho marca o compasso.</li>
    <li>Escolha o <strong>tipo</strong> do padrão.</li>
    <li>Se for <strong>arpejo</strong> ou <strong>trêmolo</strong>, escreva a <strong>sequência</strong> de dedos
      tocada (p, i, m, a), na ordem. Use os botões ou digite. Ex.: p-i-m-a-m-i.</li>
    <li>Se for <strong>melodia</strong>, escolha a <strong>alternância</strong> dos dedos principais.</li>
    <li>Escolha o <strong>apoio</strong> (se a mão apoia nas cordas). Se não souber, marque ?.</li>
    <li>Ao completar, a página avança sozinha. Use <em>Anterior</em> e <em>Próximo</em> para voltar.</li>
  </ol>
  <div class="dica">Cada resposta é gravada na hora. Nada apaga o que já foi respondido.
    Atalhos: seta esquerda e seta direita trocam de compasso.</div>
</section>

<div class="barra">
  <div class="contador" id="contador">carregando...</div>
  <div class="info" id="posicao"></div>
</div>

<section class="cartao" id="cabecalho">
  <h2 id="titulo"></h2>
  <div class="info" id="info"></div>
</section>

<section class="cartao">
  <div class="videos">
    <figure>
      <figcaption>Lento (0,5×)</figcaption>
      <video id="v_lento" controls loop autoplay muted playsinline preload="auto"></video>
    </figure>
    <figure>
      <figcaption>Normal</figcaption>
      <video id="v_normal" controls loop autoplay muted playsinline preload="auto"></video>
    </figure>
  </div>
</section>

<section class="cartao tab">
  <h2>Tablatura (o retângulo marca o compasso)</h2>
  <img id="imgtab" alt="tablatura do compasso">
</section>

<section class="cartao">
  <div class="campo">
    <span class="rotulo">Tipo do padrão</span>
    <div class="opcoes" id="opc_tipo"></div>
  </div>

  <div class="campo" id="bloco_seq">
    <span class="rotulo">Sequência de dedos (só arpejo e trêmolo)</span>
    <div class="seq">
      <input id="seq" type="text" inputmode="text" autocomplete="off"
        placeholder="ex.: p-i-m-a-m-i" aria-label="sequência de dedos">
      <button type="button" class="pequeno" data-seq="p">p</button>
      <button type="button" class="pequeno" data-seq="i">i</button>
      <button type="button" class="pequeno" data-seq="m">m</button>
      <button type="button" class="pequeno" data-seq="a">a</button>
      <button type="button" class="pequeno" data-seq="-">-</button>
      <button type="button" class="pequeno" id="seq_apagar">apagar</button>
    </div>
    <div class="dica" id="dica_seq"></div>
  </div>

  <div class="campo" id="bloco_alt">
    <span class="rotulo">Alternância de dedos (só melodia)</span>
    <div class="opcoes" id="opc_alt"></div>
  </div>

  <div class="campo">
    <span class="rotulo">Apoio da mão</span>
    <div class="opcoes" id="opc_apoio"></div>
  </div>

  <div class="campo">
    <label class="rotulo" for="obs">Observação (opcional)</label>
    <textarea id="obs" maxlength="500" placeholder="o que chamou atenção"></textarea>
  </div>

  <div class="erro" id="erro"></div>
  <div class="salvo" id="salvo"></div>

  <div class="nav">
    <button type="button" id="ant">Anterior</button>
    <button type="button" id="prox_inc">Ir para o próximo incompleto</button>
    <button type="button" id="prox">Próximo</button>
  </div>
</section>
</main>

<script>
const TIPOS = [
  ["arpejo", "arpejo", "notas uma depois da outra"],
  ["rasgueado", "rasgueado", "os dedos varrem as cordas"],
  ["tremolo", "trêmolo", "a mesma nota repetida rápido"],
  ["plaqueado", "plaqueado", "notas juntas, de uma vez"],
  ["melodia", "melodia", "uma voz principal"],
  ["misto", "misto", "mistura de padrões"],
  ["?", "não sei", ""]
];
const APOIOS = [["apoiado", "apoiado"], ["sem_apoio", "sem apoio"], ["misto", "misto"], ["?", "não sei"]];
const ALTERNANCIAS = [["i-m", "i-m"], ["m-a", "m-a"], ["i-a", "i-a"], ["p", "p"], ["outra", "outra"], ["?", "não sei"]];
const TIPOS_SEQ = ["arpejo", "tremolo"];

let indice = [];
let gabarito = null;
let atual = 0;
let sequenciaTimer = null;
let sequenciaPendente = false;

function $(id) { return document.getElementById(id); }

function completo(reg) {
  if (!reg || reg.tipo == null || reg.apoio == null) return false;
  if (TIPOS_SEQ.includes(reg.tipo) && reg.sequencia == null) return false;
  if (reg.tipo === "melodia" && reg.alternancia == null) return false;
  return true;
}

function idAtual() { return indice[atual].id; }
function regAtual() { return gabarito.itens[idAtual()]; }

function botoes(container, opcoes, campo, valorAtual, aoMudar) {
  container.innerHTML = "";
  opcoes.forEach(([valor, rotulo, ajuda]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = rotulo;
    if (ajuda) b.title = ajuda;
    if (valorAtual === valor) b.classList.add("marcado");
    b.addEventListener("click", () => gravar(campo, valorAtual === valor ? null : valor));
    container.appendChild(b);
  });
}

function render() {
  if (!gabarito) return;
  const it = indice[atual];
  const reg = regAtual();
  const [feitos, total] = [
    Object.values(gabarito.itens).filter(completo).length,
    Object.keys(gabarito.itens).length
  ];
  $("contador").textContent = `${feitos}/${total} completos`;
  $("posicao").textContent = `compasso ${atual + 1} de ${indice.length}`;
  $("titulo").textContent = `${it.id}: compasso ${it.compasso}, tela ${it.tela}, exibição ${it.exibicao}`;
  const [ini, fim] = it.janela;
  $("info").textContent = `${it.video} · ${it.n_notas} notas · janela ${ini.toFixed(1)} s a ${fim.toFixed(1)} s`;
  const vl = $("v_lento"), vn = $("v_normal");
  if (!vl.src.endsWith(`/${it.id}/clipe_lento.mp4`)) {
    vl.src = `${it.id}/clipe_lento.mp4`;
    vn.src = `${it.id}/clipe.mp4`;
  }
  $("imgtab").src = `${it.id}/tab.png`;
  botoes($("opc_tipo"), TIPOS, "tipo", reg.tipo, null);
  botoes($("opc_apoio"), APOIOS, "apoio", reg.apoio, null);
  botoes($("opc_alt"), ALTERNANCIAS, "alternancia", reg.alternancia, null);
  const seqAtiva = TIPOS_SEQ.includes(reg.tipo);
  const altAtiva = reg.tipo === "melodia";
  $("bloco_seq").classList.toggle("inativo", !seqAtiva);
  $("bloco_alt").classList.toggle("inativo", !altAtiva);
  document.querySelectorAll("[data-seq], #seq_apagar, #seq").forEach(el => el.disabled = !seqAtiva);
  document.querySelectorAll("#opc_alt button").forEach(b => b.disabled = !altAtiva);
  if (!sequenciaPendente && document.activeElement !== $("seq")) {
    $("seq").value = reg.sequencia || "";
  }
  if (document.activeElement !== $("obs")) $("obs").value = reg.obs || "";
  $("dica_seq").textContent = seqAtiva
    ? "Ordem tocada, da primeira à última nota (p, i, m, a)."
    : "Só para arpejo e trêmolo. Escolha o tipo acima.";
  $("ant").disabled = atual === 0;
  $("prox").disabled = atual === indice.length - 1;
  $("prox_inc").disabled = !Object.values(gabarito.itens).some(r => !completo(r));
  $("salvo").textContent = reg.respondido_em ? `última resposta: ${reg.respondido_em}` : "ainda não respondido";
  $("erro").textContent = "";
}

async function enviar(campo, valor) {
  const resp = await fetch("/responder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: idAtual(), campo, valor })
  });
  const dados = await resp.json();
  if (!dados.ok) {
    $("erro").textContent = "Não foi gravado: " + dados.erro;
    return null;
  }
  gabarito.itens[dados.id] = dados.registro;
  $("salvo").textContent = `gravado às ${dados.salvo_em}`;
  return dados;
}

async function salvarSequencia() {
  clearTimeout(sequenciaTimer);
  if (!sequenciaPendente) return;
  sequenciaPendente = false;
  await gravar("sequencia", $("seq").value);
}

async function gravar(campo, valor) {
  if (campo !== "sequencia" && sequenciaPendente) await salvarSequencia();
  if (campo === "sequencia") { clearTimeout(sequenciaTimer); sequenciaPendente = false; }
  const dados = await enviar(campo, valor);
  if (!dados) return;
  if (dados.completo && dados.proximo) {
    const pos = indice.findIndex(it => it.id === dados.proximo);
    atual = pos;
  }
  render();
}

async function trocar(delta) {
  const novo = atual + delta;
  if (novo < 0 || novo >= indice.length) return;
  await salvarSequencia();
  atual = novo;
  render();
}

async function irProximoIncompleto() {
  await salvarSequencia();
  const pos = indice.findIndex((it, i) => i > atual && !completo(gabarito.itens[it.id]));
  const seg = pos >= 0 ? pos : indice.findIndex(it => !completo(gabarito.itens[it.id]));
  if (seg >= 0) { atual = seg; render(); }
}

function setup() {
  document.querySelectorAll("[data-seq]").forEach(b => b.addEventListener("click", () => {
    const campo = $("seq");
    const v = campo.value;
    const sep = b.dataset.seq;
    if (sep === "-") {
      if (v && !v.endsWith("-")) campo.value = v + "-";
    } else {
      campo.value = v + sep;
    }
    agendarSequencia();
  }));
  $("seq_apagar").addEventListener("click", () => { $("seq").value = ""; gravar("sequencia", null); });
  $("seq").addEventListener("input", agendarSequencia);
  $("seq").addEventListener("change", () => salvarSequencia());
  $("obs").addEventListener("change", () => gravar("obs", $("obs").value));
  $("ant").addEventListener("click", () => trocar(-1));
  $("prox").addEventListener("click", () => trocar(1));
  $("prox_inc").addEventListener("click", irProximoIncompleto);
  document.addEventListener("keydown", e => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    if (e.key === "ArrowLeft") trocar(-1);
    if (e.key === "ArrowRight") trocar(1);
  });
}

function agendarSequencia() {
  sequenciaPendente = true;
  clearTimeout(sequenciaTimer);
  sequenciaTimer = setTimeout(() => salvarSequencia(), 600);
}

async function carregar() {
  setup();
  const [ri, rg] = await Promise.all([fetch("indice.json"), fetch("/gabarito.json")]);
  indice = (await ri.json()).itens;
  gabarito = await rg.json();
  const pendente = indice.findIndex(it => !completo(gabarito.itens[it.id]));
  atual = pendente >= 0 ? pendente : 0;
  render();
}

carregar().catch(erro => { $("erro").textContent = "Falha ao carregar: " + erro; });
</script>
</body></html>
"""


def servir(pasta: Path, ouro: Path, porta: int, host: str) -> int:
    """Sobe o servidor e fica nele até Ctrl+C.

    Args:
        pasta: pasta do ``preparar`` (``indice.json`` e as pastas ``cNN/``).
        ouro: gabarito dos padrões (já criado pelo ``preparar``).
        porta: porta TCP.
        host: endereço de escuta.

    Returns:
        Código de saída.
    """
    if not (pasta / "indice.json").exists():
        print(f"sem indice.json em {pasta}; rode o preparar antes", file=sys.stderr)
        return 2
    if not ouro.exists():
        print(f"sem gabarito em {ouro}; rode o preparar antes", file=sys.stderr)
        return 2
    if json.loads(ouro.read_text(encoding="utf-8")).get("formato") != FORMATO_GABARITO:
        print(f"{ouro} não está no formato {FORMATO_GABARITO}", file=sys.stderr)
        return 2
    servidor = criar_servidor(pasta, ouro, porta, host)
    print(f"ferramenta dos padrões: http://127.0.0.1:{servidor.server_address[1]}/")
    print(f"escutando em {host}; cada resposta é gravada em: {ouro}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


def main() -> int:
    """Ponto de entrada do CLI (subcomando ``servir``).

    Returns:
        Código de saída.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    servidor = sub.add_parser("servir", help="servidor da ferramenta")
    servidor.add_argument("--pasta", type=Path, default=MAOS_M5)
    servidor.add_argument("--ouro", type=Path, default=GABARITO_PADROES)
    servidor.add_argument("--porta", type=int, default=8097)
    servidor.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    return servir(args.pasta, args.ouro, args.porta, args.host)


if __name__ == "__main__":
    sys.exit(main())
