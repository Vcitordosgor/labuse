"""RECETTE-10 T11 — CE QUE LE SCORE APPORTE, MESURÉ sur le run servi (jamais recalculé).

Question de Vic : hors du tri par critères, que fait le modèle qu'un filtre ne ferait pas ? La réponse
est dans les chiffres : on regarde, sur les 12 derniers mois de ventes DVF, combien de parcelles de
CHAQUE palier ont effectivement muté (une vente DVF tombe dans leur géométrie), rapporté au taux de
mutation moyen — c'est le RAPPORT DE RISQUE réel du modèle AUJOURD'HUI. On le compare à ce qu'un filtre
évident (« terrain nu constructible en zone U ») obtiendrait sur la même période.

Lecture SEULE : on lit le run servi (`parcel_p_score_v2.tier`), les ventes DVF (`dvf_mutations`), les
zones (`parcel_zone_plu`) et l'emprise résiduelle (`parcel_residuel`). Aucun rescoring. Le lien
mutation↔parcelle est SPATIAL (la vente DVF est un point ; DVF 974 ne porte pas d'id parcelle).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: libellés client des tiers (mêmes paliers que la carte) — les codes techniques ne sortent pas.
PALIER_LABEL = {
    "brulante": "Priorité", "chaude": "À suivre", "reserve_fonciere": "Réserve foncière",
    "a_creuser": "Sans signal", "priorite": "Priorité", "a_suivre": "À suivre",
    "sans_signal": "Sans signal",
}
_VENTE = "d.date_mutation >= :cut AND d.nature_mutation ILIKE '%vente%'"


def mutation_lift(db: Session) -> dict:
    """Le backtest complet, servi tel quel. `base_pct` = taux de mutation moyen (toutes parcelles
    scorées) sur 12 mois ; `paliers` = par tier {n, mutees, taux_pct, lift} ; `filtres` = ce qu'un
    filtre simple obtiendrait. `lift` = taux du palier ÷ taux moyen (× combien de fois plus que le
    hasard). Fenêtre = 12 mois avant la vente DVF la plus récente."""
    from ..api.app import _score_v2_run_id
    v2 = _score_v2_run_id(db)
    fin = db.execute(text("SELECT max(date_mutation) FROM dvf_mutations")).scalar()
    cut = db.execute(text("SELECT max(date_mutation) - INTERVAL '12 months' FROM dvf_mutations")).scalar()
    tot = dict(db.execute(text(
        "SELECT tier, count(*) FROM parcel_p_score_v2 WHERE run_id=:v GROUP BY tier"), {"v": v2}).all())
    mut = dict(db.execute(text(f"""
        SELECT s.tier, count(DISTINCT p.idu)
        FROM dvf_mutations d
        JOIN parcels p ON ST_Contains(p.geom, d.geom)
        JOIN parcel_p_score_v2 s ON s.parcelle_id=p.idu AND s.run_id=:v
        WHERE {_VENTE} GROUP BY s.tier"""), {"v": v2, "cut": cut}).all())
    T = sum(tot.values()) or 1
    M = sum(mut.values())
    base = 100.0 * M / T
    paliers = []
    for tier, n in sorted(tot.items(), key=lambda kv: -((mut.get(kv[0], 0) / kv[1]) if kv[1] else 0)):
        m = mut.get(tier, 0)
        taux = 100.0 * m / n if n else 0.0
        paliers.append({"tier": tier, "label": PALIER_LABEL.get(tier, tier),
                        "n": n, "mutees": m, "taux_pct": round(taux, 3),
                        "lift": round(taux / base, 2) if base else None})

    #: jointures des filtres (zone PLU, résiduel, score V pour le type de propriétaire).
    _JOIN = ("JOIN parcel_zone_plu z ON z.idu=p.idu "
             "LEFT JOIN parcel_residuel r ON r.parcel_id=p.id "
             "LEFT JOIN parcel_v_score vs ON vs.parcelle_id=p.idu")

    def _filtre(where: str) -> dict:
        n = db.execute(text(f"SELECT count(*) FROM parcels p {_JOIN} WHERE {where}")).scalar() or 0
        m = db.execute(text(
            f"SELECT count(DISTINCT p.idu) FROM parcels p {_JOIN} "
            f"JOIN dvf_mutations d ON ST_Contains(p.geom,d.geom) AND {_VENTE} WHERE {where}"),
            {"cut": cut}).scalar() or 0
        taux = 100.0 * m / n if n else 0.0
        return {"n": n, "mutees": m, "taux_pct": round(taux, 3),
                "lift": round(taux / base, 2) if base else None}

    # RECETTE-10 (recette T11) — le filtre « terrain nu en zone U » PERDAIT contre le hasard (le foncier
    # nu se garde) : le comparer flattait le modèle. On garde donc un filtre RÉALISTE, celui qu'un
    # analyste tracerait vraiment : zone U + surface développable + propriétaire personne PHYSIQUE
    # (une PM optimise déjà) + pas de permis récent (pas déjà en chantier). C'est LUI le vrai
    # concurrent du modèle.
    _PP = "coalesce(vs.owner_type,'pp')='pp'"
    _PAS_PC = ("NOT EXISTS (SELECT 1 FROM p_model_permits pp WHERE pp.idu=p.idu AND pp.type='PC' "
               "AND pp.date_autorisation >= CURRENT_DATE - INTERVAL '60 months')")
    filtres = {
        "realiste": {"libelle": "Ciblage manuel réaliste : zone U, > 1 000 m², propriétaire particulier, "
                                "sans permis récent",
                     **_filtre(f"z.zone_fam='U' AND p.surface_m2>=1000 AND {_PP} AND {_PAS_PC}")},
        "realiste_400": {"libelle": "Idem, surface ≥ 400 m²",
                         **_filtre(f"z.zone_fam='U' AND p.surface_m2>=400 AND {_PP} AND {_PAS_PC}")},
        "terrain_nu_zone_u": {"libelle": "Terrain nu constructible en zone U (règle naïve)",
                              **_filtre("z.zone_fam='U' AND r.taux_emprise_pct IS NOT NULL "
                                        "AND r.taux_emprise_pct < 5")},
    }
    return {"run": v2, "fenetre_fin": (fin.date().isoformat() if fin else None),
            "base_pct": round(base, 3), "total_parcelles": T, "total_mutees": M,
            "paliers": paliers, "filtres": filtres}


def phrase_client(bt: dict) -> str | None:
    """Une phrase CHIFFRÉE, DATÉE et HONNÊTE pour le client (à côté du palier). On compare le palier
    « À suivre » (le seul dont l'échantillon est robuste) à un CIBLAGE MANUEL RÉALISTE — jamais à la
    règle naïve « terrain nu » qui perd contre le hasard (ce serait un homme de paille). None si le
    modèle ne bat pas nettement CE filtre-là (pas de fausse promesse ; jamais un score nu vanté)."""
    a_suivre = next((p for p in bt.get("paliers", []) if p["tier"] in ("chaude", "a_suivre")), None)
    filtre = bt.get("filtres", {}).get("realiste")
    if not a_suivre or not a_suivre.get("lift") or not filtre or not filtre.get("lift"):
        return None
    fl = filtre["lift"] or 0.0
    # le modèle doit battre le filtre RÉALISTE d'un facteur net (≥ 2×), sinon on n'affiche rien.
    if fl <= 0 or a_suivre["lift"] / fl < 2:
        return None
    fin = bt.get("fenetre_fin")
    fois = a_suivre["lift"] / fl
    return (f"Sur 12 mois de ventes DVF (au {fin}), les parcelles « {a_suivre['label']} » se sont vendues "
            f"{a_suivre['lift']:g}× plus que la moyenne — et {fois:.0f}× plus qu'un ciblage manuel réaliste "
            f"(zone U, > 1 000 m², propriétaire particulier, sans permis récent : {filtre['taux_pct']:g} %).")
