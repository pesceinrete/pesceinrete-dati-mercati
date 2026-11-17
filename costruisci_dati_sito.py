"""Genera tutto quello che la pagina pubblica.

Produce tre cose, ciascuna con un compito diverso:

* `mercati.json` — i dati che la pagina usa per grafici e comandi;
* `sintesi-<prodotto>.html` — un blocco HTML statico con la lettura dei
  numeri e la tabella delle ultime dodici settimane. Esiste perché quello
  che sta solo dentro JavaScript non viene indicizzato e non si legge bene
  con uno screen reader: questa parte è testo vero, presente anche senza
  script;
* `bollettini/<prodotto>-<settimana>.md` — la bozza settimanale per la
  redazione.

Uso:
    python costruisci_dati_sito.py --db dati/archivio.sqlite --uscita web/data
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RADICE = Path(__file__).resolve().parent
sys.path.insert(0, str(RADICE))

from config.prodotti import nome_paese, pubblicati, serie_flussi
from core import bollettino as modulo_bollettino
from core import isoweek, mese, metrics, redazione
from core.store import Archivio
from core.testi import LINGUE, MESI, SINTESI, traduci

MARCATORE_DIMOSTRATIVO = "DIMOSTRATIVO"
ANNOTAZIONI = RADICE / "config" / "annotazioni.json"
RESE = RADICE / "config" / "rese.json"


def rese_per(prodotto_id: str, lingua: str) -> list[dict]:
    if not RESE.exists():
        return []
    voci = json.loads(RESE.read_text(encoding="utf-8")).get(prodotto_id, [])
    return [{"etichetta": v.get(lingua) or v.get("it"), "resa": v["resa"]} for v in voci if "resa" in v]


def annotazioni_per(prodotto_id: str, lingua: str, dimostrativo: bool) -> list[dict]:
    """Le note della redazione per questa specie, nella lingua richiesta.

    Le note segnate come dimostrative compaiono solo finché i dati sono
    dimostrativi: con i dati veri restano fuori, così nessuno pubblica per
    sbaglio l'esempio.
    """
    if not ANNOTAZIONI.exists():
        return []
    voci = json.loads(ANNOTAZIONI.read_text(encoding="utf-8")).get("annotazioni", [])
    risultato = []
    for v in voci:
        if v.get("specie") not in (prodotto_id, "tutte"):
            continue
        if v.get("dimostrativa") and not dimostrativo:
            continue
        testo = v.get(lingua) or v.get("it") or ""
        if v.get("settimana") and testo:
            risultato.append({"periodo": v["settimana"], "testo": testo})
    return sorted(risultato, key=lambda x: x["periodo"])


# --------------------------------------------------------------------------
# Composizione di un prodotto
# --------------------------------------------------------------------------


ANNI_IN_PAGINA = 6  # la pagina porta con sé sei anni; l'archivio li tiene tutti


def componi_prodotto(archivio: Archivio, scheda: dict, dimostrativo: bool, lingua: str = "it"):
    riferimenti = scheda["prezzo"]
    anagrafica = archivio.serie(riferimenti["serie"])
    if anagrafica is None:
        return None, None, None

    in_origine = archivio.osservazioni(riferimenti["serie"])
    # Le fonti con quotazioni giornaliere (RNM) scrivono il giorno:
    # la settimana si costruisce qui.
    if in_origine and in_origine[0]["periodo"].count("-") == 2:
        in_origine = metrics.da_giornaliero_a_settimanale(in_origine)

    cambi = {}
    if riferimenti.get("cambio"):
        cambi = {
            o["periodo"]: o["valore"]
            for o in archivio.osservazioni(riferimenti["cambio"])
            if o.get("valore")
        }

    in_euro = metrics.converti(in_origine, cambi) if cambi else [dict(o) for o in in_origine]
    disponibili = [o for o in in_euro if o.get("valore") is not None]
    if not disponibili:
        return None, None, None

    ultima = disponibili[-1]["periodo"]
    variazioni = metrics.variazioni_recenti(in_euro, ultima)
    stagionale = metrics.posizione_stagionale(in_euro, ultima)
    stagionale_netta = metrics.posizione_stagionale_al_netto_del_livello(in_euro, ultima)
    banda = metrics.banda_stagionale(in_euro)
    anno_corrente = isoweek.scomponi(ultima)[0]
    ultime_52 = metrics.aggrega(in_euro, isoweek.sposta(ultima, -51), ultima)
    volumi_percentile = None
    if anagrafica["valuta"] != "EUR":
        serie_volumi = [{"periodo": o["periodo"], "valore": o.get("quantita")} for o in in_euro if o.get("quantita")]
        if serie_volumi:
            volumi_percentile = metrics.posizione_stagionale(serie_volumi, ultima).percentile
    revisioni = archivio.revisioni(riferimenti["serie"])[:20]
    flussi = componi_flussi(archivio, scheda, lingua)

    bozza = modulo_bollettino.componi(
        in_euro, in_origine, ultima, revisioni, traduci(scheda["nome"], lingua), lingua
    )

    def tr(testo):
        return traduci(testo, lingua)

    prodotto = {
        "id": scheda["id"],
        "lingua": lingua,
        "fonte_prezzo": riferimenti["fonte"],
        "nome": tr(scheda["nome"]),
        "sottotitolo": tr(scheda["sottotitolo"]),
        "titolo_pagina": tr(scheda["titolo_pagina"]),
        "descrizione_pagina": tr(scheda["descrizione_pagina"]),
        "domande": [
            {"domanda": tr(d[0]), "risposta": tr(d[1])}
            for d in scheda.get("domande", [])
        ],
        "serie": {
            "id": anagrafica["id"],
            "indicatore": tr(anagrafica["indicatore"]),
            "fase": tr(anagrafica["fase"]),
            "mercato": tr(anagrafica["mercato"]),
            "presentazione": tr(anagrafica["presentazione"]),
            "conservazione": tr(anagrafica["conservazione"]),
            "pezzatura": tr(anagrafica["pezzatura"]),
            "unita_origine": anagrafica["unita"],
            "valuta_origine": anagrafica["valuta"],
            "frequenza": tr(anagrafica["frequenza"]),
            "fonte": tr(anagrafica["fonte"]),
            "fonte_url": anagrafica["fonte_url"],
            "licenza": tr(anagrafica["licenza"]),
            "licenza_url": anagrafica["licenza_url"],
            "elaborazione": tr(anagrafica["elaborazione"]),
            "note": tr(anagrafica["note"]),
        },
        "ultimo_periodo": ultima,
        "ultimo_periodo_esteso": periodo_esteso(ultima, lingua),
        "prezzo_eur_kg": arrotonda(disponibili[-1]["valore"], 3),
        "prezzo_origine": valore_a(in_origine, ultima),
        "cambio": arrotonda(disponibili[-1].get("cambio"), 4),
        "volume_tonnellate": disponibili[-1].get("quantita"),
        "variazioni": {c: arrotonda(v, 2) for c, v in variazioni.items()},
        "stagionale": {
            "percentile": arrotonda(stagionale.percentile, 1),
            "lettura": stagionale.lettura(lingua),
            "osservazioni": stagionale.osservazioni_confronto,
            "anni": stagionale.anni_usati,
            "minimo": arrotonda(stagionale.minimo, 3),
            "mediana": arrotonda(stagionale.mediana, 3),
            "massimo": arrotonda(stagionale.massimo, 3),
            "attendibile": stagionale.attendibile,
        },
        "stagionale_al_netto": {
            "percentile": arrotonda(stagionale_netta.percentile, 1),
            "lettura": stagionale_netta.lettura(lingua),
            "attendibile": stagionale_netta.attendibile,
        },
        "banda_stagionale": [
            {
                "settimana": settimana,
                "minimo": arrotonda(v["minimo"], 3),
                "mediana": arrotonda(v["mediana"], 3),
                "massimo": arrotonda(v["massimo"], 3),
                "osservazioni": v["osservazioni"],
            }
            for settimana, v in banda.items()
        ],
        "anno_corrente": {
            "anno": anno_corrente,
            "punti": [
                {
                    "settimana": isoweek.scomponi(o["periodo"])[1],
                    "valore": arrotonda(o["valore"], 3),
                }
                for o in disponibili
                if isoweek.scomponi(o["periodo"])[0] == anno_corrente
            ],
        },
        "anno_precedente": {
            "anno": anno_corrente - 1,
            "punti": [
                {
                    "settimana": isoweek.scomponi(o["periodo"])[1],
                    "valore": arrotonda(o["valore"], 3),
                }
                for o in disponibili
                if isoweek.scomponi(o["periodo"])[0] == anno_corrente - 1
            ],
        },
        "ultime_52_settimane": {
            "prezzo_medio_ponderato": arrotonda(ultime_52.prezzo_medio_ponderato, 3),
            "volume_totale": ultime_52.volume_totale,
            "settimane_usate": ultime_52.settimane_usate,
            "avvertenze": ultime_52.avvertenze,
        },
        "storico": [
            {
                "periodo": o["periodo"],
                "eur": arrotonda(o.get("valore"), 3),
                "origine": valore_a(in_origine, o["periodo"]),
                "tonnellate": o.get("quantita") if anagrafica["valuta"] != "EUR" else None,
                "cambio": arrotonda(o.get("cambio"), 4),
            }
            for o in in_euro
            if isoweek.scomponi(o["periodo"])[0] >= anno_corrente - ANNI_IN_PAGINA
        ],
        "con_volumi": anagrafica["valuta"] != "EUR",
        "flussi": flussi,
        "revisioni_recenti": [
            {
                "periodo": r["periodo"],
                "da": r["valore_precedente"],
                "a": r["valore_nuovo"],
                "rilevata_il": r["rilevata_il"][:10],
            }
            for r in revisioni
        ],
        "bollettino": [
            {"titolo": v.titolo, "testo": v.testo, "rilievo": v.rilievo} for v in bozza.voci
        ],
        "annotazioni": annotazioni_per(scheda["id"], lingua, dimostrativo),
        "rese": rese_per(scheda["id"], lingua),
        "dimostrativo": dimostrativo,
    }

    prodotto["lede"] = redazione.lede(
        prodotto_id=scheda["id"],
        nome=prodotto["nome"],
        fonte=riferimenti["fonte"],
        periodo=ultima,
        prezzo_eur=prodotto["prezzo_eur_kg"],
        variazioni=prodotto["variazioni"],
        stagionale=prodotto["stagionale"],
        volumi=prodotto["volume_tonnellate"] if anagrafica["valuta"] != "EUR" else None,
        volumi_percentile=volumi_percentile,
        flussi=flussi,
        lingua=lingua,
    )
    prodotto["sintesi_html"] = sintesi_html(prodotto)
    return prodotto, prodotto["sintesi_html"], bozza.markdown()


def componi_flussi(archivio: Archivio, scheda: dict, lingua: str = "it"):
    """Importazioni mensili per provenienza, se le serie sono in archivio.

    Il prezzo dice quanto costa il prodotto sul mercato di riferimento.
    Questo dice quanto ne entra in Italia e da dove: domande diverse,
    tenute separate anche graficamente.
    """
    flussi = scheda.get("flussi")
    if not flussi:
        return None
    serie_mondo = serie_flussi(scheda, "WORLD")
    anagrafica = archivio.serie(serie_mondo)
    osservazioni = archivio.osservazioni(serie_mondo) if anagrafica else []
    if not osservazioni:
        return None

    ultimo = osservazioni[-1]["periodo"]
    mobile = mese.somma_dodici_mesi(osservazioni, ultimo)
    precedente = mese.somma_dodici_mesi(osservazioni, mese.sposta(ultimo, -12))

    provenienze = []
    for partner in flussi["partner"]:
        if partner == "WORLD":
            continue
        serie_partner = serie_flussi(scheda, partner)
        if not archivio.serie(serie_partner):
            continue
        parziale = mese.somma_dodici_mesi(archivio.osservazioni(serie_partner), ultimo)
        if parziale["quantita"] and mobile["quantita"]:
            provenienze.append({
                "codice": partner,
                "paese": nome_paese(partner, lingua),
                "tonnellate": arrotonda(parziale["quantita"], 0),
                "quota": arrotonda(parziale["quantita"] / mobile["quantita"] * 100, 1),
                "valore_unitario": arrotonda(parziale["valore_unitario"], 3),
            })
    provenienze.sort(key=lambda x: -(x["tonnellate"] or 0))

    principale = next((x for x in provenienze if x["codice"] == flussi.get("principale")), None)

    def delta(adesso, prima):
        return (adesso - prima) / prima * 100 if adesso and prima else None

    return {
        "fonte": traduci(anagrafica["fonte"], lingua),
        "fonte_url": anagrafica["fonte_url"],
        "indicatore": traduci(anagrafica["indicatore"], lingua),
        "note": traduci(anagrafica["note"], lingua),
        "descrizione": traduci(flussi["descrizione"], lingua),
        "ultimo_mese": ultimo,
        "ultimo_mese_esteso": mese_esteso(ultimo, lingua),
        "mese": {
            "tonnellate": osservazioni[-1].get("quantita"),
            "valore_unitario": arrotonda(osservazioni[-1].get("valore"), 3),
        },
        "dodici_mesi": {
            "tonnellate": arrotonda(mobile["quantita"], 0),
            "valore_unitario": arrotonda(mobile["valore_unitario"], 3),
            "mesi_usati": mobile["mesi_usati"],
            "mesi_mancanti": mobile["mesi_mancanti"],
            "delta_tonnellate": arrotonda(delta(mobile["quantita"], precedente["quantita"]), 1),
            "delta_valore_unitario": arrotonda(
                delta(mobile["valore_unitario"], precedente["valore_unitario"]), 1
            ),
        },
        "principale": principale,
        "quota_norvegia": principale["quota"] if principale else None,  # compatibilità pagina
        "provenienze": provenienze,
        "serie": [
            {
                "periodo": o["periodo"],
                "tonnellate": o.get("quantita"),
                "valore_unitario": arrotonda(o.get("valore"), 3),
            }
            for o in osservazioni[-72:]
        ],
    }


# --------------------------------------------------------------------------
# Blocco statico
# --------------------------------------------------------------------------


def numero(valore, decimali=2, lingua="it"):
    if valore is None:
        return "n.d." if lingua == "it" else "n/a"
    testo = f"{valore:,.{decimali}f}"
    if lingua == "it":
        return testo.replace(",", "@").replace(".", ",").replace("@", ".")
    return testo


def sintesi_html(prodotto: dict) -> str:
    """Testo e tabella presenti nella pagina anche senza JavaScript."""
    lingua = prodotto.get("lingua", "it")
    T = SINTESI[lingua]
    s = prodotto["serie"]
    v = prodotto["variazioni"]

    def frase(chiave, valore):
        etichetta = T["etichette"][chiave]
        if valore is None:
            return T["non_confrontabile"].format(etichetta=etichetta)
        verso = T["verso"]["su" if valore > 0 else ("giu" if valore < 0 else "fermo")]
        return T["variazione"].format(
            etichetta=etichetta, verso=verso, valore=numero(abs(valore), 1, lingua)
        )

    in_euro = s["valuta_origine"] == "EUR"
    con_volumi = prodotto.get("con_volumi", False)

    def riga(o):
        celle = ["<td>" + html.escape(o["periodo"]) + "</td>", "<td>" + numero(o["eur"], 2, lingua) + "</td>"]
        if not in_euro:
            celle.append("<td>" + numero(o["origine"], 2, lingua) + "</td>")
        if con_volumi:
            celle.append("<td>" + numero(o["tonnellate"], 0, lingua) + "</td>")
        return "<tr>" + "".join(celle) + "</tr>"

    righe = "".join(riga(o) for o in prodotto["storico"][-12:])

    domande = "".join(
        f"<dt>{html.escape(d['domanda'])}</dt><dd>{html.escape(d['risposta'])}</dd>"
        for d in prodotto.get("domande", [])
    )
    frasi = ", ".join([
        frase("settimana", v.get("settimana")),
        frase("quattro", v.get("quattro_settimane")),
        frase("anno", v.get("anno")),
    ])
    indicatore = s["indicatore"].lower()
    articolo = T["articolo_f"] if indicatore.startswith(("quotazione",)) else T["articolo_m"]
    apertura = T["apertura"].format(
        settimana=html.escape(prodotto["ultimo_periodo"][6:]),
        esteso=html.escape(prodotto["ultimo_periodo_esteso"]),
        articolo=articolo,
        indicatore=html.escape(indicatore),
        eur=numero(prodotto["prezzo_eur_kg"], 2, lingua),
        origine="" if in_euro else T["origine"].format(
            origine=numero(prodotto["prezzo_origine"], 2, lingua), unita=html.escape(s["unita_origine"])
        ),
        frasi=frasi,
    )
    colonne = [T["colonne"][0], T["colonne"][1]]
    if not in_euro:
        colonne.append(T["colonne"][2].format(unita=html.escape(s["unita_origine"])))
    if con_volumi:
        colonne.append(T["colonne"][3])
    intestazioni = "".join(f"<th>{c}</th>" for c in colonne)
    didascalia = (T["didascalia_euro"] if in_euro else T["didascalia"]).format(fonte=html.escape(s["fonte"]))

    return f"""<section class="pir-riquadro pir-sintesi" id="sintesi">
  <h2>{T["titolo"].format(nome=html.escape(prodotto['nome']))}</h2>
  <p class="pir-lede">{html.escape(prodotto.get('lede') or apertura)}</p>
  <table class="pir-tabella">
    <caption>{didascalia}</caption>
    <thead><tr>{intestazioni}</tr></thead>
    <tbody>{righe}</tbody>
  </table>
  <dl class="pir-domande">{domande}</dl>
</section>"""


# --------------------------------------------------------------------------
# Utilità
# --------------------------------------------------------------------------


def arrotonda(valore, decimali):
    return round(valore, decimali) if valore is not None else None


def valore_a(serie: list[dict], periodo: str):
    for o in serie:
        if o["periodo"] == periodo and o.get("valore") is not None:
            return round(o["valore"], 3)
    return None


def periodo_esteso(periodo: str, lingua: str = "it") -> str:
    inizio, fine = isoweek.lunedi(periodo), isoweek.domenica(periodo)
    nomi = MESI.get(lingua, MESI["it"])
    if inizio.month == fine.month:
        return f"{inizio.day}-{fine.day} {nomi[fine.month - 1]} {fine.year}"
    return f"{inizio.day} {nomi[inizio.month - 1]} - {fine.day} {nomi[fine.month - 1]} {fine.year}"


def mese_esteso(chiave_mese: str, lingua: str = "it") -> str:
    anno, numero_mese = mese.scomponi(chiave_mese)
    return f"{MESI.get(lingua, MESI['it'])[numero_mese - 1]} {anno}"


# --------------------------------------------------------------------------


def esegui(percorso_db: str, uscita: str) -> int:
    archivio = Archivio(percorso_db)
    dimostrativo = (Path(percorso_db).parent / MARCATORE_DIMOSTRATIVO).exists()
    cartella = Path(uscita)
    cartella.mkdir(parents=True, exist_ok=True)
    cartella_bollettini = cartella.parent / "bollettini"
    cartella_bollettini.mkdir(parents=True, exist_ok=True)

    diario = [
        {
            "fonte": e["fonte"],
            "esito": e["esito"],
            "quando": e["avviata_il"][:16].replace("T", " "),
            "nuove": e["nuove"],
            "riviste": e["riviste"],
            "messaggio": (e["messaggio"] or "")[:200],
        }
        for e in archivio.ultime_esecuzioni(8)
    ]

    cartella_prodotti = cartella / "prodotti"
    cartella_prodotti.mkdir(parents=True, exist_ok=True)

    for lingua in LINGUE:
        suffisso = "" if lingua == "it" else f".{lingua}"
        indice = []
        for scheda in pubblicati():
            prodotto, blocco, bozza = componi_prodotto(archivio, scheda, dimostrativo, lingua)
            if prodotto is None:
                if lingua == "it":
                    print(f"{scheda['id']}: nessun dato in archivio, non pubblicato")
                continue

            (cartella / f"sintesi-{scheda['id']}{suffisso}.html").write_text(blocco, encoding="utf-8")
            (cartella_bollettini / f"{scheda['id']}-{prodotto['ultimo_periodo']}{suffisso}.md").write_text(
                bozza, encoding="utf-8"
            )
            # Un file per prodotto: la pagina carica solo quello che mostra.
            (cartella_prodotti / f"{scheda['id']}{suffisso}.json").write_text(
                json.dumps(prodotto, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            indice.append({
                "id": prodotto["id"],
                "nome": prodotto["nome"],
                "sottotitolo": prodotto["sottotitolo"],
                "titolo_pagina": prodotto["titolo_pagina"],
                "descrizione_pagina": prodotto["descrizione_pagina"],
                "ultimo_periodo": prodotto["ultimo_periodo"],
                "prezzo_eur_kg": prodotto["prezzo_eur_kg"],
                "unita_origine": prodotto["serie"]["unita_origine"],
                "fonte": prodotto["serie"]["fonte"],
                "variazione_settimana": prodotto["variazioni"].get("settimana"),
                "variazione_anno": prodotto["variazioni"].get("anno"),
                "percentile": prodotto["stagionale"]["percentile"],
                "stagionale_attendibile": prodotto["stagionale"]["attendibile"],
                "voci_bollettino": len(prodotto["bollettino"]),
            })
            if lingua == "it":
                print(
                    f"{scheda['id']}: ultima settimana {prodotto['ultimo_periodo']}, "
                    f"{len(prodotto['storico'])} osservazioni in pagina, "
                    f"{len(prodotto['bollettino'])} voci di bollettino"
                    + (", flussi collegati" if prodotto.get("flussi") else ", flussi assenti")
                )

        if not indice:
            raise SystemExit("nessun prodotto con dati: niente da pubblicare")
        documento = {
            "generato_il": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "lingua": lingua,
            "stato": "dimostrativo" if dimostrativo else "in linea",
            "prodotti": indice,
            "diario": diario,
        }
        destinazione = cartella / f"mercati{suffisso}.json"
        destinazione.write_text(
            json.dumps(documento, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        peso_prodotti = sum(f.stat().st_size for f in cartella_prodotti.glob(f"*{suffisso}.json")
                            if (suffisso or ".en." not in f.name))
        print(
            f"Scritto {destinazione} ({destinazione.stat().st_size / 1024:.0f} kB) + "
            f"{len(indice)} file prodotto ({peso_prodotti / 1024:.0f} kB in tutto), "
            f"stato {documento['stato']}, lingua {lingua}"
        )

    # Controllo: etichette di anagrafica senza traduzione inglese.
    etichette = []
    for serie in archivio.elenco_serie():
        etichette += [serie[c] for c in ("indicatore", "fase", "mercato", "presentazione",
                                         "conservazione", "pezzatura", "note", "elaborazione")]
    from core.testi import TRADUZIONI_EN
    senza = sorted({e for e in etichette if e and traduci(e, "en") == e and e not in TRADUZIONI_EN})
    if senza:
        print(f"Attenzione: {len(senza)} etichette senza traduzione inglese (resta l'italiano):")
        for e in senza[:8]:
            print("   ", e[:90])

    archivio.chiudi()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="dati/archivio.sqlite")
    parser.add_argument("--uscita", default="web/data")
    a = parser.parse_args()
    raise SystemExit(esegui(a.db, a.uscita))
