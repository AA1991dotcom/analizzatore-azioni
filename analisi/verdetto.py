"""Sintesi finale: combina indicatori + Elliott in un verdetto semplice a semaforo.

Il linguaggio delle spiegazioni e' volutamente NON tecnico: ogni pilastro e'
tradotto in una frase comprensibile a chi non conosce l'analisi tecnica.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import fibonacci as fib_mod


@dataclass
class Verdetto:
    semaforo: str          # 'verde' | 'giallo' | 'rosso'
    titolo: str            # es. "INVESTIRE"
    confidenza: int        # 0..100
    punteggio: float       # punteggio grezzo (per trasparenza)
    riassunto: str         # 2-3 frasi in parole semplici: la conclusione
    motivazioni: list[str] # una frase semplice per pilastro (con emoji)
    dettagli_tecnici: list[str] = field(default_factory=list)  # versione "da addetti"


def calcola(indic: dict, elliott: dict, fib=None) -> Verdetto:
    """Combina gli ultimi valori degli indicatori, l'analisi di Elliott e Fibonacci."""
    u = indic["ultimi"]
    punteggio = 0.0
    motivazioni: list[str] = []
    tecnici: list[str] = []

    # --- Forza del trend (ADX): modula il peso dei segnali di trend ---
    adx = u["adx"]
    if adx >= 25:
        peso_trend, forza = 1.0, "forte"
    elif adx >= 20:
        peso_trend, forza = 0.6, "media"
    else:
        peso_trend, forza = 0.3, "debole"

    # --- Trend (medie mobili, Supertrend, Ichimoku) ---
    p = u["prezzo"]
    trend_score = 0.0
    trend_score += 1 if p > u["sma200"] else -1
    trend_score += 1 if u["sma50"] > u["sma200"] else -1
    trend_score += 1 if u["supertrend_dir"] > 0 else -1
    nuvola_top = max(u["ichi_senkou_a"], u["ichi_senkou_b"])
    nuvola_bot = min(u["ichi_senkou_a"], u["ichi_senkou_b"])
    if p > nuvola_top:
        trend_score += 1
    elif p < nuvola_bot:
        trend_score -= 1

    punteggio += peso_trend * trend_score
    if trend_score > 0:
        dir_trend = "al rialzo"
    elif trend_score < 0:
        dir_trend = "al ribasso"
    else:
        dir_trend = "incerta"
    motivazioni.append(
        f"**Tendenza di fondo {dir_trend}** e di forza {forza}: "
        f"il prezzo si trova {'sopra' if p > u['sma200'] else 'sotto'} la sua media di lungo periodo."
    )
    tecnici.append(
        f"Trend: prezzo {'>' if p > u['sma200'] else '<'} SMA200, "
        f"SMA50 {'>' if u['sma50'] > u['sma200'] else '<'} SMA200, "
        f"Supertrend {'rialzo' if u['supertrend_dir'] > 0 else 'ribasso'}, ADX {adx:.0f}."
    )

    # --- Momentum (MACD + RSI) ---
    mom_score = 1 if u["macd_hist"] > 0 else -1
    rsi = u["rsi"]
    extra = ""
    if rsi > 70:
        mom_score -= 1
        extra = " Attenzione: è salito molto in fretta e potrebbe prendere fiato."
    elif rsi < 30:
        mom_score += 1
        extra = " È sceso parecchio e potrebbe esserci un rimbalzo."
    punteggio += mom_score
    slancio = "sta spingendo verso l'alto" if mom_score > 0 else ("sta perdendo forza" if mom_score < 0 else "è stabile")
    motivazioni.append(f"**Slancio recente**: il movimento {slancio}.{extra}")
    tecnici.append(
        f"Momentum: MACD ist. {'>' if u['macd_hist'] > 0 else '<'} 0 ({u['macd_hist']:.2f}), RSI {rsi:.0f}."
    )

    # --- Volatilita' (Bollinger) ---
    if p >= u["bb_alta"]:
        punteggio -= 0.5
        vol = "molto in alto rispetto alla sua oscillazione abituale (potrebbe rientrare)"
    elif p <= u["bb_bassa"]:
        punteggio += 0.5
        vol = "molto in basso rispetto alla sua oscillazione abituale (potrebbe rimbalzare)"
    else:
        vol = "in una zona normale rispetto alla sua oscillazione abituale"
    motivazioni.append(f"**Posizione del prezzo**: {vol}.")
    tecnici.append(f"Bollinger: prezzo {p:.2f}, banda {u['bb_bassa']:.2f}–{u['bb_alta']:.2f}.")

    # --- Volume (OBV) ---
    obv_t = u["obv_trend"]
    punteggio += 0.5 * obv_t
    vol_msg = ("confermano il movimento (c'è partecipazione)" if obv_t > 0
               else "non confermano il movimento (poca partecipazione)" if obv_t < 0
               else "sono stabili")
    motivazioni.append(f"**Scambi (volumi)**: {vol_msg}.")
    tecnici.append(f"OBV trend: {obv_t:+.0f}.")

    # --- Elliott ---
    # sotto questa confidenza il conteggio non e' abbastanza affidabile da pesare
    if (elliott["stato"] != "ok" or elliott["migliore"] is None
            or elliott["migliore"].confidenza < 30):
        motivazioni.append(
            "**Fase del ciclo (onde di Elliott)**: al momento non è leggibile con certezza, "
            "quindi non pesa sul giudizio."
        )
        tecnici.append("Elliott: nessun conteggio valido.")
    else:
        mig = elliott["migliore"]
        peso_ell = (mig.confidenza / 100.0) * (1.0 if mig.recente else 0.3)
        ell_score = 0.0
        if mig.tipo == "impulso_rialzista":
            ell_score += 1.0 if mig.in_corso else -1.0
        elif mig.tipo == "impulso_ribassista":
            ell_score += -1.0 if mig.in_corso else 1.0
        elif mig.tipo == "correzione_abc":
            # un A-B-C al rialzo e' un rimbalzo contro-tendenza dentro una discesa:
            # il suo completamento suggerisce la ripresa della discesa (e viceversa)
            ell_score += -0.5 if mig.corr_rialzista else 0.5
        punteggio += 1.5 * peso_ell * ell_score
        affid = "alta" if mig.confidenza >= 60 else ("media" if mig.confidenza >= 40 else "bassa")
        motivazioni.append(
            f"**Fase del ciclo (onde di Elliott)**: {mig.onda_corrente} (affidabilità {affid})."
        )
        tecnici.append(f"Elliott: {mig.tipo}, confidenza {mig.confidenza}%, recente={mig.recente}.")

    # --- Fibonacci (livelli sullo swing dominante) ---
    fib_score, fib_nota = fib_mod.segnale_verdetto(fib)
    punteggio += fib_score
    motivazioni.append("**Livelli di Fibonacci**: " + fib_nota)
    if fib is not None:
        tecnici.append(f"Fibonacci: swing {fib.p0:.2f}->{fib.p1:.2f}, ritracciato {fib.frazione_corrente*100:.0f}%.")

    # --- Mappa punteggio -> semaforo ---
    if punteggio >= 2.0:
        semaforo, titolo = "verde", "INVESTIRE"
    elif punteggio <= -1.5:
        semaforo, titolo = "rosso", "NON INVESTIRE ORA"
    else:
        semaforo, titolo = "giallo", "ATTENDERE"

    confidenza = int(round(min(100, abs(punteggio) / 5.0 * 100)))

    # --- Riassunto in parole semplici ---
    if semaforo == "verde":
        riassunto = (
            f"I segnali sono in prevalenza **positivi**. La tendenza di fondo è {dir_trend} "
            f"e c'è ancora spinta. Può essere un momento ragionevole da valutare per un ingresso, "
            f"sempre gestendo il rischio."
        )
    elif semaforo == "rosso":
        riassunto = (
            f"I segnali sono in prevalenza **negativi**. La tendenza e/o lo slancio sono deboli: "
            f"al momento è più prudente **non** entrare e aspettare che la situazione migliori."
        )
    else:
        riassunto = (
            "I segnali sono **contrastanti**: alcuni positivi, altri negativi. "
            "Conviene **aspettare** una conferma più chiara prima di muoversi."
        )

    return Verdetto(
        semaforo=semaforo,
        titolo=titolo,
        confidenza=confidenza,
        punteggio=round(punteggio, 2),
        riassunto=riassunto,
        motivazioni=motivazioni,
        dettagli_tecnici=tecnici,
    )
