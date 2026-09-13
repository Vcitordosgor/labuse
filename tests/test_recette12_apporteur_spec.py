"""RECETTE-12 E — le test de SPEC de l'Apporteur : le `pdftotext` du Brief comparé à la liste FERMÉE
de `docs/audit-2026-09/EXPORTS/APPORTEUR-SPEC.md`. TOUTE ligne hors liste échoue ; tout motif INTERDIT
échoue. La preuve = l'artefact `captures-recette-12/E-apporteur-EL0157.txt` (pdftotext du Brief EL0157
régénéré, émetteur = compte 30). Toute modification future de l'Apporteur passe d'abord par la spec.
"""
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = _ROOT / "docs" / "audit-2026-09" / "EXPORTS" / "APPORTEUR-SPEC.md"
_ARTEFACT = _ROOT / "docs" / "audit-2026-09" / "captures-recette-12" / "E-apporteur-EL0157.txt"


def _blocs():
    txt = _SPEC.read_text(encoding="utf-8").split("```")
    autor = [l.strip() for l in txt[1].splitlines() if l.strip()]
    inter = [l.strip() for l in txt[3].splitlines() if l.strip()]
    return autor, inter


def _lignes():
    return [l.strip() for l in _ARTEFACT.read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.mark.skipif(not (_SPEC.exists() and _ARTEFACT.exists()), reason="spec/artefact absents")
def test_apporteur_aucune_ligne_hors_spec():
    autor, _ = _blocs()
    pats = [re.compile(p) for p in autor]
    hors = [l for l in _lignes() if not any(p.fullmatch(l) for p in pats)]
    assert not hors, f"lignes hors spec (passer d'abord par APPORTEUR-SPEC.md) : {hors}"


@pytest.mark.skipif(not (_SPEC.exists() and _ARTEFACT.exists()), reason="spec/artefact absents")
def test_apporteur_aucun_motif_interdit():
    _, inter = _blocs()
    trouves = sorted({l for l in _lignes() for ip in inter if re.search(ip, l)})
    assert not trouves, f"contenu INTERDIT dans le Brief : {trouves}"


@pytest.mark.skipif(not _ARTEFACT.exists(), reason="artefact absent")
def test_apporteur_trois_essentiels_et_emetteur():
    lignes = _lignes()
    n = sum(1 for l in lignes if l == "L'ESSENTIEL")
    assert n == 3, f"il faut EXACTEMENT 3 « L'ESSENTIEL » (prix, bail, voisines), trouvé {n}"
    # le contact est le premier champ obligatoire, SANS l'étiquette
    assert any("Nom et coordonnées de la personne" in l and "(obligatoire)" in l for l in lignes)
    # l'émetteur est nommé (nom + coordonnées), l'apporteur lui renvoie tout
    assert any(l.startswith("Émetteur : ") for l in lignes), "émetteur absent (anonymat refusé 05/09)"
    assert any("renvoyez vos réponses et vos photos" in l for l in lignes)
