"""DOCS-1 (décision Vic) — le BANC DES DOCUMENTS en test : sur les parcelles témoins, chaque
document rendu ne porte AUCUN jeton de cuisine interne (config/mots_interdits.yaml) et AUCUNE faute
de format (décimale au point, date ISO) ; un fait imprimé n'a qu'une valeur d'un document à l'autre.

Marqué `reel`+`local` : exige la base RÉELLE `labuse` (DVF/PLU/scoring servis) et weasyprint
(venv PDF) — jamais en CI (base vierge). Rejoué au banc de nuit et dans la recette DOCS-1 :

    PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
      ~/Desktop/labuse/.venv/bin/python -m pytest tests/test_docs1_banc.py -m "reel or local"

L'enforcement complet (faits à deux valeurs compris) vit dans le script
`scripts.coherence.documents_banc` ; ce test verrouille les deux contrôles DÉJÀ au vert (jetons,
format) et IMPRIME les faits encore à deux valeurs (chantier d'unification à la source en cours)."""
from __future__ import annotations

import shutil

import pytest

pytestmark = [pytest.mark.reel, pytest.mark.local]


@pytest.fixture(scope="module")
def rapport():
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext (poppler) indisponible")
    try:
        from scripts.coherence.documents_banc import TEMOINS, rejouer
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"banc des documents non importable : {exc}")
    rap = rejouer(TEMOINS)
    if rap["n_docs"] == 0:
        pytest.skip("aucun document rendu (base réelle/weasyprint indisponibles)")
    return rap


def test_aucun_jeton_de_cuisine_interne(rapport):
    """Plus aucun jeton interdit dans le texte rendu d'un document client (DOCS-1)."""
    leaks = rapport["leaks"]
    assert leaks == [], "jetons interdits imprimés : " + "; ".join(
        f"{l['idu']}·{l['doc']}·« {l['jeton']} »" for l in leaks[:20])


def test_aucune_faute_de_format(rapport):
    """Un seul format : décimale à la virgule, dates jj/mm/aaaa (jamais ISO)."""
    f = rapport["fautes_fmt"]
    assert f == [], "fautes de format : " + "; ".join(
        f"{x['idu']}·{x['doc']}·{x['faute']}" for x in f[:20])


def test_faits_a_une_seule_valeur(rapport):
    """Un fait imprimé = UNE seule valeur d'un document à l'autre (DOCS-1, point cardinal). Les deux
    chantiers moteur sont clos : le document Financier (qui inventait une SDP de programme) est
    supprimé ; le Gabarit lit les SUP de la fiche (dispositifs.sup), comme le Dossier. Zéro toléré."""
    div = rapport["divergences"]
    assert div == [], "faits à deux valeurs : " + "; ".join(
        f"{d['idu']}·{d['fait']} ({d['valeurs']})" for d in div[:20])
