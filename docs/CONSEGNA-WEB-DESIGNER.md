# Consegna al web designer — sezione "Dati e mercati"

Questo documento dice che cosa ricevi, che cosa devi fare, in che ordine,
e che cosa non toccare. Il resto della documentazione è di supporto.

## Che cosa ricevi

| File | A cosa serve |
|---|---|
| `pesceinrete-dati-mercati-plugin.zip` | Il plugin WordPress. Si carica dal pannello, crea le pagine da solo |
| `pesceinrete-dati-mercati.zip` | Il progetto completo (dati, codice, workflow). Va caricato su GitHub, non su WordPress |
| `GUIDA-SENZA-TERMINALE.md` | La procedura passo per passo, solo dal browser, per GitHub e WordPress |
| `pesceinrete-anteprima.html` | L'anteprima della pagina fuori dal sito, con dati dimostrativi |

Dentro il progetto, `docs/INSTALLAZIONE.md` è la stessa procedura per chi
usa il terminale, e `README.md` è la panoramica.

## Due lavori, in quest'ordine

**1. GitHub (chi gestisce il repository — può essere la stessa persona).**
Seguire `GUIDA-SENZA-TERMINALE.md`, passi 1 e 2: creare il repository,
caricare il progetto, abilitare i permessi dei workflow, attivare GitHub
Pages, lanciare "Primo caricamento dei dati veri". Alla fine si ottiene un
indirizzo del tipo `https://<utente>.github.io/pesceinrete-dati-mercati/`.
Quell'indirizzo serve al passo successivo. Senza, il plugin funziona lo
stesso con i dati inclusi nel pacchetto, ma fermi alla data del pacchetto.

**2. WordPress (il web designer).**

1. Plugin → Aggiungi nuovo → Carica plugin → `pesceinrete-dati-mercati-plugin.zip` → Attiva.
   All'attivazione il plugin crea 22 pagine **private**: `/dati-mercati/` e
   `/market-data/` con una pagina figlia per specie (`salmone`, `orata`,
   `spigola`, `polpo`, `gambero`, `merluzzo`, `tonno`, `pesce_spada`,
   `cozze`, `vongole`). Private: le vede solo chi è loggato come
   amministratore.
2. Impostazioni → Dati e mercati → "Indirizzo dei file pubblicati":
   incollare l'indirizzo di GitHub Pages del passo 1 → Salva.
3. Aprire `/dati-mercati/` da loggato e controllare con il tema vero:
   larghezza, menu, carattere. Se qualcosa stona, vedere "Regolazioni".
4. Aspetto → Menu: aggiungere **una sola voce**, "Dati e mercati", dentro
   "Mercati". I pulsanti della sezione stanno dentro la pagina.
5. Quando l'aspetto convince: Impostazioni → Dati e mercati → "Pubblica le
   pagine". Da quel momento sono visibili a tutti.
6. Facoltativo, newsletter: nello stesso pannello, "Modulo di iscrizione al
   bollettino", incollare l'indirizzo di invio del modulo del servizio
   scelto (Brevo, Mailchimp, MailerLite). Compare il riquadro di iscrizione.

## Come è fatta la sezione

- Una sola riga di shortcode per pagina: `[dati_mercati prodotto="orata"]`
  (il plugin le scrive da solo). La lingua inglese usa `lingua="en"`.
- Il plugin inserisce nella pagina un blocco HTML con il proprio CSS e il
  proprio JavaScript, tutto racchiuso in `.pir-mercati`. Ogni classe inizia
  con `pir-`: non tocca nulla del tema e il tema non dovrebbe toccare lui.
- Il carattere è Manrope, caricato dalla sezione stessa da Google Fonts.
- I colori sono quelli dei marchi: `#1F8DCC` (blu del logo Pesceinrete e
  di IGB) per le azioni, `#003757` (navy del menu IGB) per l'eroe e i
  titoli, `#E6F6FF` (fondo IGB) per il fondo. Non vengono dal tema.
- Il logo Pesceinrete compare in testa alla sezione **solo fuori dal
  sito**; dentro WordPress il plugin lo toglie, perché lo mostra già
  l'intestazione del tema.
- Il modello di pagina deve essere **a larghezza piena**: i grafici hanno
  bisogno di almeno 900 px.

## Regolazioni

Nel CSS del tema figlio, se serve:

```css
/* colori: solo se i marchi cambiano */
.pir-mercati{ --azzurro:#1F8DCC; --navy:#003757; --cielo:#E6F6FF; }

/* se il tema aggiunge margini o un contenitore stretto attorno al contenuto */
.page-id-XXX .entry-content{ max-width:none; padding:0; }
```

Il sito ha una versione inglese con WPML: le pagine `/market-data/` sono
già create dal plugin; se WPML chiede di collegarle come traduzioni di
quelle italiane, farlo dal pannello di WPML. Lo shortcode non cambia.

## Che cosa non fare

- Non modificare `dati-mercati.html` dentro il plugin: viene rigenerato dal
  repository. Le modifiche di stile si fanno nel CSS del tema figlio con le
  classi `pir-`, oppure nel progetto (`web/src/stile.css`) seguito da
  `python strumenti/componi_pagina.py`.
- Non copiare i file dei dati via FTP se l'indirizzo di GitHub Pages è
  configurato: si aggiornano da soli.
- Non cambiare gli slug delle pagine: i collegamenti fra specie, le
  anteprime per la condivisione e gli `hreflang` li usano.
- Non caricare il progetto (lo zip grande) su WordPress: va su GitHub.

## Se qualcosa non va

**La pagina è vuota.** Il tema figlio non è attivo o il plugin è
disattivato. Verificare in Plugin.

**I grafici non si vedono ma il testo sì.** Un plugin di cache o di
ottimizzazione rinvia o accorpa il JavaScript: escludere le pagine della
sezione da quel plugin (opzione "escludi pagine" in WP Rocket, LiteSpeed,
Autoptimize). Oppure il modello non è a larghezza piena.

**La fascia gialla "Dati dimostrativi" resta.** Il passo 1 su GitHub non è
completato, oppure l'indirizzo delle impostazioni non finisce con una
barra. Nel pannello del plugin c'è il pulsante "Svuota la cache".

**Il carattere non è Manrope.** Un plugin di privacy blocca Google Fonts.
Si può servire Manrope dal tema: il file è in `risorse/font/` del progetto,
con la sua licenza OFL; basta un `@font-face` nel CSS del tema figlio e
`.pir-mercati{--testo:'Manrope';--titoli:'Manrope'}`.

Per tutto il resto: il messaggio d'errore esatto, e si risolve.
