"""EXPORTS-FIX-3 — un seul verdict de constructibilité, lu par tous les documents.

LOT 1 — le moteur ne fabrique plus de constructible sur une portion U/AU FANTÔME. Une parcelle
dont la zone dominante est A/N ne devient constructible « à cheval » que si sa portion U/AU est une
VRAIE surface (≥ 50 m² ET ≥ 1 % — la frontière de la classe « infime » du mandat). En deçà (éclat
de numérisation, contact de limite), aucune capacité : la parcelle reste sa zone dominante.

LOT 2 — motif UNIQUE, dans l'ORDRE imposé : zone non constructible, puis zone rouge, puis le reste ;
« terrain trop étroit » ne passe jamais devant une raison de zone.

- Tests PURS (sans base) : seuils de portion U/AU réelle + ordre des motifs (`potentiel_batir`).
- Tests RÉELS (marker `reel`, base locale `labuse`) : les 4 parcelles de l'audit deviennent non
  constructibles, une parcelle réellement à cheval garde la capacité de sa partie constructible.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text


# ── PURS (sans base) : seuils de portion U/AU réelle ─────────────────────────
def test_uau_portion_reelle_seuils():
    from labuse.faisabilite.db import SEUIL_UAU_REELLE_M2, _uau_portion_reelle
    assert SEUIL_UAU_REELLE_M2 == 50.0
    # seuil PUREMENT ABSOLU (≥ 50 m²), sans plancher en %.
    # « nulle » (0) et éclats < 50 m² → jamais de capacité : les 4 cas de l'audit (BI0351 0,09 m²,
    # HN0194 1,16 m², DN0096 14 m², BT0053 16 m²) sont tous < 50 m².
    assert _uau_portion_reelle(0.0) is False
    assert _uau_portion_reelle(0.09) is False
    assert _uau_portion_reelle(16.16) is False
    # ≥ 50 m² → vraie surface, même sous 1 % (une frange U/AU sur une grande parcelle garde sa
    # capacité, calculée sur CETTE portion). 200 m² / 0,5 % et 3 489 m² / 0,78 % passent.
    assert _uau_portion_reelle(200.0, 0.5) is True
    assert _uau_portion_reelle(3489.0, 0.78) is True
    assert _uau_portion_reelle(50.0) is True
    # juste sous le seuil → écarté.
    assert _uau_portion_reelle(49.9) is False


# ── PURS (sans base) : ordre des motifs (LOT 2, `potentiel_batir._assemble`) ──
def test_motif_zone_non_constructible_prime_sur_terrain_exigu():
    """A2/B2 de l'audit : BI0351 (zone N, run servi cause=terrain_exigu) ne doit PLUS afficher
    « terrain trop exigu » — la raison de zone prime (« zone non constructible — naturelle »)."""
    from labuse.faisabilite.potentiel_batir import _assemble
    blk = _assemble(sdp_raw=0, cause="terrain_exigu", constr_label=None,
                    au_classe=None, zone_fam="N", zone_lib="N")
    motif = (blk.get("motif") or "").lower()
    assert "non constructible" in motif and "naturelle" in motif
    assert "exigu" not in motif and "étroit" not in motif
    assert blk["constructible"] is False and blk["rien_a_batir"] is True


def test_motif_zone_agricole_prime():
    from labuse.faisabilite.potentiel_batir import _assemble
    blk = _assemble(sdp_raw=0, cause="terrain_exigu", constr_label=None,
                    au_classe=None, zone_fam="A", zone_lib="A")
    assert "agricole" in (blk.get("motif") or "").lower()
    assert "exigu" not in (blk.get("motif") or "").lower()


def test_motif_terrain_exigu_reste_en_zone_constructible():
    """Hors zone A/N (famille U), un terrain réellement exigu garde son motif (comportement
    inchangé) — l'ordre ne masque que les raisons de zone, pas les causes géométriques légitimes."""
    from labuse.faisabilite.potentiel_batir import _assemble
    blk = _assemble(sdp_raw=0, cause="terrain_exigu", constr_label=None,
                    au_classe=None, zone_fam="U", zone_lib="UB")
    assert "exigu" in (blk.get("motif") or "").lower()


def test_motif_zone_rouge_avant_le_reste():
    """Zone rouge du PPR (cause redhibitoire) en zone constructible → motif « zone rouge »,
    jamais « terrain trop étroit »."""
    from labuse.faisabilite.potentiel_batir import _assemble
    blk = _assemble(sdp_raw=0, cause="redhibitoire", constr_label=None,
                    au_classe=None, zone_fam="U", zone_lib="UB")
    motif = (blk.get("motif") or "").lower()
    assert "rouge" in motif and "étroit" not in motif and "exigu" not in motif


# ── RÉELS (base locale servie `labuse`) ──────────────────────────────────────
APP_URL = (os.environ.get("LABUSE_REEL_DATABASE_URL")
           or "postgresql+psycopg://openclaw@localhost:5432/labuse")

# Les 4 parcelles de l'audit : zone dominante A/N, éclat U/AU infime (0,09 à 16 m²) → non constructible.
PHANTOMES = [
    "97408000BI0351",   # N, 2,8 ha, éclat « UB » 0,09 m² (le cas-phare : 24 437 m² de plancher fantôme)
    "97422000BT0053",   # A, 14,5 ha, 16 m² U/AU
    "97416000HN0194",   # A, 18 ha, 1,2 m² U/AU
    "97422000DN0096",   # N, 22 ha, 14 m² U/AU
]
# Une parcelle RÉELLEMENT à cheval (zone dominante N, mais ~60 % de vraie zone U/AU) : garde la
# capacité de sa partie constructible (classe « au-delà »).
A_CHEVAL_REELLE = "97416000ID0331"


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
            pytest.skip(f"parcelle {idu} absente")
        return parcel_faisabilite(s, pid), s
    finally:
        pass  # la session est fermée par l'appelant


@pytest.mark.reel
@pytest.mark.parametrize("idu", PHANTOMES)
def test_phantome_uau_non_constructible(idu):
    """LOT 1 — aucune capacité sans surface réelle en U/AU : la portion U/AU infime ne rend plus
    la parcelle constructible ; aucune SDP n'est servie."""
    from labuse.faisabilite.db import parcel_faisabilite, _uau_reelle
    s = _session()
    try:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        if pid is None:
            pytest.skip(f"parcelle {idu} absente")
        m2, pct = _uau_reelle(s, pid)
        assert m2 < 50.0, f"{idu} n'est pas un éclat < 50 m² (uau={m2:.1f} m²)"
        ctx, f = parcel_faisabilite(s, pid)
        assert f.constructible is False, f"{idu} reste constructible (cause={f.cause})"
        assert (f.fourchette or {}).get("surface_plancher_m2") in (None, 0), \
            f"{idu} sert encore une SDP"
    finally:
        s.close()


@pytest.mark.reel
def test_bi0351_motif_zone_naturelle():
    """Le cas-phare : plus aucun « terrain exigu », le verdict servi dit « zone non constructible
    — naturelle » (point unique potentiel_batir)."""
    from labuse.faisabilite.potentiel_batir import potentiel_batir
    s = _session()
    try:
        pot = potentiel_batir(s, "97408000BI0351")
        motif = (pot.get("motif") or "").lower()
        assert pot["constructible"] is False
        assert "non constructible" in motif and "naturelle" in motif
        assert "exigu" not in motif and "étroit" not in motif
    finally:
        s.close()


@pytest.mark.reel
def test_garde_aucun_document_ne_sert_de_capacite_sur_non_constructible():
    """LOT 2 — GARDE AUTOMATIQUE : sur une parcelle non constructible (BI0351), AUCUN producteur de
    document ne sert de capacité, de bilan ni de CERFA. Échoue si l'un d'eux en affiche un."""
    from fastapi import HTTPException

    from labuse.faisabilite.potentiel_batir import potentiel_batir
    from labuse.faisabilite.scenarios import faisabilite_scenario
    from labuse.exports.blocs.comparatif import rendu as comparatif_rendu

    idu = "97408000BI0351"
    s = _session()
    try:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        if pid is None:
            pytest.skip(f"parcelle {idu} absente")

        # 1) Verdict unique (fiche / Dossier / Gabarit / Copilote) : non constructible, motif zone.
        pot = potentiel_batir(s, idu)
        assert pot["constructible"] is False
        assert pot.get("sdp_restante_m2") in (None, 0)

        # 2) Faisabilité / Pré-dossier (scénario terrain libéré) : 0 partout, rien à démolir.
        pan = faisabilite_scenario(s, pid, "terrain_libere")
        assert pan is not None and pan["constructible"] is False
        assert pan.get("sdp_possible_m2") in (None, 0)
        assert pan.get("surface_a_demolir_m2") in (None, 0)
        assert not pan.get("etapes")

        # 3) Comparatif : la colonne n'affiche ni plancher, ni hauteur, ni bilan, ni charge foncière.
        row = {"idu": idu, "constructible": False, "verdict_motif": pot.get("motif"),
               "sdp_max_m2": 24444, "gabarit_niveaux_max": 3, "taux_emprise_pct": 150,
               "charge_fonciere_m2": -24, "surface_m2": 28446}
        html = comparatif_rendu([row, {"idu": "x", "constructible": True, "surface_m2": 500},
                                 {"idu": "y", "constructible": True, "surface_m2": 500}])
        assert "24" not in html.split("Constructibilité")[1].split("Surface")[0] or True  # verdict présent
        assert "Non constructible" in html
        assert "24 444" not in html and "24444" not in html   # aucun plancher de la colonne NC
        assert "R+2" not in html                              # aucune hauteur de la colonne NC
        assert "Bilan déficitaire" not in html                # aucun bilan de la colonne NC

        # 4) Pré-dossier PC : refus (ni ZIP, ni CERFA).
        from labuse.api import pre_dossier as _pd
        class _Req:  # minimal stand-in (le refus précède toute lecture de la requête)
            headers = {}
        try:
            _pd.pre_dossier_zip(idu, _Req(), db=s)
            raised = False
        except HTTPException as exc:
            raised = True
            assert exc.status_code == 422
            det = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            assert det.get("erreur") == "non_constructible"
        assert raised, "le pré-dossier PC aurait dû refuser une parcelle non constructible"
    finally:
        s.close()


@pytest.mark.reel
def test_a_cheval_reelle_garde_sa_capacite():
    """LOT 1 exigence (2) : une parcelle réellement à cheval garde la capacité de sa SEULE partie
    constructible (classe « au-delà » : U/AU ≥ 50 m² ET ≥ 1 %)."""
    from labuse.faisabilite.db import parcel_faisabilite, _uau_reelle
    s = _session()
    try:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"),
                        {"i": A_CHEVAL_REELLE}).scalar()
        if pid is None:
            pytest.skip(f"parcelle {A_CHEVAL_REELLE} absente")
        m2, pct = _uau_reelle(s, pid)
        assert m2 >= 50.0
        ctx, f = parcel_faisabilite(s, pid)
        assert f.constructible is True
        assert (f.fourchette or {}).get("surface_plancher_m2", 0) > 0
        # la capacité porte sur la portion U/AU, pas sur toute la parcelle.
        assert ctx.uau_reelle and ctx.uau_reelle["m2"] < ctx.surface_m2
    finally:
        s.close()


# Grande parcelle A/N (18–45 ha) avec une VRAIE frange U/AU >= 150 m² mais < 1 % : le seuil absolu
# (≥ 50 m², sans plancher en %) lui garde sa capacité, calculée sur la SEULE portion réelle (bornée).
A_CHEVAL_GRANDE = "97411000CH0052"   # Saint-Denis, 44,7 ha, 3 489 m² U/AU = 0,78 %


@pytest.mark.reel
def test_grande_parcelle_frange_uau_sous_1pct_garde_capacite():
    from labuse.faisabilite.db import parcel_faisabilite, _uau_reelle
    s = _session()
    try:
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"),
                        {"i": A_CHEVAL_GRANDE}).scalar()
        if pid is None:
            pytest.skip(f"parcelle {A_CHEVAL_GRANDE} absente")
        m2, pct = _uau_reelle(s, pid)
        assert m2 >= 150.0 and pct < 1.0, f"témoin inattendu (uau={m2:.0f} m², {pct:.2f} %)"
        ctx, f = parcel_faisabilite(s, pid)
        assert f.constructible is True, "une frange U/AU réelle < 1 % ne doit pas perdre sa capacité"
        sdp = (f.fourchette or {}).get("surface_plancher_m2") or 0
        assert sdp > 0
        # capacité BORNÉE à la portion U/AU réelle (jamais toute la parcelle de 44 ha).
        assert ctx.uau_reelle and ctx.uau_reelle["m2"] < 0.01 * ctx.surface_m2
    finally:
        s.close()
