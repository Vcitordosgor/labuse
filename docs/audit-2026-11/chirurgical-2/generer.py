#!/usr/bin/env python3
"""AUDIT-CHIRURGICAL-2 — LOT A. Génère RÉELLEMENT tous les documents des 12 parcelles.
Lecture seule côté métier ; les seules écritures sont les documents_generes/courrier du
compte de test « AUDIT-TEST » (nettoyé en fin de mandat). Produit un manifest pour COUVERTURE-2.
"""
from __future__ import annotations
import json, os, subprocess, sys, zipfile
from pathlib import Path
import httpx

BASE = "http://127.0.0.1:7440"
COOKIE = os.environ["AUDIT_COOKIE"]  # u.<token> de AUDIT-TEST
OUT = Path.home() / "Desktop" / "chasse-1"
MANIFEST = []

PARCELLES = [
    "97422000AD0887",  # canari — Le Tampon, constructible 1699 m²
    "97416000HT0538",  # canari — Saint-Pierre 509 m² (0 place stationnement)
    "97403000AR1517",  # A constructible — Entre-Deux 734 m²
    "97404000AM0838",  # grande + non constructible UE — L'Étang-Salé 20798 m²
    "97417000AO0050",  # RNU — Saint-Philippe 1549 m²
    "97411000IS0448",  # à cheval + EBC zone N — Saint-Denis 818 m²
    "97404000AY0153",  # zone rouge partielle — L'Étang-Salé 256 m²
    "97414000CO0153",  # zone rouge partielle + grande agricole — Saint-Louis 6670 m²
    "97421000BN0260",  # à cheval + grande agricole — Salazie 3353 m²
    "97422000BW2635",  # copropriété — Le Tampon 2002 m²
    "97412000CV0446",  # propriétaire public — Saint-Joseph 567 m²
    "97424000AO1198",  # très petite non constructible (exigu) — Cilaos 0.69 m²
]

client = httpx.Client(base_url=BASE, cookies={"labuse_session": COOKIE}, timeout=120.0, follow_redirects=False)


def rec(idu, doc, method, url, status, size, note=""):
    MANIFEST.append({"idu": idu, "doc": doc, "method": method, "url": url,
                     "status": status, "size": size, "note": note})
    print(f"  [{status}] {doc:20} {size:>9}B {note}")


def save(p: Path, content: bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)


def totext(pdf: Path):
    try:
        subprocess.run(["pdftotext", "-layout", str(pdf), str(pdf.with_suffix(".txt"))],
                       check=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        (pdf.with_suffix(".txt")).write_text(f"[pdftotext échec: {e}]")


def get(idu, doc, path, out: Path, totxt=False):
    try:
        r = client.get(path)
    except Exception as e:  # noqa: BLE001
        rec(idu, doc, "GET", path, "ERR", 0, str(e)[:80]); return None
    note = ""
    if r.status_code == 200:
        save(out, r.content)
        if totxt and out.suffix == ".pdf":
            totext(out)
    else:
        note = r.text[:120].replace("\n", " ")
    rec(idu, doc, "GET", path, r.status_code, len(r.content), note)
    return r


def post(idu, doc, path, body, out: Path | None, totxt=False, is_pdf=False):
    try:
        r = client.post(path, json=body)
    except Exception as e:  # noqa: BLE001
        rec(idu, doc, "POST", path, "ERR", 0, str(e)[:80]); return None
    note = ""
    if r.status_code == 200 and out is not None:
        save(out, r.content)
        if totxt and out.suffix == ".pdf":
            totext(out)
    elif r.status_code != 200:
        note = r.text[:140].replace("\n", " ")
    rec(idu, doc, "POST", path, r.status_code, len(r.content), note)
    return r


def default_bilan_payload(idu):
    r = client.get(f"/bilan/{idu}/modele")
    if r.status_code != 200:
        return None, r
    m = r.json()
    cal = {c["id"]: c.get("defaut") for c in (m.get("calendrier") or [])}
    postes = {pid: {"valeur": v["valeur"], "etat": "ratios", "tva": v.get("tva")}
              for pid, v in (m.get("ratios_compte") or {}).items()}
    payload = {
        "programme": {"terrain": m["sourcee"].get("terrain"), "surface_taxable": None,
                      "loyer": None, "sdp": None},
        "produits": [{"libelle": "Produit 1", "lots": None, "suv": None, "prix_ttc_m2_suv": None, "tva": None},
                     {"libelle": "Produit 2", "lots": None, "suv": None, "prix_ttc_m2_suv": None, "tva": None}],
        "postes": postes, "mode": "marge", "marge_cible": None, "calendrier": cal, "empreinte": None,
    }
    return payload, r


def one(idu):
    print(f"\n=== {idu} ===")
    d = OUT / idu
    get(idu, "dossier", f"/dossier/{idu}.pdf", d / "dossier.pdf", totxt=True)
    get(idu, "gabarit", f"/gabarit/{idu}.pdf", d / "gabarit.pdf", totxt=True)
    get(idu, "apporteur", f"/apporteur/{idu}.pdf", d / "apporteur.pdf", totxt=True)
    get(idu, "estimer_parcelle", f"/analyse-annonce/{idu}.pdf", d / "estimer.pdf", totxt=True)
    get(idu, "etude_zone", f"/etude-zone.pdf?idu={idu}&rayon_km=1", d / "etudezone.pdf", totxt=True)

    # pré-dossier ZIP + extraction des pièces
    r = get(idu, "predossier_zip", f"/pre-dossier/{idu}.zip", d / "predossier.zip")
    if r is not None and r.status_code == 200:
        try:
            zf = zipfile.ZipFile(d / "predossier.zip")
            pieces = d / "predossier_pieces"
            pieces.mkdir(exist_ok=True)
            zf.extractall(pieces)
            for p in pieces.rglob("*.pdf"):
                totext(p)
            rec(idu, "predossier_pieces", "-", "-", "OK", 0, ",".join(zf.namelist()))
        except Exception as e:  # noqa: BLE001
            rec(idu, "predossier_pieces", "-", "-", "ERR", 0, str(e)[:80])

    # Bilan PDF + Excel (pré-remplissage par défaut → generer → doc_id)
    payload, mr = default_bilan_payload(idu)
    if payload is None:
        rec(idu, "bilan_modele", "GET", f"/bilan/{idu}/modele", mr.status_code, 0, mr.text[:120])
    else:
        # (a) pré-remplissage par DÉFAUT (sans produit) — attendu : 422 export sans CA.
        g = client.post(f"/bilan/{idu}/generer", json=payload)
        if g.status_code == 200:
            doc_id = g.json()["doc_id"]
            rec(idu, "bilan_generer_defaut", "POST", f"/bilan/{idu}/generer", 200, 0,
                f"doc_id={doc_id} complet={g.json().get('complet')} vides={g.json().get('lignes_vides')}")
            get(idu, "bilan_pdf_defaut", f"/bilan/{idu}.pdf?doc_id={doc_id}", d / "bilan_defaut.pdf", totxt=True)
            get(idu, "bilan_xlsx_defaut", f"/bilan/{idu}.xlsx?doc_id={doc_id}", d / "bilan_defaut.xlsx")
        else:
            rec(idu, "bilan_generer_defaut", "POST", f"/bilan/{idu}/generer", g.status_code, 0, g.text[:120])
        # (b) scénario MINIMAL chiffré (produit + prix repère DVF neuf) pour exercer PDF/Excel + arithmétique.
        mj = mr.json()
        dvf = (mj.get("reperes_publics") or {}).get("dvf_neuf") or {}
        prix = dvf.get("valeur") or 4000.0
        filled = json.loads(json.dumps(payload))
        filled["produits"][0] = {"libelle": "Logements", "lots": 10, "suv": 60.0,
                                 "prix_ttc_m2_suv": prix, "tva": 20.0}
        filled["programme"]["sdp"] = 600.0
        g2 = client.post(f"/bilan/{idu}/generer", json=filled)
        if g2.status_code == 200:
            doc_id2 = g2.json()["doc_id"]
            rec(idu, "bilan_generer_rempli", "POST", f"/bilan/{idu}/generer", 200, 0,
                f"doc_id={doc_id2} prix={prix} complet={g2.json().get('complet')}")
            get(idu, "bilan_pdf", f"/bilan/{idu}.pdf?doc_id={doc_id2}", d / "bilan.pdf", totxt=True)
            get(idu, "bilan_xlsx", f"/bilan/{idu}.xlsx?doc_id={doc_id2}", d / "bilan.xlsx")
        else:
            rec(idu, "bilan_generer_rempli", "POST", f"/bilan/{idu}/generer", g2.status_code, 0, g2.text[:120])

    # Courrier propriétaire
    post(idu, "courrier_composer", "/courrier/composer", {"idu": idu}, d / "courrier_composer.json")
    cp = client.post("/courrier/pdf", json={"idu": idu})
    if cp.status_code == 200:
        save(d / "courrier.pdf", cp.content); totext(d / "courrier.pdf")
    rec(idu, "courrier_pdf", "POST", "/courrier/pdf", cp.status_code, len(cp.content),
        "" if cp.status_code == 200 else cp.text[:120])

    # Étude de faisabilité — moteur réel (lent). Analyse JSON puis PDF.
    cfg = {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
           "stationnement": "aerien", "terrain": "libere"}
    ra = client.post("/modules/etude", json=cfg, timeout=120.0)
    if ra.status_code == 200:
        save(d / "etude_faisa.json", ra.content)
    rec(idu, "etude_faisa_json", "POST", "/modules/etude", ra.status_code, len(ra.content),
        "" if ra.status_code == 200 else ra.text[:140])
    rp = client.post("/modules/etude/pdf", json=cfg, timeout=120.0)
    if rp.status_code == 200:
        save(d / "etude_faisa.pdf", rp.content); totext(d / "etude_faisa.pdf")
    rec(idu, "etude_faisa_pdf", "POST", "/modules/etude/pdf", rp.status_code, len(rp.content),
        "" if rp.status_code == 200 else rp.text[:140])

    # Stationnement (canari C-a + règle maison/immeuble)
    st = client.post("/modules/etude/stationnement", json={"idus": [idu], "type_projet": "collectif"})
    if st.status_code == 200:
        save(d / "stationnement.json", st.content)
    rec(idu, "stationnement", "POST", "/modules/etude/stationnement", st.status_code, len(st.content), "")

    # Fiche JSON (référence des faits servis)
    get(idu, "fiche", f"/parcels/{idu}", d / "fiche.json")


def comparatifs():
    print("\n=== COMPARATIFS ===")
    cdir = OUT / "_comparatifs"
    combos = [
        ("c1_constructibles", ["97422000AD0887", "97416000HT0538", "97403000AR1517"]),
        ("c2_rouge_grandes", ["97404000AY0153", "97414000CO0153", "97404000AM0838"]),
        ("c3_cheval_public_copro", ["97411000IS0448", "97412000CV0446", "97422000BW2635"]),
        ("c4_rnu_exigu_salazie", ["97417000AO0050", "97424000AO1198", "97421000BN0260"]),
    ]
    for name, idus in combos:
        q = ",".join(idus)
        get(name, "comparatif", f"/comparatif.pdf?idus={q}", cdir / f"{name}.pdf", totxt=True)


def estimer_lien():
    print("\n=== ESTIMER PAR LIEN D'ANNONCE (Radar local) ===")
    edir = OUT / "_estimer_lien"
    # URLs d'annonces à fournir par l'orchestrateur via ESTIMER_LIENS (séparées par ;)
    liens = [u for u in os.environ.get("ESTIMER_LIENS", "").split(";") if u.strip()]
    if not liens:
        rec("-", "estimer_lien", "-", "-", "SKIP", 0, "aucune URL d'annonce fournie (ESTIMER_LIENS vide)")
        return
    for i, url in enumerate(liens[:2], 1):
        from urllib.parse import quote
        get(f"lien{i}", "estimer_lien", f"/analyse-annonce.pdf?url={quote(url, safe='')}",
            edir / f"estimer_lien_{i}.pdf", totxt=True)


if __name__ == "__main__":
    only = sys.argv[1:] or PARCELLES
    for idu in only:
        if idu.startswith("97"):
            one(idu)
    if not sys.argv[1:]:
        comparatifs()
        estimer_lien()
    man = Path(__file__).parent / "manifest_generation.csv"
    import csv
    with man.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "doc", "method", "url", "status", "size", "note"])
        w.writeheader(); w.writerows(MANIFEST)
    print(f"\nManifest → {man} ({len(MANIFEST)} lignes)")
