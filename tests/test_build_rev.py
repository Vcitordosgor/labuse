"""MISE-EN-LIGNE-1 — le tampon de version des PDF/fiches ne ment plus en prod (rsync sans .git) :
repli sur le marqueur `config/deploiement.json` écrit par deploy_app.sh à chaque mise en ligne."""
import json

from labuse.build_rev import deploiement_sha


def test_marqueur_lisible(tmp_path):
    p = tmp_path / "deploiement.json"
    p.write_text(json.dumps({"sha": "502ff7c03aabbccdd", "deploye_le": "2026-11-21"}),
                 encoding="utf-8")
    assert deploiement_sha(p) == "502ff7c03aab"   # tronqué à 12


def test_marqueur_absent_ou_cabosse(tmp_path):
    assert deploiement_sha(tmp_path / "absent.json") is None
    p = tmp_path / "cabosse.json"
    p.write_text("{pas du json", encoding="utf-8")
    assert deploiement_sha(p) is None
    p2 = tmp_path / "sans_sha.json"
    p2.write_text(json.dumps({"deploye_le": "2026-11-21"}), encoding="utf-8")
    assert deploiement_sha(p2) is None


def test_commit_build_retombe_sur_le_marqueur(monkeypatch, tmp_path):
    """Sans env NI git (prod), _commit_build sert le sha du marqueur — plus jamais un PDF sans version."""
    from labuse import build_rev
    from labuse.exports import etude_faisabilite as ef
    monkeypatch.delenv("LABUSE_BUILD_COMMIT", raising=False)
    p = tmp_path / "deploiement.json"
    p.write_text(json.dumps({"sha": "abcdef123456789"}), encoding="utf-8")
    monkeypatch.setattr(build_rev, "_MARQUEUR", p)
    # neutralise git (prod : pas de dépôt) — rev-parse échoue
    import subprocess

    def _pas_de_git(*a, **k):
        raise FileNotFoundError("git absent (prod)")
    monkeypatch.setattr(subprocess, "run", _pas_de_git)
    assert ef._commit_build() == "abcdef123456"
