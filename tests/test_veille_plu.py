"""M41 — radar procédures PLU : lint strict + conséquences servables (SOURCE only, sursis gaté PADD)."""
from __future__ import annotations

from labuse import veille_plu as V


def test_lint_registre_reel_passe():
    """Le registre curaté config/veille_plu.yaml passe le lint (schéma strict, confiance obligatoire)."""
    assert V.lint() == []


def test_lint_refuse_entree_incomplete():
    bad = {"97499": {"commune": "X", "procedure": "revision_plu"}}  # champs manquants
    errs = V.lint(bad)
    assert any("obligatoire manquant" in e for e in errs)


def test_lint_refuse_deduit_sans_raisonnement():
    bad = {"97499": {"commune": "X", "procedure": "cloturee", "stade": "approuvee_probable",
                     "date_acte": "ABSENT", "debat_padd": "ABSENT", "source": "s", "source_url": "u",
                     "date_constat": "2026-08-06", "confiance": "DEDUIT"}}
    assert any("DEDUIT exige un « raisonnement »" in e for e in V.lint(bad))


def test_lint_refuse_confiance_absente():
    bad = {"97499": {"commune": "X", "procedure": "aucune", "stade": "aucune", "date_acte": "ABSENT",
                     "debat_padd": "ABSENT", "source": "s", "source_url": "u",
                     "date_constat": "2026-08-06"}}  # pas de confiance
    assert any("confiance" in e for e in V.lint(bad))


def test_cible_sert_veille_au_mais_pas_sursis_sans_padd():
    # Saint-Leu : révision SOURCE, débat PADD ABSENT → veille AU servie, sursis DARK
    assert V.fiche_en_cours("97413000AA0001") is not None
    assert V.vigilance_veille_au("97413000AA0001") is not None
    assert V.vigilance_sursis("97413000AA0001") is None


def test_deduit_et_dormante_ne_servent_rien():
    assert V.fiche_en_cours("97411000AA0001") is None      # Saint-Denis clôturée DEDUIT
    assert V.vigilance_veille_au("97417000AA0001") is None  # Saint-Philippe dormante
    assert V.vigilance_sursis("97417000AA0001") is None


def test_geste_trimestriel_vide_apres_curation_et_detecte_vieillissement():
    import datetime
    reg = V._registre()
    # juste après la curation initiale (today = date_constat) → rien à re-vérifier
    assert V.a_reverifier(reg, datetime.date(2026, 8, 6)) == []
    # +45 j : seuls les radars ACTIFS (seuil 30 j) sortent, pas les 90 j
    r45 = V.a_reverifier(reg, datetime.date(2026, 9, 20))
    assert r45 and all(x["seuil"] == 30 and x["actif"] for x in r45)
    # +106 j : tout le monde sort
    assert len(V.a_reverifier(reg, datetime.date(2026, 11, 20))) == 24


def test_sursis_s_arme_quand_padd_source():
    # preuve que le sursis s'allume dès qu'un débat PADD est constaté (sourcé) — cas synthétique
    e = {"commune": "T", "procedure": "revision_plu", "stade": "debat_padd",
         "date_acte": "2022-01-01", "debat_padd": "2025-06-01", "source": "délib n°X",
         "source_url": "http://x", "date_constat": "2026-08-06", "confiance": "SOURCE"}
    assert V.sursis_arme(e) is True
    # même entrée sans PADD → sursis éteint
    e2 = {**e, "debat_padd": "ABSENT"}
    assert V.sursis_arme(e2) is False
    # PADD présent mais confiance DEDUIT → jamais servi
    e3 = {**e, "confiance": "DEDUIT"}
    assert V.sursis_arme(e3) is False
