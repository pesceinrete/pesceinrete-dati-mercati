# Fonti per specie

Criterio, nell'ordine: ente statistico o pubblico; frequenza settimanale
per il prezzo, mensile per i flussi; licenza che consente la
ripubblicazione o conferma scritta; acquisizione automatizzabile.

Un principio vale per tutte le specie: **il prezzo di riferimento e i
flussi sono due fonti distinte** e restano separati in pagina. Il prezzo
dice quanto costa il prodotto sul mercato dove si forma; i flussi dicono
quanto ne entra in Italia e da dove. Nessuna delle due da sola risponde a
chi compra.

## Il quadro

| Specie | Prezzo settimanale | Fonte | Flussi mensili (Comext, codici NC) | Provenienze seguite |
|---|---|---|---|---|
| Salmone atlantico | Prezzo medio all'esportazione dalla Norvegia, fresco | SSB 03024 | 03021411, 03021419 | Norvegia, Danimarca |
| Orata | Quotazione all'ingrosso, allevamento 400-600 g | RNM Rungis | 03028530 | Grecia, Turchia, Croazia |
| Spigola | Quotazione all'ingrosso, allevamento 400-600 g | RNM Rungis | 03028410 | Grecia, Turchia, Croazia |
| Polpo | Quotazione all'ingrosso, marocchino congelato | RNM Rungis | 03075100, 03075200 | Marocco, Mauritania, Spagna |
| Gambero | Quotazione all'ingrosso, congelato | RNM Rungis | 03061792, 03061799 | Ecuador, Argentina, India, Spagna |
| Merluzzo | Quotazione all'ingrosso, fresco | RNM Rungis | 03025110, 03036310, 03056200 | Norvegia, Islanda, Danimarca |
| Tonno pinna gialla | Quotazione all'ingrosso, lombo fresco | RNM Rungis | 03023210, 03023290, 03034220, 03034290 | Spagna, Francia, Vietnam |
| Pesce spada | Quotazione all'ingrosso, fresco | RNM Rungis | 03024700, 03035700 | Spagna, Vietnam, Cile |
| Cozze | Prezzo all'ingrosso sui mercati ittici italiani | BMTI | 03073110 | Spagna, Grecia, Francia |
| Vongole | Prezzo all'ingrosso sui mercati ittici italiani | BMTI | 03077100 | Spagna, Francia |

Più il cambio BCE NOK/EUR per leggere il salmone in euro.

## Perché queste e non altre

**Statistics Norway per il salmone.** È l'unica fonte pubblica, settimanale,
con licenza aperta (CC BY 4.0) e API documentata. Non è l'indice
contrattuale — quello è SISALMONI, a pagamento e non ripubblicabile — e la
pagina lo dice. Come riferimento di andamento è il migliore disponibile.

**RNM Rungis per il pesce fresco e congelato di importazione.** In Italia
non esiste una rilevazione pubblica settimanale per orata, spigola, polpo,
gambero, merluzzo, tonno e pesce spada. FranceAgriMer rileva ogni giorno a
Rungis, il più grande mercato all'ingrosso d'Europa, con conjoncturisti
pubblici e procedura certificata, su circa 300 prodotti ittici definiti
per specie, origine, presentazione e calibro. È un prezzo francese, e la
pagina lo dichiara: ma segue lo stesso prodotto greco, turco, marocchino,
ecuadoriano che arriva in Italia, e per un compratore italiano un
riferimento continuo e documentato su un mercato vicino vale più
dell'assenza di qualsiasi riferimento.

**BMTI per cozze e vongole.** Sono prodotti in gran parte nazionali: un
prezzo estero non direbbe niente. La Borsa Merci Telematica Italiana
rileva i prezzi all'ingrosso sui mercati ittici italiani per conto delle
Camere di commercio. È l'unica fonte pubblica italiana con cadenza
settimanale.

**Eurostat Comext per i flussi, sempre.** È la fonte ufficiale del
commercio estero, gratuita, con API, e permette di distinguere le
provenienze con i codici della nomenclatura combinata. Due avvertenze che
la pagina riporta: il valore in dogana comprende il trasporto fino alla
frontiera e non è il prezzo pagato da nessuno; lo Stato membro che
registra l'importazione è spesso il punto di ingresso doganale, non la
destinazione finale.

## Che cosa è automatico oggi e che cosa manca

| Fonte | Stato | Che cosa serve |
|---|---|---|
| SSB | Automatica, parser verificato sulla risposta reale della PxWebApi v2 (ottobre 2026) | niente |
| BCE | Automatica | niente |
| Eurostat Comext | Automatica per tutte le 39 serie, parser verificato sulla risposta reale di DS-045409 | niente |
| RNM Rungis | Automatica; indirizzi delle pagine prodotto e diciture reali già in `config/rnm.json`, da confermare alla prima esecuzione | una mail a FranceAgriMer per il riuso |
| BMTI | Modulo pronto, da file esportato | conferma scritta sul riuso; poi si valuta l'automazione |
| EUMOFA import UE settimanali | Modulo pronto, da file esportato | conferma scritta sul riuso |

Finché una fonte di prezzo non è collegata, la specie resta in pagina con
dati dimostrativi e la fascia rossa in cima. Non è un difetto da
nascondere: è la ragione per cui il primo lavoro dopo l'installazione è
`./gestisci controlla`.

## I codici doganali vanno riverificati ogni gennaio

La nomenclatura combinata cambia ogni anno. I codici nel registro sono
quelli in vigore per quanto si è potuto verificare; una serie che da
gennaio restituisce zero quantità è il segnale che il codice è cambiato.
Il cruscotto della redazione lo mostra come "in ritardo".

## Quello che non facciamo

Un prezzo italiano raccolto dagli operatori. Sarebbe l'informazione più
preziosa, ed è quella che espone Pesceinrete e i contributori al problema
dello scambio di informazioni fra concorrenti. Se un giorno si vorrà fare,
va impostato con un legale: aggregazione, anonimato, ritardo di
pubblicazione. Non dopo.
