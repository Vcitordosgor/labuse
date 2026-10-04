"""COHERENCE-FIX-1 (lot A) — LA FRAÎCHEUR DES CACHES : une clé, un geste, un contrôle.

Constat COHERENCE-1 : 70 % des écarts du banc venaient de deux caches périmés EN SILENCE
(fiche commune calculée avant le merge SOURCES-FIX-2, tuiles bâties avant la bascule du
résiduel seq 10). Le bug n'est pas la valeur périmée, c'est le cache qui se périme sans le
dire. Doctrine posée ici :

  1. **Une clé de fraîcheur** (`empreinte_attendue`) : tout cache porte l'empreinte de ce
     dont il dépend — run servi (`runs.current()` + cascade), run résiduel servi
     (`residuel_runs.is_served`), millésimes des sources (`data_sources.source_millesime`),
     version du code (sha de commit). Une dépendance change → l'entrée est invalide,
     régénérée à la prochaine lecture (fiche commune) ou par le geste ci-dessous (tuiles).
  2. **Un seul geste** : `labuse rebuild` (→ `rebuild_tout`) régénère ce qui est périmé —
     et RÉUTILISE le mécanisme ALGO-FIX-1 point 4 (rebuild_mvt_servies = geste unique M48,
     planifier_reconstruction_tuiles à la bascule) au lieu d'en créer un second.
  3. **Un contrôle** : `etat(db)` liste chaque cache avec sa clé attendue / sa clé réelle ;
     servi par `/sante/fraicheur` (admin), affiché page Données, joué par le test de fumée
     du déploiement (`labuse rebuild --dry-run` échoue si un cache est périmé).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from sqlalchemy import text

from . import runs

_RACINE = Path(__file__).resolve().parents[2]

#: sha du code : figé par process (le code d'un process ne change pas). Prod : deploiement.json
#: (écrit par deploy.sh) ; dev : git rev-parse. Jamais d'échec : « inconnu » plutôt qu'un crash.
_CODE_SHA: dict = {"v": None}


def code_sha() -> str:
    """La version du code qui calcule les caches (composante de la clé de fraîcheur)."""
    if _CODE_SHA["v"] is not None:
        return _CODE_SHA["v"]
    sha = None
    dep = _RACINE / "config" / "deploiement.json"
    if dep.exists():
        try:
            sha = (json.loads(dep.read_text()).get("sha") or "")[:12] or None
        except Exception:  # noqa: BLE001
            sha = None
    if sha is None:
        try:
            sha = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=_RACINE,
                                 capture_output=True, text=True, timeout=5).stdout.strip() or None
        except Exception:  # noqa: BLE001
            sha = None
    _CODE_SHA["v"] = sha or "inconnu"
    return _CODE_SHA["v"]


def residuel_seq_servi(db) -> int | None:
    """La vérité du run résiduel servi (ALGO-FIX-1 point 1 : `residuel_runs.is_served`)."""
    from .bascule_flux import _residuel_seq_servi
    return _residuel_seq_servi(db)


def millesimes_hash(db) -> str:
    """Empreinte courte des millésimes de TOUTES les sources (`data_sources.source_millesime`).
    Un millésime qui bouge (nouvelle édition producteur) invalide les caches qui en dérivent —
    sur-invalider une source non lue est bénin (le job régénère), sous-invalider est le bug."""
    try:
        rows = db.execute(text(
            "SELECT name, coalesce(source_millesime, '') FROM data_sources ORDER BY name")).all()
    except Exception:  # noqa: BLE001 — table absente (base de test nue) : composante neutre
        return "sans-sources"
    h = hashlib.md5("|".join(f"{n}={m}" for n, m in rows).encode(), usedforsecurity=False).hexdigest()[:10]
    return h


def empreinte_attendue(db) -> str:
    """LA CLÉ DE FRAÎCHEUR — lisible (elle s'affiche page Données à côté de la clé réelle) :
    run servi + cascade + résiduel servi + millésimes sources + version du code."""
    seq = residuel_seq_servi(db)
    return (f"run={runs.current()}|cascade={runs.cascade()}|residuel=seq{seq}"
            f"|sources={millesimes_hash(db)}|code={code_sha()}")


def empreinte_courte(db) -> str:
    """Version 10 caractères de l'empreinte (clés composites à largeur bornée, ex. ia_cache)."""
    return hashlib.md5(empreinte_attendue(db).encode(), usedforsecurity=False).hexdigest()[:10]


# ═══════════════════════════ l'état — clé attendue / clé réelle ═══════════════════════════

def _etat_commune_cache(db, attendue: str) -> dict:
    n = perimes = 0
    reelle = None
    try:
        if db.execute(text("SELECT to_regclass('commune_contexte_cache')")).scalar():
            a_cle = db.execute(text(
                "SELECT 1 FROM information_schema.columns WHERE table_name='commune_contexte_cache'"
                " AND column_name='cle_fraicheur'")).scalar()
            if not a_cle:
                # cache d'avant le mécanisme de fraîcheur : PAR DÉFINITION sans clé → périmé.
                n = int(db.execute(text("SELECT count(*) FROM commune_contexte_cache")).scalar() or 0)
                perimes, reelle = n, "∅ (cache antérieur à la clé de fraîcheur)"
            else:
                row = db.execute(text(
                    "SELECT count(*), count(*) FILTER (WHERE cle_fraicheur IS DISTINCT FROM :a), "
                    "       min(cle_fraicheur) FILTER (WHERE cle_fraicheur IS DISTINCT FROM :a)"
                    " FROM commune_contexte_cache"), {"a": attendue}).first()
                n, perimes, reelle = int(row[0]), int(row[1]), row[2]
    except Exception as e:  # noqa: BLE001
        db.rollback()      # ne jamais laisser la transaction avortée aux états suivants
        return {"cache": "commune_contexte_cache", "erreur": str(e)[:120], "perime": True}
    total_communes = db.execute(text(
        "SELECT count(DISTINCT commune) FROM parcels WHERE commune IS NOT NULL")).scalar() or 0
    manquantes = max(0, int(total_communes) - n)
    return {"cache": "commune_contexte_cache",
            "porte_sur": f"{n} communes (attendues : {total_communes})",
            "cle_attendue": attendue,
            "cle_reelle": attendue if (n and not perimes) else reelle,
            "perime": bool(perimes or manquantes),
            "detail": (f"{perimes} périmée(s), {manquantes} manquante(s)"
                       if (perimes or manquantes) else "à jour"),
            "remede": "labuse rebuild (ou lecture : la fiche se régénère d'elle-même)"}


def _etat_tuiles(db) -> dict:
    from .api.tiles import tuiles_etat
    t = tuiles_etat(db)
    return {"cache": "mvt_parcels (tuiles carte)",
            "porte_sur": f"run carte « {t.get('run_carte') or '∅'} », bâties le {t.get('carte_le') or '∅'}",
            "cle_attendue": t.get("cle_attendue"),
            "cle_reelle": t.get("cle_reelle"),
            "perime": bool(t.get("perime")),
            "detail": t.get("motif_detail") or ("à jour" if not t.get("perime") else t.get("motif")),
            "remede": "labuse rebuild (geste unique build-mvt + tiles-warm)"}


def _etat_tile_cache(db) -> dict:
    perime, detail, reelle, attendue = False, "à jour", None, None
    try:
        if not db.execute(text("SELECT to_regclass('mvt_tile_cache')")).scalar():
            return {"cache": "mvt_tile_cache (z9-11 pré-générées)", "perime": True,
                    "detail": "absent (jamais chauffé)", "remede": "labuse rebuild"}
        attendue = db.execute(text(
            "SELECT to_char(updated_at, 'YYYYMMDDHH24MISSMS') FROM mvt_meta "
            "WHERE key='run_label'")).scalar()
        row = db.execute(text(
            "SELECT count(*) FILTER (WHERE version = :v), count(DISTINCT version), max(version)"
            " FROM mvt_tile_cache"), {"v": attendue}).first()
        n_ok, reelle = int(row[0]), row[2]
        if not n_ok:
            perime, detail = True, "aucune tuile à la version courante des MVT"
        else:
            detail, reelle = f"{n_ok} tuiles à la version courante", attendue
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        perime, detail = True, str(e)[:120]
    return {"cache": "mvt_tile_cache (z9-11 pré-générées)",
            "cle_attendue": f"version-mvt={attendue}", "cle_reelle": f"version-mvt={reelle}",
            "perime": perime, "detail": detail, "remede": "labuse rebuild"}


def _etat_spatial_sub(db) -> dict:
    perime, detail = False, "à jour"
    try:
        if not db.execute(text("SELECT to_regclass('spatial_layers_sub')")).scalar():
            perime, detail = True, "absent"
        else:
            stale = db.execute(text(
                "SELECT EXISTS (SELECT 1 FROM spatial_layers sl WHERE sl.kind <> 'batiment' "
                "  AND sl.id > COALESCE((SELECT max(lid) FROM spatial_layers_sub), 0)) "
                " OR EXISTS (SELECT 1 FROM spatial_layers_sub s WHERE NOT EXISTS "
                "  (SELECT 1 FROM spatial_layers sl WHERE sl.id = s.lid))")).scalar()
            if stale:
                perime, detail = True, "spatial_layers a bougé depuis la subdivision"
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        perime, detail = True, str(e)[:120]
    return {"cache": "spatial_layers_sub (couches subdivisées)",
            "cle_attendue": "max(id) et effectif de spatial_layers",
            "cle_reelle": detail, "perime": perime, "detail": detail,
            "remede": "labuse rebuild (ensure_spatial_layers_sub, déjà auto-réparant à la cascade)"}


def _etat_ia_cache(db, courte: str) -> dict:
    n_frais = n_total = 0
    try:
        if db.execute(text("SELECT to_regclass('ia_cache')")).scalar():
            run = runs.current()
            row = db.execute(text(
                "SELECT count(*) FILTER (WHERE run_label = :k), count(*) FROM ia_cache"),
                {"k": f"{run}+{courte}"}).first()
            n_frais, n_total = int(row[0]), int(row[1])
    except Exception:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
    # ce cache est AUTO-CLÉ (la clé de fraîcheur est DANS la clé de ligne) : il ne peut pas être
    # périmé, seulement froid (les vieilles entrées ne sont plus jamais servies).
    return {"cache": "ia_cache (réponses Copilote/fiche_ask)",
            "cle_attendue": f"{runs.current()}+{courte}",
            "cle_reelle": "clé portée par chaque ligne (auto)",
            "perime": False,
            "detail": f"{n_frais} réponses fraîches / {n_total} au total (vieilles = jamais servies)",
            "remede": "aucun (auto-clé)"}


def _etat_manifeste(db) -> dict:
    """PRE-DEPLOY-1 (lot C) — LE MANIFESTE NE PEUT PLUS MENTIR. `config/served_manifest.json` (le
    fichier COMMITÉ) doit refléter CE QUI EST RÉELLEMENT SERVI en base. On confronte :
      · résiduel : `residuel_run_seq` (miroir du manifeste) vs `residuel_runs.is_served` (LA vérité,
        ALGO-FIX-1 point 1) — c'est le bug fondateur « manifeste run 8 ↔ is_served run 10 » (7ae2c2b7) ;
      · scoring : `scoring_run` (manifeste) vs sa vue dérivée `config/served_run.txt` (write partiel).
    Un écart = PÉRIMÉ (rouge page Données, échec `rebuild --dry-run` = fumée du déploiement, échec V6b).

    GARDE base de test : on ne crie au loup QUE si le run résiduel du manifeste EXISTE dans cette base
    (sur un poste de test, le manifeste pointe des runs de prod absents → on n'est pas sur la base
    servie, rien à comparer). Le bug réel (8 ↔ 10) a les DEUX runs présents → attrapé."""
    from . import manifeste as _manifeste
    from .bascule_flux import _residuel_seq_servi
    ecarts: list[str] = []
    m = _manifeste.lire()
    if m is None:
        return {"cache": "served_manifest.json (pointeur servi)", "perime": True,
                "porte_sur": "aucun manifeste", "cle_attendue": "présent", "cle_reelle": "absent",
                "detail": "manifeste absent (jamais posé) — le run servi n'est pas traçable",
                "remede": "labuse golden promote <run> (ou residuel-serve) pose le manifeste"}
    seq_manifeste = m.get("residuel_run_seq")
    seq_servi = _residuel_seq_servi(db)
    # le run du manifeste existe-t-il dans CETTE base ? (sinon : base de test/dev, pas la servie)
    manifeste_ici = False
    if seq_manifeste is not None:
        try:
            manifeste_ici = bool(db.execute(text(
                "SELECT 1 FROM residuel_runs WHERE run_seq = :s"), {"s": seq_manifeste}).scalar())
        except Exception:  # noqa: BLE001 — table absente (base nue) : rien à comparer
            manifeste_ici = False
    if seq_servi is not None and manifeste_ici and seq_manifeste != seq_servi:
        ecarts.append(f"résiduel : manifeste seq {seq_manifeste} ≠ is_served seq {seq_servi} (base)")
    # scoring : le manifeste et sa vue dérivée served_run.txt doivent coïncider (write atomique).
    try:
        from . import runs as _runs
        fichier_scoring = _runs._lire_fichier()
        if m.get("scoring_run") and m["scoring_run"] != fichier_scoring:
            ecarts.append(f"scoring : manifeste « {m['scoring_run']} » ≠ served_run.txt « {fichier_scoring} »")
    except Exception:  # noqa: BLE001 — served_run.txt illisible : non bloquant ici
        pass
    perime = bool(ecarts)
    return {"cache": "served_manifest.json (pointeur servi)",
            "porte_sur": f"scoring={m.get('scoring_run')}, résiduel seq{seq_manifeste}",
            "cle_attendue": f"is_served seq{seq_servi} · served_run.txt",
            "cle_reelle": " ; ".join(ecarts) if perime else "aligné sur le servi en base",
            "perime": perime,
            "detail": (" ; ".join(ecarts)) if perime else "manifeste = servi en base (aligné)",
            "remede": "réécrire config/served_manifest.json (residuel-serve/golden promote le font) "
                      "puis committer le fichier"}


def _etat_intersections(db) -> dict:
    """PRE-DEPLOY-1 (lot D) — `parcel_couche_intersection` (servitudes matérialisées, VITESSE-FIX-1) :
    complète / partielle / vide / absente + nombre de lignes, couches, parcelles, date de build.

    NON bloquant (`perime` False) : un manque n'est PAS une erreur — les lecteurs (fiche, Gabarit)
    REPASSENT au calcul au vol, à résultat IDENTIQUE, juste plus lent (`couche_intersection.fraiche`).
    Mais on le DIT (page Données, fumée du déploiement) pour qu'une table incomplète ne passe jamais
    inaperçue. Reconstruite par `labuse build-intersections` (geste de Vic) ou `labuse rebuild`."""
    from . import couche_intersection as _ci
    statut, n, n_couches, n_parcelles, date = "absente", 0, 0, 0, None
    try:
        if db.execute(text(f"SELECT to_regclass('{_ci.TABLE}')")).scalar():
            row = db.execute(text(
                f"SELECT count(*), count(DISTINCT layer_id), count(DISTINCT parcel_id) "
                f"FROM {_ci.TABLE}")).first()
            n, n_couches, n_parcelles = int(row[0]), int(row[1]), int(row[2])
            if db.execute(text(f"SELECT to_regclass('{_ci._META}')")).scalar():
                date = db.execute(text(
                    f"SELECT to_char(max(updated_at),'YYYY-MM-DD HH24:MI') FROM {_ci._META}")).scalar()
            if n and _ci.fraiche(db):
                statut = "complète"
            elif n:
                statut = "partielle"      # présente mais sources changées (périmée vs fraîcheur)
            else:
                statut = "vide"
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {"cache": "parcel_couche_intersection (servitudes)", "perime": False,
                "statut": "erreur", "detail": str(e)[:120],
                "remede": "labuse build-intersections"}
    detail = {"complète": f"{n} intersections · {n_couches} couches · {n_parcelles} parcelles · le {date or '?'}",
              "partielle": f"{n} lignes mais sources SERVITUDES changées (calcul au vol) · le {date or '?'}",
              "vide": "table présente mais VIDE (calcul au vol)",
              "absente": "table absente — jamais construite (calcul au vol, correct mais lent)"}[statut]
    return {"cache": "parcel_couche_intersection (servitudes)",
            "porte_sur": f"{n} intersections · {n_couches} couches · {n_parcelles} parcelles",
            "cle_attendue": "servitudes alignées (fraiche)", "cle_reelle": statut,
            "perime": False, "statut": statut, "date": date, "n": n,
            "n_couches": n_couches, "n_parcelles": n_parcelles, "detail": detail,
            "remede": "labuse build-intersections (geste de Vic) ou labuse rebuild — calcul au vol si absente"}


def _etat_defisc_bareme() -> dict:
    """CALCULS-FIX-1 (Lot C) — fraîcheur du barème de défiscalisation (config millésimée). Périmé
    dès que l'année du barème servi est < année courante (geste annuel de loi de finances non fait)."""
    import datetime

    from .faisabilite import defisc
    an = datetime.date.today().year
    ba = defisc.annee_active()
    perime = ba < an
    return {"cache": "barème défiscalisation (config millésimée)",
            "porte_sur": f"plafonds de loyer + coefficient de surface — barème {ba}",
            "cle_attendue": f"barème {an}", "cle_reelle": f"barème {ba}",
            "perime": perime, "statut": "perime" if perime else "frais", "date": str(ba),
            "detail": (defisc.signalement_fraicheur()
                       or f"Barème {ba} à jour pour {an}."),
            "remede": (f"dupliquer config/calibrage/defisc_{ba}.yaml en defisc_{an}.yaml et le "
                       f"mettre à jour depuis le barème officiel de loi de finances {an}")}


def etat(db) -> dict:
    """L'ÉTAT DE FRAÎCHEUR de chaque cache : clé attendue / clé réelle / périmé. Servi par
    `/sante/fraicheur`, affiché page Données, joué par `labuse rebuild --dry-run` (fumée)."""
    attendue = empreinte_attendue(db)
    caches = [_etat_manifeste(db), _etat_commune_cache(db, attendue), _etat_tuiles(db),
              _etat_tile_cache(db), _etat_spatial_sub(db), _etat_ia_cache(db, empreinte_courte(db)),
              _etat_intersections(db), _etat_defisc_bareme()]
    return {"empreinte_attendue": attendue,
            "perimes": [c["cache"] for c in caches if c.get("perime")],
            "caches": caches}


# ═══════════════════════════ le geste — labuse rebuild ═══════════════════════════

def rebuild_tout(engine, log=lambda *_: None, force: bool = False) -> dict:
    """LE GESTE UNIQUE de régénération (COHERENCE-FIX-1 lot A) : régénère chaque cache PÉRIMÉ
    (tous si `force`). Réutilise le mécanisme existant — `ensure_spatial_layers_sub` (auto-réparant),
    `rebuild_mvt_servies` (geste unique M48 d'ALGO-FIX-1, qui enchaîne flags + renouvellement +
    score_e + tiles-warm), `rafraichir_contexte_cache` (point d'écriture unique FICHE-COMMUNE-2).
    Appelé par : la bascule scoring (stratégie ALGO-FIX-1 planifier), `labuse residuel-serve`,
    `deploy.sh`, et la commande `labuse rebuild` — jamais à la main, jamais oublié."""
    from .db import session_factory
    from .models import ensure_spatial_layers_sub
    fait: dict = {}

    # 1) couches subdivisées (rapide si à jour — la garde interne décide)
    n_sub = ensure_spatial_layers_sub(engine, force=force)
    fait["spatial_layers_sub"] = n_sub
    log(f"✓ spatial_layers_sub : {n_sub} pièces (garde interne : rebuild si couches changées).")

    # 2) tuiles + tables run-scopées (le geste unique M48) — seulement si périmées (ou force).
    # MÊME garde anti-deadlock que `labuse build-mvt` (DONNEES-2 B1) : les DROP/RENAME prennent un
    # verrou exclusif qui peut deadlocker avec les lectures de l'API vivante → lock_timeout borné
    # + 3 tentatives (transaction annulée entre deux : rien de partiel).
    import time as _t
    from sqlalchemy import text as _text
    from sqlalchemy.exc import OperationalError
    from .api.tiles import rebuild_mvt_servies, tuiles_etat
    db = session_factory()()
    try:
        perime_tuiles = force or tuiles_etat(db).get("perime")
    finally:
        db.close()
    if perime_tuiles:
        for tentative in range(3):
            db = session_factory()()
            try:
                db.execute(_text("SET lock_timeout = '30s'"))
                res = rebuild_mvt_servies(db, log=log)
                db.commit()
                fait["mvt"] = {"n": res.get("n"), "tuiles_prechauffees": res.get("tuiles_prechauffees")}
                break
            except OperationalError as exc:
                db.rollback()
                if tentative == 2:
                    raise
                log(f"⚠ verrou/deadlock (tentative {tentative + 1}/3) : {type(exc).__name__} — "
                    f"nouvelle tentative dans 6 s…")
                _t.sleep(6)
            finally:
                db.close()
    else:
        fait["mvt"] = "à jour"
        log("· mvt_parcels/tuiles : à jour (rien à reconstruire).")

    # 3) fiche commune : chaque commune dont la clé ne colle plus (ou toutes si force)
    db = session_factory()()
    try:
        from .api.app import _ensure_contexte_cache, rafraichir_contexte_cache
        _ensure_contexte_cache(db)      # pose table + colonne cle_fraicheur (base d'avant le mandat)
        db.commit()
        attendue = empreinte_attendue(db)
        communes = [r[0] for r in db.execute(text(
            "SELECT DISTINCT commune FROM parcels WHERE commune IS NOT NULL ORDER BY commune")).all()]
        a_faire = communes
        if not force and db.execute(text("SELECT to_regclass('commune_contexte_cache')")).scalar():
            fraiches = {r[0] for r in db.execute(text(
                "SELECT commune FROM commune_contexte_cache WHERE cle_fraicheur = :a"),
                {"a": attendue}).all()}
            a_faire = [c for c in communes if c not in fraiches]
        ok, echecs = 0, []
        for c in a_faire:
            try:
                rafraichir_contexte_cache(db, c)
                db.commit()
                ok += 1
                log(f"✓ fiche commune : {c}")
            except Exception as e:  # noqa: BLE001 — une commune ratée ne tue pas le geste
                db.rollback()
                echecs.append(f"{c}: {e}"[:120])
                log(f"✗ fiche commune : {c} — {e}")
        fait["fiche_commune"] = {"regenerees": ok, "deja_fraiches": len(communes) - len(a_faire),
                                 "echecs": echecs or None}
    finally:
        db.close()
    return fait
