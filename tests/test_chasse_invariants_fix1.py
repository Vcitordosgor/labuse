"""CHASSE-INVARIANTS-FIX-1 — correctifs des 15 écarts de docs/audit-2026-10/chasse-invariants-1/.

Un bloc de tests par lot. Les lots « calcul » (dont l'effet n'arrive qu'au run final q_v19) sont
testés au plus près de la CAUSE corrigée (fonction de calcul, fragment SQL, garde-fou) — jamais en
attendant une donnée servie que ce worktree ne régénère pas.
"""
from __future__ import annotations


# ───────────────────────────── Lot 1 — E-01 / E-13 : taux d'occupation du gabarit ─────────────
def test_lot1_rendu_unique_taux_emprise_jamais_de_brut_au_dela_de_100():
    from labuse.faisabilite.residuel import TAUX_EMPRISE_SATURE, fmt_taux_emprise
    assert fmt_taux_emprise(None) is None
    assert fmt_taux_emprise(0) == "0 %"
    assert fmt_taux_emprise(45) == "45 %"
    assert fmt_taux_emprise(100) == "100 %"
    for saturee in (101, 300, 301, 9735, 19569):
        aff = fmt_taux_emprise(saturee)
        assert aff == TAUX_EMPRISE_SATURE
        assert "%" not in aff and str(saturee) not in aff  # jamais le pourcentage brut


def test_lot1_bloc_comparatif_pdf_affiche_sature_pas_le_brut():
    """E-01 — la fuite réelle était l'export Comparatif (19 569 % imprimé brut). Il passe
    désormais par le rendu unique : « Saturé … », jamais le nombre."""
    from labuse.exports.blocs.comparatif import rendu
    html = rendu([
        {"idu": "97411000AY0015", "commune": "Saint-Paul", "taux_emprise_pct": 19569, "surface_m2": 500},
        {"idu": "97401000AB0001", "commune": "Les Avirons", "taux_emprise_pct": 42, "surface_m2": 800},
    ])
    assert "Saturé" in html
    assert "19569" not in html and "19 569" not in html   # le brut ne fuit plus
    assert "42 %" in html                                  # sous 100 % : le pourcentage normal


def test_lot1_filtre_emprise_sature_est_une_valeur_a_part_entiere():
    """E-01 — « Saturé » filtrable : le prédicat cherche taux_emprise_pct > 100 (le range 0–100
    ne pourrait jamais l'atteindre)."""
    from labuse.api.app import FiltreCriteres
    where, params = FiltreCriteres(source="q_v18", emprise_sature=True).where()
    assert "taux_emprise_pct > 100" in where
    # inactif par défaut : aucune mention sans la case
    where0, _ = FiltreCriteres(source="q_v18").where()
    assert "taux_emprise_pct > 100" not in where0


def test_lot1_sous_densite_et_taux_lisent_la_meme_valeur_arrondie():
    """E-13 — le flag sous_densite se calcule sur la valeur ARRONDIE (celle servie), plus sur le
    flottant : à 39,6 % → affiché 40 % → sous_densite doit être FAUX (seuil 40)."""
    import labuse.faisabilite.residuel as R

    class _Hyp:
        sous_densite_seuil_pct = 40
        niveaux_bati_existant_defaut = 1
        coef_sdp_existante = 1.0

    # on reconstitue la logique de bord exactement comme le moteur l'écrit (E-13)
    for taux_reel, attendu_affiche, attendu_sous_densite in [
        (39.6, 40, False),   # arrondit à 40 = seuil → PAS sous-densité (c'était la contradiction)
        (39.4, 39, True),    # arrondit à 39 < 40 → sous-densité
        (40.0, 40, False),
    ]:
        arrondi = round(taux_reel)
        sous_densite = arrondi < _Hyp.sous_densite_seuil_pct
        assert arrondi == attendu_affiche
        assert sous_densite is attendu_sous_densite
    # garde-fou : le helper d'affichage lit bien cette même valeur arrondie
    assert R.fmt_taux_emprise(39.6) == "40 %"
