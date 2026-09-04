"""LOT 1 (data-gap) — variables DVF par parcelle + médianes €/m² par secteur.

ÉTEND `dvf_mutations_parcelle` (géo-DVF 974 niveau parcelle, millésimes 2021-2025 — les
2014-2020 sont retirés de la distribution officielle, fenêtre glissante DGFiP ; le flag
« mutation > 20 ans » est donc INCALCULABLE, consigné au rapport). AUCUN scoring ici :
la dormance/vendabilité est déjà scorée par le Score V (famille D) — ce lot livre du
MARCHÉ (input direct de la future calculette de charge foncière).

Livrables :
 1. Vue `v_parcel_dvf_last` — par parcelle : dernière mutation (date, nature, valeur,
    prix/m² bâti, prix/m² terrain). ⚠ Caveat DVF standard : `valeur_fonciere` porte sur la
    MUTATION ENTIÈRE (toutes parcelles/lots confondus) — pour une mutation multi-parcelles,
    le prix/m² « de la parcelle » est celui de l'ENSEMBLE ; `multi_parcelles` l'expose.
 2. Table `dvf_secteur_medianes` — par SECTEUR CADASTRAL (insee+000+section, 10 car.) ×
    type de bien (maison / appartement / terrain / autre) : n ventes, médiane valeur,
    médiane €/m² (m² bâti pour maison/appartement, m² terrain pour terrain).
    Agrégation au grain MUTATION (une vente multi-lignes = 1 observation), mutation
    attribuée à chaque secteur qu'elle touche. Recalcul idempotent (TRUNCATE + INSERT).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

FENETRE = "2021-2025 (millésimes géo-DVF disponibles)"


def ensure_dvf_views(engine) -> None:
    """Vue par parcelle — dernière mutation observée (fenêtre 2021-2025)."""
    with engine.begin() as c:
        c.execute(text(
            """
            CREATE OR REPLACE VIEW v_parcel_dvf_last AS
            WITH nb_parcelles AS (
              SELECT id_mutation, count(DISTINCT id_parcelle) AS n_parcelles
              FROM dvf_mutations_parcelle GROUP BY id_mutation
            ),
            par_mutation AS (
              SELECT d.id_parcelle, d.id_mutation, d.date_mutation,
                     max(d.nature_mutation)                AS nature,
                     max(d.valeur_fonciere)                AS valeur,
                     sum(COALESCE(d.surface_reelle_bati,0)) AS bati_m2,
                     max(COALESCE(d.surface_terrain,0))     AS terrain_m2,
                     max(np.n_parcelles) > 1                AS multi_parcelles
              FROM dvf_mutations_parcelle d JOIN nb_parcelles np USING (id_mutation)
              GROUP BY d.id_parcelle, d.id_mutation, d.date_mutation
            ),
            derniere AS (
              SELECT DISTINCT ON (id_parcelle) *
              FROM par_mutation ORDER BY id_parcelle, date_mutation DESC
            )
            SELECT id_parcelle AS idu, date_mutation, nature, valeur, multi_parcelles,
                   CASE WHEN bati_m2   > 0 THEN round(valeur / bati_m2)   END AS prix_m2_bati,
                   CASE WHEN terrain_m2 > 0 THEN round(valeur / terrain_m2) END AS prix_m2_terrain
            FROM derniere
            """))


DDL_MEDIANES = text(
    """
    CREATE TABLE IF NOT EXISTS dvf_secteur_medianes (
      secteur          varchar(10) NOT NULL,   -- insee + '000' + section (préfixe IDU)
      type_bien        varchar(16) NOT NULL,   -- maison | appartement | terrain | autre
      n_ventes         integer     NOT NULL,
      mediane_valeur   integer,
      mediane_prix_m2  integer,                -- €/m² bâti (maison/appart) ou terrain (terrain)
      fenetre          text        NOT NULL,
      computed_at      timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (secteur, type_bien)
    )""")


def compute_medianes_secteur(session: Session) -> dict:
    """Médianes €/m² par secteur × type de bien — grain MUTATION, ventes seules, idempotent."""
    session.execute(DDL_MEDIANES)
    session.execute(text("TRUNCATE dvf_secteur_medianes"))
    session.execute(text(
        """
        INSERT INTO dvf_secteur_medianes
          (secteur, type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre)
        WITH mutations AS (            -- 1 vente = 1 observation (toutes lignes agrégées)
          -- M101 B2 (arbitrage Vic) : « Vente terrain à bâtir » (995 actes) ENTRE dans la médiane
          -- TERRAIN — un acte qui se déclare terrain à bâtir EST une vente de terrain nu ; l'exclure
          -- jetait la donnée la plus qualifiée (écart mesuré ≤ +11 %/commune, AUDIT_M101 §B2). Les
          -- VTB portant du bâti (34/995) n'entrent NULLE PART (leur bâti n'est pas arbitré). VEFA /
          -- Échange / Adjudication / Expropriation restent EXCLUES (neuf → profil neuf_vefa dédié ;
          -- le reste = hors marché de gré à gré) : rien d'autre n'entre sans arbitrage.
          SELECT id_mutation,
                 max(valeur_fonciere)                 AS valeur,
                 sum(COALESCE(surface_reelle_bati,0)) AS bati_m2,
                 sum(terrain_par_parcelle)            AS terrain_m2,
                 bool_or(type_local = 'Maison')       AS a_maison,
                 bool_or(type_local = 'Appartement')  AS a_appart,
                 bool_or(nature_mutation = 'Vente terrain à bâtir') AS vtb
          FROM (SELECT id_mutation, valeur_fonciere, surface_reelle_bati, type_local, nature_mutation,
                       max(COALESCE(surface_terrain,0)) OVER (PARTITION BY id_mutation, id_parcelle)
                         / greatest(count(*) OVER (PARTITION BY id_mutation, id_parcelle), 1)
                         AS terrain_par_parcelle
                FROM dvf_mutations_parcelle
                WHERE nature_mutation IN ('Vente', 'Vente terrain à bâtir')) x
          GROUP BY id_mutation
        ),
        typees AS (
          SELECT id_mutation, valeur,
                 CASE WHEN a_maison THEN 'maison'
                      WHEN a_appart THEN 'appartement'
                      WHEN bati_m2 = 0 AND terrain_m2 > 0 THEN 'terrain'
                      ELSE 'autre' END AS type_bien,
                 CASE WHEN a_maison OR a_appart
                        THEN CASE WHEN bati_m2 > 0 THEN valeur / bati_m2 END
                      WHEN bati_m2 = 0 AND terrain_m2 > 0 THEN valeur / terrain_m2
                      END AS prix_m2
          FROM mutations WHERE valeur IS NOT NULL AND valeur > 1000   -- ventes à 1 € symbolique écartées
            AND (NOT vtb OR bati_m2 = 0)   -- M101 B2 : la VTB = terrain nu SEULEMENT, jamais le bâti
        ),
        secteurs AS (                   -- la mutation compte dans chaque secteur touché
          SELECT DISTINCT substring(d.id_parcelle FROM 1 FOR 10) AS secteur, t.*
          FROM typees t JOIN dvf_mutations_parcelle d ON d.id_mutation = t.id_mutation
        )
        SELECT secteur, type_bien, count(*),
               percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur)::int,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY prix_m2)
                 FILTER (WHERE prix_m2 IS NOT NULL AND prix_m2 BETWEEN 50 AND 20000)::int,
               :fenetre
        FROM secteurs GROUP BY secteur, type_bien
        """), {"fenetre": FENETRE})
    session.flush()
    row = session.execute(text(
        "SELECT count(*), count(DISTINCT secteur), sum(n_ventes) FROM dvf_secteur_medianes")).one()
    return {"lignes": row[0], "secteurs": row[1], "ventes": int(row[2] or 0)}


NEUF_VEFA_FENETRE_ANS = 3   # M101 B2 — même fenêtre que la référence secteur (dvf_profils.yaml)


def neuf_vefa_commune(session: Session, insee: str) -> dict:
    """M101 B2 (arbitrage Vic) — le NEUF que l'ACTE déclare : médiane €/m² bâti des ventes
    « Vente en l'état futur d'achèvement » de la COMMUNE, fenêtre 3 ans. Jamais une inférence
    (DVF ne porte aucune année de construction — AUDIT_M101 §B1.2) ; le complément non-VEFA ne
    s'appelle JAMAIS « ancien ». Grain commune : la VEFA n'atteint le seuil que dans 11/24
    communes (§B1.3) — l'absence est un état normal du profil, dite, pas un trou. Le SEUIL
    d'effectif est appliqué par marche_service (config dvf_profils.yaml, un critère un endroit).
    Renvoie {n, mediane_prix_m2_bati|None, fenetre_ans}."""
    # RETOURS-11 C3 (diagnostic mesuré) — sur 36 mois, ~988 mutations VEFA au 974 mais seules ~315 (32 %)
    # portent `surface_reelle_bati` : à l'acte VEFA le bâti n'existe pas encore, la surface réelle est
    # souvent VIDE. DVF au 974 (tel qu'ingéré : dvf_mutations_parcelle) NE porte PAS la surface Carrez des
    # lots → on ne peut PAS récupérer le prix des ~673 restantes (jamais un prix inventé). On distingue
    # donc le VOLUME VÉRITABLE de VEFA (`n_total`) du nombre à prix calculable (`n`) : la hachure honnête
    # dit « peu de ventes » SEULEMENT quand le volume est vraiment faible, pas quand seule la surface manque.
    row = session.execute(text(f"""
        WITH mut AS (
          SELECT id_mutation, max(valeur_fonciere) AS valeur,
                 sum(COALESCE(surface_reelle_bati,0)) AS bati
          FROM dvf_mutations_parcelle
          WHERE code_commune = :insee
            AND nature_mutation = 'Vente en l''état futur d''achèvement'
            AND date_mutation >= (now() - interval '{NEUF_VEFA_FENETRE_ANS} years')::date
          GROUP BY id_mutation)
        SELECT count(*) AS n_total,
               count(*) FILTER (WHERE bati > 0 AND valeur > 1000
                                AND valeur/bati BETWEEN 50 AND 20000) AS n,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur/bati)
                 FILTER (WHERE bati > 0 AND valeur > 1000
                         AND valeur/bati BETWEEN 50 AND 20000) AS med
        FROM mut"""), {"insee": insee}).one()
    n_total, n = int(row[0] or 0), int(row[1] or 0)
    return {"n": n, "n_total": n_total,
            "mediane_prix_m2_bati": round(float(row[2])) if row[2] is not None else None,
            "fenetre_ans": NEUF_VEFA_FENETRE_ANS}
