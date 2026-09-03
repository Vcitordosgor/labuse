"""DESTINATIONS-1 — X1 : référentiel R151-27/28, verdicts, silence, CDAC, états."""
from __future__ import annotations

import textwrap

import pytest

from labuse.plu import destinations as d


# ---------------------------------------------------------------------------
# Référentiel (version en vigueur 01/07/2023 — décret 2023-195)
# ---------------------------------------------------------------------------

def test_referentiel_5_destinations_23_sous_destinations():
    assert len(d.DESTINATIONS) == 5
    assert len(d.SOUS_DESTINATIONS) == 23
    # chaque sous-destination pointe vers une destination existante
    for slug, (parent, libelle) in d.SOUS_DESTINATIONS.items():
        assert parent in d.DESTINATIONS, slug
        assert libelle
    # les ajouts du décret 2023-195 sont bien là
    assert "lieux_culte" in d.SOUS_DESTINATIONS
    assert "cuisine_vente_en_ligne" in d.SOUS_DESTINATIONS
    assert "primaire" in d.DESTINATIONS["autres_activites"]


def test_sous_destination_inconnue_leve():
    with pytest.raises(ValueError):
        d.verdict("Saint-Denis", "UA", "piscine_geante")


# ---------------------------------------------------------------------------
# Fixture : une commune calibrée factice
# ---------------------------------------------------------------------------

_FIXTURE = textwrap.dedent("""
meta:
  insee: "97499"
  commune: "Testville"
  document: "97499_reglement_20250101.pdf"
  document_gpu: "97499_PLU_20250101"
  millesime: "2025-01-01"
  lu_le: "2026-09-03"
zones:
  UA:
    silence: autorise
    silence_src: "Art. UA1 : le règlement énumère les seules occupations interdites (p. 10)"
    sous_destinations:
      industrie: {statut: interdit, article: "UA1", page_pdf: 10,
                  citation: "les constructions à destination d'industrie sont interdites"}
      artisanat_commerce_detail: {statut: sous_condition, condition: "surface de vente limitée à 300 m²",
                                  seuil_m2: 300, seuil_type: surface_vente, article: "UA2", page_pdf: 11}
      logement: {statut: autorise, article: "UA2", page_pdf: 11}
  UE:
    silence: interdit
    silence_src: "Art. UE2 : seules sont admises les occupations énumérées (p. 40)"
    sous_destinations:
      artisanat_commerce_detail: {statut: autorise, article: "UE2", page_pdf: 41}
  1AUA:
    renvoi: UA
    renvoi_src: "caractère de zone 1AUa, p. 60 : « se reporter au règlement de la zone UA »"
""")


@pytest.fixture()
def commune_test(tmp_path, monkeypatch):
    dest = tmp_path / "plu_destinations"
    dest.mkdir()
    (dest / "97499_testville.yaml").write_text(_FIXTURE, encoding="utf-8")
    cfg = tmp_path / "plu_millesimes.yaml"
    cfg.write_text(textwrap.dedent("""
      communes:
        "97499": {commune: "Testville", idurba: "97499_PLU_20250101", statut: a_jour}
        "97498": {commune: "Rnuville", idurba: null, statut: rnu}
    """), encoding="utf-8")
    monkeypatch.setattr(d, "_DEST_DIR", dest)
    monkeypatch.setattr(d, "_CONFIG_DIR", tmp_path)
    d._load_yaml.cache_clear()
    yield
    d._load_yaml.cache_clear()


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

def test_verdict_interdit_cite_article_et_page(commune_test):
    v = d.verdict("Testville", "UA", "industrie")
    assert v["statut"] == "interdit" and v["statut_effectif"] == "interdit"
    assert v["article"] == "UA1" and v["page_pdf"] == 10
    assert v["millesime"] == "2025-01-01"
    assert "interdit" in v["phrase"] and "UA1" in v["phrase"]


def test_verdict_sous_condition_seuil_sans_cdac(commune_test):
    v = d.verdict("Testville", "UA", "artisanat_commerce_detail")
    assert v["statut"] == "sous_condition"
    assert v["seuil_m2"] == 300
    assert v["cdac"] is None          # 300 <= 1000 : pas de mention CDAC
    assert "300" in v["phrase"]


def test_verdict_autorise_sans_seuil_porte_cdac(commune_test):
    # UE : commerce de détail autorisé SANS plafond → la CDAC (L752-1) est dite.
    v = d.verdict("Testville", "UE", "artisanat_commerce_detail")
    assert v["statut_effectif"] == "autorise"
    assert v["cdac"] and v["cdac"]["seuil_m2"] == 1000
    assert "CDAC" in v["phrase"]


def test_silence_zone_autorise(commune_test):
    # UA non mentionné + silence=autorise → effectif autorisé, la règle de silence est citée
    v = d.verdict("Testville", "UA", "restauration")
    assert v["statut"] == "non_mentionne"
    assert v["statut_effectif"] == "autorise"
    assert "Art. UA1" in (v["silence"] or {}).get("source", "")


def test_silence_zone_interdit(commune_test):
    v = d.verdict("Testville", "UE", "industrie")
    assert v["statut"] == "non_mentionne"
    assert v["statut_effectif"] == "interdit"


def test_renvoi_de_zone_suit_le_reglement(commune_test):
    v = d.verdict("Testville", "1AUA", "industrie")
    assert v["statut_effectif"] == "interdit"
    assert "se reporter" in v.get("via_renvoi", "") or "règles de" in v.get("via_renvoi", "")


def test_zone_non_lue(commune_test):
    v = d.verdict("Testville", "N", "logement")
    assert v["statut"] == "non_lu"
    assert "calibration en cours" in v["phrase"]


def test_commune_non_calibree(commune_test):
    v = d.verdict("Saint-Nulle-Part", "UA", "logement")
    assert v["etat_calibration"] == "non_calibree"
    assert v["phrase"] == "destination non calibrée sur cette commune"


def test_zone_destinations_table_complete(commune_test):
    t = d.zone_destinations("Testville", "UA")
    assert len(t["lignes"]) == 23
    assert t["etat_calibration"] == "calibree"


# ---------------------------------------------------------------------------
# États (X5.2 / X5.3)
# ---------------------------------------------------------------------------

def test_etat_calibree_puis_a_relire(commune_test, tmp_path):
    assert d.etat_commune("Testville")["etat"] == "calibree"
    # une nouvelle version de PLU apparaît au catalogue → « à relire »
    (tmp_path / "plu_millesimes.yaml").write_text(textwrap.dedent("""
      communes:
        "97499": {commune: "Testville", idurba: "97499_PLU_20260601", statut: a_jour}
    """), encoding="utf-8")
    d._load_yaml.cache_clear()
    assert d.etat_commune("Testville")["etat"] == "a_relire"


def test_etats_ile_couvre_le_catalogue(commune_test):
    etats = d.etats_ile()
    assert {e["insee"] for e in etats} == {"97498", "97499"}
    par_insee = {e["insee"]: e for e in etats}
    assert par_insee["97499"]["etat"] == "calibree"
    assert par_insee["97498"]["etat"] == "non_calibree"   # rnu.yaml absent → non calibrée


def test_lookup_par_insee(commune_test):
    assert d.etat_commune("97499")["etat"] == "calibree"


# ---------------------------------------------------------------------------
# X4 — les surfaces lisent le MÊME moteur
# ---------------------------------------------------------------------------

def test_verdicts_zones_etude_chalandise(commune_test):
    # X4.1 — verdict par zone PLU recouverte + états « en cours de calibration »
    zones = [{"zone": "UA", "commune": "Testville", "part_pct": 70},
             {"zone": "N", "commune": "Testville", "part_pct": 20},
             {"zone": "UA", "commune": "Saint-Nulle-Part", "part_pct": 10}]
    out = d.verdicts_zones_etude(zones, "artisanat_commerce_detail")
    etats = {(z["zone"], z["commune"]): z["etat"] for z in out["zones"]}
    assert etats[("UA", "Testville")] == "sous_condition"
    assert etats[("N", "Testville")] == "en_cours_de_calibration"      # zone non lue
    assert etats[("UA", "Saint-Nulle-Part")] == "en_cours_de_calibration"  # commune non calibrée
    with pytest.raises(ValueError):
        d.verdicts_zones_etude(zones, "hammam_geant")


def test_zone_resume_fiche(commune_test):
    # X4.2 — la ligne « Destinations » de la fiche : groupes + seuil commerce + dépliable
    r = d.zone_resume("Testville", "UA")
    assert r["etat_calibration"] == "calibree"
    assert "Industrie" in r["interdites"]
    assert any("300" in (s or "") for s in [str(r["seuil_commerce_m2"])])
    assert len(r["lignes"]) == 23
    assert d.zone_resume("Saint-Nulle-Part", "UA")["phrase"] == \
        "destination non calibrée sur cette commune"


def test_resoudre_sous_destination():
    # X4.4 — Copilote : « restaurant » → restauration, jamais un slug deviné
    assert d.resoudre_sous_destination("restaurant") == "restauration"
    assert d.resoudre_sous_destination("Hôtel") == "hotels"
    assert d.resoudre_sous_destination("commerce") == "artisanat_commerce_detail"
    assert d.resoudre_sous_destination("Cinéma") == "cinema"
    assert d.resoudre_sous_destination("logement") == "logement"
    assert d.resoudre_sous_destination("téléporteur quantique") is None


def test_referentiel_servi():
    ref = d.referentiel()
    assert len(ref["destinations"]) == 5 and len(ref["sous_destinations"]) == 23


def test_scot_daac_verdicts_reels():
    # X3.2 — fichier réel : 24 communes, trois verdicts possibles, secteurs cités par page
    s = d.scot_daac("Saint-Pierre")
    assert s["verdict"] == "oui" and len(s["secteurs"]) == 4
    assert all(sec.get("page_pdf") for sec in s["secteurs"])
    assert d.scot_daac("Cilaos")["verdict"] == "non"           # DAAC en vigueur, commune sans ZPLC
    assert d.scot_daac("Saint-Denis")["verdict"] == "non_localise"   # CINOR : DAACL en projet
    assert d.scot_daac("97415")["verdict"] == "non_localise"         # TCO : pas de DAAC


# ---------------------------------------------------------------------------
# X5.1 — module UNIQUE : aucune autre lecture du dossier de calibration
# ---------------------------------------------------------------------------

def test_module_unique_aucune_autre_lecture():
    """Le dossier config/plu_destinations n'est référencé QUE par plu/destinations.py
    (les surfaces passent par le module, jamais par les YAML)."""
    import subprocess
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src"
    out = subprocess.run(["grep", "-rl", "plu_destinations", str(src)],
                         capture_output=True, text=True).stdout.split()
    offenders = [p for p in out
                 if Path(p).name != "destinations.py" and "__pycache__" not in p]
    assert not offenders, f"lectures hors module unique : {offenders}"
