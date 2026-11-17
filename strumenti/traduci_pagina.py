"""Genera `dati-mercati.en.html` dalla pagina italiana.

La logica della pagina è una sola e vive in `dati-mercati.html`. La
versione inglese non è una seconda pagina da mantenere: è generata a ogni
build sostituendo i testi, con due controlli che impediscono di
pubblicare traduzioni a metà:

1. ogni voce del dizionario deve trovare almeno una corrispondenza (se un
   testo italiano viene riscritto, la traduzione smette di agganciarsi e
   il build si ferma invece di lasciare l'italiano in pagina);
2. la pagina generata non deve contenere parole italiane riconoscibili
   nei testi visibili.

    python strumenti/traduci_pagina.py
"""

from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]

# (italiano, inglese). L'ordine conta: le voci più lunghe prima, così una
# sostituzione corta non rompe una frase lunga che la contiene.
TRADUZIONI = [
    # --- head
    ("<html lang=\"it\">", "<html lang=\"en\">"),
    ("<title>Dati e mercati — Pesceinrete</title>", "<title>Market data — Pesceinrete</title>"),
    ("content=\"Prezzi, volumi e serie storiche dei principali prodotti ittici, con fonte, periodo e metodo dichiarati. Aggiornamento settimanale.\"",
     "content=\"Prices, volumes and historical series for the main seafood products, with source, period and method disclosed. Updated weekly.\""),
    # --- testata
    ("<a href=\"/category/mercati/\">Mercati</a> / Dati e mercati", "<a href=\"/category/mercati/\">Markets</a> / Market data"),
    ("<h1 class=\"pir-titolo-sezione\">Dati e mercati</h1>", "<h1 class=\"pir-titolo-sezione\">Market data</h1>"),
    ("Prezzi e volumi delle materie prime ittiche, con fonte, periodo e metodo\n        dichiarati accanto a ogni numero. Aggiornamento il giovedi mattina.",
     "Prices and volumes of seafood raw materials, with source, period and method\n        stated next to every figure. Updated on Thursday morning."),
    ("aria-label=\"Percorso\"", "aria-label=\"Breadcrumb\""),
    ("aria-label=\"Sezione\"", "aria-label=\"Section\""),
    (">Scheda prodotto</a>", ">Product</a>"),
    (">Arrivi in Italia</a>", ">Imports into Italy</a>"),
    (">La settimana</a>", ">This week</a>"),
    (">Confronto periodi</a>", ">Compare periods</a>"),
    (">Costo a destino</a>", ">Landed cost</a>"),
    (">Fonti e metodo</a>", ">Sources and method</a>"),
    ("aria-label=\"Prodotto\"", "aria-label=\"Product\""),
    # --- apertura
    (">Salmone atlantico</h2>", ">Atlantic salmon</h2>"),
    # --- flussi
    ("<h2 id=\"pir-titolo-flussi\">Arrivi <b>in Italia</b></h2>", "<h2 id=\"pir-titolo-flussi\">Imports <b>into Italy</b></h2>"),
    ("—<span>tonnellate</span>", "—<span>tonnes</span>"),
    # --- bollettino
    ("<h2 id=\"pir-titolo-bollettino\">La settimana <b>in breve</b></h2>", "<h2 id=\"pir-titolo-bollettino\">This week <b>in brief</b></h2>"),
    ("Solo i fatti che il grafico non mostra da solo. Le cause non vengono\n          indovinate: dove servono, le aggiunge la redazione dopo averle verificate.",
     "Only the facts the chart does not show by itself. Causes are not\n          guessed: where needed, the editorial team adds them after checking."),
    # --- andamento
    ("<h2 id=\"pir-titolo-storico\">Andamento <b>storico</b></h2>", "<h2 id=\"pir-titolo-storico\">Price <b>history</b></h2>"),
    ("Il prezzo è convertito in euro con il cambio medio della stessa settimana,\n          non con il cambio di oggi.",
     "The price is converted to euro at the average exchange rate of the same week,\n          not at today's rate."),
    ("aria-label=\"Grandezza\"", "aria-label=\"Measure\""),
    (">Prezzo €/kg</button>", ">Price €/kg</button>"),
    (">Prezzo in valuta</button>", ">Price in currency</button>"),
    (">Volume</button>", ">Volume</button>"),
    ("aria-label=\"Periodo\"", "aria-label=\"Period\""),
    (">3 mesi</button>", ">3 months</button>"),
    (">1 anno</button>", ">1 year</button>"),
    (">5 anni</button>", ">5 years</button>"),
    (">Tutto</button>", ">All</button>"),
    ("<label class=\"pir-campo\">Dal<input type=\"date\" id=\"pir-dal\"></label>", "<label class=\"pir-campo\">From<input type=\"date\" id=\"pir-dal\"></label>"),
    ("<label class=\"pir-campo\">Al<input type=\"date\" id=\"pir-al\"></label>", "<label class=\"pir-campo\">To<input type=\"date\" id=\"pir-al\"></label>"),
    (">Scarica CSV</button>", ">Download CSV</button>"),
    # --- confronto
    ("<h2 id=\"pir-titolo-confronto\">Confronto <b>fra periodi</b></h2>", "<h2 id=\"pir-titolo-confronto\">Compare <b>periods</b></h2>"),
    ("Il prezzo del periodo è la media ponderata sui volumi settimanali. I confronti\n          fra periodi di lunghezza diversa vengono segnalati e i totali non vengono messi a percentuale.",
     "The period price is the volume-weighted average of weekly prices. Comparisons\n          between periods of different length are flagged and totals are not expressed as percentages."),
    ("aria-label=\"Termine di paragone\"", "aria-label=\"Comparison basis\""),
    (">Periodo precedente</button>", ">Previous period</button>"),
    (">Anno precedente</button>", ">Previous year</button>"),
    (">Date scelte</button>", ">Custom dates</button>"),
    ("hidden>Riferimento dal<input", "hidden>Reference from<input"),
    ("hidden>Riferimento al<input", "hidden>Reference to<input"),
    # --- costo
    ("<h2 id=\"pir-titolo-costo\">Dal riferimento <b>al tuo costo</b></h2>", "<h2 id=\"pir-titolo-costo\">From the reference <b>to your cost</b></h2>"),
    ("Il filetto tratteggiato segnala che questa non è una fonte: è una simulazione\n          costruita sui parametri che inserisci. Serve a portare il riferimento di mercato sul prodotto come\n          lo compri e lo lavori tu.",
     "The dashed rule signals that this is not a source: it is a simulation\n          built on the parameters you enter. It brings the market reference down to the product as\n          you buy and process it."),
    ("Riferimento €/kg\n                <input", "Reference €/kg\n                <input"),
    ("Maggiorazione %\n                <input", "Mark-up %\n                <input"),
    ("Trasporto €/kg\n                <input", "Freight €/kg\n                <input"),
    ("Altri costi €/kg\n                <input", "Other costs €/kg\n                <input"),
    ("Glassatura %\n                <input", "Glaze %\n                <input"),
    ("Resa %\n                <input", "Yield %\n                <input"),
    ("<summary>Come vengono usati questi parametri</summary>", "<summary>How these parameters are used</summary>"),
    ("La maggiorazione e il trasporto si sommano al riferimento e danno il costo reso.\n                    La glassatura è acqua: su un congelato glassato al 10% il prodotto netto costa il\n                    costo reso diviso 0,90. La resa è quel che resta dopo la lavorazione, e divide di\n                    nuovo il costo.",
     "Mark-up and freight are added to the reference and give the landed cost.\n                    Glaze is water: on a frozen product with 10% glaze the net product costs the\n                    landed cost divided by 0.90. Yield is what remains after processing, and divides\n                    the cost again."),
    ("Il risultato serve a confrontare offerte diverse sulla stessa base, non a stabilire\n                    un prezzo di acquisto. Nessuno dei parametri viene salvato o inviato.",
     "The result is for comparing different offers on the same basis, not for setting\n                    a purchase price. None of the parameters is stored or sent anywhere."),
    ("—<span>€/kg utile</span>", "—<span>€/kg usable</span>"),
    # --- metodo
    ("<h2 id=\"pir-titolo-metodo\">Fonti <b>e metodo</b></h2>", "<h2 id=\"pir-titolo-metodo\">Sources <b>and method</b></h2>"),
    ("<summary>Il perimetro esatto del prezzo</summary>", "<summary>What exactly this price covers</summary>"),
    ("<summary>Fonte, licenza e aggiornamento</summary>", "<summary>Source, licence and updates</summary>"),
    ("<summary>Come leggiamo la stagionalità</summary>", "<summary>How we read seasonality</summary>"),
    ("La banda raccoglie i valori delle stesse settimane dei cinque anni precedenti, presi in una\n                finestra di due settimane prima e due dopo. Il percentile dice quanti di quei valori stanno\n                sotto il prezzo di questa settimana.",
     "The band collects the values of the same weeks in the previous five years, taken in a\n                window of two weeks before and two after. The percentile says how many of those values sit\n                below this week's price."),
    ("Il confronto con il solo anno precedente non basta: un anno può essere stato anomalo. Con\n                meno di tre anni di storico o meno di dodici osservazioni utili la lettura stagionale non\n                viene pubblicata.",
     "Comparing with last year alone is not enough: a single year may have been anomalous. With\n                fewer than three years of history or fewer than twelve usable observations the seasonal\n                reading is not published."),
    ("<summary>Revisioni e aggiornamenti recenti</summary>", "<summary>Recent revisions and updates</summary>"),
    ("aria-label=\"Livello di dettaglio\"", "aria-label=\"Level of detail\""),
    ("<strong>In breve</strong>\n            <span>Prezzo della settimana, stagionalità, sintesi</span>",
     "<strong>At a glance</strong>\n            <span>Price of the week, seasonality, summary</span>"),
    ("<strong>Analisi completa</strong>\n            <span>Storico, arrivi in Italia, confronti, costo a destino, fonti</span>",
     "<strong>Full analysis</strong>\n            <span>History, imports into Italy, comparisons, landed cost, sources</span>"),
    ("<p class=\"pir-sopratitolo\">Posizione nella stagione</p>", "<p class=\"pir-sopratitolo\">Seasonal position</p>"),
    ("<p class=\"pir-sottotitolo\">La settimana contro le stesse settimane degli ultimi cinque anni</p>",
     "<p class=\"pir-sottotitolo\">This week against the same weeks of the last five years</p>"),
    ("\"<div><dt>Settimana</dt><dd>\"+segno(v.settimana,1)+\"%</dd></div>\"+\n    \"<div><dt>4 settimane</dt><dd>\"+segno(v.quattro_settimane,1)+\"%</dd></div>\"+\n    \"<div><dt>Anno</dt><dd>\"+segno(v.anno,1)+\"%</dd></div>\";",
     "\"<div><dt>Week</dt><dd>\"+segno(v.settimana,1)+\"%</dd></div>\"+\n    \"<div><dt>4 weeks</dt><dd>\"+segno(v.quattro_settimane,1)+\"%</dd></div>\"+\n    \"<div><dt>Year</dt><dd>\"+segno(v.anno,1)+\"%</dd></div>\";"),
    ("aria-label=\"Sezioni dell'analisi completa\"", "aria-label=\"Sections of the full analysis\""),
    ("<a href=\"#storico\">Andamento storico</a>", "<a href=\"#storico\">Price history</a>"),
    ("<a href=\"#confronto\">Confronto fra periodi</a>", "<a href=\"#confronto\">Compare periods</a>"),
    ("<p><strong>Vuoi andare oltre?</strong> L'analisi completa aggiunge lo storico con le date esatte,\n            gli arrivi in Italia per provenienza, il confronto fra periodi, il calcolatore del costo a destino\n            e le fonti.</p>",
     "<p><strong>Want to go further?</strong> The full analysis adds the history with exact dates,\n            imports into Italy by origin, period comparison, the landed-cost calculator\n            and the sources.</p>"),
    (">Apri l'analisi completa</button>", ">Open the full analysis</button>"),
    ("<strong>Ricevi il bollettino ogni giovedì</strong>", "<strong>Get the bulletin every Thursday</strong>"),
    ("<small>Una mail con i prezzi di tutte le specie e quello che merita attenzione. Niente altro, mai.</small>",
     "<small>One email with the prices of all species and what deserves attention. Nothing else, ever.</small>"),
    ("placeholder=\"la tua email di lavoro\"", "placeholder=\"your work email\""),
    ("<button type=\"submit\">Iscrivimi</button>", "<button type=\"submit\">Subscribe</button>"),
    ("<label class=\"pir-campo\">Il riferimento è\n                <select id=\"pir-base-resa\">\n                  <option value=\"origine\">all'origine (FOB/FCA): aggiungo trasporto</option>\n                  <option value=\"destino\">reso a destino (DAP/DDP): trasporto incluso</option>\n                </select></label>",
     "<label class=\"pir-campo\">The reference is\n                <select id=\"pir-base-resa\">\n                  <option value=\"origine\">at origin (FOB/FCA): I add freight</option>\n                  <option value=\"destino\">delivered (DAP/DDP): freight included</option>\n                </select></label>"),
    ("<label class=\"pir-campo\">Lavorazione\n                <select id=\"pir-lavorazione\"></select></label>", "<label class=\"pir-campo\">Processing\n                <select id=\"pir-lavorazione\"></select></label>"),
    ("+'<option value=\"\">altro (imposto la resa a mano)</option>'", "+'<option value=\"\">other (I set the yield by hand)</option>'"),
    (": '<option value=\"\">resa a mano</option>';", ": '<option value=\"\">yield by hand</option>';"),
    ("var verdetto=sn.percentile>=80?\"sopra la norma\":(sn.percentile<=20?\"sotto la norma\":\"nella norma\");",
     "var verdetto=sn.percentile>=80?\"above normal\":(sn.percentile<=20?\"below normal\":\"normal\");"),
    ("netto.innerHTML=\"Al netto del livello generale dei prezzi: <b>\"+verdetto+\"</b> (percentile \"+num(sn.percentile,0)+\n        \" sul rapporto con la media mobile a 52 settimane).\";",
     "netto.innerHTML=\"Net of the general price level: <b>\"+verdetto+\"</b> (percentile \"+num(sn.percentile,0)+\n        \" on the ratio to the 52-week moving average).\";"),
    ("riga.textContent=\"Dalla tua ultima visita (settimana \"+prima.periodo.slice(6)+\", \"+num(prima.prezzo,2)+\" €/kg) il prezzo è \"+\n      (Math.abs(delta)<0.5?\"praticamente fermo\":((delta>0?\"salito\":\"sceso\")+\" del \"+num(Math.abs(delta),1)+\"%\"))+\".\";",
     "riga.textContent=\"Since your last visit (week \"+prima.periodo.slice(6)+\", \"+num(prima.prezzo,2)+\" €/kg) the price is \"+\n      (Math.abs(delta)<0.5?\"virtually unchanged\":((delta>0?\"up\":\"down\")+\" \"+num(Math.abs(delta),1)+\"%\"))+\".\";"),
    ("<label class=\"pir-scelta-mobile\" id=\"pir-scelta-mobile\" hidden>Specie", "<label class=\"pir-scelta-mobile\" id=\"pir-scelta-mobile\" hidden>Species"),
    ("<button type=\"button\" id=\"pir-scarica-grafico\">Scarica il grafico</button>", "<button type=\"button\" id=\"pir-scarica-grafico\">Download the chart</button>"),
    ("<button type=\"button\" id=\"pir-copia-link\">Copia il link a questa vista</button>", "<button type=\"button\" id=\"pir-copia-link\">Copy link to this view</button>"),
    ("<h2 id=\"pir-titolo-panoramica\">Tutte le specie, <b>questa settimana</b></h2>", "<h2 id=\"pir-titolo-panoramica\">All species, <b>this week</b></h2>"),
    ("Prezzo di riferimento in euro al chilo, variazione sulla settimana e sull'anno, posizione rispetto alla stagione.",
     "Reference price in euro per kilo, change on the week and on the year, position against the season."),
    ("var etichetta=(!att||p===null)?\"storico corto\":(p>=80?\"sopra la norma\":(p<=20?\"sotto la norma\":\"nella norma\"));",
     "var etichetta=(!att||p===null)?\"short history\":(p>=80?\"above normal\":(p<=20?\"below normal\":\"normal\"));"),
    ("\"<thead><tr><th>Specie</th><th>€/kg</th><th>Settimana</th><th>Anno</th><th>Stagione</th></tr></thead><tbody>\"+righe+\"</tbody>\";",
     "\"<thead><tr><th>Species</th><th>€/kg</th><th>Week</th><th>Year</th><th>Season</th></tr></thead><tbody>\"+righe+\"</tbody>\";"),
    ("esito(\"Grafico scaricato.\");", "esito(\"Chart downloaded.\");"),
    ("img.onerror=function(){ esito(\"Non sono riuscito a generare l'immagine.\"); };", "img.onerror=function(){ esito(\"Could not generate the image.\"); };"),
    ("function fatto(){ esito(\"Link copiato.\"); }", "function fatto(){ esito(\"Link copied.\"); }"),
    ("<strong id=\"pir-igb-titolo\">Cerchi fornitori di salmone?</strong>", "<strong id=\"pir-igb-titolo\">Looking for salmon suppliers?</strong>"),
    ("<small>Su Ittico Guida Buyer trovi produttori e distributori selezionati, con profili completi e contatti diretti.</small>",
     "<small>On Ittico Guida Buyer you find selected producers and distributors, with full profiles and direct contacts.</small>"),
    ("<a href=\"https://igb.pesceinrete.com/prodotti/\" id=\"pir-igb-link\">Vai a Ittico Guida Buyer</a>",
     "<a href=\"https://igb.pesceinrete.com/en/\" id=\"pir-igb-link\">Go to Ittico Guida Buyer</a>"),
    ("\"Settimana \"+P.ultimo_periodo.slice(6)+\" · \"+P.ultimo_periodo_esteso;", "\"Week \"+P.ultimo_periodo.slice(6)+\" · \"+P.ultimo_periodo_esteso;"),
    ("if(titoloIgb) titoloIgb.textContent=\"Cerchi fornitori di \"+P.nome.toLowerCase()+\"?\";", "if(titoloIgb) titoloIgb.textContent=\"Looking for \"+P.nome.toLowerCase()+\" suppliers?\";"),
    ("(stretto?\"\":\"intervallo \")+primoAnno+\"-\"+String(ultimoAnno).slice(2)));", "(stretto?\"\":\"range \")+primoAnno+\"-\"+String(ultimoAnno).slice(2)));"),
    ("\"Euro al chilo per settimana. La fascia chiara è l'intervallo fra minimo e massimo delle stesse \"+\n    \"settimane degli anni \"+(anni.length?anni[0]+\"-\"+anni[anni.length-1]:\"precedenti\")+\n    \"; la linea scura è il \"+anno.anno+\", quella grigia il \"+(anno.anno-1)+\".\";",
     "\"Euro per kilo by week. The light band is the range between minimum and maximum of the same \"+\n    \"weeks in \"+(anni.length?anni[0]+\"-\"+anni[anni.length-1]:\"previous years\")+\n    \"; the dark line is \"+anno.anno+\", the grey one \"+(anno.anno-1)+\".\";"),
    ("\"A cura della redazione · settimana \"+P.ultimo_periodo.slice(6)+\", \"+P.ultimo_periodo_esteso+\n    \" · aggiornato il \"+",
     "\"By the editorial team · week \"+P.ultimo_periodo.slice(6)+\", \"+P.ultimo_periodo_esteso+\n    \" · updated \"+"),
    # --- JavaScript: stringhe visibili
    ("var MESI = [\"gen\",\"feb\",\"mar\",\"apr\",\"mag\",\"giu\",\"lug\",\"ago\",\"set\",\"ott\",\"nov\",\"dic\"];",
     "var MESI = [\"Jan\",\"Feb\",\"Mar\",\"Apr\",\"May\",\"Jun\",\"Jul\",\"Aug\",\"Sep\",\"Oct\",\"Nov\",\"Dec\"];"),
    ("return \"n.d.\";", "return \"n/a\";"),
    ("parti[0]=parti[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,\".\");\n  return (negativo?\"-\":\"\")+parti[0]+(parti[1]?\",\"+parti[1]:\"\");",
     "parti[0]=parti[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,\",\");\n  return (negativo?\"-\":\"\")+parti[0]+(parti[1]?\".\"+parti[1]:\"\");"),
    ("if(misura===\"tonnellate\") return \"tonnellate\";", "if(misura===\"tonnellate\") return \"tonnes\";"),
    ("passi.push([\"Riferimento di mercato\", base]);", "passi.push([\"Market reference\", base]);"),
    ("passi.push([\"Maggiorazione \"+maggiorazione+\"%\", q]);", "passi.push([\"Mark-up \"+maggiorazione+\"%\", q]);"),
    ("passi.push([\"Trasporto\", trasporto]);", "passi.push([\"Freight\", trasporto]);"),
    ("passi.push([\"Altri costi\", altri]);", "passi.push([\"Other costs\", altri]);"),
    ("passi.push([\"Costo reso a destino\", prezzo]);", "passi.push([\"Landed cost\", prezzo]);"),
    ("passi.push([\"Netto glassatura \"+glassatura+\"%\", prezzo]);", "passi.push([\"Net of \"+glassatura+\"% glaze\", prezzo]);"),
    ("passi.push([\"Per kg utilizzabile, resa \"+resa+\"%\", utile]);", "passi.push([\"Per usable kg, yield \"+resa+\"%\", utile]);"),
    ("contenitore.textContent=\"Storico insufficiente.\";", "contenitore.textContent=\"Not enough history.\";"),
    ("contenitore.textContent=\"Nessun dato nel periodo scelto.\";", "contenitore.textContent=\"No data in the selected period.\";"),
    ("punti.length+\" settimane, da \"+etichettaBreve(punti[0].periodo)+\" a \"+", "punti.length+\" weeks, from \"+etichettaBreve(punti[0].periodo)+\" to \"+"),
    ("? \"Volume complessivo \"+num(agg.volume,0)+\" tonnellate.\"", "? \"Total volume \"+num(agg.volume,0)+\" tonnes.\""),
    (": \"Media ponderata sui volumi \"+num(agg.prezzo,2)+\" €/kg.\");", ": \"Volume-weighted average \"+num(agg.prezzo,2)+\" €/kg.\");"),
    ("f.indicatore+\". \"+f.note+\" Ultimo mese disponibile: \"+f.ultimo_mese_esteso+\n    \", con il consueto ritardo di questa fonte rispetto ai prezzi settimanali.\";",
     "f.indicatore+\". \"+f.note+\" Latest month available: \"+f.ultimo_mese_esteso+\n    \", with this source's usual lag behind weekly prices.\";"),
    ("num(d.tonnellate,0)+\"<span>tonnellate</span>\";", "num(d.tonnellate,0)+\"<span>tonnes</span>\";"),
    ("\"Dodici mesi fino a \"+f.ultimo_mese_esteso+\n    (d.delta_tonnellate===null?\"\":\", \"+segno(d.delta_tonnellate,1)+\"% sui dodici precedenti\")+\n    (d.mesi_usati<12?\" · attenzione: solo \"+d.mesi_usati+\" mesi disponibili\":\"\");",
     "\"Twelve months to \"+f.ultimo_mese_esteso+\n    (d.delta_tonnellate===null?\"\":\", \"+segno(d.delta_tonnellate,1)+\"% on the previous twelve\")+\n    (d.mesi_usati<12?\" · note: only \"+d.mesi_usati+\" months available\":\"\");"),
    ("\"Valore unitario medio in dogana\"+\n    (d.delta_valore_unitario===null?\"\":\", \"+segno(d.delta_valore_unitario,1)+\"% sui dodici precedenti\")+\n    \". Non è un prezzo di acquisto.\";",
     "\"Average customs unit value\"+\n    (d.delta_valore_unitario===null?\"\":\", \"+segno(d.delta_valore_unitario,1)+\"% on the previous twelve\")+\n    \". Not a purchase price.\";"),
    ("\"Importazioni italiane mensili in tonnellate, ultimi \"+serie.length+\" mesi. \"+f.fonte+\".\";",
     "\"Monthly Italian imports in tonnes, last \"+serie.length+\" months. \"+f.fonte+\".\";"),
    ("contenitore.innerHTML='<p class=\"pir-quiete\">Nessun movimento fuori dall\\'ordinario: '+\n      \"il prezzo resta dentro l'intervallo abituale del periodo e i volumi non presentano \"+\n      \"scarti. Anche questa è un'informazione per chi deve decidere se comprare adesso \"+\n      \"o aspettare.</p>\";",
     "contenitore.innerHTML='<p class=\"pir-quiete\">Nothing out of the ordinary: '+\n      \"the price remains within the usual range for the period and volumes show no \"+\n      \"anomalies. That too is information for anyone deciding whether to buy now \"+\n      \"or wait.</p>\";"),
    ("    bottoneOrigine.textContent=\"Prezzo \"+P.serie.unita_origine;", "    bottoneOrigine.textContent=\"Price \"+P.serie.unita_origine;"),
    ("(P.cambio?\" al cambio \"+num(P.cambio,3):\"\")+\n    (P.con_volumi&&P.volume_tonnellate?\" · \"+num(P.volume_tonnellate,0)+\" tonnellate\":\"\");",
     "(P.cambio?\" at \"+num(P.cambio,3)+\" per euro\":\"\")+\n    (P.con_volumi&&P.volume_tonnellate?\" · \"+num(P.volume_tonnellate,0)+\" tonnes\":\"\");"),
    ("\"<span class='pir-etichetta-piccola'>Provenienze, ultimi dodici mesi</span>\"+",
     "\"<span class='pir-etichetta-piccola'>Origins, last twelve months</span>\"+"),
    ("errore(\"Il dettaglio del prodotto non è stato caricato (\"+e.message+\").\");",
     "errore(\"The product detail could not be loaded (\"+e.message+\").\");"),
    ("\"Settimana \"+P.ultimo_periodo.slice(6)+\", \"+P.ultimo_periodo_esteso;", "\"Week \"+P.ultimo_periodo.slice(6)+\", \"+P.ultimo_periodo_esteso;"),
    ("!P.stagionale.attendibile||p===null ? \"Storico corto\" :\n    (alto?\"Sopra la norma\":(basso?\"Sotto la norma\":\"Nella norma\")));",
     "!P.stagionale.attendibile||p===null ? \"Short history\" :\n    (alto?\"Above normal\":(basso?\"Below normal\":\"Normal\")));"),
    ("[\"Prezzo medio ponderato\",\"€/kg\",", "[\"Weighted average price\",\"€/kg\","),
    ("[\"Volume complessivo\",\"tonnellate\",", "[\"Total volume\",\"tonnes\","),
    ("[\"Valore ricostruito\",\"euro\",", "[\"Reconstructed value\",\"euro\","),
    ("'<table class=\"pir-tabella\"><caption>Periodo selezionato '+\n    etichettaBreve(selezione.dal)+\" – \"+etichettaBreve(selezione.al)+\" (\"+corrente.settimane+\n    \" settimane complete) contro \"+etichettaBreve(rif.dal)+\" – \"+etichettaBreve(rif.al)+\n    \" (\"+base.settimane+\")</caption><thead><tr><th>Grandezza</th><th>Selezionato</th>\"+\n    \"<th>Riferimento</th><th>Differenza</th><th>Variazione</th></tr></thead><tbody>\";",
     "'<table class=\"pir-tabella\"><caption>Selected period '+\n    etichettaBreve(selezione.dal)+\" – \"+etichettaBreve(selezione.al)+\" (\"+corrente.settimane+\n    \" complete weeks) versus \"+etichettaBreve(rif.dal)+\" – \"+etichettaBreve(rif.al)+\n    \" (\"+base.settimane+\")</caption><thead><tr><th>Measure</th><th>Selected</th>\"+\n    \"<th>Reference</th><th>Difference</th><th>Change</th></tr></thead><tbody>\";"),
    ("if(r[0]!==\"Prezzo medio ponderato\" && !omogeneo){ differenza=null; }", "if(r[0]!==\"Weighted average price\" && !omogeneo){ differenza=null; }"),
    ("(differenza===null?\"n.d.\":segno(differenza,r[5]))+\"</td><td>\"+\n      (r[4]===null?\"n.d.\":segno(r[4],1)+\"%\")+\"</td></tr>\";",
     "(differenza===null?\"n/a\":segno(differenza,r[5]))+\"</td><td>\"+\n      (r[4]===null?\"n/a\":segno(r[4],1)+\"%\")+\"</td></tr>\";"),
    ("html+='<p class=\"pir-nota\">I due periodi contengono un numero diverso di settimane complete ('+\n      corrente.settimane+\" contro \"+base.settimane+\"). Il prezzo medio resta confrontabile perché \"+\n      \"ponderato, i totali no: la loro variazione percentuale non viene calcolata.</p>\";",
     "html+='<p class=\"pir-nota\">The two periods contain a different number of complete weeks ('+\n      corrente.settimane+\" versus \"+base.settimane+\"). The average price remains comparable because \"+\n      \"it is weighted, the totals do not: their percentage change is not calculated.</p>\";"),
    ("html+='<p class=\"pir-nota\">Volumi assenti in alcune settimane: il prezzo del periodo è una media '+\n      \"semplice, non ponderata.</p>\";",
     "html+='<p class=\"pir-nota\">Volumes missing in some weeks: the period price is a simple '+\n      \"average, not weighted.</p>\";"),
    ("html+='<p class=\"pir-didascalia\">Il valore ricostruito è la somma di prezzo per volume. Non è un dato '+\n    \"pubblicato dalla fonte né una conferma indipendente dell'andamento: è la stessa informazione dei \"+\n    \"due numeri sopra, moltiplicata.</p>\";",
     "html+='<p class=\"pir-didascalia\">The reconstructed value is the sum of price times volume. It is not a figure '+\n    \"published by the source nor an independent confirmation of the trend: it is the same information as the \"+\n    \"two figures above, multiplied.</p>\";"),
    ("num(esito.utile,2)+\"<span>€/kg utile</span>\";", "num(esito.utile,2)+\"<span>€/kg usable</span>\";"),
    ("\"<p>Prodotto: \"+s.conservazione.toLowerCase()+\", \"+s.pezzatura.toLowerCase()+\n    \". Unità della fonte: \"+s.unita_origine+\"; la conversione in euro è nostra, \"+\n    \"con il cambio di riferimento BCE medio della stessa settimana, indicativo e non \"+\n    \"applicabile alle transazioni.</p>\";",
     "\"<p>Product: \"+s.conservazione.toLowerCase()+\", \"+s.pezzatura.toLowerCase()+\n    \". Source unit: \"+s.unita_origine+\"; the euro conversion is ours, \"+\n    \"at the average ECB reference rate of the same week, indicative and not \"+\n    \"applicable to transactions.</p>\";"),
    ("\"<dt>Fonte</dt><dd><a href='\"+s.fonte_url+\"' rel='noopener'>\"+s.fonte+\"</a></dd>\"+\n    \"<dt>Licenza</dt><dd><a href='\"+s.licenza_url+\"' rel='noopener'>\"+s.licenza+\"</a></dd>\"+\n    \"<dt>Elaborazione</dt><dd>\"+s.elaborazione+\"</dd>\"+\n    \"<dt>Frequenza</dt><dd>\"+s.frequenza+\", pubblicazione della fonte il mercoledi mattina</dd>\"+\n    \"<dt>Ultimo periodo</dt><dd>\"+P.ultimo_periodo+\" (\"+P.ultimo_periodo_esteso+\")</dd>\"+\n    \"<dt>Pagina aggiornata</dt><dd>\"+D.generato_il.slice(0,16).replace(\"T\",\" \")+\" UTC</dd>\";",
     "\"<dt>Source</dt><dd><a href='\"+s.fonte_url+\"' rel='noopener'>\"+s.fonte+\"</a></dd>\"+\n    \"<dt>Licence</dt><dd><a href='\"+s.licenza_url+\"' rel='noopener'>\"+s.licenza+\"</a></dd>\"+\n    \"<dt>Processing</dt><dd>\"+s.elaborazione+\"</dd>\"+\n    \"<dt>Frequency</dt><dd>\"+s.frequenza+\", published by the source on Wednesday morning</dd>\"+\n    \"<dt>Latest period</dt><dd>\"+P.ultimo_periodo+\" (\"+P.ultimo_periodo_esteso+\")</dd>\"+\n    \"<dt>Page updated</dt><dd>\"+D.generato_il.slice(0,16).replace(\"T\",\" \")+\" UTC</dd>\";"),
    ("? \"<p>Le statistiche del commercio estero vengono riviste. Queste sono le correzioni registrate \"+\n      \"sulle settimane già pubblicate.</p>\"+\n      \"<table class='pir-tabella'><thead><tr><th>Settimana</th><th>Prima</th><th>Dopo</th>\"+\n      \"<th>Rilevata</th></tr></thead><tbody>\"+",
     "? \"<p>Foreign trade statistics get revised. These are the corrections recorded \"+\n      \"on weeks already published.</p>\"+\n      \"<table class='pir-tabella'><thead><tr><th>Week</th><th>Before</th><th>After</th>\"+\n      \"<th>Detected</th></tr></thead><tbody>\"+"),
    (": \"<p>Nessuna revisione registrata sulle settimane già pubblicate.</p>\";", ": \"<p>No revisions recorded on weeks already published.</p>\";"),
    ("return e.quando+\" · \"+e.fonte+\" · \"+e.esito+\" (\"+e.nuove+\" nuove, \"+e.riviste+\" riviste)\";",
     "return e.quando+\" · \"+e.fonte+\" · \"+e.esito+\" (\"+e.nuove+\" new, \"+e.riviste+\" revised)\";"),
    ("\"Dati: \"+s.fonte+\", \"+s.licenza+\", con elaborazioni di Pesceinrete. \"+\n    \"Cambi: Banca centrale europea, valori di riferimento. \"+\n    \"Se un controllo di qualità non passa resta pubblicata l'ultima versione valida.<br><br>\"+\n    \"<span style='color:var(--tenue)'>Ultimi aggiornamenti<br>\"+diario+\"</span>\";",
     "\"Data: \"+s.fonte+\", \"+s.licenza+\", with processing by Pesceinrete. \"+\n    \"Exchange rates: European Central Bank, reference rates. \"+\n    \"If a quality check fails, the last valid version stays online.<br><br>\"+\n    \"<span style='color:var(--tenue)'>Latest updates<br>\"+diario+\"</span>\";"),
    ("{\"@type\":\"PropertyValue\",\"name\":\"Prezzo medio all'esportazione\",\"unitText\":\"EUR/kg\",", "{\"@type\":\"PropertyValue\",\"name\":\"Average export price\",\"unitText\":\"EUR/kg\","),
    ("{\"@type\":\"PropertyValue\",\"name\":\"Volume esportato\",\"unitText\":\"tonnellate\",", "{\"@type\":\"PropertyValue\",\"name\":\"Export volume\",\"unitText\":\"tonnes\","),
    ("fascia.innerHTML='<div class=\"pir-fascia\"><strong>Dati dimostrativi.</strong> '+\n    \"Questa pagina mostra una serie inventata, utile solo a provare il funzionamento. \"+\n    \"Non usarla per decisioni commerciali: diventerà reale al primo collegamento con la fonte.</div>\";",
     "fascia.innerHTML='<div class=\"pir-fascia\"><strong>Demo data.</strong> '+\n    \"This page shows an invented series, useful only to test how it works. \"+\n    \"Do not use it for commercial decisions: it becomes real at the first connection to the source.</div>\";"),
    ("\"# Fonte: \"+s.fonte+\" (\"+s.fonte_url+\")\",\n    \"# Licenza: \"+s.licenza+\" (\"+s.licenza_url+\")\",\n    \"# Elaborazione Pesceinrete: conversione in euro al cambio BCE medio della stessa settimana\",\n    \"# Perimetro: \"+s.conservazione+\", \"+s.pezzatura+\", \"+s.fase,\n    \"# Periodo estratto: \"+selezione.dal+\" - \"+selezione.al,\n    \"# Stato dati: \"+D.stato+\" — estratto il \"+new Date().toISOString().slice(0,10),\n    \"settimana;inizio;fine;prezzo_eur_kg;prezzo_valuta_origine;cambio;tonnellate\"",
     "\"# Source: \"+s.fonte+\" (\"+s.fonte_url+\")\",\n    \"# Licence: \"+s.licenza+\" (\"+s.licenza_url+\")\",\n    \"# Processing by Pesceinrete: euro conversion at the average ECB rate of the same week\",\n    \"# Scope: \"+s.conservazione+\", \"+s.pezzatura+\", \"+s.fase,\n    \"# Period extracted: \"+selezione.dal+\" - \"+selezione.al,\n    \"# Data status: \"+D.stato+\" — extracted on \"+new Date().toISOString().slice(0,10),\n    \"week;start;end;price_eur_kg;price_source_currency;fx_rate;tonnes\""),
    ("o.eur===null?\"\":String(o.eur).replace(\".\",\",\"),\n      o.origine===null?\"\":String(o.origine).replace(\".\",\",\"),\n      o.cambio===null?\"\":String(o.cambio).replace(\".\",\",\"),",
     "o.eur===null?\"\":String(o.eur),\n      o.origine===null?\"\":String(o.origine),\n      o.cambio===null?\"\":String(o.cambio),"),
    ("fetch(window.PESCEINRETE_URL_DATI||\"./data/mercati.json\",{cache:\"no-cache\"})", "fetch(window.PESCEINRETE_URL_DATI||\"./data/mercati.en.json\",{cache:\"no-cache\"})"),
    ("'<div class=\"pir-fascia\"><strong>Dati non disponibili.</strong> '+messaggio+\n    \" Riprova fra qualche minuto oppure segnala il problema alla redazione.</div>\";",
     "'<div class=\"pir-fascia\"><strong>Data unavailable.</strong> '+messaggio+\n    \" Try again in a few minutes or report the problem to the editorial team.</div>\";"),
    ("errore(\"Il file dei dati non è stato caricato (\"+e.message+\").\");", "errore(\"The data file could not be loaded (\"+e.message+\").\");"),
]

# Parole che non devono comparire nei testi visibili della pagina inglese.
SPIE_ITALIANE = re.compile(
    r"\b(settimana|settimane|prezzo|periodo|precedente|volume complessivo|tonnellate|"
    r"della|delle|degli|dalla|nella|sulla|anno in corso|mediana|riferimento|confronto|"
    r"scarica|essenziale|completa|fonte|metodo|è|perché|più|già|può)\b",
    re.IGNORECASE,
)


def traduci(html: str) -> str:
    for italiano, inglese in TRADUZIONI:
        if italiano not in html:
            raise SystemExit(
                "Traduzione non agganciata, il testo italiano è cambiato:\n  " + italiano[:110]
            )
        html = html.replace(italiano, inglese)
    return html


def residui(html: str) -> list[str]:
    """Parole italiane nei testi visibili (fuori da script e style)."""
    corpo = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    testi = " ".join(re.findall(r">([^<>]+)<", corpo))
    return sorted(set(m.group(0).lower() for m in SPIE_ITALIANE.finditer(testi)))


def esegui(origine: Path, destinazione: Path) -> int:
    html = traduci(origine.read_text(encoding="utf-8"))
    trovati = residui(html)
    if trovati:
        raise SystemExit("Parole italiane rimaste nella pagina inglese: " + ", ".join(trovati))
    destinazione.write_text(html, encoding="utf-8")
    print(f"Scritto {destinazione} ({len(TRADUZIONI)} sostituzioni, nessun residuo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(esegui(RADICE / "web/dati-mercati.html", RADICE / "web/dati-mercati.en.html"))
