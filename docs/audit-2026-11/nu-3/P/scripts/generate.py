#!/usr/bin/env python3
"""LOT P — génère tous les documents de chaque parcelle. Lecture seule (lit l'API 9440 + Flash direct)."""
import json, os, sys, urllib.request, urllib.error, zipfile, io, pathlib, csv
BASE = "http://127.0.0.1:9440"
OUT = pathlib.Path("/Users/openclaw/Desktop/labuse-nu3-p/docs/audit-2026-11/nu-3/P/out")
PDFDIR = OUT / "pdf"
PDFDIR.mkdir(parents=True, exist_ok=True)

PARCELLES = []
with open(OUT / "parcelles.csv") as f:
    for row in csv.DictReader(f):
        PARCELLES.append(row)
IDUS = [p["idu"] for p in PARCELLES]

def http_get(path, timeout=120):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, r.headers.get_content_type(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get_content_type() if e.headers else "", e.read()
    except Exception as e:
        return -1, "", str(e).encode()

def http_post(path, body, timeout=180):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get_content_type(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get_content_type() if e.headers else "", e.read()
    except Exception as e:
        return -1, "", str(e).encode()

log = []
def save(idu, doc, status, ctype, blob):
    ok = status == 200 and ("pdf" in (ctype or "") or doc == "pre-dossier")
    note = ""
    if status == 200 and "pdf" in (ctype or ""):
        (PDFDIR / f"{idu}__{doc}.pdf").write_bytes(blob)
        note = f"{len(blob)}o"
    elif doc == "pre-dossier" and status == 200:
        # extraire tous les PDF du zip, concaténer en un pseudo-doc par pièce
        try:
            z = zipfile.ZipFile(io.BytesIO(blob))
            names = z.namelist()
            note = "zip:" + ",".join(n.split("-", 1)[-1][:24] for n in names)
            for n in names:
                if n.lower().endswith(".pdf"):
                    piece = n.split("-", 1)[-1].replace(".pdf", "").replace("/", "_")[:30]
                    (PDFDIR / f"{idu}__predossier_{piece}.pdf").write_bytes(z.read(n))
            # LISEZMOI
            for n in names:
                if "LISEZMOI" in n.upper() or n.lower().endswith(".txt"):
                    (PDFDIR / f"{idu}__predossier_LISEZMOI.txt").write_bytes(z.read(n))
        except Exception as e:
            note = "zip-err:" + str(e)[:40]
            ok = False
    else:
        # échec : garder le message
        try:
            msg = json.loads(blob).get("detail")
            if isinstance(msg, dict):
                msg = msg.get("message") or json.dumps(msg, ensure_ascii=False)
        except Exception:
            msg = blob[:160].decode("utf-8", "replace")
        note = f"{status} {ctype} :: {str(msg)[:140]}"
    log.append({"idu": idu, "doc": doc, "status": status, "ctype": ctype, "ok": ok, "note": note})
    print(f"  {doc:22} -> {status} {ctype:18} {note[:80]}")

for i, p in enumerate(PARCELLES):
    idu = p["idu"]
    print(f"[{p['role']}] {idu} ({p['commune']})")
    # 1. Dossier (expert)
    save(idu, "dossier", *http_get(f"/dossier/{idu}.pdf"))
    # 2. Export fiche PDF (premium)
    save(idu, "export-fiche", *http_get(f"/parcels/{idu}/export.pdf?source=q_v20"))
    # 3. Apporteur
    save(idu, "apporteur", *http_get(f"/apporteur/{idu}.pdf"))
    # 4. Pré-dossier PC (zip)
    save(idu, "pre-dossier", *http_get(f"/pre-dossier/{idu}.zip"))
    # 5. Gabarit
    save(idu, "gabarit", *http_get(f"/gabarit/{idu}.pdf"))
    # 6. Étude de zone
    save(idu, "etude-zone", *http_get(f"/etude-zone.pdf?idu={idu}&rayon_km=2"))
    # 7. Estimer (analyse-annonce parcelle)
    save(idu, "estimer", *http_get(f"/analyse-annonce/{idu}.pdf"))
    # 8. Financier / Bilan (banquier == argumentaire, redirections)
    save(idu, "financier", *http_get(f"/financier/{idu}.pdf"))
    # 9. Comparatif (apparié avec la parcelle suivante)
    partner = IDUS[(i + 1) % len(IDUS)]
    save(idu, "comparatif", *http_get(f"/comparatif.pdf?idus={idu},{partner}"))
    # 10. Étude de faisabilité (POST) — tentative minimale
    body = {"idu": idu, "programme": "libre", "niveaux": 2}
    save(idu, "etude-faisabilite", *http_post("/modules/etude/pdf", body))

with open(OUT / "generation_log.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["idu", "doc", "status", "ctype", "ok", "note"])
    w.writeheader()
    w.writerows(log)
print("\nTotal lignes:", len(log), "— OK:", sum(1 for r in log if r["ok"]))
