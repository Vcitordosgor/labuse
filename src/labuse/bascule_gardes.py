"""Gardes de bascule — 6 briques IMPORTABLES (5 extraites de scripts/bascule_v8_calibre.py).

Un run servi ne doit JAMAIS être matérialisé ni servi sans que ces gardes soient passées.
Elles sont ici pour être RÉUTILISÉES (bascule v8, bascule pondération, futures bascules,
rebuild post-calibration du train 6) sans recopier une seule ligne de logique. Ordre
historique (n° = date d'ajout) :

  1. check_run_absent      — ANTI-ÉCRASEMENT : refuse de reconstruire un run déjà matérialisé.
  2. check_disque          — DISQUE : refuse de démarrer si la marge d'espace manque.
  3. ensure_backups        — SAUVEGARDE : fige les features pré-bascule (rollback possible).
  4. verify_completude     — COMPLÉTUDE : un run incomplet est plus dangereux qu'un run qui échoue.
  5. check_peremption      — PÉREMPTION : refuse de servir des déclassées AU périmées (> seuil).
  6. check_golden_regenere — GOLDEN (Vic 04/08) : toute bascule régénère le golden DANS LE MÊME
     GESTE. La référence restée sur q_v7 pendant la bascule v8 était une dette de PROCESS, pas
     un incident : 46 FAIL permanents masquaient toute vraie régression. La bascule n'est pas
     complète tant que le golden ne cite pas le run servi.

Lecture seule / idempotentes sauf ensure_backups (écrit une fois, jamais écrasé).
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from labuse.db import engine, session_scope

TARGET = "q_v8_calibre"

#: Référence golden versionnée (qa/golden_check.py la compare champ par champ).
GOLDEN_PATH = Path(__file__).resolve().parents[2] / "reports" / "m6-audit" / "golden" / "golden-parcelles.json"


class GoldenPerimeError(RuntimeError):
    """6ᵉ garde : la référence golden cite un AUTRE run que le run servi — elle a raté une
    bascule. Régénérer (qa/golden_check.py --dump, ancres préservées) puis re-vérifier."""


def check_golden_regenere(run_servi: str, golden_path: Path | str = GOLDEN_PATH) -> dict:
    """6ᵉ garde (arbitrage Vic 04/08) — refuse de déclarer une bascule complète si la référence
    golden ne cite pas le run servi (meta.run_v2_servi). Ne régénère PAS elle-même (le dump
    exige l'API) : elle IMPOSE que la régénération ait eu lieu dans le même geste. Lecture seule."""
    p = Path(golden_path)
    if not p.exists():
        raise GoldenPerimeError(f"GOLDEN ABSENT : {p} — générer la référence "
                                f"(qa/golden_check.py --dump) avant de déclarer la bascule.")
    meta = (json.loads(p.read_text(encoding="utf-8")).get("meta") or {})
    ref_run = meta.get("run_v2_servi")
    if ref_run != run_servi:
        raise GoldenPerimeError(
            f"GOLDEN PÉRIMÉ : la référence cite run_v2_servi={ref_run!r} mais le run servi est "
            f"{run_servi!r} — la bascule v8 a déjà fait cette erreur (46 FAIL permanents). "
            f"Régénérer dans le même geste : qa/golden_check.py --dump --idu <les IDs de la "
            f"référence> (le --dump nu retombe sur GOLDEN_IDUS et PERD les ancres J3).")
    return {"golden": str(p), "run_v2_servi": ref_run,
            "n_parcelles": meta.get("n_parcelles"), "ok": True}


class RunDejaExistantError(RuntimeError):
    """1ʳᵉ garde : le run cible est déjà matérialisé — la reconstruction serait un écrasement
    silencieux. Le rollback est EXPLICITE (scripts/rollback_v8_calibre.py), jamais implicite."""


class RunIncompletError(RuntimeError):
    """Levée par verify_completude quand une table attendue manque — échec BRUYANT."""


# ─────────────────────────────── gardes de démarrage ───────────────────────────────

class DisqueInsuffisantError(RuntimeError):
    """Espace disque insuffisant pour finir la re-passe — refus de démarrer (échec bruyant)."""


class PeremptionError(RuntimeError):
    """5ᵉ garde (arbitrage Vic 30/07, option B) : des déclassements AU dépassent le seuil de
    blocage (180 j) — refus de SERVIR un run qui les exposerait encore, sauf --peremption-ack
    humain et tracé. Ne DURCIT jamais la parcelle (pas d'escalade vers ecartee = option A) : le
    garde vise NOTRE oubli (règlement non lu), pas la parcelle."""


def check_peremption(ack_motif: str | None = None) -> dict:
    """Refuse de basculer si des déclassées AU dépassent 180 j, sauf contournement tracé.
    L'ack est BAVARD (exigence Vic) : journalise QUI, QUAND, COMBIEN — consultable après coup."""
    import getpass
    from labuse.faisabilite.au_statut import (
        declassees_perimees, journalise_peremption_ack, SEUIL_BLOCAGE_JOURS)
    with session_scope() as s:
        n = declassees_perimees(s, SEUIL_BLOCAGE_JOURS)
    if n == 0:
        return {"perimees": 0, "acked": False}
    if not ack_motif:
        raise PeremptionError(
            f"BLOCAGE PÉREMPTION — {n} déclassées AU dépassent {SEUIL_BLOCAGE_JOURS} j sans "
            f"vérification d'ouverture (les deux taxonomies : générique, declasse_au_fermee, "
            f"declasse_au_statut_inconnu).\n    Le déclassement était TEMPORAIRE : lis les règlements "
            f"(calibre puis `labuse compute-au-ouverture` ; `compute-au-statut` pour le reste) OU "
            f"contourne, tracé :\n    --peremption-ack \"motif du passage en force\"")
    who = getpass.getuser()
    with session_scope() as s:
        journalise_peremption_ack(s, acked_by=who, n_parcels=n,
                                  seuil_jours=SEUIL_BLOCAGE_JOURS, motif=ack_motif)
    print(f"{_ts()} ⚠ PÉREMPTION CONTOURNÉE par {who} : {n} déclassées AU > {SEUIL_BLOCAGE_JOURS} j "
          f"servies quand même. Motif : « {ack_motif} ». Tracé dans au_statut_ack_journal.", flush=True)
    return {"perimees": n, "acked": True, "acked_by": who, "motif": ack_motif}


# M32 Phase B §2 : cadence normée → jours attendus entre deux millésimes amont. Seuil d'alerte = ×2.
_CADENCE_JOURS = {"hebdo": 7, "hebdomadaire": 7, "mensuel": 30, "trimestriel": 91,
                  "semestriel": 182, "annuel": 365}


def check_fraicheur(seuil_facteur: float = 2.0, session=None) -> dict:
    """Garde d'exploitation (spec millésime §5, arbitrage Vic : INCLUSE d'office au rebuild).
    Pour chaque couche à horizon connu, si `now − source_horizon_at` dépasse la cadence attendue
    ×`seuil_facteur`, AVERTISSEMENT BRUYANT — **jamais bloquant** (le retard de la source n'est pas
    une faute de la bascule, mais il doit se VOIR). Les couches « continu » ou à horizon inconnu
    sont ignorées (pas de cadence de référence). `session` optionnelle (tests) ; sinon session_scope.
    Retourne la liste des retards constatés."""
    import datetime
    retards = []
    _sql = ("SELECT name, source_horizon_at, source_cadence FROM data_sources "
            "WHERE source_horizon_at IS NOT NULL AND source_cadence IS NOT NULL")
    if session is not None:
        rows = session.execute(text(_sql)).all()
    else:
        with session_scope() as s:
            rows = s.execute(text(_sql)).all()
    today = datetime.date.today()
    for name, horizon, cadence in rows:
        jours_attendus = _CADENCE_JOURS.get((cadence or "").lower())
        if not jours_attendus:
            continue  # cadence non bornable (continu) → pas de seuil de retard
        age = (today - horizon).days
        if age > jours_attendus * seuil_facteur:
            retards.append({"source": name, "horizon": str(horizon), "age_jours": age,
                            "cadence": cadence, "seuil_jours": int(jours_attendus * seuil_facteur)})
    for r in retards:
        print(f"{_ts()} ⚠ FRAÎCHEUR — « {r['source']} » : horizon {r['horizon']} "
              f"({r['age_jours']} j, cadence {r['cadence']} → seuil {r['seuil_jours']} j). "
              f"Source en retard — NON bloquant, mais à voir.", flush=True)
    if not retards:
        print(f"{_ts()} ✓ fraîcheur : toutes les couches datées dans leur cadence.", flush=True)
    return {"retards": retards, "n_retards": len(retards)}


def _ts() -> str:
    """Horodatage HH:MM:SS pour la journalisation (Date.now() indisponible dans les workflows,
    mais ici on est en script Python standard)."""
    import datetime
    return datetime.datetime.now().strftime("%H:%M:%S")


def check_disque(target: str = TARGET, marge: float = 1.25) -> dict:
    """Garde DISQUE (garde manquante qui a tué le job à 20 %, Vic 30/07). Estime l'espace que la
    re-passe q_v8 va CONSOMMER (cascade + evaluations + scores + snapshot, dimensionné sur la
    référence complète q_v7_defisc), le compare à l'espace DISPONIBLE = libre OS + espace mort
    RÉUTILISABLE dans les tables cibles (le job réutilise les lignes supprimées sans grossir le
    fichier). Refuse de démarrer si disponible < besoin × marge. Idempotent, lecture seule."""
    import shutil
    with engine().connect() as c:
        # besoin = taille des tranches q_v7 (référence complète) MOINS ce que q_v8 a déjà écrit
        need = c.execute(text("""
            SELECT
              (SELECT pg_total_relation_size('dryrun_cascade_results')::float
                      * (SELECT count(*) FROM dryrun_cascade_results WHERE run_label='q_v7_defisc')
                      / NULLIF((SELECT count(*) FROM dryrun_cascade_results),0)) +
              (SELECT pg_total_relation_size('parcel_p_score_v2')::float / NULLIF((SELECT count(DISTINCT run_id) FROM parcel_p_score_v2),0)) +
              (SELECT pg_total_relation_size('dryrun_parcel_evaluations')::float
                      * (SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label='q_v7_defisc')
                      / NULLIF((SELECT count(*) FROM dryrun_parcel_evaluations),0))
        """)).scalar() or 0.0
        already = c.execute(text("""
            SELECT (SELECT count(*) FROM dryrun_cascade_results WHERE run_label=:t)::float
                   / NULLIF((SELECT count(*) FROM dryrun_cascade_results WHERE run_label='q_v7_defisc'),0)"""),
            {"t": target}).scalar() or 0.0
        need_rest = need * max(0.0, 1.0 - already)
        # espace RÉUTILISABLE dans les tables cibles (lignes supprimées non rendues à l'OS, mais
        # réutilisées par les INSERT). Mesure EXACTE via pg_freespacemap (FSM) si l'extension est
        # présente — post-VACUUM `n_dead_tup` retombe à 0 et sous-compterait ; repli n_dead_tup sinon.
        _tables = ('dryrun_cascade_results', 'parcel_p_score_v2', 'dryrun_parcel_evaluations', 'score_snapshot_parcelles')
        _has_fsm = c.execute(text("SELECT 1 FROM pg_extension WHERE extname='pg_freespacemap'")).scalar()
        if _has_fsm:
            dead = 0.0
            for t in _tables:
                if c.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar():
                    dead += float(c.execute(text(f"SELECT COALESCE(sum(avail),0) FROM pg_freespace('{t}')")).scalar() or 0)
        else:
            dead = c.execute(text("""
                SELECT COALESCE(sum(n_dead_tup::float / NULLIF(n_live_tup,0) * pg_relation_size(relid)),0)
                FROM pg_stat_user_tables WHERE relname = ANY(:t)"""), {"t": list(_tables)}).scalar() or 0.0
    free = shutil.disk_usage(".").free
    # Le FSM ABSORBE les écritures (réutilisation sans grossir le fichier) ; seul le DÉBORDEMENT
    # (besoin − FSM) tombe sur le disque OS. On garde donc sur le besoin OS RÉEL, pas le brut.
    besoin_os = max(0.0, need_rest - dead)
    rep = {"besoin_reste_go": round(need_rest/1e9, 2), "fsm_reutilisable_go": round(dead/1e9, 2),
           "besoin_os_go": round(besoin_os/1e9, 2), "libre_os_go": round(free/1e9, 2),
           "marge": marge, "ok": free >= besoin_os * marge}
    print(f"  [garde disque] besoin≈{rep['besoin_reste_go']} Go, dont FSM réutilisable "
          f"{rep['fsm_reutilisable_go']} Go → débordement OS ≈{rep['besoin_os_go']} Go vs libre OS "
          f"{rep['libre_os_go']} Go (marge ×{marge})", flush=True)
    if not rep["ok"]:
        raise DisqueInsuffisantError(
            f"DISQUE INSUFFISANT : débordement OS ≈{rep['besoin_os_go']} Go × {marge} > libre "
            f"{rep['libre_os_go']} Go. Libérer des runs obsolètes (purge q_v6_m8 + anciens runs) "
            f"puis VACUUM, ou --skip-disk-check si réutilisation certaine.")
    return rep

def ensure_backups() -> None:
    """Sauvegardes features pré-bascule (créées une seule fois ; jamais écrasées)."""
    with engine().begin() as c:
        for src, bak in [("parcel_residuel", "parcel_residuel_pre_v8"),
                         ("p_model_static", "p_model_static_pre_v8")]:
            if not c.execute(text("SELECT to_regclass(:b)"), {"b": bak}).scalar():
                c.execute(text(f"CREATE TABLE {bak} AS SELECT * FROM {src}"))
                print(f"  backup créé : {bak}", flush=True)


def verify_completude(target: str, n_expected_cascade: int, n_expected_scores: int) -> dict:
    """5) AUTO-VÉRIFICATION. Compte chaque table clé-run vs attendu. Lève RunIncompletError (échec
    BRUYANT) au premier manque — le run n'est PAS déclaré servable tant que les 4 tables ne sont pas
    complètes : scores P, cascade (evaluations + résultats), snapshot."""
    with engine().connect() as c:
        counts = {
            "parcel_p_score_v2":         c.execute(text("SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=:r"), {"r": target}).scalar(),
            "dryrun_parcel_evaluations": c.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:r"), {"r": target}).scalar(),
            "dryrun_cascade_results":    c.execute(text("SELECT count(*) FROM dryrun_cascade_results WHERE run_label=:r"), {"r": target}).scalar(),
            "matrice_statut_non_null":   c.execute(text("SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=:r AND matrice_statut IS NOT NULL"), {"r": target}).scalar(),
            "p_score_v2_runs":           c.execute(text("SELECT count(*) FROM p_score_v2_runs WHERE run_id=:r"), {"r": target}).scalar(),
            "snapshot_parcelles":        c.execute(text("SELECT count(*) FROM score_snapshot_parcelles sp JOIN score_snapshots ss ON ss.id=sp.snapshot_id WHERE ss.run_label=:r"), {"r": target}).scalar(),
        }
    problems = []
    if counts["parcel_p_score_v2"] != n_expected_scores:
        problems.append(f"scores P {counts['parcel_p_score_v2']} ≠ {n_expected_scores}")
    if counts["dryrun_parcel_evaluations"] != n_expected_cascade:
        problems.append(f"cascade evaluations {counts['dryrun_parcel_evaluations']} ≠ {n_expected_cascade}")
    if counts["matrice_statut_non_null"] != n_expected_cascade:
        problems.append(f"matrice_statut renseigné {counts['matrice_statut_non_null']} ≠ {n_expected_cascade}")
    if counts["dryrun_cascade_results"] <= 0:
        problems.append("dryrun_cascade_results VIDE (cascade non produite)")
    if counts["p_score_v2_runs"] != 1:
        problems.append(f"header p_score_v2_runs {counts['p_score_v2_runs']} ≠ 1")
    if counts["snapshot_parcelles"] != n_expected_scores:
        problems.append(f"snapshot {counts['snapshot_parcelles']} ≠ {n_expected_scores}")
    if problems:
        raise RunIncompletError(f"RUN {target} INCOMPLET — NE PAS SERVIR :\n    - " + "\n    - ".join(problems)
                                + f"\n  détail: {counts}")
    return counts



def check_run_absent(target: str = TARGET) -> int:
    """1ʳᵉ garde ANTI-ÉCRASEMENT. Refuse si le run cible existe déjà ; sinon renvoie le nombre
    de parcelles (dimensionne la re-passe). Lecture seule."""
    with engine().connect() as c:
        if c.execute(text("SELECT 1 FROM p_score_v2_runs WHERE run_id=:t"), {"t": target}).scalar():
            raise RunDejaExistantError(
                f"{target} existe déjà — rollback d'abord (python scripts/rollback_v8_calibre.py).")
        return c.execute(text("SELECT count(*) FROM parcels")).scalar()


def _idurba_date(idurba: str | None):
    """Extrait la date (AAAAMMJJ finale) d'un idurba (`97412_PLU_20240320`, `97409_20190228`).
    None si non parsable. Sert à chiffrer l'AMPLEUR d'une divergence."""
    import datetime
    import re
    m = re.search(r"(\d{8})\D*$", idurba or "")
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def _confronter_idurba(communes: dict, gpu: dict) -> list[dict]:
    """Cœur PUR de la confrontation (sans DB, testable) : `communes` = config plu_millesimes
    ({insee: {idurba, commune, statut, date_mairie}}), `gpu` = {insee: [idurba ingérés]}.
    Retourne la liste des divergences MANQUANT / RESIDU avec l'ampleur en jours."""
    import datetime
    out: list[dict] = []
    for insee, cfg in sorted(communes.items()):
        if cfg.get("statut") == "rnu":
            continue
        cidu = (cfg.get("idurba") or "").strip()
        gidus = gpu.get(insee, [])
        gset = {g.lower() for g in gidus}
        d_mairie = _idurba_date(cidu)
        if d_mairie is None and cfg.get("date_mairie"):
            try:
                d_mairie = datetime.date.fromisoformat(cfg["date_mairie"])
            except (ValueError, TypeError):
                d_mairie = None
        if cidu and cidu.lower() not in gset:
            newest = max((_idurba_date(g) for g in gidus if _idurba_date(g)), default=None)
            ampleur = (d_mairie - newest).days if d_mairie and newest else None
            out.append({"insee": insee, "commune": cfg.get("commune"), "type": "MANQUANT",
                        "idurba_mairie": cidu, "idurba_gpu": " | ".join(sorted(gidus)) or "(aucun)",
                        "ampleur_jours": ampleur})
        for g in sorted(x for x in gidus if x.lower() != cidu.lower()):
            dg = _idurba_date(g)
            ampleur = (d_mairie - dg).days if d_mairie and dg else None
            out.append({"insee": insee, "commune": cfg.get("commune"), "type": "RESIDU",
                        "idurba_mairie": cidu, "idurba_gpu": g, "ampleur_jours": ampleur})
    return out


def check_coherence_idurba(session=None) -> dict:
    """Garde de CONFRONTATION GPU-vs-mairie (M40) — bruyante, NON bloquante (même régime que
    `check_fraicheur` : elle alerte, elle n'empêche pas un geste légitime). Oppose, par commune,
    l'idurba MAIRIE (référence d'approbation, `config/plu_millesimes.yaml`) à l'idurba GPU
    réellement ingéré (`spatial_layers.plu_gpu_zone`). Deux divergences :
      · **MANQUANT** : le document mairie n'est PAS servi au GPU → vrai retard GPU-derrière-mairie
        (la raison d'être de cette garde : elle attrapera ce cas le jour où il arrivera) ;
      · **RESIDU**  : le GPU garde un document superseded à côté du courant (hygiène — Saint-Joseph).
    `rnu` et communes hors config ignorées. Casse PLU/plu neutralisée. Lecture seule.
    Retourne `{divergences: [...], n_manquant, n_residu}`."""
    from labuse.config import load_yaml_config
    communes = (load_yaml_config("plu_millesimes") or {}).get("communes", {})
    sql = ("SELECT left(attrs->>'idurba',5) insee, array_agg(DISTINCT attrs->>'idurba') idus "
           "FROM spatial_layers WHERE kind='plu_gpu_zone' AND attrs->>'idurba' IS NOT NULL GROUP BY 1")
    if session is not None:
        rows = session.execute(text(sql)).all()
    else:
        with engine().connect() as c:
            rows = c.execute(text(sql)).all()
    gpu = {insee: [i for i in idus if i] for insee, idus in rows}
    divergences = _confronter_idurba(communes, gpu)
    for d in divergences:
        amp = f", ampleur {d['ampleur_jours']} j" if d.get("ampleur_jours") is not None else ""
        print(f"{_ts()} ⚠ IDURBA [{d['type']}] — {d['commune']} ({d['insee']}) : "
              f"mairie « {d['idurba_mairie']} » vs GPU « {d['idurba_gpu']} »{amp}. "
              f"Confrontation GPU↔mairie — NON bloquant, à voir.", flush=True)
    if not divergences:
        print(f"{_ts()} ✓ idurba : GPU = mairie pour toutes les communes outillées.", flush=True)
    n_manquant = sum(1 for d in divergences if d["type"] == "MANQUANT")
    return {"divergences": divergences, "n": len(divergences),
            "n_manquant": n_manquant, "n_residu": len(divergences) - n_manquant}


def check_coherence_renouvellement(session=None) -> dict:
    """Garde de COHÉRENCE du segment Renouvellement (M47) — bruyante, NON bloquante (même régime
    que `check_fraicheur`/`check_coherence_idurba` : elle alerte, elle n'empêche jamais un geste).
    `parcel_renouvellement` était la SEULE table run-scopée montée par une commande isolée
    (`labuse renouv`) : sans garde ni câblage, elle re-portait un run mort en silence à la première
    bascule (constat M47-P0). On oppose le(s) `run_label` présent(s) dans la table au run SERVI
    (`config/served_run.txt`, via `Q_A_RUN_LABEL`). Trois cas d'alerte :
      · **ABSENTE**  : la table n'existe pas → segment non calculé (relancer `labuse build-mvt`) ;
      · **PÉRIMÉE**  : run(table) ≠ run servi → un chiffre périmé serait servi (fiche/carte/liste) ;
      · **MÉLANGÉE** : plusieurs run_label coexistent → une lecture non scopée mélangerait deux runs.
    Lecture seule. Retourne `{ok, servi, runs, statut}`."""
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    servi = Q_A_RUN_LABEL
    sql_exist = "SELECT to_regclass('parcel_renouvellement') IS NOT NULL"
    sql_runs = "SELECT run_label, count(*) FROM parcel_renouvellement GROUP BY 1 ORDER BY 2 DESC"
    if session is not None:
        exists = bool(session.execute(text(sql_exist)).scalar())
        rows = session.execute(text(sql_runs)).all() if exists else []
    else:
        with engine().connect() as c:
            exists = bool(c.execute(text(sql_exist)).scalar())
            rows = c.execute(text(sql_runs)).all() if exists else []
    runs = {r: int(n) for r, n in rows}
    if not exists:
        statut, ok = "ABSENTE", False
    elif set(runs) == {servi}:
        statut, ok = "OK", True
    elif servi not in runs:
        statut, ok = "PÉRIMÉE", False
    else:
        statut, ok = "MÉLANGÉE", False
    if ok:
        print(f"{_ts()} ✓ renouvellement : segment sur le run servi « {servi} » "
              f"({runs[servi]} parcelles).", flush=True)
    else:
        print(f"{_ts()} ⚠ RENOUVELLEMENT [{statut}] — run servi « {servi} », table {runs or '∅'}. "
              f"Relancer `labuse build-mvt` (segment câblé au geste). NON bloquant, à voir.", flush=True)
    return {"ok": ok, "servi": servi, "runs": runs, "statut": statut}


def check_peremption_tuiles(session=None) -> dict:
    """Garde de PÉREMPTION des tuiles carte (M48) — bruyante, NON bloquante (même régime que
    `check_fraicheur`/`check_coherence_renouvellement`). La carte est servie depuis la table
    MATÉRIALISÉE `mvt_parcels` ; si elle a été bâtie AVANT le dernier re-score du run servi
    (`parcel_p_score_v2`) ou le dernier calcul de `parcel_residuel`, elle raconte des tiers/SDP
    périmés — la carte contredit alors la fiche (constat M48 : bascule M39 sans `build-mvt`).
    Compare `mvt_meta.updated_at` aux `max(computed_at)` des tables amont. Lecture seule.
    Retourne `{ok, mvt_at, amont_at, retard_min}`."""
    import datetime
    sql = {
        "mvt": "SELECT value AS run, updated_at FROM mvt_meta WHERE key='run_label'",
        "score": "SELECT max(computed_at) FROM parcel_p_score_v2 WHERE run_id="
                 "(SELECT value FROM mvt_meta WHERE key='run_label')",
        "resid": "SELECT max(computed_at) FROM parcel_residuel",
    }
    def _run(conn):
        m = conn.execute(text(sql["mvt"])).first()
        if not m:
            return None, None, None
        sc = conn.execute(text(sql["score"])).scalar()
        rs = conn.execute(text(sql["resid"])).scalar()
        amont = max([d for d in (sc, rs) if d is not None], default=None)
        return m.run, m.updated_at, amont
    if session is not None:
        run, mvt_at, amont_at = _run(session)
    else:
        with engine().connect() as c:
            run, mvt_at, amont_at = _run(c)
    if mvt_at is None:
        print(f"{_ts()} ⚠ TUILES [ABSENTES] — `mvt_parcels`/`mvt_meta` non matérialisées. "
              f"Lancer `labuse build-mvt`. NON bloquant, à voir.", flush=True)
        return {"ok": False, "mvt_at": None, "amont_at": None, "retard_min": None}
    ok = amont_at is None or mvt_at >= amont_at
    retard = None if amont_at is None else round((amont_at - mvt_at).total_seconds() / 60)
    if ok:
        print(f"{_ts()} ✓ tuiles : `mvt_parcels` (run « {run} ») postérieure au dernier calcul amont.",
              flush=True)
    else:
        print(f"{_ts()} ⚠ TUILES [PÉRIMÉES] — bâties {mvt_at} < amont {amont_at} (retard {retard} min). "
              f"La carte sert des tiers/SDP périmés — relancer `labuse build-mvt`. NON bloquant, à voir.",
              flush=True)
    return {"ok": ok, "mvt_at": str(mvt_at), "amont_at": str(amont_at) if amont_at else None,
            "retard_min": retard}


#: kinds spatial_layers pour lesquels l'ABSENCE de data_source_id est LÉGITIME (documentée) :
#: couches synthétiques sans producteur externe. Vide aujourd'hui (le jeu de démo pose déjà sa source).
SOURCES_DECLAREES_LEGITIMES: frozenset[str] = frozenset()


def check_sources_declarees(session=None) -> dict:
    """Garde M-H — assertion « toute couche spatial_layers DÉCLARE sa source ». Rien ne détectait
    qu'un kind était ingéré sans data_source_id (traçabilité source ↔ couche trouée). Pour CHAQUE
    kind : OK (aucune ligne sans source) / ORPHELIN (des lignes sans data_source_id) / SOURCE ABSENTE
    (le kind est mappé — KIND_SOURCE — à un nom data_sources inexistant au catalogue). Bruyante, NON
    bloquante (même régime que check_coherence_tables_run_scopees). Retourne `{kind: statut}`."""
    from labuse.ingestion.layers_ingest import KIND_SOURCE
    out: dict[str, str] = {}

    def _run(conn):
        noms = {n for (n,) in conn.execute(text("SELECT name FROM data_sources"))}
        rows = conn.execute(text(
            "SELECT kind, count(*) FILTER (WHERE data_source_id IS NULL) AS orphelins, count(*) AS n "
            "FROM spatial_layers GROUP BY kind ORDER BY kind")).all()
        for kind, orphelins, n in rows:
            src = KIND_SOURCE.get(kind)
            if src is not None and src not in noms:
                out[kind] = "SOURCE ABSENTE"
                print(f"{_ts()} ⚠ {kind} [SOURCE ABSENTE] — mappé à « {src} », absent du catalogue "
                      f"data_sources. {n} ligne(s). NON bloquant.", flush=True)
            elif orphelins and kind not in SOURCES_DECLAREES_LEGITIMES:
                out[kind] = "ORPHELIN"
                print(f"{_ts()} ⚠ {kind} [ORPHELIN] — {orphelins}/{n} ligne(s) sans data_source_id "
                      f"(source ↔ couche non tracée). NON bloquant, à rattacher.", flush=True)
            else:
                out[kind] = "OK"
                print(f"{_ts()} ✓ {kind} : source déclarée ({n}).", flush=True)
    if session is not None:
        _run(session)
    else:
        with engine().connect() as c:
            _run(c)
    return out


def check_coherence_tables_run_scopees(session=None) -> dict:
    """Garde M50 — assertion « aucune table SERVIE run-scopée silencieusement périmée ». Pour CHAQUE
    table servie portant `run_label`, compare son/ses run(s) au run servi (`config/served_run.txt`).
    Bruyante, NON bloquante (régime check_fraicheur). `division_or_candidates` = workflow de revue PAR
    COMMUNE (peut légitimement retarder le run servi, il attend une revue humaine) → alerté mais toléré.
    Statuts par table : OK / PÉRIMÉE / MÉLANGÉE / ABSENTE. Retourne `{table: statut}`."""
    from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
    servi = Q_A_RUN_LABEL
    # (table, colonne_run, workflow_par_commune?) — flags/renouvellement/score_e montent DANS le geste ;
    # division_or est un workflow de revue par commune (garde informative, tolérée).
    tables = [("parcel_renouvellement", "run_label", False), ("score_e", "run_label", False),
              ("parcel_flags", "run_label", False), ("division_or_candidates", "run_label", True)]
    out: dict[str, str] = {}

    def _run(conn):
        for tbl, col, wf in tables:
            if not conn.execute(text(f"SELECT to_regclass('{tbl}')")).scalar():
                out[tbl] = "ABSENTE"
                print(f"{_ts()} ⚠ {tbl} [ABSENTE] — table non matérialisée. NON bloquant.", flush=True)
                continue
            runs = dict(conn.execute(text(f"SELECT {col}, count(*) FROM {tbl} GROUP BY 1")).all())
            if set(runs) == {servi}:
                out[tbl] = "OK"
                print(f"{_ts()} ✓ {tbl} : run servi « {servi} » ({runs[servi]}).", flush=True)
            else:
                out[tbl] = "PÉRIMÉE" if servi not in runs else "MÉLANGÉE"
                note = " (workflow revue par commune — toléré)" if wf else ""
                print(f"{_ts()} ⚠ {tbl} [{out[tbl]}]{note} — servi « {servi} », table {runs or '∅'}. "
                      f"NON bloquant, à voir.", flush=True)
    if session is not None:
        _run(session)
    else:
        with engine().connect() as c:
            _run(c)
    return out
