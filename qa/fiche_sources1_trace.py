"""FICHE-SOURCES-1 — trace RÉEL (lecture seule). Pour chacune des 92 sources de la vitrine, un
verdict par DEUX chemins croisés :
  (1) registre : source →(NOM_VERS_SLUG)→ réservoir → donnée (donnees.py) → robinet (catégorie+parent) ;
  (2) couches  : source → spatial_layers.data_source_id → couche ; kind thématique (couches_carte)
      = couche évaluée qui « remonte à la fiche » (les 51/53 déclarées).
Priorité FICHE > COMMUNE > OUTIL > AUTRE > AUCUN. Génère le rapport markdown sur stdout."""
from __future__ import annotations
import os, sqlalchemy as sa
from labuse.registre.donnees import DONNEES
from labuse.registre.robinets import ROBINETS
from labuse.registre import declarations as DEC
from labuse.circuit_etats import NOM_VERS_SLUG
from labuse.sources_catalog import WHERE_AFFICHEES, masquees_param

URL = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
e = sa.create_engine(URL)

# --- registre : slug -> données ; donnée -> robinets ; quoi -> sections déclarées (fiche) ---
slug2don: dict[str, list[str]] = {}
for cid, d in DONNEES.items():
    for s in d.reservoirs:
        slug2don.setdefault(s, []).append(cid)
don2rob: dict[str, list[tuple]] = {}
for rid, r in ROBINETS.items():
    for cid in r.chiffres:
        don2rob.setdefault(cid, []).append((r.categorie, r.parent, r.nom))
quoi2sec: dict[str, set] = {}
kind2fam: dict[str, str] = {}
for c in DEC.couches_carte():
    if c.get("kind"):
        kind2fam[c["kind"]] = c.get("famille", "urbanisme")
for s in DEC.charger()[0]:
    if s.categorie == "fiche":
        for l in s.donnees:
            if l.section:
                quoi2sec.setdefault(l.quoi, set()).add(l.section)
# FICHE-SOURCES-1 — les kinds STOCKÉS (spatial_layers.kind) → section de la fiche. Toute couche
# thématique « remonte à la fiche » (fait donné : 51/51). Les basemaps/repères n'ont pas de
# data_source_id (WMTS) → n'apparaissent pas ici. Section best-effort par nature de la couche.
KIND_SECTION = {
    "mvt": "§5 Risques", "georisque_alea": "§5 Risques", "cavite": "§5 Risques", "icpe": "§5 Risques",
    "sol_pollue": "§5 Risques", "ppr": "§5 Risques", "ppr_etat": "§5 Risques", "bruit_carte": "§5 Risques",
    "bruit_route": "§5 Risques", "cinquante_pas": "§5 Risques", "trait_de_cote": "§5 Risques",
    "endiguement": "§5 Risques", "bassin_versant": "§5 Risques", "tri_zone": "§5 Risques",
    "znieff": "§5 Risques", "ravine": "§5 Risques", "water": "§5 Risques", "zone_humide": "§5 Risques",
    "ens": "§5 Risques", "cimetiere": "§5 Risques", "parc_national": "§5 Risques",
    "plu_gpu_zone": "§4 Urbanisme", "plu_gpu_zone__archive_m40": "§4 Urbanisme",
    "plu_gpu_prescription": "§4 Urbanisme", "er": "§4 Urbanisme", "ebc": "§4 Urbanisme",
    "dpu": "§4 Urbanisme", "peb": "§4 Urbanisme", "sar": "§4 Urbanisme", "safer": "§4 Urbanisme",
    "artificialisation": "§4 Urbanisme", "ocs_ge": "§4 Urbanisme", "foret_publique": "§4 Urbanisme",
    "abf": "§4 Urbanisme", "construction_lineaire": "§4 Urbanisme", "construction_surfacique": "§4 Urbanisme",
    "zonage_assainissement": "§6 Réseaux", "osm_faux_positif": "§4 Urbanisme",
    "qpv": "§7 Fiscalité", "anru": "§7 Fiscalité", "zfang": "§7 Fiscalité", "frr": "§7 Fiscalité",
    "tva_primo": "§7 Fiscalité",
    "ligne_ht": "§6 Réseaux", "ligne_mt": "§6 Réseaux", "tcsp_station": "§6 Réseaux",
    "tcsp_troncon": "§6 Réseaux", "tcsp_zone": "§6 Réseaux", "transport_arret": "§6 Réseaux",
    "transport_ligne": "§6 Réseaux", "pole_echange": "§6 Réseaux", "telepherique": "§6 Réseaux",
    "axe_structurant": "§6 Réseaux", "voirie": "§6 Réseaux",
    "potentiel_foncier": "§10 Potentiel", "vefa_neuf": "§8 Marché", "zone_activite": "§8 Marché",
    "batiment": "§3 Bâti", "batiment_cosia": "§3 Bâti", "piscine_cosia": "§2 Terrain",
    "iris_insee": "§9 Quartier", "amenite": "§9 Quartier", "amenite_bpe": "§9 Quartier",
    "sup": "§4 Urbanisme", "dpf": "§5 Risques", "pente": "§2 Terrain", "friche": "§4 Urbanisme",
}
CAT_LABEL = {"couche": "carte", "fond": "carte (fond)", "copilote": "copilote", "pdf": "exports (PDF)",
             "page_client": "page client", "veille": "Radar/Veille", "projets": "Projets", "crm": "CRM",
             "notification": "notification", "admin": "admin"}

with e.connect() as c:
    sources = [(r[0], r[1]) for r in c.execute(sa.text(
        f"SELECT id, name FROM data_sources WHERE {WHERE_AFFICHEES} ORDER BY name"),
        {"masquees": masquees_param()}).all()]
    # couches par source (kinds distincts) — toute couche thématique remonte à la fiche (51/51)
    src_kinds: dict[int, set] = {}
    for sid, kind in c.execute(sa.text(
        "SELECT data_source_id, kind FROM spatial_layers WHERE data_source_id IS NOT NULL GROUP BY data_source_id, kind")).all():
        src_kinds.setdefault(sid, set()).add(kind)
    # sources de la CASCADE servie (dryrun_cascade_results) — le manifeste réel « sources de la fiche »
    cascade_ids = {r[0] for r in c.execute(sa.text(
        "SELECT DISTINCT data_source_id FROM dryrun_cascade_results WHERE data_source_id IS NOT NULL")).all()}

rows, counts, aucun = [], {"FICHE": 0, "COMMUNE": 0, "OUTIL": 0, "AUTRE": 0, "AUCUN": 0}, []
for sid, name in sources:
    slug = NOM_VERS_SLUG.get(name)
    donnees = sorted(set(slug2don.get(slug, []))) if slug else []
    robs = [rb for cid in donnees for rb in don2rob.get(cid, [])]
    # DÉCLARÉE sur la fiche parcelle (declarations/fiche/, désormais complètes) — signal fort :
    # une donnée déclarée s'affiche (prouvé FICHE-RANGEMENT-2 lot 2). Rattrape les données de maille
    # commune MONTRÉES sur la parcelle (ex. taxe foncière REI, tuile §7) que le parent du robinet
    # étiquette « fiche_commune ».
    fp = [cid for cid in donnees if cid in quoi2sec or any(cat == "fiche" and par == "fiche_parcelle" for cat, par, _ in don2rob.get(cid, []))]
    fc = [cid for cid in donnees if any(cat == "fiche" and par == "fiche_commune" for cat, par, _ in don2rob.get(cid, []))]
    outils = sorted({nom for cat, par, nom in robs if cat == "outil"})
    autres = sorted({CAT_LABEL.get(cat, cat) for cat, par, nom in robs
                     if cat not in ("fiche", "outil")} | ({"Radar"} if any(cat == "fiche" and par not in ("fiche_parcelle", "fiche_commune") for cat, par, _ in robs) else set()))
    kinds = src_kinds.get(sid, set())
    in_cascade = sid in cascade_ids
    lignes = section = note = ""
    if fp or kinds or in_cascade:
        verdict = "FICHE"
        secs = set()
        for cid in fp:
            for cat, par, nom in don2rob.get(cid, []):
                if cat == "fiche" and par == "fiche_parcelle":
                    secs.add(nom)
            secs |= quoi2sec.get(cid, set())
        for k in kinds:
            secs.add(KIND_SECTION.get(k, "carte/cascade"))
        parts = [DONNEES[c].libelle for c in fp[:4]]
        if kinds:
            parts.append(f"couche(s) : {', '.join(sorted(kinds)[:4])}" + (" …" if len(kinds) > 4 else ""))
        elif in_cascade:
            parts.append("couche évaluée (cascade servie)")
        lignes = "; ".join(parts)
        section = " · ".join(sorted(s for s in secs if s and s not in ("carte", "carte/cascade"))[:5]) or "carte/cascade"
        if outils:
            note = "aussi OUTIL: " + ", ".join(outils[:2])
    elif fc:
        verdict = "COMMUNE"
        section = " · ".join(sorted({nom for cid in fc for cat, par, nom in don2rob.get(cid, []) if cat == "fiche" and par == "fiche_commune"})[:5])
        lignes = "; ".join(DONNEES[c].libelle for c in fc[:5])
        if outils:
            note = "aussi OUTIL: " + ", ".join(outils[:2])
    elif outils:
        verdict = "OUTIL"; note = ", ".join(outils[:4])
    elif autres or kinds:
        verdict = "AUTRE"
        note = ", ".join(sorted(set(autres) | ({"carte"} if kinds and not kthem else set()))) or "carte"
    else:
        verdict = "AUCUN"; note = ("slug " + slug if slug else "aucun réservoir (NOM_VERS_SLUG)") + " — rien de visible"
        aucun.append(name)
    counts[verdict] += 1
    rows.append((name, verdict, lignes, section, note))

print("# FICHE-SOURCES-1 — quelles sources alimentent la fiche parcelle\n")
print(f"**{len(sources)} sources de la vitrine** (data_sources WHERE_AFFICHEES). Trace réelle, deux "
      "chemins croisés : (1) registre `NOM_VERS_SLUG → donnees.py → robinets.py` (catégorie+parent) ; "
      "(2) couches `spatial_layers.data_source_id`, kind thématique (`couches_carte`, les 53 qui "
      "remontent à la fiche). Priorité FICHE > COMMUNE > OUTIL > AUTRE > AUCUN. **Lecture seule.**\n")
print("## Les chiffres")
print(f"- **{counts['FICHE']}** sources sur {len(sources)} alimentent la **fiche parcelle** (FICHE).")
print(f"- **{counts['COMMUNE']}** alimentent la **fiche commune** seulement (COMMUNE).")
print(f"- **{counts['OUTIL']}** alimentent un **outil** seulement (OUTIL).")
print(f"- **{counts['AUTRE']}** alimentent **autre chose** (carte seule / Radar / copilote / exports / page client).")
print(f"- **{counts['AUCUN']}** n'alimentent **rien de visible** (AUCUN).\n")
print("## Tableau des 92 sources\n")
print("| Source | Verdict | Ligne(s) de la fiche | Section | Note |")
print("|---|---|---|---|---|")
for name, verdict, lignes, section, note in rows:
    print(f"| {name} | {verdict} | {lignes} | {section} | {note} |")
print("\n## Sources qui n'alimentent rien de visible (AUCUN)\n")
print("\n".join(f"- {a}" for a in aucun) if aucun else "*(aucune)*")
print("""
Réconciliation (vérifiée à la main) — les deux AUCUN sont RÉELS, pas des trous à combler :
- **SIRENE** (data_sources id 21) : les données SIRENE de la fiche (identité PM, événements
  propriétaire, concurrents) viennent de « **SIRENE établissements géolocalisés** » (id 86, verdict
  FICHE) et de « Recherche d'entreprises (DINUM) » (FICHE). L'entrée « SIRENE » nue est un doublon
  de catalogue qu'aucune donnée ni couche ne référence.
- **VRD / assainissement (SPANC)** : source manuelle du catalogue ; sur la fiche, le poste VRD est
  SAISI par le client (donnée `projet`, sans réservoir) — la source n'alimente aucune ligne servie.

## Notes de méthode
- **FICHE** = la source alimente ≥1 élément de la fiche parcelle, établi par l'un de : (a) donnée
  servie par un robinet `fiche_parcelle` ; (b) donnée DÉCLARÉE dans `declarations/fiche/` (surfaces
  parcelle, complètes depuis FICHE-RANGEMENT-2 lot 2) ; (c) couche `spatial_layers.data_source_id`
  (les 51/53 couches thématiques « remontent à la fiche ») ; (d) source de la cascade servie
  (`dryrun_cascade_results`). La « section » est au mieux : robinet/déclaration pour (a)(b), nature
  de la couche pour (c)(d).
- Les sous-sources Géorisques granulaires (mvt/ICPE/cavités/sites-sols) et les couches (OCS, forêt,
  EDF HTA, GéoLittoral, Potentiel foncier…) alimentent la fiche par leur COUCHE (chemin c/d) ; leurs
  DONNÉES cascade sont attribuées au réservoir agrégé `georisques_api` — attribution registre grossière
  mais visible côté fiche (à affiner si on veut la source granulaire au « i »).
- Rien n'a été corrigé ni rattaché (lecture seule).""")
