"""EUMOFA - importazioni UE settimanali.

È la fonte che chiude il buco più grande della sezione: le esportazioni
norvegesi dicono quanto pesce esce dalla Norvegia, non quanto ne arriva in
Italia. EUMOFA pubblica importazioni UE settimanali in peso netto e valore,
alimentate dai dati settimanali della Commissione sulle importazioni
extra-UE (sistema Surveillance della DG TAXUD), oltre a prime vendite
mensili, prezzi lungo la filiera e prezzi al dettaglio.

Stato dell'automazione, da non nascondere in pagina: la dashboard EUMOFA è
consultabile ed esportabile, ma non espone una API pubblica documentata e
stabile. Finché non è verificata una estrazione utilizzabile e le
condizioni di riuso sono confermate per iscritto, questo modulo lavora sul
file esportato manualmente dalla dashboard. La cadenza resta settimanale e
richiede pochi minuti di lavoro redazionale.

Attenzione a un equivoco ricorrente: lo Stato membro che registra
l'importazione è spesso solo il punto di ingresso doganale, non la
destinazione finale della merce. Il dato va letto come flusso, non come
consumo nazionale.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import isoweek  # noqa: E402
from core.store import Archivio, Osservazione  # noqa: E402

DEFINIZIONE = dict(
    id="eumofa.import.ue.salmone.settimanale",
    prodotto="Salmone atlantico",
    presentazione="Secondo la nomenclatura combinata del file esportato",
    conservazione="Fresco o refrigerato",
    pezzatura=None,
    mercato="Importazioni nell'Unione europea da paesi terzi",
    fase="Importazione",
    indicatore="Quantità e valore unitario delle importazioni",
    unita="EUR/kg",
    valuta="EUR",
    frequenza="settimanale",
    fonte="EUMOFA, importazioni UE settimanali (origine: DG TAXUD Surveillance)",
    fonte_url="https://eumofa.eu/weekly-eu-import",
    licenza="Da confermare per iscritto prima della pubblicazione",
    licenza_url="https://eumofa.eu/",
    elaborazione=(
        "Valore unitario calcolato come valore diviso quantità. Non è una "
        "quotazione: è il valore medio dichiarato in dogana."
    ),
    note=(
        "Lo Stato membro di importazione è spesso il punto di ingresso doganale, "
        "non la destinazione finale della merce."
    ),
)

# Intestazioni accettate, in minuscolo. La dashboard EUMOFA cambia
# denominazione fra una versione e l'altra: meglio elencare le varianti
# che indovinare la posizione delle colonne.
COLONNE = {
    "periodo": ("week", "settimana", "periode", "period"),
    "anno": ("year", "anno"),
    "quantita": ("volume", "quantity", "net weight", "quantita"),
    "valore": ("value", "valore"),
}


def _trova(intestazioni: list[str], gruppo: str) -> str | None:
    for intestazione in intestazioni:
        pulita = intestazione.strip().lower()
        if any(parola in pulita for parola in COLONNE[gruppo]):
            return intestazione
    return None


def leggi(percorso: Path) -> list[Osservazione]:
    with percorso.open(encoding="utf-8-sig", newline="") as sorgente:
        campione = sorgente.read(4096)
        sorgente.seek(0)
        dialetto = csv.Sniffer().sniff(campione, delimiters=",;\t")
        lettore = csv.DictReader(sorgente, dialect=dialetto)
        intestazioni = lettore.fieldnames or []

        colonne = {gruppo: _trova(intestazioni, gruppo) for gruppo in COLONNE}
        mancanti = [g for g in ("periodo", "quantita", "valore") if not colonne[g]]
        if mancanti:
            raise ValueError(
                f"colonne non riconosciute nel file EUMOFA: {mancanti}. "
                f"Intestazioni trovate: {intestazioni}"
            )

        osservazioni = []
        for riga in lettore:
            grezzo_periodo = (riga.get(colonne["periodo"]) or "").strip()
            if not grezzo_periodo:
                continue
            periodo = _normalizza_periodo(
                grezzo_periodo, riga.get(colonne["anno"]) if colonne["anno"] else None
            )
            if not periodo:
                continue
            quantita = _numero(riga.get(colonne["quantita"]))
            valore = _numero(riga.get(colonne["valore"]))
            if not quantita:
                continue
            osservazioni.append(
                Osservazione(
                    periodo=periodo,
                    valore=(valore / quantita) if valore else None,
                    quantita=quantita,
                )
            )
    osservazioni.sort(key=lambda o: o.periodo)
    return osservazioni


def _normalizza_periodo(grezzo: str, anno: str | None) -> str | None:
    """Accetta "2026-W12", "2026/12", "12" con anno a parte, "2026-03-23"."""
    testo = grezzo.replace("/", "-").replace(" ", "")
    if "W" in testo.upper():
        parti = testo.upper().split("W")
        if len(parti) == 2 and parti[0].strip("-").isdigit():
            return isoweek.chiave(int(parti[0].strip("-")), int(parti[1]))
    if testo.count("-") == 2:
        anno_d, mese, giorno = (int(p) for p in testo.split("-"))
        return isoweek.da_data(date(anno_d, mese, giorno))
    if testo.count("-") == 1:
        primo, secondo = testo.split("-")
        if primo.isdigit() and secondo.isdigit():
            return isoweek.chiave(int(primo), int(secondo))
    if testo.isdigit() and anno and anno.strip().isdigit():
        return isoweek.chiave(int(anno.strip()), int(testo))
    return None


def _numero(grezzo: str | None) -> float | None:
    if not grezzo:
        return None
    pulito = grezzo.strip().replace(" ", "").replace("\u00a0", "")
    if pulito.count(",") and pulito.count("."):
        pulito = pulito.replace(".", "").replace(",", ".")
    elif pulito.count(","):
        pulito = pulito.replace(",", ".")
    try:
        return float(pulito)
    except ValueError:
        return None


def esegui(percorso_db: str, percorso_file: str) -> int:
    file_dati = Path(percorso_file)
    if not file_dati.exists():
        print(f"File non trovato: {file_dati}", file=sys.stderr)
        print(
            "Esportare i dati dalla dashboard EUMOFA delle importazioni UE settimanali "
            "e salvarli in formato CSV.",
            file=sys.stderr,
        )
        return 1

    archivio = Archivio(percorso_db)
    archivio.registra_serie(**DEFINIZIONE)
    osservazioni = leggi(file_dati)
    esito = archivio.carica(DEFINIZIONE["id"], osservazioni)
    print(f"{DEFINIZIONE['id']}: {esito.nuove} nuove, {esito.riviste} riviste")
    archivio.registra_esecuzione(
        "EUMOFA import settimanali",
        "completata",
        nuove=esito.nuove,
        riviste=esito.riviste,
        messaggio=f"da file {file_dati.name}",
    )
    archivio.chiudi()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--file", required=True, help="CSV esportato da EUMOFA")
    argomenti = parser.parse_args()
    raise SystemExit(esegui(argomenti.db, argomenti.file))
