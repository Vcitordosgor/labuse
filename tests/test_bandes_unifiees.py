"""BANDES-UNIFIEES (fix/logements-source-unique, volet 3) — UN SEUL libellé de bande, celui de
la fiche, pour l'écran Comparer ET le PDF Comparatif : « lettre · libellé client · Signal X ».

Avant : l'écran affichait « À étudier »/« Bonne »/« Faible » (bandeMeta) là où le PDF écrivait
« C · signal faible » (lettre + slug brut). Sources uniques : barème `vocabulaire_client`
(= BANDE_META front) + `signal_mutation.NIVEAU_LABELS` (= SIGNAL_META front). Le miroir front est
figé par frontend/src/lib/status.bandes.test.ts.
"""
from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _lire(rel: str) -> str:
    return (RACINE / rel).read_text()


def test_comparatif_bandes_vocabulaire_de_la_fiche():
    """PDF : « C · À étudier · Signal faible » (lettre + vocabulaire_client + libellé Signal) —
    plus jamais « C · signal faible » (slug). Même forme que l'écran Comparer (bandeMeta)."""
    from labuse.exports.blocs.comparatif import _classement
    assert _classement({"bande": "C", "signal_niveau": "faible"}) == "C · À étudier · Signal faible"
    assert _classement({"bande": "B", "signal_niveau": "fort"}) == "B · Bonne · Signal fort"
    assert _classement({"bande": "A", "signal_niveau": None}) == "A · Excellente"
    assert _classement({"bande": None}) is None
    # NC garde son libellé client (sans cause ici — la cause est portée par la fiche).
    assert _classement({"bande": "NC"}) == "NC · Analyse incomplète"
    # HC (écartée en dur, E-10) : hors barème — libellé front repris, même rendu que l'écran.
    assert _classement({"bande": "HC"}) == "HC · Hors classement"


def test_ecran_comparer_meme_forme_que_le_pdf():
    """L'écran Comparer rend « lettre · libellé » (bandeMeta) + badge Signal (signalMeta) — figé
    au niveau source (le vitest couvre le rendu) : plus de label seul divergeant du PDF."""
    panel = _lire("frontend/src/components/compare/ComparePanel.tsx")
    assert "`${r.bande} · ${bm.label}`" in panel          # val() copie/tri
    assert "{r.bande} · {bm.label}" in panel              # badge rendu
    # les libellés Python (NIVEAU_LABELS) sont le miroir exact de SIGNAL_META (fort/moyen/faible).
    from labuse.scoring.signal_mutation import NIVEAU_LABELS
    status = _lire("frontend/src/lib/status.ts")
    for slug, label in NIVEAU_LABELS.items():
        assert f"label: '{label}'" in status, (slug, label)
    # et le vocabulaire des bandes du barème == BANDE_META front (A/B/C/D/0/NC).
    from labuse.scoring.score_labuse import charger_bareme, libelle_client_bande
    bareme, _sha = charger_bareme()
    for bande in ("A", "B", "C", "D", "0", "NC"):
        assert f"label: '{libelle_client_bande(bande, bareme)}'" in status, bande


