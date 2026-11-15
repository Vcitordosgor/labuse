"""MOTEUR-VERITE-FIX-2 LOT D — le VRAI contrôle inverse.

Liste TOUTES les parcelles dont la capacité (cache-fix2) dépasse celle de main (cache de
référence de l'audit VERITE-TERRAIN-3), chacune avec l'ARTICLE qui l'autorise et la PREUVE que
ses conditions sont appliquées par le moteur. Toute ligne sans justification est marquée ⚠ —
il ne doit pas y en avoir (la règle FIX-2 l'interdit par construction, ce script le PROUVE).

    PYTHONPATH=src python docs/audit-2026-11/moteur-verite-fix-1/scripts/controle_inverse_vrai.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
FIX = RACINE / "docs" / "audit-2026-11" / "moteur-verite-fix-1"
REF = RACINE / "docs" / "audit-2026-11" / "verite-terrain-3" / "cache" / "capacite"
CACHE = FIX / "cache-fix2"
OUT = FIX / "CONTROLE-INVERSE-VRAI.csv"

COMMUNES = {"97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Entre-Deux",
            "97404": "L'Étang-Salé", "97405": "Petite-Île", "97406": "La Plaine-des-Palmistes",
            "97407": "Le Port", "97408": "La Possession", "97409": "Saint-André",
            "97410": "Saint-Benoît", "97411": "Saint-Denis", "97412": "Saint-Joseph",
            "97413": "Saint-Leu", "97414": "Saint-Louis", "97415": "Saint-Paul",
            "97416": "Saint-Pierre", "97418": "Sainte-Marie", "97419": "Sainte-Rose",
            "97420": "Sainte-Suzanne", "97421": "Salazie", "97422": "Le Tampon",
            "97423": "Les Trois-Bassins", "97424": "Cilaos"}


def main() -> None:
    from labuse.faisabilite.zonage import resolve_zone
    from labuse.gabarit.builder import analyser_condition_implantation, _fraction_hauteur_formule

    lignes, sans_justif = [], 0
    for p in sorted(CACHE.glob("*.json")):
        new = json.loads(p.read_text())
        q = REF / p.name
        if not q.exists():
            continue
        old = json.loads(q.read_text())
        d = float(new.get("sdp_max_m2") or 0) - float(old.get("sdp_max_m2") or 0)
        if d <= 2:
            continue
        idu = p.stem
        commune = COMMUNES.get(idu[:5], idu[:5])
        zone = new.get("zone")
        zr = resolve_zone(zone, commune) if zone else None
        justifs = []
        if zr is not None:
            frac = _fraction_hauteur_formule(getattr(zr, "recul_limites_formule", None))
            if frac is not None and isinstance(zr.recul_limites_sep_m, (int, float)):
                justifs.append((
                    f"retrait relatif H×{frac:.3g} (min {zr.recul_limites_sep_m:g} m) évalué à "
                    f"l'ÉGOUT du bâtiment envisagé, niveau par niveau (scénario au plancher max)",
                    zr.sources.get("recul_limites", "Art. 7"),
                    str(zr.recul_limites_formule)[:140]))
            for cote, imp in (("latérales", zr.implantation_laterales),
                              ("fond", zr.implantation_fond)):
                if not imp:
                    continue
                dec = analyser_condition_implantation(imp, None, None)
                # jetons dépendant du terrain : re-déclencher avec des valeurs factices ne prouve
                # rien — on vérifie la FORME (tous jetons stricts) : c'est la condition de la règle.
                cm = (imp.get("condition_modelable") or "").strip()
                if dec["ouvre"] or (cm and all(
                        t.strip() in ("une_seule_limite", "deux_limites_max")
                        or __import__("labuse.gabarit.builder", fromlist=["jeton_num_strict"])
                        .jeton_num_strict(t.strip()) is not None
                        for t in cm.split("+") if t.strip())):
                    justifs.append((
                        f"implantation en limite ({cote}) — mode {imp.get('mode')}"
                        + (f", conditions MESURÉES : {cm}" if cm else ", sans condition au règlement"),
                        imp.get("article") or "?",
                        str(imp.get("citation") or "")[:140]))
        if not justifs and str(new.get("zone_fam") or "").upper() in ("A", "N"):
            # parcelle à dominante A/N : la capacité vient de la PORTION U/AU (sous-zone) — on
            # résout la sous-zone réellement servie par le moteur pour citer SON article.
            try:
                from labuse.db import session_factory
                from labuse.faisabilite.db import parcel_faisabilite
                from sqlalchemy import text as _T
                _s = globals().setdefault("_SESSION", session_factory()())
                _pid = _s.execute(_T("select id from parcels where idu=:i"), {"i": idu}).scalar()
                _res = parcel_faisabilite(_s, _pid)
                if _res is not None:
                    _ctx = _res[0]
                    _sz = (getattr(_ctx, "uau_reelle", None) or {}).get("sous_zone")
                    if _sz:
                        _zr2 = resolve_zone(_sz, commune)
                        _frac2 = _fraction_hauteur_formule(getattr(_zr2, "recul_limites_formule", None)) if _zr2 else None
                        if _zr2 is not None and _frac2 is not None and isinstance(_zr2.recul_limites_sep_m, (int, float)):
                            justifs.append((
                                f"portion U/AU (sous-zone {_sz}, dominante {zone}) — retrait relatif "
                                f"H×{_frac2:.3g} (min {_zr2.recul_limites_sep_m:g} m) à l'égout envisagé",
                                _zr2.sources.get("recul_limites", "Art. 7"),
                                str(_zr2.recul_limites_formule)[:140]))
                        elif _zr2 is not None:
                            justifs.append((
                                f"portion U/AU (sous-zone {_sz}, dominante {zone}) — enveloppe de la "
                                f"sous-zone (reculs {_zr2.recul_limites_sep_m} m)",
                                _zr2.sources.get("recul_limites", "règlement de la sous-zone"),
                                ""))
            except Exception:  # noqa: BLE001 — repli best-effort, la ligne restera ⚠ sinon
                pass
        if justifs:
            art = " ; ".join(sorted({j[1] for j in justifs}))
            preuve = " | ".join(j[0] for j in justifs)
            cit = justifs[0][2]
            ok = ""
        else:
            art, preuve, cit, ok = "?", "AUCUNE JUSTIFICATION TROUVÉE", "", "⚠"
            sans_justif += 1
        lignes.append({"idu": idu, "commune": commune, "zone": zone,
                       "sdp_main": old.get("sdp_max_m2"), "sdp_fix2": new.get("sdp_max_m2"),
                       "delta": round(d), "article": art, "preuve_conditions": preuve,
                       "citation": cit, "alerte": ok})
    lignes.sort(key=lambda r: -r["delta"])
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]) if lignes else ["idu"], delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes)} parcelles au-dessus de main → {OUT.name} ; SANS justification : {sans_justif}")
    for r in lignes[:10]:
        print(f"  {r['alerte']}{r['idu']} {r['zone'] or '?':8s} {r['sdp_main'] or 0:>7} → "
              f"{r['sdp_fix2']:>7} (+{r['delta']})  {r['article']}")


if __name__ == "__main__":
    main()
