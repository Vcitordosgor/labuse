"""OUTIL-COMMUNES-FIX-5 (1) — PREUVE terrain nu REFAITE AVEC LA FONCTION SERVIE.

Le tableau FIX-4 (`communes_fix4_terrain_preuve.py`) appliquait un filtre `BETWEEN 50 AND 4000 €/m²`
que la fonction servie au tableau (`faisabilite/marche_commune.py::ligne2_terrain_zone`) N'APPLIQUE
PAS : ses médianes/effectifs divergeaient donc de l'écran (relecture-communes-3 §2).

Ici :
  · colonne APRÈS  = `ligne2_terrain_zone(db, commune)` — LA fonction servie, telle quelle (arrondie,
    seuil d'effectif appliqué) → ces chiffres SONT ceux de l'écran.
  · colonne AVANT  = la MÊME requête que `ligne2_terrain_zone`, mot pour mot, mais avec la qualification
    d'AVANT FIX-4 (`ACTE_NU_AVANT` : bâti=0 seul, surface = plus grande ligne, sans filtre local ni
    multi-communes). Aucune borne €/m² ajoutée nulle part.
  · ligne de contrôle : pour les 3 témoins du rapport, APRÈS calculé ici == `ligne2_terrain_zone`
    servie (287·594 Saint-Denis U, 271·872 Saint-Paul U, 202·653 Le Tampon U).

Usage : PYTHONPATH=src python scripts/communes_fix5_terrain_preuve.py
Lecture seule."""
from __future__ import annotations

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.marche_commune import SEUIL_TERRAIN_CELLULE_N, ligne2_terrain_zone
from labuse.marche_dvf_commune import ACTE_TERRAIN_NU_CTE

# Qualification d'AVANT FIX-4 : bâti=0 sur l'acte, surface = plus grande ligne (max) par (mutation,
# parcelle), AUCUN filtre local, AUCUN filtre multi-communes.
ACTE_NU_AVANT = """acte_nu AS (
  SELECT id_mutation, sum(terr_p) AS terr_tot, max(val) AS val, max(mill) AS mill,
         min(d0) AS d0, max(d1) AS d1
  FROM (SELECT id_mutation, id_parcelle,
               max(COALESCE(surface_reelle_bati, 0)) AS bati_p,
               max(COALESCE(surface_terrain, 0))     AS terr_p,
               max(valeur_fonciere) AS val, max(millesime) AS mill,
               min(date_mutation) AS d0, max(date_mutation) AS d1
        FROM dvf_mutations_parcelle
        WHERE nature_mutation IN ('Vente', 'Vente terrain à bâtir')
        GROUP BY id_mutation, id_parcelle) pp
  GROUP BY id_mutation HAVING sum(bati_p) = 0 AND sum(terr_p) > 0)"""

# EXACTEMENT la requête de ligne2_terrain_zone (marche_commune.py), sans aucune borne ajoutée. Seul le
# CTE est paramétré (AVANT vs servi). On applique ensuite le MÊME traitement Python que la fonction :
# round(med) et seuil d'effectif SEUIL_TERRAIN_CELLULE_N.
_ZONE_SQL = """
WITH {cte},
zm AS (SELECT m.id_mutation, bool_or(z.zone_fam = 'U') AS has_u, bool_or(z.zone_fam = 'AU') AS has_au
       FROM dvf_mutations_parcelle m
       JOIN parcel_zone_plu z ON z.idu = m.id_parcelle AND z.zone_fam IN ('U','AU')
       WHERE m.code_commune = :insee AND m.nature_mutation IN ('Vente','Vente terrain à bâtir')
       GROUP BY m.id_mutation),
tot AS (SELECT a.val, a.terr_tot, zm.has_u, zm.has_au FROM acte_nu a JOIN zm USING (id_mutation))
SELECT 'U' AS zone_fam,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY val / NULLIF(terr_tot,0)) AS med,
       count(*) FILTER (WHERE val / NULLIF(terr_tot,0) IS NOT NULL) AS n
FROM tot WHERE has_u
UNION ALL
SELECT 'AU',
       percentile_cont(0.5) WITHIN GROUP (ORDER BY val / NULLIF(terr_tot,0)),
       count(*) FILTER (WHERE val / NULLIF(terr_tot,0) IS NOT NULL)
FROM tot WHERE has_au"""


def _zone(db, insee, cte):
    """Même logique que ligne2_terrain_zone : round(med) + cellule servie seulement si n >= seuil."""
    out = {}
    for r in db.execute(text(_ZONE_SQL.format(cte=cte)), {"insee": insee}).mappings().all():
        n = int(r["n"] or 0)
        servi = (n >= SEUIL_TERRAIN_CELLULE_N and r["med"] is not None)
        out[r["zone_fam"]] = (round(r["med"]) if servi else None, n, servi)
    return out


def _cell(t):
    med, n, servi = t
    return f"{med}·{n}" if servi else (f"(—·{n})" if med is None else f"{med}·{n}")


def main() -> None:
    with session_scope() as db:
        communes = [(r[0], r[1]) for r in db.execute(text(
            "SELECT insee, nom FROM communes_referentiel ORDER BY nom")).all()]
        print(f"seuil d'effectif cellule servie = {SEUIL_TERRAIN_CELLULE_N}  "
              "(APRÈS = ligne2_terrain_zone servie ; — = cellule sous le seuil, non servie)")
        print(f"{'Commune':24} | {'U avant':>12} | {'U servi':>12} | {'AU avant':>12} | {'AU servi':>12}")
        print("-" * 86)
        for insee, nom in communes:
            av = _zone(db, insee, ACTE_NU_AVANT)
            # APRÈS = la fonction SERVIE elle-même.
            pz = (ligne2_terrain_zone(db, nom).get("valeurs") or {}).get("par_zone") or {}

            def _srv(fam):
                c = pz.get(fam) or {}
                return (c.get("median_eur_m2"), int(c.get("n") or 0), bool(c.get("calculable")))
            au_u, au_au = av.get("U", (None, 0, False)), av.get("AU", (None, 0, False))
            sv_u, sv_au = _srv("U"), _srv("AU")
            flag = "  ←bouge" if (au_u[:2] != sv_u[:2] or au_au[:2] != sv_au[:2]) else ""
            print(f"{nom:24} | {_cell(au_u):>12} | {_cell(sv_u):>12} | "
                  f"{_cell(au_au):>12} | {_cell(sv_au):>12}{flag}")

        # ── contrôle : APRÈS (ligne2 servi) == cibles relecture-3 ──────────────────────────────
        print("\n=== CONTRÔLE : fonction servie == écran (relecture-3) ===")
        for nom, attendu in (("Saint-Denis", (287, 594)), ("Saint-Paul", (271, 872)), ("Le Tampon", (202, 653))):
            u = ((ligne2_terrain_zone(db, nom).get("valeurs") or {}).get("par_zone") or {}).get("U") or {}
            got = (u.get("median_eur_m2"), int(u.get("n") or 0))
            print(f"{nom} U : servi {got[0]}·{got[1]}  attendu {attendu[0]}·{attendu[1]}  "
                  f"{'OK' if got == attendu else 'ÉCART'}")


if __name__ == "__main__":
    main()
