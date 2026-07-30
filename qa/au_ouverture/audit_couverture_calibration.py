"""Point 2.4 de l'ARBITRAGE RE-RUN (Vic) — couverture de calibration + origine des libellés perdus.
MESURE SEULE (Vic : « mesurer, pas corriger »). Read-only.

Découverte : parcel_zone_plu.zone_lib est peuplé DE FAÇON INCOHÉRENTE selon la forme de la partition
GPU de la commune — parfois le code fin (Saint-Paul : name='U6c'), parfois la FAMILLE (Bras-Panon /
Saint-Pierre : subtype='U'), parfois un ID NUMÉRIQUE (Cilaos : name='95'). Or le code fin CORRECT est
TOUJOURS dans `spatial_layers.attrs->>'libelle'` (Ud, 1AUb, Uf, Uc…). Résultat : la calibration YAML
de 8 communes est INERTE (zone_lib ne matche jamais les clés) → estimation générique servie à tort.
Récupérable : le bon libellé existe, il suffirait de re-dériver zone_lib depuis attrs.libelle.

Saint-Benoît est un cas SÉPARÉ et DÉLIBÉRÉ : zones:{} vide par arbitrage Vic 28/07 (hauteurs par
secteur graphique, non portables par le schéma v1) + ouverture AU non extraite (règlement deux colonnes).
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
import yaml
from sqlalchemy import text
from labuse.db import session_scope
from labuse.faisabilite.plu_rules import resolve_zone, _commune_slug, _CONFIG_DIR

with session_scope() as s:
    communes = s.execute(text("SELECT substring(idu from 1 for 5) i, commune c FROM parcels GROUP BY 1,2 ORDER BY 1")).all()
    print(f"{'commune':22s}{'servies':>8}{'%génér.':>8}{'zonesYAML':>10}{'fins∈YAML':>10}  diagnostic")
    total_recuperable = 0
    for insee, commune in communes:
        p = _CONFIG_DIR / f"plu_{_commune_slug(commune)}.yaml"
        outillee = p.is_file()
        keys = set((yaml.safe_load(p.read_text()).get("zones") or {}).keys()) if outillee else set()
        rows = s.execute(text("""
          SELECT z.zone_lib, count(*) n FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
          JOIN parcel_p_score_v2 sc ON sc.parcelle_id=p.idu AND sc.run_id='q_v7_defisc'
          WHERE substring(p.idu from 1 for 5)=:i AND sc.tier<>'ecartee' GROUP BY 1"""), {"i": insee}).all()
        servies = sum(n for _, n in rows)
        gen = sum(n for zl, n in rows if (lambda r: r is None or not r.calibree)(resolve_zone(zl, commune)))
        pct = 100 * gen / servies if servies else 0
        libs = [r[0] for r in s.execute(text(
            "SELECT DISTINCT attrs->>'libelle' FROM spatial_layers WHERE kind='plu_gpu_zone' AND commune ILIKE :c"),
            {"c": f"%{commune}%"}).all() if r[0]]
        fins_match = sum(1 for l in libs if l in keys)
        # récupérable = commune outillée, ~100% générique, mais les libellés fins matcheraient
        recup = outillee and keys and pct >= 99 and fins_match > 0 and commune != "Saint-Benoît"
        if recup:
            total_recuperable += servies
        diag = ("libellés PERDUS à l'ingestion (récupérables via attrs.libelle)" if recup
                else "zones:{} VIDE délibéré (hauteurs secteur graphique)" if outillee and not keys
                else "non outillée (pas de plu_)" if not outillee
                else "calibration active")
        print(f"{commune:22s}{servies:>8}{pct:>7.0f}%{len(keys):>10}{fins_match:>10}  {diag}")
    print(f"\nSERVIES RÉCUPÉRABLES (calibration inerte par libellé perdu) : {total_recuperable}")
