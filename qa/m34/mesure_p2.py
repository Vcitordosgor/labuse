"""M34 Phase 2 — RE-MESURE : 0 divergence tier servi vs verdict de fiche, DANS LES DEUX SENS.

Bout-en-bout et LECTURE SEULE : on appelle le vrai constructeur de fiche legacy
(`_build_fiche`) sur un échantillon stratifié (tous tiers + ancres + registre + P0)
et on vérifie que le verdict AFFICHÉ est la traduction exacte du tier servi :
  - aucun déclassement silencieux (tier haut → verdict déclassé) ;
  - aucune divergence montante (a_creuser → verdict supérieur) ;
  - plus AUCUNE occurrence du vocabulaire cascade legacy en position de verdict ;
  - les seuls écarts admis = verdicts de déclassement motivés (declasse_*/registre).

Usage : PYTHONPATH=src python qa/m34/mesure_p2.py
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from labuse.db import session_factory
from labuse.scoring.score_v_constants import Q_A_RUN_LABEL
from labuse.verdict_servi import TIERS_SERVABLES

LEGACY_VOCAB = {"opportunite", "faux_positif_probable"}  # ne doivent plus JAMAIS être un verdict
ANCRES = ["97422000CY0197", "97418000AT2542", "97418000AT2317"]
P0_SAMPLE = [  # les 20 IDU du constat P0 (brûlantes divergentes d'alors)
    "97411000KA0296", "97410000CD0905", "97418000AT2379", "97408000AP1603",
    "97416000ET2164", "97416000ET2243", "97416000ET2167", "97416000ET2166",
    "97412000CP0462", "97422000BX1123", "97411000CE1132", "97411000CE1133",
    "97415000AX1100", "97413000AV2297", "97412000CE2776", "97411000EL0665",
    "97416000ET2242", "97415000AY1587", "97413000AV2267",
]
STRATES = [
    ("brulante", None),          # exhaustif (119)
    ("chaude", 250),
    ("a_creuser", 250),          # couvre les ex-« montantes »
    ("reserve_fonciere", 200),
    ("declasse_bati_revele", 50),
    ("declasse_bati_sature", 50),
    ("declasse_zone_fermee", 25),
    ("declasse_au_statut_inconnu", 25),
    ("ecartee", 100),
]


def main() -> int:
    db = session_factory()()
    from labuse.api.app import _build_fiche

    idus: list[tuple[str, str]] = []
    for tier, n in STRATES:
        q = ("SELECT parcelle_id FROM parcel_p_score_v2 WHERE run_id = :r AND tier = :t "
             "ORDER BY md5(parcelle_id)" + (f" LIMIT {n}" if n else ""))
        idus += [(i, tier) for (i,) in db.execute(text(q), {"r": Q_A_RUN_LABEL, "t": tier})]
    ex_reg = [(i, t) for (i, t) in db.execute(text(
        "SELECT e.idu, s.tier FROM served_run_exceptions e "
        "JOIN parcel_p_score_v2 s ON s.parcelle_id = e.idu AND s.run_id = e.run_id "
        "WHERE e.run_id = :r"), {"r": Q_A_RUN_LABEL})]
    tiers_connus = {i: t for i, t in idus + ex_reg}
    for a in ANCRES + P0_SAMPLE:
        if a not in tiers_connus:
            t = db.execute(text("SELECT tier FROM parcel_p_score_v2 WHERE run_id=:r AND parcelle_id=:i"),
                           {"r": Q_A_RUN_LABEL, "i": a}).scalar()
            tiers_connus[a] = t

    total = len(tiers_connus)
    silencieux, montantes, vocab_legacy, erreurs = [], [], [], []
    servables = set(TIERS_SERVABLES)
    hauts = {"brulante", "chaude", "reserve_fonciere"}

    for n, (idu, tier) in enumerate(sorted(tiers_connus.items()), 1):
        try:
            fiche = _build_fiche(db, idu, with_assistant=False)
        except Exception as e:  # noqa: BLE001
            erreurs.append((idu, tier, f"{type(e).__name__}: {e}"))
            continue
        v = fiche["verdict"]
        st = v["status"]
        rs = (fiche.get("resume") or {}).get("statut")
        if st != tier or rs != tier:
            erreurs.append((idu, tier, f"verdict={st} resume={rs} ≠ tier"))
        if st in LEGACY_VOCAB or rs in LEGACY_VOCAB:
            vocab_legacy.append((idu, tier, st))
        # sens 1 : tier haut servi → verdict qui déclasse (a_creuser/declasse/ecartee)
        if tier in hauts and (st not in servables or st == "a_creuser"):
            silencieux.append((idu, tier, st))
        # sens 2 : a_creuser servi → verdict supérieur à son tier
        if tier == "a_creuser" and st in hauts:
            montantes.append((idu, tier, st))
        if n % 100 == 0:
            print(f"  … {n}/{total}", flush=True)

    print(f"\nÉchantillon : {total} parcelles (brûlantes exhaustives + strates + ancres + P0 + registre)")
    print(f"Déclassements silencieux (sens 1) : {len(silencieux)}")
    print(f"Divergences montantes   (sens 2) : {len(montantes)}")
    print(f"Vocabulaire legacy en verdict    : {len(vocab_legacy)}")
    print(f"Incohérences verdict≠tier / err  : {len(erreurs)}")
    for lst, nom in ((silencieux, "SILENCIEUX"), (montantes, "MONTANTES"),
                     (vocab_legacy, "LEGACY"), (erreurs, "ERREURS")):
        for row in lst[:10]:
            print(f"  [{nom}] {row}")
    # Ancres nommées — affichage de contrôle
    for a in ANCRES:
        f = _build_fiche(db, a, with_assistant=False)
        v = f["verdict"]
        print(f"ANCRE {a} : tier={tiers_connus.get(a)} verdict={v['status']} "
              f"label={v['label']} badge={v['badge_division_libelle']}")
    db.close()
    ok = not (silencieux or montantes or vocab_legacy or erreurs)
    print("\nRESULTAT :", "0 divergence dans les deux sens — PASS" if ok else "DIVERGENCES — FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
