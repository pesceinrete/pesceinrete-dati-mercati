"""Dice se dall'istante indicato sono entrati dati nuovi o rivisti.

Serve al ciclo automatico per pubblicare solo quando serve. L'archivio
può essere interrogato più volte al giorno senza costi: è la
pubblicazione che deve avvenire una volta sola, quando la fonte ha
davvero emesso qualcosa.

    python strumenti/novita.py --db dati/archivio.sqlite --dal 2026-09-17T06:00:00

Stampa una riga per fonte e termina con `novita=si` o `novita=no`, in un
formato che GitHub Actions legge come output di passo.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def esegui(percorso_db: str, dal: str) -> int:
    if not Path(percorso_db).exists():
        print("novita=no")
        return 0
    db = sqlite3.connect(percorso_db)
    db.row_factory = sqlite3.Row
    righe = db.execute(
        "SELECT fonte, esito, nuove, riviste, messaggio FROM esecuzioni "
        "WHERE avviata_il >= ? ORDER BY avviata_il",
        (dal,),
    ).fetchall()

    totale_nuove = sum(r["nuove"] or 0 for r in righe)
    totale_riviste = sum(r["riviste"] or 0 for r in righe)
    errori = [r for r in righe if r["esito"] == "errore"]

    for r in righe:
        print(f"{r['fonte']}: {r['esito']}, {r['nuove']} nuove, {r['riviste']} riviste")

    novita = "si" if (totale_nuove or totale_riviste) else "no"
    riassunto = f"{totale_nuove} nuove, {totale_riviste} riviste"
    if errori:
        riassunto += f", {len(errori)} fonti in errore"

    print(f"novita={novita}")
    print(f"riassunto={riassunto}")

    uscita = os.environ.get("GITHUB_OUTPUT")
    if uscita:
        with open(uscita, "a", encoding="utf-8") as f:
            f.write(f"novita={novita}\n")
            f.write(f"riassunto={riassunto}\n")
            f.write(f"errori={len(errori)}\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--dal", required=True, help="istante ISO UTC di inizio esecuzione")
    a = parser.parse_args()
    sys.exit(esegui(a.db, a.dal))
