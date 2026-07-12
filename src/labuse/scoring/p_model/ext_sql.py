"""M3.6 — SQL du flag copro (lot 0) et du label L2-F (lot 1).

Tables NOUVELLES préfixées p_model_ext_* uniquement ; tables M3 (p_model_*) et
prod en LECTURE SEULE.

Deux règles distinctes, volontairement :
  - FLAG COPRO (parcelle, lot 0.1) : RNIC (idu_codes + parcelle_idu) ∪ parcelles
    ayant ≥1 mutation L2 « exclusivement Appartement » (tous locaux non nuls dans
    {Appartement, Dépendance} et ≥1 Appartement, SANS plafond : une vente en bloc
    de 10 appartements signe aussi un immeuble collectif).
  - EXCLUSION L2-F (mutation, lot 1) : une mutation L2 est exclue ssi tous ses
    locaux non nuls ∈ {Appartement, Dépendance}, ≥1 Appartement ET ≤ 3 appartements
    — le plafond préserve les ventes d'IMMEUBLE ENTIER (conservées au mandat).
    Maison, terrain nu, local mixte, dépendance seule : conservés.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: Plafond d'appartements au-delà duquel une mutation exclusivement-appartements
#: est réputée « immeuble entier » (conservée dans L2-F).
IMMEUBLE_ENTIER_MIN_APP = 4

L2_NATURES = "('Vente', 'Vente terrain à bâtir')"


def _exec(session: Session, sql: str) -> None:
    session.execute(text(sql))


def build_copro_flags(session: Session, dvf_table: str = "dvf_mutations_parcelle") -> None:
    """p_model_ext_copro : 1 ligne par parcelle du frame M3, flags copro."""
    has_rnic = bool(session.execute(text(
        "SELECT to_regclass('rnic_coproprietes') IS NOT NULL")).scalar())
    rnic_sql = """
        SELECT DISTINCT c.idu
        FROM rnic_coproprietes r, jsonb_array_elements_text(coalesce(r.idu_codes, '[]')) c(idu)
        UNION
        SELECT r.parcelle_idu FROM rnic_coproprietes r WHERE r.parcelle_idu IS NOT NULL
    """ if has_rnic else "SELECT NULL::varchar AS idu WHERE false"
    _exec(session, f"""
        DROP TABLE IF EXISTS p_model_ext_copro;
        CREATE TABLE p_model_ext_copro AS
        WITH rnic AS ({rnic_sql}),
        unit AS (
            SELECT id_mutation, id_parcelle AS idu,
                   coalesce(bool_and(type_local IN ('Appartement', 'Dépendance'))
                            FILTER (WHERE type_local IS NOT NULL), false) AS only_app_dep,
                   bool_or(type_local = 'Appartement')                     AS has_app
            FROM {dvf_table}
            WHERE nature_mutation IN {L2_NATURES}
            GROUP BY 1, 2
        )
        SELECT f.idu,
               EXISTS (SELECT 1 FROM rnic r WHERE r.idu = f.idu)          AS copro_rnic,
               EXISTS (SELECT 1 FROM unit u
                       WHERE u.idu = f.idu AND u.only_app_dep AND u.has_app) AS copro_dvf
        FROM p_model_frame f;
        ALTER TABLE p_model_ext_copro ADD PRIMARY KEY (idu);
    """)
    session.commit()


def l2f_mutation_flags(dvf_table: str) -> str:
    """Fragment SQL : par (mutation, dans {dvf_table}), flag `exclue_l2f`.

    Exclue ssi : tous locaux non nuls ∈ {Appartement, Dépendance}, ≥1 Appartement,
    < IMMEUBLE_ENTIER_MIN_APP appartements.
    """
    return f"""
        SELECT id_mutation,
               coalesce(bool_and(type_local IN ('Appartement', 'Dépendance'))
                        FILTER (WHERE type_local IS NOT NULL), false)
               AND bool_or(type_local = 'Appartement')
               AND count(*) FILTER (WHERE type_local = 'Appartement') < {IMMEUBLE_ENTIER_MIN_APP}
                   AS exclue_l2f
        FROM {dvf_table}
        WHERE nature_mutation IN {L2_NATURES}
        GROUP BY id_mutation
    """


# ======================== Lot 1-2 : dataset étendu 2017-2025 ========================

EXT_YEARS = (2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026)
EXT_DVF_START = "DATE '2014-01-01'"


def build_ext_union(session: Session) -> None:
    """p_model_ext_dvf : vue UNION matérialisée histo (2014-2020, éditions cquest
    tardives = réputées complètes) + prod (2021-2025). Aucun chevauchement d'années.
    """
    _exec(session, """
        DROP TABLE IF EXISTS p_model_ext_dvf;
        CREATE TABLE p_model_ext_dvf AS
        SELECT id_mutation, date_mutation, nature_mutation, valeur_fonciere,
               id_parcelle, type_local, surface_reelle_bati, surface_terrain,
               'histo' AS source
        FROM dvf_mutations_histo
        UNION ALL
        SELECT id_mutation, date_mutation, nature_mutation, valeur_fonciere,
               id_parcelle, type_local, surface_reelle_bati, surface_terrain,
               'prod' AS source
        FROM dvf_mutations_parcelle;
        CREATE INDEX ON p_model_ext_dvf (id_parcelle, date_mutation);
        CREATE INDEX ON p_model_ext_dvf (date_mutation);
    """)
    session.commit()


def build_ext_mutations(session: Session) -> None:
    """Événements L2 dédupliqués sur l'UNION + flag L2-F (exclusion des ventes
    d'unités de copro, immeuble entier conservé). Même dédup que M3."""
    _exec(session, f"""
        DROP TABLE IF EXISTS p_model_ext_mut_l2;
        CREATE TABLE p_model_ext_mut_l2 AS
        WITH par AS (
            SELECT id_mutation, id_parcelle AS idu,
                   min(date_mutation) AS date_mutation,
                   max(valeur_fonciere) AS valeur,
                   max(coalesce(surface_terrain, 0)) AS s_terrain,
                   sum(coalesce(surface_reelle_bati, 0)) AS s_bati
            FROM p_model_ext_dvf
            WHERE nature_mutation IN {L2_NATURES}
            GROUP BY 1, 2
        ), mut AS (
            SELECT id_mutation, bool_or(s_bati > 0) AS bati, max(valeur) AS valeur,
                   sum(s_terrain) AS mut_s_terrain, sum(s_bati) AS mut_s_bati
            FROM par GROUP BY 1
        ), l2f AS ({l2f_mutation_flags('p_model_ext_dvf')})
        SELECT p.idu, p.id_mutation, p.date_mutation, m.bati,
               coalesce(f.exclue_l2f, false) AS exclue_l2f,
               CASE WHEN NOT m.bati AND m.mut_s_terrain > 0
                    THEN m.valeur / m.mut_s_terrain END AS pm2_terrain,
               CASE WHEN m.bati AND m.mut_s_bati > 0
                    THEN m.valeur / m.mut_s_bati END AS pm2_bati
        FROM par p JOIN mut m USING (id_mutation) LEFT JOIN l2f f USING (id_mutation);
        CREATE INDEX ON p_model_ext_mut_l2 (idu, date_mutation);
        CREATE INDEX ON p_model_ext_mut_l2 (date_mutation);

        DROP TABLE IF EXISTS p_model_ext_mut_all;
        CREATE TABLE p_model_ext_mut_all AS
        SELECT DISTINCT id_parcelle AS idu, date_mutation FROM p_model_ext_dvf;
        CREATE INDEX ON p_model_ext_mut_all (idu, date_mutation);
    """)
    session.commit()


def build_ext_dataset(session: Session, years: tuple[int, ...] = EXT_YEARS) -> None:
    """p_model_ext_dataset : même grammaire que M3 (fenêtres strictes as-of,
    clampées à 2014 → 36 mois PLEINS dès 2017), avec DEUX labels :
      - label      = L2-F (primaire, foncier)
      - label_l2   = L2 d'origine (contrôle)
    Rotations calculées sur les mutations L2-F (le signal de zone produit).
    Statiques et permis : RÉUTILISE p_model_static / p_model_permits (lecture seule).
    """
    yrs = ", ".join(f"({y})" for y in years)
    _exec(session, f"""
        DROP TABLE IF EXISTS p_model_ext_dataset;
        CREATE TABLE p_model_ext_dataset AS
        WITH years(annee) AS (VALUES {yrs}),
        maxy AS (
            SELECT coalesce(extract(year FROM max(date_mutation))::int, 0) AS y
            FROM p_model_ext_mut_l2
        ),
        stock AS (
            SELECT secteur, count(*)::float AS n_parcelles FROM p_model_frame GROUP BY 1
        ),
        win AS (
            SELECT annee,
                   make_date(annee, 1, 1)                                AS asof,
                   greatest(make_date(annee - 3, 1, 1), {EXT_DVF_START}) AS w36_start,
                   make_date(annee - 1, 1, 1)                            AS w12_start,
                   greatest(make_date(annee - 2, 1, 1), {EXT_DVF_START}) AS w24_start
            FROM years
        ),
        z_sect AS (
            SELECT f.secteur, w.annee,
                   count(DISTINCT m.id_mutation) FILTER (WHERE NOT m.bati AND NOT m.exclue_l2f) AS n_mut_nu_36m,
                   count(DISTINCT m.id_mutation) FILTER (WHERE m.bati AND NOT m.exclue_l2f)     AS n_mut_bati_36m,
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
            FROM p_model_ext_mut_l2 m
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
            FROM p_model_ext_mut_all ma CROSS JOIN win w
            WHERE ma.date_mutation < w.asof GROUP BY 1, 2
        ),
        d_permit AS (
            SELECT pp.idu, w.annee, max(pp.date_autorisation) AS dernier_permis
            FROM p_model_permits pp CROSS JOIN win w
            WHERE pp.date_autorisation < w.asof GROUP BY 1, 2
        ),
        dens AS (
            SELECT f.secteur,
                   sum(coalesce(st.emprise_bati_m2, 0)) / nullif(sum(f.surface_m2), 0) AS dens_bati_secteur,
                   avg((coalesce(st.emprise_bati_m2, 0) > 20)::int)::float             AS pct_bati_secteur
            FROM p_model_frame f JOIN p_model_static st ON st.idu = f.idu GROUP BY 1
        )
        SELECT
            f.idu, w.annee,
            CASE WHEN w.annee <= (SELECT y FROM maxy) THEN
                 (EXISTS (SELECT 1 FROM p_model_ext_mut_l2 mu
                          WHERE mu.idu = f.idu AND NOT mu.exclue_l2f
                            AND mu.date_mutation >= w.asof
                            AND mu.date_mutation < make_date(w.annee + 1, 1, 1)))::int
            END AS label,
            CASE WHEN w.annee <= (SELECT y FROM maxy) THEN
                 (EXISTS (SELECT 1 FROM p_model_ext_mut_l2 mu
                          WHERE mu.idu = f.idu
                            AND mu.date_mutation >= w.asof
                            AND mu.date_mutation < make_date(w.annee + 1, 1, 1)))::int
            END AS label_l2,
            f.commune, f.secteur, st.owner_type,
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
            (st.emprise_bati_m2 <= 20)                                          AS nu,
            (st.emprise_bati_m2 <= 20
             AND coalesce(st.zone_plu, '') IN ('U', 'AU'))                      AS nu_constructible,
            f.surface_m2, st.emprise_bati_m2,
            st.pct_potentiel, st.sous_densite, st.sdp_residuelle_m2,
            CASE
                WHEN dt.derniere_mutation IS NULL THEN 'inconnu'
                WHEN dt.derniere_mutation >= w.asof - INTERVAL '1 year'  THEN '<1'
                WHEN dt.derniere_mutation >= w.asof - INTERVAL '2 years' THEN '1-2'
                WHEN dt.derniere_mutation >= w.asof - INTERVAL '3 years' THEN '2-3'
                ELSE '3+'
            END AS tenure_bin,
            CASE
                WHEN dp.dernier_permis IS NULL THEN 'jamais'
                WHEN dp.dernier_permis >= w.asof - INTERVAL '2 years'  THEN '<2a'
                WHEN dp.dernier_permis >= w.asof - INTERVAL '5 years'  THEN '2-5a'
                WHEN dp.dernier_permis >= w.asof - INTERVAL '10 years' THEN '5-10a'
                ELSE '10a+'
            END AS permis_bin,
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
        CREATE UNIQUE INDEX ON p_model_ext_dataset (idu, annee);
        CREATE INDEX ON p_model_ext_dataset (annee);
    """)
    session.commit()
