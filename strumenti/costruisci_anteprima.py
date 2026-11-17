"""Crea una copia della pagina con i dati incorporati.

Serve per l'anteprima: un unico file apribile con doppio clic, senza
server locale. La versione che va in produzione resta `dati-mercati.html`,
che legge il JSON separato e quindi si aggiorna da sola.

    python strumenti/costruisci_anteprima.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]


def esegui(pagina: Path, dati: Path, uscita: Path) -> int:
    html = pagina.read_text(encoding="utf-8")
    json_dati = dati.read_text(encoding="utf-8")
    suffisso = ".en" if dati.name.endswith(".en.json") else ""

    # Il blocco statico di sintesi della prima specie: in produzione lo
    # inserisce lo shortcode WordPress, qui lo incolliamo nel segnaposto.
    primo = dati.parent / f"sintesi-salmone{suffisso}.html"
    if primo.exists():
        html = html.replace(
            '<div id="pir-sintesi-statica"></div>',
            '<div id="pir-sintesi-statica">' + primo.read_text(encoding="utf-8") + "</div>",
            1,
        )

    import json as _json
    prodotti = {}
    for f in sorted((dati.parent / "prodotti").glob(f"*{suffisso}.json")):
        if not suffisso and ".en." in f.name:
            continue
        prodotti[f.name.split(".")[0]] = _json.loads(f.read_text(encoding="utf-8"))
    incorporato = (
        "<script>window.PESCEINRETE_DATI=" + json_dati + ";window.PESCEINRETE_PRODOTTI="
        + _json.dumps(prodotti, ensure_ascii=False, separators=(",", ":"))
        + ";</script>\n<script>\n\"use strict\";"
    )
    html = html.replace('<script>\n(function(){\n"use strict";', incorporato + "\n(function(){", 1)

    # Solo nell'anteprima: un carattere vicino a quello di IGB. Dentro il
    # sito il carattere lo dà il tema e questa riga non esiste.
    html = html.replace(
        "</head>",
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;800&display=swap">'
        "<style>.pir-mercati{--testo:'Montserrat',Arial,sans-serif;--titoli:'Montserrat',Arial,sans-serif}</style></head>",
        1,
    )
    uscita.write_text(html, encoding="utf-8")
    print(f"Scritto {uscita} ({uscita.stat().st_size / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pagina", default=None)
    parser.add_argument("--dati", default=None)
    parser.add_argument("--uscita", default=None)
    parser.add_argument("--lingua", default="it", choices=("it", "en"))
    a = parser.parse_args()
    suffisso = "" if a.lingua == "it" else ".en"
    pagina = Path(a.pagina) if a.pagina else RADICE / f"web/dati-mercati{suffisso}.html"
    dati = Path(a.dati) if a.dati else RADICE / f"web/data/mercati{suffisso}.json"
    uscita = Path(a.uscita) if a.uscita else RADICE / f"web/anteprima-dati-mercati{suffisso}.html"
    raise SystemExit(esegui(pagina, dati, uscita))
