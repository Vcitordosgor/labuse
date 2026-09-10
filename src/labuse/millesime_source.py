"""RECETTE-8 W16 — LE producteur UNIQUE du millésime affichable d'une source.

Avant, deux endroits composaient le millésime d'une même source et divergeaient dans le MÊME
document : le pied de section (registre/valeur.py) imprimait le `source_millesime` BRUT
(« BD TOPO® V3 (IGN) — édition non enregistrée ») pendant que la section « Sources et millésimes »
(api.app._data_sources_fiche) appliquait la composition RECETTE-7 E10 (« … — édition courante, vue
le 31/07/2026 (sentinelle) »). Une source, deux vérités.

Ici, UNE fonction pure compose le millésime affichable depuis les mêmes entrées ; les deux chemins
l'appellent. Ordre (EXPORTS-1 6.4, audit B13 + E10) : millésime amont publié → sinon date amont
VUE par la sentinelle → sinon date d'ingestion étiquetée → sinon None (cellule masquée). Le cas
IGN « édition non enregistrée » (WFS/Géoplateforme sans millésime versionné) est réécrit en
« édition courante, vue/ingérée le … » plutôt qu'un libellé mort.
"""
from __future__ import annotations

import re
from datetime import date, datetime

_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")

#: RECETTE-11 D6 — notes d'ingénierie internes qui fuyaient dans les millésimes/sources affichés
#: au client (§10 « Sources et millésimes » ET pieds de section, tous deux via `composer`).
_NOTES_INTERNES = (
    (" — RPG.LATEST, année non pinnée", ", édition courante"),
    ("RPG.LATEST, année non pinnée", "édition courante"),
    ("RPG.LATEST", "RPG"),
    ("année non pinnée", "édition courante"),
    (" (propre non public)", ""),
    ("propre non public", ""),
    (" — « latest » ingérée", ", édition courante"),
    ("« latest » ingérée", "édition courante"),
    ("« latest »", "édition courante"),
)


def nettoyer_notes_internes(s):
    """Retire les notes techniques internes d'une chaîne affichée au client (D6). None → None."""
    if not s:
        return s
    for avant, apres in _NOTES_INTERNES:
        s = s.replace(avant, apres)
    return s.replace(" ·  ", " · ").strip(" ·—")


def _fr(d) -> str | None:
    """JJ/MM/AAAA depuis une date/datetime/ISO ; None si absent/illisible."""
    if d is None:
        return None
    if isinstance(d, (date, datetime)):
        return d.strftime("%d/%m/%Y")
    s = str(d)
    if _ISO.match(s):
        return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
    return None


def composer(source_millesime, *, source_horizon_at=None, dernier_vu=None,
             last_sync_at=None) -> str | None:
    """Le millésime AFFICHABLE d'une source (point unique). Voir docstring du module pour l'ordre."""
    mill = source_millesime or None
    if not mill and source_horizon_at is not None:
        an = getattr(source_horizon_at, "year", None)
        mill = str(an) if an else None
    vu = _fr(dernier_vu)
    if not mill and vu:
        return f"amont à jour au {vu} (sentinelle)"
    sync = _fr(last_sync_at)
    if not mill and sync:
        return f"ingéré le {sync} (date d'ingestion, millésime amont non publié)"
    # cas IGN « édition non enregistrée » — réécrit, jamais un libellé mort (E10).
    if mill and "édition non enregistrée" in str(mill):
        base = str(mill).split(" — ")[0]
        if vu:
            return f"{base} — édition courante, vue le {vu} (sentinelle)"
        if sync:
            return f"{base} — édition courante, ingérée le {sync} (millésime amont non versionné par l'IGN)"
        return f"{base} — édition courante (millésime amont non versionné par l'IGN)"
    return nettoyer_notes_internes(mill)
