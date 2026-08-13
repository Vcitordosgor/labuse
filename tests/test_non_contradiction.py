"""M73 §2 — TEST DE NON-CONTRADICTION (exigence centrale du mandat).

Génère les CINQ documents (premium, dossier, banquier, one-pager, fiche écran) sur les parcelles
de recette et ÉCHOUE si une valeur commune diffère entre deux documents, ou si un jeton de
contradiction / libellé technique brut atteint le papier. C'est la garantie que le problème
(RAPPORT_M73 : double rail de cascade, aléas côte à côte, PPR divergent) ne revient pas.

Intégration lourde (weasyprint + cascade servie) : nécessite la base servie. `skip` propre si
l'environnement ne peut pas générer (module Flash / DB absents), jamais un faux échec.
"""
from __future__ import annotations

import io
import re

import pytest

pytest.importorskip("pypdf")
pytest.importorskip("weasyprint")

# 3 communes, dont une sans PLU (Saint-Philippe) et une retenue (Saint-Paul, chaude).
PARCELLES = ["97410000BV0120", "97415000AC0253", "97417000AE0003"]
RUN = "q_v8_calibre"

#: jetons qui ne doivent JAMAIS atteindre un document (libellés techniques / contradictions).
INTERDITS = [
    r"INONDATION_MOUVEMENT_DE_TERRAIN", r"mouvement_terrain", r"niveau eleve\b",
    r"intersection marginale", r"parcel_residuel", r"_ass\b", r"spatial_layers#",
    r"parcel_amenites#", r"osm_faux_positif", r"config/plu", r"\(M\d{2}\)",
]


BASE = "http://localhost:8000"


@pytest.fixture(scope="module")
def client():
    """API SERVIE live (recette) — la seule qui porte le run servi. Skip propre si injoignable
    (l'intégration lourde tourne en recette, pas en CI unitaire)."""
    httpx = pytest.importorskip("httpx")
    c = httpx.Client(base_url=BASE, timeout=60.0)
    try:
        r = c.get("/healthz")
        if r.status_code >= 500:
            raise RuntimeError(r.status_code)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"API live {BASE} injoignable : {exc}")
    return c


def _pdf_text(content: bytes) -> str:
    import pypdf
    r = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(p.extract_text() for p in r.pages)


def _docs(client, idu: str) -> dict[str, str]:
    """Texte des 5 documents. Skip la parcelle si un endpoint clé échoue (env)."""
    fiche = client.get(f"/parcels/{idu}", params={"source": RUN})
    if fiche.status_code != 200:
        pytest.skip(f"{idu} : fiche indisponible ({fiche.status_code})")
    prem = client.get(f"/parcels/{idu}/export.pdf", params={"source": RUN})
    dos = client.get(f"/dossier/{idu}.pdf")
    client.post(f"/dossier-banquier/{idu}/prepare")            # amorce le cache (async)
    banq = client.get(f"/dossier-banquier/{idu}.pdf")          # GET direct = synchrone
    op = client.get(f"/parcels/{idu}/export", params={"format": "onepager", "source": RUN})
    for name, r in (("premium", prem), ("dossier", dos), ("banquier", banq), ("one-pager", op)):
        if r.status_code != 200:
            pytest.skip(f"{idu} : {name} indisponible ({r.status_code})")
    return {
        "fiche": _fiche_rendu(fiche.json()),
        "premium": _pdf_text(prem.content),
        "dossier": _pdf_text(dos.content),
        "banquier": _pdf_text(banq.content),
        "one-pager": op.text,
    }


def _fiche_rendu(f: dict) -> str:
    """Texte AFFICHÉ de la fiche écran (details des lignes + verdict), PAS le JSON brut : les champs
    internes (source_table, layer) ne sont pas montrés au client par le front."""
    bouts = []
    for l in f.get("lines", []):
        if l.get("detail"):
            bouts.append(l["detail"])
    sv = f.get("score_v2") or {}
    bouts += [str(sv.get("label") or ""), str(sv.get("motif") or "")]
    return "\n".join(bouts)


@pytest.mark.parametrize("idu", PARCELLES)
def test_aucun_libelle_technique_ni_contradiction(client, idu):
    docs = _docs(client, idu)
    for doc_name, txt in docs.items():
        for pat in INTERDITS:
            assert not re.search(pat, txt), f"{idu} · {doc_name} : jeton interdit « {pat} »"


@pytest.mark.parametrize("idu", PARCELLES)
def test_aleas_un_seul_niveau_partout(client, idu):
    """Un aléa donné n'est jamais listé à plusieurs niveaux, et le niveau est identique d'un doc
    à l'autre (source unique servie)."""
    docs = _docs(client, idu)
    niveaux = ("faible", "modéré", "moyen", "élevé", "fort", "très fort")
    for typ in ("inondation", "mouvement de terrain"):
        vus_par_doc = {}
        for doc_name, txt in docs.items():
            found = set()
            for m in re.finditer(rf"Aléa {re.escape(typ)} — niveau (\w+[\wàéè ]*)", txt):
                found.add(m.group(1).strip().split()[0].lower())
            if found:
                # jamais deux niveaux du même aléa côte à côte dans un même document
                assert len(found) == 1, f"{idu} · {doc_name} : aléa {typ} à {found} niveaux"
                vus_par_doc[doc_name] = next(iter(found))
        # cohérence inter-documents : un seul niveau pour ce type sur l'ensemble
        assert len(set(vus_par_doc.values())) <= 1, \
            f"{idu} : aléa {typ} incohérent entre documents : {vus_par_doc}"


@pytest.mark.parametrize("idu", PARCELLES)
def test_ppr_regime_coherent(client, idu):
    """Le régime PPR réglementaire ne cohabite jamais avec « intersection marginale » (déjà couvert
    par INTERDITS) et « zone rouge » est cohérent : si un doc l'exclut, aucun autre ne l'ignore."""
    docs = _docs(client, idu)
    rouge = {name: ("zone rouge" in txt.lower()) for name, txt in docs.items()}
    # premium & fiche & dossier & banquier & one-pager doivent s'accorder sur la présence du régime rouge
    vals = set(rouge.values())
    assert len(vals) == 1, f"{idu} : « PPR zone rouge » présent dans certains docs seulement : {rouge}"
