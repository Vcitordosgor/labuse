"""RETOURS-17 — panneau Permis : compteurs et états qui se LISENT juste.

Constat Vic 05/09 : « pourquoi ça dit 50k mais j'ai que 5k récents et 15k dormants ? » — les trois
chips se lisaient comme une répartition alors que deux étaient des fenêtres de temps et la troisième
un total. Correctif : la base se PARTITIONNE en quatre états dont la somme fait le total.

W1 — les 29 498 « autres » mesurés : 70 % sont des permis ACHEVÉS (DAACT). Ils méritent leur ligne.
W2 — bloc total en tête + quatre états empilés (Récent · Dormant · Achevé · Autre) dont la SOMME
     fait le total ; définitions sur les lignes ; DA existante (aucune couleur nouvelle).
W3 — la carte peint chaque point PAR ÉTAT (vert/corail/gris), source unique lib/permisEtats.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

ROOT = Path(__file__).resolve().parents[1]
MP = (ROOT / "frontend/src/components/outils/ModulePanel.tsx").read_text(encoding="utf-8")
MV = (ROOT / "frontend/src/components/map/MapView.tsx").read_text(encoding="utf-8")
LG = (ROOT / "frontend/src/components/map/Legend.tsx").read_text(encoding="utf-8")
ET = (ROOT / "frontend/src/lib/permisEtats.ts").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def client(engine):
    """Base test peuplée de trois permis couvrant Récent / Achevé / Autre (le dormant exige parcelles
    + run notés, hors de ce lot léger ; il compte 0 ici, ce qui n'affecte pas l'invariant de partition)."""
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sitadel_permits (permit_id, type, date, commune, raw, geom) VALUES
              ('R17RECENT', 'PC', now() - interval '2 months', 'Saint-Paul',
               '{"etat": "4"}'::jsonb, ST_SetSRID(ST_MakePoint(55.27, -21.01), 4326)),
              ('R17ACHEVE', 'PC', now() - interval '60 months', 'Saint-Paul',
               '{"etat": "6", "daact": "2021-01-01"}'::jsonb, ST_SetSRID(ST_MakePoint(55.28, -21.02), 4326)),
              ('R17AUTRE', 'DP', now() - interval '60 months', 'Saint-Paul',
               '{"etat": "4"}'::jsonb, NULL)"""))
    try:
        yield TestClient(app)
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM sitadel_permits WHERE permit_id LIKE 'R17%'"))


def _count(client, qs: str) -> int:
    r = client.get(f"/modules/permis?months=240&count_only=true{qs}")
    assert r.status_code == 200, r.text[:300]
    return r.json()["total"]


def test_w1_w2_partition_exacte_somme_egale_total(client):
    """La somme des QUATRE états (Récent + Dormant + Achevé + Autre) fait EXACTEMENT le total en base.
    C'est l'invariant central du mandat : plus jamais trois chips qui ne s'additionnent pas."""
    total = _count(client, "")
    recent = _count(client, "&etat=recent")
    acheve = _count(client, "&etat=acheve")
    autre = _count(client, "&etat=autre")
    dormant = client.get("/modules/promesses?months=36&count_only=true").json()["total"]
    assert recent + dormant + acheve + autre == total, (
        f"partition rompue : {recent}+{dormant}+{acheve}+{autre} != {total}")
    # les trois permis semés tombent chacun dans un état distinct (récent, achevé, autre)
    assert total >= 3 and recent >= 1 and acheve >= 1 and autre >= 1


def test_w1_etat_whitelist_fermee_valeur_libre_ignoree(client):
    """Une valeur d'`etat` hors whitelist retombe sur « tous » (aucune injection, aucun 500)."""
    assert _count(client, "&etat=recent") <= _count(client, "")
    assert _count(client, "&etat=n_importe_quoi") == _count(client, "")   # ignorée → total


def test_w2_cinq_lignes_etat_avec_definitions_sur_les_lignes():
    """Le segment porte les CINQ lignes (Tous + 4 états) avec leur définition COURTE sur la ligne."""
    for k in ("'tous'", "'cours'", "'mort'", "'acheve'", "'autre'"):
        assert k in MP, k
    for label in ("'Récent'", "'Dormant'", "'Achevés'", "'Autres'"):
        assert label in MP, label
    # définitions courtes SUR les lignes (plus dans un paragraphe)
    assert "autorisé ≤ 24 mois" in MP
    assert "ni récent, ni dormant, ni achevé" in MP
    # bloc total en tête + bandeau court
    assert "permis autorisés en base" in MP
    assert "l'instruction déposée n'y figure pas" in MP


def test_w2_w3_source_unique_des_couleurs_aucune_teinte_nouvelle():
    """Une SEULE source de couleurs (lib/permisEtats), reprise par le panneau ET la carte : vert de
    marque (mint), corail historique, gris neutre EXISTANT (st-exclue) — aucune teinte inventée, aucun bleu."""
    # le module de couleurs tire des TOKENS existants, ne pose aucun hex nouveau
    assert "TOKENS.mint" in ET and "TOKENS.coral" in ET and "TOKENS.stExclue" in ET
    assert "'#" not in ET  # aucune couleur HEX en dur (les hex en commentaire documentent le token)
    # panneau et carte importent la MÊME source
    assert "from '../../lib/permisEtats'" in MP
    assert "from '../../lib/permisEtats'" in MV
    assert "PERMIS_ETAT_COLOR" in MV
    # l'ancienne bascule binaire point_mort a disparu du rendu carte
    assert "'point_mort'" not in MV
    # gris = st-exclue #6B7A72 (palette existante, pas une teinte neuve)
    assert "#6B7A72" not in MP and "#6B7A72" not in MV   # jamais en dur : passe par le token


def test_w3_legende_trois_entrees_quand_permis_actif():
    """La légende de carte montre les TROIS couleurs de permis quand l'outil est actif (W3)."""
    assert "PERMIS_LEGENDE" in LG
    assert "moduleActif === 'permis' || moduleActif === 'promesses'" in LG
    # trois entrées dans la source unique (Achevé + Autre fondus en gris)
    assert ET.count("label:") == 3 or ET.count("label:'") + ET.count("label: '") == 3
    assert "Récent (autorisé ≤ 24 mois)" in ET
    assert "Achevé ou autre" in ET
