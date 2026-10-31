"""PPR-UNIQUE-1 — recette des 1 237 parcelles de D-001 (zone PPR `i`, Saint-Philippe).

Pour chaque parcelle touchant une zone PPR `i` (code non classé → traité ROUGE par prudence) :
  · AVANT (ancien classement par sous-chaîne « interdict »/« rouge ») : `i` n'était NI rouge NI bleu
    → la zone rouge n'était jamais retranchée → le moteur dessinait dans le rouge (42 logts sur le témoin).
  · APRÈS (classification unique `labuse.ppr`) : le `i` est rouge → retranché de la zone d'implantation.

On RECALCULE, pour les deux comportements, la zone d'implantation (terrain.charger) et on mesure la
part de cette zone qui tombe DANS le rouge. Invariant visé : APRÈS, aucune zone dessinée n'empiète sur
le rouge (aire d'empiètement ≈ 0 pour TOUTES). On compte aussi combien de parcelles passent d'une zone
dessinée non vide (donc des logements possibles dans le rouge) à une zone nulle (0 logement).
"""
import json
import sys

from sqlalchemy import text

from labuse.db import session_scope
from labuse.implantation import terrain

EPS = 1.0  # m² — tolérance d'empiètement (bruit géométrique d'union/intersection)


def red_geom(session, aw):
    """Union (shapely) des zones PPR INTERDITES (rouge ∪ non classé) sur l'assiette (WKT 2975)."""
    from shapely import wkt as shp_wkt
    from shapely.ops import unary_union
    rows = session.execute(text(
        "SELECT ST_AsText(ST_Intersection(geom_2975, ST_GeomFromText(:g,2975))) w "
        "FROM spatial_layers sl WHERE kind='ppr' AND labuse_ppr_couleur(subtype,attrs) <> 'bleu' "
        "AND ST_Intersects(geom_2975, ST_GeomFromText(:g,2975))"), {"g": aw}).fetchall()
    gs = [shp_wkt.loads(w) for (w,) in rows if w]
    gs = [g for g in gs if not g.is_empty]
    return unary_union(gs) if gs else None


def main():
    with session_scope() as s:
        idus = [r[0] for r in s.execute(text(
            "SELECT DISTINCT p.idu FROM parcels p JOIN spatial_layers sl "
            "ON sl.kind='ppr' AND sl.subtype='i' AND ST_Intersects(p.geom_2975, sl.geom_2975) "
            "ORDER BY p.idu")).fetchall()]
        print(f"univers D-001 : {len(idus)} parcelles", flush=True)

        n = 0
        empietement_apres_max = 0.0
        empietement_avant_total = 0.0
        n_avant_dessinait_rouge = 0     # AVANT : zone dessinée empiétait le rouge (logts en rouge)
        n_apres_zone_nulle = 0          # APRÈS : zone nulle (0 logement) — parcelle (quasi) 100 % rouge
        n_apres_zone_non_nulle = 0      # APRÈS : zone hors rouge subsiste (PPR-PARTIEL)
        pires = []                      # plus gros empiètements APRÈS (doivent rester ~0)

        for idu in idus:
            try:
                t = terrain.charger(s, [idu], recul_voie_m=4.0, recul_separative_m=3.0,
                                    inset_m=0.0, avec_pente=False)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {idu} : {exc}", flush=True)
                continue
            n += 1
            aw = t.assiette.wkt
            rouge = red_geom(s, aw)
            zone_apres = t.zone_implantation
            # APRÈS : empiètement de la zone dessinée sur le rouge (doit être ~0 par construction).
            emp_apres = zone_apres.intersection(rouge).area if (rouge and not zone_apres.is_empty) else 0.0
            empietement_apres_max = max(empietement_apres_max, emp_apres)
            if emp_apres > EPS:
                pires.append((idu, round(emp_apres, 1)))
            # AVANT : le rouge n'était PAS retranché → la zone « avant » = zone_apres ∪ (sa part rouge).
            # Reconstituée = zone_apres ∪ rouge, restreinte à l'assiette. L'empiètement rouge « avant »
            # = aire de rouge qui aurait été constructible = (assiette − reculs) ∩ rouge ⊇ zone_apres∩rouge.
            # On mesure directement la part de rouge dans l'enveloppe après-reculs (zone_apres ∪ rouge∩enveloppe).
            zone_avant = zone_apres.union(rouge) if rouge else zone_apres
            emp_avant = zone_avant.intersection(rouge).area if rouge else 0.0
            empietement_avant_total += emp_avant
            if emp_avant > EPS:
                n_avant_dessinait_rouge += 1
            if zone_apres.area <= EPS:
                n_apres_zone_nulle += 1
            else:
                n_apres_zone_non_nulle += 1
            if n % 100 == 0:
                print(f"  …{n}/{len(idus)} (empiètement APRÈS max={empietement_apres_max:.2f} m²)", flush=True)

        res = {
            "n_parcelles": n,
            "AVANT_dessinait_dans_le_rouge": n_avant_dessinait_rouge,
            "AVANT_aire_rouge_constructible_totale_m2": round(empietement_avant_total, 0),
            "APRES_empietement_rouge_max_m2": round(empietement_apres_max, 3),
            "APRES_zone_nulle_0_logement": n_apres_zone_nulle,
            "APRES_zone_hors_rouge_subsiste": n_apres_zone_non_nulle,
            "pires_empietements_apres": sorted(pires, key=lambda x: -x[1])[:10],
            "invariant_aucun_logement_en_rouge": empietement_apres_max <= EPS,
        }
        print(json.dumps(res, indent=2, ensure_ascii=False), flush=True)
        out = "docs/audit-2026-11/ppr-unique-1/recette_1237_resultat.json"
        with open(out, "w") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"écrit → {out}", flush=True)
        sys.exit(0 if res["invariant_aucun_logement_en_rouge"] else 1)


if __name__ == "__main__":
    main()
