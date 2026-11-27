"""OUTIL-COMMUNES-FIX-7 — LOT 0 : le FILET. Un test par témoin du recontrôle
(`~/Desktop/audit-outils/03-COMMUNES-ASTRA-5.md`, liste « C'est faux »), valeur PRÉCISE. Écrits AVANT
correction : rouges maintenant, verts une fois les LOTS 1-3 livrés.

  · seuil de diffusion du prix de SECTION appliqué PARTOUT (pas écran par écran) :
      97415000CD (Saint-Paul) : 1 vente dans les bornes → AUCUN prix de terrain ni au Carnet de secteur,
      ni à la fiche parcelle (dvf_parcelle.secteur) ; Comparer le masque déjà ;
      97401000AT (Les Avirons) et 97408000AB (La Possession) : 7 ventes de maison utilisées sur 8 → sous
      le seuil → AUCUN prix de maison (le bâti comptait tous les actes au lieu des ventes utilisées).
  · révisions — date de la dernière pièce IDENTIFIÉE de la révision générale :
      Saint-Leu 18/11/2026 (avis commission d'enquête), Saint-André 03/10/2025 (avis MRAe),
      Les Trois-Bassins mai 2025 (PADD de concertation). (3 dates servies encore au 31/12/2024.)
  · Plaine-des-Palmistes : le lien de source ne pointe plus vers le domaine mort www.plaine-des-palmistes.re.

(Le grand bandeau « État du PLU » qui porte la date : `frontend/src/lib/plu.test.ts`.)

Tests `db` : skip sans cache secteur. Lisent les VRAIS lecteurs (Carnet, fiche parcelle flash)."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


def _skip_sans_cache(c):
    try:
        if not c.execute(text("SELECT 1 FROM dvf_secteur_medianes LIMIT 1")).scalar():
            pytest.skip("cache dvf_secteur_medianes vide")
    except Exception:  # noqa: BLE001
        pytest.skip("cache dvf_secteur_medianes absent")


def _carnet_prix(c, secteur):
    """Les prix DVF par type du Carnet de secteur (api/carnet.py::_carnet) : prix['dvf'][type_bien]."""
    from labuse.api import carnet as carnet_mod
    return ((carnet_mod._carnet(secteur, Session(bind=c)) or {}).get("prix") or {}).get("dvf") or {}


@pytest.mark.db
def test_carnet_cd_terrain_aucun_prix():
    """Carnet de la section CD de Saint-Paul : 1 vente dans les bornes → le prix de terrain (133 €/m²)
    ne doit PAS être diffusé (sous le seuil de 8). Même seuil que Comparer, appliqué au Carnet."""
    from labuse.db import engine
    with engine().connect() as c:
        _skip_sans_cache(c)
        prix = _carnet_prix(c, "97415000CD")
        terr = prix.get("terrain") or {}
        assert terr.get("mediane_prix_m2") is None, \
            f"CD terrain : 1 vente < seuil → aucun prix diffusé, obtenu {terr.get('mediane_prix_m2')}"


@pytest.mark.db
@pytest.mark.parametrize("secteur,commune", [("97401000AT", "Les Avirons"), ("97408000AB", "La Possession")])
def test_carnet_maison_section_sous_seuil(secteur, commune):
    """Maisons par section : l'effectif = les ventes UTILISÉES dans la médiane (dans les bornes), pas le
    total des actes. AT et AB ont 7 ventes utilisées sur 8 → sous le seuil de 8 → AUCUN prix de maison."""
    from labuse.db import engine
    with engine().connect() as c:
        _skip_sans_cache(c)
        maison = (_carnet_prix(c, secteur).get("maison") or {})
        assert maison.get("mediane_prix_m2") is None, \
            f"{commune} {secteur} : 7 ventes utilisées < 8 → aucun prix de maison, obtenu {maison.get('mediane_prix_m2')}"


@pytest.mark.db
def test_fonction_unique_prix_section_cd_terrain():
    """La fonction UNIQUE `prix_section` (LOT 1) — celle que la fiche parcelle, Comparer, le Carnet et le
    Bilan appellent tous — applique le seuil : CD terrain (1 vente) → pas de prix (assez=False). Rouge
    maintenant (la fonction n'existe pas), vert au LOT 1."""
    from labuse.db import engine
    from labuse.dvf_secteur import prix_section   # n'existe qu'après le LOT 1
    with engine().connect() as c:
        _skip_sans_cache(c)
        r = prix_section(Session(bind=c), "97415000CD", "terrain")
        assert r["assez"] is False and r["prix_m2"] is None, \
            f"CD terrain : 1 vente < seuil → pas de prix, obtenu {r}"
        assert r["n"] == 1


@pytest.mark.parametrize("insee,commune,attendu", [
    ("97413", "Saint-Leu", "2026-11-18"),
    ("97409", "Saint-André", "2025-10-03"),
])
def test_revision_derniere_piece_identifiee(insee, commune, attendu):
    """La date de « dernière pièce » d'une révision générale porte une pièce officielle identifiée
    ultérieure, pas le squelette 31/12/2024 : Saint-Leu 18/11/2026, Saint-André 03/10/2025 (sans base)."""
    from labuse import veille_plu
    e = veille_plu.entry(insee) or {}
    assert e.get("etat_source_date") == attendu, \
        f"{commune} : dernière pièce attendue {attendu}, obtenu {e.get('etat_source_date')!r}"


def test_revision_trois_bassins_debat_padd():
    from labuse import veille_plu
    e = veille_plu.entry("97423")
    assert e["etat_source_date"] == e["debat_padd_tenu"] == "2025-09-04"


def test_plaine_lien_source_domaine_vivant():
    """Le lien de la citation de La Plaine-des-Palmistes ne pointe plus vers www.plaine-des-palmistes.re
    (domaine dont la résolution échoue). (sans base)"""
    from labuse import veille_plu
    url = (veille_plu.entry("97406") or {}).get("source_url") or ""
    assert "plaine-des-palmistes.re" not in url, \
        f"lien Plaine toujours sur le domaine mort : {url!r}"
