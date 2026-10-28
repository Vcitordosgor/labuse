"""O6 — COMPARATEUR DE COMMUNES : « où investir ? » un tableau, une ligne par commune.

Agrège des indicateurs DÉJÀ en base (zéro donnée nouvelle), un par colonne, chacun Sourcé/Estimé :
  · stock d'opportunités (parcelles brûlantes + chaudes du run servi) ;
  · vélocité administrative (délai médian dépôt→autorisation des permis logements, m10) ;
  · dynamisme permis (SITADEL, 24 derniers mois) ;
  · déficit SRU (écart objectif − taux LLS, DHUP) ;
  · pression ZAN (ENAF consommé 2021-2024, Cerema) ;
  · prix de sortie neuf (DVF, niveau commune).

Le classement composite est une **commodité, pas un score calibré** : la pondération est **présentée,
réglable** (query params) et **documentée** ; chaque indicateur est normalisé min-max [0-100] avec sa
direction (plus haut = « mieux pour investir »). Tout est labellisé ; une commune sans donnée sur un axe
reste `null` (jamais 0 trompeur) et l'axe est ignoré dans SON composite (renormalisation des poids présents).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import runs
# communes-tableau — le « €/m² ancien » vient de la MÊME source que le Baromètre (DVF ventes strictes,
# toutes mutations) : on réutilise le filtre de retenue du baromètre, point de vérité unique.
from .moteurs import prix_ancien_communes
# CIRCUIT-2 lot 1.6 — les calculs (SQL des indicateurs + composite) vivent au moteur nommé
# `commune_compteurs` (registre/moteurs/commune.py) : ce robinet ne calcule plus, il appelle.
# INDICATEURS y vit aussi (ré-importé ici pour les lecteurs existants — même objet, pas une copie).
from ..registre.moteurs.commune import INDICATEURS, composite_communes, indicateurs_communes

#: alias rétro-compatible (tests, lecteurs historiques) — la MÊME fonction, jamais une copie.
_normalize = composite_communes

log = logging.getLogger("labuse.comparateur")
router = APIRouter(prefix="/comparateur-communes", tags=["comparateur-communes"])


def get_db():
    from .app import get_db as _g
    yield from _g()


def _compute_raw(db: Session) -> dict[str, dict]:
    """Le CALCUL réel des indicateurs bruts par commune (24 communes, 6-joins + Radar/DVF/terrain) —
    coûteux (~4 s mesuré en prod). Appelé par le cache PARTAGÉ (job nocturne / déploiement) et, en
    dernier recours, par une lecture qui tombe sur un cache vide. Ne touche JAMAIS le chemin chaud."""
    from ..ingestion.dvf_marche import neuf_vefa_commune
    from ..marche_service import neuf_vefa_seuil
    from ..faisabilite.marche_commune import ligne2_terrain_zone
    seuil = neuf_vefa_seuil()
    rows = indicateurs_communes(db, runs.current())   # 1.6 — moteur commune_compteurs
    pa = prix_ancien_communes(db)   # §1b — SOURCE UNIQUE du €/m² ancien (partagée avec le PDF baromètre)
    for r in rows:
        r["prix_ancien"] = (pa.get(r["commune"]) or {}).get("median")
        r["prix_ancien_n"] = (pa.get(r["commune"]) or {}).get("n")
        # RETOURS-11F M1 — NEUF depuis le moteur live (même seuil/fenêtre que la fiche et la carte) :
        # sous le seuil, prix_neuf reste null (jamais un chiffre fragile ni un précalcul périmé).
        v = neuf_vefa_commune(db, r["insee"])
        suffisant = v["n"] >= seuil and v["mediane_prix_m2_bati"] is not None
        r["prix_neuf"] = v["mediane_prix_m2_bati"] if suffisant else None
        r["prix_neuf_n"] = v["n"]
        # RETOURS-11F M13 — €/m² TERRAIN NU DVF (« le chiffre du promoteur », O14) : MÊME moteur
        # que la fiche (Marché) et la calculette — `ligne2_terrain_zone`, aucun calcul parallèle.
        # Zone U de préférence, sinon AU ; sous le seuil de cellule → null (jamais un 0 trompeur).
        try:
            pz = (ligne2_terrain_zone(db, r["commune"]).get("valeurs") or {}).get("par_zone") or {}
        except Exception:  # noqa: BLE001 — le terrain nu ne casse jamais le tableau
            pz = {}
        tn = None
        for fam in ("U", "AU"):
            cell = pz.get(fam) or {}
            if cell.get("calculable") and cell.get("median_eur_m2"):
                tn = {"eur_m2": cell["median_eur_m2"], "n": cell.get("n"), "zone": fam}
                break
        r["prix_terrain_nu"] = tn["eur_m2"] if tn else None
        r["prix_terrain_nu_n"] = tn["n"] if tn else None
        r["prix_terrain_nu_zone"] = tn["zone"] if tn else None
    return {r["commune"]: r for r in rows}


# VITESSE-2 (Lot 1) — CACHE PARTAGÉ des indicateurs bruts. Avant, `raw_rows` était mémoïsé PAR WORKER
# (TTL 1 h) : le 1ᵉʳ clic sur une commune touchant un worker froid recalculait les 24 communes (~5 s en
# prod), et ce PLUSIEURS FOIS PAR JOUR (5 workers × TTL 1 h) — c'est le résiduel « clic commune lent »
# de DEPLOY-1028 §Phase 4. On sort le calcul du chemin de lecture : le résultat est stocké EN BASE
# (`comparateur_raw_cache`, UNE ligne par empreinte servie) où TOUS les workers le lisent, écrit par le
# job nocturne + le réchauffage de déploiement, invalidé par la clé de fraîcheur du run servi. Un worker
# chaud garde un mémo in-process (L1) ; un worker froid lit la base (L2, quelques ms) au lieu de recalculer.
_RAW_CACHE_DDL = """
CREATE TABLE IF NOT EXISTS comparateur_raw_cache (
  cle_fraicheur text PRIMARY KEY,
  payload jsonb NOT NULL,
  computed_at timestamptz NOT NULL DEFAULT now()
)
"""


def _raw_cache_json(payload: dict) -> str:
    """Sérialise le payload en JSON tolérant (Decimal/date/datetime → primitives) — mêmes types que
    ce que FastAPI sert déjà en sortie, donc round-trip neutre (valeur servie identique avant/après)."""
    import json as _json
    from datetime import date as _date, datetime as _dt
    from decimal import Decimal as _Dec

    def _default(o):
        if isinstance(o, _Dec):
            return float(o)
        if isinstance(o, (_date, _dt)):
            return o.isoformat()
        raise TypeError(f"non sérialisable : {type(o)}")
    return _json.dumps(payload, ensure_ascii=False, default=_default)


def _persister_raw_cache(cle: str, payload: dict) -> None:
    """Écrit le payload dans `comparateur_raw_cache` via une session DÉDIÉE (jamais la session de
    lecture de l'appelant : une écriture+commit ne doit pas entraîner la transaction d'une fiche).
    Crée la table au besoin. Best-effort : une base en lecture seule ne casse pas la lecture."""
    from ..db import session_factory
    s = session_factory()()
    try:
        s.execute(text(_RAW_CACHE_DDL))
        s.execute(text(
            "INSERT INTO comparateur_raw_cache (cle_fraicheur, payload, computed_at) "
            "VALUES (:k, CAST(:p AS jsonb), now()) "
            "ON CONFLICT (cle_fraicheur) DO UPDATE SET payload = EXCLUDED.payload, computed_at = now()"),
            {"k": cle, "p": _raw_cache_json(payload)})
        s.commit()
    except Exception:  # noqa: BLE001 — l'écriture du cache ne doit jamais casser une lecture
        s.rollback()
    finally:
        s.close()


def rafraichir_raw_cache(db: Session) -> dict[str, dict]:
    """POINT D'ÉCRITURE du cache partagé (job nocturne `fiche-commune-cache`, `labuse rebuild`,
    réchauffage de déploiement) : calcule les 24 communes UNE fois et les stocke pour TOUS les workers,
    clé = empreinte du run servi. Purge les clés périmées (> 7 j). Rend le payload calculé."""
    from ..fraicheur_caches import empreinte_attendue
    cle = empreinte_attendue(db)
    payload = _compute_raw(db)
    _persister_raw_cache(cle, payload)
    try:
        from ..db import session_factory
        s = session_factory()()
        try:
            s.execute(text("DELETE FROM comparateur_raw_cache WHERE cle_fraicheur <> :k "
                           "AND computed_at < now() - interval '7 days'"), {"k": cle})
            s.commit()
        finally:
            s.close()
    except Exception:  # noqa: BLE001 — la purge n'est jamais bloquante
        pass
    return payload


def raw_rows(db: Session) -> dict[str, dict]:
    """SOURCE UNIQUE des indicateurs bruts PAR COMMUNE (avant normalisation) — le comparateur ET la
    fiche commune (OUTILS-6 C2) la lisent : ancien/neuf/permis/vélocité/stock viennent du MÊME run et
    des MÊMES requêtes des deux côtés, donc chaque chiffre commun est identique. Clé = nom de commune.

    VITESSE-2 (Lot 1) — lecture en deux étages, HORS du calcul coûteux : L1 mémo in-process (worker
    chaud), L2 cache PARTAGÉ en base `comparateur_raw_cache` (tous les workers, clé = empreinte servie).
    Le chemin chaud ne fait qu'un SELECT PK ; le calcul n'a lieu QUE si la base n'a pas encore été
    réchauffée (job nocturne / déploiement), et il est alors persisté pour les workers suivants."""
    from .app import _mem_cached
    from ..fraicheur_caches import empreinte_attendue
    cle = empreinte_attendue(db)

    def _load():
        # Tests : JAMAIS le cache partagé — l'app de test attend un calcul LIVE qui reflète les
        # insertions NON committées de la session du test (comme `parcel_fiche` désactive son cache
        # sous pytest). Le mémo in-process est vidé entre tests (fixture `_clear_mem_caches`).
        import os as _os
        if _os.environ.get("PYTEST_CURRENT_TEST"):
            return _compute_raw(db)
        # L2 — cache partagé en base. Garde par EXISTENCE (`to_regclass` : ne vide JAMAIS la
        # transaction de l'appelant si la table manque, contrairement à un SELECT qui lèverait et
        # exigerait un rollback — destructeur en pleine requête). Aucune DDL sur le chemin de lecture
        # (la table est créée par le 1ᵉʳ écrivain : job nocturne / déploiement / ce miss).
        if db.execute(text("SELECT to_regclass('comparateur_raw_cache')")).scalar():
            row = db.execute(text(
                "SELECT payload FROM comparateur_raw_cache WHERE cle_fraicheur = :k"),
                {"k": cle}).scalar()
            if row is not None:
                return row   # jsonb → dict (valeurs identiques à ce que FastAPI sert)
        payload = _compute_raw(db)   # lectures sur la session de l'appelant (aucune écriture ici)
        _persister_raw_cache(cle, payload)   # persistance via session dédiée (pour les workers suivants)
        return payload

    # L1 — mémo in-process, clé incluant l'empreinte servie : une bascule de run l'invalide d'elle-même.
    return _mem_cached(("o6-raw", cle), 3600.0, _load)


def _compute(db: Session, poids: dict) -> dict:
    """Cœur testable : assemble les indicateurs par commune, normalise, compose. `poids` = dict d'axes→poids."""
    rows = [dict(r) for r in raw_rows(db).values()]
    for r in rows:   # arrondis lisibles (les valeurs brutes restent la vérité)
        if r.get("velocite") is not None:
            r["velocite"] = round(float(r["velocite"]), 1)
        if r.get("pression_zan") is not None:
            r["pression_zan"] = round(float(r["pression_zan"]), 1)
        if r.get("deficit_sru") is not None:
            r["deficit_sru"] = round(float(r["deficit_sru"]), 1)
    rows = composite_communes(rows, poids)   # 1.6 — moteur commune_compteurs (comparateur_composite)
    return {
        "communes": rows,
        "indicateurs": {k: {"libelle": v[0], "direction": "haut = mieux" if v[1] > 0 else "bas = mieux",
                            "poids": poids.get(k), "source": v[3], "nature": v[4]}
                        for k, v in INDICATEURS.items()},
        "poids_total": round(sum(poids.values()), 3),
        "methode": ("Composite de COMMODITÉ (non calibré) : chaque indicateur normalisé min-max [0-100] selon sa "
                    "direction, moyenne pondérée des axes présents (poids renormalisés si une donnée manque). "
                    "La pondération est réglable via les paramètres w_* ; les valeurs brutes restent la référence."),
        "avertissement": "Aide à la comparaison, pas un score de rendement ; un axe manquant reste null (jamais 0).",
    }


@router.get("")
def comparateur_communes(
    db: Session = Depends(get_db),
    w_stock: float = Query(0.30, ge=0, le=1), w_velocite: float = Query(0.15, ge=0, le=1),
    w_permis: float = Query(0.15, ge=0, le=1), w_deficit_sru: float = Query(0.15, ge=0, le=1),
    w_pression_zan: float = Query(0.10, ge=0, le=1), w_prix_neuf: float = Query(0.15, ge=0, le=1),
) -> dict:
    """Tableau « où investir » : une ligne par commune, indicateurs sourcés + composite à pondération réglable."""
    poids = {"stock": w_stock, "velocite": w_velocite, "permis": w_permis,
             "deficit_sru": w_deficit_sru, "pression_zan": w_pression_zan, "prix_neuf": w_prix_neuf}
    # BLOC B (B1.4) : cache TTL 1 h par jeu de pondérations (mêmes raisons/rythme que le
    # carnet O7 : les indicateurs suivent les crons quotidiens ; single-flight anti-stampede).
    from .app import _mem_cached
    return _mem_cached(("o6", tuple(sorted(poids.items()))), 3600.0, lambda: _compute(db, poids))
