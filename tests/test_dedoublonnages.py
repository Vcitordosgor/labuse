"""CONNEXIONS-2 Lot 9 — Dédoublonnages (KO-12 transport mail, KO-13 BAN, KO-15 ratio assemblage).

Ces gardes ÉCHOUENT si un second transport mail est instancié, ou si un second géocodeur BAN réapparaît.
"""
from __future__ import annotations

import pathlib

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.db

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "labuse"


def _fichiers_contenant(motif: str) -> list[str]:
    """Noms de fichiers .py de src/labuse contenant `motif` (chemin relatif à src/labuse)."""
    out = []
    for p in SRC.rglob("*.py"):
        try:
            if motif in p.read_text(encoding="utf-8"):
                out.append(str(p.relative_to(SRC)))
        except Exception:  # noqa: BLE001
            pass
    return sorted(set(out))


def test_transport_mail_unique():
    """KO-12 — une SEULE façade d'envoi (`mail`), un seul point pour chaque voie de livraison :
    · SMTP instancié UNIQUEMENT dans mail.py ;
    · l'appel HTTP Brevo UNIQUEMENT dans brevo.py ;
    · l'ENVOI templatisé (`brevo.envoyer_template(...)`) appelé UNIQUEMENT par la façade mail.py.
    Échoue si un second transport est instancié ou si Brevo est appelé en direct ailleurs."""
    assert _fichiers_contenant("smtplib.SMTP(") == ["mail.py"]
    assert _fichiers_contenant("api.brevo.com") == ["brevo.py"]
    assert _fichiers_contenant("brevo.envoyer_template(") == ["mail.py"]


def test_mail_facade_delegue_a_brevo(monkeypatch):
    """KO-12 — `mail.envoyer_template` est LA façade : elle délègue à Brevo (une seule voie templatisée)."""
    from labuse import brevo, mail
    vu = {}
    monkeypatch.setattr(brevo, "envoyer_template",
                        lambda to, key, params=None: vu.update(to=to, key=key) or {"envoye": True})
    assert mail.envoyer_template("a@b.c", "essai", {"nom": "X"}) == {"envoye": True}
    assert vu == {"to": "a@b.c", "key": "essai"}


def test_geocode_ban_unique_source():
    """KO-13 — un seul BAN_URL : audit ré-exporte celui de `geocode` ; scoreur ne redéfinit plus le sien ;
    ni audit.py ni scoreur.py ne contiennent l'URL /search en dur (une seule vérité : geocode.py)."""
    from labuse import audit, geocode
    from labuse.api import scoreur
    assert audit.BAN_URL is geocode.BAN_URL
    assert not hasattr(scoreur, "BAN_URL")
    assert "api-adresse.data.gouv.fr/search" not in (SRC / "audit.py").read_text(encoding="utf-8")
    assert "api-adresse.data.gouv.fr/search" not in (SRC / "api" / "scoreur.py").read_text(encoding="utf-8")


def test_geocode_ban_appele_par_les_deux(monkeypatch, db_session):
    """KO-13 — audit ET scoreur passent par la fonction UNIQUE `geocode.geocode_ban`."""
    from labuse import audit, geocode
    from labuse.api import scoreur

    # scoreur : délègue + traduit l'erreur BAN en HTTP 404
    monkeypatch.setattr(geocode, "geocode_ban",
                        lambda q, **k: {"lon": 55.0, "lat": -21.0, "label": q, "properties": {}})
    assert scoreur._geocode("1 rue Test 97400")["lon"] == 55.0

    def _introuvable(q, **k):
        raise geocode.BanIntrouvable("x")
    monkeypatch.setattr(geocode, "geocode_ban", _introuvable)
    with pytest.raises(HTTPException) as ex:
        scoreur._geocode("adresse inconnue")
    assert ex.value.status_code == 404
    # audit : même géocodeur → « introuvable » propagé en AuditResult
    r = audit.audit_by_address(db_session, "adresse inconnue")
    assert r["ok"] is False and r["error"] == "introuvable"
