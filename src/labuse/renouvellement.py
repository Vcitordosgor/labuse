"""SEGMENT RENOUVELLEMENT (mandat M-RENOUV, lot A) — table additive `parcel_renouvellement`.

Rend visible le gisement chiffré par DOC-P (docs/SCORING_SPEC.md, annexe quantitative) :
les parcelles écartées à l'étage 0 pour occupation bâtie (BatiLayer, codes francs) mais
en zone U/AU avec un signal de capacité réel — densification, division, démolition-
reconstruction. ~73 078 avant filtres copro/foncier public (mesure 2026-07-26).

GARANTIES (règle 1 du mandat) :
- LECTURE SEULE sur tout l'existant : cascade, étage 0, modèle P, tiers servis,
  `parcel_p_score_v2` ne sont NI modifiés NI relus différemment. La seule écriture
  est la table additive `parcel_renouvellement` (rebuild complet idempotent).
- DOCTRINE : parcelles OCCUPÉES → « potentiel de renouvellement urbain », jamais
  « opportunité ». Jamais mélangées aux Chaudes/Brûlantes (vitrine parallèle,
  comme la Réserve foncière).
- Score = HEURISTIQUE DÉTERMINISTE TRANSPARENTE (percent_rank intra-segment,
  pondérations dans config/renouvellement.yaml). Aucun modèle appris ici — le
  P dédié (walk-forward + arène) est un mandat futur.

Définition (A1) — une parcelle entre dans le segment ssi TOUTES ces conditions :
  1. exclue à l'étage 0 par BatiLayer (HARD_EXCLUDE, codes deja_bati /
     deja_bati_probable / ensemble_bati) — lue dans dryrun_cascade_results du run
     servi ; le code est reconnu par le préfixe du motif (contrat d'affichage de
     `bati.classify`, source unique des libellés) ;
  2. zone_plu ∈ {U, AU}  (p_model_ext_dataset, année de scoring = max(annee)) ;
  3. sdp_residuelle_m2 > seuils.sdp_min_m2  OU  surface_m2 ≥ seuils.surface_min_m2 ;
  4. NON copro (p_model_ext_copro : rnic OU dvf) — un immeuble en copropriété ne se
     renouvelle pas par un acheteur unique ;
  5. NON foncier public : la couche cascade `foncier_public` (HARD_EXCLUDE = domaine
     non acquérable) existe et est appliquée — on ne sert pas le stade municipal
     comme potentiel.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import runs
from .config import load_yaml_config

#: Reconnaissance du code BatiLayer depuis le motif stocké (préfixes émis par
#: `bati.classify` — source unique de vérité des libellés ; l'ordre teste le cas
#: le plus spécifique d'abord : « déjà bâtie probable » avant « déjà bâtie »).
BATI_CODE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("déjà bâtie probable", "deja_bati_probable"),
    ("déjà bâtie", "deja_bati"),
    ("ensemble bâti", "ensemble_bati"),
)

#: Libellé produit du segment — wording DOCTRINAL (jamais « opportunité »). §5 : côté client
#: « Densifier l'existant » (la clé interne, la table et l'endpoint gardent « renouvellement »).
LIBELLE_SEGMENT = "Parcelle occupée — potentiel de densification"

#: Libellés client des 3 composantes (affichage « pourquoi »).
#: M129-C (Vic 19/08/2026) : `comp_divisibilite` RETIRÉE — division_or sort du produit.
#: Impact mesuré avant retrait : 2 lignes/67 258 portaient le +15, 0 sortie du top 100.
LIBELLES_COMPOSANTES = {
    "comp_potentiel": "droits à bâtir résiduels NETS des contraintes (pente, PPR rouge, ravine)",
    "comp_assiette": "taille de l'assiette foncière",
    "comp_marche": "rotation du bâti dans le secteur",
}


def code_from_detail(detail: str | None) -> str | None:
    """Code BatiLayer depuis le motif du verdict — miroir Python EXACT du CASE SQL
    (testable) ; None si le motif n'est pas un des trois cas francs."""
    d = (detail or "").strip()
    for prefix, code in BATI_CODE_PREFIXES:
        if d.startswith(prefix):
            return code
    return None


def load_config() -> dict:
    """Convention versionnée (config/renouvellement.yaml). REFUS explicite si les
    poids ne somment pas à 100 — un score /100 à pondérations fausses est un mensonge."""
    cfg = load_yaml_config("renouvellement")
    poids, seuils = cfg["poids"], cfg["seuils"]
    total = sum(int(v) for v in poids.values())
    if total != 100:
        raise ValueError(f"renouvellement.yaml : Σ poids = {total} ≠ 100 — corriger la config.")
    # RETOURS-11F M9 — facteurs de capacité NETTE (défauts sûrs si la section manque).
    cn = cfg.get("capacite_nette") or {}
    capacite_nette = {
        "pente_seuil_pct": float(cn.get("pente_seuil_pct", 30)),
        "facteur_pente_forte": float(cn.get("facteur_pente_forte", 0.5)),
        "facteur_ravine": float(cn.get("facteur_ravine", 0.85)),
        "facteur_mvt": float(cn.get("facteur_mvt", 0.90)),
    }
    return {"poids": {k: int(v) for k, v in poids.items()},
            "seuils": {k: int(v) for k, v in seuils.items()},
            "capacite_nette": capacite_nette}


DDL = """
CREATE TABLE IF NOT EXISTS parcel_renouvellement (
  idu                varchar(14) PRIMARY KEY,
  renouv_score       numeric(5,1) NOT NULL,  -- RETOURS-11F M9 : 0-100 CONTINU (1 décimale). L'ancien
                                          -- int (round par composante + LEAST(100)) écrasait la tête de
                                          -- liste sur un plateau (mesuré : top 50 = 2 scores distincts,
                                          -- 23 à 100). Le score naît des percent_rank BRUTS (non arrondis
                                          -- par composante) → il discrimine, y compris en tête.
  comp_potentiel     int  NOT NULL,      -- 0-47  : SDP résiduelle (percent_rank segment)
  comp_assiette      int  NOT NULL,      -- 0-29  : surface (percent_rank segment)
  comp_marche        int  NOT NULL,      -- 0-24  : rotation bâti secteur (percent_rank)
  code_bati_origine  text NOT NULL,      -- deja_bati | deja_bati_probable | ensemble_bati
  sdp_residuelle_m2  int,                -- SDP résiduelle BRUTE (droits à bâtir non consommés)
  sdp_nette_m2       int,                -- RETOURS-11F M9 : SDP résiduelle NETTE des contraintes
                                          -- (pente > 30 %, PPR rouge %, ravine/mvt). C'est ELLE qui
                                          -- alimente comp_potentiel — une parcelle contrainte descend.
  contrainte_pct     int,                -- part déduite (0-100) = 100 × (1 − sdp_nette/sdp_brute)
  surelevation_possible boolean,         -- OUTILS-FIX-1 C1 : PLUS ALIMENTÉE (surélévation débranchée) —
  niveaux_surelevation  int,             -- colonnes conservées sans migration, à SUPPRIMER au prochain rebuild de schéma
  surface_m2         int,
  zone_plu           text,
  commune            varchar(5) NOT NULL,
  rang_segment       int  NOT NULL,      -- rang île (score DESC, idu — déterministe)
  rang_commune       int  NOT NULL,
  run_label          text NOT NULL,      -- run servi dont provient l'étage 0
  computed_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_renouv_commune ON parcel_renouvellement (commune, rang_commune);
CREATE INDEX IF NOT EXISTS ix_renouv_rang ON parcel_renouvellement (rang_segment);
"""

#: CASE SQL du code — MIROIR de code_from_detail (testé par symétrie).
_CODE_CASE = """
    CASE WHEN cr.detail LIKE 'déjà bâtie probable%' THEN 'deja_bati_probable'
         WHEN cr.detail LIKE 'déjà bâtie%'          THEN 'deja_bati'
         WHEN cr.detail LIKE 'ensemble bâti%'        THEN 'ensemble_bati'
    END
"""

_FUNNEL_SQL = {
    # Chaque étape s'appuie sur la précédente — l'entonnoir complet est rapporté tel quel.
    "1_bati_fait": """
        SELECT count(DISTINCT cr.parcel_id)
        FROM dryrun_cascade_results cr
        WHERE cr.run_label = :run AND cr.layer_name = 'bati'
          AND cr.result = 'SOFT_FLAG' AND ({code}) IS NOT NULL
    """,
    "2_zone_u_au": """
        SELECT count(*) FROM ({base}) b
        JOIN parcels p ON p.id = b.parcel_id
        JOIN p_model_ext_dataset d ON d.idu = p.idu AND d.annee = :annee
        WHERE d.zone_plu IN ('U', 'AU')
    """,
    "3_capacite": """
        SELECT count(*) FROM ({base}) b
        JOIN parcels p ON p.id = b.parcel_id
        JOIN p_model_ext_dataset d ON d.idu = p.idu AND d.annee = :annee
        WHERE d.zone_plu IN ('U', 'AU')
          AND (d.sdp_residuelle_m2 > :sdp_min OR d.surface_m2 >= :surf_min)
    """,
}

# M129-D : le bâti n'exclut plus (M129 P1 — flag INFO, motif classify inchangé) : la MÊME
# population « bâti franc » se lit sur le FAIT (SOFT_FLAG), plus jamais sur HARD_EXCLUDE.
_BATI_BASE = """
    SELECT DISTINCT cr.parcel_id
    FROM dryrun_cascade_results cr
    WHERE cr.run_label = :run AND cr.layer_name = 'bati'
      AND cr.result = 'SOFT_FLAG' AND ({code}) IS NOT NULL
""".replace("{code}", _CODE_CASE)

_BUILD_SQL = """
WITH bati_x AS (
    SELECT DISTINCT ON (p.idu) p.idu, {code} AS code
    FROM dryrun_cascade_results cr
    JOIN parcels p ON p.id = cr.parcel_id
    WHERE cr.run_label = :run AND cr.layer_name = 'bati'
      AND cr.result = 'SOFT_FLAG' AND ({code}) IS NOT NULL
    ORDER BY p.idu, cr.id DESC
),
public_x AS (
    SELECT DISTINCT p.idu
    FROM dryrun_cascade_results cr
    JOIN parcels p ON p.id = cr.parcel_id
    WHERE cr.run_label = :run AND cr.layer_name = 'foncier_public'
      AND cr.result = 'SOFT_FLAG'
),
-- RETOURS-11F M9 — contraintes NON constructibles servies par le run (jamais inventées) :
-- PPR zone rouge (fraction RÉELLE lue dans le motif « N % de la surface »), ravine (contact
-- berge), mouvement de terrain. Elles réduisent la SDP résiduelle exploitable → la NETTE.
ppr_x AS (
    SELECT p.idu,
           max((regexp_match(cr.detail, '([0-9]+) % de la surface'))[1]::int) AS pct_rouge
    FROM dryrun_cascade_results cr
    JOIN parcels p ON p.id = cr.parcel_id
    WHERE cr.run_label = :run AND cr.layer_name = 'risques'
      AND cr.result = 'HARD_EXCLUDE' AND cr.detail LIKE '%PPR zone rouge%'
    GROUP BY p.idu
),
ravine_x AS (
    SELECT DISTINCT p.idu FROM dryrun_cascade_results cr JOIN parcels p ON p.id = cr.parcel_id
    WHERE cr.run_label = :run AND cr.layer_name = 'ravine' AND cr.result = 'SOFT_FLAG'
),
mvt_x AS (
    SELECT DISTINCT p.idu FROM dryrun_cascade_results cr JOIN parcels p ON p.id = cr.parcel_id
    WHERE cr.run_label = :run AND cr.layer_name = 'mvt' AND cr.result = 'SOFT_FLAG'
),
seg AS (
    SELECT b.idu, b.code, left(b.idu, 5) AS commune, d.zone_plu,
           coalesce(d.sdp_residuelle_m2, 0)::int AS sdp,
           round(d.surface_m2)::int              AS surface,
           coalesce(d.rot_bati_brute, 0)         AS rot_bati,
           -- facteur de constructibilité MULTIPLICATIF borné [0,1] (config capacite_nette) :
           greatest(0.0, (
               (1.0 - coalesce(ppr.pct_rouge, 0) / 100.0)
             * CASE WHEN tan(radians(coalesce(t.pente_non_batie_deg, t.pente_moy_deg, 0))) * 100
                         > :pente_seuil THEN :f_pente ELSE 1.0 END
             * CASE WHEN rav.idu IS NOT NULL THEN :f_ravine ELSE 1.0 END
             * CASE WHEN mvt.idu IS NOT NULL THEN :f_mvt   ELSE 1.0 END
           )) AS frac_net
           -- OUTILS-FIX-1 C1 (décision Vic 06/09) : la surélévation N'EST PLUS calculée ici. EXPORTS-1
           -- lot 3 avait débranché la table orpheline (parcel_residuel_bati, faîtage) en écrivant
           -- false/NULL en dur ; la colonne servie restait donc périmée jusqu'au prochain rebuild
           -- (VERIF-1 Q3). On cesse d'alimenter surelevable/niveaux_sur : « pas de signal plutôt qu'un
           -- signal périmé ». Le signal VIVANT reste au moteur commun (faisabilite/potentiel.surelevation,
           -- hauteur à l'égout), servi par la fiche. Les colonnes de parcel_renouvellement seront
           -- supprimées au prochain rebuild de schéma (pas de migration ici).
    FROM bati_x b
    JOIN p_model_ext_dataset d ON d.idu = b.idu AND d.annee = :annee
    LEFT JOIN p_model_ext_copro c ON c.idu = b.idu
    LEFT JOIN ppr_x    ppr ON ppr.idu = b.idu
    LEFT JOIN ravine_x rav ON rav.idu = b.idu
    LEFT JOIN mvt_x    mvt ON mvt.idu = b.idu
    LEFT JOIN parcel_terrain      t  ON t.idu  = b.idu
    WHERE d.zone_plu IN ('U', 'AU')
      AND (d.sdp_residuelle_m2 > :sdp_min OR d.surface_m2 >= :surf_min)
      AND NOT coalesce(c.copro_rnic OR c.copro_dvf, false)
      AND NOT EXISTS (SELECT 1 FROM public_x px WHERE px.idu = b.idu)
),
netd AS (
    -- SDP NETTE = SDP brute × facteur de constructibilité ; part de contrainte déduite (0-100).
    SELECT s.*,
           round(s.sdp * s.frac_net)::int                  AS sdp_nette,
           round(100 * (1.0 - s.frac_net))::int            AS contrainte_pct
    FROM seg s
),
comp AS (
    SELECT n.*,
           -- percent_rank BRUTS (0-1) — la source de discrimination fine ; les composantes affichées
           -- (points arrondis) restent des ENTIERS pour le « pourquoi », mais ne portent PLUS le score.
           -- M9 : le potentiel rank sur la SDP NETTE (contraintes déduites), plus sur la brute.
           :w_pot * percent_rank() OVER (ORDER BY n.sdp_nette)      AS pr_pot,
           :w_ass * percent_rank() OVER (ORDER BY n.surface)        AS pr_ass,
           :w_mar * percent_rank() OVER (ORDER BY n.rot_bati)       AS pr_mar,
           round(:w_pot * percent_rank() OVER (ORDER BY n.sdp_nette))::int    AS comp_potentiel,
           round(:w_ass * percent_rank() OVER (ORDER BY n.surface))::int      AS comp_assiette,
           round(:w_mar * percent_rank() OVER (ORDER BY n.rot_bati))::int     AS comp_marche
    FROM netd n
),
scored AS (
    -- RETOURS-11F M9 — score CONTINU (1 décimale) issu des percent_rank bruts : plus de plateau à 100.
    -- Les poids somment à 100 (config) → percent_rank ≤ 1 borne à 100 sans clamp (LEAST retiré : il ne
    -- servait qu'à masquer un dépassement impossible ici, et cachait la vérité du score en tête).
    SELECT c.*,
           round((c.pr_pot + c.pr_ass + c.pr_mar)::numeric, 1) AS score
    FROM comp c
)
INSERT INTO parcel_renouvellement
    (idu, renouv_score, comp_potentiel, comp_assiette, comp_marche,
     code_bati_origine, sdp_residuelle_m2, sdp_nette_m2, contrainte_pct,
     surface_m2, zone_plu, commune,
     rang_segment, rang_commune, run_label)
SELECT idu, score, comp_potentiel, comp_assiette, comp_marche,
       code, nullif(sdp, 0), nullif(sdp_nette, 0), contrainte_pct,
       surface, zone_plu, commune,
       rank() OVER (ORDER BY score DESC, idu),
       rank() OVER (PARTITION BY commune ORDER BY score DESC, idu),
       :run
FROM scored
""".replace("{code}", _CODE_CASE)


def build(session: Session, *, run_label: str | None = None,
          commit: bool = True, log=lambda *_: None) -> dict:
    """Reconstruit `parcel_renouvellement` (rebuild complet, idempotent) et renvoie
    l'entonnoir chiffré. LECTURE SEULE des sources ; ne touche jamais les runs servis."""
    run = run_label or runs.current()
    cfg = load_config()
    seuils, poids = cfg["seuils"], cfg["poids"]

    annee = session.execute(text(
        "SELECT max(annee) FROM p_model_ext_dataset")).scalar()
    if annee is None:
        raise RuntimeError("p_model_ext_dataset absent/vide — lancer `labuse score-v2` d'abord "
                           "(le segment lit l'as-of du dataset servi, il n'invente rien).")

    params = {"run": run, "annee": int(annee),
              "sdp_min": seuils["sdp_min_m2"], "surf_min": seuils["surface_min_m2"]}

    # ── entonnoir (mesuré AVANT l'écriture, sur les mêmes définitions) ────────────
    funnel: dict[str, int] = {}
    funnel["1_bati_fait"] = int(session.execute(text(
        _FUNNEL_SQL["1_bati_fait"].replace("{code}", _CODE_CASE)), params).scalar() or 0)
    # M129-D (leçon de la bascule q_v10) : une BASE VIDE = un prédicat mort ou un run absent —
    # on REFUSE, on n'écrit jamais un segment vide en silence (règle des trois fois M71-B3 :
    # c'est un « segment Renouvellement à 0 » qui a servi une carte vide à la recette).
    if funnel["1_bati_fait"] == 0:
        raise RuntimeError(
            f"Renouvellement : base « bâti (fait) » VIDE sur le run {run} — prédicat mort ou run "
            "non calculé. Rien n'est écrit (un 0 silencieux a déjà servi une carte vide, M129-D).")
    for step in ("2_zone_u_au", "3_capacite"):
        funnel[step] = int(session.execute(text(
            _FUNNEL_SQL[step].replace("{base}", _BATI_BASE)), params).scalar() or 0)

    # ── rebuild ───────────────────────────────────────────────────────────────────
    session.execute(text("DROP TABLE IF EXISTS parcel_renouvellement"))
    from .db import sql_statements  # FIX-GB-011 : plus de split(';') naif
    for stmt in sql_statements(DDL):
        if stmt.strip():
            session.execute(text(stmt))
    cn = cfg["capacite_nette"]
    session.execute(text(_BUILD_SQL), {
        **params, "w_pot": poids["potentiel_residuel"], "w_ass": poids["assiette"],
        "w_mar": poids["contexte_marche"],
        "pente_seuil": cn["pente_seuil_pct"], "f_pente": cn["facteur_pente_forte"],
        "f_ravine": cn["facteur_ravine"], "f_mvt": cn["facteur_mvt"]})

    n = int(session.execute(text("SELECT count(*) FROM parcel_renouvellement")).scalar() or 0)
    # 4/5 mesurés après coup (différences successives, mêmes définitions que le build)
    sans_copro = int(session.execute(text(_FUNNEL_SQL["3_capacite"]
        .replace("{base}", _BATI_BASE)
        + " AND NOT coalesce((SELECT c.copro_rnic OR c.copro_dvf FROM p_model_ext_copro c"
          "                   WHERE c.idu = p.idu), false)"), params).scalar() or 0)
    funnel["4_hors_copro"] = sans_copro
    funnel["5_hors_foncier_public_final"] = n

    if commit:
        session.commit()
    log(f"parcel_renouvellement : {n} parcelles (run {run}, année as-of {annee}) — "
        f"entonnoir {funnel}")
    return {"n": n, "run_label": run, "annee": int(annee), "funnel": funnel,
            "poids": poids, "seuils": seuils}


def top(session: Session, n: int = 20, commune: str | None = None) -> list[dict]:
    """Top du segment (île ou commune), avec les composantes — pour la CLI et le rapport."""
    where = "WHERE commune = :c" if commune else ""
    return [dict(r) for r in session.execute(text(f"""
        SELECT idu, commune, renouv_score, rang_segment, rang_commune,
               comp_potentiel, comp_assiette, comp_marche,
               code_bati_origine, sdp_residuelle_m2, sdp_nette_m2, contrainte_pct,
               surface_m2, zone_plu
        FROM parcel_renouvellement {where}
        ORDER BY rang_segment LIMIT :n"""),
        {"n": n, "c": commune}).mappings().all()]
