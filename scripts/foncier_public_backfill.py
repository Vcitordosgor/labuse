"""FONCIER-PUBLIC-1 — backfill des colonnes `public_facility` / `public_land` sur un run de
scénarios DÉJÀ persisté (ici le run servi `q_v20`), + application de la règle d'équipement public
(statut « Hors de ce projet ») et mesure AVANT/APRÈS sur l'île.

Pourquoi un backfill plutôt qu'un recalcul : la table `parcel_scenario_v2_runs` porte déjà les
quantités ENRICHIES (reconstruction exacte) du run. Un recalcul `enrich=False` les écraserait. On ne
fait donc qu'AJOUTER l'overlay foncier/équipement : deux colonnes, et pour les équipements publics un
override du statut (les quantités restent, le statut domine). Idempotent.

La classification vient du module `equipement_public` (source unique, mirroir de l'adaptateur et des
tests). LECTURE de la BPE (`spatial_layers kind='amenite_bpe'`, point dans parcelle, `geom_2975`
indexé) et des propriétaires (`parcelle_personne_morale`, groupes DGFiP publics). Aucune écriture hors
`parcel_scenario_v2_runs`.

Usage : python -m scripts.foncier_public_backfill [run_label]  (défaut q_v20)
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import text

from labuse.db import make_engine
from labuse.scoring import equipement_public as eqp
from labuse.proprietaire_type import PUBLIC_DGFIP_GROUPES

URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")


def main(run: str = "q_v20") -> None:
    eng = make_engine(URL)
    cat = eqp.categorie_sql("b")
    prio = eqp.priorite_sql(cat)
    with eng.begin() as cx:
        # 0. colonnes (idempotent) — même DDL que le module de persistance.
        cx.execute(text("ALTER TABLE parcel_scenario_v2_runs ADD COLUMN IF NOT EXISTS public_facility text"))
        cx.execute(text("ALTER TABLE parcel_scenario_v2_runs "
                        "ADD COLUMN IF NOT EXISTS public_land boolean NOT NULL DEFAULT false"))

        # 1. équipement public dominant PAR PARCELLE — on part des ~3 500 points BPE RETENUS (indexés)
        #    et on trouve la parcelle qui les contient : bien moins coûteux que scanner 433k parcelles.
        cx.execute(text("DROP TABLE IF EXISTS _fp_fac"))
        cx.execute(text(f"""
            CREATE TEMP TABLE _fp_fac AS
            SELECT DISTINCT ON (p.id) p.id AS parcel_id, {cat} AS public_facility
            FROM spatial_layers b
            JOIN parcels p ON ST_Intersects(b.geom_2975, p.geom_2975)
            WHERE b.kind = 'amenite_bpe' AND b.attrs->>'sdom' = ANY(:sdoms)
            ORDER BY p.id, {prio}"""), {"sdoms": list(eqp.RETENU_SDOM)})
        cx.execute(text("CREATE INDEX _fp_fac_ix ON _fp_fac (parcel_id)"))

        # 2. propriétaire public PAR PARCELLE (restreint aux parcelles du run).
        cx.execute(text("DROP TABLE IF EXISTS _fp_land"))
        cx.execute(text("""
            CREATE TEMP TABLE _fp_land AS
            SELECT DISTINCT s.parcel_id
            FROM parcel_scenario_v2_runs s
            JOIN parcelle_personne_morale m ON m.idu = s.idu AND m.groupe = ANY(:pub)
            WHERE s.run_label = :run"""), {"pub": list(PUBLIC_DGFIP_GROUPES), "run": run})
        cx.execute(text("CREATE INDEX _fp_land_ix ON _fp_land (parcel_id)"))

        # ── MESURE AVANT (sur la CONSERVATION servie ; l'île = toutes les parcelles du run) ──────────
        def scal(sql, **p):
            return cx.execute(text(sql), {"run": run, **p}).scalar() or 0

        ab_avant = scal("SELECT count(*) FROM parcel_scenario_v2_runs "
                        "WHERE run_label=:run AND scenario='keep' AND status='ESTIMATED' AND band IN ('A','B')")
        equip_total = scal("SELECT count(*) FROM _fp_fac f "
                           "WHERE EXISTS (SELECT 1 FROM parcel_scenario_v2_runs s "
                           "WHERE s.run_label=:run AND s.parcel_id=f.parcel_id)")
        # équipements qui n'étaient PAS déjà « Hors projet » en conservation → ils SORTENT.
        equip_sortent = scal("""
            SELECT count(*) FROM _fp_fac f
            JOIN parcel_scenario_v2_runs s ON s.run_label=:run AND s.scenario='keep' AND s.parcel_id=f.parcel_id
            WHERE s.status <> 'OUTSIDE_OBJECTIVE'""")
        equip_ab = scal("""
            SELECT count(*) FROM _fp_fac f
            JOIN parcel_scenario_v2_runs s ON s.run_label=:run AND s.scenario='keep' AND s.parcel_id=f.parcel_id
            WHERE s.status='ESTIMATED' AND s.band IN ('A','B')""")
        par_cat = cx.execute(text("""
            SELECT f.public_facility, count(*) FROM _fp_fac f
            JOIN parcel_scenario_v2_runs s ON s.run_label=:run AND s.scenario='keep' AND s.parcel_id=f.parcel_id
            GROUP BY 1 ORDER BY 2 DESC"""), {"run": run}).fetchall()
        foncier_sans_equip = scal("""
            SELECT count(*) FROM _fp_land l
            WHERE NOT EXISTS (SELECT 1 FROM _fp_fac f WHERE f.parcel_id=l.parcel_id)""")
        foncier_sans_equip_ab = scal("""
            SELECT count(*) FROM _fp_land l
            JOIN parcel_scenario_v2_runs s ON s.run_label=:run AND s.scenario='keep' AND s.parcel_id=l.parcel_id
            WHERE s.status='ESTIMATED' AND s.band IN ('A','B')
              AND NOT EXISTS (SELECT 1 FROM _fp_fac f WHERE f.parcel_id=l.parcel_id)""")

        # ── ÉCRITURE (les deux scénarios) ───────────────────────────────────────────────────────────
        cx.execute(text("""
            UPDATE parcel_scenario_v2_runs t
            SET public_land = EXISTS (SELECT 1 FROM _fp_land l WHERE l.parcel_id = t.parcel_id)
            WHERE t.run_label = :run"""), {"run": run})
        cx.execute(text("""
            UPDATE parcel_scenario_v2_runs t
            SET public_facility = f.public_facility
            FROM _fp_fac f WHERE f.parcel_id = t.parcel_id AND t.run_label = :run"""), {"run": run})
        # Équipement public → « Hors de ce projet », cause EQUIPEMENT_PUBLIC:<cat> (les DEUX scénarios).
        # Les quantités restent pour la traçabilité ; le statut domine, la bande/score sont retirés.
        maj = cx.execute(text("""
            UPDATE parcel_scenario_v2_runs t
            SET status='OUTSIDE_OBJECTIVE',
                cause = to_jsonb(ARRAY['EQUIPEMENT_PUBLIC:' || t.public_facility]),
                band=NULL, score=NULL, band_provisional=NULL
            WHERE t.run_label=:run AND t.public_facility IS NOT NULL"""), {"run": run}).rowcount

        ab_apres = scal("SELECT count(*) FROM parcel_scenario_v2_runs "
                        "WHERE run_label=:run AND scenario='keep' AND status='ESTIMATED' AND band IN ('A','B')")
        hors_apres = scal("SELECT count(*) FROM parcel_scenario_v2_runs "
                          "WHERE run_label=:run AND scenario='keep' AND status='OUTSIDE_OBJECTIVE'")

    print(f"== FONCIER-PUBLIC-1 backfill — run {run} ==")
    print(f"équipement public (parcelles distinctes)           : {equip_total}")
    print(f"  dont bande A/B avant (conservation)              : {equip_ab}")
    print(f"  SORTENT (n'étaient pas déjà Hors projet)         : {equip_sortent}")
    for c, n in par_cat:
        print(f"    · {c:<14}: {n}")
    print(f"lignes passées « Hors de ce projet » (2 scénarios) : {maj}")
    print(f"foncier public SANS équipement (drapeau)           : {foncier_sans_equip}")
    print(f"  dont bande A/B (gardées, drapeau)                : {foncier_sans_equip_ab}")
    print(f"île — bande A/B conservation  AVANT → APRÈS        : {ab_avant} → {ab_apres} "
          f"(− {ab_avant - ab_apres})")
    print(f"île — « Hors de ce projet » conservation APRÈS     : {hors_apres}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "q_v20")
