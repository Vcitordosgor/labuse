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
    # même porte que dev_mode : la protection anti-scraping est court-circuitée quand le flag est posé.
    # QUOTA-FICHE a étendu la condition avec le mode local (`_mode_local_dev`) ; `rate_limit_off` reste
    # un terme du court-circuit — c'est ce qu'on garde ici (sans figer la fin de la ligne).
    src = Path(__file__).resolve().parents[1] / "src/labuse/api/protection.py"
    txt = src.read_text(encoding="utf-8")
    assert "if s.dev_mode or s.rate_limit_off or " in txt


def test_banc_ne_depend_pas_de_dev_mode():
    """PRE-DEPLOY-1 — garde-fou : le banc de cohérence ne DÉPEND JAMAIS de LABUSE_DEV_MODE / dev_mode
    (il a son propre levier local, LABUSE_RATE_LIMIT_OFF).

    CI-1 : on vérifie l'absence de DÉPENDANCE DE CODE, pas du simple mot — les docstrings de banc.py /
    lib.py mentionnent légitimement « LABUSE_DEV_MODE » pour EXPLIQUER qu'elles ne s'en servent pas.
    On retire donc commentaires ET chaînes (tokenize) avant de chercher le token dans le CODE restant."""
    import io
    import tokenize

    def _code_nu(src: str) -> str:
        toks = []
        try:
            for t in tokenize.generate_tokens(io.StringIO(src).readline):
                if t.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                toks.append(t.string)
        except tokenize.TokenError:
            return src                      # fichier tronqué improbable → repli prudent (texte brut)
        return " ".join(toks)

    banc_dir = Path(__file__).resolve().parents[1] / "scripts/coherence"
    for py in banc_dir.glob("*.py"):
        code = _code_nu(py.read_text(encoding="utf-8"))
        assert "LABUSE_DEV_MODE" not in code and "dev_mode" not in code, f"{py.name} dépend de dev_mode"
