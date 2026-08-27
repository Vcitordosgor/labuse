"""E6 (parcours d'entrée) — l'engagement 12 mois est cohérent et l'échéance annuelle correcte."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from labuse import comptes
from labuse.db import session_scope
from labuse.offres import offre_integral

pytestmark = pytest.mark.db


def test_engagement_source_unique():
    assert offre_integral()["engagement_mois"] == 12


def test_cgv_dit_l_engagement(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    c = TestClient(app, base_url="https://testserver")
    html = c.get("/cgv").text
    assert "12 mois" in html and "reconduit tacitement" in html.lower().replace("é", "é")


def test_avis_echeance_ancre_sur_activation_annuelle(engine):
    """L'échéance Chatel tombe ~2 mois avant le 1er anniversaire de l'ACTIVATION (12 mois),
    pas de la création — et l'avis n'est dû qu'une fois par terme."""
    email = f"eng-{uuid.uuid4().hex[:8]}@ex.test"
    with session_scope() as db:
        inv = comptes.creer_invitation(db, email)
        tok = inv["lien"].split("token=")[1]
        comptes.activer_par_invitation(db, tok, "MotDePasse123!", "2026-07-23")
        from sqlalchemy import text
        db.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        # activation il y a ~10 mois (via un événement stripe_activation daté)
        activation = date.today() - timedelta(days=305)
        db.execute(text("INSERT INTO evenements_compte (type, compte_id, at) "
                        "VALUES ('stripe_activation', :c, :t)"),
                   {"c": inv["compte_id"], "t": activation})
        db.commit()
        dus = comptes.avis_echeance_dus(db)
        mien = [d for d in dus if d["email"] == email]
        assert mien, "l'avis Chatel devrait être dû ~2 mois avant l'anniversaire annuel"
        ech = date.fromisoformat(mien[0]["echeance"])
        # échéance = activation + 12 mois (à quelques jours près pour les années bissextiles)
        attendu = activation.replace(year=activation.year + 1)
        assert abs((ech - attendu).days) <= 1
