"""Immagini di anteprima per la condivisione, una per specie e per lingua.

Quando un buyer manda il link su WhatsApp, LinkedIn o per email, l'anteprima
che compare è la prima cosa che il destinatario vede. Una card con il
prezzo della settimana e la posizione stagionale vale più di qualsiasi
titolo. Le immagini vengono rigenerate a ogni aggiornamento dei dati e
il plugin le dichiara come og:image.

Formato 1200x630, il più usato dalle piattaforme. Carattere Manrope
(licenza OFL, in risorse/font). Palette IGB.

    python strumenti/genera_anteprime_social.py --dati web/data --uscita web/data/social
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RADICE = Path(__file__).resolve().parents[1]
FONT = RADICE / "risorse" / "font" / "Manrope.ttf"

NAVY = (0, 55, 87)         # #003757, il navy del menu IGB
GIALLO = (31, 141, 204)     # #1F8DCC, il blu del logo Pesceinrete e del quadrato IGB (nome storico della costante)
BIANCO = (255, 255, 255)
GRIGIO = (170, 196, 214)

TESTI = {
    "it": {"marchio": "DATI E MERCATI · PESCEINRETE", "settimana": "Settimana {s} · {esteso}",
           "alto": "SOPRA LA NORMA STAGIONALE", "basso": "SOTTO LA NORMA STAGIONALE",
           "norma": "NELLA NORMA STAGIONALE", "corto": "STORICO IN COSTRUZIONE",
           "sett": "sulla settimana", "anno": "sull'anno", "fonte": "Fonte: {fonte}"},
    "en": {"marchio": "MARKET DATA · PESCEINRETE", "settimana": "Week {s} · {esteso}",
           "alto": "ABOVE SEASONAL NORM", "basso": "BELOW SEASONAL NORM",
           "norma": "WITHIN SEASONAL NORM", "corto": "HISTORY BEING BUILT",
           "sett": "on the week", "anno": "on the year", "fonte": "Source: {fonte}"},
}


def carattere(dimensione: int, peso: str = "ExtraBold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), dimensione)
    try:
        f.set_variation_by_name(peso)
    except Exception:  # noqa: BLE001
        pass
    return f


def numero(valore, decimali, lingua):
    if valore is None:
        return "n.d." if lingua == "it" else "n/a"
    testo = f"{valore:,.{decimali}f}"
    return testo.replace(",", "@").replace(".", ",").replace("@", ".") if lingua == "it" else testo


def segno(valore, lingua):
    if valore is None:
        return "—"
    # Manrope non ha i triangoli: segno in chiaro
    return ("+" if valore > 0 else ("-" if valore < 0 else "")) + numero(abs(valore), 1, lingua) + "%"


def disegna(prodotto: dict, lingua: str, destinazione: Path) -> None:
    T = TESTI[lingua]
    img = Image.new("RGB", (1200, 630), NAVY)
    d = ImageDraw.Draw(img)

    # fascia azzurra in alto, come la fascia alta di IGB
    d.rectangle([0, 0, 1200, 10], fill=GIALLO)

    # marchio in alto a sinistra: PESCEINRETE con la "IN" azzurra, come nel logo, poi la sezione
    f_m = carattere(22, "ExtraBold")
    x = 64
    for parte, colore in (("PESCE", BIANCO), ("IN", GIALLO), ("RETE", BIANCO)):
        d.text((x, 52), parte, font=f_m, fill=colore)
        x += d.textlength(parte, font=f_m)
    d.text((x + 16, 52), ("· DATI E MERCATI" if lingua == "it" else "· MARKET DATA"), font=f_m, fill=GRIGIO)
    settimana = T["settimana"].format(s=prodotto["ultimo_periodo"][6:], esteso=prodotto["ultimo_periodo_esteso"])
    f_sett = carattere(22, "SemiBold")
    larghezza = d.textlength(settimana, font=f_sett)
    d.text((1200 - 64 - larghezza, 52), settimana, font=f_sett, fill=GRIGIO)

    # specie
    nome = prodotto["nome"]
    f_nome = carattere(64, "ExtraBold")
    if d.textlength(nome, font=f_nome) > 1000:
        f_nome = carattere(52, "ExtraBold")
    d.text((64, 140), nome, font=f_nome, fill=BIANCO)
    # sottotitolo: tagliato a una parola intera, mai a metà
    f_sotto = carattere(22, "Medium")
    sotto = prodotto["serie"]["indicatore"] + " · " + prodotto["serie"]["mercato"]
    while d.textlength(sotto, font=f_sotto) > 1072 and " " in sotto:
        sotto = sotto.rsplit(" ", 1)[0].rstrip(" ·,") + "…"
    d.text((64, 222), sotto, font=f_sotto, fill=GRIGIO)

    # prezzo
    prezzo = numero(prodotto["prezzo_eur_kg"], 2, lingua)
    f_prezzo = carattere(150, "ExtraBold")
    d.text((58, 270), prezzo, font=f_prezzo, fill=BIANCO)
    lp = d.textlength(prezzo, font=f_prezzo)
    d.text((64 + lp + 18, 372), "€/kg", font=carattere(40, "Bold"), fill=GRIGIO)

    # variazioni
    v = prodotto["variazioni"]
    y = 470
    f_val = carattere(34, "ExtraBold")
    f_lab = carattere(20, "Medium")
    x = 64
    for valore, etichetta in ((v.get("settimana"), T["sett"]), (v.get("anno"), T["anno"])):
        testo = segno(valore, lingua)
        d.text((x, y), testo, font=f_val, fill=BIANCO)
        lt = d.textlength(testo, font=f_val)
        d.text((x + lt + 12, y + 12), etichetta, font=f_lab, fill=GRIGIO)
        x += lt + d.textlength(etichetta, font=f_lab) + 60

    # posizione stagionale: pastiglia gialla
    p = prodotto["stagionale"].get("percentile")
    att = prodotto["stagionale"].get("attendibile")
    chiave = "corto" if (not att or p is None) else ("alto" if p >= 80 else ("basso" if p <= 20 else "norma"))
    etichetta = T[chiave]
    f_pill = carattere(20, "ExtraBold")
    lw = d.textlength(etichetta, font=f_pill)
    x0, y0 = 64, 540
    d.rounded_rectangle([x0, y0, x0 + lw + 36, y0 + 44], radius=8, fill=GIALLO)
    d.text((x0 + 18, y0 + 10), etichetta, font=f_pill, fill=BIANCO)

    # fonte
    fonte = T["fonte"].format(fonte=prodotto["serie"]["fonte"])
    f_fonte = carattere(18, "Medium")
    lf = d.textlength(fonte, font=f_fonte)
    d.text((1200 - 64 - lf, 556), fonte[:80], font=f_fonte, fill=GRIGIO)

    destinazione.parent.mkdir(parents=True, exist_ok=True)
    img.save(destinazione, "PNG", optimize=True)


def esegui(cartella_dati: str, uscita: str) -> int:
    dati = Path(cartella_dati)
    cartella_uscita = Path(uscita)
    quante = 0
    for lingua, suffisso in (("it", ""), ("en", ".en")):
        for f in sorted((dati / "prodotti").glob(f"*{suffisso}.json")):
            if not suffisso and ".en." in f.name:
                continue
            prodotto = json.loads(f.read_text(encoding="utf-8"))
            disegna(prodotto, lingua, cartella_uscita / f"{prodotto['id']}{suffisso}.png")
            quante += 1
    print(f"{quante} anteprime scritte in {cartella_uscita}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dati", default=str(RADICE / "web/data"))
    parser.add_argument("--uscita", default=str(RADICE / "web/data/social"))
    a = parser.parse_args()
    raise SystemExit(esegui(a.dati, a.uscita))
