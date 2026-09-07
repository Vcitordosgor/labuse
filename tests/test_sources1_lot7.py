"""SOURCES-1 lot 7 — gardes : le catalogue mis d'équerre.

BDNB retirée de la vitrine (veille conservée), sept chantiers nommés « en attente de
demande », les trois lignes Cerema sous convention, la demande Région/EPCI committée."""
from __future__ import annotations

CHANTIERS = (
    "Zonages d'assainissement SIG complets (EPCI / régies)",
    "Inventaires ZAE (EPCI — loi Climat et résilience)",
    "Périmètres de ZAC (EPCI / communes / EPF Réunion)",
    "OPAH / PIG (Anah / EPCI)",
    "Périmètres ORT infra-communaux (EPCI)",
    "ENS du Département (Conseil départemental)",
    "Micro-données OLL (ADIL / AGORAH)",
)
CEREMA = ("Fichiers fonciers (Cerema)", "LOVAC (logements vacants)", "DV3F (Cerema)")


def test_bdnb_retiree_avec_raison_et_veille():
    from labuse.ingestion.seed_sources import RETRAITS
    assert "BDNB" in RETRAITS
    assert "ne couvre pas le 974" in RETRAITS["BDNB"]
    # la veille amont RESTE : la sonde data.gouv du SEED survit au retrait
    from labuse import sentinelle
    assert any(e["name"] == "BDNB" for e in sentinelle.SEED)


def test_chantiers_au_catalogue_avec_organisme():
    from labuse.ingestion.seed_sources import MODE_ET_CADENCE, SOURCES
    par_nom = {r["name"]: r for r in SOURCES}
    for nom in CHANTIERS:
        r = par_nom[nom]
        assert r["status"].value == "a_faire", nom          # pas d'enum « chantier » — décision lot 7
        assert "CHANTIER" in r["technical_notes"], nom      # l'organisme à solliciter est en tête
        assert "en attente de la demande" in r["source_millesime"], nom
        assert MODE_ET_CADENCE[nom][0] == "absente", nom


def test_cerema_sous_convention():
    from labuse.ingestion.seed_sources import SOURCES
    par_nom = {r["name"]: r for r in SOURCES}
    for nom in CEREMA:
        r = par_nom[nom]
        assert r["status"].value == "manuel", nom           # pas d'enum « sous_convention » — décision
        assert "SOUS CONVENTION" in r["technical_notes"], nom
    assert "réservé" in par_nom["LOVAC (logements vacants)"]["legal_notes"].lower()


def test_demande_region_epci_committee():
    texte = open("docs/CIRCUIT/DEMANDE-REGION-EPCI.md", encoding="utf-8").read()
    for destinataire in ("Région Réunion", "CINOR", "Conseil départemental", "AGORAH",
                         "DEAL Réunion", "DPU non publié"):
        assert destinataire in texte, destinataire
    # les listes mesurées par les lots précédents sont réutilisées, pas réinventées
    assert "Salazie" in texte and "SAR 2050" in texte and "DPE" in texte


def test_pont_et_carte_lot7():
    import csv
    from labuse.circuit_etats import NOM_VERS_SLUG
    from labuse.registre.tables import RESERVOIR_TABLES
    slugs = ("assainissement_sig_epci", "zae_epci", "zac_perimetres", "opah_pig",
             "ort_perimetres_epci", "ens_departement", "oll_microdonnees", "dv3f")
    for s in slugs:
        assert s in RESERVOIR_TABLES, s
        assert not RESERVOIR_TABLES[s].tables, s            # rien de remis = aucune table
    for nom in CHANTIERS + ("DV3F (Cerema)",):
        assert nom in NOM_VERS_SLUG, nom
    with open("docs/CIRCUIT/inventaire/reservoirs.csv") as f:
        ids = {r[0] for r in csv.reader(f, delimiter=";")}
    for s in slugs:
        assert s in ids, s
