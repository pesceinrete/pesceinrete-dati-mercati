"""Coerenza del registro delle specie.

Il registro è configurazione, non codice, e quindi è il posto dove un
errore di battitura passa inosservato: un codice doganale di sette cifre,
un partner non in elenco, un'etichetta senza traduzione che finisce in
italiano nella pagina inglese. Questi controlli lo impediscono.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.prodotti import (FONTI_PREZZO, PAESI, PAESI_EUMOFA, PRODOTTI, con_eumofa, pubblicati,
                             serie_eumofa, serie_flussi)
from core.testi import traduci
from ingest.eurostat_comext import definizioni as definizioni_comext
from ingest.eumofa_import import definizioni as definizioni_eumofa


def test_identificativi_unici_e_puliti():
    ids = [p["id"] for p in PRODOTTI]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z_]+", i) for i in ids), ids


def test_ogni_specie_ha_prezzo_e_fonte_dichiarata():
    for p in pubblicati():
        assert p["prezzo"]["serie"], p["id"]
        assert p["prezzo"]["fonte"] in FONTI_PREZZO, p["id"]


def test_codici_doganali_a_otto_cifre_e_partner_noti():
    for p in pubblicati():
        flussi = p["flussi"]
        for codice in flussi["codici"]:
            assert re.fullmatch(r"\d{8}", codice), (p["id"], codice)
        for partner in flussi["partner"]:
            assert partner in PAESI, (p["id"], partner)
        assert "WORLD" in flussi["partner"], p["id"]
        assert flussi["principale"] == "auto" or flussi["principale"] in flussi["partner"], p["id"]


def test_una_serie_comext_per_ogni_coppia_specie_partner():
    serie = definizioni_comext()
    attese = sum(len(p["flussi"]["partner"]) for p in pubblicati())
    assert len(serie) == attese
    for p in pubblicati():
        for partner in p["flussi"]["partner"]:
            assert serie_flussi(p, partner) in serie


def test_serie_eumofa_coerenti_con_il_registro():
    serie = definizioni_eumofa()
    for p in con_eumofa():
        voce = p["eumofa"]
        assert p["prezzo"]["fonte"] == "eumofa", p["id"]
        # il prezzo in copertina è la serie della provenienza principale
        assert p["prezzo"]["serie"] == serie_eumofa(p, voce["principale"]), p["id"]
        assert p["prezzo"]["serie"] in serie, p["id"]
        # il totale serve per le quote: c'è sempre
        assert serie_eumofa(p, "WORLD") in serie, p["id"]
        for codice in voce["codici"]:
            assert re.fullmatch(r"\d{8}", codice), (p["id"], codice)
        for partner in [voce["principale"], *voce["altre"]]:
            assert partner in PAESI, (p["id"], partner)
            assert partner == "WORLD" or partner in PAESI_EUMOFA, (p["id"], partner)


def test_nessuna_fonte_esclusa_resta_nel_registro():
    """Rungis e BMTI sono usciti dal progetto: non devono rientrare per sbaglio."""
    assert set(FONTI_PREZZO) == {"ssb", "eumofa"}
    for p in PRODOTTI:
        assert "rnm" not in p["prezzo"]["serie"] and "bmti" not in p["prezzo"]["serie"]


def test_etichette_delle_serie_eumofa_tradotte():
    senza = []
    for voce in definizioni_eumofa().values():
        for campo in ("prodotto", "presentazione", "conservazione", "pezzatura", "mercato", "fase",
                      "indicatore", "fonte", "elaborazione", "note"):
            testo = voce["anagrafica"][campo]
            if traduci(testo, "en") == testo:
                senza.append(testo[:60])
    assert not senza, sorted(set(senza))


def test_tutte_le_etichette_del_registro_hanno_la_traduzione():
    """Un'etichetta non tradotta finisce in italiano nella pagina inglese."""
    senza = []
    for p in pubblicati():
        campi = [p["nome"], p["sottotitolo"], p["titolo_pagina"], p["descrizione_pagina"],
                 p["flussi"]["descrizione"]]
        campi += [p.get("eumofa", {}).get(c) for c in ("prodotto", "presentazione", "conservazione")]
        campi += [d for coppia in p.get("domande", []) for d in coppia]
        for testo in campi:
            if testo and traduci(testo, "en") == testo and not re.fullmatch(r"[\d\- g]+", testo):
                senza.append((p["id"], testo[:60]))
    assert not senza, senza


def test_paesi_tradotti_nelle_due_lingue():
    for codice, (it, en) in PAESI.items():
        assert it and en, codice
    assert traduci("Importazioni in Italia dalla Grecia", "en") == "Imports into Italy from Greece"
    assert traduci("Importazioni in Italia dall'Ecuador", "en") == "Imports into Italy from Ecuador"
