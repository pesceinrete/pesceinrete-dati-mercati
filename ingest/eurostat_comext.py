"""Eurostat Comext - importazioni italiane mensili.

Risponde alla domanda che il prezzo norvegese da solo non risolve: quanto
prodotto arriva davvero in Italia, da dove, e a quale valore dichiarato.

Endpoint: le tabelle Comext hanno una base distinta da quella del resto di
Eurostat, `https://ec.europa.eu/eurostat/api/comext/dissemination`, e non
possono essere scaricate intere: vanno sempre filtrate. Le dimensioni sono
REPORTER, PARTNER, PRODUCT, FLOW, STAT_PROCEDURE e PERIOD; le misure sono
VALUE_IN_EUR e QUANTITY_IN_KG.

Tre avvertenze che vanno riportate in pagina:

* il valore diviso la quantità è il valore unitario delle importazioni,
  cioè il valore medio dichiarato in dogana. Non è una quotazione e non
  è il prezzo pagato da nessuno;
* lo Stato che registra l'importazione è spesso solo il punto di ingresso
  doganale, non la destinazione finale della merce;
* quando esce un mese nuovo, Eurostat rivede anche i mesi precedenti. Per
  questo l'archivio conserva le revisioni.

I codici doganali e i partner di ogni specie stanno nel registro
`config/prodotti.py`: una serie per ogni coppia specie/partner.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import mese  # noqa: E402
from core.store import Archivio, Osservazione  # noqa: E402

BASE = "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data"
INSIEME = "DS-045409"   # maiuscolo: è così che il servizio lo serve

# Struttura verificata sulla risposta reale del servizio (settembre 2026):
#   id: freq, reporter, partner, product, flow, indicators, time
#   indicatori: VALUE_IN_EUROS, QUANTITY_IN_100KG (quantità in quintali!)
#   time: "2026-07"; value: dizionario indice -> numero
# Non si filtra per indicatore e per partner: una sola chiamata per
# codice restituisce tutti i partner e tutti gli indicatori, e da lì si
# ricavano sia il totale mondo sia le singole provenienze.

from config.prodotti import nome_paese, pubblicati, serie_flussi  # noqa: E402


def articolo_paese(nome: str) -> str:
    """'Grecia' -> 'dalla Grecia', 'Marocco' -> 'dal Marocco', 'tutte le provenienze' -> 'da tutte le provenienze'."""
    if nome.startswith("tutte"):
        return "da " + nome
    if nome in ("Paesi Bassi",):
        return "dai " + nome
    if nome[0] in "AEIOU":
        return "dall'" + nome
    femminili = ("Norvegia", "Grecia", "Turchia", "Croazia", "Spagna", "Mauritania", "Argentina",
                 "India", "Islanda", "Danimarca", "Francia", "Thailandia")
    if nome in femminili:
        return "dalla " + nome
    return "dal " + nome


def definizioni() -> dict[str, dict]:
    """Una serie per ogni coppia prodotto/partner del registro."""
    risultato = {}
    for prodotto in pubblicati():
        flussi = prodotto.get("flussi")
        if not flussi:
            continue
        for partner in flussi["partner"]:
            serie_id = serie_flussi(prodotto, partner)
            risultato[serie_id] = dict(
                id=serie_id,
                prodotto_id=prodotto["id"],
                partner=partner,
                codici=flussi["codici"],
                anagrafica=dict(
                    id=serie_id,
                    prodotto=flussi["descrizione"],
                    presentazione="Secondo la nomenclatura combinata",
                    conservazione=None,
                    pezzatura="Non distinta dalla fonte",
                    mercato="Importazioni in Italia " + articolo_paese(nome_paese(partner)),
                    fase="Importazione (valore dichiarato in dogana)",
                    indicatore="Valore unitario delle importazioni",
                    unita="EUR/kg",
                    valuta="EUR",
                    frequenza="mensile",
                    fonte=f"Eurostat Comext, {INSIEME}, codici {', '.join(flussi['codici'])}",
                    fonte_url="https://ec.europa.eu/eurostat/comext/newxtweb/",
                    licenza="Riuso consentito con attribuzione",
                    licenza_url="https://ec.europa.eu/eurostat/about-us/policies/copyright",
                    elaborazione="Valore diviso quantità, somma dei codici doganali indicati.",
                    note=(
                        "Lo Stato di importazione è spesso il punto di ingresso doganale, non la "
                        "destinazione finale. Il valore in dogana comprende il trasporto fino alla frontiera."
                    ),
                ),
            )
    return risultato


def indirizzo(codice: str, dal_anno: int, al_anno: int | None = None,
              dal_mese: str | None = None, al_mese: str | None = None) -> str:
    """Indirizzo della richiesta. `dal_mese` e `al_mese` ("AAAA-MM"), se
    indicati, prevalgono sugli anni: servono a chiedere pochi mesi per volta."""
    parametri = {
        "format": "JSON",
        "freq": "M",
        "reporter": "IT",
        "product": codice,
        "flow": "1",  # 1 importazioni, 2 esportazioni
        "sinceTimePeriod": dal_mese or f"{dal_anno}-01",
        "lang": "EN",
    }
    if al_mese is not None:
        parametri["untilTimePeriod"] = al_mese
    elif al_anno is not None:
        parametri["untilTimePeriod"] = f"{al_anno}-12"
    return f"{BASE}/{INSIEME}?" + urllib.parse.urlencode(parametri)


def unisci(destinazione: dict, parte: dict) -> None:
    """Aggiunge i mesi di una risposta parziale a quelli già raccolti."""
    for partner, periodi in parte.items():
        destinazione.setdefault(partner, {}).update(periodi)


def _scarica_mesi(codice: str, anno: int, primo: int, ultimo: int) -> dict:
    """Scarica i mesi primo..ultimo di un anno; se la risposta è troppo
    grande (413) dimezza l'intervallo e riprova, fino al singolo mese."""
    try:
        return analizza(scarica(indirizzo(
            codice, anno, dal_mese=f"{anno}-{primo:02d}", al_mese=f"{anno}-{ultimo:02d}")))
    except urllib.error.HTTPError as errore:
        if errore.code != 413 or primo == ultimo:
            raise
    meta = (primo + ultimo) // 2
    risultato: dict = {}
    unisci(risultato, _scarica_mesi(codice, anno, primo, meta))
    unisci(risultato, _scarica_mesi(codice, anno, meta + 1, ultimo))
    return risultato


def scarica_a_blocchi(codice: str, dal_anno: int) -> dict:
    """Per i codici con molti partner (il salmone) il servizio risponde
    413, "risposta troppo grande", se si chiedono tutti gli anni insieme.
    In quel caso si chiede un anno per volta e, se anche un anno è troppo,
    un semestre, un trimestre, fino al singolo mese. I pezzi si uniscono:
    il risultato è identico a quello di una richiesta unica."""
    from datetime import date
    risultato: dict = {}
    oggi = date.today()
    for anno in range(dal_anno, oggi.year + 1):
        ultimo = 12 if anno < oggi.year else oggi.month
        try:
            unisci(risultato, _scarica_mesi(codice, anno, 1, ultimo))
        except urllib.error.HTTPError as errore:
            # un anno ancora senza mesi pubblicati non è un errore
            if errore.code in (400, 404) and anno == oggi.year:
                continue
            raise
    return risultato


def scarica(url: str, timeout: int = 90) -> dict:
    richiesta = urllib.request.Request(
        url, headers={"User-Agent": "Pesceinrete Dati e mercati"}
    )
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        return json.loads(risposta.read().decode("utf-8"))


def analizza(documento: dict) -> dict[str, dict[str, dict[str, float]]]:
    """Da una risposta JSON-stat a {partner: {mese: {"valore": €, "quantita": kg}}}.

    Il formato è lo stesso di SSB: dimensioni con indici e valori
    linearizzati. Qui servono partner, indicatore e tempo; le altre
    dimensioni sono filtrate dalla richiesta e hanno una sola categoria.
    """
    dimensioni = documento.get("dimension", {})
    ordine = documento.get("id") or list(dimensioni)
    misure = documento.get("size") or []
    valori = documento.get("value", {})

    def indici(nome: str) -> dict[str, int]:
        categoria = dimensioni[nome]["category"]["index"]
        if isinstance(categoria, list):
            return {codice: posizione for posizione, codice in enumerate(categoria)}
        return categoria

    def trova(*nomi):
        return next((n for n in ordine if n.lower() in nomi), None)

    nome_tempo = trova("time", "period", "tid")
    nome_indicatore = trova("indicators", "indicator")
    nome_partner = trova("partner")
    if not nome_tempo or not nome_indicatore:
        raise KeyError(f"dimensioni attese non trovate in Comext: presenti {ordine}")

    indici_tempo = indici(nome_tempo)
    indici_indicatore = indici(nome_indicatore)
    indici_partner = indici(nome_partner) if nome_partner else {"WORLD": 0}

    chiave_valore = next((c for c in indici_indicatore if "VALUE" in c.upper()), None)
    chiave_quantita = next(
        (c for c in indici_indicatore if "QUANTITY" in c.upper() or "KG" in c.upper()), None
    )
    if not chiave_valore or not chiave_quantita:
        raise KeyError(f"indicatori non riconosciuti: {list(indici_indicatore)}")
    fattore_kg = 100.0 if "100KG" in chiave_quantita.upper() else 1.0

    def posizione_lineare(posizioni: dict[str, int]) -> int:
        indice = 0
        for nome, dimensione in zip(ordine, misure):
            indice = indice * dimensione + posizioni.get(nome, 0)
        return indice

    def leggi(indice: int):
        if isinstance(valori, dict):
            return valori.get(str(indice))
        return valori[indice] if indice < len(valori) else None

    risultato: dict[str, dict[str, dict[str, float]]] = {}
    for codice_partner, posizione_partner in indici_partner.items():
        for codice_tempo, posizione_tempo in indici_tempo.items():
            periodo = mese.da_formato_eurostat(codice_tempo)
            if not periodo:
                continue
            base = {nome_tempo: posizione_tempo}
            if nome_partner:
                base[nome_partner] = posizione_partner
            base[nome_indicatore] = indici_indicatore[chiave_valore]
            valore = leggi(posizione_lineare(base))
            base[nome_indicatore] = indici_indicatore[chiave_quantita]
            quantita = leggi(posizione_lineare(base))
            if valore is None and quantita is None:
                continue
            voce = risultato.setdefault(codice_partner, {}).setdefault(
                periodo, {"valore": 0.0, "quantita": 0.0}
            )
            voce["valore"] += float(valore or 0)
            voce["quantita"] += float(quantita or 0) * fattore_kg
    return risultato


def somma_partner(per_partner: dict, partner: str) -> dict[str, dict[str, float]]:
    """Serie di un partner. "WORLD": il totale della fonte se c'è, altrimenti
    la somma dei singoli paesi (codici di due lettere), mai degli aggregati."""
    if partner != "WORLD":
        return per_partner.get(partner, {})
    if "WORLD" in per_partner:
        return per_partner["WORLD"]
    totale: dict[str, dict[str, float]] = {}
    for codice, periodi in per_partner.items():
        if len(codice) != 2 or not codice.isalpha():
            continue
        for periodo, voce in periodi.items():
            acc = totale.setdefault(periodo, {"valore": 0.0, "quantita": 0.0})
            acc["valore"] += voce["valore"]
            acc["quantita"] += voce["quantita"]
    return totale


_CACHE: dict[tuple[str, int], dict] = {}


STATO_CODICI: dict[str, str] = {}


def per_codice(codice: str, dal_anno: int) -> dict:
    """Una sola richiesta per codice doganale, riusata per tutti i partner.

    Un codice che il servizio non riconosce (nomenclatura cambiata, cifra
    sbagliata) viene registrato in STATO_CODICI invece di rompere il
    carico: il cruscotto e il riepilogo lo mostrano, e la specie va avanti
    con gli altri codici.
    """
    chiave = (codice, dal_anno)
    if chiave not in _CACHE:
        try:
            documento = scarica(indirizzo(codice, dal_anno))
        except urllib.error.HTTPError as errore:
            if errore.code == 413:
                try:
                    risultato = scarica_a_blocchi(codice, dal_anno)
                except urllib.error.HTTPError as secondo:
                    if secondo.code != 413:
                        raise
                    # troppo grande anche per un mese solo: il servizio sta
                    # ignorando il filtro sul prodotto, cioè il codice non esiste
                    STATO_CODICI[codice] = ("risposta troppo grande anche per un solo mese: il codice "
                                            "quasi certamente non esiste nella nomenclatura")
                    _CACHE[chiave] = {}
                    return _CACHE[chiave]
                totale = sum(v["quantita"] for p in risultato.values() for v in p.values())
                STATO_CODICI[codice] = (
                    f"ok, {len(risultato)} partner (scaricato un anno per volta)" if totale > 0
                    else "riconosciuto ma senza quantità: verificare il codice"
                )
                _CACHE[chiave] = risultato
                return risultato
            if errore.code in (400, 404):
                STATO_CODICI[codice] = f"codice non riconosciuto dal servizio (HTTP {errore.code})"
                _CACHE[chiave] = {}
                return _CACHE[chiave]
            raise
        risultato = analizza(documento)
        totale = sum(v["quantita"] for p in risultato.values() for v in p.values())
        STATO_CODICI[codice] = (
            f"ok, {len(risultato)} partner" if totale > 0 else "riconosciuto ma senza quantità: verificare il codice"
        )
        _CACHE[chiave] = risultato
    return _CACHE[chiave]


def raccogli(partner: str, dal_anno: int, codici: list[str]) -> list[Osservazione]:
    """Somma i codici doganali e costruisce le osservazioni mensili."""
    totale: dict[str, dict[str, float]] = {}
    for codice in codici:
        parziale = somma_partner(per_codice(codice, dal_anno), partner)
        for periodo, voce in parziale.items():
            accumulato = totale.setdefault(periodo, {"valore": 0.0, "quantita": 0.0})
            accumulato["valore"] += voce["valore"]
            accumulato["quantita"] += voce["quantita"]

    osservazioni = []
    for periodo in sorted(totale):
        voce = totale[periodo]
        quantita_kg = voce["quantita"]
        if quantita_kg <= 0:
            continue
        osservazioni.append(
            Osservazione(
                periodo=periodo,
                valore=voce["valore"] / quantita_kg,
                quantita=quantita_kg / 1000.0,  # in archivio le quantità sono tonnellate
            )
        )
    return osservazioni


def esegui(percorso_db: str, dal_anno: int = 2019, solo_controllo: bool = False,
           solo_prodotto: str | None = None) -> int:
    archivio = Archivio(percorso_db)
    uscita = 0
    serie = definizioni()

    for serie_id, voce in serie.items():
        if solo_prodotto and voce["prodotto_id"] != solo_prodotto:
            continue
        archivio.registra_serie(**voce["anagrafica"])
        try:
            osservazioni = raccogli(voce["partner"], dal_anno, voce["codici"])
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError) as errore:
            archivio.registra_esecuzione(f"Comext {serie_id}", "errore", messaggio=str(errore))
            print(f"{serie_id}: scaricamento fallito ({errore})", file=sys.stderr)
            uscita = 1
            continue

        if not osservazioni:
            print(f"{serie_id}: nessun mese restituito", file=sys.stderr)
            continue

        if solo_controllo:
            print(
                f"{serie_id}: {len(osservazioni)} mesi, da {osservazioni[0].periodo} "
                f"a {osservazioni[-1].periodo}, ultimo valore unitario "
                f"{osservazioni[-1].valore:.2f} EUR/kg"
            )
            continue

        esito = archivio.carica(serie_id, osservazioni, tolleranza_revisione=0.0005)
        print(f"{serie_id}: {esito.nuove} nuovi mesi, {esito.riviste} rivisti")
        archivio.registra_esecuzione(
            f"Comext {serie_id}",
            "completata",
            nuove=esito.nuove,
            riviste=esito.riviste,
            messaggio="le revisioni dei mesi precedenti sono normali su questa fonte",
        )

    # Riepilogo dei codici: è qui che si scopre un codice sbagliato
    if STATO_CODICI:
        print("\nCodici doganali:")
        for codice, stato in sorted(STATO_CODICI.items()):
            segnale = "  " if stato.startswith("ok") else "!!"
            print(f" {segnale} {codice}: {stato}")
        problemi = [c for c, s in STATO_CODICI.items() if not s.startswith("ok")]
        if problemi:
            archivio.registra_esecuzione(
                "Comext codici", "completata con avvisi",
                messaggio="codici da verificare: " + ", ".join(sorted(problemi)),
            )
            uscita = max(uscita, 0)   # non blocca: le altre specie restano valide

    archivio.chiudi()
    return uscita


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--dal", type=int, default=2019)
    parser.add_argument("--controllo", action="store_true")
    parser.add_argument("--prodotto", default=None, help="solo questo prodotto del registro")
    a = parser.parse_args()
    raise SystemExit(esegui(a.db, a.dal, a.controllo, a.prodotto))
