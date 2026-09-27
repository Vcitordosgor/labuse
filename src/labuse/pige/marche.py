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


def tableau(db: Session, commune: str | None = None) -> dict:
    """RADAR-2 (Lot 3) — LE MARCHÉ (colonne de droite du Radar) pour une commune ou toute l'île. Rien de
    neuf n'est calculé : le prix ACTÉ vient du MÊME moteur que la fiche commune (baromètre DVF commune
    entière, `comparateur.raw_rows` → `prix_ancien`) pour les chiffres MAISONS et l'écart par commune ;
    les lignes du tableau par type réutilisent les référentiels DVF existants (`signaux._dvf_terrain` /
    `_dvf_bati_type`). L'ÉCART n'est servi qu'au-delà de `SEUIL_ECART` annonces (30) — sinon « sous le
    seuil » (même règle que la fiche commune)."""
    from statistics import median
    from ..api.comparateur import raw_rows
    from .signaux import _dvf_bati_type, _dvf_terrain
    from ..pige.signaux import SEUIL_REF_TYPE as SEUIL_ECART

    srows = stats(db)
    by_commune = {r["commune"]: r for r in srows["communes"]}
    acte_map = raw_rows(db)                      # {commune: {prix_ancien, prix_ancien_n, …}}, memo 1 h
    scope_where = "b.commune = :c" if commune else "TRUE"
    params: dict = {"c": commune} if commune else {}

    def _chiffre(valeur, n) -> dict:
        return {"valeur": round(float(valeur)) if valeur is not None else None,
                "n": int(n or 0), "sous_seuil": (n or 0) < SEUIL_ECART}

    # ── chiffres MAISONS (le moteur fiche commune : demandé bâti robuste ≥ 30 vs acté baromètre) ──
    if commune:
        row = by_commune.get(commune) or {}
        dem = row.get("prix_m2_bati") or {}
        dem_v, dem_n = dem.get("valeur"), int(dem.get("n") or 0)
        acte_cell = acte_map.get(commune) or {}
        acte_v, acte_n = acte_cell.get("prix_ancien"), int(acte_cell.get("prix_ancien_n") or 0)
    else:
        dem = srows["ile"].get("prix_m2_bati") or {}
        dem_v, dem_n = dem.get("valeur"), int(dem.get("n") or 0)
        actes = [float(v["prix_ancien"]) for v in acte_map.values() if v.get("prix_ancien")]
        acte_v = median(actes) if actes else None
        acte_n = sum(int(v.get("prix_ancien_n") or 0) for v in acte_map.values())
    robuste = dem_v is not None and dem_n >= SEUIL_ECART
    ecart = round(100.0 * (dem_v - acte_v) / acte_v, 1) if (robuste and acte_v) else None

    # ── comptes par type (en vente, > 90 j, baisses 30 j) ──
    baisse_30j = ("EXISTS (SELECT 1 FROM pige_prix_historique h WHERE h.bien_id = b.bien_id "
                  "AND h.nouveau_prix < h.ancien_prix "
                  "AND h.date_constat >= (now() AT TIME ZONE 'Indian/Reunion')::date - 30)")
    crows = {r["type_bien"]: r for r in db.execute(text(f"""
        SELECT b.type_bien,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue'))          AS en_vente,
          count(*) FILTER (WHERE b.statut = 'en_vente_longue')                      AS sup90,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue') AND {baisse_30j}) AS baisses30
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false AND {scope_where}
        GROUP BY b.type_bien"""), params).mappings()}

    def _type_ligne(t: str) -> dict:
        st = radar_stats(db, commune, t)["prix_m2_median_demande"]
        dv, dn = st.get("valeur"), int(st.get("n") or 0)
        av = None
        if commune:
            acte = _dvf_terrain(db, commune) if t == "terrain" else _dvf_bati_type(db, commune, t)
            av = acte.get("eur_m2")
        e, sous = None, True
        if commune and dv and av and dn >= SEUIL_ECART:
            e = round(100.0 * (dv - av) / av, 1); sous = False
        c = crows.get(t, {})
        return {"type": t, "en_vente": int(c.get("en_vente") or 0),
                "demande_eur_m2": round(float(dv)) if dv else None,
                "acte_eur_m2": round(float(av)) if av else None,
                "ecart_pct": e, "ecart_sous_seuil": sous,
                "sup_90j": int(c.get("sup90") or 0), "baisses_30j": int(c.get("baisses30") or 0)}

    par_type = [_type_ligne("terrain"), _type_ligne("maison"), _type_ligne("appartement")]
    biens_en_vente = sum(int((crows.get(t) or {}).get("en_vente") or 0) for t in crows)
    biens_sup_90j = sum(int((crows.get(t) or {}).get("sup90") or 0) for t in crows)

    # ── ce qui a bougé · 30 jours ──
    b30 = db.execute(text(f"""
        SELECT
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue')
                           AND b.date_premiere_saisie >= (now() AT TIME ZONE 'Indian/Reunion')::date - 30) AS nouvelles,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue') AND {baisse_30j})                AS baisses,
          count(*) FILTER (WHERE b.statut IN ('retiree','retiree_sans_vente')
                           AND b.retiree_le >= now() - interval '30 days')                                 AS retirees,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue')
                           AND b.last_seen_at >= now() - interval '30 days'
                           AND EXISTS (SELECT 1 FROM event_log e WHERE e.dedup = :ddp || b.bien_id || :dds)) AS de_retour
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false AND {scope_where}"""),
        {**params, "ddp": "pige:statut:", "dds": ":retiree"}).mappings().first() or {}

    # ── écart demandé / acté par commune (maisons = bâti, moteur fiche commune) ──
    ecart_par_commune = []
    for c, r in by_commune.items():
        d = (r.get("prix_m2_bati") or {})
        dvv, dvn = d.get("valeur"), int(d.get("n") or 0)
        av = (acte_map.get(c) or {}).get("prix_ancien")
        if dvv is not None and av and dvn >= SEUIL_ECART:
            ecart_par_commune.append({"commune": c, "ecart_pct": round(100.0 * (dvv - av) / av, 1)})
    ecart_par_commune.sort(key=lambda x: x["ecart_pct"], reverse=True)

    # millésime DVF (pied de colonne) — du moteur commune, sinon d'une commune représentative.
    from ..faisabilite.marche_commune import _dvf_millesime
    try:
        mill = _dvf_millesime(db, commune) if commune else None
    except Exception:  # noqa: BLE001
        mill = None
    capture = db.execute(text("SELECT max(captured_at) FROM pige_passes")).scalar()
    if capture is None:
        capture = db.execute(text("SELECT max(last_seen_at) FROM pige_biens")).scalar()

    return {
        "scope": commune or "Toute l'île", "commune": commune,
        "prix_demande_median_eur_m2": _chiffre(dem_v, dem_n),
        # l'acté DVF (baromètre commune) n'est pas gardé par le seuil Radar : il est servi dès qu'il existe.
        "prix_acte_median_eur_m2": {"valeur": round(float(acte_v)) if acte_v else None,
                                    "n": int(acte_n), "sous_seuil": acte_v is None},
        "ecart_demande_acte_pct": ecart, "ecart_sous_seuil": ecart is None,
        "biens_en_vente": biens_en_vente, "biens_sup_90j": biens_sup_90j,
        "par_type": par_type,
        "bouge_30j": {"nouvelles": int(b30.get("nouvelles") or 0), "baisses": int(b30.get("baisses") or 0),
                      "retirees": int(b30.get("retirees") or 0), "de_retour": int(b30.get("de_retour") or 0)},
        "ecart_par_commune": ecart_par_commune,
        "seuil_ecart_n": SEUIL_ECART, "millesime_dvf": mill,
        "derniere_capture_at": capture.isoformat() if capture else None,
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
