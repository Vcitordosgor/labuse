"""Tests du moteur de pré-faisabilité (ÉTAPE B). Purs (sans DB)."""
from labuse.faisabilite import estimate_capacity, resolve_zone
from labuse.faisabilite.engine import Contraintes, Hypotheses


def test_resolution_zone_directe():
    r = resolve_zone("U1c")
    assert r is not None and r.he_m == 15 and r.hf_m == 19
    assert r.constructible_neuf is True


def test_resolution_au_renvoi_vers_u():
    r = resolve_zone("AU1a")
    assert r is not None and r.via_renvoi and "U1a" in r.via_renvoi
    assert r.he_m == resolve_zone("U1a").he_m  # mêmes règles que U1a


def test_au_st_non_constructible_neuf():
    r = resolve_zone("AU3st")
    assert r is not None and r.constructible_neuf is False
    f = estimate_capacity(r, 1000)
    assert f.constructible is False and "transition" in f.verdict.lower()
    assert f.fourchette["logements"] == (0, 0)


def test_emprise_bornee_par_reculs_pas_par_emprise():
    # U2c : emprise non réglementée → l'enveloppe vient des reculs, pas d'un %.
    r = resolve_zone("U2c")
    f = estimate_capacity(r, 1000)
    libs = " ".join(s.formule + s.valeur for s in f.steps)
    assert "non réglementée" in libs  # Art. 9 = pas de règle d'emprise
    assert any("reculs" in s.label.lower() for s in f.steps)


def test_hauteur_he_donne_niveaux():
    # hé 15 m ÷ 3 = 5 niveaux → R+4 (U1c)
    f = estimate_capacity(resolve_zone("U1c"), 1200)
    assert f.fourchette["niveaux"] == "R+4"
    assert f.constructible and f.fourchette["logements"][1] >= f.fourchette["logements"][0]


def test_zone_basse_moins_de_niveaux():
    # U2d hé 4,5 m ÷ 3 = 1 niveau → R+0
    f = estimate_capacity(resolve_zone("U2d"), 1000)
    assert f.fourchette["niveaux"] == "R+0"


def test_pleine_terre_reduit_emprise():
    # U3a a 20% pleine terre → présence de l'étape de réduction
    f = estimate_capacity(resolve_zone("U3a"), 1000)
    assert any("pleine terre" in s.label.lower() for s in f.steps)


def test_modulation_alea_fort_annule():
    f = estimate_capacity(resolve_zone("U1c"), 1000, Contraintes(alea_ppr="fort"))
    assert f.constructible is False
    assert f.fourchette["logements"] == (0, 0)
    assert any("aléa fort" in m.lower() for m in f.modulation)


def test_modulation_pente_forte_reduit():
    base = estimate_capacity(resolve_zone("U6a"), 1500)
    pentu = estimate_capacity(resolve_zone("U6a"), 1500, Contraintes(pente_pct=35))
    assert pentu.fourchette["logements"][1] <= base.fourchette["logements"][1]
    assert any("pente forte" in m.lower() for m in pentu.modulation)


def test_recul_a_verifier_signale_et_prudent():
    # U1a : recul voirie "a_verifier" → avertissement + hypothèse prudente utilisée
    f = estimate_capacity(resolve_zone("U1a"), 1000)
    assert any("recul voirie" in a.lower() and "à_vérifier" in a.lower() for a in f.avertissements)


def test_resultat_est_une_fourchette():
    f = estimate_capacity(resolve_zone("U4a"), 2000)
    lo, hi = f.fourchette["logements"]
    assert isinstance(lo, int) and isinstance(hi, int) and hi >= lo
    assert "à" in f.verdict  # « ~X à Y logements »


def test_bandeau_present():
    f = estimate_capacity(resolve_zone("U5b"), 800)
    assert "ne remplace pas" in f.bandeau


def test_hypotheses_signalees():
    f = estimate_capacity(resolve_zone("U1c"), 1000, hyp=Hypotheses())
    txt = " ".join(f.hypotheses)
    assert "hauteur d'étage" in txt.lower() and "logement" in txt.lower()
