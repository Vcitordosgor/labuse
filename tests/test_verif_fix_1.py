"""VERIF-FIX-1 — les corrections de l'audit VERIF-2 (pures, sans base).

Couvre : l'ÉCHÉANCE de revue des couches carte (Q2 — fraîcheur) et le contrôle d'ortho plus récente
POUR LA RÉUNION (Q3). Les deux lisent/écrivent la base en prod ; ici on prouve la LOGIQUE isolément.
"""
from __future__ import annotations

from datetime import date

from labuse import echeances_couches as ech
from labuse import sentinelle


# ─────────────────────────── Q2 · échéance de revue des couches ───────────────────────────
AUJ = date(2026, 11, 9)


def test_couches_anciennes_remontent_a_verifier():
    """Les couches nommées par le mandat (datées 2006→2022) dépassent la fenêtre de revue (24 mois)."""
    cas = [
        ("Ravines — domaine public fluvial (DEAL)", "DPF arrêté 06-3077 du 21/08/2006"),
        ("Cerema / GéoLittoral — érosion", "millésime 2018"),
        ("EDF Réunion — lignes moyenne tension HTA", "EDF géométrie ~02/2020 · publié 16/10/2025"),
        ("Parc National de La Réunion (INPN)", "millésime 2021"),
        ("DEAL — cartes de bruit stratégiques (CBS)", "CBS 2022"),
    ]
    for nom, mill in cas:
        assert ech.echeance_pour(nom, mill, None, AUJ)["a_verifier"] is True, nom


def test_edf_juge_sur_la_donnee_pas_la_publication():
    """EDF : la géométrie est de 2020 même si « publié 2025 » — l'échéance s'ancre sur 2020 (à vérifier),
    jamais sur l'année de publication (qui masquerait l'ancienneté)."""
    r = ech.echeance_pour("EDF Réunion — lignes moyenne tension HTA",
                          "EDF géométrie ~02/2020 · publié 16/10/2025", None, AUJ)
    assert r["horizon"] == date(2020, 2, 1) and r["a_verifier"] is True


def test_couches_recentes_ne_remontent_pas():
    for nom, mill in [("BPE INSEE", "millésime 2025"),
                      ("Transport public — GTFS", "màj 2025-12-29 → 2026-10-10"),
                      ("DEAL Réunion — PPR / aléas", "PPR approuvé le 2026-04-16")]:
        assert ech.echeance_pour(nom, mill, None, AUJ)["a_verifier"] is False, nom


def test_archives_figees_et_sans_date_jamais_a_verifier():
    # cadastre 1877 géoréférencé : archive figée → aucune échéance (ne clignote jamais)
    assert ech.echeance_pour("50 pas géométriques", "cadastre 1877 (géoréf. 2012/1950)", None, AUJ)["echeance"] is None
    # millésime illisible → pas d'échéance inventée
    assert ech.echeance_pour("Géorisques — ICPE", None, None, AUJ)["a_verifier"] is False


def test_horizon_ingester_respecte_si_pas_de_curation():
    """Un horizon écrit par l'ingester (source non curée) est respecté tel quel."""
    r = ech.echeance_pour("Une source quelconque", None, date(2017, 6, 1), AUJ)
    assert r["horizon"] == date(2017, 6, 1) and r["a_verifier"] is True


def test_edition_inec_recente_avec_periode_historique():
    date_edition = date(2026, 8, 24)
    resultat = ech.echeance_pour("Cerema / GéoLittoral — érosion",
                                "INEC 2026 : période 1950–2020", date_edition, AUJ)
    assert resultat["horizon"] == date_edition
    assert resultat["a_verifier"] is False


def test_annee_seule_ne_devient_pas_une_date_de_publication():
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite://")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE data_sources (id int, name text, source_millesime text, "
                       "source_horizon_at date, prochain_millesime_at date)"))
        c.execute(text("CREATE TABLE spatial_layers (data_source_id int)"))
        c.execute(text("INSERT INTO spatial_layers VALUES (1)"))
        c.execute(text("INSERT INTO data_sources VALUES (1, 'Carte', 'Édition 2026', NULL, NULL)"))
    ech.ensure_echeances_couches(engine)
    with engine.connect() as c:
        horizon, prochaine_revue = c.execute(text(
            "SELECT source_horizon_at, prochain_millesime_at FROM data_sources")).one()
    assert horizon is None
    assert prochaine_revue is not None


# ─────────────────────────── Q3 · ortho plus récente pour La Réunion ───────────────────────────
_CAPS = (
    "<Layer><ows:Identifier>ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2024</ows:Identifier></Layer>"
    "<Layer><ows:Identifier>ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2025</ows:Identifier></Layer>"
    "<Layer><ows:Identifier>ORTHOIMAGERY.ORTHOPHOTOS.RVB-EXPRESS.2026</ows:Identifier></Layer>"
)
_CAPS_URL = "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0"
_SERVI = "BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %)"


def _tuile_url(layer: str) -> str:
    z, x, y = sentinelle._ORTHO_TUILE_974
    return sentinelle._ORTHO_TUILE_URL.format(layer=layer, z=z, x=x, y=y)


def _http_ortho(tuile_2026_status: int):
    def _h(url: str, *, methode_http: str = "GET"):
        if url == _CAPS_URL:
            return (200, {}, _CAPS)
        if url == _tuile_url("ORTHOIMAGERY.ORTHOPHOTOS.RVB-EXPRESS.2026"):
            return (tuile_2026_status, {}, "" if tuile_2026_status >= 400 else "JPEGDATA")
        raise ConnectionError(f"url inattendue : {url}")
    return _h


def test_ortho_2026_hors_reunion_reste_a_jour():
    """La plus récente (2026) existe mais renvoie 404 sur une tuile Réunion → on NE crie PAS."""
    row = {"methode": "ortho", "url_version": _CAPS_URL, "selecteur": None}
    s = sentinelle.sonder_ligne(row, servi=_SERVI, http=_http_ortho(404))
    assert s.statut == "ok" and "2026" in (s.message or "")


def test_ortho_2026_sur_reunion_est_nouvelle_version():
    """Dès que 2026 couvre La Réunion (tuile 200), la sentinelle signale « nouvelle version »."""
    row = {"methode": "ortho", "url_version": _CAPS_URL, "selecteur": None}
    s = sentinelle.sonder_ligne(row, servi=_SERVI, http=_http_ortho(200))
    assert s.statut == "nouvelle_version" and "RVB-EXPRESS.2026" in s.vu
