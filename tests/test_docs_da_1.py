"""DOCS-DA-1 (gabarit-documents-A, arbitrage Vic) — le GABARIT en test : sur une parcelle témoin,
chaque document rendu respecte les trois invariants de la maquette validée :

  1. AUCUN fond sombre PLEINE PAGE — le papier est blanc partout ; le seul aplat sombre (le bandeau
     de couverture) est un bandeau, jamais une page entière.
  2. POLICES EMBARQUÉES — toute police utilisée est embarquée dans le PDF, et c'est l'une des deux
     familles du gabarit (Inter / JetBrains Mono, « IBM Plex Mono » côté CSS), au repli DejaVu près.
  3. AUCUNE TAILLE SOUS 10,5 px — l'échelle unique (34/20/13,5/12,5/11/10,5 px) a pour plancher
     10,5 px = 7,875 pt ; aucun glyphe ne descend sous ce seuil.

Marqué `reel`+`local` : exige la base RÉELLE `labuse` et weasyprint (venv PDF) + PyMuPDF (fitz) —
jamais en CI (base vierge). Rejoué dans la recette DOCS-DA-1 :

    PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
      ~/Desktop/labuse/.venv/bin/python -m pytest tests/test_docs_da_1.py -m "reel or local"
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.reel, pytest.mark.local]

#: parcelle témoin de référence (Saint-Denis, Uh, bâtie, PPR bleue) + deux voisines pour le Comparatif.
_IDU = "97411000BZ1065"
_VOISINES = ("97411000BZ1066", "97411000BZ1288")
#: plancher de l'échelle : 10,5 px = 7,875 pt (tolérance d'arrondi de rendu : 7,8 pt).
_MIN_PT = 7.8
#: familles admises (au repli système DejaVu près) — AUCUNE autre (plus de Space Grotesk / Verdana).
_FAMILLES_OK = ("Inter", "IBM-Plex", "IBMPlex", "JetBrains", "DejaVu")


@pytest.fixture(scope="module")
def pdfs():
    fitz = pytest.importorskip("fitz", reason="PyMuPDF (fitz) indisponible")
    try:
        from fastapi.testclient import TestClient

        from labuse.api import bilan as _bilan, tenant
        from labuse.api.app import app
        from labuse.db import session_factory
        from sqlalchemy import text
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"application non importable : {exc}")
    db = session_factory()()
    cid = (db.execute(text("SELECT id FROM comptes WHERE statut='actif' ORDER BY id LIMIT 1")).scalar()
           or db.execute(text("SELECT id FROM comptes ORDER BY id LIMIT 1")).scalar() or 1)
    tenant.current_compte = lambda request=None: cid        # type: ignore[assignment]
    _bilan.current_compte = lambda request=None: cid         # type: ignore[assignment]
    c = TestClient(app)
    routes = {
        "Dossier": f"/dossier/{_IDU}.pdf",
        "Gabarit": f"/gabarit/{_IDU}.pdf",
        "Estimer": f"/analyse-annonce/{_IDU}.pdf",
        "Etude-zone": f"/etude-zone.pdf?idu={_IDU}&rayon_km=1",
        "Comparatif": f"/comparatif.pdf?idus={_IDU},{_VOISINES[0]},{_VOISINES[1]}",
    }
    out: dict[str, bytes] = {}
    for nom, url in routes.items():
        r = c.get(url)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            out[nom] = r.content
    # le Flash a son propre moteur (produit 79 €) — même gabarit.
    try:
        from labuse.db import session_scope
        from labuse.flash.report import generate_flash_report
        with session_scope() as s:
            out["Flash"] = generate_flash_report(_IDU, order_ref="DA1", force=True, db=s,
                                                  with_map=False).read_bytes()
    except Exception:  # noqa: BLE001 — Flash best-effort (réseau tuiles) ; les autres documents suffisent
        pass
    if not out:
        pytest.skip("aucun document rendu (base réelle/weasyprint indisponibles)")
    return out


def _spans(fitz, octets: bytes):
    d = fitz.open(stream=octets, filetype="pdf")
    for pg in d:
        for blk in pg.get_text("dict")["blocks"]:
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    if sp["text"].strip():
                        yield sp


def test_aucune_taille_sous_10_5_px(pdfs):
    """L'échelle unique a pour plancher 10,5 px (7,875 pt) : aucun glyphe en dessous."""
    import fitz
    fautes = []
    for nom, octets in pdfs.items():
        for sp in _spans(fitz, octets):
            if sp["size"] < _MIN_PT:
                fautes.append(f"{nom}: {sp['size']:.2f}pt « {sp['text'][:24]} »")
    assert not fautes, "tailles sous 10,5 px : " + " ; ".join(sorted(set(fautes))[:20])


def test_polices_embarquees_inter_et_mono(pdfs):
    """Toute police est embarquée et appartient aux deux familles du gabarit (Inter / JetBrains)."""
    import fitz
    hors = []
    for nom, octets in pdfs.items():
        d = fitz.open(stream=octets, filetype="pdf")
        for pno in range(d.page_count):
            for f in d.get_page_fonts(pno):
                # f = (xref, ext, type, basefont, name, encoding, ...) ; basefont = f[3]
                base = f[3] or ""
                emb = f[1] not in ("", "n/a")   # ext présent → fonte embarquée
                if not emb:
                    hors.append(f"{nom}: « {base} » NON embarquée")
                elif not any(k in base for k in _FAMILLES_OK):
                    hors.append(f"{nom}: « {base} » hors Inter/JetBrains")
    assert not hors, "polices non conformes : " + " ; ".join(sorted(set(hors))[:20])


def test_aucun_fond_sombre_pleine_page(pdfs):
    """Papier blanc partout : aucune page n'est majoritairement sombre. Le bandeau de couverture est
    un bandeau (≈ 6 % de la hauteur), la page de garde reste claire ; un aplat sombre pleine page
    (ancien thème) noircirait la majorité des pixels."""
    import fitz
    sombres = []
    for nom, octets in pdfs.items():
        d = fitz.open(stream=octets, filetype="pdf")
        for pno in range(d.page_count):
            pix = d[pno].get_pixmap(dpi=24)          # basse résolution : on juge la teinte d'ensemble
            n = pix.width * pix.height
            if n == 0:
                continue
            px = pix.samples
            k = pix.n                                  # octets par pixel
            dark = 0
            for i in range(0, len(px), k):
                # luminance approchée (RGB ou gris) ; alpha ignoré
                if k >= 3:
                    lum = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
                else:
                    lum = px[i]
                if lum < 110:
                    dark += 1
            if dark / n > 0.40:
                sombres.append(f"{nom} p{pno + 1}: {100 * dark / n:.0f}% sombre")
    assert not sombres, "fond sombre pleine page : " + " ; ".join(sombres[:20])
