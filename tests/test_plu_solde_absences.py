import pytest
from labuse.api import modules
from labuse.ingestion import plu_ingest as plu
from scripts import plu_fix14_mesure as mesure
from test_plu_solde import articles


def page_vide(monkeypatch, code, zone, theme):
    for nom, valeur in [("corpus_status", {code: {}}), ("count_reglement", 0),
                        ("search_reglement", []), ("zone_renvoi_note", None)]:
        monkeypatch.setattr(plu, nom, lambda *args, val=valeur, **kw: val)
    return modules.plu_annuaire_search(theme, code, zone, 25, 0, None)


@pytest.mark.parametrize("zone,annexe", [("A", None), ("N", None), ("Ns36", 78), ("Nta53", 86), ("Nta54", 87)])
def test_absence_documentee_et_fiche_du_secteur(monkeypatch, zone, annexe):
    c = page_vide(monkeypatch, "97410", zone, "stationnement")["absence_article"]
    assert c["nature"] == "absence_documentee" and c["document"] == "97410_reglement_20200206.pdf"
    assert "nombre de places" in c["texte"]
    if annexe:
        assert c["complement"]["url"].endswith(f"#page={annexe}")
    if zone == "Nta53":
        assert "accès piéton depuis le parking du Grand Etang" in c["complement"]["texte"]


def test_possession_up_rattachement_incertain(monkeypatch):
    c = page_vide(monkeypatch, "97408", "Up", "hauteur")["absence_article"]
    assert c["nature"] == "rattachement_incertain" and c["url"].endswith("97408_reglement_20260625.pdf#page=7")
    assert "Up" in c["texte"] and "rattachement non établi" in c["texte"]


@pytest.mark.reel
def test_article_12_des_trois_bassins_rend_les_deux_renvois():
    a = next(a for a in articles("97423") if a["article_ref"] == "ARTICLE AUINDICEE 12")
    assert a["page_debut"] == a["page_fin"] == 69
    assert "STATIONNEMENT" in a["texte"] and "Pour la zone AUt, se reporter au règlement de la zone Ub." in a["texte"]
    assert "Pour les autres zones" in a["texte"]


def test_mesure_distingue_non_reglemente_et_titre_seul():
    titre = "Article AUx.12 . Aires de stationnement"
    assert mesure._is_title_only({"texte_verbatim": titre})
    assert not mesure._is_title_only({"texte_verbatim": titre + "\nNon réglementé."})


@pytest.mark.parametrize("code,zone,theme,lettre", [("97410", "Ns36", "stationnement", "D"),
                                                 ("97408", "Up", "hauteur", "I")])
def test_mesure_refuse_une_absence_sans_preuve(monkeypatch, code, zone, theme, lettre):
    route = page_vide(monkeypatch, code, zone, theme)
    monkeypatch.setattr(mesure.M, "plu_annuaire_search", lambda **kw: route)
    assert mesure.classify(None, code, zone, theme) == lettre
    route["absence_article"]["url"] = "https://exemple.invalid/#page=1"
    assert mesure.classify(None, code, zone, theme) == "A"

def test_saint_denis_separe_le_titre_de_la_reponse():
    assert modules.plu_titre_corps("Article AUx.12 . Aires de stationnement\n\nNon réglementé.") == (
        "Aires de stationnement", "Non réglementé.")


@pytest.mark.parametrize("zone,cible,page", [("1AUt", "Ub", 36), ("2AUa", "Ua", 21), ("1AUe", "Ue", 60), ("2AUc", "Uc", 50)])
def test_lien_vers_le_bareme_vise_par_article_12(monkeypatch, zone, cible, page):
    url = "https://data.geopf.fr/annexes/gpu/documents/DU_97423/cf21c184c89988947c077c0500749264/97423_reglement_20220602.pdf"
    row = {"zone": "AUINDICEE", "article_ref": "ARTICLE AUINDICEE 12",
           "document": url.rsplit("/", 1)[1], "pdf_url": url, "page_debut": 69,
           "texte_verbatim": "ARTICLE AUINDICEE 12 - REALISATION D’AIRES DE STATIONNEMENT"}
    monkeypatch.setattr(plu, "corpus_status", lambda *a: {"97423": {}})
    monkeypatch.setattr(plu, "count_reglement", lambda *a, **k: 1)
    monkeypatch.setattr(plu, "search_reglement", lambda *a, **k: [row])
    monkeypatch.setattr(plu, "zone_renvoi_note", lambda *a: None)
    c = modules.plu_annuaire_search("stationnement", "97423", zone, 25, 0, None)["resultats"][0]
    assert c["renvoi_article"] == {"article": cible + " 12", "page": page, "url": url + f"#page={page}"}


@pytest.mark.reel
def test_saint_denis_annexe_des_captages_distincte_du_chapitre_n():
    rows = articles("97411")
    n13 = next(r for r in rows if r["article_ref"] == "Article N.13")
    assert n13["page_fin"] == 123 and "captages et forages" not in n13["texte"].lower()
    annexes = [r for r in rows if r["page_debut"] >= 124]
    assert annexes and all(r["zone"] is None for r in annexes)
    assert any("captage" in r["texte"].lower() for r in annexes)
    r = {"insee": "97411", "document": "97411_reglement_20260805.pdf", "zone": None,
         "page_debut": 138, "article_ref": "Article 10.", "texte_verbatim": "Prescriptions spécifiques aux captages"}
    assert plu._filtre_scope([r], "N", ["N"]) == []
    assert plu._filtre_scope([r], None, None) == [r]


def test_plaine_carte_ub_explique_le_renvoi_imprime_page_75():
    r = {"insee": "97406", "document": "97406_reglement_20230527.pdf", "zone": "UB", "texte_verbatim": "ARTICLE Ub 6"}
    assert plu.mention_rattachement(r, "AUb") == "renvoi à la zone Ub dans le chapitre AU indicée (p. 75)"


def test_trois_bassins_priorise_le_bareme_au_mot_incident(monkeypatch):
    url = "https://data.geopf.fr/annexes/gpu/documents/DU_97423/cf21c184c89988947c077c0500749264/97423_reglement_20220602.pdf"
    rows = [{"article_ref": f"ARTICLE AUINDICEE {n}", "page_debut": p, "zone": "AUINDICEE",
             "document": url.split("/")[-1], "pdf_url": url, "texte_verbatim": txt}
            for n,p,txt in [(2,65,"Les installations de stationnement."),(12,69,"ARTICLE AUINDICEE 12 - STATIONNEMENT")]]
    monkeypatch.setattr(plu, "corpus_status", lambda *a: {"97423": {}})
    monkeypatch.setattr(plu, "count_reglement", lambda *a, **k: 2)
    monkeypatch.setattr(plu, "search_reglement", lambda *a, **k: rows)
    monkeypatch.setattr(plu, "zone_renvoi_note", lambda *a: None)
    d = modules.plu_annuaire_search("stationnement", "97423", "1AUt", 1, 0, None)
    assert d["resultats"][0]["article_ref"] == "ARTICLE AUINDICEE 12" and d["n_groupes"] == 2


def test_mesure_respecte_incertain_sur_toutes_les_cartes(monkeypatch):
    card = {"insee": "97423", "zone": "N", "document": "97423_reglement_20220602.pdf",
            "article_ref": "ARTICLE N 6", "page_debut": 87, "page_fin": 88,
            "texte_verbatim": "ARTICLE N 6 - IMPLANTATION DES CONSTRUCTIONS PAR RAPPORT AUX VOIES ET EMPRISES PUBLIQUES",
            "mention_rattachement": "rattachement non établi dans le règlement écrit, à vérifier"}
    monkeypatch.setattr(modules, "plu_annuaire_search", lambda **kwargs: {"resultats": [card]})
    assert mesure.classify(None, "97423", "Nto1", "implantation") == "I"


@pytest.mark.parametrize("fichier,label,zone,page", [
    ("97422_reglement_20230811.pdf", "1AUe", "UE", 85),
    ("97422_reglement_20230811.pdf", "2AUb", "UB", 85),
    ("97406_reglement_20230527.pdf", "AUe", "UE", 75),
])
def test_renvoi_au_reglement_urbain_de_meme_indice(fichier, label, zone, page):
    r = {"insee": fichier[:5], "document": fichier, "zone": zone, "texte_verbatim": "Implantation des constructions"}
    assert plu.mention_rattachement(r, label) == f"renvoi à la zone {zone.capitalize()} dans le chapitre AU indicée (p. {page})"
