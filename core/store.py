"""Archivio centrale delle serie storiche.

Due principi guidano lo schema:

1. Una osservazione non viene mai sovrascritta in silenzio. Le statistiche
   del commercio estero vengono riviste: se sovrascriviamo perdiamo la
   possibilità di dire "questo è il dato che era pubblicato quella
   settimana". La tabella `revisioni` conserva ogni cambiamento, così
   l'archivio resta interrogabile a una data passata.

2. Prodotto e serie sono cose distinte. Una pagina "Salmone" raccoglie più
   serie (prezzo export norvegese, import UE, prima vendita): ognuna
   conserva la propria unità, frequenza, fonte e licenza.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS serie (
    id                TEXT PRIMARY KEY,
    prodotto          TEXT NOT NULL,
    presentazione     TEXT,
    conservazione     TEXT,
    pezzatura         TEXT,
    mercato           TEXT NOT NULL,
    fase              TEXT NOT NULL,
    indicatore        TEXT NOT NULL,
    unita             TEXT NOT NULL,
    valuta            TEXT,
    frequenza         TEXT NOT NULL,
    fonte             TEXT NOT NULL,
    fonte_url         TEXT,
    licenza           TEXT,
    licenza_url       TEXT,
    elaborazione      TEXT,
    note              TEXT
);

CREATE TABLE IF NOT EXISTS osservazioni (
    serie_id          TEXT NOT NULL REFERENCES serie(id),
    periodo           TEXT NOT NULL,
    valore            REAL,
    quantita          REAL,
    prima_pubblicazione TEXT NOT NULL,
    ultimo_aggiornamento TEXT NOT NULL,
    PRIMARY KEY (serie_id, periodo)
);

CREATE TABLE IF NOT EXISTS revisioni (
    serie_id          TEXT NOT NULL,
    periodo           TEXT NOT NULL,
    valore_precedente REAL,
    valore_nuovo      REAL,
    quantita_precedente REAL,
    quantita_nuova    REAL,
    rilevata_il       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oss_serie ON osservazioni(serie_id, periodo);
CREATE INDEX IF NOT EXISTS idx_rev_serie ON revisioni(serie_id, periodo);

CREATE TABLE IF NOT EXISTS esecuzioni (
    avviata_il        TEXT NOT NULL,
    conclusa_il       TEXT,
    fonte             TEXT NOT NULL,
    esito             TEXT NOT NULL,
    nuove             INTEGER DEFAULT 0,
    riviste           INTEGER DEFAULT 0,
    messaggio         TEXT
);
"""


def adesso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@dataclass
class Osservazione:
    periodo: str
    valore: float | None
    quantita: float | None = None


@dataclass
class EsitoCarico:
    nuove: int = 0
    riviste: int = 0
    invariate: int = 0
    scartate: list[str] = None

    def __post_init__(self):
        if self.scartate is None:
            self.scartate = []


class Archivio:
    def __init__(self, percorso: str | Path):
        self.percorso = Path(percorso)
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.percorso)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # -- anagrafica -------------------------------------------------------

    def registra_serie(self, **campi) -> None:
        colonne = ", ".join(campi)
        segnaposto = ", ".join("?" for _ in campi)
        self.db.execute(
            f"INSERT OR REPLACE INTO serie ({colonne}) VALUES ({segnaposto})",
            tuple(campi.values()),
        )
        self.db.commit()

    def serie(self, serie_id: str) -> dict | None:
        riga = self.db.execute("SELECT * FROM serie WHERE id = ?", (serie_id,)).fetchone()
        return dict(riga) if riga else None

    def elenco_serie(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM serie ORDER BY id")]

    # -- carico -----------------------------------------------------------

    def carica(
        self,
        serie_id: str,
        osservazioni: list[Osservazione],
        tolleranza_revisione: float = 0.0,
    ) -> EsitoCarico:
        """Inserisce o aggiorna osservazioni tracciando le revisioni.

        `tolleranza_revisione` è la variazione relativa sotto la quale un
        cambiamento viene considerato arrotondamento della fonte e non
        registrato come revisione (resta comunque scritto il nuovo valore).
        """
        if self.serie(serie_id) is None:
            raise KeyError(f"serie non registrata: {serie_id}")

        esito = EsitoCarico()
        istante = adesso()

        for oss in osservazioni:
            if oss.valore is None and oss.quantita is None:
                esito.scartate.append(f"{oss.periodo}: nessun valore")
                continue
            if oss.valore is not None and oss.valore < 0:
                esito.scartate.append(f"{oss.periodo}: valore negativo")
                continue

            esistente = self.db.execute(
                "SELECT valore, quantita, prima_pubblicazione FROM osservazioni "
                "WHERE serie_id = ? AND periodo = ?",
                (serie_id, oss.periodo),
            ).fetchone()

            if esistente is None:
                self.db.execute(
                    "INSERT INTO osservazioni (serie_id, periodo, valore, quantita, "
                    "prima_pubblicazione, ultimo_aggiornamento) VALUES (?, ?, ?, ?, ?, ?)",
                    (serie_id, oss.periodo, oss.valore, oss.quantita, istante, istante),
                )
                esito.nuove += 1
                continue

            cambiato = _differisce(
                esistente["valore"], oss.valore, tolleranza_revisione
            ) or _differisce(esistente["quantita"], oss.quantita, tolleranza_revisione)

            if not cambiato:
                esito.invariate += 1
                continue

            self.db.execute(
                "INSERT INTO revisioni (serie_id, periodo, valore_precedente, valore_nuovo, "
                "quantita_precedente, quantita_nuova, rilevata_il) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    serie_id,
                    oss.periodo,
                    esistente["valore"],
                    oss.valore,
                    esistente["quantita"],
                    oss.quantita,
                    istante,
                ),
            )
            self.db.execute(
                "UPDATE osservazioni SET valore = ?, quantita = ?, ultimo_aggiornamento = ? "
                "WHERE serie_id = ? AND periodo = ?",
                (oss.valore, oss.quantita, istante, serie_id, oss.periodo),
            )
            esito.riviste += 1

        self.db.commit()
        return esito

    # -- lettura ----------------------------------------------------------

    def osservazioni(
        self,
        serie_id: str,
        dalla: str | None = None,
        alla: str | None = None,
        al_momento: str | None = None,
    ) -> list[dict]:
        """Serie ordinata per periodo.

        Con `al_momento` (timestamp ISO) la lettura è point-in-time:
        le revisioni successive vengono annullate e si ottiene il dato
        come era pubblicato a quella data.
        """
        condizioni, parametri = ["serie_id = ?"], [serie_id]
        if dalla:
            condizioni.append("periodo >= ?")
            parametri.append(dalla)
        if alla:
            condizioni.append("periodo <= ?")
            parametri.append(alla)
        if al_momento:
            condizioni.append("prima_pubblicazione <= ?")
            parametri.append(al_momento)

        righe = [
            dict(r)
            for r in self.db.execute(
                "SELECT periodo, valore, quantita, prima_pubblicazione, ultimo_aggiornamento "
                f"FROM osservazioni WHERE {' AND '.join(condizioni)} ORDER BY periodo",
                parametri,
            )
        ]

        if al_momento:
            righe = [self._riavvolgi(serie_id, r, al_momento) for r in righe]
        return righe

    def _riavvolgi(self, serie_id: str, riga: dict, al_momento: str) -> dict:
        """Riporta una riga al valore che aveva alla data indicata."""
        revisione = self.db.execute(
            "SELECT valore_precedente, quantita_precedente FROM revisioni "
            "WHERE serie_id = ? AND periodo = ? AND rilevata_il > ? "
            "ORDER BY rilevata_il ASC LIMIT 1",
            (serie_id, riga["periodo"], al_momento),
        ).fetchone()
        if revisione:
            riga = dict(riga)
            riga["valore"] = revisione["valore_precedente"]
            riga["quantita"] = revisione["quantita_precedente"]
            riga["riavvolta"] = True
        return riga

    def revisioni(self, serie_id: str, dalla_data: str | None = None) -> list[dict]:
        condizioni, parametri = ["serie_id = ?"], [serie_id]
        if dalla_data:
            condizioni.append("rilevata_il >= ?")
            parametri.append(dalla_data)
        return [
            dict(r)
            for r in self.db.execute(
                f"SELECT * FROM revisioni WHERE {' AND '.join(condizioni)} "
                "ORDER BY rilevata_il DESC, periodo DESC",
                parametri,
            )
        ]

    # -- diario -----------------------------------------------------------

    def registra_esecuzione(
        self, fonte: str, esito: str, nuove: int = 0, riviste: int = 0, messaggio: str = ""
    ) -> None:
        self.db.execute(
            "INSERT INTO esecuzioni (avviata_il, conclusa_il, fonte, esito, nuove, riviste, messaggio) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (adesso(), adesso(), fonte, esito, nuove, riviste, messaggio),
        )
        self.db.commit()

    def ultime_esecuzioni(self, quante: int = 20) -> list[dict]:
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM esecuzioni ORDER BY avviata_il DESC LIMIT ?", (quante,)
            )
        ]

    def chiudi(self) -> None:
        self.db.close()


def _differisce(vecchio, nuovo, tolleranza: float) -> bool:
    if vecchio is None and nuovo is None:
        return False
    if vecchio is None or nuovo is None:
        return True
    if vecchio == 0:
        return nuovo != 0
    return abs(nuovo - vecchio) / abs(vecchio) > tolleranza


def esporta_metadati(archivio: Archivio) -> str:
    return json.dumps(archivio.elenco_serie(), ensure_ascii=False, indent=2)
