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
from ingest import eumofa_import


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
# EUMOFA, importazioni settimanali
# --------------------------------------------------------------------------

INT_EUMOFA = "year~week~issuer~origin~goods~volume(Kg)~value(EUR)"


def file_eumofa(settimane: dict[int, int], extra: list[str] = ()) -> bytes:
    """File annuale 2026 nel formato della fonte.

    `settimane` dice quante righe "di riempimento" (altri Stati, altri
    prodotti) ha ogni settimana: servono a far giudicare la completezza.
    Per ogni settimana c'è anche l'orata turca verso l'Italia, 1.000 kg a
    6,00 €/kg più 10 centesimi per settimana.
    """
    righe = [INT_EUMOFA]
    for settimana, quante in settimane.items():
        righe += [f"2026~{settimana:02d}~Spain~China~03074399-Cuttle fish and squid, frozen~10.0~40.0"] * quante
        prezzo = 6.0 + settimana / 10
        righe.append(f"2026~{settimana:02d}~Italy~Turkey~03028530-Fresh or chilled gilt-head sea bream~1000.0~{1000 * prezzo}")
    righe += list(extra)
    return "\n".join(righe).encode("utf-8")


def test_eumofa_legge_italia_per_provenienza_e_scarta_il_resto():
    serie = eumofa_import.definizioni()
    extra = [
        # stessa specie, altro Stato importatore: non è Italia
        "2026~03~Greece~Turkey~03028530-Fresh or chilled gilt-head sea bream~5000.0~10000.0",
        # Italia, altra provenienza: entra nel totale, non nella serie turca
        "2026~03~Italy~Albania~03028530-Fresh or chilled gilt-head sea bream~1000.0~5000.0",
        # Italia, altro sparide con codice diverso: fuori
        "2026~03~Italy~Turkey~03028590-Fresh or chilled sea bream (other)~9000.0~9000.0",
        # riga senza peso: saltata
        "2026~03~Italy~Turkey~03028530-Fresh or chilled gilt-head sea bream~0.0~500.0",
    ]
    letto = eumofa_import.leggi(file_eumofa({s: 20 for s in range(1, 11)}, extra), serie)
    turca = letto["somme"]["eumofa.it.import.orata.tr.settimanale"]["2026-W03"]
    assert turca == [1000.0, pytest.approx(6300.0)]
    totale = letto["somme"]["eumofa.it.import.orata.world.settimanale"]["2026-W03"]
    assert totale == [2000.0, pytest.approx(11300.0)]
    assert letto["somme"]["eumofa.it.import.orata.al.settimanale"]["2026-W03"] == [1000.0, 5000.0]


def test_eumofa_pubblica_solo_le_settimane_complete():
    # dieci settimane piene, la 11 a metà, la 12 appena cominciata
    conteggi = {s: 20 for s in range(1, 11)} | {11: 9, 12: 3}
    letto = eumofa_import.leggi(file_eumofa(conteggi), eumofa_import.definizioni())
    complete, tipica = eumofa_import.settimane_complete(letto["per_settimana"])
    assert tipica == 21                      # 20 di riempimento + la riga italiana
    assert "2026-W10" in complete
    assert "2026-W11" not in complete        # sotto il 70% della settimana tipica
    assert "2026-W12" not in complete        # l'ultima del file non esce mai
    oss = eumofa_import.osservazioni(
        letto["somme"]["eumofa.it.import.orata.tr.settimanale"], complete)
    assert [o.periodo for o in oss][-1] == "2026-W10"
    assert oss[-1].valore == pytest.approx(7.0) and oss[-1].quantita == pytest.approx(1.0)  # tonnellate


def test_eumofa_ultima_settimana_esclusa_anche_se_sembra_piena():
    letto = eumofa_import.leggi(file_eumofa({s: 20 for s in range(1, 11)}), eumofa_import.definizioni())
    complete, _ = eumofa_import.settimane_complete(letto["per_settimana"])
    assert "2026-W10" not in complete and "2026-W09" in complete


def test_eumofa_anno_chiuso_pubblica_anche_l_ultima_settimana():
    letto = eumofa_import.leggi(file_eumofa({s: 20 for s in range(1, 11)}), eumofa_import.definizioni())
    complete, _ = eumofa_import.settimane_complete(letto["per_settimana"], anno_chiuso=True)
    assert "2026-W10" in complete and len(complete) == 10


def test_eumofa_a_inizio_anno_vale_la_settimana_tipica_dell_anno_prima():
    letto = eumofa_import.leggi(file_eumofa({1: 20, 2: 20, 3: 4}), eumofa_import.definizioni())
    # senza riferimento la mediana di tre settimane non basta a giudicare
    complete, tipica = eumofa_import.settimane_complete(letto["per_settimana"], tipica_di_riserva=40)
    assert tipica == 40 and complete == set()       # 21 righe su 40 tipiche: incomplete
    complete, _ = eumofa_import.settimane_complete(letto["per_settimana"], tipica_di_riserva=22)
    assert complete == {"2026-W01", "2026-W02"}


def test_eumofa_buchi_storici_restano_buchi():
    conteggi = {s: 20 for s in range(1, 14)} | {5: 3}       # la settimana 5 è bucata alla fonte
    letto = eumofa_import.leggi(file_eumofa(conteggi), eumofa_import.definizioni())
    complete, _ = eumofa_import.settimane_complete(letto["per_settimana"])
    assert "2026-W05" not in complete and "2026-W04" in complete and "2026-W06" in complete


def test_eumofa_intestazione_cambiata_ferma_il_carico():
    with pytest.raises(ValueError, match="cambiato struttura"):
        eumofa_import.leggi(b"year;week;issuer\n2026;1;Italy", eumofa_import.definizioni())


def test_eumofa_riconosce_le_grafie_alternative_dei_paesi():
    extra = ["2026~03~Italy~T\u00fcrkiye~03028530-Fresh or chilled gilt-head sea bream~1000.0~6000.0"]
    letto = eumofa_import.leggi(file_eumofa({s: 20 for s in range(1, 6)}, extra), eumofa_import.definizioni())
    assert letto["somme"]["eumofa.it.import.orata.tr.settimanale"]["2026-W03"][0] == 2000.0


def test_comext_dimezza_la_richiesta_quando_la_risposta_e_troppo_grande(monkeypatch):
    """413 su un anno intero: semestre, trimestre, fino a un intervallo accettato."""
    import urllib.error
    import urllib.parse

    chiamate = []

    def finta(url, timeout=90):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        dal, al = q["sinceTimePeriod"], q.get("untilTimePeriod")
        chiamate.append((dal, al))
        mesi = (int(al[:4]) * 12 + int(al[5:])) - (int(dal[:4]) * 12 + int(dal[5:])) + 1 if al else 99
        if mesi > 3:
            raise urllib.error.HTTPError(url, 413, "troppo grande", None, None)
        return {"dal": dal, "al": al}

    monkeypatch.setattr(eurostat_comext, "scarica", finta)
    monkeypatch.setattr(eurostat_comext, "analizza",
                        lambda d: {"NO": {d["dal"]: {"valore": 1.0, "quantita": 1.0}}})
    risultato = eurostat_comext._scarica_mesi("03021400", 2025, 1, 12)
    assert sorted(risultato["NO"]) == ["2025-01", "2025-04", "2025-07", "2025-10"]
    assert ("2025-01", "2025-12") in chiamate and ("2025-01", "2025-03") in chiamate


def test_comext_codice_inesistente_non_rompe_il_carico(monkeypatch):
    import urllib.error

    def sempre_413(url, timeout=90):
        raise urllib.error.HTTPError(url, 413, "troppo grande", None, None)

    monkeypatch.setattr(eurostat_comext, "scarica", sempre_413)
    eurostat_comext._CACHE.clear()
    assert eurostat_comext.per_codice("99999999", 2025) == {}
    assert "non esiste" in eurostat_comext.STATO_CODICI["99999999"]
    eurostat_comext._CACHE.clear()


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
