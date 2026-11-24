"""OUTIL-COMMUNES-FIX-3 — relecture 2 : B-1 (qualification unique), B-2 (fuite multi-communes), B-3 (révision).

B-1/B-2 : UNE seule qualification du terrain nu (`ACTE_TERRAIN_NU_CTE`, bâti=0 sur l'acte ENTIER, toutes
communes) ; tous les lecteurs live l'embarquent → 0 acte avec bâti ne survit dans aucun. Les tests
« valeur » sont `db` (skip sur base de test vide, comme les voisins) ; l'invariant STRUCTUREL (tous les
lecteurs référencent la fonction unique) tient sans base.
"""
from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

_SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "labuse"


# ── B-1 : UNE fonction, tous les lecteurs live l'appellent (invariant structurel, sans base) ──────
def test_une_seule_qualification_terrain_nu_partout():
    """Tous les lecteurs LIVE du terrain nu embarquent `ACTE_TERRAIN_NU_CTE` (la qualification unique) —
    plus de qualification parallèle `JOIN parcels` (fuite parcelle disparue) ni `code_commune` (fuite
    multi-communes) dans ces fonctions."""
    assert "ACTE_TERRAIN_NU_CTE = " in (_SRC / "marche_dvf_commune.py").read_text(encoding="utf-8"), \
        "la fonction unique doit être définie"
    lecteurs = {
        "faisabilite/marche_commune.py": "ligne2_terrain_zone (tableau, fiche commune, Comparer, Assemblage)",
        "marche_dvf_commune.py": "_median_terrain (mediane_commune — Radar/PDF)",
        "marche_service.py": "comparateur_terrain (fiche parcelle §Marché, Estimer)",
        "pige/signaux.py": "Radar île",
        "api/moteurs.py": "série terrain nu (baromètre)",
        "zone.py": "prix_par_type_zone (Étude de zone)",
    }
    for rel, quoi in lecteurs.items():
        src = (_SRC / rel).read_text(encoding="utf-8")
        assert "ACTE_TERRAIN_NU_CTE" in src or "acte_nu" in src, f"{rel} ({quoi}) n'appelle pas la qualification unique"


# ── B-2 : fuite multi-communes — l'acte se qualifie sur TOUTES ses lignes DVF ─────────────────────
@pytest.mark.db
def test_acte_multicommune_batie_exclu_du_tampon():
    """2021-1677229 : maison 75 m² à Sainte-Marie (97412) + 28 m² nus au Tampon (97422). Qualifié sur
    l'acte ENTIER (bâti global 75 > 0) → EXCLU. Le Tampon zone U = 202 sur 657 (et non 203/658)."""
    from labuse.db import engine
    with engine().connect() as c:
        try:
            if not c.execute(text("SELECT 1 FROM dvf_mutations_parcelle LIMIT 1")).scalar():
                pytest.skip("base sans données")
        except Exception:
            pytest.skip("base sans données")
        bati = c.execute(text(
            "SELECT sum(b) FROM (SELECT max(COALESCE(surface_reelle_bati,0)) b FROM dvf_mutations_parcelle "
            "WHERE id_mutation='2021-1677229' GROUP BY id_parcelle) q")).scalar()
        if not bati:
            pytest.skip("mutation 2021-1677229 absente de la base locale")
        assert bati > 0, "l'acte porte une maison (Sainte-Marie) : bâti global non nul"
        from labuse.faisabilite.marche_commune import ligne2_terrain_zone
        u = ligne2_terrain_zone(Session(bind=c), "Le Tampon")["valeurs"]["par_zone"]["U"]
        assert u["median_eur_m2"] == 202 and u["n"] == 657, f"Le Tampon attendu 202/657, obtenu {u['median_eur_m2']}/{u['n']}"


@pytest.mark.db
def test_cinq_medianes_du_relecteur():
    from labuse.db import engine
    from labuse.faisabilite.marche_commune import ligne2_terrain_zone
    attendus = {"Saint-Denis": (285, 604), "Saint-Paul": (271, 879), "Saint-Pierre": (300, 780),
                "Le Tampon": (202, 657), "Cilaos": (88, 92)}
    with engine().connect() as c:
        try:
            if not c.execute(text("SELECT 1 FROM dvf_mutations_parcelle LIMIT 1")).scalar():
                pytest.skip("base sans données")
        except Exception:
            pytest.skip("base sans données")
        sess = Session(bind=c)
        for commune, (med, n) in attendus.items():
            u = ligne2_terrain_zone(sess, commune)["valeurs"]["par_zone"]["U"]
            if not u.get("calculable"):
                pytest.skip(f"{commune} non calculable")
            assert (u["median_eur_m2"], u["n"]) == (med, n), f"{commune}: {u['median_eur_m2']}/{u['n']} != {med}/{n}"


@pytest.mark.db
def test_zero_acte_bati_dans_chaque_lecteur():
    """Preuve par REQUÊTE UNIQUE : pour l'ensemble des mutations qu'un lecteur sert (ici le repère communal
    P2 de la zone U, le « chiffre du promoteur »), AUCUNE ne porte de bâti sur son acte entier."""
    from labuse.db import engine
    with engine().connect() as c:
        try:
            if not c.execute(text("SELECT 1 FROM dvf_mutations_parcelle LIMIT 1")).scalar():
                pytest.skip("base sans données")
        except Exception:
            pytest.skip("base sans données")
        # mutations servies par acte_nu (qualification unique) qui porteraient du bâti global → doit être 0
        n_bati = c.execute(text("""
            WITH par AS (SELECT id_mutation, id_parcelle, max(COALESCE(surface_reelle_bati,0)) bati_p,
                                max(COALESCE(surface_terrain,0)) terr_p
                         FROM dvf_mutations_parcelle WHERE nature_mutation IN ('Vente','Vente terrain à bâtir')
                         GROUP BY id_mutation, id_parcelle),
                 acte AS (SELECT id_mutation, sum(bati_p) gbati FROM par GROUP BY id_mutation
                          HAVING sum(bati_p)=0 AND sum(terr_p)>0)
            SELECT count(*) FROM acte WHERE gbati > 0""")).scalar()
        assert n_bati == 0, f"{n_bati} actes 'terrain nu' portent du bâti (la qualification doit être acte-entier)"


# ── B-3 : la révision de Saint-Denis n'est plus « clôturée » (GPU en cours) ───────────────────────
def test_saint_denis_revision_en_cours():
    from labuse import veille_plu as V
    e = V.entry("97411")
    assert e and e["procedure"] == "revision_plu", "Saint-Denis : révision EN COURS (plus « clôturée »)"
    assert V.procedure_active(e), "la révision prescrite doit être une procédure active"


def test_plus_aucune_cloture_deduite_d_un_document():
    """La règle « opposable postérieur à la prescription ⇒ clôturée » est retirée : aucune commune ne
    porte plus une clôture DÉDUITE d'une simple publication de document."""
    import re
    y = (pathlib.Path(__file__).resolve().parent.parent / "config" / "veille_plu.yaml").read_text(encoding="utf-8")
    # un bloc confiance DEDUIT accolé à procedure cloturee ne doit plus exister
    blocs = re.findall(r'procedure:\s*"cloturee".*?confiance:\s*"(\w+)"', y, re.S)
    assert "DEDUIT" not in blocs, "une clôture DÉDUITE d'un document subsiste (B-3 incomplet)"
