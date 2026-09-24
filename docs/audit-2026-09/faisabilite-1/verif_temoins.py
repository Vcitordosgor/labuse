"""FAISABILITE-1 Lot A — vérification sur témoins : moteur live vs résiduel servi.
Lancé : PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/.../verif_temoins.py
"""
import json
from labuse.db import session_scope
from labuse.faisabilite.db import parcel_faisabilite
from labuse.faisabilite.residuel import compute_residuel
from sqlalchemy import text

TEMOINS = {
    "BZ1065 (Saint-Denis)": 336319,
    "BW0457 (Saint-Paul, bâti)": 26887,
    "BW0457 (Saint-Benoît, sur-bâti)": 297303,
    "AB1117 (Bras-Panon, N-96% à cheval)": 63195,
}

with session_scope() as s:
    for nom, pid in TEMOINS.items():
        print("=" * 90)
        print(f"### {nom} — parcel_id={pid}")
        res = parcel_faisabilite(s, pid)  # défaut assiette_clippee=False (= servi live)
        if res is None:
            print("  parcel_faisabilite → None (hors PLU)")
        else:
            ctx, f = res
            print(f"  zone={f.zone} resolue={f.zone_resolue} constructible={f.constructible} "
                  f"calibree={f.calibree} cause={f.cause}")
            print(f"  verdict: {f.verdict}")
            print(f"  surface_m2={round(ctx.surface_m2)}")
            print("  --- STEPS (label | valeur | prov | source) ---")
            for st in f.steps:
                print(f"    · {st.label} | {st.valeur} | prov='{st.prov}' | {st.source}")
            fr = f.fourchette or {}
            for k in ("emprise_constructible_m2", "emprise_batie_max_m2", "surface_plancher_m2",
                      "niveaux_max", "logements_au_sol", "logements_sous_sol", "shab_vendable_m2"):
                if k in fr:
                    print(f"    fourchette.{k} = {fr[k]}")
        # résiduel LIVE deux modes
        r0 = compute_residuel(s, pid, assiette_clippee=False)
        r1 = compute_residuel(s, pid, assiette_clippee=True)
        print(f"  résiduel LIVE (clippee=False): dispo={r0.get('disponible')} "
              f"sdp_res={r0.get('sdp_residuelle_m2')} sdp_ecrite={r0.get('sdp_ecrite')} "
              f"cause={r0.get('cause')} taux_emprise={r0.get('taux_emprise_pct')}")
        print(f"  résiduel LIVE (clippee=True):  dispo={r1.get('disponible')} "
              f"sdp_res={r1.get('sdp_residuelle_m2')} sdp_ecrite={r1.get('sdp_ecrite')} "
              f"cause={r1.get('cause')}")
        # résiduel SERVI (vue)
        servi = s.execute(text(
            "SELECT sdp_residuelle_m2, taux_emprise_pct, pct_potentiel, cause, capacite_estimee "
            "FROM parcel_residuel WHERE parcel_id=:p"), {"p": pid}).first()
        print(f"  résiduel SERVI (vue parcel_residuel): {dict(servi._mapping) if servi else None}")
