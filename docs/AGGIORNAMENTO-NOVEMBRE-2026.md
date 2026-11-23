# Aggiornamento di novembre 2026 — nota per il tecnico

Cambiano le fonti dei prezzi. Rungis (RNM) e BMTI escono dal progetto;
entrano i dati doganali settimanali di EUMOFA (Commissione europea).
Nessuna autorizzazione da chiedere, nessun blocco da aggirare.

Tempo richiesto: circa 30 minuti. Nessun terminale.

## Cosa cambia

| Prima | Adesso |
|---|---|
| 10 specie, di cui 9 senza dati (Rungis e BMTI non raggiungibili) | 9 specie, tutte con dati veri |
| Salmone: SSB | Salmone: SSB (invariato) |
| Orata, spigola, polpo, gambero, pesce spada: Rungis | Valore medio delle importazioni in Italia per provenienza, EUMOFA, settimanale |
| Merluzzo, tonno, cozze, vongole | Tolte: il dato settimanale non regge (vedi `docs/fonti-per-specie.md`) |
| n.d. | Nuove: calamaro, seppia, astice |

## Difetti trovati in linea (verificati il 21 novembre)

1. **Il flusso "Aggiornamento dei dati" è disattivato a mano** e non ha
   mai girato: per questo i dati sono fermi al 17 novembre. Va riattivato
   (passo 6).
2. **`pubblica-pagine.yml` non è un file valido** (riga `paths:` rientrata
   male, dal 17 novembre). GitHub lo rifiuta: "Invalid workflow file,
   line 8". Corretto in questa versione.
3. **Importazioni Eurostat del salmone assenti.** Il codice doganale era
   sbagliato: quello giusto è 03021400 (verificato: risponde con i dati).
   In più, la Norvegia non compare fra le provenienze perché il salmone
   norvegese arriva in Italia passando da altri paesi UE: ora si seguono
   Svezia, Danimarca, Paesi Bassi e Polonia.
4. **Le 22 pagine WordPress sono tutte alla radice del sito**, senza
   pagina genitore (`/salmone/`, `/orata-2/`, `/pesce_spada-2/`...). La
   pagina però collegava le specie a `/dati-mercati/salmone/`, che non
   esiste: il sito reindirizza a una fotografia. Il plugin 1.1.0 non
   presuppone più una struttura: legge dove stanno davvero le pagine.
5. **Titolo e anteprima social della pagina d'ingresso erano quelli del
   salmone**, e Yoast SEO sovrascriveva il titolo. Corretto nel plugin.

## Passi

### 1. Prova dello scaricamento (5 minuti)

Caricare `.github/workflows/prova-eumofa.yml`, poi **Actions → Prova
EUMOFA → Run workflow**. Deve finire con "ESITO: RIUSCITO". Se fallisce,
fermarsi e inviare la tabella del riepilogo.

### 2. Caricare i file nuovi

Dallo zip, caricare nel repository sovrascrivendo (**Add file → Upload
files**, una cartella per volta):

- `.github/workflows/` (tutti e cinque i file)
- `config/`, `core/`, `ingest/`, `strumenti/`, `tests/`
- `web/src/`, `web/dati-mercati.html`, `web/dati-mercati.en.html`
- `wordpress/`, `docs/`
- `costruisci_dati_sito.py`, `gestisci`, `README.md`

Le cartelle `dati/` e `web/data/` non sono nello zip: le ricrea il passo 4.

### 3. Cancellare quattro file

Il caricamento da web non cancella i file vecchi. Vanno tolti a mano
(aprire il file → icona del cestino → Commit):

- `ingest/rnm_rungis.py`
- `ingest/bmti.py`
- `config/rnm.json`
- `config/bmti.json`

Se restano non rompono niente, ma sono codice morto.

### 4. Primo caricamento

**Actions → Primo caricamento dei dati veri → Run workflow → SI.**
Scarica SSB, BCE, Eurostat e i file EUMOFA dal 2023 (quattro file da circa
20 MB), ricostruisce le pagine e pubblica. Nel riepilogo devono comparire
nove specie, tutte con ultima settimana e prezzo, e la tabella "Esito
delle fonti". Inviare il riepilogo.

### 5. Plugin WordPress, versione 1.1.0 (sito con Yoast SEO)

Caricare `pesceinrete-dati-mercati-plugin.zip` da **Plugin → Aggiungi
nuovo → Carica plugin → Sostituisci**, poi aprire una pagina qualsiasi
del pannello: il plugin crea le pagine che mancano (calamaro, seppia,
astice, in italiano e in inglese), private, e non duplica quelle che
esistono già.

Poi, a mano, in quest'ordine:

1. **Cestinare** le pagine di merluzzo, tonno, cozze e vongole, in
   italiano e in inglese (otto pagine).
2. **Sistemare gli indirizzi prima di pubblicare** (consigliato: un
   indirizzo pubblicato non si cambia più volentieri). Per ogni pagina di
   specie: Modifica rapida → Genitore "Dati e mercati" (o "Market data"
   per quelle inglesi) → Slug uguale al nome della specie (`orata`, non
   `orata-2`). Vale anche per `/salmone/`, che diventa
   `/dati-mercati/salmone/`. Se le pagine sono state messe alla radice
   apposta, si possono lasciare dove sono: il plugin funziona lo stesso.
3. **Pubblicare** le pagine delle specie quando sono state controllate.
   Finché una pagina è privata, i visitatori non vedono quella specie nel
   selettore: nessun collegamento porta a un errore.

Da controllare dopo l'installazione, nel sorgente di `/dati-mercati/`:

- `<title>` deve essere "Dati e mercati ittici: prezzi settimanali
  all'importazione e arrivi in Italia — Pesceinrete";
- `og:title` e `og:description` di Yoast devono essere quelli della
  sezione. Resterà un terzo `og:title` ("Dati e mercati", con la
  descrizione "Visita l'articolo per saperne di più"): non viene né dal
  plugin né da Yoast, ma dal tema o da un altro plugin di condivisione.
  Se dà fastidio nelle anteprime, va individuato e spento per queste
  pagine.

I filtri per Yoast sono scritti sui nomi documentati, ma non è stato
possibile provarli su un sito vero.

### 6. Riattivare il ciclo quotidiano

**Actions → Aggiornamento dei dati → Enable workflow.** Oggi risulta
disattivato a mano. Poi **Run workflow** una volta, per verificare che
finisca in verde. Da lì gira da solo, più volte al giorno.

## Come si aggiorna da qui in poi

Da solo. Il ciclo quotidiano controlla tutte le fonti; EUMOFA riscrive i
file il martedì e il sistema li riscarica solo se sono cambiati. Viene
pubblicata solo l'ultima settimana completa alla fonte, cioè circa due
settimane prima della data di oggi.

Se EUMOFA sposta i file: la pagina resta sull'ultima settimana valida e
il resoconto segnala l'errore. Il rimedio a mano è in
`docs/SENZA-TERMINALE.md`, sezione "Se i dati EUMOFA non arrivano".

## Cosa è stato verificato e cosa no

Verificato il 21 novembre su un computer con accesso libero alla rete:
i quattro file EUMOFA si scaricano (2023-2026); il codice 03021400
risponde su Eurostat; tutti i codici doganali del registro esistono; il
caricamento completo dà 12.304 osservazioni in 68 serie, con tutte e nove
le specie; 88 controlli sui calcoli superati.

Non ancora verificato:

- lo scaricamento EUMOFA dalle macchine di GitHub (è il passo 1);
- il plugin 1.1.0 su WordPress: provato solo con un sito simulato;
- le provenienze del salmone (Svezia, Danimarca, Paesi Bassi, Polonia):
  scelte per conoscenza del mercato, da confermare nel riepilogo del
  passo 4;
- l'aspetto delle pagine con lo storico vero 2023-2025.
