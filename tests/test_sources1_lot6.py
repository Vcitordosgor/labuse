"""SOURCES-1 lot 6 — gardes : le foncier et les gens (DFI, recensement IRIS).

Épinglages des fiches de règle (regles/filiation_parcelle.py, regles/iris_quartier.py) +
invariants du circuit (catalogue, filtres, registre, vanne). Tests PURS (pas de réseau)."""
from __future__ import annotations


# ───────────────────────── DFI : IDU reconstruit + codes amont ─────────────────────────

def test_filiation_idu_reconstruit():
    """Calcul refait à la main sur une ligne réelle lue le 07/09/2026 :
    (97422, '000', 'BD1347') → 97422000BD1347 (14 caractères, format LABUSE)."""
    insee, prefixe, parcelle = "97422", "000", "BD1347"
    idu = f"{insee}{prefixe.zfill(3)}{parcelle}"
    assert idu == "97422000BD1347" and len(idu) == 14


def test_filiation_codes_amont_etiquetes():
    """PDP (passage au domaine public) et EDNC (issue du non-cadastré) sont des codes AMONT
    légitimes — étiquetés lisiblement, jamais traités comme des parcelles difformes."""
    idu_pdp = "97422000PDP"      # 11 caractères — fille au domaine public
    idu_ednc = "97423000EDNC"    # 12 caractères — mère non cadastrée
    codes = {"PDP": "passage au domaine public", "EDNC": "issue du non-cadastré"}
    assert codes.get(idu_pdp[8:]) == "passage au domaine public"
    assert codes.get(idu_ednc[8:]) == "issue du non-cadastré"


# ───────────────────────── IRIS : dérivées refaites à la main ─────────────────────────

def test_iris_derives_a_la_main():
    """Les dérivées de la fiche de règle, refaites indépendamment du moteur."""
    from labuse.ingestion.iris_rp import _derives
    r = {"log": 200.0, "logvac": 30.0, "rp": 150.0, "nper_rp": 405.0,
         "ach_tot": 140.0, "ach_1919": 10.0, "ach_1945": 10.0, "ach_1970": 30.0,
         "ach_1990": 20.0, "ach_2005": 40.0, "ach_2019": 30.0,
         "pop": 400.0, "pop_6074": 60.0, "pop_75p": 20.0,
         "rp_loc": 90.0, "rp_lochlmv": 45.0}
    d = _derives(r)
    assert d["vacance_pct"] == 15.0                      # 30/200
    assert d["part_bati_avant_1990_pct"] == 50.0         # (10+10+30+20)/140
    assert d["taille_menages"] == 2.7                    # 405/150
    assert d["part_60_plus_pct"] == 20.0                 # 80/400
    assert d["part_locataires_pct"] == 60.0 and d["part_hlm_pct"] == 30.0


def test_iris_derives_denominateurs_nuls():
    from labuse.ingestion.iris_rp import _derives
    d = _derives({"log": 0.0, "logvac": 0.0, "rp": None, "nper_rp": None,
                  "ach_tot": None, "pop": None})
    assert d["vacance_pct"] is None and d["taille_menages"] is None
    assert d["part_bati_avant_1990_pct"] is None and d["part_60_plus_pct"] is None


# ───────────────────────── circuit : catalogue, filtres, registre, vanne ─────────────────────────

def test_catalogue_lot6():
    from labuse.ingestion.seed_sources import SOURCES, verifier_catalogue
    noms = {r["name"] for r in SOURCES}
    assert "DFI — documents de filiation informatisés (DGFiP)" in noms
    assert "INSEE RP2022 — bases IRIS (logement, population)" in noms
    assert verifier_catalogue() == []


def test_filtres_lot6():
    from labuse.filtres.sources import FILTRES_RICHES
    assert "dfi" in FILTRES_RICHES and "iris_rp" in FILTRES_RICHES
    ids = {c.id for c in FILTRES_RICHES["dfi"].propres}
    assert {"d_dfi_idu_forme", "d_dfi_codes_amont", "d_dfi_auto_lien"} <= ids
    ids_iris = {c.id for c in FILTRES_RICHES["iris_rp"].propres}
    assert {"d_iris_contours", "d_iris_vacance_plage"} <= ids_iris


def test_vanne_lot6():
    from labuse import filtres
    labels = {e.get("label") for e in filtres.sources_a_job()}
    assert {"dfi", "iris_rp"} <= labels


def test_registre_lot6():
    from labuse.registre import ROBINETS
    from labuse.registre.couverture import FICHE_PARCELLE_CLES
    from labuse.registre.donnees import DONNEES
    for cid in ("filiation_parcelle", "iris_quartier", "iris_commune_quartiers"):
        assert cid in DONNEES, cid
        assert DONNEES[cid].en_attente is None
    assert "filiation" in FICHE_PARCELLE_CLES and "iris_quartier" in FICHE_PARCELLE_CLES
    servies = {c for r in ROBINETS.values() for c in r.chiffres}
    assert {"filiation_parcelle", "iris_quartier", "iris_commune_quartiers"} <= servies


def test_reservoirs_carte_lot6():
    import csv
    with open("docs/CIRCUIT/inventaire/reservoirs.csv") as f:
        ids = {r[0] for r in csv.reader(f, delimiter=";")}
    assert {"dgfip_dfi", "insee_rp_iris"} <= ids
    from labuse.registre.tables import RESERVOIR_TABLES
    assert RESERVOIR_TABLES["dgfip_dfi"].tables == ("dfi_filiation",)
    assert RESERVOIR_TABLES["insee_rp_iris"].tables == ("iris_rp",)


def test_fiches_de_regle_lot6():
    import labuse.regles as regles
    fiches = regles.charger()
    assert "filiation_parcelle" in fiches and "iris_quartier" in fiches
    assert "PDP" in fiches["filiation_parcelle"].formule_codee
    assert "NPER_RP/RP" in fiches["iris_quartier"].formule_codee
