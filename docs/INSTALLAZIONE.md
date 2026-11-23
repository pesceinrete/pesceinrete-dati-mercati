# Installazione

Tre fasi: mettere in piedi l'aggiornamento automatico, collegare i dati
veri, pubblicare la pagina su WordPress. In tutto meno di un'ora, di cui
la maggior parte di attesa.

Serve: un repository (GitHub va bene, è gratuito per questo uso), accesso
FTP o al file manager dell'hosting, e un tema figlio di JNews. Se il tema
figlio non esiste, va creato prima: modificare il tema originale
significherebbe perdere tutto al primo aggiornamento del tema.

---

## Fase 1. L'aggiornamento automatico

1. Creare un repository privato e caricarci il contenuto di questa
   cartella.
2. Nelle impostazioni del repository, sezione Actions, verificare che i
   workflow abbiano il permesso di scrittura ("Read and write
   permissions"): serve a pubblicare i dati aggiornati.
3. Facoltativo ma consigliato: nelle impostazioni, Secrets and variables →
   Actions, creare il segreto `NOTIFICA_WEBHOOK` con l'indirizzo di un
   webhook Slack, Teams o di un servizio di posta. È quello che vi
   avvisa quando esce un dato nuovo o quando una fonte non risponde.
   Senza il segreto il sistema funziona lo stesso, in silenzio.
4. Aprire la scheda Actions ed eseguire a mano "Aggiornamento dei dati"
   la prima volta, per vedere che tutto giri.

Da qui in poi il ciclo controlla le fonti quattro volte al giorno e
pubblica solo quando c'è qualcosa di nuovo.

## Fase 2. I dati veri

Sul proprio computer, dentro la cartella del progetto:

```bash
./gestisci controlla     # interroga le fonti e mostra cosa trova
```

Questo passo non scrive niente. Interroga SSB, le serie Comext e i file
settimanali EUMOFA. Serve a verificare che le fonti
rispondano e che le etichette delle categorie siano riconosciute. Se SSB
ha cambiato le diciture, lo script si ferma con un errore esplicito
invece di caricare la serie sbagliata: in quel caso si aggiorna la mappa
`RICONOSCIMENTO` in `ingest/ssb_laks.py` e si riprova.

Quando il controllo passa:

```bash
./gestisci reale         # primo caricamento: circa 1.300 settimane dal 2000
```

Il comando cancella il marcatore `dati/DIMOSTRATIVO`, e da quel momento la
fascia rossa in cima alla pagina sparisce.

Poi si fa un commit e si carica il repository: l'archivio aggiornato deve
stare lì, perché è quello che il ciclo automatico continuerà ad
aggiornare.

## Fase 3. La pagina su WordPress

```bash
./gestisci pacchetto     # prepara la cartella consegna/
```

Caricare via FTP, dentro il tema figlio:

```
consegna/dati-mercati/   ->  wp-content/themes/<tema-figlio>/dati-mercati/
consegna/inc/            ->  wp-content/themes/<tema-figlio>/inc/
```

Aggiungere in fondo al `functions.php` del tema figlio:

```php
require_once get_stylesheet_directory() . '/inc/pesceinrete-dati-mercati.php';
```

In WordPress:

1. Pagine → Aggiungi nuova, titolo "Dati e mercati", permalink
   `/dati-mercati/`.
2. Modello: larghezza piena. I grafici hanno bisogno di spazio.
3. Nel contenuto, un blocco Shortcode con dentro: `[dati_mercati]`
4. Aspetto → Menu: aggiungere la voce "Dati e mercati" **dentro**
   "Mercati". Una sola voce: i pulsanti della sezione stanno dentro la
   pagina, non nel menu del sito.
5. Pubblicare e guardare la pagina da telefono, che è dove verrà letta
   più spesso.

**Una pagina per specie, consigliato.** La pagina principale permette di
passare da una specie all'altra sul posto, ma per i motori di ricerca
ogni specie deve avere un indirizzo proprio, con titolo e testo propri:
"prezzo dell'orata" deve portare a `/dati-mercati/orata/`, non a una
pagina generica. Per farlo:

1. creare una pagina figlia di "Dati e mercati" per ogni specie, con slug
   uguale all'identificativo del registro (`salmone`, `orata`, `spigola`,
   `gambero`, `polpo`, `calamaro`, `seppia`, `astice`, `pesce_spada`) e dentro lo shortcode `[dati_mercati prodotto="orata"]`;
2. nel `functions.php` aggiungere:

```php
add_filter( 'pir_dm_url_prodotto', function () {
    return home_url( '/dati-mercati/{id}/' );
} );
```

Da quel momento il selettore delle specie in pagina diventa un elenco di
collegamenti, ogni pagina ha titolo, descrizione e blocco statico della
propria specie, e la data di ultima modifica è quella vera dei dati.

## La versione inglese

La base dati non cambia: contiene numeri, periodi e identificativi, non
parole. La lingua entra solo nei testi generati e nelle etichette, e il
sistema produce già tutto in due lingue: `dati-mercati.en.html`,
`mercati.en.json`, `sintesi-salmone.en.html` e la bozza del bollettino in
inglese. Il pacchetto di consegna li contiene.

Per pubblicarla:

1. creare una seconda pagina WordPress con permalink `/market-data/`,
   stesso modello a larghezza piena;
2. inserire lo shortcode `[dati_mercati lingua="en"]`;
3. non serve altro: il file PHP riconosce lo slug `market-data`, usa i
   file inglesi e aggiunge da solo i collegamenti `hreflang` fra le due
   pagine.

Se si usa un plugin multilingua (WPML, Polylang), la pagina inglese va
creata come traduzione di quella italiana e lo shortcode resta lo stesso.

## Aggiornare la pagina dopo la prima volta

I dati si aggiornano da soli, ma i file sul server no: il ciclo automatico
scrive nel repository, non sul vostro hosting. Ci sono due modi.

**Il modo semplice.** Una volta a settimana si scarica dal repository il
file `web/data/mercati.json` e la relativa `sintesi-salmone.html` e si
sovrascrivono via FTP. Due file, un minuto.

**Il modo definitivo.** Si fa puntare la sezione direttamente ai file
pubblicati dal repository, che GitHub serve già come pagine statiche.
In quel caso nel `functions.php` basta aggiungere prima dello shortcode:

```php
add_filter( 'pir_dm_url_dati', function () {
    return 'https://<utente>.github.io/<repository>/web/data/mercati.json';
} );
```

e i dati sul sito diventano sempre aggiornati senza toccare più nulla.
Va fatto dopo aver attivato GitHub Pages sul repository.

Un'avvertenza su questo secondo modo: il blocco statico di sintesi (la
tabella delle ultime dodici settimane e il testo che la precede) resta
quello caricato via FTP, mentre i grafici leggono i dati dal repository.
Se non si aggiorna mai il file `sintesi-salmone.html` sul server, i due
finiscono per non coincidere. Per evitarlo, il file PHP legge anche la
sintesi da remoto quando il filtro è attivo, con una cache di un'ora, e
ricade sulla copia locale se il repository non risponde.

---

## Controllo finale

- la fascia rossa "Dati dimostrativi" non c'è più;
- la data dell'ultimo aggiornamento in fondo alla pagina è quella vera;
- `/dati-mercati/` compare nella sitemap;
- lo strumento di test dei risultati avanzati di Google riconosce i dati
  strutturati `Dataset`;
- la pagina si legge bene da telefono.

## Se qualcosa non va

**La pagina è bianca.** Il file `dati-mercati.html` non è nella cartella
giusta, oppure il tema figlio non è attivo.

**I grafici non si vedono ma il testo si.** Il modello della pagina non è
a larghezza piena, oppure un plugin di ottimizzazione sta rinviando
l'esecuzione di JavaScript: escludere la pagina da quel plugin.

**I colori sono sbagliati.** I colori non vengono dal tema: sono scritti
nel foglio di stile della sezione. Se mai servisse cambiarli, nel CSS del
tema figlio:
`.pir-mercati{ --azzurro:#1F8DCC; --navy:#003757; }`

**I dati sono fermi.** Aprire il cruscotto allegato all'ultima esecuzione:
dice quale fonte non risponde e da quanto. Se una fonte è in ritardo,
online resta l'ultimo dato valido con la sua data. Non va forzato niente.
