"""Compone `web/dati-mercati.html` dai sorgenti in `web/src/`.

Chi mantiene la pagina lavora su tre file separati — `pagina.html`,
`stile.css`, `script.js` — con il proprio editor e i propri strumenti. Il
risultato resta un file solo, perché un file solo è quello che lo
shortcode e il plugin sanno inserire. Si rigenera a ogni build e il
collaudo gira sul risultato, non sui sorgenti.

    python strumenti/componi_pagina.py
"""

from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
SRC = RADICE / "web" / "src"
USCITA = RADICE / "web" / "dati-mercati.html"


def esegui() -> int:
    pagina = (SRC / "pagina.html").read_text(encoding="utf-8")
    stile = (SRC / "stile.css").read_text(encoding="utf-8")
    script = (SRC / "script.js").read_text(encoding="utf-8")
    for segnaposto in ("/* __STILE__ */", "/* __SCRIPT__ */"):
        if segnaposto not in pagina:
            raise SystemExit(f"segnaposto mancante in pagina.html: {segnaposto}")
    composta = pagina.replace("/* __STILE__ */", stile.rstrip("\n"), 1).replace("/* __SCRIPT__ */", script.rstrip("\n"), 1)
    USCITA.write_text(composta, encoding="utf-8")
    print(f"Composta {USCITA.relative_to(RADICE)} ({composta.count(chr(10))} righe) da "
          f"pagina.html + stile.css ({stile.count(chr(10))}) + script.js ({script.count(chr(10))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(esegui())
