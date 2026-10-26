"""FIX-PRIX-ET-OPPORTUNITES lot 3 — la capacité constructible est présentée comme un MAXIMUM
réglementaire, avec une mention mesurée (volet D : les permis réels en utilisent ~½ en médiane)."""
from __future__ import annotations

from pathlib import Path

from labuse import capacite_max

RACINE = Path(__file__).resolve().parents[1]


def _lire(rel: str) -> str:
    return (RACINE / rel).read_text()


def test_mention_cite_la_mesure_du_volet_d():
    assert capacite_max.RATIO_MEDIAN_SDP == 0.46
    assert capacite_max.RATIO_MEDIAN_LOGEMENTS == 0.40
    assert "0,46" in capacite_max.MENTION and "0,40" in capacite_max.MENTION
    assert "maximum" in capacite_max.MENTION.lower()
    assert "volet D" in capacite_max.MENTION
    assert "½" in capacite_max.MENTION_COURTE and "maximum" in capacite_max.MENTION_COURTE.lower()


def test_exports_portent_la_mention_capacite():
    # Le Financier et le Potentiel portent la mention « capacité = maximum réglementaire ».
    for rel in ("src/labuse/exports/blocs/financier.py",
                "src/labuse/exports/blocs/potentiel.py"):
        assert "capacite_max" in _lire(rel), rel
    # libellés « maximum » posés — LOGEMENTS-SOURCE-UNIQUE : la ligne logements du Financier ne
    # porte plus un « maximum » de l'ancien calcul : saisie du porteur (« Logements (projet) »)
    # ou RENVOI vers l'Étude de faisabilité (le même que la fiche).
    fin = _lire("src/labuse/exports/blocs/financier.py")
    assert "Surface de plancher (maximum)" in fin
    assert "Logements (maximum)" not in fin
    assert "Logements (projet)" in fin and "RENVOI_ETUDE" in fin
    # RECETTE-OUTILS-2 (R18, décision Vic) — le Comparatif ne porte PLUS la note « capacité = maximum
    # réglementaire … (0,46 / 0,40) », retirée pour être IDENTIQUE à l'outil (où elle l'a déjà été). Il
    # ne référence donc plus `capacite_max` du tout.
    _cmp = _lire("src/labuse/exports/blocs/comparatif.py")
    assert "note(_CAP)" not in _cmp and "capacite_max" not in _cmp


def test_fiche_et_gabarit_portent_la_mention():
    assert "capaciteMax" in _lire("frontend/src/components/fiche/constructibilite.tsx")
    assert "SDP max" in _lire("frontend/src/components/fiche/constructibilite.tsx")
    assert "capaciteMax" in _lire("frontend/src/components/outils/Gabarit.tsx")
    assert "capaciteMax" in _lire("frontend/src/components/compare/ComparePanel.tsx")


def test_copilote_porte_la_mention_sur_la_capacite():
    assert "capacite_max" in _lire("src/labuse/copilote_v2/resume_fiche.py")


# ── FIX-ORFEVRE-1 (décision Vic 18/10/2026) ──────────────────────────────────────────────────


def test_ratios_declares_au_registre_et_ancres_sans_exception():
    """Les ratios 0,46 / 0,40 de la note « capacité maximale » sont DÉCLARÉS au registre et ancrés
    nommément par le verrou de provenance — plus d'exception ni d'ancrage accidentel : la note
    seule, sans AUCUNE valeur servie (donc sans le zéro qui ancrait round(0,46)=0), ne fuit plus."""
    from labuse.exports import provenance
    from labuse.registre.donnees import DONNEES

    assert DONNEES["capacite_ratio_median_sdp"].calcul == "constante"
    assert DONNEES["capacite_ratio_median_logements"].calcul == "constante"
    ancres = provenance.nombres_ancres({})
    assert ancres[0.46] == "capacite_ratio_median_sdp"
    assert ancres[0.4] == "capacite_ratio_median_logements"
    assert provenance.fuites("note/capacite", {}, f"<p>{capacite_max.MENTION}</p>") == []
    # aucune entrée de liste blanche pour les ratios : c'est la déclaration qui les porte.
    assert 0.46 not in provenance.ALLOWLIST and 0.4 not in provenance.ALLOWLIST
    # et le lecteur existe (V6b) : le Financier, qui imprime la note complète.
    from labuse.registre.robinets import ROBINETS
    assert "capacite_ratio_median_sdp" in ROBINETS["pdf_financier"].chiffres
    assert "capacite_ratio_median_logements" in ROBINETS["pdf_financier"].chiffres


def test_aucun_nombre_de_logements_ancien_moteur_fiche_et_comparatif():
    """Décision Vic 18/10/2026 — la ligne « Logements possibles (max.) » (écran Comparer + document
    Comparatif) ne porte plus de nombre : elle renvoie à l'Étude de faisabilité. Les champs
    logements_min/logements_possibles ne sont plus servis par /compare (aucun autre lecteur)."""
    comparatif = _lire("src/labuse/exports/blocs/comparatif.py")
    panel = _lire("frontend/src/components/compare/ComparePanel.tsx")
    assert "voir l'Étude de faisabilité" in comparatif
    assert "Étude de faisabilité" in panel
    assert "logements_possibles" not in comparatif and "logements_min" not in comparatif
    assert "logements_possibles" not in panel and "logements_min" not in panel
    app_py = _lire("src/labuse/api/app.py")
    assert '"logements_possibles":' not in app_py and '"logements_min":' not in app_py
