"""CIRCUIT-5 — LES VERROUS. Un verrou = une phrase en français + un test qui la fait
respecter + un endroit sur la page où elle se lit (règle 1 du mandat).

Tous les verrous sont réunis dans UNE commande — `labuse circuit verrous` — qui les joue
dans l'ordre des lots et sort en erreur au premier cassé. Elle est jouée par pytest
(`tests/verrous/`, marque `verrous`), par la sonde de nuit (résultat au Journal), et par
`deploy.sh` avant tout déploiement (règle 2).

Trois verdicts :
  · `ok`        — la phrase est vraie, la preuve le dit ;
  · `casse`     — la phrase est fausse : la commande sort en erreur, le déploiement refuse ;
  · `a_decider` — rien de cassé, mais une question attend le geste de Vic (orphelines à
    purger, réservoirs sans lecteur) : affiché au Résumé, ne bloque jamais un déploiement.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from sqlalchemy import event, text

# ── le cadre ────────────────────────────────────────────────────────────────────────────


@dataclass
class ResultatVerrou:
    id: str
    phrase: str
    verdict: str                    # ok | casse | a_decider
    preuve: str                     # une ligne lisible (ce qui a été mesuré)
    details: list[str] = field(default_factory=list)   # les éléments en cause, s'il y en a


@dataclass(frozen=True)
class Verrou:
    id: str
    lot: int
    phrase: str
    jouer: Callable[..., ResultatVerrou]    # jouer(db) — db peut être ignoré (verrous statiques)


# ── outillage : les noms de tables dans une requête ─────────────────────────────────────

#: FROM/JOIN/INTO/UPDATE/DELETE FROM <ident> — les faux positifs (imports Python, alias…)
#: sont éliminés en ne retenant que les identifiants qui SONT des relations du schéma.
_RE_TABLE = re.compile(
    r"\b(?:from|join|into|update|delete\s+from)\s+([a-zA-Z_][a-zA-Z0-9_.]*)", re.IGNORECASE)

#: suffixes de l'échange CIRCUIT-3 (quarantaine) : `x__attente`/`x__precedente` appartiennent
#: au même réservoir que `x`.
_SUFFIXES_ECHANGE = ("__attente", "__precedente")


def _normaliser(ident: str) -> str:
    ident = ident.split(".")[-1].strip('"').lower()
    for suf in _SUFFIXES_ECHANGE:
        if ident.endswith(suf):
            ident = ident[: -len(suf)]
    return ident


def tables_citees(texte: str) -> set[str]:
    """Les identifiants candidats (après FROM/JOIN/INTO/UPDATE/DELETE FROM), normalisés."""
    return {_normaliser(m.group(1)) for m in _RE_TABLE.finditer(texte)}


_RE_PREMIER_IDENT = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)")


def table_declaree(champ: str) -> str | None:
    """Le nom de table d'un champ `Donnee.table` — format réel du registre : `parcels.surface_m2`,
    `commune_contexte_sru (objectif_pct, taux_lls)`, `spatial_layers (kind=znieff)`,
    `(web — aucun réservoir…)` (→ None : pas une table)."""
    m = _RE_PREMIER_IDENT.match(champ)
    return _normaliser(m.group(1)) if m else None


def relations_schema(db) -> set[str]:
    """Toutes les relations du schéma public (tables, vues, matérialisations, partitions)."""
    rows = db.execute(text(
        "SELECT c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public' "
        "WHERE c.relkind IN ('r', 'm', 'v', 'p')")).scalars().all()
    return {r.lower() for r in rows}


@contextmanager
def journal_requetes(bind) -> Iterator[set[str]]:
    """Capture les tables touchées par TOUTES les requêtes émises pendant le bloc (lecture à
    l'exécution du verrou V1b — le « journal des requêtes de la session » du mandat)."""
    touchees: set[str] = set()

    def _capter(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        touchees.update(tables_citees(statement))

    engine = getattr(bind, "engine", bind)
    event.listen(engine, "before_cursor_execute", _capter)
    try:
        yield touchees
    finally:
        event.remove(engine, "before_cursor_execute", _capter)


# ── LOT 1 — le verrou des tables ────────────────────────────────────────────────────────

_MOTEURS_DIR = Path(__file__).parent / "registre" / "moteurs"


def _carte() -> set[str]:
    from .registre import tables as T
    return {t.lower() for t in T.tables_carte()}


def verrou_tables_statique(db=None, *, sources: list[Path] | None = None,
                           schema: set[str] | None = None) -> ResultatVerrou:
    """V1a — analyse statique : les noms de tables dans les requêtes des moteurs du registre
    et des passe-plats (`Donnee.table`) sont tous dans la carte. Seul un candidat qui EST une
    relation du schéma est une violation (le reste = faux positifs du texte Python : imports,
    prose, tuilages WMTS distants). `sources`/`schema` sont surchargés par le test de preuve
    (une fonction témoin qui lit une table orpheline doit CASSER)."""
    from .registre.donnees import DONNEES

    fichiers = sorted(sources if sources is not None else _MOTEURS_DIR.glob("*.py"))
    if schema is None and db is not None:
        schema = relations_schema(db)
    if schema is None:
        return ResultatVerrou("V1a", PHRASES["V1a"], "casse",
                              "injouable sans schéma (base indisponible)")
    carte = _carte()
    hors_carte: list[str] = []
    for f in fichiers:
        candidats = tables_citees(Path(f).read_text(encoding="utf-8"))
        for t in sorted(candidats):
            if t not in carte and t in schema:
                hors_carte.append(f"{Path(f).name} : {t}")
    # les passe-plats : chaque table déclarée par une donnée doit être dans la carte
    for cid, d in DONNEES.items():
        t = table_declaree(d.table) if d.table else None
        if t and t not in carte and t in schema:
            hors_carte.append(f"donnée {cid} : table déclarée {d.table} hors carte")
    if hors_carte:
        return ResultatVerrou("V1a", PHRASES["V1a"], "casse",
                              f"{len(hors_carte)} lecture(s) hors carte", hors_carte)
    return ResultatVerrou("V1a", PHRASES["V1a"], "ok",
                          f"{len(fichiers)} module(s) moteur + {len(DONNEES)} données passés au crible")


def verrou_tables_execution(db) -> ResultatVerrou:
    """V1b — lecture à l'exécution : un passage de la sonde sur les témoins ne touche aucune
    table hors carte (journal des requêtes de la session)."""
    from . import sonde_circuit

    carte = _carte()
    schema = relations_schema(db)
    with journal_requetes(db.get_bind()) as touchees:
        sonde_circuit.verifier_robinets(db)
    reelles = {t for t in touchees if t in schema}
    hors = sorted(reelles - carte)
    if hors:
        return ResultatVerrou("V1b", PHRASES["V1b"], "casse",
                              f"{len(hors)} table(s) touchée(s) hors carte pendant la sonde", hors)
    return ResultatVerrou("V1b", PHRASES["V1b"], "ok",
                          f"{len(reelles)} tables touchées pendant la sonde, toutes dans la carte")


def verrou_tables_orphelines(db) -> ResultatVerrou:
    """V1c — les orphelines sont connues, listées, et attendent le geste de Vic (jamais un
    DROP). Une orpheline SANS action proposée est un trou de curation : elle est nommée."""
    from .registre import tables as T

    orph = sorted(T.orphelines(relations_schema(db)))
    sans_action = [t for t in orph if t not in T.ACTIONS_PROPOSEES]
    if sans_action:
        return ResultatVerrou("V1c", PHRASES["V1c"], "casse",
                              f"{len(sans_action)} orpheline(s) sans action proposée "
                              f"(docs/CIRCUIT/TABLES-ORPHELINES.md à compléter)", sans_action)
    if orph:
        return ResultatVerrou("V1c", PHRASES["V1c"], "a_decider",
                              f"{len(orph)} orpheline(s) à purger/archiver (labuse tables purger)", orph)
    return ResultatVerrou("V1c", PHRASES["V1c"], "ok", "aucune table orpheline dans le schéma")


def verrou_reservoirs_sans_lecteur(db=None) -> ResultatVerrou:
    """V1d — chaque réservoir de la vitrine est lu par au moins une donnée du registre ; un
    réservoir sans lecteur pose la question « source à retirer, ou lecteur manquant ? »."""
    from .registre import tables as T
    from .registre.donnees import DONNEES

    # un réservoir est LU si une donnée le nomme (reservoirs=), si elle déclare une de ses
    # tables (table=), ou si elle déclare une de ses couches (kind=… dans spatial_layers).
    couche_vers_slugs: dict[str, set[str]] = {}
    for slug, rt in T.RESERVOIR_TABLES.items():
        for k in rt.couches:
            couche_vers_slugs.setdefault(k, set()).add(slug)
    lus = {res for d in DONNEES.values() for res in d.reservoirs}
    for d in DONNEES.values():
        if not d.table:
            continue
        t = table_declaree(d.table)
        if t:
            lus.update(T.reservoirs_de(t))
        for k in re.findall(r"kind=([a-zA-Z_0-9]+)", d.table):
            lus.update(couche_vers_slugs.get(k, ()))
    sans_lecteur = sorted(
        slug for slug, rt in T.RESERVOIR_TABLES.items()
        if rt.tables and rt.note is None and slug not in lus)
    if sans_lecteur:
        return ResultatVerrou("V1d", PHRASES["V1d"], "a_decider",
                              f"{len(sans_lecteur)} réservoir(s) sans lecteur — source à retirer, "
                              "ou lecteur manquant ?", sans_lecteur)
    return ResultatVerrou("V1d", PHRASES["V1d"], "ok",
                          "chaque réservoir servi est lu par au moins une donnée du registre")


# ── LOT 2 — le verrou des sources : 68, pas un de plus ─────────────────────────────────


def analyse_catalogue(rows: list[dict]) -> list[str]:
    """Discipline des statuts (pur, testable sans base) : chaque ligne de `data_sources` est
    soit SERVIE (vitrine), soit porte un statut de première classe qui dit pourquoi elle n'y
    est pas — alias (avec sa cible en vitrine), retiree (avec date et raison), hub, a_faire
    (avec son chantier en note), ou masquée d'un geste au dashboard (`affichage_desactive`).
    Un doublon caché (statut vitrine + note DOUBLON) est une violation."""
    from .sources_catalog import est_affichee

    par_id = {r.get("id"): r for r in rows}
    pbs: list[str] = []
    for r in rows:
        nom, statut = r.get("name") or "?", (r.get("status") or "").lower()
        affichee = est_affichee(nom, r.get("technical_notes"), r.get("status"),
                                r.get("affichage_desactive"))
        if affichee:
            if r.get("alias_de"):
                pbs.append(f"{nom} : en vitrine ET alias_de={r['alias_de']} (contradiction)")
            continue
        if r.get("affichage_desactive"):
            continue        # masquée d'un geste admin (CONNEXIONS-2) — raison vivante en base
        if statut == "alias":
            cible = par_id.get(r.get("alias_de"))
            if not cible:
                pbs.append(f"{nom} : alias sans cible (alias_de manquant ou inconnu)")
            elif not est_affichee(cible.get("name"), cible.get("technical_notes"),
                                  cible.get("status"), cible.get("affichage_desactive")):
                pbs.append(f"{nom} : alias d'une ligne HORS vitrine ({cible.get('name')})")
        elif statut == "retiree":
            if not (r.get("retiree_le") and r.get("retiree_raison")):
                pbs.append(f"{nom} : retirée sans date ou sans raison")
        elif statut == "hub":
            pass
        elif statut == "a_faire":
            if not (r.get("technical_notes") or "").strip():
                pbs.append(f"{nom} : a_faire sans chantier nommé (note vide)")
        else:
            pbs.append(f"{nom} : hors vitrine avec un statut de vitrine ({statut or 'vide'}) "
                       "— doublon caché ou note-préfixe sans statut de première classe")
    return pbs


def _lignes_catalogue(db) -> list[dict]:
    return [dict(r) for r in db.execute(text(
        "SELECT id, name, status, technical_notes, affichage_desactive,"
        " alias_de, retiree_le, retiree_raison FROM data_sources")).mappings().all()]


def verrou_sources_statuts(db) -> ResultatVerrou:
    """V2b — chaque ligne hors vitrine porte un statut de première classe motivé."""
    pbs = analyse_catalogue(_lignes_catalogue(db))
    if pbs:
        return ResultatVerrou("V2b", PHRASES["V2b"], "casse", f"{len(pbs)} ligne(s) indisciplinée(s)", pbs)
    return ResultatVerrou("V2b", PHRASES["V2b"], "ok", "toutes les lignes hors vitrine disent pourquoi")


def verrou_sources_comptes(db) -> ResultatVerrou:
    """V2a — le même nombre partout : vitrine SQL (`WHERE_AFFICHEES`), prédicat Python
    (`est_affichee`), page (`flux.construire_flux` — ce que sert /admin/circuit), et carte
    (chaque source servie a son slug dans le pont ET dans la carte table → réservoir)."""
    from . import flux
    from .circuit_etats import NOM_VERS_SLUG
    from .registre import tables as T
    from .sources_catalog import WHERE_AFFICHEES, est_affichee, masquees_param

    n_sql = db.execute(text(f"SELECT count(*) FROM data_sources WHERE {WHERE_AFFICHEES}"),
                       {"masquees": masquees_param()}).scalar() or 0
    rows = _lignes_catalogue(db)
    servies = [r for r in rows if est_affichee(r["name"], r["technical_notes"], r["status"],
                                               r["affichage_desactive"])]
    n_py = len(servies)
    n_page = len(flux.construire_flux(db)["sources"])
    pbs: list[str] = []
    for r in servies:
        slug = NOM_VERS_SLUG.get(r["name"])
        if not slug:
            pbs.append(f"{r['name']} : servie mais absente du pont NOM_VERS_SLUG")
        elif slug not in T.RESERVOIR_TABLES:
            pbs.append(f"{r['name']} : slug {slug} absent de la carte table → réservoir")
    if n_sql == n_py == n_page and not pbs:
        return ResultatVerrou("V2a", PHRASES["V2a"], "ok",
                              f"{n_sql} = {n_py} = {n_page} (vitrine SQL, prédicat, page) ; "
                              f"{len(servies)} sources servies toutes dans la carte")
    if n_sql != n_py or n_sql != n_page:
        pbs.insert(0, f"comptes divergents : SQL {n_sql} · Python {n_py} · page {n_page}")
    return ResultatVerrou("V2a", PHRASES["V2a"], "casse", pbs[0], pbs)


# ── LOT 3 — le verrou des versions : une seule version servie, partout ─────────────────


def verrou_versions_generations(db=None, *, schema: set[str] | None = None) -> ResultatVerrou:
    """V3a — pour chaque table servie d'un réservoir, les seules générations admises dans le
    schéma sont `x`, `x__attente` (échange en cours) et `x__precedente` (retour possible) ;
    et les tuiles servies sont fabriquées pour LE run du manifeste. Un `x__2025`, un
    `x__essai`, deux millésimes côte à côte = verrou cassé."""
    from .registre import tables as T

    if schema is None and db is not None:
        schema = relations_schema(db)
    if schema is None:
        return ResultatVerrou("V3a", PHRASES["V3a"], "casse", "injouable sans schéma")
    pbs: list[str] = []
    for base in sorted(T.tables_reservoirs()):
        for rel in schema:
            if rel.startswith(base + "__") and rel not in (base + "__attente", base + "__precedente"):
                pbs.append(f"{base} : génération inattendue {rel}")
    if db is not None:
        try:
            from . import runs
            run_mvt = db.execute(text(
                "SELECT value FROM mvt_meta WHERE key = 'run_label'")).scalar() \
                if db.execute(text("SELECT to_regclass('mvt_meta')")).scalar() else None
            run_servi = runs.current()
            if run_mvt and run_servi and run_mvt != run_servi:
                pbs.append(f"tuiles fabriquées pour {run_mvt}, manifeste sert {run_servi}")
        except Exception as e:  # noqa: BLE001
            pbs.append(f"pointeurs du manifeste illisibles : {e.__class__.__name__}")
    if pbs:
        return ResultatVerrou("V3a", PHRASES["V3a"], "casse", f"{len(pbs)} génération(s) en trop", pbs)
    return ResultatVerrou("V3a", PHRASES["V3a"], "ok",
                          f"{len(T.tables_reservoirs())} tables de réservoir, une génération servie chacune")


def verrou_eau_ancienne(db) -> ResultatVerrou:
    """V3b — mesurée MAINTENANT (pas les archives du journal) : aucune eau ancienne ouverte
    hors « gelé, étiqueté ». S'il en reste une, le verrou nomme la donnée et le robinet."""
    from . import sonde_circuit

    lignes = sonde_circuit.eau_lignes(db)
    ouvertes = [x for x in lignes if x[5] == "ouvert"]
    etiquetees = [x for x in lignes if x[5] == "etiquete"]
    if ouvertes:
        return ResultatVerrou("V3b", PHRASES["V3b"], "casse",
                              f"{len(ouvertes)} eau(x) ancienne(s) ouverte(s)",
                              [f"{c} → {r} ({m})" for (c, r, _t, _a, m, _s) in ouvertes])
    return ResultatVerrou("V3b", PHRASES["V3b"], "ok",
                          f"aucune eau ouverte ({len(etiquetees)} gel(s) assumé(s) étiqueté(s))")


def verrou_sonde_ids(db) -> ResultatVerrou:
    """V3c — la sonde écrit des ids (dette CIRCUIT-P3) : toute ligne d'écart ou d'eau dont le
    côté correspond à un robinet du registre porte son `robinet_id`, et tout `chiffre_id`
    écrit appartient au registre."""
    from .registre import CHIFFRES, ROBINETS

    pbs: list[str] = []
    for table, lib, cible in (("circuit_ecarts", "robinet_a", "robinet_a_id"),
                              ("circuit_ecarts", "robinet_b", "robinet_b_id"),
                              ("circuit_eau_ancienne", "robinet", "robinet_id")):
        rows = db.execute(text(
            f"SELECT DISTINCT {lib} FROM {table} WHERE {cible} IS NULL")).scalars().all()  # noqa: S608
        for v in rows:
            if v in ROBINETS:
                pbs.append(f"{table}.{lib} = {v!r} : robinet du registre SANS robinet_id")
    chiffres = db.execute(text(
        "SELECT DISTINCT chiffre_id FROM circuit_ecarts "
        "UNION SELECT DISTINCT chiffre_id FROM circuit_eau_ancienne")).scalars().all()
    admis_hors_registre = {"exports_recette", "mots_interdits"}   # cas de la recette PDF (0-bis)
    for c in chiffres:
        if c not in CHIFFRES and c not in admis_hors_registre:
            pbs.append(f"chiffre_id hors registre dans la sonde : {c!r}")
    if pbs:
        return ResultatVerrou("V3c", PHRASES["V3c"], "casse", f"{len(pbs)} ligne(s) non attribuable(s)", pbs)
    return ResultatVerrou("V3c", PHRASES["V3c"], "ok",
                          "écarts et eau ancienne attribuables (ids du registre)")


# ── LOT 4 — le verrou des communes : la bonne ligne pour la bonne commune ───────────────


def verrou_communes_fk(db) -> ResultatVerrou:
    """V4a — chaque table à la maille commune porte sa clé étrangère sur le référentiel des
    24 : un code hors référentiel ne peut plus ENTRER. Contrainte absente = cassé ; contrainte
    NOT VALID (lignes fautives héritées) = à décider, les lignes sont comptées."""
    from . import referentiel_communes as RC

    etat = RC.etat_fks(db)
    absentes = [f"{t} : {e}" for t, e in etat.items() if e == "absente"]
    heritees = [f"{t} : {e}" for t, e in etat.items() if e.startswith("not_valid")]
    if absentes:
        return ResultatVerrou("V4a", PHRASES["V4a"], "casse",
                              f"{len(absentes)} table(s) sans clé étrangère commune", absentes)
    if heritees:
        return ResultatVerrou("V4a", PHRASES["V4a"], "a_decider",
                              "l'entrée est verrouillée partout ; lignes fautives HÉRITÉES à corriger",
                              heritees)
    return ResultatVerrou("V4a", PHRASES["V4a"], "ok",
                          f"{len(etat)} tables sous clé étrangère, toutes validées")


#: lot 4.2 — les deux communes témoins de la permutation (choisies dans l'échantillon : le
#: producteur les distingue nettement sur CatNat — 17 vs 22 arrêtés).
COMMUNES_PERMUTATION: tuple[tuple[str, str], ...] = (
    ("97410", "Saint-Benoît"), ("97418", "Sainte-Marie"))


def _payload_contexte(db, insee: str, nom: str) -> dict:
    """Le payload que la page sert : le cache `commune_contexte_cache` (c'est LUI l'écran —
    lu par la session du verrou, jamais par un TestClient qui pointerait une autre base)."""
    row = db.execute(text(
        "SELECT payload FROM commune_contexte_cache WHERE insee = :i OR commune = :n "
        "ORDER BY computed_at DESC LIMIT 1"), {"i": insee, "n": nom}).scalar()
    return row or {}


def verrou_communes_permutation(db=None, *, payloads: dict[str, dict] | None = None) -> ResultatVerrou:
    """V4b — pour chaque donnée à la maille commune : la valeur servie pour Saint-Benoît et
    Sainte-Marie est CELLE ATTENDUE pour chacune (identité du bloc SRU + attendus producteur
    de l'échantillon), pas seulement différente. Une jointure décalée d'une ligne ou un
    « première ligne » par défaut casse le verrou."""
    from .filtres import echantillon_communes as EC

    pbs: list[str] = []
    charge = payloads or {}
    for insee, nom in COMMUNES_PERMUTATION:
        p = charge.get(insee) or _payload_contexte(db, insee, nom)
        charge[insee] = p
        if not p:
            pbs.append(f"{nom} : aucun payload servi (cache fiche commune vide)")
            continue
        sru = p.get("sru") or {}
        if sru.get("insee") and sru["insee"] != insee:
            pbs.append(f"{nom} : le bloc SRU servi porte insee={sru['insee']} (attendu {insee}) "
                       "— ligne d'une autre commune")
        if sru.get("commune") and sru["commune"] != nom:
            pbs.append(f"{nom} : le bloc SRU servi porte commune={sru['commune']!r}")
    for r in EC.rejouer(charge):
        if r["verdict"] == "ecart":
            pbs.append(f"carte {r['carte']} · {r['insee']} : servi {r['servi']} ≠ attendu "
                       f"producteur {r['attendu']}")
    if pbs:
        return ResultatVerrou("V4b", PHRASES["V4b"], "casse", f"{len(pbs)} valeur(s) déplacée(s)", pbs)
    return ResultatVerrou("V4b", PHRASES["V4b"], "ok",
                          "Saint-Benoît et Sainte-Marie servent chacune SES valeurs "
                          "(identité SRU + attendus producteur)")


def verrou_communes_frontiere(db, *, temoins: dict | None = None) -> ResultatVerrou:
    """V4c — trois parcelles témoins AU CONTACT d'une limite communale : la commune de
    rattachement et la zone PLU au centroïde sont celles de LEUR commune (partition GPU
    DU_<insee>) — une couche de la commune voisine collée par erreur casse le verrou.
    `temoins` est injectable par le test de preuve (attendus décalés → cassé)."""
    from .filtres.echantillon_communes import DOSSIER
    import json as _json

    doc = temoins if temoins is not None else _json.loads(
        (DOSSIER / "frontieres.json").read_text(encoding="utf-8"))
    pbs: list[str] = []
    mesures = 0
    for l in doc["lignes"]:
        row = db.execute(text(
            "SELECT p.commune,"
            " (SELECT sl.attrs->>'partition' FROM spatial_layers sl"
            "  WHERE sl.kind = 'plu_gpu_zone' AND ST_Contains(sl.geom, ST_Centroid(p.geom))"
            "  LIMIT 1)"
            " FROM parcels p WHERE p.idu = :i"), {"i": l["idu"]}).first()
        if row is None:
            pbs.append(f"{l['idu']} : parcelle témoin absente du cadastre servi")
            continue
        mesures += 1
        commune, partition = row
        if commune != l["commune_attendue"]:
            pbs.append(f"{l['idu']} : rattachée à {commune!r} (attendu {l['commune_attendue']!r}, "
                       f"voisine {l['voisine']})")
        if partition and partition != f"DU_{l['insee_attendu']}":
            pbs.append(f"{l['idu']} : zone PLU du document {partition} (attendu "
                       f"DU_{l['insee_attendu']}) — couche d'une autre commune sous le centroïde")
    if pbs:
        return ResultatVerrou("V4c", PHRASES["V4c"], "casse", f"{len(pbs)} témoin(s) déplacé(s)", pbs)
    return ResultatVerrou("V4c", PHRASES["V4c"], "ok",
                          f"{mesures} parcelles frontière : commune et document PLU de LEUR commune")


def verrou_communes_echantillons(db=None) -> ResultatVerrou:
    """V4d — l'échantillon producteur couvre TOUTE la fiche commune : 15 cartes × 24
    communes, chacune avec un attendu lu chez le producteur OU une ligne à valider motivée
    (ECHANTILLONS-A-VALIDER.md) — jamais un trou silencieux."""
    from .filtres.echantillon_communes import CARTES, problemes_structure

    pbs = problemes_structure()
    if pbs:
        return ResultatVerrou("V4d", PHRASES["V4d"], "casse", f"{len(pbs)} trou(s) d'échantillon", pbs)
    return ResultatVerrou("V4d", PHRASES["V4d"], "ok",
                          f"{len(CARTES)} cartes × 24 communes : un attendu ou un à-valider partout")


# ── LOT 5 — le verrou des concepts et des moteurs ───────────────────────────────────────


def _normaliser_texte(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return " ".join(s.split())


def verrou_concepts(db=None) -> ResultatVerrou:
    """V5a — un concept = un id : deux données au libellé normalisé ou à la définition
    identiques ne peuvent pas coexister avec deux ids ; les seules exceptions sont les
    groupes ASSUMÉS (DEFINITIONS_PARTAGEES_ASSUMEES, motivés dans CONCEPTS-CANONIQUES.md)."""
    from collections import defaultdict

    from .registre.donnees import DEFINITIONS_PARTAGEES_ASSUMEES, DONNEES

    pbs: list[str] = []
    for champ in ("libelle", "definition"):
        groupes: dict[str, list[str]] = defaultdict(list)
        for cid, d in DONNEES.items():
            groupes[_normaliser_texte(getattr(d, champ))].append(cid)
        for texte, ids in groupes.items():
            if len(ids) < 2:
                continue
            if any(set(ids) <= assume for assume in DEFINITIONS_PARTAGEES_ASSUMEES):
                continue
            pbs.append(f"{champ} partagé par {sorted(ids)} : {texte[:80]!r}")
    if pbs:
        return ResultatVerrou("V5a", PHRASES["V5a"], "casse", f"{len(pbs)} concept(s) en double", pbs)
    return ResultatVerrou("V5a", PHRASES["V5a"], "ok",
                          f"{len(_donnees_count())} données, aucun libellé ni définition en double "
                          f"hors {len(DEFINITIONS_PARTAGEES_ASSUMEES)} groupes assumés")


def _donnees_count():
    from .registre.donnees import DONNEES
    return DONNEES


def verrou_une_donnee_une_fonction(db=None) -> ResultatVerrou:
    """V5b — une donnée = une fonction : chaque id porte UN producteur nommé ; plus aucun
    `sql_propre` ni `front` (les gardes CIRCUIT-2, réunies ici) ; le registre est intègre."""
    from .registre import verifier
    from .registre.donnees import DONNEES

    pbs = [f"donnée {cid} : calcul {d.calcul} (interdit — à rapatrier au moteur)"
           for cid, d in DONNEES.items() if d.calcul in ("sql_propre", "front")]
    pbs += [f"donnée {cid} : sans fonction productrice"
            for cid, d in DONNEES.items() if not (d.fonction or "").strip()]
    pbs += [f"registre : {p}" for p in verifier()]
    if pbs:
        return ResultatVerrou("V5b", PHRASES["V5b"], "casse", f"{len(pbs)} donnée(s) sans fonction unique", pbs)
    return ResultatVerrou("V5b", PHRASES["V5b"], "ok",
                          f"{len(DONNEES)} données : une fonction chacune, sql_propre = 0, front = 0")


def verrou_couples_sondes(db=None) -> ResultatVerrou:
    """V5c — zéro couple silencieux : chaque couple (donnée, robinet) déclaré est comparé par
    la sonde (SONDE_COUVRE), ou mono-robinet (aucune comparaison possible — vérité tenue par
    golden/règles), ou porte sa raison nommée (NON_SONDES). Un couple sans rien = cassé."""
    from .registre import ROBINETS
    from .sonde_circuit import NON_SONDES, SONDE_COUVRE

    robs_par_chiffre: dict[str, set[str]] = {}
    for rid, r in ROBINETS.items():
        for c in r.chiffres:
            robs_par_chiffre.setdefault(c, set()).add(rid)
    couverts = raisonnes = monos = 0
    pbs: list[str] = []
    for c, robs in sorted(robs_par_chiffre.items()):
        for r in sorted(robs):
            if len(robs) == 1:
                monos += 1              # pas de partenaire de comparaison : golden/règles font foi
            elif r in SONDE_COUVRE.get(c, ()):
                couverts += 1
            elif c in NON_SONDES:
                raisonnes += 1
            else:
                pbs.append(f"couple silencieux : ({c}, {r}) — ni sondé, ni raison déclarée")
    if pbs:
        return ResultatVerrou("V5c", PHRASES["V5c"], "casse", f"{len(pbs)} couple(s) silencieux", pbs)
    return ResultatVerrou("V5c", PHRASES["V5c"], "ok",
                          f"{couverts} couples sondés · {raisonnes} raisonnés (NON_SONDES) · "
                          f"{monos} mono-robinet (golden/règles)")


# ── le registre des verrous (complété lot par lot) ──────────────────────────────────────

PHRASES: dict[str, str] = {
    "V1a": "Aucun moteur ne lit une table hors de la carte table → réservoir (analyse statique).",
    "V1b": "Pendant un passage de la sonde sur les témoins, aucune table hors carte n'est touchée.",
    "V1c": "Toute table du schéma appartient à la carte, ou est une orpheline listée qui attend le geste de Vic.",
    "V1d": "Chaque réservoir servi est lu par au moins une donnée — aucun réservoir muet ne dort dans la vitrine.",
    "V2a": "Le nombre de sources servies est LE MÊME partout : vitrine SQL, prédicat Python, page — et chacune a sa place dans la carte.",
    "V2b": "Toute ligne du catalogue hors vitrine dit pourquoi : alias (cible en vitrine), retirée (date + raison), hub, ou chantier nommé.",
    "V3a": "Chaque réservoir n'a qu'une version servie : ses seules générations sont la table, son __attente et sa __precedente — et les tuiles servent le run du manifeste.",
    "V3b": "Après une bascule, zéro eau ancienne : rien d'ouvert hors « gelé, étiqueté » — sinon le verrou nomme la donnée et le robinet.",
    "V3c": "La sonde écrit des ids, plus des libellés : chaque écart et chaque eau ancienne sont attribuables à leur donnée et à leur robinet du registre.",
    "V4a": "Toute table à la maille commune porte une clé étrangère sur le référentiel des 24 — un code hors référentiel ne peut plus entrer.",
    "V4b": "Saint-Benoît sert les valeurs de Saint-Benoît, Sainte-Marie celles de Sainte-Marie — celles attendues chez le producteur, pas seulement différentes.",
    "V4c": "Sur les parcelles frontière, la commune de rattachement et la zone PLU au centroïde sont celles de LEUR commune, jamais de la voisine.",
    "V4d": "Chacune des 15 cartes de la fiche commune a, pour chacune des 24 communes, son attendu producteur ou sa ligne à valider — jamais un trou silencieux.",
    "V5a": "Un concept = un id : deux données au libellé ou à la définition identiques n'existent pas, hors synonymes assumés et motivés.",
    "V5b": "Une donnée = une fonction : chaque id porte un producteur nommé, plus aucun sql_propre ni front, et le registre est intègre.",
    "V5c": "Zéro couple silencieux : chaque couple (donnée, robinet) est sondé, mono-robinet (golden/règles), ou porte sa raison nommée.",
}

VERROUS: tuple[Verrou, ...] = (
    Verrou("V1a", 1, PHRASES["V1a"], verrou_tables_statique),
    Verrou("V1b", 1, PHRASES["V1b"], verrou_tables_execution),
    Verrou("V1c", 1, PHRASES["V1c"], verrou_tables_orphelines),
    Verrou("V1d", 1, PHRASES["V1d"], verrou_reservoirs_sans_lecteur),
    Verrou("V2a", 2, PHRASES["V2a"], verrou_sources_comptes),
    Verrou("V2b", 2, PHRASES["V2b"], verrou_sources_statuts),
    Verrou("V3a", 3, PHRASES["V3a"], verrou_versions_generations),
    Verrou("V3b", 3, PHRASES["V3b"], verrou_eau_ancienne),
    Verrou("V3c", 3, PHRASES["V3c"], verrou_sonde_ids),
    Verrou("V4a", 4, PHRASES["V4a"], verrou_communes_fk),
    Verrou("V4b", 4, PHRASES["V4b"], verrou_communes_permutation),
    Verrou("V4c", 4, PHRASES["V4c"], verrou_communes_frontiere),
    Verrou("V4d", 4, PHRASES["V4d"], verrou_communes_echantillons),
    Verrou("V5a", 5, PHRASES["V5a"], verrou_concepts),
    Verrou("V5b", 5, PHRASES["V5b"], verrou_une_donnee_une_fonction),
    Verrou("V5c", 5, PHRASES["V5c"], verrou_couples_sondes),
)


def jouer_tous(db, *, arret_premier: bool = False) -> list[ResultatVerrou]:
    """Joue tous les verrous dans l'ordre des lots. `arret_premier` : sort au premier cassé
    (comportement CLI/deploy) ; sinon joue tout (page Circuit, rapport complet)."""
    resultats: list[ResultatVerrou] = []
    for v in VERROUS:
        try:
            r = v.jouer(db)
        except Exception as e:  # un verrou qui ne peut pas se jouer est un verrou cassé
            r = ResultatVerrou(v.id, v.phrase, "casse", f"injouable : {e.__class__.__name__}: {e}")
        resultats.append(r)
        if arret_premier and r.verdict == "casse":
            break
    return resultats
