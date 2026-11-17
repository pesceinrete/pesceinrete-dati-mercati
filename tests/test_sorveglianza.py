"""La sorveglianza propone, non dispone: questi test fissano i suoi limiti."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strumenti import sorveglianza

REGISTRO = """2026-10-15T06:21:05Z   File "ingest/ssb_laks.py", line 240, in analizza_csv
2026-10-15T06:21:05Z KeyError: nessuna categoria fresco/congelato riconosciuta nel CSV SSB
2026-10-15T06:21:05Z ##[error]Process completed with exit code 1."""


def test_individua_il_modulo_dal_registro():
    assert sorveglianza.modulo_coinvolto(REGISTRO)[0] == "ingest/ssb_laks.py"


def test_senza_percorsi_usa_la_fonte_citata():
    assert sorveglianza.modulo_coinvolto("Comext: scaricamento fallito (timeout)") == ["ingest/eurostat_comext.py"]


def test_estratto_toglie_i_timestamp():
    assert not sorveglianza.estratto(REGISTRO).startswith("2026-")


def test_interpreta_json_anche_dentro_le_virgolette_di_codice():
    r = sorveglianza.interpreta('```json\n{"diagnosi": "x", "causa": "altro", "correzione": null}\n```')
    assert r and r["causa"] == "altro"
    assert sorveglianza.interpreta("non è json") is None
    assert sorveglianza.interpreta('{"senza_diagnosi": 1}') is None


def test_correzione_solo_in_ingest_e_config():
    ok, motivo = sorveglianza.correzione_ammissibile(
        {"file": "core/metrics.py", "sostituzioni": [{"vecchio": "def aggrega", "nuovo": "def aggrega"}]}
    )
    assert not ok and "non modificabile" in motivo
    ok, motivo = sorveglianza.correzione_ammissibile(
        {"file": "tests/test_calcoli.py", "sostituzioni": [{"vecchio": "import", "nuovo": "import"}]}
    )
    assert not ok


def test_correzione_richiede_corrispondenza_unica():
    ok, motivo = sorveglianza.correzione_ammissibile(
        {"file": "ingest/ssb_laks.py", "sostituzioni": [{"vecchio": "import", "nuovo": "import"}]}
    )
    assert not ok and "esattamente una volta" in motivo
    ok, _ = sorveglianza.correzione_ammissibile(
        {"file": "ingest/ssb_laks.py", "sostituzioni": [{"vecchio": '"fresco": ("fresh", "fersk"),', "nuovo": '"fresco": ("fresh", "fersk", "chilled"),'}]}
    )
    assert ok


def test_nessuna_correzione_quando_il_modello_non_risponde():
    ok, motivo = sorveglianza.correzione_ammissibile(None)
    assert not ok and "nessuna" in motivo


def test_relazione_leggibile_anche_senza_modello():
    ctx = sorveglianza.contesto(REGISTRO)
    testo = sorveglianza.testo_relazione(None, ctx, "1", "nessuna proposta")
    assert "Il ciclo di aggiornamento è fallito" in testo
    assert "ingest/ssb_laks.py" in testo
