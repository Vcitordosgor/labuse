"""OUTIL-COMMUNES-FIX-4 — LOT 0 : le FILET. Un test par témoin du recontrôle externe
(`~/Desktop/audit-outils/03-COMMUNES-ASTRA-3.md`, liste « C'est faux »), chacun avec la valeur
PRÉCISE attendue. Écrits AVANT toute correction : ils doivent ÉCHOUER sur `main` au commit contrôlé
(add341ebb) et passer au VERT une fois les LOTS 1-4 livrés.

Périmètre = exactement les témoins nommés par le rapport :
  · terrain nu   — 2023-1315722 (local déclaré) exclu + absent des comparables de IZ0236 ;
                   2022-1639451 (multi-communes) exclu de Petite-Île ET Saint-Joseph ;
                   2021-1676912 = 1 895 m², 280 €/m² (surface = somme des subdivisions).
  · faux zéro    — Saint-Denis 14 arrêtés CatNat, Saint-Paul 17, La Plaine-des-Palmistes 9,
                   SERVIS même quand le calcul d'exposition (PPR/mvt) échoue (jamais 0 menteur).
  · baromètre    — Cilaos répond (plus de pendaison 200 s → HTTP 500 sous statement_timeout).
  · procédures   — Sainte-Marie et Sainte-Suzanne APPROUVÉES (plus « en révision »).

Tests `db` : ils se sautent (skip) sur une base de test vide, comme leurs voisins.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


def _skip_si_pas_de_dvf(c):
    try:
        if not c.execute(text("SELECT 1 FROM dvf_mutations_parcelle LIMIT 1")).scalar():
            pytest.skip("base sans données DVF")
    except Exception:  # noqa: BLE001
        pytest.skip("base sans données DVF")


def _acte_nu(c, mid):
    """La ligne de l'acte `mid` dans la qualification UNIQUE du terrain nu (`ACTE_TERRAIN_NU_CTE`),
    ou None si l'acte n'y entre pas. `terr_tot`/`val` = surface terrain reconstituée et valeur."""
    from labuse.marche_dvf_commune import ACTE_TERRAIN_NU_CTE
    return c.execute(text("WITH " + ACTE_TERRAIN_NU_CTE +
                          " SELECT terr_tot, val FROM acte_nu WHERE id_mutation = :m"),
                     {"m": mid}).mappings().first()


# ────────────────────────────── terrain nu (rapport §1) ──────────────────────────────
@pytest.mark.db
def test_2023_1315722_local_declare_exclu_du_terrain_nu():
    """IZ0236 porte un « Local industriel. commercial ou assimilé » SANS surface bâtie renseignée.
    Un acte qui DÉCLARE un local n'est pas une vente de terrain nu, même sans surface → EXCLU."""
    from labuse.db import engine
    with engine().connect() as c:
        _skip_si_pas_de_dvf(c)
        if _acte_nu(c, "2023-1315722") is None and not c.execute(text(
                "SELECT 1 FROM dvf_mutations_parcelle WHERE id_mutation='2023-1315722' LIMIT 1")).scalar():
            pytest.skip("acte 2023-1315722 absent de la base locale")
        assert _acte_nu(c, "2023-1315722") is None, \
            "2023-1315722 déclare un local → ne doit PAS être qualifié terrain nu"


@pytest.mark.db
def test_2023_1315722_absent_de_ses_propres_comparables_IZ0236():
    """Le moteur de comparables du terrain (fiche parcelle §Marché + Estimer) rendait l'acte du bien
    ÉTUDIÉ comme son premier comparable « Terrain » (80 m², 250 €/m², distance 0 m), via la 2ᵉ
    parcelle de la mutation. L'acte du sujet ne doit JAMAIS figurer dans ses propres comparables."""
    from labuse.db import engine
    from labuse.marche_service import comparateur_terrain
    with engine().connect() as c:
        _skip_si_pas_de_dvf(c)
        if not c.execute(text("SELECT 1 FROM parcels WHERE idu='97411000IZ0236'")).scalar():
            pytest.skip("parcelle 97411000IZ0236 absente de la base locale")
        res = comparateur_terrain(Session(bind=c), "97411000IZ0236")
        cmps = res.get("comparables") or []
        temoin = [x for x in cmps if x.get("surface_m2") == 80 and x.get("prix_m2") == 250]
        assert not temoin, f"l'acte du sujet (80 m², 250 €/m²) reparaît dans ses comparables : {temoin}"


@pytest.mark.db
def test_2022_1639451_multicommune_exclu_de_petite_ile_et_saint_joseph():
    """60 000 €, 465 m² à Petite-Île (AH0758) + 485 m² à Saint-Joseph (AO0895) : un acte sur DEUX
    communes. Il entrait dans les deux populations U (63,16 €/m²). Un acte multi-communes est écarté
    PARTOUT → absent de la qualification unique."""
    from labuse.db import engine
    with engine().connect() as c:
        _skip_si_pas_de_dvf(c)
        communes = c.execute(text(
            "SELECT count(DISTINCT code_commune) FROM dvf_mutations_parcelle WHERE id_mutation='2022-1639451'"
        )).scalar()
        if not communes:
            pytest.skip("acte 2022-1639451 absent de la base locale")
        assert communes == 2, "le témoin doit bien porter sur deux communes"
        assert _acte_nu(c, "2022-1639451") is None, \
            "2022-1639451 est multi-communes → écarté partout (Petite-Île ET Saint-Joseph)"


@pytest.mark.db
def test_2021_1676912_surface_somme_des_subdivisions_1895m2_280eurm2():
    """ET0142 est ventilée par DVF en 1 195 m² de « sols » + 700 m² de « terres » : deux subdivisions
    DISTINCTES. La contenance cadastrale confirme 1 895 m². Le prix du terrain nu divise la valeur
    (530 000 €) par la SOMME des subdivisions (1 895 m² → 280 €/m²), jamais par la plus grande ligne
    (1 195 m² → 444 €/m²)."""
    from labuse.db import engine
    with engine().connect() as c:
        _skip_si_pas_de_dvf(c)
        row = _acte_nu(c, "2021-1676912")
        if row is None and not c.execute(text(
                "SELECT 1 FROM dvf_mutations_parcelle WHERE id_mutation='2021-1676912' LIMIT 1")).scalar():
            pytest.skip("acte 2021-1676912 absent de la base locale")
        assert row is not None, "2021-1676912 est une vente de terrain nu (aucun bâti, aucun local)"
        assert round(row["terr_tot"]) == 1895, f"surface attendue 1 895 m², obtenue {row['terr_tot']}"
        assert round(row["val"] / row["terr_tot"]) == 280, \
            f"prix attendu 280 €/m², obtenu {round(row['val'] / row['terr_tot'])}"


# ────────────────────────────── faux zéro CatNat (rapport §5) ──────────────────────────────
@pytest.mark.db
@pytest.mark.parametrize("commune,insee,attendu", [
    ("Saint-Denis", "97411", 14), ("Saint-Paul", "97415", 17), ("La Plaine-des-Palmistes", "97406", 9)])
def test_catnat_jamais_faux_zero_quand_exposition_echoue(monkeypatch, commune, insee, attendu):
    """Le nombre d'arrêtés CatNat est FACTUEL (table source) et INDÉPENDANT du calcul d'exposition
    PPR/mouvement de terrain. Quand ce dernier échoue (sur ces trois communes, le scan spatial dépasse
    le statement_timeout de l'API), la fiche doit TOUJOURS servir le vrai compte d'arrêtés — jamais le
    repli 0 menteur. Témoin : Saint-Denis 14, Saint-Paul 17, La Plaine-des-Palmistes 9."""
    from labuse.db import engine
    import labuse.registre.moteurs.commune as cm

    def _timeout(*a, **k):
        raise RuntimeError("statement_timeout simulé (scan PPR/mvt)")
    monkeypatch.setattr(cm, "pct_parcelles_couche", _timeout)
    from labuse.api.fiche_commune import risques
    with engine().connect() as c:
        try:
            src = c.execute(text("SELECT count(DISTINCT date_arrete) FROM catnat_arretes WHERE insee=:i"),
                            {"i": insee}).scalar()
        except Exception:  # noqa: BLE001
            pytest.skip("table catnat_arretes absente")
        if not src:
            pytest.skip(f"aucun arrêté CatNat en base pour {insee}")
        assert src == attendu, f"la table source doit porter {attendu} arrêtés distincts ({commune})"
        r = risques(Session(bind=c), commune, insee)
        assert r["catnat_arretes"] == attendu, \
            f"{commune} : {attendu} arrêtés servis même si l'exposition échoue (obtenu {r['catnat_arretes']})"
        assert r["ppr_pct"] is None, "l'exposition indisponible est servie None (indisponible), pas 0"


def test_fallback_risques_catnat_indisponible_pas_zero():
    """Le repli du bloc risques ne doit pas présenter l'indisponibilité comme une absence d'arrêté :
    catnat_arretes = None (indisponible), jamais 0 (sans base)."""
    from labuse.api.fiche_commune import _FALLBACK
    assert _FALLBACK["risques"]["catnat_arretes"] is None, \
        "un bloc risques en échec doit afficher « indisponible » (None), jamais 0 arrêté"


# ────────────────────────────── baromètre Cilaos (rapport §6) ──────────────────────────────
@pytest.mark.db
def test_barometre_cilaos_repond_sous_statement_timeout():
    """GET /moteurs/barometre?insee=97424 pendait ~200 s (plan nested-loop re-scannant la table) → HTTP
    500 sous le statement_timeout de l'API. Le parcours communal de Cilaos doit répondre bien en deçà."""
    from labuse.db import engine
    from labuse.api.moteurs import _barometre_data
    with engine().connect() as c:
        _skip_si_pas_de_dvf(c)
        c.execute(text("SET LOCAL statement_timeout = '25s'"))
        r = _barometre_data(Session(bind=c), insee="97424")
        assert r["insee"] == "97424" and r["commune"] == "Cilaos"
        # chiffres du trimestre = base : les permis servis correspondent au comptage Sitadel direct.
        base = {x[0]: x[1] for x in c.execute(text(
            "SELECT to_char(date_trunc('quarter', date), 'YYYY\"T\"Q') AS t, count(*) "
            "FROM sitadel_permits WHERE commune='Cilaos' "
            "  AND date_trunc('quarter', date) < date_trunc('quarter', CURRENT_DATE) "
            "GROUP BY 1")).all()}
        for row in r["permis_trimestres"]:
            if row["trimestre"] in base:
                assert row["permis"] == base[row["trimestre"]], \
                    f"permis {row['trimestre']} servi {row['permis']} ≠ base {base[row['trimestre']]}"


# ────────────────────────────── procédures PLU (rapport §4) ──────────────────────────────
def test_sainte_marie_plu_approuve():
    """La mairie a approuvé le PLU révisé le 26/11/2025 (exécutoire le 14/01/2026) : la fiche ne doit
    plus renvoyer « en révision ». Registre = procédure clôturée (approbation), date 2025-11-26."""
    from labuse import veille_plu
    e = veille_plu.entry("97418") or {}
    assert e.get("procedure") == "cloturee", f"Sainte-Marie : révision approuvée, obtenu {e.get('procedure')!r}"
    assert e.get("date_acte") == "2025-11-26", f"approbation attendue le 2025-11-26, obtenu {e.get('date_acte')!r}"


def test_sainte_suzanne_plu_approuve():
    """La pièce officielle du PLU porte la prescription (28/02/2018) ET l'approbation (29/09/2025) de la
    MÊME procédure : la fiche ne doit plus renvoyer « en révision ». Registre = clôturée, 2025-09-29."""
    from labuse import veille_plu
    e = veille_plu.entry("97420") or {}
    assert e.get("procedure") == "cloturee", f"Sainte-Suzanne : révision approuvée, obtenu {e.get('procedure')!r}"
    assert e.get("date_acte") == "2025-09-29", f"approbation attendue le 2025-09-29, obtenu {e.get('date_acte')!r}"


# ────────────────────── FIX-5 (2) — libellé des communes sans procédure ──────────────────────
def test_plu_aucune_procedure_pas_a_jour_structurel():
    """FIX-5 : une commune « sans procédure » ne doit plus être mappée sur « à jour » (le squelette
    Sudocuh 31/12/2024 ne prouve pas l'absence de procédure LANCÉE depuis). `_fr_date_iso` formate la
    date de source. Invariant pur (sans base)."""
    from labuse.api.fiche_commune import _PLU_STATUT, _fr_date_iso
    assert _PLU_STATUT.get("aucune") != "à jour", "« aucune » ne doit plus donner « à jour »"
    assert _fr_date_iso("2024-12-31") == "31/12/2024"


@pytest.mark.db
def test_plu_13_sans_procedure_libelle_date():
    """Les 13 communes « sans procédure » servent « aucune procédure connue au 31/12/2024 » (date de la
    source Sudocuh), JAMAIS « à jour ». Aucune commune sur source > 12 mois ne dit « à jour » (seules
    les clôturées — PLU approuvé daté — gardent « à jour »)."""
    from labuse.db import engine
    from labuse.api.fiche_commune import plu_statut
    from labuse import veille_plu
    sans_proc = [i for i, e in (veille_plu._registre() or {}).items() if e.get("procedure") == "aucune"]
    assert len(sans_proc) == 13, f"attendu 13 communes sans procédure, obtenu {len(sans_proc)}"
    with engine().connect() as c:
        try:
            c.execute(text("SELECT 1 FROM sudocuh_procedures LIMIT 1"))
        except Exception:  # noqa: BLE001
            pytest.skip("table sudocuh_procedures absente")
        s = Session(bind=c)
        for insee in sans_proc:
            nom = (veille_plu.entry(insee) or {}).get("commune")
            st = plu_statut(s, insee, nom)["statut"]
            assert st == "aucune procédure connue au 31/12/2024", f"{insee} ({nom}) : « {st} »"
            assert st != "à jour"
