"""M137 — UN SEUL VOCABULAIRE SERVI : celui des chips (le libellé COURT), partout.

Défaut M135 : le « i » des paliers disait le libellé LONG (« À contacter en priorité ») pendant
que la bande de résumé, les cartes et la fiche disaient le COURT (« Priorité ») — le client ne
pouvait pas relier les deux. M137 : le mot servi PARTOUT (chips, bande, cartes, fiche, PDF,
exports, assistant, scoreur) est le CHIP COURT ; le libellé long ne vit QUE dans l'explication du
« i » des paliers, accolé à son chip.

Ce verrou casse si un point de service se remet à servir le libellé long, ou si le « i » cesse de
montrer le chip d'abord.
"""
from pathlib import Path

from labuse.scoring.tiers_client import TIERS_CLIENT, court

ROOT = Path(__file__).resolve().parents[1]


def _court(k: str) -> str:
    return court(k)


def test_backend_sert_le_chip_court_partout():
    # Chaque table de libellés servie côté backend = le CHIP COURT (v[0]), jamais le long (v[1]).
    from labuse.verdict_servi import TIER_LABELS
    from labuse.api.scoreur import _TIER_LABELS
    from labuse.api.projets import _TIER_LABEL
    from labuse.api.assistant import _STATUT_PHRASE

    for k in TIERS_CLIENT:
        chip = _court(k)
        assert TIER_LABELS[k] == chip, f"verdict_servi sert le long pour {k}"
        assert _TIER_LABELS[k] == chip, f"scoreur sert le long pour {k}"
        assert _TIER_LABEL[k] == chip, f"projets sert le long pour {k}"
        assert _STATUT_PHRASE[k] == chip, f"assistant sert le long pour {k}"
    # aucune de ces tables ne doit servir un libellé long
    longs = {v[1] for v in TIERS_CLIENT.values()}
    for lbl in TIER_LABELS.values():
        assert lbl not in longs or lbl in {v[0] for v in TIERS_CLIENT.values()}, lbl


def test_verdict_servi_label_est_le_court():
    # Le point de traduction UNIQUE (verdict_servi) sert le chip court — la fiche, le PDF et la
    # page de partage lisent tous score_v2.label = ce label.
    from labuse.verdict_servi import TIER_LABELS
    assert TIER_LABELS["brulante"] == "Priorité"
    assert TIER_LABELS["chaude"] == "À suivre"
    assert TIER_LABELS["reserve_fonciere"] == "Long terme"
    assert TIER_LABELS["a_creuser"] == "Neutre"
    assert TIER_LABELS["declasse_bati_sature"] == "Faible"
    assert TIER_LABELS["ecartee"] == "Écartée"


def test_legende_i_montre_le_chip_dabord():
    # Le « i » des paliers (LeftPanel) préfixe l'explication par le CHIP (tierChipLabel), et les
    # définitions (strings.ts) NE commencent PLUS par le libellé long — elles sont l'explication.
    status = (ROOT / "frontend/src/lib/status.ts").read_text(encoding="utf-8")
    strings = (ROOT / "frontend/src/lib/strings.ts").read_text(encoding="utf-8")
    leftpanel = (ROOT / "frontend/src/components/panel/LeftPanel.tsx").read_text(encoding="utf-8")

    # 1) la source unique du chip de légende existe (dérivée des META servies, groupe declassees inclus)
    assert "export function tierChipLabel" in status
    assert "declassees" in status and "TIER_DECLASSE_META.declasse_bati_sature.label" in status

    # 2) le « i » (LeftPanel) rend le chip AVANT la définition
    assert "tierChipLabel(key)" in leftpanel
    i_chip = leftpanel.index("tierChipLabel(key)")
    i_def = leftpanel.index("defTiers[key]")
    assert i_chip < i_def, "le chip doit précéder l'explication dans le « i » des paliers"

    # 3) les définitions ne LÈVENT plus avec le libellé long (elles commencent par l'explication)
    for long_lbl in ("À contacter en priorité —", "À suivre de près —", "Sans signal particulier —"):
        assert long_lbl not in strings, f"la définition lève encore avec le long : {long_lbl!r}"
