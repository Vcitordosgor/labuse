#!/usr/bin/env python3
"""GABARIT-AUDIT-COUVERTURE (suite) — calibration des zones U par commune (lecture seule).

Pour chaque commune (23, hors Saint-Philippe RNU), énumère les codes de zone U réellement portés par
des parcelles (`parcel_zone_plu.zone_fam='U'`) avec le nombre de parcelles, et dit, via `regles_zone`
(config validée) + `resolve_zone`, si chaque zone a une règle CHIFFRÉE VALIDÉE pour : retrait voie,
retrait limites séparatives, hauteur, CES. Compte les zones U sans AUCUNE règle et les parcelles
concernées. N'écrit rien.
"""
from __future__ import annotations

import json
import sys

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.zonage import resolve_zone
from labuse.plu.destinations import regles_zone


def _num(x):
    return x if isinstance(x, (int, float)) else None


def familles(commune: str, zone: str) -> dict:
    """Les 4 familles : chiffrée validée ? (valeur ou None). Fondé sur regles_zone (statut) + resolve_zone."""
    reg = regles_zone(commune, zone) or {}
    zr = resolve_zone(zone, commune)
    ret = (reg.get("retraits") or {})
    haut = (reg.get("hauteur") or {})
    emp = (reg.get("emprise_sol") or {})

    def valide(leaf):
        return isinstance(leaf, dict) and str(leaf.get("statut")) == "valide"

    voie_leaf = ret.get("voie") or {}
    sep_leaf = ret.get("limites_separatives") or ret.get("limites") or {}
    ces_leaf = emp.get("ces") or {}

    def stat(valide_flag, num, align=False, silence=False):
        """'chiffree' (nombre / alignement / silence prouvé) · 'validee' (valide sans nombre) · '—'."""
        if num is not None or align or silence:
            return "chiffree"
        if valide_flag:
            return "validee"
        return "—"

    voie_num = _num(getattr(zr, "recul_voirie_m", None)) if zr else None
    sep_num = _num(getattr(zr, "recul_limites_sep_m", None)) if zr else None
    haut_num = _num(getattr(zr, "hf_m", None)) if zr else None
    ces_num = _num(getattr(zr, "emprise_sol_pct", None)) if zr else None
    voie_stat = stat(valide(voie_leaf), voie_num, align=bool(getattr(zr, "recul_voirie_alignement", False)) if zr else False)
    sep_stat = stat(valide(sep_leaf), sep_num, align=bool(getattr(zr, "recul_limites_alignement", False)) if zr else False)
    haut_stat = stat(valide(haut.get("faitage") or {}) or valide(haut.get("egout") or {}), haut_num)
    ces_silence = isinstance(ces_leaf, dict) and ces_leaf.get("absent") is True
    ces_stat = stat(valide(ces_leaf), ces_num, silence=ces_silence)
    stats = [voie_stat, sep_stat, haut_stat, ces_stat]
    return {
        "voie": voie_num, "voie_stat": voie_stat,
        "sep": sep_num, "sep_stat": sep_stat,
        "haut": haut_num, "haut_stat": haut_stat,
        "ces": ces_num, "ces_stat": ces_stat,
        "calibree": bool(getattr(zr, "calibree", False)) if zr else False,
        "n_rubriques": len(reg),
        "any_rule": any(x != "—" for x in stats),          # au moins une famille validée (chiffrée ou non)
        "toutes_chiffrees": all(x == "chiffree" for x in stats),
    }


def main():
    with session_scope() as s:
        communes = s.execute(text(
            "SELECT DISTINCT substr(idu,1,5) insee, commune FROM parcels ORDER BY commune")).fetchall()
        out = {}
        for insee, commune in communes:
            rows = s.execute(text(
                "SELECT zone_lib, count(*) n FROM parcel_zone_plu "
                "WHERE substr(idu,1,5)=:i AND zone_fam='U' GROUP BY zone_lib ORDER BY n DESC"),
                {"i": insee}).fetchall()
            if not rows:
                continue
            zones = []
            for zone_lib, n in rows:
                f = familles(commune, zone_lib)
                f.update({"zone": zone_lib, "n": n})
                zones.append(f)
            n_zones = len(zones)
            no_rule = [z for z in zones if not z["any_rule"]]
            non_cal = [z for z in zones if not z["calibree"]]
            incomplet = [z for z in zones if z["calibree"] and not z["toutes_chiffrees"]]
            out[commune] = {
                "insee": insee,
                "n_parc_u": sum(z["n"] for z in zones),
                "n_zones": n_zones,
                "n_zones_sans_regle": len(no_rule),
                "n_parc_sans_regle": sum(z["n"] for z in no_rule),
                "n_zones_non_calibree": len(non_cal),
                "n_parc_non_calibree": sum(z["n"] for z in non_cal),
                "n_zones_incompletes": len(incomplet),
                "n_parc_incompletes": sum(z["n"] for z in incomplet),
                "zones": zones,
            }
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
