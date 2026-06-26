"""Sintesi finale: combina indicatori + Elliott in un verdetto semplice a semaforo."""

from __future__ import annotations

from dataclasses import dataclass

from . import fibonacci as fib_mod


@dataclass
class Verdetto:
    semaforo: str          # 'verde' | 'giallo' | 'rosso'
    titolo: str            # es. "INVESTIRE"
    confidenza: int        # 0..100
    punteggio: float       # punteggio grezzo (per trasparenza)
    motivazioni: list[str] # frasi in italiano semplice, una per pilastro


def _segno(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def calcola(indic: dict, elliott: dict, fib=None) -> Verdetto:
    """Combina gli ultimi valori degli indicatori, l'analisi di Elliott e Fibonacci."""
    u = indic["ultimi"]
    punteggio = 0.0
    motivazioni: list[str] = []

    # --- Forza del trend (ADX): modula il peso dei segnali di trend ---
    adx = u["adx"]
    if adx >= 25:
        peso_trend = 1.0
        forza = "forte"
    elif adx >= 20:
        peso_trend = 0.6
        forza = "moderato"
    else:
        peso_trend = 0.3
        forza = "debole/laterale"

    # --- Trend (medie mobili, Supertrend, Ichimoku) ---
    p = u["prezzo"]
    trend_score = 0.0
    if p > u["sma200"]:
        trend_score += 1
    else:
        trend_score -= 1
    if u["sma50"] > u["sma200"]:
        trend_score += 1
    else:
        trend_score -= 1
    if u["supertrend_dir"] > 0:
        trend_score += 1
    else:
        trend_score -= 1
    nuvola_top = max(u["ichi_senkou_a"], u["ichi_senkou_b"])
    nuvola_bot = min(u["ichi_senkou_a"], u["ichi_senkou_b"])
    if p > nuvola_top:
        trend_score += 1
    elif p < nuvola_bot:
        trend_score -= 1

    punteggio += peso_trend * trend_score
    direzione_trend = "rialzista" if trend_score > 0 else ("ribassista" if trend_score < 0 else "neutro")
    motivazioni.append(
        f"Trend {direzione_trend} (ADX {adx:.0f}, {forza}): prezzo "
        f"{'sopra' if p > u['sma200'] else 'sotto'} la media a 200, "
        f"Supertrend {'verde' if u['supertrend_dir'] > 0 else 'rosso'}."
    )

    # --- Momentum (MACD + RSI) ---
    mom_score = 0.0
    if u["macd_hist"] > 0:
        mom_score += 1
    else:
        mom_score -= 1
    rsi = u["rsi"]
    if rsi > 70:
        mom_score -= 1
        nota_rsi = f"RSI {rsi:.0f} (ipercomprato: cautela)"
    elif rsi < 30:
        mom_score += 1
        nota_rsi = f"RSI {rsi:.0f} (ipervenduto: possibile rimbalzo)"
    else:
        nota_rsi = f"RSI {rsi:.0f} (neutro)"
    punteggio += mom_score
    motivazioni.append(
        f"Momentum {'positivo' if mom_score > 0 else ('negativo' if mom_score < 0 else 'neutro')}: "
        f"istogramma MACD {'sopra' if u['macd_hist'] > 0 else 'sotto'} lo zero, {nota_rsi}."
    )

    # --- Volatilita' (Bollinger) ---
    vol_nota = ""
    if p >= u["bb_alta"]:
        punteggio -= 0.5
        vol_nota = "prezzo sulla banda di Bollinger superiore (esteso al rialzo, possibile rientro)."
    elif p <= u["bb_bassa"]:
        punteggio += 0.5
        vol_nota = "prezzo sulla banda di Bollinger inferiore (esteso al ribasso, possibile rimbalzo)."
    else:
        vol_nota = "prezzo all'interno delle bande di Bollinger (volatilita' nella norma)."
    motivazioni.append("Volatilita': " + vol_nota)

    # --- Volume (OBV) ---
    obv_t = u["obv_trend"]
    punteggio += 0.5 * obv_t
    motivazioni.append(
        "Volume: l'OBV "
        + ("conferma la salita (volumi in accumulo)." if obv_t > 0
           else "indica distribuzione (volumi in calo)." if obv_t < 0
           else "e' stabile.")
    )

    # --- Elliott ---
    if elliott["stato"] != "ok" or elliott["migliore"] is None:
        motivazioni.append("Onde di Elliott: struttura non chiara (nessun conteggio valido) — non incide sul verdetto.")
    else:
        mig = elliott["migliore"]
        # un conteggio non recente (storico) e' contesto, non un segnale live: pesa meno
        peso_ell = (mig.confidenza / 100.0) * (1.0 if mig.recente else 0.3)
        ell_score = 0.0
        if mig.tipo == "impulso_rialzista":
            if "in corso" in mig.onda_corrente:
                ell_score += 1.0   # trend rialzista ancora attivo
            else:
                ell_score -= 1.0   # impulso su completato -> attesa correzione
        elif mig.tipo == "impulso_ribassista":
            if "in corso" in mig.onda_corrente:
                ell_score -= 1.0
            else:
                ell_score += 1.0   # impulso giu' completato -> possibile rimbalzo
        elif mig.tipo == "correzione_abc":
            ell_score += 0.5 if "rialzista" in mig.onda_corrente else -0.5
        punteggio += 1.5 * peso_ell * ell_score
        motivazioni.append(
            f"Onde di Elliott ({mig.confidenza}% confidenza): {mig.onda_corrente}"
        )

    # --- Fibonacci (livelli sullo swing dominante) ---
    fib_score, fib_nota = fib_mod.segnale_verdetto(fib)
    punteggio += fib_score
    motivazioni.append(fib_nota)

    # --- Mappa punteggio -> semaforo ---
    if punteggio >= 2.0:
        semaforo, titolo = "verde", "INVESTIRE"
    elif punteggio <= -1.5:
        semaforo, titolo = "rosso", "NON INVESTIRE ORA"
    else:
        semaforo, titolo = "giallo", "ATTENDERE / accumulare con cautela"

    # confidenza: quanto sono concordi i segnali (|punteggio| normalizzato)
    confidenza = int(round(min(100, abs(punteggio) / 5.0 * 100)))

    return Verdetto(
        semaforo=semaforo,
        titolo=titolo,
        confidenza=confidenza,
        punteggio=round(punteggio, 2),
        motivazioni=motivazioni,
    )
