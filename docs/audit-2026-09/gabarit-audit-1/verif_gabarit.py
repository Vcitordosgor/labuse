#!/usr/bin/env python
"""GABARIT-AUDIT-1 — sonde lecture seule.

Pour chaque parcelle : exécute le MÊME moteur que l'endpoint /outils/gabarit
(build_gabarit_input + compute_gabarit) et, en regard, le moteur résiduel
(parcel_faisabilite) + la contenance cadastrale + la hauteur d'en-tête fiche
(niveaux × étage). Aucune écriture.

Lancer :  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
          PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python \
          docs/audit-2026-09/gabarit-audit-1/verif_gabarit.py
"""
import json
from sqlalchemy import text
from labuse.db import session_factory
from labuse.gabarit.builder import build_gabarit_input
from labuse.gabarit.engine import compute_gabarit
from labuse.faisabilite.db import parcel_faisabilite

IDUS = [
    "97415000BW0102",  # Vic — Saint-Paul U6c — à cheval A/N
    "97411000BZ1065",  # Vic — Saint-Denis Uh — U mono
    "97411000AV0055",  # U simple #1 (Uh, hors PPR)
    "97411000AV0056",  # U simple #2 (Uh, hors PPR)
    "97415000AD0242",  # à cheval #2 (U1g + N)
    "97415000AC0071",  # à cheval #3 (U1g + A)
    "97411000AH0022",  # PPR rouge #1 (Ua)
    "97411000AW0732",  # PPR rouge #2 (Ua)
    "97411000HB0374",  # enclave E1 réelle (Ui, séparatives seules, aucune façade voie)
    "97411000AK0069",  # Ud Saint-Denis — hauteur non chiffrée (prospect)
]

Session = session_factory()


def cadastre(db, idu):
    r = db.execute(text(
        "SELECT id, surface_m2, "
        "round(ST_Area(geom_2975)::numeric,1) AS aire_2975 "
        "FROM parcels WHERE idu=:i"), {"i": idu}).mappings().first()
    return r


def residuel_row(db, pid):
    r = db.execute(text(
        "SELECT sdp_residuelle_m2, taux_emprise_pct, pct_potentiel, cause "
        "FROM parcel_residuel WHERE parcel_id=:p"), {"p": pid}).mappings().first()
    return dict(r) if r else None


def run():
    db = Session()
    out = []
    for idu in IDUS:
        rec = {"idu": idu}
        cad = cadastre(db, idu)
        if not cad:
            rec["erreur"] = "parcelle inconnue"
            out.append(rec)
            continue
        pid = cad["id"]
        rec["cadastre_surface_m2"] = round(float(cad["surface_m2"]), 1)
        rec["cadastre_aire_2975"] = float(cad["aire_2975"])

        # --- moteur GABARIT (endpoint) --------------------------------------
        build = build_gabarit_input(db, idu)
        if build is None:
            rec["gabarit"] = {"status": "parcelle inconnue"}
        elif build.blocking:
            rec["gabarit"] = {"status": "incomplete", "blocking": build.blocking,
                              "zone": build.raccordement.get("zone")}
        else:
            res = compute_gabarit(build.input)
            reculs = {}
            for ar in res.appliedRules:
                if ar.category in ("setback",) or (ar.ruleId or "").startswith("limite"):
                    reculs.setdefault(ar.ruleId or ar.label, ar.value)
            rec["gabarit"] = {
                "status": res.status,
                "zone": build.raccordement.get("zone"),
                "multizone": build.raccordement.get("multizone"),
                "surfaceParcelleM2": res.surfaceParcelleM2,
                "zoneImplantationM2": res.zoneImplantationM2,
                "plafondEmpriseM2": res.plafondEmpriseM2,
                "plafondEmpriseStatus": res.plafondEmpriseStatus,
                "hauteurReglementaireM": res.hauteurReglementaireM,
                "hauteurStatus": res.hauteurStatus,
                "hauteurSource": (res.hauteurSource.article if res.hauteurSource else None),
                "coverage": {"reculs": res.coverage.reculs, "hauteur": res.coverage.hauteur,
                             "emprise": res.coverage.emprise, "risques": res.coverage.risques},
                "reculs_appliques": [
                    {"rule": ar.ruleId, "label": ar.label, "value": ar.value, "unit": ar.unit}
                    for ar in res.appliedRules if (ar.ruleId or "").startswith("limite")],
                "nonIntegres": [n.label for n in res.nonIntegratedRules],
                "exclusions": [ar.label for ar in res.appliedRules if ar.category == "exclusion"],
            }

        # --- moteur RESIDUEL (fiche / parcel_residuel) ----------------------
        rec["residuel_servi"] = residuel_row(db, pid)
        try:
            fa = parcel_faisabilite(db, pid, assiette_clippee=False)
            if fa:
                _ctx, f = fa
                fr = f.fourchette or {}
                rec["faisa_live"] = {
                    "zone": getattr(_ctx, "zone", None), "a_cheval": getattr(_ctx, "a_cheval", None),
                    "emprise_constructible_m2": fr.get("emprise_constructible_m2"),
                    "hauteur_m_entete_fiche": fr.get("hauteur_m"),
                    "niveaux": fr.get("niveaux"),
                    "hauteur_etage_m": fr.get("hauteur_etage_m"),
                }
            else:
                rec["faisa_live"] = None
        except Exception as e:  # noqa
            rec["faisa_live"] = {"erreur": repr(e)}
        out.append(rec)
    db.close()
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
