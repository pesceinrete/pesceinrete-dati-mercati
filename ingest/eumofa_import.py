"""EUMOFA - importazioni settimanali in Italia da paesi extra-UE.

È la fonte dei prezzi settimanali di tutte le specie tranne il salmone.
EUMOFA, l'osservatorio della Commissione europea, pubblica ogni settimana
le dichiarazioni doganali di importazione (sistema Surveillance della DG
TAXUD) per codice doganale a otto cifre, Stato membro importatore e paese
di provenienza: peso netto e valore. Da qui si ricava, per ogni specie,
il valore medio di quello che entra in Italia da ciascuna provenienza.

Cosa è e cosa non è
-------------------
* È un censimento, non un campione: tutte le dichiarazioni.
* Non è una quotazione: è valore dichiarato diviso peso, trasporto fino
  alla frontiera compreso.
* Copre solo gli arrivi da fuori Unione. Grecia, Croazia e Spagna stanno
  nel dato mensile Eurostat (ingest/eurostat_comext.py).
* I totali annui coincidono con quelli di Eurostat Comext per l'Italia
  (verificato sul 2025 per orata, spigola, polpo e gambero).

Scaricamento
------------
I file stanno a un indirizzo pubblico e fisso, uno per anno, che la
fonte riscrive a ogni aggiornamento. Si scaricano l'anno in corso e i
precedenti a partire da ANNO_INIZIO, perché la fonte rivede anche gli
anni passati. Un file che non è cambiato dall'ultima volta (stessa
impronta ETag) non viene riscaricato.

Se l'indirizzo dovesse cambiare, il modulo fallisce in modo dichiarato e
la pagina resta sull'ultima settimana valida. Rimedio manuale: scaricare
il file dell'anno dal Bulk Download di EUMOFA ("Weekly-Import") e
caricarlo, senza rinominarlo, in dati/manuale/: viene letto quando la
fonte non risponde. In alternativa, lanciare questo modulo con --file.

Settimane complete
------------------
L'ultima settimana presente nel file è sempre parziale: le dichiarazioni
continuano ad arrivare. Una settimana viene pubblicata solo se

1. nel file esiste già una settimana successiva (vale per l'anno in
   corso: negli anni chiusi l'ultima settimana è definitiva), e
2. ha almeno il 70% delle righe di una settimana tipica dello stesso anno.

La seconda regola scarta anche le settimane bucate che la fonte ha negli
anni 2023 e 2024 (quasi tutte a cavallo di fine mese). Una settimana
scartata resta un buco: nessuna interpolazione.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.prodotti import (  # noqa: E402
    FONTI_PREZZO, MERCATO_EUMOFA, PAESI, PAESI_EUMOFA, con_eumofa, serie_eumofa,
)
from core import isoweek  # noqa: E402
from core.store import Archivio, Osservazione  # noqa: E402

BASE = os.environ.get("EUMOFA_BASE", "https://dev-eumofa-bulk.s3.eu-west-1.amazonaws.com/")
NOME_FILE = "{anno}_EU Import from third countries.csv"
ANNO_INIZIO = 2023
IMPORTATORE = "Italy"
INTESTAZIONE = ["year", "week", "issuer", "origin", "goods", "volume(Kg)", "value(EUR)"]
SOGLIA_COMPLETEZZA = 0.70
MINIMO_SETTIMANE_PER_MEDIANA = 8
AGENTE = "Pesceinrete Dati e mercati (+https://www.pesceinrete.com/dati-mercati/)"


# --------------------------------------------------------------------------
# Serie
# --------------------------------------------------------------------------


def definizioni() -> dict[str, dict]:
    """Una serie per ogni coppia specie-provenienza del registro."""
    fonte = FONTI_PREZZO["eumofa"]
    risultato = {}
    for prodotto in con_eumofa():
        voce = prodotto["eumofa"]
        for partner in dict.fromkeys([voce["principale"], "WORLD", *voce.get("altre", [])]):
            serie_id = serie_eumofa(prodotto, partner)
            if partner == "WORLD":
                mercato = MERCATO_EUMOFA
            else:
                mercato = f"{MERCATO_EUMOFA}: {PAESI[partner][0]}"
            risultato[serie_id] = {
                "prodotto_id": prodotto["id"],
                "partner": partner,
                "codici": tuple(voce["codici"]),
                "anagrafica": dict(
                    id=serie_id,
                    prodotto=voce["prodotto"],
                    presentazione=voce["presentazione"],
                    conservazione=voce["conservazione"],
                    pezzatura="Tutte le pezzature",
                    mercato=mercato,
                    fase="Importazione (valore dichiarato in dogana)",
                    indicatore="Valore unitario delle importazioni",
                    unita="EUR/kg",
                    valuta="EUR",
                    frequenza="settimanale",
                    fonte=fonte["nome"],
                    fonte_url=fonte["url"],
                    licenza=fonte["licenza"],
                    licenza_url=fonte["licenza_url"],
                    elaborazione=(
                        "Valore dichiarato diviso peso netto, somma dei codici doganali della "
                        "specie. Sono pubblicate solo le settimane complete alla fonte."
                    ),
                    note=(
                        "Non è una quotazione: è il valore medio dichiarato in dogana, trasporto "
                        "fino alla frontiera compreso. Copre solo gli arrivi da fuori Unione; la "
                        "fonte rivede i dati anche a distanza di mesi."
                    ),
                ),
            }
    return risultato


# --------------------------------------------------------------------------
# Scaricamento
# --------------------------------------------------------------------------


def indirizzo(anno: int) -> str:
    return BASE + urllib.parse.quote(NOME_FILE.format(anno=anno))


def scarica(anno: int, impronta_nota: str | None = None, timeout: int = 300):
    """Restituisce (contenuto, impronta). Contenuto None se il file non è cambiato."""
    intestazioni = {"User-Agent": AGENTE}
    if impronta_nota:
        # un ETag sta fra virgolette; altrimenti l'impronta è una data
        campo = "If-None-Match" if impronta_nota.lstrip("W/").startswith('"') else "If-Modified-Since"
        intestazioni[campo] = impronta_nota
    richiesta = urllib.request.Request(indirizzo(anno), headers=intestazioni)
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            impronta = risposta.headers.get("ETag") or risposta.headers.get("Last-Modified")
            return risposta.read(), impronta
    except urllib.error.HTTPError as errore:
        if errore.code == 304:
            return None, impronta_nota
        raise


# --------------------------------------------------------------------------
# Lettura
# --------------------------------------------------------------------------


def leggi(contenuto: bytes, serie: dict[str, dict]) -> dict:
    """Legge un file annuale e lo riduce alle serie del registro.

    Restituisce le righe per settimana (tutti gli Stati: servono per
    giudicare la completezza), le righe italiane, e per ogni serie i chili
    e gli euro per settimana.
    """
    testo = contenuto.decode("utf-8-sig", errors="replace")
    righe = csv.reader(io.StringIO(testo), delimiter="~")
    intestazione = [c.strip() for c in next(righe, [])]
    if intestazione != INTESTAZIONE:
        raise ValueError(
            f"il file EUMOFA ha cambiato struttura. Intestazione trovata: {intestazione}; "
            f"attesa: {INTESTAZIONE}"
        )

    # provenienza come la scrive la fonte -> codici paese del registro
    da_nome = {nome: codice for codice, nomi in PAESI_EUMOFA.items() for nome in nomi}
    piano = [(sid, v["codici"], v["partner"]) for sid, v in serie.items()]

    per_settimana: Counter = Counter()
    italiane = 0
    somme: dict[str, dict[str, list[float]]] = {sid: {} for sid in serie}
    provenienze_viste: set[str] = set()

    for riga in righe:
        if len(riga) != 7:
            continue
        try:
            periodo = isoweek.chiave(int(riga[0]), int(riga[1]))
        except ValueError:
            continue
        per_settimana[periodo] += 1
        if riga[2] != IMPORTATORE:
            continue
        italiane += 1
        codice = riga[4].split("-", 1)[0].strip()
        paese = da_nome.get(riga[3])
        chili, euro = _numero(riga[5]), _numero(riga[6])
        if not chili or chili <= 0 or euro is None:
            continue
        for sid, prefissi, partner in piano:
            if not codice.startswith(prefissi):
                continue
            provenienze_viste.add(riga[3])
            if partner != "WORLD" and paese != partner:
                continue
            voce = somme[sid].setdefault(periodo, [0.0, 0.0])
            voce[0] += chili
            voce[1] += euro
    return {"per_settimana": per_settimana, "italiane": italiane, "somme": somme,
            "provenienze": provenienze_viste}


def _numero(grezzo: str) -> float | None:
    try:
        return float(grezzo)
    except (TypeError, ValueError):
        return None


def settimane_complete(per_settimana: Counter, tipica_di_riserva: float | None = None,
                       anno_chiuso: bool = False) -> tuple[set[str], float]:
    """Le settimane pubblicabili di un file annuale e il numero tipico di righe.

    `anno_chiuso` vale per i file degli anni passati: lì l'ultima settimana
    non è "in corso", quindi conta solo la soglia sulle righe.
    """
    if not per_settimana:
        return set(), tipica_di_riserva or 0.0
    ordinate = sorted(per_settimana)
    conteggi = sorted(per_settimana.values())
    if len(conteggi) >= MINIMO_SETTIMANE_PER_MEDIANA or not tipica_di_riserva:
        tipica = float(conteggi[len(conteggi) // 2])
    else:
        # a inizio anno le settimane sono troppo poche: vale l'anno prima
        tipica = float(tipica_di_riserva)
    ultima = None if anno_chiuso else ordinate[-1]
    complete = {
        s for s in ordinate
        if s != ultima and per_settimana[s] >= SOGLIA_COMPLETEZZA * tipica
    }
    return complete, tipica


def osservazioni(somme: dict[str, list[float]], complete: set[str]) -> list[Osservazione]:
    risultato = []
    for periodo in sorted(somme):
        chili, euro = somme[periodo]
        if periodo not in complete or chili <= 0:
            continue
        risultato.append(Osservazione(periodo=periodo, valore=euro / chili, quantita=chili / 1000.0))
    return risultato


# --------------------------------------------------------------------------
# Stato fra un'esecuzione e l'altra
# --------------------------------------------------------------------------


def leggi_stato(percorso: Path) -> dict:
    if percorso.exists():
        try:
            return json.loads(percorso.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {"impronte": {}, "tipiche": {}}


# --------------------------------------------------------------------------


def esegui(percorso_db: str, file_locali: list[str] | None = None, solo_controllo: bool = False,
           anno_inizio: int = ANNO_INIZIO, forza: bool = False) -> int:
    serie = definizioni()
    archivio = Archivio(percorso_db)
    percorso_stato = Path(percorso_db).parent / "eumofa_stato.json"
    stato = leggi_stato(percorso_stato)
    uscita = 0
    nuove = riviste = 0
    righe_riepilogo = []
    anno_corrente = date.today().year

    if not solo_controllo:
        for voce in serie.values():
            archivio.registra_serie(**voce["anagrafica"])

    # (anno, contenuto) da leggere: da file locali oppure dalla rete
    da_leggere: list[tuple[str, bytes, str | None]] = []
    if file_locali:
        for nome in file_locali:
            percorso = Path(nome)
            if not percorso.exists():
                print(f"File non trovato: {percorso}", file=sys.stderr)
                return 1
            da_leggere.append((percorso.name[:4], percorso.read_bytes(), None))
    else:
        for anno in range(anno_inizio, anno_corrente + 1):
            nota = None if (forza or solo_controllo) else stato["impronte"].get(str(anno))
            try:
                contenuto, impronta = scarica(anno, nota)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as errore:
                # a gennaio il file del nuovo anno può non esistere ancora
                assente = isinstance(errore, urllib.error.HTTPError) and errore.code in (403, 404)
                if assente and anno == anno_corrente and date.today().month == 1:
                    print(f"EUMOFA {anno}: file non ancora pubblicato")
                    continue
                manuale = Path(percorso_db).parent / "manuale" / NOME_FILE.format(anno=anno)
                if manuale.exists():
                    print(f"EUMOFA {anno}: fonte non raggiungibile ({errore}), uso il file caricato a mano")
                    da_leggere.append((str(anno), manuale.read_bytes(), None))
                    continue
                messaggio = f"scaricamento fallito ({errore}). Indirizzo: {indirizzo(anno)}"
                print(f"EUMOFA {anno}: {messaggio}", file=sys.stderr)
                if not solo_controllo:
                    archivio.registra_esecuzione(f"EUMOFA {anno}", "errore", messaggio=messaggio)
                uscita = 1
                continue
            if contenuto is None:
                print(f"EUMOFA {anno}: invariato alla fonte")
                continue
            da_leggere.append((str(anno), contenuto, impronta))

    for anno, contenuto, impronta in sorted(da_leggere):
        try:
            letto = leggi(contenuto, serie)
        except ValueError as errore:
            print(f"EUMOFA {anno}: {errore}", file=sys.stderr)
            if not solo_controllo:
                archivio.registra_esecuzione(f"EUMOFA {anno}", "errore", messaggio=str(errore))
            uscita = 1
            continue

        riserva = stato["tipiche"].get(str(int(anno) - 1)) if anno.isdigit() else None
        chiuso = anno.isdigit() and int(anno) < anno_corrente
        complete, tipica = settimane_complete(letto["per_settimana"], riserva, anno_chiuso=chiuso)
        if not complete and not chiuso and len(letto["per_settimana"]) <= 3:
            # inizio anno: il file esiste ma non ha ancora una settimana chiusa
            print(f"EUMOFA {anno}: file appena avviato, nessuna settimana ancora completa")
            continue
        if letto["italiane"] == 0 or not complete:
            messaggio = (f"nessuna riga per '{IMPORTATORE}' o nessuna settimana completa "
                         f"({sum(letto['per_settimana'].values())} righe nel file)")
            print(f"EUMOFA {anno}: {messaggio}", file=sys.stderr)
            if not solo_controllo:
                archivio.registra_esecuzione(f"EUMOFA {anno}", "errore", messaggio=messaggio)
            uscita = 1
            continue

        presenti = sorted(letto["per_settimana"])
        scartate = [s[5:] for s in presenti if s not in complete]
        vuote = []
        nuove_anno = riviste_anno = 0
        for serie_id, voce in serie.items():
            oss = osservazioni(letto["somme"][serie_id], complete)
            if not oss:
                # solo la provenienza principale è un allarme: le altre possono mancare
                principale = serie_id == next(
                    p["prezzo"]["serie"] for p in con_eumofa() if p["id"] == voce["prodotto_id"])
                if principale:
                    vuote.append(serie_id)
                continue
            if solo_controllo:
                continue
            esito = archivio.carica(serie_id, oss, tolleranza_revisione=0.0005)
            nuove_anno += esito.nuove
            riviste_anno += esito.riviste

        ultima = max(complete)
        messaggio = f"ultima settimana completa {ultima[5:]}; scartate perché incomplete: " \
                    f"{', '.join(scartate) if scartate else 'nessuna'}"
        if vuote:
            messaggio += f"; SERIE VUOTE: {', '.join(vuote)} (provenienze nel file: " \
                         f"{', '.join(sorted(letto['provenienze'])[:12])})"
        print(f"EUMOFA {anno}: {sum(letto['per_settimana'].values())} righe, {letto['italiane']} italiane, "
              f"{len(complete)} settimane complete su {len(presenti)}, {nuove_anno} nuove, "
              f"{riviste_anno} riviste. {messaggio}")
        righe_riepilogo.append((anno, len(complete), len(presenti), ultima))
        nuove += nuove_anno
        riviste += riviste_anno

        if not solo_controllo:
            archivio.registra_esecuzione(
                f"EUMOFA {anno}", "completata con avvisi" if vuote else "completata",
                nuove=nuove_anno, riviste=riviste_anno, messaggio=messaggio,
            )
            stato["tipiche"][anno] = tipica
            if impronta:
                stato["impronte"][anno] = impronta

    if solo_controllo:
        for serie_id in sorted(serie):
            print(f"  serie prevista: {serie_id}")
    else:
        percorso_stato.write_text(json.dumps(stato, indent=1, sort_keys=True), encoding="utf-8")
    archivio.chiudi()
    return uscita


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--file", action="append", help="file annuale scaricato a mano (ripetibile)")
    parser.add_argument("--controllo", action="store_true", help="interroga la fonte senza scrivere")
    parser.add_argument("--dal", type=int, default=ANNO_INIZIO)
    parser.add_argument("--forza", action="store_true", help="riscarica anche i file invariati")
    a = parser.parse_args()
    raise SystemExit(esegui(a.db, a.file, a.controllo, a.dal, a.forza))
