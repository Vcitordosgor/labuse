"""SQL as-of du dataset personne-période (parcelle × année) — cœur anti-leakage.

Convention temporelle UNIQUE, appliquée partout :
  - pour une année d'observation Y, les features n'utilisent QUE des événements
    strictement antérieurs au 01/01/Y (`date < make_date(Y,1,1)`) ;
  - le label n'utilise QUE les événements de [01/01/Y, 31/12/Y] ;
  - les fenêtres glissantes sont clampées au 01/01/2021 (début DVF disponible) et
    la couverture réelle est exposée via `window_coverage` (mois disponibles / 36).

Tables créées (toutes NOUVELLES, préfixe p_model_, jamais les tables de prod) :
  p_model_frame     — socle : 1 ligne par parcelle (IDU dédupliqué), secteur = left(idu,10)
  p_model_mut_l2    — événements L2 dédupliqués : 1 ligne par mutation × parcelle
  p_model_mut_all   — toutes natures (tenure uniquement)
  p_model_permits   — permis Sitadel explosés : 1 ligne par permis × parcelle
  p_model_bati      — emprise bâtie BD TOPO par parcelle (intersection exacte)
  p_model_static    — features statiques parcelle (millésime 2026, consigné au dictionnaire)
  p_model_dataset   — dataset final parcelle × année (features + label + méta)

Les tables sources existantes sont accédées en LECTURE SEULE.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: Années d'observation matérialisées. 2022 ne sert qu'à la sensibilité « train étendu »
#: (lot 1.4) ; 2026 n'a pas de label (scoring produit, lot 6).
YEARS = (2022, 2023, 2024, 2025, 2026)

#: Natures DVF du périmètre L2 (labels ET rotations). VEFA, échange, adjudication,
#: expropriation exclus.
L2_NATURES = "('Vente', 'Vente terrain à bâtir')"

#: Début de l'historique DVF réellement en base (millésimes 2014-2020 retirés par la DGFiP).
DVF_START = "DATE '2021-01-01'"

#: Seuil d'emprise BD TOPO (m²) en dessous duquel une parcelle est considérée nue
#: (tolère cabanons/artefacts de digitalisation).
NU_SEUIL_M2 = 20


def _exec(session: Session, sql: str) -> None:
    # Pas de commit ici : l'appelant décide (session_scope commite, les tests rollbackent).
    session.execute(text(sql))


def _has_table(session: Session, name: str) -> bool:
    return bool(session.execute(text(f"SELECT to_regclass('{name}') IS NOT NULL")).scalar())


def build_frame(session: Session) -> None:
    """Socle parcelles : mvt_parcels (le parc de référence, 431 663) si présente et
    non vide, sinon parcels (base de test)."""
    use_mvt = _has_table(session, "mvt_parcels") and bool(
        session.execute(text("SELECT EXISTS (SELECT 1 FROM mvt_parcels)")).scalar())
    if use_mvt:
        frame_src = """
            SELECT DISTINCT ON (m.idu) m.idu, p.id AS parcel_id,
                   coalesce(m.surface_m2, p.surface_m2) AS surface_m2, p.centroid
            FROM mvt_parcels m LEFT JOIN parcels p ON p.idu = m.idu
            ORDER BY m.idu, p.id"""
    else:
        frame_src = """
            SELECT DISTINCT ON (p.idu) p.idu, p.id AS parcel_id, p.surface_m2, p.centroid
            FROM parcels p ORDER BY p.idu, p.id"""
    _exec(session, f"""
        DROP TABLE IF EXISTS p_model_frame;
        CREATE TABLE p_model_frame AS
        SELECT idu, parcel_id, surface_m2, centroid,
               left(idu, 5)  AS commune,
               left(idu, 10) AS secteur
        FROM ({frame_src}) s;
        CREATE UNIQUE INDEX ON p_model_frame (idu);
        CREATE INDEX ON p_model_frame (secteur);
    """)


def build_mutations(session: Session) -> None:
    """Événements DVF dédupliqués.

    DVF+ livre 1 ligne par (mutation × parcelle × local) : la dédup se fait en deux
    temps — d'abord 1 ligne par mutation × parcelle (surface terrain = max, les lignes
    par local la répètent ; surfaces bâties sommées), puis agrégat par mutation pour
    le caractère nu/bâti et le prix au m² de la mutation ENTIÈRE (multi-parcelles).
    """
    _exec(session, f"""
        DROP TABLE IF EXISTS p_model_mut_l2;
        CREATE TABLE p_model_mut_l2 AS
        WITH par AS (
            SELECT id_mutation, id_parcelle AS idu,
                   min(date_mutation) AS date_mutation,
                   max(valeur_fonciere) AS valeur,
                   max(coalesce(surface_terrain, 0)) AS s_terrain,
                   sum(coalesce(surface_reelle_bati, 0)) AS s_bati
            FROM dvf_mutations_parcelle
            WHERE nature_mutation IN {L2_NATURES}
            GROUP BY 1, 2
        ), mut AS (
            SELECT id_mutation,
                   bool_or(s_bati > 0) AS bati,
                   max(valeur) AS valeur,
                   sum(s_terrain) AS mut_s_terrain,
                   sum(s_bati) AS mut_s_bati
            FROM par GROUP BY 1
        )
        SELECT p.idu, p.id_mutation, p.date_mutation,
               m.bati, m.valeur,
               CASE WHEN NOT m.bati AND m.mut_s_terrain > 0
                    THEN m.valeur / m.mut_s_terrain END AS pm2_terrain,
               CASE WHEN m.bati AND m.mut_s_bati > 0
                    THEN m.valeur / m.mut_s_bati END AS pm2_bati
        FROM par p JOIN mut m USING (id_mutation);
        CREATE INDEX ON p_model_mut_l2 (idu, date_mutation);
        CREATE INDEX ON p_model_mut_l2 (date_mutation);
    """)

    # Toutes natures : sert uniquement à la tenure (« dernière mutation avant 01/01/Y »).
    _exec(session, """
        DROP TABLE IF EXISTS p_model_mut_all;
        CREATE TABLE p_model_mut_all AS
        SELECT DISTINCT id_parcelle AS idu, date_mutation
        FROM dvf_mutations_parcelle;
        CREATE INDEX ON p_model_mut_all (idu, date_mutation);
    """)


def build_permits(session: Session) -> None:
    """Permis Sitadel explosés par parcelle. `date` = DATE_REELLE_AUTORISATION
    (connue à l'autorisation → utilisable as-of ; délai de publication ~1-3 mois
    consigné au dictionnaire)."""
    _exec(session, """
        DROP TABLE IF EXISTS p_model_permits;
        CREATE TABLE p_model_permits AS
        SELECT DISTINCT s.permit_id, c.idu, s.type, s.date::date AS date_autorisation
        FROM sitadel_permits s, jsonb_array_elements_text(s.idu_codes) c(idu);
        CREATE INDEX ON p_model_permits (idu, date_autorisation);
        CREATE INDEX ON p_model_permits (date_autorisation);
    """)


def build_bati(session: Session) -> None:
    """Emprise bâtie BD TOPO par parcelle : intersection exacte bâtiments × parcelle
    (EPSG:2975). Source du caractère nu/bâti et de la densité bâtie de secteur.
    Couche statique (millésime BD TOPO de l'ingestion) — consigné au dictionnaire."""
    if not _has_table(session, "spatial_layers"):
        _exec(session, """
            DROP TABLE IF EXISTS p_model_bati;
            CREATE TABLE p_model_bati (idu varchar PRIMARY KEY, emprise_bati_m2 float);
        """)
        return
    _exec(session, """
        DROP TABLE IF EXISTS p_model_bati;
        CREATE TABLE p_model_bati AS
        SELECT f.idu,
               sum(ST_Area(ST_Intersection(b.geom_2975, p.geom_2975))) AS emprise_bati_m2
        FROM p_model_frame f
        JOIN parcels p ON p.id = f.parcel_id
        JOIN spatial_layers b
          ON b.kind = 'batiment' AND b.geom_2975 && p.geom_2975
         AND ST_Intersects(b.geom_2975, p.geom_2975)
        GROUP BY f.idu;
        ALTER TABLE p_model_bati ADD PRIMARY KEY (idu);
    """)


def build_static(session: Session) -> None:
    """Features statiques parcelle — couches SANS axe temporel en base (millésime
    unique, celui de l'ingestion 2026). Risque de fuite faible, consigné feature par
    feature au dictionnaire. AUCUNE colonne issue de la matrice, de V, ni computed_at.

    `owner_type` (parcel_v_score) est embarqué comme MÉTA de ventilation d'évaluation
    (PM/PP/public/bailleur) — jamais comme feature (exclu des FEATURES à features.py).
    """
    opt = {t: _has_table(session, t)
           for t in ("parcel_terrain", "parcel_vegetation", "parcel_residuel",
                     "parcel_residuel_bati", "parcel_amenites", "ortho_detections",
                     "filosofi_carreaux_200m", "parcel_v_score", "spatial_layers")}

    # Couches polygonales : passage OBLIGATOIRE par ST_Subdivide (les zones PLU
    # A/N font parfois >100k sommets ; un point-dans-polygone brut y est CPU-bound,
    # constaté : >40 min — subdivisé : ~1-2 min pour tout le parc).
    if opt["spatial_layers"]:
        _exec(session, """
            DROP TABLE IF EXISTS p_model_layers_sub;
            CREATE TABLE p_model_layers_sub AS
            SELECT kind,
                   CASE WHEN kind = 'plu_gpu_zone' AND subtype IN ('AUc', 'AUs')
                        THEN 'AU' ELSE subtype END AS subtype,
                   ST_Subdivide(ST_MakeValid(geom), 64) AS geom
            FROM spatial_layers
            WHERE kind IN ('plu_gpu_zone', 'qpv', 'friche');
            CREATE INDEX ON p_model_layers_sub USING gist (geom);
            ANALYZE p_model_layers_sub;
        """)
        _exec(session, """
            DROP TABLE IF EXISTS p_model_geo;
            CREATE TABLE p_model_geo AS
            WITH zone AS (
                SELECT DISTINCT ON (f.idu) f.idu, s.subtype
                FROM p_model_frame f
                JOIN p_model_layers_sub s
                  ON s.kind = 'plu_gpu_zone' AND ST_Intersects(s.geom, f.centroid)
                ORDER BY f.idu, s.subtype
            ), qpv AS (
                SELECT DISTINCT f.idu FROM p_model_frame f
                JOIN p_model_layers_sub s
                  ON s.kind = 'qpv' AND ST_Intersects(s.geom, f.centroid)
            ), friche AS (
                SELECT DISTINCT f.idu FROM p_model_frame f
                JOIN p_model_layers_sub s
                  ON s.kind = 'friche' AND ST_Intersects(s.geom, f.centroid)
            )
            SELECT f.idu, z.subtype AS zone_plu,
                   (q.idu IS NOT NULL) AS qpv, (fr.idu IS NOT NULL) AS friche
            FROM p_model_frame f
            LEFT JOIN zone z ON z.idu = f.idu
            LEFT JOIN qpv q ON q.idu = f.idu
            LEFT JOIN friche fr ON fr.idu = f.idu;
            CREATE UNIQUE INDEX ON p_model_geo (idu);
        """)
    else:
        _exec(session, """
            DROP TABLE IF EXISTS p_model_geo;
            CREATE TABLE p_model_geo AS
            SELECT idu, NULL::text AS zone_plu, false AS qpv, false AS friche
            FROM p_model_frame;
        """)

    filo_join = ""
    filo_cols = ("NULL::float AS filo_snv_pp, NULL::float AS filo_pct_pauv, "
                 "NULL::float AS filo_pct_prop, NULL::float AS filo_dens_pop")
    if opt["filosofi_carreaux_200m"]:
        # carreaux 200 m = petits carrés → jointure set-based directe sur le point 2975
        _exec(session, """
            DROP TABLE IF EXISTS p_model_filo;
            CREATE TABLE p_model_filo AS
            SELECT DISTINCT ON (f.idu) f.idu,
                   fc.ind_snv / nullif(fc.ind, 0)  AS snv_pp,
                   fc.men_pauv / nullif(fc.men, 0) AS pct_pauv,
                   fc.men_prop / nullif(fc.men, 0) AS pct_prop,
                   fc.ind / 0.04                   AS dens_pop
            FROM p_model_frame f
            JOIN filosofi_carreaux_200m fc
              ON ST_Intersects(fc.geom, ST_Transform(f.centroid, 2975))
            ORDER BY f.idu;
            CREATE UNIQUE INDEX ON p_model_filo (idu);
        """)
        filo_join = "LEFT JOIN p_model_filo filo ON filo.idu = f.idu"
        filo_cols = ("filo.snv_pp AS filo_snv_pp, filo.pct_pauv AS filo_pct_pauv, "
                     "filo.pct_prop AS filo_pct_prop, filo.dens_pop AS filo_dens_pop")

    def left(table: str, cols: str, join: str, fallback: str) -> tuple[str, str]:
        return (join, cols) if opt[table] else ("", fallback)

    terr_j, terr_c = left("parcel_terrain", "pt.pente_moy_deg",
                          "LEFT JOIN parcel_terrain pt ON pt.idu = f.idu",
                          "NULL::real AS pente_moy_deg")
    veg_j, veg_c = left("parcel_vegetation", "pv.canopee_pct, pv.ndvi_moyen",
                        "LEFT JOIN parcel_vegetation pv ON pv.idu = f.idu",
                        "NULL::float AS canopee_pct, NULL::float AS ndvi_moyen")
    res_j, res_c = left("parcel_residuel",
                        "pr.pct_potentiel, pr.sous_densite, pr.sdp_residuelle_m2",
                        "LEFT JOIN parcel_residuel pr ON pr.parcel_id = f.parcel_id",
                        "NULL::int AS pct_potentiel, NULL::boolean AS sous_densite, "
                        "NULL::int AS sdp_residuelle_m2")
    am_j, am_c = left("parcel_amenites",
                      "am.dist_ecole_m, am.dist_sante_m, am.dist_commerce_m, am.dist_tcsp_m",
                      "LEFT JOIN parcel_amenites am ON am.parcel_id = f.parcel_id",
                      "NULL::float AS dist_ecole_m, NULL::float AS dist_sante_m, "
                      "NULL::float AS dist_commerce_m, NULL::float AS dist_tcsp_m")
    vsc_j, vsc_c = left("parcel_v_score", "vs.owner_type",
                        "LEFT JOIN parcel_v_score vs ON vs.parcelle_id = f.idu",
                        "NULL::text AS owner_type")

    zone_sql = "geo.zone_plu"
    qpv_sql = "geo.qpv"
    friche_sql = "geo.friche"

    pisc_sql = pv_sql = "false"
    if opt["ortho_detections"]:
        pisc_sql = """EXISTS (SELECT 1 FROM ortho_detections od
            WHERE od.idu = f.idu AND od.type = 'piscine'
              AND coalesce(od.validation, '') <> 'faux_positif')"""
        pv_sql = """EXISTS (SELECT 1 FROM ortho_detections od
            WHERE od.idu = f.idu AND od.type = 'pv'
              AND coalesce(od.validation, '') <> 'faux_positif')"""

    _exec(session, f"""
        DROP TABLE IF EXISTS p_model_static;
        CREATE TABLE p_model_static AS
        SELECT f.idu, f.commune, f.secteur, f.surface_m2,
               {zone_sql} AS zone_plu,
               ({qpv_sql}) AS qpv,
               ({friche_sql}) AS friche,
               {filo_cols},
               {terr_c}, {veg_c}, {res_c}, {am_c},
               coalesce(pb.emprise_bati_m2, 0) AS emprise_bati_m2,
               ({pisc_sql}) AS piscine,
               ({pv_sql}) AS pv_candidat,
               {vsc_c}
        FROM p_model_frame f
        LEFT JOIN p_model_geo geo ON geo.idu = f.idu
        LEFT JOIN p_model_bati pb ON pb.idu = f.idu
        {filo_join} {terr_j} {veg_j} {res_j} {am_j} {vsc_j};
        CREATE UNIQUE INDEX ON p_model_static (idu);
    """)


def build_dataset(session: Session, years: tuple[int, ...] = YEARS) -> None:
    """Assemble p_model_dataset : 1 ligne par parcelle × année.

    Bloc Z par (secteur, année) : comptes L2 36 mois nu/bâti (clampés à 2021,
    annualisés via mois_dispo), comptes bruts + stock exposés pour le shrinkage
    (fait en aval, features.py), médianes €/m² 36 mois et tendance (12 derniers
    mois vs le début de fenêtre), permis PC/PA 24 mois normalisés par le stock.
    Bloc D par (parcelle, année) : tenure DVF et ancienneté du dernier permis,
    en BINS PRESCRITS avec bin « inconnu »/« jamais » explicite.

    Le label vaut NULL pour toute année postérieure au dernier millésime DVF
    (année de scoring produit).
    """
    yrs = ", ".join(f"({y})" for y in years)
    _exec(session, f"""
        DROP TABLE IF EXISTS p_model_dataset;
        CREATE TABLE p_model_dataset AS
        WITH years(annee) AS (VALUES {yrs}),
        maxy AS (
            SELECT coalesce(extract(year FROM max(date_mutation))::int, 0) AS y
            FROM p_model_mut_l2
        ),
        stock AS (
            SELECT secteur, count(*)::float AS n_parcelles
            FROM p_model_frame GROUP BY 1
        ),
        win AS (
            SELECT annee,
                   make_date(annee, 1, 1)                            AS asof,
                   greatest(make_date(annee - 3, 1, 1), {DVF_START}) AS w36_start,
                   make_date(annee - 1, 1, 1)                        AS w12_start,
                   greatest(make_date(annee - 2, 1, 1), {DVF_START}) AS w24_start
            FROM years
        ),
        -- Z : événements L2 STRICTEMENT antérieurs au 01/01/Y, par secteur × année
        z_sect AS (
            SELECT f.secteur, w.annee,
                   count(DISTINCT m.id_mutation) FILTER (WHERE NOT m.bati) AS n_mut_nu_36m,
                   count(DISTINCT m.id_mutation) FILTER (WHERE m.bati)     AS n_mut_bati_36m,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY m.pm2_terrain)
                       FILTER (WHERE m.pm2_terrain IS NOT NULL)            AS med_pm2_terrain_36m,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY m.pm2_bati)
                       FILTER (WHERE m.pm2_bati IS NOT NULL)               AS med_pm2_bati_36m,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY m.pm2_bati)
                       FILTER (WHERE m.pm2_bati IS NOT NULL
                               AND m.date_mutation >= w.w12_start)         AS med_pm2_bati_12m,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY m.pm2_bati)
                       FILTER (WHERE m.pm2_bati IS NOT NULL
                               AND m.date_mutation < w.w12_start)          AS med_pm2_bati_avant
            FROM p_model_mut_l2 m
            JOIN p_model_frame f ON f.idu = m.idu
            CROSS JOIN win w
            WHERE m.date_mutation >= w.w36_start AND m.date_mutation < w.asof
            GROUP BY 1, 2
        ),
        z_perm AS (
            SELECT f.secteur, w.annee, count(DISTINCT pp.permit_id) AS n_permis_24m
            FROM p_model_permits pp
            JOIN p_model_frame f ON f.idu = pp.idu
            CROSS JOIN win w
            WHERE pp.type IN ('PC', 'PA')
              AND pp.date_autorisation >= w.w24_start AND pp.date_autorisation < w.asof
            GROUP BY 1, 2
        ),
        d_tenure AS (
            SELECT ma.idu, w.annee, max(ma.date_mutation) AS derniere_mutation
            FROM p_model_mut_all ma
            CROSS JOIN win w
            WHERE ma.date_mutation < w.asof
            GROUP BY 1, 2
        ),
        d_permit AS (
            SELECT pp.idu, w.annee, max(pp.date_autorisation) AS dernier_permis
            FROM p_model_permits pp
            CROSS JOIN win w
            WHERE pp.date_autorisation < w.asof
            GROUP BY 1, 2
        ),
        dens AS (
            SELECT f.secteur,
                   sum(coalesce(st.emprise_bati_m2, 0)) / nullif(sum(f.surface_m2), 0) AS dens_bati_secteur,
                   avg((coalesce(st.emprise_bati_m2, 0) > {NU_SEUIL_M2})::int)::float  AS pct_bati_secteur
            FROM p_model_frame f JOIN p_model_static st ON st.idu = f.idu
            GROUP BY 1
        )
        SELECT
            f.idu, w.annee,
            -- ===== label : mutation L2 dans [01/01/Y, 31/12/Y] =====
            CASE WHEN w.annee <= (SELECT y FROM maxy) THEN
                 (EXISTS (SELECT 1 FROM p_model_mut_l2 mu
                          WHERE mu.idu = f.idu
                            AND mu.date_mutation >= w.asof
                            AND mu.date_mutation < make_date(w.annee + 1, 1, 1)))::int
            END AS label,
            -- ===== méta (JAMAIS features) =====
            f.commune, f.secteur, st.owner_type,
            -- ===== bloc Z =====
            least((w.asof - w.w36_start) / 30.44, 36.0) / 36.0                  AS window_coverage,
            coalesce(zs.n_mut_nu_36m, 0)                                        AS n_mut_nu_36m,
            coalesce(zs.n_mut_bati_36m, 0)                                      AS n_mut_bati_36m,
            sk.n_parcelles                                                      AS stock_secteur,
            coalesce(zs.n_mut_nu_36m, 0)   / sk.n_parcelles
                / ((w.asof - w.w36_start) / 30.44) * 12                         AS rot_nu_brute,
            coalesce(zs.n_mut_bati_36m, 0) / sk.n_parcelles
                / ((w.asof - w.w36_start) / 30.44) * 12                         AS rot_bati_brute,
            zs.med_pm2_terrain_36m, zs.med_pm2_bati_36m,
            CASE WHEN zs.med_pm2_bati_avant > 0
                 THEN zs.med_pm2_bati_12m / zs.med_pm2_bati_avant - 1 END       AS tendance_pm2_bati,
            coalesce(zp.n_permis_24m, 0) / sk.n_parcelles                       AS permis_24m_norm,
            dn.dens_bati_secteur, dn.pct_bati_secteur,
            st.filo_snv_pp, st.filo_pct_pauv, st.filo_pct_prop, st.filo_dens_pop,
            st.qpv, st.pente_moy_deg,
            st.dist_ecole_m, st.dist_sante_m, st.dist_commerce_m, st.dist_tcsp_m,
            coalesce(st.zone_plu, 'inconnu')                                    AS zone_plu,
            -- ===== bloc D =====
            (st.emprise_bati_m2 <= {NU_SEUIL_M2})                               AS nu,
            (st.emprise_bati_m2 <= {NU_SEUIL_M2}
             AND coalesce(st.zone_plu, '') IN ('U', 'AU'))                      AS nu_constructible,
            f.surface_m2,
            st.emprise_bati_m2,
            st.pct_potentiel, st.sous_densite, st.sdp_residuelle_m2,
            CASE
                WHEN dt.derniere_mutation IS NULL THEN 'inconnu'
                WHEN dt.derniere_mutation >= w.asof - INTERVAL '1 year'  THEN '<1'
                WHEN dt.derniere_mutation >= w.asof - INTERVAL '2 years' THEN '1-2'
                WHEN dt.derniere_mutation >= w.asof - INTERVAL '3 years' THEN '2-3'
                ELSE '3+'
            END                                                                 AS tenure_bin,
            CASE
                WHEN dp.dernier_permis IS NULL THEN 'jamais'
                WHEN dp.dernier_permis >= w.asof - INTERVAL '2 years'  THEN '<2a'
                WHEN dp.dernier_permis >= w.asof - INTERVAL '5 years'  THEN '2-5a'
                WHEN dp.dernier_permis >= w.asof - INTERVAL '10 years' THEN '5-10a'
                ELSE '10a+'
            END                                                                 AS permis_bin,
            st.canopee_pct, st.ndvi_moyen, st.friche, st.piscine, st.pv_candidat
        FROM p_model_frame f
        CROSS JOIN win w
        JOIN stock sk ON sk.secteur = f.secteur
        JOIN p_model_static st ON st.idu = f.idu
        LEFT JOIN z_sect zs ON zs.secteur = f.secteur AND zs.annee = w.annee
        LEFT JOIN z_perm zp ON zp.secteur = f.secteur AND zp.annee = w.annee
        LEFT JOIN d_tenure dt ON dt.idu = f.idu AND dt.annee = w.annee
        LEFT JOIN d_permit dp ON dp.idu = f.idu AND dp.annee = w.annee
        LEFT JOIN dens dn ON dn.secteur = f.secteur;
        CREATE UNIQUE INDEX ON p_model_dataset (idu, annee);
        CREATE INDEX ON p_model_dataset (annee);
    """)


def build_all(session: Session, years: tuple[int, ...] = YEARS) -> None:
    build_frame(session)
    build_mutations(session)
    build_permits(session)
    build_bati(session)
    build_static(session)
    build_dataset(session, years)
