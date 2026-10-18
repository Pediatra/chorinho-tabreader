"""Completar a pauta pela tab: função pura, usada pela E1 e pela P4 (rodadas 3170 e 3027).

Para cada evento da tab sem nota da partitura com aquela altura, a nota entra:

- **acorde**: há evento da partitura pareado no mesmo x (par conferido). A nota entra nele,
  com a figura e a voz do evento (voz 2 para as cordas 4 a 6, quando o compasso já tem duas
  vozes);
- **ataque isolado**: não há evento pareado. A figura vem do déficit do compasso (duração
  esperada menos a maior soma por voz), se o déficit cabe numa figura só. Senão a figura fica
  ``None``;
- nunca se descarta nota.

Dois usos: a E1 (``tab/partitura_completar.py``, que mostra a figura do déficit) e a P4,
``completar_pauta``, que grava a nota com figura ``null`` e as regras da rodada 3172.

Este módulo não importa ``tab.partitura_video``: assim ``partitura_video`` pode importá-lo sem
import circular. Não lê nem grava arquivo: recebe os dados prontos.
"""

from __future__ import annotations

from collections import defaultdict

from .partitura_regua import _seminimas

#: Valor em semínimas de cada figura do MusicXML.
FIGURAS = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "16th": 0.25,
    "32nd": 0.125,
}
#: Déficit que cabe numa figura só: (semínimas, nome, pontuada).
FIGURA_UNICA = [
    (4.0, "whole", False),
    (3.0, "half", True),
    (2.0, "half", False),
    (1.5, "quarter", True),
    (1.0, "quarter", False),
    (0.75, "eighth", True),
    (0.5, "eighth", False),
    (0.25, "16th", False),
    (0.125, "32nd", False),
]
TOLERANCIA_PX = 5.0
TOLERANCIA_DURACAO = 1e-6
CORDAS_VOZ_2 = {4, 5, 6}
#: ``tecnica`` do produto que marca o harmônico (rodada 3172: harmônico vem só da tab).
TECNICA_HARMONICO = "harm"
#: ``tecnica`` do produto que marca a nota ligada (casa presa, entre parênteses).
TECNICA_LIGADA = "lig"
#: Nomes das notas, para o campo ``nome`` do símbolo completado.
NOMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _duracao(simbolo: dict) -> float:
    """Duração de um símbolo em semínimas (pontuada ×1,5).

    Args:
        simbolo: símbolo normalizado (com ``figura`` e ``pontuada``).

    Returns:
        Duração em semínimas, ou 0.0 se a figura é desconhecida.
    """
    base = FIGURAS.get(simbolo.get("figura"), 0.0)
    return base * 1.5 if simbolo.get("pontuada") else base


def _normalizar(simbolos: list[dict]) -> list[dict]:
    """Símbolos com as chaves ``midi``, ``figura``, ``pontuada`` e ``voz``.

    Aceita o formato do ``.partitura.json`` (``midi_escrito``) e o de ``ler_partitura``
    (``midi``).

    Args:
        simbolos: símbolos em um dos dois formatos.

    Returns:
        Lista com as mesmas notas nas chaves padrão.
    """
    saida = []
    for s in simbolos:
        midi = s.get("midi_escrito", s.get("midi"))
        saida.append(
            {
                "midi": midi,
                "figura": s.get("figura"),
                "pontuada": bool(s.get("pontuada")),
                "voz": str(s.get("voz", "1")),
            }
        )
    return saida


def _candidato_oitava(midi: int, x: float | None, eventos: list[dict]) -> bool:
    """Diz se a pauta tem a nota uma oitava acima, no mesmo x (candidato a harmônico).

    Só diagnóstico: a regra da 3013 (a pauta tem a nota uma oitava acima no mesmo x).
    O harmônico de verdade vem da tab (símbolo), não daqui; a decisão do dono (3170) tirou
    esta regra da conta.

    Args:
        midi: altura escrita da nota da tab que falta na pauta.
        x: posição x da coluna da tab.
        eventos: eventos normalizados da partitura do recorte ou da tela.

    Returns:
        True se algum evento da partitura no mesmo x tem ``midi + 12``.
    """
    if x is None:
        return False
    for evento in eventos:
        if (
            evento["x"] is not None
            and abs(evento["x"] - x) <= TOLERANCIA_PX
            and (midi + 12) in evento["midis"]
        ):
            return True
    return False


def _compasso_de_x(x: float | None, compassos: list[dict]) -> str | None:
    """Número do compasso que contém o x, pelo último compasso que começa antes dele.

    Args:
        x: posição x no quadro da nota da tab.
        compassos: lista ``{"numero", "fracao", "x_quadro"}``, na ordem.

    Returns:
        O ``numero`` do compasso, ou None se não há compasso com x até ``x``.
    """
    if x is None:
        return None
    escolhido = None
    for compasso in compassos:
        cx = compasso.get("x_quadro")
        if cx is not None and cx <= x + TOLERANCIA_PX:
            escolhido = compasso["numero"]
    return escolhido


def _figura_do_deficit(deficit: float) -> tuple[str | None, bool]:
    """Figura de um déficit de compasso, se ele cabe numa figura só.

    Args:
        deficit: esperada menos a maior soma por voz, em semínimas.

    Returns:
        ``(figura, pontuada)``, ou ``(None, False)`` se o déficit não é uma figura só.
    """
    for valor, nome, pontuada in FIGURA_UNICA:
        if abs(deficit - valor) < TOLERANCIA_DURACAO:
            return nome, pontuada
    return None, False


def _soma_do_compasso(eventos: list[dict], numero: str) -> float:
    """Maior soma por voz das durações dos eventos de um compasso (acorde conta uma vez).

    Args:
        eventos: eventos normalizados, com ``compasso`` e ``simbolos``.
        numero: número do compasso.

    Returns:
        A maior soma por voz, em semínimas.
    """
    somas: dict[str, float] = defaultdict(float)
    for evento in eventos:
        if evento["compasso"] != numero or not evento["simbolos"]:
            continue
        primeiro = evento["simbolos"][0]
        somas[primeiro["voz"]] += _duracao(primeiro)
    return max(somas.values(), default=0.0)


def _completar(
    notas_tab: list[dict],
    eventos: list[dict],
    pares: dict[int, int],
    compassos: list[dict],
    identificacao: dict,
) -> list[dict]:
    """Monta as notas completadas de um recorte ou tela.

    Args:
        notas_tab: eventos da tab; cada um tem ``x``, ``midis`` (escritas) e ``cordas``
            (corda de cada altura).
        eventos: eventos da partitura normalizados, com ``compasso``, ``x``, ``midis`` e
            ``simbolos``.
        pares: ``{indice do evento da tab: indice do evento da partitura}``, só com par
            conferido.
        compassos: ``{"numero", "fracao", "x_quadro"}`` do recorte ou da tela.
        identificacao: campos que vão para cada nota (``video``, ``tela``, ``recorte``).

    Returns:
        Uma entrada por nota completada, com ``origem`` ``tab_completada``, ``tipo``
        (``acorde`` ou ``isolado``), ``figura`` (ou None) e ``pontuada``.
    """
    completadas = []
    for j, tab in enumerate(notas_tab):
        i = pares.get(j)
        if i is not None:
            evento = eventos[i]
            faltam = sorted(m for m in tab["midis"] if m not in evento["midis"])
            if not faltam:
                continue
            primeiro = evento["simbolos"][0] if evento["simbolos"] else None
            compasso = evento["compasso"]
            tem_voz2 = any(
                s["voz"] == "2"
                for e in eventos
                if e["compasso"] == compasso
                for s in e["simbolos"]
            )
            for midi in faltam:
                cordas = tab["cordas"].get(midi, 0)
                voz = (
                    "2"
                    if cordas in CORDAS_VOZ_2 and tem_voz2
                    else (primeiro["voz"] if primeiro else "1")
                )
                da_voz = [s for s in evento["simbolos"] if s["voz"] == voz]
                mesma_voz = da_voz[0] if da_voz else None
                completadas.append(
                    {
                        **identificacao,
                        "origem": "tab_completada",
                        "tipo": "acorde",
                        "compasso": compasso,
                        "midi": midi,
                        "figura": mesma_voz["figura"] if mesma_voz else None,
                        "pontuada": mesma_voz["pontuada"] if mesma_voz else False,
                        "voz": voz,
                        "x": tab["x"],
                        "harmonico": bool(tab.get("harmonico_tab")),
                        "candidato_oitava": _candidato_oitava(midi, tab["x"], eventos),
                    }
                )
        else:
            compasso = _compasso_de_x(tab["x"], compassos)
            esperada = _seminimas_compasso(compassos, compasso)
            soma = _soma_do_compasso(eventos, compasso) if compasso is not None else 0.0
            deficit = (esperada - soma) if esperada is not None else None
            figura, pontuada = (
                _figura_do_deficit(deficit)
                if deficit is not None and deficit > 0
                else (None, False)
            )
            for midi in sorted(tab["midis"]):
                completadas.append(
                    {
                        **identificacao,
                        "origem": "tab_completada",
                        "tipo": "isolado",
                        "compasso": compasso,
                        "midi": midi,
                        "figura": figura,
                        "pontuada": pontuada,
                        "voz": "1",
                        "x": tab["x"],
                        "harmonico": bool(tab.get("harmonico_tab")),
                        "candidato_oitava": _candidato_oitava(midi, tab["x"], eventos),
                        "deficit": deficit,
                    }
                )
    return completadas


def _seminimas_compasso(compassos: list[dict], numero: str | None) -> float | None:
    """Duração esperada de um compasso, em semínimas, pela fração.

    Args:
        compassos: ``{"numero", "fracao", "x_quadro"}`` do recorte ou da tela.
        numero: número do compasso.

    Returns:
        Semínimas do compasso, ou None se não há fração ou compasso.
    """
    for compasso in compassos:
        if compasso["numero"] == numero:
            return _seminimas(compasso.get("fracao"))
    return None


def _nome(midi: int) -> str:
    """Nome de uma altura MIDI, como ``E5`` (oitava científica).

    Cópia de ``tab.partitura_completar_itens._nome``, não importada: aquele módulo importa
    ``partitura_video``, e importá-lo daqui faria um ciclo.

    Args:
        midi: altura escrita em MIDI.

    Returns:
        Nome da nota com a oitava.
    """
    return f"{NOMES[midi % 12]}{midi // 12 - 1}"


def _simbolo_completado(midi: int, voz: str, harmonico: bool) -> dict:
    """Símbolo de uma nota completada pela tab, no formato de ``chorinho/partitura@1``.

    A figura é sempre ``None`` (rodada 3172: não se chuta figura). ``harmonico`` só entra
    quando é verdadeiro.

    Args:
        midi: altura escrita.
        voz: voz da nota.
        harmonico: se a nota da tab é harmônico (``tecnica`` ``harm``).

    Returns:
        Símbolo com os campos de ``_simbolo_do_documento`` e ``origem`` ``tab_completada``.
    """
    simbolo = {
        "nome": _nome(midi),
        "midi_escrito": midi,
        "figura": None,
        "pontuada": False,
        "voz": voz,
        "ligadura_inicio": False,
        "ligadura_fim": False,
        "notacoes": [],
        "origem": "tab_completada",
    }
    if harmonico:
        simbolo["harmonico"] = True
    return simbolo


def _posicao_por_x(eventos: list[dict], x: float) -> int:
    """Posição de um evento novo, antes do primeiro evento com x maior.

    Os eventos que já estão na pauta não são reordenados (uma pauta fora de ordem fica como
    está). Sem evento com x maior, a posição é o fim da lista.

    Args:
        eventos: eventos da pauta, no formato do documento.
        x: ``x_quadro`` do evento novo.

    Returns:
        Índice onde o evento novo entra.
    """
    for posicao, evento in enumerate(eventos):
        if evento["x_quadro"] is not None and evento["x_quadro"] > x:
            return posicao
    return len(eventos)


#: Contagens de ``completar_pauta``: as completadas e uma por motivo de não entrar.
CONTAGENS = (
    "acorde",
    "isolado",
    "nao_ligada",
    "nao_harmonico",
    "nao_pausa",
    "nao_cabecalho",
    "nao_oitava",
)
#: Contador de cada motivo de não entrar (rodada 3027, Ajuste 1).
CONTADOR_DO_MOTIVO = {
    "ligada": "nao_ligada",
    "harmonico": "nao_harmonico",
    "pausa": "nao_pausa",
    "cabecalho": "nao_cabecalho",
    "oitava": "nao_oitava",
}


def _oitava_na_pauta(midi: int, x: float | None, eventos: list[dict]) -> bool:
    """Diz se a pauta tem a mesma nota uma oitava acima ou abaixo, no mesmo x.

    Mesma tolerância de ``_candidato_oitava`` (``TOLERANCIA_PX``), nos dois sentidos.

    Args:
        midi: altura escrita da nota da tab.
        x: posição x da coluna da tab.
        eventos: eventos normalizados da pauta (``x`` e ``midis``).

    Returns:
        True se algum evento a até ``TOLERANCIA_PX`` tem ``midi + 12`` ou ``midi - 12``.
    """
    if x is None:
        return False
    return any(
        evento["x"] is not None
        and abs(evento["x"] - x) <= TOLERANCIA_PX
        and (midi + 12 in evento["midis"] or midi - 12 in evento["midis"])
        for evento in eventos
    )


def _motivo_de_nao_entrar(
    nota: dict,
    tab_j: dict,
    normalizados: list[dict],
    pausas_x: list[float],
    primeiro_x: float | None,
) -> str | None:
    """Motivo pelo qual uma nota da tab não entra na pauta, ou None se ela entra.

    Ordem das regras (rodada 3027, Ajuste 1): ligada, harmônico, pausa, cabeçalho e oitava.
    Vale a primeira que se aplica.

    Args:
        nota: nota de ``_completar`` (``midi``, ``x``, ``harmonico``).
        tab_j: evento da tab da nota (``ligadas``).
        normalizados: eventos normalizados da pauta.
        pausas_x: x no quadro das pausas do recorte.
        primeiro_x: x do primeiro evento da pauta (nota ou pausa), ou None.

    Returns:
        ``ligada``, ``harmonico``, ``pausa``, ``cabecalho``, ``oitava`` ou None.
    """
    if nota["midi"] in tab_j["ligadas"]:
        return "ligada"
    oitava = _oitava_na_pauta(nota["midi"], nota["x"], normalizados)
    if nota["harmonico"] and oitava:
        return "harmonico"
    if any(abs(p - nota["x"]) <= TOLERANCIA_PX for p in pausas_x):
        return "pausa"
    if primeiro_x is not None and nota["x"] < primeiro_x - TOLERANCIA_PX:
        return "cabecalho"
    if oitava:
        return "oitava"
    return None


def _voz_isolada(
    midi: int,
    cordas: dict[int, int],
    compasso: str | None,
    vozes_por_compasso: dict[str, set[str]] | None,
) -> str:
    """Voz de uma nota isolada, pela mesma escolha de ``_completar`` (rodada 3027, Ajuste 2).

    Cordas 4 a 6 vão para a voz 2 se o compasso tem duas vozes na leitura herdada; senão, voz 1.

    Args:
        midi: altura escrita da nota.
        cordas: ``{altura escrita: corda}`` da coluna da tab.
        compasso: número do compasso da nota (``_compasso_de_x``), ou None.
        vozes_por_compasso: ``{numero do compasso: vozes das notas e pausas}``, ou None.

    Returns:
        ``"2"`` ou ``"1"``.
    """
    tem_voz2 = (
        compasso is not None
        and vozes_por_compasso is not None
        and "2" in vozes_por_compasso.get(compasso, set())
    )
    return "2" if cordas.get(midi, 0) in CORDAS_VOZ_2 and tem_voz2 else "1"


def completar_pauta(
    eventos: list[dict],
    tab: list[dict],
    compassos: list[dict],
    tela: int,
    pausas: list[tuple[float, str]] | None = None,
    vozes_por_compasso: dict[str, set[str]] | None = None,
) -> tuple[list[dict], dict[str, int], list[dict]]:
    """Acrescenta à pauta as notas da tab que ela não leu (regras da rodada 3172 e 3027).

    Cada evento da tab (uma coluna) entra assim:

    - com evento pareado (``par`` com ``confere_x`` verdadeiro, na mesma ``tela``): as notas
      que faltam entram nesse evento, como símbolos novos no fim de ``simbolos``;
    - sem evento pareado: entra um evento novo, com ``compasso`` de ``_compasso_de_x``,
      ``t`` None, ``x_quadro`` da coluna e ``par`` com ``metodo`` ``tab``. O evento novo
      entra antes do primeiro evento de x maior.

    Regras: a figura é sempre ``None``. Símbolo que já existe não muda. Uma nota da tab
    não entra, e é contada pelo primeiro motivo que se aplica (``_motivo_de_nao_entrar``):
    ``ligada`` (``tecnica`` lig), ``harmonico`` (``tecnica`` harm com oitava na pauta),
    ``pausa`` (nota isolada: pausa a até ``TOLERANCIA_PX`` do x, na mesma voz que a nota
    recebe; o acorde não tem essa regra), ``cabecalho`` (x antes do primeiro
    evento da pauta, nota ou pausa, menos ``TOLERANCIA_PX``) e ``oitava`` (a pauta tem a
    mesma nota uma oitava acima ou abaixo, a até ``TOLERANCIA_PX``).

    Args:
        eventos: eventos da pauta, no formato do documento (``compasso``, ``t``,
            ``x_quadro``, ``par``, ``simbolos``, ``trocadas``). A lista não é alterada.
        tab: eventos da tab na janela do recorte, em ordem de x. Cada um tem ``x``,
            ``coluna``, ``midis`` (alturas escritas), ``cordas`` (altura escrita para
            corda), ``harmonico_tab`` (há nota harm) e ``ligadas`` (alturas escritas das
            notas lig).
        compassos: ``{"numero", "fracao", "x_quadro"}`` do recorte.
        tela: tela do produto (vai no ``par`` dos eventos novos).
        pausas: ``(x no quadro, voz)`` de cada pausa do recorte, da leitura herdada. ``None``
            é lista vazia.
        vozes_por_compasso: ``{numero do compasso: vozes das notas e pausas}``, da leitura
            herdada. Dá a voz da nota isolada (``_voz_isolada``). ``None`` põe todas na voz 1.

    Returns:
        ``(eventos, contagens, motivos)``: a pauta com as notas completadas; ``contagens``
        com as chaves de ``CONTAGENS``; e ``motivos``, uma entrada por nota que não entrou,
        com ``x``, ``midi``, ``tipo``, ``compasso`` e ``motivo``.
    """
    normalizados = []
    for evento in eventos:
        simbolos = _normalizar(evento["simbolos"])
        normalizados.append(
            {
                "compasso": evento["compasso"],
                "x": evento["x_quadro"],
                "simbolos": simbolos,
                "midis": {s["midi"] for s in simbolos},
            }
        )
    pausas_todas = list(pausas or [])
    xs_da_pauta = [e["x"] for e in normalizados if e["x"] is not None] + [
        x for x, _ in pausas_todas
    ]
    primeiro_x = min(xs_da_pauta) if xs_da_pauta else None
    ocupados: dict[int, int] = {}
    for indice, evento in enumerate(eventos):
        par = evento.get("par") or {}
        if par.get("tela") == tela and par.get("confere_x") is True:
            ocupados.setdefault(par["coluna"], indice)
    saida = [{**evento, "simbolos": list(evento["simbolos"])} for evento in eventos]
    novos: list[dict] = []
    contagens = dict.fromkeys(CONTAGENS, 0)
    motivos: list[dict] = []
    for tab_j in tab:
        i = ocupados.get(tab_j["coluna"])
        feitas = _completar(
            [tab_j], normalizados, {} if i is None else {0: i}, compassos, {}
        )
        isolados = []
        for nota in feitas:
            voz = nota["voz"]
            pausas_da_voz: list[float] = []
            if nota["tipo"] == "isolado":
                voz = _voz_isolada(
                    nota["midi"], tab_j["cordas"], nota["compasso"], vozes_por_compasso
                )
                pausas_da_voz = [x for x, v in pausas_todas if v == voz]
            motivo = _motivo_de_nao_entrar(
                nota, tab_j, normalizados, pausas_da_voz, primeiro_x
            )
            if motivo is not None:
                contagens[CONTADOR_DO_MOTIVO[motivo]] += 1
                motivos.append(
                    {
                        "x": nota["x"],
                        "midi": nota["midi"],
                        "tipo": nota["tipo"],
                        "compasso": nota["compasso"],
                        "motivo": motivo,
                    }
                )
                continue
            simbolo = _simbolo_completado(nota["midi"], voz, nota["harmonico"])
            if nota["tipo"] == "acorde":
                saida[i]["simbolos"].append(simbolo)
                contagens["acorde"] += 1
            else:
                isolados.append(simbolo)
                contagens["isolado"] += 1
        if isolados:
            novos.append(
                {
                    "compasso": _compasso_de_x(tab_j["x"], compassos),
                    "t": None,
                    "x_quadro": tab_j["x"],
                    "par": {
                        "tela": tela,
                        "coluna": tab_j["coluna"],
                        "distancia_x": 0.0,
                        "confere_x": True,
                        "metodo": "tab",
                    },
                    "simbolos": isolados,
                    "trocadas": [],
                }
            )
    for novo in novos:
        saida.insert(_posicao_por_x(saida, novo["x_quadro"]), novo)
    return saida, contagens, motivos
