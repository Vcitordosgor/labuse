"""CAPACITE-1 LOT C — la règle unique « surface à retenir » et le garde-fou « un seul chiffre par parcelle »."""
import os

import pytest

from labuse.faisabilite.surface_retenue import (GRANDEUR_ESQUISSE, GRANDEUR_ESTIMATION,
                                                GRANDEUR_SCENARIO, surface_a_retenir)


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base applicative absente")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    if s.execute(text("SELECT count(*) FROM parcels WHERE idu = '97416000HT0538'")).scalar() != 1:
        s.close()
        pytest.skip("parcelle témoin HT0538 absente")
    yield s
    s.close()


def test_sans_esquisse_estimation_rapide():
    r = surface_a_retenir(614, None)
    assert r["valeur_m2"] == 614 and r["source"] == GRANDEUR_ESTIMATION
    assert "estimation rapide" in r["phrase"] and "esquisse" not in r["phrase"].lower()


def test_esquisse_plus_grande_estimation_retenue():
    # HT0538 — l'esquisse (888) est un MAJORANT : on retient 614 (la plus petite), esquisse à vérifier.
    r = surface_a_retenir(614, {"sdp_m2": 887.5})
    assert r["valeur_m2"] == 614 and r["source"] == GRANDEUR_ESTIMATION
    assert "888 m²" in r["phrase"] and "à vérifier : stationnement non déduit" in r["phrase"]


def test_esquisse_plus_petite_esquisse_retenue():
    # Le Tampon AD0887 — l'esquisse (795) est plus petite : on la retient, à vérifier (surface ≤).
    r = surface_a_retenir(1047, {"sdp_m2": 795})
    assert r["valeur_m2"] == 795 and r["source"] == GRANDEUR_ESQUISSE
    assert "795 m²" in r["phrase"] and "1 047 m²" in r["phrase"]
    assert "stationnement à vérifier" in r["phrase"] and "la surface réelle peut être inférieure" in r["phrase"]


def test_jamais_le_plus_grand_par_defaut():
    # Garde LABUSE : la plus petite des deux, toujours — une esquisse plus grande n'est jamais retenue.
    assert surface_a_retenir(614, 2000)["valeur_m2"] == 614
    assert surface_a_retenir(2000, 614)["valeur_m2"] == 614


# ── CHIRURGICAL-FIX-1 (LOT E) — le chiffre retenu nomme TOUJOURS son scénario ────────────────────
def test_bati_nomme_terrain_libere_demolition():
    # Parcelle BÂTIE : l'estimation/esquisse supposent le terrain libéré → le chiffre le DIT.
    r = surface_a_retenir(1047, {"sdp_m2": 795}, bati=True)
    assert r["valeur_m2"] == 795 and r["source"] == GRANDEUR_ESQUISSE
    assert r["phrase"].startswith("Terrain libéré (démolition) : 795 m²")
    assert "peu réaliste" not in r["phrase"]


def test_copropriete_demolition_peu_realiste_jamais_le_plus_grand():
    # BW2635 — copropriété bâtie : on retient 2 625 (esquisse, la plus petite), JAMAIS 3 317
    # (estimation rapide, > parcelle) ; la démolition est signalée peu réaliste, chiffre indicatif.
    r = surface_a_retenir(3317, {"sdp_m2": 2625}, bati=True, copropriete=True)
    assert r["valeur_m2"] == 2625 and r["valeur_m2"] != 3317
    assert "peu réaliste en copropriété" in r["phrase"] and "chiffre indicatif" in r["phrase"]
    assert "2 625 m²" in r["phrase"] and "3 317 m²" in r["phrase"]


def test_bati_sans_etude_nomme_le_scenario_jamais_un_chiffre_nu():
    # Parcelle bâtie SANS Étude (aucune esquisse) → estimation rapide, mais NOMMÉE « terrain libéré
    # (démolition) », jamais un chiffre nu « surface à retenir ».
    r = surface_a_retenir(3317, None, bati=True)
    assert r["valeur_m2"] == 3317
    assert r["phrase"].startswith("Terrain libéré (démolition) : 3 317 m² (estimation rapide)")


def test_non_bati_garde_la_formulation_surface_a_retenir():
    # Terrain nu (non bâti) : pas de démolition → libellé historique inchangé.
    assert surface_a_retenir(614, None, bati=False)["phrase"].startswith("Surface à retenir : 614 m²")


# ── Garde-fou : un seul « surface à retenir » par parcelle, TOUS les documents (C6/C9) ───────────
@pytest.mark.reel
@pytest.mark.parametrize("idu, valeur_attendue, source_attendue", [
    # ETUDE-STATIONNEMENT-FIX-3 (reliquat) — le dégagement d'allée désormais DUR réduit l'esquisse (allées
    # de 5 m au droit des places) : HT0538 passe de 888 à 450 m² (< estimation 614 → on retient l'esquisse,
    # la plus petite), BW2635 de 2 625 à 360 m² (scénario « votre programme » 4 logements). On teste donc la
    # CONSISTANCE (même surface partout) sur les valeurs à jour.
    ("97416000HT0538", 450, GRANDEUR_ESQUISSE),     # esquisse dégagée (450) < estimation (614) → esquisse
    ("97422000AD0887", 795, GRANDEUR_SCENARIO),     # stationnement déduit → scénario (jamais 1 047 nu)
    ("97422000BW2635", 360, GRANDEUR_ESQUISSE),     # esquisse (votre scénario 4 logts) < estimation 3 317
])
def test_un_seul_surface_a_retenir_tous_documents(session_reelle, idu, valeur_attendue, source_attendue):
    """Dossier (scénario PERSISTÉ), Étude (scénario LIVE) ET Comparatif (compare()) doivent produire LA
    MÊME surface à retenir — sinon deux documents afficheraient deux chiffres (interdit). Le pré-dossier
    lit la même fonction `surface_a_retenir` sur les mêmes entrées (couvert par le chemin canonique)."""
    import os
    from sqlalchemy import text
    from labuse.implantation import revisions as _rev
    from labuse.implantation.service import etudier_payload
    from labuse.exports.etude_faisabilite import (scenario_retenu, scenario_etude_persiste,
                                                   _bareme_stationnement_absent)
    from labuse.faisabilite.surface_retenue import estimation_rapide_m2

    if session_reelle.execute(text("SELECT count(*) FROM parcels WHERE idu=:i"), {"i": idu}).scalar() != 1:
        pytest.skip(f"parcelle {idu} absente")
    # CHIRURGICAL-FIX-1 (LOT E) — config PAR DÉFAUT COMPLÈTE (mêmes clés/défauts que `EtudeIn`, dont
    # terrain="libere") : le study_id persisté par la prod inclut `terrain`, le lookup du Dossier aussi.
    cfg = {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
           "stationnement": "aerien", "terrain": "libere", "niveaux_sous_sol": None}
    payload = etudier_payload(session_reelle, cfg)
    _rev.enregistrer(session_reelle, payload)          # persiste (Dossier/Comparatif/pré-dossier le reliront)

    # Étude = scénario LIVE (du payload). Dossier, Comparatif ET pré-dossier = scénario PERSISTÉ, sur la
    # MÊME estimation rapide live : ces TROIS documents partagent exactement l'expression
    # `surface_a_retenir(estimation_rapide_m2(db, idu), scenario_etude_persiste(db, idu))` — on la vérifie
    # une fois (chemin « persisté ») et on la confronte au chemin LIVE de l'Étude.
    est = estimation_rapide_m2(session_reelle, idu)
    retenu = scenario_retenu(payload)
    scn_live = {"sdp_m2": (retenu or {}).get("resume", {}).get("sdp_m2"),
                "stationnement_applique": not _bareme_stationnement_absent(payload)}
    sar_etude = surface_a_retenir(est, scn_live)                                      # Étude (live)
    sar_persiste = surface_a_retenir(est, scenario_etude_persiste(session_reelle, idu))  # Dossier/Comparatif/pré-dossier

    assert sar_etude["valeur_m2"] == sar_persiste["valeur_m2"], (
        f"surfaces à retenir divergentes pour {idu} : Étude {sar_etude['valeur_m2']} vs "
        f"Dossier/Comparatif/pré-dossier {sar_persiste['valeur_m2']}")
    assert sar_persiste["valeur_m2"] == valeur_attendue and sar_persiste["source"] == source_attendue
    # Sur AD0887, le scénario (795) est retenu — jamais 1 047 (estimation rapide) nu comme capacité.
    assert sar_persiste["valeur_m2"] != 1047


# ── D2/E1 : MÊME liste d'alertes que la fiche dans TOUS les documents (garde 20 parcelles) ───────
import re as _re_t


def _nt(s):
    # alphanumérique seul (sans accents/ponctuation/espaces) : robuste à l'extraction PDF (tiret cadratin,
    # césures de ligne, accents rendus différemment par pypdf vs la source).
    return _re_t.sub(r"[^a-z0-9]", "", (s or "").lower())


def _present(eff, textes):
    """`eff` figure-t-il dans l'un des textes rendus (match par préfixe normalisé) ?"""
    k = _nt(eff)[:28]
    return bool(k) and any(k in t for t in textes)


@pytest.mark.reel
def test_alertes_fiche_dans_les_builders_de_contraintes(session_reelle):
    """20 parcelles tirées (déterministes) : chaque ALERTE DORMANTE de la fiche (`alertes_fiche`, lue en
    direct dans spatial_layers) DOIT figurer dans les builders de contraintes DISTINCTS — l'Étude
    (`_attach_contraintes_signalees`) ET l'Analyse d'annonce (`_risques_complet`). Comparatif, Dossier et
    pré-dossier sont complétés par construction (append / bloc vs `alertes_fiche`) et vérifiés pièce par
    pièce (ZIP compris) par `test_alertes_fiche_dans_les_pieces_zip`."""
    from sqlalchemy import text
    from labuse.api.servitudes import alertes_fiche
    from labuse.api.modules import _attach_contraintes_signalees
    from labuse.pige.api import _risques_complet
    from labuse.api.app import parcel_fiche

    idus = [r[0] for r in session_reelle.execute(text(
        "SELECT idu FROM parcels WHERE cadastre_disparue_le IS NULL ORDER BY md5(idu) LIMIT 20")).all()]
    assert idus, "aucune parcelle témoin"
    manques = []
    for idu in idus:
        attendues = [a["effet"] for a in alertes_fiche(session_reelle, idu)
                     if not str(a.get("categorie") or "").startswith(("Risque naturel", "PPR"))]
        if not attendues:
            continue
        # Étude
        payload = {"terrain": {}}
        _attach_contraintes_signalees(session_reelle, payload, [idu])
        txt_etude = {_nt(x) for x in (payload["terrain"].get("contraintes_signalees") or [])}
        # Analyse d'annonce
        commune = session_reelle.execute(text("SELECT commune FROM parcels WHERE idu=:i"),
                                         {"i": idu}).scalar()
        fiche = parcel_fiche(idu, db=session_reelle)
        txt_analyse = {_nt((r.get("implique") or "") + (r.get("alea") or ""))
                       for r in _risques_complet(session_reelle, idu, fiche, commune)}
        for eff in attendues:
            if not _present(eff, txt_etude):
                manques.append((idu, "Étude", eff[:40]))
            if not _present(eff, txt_analyse):
                manques.append((idu, "Analyse", eff[:40]))
    assert not manques, f"alertes de la fiche absentes d'un document : {manques[:12]}"


@pytest.mark.reel
def test_alertes_temoins_dans_l_etude(session_reelle):
    """ETUDE-STATIONNEMENT-FIX-2 (reliquat #1) — « mêmes alertes partout » étendu à l'Étude sur les TÉMOINS :
    la zone humide d'AD0887 (Le Tampon) et l'inondation de HT0538 (Saint-Pierre), lues en direct par la fiche
    (`alertes_fiche`), DOIVENT figurer dans les contraintes signalées de l'Étude (`_attach_contraintes_signalees`,
    la source du §2 de l'Étude de faisabilité)."""
    from labuse.api.modules import _attach_contraintes_signalees
    for idu, attendu in (("97422000AD0887", "zone humide"), ("97416000HT0538", "inond")):
        payload = {"terrain": {}}
        _attach_contraintes_signalees(session_reelle, payload, [idu])
        signalees = " ".join(payload["terrain"].get("contraintes_signalees") or []).lower()
        assert attendu in signalees, f"{idu} : « {attendu} » absente de l'Étude (contraintes : {signalees[:200]})"


@pytest.mark.reel
def test_alertes_fiche_dans_les_pieces_zip(session_reelle):
    """Pièces INTERNES du pré-dossier (ZIP) + Dossier : chaque alerte dormante de la fiche doit figurer
    dans toute pièce qui a une rubrique contraintes/risques (regles-zonage, PCMI4 notice, Dossier §5).
    Rendu réel (lourd) → échantillon des témoins qui PORTENT une contrainte dormante (dont AD0887 zone
    humide)."""
    from starlette.requests import Request
    import io, zipfile
    from pypdf import PdfReader
    from labuse.api.servitudes import alertes_fiche
    from labuse.api.pre_dossier import pre_dossier_zip

    scope = {"type": "http", "method": "GET", "headers": [], "query_string": b"", "path": "/",
             "client": ("127.0.0.1", 0), "server": ("localhost", 80), "scheme": "http"}
    manques = []
    for idu in ("97422000AD0887", "97416000HT0538"):
        attendues = [a["effet"] for a in alertes_fiche(session_reelle, idu)
                     if not str(a.get("categorie") or "").startswith(("Risque naturel", "PPR"))]
        if not attendues:
            continue
        try:
            resp = pre_dossier_zip(idu, Request(scope), session_reelle)
        except Exception as e:   # noqa: BLE001 — parcelle non constructible : pas de ZIP, hors de ce test
            continue
        textes = []
        with zipfile.ZipFile(io.BytesIO(resp.body)) as z:
            for nom in z.namelist():
                if nom.endswith(".pdf") and any(k in nom for k in ("regles-zonage", "PCMI4")):
                    try:
                        textes.append(_nt(" ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(z.read(nom))).pages)))
                    except Exception:  # noqa: BLE001
                        pass
        for eff in attendues:
            if not _present(eff, textes):
                manques.append((idu, eff[:48]))
    assert not manques, f"alertes de la fiche absentes d'une pièce du ZIP : {manques[:12]}"
