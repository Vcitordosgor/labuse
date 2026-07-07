"""Dry-run scoring (étages 1+2) — lecture des tables parallèles `dryrun_*`.

Le calcul à blanc est écrit par cascade.pipeline.evaluate_parcels(dryrun_label=…) ; ici on ne fait
que LIRE pour produire les livrables (distributions, top N, DIFF entre runs, contrôle de traçabilité).
Ne touche JAMAIS les évaluations live.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config


def compute_matrice(session: Session, run_label: str, commune: str) -> dict:
    """Post-pass matrice Q×A sur un run existant (lit dryrun_cascade_results, écrit q/a/statut dans
    dryrun_parcel_evaluations). Aucune ré-évaluation. Seuils/couches-A/base en config (tunable).

    Q = base + Σ(poids étages 0/1) ; A = base + Σ(poids étage 2, cf. a_layers) ; A-complétude =
    part des signaux A ≠ UNKNOWN. Une parcelle exclue étage 0 = écartée. DOUBLE VERROU : chaude
    exige A≥seuil ET A-complétude ≥ min (jamais chaude sur une accessibilité à moitié inconnue).
    Bascule : evenement='rouge' → chaude sur les SURVIVANTES (l'exclusion étage 0 n'est pas surchargée)."""
    cfg = load_yaml_config("scoring_matrice")
    s = cfg["seuils"]
    params = {"r": run_label, "c": commune, "a_layers": cfg["a_layers"], "base": cfg["base"],
              "qs": s["q_chaude"], "as_": s["a_chaude"], "acm": s["a_completude_min"], "qe": s["q_ecartee"]}
    session.execute(text(
        "WITH w AS ("
        "  SELECT cr.parcel_id, (cr.layer_name = ANY(:a_layers)) AS is_a, cr.result, cr.weight_applied, cr.evenement "
        "  FROM dryrun_cascade_results cr JOIN parcels p ON p.id=cr.parcel_id "
        "  WHERE cr.run_label=:r AND p.commune=:c), "
        "qa AS ("
        "  SELECT parcel_id, bool_or(result='HARD_EXCLUDE') AS excl, "
        "    GREATEST(1,LEAST(100, :base + COALESCE(sum(weight_applied) FILTER (WHERE NOT is_a),0)))::int AS q, "
        "    GREATEST(1,LEAST(100, :base + COALESCE(sum(weight_applied) FILTER (WHERE is_a),0)))::int AS a, "
        "    round(100.0 * count(*) FILTER (WHERE is_a AND result<>'UNKNOWN') "
        "          / NULLIF(count(*) FILTER (WHERE is_a),0))::int AS acompl, "
        "    bool_or(evenement='rouge') AS rouge "
        "  FROM w GROUP BY parcel_id) "
        "UPDATE dryrun_parcel_evaluations d SET q_score=qa.q, a_score=qa.a, a_completude=qa.acompl, "
        "  matrice_statut = CASE "
        "    WHEN qa.excl THEN 'ecartee' "
        "    WHEN qa.rouge THEN 'chaude' "
        "    WHEN qa.q >= :qs AND qa.a >= :as_ AND COALESCE(qa.acompl,0) >= :acm THEN 'chaude' "
        "    WHEN qa.q >= :qs THEN 'a_surveiller' "
        "    WHEN qa.q >= :qe THEN 'a_creuser' "
        "    ELSE 'ecartee' END "
        "FROM qa WHERE d.parcel_id=qa.parcel_id AND d.run_label=:r"), params)
    session.flush()
    return {r[0]: r[1] for r in session.execute(text(
        "SELECT matrice_statut, count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c GROUP BY 1 ORDER BY 2 DESC"), {"r": run_label, "c": commune}).all()}


def _top(session: Session, run_label: str, commune: str, statut: str, n: int = 20) -> list[dict]:
    out = []
    for row in session.execute(text(
        "SELECT p.idu, d.q_score, d.a_score, d.a_completude, d.opportunity_score "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c AND d.matrice_statut=:s "
        "ORDER BY d.q_score+d.a_score DESC, d.q_score DESC LIMIT :n"),
        {"r": run_label, "c": commune, "s": statut, "n": n}).mappings().all():
        motifs = [f"{m[0]}({m[1]:+g})" for m in session.execute(text(
            "SELECT layer_name, weight_applied FROM dryrun_cascade_results "
            "WHERE run_label=:r AND parcel_id=(SELECT id FROM parcels WHERE idu=:idu) "
            "AND weight_applied IS NOT NULL ORDER BY abs(weight_applied) DESC LIMIT 5"),
            {"r": run_label, "idu": row["idu"]}).all()]
        ev = session.execute(text(
            "SELECT string_agg(DISTINCT layer_name||':'||left(detail,40),' | ') FROM dryrun_cascade_results "
            "WHERE run_label=:r AND parcel_id=(SELECT id FROM parcels WHERE idu=:idu) AND evenement='rouge'"),
            {"r": run_label, "idu": row["idu"]}).scalar()
        out.append({**dict(row), "motifs": motifs, "evenement": ev})
    return out


def matrice_report(session: Session, run_label: str, commune: str) -> dict:
    return {"run_label": run_label, "commune": commune,
            "repartition": {r[0]: r[1] for r in session.execute(text(
                "SELECT matrice_statut, count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
                "WHERE d.run_label=:r AND p.commune=:c GROUP BY 1 ORDER BY 2 DESC"),
                {"r": run_label, "c": commune}).all()},
            "top_chaudes": _top(session, run_label, commune, "chaude"),
            "top_a_surveiller": _top(session, run_label, commune, "a_surveiller")}


def report(session: Session, run_label: str, commune: str, top_n: int = 50) -> dict:
    """Livrable d'un run : couverture, histogramme d'opportunité, comptes par statut/verdict,
    parcelles UNKNOWN-ABF, top N opportunités motivées, et contrôle base+Σ=score."""
    base = {"run_label": run_label, "commune": commune}

    base["n_parcelles"] = int(session.execute(text(
        "SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c"), {"r": run_label, "c": commune}).scalar() or 0)

    base["par_statut"] = {r[0]: r[1] for r in session.execute(text(
        "SELECT d.status, count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c GROUP BY d.status ORDER BY 2 DESC"),
        {"r": run_label, "c": commune}).all()}

    # histogramme opportunité par tranches de 10
    base["histogramme_opportunite"] = {int(r[0]): r[1] for r in session.execute(text(
        "SELECT (opportunity_score/10)*10 AS tranche, count(*) "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c GROUP BY 1 ORDER BY 1"),
        {"r": run_label, "c": commune}).all()}

    base["opportunite_stats"] = dict(session.execute(text(
        "SELECT min(opportunity_score) AS min, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY opportunity_score)::int AS median, "
        "  max(opportunity_score) AS max, round(avg(opportunity_score))::int AS moyenne, "
        "  percentile_cont(0.5) WITHIN GROUP (ORDER BY completeness_score)::int AS median_completude "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c"), {"r": run_label, "c": commune}).mappings().first() or {})

    base["verdicts_par_couche"] = {f"{r[0]}:{r[1]}": r[2] for r in session.execute(text(
        "SELECT cr.layer_name, cr.result, count(*) "
        "FROM dryrun_cascade_results cr JOIN parcels p ON p.id=cr.parcel_id "
        "WHERE cr.run_label=:r AND p.commune=:c GROUP BY 1,2 ORDER BY 3 DESC LIMIT 25"),
        {"r": run_label, "c": commune}).all()}

    base["unknown_abf"] = int(session.execute(text(
        "SELECT count(*) FROM dryrun_cascade_results cr JOIN parcels p ON p.id=cr.parcel_id "
        "WHERE cr.run_label=:r AND p.commune=:c AND cr.layer_name='abf' AND cr.result='UNKNOWN'"),
        {"r": run_label, "c": commune}).scalar() or 0)

    # top N opportunités + motifs (lignes à points ≠ 0, tracées)
    top = []
    for row in session.execute(text(
        "SELECT p.idu, d.opportunity_score, d.completeness_score, d.status "
        "FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c "
        "ORDER BY d.opportunity_score DESC, d.completeness_score DESC LIMIT :n"),
        {"r": run_label, "c": commune, "n": top_n}).mappings().all():
        motifs = [f"{m[0]}({m[1]:+g}) {m[2]}" for m in session.execute(text(
            "SELECT layer_name, weight_applied, left(detail,60) FROM dryrun_cascade_results cr "
            "JOIN parcels p ON p.id=cr.parcel_id "
            "WHERE cr.run_label=:r AND p.idu=:idu AND cr.weight_applied IS NOT NULL "
            "ORDER BY abs(cr.weight_applied) DESC LIMIT 4"),
            {"r": run_label, "idu": row["idu"]}).all()]
        top.append({**dict(row), "motifs": motifs})
    base["top"] = top

    # contrôle de traçabilité : base + Σ(weight_applied) == opportunity_score (hors HARD_EXCLUDE/clamp)
    ok = session.execute(text(
        "SELECT count(*) FROM ("
        "  SELECT d.parcel_id, d.opportunity_base, d.opportunity_score, "
        "    COALESCE(sum(cr.weight_applied),0) AS somme "
        "  FROM dryrun_parcel_evaluations d "
        "  JOIN parcels p ON p.id=d.parcel_id "
        "  LEFT JOIN dryrun_cascade_results cr ON cr.run_label=d.run_label AND cr.parcel_id=d.parcel_id "
        "  WHERE d.run_label=:r AND p.commune=:c AND d.opportunity_score > 0 "
        "  GROUP BY d.parcel_id, d.opportunity_base, d.opportunity_score"
        ") t WHERE opportunity_base + somme = opportunity_score"), {"r": run_label, "c": commune}).scalar()
    total_non_excl = session.execute(text(
        "SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id "
        "WHERE d.run_label=:r AND p.commune=:c AND d.opportunity_score > 0"),
        {"r": run_label, "c": commune}).scalar()
    base["tracabilite_base_plus_somme"] = f"{ok}/{total_non_excl} (hors clamp/hard-exclude)"
    return base


# ═══════════════ CONVENTION VERSIONNÉE — SIMULATION & APPLICATION ═══════════════

#: candidat de convention = les 4 seuils (la bascule événementielle est DOCTRINALE : jamais balayée)
_SIM_STATUT = """
CASE WHEN s.excl THEN 'ecartee'
     WHEN s.rouge THEN 'chaude'
     WHEN s.q >= :qs AND s.a >= :as_ AND s.acompl >= :acm THEN 'chaude'
     WHEN s.q >= :qs THEN 'a_surveiller'
     WHEN s.q >= :qe THEN 'a_creuser'
     ELSE 'ecartee' END
"""


def _sim_base(session: Session, run_label: str) -> None:
    """Base de simulation : UNE passe sur les 431k (q/a/acompl + excl + rouge + siren) dans une
    table TEMPORAIRE (session-locale, disparaît à la déconnexion — AUCUNE écriture persistante)."""
    session.execute(text("DROP TABLE IF EXISTS _sim_matrice"))
    session.execute(text("""
        CREATE TEMP TABLE _sim_matrice AS
        SELECT d.parcel_id, p.commune, d.q_score AS q, d.a_score AS a,
               COALESCE(d.a_completude, 0) AS acompl,
               COALESCE(c.excl, false) AS excl, COALESCE(c.rouge, false) AS rouge,
               pm.siren
        FROM dryrun_parcel_evaluations d
        JOIN parcels p ON p.id = d.parcel_id
        LEFT JOIN (SELECT parcel_id, bool_or(result = 'HARD_EXCLUDE') AS excl,
                          bool_or(evenement = 'rouge') AS rouge
                   FROM dryrun_cascade_results WHERE run_label = :r GROUP BY parcel_id) c
               ON c.parcel_id = d.parcel_id
        LEFT JOIN parcelle_personne_morale pm ON pm.idu = p.idu
        WHERE d.run_label = :r"""), {"r": run_label})
    session.execute(text("CREATE INDEX ON _sim_matrice (commune)"))


def simulate_matrice(session: Session, run_label: str, candidates: list[dict]) -> list[dict]:
    """Simulation À BLANC de conventions candidates (SELECT uniquement, cf. _sim_base).
    Par candidat : statuts île (chaude SÉPARÉE matrice vs événement), dossiers propriétaires
    identifiés parmi les chaudes (+ reliquat sans identité), détail chaudes par commune."""
    _sim_base(session, run_label)
    out = []
    for cand in candidates:
        params = {"qs": cand["q_chaude"], "as_": cand["a_chaude"],
                  "acm": cand.get("a_completude_min", 50), "qe": cand.get("q_ecartee", 50)}
        row = session.execute(text(f"""
            WITH st AS (SELECT s.*, {_SIM_STATUT} AS statut FROM _sim_matrice s)
            SELECT count(*) FILTER (WHERE statut = 'chaude')                          AS chaude,
                   count(*) FILTER (WHERE statut = 'chaude' AND rouge)                AS chaude_evenement,
                   count(*) FILTER (WHERE statut = 'chaude' AND NOT rouge)            AS chaude_matrice,
                   count(*) FILTER (WHERE statut = 'a_surveiller')                    AS a_surveiller,
                   count(*) FILTER (WHERE statut = 'a_creuser')                       AS a_creuser,
                   count(*) FILTER (WHERE statut = 'ecartee')                         AS ecartee,
                   count(DISTINCT siren) FILTER (WHERE statut = 'chaude' AND siren IS NOT NULL) AS dossiers,
                   count(*) FILTER (WHERE statut = 'chaude' AND siren IS NULL)        AS chaudes_sans_identite
            FROM st"""), params).mappings().one()
        communes = {r["commune"]: int(r["n"]) for r in session.execute(text(f"""
            WITH st AS (SELECT s.*, {_SIM_STATUT} AS statut FROM _sim_matrice s)
            SELECT commune, count(*) AS n FROM st WHERE statut = 'chaude' GROUP BY 1"""),
            params).mappings().all()}
        out.append({**cand, **{k: int(v or 0) for k, v in row.items()}, "par_commune": communes})
    return out


def apply_convention(session: Session, run_label: str = "q_v2") -> dict:
    """UN point d'entrée : rejoue la matrice ×24 depuis le YAML versionné + reconstruit les
    tuiles MVT. Idempotent (deux passes = même état). Les tops HTML sont régénérés par le CLI
    (script séparé). CANARI : 97415000AC0253 doit rester chaude (par ÉVÉNEMENT) — si elle
    tombe, la bascule est cassée : on lève, on n'applique pas silencieusement."""
    from ..api.tiles import build_mvt_table

    cfg = load_yaml_config("scoring_matrice")
    communes = [r[0] for r in session.execute(text("SELECT DISTINCT commune FROM parcels ORDER BY 1")).all()]
    stats = {}
    for c in communes:
        stats[c] = compute_matrice(session, run_label, c)
    session.commit()
    canari = session.execute(text(
        "SELECT d.matrice_statut FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id"
        " WHERE d.run_label = :r AND p.idu = '97415000AC0253'"), {"r": run_label}).scalar()
    if canari != "chaude":
        raise RuntimeError(
            f"CANARI 97415000AC0253 = {canari!r} (attendu chaude PAR ÉVÉNEMENT) — la bascule "
            "BODACC est cassée, pas un seuil. Application stoppée, tuiles NON reconstruites.")
    n_mvt = build_mvt_table(session, run_label)
    build_entonnoir(session, run_label)   # le popover entonnoir suit toujours la matrice
    return {"convention": cfg.get("convention"), "seuils": cfg["seuils"],
            "communes": len(communes), "mvt_parcelles": n_mvt, "canari_AC0253": canari,
            "statuts": {k: sum(s.get(k, 0) for s in stats.values())
                        for k in ("chaude", "a_surveiller", "a_creuser", "ecartee")}}


#: buckets de l'ENTONNOIR (C4, revue Vic) — libellé humain → couches excluantes
_ENTONNOIR_BUCKETS: list[tuple[str, list[str]]] = [
    ("déjà bâtie", ["bati"]),
    ("PPR rouge / aléa fort", ["risques"]),
    ("zonage A/N non constructible", ["zonage_plu_gpu"]),
    ("surface < 100 m²", ["surface"]),
    ("pente > 60 %", ["pente"]),
    ("faux positif OSM (école, cimetière, parking…)", ["osm_faux_positif"]),
    ("forêt domaniale / cœur de parc", ["foret_publique", "parc_national"]),
    ("prescription PLU (emplacements réservés…)", ["prescription_plu"]),
    ("eau / trait de côte", ["eau", "trait_de_cote"]),
    ("foncier public (Saint-Paul uniquement)", ["foncier_public"]),
    ("emprise voirie/linéaire (Saint-Paul uniquement)", ["emprise_lineaire"]),
]


def build_entonnoir(session: Session, run_label: str = "q_v2") -> int:
    """Matérialise la décomposition des écartées PAR MOTIF (île + par commune) — le popover
    entonnoir la sert instantanément. Une parcelle peut cumuler des motifs (affiché tel quel).
    À reconstruire après chaque matrice (matrice-apply le fait)."""
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS entonnoir_motifs (
          run_label text, commune text, ord int, motif text, n bigint,
          PRIMARY KEY (run_label, commune, motif))"""))
    session.execute(text("DELETE FROM entonnoir_motifs WHERE run_label = :r"), {"r": run_label})
    buckets_sql = " UNION ALL ".join(
        f"SELECT {i + 2} AS ord, '{label.replace(chr(39), chr(39) * 2)}' AS motif, count(*) AS n, commune "
        f"FROM ec WHERE layers && ARRAY[{', '.join(repr(x) for x in layers)}]::text[] GROUP BY commune"
        for i, (label, layers) in enumerate(_ENTONNOIR_BUCKETS))
    session.execute(text(f"""
        WITH excl AS (
          SELECT c.parcel_id, array_agg(DISTINCT c.layer_name)::text[] AS layers
          FROM dryrun_cascade_results c
          WHERE c.run_label = :r AND c.result = 'HARD_EXCLUDE' GROUP BY c.parcel_id),
        ec AS (
          SELECT d.parcel_id, p.commune, e.layers
          FROM dryrun_parcel_evaluations d
          JOIN parcels p ON p.id = d.parcel_id
          LEFT JOIN excl e ON e.parcel_id = d.parcel_id
          WHERE d.run_label = :r AND d.matrice_statut = 'ecartee'),
        rows AS (
          SELECT 0 AS ord, 'écartées (total)' AS motif, count(*) AS n, commune FROM ec GROUP BY commune
          UNION ALL
          SELECT 1, 'qualité insuffisante (Q<50, sans exclusion dure)', count(*), commune
          FROM ec WHERE layers IS NULL GROUP BY commune
          UNION ALL {buckets_sql})
        INSERT INTO entonnoir_motifs (run_label, commune, ord, motif, n)
        SELECT :r, commune, ord, motif, n FROM rows
        UNION ALL
        SELECT :r, '__ile__', ord, motif, sum(n) FROM rows GROUP BY ord, motif"""),
        {"r": run_label})
    n = session.execute(text("SELECT count(*) FROM entonnoir_motifs WHERE run_label = :r"),
                        {"r": run_label}).scalar() or 0
    session.commit()
    return int(n)
