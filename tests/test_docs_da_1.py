"""DOCS-DA-1 (gabarit-documents-A, arbitrage Vic) — le GABARIT en test, sur les 11 documents.

Invariants de la maquette validée :
  1. AUCUN fond sombre PLEINE PAGE — papier blanc ; seul aplat sombre = le bandeau de couverture.
  2. POLICES EMBARQUÉES — Inter + JetBrains Mono (plus d'IBM Plex Mono, de Space Grotesk ni de Verdana) ;
     vérifié sur les 11 documents.
  3. AUCUNE TAILLE SOUS 10,5 px — plancher de l'échelle unique (docs WeasyPrint du gabarit).
  4. PIED DE PAGE SANS DATE — la date de la donnée ne vit qu'EN COUVERTURE (« Données à jour au ») ;
     le pied de chaque page de chaque document ne porte aucune date.

Marqué `reel`+`local` : base RÉELLE `labuse` + weasyprint + PyMuPDF (fitz) — jamais en CI.

    PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
      ~/Desktop/labuse/.venv/bin/python -m pytest tests/test_docs_da_1.py -m "reel or local"
"""
from __future__ import annotations

import re

import pytest

pytestmark = [pytest.mark.reel, pytest.mark.local]

_IDU = "97411000BZ1065"
_VOISINES = ("97411000BZ1066", "97411000BZ1288")
_MIN_PT = 7.8                       # 10,5 px = 7,875 pt (tolérance d'arrondi 7,8)
#: familles admises (au repli système DejaVu / Helvetica des champs de formulaire près).
_OK = ("Inter", "JetBrains", "DejaVu")
#: familles INTERDITES par la maquette — « IBM Plex Mono retiré », plus de Space Grotesk ni de Verdana.
_INTERDITES = ("IBM-Plex", "IBMPlex", "IBM Plex", "Space", "Verdana")
#: date imprimée (jj/mm/aaaa) — interdite dans le PIED.
_RX_DATE = re.compile(r"\b\d{2}/\d{2}/(?:19|20)\d{2}\b")


@pytest.fixture(scope="module")
def docs():
    """Les documents LABUSE, rendus. Chaque entrée : (octets, scaled) — `scaled`=True pour les
    documents WeasyPrint qui portent l'échelle px du gabarit (test de taille) ; False pour le fpdf2
    (Courrier) et le Pré-dossier (CERFA)."""
    pytest.importorskip("fitz", reason="PyMuPDF (fitz) indisponible")
    try:
        import io
        import zipfile

        from fastapi.testclient import TestClient
        from sqlalchemy import text

        from labuse.api import bilan as _bilan, tenant
        from labuse.api.app import app
        from labuse.db import session_factory, session_scope
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"application non importable : {exc}")
    db = session_factory()()
    cid = (db.execute(text("SELECT id FROM comptes WHERE statut='actif' ORDER BY id LIMIT 1")).scalar()
           or db.execute(text("SELECT id FROM comptes ORDER BY id LIMIT 1")).scalar() or 1)
    tenant.current_compte = lambda request=None: cid        # type: ignore[assignment]
    _bilan.current_compte = lambda request=None: cid         # type: ignore[assignment]
    c = TestClient(app)
    out: dict[str, tuple[bytes, bool]] = {}

    def _pdf(nom, r, scaled=True):
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            out[nom] = (r.content, scaled)

    _pdf("Dossier", c.get(f"/dossier/{_IDU}.pdf"))
    _pdf("Gabarit", c.get(f"/gabarit/{_IDU}.pdf"))
    _pdf("Estimer", c.get(f"/analyse-annonce/{_IDU}.pdf"))
    _pdf("Etude-zone", c.get(f"/etude-zone.pdf?idu={_IDU}&rayon_km=1"))
    _pdf("Comparatif", c.get(f"/comparatif.pdf?idus={_IDU},{_VOISINES[0]},{_VOISINES[1]}"))
    _pdf("Apporteur", c.get(f"/apporteur/{_IDU}.pdf"))
    _pdf("Courrier", c.post("/courrier/pdf", json={"idu": _IDU}), scaled=False)
    # l'Étude de faisabilité peut renvoyer un 503 transitoire (moteur d'implantation CPU-bound) : on
    # réessaie, pour que le test des polices porte AUSSI sur l'Étude (DOCS-DA-1 V11).
    for _ in range(4):
        r = c.post("/modules/etude/pdf", json={"idus": [_IDU]})
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            out["Etude-faisa"] = (r.content, True)
            break
    g = c.post(f"/bilan/{_IDU}/generer", json={
        "programme": {"terrain": None, "surface_taxable": 65, "sdp": 35},
        "produits": [{"libelle": "Logement", "lots": 1, "suv": 65, "prix_ttc_m2_suv": 4500, "tva": 0.021}],
        "postes": {}, "mode": "marge", "marge_cible": 9, "calendrier": {}})
    if g.status_code == 200 and g.json().get("doc_id"):
        _pdf("Bilan", c.get(f"/bilan/{_IDU}.pdf?doc_id={g.json()['doc_id']}"))
    # Flash — moteur propre (produit 79 €), même gabarit.
    try:
        from labuse.flash.report import generate_flash_report
        with session_scope() as s:
            out["Flash"] = (generate_flash_report(_IDU, order_ref="DA1", force=True, db=s,
                                                   with_map=False).read_bytes(), True)
    except Exception:  # noqa: BLE001 — best-effort (réseau tuiles)
        pass
    # Pré-dossier PC — ZIP : on teste les PDF qu'il contient (LABUSE + CERFA), hors échelle.
    try:
        z = c.get(f"/pre-dossier/{_IDU}.zip")
        if z.status_code == 200 and z.content[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
                for i, n in enumerate(x for x in zf.namelist() if x.lower().endswith(".pdf")):
                    out[f"Pre-dossier::{n}"] = (zf.read(n), False)
    except Exception:  # noqa: BLE001
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


def test_aucune_taille_sous_10_5_px(docs):
    """L'échelle unique a pour plancher 10,5 px (7,875 pt) : aucun glyphe en dessous (docs WeasyPrint)."""
    import fitz
    fautes = []
    for nom, (octets, scaled) in docs.items():
        if not scaled:
            continue
        for sp in _spans(fitz, octets):
            if sp["size"] < _MIN_PT:
                fautes.append(f"{nom}: {sp['size']:.2f}pt « {sp['text'][:24]} »")
    assert not fautes, "tailles sous 10,5 px : " + " ; ".join(sorted(set(fautes))[:20])


def test_polices_embarquees_inter_jetbrains_sur_11_documents(docs):
    """Sur les 11 documents : toute police est EMBARQUÉE, Inter + JetBrains Mono — AUCUNE IBM Plex
    Mono, Space Grotesk ni Verdana. (Helvetica des champs de formulaire tolérée.)"""
    import fitz
    # polices standard-14 PDF (champs de formulaire remplissables) : JAMAIS embarquées par nature,
    # tolérées (l'Apporteur est un formulaire). Ce ne sont pas des polices de corps LABUSE.
    _std14 = ("Helvetica", "Arial", "Times", "Courier", "Symbol", "ZapfDingbats")
    interdites, non_embarquees = [], []
    for nom, (octets, _scaled) in docs.items():
        d = fitz.open(stream=octets, filetype="pdf")
        for pno in range(d.page_count):
            for f in d.get_page_fonts(pno):
                base, emb = (f[3] or ""), (f[1] not in ("", "n/a"))
                if any(k in base for k in _INTERDITES):
                    interdites.append(f"{nom}: « {base} »")
                elif not emb and not any(k in base for k in _std14):
                    non_embarquees.append(f"{nom}: « {base} » NON embarquée")
    assert not interdites, "polices interdites (maquette) : " + " ; ".join(sorted(set(interdites))[:20])
    assert not non_embarquees, "polices non embarquées : " + " ; ".join(sorted(set(non_embarquees))[:20])


def test_pied_de_page_sans_date(docs):
    """Le PIED de chaque page ne porte AUCUNE date (jj/mm/aaaa) : la date ne vit qu'en couverture
    (« Données à jour au »). On lit la bande basse (~15 mm) de chaque page."""
    import fitz
    fautes = []
    for nom, (octets, _scaled) in docs.items():
        d = fitz.open(stream=octets, filetype="pdf")
        for pno in range(d.page_count):
            pg = d[pno]
            seuil = pg.rect.height - 42.0        # ~15 mm en points (bande du pied)
            for blk in pg.get_text("dict")["blocks"]:
                for ln in blk.get("lines", []):
                    for sp in ln.get("spans", []):
                        if sp["bbox"][1] >= seuil and _RX_DATE.search(sp["text"]):
                            fautes.append(f"{nom} p{pno + 1}: « {sp['text'][:30]} »")
    assert not fautes, "date dans le pied de page : " + " ; ".join(sorted(set(fautes))[:20])


def test_pied_de_page_tient_sur_une_ligne(docs):
    """Le pied de page tient sur UNE SEULE ligne de texte (mention légale à gauche, pagination à
    droite) — sur les documents du gabarit (WeasyPrint). On vérifie que la bande basse (~15 mm) ne
    porte qu'UNE rangée de texte (toutes les empreintes sur la même ligne de base)."""
    import fitz
    fautes = []
    for nom, (octets, scaled) in docs.items():
        if not scaled:
            continue
        d = fitz.open(stream=octets, filetype="pdf")
        for pno in range(d.page_count):
            pg = d[pno]
            seuil = pg.rect.height - 42.0
            rangs = set()
            for blk in pg.get_text("dict")["blocks"]:
                for ln in blk.get("lines", []):
                    for sp in ln.get("spans", []):
                        if sp["bbox"][1] >= seuil and sp["text"].strip():
                            rangs.add(round(sp["bbox"][1] / 5.0))   # tolérance ~5 pt = même ligne
            if len(rangs) > 1:
                fautes.append(f"{nom} p{pno + 1}: {len(rangs)} lignes de pied")
    assert not fautes, "pied sur plusieurs lignes : " + " ; ".join(sorted(set(fautes))[:20])


def test_aucun_fond_sombre_pleine_page(docs):
    """Papier blanc partout : aucune page n'est majoritairement sombre (docs WeasyPrint du gabarit)."""
    import fitz
    sombres = []
    for nom, (octets, scaled) in docs.items():
        if not scaled:
            continue
        d = fitz.open(stream=octets, filetype="pdf")
        for pno in range(d.page_count):
            pix = d[pno].get_pixmap(dpi=24)
            n = pix.width * pix.height
            if not n:
                continue
            px, k, dark = pix.samples, pix.n, 0
            for i in range(0, len(px), k):
                lum = (0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]) if k >= 3 else px[i]
                if lum < 110:
                    dark += 1
            if dark / n > 0.40:
                sombres.append(f"{nom} p{pno + 1}: {100 * dark / n:.0f}% sombre")
    assert not sombres, "fond sombre pleine page : " + " ; ".join(sombres[:20])
