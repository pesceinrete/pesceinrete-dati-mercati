# Pesceinrete — Dati e mercati

Sezione di dati di mercato per pesceinrete.com: archivio delle serie
storiche, aggiornamento automatico dalle fonti, pagina di consultazione
integrata in WordPress.

Non dipende da nessun servizio di chat, da nessun abbonamento e da nessuna
libreria esterna: gira con Python 3.11 o superiore e la sola libreria
standard. Il repository è l'unico posto dove vivono i dati, e resta
vostro.

**Per il web designer: [docs/CONSEGNA-WEB-DESIGNER.md](docs/CONSEGNA-WEB-DESIGNER.md).**
**Per metterlo in linea senza terminale, solo dal browser: [docs/SENZA-TERMINALE.md](docs/SENZA-TERMINALE.md).**
**Per chi usa il terminale: [docs/INSTALLAZIONE.md](docs/INSTALLAZIONE.md) e `./gestisci prova`.**

---

## Il comando unico

```
./gestisci prova        dati inventati + anteprima, per vedere com'è
./gestisci controlla    interroga le fonti senza scrivere niente
./gestisci reale        primo caricamento dei dati veri
./gestisci aggiorna     scarica, ricostruisce, collauda
./gestisci sito         ricostruisce solo i file della pagina
./gestisci test         tutti i controlli
./gestisci pacchetto    prepara la cartella da caricare su WordPress
./gestisci pulisci      cancella archivio e file generati
```

## Com'è fatto

```
config/      registro dei prodotti: aggiungerne uno è configurazione
core/        archivio, settimane e mesi, calcoli, bollettino
ingest/      una fonte per file: SSB, BCE, Eurostat Comext, RNM, EUMOFA
strumenti/   dati di prova, anteprima, cruscotto, rilevatore di novità
tests/       76 controlli su calcoli, parser (anche su risposte reali), registro, lingue e sorveglianza; 145 sulla pagina
web/         la pagina e i file che la alimentano
wordpress/   il plugin installabile dal pannello e, in alternativa, il file per il tema figlio
docs/        installazione, fonti e licenze, metodo, design, specie
.github/     il ciclo di aggiornamento automatico
```

Tre pezzi separabili: l'**archivio** (SQLite versionato, con lo storico
delle revisioni), la **pubblicazione** (uno script che genera un JSON
statico da 50 kB), la **presentazione** (un file HTML senza build e senza
framework). Se domani cambiate CMS, si riscrive solo il terzo.

## Che cosa mostra la pagina

Si apre in vista essenziale: il prezzo della settimana in euro, la sua
posizione rispetto alle stesse settimane dei cinque anni precedenti, la
sintesi e il bollettino. Chi vuole solo sapere se il prezzo è alto ha
finito.

La vista completa aggiunge l'andamento storico con date esatte, gli arrivi
in Italia, il confronto fra periodi con controllo di omogeneità, il
calcolatore del costo per chilogrammo utilizzabile e il metodo. Le sezioni
nascoste restano nel documento: contano per l'indicizzazione e per chi
legge senza JavaScript.

## Le regole che il codice fa rispettare

- Il prezzo di un periodo è sempre ponderato sui volumi.
- Due periodi con un numero diverso di settimane non producono percentuali
  sui totali.
- Una settimana mancante resta mancante: niente interpolazioni.
- La conversione in euro usa il cambio della stessa settimana, mai quello
  di oggi.
- Le revisioni della fonte vengono conservate: l'archivio è interrogabile
  a una data passata.
- Il valore è prezzo per volume, ed è etichettato come ricostruito: non
  è una conferma indipendente dell'andamento.
- Sotto tre anni di storico la lettura stagionale non viene pubblicata.
- Il bollettino scrive fatti, mai cause.
- Se un controllo non passa, online resta l'ultima versione valida.

## L'aggiornamento

Il ciclo controlla le fonti quattro volte al giorno, agli orari in cui
pubblicano, e pubblica solo quando c'è davvero qualcosa di nuovo. Un
controllo a vuoto costa pochi secondi e non lascia traccia.

Quando esce un dato, ricostruisce la pagina, la collauda, genera la bozza
del bollettino e il cruscotto, pubblica e avvisa sul webhook configurato.
Nessuno deve fare niente a mano.

## Due lingue, una base dati

Tutto esce in italiano e in inglese: pagina, sintesi statica, bollettino,
etichette. La base dati non ha lingua e non cambia; i testi generati
vengono dai dizionari in `core/testi.py`, la pagina inglese viene
generata da quella italiana a ogni build (`strumenti/traduci_pagina.py`),
con due controlli che fermano la pubblicazione se una traduzione non si
aggancia o se resta una parola italiana nei testi visibili. Per aggiungere
una terza lingua si aggiunge un dizionario, non una pagina.

## Metodo: due letture della stagione

La posizione stagionale è calcolata due volte: sui prezzi nominali, che
sono quelli che si pagano, e al netto del livello generale dei prezzi
(rapporto con la media mobile a 52 settimane), che toglie l'inflazione e
lascia la stagione. In un ciclo di rincari la prima lettura dice "sopra
la norma" ogni settimana e smette di informare; la seconda no. La pagina
le mostra entrambe. Le soglie di tutte le regole stanno in
`config/soglie.json`, e `./gestisci calibra` dice quante volte l'anno
scatta ciascuna regola sulla storia in archivio, per ricalibrarle con i
dati veri.

## Newsletter e avvisi

A ogni aggiornamento il ciclo genera la newsletter del giovedì in HTML con
stile in linea, in due lingue, pronta da incollare in Brevo, Mailchimp o
MailerLite (`web/newsletter/`), e valuta gli avvisi redazionali di
`config/avvisi.json` — soglie di prezzo e variazioni — che finiscono nel
messaggio sul webhook e in `web/data/avvisi.json`. Nel plugin si indica
l'indirizzo del modulo del servizio di newsletter: compare in pagina il
riquadro "Ricevi il bollettino ogni giovedì".

## Il calcolatore

Il costo per chilogrammo utilizzabile parte dal riferimento, chiede se è
all'origine o reso a destino (incoterm), e propone le rese tipiche per
lavorazione di ogni specie da `config/rese.json` — filetto trim C o D,
code HLSO, polpa sgusciata, baccalà dissalato — come scelte rapide, da
adeguare alle proprie.

## Le note della redazione

In `config/annotazioni.json` la redazione segna i fatti documentati con
la loro settimana — uno sciopero, una chiusura della pesca, un dazio — e
la pagina li mostra come marcatori numerati sui grafici, con la nota
sotto. Non spiegano il prezzo: lo datano. Il file si modifica
direttamente su GitHub, senza toccare altro. Le note segnate come
dimostrative spariscono da sole quando i dati diventano veri.

Il browser del lettore ricorda il prezzo che ha visto l'ultima volta per
ogni specie, e alla visita successiva la pagina gli dice cosa è cambiato
da allora. Resta sul suo dispositivo, non viene inviato a nessuno.

## Condivisione e stampa

Ogni specie ha un'immagine di anteprima 1200×630 — navy, prezzo in bianco,
variazioni, posizione stagionale — rigenerata a ogni aggiornamento e
dichiarata dal plugin come `og:image`: quando un buyer manda il link su
WhatsApp o LinkedIn compare la card con il prezzo, non un'anteprima vuota.
Dal grafico si scarica un PNG con fonte e settimana in calce, e si copia il
link alla vista esatta. La pagina ha uno stile di stampa: l'eroe diventa
bianco, i comandi spariscono, l'analisi completa esce tutta.

## La sorveglianza

Il ciclo è deterministico e deve restarlo: un modello non va messo a
girare la manovella. Va messo dove serve capire qualcosa di nuovo. Quando
un'esecuzione fallisce, `.github/workflows/sorveglianza.yml` raccoglie il
registro, chiede al modello una diagnosi in italiano piano e, se c'è una
correzione sicura — minima, solo in `ingest/` o `config/`, con tutti i
test che passano — la propone in una richiesta di modifica che la
redazione approva con un clic. Altrimenti apre una segnalazione con la
diagnosi e cosa fare a mano. Non tocca mai il ramo principale. Senza la
chiave del modello (segreto `ANTHROPIC_API_KEY`) apre comunque la
segnalazione con l'estratto del registro.

## Sicurezza

Il plugin esegue solo il codice incluso nel proprio pacchetto. Dal
repository scarica dati — JSON, blocchi di sintesi, immagini — e dai
blocchi di sintesi toglie comunque qualunque script. Un accesso abusivo
al repository non può far eseguire codice sul sito. L'account GitHub va
protetto con la verifica in due passaggi.

## Manutenzione

La pagina si mantiene in tre sorgenti separati, `web/src/pagina.html`,
`stile.css` e `script.js`; `strumenti/componi_pagina.py` li ricompone
nel file unico che il plugin inserisce. Il collaudo gira sul risultato.

## Lo stile

Un sistema di design proprio con i colori dei marchi — il blu `#1F8DCC`
del logo Pesceinrete e di IGB, il navy `#003757` del menu IGB, il fondo
cielo `#E6F6FF` — i loghi veri in testa e nel ponte verso IGB, Manrope
come unico carattere, scale fisse di tipografia e spazi.
Le motivazioni sono in [docs/scelte-di-design.md](docs/scelte-di-design.md).

## Le specie

Dieci: salmone, orata, spigola, polpo, gambero, merluzzo, tonno pinna
gialla, pesce spada, cozze, vongole. Per ciascuna un prezzo settimanale di
riferimento e le importazioni italiane mensili per provenienza, 39 serie
Comext in tutto. Le fonti, scelte per autorevolezza e automatizzabilità, e
le motivazioni sono in [docs/fonti-per-specie.md](docs/fonti-per-specie.md).

## Stato

Il sistema è completo e gira. I dati nell'anteprima sono dimostrativi per
tutte le specie: diventano reali con il workflow "Primo caricamento dei
dati veri", un pulsante nella scheda Actions del repository.

I parser di SSB e di Eurostat Comext sono stati verificati sulle risposte
reali dei due servizi (ottobre 2026): formato CSV della PxWebApi v2 di SSB,
struttura JSON di DS-045409 con quantità in quintali. L'API con i dataset
pronti di SSB, dismessa a fine 2025, non viene più usata. RNM Rungis: le
pagine prodotto e le diciture delle mercuriali sono quelle reali, la prima
esecuzione le conferma. BMTI resta da file esportato.

Due modi di installare: un plugin WordPress che si carica dal pannello e
crea le pagine da solo, oppure i file nel tema figlio.

## Una cosa da sapere

Il prezzo pubblicato è un riferimento statistico all'esportazione, su
tutte le pezzature e destinazioni. Non è l'indice su cui si negozia:
quello è SISALMONI, a pagamento e non ripubblicabile. La pagina lo dice
apertamente, ed è quello che la rende credibile davanti a un operatore
che il mercato lo conosce.
