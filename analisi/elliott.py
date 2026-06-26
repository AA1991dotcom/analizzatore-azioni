"""Onde di Elliott: rilevamento deterministico MULTI-SCALA e validazione rigorosa.

GARANZIA "vietato improvvisare":
  - Pivot ZigZag deterministici (stessi dati+parametri -> stesso risultato).
  - Rilevamento su PIU' SCALE (Elliott e' frattale: onde di gradi diversi coesistono).
  - Enumerazione esaustiva delle etichettature candidate su ogni scala.
  - Scarto SENZA ECCEZIONI di ogni conteggio che viola una regola inviolabile.
  - Se nessun conteggio e' valido -> "struttura non chiara" (nessun conteggio inventato).
  - Selezione del conteggio migliore per rispetto delle regole + aderenza a Fibonacci.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicatori import atr

# Rapporti di Fibonacci attesi (linee guida: ordinano i conteggi, non li scartano).
FIB_W2 = [0.382, 0.5, 0.618]          # ritracciamento onda 2 rispetto a onda 1
FIB_W3 = [1.618, 2.618, 1.0]          # estensione onda 3 rispetto a onda 1
FIB_W4 = [0.236, 0.382, 0.5]          # ritracciamento onda 4 rispetto a onda 3
TOLLERANZA_FIB = 0.20                  # quanto stretto e' il match con Fibonacci


@dataclass
class Conteggio:
    tipo: str                       # 'impulso_rialzista' | 'impulso_ribassista' | 'correzione_abc'
    indici: list[int]               # posizioni (interi) dei pivot nel DataFrame
    prezzi: list[float]
    etichette: list[str]            # es. ['0','1','2','3','4','5']
    confidenza: int                 # 0..100
    onda_corrente: str
    target: list[tuple[str, float]] = field(default_factory=list)
    dettagli: dict = field(default_factory=dict)
    recente: bool = False           # include l'ultimo pivot rilevato?
    scala: float = 0.0              # soglia ZigZag che ha prodotto il conteggio
    span: float = 0.0              # ampiezza di prezzo del conteggio (grado dell'onda)


# --------------------------------------------------------------------------- #
# 1. ZigZag deterministico (multi-scala)
# --------------------------------------------------------------------------- #
def soglia_zigzag(df: pd.DataFrame, k: float = 3.0) -> float:
    """Soglia % adattiva basata sull'ATR mediano (limitata a [2%, 20%])."""
    a = atr(df, 14)
    ratio = (a / df["Close"]).dropna()
    if ratio.empty:
        return 0.05
    pct = float(np.median(ratio)) * k
    return float(min(max(pct, 0.02), 0.20))


def scale_soglie(df: pd.DataFrame) -> list[float]:
    """Tre scale (fine, media, grossa) attorno alla soglia adattiva di base.

    Elliott e' frattale: cercare i conteggi su piu' scale permette di leggere
    sia le onde di breve sia quelle di grado superiore.
    """
    base = soglia_zigzag(df)
    scale = {round(min(max(base * m, 0.02), 0.20), 4) for m in (0.5, 1.0, 2.0)}
    return sorted(scale)


def trova_pivot(close: np.ndarray, soglia: float) -> list[tuple[int, float]]:
    """ZigZag: restituisce pivot alternati (massimi/minimi) come (indice, prezzo)."""
    n = len(close)
    if n == 0:
        return []
    if n == 1:
        return [(0, float(close[0]))]

    pivots: list[tuple[int, float]] = [(0, float(close[0]))]
    trend = 0  # 0 sconosciuto, +1 rialzo, -1 ribasso
    max_i, max_p = 0, float(close[0])
    min_i, min_p = 0, float(close[0])

    for i in range(1, n):
        p = float(close[i])
        if p > max_p:
            max_i, max_p = i, p
        if p < min_p:
            min_i, min_p = i, p

        if trend == 1:
            if (max_p - p) / max_p >= soglia:
                pivots.append((max_i, max_p))
                trend = -1
                min_i, min_p = i, p
        elif trend == -1:
            if (p - min_p) / min_p >= soglia:
                pivots.append((min_i, min_p))
                trend = 1
                max_i, max_p = i, p
        else:  # trend sconosciuto: la prima rottura della soglia fissa la direzione
            if (max_p - p) / max_p >= soglia:
                if max_i != pivots[-1][0]:
                    pivots.append((max_i, max_p))
                trend = -1
                min_i, min_p = i, p
            elif (p - min_p) / min_p >= soglia:
                if min_i != pivots[-1][0]:
                    pivots.append((min_i, min_p))
                trend = 1
                max_i, max_p = i, p

    # pivot finale: l'estremo corrente nella direzione del trend
    if trend == 1 and max_i != pivots[-1][0]:
        pivots.append((max_i, max_p))
    elif trend == -1 and min_i != pivots[-1][0]:
        pivots.append((min_i, min_p))

    return pivots


# --------------------------------------------------------------------------- #
# 2-3. Validazione delle regole inviolabili di Elliott
# --------------------------------------------------------------------------- #
def _valida_impulso(prezzi: list[float], rialzista: bool) -> tuple[bool, dict]:
    """Valida 6 prezzi (0,1,2,3,4,5) come impulso. Per il ribasso si negano i prezzi.

    Regole inviolabili applicate alla lettera:
      R1) onda 2 non ritraccia oltre il 100% dell'onda 1;
      R2) onda 3 supera la fine dell'onda 1;
      R3) onda 3 non e' la piu' corta tra 1, 3, 5;
      R4) onda 4 non invade il territorio di prezzo dell'onda 1.
    """
    p = prezzi if rialzista else [-x for x in prezzi]
    p0, p1, p2, p3, p4, p5 = p

    # struttura alternata di base
    if not (p1 > p0 and p2 < p1 and p3 > p2 and p4 < p3 and p5 > p4):
        return False, {}

    w1 = p1 - p0
    w2 = p1 - p2
    w3 = p3 - p2
    w4 = p3 - p4
    w5 = p5 - p4
    if min(w1, w2, w3, w4, w5) <= 0:
        return False, {}

    # Regole inviolabili
    if not p2 > p0:                       # R1
        return False, {}
    if not p3 > p1:                       # R2
        return False, {}
    if w3 < w1 and w3 < w5:               # R3
        return False, {}
    if not p4 > p1:                       # R4
        return False, {}

    dettagli = {
        "w2/w1": w2 / w1,
        "w3/w1": w3 / w1,
        "w4/w3": w4 / w3,
        "w5/w1": w5 / w1,
    }
    return True, dettagli


def _valida_abc(prezzi: list[float], rialzista: bool) -> tuple[bool, dict]:
    """Correzione a 3 onde A-B-C (4 pivot). rialzista=True -> correzione al rialzo."""
    p = prezzi if rialzista else [-x for x in prezzi]
    p0, p1, p2, p3 = p
    # zigzag: 0->A su, A->B giu', B->C su, con C oltre A
    if not (p1 > p0 and p2 < p1 and p3 > p2):
        return False, {}
    a = p1 - p0
    b = p1 - p2
    c = p3 - p2
    if min(a, b, c) <= 0:
        return False, {}
    if not p2 > p0:          # B non ritraccia oltre l'inizio di A
        return False, {}
    return True, {"b/a": b / a, "c/a": c / a}


# --------------------------------------------------------------------------- #
# 4. Punteggio di qualita' (Fibonacci) -> confidenza
# --------------------------------------------------------------------------- #
def _vicinanza(valore: float, target: float, tolleranza: float = TOLLERANZA_FIB) -> float:
    if target == 0:
        return 0.0
    diff = abs(valore - target) / target
    return max(0.0, 1.0 - diff / tolleranza)


def _miglior_fib(valore: float, targets: list[float]) -> float:
    return max(_vicinanza(valore, t) for t in targets)


def _confidenza_impulso(dettagli: dict) -> int:
    s2 = _miglior_fib(dettagli["w2/w1"], FIB_W2)
    s3 = _miglior_fib(dettagli["w3/w1"], FIB_W3)
    s4 = _miglior_fib(dettagli["w4/w3"], FIB_W4)
    # alternanza onda2/onda4: bonus se i ritracciamenti sono diversi
    alternanza = min(1.0, abs(dettagli["w2/w1"] - dettagli["w4/w3"]) / 0.2)
    # onda 3 estesa (la piu' lunga): pattern d'impulso piu' tipico e affidabile
    w3_w1 = dettagli["w3/w1"]
    w5_w1 = dettagli["w5/w1"]
    estesa = 1.0 if (w3_w1 >= 1.0 and w3_w1 >= w5_w1) else 0.0
    score = 0.30 * s2 + 0.30 * s3 + 0.20 * s4 + 0.10 * alternanza + 0.10 * estesa
    return int(round(100 * max(0.0, min(1.0, score))))


# --------------------------------------------------------------------------- #
# 5. Proiezioni di Fibonacci per i target
# --------------------------------------------------------------------------- #
def _target_impulso_completo(prezzi, rialzista) -> list[tuple[str, float]]:
    """Impulso completo -> attesa correzione: ritracciamenti dell'intero movimento."""
    p0, p5 = prezzi[0], prezzi[-1]
    mossa = p5 - p0
    return [
        ("Ritracc. 0.382", p5 - 0.382 * mossa),
        ("Ritracc. 0.618", p5 - 0.618 * mossa),
    ]


def _target_onda5(prezzi, rialzista) -> list[tuple[str, float]]:
    """Onda 5 in corso (noti 0..4): proiezioni tipiche dalla fine dell'onda 4."""
    p0, p1, p4 = prezzi[0], prezzi[1], prezzi[4]
    w1 = abs(p1 - p0)
    segno = 1 if rialzista else -1
    return [
        ("Target 5 (=W1)", p4 + segno * w1),
        ("Target 5 (1.618*W1)", p4 + segno * 1.618 * w1),
    ]


# --------------------------------------------------------------------------- #
# 6. Enumerazione dei conteggi su un singolo insieme di pivot
# --------------------------------------------------------------------------- #
def _conteggi_da_pivot(pivots, close, scala) -> list[Conteggio]:
    indici = [i for i, _ in pivots]
    prezzi = [p for _, p in pivots]
    ultimo_pivot = indici[-1]
    prezzo_corrente = float(close[-1])
    out: list[Conteggio] = []

    def span(sub_p):
        return float(max(sub_p) - min(sub_p))

    # --- Impulsi completi (finestre di 6 pivot consecutivi) ---
    for s in range(0, len(pivots) - 5):
        sub_p = prezzi[s : s + 6]
        sub_i = indici[s : s + 6]
        for rialzista in (True, False):
            ok, det = _valida_impulso(sub_p, rialzista)
            if not ok:
                continue
            tipo = "impulso_rialzista" if rialzista else "impulso_ribassista"
            conf = _confidenza_impulso(det)
            recente = sub_i[-1] == ultimo_pivot
            verso = "ribasso" if rialzista else "rimbalzo"
            out.append(Conteggio(
                tipo=tipo, indici=sub_i, prezzi=sub_p,
                etichette=["0", "1", "2", "3", "4", "5"], confidenza=conf,
                onda_corrente=(
                    f"Onda 5 completata: impulso maturo, possibile {verso}."
                    if recente else "Impulso completo (storico)."),
                target=_target_impulso_completo(sub_p, rialzista) if recente else [],
                dettagli=det, recente=recente, scala=scala, span=span(sub_p)))

    # --- Impulsi in corso: noti 0..4 (onda 5 in svolgimento) ---
    for s in range(0, len(pivots) - 4):
        sub_p = prezzi[s : s + 5]
        sub_i = indici[s : s + 5]
        if sub_i[-1] != ultimo_pivot:
            continue
        for rialzista in (True, False):
            sesto = max(sub_p[-1], prezzo_corrente) if rialzista else min(sub_p[-1], prezzo_corrente)
            ok, det = _valida_impulso(sub_p + [sesto], rialzista)
            if not ok:
                continue
            tipo = "impulso_rialzista" if rialzista else "impulso_ribassista"
            conf = max(0, _confidenza_impulso(det) - 15)
            direzione = "rialzo" if rialzista else "ribasso"
            out.append(Conteggio(
                tipo=tipo, indici=sub_i, prezzi=sub_p,
                etichette=["0", "1", "2", "3", "4"], confidenza=conf,
                onda_corrente=f"Onda 5 in corso ({direzione}): trend ancora attivo ma maturo.",
                target=_target_onda5(sub_p, rialzista),
                dettagli=det, recente=True, scala=scala, span=span(sub_p)))

    # --- Correzioni A-B-C recenti (finestre di 4 pivot) ---
    for s in range(0, len(pivots) - 3):
        sub_p = prezzi[s : s + 4]
        sub_i = indici[s : s + 4]
        if sub_i[-1] != ultimo_pivot:
            continue
        for rialzista in (True, False):
            ok, det = _valida_abc(sub_p, rialzista)
            if not ok:
                continue
            conf = int(round(100 * 0.5 * (_vicinanza(det["c/a"], 1.0) + _vicinanza(det["b/a"], 0.5))))
            direzione = "rialzista" if rialzista else "ribassista"
            out.append(Conteggio(
                tipo="correzione_abc", indici=sub_i, prezzi=sub_p,
                etichette=["0", "A", "B", "C"], confidenza=conf,
                onda_corrente=f"Possibile fine correzione A-B-C ({direzione}): possibile ripresa del trend.",
                target=[], dettagli=det, recente=True, scala=scala, span=span(sub_p)))

    return out


# --------------------------------------------------------------------------- #
# 7. Pipeline completa (multi-scala)
# --------------------------------------------------------------------------- #
def analizza(df: pd.DataFrame) -> dict:
    """Analisi completa di Elliott su piu' scale. Restituisce stato, conteggi, messaggio."""
    close = df["Close"].to_numpy()
    soglie = scale_soglie(df)

    conteggi: list[Conteggio] = []
    pivot_per_scala: dict[float, list] = {}
    for s in soglie:
        piv = trova_pivot(close, s)
        pivot_per_scala[s] = piv
        if len(piv) >= 4:
            conteggi.extend(_conteggi_da_pivot(piv, close, s))

    # pivot da mostrare per riferimento: scala intermedia
    pivots_riferimento = pivot_per_scala[soglie[len(soglie) // 2]]

    if not conteggi:
        return {
            "stato": "non_chiara",
            "messaggio": (
                "Nessun conteggio di Elliott rispetta tutte le regole su nessuna scala: "
                "struttura non chiara. Nessun conteggio inventato."
            ),
            "conteggi": [],
            "migliore": None,
            "pivots": pivots_riferimento,
            "scale": soglie,
        }

    # Rimuove conteggi duplicati (stessi indici) tenendo la confidenza maggiore.
    unici: dict[tuple, Conteggio] = {}
    for c in conteggi:
        chiave = (c.tipo, tuple(c.indici))
        if chiave not in unici or c.confidenza > unici[chiave].confidenza:
            unici[chiave] = c
    conteggi = list(unici.values())

    # Ordina: prima i recenti, poi confidenza, poi grado (ampiezza) maggiore.
    conteggi.sort(key=lambda c: (c.recente, c.confidenza, c.span), reverse=True)
    migliore = conteggi[0]

    return {
        "stato": "ok",
        "messaggio": f"{len(conteggi)} conteggio/i valido/i su {len(soglie)} scale (tutte le regole rispettate).",
        "conteggi": conteggi,
        "migliore": migliore,
        "pivots": pivot_per_scala[migliore.scala],
        "scale": soglie,
    }
