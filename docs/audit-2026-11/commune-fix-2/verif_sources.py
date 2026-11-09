"""COMMUNE-FIX-2 — vérification fait-par-fait des 24 fiches commune contre leurs sources.
Compare le payload SERVI (/communes/{c}/contexte, sauvé dans /tmp/cf2/<insee>.json) aux TABLES SOURCES
(INSEE population_legale + commune_insee_logement, Sitadel sitadel_permits, DVF dvf_mutations, SRU
commune_contexte_sru, GPU spatial_layers). Lecture seule. Sortie : tableau + liste des écarts."""
import json, glob, sys
import psycopg

DB = "postgresql://openclaw@localhost:5432/labuse"
cx = psycopg.connect(DB)
cx.autocommit = True

def q1(sql, **p):
    with cx.cursor() as c:
        c.execute(sql, p)
        r = c.fetchone()
        return r[0] if r else None

def qrow(sql, **p):
    with cx.cursor() as c:
        c.execute(sql, p)
        return c.fetchone()

def near(a, b, tol=0.0):
    if a is None and b is None: return True
    if a is None or b is None: return False
    try: return abs(float(a) - float(b)) <= tol
    except Exception: return str(a) == str(b)

payloads = {}
for f in sorted(glob.glob('/tmp/cf2/*.json')):
    d = json.load(open(f))
    payloads[d['insee']] = d

rows = []          # (insee, commune, famille, fait, servi, source, verdict)
ecarts = []

for insee, d in sorted(payloads.items()):
    nom = d['commune']
    pop = d.get('population') or {}
    sru = d.get('sru') or {}
    pb = d.get('permis_bloc') or {}
    cmp = d.get('comparable') or {}
    fon = d.get('foncier') or {}
    plu = d.get('plu_statut') or {}

    def check(famille, fait, servi, source, ok):
        v = 'V' if ok else 'R'
        rows.append((insee, nom, famille, fait, servi, source, v))
        if not ok:
            ecarts.append((insee, nom, famille, fait, servi, source))

    # ───── INSEE : population légale ─────
    src = qrow("SELECT pop_mun, millesime FROM population_legale WHERE insee=%(i)s", i=insee)
    s_pop, s_mil = (src if src else (None, None))
    check('INSEE', 'habitants (pop. municipale)', pop.get('habitants'), s_pop, near(pop.get('habitants'), s_pop))
    check('INSEE', 'millésime population', pop.get('habitants_millesime'), s_mil, str(pop.get('habitants_millesime')) == str(s_mil))

    # ───── INSEE : logement (RP) ─────
    lg = qrow("SELECT logements, res_principales, vacants FROM commune_insee_logement WHERE insee=%(i)s", i=insee)
    s_log, s_rp, s_vac = (lg if lg else (None, None, None))
    check('INSEE', 'logements', pop.get('logements'), s_log, near(pop.get('logements'), s_log))
    check('INSEE', 'ménages (rés. princ.)', pop.get('menages'), s_rp, near(pop.get('menages'), s_rp))
    s_vac_pct = round(100.0 * s_vac / s_log, 1) if (s_log and s_vac is not None) else None
    check('INSEE', 'vacance %', pop.get('vacance_pct'), s_vac_pct, near(pop.get('vacance_pct'), s_vac_pct, 0.1))

    # ───── SRU ─────
    sr = qrow("SELECT taux_lls, objectif_pct, statut, millesime, detail->>'nb_lls' FROM commune_contexte_sru WHERE insee=%(i)s", i=insee)
    if sr:
        s_taux, s_obj, s_stat, s_mille, s_nblls = sr
        check('SRU', 'taux LLS %', sru.get('taux_lls'), s_taux, near(sru.get('taux_lls'), s_taux, 0.05))
        check('SRU', 'objectif %', sru.get('objectif_pct'), s_obj, near(sru.get('objectif_pct'), s_obj, 0.05))
        check('SRU', 'statut', sru.get('statut'), s_stat, str(sru.get('statut')) == str(s_stat))
        nb = (sru.get('detail') or {}).get('nb_lls')
        check('SRU', 'nb LLS', nb, s_nblls, near(nb, float(s_nblls) if s_nblls else None, 0.5))
    else:
        check('SRU', 'présence table', bool(sru), 'absente', not sru)

    # ───── Sitadel : permis 12 mois (fenêtre ancrée au max(date) global) ─────
    s_p12 = q1("SELECT count(*) FROM sitadel_permits WHERE commune=%(c)s AND date > "
               "(SELECT max(date) FROM sitadel_permits) - interval '12 months'", c=nom)
    # le payload « permis_12m » = permis déposés 12 mois (inclut annulés) ; recompte brut
    check('Sitadel', 'permis 12 mois (nb)', pb.get('permis_12m'), s_p12, near(pb.get('permis_12m'), s_p12))

    # ───── DVF : médiane ancien €/m² (ventes bâti) ─────
    s_med = q1("SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY valeur_fonciere/NULLIF(surface_reelle_bati,0))) "
               "FROM dvf_mutations WHERE commune=%(c)s AND nature_mutation='Vente' AND valeur_fonciere>1000 "
               "AND valeur_fonciere/NULLIF(surface_reelle_bati,0) BETWEEN 100 AND 12000", c=nom)
    s_n = q1("SELECT count(*) FROM dvf_mutations WHERE commune=%(c)s AND nature_mutation='Vente' AND valeur_fonciere>1000 "
             "AND valeur_fonciere/NULLIF(surface_reelle_bati,0) BETWEEN 100 AND 12000", c=nom)
    s_med_served = s_med if (s_n or 0) >= 100 else None
    check('DVF', 'prix ancien médian €/m²', cmp.get('ancien_median_eur_m2'), s_med_served,
          near(cmp.get('ancien_median_eur_m2'), s_med_served, 1.0))

    # ───── DVF : mutations 12 mois (fenêtre ancrée au max par commune) ─────
    s_mut = q1("SELECT count(*) FROM dvf_mutations WHERE commune=%(c)s AND date_mutation > "
               "(SELECT max(date_mutation) FROM dvf_mutations WHERE commune=%(c)s) - interval '12 months'", c=nom)
    check('DVF', 'mutations 12 mois', fon.get('mutations_12m'), s_mut, near(fon.get('mutations_12m'), s_mut))

    # ───── GPU : zonage familles somme ~100 % (cohérence interne) ─────
    rep = (fon.get('repartition_zonage') or {}).get('familles') or {}
    somme = sum((rep.get(k) or {}).get('pct', 0) for k in ('U', 'AU', 'A', 'N')) if rep else None
    check('GPU', 'zonage Σ familles ≈100 %', somme, '≈100', somme is not None and 98.0 <= somme <= 102.0)

# ───── rapport ─────
n = len(rows)
nv = sum(1 for r in rows if r[6] == 'V')
print(f"TOTAL {n} faits · {nv} VERTS · {len(ecarts)} ÉCARTS\n")
if ecarts:
    print("=== ÉCARTS ===")
    for e in ecarts:
        print(f"  [{e[0]} {e[1]}] {e[2]} · {e[3]} : servi={e[4]!r} ≠ source={e[5]!r}")
else:
    print("AUCUN ÉCART — les 24 fiches sont conformes à leurs sources sur les faits vérifiés.")

# récap par famille
print("\n=== RÉCAP PAR FAMILLE ===")
fams = {}
for r in rows:
    fams.setdefault(r[2], [0, 0])
    fams[r[2]][0] += 1
    if r[6] == 'V': fams[r[2]][1] += 1
for f, (t, v) in sorted(fams.items()):
    print(f"  {f:10s} {v}/{t}")

# écrire le CSV complet
import csv
with open('/tmp/cf2/verif_table.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['insee', 'commune', 'famille', 'fait', 'servi', 'source', 'verdict'])
    w.writerows(rows)
print("\nTableau complet → /tmp/cf2/verif_table.csv")
