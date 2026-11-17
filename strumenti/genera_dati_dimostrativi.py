"""Popola l'archivio con serie dimostrative per tutte le specie del registro.

Serve solo a far girare la pagina completa prima che le fonti reali siano
collegate. I valori sono verosimili nei livelli e nella stagionalità ma
inventati: lo script scrive un marcatore `DIMOSTRATIVO` accanto al
database, e finché quel file esiste la pagina mostra una fascia rossa in
cima. Il collegamento reale si fa con `./gestisci reale`.

    python strumenti/genera_dati_dimostrativi.py --db dati/archivio.sqlite
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.prodotti import pubblicati, serie_flussi
from core import isoweek, mese
from core.store import Archivio, Osservazione
from ingest.bce_cambi import definizione_serie
from ingest.bmti import serie_dal_registro as serie_bmti
from ingest.eurostat_comext import definizioni as definizioni_comext
from ingest.rnm_rungis import serie_dal_registro as serie_rnm
from ingest.ssb_laks import SERIE as SERIE_SSB

PRIMO_ANNO = 2019
ULTIMA_SETTIMANA = "2026-W39"
ULTIMO_MESE = "2026-M07"   # i flussi doganali escono con due o tre mesi di ritardo

# Livello medio in EUR/kg (o NOK/kg per il salmone), picco stagionale (settimana ISO),
# ampiezza della stagionalità, volatilità settimanale, tonnellate importate al mese.
PROFILI = {
    "salmone":     dict(livello=74.0, picco=20, ampiezza=0.22, rumore=2.4, mensili=2100, valuta="NOK"),
    "orata":       dict(livello=6.1, picco=50, ampiezza=0.10, rumore=0.10, mensili=2600),
    "spigola":     dict(livello=7.4, picco=50, ampiezza=0.11, rumore=0.12, mensili=2300),
    "polpo":       dict(livello=10.8, picco=48, ampiezza=0.14, rumore=0.25, mensili=1900),
    "gambero":     dict(livello=8.9, picco=48, ampiezza=0.08, rumore=0.18, mensili=4200),
    "merluzzo":    dict(livello=9.6, picco=12, ampiezza=0.12, rumore=0.20, mensili=3600),
    "tonno":       dict(livello=12.4, picco=28, ampiezza=0.09, rumore=0.30, mensili=1500),
    "pesce_spada": dict(livello=11.9, picco=30, ampiezza=0.10, rumore=0.28, mensili=900),
    "cozze":       dict(livello=1.65, picco=30, ampiezza=0.18, rumore=0.06, mensili=2800),
    "vongole":     dict(livello=7.8, picco=52, ampiezza=0.15, rumore=0.22, mensili=180),
}


def serie_settimanale(prodotto_id: str, casuale: random.Random) -> list[Osservazione]:
    profilo = PROFILI[prodotto_id]
    deriva, osservazioni = 0.0, []
    for anno in range(PRIMO_ANNO, 2027):
        tendenza = 1 + 0.03 * (anno - 2022)   # lieve inflazione dei prezzi
        for settimana in range(1, isoweek.settimane_nell_anno(anno) + 1):
            periodo = isoweek.chiave(anno, settimana)
            if periodo > ULTIMA_SETTIMANA:
                break
            stagione = math.cos((settimana - profilo["picco"]) / 52 * 2 * math.pi)
            deriva = deriva * 0.82 + casuale.gauss(0, 1) * profilo["rumore"]
            prezzo = profilo["livello"] * tendenza * (1 + profilo["ampiezza"] * stagione) + deriva
            prezzo = max(prezzo, profilo["livello"] * 0.45)
            quantita = None
            if profilo.get("valuta") == "NOK":
                volume = 17000 + 5200 * math.cos((settimana - 46) / 52 * 2 * math.pi)
                quantita = round(max(volume * (1 + casuale.gauss(0, 0.06)), 4000), 0)
            osservazioni.append(Osservazione(periodo, round(prezzo, 2), quantita))
    return osservazioni


def serie_cambio(casuale: random.Random) -> list[Osservazione]:
    base = {2019: 9.85, 2020: 10.72, 2021: 10.16, 2022: 10.10, 2023: 11.42, 2024: 11.63, 2025: 11.70, 2026: 11.55}
    osservazioni = []
    for anno in range(PRIMO_ANNO, 2027):
        for settimana in range(1, isoweek.settimane_nell_anno(anno) + 1):
            periodo = isoweek.chiave(anno, settimana)
            if periodo > ULTIMA_SETTIMANA:
                break
            osservazioni.append(Osservazione(
                periodo, round(base[anno] + 0.32 * math.sin(settimana / 9) + casuale.gauss(0, 0.05), 4), 5.0
            ))
    return osservazioni


def serie_mensili(prodotto: dict, casuale: random.Random) -> dict[str, list[Osservazione]]:
    """Importazioni mensili per partner, con quote verosimili e stagionalità dei consumi."""
    profilo = PROFILI[prodotto["id"]]
    flussi = prodotto["flussi"]
    partner = [p for p in flussi["partner"] if p != "WORLD"]
    quote = {}
    residuo = 0.92
    for i, codice in enumerate(partner):
        quota = (0.62 if codice == flussi.get("principale") else residuo / max(1, len(partner) - 1) * 0.45)
        quote[codice] = quota
    somma = sum(quote.values())
    quote = {c: q / somma * 0.9 for c, q in quote.items()}   # il resto è "altri"

    risultato = {serie_flussi(prodotto, c): [] for c in flussi["partner"]}
    corrente = mese.chiave(PRIMO_ANNO, 1)
    while corrente <= ULTIMO_MESE:
        _, numero_mese = mese.scomponi(corrente)
        spinta = 1.0 + (0.22 if numero_mese == 12 else 0) + (0.08 if numero_mese in (7, 8) else 0)
        totale = profilo["mensili"] * spinta * (1 + casuale.gauss(0, 0.08))
        valore = (profilo["livello"] / (11.5 if profilo.get("valuta") == "NOK" else 1.0)) * 1.08
        valore *= 1 + 0.08 * math.cos((numero_mese - 5) / 12 * 2 * math.pi) + casuale.gauss(0, 0.03)
        risultato[serie_flussi(prodotto, "WORLD")].append(Osservazione(corrente, round(valore, 3), round(totale, 1)))
        for codice in partner:
            risultato[serie_flussi(prodotto, codice)].append(Osservazione(
                corrente, round(valore * (0.97 + casuale.gauss(0, 0.02)), 3),
                round(totale * quote[codice] * (1 + casuale.gauss(0, 0.05)), 1)
            ))
        corrente = mese.sposta(corrente, 1)
    return risultato


def esegui(percorso_db: str) -> int:
    casuale = random.Random(20261003)
    archivio = Archivio(percorso_db)

    # anagrafiche
    for definizione in SERIE_SSB.values():
        archivio.registra_serie(**definizione)
    archivio.registra_serie(**definizione_serie("NOK"))
    for voce in serie_rnm():
        archivio.registra_serie(id=voce["id"], **voce["anagrafica"])
    for serie_id, voce in serie_bmti().items():
        archivio.registra_serie(id=serie_id, **voce["anagrafica"])
    for voce in definizioni_comext().values():
        archivio.registra_serie(**voce["anagrafica"])

    settimane = mesi = 0
    archivio.carica("bce.cambio.nok.eur.settimanale", serie_cambio(casuale))
    for prodotto in pubblicati():
        serie_id = prodotto["prezzo"]["serie"]
        prezzi = serie_settimanale(prodotto["id"], casuale)

        if prodotto["id"] == "salmone":
            # Un rialzo di fine estate contrario all'andamento abituale, per
            # mostrare che il bollettino lo riconosce. Con dati veri non c'è.
            for scostamento, spinta in enumerate((1.06, 1.11, 1.15)):
                indice = len(prezzi) - 3 + scostamento
                prezzi[indice] = Osservazione(prezzi[indice].periodo, round(prezzi[indice].valore * spinta, 2), prezzi[indice].quantita)
            archivio.carica("ssb.laks.congelato.prezzo", [
                Osservazione(o.periodo, round(o.valore * 1.12, 2), round((o.quantita or 0) * 0.045, 0)) for o in prezzi
            ])

        settimane += archivio.carica(serie_id, prezzi).nuove
        for serie_flusso, osservazioni in serie_mensili(prodotto, casuale).items():
            mesi += archivio.carica(serie_flusso, osservazioni).nuove

    archivio.registra_esecuzione(
        "dati dimostrativi", "completata", nuove=settimane + mesi,
        messaggio="serie inventate per tutte le specie, da sostituire con le fonti reali",
    )
    archivio.chiudi()

    marcatore = Path(percorso_db).parent / "DIMOSTRATIVO"
    marcatore.write_text(
        "I dati in archivio sono inventati. Eseguire ./gestisci reale per pubblicare.\n", encoding="utf-8"
    )
    print(f"{len(pubblicati())} specie, {settimane} settimane di prezzo e {mesi} mesi di flussi. "
          f"Marcatore scritto in {marcatore}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    raise SystemExit(esegui(parser.parse_args().db))
