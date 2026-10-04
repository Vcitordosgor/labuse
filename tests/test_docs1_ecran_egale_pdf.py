"""DOCS-1 (Lot D) — « écran = PDF » + verrou étendu aux 3 nouveaux documents.

Chaque document est le MIROIR de son écran : il rend le résultat de l'endpoint, sans recalcul. Deux
garanties, sur les témoins du mandat :
  1. VERROU (V5d/V5f étendu) : tout nombre imprimé se rattache à une donnée du registre — provenance
     .fuites() == [] (le contexte porte le résultat de l'outil, rattaché à sa donnée-tête).
  2. ÉCRAN = PDF : les valeurs servies par l'endpoint (gabarit : zone/hauteur ; Comparer : surface ;
     Étude de zone : population) se RETROUVENT imprimées (aucune valeur silencieusement perdue).
Et le Gabarit REFUSE de se générer quand le calcul est incomplet (zone A/N) → DocumentNonEtablissable.

Marqué `local` : lit la base APPLICATIVE réelle (les témoins y portent toutes leurs couches).
"""
from __future__ import annotations

import os

import pytest

from labuse.exports import builder, provenance

pytestmark = pytest.mark.local

GABARIT_SERVIE = "97415000BW0102"     # Saint-Paul — gabarit calculable
GABARIT_BLOQUEE = "97415000AB0001"    # zone A/N — « Calcul incomplet » → refus
COMPARATIF = ["97415000CV1201", "97415000CV1498", "97415000CV1289"]
ZONE_IDU, ZONE_RAYON = "97402000AB1117", 2.0


@pytest.fixture(autouse=True)
def _base_reelle():
    """Rebranche l'engine de l'app sur la base APPLICATIVE réelle (LABUSE_APP_DATABASE_URL) le temps
    du test, puis restaure — même patron que test_circuit_provenance."""
    from labuse import db as db_mod
    app_url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not app_url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent — base applicative réelle inconnue")
    ancien_eng, ancien_sess = db_mod._engine, db_mod._Session
    db_mod._engine = db_mod.make_engine(app_url)
    db_mod._Session = None
    try:
        yield
    finally:
        db_mod._engine, db_mod._Session = ancien_eng, ancien_sess


def _printed(html: str) -> set[int]:
    """Les nombres (arrondis) RÉELLEMENT imprimés dans le document."""
    return {round(n) for n, _ in provenance.nombres_imprimes(provenance._texte_de(html))}


def _no_fuite(tag: str, res) -> None:
    fu = provenance.fuites(tag, res.valeurs, res.html, res.contexte)
    assert not fu, f"{tag} — nombres imprimés hors registre :\n" + "\n".join(
        f"  {f['nombre']:g} — « {f['contexte']} »" for f in fu)


def test_gabarit_ecran_egale_pdf_et_verrou():
    from labuse.db import session_scope
    from labuse.gabarit.builder import build_gabarit_input
    from labuse.gabarit.engine import compute_gabarit
    with session_scope() as s:
        b = build_gabarit_input(s, GABARIT_SERVIE)
        if b is None or b.blocking:
            pytest.skip("témoin gabarit non calculable aujourd'hui (données évoluées)")
        gr = compute_gabarit(b.input)
        if gr.status != "ok":
            pytest.skip("témoin gabarit incomplet aujourd'hui (données évoluées)")
        res = builder.construire_gabarit(s, GABARIT_SERVIE)
    _no_fuite(f"{GABARIT_SERVIE}/gabarit", res)              # VERROU
    nums = _printed(res.html)                                 # ÉCRAN = PDF
    if gr.zoneImplantationM2 is not None:
        assert round(gr.zoneImplantationM2) in nums, "zone d'implantation absente du PDF"
    if isinstance(gr.hauteurReglementaireM, (int, float)):
        assert round(gr.hauteurReglementaireM) in nums, "hauteur réglementaire absente du PDF"


def test_gabarit_refuse_si_incomplet():
    """Zone A/N → le Gabarit NE se génère PAS (DocumentNonEtablissable avec le message du mandat)."""
    from labuse.db import session_scope
    with session_scope() as s:
        from labuse.gabarit.builder import build_gabarit_input
        b = build_gabarit_input(s, GABARIT_BLOQUEE)
        if b is not None and not b.blocking:
            from labuse.gabarit.engine import compute_gabarit
            if compute_gabarit(b.input).status == "ok":
                pytest.skip("le témoin bloqué est calculable aujourd'hui (données évoluées)")
        with pytest.raises(builder.DocumentNonEtablissable) as exc:
            builder.construire_gabarit(s, GABARIT_BLOQUEE)
    assert "non calculable" in exc.value.manques[0]["libelle"]


def test_comparatif_ecran_egale_pdf_et_verrou():
    from labuse.db import session_scope
    from labuse.api.app import compare
    with session_scope() as s:
        data = compare(idus=",".join(COMPARATIF), db=s)
        rows = data.get("parcels") or []
        if len(rows) < 2:
            pytest.skip("moins de 2 témoins Comparatif présents aujourd'hui")
        res = builder.construire_comparatif(COMPARATIF, rows)
    _no_fuite("comparatif", res)                              # VERROU (paysage + 17 lignes)
    nums = _printed(res.html)                                  # ÉCRAN = PDF
    for r in rows:
        if r.get("surface_m2"):
            assert round(r["surface_m2"]) in nums, f"surface de {r.get('idu')} absente du PDF"


def test_etude_zone_ecran_egale_pdf_et_verrou():
    from labuse.db import session_scope
    from labuse.api.app import EtudeZoneIn, etude_zone
    with session_scope() as s:
        z = etude_zone(EtudeZoneIn(idu=ZONE_IDU, rayon_km=ZONE_RAYON), db=s)
        res = builder.construire_etude_zone(ZONE_IDU, ZONE_RAYON, z,
                                            '<div class="zone-map-ph">Carte</div>')
    _no_fuite(f"{ZONE_IDU}/etude-zone", res)                  # VERROU (7 sections)
    nums = _printed(res.html)                                  # ÉCRAN = PDF
    hab = (z.get("population") or {}).get("habitants")
    if isinstance(hab, (int, float)) and hab:
        assert round(hab) in nums, "population absente du PDF"
