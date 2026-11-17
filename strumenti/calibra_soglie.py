"""Quante volte l'anno scatta ogni regola, sulla storia che c'è in archivio.

Le soglie del bollettino sono fissate a giudizio. Questo strumento le
mette alla prova: rilegge la storia settimana per settimana come se la
pagina fosse stata pubblicata ogni volta, e conta quante volte ogni regola
avrebbe prodotto una voce. Un bollettino che grida "fuori norma" ogni due
settimane è un bollettino che nessuno legge; uno che non dice mai niente
non serve. Il bersaglio ragionevole, per specie, è fra 6 e 15 voci l'anno
per la stagionalità e fra 3 e 8 per i volumi.

    python strumenti/calibra_soglie.py --db dati/archivio.sqlite
    python strumenti/calibra_soglie.py --db dati/archivio.sqlite --fascia-alta 85 --fascia-bassa 15
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.prodotti import pubblicati
from core import bollettino, metrics
from core.store import Archivio
from core.testi import soglie


def conta(archivio: Archivio, scheda: dict, anni_prova: int, stagionale_alta: int, stagionale_bassa: int) -> dict:
    serie_id = scheda["prezzo"]["serie"]
    in_origine = archivio.osservazioni(serie_id)
    if in_origine and in_origine[0]["periodo"].count("-") == 2:
        in_origine = metrics.da_giornaliero_a_settimanale(in_origine)
    cambio = scheda["prezzo"].get("cambio")
    cambi = {o["periodo"]: o["valore"] for o in archivio.osservazioni(cambio) if o.get("valore")} if cambio else {}
    in_euro = metrics.converti(in_origine, cambi) if cambi else in_origine
    disponibili = [o for o in in_euro if o.get("valore") is not None]
    if len(disponibili) < 120:
        return {"specie": scheda["id"], "settimane": len(disponibili), "nota": "storico troppo corto per calibrare"}

    ultime = disponibili[-52 * anni_prova:]
    titoli = Counter()
    fasce = Counter()
    fasce_nette = Counter()
    for o in ultime:
        periodo = o["periodo"]
        bozza = bollettino.componi(in_euro, in_origine, periodo, [], scheda["nome"])
        for voce in bozza.voci:
            titoli[voce.titolo.split(":")[-1].strip()[:40]] += 1
        p = metrics.posizione_stagionale(in_euro, periodo).percentile
        if p is not None:
            fasce["alta" if p >= stagionale_alta else ("bassa" if p <= stagionale_bassa else "centrale")] += 1
        pn = metrics.posizione_stagionale_al_netto_del_livello(in_euro, periodo).percentile
        if pn is not None:
            fasce_nette["alta" if pn >= stagionale_alta else ("bassa" if pn <= stagionale_bassa else "centrale")] += 1

    anni = max(1, len(ultime) / 52)
    return {
        "specie": scheda["id"],
        "settimane": len(ultime),
        "voci_per_anno": {k: round(v / anni, 1) for k, v in titoli.items()},
        "fasce_nominali": {k: round(v / anni, 1) for k, v in fasce.items()},
        "fasce_al_netto": {k: round(v / anni, 1) for k, v in fasce_nette.items()},
    }


def esegui(percorso_db: str, anni_prova: int, fascia_alta: int, fascia_bassa: int) -> int:
    archivio = Archivio(percorso_db)
    s = soglie()
    print(f"Soglie in uso: stagionale {s['stagionale']['fascia_bassa']}/{s['stagionale']['fascia_alta']}, "
          f"prova con {fascia_bassa}/{fascia_alta}; ultimi {anni_prova} anni\n")
    for scheda in pubblicati():
        esito = conta(archivio, scheda, anni_prova, fascia_alta, fascia_bassa)
        print(f"== {esito['specie']} ({esito['settimane']} settimane)")
        if "nota" in esito:
            print("   " + esito["nota"])
            continue
        print("   voci di bollettino per anno:", esito["voci_per_anno"] or "nessuna")
        print("   settimane/anno per fascia, prezzi nominali: ", esito["fasce_nominali"])
        print("   settimane/anno per fascia, al netto del livello:", esito["fasce_al_netto"])
    print("\nLettura: se la fascia 'alta' nominale supera le 26 settimane l'anno, la lettura nominale sta "
          "misurando l'inflazione e non la stagione; alzare le soglie o dare risalto alla lettura al netto.")
    archivio.chiudi()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--anni", type=int, default=3)
    parser.add_argument("--fascia-alta", type=int, default=soglie()["stagionale"]["fascia_alta"])
    parser.add_argument("--fascia-bassa", type=int, default=soglie()["stagionale"]["fascia_bassa"])
    a = parser.parse_args()
    raise SystemExit(esegui(a.db, a.anni, a.fascia_alta, a.fascia_bassa))
