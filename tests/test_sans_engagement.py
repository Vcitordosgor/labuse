"""S1 (sans engagement) — Intégral est mensuel SANS engagement ; anti-régression.

Décision Vic 27/08/2026 : plus de durée ferme de 12 mois, plus de reconduction annuelle, plus de
loi Chatel. Ce test échoue si « engagement », « 12 mois » (hors le plafond de responsabilité de
l'article 9) ou « L. 215-1 » réapparaît dans les écrans ou les CGV.
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from labuse import comptes
from labuse.db import session_scope
from labuse.offres import offre_integral

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    return TestClient(app, base_url="https://testserver")


def _token_client() -> str:
    email = f"cli-{uuid.uuid4().hex[:8]}@exemple.test"
    with session_scope() as db:
        inv = comptes.creer_invitation(db, email)
    return inv["lien"].split("token=")[1]


def test_offre_integral_sans_engagement():
    o = offre_integral()
    assert o["engagement"] is False
    assert "engagement_mois" not in o
    assert o["periodicite"] == "mois"


def test_ecran_invitation_dit_sans_engagement(client):
    html = client.get(f"/invitation?token={_token_client()}").text
    assert "sans engagement" in html.lower()
    assert "engagement 12 mois" not in html.lower()


BANNIS = ("engagement 12", "12 mois", "durée ferme", "reconduction annuelle",
          "reconduit tacitement pour", "L. 215-1", "L.215-1", "loi chatel", "avis d'échéance",
          "date anniversaire")


def _sans_bannis(html: str, *, autoriser_resp_9: bool) -> list[str]:
    """Renvoie les termes bannis trouvés. L'article 9 (plafond de responsabilité sur 12 mois
    glissants) est une notion DIFFÉRENTE, autorisée à porter « 12 » — on neutralise cette phrase."""
    texte = html
    if autoriser_resp_9:
        # retirer la phrase du plafond de responsabilité (12 derniers mois) avant le contrôle
        texte = re.sub(r"douze \(12\) derniers mois", "«resp9»", texte, flags=re.I)
    bas = texte.lower()
    return [b for b in BANNIS if b.lower() in bas]


def test_cgv_sans_engagement_ni_chatel(client):
    html = client.get("/cgv").text
    trouves = _sans_bannis(html, autoriser_resp_9=True)
    assert not trouves, f"termes d'engagement/Chatel réapparus dans les CGV : {trouves}"
    # l'article 5 dit la bonne chose
    assert "sans engagement" in html.lower()
    assert "demande écrite adressée à labuse" in html.lower()
    # l'article 9 (responsabilité, 12 mois glissants) est bien CONSERVÉ
    assert "douze (12) derniers mois" in html


def test_art9_responsabilite_conserve_le_12_mois(client):
    """Garde-fou inverse : le « 12 mois » de l'article 9 NE doit PAS avoir été supprimé par erreur."""
    html = client.get("/cgv").text
    assert "responsabilité" in html.lower() and "douze (12) derniers mois" in html


def test_mentions_et_paiement_sans_avis_echeance(client):
    for url in ("/mentions-legales",):
        html = client.get(url).text
        assert "avis d'échéance" not in html.lower() and "215-1" not in html


def test_avis_echeance_commande_neutralisee():
    """La commande CLI existe encore mais est un no-op (ne déclenche plus rien)."""
    from typer.testing import CliRunner

    from labuse.cli import app as cli_app
    r = CliRunner().invoke(cli_app, ["avis-echeance"])
    assert r.exit_code == 0
    assert "sans objet" in r.output.lower()


def test_fonctions_chatel_supprimees():
    """Les fonctions de la mécanique Chatel n'existent plus (rien de mort)."""
    assert not hasattr(comptes, "declencher_avis_echeance")
    assert not hasattr(comptes, "avis_echeance_dus")
    from labuse import emails
    assert not hasattr(emails, "avis_echeance")
