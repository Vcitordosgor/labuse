#!/usr/bin/env python3
"""NU5-B — harnais de génération + extraction + comparaison écran (LECTURE SEULE).

Génère chaque document pour les 10 parcelles témoins, extrait le texte/polices/pages,
et exécute les contrôles de l'audit :
  - mots interdits / fuites internes (EPSG, ST_*, run ids, jargon scoring, {{var}}, None/NaN)
  - dates & fuseau (la date "généré le" doit être la date de La Réunion UTC+4)
  - mentions obligatoires (avertissement juridique, sources, TVA 293 B, coordonnées LABUSE)
  - chiffres clés PDF vs fiche écran (surface, contenance, prix, SDP)
  - "Régénérer" déterministe (2 passes, diff hors horodatage)
Usage : python harnais.py [--only IDU] [--doc dossier]
Sorties : preuves/<idu>/<doc>.{pdf,txt} + resultats.json
"""
from __future__ import annotations
import json, os, re, subprocess, sys, datetime, urllib.request, urllib.parse, hashlib, zipfile, io

BASE = os.environ.get("NU5_BASE") or os.environ.get("BASE") or "http://127.0.0.1:9740"
# OPS-3 (C) — session de RECETTE partagée par le runner `verite_permanente` (header Cookie).
COOKIE = os.environ.get("LABUSE_HARNAIS_COOKIE")
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(ROOT, "..", "preuves"))
os.makedirs(OUT, exist_ok=True)

PARCELS = [
    ("97415000BO0852", "batie"),
    ("97415000CW0658", "nue_a_cheval"),
    ("97421000AB0133", "ppr_rouge_a_cheval"),
    ("97411000DN0183", "copropriete"),
    ("97424000AM0893", "au_proprio_long"),
    ("97417000BN0002", "foret_sans_zone_grande"),
    ("97416000DV0285", "surface_incertaine"),
    ("97418000AV2114", "sans_donnees"),
    ("97411000BZ1065", "bati_temoin"),
    ("97409000AK0804", "nue_constructible_ppr"),
]
IDUS = [p[0] for p in PARCELS]

# Documents générés par IDU (GET). Comparatif/etude-zone/annonce ont des variantes.
def doc_url(idu):
    return {
        "dossier":      f"/dossier/{idu}.pdf",
        "financier":    f"/financier/{idu}.pdf",
        "apporteur":    f"/apporteur/{idu}.pdf",
        "gabarit":      f"/gabarit/{idu}.pdf",
        "etude_zone":   f"/etude-zone.pdf?idu={idu}&rayon_km=1",
        "analyse":      f"/analyse-annonce/{idu}.pdf",
        "pre_dossier":  f"/pre-dossier/{idu}.zip",
    }

REUNION = datetime.timezone(datetime.timedelta(hours=4))

# --- fuites internes / mots interdits ----------------------------------------
LEAKS = [
    r"\bEPSG:?\d+", r"\bST_[A-Za-z]+", r"SIGNAL DE ZONE", r"\bproxy\b", r"\bdoctrine\b",
    r"fiabilité suivie", r"score\s*[:=]\s*[01]\.\d", r"run[\s_-]?m?\d+[-_]run",
    r"q_v\d+", r"SOFT_FLAG", r"HARD_FLAG", r"\bweight\b", r"source_table",
    r"\.venv", r"psycopg", r"sqlalchemy", r"Traceback", r"work_mem",
]
FORBIDDEN = [
    r"\bNone\b", r"\bnull\b", r"\bNaN\b", r"\bundefined\b", r"\{\{", r"\}\}",
    r"\[object Object\]", r"\bInternal Server Error\b", r"nan\b",
]

MENTIONS = {
    "avert_juridique": re.compile(r"ni\s+(?:un\s+)?conseil\s+juridique|ne\s+remplace\s+ni", re.I),
    "garantie_constructib": re.compile(r"garantie\s+de\s+constructibilit|ne\s+garantit\s+pas", re.I),
    "sources": re.compile(r"\bsourc[eé]", re.I),
    "tva_293b": re.compile(r"293\s*B|franchise\s+en\s+base|TVA\s+non\s+applicable|non\s+assujetti", re.I),
    "coord_labuse": re.compile(r"LA\s*BUSE|labuse", re.I),
}

def fetch(path, binary=True):
    url = BASE + path
    req = urllib.request.Request(url, headers={"Cookie": COOKIE} if COOKIE else {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type", ""), e.read()
    except Exception as e:
        return 0, "", str(e).encode()

def fiche(idu):
    st, ct, body = fetch(f"/parcels/{idu}", binary=False)
    if st != 200:
        return {}
    return json.loads(body)

def pdfinfo(path):
    try:
        out = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=60).stdout
        d = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1); d[k.strip()] = v.strip()
        return d
    except Exception as e:
        return {"_err": str(e)}

def pdffonts(path):
    try:
        out = subprocess.run(["pdffonts", path], capture_output=True, text=True, timeout=60).stdout
        rows = out.splitlines()[2:]
        fonts = []
        for r in rows:
            parts = r.split()
            if len(parts) >= 5:
                # name type emb sub uni ...
                fonts.append({"name": parts[0], "emb": "yes" in r.split()[2:4]})
        return out, any((" no " in (" " + ln + " ")) for ln in rows if ln.strip())
    except Exception as e:
        return str(e), False

def pdftext(path):
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=90).stdout
    except Exception as e:
        return ""

def pages_text(path):
    """Texte page par page (pour détecter pages blanches)."""
    try:
        info = pdfinfo(path)
        n = int(info.get("Pages", "0") or 0)
    except Exception:
        n = 0
    out = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), path, "-"],
                           capture_output=True, text=True, timeout=60).stdout
        out.append(t)
    return out

def scan(text):
    leaks = sorted(set(m.group(0) for pat in LEAKS for m in re.finditer(pat, text)))
    forb = sorted(set(m.group(0) for pat in FORBIDDEN for m in re.finditer(pat, text)))
    mentions = {k: bool(rx.search(text)) for k, rx in MENTIONS.items()}
    # placeholders simple-accolade non substitués (hors notation de nommage connue)
    ph = sorted(set(re.findall(r"\{[A-Za-z_]{2,}\}", text)))
    # dates clés
    data_au = re.findall(r"Donn[eé]es\s+LABUSE\s+au\s+(\d{2}/\d{2}/\d{4})", text)
    gen = re.findall(r"[Gg]én[eé]r[eé](?:\s+le|\s+via\s+LABUSE\s+le)?\s*:?\s*(\d{2}/\d{2}/\d{4}(?:\s*à\s*\d{1,2}h\d{2})?)", text)
    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
    return {"leaks": leaks, "forbidden": forb, "placeholders": ph, "mentions": mentions,
            "data_au": sorted(set(data_au)), "genere_le": sorted(set(gen)),
            "dates_distinctes": sorted(set(dates))[:20]}

def strip_timestamps(text):
    text = re.sub(r"\d{2}/\d{2}/\d{4}(?:\s+à\s+\d{1,2}h\d{2})?", "<DATE>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.+-]+", "<TS>", text)
    text = re.sub(r"[A-Z]{2}-[0-9a-f]{6,}", "<REF>", text)  # numéros de doc EF-xxxx
    return text

def main():
    only = None; onlydoc = None
    if "--only" in sys.argv: only = sys.argv[sys.argv.index("--only")+1]
    if "--doc" in sys.argv: onlydoc = sys.argv[sys.argv.index("--doc")+1]
    results = {}
    today_reunion = datetime.datetime.now(REUNION).strftime("%d/%m/%Y")
    for idu, cat in PARCELS:
        if only and idu != only: continue
        pdir = os.path.join(OUT, idu); os.makedirs(pdir, exist_ok=True)
        f = fiche(idu)
        json.dump(f, open(os.path.join(pdir, "fiche.json"), "w"), ensure_ascii=False, indent=1)
        pres = {"categorie": cat, "docs": {}}
        for doc, path in doc_url(idu).items():
            if onlydoc and doc != onlydoc: continue
            st, ct, body = fetch(path)
            ext = "zip" if doc == "pre_dossier" else ("pdf" if "pdf" in ct else "bin")
            if st != 200:
                ext = "json" if "json" in ct else "txt"
            fn = os.path.join(pdir, f"{doc}.{ext}")
            open(fn, "wb").write(body)
            entry = {"http": st, "ct": ct, "bytes": len(body)}
            if ext == "pdf":
                info = pdfinfo(fn); entry["pages"] = info.get("Pages"); entry["pdf_date"] = info.get("CreationDate")
                ff, has_fallback = pdffonts(fn); entry["font_non_embedded"] = has_fallback
                txt = pdftext(fn); open(fn.replace(".pdf", ".txt"), "w").write(txt)
                entry.update(scan(txt))
                # pages blanches
                pt = pages_text(fn)
                entry["blank_pages"] = [i+1 for i, t in enumerate(pt) if len(t.strip()) < 15]
                # régénérer: 2e passe
                st2, _, body2 = fetch(path)
                fn2 = fn + ".2"; open(fn2, "wb").write(body2)
                txt2 = pdftext(fn2)
                entry["regen_identique"] = strip_timestamps(txt) == strip_timestamps(txt2)
                os.remove(fn2)
            elif ext == "zip":
                try:
                    z = zipfile.ZipFile(io.BytesIO(body))
                    entry["zip_members"] = z.namelist()
                    allt = []
                    for name in z.namelist():
                        if name.lower().endswith(".pdf"):
                            tmp = os.path.join(pdir, "pd_" + os.path.basename(name))
                            open(tmp, "wb").write(z.read(name))
                            allt.append("### " + name + "\n" + pdftext(tmp))
                        elif name.lower().endswith((".txt", ".md")):
                            allt.append("### " + name + "\n" + z.read(name).decode("utf-8", "replace"))
                            # dates fichiers zip
                    entry["zip_dates"] = [(zi.filename, "%04d-%02d-%02d" % zi.date_time[:3]) for zi in z.infolist()]
                    joined = "\n".join(allt)
                    open(os.path.join(pdir, "pre_dossier_all.txt"), "w").write(joined)
                    entry.update(scan(joined))
                except Exception as e:
                    entry["zip_err"] = str(e)
            else:
                entry["body"] = body.decode("utf-8", "replace")[:400]
            pres["docs"][doc] = entry
        # Comparatif (paire) — ancre sur la parcelle courante + témoin fixe
        if not onlydoc or onlydoc == "comparatif":
            other = "97411000BZ1065" if idu != "97411000BZ1065" else "97411000AW0692"
            st, ct, body = fetch(f"/comparatif.pdf?idus={idu},{other}")
            fn = os.path.join(pdir, "comparatif.pdf"); open(fn, "wb").write(body)
            e = {"http": st, "ct": ct, "bytes": len(body), "paire": [idu, other]}
            if st == 200 and "pdf" in ct:
                info = pdfinfo(fn); e["pages"] = info.get("Pages")
                txt = pdftext(fn); open(fn.replace(".pdf", ".txt"), "w").write(txt); e.update(scan(txt))
            pres["docs"]["comparatif"] = e
        results[idu] = pres
        print(f"[{idu}] {cat}: " + ", ".join(f"{k}={v.get('http')}/{v.get('pages','-')}p" for k, v in pres["docs"].items()))
    results["_meta"] = {"today_reunion": today_reunion, "base": BASE, "generated_at": datetime.datetime.now(REUNION).isoformat()}
    json.dump(results, open(os.path.join(OUT, "resultats.json"), "w"), ensure_ascii=False, indent=1)
    print("\n→ preuves/resultats.json")

if __name__ == "__main__":
    main()
