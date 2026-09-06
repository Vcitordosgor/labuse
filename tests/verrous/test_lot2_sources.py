"""CIRCUIT-5 lot 2 — le verrou des sources : le même compte partout (68 à CIRCUIT-5, 72
depuis CIRCUIT-5b lot 1 — les quatre « à rattacher » entrées au catalogue).

Chaque garde est prouvée CASSÉE sur un cas construit (doublon caché, alias sans cible,
retirée sans raison, source sans cadence au seed) puis VERTE sur le catalogue réel.
"""
from __future__ import annotations

import pytest

from labuse import circuit_verrous as CV
from labuse.ingestion import seed_sources

pytestmark = pytest.mark.verrous


def _ligne(**kw) -> dict:
    base = dict(id=1, name="Source témoin", status="connecte", technical_notes="✓ live",
                affichage_desactive=False, alias_de=None, retiree_le=None, retiree_raison=None)
    base.update(kw)
    return base


# ── V2b — discipline des statuts (analyse pure) ─────────────────────────────────────────

def test_v2b_prouve_le_doublon_cache():
    """Une ligne au statut de vitrine mais chassée par sa note DOUBLON (l'état d'avant le
    lot 2) casse le verrou — le doublon doit devenir un alias de première classe."""
    rows = [_ligne(id=1), _ligne(id=2, name="Canal doublon",
                                 technical_notes="DOUBLON de « Source témoin » (M71)")]
    pbs = CV.analyse_catalogue(rows)
    assert any("doublon caché" in p for p in pbs)


def test_v2b_prouve_alias_sans_cible_et_alias_vers_hors_vitrine():
    rows = [_ligne(id=2, name="Alias perdu", status="alias", alias_de=None)]
    assert any("alias sans cible" in p for p in CV.analyse_catalogue(rows))
    rows = [_ligne(id=1, status="retiree", retiree_le="2026-09-06", retiree_raison="morte"),
            _ligne(id=2, name="Alias d'une morte", status="alias", alias_de=1)]
    assert any("HORS vitrine" in p for p in CV.analyse_catalogue(rows))


def test_v2b_prouve_retiree_sans_raison_et_a_faire_sans_chantier():
    rows = [_ligne(status="retiree", retiree_le=None, retiree_raison=None)]
    assert any("sans date ou sans raison" in p for p in CV.analyse_catalogue(rows))
    rows = [_ligne(status="a_faire", technical_notes="  ")]
    assert any("sans chantier nommé" in p for p in CV.analyse_catalogue(rows))


def test_v2b_vert_sur_un_catalogue_discipline():
    rows = [
        _ligne(id=1),
        _ligne(id=2, name="Canal bulk", status="alias", alias_de=1),
        _ligne(id=3, name="Hub", status="hub"),
        _ligne(id=4, name="Morte", status="retiree", retiree_le="2026-09-06",
               retiree_raison="amont 410 Gone"),
        _ligne(id=5, name="Chantier", status="a_faire", technical_notes="CIRCUIT-9 : à venir"),
        _ligne(id=6, name="Masquée d'un geste", affichage_desactive=True),
    ]
    assert CV.analyse_catalogue(rows) == []


def test_v2b_une_servie_ne_peut_pas_etre_un_alias():
    rows = [_ligne(id=1), _ligne(id=2, name="Servie et alias", alias_de=1)]
    assert any("contradiction" in p for p in CV.analyse_catalogue(rows))


# ── V2a — le même compte partout (72 depuis CIRCUIT-5b lot 1) ───────────────────────────

@pytest.mark.local
def test_v2a_68_partout_sur_la_base_reelle(monkeypatch):
    """Sur la base réelle : vitrine SQL = prédicat Python = page, et chaque source servie a
    son slug dans le pont et dans la carte. PREUVE CASSÉ : une page qui servirait un compte
    différent (flux monkeypatché) fait diverger les nombres → casse."""
    import os

    from sqlalchemy.orm import sessionmaker

    from labuse import db as db_mod, flux
    real = db_mod.make_engine(os.environ["LABUSE_APP_DATABASE_URL"])
    with sessionmaker(bind=real)() as s:
        r = CV.verrou_sources_comptes(s)
        assert r.verdict == "ok", (r.preuve, r.details[:5])

        vrai = flux.construire_flux
        monkeypatch.setattr(flux, "construire_flux",
                            lambda db: {**vrai(db), "sources": []})
        r2 = CV.verrou_sources_comptes(s)
        assert r2.verdict == "casse"
        assert "divergents" in r2.preuve


@pytest.mark.local
def test_v2b_vert_sur_la_base_reelle():
    import os

    from sqlalchemy.orm import sessionmaker

    from labuse import db as db_mod
    real = db_mod.make_engine(os.environ["LABUSE_APP_DATABASE_URL"])
    with sessionmaker(bind=real)() as s:
        r = CV.verrou_sources_statuts(s)
        assert r.verdict == "ok", r.details[:8]


# ── 2.3 — le seed refuse une source incomplète ──────────────────────────────────────────

def test_seed_refuse_une_source_sans_producteur_ni_cadence():
    """PREUVE CASSÉ : une ligne sans producteur, sans cadence (hors MODE_ET_CADENCE) et sans
    sonde est refusée — trois problèmes nommés."""
    pbs = seed_sources.verifier_catalogue([dict(name="Essai fantôme", provider=None,
                                                access_type=None)])
    assert any("sans producteur" in p for p in pbs)
    assert any("sans mode de remplissage" in p for p in pbs)
    assert any("sans sonde" in p for p in pbs)


def test_seed_refuse_vraiment(db_session, monkeypatch):
    """`seed()` lève AVANT toute écriture si le catalogue est incomplet."""
    monkeypatch.setattr(seed_sources, "SOURCES",
                        seed_sources.SOURCES + [dict(name="Essai fantôme", provider=None)])
    with pytest.raises(ValueError, match="seed refusé"):
        seed_sources.seed(db_session)


def test_catalogue_reel_passe_la_garde():
    """VERT : les 71 lignes du seed ont id, producteur, mode d'accès, mode+cadence, et une
    sonde ou sa raison d'absence. (La garde a mordu à sa pose : CatNat, Taxe d'aménagement
    et Cadastre d'époque n'avaient ni mode ni cadence — déclarés depuis.)"""
    assert seed_sources.verifier_catalogue() == []


def test_pont_et_carte_couvrent_le_seed():
    """Chaque source du seed destinée à la vitrine (statut connecte/manuel) a son slug dans
    le pont NOM_VERS_SLUG et dans la carte — une source ne peut pas entrer sans sa place."""
    from labuse.circuit_etats import NOM_VERS_SLUG
    from labuse.registre import tables as T
    from labuse.sources_catalog import est_affichee
    manquants = []
    for row in seed_sources.SOURCES:
        if not est_affichee(row["name"], row.get("technical_notes"),
                            str(row.get("status") or ""), False):
            continue
        slug = NOM_VERS_SLUG.get(row["name"])
        if not slug or slug not in T.RESERVOIR_TABLES:
            manquants.append(row["name"])
    assert manquants == [], manquants
