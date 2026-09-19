"""SOURCES-AUDIT-1 — binding lecture seule : 94 sources → slug → tables/couches,
puis Remplie (comptes) + Réinjectable (last_sync/fraicheur/mode). AUCUNE écriture.
Sortie TSV sur stdout : id, name, slug, tables, couches, remplie_detail, last_sync,
fraicheur, mode, cadence_statut.
"""
from __future__ import annotations
import os, sys, json
from sqlalchemy import create_engine, text

sys.path.insert(0, "src")
from labuse.circuit_etats import NOM_VERS_SLUG  # noqa: E402
from labuse.registre.tables import RESERVOIR_TABLES  # noqa: E402
from labuse.sources_catalog import WHERE_AFFICHEES  # noqa: E402

URL = os.environ["LABUSE_DATABASE_URL"]
eng = create_engine(URL)

WHERE = WHERE_AFFICHEES  # utilise :masquees
with eng.begin() as c:
    rows = c.execute(text(
        "SELECT id, name, status, mode_remplissage, last_sync_at, fraicheur_statut, "
        "fraicheur_erreur_at, cadence_statut, source_millesime "
        f"FROM data_sources WHERE {WHERE} ORDER BY name"), {"masquees": []}).mappings().all()

    # existence de table + colonnes utiles
    def table_exists(t):
        return c.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar() is not None

    def count_rows(t):
        if not table_exists(t):
            return None
        return c.execute(text(f"SELECT count(*) FROM {t}")).scalar()

    def count_kind(kind):
        return c.execute(text("SELECT count(*) FROM spatial_layers WHERE kind=:k"),
                         {"k": kind}).scalar()

    out = []
    for r in rows:
        nom = r["name"]
        slug = NOM_VERS_SLUG.get(nom, "")
        rt = RESERVOIR_TABLES.get(slug)
        tables = list(rt.tables) if rt else []
        couches = list(rt.couches) if rt else []
        note = (rt.note if rt else "") or ""
        # Remplie : détail par table (hors spatial_layers) + par couche
        detail = {}
        for t in tables:
            if t == "spatial_layers":
                continue
            detail[t] = count_rows(t)
        for k in couches:
            detail[f"spatial_layers[{k}]"] = count_kind(k)
        rempli_total = sum(v for v in detail.values() if isinstance(v, int))
        out.append({
            "id": r["id"], "name": nom, "slug": slug or "(non-mappé)",
            "status": r["status"], "mode": r["mode_remplissage"],
            "tables": ",".join(tables) or "(aucune)",
            "couches": ",".join(couches) or "",
            "note": note,
            "remplie_detail": json.dumps(detail, ensure_ascii=False),
            "rempli_total": rempli_total,
            "last_sync": str(r["last_sync_at"].date()) if r["last_sync_at"] else "",
            "fraicheur": r["fraicheur_statut"] or "",
            "err": str(r["fraicheur_erreur_at"].date()) if r["fraicheur_erreur_at"] else "",
            "cadence_statut": r["cadence_statut"] or "",
        })

print(f"# {len(out)} sources\n")
for o in out:
    print("\t".join(str(o[k]) for k in
          ["id", "name", "slug", "tables", "couches", "rempli_total",
           "last_sync", "fraicheur", "err", "mode", "cadence_statut", "note"]))
# JSON complet pour la suite
with open("/tmp/sources_audit_bind.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("\n# détail écrit dans /tmp/sources_audit_bind.json", file=sys.stderr)
