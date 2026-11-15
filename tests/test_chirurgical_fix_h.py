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


def test_excel_gele_resultat_si_cout_requis_manquant():
    # Programme + produit (donc un CA), AUCUN coût → le moteur ne calcule pas de résultat.
    e = EntreesBilan(programme=Programme(terrain=2000),
                     produits=[Produit("P1", 10, 600, 4785, 0.20)], postes={})
    assert Moteur().calculer(e).resultat_net is None, "pré-condition : incomplet"
    rows = _ws_rows(classeur_bilan(e, titre="t"))
    # Résultat net & cash-flow : texte « non calculable », PAS une formule « =D..-D.. ».
    assert rows["Résultat net"][0] == "non calculable — saisissez vos coûts"
    assert not str(rows["Résultat net"][0]).startswith("=")
    assert rows["Cash flow"][0] == "non calculable — saisissez vos coûts"
    # Marge % (colonne E de la ligne Résultat) : vide, jamais « 100 % ».
    assert rows["Résultat net"][1] in (None, "")
    # Renta nette / CA HT : vide quand incomplet (pas de division sur un texte).
    assert rows["Renta nette / CA HT"][1] in (None, "")


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


def test_excel_garde_les_formules_quand_le_resultat_est_calculable():
    e = EntreesBilan(programme=Programme(terrain=2000), produits=[Produit("P1", 10, 600, 4785, 0.20)],
                     postes={"achat": SaisiePoste(valeur=1_000_000, etat="montant"),
                             "constr": SaisiePoste(valeur=1500, etat="ratio")})
    assert Moteur().calculer(e).resultat_net is not None, "pré-condition : calculable"
    rn = _ws_rows(classeur_bilan(e, titre="t"))["Résultat net"][0]
    assert str(rn).startswith("="), "un bilan calculable garde la formule Excel"
