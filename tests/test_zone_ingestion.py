"""ÉTUDE DE ZONE · Z1 — ingestion SIRENE établissements + MOBPRO.

On gèle deux invariants légaux/produit :
  · SIRENE : un établissement en DIFFUSION PARTIELLE ('P', personne physique opposée) n'a NI nom NI
    adresse stockés en clair — seuls SIRET/NAF/geom/commune (diffusibles) subsistent. Obligation légale.
  · MOBPRO : agrégat des emplois au LIEU DE TRAVAIL par commune (974), pondéré IPONDI.
Données de test créées puis PURGÉES (aucune trace résiduelle).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.ingestion import seed_sources
from labuse.ingestion.mobpro import build_mobpro, ensure_tables as mobpro_ens
from labuse.ingestion.sirene_etablissements import build_sirene_etablissements, ensure_tables as se_ens

pytestmark = pytest.mark.db

_SIRENE_CSV = """siret,activitePrincipaleEtablissement,denominationUsuelleEtablissement,enseigne1Etablissement,numeroVoieEtablissement,typeVoieEtablissement,libelleVoieEtablissement,codeCommuneEtablissement,etatAdministratifEtablissement,statutDiffusionEtablissement,longitude,latitude
90000000000011,10.71C,BOULANGERIE DU CENTRE,,12,RUE,DE LA GARE,97409,A,O,55.6556,-20.9332
90000000000022,10.71C,MONSIEUR DUPONT,,5,RUE,DES FLEURS,97409,A,P,55.6560,-20.9340
90000000000033,10.71C,PAIN CREOLE,AU PAIN CREOLE,8,AV,BOURBON,97409,A,O,55.6570,-20.9310
90000000000044,10.71C,BOULANGERIE FERMEE,,1,RUE,X,97409,F,O,55.6540,-20.9350
90000000000055,10.71C,HORS 974,,1,RUE,Y,75001,A,O,2.35,48.85
"""

_MOBPRO_CSV = """COMMUNE;DCLT;IPONDI
97411;97409;120.0
97409;97409;80.5
97409;97411;15.0
75056;75056;9.0
"""


@pytest.fixture
def sirene(engine, tmp_path):
    p = tmp_path / "sirene.csv"
    p.write_text(_SIRENE_CSV, encoding="utf-8")
    with session_scope() as s:
        seed_sources.seed(s)
        se_ens(s)
        r = build_sirene_etablissements(s, file=str(p))
    yield r
    with session_scope() as s:
        s.execute(text("DELETE FROM sirene_etablissements WHERE siret LIKE '9000000000%'"))


def test_sirene_diffusion_partielle_masque_nom_et_adresse(sirene):
    with session_scope() as s:
        rows = {r["siret"]: dict(r) for r in s.execute(text(
            "SELECT siret, naf, denomination, adresse, diffusible FROM sirene_etablissements "
            "WHERE siret LIKE '9000000000%'")).mappings()}
    # actifs 974 géolocalisés seulement : le fermé (F) et le hors-974 sont écartés
    assert set(rows) == {"90000000000011", "90000000000022", "90000000000033"}
    # l'établissement en diffusion PARTIELLE ('P') : nom ET adresse NULL, mais NAF conservé
    p = rows["90000000000022"]
    assert p["diffusible"] is False
    assert p["denomination"] is None and p["adresse"] is None, "diffusion partielle : ni nom ni adresse en clair"
    assert p["naf"] == "1071C", "le NAF (diffusible) est conservé — l'établissement compte dans la zone"
    # un établissement diffusible garde son nom
    assert rows["90000000000011"]["denomination"] == "BOULANGERIE DU CENTRE"


def test_sirene_naf_normalise_le_point(sirene):
    with session_scope() as s:
        nafs = {r[0] for r in s.execute(text("SELECT DISTINCT naf FROM sirene_etablissements WHERE siret LIKE '9000000000%'"))}
    assert nafs == {"1071C"}, "le NAF '10.71C' est normalisé en '1071C' (comparable à la BPE/maquette)"


def test_mobpro_agrege_les_emplois_au_lieu_de_travail(engine, tmp_path):
    p = tmp_path / "mobpro.csv"
    p.write_text(_MOBPRO_CSV, encoding="utf-8")
    with session_scope() as s:
        seed_sources.seed(s)
        mobpro_ens(s)
        build_mobpro(s, file=str(p), millesime="MOBPRO test")
    with session_scope() as s:
        emplois = {r[0]: r[1] for r in s.execute(text(
            "SELECT insee, emplois_lieu_travail FROM mobpro_commune WHERE insee LIKE '974%'"))}
    # LIEU DE TRAVAIL 97409 : 120 (depuis 97411) + 80,5 (depuis 97409) = 200,5 → 200 ; 97411 = 15
    assert emplois["97409"] == 200 and emplois["97411"] == 15
    assert "75056" not in emplois, "seul le 974 est retenu (DCLT)"
    with session_scope() as s:
        s.execute(text("DELETE FROM mobpro_commune WHERE millesime='MOBPRO test'"))
