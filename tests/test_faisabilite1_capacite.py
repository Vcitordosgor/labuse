"""FAISABILITE-1 (lot B) — verrous du filtre global « Capacité ».

Le filtre Destination autorisée est traité à l'endpoint /filtre (accès base pour lever les
verdicts plu_destinations), PAS dans `_q_v2_where` (pur). Ces verrous sont DB-free : ils fixent
le contrat (champ query-param, entrée dans le memo, validation du slug, règle « calibration en
cours = non filtrée »). L'effet SQL sur le compteur est prouvé en recette (FAISABILITE-1.md).
"""
from __future__ import annotations

import dataclasses

from labuse.api.app import FiltreCriteres, _destination_interdit_keys
from labuse.plu.destinations import SOUS_DESTINATIONS


def test_destination_est_un_critere_du_filtre():
    """`destination` est un champ de FiltreCriteres → devient un query-param /filtre (comme les
    autres facettes) ; il entre dans la clé de mémorisation (sinon deux destinations partageraient
    le compteur caché)."""
    champs = {f.name for f in dataclasses.fields(FiltreCriteres)}
    assert "destination" in champs
    a = FiltreCriteres(source="q_v10_m129", destination="logement")
    b = FiltreCriteres(source="q_v10_m129", destination="hotels")
    n = FiltreCriteres(source="q_v10_m129")
    assert a.cache_key() != b.cache_key(), "deux destinations = deux compteurs mémorisés"
    assert a.cache_key() != n.cache_key(), "avec/sans destination = clés distinctes"
    assert a.cache_key()[-1] == "logement", "la destination est le dernier élément de la clé"


def test_slug_destination_connu():
    """Le slug par défaut du groupe Capacité (logement) et les sous-destinations filtrables
    existent bien au référentiel R151-28 (sinon l'endpoint renvoie 400)."""
    for slug in ("logement", "hotels", "artisanat_commerce_detail"):
        assert slug in SOUS_DESTINATIONS


def test_interdit_ignore_les_non_calibrees(monkeypatch):
    """Règle du mandat : « calibration en cours » (non calibrée) n'écarte JAMAIS une parcelle —
    seule une zone dont le règlement INTERDIT la destination est exclue. Vérifié sur un faux jeu
    de couples (commune, zone) sans base : verdict stubé, seule l'interdite ressort."""
    import labuse.api.app as app_mod

    class _Row:
        def __init__(self, commune, zone):
            self.commune, self.zone = commune, zone

    class _DB:
        def execute(self, *_a, **_k):
            class _R:
                @staticmethod
                def all():
                    return [_Row("A", "Zi"), _Row("A", "Zc"), _Row("A", "Zx")]
            return _R()

    def _fake_verdict(commune, zone, sd):
        if zone == "Zi":
            return {"etat_calibration": "calibree", "statut_effectif": "interdit"}
        if zone == "Zc":
            return {"etat_calibration": "non_calibree", "statut_effectif": "interdit"}  # non calibrée : ignorée
        return {"etat_calibration": "calibree", "statut_effectif": "autorise"}

    monkeypatch.setattr("labuse.plu.destinations.verdict", _fake_verdict)
    keys = _destination_interdit_keys(_DB(), "logement")
    assert keys == ["A||Zi"], "seule la zone calibrée ET interdite est écartée"


# ─────────────────────── Lot D — hypothèses modifiables + lignes manquantes ───────────────────────

def test_lignes_manquantes_ajoutees():
    """Lot D + FICHE-FIX-2 P4 — `extras` ajoute « Espaces inconstructibles déduits » (ER/EBC/greve)
    SANS changer le calcul ; l'étape « Logements sociaux imposés (LLS) » est TOUJOURS présente,
    branchée sur la règle VALIDÉE de la zone (`rules.mixite`), pas sur `extras`. U1c (Saint-Paul)
    n'en porte pas → « non modélisée pour cette zone » (jamais un 0 muet, jamais « non renseigné »)."""
    from labuse.faisabilite.engine import estimate_capacity
    from labuse.faisabilite.zonage import resolve_zone
    base = estimate_capacity(resolve_zone("U1c"), 2000, emprise_geo=(1200.0, 3.0))
    avec = estimate_capacity(resolve_zone("U1c"), 2000, emprise_geo=(1200.0, 3.0),
                             extras={"total_deduit_m2": 120, "er_m2": 120, "mixite": True})
    labels = [s.label for s in avec.steps]
    assert "Espaces inconstructibles déduits" in labels
    assert "Logements sociaux imposés (LLS)" in labels
    # la fourchette (le calcul) est INCHANGÉE — les lignes sont informatives
    assert avec.fourchette["logements_au_sol"] == base.fourchette["logements_au_sol"]
    mix = next(s for s in avec.steps if s.label == "Logements sociaux imposés (LLS)")
    assert mix.valeur == "non modélisée pour cette zone"


def test_mixite_lls_branchee_regle_validee():
    """FICHE-FIX-2 P4 — quand la zone porte une clause de mixité VALIDÉE (Uh Saint-Denis : 15 % dès
    30 logts, Art. Uh.2), l'étape LLS est SOURCÉE et cite l'article ; sinon « non modélisée »."""
    from labuse.faisabilite.engine import estimate_capacity
    from labuse.faisabilite.zonage import resolve_zone
    zr = resolve_zone("Uh", "Saint-Denis")
    assert zr and zr.mixite and zr.mixite.get("statut") == "valide"
    assert zr.mixite.get("quota_pct") == 15 and zr.mixite.get("seuil_logements") == 30
    fa = estimate_capacity(zr, 8000, emprise_geo=(5000.0, 3.0))
    mix = next(s for s in fa.steps if s.label == "Logements sociaux imposés (LLS)")
    assert mix.prov == "sourcee" and "Uh.2" in mix.source


def test_overrides_hypotheses_bornes_et_pct():
    """Lot D — les surcharges d'hypothèses sont clampées aux bornes, converties (% → fraction),
    et les clés inconnues/hors bornes sont ignorées (jamais un calcul détourné)."""
    from labuse.faisabilite.engine import Hypotheses, appliquer_overrides_hypotheses
    h = Hypotheses()
    ret = appliquer_overrides_hypotheses(h, {"coef_occupation": 60, "logement_m2": 50,
                                             "coef_rendement": 999, "inconnu": 1})
    assert ret == {"coef_occupation": 60.0, "logement_m2": 50.0}   # 999 hors borne + inconnu ignorés
    assert h.coef_occupation == 0.60                               # % → fraction
    assert h.logement_m2_bas == 50.0 and h.logement_m2_haut == 50.0  # « moyenne » → les deux bornes


def test_overrides_gardes_dans_le_projet_pas_ailleurs():
    """Lot D (doctrine 09/09) — les overrides se GARDENT dans le projet (prospection.faisa_overrides,
    validés par le moteur) ; une clé inconnue ou hors borne n'y entre pas."""
    from labuse.prospection import merge_prospection
    out = merge_prospection({}, {"faisa_overrides": {"coef_occupation": 60, "coef_rendement": 999, "x": 1}})
    assert out["faisa_overrides"] == {"coef_occupation": 60.0}   # seul le valide/borné est gardé
    # non-dict ignoré, jamais de stockage arbitraire
    assert "faisa_overrides" not in merge_prospection({}, {"faisa_overrides": "bidon"})
