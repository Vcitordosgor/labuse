"""Badge « micro-opportunité » (Option A, audit petites opportunités 251–500 m²).

Le badge est un AFFICHAGE pur : il NUANCE une opportunité de petite surface sans toucher au verdict
ni aux scores. Ces tests verrouillent :
  - une opportunité ≤ 500 m² est taguée « micro-opportunité » ; une > 500 m² ne l'est pas ;
  - le statut/verdict n'est JAMAIS modifié par le badge (le déclassement métier reste seul juge) ;
  - aucun calcul métier n'est touché (la fonction est pure, sans effet de bord).
Fonctions pures (un dict / deux scalaires) — pas de DB.
"""
from labuse.api.export import fiche_html, fiche_markdown
from labuse.api.resume import MICRO_OPPORTUNITE_MAX_M2, is_micro_opportunite
from labuse.enums import EvaluationStatus as ES
from labuse.scoring.declassement import apply_declassement


# ── 1. Fonction pure : seuil et conditions ───────────────────────────────────
def test_opportunite_petite_est_micro():
    assert is_micro_opportunite("opportunite", 300) is True
    assert is_micro_opportunite("opportunite", 251) is True
    assert is_micro_opportunite("opportunite", MICRO_OPPORTUNITE_MAX_M2) is True   # 500 inclus


def test_opportunite_grande_n_est_pas_micro():
    assert is_micro_opportunite("opportunite", 501) is False
    assert is_micro_opportunite("opportunite", 7000) is False


def test_seuil_est_500():
    assert MICRO_OPPORTUNITE_MAX_M2 == 500.0


def test_seul_le_statut_opportunite_est_concerne():
    # le badge ne s'applique qu'aux opportunités — jamais aux autres verdicts
    for st in ("a_creuser", "exclue", "faux_positif_probable", "inconnu", None):
        assert is_micro_opportunite(st, 300) is False


def test_surface_absente_jamais_micro():
    assert is_micro_opportunite("opportunite", None) is False


def test_fonction_pure_renvoie_bool():
    # pas d'effet de bord : deux scalaires en lecture seule → un booléen
    r = is_micro_opportunite("opportunite", 300)
    assert isinstance(r, bool)


# ── 2. Le badge n'altère PAS le verdict (déclassement métier inchangé) ────────
def test_micro_opportunite_garde_son_verdict():
    # une opportunité de 300 m² (donc « micro ») reste OPPORTUNITE : le badge nuance, ne déclasse pas
    statut, motif = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 300.0})
    assert statut is ES.OPPORTUNITE and motif is None
    # cohérence : tag d'affichage actif sur cette même parcelle
    assert is_micro_opportunite(statut.value, 300.0) is True


def test_seuil_declassement_250_inchange():
    # garde-fou : sous 250 m² c'est le DÉCLASSEMENT (verdict) qui agit, pas le badge → plus d'opportunité
    statut, _ = apply_declassement(ES.OPPORTUNITE, {"surface_m2": 249.0})
    assert statut is ES.A_CREUSER
    assert is_micro_opportunite(statut.value, 249.0) is False   # plus « opportunité » → pas de tag


# ── 3. Intégration export (Markdown + HTML) : badge présent/absent ───────────
def _fiche(status, surface):
    return {
        "parcel": {"idu": "97415000DE1325", "commune": "Saint-Paul", "surface_m2": surface,
                   "section": "DE", "numero": "1325"},
        "verdict": {"status": status, "opportunity_score": 67, "completeness_score": 92,
                    "reasons": [], "micro_opportunite": is_micro_opportunite(status, surface)},
        "cascade": [], "sources_responded": ["DVF"], "sources_silent": [],
        "disclaimer": "Pré-analyse. Rien n'est garanti.",
        "faisabilite": {"bilan": {"fiable": False}},
        "ai": None,
    }


def test_export_petite_opportunite_affiche_micro():
    f = _fiche("opportunite", 300)
    md, h = fiche_markdown(f), fiche_html(f)
    assert "micro-opportunité" in md and "micro-opportunité" in h
    assert "assemblage" in md.lower() and "assemblage" in h.lower()
    # le verdict « opportunité » reste affiché à côté du badge (nuance, pas remplacement)
    assert "opportunite" in md


def test_export_grande_opportunite_sans_micro():
    f = _fiche("opportunite", 7000)
    md, h = fiche_markdown(f), fiche_html(f)
    assert "micro-opportunité" not in md and "micro-opportunité" not in h


def test_export_a_creuser_sans_micro():
    f = _fiche("a_creuser", 300)   # petite mais pas une opportunité → pas de badge
    md, h = fiche_markdown(f), fiche_html(f)
    assert "micro-opportunité" not in md and "micro-opportunité" not in h
