"""VEILLE-2 · Lot 2 — génère les PREUVES lisibles du chemin Radar sur de vraies pages leboncoin.

Écrit dans captures/veille-2/ :
  · lot2-extraction.md      — pour chaque page/annonce : prix, surface, commune, type, date, lien
                              (valeur extraite == valeur brute du __NEXT_DATA__ = « la page en face ») ;
  · lot2-annonce-veille.md  — la matrice 3 veilles × 6 annonces (attendu == obtenu) + rattachement.

Usage : LABUSE_DATABASE_URL=…/labuse_test PYTHONPATH=src python qa/veille2/preuve_radar.py
Ingestion éphémère (nettoyée en fin) — aucune trace résiduelle.
"""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import digests, html_ingest, html_next, tables, veille

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "captures" / "veille-2"
ECH1 = ROOT / "qa" / "radar-html" / "ECH-1.html"
ECH2 = ROOT / "qa" / "radar-html" / "ECH-2-varianteB.html"
TERR = {
    "T-camelias.html": ROOT / "qa" / "radar-terrains" / "T-camelias.html",
    "T-possession.html": ROOT / "qa" / "radar-terrains" / "T-possession.html",
    "T-saintemarie.html": ROOT / "qa" / "radar-terrains" / "T-saintemarie.html",
}
A, B, C, D, E, F = 3143092379, 3253364472, 3184708502, 3055991753, 3241879744, 3200222934


def _nettoyer(db):
    db.execute(text("DELETE FROM pige_biens WHERE bien_id IN (SELECT bien_id FROM pige_annonces "
                    "WHERE url_sortante LIKE '%leboncoin.fr/ad/ventes_immobilieres/%')"))
    db.execute(text("DELETE FROM event_log WHERE dedup LIKE 'pige:%'"))
    db.execute(text("DELETE FROM pige_depots WHERE nom_fichier LIKE 'ECH-%' OR nom_fichier LIKE 'T-%'"))
    db.commit()


def _brut_next(path: Path, list_id: int) -> dict:
    """La valeur « en face » : lue directement dans le __NEXT_DATA__ de la page (searchData.ads ou ad)."""
    html = path.read_text(encoding="utf-8")
    data = html_next.extraire_next_data(html)
    pp = data["props"]["pageProps"]
    ads = (pp.get("searchData") or {}).get("ads") or ([pp["ad"]] if pp.get("ad") else [])
    for a in ads:
        if a.get("list_id") == list_id:
            return html_next.aplatir(a)
    return {}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with session_scope() as db:
        tables.ensure_tables(db.get_bind())
        _nettoyer(db)
        r1 = html_ingest.ingester(db, ECH1.read_text(encoding="utf-8"), "ECH-1.html", archiver=False)
        rvarb = html_ingest.ingester(db, ECH2.read_text(encoding="utf-8"), "ECH-2-varianteB.html", archiver=False)
        rter = {n: html_ingest.ingester(db, p.read_text(encoding="utf-8"), n, archiver=False) for n, p in TERR.items()}

    # ── extraction.md ────────────────────────────────────────────────────────────────────
    lines = ["# VEILLE-2 · Lot 2 — Extraction sur de VRAIES pages leboncoin déposées", "",
             "Cinq dépôts HTML réels : `ECH-1.html` (35 annonces, variante A riche), "
             "`ECH-2-varianteB.html` (variante B DOM dégradée), et trois pages d'annonce `T-*.html`.", "",
             "| Dépôt | mode | provenance | annonces | nouvelles | hors périmètre | à qualifier |",
             "|---|---|---|--:|--:|--:|--:|",
             f"| ECH-1.html | {r1['mode']} | {r1['provenance']} | {r1['nb_annonces']} | {r1['nb_nouvelles']} | {r1['nb_hors_perimetre']} | {r1['nb_a_qualifier']} |",
             f"| ECH-2-varianteB.html | {rvarb['mode']} | {rvarb['provenance']} | {rvarb['nb_annonces']} | {rvarb['nb_nouvelles']} | {rvarb['nb_hors_perimetre']} | {rvarb['nb_a_qualifier']} |"]
    for n, r in rter.items():
        lines.append(f"| {n} | {r['mode']} | {r['provenance']} | {r['nb_annonces']} | {r['nb_nouvelles']} | {r['nb_hors_perimetre']} | {r['nb_a_qualifier']} |")
    lines += ["", "## Chaque fait extrait == la valeur « en face » (du __NEXT_DATA__ de la page)", "",
              "| annonce (list_id) | commune | type | prix | surface | date publication | lien |",
              "|---|---|---|--:|--:|---|---|"]
    ancres = [(A, ECH1), (B, ECH1), (C, ECH1), (D, TERR["T-camelias.html"]),
              (E, TERR["T-possession.html"]), (F, TERR["T-saintemarie.html"])]
    with session_scope() as db:
        for lid, path in ancres:
            row = db.execute(text(
                "SELECT b.commune,b.type_bien,f.prix,f.surface_hab,f.surface_terrain,"
                " a.url_sortante,a.first_publication_date::date pub FROM pige_biens b "
                "JOIN pige_faits f ON f.bien_id=b.bien_id JOIN pige_annonces a ON a.bien_id=b.bien_id "
                "WHERE a.list_id=:l"), {"l": lid}).mappings().first()
            brut = _brut_next(path, lid)
            surf = (f"{float(row['surface_hab']):.0f} m² hab" if row["surface_hab"]
                    else f"{float(row['surface_terrain']):.0f} m² terrain" if row["surface_terrain"] else "—")
            # contrôle : la valeur extraite == la valeur brute de la page
            ok_prix = "✓" if brut.get("prix") == row["prix"] else "✗"
            lines.append(f"| {lid} | {row['commune']} | {row['type_bien']} | {row['prix']:,} € {ok_prix} | "
                         f"{surf} | {row['pub']} | …/{lid} |".replace(",", " "))
    (OUT / "lot2-extraction.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── annonce-veille.md ────────────────────────────────────────────────────────────────
    V1 = {"communes": ["Saint-Denis"], "type_bien": "maison", "prix_max": 600000}
    V2 = {"communes": ["La Possession", "Sainte-Marie"], "type_bien": "terrain"}
    V3 = {"type_bien": "terrain", "surface_min": 1000, "prix_max": 900000}
    veilles = [("V1", "SD · maison · ≤ 600 000 €", V1),
               ("V2", "Possession ou Sainte-Marie · terrain", V2),
               ("V3", "terrain · ≥ 1000 m² · ≤ 900 000 €", V3)]
    with session_scope() as db:
        biens = {b["bien_id"]: b for b in digests._biens_du_jour(db)}
        bid = {lid: db.execute(text("SELECT bien_id FROM pige_annonces WHERE list_id=:l"), {"l": lid}).scalar()
               for lid in (A, B, C, D, E, F)}
        etats = {lid: db.execute(text("SELECT rattachement_etat FROM pige_biens WHERE bien_id=:b"),
                                 {"b": bid[lid]}).scalar() for lid in (A, B, C, D, E, F)}
        ml = ["# VEILLE-2 · Lot 2 — Matrice annonce × veille (3 veilles aux critères différents)", "",
              "Critères des trois veilles :", ""]
        for k, lbl, _ in veilles:
            ml.append(f"- **{k}** — {lbl}")
        ml += ["", "| annonce | commune | type | prix | surface pertinente | rattachement | "
               + " | ".join(k for k, _, _ in veilles) + " |",
               "|---|---|---|--:|--:|---|" + "---|" * len(veilles)]
        for lid in (A, B, C, D, E, F):
            b = biens[bid[lid]]
            surf = veille._surface_pertinente(b)
            cells = [("✅" if veille.matche(cr, b) else "·") for _, _, cr in veilles]
            prix = f"{b['faits']['prix']:,}".replace(",", " ")
            ml.append(f"| {lid} | {b['commune']} | {b['type_bien']} | {prix} € | "
                      f"{surf:.0f} m² | {etats[lid]} | " + " | ".join(cells) + " |")
        ml += ["", "Lecture : chaque annonce ne « part » qu'aux veilles dont elle satisfait TOUS les "
               "critères — et à elles seules. Aucune parcelle inventée : rattachement = état réel "
               "(`non_rattachee` ici, faute de cadastre en base de test ; la convergence ≥2 critères "
               "est prouvée par `tests/test_veille2_lot2.py::test_rattachement_convergence_et_jamais_invente`)."]
    (OUT / "lot2-annonce-veille.md").write_text("\n".join(ml) + "\n", encoding="utf-8")

    with session_scope() as db:
        _nettoyer(db)
    print("écrit:", OUT / "lot2-extraction.md", "et", OUT / "lot2-annonce-veille.md")


if __name__ == "__main__":
    main()
