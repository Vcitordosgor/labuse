"""FRONT-CHIFFRES-2 — LABUSE_RATE_LIMIT_OFF : court-circuiter la protection anti-scraping sans
dev_mode. But : rejouer le banc de cohérence pendant des redémarrages d'API en DEV sans que le
compteur 60/min (ou les quotas de consultation) ne le bloque. PRE-DEPLOY-1 : le banc ne doit
JAMAIS dépendre de LABUSE_DEV_MODE.
"""
from __future__ import annotations

from pathlib import Path


def test_rate_limit_off_wire_et_off_par_defaut(monkeypatch):
    from labuse import config
    # off par défaut (prod ne le pose pas)
    monkeypatch.delenv("LABUSE_RATE_LIMIT_OFF", raising=False)
    config.get_settings.cache_clear()
    assert config.get_settings().rate_limit_off is False
    # posé à 1 → actif
    monkeypatch.setenv("LABUSE_RATE_LIMIT_OFF", "1")
    config.get_settings.cache_clear()
    assert config.get_settings().rate_limit_off is True
    monkeypatch.delenv("LABUSE_RATE_LIMIT_OFF")
    config.get_settings.cache_clear()


def test_middleware_court_circuite_sur_le_flag_comme_dev_mode():
    # même porte que dev_mode : la protection anti-scraping est court-circuitée quand le flag est posé
    src = Path(__file__).resolve().parents[1] / "src/labuse/api/protection.py"
    txt = src.read_text(encoding="utf-8")
    assert "if s.dev_mode or s.rate_limit_off:" in txt


def test_banc_ne_depend_pas_de_dev_mode():
    """PRE-DEPLOY-1 — garde-fou : le banc de cohérence ne référence JAMAIS LABUSE_DEV_MODE / dev_mode
    (il a son propre levier local, LABUSE_RATE_LIMIT_OFF)."""
    banc_dir = Path(__file__).resolve().parents[1] / "scripts/coherence"
    for py in banc_dir.glob("*.py"):
        t = py.read_text(encoding="utf-8")
        assert "LABUSE_DEV_MODE" not in t and "dev_mode" not in t, f"{py.name} dépend de dev_mode"
