# Le fonti, specie per specie

Aggiornato il 21 novembre 2026, dopo la revisione completa delle fonti.

## La regola

Una serie entra in pagina solo se regge a quattro domande:

1. **È ufficiale?** Ente statistico o istituzione pubblica.
2. **È libera?** Riuso dichiarato dalla fonte, senza permessi da chiedere.
3. **È automatica?** Si scarica da un indirizzo pubblico, senza aggirare blocchi.
4. **Si legge?** Misurata sui dati veri: il prezzo da una settimana
   all'altra deve muoversi come un mercato, non saltare con il mix dei
   carichi. Soglia pratica: variazione settimanale tipica sotto il 6%.

## Che cos'è il prezzo delle specie importate

Per tutte le specie tranne il salmone il prezzo è il **valore medio
dichiarato in dogana** da chi importa in Italia da paesi extra-UE, per
provenienza: valore diviso peso netto. La fonte è EUMOFA, l'osservatorio
della Commissione europea, che pubblica ogni settimana le dichiarazioni
doganali di tutti gli Stati membri.

* È un censimento di tutte le dichiarazioni, non un campione.
* Non è una quotazione né un listino. Serve per confrontare il proprio
  prezzo d'acquisto con la media e per leggere l'andamento.
* Esce con circa due settimane di ritardo: l'ultima settimana è sempre
  incompleta alla fonte e viene pubblicata solo quando è chiusa.
* Copre solo gli arrivi da fuori Unione. Grecia, Croazia e Spagna stanno
  nel dato mensile Eurostat, nel riquadro "Arrivi in Italia".
* I totali annui coincidono con quelli ufficiali di Eurostat per l'Italia
  (verificato sul 2025 per orata, spigola, polpo e gambero).

## Le nove specie

Variazione tipica = mediana della variazione assoluta del prezzo da una
settimana all'altra, misurata su 2023, 2024, 2025 e 2026.

| Specie | Prezzo in copertina | Variazione tipica | Altre provenienze (media a 4 settimane) |
|---|---|---|---|
| Salmone | Esportazione dalla Norvegia, SSB | n.d. (fonte diversa) | n.d. |
| Orata | Fresca dalla Turchia | 0,7% - 1,9% | Albania, Tunisia |
| Spigola | Fresca dalla Turchia | 0,9% - 1,1% | n.d. |
| Gambero | Congelato dall'Ecuador | 2,8% - 5,1% | Argentina, India |
| Polpo | Dal Marocco | 3,3% - 5,9% | Senegal, Mauritania |
| Calamaro | Loligo vulgaris congelato, tutte le provenienze (94% Marocco) | 4,7% - 6,0% | Marocco |
| Seppia | Congelata, tutte le provenienze, **media a 4 settimane** | 5,1% - 6,6% sulla singola settimana | Senegal, Marocco, Tunisia |
| Astice | Vivo, tutte le provenienze (Stati Uniti e Canada) | 1,9% - 3,3% | Stati Uniti, Canada |
| Pesce spada | Filetti e lombi freschi, tutte le provenienze | 1,6% - 4,3% | Sri Lanka, Cile |

Per la seppia il prezzo pubblicato è la media delle ultime quattro
settimane pesata sui volumi: la singola settimana è al limite della soglia.

## Specie misurate e lasciate fuori

| Specie | Cosa è stato misurato | Perché è fuori |
|---|---|---|
| Tonno pinna gialla congelato | Variazione tipica 14% - 26% | È soprattutto prodotto per conserva, in carichi irregolari |
| Filetti di tonno congelati | 15% - 18% | Mix di qualità molto diverse |
| Merluzzo, filetti congelati | 8% - 18%, 26-40 settimane su 52 | Volumi piccoli verso l'Italia, arrivi radi |
| Pesce spada congelato | 12,5% | Carichi irregolari; resta nel dato mensile |
| Cozze | 9 settimane su 46 con dati | Prodotto nazionale e UE: quasi nessun arrivo extra-UE |
| Vongole | 558 tonnellate in un anno | Come sopra |

Possono rientrare in una seconda fase come schede mensili (Eurostat), con
la cadenza dichiarata, oppure con un prezzo a media mobile se la misura lo
giustifica.

## Limiti noti della fonte settimanale

* **Storico corto e con buchi.** Si carica dal 2023. Nel 2023 e nel 2024
  la fonte ha alcune settimane quasi vuote, quasi tutte a cavallo di fine
  mese (2023: 13, 22, 26, 35, 44, 48; 2024: 5, 9, 22, 31, 35, 44). Il
  sistema le scarta e lascia il buco. Il 2025 è completo. Il confronto
  stagionale dichiara quanti anni usa.
* **Revisioni.** La fonte riscrive anche gli anni passati e consolida i
  dati dopo 36 mesi. Ogni revisione è registrata in archivio.
* **Indirizzo dei file.** È pubblico e fisso, ma contiene "dev": la fonte
  può spostarlo. Se succede la pagina resta sull'ultima settimana valida e
  l'errore compare nel resoconto (vedi docs/SENZA-TERMINALE.md).
* **Luogo di sdoganamento.** "Italia" è lo Stato in cui la merce è
  sdoganata. Il salmone, sdoganato altrove, in questo file per l'Italia
  non c'è: per questo resta sulla fonte norvegese.

## Codici doganali

| Specie | Prezzo settimanale (EUMOFA) | Arrivi mensili (Eurostat) |
|---|---|---|
| Salmone | n.d. | 03021400 |
| Orata | 03028530 | 03028530 |
| Spigola | 03028410 | 03028410 |
| Gambero | 03061792, 03061799 | 03061792, 03061799 |
| Polpo | 03075100, 03075200 | 03075100, 03075200 |
| Calamaro | 03074331 | 03074331, 03074333, 03074335, 03074338 |
| Seppia | 03074329 | 03074329 |
| Astice | 03063210 | 03063210 |
| Pesce spada | 03044500 | 03024700, 03044500, 03035700 |

Tutti i codici sono stati riscontrati nel file EUMOFA 2026. Vanno
riverificati a ogni gennaio: la nomenclatura combinata cambia.
