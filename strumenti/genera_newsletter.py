"""La newsletter del giovedì, pronta per Brevo, Mailchimp o MailerLite.

I testi esistono già: il lede di ogni specie e le voci del bollettino.
Qui diventano una mail in HTML con stile in linea (è l'unico modo in cui
i client di posta la mostrano uguale), navy e giallo, tabella di tutte le
specie e un blocco per le specie con qualcosa da dire. Si incolla nel
modello del servizio di invio come contenuto HTML.

Esce in `web/newsletter/<settimana>.html` e `.en.html`, con una versione
in testo semplice accanto, perché i servizi la chiedono.

    python strumenti/genera_newsletter.py --dati web/data --uscita web/newsletter --sito https://www.pesceinrete.com
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]

T = {
    "it": {"oggetto": "Dati e mercati · settimana {s}: {primo}", "intro": "I prezzi di riferimento delle specie ittiche, ogni giovedì.",
           "tabella": "Tutte le specie, questa settimana", "col": ("Specie", "€/kg", "Settimana", "Anno", "Stagione"),
           "attenzione": "Che cosa merita attenzione", "apri": "Apri la scheda", "piede": "Ricevi questa mail perché ti sei iscritto a Dati e mercati di Pesceinrete. Fonti e metodo sono dichiarati in ogni scheda.",
           "stagione": {"alto": "sopra la norma", "basso": "sotto la norma", "norma": "nella norma", "corto": "storico corto"},
           "radice": "dati-mercati"},
    "en": {"oggetto": "Market data · week {s}: {primo}", "intro": "Reference prices for seafood species, every Thursday.",
           "tabella": "All species, this week", "col": ("Species", "€/kg", "Week", "Year", "Season"),
           "attenzione": "What deserves attention", "apri": "Open the page", "piede": "You receive this email because you subscribed to Pesceinrete Market data. Sources and method are stated on every page.",
           "stagione": {"alto": "above normal", "basso": "below normal", "norma": "normal", "corto": "short history"},
           "radice": "market-data"},
}


def numero(v, d, lingua):
    if v is None:
        return "n.d." if lingua == "it" else "n/a"
    s = f"{v:,.{d}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".") if lingua == "it" else s


def segno(v, lingua):
    if v is None:
        return "—"
    return ("+" if v > 0 else ("−" if v < 0 else "")) + numero(abs(v), 1, lingua) + "%"


def componi(indice: dict, prodotti: list[dict], lingua: str, sito: str) -> tuple[str, str, str]:
    t = T[lingua]
    settimana = prodotti[0]["ultimo_periodo"]
    primo = prodotti[0]
    oggetto = t["oggetto"].format(s=settimana[6:], primo=f"{primo['nome']} {numero(primo['prezzo_eur_kg'], 2, lingua)} €/kg ({segno(primo['variazioni'].get('settimana'), lingua)})")

    righe = ""
    for p in prodotti:
        pc = p["stagionale"].get("percentile"); att = p["stagionale"].get("attendibile")
        chiave = "corto" if (not att or pc is None) else ("alto" if pc >= 80 else ("basso" if pc <= 20 else "norma"))
        url = f"{sito}/{t['radice']}/{p['id']}/"
        righe += (
            f'<tr><td style="padding:10px 8px;border-bottom:1px solid #e3e8ef;font-weight:700;color:#003757">'
            f'<a href="{url}" style="color:#003757;text-decoration:none">{html.escape(p["nome"])}</a></td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #e3e8ef;text-align:right">{numero(p["prezzo_eur_kg"], 2, lingua)}</td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #e3e8ef;text-align:right">{segno(p["variazioni"].get("settimana"), lingua)}</td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #e3e8ef;text-align:right">{segno(p["variazioni"].get("anno"), lingua)}</td>'
            f'<td style="padding:10px 8px;border-bottom:1px solid #e3e8ef;text-align:right;font-size:12px;text-transform:uppercase;letter-spacing:.04em">{t["stagione"][chiave]}</td></tr>'
        )

    blocchi, testo_semplice = "", []
    for p in prodotti:
        voci = p.get("bollettino") or []
        if not voci and not p.get("lede"):
            continue
        url = f"{sito}/{t['radice']}/{p['id']}/"
        blocchi += (
            f'<h3 style="margin:28px 0 6px;font-size:18px;color:#003757">{html.escape(p["nome"])} · {numero(p["prezzo_eur_kg"], 2, lingua)} €/kg</h3>'
            f'<p style="margin:0 0 8px;font-size:15px;line-height:1.55;color:#1f2933">{html.escape(p.get("lede") or "")}</p>'
        )
        testo_semplice.append(f"{p['nome']} · {numero(p['prezzo_eur_kg'], 2, lingua)} €/kg\n{p.get('lede') or ''}")
        for v in voci:
            blocchi += (f'<p style="margin:0 0 8px;font-size:14px;line-height:1.5;color:#44536a">'
                        f'<b style="color:#003757">{html.escape(v["titolo"])}.</b> {html.escape(v["testo"])}</p>')
            testo_semplice.append(f"- {v['titolo']}. {v['testo']}")
        blocchi += (f'<p style="margin:0 0 8px"><a href="{url}" style="display:inline-block;background:#1f8dcc;color:#003757;'
                    f'font-weight:800;text-decoration:none;padding:9px 16px;border-radius:8px;font-size:13px;'
                    f'">{t["apri"]}</a></p>')
        testo_semplice.append(url + "\n")

    corpo = f"""<!doctype html><html lang="{lingua}"><head><meta charset="utf-8"><title>{html.escape(oggetto)}</title></head>
<body style="margin:0;padding:0;background:#e6f6ff;font-family:Manrope,Helvetica,Arial,sans-serif;color:#1f2933">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#e6f6ff"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%">
  <tr><td style="background:#003757;border-top:6px solid #1f8dcc;padding:22px 28px;color:#fff">
    <div style="font-size:12px;font-weight:800;letter-spacing:.14em;color:#8fd0ff">{"DATI E MERCATI" if lingua == "it" else "MARKET DATA"}</div>
    <div style="font-size:24px;font-weight:800;margin-top:8px">{"Settimana" if lingua == "it" else "Week"} {settimana[6:]} · {html.escape(primo["ultimo_periodo_esteso"])}</div>
    <div style="font-size:14px;color:rgba(255,255,255,.85);margin-top:6px">{t["intro"]}</div>
  </td></tr>
  <tr><td style="background:#fff;padding:24px 28px;border:1px solid #e3e8ef;border-top:0">
    <h2 style="margin:0 0 10px;font-size:18px;color:#003757">{t["tabella"]}</h2>
    <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px">
      <thead><tr>{''.join(f'<th style="text-align:{"left" if i == 0 else "right"};padding:6px 8px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#6b7a90;border-bottom:2px solid #e3e8ef">{c}</th>' for i, c in enumerate(t["col"]))}</tr></thead>
      <tbody>{righe}</tbody>
    </table>
    <h2 style="margin:28px 0 0;font-size:18px;color:#003757">{t["attenzione"]}</h2>
    {blocchi}
  </td></tr>
  <tr><td style="padding:18px 28px;font-size:12px;color:#6b7a90;line-height:1.5">{t["piede"]}</td></tr>
</table></td></tr></table></body></html>"""

    semplice = f"{oggetto}\n\n" + "\n\n".join(testo_semplice) + f"\n\n{t['piede']}"
    return oggetto, corpo, semplice


def esegui(cartella_dati: str, uscita: str, sito: str) -> int:
    dati = Path(cartella_dati)
    out = Path(uscita)
    out.mkdir(parents=True, exist_ok=True)
    for lingua, suffisso in (("it", ""), ("en", ".en")):
        indice = json.loads((dati / f"mercati{suffisso}.json").read_text(encoding="utf-8"))
        prodotti = []
        for voce in indice["prodotti"]:
            f = dati / "prodotti" / f"{voce['id']}{suffisso}.json"
            if f.exists():
                prodotti.append(json.loads(f.read_text(encoding="utf-8")))
        if not prodotti:
            continue
        oggetto, corpo, semplice = componi(indice, prodotti, lingua, sito.rstrip("/"))
        settimana = prodotti[0]["ultimo_periodo"]
        (out / f"{settimana}{suffisso}.html").write_text(corpo, encoding="utf-8")
        (out / f"{settimana}{suffisso}.txt").write_text(semplice, encoding="utf-8")
        (out / f"{settimana}{suffisso}.oggetto.txt").write_text(oggetto, encoding="utf-8")
        print(f"[{lingua}] {oggetto}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dati", default=str(RADICE / "web/data"))
    parser.add_argument("--uscita", default=str(RADICE / "web/newsletter"))
    parser.add_argument("--sito", default="https://www.pesceinrete.com")
    a = parser.parse_args()
    raise SystemExit(esegui(a.dati, a.uscita, a.sito))
