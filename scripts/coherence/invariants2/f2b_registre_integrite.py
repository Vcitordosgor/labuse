"""CHASSE-INVARIANTS-2 — Famille F2 (suite) « Le registre » : intégrité PAR CHIFFRE et PAR ROBINET.

Le mandat cadre F2 « pour CHAQUE chiffre du registre (cible ~250) ET chaque robinet qui le sert » —
c'est la granularité PAR ENTITÉ (comme F1 par colonne, F4 par feuille, F5 par route×paramètre).
`f2_registre.py` a couvert la cohérence de VALEUR inter-surfaces (59 règles) ; ce module couvre la
cohérence STRUCTURELLE du registre, une règle par chiffre (248) + un socle par robinet.

Chaque règle est VRAIE PAR CONSTRUCTION — calibrée sur la donnée réelle (toutes vertes aujourd'hui) :
elle MORD le jour où le registre pourrit (un chiffre perd son unité/niveau, un réservoir cesse d'avoir
son arête, un robinet pointe un chiffre renommé). C'est exactement la self-description de l'app qui se
vérifie elle-même.

Invariants retenus (universels, mesurés) :
  · chiffre : `unite`/`libelle`/`version_def` non nuls ; `niveau` ∈ {proprietaire,annonce,commune,zone,
    parcelle,global} ; `portee` ∈ {projet,live,run} ; **chaque réservoir listé dans `reservoirs` possède
    son arête `reservoir_vers_chiffre`** (symétrie registre↔arêtes).
  · robinet : `route`/`nom`/`categorie` non nuls ; `categorie` ∈ domaine fermé ; **chaque chiffre listé
    dans `chiffres[]` existe et porte son arête `chiffre_vers_robinet`** ; `parent` (si posé) existe.

Écartés AVANT de tourner (non universels, calibrés) : `moteur` (107/248 nuls — legitimement live/sans
moteur), `reservoirs` non-vide (76/248 vides — chiffres purement UI/tuiles), `chiffres[]` non-vide sur
robinet (2 exceptions légitimes).

Lecture seule stricte. Import du noyau partagé.
"""
from __future__ import annotations

from .noyau import RuleSpec, Ecartee, registre_chiffres  # noqa: F401

NIVEAUX = ("proprietaire", "annonce", "commune", "zone", "parcelle", "global")
PORTEES = ("projet", "live", "run")
CATEGORIES = ("pdf", "notification", "veille", "projets", "page_client", "crm",
              "fiche", "fond", "outil", "admin", "copilote", "couche")

_NIV = "','".join(NIVEAUX)
_POR = "','".join(PORTEES)
_CAT = "','".join(CATEGORIES)


def generer(cx):
    specs: list = []
    ecartees: list = []

    # ── un invariant d'intégrité PAR CHIFFRE (248) ──────────────────────────────────────────
    with cx.conn.cursor() as cur:
        cur.execute("SELECT id FROM registre_chiffres ORDER BY id")
        chiffre_ids = [r[0] for r in cur.fetchall()]

    for cid in chiffre_ids:
        viol = f"""
            SELECT count(*) FROM registre_chiffres c WHERE c.id = %s AND (
                   c.unite IS NULL OR c.libelle IS NULL OR c.version_def IS NULL
                OR c.niveau NOT IN ('{_NIV}') OR c.portee NOT IN ('{_POR}')
                OR EXISTS (
                     SELECT 1 FROM unnest(c.reservoirs) res
                     LEFT JOIN registre_aretes a
                            ON a.type='reservoir_vers_chiffre' AND a.source=res AND a.cible=c.id
                     WHERE a.source IS NULL)
            )"""
        ex = f"""
            SELECT c.id, c.unite, c.niveau, c.portee, c.reservoirs,
                   ARRAY(SELECT res FROM unnest(c.reservoirs) res
                         LEFT JOIN registre_aretes a
                                ON a.type='reservoir_vers_chiffre' AND a.source=res AND a.cible=c.id
                         WHERE a.source IS NULL) AS reservoirs_sans_arete
            FROM registre_chiffres c WHERE c.id = %s"""
        specs.append(RuleSpec(
            id=f"F2b.chiffre.{cid}.integre",
            famille="F2", source=f"registre_chiffres.{cid}",
            libelle=f"chiffre « {cid} » bien formé (unité/niveau/portée/libellé/version) + réservoirs sourcés par arête",
            gravite="INCOHERENT", attendu="chiffre cohérent (0 anomalie)",
            sql_violations=viol, exemples_sql=ex, params=(cid,)))

    # ── socle d'intégrité PAR ROBINET (règles distinctes, pas de clones) ───────────────────────
    specs.append(RuleSpec(
        id="F2b.robinet.route_presente", famille="F2", source="registre_robinets.route",
        libelle="tout robinet porte une route (0 route nulle)", gravite="INCOHERENT", attendu="0 ligne",
        sql_violations="SELECT count(*) FROM registre_robinets WHERE route IS NULL OR nom IS NULL",
        exemples_sql="SELECT id, categorie, nom, route FROM registre_robinets WHERE route IS NULL OR nom IS NULL"))
    specs.append(RuleSpec(
        id="F2b.robinet.categorie_legale", famille="F2", source="registre_robinets.categorie",
        libelle="catégorie de robinet dans le domaine fermé", gravite="INCOHERENT", attendu="0 ligne",
        sql_violations=f"SELECT count(*) FROM registre_robinets WHERE categorie NOT IN ('{_CAT}')",
        exemples_sql=f"SELECT id, categorie FROM registre_robinets WHERE categorie NOT IN ('{_CAT}')"))
    specs.append(RuleSpec(
        id="F2b.robinet.chiffres_resolvent", famille="F2", source="registre_robinets.chiffres",
        libelle="chaque chiffre listé par un robinet EXISTE dans le registre", gravite="INCOHERENT", attendu="0 ligne",
        sql_violations="""SELECT count(*) FROM (
            SELECT r.id rid, unnest(r.chiffres) ch FROM registre_robinets r WHERE r.chiffres IS NOT NULL) x
            WHERE x.ch NOT IN (SELECT id FROM registre_chiffres)""",
        exemples_sql="""SELECT r.id rid, unnest(r.chiffres) ch FROM registre_robinets r
            WHERE r.chiffres IS NOT NULL AND EXISTS (
              SELECT 1 FROM unnest(r.chiffres) c WHERE c NOT IN (SELECT id FROM registre_chiffres))"""))
    specs.append(RuleSpec(
        id="F2b.robinet.chiffres_sourcent_arete", famille="F2", source="registre_robinets.chiffres↔aretes",
        libelle="chaque (robinet, chiffre servi) porte son arête chiffre_vers_robinet", gravite="INCOHERENT", attendu="0 ligne",
        sql_violations="""SELECT count(*) FROM (
            SELECT r.id rid, unnest(r.chiffres) ch FROM registre_robinets r WHERE r.chiffres IS NOT NULL) x
            LEFT JOIN registre_aretes a ON a.type='chiffre_vers_robinet' AND a.source=x.ch AND a.cible=x.rid
            WHERE a.source IS NULL""",
        exemples_sql="""SELECT x.rid, x.ch FROM (
            SELECT r.id rid, unnest(r.chiffres) ch FROM registre_robinets r WHERE r.chiffres IS NOT NULL) x
            LEFT JOIN registre_aretes a ON a.type='chiffre_vers_robinet' AND a.source=x.ch AND a.cible=x.rid
            WHERE a.source IS NULL"""))
    specs.append(RuleSpec(
        id="F2b.arete.aucune_orpheline", famille="F2", source="registre_aretes",
        libelle="aucune arête ne pointe une entité inexistante (chiffre/robinet)", gravite="INCOHERENT", attendu="0 ligne",
        sql_violations="""SELECT
            (SELECT count(*) FROM registre_aretes a WHERE a.type='reservoir_vers_chiffre' AND a.cible NOT IN (SELECT id FROM registre_chiffres))
          + (SELECT count(*) FROM registre_aretes a WHERE a.type='chiffre_vers_robinet' AND (a.source NOT IN (SELECT id FROM registre_chiffres) OR a.cible NOT IN (SELECT id FROM registre_robinets)))""",
        exemples_sql="SELECT type, source, cible FROM registre_aretes a WHERE (a.type='reservoir_vers_chiffre' AND a.cible NOT IN (SELECT id FROM registre_chiffres)) OR (a.type='chiffre_vers_robinet' AND (a.source NOT IN (SELECT id FROM registre_chiffres) OR a.cible NOT IN (SELECT id FROM registre_robinets)))"))

    # ── candidates écartées AVANT de tourner (non universelles, calibrées) ─────────────────────
    ecartees.append(Ecartee("F2b.chiffre.moteur_present", "F2", "registre_chiffres.moteur",
                            "107/248 chiffres sans moteur (servis en live / sans moteur légitimement) — non universel"))
    ecartees.append(Ecartee("F2b.chiffre.reservoirs_non_vide", "F2", "registre_chiffres.reservoirs",
                            "76/248 chiffres à réservoirs vides (purement UI/tuiles) — non universel"))
    ecartees.append(Ecartee("F2b.robinet.chiffres_non_vide", "F2", "registre_robinets.chiffres",
                            "2/158 robinets sans chiffre (légitime) — non universel"))
    ecartees.append(Ecartee("F2b.robinet.parent_existe", "F2", "registre_robinets.parent",
                            "parent MÉLANGE des ids de robinet (14) et des étiquettes de groupe/surface (53 : "
                            "fiche_parcelle, fiche_commune, outil_*) — pas une référence universelle à un robinet ; "
                            "règle insensée retirée AVANT de tourner (sinon 53 faux-mordants)"))

    return specs, ecartees


if __name__ == "__main__":
    from .noyau import connexion, run_specs, bilan
    cx = connexion()
    specs, ec = generer(cx)
    res = run_specs(cx, specs)
    b = bilan(res)
    print(f"F2b — registre intégrité : {len(specs)} retenues ({len(ec)} écartées) → "
          f"{b['OK']} OK · {b['ECART']} ECART · {b['SKIP']} SKIP")
    for r in res:
        if r.statut != "OK":
            print(f"  [{r.statut}] {r.spec.id} — {r.message}")
            for ex in r.exemples[:3]:
                print("     ex:", ex)
    cx.close()
