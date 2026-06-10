"""Tests du moteur de pré-faisabilité (ÉTAPE B). Purs (sans DB)."""
from labuse.faisabilite import estimate_capacity, resolve_zone
from labuse.faisabilite.engine import Contraintes, Hypotheses


def test_resolution_zone_directe():
    r = resolve_zone("U1c")
    assert r is not None and r.he_m == 15 and r.hf_m == 19 and r.constructible_neuf


def test_resolution_au_renvoi_vers_u():
    r = resolve_zone("AU1a")
    assert r is not None and r.via_renvoi and "U1a" in r.via_renvoi
    assert r.he_m == resolve_zone("U1a").he_m


def test_au_st_non_constructible_neuf():
    r = resolve_zone("AU3st")
    assert r is not None and r.constructible_neuf is False
    f = estimate_capacity(r, 1000)
    assert f.constructible is False and "transition" in f.verdict.lower()
    assert f.fourchette["logements_au_sol"] == (0, 0)


def test_emprise_bornee_par_reculs_pas_par_emprise():
    f = estimate_capacity(resolve_zone("U2c"), 1000)
    assert any("non réglementée" in s.formule for s in f.steps)
    assert any("reculs" in s.label.lower() for s in f.steps)


def test_hauteur_he_donne_niveaux():
    f = estimate_capacity(resolve_zone("U1c"), 1200)
    assert f.fourchette["niveaux"] == "R+4"
    lo, hi = f.fourchette["logements_au_sol"]
    assert hi >= lo and f.constructible


def test_zone_basse_moins_de_niveaux():
    f = estimate_capacity(resolve_zone("U2d"), 1000)
    assert f.fourchette["niveaux"] == "R+0"


def test_pleine_terre_reduit_emprise():
    f = estimate_capacity(resolve_zone("U3a"), 1000)
    assert any("pleine terre" in s.label.lower() for s in f.steps)


def test_deux_scenarios_stationnement():
    # sous-sol (sol non consommé) >= au sol (plafonné par le parking)
    f = estimate_capacity(resolve_zone("U1c"), 4000)
    sol = f.fourchette["logements_au_sol"]
    sous = f.fourchette["logements_sous_sol"]
    assert sous[1] >= sol[1] and f.fourchette["stationnement_regime"] == "borne"
    assert "au sol" in f.verdict and "sous-sol" in f.verdict


def test_u1pru_stationnement_exempte_non_borne():
    f = estimate_capacity(resolve_zone("U1pru"), 3000)
    assert f.fourchette["stationnement_regime"] == "exempt"
    assert f.fourchette["logements_au_sol"] == f.fourchette["logements_sous_sol"]
    assert "non réglementé" in f.verdict.lower()


def test_geometrie_reelle_utilisee():
    # emprise_geo fournie → l'étape cite la géométrie réelle
    f = estimate_capacity(resolve_zone("U1c"), 1000, emprise_geo=(600.0, 3.0))
    assert any("géométrie réelle" in s.label.lower() for s in f.steps)


def test_terrain_trop_exigu():
    f = estimate_capacity(resolve_zone("U1c"), 80, emprise_geo=(2.0, 3.0))
    assert f.constructible is False and "exigu" in f.verdict.lower()


def test_modulation_alea_fort_annule():
    f = estimate_capacity(resolve_zone("U1c"), 1000, Contraintes(alea_ppr="fort"))
    assert f.constructible is False and f.fourchette["logements_au_sol"] == (0, 0)
    assert any("aléa fort" in m.lower() for m in f.modulation)


def test_modulation_pente_forte_reduit():
    base = estimate_capacity(resolve_zone("U6a"), 1500)
    pentu = estimate_capacity(resolve_zone("U6a"), 1500, Contraintes(pente_pct=35))
    assert pentu.fourchette["logements_au_sol"][1] <= base.fourchette["logements_au_sol"][1]
    assert any("pente forte" in m.lower() for m in pentu.modulation)


def test_recul_a_verifier_signale_et_prudent():
    f = estimate_capacity(resolve_zone("U1a"), 1000)
    assert any("recul voirie" in a.lower() and "à_vérifier" in a.lower() for a in f.avertissements)


def test_bandeau_et_hypotheses():
    f = estimate_capacity(resolve_zone("U5b"), 800)
    assert "ne remplace pas" in f.bandeau
    txt = " ".join(f.hypotheses).lower()
    assert "hauteur d'étage" in txt and "logement" in txt


def test_capacite_realiste_ordre_de_grandeur():
    # U1c ~4500 m² R+4 doit donner ~40-70 logts (repère réaliste), PAS 200+.
    f = estimate_capacity(resolve_zone("U1c"), 4500, emprise_geo=(2600.0, 3.0))
    hi = f.fourchette["logements_au_sol"][1]
    assert 35 <= hi <= 80, f"hors ordre de grandeur réaliste: {f.fourchette}"


def test_etapes_rendement_et_occupation():
    f = estimate_capacity(resolve_zone("U1c"), 2000)
    labels = " ".join(s.label.lower() for s in f.steps)
    assert "occupation" in labels and "habitable" in labels and "densité" in labels
    txt = " ".join(f.hypotheses).lower()
    assert "rendement" in txt and "occupation" in txt and "densité" in txt


def test_plafond_densite_borne_les_zones_denses():
    # U1pru R+9 sans plafond exploserait ; le plafond densité doit le borner et le signaler.
    f = estimate_capacity(resolve_zone("U1pru"), 4000, emprise_geo=(3200.0, 3.0))
    assert any("plafond de densité" in m.lower() for m in f.modulation)
    assert f.fourchette["logements_sous_sol"][1] < 200  # borné, plus de 400+


def test_hypotheses_chargees_depuis_yaml():
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses.charger()
    assert h.coef_rendement == 0.80 and h.coef_occupation == 0.45
    assert h.logement_m2_bas == 65.0 and h.densite_logts_ha_par_niveau == 30.0
