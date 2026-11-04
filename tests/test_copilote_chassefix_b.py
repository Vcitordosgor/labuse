"""CHASSE-FIX-1 — lot B Copilote : reproductions rouge-avant / verte-après des trouvailles.

B-5 (adresse voie+commune), B-6 (zone à cheval citée en entier), CH-B-m5 (relance sans possessif
hérite la parcelle), CH-B-m7 (hauteur avec son unité). Tests DÉTERMINISTES : les grammaires d'omnibox
(`_sugg_adresse`) et le moteur de zone (`zone_dominante`) sont des bouchons, le modèle de routage est
court-circuité — on teste la LOGIQUE corrigée, pas la base ni l'IA.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from labuse.copilote_v2 import outils
from labuse.copilote_v2 import resolveur as R
from labuse.copilote_v2 import resume_fiche as RF
from labuse.copilote_v2 import router


@pytest.fixture(scope="module")
def db():
    from labuse.db import session_factory
    s = session_factory()()
    try:
        yield s
    finally:
        s.close()


# ─────────────────────────── B-5 — adresse : voie ET commune ───────────────────────────
def test_mots_adresse_separe_voie_commune():
    voie, commune, cp = R._mots_adresse("3 chemin de la citerne 97417 la montagne")
    assert voie == ["citerne"] and commune == ["montagne"] and cp == "97417"
    voie, commune, cp = R._mots_adresse("777 avenue bidon a gotham")
    assert voie == ["bidon"] and commune == ["gotham"] and cp is None


def _stub_sugg(mapping):
    """Bouchon de `_sugg_adresse` : rend les candidates pour certaines requêtes relaxées, [] sinon."""
    def _s(db, q, n):
        return mapping.get(q.strip(), [])
    return _s


def test_resoudre_adresse_rejette_voie_et_commune_bidon(monkeypatch):
    """B-5 (CH-B-M5) — « 777 avenue bidon à Gotham » ne doit PLUS matcher une avenue réelle d'une autre
    commune sur le seul numéro. Avant : kind='candidats' (présentées comme des correspondances) ;
    après : kind='introuvable' (honnête), avec éventuellement des pistes proches."""
    from labuse.api import recherche
    # la relaxe tombe sur « 777 avenue » → l'omnibox rend des avenues réelles de Saint-André
    cands = [{"idu": "97409000BI0232", "label": "781 Avenue de Bourbon", "sub": "97440 Saint-André"},
             {"idu": "97409000BI0240", "label": "782 Avenue de Bourbon", "sub": "97440 Saint-André"}]
    monkeypatch.setattr(recherche, "_sugg_adresse", _stub_sugg({"777 avenue": cands}))
    res = R._resoudre_adresse(None, "parcelle au 777 avenue bidon à Gotham")
    assert res is not None and res.kind == "introuvable"
    # aucune candidate « avenue de Bourbon » n'est proposée comme correspondance (voie « bidon » absente)
    assert all(c["idu"] not in {x["idu"] for x in cands} for c in res.candidats)


def test_resoudre_adresse_garde_adresse_reelle(monkeypatch):
    """B-5 — une VRAIE adresse (voie + commune cohérentes) résout toujours à sa parcelle."""
    from labuse.api import recherche
    cand = [{"idu": "97411000BZ1065", "label": "3 Chemin de la Citerne", "sub": "97417 La Montagne"}]
    monkeypatch.setattr(recherche, "_sugg_adresse",
                        lambda db, q, n: cand if "citerne" in q else [])
    res = R._resoudre_adresse(None, "la parcelle au 3 chemin de la Citerne 97417 La Montagne")
    assert res is not None and res.kind == "idu" and res.idu == "97411000BZ1065"


def test_resoudre_adresse_voie_inexistante_echoue(monkeypatch):
    """B-5 — garde conservée : une voie inventée dans une commune inventée échoue proprement."""
    from labuse.api import recherche
    cands = [{"idu": "97418000AA0001", "label": "5 Rue du Coin Tranquille", "sub": "97418 Le Tampon"}]
    monkeypatch.setattr(recherche, "_sugg_adresse", _stub_sugg({"999 rue": cands}))
    res = R._resoudre_adresse(None, "999 rue qui nexiste pas à Trifouillis")
    assert res is not None and res.kind == "introuvable"


# ─────────────────────────── B-6 — zone à cheval citée en entier ───────────────────────────
class _FakeDb:
    def execute(self, *a, **k):
        return SimpleNamespace(first=lambda: (1,))


def test_zone_a_cheval_cite_toutes_les_zones(monkeypatch):
    """B-6 (CH-B-M6) — la réponse zone d'une parcelle à cheval cite TOUTES les zones avec leur part,
    comme la fiche — plus seulement la dominante constructible."""
    from labuse.faisabilite import zone_servie
    zs = SimpleNamespace(a_cheval=True,
                         parts=[{"zone": "U6c", "fam": "U", "pct": 68.0},
                                {"zone": "N", "fam": "N", "pct": 32.0}])
    monkeypatch.setattr(zone_servie, "zone_dominante", lambda db, pid: zs)
    out = RF._ajouter_zones_a_cheval(_FakeDb(), "97415000DV0499", "Zone PLU : Zone U6c (famille U).")
    assert "U6c" in out and "N" in out and "à cheval" in out and "68 %" in out and "32 %" in out


def test_zone_non_a_cheval_inchangee(monkeypatch):
    """B-6 — une parcelle d'une seule zone garde sa réponse courte (aucune mention à cheval)."""
    from labuse.faisabilite import zone_servie
    zs = SimpleNamespace(a_cheval=False, parts=[{"zone": "U5b", "fam": "U", "pct": 100.0}])
    monkeypatch.setattr(zone_servie, "zone_dominante", lambda db, pid: zs)
    base = "Zone PLU : Zone U5b (famille U)."
    assert RF._ajouter_zones_a_cheval(_FakeDb(), "97415000ER0783", base) == base


# ─────────────────────────── CH-B-m5 — relance sans possessif hérite la parcelle ───────────────────────────
def test_est_relance_parcelle():
    assert router._est_relance_parcelle("et le prix au m2 ?")
    assert router._est_relance_parcelle("et les risques ?")
    assert router._est_relance_parcelle("et sa surface ?")
    assert not router._est_relance_parcelle("quelle est la surface de 97415000ER0783 ?")  # pas une relance
    assert not router._est_relance_parcelle("et à Saint-Pierre ?")                        # pas un attribut


def test_relance_herite_idu_du_fil(monkeypatch):
    """CH-B-m5 — « et le prix au m2 ? » après une parcelle établie hérite de son idu, comme « et SON
    prix ». Avant : le routeur la classait en nouveau sujet (prix aussi à la commune) et lâchait l'idu."""
    # le modèle (court-circuité) classe la relance en NOUVEAU sujet sans idu — le pire cas
    monkeypatch.setattr(router.core, "complete", lambda *a, **k: SimpleNamespace(
        degraded=False, reason=None,
        text='{"intent":"QUESTION","params":{},"nouveau_sujet":true,"confidence":0.8}'))
    route = router.classify(None, "et le prix au m2 ?", prior_params={"idu": "97415000ER0783"})
    assert route.params.get("idu") == "97415000ER0783"
    assert route.herites.get("idu") == "97415000ER0783"


def test_relance_ne_detourne_pas_une_commune(monkeypatch):
    """CH-B-m5 — une relance qui NOMME une commune (« et le prix à Saint-Pierre ? ») ne se fait pas
    rattacher à la parcelle du fil."""
    monkeypatch.setattr(router.core, "complete", lambda *a, **k: SimpleNamespace(
        degraded=False, reason=None,
        text='{"intent":"QUESTION","params":{"commune":"Saint-Pierre"},"nouveau_sujet":true}'))
    route = router.classify(None, "et le prix à Saint-Pierre ?", prior_params={"idu": "97415000ER0783"})
    assert route.params.get("idu") is None


# ─────────────────────────── CH-B-m7 — hauteur avec son unité ───────────────────────────
def test_hauteur_valeur_porte_unite_m(db):
    """CH-B-m7 — la valeur de tête de regles_plu_zone porte « m » (« 13 m (faîtage) »), plus le
    flottant nu « 13.0 ». Skip si la zone témoin n'est pas calibrée sur cette base."""
    r = outils.regles_plu_zone(db, commune="Saint-Denis", zone="Ua")
    if not r.ok or not (r.data or {}).get("calibree") or (r.data["regles"].get("hauteur_m") is None):
        pytest.skip("zone Ua de Saint-Denis non calibrée (hauteur) sur cette base")
    assert isinstance(r.valeur, str) and " m" in r.valeur
    assert isinstance(r.data["regles"]["hauteur_m"], (int, float))   # le chiffre brut reste disponible
