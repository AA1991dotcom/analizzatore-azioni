"""Indicatori di analisi tecnica, calcolati a mano con pandas/numpy.

Tutto deterministico e trasparente (formule standard). Ogni funzione lavora
su Series/DataFrame con colonne OHLCV e restituisce Series allineate all'indice.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Medie mobili
# --------------------------------------------------------------------------- #
def sma(serie: pd.Series, periodo: int) -> pd.Series:
    return serie.rolling(periodo).mean()


def ema(serie: pd.Series, periodo: int) -> pd.Series:
    return serie.ewm(span=periodo, adjust=False).mean()


# --------------------------------------------------------------------------- #
# MACD
# --------------------------------------------------------------------------- #
def macd(serie: pd.Series, veloce: int = 12, lenta: int = 26, signal: int = 9):
    linea = ema(serie, veloce) - ema(serie, lenta)
    segnale = ema(linea, signal)
    istogramma = linea - segnale
    return linea, segnale, istogramma


# --------------------------------------------------------------------------- #
# RSI (formula di Wilder)
# --------------------------------------------------------------------------- #
def rsi(serie: pd.Series, periodo: int = 14) -> pd.Series:
    delta = serie.diff()
    guadagni = delta.clip(lower=0)
    perdite = -delta.clip(upper=0)
    # media esponenziale di Wilder: alpha = 1/periodo
    media_g = guadagni.ewm(alpha=1 / periodo, adjust=False).mean()
    media_p = perdite.ewm(alpha=1 / periodo, adjust=False).mean()
    rs = media_g / media_p.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)  # quando non ci sono perdite, neutralizza i NaN iniziali


# --------------------------------------------------------------------------- #
# ATR (Average True Range)
# --------------------------------------------------------------------------- #
def true_range(df: pd.DataFrame) -> pd.Series:
    prec_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prec_close).abs(),
            (df["Low"] - prec_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    tr = true_range(df)
    return tr.ewm(alpha=1 / periodo, adjust=False).mean()


# --------------------------------------------------------------------------- #
# ADX / DMI
# --------------------------------------------------------------------------- #
def adx(df: pd.DataFrame, periodo: int = 14):
    up = df["High"].diff()
    down = -df["Low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    tr = true_range(df)
    atr_ = tr.ewm(alpha=1 / periodo, adjust=False).mean()

    plus_di = 100 * plus_dm.ewm(alpha=1 / periodo, adjust=False).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=1 / periodo, adjust=False).mean() / atr_

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_ = dx.ewm(alpha=1 / periodo, adjust=False).mean()
    return adx_, plus_di, minus_di


# --------------------------------------------------------------------------- #
# Supertrend
# --------------------------------------------------------------------------- #
def supertrend(df: pd.DataFrame, periodo: int = 10, moltiplicatore: float = 3.0):
    """Restituisce (linea_supertrend, direzione) dove direzione = +1 rialzo, -1 ribasso."""
    atr_ = atr(df, periodo)
    hl2 = (df["High"] + df["Low"]) / 2
    upper = hl2 + moltiplicatore * atr_
    lower = hl2 - moltiplicatore * atr_

    close = df["Close"].to_numpy()
    upper = upper.to_numpy()
    lower = lower.to_numpy()
    n = len(df)

    final_upper = np.full(n, np.nan)
    final_lower = np.full(n, np.nan)
    direzione = np.ones(n)  # +1 rialzo, -1 ribasso
    st = np.full(n, np.nan)

    for i in range(1, n):
        # banda superiore: stringe finche' resta valida
        final_upper[i] = (
            upper[i]
            if (upper[i] < final_upper[i - 1] or close[i - 1] > final_upper[i - 1])
            or np.isnan(final_upper[i - 1])
            else final_upper[i - 1]
        )
        final_lower[i] = (
            lower[i]
            if (lower[i] > final_lower[i - 1] or close[i - 1] < final_lower[i - 1])
            or np.isnan(final_lower[i - 1])
            else final_lower[i - 1]
        )

        if close[i] > final_upper[i - 1] if not np.isnan(final_upper[i - 1]) else False:
            direzione[i] = 1
        elif close[i] < final_lower[i - 1] if not np.isnan(final_lower[i - 1]) else False:
            direzione[i] = -1
        else:
            direzione[i] = direzione[i - 1]

        st[i] = final_lower[i] if direzione[i] == 1 else final_upper[i]

    return (
        pd.Series(st, index=df.index),
        pd.Series(direzione, index=df.index),
    )


# --------------------------------------------------------------------------- #
# Ichimoku Cloud
# --------------------------------------------------------------------------- #
def ichimoku(df: pd.DataFrame):
    high, low, close = df["High"], df["Low"], df["Close"]

    def media_periodo(p):
        return (high.rolling(p).max() + low.rolling(p).min()) / 2

    tenkan = media_periodo(9)          # linea di conversione
    kijun = media_periodo(26)          # linea base
    senkou_a = ((tenkan + kijun) / 2).shift(26)   # bordo nuvola A
    senkou_b = media_periodo(52).shift(26)         # bordo nuvola B
    chikou = close.shift(-26)          # linea ritardata
    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }


# --------------------------------------------------------------------------- #
# Bollinger Bands
# --------------------------------------------------------------------------- #
def bollinger(serie: pd.Series, periodo: int = 20, sigma: float = 2.0):
    media = serie.rolling(periodo).mean()
    std = serie.rolling(periodo).std()
    alta = media + sigma * std
    bassa = media - sigma * std
    return alta, media, bassa


# --------------------------------------------------------------------------- #
# OBV (On-Balance Volume)
# --------------------------------------------------------------------------- #
def obv(df: pd.DataFrame) -> pd.Series:
    direzione = np.sign(df["Close"].diff().fillna(0))
    return (direzione * df["Volume"]).cumsum()


# --------------------------------------------------------------------------- #
# Calcolo aggregato
# --------------------------------------------------------------------------- #
def calcola_tutti(df: pd.DataFrame, settimanale: bool = False) -> dict:
    """Calcola tutti gli indicatori e restituisce un dict di Series/valori.

    Chiave 'ultimi' contiene gli ultimi valori scalari utili al verdetto.

    settimanale: su candele settimanali le medie di tendenza restano definite in
    GIORNI di borsa (200 giorni ~ 40 settimane). Senza questa conversione la
    SMA200 diventerebbe una media di ~4 anni: un filtro inutilmente lento.
    Gli oscillatori (RSI, MACD, ADX, ATR, Bollinger) restano ai periodi standard,
    come da prassi sui grafici settimanali.
    """
    p_ema20, p_sma50, p_sma200 = (4, 10, 40) if settimanale else (20, 50, 200)
    close = df["Close"]

    linea_macd, segnale_macd, ist_macd = macd(close)
    adx_, plus_di, minus_di = adx(df)
    st_linea, st_dir = supertrend(df)
    ichi = ichimoku(df)
    bb_alta, bb_media, bb_bassa = bollinger(close)
    rsi_ = rsi(close)
    atr_ = atr(df)
    obv_ = obv(df)

    serie = {
        "sma50": sma(close, p_sma50),
        "sma200": sma(close, p_sma200),
        "ema20": ema(close, p_ema20),
        "macd": linea_macd,
        "macd_signal": segnale_macd,
        "macd_hist": ist_macd,
        "rsi": rsi_,
        "adx": adx_,
        "plus_di": plus_di,
        "minus_di": minus_di,
        "supertrend": st_linea,
        "supertrend_dir": st_dir,
        "bb_alta": bb_alta,
        "bb_media": bb_media,
        "bb_bassa": bb_bassa,
        "atr": atr_,
        "obv": obv_,
        **{f"ichi_{k}": v for k, v in ichi.items()},
    }

    def ult(s):
        s = s.dropna()
        return float(s.iloc[-1]) if len(s) else float("nan")

    prezzo = float(close.iloc[-1])
    ultimi = {
        "prezzo": prezzo,
        "sma50": ult(serie["sma50"]),
        "sma200": ult(serie["sma200"]),
        "ema20": ult(serie["ema20"]),
        "macd_hist": ult(serie["macd_hist"]),
        "macd": ult(serie["macd"]),
        "macd_signal": ult(serie["macd_signal"]),
        "rsi": ult(serie["rsi"]),
        "adx": ult(serie["adx"]),
        "plus_di": ult(serie["plus_di"]),
        "minus_di": ult(serie["minus_di"]),
        "supertrend_dir": ult(serie["supertrend_dir"]),
        "bb_alta": ult(serie["bb_alta"]),
        "bb_bassa": ult(serie["bb_bassa"]),
        "atr": ult(serie["atr"]),
        "obv_trend": _pendenza(serie["obv"]),
        "ichi_senkou_a": ult(serie["ichi_senkou_a"]),
        "ichi_senkou_b": ult(serie["ichi_senkou_b"]),
    }

    serie["ultimi"] = ultimi
    return serie


def _pendenza(serie: pd.Series, finestra: int = 20) -> float:
    """+1 se la serie e' in crescita nelle ultime *finestra* barre, -1 se in calo, 0 piatta."""
    s = serie.dropna()
    if len(s) < finestra:
        return 0.0
    delta = float(s.iloc[-1] - s.iloc[-finestra])
    if delta > 0:
        return 1.0
    if delta < 0:
        return -1.0
    return 0.0
