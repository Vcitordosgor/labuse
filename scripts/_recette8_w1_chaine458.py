"""RECETTE-8 W1 — montrer la chaîne des m² taxés, étape par étape, sur 3 parcelles.

Pour chaque parcelle (nue / bâtie EL0157 / bâtie dense), on dump :
  - les Step du moteur de faisabilité (formule → valeur → source), c.-à-d. la chaîne
    surface → emprise → footprint → niveaux → SDP créée (plancher) ;
  - le bloc potentiel servi (au_sol.sdp_residuelle_m2 vs table_rase.plancher_m2) ;
  - le bloc taxe d'aménagement servi (assiette_m2 = plancher, total).

Aucune écriture. Lecture seule. `PYTHONPATH=src`.
"""
import sys
from sqlalchemy import text
from labuse.db import session_scope
from labuse.faisabilite.db import parcel_faisabilite
from labuse.faisabilite.potentiel import bloc_potentiel

PARCELS = [
    ("nue", "97401000AD0554"),
    ("bâtie (EL0157)", "97411000EL0157"),
    ("bâtie dense", "97411000BD0527"),
]


def main() -> None:
    with session_scope() as db:
        for label, idu in PARCELS:
            row = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).first()
            print("=" * 78)
            print(f"PARCELLE {label} — {idu}")
            if not row:
                print("  ABSENTE de la base locale")
                continue
            pid = row[0]
            surf = db.execute(text("SELECT round(ST_Area(geom::geography)) FROM parcels WHERE id=:p"),
                              {"p": pid}).scalar()
            nb = db.execute(text("SELECT count(*) FROM spatial_layers b JOIN parcels p ON p.id=:p "
                                 "WHERE b.kind='batiment' AND ST_Intersects(b.geom,p.geom)"),
                            {"p": pid}).scalar()
            print(f"  surface parcelle = {surf} m² · bâtiments intersectants = {nb}")

            pf = parcel_faisabilite(db, pid)
            if pf is None:
                print("  parcel_faisabilite → None (zone non résolue)")
            else:
                ctx, fa = pf
                print(f"  zone = {ctx.zone} (famille {ctx.zone_fam}) · commune {ctx.commune}")
                print(f"  constructible={fa.constructible} · cause={fa.cause}")
                print("  --- CHAÎNE (moteur estimate_capacity, faisabilite/engine.py) ---")
                for i, s in enumerate(fa.steps, 1):
                    print(f"   {i:2d}. {s.label}")
                    print(f"       formule : {s.formule}")
                    print(f"       valeur  : {s.valeur}   [source: {s.source}]")
                fo = fa.fourchette or {}
                print("  --- SORTIES fourchette ---")
                for k in ("emprise_batie_max_m2", "surface_plancher_m2", "shab_vendable_m2",
                          "niveaux", "niveaux_max", "hauteur_m", "logements_au_sol"):
                    if k in fo:
                        print(f"       {k} = {fo[k]}")

            pot = bloc_potentiel(db, pid)
            if pot:
                au = pot.get("au_sol") or {}
                tr = pot.get("table_rase") or {}
                print("  --- bloc_potentiel (potentiel.py) ---")
                print(f"       au_sol.sdp_residuelle_m2  = {au.get('sdp_residuelle_m2')}  (résiduel, ce qu'on ajoute sans démolir)")
                print(f"       table_rase.plancher_m2    = {tr.get('plancher_m2')}  (SDP créée, assiette taxe)")

            # bloc taxe servi
            from labuse.api.app import _taxe_amenagement_block
            tx = _taxe_amenagement_block(db, idu, pid)
            print("  --- bloc taxe (_taxe_amenagement_block) ---")
            if tx is None:
                print("       None (scénario table rase non constructible → pas d'estimation)")
            else:
                print(f"       assiette_m2 = {tx['assiette_m2']}  → total_eur = {tx['total_eur']}  "
                      f"(taux communal {tx['taux_communal_pct']})")
                print(f"       scenario = {tx['scenario']!r}")
            print()


if __name__ == "__main__":
    main()
