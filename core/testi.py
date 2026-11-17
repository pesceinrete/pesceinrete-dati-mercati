"""Testi generati dal sistema, in italiano e in inglese.

La base dati non ha lingua: contiene numeri, periodi e identificativi. La
lingua entra solo qui, dove i numeri diventano frasi, e nelle etichette
delle serie. Per aggiungere una lingua si aggiunge una voce a questi
dizionari; l'archivio, i calcoli e l'aggiornamento non cambiano.
"""

from __future__ import annotations

LINGUE = ("it", "en")


def soglie() -> dict:
    """Le soglie di config/soglie.json, con i valori iniziali come ripiego."""
    import json
    from pathlib import Path

    predefinite = {
        "stagionale": {"fascia_alta": 80, "fascia_bassa": 20, "finestra_settimane": 2, "anni": 5, "minimo_osservazioni": 12},
        "bollettino": {"variazione_minima_settimana": 1.0, "movimento_abituale_minimo": 0.5,
                       "cambio_divergenza_minima": 0.8, "volumi_fascia_alta": 90, "volumi_fascia_bassa": 10},
        "controlli": {"salto_sospetto_percento": 35, "scarto_cruscotto_percento": 12},
    }
    percorso = Path(__file__).resolve().parents[1] / "config" / "soglie.json"
    if percorso.exists():
        try:
            lette = json.loads(percorso.read_text(encoding="utf-8"))
            for sezione, valori in predefinite.items():
                valori.update({k: v for k, v in lette.get(sezione, {}).items() if not k.startswith("_")})
        except (ValueError, OSError):
            pass
    return predefinite

# --------------------------------------------------------------------------
# Lettura stagionale
# --------------------------------------------------------------------------

STAGIONALE = {
    "it": {
        "insufficiente": "Storico insufficiente per valutare la normalità stagionale.",
        "alto": "Più alto di circa il {p:.0f}% dei valori registrati in questo periodo dell'anno.",
        "basso": "Più basso di circa il {p:.0f}% dei valori registrati in questo periodo dell'anno.",
        "massimo": "Più alto di tutti i valori registrati in questo periodo dell'anno negli ultimi cinque anni.",
        "minimo": "Più basso di tutti i valori registrati in questo periodo dell'anno negli ultimi cinque anni.",
        "norma": "In linea con i valori abituali di questo periodo dell'anno.",
        "netto_prefisso": "Al netto del livello generale dei prezzi: ",
    },
    "en": {
        "insufficiente": "Not enough history to assess whether this level is seasonal.",
        "alto": "Higher than roughly {p:.0f}% of the values recorded at this time of year.",
        "basso": "Lower than roughly {p:.0f}% of the values recorded at this time of year.",
        "massimo": "Higher than every value recorded at this time of year in the last five years.",
        "minimo": "Lower than every value recorded at this time of year in the last five years.",
        "norma": "In line with the usual values for this time of year.",
        "netto_prefisso": "Net of the general price level: ",
    },
}

# --------------------------------------------------------------------------
# Bollettino
# --------------------------------------------------------------------------

BOLLETTINO = {
    "it": {
        "intestazione": "Settimana {periodo}",
        "quiete": (
            "Nessun movimento fuori dall'ordinario. Il prezzo resta dentro "
            "l'intervallo abituale del periodo e i volumi non presentano scarti."
        ),
        "coda": (
            "Bozza generata dai dati. Le spiegazioni dei movimenti vanno aggiunte "
            "dalla redazione e devono essere documentate."
        ),
        "fascia": {"alta": "alta", "bassa": "bassa", "centrale": "centrale"},
        "verso": {"su": "in aumento", "giu": "in calo"},
        "soglia_titolo": "{prodotto}: cambia la posizione rispetto alla stagione",
        "soglia_testo": (
            "Quattro settimane fa il prezzo si collocava nella fascia {da} dei valori "
            "registrati in questo periodo dell'anno; ora si colloca nella fascia {a} "
            "(percentile {percentile:.0f} su {n} osservazioni degli anni {primo}-{ultimo}). "
            "È il passaggio che conta per chi deve decidere se anticipare o rimandare "
            "un acquisto."
        ),
        "contro_titolo": "Movimento contrario a quello abituale del periodo",
        "contro_testo": (
            "Nella settimana {settimana} il prezzo è {verso} del {variazione}. Nelle stesse "
            "settimane dei {anni} anni precedenti il movimento medio era {verso_media} del "
            "{media}. Vale la pena verificare con gli operatori se dipende da "
            "disponibilità, da domanda o da un fatto puntuale."
        ),
        "cambio_titolo": "Il movimento in euro non è un movimento di mercato",
        "cambio_testo": (
            "Nella valuta della fonte il prezzo è {verso_origine} del {origine}; in euro è "
            "{verso_euro} del {euro}. La differenza viene dal cambio. Per chi compra in euro "
            "conta il secondo dato, ma la trattativa con un fornitore che ragiona in valuta "
            "locale parte dal primo."
        ),
        "volumi_titolo": "Volumi fuori dall'intervallo abituale",
        "volumi_testo": (
            "Le quantità della settimana ({corrente} tonnellate) sono {posizione} quasi tutti "
            "i valori delle stesse settimane degli ultimi anni (intervallo abituale da "
            "{minimo} a {massimo} tonnellate). Sui volumi lo scarto anticipa spesso il "
            "prezzo delle settimane seguenti."
        ),
        "sopra": "sopra", "sotto": "sotto",
        "revisioni_titolo": "La fonte ha corretto settimane già pubblicate",
        "revisioni_testo": (
            "Sono state riviste {n} settimane: {elenco}{altre} I valori in pagina sono "
            "quelli aggiornati. L'archivio conserva anche quelli precedenti, quindi un "
            "confronto fatto la settimana scorsa resta ricostruibile."
        ),
        "altre": " e altre.", "punto": ".",
    },
    "en": {
        "intestazione": "Week {periodo}",
        "quiete": (
            "Nothing out of the ordinary. The price remains within the usual range "
            "for the period and volumes show no anomalies."
        ),
        "coda": (
            "Draft generated from the data. Explanations of the movements must be added "
            "by the editorial team and must be documented."
        ),
        "fascia": {"alta": "upper", "bassa": "lower", "centrale": "middle"},
        "verso": {"su": "up", "giu": "down"},
        "soglia_titolo": "{prodotto}: seasonal position has changed",
        "soglia_testo": (
            "Four weeks ago the price sat in the {da} band of the values recorded at this "
            "time of year; it now sits in the {a} band (percentile {percentile:.0f} over {n} "
            "observations from {primo}-{ultimo}). This is the shift that matters when "
            "deciding whether to bring forward or postpone a purchase."
        ),
        "contro_titolo": "Movement against the usual pattern for the period",
        "contro_testo": (
            "In week {settimana} the price is {verso} {variazione}. In the same weeks of the "
            "previous {anni} years the average movement was {verso_media} {media}. Worth "
            "checking with operators whether this reflects availability, demand or a "
            "one-off event."
        ),
        "cambio_titolo": "The move in euro is not a market move",
        "cambio_testo": (
            "In the source currency the price is {verso_origine} {origine}; in euro it is "
            "{verso_euro} {euro}. The difference comes from the exchange rate. For euro "
            "buyers the second figure is what counts, but a negotiation with a supplier "
            "who thinks in local currency starts from the first."
        ),
        "volumi_titolo": "Volumes outside the usual range",
        "volumi_testo": (
            "This week's quantities ({corrente} tonnes) are {posizione} almost all values "
            "for the same weeks in recent years (usual range {minimo} to {massimo} tonnes). "
            "A volume anomaly often leads the price of the following weeks."
        ),
        "sopra": "above", "sotto": "below",
        "revisioni_titolo": "The source has revised weeks already published",
        "revisioni_testo": (
            "{n} weeks were revised: {elenco}{altre} The figures on the page are the updated "
            "ones. The archive also keeps the previous values, so a comparison made last "
            "week can still be reconstructed."
        ),
        "altre": " and others.", "punto": ".",
    },
}

# --------------------------------------------------------------------------
# Sintesi statica
# --------------------------------------------------------------------------

SINTESI = {
    "it": {
        "titolo": "{nome} <b>in sintesi</b>",
        "apertura": (
            "Nella settimana {settimana} ({esteso}) {articolo} {indicatore} è pari a {eur} €/kg"
            "{origine}: {frasi}."
        ),
        "origine": " ({origine} {unita})",
        "articolo_f": "la", "articolo_m": "il",
        "variazione": "{etichetta} {verso} del {valore}%",
        "non_confrontabile": "{etichetta} non confrontabile",
        "etichette": {
            "settimana": "sulla settimana precedente",
            "quattro": "sulle quattro settimane",
            "anno": "sullo stesso periodo dell'anno precedente",
        },
        "verso": {"su": "in aumento", "giu": "in calo", "fermo": "stabile"},
        "flussi": (
            "Nei dodici mesi fino a {mese} l'Italia ha importato {tonnellate} tonnellate "
            "di questo prodotto, a un valore unitario medio in dogana di {valore} €/kg.{quota}"
        ),
        "quota": " {paese} pesa per il {quota}% delle quantità.",
        "didascalia": (
            "Ultime dodici settimane. {fonte}; conversione in euro ai cambi di riferimento "
            "BCE della stessa settimana."
        ),
        "didascalia_euro": "Ultime dodici settimane. {fonte}.",
        "colonne": ("Settimana", "€/kg", "{unita}", "Tonnellate"),
    },
    "en": {
        "titolo": "{nome} <b>at a glance</b>",
        "apertura": (
            "In week {settimana} ({esteso}) the {indicatore} stands at €{eur}/kg"
            "{origine}: {frasi}."
        ),
        "origine": " ({origine} {unita})",
        "articolo_f": "the", "articolo_m": "the",
        "variazione": "{etichetta} {verso} {valore}%",
        "non_confrontabile": "{etichetta} not comparable",
        "etichette": {
            "settimana": "week on week",
            "quattro": "over four weeks",
            "anno": "versus the same period last year",
        },
        "verso": {"su": "up", "giu": "down", "fermo": "unchanged"},
        "flussi": (
            "In the twelve months to {mese}, Italy imported {tonnellate} tonnes of this "
            "product, at an average customs unit value of €{valore}/kg.{quota}"
        ),
        "quota": " {paese} accounts for {quota}% of the quantity.",
        "didascalia": (
            "Last twelve weeks. {fonte}; converted to euro at the ECB reference rate of "
            "the same week."
        ),
        "didascalia_euro": "Last twelve weeks. {fonte}.",
        "colonne": ("Week", "€/kg", "{unita}", "Tonnes"),
    },
}

MESI = {
    "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
           "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}

# --------------------------------------------------------------------------
# Etichette delle serie e dei prodotti
#
# L'anagrafica in archivio è in italiano. Qui la traduzione, chiave per
# chiave: se manca, resta l'italiano, mai una stringa vuota.
# --------------------------------------------------------------------------

TRADUZIONI_EN = {
    # serie SSB
    "Salmone atlantico d'allevamento": "Farmed Atlantic salmon",
    "Intero, non specificato dalla fonte": "Whole, not specified by the source",
    "Fresco o refrigerato": "Fresh or chilled",
    "Congelato": "Frozen",
    "Tutte le pezzature aggregate": "All sizes aggregated",
    "Esportazioni dalla Norvegia, tutte le destinazioni": "Exports from Norway, all destinations",
    "Esportazione (valore statistico FOB frontiera norvegese)":
        "Export (statistical value, FOB Norwegian border)",
    "Prezzo medio all'esportazione": "Average export price",
    "settimanale": "weekly",
    "mensile": "monthly",
    "Statistics Norway (SSB), tabella 03024": "Statistics Norway (SSB), table 03024",
    "Nessuna sul valore. Conversione in euro calcolata a parte.":
        "None on the value. Euro conversion calculated separately.",
    "Nessuna sul valore.": "None on the value.",
    "Media di tutte le pezzature e destinazioni. Non è una quotazione contrattuale: "
    "il riferimento usato nei contratti fisici europei è l'indice spot su panel di "
    "esportatori, oggi SISALMONI.":
        "Average across all sizes and destinations. Not a contractual quotation: the "
        "reference used in European physical contracts is the exporter-panel spot index, "
        "today SISALMONI.",
    "Volumi molto inferiori al fresco: le variazioni settimanali sono più erratiche.":
        "Volumes far below fresh: weekly changes are more erratic.",
    # cambio
    "Media settimanale dei cambi giornalieri di riferimento":
        "Weekly average of daily reference rates",
    "Banca centrale europea": "European Central Bank",
    "Cambio di riferimento": "Reference exchange rate",
    "Media aritmetica dei giorni di quotazione di ciascuna settimana ISO.":
        "Arithmetic mean of the quotation days of each ISO week.",
    "Cambio informativo, non applicabile alle transazioni. Le settimane con meno di 3 "
    "quotazioni vengono segnalate.":
        "Indicative rate, not applicable to transactions. Weeks with fewer than 3 "
        "quotations are flagged.",
    "Riuso consentito con attribuzione, vedere le condizioni BCE":
        "Reuse permitted with attribution, see ECB terms",
    # Comext
    "Intero o in pezzi, secondo la nomenclatura combinata":
        "Whole or in pieces, per the Combined Nomenclature",
    "Non distinta dalla fonte": "Not distinguished by the source",
    "Importazioni in Italia da tutte le provenienze": "Imports into Italy from all origins",
    "Importazioni in Italia dalla Norvegia": "Imports into Italy from Norway",
    "Importazione (valore dichiarato in dogana)": "Import (value declared at customs)",
    "Valore unitario delle importazioni": "Import unit value",
    "Riuso consentito con attribuzione": "Reuse permitted with attribution",
    "Valore diviso quantità. Somma dei due codici doganali.":
        "Value divided by quantity. Sum of the two customs codes.",
    "Somma dei codici 03021411 e 03021419. Lo Stato di importazione è spesso il punto di "
    "ingresso doganale, non la destinazione finale.":
        "Sum of codes 03021411 and 03021419. The importing Member State is often the "
        "customs point of entry, not the final destination.",
    "Confrontabile con il prezzo medio all'esportazione norvegese solo nell'andamento: il "
    "valore in dogana all'ingresso comprende il trasporto, quello all'uscita dalla Norvegia no.":
        "Comparable with the Norwegian export price only in its trend: the customs value "
        "on entry includes transport, the value on exit from Norway does not.",
    # prodotti
    "Salmone atlantico": "Atlantic salmon",
    "Fresco o refrigerato, esportazioni dalla Norvegia": "Fresh or chilled, exports from Norway",
    "Prezzo del salmone: quotazioni settimanali e import in Italia":
        "Salmon price: weekly quotations and imports into Italy",
    "Prezzo medio settimanale all'esportazione del salmone norvegese in euro, volumi, "
    "posizione stagionale su cinque anni e importazioni italiane. Fonti dichiarate, "
    "aggiornamento settimanale.":
        "Weekly average export price of Norwegian salmon in euro, volumes, five-year "
        "seasonal position and Italian imports. Sources disclosed, updated weekly.",
    "Questo prezzo è alto per il periodo?": "Is this price high for the time of year?",
    "La banda in apertura confronta la settimana con le stesse settimane dei cinque anni "
    "precedenti.":
        "The band at the top compares the week with the same weeks of the previous five years.",
    "Corrisponde al prezzo che mi chiede il fornitore?": "Is this the price my supplier is asking?",
    "No. È il valore medio all'esportazione dalla Norvegia, su tutte le pezzature e "
    "destinazioni. Serve come riferimento di andamento, non come quotazione contrattuale.":
        "No. It is the average export value from Norway, across all sizes and destinations. "
        "It serves as a trend reference, not as a contractual quotation.",
    "Quanto ne arriva in Italia?": "How much of it reaches Italy?",
    "Il riquadro sui flussi mostra le importazioni italiane mensili e il totale mobile a "
    "dodici mesi.":
        "The flows panel shows monthly Italian imports and the rolling twelve-month total.",
}


def _carica_registro():
    """Le traduzioni dichiarate accanto alle specie, nel registro prodotti."""
    try:
        from config.prodotti import PAESI, TRADUZIONI_EN_PRODOTTI
    except Exception:  # noqa: BLE001
        return {}, {}
    return TRADUZIONI_EN_PRODOTTI, PAESI


_EXTRA, _PAESI = _carica_registro()
TRADUZIONI_EN.update(_EXTRA)

_PREFISSI_PAESE = (
    ("Importazioni in Italia da ", "Imports into Italy from "),
    ("Importazioni in Italia dalla ", "Imports into Italy from "),
    ("Importazioni in Italia dal ", "Imports into Italy from "),
    ("Importazioni in Italia dai ", "Imports into Italy from "),
    ("Importazioni in Italia dall'", "Imports into Italy from "),
)


def traduci(testo, lingua: str):
    """Traduce un'etichetta di anagrafica; in italiano restituisce l'originale."""
    if lingua == "it" or testo is None:
        return testo
    if testo in TRADUZIONI_EN:
        return TRADUZIONI_EN[testo]
    # "Importazioni in Italia dalla Grecia" -> "Imports into Italy from Greece"
    for prefisso_it, prefisso_en in _PREFISSI_PAESE:
        if testo.startswith(prefisso_it):
            resto = testo[len(prefisso_it):]
            for codice, (nome_it, nome_en) in _PAESI.items():
                if resto == nome_it:
                    return prefisso_en + nome_en
            return prefisso_en + resto
    return testo


def mancanti_en(etichette: list[str]) -> list[str]:
    """Etichette italiane senza traduzione: utile come controllo in fase di build."""
    return [e for e in etichette if e and e not in TRADUZIONI_EN]
