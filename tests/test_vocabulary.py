"""Vocabulaire prudent : « opportunité vérifiée » (pas « fiable »), SAR honnête, exports.

Garde-fou anti-surpromesse après l'intégration SAR partielle. Aucune donnée ni scoring touché."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "src/labuse/api/web/app.js").read_text(encoding="utf-8")
EXPORT = (ROOT / "src/labuse/api/export.py").read_text(encoding="utf-8")
PHASE1 = (ROOT / "src/labuse/cascade/layers/phase1.py").read_text(encoding="utf-8")


def test_badge_opportunite_n_est_plus_fiable():
    assert "opportunité fiable" not in APP_JS.lower()      # plus de sur-promesse
    assert "Opportunité vérifiée" in APP_JS                # libellé tempéré


def test_sous_texte_honnete_present():
    assert "ne vaut pas garantie de constructibilité" in APP_JS
    assert "SAR partiel" in APP_JS                          # la limite SAR est dite


def test_prix_de_marche_fiable_conserve():
    # le « prix de marché fiable » (moteur DVF) garde son libellé — concept distinct.
    assert "Prix de marché fiable" in APP_JS


def test_distinction_des_trois_notions():
    low = APP_JS.lower()
    assert "opportunité vérifiée" in low          # 1. opportunité (couches)
    assert "prix de marché fiable" in low          # 2. prix de marché (DVF)
    assert "simulation indicative" in low or "simulation" in low  # 3. bilan promoteur


def test_export_pas_d_opportunite_fiable():
    assert "opportunité fiable" not in EXPORT.lower()
    assert "Prix de marché fiable" in EXPORT       # distinction préservée dans l'export


def test_sar_libelles_honnetes_dans_la_cascade():
    # hors îlot / compatible / à vérifier : formulations prudentes exactes.
    assert "hors îlot cartographié — aucune contrainte SAR déduite automatiquement" in PHASE1
    assert "vocation compatible détectée" in PHASE1 and "à croiser avec PLU/PPR" in PHASE1
    assert "vocation à vérifier" in PHASE1 and "possible contrainte régionale" in PHASE1
