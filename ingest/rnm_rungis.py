"""FranceAgriMer RNM - quotazioni del mercato di Rungis.

Perché questa fonte: è l'unica in Europa che pubblica ogni giorno, in
accesso libero e in tempo reale, quotazioni all'ingrosso su circa 300
prodotti della pesca, compresi quelli su cui l'Italia non ha alcun
riferimento pubblico settimanale: orata, spigola, polpo. Il rilevamento è
fatto da conjoncturistes pubblici ed è certificato ISO 9001.

Che cosa misura: il prezzo di vendita all'ingrosso sulla piazza di Rungis,
per prodotto rigorosamente definito (specie, origine, presentazione,
calibro). Non è un prezzo italiano e non è un prezzo alla produzione: è
un riferimento di mercato europeo, da etichettare come tale.

Stato di questo modulo, da leggere prima di usarlo:

* il portale non espone una API documentata; il modulo scarica la pagina
  del prodotto (https://rnm.franceagrimer.fr/prix?DAURADE e simili) e ne
  estrae le tabelle. Le pagine riportano "dernière cotation avant le
  gg-mm-aaaa" e righe come "DAURADE Royale aquaculture 400-600g U.E." con
  le colonne prix moyen, mini, maxi;
* la struttura della pagina non è stata verificata da questo ambiente:
  la prima esecuzione va fatta con `--controllo`, che stampa le tabelle
  trovate senza scrivere niente. Solo dopo si fissa in `config/rnm.json`
  quale riga corrisponde a quale serie;
* le condizioni di riuso: i contenuti contrassegnati "Licence Ouverte"
  sono riutilizzabili anche a fini commerciali con attribuzione; per gli
  altri FranceAgriMer prevede una richiesta. Va controllato per ciascuna
  mercuriale prima di pubblicare, e la risposta scritta va conservata.

Quando i tre punti sono chiusi, orata, spigola e polpo diventano schede
pubblicate con una riga di configurazione.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.prodotti import FONTI_PREZZO, pubblicati  # noqa: E402
from core.store import Archivio, Osservazione  # noqa: E402

CONFIGURAZIONE = Path(__file__).resolve().parents[1] / "config" / "rnm.json"


def serie_dal_registro() -> list[dict]:
    """Le serie RNM dichiarate nel registro, con l'anagrafica già composta.

    In `config/rnm.json` restano solo l'indirizzo della mercuriale e la
    colonna del prezzo, che si fissano dopo il primo `--controllo`.
    """
    fonte = FONTI_PREZZO["rnm"]
    serie = []
    for prodotto in pubblicati():
        prezzo = prodotto.get("prezzo", {})
        if prezzo.get("fonte") != "rnm":
            continue
        base = prezzo.get("anagrafica", {})
        serie.append(dict(
            id=prezzo["serie"],
            etichetta=prezzo.get("rnm_etichetta", prodotto["nome"].lower()),
            prodotto_id=prodotto["id"],
            anagrafica=dict(
                prodotto=base.get("prodotto", prodotto["nome"]),
                presentazione=base.get("presentazione"),
                conservazione=base.get("conservazione"),
                pezzatura=base.get("pezzatura"),
                mercato="Mercato all'ingrosso di Rungis (Parigi)",
                fase="Ingrosso",
                indicatore="Quotazione all'ingrosso, media settimanale delle rilevazioni giornaliere",
                unita="EUR/kg",
                valuta="EUR",
                frequenza="settimanale",
                fonte=fonte["nome"],
                fonte_url=fonte["url"],
                licenza=fonte["licenza"],
                licenza_url=fonte["licenza_url"],
                elaborazione="Media delle quotazioni giornaliere della settimana ISO",
                note="Prezzo di mercato francese: segue lo stesso prodotto che arriva in Italia, ma non è un prezzo italiano.",
            ),
        ))
    return serie


class EstrattoreTabelle(HTMLParser):
    """Raccoglie tutte le tabelle della pagina come liste di righe di celle."""

    def __init__(self):
        super().__init__()
        self.tabelle: list[list[list[str]]] = []
        self._tabella = None
        self._riga = None
        self._cella = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._tabella = []
        elif tag == "tr" and self._tabella is not None:
            self._riga = []
        elif tag in ("td", "th") and self._riga is not None:
            self._cella = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cella is not None and self._riga is not None:
            self._riga.append(" ".join("".join(self._cella).split()))
            self._cella = None
        elif tag == "tr" and self._riga is not None and self._tabella is not None:
            if any(self._riga):
                self._tabella.append(self._riga)
            self._riga = None
        elif tag == "table" and self._tabella is not None:
            if self._tabella:
                self.tabelle.append(self._tabella)
            self._tabella = None

    def handle_data(self, dati):
        if self._cella is not None:
            self._cella.append(dati)


def scarica(url: str, timeout: int = 60) -> str:
    richiesta = urllib.request.Request(
        url, headers={"User-Agent": "Pesceinrete Dati e mercati (redazione@pesceinrete.com)"}
    )
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        grezzo = risposta.read()
    for codifica in ("utf-8", "latin-1"):
        try:
            return grezzo.decode(codifica)
        except UnicodeDecodeError:
            continue
    return grezzo.decode("utf-8", errors="replace")


def numero_francese(testo: str) -> float | None:
    """"7,80" -> 7.8; "7,80 €/kg" -> 7.8; "-" -> None."""
    trovato = re.search(r"-?\d+(?:[.,]\d+)?", testo or "")
    if not trovato:
        return None
    return float(trovato.group(0).replace(",", "."))


def data_dalla_pagina(html: str) -> date | None:
    """La pagina scrive "dernière cotation avant le 16-02-2024" (o con le barre)."""
    trovato = re.search(r"cotation[^0-9]{0,40}(\d{2})[-/](\d{2})[-/](\d{4})", html, re.I)
    if not trovato:
        trovato = re.search(r"(\d{2})[-/](\d{2})[-/](\d{4})", html)
    if not trovato:
        return None
    giorno, mese, anno = (int(x) for x in trovato.groups())
    try:
        return date(anno, mese, giorno)
    except ValueError:
        return None


def _normalizza(testo: str) -> str:
    """Minuscolo, senza accenti, con un solo tipo di separatore nei calibri."""
    import unicodedata

    piatto = unicodedata.normalize("NFKD", testo)
    piatto = "".join(c for c in piatto if not unicodedata.combining(c))
    return piatto.lower().replace("/", "-").replace("[", " ").replace("]", " ")


def cerca_righe(tabelle: list, etichetta: str) -> list[list[str]]:
    """Righe che contengono tutti i termini dell'etichetta.

    Il confronto ignora maiuscole e accenti e tratta "400/600" e "400-600"
    allo stesso modo: le mercuriali scrivono "DAURADE Royale aquaculture
    400-600g U.E." e un'etichetta scritta a mano non deve rompersi per
    una barra.
    """
    termini = [_normalizza(t) for t in etichetta.split()]
    risultato = []
    for tabella in tabelle:
        for riga in tabella:
            testo = _normalizza(" ".join(riga))
            if all(termine in testo for termine in termini):
                risultato.append(riga)
    return risultato


def esegui(percorso_db: str, solo_controllo: bool) -> int:
    indirizzi = {}
    if CONFIGURAZIONE.exists():
        indirizzi = json.loads(CONFIGURAZIONE.read_text(encoding="utf-8")).get("indirizzi", {})

    serie_registro = serie_dal_registro()
    archivio = Archivio(percorso_db)
    uscita = 0

    for serie in serie_registro:
        voce = indirizzi.get(serie["id"], {})
        url = voce.get("url")
        if not url:
            print(f"{serie['id']}: nessun indirizzo in config/rnm.json, saltata "
                  f"(etichetta cercata: '{serie['etichetta']}')", file=sys.stderr)
            continue
        try:
            html = scarica(url)
        except Exception as errore:  # noqa: BLE001
            print(f"{serie['id']}: scaricamento fallito ({errore})", file=sys.stderr)
            archivio.registra_esecuzione(f"RNM {serie['id']}", "errore", messaggio=str(errore))
            uscita = 1
            continue

        estrattore = EstrattoreTabelle()
        estrattore.feed(html)
        giorno = data_dalla_pagina(html)
        righe = cerca_righe(estrattore.tabelle, voce.get("etichetta", serie["etichetta"]))

        if solo_controllo:
            print(f"\n{serie['id']}: {len(estrattore.tabelle)} tabelle, data rilevata {giorno}, "
                  f"{len(righe)} righe per '{voce.get('etichetta', serie['etichetta'])}'")
            for riga in righe[:5]:
                print("   ", " | ".join(riga))
            if not righe and estrattore.tabelle:
                print("    prime righe della prima tabella, per orientarsi:")
                for riga in estrattore.tabelle[0][:5]:
                    print("   ", " | ".join(riga))
            continue

        if not righe or giorno is None:
            print(f"{serie['id']}: riga o data non trovate, niente scritto", file=sys.stderr)
            uscita = 1
            continue

        prezzo = numero_francese(righe[0][voce.get("colonna_prezzo", 1)])
        if prezzo is None:
            print(f"{serie['id']}: prezzo non leggibile in {righe[0]}", file=sys.stderr)
            uscita = 1
            continue

        archivio.registra_serie(id=serie["id"], **serie["anagrafica"])
        # Le quotazioni sono giornaliere: si scrive il giorno, la media
        # settimanale la fa il generatore del sito.
        esito = archivio.carica(serie["id"], [Osservazione(periodo=giorno.isoformat(), valore=prezzo)])
        print(f"{serie['id']}: {giorno} {prezzo} EUR/kg ({'nuovo' if esito.nuove else 'già presente'})")
        archivio.registra_esecuzione(
            f"RNM {serie['id']}", "completata", nuove=esito.nuove, riviste=esito.riviste
        )

    archivio.chiudi()
    return uscita


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--controllo", action="store_true",
                        help="scarica e mostra le tabelle trovate senza scrivere")
    a = parser.parse_args()
    raise SystemExit(esegui(a.db, a.controllo))
