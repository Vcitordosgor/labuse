"""CHASSE-CALCULS-1 — D2 : 5 témoins × chaque export, PDF→texte, confronté à la fiche.
LECTURE SEULE (génère les PDF en-process, aucune écriture). Pour chaque témoin :
  · lit la fiche /parcels/{idu} → chiffres SERVIS (surface terrain, SDP, taux TA, zone, commune) ;
  · génère Dossier / Bilan(financier) / Apporteur / Gabarit / Comparatif / Étude-zone / KMZ ;
  · extrait le texte (pdftotext) et vérifie : présence des chiffres fiche, absence de None/null,
    présence de la commune et du pied « Données LABUSE au ».
    LABUSE_DATABASE_URL=... PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/_exports_d2.py
"""
import json, subprocess, tempfile, os
from fastapi.testclient import TestClient
from labuse.api import auth
from labuse.api.app import app
from labuse.api.protection import HOTE_INTERNE

C = TestClient(app, client=(HOTE_INTERNE, 0)); C.cookies.set(auth.COOKIE, auth.make_token())
TEMOINS = ["97409000AK0804","97412000BV0419","97413000CA0243","97416000ES2238","97411000BZ1065"]

def pdftext(b):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b); p = f.name
    try:
        out = subprocess.run(["pdftotext","-layout",p,"-"],capture_output=True,timeout=60)
        return out.stdout.decode("utf-8","replace")
    finally:
        os.unlink(p)

def num_variants(n):
    if n is None: return []
    n = int(round(float(n)))
    s = str(n)
    grp = f"{n:,}".replace(",", " ")           # 27 862
    grp2 = f"{n:,}".replace(",", " ")      # fine space
    return list({s, grp, grp2})

def present(text, n):
    return any(v in text for v in num_variants(n))

for idu in TEMOINS:
    f = json.loads(C.get(f"/parcels/{idu}").content)
    surf = f.get("surface_terrain_m2")
    sdp = (f.get("potentiel_transformation") or {}).get("sdp_residuelle_m2")
    commune = f.get("commune")
    taxe = f.get("taxe_amenagement") or {}
    taux = taxe.get("taux_communal_pct")
    print("="*80)
    print(f"{idu}  {commune}  | surface={surf} SDP_servie={sdp} tauxTA={taux}")
    EXPORTS = {
        "Dossier":    f"/dossier/{idu}.pdf",
        "Bilan":      f"/financier/{idu}.pdf",
        "Apporteur":  f"/apporteur/{idu}.pdf",
        "Gabarit":    f"/gabarit/{idu}.pdf",
        "Comparatif": f"/comparatif.pdf?idus={idu}",
        "EtudeZone":  f"/etude-zone.pdf?idu={idu}",
        "KMZ":        f"/parcels/{idu}.kmz",
    }
    for nom, url in EXPORTS.items():
        r = C.get(url)
        if r.status_code != 200:
            print(f"   {nom:11} HTTP {r.status_code} — {r.text[:70]}")
            continue
        b = r.content
        if nom == "KMZ":
            import zipfile, io
            try:
                z = zipfile.ZipFile(io.BytesIO(b)); kml = z.read(z.namelist()[0]).decode("utf-8","replace")
                print(f"   {nom:11} {len(b):>7}o  kml={len(kml)}c  commune? {'oui' if (commune or '') in kml else 'non'}  idu? {'oui' if idu in kml else 'non'}")
            except Exception as e:
                print(f"   {nom:11} {len(b)}o  KMZ illisible: {e}")
            continue
        t = pdftext(b)
        flags = []
        if present(t, surf): flags.append("surface✓")
        elif surf: flags.append("surface✗")
        if sdp is not None:
            flags.append("SDP✓" if present(t, sdp) else "SDP✗")
        flags.append("commune✓" if (commune or "") in t else "commune✗")
        flags.append("pied✓" if "Données LABUSE au" in t else "pied✗")
        bad = [w for w in ("None","none","null","nan","undefined") if w in t]
        flags.append("None!"+str(bad) if bad else "0None✓")
        print(f"   {nom:11} {len(b):>7}o  texte={len(t):>5}c  {' '.join(flags)}")
