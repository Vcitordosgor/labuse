"""CHIRURGICAL-FIX-1 — LOT K (4ᵉ contre-audit, 4 parcelles). Gardes déterministes, sans base.

Bilan honnête (terrain cadastre sans erreur avalée, garde-fou en tête PDF+Excel, TVA validée),
formulations (stationnement Estimer, sol, marge IS0448, zone humide AD0887, gardiennage AM0838,
couverture), CERFA « 18 ter », numéros Estimer/Comparatif par contenu, jour des ventes.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


# ── K2a — route Excel : terrain du cadastre, helper partagé, aucune erreur avalée ────────────
def test_k2a_terrain_sourcee_partage_sans_except_avale():
    b = (_SRC / "api" / "bilan.py").read_text()
    assert "def _terrain_sourcee(" in b
    # les DEUX routes utilisent le helper ; l'ancien try/except qui masquait le NameError a disparu.
    assert b.count("_terrain_sourcee(db, idu)") >= 2
    assert "# noqa: BLE001 — contenance non résolue" not in b


# ── K2b — garde-fou en tête du PDF ET de l'Excel ─────────────────────────────────────────────
def test_k2b_garde_fou_pdf_et_excel():
    from labuse.bilan.pdf import construire_html
    from labuse.bilan.excel import classeur_bilan
    from labuse.bilan.moteur import EntreesBilan, Moteur, Produit, Programme, SaisiePoste
    e = EntreesBilan(programme=Programme(terrain=20336, sdp=500, surface_taxable=500),
                     produits=[Produit("P", 7, 500.0, 4000.0, 0.085)],
                     postes={"achat": SaisiePoste(1000, "saisi", tva=0.0), "constr": SaisiePoste(2293, "saisi")})
    gf = {"alertes": ["Habitat interdit dans cette zone",
                      "La surface de plancher saisie (500 m²) dépasse la capacité estimée de la fiche "
                      "(0 m² avec le bâti conservé ; 85 m² en terrain libéré)."], "non_constructible": True}
    html, _ = construire_html(Moteur().calculer(e), idu="X", jour=date(2026, 11, 16), garde_fou=gf)
    assert "Programme saisi — non vérifié" in html and "Habitat interdit" in html and "dépasse la capacité" in html
    ws = classeur_bilan(e, None, "t", garde_fou=gf).active
    assert "non vérifié" in (ws["A2"].value or "") and "Habitat interdit" in (ws["A2"].value or "")


# ── K2d — TVA de vente hors [0,1] : formule « saisie invalide » + validation « entre 0 et 1 » ──
def test_k2d_tva_invalide_bloque():
    from labuse.bilan.excel import classeur_bilan
    from labuse.bilan.moteur import EntreesBilan, Produit, Programme, SaisiePoste
    ws = classeur_bilan(EntreesBilan(programme=Programme(terrain=1000),
                                     produits=[Produit("P", 1, 55.0, 4500.0, 0.085)], postes={}), None, "t").active
    ht = [c.value for row in ws.iter_rows() for c in row
          if isinstance(c.value, str) and "saisie invalide" in c.value]
    assert ht and all(">1" in f and "<0" in f for f in ht)
    dvs = list(ws.data_validations.dataValidation)
    assert any(d.operator == "between" and d.formula1 == "0" and d.formula2 == "1" for d in dvs)


# ── K3a — Estimer : stationnement Le Tampon = renvoi à l'article (comme le Dossier) ──────────
def test_k3a_estimer_stationnement_renvoi():
    from labuse.pige.api import _regles_zone
    for zc in ("Ud", "Uav"):
        r = {x["cle"]: x["valeur"] for x in _regles_zone(zc, "Le Tampon")}
        assert r["Stationnement"].startswith("barème selon le type de logement et la taille de l'opération")
        assert "1 place" not in r["Stationnement"]


# ── K3b — sol : « X % de LA PARCELLE … et Y % de LA PARCELLE … » (pas « dont ») ──────────────
def test_k3b_sol_deux_pourcentages_de_la_parcelle():
    from labuse.faisabilite.zonage import resolve_zone
    from labuse.plu_reglement import _regles_valeurs
    z = resolve_zone("Ud", "Le Tampon")
    v = {r["cle"]: r for r in _regles_valeurs(z, None, 0)}["pleine_terre"]["valeur"]
    assert v == "40 % de la parcelle en surface perméable et 30 % de la parcelle en pleine terre"
    assert "dont" not in v


# ── K3c — IS0448 : raison concrète (4,1 à l'égout, 4,5 / 7 réglementaires, différence de repère) ──
def test_k3c_marge_surelevation_chiffres():
    from labuse.exports.miroir import _raison_marge_surelevation
    from labuse.registre.valeur import Valeur
    fiche = {"commune": "Saint-Denis", "reglement_plu": {"zones": [{"zone": "Uh"}]}}
    valeurs = {"hauteur_egout_mesuree_m": Valeur(valeur=4.1, chiffre_id="hauteur_egout_mesuree_m",
                                                 version_def=None, run=None)}
    r = _raison_marge_surelevation(fiche, valeurs)
    assert r and "4,1 m" in r and "4,5 m" in r and "7 m" in r and "repère différent" in r


# ── K3d — AD0887 : le verdict §Risques NOMME la zone humide (pas « aucun rédhibitoire ») ─────
def test_k3d_zone_humide_nommee():
    from labuse.exports.miroir import _bandeau
    from labuse.registre.valeur import Valeur
    valeurs = {
        "aleas_parcelle_liste": Valeur(valeur=[{"nature": "Aléa mouvement_terrain", "redhibitoire": False}],
                                       chiffre_id="aleas_parcelle_liste", version_def=None, run=None),
        "contraintes_parcelle_liste": Valeur(
            valeur=[{"nature": "zone_humide", "libelle": "Zone humide inventoriée : La Grande Ferme (100 % de la parcelle)"}],
            chiffre_id="contraintes_parcelle_liste", version_def=None, run=None),
    }
    html = _bandeau("risques", valeurs)
    assert "Zone humide" in html and "100 %" in html and "aucun rédhibitoire" not in html


# ── K3e — AM0838/UE : l'exception « gardiennage, 50 m² » est nommée (pas « Logement » sec) ────
def test_k3e_exception_gardiennage():
    from labuse.plu.destinations import zone_resume
    sc = zone_resume("L'Étang-Salé", "UE").get("sous_conditions") or []
    log = next((s for s in sc if s.startswith("Logement")), "")
    assert "gardiennage" in log and "50 m²" in log


# ── K3f — couverture : risque principal + motif du « 0 m² » ──────────────────────────────────
def test_k3f_risque_principal_et_motif():
    from labuse.exports.miroir import _risque_principal_cover
    fiche = {"aleas": {"liste": [{"nature": "Aléa mouvement_terrain", "redhibitoire": False,
                                  "libelle": "Aléa mouvement de terrain — niveau faible sur 100 %"}]},
             "lines": [{"layer": "tri_zone", "result": "SOFT_FLAG",
                        "libelle": "Zone inondable TRI — scénario extreme (85 % de la parcelle)"}]}
    assert "inondable TRI" in (_risque_principal_cover(fiche, {}) or "")


# ── K3g — CERFA : numéro de voie + indice (bis/ter) ; numéros Estimer/Comparatif par contenu ──
def test_k3g_cerfa_numero_rep_et_numeros_contenu():
    pd = (_SRC / "api" / "pre_dossier.py").read_text()
    assert '"T2Q_numero": _num_voie' in pd and '(adresse or {}).get("rep")' in pd
    from labuse.exports import builder
    a = builder.construire_comparatif(["A", "B"], [{"idu": "A"}], jour=date(2026, 9, 5))
    b = builder.construire_comparatif(["A", "B"], [{"idu": "A"}], jour=date(2026, 9, 5),
                                      note_limite="3 non affichées : X")
    assert a.numero == builder.construire_comparatif(["A", "B"], [{"idu": "A"}], jour=date(2026, 9, 5)).numero
    assert a.numero != b.numero          # contenu rendu différent → numéro différent


# ── K3h — ventes comparables : la date porte le jour quand la source le porte ────────────────
def test_k3h_jour_dans_date_ventes():
    from labuse.pige.estimer3 import _jour_mois_annee
    assert _jour_mois_annee("2022-05-16") == "16/05/2022"
    assert _jour_mois_annee("05/2022") == "05/2022"   # terrain déjà sans jour : inchangé
