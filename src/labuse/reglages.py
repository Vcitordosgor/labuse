"""CONNEXIONS-2 Lot 7.1 (N2) — réglages runtime éditables au dashboard (admin), relus À CHAUD.

Un seul point de vérité pour les bascules d'exploitation qui doivent changer SANS redéploiement :
table clé/valeur `app_reglages`. Aujourd'hui : le drapeau « dépôt agence » (parcours « Publier une
annonce »), qui vivait dans l'env (`config.radar_depot_agence_actif`) — donc figé jusqu'au prochain
déploiement. La valeur d'env reste le DÉFAUT (sûr : fermé) ; le réglage en base, s'il existe, prime.

Cache court (5 s) pour ne pas frapper la base à chaque lecture de flux Radar, mais assez court pour
que la bascule au dashboard soit « immédiate » à l'écran (mandat : bascule → visibilité immédiate).
"""
from __future__ import annotations

import time

from sqlalchemy import text

_DDL = """
CREATE TABLE IF NOT EXISTS app_reglages (
    cle        varchar(64) PRIMARY KEY,
    valeur     text,
    updated_at timestamptz NOT NULL DEFAULT now()
)
"""

#: clé canonique du drapeau dépôt agence.
CLE_DEPOT_AGENCE = "radar_depot_agence_actif"
#: RETOURS-8 (R11) — rétention des conversations Copilote (jours), éditable à chaud (défaut config 7).
CLE_COPILOTE_RETENTION = "copilote_retention_jours"

_cache: dict = {}          # cle -> (expire_at, valeur_bool)
_CACHE_TTL_S = 5.0


def ensure_reglages(engine) -> None:
    """Crée la table (idempotent) — appelée au heal de schéma."""
    with engine.begin() as c:
        c.execute(text(_DDL))


def _lire_brut(cle: str) -> str | None:
    from .db import session_scope
    try:
        with session_scope() as s:
            s.execute(text(_DDL))            # ceinture : base jamais healée
            return s.execute(text("SELECT valeur FROM app_reglages WHERE cle = :k"),
                             {"k": cle}).scalar()
    except Exception:  # noqa: BLE001 — un souci de lecture retombe sur le défaut d'env, jamais un crash
        return None


def get_bool(cle: str, defaut: bool) -> bool:
    """Valeur booléenne du réglage (cache 5 s). Absent → `defaut` (la valeur d'env)."""
    now = time.time()
    hit = _cache.get(cle)
    if hit and hit[0] > now:
        return hit[1]
    brut = _lire_brut(cle)
    val = defaut if brut is None else (brut.strip().lower() in ("1", "true", "t", "oui", "on"))
    _cache[cle] = (now + _CACHE_TTL_S, val)
    return val


def set_bool(cle: str, valeur: bool) -> None:
    """Écrit le réglage (admin) et INVALIDE le cache — la bascule est visible à la requête suivante."""
    from .db import session_scope
    with session_scope() as s:
        s.execute(text(_DDL))
        s.execute(text(
            "INSERT INTO app_reglages (cle, valeur, updated_at) VALUES (:k, :v, now()) "
            "ON CONFLICT (cle) DO UPDATE SET valeur = EXCLUDED.valeur, updated_at = now()"),
            {"k": cle, "v": "true" if valeur else "false"})
        s.commit()
    _cache.pop(cle, None)


def get_int(cle: str, defaut: int) -> int:
    """RETOURS-8 (R11) — valeur ENTIÈRE d'un réglage (cache 5 s). Absent/illisible → `defaut`."""
    now = time.time()
    hit = _cache.get(cle)
    if hit and hit[0] > now:
        return hit[1]
    brut = _lire_brut(cle)
    try:
        val = defaut if brut is None else int(str(brut).strip())
    except ValueError:
        val = defaut
    _cache[cle] = (now + _CACHE_TTL_S, val)
    return val


def set_int(cle: str, valeur: int) -> None:
    """Écrit un réglage entier (admin) et INVALIDE le cache."""
    from .db import session_scope
    with session_scope() as s:
        s.execute(text(_DDL))
        s.execute(text(
            "INSERT INTO app_reglages (cle, valeur, updated_at) VALUES (:k, :v, now()) "
            "ON CONFLICT (cle) DO UPDATE SET valeur = EXCLUDED.valeur, updated_at = now()"),
            {"k": cle, "v": str(int(valeur))})
        s.commit()
    _cache.pop(cle, None)


def copilote_retention_jours() -> int:
    """RETOURS-8 (R11) — la rétention EFFECTIVE des conversations Copilote : réglage base s'il existe,
    sinon défaut config (7 jours). Lue par le job de purge ET par le bandeau front (via /copilote-v2)."""
    from .config import get_settings
    return get_int(CLE_COPILOTE_RETENTION, int(get_settings().copilote_v2_retention_jours))


def depot_agence_actif() -> bool:
    """Le drapeau « dépôt agence » EFFECTIF : réglage base s'il existe, sinon défaut d'env (fermé)."""
    from .config import get_settings
    return get_bool(CLE_DEPOT_AGENCE, bool(get_settings().radar_depot_agence_actif))


def exclusion_depot_agence_sql(alias: str = "b") -> str:
    """CONNEXIONS-2 Lot 7 (#12/H5) — fragment SQL à ajouter aux lectures CLIENT du Radar : tant que le
    drapeau est FERMÉ, un dépôt agence (même validé par un test admin) N'EST PAS servi aux clients.
    Renvoie '' si le drapeau est ouvert, sinon ' AND NOT <alias>.depose_par_agence'. Pas de bind param
    (fragment pur) : composable dans les constantes de requête existantes."""
    if depot_agence_actif():
        return ""
    return f" AND NOT {alias}.depose_par_agence"
