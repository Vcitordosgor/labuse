"""M-P — exports : matrice morte retirée (P2-62/67), age_dirigeant hors PDF (P2-63), troncature
nommée (P2-64), méthode marché étiquetée (P2-66), sources par nom (P2-68), légal (point 5)."""
from __future__ import annotations

import inspect

import pytest
from sqlalchemy import text


# ── P2-62 / P2-63 — pdf_premium : plus de matrice morte, age_dirigeant exclu (PUR) ──
def test_pdf_premium_pas_de_matrice_morte_et_exclut_age_dirigeant():
    from labuse.api import pdf_premium as pp
    assert not hasattr(pp, "STATUT"), "table matrice morte (STATUT) encore présente"
    assert "age_dirigeant" in pp.COUCHES_EXCLUES, "age_dirigeant doit être exclu du PDF (circule loin)"
    src = inspect.getsource(pp.render_fiche_pdf)
    assert "Statut matrice (historique)" not in src, "second verdict (matrice) encore imprimé"
    assert "sections_omises" in src, "la troncature 2 pages doit NOMMER la section omise (P2-64)"


# ── point 5 — légal : identité EI + déclaration e-mails exacte (PUR) ──
def test_editeur_identite_renseignee():
    from labuse.api.onboarding import _EDITEUR
    assert "987" in _EDITEUR and "917" in _EDITEUR                 # SIREN/SIRET posés
    assert "Saint-Paul" in _EDITEUR and "Saint-Denis" not in _EDITEUR
    assert "à confirmer" not in _EDITEUR                           # plus de placeholder SIREN


def test_cgv_et_mentions_declarent_les_emails():
    from labuse.api import onboarding
    for fn in ("cgv_page", "mentions_page"):
        html = getattr(onboarding, fn)().body.decode()
        assert "Aucun email automatique" not in html
        assert "Aucun envoi d'email automatique" not in html      # déclaration RGPD inexacte retirée
        assert "transactionnels" in html and "List-Unsubscribe" in html
    # article 5 : le point L.215-1-consommation-en-B2B est signalé pour l'avocat (commentaire source)
    assert "SIGNALER À L'AVOCAT" in inspect.getsource(onboarding.cgv_page)


# ── P2-68 — flash : sources par NOM (stables après reconstruction du seed) ──
def test_section_sources_par_nom_pas_par_id():
    from labuse.flash.data import _SECTION_SOURCES
    for section, label, src_name, statique in _SECTION_SOURCES:
        assert src_name is None or isinstance(src_name, str), \
            f"source « {label} » référencée par id numérique (fragile) : {src_name!r}"


@pytest.mark.db
def test_flash_sources_noms_resolvent_et_attribuent_la_bonne_date(db_session):
    """Validation #5 : chaque nom de _SECTION_SOURCES existe (aucun typo → aucun « — » silencieux),
    et la date de synchro est attribuée PAR NOM (indépendante de l'id serial → stable après un seed
    reconstruit dans un ordre différent)."""
    from labuse.flash.data import _SECTION_SOURCES, _sources
    s = db_session
    noms_base = {n for (n,) in s.execute(text("SELECT name FROM data_sources"))}
    for _sec, label, src_name, _st in _SECTION_SOURCES:
        assert src_name is None or src_name in noms_base, f"nom introuvable (typo) : {src_name!r}"
    # une source avec last_sync_at → sa date remonte bien via le nom
    row = s.execute(text("SELECT name, last_sync_at FROM data_sources "
                         "WHERE last_sync_at IS NOT NULL LIMIT 1")).first()
    if row:
        nom, dt = row
        # injecte une entrée de section pointant ce nom et vérifie l'attribution
        import labuse.flash.data as D
        D._SECTION_SOURCES.append(("identite", "SONDE MP", nom, None))
        try:
            out = _sources(s, {"data_sources"}, {"identite"})
        finally:
            D._SECTION_SOURCES.pop()
        sonde = next((o for o in out if o["source"] == "SONDE MP"), None)
        assert sonde and dt.date().isoformat() in sonde["millesime"]


# ── P2-66 — flash : le bloc marché porte une étiquette de MÉTHODE (PUR) ──
def test_marche_construit_une_etiquette_de_methode():
    from labuse.flash import data as D
    src = inspect.getsource(D._marche)
    assert '"methode"' in src and "aberrant" in src               # distingue _marche de sector_price
    tmpl = (__import__("pathlib").Path(D.__file__).parent / "templates" / "rapport.html.j2").read_text()
    assert "m.methode" in tmpl                                    # rendu dans le rapport


# ── P2-66 / P2-67 — flash : méthode marché étiquetée, grille matrice retirée (DB) ──
@pytest.mark.db
def test_flash_marche_methode_et_pas_de_grille_matrice(db_session):
    from labuse.flash.data import collect_report_data
    s = db_session
    # on cherche une parcelle dont le bloc marché est NON vide (pour exercer l'étiquette de méthode)
    idu = None
    for (cand,) in s.execute(text(
            "SELECT p.idu FROM parcels p JOIN parcel_p_score_v2 v ON v.parcelle_id = p.idu "
            "WHERE v.tier IN ('brulante','chaude') LIMIT 40")):
        d = collect_report_data(s, cand)
        assert "score" not in d, "grille matrice Q/A encore servie sur le Flash (P2-67)"
        if d.get("marche") and not d["marche"].get("rien"):
            idu = cand
            break
    if idu is None:
        pytest.skip("aucune parcelle avec marché DVF non vide")
    assert d["marche"].get("methode"), "bloc marché sans étiquette de méthode (P2-66)"
    assert "aberrant" in d["marche"]["methode"]                   # distingue de sector_price
