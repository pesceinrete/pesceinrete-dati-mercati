"""Bozza del bollettino settimanale.

Un bollettino che ripete i numeri già visibili nella pagina non merita di
essere letto. Questo modulo cerca solo i fatti che il lettore non vede da
solo guardando il grafico, e li scrive senza attribuire cause.

Le regole sono cinque:

1. il prezzo entra o esce dalla fascia alta o bassa della stagione;
2. il movimento va in direzione contraria a quella abituale del periodo;
3. prezzo e cambio si muovono in modo opposto, cioè il movimento in euro
   non è un movimento di mercato;
4. il volume della settimana è fuori dall'intervallo abituale;
5. la fonte ha rivisto settimane già pubblicate.

Se nessuna regola scatta, il bollettino lo dice. "Settimana senza
movimenti rilevanti" è un'informazione utile per chi deve decidere se
comprare adesso o aspettare.

Quello che esce di qui è una bozza per la redazione, non un testo da
pubblicare senza rileggerlo: le cause le mette chi conosce il mercato,
non un calcolo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import isoweek, metrics
from .testi import BOLLETTINO, soglie


@dataclass
class Osservazione:
    titolo: str
    testo: str
    rilievo: str = "normale"  # normale | alto


@dataclass
class Bollettino:
    periodo: str
    lingua: str = "it"
    voci: list[Osservazione] = field(default_factory=list)

    @property
    def vuoto(self) -> bool:
        return not self.voci

    def markdown(self) -> str:
        t = BOLLETTINO[self.lingua]
        righe = ["# " + t["intestazione"].format(periodo=self.periodo), ""]
        if self.vuoto:
            righe.append(t["quiete"])
        for voce in self.voci:
            righe += [f"## {voce.titolo}", "", voce.testo, ""]
        righe += ["---", "", t["coda"]]
        return "\n".join(righe)


def _percento(valore: float, lingua: str) -> str:
    testo = f"{abs(valore):.1f}%"
    return testo.replace(".", ",") if lingua == "it" else testo


def _verso(valore: float, lingua: str) -> str:
    return BOLLETTINO[lingua]["verso"]["su" if valore > 0 else "giu"]


def _tonnellate(valore: float, lingua: str) -> str:
    testo = f"{valore:,.0f}"
    return testo.replace(",", ".") if lingua == "it" else testo


def componi(
    in_euro: list[dict],
    in_valuta_origine: list[dict],
    periodo: str,
    revisioni: list[dict] | None = None,
    nome_prodotto: str = "Il prodotto",
    lingua: str = "it",
) -> Bollettino:
    if lingua not in BOLLETTINO:
        lingua = "it"
    bollettino = Bollettino(periodo=periodo, lingua=lingua)
    valori = {o["periodo"]: o for o in in_euro if o.get("valore") is not None}
    if periodo not in valori:
        return bollettino

    _regola_soglia_stagionale(bollettino, in_euro, periodo, nome_prodotto)
    _regola_controstagione(bollettino, in_euro, periodo)
    _regola_cambio(bollettino, in_euro, in_valuta_origine, periodo)
    _regola_volumi(bollettino, in_euro, periodo)
    _regola_revisioni(bollettino, revisioni or [])

    bollettino.voci.sort(key=lambda v: 0 if v.rilievo == "alto" else 1)
    return bollettino


# --------------------------------------------------------------------------


def _regola_soglia_stagionale(bollettino, serie, periodo, nome_prodotto):
    adesso = metrics.posizione_stagionale(serie, periodo)
    prima = metrics.posizione_stagionale(serie, isoweek.sposta(periodo, -4))
    if not adesso.attendibile or adesso.percentile is None or prima.percentile is None:
        return

    s = soglie()["stagionale"]

    def fascia(percentile):
        if percentile >= s["fascia_alta"]:
            return "alta"
        if percentile <= s["fascia_bassa"]:
            return "bassa"
        return "centrale"

    da, a = fascia(prima.percentile), fascia(adesso.percentile)
    if da == a:
        return

    t = BOLLETTINO[bollettino.lingua]
    bollettino.voci.append(
        Osservazione(
            titolo=t["soglia_titolo"].format(prodotto=nome_prodotto),
            testo=t["soglia_testo"].format(
                da=t["fascia"][da], a=t["fascia"][a], percentile=adesso.percentile,
                n=adesso.osservazioni_confronto,
                primo=adesso.anni_usati[0], ultimo=adesso.anni_usati[-1],
            ),
            rilievo="alto" if a in ("alta", "bassa") else "normale",
        )
    )


def _regola_controstagione(bollettino, serie, periodo):
    """Il movimento va nella direzione opposta a quella abituale del periodo."""
    valori = {o["periodo"]: o["valore"] for o in serie if o.get("valore") is not None}
    corrente = valori.get(periodo)
    precedente = valori.get(isoweek.sposta(periodo, -1))
    if corrente is None or not precedente:
        return
    variazione = (corrente - precedente) / precedente * 100
    sb = soglie()["bollettino"]
    if abs(variazione) < sb["variazione_minima_settimana"]:
        return

    anno, settimana = isoweek.scomponi(periodo)
    abituali = []
    for indietro in range(1, 6):
        chiave_corrente = isoweek.stessa_settimana_anno_precedente(periodo, indietro)
        chiave_prima = isoweek.sposta(chiave_corrente, -1)
        a, b = valori.get(chiave_corrente), valori.get(chiave_prima)
        if a is not None and b:
            abituali.append((a - b) / b * 100)
    if len(abituali) < 3:
        return

    media = sum(abituali) / len(abituali)
    if abs(media) < sb["movimento_abituale_minimo"] or (media > 0) == (variazione > 0):
        return

    lingua = bollettino.lingua
    t = BOLLETTINO[lingua]
    bollettino.voci.append(
        Osservazione(
            titolo=t["contro_titolo"],
            testo=t["contro_testo"].format(
                settimana=settimana, verso=_verso(variazione, lingua),
                variazione=_percento(variazione, lingua), anni=len(abituali),
                verso_media=_verso(media, lingua), media=_percento(media, lingua),
            ),
            rilievo="alto",
        )
    )


def _regola_cambio(bollettino, in_euro, in_origine, periodo):
    """Il prezzo in euro si muove per il cambio, non per il mercato."""
    def variazione(serie):
        valori = {o["periodo"]: o["valore"] for o in serie if o.get("valore") is not None}
        corrente = valori.get(periodo)
        precedente = valori.get(isoweek.sposta(periodo, -1))
        if corrente is None or not precedente:
            return None
        return (corrente - precedente) / precedente * 100

    euro, origine = variazione(in_euro), variazione(in_origine)
    if euro is None or origine is None:
        return
    minima = soglie()["bollettino"]["cambio_divergenza_minima"]
    if abs(euro) < minima and abs(origine) < minima:
        return
    if (euro > 0) == (origine > 0):
        return

    lingua = bollettino.lingua
    t = BOLLETTINO[lingua]
    bollettino.voci.append(
        Osservazione(
            titolo=t["cambio_titolo"],
            testo=t["cambio_testo"].format(
                verso_origine=_verso(origine, lingua), origine=_percento(origine, lingua),
                verso_euro=_verso(euro, lingua), euro=_percento(euro, lingua),
            ),
            rilievo="alto",
        )
    )


def _regola_volumi(bollettino, serie, periodo):
    volumi = [
        {"periodo": o["periodo"], "valore": o["quantita"]}
        for o in serie
        if o.get("quantita")
    ]
    if not volumi:
        return
    posizione = metrics.posizione_stagionale(volumi, periodo)
    if not posizione.attendibile or posizione.percentile is None:
        return
    sb = soglie()["bollettino"]
    if sb["volumi_fascia_bassa"] < posizione.percentile < sb["volumi_fascia_alta"]:
        return

    corrente = next((v["valore"] for v in volumi if v["periodo"] == periodo), None)
    if corrente is None:
        return
    alto = posizione.percentile >= sb["volumi_fascia_alta"]
    lingua = bollettino.lingua
    t = BOLLETTINO[lingua]
    bollettino.voci.append(
        Osservazione(
            titolo=t["volumi_titolo"],
            testo=t["volumi_testo"].format(
                corrente=_tonnellate(corrente, lingua),
                posizione=t["sopra"] if alto else t["sotto"],
                minimo=_tonnellate(posizione.minimo, lingua),
                massimo=_tonnellate(posizione.massimo, lingua),
            ),
        )
    )


def _regola_revisioni(bollettino, revisioni):
    recenti = revisioni[:12]
    if not recenti:
        return
    periodi = sorted({r["periodo"] for r in recenti})
    t = BOLLETTINO[bollettino.lingua]
    bollettino.voci.append(
        Osservazione(
            titolo=t["revisioni_titolo"],
            testo=t["revisioni_testo"].format(
                n=len(periodi), elenco=", ".join(periodi[:8]),
                altre=t["altre"] if len(periodi) > 8 else t["punto"],
            ),
        )
    )
