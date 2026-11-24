"""OUTIL-COMMUNES-FIX-6 — LOT 0 : le FILET. Un test par témoin du recontrôle
(`~/Desktop/audit-outils/03-COMMUNES-ASTRA-4.md`, liste « C'est faux »), valeur PRÉCISE. Écrits AVANT
correction : rouges maintenant, verts une fois les LOTS 1-3 livrés.

  · prix de section — l'effectif ET le seuil portent sur les ventes DANS les bornes [50 ; 20 000] €/m²
    (celles qui entrent dans la médiane), pas sur le total des actes :
      97411000IZ = 284 €/m² sur 14 ventes (et non 18 : 4 actes hors bornes 5,08/7,62/7,62/36 000) ;
      97415000CD = 1 seule vente dans les bornes → sous le seuil → AUCUN prix de section servi (et
      non 133 €/m² sur 13).
  · procédure — La Plaine-des-Palmistes datée de sa pièce la plus récente, le 27/11/2025 (et non le
    27/05/2023, l'opposable GPU antérieur).

(Le témoin CatNat « et N autres » — Saint-Paul 18, Saint-Denis 15 — est côté front : testé par
`frontend/src/lib/catnat.test.ts`.)

Tests `db` : skip sur base sans cache secteur. Lisent le cache SERVI (`dvf_secteur_medianes`)."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


def _section_terrain(c, secteur):
    """n_ventes et médiane €/m² TERRAIN du cache de section SERVI (ce que lit Comparer / fiche §8)."""
    return c.execute(text(
        "SELECT n_ventes, mediane_prix_m2 FROM dvf_secteur_medianes "
        "WHERE secteur = :s AND type_bien = 'terrain'"), {"s": secteur}).mappings().first()


@pytest.mark.db
def test_section_iz_effectif_14_pas_18():
    """Section IZ de Saint-Denis (parcelle 97411000IZ0001) : 18 actes de terrain nu, 4 hors bornes de
    prix → 14 entrent dans la médiane. L'effectif SERVI doit être 14 (la médiane reste 284 €/m²)."""
    from labuse.db import engine
    with engine().connect() as c:
        try:
            if not c.execute(text("SELECT 1 FROM dvf_secteur_medianes LIMIT 1")).scalar():
                pytest.skip("cache dvf_secteur_medianes vide")
        except Exception:  # noqa: BLE001
            pytest.skip("cache dvf_secteur_medianes absent")
        r = _section_terrain(c, "97411000IZ")
        if not r:
            pytest.skip("section 97411000IZ absente du cache local")
        assert r["n_ventes"] == 14, f"effectif de section attendu 14 (ventes dans les bornes), obtenu {r['n_ventes']}"
        assert r["mediane_prix_m2"] == 284, f"médiane attendue 284 €/m², obtenue {r['mediane_prix_m2']}"


@pytest.mark.db
def test_section_cd_aucun_prix():
    """Section CD de Saint-Paul (parcelle 97415000CD0003) : 13 actes, UNE SEULE vente dans les bornes de
    prix. Sous le seuil de diffusion (SEUIL_N = 8), AUCUN prix de section n'est servi — pas 133 €/m²
    sur 13."""
    from labuse.db import engine
    from labuse.dvf_mediane import SEUIL_N
    with engine().connect() as c:
        try:
            if not c.execute(text("SELECT 1 FROM dvf_secteur_medianes LIMIT 1")).scalar():
                pytest.skip("cache dvf_secteur_medianes vide")
        except Exception:  # noqa: BLE001
            pytest.skip("cache dvf_secteur_medianes absent")
        r = _section_terrain(c, "97415000CD")
        if not r:
            pytest.skip("section 97415000CD absente du cache local")
        assert r["n_ventes"] == 1, f"effectif de section attendu 1 (vente dans les bornes), obtenu {r['n_ventes']}"
        # le prix par section n'est servi par Comparer que si n_ventes >= SEUIL_N
        assert r["n_ventes"] < SEUIL_N, \
            f"1 vente < seuil {SEUIL_N} → AUCUN prix de section servi (obtenu n={r['n_ventes']})"


def test_plaine_des_palmistes_revision_datee_27_11_2025():
    """La pièce municipale du 27/11/2025 confirme la révision EN COURS : c'est la date de preuve la plus
    récente, pas l'opposable GPU du 27/05/2023. Registre = etat_source_date 2025-11-27 (sans base)."""
    from labuse import veille_plu
    e = veille_plu.entry("97406") or {}
    assert e.get("procedure") == "revision_plu", f"Plaine-des-Palmistes toujours en révision, obtenu {e.get('procedure')!r}"
    assert e.get("etat_source_date") == "2025-11-27", \
        f"dernière pièce attendue le 2025-11-27, obtenu {e.get('etat_source_date')!r}"
