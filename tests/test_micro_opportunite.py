"""Badge « micro-opportunité » (Option A, audit petites opportunités 251–500 m²).

M34 (dette #14) : le badge s'applique aux TIERS HAUTS servis (brûlante/chaude) — le
vocabulaire cascade legacy (« opportunite ») n'est plus un verdict. Le badge reste un
AFFICHAGE pur : il NUANCE sans toucher au verdict ni aux scores. Ces tests verrouillent :
  - un tier haut ≤ 500 m² est tagué « micro-opportunité » ; > 500 m² non ;
  - le statut/verdict n'est JAMAIS modifié par le badge ;
  - le signal cascade (surface < 250) reste un signal de VIGILANCE (rail informatif),
    plus jamais un verdict — il ne pilote plus le badge.
Fonctions pures (un dict / deux scalaires) — pas de DB.
"""
from labuse.api.export import fiche_html, fiche_markdown
from labuse.api.resume import MICRO_OPPORTUNITE_MAX_M2, is_micro_opportunite
from labuse.enums import EvaluationStatus as ES
from labuse.scoring.declassement import apply_declassement


# ── 1. Fonction pure : seuil et conditions ───────────────────────────────────
def test_tier_haut_petit_est_micro():
    assert is_micro_opportunite("brulante", 300) is True
    assert is_micro_opportunite("chaude", 251) is True
    assert is_micro_opportunite("brulante", MICRO_OPPORTUNITE_MAX_M2) is True   # 500 inclus


def test_tier_haut_grand_n_est_pas_micro():
    assert is_micro_opportunite("brulante", 501) is False
    assert is_micro_opportunite("chaude", 7000) is False


def test_seuil_est_500():
    assert MICRO_OPPORTUNITE_MAX_M2 == 500.0


def test_seuls_les_tiers_hauts_sont_concernes():
    # le badge ne s'applique qu'aux tiers hauts servis — jamais aux autres verdicts
    for st in ("a_creuser", "reserve_fonciere", "ecartee", "declasse_bati_sature",
               "non_evaluee", "opportunite", None):
        assert is_micro_opportunite(st, 300) is False


def test_surface_absente_jamais_micro():
    assert is_micro_opportunite("brulante", None) is False


def test_fonction_pure_renvoie_bool():
    r = is_micro_opportunite("brulante", 300)
    assert isinstance(r, bool)


# ── 2. Le rail cascade reste une mécanique de VIGILANCE (M34) — seuils inchangés ──
def test_cascade_surface_300_sans_signal():
    # 300 m² : aucun signal non-franc — le rail vigilance reste silencieux
    statut, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 300.0})
    assert statut is ES.OPPORTUNITE and motif is None


def test_seuil_cascade_250_inchange():
    # sous 250 m² le rail cascade émet son signal (motif) — depuis M34 c'est une VIGILANCE
    # informative de fiche, plus jamais un verdict (le tier servi seul fait verdict).
    statut, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 249.0})
    assert statut is ES.A_CREUSER and "surface réduite" in motif


# ── 3. Intégration export (Markdown + HTML) : badge présent/absent ───────────
def _fiche(status, surface, label=None):
    return {
        "parcel": {"idu": "97415000DE1325", "commune": "Saint-Paul", "surface_m2": surface,
                   "section": "DE", "numero": "1325"},
        "verdict": {"status": status, "label": label, "opportunity_score": 67,
                    "completeness_score": 92, "reasons": [], "servable": True,
                    "micro_opportunite": is_micro_opportunite(status, surface)},
        "cascade": [], "sources_responded": ["DVF"], "sources_silent": [],
        "disclaimer": "Pré-analyse. Rien n'est garanti.",
        "faisabilite": {"bilan": {"fiable": False}},
        "ai": None,
    }


def test_export_petit_tier_haut_affiche_micro():
    f = _fiche("brulante", 300, label="Brûlante")
    md, h = fiche_markdown(f), fiche_html(f)
    assert "micro-opportunité" in md and "micro-opportunité" in h
    assert "assemblage" in md.lower() and "assemblage" in h.lower()
    # le verdict traduit reste affiché à côté du badge (nuance, pas remplacement)
    assert "Brûlante" in md


def test_export_grand_tier_haut_sans_micro():
    f = _fiche("brulante", 7000, label="Brûlante")
    md, h = fiche_markdown(f), fiche_html(f)
    assert "micro-opportunité" not in md and "micro-opportunité" not in h


def test_export_a_creuser_sans_micro():
    f = _fiche("a_creuser", 300)   # petite mais pas un tier haut → pas de badge
    md, h = fiche_markdown(f), fiche_html(f)
    assert "micro-opportunité" not in md and "micro-opportunité" not in h
