"""A-05-1 (RECETTE-GENERALE-1) — « Capacité (logements) » du Dossier expert = la FOURCHETTE de
la fiche, jamais le drapeau `capacite_estimee`.

Bug corrigé : l'extracteur `capacite_logements` (robinet_fiche) renvoyait le drapeau booléen
`potentiel_transformation.capacite_estimee` → le Dossier imprimait « 1 ». La capacité en
logements que la FICHE affiche vient de getFaisabilite(idu) =
`/modules/faisabilite → capacite.fourchette.logements_au_sol = [min, max]` (rendu « min–max »
par constructibilite.tsx). Le PDF doit montrer EXACTEMENT ce chiffre.

Garantie : pour des parcelles témoins à capacité > 0, la fourchette lue au MÊME moteur que l'écran
(parcel_faisabilite) == la ligne « Capacité (logements) » réellement imprimée dans le PDF
(extraite par pdftotext). Marqué `local` + `reel` : lit la base APPLICATIVE réelle (run servi,
PLU calibré) → hors de la famille unitaire du hook pre-push, rejoué en CI/banc.
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


@pytest.fixture(autouse=True)
def _base_reelle():
    """Rebranche l'engine de l'app sur la base APPLICATIVE réelle (LABUSE_APP_DATABASE_URL) le
    temps du test, puis restaure — même patron que test_docs1_ecran_egale_pdf."""
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


def _fiche_logements_txt(fourchette: dict) -> str | None:
    """La valeur « logements » telle que la FICHE la montre (constructibilite.tsx) : borne haute
    de logements_au_sol ; « min–max » si bornes distinctes, un seul nombre sinon. None si la fiche
    n'affiche pas de nombre (non constructible / capacité nulle)."""
    au_sol = (fourchette or {}).get("logements_au_sol")
    if not isinstance(au_sol, (list, tuple)) or len(au_sol) != 2:
        return None
    lo, hi = int(au_sol[0] or 0), int(au_sol[1] or 0)
    if hi <= 0:
        return None
    return str(hi) if lo == hi else f"{lo}–{hi}"   # demi-cadratin, comme l'écran


def _pdf_capacite_txt(html: str) -> str | None:
    """La ligne « Capacité (logements) » réellement IMPRIMÉE dans le PDF (pdftotext)."""
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
        if "Capacité (logements)" in line:
            # « Capacité (logements)   <valeur>   estimé » → on isole le segment logements.
            m = re.search(r"Capacité \(logements\)\s+(\S+)", line)
            return m.group(1) if m else None
    return None


@pytest.mark.parametrize("idu", TEMOINS)
def test_dossier_capacite_logements_egale_la_fiche(idu):
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

        # 1) ce que la FICHE affiche (source de vérité = getFaisabilite/parcel_faisabilite)
        attendu = _fiche_logements_txt(fz[1].fourchette or {})
        if attendu is None:
            pytest.skip(f"témoin {idu} sans capacité > 0 aujourd'hui (données évoluées)")

        # 2) ce que le PDF (Dossier expert) imprime
        f = parcel_fiche(idu, db=s, request=None)
        res = builder.construire(s, idu, "dossier", fiche=f)

    # L'extracteur sert la MÊME fourchette que la fiche (pas le drapeau).
    cap = res.valeurs.get("capacite_logements")
    assert cap is not None, "capacite_logements non servie au Dossier"
    assert cap.valeur.get("texte") == attendu, (
        f"extracteur {cap.valeur!r} != fiche {attendu!r}")

    # Et le PDF imprime EXACTEMENT ce nombre (jamais « 1 », jamais le drapeau).
    imprime = _pdf_capacite_txt(res.html)
    assert imprime == attendu, (
        f"PDF imprime {imprime!r}, la fiche montre {attendu!r} (régression A-05-1 : drapeau ?)")
    assert imprime not in ("1", "True"), "le Dossier réimprime le drapeau capacite_estimee"
