"""Registro delle specie pubblicate, delle loro serie e delle fonti.

Criterio di scelta delle fonti, nell'ordine:

1. ente statistico o pubblico (SSB, Eurostat, FranceAgriMer, BMTI): il
   dato è rilevato con metodo dichiarato e stabile nel tempo;
2. frequenza almeno settimanale per il prezzo, mensile per i flussi;
3. licenza che consente la ripubblicazione, o conferma scritta;
4. acquisizione automatizzabile.

Per ogni specie:

* `prezzo` è la serie settimanale di riferimento, con la fonte che la
  produce;
* `flussi` sono le importazioni italiane mensili da Eurostat Comext, per
  provenienza, costruite sui codici della nomenclatura combinata indicati.
  I codici vanno riverificati a ogni gennaio: la nomenclatura cambia.

Le etichette sono in italiano con la traduzione inglese accanto: la base
dati non ha lingua, i testi sì.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Paesi partner (codice Eurostat -> nome)
# --------------------------------------------------------------------------

PAESI = {
    "WORLD": ("tutte le provenienze", "all origins"),
    "NO": ("Norvegia", "Norway"),
    "GR": ("Grecia", "Greece"),
    "TR": ("Turchia", "Türkiye"),
    "HR": ("Croazia", "Croatia"),
    "ES": ("Spagna", "Spain"),
    "MA": ("Marocco", "Morocco"),
    "MR": ("Mauritania", "Mauritania"),
    "EC": ("Ecuador", "Ecuador"),
    "AR": ("Argentina", "Argentina"),
    "IN": ("India", "India"),
    "IS": ("Islanda", "Iceland"),
    "DK": ("Danimarca", "Denmark"),
    "NL": ("Paesi Bassi", "Netherlands"),
    "FR": ("Francia", "France"),
    "VN": ("Vietnam", "Vietnam"),
    "CL": ("Cile", "Chile"),
    "TH": ("Thailandia", "Thailand"),
}

# --------------------------------------------------------------------------
# Fonti di prezzo
# --------------------------------------------------------------------------

FONTI_PREZZO = {
    "ssb": {
        "nome": "Statistics Norway (SSB), tabella 03024",
        "url": "https://www.ssb.no/en/statbank/table/03024",
        "licenza": "CC BY 4.0",
        "licenza_url": "https://creativecommons.org/licenses/by/4.0/",
        "stato": "automatica",
    },
    "rnm": {
        "nome": "FranceAgriMer, RNM Rungis",
        "url": "https://rnm.franceagrimer.fr/",
        "licenza": "Da verificare per questa mercuriale",
        "licenza_url": "https://rnm.franceagrimer.fr/",
        "stato": "da validare sulla pagina, poi automatica",
    },
    "bmti": {
        "nome": "BMTI, Ittico dati — prezzi all'ingrosso dei mercati ittici italiani",
        "url": "https://www.bmti.it/",
        "licenza": "Da confermare per iscritto",
        "licenza_url": "https://www.bmti.it/",
        "stato": "da file esportato, in attesa di conferma",
    },
}

# --------------------------------------------------------------------------
# Specie
# --------------------------------------------------------------------------

PRODOTTI = [
    {
        "id": "salmone",
        "nome": "Salmone atlantico",
        "sottotitolo": "Fresco, esportazioni dalla Norvegia; importazioni italiane",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del salmone: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Prezzo medio settimanale all'esportazione del salmone norvegese in euro, volumi, posizione stagionale su cinque anni e importazioni italiane. Fonti dichiarate, aggiornamento settimanale.",
        "prezzo": {"serie": "ssb.laks.fersk.prezzo", "fonte": "ssb", "cambio": "bce.cambio.nok.eur.settimanale"},
        "flussi": {
            "codici": ["03021411", "03021419"],
            "descrizione": "Salmone atlantico d'allevamento, fresco o refrigerato",
            "partner": ["WORLD", "NO", "DK"],
            "principale": "NO",
        },
        "domande": [
            ("Questo prezzo è alto per il periodo?", "La banda in apertura confronta la settimana con le stesse settimane dei cinque anni precedenti."),
            ("Corrisponde al prezzo che mi chiede il fornitore?", "No. È il valore medio all'esportazione dalla Norvegia, su tutte le pezzature e destinazioni. Serve come riferimento di andamento, non come quotazione contrattuale."),
            ("Quanto ne arriva in Italia?", "Il riquadro sui flussi mostra le importazioni italiane mensili e il totale mobile a dodici mesi."),
        ],
    },
    {
        "id": "orata",
        "nome": "Orata",
        "sottotitolo": "Allevamento, quotazione all'ingrosso a Rungis; importazioni da Grecia e Turchia",
        "pubblicato": True,
        "titolo_pagina": "Prezzo dell'orata: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Quotazione settimanale all'ingrosso dell'orata d'allevamento a Rungis, posizione stagionale e importazioni italiane da Grecia e Turchia.",
        "prezzo": {"serie": "rnm.rungis.orata.allevamento", "fonte": "rnm",
                   "rnm_etichetta": "dorade royale élevage 400/600",
                   "anagrafica": {"prodotto": "Orata d'allevamento", "presentazione": "Intera", "conservazione": "Fresca", "pezzatura": "400-600 g"}},
        "flussi": {
            "codici": ["03028530"],
            "descrizione": "Orata (Sparus aurata), fresca o refrigerata",
            "partner": ["WORLD", "GR", "TR", "HR"],
            "principale": "GR",
        },
        "domande": [
            ("Perché un prezzo francese?", "In Italia non esiste una rilevazione pubblica settimanale dell'orata. Rungis è il mercato all'ingrosso europeo con la rilevazione più continua e documentata, e segue lo stesso prodotto greco e turco che arriva in Italia."),
            ("Quanto pesa la Grecia?", "Il riquadro sugli arrivi mostra la quota della provenienza principale sulle importazioni italiane degli ultimi dodici mesi."),
        ],
    },
    {
        "id": "spigola",
        "nome": "Spigola",
        "sottotitolo": "Allevamento, quotazione all'ingrosso a Rungis; importazioni da Grecia e Turchia",
        "pubblicato": True,
        "titolo_pagina": "Prezzo della spigola: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Quotazione settimanale all'ingrosso della spigola d'allevamento a Rungis, posizione stagionale e importazioni italiane da Grecia e Turchia.",
        "prezzo": {"serie": "rnm.rungis.spigola.allevamento", "fonte": "rnm",
                   "rnm_etichetta": "bar élevage 400/600",
                   "anagrafica": {"prodotto": "Spigola d'allevamento", "presentazione": "Intera", "conservazione": "Fresca", "pezzatura": "400-600 g"}},
        "flussi": {
            "codici": ["03028410"],
            "descrizione": "Spigola (Dicentrarchus labrax), fresca o refrigerata",
            "partner": ["WORLD", "GR", "TR", "HR"],
            "principale": "GR",
        },
        "domande": [
            ("Perché un prezzo francese?", "In Italia non esiste una rilevazione pubblica settimanale della spigola. Rungis è il mercato all'ingrosso europeo con la rilevazione più continua e documentata."),
        ],
    },
    {
        "id": "polpo",
        "nome": "Polpo",
        "sottotitolo": "Congelato, quotazione all'ingrosso a Rungis; importazioni da Marocco e Mauritania",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del polpo: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Quotazione settimanale all'ingrosso del polpo congelato a Rungis, posizione stagionale e importazioni italiane da Marocco e Mauritania.",
        "prezzo": {"serie": "rnm.rungis.polpo.congelato", "fonte": "rnm",
                   "rnm_etichetta": "poulpe maroc congelé",
                   "anagrafica": {"prodotto": "Polpo (Octopus vulgaris)", "presentazione": "Intero", "conservazione": "Congelato", "pezzatura": "Taglia secondo la mercuriale"}},
        "flussi": {
            "codici": ["03075100", "03075200"],
            "descrizione": "Polpo, fresco e congelato",
            "partner": ["WORLD", "MA", "MR", "ES"],
            "principale": "MA",
        },
        "domande": [
            ("Dove si forma il prezzo?", "Alle aste marocchine e mauritane e nei congelatori. Rungis quota il polpo marocchino congelato per taglia ed è il riferimento che gli importatori guardano."),
        ],
    },
    {
        "id": "gambero",
        "nome": "Gambero",
        "sottotitolo": "Vannamei e gambero argentino, congelati; importazioni da Ecuador, Argentina e India",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del gambero: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Quotazione settimanale all'ingrosso del gambero congelato a Rungis, posizione stagionale e importazioni italiane da Ecuador, Argentina e India.",
        "prezzo": {"serie": "rnm.rungis.gambero.congelato", "fonte": "rnm",
                   "rnm_etichetta": "crevette congelée",
                   "anagrafica": {"prodotto": "Gambero d'allevamento (Penaeus vannamei)", "presentazione": "Intero", "conservazione": "Congelato", "pezzatura": "Calibro secondo la mercuriale"}},
        "flussi": {
            "codici": ["03061792", "03061799"],
            "descrizione": "Gamberi congelati, genere Penaeus e altri",
            "partner": ["WORLD", "EC", "AR", "IN", "ES"],
            "principale": "EC",
        },
        "domande": [
            ("Vannamei e argentino insieme?", "I codici doganali li tengono separati: il vannamei nel genere Penaeus, l'argentino negli altri gamberi congelati. Il riquadro sugli arrivi li somma; le provenienze li distinguono."),
        ],
    },
    {
        "id": "merluzzo",
        "nome": "Merluzzo",
        "sottotitolo": "Fresco, congelato e salato; importazioni da Norvegia e Islanda",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del merluzzo: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Quotazione settimanale all'ingrosso del merluzzo a Rungis, posizione stagionale e importazioni italiane di merluzzo fresco, congelato e salato da Norvegia e Islanda.",
        "prezzo": {"serie": "rnm.rungis.merluzzo.fresco", "fonte": "rnm",
                   "rnm_etichetta": "cabillaud",
                   "anagrafica": {"prodotto": "Merluzzo atlantico (Gadus morhua)", "presentazione": "Intero eviscerato", "conservazione": "Fresco", "pezzatura": "Secondo la mercuriale"}},
        "flussi": {
            "codici": ["03025110", "03036310", "03056200"],
            "descrizione": "Merluzzo fresco, congelato e salato (baccalà)",
            "partner": ["WORLD", "NO", "IS", "DK"],
            "principale": "NO",
        },
        "domande": [
            ("Fresco, congelato e baccalà insieme?", "Il riquadro sugli arrivi somma i tre codici doganali, perché in Italia il merluzzo entra soprattutto salato. Il prezzo di riferimento è invece quello del fresco."),
        ],
    },
    {
        "id": "tonno",
        "nome": "Tonno",
        "sottotitolo": "Pinna gialla fresco e congelato; importazioni",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del tonno: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Quotazione settimanale all'ingrosso del tonno pinna gialla a Rungis, posizione stagionale e importazioni italiane di tonno fresco e congelato.",
        "prezzo": {"serie": "rnm.rungis.tonno.pinna_gialla", "fonte": "rnm",
                   "rnm_etichetta": "thon albacore",
                   "anagrafica": {"prodotto": "Tonno pinna gialla (Thunnus albacares)", "presentazione": "Lombo", "conservazione": "Fresco", "pezzatura": "Secondo la mercuriale"}},
        "flussi": {
            "codici": ["03023210", "03023290", "03034220", "03034290"],
            "descrizione": "Tonno pinna gialla, fresco e congelato",
            "partner": ["WORLD", "ES", "FR", "VN"],
            "principale": "ES",
        },
        "domande": [
            ("E il tonno in scatola?", "Segue un'altra filiera e altri codici doganali. Questa scheda copre il pinna gialla fresco e congelato; la conserva potrà avere una scheda propria."),
        ],
    },
    {
        "id": "pesce_spada",
        "nome": "Pesce spada",
        "sottotitolo": "Fresco e congelato; importazioni",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del pesce spada: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Quotazione settimanale all'ingrosso del pesce spada a Rungis, posizione stagionale e importazioni italiane di pesce spada fresco e congelato.",
        "prezzo": {"serie": "rnm.rungis.pesce_spada", "fonte": "rnm",
                   "rnm_etichetta": "espadon",
                   "anagrafica": {"prodotto": "Pesce spada (Xiphias gladius)", "presentazione": "Intero o tranci", "conservazione": "Fresco", "pezzatura": "Secondo la mercuriale"}},
        "flussi": {
            "codici": ["03024700", "03035700"],
            "descrizione": "Pesce spada, fresco e congelato",
            "partner": ["WORLD", "ES", "VN", "CL"],
            "principale": "ES",
        },
        "domande": [],
    },
    {
        "id": "cozze",
        "nome": "Cozze",
        "sottotitolo": "Prezzi all'ingrosso sui mercati ittici italiani; importazioni da Spagna e Grecia",
        "pubblicato": True,
        "titolo_pagina": "Prezzo delle cozze: quotazioni settimanali e import in Italia",
        "descrizione_pagina": "Prezzo settimanale all'ingrosso delle cozze sui mercati ittici italiani (BMTI), posizione stagionale e importazioni italiane da Spagna e Grecia.",
        "prezzo": {"serie": "bmti.ingrosso.cozze", "fonte": "bmti",
                   "anagrafica": {"prodotto": "Cozze (Mytilus galloprovincialis)", "presentazione": "Vive, in rete", "conservazione": "Fresche", "pezzatura": "Non distinta"}},
        "flussi": {
            "codici": ["03073110"],
            "descrizione": "Cozze vive, fresche o refrigerate",
            "partner": ["WORLD", "ES", "GR", "FR"],
            "principale": "ES",
        },
        "domande": [
            ("Perché qui la fonte è italiana?", "Le cozze sono un prodotto in gran parte nazionale: il riferimento sono i mercati all'ingrosso italiani rilevati da BMTI, non un mercato estero."),
        ],
    },
    {
        "id": "vongole",
        "nome": "Vongole",
        "sottotitolo": "Vongola verace, prezzi all'ingrosso sui mercati ittici italiani",
        "pubblicato": True,
        "titolo_pagina": "Prezzo delle vongole: quotazioni settimanali sui mercati italiani",
        "descrizione_pagina": "Prezzo settimanale all'ingrosso della vongola verace sui mercati ittici italiani (BMTI), posizione stagionale e importazioni.",
        "prezzo": {"serie": "bmti.ingrosso.vongole", "fonte": "bmti",
                   "anagrafica": {"prodotto": "Vongola verace (Ruditapes philippinarum)", "presentazione": "Vive", "conservazione": "Fresche", "pezzatura": "Non distinta"}},
        "flussi": {
            "codici": ["03077100"],
            "descrizione": "Vongole vive, fresche o refrigerate",
            "partner": ["WORLD", "ES", "FR"],
            "principale": "ES",
        },
        "domande": [
            ("Perché quasi nessuna importazione?", "La vongola verace è un prodotto quasi interamente nazionale, dal delta del Po e dalle lagune adriatiche. Il prezzo si forma sui mercati italiani."),
        ],
    },
]

# --------------------------------------------------------------------------
# Traduzioni inglesi delle etichette di questo file
# --------------------------------------------------------------------------

TRADUZIONI_EN_PRODOTTI = {
    "Salmone atlantico": "Atlantic salmon",
    "Fresco, esportazioni dalla Norvegia; importazioni italiane": "Fresh, exports from Norway; Italian imports",
    "Prezzo del salmone: quotazioni settimanali e import in Italia": "Salmon price: weekly quotations and imports into Italy",
    "Prezzo medio settimanale all'esportazione del salmone norvegese in euro, volumi, posizione stagionale su cinque anni e importazioni italiane. Fonti dichiarate, aggiornamento settimanale.": "Weekly average export price of Norwegian salmon in euro, volumes, five-year seasonal position and Italian imports. Sources disclosed, updated weekly.",
    "Salmone atlantico d'allevamento, fresco o refrigerato": "Farmed Atlantic salmon, fresh or chilled",
    "Questo prezzo è alto per il periodo?": "Is this price high for the time of year?",
    "La banda in apertura confronta la settimana con le stesse settimane dei cinque anni precedenti.": "The band at the top compares the week with the same weeks of the previous five years.",
    "Corrisponde al prezzo che mi chiede il fornitore?": "Is this the price my supplier is asking?",
    "No. È il valore medio all'esportazione dalla Norvegia, su tutte le pezzature e destinazioni. Serve come riferimento di andamento, non come quotazione contrattuale.": "No. It is the average export value from Norway, across all sizes and destinations. It serves as a trend reference, not as a contractual quotation.",
    "Quanto ne arriva in Italia?": "How much of it reaches Italy?",
    "Il riquadro sui flussi mostra le importazioni italiane mensili e il totale mobile a dodici mesi.": "The flows panel shows monthly Italian imports and the rolling twelve-month total.",

    "Orata": "Gilt-head sea bream",
    "Allevamento, quotazione all'ingrosso a Rungis; importazioni da Grecia e Turchia": "Farmed, wholesale quotation at Rungis; imports from Greece and Türkiye",
    "Prezzo dell'orata: quotazioni settimanali e import in Italia": "Sea bream price: weekly quotations and imports into Italy",
    "Quotazione settimanale all'ingrosso dell'orata d'allevamento a Rungis, posizione stagionale e importazioni italiane da Grecia e Turchia.": "Weekly wholesale quotation of farmed sea bream at Rungis, seasonal position and Italian imports from Greece and Türkiye.",
    "Orata d'allevamento": "Farmed gilt-head sea bream",
    "Orata (Sparus aurata), fresca o refrigerata": "Gilt-head sea bream (Sparus aurata), fresh or chilled",
    "Perché un prezzo francese?": "Why a French price?",
    "In Italia non esiste una rilevazione pubblica settimanale dell'orata. Rungis è il mercato all'ingrosso europeo con la rilevazione più continua e documentata, e segue lo stesso prodotto greco e turco che arriva in Italia.": "There is no public weekly survey of sea bream prices in Italy. Rungis is the European wholesale market with the most continuous and documented survey, and it tracks the same Greek and Turkish product that reaches Italy.",
    "Quanto pesa la Grecia?": "How much does Greece weigh?",
    "Il riquadro sugli arrivi mostra la quota della provenienza principale sulle importazioni italiane degli ultimi dodici mesi.": "The imports panel shows the share of the main origin in Italian imports over the last twelve months.",

    "Spigola": "European sea bass",
    "Prezzo della spigola: quotazioni settimanali e import in Italia": "Sea bass price: weekly quotations and imports into Italy",
    "Quotazione settimanale all'ingrosso della spigola d'allevamento a Rungis, posizione stagionale e importazioni italiane da Grecia e Turchia.": "Weekly wholesale quotation of farmed sea bass at Rungis, seasonal position and Italian imports from Greece and Türkiye.",
    "Spigola d'allevamento": "Farmed European sea bass",
    "Spigola (Dicentrarchus labrax), fresca o refrigerata": "European sea bass (Dicentrarchus labrax), fresh or chilled",
    "In Italia non esiste una rilevazione pubblica settimanale della spigola. Rungis è il mercato all'ingrosso europeo con la rilevazione più continua e documentata.": "There is no public weekly survey of sea bass prices in Italy. Rungis is the European wholesale market with the most continuous and documented survey.",

    "Polpo": "Octopus",
    "Congelato, quotazione all'ingrosso a Rungis; importazioni da Marocco e Mauritania": "Frozen, wholesale quotation at Rungis; imports from Morocco and Mauritania",
    "Prezzo del polpo: quotazioni settimanali e import in Italia": "Octopus price: weekly quotations and imports into Italy",
    "Quotazione settimanale all'ingrosso del polpo congelato a Rungis, posizione stagionale e importazioni italiane da Marocco e Mauritania.": "Weekly wholesale quotation of frozen octopus at Rungis, seasonal position and Italian imports from Morocco and Mauritania.",
    "Polpo (Octopus vulgaris)": "Octopus (Octopus vulgaris)",
    "Polpo, fresco e congelato": "Octopus, fresh and frozen",
    "Dove si forma il prezzo?": "Where is the price formed?",
    "Alle aste marocchine e mauritane e nei congelatori. Rungis quota il polpo marocchino congelato per taglia ed è il riferimento che gli importatori guardano.": "At the Moroccan and Mauritanian auctions and in the cold stores. Rungis quotes frozen Moroccan octopus by size and is the reference importers look at.",

    "Gambero": "Shrimp",
    "Vannamei e gambero argentino, congelati; importazioni da Ecuador, Argentina e India": "Vannamei and Argentine red shrimp, frozen; imports from Ecuador, Argentina and India",
    "Prezzo del gambero: quotazioni settimanali e import in Italia": "Shrimp price: weekly quotations and imports into Italy",
    "Quotazione settimanale all'ingrosso del gambero congelato a Rungis, posizione stagionale e importazioni italiane da Ecuador, Argentina e India.": "Weekly wholesale quotation of frozen shrimp at Rungis, seasonal position and Italian imports from Ecuador, Argentina and India.",
    "Gambero d'allevamento (Penaeus vannamei)": "Farmed shrimp (Penaeus vannamei)",
    "Gamberi congelati, genere Penaeus e altri": "Frozen shrimps, genus Penaeus and others",
    "Vannamei e argentino insieme?": "Vannamei and Argentine together?",
    "I codici doganali li tengono separati: il vannamei nel genere Penaeus, l'argentino negli altri gamberi congelati. Il riquadro sugli arrivi li somma; le provenienze li distinguono.": "Customs codes keep them apart: vannamei under genus Penaeus, Argentine under other frozen shrimps. The imports panel sums them; the origins tell them apart.",

    "Merluzzo": "Cod",
    "Fresco, congelato e salato; importazioni da Norvegia e Islanda": "Fresh, frozen and salted; imports from Norway and Iceland",
    "Prezzo del merluzzo: quotazioni settimanali e import in Italia": "Cod price: weekly quotations and imports into Italy",
    "Quotazione settimanale all'ingrosso del merluzzo a Rungis, posizione stagionale e importazioni italiane di merluzzo fresco, congelato e salato da Norvegia e Islanda.": "Weekly wholesale quotation of cod at Rungis, seasonal position and Italian imports of fresh, frozen and salted cod from Norway and Iceland.",
    "Merluzzo atlantico (Gadus morhua)": "Atlantic cod (Gadus morhua)",
    "Merluzzo fresco, congelato e salato (baccalà)": "Cod, fresh, frozen and salted",
    "Fresco, congelato e baccalà insieme?": "Fresh, frozen and salted together?",
    "Il riquadro sugli arrivi somma i tre codici doganali, perché in Italia il merluzzo entra soprattutto salato. Il prezzo di riferimento è invece quello del fresco.": "The imports panel sums the three customs codes, because cod enters Italy mostly salted. The reference price, however, is for fresh cod.",

    "Tonno": "Tuna",
    "Pinna gialla fresco e congelato; importazioni": "Yellowfin, fresh and frozen; imports",
    "Prezzo del tonno: quotazioni settimanali e import in Italia": "Tuna price: weekly quotations and imports into Italy",
    "Quotazione settimanale all'ingrosso del tonno pinna gialla a Rungis, posizione stagionale e importazioni italiane di tonno fresco e congelato.": "Weekly wholesale quotation of yellowfin tuna at Rungis, seasonal position and Italian imports of fresh and frozen tuna.",
    "Tonno pinna gialla (Thunnus albacares)": "Yellowfin tuna (Thunnus albacares)",
    "Tonno pinna gialla, fresco e congelato": "Yellowfin tuna, fresh and frozen",
    "E il tonno in scatola?": "What about canned tuna?",
    "Segue un'altra filiera e altri codici doganali. Questa scheda copre il pinna gialla fresco e congelato; la conserva potrà avere una scheda propria.": "It follows a different chain and different customs codes. This page covers fresh and frozen yellowfin; canned tuna may get its own page.",

    "Pesce spada": "Swordfish",
    "Fresco e congelato; importazioni": "Fresh and frozen; imports",
    "Prezzo del pesce spada: quotazioni settimanali e import in Italia": "Swordfish price: weekly quotations and imports into Italy",
    "Quotazione settimanale all'ingrosso del pesce spada a Rungis, posizione stagionale e importazioni italiane di pesce spada fresco e congelato.": "Weekly wholesale quotation of swordfish at Rungis, seasonal position and Italian imports of fresh and frozen swordfish.",
    "Pesce spada (Xiphias gladius)": "Swordfish (Xiphias gladius)",
    "Pesce spada, fresco e congelato": "Swordfish, fresh and frozen",

    "Cozze": "Mussels",
    "Prezzi all'ingrosso sui mercati ittici italiani; importazioni da Spagna e Grecia": "Wholesale prices on Italian fish markets; imports from Spain and Greece",
    "Prezzo delle cozze: quotazioni settimanali e import in Italia": "Mussel price: weekly quotations and imports into Italy",
    "Prezzo settimanale all'ingrosso delle cozze sui mercati ittici italiani (BMTI), posizione stagionale e importazioni italiane da Spagna e Grecia.": "Weekly wholesale price of mussels on Italian fish markets (BMTI), seasonal position and Italian imports from Spain and Greece.",
    "Cozze (Mytilus galloprovincialis)": "Mussels (Mytilus galloprovincialis)",
    "Cozze vive, fresche o refrigerate": "Live mussels, fresh or chilled",
    "Perché qui la fonte è italiana?": "Why is the source Italian here?",
    "Le cozze sono un prodotto in gran parte nazionale: il riferimento sono i mercati all'ingrosso italiani rilevati da BMTI, non un mercato estero.": "Mussels are largely a domestic product: the reference is the Italian wholesale markets surveyed by BMTI, not a foreign market.",

    "Vongole": "Clams",
    "Vongola verace, prezzi all'ingrosso sui mercati ittici italiani": "Manila clam, wholesale prices on Italian fish markets",
    "Prezzo delle vongole: quotazioni settimanali sui mercati italiani": "Clam price: weekly quotations on Italian markets",
    "Prezzo settimanale all'ingrosso della vongola verace sui mercati ittici italiani (BMTI), posizione stagionale e importazioni.": "Weekly wholesale price of Manila clams on Italian fish markets (BMTI), seasonal position and imports.",
    "Vongola verace (Ruditapes philippinarum)": "Manila clam (Ruditapes philippinarum)",
    "Vongole vive, fresche o refrigerate": "Live clams, fresh or chilled",
    "Perché quasi nessuna importazione?": "Why almost no imports?",
    "La vongola verace è un prodotto quasi interamente nazionale, dal delta del Po e dalle lagune adriatiche. Il prezzo si forma sui mercati italiani.": "Manila clams are an almost entirely domestic product, from the Po delta and the Adriatic lagoons. The price is formed on Italian markets.",

    # anagrafica comune
    "Intera": "Whole", "Intero": "Whole", "Fresca": "Fresh", "Fresche": "Fresh", "Fresco": "Fresh",
    "Congelato": "Frozen", "Vive, in rete": "Live, netted", "Vive": "Live",
    "400-600 g": "400-600 g", "Non distinta": "Not distinguished",
    "Taglia secondo la mercuriale": "Size as per the market list",
    "Calibro secondo la mercuriale": "Grade as per the market list",
    "Secondo la mercuriale": "As per the market list",
    "Intero eviscerato": "Whole gutted", "Lombo": "Loin", "Intero o tranci": "Whole or steaks",
    "Mercato all'ingrosso di Rungis (Parigi)": "Rungis wholesale market (Paris)",
    "Mercati ittici all'ingrosso italiani": "Italian wholesale fish markets",
    "Ingrosso": "Wholesale",
    "Quotazione all'ingrosso, media settimanale delle rilevazioni giornaliere": "Wholesale quotation, weekly average of daily surveys",
    "Prezzo all'ingrosso, media settimanale": "Wholesale price, weekly average",
    "Media delle quotazioni giornaliere della settimana ISO": "Average of the daily quotations of the ISO week",
    "Media delle rilevazioni settimanali dei mercati": "Average of the weekly market surveys",
    "Prezzo di mercato francese: segue lo stesso prodotto che arriva in Italia, ma non è un prezzo italiano.": "French market price: it tracks the same product that reaches Italy, but it is not an Italian price.",
    "Prezzo rilevato sui mercati ittici italiani; la copertura dei mercati può variare fra le settimane.": "Price surveyed on Italian fish markets; market coverage may vary between weeks.",
    "Da verificare per questa mercuriale": "To be verified for this market list",
    "Da confermare per iscritto": "To be confirmed in writing",
    "FranceAgriMer, RNM Rungis": "FranceAgriMer, RNM Rungis",
    "BMTI, Ittico dati — prezzi all'ingrosso dei mercati ittici italiani": "BMTI, Ittico dati — wholesale prices on Italian fish markets",
    "Importazione (valore dichiarato in dogana)": "Import (value declared at customs)",
    "Valore unitario delle importazioni": "Import unit value",
    "Non distinta dalla fonte": "Not distinguished by the source",
    "Secondo la nomenclatura combinata": "As per the Combined Nomenclature",
    "Riuso consentito con attribuzione": "Reuse permitted with attribution",
    "Valore diviso quantità, somma dei codici doganali indicati.": "Value divided by quantity, sum of the customs codes listed.",
    "Lo Stato di importazione è spesso il punto di ingresso doganale, non la destinazione finale. Il valore in dogana comprende il trasporto fino alla frontiera.": "The importing Member State is often the customs point of entry, not the final destination. The customs value includes transport to the border.",
}


def pubblicati() -> list[dict]:
    return [p for p in PRODOTTI if p.get("pubblicato")]


def per_id(identificativo: str) -> dict | None:
    for prodotto in PRODOTTI:
        if prodotto["id"] == identificativo:
            return prodotto
    return None


def serie_flussi(prodotto: dict, partner: str) -> str:
    """Identificativo della serie Comext di un prodotto per un partner."""
    return f"comext.it.import.{prodotto['id']}.{partner.lower()}.mensile"


def nome_paese(codice: str, lingua: str = "it") -> str:
    voce = PAESI.get(codice, (codice, codice))
    return voce[0] if lingua == "it" else voce[1]
