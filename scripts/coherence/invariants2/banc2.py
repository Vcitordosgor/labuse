"""CHASSE-INVARIANTS-2 — le banc de nuit de la vague 2 (une seule commande, rejouable).

Rejoue, en LECTURE SEULE :
  · la BASE de la vague 1 (les 97 invariants de `chasse_invariants.py`, repris tels quels —
    jamais réécrits) ;
  · les 6 familles GÉNÉRÉES de la vague 2 (F1 schéma · F2 registre · F3 métamorphique ·
    F4 PLU · F5 API · F6 zones muettes), chacune via son `generer(cx) -> (specs, ecartees)`.

Usage :
    PYTHONPATH=src .venv/bin/python -m scripts.coherence.invariants2.banc2 \
        [--api URL] [--famille F1,F3] [--nuit | --tout] [--base/--no-base]

  --nuit   (défaut) : sous-ensemble RAPIDE compatible garde de nuit (<30 min) — saute les
           familles à boucle HTTP cadencée et le gros calcul-à-blanc (F5 API, F3 métamorphique,
           la faisabilité 5000 de F6). Tout le reste (SQL île entière) tourne.
  --tout   : TOUTES les règles (hebdomadaire). Peut dépasser 30 min (F5 cadencé 60/min).

Sortie : un bilan par famille (OK/ECART/SKIP), un grand total, et la liste des ECART.
exit 1 si au moins un ECART (le banc MORD), 0 sinon.
"""
from __future__ import annotations

import argparse
import importlib
import pathlib
import sys
import time

_RACINE = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_RACINE / "scripts"))

from coherence.chasse_invariants import Cx, _plan as _plan_v1, _served_run  # noqa: E402
from coherence.lib import _dsn_defaut  # noqa: E402
from coherence.invariants2.noyau import run_specs, bilan  # noqa: E402

# famille → (module, cadencée/lourde ⇒ hors --nuit)
FAMILLES = [
    ("F1", "coherence.invariants2.f1_schema", False),
    ("F2", "coherence.invariants2.f2_registre", True),   # boucle fiches + listes île entière
    ("F2b", "coherence.invariants2.f2b_registre_integrite", False),  # intégrité registre (par chiffre), SQL rapide
    ("F3", "coherence.invariants2.f3_metamorphique", False),  # ~5400 cas calcul-à-blanc en-process (~4 s)
    ("F4", "coherence.invariants2.f4_plu", False),
    ("F5", "coherence.invariants2.f5_api", True),        # ~250 requêtes cadencées 60/min (~5 min)
    ("F6", "coherence.invariants2.f6_zones_muettes", False),  # jointure spatiale + faisabilité 5000 (~6 s)
]


def _run_base_v1(cx, api):
    """Les 97 de la vague 1, repris tels quels (base). Rend (ok, ecart, skip, [ecarts])."""
    run, rseq, cascade = _served_run()
    n_ok = n_ec = n_sk = 0
    ecarts = []
    for dom, gardes in _plan_v1(run, rseq, cascade, api):
        for libelle, fn in gardes:
            statut, msg = fn(cx)
            if statut == "OK":
                n_ok += 1
            elif statut == "ECART":
                n_ec += 1
                ecarts.append(f"BASE/{dom} :: {libelle} — {msg}")
            else:
                n_sk += 1
    return n_ok, n_ec, n_sk, ecarts


def main():
    ap = argparse.ArgumentParser(description="CHASSE-INVARIANTS-2 — banc de nuit (lecture seule)")
    ap.add_argument("--api", default="http://127.0.0.1:8793")
    ap.add_argument("--famille", default=None, help="sous-liste, ex. 'F1,F4'")
    ap.add_argument("--tout", action="store_true", help="toutes les règles (hebdo)")
    ap.add_argument("--nuit", action="store_true", help="sous-ensemble rapide (défaut)")
    ap.add_argument("--no-base", dest="base", action="store_false", help="ne pas rejouer les 97 de la vague 1")
    ap.set_defaults(base=True)
    args = ap.parse_args()
    tout = args.tout and not args.nuit
    vouloir = set(f.strip().upper() for f in args.famille.split(",")) if args.famille else None

    run, rseq, cascade = _served_run()
    mode = "TOUT (hebdo)" if tout else "NUIT (rapide)"
    print(f"CHASSE-INVARIANTS-2 — banc de nuit · run servi {run}/seq{rseq}/{cascade} · mode {mode}")
    print(f"DSN={_dsn_defaut()}  API={args.api}\n")

    cx = Cx(_dsn_defaut())
    t0 = time.time()
    tot_ok = tot_ec = tot_sk = 0
    tous_ecarts = []

    try:
        if args.base and (vouloir is None):
            tb = time.time()
            ok, ec, sk, ecs = _run_base_v1(cx, args.api)
            tot_ok += ok; tot_ec += ec; tot_sk += sk; tous_ecarts += ecs
            print(f"── BASE vague-1 (97 repris) : {ok} OK · {ec} ECART · {sk} SKIP  [{time.time()-tb:.0f}s]")

        for code, modname, lourde in FAMILLES:
            if vouloir is not None and code.upper() not in vouloir:
                continue
            if not tout and lourde:
                print(f"── {code} : sauté en mode NUIT (lourd/cadencé — rejoué en --tout)")
                continue
            try:
                mod = importlib.import_module(modname)
            except Exception as e:  # noqa: BLE001
                print(f"── {code} : INDISPONIBLE ({type(e).__name__}: {e})")
                continue
            tf = time.time()
            _res = mod.generer(cx)            # F1 rend (specs, ecartees, n_gen) ; les autres (specs, ecartees)
            specs, ecartees = _res[0], _res[1]
            res = run_specs(cx, specs, args.api)
            b = bilan(res)
            tot_ok += b["OK"]; tot_ec += b["ECART"]; tot_sk += b["SKIP"]
            for r in res:
                if r.statut == "ECART":
                    tous_ecarts.append(f"{code} :: {r.spec.id} [{r.spec.gravite}] — {r.message}")
            print(f"── {code} : {len(specs)} retenues ({len(ecartees)} écartées) → "
                  f"{b['OK']} OK · {b['ECART']} ECART · {b['SKIP']} SKIP  [{time.time()-tf:.0f}s]")
    finally:
        cx.close()

    print(f"\nBILAN vague 2 : {tot_ok} OK · {tot_ec} ECART · {tot_sk} SKIP  "
          f"(règles exécutées : {tot_ok + tot_ec + tot_sk})  [{time.time()-t0:.0f}s]")
    if tous_ecarts:
        print("ECARTS :")
        for e in tous_ecarts:
            print("  - " + e)
    sys.exit(1 if tot_ec else 0)


if __name__ == "__main__":
    main()
