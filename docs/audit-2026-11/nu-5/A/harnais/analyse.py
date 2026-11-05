#!/usr/bin/env python
"""NU5-A — synthèse de cohérence. Lit preuves/resultats.json et, pour chaque
parcelle × outil, extrait le statut + les chiffres clés et calcule l'écart à la fiche.
Produit un tableau lisible (stdout) qui alimente le jugement vert/orange/rouge du RAPPORT.
"""
from __future__ import annotations
import json

R = json.load(open("docs/audit-2026-11/nu-5/A/preuves/resultats.json"))

def g(d, *ks, default=None):
    for k in ks:
        if not isinstance(d, dict): return default
        d = d.get(k)
    return d if d is not None else default

def st(call):
    if not isinstance(call, dict): return "?"
    if "skip" in call: return "skip"
    return str(call.get("status"))

def jj(call): return call.get("json", {}) if isinstance(call, dict) else {}

def summarize():
    for piege, blk in R["parcelles"].items():
        idu = blk["idu"]; f = blk["fiche"]; o = blk["outils"]
        print(f"\n{'='*90}\n{piege}  {idu}  ({blk['commune']})")
        print(f"  FICHE: surf_terrain={f.get('surface_terrain_m2')} dessin={f.get('surface_dessin_m2')} "
              f"etat={f.get('etat_bien')} zone={f.get('zone_lib')}/{f.get('zone_fam')} "
              f"constr={f.get('constructible')} sdp_rest={f.get('sdp_restante_m2')} "
              f"pente={f.get('pente_moy_deg')} copro_n={f.get('coproprietes_n')} "
              f"taux_com={f.get('taux_communal_pct')} pm_siren={f.get('pm_siren')}")
        if f.get("aleas"): print(f"         aleas: {f['aleas']}")
        # par outil
        ri = o.get("risques", {})
        print(f"  risques[{st(ri)}]: n={g(jj(ri),'n')} synthese={str(g(jj(ri),'synthese'))[:70]}")
        if g(jj(ri),'servitudes'):
            for s in jj(ri)['servitudes'][:4]:
                print(f"      - {s.get('categorie')}: {str(s.get('effet'))[:80]} redhib={s.get('redhibitoire')}")
        ga = o.get("gabarit", {})
        jg = jj(ga)
        print(f"  gabarit[{st(ga)}]: status={jg.get('status')} msg={str(jg.get('message'))[:50]} "
              f"surfParc={jg.get('surfaceParcelleM2')} zoneImpl_m2={jg.get('zoneImplantationM2')} "
              f"hauteur={jg.get('hauteurReglementaireM')} emprisePct={jg.get('plafondEmprisePct')} "
              f"multizone={g(jg,'raccordement','multizone')}")
        tp = o.get("taxe_prefill", {})
        print(f"  taxe_prefill[{st(tp)}]: zone={g(jj(tp),'zone')} terrain_m2={g(jj(tp),'surface_terrain_m2')} "
              f"sdp_ref={g(jj(tp),'sdp_gabarit_m2')} taux_com={g(jj(tp),'taux_communal_pct')}")
        es = o.get("estimation", {})
        je = jj(es)
        print(f"  estimation[{st(es)}]: median={je.get('median')} n={je.get('n')} fiab={je.get('fiabilite_mot')} "
              f"type={je.get('type_comparateur')} note={str(je.get('note'))[:60]}")
        so = o.get("solaire_parcelle", {})
        js = jj(so)
        print(f"  solaire[{st(so)}]: ok={js.get('ok')} productible={js.get('productible')} toit_m2={js.get('toit_m2')} "
              f"abf={js.get('abf')} proba_occ={js.get('proba_occ')}")
        tm = o.get("temps_epoque", {})
        print(f"  temps[{st(tm)}]: millesimes={g(jj(tm),'millesimes')} n_features={len(g(jj(tm),'features',default=[]))}")
        pp = o.get("parcelle_permis", {})
        print(f"  parcelle_permis[{st(pp)}]: n={len(g(jj(pp),'permis',default=g(jj(pp),'items',default=[])))}")
        cp = o.get("comparer", {})
        jc = jj(cp)
        pr = (jc.get('parcels') or [{}])
        p0 = pr[0] if pr else {}
        print(f"  comparer[{st(cp)}]: count={jc.get('count')} surf0={p0.get('surface_m2')} zone0={p0.get('zone')} "
              f"sdp_max={p0.get('sdp_max_m2')} sdp_res={p0.get('sdp_residuelle_m2')} proprio={p0.get('proprietaire')}")
        ez = o.get("etude_zone", {})
        print(f"  etude_zone[{st(ez)}]: dispo={g(jj(ez),'zone_disponible')} rayon={g(jj(ez),'rayon_km')} "
              f"hab={g(jj(ez),'population','habitants')} note={str(g(jj(ez),'note'))[:40]}")
        asg = o.get("assemblage_seule", {})
        print(f"  assemblage_1[{st(asg)}]: n={g(jj(asg),'n')} contigu={g(jj(asg),'contigu')} err={asg.get('error','')[:60]}")
        ca = o.get("calculette", {})
        jca = jj(ca)
        print(f"  calculette[{st(ca)}]: calculable={jca.get('calculable')} charge_central={g(jca,'charge_fonciere','central')} "
              f"par_m2={g(jca,'charge_fonciere','par_m2_terrain')} note={str(jca.get('note'))[:50]}")
        pa = o.get("patrimoine", {})
        print(f"  patrimoine[{st(pa)}]: n={g(jj(pa),'n')} nom={str(g(jj(pa),'nom'))[:40]}")
        cac = o.get("communes_acq", {})
        print(f"  communes_acq[{st(cac)}]: n={g(jj(cac),'n')}")

if __name__ == "__main__":
    summarize()
