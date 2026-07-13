"""Test delle regole di Elliott: applicazione rigorosa + determinismo."""

import numpy as np
import pandas as pd

from analisi import elliott, fibonacci


def _df_da_close(close):
    """Costruisce un DataFrame OHLCV minimale da una serie di chiusure."""
    close = np.asarray(close, dtype=float)
    idx = pd.date_range("2020-01-01", periods=len(close), freq="D")
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.001,
            "Low": close * 0.999,
            "Close": close,
            "Volume": np.full(len(close), 1000.0),
        },
        index=idx,
    )


# --------------------------------------------------------------------------- #
# Regole inviolabili
# --------------------------------------------------------------------------- #
def test_impulso_valido_accettato():
    # impulso rialzista pulito: 0,1,2,3,4,5
    prezzi = [100, 120, 110, 150, 135, 170]
    ok, det = elliott._valida_impulso(prezzi, rialzista=True)
    assert ok
    assert det["w3/w1"] > 1.0  # onda 3 piu' lunga dell'onda 1


def test_regola_w4_invade_w1_rifiutata():
    # onda 4 (p4=115) scende sotto la fine dell'onda 1 (p1=120) -> NON valido
    prezzi = [100, 120, 110, 150, 115, 170]
    ok, _ = elliott._valida_impulso(prezzi, rialzista=True)
    assert not ok


def test_regola_w2_oltre_100pct_rifiutata():
    # onda 2 (p2=95) scende sotto l'inizio dell'onda 1 (p0=100) -> NON valido
    prezzi = [100, 120, 95, 150, 135, 170]
    ok, _ = elliott._valida_impulso(prezzi, rialzista=True)
    assert not ok


def test_regola_w3_piu_corta_rifiutata():
    # onda 3 = 5 (150->155), piu' corta di onda1 (20) e onda5 (40) -> NON valido
    prezzi = [100, 120, 150, 155, 130, 170]
    ok, _ = elliott._valida_impulso(prezzi, rialzista=True)
    assert not ok


def test_impulso_ribassista_valido():
    # mirror dell'impulso rialzista
    prezzi = [170, 150, 160, 120, 135, 100]
    ok, _ = elliott._valida_impulso(prezzi, rialzista=False)
    assert ok


# --------------------------------------------------------------------------- #
# Pipeline completa
# --------------------------------------------------------------------------- #
def test_struttura_non_chiara_su_rumore_piatto():
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 0.05, 300))  # quasi piatto
    res = elliott.analizza(_df_da_close(close))
    # non deve mai inventare: o trova conteggi validi o dichiara non chiara
    assert res["stato"] in ("ok", "non_chiara")
    if res["stato"] == "ok":
        for c in res["conteggi"]:
            assert c.confidenza >= 0


def test_determinismo():
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0.05, 1.0, 400))
    df = _df_da_close(close)
    r1 = elliott.analizza(df)
    r2 = elliott.analizza(df)
    assert r1["stato"] == r2["stato"]
    assert len(r1["conteggi"]) == len(r2["conteggi"])
    if r1["migliore"] and r2["migliore"]:
        assert r1["migliore"].indici == r2["migliore"].indici
        assert r1["migliore"].confidenza == r2["migliore"].confidenza


def test_impulso_rilevato_in_serie_costruita():
    # serie con un chiaro impulso 5 onde rialzista, poi correzione
    segmenti = [
        np.linspace(100, 130, 30),   # onda 1
        np.linspace(130, 115, 15),   # onda 2
        np.linspace(115, 175, 50),   # onda 3 (la piu' lunga)
        np.linspace(175, 155, 20),   # onda 4
        np.linspace(155, 195, 30),   # onda 5
    ]
    close = np.concatenate(segmenti)
    res = elliott.analizza(_df_da_close(close))
    assert res["stato"] == "ok"
    tipi = {c.tipo for c in res["conteggi"]}
    assert "impulso_rialzista" in tipi


def test_pivot_agganciati_agli_estremi_reali():
    # picco sulle chiusure al giorno 30, ma il massimo REALE (High) e' al giorno 31
    close = np.concatenate([np.linspace(100, 150, 31), np.linspace(148, 100, 30)])
    df = _df_da_close(close)
    df.iloc[31, df.columns.get_loc("High")] = 160.0  # spike di High dopo il picco di chiusura
    pivots = elliott._aggancia_estremi(
        elliott.trova_pivot(df["Close"].to_numpy(), 0.05),
        df["High"].to_numpy(), df["Low"].to_numpy(),
    )
    prezzi = [p for _, p in pivots]
    assert 160.0 in prezzi  # il pivot del massimo deve stare sull'estremo vero


def test_conteggio_migliore_privilegia_grado_maggiore():
    # grande impulso a 5 onde + rumore fine sovrapposto: il migliore deve coprire
    # la struttura grande, non una micro-onda
    segmenti = [
        np.linspace(100, 140, 40), np.linspace(140, 120, 20),
        np.linspace(120, 200, 60), np.linspace(200, 170, 25),
        np.linspace(170, 230, 40),
    ]
    rng = np.random.default_rng(3)
    close = np.concatenate(segmenti) + rng.normal(0, 1.0, 185)
    res = elliott.analizza(_df_da_close(close))
    assert res["stato"] == "ok"
    span_max = max(c.span for c in res["conteggi"])
    assert res["migliore"].span >= 0.6 * span_max


def test_multiscala_produce_piu_scale():
    rng = np.random.default_rng(11)
    close = 100 + np.cumsum(rng.normal(0.08, 1.0, 600))
    df = _df_da_close(close)
    assert len(elliott.scale_soglie(df)) >= 2  # almeno due scale distinte
    res = elliott.analizza(df)
    assert "scale" in res


def test_abc_rifiutata_se_fa_nuovi_massimi():
    # zigzag ascendente che SUPERA il massimo precedente (150): non e' una correzione,
    # e' una nuova spinta -> l'etichetta A-B-C non deve comparire
    pivots = [(0, 150.0), (10, 120.0), (20, 140.0), (30, 130.0), (40, 170.0)]
    close = np.full(41, 170.0)
    conteggi = elliott._conteggi_da_pivot(pivots, close, scala=0.05)
    abc = [c for c in conteggi if c.tipo == "correzione_abc"]
    assert abc == []


def test_abc_accettata_se_resta_sotto_il_massimo_precedente():
    # rimbalzo in 3 onde dentro una discesa: C (140) resta sotto il massimo (150)
    pivots = [(0, 150.0), (10, 100.0), (20, 130.0), (30, 115.0), (40, 140.0)]
    close = np.full(41, 140.0)
    conteggi = elliott._conteggi_da_pivot(pivots, close, scala=0.05)
    abc = [c for c in conteggi if c.tipo == "correzione_abc"]
    assert len(abc) == 1
    assert abc[0].corr_rialzista  # rimbalzo al rialzo (contro-tendenza in una discesa)


# --------------------------------------------------------------------------- #
# Fibonacci
# --------------------------------------------------------------------------- #
def test_fibonacci_swing_dominante_e_livelli():
    pivots = [(0, 100.0), (10, 110.0), (20, 105.0), (40, 200.0)]  # gamba max: 105->200
    f = fibonacci.calcola(pivots, prezzo_corrente=150.0)
    assert f is not None
    assert (f.p0, f.p1) == (105.0, 200.0)
    assert f.rialzista
    # 0% = massimo swing, 100% = minimo swing
    assert abs(f.ritracciamenti["0.000"] - 200.0) < 1e-6
    assert abs(f.ritracciamenti["1.000"] - 105.0) < 1e-6
    # livello 50% = punto medio
    assert abs(f.ritracciamenti["0.500"] - 152.5) < 1e-6


def test_fibonacci_segnale_zona_aurea_positivo():
    pivots = [(0, 100.0), (40, 200.0)]   # swing rialzista
    # prezzo sul ~61.8% di ritracciamento -> zona d'ingresso favorevole
    prezzo = 200.0 - 0.6 * 100.0
    f = fibonacci.calcola(pivots, prezzo_corrente=prezzo)
    score, _ = fibonacci.segnale_verdetto(f)
    assert score > 0
