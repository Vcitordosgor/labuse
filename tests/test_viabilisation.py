"""M-VIA — tests de l'indicateur de viabilisation. Purs (sans DB) sauf le mapping YAML."""
import re
from pathlib import Path

from labuse.faisabilite import viabilisation as V


def _sig(**kw):
    base = dict(zone_fam=None, c100=0, c200=0, c100_recent=0, c100_acheve=0,
                voie10=False, voie75=False, bati10=False, bati30=False, bati75=False)
    base.update(kw)
    return base


def test_poids_somment_a_100():
    assert V.W_PERMIS + V.W_FACADE + V.W_BATI + V.W_ZONE == 100


def test_parcelle_urbaine_confirmee():
    s = _sig(zone_fam="U", c100=8, c200=20, c100_recent=4, c100_acheve=3,
             voie10=True, voie75=True, bati10=True, bati30=True, bati75=True)
    assert V.compute_score(s) == 100
    assert V.band(100) == ("confirmee", "Viabilisation confirmée par les faits")


def test_parcelle_enclavee_lourde():
    s = _sig(zone_fam="N")  # rien : ni permis, ni voie, ni bâti
    assert V.compute_score(s) == 0
    code, lib = V.band(0)
    assert code == "lourde" and "lourde" in lib.lower()


def test_seuils_de_bande():
    assert V.band(70)[0] == "confirmee"
    assert V.band(69)[0] == "probable"
    assert V.band(45)[0] == "probable"
    assert V.band(44)[0] == "incertaine"
    assert V.band(25)[0] == "incertaine"
    assert V.band(24)[0] == "lourde"


def test_permis_le_signal_le_plus_fort():
    """6 permis < 100 m pèsent plus que la zone seule."""
    permis = V.compute_score(_sig(c100=6))
    zone = V.compute_score(_sig(zone_fam="U"))
    assert permis > zone == V.W_ZONE
    assert permis == V.W_PERMIS


def test_facade_urbanisee_exige_bati_riverain():
    """Voie au contact SANS bâti riverain ≠ façade urbanisée (BD TOPO inclut les chemins)."""
    voie_seule = V.compute_score(_sig(voie10=True))
    voie_urbanisee = V.compute_score(_sig(voie10=True, bati30=True))
    assert voie_seule == 8
    assert voie_urbanisee > voie_seule


def test_monotonie_permis():
    prev = -1
    for c in (0, 1, 3, 6, 12):
        sc = V.compute_score(_sig(c100=c))
        assert sc >= prev
        prev = sc


def test_contributions_tracent_le_pourquoi():
    s = _sig(zone_fam="U", c100=6, c100_recent=2, c100_acheve=1, voie10=True, bati10=True, bati30=True)
    contribs = V.contributions(s)
    top = contribs[0]
    assert top["libelle"] == "Permis accordés à proximité" and top["points"] == V.W_PERMIS
    assert "6 permis" in top["detail"] and "2 depuis 2022" in top["detail"]
    # trié par poids décroissant
    assert [c["points"] for c in contribs] == sorted((c["points"] for c in contribs), reverse=True)


def test_cout_raccordement_qualitatif_jamais_en_euros():
    for band_code in ("confirmee", "probable", "incertaine", "lourde"):
        c = V.cout_raccordement(_sig(), band_code)
        blob = " ".join(c.values())
        assert "€" not in blob and not re.search(r"\d+\s*(eur|euro)", blob.lower())
    # ANC → mention filière autonome
    anc = V.cout_raccordement(_sig(assainissement_zonage="anc"), "lourde")
    assert "autonome" in anc["assainissement"].lower()


def test_indicateur_porte_disclaimer_et_est_un_indicateur():
    ind = V.build_indicateur(_sig(zone_fam="U", c100=6))
    assert "indicateur" in ind["disclaimer"].lower() or "probabilité" in ind["disclaimer"].lower()
    assert "certitude" in ind["disclaimer"].lower()  # jamais un verrou


def test_elec_pv_note_ilot_injectee():
    ilot = {"statut": "saturee", "note": "test", "disclaimer": "x"}
    ind = V.build_indicateur(_sig(zone_fam="U"), elec_pv=ilot)
    assert ind["elec_pv"] == ilot
    # sans note d'îlot → pas de clé elec_pv fabriquée
    assert "elec_pv" not in V.build_indicateur(_sig(zone_fam="U"))


def test_mapping_gestionnaires_couvre_les_24_communes():
    g = V.resolve_gestionnaires("Saint-Paul")
    assert g and g["epci"]["code"] == "TCO"
    assert g["electricite"]["gestionnaire"] == "EDF SEI"
    assert g["a_jour_au"] and g["eau"]["operateur"]


def test_sql_miroir_des_poids_python():
    """Le batch SQL doit référencer EXACTEMENT les mêmes constantes de poids."""
    from labuse.faisabilite import viabilisation_build as B
    for w in (V.W_PERMIS, V.W_FACADE, V.W_BATI, V.W_ZONE):
        assert str(w) in B._SCORE_SQL
    # les seuils de bande SQL == Python
    assert "70" in B._BAND_SQL and "45" in B._BAND_SQL and "25" in B._BAND_SQL


def test_config_yaml_24_communes():
    import yaml
    root = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / "config" / "gestionnaires_via.yaml").read_text())
    assert len(cfg["communes"]) == 24
    for nom, c in cfg["communes"].items():
        assert c.get("epci") in {"CINOR", "CIREST", "TCO", "CIVIS", "CASUD"}, nom
        assert c.get("eau") and c.get("assainissement"), nom
