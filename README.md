# 📈 Analisi Azioni

Tool semplice che, dato un ticker, scarica i dati aggiornati da **Yahoo Finance** e
risponde in modo chiaro: **conviene investire o no?**

Combina **medie mobili, MACD, RSI, ADX/DMI, Supertrend, Ichimoku, Bollinger Bands, OBV**
e una ricostruzione **rigorosa delle onde di Elliott**, sintetizzando tutto in un
verdetto a semaforo (🟢 Investire · 🟡 Attendere · 🔴 Non investire ora).

## Avvio (un solo comando)

```bash
bash avvia.sh
```

Lo script crea l'ambiente virtuale, installa le dipendenze e apre l'app nel browser.

> Serve Python ≥ 3.10. Se hai solo la versione di sistema (3.9), installa una versione
> recente con Homebrew: `brew install python@3.12`.

## Uso

1. Scrivi il **ticker**:
   - Azioni USA: `AAPL`, `MSFT`, `NVDA`
   - Borsa Italiana: aggiungi `.MI` → `ENI.MI`, `ISP.MI`, `ENEL.MI`
2. Scegli l'**orizzonte temporale** (per Elliott a lungo termine usa "Molto lungo", che
   passa alle candele settimanali).
3. Premi **Analizza**.

## Onde di Elliott — "vietato improvvisare"

L'algoritmo è **deterministico** e **non inventa mai** un conteggio:
- rileva i pivot con uno **ZigZag** a soglia adattiva (basata su ATR);
- **enumera** tutte le etichettature possibili;
- **scarta** ogni conteggio che viola una regola inviolabile (onda 2 < 100% onda 1,
  onda 3 mai la più corta, onda 4 non invade l'onda 1);
- se **nessun** conteggio è valido → dichiara *"struttura non chiara"*;
- se più conteggi sono validi → li mostra **tutti**, ordinati per aderenza a Fibonacci.

Resta una tecnica interpretativa: il tool garantisce il rigore delle regole, non la
certezza della previsione.

## Test

```bash
source .venv/bin/activate
python -m pytest test_elliott.py -v
```

## Avvertenza

Strumento di supporto all'analisi tecnica, **non** consulenza finanziaria.
