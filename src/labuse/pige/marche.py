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


# ─────────────────── RADAR-AUTO-1 (Lot E) — cœur radar_stats(commune, type) réutilisable ───────────────────
# UN seul calcul des chiffres Radar « prix DEMANDÉS » (jamais confondus avec l'acté DVF), servi à l'outil
# Communes ET à la fiche §Marché à côté du DVF. Les APPARTEMENTS sont INCLUS (la règle copro ne vaut que
# pour la carte / les digests / les veilles, cf. RADAR-AUDIT-1 §0.4). Un id de registre par chiffre.
_REG = {  # chiffre → id de registre (traçabilité, robinets)
    "actives_n": "annonces_actives_n",
    "prix_m2_median_demande": "prix_demande_median_eur_m2",
    "baisses_30j_pct": "radar_baisses_30j_pct",
    "delai_median_retrait_j": "delai_vente_median_j",
}


def radar_stats(db: Session, commune: str | None = None, type_bien: str | None = None) -> dict:
    """Chiffres Radar (prix DEMANDÉS) d'une commune (ou toute l'île si None) et d'un type (ou tous) :
    annonces actives, médiane €/m² demandé, part de baisses sur 30 j, délai médian de retrait. Mesures
    masquées sous SEUIL_N. Appartements INCLUS. Chaque chiffre porte son `n` et son `registre_id`."""
    where = ["f.valide_at IS NOT NULL", "b.a_qualifier = false"]
    params: dict = {}
    if commune:
        where.append("b.commune = :commune"); params["commune"] = commune
    if type_bien:
        where.append("b.type_bien = :type_bien"); params["type_bien"] = type_bien
    from .. import reglages
    excl = reglages.exclusion_depot_agence_sql("b")  # dépôt agence hors stats (comme marche.stats)
    w = " AND ".join(where) + excl
    row = db.execute(text(f"""
        SELECT count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue'))                 AS actives,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY
                 CASE WHEN b.type_bien = 'terrain' THEN f.prix / NULLIF(f.surface_terrain,0)
                      ELSE f.prix / NULLIF(f.surface_hab,0) END)
                 FILTER (WHERE f.prix IS NOT NULL
                         AND ((b.type_bien='terrain' AND f.surface_terrain>0)
                           OR (b.type_bien IN ('maison','appartement','immeuble') AND f.surface_hab>0))) AS med_m2,
               count(*) FILTER (WHERE f.prix IS NOT NULL
                         AND ((b.type_bien='terrain' AND f.surface_terrain>0)
                           OR (b.type_bien IN ('maison','appartement','immeuble') AND f.surface_hab>0)))   AS n_m2,
               count(DISTINCT b.bien_id) FILTER (WHERE b.statut IN ('active','en_vente_longue'))          AS n_ouvertes,
               count(DISTINCT ph.bien_id) FILTER (WHERE ph.nouveau_prix < ph.ancien_prix
                         AND ph.date_constat >= (now() AT TIME ZONE 'Indian/Reunion')::date - 30)         AS baisses_30j,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY
                 COALESCE(b.vendue_delai_j, (b.retiree_le::date - b.date_publication)))
                 FILTER (WHERE b.date_publication IS NOT NULL
                         AND (b.vendue_delai_j IS NOT NULL OR b.retiree_le IS NOT NULL))                  AS delai,
               count(*) FILTER (WHERE b.date_publication IS NOT NULL
                         AND (b.vendue_delai_j IS NOT NULL OR b.retiree_le IS NOT NULL))                  AS n_delai
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        LEFT JOIN pige_prix_historique ph ON ph.bien_id = b.bien_id
        WHERE {w}"""), params).mappings().first() or {}
    g = lambda k: int(row.get(k) or 0)
    ouvertes = g("n_ouvertes")
    def tag(cle, m):
        return {**m, "registre_id": _REG[cle]}
    return {
        "commune": commune, "type_bien": type_bien,
        "actives_n": tag("actives_n", {"valeur": g("actives"), "n": g("actives"), "insuffisant": False}),
        "prix_m2_median_demande": tag("prix_m2_median_demande", _mesure(row.get("med_m2"), g("n_m2"))),
        "baisses_30j_pct": tag("baisses_30j_pct",
            _mesure((100.0 * g("baisses_30j") / ouvertes) if ouvertes else None, ouvertes)),
        "delai_median_retrait_j": tag("delai_median_retrait_j", _mesure(row.get("delai"), g("n_delai"))),
        "libelle": "prix demandés (Radar)", "seuil_n": SEUIL_N,
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
