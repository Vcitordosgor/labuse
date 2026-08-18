"""M110 · gate — LA FACETTE EST INTERROGEABLE. Les critères branchés sur compter_parcelles rendent
LE MÊME chiffre que la facette (oracle indépendant, hand-SQL contre les tables brutes — jamais
`filtre()`), l'acronyme SIDR résout la BONNE entité, les concepts fantôme/bailleur ouvrent l'outil.

Bloquant : un critère branché qui diffère de la base · l'acronyme qui rate l'entité · un concept
qui ne route pas vers son outil. Modèle réel requis (ANTHROPIC_API_KEY).

Usage : .venv/bin/python qa/m110/veracite_facette.py
"""
from __future__ import annotations

from sqlalchemy import text

from labuse.copilote_v2.answering import answer
from labuse.copilote_v2.verifs import _num_match
from labuse.db import session_scope

RUN = "q_v9_m81"

# ── critères BRANCHÉS : oracle SQL indépendant (main-written), doit égaler le chiffre servi ──
CAS_COMPTE = [
    {"q": "Combien de parcelles en procédure judiciaire à Saint-Denis ?",   # LE CONSTAT de Vic
     "sql": "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Denis' AND EXISTS("
            "SELECT 1 FROM parcelle_personne_morale pms JOIN bodacc_procedures bps ON bps.siren=pms.siren "
            "WHERE pms.idu=p.idu)"},
    {"q": "Combien de friches à Saint-Paul ?",                              # était détourné au web
     "sql": "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Paul' AND EXISTS("
            "SELECT 1 FROM parcel_signaux_vie sv WHERE sv.idu=p.idu AND sv.signal='friche')"},
    {"q": "Combien de parcelles sans adresse à Saint-Pierre ?",
     "sql": "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Pierre' AND NOT EXISTS("
            "SELECT 1 FROM adresse_parcelles ap WHERE ap.idu=p.idu)"},
    {"q": "Combien de copropriétés à Saint-Denis ?",
     "sql": "SELECT count(*) FROM parcels p JOIN parcel_p_score_v2 s ON s.parcelle_id=p.idu "
            "AND s.run_id=:run WHERE p.commune='Saint-Denis' AND s.copro"},
    {"q": "Combien de parcelles en défiscalisation à Saint-Leu ?",
     "sql": "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Leu' AND EXISTS("
            "SELECT 1 FROM defisc_fenetres df WHERE df.idu=p.idu AND df.fenetre_active)"},
    {"q": "Combien de parcelles d'au moins 5000 m² en renouvellement urbain à Saint-Denis ?",  # M109 → 213
     "sql": "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Denis' AND p.surface_m2>=5000 "
            "AND EXISTS(SELECT 1 FROM parcel_renouvellement rn WHERE rn.idu=p.idu AND rn.run_label=:run)"},
    {"q": "Combien de parcelles en zone U à Saint-Benoît ?",               # M109 miscompte 21671 → vrai
     "sql": "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Benoît' AND EXISTS("
            "SELECT 1 FROM parcel_zone_plu z WHERE z.idu=p.idu AND z.zone_fam='U')"},
    {"q": "Combien de parcelles à événement rouge à Saint-Denis ?",
     "sql": "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Denis' AND EXISTS("
            "SELECT 1 FROM dryrun_cascade_results c WHERE c.parcel_id=p.id AND c.run_label=:run "
            "AND c.evenement='rouge')"},
    {"q": "Quelles parcelles appartiennent à la SIDR ?",                   # M110 acronyme → 4183 (pas 16)
     "sql": "SELECT count(DISTINCT pm.idu) FROM parcelle_personne_morale pm JOIN parcels p "
            "ON p.idu=pm.idu WHERE pm.siren='310863592'"},
]

# ── concepts-outils : M118 — ouvrir un outil QUITTE le chat → refus + voie « outils » (navigation,
# jamais exécution). Le comptage facette (au-dessus) reste, lui, une mission 1 servie. ──
CAS_PORTE = [
    {"q": "Montre-moi les parcelles fantômes à Saint-Paul", "voie": "outils"},
    {"q": "Quelles parcelles de bailleurs sociaux à Saint-Denis", "voie": "outils"},
]


def main() -> int:
    echecs = []
    with session_scope() as db:
        for c in CAS_COMPTE:
            oracle = db.execute(text(c["sql"]), {"run": RUN}).scalar()
            rep = answer(db, c["q"])
            txt = rep.get("text", "")
            cna = rep.get("criteres_non_appliques") or []
            if cna:
                echecs.append((c["q"], f"critère faussement lâché : {cna}"))
            elif not _num_match(oracle, txt):
                echecs.append((c["q"], f"servi ≠ oracle {oracle} : {txt[:110]}"))
            else:
                print(f" OK  [{oracle}] {c['q'][:64]}")
        for c in CAS_PORTE:
            rep = answer(db, c["q"])
            got = (rep.get("voie") or {}).get("cible")
            if rep.get("refus") != "hors_mission" or got != c["voie"]:
                echecs.append((c["q"], f"refus-voie {c['voie']} attendu, obtenu refus={rep.get('refus')} voie={got}"))
            else:
                print(f" OK  [voie {c['voie']}] {c['q'][:56]}")
    total = len(CAS_COMPTE) + len(CAS_PORTE)
    print(f"\n=== BILAN FACETTE M110 : {total - len(echecs)}/{total} ===")
    for q, why in echecs:
        print(f"  ÉCHEC : {q[:60]} — {why}")
    return 0 if not echecs else 1


if __name__ == "__main__":
    raise SystemExit(main())
