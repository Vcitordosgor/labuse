"""Vocabulaire prudent : « opportunité vérifiée » (pas « fiable »), SAR honnête, exports.

Garde-fou anti-surpromesse après l'intégration SAR partielle. Aucune donnée ni scoring touché."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# B2 (BLOC B) : le proto Vue est archivé (tag archive/proto-vue) — les garde-fous de
# vocabulaire visent désormais le front React servi (la fiche porte le disclaimer).
APP_JS = (ROOT / "frontend/src/components/fiche/Fiche.tsx").read_text(encoding="utf-8")
EXPORT = (ROOT / "src/labuse/api/export.py").read_text(encoding="utf-8")
ASSISTANT = (ROOT / "src/labuse/api/assistant.py").read_text(encoding="utf-8")


def test_badge_opportunite_n_est_plus_fiable():
    assert "opportunité fiable" not in APP_JS.lower()      # plus de sur-promesse


def test_sous_texte_honnete_present():
    assert "garantie de constructibilité" in APP_JS        # le disclaimer fiche (React)
    assert "certificat d'urbanisme" in APP_JS              # la limite juridique est dite


def test_prix_de_marche_fiable_conserve():
    # B2 : la distinction fiable/fragile du prix (DVF) vit désormais dans le socle IA
    # (assistant.py) — jamais un prix fragile vendu comme fiable.
    assert "prix de sortie fiable" in ASSISTANT
    assert "fragile" in ASSISTANT


def test_distinction_des_trois_notions():
    low = ASSISTANT.lower()
    assert "fiable" in low and "fragile" in low    # 1. prix de marché qualifié (DVF)
    assert "estimé" in low                          # 2. boussole Sourcé/Estimé
    assert "simulation" in APP_JS.lower() or "estimations indicatives" in APP_JS.lower()  # 3. bilan indicatif (fiche)


def test_export_pas_d_opportunite_fiable():
    assert "opportunité fiable" not in EXPORT.lower()
    assert "Prix de marché fiable" in EXPORT       # distinction préservée dans l'export


def test_sar_libelles_honnetes_dans_la_cascade():
    """SORTIE SERVIE, plus un grep du .py — on EXÉCUTE SarLayer et on lit le VERDICT rendu.
    Un test qui grep le source cassait à chaque renommage (ici SAR → « Potentiel foncier Région »,
    bascule vocabulaire 2026, M125-C6). Doctrine : le SAR est un PROXY DE VOCATION, jamais une
    interdiction ni une constructibilité, et jamais « juridiquement supérieur au PLU »."""
    from labuse.cascade.context import Intersection, ParcelRef
    from labuse.cascade.layers.phase1 import SarLayer
    from labuse.enums import CascadeVerdict

    P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)
    SAR = {"spatial_kind": "sar", "plu_kind": "plu_gpu_zone", "uau_prefixes": ["U", "AU"],
           "divergent_subtypes": ["vocation_naturelle"], "info_subtypes": ["vocation_mixte"]}

    class _Ctx:
        def __init__(self, by): self.by = by
        def kind_present(self, k): return k in self.by
        def intersections(self, _p, k): return self.by.get(k, [])

    def _i(sub, cov, lib=None):
        return Intersection(sub, None, cov, {"libelle": lib} if lib else {}, None)

    def _run(by):
        return SarLayer().evaluate(P, _Ctx(by), SAR)

    # hors îlot cartographié (couverture nulle) : on ne conclut PAS à « aucune contrainte »
    v = _run({"sar": [_i("vocation_naturelle", 0.0)]})
    assert v.result == CascadeVerdict.PASS
    assert "hors îlot cartographié — aucune contrainte déduite automatiquement" in v.detail.lower()
    # vocation compatible (urbaine) : information, à croiser avec PLU/PPR
    v = _run({"sar": [_i("vocation_urbaine", 1.0, "territoire urbain")]})
    assert v.result == CascadeVerdict.PASS
    assert "vocation compatible détectée" in v.detail and "à croiser avec PLU/PPR" in v.detail
    # proxy indicatif (naturel, sans zone U/AU) : ne vaut ni interdiction ni constructibilité
    v = _run({"sar": [_i("vocation_naturelle", 1.0, "espace naturel")]})
    assert v.result == CascadeVerdict.PASS
    assert "ne vaut ni interdiction ni constructibilité" in v.detail
    # divergent du PLU (naturel sur zone U) : ⚠ vigilance, wording « Potentiel foncier Région »
    v = _run({"sar": [_i("vocation_naturelle", 0.98, "espace naturel")], "plu_gpu_zone": [_i("U1b", 1.0)]})
    assert v.result == CascadeVerdict.PASS
    assert v.detail.startswith("⚠ Potentiel foncier Région divergent du PLU")
    # HONNÊTETÉ servie : jamais « juridiquement supérieur », toujours nommé « Potentiel foncier Région »
    for by in ({"sar": [_i("vocation_urbaine", 1.0)]}, {"sar": [_i("vocation_naturelle", 1.0)]}):
        d = _run(by).detail
        assert "juridiquement supérieur" not in d.lower() and "Potentiel foncier Région" in d
