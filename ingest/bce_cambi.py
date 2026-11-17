"""Banca centrale europea - cambi di riferimento giornalieri.

Servono a leggere in euro una serie pubblicata in corone norvegesi. Due
avvertenze che vanno riportate anche in pagina:

* i cambi BCE sono di riferimento, a scopo informativo: non sono i cambi
  a cui un'azienda regola una fattura;
* la conversione usa il cambio medio della stessa settimana del prezzo.
  Applicare il cambio di oggi a tutto lo storico riscriverebbe la storia
  del mercato.

Endpoint SDMX: https://data-api.ecb.europa.eu/service/data/EXR/D.NOK.EUR.SP00.A
La serie è quotata come unità di valuta estera per 1 euro: per passare da
NOK/kg a EUR/kg si divide.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import isoweek  # noqa: E402
from core.store import Archivio, Osservazione  # noqa: E402

URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/D.{valuta}.EUR.SP00.A"
    "?format=csvdata&detail=dataonly"
)

SERIE_ID = "bce.cambio.{valuta}.eur.settimanale"

MINIMO_QUOTAZIONI = 3  # sotto questa soglia la settimana è poco rappresentativa


def definizione_serie(valuta: str) -> dict:
    return dict(
        id=SERIE_ID.format(valuta=valuta.lower()),
        prodotto=f"Cambio {valuta}/EUR",
        presentazione=None,
        conservazione=None,
        pezzatura=None,
        mercato="Banca centrale europea",
        fase="Cambio di riferimento",
        indicatore="Media settimanale dei cambi giornalieri di riferimento",
        unita=f"{valuta} per 1 EUR",
        valuta=valuta,
        frequenza="settimanale",
        fonte="BCE, cambi di riferimento dell'euro",
        fonte_url="https://data.ecb.europa.eu/",
        licenza="Riuso consentito con attribuzione, vedere le condizioni BCE",
        licenza_url="https://www.ecb.europa.eu/services/disclaimer/html/index.en.html",
        elaborazione="Media aritmetica dei giorni di quotazione di ciascuna settimana ISO.",
        note=(
            "Cambio informativo, non applicabile alle transazioni. Le settimane "
            f"con meno di {MINIMO_QUOTAZIONI} quotazioni vengono segnalate."
        ),
    )


def scarica(valuta: str, timeout: int = 60) -> str:
    richiesta = urllib.request.Request(
        URL.format(valuta=valuta.upper()),
        headers={"User-Agent": "Pesceinrete Dati e mercati"},
    )
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        return risposta.read().decode("utf-8")


def aggrega_per_settimana(testo_csv: str) -> tuple[list[Osservazione], list[str]]:
    lettore = csv.DictReader(io.StringIO(testo_csv))
    per_settimana: dict[str, list[float]] = defaultdict(list)

    for riga in lettore:
        giorno = riga.get("TIME_PERIOD") or riga.get("TIME")
        grezzo = riga.get("OBS_VALUE")
        if not giorno or not grezzo:
            continue
        try:
            valore = float(grezzo)
        except ValueError:
            continue  # giorni di chiusura, valore assente
        anno, mese, giorno_mese = (int(p) for p in giorno.split("-"))
        per_settimana[isoweek.da_data(date(anno, mese, giorno_mese))].append(valore)

    osservazioni, avvisi = [], []
    for settimana in sorted(per_settimana):
        quotazioni = per_settimana[settimana]
        osservazioni.append(
            Osservazione(
                periodo=settimana,
                valore=sum(quotazioni) / len(quotazioni),
                quantita=float(len(quotazioni)),
            )
        )
        if len(quotazioni) < MINIMO_QUOTAZIONI:
            avvisi.append(f"{settimana}: solo {len(quotazioni)} quotazioni")
    return osservazioni, avvisi


def esegui(percorso_db: str, valuta: str = "NOK") -> int:
    archivio = Archivio(percorso_db)
    definizione = definizione_serie(valuta)
    archivio.registra_serie(**definizione)

    try:
        testo = scarica(valuta)
    except Exception as errore:  # noqa: BLE001
        archivio.registra_esecuzione(f"BCE {valuta}", "errore", messaggio=str(errore))
        print(f"Scaricamento cambi fallito: {errore}", file=sys.stderr)
        return 1

    osservazioni, avvisi = aggrega_per_settimana(testo)
    esito = archivio.carica(definizione["id"], osservazioni, tolleranza_revisione=0.0001)
    print(f"{definizione['id']}: {esito.nuove} nuove, {esito.riviste} riviste")
    for avviso in avvisi[-5:]:
        print(f"  settimana parziale: {avviso}", file=sys.stderr)

    archivio.registra_esecuzione(
        f"BCE {valuta}",
        "completata",
        nuove=esito.nuove,
        riviste=esito.riviste,
        messaggio=f"{len(avvisi)} settimane con quotazioni parziali",
    )
    archivio.chiudi()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--valuta", default="NOK")
    argomenti = parser.parse_args()
    raise SystemExit(esegui(argomenti.db, argomenti.valuta))
