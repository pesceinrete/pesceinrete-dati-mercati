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

from config.prodotti import FONTI_PREZZO, PAESI, PRODOTTI, pubblicati, serie_flussi
from core.testi import traduci
from ingest.eurostat_comext import definizioni as definizioni_comext
from ingest.rnm_rungis import serie_dal_registro as serie_rnm


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
        assert flussi["principale"] in flussi["partner"], p["id"]


def test_una_serie_comext_per_ogni_coppia_specie_partner():
    serie = definizioni_comext()
    attese = sum(len(p["flussi"]["partner"]) for p in pubblicati())
    assert len(serie) == attese
    for p in pubblicati():
        for partner in p["flussi"]["partner"]:
            assert serie_flussi(p, partner) in serie


def test_serie_rnm_coerenti_con_il_registro():
    ids = {s["id"] for s in serie_rnm()}
    for p in pubblicati():
        if p["prezzo"]["fonte"] == "rnm":
            assert p["prezzo"]["serie"] in ids, p["id"]
            assert p["prezzo"].get("rnm_etichetta"), p["id"]


def test_tutte_le_etichette_del_registro_hanno_la_traduzione():
    """Un'etichetta non tradotta finisce in italiano nella pagina inglese."""
    senza = []
    for p in pubblicati():
        campi = [p["nome"], p["sottotitolo"], p["titolo_pagina"], p["descrizione_pagina"],
                 p["flussi"]["descrizione"]]
        campi += [v for v in p["prezzo"].get("anagrafica", {}).values()]
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
