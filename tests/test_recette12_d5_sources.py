"""RECETTE-12 D5 — garde : aucun libellé de source imprimé ne porte de texte libre technique.

La liste de mots interdits a échoué DEUX fois (RECETTE-8 W5, RECETTE-11 D6) car elle remplaçait des
chaînes EXACTES. Ici on vérifie que le NETTOYEUR (motifs robustes) retire les notes quelle que soit
leur date, et que le COMPOSER ne fabrique JAMAIS une note client quand le millésime amont manque.

La PREUVE finale reste le `pdftotext` du Dossier régénéré (0 occurrence des marqueurs) — cf. rapport.
"""
import re

from labuse.millesime_source import composer, nettoyer_notes_internes

# marqueurs interdits dans un libellé client (« Nom — éditeur — millésime » et rien d'autre)
_LEAKS = re.compile(
    r"sentinelle|\bproxy\b|ENS dép|passe \d{2}/\d{2}|date d'ingestion|typeinf|non-publiées|non public"
    r"|amont à jour|non versionné")

# chaînes RÉELLEMENT vues dans le catalogue data_sources (millésimes/éditeurs pollués)
_POLLUES = [
    "proxy RPG (IGN), édition courante",
    "ingéré le 06/07/2026 (date d'ingestion, millésime amont non publié)",
    "INPN/patrinat espaces protégés — passe 05/07/2026",
    "amont à jour au 14/04/2023 (sentinelle)",
    "BD CARTO® V5 — occupation du sol (IGN, proxy)",
    "INPN/MNHN (espaces protégés) · ENS dép. non public",
    "DAAF · proxy RPG/IGN",
    "typeinf 04 — partiel, non-publiées listées",
    "amont à jour au 27/08/2026 (sentinelle)",
]

# millésimes LÉGITIMES : le nettoyeur ne doit pas les abîmer
_PROPRES = [
    "2026-07", "2026", "millésime 2021",
    "géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020",
    "cadastre 1877 (géoréf. 2012/1950)",
]


def test_d5_nettoyeur_retire_toute_note_technique():
    for p in _POLLUES:
        c = nettoyer_notes_internes(p) or ""
        assert not _LEAKS.search(c), f"note technique restante : {p!r} -> {c!r}"


def test_d5_nettoyeur_preserve_les_millesimes_propres():
    for p in _PROPRES:
        c = nettoyer_notes_internes(p) or ""
        # un millésime propre garde son année (on n'a rien retiré d'utile)
        assert re.search(r"\d{4}", c), f"millésime propre abîmé : {p!r} -> {c!r}"


def test_d5_composer_sans_millesime_ne_fabrique_pas_de_note():
    # pas de millésime amont publié → cellule millésime VIDE (jamais « (sentinelle) »/« date d'ingestion »)
    assert composer(None, dernier_vu="2023-04-14") is None
    assert composer(None, last_sync_at="2026-07-06") is None


def test_d5_composer_edition_non_enregistree_sans_date():
    # « édition non enregistrée » → « édition courante », SANS date ni sentinelle
    out = composer("BD TOPO® V3 (IGN) — édition non enregistrée")
    assert out == "BD TOPO® V3 (IGN) — édition courante"
    assert not _LEAKS.search(out)
