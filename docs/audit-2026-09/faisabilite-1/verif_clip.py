"""FAISABILITE-clip — le moteur live (clippé par défaut) : fiche §capacité == onglet Faisabilité,
capacité POSITIVE sur les parcelles A/N à cheval, alignée sur le run résiduel servi.
Lancé : PYTHONPATH=src LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
        ~/Desktop/labuse/.venv/bin/python docs/.../verif_clip.py
"""
from fastapi.testclient import TestClient
from labuse.api.app import app
from labuse.db import session_scope
from labuse.faisabilite.db import fiche_payload
from sqlalchemy import text

c = TestClient(app)
TEMOINS = {
    "AB1117 (Bras-Panon, N-96%)": "97402000AB1117",
    "AL0693 (Saint-André, A)": "97409000AL0693",
    "CW0979 (Saint-Paul, N)": "97415000CW0979",
}

with session_scope() as s:
    for nom, idu in TEMOINS.items():
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        # onglet Faisabilité (outil + fiche) = endpoint sens1
        j = c.get(f"/modules/faisabilite/{idu}").json()
        cap = j.get("capacite") or {}
        sens1_sdp = (cap.get("fourchette") or {}).get("surface_plancher_m2")
        sens1_verdict = cap.get("verdict")
        # fiche §capacité = fiche_payload
        fp = fiche_payload(s, pid) or {}
        fiche_sdp = (fp.get("fourchette") or {}).get("surface_plancher_m2")
        fiche_verdict = fp.get("verdict")
        # run résiduel servi
        servi = s.execute(text("SELECT sdp_residuelle_m2 FROM parcel_residuel WHERE parcel_id=:p"),
                          {"p": pid}).scalar()
        ok = (sens1_sdp == fiche_sdp) and (sens1_verdict == fiche_verdict)
        print(f"### {nom}")
        print(f"  onglet Faisabilité (sens1) : constructible={fp.get('constructible')} "
              f"SDP={sens1_sdp} — {sens1_verdict}")
        print(f"  fiche §capacité (fiche_payload) : SDP={fiche_sdp} — {fiche_verdict}")
        print(f"  résiduel servi (parcel_residuel) : {servi} m²")
        print(f"  → MÊME CHIFFRE fiche == outil : {'OUI' if ok else 'NON'}")
        print()
