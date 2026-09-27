"""VEILLE-FIX-2 — LA GRILLE, lue par le code.

`config/veille.yaml` est la décision de Vic (27/09/2026) : pour chaque événement, qui est prévenu, à la
cloche et/ou par mail. Ce module la charge et l'expose. Le code de notification (cloche, digest, envoi
immédiat) DÉRIVE d'ici — jamais une liste de `kind` recopiée en dur. `tests/test_veille_grille.py` garde
la table ET vérifie que les dérivations du code (`_CLOCHE_KINDS`, `_DIGEST_KINDS`…) collent à la grille.
"""
from __future__ import annotations

import functools

from . import config

DESTINATAIRES = ("suiveur", "criteres", "tous", "compte")
CLOCHE = ("non", "oui", "tete")
MAIL = ("non", "digest", "immediat", "dedie")


@functools.lru_cache(maxsize=1)
def charger() -> dict:
    """La grille YAML (cache : la config ne change pas en cours d'exécution)."""
    return config.load_yaml_config("veille")


def evenements() -> dict:
    return charger().get("evenements", {})


def _lignes() -> list[dict]:
    return list(evenements().values())


def _kinds(pred) -> tuple:
    """Les `kind` (non nuls, dédoublonnés en gardant l'ordre) des événements satisfaisant `pred`."""
    out: list[str] = []
    for e in _lignes():
        k = e.get("kind")
        if k and pred(e) and k not in out:
            out.append(k)
    return tuple(out)


def kinds_cloche() -> tuple:
    """Les `kind` qui vont à la cloche (oui OU tete)."""
    return _kinds(lambda e: e.get("cloche") in ("oui", "tete"))


def kinds_tete() -> tuple:
    """Les `kind` prioritaires (en tête de la cloche)."""
    return _kinds(lambda e: e.get("cloche") == "tete")


def kinds_digest() -> tuple:
    """Les `kind` e-mailés dans le digest."""
    return _kinds(lambda e: e.get("mail") == "digest")


def kinds_immediat() -> tuple:
    """Les `kind` à mail immédiat (la seule = mise en vente d'une parcelle suivie)."""
    return _kinds(lambda e: e.get("mail") == "immediat")


def kinds_broadcast() -> tuple:
    """Les `kind` destinés à TOUS les comptes actifs (marché / nouveautés) — cloche, jamais mail."""
    return _kinds(lambda e: e.get("destinataire") == "tous")


def destinataire(kind: str) -> str | None:
    for e in _lignes():
        if e.get("kind") == kind:
            return e.get("destinataire")
    return None


def mode_mail(kind: str) -> str | None:
    for e in _lignes():
        if e.get("kind") == kind:
            return e.get("mail")
    return None


# ── fréquence ────────────────────────────────────────────────────────────────

def frequences() -> list:
    return list(charger().get("frequences", ["quotidien"]))


def frequence_defaut() -> str:
    return charger().get("frequence_defaut", "quotidien")


def frequence_valide(freq: str | None) -> str:
    """Normalise : une valeur inconnue (ou NULL en base) retombe sur le défaut."""
    return freq if freq in frequences() else frequence_defaut()


def digest_heure_reunion() -> str:
    return charger().get("digest", {}).get("heure_reunion", "07:15")


def hebdo_jour() -> int:
    """Jour ISO du digest hebdo (0 = lundi, comme datetime.weekday())."""
    return int(charger().get("digest", {}).get("hebdo_jour", 0))
