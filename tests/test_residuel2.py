"""RESIDUEL-2 — fin du double retrait (union globale) + qualification du repli legacy.

Deux choses verrouillées :
  1. DOUBLE RETRAIT — le chemin legacy soustrait l'UNION GLOBALE des contraintes certaines
     (ER ∪ EBC ∪ PPR rouge ∪ PEB ∪ DPF ∪ ravine ∪ 50 pas), jamais deux soustractions successives
     dont le chevauchement est retranché deux fois. Propriété : l'emprise « union » est TOUJOURS ≥
     l'emprise de l'ancien double retrait (jamais une régression), stricte là où les contraintes se
     recouvrent. Le seam de mesure `legacy_union=False` rejoue l'ancienne mécanique.
  2. QUALIFICATION — une capacité de repli n'est QUALIFIÉE (`residuel_legacy_qualifie`) que si le
     gabarit n'a bloqué QUE sur des arêtes non qualifiables (ravine/littoral/DPF/micro-arête) : là
     l'inset uniforme + l'union des contraintes applique provablement les règles du cas. Tout motif
     impliquant une règle devinée (recul voie, voie privée, PLU non calibré, CES/hauteur absents,
     multi-zones) laisse la capacité NON qualifiée (`residuel_legacy`).

Les tests `reel` (base servie) : témoins, batch ≡ fiche, propriété du double retrait.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text


# ── 1. Qualification — logique PURE (sans base, jouée au hook) ────────────────────────────────────
def test_repli_qualifiable_seulement_sur_limites_non_qualifiees():
    from labuse.faisabilite.db import _repli_qualifiable

    lim = "Limites de la parcelle non qualifiées (voie / limite séparative) — arête sans voie ni voisin"
    # Qualifié : uniquement des arêtes naturelles non classables.
    assert _repli_qualifiable([lim]) is True
    assert _repli_qualifiable([lim, lim]) is True
    # NON qualifié : toute règle devinée.
    assert _repli_qualifiable(["recul sur voie non réglementé / non validé"]) is False
    assert _repli_qualifiable(["PLU non calibré pour la zone N (estimation générique)"]) is False
    assert _repli_qualifiable(["emprise (CES) non réglementée / non validée"]) is False
    assert _repli_qualifiable(
        ["parcelle sur ≥ 2 zones constructibles distinctes (AUm, Um) : découpage multi-CES non servi"]
    ) is False
    # NON qualifié : mélange limites + règle devinée (le mélange disqualifie).
    assert _repli_qualifiable([lim, "recul sur voie non réglementé / non validé"]) is False
    # NON qualifié : liste vide (compute échoué, build None) — jamais qualifié par défaut.
    assert _repli_qualifiable([]) is False


def test_assiette_gabarit_renvoie_motifs_de_blocage():
    """La porte gabarit renvoie désormais `(gab, blocages)` — la liste de motifs pilote la qualification."""
    import inspect

    from labuse.faisabilite import db

    src = inspect.getsource(db._assiette_gabarit)
    assert "return None, [" in src and "return (build, res), []" in src
    # Le seam de mesure du double retrait existe sans polluer le service (défaut union).
    assert db.parcel_faisabilite.__defaults__ is not None
    assert "legacy_union" in inspect.signature(db.parcel_faisabilite).parameters


def test_union_globale_cablee_dans_la_branche_legacy():
    """La branche legacy soustrait `greve_total` (union) — plus jamais `greve_a + greve_cert`."""
    import inspect

    from labuse.faisabilite import db

    src = inspect.getsource(db.parcel_faisabilite)
    assert "_GREVE_LEGACY_UNION" in src
    assert "base - greve_union" in src
    # L'extra `total_deduit_m2` ne re-somme plus greve_a + greve_cert (double compte d'affichage).
    full = inspect.getsource(db)
    assert "greve_a + greve_cert" not in full


# ── 2. Base réelle — témoins, batch ≡ fiche, propriété du double retrait ──────────────────────────
_TEMOINS = [
    "97411000EH0043", "97411000EI0085", "97403000AL0258", "97411000DH0076",
    "97411000BZ1065", "97410000AK0804", "97403000AM0314", "97403000AM0473",
    "97403000AM0561",
]


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine
    url = (os.environ.get("LABUSE_APP_DATABASE_URL")
           or os.environ.get("LABUSE_DATABASE_URL"))
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL/LABUSE_DATABASE_URL absent")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    yield s
    s.close()


def _cle(d: dict) -> tuple:
    return (d.get("disponible"), d.get("cause"), d.get("sdp_residuelle_m2"),
            d.get("sdp_ecrite"), d.get("emprise_constructible_m2"))


@pytest.mark.reel
@pytest.mark.parametrize("idu", _TEMOINS)
def test_batch_egale_fiche_sur_temoins(session_reelle, idu):
    """Batch (résout la faisabilité) ≡ fiche (faisabilité passée) : même verdict/SDP/emprise."""
    from labuse.faisabilite.db import parcel_faisabilite
    from labuse.faisabilite.residuel import compute_residuel
    s = session_reelle
    pid = s.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"témoin {idu} absent")
    batch = compute_residuel(s, pid)
    fiche = compute_residuel(s, pid, faisa=parcel_faisabilite(s, pid))
    assert _cle(batch) == _cle(fiche), f"{idu} : batch {_cle(batch)} ≠ fiche {_cle(fiche)}"


@pytest.mark.reel
def test_qualification_temoins(session_reelle):
    """EI0085 (multi-zones) et AK0804 (recul voie) restent NON qualifiés ; AM0314/AM0473 (arête
    naturelle seule) sont QUALIFIÉS. La qualification ne se déduit jamais de l'absence de contrainte."""
    from labuse.faisabilite.db import parcel_faisabilite
    s = session_reelle
    attendu = {
        "97403000AM0314": "residuel_legacy_qualifie",
        "97403000AM0473": "residuel_legacy_qualifie",
        "97411000EI0085": "residuel_legacy",
        "97410000AK0804": "residuel_legacy",
    }
    for idu, src in attendu.items():
        pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
        if pid is None:
            pytest.skip(f"témoin {idu} absent")
        res = parcel_faisabilite(s, pid)
        assert res is not None, idu
        assert res[1].fourchette.get("assiette_source") == src, idu


@pytest.mark.reel
@pytest.mark.parametrize("idu", _TEMOINS)
def test_union_jamais_moins_que_double_retrait(session_reelle, idu):
    """Propriété FONDAMENTALE : l'emprise « union globale » (servie) est TOUJOURS ≥ l'emprise de
    l'ancien double retrait — corriger le double compte ne retire jamais de capacité. Pour un gabarit
    le paramètre est sans effet (chemin non legacy) → stricte égalité."""
    from labuse.faisabilite.db import parcel_faisabilite
    s = session_reelle
    pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
    if pid is None:
        pytest.skip(f"témoin {idu} absent")
    new = parcel_faisabilite(s, pid)
    old = parcel_faisabilite(s, pid, legacy_union=False)
    if new is None or old is None:
        pytest.skip(f"{idu} non constructible")
    e_new = float(new[1].fourchette.get("emprise_constructible_m2") or 0.0)
    e_old = float(old[1].fourchette.get("emprise_constructible_m2") or 0.0)
    assert e_new >= e_old - 0.5, f"{idu} : union {e_new} < double retrait {e_old}"
    src = new[1].fourchette.get("assiette_source")
    if src == "gabarit":
        assert abs(e_new - e_old) < 0.5, f"{idu} gabarit : le seam legacy ne doit pas changer l'emprise"
