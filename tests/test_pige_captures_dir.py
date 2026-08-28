"""GARDE RV2-V1 (retours visuels 2) — le répertoire de captures Radar : diagnostic écrivable/nommé.

En prod, déposer une capture renvoyait « répertoire privé inaccessible » : le répertoire par défaut
(/srv/labuse/pige/captures) n'existait pas et l'utilisateur `labuse` ne pouvait pas le créer. Le refus
était propre (rien de faux en base) mais le Radar était inutilisable — et le message ne NOMMAIT pas le
chemin fautif.

Ces tests figent le contrat de `captures_dir_writable()` : elle tente la création + un témoin d'écriture,
retourne (ok, detail) et `detail` NOMME toujours le chemin. Sans base ni réseau.
"""
from __future__ import annotations

from labuse.pige.tables import captures_dir, captures_dir_writable


def test_writable_ok_sur_repertoire_accessible(tmp_path, monkeypatch):
    """Répertoire accessible (créé à la volée) → (True, chemin)."""
    cible = tmp_path / "pige" / "captures"
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", str(cible))
    ok, detail = captures_dir_writable()
    assert ok is True
    assert str(cible) in detail
    assert cible.is_dir()   # la fonction CRÉE le répertoire manquant (mkdir -p)


def test_writable_ko_nomme_le_chemin_fautif(monkeypatch):
    """Répertoire non créable (parent système en lecture seule) → (False, message QUI NOMME le chemin)."""
    interdit = "/proc/labuse-interdit/captures"   # /proc est en lecture seule : mkdir échoue partout
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", interdit)
    ok, detail = captures_dir_writable()
    assert ok is False
    assert interdit in detail, "le message d'échec doit NOMMER le chemin fautif (pas un message générique)"
    assert "inaccessible" in detail.lower()


def test_captures_dir_hors_repertoire_applicatif(monkeypatch):
    """Le chemin par défaut vit HORS de l'app (/opt/labuse/app) — un déploiement ne l'efface pas."""
    monkeypatch.delenv("LABUSE_PIGE_CAPTURES_DIR", raising=False)
    d = str(captures_dir())
    assert "/opt/labuse/app" not in d, "les captures ne doivent PAS vivre sous le répertoire de l'app"
