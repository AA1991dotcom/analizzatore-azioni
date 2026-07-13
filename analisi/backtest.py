"""Backtest onesto del semaforo: walk-forward senza guardare il futuro.

Principi:
  - A ogni valutazione il verdetto usa SOLO i dati fino a quel giorno
    (niente look-ahead: e' cio' che un utente avrebbe visto davvero).
  - Il segnale calcolato alla chiusura del giorno t vale dal giorno t+1.
  - Regole: verde -> investito, rosso -> fuori, giallo -> mantiene la posizione.
  - Nessun costo di transazione ne' tasse: i risultati reali sarebbero inferiori.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import elliott, fibonacci, indicatori, verdetto

# barre minime perche' gli indicatori lunghi (SMA200) siano pronti
WARMUP = 210
# tetto alle valutazioni: oltre, il passo si allarga da solo (tempi ragionevoli)
MAX_VALUTAZIONI = 300


@dataclass
class Risultato:
    date: list                       # date della finestra di test
    equity_strategia: np.ndarray     # base 100
    equity_benchmark: np.ndarray     # comprare e tenere, base 100
    rendimento_strategia: float      # %
    rendimento_benchmark: float      # %
    drawdown_strategia: float        # % (max perdita dal picco)
    drawdown_benchmark: float        # %
    n_operazioni: int                # cambi di posizione (entrate + uscite)
    pct_investito: float             # % del tempo passato investiti
    n_valutazioni: int
    passo: int                       # barre tra una valutazione e l'altra


def _drawdown_massimo(equity: np.ndarray) -> float:
    picchi = np.maximum.accumulate(equity)
    dd = (equity - picchi) / picchi
    return float(dd.min()) * 100


def equity_da_posizioni(close: np.ndarray, posizioni: np.ndarray) -> np.ndarray:
    """Curva equity (base 100). posizioni[t] = quota investita DURANTE il giorno t
    (decisa al piu' tardi alla chiusura del giorno t-1)."""
    equity = np.empty(len(close))
    equity[0] = 100.0
    for t in range(1, len(close)):
        rendimento_giorno = close[t] / close[t - 1] - 1
        equity[t] = equity[t - 1] * (1 + posizioni[t] * rendimento_giorno)
    return equity


def esegui(df: pd.DataFrame, passo: int = 5, avanzamento=None) -> Risultato | None:
    """Esegue il backtest walk-forward. Restituisce None se lo storico e' troppo corto.

    avanzamento: callback opzionale f(frazione) per la barra di progresso.
    """
    n = len(df)
    if n < WARMUP + passo * 8:
        return None
    close = df["Close"].to_numpy()

    # il passo si allarga da solo se le valutazioni sarebbero troppe
    passo = max(passo, (n - WARMUP) // MAX_VALUTAZIONI)
    valutazioni = list(range(WARMUP, n, passo))

    posizioni = np.zeros(n)
    pos = 0.0
    n_operazioni = 0
    for k, t in enumerate(valutazioni):
        sotto = df.iloc[: t + 1]
        ind = indicatori.calcola_tutti(sotto)
        ell = elliott.analizza(sotto)
        fib = fibonacci.calcola(ell["pivots"], ind["ultimi"]["prezzo"])
        v = verdetto.calcola(ind, ell, fib)
        nuova = 1.0 if v.semaforo == "verde" else (0.0 if v.semaforo == "rosso" else pos)
        if nuova != pos:
            n_operazioni += 1
        pos = nuova
        # la decisione presa alla chiusura di t vale dal giorno t+1 in poi
        # (le decisioni successive sovrascrivono la coda)
        if t + 1 < n:
            posizioni[t + 1 :] = pos
        if avanzamento is not None:
            avanzamento((k + 1) / len(valutazioni))

    # confronto equo: entrambe le curve partono dal primo giorno valutabile
    s = WARMUP
    close_bt = close[s:]
    eq_strat = equity_da_posizioni(close_bt, posizioni[s:])
    eq_bench = equity_da_posizioni(close_bt, np.ones(len(close_bt)))

    return Risultato(
        date=list(df.index[s:]),
        equity_strategia=eq_strat,
        equity_benchmark=eq_bench,
        rendimento_strategia=float(eq_strat[-1] - 100.0),
        rendimento_benchmark=float(eq_bench[-1] - 100.0),
        drawdown_strategia=_drawdown_massimo(eq_strat),
        drawdown_benchmark=_drawdown_massimo(eq_bench),
        n_operazioni=n_operazioni,
        pct_investito=float(posizioni[s:].mean() * 100),
        n_valutazioni=len(valutazioni),
        passo=passo,
    )
