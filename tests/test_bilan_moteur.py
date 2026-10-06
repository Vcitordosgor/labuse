"""BILAN-1 Lot 2 — le moteur du bilan promoteur.

Non-régression : on recalcule le bilan de la promotrice avec SES propres valeurs
saisies et on exige les mêmes totaux que son Excel. Toutes les lignes tombent au
centime SAUF deux conventions d'assiette qu'elle a composées à la main (assurances
D.O / C.N.R et TRC : base « total (2) + étude de sol − imprévus »), que la maquette
validée a simplifiées en « total (2) ». Ces deux écarts sont ÉNUMÉRÉS et expliqués,
et on vérifie qu'ils expliquent la totalité de l'écart de résultat (résidu nul).
"""

from __future__ import annotations

import io
import pathlib
import re
import zipfile

import pytest

from labuse.bilan.moteur import (
    EntreesBilan,
    Moteur,
    Produit,
    Programme,
    SaisiePoste,
    SANS_OBJET,
    SAISI,
)

_RACINE = pathlib.Path(__file__).resolve().parents[1]
_XLSX = _RACINE / "docs" / "audit-2026-10" / "bilan-1" / "modele-promotrice.xlsx"

besoin_modele = pytest.mark.skipif(
    not _XLSX.exists(), reason="modèle de la promotrice absent (gitignoré)"
)


def charger_feuille_bilan(data_only: bool):
    """Feuille BILAN, `definedNames` cassés (#N/A) neutralisés en mémoire."""
    openpyxl = pytest.importorskip("openpyxl")
    brut = _XLSX.read_bytes()
    tampon = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(brut)) as zin, zipfile.ZipFile(
        tampon, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.namelist():
            data = zin.read(item)
            if item == "xl/workbook.xml":
                txt = re.sub(
                    r"<definedNames>.*?</definedNames>",
                    "",
                    data.decode("utf-8"),
                    flags=re.S,
                )
                data = txt.encode("utf-8")
            zout.writestr(item, data)
    tampon.seek(0)
    return openpyxl.load_workbook(tampon, data_only=data_only)["BILAN"]


def entrees_temoin_promotrice() -> EntreesBilan:
    """Les valeurs réellement saisies par la promotrice dans son modèle témoin."""
    S = SaisiePoste
    postes = {
        # Charge foncière
        "achat": S(1000, SAISI, tva=0.0),  # 1 000 €/m², terrain nu TVA 0
        "apport": S(3, SAISI),  # 3 % (commission TTC, base ttc)
        "notT": S(1.5, SAISI, tva=0.06),
        "notP": S(1.5, SAISI, tva=0.06, assiette_valeur=800000),
        "txLog": S(22.3, SAISI),
        "txPkg": S(11.15, SAISI),
        "tre": S(20.8, SAISI),
        "archeo": S(3, SAISI),
        "topo": S(3500, SAISI),
        "born": S(2000, SAISI),
        "sol": S(12500, SAISI),
        "hydro": S(4500, SAISI),
        "affPC": S(900, SAISI),
        "branch": S(900, SAISI),
        "edf": S(100000, SAISI),
        "amiante": S(2000, SAISI),
        "demol": S(100000, SAISI),
        "aleaT": S(0, SAISI),
        # Construction & honoraires
        "constr": S(5870000 / 2560, SAISI),  # 5 870 000 € pour 2 560 m² SUV
        "deco": S(30000, SAISI),
        "archi": S(2, SAISI),
        "pays": S(0.2, SAISI),
        "moe": S(3.8, SAISI),
        "opc": S(0.6, SAISI),
        "labels": S(28000, SAISI),
        "sps": S(0.26, SAISI),
        "ctrl": S(0.86, SAISI),
        "aleaC": S(90000 / 5870000 * 100, SAISI),  # 90 000 € forfait exprimé en %
        # Gestion
        "pub": S(0.2, SAISI),
        "jur": S(0.04, SAISI),
        "cvae": S(0.26, SAISI, assiette_valeur=848970),
        "mod": S(5, SAISI),
        "gfa": S(1, SAISI),
        "gp": S(0, SAISI),
        "ff": S(0.5, SAISI),
        "do": S(1.32, SAISI),
        "trc": S(0.34, SAISI),
        "aleaG": S(0, SAISI),
        # Commercialisation
        "com1": S(10, SAISI),
        "com2": S(10, SAISI),
        "acte": S(etat=SANS_OBJET),
        "pack": S(etat=SANS_OBJET),
        "proc": S(etat=SANS_OBJET),
        "gpl": S(etat=SANS_OBJET),
        "aleaV": S(0, SAISI),
    }
    return EntreesBilan(
        programme=Programme(terrain=1746, surface_taxable=2500),
        produits=[
            Produit("Produit 1", 26, 1372, 6664000 / 1372, 0.021),
            Produit("Produit 2", 20, 1188, 5742000 / 1188, 0.021),
        ],
        postes=postes,
    )


# ---------------------------------------------------------------------------
# Mécanique du moteur (sans le modèle)
# ---------------------------------------------------------------------------
def test_bilan_vide_ne_calcule_rien():
    """Doctrine 3 : aucune marge tant qu'un poste est à renseigner."""
    e = EntreesBilan(
        programme=Programme(terrain=1000),
        produits=[Produit("Libre", 10, 800, 5000, 0.085)],
    )
    r = Moteur().calculer(e)
    assert not r.complet
    assert r.resultat_net is None and r.marge_pct is None
    assert r.manquants  # des postes restent à renseigner


def test_ht_tva_ttc_coherents_et_sans_objet():
    e = EntreesBilan(
        programme=Programme(terrain=1000, surface_taxable=800),
        produits=[Produit("Libre", 10, 800, 5000, 0.085)],
        postes={"topo": SaisiePoste(1000, SAISI)},
    )
    r = Moteur().calculer(e)
    topo = next(ln for ln in r.lignes if ln.id == "topo")
    assert topo.ht == pytest.approx(1000)
    assert topo.tva == pytest.approx(85.0)  # 8,5 % sourcé
    assert topo.ttc == pytest.approx(1085.0)
    # Sans objet => 0, jamais « à renseigner »
    e.postes["edf"] = SaisiePoste(etat=SANS_OBJET)
    r2 = Moteur().calculer(e)
    edf = next(ln for ln in r2.lignes if ln.id == "edf")
    assert edf.ht == 0 and edf.tva == 0 and not edf.manquant


def test_apport_est_en_base_ttc():
    """La commission d'apport (3 %) est toutes taxes, ramenée HT."""
    e = EntreesBilan(
        programme=Programme(terrain=1746),
        produits=[Produit("Libre", 46, 2560, 4800, 0.085)],
        postes={"achat": SaisiePoste(1000, SAISI, tva=0.0), "apport": SaisiePoste(3, SAISI)},
    )
    r = Moteur().calculer(e)
    apport = next(ln for ln in r.lignes if ln.id == "apport")
    assert apport.ttc == pytest.approx(1746000 * 0.03)  # 3 % du prix = TTC
    assert apport.ht == pytest.approx(1746000 * 0.03 / 1.085)


# ---------------------------------------------------------------------------
# Non-régression contre le modèle de la promotrice
# ---------------------------------------------------------------------------
@besoin_modele
def test_non_regression_lignes_au_centime():
    ws = charger_feuille_bilan(data_only=True)

    def cell(r, c):
        v = ws.cell(r, c).value
        return 0.0 if v in (None, "") else float(v)

    m = Moteur()
    r = m.calculer(entrees_temoin_promotrice())
    assert r.complet, r.manquants

    # TOUTES les lignes au centime — assiettes D.O/TRC recopiées à l'identique.
    for ln in r.lignes:
        row = m.cat.poste(ln.id).ligne_modele
        eX, fX, gX = cell(row, 5), cell(row, 6), cell(row, 7)
        assert (ln.ht or 0) == pytest.approx(eX, abs=1.0), f"{ln.id} HT"
        assert (ln.tva or 0) == pytest.approx(fX, abs=1.0), f"{ln.id} TVA"
        assert (ln.ttc or 0) == pytest.approx(gX, abs=1.0), f"{ln.id} TTC"


@besoin_modele
def test_non_regression_totaux_et_residu_nul():
    ws = charger_feuille_bilan(data_only=True)

    def cell(r, c):
        v = ws.cell(r, c).value
        return 0.0 if v in (None, "") else float(v)

    m = Moteur()
    r = m.calculer(entrees_temoin_promotrice())

    # CA : exact
    assert r.ca_ht == pytest.approx(cell(115, 5), abs=1.0)
    assert r.ca_ttc == pytest.approx(cell(115, 7), abs=1.0)

    # Tous les totaux de bloc exacts (DO/TRC recopiées → bloc G exact aussi)
    htsX = {"T": cell(62, 5), "C": cell(77, 5), "G": cell(92, 5), "V": cell(106, 5)}
    hts = {b.id: b.ht for b in r.blocs}
    for bid, vx in htsX.items():
        assert hts[bid] == pytest.approx(vx, abs=1.0), f"bloc {bid}"

    # Résultat net : IDENTIQUE au modèle, 0 € d'écart.
    assert r.resultat_net == pytest.approx(cell(119, 5), abs=1.0)


@besoin_modele
def test_prix_max_terrain_est_l_inverse_de_la_marge():
    """Les deux sens sur le même écran : au prix saisi -> marge ; à la marge
    saisie -> prix max. L'un doit être l'inverse exact de l'autre."""
    m = Moteur()
    base = m.calculer(entrees_temoin_promotrice())
    marge = base.marge_pct * 100.0

    e = entrees_temoin_promotrice()
    e.mode = "prix"
    e.marge_cible = marge
    r = m.calculer(e)
    # prix max du terrain = le prix d'achat saisi (1 000 €/m² × 1 746 m²)
    assert r.prix_max_terrain == pytest.approx(1746000, abs=1.0)
    assert r.prix_max_terrain_m2 == pytest.approx(1000, abs=0.01)
