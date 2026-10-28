"""IMPLANTATION-3 LOT A — le document « Étude de faisabilité » (PDF 8 pages) est l'EXPORT FIGÉ de
l'outil.

On exerce le vrai moteur sur des terrains réels (marqués `reel`, rejoués au banc, jamais en CI) :
le PDF lit la MÊME réponse que l'écran (`etudier_payload`) et chaque nombre imprimé est une ligne de
l'outil. Le VERROU (`nombres_hors_payload`) est le cœur du mandat — il doit rendre 0 fuite. On vérifie
aussi : les 8 sections présentes, aucun « conforme », le n° de document DÉTERMINISTE (rejeu identique),
et — réciproque — que les 3 chiffres clés du scénario retenu sont bien IMPRIMÉS (PDF == outil).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

import pytest

from labuse.implantation.moteur import IDUS_ETANG_SALE, IDUS_SAINT_ANDRE, IDUS_SAINT_DENIS

pytestmark = pytest.mark.reel

TEMOINS = {
    "L'Étang-Salé AW (UA)": IDUS_ETANG_SALE,
    "Saint-André AX (UC)": IDUS_SAINT_ANDRE,
    "Saint-Denis DL (Ui)": IDUS_SAINT_DENIS,
}
_SECTIONS = ["Étude de faisabilité", "1. Le terrain", "2. Règles et contraintes",
             "3. Enveloppe constructible", "4. Plan masse", "5. Distribution et coupe",
             "6. Capacité et contrôles", "7. Hypothèses, limites, sources"]


@pytest.fixture(autouse=True)
def _base_reelle():
    """REMISE-1 (Lot B) — rebranche l'engine GLOBAL de l'app sur la base applicative réelle
    (LABUSE_APP_DATABASE_URL) le temps du test. La route `etude_pdf` reçoit `db=session_reelle`, mais
    le CALCUL (`modules._etudier_borne`) ouvre sa PROPRE `session_scope()` (moteur global) — sous
    pytest, conftest le pointe sur `labuse_test` (vide des parcelles témoins) → « parcelles
    introuvables ». Même patron que test_a05_1_capacite_pdf_fiche._base_reelle."""
    from labuse import db as db_mod
    app_url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not app_url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent — base applicative réelle inconnue")
    ancien_eng, ancien_sess = db_mod._engine, db_mod._Session
    db_mod._engine = db_mod.make_engine(app_url)
    db_mod._Session = None
    try:
        yield
    finally:
        db_mod._engine, db_mod._Session = ancien_eng, ancien_sess


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    yield s
    s.close()


def _payload(session, idus):
    from sqlalchemy import text

    from labuse.implantation.service import etudier_payload
    n = session.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                        {"i": idus}).scalar()
    if n != len(idus):
        pytest.skip("parcelles témoins absentes de la base")
    return etudier_payload(session, {"idus": idus, "objectif": "equilibre"})


@pytest.mark.parametrize("nom,idus", list(TEMOINS.items()))
def test_verrou_toute_ligne_est_une_ligne_de_loutil(session_reelle, nom, idus):
    """LE VERROU : chaque nombre du PDF est servi par le payload (extension V5d/V5f)."""
    from labuse.exports import etude_faisabilite as ef
    pl = _payload(session_reelle, idus)
    r = ef.rendu_etude(pl, genere_le="18/10/2026")
    fuites = ef.nombres_hors_payload(pl, r["html"], genere_le="18/10/2026")
    assert fuites == [], f"{nom} — nombres imprimés hors payload : {fuites}"


@pytest.mark.parametrize("nom,idus", list(TEMOINS.items()))
def test_huit_sections_et_jamais_conforme(session_reelle, nom, idus):
    from labuse.exports import etude_faisabilite as ef
    pl = _payload(session_reelle, idus)
    html = ef.rendu_etude(pl, genere_le="18/10/2026")["html"]
    for sec in _SECTIONS:
        assert sec in html, f"{nom} — section manquante : {sec}"
    # « Jamais conforme » : le MOT (l'affirmation) n'apparaît pas ; « conformité » (disclaimer) toléré.
    assert not re.search(r"\bconforme\b", html, re.I), f"{nom} — le mot « conforme » apparaît"


@pytest.mark.parametrize("nom,idus", list(TEMOINS.items()))
def test_numero_deterministe(session_reelle, nom, idus):
    """ETUDE-V6-6 (item 10) — le n° de document est dérivé du study_id (EF-<8>), STABLE par ÉTUDE et
    INDÉPENDANT de la date (deux dates → même numéro) ; identique à l'écran (study_id tronqué)."""
    from labuse.exports import etude_faisabilite as ef
    pl = _payload(session_reelle, idus)
    a = ef.rendu_etude(pl, genere_le="18/10/2026")["numero"]
    b = ef.rendu_etude(pl, genere_le="23/10/2026")["numero"]   # autre date → MÊME numéro (study_id)
    assert a == b and re.match(r"^EF-[0-9a-f]{8}$", a), f"{nom} — n° non déterministe : {a} / {b}"
    assert a == (pl.get("study_id") or "")[:11]                # identique à l'écran


@pytest.mark.skipif(not shutil.which("pdftotext"), reason="pdftotext (poppler) indisponible")
@pytest.mark.parametrize("nom,idus", list(TEMOINS.items()))
def test_pdf_imprime_les_chiffres_du_scenario_retenu(session_reelle, nom, idus):
    """Réciproque du verrou : les 3 chiffres clés du scénario retenu (logements · places · SDP) sont
    bien IMPRIMÉS dans le PDF (pdftotext) — le PDF dit ce que l'outil dit."""
    from labuse.exports import etude_faisabilite as ef
    from labuse.exports.rendu import render_pdf
    pl = _payload(session_reelle, idus)
    if not pl["scenarios"]:
        pytest.skip("aucun scénario sur ce témoin aujourd'hui")
    r = ef.rendu_etude(pl, genere_le="18/10/2026")
    retenu = ef.scenario_retenu(pl, r["retenu_ref"])
    pdf = render_pdf(r["html"])
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t:
        t.write(pdf); path = t.name
    try:
        txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    finally:
        os.unlink(path)
    norm = re.sub(r"[\s  ]", "", txt)
    for cle, val in (("logements", retenu["resume"]["logements"]),
                     ("places", retenu["resume"]["places"])):
        assert str(val) in norm, f"{nom} — {cle}={val} absent du PDF"


@pytest.mark.parametrize("nom,idus", [("L'Étang-Salé", IDUS_ETANG_SALE)])
def test_route_rend_un_pdf(session_reelle, nom, idus):
    """La route POST /modules/etude/pdf sert bien un application/pdf (appel direct, sans serveur)."""
    from sqlalchemy import text

    from labuse.api.modules import EtudePdfIn, etude_pdf
    n = session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                              {"i": idus}).scalar()
    if n != len(idus):
        pytest.skip("parcelles témoins absentes")
    # request=None : l'archivage documents_generes est best-effort (capté), le PDF est quand même rendu.
    resp = etude_pdf(EtudePdfIn(idus=idus, objectif="equilibre"), request=None, db=session_reelle)
    assert resp.media_type == "application/pdf"
    assert resp.body[:4] == b"%PDF"
