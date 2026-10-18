#!/usr/bin/env python
"""IMPLANTATION-2 LOT A — banc de robustesse du moteur AVANT tout écran.

Joue le moteur servi sur les 3 témoins + 20 parcelles U tirées au hasard (ordre déterministe par
md5(idu)) dans ≥ 8 communes. Produit `robustesse.md` : servies / simulation impossible (raison) /
durée, et un VERDICT dur. STOP (exit 1) si une seule invariance casse :
  - 0 géométrie invalide,
  - 0 chevauchement entre objets de sol (bâti · places · allées · accès · espaces libres),
  - 0 contrôle « Réussi » sans règle citée.

Lancer :
  PGHOST=/tmp PYTHONPATH=src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
  <python> docs/audit-2026-10/implantation-2/robustesse.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from shapely.ops import unary_union
from sqlalchemy import text

from labuse.db import session_scope
from labuse.implantation import moteur as M
from labuse.implantation.controles import REUSSI

TEMOINS = {
    "L'Étang-Salé AW (UA)": M.IDUS_ETANG_SALE,
    "Saint-André AX (UC)": M.IDUS_SAINT_ANDRE,
    "Saint-Denis DL (Ui)": M.IDUS_SAINT_DENIS,
}

SOL = ("batiment_emprise", "place", "allee", "acces", "espace_libre")
OUT = Path(__file__).resolve().parent / "robustesse.md"


def _echantillon(session, n_communes=10, par_commune=2) -> list[tuple[str, list[str]]]:
    """≥ 8 communes × 2 parcelles U, contenance 600–5000 m², ordre déterministe par md5(idu)."""
    communes = [r[0] for r in session.execute(text("""
        SELECT substr(z.idu,1,5) insee FROM parcel_zone_plu z JOIN parcels p ON p.idu=z.idu
        WHERE z.zone_lib LIKE 'U%' GROUP BY 1 ORDER BY count(*) DESC LIMIT :k"""),
        {"k": n_communes}).fetchall()]
    sample: list[tuple[str, list[str]]] = []
    for insee in communes:
        rows = session.execute(text("""
            SELECT z.idu, z.zone_lib FROM parcel_zone_plu z JOIN parcels p ON p.idu=z.idu
            WHERE substr(z.idu,1,5)=:i AND z.zone_lib LIKE 'U%'
              AND p.contenance_m2 BETWEEN 600 AND 5000
            ORDER BY md5(z.idu) LIMIT :n"""), {"i": insee, "n": par_commune}).fetchall()
        for idu, zone in rows:
            sample.append((f"{insee} {zone} {idu[-4:]}", [idu]))
    return sample


def _invariants(scenarios) -> list[str]:
    """Renvoie la liste des VIOLATIONS (vide = tout bon) sur les scénarios servis."""
    viol: list[str] = []
    for sc in scenarios:
        for o in sc.scene.objets:
            g = o.geom_world if o.geom_world is not None else o.geom_local
            if g is None or not g.is_valid:
                viol.append(f"{sc.forme} R+{sc.niveaux-1} : géométrie {o.kind} invalide")
        sol = {k: unary_union([o.geom_world for o in sc.scene.of(k)]) for k in SOL
               if sc.scene.of(k)}
        kinds = list(sol)
        for i in range(len(kinds)):
            for j in range(i + 1, len(kinds)):
                inter = sol[kinds[i]].intersection(sol[kinds[j]]).area
                if inter > 1e-6:
                    viol.append(f"{sc.forme} R+{sc.niveaux-1} : {kinds[i]} ∩ {kinds[j]} = {inter:.3f} m²")
        for c in sc.controles:
            if c.resultat == REUSSI and not (c.citation and str(c.citation).strip()):
                viol.append(f"{sc.forme} R+{sc.niveaux-1} : « Réussi » sans citation → {c.nom}")
    return viol


def main() -> int:
    lignes, violations_globales = [], []
    with session_scope() as s:
        cas = [(nom, idus) for nom, idus in TEMOINS.items()]
        cas += _echantillon(s)
        for nom, idus in cas:
            t0 = time.time()
            try:
                scenarios, message, terrain, regles, _conv = M.etudier_multi(
                    session=s, idus=idus, objectif="equilibre", avec_pente=False)
                dt = time.time() - t0
                viol = _invariants(scenarios)
                violations_globales += [f"{nom} — {v}" for v in viol]
                if scenarios:
                    best = scenarios[0]
                    etat = f"servie ({len(scenarios)} scn · {best.statut})"
                    detail = (f"{best.forme} R+{best.niveaux-1} · {best.capacite.logements} logts · "
                              f"{best.capacite.places} places")
                else:
                    etat = "non servie"
                    detail = message or "simulation impossible"
                zone = regles.zone
            except Exception as exc:  # noqa: BLE001
                dt = time.time() - t0
                etat, detail, zone = "ERREUR", f"{type(exc).__name__}: {exc}", "?"
                violations_globales.append(f"{nom} — exception {type(exc).__name__}: {exc}")
            lignes.append((nom, zone, etat, detail, dt))
            print(f"{nom:28s} {zone:5s} {etat:28s} {dt:5.1f}s  {detail}")

    servies = sum(1 for _l in lignes if _l[2].startswith("servie"))
    md = ["# IMPLANTATION-2 — Robustesse du moteur (LOT A)", "",
          f"{servies}/{len(lignes)} assiettes servies. 3 témoins + "
          f"{len(lignes)-3} parcelles U au hasard (≥ 8 communes).", "",
          "| Assiette | Zone | État | Détail / raison | Durée |",
          "|---|---|---|---|---:|"]
    for nom, zone, etat, detail, dt in lignes:
        md.append(f"| {nom} | {zone} | {etat} | {detail} | {dt:.1f} s |")
    md += ["", "## Invariants durs"]
    if violations_globales:
        md.append("**STOP — violations détectées :**")
        md += [f"- {v}" for v in violations_globales]
    else:
        md.append("0 géométrie invalide · 0 chevauchement (bâti/places/allées/accès/espaces "
                  "libres) · 0 « Réussi » sans règle citée. **OK.**")
    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\n→ {OUT}")
    if violations_globales:
        print(f"STOP : {len(violations_globales)} violation(s).")
        return 1
    print("Invariants durs : OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
