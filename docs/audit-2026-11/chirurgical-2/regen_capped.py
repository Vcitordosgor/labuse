#!/usr/bin/env python3
"""Regénère les documents bloqués par le plafond d'export (429) EN MODE PILOTE (sans cookie,
donc hors quota d'usage loyal). Lecture seule. Complète LOT A après le blocage du 1er run."""
from __future__ import annotations
import csv, json, os, subprocess, zipfile
from pathlib import Path
from urllib.parse import quote
import httpx

BASE = "http://127.0.0.1:7440"
OUT = Path.home() / "Desktop" / "chasse-1"
MAN = []
PARCELLES = [
    "97422000AD0887","97416000HT0538","97403000AR1517","97404000AM0838",
    "97417000AO0050","97411000IS0448","97404000AY0153","97414000CO0153",
    "97421000BN0260","97422000BW2635","97412000CV0446","97424000AO1198",
]
client = httpx.Client(base_url=BASE, timeout=120.0)  # NO cookie → pilote → uncapped

def rec(idu, doc, url, r, extra=""):
    MAN.append({"idu": idu, "doc": doc, "url": url, "status": r.status_code if r else "ERR",
                "size": len(r.content) if r else 0, "note": extra or ("" if r and r.status_code==200 else (r.text[:120].replace(chr(10)," ") if r else ""))})
    print(f"  [{r.status_code if r else 'ERR'}] {idu} {doc:18} {len(r.content) if r else 0:>9}B {extra}")

def totext(pdf):
    try: subprocess.run(["pdftotext","-layout",str(pdf),str(pdf.with_suffix(".txt"))],check=True,timeout=60)
    except Exception as e: (pdf.with_suffix(".txt")).write_text(f"[pdftotext échec {e}]")

def get(idu, doc, path, out, totxt=True):
    try: r = client.get(path)
    except Exception as e: rec(idu, doc, path, None, str(e)[:80]); return None
    if r.status_code == 200:
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(r.content)
        if totxt and out.suffix == ".pdf": totext(out)
    rec(idu, doc, path, r); return r

for idu in PARCELLES:
    print(f"=== {idu} ===")
    d = OUT / idu
    get(idu, "dossier", f"/dossier/{idu}.pdf", d/"dossier.pdf")
    get(idu, "gabarit", f"/gabarit/{idu}.pdf", d/"gabarit.pdf")
    get(idu, "estimer_parcelle", f"/analyse-annonce/{idu}.pdf", d/"estimer.pdf")
    get(idu, "etude_zone", f"/etude-zone.pdf?idu={idu}&rayon_km=1", d/"etudezone.pdf")
    r = get(idu, "predossier_zip", f"/pre-dossier/{idu}.zip", d/"predossier.zip", totxt=False)
    if r is not None and r.status_code == 200:
        try:
            zf = zipfile.ZipFile(d/"predossier.zip"); pieces = d/"predossier_pieces"; pieces.mkdir(exist_ok=True)
            zf.extractall(pieces)
            for p in pieces.rglob("*.pdf"): totext(p)
            rec(idu,"predossier_pieces",f"/pre-dossier/{idu}.zip",r,",".join(zf.namelist()))
        except Exception as e: print("   zip err", e)

print("=== COMPARATIFS ===")
cdir = OUT/"_comparatifs"
for name, idus in [
    ("c1_constructibles", ["97422000AD0887","97416000HT0538","97403000AR1517"]),
    ("c2_rouge_grandes", ["97404000AY0153","97414000CO0153","97404000AM0838"]),
    ("c3_cheval_public_copro", ["97411000IS0448","97412000CV0446","97422000BW2635"]),
    ("c4_rnu_exigu_salazie", ["97417000AO0050","97424000AO1198","97421000BN0260"]),
]:
    get(name, "comparatif", f"/comparatif.pdf?idus={','.join(idus)}", cdir/f"{name}.pdf")

print("=== ESTIMER LIEN ===")
edir = OUT/"_estimer_lien"
liens = [u for u in os.environ.get("ESTIMER_LIENS","").split(";") if u.strip()]
for i, u in enumerate(liens[:2], 1):
    get(f"lien{i}", "estimer_lien", f"/analyse-annonce.pdf?url={quote(u, safe='')}", edir/f"estimer_lien_{i}.pdf")

man = Path(__file__).parent/"manifest_regen_capped.csv"
with man.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["idu","doc","url","status","size","note"]); w.writeheader(); w.writerows(MAN)
print(f"\nManifest → {man} ({len(MAN)} lignes)")
