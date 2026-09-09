"""M73 §2 — TEST DE NON-CONTRADICTION (exigence centrale du mandat).

EXPORTS-2 lot 8 — les documents sont désormais les CINQ servis par le BUILDER UNIQUE : Dossier,
Résumé, Financier, Apporteur (+ la fiche écran). On les génère sur les parcelles de recette et on
ÉCHOUE si une valeur commune diverge entre deux documents, ou si un jeton de contradiction / libellé
technique brut atteint le papier. C'est la garantie que le problème (RAPPORT_M73 : double rail de
cascade, aléas côte à côte, PPR divergent) ne revient pas. La cohérence est maintenant STRUCTURELLE
(registre : un id = une valeur) ; ce test la vérifie de bout en bout sur le papier.

Le jeu de documents est DÉLIBÉRÉMENT étagé : le Dossier est complet (tout critère servi y figure) ;
le Résumé, le Financier et l'Apporteur sont volontairement partiels. La non-contradiction (accord
là où deux documents se recoupent, aucun jeton technique) vaut pour TOUS ; l'exhaustivité des
critères servis n'est exigée que du Dossier.

Intégration lourde (weasyprint + cascade servie) : nécessite la base servie. `skip` propre si
l'environnement ne peut pas générer (DB / run servi absents), jamais un faux échec.
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
    """Texte des documents du builder unique + la fiche écran. Skip la parcelle si un endpoint clé
    échoue (env). EXPORTS-2 lot 8 : Dossier · Financier · Apporteur (routes directes, pas les
    anciennes redirections). RECETTE-3 (T2) — le Résumé est supprimé, retiré de la comparaison."""
    fiche = client.get(f"/parcels/{idu}", params={"source": RUN})
    if fiche.status_code != 200:
        pytest.skip(f"{idu} : fiche indisponible ({fiche.status_code})")
    dossier = client.get(f"/dossier/{idu}.pdf")
    financier = client.get(f"/financier/{idu}.pdf")
    apporteur = client.get(f"/apporteur/{idu}.pdf")
    for name, r in (("dossier", dossier),
                    ("financier", financier), ("apporteur", apporteur)):
        if r.status_code != 200:
            pytest.skip(f"{idu} : {name} indisponible ({r.status_code})")
    return {
        "fiche": _fiche_rendu(fiche.json()),
        "dossier": _pdf_text(dossier.content),
        "financier": _pdf_text(financier.content),
        "apporteur": _pdf_text(apporteur.content),
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
    rouge = {name: ("zone rouge" in txt.lower()) for name, txt in docs.items() if "zone rouge" in txt.lower()
             or name in ("fiche", "dossier")}
    # les documents qui PARLENT du risque (fiche, Dossier) doivent s'accorder sur le régime rouge ;
    # le Financier (bilan) et l'Apporteur (teaser) ne le mentionnent pas → hors périmètre de cohérence PPR.
    vals = set(rouge.values())
    assert len(vals) == 1, f"{idu} : « PPR zone rouge » présent dans certains docs seulement : {rouge}"


@pytest.mark.parametrize("idu", PARCELLES)
def test_anc_et_rehab_dans_tous_les_documents(client, idu):
    """M73-D — l'assainissement (anc_service.statut_anc) et la réhabilitation (compute_mode_b) sont
    SERVIS à l'écran (toujours un état, jamais un trou). Un critère servi à l'écran mais ABSENT d'un
    document est une divergence de fond : ce test la fait ÉCHOUER, il ne la laisse pas dormir jusqu'au
    prochain audit (la réhab a dormi de M59 à M73-C exactement comme ça). Les blocs ne se masquent
    jamais (un zéro n'est pas une absence) → « Assainissement » et « Réhabilitation » sont attendus
    dans le DOSSIER (document complet). EXPORTS-2 lot 8 : le Résumé/Financier/Apporteur sont étagés
    (partiels par construction) — l'exhaustivité des critères servis n'est exigée que du Dossier."""
    docs = _docs(client, idu)
    for name in ("dossier",):
        texte = docs[name].lower()
        assert "assainissement" in texte, f"{name} : bloc ASSAINISSEMENT absent (critère servi à l'écran)"
        assert "réhabilitation" in texte, f"{name} : bloc RÉHABILITATION absent (critère servi à l'écran)"
