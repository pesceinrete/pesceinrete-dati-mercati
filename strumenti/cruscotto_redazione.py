"""Cruscotto della redazione.

I cinque minuti del giovedi mattina. Invece di aprire il database o
guardare i log, la redazione apre una pagina che risponde a quattro
domande: è arrivato il dato nuovo, qualcosa è stato corretto, qualcosa è
fuori scala, e che cosa c'è da raccontare questa settimana.

Non è pubblica: sta in una cartella separata e non finisce nel sito.

    python strumenti/cruscotto_redazione.py --db dati/archivio.sqlite
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import date, datetime, timezone
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE))

from config.prodotti import pubblicati, serie_flussi
from core import bollettino as modulo_bollettino
from core import isoweek, mese, metrics
from core.store import Archivio

GIORNI_DI_ATTESA = {"settimanale": 9, "mensile": 75}


def stato_serie(archivio: Archivio, serie_id: str) -> dict:
    anagrafica = archivio.serie(serie_id)
    if anagrafica is None:
        return {"id": serie_id, "esito": "assente", "dettaglio": "serie non in archivio"}

    osservazioni = archivio.osservazioni(serie_id)
    if not osservazioni:
        return {"id": serie_id, "esito": "vuota", "dettaglio": "nessuna osservazione"}

    ultimo = osservazioni[-1]["periodo"]
    mensile = mese.e_mensile(ultimo)
    fine = mese.ultimo_giorno(ultimo) if mensile else isoweek.domenica(ultimo)
    ritardo = (date.today() - fine).days
    soglia = GIORNI_DI_ATTESA["mensile" if mensile else "settimanale"]

    buchi = []
    if not mensile:
        attese = isoweek.intervallo(osservazioni[0]["periodo"], ultimo)
        presenti = {o["periodo"] for o in osservazioni}
        buchi = [p for p in attese if p not in presenti]

    return {
        "id": serie_id,
        "frequenza": anagrafica["frequenza"],
        "fonte": anagrafica["fonte"],
        "ultimo": ultimo,
        "osservazioni": len(osservazioni),
        "ritardo": ritardo,
        "esito": "in ritardo" if ritardo > soglia else "aggiornata",
        "dettaglio": (
            f"ultimo periodo {ultimo}, chiuso da {ritardo} giorni"
            + (f", {len(buchi)} periodi mancanti" if buchi else "")
        ),
        "buchi": buchi[-6:],
    }


def anomalie(archivio: Archivio, serie_id: str, quante: int = 26) -> list[str]:
    """Scarti che vale la pena guardare prima di pubblicare."""
    osservazioni = [
        o for o in archivio.osservazioni(serie_id)[-quante:] if o.get("valore") is not None
    ]
    avvisi = []
    for precedente, corrente in zip(osservazioni, osservazioni[1:]):
        if not precedente["valore"]:
            continue
        variazione = (corrente["valore"] - precedente["valore"]) / precedente["valore"] * 100
        if abs(variazione) >= 12:
            avvisi.append(
                f"{corrente['periodo']}: {variazione:+.1f}% sul periodo precedente "
                f"({precedente['valore']:.2f} verso {corrente['valore']:.2f})"
            )
    return avvisi


def componi(archivio: Archivio) -> str:
    blocchi = []
    momento = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    for scheda in pubblicati():
        righe_serie, righe_anomalie = [], []
        collegate = {"prezzo": scheda["prezzo"]["serie"]}
        if scheda["prezzo"].get("cambio"):
            collegate["cambio"] = scheda["prezzo"]["cambio"]
        for partner in (scheda.get("flussi") or {}).get("partner", []):
            collegate["import " + partner.lower()] = serie_flussi(scheda, partner)
        for ruolo, serie_id in collegate.items():
            stato = stato_serie(archivio, serie_id)
            colore = {
                "aggiornata": "buono",
                "in ritardo": "attenzione",
            }.get(stato["esito"], "male")
            righe_serie.append(
                f"<tr class='{colore}'><td>{html.escape(ruolo)}</td>"
                f"<td>{html.escape(serie_id)}</td>"
                f"<td>{html.escape(stato['esito'])}</td>"
                f"<td>{html.escape(stato['dettaglio'])}</td></tr>"
            )
            for avviso in anomalie(archivio, serie_id):
                righe_anomalie.append(f"<li>{html.escape(serie_id)} — {html.escape(avviso)}</li>")

        chiave_prezzo = scheda["prezzo"]["serie"]
        in_origine = archivio.osservazioni(chiave_prezzo)
        if in_origine and in_origine[0]["periodo"].count("-") == 2:
            in_origine = metrics.da_giornaliero_a_settimanale(in_origine)
        chiave_cambio = scheda["prezzo"].get("cambio")
        cambi = {
            o["periodo"]: o["valore"]
            for o in archivio.osservazioni(chiave_cambio)
            if o.get("valore")
        } if chiave_cambio else {}
        in_euro = metrics.converti(in_origine, cambi) if cambi else in_origine
        disponibili = [o for o in in_euro if o.get("valore") is not None]

        revisioni = archivio.revisioni(chiave_prezzo)[:20]
        righe_revisioni = "".join(
            f"<tr><td>{html.escape(r['periodo'])}</td><td>{r['valore_precedente']:.3f}</td>"
            f"<td>{r['valore_nuovo']:.3f}</td><td>{html.escape(r['rilevata_il'][:16])}</td></tr>"
            for r in revisioni
            if r["valore_precedente"] is not None and r["valore_nuovo"] is not None
        )

        bozza = ""
        if disponibili:
            bollettino = modulo_bollettino.componi(
                in_euro, in_origine, disponibili[-1]["periodo"], revisioni, scheda["nome"]
            )
            bozza = "".join(
                f"<div class='voce'><h4>{html.escape(v.titolo)}</h4>"
                f"<p>{html.escape(v.testo)}</p></div>"
                for v in bollettino.voci
            ) or "<p class='quieto'>Nessun movimento fuori dall'ordinario.</p>"

        blocchi.append(f"""
<section>
  <h2>{html.escape(scheda['nome'])}</h2>

  <h3>Serie collegate</h3>
  <table><thead><tr><th>Ruolo</th><th>Serie</th><th>Stato</th><th>Dettaglio</th></tr></thead>
  <tbody>{''.join(righe_serie)}</tbody></table>

  <h3>Scarti da guardare prima di pubblicare</h3>
  {'<ul>' + ''.join(righe_anomalie) + '</ul>' if righe_anomalie
   else "<p class='quieto'>Nessuno scarto oltre il 12% nei periodi recenti.</p>"}

  <h3>Correzioni della fonte</h3>
  {'<table><thead><tr><th>Periodo</th><th>Prima</th><th>Dopo</th><th>Rilevata</th></tr></thead><tbody>'
   + righe_revisioni + '</tbody></table>' if righe_revisioni
   else "<p class='quieto'>Nessuna revisione registrata.</p>"}

  <h3>Bozza del bollettino</h3>
  {bozza}
</section>""")

    righe_esecuzioni = "".join(
        f"<tr><td>{html.escape(e['avviata_il'][:16].replace('T', ' '))}</td>"
        f"<td>{html.escape(e['fonte'])}</td><td>{html.escape(e['esito'])}</td>"
        f"<td>{e['nuove']}</td><td>{e['riviste']}</td>"
        f"<td>{html.escape((e['messaggio'] or '')[:220])}</td></tr>"
        for e in archivio.ultime_esecuzioni(12)
    )

    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Cruscotto redazione — Dati e mercati</title>
<style>
 body{{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#10201f;
   background:#eef1ef;margin:0;padding:28px 20px 60px}}
 .guscio{{max-width:1000px;margin:0 auto}}
 h1{{font-size:1.6rem;font-weight:600;margin:0 0 4px}}
 .momento{{color:#55655f;font-size:.9rem;margin-bottom:22px}}
 section{{background:#fff;border:1px solid #c6d1cd;border-radius:4px;padding:20px;margin-bottom:20px}}
 h2{{font-size:1.2rem;margin:0 0 14px}}
 h3{{font-size:.95rem;margin:20px 0 8px;color:#55655f}}
 h4{{font-size:.95rem;margin:0 0 4px}}
 table{{width:100%;border-collapse:collapse;font-size:.88rem;font-variant-numeric:tabular-nums}}
 th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid #dfe6e3}}
 th{{font-size:.78rem;color:#55655f;font-weight:600}}
 tr.buono td:nth-child(3){{color:#16625b}}
 tr.attenzione td:nth-child(3){{color:#8f4d16;font-weight:600}}
 tr.male td:nth-child(3){{color:#8c2b20;font-weight:600}}
 ul{{margin:0;padding-left:20px;font-size:.88rem}}
 .quieto{{color:#55655f;font-size:.9rem;margin:0}}
 .voce{{border-left:3px solid #c6d1cd;padding:2px 0 2px 12px;margin-bottom:12px}}
 .voce p{{margin:0;color:#55655f;font-size:.9rem}}
 .promemoria{{background:#fff;border-left:4px solid #8f4d16;border-radius:4px;padding:16px 20px;
   margin-bottom:20px;font-size:.92rem}}
</style></head>
<body><div class="guscio">
<h1>Cruscotto redazione</h1>
<p class="momento">Generato il {momento}. Pagina interna, non indicizzata.</p>

<div class="promemoria">
  Da controllare prima di considerare chiusa la settimana: che le serie risultino aggiornate,
  che gli scarti segnalati abbiano una spiegazione, e che la bozza del bollettino dica qualcosa
  che il lettore non vede già dal grafico. Se una fonte è in ritardo, online resta l'ultimo
  dato valido con la sua data: non va forzato nulla.
</div>

{''.join(blocchi)}

<section>
  <h2>Ultime esecuzioni</h2>
  <table><thead><tr><th>Quando</th><th>Fonte</th><th>Esito</th><th>Nuove</th><th>Riviste</th>
    <th>Note</th></tr></thead><tbody>{righe_esecuzioni}</tbody></table>
</section>
</div></body></html>"""


def esegui(percorso_db: str, uscita: str) -> int:
    archivio = Archivio(percorso_db)
    destinazione = Path(uscita)
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    destinazione.write_text(componi(archivio), encoding="utf-8")
    print(f"Scritto {destinazione}")
    archivio.chiudi()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--uscita", default="redazione/cruscotto.html")
    a = parser.parse_args()
    raise SystemExit(esegui(a.db, a.uscita))
