(function(){
"use strict";

/* ====================================================================
   Stato
   ==================================================================== */
var D = null;          // documento completo
var P = null;          // prodotto corrente
var misura = "eur";
var vista = "essenziale";
var paragone = "precedente";
var selezione = {dal:null, al:null};

var MESI = ["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"];

/* Lo stato della consultazione vive nell'indirizzo: un collega che riceve
   il collegamento vede la stessa cosa, non la vista predefinita. */
function leggiIndirizzo(){
  var frammento=(window.location.hash||"").replace(/^#/,"");
  var stato={};
  frammento.split("&").forEach(function(pezzo){
    var parti=pezzo.split("=");
    if(parti.length===2) stato[decodeURIComponent(parti[0])]=decodeURIComponent(parti[1]);
  });
  return stato;
}
function scriviIndirizzo(){
  if(!P) return;
  var pezzi=["p="+P.id,"v="+vista,"m="+misura,"dal="+selezione.dal,"al="+selezione.al];
  var nuovo="#"+pezzi.join("&");
  if(window.location.hash!==nuovo){
    try{ history.replaceState(null,"",nuovo); }catch(e){ }
  }
}

/* ====================================================================
   Utilità
   ==================================================================== */
/* Formattazione italiana scritta a mano: toLocaleString dipende dai dati
   locali del browser e su alcuni ambienti restituisce il punto decimale
   inglese. Su una pagina di prezzi non è un dettaglio. */
function num(valore, decimali){
  if(valore===null||valore===undefined||valore===""||isNaN(valore)) return "n.d.";
  var negativo=valore<0;
  // arrotondamento commerciale: 17,075 deve dare 17,08, e toFixed da solo dà 17,07
  var scala=Math.pow(10,decimali);
  var parti=(Math.round((Math.abs(valore)+1e-9)*scala)/scala).toFixed(decimali).split(".");
  parti[0]=parti[0].replace(/\B(?=(\d{3})+(?!\d))/g,".");
  return (negativo?"-":"")+parti[0]+(parti[1]?","+parti[1]:"");
}
function segno(valore, decimali){
  if(valore===null||valore===undefined) return "n.d.";
  var glifo = valore>0?"▲ ":(valore<0?"▼ ":"= ");
  return glifo+num(Math.abs(valore),decimali);
}
function settimanaVerso(chiave){                    // "2026-W36" -> Date del lunedi
  var anno=+chiave.slice(0,4), sett=+chiave.slice(6);
  var quattro=new Date(Date.UTC(anno,0,4));
  var lunediUno=new Date(quattro);
  lunediUno.setUTCDate(quattro.getUTCDate()-((quattro.getUTCDay()+6)%7));
  var giorno=new Date(lunediUno);
  giorno.setUTCDate(lunediUno.getUTCDate()+(sett-1)*7);
  return giorno;
}
function versoSettimana(data){                      // Date -> "2026-W36"
  var d=new Date(Date.UTC(data.getUTCFullYear(),data.getUTCMonth(),data.getUTCDate()));
  d.setUTCDate(d.getUTCDate()+4-((d.getUTCDay()+6)%7));
  var inizio=new Date(Date.UTC(d.getUTCFullYear(),0,1));
  var n=Math.ceil(((d-inizio)/86400000+1)/7);
  return d.getUTCFullYear()+"-W"+(n<10?"0"+n:n);
}
function iso(data){ return data.toISOString().slice(0,10); }
function etichettaBreve(chiave){
  var d=settimanaVerso(chiave);
  return d.getUTCDate()+" "+MESI[d.getUTCMonth()]+" "+String(d.getUTCFullYear()).slice(2);
}
function serieSelezionata(){
  return P.storico.filter(function(o){ return o.periodo>=selezione.dal && o.periodo<=selezione.al; });
}
function valoreDi(o){ return o[misura]; }
function unitaCorrente(){
  if(misura==="tonnellate") return "tonnellate";
  return misura==="origine" ? P.serie.unita_origine : "€/kg";
}

/* ====================================================================
   Calcoli, identici a core/metrics.py
   ==================================================================== */
function aggrega(punti){
  var usate=punti.filter(function(o){return o.eur!==null;});
  if(!usate.length) return {settimane:0, prezzo:null, volume:null, valore:null};
  var conVolume=usate.filter(function(o){return o.tonnellate;});
  if(conVolume.length===usate.length){
    var volume=0, valore=0;
    usate.forEach(function(o){ volume+=o.tonnellate; valore+=o.eur*o.tonnellate; });
    return {settimane:usate.length, prezzo:valore/volume, volume:volume, valore:valore, ponderato:true};
  }
  var somma=0; usate.forEach(function(o){somma+=o.eur;});
  return {settimane:usate.length, prezzo:somma/usate.length, volume:null, valore:null, ponderato:false};
}
function costoADestino(base, maggiorazione, trasporto, altri, glassatura, resa){
  var passi=[], prezzo=base;
  passi.push(["Riferimento di mercato", base]);
  if(maggiorazione){ var q=prezzo*maggiorazione/100; prezzo+=q; passi.push(["Maggiorazione "+maggiorazione+"%", q]); }
  if(trasporto){ prezzo+=trasporto; passi.push(["Trasporto", trasporto]); }
  if(altri){ prezzo+=altri; passi.push(["Altri costi", altri]); }
  passi.push(["Costo reso a destino", prezzo]);
  if(glassatura){ prezzo=prezzo/(1-glassatura/100); passi.push(["Netto glassatura "+glassatura+"%", prezzo]); }
  var utile=prezzo/(resa/100);
  passi.push(["Per kg utilizzabile, resa "+resa+"%", utile]);
  return {utile:utile, passi:passi};
}

/* ====================================================================
   Grafici
   ==================================================================== */
function scala(dominio, intervallo){
  var d0=dominio[0], d1=dominio[1], r0=intervallo[0], r1=intervallo[1];
  var ampiezza=(d1-d0)||1;
  return function(valore){ return r0+(valore-d0)/ampiezza*(r1-r0); };
}
function nodo(tag, attributi, testo){
  var elemento=document.createElementNS("http://www.w3.org/2000/svg",tag);
  for(var chiave in attributi){ if(attributi[chiave]!==null) elemento.setAttribute(chiave,attributi[chiave]); }
  if(testo!==undefined) elemento.textContent=testo;
  return elemento;
}
/* Un grafico disegnato per 1000 px e ridotto a 360 rende le etichette
   illeggibili: sotto i 560 px si usa una geometria compatta. */
function schermoStretto(contenitore){
  try{ if(window.matchMedia && window.matchMedia("(max-width: 560px)").matches) return true; }catch(e){}
  var largo=contenitore&&contenitore.clientWidth;
  return !!largo && largo<560;
}

function telaio(larghezza, altezza){
  var svg=nodo("svg",{viewBox:"0 0 "+larghezza+" "+altezza,preserveAspectRatio:"xMidYMid meet"});
  return svg;
}
function assi(svg, m, x, y, etichetteX, decimali){
  var passi=3;
  for(var i=0;i<=passi;i++){
    var valore=y.invertito[0]+(y.invertito[1]-y.invertito[0])*i/passi;
    var py=y(valore);
    svg.appendChild(nodo("line",{x1:m.sinistra,x2:m.larghezza-m.destra,y1:py,y2:py,
      stroke:coloreVariabile("--riga","#e4e8ee"),"stroke-width":1}));
    svg.appendChild(nodo("text",{x:m.sinistra-8,y:py+4,"text-anchor":"end",
      "font-size":11,fill:coloreVariabile("--tenue","#9aa5b1")},num(valore,decimali)));
  }
  etichetteX.forEach(function(e){
    svg.appendChild(nodo("text",{x:x(e.posizione),y:m.altezza-m.sotto+18,"text-anchor":"middle",
      "font-size":11,fill:coloreVariabile("--tenue","#9aa5b1")},e.testo));
  });
}

function disegnaBanda(){
  var contenitore=document.getElementById("pir-banda");
  contenitore.innerHTML="";
  var banda=P.banda_stagionale, anno=P.anno_corrente;
  if(!banda.length){ contenitore.textContent="Storico insufficiente."; return; }

  var stretto=schermoStretto(contenitore);
  var m=stretto
    ? {larghezza:420,altezza:250,sinistra:36,destra:50,sopra:16,sotto:24}
    : {larghezza:900,altezza:320,sinistra:40,destra:96,sopra:18,sotto:26};
  var svg=telaio(m.larghezza,m.altezza);

  var valori=[];
  banda.forEach(function(b){ valori.push(b.minimo,b.massimo); });
  anno.punti.forEach(function(p){ valori.push(p.valore); });
  var minimo=Math.min.apply(null,valori), massimo=Math.max.apply(null,valori);
  var margine=(massimo-minimo)*0.12;

  var x=scala([1,52],[m.sinistra,m.larghezza-m.destra]);
  var y=scala([minimo-margine,massimo+margine],[m.altezza-m.sotto,m.sopra]);
  y.invertito=[minimo-margine,massimo+margine];

  // mesi invece di numeri di settimana: si legge senza pensare
  var mesiSett=stretto?[[1,0],[18,4],[36,8]]:[[1,0],[9,2],[18,4],[27,6],[36,8],[44,10]];
  var etichette=mesiSett.map(function(c){ return {posizione:c[0],testo:MESI[c[1]]}; });
  assi(svg,m,x,y,etichette,2);

  var sopra="", sotto="";
  banda.forEach(function(b,i){ sopra+=(i?" L":"M")+x(b.settimana)+" "+y(b.massimo); });
  for(var i=banda.length-1;i>=0;i--){ sotto+=" L"+x(banda[i].settimana)+" "+y(banda[i].minimo); }
  svg.appendChild(nodo("path",{d:sopra+sotto+" Z",fill:coloreVariabile("--accento-velo","#eef5fa"),stroke:"none"}));

  // l'anno scorso, in grigio: è il confronto che un compratore fa a mente
  var scorso=(P.anno_precedente&&P.anno_precedente.punti)||[];
  if(scorso.length>1){
    var ls="";
    scorso.forEach(function(p,i){ ls+=(i?"L":"M")+x(p.settimana)+" "+y(p.valore); });
    svg.appendChild(nodo("path",{d:ls,fill:"none",stroke:coloreVariabile("--riga-forte","#cbd2db"),
      "stroke-width":1.6,"stroke-linejoin":"round"}));
    var fineScorso=scorso[scorso.length-1];
    svg.appendChild(nodo("text",{x:x(fineScorso.settimana)+6,y:y(fineScorso.valore)+4,"font-size":11,
      fill:coloreVariabile("--tenue","#9aa5b1")},String(P.anno_precedente.anno)));
  }
  // etichetta della fascia, in alto a destra dentro la fascia
  var ultimaBanda=banda[banda.length-1];
  var primoAnno=(P.stagionale.anni||[])[0], ultimoAnno=(P.stagionale.anni||[]).slice(-1)[0];
  if(ultimaBanda && primoAnno){
    svg.appendChild(nodo("text",{x:x(ultimaBanda.settimana)-4,y:y(ultimaBanda.massimo)-6,"font-size":11,
      "text-anchor":"end",fill:coloreVariabile("--tenue","#9aa5b1")},
      (stretto?"":"intervallo ")+primoAnno+"-"+String(ultimoAnno).slice(2)));
  }

  var linea="";
  anno.punti.forEach(function(p,i){ linea+=(i?"L":"M")+x(p.settimana)+" "+y(p.valore); });
  var tracciato=nodo("path",{d:linea,fill:"none",stroke:coloreVariabile("--accento","#003757"),"stroke-width":2.2,
    "stroke-linejoin":"round","stroke-linecap":"round",class:"pir-anima"});
  svg.appendChild(tracciato);

  var ultimo=anno.punti[anno.punti.length-1];
  if(ultimo){
    svg.appendChild(nodo("circle",{cx:x(ultimo.settimana),cy:y(ultimo.valore),r:5.5,fill:coloreVariabile("--azzurro","#1f8dcc"),
      stroke:coloreVariabile("--accento","#003757"),"stroke-width":2}));
    var testo=nodo("text",{x:x(ultimo.settimana)+9,y:y(ultimo.valore)+4,"font-size":13,
      "font-weight":700,fill:coloreVariabile("--accento","#003757")},num(ultimo.valore,2)+" · "+anno.anno);
    if(x(ultimo.settimana)>m.larghezza-m.destra-30){
      testo.setAttribute("x",x(ultimo.settimana)-9);
      testo.setAttribute("text-anchor","end");
    }
    svg.appendChild(testo);
  }

  // note della redazione dell'anno in corso: un marcatore giallo con il numero
  var noteAnno=(P.annotazioni||[]).filter(function(n){ return parseInt(n.periodo.slice(0,4),10)===anno.anno; });
  noteAnno.forEach(function(n,i){
    var settimana=parseInt(n.periodo.slice(6),10);
    var punto=anno.punti.filter(function(p){ return p.settimana===settimana; })[0];
    if(!punto) return;
    svg.appendChild(nodo("line",{x1:x(settimana),x2:x(settimana),y1:y(punto.valore)-8,y2:m.sopra+6,
      stroke:coloreVariabile("--azzurro","#1f8dcc"),"stroke-width":1.5,"stroke-dasharray":"2 3"}));
    svg.appendChild(nodo("circle",{cx:x(settimana),cy:m.sopra+6,r:8,fill:coloreVariabile("--azzurro","#1f8dcc"),
      stroke:coloreVariabile("--accento","#003757"),"stroke-width":1.5}));
    svg.appendChild(nodo("text",{x:x(settimana),y:m.sopra+10,"font-size":10,"font-weight":800,"text-anchor":"middle",
      fill:coloreVariabile("--accento","#003757")},String(i+1)));
  });
  scriviNote("pir-note-banda",noteAnno);

  contenitore.appendChild(svg);
  requestAnimationFrame(function(){
    try{ tracciato.style.setProperty("--lunghezza",tracciato.getTotalLength()); }catch(e){}
  });

  var anni=P.stagionale.anni||[];
  document.getElementById("pir-banda-testo").textContent =
    "Euro al chilo per settimana. La fascia chiara è l'intervallo fra minimo e massimo delle stesse "+
    "settimane degli anni "+(anni.length?anni[0]+"-"+anni[anni.length-1]:"precedenti")+
    "; la linea scura è il "+anno.anno+", quella grigia il "+(anno.anno-1)+".";
}

function disegnaStorico(){
  var contenitore=document.getElementById("pir-storico");
  contenitore.innerHTML="";
  var punti=serieSelezionata().filter(function(o){ return valoreDi(o)!==null; });
  if(punti.length<2){
    contenitore.textContent="Nessun dato nel periodo scelto.";
    document.getElementById("pir-storico-testo").textContent="";
    return;
  }

  var stretto=schermoStretto(contenitore);
  var m=stretto
    ? {larghezza:480,altezza:260,sinistra:46,destra:12,sopra:12,sotto:28}
    : {larghezza:1020,altezza:290,sinistra:52,destra:16,sopra:14,sotto:30};
  var svg=telaio(m.larghezza,m.altezza);

  var valori=punti.map(valoreDi);
  var minimo=Math.min.apply(null,valori), massimo=Math.max.apply(null,valori);
  var margine=(massimo-minimo)*0.12||1;
  var base=misura==="tonnellate"?0:minimo-margine;

  var x=scala([0,punti.length-1],[m.sinistra,m.larghezza-m.destra]);
  var y=scala([base,massimo+margine],[m.altezza-m.sotto,m.sopra]);
  y.invertito=[base,massimo+margine];

  var quante=Math.min(stretto?4:6,punti.length);
  var etichette=[];
  for(var i=0;i<quante;i++){
    var indice=Math.round(i*(punti.length-1)/(quante-1||1));
    etichette.push({posizione:indice,testo:etichettaBreve(punti[indice].periodo)});
  }
  assi(svg,m,x,y,etichette,misura==="tonnellate"?0:2);

  if(misura==="tonnellate"){
    var passo=Math.max(1,(m.larghezza-m.sinistra-m.destra)/punti.length-1);
    punti.forEach(function(o,i){
      svg.appendChild(nodo("rect",{x:x(i)-passo/2,y:y(valoreDi(o)),width:passo,
        height:Math.max(0,y(0)-y(valoreDi(o))),fill:coloreVariabile("--accento","#003757"),opacity:.75}));
    });
  }else{
    var d="";
    punti.forEach(function(o,i){ d+=(i?"L":"M")+x(i)+" "+y(valoreDi(o)); });
    svg.appendChild(nodo("path",{d:d,fill:"none",stroke:coloreVariabile("--accento","#003757"),
      "stroke-width":1.9,"stroke-linejoin":"round"}));
    var ultimo=punti[punti.length-1];
    svg.appendChild(nodo("circle",{cx:x(punti.length-1),cy:y(valoreDi(ultimo)),r:3.5,fill:coloreVariabile("--accento","#003757")}));
  }

  // note della redazione dentro il periodo mostrato
  var notePeriodo=(P.annotazioni||[]).filter(function(n){ return n.periodo>=selezione.dal && n.periodo<=selezione.al; });
  notePeriodo.forEach(function(n,i){
    var indice=-1;
    punti.forEach(function(o,k){ if(o.periodo===n.periodo) indice=k; });
    if(indice<0) return;
    svg.appendChild(nodo("line",{x1:x(indice),x2:x(indice),y1:m.sopra+6,y2:m.altezza-m.sotto,
      stroke:coloreVariabile("--azzurro","#1f8dcc"),"stroke-width":1.5,"stroke-dasharray":"2 3"}));
    svg.appendChild(nodo("circle",{cx:x(indice),cy:m.sopra+6,r:8,fill:coloreVariabile("--azzurro","#1f8dcc"),
      stroke:coloreVariabile("--accento","#003757"),"stroke-width":1.5}));
    svg.appendChild(nodo("text",{x:x(indice),y:m.sopra+10,"font-size":10,"font-weight":800,"text-anchor":"middle",
      fill:coloreVariabile("--accento","#003757")},String(i+1)));
  });
  scriviNote("pir-note-storico",notePeriodo);

  contenitore.appendChild(svg);
  collegaLettura(svg, punti, x, y, m);

  var agg=aggrega(serieSelezionata());
  document.getElementById("pir-storico-testo").textContent =
    punti.length+" settimane, da "+etichettaBreve(punti[0].periodo)+" a "+
    etichettaBreve(punti[punti.length-1].periodo)+". "+
    (misura==="tonnellate"
      ? "Volume complessivo "+num(agg.volume,0)+" tonnellate."
      : "Media ponderata sui volumi "+num(agg.prezzo,2)+" €/kg.");
}

/* ====================================================================
   Testi
   ==================================================================== */
/* Lettura puntuale: passando sopra il grafico si legge la settimana e il
   valore esatto. Un grafico di prezzi senza questa possibilità obbliga a
   scaricare il CSV per sapere un numero. */
function collegaLettura(svg, punti, x, y, m){
  var figura=svg.parentNode.parentNode;
  var etichetta=figura.querySelector(".pir-lettura");
  if(!etichetta){
    etichetta=document.createElement("div");
    etichetta.className="pir-lettura";
    figura.appendChild(etichetta);
  }
  var guida=nodo("line",{x1:0,x2:0,y1:m.sopra,y2:m.altezza-m.sotto,
    stroke:coloreVariabile("--accento","#003757"),"stroke-width":1,opacity:0});
  svg.appendChild(guida);

  function muovi(evento){
    var riquadro=svg.getBoundingClientRect();
    var punto=(evento.touches?evento.touches[0]:evento);
    var relativo=(punto.clientX-riquadro.left)/riquadro.width*m.larghezza;
    var frazione=(relativo-m.sinistra)/((m.larghezza-m.destra-m.sinistra)||1);
    var indice=Math.round(frazione*(punti.length-1));
    if(indice<0) indice=0;
    if(indice>punti.length-1) indice=punti.length-1;
    var scelto=punti[indice];

    guida.setAttribute("x1",x(indice));
    guida.setAttribute("x2",x(indice));
    guida.setAttribute("opacity",0.35);
    etichetta.textContent=etichettaBreve(scelto.periodo)+" · "+
      num(valoreDi(scelto),misura==="tonnellate"?0:2)+" "+unitaCorrente();
    etichetta.style.left=(x(indice)/m.larghezza*100)+"%";
    etichetta.style.top=(y(valoreDi(scelto))/m.altezza*100)+"%";
    etichetta.setAttribute("data-visibile","1");
  }
  function esci(){
    guida.setAttribute("opacity",0);
    etichetta.setAttribute("data-visibile","0");
  }
  svg.addEventListener("mousemove",muovi);
  svg.addEventListener("touchmove",muovi,{passive:true});
  svg.addEventListener("mouseleave",esci);
  svg.addEventListener("touchend",esci);
}

function scriviNote(id, note){
  var elenco=document.getElementById(id);
  if(!elenco) return;
  elenco.innerHTML=note.map(function(n,i){
    return "<li><b>"+(i+1)+"</b><span>"+etichettaBreve(n.periodo)+" — "+n.testo+"</span></li>";
  }).join("");
  elenco.hidden=!note.length;
}

/* "Dalla tua ultima visita": il browser ricorda prezzo e settimana che
   il lettore ha visto l'ultima volta per questa specie, e la pagina gli
   dice cosa è cambiato. Resta sul suo dispositivo, non viene inviato. */
function ultimaVisita(){
  var riga=document.getElementById("pir-ultima-visita");
  if(!riga) return;
  var chiave="pir-visita-"+P.id, prima=null;
  try{ prima=JSON.parse(localStorage.getItem(chiave)||"null"); }catch(e){}
  riga.hidden=true;
  if(prima && prima.periodo && prima.periodo!==P.ultimo_periodo && prima.prezzo){
    var delta=(P.prezzo_eur_kg-prima.prezzo)/prima.prezzo*100;
    riga.textContent="Dalla tua ultima visita (settimana "+prima.periodo.slice(6)+", "+num(prima.prezzo,2)+" €/kg) il prezzo è "+
      (Math.abs(delta)<0.5?"praticamente fermo":((delta>0?"salito":"sceso")+" del "+num(Math.abs(delta),1)+"%"))+".";
    riga.hidden=false;
  }
  try{ localStorage.setItem(chiave,JSON.stringify({periodo:P.ultimo_periodo,prezzo:P.prezzo_eur_kg})); }catch(e){}
}

function disegnaFlussi(){
  var sezione=document.getElementById("flussi");
  var f=P.flussi;
  if(!f){ sezione.hidden=true; return; }
  sezione.hidden=false;

  var d=f.dodici_mesi;
  document.getElementById("pir-flussi-spiega").textContent=
    f.indicatore+". "+f.note+" Ultimo mese disponibile: "+f.ultimo_mese_esteso+
    ", con il consueto ritardo di questa fonte rispetto ai prezzi settimanali.";

  document.getElementById("pir-flussi-quantita").innerHTML=
    num(d.tonnellate,0)+"<span>tonnellate</span>";
  document.getElementById("pir-flussi-quantita-nota").textContent=
    "Dodici mesi fino a "+f.ultimo_mese_esteso+
    (d.delta_tonnellate===null?"":", "+segno(d.delta_tonnellate,1)+"% sui dodici precedenti")+
    (d.mesi_usati<12?" · attenzione: solo "+d.mesi_usati+" mesi disponibili":"");

  document.getElementById("pir-flussi-valore").innerHTML=
    num(d.valore_unitario,2)+"<span>€/kg</span>";
  document.getElementById("pir-flussi-valore-nota").textContent=
    "Valore unitario medio in dogana"+
    (d.delta_valore_unitario===null?"":", "+segno(d.delta_valore_unitario,1)+"% sui dodici precedenti")+
    ". Non è un prezzo di acquisto.";

  var provenienze=(f.provenienze||[]).slice(0,4);
  document.getElementById("pir-flussi-quota").innerHTML= provenienze.length
    ? "<span class='pir-etichetta-piccola'>Provenienze, ultimi dodici mesi</span>"+
      "<ul class='pir-provenienze'>"+provenienze.map(function(pr){
        return "<li><span>"+pr.paese+"</span><span>"+num(pr.quota,1)+"%</span>"+
          "<span>"+num(pr.valore_unitario,2)+" €/kg</span></li>";
      }).join("")+"</ul>"
    : "";

  var contenitore=document.getElementById("pir-flussi-grafico");
  contenitore.innerHTML="";
  var serie=f.serie.slice(-36);
  if(serie.length<2) return;

  var stretto=schermoStretto(contenitore);
  var m=stretto
    ? {larghezza:420,altezza:230,sinistra:44,destra:10,sopra:12,sotto:26}
    : {larghezza:620,altezza:250,sinistra:48,destra:14,sopra:14,sotto:28};
  var svg=telaio(m.larghezza,m.altezza);
  var valori=serie.map(function(o){ return o.tonnellate; });
  var massimo=Math.max.apply(null,valori);
  var x=scala([0,serie.length-1],[m.sinistra,m.larghezza-m.destra]);
  var y=scala([0,massimo*1.1],[m.altezza-m.sotto,m.sopra]);
  y.invertito=[0,massimo*1.1];

  var etichette=[];
  for(var i=0;i<4;i++){
    var indice=Math.round(i*(serie.length-1)/3);
    var parti=serie[indice].periodo.split("-M");
    etichette.push({posizione:indice,testo:MESI[parseInt(parti[1],10)-1]+" "+parti[0].slice(2)});
  }
  assi(svg,m,x,y,etichette,0);

  var passo=Math.max(2,(m.larghezza-m.sinistra-m.destra)/serie.length-2);
  serie.forEach(function(o,i){
    svg.appendChild(nodo("rect",{x:x(i)-passo/2,y:y(o.tonnellate),width:passo,
      height:Math.max(0,y(0)-y(o.tonnellate)),fill:coloreVariabile("--accento","#003757"),opacity:.7}));
  });
  contenitore.appendChild(svg);

  document.getElementById("pir-flussi-testo").textContent=
    "Importazioni italiane mensili in tonnellate, ultimi "+serie.length+" mesi. "+f.fonte+".";
}

function scriviBollettino(){
  var voci=P.bollettino||[];
  var contenitore=document.getElementById("pir-voci");
  if(!voci.length){
    contenitore.innerHTML='<p class="pir-quiete">Nessun movimento fuori dall\'ordinario: '+
      "il prezzo resta dentro l'intervallo abituale del periodo e i volumi non presentano "+
      "scarti. Anche questa è un'informazione per chi deve decidere se comprare adesso "+
      "o aspettare.</p>";
    return;
  }
  contenitore.innerHTML=voci.map(function(v){
    return '<div class="pir-voce'+(v.rilievo==="alto"?" pir-voce--alto":"")+'">'+
      "<h3>"+v.titolo+"</h3><p>"+v.testo+"</p></div>";
  }).join("");
}

/* Indirizzo della pagina di una specie quando la sezione vive dentro il sito.
   Il sito passa l'elenco vero delle pagine (PESCEINRETE_URL_PRODOTTI); se non
   c'è, vale lo schema fisso. Restituisce null se la pagina non esiste: in quel
   caso la specie si mostra senza collegamento, invece di portare a un errore. */
function conPagine(){ return !!(window.PESCEINRETE_URL_PRODOTTI||window.PESCEINRETE_URL_PRODOTTO); }
function paginaProdotto(id){
  var mappa=window.PESCEINRETE_URL_PRODOTTI;
  if(mappa) return mappa[id]||null;
  var schema=window.PESCEINRETE_URL_PRODOTTO;
  return schema?schema.replace("{id}",id):null;
}

function scriviPanoramica(){
  var sezione=document.getElementById("panoramica");
  if(!sezione) return;
  if(D.prodotti.length<2){ sezione.hidden=true; return; }
  sezione.hidden=false;
  var schema=conPagine();
  var righe=D.prodotti.map(function(pr){
    var p=pr.percentile, att=pr.stagionale_attendibile;
    var classe=(!att||p===null)?"":(p>=80?" pir-posizione--alto":(p<=20?" pir-posizione--basso":""));
    var etichetta=(!att||p===null)?"storico corto":(p>=80?"sopra la norma":(p<=20?"sotto la norma":"nella norma"));
    var indirizzo=schema?paginaProdotto(pr.id):null;
    var nome=schema?(indirizzo?'<a href="'+indirizzo+'">'+pr.nome+"</a>":pr.nome):
      '<a href="#p='+pr.id+'" data-prodotto-riga="'+pr.id+'">'+pr.nome+"</a>";
    var periodo="sett. "+Number(pr.ultimo_periodo.slice(6))+(pr.media_settimane?", media "+pr.media_settimane+" sett.":"");
    return "<tr><td>"+nome+"</td><td>"+periodo+"</td><td>"+num(pr.prezzo_eur_kg,2)+"</td><td>"+segno(pr.variazione_settimana,1)+"%</td>"+
      "<td>"+segno(pr.variazione_anno,1)+"%</td><td><span class='pir-posizione"+classe+"'>"+etichetta+"</span></td></tr>";
  }).join("");
  document.getElementById("pir-tabella-panoramica").innerHTML=
    "<thead><tr><th>Specie</th><th>Periodo</th><th>€/kg</th><th>Sulla settimana</th><th>Sull'anno</th><th>Stagione</th></tr></thead><tbody>"+righe+"</tbody>";
  if(!schema){
    Array.prototype.forEach.call(document.querySelectorAll("[data-prodotto-riga]"),function(a){
      a.addEventListener("click",function(ev){
        ev.preventDefault();
        var id=a.getAttribute("data-prodotto-riga");
        caricaProdotto(id,function(prodotto){ P=prodotto; scriviSelettore(); mostraProdotto();
          var cima=document.getElementById("scheda"); if(cima&&cima.scrollIntoView) cima.scrollIntoView({behavior:"smooth"}); });
      });
    });
  }
}

function scriviSelettore(){
  var contenitore=document.getElementById("pir-prodotti");
  var mobile=document.getElementById("pir-scelta-mobile");
  var select=document.getElementById("pir-select-prodotto");
  if(D.prodotti.length<2){ contenitore.hidden=true; if(mobile) mobile.hidden=true; return; }
  contenitore.hidden=false;
  if(mobile && select){
    mobile.hidden=false;
    select.innerHTML=D.prodotti.filter(function(pr){
      return !conPagine()||pr.id===P.id||paginaProdotto(pr.id);
    }).map(function(pr){
      return '<option value="'+pr.id+'"'+(pr.id===P.id?" selected":"")+'>'+pr.nome+" · "+num(pr.prezzo_eur_kg,2)+" €/kg</option>";
    }).join("");
    if(!select.getAttribute("data-collegato")){
      select.setAttribute("data-collegato","1");
      select.addEventListener("change",function(){
        if(conPagine()){ var meta=paginaProdotto(select.value); if(meta) window.location.href=meta; return; }
        caricaProdotto(select.value,function(prodotto){ P=prodotto; scriviSelettore(); mostraProdotto(); });
      });
    }
  }
  var schema=conPagine();
  contenitore.innerHTML=D.prodotti.map(function(prodotto){
    var prezzo='<span class="pir-selettore-prezzo">'+num(prodotto.prezzo_eur_kg,2)+'</span>';
    if(schema){
      var indirizzo=paginaProdotto(prodotto.id);
      // specie senza pagina (non ancora pubblicata): niente collegamento morto
      if(!indirizzo && prodotto.id!==P.id) return "";
      return '<a href="'+(indirizzo||"#")+'" data-prodotto="'+prodotto.id+
        '" aria-current="'+(prodotto.id===P.id?"page":"false")+'">'+prodotto.nome+prezzo+"</a>";
    }
    return '<button type="button" data-prodotto="'+prodotto.id+'" aria-pressed="'+
      (prodotto.id===P.id)+'">'+prodotto.nome+prezzo+"</button>";
  }).join("");
  if(schema) return;
  gruppo("[data-prodotto]","data-prodotto",function(identificativo){
    caricaProdotto(identificativo,function(prodotto){ P=prodotto; mostraProdotto(); });
  });
}

function scriviApertura(){
  var s=P.serie;
  document.getElementById("pir-nome-prodotto").textContent=P.nome;
  document.getElementById("pir-qualifica").textContent=
    s.conservazione+". "+s.pezzatura+". "+s.fase+".";
  document.getElementById("pir-prezzo").innerHTML=num(P.prezzo_eur_kg,2)+"<span>€/kg</span>";
  document.getElementById("pir-origine").textContent=
    (P.serie.valuta_origine==="EUR" ? P.serie.fonte : num(P.prezzo_origine,2)+" "+P.serie.unita_origine)+
    (P.cambio?" al cambio "+num(P.cambio,3):"")+
    (P.con_volumi&&P.volume_tonnellate?" · "+num(P.volume_tonnellate,0)+" tonnellate":"");
  document.getElementById("pir-settimana").textContent=
    "Settimana "+P.ultimo_periodo.slice(6)+", "+P.ultimo_periodo_esteso;

  var badge=document.getElementById("pir-badge");
  var p=P.stagionale.percentile;
  var alto=P.stagionale.attendibile && p!==null && p>=80;
  var basso=P.stagionale.attendibile && p!==null && p<=20;
  badge.textContent=P.stagionale.lettura;
  badge.setAttribute("data-verdetto",
    !P.stagionale.attendibile||p===null ? "Storico corto" :
    (alto?"Sopra la norma":(basso?"Sotto la norma":"Nella norma")));
  badge.className="pir-badge pir-nascosto "+(alto?"pir-badge--sopra":(basso?"pir-badge--sotto":"pir-badge--norma"));

  var v=P.variazioni;
  document.getElementById("pir-delta").innerHTML=
    "<div><dt>Settimana</dt><dd>"+segno(v.settimana,1)+"%</dd></div>"+
    "<div><dt>4 settimane</dt><dd>"+segno(v.quattro_settimane,1)+"%</dd></div>"+
    "<div><dt>Anno</dt><dd>"+segno(v.anno,1)+"%</dd></div>";
  document.getElementById("pir-lede").textContent=P.lede||"";
  var netto=document.getElementById("pir-netto"), sn=P.stagionale_al_netto;
  if(netto){
    if(sn && sn.attendibile && sn.percentile!==null){
      var verdetto=sn.percentile>=80?"sopra la norma":(sn.percentile<=20?"sotto la norma":"nella norma");
      netto.innerHTML="Al netto del livello generale dei prezzi: <b>"+verdetto+"</b> (percentile "+num(sn.percentile,0)+
        " sul rapporto con la media mobile a 52 settimane).";
      netto.hidden=false;
    }else{ netto.hidden=true; }
  }
  document.getElementById("pir-quando").textContent=
    "Settimana "+P.ultimo_periodo.slice(6)+" · "+P.ultimo_periodo_esteso;
  var titoloIgb=document.getElementById("pir-igb-titolo");
  if(titoloIgb) titoloIgb.textContent="Cerchi fornitori di "+P.nome.toLowerCase()+"?";
  document.getElementById("pir-firma").textContent=
    "A cura della redazione · settimana "+P.ultimo_periodo.slice(6)+", "+P.ultimo_periodo_esteso+
    " · aggiornato il "+D.generato_il.slice(8,10)+"/"+D.generato_il.slice(5,7)+"/"+D.generato_il.slice(0,4);
}

function scriviConfronto(){
  var punti=serieSelezionata();
  var corrente=aggrega(punti);
  var rif=riferimento();
  var puntiRif=P.storico.filter(function(o){ return o.periodo>=rif.dal && o.periodo<=rif.al; });
  var base=aggrega(puntiRif);

  var omogeneo=corrente.settimane===base.settimane && corrente.settimane>0;
  function delta(a,b){ return (a!==null&&b)?((a-b)/b*100):null; }

  var righe=[
    ["Prezzo medio ponderato","€/kg",corrente.prezzo,base.prezzo,
      delta(corrente.prezzo,base.prezzo),2,true],
    ["Volume complessivo","tonnellate",corrente.volume,base.volume,
      omogeneo?delta(corrente.volume,base.volume):null,0,false],
    ["Valore ricostruito","euro",corrente.valore,base.valore,
      omogeneo?delta(corrente.valore,base.valore):null,0,false]
  ];

  var html='<table class="pir-tabella"><caption>Periodo selezionato '+
    etichettaBreve(selezione.dal)+" – "+etichettaBreve(selezione.al)+" ("+corrente.settimane+
    " settimane complete) contro "+etichettaBreve(rif.dal)+" – "+etichettaBreve(rif.al)+
    " ("+base.settimane+")</caption><thead><tr><th>Grandezza</th><th>Selezionato</th>"+
    "<th>Riferimento</th><th>Differenza</th><th>Variazione</th></tr></thead><tbody>";

  righe.forEach(function(r){
    var differenza=(r[2]!==null&&r[3]!==null)?r[2]-r[3]:null;
    if(r[0]!=="Prezzo medio ponderato" && !omogeneo){ differenza=null; }
    html+="<tr><td>"+r[0]+" <span style='color:var(--tenue)'>"+r[1]+"</span></td>"+
      '<td class="pir-forte">'+num(r[2],r[5])+"</td><td>"+num(r[3],r[5])+"</td><td>"+
      (differenza===null?"n.d.":segno(differenza,r[5]))+"</td><td>"+
      (r[4]===null?"n.d.":segno(r[4],1)+"%")+"</td></tr>";
  });
  html+="</tbody></table>";

  if(!omogeneo){
    html+='<p class="pir-nota">I due periodi contengono un numero diverso di settimane complete ('+
      corrente.settimane+" contro "+base.settimane+"). Il prezzo medio resta confrontabile perché "+
      "ponderato, i totali no: la loro variazione percentuale non viene calcolata.</p>";
  }
  if(!corrente.ponderato && corrente.settimane){
    html+='<p class="pir-nota">Volumi assenti in alcune settimane: il prezzo del periodo è una media '+
      "semplice, non ponderata.</p>";
  }
  html+='<p class="pir-didascalia">Il valore ricostruito è la somma di prezzo per volume. Non è un dato '+
    "pubblicato dalla fonte né una conferma indipendente dell'andamento: è la stessa informazione dei "+
    "due numeri sopra, moltiplicata.</p>";

  document.getElementById("pir-tabella-confronto").innerHTML=html;
}

function riferimento(){
  var tutte=P.storico.map(function(o){return o.periodo;});
  var da=tutte.indexOf(selezione.dal), a=tutte.indexOf(selezione.al);
  var lunghezza=a-da+1;

  if(paragone==="precedente"){
    var fine=Math.max(0,da-1);
    var inizio=Math.max(0,fine-lunghezza+1);
    return {dal:tutte[inizio],al:tutte[fine]};
  }
  if(paragone==="anno"){
    var indietro=52;
    return {dal:tutte[Math.max(0,da-indietro)],al:tutte[Math.max(0,a-indietro)]};
  }
  var dal=document.getElementById("pir-rif-dal").value;
  var al=document.getElementById("pir-rif-al").value;
  return {
    dal: dal?versoSettimana(new Date(dal)):tutte[Math.max(0,da-52)],
    al: al?versoSettimana(new Date(al)):tutte[Math.max(0,a-52)]
  };
}

function scriviLavorazioni(){
  var select=document.getElementById("pir-lavorazione");
  if(!select) return;
  var rese=P.rese||[];
  select.innerHTML=rese.length
    ? rese.map(function(r,i){ return '<option value="'+r.resa+'"'+(i===0?" selected":"")+'>'+r.etichetta+" · "+r.resa+"%</option>"; }).join("")
      +'<option value="">altro (imposto la resa a mano)</option>'
    : '<option value="">resa a mano</option>';
  if(rese.length) document.getElementById("pir-resa").value=rese[0].resa;
  if(!select.getAttribute("data-collegato")){
    select.setAttribute("data-collegato","1");
    select.addEventListener("change",function(){
      if(select.value){ document.getElementById("pir-resa").value=select.value; }
      scriviCalcolo();
    });
    var base=document.getElementById("pir-base-resa");
    base.addEventListener("change",function(){
      var trasporto=document.getElementById("pir-trasporto");
      if(base.value==="destino"){ trasporto.setAttribute("data-prima",trasporto.value); trasporto.value="0"; trasporto.disabled=true; }
      else{ trasporto.disabled=false; if(trasporto.getAttribute("data-prima")) trasporto.value=trasporto.getAttribute("data-prima"); }
      scriviCalcolo();
    });
  }
}

function scriviCalcolo(){
  function leggi(id,predefinito){
    var valore=parseFloat(document.getElementById(id).value);
    return isNaN(valore)?predefinito:valore;
  }
  var resa=Math.min(400,Math.max(1,leggi("pir-resa",100)));   // il baccalà dissalato rende più del 100%
  var glassatura=Math.min(60,Math.max(0,leggi("pir-glassatura",0)));
  var esito=costoADestino(
    leggi("pir-base",P.prezzo_eur_kg),
    Math.max(0,leggi("pir-maggiorazione",0)),
    Math.max(0,leggi("pir-trasporto",0)),
    Math.max(0,leggi("pir-altri",0)),
    glassatura, resa
  );
  document.getElementById("pir-esito-utile").innerHTML=
    num(esito.utile,2)+"<span>€/kg utile</span>";
  document.getElementById("pir-passi").innerHTML=esito.passi.map(function(p){
    return "<li><span>"+p[0]+"</span><span>"+num(p[1],2)+"</span></li>";
  }).join("");
}

function scriviMetodo(){
  var s=P.serie;
  document.getElementById("pir-perimetro").innerHTML=
    "<p>"+s.indicatore+" — "+s.fase+". "+s.mercato+".</p>"+
    "<p>"+s.note+"</p>"+
    "<p>Prodotto: "+s.conservazione.toLowerCase()+", "+s.pezzatura.toLowerCase()+
    ". Unità della fonte: "+s.unita_origine+"; la conversione in euro è nostra, "+
    "con il cambio di riferimento BCE medio della stessa settimana, indicativo e non "+
    "applicabile alle transazioni.</p>";

  document.getElementById("pir-provenienza").innerHTML=
    "<dt>Fonte</dt><dd><a href='"+s.fonte_url+"' rel='noopener'>"+s.fonte+"</a></dd>"+
    "<dt>Licenza</dt><dd><a href='"+s.licenza_url+"' rel='noopener'>"+s.licenza+"</a></dd>"+
    "<dt>Elaborazione</dt><dd>"+s.elaborazione+"</dd>"+
    "<dt>Frequenza</dt><dd>"+s.frequenza+", pubblicazione della fonte il mercoledi mattina</dd>"+
    "<dt>Ultimo periodo</dt><dd>"+P.ultimo_periodo+" ("+P.ultimo_periodo_esteso+")</dd>"+
    "<dt>Pagina aggiornata</dt><dd>"+D.generato_il.slice(0,16).replace("T"," ")+" UTC</dd>";

  var revisioni=P.revisioni_recenti||[];
  document.getElementById("pir-revisioni").innerHTML= revisioni.length
    ? "<p>Le statistiche del commercio estero vengono riviste. Queste sono le correzioni registrate "+
      "sulle settimane già pubblicate.</p>"+
      "<table class='pir-tabella'><thead><tr><th>Settimana</th><th>Prima</th><th>Dopo</th>"+
      "<th>Rilevata</th></tr></thead><tbody>"+
      revisioni.map(function(r){
        return "<tr><td>"+r.periodo+"</td><td>"+num(r.da,2)+"</td><td>"+num(r.a,2)+
          "</td><td>"+r.rilevata_il+"</td></tr>";
      }).join("")+"</tbody></table>"
    : "<p>Nessuna revisione registrata sulle settimane già pubblicate.</p>";

  var diario=(D.diario||[]).slice(0,4).map(function(e){
    return e.quando+" · "+e.fonte+" · "+e.esito+" ("+e.nuove+" nuove, "+e.riviste+" riviste)";
  }).join("<br>");
  document.getElementById("pir-piede").innerHTML=
    "Dati: "+s.fonte+", "+s.licenza+", con elaborazioni di Pesceinrete. "+
    "Cambi: Banca centrale europea, valori di riferimento. "+
    "Se un controllo di qualità non passa resta pubblicata l'ultima versione valida.<br><br>"+
    "<span style='color:var(--tenue)'>Ultimi aggiornamenti<br>"+diario+"</span>";
}

function scriviSchema(){
  var s=P.serie;
  document.getElementById("pir-schema").textContent=JSON.stringify({
    "@context":"https://schema.org",
    "@type":"Dataset",
    "name":P.titolo_pagina,
    "description":P.descrizione_pagina,
    "temporalCoverage":P.storico[0].periodo.slice(0,4)+"/"+P.ultimo_periodo.slice(0,4),
    "isAccessibleForFree":true,
    "license":s.licenza_url,
    "creator":{"@type":"Organization","name":"Pesceinrete"},
    "isBasedOn":s.fonte_url,
    "variableMeasured":[
      {"@type":"PropertyValue","name":"Prezzo medio all'esportazione","unitText":"EUR/kg",
       "value":P.prezzo_eur_kg},
      {"@type":"PropertyValue","name":"Volume esportato","unitText":"tonnellate",
       "value":P.volume_tonnellate}
    ],
    "dateModified":D.generato_il.slice(0,10)
  });
}

function scriviStato(){
  var fascia=document.getElementById("pir-stato");
  if(D.stato==="in linea"){ fascia.hidden=true; return; }
  fascia.hidden=false;
  fascia.innerHTML='<div class="pir-fascia"><strong>Dati dimostrativi.</strong> '+
    "Questa pagina mostra una serie inventata, utile solo a provare il funzionamento. "+
    "Non usarla per decisioni commerciali: diventerà reale al primo collegamento con la fonte.</div>";
}

/* ====================================================================
   CSV
   ==================================================================== */
function scaricaCsv(){
  var s=P.serie;
  // la nota sull'elaborazione dipende dalla fonte: una serie già in euro non passa dal cambio
  var inEuro=String(s.unita_origine||"").indexOf("EUR")===0;
  var elaborazione=inEuro?
    "# Elaborazione Pesceinrete: valore dichiarato diviso peso netto, sole settimane complete; dato già in euro, nessun cambio applicato":
    "# Elaborazione Pesceinrete: conversione in euro al cambio BCE medio della stessa settimana";
  if(inEuro && P.media_settimane) elaborazione+="; prezzo = media delle ultime "+P.media_settimane+" settimane pesata sui volumi";
  var righe=[
    "# "+P.nome+" — "+s.indicatore,
    "# Fonte: "+s.fonte+" ("+s.fonte_url+")",
    "# Licenza: "+s.licenza+" ("+s.licenza_url+")",
    elaborazione,
    "# Perimetro: "+s.conservazione+", "+s.pezzatura+", "+s.fase,
    "# Periodo estratto: "+selezione.dal+" - "+selezione.al,
    "# Stato dati: "+D.stato+" — estratto il "+new Date().toISOString().slice(0,10),
    "settimana;inizio;fine;prezzo_eur_kg;prezzo_valuta_origine;cambio;tonnellate"
  ];
  serieSelezionata().forEach(function(o){
    var lunedi=settimanaVerso(o.periodo);
    var domenica=new Date(lunedi); domenica.setUTCDate(lunedi.getUTCDate()+6);
    righe.push([o.periodo,iso(lunedi),iso(domenica),
      o.eur===null?"":String(o.eur).replace(".",","),
      o.origine===null?"":String(o.origine).replace(".",","),
      o.cambio===null?"":String(o.cambio).replace(".",","),
      o.tonnellate===null?"":o.tonnellate].join(";"));
  });
  var blob=new Blob(["\ufeff"+righe.join("\n")],{type:"text/csv;charset=utf-8"});
  var collegamento=document.createElement("a");
  collegamento.href=URL.createObjectURL(blob);
  collegamento.download="pesceinrete-"+P.id+"-"+selezione.dal+"-"+selezione.al+".csv";
  document.body.appendChild(collegamento);
  collegamento.click();
  document.body.removeChild(collegamento);
  URL.revokeObjectURL(collegamento.href);
}

/* ====================================================================
   Interazione
   ==================================================================== */
function applicaFinestra(settimane){
  var tutte=P.storico.map(function(o){ return o.periodo; });
  var fine=tutte.length-1;
  var inizio=settimane?Math.max(0,fine-settimane+1):0;
  selezione.dal=tutte[inizio];
  selezione.al=tutte[fine];
  document.getElementById("pir-dal").value=iso(settimanaVerso(selezione.dal));
  document.getElementById("pir-al").value=iso(settimanaVerso(selezione.al));
}

function gruppo(selettore, attributo, azione){
  Array.prototype.forEach.call(document.querySelectorAll(selettore),function(bottone){
    bottone.addEventListener("click",function(){
      Array.prototype.forEach.call(document.querySelectorAll(selettore),function(altro){
        altro.setAttribute("aria-pressed",String(altro===bottone));
      });
      azione(bottone.getAttribute(attributo));
    });
  });
}

function aggiorna(){
  disegnaStorico();
  scriviConfronto();
  scriviIndirizzo();
}

function applicaVista(nuova, scorriA){
  vista=(nuova==="completa")?"completa":"essenziale";
  document.querySelector(".pir-mercati").setAttribute("data-vista",vista);
  try{ localStorage.setItem("pir-vista",vista); }catch(e){}
  if(scorriA){
    var bersaglio=document.getElementById(scorriA);
    if(bersaglio && bersaglio.scrollIntoView) bersaglio.scrollIntoView({behavior:"smooth",block:"start"});
  }
  Array.prototype.forEach.call(document.querySelectorAll("[data-vista]"),function(b){
    if(b.tagName==="BUTTON") b.setAttribute("aria-pressed",String(b.getAttribute("data-vista")===vista));
  });
  Array.prototype.forEach.call(document.querySelectorAll(".pir-nav a"),function(a){
    var destinazione=document.querySelector(a.getAttribute("href"));
    a.hidden=!!(destinazione && destinazione.getAttribute("data-livello")==="2" && vista==="essenziale");
  });
  scriviIndirizzo();
  // I grafici nascosti non hanno dimensioni: si ridisegnano quando la vista
  // si apre. Ma solo se il prodotto è già caricato: all'avvio la vista
  // viene applicata prima dei dati (e la scelta "completa" può arrivare
  // dalla memoria del browser di una visita precedente).
  if(vista==="completa" && P) disegnaStorico();
}

function collega(){
  var attesa=null;
  window.addEventListener("resize",function(){
    clearTimeout(attesa);
    attesa=setTimeout(function(){ if(P){ disegnaBanda(); disegnaStorico(); disegnaFlussi(); } },180);
  });
  Array.prototype.forEach.call(document.querySelectorAll("button[data-vista]"),function(b){
    b.addEventListener("click",function(){ applicaVista(b.getAttribute("data-vista"), b.getAttribute("data-scorri")); });
  });
  gruppo("[data-misura]","data-misura",function(valore){ misura=valore; disegnaStorico(); });
  gruppo("[data-finestra]","data-finestra",function(valore){
    applicaFinestra(parseInt(valore,10)); aggiorna();
  });
  gruppo("[data-paragone]","data-paragone",function(valore){
    paragone=valore;
    var libero=valore==="libero";
    document.getElementById("pir-campo-rif-dal").hidden=!libero;
    document.getElementById("pir-campo-rif-al").hidden=!libero;
    scriviConfronto();
  });

  ["pir-dal","pir-al"].forEach(function(id){
    document.getElementById(id).addEventListener("change",function(){
      var dal=document.getElementById("pir-dal").value;
      var al=document.getElementById("pir-al").value;
      if(!dal||!al) return;
      var primo=P.storico[0].periodo, ultimo=P.storico[P.storico.length-1].periodo;
      var a=versoSettimana(new Date(dal)), b=versoSettimana(new Date(al));
      if(a>b){ var scambio=a; a=b; b=scambio; }
      selezione.dal=a<primo?primo:a;
      selezione.al=b>ultimo?ultimo:b;
      Array.prototype.forEach.call(document.querySelectorAll("[data-finestra]"),function(bottone){
        bottone.setAttribute("aria-pressed","false");
      });
      aggiorna();
    });
  });

  ["pir-rif-dal","pir-rif-al"].forEach(function(id){
    document.getElementById(id).addEventListener("change",scriviConfronto);
  });

  ["pir-base","pir-maggiorazione","pir-trasporto","pir-altri","pir-glassatura","pir-resa"]
    .forEach(function(id){
      document.getElementById(id).addEventListener("input",scriviCalcolo);
    });

  document.getElementById("pir-csv").addEventListener("click",scaricaCsv);
  var bg=document.getElementById("pir-scarica-grafico"); if(bg) bg.addEventListener("click",scaricaGrafico);
  var bl=document.getElementById("pir-copia-link"); if(bl) bl.addEventListener("click",copiaLink);
}

/* Legge una variabile per usarla dentro l'SVG, che non eredita da solo.
   Se il browser non restituisce un colore utilizzabile si usa il ripiego:
   meglio un grafico con i colori predefiniti che un grafico invisibile. */
function coloreVariabile(nome, ripiego){
  var radice=document.querySelector(".pir-mercati");
  if(!radice||!window.getComputedStyle) return ripiego;
  var valore=((getComputedStyle(radice).getPropertyValue(nome))||"").trim();
  return /^(#|rgb|hsl)/i.test(valore) ? valore : ripiego;
}

/* ====================================================================
   Azioni: grafico in PNG, collegamento alla vista
   ==================================================================== */
function scaricaGrafico(){
  var svg=document.querySelector("#pir-banda svg");
  if(!svg) return;
  var clone=svg.cloneNode(true);
  // i colori dei font e delle linee sono già scritti nell'SVG; aggiungo il carattere
  clone.setAttribute("xmlns","http://www.w3.org/2000/svg");
  clone.setAttribute("style","font-family:Manrope,Arial,sans-serif;background:#fff");
  var vb=(svg.getAttribute("viewBox")||"0 0 680 300").split(" ").map(Number);
  var scala=2, l=vb[2], a=vb[3]+44;
  var intest=document.createElementNS("http://www.w3.org/2000/svg","text");
  intest.setAttribute("x",vb[0]+8); intest.setAttribute("y",vb[1]+vb[3]+30);
  intest.setAttribute("font-size","11"); intest.setAttribute("fill","#6b7a90");
  intest.textContent=P.nome+" · "+num(P.prezzo_eur_kg,2)+" €/kg · "+P.ultimo_periodo+" · Pesceinrete, "+P.serie.fonte;
  clone.setAttribute("viewBox",vb[0]+" "+vb[1]+" "+l+" "+a);
  clone.appendChild(intest);
  var testo=new XMLSerializer().serializeToString(clone);
  var url=URL.createObjectURL(new Blob([testo],{type:"image/svg+xml;charset=utf-8"}));
  var img=new Image();
  img.onload=function(){
    var tela=document.createElement("canvas");
    tela.width=l*scala; tela.height=a*scala;
    var ctx=tela.getContext("2d");
    ctx.fillStyle="#fff"; ctx.fillRect(0,0,tela.width,tela.height);
    ctx.drawImage(img,0,0,tela.width,tela.height);
    URL.revokeObjectURL(url);
    var a2=document.createElement("a");
    a2.download="pesceinrete-"+P.id+"-"+P.ultimo_periodo+".png";
    a2.href=tela.toDataURL("image/png");
    document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
    esito("Grafico scaricato.");
  };
  img.onerror=function(){ esito("Non sono riuscito a generare l'immagine."); };
  img.src=url;
}
function copiaLink(){
  var indirizzo=window.location.href;
  function fatto(){ esito("Link copiato."); }
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(indirizzo).then(fatto,function(){ esito(indirizzo); });
  }else{ esito(indirizzo); }
}
function esito(messaggio){
  var e=document.getElementById("pir-azioni-esito");
  if(!e) return;
  e.textContent=messaggio;
  clearTimeout(esito._t); esito._t=setTimeout(function(){ e.textContent=""; },3500);
}

/* ====================================================================
   Avvio
   ==================================================================== */
function mostraProdotto(stato){
  stato=stato||{};
  // Sulla pagina d'ingresso della sezione titolo e descrizione sono della
  // sezione e li scrive il sito: non vanno sostituiti con quelli di una specie.
  if(!window.PESCEINRETE_PAGINA_INGRESSO){
    document.title=P.titolo_pagina+" — Pesceinrete";
    var descrizione=document.querySelector('meta[name="description"]');
    if(descrizione) descrizione.setAttribute("content",P.descrizione_pagina);
  }

  var bottoneOrigine=document.getElementById("pir-bottone-origine");
  var inEuro=P.serie.valuta_origine==="EUR";
  if(bottoneOrigine){
    bottoneOrigine.textContent="Prezzo "+P.serie.unita_origine;
    bottoneOrigine.hidden=inEuro;
  }
  var bottoneVolume=document.querySelector('[data-misura="tonnellate"]');
  if(bottoneVolume) bottoneVolume.hidden=!P.con_volumi;
  if((inEuro && misura==="origine")||(!P.con_volumi && misura==="tonnellate")){
    misura="eur";
    Array.prototype.forEach.call(document.querySelectorAll("[data-misura]"),function(b){
      b.setAttribute("aria-pressed",String(b.getAttribute("data-misura")==="eur"));
    });
  }

  // Il blocco statico viene inserito dal server per la specie iniziale; al
  // cambio di specie si sostituisce con quello della specie mostrata.
  var statico=document.getElementById("pir-sintesi-statica");
  if(statico && P.sintesi_html) statico.innerHTML=P.sintesi_html;

  scriviApertura();
  ultimaVisita();
  disegnaBanda();
  disegnaFlussi();
  scriviBollettino();

  if(stato.dal && stato.al){
    selezione.dal=stato.dal; selezione.al=stato.al;
    document.getElementById("pir-dal").value=iso(settimanaVerso(selezione.dal));
    document.getElementById("pir-al").value=iso(settimanaVerso(selezione.al));
  }else{
    applicaFinestra(52);
  }

  document.getElementById("pir-base").value=P.prezzo_eur_kg;
  scriviLavorazioni();
  scriviCalcolo();
  scriviMetodo();
  scriviSchema();
  aggiorna();
}

/* L'indice (mercati.json) è piccolo e contiene una riga per specie; il
   dettaglio di ciascuna sta in un file a parte, caricato solo quando
   serve. Dieci specie non devono costare dieci volte il peso di una. */
var CACHE_PRODOTTI={};

function urlProdotto(id){
  var base=window.PESCEINRETE_URL_DATI||"./data/mercati.json";
  return base.replace(/mercati(\.en)?\.json/,"prodotti/"+id+"$1.json");
}

function caricaProdotto(id, poi){
  if(window.PESCEINRETE_PRODOTTI && window.PESCEINRETE_PRODOTTI[id]){
    poi(window.PESCEINRETE_PRODOTTI[id]); return;
  }
  if(CACHE_PRODOTTI[id]){ poi(CACHE_PRODOTTI[id]); return; }
  fetch(urlProdotto(id),{cache:"no-cache"})
    .then(function(r){ if(!r.ok) throw new Error("risposta "+r.status); return r.json(); })
    .then(function(prodotto){ CACHE_PRODOTTI[id]=prodotto; poi(prodotto); })
    .catch(function(e){ errore("Il dettaglio del prodotto non è stato caricato ("+e.message+")."); });
}

function avvia(documento){
  D=documento;
  var stato=leggiIndirizzo();
  var richiesto=stato.p||window.PESCEINRETE_PRODOTTO||D.prodotti[0].id;
  var voce=D.prodotti.filter(function(x){ return x.id===richiesto; })[0]||D.prodotti[0];
  if(stato.m==="eur"||stato.m==="origine"||stato.m==="tonnellate"){
    misura=stato.m;
    Array.prototype.forEach.call(document.querySelectorAll("[data-misura]"),function(b){
      b.setAttribute("aria-pressed",String(b.getAttribute("data-misura")===misura));
    });
  }
  document.querySelector(".pir-mercati").setAttribute("data-script","1");
  scriviStato();
  var iscrizione=document.getElementById("pir-iscrizione");
  if(iscrizione && window.PESCEINRETE_URL_ISCRIZIONE){
    document.getElementById("pir-modulo-iscrizione").setAttribute("action",window.PESCEINRETE_URL_ISCRIZIONE);
    iscrizione.hidden=false;
  }
  scriviPanoramica();
  collega();
  var ricordata=null;
  try{ ricordata=localStorage.getItem("pir-vista"); }catch(e){}
  applicaVista(stato.v||ricordata||"essenziale");
  caricaProdotto(voce.id,function(prodotto){
    P=prodotto;
    scriviSelettore();
    mostraProdotto(stato);
  });
}

function errore(messaggio){
  document.getElementById("pir-stato").hidden=false;
  document.getElementById("pir-stato").innerHTML=
    '<div class="pir-fascia"><strong>Dati non disponibili.</strong> '+messaggio+
    " Riprova fra qualche minuto oppure segnala il problema alla redazione.</div>";
}

if(window.PESCEINRETE_DATI){
  avvia(window.PESCEINRETE_DATI);
}else{
  fetch(window.PESCEINRETE_URL_DATI||"./data/mercati.json",{cache:"no-cache"})
    .then(function(risposta){
      if(!risposta.ok) throw new Error("risposta "+risposta.status);
      return risposta.json();
    })
    .then(avvia)
    .catch(function(e){ errore("Il file dei dati non è stato caricato ("+e.message+")."); });
}
})();
