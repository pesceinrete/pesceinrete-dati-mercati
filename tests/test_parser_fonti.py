"""Parser delle fonti, provati su documenti costruiti nella loro struttura.

Le fonti reali non sono raggiungibili dall'ambiente in cui il codice è
stato scritto. Questi test riproducono il formato JSON-stat 2.0 di SSB e
di Eurostat Comext, compresi i dettagli che rompono un parser ingenuo:
l'ordine delle dimensioni, i valori mancanti, le etichette in una lingua
diversa da quella attesa, un mese in più da sommare fra due codici.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest import eurostat_comext, ssb_laks
from ingest.bce_cambi import aggrega_per_settimana
from ingest.eumofa_import import _normalizza_periodo, _numero


# --------------------------------------------------------------------------
# SSB 03024
# --------------------------------------------------------------------------


def documento_ssb(lingua="en", buchi=False):
    """JSON-stat 2.0 con tre settimane, fresco e congelato, prezzo e peso."""
    etichette = {
        "en": {"fresh": "Fresh or chilled salmon", "frozen": "Frozen salmon",
               "price": "Price per kilo (NOK)", "weight": "Weight (tonnes)"},
        "no": {"fresh": "Fersk laks", "frozen": "Fryst laks",
               "price": "Kilopris (kr)", "weight": "Vekt (tonn)"},
    }[lingua]
    settimane = ["2026U34", "2026U35", "2026U36"]

    # ordine delle dimensioni: merce, contenuto, tempo
    valori = []
    for merce in ("fresh", "frozen"):
        for contenuto in ("weight", "price"):
            for i, _ in enumerate(settimane):
                if merce == "fresh" and contenuto == "weight":
                    valori.append(17000 + 500 * i)
                elif merce == "fresh":
                    valori.append(75.0 + i)
                elif contenuto == "weight":
                    valori.append(None if (buchi and i == 1) else 700 + 10 * i)
                else:
                    valori.append(None if (buchi and i == 1) else 84.0 + i)

    return {
        "version": "2.0",
        "class": "dataset",
        "id": ["VareGrupper2", "ContentsCode", "Tid"],
        "size": [2, 2, len(settimane)],
        "dimension": {
            "VareGrupper2": {
                "label": "commodity group",
                "category": {"index": {"01": 0, "02": 1},
                             "label": {"01": etichette["fresh"], "02": etichette["frozen"]}},
            },
            "ContentsCode": {
                "label": "contents",
                "category": {"index": {"Vekt": 0, "Kilopris": 1},
                             "label": {"Vekt": etichette["weight"], "Kilopris": etichette["price"]}},
            },
            "Tid": {
                "label": "week",
                "category": {"index": {s: i for i, s in enumerate(settimane)},
                             "label": {s: s for s in settimane}},
            },
        },
        "role": {"time": ["Tid"]},
        "value": valori,
    }


def test_ssb_legge_fresco_e_congelato_in_inglese():
    serie = ssb_laks.analizza(documento_ssb("en"))
    fresco = serie[("fresco", "prezzo")]
    assert [o.periodo for o in fresco] == ["2026-W34", "2026-W35", "2026-W36"]
    assert fresco[-1].valore == pytest.approx(77.0)
    assert fresco[-1].quantita == pytest.approx(18000)
    assert serie[("congelato", "prezzo")][0].valore == pytest.approx(84.0)


def test_ssb_legge_anche_le_etichette_norvegesi():
    serie = ssb_laks.analizza(documento_ssb("no"))
    assert ("fresco", "prezzo") in serie and ("congelato", "prezzo") in serie


def test_ssb_valori_mancanti_non_diventano_zero():
    serie = ssb_laks.analizza(documento_ssb("en", buchi=True))
    congelato = serie[("congelato", "prezzo")]
    periodi = [o.periodo for o in congelato]
    assert "2026-W35" not in periodi  # settimana senza dato: assente, non zero


def test_ssb_valori_come_dizionario_sparso():
    """Il formato JSON-stat ammette 'value' come dizionario indice->valore."""
    documento = documento_ssb("en")
    documento["value"] = {str(i): v for i, v in enumerate(documento["value"]) if v is not None}
    serie = ssb_laks.analizza(documento)
    assert serie[("fresco", "prezzo")][-1].valore == pytest.approx(77.0)


def test_ssb_ordine_diverso_delle_dimensioni():
    """Se la fonte cambia l'ordine delle dimensioni il parser non deve sbagliare cella."""
    documento = documento_ssb("en")
    # riordino: tempo, merce, contenuto
    settimane = list(documento["dimension"]["Tid"]["category"]["index"])
    nuovi = []
    vecchi = documento["value"]
    for t in range(len(settimane)):
        for m in range(2):
            for c in range(2):
                nuovi.append(vecchi[(m * 2 + c) * len(settimane) + t])
    documento["id"] = ["Tid", "VareGrupper2", "ContentsCode"]
    documento["size"] = [len(settimane), 2, 2]
    documento["value"] = nuovi
    serie = ssb_laks.analizza(documento)
    assert serie[("fresco", "prezzo")][-1].valore == pytest.approx(77.0)
    assert serie[("congelato", "prezzo")][0].quantita == pytest.approx(700)


def test_ssb_etichette_sconosciute_fermano_il_carico():
    documento = documento_ssb("en")
    documento["dimension"]["VareGrupper2"]["category"]["label"] = {"01": "Gruppo A", "02": "Gruppo B"}
    with pytest.raises(KeyError):
        ssb_laks.analizza(documento)


def test_ssb_controlli_di_qualita():
    serie = ssb_laks.analizza(documento_ssb("en"))
    assert ssb_laks.controlla(serie[("fresco", "prezzo")], "prova") == []

    fresco = serie[("fresco", "prezzo")]
    fresco[-1].valore = fresco[-2].valore * 1.6  # salto del 60%
    problemi = ssb_laks.controlla(fresco, "prova")
    assert any("35%" in p for p in problemi)


# --------------------------------------------------------------------------
# Eurostat Comext
# --------------------------------------------------------------------------


def documento_comext(mesi, valori_eur, quantita_kg):
    """Risposta filtrata: una sola categoria per reporter, partner, prodotto, flusso."""
    return {
        "version": "2.0",
        "class": "dataset",
        "id": ["freq", "reporter", "partner", "product", "flow", "indicators", "time"],
        "size": [1, 1, 1, 1, 1, 2, len(mesi)],
        "dimension": {
            "freq": {"category": {"index": {"M": 0}}},
            "reporter": {"category": {"index": {"IT": 0}}},
            "partner": {"category": {"index": {"NO": 0}}},
            "product": {"category": {"index": {"03021411": 0}}},
            "flow": {"category": {"index": {"1": 0}}},
            "indicators": {"category": {"index": {"VALUE_IN_EUR": 0, "QUANTITY_IN_KG": 1}}},
            "time": {"category": {"index": {m: i for i, m in enumerate(mesi)}}},
        },
        "value": {
            **{str(i): v for i, v in enumerate(valori_eur) if v is not None},
            **{str(len(mesi) + i): q for i, q in enumerate(quantita_kg) if q is not None},
        },
    }


def test_comext_valore_unitario_per_mese():
    documento = documento_comext(["2026-05", "2026-06"], [1_500_000, 1_800_000], [200_000, 225_000])
    esito = eurostat_comext.analizza(documento)["NO"]
    assert esito["2026-M05"]["valore"] == pytest.approx(1_500_000)
    assert esito["2026-M06"]["quantita"] == pytest.approx(225_000)


def test_comext_accetta_i_formati_di_periodo():
    for grezzo in ("2026-05", "202605", "2026M05"):
        documento = documento_comext([grezzo], [100.0], [10.0])
        assert "2026-M05" in eurostat_comext.analizza(documento)["NO"]


def test_comext_mese_senza_valore_viene_saltato():
    documento = documento_comext(["2026-05", "2026-06"], [1_000.0, None], [100.0, None])
    esito = eurostat_comext.analizza(documento)["NO"]
    assert "2026-M06" not in esito


def test_comext_indicatori_non_riconosciuti_fermano_il_carico():
    documento = documento_comext(["2026-05"], [1.0], [1.0])
    documento["dimension"]["indicators"]["category"]["index"] = {"A": 0, "B": 1}
    with pytest.raises(KeyError):
        eurostat_comext.analizza(documento)


# --------------------------------------------------------------------------
# BCE
# --------------------------------------------------------------------------


def test_bce_media_settimanale_e_settimane_parziali():
    csv = "\n".join([
        "KEY,FREQ,CURRENCY,TIME_PERIOD,OBS_VALUE",
        "EXR.D.NOK.EUR.SP00.A,D,NOK,2026-09-07,11.50",
        "EXR.D.NOK.EUR.SP00.A,D,NOK,2026-09-08,11.60",
        "EXR.D.NOK.EUR.SP00.A,D,NOK,2026-09-09,11.70",
        "EXR.D.NOK.EUR.SP00.A,D,NOK,2026-09-10,",          # giorno di chiusura
        "EXR.D.NOK.EUR.SP00.A,D,NOK,2026-09-14,11.80",     # settimana 38, un giorno solo
    ])
    osservazioni, avvisi = aggrega_per_settimana(csv)
    per_periodo = {o.periodo: o for o in osservazioni}
    assert per_periodo["2026-W37"].valore == pytest.approx(11.6)
    assert per_periodo["2026-W37"].quantita == 3
    assert any("2026-W38" in a for a in avvisi)  # segnalata come parziale


# --------------------------------------------------------------------------
# EUMOFA da file
# --------------------------------------------------------------------------


def test_eumofa_normalizza_periodi_e_numeri():
    assert _normalizza_periodo("2026-W12", None) == "2026-W12"
    assert _normalizza_periodo("2026/12", None) == "2026-W12"
    assert _normalizza_periodo("12", "2026") == "2026-W12"
    assert _normalizza_periodo("2026-03-23", None) == "2026-W13"
    assert _numero("1.234,56") == pytest.approx(1234.56)
    assert _numero("1234,5") == pytest.approx(1234.5)
    assert _numero("-") is None


# --------------------------------------------------------------------------
# Risposte reali dei servizi (campioni ottenuti il 3 ottobre 2026)
# --------------------------------------------------------------------------

CSV_SSB_REALE = '''"VareGrupper2 - commodity group";"Tid - week";"ContentsCode - contents";"03024: Export of salmon, fish-farm bred,"
"01 - Fish-farm bred salmon, fresh or chilled";"2026U32 - 2026U32";"Vekt - Weight (tonnes)";28602
"01 - Fish-farm bred salmon, fresh or chilled";"2026U32 - 2026U32";"Kilopris - Price per kg (NOK)";74.90
"01 - Fish-farm bred salmon, fresh or chilled";"2026U33 - 2026U33";"Vekt - Weight (tonnes)";28762
"01 - Fish-farm bred salmon, fresh or chilled";"2026U33 - 2026U33";"Kilopris - Price per kg (NOK)";72.66
"01 - Fish-farm bred salmon, fresh or chilled";"2026U34 - 2026U34";"Vekt - Weight (tonnes)";31378
"01 - Fish-farm bred salmon, fresh or chilled";"2026U34 - 2026U34";"Kilopris - Price per kg (NOK)";73.52
"02 - Fish-farm bred salmon, frozen";"2026U32 - 2026U32";"Vekt - Weight (tonnes)";638
"02 - Fish-farm bred salmon, frozen";"2026U32 - 2026U32";"Kilopris - Price per kg (NOK)";74.09
"02 - Fish-farm bred salmon, frozen";"2026U33 - 2026U33";"Vekt - Weight (tonnes)";751
"02 - Fish-farm bred salmon, frozen";"2026U33 - 2026U33";"Kilopris - Price per kg (NOK)";69.12
"02 - Fish-farm bred salmon, frozen";"2026U34 - 2026U34";"Vekt - Weight (tonnes)";727
"02 - Fish-farm bred salmon, frozen";"2026U34 - 2026U34";"Kilopris - Price per kg (NOK)";75.03
'''


def test_ssb_csv_v2_reale():
    serie = ssb_laks.analizza_csv(CSV_SSB_REALE)
    fresco = serie[("fresco", "prezzo")]
    assert [o.periodo for o in fresco] == ["2026-W32", "2026-W33", "2026-W34"]
    assert fresco[-1].valore == pytest.approx(73.52)
    assert fresco[-1].quantita == pytest.approx(31378)
    congelato = serie[("congelato", "prezzo")]
    assert congelato[0].valore == pytest.approx(74.09)
    assert ssb_laks.controlla(fresco, "fresco") == []


def test_ssb_csv_valori_mancanti():
    csv = CSV_SSB_REALE.replace(
        '"01 - Fish-farm bred salmon, fresh or chilled";"2026U33 - 2026U33";"Kilopris - Price per kg (NOK)";72.66',
        '"01 - Fish-farm bred salmon, fresh or chilled";"2026U33 - 2026U33";"Kilopris - Price per kg (NOK)";..',
    )
    fresco = ssb_laks.analizza_csv(csv)[("fresco", "prezzo")]
    w33 = next(o for o in fresco if o.periodo == "2026-W33")
    assert w33.valore is None and w33.quantita == pytest.approx(28762)


def documento_comext_reale(partners, mesi):
    """Struttura verificata su DS-045409: indicatori VALUE_IN_EUROS e QUANTITY_IN_100KG."""
    return {
        "version": "2.0", "class": "dataset",
        "id": ["freq", "reporter", "partner", "product", "flow", "indicators", "time"],
        "size": [1, 1, len(partners), 1, 1, 2, len(mesi)],
        "dimension": {
            "freq": {"category": {"index": {"M": 0}}},
            "reporter": {"category": {"index": {"IT": 0}}},
            "partner": {"category": {"index": {p: i for i, p in enumerate(partners)}}},
            "product": {"category": {"index": {"03021411": 0}}},
            "flow": {"category": {"index": {"1": 0}}},
            "indicators": {"category": {"index": {"VALUE_IN_EUROS": 0, "QUANTITY_IN_100KG": 1}}},
            "time": {"category": {"index": {m: i for i, m in enumerate(mesi)}}},
        },
        "value": {},
    }


def test_comext_quintali_convertiti_in_chili_e_totale_mondo():
    doc = documento_comext_reale(["NO", "GR", "EU27_2020"], ["2026-06", "2026-07"])
    # ordine lineare: partner x indicatore x tempo
    valori = {}
    def metti(ip, ii, it, v):
        valori[str((ip * 2 + ii) * 2 + it)] = v
    metti(0, 0, 0, 1_500_000); metti(0, 1, 0, 2_000)    # NO: €1,5M, 2000 quintali = 200 t
    metti(1, 0, 0, 300_000);   metti(1, 1, 0, 500)      # GR: €0,3M, 50 t
    metti(2, 0, 0, 9_999_999); metti(2, 1, 0, 99_999)   # aggregato UE: da ignorare nel totale
    doc["value"] = valori
    r = eurostat_comext.analizza(doc)
    assert r["NO"]["2026-M06"]["quantita"] == pytest.approx(200_000)       # kg
    mondo = eurostat_comext.somma_partner(r, "WORLD")
    assert mondo["2026-M06"]["quantita"] == pytest.approx(250_000)        # solo paesi, non aggregati
    assert mondo["2026-M06"]["valore"] == pytest.approx(1_800_000)


def test_comext_usa_il_totale_mondo_della_fonte_se_presente():
    doc = documento_comext_reale(["NO", "WORLD"], ["2026-06"])
    doc["value"] = {"0": 100.0, "1": 10.0, "2": 400.0, "3": 40.0}
    r = eurostat_comext.analizza(doc)
    assert eurostat_comext.somma_partner(r, "WORLD")["2026-M06"]["valore"] == pytest.approx(400.0)


def test_rnm_etichette_reali_senza_accenti_e_con_barre():
    from ingest.rnm_rungis import EstrattoreTabelle, cerca_righe, data_dalla_pagina, numero_francese
    html = """<p>dernière cotation avant le 02-10-2026</p><table>
      <tr><th>produit</th><th>prix moyen</th><th>mini</th><th>maxi</th></tr>
      <tr><td>DAURADE Royale aquaculture 400-600g U.E.</td><td>8.50</td><td>8.00</td><td>9.00</td></tr>
      <tr><td>DAURADE Royale aquaculture 600-800g U.E.</td><td>9.20</td><td>9.00</td><td>9.50</td></tr></table>"""
    e = EstrattoreTabelle(); e.feed(html)
    righe = cerca_righe(e.tabelle, "daurade royale aquaculture 400/600")
    assert len(righe) == 1 and numero_francese(righe[0][1]) == pytest.approx(8.5)
    assert str(data_dalla_pagina(html)) == "2026-10-02"
