"""Recupero dati di mercato da Yahoo Finance (gratis, senza chiave API)."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

# Orizzonti temporali offerti all'utente -> (period, interval) per yfinance.
# Su orizzonti molto lunghi si usano candele settimanali: le onde di Elliott
# a lungo termine si leggono meglio sul settimanale (meno rumore).
ORIZZONTI: dict[str, tuple[str, str]] = {
    "Medio (1-2 anni)": ("2y", "1d"),
    "Lungo (5 anni)": ("5y", "1d"),
    "Molto lungo (10 anni, settimanale)": ("max", "1wk"),
}


class ErroreDati(Exception):
    """Sollevata quando i dati non possono essere recuperati."""


def scarica(ticker: str, orizzonte: str) -> pd.DataFrame:
    """Scarica lo storico OHLCV per *ticker* sull'*orizzonte* indicato.

    Restituisce un DataFrame con colonne: Open, High, Low, Close, Volume
    e indice temporale crescente. Solleva ErroreDati in caso di problemi.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise ErroreDati("Inserisci un ticker (es. AAPL, ENI.MI).")

    if orizzonte not in ORIZZONTI:
        raise ErroreDati(f"Orizzonte non valido: {orizzonte!r}.")

    period, interval = ORIZZONTI[orizzonte]

    try:
        dati = yf.Ticker(ticker).history(
            period=period, interval=interval, auto_adjust=True
        )
    except Exception as exc:  # rete, ticker malformato, ecc.
        raise ErroreDati(
            f"Impossibile scaricare i dati per {ticker!r}: {exc}"
        ) from exc

    if dati is None or dati.empty:
        raise ErroreDati(
            f"Nessun dato trovato per {ticker!r}. "
            "Controlla il ticker (azioni Borsa Italiana: aggiungi '.MI', es. ENI.MI)."
        )

    dati = dati[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if len(dati) < 60:
        raise ErroreDati(
            f"Storico troppo corto per {ticker!r} ({len(dati)} candele): "
            "scegli un orizzonte piu' lungo o un altro titolo."
        )

    return dati
