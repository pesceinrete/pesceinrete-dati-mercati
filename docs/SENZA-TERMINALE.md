# Mettere in linea la sezione senza usare un terminale

Tutto quello che segue si fa dal browser, con clic. Servono un account
GitHub (gratuito) e l'accesso di amministratore a WordPress. In tutto,
circa 40 minuti, di cui metà di attesa.

---

## 1. Il repository (10 minuti)

1. Vai su github.com, accedi (o crea un account gratuito).
2. In alto a destra, **+** → **New repository**. Nome:
   `pesceinrete-dati-mercati`. Visibilità: **Public** (serve per GitHub
   Pages gratuito; i dati sono pubblici per natura e il codice non contiene
   segreti). **Create repository**.
3. Nella pagina del repository vuoto, clicca **uploading an existing file**.
   Trascina nella finestra **tutto il contenuto** della cartella del
   progetto (non la cartella stessa: aprila e seleziona tutto quello che
   c'è dentro, compresa la cartella `.github`). Attendi il caricamento,
   scrivi "Primo caricamento" nel campo in basso e **Commit changes**.

   Se la cartella `.github` non si vede quando selezioni i file (su alcuni
   sistemi è nascosta): su Windows, Visualizza → Elementi nascosti; su
   Mac, Cmd+Shift+. nella finestra di selezione.

4. **Settings** (in alto) → a sinistra **Actions** → **General** → in
   fondo, "Workflow permissions": seleziona **Read and write permissions**
   → **Save**.
5. **Settings** → a sinistra **Pages** → "Source": scegli **GitHub
   Actions**. Non serve altro.

## 2. I dati veri (5 minuti + attesa)

1. Scheda **Actions** (in alto). Se chiede di abilitare i workflow,
   conferma.
2. A sinistra, **Primo caricamento dei dati veri** → a destra **Run
   workflow** → nel campo scrivi `SI` → **Run workflow**.
3. Attendi 3-5 minuti. Quando il pallino diventa verde, clicca
   sull'esecuzione: in fondo trovi il **riepilogo** con la tabella delle
   specie pubblicate e, se qualcosa non ha risposto, il motivo.

   Pallino rosso: apri l'esecuzione e leggi quale passo ha fallito. Il
   caso più probabile è una fonte che non risponde in quel momento:
   rilancia dopo un'ora. Se fallisce di nuovo, copia il testo
   dell'errore e mandalo: si corregge in pochi minuti.

4. Sempre in **Actions**, lancia a mano anche **Pubblica i file della
   pagina su GitHub Pages** (Run workflow). Alla fine, nell'esecuzione,
   compare l'indirizzo pubblico, del tipo
   `https://nome-utente.github.io/pesceinrete-dati-mercati/`.
   **Copialo**: serve al passo 3.

Da questo momento il repository si aggiorna da solo quattro volte al
giorno e ripubblica i file ogni volta che c'è un dato nuovo.

## 3. WordPress (10 minuti)

1. Scarica dal repository il file `consegna/pesceinrete-dati-mercati-plugin.zip`
   (oppure usa quello consegnato insieme a questa guida).
2. Nel pannello di WordPress: **Plugin** → **Aggiungi nuovo** → **Carica
   plugin** → scegli lo zip → **Installa adesso** → **Attiva**.
   All'attivazione il plugin crea da solo le pagine `/dati-mercati/` e
   `/market-data/`, ognuna con una pagina figlia per specie.
3. **Impostazioni** → **Dati e mercati** → incolla l'indirizzo copiato al
   passo 2.4 nel campo "Indirizzo dei file pubblicati" → **Salva**.
4. **Aspetto** → **Menu**: aggiungi la voce "Dati e mercati" dentro
   "Mercati". Una voce sola: i pulsanti della sezione stanno dentro la
   pagina.
5. Apri `/dati-mercati/` dal telefono. Se compare la fascia rossa "Dati
   dimostrativi", il passo 2 non è completato o l'indirizzo del passo 3.3
   non è corretto: controlla che finisca con una barra.

## 4. Autorizzazioni: nessuna

Tutte le fonti in uso (Statistics Norway, EUMOFA, Eurostat, BCE) sono
pubbliche e dichiarano il riuso libero con citazione della fonte. Non c'è
nessuna richiesta da inviare. La citazione la mette la pagina da sola.

## Cosa succede dopo

Niente che richieda te. Il ciclo controlla le fonti quattro volte al
giorno e pubblica solo quando c'è un dato nuovo. Se vuoi un avviso:
**Settings** → **Secrets and variables** → **Actions** → **New repository
secret**, nome `NOTIFICA_WEBHOOK`, valore l'indirizzo di un webhook Slack,
Teams o di un servizio di posta. Senza, GitHub ti scrive solo se qualcosa
fallisce.

## Attivare la sorveglianza (consigliato)

Se un giorno il ciclo fallisce — una fonte cambia pagina, un codice
cambia nome — la sorveglianza ti apre da sola una segnalazione nel
repository con la spiegazione in italiano e, quando possibile, una
richiesta di modifica già pronta: la approvi con il pulsante verde
"Merge". Per attivarla serve una chiave API di Anthropic (console.anthropic.com,
sezione API keys): **Settings** → **Secrets and variables** → **Actions**
→ **New repository secret**, nome `ANTHROPIC_API_KEY`, valore la chiave.
Costa qualche centesimo per ogni guasto; senza chiave la segnalazione si
apre lo stesso, solo senza la diagnosi.

## Attivare la newsletter

Serve un servizio di invio (Brevo, Mailchimp, MailerLite: tutti hanno un
piano gratuito). Nel servizio si crea un modulo di iscrizione e si copia
l'indirizzo a cui il modulo invia i dati (il campo "action"). In
WordPress, Impostazioni → Dati e mercati → "Modulo di iscrizione al
bollettino": si incolla, si salva. In pagina compare il riquadro "Ricevi
il bollettino ogni giovedì".

Ogni giovedì il repository genera la mail pronta in `web/newsletter/`,
nelle due lingue, con oggetto, versione HTML e versione in testo: si
incolla nel servizio e si invia. Quando il servizio lo permette, l'invio
si può programmare dal file stesso via API: è un passo successivo.

## Aggiungere una nota sui grafici

Nel repository, aprire `config/annotazioni.json`, cliccare la matita,
aggiungere una voce come questa dentro l'elenco:

```json
{ "specie": "orata", "settimana": "2026-W41",
  "it": "Sciopero dei trasporti in Grecia", "en": "Transport strike in Greece" }
```

**Commit changes**. Al prossimo aggiornamento la nota compare come
marcatore azzurro sui grafici dell'orata, con il testo sotto. `"specie":
"tutte"` la mette su tutte le schede.

## Se i dati EUMOFA non arrivano

I prezzi settimanali di tutte le specie tranne il salmone vengono da un
file che EUMOFA pubblica a un indirizzo fisso. Se quell'indirizzo cambia,
nel riepilogo dell'esecuzione compare "EUMOFA: scaricamento fallito" e la
pagina resta sull'ultima settimana valida: non si rompe niente.

Rimedio a mano, due minuti:

1. apri il Bulk Download di EUMOFA (dal sito eumofa.eu), scegli
   **Weekly-Import** e scarica il file dell'anno in corso;
2. caricalo nel repository, nella cartella `dati/manuale/` (**Add file →
   Upload files**), senza cambiargli nome;
3. avvisa chi mantiene il codice: l'indirizzo nuovo va scritto in
   `ingest/eumofa_import.py`, alla riga `BASE`.
