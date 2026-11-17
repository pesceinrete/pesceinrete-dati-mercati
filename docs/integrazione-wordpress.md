# Integrazione su pesceinrete.com

## Il principio

La pagina non deve dipendere da nessuna chat, da nessun account e da
nessun servizio esterno che possa cambiare condizioni. Deve essere un
pezzo di Pesceinrete: stesso dominio, stessa testata, stesso menu, stessa
indicizzazione.

L'architettura è quindi in tre pezzi separabili:

1. **archivio** — SQLite versionato nel repository. È vostro, sta in un
   file, si copia e si ispeziona;
2. **pubblicazione** — uno script genera `mercati.json`, un file statico di
   circa 40 kB per prodotto, anch'esso versionato;
3. **presentazione** — un file HTML che legge quel JSON. Nessuna build,
   nessun framework, nessuna dipendenza da installare.

Se domani cambiate hosting o CMS, la parte 3 si riscrive e le parti 1 e 2
restano.

## Dove mettere i file

Caricate `dati-mercati.html` e `data/mercati.json` in una cartella del
tema figlio, per esempio `wp-content/themes/<tema-figlio>/dati-mercati/`.

Il JSON viene sostituito ogni settimana dall'aggiornamento automatico. La
pagina non va mai toccata.

## Metodo consigliato: uno shortcode

Nel `functions.php` del tema figlio:

```php
/**
 * Sezione "Dati e mercati".
 * Uso: [dati_mercati] dentro una pagina WordPress.
 */
function pesceinrete_dati_mercati() {
    $cartella = get_stylesheet_directory() . '/dati-mercati/';
    $indirizzo = get_stylesheet_directory_uri() . '/dati-mercati/';

    if ( ! file_exists( $cartella . 'dati-mercati.html' ) ) {
        return '<p>Sezione non disponibile.</p>';
    }

    $html = file_get_contents( $cartella . 'dati-mercati.html' );

    // Teniamo solo il contenuto: testata, menu e piede sono quelli del sito.
    if ( preg_match( '#<body[^>]*>(.*)</body>#sì, $html, $parti ) ) {
        $html = $parti[1];
    }

    // Il blocco statico di sintesi: testo vero, indicizzabile e leggibile
    // anche se JavaScript non parte. Va inserito lato server, non dal browser.
    $sintesi = $cartella . 'data/sintesi-salmone.html';
    if ( file_exists( $sintesi ) ) {
        $html = str_replace(
            '<div id="pir-sintesi-statica"></div>',
            '<div id="pir-sintesi-statica">' . file_get_contents( $sintesi ) . '</div>',
            $html
        );
    }

    // La versione nel nome forza il rinfresco della cache a ogni aggiornamento.
    $versione = @filemtime( $cartella . 'data/mercati.json' ) ?: time();
    $url_dati = esc_url( $indirizzo . 'data/mercati.json?v=' . $versione );

    return '<script>window.PESCEINRETE_URL_DATI="' . $url_dati . '";</script>' . $html;
}
add_shortcode( 'dati_mercati', 'pesceinrete_dati_mercati' );
```

Poi si crea la pagina WordPress "Dati e mercati" con indirizzo
`/dati-mercati/`, si incolla `[dati_mercati]` nel contenuto e si sceglie
un modello a larghezza piena.

Nel menu principale va **una sola voce**, "Dati e mercati", dentro
"Mercati". I pulsanti della sezione (prodotto, confronto, costo, metodo)
restano dentro la pagina: non vanno nel menu del sito.

## Convivenza con il tema

Tutto il foglio di stile è racchiuso in `.pir-mercati` e tutte le classi
cominciano per `pir-`. Non tocca nulla del tema e il tema difficilmente
tocca lui.

Colori e caratteri non vanno impostati a mano: la sezione li legge dal
tema quando la pagina si carica. Prende il carattere dal corpo e dal primo
titolo, il colore del testo dal corpo, e il colore d'accento cercandolo
prima fra le variabili del tema, poi nei collegamenti di navigazione e di
categoria. Le tinte derivate, la versione scura e quella schiarita per la
banda dei grafici, sono calcolate da quel colore.

Se il rilevamento automatico prendesse il colore sbagliato, si fissa a
mano scrivendo nel CSS del tema figlio:

```css
.pir-mercati{ --accento:#______; }
```

Una riga sola, e vince su tutto il resto.

Se il tema impone un contenitore stretto serve un modello di pagina a
larghezza piena: i grafici hanno bisogno di spazio.

## Prima del collaudo pubblico

- rimuovere `strumenti/genera_dati_dimostrativi.py` dall'esecuzione e
  cancellare il file `dati/DIMOSTRATIVO`: finché esiste, la pagina
  mostra la fascia rossa;
- verificare che `/dati-mercati/` sia nella sitemap;
- controllare che i dati strutturati `Dataset` vengano letti (strumento di
  test dei risultati avanzati di Google);
- provare la pagina da telefono, che è dove verrà letta più spesso.

## Indicizzazione

La sezione produce pagine che rispondono a ricerche ricorrenti tutto
l'anno: "prezzo salmone", "quotazioni salmone norvegese", e poi le stesse
per ogni prodotto aggiunto. Sono query costanti, non di attualità: una
pagina aggiornata ogni settimana, con dati strutturati e fonte
verificabile, ha un vantaggio strutturale su un articolo che invecchia.

Il punto tecnico che decide tutto: i numeri dentro JavaScript non vengono
indicizzati. Per questo il generatore produce `sintesi-<prodotto>.html`,
un blocco di testo vero con la lettura della settimana, la tabella delle
ultime dodici settimane e le domande frequenti. Lo shortcode qui sopra lo
inserisce lato server. Senza quel blocco, per un motore di ricerca la
pagina sarebbe quasi vuota.

Tre accorgimenti che valgono più di qualunque altra ottimizzazione:

1. il titolo e la descrizione devono contenere il prodotto e la parola
   prezzo, non il nome della sezione;
2. la data dell'ultimo aggiornamento deve essere visibile e vera;
3. gli articoli di Pesceinrete sui mercati devono collegarsi alla scheda
   prodotto, e la scheda deve collegarsi agli articoli.

## Cosa serve dalla redazione

L'aggiornamento è automatico, la responsabilità no. Ogni giovedi mattina
qualcuno apre `redazione/cruscotto.html`, che l'esecuzione automatica
allega come artefatto: dice se le serie sono arrivate, quali scarti
guardare, che cosa ha corretto la fonte e che cosa dice la bozza del
bollettino. Sono cinque minuti, ma senza quei cinque minuti il primo dato
sbagliato lo scopre un lettore.

Il cruscotto non va caricato sul sito: è una pagina interna, e riporta
anche il divieto di indicizzazione.

## Il bollettino

La bozza settimanale viene generata dai dati e salvata in
`web/bollettini/`. Contiene solo fatti che il grafico non mostra da solo:
il passaggio di fascia stagionale, un movimento contrario a quello
abituale del periodo, un rialzo che in realtà è il cambio, volumi fuori
scala, correzioni della fonte. Se non c'è niente, lo dice.

Le cause non le scrive: quelle le mette la redazione, dopo averle
verificate con gli operatori. È esattamente la differenza fra un
bollettino che si legge e uno che ripete i numeri già visibili.
