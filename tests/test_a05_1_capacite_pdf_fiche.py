"""A-05-1 → IMPLANTATION-3 (LOT B) — le Dossier NE CHIFFRE PLUS la capacité en logements.

Histoire : l'extracteur `capacite_logements` (robinet_fiche) lisait l'ancien moteur de faisabilité et
le Dossier imprimait « Capacité (logements) : N » (au départ, le drapeau booléen « 1 » ; corrigé en
fourchette par A-05-1). IMPLANTATION-3 crée un document dédié « Étude de faisabilité » (moteur
`src/labuse/implantation`) : le NOMBRE de logements lui revient. Le §Potentiel du Dossier (et donc du
Flash) imprime désormais un RENVOI « Nombre de logements · voir l'Étude de faisabilité », JAMAIS un
nombre tiré de l'ancien moteur. La partie réglementaire (SDP résiduelle, surélévation) reste.

Garantie : pour une parcelle témoin constructible, le Dossier (a) imprime le renvoi, (b) n'imprime
aucun nombre de logements à cette ligne, (c) n'imprime plus le libellé « Capacité (logements) ».
Marqué `local` + `reel` : lit la base APPLICATIVE réelle (run servi, PLU calibré).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

import pytest

pytestmark = [pytest.mark.local, pytest.mark.reel]

# Témoins à capacité > 0 (R+6 Le Tampon, R+3 Saint-Denis) — cf. mandat A-05-1.
TEMOINS = ("97422000BX1106", "97411000AT0427")
RENVOI = "voir l'Étude de faisabilité"


@pytest.fixture(autouse=True)
def _base_reelle():
    """Rebranche l'engine de l'app sur la base APPLICATIVE réelle (LABUSE_APP_DATABASE_URL) le temps
    du test, puis restaure — même patron que test_docs1_ecran_egale_pdf."""
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


def _ligne_potentiel_pdf(html: str) -> str | None:
    """La ligne « Nombre de logements … » réellement IMPRIMÉE dans le PDF (pdftotext)."""
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext (poppler) indisponible")
    from labuse.exports import rendu
    pdf = rendu.render_pdf(html)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t:
        t.write(pdf)
        path = t.name
    try:
        txt = subprocess.run(["pdftotext", "-layout", path, "-"],
                             capture_output=True, text=True).stdout
    finally:
        os.unlink(path)
    for line in txt.splitlines():
        if "Nombre de logements" in line:
            return line
    return None


@pytest.mark.parametrize("idu", TEMOINS)
def test_dossier_renvoie_vers_letude_sans_chiffrer(idu):
    from sqlalchemy import text

    from labuse.api.app import parcel_fiche
    from labuse.db import session_scope
    from labuse.exports import builder
    from labuse.faisabilite.db import parcel_faisabilite

    with session_scope() as s:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        if pid is None:
            pytest.skip(f"témoin {idu} absent de la base aujourd'hui")
        fz = parcel_faisabilite(s, pid)
        if fz is None or not fz[1].constructible:
            pytest.skip(f"témoin {idu} non constructible aujourd'hui (données évoluées)")

        f = parcel_fiche(idu, db=s, request=None)
        res = builder.construire(s, idu, "dossier", fiche=f)

    html = res.html
    # (a) le renvoi est imprimé (l'apostrophe est échappée en &#x27; dans le HTML — on compare la ligne) ;
    #     (c) l'ancien libellé « Capacité (logements) » a disparu.
    assert "Nombre de logements" in html and "Étude de faisabilité" in html, (
        "le renvoi vers l'Étude de faisabilité est absent du Dossier")
    assert "Capacité (logements)" not in html, "l'ancien libellé « Capacité (logements) » subsiste"

    # (b) la ligne imprimée ne porte AUCUN nombre de logements tiré de l'ancien moteur.
    ligne = _ligne_potentiel_pdf(html)
    assert ligne is not None, "ligne « Nombre de logements » absente du PDF"
    assert RENVOI in ligne, f"la ligne ne renvoie pas vers l'Étude : {ligne!r}"
    assert not re.search(r"\d", ligne.split("Nombre de logements", 1)[1]), (
        f"un nombre est imprimé sur la ligne de capacité : {ligne!r}")
