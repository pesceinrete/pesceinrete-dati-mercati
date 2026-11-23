# Fonti, licenze e vincoli

## Il punto da cui dipende tutto: quale prezzo stiamo pubblicando

Nel salmone circolano almeno quattro numeri diversi che un lettore
distratto chiama tutti "prezzo del salmone". Confonderli è l'errore che
toglie credibilità a un servizio di dati.

| Numero | Che cos'è | Che cosa non è |
|---|---|---|
| Prezzo medio all'esportazione SSB | Valore doganale diviso tonnellate, FOB frontiera norvegese, tutte le pezzature e destinazioni | Non è una quotazione: cambia anche solo perché cambia il mix di pezzature esportate |
| Indice spot su panel di esportatori | Media ponderata di transazioni fisiche dichiarate da un panel, per classe di pezzatura | Non è pubblico né ripubblicabile liberamente |
| Valore unitario delle importazioni | Valore dichiarato in dogana diviso quantità importata | Non è il prezzo di acquisto di nessuno |
| Quotazione di mercato all'ingrosso | Prezzo rilevato su una piazza specifica, in una fase specifica | Non è confrontabile con un prezzo all'esportazione |

Ogni grafico della sezione deve dire quale dei quattro sta mostrando.

## Il benchmark contrattuale: attenzione, è cambiato

Fino al 2024 il riferimento usato nei contratti fisici europei e come
sottostante dei derivati era il Nasdaq Salmon Index (NQSALMON), media
ponderata delle vendite settimanali di salmone atlantico Superior fresco
eviscerato, riportate da un panel di esportatori norvegesi.

**Nasdaq ha cessato il calcolo e la diffusione dell'indice dopo il 6 agosto
2024**, dopo che numerosi conferitori avevano disdetto l'accordo di
contribuzione dati. Il ruolo è passato a **SISALMONI** (Sitagri Salmon
Spot Index, amministratore FinanceAgri, registrato BMR sotto vigilanza
AMF), pubblicato ogni martedi e distribuito da Fish Pool: undici
benchmark, nove classi di pezzatura da 1 a 9+ kg più la media ponderata
generale e l'indice 3-6 kg, che regola il future in euro quotato su
Euronext.

Conseguenze operative:

1. mai citare NQSALMON come indice corrente: chi lavora nel settore se ne
   accorge subito;
2. SISALMONI è a pagamento e non può essere ripubblicato: possiamo
   citarlo, spiegarne il ruolo e rimandare alla fonte;
3. è onesto e utile scrivere in pagina che il prezzo SSB che pubblichiamo
   è un riferimento statistico e non l'indice su cui si negozia. Il
   lettore competente lo sa già: dirlo ci qualifica, tacerlo ci squalifica.

Se in futuro serve il dato per pezzatura, l'unica strada è un abbonamento
con licenza di ripubblicazione negoziata. Va messo a budget, non dato per
scontato.

## Stato delle fonti

| Fonte | Che cosa dà | Frequenza | Licenza | Automazione |
|---|---|---|---|---|
| SSB, tabella 03024 | Prezzo medio export e volumi, fresco e congelato | Settimanale, mercoledi | CC BY 4.0: riuso anche commerciale con attribuzione, link alla licenza e indicazione delle modifiche | API pubblica, già implementata |
| BCE, cambi di riferimento | Cambio giornaliero NOK/EUR | Giornaliera | Riuso con attribuzione | API pubblica, già implementata |
| EUMOFA (Commissione europea) | Importazioni settimanali per codice doganale, Stato importatore e provenienza, da dati doganali DG TAXUD | Settimanale, con circa due settimane di ritardo | Riuso dei contenuti della Commissione, CC BY 4.0 | File pubblici a indirizzo fisso, implementata |
| Eurostat Comext | Import ed export per Stato membro e partner, anche intra-UE | Mensile, due o tre mesi di ritardo | Riuso consentito con attribuzione | API pubblica, implementata |
| FranceAgriMer RNM | Quotazioni per prodotto e piazza, Rungis compreso | Settimanale | Non rilevante | **Esclusa**: il sito blocca lo scaricamento automatico |
| BMTI | Prezzi all'ingrosso dei mercati ittici italiani | Settimanale | Autorizzazione scritta | **Esclusa**: nessun collegamento automatico |
| Mercabarna | Quantità e prezzi medi del mercato ittico di Barcellona | Anche settimanale | Da verificare | Da valutare |
| FAO GLOBEFISH | Prezzi di oltre 350 prodotti sui mercati europei | Settimanale | Condizioni miste, eccezioni per dati di terzi: non estendere il permesso a tutto il portale | Da valutare |

Regola pratica, dal 21 novembre 2026: in pagina entrano solo fonti
pubbliche che dichiarano il riuso libero e si scaricano da un indirizzo
pubblico. Non si chiedono autorizzazioni e non si aggirano blocchi: una
fonte che non rispetta le due condizioni resta fuori.

## Il diritto sulla banca dati

Citare la fonte è necessario ma non sostituisce un permesso quando
serve. Costruire grafici originali non elimina i diritti sulla banca dati
sottostante, e l'estrazione ripetuta e sistematica di parti sostanziali è
proprio la condotta che il diritto sui generis limita.

Per questo il nostro archivio conserva solo le serie con licenza
verificata, e per le altre la sezione rimanda alla fonte invece di
ricostruirne il contenuto.

## Un rischio che nessuno mette in conto: la concorrenza

Finché pubblichiamo dati di fonti pubbliche il problema non si pone. Si
pone nel momento in cui venisse l'idea di costruire un indice
Pesceinrete raccogliendo i prezzi direttamente dagli operatori.

Raccogliere prezzi presso imprese concorrenti e restituirli al mercato è
uno scambio di informazioni sensibili. Si può fare, e nel settore
agroalimentare si fa, ma dentro regole precise: dati aggregati su un numero
sufficiente di contributori, nessuna riconducibilità al singolo, prezzi
storici e non futuri, ritardo nella pubblicazione, regolamento scritto.
Improvvisarlo esporrebbe Pesceinrete e i suoi contributori.

Se quella strada interessa, va impostata con un legale prima di chiedere il
primo prezzo a chiunque.

## Attribuzione da esporre in pagina

> Salmone — Dati: Statistics Norway (SSB), tabella 03024, CC BY 4.0, con
> elaborazioni di Pesceinrete (conversione in euro ai cambi di riferimento
> BCE della stessa settimana).
>
> Altre specie — Dati: EUMOFA (Commissione europea), importazioni UE
> settimanali da dati doganali, CC BY 4.0, con elaborazioni di Pesceinrete
> (valore unitario per provenienza, sole settimane complete).
>
> Arrivi mensili — Dati: Eurostat, Comext DS-045409.

La formula compare già nel piede della pagina e nell'intestazione di ogni
file CSV esportato.

## Eurostat Comext: come lo interroghiamo

Le tabelle Comext hanno una base distinta dal resto di Eurostat,
`https://ec.europa.eu/eurostat/api/comext/dissemination`, e non si possono
scaricare intere: vanno sempre filtrate. Le dimensioni sono REPORTER,
PARTNER, PRODUCT, FLOW, STAT_PROCEDURE e PERIOD; le misure sono
VALUE_IN_EUR e QUANTITY_IN_KG.

Chiediamo, per ciascuno dei codici 03021411 e 03021419: reporter IT, flusso
importazioni, frequenza mensile, una volta senza partner (tutte le
provenienze) e una volta con partner NO. I due codici vengono sommati
prima di calcolare il valore unitario, altrimenti la media sarebbe di due
medie.

Tre cose da ricordare quando si legge quel numero:

* è il valore dichiarato in dogana diviso la quantità: non è una
  quotazione e non è il prezzo pagato da nessuno;
* comprende il trasporto fino alla frontiera di ingresso, mentre il prezzo
  all'esportazione norvegese è preso all'uscita. I due livelli non sono
  confrontabili: lo è il loro andamento;
* lo Stato che registra l'importazione è spesso solo il punto di ingresso
  doganale. Una partita sdoganata in Olanda e venduta in Italia risulta
  importata in Olanda.

Quando esce un mese nuovo, Eurostat rivede anche i precedenti. Le revisioni
su questa fonte sono normali e l'archivio le conserva: non sono un errore
da inseguire.

## EUMOFA: come la leggiamo

EUMOFA pubblica le importazioni UE **settimanali** da dati doganali. Il
suo "Bulk Download" espone un file per anno a un indirizzo pubblico e
fisso; il modulo `ingest/eumofa_import.py` lo scarica, tiene le righe con
l'Italia come Stato importatore e calcola il valore unitario per
provenienza. Le regole (settimane complete, buchi, revisioni) sono
descritte in testa al modulo e in [fonti-per-specie.md](fonti-per-specie.md).

Se l'indirizzo cambia, il rimedio a mano è in
[SENZA-TERMINALE.md](SENZA-TERMINALE.md).
