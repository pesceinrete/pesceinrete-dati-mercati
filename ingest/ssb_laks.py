"""Statistics Norway - tabella 03024, esportazioni settimanali di salmone.

Che cosa contiene davvero la fonte, perché da qui dipende tutto il resto:

* è il valore statistico all'esportazione diviso le tonnellate esportate,
  non una quotazione di mercato;
* il valore è FOB alla frontiera norvegese, comprensivo di trasporto e
  assicurazione fino a quel punto, al netto di dazi e imposte;
* aggrega tutte le pezzature e tutte le destinazioni: una settimana in cui
  la Norvegia esporta più pesce piccolo mostra un prezzo medio più basso
  anche a mercato fermo;
* codici doganali: fresco 03.02.1411 e 03.02.1419, congelato 03.03.1311 e
  03.03.1319 (dal 2012; prima erano altri, la rottura di serie è nota).

Pubblicazione: mercoledì mattina. Licenza: CC BY 4.0, riuso anche
commerciale con attribuzione, link alla licenza e indicazione delle
modifiche apportate.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from core import isoweek  # noqa: E402
from core.store import Archivio, Osservazione  # noqa: E402

TABELLA = "03024"

# PxWebApi v2 (GET). L'API con i dataset pronti (/api/v0/dataset/) è stata
# dismessa il 31 dicembre 2025: non va più usata. Il formato CSV con codici
# e testi è quello verificato sulla risposta reale del servizio.
URL_V2_CSV = (
    f"https://data.ssb.no/api/pxwebapi/v2/tables/{TABELLA}/data?lang=en"
    "&valuecodes[ContentsCode]=*&valuecodes[VareGrupper2]=*&valuecodes[Tid]=*"
    "&stub=VareGrupper2,Tid,ContentsCode"
    "&outputformat=csv&outputformatparams=separatorsemicolon,usecodesandtexts"
)
URL_V2_JSON = (
    f"https://data.ssb.no/api/pxwebapi/v2/tables/{TABELLA}/data?lang=en"
    "&valuecodes[ContentsCode]=*&valuecodes[VareGrupper2]=*&valuecodes[Tid]=*"
    "&outputformat=json-stat2"
)
# ultimo ripiego: la vecchia API v0 con POST, ancora attiva
URL_V0_POST = f"https://data.ssb.no/api/v0/en/table/{TABELLA}"
INTERROGAZIONE_V0 = {
    "query": [
        {"code": "VareGrupper2", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "ContentsCode", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Tid", "selection": {"filter": "all", "values": ["*"]}},
    ],
    "response": {"format": "json-stat2"},
}

SERIE = {
    "ssb.laks.fersk.prezzo": dict(
        id="ssb.laks.fersk.prezzo",
        prodotto="Salmone atlantico d'allevamento",
        presentazione="Intero, non specificato dalla fonte",
        conservazione="Fresco o refrigerato",
        pezzatura="Tutte le pezzature aggregate",
        mercato="Esportazioni dalla Norvegia, tutte le destinazioni",
        fase="Esportazione (valore statistico FOB frontiera norvegese)",
        indicatore="Prezzo medio all'esportazione",
        unita="NOK/kg",
        valuta="NOK",
        frequenza="settimanale",
        fonte="Statistics Norway (SSB), tabella 03024",
        fonte_url="https://www.ssb.no/en/statbank/table/03024",
        licenza="CC BY 4.0",
        licenza_url="https://creativecommons.org/licenses/by/4.0/",
        elaborazione="Nessuna sul valore. Conversione in euro calcolata a parte.",
        note=(
            "Media di tutte le pezzature e destinazioni. Non è una quotazione "
            "contrattuale: il riferimento usato nei contratti fisici europei è "
            "l'indice spot su panel di esportatori, oggi SISALMONI."
        ),
    ),
    "ssb.laks.congelato.prezzo": dict(
        id="ssb.laks.congelato.prezzo",
        prodotto="Salmone atlantico d'allevamento",
        presentazione="Intero, non specificato dalla fonte",
        conservazione="Congelato",
        pezzatura="Tutte le pezzature aggregate",
        mercato="Esportazioni dalla Norvegia, tutte le destinazioni",
        fase="Esportazione (valore statistico FOB frontiera norvegese)",
        indicatore="Prezzo medio all'esportazione",
        unita="NOK/kg",
        valuta="NOK",
        frequenza="settimanale",
        fonte="Statistics Norway (SSB), tabella 03024",
        fonte_url="https://www.ssb.no/en/statbank/table/03024",
        licenza="CC BY 4.0",
        licenza_url="https://creativecommons.org/licenses/by/4.0/",
        elaborazione="Nessuna sul valore.",
        note="Volumi molto inferiori al fresco: le variazioni settimanali sono più erratiche.",
    ),
}

# Frammenti di etichetta usati per riconoscere le categorie della fonte.
# Se SSB cambia le diciture, l'ingestion si ferma con un errore esplicito
# invece di caricare la serie sbagliata in silenzio.
RICONOSCIMENTO = {
    "fresco": ("fresh", "fersk"),
    "congelato": ("frozen", "fryst", "frosset"),
    "prezzo": ("price", "pris"),
    "quantita": ("weight", "quantity", "vekt", "mengde"),
}


INTESTAZIONI = {"User-Agent": "Pesceinrete Dati e mercati (redazione@pesceinrete.com)"}


def scarica_testo(url: str, timeout: int = 90) -> str:
    richiesta = urllib.request.Request(url, headers=INTESTAZIONI)
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        grezzo = risposta.read()
    for codifica in ("utf-8", "iso-8859-1"):
        try:
            return grezzo.decode(codifica)
        except UnicodeDecodeError:
            continue
    return grezzo.decode("utf-8", errors="replace")


def scarica_json(url: str, corpo: dict | None = None, timeout: int = 90) -> dict:
    dati = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    intestazioni = dict(INTESTAZIONI)
    if corpo is not None:
        intestazioni["Content-Type"] = "application/json"
    richiesta = urllib.request.Request(url, data=dati, headers=intestazioni)
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        return json.loads(risposta.read().decode("utf-8"))


def analizza_csv(testo: str) -> dict[tuple[str, str], list[Osservazione]]:
    """Legge il CSV di PxWebApi v2 con codici e testi.

    Formato verificato sulla risposta reale:
        "VareGrupper2 - commodity group";"Tid - week";"ContentsCode - contents";"03024: ..."
        "01 - Fish-farm bred salmon, fresh or chilled";"2026U34 - 2026U34";"Kilopris - Price per kg (NOK)";73.52
    """
    import csv
    import io

    righe = list(csv.reader(io.StringIO(testo), delimiter=";"))
    if len(righe) < 2:
        raise KeyError("CSV SSB vuoto")
    per_serie: dict[str, dict[str, dict[str, float | None]]] = {}
    for riga in righe[1:]:
        if len(riga) < 4:
            continue
        merce, tempo, contenuto, valore = riga[0], riga[1], riga[2], riga[3]
        testo_merce = merce.lower()
        if any(p in testo_merce for p in RICONOSCIMENTO["fresco"]):
            conservazione = "fresco"
        elif any(p in testo_merce for p in RICONOSCIMENTO["congelato"]):
            conservazione = "congelato"
        else:
            continue
        codice_tempo = tempo.split(" - ")[0].strip()
        try:
            periodo = isoweek.da_formato_ssb(codice_tempo)
        except (ValueError, TypeError):
            continue
        testo_contenuto = contenuto.lower()
        if any(p in testo_contenuto for p in RICONOSCIMENTO["prezzo"]):
            campo = "valore"
        elif any(p in testo_contenuto for p in RICONOSCIMENTO["quantita"]):
            campo = "quantita"
        else:
            continue
        try:
            numero = float(valore.replace(",", ".")) if valore.strip() not in ("", ".", "..", ":") else None
        except ValueError:
            numero = None
        per_serie.setdefault(conservazione, {}).setdefault(periodo, {"valore": None, "quantita": None})[campo] = numero

    risultato = {}
    for conservazione, periodi in per_serie.items():
        osservazioni = [
            Osservazione(periodo=p, valore=v["valore"], quantita=v["quantita"])
            for p, v in sorted(periodi.items())
            if v["valore"] is not None or v["quantita"] is not None
        ]
        risultato[(conservazione, "prezzo")] = osservazioni
    if not risultato:
        raise KeyError("nessuna categoria fresco/congelato riconosciuta nel CSV SSB")
    return risultato


def scarica_con_ripiego() -> dict[tuple[str, str], list[Osservazione]]:
    """Tre strade, dalla più verificata alla più vecchia."""
    errori = []
    try:
        return analizza_csv(scarica_testo(URL_V2_CSV))
    except Exception as errore:  # noqa: BLE001
        errori.append(f"v2 csv: {errore}")
    try:
        return analizza(scarica_json(URL_V2_JSON))
    except Exception as errore:  # noqa: BLE001
        errori.append(f"v2 json-stat2: {errore}")
    try:
        return analizza(scarica_json(URL_V0_POST, INTERROGAZIONE_V0))
    except Exception as errore:  # noqa: BLE001
        errori.append(f"v0 post: {errore}")
    raise RuntimeError("SSB non raggiungibile su nessun endpoint: " + " | ".join(errori))


# --------------------------------------------------------------------------
# Lettura JSON-stat 2.0
# --------------------------------------------------------------------------


def _dimensioni(documento: dict) -> dict:
    return documento.get("dimension", documento)


def _etichette(dimensione: dict) -> dict[str, str]:
    categoria = dimensione["category"]
    indici = categoria["index"]
    if isinstance(indici, list):
        indici = {codice: posizione for posizione, codice in enumerate(indici)}
    etichette = categoria.get("label", {})
    return {codice: etichette.get(codice, codice) for codice in indici}


def _trova_dimensione(documento: dict, parole: tuple[str, ...]) -> str:
    """Individua una dimensione dalle etichette delle sue categorie."""
    dimensioni = _dimensioni(documento)
    for nome in documento.get("id", list(dimensioni)):
        if nome not in dimensioni or "category" not in dimensioni[nome]:
            continue
        testo = " ".join(_etichette(dimensioni[nome]).values()).lower()
        if any(parola in testo for parola in parole):
            return nome
    raise KeyError(f"nessuna dimensione riconosciuta per {parole}")


def _dimensione_tempo(documento: dict) -> str:
    dimensioni = _dimensioni(documento)
    for nome, contenuto in dimensioni.items():
        if isinstance(contenuto, dict) and contenuto.get("link", {}).get("describedby"):
            continue
        if nome.lower() in ("tid", "time"):
            return nome
    for nome in documento.get("role", {}).get("time", []):
        return nome
    raise KeyError("dimensione temporale non trovata")


def analizza(documento: dict) -> dict[tuple[str, str], list[Osservazione]]:
    """Restituisce le osservazioni per (conservazione, indicatore)."""
    dimensioni = _dimensioni(documento)
    ordine = documento.get("id") or documento.get("size") and list(dimensioni)
    misure = documento["size"]
    valori = documento["value"]

    nome_tempo = _dimensione_tempo(documento)
    nome_merce = _trova_dimensione(
        documento, RICONOSCIMENTO["fresco"] + RICONOSCIMENTO["congelato"]
    )
    nome_contenuto = _trova_dimensione(
        documento, RICONOSCIMENTO["prezzo"] + RICONOSCIMENTO["quantita"]
    )

    codici = {nome: list(_etichette(dimensioni[nome])) for nome in ordine}
    etichette = {nome: _etichette(dimensioni[nome]) for nome in ordine}

    def valore_a(posizioni: dict[str, int]):
        indice = 0
        for nome, dimensione in zip(ordine, misure):
            indice = indice * dimensione + posizioni[nome]
        if isinstance(valori, dict):
            return valori.get(str(indice))
        return valori[indice] if indice < len(valori) else None

    def classifica(testo: str, gruppo: str) -> bool:
        return any(parola in testo.lower() for parola in RICONOSCIMENTO[gruppo])

    risultato: dict[tuple[str, str], list[Osservazione]] = {}

    for posizione_merce, codice_merce in enumerate(codici[nome_merce]):
        testo_merce = etichette[nome_merce][codice_merce]
        if classifica(testo_merce, "fresco"):
            conservazione = "fresco"
        elif classifica(testo_merce, "congelato"):
            conservazione = "congelato"
        else:
            continue

        indici_contenuto = {}
        for posizione_c, codice_c in enumerate(codici[nome_contenuto]):
            testo_c = etichette[nome_contenuto][codice_c]
            if classifica(testo_c, "prezzo"):
                indici_contenuto["prezzo"] = posizione_c
            elif classifica(testo_c, "quantita"):
                indici_contenuto["quantita"] = posizione_c
        if "prezzo" not in indici_contenuto:
            raise KeyError("contenuto 'prezzo' non riconosciuto nella tabella SSB")

        osservazioni = []
        for posizione_tempo, codice_tempo in enumerate(codici[nome_tempo]):
            base = {n: 0 for n in ordine}
            base[nome_merce] = posizione_merce
            base[nome_tempo] = posizione_tempo

            base[nome_contenuto] = indici_contenuto["prezzo"]
            prezzo = valore_a(base)

            quantita = None
            if "quantita" in indici_contenuto:
                base[nome_contenuto] = indici_contenuto["quantita"]
                quantita = valore_a(base)

            if prezzo is None and quantita is None:
                continue
            osservazioni.append(
                Osservazione(
                    periodo=isoweek.da_formato_ssb(codice_tempo),
                    valore=prezzo,
                    quantita=quantita,
                )
            )
        risultato[(conservazione, "prezzo")] = osservazioni

    if not risultato:
        raise KeyError(
            "nessuna categoria fresco/congelato riconosciuta: le etichette SSB "
            "sono cambiate, aggiornare RICONOSCIMENTO"
        )
    return risultato


# --------------------------------------------------------------------------
# Controlli
# --------------------------------------------------------------------------


def controlla(osservazioni: list[Osservazione], etichetta: str) -> list[str]:
    """Verifiche minime prima di scrivere in archivio."""
    problemi = []
    periodi = [o.periodo for o in osservazioni]

    if len(periodi) != len(set(periodi)):
        problemi.append(f"{etichetta}: periodi duplicati")
    if periodi != sorted(periodi):
        problemi.append(f"{etichetta}: periodi non ordinati")

    prezzi = [o.valore for o in osservazioni if o.valore is not None]
    if not prezzi:
        problemi.append(f"{etichetta}: nessun prezzo valido")
        return problemi
    if min(prezzi) <= 0:
        problemi.append(f"{etichetta}: prezzi non positivi")

    ultimi = [o for o in osservazioni[-52:] if o.valore]
    for precedente, corrente in zip(ultimi, ultimi[1:]):
        if precedente.valore and abs(corrente.valore - precedente.valore) / precedente.valore > 0.35:
            problemi.append(
                f"{etichetta}: salto superiore al 35% fra {precedente.periodo} e "
                f"{corrente.periodo} ({precedente.valore} -> {corrente.valore}), da verificare"
            )
    return problemi


def esegui(percorso_db: str, solo_controllo: bool = False) -> int:
    archivio = Archivio(percorso_db)
    for definizione in SERIE.values():
        archivio.registra_serie(**definizione)

    try:
        serie_lette = scarica_con_ripiego()
    except Exception as errore:  # noqa: BLE001
        archivio.registra_esecuzione("SSB 03024", "errore", messaggio=str(errore)[:900])
        print(f"Scaricamento fallito: {errore}", file=sys.stderr)
        print("Resta pubblicata l'ultima versione valida.", file=sys.stderr)
        return 1

    mappa = {
        ("fresco", "prezzo"): "ssb.laks.fersk.prezzo",
        ("congelato", "prezzo"): "ssb.laks.congelato.prezzo",
    }

    totale_nuove = totale_riviste = 0
    tutti_i_problemi: list[str] = []

    for chiave, osservazioni in serie_lette.items():
        serie_id = mappa.get(chiave)
        if not serie_id:
            continue
        problemi = controlla(osservazioni, serie_id)
        tutti_i_problemi += problemi
        if solo_controllo:
            print(f"{serie_id}: {len(osservazioni)} settimane, "
                  f"da {osservazioni[0].periodo} a {osservazioni[-1].periodo}")
            continue
        esito = archivio.carica(serie_id, osservazioni, tolleranza_revisione=0.0005)
        totale_nuove += esito.nuove
        totale_riviste += esito.riviste
        print(
            f"{serie_id}: {esito.nuove} nuove, {esito.riviste} riviste, "
            f"{esito.invariate} invariate, {len(esito.scartate)} scartate"
        )

    for problema in tutti_i_problemi:
        print(f"  da verificare: {problema}", file=sys.stderr)

    if not solo_controllo:
        archivio.registra_esecuzione(
            "SSB 03024",
            "completata" if not tutti_i_problemi else "completata con avvisi",
            nuove=totale_nuove,
            riviste=totale_riviste,
            messaggio="; ".join(tutti_i_problemi)[:1000],
        )
    archivio.chiudi()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument(
        "--controllo",
        action="store_true",
        help="scarica e verifica senza scrivere in archivio",
    )
    argomenti = parser.parse_args()
    raise SystemExit(esegui(argomenti.db, argomenti.controllo))
