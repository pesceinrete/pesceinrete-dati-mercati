# Aggiornamento 1.2.1 — correzioni dopo la messa in linea (25 novembre 2026)

Installazione riuscita: nove specie in linea, dati veri, ciclo automatico
attivo. Questa versione corregge i difetti emersi dal controllo delle
pagine pubblicate. Tempo: 15 minuti.

## La linguetta italiano / inglese è dentro il plugin

La modifica fatta sul sito (titolo della pagina con accanto la linguetta
"English" / "Italiano" e la bandiera) è stata riportata nel plugin, con lo
stesso codice HTML e lo stesso stile che sono oggi in linea: installando
la 1.2.1 non si perde. Due differenze volute:

- l'indirizzo dell'altra lingua non è scritto a mano: il plugin lo legge
  dalle pagine che contengono lo shortcode, quindi segue gli slug veri
  (per esempio `/market-data/sea-bream/`);
- la linguetta compare solo se la pagina gemella esiste ed è pubblicata.

Se sul sito sono state fatte **altre** modifiche al file del plugin oltre
alla linguetta, vanno segnalate prima di installare: questa versione le
sovrascriverebbe.

## Cosa corregge

| Difetto visto in linea | Correzione |
|---|---|
| Il riquadro di iscrizione al bollettino era visibile anche senza un indirizzo di destinazione: il tema del sito annullava l'attributo `hidden` | Ora resta nascosto finché non si compila l'indirizzo in Impostazioni → Dati e mercati |
| Tre serie di metadati social per pagina (plugin, Yoast, Jetpack) | Sulle pagine della sezione resta una serie sola |
| Sulla pagina d'ingresso il titolo diventava quello del salmone dopo il caricamento | Resta quello della sezione |
| Prima del caricamento ogni scheda mostrava "Salmone atlantico" | Nome e prezzo della specie giusta sono scritti dal server |
| Le pagine inglesi non dichiaravano la lingua | Il contenuto della sezione dichiara `lang="en"` |
| Tabella "Tutte le specie, questa settimana": le fonti non sono tutte della stessa settimana | Si chiama "ultimi dati disponibili" e ogni riga mostra la sua settimana |
| "Ultimi dodici mesi" senza dire quali | Il testo indica il periodo, per esempio da settembre 2025 ad agosto 2026 |
| Astice 17,07 invece di 17,08 | Arrotondamento commerciale ovunque |
| Il CSV delle specie in euro citava il cambio BCE | La nota del CSV dipende dalla fonte |
| La scheda del gambero parlava di "vannamei": il codice doganale identifica solo il genere Penaeus | Testo corretto |

## Passi

1. **GitHub.** Caricare dallo zip, sovrascrivendo: `.github/workflows/aggiorna-dati.yml`,
   `config/`, `core/`, `strumenti/`, `tests/`, `web/src/`, `web/dati-mercati.html`,
   `web/dati-mercati.en.html`, `wordpress/`, `docs/`, `costruisci_dati_sito.py`.
2. **Actions → Aggiornamento dei dati → Run workflow.** Lanciato a mano
   ora ricostruisce sempre le pagine, anche senza dati nuovi. Deve finire
   in verde.
3. **WordPress.** Plugin → Aggiungi nuovo → Carica plugin →
   `pesceinrete-dati-mercati-plugin.zip` (versione 1.2.1) → Sostituisci.
   Poi svuotare la cache del sito, se c'è un plugin di cache.

## Da controllare dopo

Nel sorgente di una scheda, per esempio `/dati-mercati/seppia/`:

- un solo `og:title` e un solo `og:description`;
- `<h2 ... id="pir-nome-prodotto">Seppia</h2>` già nel sorgente;
- nessun riquadro di iscrizione visibile in pagina;
- titolo e linguetta della lingua presenti una volta sola, in cima alla sezione.

I filtri che spengono i metadati di Yoast e Jetpack sono stati provati
solo su un sito simulato. Se dopo l'installazione i metadati risultano
ancora doppi, oppure spariscono del tutto, segnalarlo: si torna alla
versione 1.1.0 ricaricando lo zip precedente.
