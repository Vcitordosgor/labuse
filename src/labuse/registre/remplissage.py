"""CIRCUIT-6 lot 2 — le REMPLISSAGE mesuré : la donnée d'une source atteint-elle des
parcelles témoins ? (G2 — « visible ou pas, je le sais »).

Le cas d'école est le DPE : branché, « à jour », 17 lignes — fiche vide partout. Un statut
binaire ne le voit pas ; on MESURE. Pour chaque source, selon sa table réservoir
(registre/tables.py, la vérité du code) :
  · type « parcelle »  — jointure idu / parcelle_idu ;
  · type « commune »   — jointure code_insee / insee / commune ;
  · type « carte »     — présence d'objets de ses kinds dans les communes témoins ;
  · type « n.a. »      — API en direct, règles portées par le code, aucune table jointe.

Leçon de SOURCES-AUDIT (2ᵉ passe) : un 0/N ne suffit JAMAIS seul.
  · « carte » 0/N par commune = tagging commune partiel, pas une invisibilité ;
  · « parcelle » 0/N sur une source RICHE (RNIC, Radar) = ces témoins n'ont pas l'attribut.
Le verdict INVISIBLE (vide) exige la signature complète : type parcelle + 0/N témoins +
table quasi vide (< SEUIL_QUASI_VIDE lignes). Jamais d'intersection spatiale par parcelle
(mesurée à 43–70 s l'appel — inutilisable).
"""
from __future__ import annotations

import hashlib

from sqlalchemy import text

from ..tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17) — témoins tirés sur le jour Réunion

#: sous ce nombre de lignes, une table « parcelle » vide sur tous les témoins est un VRAI
#: creux (signature DPE : 17 lignes), pas un échantillon clairsemé.
SEUIL_QUASI_VIDE = 100


# VITESSE-2 (Lot 2) — index fonctionnels pour le remplissage « parcelle ». Le test de présence
# `WHERE left(idu, 14) = ANY(:v)` (ligne du SELECT count ci-dessous) ne peut PAS utiliser un btree
# sur `idu` (prédicat fonctionnel) → Parallel Seq Scan mesuré à 84 ms sur pm_proprietaires_millesimes
# (153 k lignes, retirées une à une), rejoué pour CHAQUE fiche parcelle via `_data_sources_fiche`.
# Un index sur l'expression `left(idu, 14)` rend le test indexé (0,13 ms mesuré, Bitmap Index Scan).
# Les deux tables visées sont les grosses tables « parcelle » du catalogue (propriétaires PM
# millésimés + rattachement PM courant) ; les autres réservoirs idu sont petits. Idempotent.
_FICHE_PERF_INDEXES = (
    ("pm_proprietaires_millesimes", "ix_pm_millesimes_idu14"),
    ("parcelle_personne_morale", "ix_parcelle_pm_idu14"),
)


def ensure_perf_indexes(engine) -> int:
    """Pose les index fonctionnels `left(idu,14)` manquants (VITESSE-2 Lot 2). Rend le nombre
    d'index créés. Idempotent (IF NOT EXISTS), non destructif ; une table absente est ignorée."""
    n = 0
    with engine.begin() as c:
        for table, idx in _FICHE_PERF_INDEXES:
            if c.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is None:
                continue
            avant = c.execute(text("SELECT to_regclass(:i)"), {"i": idx}).scalar()
            c.execute(text(f"CREATE INDEX IF NOT EXISTS {idx} ON {table} (left(idu, 14))"))
            if avant is None:
                n += 1
    return n

#: 4 témoins URBAINS fixes (N/O/S/E, bâtis — ceux de SOURCES-AUDIT, vérifiés en base) +
#: 4 témoins RURAUX fixes (cirques et Est sauvage — attrapent les couches nature).
TEMOINS_URBAINS = (
    ("97411000CD0083", "97411", "Saint-Denis"),
    ("97415000DI0183", "97415", "Saint-Paul"),
    ("97416000CO0318", "97416", "Saint-Pierre"),
    ("97409000AB0394", "97409", "Saint-André"),
)
TEMOINS_RURAUX = (
    ("97421000AB0001", "97421", "Salazie"),
    ("97424000AB0001", "97424", "Cilaos"),
    ("97419000AB0001", "97419", "Sainte-Rose"),
    ("97417000AC0003", "97417", "Saint-Philippe"),
)


def temoins_du_jour(db) -> list[tuple[str, str, str]]:
    """Les 12 témoins de la nuit : 4 urbains + 4 ruraux (fixes) + 4 TIRÉS du jour
    (déterministe : md5(idu ‖ date), rejouable dans la nuit, différents chaque jour)."""
    fixes = list(TEMOINS_URBAINS + TEMOINS_RURAUX)
    exclus = {t[0] for t in fixes}
    jour = today_reunion().isoformat()
    rows = db.execute(text(
        "SELECT idu, commune FROM parcels"
        " WHERE md5(idu || :jour) < '0002' AND geom IS NOT NULL LIMIT 200"),
        {"jour": jour}).all()
    tires = []
    for idu, commune in sorted(rows, key=lambda r: hashlib.md5(
            (r[0] + jour).encode(), usedforsecurity=False).hexdigest()):
        if idu not in exclus:
            tires.append((idu, idu[:5], commune or ""))
        if len(tires) == 4:
            break
    return fixes + tires


def schema_public(db) -> dict[str, set[str]]:
    """PERF (SOURCES-3b) : table → colonnes, en UNE requête au catalogue (les tables absentes n'y
    sont pas). Remplace N appels `information_schema`/`to_regclass` par source×table (ce qui faisait
    franchir la seconde à /admin/circuit après le merge). Passé à remplissage_source par mesurer_vitrine."""
    out: dict[str, set[str]] = {}
    for t, col in db.execute(text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public'")):
        out.setdefault(t, set()).add(col)
    return out


def _colonnes(db, table: str, schema: dict[str, set[str]] | None = None) -> set[str]:
    if schema is not None:
        return schema.get(table, set())
    return {r[0] for r in db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": table})}


def _existe(db, table: str, schema: dict[str, set[str]] | None = None) -> bool:
    if schema is not None:
        return table in schema
    return db.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is not None


def remplissage_source(db, slug: str, temoins: list[tuple[str, str, str]],
                       *, sans_carte: bool = False, schema: dict[str, set[str]] | None = None) -> dict:
    """Mesure {type, remplis (0..N), n_temoins, quasi_vide} pour UN réservoir sur les témoins.
    type ∈ parcelle | commune | carte | n.a. — le premier joignable gagne (parcelle d'abord).
    `schema` (table→colonnes) : cache d'introspection partagé (mesurer_vitrine) — sinon requêté à la volée."""
    from .tables import RESERVOIR_TABLES
    rt = RESERVOIR_TABLES.get(slug)
    n = len(temoins)
    if rt is None:
        return {"type": "n.a.", "remplis": None, "n_temoins": n, "quasi_vide": False}
    idus = [t[0] for t in temoins]
    insees = [t[1] for t in temoins]
    communes_up = sorted({t[2].upper() for t in temoins if t[2]})
    best, typ, meilleur_compte = 0, None, None
    for t in rt.tables:
        if t == "spatial_layers" or not _existe(db, t, schema):
            continue
        cols = _colonnes(db, t, schema)
        try:
            if "idu" in cols:
                q = f"SELECT count(DISTINCT left(idu, 14)) FROM {t} WHERE left(idu, 14) = ANY(:v)"
                typ = typ or "parcelle"
            elif "parcelle_idu" in cols:
                q = f"SELECT count(DISTINCT parcelle_idu) FROM {t} WHERE parcelle_idu = ANY(:v)"
                typ = typ or "parcelle"
            elif "code_insee" in cols:
                q = f"SELECT count(DISTINCT code_insee) FROM {t} WHERE code_insee = ANY(:v)"
                typ = typ or "commune"
            elif "insee" in cols:
                q = f"SELECT count(DISTINCT insee) FROM {t} WHERE insee = ANY(:v)"
                typ = typ or "commune"
            elif "commune" in cols:
                q = f"SELECT count(DISTINCT upper(commune)) FROM {t} WHERE upper(commune) = ANY(:v)"
                typ = typ or "commune"
            else:
                continue
            v = idus if "idu" in q else (communes_up if "upper(commune)" in q else insees)
            best = max(best, db.execute(text(q), {"v": v}).scalar() or 0)
            if typ == "parcelle":
                # le compte le MIEUX rempli des tables du réservoir : une source n'est pas
                # « vide » si l'une de ses tables est pleine (le creux exige TOUT quasi nul).
                # PERF (SOURCES-3b) : on ne teste ce compte QUE contre SEUIL_QUASI_VIDE (100) —
                # inutile de compter 431 k lignes (parcel_vegetation) ou 340 k (adresses). Compte
                # BORNÉ à SEUIL (min(count, SEUIL)) : verdict `quasi_vide` identique, plus de scan
                # complet — c'est ce qui faisait franchir la seconde à /admin/circuit (P2 lot 5).
                cnt = db.execute(text(
                    f"SELECT count(*) FROM (SELECT 1 FROM {t} LIMIT {SEUIL_QUASI_VIDE}) _q")).scalar() or 0
                meilleur_compte = cnt if meilleur_compte is None else max(meilleur_compte, cnt)
        except Exception:  # noqa: BLE001 — une table illisible ne casse pas la mesure
            continue
    if typ is None and rt.couches and not sans_carte and _existe(db, "spatial_layers", schema):
        try:
            best = db.execute(text(
                "SELECT count(DISTINCT upper(commune)) FROM spatial_layers"
                " WHERE kind = ANY(:k) AND upper(commune) = ANY(:c)"),
                {"k": list(rt.couches), "c": communes_up}).scalar() or 0
            typ = "carte"
        except Exception:  # noqa: BLE001
            typ = None
    if typ is None:
        return {"type": "n.a.", "remplis": None, "n_temoins": n, "quasi_vide": False}
    quasi_vide = (typ == "parcelle" and best == 0
                  and meilleur_compte is not None and meilleur_compte < SEUIL_QUASI_VIDE)
    return {"type": typ, "remplis": best, "n_temoins": n, "quasi_vide": quasi_vide}


def mesurer_vitrine(db, temoins=None, *, rapide: bool = False) -> dict[str, dict]:
    """Le remplissage de TOUTES les sources en vitrine (slug → mesure). Les types
    « parcelle » et « commune » sont des jointures rapides ; « carte » interroge
    spatial_layers par kind×commune (l'appel le plus lourd, ~1-2 s par source) —
    rapide=True saute cette mesure carte (une couche ne peut pas être « invisible »)."""
    from ..circuit_etats import NOM_VERS_SLUG
    from ..sources_catalog import WHERE_AFFICHEES, masquees_param
    temoins = temoins or temoins_du_jour(db)
    noms = [r[0] for r in db.execute(text(
        f"SELECT name FROM data_sources WHERE {WHERE_AFFICHEES}"),
        {"masquees": masquees_param()})]
    schema = schema_public(db)   # PERF : une seule introspection, partagée par toutes les sources
    out: dict[str, dict] = {}
    for nom in noms:
        slug = NOM_VERS_SLUG.get(nom)
        if slug:
            out[slug] = {"nom": nom,
                         **remplissage_source(db, slug, temoins, sans_carte=rapide, schema=schema)}
    return out
