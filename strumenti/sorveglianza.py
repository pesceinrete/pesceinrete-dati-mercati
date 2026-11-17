"""Quando il ciclo fallisce, qualcuno deve capire perché. Qui lo fa un modello.

Il ciclo automatico è deterministico e deve restarlo: un modello non va
messo a girare la manovella. Va messo dove serve capire qualcosa di
nuovo: una fonte che ha cambiato le etichette, una pagina riorganizzata,
un codice doganale rinominato.

Questo script gira solo dopo un fallimento. Raccoglie il registro
dell'esecuzione fallita, individua il modulo coinvolto, allega il suo
sorgente e la configurazione, e chiede al modello una diagnosi in
italiano piano e, se possibile, una correzione minima. Poi:

* se il modello propone una correzione, la applica su un ramo separato,
  esegue tutti i test, e apre una richiesta di modifica (pull request)
  con la spiegazione: la redazione la approva o la rifiuta con un clic;
* se non propone niente, o i test non passano, apre una segnalazione
  (issue) con la diagnosi e cosa fare a mano.

Non tocca mai il ramo principale. Può modificare solo i file in
`ingest/` e `config/`. Senza chiave del modello, apre comunque la
segnalazione con l'estratto del registro: degrada, non sparisce.

Variabili d'ambiente: ANTHROPIC_API_KEY (segreto del repository),
MODELLO_AI (facoltativa), GITHUB_TOKEN e GITHUB_REPOSITORY (le mette
GitHub Actions).

    python strumenti/sorveglianza.py --registro registro-fallito.txt --esecuzione 123456
    python strumenti/sorveglianza.py --registro registro-fallito.txt --prova   (senza chiamare il modello)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
FILE_MODIFICABILI = ("ingest/", "config/")
MODELLO = os.environ.get("MODELLO_AI", "claude-sonnet-4-6")

ISTRUZIONI = """Sei il manutentore di un sistema in Python che scarica dati di mercato ittici da fonti
pubbliche (Statistics Norway, Eurostat Comext, FranceAgriMer RNM, BCE) e pubblica una pagina.
Il ciclo automatico è fallito. Ti do il registro dell'esecuzione fallita, il sorgente del modulo
coinvolto e la sua configurazione.

Rispondi SOLO con un oggetto JSON, senza testo attorno, con queste chiavi:
- "diagnosi": due o tre frasi in italiano piano, per una redazione non tecnica: cosa è successo e perché.
- "causa": una di "fonte_cambiata", "fonte_non_raggiungibile", "codice_non_valido", "errore_nel_codice", "altro".
- "temporaneo": true se è probabile che si risolva da solo (es. servizio non raggiungibile), altrimenti false.
- "correzione": null oppure un oggetto {"file": "<percorso relativo>", "sostituzioni": [{"vecchio": "<testo esatto presente nel file>", "nuovo": "<testo sostitutivo>"}], "motivo": "<una frase>"}.
  Proponi una correzione solo se sei sicuro: minima, chirurgica, nei file in ingest/ o config/. Il testo "vecchio" deve
  comparire nel file esattamente una volta. Mai proporre correzioni a tests/ o core/.
- "cosa_fare": istruzioni in italiano per una persona non tecnica, in due o tre punti, nel caso la correzione non basti.

Non inventare dettagli sulle fonti che non vedi nel registro. Se il registro mostra un errore di rete o un
timeout, la causa è "fonte_non_raggiungibile" e la correzione è null."""


# --------------------------------------------------------------------------
# Lettura del registro
# --------------------------------------------------------------------------


def modulo_coinvolto(registro: str) -> list[str]:
    """I file del progetto citati nel registro, dal più al meno citato."""
    conteggio = {}
    for m in re.finditer(r"((?:ingest|strumenti|core|config)/[\w\-]+\.(?:py|json))", registro):
        conteggio[m.group(1)] = conteggio.get(m.group(1), 0) + 1
    ordinati = sorted(conteggio, key=lambda f: -conteggio[f])
    if not ordinati:
        # indizi dalle fonti citate
        for parola, file in (("SSB", "ingest/ssb_laks.py"), ("Comext", "ingest/eurostat_comext.py"),
                             ("RNM", "ingest/rnm_rungis.py"), ("BCE", "ingest/bce_cambi.py")):
            if parola.lower() in registro.lower():
                ordinati.append(file)
    return ordinati[:3]


def estratto(registro: str, righe: int = 120) -> str:
    """Le ultime righe utili, senza il rumore dei timestamp di GitHub."""
    pulite = [re.sub(r"^\S+T\S+Z\s+", "", r) for r in registro.splitlines() if r.strip()]
    return "\n".join(pulite[-righe:])


def contesto(registro: str) -> dict:
    file = modulo_coinvolto(registro)
    sorgenti = {}
    for f in file:
        percorso = RADICE / f
        if percorso.exists() and percorso.stat().st_size < 60_000:
            sorgenti[f] = percorso.read_text(encoding="utf-8")
    # la configurazione collegata al modulo
    for f in list(sorgenti):
        for conf in ("config/rnm.json", "config/prodotti.py", "config/bmti.json"):
            if conf.split("/")[1].split(".")[0] in f and (RADICE / conf).exists():
                sorgenti[conf] = (RADICE / conf).read_text(encoding="utf-8")
    return {"file": file, "sorgenti": sorgenti, "registro": estratto(registro)}


# --------------------------------------------------------------------------
# Il modello
# --------------------------------------------------------------------------


def chiedi_al_modello(ctx: dict) -> dict | None:
    chiave = os.environ.get("ANTHROPIC_API_KEY")
    if not chiave:
        return None
    contenuto = "REGISTRO DELL'ESECUZIONE FALLITA:\n" + ctx["registro"] + "\n\n"
    for f, testo in ctx["sorgenti"].items():
        contenuto += f"=== FILE {f} ===\n{testo}\n\n"
    corpo = {
        "model": MODELLO,
        "max_tokens": 2000,
        "system": ISTRUZIONI,
        "messages": [{"role": "user", "content": contenuto}],
    }
    richiesta = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": chiave, "anthropic-version": "2023-06-01"},
    )
    with urllib.request.urlopen(richiesta, timeout=120) as risposta:
        dati = json.loads(risposta.read().decode("utf-8"))
    testo = "".join(b.get("text", "") for b in dati.get("content", []) if b.get("type") == "text")
    return interpreta(testo)


def interpreta(testo: str) -> dict | None:
    pulito = re.sub(r"^```(?:json)?|```$", "", testo.strip(), flags=re.M).strip()
    try:
        risposta = json.loads(pulito)
    except ValueError:
        inizio, fine = pulito.find("{"), pulito.rfind("}")
        if inizio < 0 or fine < 0:
            return None
        try:
            risposta = json.loads(pulito[inizio:fine + 1])
        except ValueError:
            return None
    if not isinstance(risposta, dict) or "diagnosi" not in risposta:
        return None
    return risposta


# --------------------------------------------------------------------------
# Applicazione della correzione, con tutte le cautele
# --------------------------------------------------------------------------


def correzione_ammissibile(correzione: dict | None) -> tuple[bool, str]:
    if not correzione:
        return False, "nessuna correzione proposta"
    file = correzione.get("file", "")
    if not file.startswith(FILE_MODIFICABILI):
        return False, f"file non modificabile automaticamente: {file}"
    percorso = RADICE / file
    if not percorso.exists():
        return False, f"file inesistente: {file}"
    sostituzioni = correzione.get("sostituzioni") or []
    if not sostituzioni or len(sostituzioni) > 6:
        return False, "numero di sostituzioni non ammesso"
    testo = percorso.read_text(encoding="utf-8")
    for s in sostituzioni:
        vecchio = s.get("vecchio", "")
        if not vecchio or testo.count(vecchio) != 1:
            return False, "il testo da sostituire non compare esattamente una volta"
        if len(s.get("nuovo", "")) > 4000:
            return False, "sostituzione troppo estesa"
    return True, "ok"


def applica(correzione: dict) -> None:
    percorso = RADICE / correzione["file"]
    testo = percorso.read_text(encoding="utf-8")
    for s in correzione["sostituzioni"]:
        testo = testo.replace(s["vecchio"], s["nuovo"], 1)
    percorso.write_text(testo, encoding="utf-8")


def test_passano() -> tuple[bool, str]:
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"], capture_output=True, text=True, cwd=RADICE)
    return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


# --------------------------------------------------------------------------
# GitHub: ramo, richiesta di modifica, segnalazione
# --------------------------------------------------------------------------


def gh(*argomenti: str) -> str:
    r = subprocess.run(["gh", *argomenti], capture_output=True, text=True, cwd=RADICE)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()


def git(*argomenti: str) -> str:
    r = subprocess.run(["git", *argomenti], capture_output=True, text=True, cwd=RADICE)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout.strip()


def testo_relazione(risposta: dict | None, ctx: dict, esecuzione: str, esito_correzione: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    collegamento = f"https://github.com/{repo}/actions/runs/{esecuzione}" if repo and esecuzione else ""
    righe = ["## Il ciclo di aggiornamento è fallito", ""]
    if risposta:
        righe += ["**Cosa è successo.** " + risposta.get("diagnosi", ""), ""]
        causa = {"fonte_cambiata": "la fonte ha cambiato struttura", "fonte_non_raggiungibile": "la fonte non era raggiungibile",
                 "codice_non_valido": "un codice (doganale o di tabella) non è più valido", "errore_nel_codice": "un errore nel nostro codice",
                 "altro": "altro"}.get(risposta.get("causa", "altro"), "altro")
        righe += [f"**Causa probabile:** {causa}." + (" È probabile che si risolva da solo al prossimo tentativo." if risposta.get("temporaneo") else ""), ""]
        if risposta.get("cosa_fare"):
            cf = risposta["cosa_fare"]
            righe += ["**Cosa fare**", ""] + ([f"- {p}" for p in cf] if isinstance(cf, list) else [cf]) + [""]
    else:
        righe += ["Non è stato possibile ottenere una diagnosi automatica (manca la chiave del modello o la risposta non era leggibile). "
                  "Qui sotto l'estratto del registro.", ""]
    righe += ["**Correzione automatica:** " + esito_correzione, ""]
    if ctx.get("file"):
        righe += ["**Moduli coinvolti:** " + ", ".join(f"`{f}`" for f in ctx["file"]), ""]
    if collegamento:
        righe += [f"**Esecuzione fallita:** {collegamento}", ""]
    righe += ["<details><summary>Estratto del registro</summary>", "", "```", ctx["registro"][-6000:], "```", "</details>"]
    return "\n".join(righe)


def esegui(percorso_registro: str, esecuzione: str, prova: bool, risposta_di_prova: str | None) -> int:
    registro = Path(percorso_registro).read_text(encoding="utf-8", errors="replace")
    ctx = contesto(registro)

    if risposta_di_prova:
        risposta = interpreta(Path(risposta_di_prova).read_text(encoding="utf-8"))
    elif prova:
        risposta = None
    else:
        try:
            risposta = chiedi_al_modello(ctx)
        except Exception as errore:  # noqa: BLE001
            print(f"Modello non raggiungibile: {errore}", file=sys.stderr)
            risposta = None

    correzione = (risposta or {}).get("correzione")
    ammissibile, motivo = correzione_ammissibile(correzione)
    esito = "nessuna proposta" if not correzione else ("proposta e verificata" if ammissibile else f"proposta ma scartata: {motivo}")

    if ammissibile and not prova:
        ramo = f"sorveglianza/correzione-{esecuzione or 'manuale'}"
        git("checkout", "-b", ramo)
        applica(correzione)
        ok, uscita_test = test_passano()
        if ok:
            git("config", "user.name", "Sorveglianza")
            git("config", "user.email", "redazione@pesceinrete.com")
            git("add", correzione["file"])
            git("commit", "-m", f"Correzione proposta: {correzione.get('motivo', 'vedi descrizione')}")
            git("push", "-u", "origin", ramo)
            corpo = testo_relazione(risposta, ctx, esecuzione, "proposta in questa richiesta: i test passano. Approvare per applicarla.")
            gh("pr", "create", "--title", f"[Sorveglianza] {correzione.get('motivo', 'correzione proposta')[:70]}",
               "--body", corpo, "--head", ramo)
            print("Richiesta di modifica aperta.")
            return 0
        git("checkout", "--", correzione["file"])
        git("checkout", "-")
        esito = "proposta, ma i test non passano: scartata\n\n```\n" + uscita_test + "\n```"

    if prova:
        print(testo_relazione(risposta, ctx, esecuzione, esito))
        return 0

    corpo = testo_relazione(risposta, ctx, esecuzione, esito)
    gh("issue", "create", "--title", "[Sorveglianza] Il ciclo di aggiornamento è fallito", "--body", corpo, "--label", "sorveglianza")
    print("Segnalazione aperta.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registro", required=True, help="file con il registro dell'esecuzione fallita")
    parser.add_argument("--esecuzione", default="", help="identificativo dell'esecuzione GitHub")
    parser.add_argument("--prova", action="store_true", help="non chiama il modello e non tocca GitHub: stampa la relazione")
    parser.add_argument("--risposta-di-prova", default=None, help="file JSON con una risposta del modello, per collaudo")
    a = parser.parse_args()
    raise SystemExit(esegui(a.registro, a.esecuzione, a.prova, a.risposta_di_prova))
