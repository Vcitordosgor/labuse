"""OUTIL-ASSEMBLAGE-FIX-2 (LOT 5) — tout chiffre du compte-rendu sort d'ICI (sortie brute collée).

Appelle l'endpoint SERVI `POST /moteurs/assemblage` (via la fonction, en base lecture seule) sur les
témoins, et imprime les grandeurs telles qu'elles sont RENVOYÉES À L'ÉCRAN — fini les chiffres
intermédiaires d'un diagnostic divergent (ex. FIX-1 avait noté 21 516 / 17 897 au lieu des 21 638 /
17 544 réellement servis). Lecture seule imposée par la base.

Usage : PYTHONPATH=src python docs/audit-2026-11/outil-assemblage-fix-1/figures_cr.py
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.api.moteurs import AssemblageIn
from labuse.api.moteurs import assemblage as endpoint

TEMOINS = {
    "DH (U2b/U2h)": ["97415000DH0076", "97415000DH0119", "97415000DH0120"],
    "CV (AU3c, bande intermédiaire)": ["97415000CV0724", "97415000CV1506", "97415000CV1507"],
    "BZ (Saint-Denis, hors SMS)": ["97411000BZ0824", "97411000BZ0381"],
}


def main() -> None:
    eng = create_engine(os.environ["LABUSE_DATABASE_URL"], pool_size=1, max_overflow=0)
    s = Session(eng)
    s.execute(text("SET default_transaction_read_only = on"))
    s.commit()
    for label, idus in TEMOINS.items():
        out = endpoint(AssemblageIn(idus=idus), db=s)
        print(f"\n### {label} — {[i[8:] for i in idus]}")
        print(f"  contigu={out['contigu']} relie={out['relie']} n={out['n']}")
        print(f"  surface_totale_m2       = {out['surface_totale_m2']}")
        print(f"  surface_constructible_m2= {out['surface_constructible_m2']}  (pct_hors_zone={out['pct_hors_zone']})")
        for z in (out.get("zones_detail") or []):
            print(f"    zone {z['zone']:5} emprise={z['emprise_m2']:>6} niveaux={z['niveaux']} "
                  f"recul_lim={z['recul_limites_m']} voie={z['recul_voirie_m']} SDP={z['sdp_m2']}")
        print(f"  sdp_terrain_libere_m2   = {out['sdp_terrain_libere_m2']}")
        print(f"  retranchements          = {out.get('retranchements')}")
        cf = out.get("charge_fonciere") or {}
        print(f"  charge_fonciere.central = {cf.get('central')}  prix_sortie={out.get('prix_sortie_eur_m2')}")
        mx = out.get("mixite")
        if mx:
            print(f"  mixite = regime={mx.get('regime')} quota={mx.get('quota_pct')}% "
                  f"borne_haute={mx.get('borne_haute')} {mx.get('article')} {mx.get('page')}")
    s.close()


if __name__ == "__main__":
    main()
