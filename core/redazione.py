"""Il paragrafo di apertura, scritto come lo scriverebbe la redazione.

Una frase-modello che elenca tre percentuali una dopo l'altra è la cosa
che più fa sembrare una pagina scritta da una macchina. Qui il testo
viene composto frase per frase in base a quello che è successo: un prezzo
fermo si dice fermo, un rialzo piccolo si dice piccolo, e la stagione
entra solo se ha qualcosa da dire. Le formulazioni cambiano leggermente
di settimana in settimana, senza mai inventare cause.
"""

from __future__ import annotations

from . import isoweek
from .testi import MESI

SOGGETTO = {
    "it": {
        "ssb": "{nome} all'esportazione dalla Norvegia",
        "eumofa": "{nome} all'importazione in Italia",
    },
    "en": {
        "ssb": "{nome} exported from Norway",
        "eumofa": "{nome} imported into Italy",
    },
}

ARTICOLI_IT = {
    "salmone": "Il salmone", "orata": "L'orata", "spigola": "La spigola", "polpo": "Il polpo",
    "gambero": "Il gambero", "calamaro": "Il calamaro", "seppia": "La seppia", "astice": "L'astice",
    "pesce_spada": "Il pesce spada",
}
PLURALI_IT: set[str] = set()

NOMI_EN = {
    "salmone": "Salmon", "orata": "Sea bream", "spigola": "Sea bass", "polpo": "Octopus",
    "gambero": "Shrimp", "calamaro": "Squid", "seppia": "Cuttlefish", "astice": "Lobster",
    "pesce_spada": "Swordfish",
}
PLURALI_EN: set[str] = set()


def _del(valore: float) -> str:
    """'del' o 'dell'' davanti a un numero, secondo come si pronuncia.

    Uno, otto, undici e gli ottanta cominciano per vocale: "dell'8%",
    "dell'1,8%", "dell'84%". Tutti gli altri prendono "del".
    """
    intero = int(abs(valore))
    if intero == 0:
        return "dello "   # "dello 0,6%"
    testa = intero
    while testa >= 1000:
        testa //= 1000   # "mille", "un milione": consonante o "un"
    if testa >= 100:
        return "del "
    vocale = testa in (1, 8, 11) or 80 <= testa <= 89
    return "dell'" if vocale else "del "


NUMERI_IT = {1: "un", 2: "due", 3: "tre", 4: "quattro", 5: "cinque"}
NUMERI_EN = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def anni_di_confronto(quanti: int, lingua: str = "it", forma: str = "di") -> str:
    """'degli ultimi tre anni' / 'negli ultimi tre anni' / 'of the last three years'.

    Il confronto stagionale usa gli anni che ci sono, fino a cinque: le
    serie doganali partono dal 2023 e dichiarare cinque anni sarebbe falso.
    """
    quanti = max(1, min(int(quanti or 5), 5))
    if lingua == "it":
        return f"{'negli' if forma == 'in' else 'degli'} ultimi {NUMERI_IT[quanti]} anni"
    return f"{'in' if forma == 'in' else 'of'} the last {NUMERI_EN[quanti]} years"


def _da_paese(nome: str) -> str:
    """'dalla Norvegia', 'dal Marocco', 'dall'Ecuador', 'dai Paesi Bassi'."""
    if nome.startswith("tutte"):
        return "da " + nome
    if nome in ("Paesi Bassi",):
        return "dai " + nome
    if nome[0] in "AEIOU":
        return "dall'" + nome
    femminili = ("Norvegia", "Grecia", "Turchia", "Croazia", "Spagna", "Mauritania", "Argentina",
                 "India", "Islanda", "Danimarca", "Francia", "Thailandia", "Tunisia", "Albania", "Svezia", "Polonia")
    if nome in ("Stati Uniti",):
        return "dagli " + nome
    return ("dalla " if nome in femminili else "dal ") + nome


def _numero(valore: float, decimali: int, lingua: str) -> str:
    from decimal import ROUND_HALF_UP, Decimal
    arrotondato = Decimal(repr(float(abs(valore)))).quantize(Decimal(1).scaleb(-decimali), rounding=ROUND_HALF_UP)
    testo = f"{arrotondato:,.{decimali}f}"
    return testo.replace(",", "@").replace(".", ",").replace("@", ".") if lingua == "it" else testo


def _momento_del_mese(periodo: str, lingua: str) -> str:
    """'fine settembre', 'metà ottobre', 'inizio novembre'."""
    giorno = isoweek.domenica(periodo)
    nome = MESI[lingua][giorno.month - 1]
    if lingua == "it":
        fase = "inizio" if giorno.day <= 10 else ("metà" if giorno.day <= 20 else "fine")
        return f"{fase} {nome}"
    fase = "early" if giorno.day <= 10 else ("mid" if giorno.day <= 20 else "late")
    return f"{fase}-{nome}" if fase == "mid" else f"{fase} {nome}"


def lede(
    prodotto_id: str,
    nome: str,
    fonte: str,
    periodo: str,
    prezzo_eur: float,
    variazioni: dict,
    stagionale: dict,
    volumi: float | None,
    volumi_percentile: float | None,
    flussi: dict | None,
    lingua: str = "it",
    provenienza: str | None = None,
    media_settimane: int | None = None,
) -> str:
    frasi = []
    settimana = int(periodo[6:])
    pari = settimana % 2 == 0
    v_sett = variazioni.get("settimana")
    v_mese = variazioni.get("quattro_settimane")
    v_anno = variazioni.get("anno")
    anno = int(periodo[:4])

    if lingua == "it":
        plurale = prodotto_id in PLURALI_IT
        soggetto = ARTICOLI_IT.get(prodotto_id, nome)
        dove = {
            "ssb": "all'esportazione dalla Norvegia",
            "eumofa": "importato in Italia" if prodotto_id not in ("orata", "spigola", "seppia") else "importata in Italia",
        }.get(fonte, "")
        if fonte == "eumofa" and provenienza and not provenienza.startswith("tutte"):
            dove += " " + _da_paese(provenienza)
        verbo = "chiudono" if plurale else "chiude"
        media = f" di media sulle ultime {media_settimane} settimane" if media_settimane else ""
        frasi.append(
            f"{soggetto} {dove} {verbo} la settimana {settimana} a {_numero(prezzo_eur, 2, lingua)} €/kg{media}"
            + _movimento_it(v_sett, v_mese, pari) + "."
        )
        if v_anno is not None and abs(v_anno) >= 1:
            sopra = v_anno > 0
            frasi.append(
                (f"Rispetto allo stesso periodo del {anno - 1} il prezzo è "
                 f"{'più alto' if sopra else 'più basso'} {_del(v_anno)}{_numero(v_anno, 1, lingua)}%.")
                if pari else
                (f"Sul {anno - 1} il confronto resta {'in positivo' if sopra else 'in negativo'}: "
                 f"{'+' if sopra else '−'}{_numero(v_anno, 1, lingua)}%.")
            )
        frasi.append(_stagione_it(stagionale, periodo))
        if volumi and volumi_percentile is not None:
            if volumi_percentile >= 85:
                frasi.append(f"I volumi, {_numero(volumi, 0, lingua)} tonnellate, sono tra i più alti del periodo.")
            elif volumi_percentile <= 15:
                frasi.append(f"I volumi, {_numero(volumi, 0, lingua)} tonnellate, sono tra i più bassi del periodo.")
        if flussi and flussi.get("dodici_mesi", {}).get("tonnellate"):
            d = flussi["dodici_mesi"]
            principale = flussi.get("principale")
            intervallo = ""
            if flussi.get("primo_mese_esteso") and flussi.get("ultimo_mese_esteso"):
                a = "ad" if flussi['ultimo_mese_esteso'][0] in "aeiou" else "a"
                intervallo = f" disponibili, da {flussi['primo_mese_esteso']} {a} {flussi['ultimo_mese_esteso']},"
            testo = (f"Negli ultimi dodici mesi{intervallo} l'Italia ne ha importato "
                     f"{_numero(d['tonnellate'], 0, lingua)} tonnellate")
            if principale:
                testo += f", per il {_numero(principale['quota'], 0, lingua)}% {_da_paese(principale['paese'])}"
            if d.get("delta_tonnellate") is not None and abs(d["delta_tonnellate"]) >= 3:
                testo += (f", {'in aumento' if d['delta_tonnellate'] > 0 else 'in calo'} "
                          f"{_del(d['delta_tonnellate'])}{_numero(d['delta_tonnellate'], 0, lingua)}% sui dodici mesi precedenti")
            frasi.append(testo + ".")
        return " ".join(f for f in frasi if f)

    # --- inglese
    plurale = prodotto_id in PLURALI_EN
    soggetto = NOMI_EN.get(prodotto_id, nome)
    dove = {
        "ssb": "exported from Norway",
        "eumofa": "imported into Italy",
    }.get(fonte, "")
    if fonte == "eumofa" and provenienza and not provenienza.startswith("all "):
        dove += " from " + provenienza
    verbo = "close" if plurale else "closes"
    media = f" on a {media_settimane}-week average" if media_settimane else ""
    frasi.append(
        f"{soggetto} {dove} {verbo} week {settimana} at €{_numero(prezzo_eur, 2, lingua)}/kg{media}"
        + _movimento_en(v_sett, v_mese, pari) + "."
    )
    if v_anno is not None and abs(v_anno) >= 1:
        sopra = v_anno > 0
        frasi.append(
            f"Against the same period of {anno - 1} the price is {_numero(v_anno, 1, lingua)}% "
            f"{'higher' if sopra else 'lower'}."
        )
    frasi.append(_stagione_en(stagionale, periodo))
    if volumi and volumi_percentile is not None:
        if volumi_percentile >= 85:
            frasi.append(f"Volumes, {_numero(volumi, 0, lingua)} tonnes, are among the highest for the period.")
        elif volumi_percentile <= 15:
            frasi.append(f"Volumes, {_numero(volumi, 0, lingua)} tonnes, are among the lowest for the period.")
    if flussi and flussi.get("dodici_mesi", {}).get("tonnellate"):
        d = flussi["dodici_mesi"]
        principale = flussi.get("principale")
        intervallo = ""
        if flussi.get("primo_mese_esteso") and flussi.get("ultimo_mese_esteso"):
            intervallo = f" available, {flussi['primo_mese_esteso']} to {flussi['ultimo_mese_esteso']},"
        testo = f"Over the last twelve months{intervallo} Italy imported {_numero(d['tonnellate'], 0, lingua)} tonnes"
        if principale:
            testo += f", {_numero(principale['quota'], 0, lingua)}% of it from {principale['paese']}"
        if d.get("delta_tonnellate") is not None and abs(d["delta_tonnellate"]) >= 3:
            testo += (f", {'up' if d['delta_tonnellate'] > 0 else 'down'} "
                      f"{_numero(d['delta_tonnellate'], 0, lingua)}% on the previous twelve")
        frasi.append(testo + ".")
    return " ".join(f for f in frasi if f)


def _movimento_it(v_sett, v_mese, pari: bool) -> str:
    if v_sett is None:
        return ""
    if abs(v_sett) < 0.5:
        base = ", praticamente fermo sulla settimana precedente" if pari else ", invariato rispetto a sette giorni fa"
    else:
        aggettivo = "" if abs(v_sett) >= 2 else ("lieve " if pari else "leggero ")
        verso = "rialzo" if v_sett > 0 else "calo"
        base = f", in {aggettivo}{verso} {_del(v_sett)}{_numero(v_sett, 1, 'it')}% sulla settimana"
    if v_mese is not None and abs(v_mese) >= 1 and (v_sett is None or (v_mese > 0) == (v_sett > 0) or abs(v_sett) < 0.5):
        base += f" e {_del(v_mese)}{_numero(v_mese, 1, 'it')}% sul mese" if abs(v_sett) >= 0.5 else (
            f"; sul mese il {'rialzo' if v_mese > 0 else 'calo'} è {_del(v_mese)}{_numero(v_mese, 1, 'it')}%")
    elif v_mese is not None and abs(v_mese) >= 1:
        base += f", ma {'sopra' if v_mese > 0 else 'sotto'} {_del(v_mese)}{_numero(v_mese, 1, 'it')}% il livello di un mese fa"
    return base


def _movimento_en(v_sett, v_mese, pari: bool) -> str:
    if v_sett is None:
        return ""
    if abs(v_sett) < 0.5:
        base = ", virtually unchanged on the week"
    else:
        aggettivo = "" if abs(v_sett) >= 2 else "slightly "
        verso = "up" if v_sett > 0 else "down"
        base = f", {aggettivo}{verso} {_numero(v_sett, 1, 'en')}% on the week"
    if v_mese is not None and abs(v_mese) >= 1 and (abs(v_sett) < 0.5 or (v_mese > 0) == (v_sett > 0)):
        base += f" and {_numero(v_mese, 1, 'en')}% on the month" if abs(v_sett) >= 0.5 else (
            f"; on the month it is {'up' if v_mese > 0 else 'down'} {_numero(v_mese, 1, 'en')}%")
    elif v_mese is not None and abs(v_mese) >= 1:
        base += f", though {'above' if v_mese > 0 else 'below'} a month ago by {_numero(v_mese, 1, 'en')}%"
    return base


def _stagione_it(stagionale: dict, periodo: str) -> str:
    p = stagionale.get("percentile")
    if not stagionale.get("attendibile") or p is None:
        return ""
    momento = _momento_del_mese(periodo, "it")
    anni = anni_di_confronto(len(stagionale.get("anni") or []), "it")
    if p >= 99.5:
        return f"Per {momento} è il livello più alto {anni}."
    if p <= 0.5:
        return f"Per {momento} è il livello più basso {anni}."
    if p >= 80:
        return (f"Per {momento} è un prezzo alto: più caro {_del(p)}{_numero(p, 0, 'it')}% delle "
                f"settimane comparabili {anni}.")
    if p <= 20:
        return (f"Per {momento} è un prezzo basso: più economico {_del(100 - p)}{_numero(100 - p, 0, 'it')}% "
                f"delle settimane comparabili {anni}.")
    return f"Per {momento} è un livello nella norma."


def _stagione_en(stagionale: dict, periodo: str) -> str:
    p = stagionale.get("percentile")
    if not stagionale.get("attendibile") or p is None:
        return ""
    momento = _momento_del_mese(periodo, "en")
    anni = anni_di_confronto(len(stagionale.get("anni") or []), "en")
    if p >= 99.5:
        return f"For {momento} it is the highest level {anni}."
    if p <= 0.5:
        return f"For {momento} it is the lowest level {anni}."
    if p >= 80:
        return (f"For {momento} it is a high price: dearer than {_numero(p, 0, 'en')}% of the "
                f"comparable weeks {anni}.")
    if p <= 20:
        return (f"For {momento} it is a low price: cheaper than {_numero(100 - p, 0, 'en')}% of the "
                f"comparable weeks {anni}.")
    return f"For {momento} it is a normal level."
