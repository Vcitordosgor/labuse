"""M42 — deux blocs de CONTEXTE fiche, jamais fusionnés (un promoteur ne les confond pas) :

1. « Sur cette parcelle » — HISTORIQUE des permis du SITE (inclut la parcelle) : ce qui a été
   déposé/autorisé/caduc ICI. Point de calcul unique `historique_permis`.
2. « Autour, à moins de 100 m » — VOISINAGE hyper-local (exclut le site) : ventes DVF + permis
   récents (36 mois) dans le buffer 100 m. Point de calcul unique `voisinage_proche`.

Doctrine : Sourcé Sitadel/DVF + millésime ; Sitadel est AUTORISATIONS-SEULES (M38) → jamais
« refusé » (on ne le sait pas), un caduc est DIT caduc. 0 tier, 0 verdict — contexte pur.
Parcelle sans matière → None (pas de bloc vide, doctrine M38). Perf : GIN(idu_codes) + geom_2975
indexée (scripts/m42_indexes.py) → ~17 ms/fiche.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# MANDAT_DVF-B — rayon/fenêtre du voisinage (profil voisinage_100m) LUS de config/dvf_profils.yaml : plus
# aucun rayon/fenêtre DVF en dur. Valeurs identiques (100 m / 36 mois) → golden stable ; repli si absente.
def _voisinage_cfg() -> tuple[int, int]:
    try:
        from ..marche_service import profil_meta
        m = profil_meta("voisinage_100m")
        return int(m["rayon_m"]), int(m["fenetre_mois"])
    except Exception:  # noqa: BLE001 — config absente = repli, jamais un crash
        return 100, 36


RAYON_M, FENETRE_MOIS = _voisinage_cfg()   # maille FIXE (M38 : libellé exact, contraste dense/rural)
SRC_SITADEL = "Sitadel (autorisations d'urbanisme, dépôts datés)"
SRC_DVF = "DVF / valeurs foncières (Etalab)"


def historique_permis(db: Session, idu: str) -> dict | None:
    """« Sur cette parcelle » : permis rattachés à l'IDU (idu_codes) + caducité (pc_caducs).
    Liste datée (type, dépôt, autorisation), un caduc DIT caduc. None si aucun permis ni caduc."""
    permis = [dict(r) for r in db.execute(text("""
        SELECT permit_id, type, date::date::text AS date_autorisation,
               date_depot::date::text AS date_depot
        FROM sitadel_permits
        WHERE idu_codes ? :idu
        ORDER BY COALESCE(date_depot, date) DESC
        LIMIT 20"""), {"idu": idu}).mappings().all()]
    caduc = db.execute(text("""
        SELECT pc_annee, caduc_depuis, statut_autorisation, statut_caducite, libelle_court, detail
        FROM pc_caducs WHERE idu = :idu"""), {"idu": idu}).mappings().first()
    if not permis and not caduc:
        return None
    return {
        "titre": "Sur cette parcelle",
        "permis": permis, "n_permis": len(permis),
        "caducite": (dict(caduc) if caduc else None),
        "source": SRC_SITADEL,
        "honnetete": "Autorisations et dépôts uniquement — refus et dossiers en cours non publiés.",
    }


def voisinage_proche(db: Session, idu: str) -> dict | None:
    """« Autour, à moins de 100 m » : ventes DVF + permis récents (36 mois) dans le buffer 100 m,
    la parcelle EXCLUE. Prix médian seulement si n≥3 (sinon « échantillon insuffisant »). None si
    aucune vente ni permis (pas de bloc vide)."""
    row = db.execute(text(f"""
        WITH a AS (SELECT geom_2975 AS g FROM parcels WHERE idu = :idu),
        since AS (SELECT (now() - interval '{FENETRE_MOIS} months')::date AS d)
        SELECT
          (SELECT count(*) FROM dvf_mutations_parcelle m JOIN parcels dp ON dp.idu = m.id_parcelle, a, since
            WHERE m.date_mutation >= since.d AND m.id_parcelle <> :idu
              AND ST_DWithin(a.g, dp.geom_2975, {RAYON_M})) AS n_dvf,
          (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY m.valeur_fonciere)
             FROM dvf_mutations_parcelle m JOIN parcels dp ON dp.idu = m.id_parcelle, a, since
            WHERE m.date_mutation >= since.d AND m.id_parcelle <> :idu AND m.valeur_fonciere > 0
              AND ST_DWithin(a.g, dp.geom_2975, {RAYON_M})) AS prix_median,
          (SELECT count(*) FROM sitadel_permits p, a, since
            WHERE p.geom_2975 IS NOT NULL AND COALESCE(p.date_depot, p.date) >= since.d
              AND NOT (p.idu_codes ? :idu) AND ST_DWithin(a.g, p.geom_2975, {RAYON_M})) AS n_permis
    """), {"idu": idu}).mappings().first()
    if not row or ((row["n_dvf"] or 0) == 0 and (row["n_permis"] or 0) == 0):
        return None
    n_dvf = row["n_dvf"] or 0
    # M103 P1 — le seuil du SIGNAL de voisinage est celui du profil voisinage_100m
    # (config/dvf_profils.yaml, n≥3 doctrine M38) — plus jamais écrit en dur ici.
    from ..marche_service import DVF_VOISINAGE_100M, profil_meta
    _seuil = int(profil_meta(DVF_VOISINAGE_100M).get("seuil_effectif") or 3)
    prix = round(row["prix_median"]) if (n_dvf >= _seuil and row["prix_median"]) else None
    return {
        "titre": f"Autour, à moins de {RAYON_M} m",
        "rayon_m": RAYON_M, "fenetre_mois": FENETRE_MOIS,
        "ventes_dvf": n_dvf,
        "prix_median_eur": prix,
        "prix_note": (None if prix is not None else "échantillon insuffisant (< 3 ventes)"),
        "permis": row["n_permis"] or 0,
        "source": f"{SRC_DVF} · {SRC_SITADEL}",
        "honnetete": "Ventes et autorisations publiées uniquement ; dossiers en cours non publiés.",
    }
