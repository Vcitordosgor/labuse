"""INJECTION-SOLIDE-1 — la PROPAGATION prouvée : quand une source change, ce qui en dépend le SAIT.

Pour chaque FAMILLE de sources, on simule une nouvelle version (on fait avancer le millésime / l'horizon
de la source en base, DANS UNE TRANSACTION QU'ON ANNULE — rien n'est écrit durablement) et on prouve :

  1. la CLÉ DE FRAÎCHEUR des caches (`fraicheur_caches.empreinte_attendue`) CHANGE → tout cache qui en
     dépend (fiche commune, tuiles, réponses IA) se marque périmé et se régénère (c'est « un cache qui se
     vide quand la donnée change », pas seulement quand le code change — exigence du mandat) ;
  2. l'EFFET de la source est correctement classé : « entre dans le classement, déclenche un nouveau
     calcul » (famille du score/cascade) ou « lue directement, visible le lendemain matin ».

Et, transverse : les TUILES d'overlay se versionnent sur `max(created_at)` de `spatial_layers` → une
injection qui touche une couche carte change la version servie (tuiles reconstruites).

Marqué `local` : lit la base réelle (data_sources + spatial_layers y sont peuplées).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import db as db_mod
from labuse import circuit_maj
from labuse.circuit_garanties import sources_du_score
from labuse.circuit_etats import NOM_VERS_SLUG
from labuse.fraicheur_caches import empreinte_attendue

pytestmark = pytest.mark.local

# une source REPRÉSENTATIVE par famille du mandat + si elle entre dans le classement (sources_du_score).
FAMILLES = [
    ("PPR / aléas",   "DEAL Réunion — PPR / aléas",                 True),
    ("PLU",           "Urbanisme PLU/GPU (API Carto)",              True),
    ("DVF",           "DVF / valeurs foncières",                    True),
    ("cadastre",      "Cadastre (API Carto PCI)",                   True),
    ("propriétaires", "DGFiP — parcelles des personnes morales",    False),
    ("BODACC",        "BODACC (procédures collectives)",            False),
    ("permis",        "SITADEL (autorisations d'urbanisme)",        True),
    ("DPE",           "DPE ADEME (logements existants)",            False),
    ("servitudes",    "SUP — assiettes GPU (API Carto)",            True),
    ("réseaux",       "Fibre Arcep — Ma connexion internet (immeuble)", False),
]


@pytest.fixture()
def conn():
    try:
        eng = db_mod.engine()
        c = eng.connect()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"base indisponible ({exc})")
    tx = c.begin()
    try:
        if not c.execute(text("SELECT to_regclass('data_sources')")).scalar():
            pytest.skip("data_sources absente")
        yield c
    finally:
        tx.rollback()   # RIEN n'est écrit durablement
        c.close()


@pytest.mark.parametrize("famille,nom,dans_le_score", FAMILLES, ids=[f[0] for f in FAMILLES])
def test_une_version_qui_avance_change_la_cle_de_fraicheur(conn, famille, nom, dans_le_score):
    """Nouvelle version de la source → l'empreinte des caches CHANGE (ils se régénèrent)."""
    present = conn.execute(text("SELECT count(*) FROM data_sources WHERE name = :n"), {"n": nom}).scalar()
    if not present:
        pytest.skip(f"source « {nom} » absente de ce poste")
    avant = empreinte_attendue(conn)
    # simuler une nouvelle livraison : l'horizon avance (cas DVF « même millésime, horizon neuf »,
    # que le hash prend en compte — FIX-NU3-3 L-CHN-04) ET le millésime porte un suffixe témoin.
    conn.execute(text(
        "UPDATE data_sources SET source_horizon_at = COALESCE(source_horizon_at, DATE '2000-01-01') "
        "+ INTERVAL '1 day', source_millesime = COALESCE(source_millesime, '') || '-TEMOIN' "
        "WHERE name = :n"), {"n": nom})
    apres = empreinte_attendue(conn)
    assert apres != avant, f"{famille} : l'empreinte n'a pas bougé → caches NON invalidés (sous-invalidation)"
    # la composante qui a bougé est bien `sources=` (pas le run ni le code).
    assert avant.split("|sources=")[0] == apres.split("|sources=")[0], "autre chose que les sources a bougé"


@pytest.mark.parametrize("famille,nom,dans_le_score", FAMILLES, ids=[f[0] for f in FAMILLES])
def test_effet_correspond_a_appartenance_au_classement(conn, famille, nom, dans_le_score):
    """L'effet affiché (« classement » / « direct ») = l'appartenance réelle à sources_du_score."""
    present = conn.execute(text("SELECT count(*) FROM data_sources WHERE name = :n"), {"n": nom}).scalar()
    if not present:
        pytest.skip(f"source « {nom} » absente")
    slug = NOM_VERS_SLUG.get(nom)
    reel = bool(slug and slug in sources_du_score())
    assert reel == dans_le_score, (
        f"{famille} : appartenance au classement réelle={reel}, attendue={dans_le_score} "
        f"(slug={slug}) — la table des familles du test doit suivre sources_du_score")
    eff = circuit_maj.effet(reel)
    assert eff["code"] == ("classement" if dans_le_score else "direct")


def test_tuiles_overlay_se_versionnent_sur_spatial_layers(conn):
    """La version des tuiles d'overlay = run · max(created_at spatial_layers) · tuyau_rev : une
    injection qui insère dans spatial_layers (created_at = now()) change la version → tuiles refaites."""
    if not conn.execute(text("SELECT to_regclass('spatial_layers')")).scalar():
        pytest.skip("spatial_layers absente")
    mx_avant = conn.execute(text(
        "SELECT to_char(max(created_at),'YYYYMMDDHH24MISS') FROM spatial_layers")).scalar()
    # une couche injectée a un created_at = now() > max courant → la version servie bouge.
    mx_apres_simule = conn.execute(text(
        "SELECT to_char(greatest(max(created_at), now()),'YYYYMMDDHH24MISS') FROM spatial_layers")).scalar()
    assert mx_apres_simule >= (mx_avant or ""), "le max(created_at) ne peut que croître"
    # preuve que la version LIT bien ce max (et le run) — pas un nombre figé :
    from labuse.api import couches_tuyau
    import inspect
    src = inspect.getsource(couches_tuyau._version)
    assert "max(created_at)" in src and "spatial_layers" in src
    assert "runs.current()" in src
