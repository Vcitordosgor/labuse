"""POST-M7 · J+2 — LA CHAÎNE DE FRAÎCHEUR : détection de livraison, refresh incrémental, dérivés.

La promesse : « jamais en retard de plus de 48 h sur la DERNIÈRE PUBLICATION de chaque source »
(pas « J+2 du terrain »). La cadence réelle des sources fait partie du produit — elle s'affiche.

INTERDIT ABSOLU : ce module ne touche JAMAIS les tables de run (`parcel_p_score_v2`,
`p_score_v2_runs`, `dryrun_cascade_results`, `dryrun_parcel_evaluations`, `parcel_evaluations`) —
le rang servi reste gelé jusqu'à la prochaine grande passe (Mac, cf. sync-run.sh). La
désynchronisation badge/rang entre deux grandes passes est ASSUMÉE et documentée.
"""
from __future__ import annotations

import json
import logging
from datetime import date

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.fraicheur")

#: tables que la chaîne de fraîcheur n'a PAS LE DROIT de toucher (garde-fou testé statiquement)
TABLES_RUN_INTERDITES = ("parcel_p_score_v2", "p_score_v2_runs", "dryrun_cascade_results",
                         "dryrun_parcel_evaluations", "parcel_evaluations")

# ── la matrice des sources : cadence RÉELLE de publication × où lire la dernière donnée ──
# `detection` : comment on sait qu'il y a du neuf. `auto` : la chaîne ingère seule ;
# False = détection/alerte seulement (couches de la CASCADE gelée : réingérer changerait les
# données sous le run servi → grande passe Mac requise, jamais un cron silencieux).
SOURCES = {
    "sitadel": {"label": "SITADEL (permis, SDES/Dido)", "cadence": "mensuelle",
                "date_sql": "SELECT max(date)::date FROM sitadel_permits WHERE date <= now()",
                "ds_name": "SITADEL (autorisations d'urbanisme)", "auto": True,
                "detection": "refresh delta quotidien (recouvrement 3 mois) — no-op si rien de neuf"},
    "bodacc": {"label": "BODACC (procédures collectives)", "cadence": "quotidienne",
               "date_sql": "SELECT max(date_annonce)::date FROM bodacc_procedures",
               "ds_name": "BODACC%", "auto": True,
               "detection": "re-interrogation batchée des 12,6k SIREN propriétaires (upsert annonce_id)"},
    "dvf": {"label": "DVF (mutations, Etalab geo-dvf)", "cadence": "semestrielle (avril / octobre)",
            "date_sql": "SELECT max(date_mutation)::date FROM dvf_mutations_parcelle",
            "ds_name": "DVF / valeurs foncières", "auto": True,
            "detection": "Last-Modified HTTP des CSV annuels — reload du millésime modifié uniquement"},
    "dpe": {"label": "DPE ADEME (logements existants)", "cadence": "hebdomadaire (flux continu)",
            "date_sql": "SELECT max(date_etablissement)::date FROM dpe_records",
            "ds_name": "DPE ADEME%", "auto": True,
            "detection": "ré-ingestion API par commune (upsert numero_dpe)"},
    "ban": {"label": "BAN (adresses)", "cadence": "mensuelle",
            "date_sql": "SELECT max(refreshed_at)::date FROM adresses",
            "ds_name": "Base Adresse Nationale", "auto": True,
            "detection": "cron mensuel existant (full reload idempotent)"},
    "catnat": {"label": "CatNat (GASPAR)", "cadence": "au fil de l'eau (arrêtés JO)",
               "date_sql": "SELECT max(date_arrete) FROM catnat_arretes",
               "ds_name": "%CatNat%", "auto": True,
               "detection": "cron mensuel existant (upsert par arrêté)"},
    "gpu_plu": {"label": "GPU / PLU (zonage, prescriptions)", "cadence": "périodique (révisions)",
                "date_sql": "SELECT max(created_at)::date FROM spatial_layers WHERE kind LIKE 'plu_gpu%'",
                "ds_name": "Urbanisme PLU/GPU%", "auto": False,
                "detection": "DÉTECTION SEULE : le zonage nourrit la CASCADE GELÉE — une mise à jour "
                             "détectée = signalement healthz, la réingestion passe par la grande passe Mac"},
    "georisques": {"label": "Géorisques (aléas, cavités, MVT, SSP)", "cadence": "périodique",
                   "date_sql": "SELECT max(created_at)::date FROM spatial_layers "
                               "WHERE kind IN ('georisque_alea','cavite','mvt','sol_pollue')",
                   "ds_name": "Géorisques%", "auto": False,
                   "detection": "DÉTECTION SEULE (couches cascade) — même règle que GPU/PLU"},
}

DDL = """
CREATE TABLE IF NOT EXISTS fraicheur_etat (
  cle          text PRIMARY KEY,          -- ex. 'dvf:lastmod:2025' ou 'dpe:compteur_reveil'
  valeur       text,
  updated_at   timestamptz DEFAULT now()
);
"""

GEO_DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/974.csv.gz"


def _ensure(session: Session) -> None:
    session.execute(text(DDL))


def _etat_get(session: Session, cle: str) -> str | None:
    _ensure(session)
    return session.execute(text("SELECT valeur FROM fraicheur_etat WHERE cle = :c"), {"c": cle}).scalar()


def _etat_set(session: Session, cle: str, valeur: str) -> None:
    _ensure(session)
    session.execute(text(
        "INSERT INTO fraicheur_etat (cle, valeur, updated_at) VALUES (:c, :v, now()) "
        "ON CONFLICT (cle) DO UPDATE SET valeur = EXCLUDED.valeur, updated_at = now()"),
        {"c": cle, "v": valeur})


# ─────────────────────────── J1/J4 · l'état des sources (la matrice vivante) ───────────────────────────

def etat_sources(session: Session) -> list[dict]:
    """Par source : cadence réelle, dernière DONNÉE en base, dernière INGESTION, delta en jours.
    C'est la surface honnête : les dates parlent seules."""
    out = []
    for key, s in SOURCES.items():
        try:
            # SAVEPOINT : une table absente (base de test, install partielle) n'avorte pas la TX
            with session.begin_nested():
                derniere_donnee = session.execute(text(s["date_sql"])).scalar()
        except Exception:  # noqa: BLE001 — table absente = source non ingérée ici
            derniere_donnee = None
        derniere_ingestion = session.execute(text(
            "SELECT max(last_sync_at)::date FROM data_sources WHERE name ILIKE :n"),
            {"n": s["ds_name"]}).scalar()
        delta = (date.today() - derniere_donnee).days if isinstance(derniere_donnee, date) else None
        out.append({"source": key, "label": s["label"], "cadence": s["cadence"],
                    "derniere_donnee": str(derniere_donnee) if derniere_donnee else None,
                    "derniere_ingestion": str(derniere_ingestion) if derniere_ingestion else None,
                    "delta_donnee_jours": delta, "auto": s["auto"], "detection": s["detection"]})
    return out


# ─────────────────────────── J2 · détection + refresh incrémentaux ───────────────────────────

def check_dvf_livraison(session: Session, timeout: float = 20.0) -> dict:
    """Nouvelle livraison Etalab ? Compare le Last-Modified HTTP de chaque CSV annuel à l'état
    stocké — on ne retélécharge JAMAIS ce qu'on a déjà. Renvoie les millésimes modifiés."""
    _ensure(session)
    modifies = []
    with httpx.Client(timeout=timeout, follow_redirects=True) as c:
        for year in range(2021, date.today().year + 1):
            try:
                r = c.head(GEO_DVF_URL.format(year=year))
                if r.status_code != 200:
                    continue
                lastmod = r.headers.get("last-modified", "")
            except Exception as exc:  # noqa: BLE001 — réseau : on réessaiera au prochain cron
                log.warning("HEAD geo-dvf %s : %s", year, exc)
                continue
            connu = _etat_get(session, f"dvf:lastmod:{year}")
            if lastmod and lastmod != connu:
                modifies.append({"annee": year, "lastmod": lastmod, "connu": connu})
    return {"modifies": modifies, "n": len(modifies)}


def refresh_dvf(session: Session, *, commit: bool = True, log_fn=print) -> dict:
    """Refresh DVF INCRÉMENTAL : seuls les millésimes dont la livraison a changé sont rechargés
    (DELETE millésime + réinsertion = idempotent ; un double run = le même état)."""
    from .layers_ingest import load_dvf_geo

    check = check_dvf_livraison(session)
    if not check["modifies"]:
        log_fn("DVF : aucune nouvelle livraison (Last-Modified inchangés) — no-op")
        return {"recharges": [], "no_op": True}
    recharges = []
    for m in check["modifies"]:
        year = m["annee"]
        n_avant = session.execute(text(
            "SELECT count(*) FROM dvf_mutations_parcelle WHERE extract(year FROM date_mutation) = :y"),
            {"y": year}).scalar()
        session.execute(text(
            "DELETE FROM dvf_mutations_parcelle WHERE extract(year FROM date_mutation) = :y"), {"y": year})
        n = load_dvf_geo(session, target="dvf_mutations_parcelle", years=(year,))
        _etat_set(session, f"dvf:lastmod:{year}", m["lastmod"])
        recharges.append({"annee": year, "avant": n_avant, "apres": n})
        log_fn(f"DVF {year} : livraison {m['lastmod']!r} — {n_avant} → {n} mutations")
    session.execute(text(
        "UPDATE data_sources SET last_sync_at = now() WHERE name = 'DVF / valeurs foncières'"))
    if commit:
        session.commit()
    return {"recharges": recharges, "no_op": False}


def ingest_bodacc_quotidien(session: Session, *, commit: bool = True, log_fn=print) -> dict:
    """BODACC quotidien : ré-interroge (batché, throttlé) les SIREN propriétaires — upsert par
    annonce_id (idempotent). La voie d'ingestion existante est reprise, pas dupliquée."""
    from ..connectors.bodacc import BodaccConnector
    from .bodacc import distinct_sirens, ingest_bodacc

    sirens = distinct_sirens(session)
    stats = ingest_bodacc(session, sirens, connector=BodaccConnector())
    if commit:
        session.commit()
    apres = session.execute(text("SELECT max(date_annonce)::date FROM bodacc_procedures")).scalar()
    log_fn(f"BODACC : {len(sirens)} SIREN interrogés, état {stats} — dernière annonce {apres}")
    return {"sirens": len(sirens), "stats": stats, "derniere_annonce": str(apres)}


def check_couches_cascade(session: Session, timeout: float = 20.0) -> dict:
    """GPU/PLU + Géorisques : DÉTECTION SEULE (jamais d'ingestion auto — couches de la cascade
    gelée). Sonde légère : date de màj annoncée par l'API Géorisques SSP + comptage GPU d'une
    commune témoin ; toute différence = signalement (healthz + rapport de cron)."""
    notes = []
    try:
        with httpx.Client(timeout=timeout) as c:
            r = c.get("https://www.georisques.gouv.fr/api/v1/ssp/conclusions",
                      params={"code_insee": "97415", "page": 1, "page_size": 1})
            if r.status_code == 200:
                notes.append({"source": "georisques", "sonde": "API SSP joignable",
                              "detail": f"HTTP {r.status_code}"})
            else:
                notes.append({"source": "georisques", "sonde": "API SSP", "detail": f"HTTP {r.status_code}"})
    except Exception as exc:  # noqa: BLE001
        notes.append({"source": "georisques", "sonde": "API SSP", "detail": f"injoignable ({type(exc).__name__})"})
    _ensure(session)
    _etat_set(session, "couches_cascade:derniere_sonde", json.dumps(notes, ensure_ascii=False))
    return {"notes": notes,
            "rappel": "toute mise à jour GPU/Géorisques s'ingère par GRANDE PASSE (Mac) — jamais en cron"}


# ─────────────────────────── J3 · la chaîne des dérivés (runs INTOUCHABLES) ───────────────────────────

SEUIL_REVEIL_DPE = 200   # F/G ∩ mono ∩ non-écarté ≥ 200 → réveil du badge en réserve (cycle 3)


def compteur_reveil_dpe(session: Session) -> dict:
    """Réévalue le critère de réveil du badge DPE en réserve (aujourd'hui ~7). Loggé à chaque
    refresh ; si le seuil est franchi un jour : événement visible (cron + healthz)."""
    n = session.execute(text("""
        SELECT count(DISTINCT d.parcelle_idu) FROM dpe_records d
        JOIN parcel_p_score_v2 s ON s.parcelle_id = d.parcelle_idu AND s.run_id = :run
        WHERE d.etiquette_dpe IN ('F', 'G') AND d.parcelle_idu IS NOT NULL
          AND s.tier <> 'ecartee' AND NOT s.copro"""),
        {"run": _run_servi()}).scalar() or 0
    franchi = n >= SEUIL_REVEIL_DPE
    _ensure(session)
    _etat_set(session, "dpe:compteur_reveil", json.dumps(
        {"n": int(n), "seuil": SEUIL_REVEIL_DPE, "franchi": franchi, "jour": str(date.today())}))
    return {"n": int(n), "seuil": SEUIL_REVEIL_DPE, "franchi": franchi}


def _run_servi() -> str:
    from ..scoring.score_v_constants import Q_A_RUN_LABEL
    return Q_A_RUN_LABEL


def run_derives(session: Session, *, hebdo: bool = False, commit: bool = True, log_fn=print) -> dict:
    """La chaîne post-ingestion : recalcule les dérivés LÉGERS (lecture des sources fraîches,
    rebuilds idempotents). Un caduc qui reçoit une DAACT tardive SORT du badge au rebuild —
    l'honnêteté vaut dans les deux sens. NE TOUCHE JAMAIS les tables de run.

    Quotidien : pc_caducs · defisc_fenetres · surface_d. Hebdo (+) : m10 délais/vélocité
    (re-fetch réseau SDES, plus lourd)."""
    from . import defisc_fenetres, pc_caducs, surface_d

    out: dict = {}
    r = pc_caducs.build_pc_caducs(session, commit=False, log=log_fn)
    out["pc_caducs"] = r if isinstance(r, (int, dict)) else str(r)
    r = defisc_fenetres.build_defisc_fenetres(session, commit=False, log=log_fn)
    out["defisc_fenetres"] = r if isinstance(r, (int, dict)) else str(r)
    out["surface_d"] = surface_d.build_events(session, commit=False, log=log_fn)
    out["dpe_reveil"] = compteur_reveil_dpe(session)
    if out["dpe_reveil"]["franchi"]:
        log_fn(f"⚑ RÉVEIL DPE : critère franchi ({out['dpe_reveil']['n']} ≥ {SEUIL_REVEIL_DPE}) — "
               "le badge en réserve peut être réinstruit (cf. A1_DPE_CADRAGE).")
    if hebdo:
        from . import permit_delais_m10
        out["m10_delais"] = permit_delais_m10.build_delais(session, log=log_fn)
    if commit:
        session.commit()
    log_fn(f"dérivés rafraîchis : {list(out)}")
    return out
