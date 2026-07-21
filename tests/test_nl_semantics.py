"""M11 · SURFACE B1 — tests de la validation SÉMANTIQUE (schéma ≠ sens).

Boussole (Vic) : signaler > refuser > appliquer un filtre douteux. On teste que :
  - la MISTRADUCTION est tuée (passoire→risques ne survit jamais),
  - le DROP SILENCIEUX est tué (critère non supporté toujours listé, jamais avalé),
  - AUCUNE régression sur les requêtes valides (filtres inchangés, liste vide),
  - AUCUN faux positif de signalement (requête pleinement supportée → rien signalé).

`check_semantics(query, filters)` est PUR (aucun appel IA, aucune DB) — testable en isolation.
Les `filters` d'entrée simulent ce que le traducteur haiku produit ; la fonction est le garde-fou APRÈS.
"""
from labuse.api.nl_semantics import check_semantics

# ─────────────────────── LOT 1 — la mistraduction est tuée ───────────────────────

def test_passoire_ne_produit_pas_flag_risques():
    """LE cas dur : « passoires thermiques G à Saint-Denis » — le modèle mistraduit DPE→flags:[risques].
    Le sens n'a aucun rapport avec un risque naturel → le flag est RETIRÉ (jamais servi)."""
    q = "les passoires thermiques classées G à Saint-Denis"
    model_out = {"commune": "Saint-Denis", "flags": ["risques"]}
    filters, non_appliques = check_semantics(q, model_out)

    assert "flags" not in filters, "flags:[risques] mistraduit doit être retiré"
    assert filters == {"commune": "Saint-Denis"}, "la commune (correcte) reste"
    assert any("DPE" in c for c in non_appliques), "le critère DPE doit être signalé non supporté"


def test_flag_risques_conserve_si_vrai_risque_demande():
    """Non-régression du garde-fou : un flag risques JUSTIFIÉ par la requête reste appliqué."""
    q = "les parcelles inondables à Sainte-Marie"
    filters, non_appliques = check_semantics(q, {"commune": "Sainte-Marie", "flags": ["risques"]})
    assert filters["flags"] == ["risques"]
    assert non_appliques == []


def test_flag_partiel_garde_le_justifie_retire_le_mistraduit():
    """Un flag justifié (abf) coexiste avec un flag mistraduit (risques) : on garde l'un, retire l'autre."""
    q = "près d'un monument historique à Saint-Denis"   # abf justifié, aucun risque évoqué
    filters, _ = check_semantics(q, {"commune": "Saint-Denis", "flags": ["abf", "risques"]})
    assert filters["flags"] == ["abf"]


# ─────────────────────── LOT 2 — le drop silencieux est tué ───────────────────────

def test_criteres_encore_non_supportes_toujours_signales():
    """Non-régression du mécanisme B1 : un critère TOUJOURS non supporté (assainissement) reste
    listé, jamais avalé. (Le drop de « personne morale » est désormais tué par B2 en l'APPLIQUANT
    — cf. test_b2_personne_morale_appliquee_pas_signalee.)"""
    q = "les brûlantes de Saint-Pierre raccordées à l'assainissement collectif"
    filters, non_appliques = check_semantics(q, {"commune": "Saint-Pierre", "tiers": ["brulante"]})
    assert filters == {"commune": "Saint-Pierre", "tiers": ["brulante"]}
    assert any("assainissement" in c for c in non_appliques)


def test_plusieurs_criteres_non_supportes_tous_listes():
    # B2 : « zone U » et « société » sont désormais SUPPORTÉS → PAS signalés ; DPE + assainissement le restent.
    q = "passoires thermiques en zone U avec assainissement collectif détenues par une société"
    _, non_appliques = check_semantics(q, {})
    labels = " | ".join(non_appliques)
    assert "DPE" in labels and "assainissement" in labels
    assert "zonage" not in labels and "personne morale" not in labels, "PM/zonage supportés par B2"
    assert len(non_appliques) == len(set(non_appliques)), "pas de doublon"


# ─────────────────────── B2 — personne morale & zonage désormais SUPPORTÉS ───────────────────────

def test_b2_personne_morale_appliquee_pas_signalee():
    """« brûlantes SP propriétaire personne morale » : le filtre s'applique ET ne figure PLUS
    dans criteres_non_appliques (B2 l'a rendu supporté — plus jamais avalé ni signalé)."""
    q = "les brûlantes de Saint-Pierre avec un propriétaire personne morale"
    f, non_appliques = check_semantics(q, {"commune": "Saint-Pierre", "tiers": ["brulante"], "personneMorale": True})
    assert f.get("personneMorale") is True
    assert non_appliques == []


def test_b2_sci_ne_declenche_plus_de_signalement():
    q = "terrains détenus par une SCI à Saint-Paul"
    _, non_appliques = check_semantics(q, {"commune": "Saint-Paul", "personneMorale": True})
    assert non_appliques == []


def test_b2_personne_morale_injectee_sans_mot_retiree():
    """Anti-mistraduction : personneMorale produit sans aucun mot justificatif → retiré (jamais appliqué)."""
    q = "les grandes parcelles de Saint-Leu de plus de 1000 m²"
    f, _ = check_semantics(q, {"commune": "Saint-Leu", "personneMorale": True})
    assert "personneMorale" not in f


def test_b2_zonage_applique_pas_signale():
    q = "parcelles constructibles en zone U à Saint-Paul"
    f, non_appliques = check_semantics(q, {"commune": "Saint-Paul", "zonage": ["U"]})
    assert f.get("zonage") == ["U"]
    assert non_appliques == []


def test_b2_zonage_injecte_sans_mot_retire():
    """Anti-mistraduction : une famille de zonage non justifiée par la requête est retirée."""
    q = "les chaudes de Saint-Denis"
    f, _ = check_semantics(q, {"commune": "Saint-Denis", "zonage": ["A"]})
    assert "zonage" not in f


def test_b2_zonage_agricole_garde_le_bon_retire_le_mistraduit():
    q = "terrains en zone agricole à Sainte-Rose"       # A justifié, U non
    f, _ = check_semantics(q, {"commune": "Sainte-Rose", "zonage": ["A", "U"]})
    assert f["zonage"] == ["A"]


# ─────────────────────── LOT 4 — non-régression & pas de faux positif ───────────────────────

def test_requete_pleinement_supportee_ne_signale_rien():
    """Requête 100 % dans le périmètre des 14 champs → filtres inchangés, AUCUN signalement (pas de loup crié)."""
    q = "les chaudes de Saint-Paul de plus de 800 m²"
    model_out = {"commune": "Saint-Paul", "tiers": ["chaude"], "surfaceMin": 800}
    filters, non_appliques = check_semantics(q, model_out)
    assert filters == model_out
    assert non_appliques == []


def test_vue_mer_justifiee_reste():
    q = "les brûlantes avec vue mer à Saint-Leu"
    filters, non_appliques = check_semantics(q, {"commune": "Saint-Leu", "tiers": ["brulante"], "vueMer": True})
    assert filters.get("vueMer") is True
    assert non_appliques == []


def test_booleen_non_demande_est_retire():
    """Un booléen catégoriel non justifié par la requête (le modèle l'a inventé) ne s'applique jamais.
    (M3 spin-off : l'exemple historique « vueMer » est parti avec la feature — même mécanique, autre booléen.)"""
    q = "les grandes parcelles de Saint-Pierre"
    filters, _ = check_semantics(q, {"commune": "Saint-Pierre", "surfaceMin": 1000, "veille": True})
    assert "veille" not in filters


def test_score_min_et_surface_intacts():
    """Les filtres chiffrés purs ne sont jamais touchés (aucun risque de mistraduction sémantique)."""
    q = "score minimum 15 et surface entre 500 et 2000 à Sainte-Suzanne"
    model_out = {"commune": "Sainte-Suzanne", "scoreMin": 15, "surfaceMin": 500, "surfaceMax": 2000}
    filters, non_appliques = check_semantics(q, model_out)
    assert filters == model_out
    assert non_appliques == []


def test_filtres_vides_et_query_vide_ne_plantent_pas():
    assert check_semantics("", {}) == ({}, [])
    assert check_semantics(None, None) == ({}, [])


def test_ne_mute_pas_le_dict_entrant():
    """check_semantics retourne une COPIE — l'appelant garde son objet intact."""
    original = {"commune": "Saint-Denis", "flags": ["risques"]}
    check_semantics("passoire thermique", original)
    assert original == {"commune": "Saint-Denis", "flags": ["risques"]}
