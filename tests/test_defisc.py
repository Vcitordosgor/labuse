"""M44 — sortie locative défisc : lint, coefficient de surface aux bornes, héritage d'étiquette."""
from __future__ import annotations

from labuse.faisabilite import defisc as D


def test_lint_config_reelle_passe():
    assert D.lint() == []


def test_lint_refuse_plafond_sans_source():
    bad = {"mention_conseil_fiscal": "x", "defaut_regime": "base",
           "plafonds_loyer": {"base": {"valeur_eur_m2_mois": 12.21}, "intermediaire": {}},
           "coef_surface": {"constante": 0.7, "numerateur": 19, "plafond_max": 1.2, "source": "s", "date": "d"},
           "rendement_cible": {"defaut_pct": 6, "bornes_pct": [3, 12], "etiquette": "Estimé", "justification": "j"}}
    errs = D.lint(bad)
    assert any("plafonds_loyer.base.source" in e for e in errs)
    assert any("plafonds_loyer.intermediaire" in e for e in errs)


def test_coef_surface_cap_petites_surfaces():
    # le cap 1,2 mord pour S ≤ 38 m² (barème 2026 : 0,7 + 19/38 = 1,2)
    assert D.coef_surface(10) == 1.2
    assert D.coef_surface(38) == 1.2
    # descend vers la constante pour les grandes surfaces
    assert D.coef_surface(76) < 1.0
    assert abs(D.coef_surface(200) - 0.795) < 0.001
    assert D.coef_surface(0) == 1.2  # garde : surface nulle → cap (jamais une division par zéro)


def test_plafond_source_marche_estime():
    r = D.sortie_locative(120, 180000)                       # plafond base par défaut
    # M59-P1 (Q2) : le plafond N'EST PLUS étiqueté « Sourcé » comme hypothèse de revenu — il DIT
    # sa nature ; la référence BOFiP reste portée par `source` (vraie pour la VALEUR du plafond).
    assert "Sourcé" not in r["loyer"]["etiquette"]
    assert "plafond réglementaire" in r["loyer"]["etiquette"]
    assert "loyer de marché observé" in r["loyer"]["etiquette"]
    assert (r["loyer"]["source"] or "").startswith("BOFiP")
    assert r["loyer"]["regime"] == "base"
    assert r["etiquette"] == "Estimé"                        # héritage : contient les travaux Estimé
    m = D.sortie_locative(120, 180000, loyer_marche_m2=14.0)  # marché → Estimé, pas de coef
    assert m["loyer"]["etiquette"].startswith("Estimé")
    assert m["loyer"]["coef_surface"] is None


def test_rendement_cible_borne_et_achat_max_baisse():
    # un rendement cible plus haut abaisse le prix d'achat max (le doute ne profite pas au chiffre)
    bas = D.sortie_locative(120, 180000, rendement_cible_pct=4.0)["achat_max_eur"]
    haut = D.sortie_locative(120, 180000, rendement_cible_pct=9.0)["achat_max_eur"]
    assert haut < bas
    # clamp aux bornes : 99 % → ramené à la borne haute (12 %)
    clamp = D.sortie_locative(120, 180000, rendement_cible_pct=99.0)
    assert clamp["rendement_cible_pct"] == 12.0


def test_bilan_negatif_dit_honnetement():
    # travaux énormes / petite surface → achat max négatif, DIT (jamais masqué)
    r = D.sortie_locative(30, 500000)
    assert r["negatif"] is True and r["message_negatif"]
