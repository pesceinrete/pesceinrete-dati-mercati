# Scelte di design

## Chi legge e cosa deve ottenere

Un responsabile acquisti con il fornitore al telefono, un importatore che
decide se comprare adesso, un trasformatore che deve sapere se la materia
prima regge il prezzo già venduto. Leggono di fretta, spesso da telefono.
La pagina risponde a due domande, in quest'ordine: il prezzo di adesso è
normale per questo periodo dell'anno? che cosa diventa quel prezzo sul
prodotto che compro io?

## I colori sono quelli dei marchi

`#1F8DCC` è il blu del logo Pesceinrete (la "IN") e del quadrato IGB: lo
stesso colore sui due siti. È il colore di ogni azione: chip attivo,
pulsanti, marcatore sul grafico, linea dell'anno in corso. `#003757` è il
navy del menu di IGB: l'eroe, i riquadri di richiamo, i titoli. `#E6F6FF`
è il fondo delle pagine IGB: il fondo della sezione. Il bianco è delle
schede. Nessun altro colore, salvo l'ocra dell'avviso sui dati
dimostrativi e le due tinte della posizione stagionale.

In testa alla sezione c'è il logo Pesceinrete vero, in SVG, su bianco come
sul sito; nel riquadro che porta ai fornitori c'è il logo Ittico Guida
Buyer vero, su navy, con il pulsante azzurro identico ad "Accedi".

## Il sistema

Manrope come unico carattere, in cinque pesi. Una scala tipografica fissa
(12 · 13 · 15 · 16 · 20 · 25 · 32 · 40 · 72) e una scala di spazi su 8
pixel. Raggi fissi: 12 per l'eroe come il banner IGB, 14 per le schede, 8
per i comandi, 999 per i chip. Un'ombra sola. Quando tutto deriva da poche
regole l'occhio lo sente anche senza saperlo dire.

## La composizione

Una testata bianca con il logo, la sezione e la settimana. Sotto, l'eroe
navy: i chip delle specie con il prezzo accanto; a sinistra il nome della
specie a 40 px, il prezzo a 72 px, le tre tessere delle variazioni, la
lettura al netto del livello, il paragrafo della redazione, la firma; a
destra il grafico della stagione in una scheda bianca. In fondo all'eroe
il controllo a due segmenti "In breve / Analisi completa".

Poi, su fondo cielo, le schede bianche: la panoramica di tutte le specie,
la sintesi e la tabella, l'iscrizione al bollettino quando è configurata,
il ponte verso IGB, la settimana in breve con l'invito all'analisi
completa, e le sezioni dell'approfondimento.

## La voce

Il paragrafo di apertura è scritto frase per frase in base a quello che è
successo: un prezzo fermo si dice fermo, un rialzo piccolo si dice
leggero, la stagione entra solo se ha qualcosa da dire. Le formulazioni
cambiano a settimane alterne. Con gli articoli giusti — "dell'8%", "del
96%", "dalla Grecia", "dal Marocco" — che è il punto in cui i testi
generati tradiscono se stessi.

## Il grafico

Niente legenda: le etichette stanno sulle linee. Il punto della settimana
porta prezzo e anno; la linea dell'anno scorso è grigia con l'anno in
fondo; la fascia dei cinque anni ha la sua etichetta. Le note della
redazione sono marcatori numerati, con il testo sotto. Tre linee di
griglia, i mesi sull'asse.

## Perché i delta non sono colorati

In borsa il verde è salita e il rosso discesa, ma qui il lettore può
essere chi compra o chi vende: un rialzo è buono per uno e pessimo per
l'altro. Colorarli suggerirebbe un giudizio che non ci compete. La
posizione stagionale invece è un fatto statistico, e su quello le due
tinte aiutano.

## Due viste, non tre

La pagina si apre in breve. L'analisi completa è a un clic, con un indice
delle sezioni e un invito in fondo alla vista breve che dice cosa
contiene. La scelta viene ricordata dal browser e sta nell'indirizzo. Le
sezioni nascoste restano nel documento: contano per l'indicizzazione e
per chi legge senza script.

## Il bordo tratteggiato

Il calcolatore del costo a destino ha un bordo tratteggiato mentre tutti
gli altri riquadri ce l'hanno pieno. È l'unica differenza formale che
porta un significato: pieno vuol dire dato di fonte, tratteggiato vuol
dire simulazione sui parametri di chi legge.

## Fuori dalla pagina

La card di condivisione per WhatsApp e LinkedIn, la newsletter del
giovedì e lo stile di stampa seguono gli stessi colori e lo stesso
carattere. Un prodotto si gioca metà della reputazione dove non è il suo
sito.

## Movimento

Uno solo: la linea dell'anno in corso si disegna all'apertura, una volta.
Tutto il resto si muove solo in risposta a un'azione. Con
`prefers-reduced-motion` non si muove niente.
