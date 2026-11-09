"""COMMUNE-FIX-2 — NON-RÉGRESSION : les 24 fiches commune contre leurs sources.

Le mandat « fiche commune propre et juste » demande « 0 chiffre faux » : ce test VERROUILLE, pour les
24 communes, que le payload SERVI par l'endpoint `/communes/{c}/contexte` (le même objet que l'écran lit,
`_rafraichir_partages` compris) EST ÉGAL à ce que disent les TABLES SOURCES — INSEE (population_legale,
commune_insee_logement), Sitadel (sitadel_permits), DVF (dvf_mutations), SRU (commune_contexte_sru), GPU
(cohérence du zonage) — plus les deux faits ajoutés au bandeau (surface cadastrale, sigle EPCI).

Marqué `reel` : il lit la base APPLICATIVE complète (vraies données), donc il tourne au BANC DE NUIT, pas
dans le pre-push (famille unitaire sans base). C'est le filet dur qui refuse qu'un futur changement fasse
diverger un chiffre de fiche de sa source.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.reel


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy.orm import sessionmaker
    from labuse.db import make_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    try:
        s.execute(text("SELECT 1 FROM population_legale LIMIT 1")).scalar()
    except Exception:
        s.close()
        pytest.skip("base applicative sans données de fiche commune")
    yield s
    s.close()


@pytest.fixture(scope="module")
def communes(session_reelle):
    rows = session_reelle.execute(text(
        "SELECT insee, commune FROM population_legale ORDER BY insee")).all()
    assert len(rows) >= 24, f"attendu ≥ 24 communes, vu {len(rows)}"
    return [(r[0], r[1]) for r in rows]


@pytest.fixture(scope="module")
def payloads(session_reelle, communes):
    """Le payload EXACTEMENT comme l'endpoint le sert (cache rafraîchi + partages live)."""
    from labuse.api.app import commune_contexte
    out = {}
    for insee, nom in communes:
        out[insee] = commune_contexte(nom, db=session_reelle)
    return out


def _near(a, b, tol=0.0):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a) == str(b)


def test_insee_population(session_reelle, communes, payloads):
    """habitants / millésime / logements / ménages / vacance == INSEE (population_legale + logement RP)."""
    ecarts = []
    for insee, nom in communes:
        d = payloads[insee]
        pop = d.get("population") or {}
        src = session_reelle.execute(text(
            "SELECT pop_mun, millesime FROM population_legale WHERE insee=:i"), {"i": insee}).first()
        if not _near(pop.get("habitants"), src[0]):
            ecarts.append((nom, "habitants", pop.get("habitants"), src[0]))
        if str(pop.get("habitants_millesime")) != str(src[1]):
            ecarts.append((nom, "millésime", pop.get("habitants_millesime"), src[1]))
        lg = session_reelle.execute(text(
            "SELECT logements, res_principales, vacants FROM commune_insee_logement WHERE insee=:i"),
            {"i": insee}).first()
        if lg:
            if not _near(pop.get("logements"), lg[0]):
                ecarts.append((nom, "logements", pop.get("logements"), lg[0]))
            if not _near(pop.get("menages"), lg[1]):
                ecarts.append((nom, "ménages", pop.get("menages"), lg[1]))
            vac = round(100.0 * lg[2] / lg[0], 1) if (lg[0] and lg[2] is not None) else None
            if not _near(pop.get("vacance_pct"), vac, 0.1):
                ecarts.append((nom, "vacance %", pop.get("vacance_pct"), vac))
    assert not ecarts, f"écarts INSEE : {ecarts}"


def test_sru(session_reelle, communes, payloads):
    """taux LLS / objectif / statut / nb LLS == inventaire SRU (commune_contexte_sru, DHUP)."""
    ecarts = []
    for insee, nom in communes:
        sru = payloads[insee].get("sru") or {}
        src = session_reelle.execute(text(
            "SELECT taux_lls, objectif_pct, statut, detail->>'nb_lls' FROM commune_contexte_sru WHERE insee=:i"),
            {"i": insee}).first()
        if not src:
            continue
        if not _near(sru.get("taux_lls"), src[0], 0.05):
            ecarts.append((nom, "taux_lls", sru.get("taux_lls"), src[0]))
        if not _near(sru.get("objectif_pct"), src[1], 0.05):
            ecarts.append((nom, "objectif", sru.get("objectif_pct"), src[1]))
        if str(sru.get("statut")) != str(src[2]):
            ecarts.append((nom, "statut", sru.get("statut"), src[2]))
        nb = (sru.get("detail") or {}).get("nb_lls")
        if not _near(nb, float(src[3]) if src[3] else None, 0.5):
            ecarts.append((nom, "nb_lls", nb, src[3]))
    assert not ecarts, f"écarts SRU : {ecarts}"


def test_sitadel_permis_12m(session_reelle, communes, payloads):
    """permis_12m == comptage Sitadel sur la fenêtre 12 mois ancrée au dernier dépôt connu."""
    ecarts = []
    for insee, nom in communes:
        pb = payloads[insee].get("permis_bloc") or {}
        n = session_reelle.execute(text(
            "SELECT count(*) FROM sitadel_permits WHERE commune=:c AND date > "
            "(SELECT max(date) FROM sitadel_permits) - interval '12 months'"), {"c": nom}).scalar()
        if not _near(pb.get("permis_12m"), n):
            ecarts.append((nom, pb.get("permis_12m"), n))
    assert not ecarts, f"écarts Sitadel permis_12m : {ecarts}"


def test_dvf_prix_et_mutations(session_reelle, communes, payloads):
    """prix ancien médian €/m² et mutations 12 mois == recalcul DVF (dvf_mutations, mêmes filtres)."""
    ecarts = []
    for insee, nom in communes:
        d = payloads[insee]
        cmp = d.get("comparable") or {}
        fon = d.get("foncier") or {}
        med = session_reelle.execute(text(
            "SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur_fonciere/NULLIF(surface_reelle_bati,0))), "
            "count(*) FROM dvf_mutations WHERE commune=:c AND nature_mutation='Vente' AND valeur_fonciere>1000 "
            "AND valeur_fonciere/NULLIF(surface_reelle_bati,0) BETWEEN 100 AND 12000"), {"c": nom}).first()
        med_src = med[0] if (med and (med[1] or 0) >= 100) else None
        if not _near(cmp.get("ancien_median_eur_m2"), med_src, 1.0):
            ecarts.append((nom, "ancien_median", cmp.get("ancien_median_eur_m2"), med_src))
        mut = session_reelle.execute(text(
            "SELECT count(*) FROM dvf_mutations WHERE commune=:c AND date_mutation > "
            "(SELECT max(date_mutation) FROM dvf_mutations WHERE commune=:c) - interval '12 months'"),
            {"c": nom}).scalar()
        if not _near(fon.get("mutations_12m"), mut):
            ecarts.append((nom, "mutations_12m", fon.get("mutations_12m"), mut))
    assert not ecarts, f"écarts DVF : {ecarts}"


def test_bandeau_surface_et_epci(session_reelle, communes, payloads):
    """COMMUNE-FIX-2 — les deux faits ajoutés au bandeau : surface cadastrale (≤ somme brute parcels,
    car servie sur le parc VIVANT) et sigle EPCI (== config autoritaire epci_974 / Banatic-INSEE)."""
    from labuse import config
    cfg = config.load_yaml_config("epci_974")["epci"]
    commune2epci = {c: k for k, v in cfg.items() for c in v["communes"]}
    ecarts = []
    for insee, nom in communes:
        d = payloads[insee]
        if d.get("epci") != commune2epci.get(nom):
            ecarts.append((nom, "epci", d.get("epci"), commune2epci.get(nom)))
        servi = (d.get("foncier") or {}).get("surface_ha")
        brut = session_reelle.execute(text(
            "SELECT round((sum(surface_m2)/10000.0)::numeric)::int FROM parcels WHERE commune=:c"),
            {"c": nom}).scalar()
        if not (servi is not None and brut and servi <= brut and (brut - servi) / brut < 0.03):
            ecarts.append((nom, "surface_ha", servi, brut))
    assert not ecarts, f"écarts bandeau (surface/EPCI) : {ecarts}"


def test_gpu_zonage_coherent(communes, payloads):
    """GPU — la répartition de zonage (U/AU/A/N) somme ~100 % quand elle est servie (cohérence interne)."""
    ecarts = []
    for insee, nom in communes:
        rep = ((payloads[insee].get("foncier") or {}).get("repartition_zonage") or {}).get("familles")
        if not rep:
            continue
        somme = sum((rep.get(k) or {}).get("pct", 0) for k in ("U", "AU", "A", "N"))
        if not (98.0 <= somme <= 102.0):
            ecarts.append((nom, somme))
    assert not ecarts, f"zonage GPU incohérent : {ecarts}"
