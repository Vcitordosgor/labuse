"""EXIGU-FIX-1 — « terrain trop étroit » ne ment plus.

Le moteur ne classait `terrain_exigu` que sur l'effondrement du CONTOUR après reculs (gabarit par
côté), sans vérifier qu'un gros morceau d'un seul tenant restait exploitable → faux positifs sur de
grandes parcelles (ALGO-LECTURE-1 §3.4-A, DEPLOY-GROUPE-3 §D). Le correctif ré-examine, SUR PREUVE
GÉOMÉTRIQUE, le plus grand morceau net d'un seul tenant :
  · exploitable (aire ≥ seuil ET largeur ≥ seuil) → capacité calculée dessus ;
  · prouvé inexploitable (petit/étroit, ou parcelle elle-même ruban) → `terrain_exigu` AVEC preuve ;
  · douteux (parcelle large sans assiette nette) → `assiette_a_verifier` (IGNORANCE, bande NC).

- Tests PURS (sans base) : la nouvelle cause d'ignorance se comporte comme zone_non_resolue partout.
- Tests RÉELS (base locale, marker `reel`) : les 5 témoins + la garantie > 1 000 m².
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from labuse.faisabilite.engine import (cause_certaine, cause_libelle, estimate_capacity)
from labuse.faisabilite.zonage import resolve_zone
from labuse.scoring.scenarios_v2_build import _eligibilite


# ── PURS (sans base) ─────────────────────────────────────────────────────────
def test_assiette_a_verifier_est_une_ignorance():
    """La cause n'est PAS certaine (pas un verdict ferme) → bande NC / « À vérifier »."""
    assert cause_certaine("assiette_a_verifier") is False
    lib = cause_libelle("assiette_a_verifier")
    assert "à vérifier" in lib.lower() and "incomplète" in lib.lower()
    assert "étroit" not in lib.lower() and "exigu" not in lib.lower()


def test_estimate_capacity_sert_a_verifier_jamais_exigu_sur_doute():
    """Assiette vidée MAIS raison 'a_verifier' (ré-examen amont douteux) → cause assiette_a_verifier,
    jamais terrain_exigu / « trop étroit »."""
    f = estimate_capacity(resolve_zone("U1c"), 2000, emprise_geo=(2.0, 3.0),
                          extras={"assiette_vide": "a_verifier"})
    assert f.constructible is False
    assert f.cause == "assiette_a_verifier"
    assert "étroit" not in f.verdict.lower() and "exigu" not in f.verdict.lower()
    assert "vérifier" in f.verdict.lower()


def test_estimate_capacity_exigu_reste_exigu_quand_raison_reculs():
    """Sans le signal 'a_verifier', l'assiette vidée reste terrain_exigu (comportement inchangé)."""
    f = estimate_capacity(resolve_zone("U1c"), 80, emprise_geo=(2.0, 3.0))
    assert f.constructible is False and f.cause == "terrain_exigu"


def test_eligibilite_scenarios_a_verifier_inconnue():
    """scenarios_v2 : la nouvelle cause tombe en eligibility='unknown' (À vérifier), pas 'allowed'."""
    el = _eligibilite("assiette_a_verifier", False, None)
    assert el["eligibility"] == "unknown"
    # garde-fou : une cause inconnue NON ignorance resterait 'allowed' — on vérifie la bascule
    assert _eligibilite("zone_non_resolue:Nh", False, None)["eligibility"] == "unknown"


def test_tous_les_lecteurs_connaissent_assiette_a_verifier():
    """REVUE (3) — TOUT lecteur de `cause` doit traiter `assiette_a_verifier` comme une IGNORANCE
    (« à vérifier » / « non vérifiable » / bande NC), JAMAIS un verdict ferme (« non constructible »,
    « surface/reculs insuffisants », « trop étroit/exigu », « rien à bâtir », « pas de potentiel »),
    ni « éligible/allowed/Estimée ». Ce test ÉCHOUE si un lecteur ne connaît pas la nouvelle cause
    (p. ex. retombe sur un repli générique faux). Couvre : Score (bande NC), carte Analyse LABUSE V2
    (éligibilité), libellé fiche/liste/Copilote, exports (tag court), constructibilité (déclassement),
    motif fiche non-constructible, avertissement verdict servi."""
    from labuse.faisabilite.engine import Faisabilite, cause_certaine, cause_libelle
    from labuse.faisabilite.constructibilite import classify_constructibilite, NON_VERIFIABLE
    from labuse.faisabilite.scenarios import _cause_limite
    from labuse.verdict_servi import _avertissement_non_constructible
    from labuse.scoring.scenarios_v2_build import _eligibilite
    from labuse.scoring.score_labuse import _cause_nc, NC_IGNORANCE, ScoreEntrees
    from labuse.exports.blocs.comparatif import _cause_court

    C = "assiette_a_verifier"
    INTERDITS = ["trop étroit", "trop exigu", "surface ou reculs insuffisants",
                 "rien à bâtir", "pas de potentiel constructible résiduel", "non constructible"]

    def _sans_verdict_ferme(txt: str):
        low = (txt or "").lower()
        for mot in INTERDITS:
            assert mot not in low, f"libellé ferme interdit « {mot} » dans : {txt}"

    f = Faisabilite("UB", "UB", False, "Assiette constructible à vérifier (géométrie).",
                    [], [], [], [], {}, "", cause=C)

    # 1) Score LABUSE → bande NC (« À vérifier »), cause d'ignorance.
    assert cause_certaine(C) is False
    e = ScoreEntrees(parcel_id=1, idu="x", commune="y", residuel_present=True,
                     sdp_residuelle_m2=0, taux_emprise_pct=None, cause=C, capacite_estimee=None,
                     pente_moy_deg=None, aire_m2=1500.0, perimetre_m=160.0, faitage_m=None,
                     au_classe=None, acces=None)
    assert _cause_nc(e) == NC_IGNORANCE

    # 2) Carte « Analyse LABUSE » (scénarios V2) → éligibilité INCONNUE (À vérifier), pas 'allowed'.
    assert _eligibilite(C, False, None)["eligibility"] == "unknown"

    # 3) Libellé fiche / liste / Dossier / Copilote (source unique cause_libelle).
    lib = cause_libelle(C)
    assert "vérifier" in lib.lower() and "incomplète" in lib.lower()
    _sans_verdict_ferme(lib)

    # 4) Exports — tag court.
    court = _cause_court(C)
    assert court == "assiette à vérifier"

    # 5) Constructibilité (candidature/déclassement) → NON vérifiable, surtout PAS « surface insuffisante ».
    label, motif = classify_constructibilite(f)
    assert label == NON_VERIFIABLE, f"déclassée à tort ({label}) au lieu de non-vérifiable"
    assert "vérifier" in motif.lower()
    _sans_verdict_ferme(motif)

    # 6) Motif fiche d'une parcelle non constructible (faisabilite.scenarios).
    _verdict, limite, logement_ok = _cause_limite(f, "UB")
    assert "vérifier" in limite.lower()
    _sans_verdict_ferme(limite)

    # 7) Avertissement du verdict servi (liste/flash) → « à vérifier », jamais « rien à bâtir ».
    av = _avertissement_non_constructible(NON_VERIFIABLE, None, C, None)
    assert av is not None and "vérifier" in av.lower()
    _sans_verdict_ferme(av)


def test_potentiel_batir_assemble_motif_a_verifier():
    """Lecteur `potentiel_batir._assemble` (bloc transformation fiche/Flash/PDF, pur) : pour la cause
    assiette_a_verifier le motif dit « à vérifier » (géométrie), JAMAIS « pas de potentiel » ni
    « surface/reculs insuffisants » ni « trop exigu ». NB : c'est un lecteur de CACHE (il lit
    parcel_residuel.cause + parcel_constructibilite.label) → la constructibilité doit être recalculée
    avec le résiduel pour ces parcelles (cf. rapport §note de déploiement)."""
    from labuse.faisabilite.potentiel_batir import _assemble
    blk = _assemble(sdp_raw=120, cause="assiette_a_verifier", constr_label=None,
                    au_classe=None, zone_fam="U", zone_lib="UB")
    motif = (blk.get("motif") or "").lower()
    assert "vérifier" in motif
    for mot in ("pas de potentiel", "surface ou reculs insuffisants", "trop exigu", "non constructible"):
        assert mot not in motif, f"motif ferme interdit « {mot} » : {blk.get('motif')}"


def test_seam_desactivation_env():
    from labuse.faisabilite.db import _exigu_fix_actif
    old = os.environ.get("LABUSE_EXIGU_FIX")
    try:
        os.environ["LABUSE_EXIGU_FIX"] = "0"
        assert _exigu_fix_actif() is False
        os.environ["LABUSE_EXIGU_FIX"] = "1"
        assert _exigu_fix_actif() is True
        del os.environ["LABUSE_EXIGU_FIX"]
        assert _exigu_fix_actif() is True              # ACTIF par défaut
    finally:
        if old is None:
            os.environ.pop("LABUSE_EXIGU_FIX", None)
        else:
            os.environ["LABUSE_EXIGU_FIX"] = old


# ── RÉELS (base locale servie) ───────────────────────────────────────────────
APP_URL = (os.environ.get("LABUSE_REEL_DATABASE_URL")
           or "postgresql+psycopg://openclaw@localhost:5432/labuse")

# témoin → (surface approx, attendu avec le fix)
TEMOINS_REGAIN = ["97418000AY0416", "97411000DK0447", "97415000CW0252"]
TEMOIN_EXIGU = "97419000AN0398"           # 57 % rouge + 11 % U/AU : morceau net ~5 m², largeur ~0,6 m
# EXPORTS-FIX-3 LOT 1 — l'ancien témoin 97403000AL0258 (11 ha, zone Npnr, U/AU = éclat 0 m²) est
# désormais lu « zone naturelle non constructible » (verdict ferme et correct) et non plus « à
# vérifier » : son doute venait de la sous-zone U/AU fantôme, supprimée par la garde d'aire réelle.
# On repointe le témoin « à vérifier » sur une parcelle large dont l'ambiguïté géométrique SUBSISTE
# (portion U/AU réelle mais aucune assiette nette fiable).
TEMOIN_AVERIFIER = "97415000BN1169"       # 1,9 ha, large (~103 m), aucune assiette nette fiable


def _session():
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine
    try:
        return sessionmaker(bind=make_engine(url=APP_URL), future=True)()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"base réelle indisponible ({type(exc).__name__})")


def _faisa(idu):
    from labuse.faisabilite.db import parcel_faisabilite
    s = _session()
    try:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        if pid is None:
            pytest.skip(f"témoin {idu} absent")
        os.environ["LABUSE_EXIGU_FIX"] = "1"
        return parcel_faisabilite(s, pid)
    finally:
        s.close()


@pytest.mark.reel
@pytest.mark.parametrize("idu", TEMOINS_REGAIN)
def test_temoins_retrouvent_une_capacite(idu):
    res = _faisa(idu)
    assert res is not None
    ctx, f = res
    assert ctx.surface_m2 > 1000
    assert f.cause is None, f"{idu} devrait retrouver une capacité, cause={f.cause}"
    assert (f.fourchette.get("surface_plancher_m2") or 0) > 0


@pytest.mark.reel
def test_temoin_exigu_garde_terrain_exigu_avec_preuve():
    ctx, f = _faisa(TEMOIN_EXIGU)
    assert f.cause == "terrain_exigu"            # morceau net mesuré minuscule → prouvé


@pytest.mark.reel
def test_temoin_doute_passe_a_verifier_jamais_etroit():
    ctx, f = _faisa(TEMOIN_AVERIFIER)
    assert ctx.surface_m2 > 1000
    assert f.cause == "assiette_a_verifier"
    assert "étroit" not in f.verdict.lower()


@pytest.mark.reel
def test_batch_egale_fiche_sur_temoins():
    """batch (compute_residuel) ≡ fiche (parcel_faisabilite) : même cause sur chaque témoin."""
    from labuse.faisabilite.db import parcel_faisabilite
    from labuse.faisabilite.residuel import compute_residuel
    s = _session()
    os.environ["LABUSE_EXIGU_FIX"] = "1"
    try:
        for idu in TEMOINS_REGAIN + [TEMOIN_EXIGU, TEMOIN_AVERIFIER]:
            pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            if pid is None:
                continue
            _ctx, f = parcel_faisabilite(s, pid)
            r = compute_residuel(s, pid)
            cause_batch = r.get("cause") if not r.get("disponible") else None
            assert cause_batch == f.cause, f"{idu}: batch {cause_batch} ≠ fiche {f.cause}"
    finally:
        s.close()


@pytest.mark.reel
def test_aucun_grand_terrain_exigu_sans_preuve():
    """GARANTIE du mandat : aucune parcelle > 1 000 m² ne garde `terrain_exigu` avec le fix sans
    PREUVE géométrique. On lit la trace du ré-examen que le moteur EXPOSE (`ctx.reexamen_exigu`,
    donc avec le recul exact qu'il a utilisé — sous-zone/exceptions comprises, pas une
    reconstruction) : un terrain_exigu conservé ⟹ decision 'exigu' AVEC un morceau net soit mesuré
    sous le seuil d'aire/largeur, soit vide sur une parcelle elle-même en ruban.
    Échantillon borné (perf) : 80 parcelles terrain_exigu(servies) > 1 000 m²."""
    from labuse.faisabilite.db import parcel_faisabilite, LARGEUR_MIN_EXPLOITABLE_M
    from labuse.faisabilite.engine import SEUIL_EXIGU_M2
    s = _session()
    os.environ["LABUSE_EXIGU_FIX"] = "1"
    try:
        pids = [r[0] for r in s.execute(text(
            "SELECT r.parcel_id FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id "
            "WHERE r.cause='terrain_exigu' AND COALESCE(p.contenance_m2,ST_Area(p.geom_2975))>1000 "
            "ORDER BY p.id LIMIT 80")).all()]
        if not pids:
            pytest.skip("aucune parcelle terrain_exigu > 1000 m² servie")
        verifies = 0
        for pid in pids:
            _ctx, f = parcel_faisabilite(s, pid)
            if f.cause != "terrain_exigu":
                continue                                 # régain / à vérifier : plus « trop étroit »
            verifies += 1
            rex = _ctx.reexamen_exigu
            assert rex is not None and rex["decision"] == "exigu", \
                f"pid={pid} garde terrain_exigu sans trace de ré-examen 'exigu' ({rex})"
            # PREUVE géométrique : morceau net mesuré petit/étroit, OU aucun morceau net sur une
            # parcelle elle-même en ruban (largeur < 2·recul+1 ≈ 7 m).
            preuve = (rex["net_m2"] < SEUIL_EXIGU_M2) or (rex["net_larg"] < LARGEUR_MIN_EXPLOITABLE_M) \
                or (not rex["has_net"] and 0 < rex["parc_larg"] < 7.0)
            assert preuve, (f"pid={pid} terrain_exigu sans preuve : net ~{rex['net_m2']:.0f} m², "
                            f"largeur ~{rex['net_larg']:.1f} m, parcelle ~{rex['parc_larg']:.1f} m")
        assert verifies > 0, "aucune parcelle n'est restée terrain_exigu — échantillon non probant"
    finally:
        s.close()
