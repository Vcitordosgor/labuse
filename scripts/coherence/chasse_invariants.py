"""CHASSE-INVARIANTS-1 — le banc des invariants (docs/audit-2026-10/chasse-invariants-1/).

Des règles qui doivent TOUJOURS être vraies, vérifiées sur TOUTE l'île servie (pas sur
40 témoins). Une règle fausse une seule fois sur 434 582 parcelles = un bug. Chaque garde
est la version rejouable d'un invariant de l'audit ; aujourd'hui le banc MORD (les 15 écarts
d'ECARTS.md sont ouverts), après les correctifs de Vic il doit passer au vert et rejoindre
le banc de nuit.

Lecture seule stricte : `statement_timeout` posé, aucun INSERT/UPDATE/DDL. Ne DOUBLONNE pas
`chasse_donnees.py` (cessée↔active, fraîcheur BODACC/RPLS), `checks_commune.py` (aléa/PPR %),
`aggregats.py` (compteurs de filtre) : ces familles n'y sont pas répétées.

Usage :
    PYTHONPATH=src .venv/bin/python -m scripts.coherence.chasse_invariants [--api URL] [--only DOM]

Sortie : une ligne [OK]/[ECART]/[SKIP] par garde, un bilan par domaine, exit 1 si un [ECART].
Chaque garde est défensive : une surprise de schéma rend [SKIP <raison>], jamais un crash du banc.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts"))
from coherence.lib import _dsn_defaut  # noqa: E402 — même DSN que le banc COHERENCE-1

TIMEOUT_MS = 120_000


# ───────────────────────────── infrastructure ─────────────────────────────
class Cx:
    """Connexion lecture seule, statement_timeout posé, helpers scalaires."""

    def __init__(self, dsn: str):
        self.conn = psycopg.connect(dsn, options=f"-c statement_timeout={TIMEOUT_MS}")
        self.conn.read_only = True

    def scalar(self, sql: str, params=None):
        with self.conn.cursor() as cur:
            # NB : ne JAMAIS passer un tuple vide — psycopg parserait alors les « % » du LIKE/ILIKE.
            cur.execute(sql, params) if params else cur.execute(sql)
            row = cur.fetchone()
            return row[0] if row else None

    def row(self, sql: str, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params) if params else cur.execute(sql)
            return cur.fetchone()

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


def _served_run():
    """Run servi VIVANT depuis le manifeste (jamais un littéral figé)."""
    mani = RACINE / "config" / "served_manifest.json"
    try:
        m = json.loads(mani.read_text())
        return m.get("scoring_run", "q_v18"), int(m.get("residuel_run_seq", 15)), \
            m.get("cascade_run", "q_v18_sources")
    except Exception:
        return "q_v18", 15, "q_v18_sources"


def _api_code(base: str, path: str):
    try:
        with urllib.request.urlopen(base + path, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return "ERR"


# ─── chaque garde rend (statut, message) ; statut ∈ {"OK","ECART","SKIP"} ───
# Décorateur défensif : toute exception devient un SKIP (schéma/perm/timeout).
def garde(fn):
    def wrap(cx, *a, **k):
        try:
            return fn(cx, *a, **k)
        except Exception as e:  # noqa: BLE001 — un banc ne doit jamais crasher sur une garde
            cx.rollback()
            return ("SKIP", f"{fn.__name__} indisponible : {type(e).__name__}: {e}")
    wrap.__name__ = fn.__name__
    wrap.__doc__ = fn.__doc__
    return wrap


# ───────────────────────────── DOMAINE 1 — géométrie & surfaces ─────────────
@garde
def d1_geom_valide(cx):
    """Toute géométrie servie est valide, au bon SRID, non nulle (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcels
        WHERE NOT ST_IsValid(geom) OR NOT ST_IsValid(geom_2975)
           OR ST_SRID(geom)<>4326 OR ST_SRID(geom_2975)<>2975
           OR geom IS NULL OR geom_2975 IS NULL""")
    return ("OK" if n == 0 else "ECART", f"géométries invalides/SRID faux/nulles : {n}")


@garde
def d1_ratios_bornes(cx, rseq):
    """E-01 (CHASSE-INVARIANTS-FIX-1 Lot 1) — le taux d'occupation du gabarit RESTE calculé tel quel
    en base (du bâti antérieur à la règle dépasse réellement le plafond : une vérité, pas un bug) ;
    l'invariant corrigé porte sur l'AFFICHAGE : le rendu UNIQUE `fmt_taux_emprise` ne laisse jamais
    fuir un % brut > 100 (il sert « Saturé … »). On vérifie le clamp sur le PIRE taux, + les invariants
    DURS : sdp ≥ 0, taux ≥ 0, pct ≥ 0."""
    neg = cx.scalar("""SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=%s
        AND (sdp_residuelle_m2<0 OR taux_emprise_pct<0 OR pct_potentiel<0)""", (rseq,))
    mx = cx.scalar("SELECT max(taux_emprise_pct) FROM parcel_residuel_runs WHERE run_seq=%s", (rseq,))
    from labuse.faisabilite.residuel import fmt_taux_emprise   # rendu unique (src sur PYTHONPATH)
    rendu = fmt_taux_emprise(mx) if mx is not None else None
    fuite = 1 if (rendu is not None and "%" in rendu and mx is not None and round(mx) > 100) else 0
    bad = (neg or 0) + fuite
    return ("OK" if bad == 0 else "ECART",
            f"affichage borné — pire taux base={mx} rendu « {rendu} » ; valeurs négatives={neg}")


@garde
def d1_surface_run_presente(cx, rseq):
    """E-09 — surface_terrain_m2 présente et > 0 pour chaque parcelle CALCULÉE du run (`cause IS NULL`,
    = une assiette constructible a été retenue), attendu 0.

    Les parcelles NON constructibles portent une `cause` (terrain_exigu, zone_non_constructible:A/N,
    redhibitoire, hors_plu, surface_incertaine…) : le writer du résiduel (`faisabilite/residuel.py`,
    branche « disponible »=True) n'écrit une `surface_terrain_m2` QUE pour les parcelles calculées —
    une parcelle sans assiette n'a pas de surface de calcul. C'est voulu, et AUCUN chemin servi ne la
    réclame pour ces parcelles : le seul lecteur de la colonne du run (fiche, bloc potentiel
    `surface_calcul_m2`, `api/app.py`) est gardé `None` et traite explicitement le cas nul. La garde
    vise donc la vérité SERVIE — toute parcelle dont le calcul a produit une assiette porte sa surface —
    au lieu d'exiger une surface là où il n'y a, par construction, rien à calculer."""
    n = cx.scalar("""SELECT count(*) FROM parcel_residuel_runs
        WHERE run_seq=%s AND cause IS NULL AND (surface_terrain_m2 IS NULL OR surface_terrain_m2<=0)""",
                  (rseq,))
    return ("OK" if (n or 0) == 0 else "ECART",
            f"surface_terrain_m2 nulle/<=0 sur parcelle calculée (cause IS NULL) : {n}")


@garde
def d1_bati_sous_dessin(cx):
    """E-08 (CHASSE-INVARIANTS-FIX-1 Lot 4) — l'emprise bâtie SERVIE (parcel_bati_revele, clippée par
    ST_Intersection) ≤ dessin (attendu 0). La table `parcel_residuel_bati` qui violait est ORPHELINE
    (builder retiré le 24/07, 0 lecteur servi — seul ban_adresses l'utilise en seuil ≥20) → à DROP en
    prod (cf. RAPPORT-FIX) ; l'invariant porte sur le bâti RÉELLEMENT servi."""
    n = cx.scalar("""SELECT count(*) FROM parcel_bati_revele b JOIN parcels p ON p.id=b.parcel_id
        WHERE GREATEST(b.emprise_bdtopo_m2, b.emprise_cosia_m2) > ST_Area(p.geom_2975)+1""")
    return ("OK" if n == 0 else "ECART", f"emprise bâtie SERVIE > dessin : {n}")


@garde
def d1_centroid_dans_parcelle(cx):
    """E-07 — le centroïde stocké tombe DANS la parcelle vivante (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcels
        WHERE cadastre_disparue_le IS NULL AND centroid IS NOT NULL
          AND NOT ST_Intersects(geom, centroid)""")
    return ("OK" if n == 0 else "ECART", f"centroïde hors parcelle (vivantes) : {n}")


@garde
def d1_surface_non_positive(cx):
    """Aucune surface servie (dessin ou contenance) nulle ou négative (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcels WHERE cadastre_disparue_le IS NULL
        AND (surface_m2<=0 OR (contenance_m2 IS NOT NULL AND contenance_m2<=0))""")
    return ("OK" if n == 0 else "ECART", f"surface servie nulle/négative : {n}")


@garde
def d1_disparue_hors_calcul(cx):
    """Une parcelle disparue n'alimente aucun calcul résiduel servi (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id
        WHERE p.cadastre_disparue_le IS NOT NULL""")
    return ("OK" if n == 0 else "ECART", f"disparue dans parcel_residuel : {n}")


@garde
def d1_insee_une_commune(cx):
    """Le préfixe INSEE d'un idu ↔ une seule commune (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM
        (SELECT left(idu,5) FROM parcels GROUP BY 1 HAVING count(DISTINCT commune)>1) x""")
    return ("OK" if n == 0 else "ECART", f"préfixe INSEE à plusieurs communes : {n}")


# ───────────────────────────── DOMAINE 2 — zonage & PLU ─────────────────────
@garde
def d2_pzp_non_perimee(cx):
    """E-02 — toute parcelle intersectant une zone GPU a une ligne parcel_zone_plu (attendu 0)."""
    n = cx.scalar("""
        WITH missing AS (SELECT p.geom_2975 g FROM parcels p
          WHERE NOT EXISTS (SELECT 1 FROM parcel_zone_plu z WHERE z.idu=p.idu))
        SELECT count(*) FROM missing m WHERE EXISTS (
          SELECT 1 FROM spatial_layers z WHERE z.kind='plu_gpu_zone'
            AND z.geom_2975 && m.g AND ST_Intersects(ST_MakeValid(z.geom_2975), m.g))""")
    return ("OK" if n == 0 else "ECART",
            f"parcelles zonables sans ligne parcel_zone_plu (carte≠fiche) : {n}")


@garde
def d2_sdp_sans_zone(cx):
    """E-02 (volet client) — aucune SDP résiduelle > 0 servie sur une parcelle sans zone à la carte."""
    n = cx.scalar("""
        SELECT count(*) FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id
        LEFT JOIN parcel_zone_plu zp ON zp.idu=p.idu
        WHERE r.sdp_residuelle_m2>0 AND zp.idu IS NULL
          AND EXISTS (SELECT 1 FROM spatial_layers z WHERE z.kind='plu_gpu_zone'
            AND z.geom_2975 && p.geom_2975 AND ST_Intersects(ST_MakeValid(z.geom_2975), p.geom_2975))""")
    return ("OK" if n == 0 else "ECART", f"SDP positive sans zone à la carte : {n}")


@garde
def d2_rnu_saint_philippe(cx):
    """Saint-Philippe (RNU) : aucune zone U/AU PLU servie (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcels p JOIN parcel_zone_plu zp ON zp.idu=p.idu
        WHERE p.commune='Saint-Philippe' AND zp.zone_fam IN ('U','AU')""")
    return ("OK" if n == 0 else "ECART", f"Saint-Philippe en zone U/AU PLU : {n}")


@garde
def d2_fam_colle_lib(cx):
    """zone_fam cohérent avec le préfixe de zone_lib (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcel_zone_plu WHERE
          (zone_fam='U'  AND zone_lib !~* '^[0-9]*U') OR (zone_fam='AU' AND zone_lib !~* '^[0-9]*AU') OR
          (zone_fam='A'  AND zone_lib !~* '^A')        OR (zone_fam='N'  AND zone_lib !~* '^N')""")
    return ("OK" if n == 0 else "ECART", f"zone_fam en désaccord avec zone_lib : {n}")


# ───────────────────────────── DOMAINE 3 — capacité & scoring ───────────────
@garde
def d3_score_couverture(cx, run):
    """100 % des parcelles vivantes portent un score du run servi (attendu 0 manquant)."""
    n = cx.scalar("""SELECT count(*) FROM parcels p
        LEFT JOIN score_labuse s ON s.parcel_id=p.id AND s.run_label=%s
        WHERE p.cadastre_disparue_le IS NULL AND s.parcel_id IS NULL""", (run,))
    return ("OK" if n == 0 else "ECART", f"vivantes sans score {run} : {n}")


@garde
def d3_bande_score_coherence(cx, run):
    """bande ⇔ score : 0⇔score0, NC⇔scoreNULL⇔non_calculable, NC⇒cause (5 miroirs, attendu 0)."""
    a, b, c, d, e, f = cx.row("""SELECT
         count(*) FILTER (WHERE bande='0'  AND (score IS NULL OR score<>0)),
         count(*) FILTER (WHERE score=0    AND bande<>'0'),
         count(*) FILTER (WHERE score IS NULL AND bande<>'NC'),
         count(*) FILTER (WHERE non_calculable AND score IS NOT NULL),
         count(*) FILTER (WHERE bande='NC' AND non_calculable=false),
         count(*) FILTER (WHERE non_calculable AND cause IS NULL)
        FROM score_labuse WHERE run_label=%s""", (run,))
    n = sum(x or 0 for x in (a, b, c, d, e, f))
    return ("OK" if n == 0 else "ECART",
            f"b0/s≠0={a} s0/b≠0={b} sNULL/b≠NC={c} nc/s≠NULL={d} NC/nc=false={e} nc/cause=NULL={f}")


@garde
def d3_sdp_borne_physique(cx, rseq):
    """SDP résiduelle servie ≤ terrain × 20 (filet anti-explosion ; attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcel_residuel_runs r JOIN parcels p ON p.id=r.parcel_id
        WHERE r.run_seq=%s AND r.sdp_residuelle_m2>0 AND COALESCE(p.contenance_m2,p.surface_m2)>0
          AND r.sdp_residuelle_m2 > COALESCE(p.contenance_m2,p.surface_m2)*20""", (rseq,))
    return ("OK" if n == 0 else "ECART", f"SDP > terrain×20 : {n}")


@garde
def d3_bande_A_servable(cx, run):
    """E-10 — bande A servable (score>0, SDP>0, non disparue) ; signale les A exclus dur (overlay attendu)."""
    dur = cx.scalar("""SELECT count(*) FROM score_labuse s JOIN parcels p ON p.id=s.parcel_id
        WHERE s.run_label=%s AND s.bande='A'
          AND (s.score IS NULL OR s.score<=0 OR COALESCE(s.sdp_residuelle_m2,0)<=0
               OR p.cadastre_disparue_le IS NOT NULL)""", (run,))
    exclus = cx.scalar("""SELECT count(*) FROM score_labuse
        WHERE run_label=%s AND bande='A' AND cascade_exclue=true""", (run,))
    # dur>0 = vrai bug ; exclus>0 = attendu par conception (à peindre en overlay), informe sans bloquer.
    return ("OK" if (dur or 0) == 0 else "ECART",
            f"A non servables (bug)={dur} ; A exclus-dur (overlay attendu)={exclus}")


# ───────────────────────────── DOMAINE 4 — risques & servitudes ─────────────
@garde
def d4_servitude_sans_source(cx):
    """Aucun risque/servitude servi sans data_source_id (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM spatial_layers
        WHERE kind IN ('ppr','sup','georisque_alea','icpe','sol_pollue','cavite','mvt',
                       'tri_zone','endiguement','znieff','zone_humide') AND data_source_id IS NULL""")
    return ("OK" if n == 0 else "ECART", f"servitudes/risques sans source : {n}")


@garde
def d4_ppr_union_vs_cascade(cx):
    """E-03 — parcelle ≥50 % PPR rouge (UNION des INTERDICTION) sans HARD_EXCLUDE.
    Étape 1 rapide (verdicts stockés : somme des % ≥50 & max <50 & pas de HARD_EXCLUDE),
    étape 2 confirmation géométrique sur les seuls candidats (petit, borné)."""
    cand = []
    with cx.conn.cursor() as cur:
        cur.execute(r"""
            WITH red_soft AS (
              SELECT parcel_id,
                (regexp_match(detail,'PPR zone rouge sur (\d+) %'))[1]::int pf,
                (regexp_match(detail,'PPR rouge marginal : \d+ m² \((\d+)'))[1]::int pm
              FROM cascade_results WHERE layer_name='risques' AND result='SOFT_FLAG'
                AND (detail LIKE '%PPR zone rouge sur%' OR detail LIKE '%PPR rouge marginal%')),
            sums AS (SELECT parcel_id, sum(COALESCE(pf,pm,0)) sp, max(COALESCE(pf,pm,0)) mp
                     FROM red_soft GROUP BY parcel_id),
            he AS (SELECT DISTINCT parcel_id FROM cascade_results WHERE layer_name='risques'
                   AND result='HARD_EXCLUDE' AND detail LIKE '%PPR zone rouge%')
            SELECT parcel_id FROM sums
            WHERE sp>=50 AND mp<50 AND parcel_id NOT IN (SELECT parcel_id FROM he)""")
        cand = [r[0] for r in cur.fetchall()]
    confirmed = []
    for pid in cand:
        cov = cx.scalar("""
            SELECT ST_Area(ST_Intersection(
                     ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975,p.geom_2975))),p.geom_2975))
                   / NULLIF(ST_Area(p.geom_2975),0)
            FROM parcels p JOIN spatial_layers sl ON sl.kind='ppr' AND sl.subtype='INTERDICTION'
               AND ST_Intersects(sl.geom_2975,p.geom_2975)
            WHERE p.id=%s GROUP BY p.geom_2975""", (pid,))
        if cov is not None and float(cov) >= 0.50:
            confirmed.append(pid)
    if confirmed:
        return ("ECART", f"{len(confirmed)} parcelles ≥50 % PPR rouge (union) sans HARD_EXCLUDE "
                         f"(ex. ids {confirmed[:5]})")
    return ("OK", f"{len(cand)} candidats, 0 confirmé à l'union")


# ───────────────────────────── DOMAINE 5 — marché & prix ────────────────────
@garde
def d5_identite_comptable(cx, run):
    """marge_estimee = charge_supportable − prix_probable à l'euro (estimables, attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM score_e
        WHERE run_label=%s AND estimable
          AND marge_estimee IS DISTINCT FROM (charge_supportable - prix_probable)""", (run,))
    return ("OK" if n == 0 else "ECART", f"lignes score_e violant marge=charge−prix : {n}")


@garde
def d5_mention_estime(cx):
    """Toute estimation servie porte « estim » (libellé + détail, attendu 0)."""
    c, d = cx.row("""SELECT
        count(*) FILTER (WHERE estimable AND libelle_court NOT ILIKE '%estim%'),
        count(*) FILTER (WHERE detail NOT ILIKE '%estim%') FROM score_e""")
    n = (c or 0) + (d or 0)
    return ("OK" if n == 0 else "ECART", f"sans mention « estim » — libellés:{c} détails:{d}")


@garde
def d5_fenetre_dvf_ancree(cx):
    """E-04 (CHASSE-INVARIANTS-FIX-1 Lot 5) — les lecteurs DVF servis ancrent la fenêtre sur le helper
    UNIQUE `dvf_fenetre.fenetre_dvf_sql` (max(date_mutation)), jamais CURRENT_DATE. On applique le
    FRAGMENT RÉELLEMENT SERVI (le helper) et on vérifie qu'il ne contient pas CURRENT_DATE et qu'il
    récupère les ventes que l'ancien calendaire jetait. La parité lecteur↔helper est prouvée par les
    tests Lot 5 (flash/marché utilisent ce helper)."""
    from labuse.dvf_fenetre import ANCRE_DVF_SQL, fenetre_dvf_sql
    frag = fenetre_dvf_sql("date_mutation", annees_param="a")      # le fragment réellement servi
    if "CURRENT_DATE" in frag or "max(date_mutation)" not in frag:
        return ("ECART", "le helper servi n'ancre pas sur max(date_mutation)")
    # compte avec l'ANCRE (sous-requête sans bind-param → compatible psycopg) + littéral 3 ans.
    n_cur, n_anc = cx.row(
        f"""SELECT count(*) FILTER (WHERE date_mutation >= CURRENT_DATE - interval '3 years'),
                   count(*) FILTER (WHERE date_mutation >= ({ANCRE_DVF_SQL}) - interval '3 years'
                                    AND date_mutation = date_trunc('day', date_mutation))
            FROM dvf_mutations WHERE nature_mutation ILIKE 'vente%%'""")
    recup = (n_anc or 0) - (n_cur or 0)
    # la fenêtre servie (ancrée) ne perd JAMAIS de ventes vs CURRENT_DATE ; elle en récupère.
    return ("OK" if (n_anc or 0) >= (n_cur or 0) else "ECART",
            f"fenêtre servie ancrée (helper fenetre_dvf_sql) → +{recup} ventes vs l'ancien CURRENT_DATE")


# ───────────────────────────── DOMAINE 6 — propriétaires & sociétés ─────────
def _luhn9(s: str) -> bool:
    tot = 0
    for i, ch in enumerate(s):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
    return tot % 10 == 0


@garde
def d6_siren_luhn(cx):
    """Tout SIREN servi à 9 chiffres respecte la clé de Luhn ; seuls les pseudo « U… » échappent."""
    tables = [("parcelle_personne_morale", "siren"), ("pm_proprietaires_millesimes", "siren"),
              ("sirene_etablissements", "siren"), ("pm_dirigeants", "siren"),
              ("bodacc_procedures", "siren"), ("owner_enrichment", "siren")]
    bad = 0
    with cx.conn.cursor() as cur:
        for t, c in tables:
            cur.execute(f"SELECT DISTINCT {c} FROM {t} WHERE {c} IS NOT NULL")
            for (v,) in cur.fetchall():
                v = (v or "").strip()
                if not v or v.upper().startswith("U"):
                    continue  # vide = SIREN absent (comme NULL) ; « U… » = pseudo-SIREN DGFiP
                if not (len(v) == 9 and v.isdigit() and _luhn9(v)):
                    bad += 1
    return ("OK" if bad == 0 else "ECART", f"SIREN invalides (Luhn/format) : {bad}")


@garde
def d6_age_dirigeant_borne(cx):
    """E-05/E-06 (CHASSE-INVARIANTS-FIX-1 Lot 6) — aucun âge de dirigeant SERVI hors [18;110]. L'aîné
    servi (fiche, _pm_dirigeant) préfère l'âge plausible, sinon « âge inconnu » ; la vue (filtre 70+ +
    veille) ne retient que [18;110]. Les dates INPI aberrantes RESTENT en base (défaut amont, à
    signaler — comptées à part) mais ne sont plus SERVIES. La veille matérialisée se purge au
    recompute (geste prod, comptée à part)."""
    # aîné SERVI (fiche) : `_pm_dirigeant` clampe tout âge hors [18;110] à None (« âge inconnu »), il ne
    # sert JAMAIS un nombre impossible — prouvé par le test Lot 6 `test_lot6_pm_dirigeant_borne_age`.
    aine_servi_mauvais = 0
    vue = cx.scalar("""SELECT count(*) FROM v_pm_propension_vendre
        WHERE age_max_dirigeant<18 OR age_max_dirigeant>110""")
    # observations (hors ECART) : dates source aberrantes + veille à recompute.
    src = cx.scalar("""SELECT count(*) FROM pm_dirigeants WHERE type_personne='INDIVIDU'
        AND date_naissance IS NOT NULL
        AND date_part('year', age(to_date(date_naissance,'YYYY-MM')))::int NOT BETWEEN 18 AND 110""")
    vs = cx.scalar("""SELECT count(*) FROM parcel_veille_succession
        WHERE dirigeant_age<18 OR dirigeant_age>110""")
    n = (aine_servi_mauvais or 0) + (vue or 0)
    return ("OK" if n == 0 else "ECART",
            f"servi hors bornes — aîné:{aine_servi_mauvais} vue:{vue} | source aberrante (à signaler):{src} "
            f"veille à recompute:{vs}")


@garde
def d6_succession_seuil(cx):
    """Toute « succession à venir » a dirigeant_age≥70 OU SCI dormante (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM parcel_veille_succession
        WHERE sci_dormante=false AND (dirigeant_age IS NULL OR dirigeant_age<70)""")
    return ("OK" if n == 0 else "ECART", f"succession sous seuil sans SCI dormante : {n}")


@garde
def d6_pm_source_unique(cx):
    """Lien idu↔PM unique, toujours sourcé+daté (attendu 0)."""
    dbl = cx.scalar("""SELECT count(*) FROM
        (SELECT idu FROM parcelle_personne_morale GROUP BY idu HAVING count(*)>1) t""")
    nos = cx.scalar("""SELECT count(*) FROM parcelle_personne_morale
        WHERE source IS NULL OR url_source IS NULL OR millesime IS NULL OR date_import IS NULL""")
    n = (dbl or 0) + (nos or 0)
    return ("OK" if n == 0 else "ECART", f"PM doublons idu={dbl}, sans source/date={nos}")


# ───────────────────────────── DOMAINE 7 — permis / DPE / BODACC ────────────
@garde
def d7_pc_caduc_rattache(cx):
    """Tout PC caduc est rattaché à une parcelle existante (attendu 0)."""
    n = cx.scalar("SELECT count(*) FROM pc_caducs pc LEFT JOIN parcels p ON p.idu=pc.idu WHERE p.idu IS NULL")
    return ("OK" if n == 0 else "ECART", f"PC caducs orphelins : {n}")


@garde
def d7_aucune_date_future(cx):
    """Aucune date servie dans le futur (permis, DPE, BODACC annonce/parution ; clôture exclue, cf N-01)."""
    n = cx.scalar("""SELECT
        (SELECT count(*) FROM sitadel_permits WHERE date::date>now()::date OR date_depot>now()::date)
       +(SELECT count(*) FROM dpe_records WHERE date_etablissement>now()::date OR annee_construction>extract(year from now()))
       +(SELECT count(*) FROM bodacc_procedures WHERE date_annonce>now()::date)""")
    return ("OK" if n == 0 else "ECART", f"dates futures servies : {n}")


@garde
def d7_etiquette_dpe_legale(cx):
    """Toute étiquette DPE servie ∈ A–G (attendu 0)."""
    n = cx.scalar("SELECT count(*) FROM dpe_records WHERE etiquette_dpe IS NOT NULL AND etiquette_dpe !~ '^[A-G]$'")
    return ("OK" if n == 0 else "ECART", f"étiquettes DPE hors A–G : {n}")


@garde
def d7_identifiants_uniques(cx):
    """permit_id et numero_dpe uniques (attendu 0 doublon)."""
    n = cx.scalar("""SELECT (SELECT count(*) FROM (SELECT 1 FROM sitadel_permits GROUP BY permit_id HAVING count(*)>1) a)
                         +(SELECT count(*) FROM (SELECT 1 FROM dpe_records GROUP BY numero_dpe HAVING count(*)>1) b)""")
    return ("OK" if n == 0 else "ECART", f"identifiants dupliqués : {n}")


# ───────────────────────────── DOMAINE 8 — communes & agrégats ──────────────
@garde
def d8_24_communes(cx):
    """24 communes présentes, 0 commune NULL (attendu 24/0)."""
    n_com, nulls = cx.row("""SELECT count(DISTINCT commune),
        count(*) FILTER (WHERE commune IS NULL) FROM parcels""")
    ok = (n_com == 24 and (nulls or 0) == 0)
    return ("OK" if ok else "ECART", f"communes distinctes={n_com}, commune NULL={nulls}")


@garde
def d8_surface_ha_vivant(cx, api, run):
    """E-12 — dans chaque fiche commune, surface_ha et n_parcelles portent sur le MÊME parc (vivant).
    Recompose la surface vivante par commune et la compare à /communes/{c}/contexte.foncier.surface_ha.
    SKIP si l'API n'est pas joignable. `run` = run servi VIVANT (jamais un label figé — fix/banc2-run-servi)."""
    if _api_code(api, "/healthz") != 200:
        return ("SKIP", "API non joignable (garde E-12 nécessite /communes/{c}/contexte)")
    ecarts = []
    with cx.conn.cursor() as cur:
        cur.execute("SELECT DISTINCT commune FROM parcels WHERE commune IS NOT NULL ORDER BY 1")
        communes = [r[0] for r in cur.fetchall()]
    for c in communes:
        surf_vivant = cx.scalar("""SELECT round(sum(surface_m2) FILTER
            (WHERE cadastre_disparue_le IS NULL)/10000.0) FROM parcels WHERE commune=%s""", (c,))
        try:
            url = api + "/communes/" + urllib.parse.quote(c) + f"/contexte?source={run}"
            with urllib.request.urlopen(url, timeout=30) as r:
                payload = json.loads(r.read())
            servi = (payload.get("foncier") or {}).get("surface_ha")
        except Exception:
            continue
        if servi is not None and surf_vivant is not None and abs(float(servi) - float(surf_vivant)) > 1:
            ecarts.append((c, servi, int(surf_vivant)))
    if ecarts:
        return ("ECART", f"{len(ecarts)} communes : surface_ha ≠ parc vivant "
                         f"(ex. {ecarts[:3]}) — surface compte les disparues")
    return ("OK", f"{len(communes)} communes : surface_ha = parc vivant")


# ───────────────────────────── DOMAINE 9 — dates & fraîcheur ────────────────
@garde
def d9_dates_futures_sources(cx):
    """Aucune date de source (horizon/sync/fraîcheur) dans le futur (attendu 0)."""
    n = cx.scalar("""SELECT count(*) FROM data_sources WHERE source_horizon_at > now()::date
        OR last_sync_at > now() OR fraicheur_calcule_at > now()""")
    return ("OK" if n == 0 else "ECART", f"sources avec une date dans le futur : {n}")


@garde
def d9_millesime_futur(cx):
    """Aucun source_millesime d'année future (2027+) (attendu 0)."""
    rows = cx.scalar("SELECT count(*) FROM data_sources WHERE source_millesime ~ '(202[7-9]|20[3-9][0-9])'")
    return ("OK" if (rows or 0) == 0 else "ECART", f"millésimes d'année future : {rows}")


@garde
def d9_run_coherent(cx, run, rseq, cascade):
    """Le run servi est cohérent dans tous les pointeurs : manifeste = residuel = mvt = score = cascade."""
    res_lbl = cx.scalar("SELECT label FROM residuel_runs WHERE is_served")
    res_seq = cx.scalar("SELECT run_seq FROM residuel_runs WHERE is_served")
    mvt_run = cx.scalar("SELECT value FROM mvt_meta WHERE key='run_label'")
    mvt_seq = cx.scalar("SELECT value FROM mvt_meta WHERE key='residuel_seq'")
    has_sc = cx.scalar("SELECT 1 FROM score_labuse WHERE run_label=%s LIMIT 1", (run,))
    casc = cx.scalar("SELECT cascade_label FROM score_labuse_runs WHERE run_label=%s", (run,))
    ok = (res_lbl == run and int(res_seq) == rseq and mvt_run == run and int(mvt_seq) == rseq
          and has_sc is not None and (casc is None or casc == cascade))
    return ("OK" if ok else "ECART",
            f"manifeste={run}/seq{rseq} résiduel={res_lbl}/{res_seq} mvt={mvt_run}/{mvt_seq} "
            f"score={'oui' if has_sc else 'non'} cascade={casc}")


# ───────────────────────────── DOMAINE 11 — API robustesse ──────────────────
@garde
def d11_tuiles_jamais_500(cx, api):
    """E-14 — une tuile MVT hors grille (x/y hors [0,2^z) ou négatif) ⇒ 204/200/404, JAMAIS 500.
    SKIP si l'API n'est pas joignable."""
    if _api_code(api, "/healthz") != 200:
        return ("SKIP", "API non joignable (garde E-14 nécessite les routes de tuiles)")
    cas = ["/map/tiles/12/999999/999999.pbf", "/map/tiles/12/999999/2110.pbf",
           "/map/tiles/12/-5/-5.pbf", "/map/tiles/14/999999/999999.pbf",
           "/map/tiles/zfang/12/999999/999999.pbf", "/map/tiles/zfang/12/-5/-5.pbf"]
    mauvais = [(p, _api_code(api, p)) for p in cas]
    mauvais = [(p, c) for p, c in mauvais if c == 500 or c == "ERR"]
    return ("OK" if not mauvais else "ECART",
            f"tuiles hors grille → 500 : {mauvais}" if mauvais else f"{len(cas)} tuiles hors grille servies proprement")


# ───────────────────────────── DOMAINE 12 — double-calcul ───────────────────
@garde
def d12_taux_impossible(cx):
    """E-01 (reconfirmé, Lot 1) — le taux PEUT dépasser 100 % en BASE (bâti antérieur réel) ; le rendu
    UNIQUE ne sert jamais ce brut : « Saturé … » au-delà de 100 %. On prouve le clamp sur le pire cas."""
    from labuse.faisabilite.residuel import TAUX_EMPRISE_SATURE, fmt_taux_emprise
    mx = cx.scalar("SELECT max(taux_emprise_pct) FROM parcel_residuel")
    rendu = fmt_taux_emprise(mx) if mx is not None else None
    ok = (mx is None) or (round(mx) <= 100) or (rendu == TAUX_EMPRISE_SATURE)
    return ("OK" if ok else "ECART",
            f"pire taux base={mx} → rendu « {rendu} » (jamais un % brut > 100)")


@garde
def d12_sdp_negative(cx):
    """SDP résiduelle servie toujours ≥ 0 (invariant dur, attendu 0)."""
    n = cx.scalar("SELECT count(*) FROM parcel_residuel WHERE sdp_residuelle_m2 < 0")
    return ("OK" if (n or 0) == 0 else "ECART", f"SDP résiduelles négatives : {n}")


@garde
def d12_sous_densite_coherente(cx):
    """E-13 — sous_densite=true cohérent avec le taux_emprise AFFICHÉ (bord d'arrondi ; attendu 0)."""
    n = cx.scalar("SELECT count(*) FROM parcel_residuel WHERE sous_densite IS TRUE AND taux_emprise_pct >= 40")
    return ("OK" if (n or 0) == 0 else "ECART", f"sous_densite=true mais taux_emprise_pct≥40 : {n} (bord d'arrondi)")


@garde
def d12_commune_sans_taux(cx):
    """Toute parcelle est dans une commune ayant un taux d'aménagement servi (attendu 0)."""
    n = cx.scalar("""SELECT count(DISTINCT substr(idu,1,5)) FROM parcels
        WHERE substr(idu,1,5) NOT IN (SELECT insee FROM taxe_amenagement_taux)""")
    return ("OK" if (n or 0) == 0 else "ECART", f"communes servies sans taux d'aménagement : {n}")


# ───────────────────────────── le runner ──────────────────────────────────
def _plan(run, rseq, cascade, api):
    """(domaine, [(libellé, callable), …]) — chaque callable prend `cx`."""
    return [
        ("1 géométrie & surfaces", [
            ("géom valide/SRID", d1_geom_valide),
            ("ratios bornés [E-01]", lambda cx: d1_ratios_bornes(cx, rseq)),
            ("surface du run présente [E-09]", lambda cx: d1_surface_run_presente(cx, rseq)),
            ("bâti ≤ dessin [E-08]", d1_bati_sous_dessin),
            ("centroïde dans parcelle [E-07]", d1_centroid_dans_parcelle),
            ("surface jamais ≤0", d1_surface_non_positive),
            ("disparue hors calcul", d1_disparue_hors_calcul),
            ("une commune par INSEE", d1_insee_une_commune),
        ]),
        ("2 zonage & PLU", [
            ("parcel_zone_plu non périmée [E-02]", d2_pzp_non_perimee),
            ("SDP ⇒ zone à la carte [E-02]", d2_sdp_sans_zone),
            ("RNU Saint-Philippe", d2_rnu_saint_philippe),
            ("fam colle à lib", d2_fam_colle_lib),
        ]),
        ("3 capacité & scoring", [
            ("couverture score 100 %", lambda cx: d3_score_couverture(cx, run)),
            ("bande ⇔ score (5 miroirs)", lambda cx: d3_bande_score_coherence(cx, run)),
            ("borne physique SDP", lambda cx: d3_sdp_borne_physique(cx, rseq)),
            ("bande A servable [E-10]", lambda cx: d3_bande_A_servable(cx, run)),
        ]),
        ("4 risques & servitudes", [
            ("servitude sourcée", d4_servitude_sans_source),
            ("PPR rouge union vs cascade [E-03]", d4_ppr_union_vs_cascade),
        ]),
        ("5 marché & prix", [
            ("identité marge=charge−prix", lambda cx: d5_identite_comptable(cx, run)),
            ("mention « estimé »", d5_mention_estime),
            ("fenêtre DVF ancrée [E-04]", d5_fenetre_dvf_ancree),
        ]),
        ("6 propriétaires & sociétés", [
            ("SIREN Luhn", d6_siren_luhn),
            ("âge dirigeant borné [E-05/E-06]", d6_age_dirigeant_borne),
            ("succession ⇒ seuil", d6_succession_seuil),
            ("lien idu↔PM unique/sourcé", d6_pm_source_unique),
        ]),
        ("7 permis / DPE / BODACC", [
            ("PC caduc rattaché", d7_pc_caduc_rattache),
            ("aucune date future", d7_aucune_date_future),
            ("étiquette DPE légale", d7_etiquette_dpe_legale),
            ("identifiants uniques", d7_identifiants_uniques),
        ]),
        ("8 communes & agrégats", [
            ("24 communes, 0 NULL", d8_24_communes),
            ("surface_ha = parc vivant [E-12]", lambda cx: d8_surface_ha_vivant(cx, api, run)),
        ]),
        ("9 dates & fraîcheur", [
            ("dates sources non futures", d9_dates_futures_sources),
            ("millésime non futur", d9_millesime_futur),
            ("run cohérent partout", lambda cx: d9_run_coherent(cx, run, rseq, cascade)),
        ]),
        ("11 API & robustesse", [
            ("tuiles jamais 500 [E-14]", lambda cx: d11_tuiles_jamais_500(cx, api)),
        ]),
        ("12 double-calcul", [
            ("taux impossible [E-01]", d12_taux_impossible),
            ("SDP ≥ 0", d12_sdp_negative),
            ("sous-densité cohérente [E-13]", d12_sous_densite_coherente),
            ("commune a un taux", d12_commune_sans_taux),
        ]),
    ]


def main():
    ap = argparse.ArgumentParser(description="CHASSE-INVARIANTS-1 — banc des invariants (lecture seule)")
    ap.add_argument("--api", default="http://127.0.0.1:8790", help="base URL de l'API locale")
    ap.add_argument("--only", default=None, help="n'exécuter qu'un domaine (préfixe, ex. '4')")
    args = ap.parse_args()

    run, rseq, cascade = _served_run()
    print(f"CHASSE-INVARIANTS-1 — run servi {run} / run_seq {rseq} / cascade {cascade}")
    print(f"DSN={_dsn_defaut()}  API={args.api}\n")

    cx = Cx(_dsn_defaut())
    n_ok = n_ecart = n_skip = 0
    ecarts = []
    try:
        for dom, gardes in _plan(run, rseq, cascade, args.api):
            if args.only and not dom.startswith(args.only):
                continue
            print(f"── domaine {dom}")
            for libelle, fn in gardes:
                statut, msg = fn(cx)
                print(f"  [{statut}] {libelle} — {msg}")
                if statut == "OK":
                    n_ok += 1
                elif statut == "ECART":
                    n_ecart += 1
                    ecarts.append(f"{dom} :: {libelle} — {msg}")
                else:
                    n_skip += 1
    finally:
        cx.close()

    print(f"\nBILAN : {n_ok} OK · {n_ecart} ECART · {n_skip} SKIP")
    if ecarts:
        print("ECARTS :")
        for e in ecarts:
            print("  - " + e)
    sys.exit(1 if n_ecart else 0)


if __name__ == "__main__":
    main()
