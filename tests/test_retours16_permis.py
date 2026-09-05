"""RETOURS-16 lot permis (V2-V4) — chips et compteurs qui disent ce qu'ils sont.

V2 : le chip « Autorisé » (état Sitadel « 2 ») est MUET dans la LISTE (information constante au
974 — Sitadel ne publie que des autorisés) ; la FICHE permis garde l'état complet. La puce de
localisation passe en premier et n'est jamais tronquée.
V3 : « Au point mort » → « Dormant » partout (décision Vic) ; la définition reste dans la phrase.
V4 : chaque compteur dit son périmètre — « Tous » = total EN BASE (count_only), plus jamais la
somme de deux fenêtres ; la ligne du bas nomme base/localisés/carte.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[1]
MP = (ROOT / "frontend/src/components/outils/ModulePanel.tsx").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def client(engine):
    """Client léger : deux permis semés (état 2 « Autorisé » + état 4 « Chantier ouvert »),
    l'un localisé — de quoi exercer étiquettes ET compteurs sans le seed démo complet."""
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sitadel_permits (permit_id, type, date, commune, raw, geom)
            VALUES ('R16A0001', 'PC', now() - interval '2 months', 'Saint-Paul',
                    '{"etat": "2"}'::jsonb, ST_SetSRID(ST_MakePoint(55.27, -21.01), 4326)),
                   ('R16A0002', 'PC', now() - interval '3 months', 'Saint-Paul',
                    '{"etat": "4"}'::jsonb, NULL)"""))
    try:
        yield TestClient(app)
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM sitadel_permits WHERE permit_id LIKE 'R16A%'"))


def test_v2_etat_autorise_muet_en_liste(client):
    """Aucune ligne de /modules/permis ne porte l'étiquette « Autorisé » (état 2 → None) ;
    les états qui VARIENT (chantier ouvert…) restent servis par le même mapping."""
    r = client.get("/modules/permis?months=240&limit=500")
    assert r.status_code == 200, r.text[:300]
    items = r.json()["items"]
    par_id = {it["permit_id"]: it for it in items}
    assert par_id["R16A0001"]["etat_label"] is None            # « Autorisé » : muet en liste
    assert par_id["R16A0002"]["etat_label"] == "Chantier ouvert"   # un état qui varie : servi
    from labuse.api.modules import _ETAT_LABELS
    assert _ETAT_LABELS["2"] == "Autorisé"   # la FICHE, elle, garde le libellé complet


def test_v2_puce_localisation_avant_les_autres_chips():
    """La puce de localisation (badge-nongeo) est rendue AVANT le délai et l'état dans le
    span des badges — elle s'affiche en entier, jamais poussée hors de la ligne."""
    assert MP.index("data-permis-badge-nongeo") < MP.index("data-permis-etat")
    badges = MP[MP.index("data-permis-badge-nongeo"):]
    assert badges.index("delai_mois") < badges.index("data-permis-etat")


def test_v3_dormant_partout_plus_de_point_mort_visible():
    """Les chaînes VISIBLES disent « Dormant » ; la définition (autorisé ancien sans achèvement
    déclaré) reste dans la phrase d'explication. « point mort » ne survit qu'en commentaire."""
    assert "'mort', 'Dormant'" in MP
    assert "« Dormant » = autorisé ancien sans achèvement déclaré (DAACT)" in MP
    assert "'Au point mort'" not in MP and "au point mort ·" not in MP
    assert "'Dormant — permis de construire" in MP or "Dormant — permis de construire" in MP
    reg = (ROOT / "frontend/src/components/outils/registry.ts").read_text(encoding="utf-8")
    assert "permis dormants" in reg and "les permis au point mort" not in reg
    ctx = (ROOT / "frontend/src/components/contexte/ContextePanel.tsx").read_text(encoding="utf-8")
    assert 'lbl="Permis dormants"' in ctx and "Permis au point mort" not in ctx
    # le Copilote route toujours le vocabulaire ancien, mais AFFICHE le nouveau libellé
    ans = (ROOT / "src/labuse/copilote_v2/answering.py").read_text(encoding="utf-8")
    assert '("promesses", "Permis dormants")' in ans
    assert '"permis au point mort"' in ans   # synonyme conservé (vocabulaire utilisateur)


def test_v4_count_only_et_chip_tous_en_base(client):
    """« Tous » compte la BASE (count_only léger, ni lignes ni carte) — plus la somme 24m+36m."""
    r = client.get("/modules/permis?months=240&count_only=true")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert set(d) >= {"total", "geocodes"} and "items" not in d and "carte" not in d
    # cohérence : total count_only == total du chemin liste (même périmètre)
    full = client.get("/modules/permis?months=240&limit=1").json()
    assert d["total"] == full["total"] and d["total"] >= 2
    assert d["geocodes"] == full["geocodes"]
    # le front branche bien le chip « Tous » dessus
    assert "modPermisCount(240)" in MP
    assert "radarEntryTotal + pmEntryTotal" not in MP   # la somme trompeuse a disparu


def test_v4_ligne_du_bas_nomme_ses_perimetres():
    """Le pied de liste dit « en base » / « sur ce filtre » / « localisés » — plus un nombre nu."""
    assert "en base (toute la profondeur Sitadel)" in MP
    assert "sur ce filtre" in MP
    assert "localisés" in MP
    assert "PC dormants" in MP
    # chaque chip du segment porte son périmètre (title)
    assert "Tous les permis en base (toute la profondeur Sitadel servie)." in MP
    assert "24 derniers mois de données Sitadel" in MP
