#!/usr/bin/env python3
"""Corrige le faux positif TVA : régénère les 12 Bilans avec TVA = fraction DOM 0.085
(et non 20.0 = 2000 % passé par erreur au 1er run), puis RECALCULE HT/TVA/TTC
indépendamment pour vérifier que le moteur est correct."""
import csv, json, os, subprocess
from pathlib import Path
import httpx

BASE = "http://127.0.0.1:7440"
COOKIE = os.environ["AUDIT_COOKIE"]
OUT = Path.home() / "Desktop" / "chasse-1"
PARCELLES = ["97422000AD0887","97416000HT0538","97403000AR1517","97404000AM0838",
    "97417000AO0050","97411000IS0448","97404000AY0153","97414000CO0153",
    "97421000BN0260","97422000BW2635","97412000CV0446","97424000AO1198"]
client = httpx.Client(base_url=BASE, cookies={"labuse_session": COOKIE}, timeout=120.0)
rows = []
for idu in PARCELLES:
    m = client.get(f"/bilan/{idu}/modele").json()
    cal = {c["id"]: c.get("defaut") for c in (m.get("calendrier") or [])}
    prix = ((m.get("reperes_publics") or {}).get("dvf_neuf") or {}).get("valeur") or 4000.0
    payload = {
        "programme": {"terrain": m["sourcee"].get("terrain"), "surface_taxable": None, "loyer": None, "sdp": 600.0},
        "produits": [{"libelle": "Logements", "lots": 10, "suv": 60.0, "prix_ttc_m2_suv": prix, "tva": 0.085},
                     {"libelle": "Produit 2", "lots": None, "suv": None, "prix_ttc_m2_suv": None, "tva": None}],
        "postes": {}, "mode": "marge", "marge_cible": None, "calendrier": cal, "empreinte": None,
    }
    g = client.post(f"/bilan/{idu}/generer", json=payload).json()
    doc_id = g["doc_id"]
    pdf = client.get(f"/bilan/{idu}.pdf?doc_id={doc_id}")
    (OUT / idu / "bilan.pdf").write_bytes(pdf.content)
    subprocess.run(["pdftotext", "-layout", str(OUT/idu/"bilan.pdf"), str(OUT/idu/"bilan.txt")], check=False)
    xls = client.get(f"/bilan/{idu}.xlsx?doc_id={doc_id}")
    (OUT / idu / "bilan.xlsx").write_bytes(xls.content)
    # recompute independently from printed CA TTC
    import re
    txt = (OUT/idu/"bilan.txt").read_text()
    def grab(label):
        m2 = re.search(label + r"[^\d\-]*([\d   ]+)", txt)
        return int(re.sub(r"[   ]", "", m2.group(1))) if m2 else None
    ttc = grab(r"Chiffre d'affaires TTC|TTC")
    ht = grab(r"Chiffre d'affaires HT|HT")
    exp_ht = round(ttc/1.085) if ttc else None
    ok = (ht is not None and exp_ht is not None and abs(ht-exp_ht) <= 2)
    rows.append({"idu": idu, "prix_ttc_m2": prix, "doc_id": doc_id, "ttc_imprime": ttc,
                 "ht_imprime": ht, "ht_attendu_/1.085": exp_ht, "coherent": ok})
    print(f"{idu} TTC={ttc} HT_imp={ht} HT_attendu={exp_ht} OK={ok}")
with (Path(__file__).parent/"bilan_tva_verif.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("→ bilan_tva_verif.csv")
