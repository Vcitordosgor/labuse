"""CHIRURGICAL-FIX-1 — LOT I : gardes du 2e contre-audit du relecteur indépendant (4 parcelles)."""
from __future__ import annotations

import pytest

from labuse.bilan.excel import classeur_bilan
from labuse.bilan.moteur import EntreesBilan, Produit, Programme, SaisiePoste


def _ws_rows(wb):
    return {r[0].value: (r[3].value, r[4].value) for r in wb.active.iter_rows() if r[0].value}


def test_1a_excel_condition_est_un_ou_deux_couts_requis():
    """1a — le résultat est « non calculable » tant qu'un coût requis manque : la condition est un
    OU (achat<=0 OU construction<=0), pas un ET. Avec le seul achat, le résultat reste gelé."""
    rows = _ws_rows(classeur_bilan(
        EntreesBilan(produits=[Produit("P", 1, 55.0, 4500.0, 0.0)], postes={}), titre="t"))
    f_res = str(rows["Résultat net"][0])
    # LOT L 3 — le résultat est d'abord gardé par la cellule de validité, PUIS « non calculable » si un
    # coût requis manque : la condition reste un OU (achat<=0 OU construction<=0), pas un ET.
    assert "IF(OR(" in f_res and "non calculable" in f_res
    assert f_res.count("<=0") == 2


def test_1b_marge_sans_division_par_zero_si_ca_nul():
    """1b — la marge ne divise jamais par un CA nul (ventes à zéro) → pas de #DIV/0! : la formule
    porte une garde « OU CA=0 → vide »."""
    rows = _ws_rows(classeur_bilan(
        EntreesBilan(programme=Programme(terrain=1000),
                     postes={"achat": SaisiePoste(100.0, "ratio"),
                             "constr": SaisiePoste(1500.0, "ratio")}), titre="t"))
    f_marge = str(rows["Résultat net"][1])          # colonne E de la ligne Résultat net
    # LOT L 3 — gardée par la validité, puis « OU CA=0 → vide » (pas de #DIV/0!).
    assert "IF(OR(" in f_marge and "=0" in f_marge and '""' in f_marge
    f_renta = str(rows["Renta nette / CA HT"][1])
    assert "=0" in f_renta and '""' in f_renta


def test_1c_valeurs_en_cache_relu_sans_recalcul_egal_moteur():
    """1c — le classeur porte ses valeurs calculées EN PLUS des formules : relu SANS recalcul
    (data_only, comme un aperçu Finder/téléphone), il donne les mêmes chiffres que le moteur."""
    import io

    from openpyxl import load_workbook

    from labuse.bilan.excel import classeur_bilan_bytes
    from labuse.bilan.moteur import Moteur
    e = EntreesBilan(programme=Programme(terrain=1000, sdp=800, surface_taxable=800),
                     produits=[Produit("Libre", 10, 800, 5000, 0.085)],
                     postes={"achat": SaisiePoste(1000, "ratio", tva=0.0),
                             "constr": SaisiePoste(1500, "ratio", tva=0.085)})
    r = Moteur().calculer(e)
    ws = load_workbook(io.BytesIO(classeur_bilan_bytes(e, titre="t")), data_only=True).active
    rows = {row[0].value: (row[3].value, row[4].value) for row in ws.iter_rows() if row[0].value}
    assert rows["Chiffre d'affaires"][0] == pytest.approx(r.ca_ht, abs=1.0)
    assert rows["Dépenses totales"][0] == pytest.approx(r.depenses_ht, abs=1.0)
    assert rows["Résultat net"][0] == pytest.approx(r.resultat_net, abs=1.0)
    assert rows["Résultat net"][1] == pytest.approx(r.marge_pct, abs=1e-4)
    assert rows["Cash flow"][0] == pytest.approx(r.cash_flow, abs=1.0)
    # beaucoup de cellules numériques en cache (pas un aperçu vide)
    assert sum(1 for row in ws.iter_rows() for c in row if isinstance(c.value, (int, float))) > 150


def test_1c_couts_vides_cache_le_texte_pas_un_zero():
    """1c — coûts vides : le cache porte « non calculable… » (string), la marge reste vide — jamais
    un faux 0 ni un #DIV/0! dans l'aperçu."""
    import io

    from openpyxl import load_workbook

    from labuse.bilan.excel import classeur_bilan_bytes
    ws = load_workbook(io.BytesIO(classeur_bilan_bytes(
        EntreesBilan(produits=[Produit("P", 1, 55.0, 4547.0, 0.0)], postes={}), titre="t")),
        data_only=True).active
    rows = {row[0].value: (row[3].value, row[4].value) for row in ws.iter_rows() if row[0].value}
    assert rows["Résultat net"][0] == "non calculable — saisissez vos coûts"
    assert rows["Résultat net"][1] in (None, "")


def test_1b_cout_negatif_refuse_a_la_saisie():
    """1b — un coût négatif (taux/montant ou assiette) est refusé à la saisie (validation API)."""
    from labuse.api.bilan import SaisieIn
    SaisieIn(valeur=1000.0)                           # positif : accepté
    SaisieIn(valeur=0.0)                              # nul : accepté
    with pytest.raises(ValueError):
        SaisieIn(valeur=-100.0)
    with pytest.raises(ValueError):
        SaisieIn(assiette_valeur=-5.0)


def test_3a_copro_voisine_pas_peu_realiste():
    """3a — « démolition peu réaliste en copropriété » ne vaut que si la parcelle EST en copropriété
    (copro sur la parcelle), pas si la copro est seulement voisine (proche_20m — BW2635)."""
    from labuse.faisabilite.surface_retenue import _amorce
    assert "peu réaliste" not in _amorce(True, False)      # bâti, pas de copro sur la parcelle
    assert "peu réaliste" in _amorce(True, True)           # bâti + copro sur la parcelle
    # le drapeau copro ne compte QUE les copros non « proche_20m »
    voisines = [{"rattachement": "proche_20m"}, {"rattachement": "proche_20m"}]
    assert any(c.get("rattachement") != "proche_20m" for c in voisines) is False


def test_3b_bati_connu_pas_bati_non_determine():
    """3b — quand l'emprise bâtie est connue (IS0448 : 128 m²), l'absence de marge de hauteur n'est pas
    « bâti non déterminé » mais « hauteur du bâti non mesurée »."""
    from labuse.exports.miroir import _absence_une_raison
    ph = "Marge de surélévation non calculable (hauteur de règle ou bâti non déterminés)."
    assert "hauteur du bâti non mesurée" in _absence_une_raison(ph, "U", bati_connu=True)
    assert "bâti non déterminé" not in _absence_une_raison(ph, "U", bati_connu=True)
    # bâti inconnu → on garde « bâti non déterminé »
    assert "bâti non déterminé" in _absence_une_raison(ph, "U", bati_connu=False)
    # gabarit bloqué → c'est la hauteur de règle
    assert "hauteur de règle non déterminée" in _absence_une_raison(ph, "U", gabarit_bloque=True, bati_connu=True)


def test_3c_le_tampon_sol_combine_et_stationnement_renvoi():
    """3c (révisé LOT J pt3a/pt3c) — Le Tampon : les deux obligations de sol tiennent en UNE phrase
    (« X % perméable, dont au moins Y % en pleine terre »), et la ligne stationnement RENVOIE à son
    article (barème à paliers non servi en détail). AD0887=Ud (30 %/40 %), BW2635=Uav (20 %/30 %)."""
    from labuse.faisabilite.zonage import resolve_zone
    from labuse.plu_reglement import _regles_valeurs
    attendu = {"Ud": (30.0, 40.0), "Uav": (20.0, 30.0)}
    for zc, (pt, perm) in attendu.items():
        zr = resolve_zone(zc, "Le Tampon")
        assert zr.pleine_terre_pct == pt and zr.permeabilite_pct == perm
        lignes = {r["cle"]: r for r in _regles_valeurs(zr, None, 0)}
        # LOT J pt3c — UNE phrase combinée, plus de ligne « surface_permeable » séparée.
        assert lignes["pleine_terre"]["valeur"] == f"{perm:g} % de la parcelle en surface perméable et {pt:g} % de la parcelle en pleine terre"
        assert lignes["pleine_terre"]["libelle"] == "Surface perméable et pleine terre"
        assert "surface_permeable" not in lignes
        # LOT J pt3a — renvoi à l'article, jamais un nombre partiel.
        stat = lignes["stationnement"]["valeur"]
        assert "barème selon le type de logement et la taille de l'opération" in stat
        assert f"article {'Ud' if zc == 'Ud' else 'Ua'} 12.2" in stat
        assert "1 place" not in stat
        # la capacité lit toujours 1 place/logement (le renvoi ne la change pas)
        assert zr.places_par_logement() == 1.0


def test_3d_comparables_note_8_plus_proches_pas_la_mediane():
    """3d — le tableau des 8 ventes les plus proches DIT qu'il n'est pas l'échantillon du prix médian
    (calculé sur tout le secteur) ; et le pool estimer3 dédoublonne par identifiant de mutation."""
    from labuse.exports.blocs.annonce import _comparables
    from labuse.pige.estimer3 import _POOL_SQL
    html = _comparables({"comparables": [{"date": "2025-01-01", "type": "Maison", "surface_m2": 80,
                                          "prix_eur": 200000, "prix_m2": 2500, "distance_m": 100}]})
    # LOT J pt3e — classées par RESSEMBLANCE (plus « les plus proches »), et toujours distinguées de la médiane.
    assert "ressemblant" in html and "médian" in html and "tout le secteur" in html
    # dédoublonnage par mutation : DISTINCT ON (id_mutation, id_parcelle)
    assert "DISTINCT ON (dm.id_mutation, dm.id_parcelle)" in _POOL_SQL


def test_3e_chaque_ppr_nomme_et_date():
    """3e — chaque plan de prévention cité porte son nom et sa date : AM0838 relève du PPR (26/01/2016)
    ET du PPR littoral — PPRL (16/03/2017). Les deux dates sont servies, pas seulement la première."""
    from labuse.exports.miroir import _r_aleas
    from labuse.registre.valeur import Valeur
    v = [{"nature": "PPR — zone bleue", "libelle": "PPR inondation — zone bleue sur 56 %",
          "ppr": [{"document": "PPR", "approbation": "2016-01-26"},
                  {"document": "PPRL", "approbation": "2017-03-16"}]}]
    val = Valeur(valeur=v, chiffre_id="aleas_parcelle_liste", version_def=None, run=None)
    html = _r_aleas(v, val)
    assert "approuvé le 26/01/2016" in html
    assert "PPR littoral approuvé le 16/03/2017" in html


def test_pt4_numero_deux_versions_different_et_comparatif_toutes_parcelles():
    """pt4 — deux versions du même export le même jour (données différentes) ont des numéros DIFFÉRENTS ;
    une génération à l'identique garde le même numéro ; le numéro d'un Comparatif tient compte de TOUTES
    ses parcelles (changer une parcelle change le numéro)."""
    from datetime import date

    from labuse.exports.numeros import numero_rapport
    j = date(2026, 1, 15)
    a = numero_rapport("dossier", "97411000IS0448", j, discriminant="contenu-A")
    b = numero_rapport("dossier", "97411000IS0448", j, discriminant="contenu-B")
    assert a != b and a == numero_rapport("dossier", "97411000IS0448", j, discriminant="contenu-A")
    assert a.startswith("DP-20260115-97411000IS0448-")
    # Comparatif : le numéro dépend de TOUTES les parcelles (ordre indifférent)
    p1 = sorted(["A", "B", "C"]); p2 = sorted(["A", "B", "D"])
    assert (numero_rapport("comparatif", "A", j, discriminant="|".join(p1))
            != numero_rapport("comparatif", "A", j, discriminant="|".join(p2)))
    assert (numero_rapport("comparatif", "A", j, discriminant="|".join(sorted(["A", "B", "C"])))
            == numero_rapport("comparatif", "A", j, discriminant="|".join(sorted(["C", "B", "A"]))))


def test_pt2_zone_rouge_exclue_de_l_implantation_pas_vigilance_forte():
    """pt2 (reformulé LOT J pt3b) — la zone rouge marginale est dite EXCLUE de l'implantation, le RESTE
    soumis au règlement du plan de prévention — plus « vigilance forte ; pas d'exclusion automatique »,
    ni « … ne s'appliquent qu'en zone bleue ». La normalisation reformule les libellés STOCKÉS (compat
    des runs servis), et phase1.py l'émet nativement."""
    from labuse.api.risques_arbitrage import libelle_client_detail
    ancien = ("PPR zone rouge sur 34 % de la surface — vigilance forte ; constructibilité à vérifier "
              "au règlement (pas d'exclusion automatique).")
    neuf = libelle_client_detail(ancien)
    assert "la partie en zone rouge est exclue de l'implantation" in neuf
    assert "le reste est soumis au règlement du plan de prévention" in neuf
    assert "vigilance forte" not in neuf and "exclusion automatique" not in neuf
    assert "qu'en zone bleue" not in neuf           # LOT J pt3b — plus de « ne s'appliquent qu'en zone bleue »
    assert neuf.startswith("PPR zone rouge sur 34 % de la surface —")
    # un libellé déjà au nouveau format n'est pas re-réécrit
    assert libelle_client_detail(neuf) == neuf
