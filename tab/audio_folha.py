"""Folha de julgamento dos cliques do alinhador: clipes, página e sorteio.

O dono do projeto julga por escuta se o instante calculado para uma coluna da tablatura está
certo. Cada pedido vira um clipe de 4 s (de ``t_audio - 2`` a ``t_audio + 2``) em que a coluna
aparece destacada por um retângulo amarelo e um clique de 10 ms soa, mixado ao áudio original,
exatamente no instante pedido. Três subcomandos:

- ``clipes``: grava os MP4 e um ``manifesto.json``. As medidas de conferência (erro do primeiro
  quadro e do clique) são feitas de novo no MP4 final, decodificado, não na conta teórica;
- ``pagina``: gera um ``index.html`` estático (sem rede) para responder certo, errado ou não sei;
- ``sortear``: escolhe K colunas por vídeo a partir dos alinhamentos, com semente fixa.

Uso::

    python -m tab.audio_folha clipes --pedidos PEDIDOS.json --pasta PASTA
    python -m tab.audio_folha pagina --pasta PASTA
    python -m tab.audio_folha sortear --alinhados A.json [B.json ...] --por-video K \\
        --semente S --saida PEDIDOS.json
"""

import argparse
import html
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

from .audio_extrair import garantir, indice_de, instante_de
from .caminhos import SAIDA

#: Metade da janela do clipe: de ``t_audio - JANELA_S`` a ``t_audio + JANELA_S``.
JANELA_S = 2.0

#: Duração do clipe, em segundos.
DURACAO_CLIPE_S = 2 * JANELA_S

#: Largura máxima do clipe de saída, em px (a altura segue a proporção).
LARGURA_MAX = 1280

#: Metade da largura do retângulo, em passos, para cada lado do centro da coluna.
FATOR_DESTAQUE = 0.6

#: Espessura do retângulo amarelo, em px do quadro original.
ESPESSURA_DESTAQUE = 3

#: Taxa do áudio do clipe e da trilha de cliques, em Hz.
TAXA_MIX = 48000

#: Duração de cada clique, em segundos.
DURACAO_CLIQUE_S = 0.010

#: Frequência do clique, em Hz.
FREQ_CLIQUE_HZ = 2000.0

#: Amplitude do clique (fração do fundo de escala); audível, sem saturar.
AMPLITUDE_CLIQUE = 0.5

#: Janela de busca do clique na medição, em torno do instante esperado (s).
JANELA_BUSCA_S = 0.050

#: Atraso máximo considerado entre o áudio do MP4 e o original (s).
MAX_ATRASO_S = 0.050

#: Resolução em que os quadros são comparados na medição do erro do primeiro quadro.
LARGURA_MEDIDA = 320
ALTURA_MEDIDA = 180

#: Quanto antes do início pedido a leitura da fonte começa, para ver os quadros vizinhos (s).
MARGEM_QUADRO_S = 0.25

#: Prefixo do acervo dentro do container.
PREFIXO_ACERVO = "/acervo/"

#: Pasta, dentro de ``SAIDA``, onde ficam os produtos ``tab.video`` dos vídeos.
PASTA_PRODUTOS = SAIDA / "audio" / "a2" / "produtos"

#: Modelo da página. Os marcadores ``__TITULO__``, ``__NOME_JS__`` e ``__DADOS__`` são trocados.
_MODELO_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<style>
:root {
  --fundo: #f7f6f3; --texto: #1d1d1b; --borda: #d6d3cb; --cartao: #ffffff;
  --certo: #2f7d4f; --errado: #b03a2e; --nsei: #6b6b6b; --atual: #d9a400;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --fundo: #1b1c1e; --texto: #eceae4; --borda: #3a3c40; --cartao: #25262a;
  }
}
:root[data-theme="dark"] {
  --fundo: #1b1c1e; --texto: #eceae4; --borda: #3a3c40; --cartao: #25262a;
}
body { margin: 0; background: var(--fundo); color: var(--texto);
  font: 16px/1.45 system-ui, sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 16px; }
header { position: sticky; top: 0; background: var(--fundo); padding: 8px 0 12px;
  border-bottom: 1px solid var(--borda); z-index: 1; }
h1 { font-size: 20px; margin: 0 0 4px; }
.ajuda { margin: 0; font-size: 14px; opacity: .8; }
#contador { font-weight: 600; }
.clipe { background: var(--cartao); border: 2px solid var(--borda); border-radius: 8px;
  padding: 12px; margin: 16px 0; }
.clipe.atual { border-color: var(--atual); }
.clipe h2 { font-size: 15px; margin: 0 0 8px; font-weight: 600; }
video { width: 100%; max-height: 60vh; background: #000; border-radius: 4px; }
.botoes { display: flex; gap: 8px; margin: 10px 0; flex-wrap: wrap; }
button { font: inherit; padding: 10px 16px; border-radius: 6px; cursor: pointer;
  border: 2px solid var(--borda); background: transparent; color: var(--texto); }
button[data-resposta="certo"] { border-color: var(--certo); }
button[data-resposta="errado"] { border-color: var(--errado); }
button[data-resposta="nao_sei"] { border-color: var(--nsei); }
button[aria-pressed="true"][data-resposta="certo"] { background: var(--certo); color: #fff; }
button[aria-pressed="true"][data-resposta="errado"] { background: var(--errado); color: #fff; }
button[aria-pressed="true"][data-resposta="nao_sei"] { background: var(--nsei); color: #fff; }
input[type="text"] { width: 100%; box-sizing: border-box; font: inherit; padding: 8px;
  border: 1px solid var(--borda); border-radius: 6px; background: var(--fundo);
  color: var(--texto); }
#exportar { margin: 24px 0 40px; }
#saida { width: 100%; box-sizing: border-box; font: 13px ui-monospace, monospace;
  background: var(--cartao); color: var(--texto); border: 1px solid var(--borda);
  border-radius: 6px; padding: 8px; margin-top: 8px; }
#status { font-size: 14px; margin-left: 8px; }
</style>
</head>
<body>
<header>
  <main>
    <h1>__TITULO__</h1>
    <p class="ajuda">Atalhos: 1 certo, 2 errado, 3 não sei (responde o clipe atual e
      passa ao próximo). Espaço toca ou pausa o clipe atual.</p>
    <p id="contador"></p>
  </main>
</header>
<main id="lista">__CARTOES__</main>
<main id="exportar">
  <button type="button" id="copiar">copiar respostas</button>
  <span id="status"></span>
  <textarea id="saida" rows="8" readonly></textarea>
</main>
<script>
(function () {
  "use strict";
  var CLIPES = __DADOS__;
  var CHAVE = "chorinho-folha:" + __NOME_JS__;
  var FOLHA = __NOME_JS__;
  var estado = carregar();
  var atual = primeiroPendente();
  var contador = document.getElementById("contador");
  var saida = document.getElementById("saida");
  var status = document.getElementById("status");

  function carregar() {
    try {
      return JSON.parse(localStorage.getItem(CHAVE)) || {};
    } catch (_e) {
      return {};
    }
  }

  function gravar() {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(estado));
    } catch (_e) {
      status.textContent = "não consegui guardar no navegador";
    }
  }

  function respostaDe(i) {
    return (estado[CLIPES[i].id] || {}).resposta || null;
  }

  function primeiroPendente() {
    for (var i = 0; i < CLIPES.length; i++) {
      if (!respostaDe(i)) return i;
    }
    return 0;
  }

  function ligarCartoes() {
    var secoes = document.querySelectorAll("section.clipe");
    secoes.forEach(function (secao, i) {
      secao.querySelectorAll("button[data-resposta]").forEach(function (b) {
        b.addEventListener("click", function () {
          responder(i, b.getAttribute("data-resposta"));
        });
      });
      var obs = secao.querySelector("input[data-obs]");
      obs.value = (estado[CLIPES[i].id] || {}).obs || "";
      obs.addEventListener("input", function () {
        var e = estado[CLIPES[i].id] || {};
        e.obs = obs.value;
        estado[CLIPES[i].id] = e;
        gravar();
        atualizarSaida();
      });
      obs.addEventListener("focus", function () {
        marcarAtual(i);
      });
      secao.addEventListener("click", function () {
        marcarAtual(i);
      }, true);
    });
  }

  function atualizarCartao(i) {
    var secao = document.getElementById("clipe-" + i);
    var resposta = respostaDe(i);
    secao.querySelectorAll("button[data-resposta]").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-resposta") === resposta ? "true" : "false");
    });
  }

  function atualizarContador() {
    var feitos = 0;
    for (var i = 0; i < CLIPES.length; i++) {
      if (respostaDe(i)) feitos++;
    }
    contador.textContent = feitos + " de " + CLIPES.length + " respondidos";
  }

  function atualizarSaida() {
    var linhas = CLIPES.map(function (c) {
      var e = estado[c.id] || {};
      return { id: c.id, resposta: e.resposta || null, obs: e.obs || "" };
    });
    saida.value = JSON.stringify({ folha: FOLHA, respostas: linhas }, null, 2);
  }

  function marcarAtual(i) {
    if (i < 0 || i >= CLIPES.length) return;
    var antigo = document.querySelector(".clipe.atual");
    if (antigo) antigo.classList.remove("atual");
    atual = i;
    var secao = document.getElementById("clipe-" + i);
    secao.classList.add("atual");
  }

  function responder(i, resposta) {
    var id = CLIPES[i].id;
    var e = estado[id] || {};
    e.resposta = resposta;
    estado[id] = e;
    gravar();
    atualizarCartao(i);
    atualizarContador();
    atualizarSaida();
    if (i + 1 < CLIPES.length) {
      marcarAtual(i + 1);
      document.getElementById("clipe-" + (i + 1)).scrollIntoView({ block: "center" });
    }
  }

  document.addEventListener("keydown", function (ev) {
    var alvo = ev.target;
    if (alvo && (alvo.tagName === "INPUT" || alvo.tagName === "TEXTAREA")) return;
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === "1") responder(atual, "certo");
    else if (ev.key === "2") responder(atual, "errado");
    else if (ev.key === "3") responder(atual, "nao_sei");
    else if (ev.key === " ") {
      var video = document.querySelector("#clipe-" + atual + " video");
      if (video) {
        if (video.paused) video.play(); else video.pause();
      }
      ev.preventDefault();
    }
  });

  document.getElementById("copiar").addEventListener("click", function () {
    atualizarSaida();
    saida.focus();
    saida.select();
    try {
      navigator.clipboard.writeText(saida.value).then(function () {
        status.textContent = "copiado";
      }, function () {
        status.textContent = "selecione e copie o texto acima";
      });
    } catch (_e) {
      status.textContent = "selecione e copie o texto acima";
    }
  });

  ligarCartoes();
  CLIPES.forEach(function (c, i) {
    atualizarCartao(i);
  });
  atualizarContador();
  atualizarSaida();
  marcarAtual(atual);
})();
</script>
</body>
</html>
"""


def _ffmpeg(args: list[str]) -> bytes:
    """Roda o ffmpeg com ``-nostdin -v error`` e devolve o que ele escrever no stdout.

    Args:
        args: argumentos depois de ``ffmpeg -nostdin -v error``.

    Returns:
        O stdout do processo (vazio se o ffmpeg só gravar arquivo).

    Raises:
        RuntimeError: se o ffmpeg devolver erro.
    """
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", *args],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        erro = proc.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ffmpeg falhou: {erro}")
    return proc.stdout


def _sondar_video(caminho: str) -> tuple[int, int, float]:
    """Largura, altura e duração do primeiro stream de vídeo, lidas do ffprobe.

    Args:
        caminho: vídeo ou clipe.

    Returns:
        ``(largura, altura, duracao_s)``.

    Raises:
        RuntimeError: se o ffprobe falhar.
    """
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            caminho,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe falhou em {caminho}: {proc.stderr.strip()}")
    bruto = json.loads(proc.stdout)
    stream = bruto["streams"][0]
    duracao = float(bruto["format"]["duration"])
    return int(stream["width"]), int(stream["height"]), duracao


def _rajada() -> np.ndarray:
    """Forma de onda de um clique: senóide de ``FREQ_CLIQUE_HZ`` com envelope de Hann.

    Returns:
        Vetor de ``round(DURACAO_CLIQUE_S * TAXA_MIX)`` amostras, em ``[-1, 1]``.
    """
    n = round(DURACAO_CLIQUE_S * TAXA_MIX)
    t = np.arange(n) / TAXA_MIX
    return AMPLITUDE_CLIQUE * np.sin(2 * np.pi * FREQ_CLIQUE_HZ * t) * np.hanning(n)


def trilha_cliques(instantes_rel: list[float], dur: float) -> np.ndarray:
    """Trilha mono com um clique em cada instante dado (relativo ao início do clipe).

    Args:
        instantes_rel: instantes dos cliques, em segundos a partir do início do clipe.
        dur: duração do clipe, em segundos.

    Returns:
        Array ``float64`` de ``round(dur * TAXA_MIX)`` amostras.
    """
    n = round(dur * TAXA_MIX)
    trilha = np.zeros(n, dtype=np.float64)
    rajada = _rajada()
    for t in instantes_rel:
        i = round(t * TAXA_MIX)
        if 0 <= i < n:
            fim = min(n, i + len(rajada))
            trilha[i:fim] += rajada[: fim - i]
    return trilha


def _gravar_wav(caminho: Path, trilha: np.ndarray) -> None:
    """Grava uma trilha mono em WAV PCM 16 bits na taxa de ``TAXA_MIX``.

    Args:
        caminho: arquivo de saída.
        trilha: amostras em ``[-1, 1]``.
    """
    pcm = np.clip(np.round(trilha * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA_MIX)
        w.writeframes(pcm.tobytes())


def _caixa_destaque(
    x_centro: float, passo: float, painel: list[int], largura: int, altura: int
) -> tuple[int, int, int, int]:
    """Retângulo do destaque da coluna, em px do quadro original.

    Args:
        x_centro: ``x_centro_quadro`` médio da coluna.
        passo: distância entre cordas, em px.
        painel: ``[x0, y0, x1, y1]`` da tablatura no quadro.
        largura: largura do quadro.
        altura: altura do quadro.

    Returns:
        ``(x, y, w, h)`` com o retângulo recortado às bordas do quadro.
    """
    x0 = max(0, round(x_centro - FATOR_DESTAQUE * passo))
    x1 = min(largura - 1, round(x_centro + FATOR_DESTAQUE * passo))
    y0 = max(0, int(painel[1]))
    y1 = min(altura - 1, int(painel[3]))
    return x0, y0, x1 - x0, y1 - y0


def _audio_mono(caminho: str, inicio: float | None) -> np.ndarray:
    """Áudio de um arquivo como float mono, na taxa de ``TAXA_MIX``, no trecho do clipe.

    Args:
        caminho: vídeo ou clipe.
        inicio: início do trecho em segundos, ou ``None`` para o arquivo inteiro.

    Returns:
        Amostras ``float64`` em ``[-1, 1]``, de ``DURACAO_CLIPE_S`` (ou até o fim).
    """
    args: list[str] = []
    if inicio is not None:
        args += ["-ss", f"{inicio:.6f}"]
    args += [
        "-i",
        caminho,
        "-map",
        "0:a:0",
        "-t",
        f"{DURACAO_CLIPE_S:.6f}",
        "-ac",
        "1",
        "-ar",
        str(TAXA_MIX),
        "-f",
        "f32le",
        "-",
    ]
    return np.frombuffer(_ffmpeg(args), dtype="<f4").astype(np.float64)


def _atraso_amostras(saida: np.ndarray, original: np.ndarray) -> int:
    """Atraso, em amostras, do áudio do MP4 em relação ao original (correlação cruzada).

    Args:
        saida: áudio decodificado do MP4.
        original: áudio do vídeo original no mesmo trecho.

    Returns:
        ``m`` tal que ``saida[k] ~ original[k - m]``, com ``|m| <= MAX_ATRASO_S``.
    """
    n = min(len(saida), len(original))
    nfft = 1 << (2 * n - 1).bit_length()
    corr = np.fft.irfft(
        np.fft.rfft(saida[:n], nfft) * np.conj(np.fft.rfft(original[:n], nfft)), nfft
    )
    m = round(MAX_ATRASO_S * TAXA_MIX)
    defasagens = np.concatenate([np.arange(0, m + 1), np.arange(-m, 0)])
    return int(defasagens[np.argmax(corr[defasagens % nfft])])


def _residuo(saida: np.ndarray, original: np.ndarray, atraso: int) -> np.ndarray:
    """Diferença entre o MP4 e o original, alinhado pelo atraso: sobra o clique.

    Args:
        saida: áudio decodificado do MP4.
        original: áudio original do mesmo trecho.
        atraso: resultado de ``_atraso_amostras``.

    Returns:
        ``saida`` menos ``original`` deslocado por ``atraso``, no comprimento comum.
    """
    n = min(len(saida), len(original))
    alinhado = np.zeros(n)
    if atraso >= 0:
        alinhado[atraso:] = original[: n - atraso]
    else:
        alinhado[: n + atraso] = original[-atraso:n]
    return saida[:n] - alinhado


def _achar_clique(residuo: np.ndarray, t_esperado: float) -> tuple[float, float]:
    """Instante do clique no resíduo, por casamento de filtro perto do instante esperado.

    Args:
        residuo: saída de ``_residuo``.
        t_esperado: instante esperado do clique, em segundos a partir do início do clipe.

    Returns:
        ``(t_medido, similaridade)``: ``t_medido`` em segundos a partir do início do clipe, e a
        similaridade de cosseno (0 a 1) entre o trecho e a rajada, como indicador de confiança.
    """
    rajada = _rajada()
    corr = np.correlate(residuo, rajada, mode="valid")
    centro = round(t_esperado * TAXA_MIX)
    janela = round(JANELA_BUSCA_S * TAXA_MIX)
    ini = max(0, centro - janela)
    fim = min(len(corr), centro + janela + 1)
    k = ini + int(np.argmax(corr[ini:fim]))
    trecho = residuo[k : k + len(rajada)]
    norma = np.linalg.norm(rajada) * np.linalg.norm(trecho)
    similaridade = float(abs(corr[k]) / norma) if norma > 0 else 0.0
    return k / TAXA_MIX, similaridade


def _quadros_fonte(video: str, t0: float, t1: float) -> tuple[list[float], np.ndarray]:
    """Quadros em cinza do vídeo original num trecho, com o instante de cada um.

    Args:
        video: vídeo original (somente leitura).
        t0: início do trecho, em segundos da linha do tempo do vídeo.
        t1: fim do trecho, no mesmo tempo. O recorte é um ``trim`` no filtro, antes do
            ``showinfo``, para que cada instante impresso corresponda a um quadro na saída.
            Com ``-copyts``, ``-t`` ou ``-to`` cortam mal (medido: saída vazia ou quadros a mais).

    Returns:
        ``(instantes, quadros)``: instante de cada quadro (``best_effort`` do ffmpeg, via
        ``showinfo``) e array ``[n, ALTURA_MEDIDA, LARGURA_MEDIDA]`` em ``uint8``.

    Raises:
        RuntimeError: se o ffmpeg falhar ou se o número de instantes não bater com os quadros.
    """
    proc = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-v",
            "info",
            "-copyts",
            "-ss",
            f"{t0:.6f}",
            "-i",
            video,
            "-map",
            "0:v:0",
            "-vf",
            f"trim=start={t0:.6f}:end={t1:.6f},"
            f"scale={LARGURA_MEDIDA}:{ALTURA_MEDIDA},format=gray,showinfo",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        erro = proc.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ffmpeg falhou nos quadros de {video}: {erro}")
    instantes = [
        float(m.group(1))
        for m in re.finditer(
            r"pts_time:(-?[0-9.]+)", proc.stderr.decode(errors="replace")
        )
    ]
    tam = LARGURA_MEDIDA * ALTURA_MEDIDA
    if len(proc.stdout) % tam or len(proc.stdout) // tam != len(instantes):
        raise RuntimeError(
            f"quadros ({len(proc.stdout) // tam}) e instantes ({len(instantes)}) não batem"
        )
    quadros = np.frombuffer(proc.stdout, dtype=np.uint8).reshape(
        -1, ALTURA_MEDIDA, LARGURA_MEDIDA
    )
    return instantes, quadros


def _primeiro_quadro_a_partir(video: str, t: float) -> float:
    """Instante do primeiro quadro do vídeo a partir de ``t`` (o quadro em que o clipe começa).

    Args:
        video: vídeo original (somente leitura).
        t: instante pedido, na linha do tempo do vídeo.

    Returns:
        O instante do primeiro quadro com ``pts >= t`` (dentro de um quadro de ``t``).

    Raises:
        RuntimeError: se não houver quadro a partir de ``t``.
    """
    instantes, _ = _quadros_fonte(video, t, t + 1.0)
    if not instantes:
        raise RuntimeError(f"sem quadro a partir de {t} s em {video}")
    return instantes[0]


def _erro_primeiro_quadro(
    clipe: Path, video: str, inicio: float
) -> tuple[float, float]:
    """Erro do primeiro quadro do MP4 em relação ao instante pedido, medido nos quadros.

    O primeiro quadro do MP4 é comparado (em cinza, reduzido) com os quadros do original numa
    janela em torno de ``inicio``; o de menor erro quadrático é o quadro de origem.

    Args:
        clipe: MP4 gerado.
        video: vídeo original.
        inicio: instante pedido do primeiro quadro, na linha do tempo do vídeo.

    Returns:
        ``(erro_ms, margem)``: erro em ms (quadro de origem menos ``inicio``) e a razão entre o
        segundo melhor erro quadrático e o melhor (quanto maior, mais claro o casamento).
    """
    instantes, fontes = _quadros_fonte(
        video, max(0.0, inicio - MARGEM_QUADRO_S), inicio + MARGEM_QUADRO_S + 0.2
    )
    primeiro = _ffmpeg(
        [
            "-i",
            str(clipe),
            "-frames:v",
            "1",
            "-vf",
            f"scale={LARGURA_MEDIDA}:{ALTURA_MEDIDA},format=gray",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ]
    )
    ref = np.frombuffer(primeiro, dtype=np.uint8).reshape(ALTURA_MEDIDA, LARGURA_MEDIDA)
    ref = ref.astype(np.float64)
    erros = np.array(
        [float(np.mean((f.astype(np.float64) - ref) ** 2)) for f in fontes]
    )
    ordem = np.argsort(erros)
    melhor = int(ordem[0])
    margem = (
        float(erros[ordem[1]] / max(erros[melhor], 1e-9)) if len(ordem) > 1 else 0.0
    )
    return (instantes[melhor] - inicio) * 1000.0, margem


def medir_clipe(clipe: Path, video: str, inicio: float, t_clique_rel: float) -> dict:
    """Mede, no MP4 final, o erro do primeiro quadro e do clique.

    Args:
        clipe: MP4 gerado por ``gerar_clipe``.
        video: vídeo original (somente leitura).
        inicio: instante, na linha do tempo do vídeo, do primeiro quadro do clipe.
        t_clique_rel: instante do clique esperado, em segundos a partir do início do clipe.

    Returns:
        Dicionário com ``erro_clique_ms``, ``similaridade_clique``, ``atraso_aac_ms``,
        ``pico_saida``, ``erro_quadro_ms`` e ``margem_quadro``.
    """
    saida = _audio_mono(str(clipe), None)
    original = _audio_mono(video, inicio)
    atraso = _atraso_amostras(saida, original)
    residuo = _residuo(saida, original, atraso)
    t_medido, similaridade = _achar_clique(residuo, t_clique_rel)
    erro_quadro_ms, margem = _erro_primeiro_quadro(clipe, video, inicio)
    return {
        "erro_clique_ms": round((t_medido - t_clique_rel) * 1000.0, 3),
        "similaridade_clique": round(similaridade, 4),
        "atraso_aac_ms": round(atraso / TAXA_MIX * 1000.0, 3),
        "pico_saida": round(float(np.max(np.abs(saida))), 4),
        "erro_quadro_ms": round(erro_quadro_ms, 3),
        "margem_quadro": round(margem, 2),
    }


def gerar_clipe(
    pedido: dict,
    pasta: Path,
    raiz: Path | None = None,
    raiz_acervo: str | None = None,
) -> dict:
    """Gera o MP4 de um pedido e mede o erro de quadro e de clique no arquivo final.

    Args:
        pedido: ``{id, video, t_audio, tela, coluna, x_centro_quadro, painel, passo, rotulo}``;
            ``video`` é o caminho no container.
        pasta: pasta de saída; o MP4 é ``<id>.mp4``.
        raiz: raiz do cache de áudio (``None`` usa a padrão); útil em testes.
        raiz_acervo: raiz do acervo para a chave do cache (``None`` usa ``/acervo``).

    Returns:
        O pedido com ``arquivo``, ``duracao_s``, ``tamanho_bytes``, ``quantizacao_ms`` (grade da
        amostra de áudio, em relação a ``t_audio``) e as medidas de ``medir_clipe``.

    Raises:
        ValueError: se ``t_audio`` estiver a menos de ``JANELA_S`` do início do vídeo.
    """
    video = str(pedido["video"])
    t_audio = float(pedido["t_audio"])
    inicio_pedido = t_audio - JANELA_S
    if inicio_pedido < 0:
        raise ValueError(f"{pedido['id']}: t_audio {t_audio} antes de {JANELA_S} s")
    _, meta = garantir(video, raiz=raiz, raiz_acervo=raiz_acervo)
    indice = indice_de(t_audio, meta)
    t_clique_abs = instante_de(indice, meta)
    # O clipe começa no primeiro quadro de fato (não no instante pedido): vídeo e áudio partem
    # do mesmo instante, senão o quadro destacado fica até um quadro adiantado em relação ao
    # som e ao clique. O atraso até esse quadro é reportado (``atraso_inicio_quadro_ms``).
    inicio = _primeiro_quadro_a_partir(video, inicio_pedido)
    t_clique_rel = t_clique_abs - inicio

    largura, altura, _ = _sondar_video(video)
    x, y, w, h = _caixa_destaque(
        float(pedido["x_centro_quadro"]),
        float(pedido["passo"]),
        list(pedido["painel"]),
        largura,
        altura,
    )
    largura_saida = min(LARGURA_MAX, largura)
    largura_saida -= largura_saida % 2
    saida = Path(pasta) / f"{pedido['id']}.mp4"
    filtro = (
        f"[0:v]drawbox=x={x}:y={y}:w={w}:h={h}:color=yellow:t={ESPESSURA_DESTAQUE},"
        f"scale={largura_saida}:-2[v];"
        "[0:a]aresample=48000,aformat=channel_layouts=stereo[a];"
        "[1:a]aformat=channel_layouts=stereo[c];"
        "[a][c]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[m]"
    )
    with tempfile.TemporaryDirectory(dir=Path(pasta)) as tmp:
        wav = Path(tmp) / "cliques.wav"
        _gravar_wav(wav, trilha_cliques([t_clique_rel], DURACAO_CLIPE_S))
        _ffmpeg(
            [
                "-y",
                "-ss",
                f"{inicio:.6f}",
                "-i",
                video,
                "-i",
                str(wav),
                "-t",
                f"{DURACAO_CLIPE_S:.6f}",
                "-filter_complex",
                filtro,
                "-map",
                "[v]",
                "-map",
                "[m]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(saida),
            ]
        )
    _, _, duracao = _sondar_video(str(saida))
    medidas = medir_clipe(saida, video, inicio, t_clique_rel)
    return {
        **pedido,
        "arquivo": saida.name,
        "duracao_s": round(duracao, 3),
        "tamanho_bytes": saida.stat().st_size,
        "inicio_clipe_s": round(inicio, 6),
        "atraso_inicio_quadro_ms": round((inicio - inicio_pedido) * 1000.0, 3),
        "quantizacao_ms": round((t_clique_abs - t_audio) * 1000.0, 4),
        **medidas,
    }


def _ler_pedidos(caminho: Path) -> list[dict]:
    """Lê a lista de pedidos de um arquivo JSON.

    Args:
        caminho: arquivo JSON com uma lista de pedidos.

    Returns:
        A lista de pedidos.

    Raises:
        ValueError: se o JSON não for uma lista.
    """
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(bruto, list):
        raise ValueError(f"{caminho} não tem uma lista de pedidos")
    return bruto


def _gravar_json(caminho: Path, dados: object) -> None:
    """Grava um JSON de forma atômica, criando a pasta se preciso.

    Args:
        caminho: arquivo de saída.
        dados: objeto serializável em JSON.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(f".{caminho.name}.tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporario, caminho)


def cmd_clipes(pedidos_arq: Path, pasta: Path) -> int:
    """Gera os clipes de uma lista de pedidos e o ``manifesto.json`` da pasta.

    Args:
        pedidos_arq: JSON com a lista de pedidos.
        pasta: pasta de saída.

    Returns:
        Código de saída (0 se deu certo).
    """
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto = []
    for pedido in _ler_pedidos(pedidos_arq):
        entrada = gerar_clipe(pedido, pasta)
        manifesto.append(entrada)
        print(
            f"{entrada['id']}: erro_quadro={entrada['erro_quadro_ms']} ms "
            f"erro_clique={entrada['erro_clique_ms']} ms "
            f"pico={entrada['pico_saida']} "
            f"tamanho={entrada['tamanho_bytes'] / 1e6:.2f} MB "
            f"duracao={entrada['duracao_s']} s"
        )
    _gravar_json(pasta / "manifesto.json", manifesto)
    print(f"{len(manifesto)} clipes em {pasta}")
    return 0


def _rotulo_pagina(entrada: dict) -> str:
    """Texto curto mostrado na página: vídeo, tela, coluna e as notas da coluna.

    Args:
        entrada: item do manifesto.

    Returns:
        Texto puro (sem HTML), por exemplo ``"vídeo · tela 7 · coluna 5 · corda 2 casa 4"``.
    """
    partes = [str(entrada.get("rotulo", "")).strip()]
    partes.append(f"tela {entrada['tela']}")
    partes.append(f"coluna {entrada['coluna']}")
    notas = entrada.get("notas") or []
    if notas:
        partes.append(" + ".join(f"corda {c} casa {k}" for c, k in notas))
    return " · ".join(p for p in partes if p)


def _cartoes(clipes: list[dict]) -> str:
    """Marcação de um cartão por clipe: vídeo, três respostas e campo de observação.

    Args:
        clipes: ``[{id, arquivo, rotulo}]`` na ordem da página.

    Returns:
        HTML dos cartões, com o texto de cada rótulo escapado.
    """
    blocos = []
    for i, clipe in enumerate(clipes, start=1):
        titulo = html.escape(f"{i} de {len(clipes)} · {clipe['rotulo']}")
        arquivo = html.escape(clipe["arquivo"], quote=True)
        blocos.append(
            f'<section class="clipe" id="clipe-{i - 1}">\n'
            f"  <h2>{titulo}</h2>\n"
            f'  <video controls preload="metadata" src="{arquivo}"></video>\n'
            '  <div class="botoes">\n'
            '    <button type="button" data-resposta="certo">certo (1)</button>\n'
            '    <button type="button" data-resposta="errado">errado (2)</button>\n'
            '    <button type="button" data-resposta="nao_sei">não sei (3)</button>\n'
            "  </div>\n"
            '  <input type="text" data-obs="1" placeholder="observação (opcional)">\n'
            "</section>"
        )
    return "\n".join(blocos)


def gerar_pagina(pasta: Path) -> Path:
    """Gera o ``index.html`` estático da folha a partir do ``manifesto.json``.

    Args:
        pasta: pasta com o manifesto e os MP4.

    Returns:
        O caminho do ``index.html`` gerado.

    Raises:
        FileNotFoundError: se não houver ``manifesto.json`` na pasta.
    """
    manifesto = json.loads((pasta / "manifesto.json").read_text(encoding="utf-8"))
    nome = pasta.name
    clipes = [
        {"id": e["id"], "arquivo": e["arquivo"], "rotulo": _rotulo_pagina(e)}
        for e in manifesto
    ]
    dados = json.dumps(clipes, ensure_ascii=False).replace("</", "<\\/")
    pagina = (
        _MODELO_HTML.replace("__TITULO__", html.escape(f"Folha: {nome}"))
        .replace("__CARTOES__", _cartoes(clipes))
        .replace("__NOME_JS__", json.dumps(nome, ensure_ascii=False))
        .replace("__DADOS__", dados)
    )
    destino = pasta / "index.html"
    destino.write_text(pagina, encoding="utf-8")
    return destino


def ler_alinhados(caminhos: list[str]) -> list[dict]:
    """Lê os itens do alinhador de um ou mais arquivos JSON.

    Formato provisório, isolado aqui para ser adaptado ao formato real do alinhador: cada arquivo
    é uma lista de itens, ou um objeto com a chave ``itens``. Cada item traz ao menos
    ``video`` (caminho no container), ``tela``, ``exibicao``, ``coluna``, ``t_audio`` (ou
    ``null``) e ``confianca``.

    Args:
        caminhos: arquivos JSON do alinhador.

    Returns:
        Todos os itens, na ordem dos arquivos.

    Raises:
        ValueError: se um arquivo não tiver nenhum dos dois formatos.
    """
    itens: list[dict] = []
    for caminho in caminhos:
        bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
        if isinstance(bruto, dict) and "itens" in bruto:
            bruto = bruto["itens"]
        if not isinstance(bruto, list):
            raise ValueError(f"{caminho}: formato de alinhamento não reconhecido")
        itens.extend(bruto)
    return itens


def _relativo_ao_acervo(video: str) -> str:
    """Caminho relativo ao acervo de um caminho no container.

    Args:
        video: caminho no container, começando por ``/acervo/``.

    Returns:
        O caminho sem o prefixo do acervo.

    Raises:
        ValueError: se o caminho não estiver no acervo.
    """
    if not video.startswith(PREFIXO_ACERVO):
        raise ValueError(f"{video} não está em {PREFIXO_ACERVO}")
    return video[len(PREFIXO_ACERVO) :]


def carregar_produtos(pasta: Path) -> dict[str, dict]:
    """Produtos ``tab.video`` de uma pasta, indexados pelo caminho relativo do vídeo.

    Args:
        pasta: pasta com os JSON de produto.

    Returns:
        ``{video_relativo: produto}``; arquivos que não são produto são ignorados.
    """
    produtos: dict[str, dict] = {}
    for arq in sorted(pasta.glob("*.json")):
        try:
            prod = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(prod, dict) and "video" in prod and "telas" in prod:
            produtos[prod["video"]["arquivo"]] = prod
    return produtos


def _pedido_do_item(item: dict, produto: dict, numero: int) -> dict:
    """Pedido de clipe a partir de um item do alinhador e do produto do vídeo.

    Args:
        item: item do alinhador (``video``, ``tela``, ``exibicao``, ``coluna``, ``t_audio``).
        produto: produto ``tab.video`` do vídeo.
        numero: número sequencial do pedido, usado no ``id``.

    Returns:
        O pedido com ``id``, ``video``, ``t_audio``, ``tela``, ``coluna``, ``exibicao``,
        ``x_centro_quadro`` (média das notas da coluna), ``painel``, ``passo``, ``rotulo``
        e ``notas`` (``[corda, casa]``).

    Raises:
        ValueError: se a tela ou as notas da coluna não estiverem no produto.
    """
    tela = next(t for t in produto["telas"] if t["id"] == item["tela"])
    notas = [
        n
        for n in produto["notas"]
        if n["tela"] == item["tela"]
        and n["coluna"] == item["coluna"]
        and n.get("exibicao") in (None, item["exibicao"])
    ]
    if not notas:
        raise ValueError(f"sem notas na tela {item['tela']} coluna {item['coluna']}")
    x_centro = sum(float(n["x_centro_quadro"]) for n in notas) / len(notas)
    notas_ord = sorted(([n["corda"], n["casa"]] for n in notas), key=lambda p: p[0])
    rotulo = os.path.splitext(os.path.basename(produto["video"]["arquivo"]))[0]
    return {
        "id": f"p{numero:03d}",
        "video": item["video"],
        "t_audio": float(item["t_audio"]),
        "tela": item["tela"],
        "coluna": item["coluna"],
        "exibicao": item["exibicao"],
        "x_centro_quadro": round(x_centro, 2),
        "painel": tela["painel"],
        "passo": tela["passo"],
        "rotulo": rotulo,
        "notas": notas_ord,
    }


def sortear_pedidos(
    itens: list[dict], produtos: dict[str, dict], por_video: int, semente: int
) -> list[dict]:
    """Sorteia K colunas por vídeo, estratificadas pelas exibições, com semente fixa.

    Só entram itens com ``t_audio`` não nulo. Dentro de cada vídeo, as exibições são
    percorridas em ordem sorteada, e de cada uma sai uma coluna por rodada.

    Args:
        itens: itens do alinhador (ver ``ler_alinhados``).
        produtos: ``{video_relativo: produto}`` (ver ``carregar_produtos``).
        por_video: número de colunas sorteadas por vídeo.
        semente: semente do sorteio.

    Returns:
        A lista de pedidos (ver ``_pedido_do_item``), vídeo a vídeo, em ordem de caminho.

    Raises:
        ValueError: se um vídeo dos itens não tiver produto na pasta de produtos.
    """
    rng = random.Random(semente)
    videos = sorted({it["video"] for it in itens})
    pedidos: list[dict] = []
    for video in videos:
        rel = _relativo_ao_acervo(video)
        if rel not in produtos:
            raise ValueError(f"sem produto para {video} (rode tab.video antes)")
        grupos: dict[object, list[dict]] = {}
        for it in itens:
            if it["video"] == video and it.get("t_audio") is not None:
                grupos.setdefault(it["exibicao"], []).append(it)
        ordem = sorted(grupos)
        rng.shuffle(ordem)
        for lista in grupos.values():
            lista.sort(key=lambda it: (it["tela"], it["coluna"]))
        escolhidos: list[dict] = []
        k = 0
        while len(escolhidos) < por_video and any(grupos.values()):
            exib = ordem[k % len(ordem)]
            k += 1
            if grupos[exib]:
                sorteado = grupos[exib].pop(rng.randrange(len(grupos[exib])))
                escolhidos.append(sorteado)
        for item in escolhidos:
            pedidos.append(_pedido_do_item(item, produtos[rel], len(pedidos) + 1))
    return pedidos


def cmd_sortear(
    alinhados: list[str], por_video: int, semente: int, saida: Path, produtos: Path
) -> int:
    """Sorteia os pedidos a partir dos alinhamentos e grava o JSON de pedidos.

    Args:
        alinhados: arquivos JSON do alinhador.
        por_video: colunas sorteadas por vídeo.
        semente: semente do sorteio.
        saida: JSON de pedidos de saída.
        produtos: pasta com os produtos ``tab.video``.

    Returns:
        Código de saída (0 se deu certo).
    """
    itens = ler_alinhados(alinhados)
    pedidos = sortear_pedidos(itens, carregar_produtos(produtos), por_video, semente)
    _gravar_json(saida, pedidos)
    print(f"{len(pedidos)} pedidos em {saida}")
    return 0


def main() -> int:
    """Ponto de entrada da CLI: subcomandos ``clipes``, ``pagina`` e ``sortear``.

    Returns:
        Código de saída (0 se deu certo).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)

    p_clipes = sub.add_parser("clipes", help="gera os MP4 dos pedidos")
    p_clipes.add_argument("--pedidos", type=Path, required=True)
    p_clipes.add_argument("--pasta", type=Path, required=True)

    p_pagina = sub.add_parser("pagina", help="gera o index.html da pasta")
    p_pagina.add_argument("--pasta", type=Path, required=True)

    p_sortear = sub.add_parser("sortear", help="sorteia colunas dos alinhamentos")
    p_sortear.add_argument("--alinhados", nargs="+", required=True)
    p_sortear.add_argument("--por-video", type=int, required=True)
    p_sortear.add_argument("--semente", type=int, required=True)
    p_sortear.add_argument("--saida", type=Path, required=True)
    p_sortear.add_argument("--produtos", type=Path, default=PASTA_PRODUTOS)

    args = parser.parse_args()
    if args.comando == "clipes":
        return cmd_clipes(args.pedidos, args.pasta)
    if args.comando == "pagina":
        destino = gerar_pagina(args.pasta)
        print(f"página gerada: {destino}")
        return 0
    return cmd_sortear(
        args.alinhados, args.por_video, args.semente, args.saida, args.produtos
    )


if __name__ == "__main__":
    sys.exit(main())
