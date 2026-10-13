"""Ferramenta dos padrões da mão direita (M5): regra, gabarito e servidor.

Fase M5 da trilha das mãos (``docs/decisoes/1004-m5-padroes-da-mao-direita.md``), revisada:
em vez de rotular do zero, o dono CONFIRMA a regra. Por compasso tocado, a regra
(``tab.maos_regra_direita``) dá o dedo de cada nota; o dono clica só no que estiver errado
e aperta "confirmar compasso".

O registro de cada compasso (formato 2) guarda:

- ``dedos``: por nota ``{corda, casa, t_ini, palpite, regra, dono}``. ``palpite`` e
  ``regra`` são o que a regra disse e o dono viu; ``dono`` é o dedo confirmado, ou ``l``
  quando a nota é ligada (slide, hammer-on, pull-off: sem ataque da direita). A regra nunca
  dá ``l``, então marcar ``l`` conta como troca;
- ``alteradas``: quantas notas o dono trocou (``dono != palpite``);
- ``confirmado``, ``obs``, ``respondido_em``.

O gabarito começa do zero (o rótulo do formato 1 foi descartado pelo dono). O contrato é
do dono: o agente não rotula.

Este módulo tem:

1. funções puras (validação, gabarito, confirmação, progresso), testadas no gate;
2. o subcomando ``servir``: servidor ``http.server`` com uma página para a amostra da
   página. Cada confirmação é gravada em disco (escrita atômica) e o servidor atende
   ``Range``, que o navegador usa para tocar o vídeo.

O material é gerado por ``tab.maos_padroes_preparar`` (sem GPU).

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
from .maos_regra_direita import atribuir_dedos_direita

#: Formato do gabarito dos padrões (2: confirmação por nota). O servidor só aceita este.
FORMATO_GABARITO = 2

#: Valores de ``dono`` aceitos: os dedos da mão direita e ``"l"`` (ligada: nota presa por
#: slide, hammer-on ou pull-off, sem ataque da direita).
DEDOS = ("p", "i", "m", "a", "l")

#: Tamanho máximo de ``obs``.
TAMANHO_OBS_MAXIMO = 500

#: Campos que identificam o compasso no gabarito (conferidos na mesclagem).
CAMPOS_DO_COMPASSO = ("video", "tela", "compasso", "exibicao")

#: Campos que a mesclagem copia de uma confirmação já existente.
CAMPOS_PRESERVADOS = ("dedos", "alteradas", "confirmado", "obs", "respondido_em")

COMO_FOI_ROTULADO = (
    "dono confirma, por compasso tocado, o dedo de cada nota sugerido pela regra "
    "(tab.maos_regra_direita), ou marca 'l' se a nota é ligada (sem ataque da direita); "
    "ferramenta tab.maos_padroes servir"
)

#: Tipos de arquivo que o servidor entrega da pasta do material.
_TIPOS = {
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".mp4": "video/mp4",
}


# ---------------------------------------------------------------------------------
# Validação e gabarito (funções puras)
# ---------------------------------------------------------------------------------


def validar_obs(valor: object) -> str | None:
    """Confere a observação de um compasso.

    Args:
        valor: texto enviado pela página, ou ``None``.

    Returns:
        O texto sem espaços nas pontas, ou ``None`` se vazio.

    Raises:
        ValueError: se não for texto ou passar de ``TAMANHO_OBS_MAXIMO``.
    """
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ValueError("obs deve ser texto")
    if len(valor) > TAMANHO_OBS_MAXIMO:
        raise ValueError(f"obs com mais de {TAMANHO_OBS_MAXIMO} caracteres")
    return valor.strip() or None


def validar_dedos(donos: object, n_notas: int) -> list[str]:
    """Confere os dedos confirmados pelo dono, um por nota do compasso.

    Args:
        donos: lista de dedos (``p``, ``i``, ``m``, ``a``) ou ``l`` (ligada), na ordem das
            notas.
        n_notas: quantas notas o compasso tem.

    Returns:
        A lista de dedos.

    Raises:
        ValueError: se não for lista, se o tamanho não bater ou se um dedo for inválido.
    """
    if not isinstance(donos, list):
        raise ValueError("dedos deve ser uma lista")
    if len(donos) != n_notas:
        raise ValueError(f"esperados {n_notas} dedos, vieram {len(donos)}")
    for dedo in donos:
        if dedo not in DEDOS:
            raise ValueError(f"dedo inválido: {dedo!r}")
    return list(donos)


def registro_em_branco(item: dict) -> dict:
    """Registro de um compasso, sem nada confirmado.

    Args:
        item: entrada do ``indice.json`` (com ``video``, ``tela``, ``compasso``,
            ``exibicao``).

    Returns:
        Registro formato 2, sem dedos, não confirmado.
    """
    return {
        "video": item["video"],
        "tela": item["tela"],
        "compasso": item["compasso"],
        "exibicao": item["exibicao"],
        "dedos": [],
        "alteradas": None,
        "confirmado": False,
        "obs": None,
        "respondido_em": None,
    }


def gabarito_novo(itens: list[dict], semente: int) -> dict:
    """Gabarito sem confirmações para a amostra dada (formato 2).

    Args:
        itens: entradas do ``indice.json``.
        semente: semente do sorteio.

    Returns:
        Dicionário no formato 2, com um registro por id.
    """
    return {
        "formato": FORMATO_GABARITO,
        "como_foi_rotulado": COMO_FOI_ROTULADO,
        "semente": semente,
        "ferramenta": "tab.maos_padroes",
        "itens": {it["id"]: registro_em_branco(it) for it in itens},
    }


def tem_resposta(registro: dict) -> bool:
    """Se o compasso já foi confirmado pelo dono.

    Args:
        registro: registro de um compasso.

    Returns:
        True quando ``confirmado`` é verdadeiro.
    """
    return registro.get("confirmado") is True


def mesclar_gabarito(novo: dict, existente: dict | None) -> dict:
    """Mescla a amostra nova com o gabarito do disco, sem apagar confirmação.

    Cada compasso confirmado copia seus campos (``CAMPOS_PRESERVADOS``) para o item de
    mesmo id, desde que vídeo, tela, compasso e exibição batam.

    Args:
        novo: gabarito gerado pela amostra atual (formato 2).
        existente: gabarito do disco (formato 2), ou ``None``.

    Returns:
        O gabarito novo, com as confirmações do existente.

    Raises:
        ValueError: se o formato do existente não for o 2, ou se uma confirmação não
            couber na amostra nova.
    """
    if existente is None:
        return novo
    if existente.get("formato") != FORMATO_GABARITO:
        raise ValueError(
            f"gabarito existente tem formato {existente.get('formato')}, "
            f"esperado {FORMATO_GABARITO}"
        )
    for id_item, antigo in existente["itens"].items():
        if not tem_resposta(antigo):
            continue
        if id_item not in novo["itens"]:
            raise ValueError(f"{id_item} tem resposta mas não está na amostra nova")
        atual = novo["itens"][id_item]
        for campo in CAMPOS_DO_COMPASSO:
            if antigo.get(campo) != atual[campo]:
                raise ValueError(f"{id_item} tem resposta de outro compasso")
        for campo in CAMPOS_PRESERVADOS:
            atual[campo] = copy.deepcopy(antigo.get(campo))
    return novo


def vista_do_item(item: dict) -> dict:
    """O que a página mostra de um compasso: notas com o palpite da regra.

    Args:
        item: entrada do ``indice.json`` (com ``notas``, ``janela``, ``n_notas``...).

    Returns:
        Dicionário com ``id``, ``video``, ``tela``, ``compasso``, ``exibicao``,
        ``janela``, ``n_notas`` e ``notas`` (``corda``, ``casa``, ``t_ini``,
        ``palpite``, ``regra``) na ordem de tempo.
    """
    previstos = atribuir_dedos_direita(item["notas"])
    return {
        "id": item["id"],
        "video": item["video"],
        "tela": item["tela"],
        "compasso": item["compasso"],
        "exibicao": item["exibicao"],
        "janela": item["janela"],
        "n_notas": item["n_notas"],
        "notas": [
            {
                "corda": p["corda"],
                "casa": p["casa"],
                "t_ini": p["t_ini"],
                "palpite": p["dedo"],
                "regra": p["regra"],
            }
            for p in previstos
        ],
    }


def confirmar_compasso(
    gabarito: dict,
    id_item: str,
    notas: list[dict],
    dedos_donos: object,
    obs: object,
    agora: str,
) -> dict:
    """Grava a confirmação do dono num compasso e devolve o registro.

    ``palpite`` e ``regra`` são recalculados aqui, com a regra atual, e guardados junto
    com o ``dono``: o registro mostra o que a regra disse no momento da confirmação.

    Args:
        gabarito: gabarito formato 2, alterado em lugar.
        id_item: id do compasso (``cNN``).
        notas: notas do compasso no ``indice.json`` (``corda``, ``casa``, ``t_ini``).
        dedos_donos: dedo confirmado de cada nota, na ordem da página.
        obs: observação (opcional).
        agora: carimbo da confirmação.

    Returns:
        O registro do compasso depois da mudança.

    Raises:
        KeyError: se o id não existe no gabarito.
        ValueError: se os dedos ou a observação forem inválidos.
    """
    registro = gabarito["itens"][id_item]
    previstos = atribuir_dedos_direita(notas)
    donos = validar_dedos(dedos_donos, len(previstos))
    texto_obs = validar_obs(obs)
    dedos = [
        {
            "corda": p["corda"],
            "casa": p["casa"],
            "t_ini": p["t_ini"],
            "palpite": p["dedo"],
            "regra": p["regra"],
            "dono": dono,
        }
        for p, dono in zip(previstos, donos, strict=True)
    ]
    registro["dedos"] = dedos
    registro["alteradas"] = sum(1 for d in dedos if d["dono"] != d["palpite"])
    registro["confirmado"] = True
    registro["obs"] = texto_obs
    registro["respondido_em"] = agora
    return registro


def ordem_da_pagina(itens: list[dict]) -> list[str]:
    """Ids que aparecem na página: só os compassos com ``na_pagina`` marcado.

    Args:
        itens: entradas do ``indice.json``; ``na_pagina`` marca a amostra da página.

    Returns:
        Ids na ordem do índice.
    """
    return [it["id"] for it in itens if it.get("na_pagina")]


def progresso(gabarito: dict, ordem: list[str]) -> tuple[int, int]:
    """Quantos compassos da página estão confirmados, de quantos.

    Args:
        gabarito: gabarito formato 2.
        ordem: ids da página.

    Returns:
        ``(confirmados, total)``.
    """
    confirmados = sum(
        1 for id_item in ordem if gabarito["itens"][id_item].get("confirmado") is True
    )
    return confirmados, len(ordem)


def proximo_pendente(ordem: list[str], gabarito: dict, atual: str | None) -> str | None:
    """Próximo compasso não confirmado depois de ``atual``, dando a volta se preciso.

    Args:
        ordem: ids da página, na ordem.
        gabarito: gabarito formato 2.
        atual: id de partida, ou ``None`` para começar do início.

    Returns:
        O id do próximo não confirmado, ou ``None`` se todos estão confirmados.
    """
    inicio = ordem.index(atual) + 1 if atual in ordem else 0
    for id_item in ordem[inicio:] + ordem[:inicio]:
        if id_item == atual:
            continue
        if gabarito["itens"][id_item].get("confirmado") is not True:
            return id_item
    return None


# ---------------------------------------------------------------------------------
# Servidor e página
# ---------------------------------------------------------------------------------


def criar_servidor(
    pasta: Path, ouro: Path, porta: int = 8097, host: str = "127.0.0.1"
) -> http.server.ThreadingHTTPServer:
    """Cria o servidor (não o inicia). Por padrão escuta SOMENTE em 127.0.0.1.

    Args:
        pasta: pasta do ``preparar`` (``indice.json`` e as pastas ``cNN/``).
        ouro: gabarito formato 2; é carregado agora e gravado a cada confirmação.
        porta: porta TCP (0 = uma livre).
        host: endereço de escuta (``0.0.0.0`` só dentro de container).

    Returns:
        O servidor; ``servidor.server_address[1]`` é a porta real.

    Raises:
        ValueError: se o gabarito não estiver no formato 2.
    """
    pasta = pasta.resolve()
    indice = json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
    estado = json.loads(ouro.read_text(encoding="utf-8"))
    if estado.get("formato") != FORMATO_GABARITO:
        raise ValueError(f"{ouro} não está no formato {FORMATO_GABARITO}")
    por_id = {it["id"]: it for it in indice["itens"]}
    ordem = ordem_da_pagina(indice["itens"])
    vistas = [vista_do_item(por_id[id_item]) for id_item in ordem]
    trava = threading.Lock()

    class Manipulador(http.server.BaseHTTPRequestHandler):
        """Serve a página, o gabarito, os itens e os arquivos; grava confirmações."""

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
            """Página, gabarito atual, itens da página e arquivos do material."""
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
            if caminho == "/itens.json":
                self._json(200, {"itens": vistas})
                return
            alvo = (pasta / caminho.lstrip("/")).resolve()
            if alvo.suffix in _TIPOS and alvo.is_relative_to(pasta) and alvo.is_file():
                self._arquivo(alvo)
                return
            self._json(404, {"ok": False, "erro": "não encontrado"})

        def do_POST(self) -> None:
            """``/confirmar``: grava a confirmação de um compasso, em escrita atômica."""
            if not self._host_ok():
                self._json(403, {"ok": False, "erro": "host recusado"})
                return
            if self.path != "/confirmar":
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
                if id_item not in por_id:
                    raise KeyError(id_item)
                agora = datetime.datetime.now().isoformat(timespec="seconds")
                with trava:
                    anterior = copy.deepcopy(estado)
                    try:
                        registro = confirmar_compasso(
                            estado,
                            id_item,
                            por_id[id_item]["notas"],
                            dados.get("dedos"),
                            dados.get("obs"),
                            agora,
                        )
                        gravar_atomico(ouro, estado)
                    except OSError:
                        estado.clear()
                        estado.update(anterior)
                        raise
                    confirmados, total = progresso(estado, ordem)
                    proximo = proximo_pendente(ordem, estado, id_item)
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
                    "alteradas": registro["alteradas"],
                    "confirmados": confirmados,
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
  --destaque:#2f6fb0; --feito:#2e7d4f; --apagado:#8a8a84; --aviso:#8a5a00; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --fundo:#1b1c1e; --texto:#ecebe6; --cartao:#26282b;
    --borda:#3b3e43; --destaque:#6aa6e8; --feito:#6cc08f; --apagado:#9a9ba0; --aviso:#e0b15a; }
}
:root[data-theme="dark"] { --fundo:#1b1c1e; --texto:#ecebe6; --cartao:#26282b;
  --borda:#3b3e43; --destaque:#6aa6e8; --feito:#6cc08f; --apagado:#9a9ba0; --aviso:#e0b15a; }
body { margin:0; background:var(--fundo); color:var(--texto);
  font-family: system-ui, "Liberation Sans", Arial, sans-serif; line-height:1.4; }
main { max-width: 1100px; margin: 0 auto; padding: 16px; box-sizing:border-box; }
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
  padding:14px; margin-bottom:14px; min-width:0; }
.info { color:var(--apagado); font-size:.92rem; overflow-wrap:anywhere; }
.videos { display:grid; grid-template-columns: minmax(0,2fr) minmax(0,1fr); gap:10px; }
.videos figure { margin:0; min-width:0; }
.videos figcaption { font-size:.85rem; color:var(--apagado); margin-bottom:4px; }
.videos video { width:100%; border-radius:6px; background:#000; display:block; }
.tab img { width:100%; border-radius:6px; background:#fff; display:block; }
.notas { margin-top:4px; }
.nota { display:flex; flex-wrap:wrap; gap:6px 10px; align-items:center;
  padding:9px 8px; border-bottom:1px solid var(--borda); border-left:4px solid transparent; }
.nota.trocada { border-left-color: var(--aviso); }
.nota.ligada .tempo, .nota.ligada .local { text-decoration: line-through; color: var(--apagado); }
.opcoes .lig { margin-left: 14px; border-style: dashed; }
.nota .tempo { min-width: 96px; font-variant-numeric: tabular-nums; font-weight:600; }
.nota .local { min-width: 120px; }
.nota .regra { flex-basis:100%; font-size:.82rem; color:var(--apagado); }
.opcoes { display:flex; flex-wrap:wrap; gap:6px; }
button { font: inherit; padding: 8px 12px; border-radius:7px; border:1px solid var(--borda);
  background:var(--cartao); color:var(--texto); cursor:pointer; min-height: 40px; min-width:44px; }
button:hover { border-color: var(--destaque); }
button.marcado { background: var(--destaque); border-color: var(--destaque); color:#fff; }
button:disabled { opacity:.45; cursor:not-allowed; }
button.confirmar { width:100%; min-height:60px; font-size:1.15rem; font-weight:600;
  background: var(--feito); border-color: var(--feito); color:#fff; margin-top:8px; }
textarea { width:100%; box-sizing:border-box; font:inherit; padding:8px; min-height:60px;
  border:1px solid var(--borda); border-radius:7px; background:var(--cartao); color:var(--texto); }
.nav { display:flex; flex-wrap:wrap; gap:8px; justify-content:space-between; margin-top:10px; }
.erro { color: #b3261e; font-weight:600; min-height:1.2em; }
.salvo { color: var(--apagado); font-size:.9rem; min-height:1.2em; }
@media (max-width: 720px) {
  main { padding: 12px; }
  .videos { grid-template-columns: 1fr; }
  .nota .local { min-width: 0; }
}
</style></head>
<body><main>
<h1>Padrões da mão direita</h1>
<section class="tutorial">
  <strong>Como responder (cada compasso):</strong>
  <ol>
    <li>Veja o vídeo <em>lento</em> (0,5×) e o normal. A tablatura embaixo mostra o compasso em vermelho.</li>
    <li>A lista mostra cada nota (tempo, corda, casa) com o <strong>dedo que a regra achou</strong> já marcado.</li>
    <li>Só clique no dedo que estiver <strong>errado</strong>. Se estiver certo, não mexa.</li>
    <li>Se a nota for <strong>ligada</strong> (slide, hammer-on, pull-off: a direita não ataca), clique em <strong>lig</strong>. Ela fica riscada e conta como troca.</li>
    <li>Aperte <strong>Confirmar compasso</strong>. Isso grava e avança para o próximo pendente.</li>
  </ol>
  <div class="info">Nada é gravado até confirmar. Confirmar grava tudo que está na tela, inclusive o que
    você não mexeu. As trocas são contadas. Setas esquerda e direita trocam de compasso.</div>
</section>

<div class="barra">
  <div class="contador" id="contador">carregando...</div>
  <div class="info" id="posicao"></div>
</div>

<section class="cartao">
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
  <h2>Dedo de cada nota</h2>
  <div class="info" id="trocas"></div>
  <div class="notas" id="notas"></div>
  <div class="campo" style="margin-top:12px">
    <label for="obs"><strong>Observação (opcional)</strong></label>
    <textarea id="obs" maxlength="500" placeholder="o que chamou atenção"></textarea>
  </div>
  <div class="erro" id="erro"></div>
  <div class="salvo" id="salvo"></div>
  <button type="button" class="confirmar" id="confirmar">Confirmar compasso</button>
  <div class="nav">
    <button type="button" id="ant">Anterior</button>
    <button type="button" id="prox_inc">Próximo pendente</button>
    <button type="button" id="prox">Próximo</button>
  </div>
</section>
</main>

<script>
const ROTULOS = { p: "polegar", i: "indicador", m: "médio", a: "anelar",
  l: "ligado — sem ataque da direita (slide, hammer-on, pull-off…)" };
let itens = [];
let gabarito = null;
let atual = 0;
let rascunhos = {};   // id -> {dedos: [...], obs}: só na memória desta aba

function $(id) { return document.getElementById(id); }

function registro(id) { return gabarito.itens[id]; }

function salvo(id) {
  const r = registro(id);
  return r && r.confirmado === true;
}

// Dedos e obs do compasso como estão gravados (confirmado) ou como a regra sugere.
function base(item) {
  const r = registro(item.id);
  if (salvo(item.id) && r.dedos.length === item.notas.length) {
    return { dedos: r.dedos.map(d => d.dono), obs: r.obs || "" };
  }
  return { dedos: item.notas.map(n => n.palpite), obs: "" };
}

// Dedos e obs que aparecem na tela agora (rascunho desta aba, ou o gravado).
function atualDoCompasso(item) {
  return rascunhos[item.id] || base(item);
}

function trocasDe(item) {
  const cur = atualDoCompasso(item).dedos;
  return item.notas.reduce((c, n, k) => c + (cur[k] !== n.palpite ? 1 : 0), 0);
}

function naoGravado(item) {
  const cur = atualDoCompasso(item);
  const b = base(item);
  if (cur.obs !== b.obs) return true;
  return cur.dedos.some((d, k) => d !== b.dedos[k]);
}

function render() {
  if (!gabarito || itens.length === 0) return;
  const it = itens[atual];
  const reg = registro(it.id);
  const feitos = itens.filter(x => salvo(x.id)).length;
  $("contador").textContent = `${feitos}/${itens.length} confirmados`;
  $("posicao").textContent = `compasso ${atual + 1} de ${itens.length}`;
  $("titulo").textContent =
    `${it.id}: compasso ${it.compasso}, tela ${it.tela}, exibição ${it.exibicao}`;
  const [ini, fim] = it.janela;
  $("info").textContent =
    `${it.video} · ${it.n_notas} notas · janela ${ini.toFixed(1)} s a ${fim.toFixed(1)} s`;
  const vl = $("v_lento"), vn = $("v_normal");
  if (!vl.src.endsWith(`/${it.id}/clipe_lento.mp4`)) {
    vl.src = `${it.id}/clipe_lento.mp4`;
    vn.src = `${it.id}/clipe.mp4`;
  }
  $("imgtab").src = `${it.id}/tab.png`;

  const cur = atualDoCompasso(it);
  const lista = $("notas");
  lista.innerHTML = "";
  it.notas.forEach((n, k) => {
    const linha = document.createElement("div");
    linha.className = "nota" + (cur.dedos[k] !== n.palpite ? " trocada" : "")
      + (cur.dedos[k] === "l" ? " ligada" : "");
    const tempo = document.createElement("span");
    tempo.className = "tempo";
    tempo.textContent = `${n.t_ini.toFixed(2)} s`;
    const local = document.createElement("span");
    local.className = "local";
    local.textContent = `corda ${n.corda} · casa ${n.casa}`;
    const opc = document.createElement("div");
    opc.className = "opcoes";
    ["p", "i", "m", "a"].forEach(d => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = d;
      b.title = ROTULOS[d];
      if (cur.dedos[k] === d) b.classList.add("marcado");
      b.addEventListener("click", () => trocarDedo(k, d));
      opc.appendChild(b);
    });
    const b = document.createElement("button");
    b.type = "button";
    b.className = "lig";
    b.textContent = "lig";
    b.title = ROTULOS.l;
    if (cur.dedos[k] === "l") b.classList.add("marcado");
    b.addEventListener("click", () => trocarDedo(k, "l"));
    opc.appendChild(b);
    const regra = document.createElement("div");
    regra.className = "regra";
    regra.textContent = `palpite da regra: ${n.palpite} (${n.regra})`;
    linha.append(tempo, local, opc, regra);
    lista.appendChild(linha);
  });
  $("trocas").textContent = `trocas em relação à regra: ${trocasDe(it)}`;
  if (document.activeElement !== $("obs")) $("obs").value = cur.obs;
  $("prox_inc").disabled = !itens.some(x => !salvo(x.id));
  $("ant").disabled = atual === 0;
  $("prox").disabled = atual === itens.length - 1;
  const r = registro(it.id);
  $("salvo").textContent = salvo(it.id)
    ? `confirmado em ${r.respondido_em}` + (naoGravado(it) ? " · há mudanças não confirmadas" : "")
    : (naoGravado(it) ? "mudanças não confirmadas" : "ainda não confirmado");
  $("erro").textContent = "";
}

function trocarDedo(k, d) {
  const it = itens[atual];
  const cur = atualDoCompasso(it);
  const dedos = cur.dedos.slice();
  dedos[k] = d;
  rascunhos[it.id] = { dedos, obs: $("obs").value.trim() };
  render();
}

async function confirmar() {
  const it = itens[atual];
  const cur = atualDoCompasso(it);
  $("erro").textContent = "";
  const obs = $("obs").value;
  const resp = await fetch("/confirmar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: it.id, dedos: cur.dedos, obs: obs })
  });
  const dados = await resp.json();
  if (!dados.ok) {
    $("erro").textContent = "Não foi gravado: " + dados.erro;
    return;
  }
  gabarito.itens[dados.id] = dados.registro;
  delete rascunhos[dados.id];
  if (dados.proximo) {
    atual = itens.findIndex(x => x.id === dados.proximo);
  }
  render();
  $("salvo").textContent =
    `gravado às ${dados.salvo_em} · trocas: ${dados.alteradas} · ` +
    (dados.proximo ? "avancei para o próximo pendente" : "todos confirmados");
}

function irPara(pos) {
  if (pos < 0 || pos >= itens.length) return;
  atual = pos;
  render();
}

function irProximoPendente() {
  const pos = itens.findIndex((x, i) => i > atual && !salvo(x.id));
  const seg = pos >= 0 ? pos : itens.findIndex(x => !salvo(x.id));
  if (seg >= 0) irPara(seg);
}

function setup() {
  $("confirmar").addEventListener("click", () => confirmar().catch(e => {
    $("erro").textContent = "Falha ao gravar: " + e;
  }));
  $("ant").addEventListener("click", () => irPara(atual - 1));
  $("prox").addEventListener("click", () => irPara(atual + 1));
  $("prox_inc").addEventListener("click", irProximoPendente);
  $("obs").addEventListener("input", () => {
    const it = itens[atual];
    const cur = atualDoCompasso(it);
    rascunhos[it.id] = { dedos: cur.dedos, obs: $("obs").value };
  });
  document.addEventListener("keydown", e => {
    if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
    if (e.key === "ArrowLeft") irPara(atual - 1);
    if (e.key === "ArrowRight") irPara(atual + 1);
  });
}

async function carregar() {
  setup();
  const [ri, rg] = await Promise.all([fetch("/itens.json"), fetch("/gabarito.json")]);
  itens = (await ri.json()).itens;
  gabarito = await rg.json();
  const pendente = itens.findIndex(it => !salvo(it.id));
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
    formato = json.loads(ouro.read_text(encoding="utf-8")).get("formato")
    if formato != FORMATO_GABARITO:
        print(
            f"{ouro} está no formato {formato}; rode o preparar para migrar "
            f"para o {FORMATO_GABARITO}",
            file=sys.stderr,
        )
        return 2
    servidor = criar_servidor(pasta, ouro, porta, host)
    print(f"ferramenta dos padrões: http://127.0.0.1:{servidor.server_address[1]}/")
    print(f"escutando em {host}; cada confirmação é gravada em: {ouro}", flush=True)
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
