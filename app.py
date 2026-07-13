"""Analizzatore azioni — interfaccia Streamlit minimal.

Avvio:  streamlit run app.py   (oppure: bash avvia.sh)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analisi import dati, elliott, fibonacci, indicatori, verdetto

st.set_page_config(page_title="Analisi azioni", page_icon="📈", layout="wide")

# Palette (validata, light mode) --------------------------------------------- #
INK = "#0b0b0b"          # testo primario
INK2 = "#52514e"         # testo secondario
MUTED = "#898781"        # assi / etichette
GRID = "#e1e0d9"         # griglia hairline
AXIS = "#c3c2b7"         # linea assi
BLU = "#2a78d6"          # serie 1: prezzo / MACD
GIALLO = "#eda100"       # serie 3: SMA50 / signal
VIOLA = "#4a3aa7"        # serie 5: onde di Elliott
AQUA = "#1baf7a"         # serie 2: candele su / RSI
ROSSO = "#e34948"        # serie 6: candele giu' / -DI
VERDE = "#008300"        # serie 4: +DI

SEMAFORO = {"verde": "#0ca30c", "giallo": "#eda100", "rosso": "#d03b3b"}
ESEMPI = ["AAPL", "MSFT", "NVDA", "ENI.MI", "ISP.MI", "ENEL.MI"]

# Soglia sotto cui un conteggio di Elliott non viene mostrato come "la fase attuale"
CONF_MINIMA_ELLIOTT = 30

FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


@st.cache_data(ttl=3600, show_spinner=False)
def _scarica(ticker: str, orizzonte: str) -> pd.DataFrame:
    return dati.scarica(ticker, orizzonte)


def _date(df, indici):
    return [df.index[i] for i in indici]


def _stile_minimal(fig, altezza):
    """Applica lo stile comune: griglia hairline, assi recessivi, font di sistema."""
    fig.update_layout(
        height=altezza,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=INK2),
        hovermode="x unified",
        hoverlabel=dict(font=dict(family=FONT, size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0,
                    font=dict(size=11, color=INK2)),
        margin=dict(t=30, b=10, l=10, r=48),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED, size=11))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED, size=11))
    return fig


def _traccia_elliott(fig, df, m, row=None):
    """Overlay delle onde di Elliott: linea viola, marcatori con anello bianco."""
    kw = dict(row=row, col=1) if row else {}
    fig.add_trace(go.Scatter(
        x=_date(df, m.indici), y=m.prezzi, mode="lines+markers+text",
        text=m.etichette, textposition="top center",
        textfont=dict(size=14, color=VIOLA, family=FONT),
        line=dict(color=VIOLA, width=2),
        marker=dict(size=10, color=VIOLA, line=dict(width=2, color="white")),
        name="Onde di Elliott"), **kw)


def _linee_fibonacci(fig, fib, livelli=None, row=None):
    """Livelli di Fibonacci come hairline orizzontali, etichette discrete."""
    kw = dict(row=row, col=1) if row else {}
    for et, p in fib.ritracciamenti.items():
        if livelli is not None and et not in livelli:
            continue
        fig.add_hline(y=p, line=dict(color=AXIS, width=0.8, dash="dot"),
                      annotation_text=f"Fib {et}", annotation_position="top right",
                      annotation_font=dict(size=9, color=MUTED), **kw)


def grafico_semplice(df, indic, m_ell, fib):
    """Vista essenziale: linea del prezzo, media lunga, onde, 3 livelli chiave."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Prezzo",
                             line=dict(width=1.8, color=INK)))
    fig.add_trace(go.Scatter(x=df.index, y=indic["sma200"], name="Media 200 giorni",
                             line=dict(width=1.2, color=MUTED)))
    if m_ell is not None:
        _traccia_elliott(fig, df, m_ell)
    if fib is not None:
        _linee_fibonacci(fig, fib, livelli={"0.382", "0.500", "0.618"})
    return _stile_minimal(fig, 460)


def grafico_avanzato(df, indic, m_ell, fib):
    """Vista completa a 4 pannelli."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, row_heights=[0.55, 0.15, 0.15, 0.15],
        vertical_spacing=0.04,
        subplot_titles=("", "MACD", "RSI", "Forza del trend (ADX)"))

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Prezzo", showlegend=False,
        increasing=dict(line=dict(color=AQUA, width=1), fillcolor=AQUA),
        decreasing=dict(line=dict(color=ROSSO, width=1), fillcolor=ROSSO)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["sma50"], name="SMA 50",
                             line=dict(width=1.2, color=GIALLO)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["sma200"], name="SMA 200",
                             line=dict(width=1.2, color=MUTED)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["bb_alta"], line=dict(width=0.6, color=AXIS),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["bb_bassa"], fill="tonexty",
                             fillcolor="rgba(195,194,183,0.12)",
                             line=dict(width=0.6, color=AXIS), name="Bollinger"), row=1, col=1)
    if m_ell is not None:
        _traccia_elliott(fig, df, m_ell, row=1)
        for nome_t, p in m_ell.target:
            fig.add_hline(y=p, line=dict(color=VIOLA, width=1, dash="dash"),
                          annotation_text=nome_t, annotation_position="right",
                          annotation_font=dict(size=9, color=VIOLA), row=1, col=1)
    if fib is not None:
        _linee_fibonacci(fig, fib, row=1)

    fig.add_trace(go.Bar(x=df.index, y=indic["macd_hist"], name="Istogramma",
                         marker_color=AXIS), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["macd"], name="MACD",
                             line=dict(width=1.2, color=BLU)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["macd_signal"], name="Signal",
                             line=dict(width=1.2, color=GIALLO)), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=indic["rsi"], name="RSI",
                             line=dict(width=1.2, color=AQUA)), row=3, col=1)
    for lv in (30, 70):
        fig.add_hline(y=lv, line=dict(color=AXIS, width=0.8, dash="dot"), row=3, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=indic["adx"], name="ADX",
                             line=dict(width=1.4, color=INK2)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["plus_di"], name="+DI",
                             line=dict(width=1, color=VERDE)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["minus_di"], name="−DI",
                             line=dict(width=1, color=ROSSO)), row=4, col=1)
    fig.add_hline(y=25, line=dict(color=AXIS, width=0.8, dash="dot"), row=4, col=1)

    fig = _stile_minimal(fig, 820)
    fig.update_annotations(font=dict(size=12, color=INK2, family=FONT))
    return fig


# --------------------------------------------------------------------------- #
# Barra laterale
# --------------------------------------------------------------------------- #
st.session_state.setdefault("ticker", "AAPL")


def _da_pill():
    sel = st.session_state.get("pill_ticker")
    if sel:
        st.session_state.ticker = sel


with st.sidebar:
    st.markdown("### Analisi azioni")
    st.text_input("Ticker", key="ticker",
                  help="USA: AAPL, MSFT · Borsa Italiana: aggiungi .MI (ENI.MI)")
    st.pills("Esempi", ESEMPI, key="pill_ticker", on_change=_da_pill,
             label_visibility="collapsed")
    orizzonte = st.selectbox("Orizzonte temporale", list(dati.ORIZZONTI.keys()), index=1)
    st.button("Analizza", type="primary", width="stretch")
    st.divider()
    st.caption("Strumento di supporto, **non** consulenza finanziaria. "
               "Le onde di Elliott sono interpretative.")

ticker = st.session_state.ticker.strip()

# --------------------------------------------------------------------------- #
# Corpo
# --------------------------------------------------------------------------- #
if not ticker:
    st.markdown("### Analisi azioni")
    st.write("Scrivi un ticker nella barra laterale e premi **Analizza**.")
    st.stop()

try:
    df = _scarica(ticker, orizzonte)
except dati.ErroreDati as e:
    st.error(str(e))
    st.stop()

indic = indicatori.calcola_tutti(df)
ell = elliott.analizza(df)
fib = fibonacci.calcola(ell["pivots"], indic["ultimi"]["prezzo"])
v = verdetto.calcola(indic, ell, fib)

# Conteggio di Elliott mostrato solo se recente e con confidenza decente:
# un conteggio debole non va disegnato come se fosse la fase attuale.
m_ell = ell["migliore"] if (
    ell["stato"] == "ok"
    and ell["migliore"] is not None
    and ell["migliore"].recente
    and ell["migliore"].confidenza >= CONF_MINIMA_ELLIOTT
) else None

# ---- Verdetto: card minimal, quadrata ----
accento = SEMAFORO[v.semaforo]
st.markdown(
    f"""
    <div style="border:1px solid rgba(11,11,11,0.10);border-left:3px solid {accento};
                padding:16px 20px;background:#fcfcfb;">
        <div style="font-family:{FONT};font-size:12px;color:{MUTED};">
            {ticker.upper()} · {orizzonte} · {df.index[-1].date()}</div>
        <div style="font-family:{FONT};font-size:26px;font-weight:700;color:{INK};">
            <span style="color:{accento};font-size:18px;">■</span> {v.titolo}</div>
        <div style="font-family:{FONT};font-size:13px;color:{INK2};">
            Confidenza dei segnali: {v.confidenza}%</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(f"{v.riassunto}")

tab_sintesi, tab_grafico, tab_dettagli, tab_panoramica = st.tabs(
    ["Sintesi", "Grafico completo", "Onde e livelli", "Panoramica"])

with tab_sintesi:
    # ---- Livelli operativi: prezzi concreti su cui ragionare ----
    prezzo = indic["ultimi"]["prezzo"]
    atr_u = indic["ultimi"]["atr"]
    livelli_fib = []
    if fib is not None:
        livelli_fib = sorted(set(fib.ritracciamenti.values()) | set(fib.estensioni.values()))
    sopra = min((l for l in livelli_fib if l > prezzo), default=None)
    sotto = max((l for l in livelli_fib if l < prezzo), default=None)
    stop = prezzo - 2 * atr_u

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prezzo", f"{prezzo:.2f}")
    m2.metric("Prossimo livello sopra", f"{sopra:.2f}" if sopra else "—",
              delta=f"{(sopra/prezzo-1)*100:+.1f}%" if sopra else None)
    m3.metric("Prossimo livello sotto", f"{sotto:.2f}" if sotto else "—",
              delta=f"{(sotto/prezzo-1)*100:+.1f}%" if sotto else None, delta_color="inverse")
    m4.metric("Stop indicativo (2×ATR)", f"{stop:.2f}",
              delta=f"{(stop/prezzo-1)*100:+.1f}%", delta_color="inverse")
    st.caption(
        "I livelli sopra/sotto sono i gradini di Fibonacci più vicini al prezzo; lo stop "
        "indicativo è una protezione basata sulla volatilità del titolo (2×ATR), non un consiglio."
    )
    st.divider()

    col_g, col_t = st.columns([3, 2])
    with col_g:
        st.plotly_chart(grafico_semplice(df, indic, m_ell, fib), width="stretch")
        st.caption(
            "I numeri sul grafico sono le **onde di Elliott** (le fasi del movimento); "
            "le linee tratteggiate sono i **livelli di Fibonacci**, i 'gradini' dove il "
            "prezzo tende a fermarsi o ripartire."
        )
    with col_t:
        st.markdown("##### Perché")
        for m in v.motivazioni:
            st.markdown(f"- {m}")

with tab_grafico:
    st.plotly_chart(grafico_avanzato(df, indic, m_ell, fib), width="stretch")

with tab_dettagli:
    st.markdown("##### In che fase siamo")
    if m_ell is not None:
        st.success(m_ell.onda_corrente)
    else:
        st.warning(
            "Le onde non sono leggibili con sufficiente affidabilità in questo momento: "
            "il programma preferisce non forzare un'interpretazione (e non disegna nulla "
            "di incerto sul grafico)."
        )

    with st.expander("Cosa sono le onde di Elliott e i livelli di Fibonacci?"):
        st.markdown(
            "**Onde di Elliott** — l'idea è che i prezzi si muovano per *fasi* ricorrenti: "
            "5 onde nella direzione della tendenza (numerate **1·2·3·4·5**) seguite da una "
            "correzione in 3 onde (**A·B·C**). Sapere *in che fase siamo* aiuta a capire se "
            "la tendenza è all'inizio o ormai matura.\n\n"
            "**Livelli di Fibonacci** — dopo un movimento, il prezzo spesso torna indietro di "
            "una quota tipica (38%, 50%, 62%…) prima di riprendere: quei livelli fanno da "
            "'gradini' di supporto o resistenza.\n\n"
            "Sono strumenti *interpretativi*: qui sono calcolati con regole rigorose, ma non "
            "sono previsioni certe."
        )

    if ell["stato"] == "ok":
        with st.expander("Conteggi alternativi e dettagli numerici"):
            scale_txt = ", ".join(f"{s*100:.1f}%" for s in ell["scale"])
            st.caption(f"Scale di lettura analizzate: {scale_txt}")
            for i, c in enumerate(ell["conteggi"][:5], start=1):
                punta = "◆ " if c is ell["migliore"] else ""
                st.markdown(f"{punta}**Conteggio {i}** ({c.tipo}) — affidabilità {c.confidenza}%")
                st.caption(c.onda_corrente)
                if c.target:
                    st.write("Possibili target:", {n: round(p, 2) for n, p in c.target})

    st.markdown("##### Livelli di Fibonacci")
    if fib is not None:
        verso = "rialzista" if fib.rialzista else "ribassista"
        st.write(f"Ultimo movimento di riferimento ({verso}): da {fib.p0:.2f} a {fib.p1:.2f}. {fib.nota}")
        c_r, c_e = st.columns(2)
        with c_r:
            st.caption("Ritracciamenti")
            st.write({k: round(val, 2) for k, val in sorted(fib.ritracciamenti.items())})
        with c_e:
            st.caption("Estensioni (target)")
            st.write({k: round(val, 2) for k, val in sorted(fib.estensioni.items())})
    else:
        st.write("Movimento di riferimento non determinabile su questo storico.")

    with st.expander("Versione tecnica (per chi conosce l'analisi tecnica)"):
        for d in v.dettagli_tecnici:
            st.markdown(f"- {d}")
        st.caption(f"Punteggio complessivo: {v.punteggio}")
        st.write({k: round(val, 3) for k, val in indic["ultimi"].items()})

with tab_panoramica:
    st.caption("Confronto rapido dei titoli d'esempio sullo stesso orizzonte temporale.")
    tickers_pan = list(dict.fromkeys([ticker.upper()] + ESEMPI))
    righe = []
    with st.spinner("Analizzo i titoli..."):
        for t in tickers_pan:
            try:
                df_t = _scarica(t, orizzonte)
            except dati.ErroreDati:
                continue
            ind_t = indicatori.calcola_tutti(df_t)
            ell_t = elliott.analizza(df_t)
            fib_t = fibonacci.calcola(ell_t["pivots"], ind_t["ultimi"]["prezzo"])
            v_t = verdetto.calcola(ind_t, ell_t, fib_t)
            righe.append({
                "Ticker": t,
                "Giudizio": v_t.titolo,
                "Confidenza": f"{v_t.confidenza}%",
                "Prezzo": round(ind_t["ultimi"]["prezzo"], 2),
                "Tendenza": "rialzo" if ind_t["ultimi"]["prezzo"] > ind_t["ultimi"]["sma200"] else "ribasso",
            })
    if righe:
        st.dataframe(pd.DataFrame(righe), hide_index=True, width="stretch")
    else:
        st.write("Nessun titolo analizzabile.")
