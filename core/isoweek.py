"""Gestione delle settimane ISO 8601.

Tutte le serie settimanali del progetto sono indicizzate come stringa
"AAAA-Wnn" (es. "2026-W37"). L'uso di una chiave testuale ordinabile
evita gli errori di confronto fra anni con 52 e 53 settimane.
"""

from __future__ import annotations

from datetime import date, timedelta

# --------------------------------------------------------------------------
# Conversioni
# --------------------------------------------------------------------------


def chiave(anno: int, settimana: int) -> str:
    """Restituisce la chiave canonica di una settimana ISO."""
    if not 1 <= settimana <= 53:
        raise ValueError(f"settimana ISO fuori intervallo: {settimana}")
    return f"{anno:04d}-W{settimana:02d}"


def scomponi(chiave_settimana: str) -> tuple[int, int]:
    """Da "2026-W37" a (2026, 37)."""
    anno, _, settimana = chiave_settimana.partition("-W")
    return int(anno), int(settimana)


def da_data(giorno: date) -> str:
    """Chiave ISO della settimana che contiene il giorno indicato."""
    anno, settimana, _ = giorno.isocalendar()
    return chiave(anno, settimana)


def lunedi(chiave_settimana: str) -> date:
    """Primo giorno (lunedi) della settimana ISO."""
    anno, settimana = scomponi(chiave_settimana)
    return date.fromisocalendar(anno, settimana, 1)


def domenica(chiave_settimana: str) -> date:
    """Ultimo giorno (domenica) della settimana ISO."""
    return lunedi(chiave_settimana) + timedelta(days=6)


def settimane_nell_anno(anno: int) -> int:
    """52 o 53 a seconda dell'anno ISO."""
    return date(anno, 12, 28).isocalendar()[1]


def da_formato_ssb(periodo: str) -> str:
    """Converte il formato periodo di Statistics Norway ("2025U09")."""
    anno, _, settimana = periodo.partition("U")
    return chiave(int(anno), int(settimana))


# --------------------------------------------------------------------------
# Aritmetica
# --------------------------------------------------------------------------


def sposta(chiave_settimana: str, delta_settimane: int) -> str:
    """Somma (o sottrae) settimane restituendo la chiave risultante."""
    nuovo = lunedi(chiave_settimana) + timedelta(weeks=delta_settimane)
    return da_data(nuovo)


def intervallo(dalla: str, alla: str) -> list[str]:
    """Elenco ordinato e continuo di settimane fra due estremi inclusi."""
    if lunedi(dalla) > lunedi(alla):
        raise ValueError("estremi invertiti")
    corrente, risultato = dalla, []
    while lunedi(corrente) <= lunedi(alla):
        risultato.append(corrente)
        corrente = sposta(corrente, 1)
    return risultato


def stessa_settimana_anno_precedente(chiave_settimana: str, anni: int = 1) -> str:
    """Stessa settimana ISO di N anni prima.

    Se l'anno di arrivo non ha la settimana 53 si usa la 52: è la
    convenzione adottata da tutti i confronti anno su anno del progetto.
    """
    anno, settimana = scomponi(chiave_settimana)
    anno_arrivo = anno - anni
    massimo = settimane_nell_anno(anno_arrivo)
    return chiave(anno_arrivo, min(settimana, massimo))


def finestra_stagionale(settimana: int, ampiezza: int = 2) -> list[int]:
    """Settimane ISO comparabili attorno a una data settimana.

    La finestra si chiude ad anello: attorno alla settimana 1 rientrano
    la 51 e la 52 dell'anno precedente.
    """
    numeri = []
    for scostamento in range(-ampiezza, ampiezza + 1):
        valore = settimana + scostamento
        if valore < 1:
            valore += 52
        elif valore > 52:
            valore -= 52
        numeri.append(valore)
    return sorted(set(numeri))
