"""COHERENCE-1 — LE BANC : rejouable en une commande, sans navigateur.

    python -m scripts.coherence.banc --echantillon   # 120 parcelles + 24 communes (< 15 min)
    python -m scripts.coherence.banc --ile           # ajoute les recalculs lourds 24 communes

Pour chaque notion des tables de vérification (checks_parcelle, checks_commune), le banc
interroge TOUS les lecteurs (fiche JSON, SQL, tuile MVT décodée, outils API) et compare
chaque couple à la tolérance près ; il vérifie aussi le DÉTERMINISME (même lecteur appelé
deux fois = même valeur) et les CROISEMENTS parcelle ↔ commune. Sortie : ECARTS.csv +
résumé console. Lecture seule.

(`labuse coherence` : l'alias CLI appartient à COHERENCE-FIX-1 — ce mandat-ci n'a pas le
droit d'écrire dans src/. La commande module ci-dessus est l'équivalent exact.)
"""
from __future__ import annotations

import csv
import json
import sys
import time

from .lib import ABSENT, Contexte, Ecarts, Erreur, RACINE, SORTIE, chemin
from .checks_parcelle import CHECKS as CHECKS_P
from .checks_commune import CHECKS as CHECKS_C, CROISEMENTS_PARCELLE, GEO_TEMOINS

ECHANTILLON = SORTIE / "ECHANTILLON.csv"


def charger_echantillon() -> list[dict]:
    with open(ECHANTILLON, newline="") as f:
        return list(csv.DictReader(f))


def _valeurs(ctx, objet, lecteurs):
    out = []
    for etiquette, getter in lecteurs:
        try:
            out.append((etiquette, getter(ctx, objet)))
        except Exception as e:  # noqa: BLE001 — un lecteur qui casse est un résultat
            out.append((etiquette, Erreur(e)))
    return out


def _comparer_tous(ec: Ecarts, notion, objet, valeurs, tol, cause):
    """Compare le PREMIER lecteur porteur à chacun des suivants (étoile, pas tous les
    couples : n-1 comparaisons lisibles, le pivot est l'écran client = premier déclaré)."""
    porteurs = [(l, v) for l, v in valeurs if v is not ABSENT]
    if len(porteurs) < 2:
        return
    (la, va), reste = porteurs[0], porteurs[1:]
    for lb, vb in reste:
        ec.noter(notion, objet, la, va, lb, vb, tol, cause)


def passe_parcelles(ctx, ec, parcelles):
    t0 = time.time()
    for i, row in enumerate(parcelles):
        idu = row["idu"]
        for notion, tol, lecteurs, cause in CHECKS_P:
            _comparer_tous(ec, notion, idu, _valeurs(ctx, idu, lecteurs), tol, cause)
        if (i + 1) % 20 == 0:
            print(f"  parcelles {i+1}/{len(parcelles)} ({time.time()-t0:.0f}s)")


def passe_communes(ctx, ec, communes, ile=False):
    for com in communes:
        for notion, tol, lecteurs, cause, geo_lourd in CHECKS_C:
            if geo_lourd and not ile and com not in GEO_TEMOINS:
                continue
            _comparer_tous(ec, notion, com, _valeurs(ctx, com, lecteurs), tol, cause)
        # fraîcheur du cache : un cache de plus de 48 h est un lecteur qui ment sur « chaque nuit »
        calc = chemin(ctx.commune_ctx(com), "cache_calcule_le")
        if isinstance(calc, str):
            age = ctx.sql1("SELECT extract(epoch FROM now() - %(t)s::timestamptz)/3600.0", t=calc)
            if age is not ABSENT and age is not None and age > 48:
                ec.lignes.append({"notion": "cache_fiche_commune_fraicheur", "objet": com,
                                  "lecteur_a": "ctx:cache_calcule_le", "valeur_a": calc,
                                  "lecteur_b": "attendu", "valeur_b": "rafraîchi chaque nuit",
                                  "ecart": f"{age:.0f} h", "cause": "cache_perime",
                                  "gravite": "INCOHERENT"})


def passe_croisements(ctx, ec, parcelles):
    """Une parcelle par commune : le taux communal lu sur la fiche parcelle = celui de la
    fiche commune."""
    par_commune: dict[str, str] = {}
    for row in parcelles:
        par_commune.setdefault(row["commune"], row["idu"])
    for com, idu in sorted(par_commune.items()):
        for notion, tol, la, chemin_fiche, lb, chemin_ctx in CROISEMENTS_PARCELLE:
            va = chemin(ctx.fiche(idu), chemin_fiche)
            vb = chemin(ctx.commune_ctx(com), chemin_ctx)
            if va is ABSENT or vb is ABSENT:
                continue
            ec.noter(notion, f"{idu}↔{com}", f"{la} ({idu})", va, lb, vb, tol,
                     "source_differente")


def passe_determinisme(ctx, ec, parcelles, communes):
    """Chaque lecteur appelé deux fois rend la même valeur (cache vs base, tuile stable)."""
    import urllib.request
    from .lib import API
    for idu in [r["idu"] for r in parcelles[:5]]:
        try:
            with urllib.request.urlopen(f"{API}/parcels/{idu}", timeout=120) as r:
                deux = json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            deux = Erreur(e)
        un = ctx.fiche(idu)
        if isinstance(un, dict) and isinstance(deux, dict):
            diffs = [k for k in set(un) | set(deux)
                     if json.dumps(un.get(k), sort_keys=True, default=str)
                     != json.dumps(deux.get(k), sort_keys=True, default=str)]
            for k in diffs:
                ec.lignes.append({"notion": f"determinisme_fiche.{k}", "objet": idu,
                                  "lecteur_a": "fiche appel 1", "valeur_a": str(un.get(k))[:120],
                                  "lecteur_b": "fiche appel 2", "valeur_b": str(deux.get(k))[:120],
                                  "ecart": "2 appels ≠", "cause": "non_deterministe",
                                  "gravite": "INCOHERENT"})
    for com in communes[:3]:
        import urllib.parse
        try:
            with urllib.request.urlopen(
                    f"{API}/communes/{urllib.parse.quote(com)}/contexte", timeout=120) as r:
                deux = json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            deux = Erreur(e)
        un = ctx.commune_ctx(com)
        if isinstance(un, dict) and isinstance(deux, dict):
            if json.dumps(un, sort_keys=True, default=str) != json.dumps(deux, sort_keys=True, default=str):
                ec.lignes.append({"notion": "determinisme_fiche_commune", "objet": com,
                                  "lecteur_a": "contexte appel 1", "valeur_a": "…",
                                  "lecteur_b": "contexte appel 2", "valeur_b": "…",
                                  "ecart": "2 appels ≠", "cause": "non_deterministe",
                                  "gravite": "INCOHERENT"})


def main() -> None:
    ile = "--ile" in sys.argv
    parcelles = charger_echantillon()
    communes = sorted({r["commune"] for r in parcelles if r["commune"] and r["commune"] != "?"})
    ctx, ec = Contexte(), Ecarts()
    t0 = time.time()
    print(f"banc de cohérence — {len(parcelles)} parcelles, {len(communes)} communes, "
          f"mode {'île' if ile else 'échantillon'}")
    passe_parcelles(ctx, ec, parcelles)
    print(f"parcelles faites ({time.time()-t0:.0f}s) ; communes…")
    passe_communes(ctx, ec, communes, ile=ile)
    passe_croisements(ctx, ec, parcelles)
    passe_determinisme(ctx, ec, parcelles, communes)
    chemin_csv = ec.ecrire()
    par_gravite: dict[str, int] = {}
    for l in ec.lignes:
        par_gravite[l["gravite"]] = par_gravite.get(l["gravite"], 0) + 1
    print(f"\n{ec.n_comparaisons} comparaisons · {len(ec.lignes)} écarts : {par_gravite}")
    print(f"→ {chemin_csv} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
