"""SOURCES-FIX-1 — LE point de calcul UNIQUE de la médiane €/m² BÂTI DVF sur un périmètre.

Clôt l'écart E1 de SOURCES-AUDIT-2 : l'Étude de zone (`zone.marche_zone`) lisait la table éclatée
`dvf_mutations_parcelle` (une mutation d'immeuble répétée sur N parcelles → artefact du « 100 888 €/m² »),
pendant que le bloc Marché de la fiche (`zone.prix_par_type_zone`) lisait la maille MUTATION
`dvf_mutations`. Deux tables, deux médianes possibles. Désormais les deux passent ICI :
même table (`dvf_mutations`), mêmes filtres, même borne, même fenêtre — une seule médiane à périmètre égal.

⚠ NE PAS confondre avec le BAROMÈTRE commune (`api.moteurs._BAROMETRE_RETENUE`, tout l'historique,
plancher €/m² lâche à 100) : c'est un AUTRE métrique, volontairement distinct (cf. moteurs.py:713-716).
Ici on sert le marché LIVE de zone : ventes bâties des 36 derniers mois, ratio borné anti-artefact.
"""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

#: paramètres du marché LIVE de zone — un critère, un endroit.
FENETRE_MOIS = 36
BORNE_EUR_M2 = (1000, 12000)   # ratio €/m² retenu (artefacts DVF écartés hors de cette plage)
def _seuil_mediane() -> int:
    # CHASSE-FIX-1 (C25) — seuil UNIQUE des médianes de référence (config dvf_profils.yaml,
    # seuils_effectif.mediane_generique) ; repli 8 si config absente. Plus jamais « 5 » en dur.
    try:
        from labuse.marche_service import seuil_effectif_local
        return seuil_effectif_local("mediane_generique", 8)
    except Exception:  # noqa: BLE001 — config indisponible : repli doctrine n≥8
        return 8
SEUIL_N = _seuil_mediane()     # CHASSE-FIX-1 (C25) : 8 (config), plus jamais 5 en dur


def mediane_bati(session: Session, *, geom_geojson: dict | None = None, commune: str | None = None,
                 type_local: str | None = None, fenetre_mois: int = FENETRE_MOIS,
                 seuil: int = SEUIL_N) -> dict:
    """Médiane €/m² BÂTI sur un périmètre (zone GeoJSON OU commune), 36 mois, ventes bâties (surface
    réelle bâtie ≥ 20 m²), ratio borné. Lit `dvf_mutations` (maille MUTATION). `type_local` filtre
    'Maison'/'Appartement' si fourni. Renvoie {median:int|None, n:int, periode:[MM/YYYY,MM/YYYY]|None} ;
    median=None sous le seuil. Contrat data-gap : table absente → tout à 0/None, jamais un 500."""
    if session.execute(text("SELECT to_regclass('dvf_mutations')")).scalar() is None:
        return {"median": None, "n": 0, "periode": None}
    params: dict = {"fen": fenetre_mois}
    if geom_geojson is not None:
        clause = "ST_Contains(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:zone), 4326), 2975), " \
                 "ST_Transform(dm.geom, 2975))"
        params["zone"] = json.dumps(geom_geojson)
    elif commune is not None:
        clause = "dm.commune = :c"
        params["c"] = commune
    else:
        raise ValueError("mediane_bati : préciser geom_geojson OU commune")
    tcond = ""
    if type_local:
        tcond = "AND dm.type_local = :t "
        params["t"] = type_local
    lo, hi = BORNE_EUR_M2
    r = session.execute(text(
        f"""WITH v AS (
              SELECT (dm.valeur_fonciere / NULLIF(dm.surface_reelle_bati, 0)) AS ratio,
                     dm.date_mutation AS d
              FROM dvf_mutations dm
              WHERE dm.geom IS NOT NULL AND dm.nature_mutation ILIKE 'vente%%'
                AND dm.valeur_fonciere > 0 AND coalesce(dm.surface_reelle_bati, 0) >= 20
                {tcond}
                AND dm.date_mutation >= (now() - make_interval(months => :fen))
                AND {clause})
           SELECT count(*) FILTER (WHERE ratio BETWEEN {lo} AND {hi}) AS n,
                  round(percentile_cont(0.5) WITHIN GROUP (ORDER BY ratio)
                        FILTER (WHERE ratio BETWEEN {lo} AND {hi})::numeric) AS med,
                  to_char(min(d), 'MM/YYYY') AS d0, to_char(max(d), 'MM/YYYY') AS d1
           FROM v"""), params).mappings().first()
    n = int(r["n"] or 0)
    return {"median": int(r["med"]) if (n >= seuil and r["med"] is not None) else None,
            "n": n, "periode": [r["d0"], r["d1"]] if n else None}
