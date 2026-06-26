"""Livelli di Fibonacci: ritracciamenti ed estensioni sullo swing dominante.

Lo "swing dominante" e' la gamba di prezzo di ampiezza maggiore tra i pivot
ZigZag: e' il movimento di riferimento su cui i trader tracciano Fibonacci.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RITRACCIAMENTI = [0.236, 0.382, 0.5, 0.618, 0.786]
ESTENSIONI = [1.272, 1.618, 2.618]


@dataclass
class Fibonacci:
    i0: int                              # indice inizio swing
    i1: int                              # indice fine swing
    p0: float                            # prezzo inizio
    p1: float                            # prezzo fine
    rialzista: bool                      # swing al rialzo (p1 > p0)?
    ritracciamenti: dict[str, float] = field(default_factory=dict)
    estensioni: dict[str, float] = field(default_factory=dict)
    frazione_corrente: float = 0.0       # quanto e' ritracciato lo swing ora (0..1+)
    nota: str = ""


def swing_dominante(pivots: list[tuple[int, float]]):
    """Swing di riferimento per Fibonacci: la gamba piu' RECENTE tra quelle significative.

    Tra tutte le gambe consecutive si considerano "significative" quelle con ampiezza
    >= 50% della massima; di queste si sceglie la piu' recente, cosi' i livelli restano
    ancorati al movimento attuale (e non a uno swing storico ormai superato).
    Restituisce (i0, p0, i1, p1) oppure None.
    """
    if not pivots or len(pivots) < 2:
        return None
    gambe = [
        (ia, pa, ib, pb, abs(pb - pa))
        for (ia, pa), (ib, pb) in zip(pivots[:-1], pivots[1:])
    ]
    max_amp = max(g[4] for g in gambe)
    if max_amp <= 0:
        return None
    significative = [g for g in gambe if g[4] >= 0.5 * max_amp]
    recente = max(significative, key=lambda g: g[2])  # indice di fine maggiore = piu' recente
    return recente[:4]


def calcola(pivots: list[tuple[int, float]], prezzo_corrente: float) -> Fibonacci | None:
    """Calcola i livelli di Fibonacci sullo swing dominante."""
    sw = swing_dominante(pivots)
    if sw is None:
        return None
    i0, p0, i1, p1 = sw
    if p1 == p0:
        return None
    rialzista = p1 > p0
    diff = p1 - p0

    # Ritracciamenti: tra p0 (livello 1.0) e p1 (livello 0.0).
    ritr = {f"{r:.3f}": p1 - r * diff for r in RITRACCIAMENTI}
    ritr["0.000"] = p1
    ritr["1.000"] = p0
    # Estensioni: oltre p1 nella direzione dello swing.
    est = {f"{e:.3f}": p0 + e * diff for e in ESTENSIONI}

    # Quanto e' ritracciato lo swing al prezzo attuale (0 = sul massimo dello swing).
    frazione = (p1 - prezzo_corrente) / diff  # per up-swing; per down-swing diff<0 inverte coerentemente

    f = Fibonacci(
        i0=i0, i1=i1, p0=p0, p1=p1, rialzista=rialzista,
        ritracciamenti=ritr, estensioni=est, frazione_corrente=frazione,
    )
    f.nota = _descrivi(f)
    return f


def _descrivi(f: Fibonacci) -> str:
    fr = f.frazione_corrente
    dir_txt = "rialzista" if f.rialzista else "ribassista"
    if fr < 0:
        return f"Prezzo oltre lo swing {dir_txt} (nuovo estremo, in zona estensioni)."
    if fr <= 0.236:
        return f"Ritracciamento minimo ({fr*100:.0f}%): trend {dir_txt} forte, poco ritracciato."
    if fr <= 0.5:
        return f"Ritracciamento moderato ({fr*100:.0f}%): area di possibile ripartenza del trend {dir_txt}."
    if fr <= 0.618:
        return f"Ritracciamento sul livello aureo (~61.8%): zona classica di ingresso nel trend {dir_txt}."
    if fr <= 0.786:
        return f"Ritracciamento profondo ({fr*100:.0f}%): ultimo supporto/resistenza Fibonacci prima dell'inversione."
    if fr <= 1.0:
        return f"Ritracciamento quasi totale ({fr*100:.0f}%): trend {dir_txt} a rischio invalidazione."
    return f"Swing {dir_txt} completamente ritracciato e superato: probabile inversione."


def segnale_verdetto(f: Fibonacci | None) -> tuple[float, str]:
    """Traduce la posizione su Fibonacci in (punteggio, motivazione) per il verdetto.

    Punteggio positivo = a favore dell'ingresso nella direzione dello swing.
    """
    if f is None:
        return 0.0, "Fibonacci: swing non determinabile."
    fr = f.frazione_corrente
    segno = 1.0 if f.rialzista else -1.0  # un ritracc. favorevole spinge nella direzione del trend

    if 0.382 <= fr <= 0.618:
        return 0.8 * segno, f"dopo l'ultimo grande movimento il prezzo è tornato indietro di circa il {fr*100:.0f}%, una zona da cui spesso la tendenza riparte."
    if 0.618 < fr <= 0.786:
        return 0.3 * segno, f"il prezzo è tornato indietro parecchio ({fr*100:.0f}% dell'ultimo movimento): può ripartire, ma è più rischioso."
    if fr > 0.786:
        return -0.6 * segno, f"il prezzo ha quasi annullato l'ultimo movimento ({fr*100:.0f}%): la tendenza è a rischio."
    if fr < 0:
        return -0.3 * segno, "il prezzo ha superato i massimi dell'ultimo movimento: è molto 'tirato', possibile presa di profitto."
    return 0.1 * segno, f"il prezzo è sceso solo di poco ({fr*100:.0f}%) dopo l'ultimo movimento: tendenza ancora intatta."
