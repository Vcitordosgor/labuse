"""CALCULS-FIX-1 Lot C — l'année de défiscalisation n'est plus figée.

`ANNEE_ACTIVE = 2026` était écrit en dur : au 1er janvier 2027, les plafonds/coefficients
auraient été servis périmés SANS que rien ne le signale. Désormais l'année active se déduit
de la date du jour et des barèmes disponibles ; si le barème de l'année courante n'existe pas
encore, on sert le dernier disponible AVEC son millésime + un signalement, jamais un chiffre muet.
"""
from __future__ import annotations

import datetime

from labuse.faisabilite import defisc


def test_annee_active_suit_la_date_pas_un_littéral():
    """Aucune année n'est figée : l'active se déduit du jour et des barèmes présents."""
    # en 2026, le barème 2026 existe → servi, non périmé
    assert defisc.annee_active(datetime.date(2026, 6, 1)) == 2026
    assert defisc.bareme_perime(datetime.date(2026, 6, 1)) is False
    assert defisc.signalement_fraicheur(datetime.date(2026, 6, 1)) is None


def test_2_janvier_2027_bareme_2026_servi_avec_signalement():
    """Simulation du 2 janvier 2027 (barème 2027 pas encore créé) : on sert le barème 2026
    AVEC son millésime et un signalement — jamais un plafond muet ni un littéral 2026 figé."""
    j = datetime.date(2027, 1, 2)
    assert defisc.annee_active(j) == 2026, "le dernier barème disponible (2026) est servi"
    assert defisc.bareme_perime(j) is True, "le barème est en retard d'un millésime"
    msg = defisc.signalement_fraicheur(j)
    assert msg and "2026" in msg and "2027" in msg, \
        "un signalement nommant le millésime servi et l'année courante doit être servi"


def test_bareme_futur_est_prefere_quand_il_existe(tmp_path, monkeypatch):
    """Dès qu'un defisc_<annee>.yaml de l'année courante existe, il prime (bascule automatique,
    sans toucher au code) — prouvé en simulant un dossier calibrage avec 2026 ET 2027."""
    cal = tmp_path / "calibrage"
    cal.mkdir()
    (cal / "defisc_2026.yaml").write_text("annee: 2026\n", encoding="utf-8")
    (cal / "defisc_2027.yaml").write_text("annee: 2027\n", encoding="utf-8")

    class _S:
        config_path = tmp_path

    monkeypatch.setattr(defisc, "get_settings", lambda: _S())
    assert defisc.annee_active(datetime.date(2027, 1, 2)) == 2027
    assert defisc.bareme_perime(datetime.date(2027, 1, 2)) is False
    # et si on est encore en 2026, on ne saute pas en avance sur le barème 2027
    assert defisc.annee_active(datetime.date(2026, 12, 31)) == 2026


def test_sortie_locative_sert_le_millesime_et_le_signalement():
    """La sortie servie porte le millésime du barème + le drapeau/signalement de fraîcheur."""
    out = defisc.sortie_locative(60.0, 40_000.0)
    assert out is not None
    assert out["millesime_bareme"] == defisc.annee_active()
    assert "bareme_perime" in out and "signalement_fraicheur" in out
