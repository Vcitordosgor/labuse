"""OUTIL-COMMUNES-FIX-1 bloquant 1 — le prix du terrain nu se qualifie SUR L'ACTE ENTIER.

Le défaut (relevé par le relecteur sur `main` 79153bb21) : le moteur filtrait les lignes NON bâties
AVANT de reconstituer la vente. Un acte « maison + jardin nu » (une parcelle bâtie, une parcelle nue)
survivait comme vente de terrain nu et recevait le prix de l'acte ENTIER rapporté à la seule surface
nue. Cas cité : la mutation 2021-1672641 à Saint-Denis vaut 225 000 € et comprend BZ0422 (terrain nu
de 2 320 m²) ET BZ1224 (maison de 87 m²). À Saint-Denis, 679 des 1 254 actes du calcul servi étaient
ainsi mixtes ; les retirer fait passer la médiane zone U de 482 à ~288 €/m².

Correctif : on ne qualifie un acte de « terrain nu » que si son bâti TOTAL (sur TOUTES ses parcelles)
est nul (`sum(surface_reelle_bati) = 0`), et la surface terrain est reconstituée sur l'acte entier.

Deux tests (marqueur `db`, base réelle, en transaction ANNULÉE — aucune écriture persistée) :
  1. le cas réel 2021-1672641 est bien un acte mixte et le filtre acte-entier l'écarte ;
  2. injecter un acte mixte (un bâti ajouté sur une autre parcelle de l'acte) ne gonfle PAS le compte
     ni la médiane du terrain nu servi — avant correctif, il le gonflait.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.db

_MUT_MIXTE = "2021-1672641"      # Saint-Denis : terrain nu BZ0422 + maison BZ1224 (relecteur)

# Les deux règles de qualification, pour montrer que la nouvelle écarte ce que l'ancienne gardait.
_RULE_PAR_PARCELLE = "COALESCE(dm.surface_reelle_bati,0) = 0 AND dm.surface_terrain > 0"  # ANCIENNE (défaut)


def _has(conn) -> bool:
    try:
        return bool(conn.execute(text("SELECT 1 FROM dvf_mutations_parcelle LIMIT 1")).scalar())
    except Exception:
        return False


def test_mutation_mixte_reelle_ecartee_par_acte_entier():
    """Le cas cité par le relecteur : 2021-1672641 est un acte mixte (bâti présent), gardé par la règle
    PAR PARCELLE mais écarté par la règle ACTE ENTIER (`sum(bati) = 0`)."""
    from labuse.db import engine
    with engine().connect() as conn:
        if not _has(conn):
            pytest.skip("base sans dvf_mutations_parcelle")
        row = conn.execute(text(
            "SELECT sum(COALESCE(surface_reelle_bati,0)) AS bati_tot, count(*) AS n_lignes "
            "FROM dvf_mutations_parcelle WHERE id_mutation = :m"), {"m": _MUT_MIXTE}).mappings().first()
        if not row or not row["n_lignes"]:
            pytest.skip(f"mutation {_MUT_MIXTE} absente de la base locale")
        # L'acte PORTE du bâti : ce n'est pas une vente de terrain nu.
        assert row["bati_tot"] and row["bati_tot"] > 0, (
            f"{_MUT_MIXTE} devrait porter du bâti (maison BZ1224) ; bati_tot={row['bati_tot']}")

        # L'ANCIENNE règle (par parcelle) retient au moins une ligne nue de cet acte …
        garde_ancien = conn.execute(text(
            f"SELECT count(*) FROM dvf_mutations_parcelle dm WHERE dm.id_mutation = :m AND {_RULE_PAR_PARCELLE}"),
            {"m": _MUT_MIXTE}).scalar()
        assert garde_ancien and garde_ancien >= 1, "l'ancienne règle gardait bien une ligne nue de l'acte"

        # … la NOUVELLE règle (acte entier) l'écarte : son bâti total n'est pas nul.
        garde_acte_entier = conn.execute(text(
            "SELECT count(*) FROM (SELECT id_mutation FROM dvf_mutations_parcelle "
            "WHERE id_mutation = :m GROUP BY id_mutation "
            "HAVING sum(COALESCE(surface_reelle_bati,0)) = 0) q"), {"m": _MUT_MIXTE}).scalar()
        assert garde_acte_entier == 0, f"{_MUT_MIXTE} doit être écarté du terrain nu (acte mixte)"


def _une_commune_avec_terrain_nu(sess: Session) -> str | None:
    return sess.execute(text(
        "SELECT p.commune FROM dvf_mutations_parcelle dm JOIN parcels p ON p.idu = dm.id_parcelle "
        "WHERE COALESCE(dm.surface_reelle_bati,0)=0 AND dm.surface_terrain > 0 "
        "  AND dm.nature_mutation IN ('Vente','Vente terrain à bâtir') "
        "GROUP BY p.commune HAVING count(*) > 20 LIMIT 1")).scalar()


def test_acte_mixte_injecte_ne_gonfle_pas_le_terrain_nu():
    """Injecter un acte MIXTE (une parcelle nue + une parcelle bâtie, même mutation, prix dans la bande)
    ne doit changer NI la médiane NI le compte du terrain nu servi (`mediane_commune`) : l'acte-entier
    l'écarte. Avant correctif, le compte montait de 1 et la médiane bougeait."""
    from labuse.db import engine
    from labuse.marche_dvf_commune import mediane_commune
    with engine().connect() as conn:
        if not _has(conn):
            pytest.skip("base sans dvf_mutations_parcelle")
        trans = conn.begin()
        sess = Session(bind=conn)
        try:
            commune = _une_commune_avec_terrain_nu(sess)
            if not commune:
                pytest.skip("aucune commune avec ventes terrain nu")
            # deux parcelles existantes DISTINCTES de la commune (pour que l'INSERT respecte la FK idu)
            parcs = [r[0] for r in sess.execute(text(
                "SELECT idu FROM parcels WHERE commune = :c LIMIT 2"), {"c": commune}).all()]
            if len(parcs) < 2:
                pytest.skip("commune avec moins de 2 parcelles")
            p_nu, p_bati = parcs[0], parcs[1]

            avant = mediane_commune(sess, commune, "terrain")
            # acte mixte synthétique : nu 6 000 m² (€/m² = 200, dans la bande [50,4000]) + bâti 120 m²
            cols = ("id_mutation, date_mutation, nature_mutation, valeur_fonciere, code_commune, "
                    "id_parcelle, type_local, surface_reelle_bati, surface_terrain, millesime")
            mut = "TEST-ACTE-MIXTE-0001"
            d = sess.execute(text(
                "SELECT max(date_mutation) FROM dvf_mutations_parcelle WHERE id_parcelle = :p"),
                {"p": p_nu}).scalar()
            insee = p_nu[:5]
            for parc, bati, terr, tl in ((p_nu, 0, 6000, None), (p_bati, 120, 0, "Maison")):
                sess.execute(text(
                    f"INSERT INTO dvf_mutations_parcelle ({cols}) VALUES "
                    "(:m, :d, 'Vente', 1200000, :insee, :p, :tl, :bati, :terr, '2025')"),
                    {"m": mut, "d": d, "insee": insee, "p": parc, "tl": tl, "bati": bati, "terr": terr})

            apres = mediane_commune(sess, commune, "terrain")
            assert avant["n"] == apres["n"], (
                f"un acte MIXTE a gonflé le compte terrain nu de {commune} : "
                f"{avant['n']} → {apres['n']} (l'acte-entier doit l'écarter)")
            assert avant["eur_m2"] == apres["eur_m2"], (
                f"un acte MIXTE a bougé la médiane terrain nu de {commune} : "
                f"{avant['eur_m2']} → {apres['eur_m2']}")
        finally:
            trans.rollback()
            sess.close()
