"""EXPORTS-2 lot 2 — le Dossier (= Flash sans §9). Mécanique sans base (db factice + fiche
fixture) :
  · les 10 sections branchées sur les ids ; une donnée absente → ligne/section OMISE (aucun ◌) ;
  · verdict de zonage déterministe ; jamais un faux constructible (cause → pas de scénario) ;
  · §7 sert la maille RÉELLE (quartier IRIS) avec son mode dans le titre ;
  · §9 = encart « renseignez » ; ABSENT du Flash ; Flash = Dossier − §9 ;
  · aucun mot interdit ; références nettoyées (« page corrigée » jamais imprimé).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from labuse.exports import builder

MOTS = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "mots_interdits.yaml").read_text())["mots"]


class _FakeDB:
    def execute(self, *a, **k):
        raise RuntimeError("pas de base en test unitaire")


#: une fiche fixture représentative (les clés réelles du payload /parcels/{idu}).
FICHE = {
    "surface_m2": 742, "adresse": "103 Chaussée Royale, 97460 Saint-Paul", "commune": "Saint-Paul",
    "proprietaire_moral": {"denomination": "MCA3", "siren": "824160717"},
    "terrain": {"pente_moy_deg": 1.3},
    "reglement_plu": {"zones": [{
        "zone": "U1a", "idurba": "97415_PLU_20251217",
        "regles_valeurs": [
            {"cle": "hauteur", "libelle": "Hauteur max", "valeur": "16 m au faîtage · 12 m à l'égout",
             "etat": "chiffre", "reference": "Zone U1a, Art. 10.2, p.20-21"},
            {"cle": "pleine_terre", "libelle": "Pleine terre min", "valeur": "10 %", "etat": "chiffre",
             "reference": "Art. 13.1, p.30-31 (page corrigée à la consolidation)"},  # note interne à nettoyer
        ],
        "destinations": {"autorisees": ["Hébergement", "Bureau"], "interdites": ["Entrepôt"],
                         "sous_conditions": ["Logement"], "commerce_cdac": {"seuil_m2": 1000}},
    }]},
    "prescriptions_verifiables": True,
    "dispositifs": {"er": None, "ebc": None, "dpu": {"etat": "servi", "statut": "simple", "libelle": "DPU CENTRE"},
                    "peb": {"zone": "hors"}, "sup": []},
    "le_bien": {"emprise_batie_m2": 540, "hauteur_bati_m": 9.4, "nb_batiments": 2, "surface_libre_m2": 202},
    "potentiel_transformation": {"libelle": "Densité autorisée atteinte", "niveau": "nul",
                                 "pct_consomme": 204, "sdp_residuelle_m2": 0.0, "hauteur_base": "égout",
                                 "hauteur_marge_m": 2.6, "hauteur_regle_m": 12.0, "hauteur_bati_m": 9.4,
                                 "surelevation_possible": False, "capacite_estimee": False, "cause": None},
    "aleas": {"n": 1, "liste": [{"nature": "Inondation", "niveau": "moyen",
                                 "libelle": "Zone bleue PPR inondation — sous prescriptions.", "redhibitoire": False}]},
    "prix_ancien": {"median": 3811, "n": 24, "n_exclus": 3, "radius_m": 500, "min": 1569, "max": 10135,
                    "tendance": "hausse", "tendance_pct": 16, "type_prix": "appartement", "periode": [2022, 2025],
                    "prix_points": [1569, 3067, 3811, 4746, 10135]},
    "mode_b": {"terrain_nu": {"prix_m2": 768, "valeur_eur": 569831, "surface_m2": 742,
                             "libelle": "terrain nu — secteur"}},
    "dvf_parcelle": {"secteur": [{"type_bien": "appartement", "n_ventes": 36, "mediane_prix_m2": 3804,
                                  "fenetre": "2021-2025"}], "derniere_mutation": None},
    "depots": {"secteur": {"count": 20}},
    "viabilisation": {"libelle": "Viabilisation confirmée par les faits", "band": "confirmee",
                      "contributions": [{"libelle": "Permis accordés à proximité", "signe": "+"}],
                      "solaire": {"prod_kwh_kwc": 1277}},
    "proximites": {"arret": {"nom": "Rue du Commerce", "reseau": "Kar'Ouest", "distance_m": 143},
                   "pole": {"nom": "Gare", "distance_m": 205}, "axe": {"nom": "N1", "distance_m": 123}},
    "anc": {"statut": "source", "libelle": "Tout-à-l'égout (collectif)"},
    "iris_quartier": {"nom": "Mairie-Hôpital", "habitants": 2226, "menages": 990, "logements": 1161,
                      "vacance_pct": 13.2, "part_60_plus_pct": 28.2, "part_locataires_pct": 45.8},
    "proximites_equipements": {"items": [{"cat": "École", "nom": "X", "distance_m": 126},
                                         {"cat": "Commerces", "nom": "SUPER U", "distance_m": 54}]},
    "territoire_fiscal": {"commune": "Saint-Paul",
                          "dispositifs_dom": [{"libelle": "Zonage d'investissement locatif : B1"}],
                          "zfang": {"libelle": "Régime standard (art. 44 quaterdecies CGI)"},
                          "frr": {"libelle": "Commune classée en partie"},
                          "perimetres": [{"libelle": "Bande QPV — TVA réduite accession"}]},
    "taxe_amenagement": {"assiette_m2": 794, "total_eur": None, "taux_communal_manquant": True,
                         "part_departementale_eur": 17706.2, "taux_departemental_pct": 2.5},
    "marche_secteur": {"rpls_commune": {"nb_logements": 7265}},
    "plu_fraicheur": {"libelle": "PLU approuvé le 17/12/2025", "statut": "a_jour"},
    "data_sources": [{"nom": "Cadastre", "fournisseur": "DGFiP/IGN", "millesime": "2026-07", "categorie": "socle"}],
    "coproprietes": [],
}


def _dossier(fiche=FICHE):
    return builder.construire(_FakeDB(), "97415000BO0852", "dossier", fiche=fiche, jour=date(2026, 9, 5))


def test_dix_sections_et_aucun_ocro():
    html = _dossier().html
    for s in range(1, 11):
        assert f">{s}. " in html, f"section {s} absente"
    assert "◌" not in html


def test_aucun_mot_interdit_et_reference_nettoyee():
    html = _dossier().html
    assert [m for m in MOTS if m in html] == []
    assert "page corrigée" not in html           # note interne de la référence nettoyée
    assert "16 m au faîtage" in html             # la règle utile reste


def test_verdict_zonage_et_contenu():
    html = _dossier().html
    # RECETTE-7 (E3) — le code de zone RÉEL (U1a) s'affiche, avec sa famille, pour coller aux
    # articles cités (plus de « Zone U » tronqué à côté d'un règlement « U1a »).
    assert "Zone U1a (famille U) — urbaine, constructible" in html
    assert "Interdites" in html and "CDAC" in html
    assert 'class="cloud"' in html               # nuage des ventes
    assert "maille IRIS" in html                 # §7 mode réel dans le titre


def test_flash_est_dossier_moins_neuf():
    d = _dossier().html
    f = builder.construire(_FakeDB(), "97415000BO0852", "flash", fiche=FICHE, jour=date(2026, 9, 5)).html
    assert "Renseignez votre opération" in d          # §9 dans le Dossier
    assert "Renseignez votre opération" not in f      # absent du Flash
    assert "10. Sources" in f                          # le reste est là
    assert "Rapport Flash" in f


def test_faux_constructible_jamais(zone="N"):
    fiche = dict(FICHE)
    fiche["reglement_plu"] = {"zones": [{"zone": "N", "regles_valeurs": [], "destinations": {}}]}
    fiche["potentiel_transformation"] = dict(FICHE["potentiel_transformation"],
                                             cause="zone_non_constructible", libelle="Fort potentiel sous-densité")
    html = builder.construire(_FakeDB(), "IDU", "dossier", fiche=fiche, jour=date(2026, 9, 5)).html
    assert "Terrain non constructible (zone N)" in html
    assert "Fort potentiel" not in html               # le libellé brut ne fuit pas
    assert "Reconstruction après démolition" not in html   # aucun scénario sous cause


def test_omission_quand_donnee_absente():
    # fiche quasi vide → seules les sections servies apparaissent, aucun ◌, aucun « non chiffré »
    html = builder.construire(_FakeDB(), "IDU", "dossier",
                              fiche={"surface_m2": 500, "commune": "X"}, jour=date(2026, 9, 5)).html
    assert "◌" not in html and "non chiffré" not in html
    assert "1. Identité et situation" in html          # surface servie
    assert "2. Zonage" not in html                     # pas de règlement → section omise


def test_archive_reproductible(tmp_path):
    from labuse.exports import archive
    res = _dossier()
    payload = archive.payload_archive("dossier", "97415000BO0852", res.numero, res.valeurs, "2026-09-05")
    assert payload["numero_rapport"] == "DP-20260905-0852"
    assert "surface_parcelle_m2" in payload["valeurs"]
    pdf = tmp_path / "d.pdf"
    pdf.write_bytes(b"%PDF fake")
    assert archive.lire_archive(archive.ecrire_archive(pdf, payload)) == payload
