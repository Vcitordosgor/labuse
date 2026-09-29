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
    ("(IGN, proxy)", "(IGN)"),        # RECETTE-12 D5 — « proxy » entre parenthèses avec l'éditeur
)

#: RECETTE-12 D5 — la liste de mots interdits a échoué DEUX fois (RECETTE-8 W5, RECETTE-11 D6) parce
#: qu'elle remplaçait des chaînes EXACTES. Ici, des MOTIFS (regex) retirent toute note technique
#: quelle que soit sa date : sentinelle, date d'ingestion, « passe », « typeinf », « proxy »,
#: « ENS dép. non public ». Objectif : chaque source imprimée = « Nom — éditeur — millésime », rien d'autre.
_NOTES_REGEX = (
    re.compile(r"\s*—?\s*amont à jour au \d{2}/\d{2}/\d{4}\s*\(sentinelle\)"),
    re.compile(r"\s*—?\s*vue le \d{2}/\d{2}/\d{4}\s*\(sentinelle\)"),
    re.compile(r"\s*—?\s*ingérée? le \d{2}/\d{2}/\d{4}\s*\([^)]*\)"),
    re.compile(r"\s*\(date d'ingestion[^)]*\)"),
    re.compile(r"\s*\(millésime amont non versionné[^)]*\)"),
    re.compile(r"\s*\(sentinelle\)"),
    re.compile(r"\s*—?\s*passe \d{2}/\d{2}/\d{4}"),
    re.compile(r"\s*·?\s*ENS dép\.?\s*non public"),
    re.compile(r"\s*typeinf\s*\d*\s*—?\s*partiel,?\s*"),
    re.compile(r",?\s*non-publiées listées"),
    re.compile(r"[,·]?\s*\bproxy\b"),
)


def nettoyer_notes_internes(s):
    """Retire les notes techniques internes d'une chaîne affichée au client (D5/D6). None → None.
    D'abord les remplacements exacts (héritage), puis les MOTIFS robustes (dates variables)."""
    if not s:
        return s
    for avant, apres in _NOTES_INTERNES:
        s = s.replace(avant, apres)
    for rx in _NOTES_REGEX:
        s = rx.sub("", s)
    # RECETTE-12 D5 — restes de ponctuation orpheline après retrait (« RPG (IGN),  » → « RPG (IGN) »)
    s = re.sub(r"\(\s*\)", "", s)           # parenthèses vides
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"[ ,·—]+$", "", s)          # ponctuation de fin orpheline
    return s.replace(" ·  ", " · ").strip(" ·—,")


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
    # RECETTE-12 D5 — quand aucun millésime amont n'est publié, le client ne voit PLUS une note
    # technique (« amont à jour au … (sentinelle) », « date d'ingestion… ») : la cellule millésime
    # reste vide (la source s'imprime « Nom — éditeur », sans texte libre). La sentinelle reste un
    # signal INTERNE (etats_sources), jamais un millésime client.
    if not mill:
        return None
    # cas IGN « édition non enregistrée » — réécrit « édition courante », SANS date ni sentinelle.
    if "édition non enregistrée" in str(mill):
        base = str(mill).split(" — ")[0]
        return f"{base} — édition courante"
    return nettoyer_notes_internes(mill)


def libelle_date_source(source_millesime, *, source_horizon_at=None, ingere_le=None) -> str | None:
    """RETOUCHES-1 point 7 — le libellé DATÉ d'une source, nommé selon sa provenance.

    « millésime <X> » quand une date est PUBLIÉE en amont (source_millesime / horizon, via composer) ;
    sinon, en repli, « ingéré le JJ/MM/AAAA » depuis la date d'ingestion LABUSE. Le mot « millésime »
    est RÉSERVÉ aux dates publiées par la source — jamais à la date d'ingestion. None si rien à dire."""
    mill = composer(source_millesime, source_horizon_at=source_horizon_at)
    if mill:
        return f"millésime {mill}"
    d = _fr(ingere_le)
    return f"ingéré le {d}" if d else None
