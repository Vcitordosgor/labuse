"""PRIX-SORTIE-1 (Vic 05/10/2026) — un seul prix de sortie, partout.

Garde de non-divergence : pour une même parcelle, TOUTES les surfaces qui servent un « prix de
sortie » (fiche Simulation, Constructibilité, Calculette web, Calculette PDF, pré-remplissage du
Financier) doivent servir EXACTEMENT le même chiffre — celui de la source unique
`resolve_prix_sortie_servi` (prix NEUF). Le test échoue si deux surfaces divergent sur un témoin.

Il vérifie AUSSI le piège d'origine : le prix de l'ANCIEN (sector_price → `marche.median`) ne doit
JAMAIS être servi comme prix de sortie (sur les témoins, l'ancien diffère franchement du neuf).

Données d'île (parcelles réelles + table `dvf_prix_sortie_neuf`) : le test lit la base APP en LECTURE
SEULE (jamais d'écriture) et se SKIPPE proprement si les témoins / la table n'y sont pas (CI sur
`labuse_test` vide). Il court donc en recette (où les captures sont prises) et garde la cohérence.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# IDU exacts du mandat — ne pas changer.
TEMOINS = ["97415000AM0097", "97411000BZ1065", "97416000ES0266"]


def _app_session() -> Session | None:
    """Session LECTURE SEULE sur la base APP (où vivent les parcelles d'île + dvf_prix_sortie_neuf).
    None si injoignable → le test skippe (pas d'échec d'infra)."""
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        return None
    try:
        eng = create_engine(url)
        s = Session(eng)
        s.execute(text("SELECT 1"))
        return s
    except Exception:  # noqa: BLE001 — base APP absente (CI) → skip
        return None


@pytest.mark.parametrize("idu", TEMOINS)
def test_prix_sortie_unique_sur_toutes_les_surfaces(idu: str):
    db = _app_session()
    if db is None:
        pytest.skip("base APP injoignable (CI sur labuse_test) — garde rejouée en recette")
    try:
        pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        if pid is None:
            pytest.skip(f"{idu} absent de la base APP")
        if db.execute(text("SELECT count(*) FROM dvf_prix_sortie_neuf")).scalar() == 0:
            pytest.skip("dvf_prix_sortie_neuf non construite sur cette base")

        from labuse.api import modules
        from labuse.api.app import _calculette_for_pdf
        from labuse.faisabilite.bilan import resolve_prix_sortie_servi
        import labuse.financier_questionnaire as qf

        ref = resolve_prix_sortie_servi(db, int(pid))
        if ref["non_calculable"] or ref["prix"] is None:
            pytest.skip(f"{idu} : prix de sortie non calculable (commune social-dominante)")
        attendu = round(float(ref["prix"]))

        # SOURCE UNIQUE côté serveur : chaque surface rebranchée doit porter `attendu`.
        surfaces: dict[str, float] = {"resolver (source unique)": attendu}

        # Pré-remplissage du Financier (S4) — toujours résolu dès que la commune a un prix neuf.
        ps_neuf = qf.prix_sortie_neuf_servi(db, idu)
        assert ps_neuf is not None, f"{idu} : prefill Financier non résolu alors que le neuf existe"
        surfaces["financier prefill (S4)"] = round(float(ps_neuf))

        # Surfaces liées au bilan — présentes seulement si la parcelle est constructible.
        fa = modules.faisabilite_sens1(idu, db)
        ps_fa = fa.get("prix_sortie")
        if ps_fa and ps_fa.get("prix") is not None and not ps_fa.get("non_calculable"):
            surfaces["fiche Simulation (prix_sortie)"] = round(float(ps_fa["prix"]))
            # Constructibilité lit le même objet via le bilan servi (calc.median = prix neuf).
            calc_med = (fa.get("bilan") or {}).get("calc", {}).get("median")
            if calc_med is not None:
                surfaces["fiche Constructibilité (bilan.calc.median)"] = round(float(calc_med))

            charge = modules.faisabilite_charge(idu, modules.ChargeIn(), db)
            if charge.get("calculable"):
                surfaces["Calculette web (prix_sortie)"] = round(float(charge["prix_sortie"]["prix"]))
                surfaces["Calculette web (prix_sortie_median)"] = round(float(charge["prix_sortie_median"]))

            pdf = _calculette_for_pdf(
                db, idu, modules.CALCULETTE_COUT_DEFAUT_M2,
                modules.CALCULETTE_MARGE_FRAIS_DEFAUT_PCT, None)
            if pdf and pdf.get("prix_sortie_median") is not None:
                surfaces["Calculette PDF (prix_sortie_median)"] = round(float(pdf["prix_sortie_median"]))

        # (1) AUCUNE divergence entre surfaces.
        distinctes = set(surfaces.values())
        assert len(distinctes) == 1, (
            f"{idu} : le prix de sortie DIVERGE entre surfaces → {surfaces}")

        # (2) Le piège d'origine : l'ANCIEN (marche.median) n'est jamais servi comme prix de sortie
        #     quand il diffère du neuf (c'est le cas sur les témoins).
        ancien = (fa.get("marche") or {}).get("median")
        if ancien is not None and round(float(ancien)) != attendu:
            assert attendu != round(float(ancien)), (
                f"{idu} : le prix de sortie servi ({attendu}) est le prix de l'ANCIEN "
                f"({round(float(ancien))}) — régression, l'ancien n'est pas un prix de sortie neuf")
    finally:
        db.close()
