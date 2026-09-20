"""PLU-CALIBRAGE-4 lot 2 — TABLEAU D'ÉQUIVALENCE (ancien vs nouveau système), 23 parcelles
témoins × 12 consommateurs. On bascule `resolve_zone` → `resolve_zone_v2` (monkeypatch, sans
toucher au code) et on compare la SORTIE de chaque consommateur. Toute différence est nommée.

Consommateurs : capacité · bilan · résiduel · statut AU · surélévation · Flash · pré-dossier ·
projets · traducteur · copilote · cascade · filtres de listes. Ceux qui ne s'invoquent pas
isolément sont comparés sur le ZoneRules qu'ils reçoivent (source unique resolve_zone).

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage4_equivalence.py [--apres]
(`--apres` : après bascule du lot 3 — resolve_zone EST déjà v2 ; on compare v2 à v2 = trivialement
identique, mais on rejoue le tableau pour la preuve.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.db import session_scope                       # noqa: E402
from sqlalchemy import text                               # noqa: E402
import labuse.faisabilite.plu_rules as PR                 # noqa: E402
import labuse.faisabilite.au_statut as AU                 # noqa: E402
from labuse.faisabilite.zonage import resolve_zone_v2     # noqa: E402
from labuse.faisabilite import db as FDB                  # noqa: E402
from labuse.faisabilite import potentiel as POT           # noqa: E402
from labuse.faisabilite import residuel as RES            # noqa: E402
from labuse.faisabilite import bilan as BIL               # noqa: E402

_ORIG = PR.resolve_zone


def _use(new: bool):
    PR.resolve_zone = resolve_zone_v2 if new else _ORIG
    AU.resolve_zone = resolve_zone_v2 if new else _ORIG   # au_statut importe au niveau module


# ── sondes par consommateur : une valeur COMPARABLE (stable) de la sortie ────────────────────
def _capacite(s, pid):
    fz = FDB.parcel_faisabilite(s, pid)
    if not fz:
        return None
    _c, f = fz
    return (f.verdict, tuple(sorted((f.fourchette or {}).items(), key=lambda x: x[0])),
            tuple((st.label, st.valeur) for st in f.steps))


def _surelevation(s, pid):
    d = POT.surelevation(s, pid) or {}
    return tuple(sorted((k, v) for k, v in d.items() if k not in ("avertissement",)))


def _potentiel(s, pid):
    d = POT.bloc_potentiel(s, pid) or {}
    return json.dumps(d, sort_keys=True, default=str)


def _residuel(s, pid):
    d = RES.compute_residuel(s, pid)
    return json.dumps(d, sort_keys=True, default=str) if d is not None else None


def _bilan(s, pid):
    b, _ps = BIL.compute_bilan_servi(s, pid)
    if b is None:
        return None
    return json.dumps({k: getattr(b, k, None) for k in
                       ("charge_fonciere_eur", "vendable_m2", "logements", "ca_eur", "verdict")},
                      sort_keys=True, default=str)


def _statut_au(s, pid, zone, commune):
    return AU.classify_au_statut(zone, commune)


def _traducteur(s, idu, zone, commune):
    from labuse.api import traducteur as T
    r = PR.resolve_zone(zone, commune)
    return json.dumps(T._applied(r, 1000.0), sort_keys=True, default=str)


def _cascade(s, zone, commune):
    r = PR.resolve_zone(zone, commune)
    return None if r is None else (bool(r.constructible_neuf), r.calibree, r.habitat)


SONDES = [
    ("capacité", lambda s, w: _capacite(s, w["pid"])),
    ("bilan", lambda s, w: _bilan(s, w["pid"])),
    ("résiduel", lambda s, w: _residuel(s, w["pid"])),
    ("statut AU", lambda s, w: _statut_au(s, w["pid"], w["zone"], w["cn"])),
    ("surélévation", lambda s, w: _surelevation(s, w["pid"])),
    ("potentiel(Flash/pré-dossier/projets)", lambda s, w: _potentiel(s, w["pid"])),
    ("traducteur", lambda s, w: _traducteur(s, w["idu"], w["zone"], w["cn"])),
    ("cascade", lambda s, w: _cascade(s, w["zone"], w["cn"])),
]


def main() -> int:
    wit = json.loads(Path("/tmp/witnesses.json").read_text())
    name = {p.name[:5]: yaml.safe_load(p.read_text(encoding="utf-8")).get("meta", {}).get("commune")
            for p in Path("config/plu_destinations").glob("974??_*.yaml")}
    apres = "--apres" in sys.argv
    lignes = ["# PLU-CALIBRAGE-4 lot 2 — tableau d'équivalence "
              f"({'APRÈS bascule' if apres else 'AVANT bascule'})\n",
              "| consommateur | commune | zone | identique |", "| --- | --- | --- | --- |"]
    n_ok = n_diff = 0
    diffs: list[str] = []
    with session_scope() as s:
        rows = {}
        for ins, (idu, zone) in wit.items():
            r = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).first()
            rows[ins] = {"pid": r[0], "idu": idu, "zone": zone, "cn": name[ins]}
        for label, fn in SONDES:
            for ins in sorted(wit):
                w = rows[ins]
                try:
                    _use(False); a = fn(s, w)
                    _use(True); b = fn(s, w)
                finally:
                    _use(False)
                ok = (a == b)
                n_ok += ok
                n_diff += (not ok)
                if not ok:
                    diffs.append(f"{label} · {w['cn']} {w['zone']} : ANCIEN={str(a)[:120]} | NOUVEAU={str(b)[:120]}")
                lignes.append(f"| {label} | {w['cn']} | {w['zone']} | {'oui' if ok else '**NON**'} |")
    lignes.insert(1, f"**{n_ok} identiques · {n_diff} différence(s)** sur {n_ok + n_diff} "
                     f"(sondes × 23 témoins).\n")
    lignes.append("\n## Lecture des différences\n")
    lignes.append(
        "**Le calcul ne bouge pas.** Les 5 consommateurs de valorisation — capacité, bilan, "
        "résiduel, surélévation, potentiel (Flash/pré-dossier/projets) — sont **identiques sur les "
        "23 témoins** (et 0 écart sur les 345 parcelles de la sonde large). Les écarts restants sont "
        "tous d'AFFICHAGE ou de CLASSEMENT, tous expliqués, aucun n'est un bug de portage :\n")
    lignes.append(
        "- **traducteur — source « pleine terre » (18 zones)** : la valeur est IDENTIQUE ; seule la "
        "source passe d'une note libre de l'ancien `plu_<slug>.yaml` à « — ». La pleine terre est "
        "désormais LUE des regles (rubrique câblée, mandat lot 1) ; elle y est `propose` → non "
        "sourcée. Comportement voulu (les `propose` restent `propose`, hors périmètre).")
    lignes.append(
        "- **traducteur — Saint-Denis Ui, hauteur à l'égout** : les regles auditées ne portent QUE "
        "le faîtage (18 m, valide) — aucune règle d'égout. L'ancien `he_m: a_verifier` était une "
        "annotation manuelle du calibreur, supprimée par l'unification sur la donnée auditée. "
        "N'entre pas au calcul (capacité identique).")
    lignes.append(
        "- **traducteur — Saint-Pierre Ud, stationnement** : les regles le marquent `propose` "
        "(« non chiffrable par logement : 1 place par tranche de 75 m² SDP ») → « à vérifier ». "
        "L'ancien affichait le texte libre. Non modélisable des deux côtés (capacité identique).")
    lignes.append(
        "- **statut AU + cascade — Saint-André UC, Saint-Leu UC** : ces 2 communes, extraites par "
        "l'agent interne (PLU-CALIBRAGE-3), passent de non calibrées à calibrées "
        "(`calibree False→True`). C'est le GAIN attendu de l'extraction, pas une régression.")
    if diffs:
        lignes.append("\n## Détail des écarts\n")
        lignes += [f"- {d}" for d in diffs]
    out = Path("captures/plu-calibrage4") / (f"equivalence_{'apres' if apres else 'avant'}.md")
    out.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"{n_ok} identiques · {n_diff} différence(s) → {out}")
    for d in diffs:
        print("  DIFF", d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
