"""RADAR P6 · D3 — onglet « Marché » : statistiques agrégées par commune (24 + total île).

HONNÊTETÉ STATISTIQUE GRAVÉE : chaque chiffre porte son `n`. Toute mesure (médiane, taux, part) dont
`n < 5` est MASQUÉE (`valeur=null`, `insuffisant=true`) — pas de fausse précision, jamais une médiane
sur trois valeurs. Les COMPTES (annonces actives, nouvelles/30j…) restent des faits bruts. Au démarrage,
la plupart des cellules sont vides : c'est normal, c'est honnête, l'écran le DIT (le corpus se constitue).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingestion.run_all import REUNION_COMMUNES

SEUIL_N = 5   # sous ce n, une mesure statistique n'est pas servie (« échantillon insuffisant »)

_AGG = """
  count(*) FILTER (WHERE b.statut = 'active')                                         AS actives,
  count(*) FILTER (WHERE b.date_premiere_saisie AT TIME ZONE 'Indian/Reunion'
                        >= (now() AT TIME ZONE 'Indian/Reunion')::date - 30)          AS nouvelles_30j,
  count(*) FILTER (WHERE b.statut IN ('retiree','retiree_sans_vente')
                        AND b.retiree_le >= now() - interval '30 days')               AS retirees_30j,
  count(*) FILTER (WHERE b.statut = 'vendue'
                        AND b.vendue_le >= (now() AT TIME ZONE 'Indian/Reunion')::date - 90) AS vendues_90j,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY f.prix / f.surface_terrain)
    FILTER (WHERE b.type_bien = 'terrain' AND f.prix IS NOT NULL AND f.surface_terrain > 0) AS med_terrain,
  count(*) FILTER (WHERE b.type_bien = 'terrain' AND f.prix IS NOT NULL AND f.surface_terrain > 0) AS n_terrain,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY f.prix / f.surface_hab)
    FILTER (WHERE b.type_bien IN ('maison','appartement','immeuble') AND f.prix IS NOT NULL AND f.surface_hab > 0) AS med_bati,
  count(*) FILTER (WHERE b.type_bien IN ('maison','appartement','immeuble') AND f.prix IS NOT NULL AND f.surface_hab > 0) AS n_bati,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY COALESCE(b.vendue_delai_j, (b.retiree_le::date - b.date_publication)))
    FILTER (WHERE b.date_publication IS NOT NULL AND (b.vendue_delai_j IS NOT NULL OR b.retiree_le IS NOT NULL)) AS delai_med,
  count(*) FILTER (WHERE b.date_publication IS NOT NULL AND (b.vendue_delai_j IS NOT NULL OR b.retiree_le IS NOT NULL)) AS n_delai,
  count(*) FILTER (WHERE b.statut IN ('retiree','retiree_sans_vente','vendue'))       AS cloturees,
  count(*) FILTER (WHERE b.statut = 'retiree_sans_vente')                             AS echecs,
  count(*) FILTER (WHERE f.particulier_pro = 'particulier')                           AS particuliers,
  count(*) FILTER (WHERE f.particulier_pro IS NOT NULL)                               AS n_pp
"""
# RADAR-HTML (Lot 2/4) : les annonces À QUALIFIER (champs contradictoires) N'ENTRENT PAS dans les
# statistiques — jamais un fait faux dans une médiane.
_FROM = ("FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id "
         "WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false")
_SQL_COMMUNE = f"SELECT b.commune, {_AGG} {_FROM} GROUP BY b.commune"
_SQL_ILE = f"SELECT {_AGG} {_FROM}"


def _mesure(valeur, n: int) -> dict:
    """Une MESURE statistique : servie seulement si n ≥ SEUIL_N, sinon « échantillon insuffisant »."""
    ok = n is not None and n >= SEUIL_N and valeur is not None
    return {"valeur": round(float(valeur)) if ok else None, "n": int(n or 0), "insuffisant": not ok}


def _ligne(commune: str, r: dict | None) -> dict:
    r = r or {}
    g = lambda k: int(r.get(k) or 0)
    cloturees, echecs, n_pp, particuliers = g("cloturees"), g("echecs"), g("n_pp"), g("particuliers")
    return {
        "commune": commune,
        # COMPTES = faits bruts (toujours servis)
        "actives": g("actives"), "nouvelles_30j": g("nouvelles_30j"),
        "retirees_30j": g("retirees_30j"), "vendues_90j": g("vendues_90j"),
        # MESURES = masquées sous SEUIL_N
        "prix_m2_terrain": _mesure(r.get("med_terrain"), g("n_terrain")),
        "prix_m2_bati": _mesure(r.get("med_bati"), g("n_bati")),
        "delai_median_j": _mesure(r.get("delai_med"), g("n_delai")),
        "taux_echec_pct": _mesure((100.0 * echecs / cloturees) if cloturees else None, cloturees),
        "part_particuliers_pct": _mesure((100.0 * particuliers / n_pp) if n_pp else None, n_pp),
    }


def stats(db: Session) -> dict:
    """Les 24 communes (même vides) + le total ÎLE. Chaque mesure porte son n ; < 5 = insuffisant."""
    # CONNEXIONS-2 Lot 7 (#12/H5) — drapeau dépôt agence fermé ⇒ les dépôts agence sortent des STATS
    # servies (comme du flux client) : un test admin ne gonfle pas « N biens » d'une commune.
    from .. import reglages
    excl = reglages.exclusion_depot_agence_sql("b")
    sql_commune = _SQL_COMMUNE.replace("GROUP BY b.commune", f"{excl} GROUP BY b.commune")
    par_commune = {row["commune"]: dict(row) for row in db.execute(text(sql_commune)).mappings()}
    communes = sorted(nom for _insee, nom in REUNION_COMMUNES)
    lignes = [_ligne(c, par_commune.get(c)) for c in communes]

    # total île : ré-agrégé sur TOUT le corpus (pas une somme des médianes — on recalcule les médianes).
    total_row = db.execute(text(_SQL_ILE + excl)).mappings().first()
    ile = _ligne("Toute l'île", dict(total_row) if total_row else None)

    corpus = sum(l["actives"] + l["retirees_30j"] + l["vendues_90j"] for l in lignes)
    return {"communes": lignes, "ile": ile, "seuil_n": SEUIL_N,
            "corpus_total": db.execute(text(
                "SELECT count(*) FROM pige_biens b JOIN pige_faits f ON f.bien_id=b.bien_id "
                f"WHERE f.valide_at IS NOT NULL{excl}")).scalar() or 0,
            "corpus_actif": corpus}
