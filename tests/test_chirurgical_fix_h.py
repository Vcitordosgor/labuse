"""CHIRURGICAL-FIX-H — gardes unitaires du contre-audit documents (LOT H).

pt1 — Bilan Excel & PDF : coûts requis manquants → résultat/marge/cash-flow GELÉS (comme le PDF),
pas un résultat = CA + 100 % de marge recalculés par formule. Taxe à assiette non renseignée → « — »,
pas « 0 € ».
"""
from __future__ import annotations

from labuse.bilan.excel import classeur_bilan
from labuse.bilan.moteur import EntreesBilan, Moteur, Produit, Programme, SaisiePoste


def _ws_rows(wb):
    return {r[0].value: (r[3].value, r[4].value) for r in wb.active.iter_rows() if r[0].value}


def test_excel_resultat_formule_vivante_gelee_si_cout_majeur_absent():
    """pt1 — le Résultat net reste une FORMULE VIVANTE (pas un texte figé) : IF(aucun coût majeur,
    « non calculable… », CA−dépenses). Tant qu'achat terrain ET construction sont vides, la cellule
    AFFICHE « non calculable » ; dès qu'un coût majeur est saisi, elle CALCULE (recalcul du client)."""
    e = EntreesBilan(programme=Programme(terrain=2000),
                     produits=[Produit("P1", 10, 600, 4785, 0.20)], postes={})
    assert Moteur().calculer(e).resultat_net is None, "pré-condition : incomplet"
    rows = _ws_rows(classeur_bilan(e, titre="t"))
    f_res, f_marge = str(rows["Résultat net"][0]), str(rows["Résultat net"][1])
    f_cash = str(rows["Cash flow"][0])
    # Résultat & cash-flow : FORMULE conditionnelle, pas un texte figé.
    assert f_res.startswith("=IF(") and "non calculable — saisissez vos coûts" in f_res
    # LOT I 1a — condition « un coût requis manque » = OU (achat<=0 OU construction<=0).
    assert "OR(" in f_res and "<=0" in f_res
    assert "-D" in f_res                                  # branche calcul : CA HT − dépenses HT
    assert f_cash.startswith("=IF(") and "non calculable" in f_cash
    # Marge % (col E) & Renta : formule « vide tant qu'incomplet, sinon division » (jamais « 100 % »).
    assert f_marge.startswith("=IF(") and '""' in f_marge
    assert str(rows["Renta nette / CA HT"][1]).startswith("=IF(")


def test_excel_formule_resultat_identique_coûts_vides_ou_saisis():
    """pt1 — la formule du Résultat net est la MÊME que les coûts soient vides ou saisis : c'est la
    cellule qui décide à l'affichage. Un classeur généré « coûts vides » calcule donc dès que le
    client remplit ses coûts (preuve de non-régression : plus de texte figé par état)."""
    prod = [Produit("P1", 1, 55.0, 4500.0, 0.0)]
    vide = _ws_rows(classeur_bilan(EntreesBilan(programme=Programme(), produits=prod, postes={})))
    plein = _ws_rows(classeur_bilan(EntreesBilan(
        programme=Programme(terrain=1000), produits=prod,
        postes={"achat": SaisiePoste(valeur=100.0, etat="ratio"),
                "constr": SaisiePoste(valeur=1500.0, etat="ratio")})))
    assert vide["Résultat net"][0] == plein["Résultat net"][0]
    assert str(vide["Résultat net"][0]).startswith("=IF(")


def test_apporteur_liste_alertes_complete_et_filtree():
    """pt2 — `contraintes_parcelle_liste` = TOUTES les alertes SOFT/HARD de la fiche (aléas, zone
    humide, inondation TRI…), SAUF le marché (VEFA) / le scoring (déclassement, bâti, SDP résiduelle)
    / bassin versant. L'Apporteur n'omet plus la zone humide, et ne liste pas « Marché du neuf »."""
    from labuse.exports.robinet_fiche import EXTRACTEURS
    fiche = {"lines": [
        {"layer": "zone_humide", "result": "SOFT_FLAG", "libelle": "Zone humide inventoriée (100 %)"},
        {"layer": "tri_zone", "result": "SOFT_FLAG", "libelle": "Zone inondable TRI — extreme (85 %)"},
        {"layer": "risques", "result": "SOFT_FLAG", "libelle": "Aléa mouvement de terrain — faible"},
        {"layer": "vefa_neuf", "result": "SOFT_FLAG", "libelle": "Marché du logement neuf (VEFA)"},
        {"layer": "declassement", "result": "SOFT_FLAG", "libelle": "bâti significatif : 20 %"},
        {"layer": "residuel_socle", "result": "SOFT_FLAG", "libelle": "SDP résiduelle 0 m²"},
        {"layer": "bassin_versant", "result": "SOFT_FLAG", "libelle": "Bassin versant"},
        {"layer": "zone_plu", "result": "PASS", "libelle": "zone U"},  # PASS → ignoré
    ]}
    out = EXTRACTEURS["contraintes_parcelle_liste"](None, "x", fiche)
    layers = {x["nature"] for x in (out or [])}
    assert "zone_humide" in layers and "tri_zone" in layers and "risques" in layers
    assert not ({"vefa_neuf", "declassement", "residuel_socle", "bassin_versant"} & layers), \
        "marché/scoring/bassin versant ne sont pas des alertes"
    assert "zone_plu" not in layers  # une ligne PASS n'est pas une alerte


def test_apporteur_alerte_porte_nature_gravite_et_part():
    """pt2 — une alerte reprise dans un document porte la MÊME nature, gravité et part que la fiche :
    « scénario extreme, 85 % » (TRI), « vigilance forte, 34 % » (zone rouge), « 100 % » (zone humide) ;
    seule l'explication longue est jetée (DPU → nature seule)."""
    from labuse.exports.blocs.apporteur import _desc_alerte
    assert _desc_alerte(
        "Zone inondable TRI — scénario extreme (85 % de la parcelle) : cartographie de la directive "
        "inondation ; complète le PPR.") == "Zone inondable TRI — scénario extreme (85 % de la parcelle)"
    assert _desc_alerte(
        "Zone humide inventoriée (espace fonctionnel (2009)) : La Grande Ferme (100 % de la parcelle) "
        "— loi sur l'eau") == "Zone humide inventoriée (espace fonctionnel (2009)) : La Grande Ferme (100 % de la parcelle)"
    assert _desc_alerte(
        "PPR zone rouge sur 34 % de la surface — cette partie est inconstructible (exclue de "
        "l'implantation) ; les prescriptions du règlement PPR ne s'appliquent qu'en zone bleue."
    ) == "PPR zone rouge sur 34 % de la surface — cette partie est inconstructible (exclue de l'implantation)"
    # explication longue sans gravité ni part → nature seule
    assert _desc_alerte(
        "Droit de préemption urbain renforcé — la commune peut préempter à la vente (DIA obligatoire)."
    ) == "Droit de préemption urbain renforcé"
    # gravité courte conservée
    assert _desc_alerte("Aléa mouvement de terrain — niveau faible.") == "Aléa mouvement de terrain — niveau faible"


def test_apporteur_contraintes_sans_doublon_depuis_la_liste_complete():
    """pt2 — avec la liste complète, les prescriptions (DPU…) ne sont pas ajoutées une 2e fois."""
    from labuse.exports.blocs.apporteur import _contraintes

    class _V:
        def __init__(self, v): self.valeur = v
    valeurs = {"contraintes_parcelle_liste": _V([
        {"libelle": "Droit de préemption urbain renforcé — …", "nature": "dpu"},
        {"libelle": "Aléa mouvement de terrain — faible", "nature": "risques"},
    ]), "dpu_perimetre": _V(True)}
    out = _contraintes(valeurs)
    assert out.count("préemption") <= 1, "pas de doublon DPU quand la liste complète le porte"
    assert "Droit de préemption urbain" in out


def test_compare_bati_pct_depuis_le_bien_et_proprio_non_determine():
    """pt4 — le Comparatif lit l'emprise SERVIE (le_bien, = la fiche), pas le résiduel : IS0448
    128/959 = 13 %, plus 27 % (résiduel 259). Sans personne morale, propriétaire « non déterminé »."""
    from labuse.api.app import _compare_row
    qv2 = {"idu": "97411000IS0448", "commune": "Saint-Denis",
           "le_bien": {"emprise_batie_m2": 128}, "surface_terrain_m2": 959,
           "proprietaire_moral": None, "score_v2": {}, "potentiel_transformation": {},
           "potentiel_a_batir": {}, "lines": []}
    faisab = {"residuel": {"disponible": True, "emprise_batie_m2": 259}, "fourchette": {}, "bilan": {}}
    row = _compare_row(qv2, faisab)
    assert row["bati_existant_pct"] == 13, "le bâti % doit venir de le_bien (128), pas du résiduel (259)"
    assert row["proprietaire"] == "non_determine", "sans PM → non déterminé (comme le Dossier), pas particulier"


def test_dossier_ne_dit_copropriete_que_si_sur_la_parcelle():
    """pt5 — une copro « proche_20m » est une voisine (≤ 20 m), pas celle de la parcelle : le Dossier
    ne doit pas la compter dans « Bâti en copropriété ». BW2635 (au 2 rue d'Allemagne) ne possède que
    les copros des 4 et 6 en proche_20m → identité du bien sans copropriété."""
    from labuse.exports.robinet_fiche import EXTRACTEURS
    f = {"coproprietes": [
        {"nom_usage": "BELLEVUE A", "rattachement": "proche_20m", "nb_lots_total": 8},
        {"nom_usage": "BELLEVUE A", "rattachement": "proche_20m", "nb_lots_total": 57},
    ]}
    assert EXTRACTEURS["coproprietes_liste"](None, "x", f) is None, \
        "aucune copro SUR la parcelle → rien à afficher comme copropriété du bien"
    f2 = {"coproprietes": [
        {"nom_usage": "SUR PARCELLE", "rattachement": "cadastre", "nb_lots_total": 12},
        {"nom_usage": "VOISINE", "rattachement": "proche_20m", "nb_lots_total": 8},
    ]}
    sur = EXTRACTEURS["coproprietes_liste"](None, "x", f2)
    assert sur is not None and len(sur) == 1 and sur[0]["nom_usage"] == "SUR PARCELLE"


def test_marge_surelevation_nommee_par_la_contrainte_qui_mord():
    """pt6 — le libellé de la marge suit `hauteur_contrainte` (source unique), jamais « au faîtage »
    en dur. AD0887 : 3,9 m À L'ÉGOUT (la contrainte qui mord), 6,3 m au faîtage — plus d'inversion."""
    from labuse.exports.miroir import libelle_marge_surelevation
    # AD0887 : LiDAR HD, l'égout mord
    assert libelle_marge_surelevation(
        {"hauteur_contrainte": "égout", "hauteur_base": "égout mesuré (LiDAR HD)"}
    ) == "Marge de surélévation à l'égout"
    # faîtage mesuré qui mord
    assert libelle_marge_surelevation(
        {"hauteur_contrainte": "faîtage", "hauteur_base": "faîtage mesuré (LiDAR HD)"}
    ) == "Marge de surélévation au faîtage"
    # BD TOPO (pas de LiDAR) : base « faîtage », pas de contrainte explicite → au faîtage
    assert libelle_marge_surelevation({"hauteur_base": "faîtage"}) == "Marge de surélévation au faîtage"
    # inconnu → libellé générique, jamais une face de toit inventée
    assert libelle_marge_surelevation({}) == "Marge de surélévation sous la règle de hauteur"


def test_estimer_aucun_mot_constructible_sur_parcelle_non_constructible():
    """pt7 — AM0838 (habitat interdit en UE) : Estimer ne qualifie pas 11 762 m² d'« assiette
    constructible » et la phrase de classement porte le motif, pas « l'assiette constructible limite »."""
    from labuse.pige.api import _classement_phrase, _contrainte_limitante, _parcelle_mesures

    # phrase de classement : non constructible → motif, jamais « assiette constructible »
    ph = _classement_phrase("0", "Non retenue",
                            {"detail": "l'assiette constructible limite : l'aléa fort déduit…"},
                            nc_motif="Rien à bâtir — Habitat interdit dans cette zone")
    assert "Habitat interdit" in ph and "assiette constructible" not in ph
    # la contrainte limitante est neutralisée (pas de règle de capacité sur une parcelle non constructible)
    assert _contrainte_limitante(None, "x", {}, "UE", "Z", non_constructible=True) == {}
    # parcelle constructible : la phrase garde sa formulation
    assert "marge constructible reste ouverte" in _classement_phrase("B", "Bonne", {})

    # le tableau des mesures : « Surface hors aléa fort » (non constr.) vs « Assiette constructible »
    class _Res:
        def scalar(self): return 11762
        def mappings(self): return self
        def first(self): return None
    class _DB:
        def execute(self, *a, **k): return _Res()
        def rollback(self): pass
    nc = _parcelle_mesures(_DB(), "x", {"potentiel_transformation": {}}, non_constructible=True)[0]
    ok = _parcelle_mesures(_DB(), "x", {"potentiel_transformation": {}}, non_constructible=False)[0]
    assert nc["cle"] == "Surface hors aléa fort" and "constructible" not in nc["cle"]
    assert ok["cle"] == "Assiette constructible, aléa déduit"


def test_espaces_libres_regle_garde_son_nom_permeable_vs_pleine_terre():
    """pt8 — la règle « art. 2.6 » garde SON nom selon sa citation sourcée : AM0838/UE L'Étang-Salé
    impose « 25 % … perméable » → « Surface perméable », jamais « Pleine terre ». Les vraies règles
    de pleine terre et de biotope gardent le leur."""
    from labuse.faisabilite.zonage import (_pleine_terre_nature, libelle_espaces_libres,
                                            resolve_zone)
    from labuse.plu_reglement import _regles_valeurs

    # classifieur par citation
    cit = lambda c: {"pleine_terre": {"pct": {"pct": 25.0, "citation": c, "statut": "valide"}}}
    assert _pleine_terre_nature(cit("Au moins 25% de la surface de la parcelle doit être perméable.")) == "permeable"
    assert _pleine_terre_nature(cit("conservés en espaces de pleine terre à hauteur de 30 %")) == "pleine_terre"
    assert _pleine_terre_nature(cit("Le coefficient de Biotope est de 30 % minimum")) == "biotope"
    assert _pleine_terre_nature(cit("40% traité en espace vert")) == "espace_vert"
    # libellés
    assert libelle_espaces_libres("permeable") == "Surface perméable"
    assert libelle_espaces_libres(None) == "Pleine terre"      # défaut rétro-compatible

    # bout-à-bout : la zone UE de L'Étang-Salé et le libellé rendu dans le règlement
    zr = resolve_zone("UE", "L'Étang-Salé")
    assert zr.pleine_terre_nature == "permeable" and zr.pleine_terre_pct == 25.0
    ligne = next(r for r in _regles_valeurs(zr, None, 0) if r["cle"] == "pleine_terre")
    assert ligne["libelle"] == "Surface perméable min", ligne["libelle"]


def test_stationnement_pas_non_reglemente_en_zone_habitat_interdit():
    """pt9 — en zone où l'habitat est interdit (AM0838/UE), l'absence de norme PAR LOGEMENT ne se dit
    pas « stationnement non réglementé » : il n'y a pas de logement, et le règlement fixe des normes
    pour les autres destinations. Une zone à habitat autorisé reste « à vérifier »/chiffrée."""
    from labuse.faisabilite.zonage import resolve_zone
    from labuse.plu_reglement import _regles_valeurs

    zr = resolve_zone("UE", "L'Étang-Salé")
    assert zr.habitat == "interdit" and zr.stat_logement is None
    stat = next(r for r in _regles_valeurs(zr, None, 0) if r["cle"] == "stationnement")
    assert "non réglementé" not in stat["valeur"]
    assert "habitat interdit" in stat["valeur"] and "autres destinations" in stat["valeur"]
    assert stat["etat"] != "absent"

    # zone à habitat autorisé : comportement inchangé (jamais le libellé « habitat interdit »)
    zr2 = resolve_zone("UA", "L'Étang-Salé")
    stat2 = next(r for r in _regles_valeurs(zr2, None, 0) if r["cle"] == "stationnement")
    assert "habitat interdit" not in stat2["valeur"]


def test_excel_garde_les_formules_quand_le_resultat_est_calculable():
    e = EntreesBilan(programme=Programme(terrain=2000), produits=[Produit("P1", 10, 600, 4785, 0.20)],
                     postes={"achat": SaisiePoste(valeur=1_000_000, etat="montant"),
                             "constr": SaisiePoste(valeur=1500, etat="ratio")})
    assert Moteur().calculer(e).resultat_net is not None, "pré-condition : calculable"
    rn = _ws_rows(classeur_bilan(e, titre="t"))["Résultat net"][0]
    assert str(rn).startswith("="), "un bilan calculable garde la formule Excel"
