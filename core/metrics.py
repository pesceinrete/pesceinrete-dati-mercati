"""Calcoli sulle serie settimanali.

Regole comuni a tutte le funzioni:

* un periodo incompleto non viene mai completato per interpolazione: si
  restituisce None e il chiamante mostra "non disponibile";
* i confronti fra periodi di lunghezza diversa vengono segnalati, non
  trasformati in percentuali;
* la media di un prezzo su più settimane è sempre ponderata sui volumi,
  perché la media semplice di un prezzo settimanale non ha significato
  economico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from . import isoweek


@dataclass
class Aggregato:
    """Sintesi di un periodo."""

    dalla: str | None
    alla: str | None
    settimane_attese: int = 0
    settimane_usate: int = 0
    prezzo_medio_ponderato: float | None = None
    volume_totale: float | None = None
    valore_totale: float | None = None
    avvertenze: list[str] = field(default_factory=list)

    @property
    def completo(self) -> bool:
        return self.settimane_attese > 0 and self.settimane_usate == self.settimane_attese


def aggrega(osservazioni: list[dict], dalla: str, alla: str) -> Aggregato:
    """Prezzo medio ponderato, volume e valore di un intervallo di settimane.

    Il valore totale è la somma di prezzo x volume. Non è un dato
    indipendente: è la ricostruzione del monte valore da cui la fonte ha
    ricavato il prezzo medio. Va etichettato come tale, mai presentato
    come terza conferma dell'andamento.
    """
    attese = isoweek.intervallo(dalla, alla)
    dentro = {
        o["periodo"]: o
        for o in osservazioni
        if dalla <= o["periodo"] <= alla and o.get("valore") is not None
    }

    agg = Aggregato(dalla=dalla, alla=alla, settimane_attese=len(attese))
    usate = [dentro[p] for p in attese if p in dentro]
    agg.settimane_usate = len(usate)

    mancanti = [p for p in attese if p not in dentro]
    if mancanti:
        agg.avvertenze.append(
            f"{len(mancanti)} settimane senza dato: {', '.join(mancanti[:6])}"
            + (" ..." if len(mancanti) > 6 else "")
        )
    if not usate:
        return agg

    con_volume = [o for o in usate if o.get("quantita")]
    if len(con_volume) == len(usate):
        volume = sum(o["quantita"] for o in usate)
        valore = sum(o["valore"] * o["quantita"] for o in usate)
        agg.volume_totale = volume
        agg.valore_totale = valore
        agg.prezzo_medio_ponderato = valore / volume if volume else None
    else:
        agg.prezzo_medio_ponderato = sum(o["valore"] for o in usate) / len(usate)
        agg.avvertenze.append(
            "volumi non disponibili per tutte le settimane: media semplice, non ponderata"
        )
    return agg


@dataclass
class Confronto:
    corrente: Aggregato
    riferimento: Aggregato
    omogeneo: bool
    delta_prezzo_assoluto: float | None = None
    delta_prezzo_percentuale: float | None = None
    delta_volume_assoluto: float | None = None
    delta_volume_percentuale: float | None = None
    avvertenze: list[str] = field(default_factory=list)


def confronta(corrente: Aggregato, riferimento: Aggregato) -> Confronto:
    """Delta fra due periodi, con controllo di omogeneità.

    Se i due periodi non hanno lo stesso numero di settimane effettivamente
    usate, le percentuali sul volume non vengono calcolate: confrontare il
    volume di 5 settimane con quello di 4 produce un -20% inesistente.
    """
    omogeneo = (
        corrente.settimane_usate == riferimento.settimane_usate
        and corrente.settimane_usate > 0
    )
    esito = Confronto(corrente=corrente, riferimento=riferimento, omogeneo=omogeneo)

    if not omogeneo:
        esito.avvertenze.append(
            f"periodi non omogenei: {corrente.settimane_usate} settimane contro "
            f"{riferimento.settimane_usate}. Il confronto sui totali non viene calcolato."
        )

    pc, pr = corrente.prezzo_medio_ponderato, riferimento.prezzo_medio_ponderato
    if pc is not None and pr:
        esito.delta_prezzo_assoluto = pc - pr
        esito.delta_prezzo_percentuale = (pc - pr) / pr * 100

    vc, vr = corrente.volume_totale, riferimento.volume_totale
    if omogeneo and vc is not None and vr:
        esito.delta_volume_assoluto = vc - vr
        esito.delta_volume_percentuale = (vc - vr) / vr * 100

    return esito


def periodo_precedente(dalla: str, alla: str) -> tuple[str, str]:
    """Intervallo immediatamente precedente, della stessa lunghezza."""
    lunghezza = len(isoweek.intervallo(dalla, alla))
    fine = isoweek.sposta(dalla, -1)
    inizio = isoweek.sposta(fine, -(lunghezza - 1))
    return inizio, fine


def periodo_anno_precedente(dalla: str, alla: str) -> tuple[str, str]:
    """Stesso intervallo di settimane ISO dell'anno precedente."""
    return (
        isoweek.stessa_settimana_anno_precedente(dalla),
        isoweek.stessa_settimana_anno_precedente(alla),
    )


# --------------------------------------------------------------------------
# Posizione stagionale
# --------------------------------------------------------------------------


@dataclass
class PosizioneStagionale:
    percentile: float | None
    osservazioni_confronto: int
    minimo: float | None = None
    mediana: float | None = None
    massimo: float | None = None
    anni_usati: list[int] = field(default_factory=list)
    attendibile: bool = False

    def lettura(self, lingua: str = "it") -> str:
        """Frase pronta per la pagina, senza attribuire cause."""
        from .testi import STAGIONALE

        frasi = STAGIONALE.get(lingua, STAGIONALE["it"])
        if self.percentile is None or not self.attendibile:
            return frasi["insufficiente"]
        from .redazione import anni_di_confronto
        anni = anni_di_confronto(len(self.anni_usati), lingua, "in")
        if self.percentile >= 99.5:
            return frasi["massimo"].format(anni=anni)
        if self.percentile <= 0.5:
            return frasi["minimo"].format(anni=anni)
        if self.percentile >= 80:
            return frasi["alto"].format(p=self.percentile)
        if self.percentile <= 20:
            return frasi["basso"].format(p=100 - self.percentile)
        return frasi["norma"]


def posizione_stagionale(
    osservazioni: list[dict],
    periodo: str,
    anni_indietro: int = 5,
    ampiezza_finestra: int = 2,
    minimo_osservazioni: int = 12,
) -> PosizioneStagionale:
    """Percentile del valore corrente rispetto allo stesso momento dell'anno.

    Risponde alla domanda che conta per chi compra: "è un livello insolito
    per essere questa settimana?". Il confronto con il solo anno precedente
    non basta, perché un singolo anno può essere anomalo.

    Il paniere di confronto sono le settimane ISO vicine (+/- 2 di default)
    degli anni precedenti, escluso l'anno corrente.
    """
    valori = {o["periodo"]: o["valore"] for o in osservazioni if o.get("valore") is not None}
    corrente = valori.get(periodo)
    if corrente is None:
        return PosizioneStagionale(percentile=None, osservazioni_confronto=0)

    anno, settimana = isoweek.scomponi(periodo)
    settimane_valide = set(isoweek.finestra_stagionale(settimana, ampiezza_finestra))

    paniere, anni = [], set()
    for chiave, valore in valori.items():
        anno_o, settimana_o = isoweek.scomponi(chiave)
        if anno_o >= anno or anno_o < anno - anni_indietro:
            continue
        if settimana_o in settimane_valide or (settimana_o == 53 and 52 in settimane_valide):
            paniere.append(valore)
            anni.add(anno_o)

    if not paniere:
        return PosizioneStagionale(percentile=None, osservazioni_confronto=0)

    sotto = sum(1 for v in paniere if v < corrente)
    pari = sum(1 for v in paniere if v == corrente)
    percentile = (sotto + 0.5 * pari) / len(paniere) * 100

    return PosizioneStagionale(
        percentile=percentile,
        osservazioni_confronto=len(paniere),
        minimo=min(paniere),
        mediana=median(paniere),
        massimo=max(paniere),
        anni_usati=sorted(anni),
        attendibile=len(paniere) >= minimo_osservazioni and len(anni) >= 3,
    )


def banda_stagionale(
    osservazioni: list[dict], anno_escluso: int | None = None, anni_indietro: int = 5
) -> dict[int, dict]:
    """Minimo, mediana e massimo per settimana ISO sugli anni precedenti.

    È la base del grafico principale: la banda mostra l'intervallo
    abituale, la linea dell'anno corrente mostra dove siamo dentro quella
    banda. Un prezzo può essere in calo e restare comunque alto per il
    periodo: la banda lo rende visibile, il delta settimanale no.
    """
    per_settimana: dict[int, list[float]] = {}
    anni_disponibili = {
        isoweek.scomponi(o["periodo"])[0]
        for o in osservazioni
        if o.get("valore") is not None
    }
    if not anni_disponibili:
        return {}
    riferimento = anno_escluso if anno_escluso is not None else max(anni_disponibili)

    for o in osservazioni:
        if o.get("valore") is None:
            continue
        anno, settimana = isoweek.scomponi(o["periodo"])
        if anno >= riferimento or anno < riferimento - anni_indietro:
            continue
        if settimana == 53:
            settimana = 52
        per_settimana.setdefault(settimana, []).append(o["valore"])

    return {
        settimana: {
            "minimo": min(valori),
            "mediana": median(valori),
            "massimo": max(valori),
            "osservazioni": len(valori),
        }
        for settimana, valori in sorted(per_settimana.items())
    }


def variazioni_recenti(osservazioni: list[dict], periodo: str) -> dict[str, float | None]:
    """Delta percentuali a 1, 4 e 52 settimane sul prezzo."""
    valori = {o["periodo"]: o["valore"] for o in osservazioni if o.get("valore") is not None}
    corrente = valori.get(periodo)
    risultato: dict[str, float | None] = {}

    riferimenti = {
        "settimana": isoweek.sposta(periodo, -1),
        "quattro_settimane": isoweek.sposta(periodo, -4),
        "anno": isoweek.stessa_settimana_anno_precedente(periodo),
    }
    for nome, chiave in riferimenti.items():
        base = valori.get(chiave)
        risultato[nome] = (
            (corrente - base) / base * 100 if corrente is not None and base else None
        )
    return risultato


# --------------------------------------------------------------------------
# Conversione valutaria
# --------------------------------------------------------------------------


def converti(
    osservazioni: list[dict], cambi_settimanali: dict[str, float]
) -> list[dict]:
    """Converte una serie di prezzi applicando il cambio della stessa settimana.

    Per un compratore italiano la valuta di lettura è l'euro: un prezzo in
    corone può salire mentre in euro scende. La conversione usa il cambio
    storico di ciascuna settimana, mai il cambio odierno applicato a tutto
    lo storico, che riscriverebbe la storia del mercato.
    """
    convertite = []
    for o in osservazioni:
        cambio = cambi_settimanali.get(o["periodo"])
        riga = dict(o)
        if o.get("valore") is not None and cambio:
            riga["valore"] = o["valore"] / cambio
            riga["cambio"] = cambio
        else:
            riga["valore"] = None
            riga["cambio"] = None
            riga["nota"] = "cambio non disponibile"
        convertite.append(riga)
    return convertite


# --------------------------------------------------------------------------
# Dal riferimento al prezzo a destino
# --------------------------------------------------------------------------


@dataclass
class CostoDestino:
    prezzo_origine: float
    prezzo_reso: float
    costo_materia_utilizzabile: float
    dettaglio: list[tuple[str, float]]


def costo_a_destino(
    prezzo_origine_kg: float,
    trasporto_kg: float = 0.0,
    altri_costi_kg: float = 0.0,
    maggiorazione_percentuale: float = 0.0,
    glassatura_percentuale: float = 0.0,
    resa_percentuale: float = 100.0,
) -> CostoDestino:
    """Dal riferimento di mercato al costo per chilogrammo utilizzabile.

    È il passaggio che nessun portale pubblico fa e che decide se
    un'offerta è conveniente:

    * la glassatura è acqua: su un congelato con il 10% di glassatura si
      paga il 10% in più per il prodotto netto;
    * la resa è ciò che resta dopo la lavorazione; un intero eviscerato
      che diventa filetto senza pelle rende molto meno del peso acquistato;
    * trasporto e maggiorazioni vanno aggiunti prima, non dopo.

    Il risultato è una simulazione sui parametri di chi la imposta, non un
    dato di fonte: va mostrata sempre come tale.
    """
    if not 0 < resa_percentuale <= 400:
        raise ValueError("la resa deve essere compresa fra 0 e 400")
    if not 0 <= glassatura_percentuale < 100:
        raise ValueError("la glassatura deve essere compresa fra 0 e 100")

    dettaglio = [("Riferimento all'origine", prezzo_origine_kg)]
    prezzo = prezzo_origine_kg

    if maggiorazione_percentuale:
        aggiunta = prezzo * maggiorazione_percentuale / 100
        prezzo += aggiunta
        dettaglio.append((f"Maggiorazione {maggiorazione_percentuale:g}%", aggiunta))
    if trasporto_kg:
        prezzo += trasporto_kg
        dettaglio.append(("Trasporto", trasporto_kg))
    if altri_costi_kg:
        prezzo += altri_costi_kg
        dettaglio.append(("Altri costi", altri_costi_kg))

    prezzo_reso = prezzo
    dettaglio.append(("Costo reso a destino", prezzo_reso))

    if glassatura_percentuale:
        prezzo = prezzo / (1 - glassatura_percentuale / 100)
        dettaglio.append((f"Al netto della glassatura {glassatura_percentuale:g}%", prezzo))

    costo_utilizzabile = prezzo / (resa_percentuale / 100)
    dettaglio.append((f"Per kg utilizzabile, resa {resa_percentuale:g}%", costo_utilizzabile))

    return CostoDestino(
        prezzo_origine=prezzo_origine_kg,
        prezzo_reso=prezzo_reso,
        costo_materia_utilizzabile=costo_utilizzabile,
        dettaglio=dettaglio,
    )


# --------------------------------------------------------------------------
# Media mobile ponderata sui volumi
# --------------------------------------------------------------------------


def media_ponderata_mobile(
    osservazioni: list[dict], settimane: int = 4, minimo_settimane: int = 2
) -> list[dict]:
    """Prezzo medio delle ultime N settimane di calendario, pesato sui volumi.

    Serve per le serie doganali in cui il prezzo della singola settimana
    salta con il mix dei carichi. Per ogni settimana con dati si sommano
    gli euro e i chili delle settimane di calendario della finestra e si
    divide: una settimana con pochi chili pesa poco. Le settimane senza
    dati restano fuori dalla somma, non vengono inventate. Il risultato è
    scritto solo se la finestra contiene almeno `minimo_settimane`
    settimane con dati. La quantità resta quella della settimana.
    """
    per_periodo = {
        o["periodo"]: o for o in osservazioni
        if o.get("valore") is not None and o.get("quantita")
    }
    risultato = []
    for periodo in sorted(per_periodo):
        finestra = [
            per_periodo[s]
            for s in (isoweek.sposta(periodo, -k) for k in range(settimane))
            if s in per_periodo
        ]
        riga = dict(per_periodo[periodo])
        peso = sum(o["quantita"] for o in finestra)
        if len(finestra) >= minimo_settimane and peso > 0:
            riga["valore"] = sum(o["valore"] * o["quantita"] for o in finestra) / peso
        else:
            riga["valore"] = None
        risultato.append(riga)
    return risultato


def finestra_ponderata(osservazioni: list[dict], ultima: str, settimane: int = 4) -> dict:
    """Tonnellate e prezzo medio ponderato delle N settimane di calendario fino a `ultima`."""
    periodi = {isoweek.sposta(ultima, -k) for k in range(settimane)}
    dentro = [o for o in osservazioni
              if o["periodo"] in periodi and o.get("valore") is not None and o.get("quantita")]
    peso = sum(o["quantita"] for o in dentro)
    return {
        "tonnellate": peso if dentro else None,
        "prezzo": (sum(o["valore"] * o["quantita"] for o in dentro) / peso) if peso else None,
        "settimane_con_dati": len(dentro),
    }


# --------------------------------------------------------------------------
# Posizione stagionale al netto del livello dei prezzi
# --------------------------------------------------------------------------


def media_mobile(osservazioni: list[dict], settimane: int = 52) -> dict[str, float]:
    """Media mobile semplice del valore, per settimana, sulle ultime N osservazioni."""
    valori = [(o["periodo"], o["valore"]) for o in osservazioni if o.get("valore") is not None]
    medie = {}
    for i in range(len(valori)):
        finestra = valori[max(0, i - settimane + 1): i + 1]
        if len(finestra) >= settimane // 2:
            medie[valori[i][0]] = sum(v for _, v in finestra) / len(finestra)
    return medie


def posizione_stagionale_al_netto_del_livello(
    osservazioni: list[dict], periodo: str, settimane_media: int = 52, **argomenti
) -> PosizioneStagionale:
    """Come posizione_stagionale, ma sul rapporto prezzo / media mobile a 52 settimane.

    In un periodo di rincaro generale ogni settimana risulta "sopra la norma"
    sui prezzi nominali, e la lettura smette di dire qualcosa. Il rapporto
    con la media mobile toglie il livello e lascia la stagionalità: dice
    se questa settimana è cara *rispetto all'anno in corso*, non rispetto a
    cinque anni fa. Per chi compra contano entrambe le letture, e la pagina
    le mostra tutte e due.
    """
    medie = media_mobile(osservazioni, settimane_media)
    rapporti = [
        {"periodo": o["periodo"], "valore": o["valore"] / medie[o["periodo"]]}
        for o in osservazioni
        if o.get("valore") is not None and o["periodo"] in medie and medie[o["periodo"]]
    ]
    return posizione_stagionale(rapporti, periodo, **argomenti)
