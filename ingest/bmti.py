"""BMTI - prezzi all'ingrosso dei mercati ittici italiani.

La Borsa Merci Telematica Italiana rileva per conto delle Camere di
commercio i prezzi all'ingrosso sui mercati ittici italiani e li pubblica
nel portale "Ittico dati". È l'unica fonte pubblica italiana con cadenza
settimanale, ed è quella giusta per i prodotti in gran parte nazionali
come cozze e vongole, dove un prezzo estero non direbbe niente.

Stato dell'automazione: BMTI non espone una API pubblica documentata e le
condizioni di riuso per una ripubblicazione commerciale con archivio vanno
confermate per iscritto. Finché la conferma non c'è, il modulo lavora sul
file esportato dal portale (CSV o foglio salvato come CSV).

Il file atteso ha una riga per rilevazione con almeno: data o settimana,
prodotto, prezzo. La corrispondenza fra il nome del prodotto nel file e la
serie del registro si fissa in `config/bmti.json`.

    python ingest/bmti.py --db dati/archivio.sqlite --file esportazione_bmti.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.prodotti import FONTI_PREZZO, pubblicati  # noqa: E402
from core import isoweek  # noqa: E402
from core.store import Archivio, Osservazione  # noqa: E402

CONFIGURAZIONE = Path(__file__).resolve().parents[1] / "config" / "bmti.json"

COLONNE = {
    "data": ("data", "date", "settimana", "week", "periodo"),
    "prodotto": ("prodotto", "specie", "product", "descrizione"),
    "prezzo": ("prezzo", "price", "medio", "media"),
    "mercato": ("mercato", "piazza", "market"),
}


def serie_dal_registro() -> dict[str, dict]:
    fonte = FONTI_PREZZO["bmti"]
    risultato = {}
    for prodotto in pubblicati():
        prezzo = prodotto.get("prezzo", {})
        if prezzo.get("fonte") != "bmti":
            continue
        base = prezzo.get("anagrafica", {})
        risultato[prezzo["serie"]] = dict(
            prodotto_id=prodotto["id"],
            anagrafica=dict(
                prodotto=base.get("prodotto", prodotto["nome"]),
                presentazione=base.get("presentazione"),
                conservazione=base.get("conservazione"),
                pezzatura=base.get("pezzatura"),
                mercato="Mercati ittici all'ingrosso italiani",
                fase="Ingrosso",
                indicatore="Prezzo all'ingrosso, media settimanale",
                unita="EUR/kg",
                valuta="EUR",
                frequenza="settimanale",
                fonte=fonte["nome"],
                fonte_url=fonte["url"],
                licenza=fonte["licenza"],
                licenza_url=fonte["licenza_url"],
                elaborazione="Media delle rilevazioni settimanali dei mercati",
                note="Prezzo rilevato sui mercati ittici italiani; la copertura dei mercati può variare fra le settimane.",
            ),
        )
    return risultato


def _trova(intestazioni, gruppo):
    for intestazione in intestazioni:
        pulita = intestazione.strip().lower()
        if any(parola in pulita for parola in COLONNE[gruppo]):
            return intestazione
    return None


def _numero(grezzo):
    if not grezzo:
        return None
    pulito = grezzo.strip().replace("€", "").replace(" ", "")
    if pulito.count(",") and pulito.count("."):
        pulito = pulito.replace(".", "").replace(",", ".")
    elif pulito.count(","):
        pulito = pulito.replace(",", ".")
    try:
        return float(pulito)
    except ValueError:
        return None


def _settimana(grezzo: str):
    testo = grezzo.strip()
    if "-W" in testo.upper():
        anno, _, settimana = testo.upper().partition("-W")
        return isoweek.chiave(int(anno), int(settimana))
    for separatore in ("-", "/"):
        parti = testo.split(separatore)
        if len(parti) == 3:
            try:
                if len(parti[0]) == 4:
                    giorno = date(int(parti[0]), int(parti[1]), int(parti[2]))
                else:
                    giorno = date(int(parti[2]), int(parti[1]), int(parti[0]))
                return isoweek.da_data(giorno)
            except ValueError:
                return None
    return None


def leggi(percorso: Path, corrispondenze: dict[str, str]) -> dict[str, list[Osservazione]]:
    """Dal file alle serie: media per settimana di tutte le rilevazioni del prodotto."""
    with percorso.open(encoding="utf-8-sig", newline="") as sorgente:
        campione = sorgente.read(4096)
        sorgente.seek(0)
        dialetto = csv.Sniffer().sniff(campione, delimiters=",;\t")
        lettore = csv.DictReader(sorgente, dialect=dialetto)
        intestazioni = lettore.fieldnames or []
        colonne = {g: _trova(intestazioni, g) for g in COLONNE}
        mancanti = [g for g in ("data", "prodotto", "prezzo") if not colonne[g]]
        if mancanti:
            raise ValueError(f"colonne non riconosciute: {mancanti}. Trovate: {intestazioni}")

        raccolta: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for riga in lettore:
            nome = (riga.get(colonne["prodotto"]) or "").strip().lower()
            serie_id = next((s for chiave, s in corrispondenze.items() if chiave.lower() in nome), None)
            if not serie_id:
                continue
            settimana = _settimana(riga.get(colonne["data"]) or "")
            prezzo = _numero(riga.get(colonne["prezzo"]))
            if settimana and prezzo:
                raccolta[serie_id][settimana].append(prezzo)

    return {
        serie_id: [
            Osservazione(periodo=s, valore=sum(v) / len(v), quantita=float(len(v)))
            for s, v in sorted(settimane.items())
        ]
        for serie_id, settimane in raccolta.items()
    }


def esegui(percorso_db: str, percorso_file: str) -> int:
    file_dati = Path(percorso_file)
    if not file_dati.exists():
        print(f"File non trovato: {file_dati}", file=sys.stderr)
        return 1
    corrispondenze = {}
    if CONFIGURAZIONE.exists():
        corrispondenze = json.loads(CONFIGURAZIONE.read_text(encoding="utf-8")).get("corrispondenze", {})
    if not corrispondenze:
        print("Manca config/bmti.json con le corrispondenze prodotto -> serie", file=sys.stderr)
        return 1

    registro = serie_dal_registro()
    archivio = Archivio(percorso_db)
    totale = 0
    for serie_id, osservazioni in leggi(file_dati, corrispondenze).items():
        if serie_id not in registro:
            print(f"{serie_id}: non nel registro, saltata", file=sys.stderr)
            continue
        archivio.registra_serie(id=serie_id, **registro[serie_id]["anagrafica"])
        esito = archivio.carica(serie_id, osservazioni)
        totale += esito.nuove
        print(f"{serie_id}: {esito.nuove} settimane nuove, {esito.riviste} riviste")
        archivio.registra_esecuzione(f"BMTI {serie_id}", "completata", nuove=esito.nuove,
                                     riviste=esito.riviste, messaggio=f"da file {file_dati.name}")
    archivio.chiudi()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--file", required=True)
    a = parser.parse_args()
    raise SystemExit(esegui(a.db, a.file))
