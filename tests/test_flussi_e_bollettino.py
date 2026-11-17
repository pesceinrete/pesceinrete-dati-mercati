"""Verifiche su periodi mensili, totali mobili e bollettino automatico."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import bollettino, isoweek, mese


def oss(periodo, valore, quantita=None):
    return {"periodo": periodo, "valore": valore, "quantita": quantita}


# --------------------------------------------------------------------------
# Periodi mensili
# --------------------------------------------------------------------------


def test_le_due_chiavi_non_si_confondono():
    assert mese.e_mensile("2026-M03")
    assert not mese.e_mensile("2026-W03")


def test_formato_eurostat():
    assert mese.da_formato_eurostat("202603") == "2026-M03"
    assert mese.da_formato_eurostat("2026M03") == "2026-M03"
    assert mese.da_formato_eurostat("non-un-periodo") is None


def test_spostamento_attraverso_capodanno():
    assert mese.sposta("2026-M01", -1) == "2025-M12"
    assert mese.sposta("2025-M12", 2) == "2026-M02"


def test_totale_mobile_pondera_il_valore_unitario():
    serie = [oss("2026-M01", 8.0, 1000.0), oss("2026-M02", 6.0, 3000.0)]
    totale = mese.somma_dodici_mesi(serie, "2026-M02")
    # media semplice 7,00; ponderata (8000 + 18000) / 4000 = 6,50
    assert totale["valore_unitario"] == pytest.approx(6.5)
    assert totale["quantita"] == pytest.approx(4000.0)


def test_totale_mobile_dichiara_i_mesi_mancanti():
    serie = [oss(mese.chiave(2026, m), 7.0, 100.0) for m in range(1, 7)]
    totale = mese.somma_dodici_mesi(serie, "2026-M06")
    assert totale["mesi_usati"] == 6
    assert "2025-M12" in totale["mesi_mancanti"]


# --------------------------------------------------------------------------
# Bollettino
# --------------------------------------------------------------------------


def _serie_piatta(valore=10.0, quantita=1000.0, fino_a=2025):
    dati = []
    for anno in range(2021, fino_a + 1):
        for settimana in range(1, 53):
            dati.append(oss(isoweek.chiave(anno, settimana), valore, quantita))
    return dati


def test_settimana_tranquilla_non_produce_voci():
    serie = _serie_piatta() + [
        oss(isoweek.chiave(2026, s), 10.0, 1000.0) for s in range(1, 27)
    ]
    esito = bollettino.componi(serie, serie, "2026-W26")
    assert esito.vuoto
    assert "Nessun movimento fuori dall'ordinario" in esito.markdown()


def test_passaggio_di_fascia_stagionale_segnalato():
    serie = _serie_piatta()
    for settimana in range(1, 23):
        serie.append(oss(isoweek.chiave(2026, settimana), 9.0, 1000.0))
    for settimana in range(23, 27):
        serie.append(oss(isoweek.chiave(2026, settimana), 14.0, 1000.0))

    esito = bollettino.componi(serie, serie, "2026-W26")
    titoli = " ".join(v.titolo for v in esito.voci)
    assert "posizione rispetto alla stagione" in titoli
    assert any(v.rilievo == "alto" for v in esito.voci)


def test_movimento_dovuto_al_cambio_riconosciuto():
    """In valuta d'origine sale, in euro scende: è il cambio, non il mercato."""
    origine, euro = [], []
    for anno in (2024, 2025):
        for settimana in range(1, 53):
            origine.append(oss(isoweek.chiave(anno, settimana), 100.0, 1000.0))
            euro.append(oss(isoweek.chiave(anno, settimana), 10.0, 1000.0))
    origine.append(oss("2026-W01", 100.0, 1000.0))
    euro.append(oss("2026-W01", 10.0, 1000.0))
    origine.append(oss("2026-W02", 103.0, 1000.0))   # +3% in corone
    euro.append(oss("2026-W02", 9.8, 1000.0))        # -2% in euro

    esito = bollettino.componi(euro, origine, "2026-W02")
    titoli = " ".join(v.titolo for v in esito.voci)
    assert "non è un movimento di mercato" in titoli


def test_stessa_direzione_non_genera_avviso_sul_cambio():
    origine, euro = [], []
    for settimana in (1, 2):
        origine.append(oss(isoweek.chiave(2026, settimana), 100.0 + settimana, 1000.0))
        euro.append(oss(isoweek.chiave(2026, settimana), 10.0 + settimana * 0.1, 1000.0))
    esito = bollettino.componi(euro, origine, "2026-W02")
    assert "cambio" not in " ".join(v.titolo for v in esito.voci).lower()


def test_revisioni_riportate():
    serie = _serie_piatta() + [oss("2026-W01", 10.0, 1000.0)]
    revisioni = [
        {"periodo": "2025-W50", "valore_precedente": 9.0, "valore_nuovo": 9.4},
        {"periodo": "2025-W51", "valore_precedente": 9.1, "valore_nuovo": 9.5},
    ]
    esito = bollettino.componi(serie, serie, "2026-W01", revisioni)
    testo = esito.markdown()
    assert "corretto settimane già pubblicate" in testo
    assert "2025-W50" in testo


def test_le_voci_di_rilievo_vengono_prima():
    serie = _serie_piatta()
    for settimana in range(1, 23):
        serie.append(oss(isoweek.chiave(2026, settimana), 9.0, 1000.0))
    for settimana in range(23, 27):
        serie.append(oss(isoweek.chiave(2026, settimana), 14.0, 1000.0))
    revisioni = [{"periodo": "2025-W10", "valore_precedente": 1, "valore_nuovo": 2}]

    esito = bollettino.componi(serie, serie, "2026-W26", revisioni)
    assert esito.voci[0].rilievo == "alto"


def test_il_bollettino_non_scrive_cause():
    """Il testo generato descrive fatti: le spiegazioni le mette la redazione."""
    serie = _serie_piatta()
    for settimana in range(1, 23):
        serie.append(oss(isoweek.chiave(2026, settimana), 9.0, 1000.0))
    for settimana in range(23, 27):
        serie.append(oss(isoweek.chiave(2026, settimana), 14.0, 1000.0))
    testo = bollettino.componi(serie, serie, "2026-W26").markdown().lower()
    for espressione in ("a causa di", "perché la domanda", "dovuto alla", "per effetto della"):
        assert espressione not in testo


# --------------------------------------------------------------------------
# Lingua
# --------------------------------------------------------------------------


def test_bollettino_in_inglese_usa_i_testi_inglesi():
    serie = _serie_piatta()
    for settimana in range(1, 23):
        serie.append(oss(isoweek.chiave(2026, settimana), 9.0, 1000.0))
    for settimana in range(23, 27):
        serie.append(oss(isoweek.chiave(2026, settimana), 14.0, 1000.0))
    esito = bollettino.componi(serie, serie, "2026-W26", nome_prodotto="Atlantic salmon", lingua="en")
    testo = esito.markdown()
    assert "seasonal position has changed" in testo
    assert "Week 2026-W26" in testo
    assert "settimane" not in testo.lower()


def test_lingua_sconosciuta_ricade_sull_italiano():
    serie = _serie_piatta() + [oss("2026-W01", 10.0, 1000.0)]
    esito = bollettino.componi(serie, serie, "2026-W01", lingua="xx")
    assert esito.lingua == "it"


def test_lettura_stagionale_bilingue():
    from core import metrics
    serie = _serie_piatta() + [oss("2026-W26", 15.0, 1000.0)]
    posizione = metrics.posizione_stagionale(serie, "2026-W26")
    assert "alto" in posizione.lettura("it")
    assert "Higher" in posizione.lettura("en")


def test_traduzione_anagrafica_non_restituisce_mai_vuoto():
    from core.testi import traduci
    assert traduci("Prezzo medio all'esportazione", "en") == "Average export price"
    assert traduci("Etichetta mai vista", "en") == "Etichetta mai vista"
    assert traduci("Prezzo medio all'esportazione", "it") == "Prezzo medio all'esportazione"
    assert traduci(None, "en") is None
