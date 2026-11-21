"""ETUDE-FIABLE-1 (LOT B) — RÉVISIONS d'étude de faisabilité.

En fin d'analyse, le résultat AFFICHÉ est enregistré en base (une révision : saisies, chiffres,
géométries du plan, contrôles, hypothèses, état de la recherche, date, version du moteur). Tout le
reste le RELIT :
  · rouvrir une étude depuis la bibliothèque affiche la révision SANS recalcul ;
  · le PDF est rendu DEPUIS la révision affichée, sans rappeler le moteur (api/modules `_worker_etude_pdf`).

Adressage par CONTENU : la clé est le `study_id` (EF-…, empreinte de la configuration). Le moteur étant
déterministe (LOT A), deux analyses de même configuration produisent la même révision → même numéro =
même contenu (B4). « Relancer l'analyse » recalcule et ré-enregistre la révision (identique si rien n'a
changé en amont — règles, version du moteur).

Best-effort : une base sans la table (ou injoignable) ne doit JAMAIS faire échouer l'étude ni le PDF ;
l'enregistrement est silencieusement ignoré et le PDF retombe sur un calcul (chemin historique).
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy import text

_log = logging.getLogger("labuse")

# Version du MOTEUR stockée avec la révision (trace : quelle logique a produit ces chiffres).
MOTEUR_VERSION = "etude-fiable-1"

_DDL = """
CREATE TABLE IF NOT EXISTS etude_revisions (
    study_id       text PRIMARY KEY,
    payload        jsonb NOT NULL,
    moteur_version text NOT NULL DEFAULT 'etude-fiable-1',
    cree_le        timestamptz NOT NULL DEFAULT now()
)
"""


def _ensure_table(session) -> bool:
    try:
        session.execute(text(_DDL))
        return True
    except Exception:  # noqa: BLE001 — la persistance ne doit jamais casser l'étude
        _log.exception("étude : création table etude_revisions impossible")
        return False


def enregistrer(session, payload: dict) -> Optional[str]:
    """Enregistre (ou met à jour) la révision correspondant au `study_id` du payload. Renvoie le study_id
    enregistré, ou None si impossible (best-effort). Le payload stocké est EXACTEMENT celui servi à l'écran."""
    if not isinstance(payload, dict):
        return None
    study_id = payload.get("study_id")
    if not study_id:
        return None
    if not _ensure_table(session):
        return None
    try:
        brut = json.dumps(payload, ensure_ascii=False, default=str)
        session.execute(text(
            "INSERT INTO etude_revisions (study_id, payload, moteur_version, cree_le) "
            "VALUES (:sid, CAST(:p AS jsonb), :mv, now()) "
            "ON CONFLICT (study_id) DO UPDATE SET payload = EXCLUDED.payload, "
            "moteur_version = EXCLUDED.moteur_version, cree_le = now()"),
            {"sid": study_id, "p": brut, "mv": MOTEUR_VERSION})
        return study_id
    except Exception:  # noqa: BLE001
        _log.exception("étude : enregistrement révision %s impossible", study_id)
        return None


def charger(session, study_id: str) -> Optional[dict]:
    """Relit la révision par study_id (EF-…). None si absente ou base sans la table. Le payload rendu est
    identique à celui servi à l'écran lors de l'analyse → le PDF/l'affichage ne rappellent PAS le moteur."""
    if not study_id:
        return None
    try:
        row = session.execute(text(
            "SELECT payload FROM etude_revisions WHERE study_id = :sid"), {"sid": study_id}).first()
    except Exception:  # noqa: BLE001 — table absente / base nue : chemin historique (recalcul)
        return None
    if not row or row[0] is None:
        return None
    payload = row[0]
    # psycopg rend le jsonb en dict ; par sécurité, tolère une chaîne.
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:  # noqa: BLE001
            return None
    return payload if isinstance(payload, dict) else None
