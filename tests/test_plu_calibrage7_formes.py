"""PLU-CALIBRAGE-7 — les deux formes de règle ajoutées au schéma, lues par le moteur.

Forme 1 : recul « à l'alignement » / « en limite séparative » = recul 0 EXPLICITE (`forme: alignement`),
jamais confondu avec « absent » ni avec l'hypothèse prudente par défaut.
Forme 2 : pleine terre COMPOSÉE « X % d'espaces verts dont Y % de pleine terre » →
pleine_terre = X × Y / 100, les deux chiffres portés/sourcés, le moteur calcule.

Le garde-fou validées-only de PLU-CALIBRAGE-6 reste intact : une feuille de l'une de ces formes
encore `propose` rend la zone non calculable.
"""
from __future__ import annotations

from labuse.faisabilite import zonage as Z
from labuse.faisabilite.engine import Hypotheses, estimate_capacity


# ── forme 1 : recul à l'alignement (recul 0 explicite) ───────────────────────────────────────────
def test_recul_alignement_lu_seulement_si_valide():
    reg_v = {"retraits": {"voie": {"forme": "alignement", "min_m": 0, "statut": "valide",
                                   "article": "U 6", "page_pdf": 1, "citation": "à l'alignement"}}}
    reg_p = {"retraits": {"voie": {"forme": "alignement", "min_m": 0, "statut": "propose"}}}
    assert Z._recul_alignement(reg_v, "voie") is True
    assert Z._recul_alignement(reg_p, "voie") is False        # propose ne branche pas


def test_forme_alignement_propose_declenche_non_calculable():
    """Une feuille recul « forme: alignement » encore propose = SDP non calculable (garde PLU-6)."""
    reg = {"retraits": {"voie": {"forme": "alignement", "statut": "propose"}}}
    assert Z._regles_sdp_non_validees(reg) == ["retraits.voie"]
    reg_v = {"retraits": {"voie": {"forme": "alignement", "min_m": 0, "statut": "valide"}}}
    assert Z._regles_sdp_non_validees(reg_v) == []            # validée → ne déclenche pas


def test_engine_alignement_recul_zero_et_emprise_plus_grande():
    """Le moteur LIT la forme : recul 0 → emprise plus grande qu'avec un recul positif, et une
    hypothèse nomme « à l'alignement » (sourcé), jamais l'hypothèse prudente."""
    base = dict(code="U1", he_m=9.0, recul_limites_sep_m=3.0,
                sources={"recul_voirie": "Art. U 6.2 · p.18 (PLU, calibrage validé)"})
    align = Z.ZoneRules(recul_voirie_m=0.0, recul_voirie_alignement=True, **base)
    pos = Z.ZoneRules(recul_voirie_m=5.0, **base)
    fa = estimate_capacity(align, 1000.0, hyp=Hypotheses())
    fp = estimate_capacity(pos, 1000.0, hyp=Hypotheses())
    empr = lambda f: next(s for s in f.steps if s.label.startswith("Emprise au sol — reculs"))
    assert "~" in empr(fa).valeur
    # recul 0 (alignement) → emprise ≥ recul 5
    va = float(empr(fa).valeur.split("~")[1].split(" ")[0])
    vp = float(empr(fp).valeur.split("~")[1].split(" ")[0])
    assert va > vp
    assert any("alignement" in h.lower() for h in fa.hypotheses)
    assert not any("hypothèse prudente" in a for a in fa.avertissements)  # 0 sourcé, pas un défaut


# ── forme 2 : pleine terre composée ──────────────────────────────────────────────────────────────
def test_pleine_terre_composee_calculee():
    reg = {"pleine_terre": {"pct": {"espaces_verts_pct": 30, "pleine_terre_part": 50,
                                    "statut": "valide", "article": "Ua 11.1", "page_pdf": 27,
                                    "citation": "30% ... dont au moins 50% de pleine terre"}}}
    assert Z._pleine_terre_val(reg) == 15.0                   # 30 × 50 % = 15
    assert Z._pleine_terre_compose(reg) == {"espaces_verts_pct": 30.0, "part_pct": 50.0}
    # directe (pct) toujours lue
    reg_d = {"pleine_terre": {"pct": {"pct": 20.0, "statut": "valide"}}}
    assert Z._pleine_terre_val(reg_d) == 20.0
    # propose composée → a_verifier (ne branche pas) + déclenche non calculable
    reg_p = {"pleine_terre": {"pct": {"espaces_verts_pct": 30, "pleine_terre_part": 50, "statut": "propose"}}}
    assert Z._pleine_terre_val(reg_p) == Z.A_VERIFIER
    assert Z._regles_sdp_non_validees(reg_p) == ["pleine_terre.pct"]


def test_engine_pleine_terre_composee_reduit_et_montre_les_deux_chiffres():
    base = dict(code="U1", he_m=9.0, recul_voirie_m=3.0, recul_limites_sep_m=3.0)
    comp = Z.ZoneRules(pleine_terre_pct=15.0,
                       pleine_terre_compose={"espaces_verts_pct": 30.0, "part_pct": 50.0}, **base)
    sans = Z.ZoneRules(**base)
    fc = estimate_capacity(comp, 1000.0, hyp=Hypotheses())
    fs = estimate_capacity(sans, 1000.0, hyp=Hypotheses())
    pt = next(s for s in fc.steps if s.label == "Contrainte pleine terre")
    assert "30" in pt.formule and "50" in pt.formule and "15" in pt.formule
    # la contrainte réduit bien l'emprise retenue (ou l'égale si déjà bornée)
    assert any(s.label == "Contrainte pleine terre" for s in fc.steps)
    assert not any(s.label == "Contrainte pleine terre" for s in fs.steps)
