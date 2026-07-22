"""Vocabulaire prudent : « opportunité vérifiée » (pas « fiable »), SAR honnête, exports.

Garde-fou anti-surpromesse après l'intégration SAR partielle. Aucune donnée ni scoring touché."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# B2 (BLOC B) : le proto Vue est archivé (tag archive/proto-vue) — les garde-fous de
# vocabulaire visent désormais le front React servi (la fiche porte le disclaimer).
APP_JS = (ROOT / "frontend/src/components/fiche/Fiche.tsx").read_text(encoding="utf-8")
EXPORT = (ROOT / "src/labuse/api/export.py").read_text(encoding="utf-8")
ASSISTANT = (ROOT / "src/labuse/api/assistant.py").read_text(encoding="utf-8")
PHASE1 = (ROOT / "src/labuse/cascade/layers/phase1.py").read_text(encoding="utf-8")


def test_badge_opportunite_n_est_plus_fiable():
    assert "opportunité fiable" not in APP_JS.lower()      # plus de sur-promesse


def test_sous_texte_honnete_present():
    assert "garantie de constructibilité" in APP_JS        # le disclaimer fiche (React)
    assert "certificat d'urbanisme" in APP_JS              # la limite juridique est dite


def test_prix_de_marche_fiable_conserve():
    # B2 : la distinction fiable/fragile du prix (DVF) vit désormais dans le socle IA
    # (assistant.py) — jamais un prix fragile vendu comme fiable.
    assert "prix de sortie fiable" in ASSISTANT
    assert "fragile" in ASSISTANT


def test_distinction_des_trois_notions():
    low = ASSISTANT.lower()
    assert "fiable" in low and "fragile" in low    # 1. prix de marché qualifié (DVF)
    assert "estimé" in low                          # 2. boussole Sourcé/Estimé
    assert "simulation" in APP_JS.lower() or "estimations indicatives" in APP_JS.lower()  # 3. bilan indicatif (fiche)


def test_export_pas_d_opportunite_fiable():
    assert "opportunité fiable" not in EXPORT.lower()
    assert "Prix de marché fiable" in EXPORT       # distinction préservée dans l'export


def test_sar_libelles_honnetes_dans_la_cascade():
    # hors îlot / compatible / proxy indicatif (Décision 2) : formulations prudentes exactes.
    assert "hors îlot cartographié — aucune contrainte SAR déduite automatiquement" in PHASE1
    assert "vocation compatible détectée" in PHASE1 and "à croiser avec PLU/PPR" in PHASE1
    assert "⚠ proxy SAR divergent du PLU — vigilance en cas de révision" in PHASE1
    assert "SAR (proxy indicatif)" in PHASE1
    assert "ne vaut ni interdiction ni constructibilité" in PHASE1
