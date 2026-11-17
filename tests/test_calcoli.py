"""Verifiche sui calcoli che finiscono in pagina.

Ogni numero pubblicato deve essere riproducibile a mano. I casi limite qui
coperti sono quelli che in un portale di dati producono figure sbagliate
senza che nessuno se ne accorga: periodi incompleti, medie non ponderate,
confronti fra periodi di lunghezza diversa, settimana 53, revisioni.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import isoweek, metrics
from core.store import Archivio, Osservazione


def osservazione(periodo, valore, quantita=None):
    return {"periodo": periodo, "valore": valore, "quantita": quantita}


# --------------------------------------------------------------------------
# Settimane ISO
# --------------------------------------------------------------------------


def test_anni_a_53_settimane():
    assert isoweek.settimane_nell_anno(2020) == 53
    assert isoweek.settimane_nell_anno(2021) == 52


def test_confronto_annuale_da_settimana_53():
    # 2021 non ha la settimana 53: il confronto ripiega sulla 52
    assert isoweek.stessa_settimana_anno_precedente("2021-W01") == "2020-W01"
    assert isoweek.stessa_settimana_anno_precedente("2020-W53") == "2019-W52"


def test_finestra_stagionale_a_cavallo_dell_anno():
    assert isoweek.finestra_stagionale(1) == [1, 2, 3, 51, 52]
    assert isoweek.finestra_stagionale(26) == [24, 25, 26, 27, 28]


def test_formato_ssb():
    assert isoweek.da_formato_ssb("2025U09") == "2025-W09"


def test_intervallo_attraversa_capodanno():
    settimane = isoweek.intervallo("2020-W52", "2021-W02")
    assert settimane == ["2020-W52", "2020-W53", "2021-W01", "2021-W02"]


# --------------------------------------------------------------------------
# Aggregazione
# --------------------------------------------------------------------------


def test_media_ponderata_non_coincide_con_media_semplice():
    dati = [
        osservazione("2026-W01", 10.0, 100.0),
        osservazione("2026-W02", 20.0, 900.0),
    ]
    aggregato = metrics.aggrega(dati, "2026-W01", "2026-W02")
    # media semplice: 15. Ponderata: (1000 + 18000) / 1000 = 19
    assert aggregato.prezzo_medio_ponderato == pytest.approx(19.0)
    assert aggregato.volume_totale == pytest.approx(1000.0)
    assert aggregato.valore_totale == pytest.approx(19000.0)
    assert aggregato.completo


def test_settimana_mancante_segnalata_e_non_interpolata():
    dati = [osservazione("2026-W01", 10.0, 100.0), osservazione("2026-W03", 12.0, 100.0)]
    aggregato = metrics.aggrega(dati, "2026-W01", "2026-W03")
    assert aggregato.settimane_attese == 3
    assert aggregato.settimane_usate == 2
    assert not aggregato.completo
    assert "2026-W02" in aggregato.avvertenze[0]


def test_senza_volumi_si_dichiara_la_media_semplice():
    dati = [osservazione("2026-W01", 10.0), osservazione("2026-W02", 20.0)]
    aggregato = metrics.aggrega(dati, "2026-W01", "2026-W02")
    assert aggregato.prezzo_medio_ponderato == pytest.approx(15.0)
    assert any("non ponderata" in a for a in aggregato.avvertenze)


# --------------------------------------------------------------------------
# Confronti
# --------------------------------------------------------------------------


def test_confronto_fra_periodi_disomogenei_non_produce_delta_sui_volumi():
    corrente = metrics.aggrega(
        [osservazione(f"2026-W0{i}", 10.0, 100.0) for i in range(1, 6)],
        "2026-W01",
        "2026-W05",
    )
    riferimento = metrics.aggrega(
        [osservazione(f"2025-W0{i}", 10.0, 100.0) for i in range(1, 5)],
        "2025-W01",
        "2025-W04",
    )
    confronto = metrics.confronta(corrente, riferimento)
    assert not confronto.omogeneo
    assert confronto.delta_volume_percentuale is None  # 500 contro 400 non è +25%
    assert confronto.delta_prezzo_percentuale == pytest.approx(0.0)
    assert confronto.avvertenze


def test_periodo_precedente_ha_la_stessa_lunghezza():
    assert metrics.periodo_precedente("2026-W10", "2026-W13") == ("2026-W06", "2026-W09")


def test_delta_a_una_quattro_cinquantadue_settimane():
    dati = [osservazione(isoweek.chiave(2025, s), 10.0, 100.0) for s in range(1, 53)]
    dati += [osservazione(isoweek.chiave(2026, s), 12.0, 100.0) for s in range(1, 11)]
    variazioni = metrics.variazioni_recenti(dati, "2026-W10")
    assert variazioni["settimana"] == pytest.approx(0.0)
    assert variazioni["anno"] == pytest.approx(20.0)


# --------------------------------------------------------------------------
# Stagionalità
# --------------------------------------------------------------------------


def _serie_stagionale():
    dati = []
    for anno in (2021, 2022, 2023, 2024, 2025):
        for settimana in range(1, 53):
            dati.append(osservazione(isoweek.chiave(anno, settimana), 10.0, 100.0))
    return dati


def test_prezzo_alto_per_il_periodo_viene_riconosciuto():
    dati = _serie_stagionale()
    dati.append(osservazione("2026-W26", 15.0, 100.0))
    posizione = metrics.posizione_stagionale(dati, "2026-W26")
    assert posizione.percentile == pytest.approx(100.0)
    assert posizione.attendibile
    assert posizione.osservazioni_confronto == 25  # 5 settimane x 5 anni
    assert "alto" in posizione.lettura()


def test_prezzo_in_calo_puo_restare_alto_per_la_stagione():
    """Il caso che i delta settimanali nascondono."""
    dati = _serie_stagionale()
    dati.append(osservazione("2026-W25", 20.0, 100.0))
    dati.append(osservazione("2026-W26", 14.0, 100.0))
    variazioni = metrics.variazioni_recenti(dati, "2026-W26")
    posizione = metrics.posizione_stagionale(dati, "2026-W26")
    assert variazioni["settimana"] < 0  # sta scendendo
    assert posizione.percentile == pytest.approx(100.0)  # resta sopra la norma


def test_storico_corto_non_e_attendibile():
    dati = [osservazione("2025-W26", 10.0), osservazione("2026-W26", 12.0)]
    posizione = metrics.posizione_stagionale(dati, "2026-W26")
    assert not posizione.attendibile
    assert "insufficiente" in posizione.lettura()


def test_banda_esclude_anno_corrente():
    dati = _serie_stagionale() + [osservazione("2026-W26", 99.0, 100.0)]
    banda = metrics.banda_stagionale(dati, anno_escluso=2026)
    assert banda[26]["massimo"] == pytest.approx(10.0)
    assert banda[26]["osservazioni"] == 5


# --------------------------------------------------------------------------
# Cambio
# --------------------------------------------------------------------------


def test_conversione_usa_il_cambio_della_settimana():
    dati = [osservazione("2026-W01", 113.0, 100.0), osservazione("2026-W02", 114.0, 100.0)]
    cambi = {"2026-W01": 11.3, "2026-W02": 11.4}
    convertite = metrics.converti(dati, cambi)
    assert convertite[0]["valore"] == pytest.approx(10.0)
    assert convertite[1]["valore"] == pytest.approx(10.0)  # in euro è fermo


def test_cambio_mancante_non_inventa_il_valore():
    convertite = metrics.converti([osservazione("2026-W01", 113.0)], {})
    assert convertite[0]["valore"] is None
    assert convertite[0]["nota"] == "cambio non disponibile"


# --------------------------------------------------------------------------
# Costo a destino
# --------------------------------------------------------------------------


def test_glassatura_e_resa_si_sommano_sul_costo_utilizzabile():
    esito = metrics.costo_a_destino(
        prezzo_origine_kg=7.00,
        trasporto_kg=0.50,
        glassatura_percentuale=10,
        resa_percentuale=75,
    )
    assert esito.prezzo_reso == pytest.approx(7.50)
    # 7,50 / 0,9 = 8,3333 al netto dell'acqua; / 0,75 = 11,1111 per kg utile
    assert esito.costo_materia_utilizzabile == pytest.approx(11.1111, abs=1e-3)


def test_resa_al_cento_per_cento_non_cambia_nulla():
    esito = metrics.costo_a_destino(10.0, resa_percentuale=100)
    assert esito.costo_materia_utilizzabile == pytest.approx(10.0)


def test_parametri_impossibili_rifiutati():
    with pytest.raises(ValueError):
        metrics.costo_a_destino(10.0, resa_percentuale=0)
    with pytest.raises(ValueError):
        metrics.costo_a_destino(10.0, glassatura_percentuale=100)


# --------------------------------------------------------------------------
# Archivio e revisioni
# --------------------------------------------------------------------------


@pytest.fixture()
def archivio(tmp_path):
    a = Archivio(tmp_path / "prova.sqlite")
    a.registra_serie(
        id="prova",
        prodotto="Prova",
        mercato="Prova",
        fase="Prova",
        indicatore="Prezzo",
        unita="EUR/kg",
        frequenza="settimanale",
        fonte="Prova",
    )
    yield a
    a.chiudi()


def test_secondo_carico_non_duplica(archivio):
    dati = [Osservazione("2026-W01", 10.0, 100.0)]
    primo = archivio.carica("prova", dati)
    secondo = archivio.carica("prova", dati)
    assert primo.nuove == 1
    assert secondo.nuove == 0 and secondo.invariate == 1
    assert len(archivio.osservazioni("prova")) == 1


def test_revisione_registrata_e_riavvolgibile(archivio):
    archivio.carica("prova", [Osservazione("2026-W01", 10.0, 100.0)])
    momento = archivio.osservazioni("prova")[0]["ultimo_aggiornamento"]

    archivio.carica("prova", [Osservazione("2026-W01", 10.6, 100.0)])
    assert archivio.osservazioni("prova")[0]["valore"] == pytest.approx(10.6)
    assert len(archivio.revisioni("prova")) == 1

    passato = archivio.osservazioni("prova", al_momento=momento)
    assert passato[0]["valore"] == pytest.approx(10.0)  # cosa era pubblicato allora


def test_arrotondamenti_sotto_tolleranza_non_sono_revisioni(archivio):
    archivio.carica("prova", [Osservazione("2026-W01", 10.0, 100.0)])
    archivio.carica("prova", [Osservazione("2026-W01", 10.0001, 100.0)], tolleranza_revisione=0.001)
    assert archivio.revisioni("prova") == []


def test_valori_negativi_scartati(archivio):
    esito = archivio.carica("prova", [Osservazione("2026-W01", -5.0, 100.0)])
    assert esito.nuove == 0 and esito.scartate


def test_serie_non_registrata_rifiutata(archivio):
    with pytest.raises(KeyError):
        archivio.carica("inesistente", [Osservazione("2026-W01", 1.0)])


# --------------------------------------------------------------------------
# Quotazioni giornaliere
# --------------------------------------------------------------------------


def test_giornaliero_diventa_media_settimanale():
    giorni = [
        osservazione("2026-09-07", 7.0),   # lunedi W37
        osservazione("2026-09-09", 8.0),
        osservazione("2026-09-11", 9.0),
        osservazione("2026-09-14", 5.0),   # lunedi W38, giorno solo
    ]
    settimane = metrics.da_giornaliero_a_settimanale(giorni)
    assert [s["periodo"] for s in settimane] == ["2026-W37"]  # W38 scartata: un giorno solo
    assert settimane[0]["valore"] == pytest.approx(8.0)
    assert settimane[0]["quantita"] == 3



def test_lettura_al_netto_del_livello_toglie_l_inflazione():
    """Prezzi in salita costante: nominalmente ogni settimana è 'alta', al netto no."""
    dati = []
    for anno in range(2020, 2027):
        for settimana in range(1, 53):
            livello = 10.0 * (1.08 ** (anno - 2020))      # +8% l'anno, nessuna stagionalità
            dati.append(osservazione(isoweek.chiave(anno, settimana), livello, 100.0))
    nominale = metrics.posizione_stagionale(dati, "2026-W30")
    netto = metrics.posizione_stagionale_al_netto_del_livello(dati, "2026-W30")
    assert nominale.percentile == pytest.approx(100.0)
    assert 20 < netto.percentile < 80
