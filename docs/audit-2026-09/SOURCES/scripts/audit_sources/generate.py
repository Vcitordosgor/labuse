"""SOURCES-AUDIT-1 — génère SOURCES-AUDIT.csv + fiches/<id>.md + SOURCES-AUDIT.md.

LECTURE SEULE. Rejouable :  python -m audit_sources.generate

La visibilité de chaque source est DÉRIVÉE du graphe du registre (réservoir → chiffre →
robinet). Les champs qualitatifs (champs non pris, potentiel, verdict nuancé) viennent de
`curation.py` — écrits à la main, adossés au code, marqués « non vérifié » quand la source
producteur n'a pas pu être consultée (aucun scraping). Tout le reste est mesuré en base.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from . import lib
from .curation import CURATION

OUT = Path(__file__).resolve().parents[2]           # …/SOURCES

# familles fines partageant un même producteur/usage → proposition canonique (lot 0 S4)
# (documentées dans SOURCES-AUDIT.md ; ce module ne MODIFIE pas la base)


def _slug_filtre(slug: str | None, filtre_keys: set[str]) -> str | None:
    """Rapproche un slug de réservoir d'une clé filtre_resultats (plus long recouvrement)."""
    if not slug:
        return None
    if slug in filtre_keys:
        return slug
    best = None
    for k in filtre_keys:
        if k and (k in slug or slug in k):
            if best is None or len(k) > len(best):
                best = k
    return best


def _emprise(src: dict, n_couches_communes: int | None) -> str:
    """Emprise déclarée (heuristique, adossée au producteur/type)."""
    cat = src["category"] or ""
    name = src["name"]
    if src["status"] in ("hub", "alias"):
        return "n/a"
    # sources par commune (tables commune_*) : île via 24 lignes
    if re.search(r"communes?|EPCI|DHUP|DGALN|REI|SRU|ABC|PLH", name):
        return "île (par commune)"
    return "île (présumé — voir note)"


def construire() -> list[dict]:
    K = lib.charger_constantes()
    nom_slug = K["NOM_VERS_SLUG"]
    reservoir_tables = K["RESERVOIR_TABLES"]
    familles = K["FAMILLE_DE_CATEGORIE"]

    conn = lib.connect()
    cur = conn.cursor()
    sources = lib.lire_sources(cur)
    veille = lib.lire_veille(cur)
    chiffres = lib.lire_chiffres(cur)
    robinets = lib.lire_robinets(cur)
    filtres = lib.lire_filtres(cur)
    layers_src = lib.layers_par_source(cur)
    filtre_keys = set(filtres)

    # index : chiffre id → chiffre ; robinets par chiffre
    ch_par_id = {c["id"]: c for c in chiffres}
    rob_par_chiffre: dict[str, list[dict]] = {}
    for rob in robinets:
        for cid in rob["chiffres"] or []:
            rob_par_chiffre.setdefault(cid, []).append(rob)

    # comptage des tables réservoir (dédupe)
    toutes_tables = {t for rt in reservoir_tables.values() for t in rt.tables}
    compte_table = {t: lib.compter_table(cur, t) for t in sorted(toutes_tables)}
    compte_couche = lib.compter_couches(cur)

    records = []
    for src in sources:
        sid = src["id"]
        name = src["name"]
        slug = nom_slug.get(name)
        rt = reservoir_tables.get(slug) if slug else None

        # chiffres servis par ce réservoir
        ch_servis = [c for c in chiffres if slug and slug in (c["reservoirs"] or [])]
        ch_ids = {c["id"] for c in ch_servis}
        # robinets touchés
        robs = []
        seen = set()
        for cid in ch_ids:
            for rob in rob_par_chiffre.get(cid, []):
                if rob["id"] not in seen:
                    seen.add(rob["id"])
                    robs.append(rob)
        rob_par_cat: dict[str, list[dict]] = {}
        for rob in robs:
            rob_par_cat.setdefault(rob["categorie"], []).append(rob)

        # couches carte
        lay = layers_src.get(sid)
        couches_carte = []
        if lay:
            couches_carte = sorted(lay["kinds"])
        elif rt and rt.couches:
            couches_carte = list(rt.couches)

        # comptage objets base (table réservoir principale ou spatial_layers via couches)
        n_objets = None
        tables_reelles = []
        if rt:
            for t in rt.tables:
                if t == "spatial_layers":
                    continue
                c = compte_table.get(t)
                tables_reelles.append((t, c))
            # priorité : première table non-spatial avec un compte
            for t, c in tables_reelles:
                if c is not None:
                    n_objets = c
                    break
            if n_objets is None and rt.couches:
                n_objets = sum(compte_couche.get(k, 0) for k in rt.couches)

        # moteurs / scoring
        moteurs = sorted({c["moteur"] for c in ch_servis if c["moteur"]})
        scoring = any(c["moteur"] in ("scoring_p_v2", "v_score", "score_e") or
                      (c["portee"] == "run") for c in ch_servis)

        # sentinelle / filtre / verrou
        v = veille.get(sid)
        fkey = _slug_filtre(slug, filtre_keys)
        f_rows = filtres.get(fkey, []) if fkey else []
        f_verdicts = {r["verdict"] for r in f_rows}
        sous_filtre = bool(f_rows)
        filtre_etat = ("KO" if "ko" in f_verdicts else "OK") if f_rows else "—"
        # sous verrou : displayed (V2a/V2b + pont) ou alimente un chiffre servi (provenance)
        displayed = (src["status"] in ("connecte", "manuel")
                     and not (src["technical_notes"] or "").startswith(("DOUBLON", "RETIRÉ", "DORMANT"))
                     and not src["affichage_desactive"])
        sous_verrou = displayed or bool(ch_ids)

        cur_o = CURATION.get(sid, {})

        # verdict automatique (curation peut l'écraser)
        verdict = _verdict_auto(src, slug, ch_ids, couches_carte, robs, cur_o)

        records.append({
            "id": sid,
            "nom": name,
            "famille": familles.get(src["category"] or "aucune", "Autres"),
            "categorie": src["category"],
            "producteur": src["provider"],
            "licence": (src["legal_notes"] or "").strip(),
            "endpoint": src["endpoint_url"],
            "doc_url": src["documentation_url"],
            "format": src["access_type"],
            "statut": src["status"],
            "mode": src["mode_remplissage"],
            "slug": slug or "—",
            "millesime_base": src["source_millesime"],
            "millesime_reservoir": (rt.millesime if rt else "") or "",
            "millesime_producteur": cur_o.get("millesime_producteur", "non vérifié"),
            "cadence_officielle": cur_o.get("cadence_officielle", "non vérifié"),
            "cadence_declaree": src["source_cadence"] or (
                f"{src['cadence_attendue_jours']} j" if src["cadence_attendue_jours"] else ""),
            "last_sync": src["last_sync_at"].isoformat() if src["last_sync_at"] else "",
            "retiree_le": src["retiree_le"].isoformat() if src["retiree_le"] else "",
            "retiree_raison": src["retiree_raison"] or "",
            "alias_de": src["alias_de"] or "",
            # flags
            "sous_sentinelle": "oui" if v else "non",
            "sentinelle_methode": (v or {}).get("methode", ""),
            "sentinelle_statut": (v or {}).get("dernier_statut", ""),
            "sous_filtre": "oui" if sous_filtre else "non",
            "filtre_etat": filtre_etat,
            "sous_verrou": "oui" if sous_verrou else "non",
            "dans_registre": "oui" if slug else "non",
            "alimente_chiffres": len(ch_ids),
            # couverture
            "emprise": cur_o.get("emprise", _emprise(src, None)),
            "communes_couvertes": cur_o.get("communes_couvertes", ""),
            "n_objets_base": n_objets if n_objets is not None else "",
            "n_objets_producteur_974": cur_o.get("n_objets_producteur", "non vérifié"),
            "ecart": cur_o.get("ecart", ""),
            "part_parcelles": cur_o.get("part_parcelles", ""),
            "tables_reservoir": ";".join(rt.tables) if rt else "",
            "reservoir_note": (rt.note if rt else "") or "",
            # complétude
            "champs_publies": cur_o.get("champs_publies", "non vérifié"),
            "champs_ingérés": cur_o.get("champs_ingeres", ""),
            "champs_non_pris": cur_o.get("champs_non_pris", ""),
            "geom_conservee": cur_o.get("geom_conservee", ""),
            "granularite": cur_o.get("granularite", ""),
            "granularite_respectee": cur_o.get("granularite_respectee", ""),
            # visibilité (dérivée)
            "viz_fiche": _libs(rob_par_cat.get("fiche")),
            "viz_couche": ";".join(couches_carte),
            "viz_outil": _libs(rob_par_cat.get("outil")),
            "viz_pdf": _libs(rob_par_cat.get("pdf")),
            "viz_copilote": _libs(rob_par_cat.get("copilote")),
            "viz_page": _libs(rob_par_cat.get("page_client")),
            "viz_scoring": "oui" if scoring else "non",
            "moteurs": ";".join(moteurs),
            "test_client_clics": cur_o.get("test_client_clics", _clics(rob_par_cat, couches_carte)),
            "i_source_millesime_limite": cur_o.get("i_dit", "non vérifié"),
            # potentiel
            "potentiel": cur_o.get("potentiel", ""),
            "manque_plein": cur_o.get("manque_plein", ""),
            "principes_ok": ";".join(cur_o.get("principes_ok", [])),
            "principes_ko": ";".join(cur_o.get("principes_ko", [])),
            # verdict
            "verdict": cur_o.get("verdict", verdict),
            "verdict_raison": cur_o.get("verdict_raison", "") or _raison_auto(
                verdict, ch_ids, couches_carte, rob_par_cat, moteurs),
        })
    cur.close()
    conn.close()
    return records


def _libs(robs: list[dict] | None) -> str:
    if not robs:
        return ""
    return " | ".join(f"{r['nom']} ({r['route']})" for r in robs)


def _clics(rob_par_cat: dict, couches: list[str]) -> str:
    if rob_par_cat.get("couche") or couches:
        return "1 clic (couche carte)"
    if rob_par_cat.get("fiche"):
        return "2-3 clics (ouvrir la parcelle/commune, dérouler la section)"
    if rob_par_cat.get("outil"):
        return "2 clics (ouvrir l'outil)"
    if rob_par_cat.get("pdf"):
        return "export (dans un PDF)"
    if rob_par_cat.get("copilote"):
        return "via Copilote (question)"
    return "nulle part (branchée invisible)"


def _raison_auto(verdict, ch_ids, couches, rob_par_cat, moteurs) -> str:
    """Raison de repli, quand la curation n'en donne pas (résumé mesuré)."""
    surfaces = []
    if rob_par_cat.get("fiche"):
        surfaces.append(f"{len(rob_par_cat['fiche'])} section(s) de fiche")
    if couches:
        surfaces.append(f"{len(couches)} couche(s) carte")
    if rob_par_cat.get("outil"):
        surfaces.append(f"{len(rob_par_cat['outil'])} outil(s)")
    if rob_par_cat.get("pdf"):
        surfaces.append(f"{len(rob_par_cat['pdf'])} PDF")
    if rob_par_cat.get("copilote"):
        surfaces.append("Copilote")
    base = f"Alimente {len(ch_ids)} chiffre(s) du registre"
    if moteurs:
        base += f" via {', '.join(moteurs)}"
    if surfaces:
        base += " ; visible dans : " + ", ".join(surfaces)
    else:
        base += " ; aucune surface client dérivée du registre"
    return base + ". *(raison auto — champs producteur non vérifiés, cf. mandat)*"


def _verdict_auto(src, slug, ch_ids, couches, robs, cur_o) -> str:
    st = src["status"]
    if st == "retiree":
        return "RETIRÉE (déjà)"
    if st == "alias":
        return "ALIAS (doublon)"
    if st == "hub":
        return "HUB (catalogue)"
    if st == "a_faire":
        return "À DEMANDER / À BRANCHER"
    served = bool(ch_ids) or bool(couches) or bool(robs)
    if st == "manuel":
        return "MANUELLE" + ("" if served else " — invisible")
    # connecte
    if not served:
        return "BRANCHÉE INVISIBLE"
    if not slug:
        return "SERVIE HORS REGISTRE"
    return "PLEINE"


# ── sorties ────────────────────────────────────────────────────────────────────────────
CSV_COLS = [
    "id", "nom", "famille", "categorie", "producteur", "licence", "endpoint", "doc_url",
    "format", "statut", "mode", "slug", "millesime_base", "millesime_reservoir",
    "millesime_producteur", "cadence_officielle", "cadence_declaree", "last_sync",
    "retiree_le", "retiree_raison", "alias_de", "sous_sentinelle", "sentinelle_methode",
    "sentinelle_statut", "sous_filtre", "filtre_etat", "sous_verrou", "dans_registre",
    "alimente_chiffres", "emprise", "communes_couvertes", "n_objets_base",
    "n_objets_producteur_974", "ecart", "part_parcelles", "tables_reservoir",
    "reservoir_note", "champs_publies", "champs_ingérés", "champs_non_pris",
    "geom_conservee", "granularite", "granularite_respectee", "viz_fiche", "viz_couche",
    "viz_outil", "viz_pdf", "viz_copilote", "viz_page", "viz_scoring", "moteurs",
    "test_client_clics", "i_source_millesime_limite", "potentiel", "manque_plein",
    "principes_ok", "principes_ko", "verdict", "verdict_raison",
]


def ecrire_csv(records):
    p = OUT / "SOURCES-AUDIT.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)
    return p


def _fiche_md(r) -> str:
    def ligne(lab, val):
        return f"- **{lab}** : {val}\n" if val not in (None, "", []) else f"- **{lab}** : —\n"
    L = [f"# {r['nom']}  \n", f"`id {r['id']}` · famille *{r['famille']}* · "
         f"catégorie `{r['categorie']}` · statut **{r['statut']}** · slug `{r['slug']}`\n",
         f"\n## Verdict — {r['verdict']}\n", f"{r['verdict_raison'] or '*(auto)*'}\n",
         "\n## Identité\n"]
    L += [ligne("Producteur", r["producteur"]), ligne("Licence", r["licence"]),
          ligne("Endpoint utilisé", r["endpoint"]), ligne("Doc", r["doc_url"]),
          ligne("Format / accès", r["format"]), ligne("Mode de remplissage", r["mode"]),
          ligne("Millésime en base", r["millesime_base"]),
          ligne("Millésime réservoir (code)", r["millesime_reservoir"]),
          ligne("Millésime producteur", r["millesime_producteur"]),
          ligne("Cadence officielle", r["cadence_officielle"]),
          ligne("Cadence déclarée", r["cadence_declaree"]),
          ligne("Dernière synchro", r["last_sync"]),
          ligne("Sous sentinelle", f"{r['sous_sentinelle']} ({r['sentinelle_methode']}, {r['sentinelle_statut']})"),
          ligne("Sous filtre", f"{r['sous_filtre']} ({r['filtre_etat']})"),
          ligne("Sous verrou", r["sous_verrou"]),
          ligne("Dans le registre (pont)", r["dans_registre"]),
          ligne("Chiffres alimentés", r["alimente_chiffres"])]
    L += ["\n## Couverture\n",
          ligne("Emprise", r["emprise"]), ligne("Communes couvertes /24", r["communes_couvertes"]),
          ligne("Objets en base (local)", r["n_objets_base"]),
          ligne("Objets producteur 974", r["n_objets_producteur_974"]),
          ligne("Écart", r["ecart"]), ligne("Part des parcelles touchées", r["part_parcelles"]),
          ligne("Tables réservoir", r["tables_reservoir"]),
          ligne("Note réservoir", r["reservoir_note"])]
    L += ["\n## Complétude — ce qu'on a laissé sur la table\n",
          ligne("Champs publiés (producteur)", r["champs_publies"]),
          ligne("Champs ingérés", r["champs_ingérés"]),
          ligne("Champs non pris", r["champs_non_pris"]),
          ligne("Géométrie conservée", r["geom_conservee"]),
          ligne("Granularité réelle", r["granularite"]),
          ligne("Granularité respectée à l'affichage", r["granularite_respectee"])]
    L += ["\n## Où elle se voit\n",
          ligne("Fiche parcelle / commune", r["viz_fiche"]),
          ligne("Couche carte", r["viz_couche"]),
          ligne("Outils", r["viz_outil"]), ligne("PDF", r["viz_pdf"]),
          ligne("Copilote", r["viz_copilote"]), ligne("Pages client", r["viz_page"]),
          ligne("Scoring / cascade", r["viz_scoring"]), ligne("Moteurs", r["moteurs"]),
          ligne("Test client (clics)", r["test_client_clics"]),
          ligne("Le « i » dit source/millésime/limite", r["i_source_millesime_limite"])]
    L += ["\n## Potentiel\n", ligne("Pourrait servir de plus", r["potentiel"]),
          ligne("Ce qui manque pour le plein potentiel", r["manque_plein"]),
          ligne("Principes tenus", r["principes_ok"]),
          ligne("Principes non tenus", r["principes_ko"])]
    return "".join(L)


def ecrire_fiches(records):
    d = OUT / "fiches"
    d.mkdir(exist_ok=True)
    for r in records:
        (d / f"{r['id']}.md").write_text(_fiche_md(r), encoding="utf-8")
    return d


def main():
    records = construire()
    ecrire_csv(records)
    ecrire_fiches(records)
    # SOURCES-AUDIT.md est écrit par grouped.py (lisible, par famille)
    from . import grouped
    grouped.ecrire(records, OUT)
    print(f"{len(records)} fiches générées.")
    return records


if __name__ == "__main__":
    main()
