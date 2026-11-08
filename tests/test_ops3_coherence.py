"""OPS-3 (A) — le banc de cohérence dit la vérité : un passage qui n'est pas allé au bout, ou qui a
sauté une vérification, est un ÉCHEC (jamais un vert) pour les contrôles de promotion, le résumé et
les incidents ; et son résultat NOMME le run contrôlé.

Tests UNITAIRES (sans base) sur le gate `autonomie.controler_run` + le banc `banc.run` ;
tests `db` sur le journal (`journaliser_passage` / `marquer_incomplet`)."""
from __future__ import annotations

import pytest


def _mesures(**over):
    """Un jeu de mesures TOUT VERT ; chaque test ne modifie que la cohérence."""
    m = {"manifeste_present": True, "run_complet": True,
         "comptes_parcelles": 100, "comptes_precedent": 100,
         "coherence_ecarts": 0, "coherence_erreurs": 0, "coherence_frais": True,
         "coherence_acheve": True, "copro_actionnables": 0, "rouge_actionnables": 0,
         "paliers_change": 0, "paliers_total": 100}
    m.update(over)
    return m


def test_gate_refuse_banc_non_acheve():
    """Passage FRAIS mais NON ACHEVÉ (vérification sautée) → échec, run non promu."""
    from labuse.autonomie import controler_run
    v = controler_run(_mesures(coherence_acheve=False,
                               coherence_incomplet_motif="invariants indisponibles : F6"),
                      palier_delta_max_pct=3.0)
    assert v.ok is False
    assert any("NON achevé" in e and "F6" in e for e in v.echecs), v.echecs
    assert "cohérence-achevée" not in v.reussis


def test_gate_accepte_banc_acheve_et_vert():
    """Passage FRAIS, ACHEVÉ et vert (0 écart, 0 erreur) → cohérence au vert."""
    from labuse.autonomie import controler_run
    v = controler_run(_mesures(), palier_delta_max_pct=3.0)
    assert v.ok is True, v.echecs
    assert "cohérence" in v.reussis and "cohérence-achevée" in v.reussis


def test_gate_vieille_base_acheve_absent_garde_comportement():
    """`coherence_acheve` absent (None, base pas migrée) → on ne bloque pas à tort (ancien comportement)."""
    from labuse.autonomie import controler_run
    v = controler_run(_mesures(coherence_acheve=None), palier_delta_max_pct=3.0)
    assert v.ok is True, v.echecs
    assert "cohérence" in v.reussis and "cohérence-achevée" not in v.reussis


def test_gate_acheve_mais_ecart_reste_rouge():
    """Un passage achevé mais avec un faux-client reste un échec (la règle d'origine tient)."""
    from labuse.autonomie import controler_run
    v = controler_run(_mesures(coherence_ecarts=1), palier_delta_max_pct=3.0)
    assert v.ok is False
    assert any("non verte" in e for e in v.echecs), v.echecs


def test_banc_run_echantillon_vide_non_acheve(monkeypatch):
    """`banc.run` sur un échantillon VIDE (base/app inatteignable) → acheve=False + motif, jamais 0/0 vert."""
    import scripts.coherence.banc as banc
    monkeypatch.setattr(banc, "charger_echantillon", lambda: [])
    r = banc.run(ile=True, en_process=False)
    assert r["acheve"] is False
    assert r["comparaisons"] == 0 and r["incomplet_motif"]
    assert r.get("phases") == []


@pytest.mark.db
def test_journal_nomme_le_run_et_scelle_incomplet(engine):
    """Le journal NOMME le run contrôlé et sait sceller un passage NON achevé (marquer_incomplet)."""
    from sqlalchemy import text

    from labuse import coherence_journal as cj

    with engine.begin() as cx:
        cx.execute(text("DROP TABLE IF EXISTS coherence_runs"))

    class _S:
        def __init__(self, cx):
            self.cx = cx

        def execute(self, *a, **k):
            return self.cx.execute(*a, **k)

    with engine.begin() as cx:
        db = _S(cx)
        # un passage ACHEVÉ qui nomme le run servi
        res = cj.journaliser_passage(db, mode="ile", fichier=cj.ECARTS_CSV.parent / "_absent.csv",
                                     run_servi="q_v20", acheve=True)
        assert res["run_servi"] == "q_v20" and res["acheve"] is True and isinstance(res["id"], int)
        row = cx.execute(text("SELECT run_servi, acheve FROM coherence_runs WHERE id = :i"),
                         {"i": res["id"]}).first()
        assert row[0] == "q_v20" and row[1] is True
        # on le scelle NON achevé a posteriori
        cj.marquer_incomplet(db, res["id"], "banc2 indisponible : F6")
        row2 = cx.execute(text("SELECT acheve, incomplet_motif FROM coherence_runs WHERE id = :i"),
                          {"i": res["id"]}).first()
        assert row2[0] is False and "F6" in (row2[1] or "")
