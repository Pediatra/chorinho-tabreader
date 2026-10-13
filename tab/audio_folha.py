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

    python -m tab.audio_folha clipes --pedidos PEDIDOS.json --pasta PASTA [--manifesto M.json]
    python -m tab.audio_folha pagina --pasta PASTA [--manifesto M.json]
    python -m tab.audio_folha sortear --alinhado ALINHADO1.json PRODUTO1.json \\
        [ALINHADO2.json PRODUTO2.json ...] --por-video K --semente S --saida PEDIDOS.json

O ``--manifesto`` deixa o manifesto FORA da pasta servida (a página só deve ter index.html e
os MP4). ``sortear`` recebe pares: a saída de ``tab.audio_alinhar`` (traz o vídeo) e o
produto ``tab.video`` do mesmo vídeo (traz painel, passo e notas).
"""

import argparse
import html
import itertools
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import wave
from collections import Counter
from pathlib import Path

import numpy as np

from .audio_extrair import garantir, indice_de, instante_de, ler
from .audio_onsets import espectrograma, fluxo_espectral, picos

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

#: Ganho do áudio original na mistura (0,5 = -6 dB). Com 1,0 o pico decodificado passava de 1
#: (saturação) em clipes com música forte + clique. Vale na mistura e na medição.
GANHO_MUSICA = 0.5

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
    __AVISO__
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
    original = _audio_mono(video, inicio) * GANHO_MUSICA
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


def _renderizar_clipe(
    video: str,
    inicio: float,
    t_clique_rel: float,
    x_centro: float,
    passo: float,
    painel: list[int],
    saida: Path,
) -> None:
    """Renderiza um MP4 de ``DURACAO_CLIPE_S`` a partir de ``inicio``.

    O quadro tem a coluna destacada por um retângulo amarelo (``_caixa_destaque``) e o áudio
    original a ``GANHO_MUSICA`` mais um clique de 10 ms em ``t_clique_rel`` (segundos a partir
    de ``inicio``). Vídeo e áudio partem do mesmo instante; quem escolhe ``inicio`` decide a
    janela.

    Args:
        video: vídeo no container (somente leitura).
        inicio: instante, na linha do tempo do vídeo, do primeiro quadro do clipe.
        t_clique_rel: instante do clique dentro do clipe, em segundos.
        x_centro: ``x_centro_quadro`` médio da coluna.
        passo: distância entre cordas, em px.
        painel: ``[x0, y0, x1, y1]`` da tablatura no quadro.
        saida: MP4 de saída; o temporário fica na mesma pasta e é removido.
    """
    largura, altura, _ = _sondar_video(video)
    x, y, w, h = _caixa_destaque(x_centro, passo, painel, largura, altura)
    largura_saida = min(LARGURA_MAX, largura)
    largura_saida -= largura_saida % 2
    filtro = (
        f"[0:v]drawbox=x={x}:y={y}:w={w}:h={h}:color=yellow:t={ESPESSURA_DESTAQUE},"
        f"scale={largura_saida}:-2[v];"
        f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={GANHO_MUSICA}[a];"
        "[1:a]aformat=channel_layouts=stereo[c];"
        "[a][c]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[m]"
    )
    with tempfile.TemporaryDirectory(dir=saida.parent) as tmp:
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

    saida = Path(pasta) / f"{pedido['id']}.mp4"
    _renderizar_clipe(
        video,
        inicio,
        t_clique_rel,
        float(pedido["x_centro_quadro"]),
        float(pedido["passo"]),
        list(pedido["painel"]),
        saida,
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


def cmd_clipes(pedidos_arq: Path, pasta: Path, manifesto_arq: Path | None) -> int:
    """Gera os clipes de uma lista de pedidos e grava o manifesto.

    Args:
        pedidos_arq: JSON com a lista de pedidos.
        pasta: pasta de saída (os MP4 vão para cá).
        manifesto_arq: onde gravar o manifesto; ``None`` grava ``pasta/manifesto.json``.
            Para folha servida por HTTP, use um caminho FORA da pasta servida.

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
    _gravar_json(manifesto_arq or pasta / "manifesto.json", manifesto)
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


def gerar_pagina(
    pasta: Path, manifesto_arq: Path | None = None, aviso: str = ""
) -> Path:
    """Gera o ``index.html`` estático da folha a partir do manifesto.

    Args:
        pasta: pasta onde o ``index.html`` é gravado e onde estão os MP4.
        manifesto_arq: manifesto; ``None`` usa ``pasta/manifesto.json``.
        aviso: texto extra mostrado abaixo das instruções (vazio não mostra nada).

    Returns:
        O caminho do ``index.html`` gerado.

    Raises:
        FileNotFoundError: se não houver ``manifesto.json`` na pasta.
    """
    arq = manifesto_arq or pasta / "manifesto.json"
    manifesto = json.loads(arq.read_text(encoding="utf-8"))
    nome = pasta.name
    clipes = [
        {"id": e["id"], "arquivo": e["arquivo"], "rotulo": _rotulo_pagina(e)}
        for e in manifesto
    ]
    dados = json.dumps(clipes, ensure_ascii=False).replace("</", "<\\/")
    pagina = (
        _MODELO_HTML.replace("__TITULO__", html.escape(f"Folha: {nome}"))
        .replace("__CARTOES__", _cartoes(clipes))
        .replace(
            "__AVISO__",
            f'<p class="ajuda">{html.escape(aviso)}</p>' if aviso else "",
        )
        .replace("__NOME_JS__", json.dumps(nome, ensure_ascii=False))
        .replace("__DADOS__", dados)
    )
    destino = pasta / "index.html"
    destino.write_text(pagina, encoding="utf-8")
    return destino


def ler_alinhamento(caminho: str) -> dict:
    """Lê um JSON de saída do ``tab.audio_alinhar``.

    Args:
        caminho: JSON de saída do alinhador.

    Returns:
        O dicionário lido, com ``video``, ``exibicoes`` e ``colunas``.

    Raises:
        ValueError: se faltar alguma dessas chaves (o arquivo não é do alinhador).
    """
    bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    for chave in ("video", "exibicoes", "colunas"):
        if chave not in bruto:
            raise ValueError(f"{caminho}: falta '{chave}' (não é saída do alinhador)")
    return bruto


def itens_afirmados(alinhamento: dict) -> list[dict]:
    """Colunas afirmadas pelo alinhador, de exibições não recusadas.

    Uma coluna entra se tem ``t_audio`` e a exibição não foi recusada inteira. O ``T_usado_s``
    da exibição vem junto, para o controle de +0,5 período.

    Args:
        alinhamento: JSON de ``ler_alinhamento``.

    Returns:
        Itens ``{video, tela, exibicao, coluna, t_audio, confianca, cos, T_usado_s}``.
    """
    video = alinhamento["video"]["arquivo"]
    exibicoes = {(e["tela"], e["exibicao"]): e for e in alinhamento["exibicoes"]}
    itens = []
    for c in alinhamento["colunas"]:
        ex = exibicoes[(c["tela"], c["exibicao"])]
        if c["t_audio"] is None or ex["recusada_exibicao"]:
            continue
        itens.append(
            {
                "video": video,
                "tela": c["tela"],
                "exibicao": c["exibicao"],
                "coluna": c["coluna"],
                "t_audio": c["t_audio"],
                "confianca": c["confianca"],
                "cos": c["cos"],
                "T_usado_s": ex.get("T_usado_s"),
            }
        )
    return itens


def ler_pares(pares: list[str]) -> tuple[list[dict], dict[str, dict]]:
    """Lê os pares ``ALINHADO PRODUTO`` (um par por vídeo).

    Formato escolhido: o alinhamento já traz o vídeo (``video.arquivo``, caminho no container),
    e o produto ``tab.video`` traz painel, passo e notas. O par liga os dois. O produto precisa
    ser do mesmo vídeo (conferido).

    Args:
        pares: caminhos alternados, ``[ALINHADO1, PRODUTO1, ALINHADO2, PRODUTO2, ...]``.

    Returns:
        ``(itens, produtos)``: itens de ``itens_afirmados`` de todos os pares, e os produtos
        indexados pelo caminho do vídeo no container.

    Raises:
        ValueError: se o número de caminhos for ímpar ou se um produto não for do vídeo.
    """
    if len(pares) % 2:
        raise ValueError(
            "--alinhado recebe pares ALINHADO PRODUTO (número par de caminhos)"
        )
    itens: list[dict] = []
    produtos: dict[str, dict] = {}
    for alin_arq, prod_arq in zip(pares[::2], pares[1::2], strict=True):
        alin = ler_alinhamento(alin_arq)
        prod = json.loads(Path(prod_arq).read_text(encoding="utf-8"))
        video = alin["video"]["arquivo"]
        if video != PREFIXO_ACERVO + prod["video"]["arquivo"]:
            raise ValueError(f"{prod_arq} não é o produto de {video}")
        produtos[video] = prod
        itens.extend(itens_afirmados(alin))
    return itens, produtos


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


def _pedido_do_item(item: dict, produto: dict, numero: int) -> dict:
    """Pedido de clipe a partir de um item afirmado e do produto do vídeo.

    Args:
        item: item de ``itens_afirmados`` (``video``, ``tela``, ``exibicao``, ``coluna``,
            ``t_audio``).
        produto: produto ``tab.video`` do vídeo.
        numero: número sequencial do pedido, usado no ``id``.

    Returns:
        O pedido com ``id``, ``video``, ``t_audio``, ``tela``, ``coluna``, ``exibicao``,
        ``x_centro_quadro`` (média das notas da coluna), ``painel``, ``passo``, ``rotulo``
        e ``notas`` (``[corda, casa]``). Nota com ``exibicao`` null vale para qualquer exibição
        (é o caso de todos os produtos sem marcador); se a exibição não tem nota na coluna,
        usa as notas da coluna em qualquer exibição.

    Raises:
        ValueError: se a tela ou as notas da coluna não estiverem no produto.
    """
    tela = next(t for t in produto["telas"] if t["id"] == item["tela"])
    da_coluna = [
        n
        for n in produto["notas"]
        if n["tela"] == item["tela"] and n["coluna"] == item["coluna"]
    ]
    # O alinhador usa a união das colunas da tela em toda exibição: se a exibição do item
    # não tem nota nessa coluna (ex.: MVP, tela 9 coluna 9), vale o conjunto da coluna.
    notas = [n for n in da_coluna if n.get("exibicao") in (None, item["exibicao"])]
    if not notas:
        notas = da_coluna
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

    Dentro de cada vídeo, as exibições são percorridas em ordem sorteada, e de cada uma sai
    uma coluna por rodada, até K.

    Args:
        itens: itens de ``itens_afirmados``.
        produtos: produtos indexados pelo caminho do vídeo no container (``ler_pares``).
        por_video: número de colunas sorteadas por vídeo.
        semente: semente do sorteio.

    Returns:
        Lista de pedidos (ver ``_pedido_do_item``), vídeo a vídeo, em ordem de caminho.

    Raises:
        ValueError: se um vídeo dos itens não tiver produto.
    """
    rng = random.Random(semente)
    pedidos: list[dict] = []
    for video in sorted({it["video"] for it in itens}):
        if video not in produtos:
            raise ValueError(f"sem produto para {video}")
        grupos: dict[object, list[dict]] = {}
        for it in itens:
            if it["video"] == video:
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
            pedidos.append(_pedido_do_item(item, produtos[video], len(pedidos) + 1))
    return pedidos


#: Intervalo mínimo, em s, entre a coluna c e a c+1 para o controle da folha 2.
INTERVALO_MIN_CONTROLE_S = 0.40

#: Distância mínima, em s, do clique de controle ao pico de fluxo mais próximo.
DISTANCIA_MIN_PICO_S = 0.080

#: Margem, em s, de cada lado do par (c, c+1) ao calcular os picos de fluxo.
MARGEM_PICOS_S = 0.5


def carregar_audio(
    video: str, raiz: Path | None = None, raiz_acervo: str | None = None
) -> tuple[np.ndarray, int, float]:
    """Áudio de um vídeo (cache do A0) para o espectrograma.

    Args:
        video: vídeo no container.
        raiz: raiz do cache de áudio (``None`` usa a padrão).
        raiz_acervo: raiz do acervo (``None`` usa ``/acervo``).

    Returns:
        ``(amostras int16 mono, taxa, t_amostra0)``.
    """
    flac, meta = garantir(video, raiz=raiz, raiz_acervo=raiz_acervo)
    amostras, taxa = ler(flac)
    return amostras, taxa, float(meta["t_amostra0"])


def picos_de_fluxo(
    amostras: np.ndarray, taxa: int, t_amostra0: float, t0: float, t1: float
) -> np.ndarray:
    """Instantes dos picos do fluxo espectral (``tab.audio_onsets``) em ``[t0, t1]``.

    Args:
        amostras: áudio ``int16`` mono de ``carregar_audio``.
        taxa: taxa do áudio, em Hz.
        t_amostra0: instante, no vídeo, da amostra 0.
        t0: início da janela, em segundos do vídeo.
        t1: fim da janela, em segundos do vídeo.

    Returns:
        Array de instantes (s, linha do tempo do vídeo), em ordem crescente.
    """
    mag, tempos, _ = espectrograma(amostras, taxa, t_amostra0, t0=t0, t1=t1)
    if len(tempos) < 3:
        return np.zeros(0)
    fluxo = fluxo_espectral(mag)
    return tempos[np.asarray(picos(fluxo, tempos), dtype=int)]


def pares_vizinhos_validos(colunas: list[dict]) -> list[tuple[dict, dict]]:
    """Pares (c, c+1) de uma exibição que servem de controle.

    Regra: as duas colunas são consecutivas na tela (c+1 logo depois de c, sem coluna entre
    elas), ambas têm ``t_audio`` (nenhuma recusada entre elas) e ``t(c+1) - t(c) >=
    INTERVALO_MIN_CONTROLE_S``. A verificação é local (vizinhos na lista), não precisa de
    programação dinâmica.

    Args:
        colunas: registros ``{coluna, t_audio, ...}`` de UMA exibição, em ordem de coluna.

    Returns:
        Pares ``(a, b)`` na ordem da tela.
    """
    pares = []
    for a, b in itertools.pairwise(colunas):
        if a["t_audio"] is None or b["t_audio"] is None:
            continue
        if b["coluna"] - a["coluna"] != 1:
            continue
        if b["t_audio"] - a["t_audio"] < INTERVALO_MIN_CONTROLE_S:
            continue
        pares.append((a, b))
    return pares


def distancia_ao_pico(instante: float, picos_t: np.ndarray) -> float:
    """Distância, em s, do instante ao pico de fluxo mais próximo (``inf`` sem picos).

    Args:
        instante: instante, em segundos.
        picos_t: instantes dos picos.

    Returns:
        ``min |instante - pico|``.
    """
    if len(picos_t) == 0:
        return float("inf")
    return float(np.min(np.abs(np.asarray(picos_t) - instante)))


def escolher_controle(
    pares: list[tuple[dict, dict]],
    audio: tuple[np.ndarray, int, float],
    rng: random.Random,
    proibidas: set[tuple[int, int]],
) -> dict | None:
    """Primeiro par (em ordem sorteada) cujo clique no ponto médio não cai perto de um pico.

    O clique fica em ``(t(c) + t(c+1)) / 2``. O par é aceito se nenhum pico de fluxo estiver a
    menos de ``DISTANCIA_MIN_PICO_S`` do clique. A janela de picos é o par com
    ``MARGEM_PICOS_S`` de cada lado.

    Args:
        pares: pares de ``pares_vizinhos_validos``, de vários candidatos.
        audio: ``carregar_audio`` do vídeo do controle.
        rng: gerador da folha (define a ordem de tentativa).
        proibidas: pares ``(tela, coluna)`` que não podem ser usados (já na folha).

    Returns:
        ``{a, b, clique, distancia_pico_s}`` ou ``None`` se nenhum par servir.
    """
    amostras, taxa, t0_amostra = audio
    ordem = list(range(len(pares)))
    rng.shuffle(ordem)
    for i in ordem:
        a, b = pares[i]
        if (a["tela"], a["coluna"]) in proibidas or (
            b["tela"],
            b["coluna"],
        ) in proibidas:
            continue
        clique = (a["t_audio"] + b["t_audio"]) / 2.0
        janela = picos_de_fluxo(
            amostras,
            taxa,
            t0_amostra,
            a["t_audio"] - MARGEM_PICOS_S,
            b["t_audio"] + MARGEM_PICOS_S,
        )
        dist = distancia_ao_pico(clique, janela)
        if dist >= DISTANCIA_MIN_PICO_S:
            return {"a": a, "b": b, "clique": clique, "distancia_pico_s": dist}
    return None


def sortear_espalhado(itens: list[dict], k: int, rng: random.Random) -> list[dict]:
    """K itens espalhados pelo vídeo: uma coluna sorteada por faixa de tempo.

    O intervalo de ``t_audio`` dos itens é dividido em ``k`` faixas de mesmo tamanho; de cada
    faixa sai uma coluna sorteada (com ``rng``). Como as exibições ocupam faixas diferentes do
    vídeo, o sorteio cobre o vídeo inteiro. Se uma faixa está vazia, usa-se o item não usado
    mais próximo do centro dela.

    Args:
        itens: itens de ``itens_afirmados`` (já filtrados).
        k: quantidade de itens.
        rng: gerador da folha.

    Returns:
        Até ``k`` itens distintos, em ordem de tempo.
    """
    if not itens or k <= 0:
        return []
    tempos = [it["t_audio"] for it in itens]
    t_min, t_max = min(tempos), max(tempos)
    passo = (t_max - t_min) / k if t_max > t_min else 1.0
    restantes = sorted(itens, key=lambda it: it["t_audio"])
    escolhidos: list[dict] = []
    for j in range(k):
        ini = t_min + j * passo
        fim_faixa = t_min + (j + 1) * passo
        centro = (ini + fim_faixa) / 2.0
        faixa = [
            it
            for it in restantes
            if ini <= it["t_audio"] < fim_faixa
            or (j == k - 1 and it["t_audio"] == t_max)
        ]
        if faixa:
            escolhido = faixa[rng.randrange(len(faixa))]
        elif restantes:
            escolhido = min(restantes, key=lambda it: abs(it["t_audio"] - centro))
        else:
            break
        restantes.remove(escolhido)
        escolhidos.append(escolhido)
    return escolhidos


def cmd_sortear(pares: list[str], por_video: int, semente: int, saida: Path) -> int:
    """Sorteia os pedidos a partir dos pares alinhamento/produto e grava o JSON.

    Args:
        pares: ver ``ler_pares``.
        por_video: colunas sorteadas por vídeo.
        semente: semente do sorteio.
        saida: JSON de pedidos de saída.

    Returns:
        Código de saída (0 se deu certo).
    """
    itens, produtos = ler_pares(pares)
    pedidos = sortear_pedidos(itens, produtos, por_video, semente)
    _gravar_json(saida, pedidos)
    print(f"{len(pedidos)} pedidos em {saida}")
    return 0


#: Deslocamentos, em ms, do clique de comparação (6 pares cada, 36 ao todo).
D_MS = (-200, -100, -50, 50, 100, 200)

#: Deslocamentos de atenção (resposta óbvia), 2 de cada sinal.
D_ATENCAO_MS = (-400, -400, 400, 400)

#: Gabarito que não entra na comparação: leitura "coluna errada" (ritornelo), confirmada.
IDS_EXCLUIDOS_COMPARACAO = frozenset({"f13"})

#: Modelo da página de comparação A/B. ``__LINHAS__`` e ``__DADOS__`` são trocados.
_MODELO_COMPARACAO = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Folha 3: comparação A/B</title>
<style>
:root { --fundo: #f7f6f3; --texto: #1d1d1b; --borda: #d6d3cb; --cartao: #ffffff;
  --ativo: #d9a400; --escolha: #2f6f9a; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --fundo: #1b1c1e; --texto: #eceae4;
    --borda: #3a3c40; --cartao: #25262a; }
}
:root[data-theme="dark"] { --fundo: #1b1c1e; --texto: #eceae4; --borda: #3a3c40;
  --cartao: #25262a; }
body { margin: 0; background: var(--fundo); color: var(--texto);
  font: 16px/1.45 system-ui, sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 16px; }
header { position: sticky; top: 0; background: var(--fundo); padding: 8px 0 12px;
  border-bottom: 1px solid var(--borda); z-index: 1; }
h1 { font-size: 20px; margin: 0 0 6px; }
.ajuda { margin: 0; font-size: 15px; }
#contador { font-weight: 600; margin: 6px 0 0; }
.linha { background: var(--cartao); border: 2px solid var(--borda); border-radius: 8px;
  padding: 12px; margin: 16px 0; }
.linha.ativa { border-color: var(--ativo); }
.linha h2 { font-size: 15px; margin: 0 0 8px; font-weight: 600; }
.videos { display: flex; gap: 12px; flex-wrap: wrap; }
.videos figure { flex: 1 1 320px; margin: 0; }
.videos figcaption { font-weight: 600; margin-bottom: 4px; }
video { width: 100%; background: #000; border-radius: 4px; }
.botoes { display: flex; gap: 8px; margin: 10px 0; flex-wrap: wrap; }
button { font: inherit; padding: 10px 16px; border-radius: 6px; cursor: pointer;
  border: 2px solid var(--borda); background: transparent; color: var(--texto); }
button[aria-pressed="true"] { background: var(--escolha); border-color: var(--escolha);
  color: #fff; }
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
    <h1>Folha 3: comparação A/B</h1>
    <p class="ajuda">Cada linha tem dois vídeos do mesmo trecho. Só muda o instante do clique.
      Em qual dos dois o clique cai mais junto com o começo das notas da caixa amarela?
      1 = A, 2 = B, 3 = não sei. Ignore o traço azul.</p>
    <p id="contador"></p>
  </main>
</header>
<main id="lista">__LINHAS__</main>
<main id="exportar">
  <button type="button" id="copiar">copiar respostas</button>
  <span id="status"></span>
  <textarea id="saida" rows="8" readonly></textarea>
</main>
<script>
(function () {
  "use strict";
  var LINHAS = __DADOS__;
  var CHAVE = "chorinho-folha3";
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
    return (estado[LINHAS[i].id] || {}).resposta || null;
  }

  function primeiroPendente() {
    for (var i = 0; i < LINHAS.length; i++) {
      if (!respostaDe(i)) return i;
    }
    return 0;
  }

  function marcar(i) {
    if (i < 0 || i >= LINHAS.length) return;
    var antiga = document.querySelector(".linha.ativa");
    if (antiga) antiga.classList.remove("ativa");
    atual = i;
    document.getElementById("linha-" + i).classList.add("ativa");
  }

  function atualizarBotoes(i) {
    var secao = document.getElementById("linha-" + i);
    var resposta = respostaDe(i);
    secao.querySelectorAll("button[data-resposta]").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-resposta") === resposta ? "true" : "false");
    });
  }

  function atualizarContador() {
    var feitos = 0;
    for (var i = 0; i < LINHAS.length; i++) {
      if (respostaDe(i)) feitos++;
    }
    contador.textContent = feitos + " de " + LINHAS.length + " respondidos";
  }

  function atualizarSaida() {
    var respostas = LINHAS.map(function (l) {
      var e = estado[l.id] || {};
      return { id: l.id, resposta: e.resposta || null, obs: e.obs || "" };
    });
    saida.value = JSON.stringify({ folha: "folha3", respostas: respostas }, null, 2);
  }

  function responder(i, resposta) {
    var id = LINHAS[i].id;
    var e = estado[id] || {};
    e.resposta = resposta;
    estado[id] = e;
    gravar();
    atualizarBotoes(i);
    atualizarContador();
    atualizarSaida();
    if (i + 1 < LINHAS.length) {
      marcar(i + 1);
      document.getElementById("linha-" + (i + 1)).scrollIntoView({ block: "center" });
    }
  }

  function ligar() {
    LINHAS.forEach(function (l, i) {
      var secao = document.getElementById("linha-" + i);
      secao.querySelectorAll("button[data-resposta]").forEach(function (b) {
        b.addEventListener("click", function () {
          responder(i, b.getAttribute("data-resposta"));
        });
      });
      var obs = secao.querySelector("input[data-obs]");
      obs.value = (estado[l.id] || {}).obs || "";
      obs.addEventListener("input", function () {
        var e = estado[l.id] || {};
        e.obs = obs.value;
        estado[l.id] = e;
        gravar();
        atualizarSaida();
      });
      obs.addEventListener("focus", function () {
        marcar(i);
      });
      secao.addEventListener("click", function () {
        marcar(i);
      }, true);
    });
  }

  document.addEventListener("keydown", function (ev) {
    var alvo = ev.target;
    if (alvo && (alvo.tagName === "INPUT" || alvo.tagName === "TEXTAREA")) return;
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === "1") responder(atual, "A");
    else if (ev.key === "2") responder(atual, "B");
    else if (ev.key === "3") responder(atual, "nao_sei");
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

  ligar();
  LINHAS.forEach(function (l, i) {
    atualizarBotoes(i);
  });
  atualizarContador();
  atualizarSaida();
  marcar(atual);
})();
</script>
</body>
</html>
"""


def elegiveis_comparacao(golds: list[dict], pedidos: dict[str, dict]) -> list[dict]:
    """Itens do gabarito que servem de base à comparação A/B.

    Entram os itens com ``resposta_dono == "certo"`` e ``controle == false``, exceto os de
    ``IDS_EXCLUIDOS_COMPARACAO``. O instante do alinhador é o ``t_clique`` do item, que tem de
    coincidir com o ``t_audio`` do pedido (conferido). A caixa (painel, passo, notas) vem do
    pedido, para sair igual à das folhas 1 e 2.

    Args:
        golds: itens dos gabaritos (``data/gold/audio/folha*.json``).
        pedidos: pedidos das folhas, indexados pelo ``id`` (``folha1_pedidos.json``,
            ``folha2_pedidos.json``).

    Returns:
        Itens com ``item_gold``, ``video``, ``tela``, ``exibicao``, ``coluna``,
        ``t_alinhador``, ``painel``, ``passo``, ``x_centro_quadro`` e ``rotulo``.

    Raises:
        ValueError: se um item certo não tem pedido correspondente, ou se o instante não bate.
    """
    elegiveis = []
    for g in golds:
        if g["resposta_dono"] != "certo" or g["controle"]:
            continue
        if g["id"] in IDS_EXCLUIDOS_COMPARACAO:
            continue
        ped = pedidos.get(g["id"])
        if ped is None:
            raise ValueError(f"{g['id']}: sem pedido correspondente")
        if abs(float(ped["t_audio"]) - float(g["t_clique"])) > 1e-5:
            raise ValueError(f"{g['id']}: t_clique do gabarito não bate com o pedido")
        elegiveis.append(
            {
                "item_gold": g["id"],
                "video": ped["video"],
                "tela": ped["tela"],
                "exibicao": ped["exibicao"],
                "coluna": ped["coluna"],
                "t_alinhador": float(g["t_clique"]),
                "painel": list(ped["painel"]),
                "passo": float(ped["passo"]),
                "x_centro_quadro": float(ped["x_centro_quadro"]),
                "rotulo": ped["rotulo"],
            }
        )
    return elegiveis


def planejar_comparacao(
    elegiveis: list[dict], semente: int, por_d: int = 6
) -> list[dict]:
    """Sorteia os pares da comparação: itens, deslocamento e posição do alinhador.

    Embaralha os elegíveis com ``Random(semente)``. Os primeiros ``len(D_MS) * por_d`` viram
    os pares principais: ordenados por vídeo e distribuídos em ciclo sobre os ``D_MS``, de modo
    que cada vídeo apareça em vários deslocamentos. Os pares de atenção (``D_ATENCAO_MS``)
    usam os itens que sobraram, e reusam itens principais se faltar. Por fim, a ordem é
    embaralhada e metade dos pares tem o alinhador em A.

    Args:
        elegiveis: saída de ``elegiveis_comparacao``.
        semente: semente do sorteio (2003 na folha 3).
        por_d: pares principais por deslocamento.

    Returns:
        Lista de pares com ``id`` (p01..), ``d_ms``, ``atencao`` e ``alinhador_e`` (``"A"`` ou
        ``"B"``), mais os campos dos elegíveis.

    Raises:
        ValueError: se houver menos itens do que pares de atenção.
    """
    if len(elegiveis) < len(D_ATENCAO_MS):
        raise ValueError("elegíveis insuficientes para os pares de atenção")
    rng = random.Random(semente)
    ordem = list(elegiveis)
    rng.shuffle(ordem)
    n_principais = min(len(D_MS) * por_d, len(ordem))
    principais = ordem[:n_principais]
    resto = ordem[n_principais:]

    por_video = sorted(
        principais, key=lambda e: (e["video"], e["tela"], e["exibicao"], e["coluna"])
    )
    pares = [
        {**it, "d_ms": D_MS[i % len(D_MS)], "atencao": False}
        for i, it in enumerate(por_video)
    ]
    reserva = resto + principais
    atencao_itens = []
    for it in reserva:
        if len(atencao_itens) == len(D_ATENCAO_MS):
            break
        atencao_itens.append(it)
    pares += [
        {**it, "d_ms": d, "atencao": True}
        for it, d in zip(atencao_itens, D_ATENCAO_MS, strict=True)
    ]

    rng.shuffle(pares)
    flags = [True] * (len(pares) // 2) + [False] * (len(pares) - len(pares) // 2)
    rng.shuffle(flags)
    for n, (par, a_e_alinhador) in enumerate(zip(pares, flags, strict=True), start=1):
        par["id"] = f"p{n:02d}"
        par["alinhador_e"] = "A" if a_e_alinhador else "B"
    return pares


def gerar_par_comparacao(
    par: dict,
    pasta: Path,
    raiz: Path | None = None,
    raiz_acervo: str | None = None,
) -> dict:
    """Gera os dois MP4 do par (``<id>_a.mp4`` e ``<id>_b.mp4``) com a mesma janela.

    A janela é ``t_alinhador - JANELA_S`` até ``t_alinhador + JANELA_S`` (começa no primeiro
    quadro), para A e B. O clique do alinhador fica em ``t_alinhador``; o outro, em
    ``t_alinhador + d_ms/1000``. A caixa é a mesma nos dois.

    Args:
        par: um par de ``planejar_comparacao``.
        pasta: pasta onde os MP4 são gravados (a pasta servida).
        raiz: raiz do cache de áudio (``None`` usa a padrão).
        raiz_acervo: raiz do acervo para a chave do cache (``None`` usa ``/acervo``).

    Returns:
        ``{id, arquivo_a, arquivo_b, inicio_clipe_s, clique_a_s, clique_b_s}``, com os
        instantes do clique em segundos da linha do tempo do clipe.

    Raises:
        ValueError: se ``t_alinhador`` estiver a menos de ``JANELA_S`` do início do vídeo.
    """
    video = str(par["video"])
    t_al = float(par["t_alinhador"])
    t_des = t_al + par["d_ms"] / 1000.0
    inicio_pedido = t_al - JANELA_S
    if inicio_pedido < 0:
        raise ValueError(f"{par['id']}: t_alinhador antes de {JANELA_S} s")
    inicio = _primeiro_quadro_a_partir(video, inicio_pedido)
    _, meta = garantir(video, raiz=raiz, raiz_acervo=raiz_acervo)
    clique_al = instante_de(indice_de(t_al, meta), meta)
    clique_des = instante_de(indice_de(t_des, meta), meta)
    if par["alinhador_e"] == "A":
        clique_a, clique_b = clique_al, clique_des
    else:
        clique_a, clique_b = clique_des, clique_al
    arquivo_a = f"{par['id']}_a.mp4"
    arquivo_b = f"{par['id']}_b.mp4"
    for arquivo, clique in ((arquivo_a, clique_a), (arquivo_b, clique_b)):
        _renderizar_clipe(
            video,
            inicio,
            clique - inicio,
            float(par["x_centro_quadro"]),
            float(par["passo"]),
            list(par["painel"]),
            Path(pasta) / arquivo,
        )
    return {
        "id": par["id"],
        "arquivo_a": arquivo_a,
        "arquivo_b": arquivo_b,
        "inicio_clipe_s": round(inicio, 6),
        "clique_a_s": round(clique_a - inicio, 6),
        "clique_b_s": round(clique_b - inicio, 6),
    }


def gerar_pagina_comparacao(pasta: Path, manifesto: list[dict]) -> Path:
    """Gera o ``index.html`` da comparação A/B: uma linha por par, sem revelar d.

    A página só recebe ``id``, ``arquivo_a`` e ``arquivo_b`` do manifesto. Nada do gabarito
    (deslocamento, alinhador, vídeo) entra nela.

    Args:
        pasta: pasta servida (recebe ``index.html``; os MP4 já estão nela).
        manifesto: ``[{id, arquivo_a, arquivo_b}]`` na ordem da página.

    Returns:
        O caminho do ``index.html``.
    """
    linhas = []
    for n, m in enumerate(manifesto):
        ident = html.escape(m["id"], quote=True)
        arq_a = html.escape(m["arquivo_a"], quote=True)
        arq_b = html.escape(m["arquivo_b"], quote=True)
        linhas.append(
            f'<section class="linha" id="linha-{n}">\n'
            f"  <h2>Linha {n + 1} de {len(manifesto)} ({ident})</h2>\n"
            '  <div class="videos">\n'
            f'    <figure><figcaption>A</figcaption><video controls preload="metadata" '
            f'src="{arq_a}"></video></figure>\n'
            f'    <figure><figcaption>B</figcaption><video controls preload="metadata" '
            f'src="{arq_b}"></video></figure>\n'
            "  </div>\n"
            '  <div class="botoes">\n'
            '    <button type="button" data-resposta="A">A (1)</button>\n'
            '    <button type="button" data-resposta="B">B (2)</button>\n'
            '    <button type="button" data-resposta="nao_sei">não sei (3)</button>\n'
            "  </div>\n"
            '  <input type="text" data-obs="1" placeholder="observação (opcional)">\n'
            "</section>"
        )
    dados = json.dumps(
        [{"id": m["id"]} for m in manifesto], ensure_ascii=False
    ).replace("</", "<\\/")
    pagina = _MODELO_COMPARACAO.replace("__LINHAS__", "\n".join(linhas)).replace(
        "__DADOS__", dados
    )
    destino = pasta / "index.html"
    destino.write_text(pagina, encoding="utf-8")
    return destino


def cmd_comparar(
    golds: list[Path],
    pedidos: list[Path],
    semente: int,
    pasta: Path,
    chave: Path,
    pedidos_saida: Path,
    manifesto: Path,
) -> int:
    """Monta a folha 3: sorteia os pares, gera os MP4 e grava chave, pedidos e manifesto.

    A chave, os pedidos e o manifesto ficam FORA de ``pasta`` (a pasta servida).

    Args:
        golds: gabaritos ``folha*.json`` (só leitura).
        pedidos: pedidos ``folha*_pedidos.json`` das mesmas folhas.
        semente: semente do sorteio (2003).
        pasta: pasta servida (``folha3/``).
        chave: JSON com o gabarito completo (fora da pasta).
        pedidos_saida: JSON com os pares sorteados (fora da pasta).
        manifesto: JSON ``[{id, arquivo_a, arquivo_b}]`` para a página (fora da pasta).

    Returns:
        Código de saída (0 se deu certo).
    """
    mapa_pedidos: dict[str, dict] = {}
    for arq in pedidos:
        for p in _ler_pedidos(arq):
            mapa_pedidos[p["id"]] = p
    golds_lidos = []
    for arq in golds:
        golds_lidos += json.loads(Path(arq).read_text(encoding="utf-8"))["itens"]
    elegiveis = elegiveis_comparacao(golds_lidos, mapa_pedidos)
    planos = planejar_comparacao(elegiveis, semente)
    pasta.mkdir(parents=True, exist_ok=True)
    saidas = []
    for plano in planos:
        saidas.append(gerar_par_comparacao(plano, pasta))
        print(f"{plano['id']} pronto")
    _gravar_json(pedidos_saida, planos)
    _gravar_json(
        chave,
        [
            {
                "id": pl["id"],
                "item_gold": pl["item_gold"],
                "video": pl["rotulo"],
                "tela": pl["tela"],
                "exibicao": pl["exibicao"],
                "coluna": pl["coluna"],
                "t_alinhador": pl["t_alinhador"],
                "d_ms": pl["d_ms"],
                "t_deslocado": round(pl["t_alinhador"] + pl["d_ms"] / 1000.0, 6),
                "alinhador_e": pl["alinhador_e"],
                "atencao": pl["atencao"],
            }
            for pl in planos
        ],
    )
    _gravar_json(
        manifesto,
        [
            {"id": s["id"], "arquivo_a": s["arquivo_a"], "arquivo_b": s["arquivo_b"]}
            for s in saidas
        ],
    )
    print(f"{len(planos)} pares em {pasta}")
    return 0


#: Folha 4 (rasgueado): tolerância entre v2 e v2.1 para uma nota "igual", em s.
TOLERANCIA_IGUAL_S = 0.010

#: Folha 4: distância mínima, em s, do clique de controle a QUALQUER coluna afirmada da tela.
DISTANCIA_COLUNA_CONTROLE_S = 0.150

#: Folha 4: quantidade de clipes de cada categoria.
QUANTIDADES_RASGUEADO = {"nota_nova": 8, "nota_igual": 3, "abafada": 3, "controle": 2}

#: Folha 4: texto extra da página (a caixa de abafada).
AVISO_RASGUEADO = (
    "Em alguns clipes a caixa marca uma batida abafada (X): a pergunta é se o clique "
    "cai junto com a batida."
)


def _chave_coluna(c: dict) -> tuple[int, int, int]:
    """Chave ``(tela, exibicao, coluna)`` de um registro de alinhamento."""
    return (int(c["tela"]), int(c["exibicao"]), int(c["coluna"]))


def candidatos_rasgueado(v2: dict, v21: dict) -> dict[str, list[dict]]:
    """Candidatos da folha 4, pelas duas versões do alinhamento.

    Notas com tempo só na v2.1 (``nota_nova``), notas com tempo nas duas versões com
    ``|Δt| <= TOLERANCIA_IGUAL_S`` (``nota_igual``) e abafadas afirmadas na v2.1 (``abafada``).
    Só a v2.1 tem ``tipo``; a v2 não tem abafadas, então ``t_v2`` é ``None`` nelas.

    Args:
        v2: alinhamento antigo (``tab.audio_alinhar`` sem o método rasgueado).
        v21: alinhamento novo, com ``tipo`` ``"nota"`` ou ``"abafada"`` em cada coluna.

    Returns:
        ``{"nota_nova": [...], "nota_igual": [...], "abafada": [...]}``; cada item tem
        ``tela``, ``exibicao``, ``coluna``, ``tipo``, ``t_audio`` (v2.1) e ``t_v2``.
    """
    antigo = {_chave_coluna(c): c for c in v2["colunas"]}
    pools: dict[str, list[dict]] = {"nota_nova": [], "nota_igual": [], "abafada": []}
    for c in v21["colunas"]:
        t21 = c["t_audio"]
        if t21 is None:
            continue
        a = antigo.get(_chave_coluna(c))
        t2 = a["t_audio"] if a is not None else None
        item = {
            "tela": int(c["tela"]),
            "exibicao": int(c["exibicao"]),
            "coluna": int(c["coluna"]),
            "tipo": c["tipo"],
            "t_audio": float(t21),
            "t_v2": None if t2 is None else float(t2),
        }
        if c["tipo"] == "abafada":
            pools["abafada"].append(item)
        elif t2 is None:
            pools["nota_nova"].append(item)
        elif abs(float(t2) - float(t21)) <= TOLERANCIA_IGUAL_S:
            pools["nota_igual"].append(item)
    return pools


def pares_consecutivos_afirmados(colunas: list[dict]) -> list[tuple[dict, dict]]:
    """Pares de colunas vizinhas na ordem da exibição, ambas afirmadas.

    Como ``colunas`` vem em ordem de coluna, duas vizinhas na lista não têm coluna no meio.
    Uma coluna recusada entre duas afirmadas quebra o par.

    Args:
        colunas: registros de UMA exibição (já com ``t_audio``), em ordem de coluna.

    Returns:
        Pares ``(a, b)`` com ``t_audio`` não nulo nos dois.
    """
    return [
        (a, b)
        for a, b in itertools.pairwise(colunas)
        if a["t_audio"] is not None and b["t_audio"] is not None
    ]


def escolher_controles_rasgueado(
    pares: list[tuple[dict, dict]],
    instantes_tela: dict[int, list[float]],
    audio: tuple[np.ndarray, int, float],
    rng: random.Random,
    n: int,
    proibidas: set[tuple[int, int]],
) -> tuple[list[dict], int]:
    """Até ``n`` controles: clique no meio de um par, longe de colunas e de picos de fluxo.

    Um par serve se, para o clique no ponto médio ``m``: (1) nenhuma coluna afirmada da tela
    (qualquer tipo) está a menos de ``DISTANCIA_COLUNA_CONTROLE_S`` de ``m`` (incluindo a e b);
    (2) nenhum pico do fluxo espectral está a menos de ``DISTANCIA_MIN_PICO_S`` de ``m``.
    Colunas sem tempo (recusadas) não têm instante, então só as afirmadas entram na regra (1).

    Args:
        pares: pares de ``pares_consecutivos_afirmados`` de todas as exibições.
        instantes_tela: ``{tela: [t de cada coluna afirmada da tela]}``.
        audio: ``carregar_audio`` do vídeo.
        rng: gerador da folha (ordem de tentativa).
        n: quantos controles se quer.
        proibidas: pares ``(tela, coluna)`` já usados (não podem ser o controle).

    Returns:
        ``(controles, candidatos_aceitos)``: cada controle tem ``a``, ``b``, ``clique``,
        ``dist_coluna_s`` (até a coluna afirmada mais próxima) e ``dist_pico_s``.
        ``len(controles) < n`` significa que não havia par assim.
    """
    amostras, taxa, t0_amostra = audio
    ordem = list(range(len(pares)))
    rng.shuffle(ordem)
    controles: list[dict] = []
    aceitos = 0
    usados: set[tuple[int, int]] = set(proibidas)
    for i in ordem:
        if len(controles) == n:
            break
        a, b = pares[i]
        chaves = {(a["tela"], a["coluna"]), (b["tela"], b["coluna"])}
        if chaves & usados:
            continue
        clique = (a["t_audio"] + b["t_audio"]) / 2.0
        vizinhas = np.asarray(instantes_tela.get(a["tela"], []), dtype=np.float64)
        dist_col = distancia_ao_pico(clique, vizinhas)
        if dist_col < DISTANCIA_COLUNA_CONTROLE_S:
            continue
        janela = picos_de_fluxo(
            amostras,
            taxa,
            t0_amostra,
            a["t_audio"] - MARGEM_PICOS_S,
            b["t_audio"] + MARGEM_PICOS_S,
        )
        dist_pico = distancia_ao_pico(clique, janela)
        aceitos += 1
        if dist_pico < DISTANCIA_MIN_PICO_S:
            continue
        controles.append(
            {
                "a": a,
                "b": b,
                "clique": clique,
                "dist_coluna_s": dist_col,
                "dist_pico_s": dist_pico,
            }
        )
        usados |= chaves
    return controles, aceitos


def pedido_abafada(item: dict, produto: dict, numero: int) -> dict:
    """Pedido de clipe de uma abafada: a caixa vem dos ``nao_notas`` da coluna.

    A coluna abafada não tem nota em ``notas``; o ``x_centro_quadro`` é a média dos
    ``x_centro_quadro`` dos ``nao_notas`` da mesma ``(tela, coluna)``.

    Args:
        item: item de ``candidatos_rasgueado`` (abafada).
        produto: produto do vídeo (``telas``, ``nao_notas``).
        numero: número do pedido, para o ``id``.

    Returns:
        O pedido com ``id``, ``video``, ``t_audio``, ``tela``, ``coluna``, ``exibicao``,
        ``x_centro_quadro``, ``painel``, ``passo``, ``rotulo`` e ``notas`` vazias.

    Raises:
        ValueError: se a tela ou os ``nao_notas`` da coluna não existirem no produto.
    """
    tela = next(t for t in produto["telas"] if t["id"] == item["tela"])
    xs = [
        float(n["x_centro_quadro"])
        for n in produto.get("nao_notas", [])
        if n["tela"] == item["tela"] and n["coluna"] == item["coluna"]
    ]
    if not xs:
        raise ValueError(
            f"sem nao_notas na tela {item['tela']} coluna {item['coluna']}"
        )
    rotulo = os.path.splitext(os.path.basename(produto["video"]["arquivo"]))[0]
    return {
        "id": f"p{numero:03d}",
        "video": item["video"],
        "t_audio": float(item["t_audio"]),
        "tela": item["tela"],
        "coluna": item["coluna"],
        "exibicao": item["exibicao"],
        "x_centro_quadro": round(sum(xs) / len(xs), 2),
        "painel": tela["painel"],
        "passo": tela["passo"],
        "rotulo": rotulo,
        "notas": [],
    }


def planejar_rasgueado(
    v2: dict,
    v21: dict,
    produto: dict,
    audio: tuple[np.ndarray, int, float],
    semente: int,
) -> list[dict]:
    """Sorteia os 16 clipes da folha 4 (controles primeiro, depois as categorias).

    Ordem do sorteio com ``Random(semente)``: 2 controles entre os pares consecutivos
    afirmados; depois 8 notas novas, 3 notas iguais e 3 abafadas, espalhadas no tempo com
    ``sortear_espalhado``, excluindo as colunas dos controles. Por fim, embaralha e dá os ids.

    Args:
        v2: alinhamento antigo.
        v21: alinhamento novo.
        produto: produto ``tab.video`` sem marcador (``telas``, ``notas``, ``nao_notas``).
        audio: ``carregar_audio`` do vídeo.
        semente: semente da folha (2004).

    Returns:
        Lista de 16 entradas com ``id``, ``categoria``, ``tipo``, ``t_v2``, ``t_v21``,
        ``dist_vizinho_s`` (distância até a coluna afirmada mais próxima da mesma tela),
        ``controle`` e o pedido (``video``, ``t_audio``, ``tela``, ``coluna``...).
        Controles faltando são reportados em ``len``, não inventados.
    """
    rng = random.Random(semente)
    pools = candidatos_rasgueado(v2, v21)
    if v21["video"]["arquivo"] != PREFIXO_ACERVO + produto["video"]["arquivo"]:
        raise ValueError("produto não é o do alinhamento")

    instantes: dict[int, list[float]] = {}
    for c in v21["colunas"]:
        if c["t_audio"] is not None:
            instantes.setdefault(int(c["tela"]), []).append(float(c["t_audio"]))

    por_exib: dict[tuple[int, int], list[dict]] = {}
    for c in v21["colunas"]:
        por_exib.setdefault((int(c["tela"]), int(c["exibicao"])), []).append(c)
    pares: list[tuple[dict, dict]] = []
    for chave in sorted(por_exib):
        ordenadas = sorted(por_exib[chave], key=lambda c: int(c["coluna"]))
        pares += pares_consecutivos_afirmados(ordenadas)

    controles, _ = escolher_controles_rasgueado(
        pares, instantes, audio, rng, QUANTIDADES_RASGUEADO["controle"], set()
    )
    proibidas: set[tuple[int, int]] = set()
    for ctrl in controles:
        proibidas |= {
            (ctrl["a"]["tela"], ctrl["a"]["coluna"]),
            (ctrl["b"]["tela"], ctrl["b"]["coluna"]),
        }

    escolhidos: list[tuple[str, dict]] = []
    for ctrl in controles:
        escolhidos.append(
            (
                "controle",
                {
                    **ctrl["a"],
                    "tipo": ctrl["a"]["tipo"],
                    "t_audio": ctrl["clique"],
                    "t_v2": None,
                    "_ctrl": ctrl,
                },
            )
        )
    for cat, chave_pool, qtd in (
        ("nota_nova", "nota_nova", QUANTIDADES_RASGUEADO["nota_nova"]),
        ("nota_igual", "nota_igual", QUANTIDADES_RASGUEADO["nota_igual"]),
        ("abafada", "abafada", QUANTIDADES_RASGUEADO["abafada"]),
    ):
        pool = [
            it
            for it in pools[chave_pool]
            if (it["tela"], it["coluna"]) not in proibidas
        ]
        for it in sortear_espalhado(pool, qtd, rng):
            escolhidos.append((cat, it))
            proibidas.add((it["tela"], it["coluna"]))

    entradas = []
    for cat, it in escolhidos:
        dist = None
        if cat != "controle":
            outros = [t for t in instantes.get(it["tela"], []) if t != it["t_audio"]]
            dist = round(distancia_ao_pico(it["t_audio"], np.asarray(outros)), 4)
        entradas.append({"categoria": cat, "item": it, "dist_vizinho_s": dist})
    rng.shuffle(entradas)
    for n, e in enumerate(entradas, start=1):
        e["id"] = f"h{n:02d}"
    return entradas


def cmd_rasgueado(
    v2_arq: Path,
    v21_arq: Path,
    produto_arq: Path,
    semente: int,
    pasta: Path,
    chave: Path,
    pedidos_saida: Path,
    manifesto: Path,
) -> int:
    """Monta a folha 4: sorteia, gera os clipes e grava chave, pedidos e manifesto.

    Args:
        v2_arq: alinhamento antigo.
        v21_arq: alinhamento novo (com ``tipo``).
        produto_arq: produto ``tab.video`` do vídeo.
        semente: semente (2004).
        pasta: pasta servida (``folha4/``).
        chave: JSON com o gabarito (fora da pasta).
        pedidos_saida: JSON com os pedidos (fora da pasta).
        manifesto: JSON ``[{id, arquivo, rotulo, tela, coluna, notas}]`` para a página.

    Returns:
        Código de saída (0 se deu certo).
    """
    v2 = ler_alinhamento(str(v2_arq))
    v21 = ler_alinhamento(str(v21_arq))
    produto = json.loads(Path(produto_arq).read_text(encoding="utf-8"))
    audio = carregar_audio(v21["video"]["arquivo"])
    entradas = planejar_rasgueado(v2, v21, produto, audio, semente)
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto_lista, chave_lista, pedidos_lista = [], [], []
    for e in entradas:
        it = e["item"]
        if e["categoria"] == "controle":
            ctrl = it["_ctrl"]
            pedido = {
                "id": e["id"],
                **{
                    k: v
                    for k, v in pedido_coluna(
                        {**ctrl["a"], "video": v21["video"]["arquivo"]}, produto, 0
                    ).items()
                    if k != "id"
                },
                "t_audio": round(ctrl["clique"], 6),
            }
        else:
            item = {**it, "video": v21["video"]["arquivo"]}
            pedido = {**pedido_coluna(item, produto, 0), "id": e["id"]}
        medido = gerar_clipe(pedido, pasta)
        manifesto_lista.append(
            {k: medido[k] for k in ("id", "arquivo", "rotulo", "tela", "coluna")}
            | {"notas": medido.get("notas", [])}
        )
        registro = {
            "id": e["id"],
            "categoria": e["categoria"],
            "controle": e["categoria"] == "controle",
            "tipo": it["tipo"],
            "tela": it["tela"],
            "exibicao": it["exibicao"],
            "coluna": it["coluna"],
            "t_v2": it["t_v2"],
            "t_v21": it["_ctrl"]["a"]["t_audio"]
            if e["categoria"] == "controle"
            else it["t_audio"],
            "t_clique": pedido["t_audio"],
            "dist_vizinho_s": e["dist_vizinho_s"],
        }
        if e["categoria"] == "controle":
            registro["dist_coluna_s"] = round(it["_ctrl"]["dist_coluna_s"], 4)
            registro["dist_pico_s"] = round(it["_ctrl"]["dist_pico_s"], 4)
            registro["t_c"] = it["_ctrl"]["a"]["t_audio"]
            registro["t_c1"] = it["_ctrl"]["b"]["t_audio"]
        chave_lista.append(registro)
        pedidos_lista.append(pedido)
    _gravar_json(chave, chave_lista)
    _gravar_json(pedidos_saida, pedidos_lista)
    _gravar_json(manifesto, manifesto_lista)
    contagem = Counter(e["categoria"] for e in entradas)
    print(f"{len(entradas)} clipes em {pasta}: {dict(contagem)}")
    return 0


def pedido_coluna(item: dict, produto: dict, numero: int) -> dict:
    """Pedido de uma coluna da folha 4: nota (``notas``) ou abafada (``nao_notas``).

    Args:
        item: item com ``video``, ``tela``, ``exibicao``, ``coluna``, ``t_audio``, ``tipo``.
        produto: produto do vídeo.
        numero: número do pedido.

    Returns:
        O pedido (ver ``_pedido_do_item`` e ``pedido_abafada``).
    """
    if item.get("tipo") == "abafada":
        return pedido_abafada(item, produto, numero)
    return _pedido_do_item(item, produto, numero)


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
    p_clipes.add_argument("--manifesto", type=Path, default=None)

    p_pagina = sub.add_parser("pagina", help="gera o index.html da pasta")
    p_pagina.add_argument("--pasta", type=Path, required=True)
    p_pagina.add_argument("--manifesto", type=Path, default=None)
    p_pagina.add_argument("--aviso", default="")

    p_sortear = sub.add_parser(
        "sortear", help="sorteia colunas afirmadas, pares ALINHADO PRODUTO"
    )
    p_sortear.add_argument("--alinhado", nargs="+", required=True)
    p_sortear.add_argument("--por-video", type=int, required=True)
    p_sortear.add_argument("--semente", type=int, required=True)
    p_sortear.add_argument("--saida", type=Path, required=True)

    p_comp = sub.add_parser("comparar", help="monta a folha A/B (pares de clipes)")
    p_comp.add_argument("--gold", type=Path, nargs="+", required=True)
    p_comp.add_argument("--pedidos", type=Path, nargs="+", required=True)
    p_comp.add_argument("--semente", type=int, required=True)
    p_comp.add_argument("--pasta", type=Path, required=True)
    p_comp.add_argument("--chave", type=Path, required=True)
    p_comp.add_argument("--pedidos-saida", type=Path, required=True)
    p_comp.add_argument("--manifesto", type=Path, required=True)

    p_pagc = sub.add_parser("pagina-comparacao", help="gera o index da folha A/B")
    p_pagc.add_argument("--pasta", type=Path, required=True)
    p_pagc.add_argument("--manifesto", type=Path, required=True)

    p_rasg = sub.add_parser("rasgueado", help="monta a folha 4 (abafadas e notas v2.1)")
    p_rasg.add_argument("--v2", type=Path, required=True)
    p_rasg.add_argument("--v21", type=Path, required=True)
    p_rasg.add_argument("--produto", type=Path, required=True)
    p_rasg.add_argument("--semente", type=int, required=True)
    p_rasg.add_argument("--pasta", type=Path, required=True)
    p_rasg.add_argument("--chave", type=Path, required=True)
    p_rasg.add_argument("--pedidos-saida", type=Path, required=True)
    p_rasg.add_argument("--manifesto", type=Path, required=True)

    args = parser.parse_args()
    if args.comando == "comparar":
        return cmd_comparar(
            args.gold,
            args.pedidos,
            args.semente,
            args.pasta,
            args.chave,
            args.pedidos_saida,
            args.manifesto,
        )
    if args.comando == "rasgueado":
        return cmd_rasgueado(
            args.v2,
            args.v21,
            args.produto,
            args.semente,
            args.pasta,
            args.chave,
            args.pedidos_saida,
            args.manifesto,
        )
    if args.comando == "pagina-comparacao":
        manifesto = json.loads(args.manifesto.read_text(encoding="utf-8"))
        destino = gerar_pagina_comparacao(args.pasta, manifesto)
        print(f"página gerada: {destino}")
        return 0
    if args.comando == "clipes":
        return cmd_clipes(args.pedidos, args.pasta, args.manifesto)
    if args.comando == "pagina":
        destino = gerar_pagina(args.pasta, args.manifesto, args.aviso)
        print(f"página gerada: {destino}")
        return 0
    return cmd_sortear(args.alinhado, args.por_video, args.semente, args.saida)


if __name__ == "__main__":
    sys.exit(main())
