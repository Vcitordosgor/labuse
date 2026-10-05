"""SDP-VERIF-1 — dump LECTURE SEULE du calcul résiduel + deux scénarios pour chaque témoin.
Aucune écriture. Lance compute_residuel, faisabilite_scenario (les deux scénarios), lit la vue servie."""
import json, sys
from sqlalchemy import text
from labuse.db import session_scope
from labuse.faisabilite.db import parcel_faisabilite
from labuse.faisabilite.residuel import compute_residuel
from labuse.faisabilite.scenarios import faisabilite_scenario

WITNESSES = ["97410000AT1066", "97411000BZ1065", "97416000ES0981"]
# + control nue added via argv
if len(sys.argv) > 1:
    WITNESSES = sys.argv[1:]

def pid_of(s, idu):
    return s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()

with session_scope() as s:
    for idu in WITNESSES:
        pid = pid_of(s, idu)
        print("="*90)
        print(f"TÉMOIN {idu}  parcel_id={pid}")
        if pid is None:
            print("  INTROUVABLE"); continue
        # 1) moteur faisabilité brut (enveloppe)
        res = parcel_faisabilite(s, pid)
        if res is None:
            print("  parcel_faisabilite=None (hors PLU)"); continue
        ctx, f = res
        fr = f.fourchette or {}
        print(f"  zone={f.zone} commune={ctx.commune} surface={ctx.surface_m2:.0f} constructible={f.constructible} cause={f.cause} calibree={f.calibree}")
        print("  --- fourchette (enveloppe) ---")
        for k in ("zone_implantation_m2","emprise_sol_max_m2","emprise_constructible_m2",
                  "niveaux","niveaux_max","hauteur_m","surface_plancher_m2","logements_au_sol",
                  "assiette_source","stationnement_regime"):
            print(f"    {k} = {fr.get(k)}")
        # 2) résiduel (bâti gardé)
        r = compute_residuel(s, pid, faisa=res, assiette_clippee=True)
        print("  --- compute_residuel (assiette_clippee=True, bâti gardé) ---")
        print("    " + json.dumps(r, ensure_ascii=False, default=str))
        r0 = compute_residuel(s, pid, faisa=res, assiette_clippee=False)
        print("  --- compute_residuel (assiette_clippee=False, chemin SERVI) ---")
        print("    " + json.dumps(r0, ensure_ascii=False, default=str))
        # 3) vue servie
        srv = s.execute(text("SELECT taux_emprise_pct, pct_potentiel, sdp_residuelle_m2, sous_densite, cause, capacite_estimee, hauteur_source FROM parcel_residuel WHERE parcel_id=:p"), {"p": pid}).first()
        print(f"  --- vue servie parcel_residuel ---\n    {srv}")
        # 4) les deux scénarios (ce que sert l'outil Faisabilité)
        for sc in ("terrain_libere", "bati_garde"):
            d = faisabilite_scenario(s, pid, scenario=sc)
            if d is None:
                print(f"  SCÉNARIO {sc}: None"); continue
            print(f"  --- faisabilite_scenario({sc}) ---")
            print(f"    bati_present={d.get('bati_present')} sdp_possible_m2={d.get('sdp_possible_m2')} "
                  f"surface_a_demolir_m2={d.get('surface_a_demolir_m2')} logements={d.get('logements')}")
            print(f"    verdict={d.get('verdict')}")
            print(f"    ce_qui_limite={d.get('ce_qui_limite')}")
        # 5) emprise bâtie brute + stats bati
        import labuse.bati as bati_mod
        st = bati_mod.stats_batch(s, [pid]).get(pid, {})
        print(f"  --- bati.stats_batch ---\n    {st}")
