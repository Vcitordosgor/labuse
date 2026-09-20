"""PLU-CALIBRAGE-4 lot 1 — MIGRATION de la métadonnée de zonage hors des plu_<slug>.yaml.

Les règles CHIFFRÉES vivent désormais dans `plu_destinations/*.yaml` (regles, PLU-CALIBRAGE-3).
Restent, dans les anciens `config/plu_<slug>.yaml`, des métadonnées de ZONAGE que `plu_rules`
sait lire et que le nouveau `resolve_zone` doit reproduire :

  · commune : mode (strict/progressif) · zones_au_st · zones_au_renvoi · zones_non_constructibles ;
  · zone    : habitat (« interdit ») · constructible_neuf · hauteur_mode (prospect) · bassin ;
  · hypotheses_faisabilite (paramètres du moteur, lus par Hypotheses.charger).

On les rassemble dans UN fichier `config/plu_zonage.yaml` keyé par INSEE — le nouveau moteur le
lit à la place des plu_<slug>.yaml. `regles_transverses` est MORTE (lue nulle part) : abandonnée.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage4_migrer_zonage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[1] / "config"
SORTIE = CONFIG / "plu_zonage.yaml"

_ZONE_META = ("habitat", "constructible_neuf", "hauteur_mode", "bassin")
_COMMUNE_META = ("mode", "zones_au_st", "zones_au_renvoi", "zones_non_constructibles",
                 "zones_non_calibrees", "zones_habitat_interdit_sans_hauteur")


def main() -> int:
    dd = {f.name[6:-5]: f.name[:5] for f in (CONFIG / "plu_destinations").glob("974??_*.yaml")}
    out: dict = {}
    for p in sorted(CONFIG.glob("plu_*.yaml")):
        if p.name in ("plu_millesimes.yaml", "plu_zonage.yaml") or "destinations" in p.name:
            continue
        slug = p.stem[4:]
        insee = dd.get(slug)
        if insee is None:
            # Saint-Paul (gold) : back-compat via commune=None. On l'indexe aussi par insee ET
            # sous la clé « _defaut » (l'ancien _YAML par défaut = Saint-Paul).
            insee = {"saint_paul": "97415"}.get(slug)
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        entree: dict = {"slug": slug}
        for k in _COMMUNE_META:
            if d.get(k) is not None:
                entree[k] = d[k]
        if d.get("hypotheses_faisabilite"):
            entree["hypotheses_faisabilite"] = d["hypotheses_faisabilite"]
        zmeta: dict = {}
        for zc, zv in (d.get("zones") or {}).items():
            if not isinstance(zv, dict):
                continue
            m = {k: zv[k] for k in _ZONE_META if zv.get(k) is not None}
            # notes libres (provenance, ouverture d'urbanisation…) — lues par classify_au_statut
            notes = [v for k, v in zv.items() if (k.endswith("_note") or k == "note") and v]
            if notes:
                m["notes"] = notes
            if m:
                zmeta[zc] = m
        if zmeta:
            entree["zones"] = zmeta
        if insee:
            out[insee] = entree

    SORTIE.write_text(
        "# PLU-CALIBRAGE-4 — métadonnée de zonage migrée hors des plu_<slug>.yaml (généré par\n"
        "# qa/plu_calibrage4_migrer_zonage.py). Les règles chiffrées sont dans plu_destinations.\n"
        + yaml.safe_dump(out, allow_unicode=True, sort_keys=True, width=100), encoding="utf-8")
    n_zmeta = sum(len(e.get("zones", {})) for e in out.values())
    n_hyp = sum(1 for e in out.values() if e.get("hypotheses_faisabilite"))
    print(f"{len(out)} communes → {SORTIE.name} · {n_zmeta} zones avec métadonnée · "
          f"{n_hyp} avec hypotheses_faisabilite")
    for insee, e in sorted(out.items()):
        flags = [k for k in _COMMUNE_META if k in e]
        print(f"  {insee} {e['slug']:22} mode={e.get('mode','progressif')} "
              f"zones-méta={len(e.get('zones', {}))} {[k for k in flags if k!='mode']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
