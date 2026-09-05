"""CIRCUIT-2 lot 1.6 — moteur `commune_compteurs` : les compteurs et parts de la MAILLE COMMUNE,
extraits des endpoints (comparateur, fiche commune, modules, app). Un robinet ne calcule pas :
il appelle ici. Chaque fonction porte l'id (ou les ids) du registre qu'elle produit.

Les données de ce moteur dont le producteur est DÉJÀ une fonction nommée dédiée restent chez
leur producteur (délégation, une seule vérité — pas de copie ici) : `zan_reste_ha`
(api/rarete.py:compute_rarete) et `n_procedures_plu` (veille_plu.communes_en_procedure).
"""
from __future__ import annotations

from sqlalchemy import text

# ── comparateur des 24 communes (extraction de api/comparateur.py) ──────────────────────────────

# Indicateur → (libellé, direction, poids par défaut, source, nature).
# direction +1 = plus haut « mieux pour investir » ; -1 = plus bas mieux (on inverse à la normalisation).
# NB communes-tableau : `prix_ancien` est une COLONNE d'affichage (pas un axe composite) — hors INDICATEURS.
INDICATEURS = {
    "stock":     ("Stock d'opportunités (brûlantes + chaudes)", +1, 0.30, "run servi", "Sourcé"),
    "velocite":  ("Vélocité admin (délai médian dépôt→autorisation, mois)", -1, 0.15, "m10 / SITADEL", "Sourcé"),
    "permis":    ("Dynamisme permis (SITADEL, 5 ans)", +1, 0.15, "SITADEL", "Sourcé"),
    "deficit_sru": ("Déficit SRU (objectif − taux LLS, points)", +1, 0.15, "DHUP", "Sourcé"),
    "pression_zan": ("Pression ZAN (ENAF consommé 2021-2024, ha)", -1, 0.10, "Cerema", "Sourcé"),
    "prix_neuf": ("Prix de sortie neuf VEFA (DVF, €/m²)", +1, 0.15, "DVF", "Sourcé"),
}

_SQL_INDICATEURS = """
WITH base AS (SELECT DISTINCT left(idu, 5) AS insee, commune FROM parcels),
stock AS (
  SELECT left(s.parcelle_id, 5) AS insee,
         count(*) FILTER (WHERE s.tier IN ('brulante', 'chaude')) AS n
  FROM parcel_p_score_v2 s WHERE s.run_id = :run GROUP BY 1),
velo AS (
  SELECT commune, percentile_cont(0.5) WITHIN GROUP (ORDER BY delai_mois) AS mois, count(*) AS n
  FROM m10_permit_delais WHERE valide AND famille = 'logements' AND delai_mois >= 0 GROUP BY 1),
permis AS (
  SELECT commune, count(*) AS n FROM sitadel_permits
  WHERE date >= (CURRENT_DATE - INTERVAL '5 years') GROUP BY 1),
sru AS (SELECT insee, greatest(objectif_pct - taux_lls, 0) AS deficit, statut FROM commune_contexte_sru),
zan AS (SELECT insee, conso_2021_2024_m2 / 10000.0 AS ha FROM commune_conso_enaf)
-- €/m² ANCIEN : SOURCE UNIQUE `prix_ancien_communes` (moteurs), mappée en Python (cf. _compute) —
-- plus de CTE recopiée : le tableau Communes et le PDF baromètre lisent la MÊME fonction (§1b).
-- RETOURS-11F M1 : le NEUF (prix_neuf) ne vient PLUS de `dvf_prix_sortie_neuf` (précalcul divergent —
-- mesuré Saint-Paul 97415 : précalc 4 730 vs live 5 003) mais du MÊME moteur live `neuf_vefa_commune`
-- que la fiche et la carte, calculé en Python dans `raw_rows` (fiche = table = carte, à l'euro près).
SELECT b.insee, b.commune,
       stock.n AS stock, velo.mois AS velocite, velo.n AS velocite_n, permis.n AS permis,
       sru.deficit AS deficit_sru, sru.statut AS sru_statut,
       zan.ha AS pression_zan
FROM base b
LEFT JOIN stock ON stock.insee = b.insee
LEFT JOIN velo ON velo.commune = b.commune
LEFT JOIN permis ON permis.commune = b.commune
LEFT JOIN sru ON sru.insee = b.insee
LEFT JOIN zan ON zan.insee = b.insee
ORDER BY b.commune;
"""


def indicateurs_communes(db, run: str | None) -> list[dict]:
    """velocite_delai_median_mois · permis_5a_n (+ socle stock/SRU/ZAN du comparateur) — les
    indicateurs bruts par commune, en UNE requête (extraction du `_SQL` d'api/comparateur.py)."""
    return [dict(r) for r in db.execute(text(_SQL_INDICATEURS), {"run": run}).mappings().all()]


def composite_communes(rows: list[dict], poids: dict) -> list[dict]:
    """comparateur_composite — normalise chaque indicateur min-max [0-100] selon sa direction ;
    composite = moyenne pondérée des axes PRÉSENTS (renormalisation des poids présents pour ne pas
    pénaliser une donnée manquante). Extraction de `_normalize` (api/comparateur.py)."""
    keys = list(INDICATEURS)
    bornes = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        bornes[k] = (min(vals), max(vals)) if vals else (None, None)
    for r in rows:
        norm, wsum, wtot = {}, 0.0, 0.0
        for k in keys:
            direction = INDICATEURS[k][1]
            lo, hi = bornes[k]
            v = r.get(k)
            if v is None or lo is None or hi == lo:
                norm[k] = None if v is None else 50.0   # borne dégénérée → neutre
            else:
                frac = (v - lo) / (hi - lo)
                norm[k] = round((frac if direction > 0 else 1 - frac) * 100, 1)
            w = poids.get(k, 0.0)
            wtot += w
            if norm[k] is not None:
                wsum += w * norm[k]
                # cumul du poids réellement appliqué (axes présents)
        present_w = sum(poids.get(k, 0.0) for k in keys if norm[k] is not None)
        r["normalise"] = norm
        r["score_composite"] = round(wsum / present_w, 1) if present_w > 0 else None
    rows.sort(key=lambda r: (r["score_composite"] is not None, r["score_composite"] or 0), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rang"] = i
    return rows


# ── le foncier de la commune (extraction de api/app.py:_foncier_commune) ────────────────────────

def compte_parcelles_commune(db, commune: str) -> int:
    """n_parcelles_commune — count parcels par commune."""
    return int(db.execute(text("SELECT count(*) FROM parcels WHERE commune = :c"),
                          {"c": commune}).scalar() or 0)


def mutations_12m(db, commune: str) -> int:
    """mutations_12m_n — count dvf_mutations sur les 12 derniers mois DE DONNÉES de la commune
    (pas calendaire : DVF est publié avec retard, une fenêtre calendaire serait trompeuse)."""
    return int(db.execute(text(
        "SELECT count(*) FROM dvf_mutations WHERE commune = :c AND date_mutation > "
        "(SELECT max(date_mutation) FROM dvf_mutations WHERE commune = :c) - interval '12 months'"),
        {"c": commune}).scalar() or 0)


# ── risques & population (extraction de api/fiche_commune.py) ───────────────────────────────────

def pct_parcelles_couche(db, commune: str, kind: str, total_parcelles: int) -> float | None:
    """ppr_pct (et mouvement_terrain_pct) — part des parcelles de la commune intersectant la
    couche `kind` de spatial_layers, sur le total FOURNI (calculé une fois par l'appelant)."""
    if not total_parcelles:
        return None
    n = db.execute(text(
        "SELECT count(DISTINCT p.idu) FROM parcels p JOIN spatial_layers sl ON sl.kind = :k "
        "AND ST_Intersects(p.geom_2975, sl.geom_2975) WHERE p.commune = :c"),
        {"k": kind, "c": commune}).scalar() or 0
    return round(100.0 * n / total_parcelles, 1)


def vacance_pct(logements: int | None, vacants: int | None) -> float | None:
    """vacance_pct — 100 × vacants / logements (INSEE RP) ; None si le dénominateur manque."""
    return round(100.0 * vacants / logements, 1) if (logements and vacants is not None) else None


# ── contexte commune (extraction de api/app.py:_compute_commune_contexte) ───────────────────────

def qpv_commune(db, commune: str) -> list[dict]:
    """qpv_n — les QPV intersectant la commune (spatial_layers kind=qpv), nom + code."""
    return [dict(r) for r in db.execute(text(
        "SELECT name AS nom, attrs->>'code_qp' AS code FROM spatial_layers"
        " WHERE kind = 'qpv' AND commune = :c ORDER BY name"), {"c": commune}).mappings().all()]


def autres_loges_pct(locataires_pct: float, proprietaires_pct: float) -> float:
    """autres_loges_pct — 100 − locataires − propriétaires (INSEE RP), arrondi 0,1, plancher 0
    (CIRCUIT-1 lot 2.4 : calculé au SERVEUR, plus jamais au front)."""
    return max(0.0, round((100.0 - float(locataires_pct) - float(proprietaires_pct)) * 10) / 10)


# ── couverture des sources (extraction de api/app.py:sources_couverture) ────────────────────────

def couverture_sources(db) -> dict:
    """couverture_commune_pct — les chiffres de COUVERTURE qui parlent au client, LUS des données
    réelles (parcelles, communes couvertes/total, DVF, Radar, date du run servi). Chaque valeur est
    gardée : une table absente (base partielle) rend `null`, jamais un 500 ni un chiffre inventé."""
    def _scal(sql: str):
        try:
            return db.execute(text(sql)).scalar()
        except Exception:  # noqa: BLE001 — base partielle : la tuile dira « — », jamais un crash
            return None
    parcelles = _scal("SELECT count(*) FROM parcels")
    communes = _scal("SELECT count(DISTINCT commune) FROM parcels")
    dvf = _scal("SELECT count(*) FROM dvf_mutations")
    radar = _scal("SELECT count(*) FROM pige_biens")
    analyse_label, analyse_date = None, None
    try:
        from ... import runs as _runs
        analyse_label = _runs.current()
        if analyse_label:
            d = db.execute(text("SELECT computed_at FROM p_score_v2_runs WHERE run_id = :r"),
                           {"r": analyse_label}).scalar()
            analyse_date = d.isoformat() if d else None
    except Exception:  # noqa: BLE001
        pass
    return {
        "parcelles": int(parcelles) if parcelles is not None else None,
        "communes": int(communes) if communes is not None else None,
        "communes_total": 24,   # les 24 communes de La Réunion (constante du référentiel radar)
        "dvf_transactions": int(dvf) if dvf is not None else None,
        "radar_annonces": int(radar) if radar is not None else None,
        "analyse_label": analyse_label, "analyse_date": analyse_date,
    }


# ── corpus PLU (extraction de api/modules.py:plu_annuaire_communes) ─────────────────────────────

def etat_corpus_plu(db, millesimes: dict | None = None) -> dict:
    """n_extraits_plu · n_communes_rnu — état du corpus PLU par commune : SERVABLE (n extraits),
    RNU, révision non réconciliée, ou non ingéré ; compteurs calculés (jamais dérivés par
    soustraction). Réponse HONNÊTE (pas de trou masqué). Bloc entier extrait de l'endpoint —
    les invariants (somme des quatre statuts = n_communes) restent verrouillés par test."""
    from ...ingestion.plu_ingest import corpus_status
    from ... import veille_plu as V   # RETOURS-12 O4 — source UNIQUE des procédures (radar Sudocuh + registre)
    if millesimes is None:
        from ...api.modules import _plu_millesimes
        millesimes = _plu_millesimes()
    ing = corpus_status(db)
    _TYPE_PROC = {"revision_plu": "révision générale", "elaboration_plu": "élaboration", "modification_plu": "modification"}
    out = []
    for insee, c in sorted(millesimes.items()):
        e = ing.get(insee)
        if e:
            out.append({"insee": insee, "commune": c["commune"], "statut": "servable",
                        "idurba": e["idurba"], "millesime": e["millesime"], "extraits": e["extraits"],
                        "doutes": e["doutes"], "pagination_ambigue": e["pagination_ambigue"],
                        # M137-P — le « PLU intégral » = le pack officiel GPU (.zip) à télécharger ;
                        # aucun PDF n'est stocké en base. document = nom du règlement PDF dans le pack.
                        "source_url": e.get("source_url"), "document": e.get("documents")})
        elif c["statut"] == "rnu":
            out.append({"insee": insee, "commune": c["commune"], "statut": "rnu", "extraits": 0,
                        "message": "RNU (règlement national d'urbanisme) — pas de règlement communal."})
        elif c["statut"] == "opposabilite_en_attente":
            out.append({"insee": insee, "commune": c["commune"], "statut": "revision", "extraits": 0,
                        "idurba": c.get("idurba"),
                        "message": "Révision en cours — règlement non servi par le GPU, vérifier en "
                                   "mairie. Complétion automatique à l'approbation (veille trimestrielle "
                                   "M41). On ne sert pas un règlement non réconcilié (garde idurba+sha)."})
        else:
            out.append({"insee": insee, "commune": c["commune"], "statut": "non_ingere",
                        "idurba": c.get("idurba"), "extraits": 0,
                        "message": "Règlement non ingéré pour cette commune."})
    # OUTILS-1 A5 — le décompte par statut est CALCULÉ ici (source unique = statut réel de l'annuaire),
    # jamais dérivé par soustraction ni figé au front : le RNU (ABSENCE de PLU) n'est pas une procédure et
    # ne doit jamais être compté « en révision ». Si une commune passe en révision demain, le bandeau suit
    # seul. `n_revision` = procédure de révision non réconciliée ; `n_rnu` = RNU ; `n_non_ingere` = corpus
    # manquant. Somme des quatre = n_communes (invariant vérifié par test).
    # RETOURS-12 O4 — RÉCONCILIATION : le compteur « en révision » de l'annuaire et le registre des
    # procédures lisaient DEUX sources différentes (statut d'opposabilité GPU vs radar Sudocuh) → l'annuaire
    # disait « 2 en révision » et ratait Les Trois-Bassins (révision prescrite le 02/06/2022, servie par le
    # radar). Désormais les DEUX lisent `veille_plu` (source unique). On attache à chaque commune sa
    # procédure ACTIVE (le fait), distincte de la disponibilité du règlement (statut GPU, conservé).
    for c in out:
        e_vp = V.entry(c["insee"])
        if e_vp and V.procedure_active(e_vp) and e_vp["procedure"] in _TYPE_PROC:
            c["procedure_active"] = _TYPE_PROC[e_vp["procedure"]]
            c["procedure_date"] = e_vp.get("date_acte")
        else:
            c["procedure_active"] = None
    servables = sum(1 for c in out if c["statut"] == "servable")
    # `n_revision`/`n_rnu` restent la disponibilité du RÈGLEMENT (statut GPU) — inchangés (invariant test).
    n_revision = sum(1 for c in out if c["statut"] == "revision")
    n_rnu = sum(1 for c in out if c["statut"] == "rnu")
    n_non_ingere = sum(1 for c in out if c["statut"] == "non_ingere")
    # `procedures` = la LISTE réconciliée des procédures PLU en cours (radar Sudocuh), par état — la MÊME
    # source que l'outil « Vérif procédure » et la fiche. C'est ce que le bandeau doit afficher.
    procedures = {}
    for c in out:
        if c["procedure_active"]:
            procedures[c["procedure_active"]] = procedures.get(c["procedure_active"], 0) + 1
    n_procedures = sum(1 for c in out if c["procedure_active"])
    return {"n_communes": len(out), "servables": servables,
            "n_revision": n_revision, "n_rnu": n_rnu, "n_non_ingere": n_non_ingere,
            # RETOURS-12 O4 — compteur RÉCONCILIÉ des procédures (source unique veille_plu).
            "n_procedures": n_procedures, "procedures_par_etat": procedures,
            "communes": out}


# ── permis & point mort (extraction de api/modules.py) ──────────────────────────────────────────

def compte_permis_commune(db, commune: str | None, months: int, nature: str | None, dmax) -> dict:
    """permis_12m_n — count sitadel_permits de la commune sur la fenêtre (ancrée sur la FIN DES
    DONNÉES `dmax`, fournie par l'appelant), + le sous-compte géocodé. Rend {"n", "geo"}."""
    return db.execute(text(
        """SELECT count(*) AS n, count(*) FILTER (WHERE geom IS NOT NULL) AS geo
           FROM sitadel_permits
           WHERE (CAST(:c AS text) IS NULL OR commune = :c)
             AND (CAST(:nat AS text) IS NULL OR type = :nat)
             AND date >= :dmax - (:m || ' months')::interval"""),
        {"c": commune, "m": months, "nat": nature, "dmax": dmax}).mappings().first()


def permis_point_mort(db, commune: str | None, months: int, run: str | None) -> int:
    """point_mort_n — permis PC autorisés sans DAACT dans la fenêtre, sur parcelle toujours non
    bâtie au run servi (extraction du chemin count_only de modules.py:promesses)."""
    return int(db.execute(text("""
        SELECT count(DISTINCT s.id) FROM sitadel_permits s
        JOIN LATERAL jsonb_array_elements_text(s.idu_codes) AS c(idu) ON true
        JOIN parcels p ON p.idu = c.idu
        JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = :run
        WHERE s.type = 'PC' AND (CAST(:c AS text) IS NULL OR s.commune = :c)
          AND s.date < now() - (:m || ' months')::interval AND s.raw->>'daact' IS NULL
          AND NOT EXISTS (SELECT 1 FROM dryrun_cascade_results cr
                          WHERE cr.run_label = :run AND cr.parcel_id = p.id
                            AND cr.layer_name = 'bati' AND cr.result = 'HARD_EXCLUDE')"""),
        {"c": commune, "m": months, "run": run}).scalar() or 0)


# ── piscines (extraction de api/modules.py:prospection_piscines) ────────────────────────────────

def compte_piscines(db, commune: str | None, bati: str, piscine_surf_min: int,
                    inclure_incertaines: bool) -> dict:
    """n_piscines — agrégats de la détection piscines gelée (parcel_equipements) : total + par
    commune (décroissant), mêmes filtres que le listing (bâti, surface, confiance, corrections
    humaines exclues). Rend {"total", "communes"}."""
    from ...api.modules import SEUIL_PISCINE_HAUTE, _piscine_conf_filtre
    join_bati = "LEFT JOIN p_model_bati b ON b.idu = e.idu"
    bati_cond = " AND coalesce(b.emprise_bati_m2, 0) > 0" if bati == "oui" \
        else " AND coalesce(b.emprise_bati_m2, 0) = 0" if bati == "non" else ""
    surf_cond = " AND e.piscine_surface_m2 >= :psmin" if piscine_surf_min else ""
    conf_cond = _piscine_conf_filtre(inclure_incertaines)
    corr_cond = " AND NOT EXISTS (SELECT 1 FROM piscine_corrections pc WHERE pc.idu = e.idu)"
    where = ("WHERE e.piscine IS TRUE" + bati_cond + surf_cond + conf_cond + corr_cond
             + (" AND p.commune = :c" if commune else ""))
    params = {"c": commune, "psmin": piscine_surf_min, "cmin": SEUIL_PISCINE_HAUTE}
    total = int(db.execute(text(
        f"SELECT count(*) FROM parcel_equipements e JOIN parcels p ON p.idu = e.idu {join_bati} {where}"),
        params).scalar() or 0)
    communes = db.execute(text(f"""
        SELECT p.commune AS commune, count(*)::int AS n
        FROM parcel_equipements e JOIN parcels p ON p.idu = e.idu {join_bati} {where}
        GROUP BY p.commune ORDER BY n DESC"""), params).mappings().all()
    return {"total": total, "communes": [dict(c) for c in communes]}
