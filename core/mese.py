"""Periodi mensili.

Le serie del commercio estero sono mensili, quelle dei prezzi settimanali.
Tenerle nello stesso archivio senza confonderle richiede due formati di
chiave distinti e riconoscibili a vista:

    2026-W37   settimana ISO
    2026-M09   mese

Nessuna funzione converte automaticamente fra i due. Un dato mensile resta
mensile: se serve affiancarlo a una serie settimanale si aggrega il
settimanale al mese, mai il contrario.
"""

from __future__ import annotations

from datetime import date, timedelta

MESI = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]


def chiave(anno: int, mese: int) -> str:
    if not 1 <= mese <= 12:
        raise ValueError(f"mese fuori intervallo: {mese}")
    return f"{anno:04d}-M{mese:02d}"


def scomponi(chiave_mese: str) -> tuple[int, int]:
    anno, _, mese = chiave_mese.partition("-M")
    return int(anno), int(mese)


def e_mensile(periodo: str) -> bool:
    return "-M" in periodo


def da_formato_eurostat(periodo: str) -> str | None:
    """Accetta "202603", "2026M03", "2026-03"."""
    testo = periodo.strip().upper().replace("-", "").replace("M", "")
    if len(testo) != 6 or not testo.isdigit():
        return None
    return chiave(int(testo[:4]), int(testo[4:]))


def sposta(chiave_mese: str, delta_mesi: int) -> str:
    anno, mese = scomponi(chiave_mese)
    totale = anno * 12 + (mese - 1) + delta_mesi
    return chiave(totale // 12, totale % 12 + 1)


def esteso(chiave_mese: str) -> str:
    anno, mese = scomponi(chiave_mese)
    return f"{MESI[mese - 1]} {anno}"


def primo_giorno(chiave_mese: str) -> date:
    anno, mese = scomponi(chiave_mese)
    return date(anno, mese, 1)


def ultimo_giorno(chiave_mese: str) -> date:
    """Serve a misurare il ritardo di una fonte mensile.

    Un mese non è in ritardo finché non è finito: il riferimento è
    l'ultimo giorno, non il primo.
    """
    return primo_giorno(sposta(chiave_mese, 1)) - timedelta(days=1)


def dodici_mesi_fino_a(chiave_mese: str) -> list[str]:
    return [sposta(chiave_mese, -scostamento) for scostamento in range(11, -1, -1)]


def somma_dodici_mesi(osservazioni: list[dict], fino_a: str) -> dict:
    """Totale mobile a dodici mesi, con l'indicazione dei mesi mancanti.

    Sui flussi commerciali il totale mobile è più leggibile del singolo
    mese, che risente di quando la merce passa la dogana.
    """
    voluti = set(dodici_mesi_fino_a(fino_a))
    dentro = [o for o in osservazioni if o["periodo"] in voluti]
    presenti = {o["periodo"] for o in dentro}

    quantita = sum(o["quantita"] for o in dentro if o.get("quantita"))
    valore = sum(
        o["valore"] * o["quantita"]
        for o in dentro
        if o.get("valore") is not None and o.get("quantita")
    )
    return {
        "mesi_usati": len(dentro),
        "mesi_mancanti": sorted(voluti - presenti),
        "quantita": quantita or None,
        "valore": valore or None,
        "valore_unitario": (valore / quantita) if quantita else None,
    }
