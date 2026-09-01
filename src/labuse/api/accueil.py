"""M55-D stage 9 — /accueil/chiffres : les chiffres PROUVÉS de la page d'accueil.

AUCUN chiffre en dur (doctrine) : tout est MESURÉ en base ou lu d'un artefact versionné
(golden), agrégé ici et mis en cache 1 h (les requêtes lourdes — dataset d'entraînement,
ensembles fonciers, bascules — ne coûtent qu'une fois par heure). Un chiffre introuvable
vaut null : le front le masque, il ne l'invente pas.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import sources_catalog as _srccat
from ..scoring.score_v_constants import Q_A_RUN_LABEL, RUN_PRECEDENT

router = APIRouter(tags=["accueil"])

# M80 — RUN_PRECEDENT n'est PLUS codé en dur ici : il est lu de config/run_precedent.txt (point de
# vérité versionné, même mécanisme que served_run.txt), importé depuis score_v_constants. Un nom de
# run hardcodé rendait la purge dangereuse (et c'était un chiffre en dur, interdit par la doctrine).
# Le diff des tiers entre les deux runs SERVIS successifs reste TOUJOURS calculé, jamais figé.

#: fenêtre d'entraînement du modèle SERVI (m36-l2f — cf. /v2/modele provenance.train)
TRAIN_ANNEES = (2017, 2024)

_cache: dict = {"at": 0.0, "data": None}
_CACHE_TTL_S = 3600


def get_db():
    from .app import get_db as _g
    yield from _g()


def _golden_counts() -> tuple[int | None, int | None]:
    """(parcelles, vérifications) du golden versionné — null si le fichier n'est pas déployé."""
    for base in (Path(__file__).resolve().parents[3], Path.cwd()):
        f = base / "reports" / "m6-audit" / "golden" / "golden-parcelles.json"
        if f.exists():
            try:
                d = json.loads(f.read_text())
                parcelles = d if isinstance(d, list) else d.get("parcelles", d)
                n = len(parcelles)
                items = parcelles if isinstance(parcelles, list) else list(parcelles.values())
                verifs = sum(len(p.get("champs", p)) if isinstance(p, dict) else 0 for p in items)
                return n, verifs or None
            except Exception:  # noqa: BLE001 — un golden illisible ne casse pas l'accueil
                return None, None
    return None, None


@router.get("/accueil/chiffres")
def accueil_chiffres(db: Session = Depends(get_db)) -> dict:
    now = time.time()
    if _cache["data"] is not None and now - _cache["at"] < _CACHE_TTL_S:
        return _cache["data"]

    def one(sql: str, params: dict | None = None) -> int | None:
        try:
            v = db.execute(text(sql), params or {}).scalar()
            return int(v) if v is not None else None
        except Exception:  # noqa: BLE001 — un chiffre indisponible = null, jamais une invention
            return None

    golden_parcelles, golden_verifs = _golden_counts()
    data = {
        # ── bloc 1 · « Je couvre tout » ──
        "parcelles": one("SELECT count(*) FROM parcel_p_score_v2 WHERE run_id = :r", {"r": Q_A_RUN_LABEL}),
        "communes": one("SELECT count(DISTINCT commune) FROM parcels"),
        # M71 F / M87 P0 : UN SEUL chiffre partout — définition CANONIQUE des sources affichées
        # (`sources_catalog.WHERE_AFFICHEES` : connecte, hors DOUBLON, hors masquées). accueil ET
        # /sources lisent d'ici. Dynamique, aucun chiffre en dur. (Office de l'eau masquée → 50.)
        "sources": one(f"SELECT count(*) FROM data_sources WHERE {_srccat.WHERE_AFFICHEES}",
                       {"masquees": _srccat.masquees_param()}),
        # ── bloc 2 · « Je ne devine pas » ──
        "ventes_train": one(
            "SELECT count(*) FROM p_model_ext_dataset WHERE label_l2 = 1 AND annee BETWEEN :a AND :b",
            {"a": TRAIN_ANNEES[0], "b": TRAIN_ANNEES[1]}),
        "communes_calibrees": one(
            "SELECT count(*) FROM (SELECT p.commune FROM parcels p JOIN parcel_zone_plu z USING (idu) "
            "GROUP BY p.commune HAVING count(*) >= 100) t"),
        "golden_parcelles": golden_parcelles,
        "golden_verifs": golden_verifs,
        # ── bloc 3 · « Je vois ce que personne ne voit » ──
        "defisc_actives": one("SELECT count(*) FROM defisc_fenetres WHERE fenetre_active"),
        "permis_caducs": one("SELECT count(*) FROM pc_caducs"),
        "ensembles_fonciers": one(
            "SELECT count(*) FROM (SELECT siren FROM parcelle_personne_morale "
            "WHERE groupe = 0 AND siren IS NOT NULL GROUP BY siren "
            "HAVING count(DISTINCT idu) >= 3) t"),
        "bascules_tiers_hauts": one(
            "SELECT count(*) FROM parcel_p_score_v2 a "
            "JOIN parcel_p_score_v2 b ON b.parcelle_id = a.parcelle_id AND b.run_id = :cur "
            "WHERE a.run_id = :prev AND b.tier IN ('brulante','chaude') "
            "  AND (a.tier IS NULL OR a.tier NOT IN ('brulante','chaude'))",
            {"cur": Q_A_RUN_LABEL, "prev": RUN_PRECEDENT}),
        "run_label": Q_A_RUN_LABEL,
    }
    _cache.update(at=now, data=data)
    return data


_cs_cache: dict = {"at": 0.0, "data": None}


@router.get("/accueil/cette-semaine")
def accueil_cette_semaine(db: Session = Depends(get_db)) -> dict:
    """B4 (M83) — trois signaux d'activité, MESURÉS en base. Doctrine « un zéro n'est pas une
    absence » : si une source est en retard d'ingestion, on le DIT (fraîcheur + dernière donnée)
    plutôt qu'un zéro trompeur. DVF n'a PAS de date de publication en base (seul date_mutation) : la
    fraîcheur se lit sur le dernier trimestre RÉEL (≥ 50 ventes), jamais sur un enregistrement isolé.
    Cache court (5 min) — requête légère."""
    now = time.time()
    if _cs_cache["data"] is not None and now - _cs_cache["at"] < 300:
        return _cs_cache["data"]

    def scal(sql: str, params: dict | None = None):
        try:
            return db.execute(text(sql), params or {}).scalar()
        except Exception:  # noqa: BLE001
            return None

    permis_7j = scal("SELECT count(*) FROM sitadel_permits WHERE date_depot > now()::date - 7")
    permis_30j = scal("SELECT count(*) FROM sitadel_permits WHERE date_depot > now()::date - 30") or 0
    permis_max = scal("SELECT max(date_depot) FROM sitadel_permits")

    ventes_7j = scal("SELECT count(*) FROM dvf_mutations WHERE date_mutation > now()::date - 7")
    ventes_30j = scal("SELECT count(*) FROM dvf_mutations WHERE date_mutation > now()::date - 30") or 0
    ventes_trim = scal(
        "SELECT to_char(max(q), 'YYYY\"T\"Q') FROM (SELECT date_trunc('quarter', date_mutation) AS q "
        "FROM dvf_mutations GROUP BY 1 HAVING count(*) >= 50) t")

    try:
        from .. import veille_plu
        communes_plu = sum(1 for e in veille_plu._registre().values() if veille_plu.procedure_active(e))
    except Exception:  # noqa: BLE001
        communes_plu = None

    data = {
        # frais = la source a bougé récemment (≥ un seuil d'activité sur 30 j) — sinon la ligne DIT la
        # dernière donnée au lieu d'un « 0 cette semaine » trompeur.
        "permis": {"n_7j": int(permis_7j or 0), "frais": permis_30j >= 10,
                   "derniere": str(permis_max)[:10] if permis_max else None},
        "ventes": {"n_7j": int(ventes_7j or 0), "frais": ventes_30j >= 20,
                   "dernier_trimestre": ventes_trim, "sans_date_publication": True},
        "communes_procedure_plu": communes_plu,
    }
    _cs_cache.update(at=now, data=data)
    return data


_fr_cache: dict = {"at": 0.0, "data": None}


@router.get("/accueil/fraicheur")
def accueil_fraicheur(db: Session = Depends(get_db)) -> dict:
    """CONNEXIONS-2 Lot 6.1 (KO-11) — la ligne de fraîcheur de l'accueil n'est plus un texte FIGÉ :
    elle est CALCULÉE depuis l'état RÉEL des sources (`data_sources.fraicheur_statut`, le MÊME champ
    que la page Sources et le dashboard). Phrase honnête : « Toutes les données sont à jour. » /
    « N sources en retard. » / « Une source en erreur. ». Cache court (5 min)."""
    now = time.time()
    if _fr_cache["data"] is not None and now - _fr_cache["at"] < 300:
        return _fr_cache["data"]

    counts = {"a_jour": 0, "en_retard": 0, "en_panne": 0, "en_erreur": 0, "sans_echeance": 0}
    total = 0
    try:
        # garde par existence de colonne : job jamais lancé / base de test → phrase « à jour » sûre.
        col_ok = db.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name='data_sources' "
            "AND column_name='fraicheur_statut'")).first()
        if col_ok:
            rows = db.execute(text(
                f"SELECT COALESCE(fraicheur_statut, 'a_jour') AS st, count(*) AS n "
                f"FROM data_sources WHERE {_srccat.WHERE_AFFICHEES} GROUP BY 1"),
                {"masquees": _srccat.masquees_param()}).mappings().all()
            for r in rows:
                total += int(r["n"])
                counts[r["st"]] = counts.get(r["st"], 0) + int(r["n"])
    except Exception:  # noqa: BLE001 — la ligne d'accueil ne casse jamais la page
        pass

    en_erreur = counts.get("en_erreur", 0)
    en_retard = counts.get("en_retard", 0) + counts.get("en_panne", 0)
    if en_erreur:
        ton = "error"
        phrase = ("Une source en erreur." if en_erreur == 1 else f"{en_erreur} sources en erreur.")
    elif en_retard:
        ton = "warn"
        phrase = ("Une source en retard." if en_retard == 1 else f"{en_retard} sources en retard.")
    else:
        ton = "ok"
        phrase = "Toutes les données sont à jour."
    data = {"ton": ton, "phrase": phrase, "en_erreur": en_erreur, "en_retard": en_retard, "total": total}
    _fr_cache.update(at=now, data=data)
    return data
