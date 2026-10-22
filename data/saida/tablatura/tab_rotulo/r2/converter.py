"""Converte as marcas de técnica do dono (regiões) em rótulo de ataque por nota.

R2, passo 1 (só máquina). Lê as telas conferidas do ouro e da T8.2, aplica a regra
do arco pelos números (seção 3 do plano e ``configs/simbolos.yaml``) e grava um
``ataque_<fonte>.json`` por fonte e um ``resumo.json``. Não escreve em ``data/gold``.

Regras desta versão:
- legato e slide: por corda da região, as notas são as que caem em [x0, x1] mais a
  vizinha mais próxima à esquerda de x0 e à direita de x1, desde que a vizinha esteja
  a no máximo 1 passo da borda. O passo é a mediana da distância vertical entre cordas
  consecutivas da tela (caixas das notas não removidas do bloco ``ferramenta``).
- X: só nota com casa ``x`` recebe motivo ``x``; nota numérica sob X vira ambíguo.

Uso (container): python data/saida/tab_rotulo/r2/converter.py
"""

import json
import random
from collections import Counter
from pathlib import Path
from statistics import median

RAIZ = Path(__file__).resolve().parents[4]
SAIDA = Path(__file__).resolve().parent
OURO = RAIZ / "data" / "gold" / "ouro_video"

FONTES = {
    "end_of_beginning": OURO / "end_of_beginning_djo_fingerstyle_guitar_tab_chords_lyrics.json",
    "tabroom_335": OURO / "tabroom_335_larry_carlton_fingerstyle_guitar.json",
    "pat_metheny": OURO / "tab_from_this_place_pat_metheny_fingerstyle_guitar_cover.json",
    "la_vie_en_rose": OURO / "la_vie_en_rose_edith_piaf_tab.json",
    "t82": RAIZ / "data" / "saida" / "t82" / "ferramenta" / "conferencia_t82.json",
}

# fontes em que tela conferida sem região quer dizer "sem técnica" (dono, 2026-10-17:
# "la vie en rose não tem técnicas marcadas"); nas outras, tela sem região fica fora.
SEM_REGIAO_E_SEM_TECNICA = {"la_vie_en_rose"}

# fontes com a regra da ligadura de uma nota só (dono, 2026-10-22): "quando não há
# segundo número em uma ligadura é a mesma coisa que quando tem dois números considere
# o primeiro como atacado". O número sozinho sob o arco de prolongamento é atacado
# (``sustentada``), de qualquer lado do arco. Nas fontes antigas vale o lado do arco.
PROLONGAMENTO_UMA_NOTA_ATACADA: set[str] = set()

CAMPO_X = "x_centro_quadro"
SEMENTE_AMOSTRA = 0

# obs que dizem legato (arco de ligadura, prolongamento, slide sem símbolo).
OBS_PROLONGAMENTO = {
    "arco prolongamento",
    "ligadura de prolongamento",
    "ligadura de prolongação",
}

OBS_LEGATO = {
    "arco prolongamento",
    "ligadura de prolongamento",
    "ligadura de prolongação",
    "legato",
    "arco legato",
    "arco de ligadura",
    "mordente",
    "ligadura slide",
    "legato slide",
    "legato em cima do slide serve pra dizer que nao deve palhetar de novo as cordas",
}
# obs que são notação ou ornamento fora do escopo (ignorados, mas contados).
OBS_IGNORAR = {
    "colcheia",
    "semi-colcheia",
    "semibreve",
    "compasso",
    "compasso - sempre no inicio da tablatura ou da partitura",
    "ritornelo",
    "bend release",
}
# obs de legato que NÃO têm símbolo de slide na tecnica: tratados como legato, com ressalva.
OBS_SLIDE_SEM_SIMBOLO = {
    "ligadura slide",
    "legato em cima do slide serve pra dizer que nao deve palhetar de novo as cordas",
}
TECNICAS_IGNORAR = {"arpejo", "rasg", "bend"}
PRIORIDADE = {"x": 0, "harm": 1, "slide": 2, "legato": 3}


def classificar(regiao: dict) -> str:
    """Diz o tipo de uma região pela tecnica e pelo obs.

    Args:
        regiao: dict com ``tecnica`` (lista) e, opcionalmente, ``obs``.

    Returns:
        Um de ``x``, ``harm``, ``slide``, ``ignorar``, ``legato`` ou ``ambiguo_obs``.
    """
    tec = set(regiao["tecnica"])
    obs = regiao.get("obs")
    if "x" in tec:
        return "x"
    if "harm" in tec:
        return "harm"
    if tec & {"/", "\\"}:
        return "slide"
    if tec & TECNICAS_IGNORAR or obs in OBS_IGNORAR:
        return "ignorar"
    if tec & {"h", "p"} or obs in OBS_LEGATO:
        return "legato"
    return "ambiguo_obs"


def cobre(regiao: dict, nota: dict) -> bool:
    """Diz se a nota cai dentro da região (cordas e x de centro).

    Args:
        regiao: região com ``cordas`` [a, b] e ``x_quadro`` [x0, x1].
        nota: nota com ``corda`` e ``x_centro_quadro``.

    Returns:
        True se a corda está em [min, max] e o x de centro está em [x0, x1].
    """
    lo, hi = min(regiao["cordas"]), max(regiao["cordas"])
    x0, x1 = regiao["x_quadro"]
    return lo <= nota["corda"] <= hi and x0 <= nota[CAMPO_X] <= x1


def numerica(casa: object) -> bool:
    """Diz se a casa é um número (x não é).

    Args:
        casa: valor da casa.

    Returns:
        True se ``casa`` converte para inteiro.
    """
    try:
        int(casa)
    except (TypeError, ValueError):
        return False
    return True


def motivo_par(anterior: object, atual: object) -> str:
    """Motivo de uma nota de legato em relação à anterior, pelos números.

    Args:
        anterior: casa da nota anterior (número).
        atual: casa da nota atual (número).

    Returns:
        ``prolongamento`` se iguais, ``h`` se a atual é maior, ``p`` se menor.
    """
    a, b = int(anterior), int(atual)
    if a == b:
        return "prolongamento"
    return "h" if b > a else "p"


def passo_da_tela(ferr_tela: dict | None) -> float | None:
    """Passo (distância vertical entre cordas) de uma tela, pelas caixas das notas.

    Usa a posição vertical do centro da caixa de cada nota não removida do bloco
    ``ferramenta``; por corda, a mediana; o passo é a mediana das diferenças entre
    cordas consecutivas.

    Args:
        ferr_tela: a tela no bloco ``ferramenta`` da fonte (ou None).

    Returns:
        Passo em px, ou None se não há caixas suficientes.
    """
    if not ferr_tela:
        return None
    ys: dict[int, list[float]] = {}
    for n in ferr_tela["notas"]:
        if n.get("removida") or "caixa" not in n:
            continue
        ys.setdefault(n["corda"], []).append((n["caixa"][1] + n["caixa"][3]) / 2)
    centros = {c: median(v) for c, v in ys.items()}
    difs = [centros[c + 1] - centros[c] for c in sorted(centros) if c + 1 in centros]
    return float(median(difs)) if difs else None


def grupos_da_regiao(notas: list[dict], regiao: dict,
                     passo: float) -> list[tuple[int, list[int]]]:
    """Notas de uma região de legato/slide, por corda, com as vizinhas nas pontas.

    Para cada corda da região: as notas com x de centro em [x0, x1], mais a vizinha
    mais próxima à esquerda de x0 e a mais próxima à direita de x1, se cada uma
    estiver a no máximo ``passo`` da borda.

    Args:
        notas: notas da tela.
        regiao: região com ``cordas`` e ``x_quadro``.
        passo: passo da tela em px.

    Returns:
        Lista de (corda, índices ordenados por x), só para cordas com alguma nota.
    """
    lo, hi = min(regiao["cordas"]), max(regiao["cordas"])
    x0, x1 = regiao["x_quadro"]
    saida = []
    for c in range(lo, hi + 1):
        idxs = [k for k, n in enumerate(notas) if n["corda"] == c]
        grupo = [k for k in idxs if x0 <= notas[k][CAMPO_X] <= x1]
        esq = [k for k in idxs if notas[k][CAMPO_X] < x0]
        dir_ = [k for k in idxs if notas[k][CAMPO_X] > x1]
        if esq:
            e = max(esq, key=lambda k: notas[k][CAMPO_X])
            if x0 - notas[e][CAMPO_X] <= passo:
                grupo.append(e)
        if dir_:
            d = min(dir_, key=lambda k: notas[k][CAMPO_X])
            if notas[d][CAMPO_X] - x1 <= passo:
                grupo.append(d)
        if grupo:
            saida.append((c, sorted(grupo, key=lambda k: notas[k][CAMPO_X])))
    return saida


def novo_resumo() -> dict:
    """Cria o acumulador de contagens de uma fonte.

    Returns:
        dict com contadores zerados e listas vazias.
    """
    return {
        "regioes_lidas": 0,
        "regioes_em_telas_conferidas": 0,
        "regioes_por_tipo": Counter(),
        "regioes_ignoradas": Counter(),
        "telas_conferidas": 0,
        "telas_com_marca": 0,
        "telas_sem_marca": 0,
        "notas_conferidas": 0,
        "notas_sem_marca": 0,
        "notas_rotuladas": 0,
        "motivos": Counter(),
        "ataques": Counter(),
        "ambiguos": [],
        "obs_nao_classificados": Counter(),
        "obs_slide_sem_simbolo": [],
        "x_regioes": 0,
        "x_sem_nota_x": 0,
        "x_sem_nota_alguma": 0,
        "x_cobre_digito": 0,
        "conflitos": [],
        "sobreposicoes": 0,
        "telas_divergem_ferramenta": [],
        "passo_por_tela": {},
        "passo_fallback_telas": [],
    }


def chave(tela: dict, idx: int) -> str:
    """Chave estável de uma nota: tela e posição na lista da tela.

    Args:
        tela: a tela.
        idx: posição da nota em ``tela["notas"]``.

    Returns:
        Texto ``t<tela>-n<idx>``.
    """
    return f"t{tela['id']}-n{idx}"


def registrar_ambiguo(res: dict, tipo: str, tela: dict, rid: str, regiao: dict,
                      cob: list[int]) -> None:
    """Anota uma região (ou corda dela) ambígua, sem rotular.

    Args:
        res: acumulador da fonte.
        tipo: nome do tipo de ambiguidade.
        tela: tela onde está a região.
        rid: id da região.
        regiao: a região.
        cob: índices das notas envolvidas.
    """
    res["ambiguos"].append({
        "tipo": tipo,
        "tela": tela["id"],
        "regiao": rid,
        "cordas": regiao["cordas"],
        "x_quadro": regiao["x_quadro"],
        "tecnica": regiao["tecnica"],
        "obs": regiao.get("obs"),
        "notas": [chave(tela, k) for k in cob],
    })


def rotular_tela(
    tela: dict, passo: float, res: dict, uma_nota_atacada: bool = False
) -> dict[int, tuple[str, str, str | None]]:
    """Rotula as notas de uma tela conferida a partir das suas regiões.

    Args:
        tela: tela com ``notas`` e ``regioes``.
        passo: passo da tela em px (para as vizinhas de legato e slide).
        res: acumulador da fonte (é atualizado).
        uma_nota_atacada: a regra de ``PROLONGAMENTO_UMA_NOTA_ATACADA``.

    Returns:
        Mapa índice da nota -> (ataque, motivo, id da região ou None).
    """
    notas = tela["notas"]
    regioes = tela.get("regioes") or []
    res["notas_conferidas"] += len(notas)
    if not regioes:
        res["telas_sem_marca"] += 1
        res["notas_sem_marca"] += len(notas)
        return {}
    res["telas_com_marca"] += 1
    reivindicacoes: dict[int, list[tuple[int, str, str, str]]] = {}
    ambiguas: set[int] = set()
    informativos: dict[int, tuple[str, str]] = {}
    for i, regiao in enumerate(regioes):
        rid = f"t{tela['id']}-r{i}"
        tipo = classificar(regiao)
        cob = [k for k, n in enumerate(notas) if cobre(regiao, n)]
        res["regioes_por_tipo"][tipo] += 1
        if regiao.get("obs") == "mordente" and not set(regiao["tecnica"]) & {"h", "p"}:
            # mordente desenhado como símbolo (zigue-zague) sobre uma nota só (dono,
            # 2026-10-17): a nota escrita é atacada; as do enfeite saem ligadas e não
            # estão na tab. O símbolo fica em cima: vale a corda dele ou a de baixo.
            x0, x1 = regiao["x_quadro"]
            meio = (x0 + x1) / 2
            c0, c1 = min(regiao["cordas"]), max(regiao["cordas"])
            for c in range(c0, c1 + 2):
                cand = [k for k, n in enumerate(notas) if n["corda"] == c
                        and x0 - 0.3 * passo <= n["x_centro_quadro"] <= x1 + 0.3 * passo]
                if cand:
                    k = min(cand, key=lambda k: abs(notas[k]["x_centro_quadro"] - meio))
                    # informação: se a nota chega por h/p/ligadura, ela segue sem ataque.
                    informativos.setdefault(k, ("mordente_simbolo", rid))
                    res["mordente_simbolo"] = res.get("mordente_simbolo", 0) + 1
                    break
            else:
                registrar_ambiguo(res, "mordente_sem_nota", tela, rid, regiao, [])
            continue
        if tipo == "ignorar":
            res["regioes_ignoradas"][f"{regiao['tecnica']}|{regiao.get('obs')}"] += 1
            # rasgueado e arpejo: a nota é atacada; o tipo fica como informação
            # (dono, 2026-10-17). Só vale onde nenhuma outra região reivindicou.
            tec = set(regiao["tecnica"])
            info = "rasgueado" if "rasg" in tec else "arpejo" if "arpejo" in tec else None
            if info:
                # o símbolo fica logo à esquerda do acorde: as notas são as da coluna
                # imediatamente à direita da região (até 1 passo), nas cordas dela.
                x0, x1 = regiao["x_quadro"]
                c0, c1 = min(regiao["cordas"]), max(regiao["cordas"])
                xs = [n["x_centro_quadro"] for n in notas if n["x_centro_quadro"] > x1]
                cob = []
                if xs and min(xs) - x1 <= passo:
                    xd = min(xs)
                    cob = [k for k, n in enumerate(notas)
                           if abs(n["x_centro_quadro"] - xd) <= 0.3 * passo
                           and c0 <= n["corda"] <= c1]
                if cob:
                    # por eliminação (dono, 2026-10-17): corda sem nota marcada entre a
                    # de cima e a de baixo do acorde ganha a nota dela na mesma coluna
                    # (até meio passo). O símbolo só cobre as cordas da técnica.
                    cordas = [notas[k]["corda"] for k in cob]
                    for c in range(min(cordas) + 1, max(cordas)):
                        if c in cordas:
                            continue
                        cand = [k for k, n in enumerate(notas) if n["corda"] == c
                                and abs(n["x_centro_quadro"] - xd) <= 0.5 * passo]
                        if cand:
                            cob.append(min(cand, key=lambda k: abs(
                                notas[k]["x_centro_quadro"] - xd)))
                            res["acorde_por_eliminacao"] = (
                                res.get("acorde_por_eliminacao", 0) + 1)
                if not cob:
                    registrar_ambiguo(res, f"{info}_sem_nota", tela, rid, regiao, [])
                for k in cob:
                    informativos.setdefault(k, (info, rid))
            continue
        if tipo == "ambiguo_obs":
            res["obs_nao_classificados"][str(regiao.get("obs"))] += 1
            registrar_ambiguo(res, "obs_nao_classificado", tela, rid, regiao, cob)
            ambiguas.update(cob)
            continue
        if tipo == "x":
            res["x_regioes"] += 1
            tem_x = [k for k in cob if str(notas[k]["casa"]).lower() == "x"]
            numericas = [k for k in cob if numerica(notas[k]["casa"])]
            if not cob:
                res["x_sem_nota_alguma"] += 1
            if not tem_x:
                res["x_sem_nota_x"] += 1
            if numericas:
                res["x_cobre_digito"] += 1
                registrar_ambiguo(res, "x_sobre_numero", tela, rid, regiao, numericas)
                ambiguas.update(numericas)
            for k in tem_x:
                reivindicacoes.setdefault(k, []).append((0, "sim", "x", rid))
            continue
        if tipo == "harm":
            if not cob:
                registrar_ambiguo(res, "harmonico_sem_nota", tela, rid, regiao, cob)
                continue
            for k in cob:
                reivindicacoes.setdefault(k, []).append((1, "sim", "harmonico", rid))
            continue
        # legato e slide: por corda, com as vizinhas nas pontas.
        grupos = grupos_da_regiao(notas, regiao, passo)
        if not grupos and max(regiao["cordas"]) < 6:
            # o arco fica ACIMA das notas: a caixa do dono pode cair só na corda de
            # cima. Sem nota na corda dela, tenta a corda logo abaixo (2026-10-17).
            abaixo = dict(regiao, cordas=[c + 1 for c in regiao["cordas"]])
            grupos = grupos_da_regiao(notas, abaixo, passo)
            if grupos:
                res["arco_corda_abaixo"] = res.get("arco_corda_abaixo", 0) + 1
        if not grupos and min(regiao["cordas"]) > 1:
            # arco ABAIXO das notas: a caixa cai na corda de baixo. Tenta a corda logo
            # acima (T8.2 t16, t23, t31; dono, 2026-10-18).
            acima = dict(regiao, cordas=[c - 1 for c in regiao["cordas"]])
            grupos = grupos_da_regiao(notas, acima, passo)
            if grupos:
                res["arco_corda_acima"] = res.get("arco_corda_acima", 0) + 1
        if not grupos:
            registrar_ambiguo(res, f"{tipo}_sem_nota", tela, rid, regiao, [])
            continue
        if tipo == "legato" and regiao.get("obs") in OBS_SLIDE_SEM_SIMBOLO:
            res["obs_slide_sem_simbolo"].append(rid)
        for _, ordem in grupos:
            if len(ordem) == 1:
                # uma nota só: o lado dela diz o caso (dono, 2026-10-17).
                k = ordem[0]
                meio = sum(regiao["x_quadro"]) / 2
                a_esquerda = notas[k][CAMPO_X] < meio
                prolonga = regiao.get("obs") in OBS_PROLONGAMENTO
                if tipo == "slide":
                    # sai deslizando: a nota é tocada; entra deslizando: slide_entrada.
                    motivo = "normal" if a_esquerda else "slide_entrada"
                    reivindicacoes.setdefault(k, []).append((2, "sim", motivo, rid))
                    continue
                if prolonga:
                    # arco da nota para o vazio: tocada e deixada soando; do vazio
                    # para a nota: continuação de uma nota anterior, sem ataque.
                    if a_esquerda or uma_nota_atacada:
                        if not a_esquerda:
                            res["uma_nota_atacada"] = res.get("uma_nota_atacada", 0) + 1
                        reivindicacoes.setdefault(k, []).append((3, "sim", "sustentada", rid))
                    else:
                        reivindicacoes.setdefault(k, []).append((3, "nao", "prolongamento", rid))
                    continue
            if len(ordem) < 2:
                registrar_ambiguo(res, f"{tipo}_uma_nota", tela, rid, regiao, ordem)
                ambiguas.update(ordem)
                continue
            if tipo == "legato" and not all(numerica(notas[k]["casa"]) for k in ordem):
                registrar_ambiguo(res, "legato_casa_nao_numerica", tela, rid, regiao, ordem)
                ambiguas.update(ordem)
                continue
            if tipo == "slide":
                for pos, k in enumerate(ordem):
                    if pos == 0:
                        reivindicacoes.setdefault(k, []).append((2, "sim", "normal", rid))
                    else:
                        reivindicacoes.setdefault(k, []).append((2, "nao", "slide_ligado", rid))
                continue
            for pos, k in enumerate(ordem):
                if pos == 0:
                    reivindicacoes.setdefault(k, []).append((3, "sim", "normal", rid))
                elif len(ordem) >= 3:
                    reivindicacoes.setdefault(k, []).append((3, "nao", "mordente", rid))
                else:
                    motivo = motivo_par(notas[ordem[pos - 1]]["casa"], notas[k]["casa"])
                    reivindicacoes.setdefault(k, []).append((3, "nao", motivo, rid))
    rotulos: dict[int, tuple[str, str, str | None]] = {}
    for k, lista in reivindicacoes.items():
        if k in ambiguas:
            continue
        ataques = {a for _, a, _, _ in lista}
        # nota no meio de uma corrente (fim de um arco/slide e começo do próximo):
        # o "sim" de começo de arco cede ao "nao" de chegada (dono, 2026-10-17).
        if ataques == {"sim", "nao"} and all(
            m in ("normal", "sustentada") for _, a, m, _ in lista if a == "sim"
        ):
            lista = [c for c in lista if c[1] == "nao"]
            ataques = {"nao"}
            res["correntes"] = res.get("correntes", 0) + 1
        if len(ataques) > 1:
            res["conflitos"].append({"tela": tela["id"], "nota": chave(tela, k),
                                     "claims": [list(c) for c in lista]})
            ambiguas.add(k)
            continue
        if len(lista) > 1:
            res["sobreposicoes"] += 1
        _, ataque, motivo, rid = min(lista, key=lambda c: c[0])
        rotulos[k] = (ataque, motivo, rid)
    for k in range(len(notas)):
        if k in rotulos or k in ambiguas:
            continue
        if k in informativos:
            motivo, rid = informativos[k]
            rotulos[k] = ("sim", motivo, rid)
            continue
        rotulos[k] = ("sim", "normal", None)
    return rotulos


def divergencia(dados: dict) -> list[int]:
    """Telas em que as notas de ``telas`` diferem das de ``ferramenta`` (sem removidas).

    Args:
        dados: JSON da fonte.

    Returns:
        Ids das telas divergentes.
    """
    ferr = {t["id"]: t for t in dados["ferramenta"]["telas"]}
    saida = []

    def assinatura(n: dict) -> str:
        return str((n["corda"], str(n["casa"]), round(float(n["x_quadro"]), 1)))

    for tela in dados["telas"]:
        f = ferr.get(tela["id"])
        if f is None:
            continue
        a = sorted(assinatura(n) for n in tela["notas"])
        b = sorted(assinatura(n) for n in f["notas"] if not n.get("removida"))
        if a != b:
            saida.append(tela["id"])
    return saida


def vizinhas_mesma_corda(tela: dict) -> dict[int, tuple[object, object]]:
    """Casa da nota imediatamente à esquerda e à direita, na mesma corda da tela.

    Args:
        tela: a tela.

    Returns:
        Mapa índice -> (casa esquerda ou None, casa direita ou None).
    """
    notas = tela["notas"]
    saida: dict[int, tuple[object, object]] = {}
    for k, n in enumerate(notas):
        mesma = sorted((m for m in notas if m["corda"] == n["corda"]), key=lambda m: m[CAMPO_X])
        pos = next(i for i, m in enumerate(mesma) if m is n)
        esq = mesma[pos - 1]["casa"] if pos > 0 else None
        dir_ = mesma[pos + 1]["casa"] if pos + 1 < len(mesma) else None
        saida[k] = (esq, dir_)
    return saida


def processar_fonte(nome: str, caminho: Path) -> tuple[dict, dict]:
    """Processa uma fonte e devolve o JSON de notas e o resumo.

    Args:
        nome: nome curto da fonte.
        caminho: arquivo JSON da fonte (só leitura).

    Returns:
        (dict do ``ataque_<nome>.json``, dict do resumo da fonte).
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    res = novo_resumo()
    res["telas_divergem_ferramenta"] = divergencia(dados)
    ferr = {t["id"]: t for t in dados["ferramenta"]["telas"]}
    passos_validos = [p for p in (passo_da_tela(t) for t in ferr.values()) if p]
    passo_global = float(median(passos_validos))
    notas_saida = []
    for tela in dados["telas"]:
        res["regioes_lidas"] += len(tela.get("regioes") or [])
        if not tela.get("conferida"):
            continue
        res["telas_conferidas"] += 1
        res["regioes_em_telas_conferidas"] += len(tela.get("regioes") or [])
        passo = passo_da_tela(ferr.get(tela["id"]))
        if passo is None:
            passo = passo_global
            res["passo_fallback_telas"].append(tela["id"])
        res["passo_por_tela"][str(tela["id"])] = round(passo, 2)
        rotulos = rotular_tela(
            tela, passo, res, uma_nota_atacada=nome in PROLONGAMENTO_UMA_NOTA_ATACADA
        )
        if not tela.get("regioes") and nome in SEM_REGIAO_E_SEM_TECNICA:
            rotulos = {k: ("sim", "normal", None) for k in range(len(tela["notas"]))}
            res["telas_sem_tecnica"] = res.get("telas_sem_tecnica", 0) + 1
        vizinhas = vizinhas_mesma_corda(tela)
        for k, nota in enumerate(tela["notas"]):
            if k not in rotulos:
                continue
            ataque, motivo, rid = rotulos[k]
            res["notas_rotuladas"] += 1
            res["motivos"][motivo] += 1
            res["ataques"][ataque] += 1
            notas_saida.append({
                "nota": chave(tela, k),
                "tela": tela["id"],
                "corda": nota["corda"],
                "casa": nota["casa"],
                CAMPO_X: nota[CAMPO_X],
                "casa_vizinha_esq": vizinhas[k][0],
                "casa_vizinha_dir": vizinhas[k][1],
                "ataque": ataque,
                "motivo": motivo,
                "regiao": rid,
            })
    saida = {
        "fonte": nome,
        "origem": str(caminho.relative_to(RAIZ)),
        "campo_x": CAMPO_X,
        "passo_global": round(passo_global, 2),
        "notas": notas_saida,
    }
    return saida, serializar(res)


def serializar(res: dict) -> dict:
    """Converte o acumulador em dict JSON (Counters viram dict ordenado).

    Args:
        res: acumulador da fonte.

    Returns:
        dict pronto para ``json.dumps``.
    """
    saida = {}
    for k, v in res.items():
        if isinstance(v, Counter):
            saida[k] = dict(sorted(v.items(), key=lambda kv: str(kv[0])))
        else:
            saida[k] = v
    saida["ambiguos_por_tipo"] = dict(
        sorted(Counter(a["tipo"] for a in res["ambiguos"]).items())
    )
    saida["nao"] = res["ataques"].get("nao", 0)
    return saida


def amostra_nao(todas: list[tuple[str, dict]], semente: int, n: int) -> list[dict]:
    """Sorteia notas ``nao`` com semente fixa, para conferência do dono.

    Args:
        todas: pares (fonte, linha de nota) com ``ataque == "nao"``.
        semente: semente do sorteio.
        n: quantas notas sortear.

    Returns:
        Lista de dicts com fonte, tela, corda, casas vizinhas, casa e motivo.
    """
    ordenadas = sorted(todas, key=lambda p: (p[0], p[1]["tela"], p[1]["nota"]))
    escolhidas = random.Random(semente).sample(ordenadas, min(n, len(ordenadas)))
    return [
        {
            "fonte": f,
            "nota": r["nota"],
            "tela": r["tela"],
            "corda": r["corda"],
            "casa_vizinha_esq": r["casa_vizinha_esq"],
            "casa": r["casa"],
            "casa_vizinha_dir": r["casa_vizinha_dir"],
            "motivo": r["motivo"],
            "regiao": r["regiao"],
        }
        for f, r in escolhidas
    ]


def main() -> None:
    """Roda todas as fontes e grava os arquivos de saída."""
    resumo = {"campo_x": CAMPO_X, "passo": "mediana das distancias entre cordas consecutivas "
              "(caixas das notas nao removidas do bloco ferramenta, por tela)",
              "fontes": {}}
    todas_nao: list[tuple[str, dict]] = []
    for nome, caminho in FONTES.items():
        ataque, res = processar_fonte(nome, caminho)
        (SAIDA / f"ataque_{nome}.json").write_text(
            json.dumps(ataque, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        resumo["fontes"][nome] = res
        todas_nao += [(nome, r) for r in ataque["notas"] if r["ataque"] == "nao"]
    resumo["amostra_nao_seed0"] = amostra_nao(todas_nao, SEMENTE_AMOSTRA, 10)
    (SAIDA / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
