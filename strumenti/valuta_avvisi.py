"""Valuta gli avvisi redazionali sui dati appena pubblicati.

Legge `config/avvisi.json` e l'indice dei prodotti; scrive
`web/data/avvisi.json` con gli avvisi scattati questa settimana e stampa
una riga per ciascuno, che il ciclo automatico inoltra sul webhook. È il
primo gradino degli avvisi personali: quando ci sarà la registrazione,
le stesse regole si applicheranno per lettore.

    python strumenti/valuta_avvisi.py --dati web/data
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]


def esegui(cartella_dati: str) -> int:
    dati = Path(cartella_dati)
    regole = json.loads((RADICE / "config" / "avvisi.json").read_text(encoding="utf-8")).get("avvisi", [])
    indice = json.loads((dati / "mercati.json").read_text(encoding="utf-8"))
    scattati = []
    for p in indice["prodotti"]:
        for r in regole:
            if r.get("specie") not in (p["id"], "tutte"):
                continue
            prezzo = p.get("prezzo_eur_kg")
            variazione = p.get("variazione_settimana")
            colpito = False
            if "sopra" in r and prezzo is not None and prezzo > r["sopra"]:
                colpito = True
            if "sotto" in r and prezzo is not None and prezzo < r["sotto"]:
                colpito = True
            if "variazione_settimana" in r and variazione is not None and abs(variazione) >= r["variazione_settimana"]:
                colpito = True
            if colpito:
                scattati.append({
                    "specie": p["id"], "nome": p["nome"], "periodo": p["ultimo_periodo"],
                    "prezzo_eur_kg": prezzo, "variazione_settimana": variazione,
                    "it": r.get("it", ""), "en": r.get("en", ""),
                })
    documento = {"valutati_il": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "settimana": indice["prodotti"][0]["ultimo_periodo"] if indice["prodotti"] else None,
                 "avvisi": scattati}
    (dati / "avvisi.json").write_text(json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8")
    for a in scattati:
        print(f"AVVISO {a['nome']}: {a['it']} ({a['prezzo_eur_kg']:.2f} €/kg, {a['variazione_settimana']:+.1f}% sulla settimana)")
    if not scattati:
        print("Nessun avviso scattato.")
    uscita = os.environ.get("GITHUB_OUTPUT")
    if uscita:
        with open(uscita, "a", encoding="utf-8") as f:
            f.write(f"avvisi={len(scattati)}\n")
            f.write("avvisi_testo=" + " | ".join(f"{a['nome']}: {a['it']}" for a in scattati)[:900] + "\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dati", default=str(RADICE / "web/data"))
    raise SystemExit(esegui(parser.parse_args().dati))
