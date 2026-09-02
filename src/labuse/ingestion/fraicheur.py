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
from contextlib import contextmanager
from datetime import date

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import runs  # S3 : run servi relu à la requête

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
                # M-R : cadence BORNABLE — SDES publie mensuellement, max(date) avance chaque mois
                # (permis fréquents sur l'île). check_fraicheur peut donc l'évaluer (seuil 2×30 j).
                "cadence_norme": "mensuel",
                "detection": "refresh delta quotidien (recouvrement 3 mois) — no-op si rien de neuf"},
    "bodacc": {"label": "BODACC (procédures collectives)", "cadence": "quotidienne",
               "date_sql": "SELECT max(date_annonce)::date FROM bodacc_procedures",
               "ds_name": "BODACC%", "auto": True,
               # M-R : PAS de cadence_norme — VÉRIFIÉ : l'horizon = max(date_annonce) parmi les SEULS
               # propriétaires suivis (~12,6k SIREN), donc des ÉVÉNEMENTS RARES (mesuré : ~37 j
               # d'ancienneté normale). Un seuil « quotidien » alarmerait en permanence sur une
               # absence d'événement, pas sur une donnée périmée → non bornable (event-driven).
               "detection": "re-interrogation batchée des 12,6k SIREN propriétaires (upsert annonce_id)"},
    "dvf": {"label": "DVF (mutations, Etalab geo-dvf)", "cadence": "semestrielle (avril / octobre)",
            "date_sql": "SELECT max(date_mutation)::date FROM dvf_mutations_parcelle",
            "ds_name": "DVF / valeurs foncières", "auto": True,
            # M32 Phase B §2 : millésime amont (vague 1 = DVF). `cadence_norme` = token servi ;
            # `prochain` = prochaine livraison géo-DVF (S1-2026 en octobre) ; `millesime` = édition
            # fournisseur (texte normé). L'horizon (max date_mutation) est CALCULÉ, pas figé ici.
            "cadence_norme": "semestriel", "prochain": "2026-10-01",
            # M124 — la profondeur DIT les deux canaux : prod geo-DVF 2021+ ET archives brutes
            # DGFiP 2014-2020 (dvf_mutations_histo, miroir cquest, Licence Ouverte).
            "millesime": "géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020",
            "detection": "Last-Modified HTTP des CSV annuels — reload du millésime modifié uniquement"},
    "dpe": {"label": "DPE ADEME (logements existants)", "cadence": "hebdomadaire (flux continu)",
            "date_sql": "SELECT max(date_etablissement)::date FROM dpe_records",
            "ds_name": "DPE ADEME%", "auto": True,
            # M-R : cadence BORNABLE — flux ADEME continu, max(date_etablissement) avance chaque
            # semaine ; check_fraicheur l'évalue (seuil 2×7 j) et alerte si l'ingestion prend du retard.
            "cadence_norme": "hebdomadaire",
            "detection": "ré-ingestion API par commune (upsert numero_dpe)"},
    "ban": {"label": "BAN (adresses)", "cadence": "mensuelle",
            "date_sql": "SELECT max(refreshed_at)::date FROM adresses",
            "ds_name": "Base Adresse Nationale", "auto": True,
            # M-R : cadence BORNABLE — full reload mensuel, max(refreshed_at) avance chaque mois.
            "cadence_norme": "mensuel",
            "detection": "cron mensuel existant (full reload idempotent)"},
    "catnat": {"label": "CatNat (GASPAR)", "cadence": "au fil de l'eau (arrêtés JO)",
               "date_sql": "SELECT max(date_arrete) FROM catnat_arretes",
               "ds_name": "%CatNat%", "auto": True,
               "detection": "cron mensuel existant (upsert par arrêté)"},
    "gpu_plu": {"label": "GPU / PLU (zonage, prescriptions)", "cadence": "périodique (révisions)",
                "date_sql": "SELECT max(created_at)::date FROM spatial_layers WHERE kind LIKE 'plu_gpu%'",
                "ds_name": "Urbanisme PLU/GPU%", "auto": False,
                # M32 §2 : millésime amont du zonage. `cadence_norme` VOLONTAIREMENT absente (révisions
                # irrégulières, pas de fréquence → check_fraicheur ne l'évalue pas). Fraîcheur FINE =
                # par commune (config/plu_millesimes.yaml, servie en fiche via _plu_fraicheur).
                "millesime": "GPU/PLU par commune (révisions — détail en fiche)",
                "prochain": None,
                "detection": "DÉTECTION SEULE : le zonage nourrit la CASCADE GELÉE — une mise à jour "
                             "détectée = signalement healthz, la réingestion passe par la grande passe Mac"},
    "georisques": {"label": "Géorisques (aléas, cavités, MVT, SSP)", "cadence": "périodique",
                   "date_sql": "SELECT max(created_at)::date FROM spatial_layers "
                               "WHERE kind IN ('georisque_alea','cavite','mvt','sol_pollue')",
                   "ds_name": "Géorisques%", "auto": False,
                   "detection": "DÉTECTION SEULE (couches cascade) — même règle que GPU/PLU"},
    "sudocuh": {"label": "Sudocuh (suivi des procédures d'urbanisme)", "cadence": "annuelle (état au 31/12)",
                "date_sql": "SELECT max(millesime_date)::date FROM sudocuh_procedures",
                "ds_name": "Sudocuh%", "auto": False,
                # M41 (radar procédures PLU) : squelette du radar. `cadence_norme` VOLONTAIREMENT absente
                # (comme gpu_plu) → check_fraicheur ne l'ALARME PAS : un Sudocuh d'un an n'est pas une
                # faute (le registre curaté config/veille_plu.yaml est la chair servie, rafraîchi
                # trimestriellement — geste scripts/veille_plu_check.py). Horizon = l'état daté (31/12).
                "millesime": "Sudocuh — état au 31/12/2024 (Licence Ouverte 2.0)",
                "prochain": None,
                "detection": "DÉTECTION SEULE : publication annuelle data.gouv.fr ; le radar servi vient "
                             "du registre curaté, pas d'un ingest automatique. Re-vérif = geste trimestriel."},
    "ortho_piscine": {"label": "BD ORTHO 20 cm (IGN) — millésime imagerie (piscine/PV/pente)",
                      "cadence": "pluriannuelle (re-survol ~3-4 ans)",
                      "date_sql": "SELECT to_date(max(millesime),'YYYY')::date FROM ortho_tiles "
                                  "WHERE millesime ~ '^[0-9]{4}$'",
                      "ds_name": "BD ORTHO 20 cm (IGN)", "auto": False,
                      # M39 (dette #13) : millésime AMONT de la couche piscine — l'âge de l'image
                      # EST l'âge du signal. `cadence_norme` VOLONTAIREMENT absente (re-survol
                      # irrégulier ~3-4 ans → check_fraicheur ne l'évalue pas, comme gpu_plu : un
                      # signal à 3 ans ne doit pas déclencher d'alerte de retard). Horizon = ANNÉE du
                      # millésime (précision de prise de vue non publiée → jamais inventée, A1).
                      "millesime": "BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %)",
                      "prochain": None,
                      "detection": "DÉTECTION SEULE : re-survol IGN ~3-4 ans → commande --refresh "
                                   "(wave-ortho Lot 7), jamais un cron ; la couche nourrit une RÈGLE "
                                   "produit (piscine_signal), pas la cascade gelée."},
    "cosia": {"label": "CoSIA (couverture du sol IA, IGN) — bâti vectorisé (PAU RNU)",
              "cadence": "pluriannuelle (re-survol imagerie ~3-4 ans)",
              # horizon = fait amont daté (editionDate du lot), porté au catalogue à l'ingestion
              "date_sql": "SELECT source_horizon_at FROM data_sources "
                          "WHERE name = 'CoSIA (couverture du sol IA, IGN)'",
              "ds_name": "CoSIA (couverture du sol IA, IGN)", "auto": False,
              # `cadence_norme` VOLONTAIREMENT absente (re-survol irrégulier → pas d'alerte de retard,
              # comme ortho_piscine/gpu_plu). La couche nourrit le recalcul PAU, pas la cascade gelée.
              "millesime": "CoSIA 2025 (PVA juil.-août 2025, 20 cm)",
              "prochain": None,
              "detection": "DÉTECTION SEULE : re-survol IGN ~3-4 ans → commande `labuse ingest-cosia` "
                           "après re-téléchargement du lot D974, jamais un cron."},
}

# M-O P1-14 — noms EXACTS de `data_sources` par source, pour l'ÉCRITURE du millésime. Les patterns
# `%` de `ds_name` faisaient du fan-out : `Géorisques%` matchait 5 lignes (Géorisques, ICPE, cavités,
# MVT, sols pollués) → le MÊME `source_horizon_at` écrit à 5 sources dont plusieurs sans rapport avec
# les kinds mesurés. persist_millesime n'écrit désormais QUE ces lignes-là. Liste vide = aucune ligne
# catalogue dédiée (l'ancien `%CatNat%` matchait 0 : no-op conservé, explicitement). `ds_name` (motif)
# reste pour les LECTEURS (etat_sources, page Sources) — ce n'est pas lui qui écrivait le mauvais horizon.
DS_NAMES: dict[str, list[str]] = {
    "sitadel": ["SITADEL (autorisations d'urbanisme)"],
    "bodacc": ["BODACC (procédures collectives)"],
    "dvf": ["DVF / valeurs foncières"],
    "dpe": ["DPE ADEME (logements existants)"],
    "ban": ["Base Adresse Nationale"],
    "catnat": [],   # aucune ligne data_sources dédiée (ancien '%CatNat%' → 0 ligne : no-op explicite)
    "gpu_plu": ["Urbanisme PLU/GPU (API Carto)"],
    "georisques": ["Géorisques", "Géorisques — ICPE", "Géorisques — cavités souterraines",
                   "Géorisques — mouvements de terrain", "Géorisques — sites et sols pollués"],
    "sudocuh": ["Sudocuh (procédures d'urbanisme)"],
    "ortho_piscine": ["BD ORTHO 20 cm (IGN)"],
    "cosia": ["CoSIA (couverture du sol IA, IGN)"],
}

# M-O P1-14 — sources dont le `date_sql` lit max(created_at) de `spatial_layers` = la DATE
# D'INGESTION LABUSE, PAS un fait daté amont → `source_horizon_at` NULL (« horizon inconnu » servi
# tel quel). Doctrine : fraîcheur = date SOURCE amont, jamais date d'ingestion. Les autres `date_sql`
# lisent un vrai fait amont (max date_mutation / date_annonce / millesime…).
HORIZON_NON_AMONT = frozenset({"gpu_plu", "georisques"})

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
                    "delta_donnee_jours": delta, "seuil_jours": seuil_jours(key),
                    "statut": statut_fraicheur(key, delta),   # M84 — verdict live (anti-faux-positif)
                    "auto": s["auto"], "detection": s["detection"]})
    return out


# ─────────────── M84 · le SEUIL de fraîcheur, dérivé de la cadence (source unique de vérité) ───────────────
# La promesse du module — « jamais en retard de plus de 2× la cadence sur la DERNIÈRE PUBLICATION » —
# repose sur UN seuil, jamais un chiffre arbitraire : il se dérive de la cadence RÉELLE de chaque source
# (`cadence_norme`, déjà dans la matrice). Une source SANS cadence bornable (event-driven, annuelle,
# révisions irrégulières, re-survol pluriannuel) ne PEUT PAS être en retard — c'est le piège du faux
# positif (DVF semestriel à 226 j, SITADEL à 45 j, Sudocuh à un an) qu'on REFUSE de réintroduire.
# M84 : ce seuil est désormais l'UNIQUE référence — la garde de rebuild (`bascule_gardes.check_fraicheur`)
# l'importe d'ici, et le statut LIVE de la page Sources en découle. Deux surfaces, un seul seuil.

CADENCE_JOURS = {"hebdomadaire": 7, "hebdo": 7, "mensuel": 30, "trimestriel": 91,
                 "semestriel": 182, "annuel": 365}
SEUIL_FACTEUR = 2   # 2× la cadence : la marge d'UN cycle de publication manqué avant de crier au retard


def seuil_jours(source_key: str) -> int | None:
    """Seuil de retard d'une source = SEUIL_FACTEUR × sa cadence normée (en jours). None si la source
    n'a pas de cadence bornable → elle ne PEUT PAS être déclarée « en retard » (anti-faux-positif)."""
    base = CADENCE_JOURS.get((SOURCES.get(source_key, {}).get("cadence_norme") or "").lower())
    return int(base * SEUIL_FACTEUR) if base else None


def statut_fraicheur(source_key: str, delta_jours: int | None) -> str:
    """Verdict LIVE d'une source, du delta observé (max(date) en base) au seuil dérivé de sa cadence :
      • `en_retard`     — delta > seuil (2× cadence) : décrochage RÉEL, à voir et corriger ;
      • `a_jour`        — delta ≤ seuil : frais pour sa cadence (SITADEL 45 j < 60 j, DVF 226 j < 360 j) ;
      • `cadence_libre` — pas de cadence bornable → JAMAIS une alerte (event-driven / annuel / révisions) ;
      • `sans_donnee`   — aucune donnée datée en base.
    Cohérent AVEC la date affichée (`derniere_donnee`) : même delta, même source de vérité."""
    seuil = seuil_jours(source_key)
    if seuil is None:
        return "cadence_libre"
    if delta_jours is None:
        return "sans_donnee"
    return "en_retard" if delta_jours > seuil else "a_jour"


def retards_live(session: Session) -> list[dict]:
    """Les sources RÉELLEMENT en retard (statut live `en_retard`). Vide = tout est frais pour sa cadence.
    Lue par la sentinelle (CLI `check-fraicheur`, code de sortie) : un décrochage y est visible en un
    GET / une commande, jamais découvert en ratant une opportunité. L'alerte qui manquait aux surfaces."""
    return [e for e in etat_sources(session) if e["statut"] == "en_retard"]


# ─────────────── M84 · trace_ingestion : toute ingestion LAISSE UNE TRACE (échec compris) ───────────────

@contextmanager
def trace_ingestion(session: Session, label: str, ds_names: list[str] | None = None):
    """Journalise TOUTE ingestion dans `ingestion_runs` (running → ok | error). bodacc/dpe/georisques
    n'y laissaient AUCUNE trace : un échec y était donc INVISIBLE — le défaut de fond de M84 (une source
    peut décrocher six semaines en silence). Désormais un échec est ÉCRIT (status='error') PUIS remonté
    (jamais avalé) ; un succès pose aussi `data_sources.last_sync_at` (cohérence avec /healthz/crons).
    La trace est committée à part pour survivre à un rollback de l'ingestion elle-même."""
    rid = session.execute(text(
        "INSERT INTO ingestion_runs (commune, status) VALUES (:c, 'running') RETURNING id"),
        {"c": label}).scalar()
    session.commit()
    try:
        yield rid
    except Exception:
        session.rollback()
        session.execute(text(
            "UPDATE ingestion_runs SET finished_at = now(), status = 'error' WHERE id = :id"), {"id": rid})
        # M85 — un échec d'ingestion PRODUIT une notification systeme (pilote/admin, hors marché) :
        # visible à la cloche, pas seulement dans un log. Import paresseux (ingestion→api) + jamais
        # bloquant : une notif défaillante ne masque PAS l'échec d'origine (motif M84).
        try:
            from ..api.events import creer_notification
            creer_notification(session, kind="systeme", compte_id=None, source=f"Ingestion · {label}",
                               titre=f"Échec d'ingestion — {label}", lien="/sources",
                               detail="La trace ingestion_runs est passée en 'error'. Rejeu à vérifier.",
                               dedup=f"ingest-echec:{label}")
        except Exception:  # noqa: BLE001 — la notification ne doit JAMAIS empêcher la remontée de l'échec
            pass
        session.commit()
        raise
    session.execute(text(
        "UPDATE ingestion_runs SET finished_at = now(), status = 'ok' WHERE id = :id"), {"id": rid})
    if ds_names:
        session.execute(text(
            "UPDATE data_sources SET last_sync_at = now() WHERE name = ANY(:names)"), {"names": ds_names})
    session.commit()


# ─────────────────────── M32 Phase B §2 · millésime amont persisté (spec Vic) ───────────────────────

def persist_millesime(session: Session, only: str | None = None, *, commit: bool = True) -> list[dict]:
    """Écrit dans `data_sources` (colonnes M32) le millésime AMONT de chaque couche : l'HORIZON
    (fait le plus récent DANS la donnée, CALCULÉ via `date_sql`), la cadence normée, l'édition
    fournisseur et la prochaine livraison attendue. `only='dvf'` = découpable par couche (ordre Vic :
    DVF d'abord). Une couche sans horizon calculable aujourd'hui → `source_horizon_at` NULL =
    « horizon inconnu » servi tel quel (jamais inventé). À appeler par l'ingester de chaque couche."""
    rendu = []
    for key, s in SOURCES.items():
        if only and key != only:
            continue
        names = DS_NAMES.get(key, [])
        if key in HORIZON_NON_AMONT:
            horizon = None                       # date_sql = date d'ingestion → horizon amont inconnu (NULL)
        else:
            try:
                with session.begin_nested():
                    horizon = session.execute(text(s["date_sql"])).scalar()
            except Exception:  # noqa: BLE001 — table absente = horizon inconnu, pas une erreur
                horizon = None
            horizon = horizon if isinstance(horizon, date) else None   # normalise (jamais un datetime)
        if names:                                # noms EXACTS (plus de pattern % : aucun fan-out)
            session.execute(text(
                "UPDATE data_sources SET source_horizon_at = :h, source_cadence = :c, "
                "source_millesime = :m, prochain_millesime_at = :p, updated_at = now() "
                "WHERE name = ANY(:names)"),
                {"h": horizon, "c": s.get("cadence_norme"), "m": s.get("millesime"),
                 "p": s.get("prochain"), "names": names})
        rendu.append({"source": key, "ds_names": names, "horizon": str(horizon) if horizon else None,
                      "cadence": s.get("cadence_norme"), "millesime": s.get("millesime"),
                      "prochain": s.get("prochain")})
    if commit:
        session.commit()
    return rendu


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

    # M84 — trace ingestion_runs (running → ok | error) : un échec BODACC est désormais VISIBLE
    # (avant : aucune trace, décrochage silencieux). Le contexte gère aussi last_sync_at au succès.
    with trace_ingestion(session, "974 (BODACC quotidien)", DS_NAMES["bodacc"]):
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
    return runs.current()


def run_derives(session: Session, *, hebdo: bool = False, commit: bool = True, log_fn=print) -> dict:
    """La chaîne post-ingestion : recalcule les dérivés LÉGERS (lecture des sources fraîches,
    rebuilds idempotents). Un caduc qui reçoit une DAACT tardive SORT du badge au rebuild —
    l'honnêteté vaut dans les deux sens. NE TOUCHE JAMAIS les tables de run.

    Quotidien : pc_caducs · defisc_fenetres · surface_d. Hebdo (+) : m10 délais/vélocité
    (re-fetch réseau SDES, plus lourd)."""
    from . import defisc_fenetres, pc_caducs, surface_d

    # M-O P2-60 — chaque dérivé est COMMITÉ et ISOLÉ (contrat build_divisions : « une commune qui
    # casse est isolée, l'île continue »). Avant : un seul commit final → les verrous exclusifs des
    # cinq rebuilds s'accumulaient jusqu'au bout, et un échec de `surface_d` emportait pc_caducs +
    # defisc pourtant bons. L'ordre est EXPLICITE : surface_d lit defisc/pc_caducs, désormais
    # committés AVANT lui (plus de couplage d'ordre dans une transaction unique).
    # En mode transactionnel (commit=False, tests) on garde l'ancienne sémantique : une seule TX,
    # l'échec REMONTE (jamais masqué).
    out: dict = {}
    etapes = [
        ("pc_caducs", lambda: pc_caducs.build_pc_caducs(session, commit=commit, log=log_fn)),
        ("defisc_fenetres", lambda: defisc_fenetres.build_defisc_fenetres(session, commit=commit, log=log_fn)),
        ("surface_d", lambda: surface_d.build_events(session, commit=commit, log=log_fn)),
    ]
    for nom, fn in etapes:
        try:
            r = fn()
            out[nom] = r if isinstance(r, (int, dict)) else str(r)
        except Exception as exc:  # noqa: BLE001 — dérivé isolé : les précédents (committés) sont saufs
            if not commit:
                raise                                  # tests (TX unique) : ne pas masquer l'échec
            session.rollback()
            out[nom] = {"erreur": f"{type(exc).__name__}: {exc}"}
            log_fn(f"⚠ dérivé {nom} ÉCHOUÉ (isolé — les précédents sont conservés) : {exc}")
    out["dpe_reveil"] = compteur_reveil_dpe(session)
    if out["dpe_reveil"]["franchi"]:
        log_fn(f"⚑ RÉVEIL DPE : critère franchi ({out['dpe_reveil']['n']} ≥ {SEUIL_REVEIL_DPE}) — "
               "le badge en réserve peut être réinstruit (cf. A1_DPE_CADRAGE).")
    if hebdo:
        from . import permit_delais_m10
        try:
            out["m10_delais"] = permit_delais_m10.build_delais(session, log=log_fn)
        except Exception as exc:  # noqa: BLE001 — hebdo réseau (SDES) : isolé comme les autres
            if not commit:
                raise
            session.rollback()
            out["m10_delais"] = {"erreur": f"{type(exc).__name__}: {exc}"}
            log_fn(f"⚠ dérivé m10_delais ÉCHOUÉ (isolé) : {exc}")
    if commit:
        session.commit()                               # dpe_reveil (fraicheur_etat) + reliquat éventuel
    log_fn(f"dérivés rafraîchis : {list(out)}")
    return out
