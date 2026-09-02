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
    "comp_potentiel": "droits à bâtir résiduels (SDP non consommée)",
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
    return {"poids": {k: int(v) for k, v in poids.items()},
            "seuils": {k: int(v) for k, v in seuils.items()}}


DDL = """
CREATE TABLE IF NOT EXISTS parcel_renouvellement (
  idu                varchar(14) PRIMARY KEY,
  renouv_score       int  NOT NULL,      -- 0-100, somme des 3 composantes
  comp_potentiel     int  NOT NULL,      -- 0-47  : SDP résiduelle (percent_rank segment)
  comp_assiette      int  NOT NULL,      -- 0-29  : surface (percent_rank segment)
  comp_marche        int  NOT NULL,      -- 0-24  : rotation bâti secteur (percent_rank)
  code_bati_origine  text NOT NULL,      -- deja_bati | deja_bati_probable | ensemble_bati
  sdp_residuelle_m2  int,                -- dénormalisé pour l'affichage « pourquoi »
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
seg AS (
    SELECT b.idu, b.code, left(b.idu, 5) AS commune, d.zone_plu,
           coalesce(d.sdp_residuelle_m2, 0)::int AS sdp,
           round(d.surface_m2)::int              AS surface,
           coalesce(d.rot_bati_brute, 0)         AS rot_bati
    FROM bati_x b
    JOIN p_model_ext_dataset d ON d.idu = b.idu AND d.annee = :annee
    LEFT JOIN p_model_ext_copro c ON c.idu = b.idu
    WHERE d.zone_plu IN ('U', 'AU')
      AND (d.sdp_residuelle_m2 > :sdp_min OR d.surface_m2 >= :surf_min)
      AND NOT coalesce(c.copro_rnic OR c.copro_dvf, false)
      AND NOT EXISTS (SELECT 1 FROM public_x px WHERE px.idu = b.idu)
),
comp AS (
    SELECT s.*,
           round(:w_pot * percent_rank() OVER (ORDER BY s.sdp))::int          AS comp_potentiel,
           round(:w_ass * percent_rank() OVER (ORDER BY s.surface))::int      AS comp_assiette,
           round(:w_mar * percent_rank() OVER (ORDER BY s.rot_bati))::int     AS comp_marche
    FROM seg s
),
scored AS (
    SELECT c.*,
           LEAST(100, c.comp_potentiel + c.comp_assiette + c.comp_marche) AS score
    FROM comp c
)
INSERT INTO parcel_renouvellement
    (idu, renouv_score, comp_potentiel, comp_assiette, comp_marche,
     code_bati_origine, sdp_residuelle_m2, surface_m2, zone_plu, commune,
     rang_segment, rang_commune, run_label)
SELECT idu, score, comp_potentiel, comp_assiette, comp_marche,
       code, nullif(sdp, 0), surface, zone_plu, commune,
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
    session.execute(text(_BUILD_SQL), {
        **params, "w_pot": poids["potentiel_residuel"], "w_ass": poids["assiette"],
        "w_mar": poids["contexte_marche"]})

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
               code_bati_origine, sdp_residuelle_m2, surface_m2, zone_plu
        FROM parcel_renouvellement {where}
        ORDER BY rang_segment LIMIT :n"""),
        {"n": n, "c": commune}).mappings().all()]
