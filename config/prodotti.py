"""Registro delle specie pubblicate, delle loro serie e delle fonti.

Criterio di scelta delle fonti, nell'ordine:

1. ente statistico o pubblico (Statistics Norway, Commissione europea,
   Eurostat, BCE): il dato è rilevato con metodo dichiarato;
2. riuso libero dichiarato dalla fonte, senza autorizzazioni da chiedere;
3. acquisizione automatica da un indirizzo pubblico, senza aggirare blocchi;
4. serie misurata prima di entrare qui: una specie è in elenco solo se il
   suo prezzo settimanale si è dimostrato leggibile sui dati veri.

Per ogni specie:

* `prezzo` è la serie settimanale di riferimento. Per il salmone è il
  prezzo all'esportazione norvegese (SSB). Per le altre è il valore
  unitario delle importazioni in Italia da paesi extra-UE, per
  provenienza, dai dati doganali settimanali pubblicati da EUMOFA;
* `eumofa` dice quali codici doganali e quali provenienze leggere dal
  file settimanale, a otto cifre. `principale` è la provenienza
  del prezzo in copertina ("WORLD" = tutte insieme); `altre` sono le
  provenienze mostrate come media mobile a quattro settimane, perché
  settimana per settimana il loro prezzo salta con il mix dei carichi;
* `flussi` sono le importazioni italiane mensili da Eurostat Comext,
  comprese le provenienze UE (Grecia, Croazia, Spagna) che il file
  settimanale non copre.

I codici vanno riverificati a ogni gennaio: la nomenclatura cambia.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Paesi partner (codice -> nome italiano, nome inglese)
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
    "SN": ("Senegal", "Senegal"),
    "TN": ("Tunisia", "Tunisia"),
    "AL": ("Albania", "Albania"),
    "EC": ("Ecuador", "Ecuador"),
    "AR": ("Argentina", "Argentina"),
    "IN": ("India", "India"),
    "DK": ("Danimarca", "Denmark"),
    "SE": ("Svezia", "Sweden"),
    "NL": ("Paesi Bassi", "Netherlands"),
    "PL": ("Polonia", "Poland"),
    "FR": ("Francia", "France"),
    "CL": ("Cile", "Chile"),
    "LK": ("Sri Lanka", "Sri Lanka"),
    "US": ("Stati Uniti", "United States"),
    "CA": ("Canada", "Canada"),
}

# Come EUMOFA scrive i paesi nel file settimanale. Più grafie per lo stesso
# paese: se la fonte ne cambia una, la serie non si svuota in silenzio.
PAESI_EUMOFA = {
    "TR": ("Turkey", "Türkiye", "Turkiye"),
    "MA": ("Morocco",),
    "MR": ("Mauritania",),
    "SN": ("Senegal",),
    "TN": ("Tunisia",),
    "AL": ("Albania",),
    "EC": ("Ecuador",),
    "AR": ("Argentina",),
    "IN": ("India",),
    "CL": ("Chile",),
    "LK": ("Sri Lanka",),
    "US": ("United States", "United States of America", "USA"),
    "CA": ("Canada",),
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
    "eumofa": {
        "nome": "EUMOFA (Commissione europea), importazioni UE settimanali da dati doganali",
        "url": "https://eumofa.eu/",
        "licenza": "CC BY 4.0",
        "licenza_url": "https://creativecommons.org/licenses/by/4.0/",
        "stato": "automatica",
    },
}

MERCATO_EUMOFA = "Importazioni in Italia da paesi extra-UE"

# --------------------------------------------------------------------------
# Specie
# --------------------------------------------------------------------------

D_FRONTIERA = ("È il prezzo che pago al fornitore?",
               "No. È il valore medio dichiarato in dogana da chi importa in Italia, su tutte le pezzature. Serve per confrontare il proprio prezzo d'acquisto con la media e per leggere l'andamento, non come quotazione.")
D_RITARDO = ("Quanto è aggiornato?",
             "Il dato esce ogni settimana e copre fino a circa due settimane prima: la settimana più recente è sempre incompleta alla fonte e viene pubblicata solo quando è chiusa.")

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
            "codici": ["03021400"],
            "descrizione": "Salmone atlantico, fresco o refrigerato",
            # La Norvegia non compare: il salmone norvegese è sdoganato in altri
            # Stati dell'Unione e arriva in Italia come scambio interno. Eurostat
            # registra il paese di spedizione. "auto" = la provenienza più grande.
            "partner": ["WORLD", "SE", "DK", "NL", "PL"],
            "principale": "auto",
        },
        "domande": [
            ("Questo prezzo è alto per il periodo?", "La banda in apertura confronta la settimana con le stesse settimane dei cinque anni precedenti."),
            ("Corrisponde al prezzo che mi chiede il fornitore?", "No. È il valore medio all'esportazione dalla Norvegia, su tutte le pezzature e destinazioni. Serve come riferimento di andamento, non come quotazione contrattuale."),
            ("Quanto ne arriva in Italia?", "Il riquadro sui flussi mostra le importazioni italiane mensili e il totale mobile a dodici mesi."),
            ("Perché tra le provenienze non c'è la Norvegia?", "Perché il salmone norvegese entra nell'Unione da altri paesi, soprattutto nordici, e da lì arriva in Italia come scambio interno. La statistica registra il paese di spedizione, non quello di allevamento."),
        ],
    },
    {
        "id": "orata",
        "nome": "Orata",
        "sottotitolo": "Fresca, importata in Italia dalla Turchia; Grecia e Croazia nel dato mensile",
        "pubblicato": True,
        "titolo_pagina": "Prezzo dell'orata all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio settimanale dell'orata fresca importata in Italia dalla Turchia, con i volumi, e importazioni mensili da Grecia e Croazia. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.orata.tr.settimanale", "fonte": "eumofa"},
        "eumofa": {"codici": ["03028530"], "principale": "TR", "altre": ["AL", "TN"],
                   "prodotto": "Orata (Sparus aurata)", "presentazione": "Intera", "conservazione": "Fresca"},
        "flussi": {
            "codici": ["03028530"],
            "descrizione": "Orata (Sparus aurata), fresca o refrigerata",
            "partner": ["WORLD", "GR", "TR", "HR"],
            "principale": "GR",
        },
        "domande": [
            ("Perché il prezzo è quello turco?", "Perché è l'unico che esiste ogni settimana: la dogana registra le importazioni da fuori Unione, e la Turchia è la prima provenienza extra-UE. Gli arrivi da Grecia e Croazia sono scambi interni all'Unione e la statistica ufficiale li pubblica solo ogni mese: sono nel riquadro sugli arrivi."),
            D_FRONTIERA, D_RITARDO,
        ],
    },
    {
        "id": "spigola",
        "nome": "Spigola",
        "sottotitolo": "Fresca, importata in Italia dalla Turchia; Grecia e Croazia nel dato mensile",
        "pubblicato": True,
        "titolo_pagina": "Prezzo della spigola all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio settimanale della spigola fresca importata in Italia dalla Turchia, con i volumi, e importazioni mensili da Grecia e Croazia. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.spigola.tr.settimanale", "fonte": "eumofa"},
        "eumofa": {"codici": ["03028410"], "principale": "TR", "altre": [],
                   "prodotto": "Spigola (Dicentrarchus labrax)", "presentazione": "Intera", "conservazione": "Fresca"},
        "flussi": {
            "codici": ["03028410"],
            "descrizione": "Spigola (Dicentrarchus labrax), fresca o refrigerata",
            "partner": ["WORLD", "GR", "TR", "HR"],
            "principale": "GR",
        },
        "domande": [
            ("Perché il prezzo è quello turco?", "Perché è l'unico che esiste ogni settimana: la dogana registra le importazioni da fuori Unione, e la Turchia è la prima provenienza extra-UE. Gli arrivi da Grecia e Croazia sono scambi interni all'Unione e la statistica ufficiale li pubblica solo ogni mese: sono nel riquadro sugli arrivi."),
            D_FRONTIERA, D_RITARDO,
        ],
    },
    {
        "id": "gambero",
        "nome": "Gambero",
        "sottotitolo": "Congelato, importato in Italia dall'Ecuador; Argentina e India a confronto",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del gambero all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio settimanale del gambero congelato importato in Italia dall'Ecuador, con i volumi, e confronto con Argentina e India. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.gambero.ec.settimanale", "fonte": "eumofa"},
        "eumofa": {"codici": ["03061792", "03061799"], "principale": "EC", "altre": ["AR", "IN"],
                   "prodotto": "Gamberi e gamberetti", "presentazione": "Interi o code", "conservazione": "Congelato"},
        "flussi": {
            "codici": ["03061792", "03061799"],
            "descrizione": "Gamberi congelati, genere Penaeus e altri",
            "partner": ["WORLD", "EC", "AR", "IN", "ES"],
            "principale": "EC",
        },
        "domande": [
            ("Perché solo l'Ecuador ha il prezzo settimanale?", "Perché dall'Ecuador arriva un prodotto omogeneo, il vannamei, e il prezzo medio si muove come il mercato. Da Argentina e India arrivano prodotti e pezzature diversi: da una settimana all'altra il prezzo medio salta con il mix dei carichi, quindi lo mostriamo come media delle ultime quattro settimane."),
            D_FRONTIERA, D_RITARDO,
        ],
    },
    {
        "id": "polpo",
        "nome": "Polpo",
        "sottotitolo": "Importato in Italia dal Marocco; Senegal e Mauritania a confronto",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del polpo all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio settimanale del polpo importato in Italia dal Marocco, con i volumi, e confronto con Senegal e Mauritania. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.polpo.ma.settimanale", "fonte": "eumofa"},
        "eumofa": {"codici": ["03075100", "03075200"], "principale": "MA", "altre": ["SN", "MR"],
                   "prodotto": "Polpo (Octopus spp.)", "presentazione": "Intero", "conservazione": "Congelato, in piccola parte fresco"},
        "flussi": {
            "codici": ["03075100", "03075200"],
            "descrizione": "Polpo, fresco e congelato",
            "partner": ["WORLD", "MA", "SN", "MR", "ES"],
            "principale": "MA",
        },
        "domande": [
            ("Perché il Marocco in copertina?", "È la prima provenienza del polpo che entra in Italia e l'unica con arrivi regolari ogni settimana. Senegal e Mauritania hanno carichi più radi: per loro mostriamo la media delle ultime quattro settimane."),
            D_FRONTIERA, D_RITARDO,
        ],
    },
    {
        "id": "calamaro",
        "nome": "Calamaro",
        "sottotitolo": "Loligo vulgaris congelato, importato in Italia, quasi tutto dal Marocco",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del calamaro all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio settimanale del calamaro congelato (Loligo vulgaris) importato in Italia, con i volumi. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.calamaro.world.settimanale", "fonte": "eumofa"},
        "eumofa": {"codici": ["03074331"], "principale": "WORLD", "altre": ["MA"],
                   "prodotto": "Calamaro (Loligo vulgaris)", "presentazione": "Intero o pulito", "conservazione": "Congelato"},
        "flussi": {
            "codici": ["03074331", "03074333", "03074335", "03074338"],
            "descrizione": "Calamari del genere Loligo, congelati",
            "partner": ["WORLD", "MA", "ES", "IN"],
            "principale": "MA",
        },
        "domande": [
            ("E il totano?", "Ha codici doganali propri e prezzi molto diversi: qui c'è solo il calamaro Loligo vulgaris, che la dogana distingue. Tenerli separati è quello che rende leggibile il prezzo."),
            D_FRONTIERA, D_RITARDO,
        ],
    },
    {
        "id": "seppia",
        "nome": "Seppia",
        "sottotitolo": "Congelata, importata in Italia da Senegal, Marocco e Tunisia; media a quattro settimane",
        "pubblicato": True,
        "titolo_pagina": "Prezzo della seppia all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio della seppia congelata importata in Italia, media mobile a quattro settimane, con i volumi settimanali e le provenienze. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.seppia.world.settimanale", "fonte": "eumofa", "media_settimane": 4},
        "eumofa": {"codici": ["03074329"], "principale": "WORLD", "altre": ["SN", "MA", "TN"],
                   "prodotto": "Seppia (Sepia officinalis)", "presentazione": "Intera o pulita", "conservazione": "Congelata"},
        "flussi": {
            "codici": ["03074329"],
            "descrizione": "Seppia (Sepia officinalis), congelata",
            "partner": ["WORLD", "SN", "MA", "TN", "ES", "FR"],
            "principale": "SN",
        },
        "domande": [
            ("Perché una media a quattro settimane?", "Le provenienze della seppia cambiano peso da una settimana all'altra, e il prezzo della singola settimana salta con il mix dei carichi. La media delle ultime quattro, pesata sui volumi, si aggiorna comunque ogni settimana e segue l'andamento vero."),
            D_FRONTIERA, D_RITARDO,
        ],
    },
    {
        "id": "astice",
        "nome": "Astice",
        "sottotitolo": "Vivo, importato in Italia da Stati Uniti e Canada",
        "pubblicato": True,
        "titolo_pagina": "Prezzo dell'astice vivo all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio settimanale dell'astice vivo importato in Italia da Stati Uniti e Canada, con i volumi. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.astice.world.settimanale", "fonte": "eumofa"},
        "eumofa": {"codici": ["03063210"], "principale": "WORLD", "altre": ["US", "CA"],
                   "prodotto": "Astice (Homarus spp.)", "presentazione": "Intero", "conservazione": "Vivo"},
        "flussi": {
            "codici": ["03063210"],
            "descrizione": "Astici (Homarus spp.), vivi",
            "partner": ["WORLD", "US", "CA", "FR"],
            "principale": "US",
        },
        "domande": [D_FRONTIERA, D_RITARDO],
    },
    {
        "id": "pesce_spada",
        "nome": "Pesce spada",
        "sottotitolo": "Filetti e lombi freschi, importati in Italia da Sri Lanka e Cile",
        "pubblicato": True,
        "titolo_pagina": "Prezzo del pesce spada fresco all'importazione: andamento settimanale in Italia",
        "descrizione_pagina": "Valore medio settimanale dei filetti e lombi freschi di pesce spada importati in Italia, con i volumi e le provenienze. Dati doganali ufficiali, aggiornamento settimanale.",
        "prezzo": {"serie": "eumofa.it.import.pesce_spada.world.settimanale", "fonte": "eumofa"},
        "eumofa": {"codici": ["03044500"], "principale": "WORLD", "altre": ["LK", "CL"],
                   "prodotto": "Pesce spada (Xiphias gladius)", "presentazione": "Filetti e lombi", "conservazione": "Fresco"},
        "flussi": {
            "codici": ["03024700", "03044500", "03035700"],
            "descrizione": "Pesce spada, fresco e congelato",
            "partner": ["WORLD", "ES", "LK", "CL"],
            "principale": "ES",
        },
        "domande": [
            ("Perché solo il fresco?", "Il pesce spada congelato arriva in carichi irregolari e di qualità molto diverse: il suo prezzo medio settimanale non è leggibile. I filetti e lombi freschi hanno invece arrivi regolari e un prezzo stabile. Il congelato è compreso nel riquadro mensile sugli arrivi."),
            D_FRONTIERA, D_RITARDO,
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
    "Salmone atlantico, fresco o refrigerato": "Atlantic salmon, fresh or chilled",
    "Questo prezzo è alto per il periodo?": "Is this price high for the time of year?",
    "La banda in apertura confronta la settimana con le stesse settimane dei cinque anni precedenti.": "The band at the top compares the week with the same weeks of the previous five years.",
    "Corrisponde al prezzo che mi chiede il fornitore?": "Is this the price my supplier is asking?",
    "No. È il valore medio all'esportazione dalla Norvegia, su tutte le pezzature e destinazioni. Serve come riferimento di andamento, non come quotazione contrattuale.": "No. It is the average export value from Norway, across all sizes and destinations. It serves as a trend reference, not as a contractual quotation.",
    "Quanto ne arriva in Italia?": "How much of it reaches Italy?",
    "Il riquadro sui flussi mostra le importazioni italiane mensili e il totale mobile a dodici mesi.": "The flows panel shows monthly Italian imports and the rolling twelve-month total.",

    "Perché tra le provenienze non c'è la Norvegia?": "Why is Norway not among the origins?",
    "Perché il salmone norvegese entra nell'Unione da altri paesi, soprattutto nordici, e da lì arriva in Italia come scambio interno. La statistica registra il paese di spedizione, non quello di allevamento.": "Because Norwegian salmon enters the Union through other countries, mainly Nordic ones, and reaches Italy from there as intra-EU trade. Statistics record the country of dispatch, not the country of farming.",

    # domande comuni alle specie da dati doganali
    "È il prezzo che pago al fornitore?": "Is this the price I pay my supplier?",
    "No. È il valore medio dichiarato in dogana da chi importa in Italia, su tutte le pezzature. Serve per confrontare il proprio prezzo d'acquisto con la media e per leggere l'andamento, non come quotazione.": "No. It is the average value declared at customs by importers into Italy, across all sizes. Use it to compare your own purchase price with the average and to read the trend, not as a quotation.",
    "Quanto è aggiornato?": "How up to date is it?",
    "Il dato esce ogni settimana e copre fino a circa due settimane prima: la settimana più recente è sempre incompleta alla fonte e viene pubblicata solo quando è chiusa.": "The data come out every week and run to about two weeks earlier: the most recent week is always incomplete at the source and is published only once it is closed.",
    "Perché il prezzo è quello turco?": "Why the Turkish price?",
    "Perché è l'unico che esiste ogni settimana: la dogana registra le importazioni da fuori Unione, e la Turchia è la prima provenienza extra-UE. Gli arrivi da Grecia e Croazia sono scambi interni all'Unione e la statistica ufficiale li pubblica solo ogni mese: sono nel riquadro sugli arrivi.": "Because it is the only one that exists every week: customs record imports from outside the Union, and Türkiye is the leading non-EU origin. Arrivals from Greece and Croatia are intra-EU trade and official statistics publish them only monthly: they are in the imports panel.",

    "Orata": "Gilt-head sea bream",
    "Fresca, importata in Italia dalla Turchia; Grecia e Croazia nel dato mensile": "Fresh, imported into Italy from Türkiye; Greece and Croatia in the monthly data",
    "Prezzo dell'orata all'importazione: andamento settimanale in Italia": "Sea bream import price: weekly trend in Italy",
    "Valore medio settimanale dell'orata fresca importata in Italia dalla Turchia, con i volumi, e importazioni mensili da Grecia e Croazia. Dati doganali ufficiali, aggiornamento settimanale.": "Weekly average value of fresh sea bream imported into Italy from Türkiye, with volumes, and monthly imports from Greece and Croatia. Official customs data, updated weekly.",
    "Orata (Sparus aurata)": "Gilt-head sea bream (Sparus aurata)",
    "Orata (Sparus aurata), fresca o refrigerata": "Gilt-head sea bream (Sparus aurata), fresh or chilled",

    "Spigola": "European sea bass",
    "Prezzo della spigola all'importazione: andamento settimanale in Italia": "Sea bass import price: weekly trend in Italy",
    "Valore medio settimanale della spigola fresca importata in Italia dalla Turchia, con i volumi, e importazioni mensili da Grecia e Croazia. Dati doganali ufficiali, aggiornamento settimanale.": "Weekly average value of fresh sea bass imported into Italy from Türkiye, with volumes, and monthly imports from Greece and Croatia. Official customs data, updated weekly.",
    "Spigola (Dicentrarchus labrax)": "European sea bass (Dicentrarchus labrax)",
    "Spigola (Dicentrarchus labrax), fresca o refrigerata": "European sea bass (Dicentrarchus labrax), fresh or chilled",

    "Gambero": "Shrimp",
    "Congelato, importato in Italia dall'Ecuador; Argentina e India a confronto": "Frozen, imported into Italy from Ecuador; Argentina and India for comparison",
    "Prezzo del gambero all'importazione: andamento settimanale in Italia": "Shrimp import price: weekly trend in Italy",
    "Valore medio settimanale del gambero congelato importato in Italia dall'Ecuador, con i volumi, e confronto con Argentina e India. Dati doganali ufficiali, aggiornamento settimanale.": "Weekly average value of frozen shrimp imported into Italy from Ecuador, with volumes, and comparison with Argentina and India. Official customs data, updated weekly.",
    "Gamberi e gamberetti": "Shrimps and prawns",
    "Interi o code": "Whole or tails",
    "Gamberi congelati, genere Penaeus e altri": "Frozen shrimps, genus Penaeus and others",
    "Perché solo l'Ecuador ha il prezzo settimanale?": "Why does only Ecuador have a weekly price?",
    "Perché dall'Ecuador arriva un prodotto omogeneo, il vannamei, e il prezzo medio si muove come il mercato. Da Argentina e India arrivano prodotti e pezzature diversi: da una settimana all'altra il prezzo medio salta con il mix dei carichi, quindi lo mostriamo come media delle ultime quattro settimane.": "Because Ecuador ships a homogeneous product, vannamei, and the average price moves with the market. Argentina and India ship different products and sizes: from one week to the next the average price jumps with the mix of shipments, so we show it as the average of the last four weeks.",

    "Polpo": "Octopus",
    "Importato in Italia dal Marocco; Senegal e Mauritania a confronto": "Imported into Italy from Morocco; Senegal and Mauritania for comparison",
    "Prezzo del polpo all'importazione: andamento settimanale in Italia": "Octopus import price: weekly trend in Italy",
    "Valore medio settimanale del polpo importato in Italia dal Marocco, con i volumi, e confronto con Senegal e Mauritania. Dati doganali ufficiali, aggiornamento settimanale.": "Weekly average value of octopus imported into Italy from Morocco, with volumes, and comparison with Senegal and Mauritania. Official customs data, updated weekly.",
    "Polpo (Octopus spp.)": "Octopus (Octopus spp.)",
    "Congelato, in piccola parte fresco": "Frozen, a small share fresh",
    "Polpo, fresco e congelato": "Octopus, fresh and frozen",
    "Perché il Marocco in copertina?": "Why Morocco as the headline?",
    "È la prima provenienza del polpo che entra in Italia e l'unica con arrivi regolari ogni settimana. Senegal e Mauritania hanno carichi più radi: per loro mostriamo la media delle ultime quattro settimane.": "It is the leading origin of octopus entering Italy and the only one with regular arrivals every week. Senegal and Mauritania ship less regularly: for them we show the average of the last four weeks.",

    "Calamaro": "Squid",
    "Loligo vulgaris congelato, importato in Italia, quasi tutto dal Marocco": "Frozen Loligo vulgaris, imported into Italy, almost all from Morocco",
    "Prezzo del calamaro all'importazione: andamento settimanale in Italia": "Squid import price: weekly trend in Italy",
    "Valore medio settimanale del calamaro congelato (Loligo vulgaris) importato in Italia, con i volumi. Dati doganali ufficiali, aggiornamento settimanale.": "Weekly average value of frozen squid (Loligo vulgaris) imported into Italy, with volumes. Official customs data, updated weekly.",
    "Calamaro (Loligo vulgaris)": "Squid (Loligo vulgaris)",
    "Intero o pulito": "Whole or cleaned",
    "Calamari del genere Loligo, congelati": "Squid of the genus Loligo, frozen",
    "E il totano?": "What about flying squid?",
    "Ha codici doganali propri e prezzi molto diversi: qui c'è solo il calamaro Loligo vulgaris, che la dogana distingue. Tenerli separati è quello che rende leggibile il prezzo.": "It has its own customs codes and very different prices: this page covers only Loligo vulgaris squid, which customs identify separately. Keeping them apart is what makes the price readable.",

    "Seppia": "Cuttlefish",
    "Congelata, importata in Italia da Senegal, Marocco e Tunisia; media a quattro settimane": "Frozen, imported into Italy from Senegal, Morocco and Tunisia; four-week average",
    "Prezzo della seppia all'importazione: andamento settimanale in Italia": "Cuttlefish import price: weekly trend in Italy",
    "Valore medio della seppia congelata importata in Italia, media mobile a quattro settimane, con i volumi settimanali e le provenienze. Dati doganali ufficiali, aggiornamento settimanale.": "Average value of frozen cuttlefish imported into Italy, four-week moving average, with weekly volumes and origins. Official customs data, updated weekly.",
    "Seppia (Sepia officinalis)": "Cuttlefish (Sepia officinalis)",
    "Intera o pulita": "Whole or cleaned",
    "Congelata": "Frozen",
    "Seppia (Sepia officinalis), congelata": "Cuttlefish (Sepia officinalis), frozen",
    "Perché una media a quattro settimane?": "Why a four-week average?",
    "Le provenienze della seppia cambiano peso da una settimana all'altra, e il prezzo della singola settimana salta con il mix dei carichi. La media delle ultime quattro, pesata sui volumi, si aggiorna comunque ogni settimana e segue l'andamento vero.": "The weight of each cuttlefish origin changes from week to week, and the single-week price jumps with the mix of shipments. The volume-weighted average of the last four weeks still updates every week and follows the real trend.",

    "Astice": "Lobster",
    "Vivo, importato in Italia da Stati Uniti e Canada": "Live, imported into Italy from the United States and Canada",
    "Prezzo dell'astice vivo all'importazione: andamento settimanale in Italia": "Live lobster import price: weekly trend in Italy",
    "Valore medio settimanale dell'astice vivo importato in Italia da Stati Uniti e Canada, con i volumi. Dati doganali ufficiali, aggiornamento settimanale.": "Weekly average value of live lobster imported into Italy from the United States and Canada, with volumes. Official customs data, updated weekly.",
    "Astice (Homarus spp.)": "Lobster (Homarus spp.)",
    "Vivo": "Live",
    "Astici (Homarus spp.), vivi": "Lobsters (Homarus spp.), live",

    "Pesce spada": "Swordfish",
    "Filetti e lombi freschi, importati in Italia da Sri Lanka e Cile": "Fresh fillets and loins, imported into Italy from Sri Lanka and Chile",
    "Prezzo del pesce spada fresco all'importazione: andamento settimanale in Italia": "Fresh swordfish import price: weekly trend in Italy",
    "Valore medio settimanale dei filetti e lombi freschi di pesce spada importati in Italia, con i volumi e le provenienze. Dati doganali ufficiali, aggiornamento settimanale.": "Weekly average value of fresh swordfish fillets and loins imported into Italy, with volumes and origins. Official customs data, updated weekly.",
    "Pesce spada (Xiphias gladius)": "Swordfish (Xiphias gladius)",
    "Filetti e lombi": "Fillets and loins",
    "Pesce spada, fresco e congelato": "Swordfish, fresh and frozen",
    "Perché solo il fresco?": "Why fresh only?",
    "Il pesce spada congelato arriva in carichi irregolari e di qualità molto diverse: il suo prezzo medio settimanale non è leggibile. I filetti e lombi freschi hanno invece arrivi regolari e un prezzo stabile. Il congelato è compreso nel riquadro mensile sugli arrivi.": "Frozen swordfish arrives in irregular shipments of very different quality: its weekly average price is not readable. Fresh fillets and loins have regular arrivals and a stable price. Frozen is included in the monthly imports panel.",

    # anagrafica comune
    "Intera": "Whole", "Intero": "Whole", "Fresca": "Fresh", "Fresco": "Fresh", "Congelato": "Frozen",
    "Importazioni in Italia da paesi extra-UE": "Imports into Italy from non-EU countries",
    "Importazione (valore dichiarato in dogana)": "Import (value declared at customs)",
    "Valore unitario delle importazioni": "Import unit value",
    "Valore unitario delle importazioni, media mobile a quattro settimane": "Import unit value, four-week moving average",
    "Tutte le pezzature": "All sizes",
    "Non distinta dalla fonte": "Not distinguished by the source",
    "Secondo la nomenclatura combinata": "As per the Combined Nomenclature",
    "Riuso consentito con attribuzione": "Reuse permitted with attribution",
    "Valore diviso quantità, somma dei codici doganali indicati.": "Value divided by quantity, sum of the customs codes listed.",
    "Valore dichiarato diviso peso netto, somma dei codici doganali della specie. Sono pubblicate solo le settimane complete alla fonte.": "Declared value divided by net weight, sum of the customs codes for the species. Only weeks that are complete at the source are published.",
    "Non è una quotazione: è il valore medio dichiarato in dogana, trasporto fino alla frontiera compreso. Copre solo gli arrivi da fuori Unione; la fonte rivede i dati anche a distanza di mesi.": "Not a quotation: it is the average value declared at customs, including transport to the border. It covers only arrivals from outside the Union; the source revises the data even months later.",
    "EUMOFA (Commissione europea), importazioni UE settimanali da dati doganali": "EUMOFA (European Commission), weekly EU imports from customs data",
    "Lo Stato di importazione è spesso il punto di ingresso doganale, non la destinazione finale. Il valore in dogana comprende il trasporto fino alla frontiera.": "The importing Member State is often the customs point of entry, not the final destination. The customs value includes transport to the border.",
}


TRADUZIONI_EN_PRODOTTI.update({
    f"{MERCATO_EUMOFA}: {it}": f"Imports into Italy from non-EU countries: {en}"
    for it, en in PAESI.values()
})


def serie_eumofa(prodotto: dict, partner: str) -> str:
    """Identificativo della serie settimanale EUMOFA di una specie per provenienza."""
    return f"eumofa.it.import.{prodotto['id']}.{partner.lower()}.settimanale"


def con_eumofa() -> list[dict]:
    return [p for p in pubblicati() if p.get("eumofa")]


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
