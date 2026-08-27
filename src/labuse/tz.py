"""Fuseau horaire MÉTIER de LABUSE — Indian/Reunion, EXPLICITE (jamais l'heure locale du process).

REVUE · R2 (bug fuseau consigné). La machine tourne en CEST, PostgreSQL rend l'heure Réunion (+2).
Toute fenêtre temporelle MÉTIER — quotas/jour, gels anti-burst, digests, « aujourd'hui », péremption,
fenêtres d'ouverture — doit se calculer sur `Indian/Reunion`, jamais sur `date.today()`/`datetime.now()`
implicites (qui prennent le fuseau du process = CEST). Sinon la bascule de jour se produit à minuit
CEST (22 h Réunion) au lieu de minuit Réunion : entre 20 h et minuit CEST, le « jour » Python diverge
du « jour » SQL (PostgreSQL en Réunion) → quotas réinitialisés au lieu de levés (bug porte partenaires).

Deux garde-fous complémentaires :
- CÔTÉ SQL : le fuseau de session PostgreSQL est forcé à Indian/Reunion (db.py, connect_args) → tout
  `CURRENT_DATE`/`now()` est en Réunion, quel que soit le fuseau du serveur de prod.
- CÔTÉ PYTHON : `today_reunion()` / `now_reunion()` remplacent `date.today()` / `datetime.now()` dans
  les fenêtres métier.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

#: le seul fuseau métier de LABUSE. Nom IANA, DST-safe (La Réunion n'a pas d'heure d'été → +4 fixe).
REUNION_TZ = ZoneInfo("Indian/Reunion")


def now_reunion() -> datetime:
    """Instant courant en heure Réunion (aware). Pour toute borne de fenêtre métier."""
    return datetime.now(REUNION_TZ)


def today_reunion() -> date:
    """Date du jour à la Réunion. Remplace `date.today()` pour toute fenêtre métier (quota/gel/jour)."""
    return now_reunion().date()
