"""Analizzatore azioni — interfaccia Streamlit pulita.

Avvio:  streamlit run app.py   (oppure: bash avvia.sh)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analisi import dati, elliott, fibonacci, indicatori, verdetto

st.set_page_config(page_title="Conviene investire?", page_icon="📈", layout="wide")

COLORI = {"verde": "#1a9850", "giallo": "#e8a200", "rosso": "#d73027"}
EMOJI = {"verde": "🟢", "giallo": "🟡", "rosso": "🔴"}
ESEMPI = ["AAPL", "MSFT", "NVDA", "ENI.MI", "ISP.MI", "ENEL.MI"]


@st.cache_data(ttl=3600, show_spinner=False)
def _scarica(ticker: str, orizzonte: str) -> pd.DataFrame:
    return dati.scarica(ticker, orizzonte)


def _date(df, indici):
    return [df.index[i] for i in indici]


def _imposta_ticker(t: str):
    st.session_state.ticker = t


# --------------------------------------------------------------------------- #
# Barra laterale: tutti gli input (main area pulita)
# --------------------------------------------------------------------------- #
st.session_state.setdefault("ticker", "AAPL")

with st.sidebar:
    st.title("📈 Analisi")
    st.text_input("Ticker", key="ticker", help="USA: AAPL, MSFT · Borsa Italiana: aggiungi .MI (ENI.MI)")
    st.caption("Esempi rapidi")
    griglia = st.columns(3)
    for i, t in enumerate(ESEMPI):
        griglia[i % 3].button(t, on_click=_imposta_ticker, args=(t,), use_container_width=True)
    orizzonte = st.selectbox("Orizzonte temporale", list(dati.ORIZZONTI.keys()), index=1)
    analizza = st.button("Analizza", type="primary", use_container_width=True)
    st.divider()
    st.caption(
        "⚠️ Strumento di supporto, **non** consulenza finanziaria. "
        "Le onde di Elliott sono interpretative."
    )

ticker = st.session_state.ticker.strip()


# --------------------------------------------------------------------------- #
# Grafici
# --------------------------------------------------------------------------- #
def grafico_semplice(df, indic, ell, fib):
    """Grafico essenziale: prezzo, due medie, onde di Elliott, livelli Fibonacci."""
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="Prezzo", showlegend=False))
    fig.add_trace(go.Scatter(x=df.index, y=indic["sma50"], name="Media 50",
                             line=dict(width=1.2, color="#1f77b4")))
    fig.add_trace(go.Scatter(x=df.index, y=indic["sma200"], name="Media 200",
                             line=dict(width=1.2, color="#9467bd")))
    if ell["stato"] == "ok" and ell["migliore"] is not None:
        m = ell["migliore"]
        fig.add_trace(go.Scatter(
            x=_date(df, m.indici), y=m.prezzi, mode="lines+markers+text",
            text=m.etichette, textposition="top center",
            textfont=dict(size=15, color="#0b3d91"),
            line=dict(color="#0b3d91", width=2.5),
            marker=dict(size=12, color="#0b3d91", line=dict(width=1.5, color="white")),
            name="Onde di Elliott"))
    if fib is not None:
        for et, p in fib.ritracciamenti.items():
            fig.add_hline(y=p, line=dict(color="rgba(180,120,0,0.45)", width=0.7, dash="dot"),
                          annotation_text=f"Fib {et}", annotation_position="left",
                          annotation_font_size=9)
    fig.update_layout(height=480, xaxis_rangeslider_visible=False, hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      margin=dict(t=30, b=10, l=10, r=10))
    return fig


def grafico_avanzato(df, indic, ell, fib):
    """Grafico completo a 4 pannelli con tutti gli indicatori."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, row_heights=[0.55, 0.15, 0.15, 0.15],
        vertical_spacing=0.03, subplot_titles=("Prezzo, medie, Bollinger, Ichimoku, Elliott", "MACD", "RSI", "ADX"))

    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                                 low=df["Low"], close=df["Close"], name="Prezzo", showlegend=False), row=1, col=1)
    for k, nome, col in [("sma50", "SMA 50", "#1f77b4"), ("sma200", "SMA 200", "#9467bd"), ("ema20", "EMA 20", "#ff7f0e")]:
        fig.add_trace(go.Scatter(x=df.index, y=indic[k], name=nome, line=dict(width=1.2, color=col)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["bb_alta"], line=dict(width=0.6, color="gray"), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["bb_bassa"], fill="tonexty", fillcolor="rgba(150,150,150,0.10)",
                             line=dict(width=0.6, color="gray"), name="Bollinger"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["ichi_senkou_a"], line=dict(width=0.5, color="rgba(0,150,0,0.4)"), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["ichi_senkou_b"], fill="tonexty", fillcolor="rgba(0,150,0,0.08)",
                             line=dict(width=0.5, color="rgba(200,0,0,0.4)"), name="Ichimoku"), row=1, col=1)
    if ell["stato"] == "ok" and ell["migliore"] is not None:
        m = ell["migliore"]
        fig.add_trace(go.Scatter(x=_date(df, m.indici), y=m.prezzi, mode="lines+markers+text",
                                 text=m.etichette, textposition="top center",
                                 textfont=dict(size=15, color="#0b3d91"),
                                 line=dict(color="#0b3d91", width=2.5),
                                 marker=dict(size=12, color="#0b3d91", line=dict(width=1.5, color="white")),
                                 name="Onde di Elliott"), row=1, col=1)
        for nome_t, p in m.target:
            fig.add_hline(y=p, line=dict(color="purple", width=1, dash="dash"),
                          annotation_text=nome_t, annotation_position="right", row=1, col=1)
    if fib is not None:
        for et, p in fib.ritracciamenti.items():
            fig.add_hline(y=p, line=dict(color="rgba(180,120,0,0.45)", width=0.7, dash="dot"),
                          annotation_text=f"Fib {et}", annotation_position="left", annotation_font_size=9, row=1, col=1)

    fig.add_trace(go.Bar(x=df.index, y=indic["macd_hist"], name="MACD ist.", marker_color="#999"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["macd"], name="MACD", line=dict(width=1, color="#1f77b4")), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["macd_signal"], name="Signal", line=dict(width=1, color="#ff7f0e")), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=indic["rsi"], name="RSI", line=dict(width=1.2, color="#2ca02c")), row=3, col=1)
    fig.add_hline(y=70, line=dict(color="red", width=0.6, dash="dot"), row=3, col=1)
    fig.add_hline(y=30, line=dict(color="green", width=0.6, dash="dot"), row=3, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=indic["adx"], name="ADX", line=dict(width=1.2, color="#000")), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["plus_di"], name="+DI", line=dict(width=0.8, color="green")), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=indic["minus_di"], name="-DI", line=dict(width=0.8, color="red")), row=4, col=1)
    fig.add_hline(y=25, line=dict(color="gray", width=0.6, dash="dot"), row=4, col=1)

    fig.update_layout(height=820, xaxis_rangeslider_visible=False, hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02), margin=dict(t=40, b=10))
    return fig


# --------------------------------------------------------------------------- #
# Corpo principale
# --------------------------------------------------------------------------- #
if not ticker:
    st.title("📈 Conviene investire?")
    st.info("Scrivi un ticker nella barra laterale a sinistra e premi **Analizza**.")
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

# ---- Verdetto: la risposta semplice ----
colore = COLORI[v.semaforo]
st.markdown(
    f"""
    <div style="background:{colore};padding:22px 26px;border-radius:14px;color:white;margin-bottom:6px;">
        <div style="font-size:13px;opacity:.9;">{ticker.upper()} · {orizzonte} · {df.index[-1].date()}</div>
        <div style="font-size:34px;font-weight:800;line-height:1.1;">{EMOJI[v.semaforo]} {v.titolo}</div>
        <div style="font-size:14px;opacity:.95;margin-top:4px;">Confidenza dei segnali: {v.confidenza}%</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(f"**In parole semplici:** {v.riassunto}")

tab_sintesi, tab_grafico, tab_dettagli = st.tabs(["📊 Sintesi", "📈 Grafico completo", "🌊 Elliott & Fibonacci"])

# ---- Tab 1: Sintesi (semplice) ----
with tab_sintesi:
    col_g, col_t = st.columns([3, 2])
    with col_g:
        st.plotly_chart(grafico_semplice(df, indic, ell, fib), use_container_width=True)
        st.caption(
            "Come leggere il grafico — i numeri **1·2·3·4·5** (o **A·B·C**) sono le **onde di Elliott**, "
            "cioè le fasi del movimento del prezzo. Le linee tratteggiate **arancioni** sono i "
            "**livelli di Fibonacci**: i 'gradini' su cui il prezzo tende a fermarsi o ripartire."
        )
    with col_t:
        st.subheader("Perché")
        for m in v.motivazioni:
            st.markdown(f"- {m}")

# ---- Tab 2: Grafico completo ----
with tab_grafico:
    st.plotly_chart(grafico_avanzato(df, indic, ell, fib), use_container_width=True)

# ---- Tab 3: dettagli Elliott + Fibonacci ----
with tab_dettagli:
    with st.expander("❓ Cosa sono le onde di Elliott e i livelli di Fibonacci?"):
        st.markdown(
            "**Onde di Elliott** — l'idea è che i prezzi si muovano per *fasi* ricorrenti: "
            "5 onde nella direzione della tendenza (numerate **1·2·3·4·5**) seguite da una "
            "correzione in 3 onde (**A·B·C**). Sapere *in che fase siamo* aiuta a capire se "
            "la tendenza è all'inizio (spesso buon momento) o ormai matura (più rischioso).\n\n"
            "**Livelli di Fibonacci** — dopo un movimento, il prezzo spesso torna indietro di "
            "una quota tipica (38%, 50%, 62%…) prima di riprendere. Quei livelli fanno da "
            "'gradini' di supporto o resistenza.\n\n"
            "⚠️ Sono strumenti *interpretativi*: qui sono calcolati con regole rigorose, ma non "
            "sono previsioni certe."
        )

    st.subheader("🌊 In che fase siamo")
    if ell["stato"] == "ok" and ell["migliore"] is not None and ell["migliore"].recente:
        st.success(ell["migliore"].onda_corrente)
    elif ell["stato"] == "ok" and ell["migliore"] is not None:
        st.info(
            "Al momento non c'è una fase *attuale* leggibile con certezza. "
            "La struttura più chiara riconoscibile è storica: " + ell["migliore"].onda_corrente
        )
    else:
        st.warning(
            "Le onde non sono leggibili con certezza in questo momento: "
            "il programma preferisce non forzare un'interpretazione."
        )

    if ell["stato"] == "ok":
        with st.expander("Conteggi alternativi e dettagli numerici"):
            scale_txt = ", ".join(f"{s*100:.1f}%" for s in ell["scale"])
            st.caption(f"Scale di lettura analizzate: {scale_txt}")
            for i, c in enumerate(ell["conteggi"][:5], start=1):
                stella = "⭐ " if c is ell["migliore"] else ""
                st.markdown(f"{stella}**Conteggio {i}** ({c.tipo}) — affidabilità {c.confidenza}%")
                st.caption(c.onda_corrente)
                if c.target:
                    st.write("Possibili target:", {n: round(p, 2) for n, p in c.target})

    st.subheader("Livelli di Fibonacci")
    if fib is not None:
        verso = "rialzista" if fib.rialzista else "ribassista"
        st.write(f"Swing dominante {verso}: da {fib.p0:.2f} a {fib.p1:.2f}. {fib.nota}")
        c_r, c_e = st.columns(2)
        with c_r:
            st.caption("Ritracciamenti")
            st.write({k: round(val, 2) for k, val in sorted(fib.ritracciamenti.items())})
        with c_e:
            st.caption("Estensioni (target)")
            st.write({k: round(val, 2) for k, val in sorted(fib.estensioni.items())})
    else:
        st.info("Swing dominante non determinabile su questo storico.")

    with st.expander("🔧 Versione tecnica (per chi conosce l'analisi tecnica)"):
        for d in v.dettagli_tecnici:
            st.markdown(f"- {d}")
        st.caption(f"Punteggio complessivo: {v.punteggio}")
        st.write({k: round(val, 3) for k, val in indic["ultimi"].items()})
