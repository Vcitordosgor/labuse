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


def _ecart_niveau(dn: int, an: int, seuil_ecart: int) -> str:
    """RADAR-FIX-3 — palier d'un écart demandé/acté selon le nombre d'ANNONCES demandées (le côté rare ;
    l'acté DVF est abondant) : « normal » ≥ seuil (30), « indicatif » de 5 à seuil−1, « insuffisant » < 5.
    Même règle partout (4 chiffres, tableau, barre par commune, bloc « Ce bien »). On exige aussi ≥ 5
    ventes actées, sinon la comparaison n'a pas de sens."""
    if dn < SEUIL_N or an < SEUIL_N:
        return "insuffisant"
    return "normal" if (dn >= seuil_ecart and an >= seuil_ecart) else "indicatif"

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
               -- RADAR-FIX-3 — « prix DEMANDÉS » = annonces EN VENTE (active/en_vente_longue) : le n de la
               -- médiane ne compte plus les retirées (leur ancien prix affiché n'est pas « demandé »
               -- aujourd'hui). Le n de la médiane = le n de « en vente » du même type (cohérence recette).
               percentile_cont(0.5) WITHIN GROUP (ORDER BY
                 CASE WHEN b.type_bien = 'terrain' THEN f.prix / NULLIF(f.surface_terrain,0)
                      ELSE f.prix / NULLIF(f.surface_hab,0) END)
                 FILTER (WHERE b.statut IN ('active','en_vente_longue') AND f.prix IS NOT NULL
                         AND ((b.type_bien='terrain' AND f.surface_terrain>0)
                           OR (b.type_bien IN ('maison','appartement','immeuble') AND f.surface_hab>0))) AS med_m2,
               count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue') AND f.prix IS NOT NULL
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
    les 4 chiffres MAISONS du haut = EXACTEMENT la ligne « maison » du tableau (même `_demande_acte`) ;
    l'écart par commune reste le moteur fiche commune (`raw_rows` → `prix_ancien`). L'ÉCART n'est servi
    qu'au-delà de `SEUIL_ECART` annonces (30), des DEUX côtés — sinon « sous le seuil »."""
    from ..api.comparateur import raw_rows
    from . import client
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

    # ── comptes par type (en vente, > 90 j, baisses 30 j) ──
    baisse_30j = ("EXISTS (SELECT 1 FROM pige_prix_historique h WHERE h.bien_id = b.bien_id "
                  "AND h.nouveau_prix < h.ancien_prix "
                  "AND h.date_constat >= (now() AT TIME ZONE 'Indian/Reunion')::date - 30)")
    crows = {r["type_bien"]: r for r in db.execute(text(f"""
        SELECT b.type_bien,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue'))          AS en_vente,
          -- RADAR-FIX-3 — « > 90 j » calculé sur la DATE de première publication (comme le badge de la
          -- liste), plus sur le statut `en_vente_longue` (jamais posé tant que le cycle ne tourne pas).
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue')
                           AND COALESCE(b.date_publication, b.date_premiere_saisie::date)
                               < (now() AT TIME ZONE 'Indian/Reunion')::date - 90) AS sup90,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue') AND {baisse_30j}) AS baisses30
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false AND {scope_where}
        GROUP BY b.type_bien"""), params).mappings()}

    def _demande_acte(t: str, comm: str | None = commune):
        """Demandé (Radar) et acté (DVF) d'un type, AU MÊME PÉRIMÈTRE partout : la médiane demandée du
        type (annonces EN VENTE) et sa référence DVF du même type. Un seul point de calcul → le tableau
        par type, les 4 chiffres du haut (maisons) ET la barre par commune disent la même chose (recette :
        cohérence). RADAR-FIX-3 — l'écart porte son PALIER (`_ecart_niveau`) : servi dès 5 annonces
        (indicatif de 5 à 29, normal ≥ 30) ; sous 5 → « sous le seuil »."""
        st = radar_stats(db, comm, t)["prix_m2_median_demande"]
        dv, dn = st.get("valeur"), int(st.get("n") or 0)
        # RADAR-2 (retouches 2) — l'acté DVF est servi POUR CHAQUE TYPE, île ET commune (le garde
        # `if commune` masquait « Toute l'île » → maisons « 0 vente ». `_dvf_*` acceptent commune=None).
        acte = _dvf_terrain(db, comm) if t == "terrain" else _dvf_bati_type(db, comm, t)
        av, an = acte.get("eur_m2"), int(acte.get("n") or 0)
        niveau = _ecart_niveau(dn, an, SEUIL_ECART)
        # écart CALCULÉ dès 5 annonces (indicatif) ; masqué seulement sous 5 (« insuffisant »).
        e = round(100.0 * (dv - av) / av, 1) if (dv and av and niveau != "insuffisant") else None
        return {"dv": dv, "dn": dn, "av": av, "an": an, "ecart": e, "niveau": niveau,
                "aperiode": acte.get("periode")}

    def _type_ligne(t: str) -> dict:
        m = _demande_acte(t)
        c = crows.get(t, {})
        return {"type": t, "en_vente": int(c.get("en_vente") or 0),
                "demande_eur_m2": round(float(m["dv"])) if m["dv"] else None,
                "acte_eur_m2": round(float(m["av"])) if m["av"] else None,
                "ecart_pct": m["ecart"], "ecart_niveau": m["niveau"],
                "ecart_sous_seuil": m["niveau"] == "insuffisant", "ecart_n": m["dn"],
                "sup_90j": int(c.get("sup90") or 0), "baisses_30j": int(c.get("baisses30") or 0)}

    par_type = [_type_ligne("terrain"), _type_ligne("maison"), _type_ligne("appartement")]
    # RADAR-2 (recette 4b) — les 4 chiffres du haut « maisons » = EXACTEMENT la ligne « maison » du tableau
    # (même appel `_demande_acte`), donc même prix acté, même écart, même palier. Plus de divergence.
    hm = _demande_acte("maison")
    dem_v, dem_n, acte_v, acte_n, ecart, ecart_niv = hm["dv"], hm["dn"], hm["av"], hm["an"], hm["ecart"], hm["niveau"]
    # RADAR-2 (recette 4a) — nombre canonique de biens en vente (= porte = liste), HORS appartements (copro).
    biens_en_vente = client.compter(db, commune)
    biens_sup_90j = client.compter(db, commune, sup90=True)

    # ── ce qui a bougé · 30 jours ──
    b30 = db.execute(text(f"""
        SELECT
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue')
                           AND b.date_premiere_saisie >= (now() AT TIME ZONE 'Indian/Reunion')::date - 30) AS nouvelles,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue') AND {baisse_30j})                AS baisses,
          -- RADAR-2 (recette 4c) — RETIRÉES = retraits CONFIRMÉS PAR L'OUVERTURE DU LIEN (radar_confirmation
          -- « supprimee » → event_log dedup 'pige:retiree:{id}'). RADAR-FIX-3 — on EXCLUT l'import initial
          -- « en bloc » : ne comptent que les retraits d'un PASSAGE QUOTIDIEN, càd datés APRÈS le jour de
          -- la toute première passe de confirmation (la passe de départ qui a soldé le corpus semé d'un
          -- coup). Sans passe de confirmation → rien de fiable à compter.
          count(*) FILTER (WHERE EXISTS (SELECT 1 FROM event_log e
                           WHERE e.dedup = :rp || b.bien_id AND e.ts >= now() - interval '30 days'
                             AND (e.ts AT TIME ZONE 'Indian/Reunion')::date
                                 > (SELECT min(captured_at AT TIME ZONE 'Indian/Reunion')::date
                                    FROM pige_passes WHERE passe = 'confirmation'))) AS retirees,
          count(*) FILTER (WHERE b.statut IN ('active','en_vente_longue')
                           AND b.last_seen_at >= now() - interval '30 days'
                           AND EXISTS (SELECT 1 FROM event_log e WHERE e.dedup = :ddp || b.bien_id || :dds)) AS de_retour
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false AND {scope_where}"""),
        {**params, "ddp": "pige:statut:", "dds": ":retiree", "rp": "pige:retiree:"}).mappings().first() or {}

    # ── écart demandé / acté par commune (MAISON contre MAISON, EXACTEMENT le calcul du tableau) ──
    # RADAR-FIX-3 — plus de bâti mélangé (maison+appartement+immeuble) opposé à un acté « tous types » :
    # une commune affiche ICI le MÊME écart que sa ligne « maison » du tableau (même `_demande_acte`).
    # Chaque barre porte son palier (normal/indicatif) ; sous 5 annonces maisons demandées → pas de barre.
    ecart_par_commune = []
    for c in by_commune:
        m = _demande_acte("maison", c)
        if m["ecart"] is not None:
            ecart_par_commune.append({"commune": c, "ecart_pct": m["ecart"], "niveau": m["niveau"],
                                      "n": m["dn"]})
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
        # `periode` = la VRAIE fenêtre des ventes retenues (année min–max), pas une fenêtre glissante.
        "prix_acte_median_eur_m2": {"valeur": round(float(acte_v)) if acte_v else None,
                                    "n": int(acte_n), "sous_seuil": acte_v is None,
                                    "periode": hm.get("aperiode")},
        "ecart_demande_acte_pct": ecart, "ecart_sous_seuil": ecart_niv == "insuffisant",
        "ecart_niveau": ecart_niv, "ecart_n": dem_n,
        "biens_en_vente": biens_en_vente, "biens_sup_90j": biens_sup_90j,
        "par_type": par_type,
        "bouge_30j": {"nouvelles": int(b30.get("nouvelles") or 0), "baisses": int(b30.get("baisses") or 0),
                      "retirees": int(b30.get("retirees") or 0), "de_retour": int(b30.get("de_retour") or 0)},
        "ecart_par_commune": ecart_par_commune,
        "seuil_ecart_n": SEUIL_ECART, "seuil_indicatif_n": SEUIL_N, "millesime_dvf": mill,
        "derniere_capture_at": capture.isoformat() if capture else None,
    }


def bien_vs_marche(db: Session, bien_id: int) -> dict | None:
    """RADAR-2 (recette) — CE BIEN FACE À SON MARCHÉ : son €/m² contre la médiane DEMANDÉE (Radar) et la
    médiane ACTÉE (DVF) de SA commune et de SON type (avec l'écart %), son ancienneté contre la médiane
    d'ancienneté de la commune (même type), et l'historique de ses prix. Réutilise les mêmes moteurs que
    le marché (`radar_stats`, `signaux._dvf_*`). Sous le seuil (30), chaque comparaison dit « sous le
    seuil ». None si le bien n'existe pas / n'est pas servi."""
    from .signaux import _dvf_bati_type, _dvf_terrain
    from ..pige.signaux import SEUIL_REF_TYPE as SEUIL_ECART
    r = db.execute(text("""
        SELECT b.bien_id, b.commune, b.type_bien, f.prix, f.surface_hab, f.surface_terrain,
               a.url_sortante, a.portail,
               ((now() AT TIME ZONE 'Indian/Reunion')::date
                - COALESCE(b.date_publication, b.date_premiere_saisie::date)) AS anciennete_j
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        LEFT JOIN LATERAL (SELECT url_sortante, portail FROM pige_annonces WHERE bien_id = b.bien_id
                           ORDER BY date_saisie DESC LIMIT 1) a ON true
        WHERE b.bien_id = :b AND f.valide_at IS NOT NULL AND b.est_copro = false"""),
        {"b": bien_id}).mappings().first()
    if not r:
        return None
    t, commune = r["type_bien"], r["commune"]
    surf = r["surface_terrain"] if t == "terrain" else (r["surface_hab"] or r["surface_terrain"])
    bien_m2 = round(float(r["prix"]) / float(surf)) if r["prix"] and surf and float(surf) > 0 else None

    dm = radar_stats(db, commune, t)["prix_m2_median_demande"]
    dem_v, dem_n = dm.get("valeur"), int(dm.get("n") or 0)
    acte = _dvf_terrain(db, commune) if t == "terrain" else _dvf_bati_type(db, commune, t)
    acte_v, acte_n = acte.get("eur_m2"), int(acte.get("n") or 0)

    def _cmp(ref, n):
        # RADAR-FIX-3 — même palier que le tableau : normal ≥ 30, indicatif 5–29, sous le seuil < 5.
        niveau = ("insuffisant" if (bien_m2 is None or not ref or n < SEUIL_N)
                  else "normal" if n >= SEUIL_ECART else "indicatif")
        return {"median": round(float(ref)) if ref else None, "n": int(n),
                "ecart_pct": round(100.0 * (bien_m2 - ref) / ref, 1) if niveau != "insuffisant" else None,
                "niveau": niveau, "sous_seuil": niveau == "insuffisant"}

    anc = db.execute(text("""
        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY
                 ((now() AT TIME ZONE 'Indian/Reunion')::date
                  - COALESCE(b.date_publication, b.date_premiere_saisie::date))) AS med,
               count(*) AS n
        FROM pige_biens b JOIN pige_faits f ON f.bien_id = b.bien_id
        WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false AND b.est_copro = false
          AND b.statut IN ('active','en_vente_longue') AND b.commune = :c AND b.type_bien = :t"""),
        {"c": commune, "t": t}).mappings().first() or {}
    anc_n = int(anc.get("n") or 0)
    hist = [{"date": h["date_constat"].isoformat() if h["date_constat"] else None,
             "ancien": h["ancien_prix"], "nouveau": h["nouveau_prix"]}
            for h in db.execute(text(
                "SELECT date_constat, ancien_prix, nouveau_prix FROM pige_prix_historique "
                "WHERE bien_id = :b ORDER BY date_constat, id"), {"b": bien_id}).mappings()]
    return {
        "bien_id": bien_id, "commune": commune, "type_bien": t, "prix": r["prix"], "eur_m2": bien_m2,
        "demande": _cmp(dem_v, dem_n), "acte": _cmp(acte_v, acte_n),
        "anciennete_j": int(r["anciennete_j"]) if r["anciennete_j"] is not None else None,
        "anciennete_mediane_j": round(float(anc["med"])) if anc.get("med") is not None and anc_n >= SEUIL_ECART else None,
        "anciennete_n": anc_n, "anciennete_sous_seuil": anc_n < SEUIL_ECART,
        "historique_prix": hist, "url_sortante": r["url_sortante"], "portail": r["portail"],
        "seuil_n": SEUIL_ECART,
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
