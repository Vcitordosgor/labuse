"""M11 · SURFACE B2 — tests des questions AGRÉGÉES (compter/classer, pas filtrer).

Deux garanties testées PUREMENT (sans DB ni modèle) :
  - la DISTINCTION filtre vs agrégat (« chaudes à SP » ≠ « combien de chaudes à SP »),
  - la RÈGLE DE FER : un chiffre inventé est rejeté par la couche 2 du socle (le vrai compte SQL passe,
    un faux compte est refusé) — c'est ce qui empêche l'IA d'halluciner un nombre.

Le pipeline complet (SQL réel → prose sourcée) est prouvé en live dans SURFACE-B2.md (la DB de test
est vide ; ces tests ciblent la logique déterministe).
"""
from labuse.ai import core
from labuse.api.nl_aggregate import _detect_tiers, is_aggregate

# ─────────────────────── distinction filtre vs agrégat ───────────────────────

def test_filtre_nest_pas_un_agregat():
    assert is_aggregate("les chaudes à Saint-Pierre") is False
    assert is_aggregate("brûlantes de Saint-Paul vue mer") is False


def test_agregat_detecte():
    assert is_aggregate("combien de chaudes à Saint-Pierre ?") is True
    assert is_aggregate("quelle commune a le plus de brûlantes ?") is True
    assert is_aggregate("répartition des brûlantes par commune") is True
    assert is_aggregate("nombre de réserves foncières à Saint-Leu") is True


def test_detect_tiers():
    assert _detect_tiers("combien de brûlantes") == [("brulante", "brûlante")]
    assert _detect_tiers("combien de chaudes") == [("chaude", "chaude")]
    assert _detect_tiers("combien d'opportunités") == []   # aucun tier nommé → tous (géré en aval)


# ─────────────────────── RÈGLE DE FER — le socle rejette un faux compte ───────────────────────

def _ctx(n):
    """Contexte agrégé minimal : un compte SOURCÉ, comme answer_aggregate le construit."""
    return {"donnees": {"nombre": {"valeur": n, "provenance": "SOURCE"}}}


def test_socle_accepte_le_vrai_compte():
    chk = core.validate_output("Saint-Paul compte 28 parcelles brûlantes ⟨src:nombre⟩.", _ctx(28))
    assert chk.ok is True
    assert "nombre" in chk.sources


def test_socle_rejette_un_faux_compte():
    """LE test qui compte : un compte inventé (35 ≠ 28) est REFUSÉ — jamais servi."""
    chk = core.validate_output("Saint-Paul compte 35 parcelles brûlantes ⟨src:nombre⟩.", _ctx(28))
    assert chk.ok is False
    assert "35" in (chk.reason or "")


def test_socle_rejette_sans_source():
    """Un compte affirmé sans citer sa source est refusé (require_sources)."""
    chk = core.validate_output("Il y a beaucoup de parcelles à Saint-Paul.", _ctx(28), require_sources=True)
    assert chk.ok is False


def test_socle_valide_un_classement():
    ctx = {"donnees": {"classement": {"valeur": [{"commune": "Saint-Paul", "nombre": 28},
                                                 {"commune": "Saint-Pierre", "nombre": 12}],
                                      "provenance": "SOURCE"}}}
    chk = core.validate_output("Saint-Paul arrive en tête avec 28 parcelles ⟨src:classement⟩.", ctx)
    assert chk.ok is True


# ───────── tolérance par RÔLE, pas par TAILLE : les PETITS comptes sont vérifiés strict ─────────

def test_petit_compte_faux_rejete_meme_sous_12():
    """LE test demandé : Cilaos a 2 brûlantes → une prose qui dit « 5 » est REJETÉE, alors que 5 ≤ 12.
    L'angle mort de la tolérance par taille est fermé."""
    chk = core.validate_output("Cilaos compte 5 parcelles brûlantes ⟨src:nombre⟩.",
                               _ctx(2), strict_numbers=True)
    assert chk.ok is False
    assert "5" in (chk.reason or "")


def test_petit_compte_correct_accepte():
    chk = core.validate_output("Cilaos compte 2 parcelles brûlantes ⟨src:nombre⟩.",
                               _ctx(2), strict_numbers=True)
    assert chk.ok is True


def test_compte_petit_et_tournure_coexistent():
    """Compte petit correct (2) ET tournure rédactionnelle (R+2, « 3 logements ») coexistent sans
    faux rejet — la tournure est tolérée par son RÔLE (motif), pas par sa taille."""
    prose = "Cilaos compte 2 parcelles brûlantes ⟨src:nombre⟩, plutôt du R+2 avec 3 logements par lot."
    chk = core.validate_output(prose, _ctx(2), strict_numbers=True)
    assert chk.ok is True


def test_mode_non_strict_inchange_pour_la_fiche():
    """Non-régression Surface A : HORS mode strict, la tolérance 0-12 reste (R+n de la barre de fiche
    ne doit pas se mettre à être rejeté)."""
    ctx = {"zone": {"valeur": "AUst", "provenance": "SOURCE"}}
    chk = core.validate_output("Gabarit R+2 envisageable en zone AUst ⟨src:zone⟩.", ctx)
    assert chk.ok is True   # « 2 » toléré comme avant (bruit rédactionnel), fiche non cassée
