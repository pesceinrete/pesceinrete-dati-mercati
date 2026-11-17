# Modello dei dati e metodo di calcolo

## Prodotto e serie sono cose diverse

La pagina "Salmone" è un contenitore. Dentro ci sono più serie, ognuna
con la propria identità: prezzo medio all'esportazione dalla Norvegia,
importazioni UE, prima vendita. Non vanno mai fuse in un unico grafico
"prezzo del salmone".

Ogni serie porta con sé sette attributi che decidono se è confrontabile
con un'altra:

- prodotto: specie, presentazione, lavorazione, pezzatura quando la fonte
  la distingue;
- mercato: paese, eventuale piazza, origine e destinazione del flusso;
- fase: prima vendita, esportazione, importazione, ingrosso, dettaglio;
- indicatore: quotazione, prezzo medio, volume, valore, valore unitario;
- misura: unità, valuta, frequenza, periodo di riferimento;
- provenienza: fonte, collegamento al dato, licenza, elaborazioni nostre;
- copertura: da quando a quando, con le rotture di serie note.

Il confronto fra due serie si propone solo quando prodotto, fase e unità
coincidono. Dove le specifiche differiscono, la differenza deve essere
scritta, non lasciata all'occhio del lettore.

## Tabelle

`serie` contiene l'anagrafica sopra. `osservazioni` contiene i valori, con
chiave serie più periodo, più data di prima pubblicazione e data
dell'ultimo aggiornamento. `revisioni` conserva ogni cambiamento di un
valore già pubblicato. `esecuzioni` è il diario degli aggiornamenti.

Il periodo settimanale è sempre una stringa `AAAA-Wnn`. È ordinabile
come testo e non si rompe sugli anni a 53 settimane, che sono la prima
causa di errori silenziosi nei confronti annuali.

## Perché conserviamo le revisioni

Le statistiche del commercio estero vengono corrette. Se sovrascriviamo il
valore vecchio perdiamo la possibilità di rispondere alla domanda che un
professionista prima o poi fa: "la settimana scorsa avevate scritto un
altro numero".

Con lo storico delle revisioni l'archivio è interrogabile a una data
passata: `osservazioni(serie, al_momento="2026-03-01T00:00:00")` restituisce
i dati come erano pubblicati quel giorno. È anche la base di una futura
pagina "che cosa è cambiato dall'ultima settimana".

Le differenze sotto lo 0,05% sono trattate come arrotondamenti della fonte:
il valore viene aggiornato ma non conta come revisione.

## I calcoli

**Prezzo di un periodo.** Sempre media ponderata sui volumi settimanali.
La media semplice di quattro prezzi settimanali non ha significato
economico: se in una settimana si sono mossi 25.000 tonnellate e in
un'altra 6.000, contarle uguali è un errore di sostanza. Se mancano i
volumi di anche una sola settimana, la pagina lo dichiara e mostra una
media semplice.

**Confronti fra periodi.** Si verifica che i due periodi abbiano lo stesso
numero di settimane complete. Se non ce l'hanno, il prezzo medio resta
confrontabile perché ponderato, ma le variazioni sui totali non vengono
calcolate: confrontare il volume di cinque settimane con quello di quattro
produce un meno venti per cento che non esiste.

**Posizione stagionale.** È la misura che risponde alla domanda vera di
chi compra: questo livello è insolito per essere questa settimana? Si
prendono le stesse settimane ISO dei cinque anni precedenti, in una
finestra di due settimane prima e due dopo, escluso l'anno in corso; si
calcola quanti di quei valori stanno sotto il valore corrente.

Sotto tre anni di storico o dodici osservazioni utili la lettura non viene
pubblicata: meglio una casella vuota che una statistica che finge.

**Confronto anno su anno.** Se l'anno di arrivo non ha la settimana 53 si
usa la 52. La convenzione è unica in tutto il sistema.

**Conversione in euro.** Si applica a ogni settimana il cambio medio della
stessa settimana, calcolato sui giorni di quotazione effettivi. Applicare
il cambio di oggi a tutto lo storico riscriverebbe la storia del mercato:
nel triennio in cui la corona si è indebolita, il salmone in corone e il
salmone in euro hanno avuto andamenti diversi, e il lettore italiano
ragiona nel secondo.

I cambi BCE sono di riferimento, a scopo informativo: non sono i cambi a
cui si regola una fattura. La pagina lo dice.

**Valore.** Prezzo per volume. Non è un dato indipendente e non conferma
niente: è la stessa informazione dei due numeri, moltiplicata. Resta nella
tabella di sintesi con l'etichetta "valore ricostruito" e una nota che lo
spiega. Non è una vista del grafico principale.

**Costo a destino.** Simulazione, non dato. Maggiorazione e trasporto si
sommano al riferimento; la glassatura divide per uno meno la percentuale,
perché è acqua; la resa divide ancora, perché è quel che resta dopo la
lavorazione. Il riquadro ha un filetto tratteggiato proprio per non essere
scambiato per una fonte.

## Controlli prima della pubblicazione

L'ingestion si ferma, e la pagina resta all'ultima versione valida, se:

- le etichette della fonte non sono più riconoscibili (protegge dal caso
  peggiore, cioè caricare la serie sbagliata credendo sia quella giusta);
- compaiono periodi duplicati o non ordinati;
- un prezzo è nullo o negativo.

Viene invece segnalato senza bloccare, perché può essere reale:

- un salto superiore al 35% fra due settimane consecutive;
- una settimana di cambio con meno di tre quotazioni giornaliere;
- una settimana mancante nel periodo richiesto.

I test in `tests/` coprono tutti questi casi, compresi gli anni a 53
settimane, le revisioni e la lettura point-in-time. Girano prima di ogni
aggiornamento automatico: se un calcolo si rompe, i dati non vengono
neppure scaricati.
