/* Collaudo della pagina in DOM simulato.
 *
 * Verifica che la pagina si apra senza errori, che i numeri scritti
 * coincidano con quelli calcolati dal pipeline Python e che i comandi
 * (misura, finestra, date, confronto, calcolatore) producano il
 * risultato atteso.
 */
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const radice = path.resolve(__dirname, "..");
const lingua = process.env.LINGUA === "en" ? "en" : "it";
const suffisso = lingua === "en" ? ".en" : "";
const pagina = path.join(radice, "web/anteprima-dati-mercati" + suffisso + ".html");
const dati = JSON.parse(fs.readFileSync(path.join(radice, "web/data/mercati" + suffisso + ".json"), "utf8"));
const dettaglio = JSON.parse(
  fs.readFileSync(path.join(radice, "web/data/prodotti/salmone" + suffisso + ".json"), "utf8")
);

let errori = [];
const console_virtuale = new VirtualConsole();
console_virtuale.on("jsdomError", (e) => errori.push(e.message));
console_virtuale.on("error", (e) => errori.push(String(e)));

const dom = new JSDOM(fs.readFileSync(pagina, "utf8"), {
  runScripts: "dangerously",
  virtualConsole: console_virtuale,
  pretendToBeVisual: true,
  url: "https://www.pesceinrete.com/dati-mercati/",
});

const doc = dom.window.document;
const prodotto = dettaglio;
let falliti = 0;

function verifica(nome, condizione, dettaglio) {
  if (condizione) {
    console.log("  ok    " + nome);
  } else {
    falliti++;
    console.log("  FALLITO " + nome + (dettaglio ? " -> " + dettaglio : ""));
  }
}

function testo(id) {
  const elemento = doc.getElementById(id);
  return elemento ? elemento.textContent.trim() : "";
}

setTimeout(() => {
  console.log("\nApertura della pagina");
  verifica("nessun errore di esecuzione", errori.length === 0, errori.join(" | "));
  verifica(
    "prezzo in apertura",
    testo("pir-prezzo").startsWith(
      lingua === "en" ? prodotto.prezzo_eur_kg.toFixed(2) : prodotto.prezzo_eur_kg.toFixed(2).replace(".", ",")
    ),
    testo("pir-prezzo")
  );
  verifica("settimana pubblicata", testo("pir-settimana").includes(prodotto.ultimo_periodo.slice(6)));
  verifica("lettura stagionale", testo("pir-badge") === prodotto.stagionale.lettura);
  verifica(
    "verdetto stagionale come etichetta",
    /Sopra la norma|Sotto la norma|Nella norma|Storico corto|Above normal|Below normal|Normal|Short history/.test(
      doc.getElementById("pir-badge").getAttribute("data-verdetto") || ""
    ),
    doc.getElementById("pir-badge").getAttribute("data-verdetto")
  );
  verifica("tre delta in una riga", (testo("pir-delta").match(/%/g) || []).length === 3, testo("pir-delta"));
  verifica("lede redazionale presente", testo("pir-lede").length > 120 && /\d/.test(testo("pir-lede")));
  verifica("firma e data", /settimana|week/i.test(testo("pir-firma")));
  // La settimana attesa si ricava dai dati, non è fissa: vale per i dati dimostrativi e per quelli veri.
  const numeroSettimana = String(parseInt(prodotto.ultimo_periodo.slice(6), 10));
  verifica(
    "testatina con la settimana",
    new RegExp("(settimana|week) " + numeroSettimana + "\\b", "i").test(testo("pir-quando")),
    testo("pir-quando")
  );
  verifica("ponte verso IGB con la specie", /salmone|salmon/i.test(testo("pir-igb-titolo")) && doc.getElementById("pir-igb-link").href.indexOf("igb.pesceinrete.com") > -1);

  console.log("\nFascia di stato");
  verifica(
    "i dati dimostrativi sono dichiarati",
    dati.stato !== "dimostrativo" || testo("pir-stato").includes(lingua === "en" ? "Demo data" : "dimostrativi"),
    testo("pir-stato").slice(0, 60)
  );

  console.log("\nGrafici");
  const banda = doc.querySelectorAll("#pir-banda svg path");
  verifica("banda, anno scorso e anno in corso disegnati", banda.length >= 3, banda.length + " tracciati");
  verifica("etichette dirette sul grafico, niente legenda",
    doc.querySelectorAll("#pir-banda svg text").length >= 8 && doc.querySelectorAll(".pir-legenda").length === 0);
  verifica("punto finale evidenziato", doc.querySelectorAll("#pir-banda svg circle[r='5.5']").length === 1);
  verifica("serie storica disegnata", doc.querySelectorAll("#pir-storico svg").length === 1);
  verifica(
    "finestra iniziale a 52 settimane",
    testo("pir-storico-testo").startsWith(lingua === "en" ? "52 weeks" : "52 settimane"),
    testo("pir-storico-testo").slice(0, 40)
  );

  console.log("\nComandi");
  doc.querySelector('[data-misura="tonnellate"]').dispatchEvent(new dom.window.Event("click"));
  verifica(
    "passaggio al volume",
    testo("pir-storico-testo").includes(lingua === "en" ? "Total volume" : "Volume complessivo"),
    testo("pir-storico-testo").slice(0, 60)
  );
  verifica("il volume si disegna a barre", doc.querySelectorAll("#pir-storico svg rect").length > 40);

  doc.querySelector('[data-misura="eur"]').dispatchEvent(new dom.window.Event("click"));
  doc.querySelector('[data-finestra="13"]').dispatchEvent(new dom.window.Event("click"));
  verifica(
    "finestra a 3 mesi",
    testo("pir-storico-testo").startsWith(lingua === "en" ? "13 weeks" : "13 settimane"),
    testo("pir-storico-testo").slice(0, 30)
  );

  console.log("\nDate esatte");
  const campoDal = doc.getElementById("pir-dal");
  const campoAl = doc.getElementById("pir-al");
  campoDal.value = "2026-01-05";
  campoAl.value = "2026-03-01";
  campoDal.dispatchEvent(new dom.window.Event("change"));
  verifica(
    "intervallo scelto a mano",
    testo("pir-storico-testo").startsWith(lingua === "en" ? "8 weeks" : "8 settimane"),
    testo("pir-storico-testo").slice(0, 30)
  );

  console.log("\nConfronto fra periodi");
  const tabella = doc.getElementById("pir-tabella-confronto").textContent;
  verifica("prezzo medio ponderato in tabella", tabella.includes(lingua === "en" ? "Weighted average price" : "Prezzo medio ponderato"));
  verifica("valore ricostruito etichettato", tabella.includes(lingua === "en" ? "Reconstructed value" : "Valore ricostruito"));
  verifica(
    "avvertenza sulla circolarità del valore",
    doc.getElementById("pir-tabella-confronto").textContent.includes(lingua === "en" ? "multiplied" : "moltiplicata")
  );

  // periodo disomogeneo: 8 settimane contro 3 scelte a mano
  doc.querySelector('[data-paragone="libero"]').dispatchEvent(new dom.window.Event("click"));
  doc.getElementById("pir-rif-dal").value = "2025-01-06";
  doc.getElementById("pir-rif-al").value = "2025-01-26";
  doc.getElementById("pir-rif-dal").dispatchEvent(new dom.window.Event("change"));
  const disomogeneo = doc.getElementById("pir-tabella-confronto").textContent;
  verifica("periodi disomogenei segnalati", disomogeneo.includes(lingua === "en" ? "different number of complete weeks" : "numero diverso di settimane"));

  console.log("\nCalcolatore del costo a destino");
  doc.getElementById("pir-base").value = "7";
  doc.getElementById("pir-trasporto").value = "0.5";
  doc.getElementById("pir-glassatura").value = "10";
  doc.getElementById("pir-resa").value = "75";
  doc.getElementById("pir-resa").dispatchEvent(new dom.window.Event("input"));
  verifica(
    "7,00 + 0,50 con glassatura 10% e resa 75% fa 11,11",
    testo("pir-esito-utile").startsWith(lingua === "en" ? "11.11" : "11,11"),
    testo("pir-esito-utile")
  );
  verifica("passaggi mostrati", doc.querySelectorAll("#pir-passi li").length >= 4);

  console.log("\nMetodo e dati strutturati");
  verifica("perimetro descritto", testo("pir-perimetro").length > 120);
  verifica("fonte e licenza esposte", testo("pir-provenienza").includes(prodotto.serie.licenza));
  const schema = JSON.parse(doc.getElementById("pir-schema").textContent);
  verifica("schema.org Dataset", schema["@type"] === "Dataset" && !!schema.license);
  verifica("copertura temporale dichiarata", /\d{4}\/\d{4}/.test(schema.temporalCoverage));

  console.log("\nSintesi statica, flussi e bollettino");
  const sintesi = doc.getElementById("pir-sintesi-statica");
  verifica("blocco statico presente nella pagina", sintesi && sintesi.textContent.length > 200);
  verifica(
    "la tabella statica ha dodici settimane",
    sintesi && sintesi.querySelectorAll("table:not(.pir-provenienze) tbody tr").length === 12,
    sintesi ? sintesi.querySelectorAll("table:not(.pir-provenienze) tbody tr").length + " righe" : "assente"
  );
  verifica(
    "le domande frequenti sono testo, non script",
    sintesi && sintesi.querySelectorAll("dt").length >= 2
  );

  const flussi = doc.getElementById("flussi");
  const conFlussi = !!(dettaglio.flussi && Object.keys(dettaglio.flussi).length);
  if (!conFlussi) {
    console.log("  --    flussi non presenti per questa specie: controlli saltati");
  } else {
  verifica("sezione flussi mostrata quando la serie esiste", !flussi.hidden);
  verifica(
    "totale mobile a dodici mesi",
    testo("pir-flussi-quantita").indexOf(lingua === "en" ? "tonnes" : "tonnellate") > -1,
    testo("pir-flussi-quantita")
  );
  verifica(
    "valore unitario non spacciato per prezzo",
    testo("pir-flussi-valore-nota").indexOf(lingua === "en" ? "Not a purchase price" : "Non è un prezzo di acquisto") > -1
  );
  verifica("grafico mensile a barre", doc.querySelectorAll("#pir-flussi-grafico rect").length > 12);
  }

  const voci = doc.getElementById("pir-voci").textContent;
  verifica("bollettino scritto", voci.length > 60, voci.slice(0, 50));
  verifica(
    "il bollettino non attribuisce cause",
    !/a causa di|perché la domanda|dovuto a/i.test(voci)
  );

  console.log("\nPiù specie");
  const selettore = doc.getElementById("pir-prodotti");
  const altra = dati.prodotti.find((p) => p.id === "orata") ? "orata" : null;
  if (dati.prodotti.length < 2) {
    console.log("  --    una sola specie con dati: controlli del selettore saltati");
  } else {
  verifica("selettore visibile con tutte le specie", !selettore.hidden && selettore.querySelectorAll("[data-prodotto]").length === dati.prodotti.length,
    selettore.querySelectorAll("[data-prodotto]").length + " voci");
  verifica("ogni voce mostra il prezzo", selettore.querySelectorAll(".pir-selettore-prezzo").length === dati.prodotti.length);
  if (conFlussi) verifica("provenienze elencate negli arrivi", doc.querySelectorAll(".pir-provenienze li").length >= 2);
  }
  if (altra) {
  const bottoneOrata = selettore.querySelector('[data-prodotto="orata"]');
  bottoneOrata.dispatchEvent(new dom.window.Event("click"));
  verifica("cambio specie: titolo aggiornato", /Orata|sea bream/i.test(testo("pir-nome-prodotto")), testo("pir-nome-prodotto"));
  verifica("cambio specie: sintesi statica sostituita", /Orata|sea bream/i.test(doc.getElementById("pir-sintesi-statica").textContent));
  verifica("serie in euro: bottone valuta nascosto", doc.getElementById("pir-bottone-origine").hidden === true);
  verifica("serie doganale con volumi: bottone volume visibile", doc.querySelector('[data-misura="tonnellate"]').hidden === false);
  verifica("l'indirizzo segue la specie", /p=orata/.test(dom.window.location.hash));
  const tabellaPrezzi = doc.querySelector("#pir-sintesi-statica table.pir-tabella:not(.pir-provenienze)");
  verifica("serie in euro: settimana, prezzo e tonnellate, senza la colonna in valuta d'origine",
    tabellaPrezzi && tabellaPrezzi.querySelectorAll("thead th").length === 3,
    tabellaPrezzi ? tabellaPrezzi.querySelectorAll("thead th").length + " colonne" : "assente");
  const tabellaProvenienze = doc.querySelector("#pir-sintesi-statica table.pir-provenienze");
  verifica("provenienze extra-UE a confronto: tabella presente con il totale",
    tabellaProvenienze && tabellaProvenienze.querySelectorAll("tbody tr").length >= 2 &&
    tabellaProvenienze.querySelectorAll("tr.pir-totale").length === 1,
    tabellaProvenienze ? tabellaProvenienze.querySelectorAll("tbody tr").length + " righe" : "assente");
  verifica("nessun riferimento a Rungis o BMTI in pagina",
    !/rungis|bmti/i.test(doc.body.textContent));
  selettore.querySelector('[data-prodotto="salmone"]').dispatchEvent(new dom.window.Event("click"));
  verifica("ritorno al salmone: bottone volume visibile", doc.querySelector('[data-misura="tonnellate"]').hidden === false);
  } else if (dati.prodotti.length >= 2) {
    console.log("  --    orata senza dati: controlli del cambio specie saltati");
  }

  console.log("\nPanoramica, azioni, telefono");
  if (dati.prodotti.length >= 2) {
  verifica("panoramica con una riga per specie", doc.querySelectorAll("#pir-tabella-panoramica tbody tr").length === dati.prodotti.length);
  verifica("posizione stagionale etichettata in panoramica", doc.querySelectorAll("#pir-tabella-panoramica .pir-posizione").length === dati.prodotti.length);
  verifica("select per il telefono con tutte le specie", doc.querySelectorAll("#pir-select-prodotto option").length === dati.prodotti.length);
  } else {
    console.log("  --    una sola specie: panoramica e menu del telefono non servono, controlli saltati");
  }
  verifica("azioni sul grafico presenti", doc.getElementById("pir-scarica-grafico") !== null && doc.getElementById("pir-copia-link") !== null);
  doc.getElementById("pir-copia-link").dispatchEvent(new dom.window.Event("click"));
  verifica("copia link risponde", testo("pir-azioni-esito").length > 0, testo("pir-azioni-esito").slice(0, 40));

  console.log("\nVista essenziale e completa");
  const radice = doc.querySelector(".pir-mercati");
  verifica("si parte dalla vista essenziale", radice.getAttribute("data-vista") === "essenziale");
  verifica(
    "le sezioni di lavoro restano nel documento anche se nascoste",
    doc.querySelectorAll('[data-livello="2"]').length === 5
  );
  verifica(
    "il menu nasconde le voci non disponibili",
    doc.querySelector('.pir-nav a[href="#costo"]').hidden === true
  );
  doc.querySelector('button[data-vista="completa"]').dispatchEvent(new dom.window.Event("click"));
  verifica("passaggio alla vista completa", radice.getAttribute("data-vista") === "completa");
  verifica("la vista è nell'indirizzo", /v=completa/.test(dom.window.location.hash));
  verifica(
    "il menu torna completo",
    doc.querySelector('.pir-nav a[href="#costo"]').hidden === false
  );

  console.log("\nStato nell'indirizzo");
  verifica(
    "l'indirizzo riflette la vista",
    /p=salmone/.test(dom.window.location.hash) && /dal=\d{4}-W/.test(dom.window.location.hash),
    dom.window.location.hash
  );

  if (lingua === "en") {
    console.log("\nEnglish text");
    const visibile = doc.querySelector(".pir-mercati").textContent;
    const spie = /\b(settimana|settimane|prezzo|periodo|tonnellate|della|delle|degli|nella|sulla|fonte|metodo|perché|più|già|può)\b/i;
    const trovato = visibile.match(spie);
    verifica("no Italian words in rendered text", !trovato, trovato ? trovato[0] : "");
    verifica("numbers use the English decimal point", /\d\.\d\d €\/kg|€\d+\.\d\d/.test(visibile));
    verifica("html lang is en", doc.documentElement.getAttribute("lang") === "en");
  }

  console.log("\nAccessibilita' minima");
  verifica("un solo h1", doc.querySelectorAll("h1").length === 1);
  verifica(
    "grafici con descrizione testuale",
    doc.querySelectorAll('[role="img"][aria-labelledby]').length === 3
  );
  verifica(
    "gruppi di comandi con stato",
    doc.querySelectorAll("[aria-pressed]").length >= 9
  );

  // Seconda apertura: il browser ricorda "Analisi completa" da una visita
  // precedente. La pagina deve comunque disegnare tutto.
  console.log("\nRiapertura con la vista completa in memoria");
  const errori2 = [];
  const vc2 = new VirtualConsole();
  vc2.on("jsdomError", (e) => errori2.push(e.message));
  const dom2 = new JSDOM(fs.readFileSync(pagina, "utf8"), {
    runScripts: "dangerously", virtualConsole: vc2, pretendToBeVisual: true,
    url: "https://www.pesceinrete.com/dati-mercati/",
    beforeParse(window) { try {
      window.localStorage.setItem("pir-vista", "completa");
      window.localStorage.setItem("pir-visita-salmone", JSON.stringify({ periodo: "2026-W36", prezzo: 6.42 }));
    } catch (e) {} },
  });
  setTimeout(() => {
    const d2 = dom2.window.document;
    verifica("nessun errore alla riapertura", errori2.length === 0, errori2.join(" | "));
    verifica("si apre direttamente in vista completa", d2.querySelector(".pir-mercati").getAttribute("data-vista") === "completa");
    verifica("prezzo disegnato anche alla riapertura", /\d/.test(d2.getElementById("pir-prezzo").textContent));
    verifica("grafico della stagione disegnato anche alla riapertura", d2.querySelectorAll("#pir-banda svg path").length >= 3);
    verifica("storico disegnato in vista completa", d2.querySelectorAll("#pir-storico svg").length === 1);
    if ((prodotto.annotazioni || []).length) {
      verifica("nota della redazione marcata sul grafico", d2.querySelectorAll("#pir-note-banda li").length >= 1 && d2.querySelectorAll("#pir-banda svg circle").length >= 2);
    } else {
      console.log("  --    nessuna nota della redazione: controllo saltato");
    }
    verifica("riga 'dalla tua ultima visita' con la variazione", d2.getElementById("pir-ultima-visita").hidden === false && /%/.test(d2.getElementById("pir-ultima-visita").textContent), d2.getElementById("pir-ultima-visita").textContent);
    // Terza apertura: dentro il sito, con le pagine delle specie a indirizzi
    // reali diversi dallo schema previsto, e solo due pagine pubblicate.
    console.log("\nDentro il sito, con due sole pagine pubblicate");
    const errori3 = [];
    const vc3 = new VirtualConsole();
    vc3.on("jsdomError", (e) => errori3.push(e.message));
    const dom3 = new JSDOM(fs.readFileSync(pagina, "utf8"), {
      runScripts: "dangerously", virtualConsole: vc3, pretendToBeVisual: true,
      url: "https://www.pesceinrete.com/dati-mercati/",
      beforeParse(window) {
        window.PESCEINRETE_PRODOTTO = "salmone";
        window.PESCEINRETE_URL_PRODOTTO = "https://www.pesceinrete.com/dati-mercati/{id}/";
        window.PESCEINRETE_URL_PRODOTTI = {
          salmone: "https://www.pesceinrete.com/salmone/",
          orata: "https://www.pesceinrete.com/orata-2/",
        };
      },
    });
    setTimeout(() => {
      const d3 = dom3.window.document;
      const collegamenti = Array.from(d3.querySelectorAll("#pir-prodotti a")).map((a) => a.getAttribute("href"));
      verifica("nessun errore dentro il sito", errori3.length === 0, errori3.join(" | "));
      verifica("selettore: solo le specie che hanno una pagina, agli indirizzi veri",
        collegamenti.length === 2 && collegamenti[0] === "https://www.pesceinrete.com/salmone/" &&
        collegamenti[1] === "https://www.pesceinrete.com/orata-2/", collegamenti.join(", "));
      const panoramica = Array.from(d3.querySelectorAll("#pir-tabella-panoramica tbody a")).map((a) => a.getAttribute("href"));
      verifica("panoramica: collegate solo le specie con una pagina, nessun collegamento morto",
        panoramica.length === 2 && panoramica.indexOf("https://www.pesceinrete.com/orata-2/") === 1 &&
        d3.querySelectorAll("#pir-tabella-panoramica tbody tr").length > 2, panoramica.join(", "));
      console.log(falliti === 0 ? "\nTutti i controlli superati." : "\n" + falliti + " controlli falliti.");
      process.exit(falliti === 0 ? 0 : 1);
    }, 400);
  }, 400);
}, 400);
