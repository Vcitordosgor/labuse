"""DEPLOY-GROUPE-3 — le `jobs selftest` tolère un harnais verite-permanente SAUTÉ/ROUGE.

Régression d'intégration (merge OPS-3) : `scripts.verite_permanente._harnais()` renvoie, pour les
lots authentifiés A/B/F SANS instance au moment du selftest, un dict `{skip|rouge}` SANS clé `cmd`.
Le selftest (jobs.py) itérait `h["cmd"]` sans garde → `KeyError('cmd')` → déploiement REFUSÉ à tort.
Ce test verrouille que le selftest ne lève plus sur un harnais sans `cmd`.
"""
from __future__ import annotations


def test_harnais_sans_prerequis_a_des_entrees_sans_cmd():
    """Sans LABUSE_HARNAIS_BASE, les lots A/B/F sont en état « skip » (pas de clé `cmd`)."""
    import scripts.verite_permanente as vp
    hs = vp._harnais()                       # ni cookie ni instance
    sans_cmd = [h for h in hs if "cmd" not in h]
    assert sans_cmd, "au moins un lot (A/B/F) doit être sauté sans prérequis d'instance"
    # et le mécanisme de lecture du selftest ne lève pas dessus
    for h in hs:
        list(a for a in h.get("cmd", []) if isinstance(a, str))


def test_selftest_ne_leve_pas_sur_harnais_sans_cmd():
    """Le selftest renvoie (ok, problèmes) sans jamais lever KeyError('cmd')."""
    from labuse.jobs import selftest
    ok, problemes = selftest()
    assert not any("KeyError('cmd')" in p or "runner non chargeable" in p for p in problemes), \
        f"le selftest ne doit plus échouer sur le harnais verite-permanente : {problemes}"
    assert isinstance(ok, bool)
