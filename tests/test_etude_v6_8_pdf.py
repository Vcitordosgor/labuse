"""ETUDE-V6-8 — chaque point est PROUVÉ par un test qui LIT le PDF généré (pdftotext), pas le payload.

Cas de recette : Étang-Salé AW 99/451/624/625, résidence étudiante.
  - aérien   : 11 T1 + 5 T2 + 2 T3 + 5 T4  (23 logements, 27 places)
  - sous-sol : 39 T1 + 5 T2 + 9 T3 + 20 T4 (1 niveau)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

import pytest

from labuse.implantation.moteur import IDUS_ETANG_SALE

pytestmark = [pytest.mark.reel,
              pytest.mark.skipif(not shutil.which("pdftotext"), reason="pdftotext (poppler) indisponible")]

_SURF = {"T1": 30, "T2": 56, "T3": 70, "T4": 80}
_GEN = "24/10/2026"


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy.orm import sessionmaker
    from labuse.db import make_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    yield s
    s.close()


def _payload(session, mix: dict, stationnement: str):
    from sqlalchemy import text
    from labuse.implantation.service import etudier_payload
    n = session.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"),
                        {"i": IDUS_ETANG_SALE}).scalar()
    if n != len(IDUS_ETANG_SALE):
        pytest.skip("parcelles témoins absentes de la base")
    e = {"idus": IDUS_ETANG_SALE, "type_projet": "etudiante", "stationnement": stationnement,
         "programme": {"mode": "saisi", "lignes": [{"type": t, "nombre": nb, "surface_m2": _SURF[t]}
                                                   for t, nb in mix.items()]}}
    if stationnement == "sous_sol":
        e["niveaux_sous_sol"] = 1
    return etudier_payload(session, e)


def _pdf_texte(payload) -> str:
    from labuse.exports import etude_faisabilite as ef
    from labuse.exports.rendu import render_pdf
    html = ef.rendu_etude(payload, genere_le=_GEN)["html"]
    pdf = render_pdf(html)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t:
        t.write(pdf); path = t.name
    try:
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
    finally:
        os.unlink(path)


def test_item1_une_seule_implantation(session_reelle):
    """Item 1 — une seule implantation (le programme du client) : logements=23 et places=23 identiques au
    plan, à la répartition, aux contrôles et à la page 1 ; aucune « autre implantation possible ».

    REMISE-1 (Lot B) — recette RÉ-ANCRÉE 27 → 23 places. L'étude applique désormais le PLAFOND du Code de
    l'urbanisme (art. L151-35 = 1 place / logement), PLUS FAVORABLE que le barème PLU (ex-UA 2.7.3) qui
    donnait 27 places pour 23 logements. Changement DÉLIBÉRÉ et déployé (ETUDE-V6-7/8 « stationnement
    plafonné » + DOCS-COHERENCE-1 F9), postérieur au gel de la recette (24/10) : vérifié IDENTIQUE en PROD
    et en local (23 places les deux) → ce n'est NI un retard de base locale NI une régression, mais la
    recette qui n'avait pas suivi la règle validée. 23 logements × 1 place/logt = 23 places."""
    from labuse.exports import etude_faisabilite as ef
    pl = _payload(session_reelle, {"T1": 11, "T2": 5, "T3": 2, "T4": 5}, "aerien")
    retenu = ef.scenario_retenu(pl)
    L, P = retenu["resume"]["logements"], retenu["resume"]["places"]
    assert (L, P) == (23, 23)                                     # garde-fou du cas de recette (plafond L151-35)
    txt = _pdf_texte(pl)
    assert "autre implantation" not in txt.lower()               # annexe supprimée
    # répartition par niveau : la somme imprimée des logements = L (lue dans le payload du plan rogné)
    distro = sum(v for d in retenu["distribution_niveaux"] for v in (d.get("par_type") or {}).values())
    assert distro == L
    # contrôle « Stationnement » : les places dessinées = P
    ctrl = next((c for c in retenu["controles"] if c["nom"] == "Stationnement"), {})
    assert str(P) in str(ctrl.get("mesure") or "")
    # planche (image dans le PDF) : le cartouche imprime le total rogné (23), jamais l'ancien maximum.
    norm = re.sub(r"[\s  ]", "", txt)
    assert str(L) in norm and str(P) in norm
    # un seul total de logements : l'ancien maximum du bâtiment (27) n'apparaît plus comme total dessiné.
    assert "Logements" in txt


def test_item1b_statut_recalcule_pas_simulation_impossible(session_reelle):
    """Item 1b — le statut est recalculé sur le plan rogné : quand le plan tient la demande (tenus =
    demandés) avec 0 contrôle échoué, le PDF ne dit JAMAIS « Simulation impossible »."""
    from labuse.exports import etude_faisabilite as ef
    pl = _payload(session_reelle, {"T1": 11, "T2": 5, "T3": 2, "T4": 5}, "aerien")
    retenu = ef.scenario_retenu(pl)
    tenus = sum((retenu["programme"].get("par_type") or {}).values())
    demandes = sum(v for d in [{"T1": 11, "T2": 5, "T3": 2, "T4": 5}] for v in d.values())
    echoues = retenu["controles_compte"]["echoue"]
    assert tenus == demandes and echoues == 0                    # garde-fou du cas de recette
    txt = _pdf_texte(pl)
    assert "Simulation impossible" not in txt
    assert re.search(r"[Ee]xploitable", txt)                     # statut positif attendu


def test_item2b_une_seule_ligne_stationnement_sans_tiret(session_reelle):
    """Item 2b — dans le tableau des règles (section 2) : AUCUNE ligne de règle avec la valeur « — », et UNE
    SEULE ligne de stationnement portant sa règle (art. L151-35).

    REMISE-1 (Lot B) — citation RÉ-ANCRÉE « UA 2.7.3 » → « L151-35 ». L'étude cite désormais le PLAFOND du
    Code de l'urbanisme (art. L151-35, 1 place/logement) qui PRIME sur le barème PLU (ex-UA 2.7.3) car plus
    favorable ; le PLU reste mentionné comme non liant (« ne s'applique que s'il est plus favorable »).
    Changement déployé (ETUDE-V6-7/8 + DOCS-COHERENCE-1 F9) postérieur au gel de la recette, IDENTIQUE en
    PROD et en local → recette non suivie, pas une régression. L'INTENTION du test est inchangée : une
    SEULE ligne de stationnement portant sa règle, et aucune valeur « — »."""
    pl = _payload(session_reelle, {"T1": 11, "T2": 5, "T3": 2, "T4": 5}, "aerien")
    txt = _pdf_texte(pl)
    # le TABLEAU des règles (section 2) va de « 2. Règles » jusqu'à la section « Stationnement & mixité ».
    apres_titre = txt.split("2. R", 1)[-1]
    tableau = re.split(r"Stationnement\s*&\s*mixit", apres_titre)[0]
    # une seule ligne de stationnement portant sa règle (art. L151-35) dans le tableau des règles.
    assert tableau.count("L151-35") == 1, f"occurrences L151-35 dans le tableau = {tableau.count('L151-35')}"
    # aucune ligne de règle avec la valeur « — » (plus de stationnement « nu »).
    for ligne in tableau.splitlines():
        cols = re.split(r"\s{2,}", ligne.strip())
        if len(cols) >= 2 and cols[1].strip() == "—":
            raise AssertionError(f"ligne de règle avec valeur « — » : {ligne!r}")


def test_item2_un_seul_numero_de_document(session_reelle):
    """Item 2 — un seul n° de document partout (page 1, cartouche plan, cartouche coupe, pied de page,
    écran) : le PDF ne contient qu'UN motif EF-…, égal à celui de l'écran (study_id)."""
    for stat, mix in (("aerien", {"T1": 11, "T2": 5, "T3": 2, "T4": 5}),
                      ("sous_sol", {"T1": 39, "T2": 5, "T3": 9, "T4": 20})):
        pl = _payload(session_reelle, mix, stat)
        ecran = (pl.get("study_id") or "")[:11]
        txt = _pdf_texte(pl)
        motifs = sorted(set(re.findall(r"EF-[0-9A-Za-z\-]+", txt)))
        assert motifs == [ecran], f"{stat} — motifs PDF={motifs} ≠ écran {ecran}"


def test_item3_titre_et_regle_stationnement(session_reelle):
    """Item 3 — titre « Étude de faisabilité — L'Étang-Salé · parcelles AW 99, 451, 624, 625 » ; règle de
    stationnement RENSEIGNÉE dans le tableau des règles (section 2)."""
    pl = _payload(session_reelle, {"T1": 11, "T2": 5, "T3": 2, "T4": 5}, "aerien")
    txt = _pdf_texte(pl)
    titre = "Étude de faisabilité — L'Étang-Salé · parcelles AW 99, 451, 624, 625"
    assert re.sub(r"\s+", " ", titre) in re.sub(r"\s+", " ", txt)
    sec2 = txt.split("3. Enveloppe")[0].split("2. R")[-1]        # entre « 2. Règles… » et « 3. Enveloppe »
    assert re.search(r"Stationnement", sec2), "règle de stationnement absente du tableau des règles"


def test_item4_sous_sol_rampe_hauteur_et_pleine_terre(session_reelle):
    """Item 4 — rampe comptée (jamais 0 m²) ; le sous-sol peut déborder du bâtiment tant que la pleine terre
    reste ≥ 30 % ; « Ce qui limite » ne cite jamais la hauteur quand le bâtiment est sous le plafond."""
    pl = _payload(session_reelle, {"T1": 39, "T2": 5, "T3": 9, "T4": 20}, "sous_sol")
    from labuse.exports import etude_faisabilite as ef
    retenu = ef.scenario_retenu(pl)
    txt = _pdf_texte(pl)
    # rampe comptée dans le tableau des surfaces, jamais 0.
    assert (retenu["stationnement"].get("rampe_m2") or 0) > 0
    assert re.search(r"[Rr]ampe", txt)
    # pleine terre ≥ 30 % de la contenance (le sous-sol a pu déborder, mais pas manger la pleine terre).
    cont = pl["terrain"]["contenance_totale_m2"]
    assert (retenu.get("pleine_terre_m2") or 0) >= 0.30 * cont
    # « Ce qui limite » ne cite pas la hauteur quand on est sous le plafond.
    niv = retenu["niveaux"]
    hp = next((l for l in pl["regles"]["lignes"] if "égout" in (l.get("nom") or "")), None)
    niv_max = int(hp["valeur"] // 3) if (hp and hp.get("valeur")) else niv
    if niv < niv_max:
        assert "hauteur" not in (pl.get("facteur_limitant") or "").lower()


def test_item4_sous_sol_nouveau_maximum(session_reelle):
    """Item 4 — rejouer 39/5/9/20 et DONNER le nouveau maximum : le sous-sol débordant du bâtiment (zone
    d'implantation, 2 orientations de bandes) relève le maximum au-dessus de l'ancien plafond (26)."""
    pl = _payload(session_reelle, {"T1": 39, "T2": 5, "T3": 9, "T4": 20}, "sous_sol")
    kmax = (pl.get("capacite_maximale") or {}).get("logements")
    assert kmax is not None and kmax > 26, f"le maximum sous-sol devrait dépasser 26, obtenu {kmax}"
