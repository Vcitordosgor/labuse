#!/usr/bin/env python3
"""PLU-CALIBRAGE-8 (oct.) Lot A — inventaire des zones constructibles (U/AU) sans gabarit servable.

Lecture seule. Pour chaque (commune, zone_lib) portée par des parcelles en famille U/AU, reproduit
EXACTEMENT la décision de blocage AU NIVEAU ZONE du moteur gabarit (`gabarit/builder.py`) — la seule
part « donnée PLU » (E-C2), indépendante de la géométrie par parcelle (façade/limites/multi-zone).

Une zone est « servable » (gabarit non bloqué au niveau zone) ssi :
  - resolve_zone ≠ None (pas le mode strict sans hit),
  - pas de `regle_non_validee` (aucune feuille SDP `propose` portant une valeur),
  - `calibree` = True (pas d'estimation générique),
  - pas de silence total (zone sans règles propres ET renvoi non résolu),
  - hauteur exploitable : faîtage OU égout chiffré, OU faîtage validé non chiffré (prospect/forme),
  - emprise exploitable : CES chiffré OU silence prouvé (feuille `absent`).

(Les reculs ne bloquent PAS le gabarit — builder.py ne les érige pas en gate ; ils ne servent qu'au
dessin s'ils sont présents.) Les parcelles « à potentiel » = `sdp_residuelle_m2 > 0` dans le run servi.

Sortie : JSON {run, zones:[...], totaux}. `--md` écrit aussi un tableau Markdown trié par potentiel.
"""
from __future__ import annotations

import json
import sys

from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.zonage import resolve_zone, _ref_u_code as _ref_u
from labuse.plu.destinations import regles_zone, reglement_meta
from labuse.gabarit.builder import _feuille_absente, _feuille_forme_hors_schema, _num

RUN = "q_v18"


def _diag_hauteur(reg: dict) -> str:
    """Pourquoi la hauteur n'est pas exploitable (zone calibrée mais pas de he/hf chiffré)."""
    h = reg.get("hauteur") or {}
    if not h:
        return "aucune hauteur au règlement transcrit"
    for cle in ("faitage", "egout"):
        leaf = h.get(cle)
        if isinstance(leaf, dict):
            if leaf.get("plage"):
                return "hauteur en plage / table graphique par secteur (hors schéma)"
            if str(leaf.get("statut")) == "valide" and not isinstance(leaf.get("m"), (int, float)):
                return "hauteur validée mais non chiffrée (prospect L≥H / forme)"
            if str(leaf.get("statut")) == "propose":
                return "hauteur en feuille propose (non validée)"
    if all((h.get(c) or {}).get("absent") for c in ("faitage", "egout") if h.get(c)):
        return "hauteur absente du règlement (silence)"
    return "hauteur non exploitable"


def classer(commune: str, zone: str) -> tuple[bool, str, str]:
    """(servable, cause_moteur, cause_mandat). cause_mandat ∈ {absente_yaml, feuille_propose,
    forme_non_modelisee, zone_inconnue_gpu, renvoi_au_u_absent, silence_total, ''}."""
    reg = regles_zone(commune, zone) or {}
    zr = resolve_zone(zone, commune)
    if zr is None:
        return False, "zone hors calibrage PLU (mode strict)", "absente_yaml"
    if getattr(zr, "regle_non_validee", None):
        return False, f"règle PLU non validée (propose) : {zr.regle_non_validee}", "feuille_propose"
    if not getattr(zr, "calibree", False):
        # calibree=False a DEUX causes distinctes :
        #  - pas de bloc `regles` du tout → zone absente du YAML (ou renvoi AU→U non calibré) ;
        #  - un bloc `regles` existe MAIS pas de hauteur exploitable → repli générique (_zone_generique)
        #    = forme non modélisée (table graphique, prospect, silence) : la vraie cause September.
        if reg:
            return False, f"calibrée partielle, repli générique — {_diag_hauteur(reg)}", "forme_non_modelisee"
        cm = "renvoi_au_u_absent" if _ref_u(zone) else "absente_yaml"
        return False, f"PLU non calibré pour la zone {zone} (estimation générique, zone absente du YAML)", cm

    emp = _num(getattr(zr, "emprise_sol_pct", None))
    haut = _num(getattr(zr, "hf_m", None))
    egout = _num(getattr(zr, "he_m", None))
    recul_voie = _num(getattr(zr, "recul_voirie_m", None))
    recul_sep = _num(getattr(zr, "recul_limites_sep_m", None))
    if recul_voie is None and getattr(zr, "recul_voirie_alignement", False):
        recul_voie = 0.0
    if recul_sep is None and getattr(zr, "recul_limites_alignement", False):
        recul_sep = 0.0
    via_renvoi = getattr(zr, "via_renvoi", None)
    propre = bool(regles_zone(commune, zone))

    silence_total = (not propre and not via_renvoi and emp is None and haut is None
                     and recul_voie is None and recul_sep is None)
    if silence_total:
        # AU dont le renvoi U n'a rien ramené = renvoi AU→U absent ; sinon silence total pur
        cm = "renvoi_au_u_absent" if zone[:2].upper().startswith("AU") or zone[:1].isdigit() else "silence_total"
        return False, "sans règles d'implantation propres (silence total / renvoi non résolu)", cm

    haut_ok = (haut is not None or egout is not None
               or _feuille_forme_hors_schema(commune, zone, "hauteur", "faitage", "m"))
    emp_ok = emp is not None or _feuille_absente(commune, zone, "emprise_sol", "ces")

    causes = []
    if not haut_ok:
        causes.append(f"hauteur réglementaire non validée ({_diag_hauteur(reg)})")
    if not emp_ok:
        causes.append("emprise (CES) non réglementée / non validée")
    if not causes:
        return True, "servable", ""
    return False, " ; ".join(causes), "forme_non_modelisee"


def main():
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT substr(p.idu,1,5) insee, p.commune, z.zone_lib, z.zone_fam, count(*) n, "
            "count(*) FILTER (WHERE sc.sdp_residuelle_m2 > 0) n_pot "
            "FROM parcel_zone_plu z JOIN parcels p ON p.idu = z.idu "
            "LEFT JOIN score_labuse sc ON sc.idu = z.idu AND sc.run_label = :run "
            "WHERE z.zone_fam IN ('U','AU') "
            "GROUP BY insee, p.commune, z.zone_lib, z.zone_fam"
        ), {"run": RUN}).fetchall()

    zones = []
    for insee, commune, zone_lib, zone_fam, n, n_pot in rows:
        servable, cause_moteur, cause_mandat = classer(commune, zone_lib)
        if servable:
            continue
        meta = reglement_meta(commune) or {}
        zones.append({
            "insee": insee, "commune": commune, "zone": zone_lib, "fam": zone_fam,
            "n_parcelles": int(n), "n_potentiel": int(n_pot or 0),
            "cause_moteur": cause_moteur, "cause": cause_mandat,
            "reglement": meta.get("document"), "millesime": meta.get("millesime"),
            "lu_le": meta.get("lu_le"),
        })
    zones.sort(key=lambda z: (-z["n_potentiel"], -z["n_parcelles"]))

    out = {
        "run": RUN,
        "n_zones_non_servables": len(zones),
        "n_parcelles_touchees": sum(z["n_parcelles"] for z in zones),
        "n_potentiel_touche": sum(z["n_potentiel"] for z in zones),
        "par_cause": {},
        "zones": zones,
    }
    for z in zones:
        c = out["par_cause"].setdefault(z["cause"], {"zones": 0, "parcelles": 0, "potentiel": 0})
        c["zones"] += 1
        c["parcelles"] += z["n_parcelles"]
        c["potentiel"] += z["n_potentiel"]

    if "--md" in sys.argv:
        print(f"Run servi : **{RUN}** · zones non servables : **{len(zones)}** · "
              f"parcelles touchées : **{out['n_parcelles_touchees']}** · "
              f"à potentiel : **{out['n_potentiel_touche']}**\n")
        print("| # | Commune | Zone | Fam | Parcelles | À potentiel | Cause (mandat) | Détail moteur | Règlement (millésime) |")
        print("|---|---|---|---|--:|--:|---|---|---|")
        for i, z in enumerate(zones, 1):
            print(f"| {i} | {z['commune']} | {z['zone']} | {z['fam']} | {z['n_parcelles']} | "
                  f"{z['n_potentiel']} | {z['cause']} | {z['cause_moteur']} | "
                  f"{z['reglement'] or '—'} ({z['millesime'] or '?'}) |")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
